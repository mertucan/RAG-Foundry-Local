import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.document_loader import LoadedDocument
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

    def query(self, message, history, filters=None):
        return {
            "text": f"Echo: {message}",
            "sources": [
                {"title": "Test Doc", "category": "Testing", "docId": "DOC-T1", "score": 0.99}
            ],
        }

    def query_stream(self, message, history, filters=None):
        yield {
            "type": "sources",
            "data": [{"title": "Test Doc", "category": "Testing", "docId": "DOC-T1", "score": 0.99}],
        }
        yield {"type": "text", "data": f"Echo: {message}"}

    def _embed(self, text):
        return [1.0, 0.0] if "rag" in text.lower() else [0.0, 1.0]


class ApiEndpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.docs_dir = Path(self.tmp.name) / "docs"
        self.docs_dir.mkdir()
        self.public_dir = Path(self.tmp.name) / "public"
        self.public_dir.mkdir()
        (self.public_dir / "index.html").write_text("<html>ok</html>", encoding="utf-8")
        self.store = VectorStore(Path(self.tmp.name) / "rag.db")
        self.store.insert("DOC-T1", "Test Doc", "Testing", 0, "RAG study note", [1.0, 0.0])
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
        self.assertIn("filters", res.json())

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
        self.assertIn(".pdf", res.json()["error"])

    def test_upload_accepts_markdown_and_indexes_it(self):
        content = """---
title: Uploaded Test
category: Testing
id: DOC-UP
---

# Uploaded Test

This document talks about RAG study notes with enough content to index.
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

    def test_upload_marks_duplicate_replacement(self):
        content = """---
title: Duplicate Test
category: Testing
id: DOC-T1
---

RAG duplicate content with enough text to index.
"""
        res = self.client.post(
            "/api/upload",
            content=content.encode("utf-8"),
            headers={"x-filename": "duplicate.md"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["duplicate"])
        self.assertIn("replaced", res.json()["warning"])

    def test_upload_accepts_pdf_and_indexes_extracted_text(self):
        with patch(
            "app.server.load_document_from_upload",
            return_value=LoadedDocument("paper", "Research Paper", "PDF Notes", "RAG research paper text."),
        ):
            res = self.client.post(
                "/api/upload",
                content=b"%PDF-1.4 fake test bytes",
                headers={"x-filename": "paper.pdf"},
            )
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertEqual(payload["docId"], "paper")
        self.assertEqual(payload["category"], "PDF Notes")
        self.assertTrue((self.docs_dir / "paper.pdf").exists())

    def test_delete_document_removes_index_and_file(self):
        (self.docs_dir / "delete-me.md").write_text("RAG delete me.", encoding="utf-8")
        self.store.insert("DOC-DEL", "Delete Me", "Testing", 0, "RAG delete me.", [1.0, 0.0], filename="delete-me.md")
        res = self.client.delete("/api/docs/DOC-DEL")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(self.store.exists(doc_id="DOC-DEL"))
        self.assertFalse((self.docs_dir / "delete-me.md").exists())

    def test_reindex_document_rebuilds_existing_file(self):
        content = """---
title: Reindex Me
category: Testing
id: DOC-RE
---

RAG reindex content with enough words for indexing.
"""
        (self.docs_dir / "reindex-me.md").write_text(content, encoding="utf-8")
        self.store.insert("DOC-RE", "Old", "Testing", 0, "old content", [0.0, 1.0], filename="reindex-me.md")
        res = self.client.post("/api/docs/DOC-RE/reindex")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["reindexed"])
        docs = {doc["doc_id"]: doc for doc in self.store.list_docs()}
        self.assertEqual(docs["DOC-RE"]["title"], "Reindex Me")

    def test_settings_returns_model_configuration(self):
        res = self.client.get("/api/settings")
        self.assertEqual(res.status_code, 200)
        self.assertIn("chatModel", res.json())

    def test_root_serves_ui(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("ok", res.text)


if __name__ == "__main__":
    unittest.main()
