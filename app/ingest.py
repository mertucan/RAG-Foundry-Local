from __future__ import annotations

import argparse
from pathlib import Path

from app.chunking import chunk_text
from app.config import CHUNK_OVERLAP, CHUNK_SIZE, DATA_DIR, DB_PATH
from app.db import connect, init_db, insert_chunk, reset_chunks
from app.document_loader import SUPPORTED_EXTENSIONS, load_document
from app.embeddings import EmbeddingClient


def ingest_documents(data_dir: Path = DATA_DIR, extra_files: list[Path] | None = None) -> int:
    data_dir.mkdir(parents=True, exist_ok=True)
    conn = connect(DB_PATH)
    init_db(conn)
    reset_chunks(conn)

    embedder = EmbeddingClient()
    total = 0

    paths = _collect_paths(data_dir, extra_files or [])

    for path, source in paths:
        text = load_document(path)
        chunks = chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)

        for index, chunk in enumerate(chunks):
            insert_chunk(conn, source, index, chunk, embedder.embed(chunk))
            total += 1

    conn.commit()
    conn.close()
    return total


def _collect_paths(data_dir: Path, extra_files: list[Path]) -> list[tuple[Path, str]]:
    paths: list[tuple[Path, str]] = []
    for path in sorted(data_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            paths.append((path, str(path.relative_to(data_dir))))

    for path in extra_files:
        resolved = path.expanduser().resolve()
        if resolved.is_file() and resolved.suffix.lower() in SUPPORTED_EXTENSIONS:
            paths.append((resolved, resolved.name))
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Dokumanlari RAG veritabanina isle.")
    parser.add_argument(
        "--file",
        action="append",
        type=Path,
        default=[],
        help="data/documents disindaki ek .txt, .md veya .docx dosyasi",
    )
    args = parser.parse_args()

    total = ingest_documents(extra_files=args.file)
    print(f"{total} dokuman parcasi SQLite veritabanina eklendi: {DB_PATH}")


if __name__ == "__main__":
    main()
