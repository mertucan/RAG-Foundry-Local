from __future__ import annotations

import argparse
import json
import mimetypes
import os
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from app.config import DB_PATH, TOP_K
from app.db import connect, count_chunks, init_db
from app.embeddings import EmbeddingClient
from app.generate import AnswerGenerator
from app.retrieve import get_top_chunks


STATIC_DIR = Path(__file__).resolve().parent / "static"


class RagWebApp:
    def __init__(self, top_k: int = TOP_K, use_foundry: bool = True) -> None:
        self.top_k = top_k
        self.conn = connect(DB_PATH, check_same_thread=False)
        self._lock = threading.RLock()
        init_db(self.conn)
        self.embedder = EmbeddingClient()
        self.generator = AnswerGenerator(use_foundry=use_foundry)

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "chunk_count": count_chunks(self.conn),
                "database": str(DB_PATH),
                "embedding_provider": self.embedder.provider,
                "answer_provider": self.generator.provider,
                "top_k": self.top_k,
            }

    def ask(self, question: str) -> dict[str, object]:
        with self._lock:
            direct_answer = self._answer_status_question(question)
            if direct_answer is not None:
                return {
                    "answer": direct_answer,
                    "sources": [],
                    "status": self.status(),
                }

            chunks = get_top_chunks(self.conn, question, self.embedder, self.top_k)
            answer = self.generator.answer(question, chunks)
            status = self.status()
        return {
            "answer": answer,
            "sources": [
                {
                    "source": chunk.source,
                    "chunk_index": chunk.chunk_index,
                    "score": round(chunk.score, 4),
                    "preview": chunk.content[:360],
                }
                for chunk in chunks
            ],
            "status": status,
        }

    def _answer_status_question(self, question: str) -> str | None:
        normalized = question.casefold()
        asks_model = any(word in normalized for word in ["model", "provider", "hangi model"])
        asks_status = any(word in normalized for word in ["durum", "status", "calisiyor", "çalışıyor"])
        if not asks_model and not asks_status:
            return None

        status = self.status()
        return (
            "Su an cevap sağlayıcısı: "
            f"{status['answer_provider']}. Embedding sağlayıcısı: {status['embedding_provider']}. "
            f"Veritabanında {status['chunk_count']} dokuman parcası var. "
            "answer_provider `extractive-fallback` ise Foundry Local modeli devrede değildir; "
            "gercek LLM cevabi icin Foundry Local SDK/model kurulumunu tamamlayip sunucuyu `--no-foundry` olmadan baslat."
        )


class RagRequestHandler(BaseHTTPRequestHandler):
    app_state: RagWebApp

    def do_GET(self) -> None:
        if self.path == "/api/status":
            self._send_json(self.app_state.status())
            return

        self._serve_static()

    def do_POST(self) -> None:
        if self.path != "/api/ask":
            self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON"}, HTTPStatus.BAD_REQUEST)
            return

        question = str(payload.get("question", "")).strip()
        if not question:
            self._send_json({"error": "Soru bos olamaz."}, HTTPStatus.BAD_REQUEST)
            return

        self._send_json(self.app_state.ask(question))

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")

    def _serve_static(self) -> None:
        route = unquote(self.path.split("?", 1)[0])
        if route in {"", "/"}:
            route = "/index.html"

        target = (STATIC_DIR / route.lstrip("/")).resolve()
        if not _is_relative_to(target, STATIC_DIR) or not target.is_file():
            self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return

        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        data = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Yerel RAG web arayuzunu baslat.")
    parser.add_argument("--host", default="127.0.0.1", help="Dinlenecek host")
    parser.add_argument("--port", type=int, default=8000, help="Dinlenecek port")
    parser.add_argument("--top-k", type=int, default=TOP_K, help="Getirilecek kaynak parca sayisi")
    parser.add_argument(
        "--no-foundry",
        action="store_true",
        help="Foundry Local modelini baslatmadan retrieval/fallback modunda calistir",
    )
    parser.add_argument("--model", default=None, help="Foundry Local chat model alias'i")
    args = parser.parse_args()

    if args.model:
        os.environ["FOUNDRY_CHAT_MODEL"] = args.model

    RagRequestHandler.app_state = RagWebApp(top_k=args.top_k, use_foundry=not args.no_foundry)
    server = ThreadingHTTPServer((args.host, args.port), RagRequestHandler)
    print(f"RAG web arayuzu hazir: http://{args.host}:{args.port}")
    print("Cikmak icin Ctrl+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSunucu kapatiliyor...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
