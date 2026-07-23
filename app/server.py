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
from .chunker import chunk_text
from .config import config
from .document_loader import is_supported_document, load_document_from_path, load_document_from_upload, page_number_for_chunk


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
    return {
        "status": "ok" if engine_ready else "loading",
        "model": config.chat_model,
        "embeddingModel": config.embedding_model,
        **last_status,
    }


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
        return {"docs": [], "filters": {}}
    return {"docs": engine.store.list_docs(), "filters": engine.store.filter_values()}


@app.delete("/api/docs/{doc_id}")
def delete_doc(doc_id: str) -> dict:
    if engine.store is None:
        return JSONResponse({"error": "The local AI engine is still loading. Wait for Offline Ready, then try again."}, status_code=503)
    filenames = engine.store.filenames_for_doc(doc_id)
    if not filenames and not engine.store.exists(doc_id=doc_id):
        return JSONResponse({"error": "Document not found"}, status_code=404)
    engine.store.remove_by_doc_id(doc_id)
    deleted_files = []
    for filename in filenames:
        candidate = (config.docs_dir / filename).resolve()
        if str(candidate).startswith(str(config.docs_dir.resolve())) and candidate.is_file():
            candidate.unlink()
            deleted_files.append(filename)
    return {"success": True, "docId": doc_id, "deletedFiles": deleted_files, "totalChunks": engine.store.count()}


@app.post("/api/docs/{doc_id}/reindex")
def reindex_doc(doc_id: str) -> dict:
    if engine.store is None:
        return JSONResponse({"error": "The local AI engine is still loading. Wait for Offline Ready, then try again."}, status_code=503)
    filenames = engine.store.filenames_for_doc(doc_id)
    if not filenames:
        return JSONResponse({"error": "Document file is not available for reindexing"}, status_code=404)
    file_path = (config.docs_dir / filenames[0]).resolve()
    if not str(file_path).startswith(str(config.docs_dir.resolve())) or not file_path.is_file():
        return JSONResponse({"error": "Document file is missing"}, status_code=404)
    try:
        result = index_file(file_path, replace=True)
    except Exception as exc:
        print(f"[API] Reindex error: {type(exc).__name__}: {exc}")
        return JSONResponse({"error": friendly_error(exc)}, status_code=500)
    return {**result, "success": True, "reindexed": True}


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
    filters = payload.get("filters") if isinstance(payload.get("filters"), dict) else {}
    try:
        return await asyncio.to_thread(engine.query, message, history, clean_filters(filters))
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
    filters = payload.get("filters") if isinstance(payload.get("filters"), dict) else {}

    async def events():
        output: queue.Queue = queue.Queue()
        sentinel = object()

        def run_stream() -> None:
            try:
                for item in engine.query_stream(message, history, clean_filters(filters)):
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
    if not is_supported_document(safe_name):
        return JSONResponse({"error": "Only .md, .txt, and .pdf files are accepted"}, status_code=400)
    body = await request.body()
    if len(body) > config.max_upload_bytes:
        return JSONResponse({"error": "File too large"}, status_code=413)
    if engine.store is None:
        return JSONResponse(
            {"error": "The local AI engine is still loading. Wait for Offline Ready, then try again."},
            status_code=503,
        )
    try:
        doc = load_document_from_upload(safe_name, body)
    except UnicodeDecodeError:
        return JSONResponse({"error": "Text documents must be UTF-8 encoded"}, status_code=400)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except RuntimeError as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)
    if len(doc.body) < 10:
        return JSONResponse({"error": "Document content is too short"}, status_code=400)

    config.docs_dir.mkdir(parents=True, exist_ok=True)
    file_path = (config.docs_dir / safe_name).resolve()
    if not str(file_path).startswith(str(config.docs_dir.resolve())):
        return JSONResponse({"error": "Invalid filename"}, status_code=400)
    duplicate = engine.store.exists(doc_id=doc.doc_id, filename=safe_name)
    file_path.write_bytes(body)

    result = index_file(file_path, loaded_doc=doc, replace=True)

    return {
        "success": True,
        "filename": safe_name,
        "docId": result["docId"],
        "title": result["title"],
        "category": result["category"],
        "chunks": result["chunks"],
        "totalChunks": engine.store.count(),
        "duplicate": duplicate,
        "warning": "This document was already indexed and has been replaced." if duplicate else "",
        "suggestions": upload_suggestions(result["title"], result["category"]),
    }


@app.get("/api/settings")
def settings() -> dict:
    return {
        "chatModel": config.chat_model,
        "embeddingModel": config.embedding_model,
        "topK": config.top_k,
        "compactTopK": config.compact_top_k,
        "maxOutputTokens": config.max_output_tokens,
        "compactMaxOutputTokens": config.compact_max_output_tokens,
        "ocrEnabled": config.ocr_enabled,
        "ocrLanguage": config.ocr_language,
    }


@app.post("/api/settings/model")
async def update_model(request: Request) -> dict:
    global engine_ready
    payload = await request.json()
    alias = payload.get("chatModel")
    if not isinstance(alias, str) or not alias.strip():
        return JSONResponse({"error": "chatModel is required"}, status_code=400)
    if engine.manager is None:
        return JSONResponse({"error": "The local AI engine is still loading. Wait for Offline Ready, then try again."}, status_code=503)
    try:
        engine_ready = False
        broadcast_status({"phase": "loading", "message": f"Switching chat model to {alias.strip()}..."})
        result = await asyncio.to_thread(engine.set_chat_model, alias)
        engine_ready = True
        broadcast_status({"phase": "ready", "message": f"Model ready: {result['model']}"})
        return {"success": True, **result}
    except Exception as exc:
        engine_ready = True
        broadcast_status({"phase": "error", "message": str(exc)})
        print(f"[API] Model switch error: {type(exc).__name__}: {exc}")
        return JSONResponse({"error": friendly_error(exc)}, status_code=500)


def index_file(file_path: Path, loaded_doc=None, replace: bool = True) -> dict:
    if engine.store is None:
        raise RuntimeError("Vector store is not initialized.")
    doc = loaded_doc or load_document_from_path(file_path)
    if replace:
        engine.store.remove_by_doc_id(doc.doc_id)
    chunks = chunk_text(doc.body, config.chunk_size, config.chunk_overlap)
    for index, chunk in enumerate(chunks):
        engine.store.insert(
            doc.doc_id,
            doc.title,
            doc.category,
            index,
            chunk,
            engine._embed(chunk),
            filename=file_path.name,
            page_number=page_number_for_chunk(chunk),
            tags=doc.tags,
            course=doc.course,
            topic=doc.topic,
            semester=doc.semester,
            source_type=doc.source_type,
        )
    return {"docId": doc.doc_id, "title": doc.title, "category": doc.category, "chunks": len(chunks)}


def clean_filters(filters: dict) -> dict:
    allowed = {"course", "topic", "semester", "source_type", "tag"}
    return {key: str(value).strip() for key, value in filters.items() if key in allowed and str(value).strip()}


def upload_suggestions(title: str, category: str) -> list[str]:
    return [
        f"What are the key points in {title}?",
        f"How does {title} relate to my study notes?",
        f"Summarize {title} for revision.",
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

    print("=== Academic Library RAG - Python Local Assistant ===\n")
    print(f"[Server] UI available at http://{config.host}:{config.port}")
    print("[Server] Initializing model in background...\n")
    uvicorn.run("app.server:app", host=config.host, port=config.port, reload=False)


if __name__ == "__main__":
    main()
