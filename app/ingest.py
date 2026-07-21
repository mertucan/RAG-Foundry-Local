from __future__ import annotations

import argparse
from pathlib import Path

from .chunker import chunk_text, parse_front_matter
from .config import config
from .embeddings import HashEmbeddingProvider
from .foundry_runtime import create_embedding_provider
from .vector_store import VectorStore


def ingest(use_foundry: bool = True) -> tuple[int, int]:
    print("=== Gas Field RAG - Python Document Ingestion ===\n")
    docs_dir = config.docs_dir
    files = sorted([p for p in docs_dir.iterdir() if p.suffix.lower() == ".md"])
    if not files:
        raise SystemExit(f"No markdown files found in {docs_dir}")

    embedder = create_embedding_provider() if use_foundry else HashEmbeddingProvider()
    store = VectorStore(config.db_path)
    store.clear()

    total_chunks = 0
    try:
        for file_path in files:
            raw = file_path.read_text(encoding="utf-8")
            meta, body = parse_front_matter(raw)
            doc_id = meta.get("id") or file_path.stem
            title = meta.get("title") or file_path.name
            category = meta.get("category") or "Uncategorised"
            chunks = chunk_text(body, config.chunk_size, config.chunk_overlap)
            for i, chunk in enumerate(chunks):
                store.insert(doc_id, title, category, i, chunk, embedder.embed(chunk))
            total_chunks += len(chunks)
            print(f"  - {file_path.name} -> {len(chunks)} chunk(s) [{category}]")
    finally:
        close = getattr(embedder, "close", None)
        if close:
            close()
        store.close()

    print(f"\nIngestion complete: {total_chunks} chunks from {len(files)} documents.")
    print(f"Database: {config.db_path}")
    return len(files), total_chunks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-foundry", action="store_true", help="Use deterministic local hash embeddings instead of Foundry embeddings.")
    args = parser.parse_args()
    ingest(use_foundry=not args.no_foundry)


if __name__ == "__main__":
    main()
