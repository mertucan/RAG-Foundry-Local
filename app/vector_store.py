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
              filename TEXT,
              page_number INTEGER,
              tags TEXT,
              course TEXT,
              topic TEXT,
              semester TEXT,
              source_type TEXT,
              chunk_index INTEGER NOT NULL,
              content TEXT NOT NULL,
              embedding_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_doc_id ON chunks(doc_id);
            """
        )
        for column, definition in {
            "filename": "TEXT",
            "page_number": "INTEGER",
            "tags": "TEXT",
            "course": "TEXT",
            "topic": "TEXT",
            "semester": "TEXT",
            "source_type": "TEXT",
        }.items():
            if existing_columns and column not in existing_columns:
                self.conn.execute(f"ALTER TABLE chunks ADD COLUMN {column} {definition}")
        self.conn.commit()

    def clear(self) -> None:
        self.conn.execute("DELETE FROM chunks")
        self.conn.commit()
        self._cache = None

    def insert(
        self,
        doc_id: str,
        title: str,
        category: str,
        chunk_index: int,
        content: str,
        embedding: list[float],
        *,
        filename: str = "",
        page_number: int | None = None,
        tags: str = "",
        course: str = "",
        topic: str = "",
        semester: str = "",
        source_type: str = "",
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO chunks (
              doc_id, title, category, filename, page_number, tags, course, topic, semester, source_type,
              chunk_index, content, embedding_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                doc_id,
                title,
                category,
                filename,
                page_number,
                tags,
                course,
                topic,
                semester,
                source_type,
                chunk_index,
                content,
                json.dumps(embedding),
            ),
        )
        self.conn.commit()
        self._cache = None

    def remove_by_doc_id(self, doc_id: str) -> None:
        self.conn.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
        self.conn.commit()
        self._cache = None

    def exists(self, *, doc_id: str | None = None, filename: str | None = None) -> bool:
        if doc_id:
            row = self.conn.execute("SELECT 1 FROM chunks WHERE doc_id = ? LIMIT 1", (doc_id,)).fetchone()
            if row:
                return True
        if filename:
            row = self.conn.execute("SELECT 1 FROM chunks WHERE filename = ? LIMIT 1", (filename,)).fetchone()
            if row:
                return True
        return False

    def filenames_for_doc(self, doc_id: str) -> list[str]:
        rows = self.conn.execute("SELECT DISTINCT filename FROM chunks WHERE doc_id = ?", (doc_id,)).fetchall()
        return [row["filename"] for row in rows if row["filename"]]

    def search(self, query_embedding: list[float], top_k: int = 5, filters: dict | None = None) -> list[dict]:
        rows = self._rows()
        scored: list[dict] = []
        for row in rows:
            if filters and not self._matches_filters(row, filters):
                continue
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
            """
            SELECT doc_id, title, category, filename, tags, course, topic, semester, source_type, COUNT(*) AS chunks
            FROM chunks
            GROUP BY doc_id, title, category, filename, tags, course, topic, semester, source_type
            ORDER BY title
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def filter_values(self) -> dict[str, list[str]]:
        docs = self.list_docs()
        values = {"course": set(), "topic": set(), "semester": set(), "source_type": set(), "tags": set()}
        for doc in docs:
            for field in ("course", "topic", "semester", "source_type"):
                if doc.get(field):
                    values[field].add(doc[field])
            for tag in split_tags(doc.get("tags") or ""):
                values["tags"].add(tag)
        return {key: sorted(items) for key, items in values.items()}

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

    def _matches_filters(self, row: dict, filters: dict) -> bool:
        for field in ("course", "topic", "semester", "source_type"):
            value = filters.get(field)
            if value and row.get(field) != value:
                return False
        tag = filters.get("tag")
        if tag and tag not in split_tags(row.get("tags") or ""):
            return False
        return True


def split_tags(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]
