from __future__ import annotations

import asyncio
import json
import queue
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Header, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .chat_engine import ChatEngine
from .chunker import chunk_text, parse_front_matter
from .config import config


engine = ChatEngine()
engine_ready = False
last_status: dict = {"phase": "init", "message": "Starting..."}
status_queues: set[asyncio.Queue] = set()


def friendly_error(exc: Exception) -> str:
    text = str(exc).strip()
    lower = text.lower()
    if "not initialized" in lower or "still loading" in lower:
        return "The local AI engine is still loading. Wait for Offline Ready, then try again."
    if "connection" in lower or "foundry" in lower:
        return "Foundry Local could not answer right now. Check that Foundry Local is installed and the model is cached."
    if "context length" in lower or "token" in lower:
        return "The request was too large for the local model. Try Edge Mode or ask a shorter question."
    return "The local model failed while generating. Check the terminal for technical details."


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async def init_background() -> None:
        global engine_ready
        try:
            await asyncio.to_thread(engine.init)
            engine_ready = True
            broadcast_status({"phase": "ready", "message": "Ready"})
            print("[Server] Fully offline - no outbound connections.")
        except Exception as exc:
            broadcast_status({"phase": "error", "message": str(exc)})
            print(f"Failed to start model engine: {exc}")

    task = asyncio.create_task(init_background())
    try:
        yield
    finally:
        if not task.done():
            task.cancel()
        engine.close()


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data:;"
    )
    return response


def broadcast_status(status: dict) -> None:
    global last_status
    last_status = status
    for queue in list(status_queues):
        queue.put_nowait(status)


engine.on_status(broadcast_status)
app.mount("/static", StaticFiles(directory=config.public_dir), name="static")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok" if engine_ready else "loading", "model": config.chat_model, **last_status}


@app.get("/api/status")
async def status_stream():
    queue: asyncio.Queue = asyncio.Queue()
    status_queues.add(queue)

    async def events():
        try:
            yield f"data: {json.dumps(last_status)}\n\n"
            if engine_ready:
                yield f"data: {json.dumps({'phase': 'ready', 'message': 'Ready'})}\n\n"
                return
            while True:
                status = await queue.get()
                yield f"data: {json.dumps(status)}\n\n"
                if status.get("phase") == "ready":
                    return
        finally:
            status_queues.discard(queue)

    return StreamingResponse(events(), media_type="text/event-stream")


@app.get("/api/docs")
def docs() -> dict:
    if engine.store is None:
        return {"docs": []}
    return {"docs": engine.store.list_docs()}


@app.post("/api/chat")
async def chat(request: Request) -> dict:
    payload = await request.json()
    message = payload.get("message")
    if not isinstance(message, str) or not message:
        return JSONResponse({"error": "message is required"}, status_code=400)
    if not engine_ready:
        return JSONResponse(
            {"error": "The local AI engine is still loading. Wait for Offline Ready, then try again."},
            status_code=503,
        )
    if "compact" in payload:
        engine.set_compact_mode(bool(payload["compact"]))
    history = payload.get("history") if isinstance(payload.get("history"), list) else []
    try:
        return await asyncio.to_thread(engine.query, message, history)
    except Exception as exc:
        print(f"[API] Chat error: {type(exc).__name__}: {exc}")
        return JSONResponse({"error": friendly_error(exc)}, status_code=500)


@app.post("/api/chat/stream")
async def chat_stream(request: Request):
    payload = await request.json()
    message = payload.get("message")
    if not isinstance(message, str) or not message:
        return JSONResponse({"error": "message is required"}, status_code=400)
    if not engine_ready:
        return JSONResponse(
            {"error": "The local AI engine is still loading. Wait for Offline Ready, then try again."},
            status_code=503,
        )
    if "compact" in payload:
        engine.set_compact_mode(bool(payload["compact"]))
    history = payload.get("history") if isinstance(payload.get("history"), list) else []

    async def events():
        output: queue.Queue = queue.Queue()
        sentinel = object()

        def run_stream() -> None:
            try:
                for item in engine.query_stream(message, history):
                    output.put(item)
            except Exception as exc:
                print(f"[API] Stream error: {type(exc).__name__}: {exc}")
                output.put({"type": "error", "data": friendly_error(exc)})
            finally:
                output.put(sentinel)

        task = asyncio.create_task(asyncio.to_thread(run_stream))
        while True:
            item = await asyncio.to_thread(output.get)
            if item is sentinel:
                break
            yield f"data: {json.dumps(item)}\n\n"
        await task
        yield "data: [DONE]\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@app.post("/api/upload")
async def upload(request: Request, x_filename: str | None = Header(default=None)) -> dict:
    if not x_filename:
        return JSONResponse({"error": "x-filename header is required"}, status_code=400)
    safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", Path(x_filename).name)
    if not safe_name.endswith((".md", ".txt")):
        return JSONResponse({"error": "Only .md and .txt files are accepted"}, status_code=400)
    body = await request.body()
    if len(body) > config.max_upload_bytes:
        return JSONResponse({"error": "File too large"}, status_code=413)
    content = body.decode("utf-8")
    if len(content) < 10:
        return JSONResponse({"error": "Document content is too short"}, status_code=400)
    if engine.store is None:
        return JSONResponse(
            {"error": "The local AI engine is still loading. Wait for Offline Ready, then try again."},
            status_code=503,
        )

    config.docs_dir.mkdir(parents=True, exist_ok=True)
    file_path = (config.docs_dir / safe_name).resolve()
    if not str(file_path).startswith(str(config.docs_dir.resolve())):
        return JSONResponse({"error": "Invalid filename"}, status_code=400)
    file_path.write_text(content, encoding="utf-8")

    meta, body_text = parse_front_matter(content)
    doc_id = meta.get("id") or Path(safe_name).stem
    title = meta.get("title") or safe_name
    category = meta.get("category") or "Uploaded"
    engine.store.remove_by_doc_id(doc_id)
    chunks = chunk_text(body_text, config.chunk_size, config.chunk_overlap)
    for index, chunk in enumerate(chunks):
        engine.store.insert(doc_id, title, category, index, chunk, engine._embed(chunk))

    return {
        "success": True,
        "filename": safe_name,
        "docId": doc_id,
        "title": title,
        "category": category,
        "chunks": len(chunks),
        "totalChunks": engine.store.count(),
        "suggestions": upload_suggestions(title, category),
    }


def upload_suggestions(title: str, category: str) -> list[str]:
    return [
        f"What are the key steps in {title}?",
        f"What safety warnings apply to {title}?",
        f"Summarize {title} for field use.",
    ]


@app.get("/")
def index():
    return FileResponse(config.public_dir / "index.html")


@app.get("/{path:path}")
def spa(path: str):
    candidate = (config.public_dir / path).resolve()
    if str(candidate).startswith(str(config.public_dir.resolve())) and candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(config.public_dir / "index.html")


def main() -> None:
    import uvicorn

    print("=== Gas Field RAG - Python Local Support Agent ===\n")
    print(f"[Server] UI available at http://{config.host}:{config.port}")
    print("[Server] Initializing model in background...\n")
    uvicorn.run("app.server:app", host=config.host, port=config.port, reload=False)


if __name__ == "__main__":
    main()
