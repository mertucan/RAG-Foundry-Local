from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .chunker import cosine_similarity


class VectorStore:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._cache: list[dict] | None = None
        self._init()

    def _init(self) -> None:
        existing = self.conn.execute("PRAGMA table_info(chunks)").fetchall()
        existing_columns = {row["name"] for row in existing}
        if existing_columns and "embedding_json" not in existing_columns:
            self.conn.execute("DROP TABLE chunks")
            self.conn.commit()

        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS chunks (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              doc_id TEXT NOT NULL,
              title TEXT,
              category TEXT,
              chunk_index INTEGER NOT NULL,
              content TEXT NOT NULL,
              embedding_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_doc_id ON chunks(doc_id);
            """
        )
        self.conn.commit()

    def clear(self) -> None:
        self.conn.execute("DELETE FROM chunks")
        self.conn.commit()
        self._cache = None

    def insert(self, doc_id: str, title: str, category: str, chunk_index: int, content: str, embedding: list[float]) -> None:
        self.conn.execute(
            "INSERT INTO chunks (doc_id, title, category, chunk_index, content, embedding_json) VALUES (?, ?, ?, ?, ?, ?)",
            (doc_id, title, category, chunk_index, content, json.dumps(embedding)),
        )
        self.conn.commit()
        self._cache = None

    def remove_by_doc_id(self, doc_id: str) -> None:
        self.conn.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
        self.conn.commit()
        self._cache = None

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[dict]:
        rows = self._rows()
        scored: list[dict] = []
        for row in rows:
            score = cosine_similarity(query_embedding, row["embedding"])
            if score > 0:
                item = {k: v for k, v in row.items() if k != "embedding"}
                item["score"] = score
                scored.append(item)
        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:top_k]

    def count(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) AS cnt FROM chunks").fetchone()["cnt"])

    def list_docs(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT doc_id, title, category, COUNT(*) AS chunks FROM chunks GROUP BY doc_id ORDER BY title"
        ).fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        self.conn.close()

    def _rows(self) -> list[dict]:
        if self._cache is None:
            rows = self.conn.execute("SELECT * FROM chunks").fetchall()
            self._cache = []
            for row in rows:
                item = dict(row)
                item["embedding"] = json.loads(item.pop("embedding_json"))
                self._cache.append(item)
        return self._cache
