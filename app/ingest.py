from __future__ import annotations

import argparse

from .chunker import chunk_text
from .config import config
from .document_loader import SUPPORTED_EXTENSIONS, load_document_from_path, page_number_for_chunk
from .embeddings import HashEmbeddingProvider
from .foundry_runtime import create_embedding_provider
from .vector_store import VectorStore


def ingest(use_foundry: bool = True) -> tuple[int, int]:
    print("=== Academic Library RAG - Python Document Ingestion ===\n")
    docs_dir = config.docs_dir
    files = sorted([p for p in docs_dir.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS])
    if not files:
        raise SystemExit(f"No supported documents found in {docs_dir}")

    embedder = create_embedding_provider() if use_foundry else HashEmbeddingProvider()
    store = VectorStore(config.db_path)
    store.clear()

    total_chunks = 0
    try:
        for file_path in files:
            doc = load_document_from_path(file_path)
            chunks = chunk_text(doc.body, config.chunk_size, config.chunk_overlap)
            for i, chunk in enumerate(chunks):
                store.insert(
                    doc.doc_id,
                    doc.title,
                    doc.category,
                    i,
                    chunk,
                    embedder.embed(chunk),
                    filename=file_path.name,
                    page_number=page_number_for_chunk(chunk),
                    tags=doc.tags,
                    course=doc.course,
                    topic=doc.topic,
                    semester=doc.semester,
                    source_type=doc.source_type,
                )
            total_chunks += len(chunks)
            print(f"  - {file_path.name} -> {len(chunks)} chunk(s) [{doc.category}]")
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
