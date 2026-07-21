import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.vector_store import VectorStore


class MockEngine:
    def __init__(self):
        self.compact_mode = False
        self.store = None

    def on_status(self, _callback):
        return None

    def init(self):
        return None

    def close(self):
        if self.store:
            self.store.close()

    def set_compact_mode(self, enabled):
        self.compact_mode = enabled

    def query(self, message, history):
        return {
            "text": f"Echo: {message}",
            "sources": [
                {"title": "Test Doc", "category": "Testing", "docId": "DOC-T1", "score": 0.99}
            ],
        }

    def query_stream(self, message, history):
        yield {
            "type": "sources",
            "data": [{"title": "Test Doc", "category": "Testing", "docId": "DOC-T1", "score": 0.99}],
        }
        yield {"type": "text", "data": f"Echo: {message}"}

    def _embed(self, text):
        return [1.0, 0.0] if "gas" in text.lower() else [0.0, 1.0]


class ApiEndpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.docs_dir = Path(self.tmp.name) / "docs"
        self.docs_dir.mkdir()
        self.public_dir = Path(self.tmp.name) / "public"
        self.public_dir.mkdir()
        (self.public_dir / "index.html").write_text("<html>ok</html>", encoding="utf-8")
        self.store = VectorStore(Path(self.tmp.name) / "rag.db")
        self.store.insert("DOC-T1", "Test Doc", "Testing", 0, "Gas leak detection", [1.0, 0.0])
        self.engine = MockEngine()
        self.engine.store = self.store

        patches = [
            patch("app.server.config.docs_dir", self.docs_dir),
            patch("app.server.config.public_dir", self.public_dir),
            patch("app.server.engine", self.engine),
            patch("app.server.engine_ready", True),
            patch("app.server.last_status", {"phase": "ready", "message": "Ready"}),
        ]
        self.patchers = patches
        for p in self.patchers:
            p.start()

        from app.server import app

        self.client = TestClient(app)

    def tearDown(self):
        for p in reversed(self.patchers):
            p.stop()
        self.store.close()
        self.tmp.cleanup()

    def test_health_returns_ready_status(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "ok")
        self.assertEqual(res.json()["phase"], "ready")

    def test_docs_returns_indexed_documents(self):
        res = self.client.get("/api/docs")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["docs"][0]["doc_id"], "DOC-T1")

    def test_chat_validates_message(self):
        res = self.client.post("/api/chat", json={})
        self.assertEqual(res.status_code, 400)
        self.assertIn("error", res.json())

    def test_chat_returns_text_and_sources(self):
        res = self.client.post("/api/chat", json={"message": "hello", "compact": True})
        self.assertEqual(res.status_code, 200)
        self.assertIn("hello", res.json()["text"])
        self.assertTrue(res.json()["sources"])
        self.assertTrue(self.engine.compact_mode)

    def test_chat_stream_returns_sse_events(self):
        res = self.client.post("/api/chat/stream", json={"message": "hello"})
        self.assertEqual(res.status_code, 200)
        body = res.text
        self.assertIn("data:", body)
        self.assertIn("[DONE]", body)
        self.assertIn("Echo: hello", body)

    def test_upload_rejects_missing_filename(self):
        res = self.client.post("/api/upload", content=b"enough content")
        self.assertEqual(res.status_code, 400)
        self.assertIn("x-filename", res.json()["error"])

    def test_upload_rejects_invalid_extension(self):
        res = self.client.post("/api/upload", content=b"enough content", headers={"x-filename": "bad.exe"})
        self.assertEqual(res.status_code, 400)
        self.assertIn(".md", res.json()["error"])

    def test_upload_accepts_markdown_and_indexes_it(self):
        content = """---
title: Uploaded Test
category: Testing
id: DOC-UP
---

# Uploaded Test

This document talks about gas leak testing with enough content to index.
"""
        res = self.client.post(
            "/api/upload",
            content=content.encode("utf-8"),
            headers={"x-filename": "../../../uploaded.md"},
        )
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertEqual(payload["docId"], "DOC-UP")
        self.assertEqual(payload["title"], "Uploaded Test")
        self.assertTrue(payload["suggestions"])
        self.assertNotIn("..", payload["filename"])
        self.assertTrue((self.docs_dir / "uploaded.md").exists())

    def test_root_serves_ui(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("ok", res.text)


if __name__ == "__main__":
    unittest.main()
