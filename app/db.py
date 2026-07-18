from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable


def connect(db_path: Path, check_same_thread: bool = True) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=check_same_thread)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            embedding TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source)")
    conn.commit()


def reset_chunks(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM chunks")
    conn.commit()


def insert_chunk(
    conn: sqlite3.Connection,
    source: str,
    chunk_index: int,
    content: str,
    embedding: list[float],
) -> None:
    conn.execute(
        """
        INSERT INTO chunks (source, chunk_index, content, embedding)
        VALUES (?, ?, ?, ?)
        """,
        (source, chunk_index, content, json.dumps(embedding)),
    )


def iter_chunks(conn: sqlite3.Connection) -> Iterable[sqlite3.Row]:
    return conn.execute(
        "SELECT id, source, chunk_index, content, embedding FROM chunks ORDER BY id"
    )


def count_chunks(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS count FROM chunks").fetchone()
    return int(row["count"])
