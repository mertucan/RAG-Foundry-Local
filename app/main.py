from __future__ import annotations

import argparse
import os

from app.config import DB_PATH, TOP_K
from app.db import connect, count_chunks, init_db
from app.embeddings import EmbeddingClient
from app.generate import AnswerGenerator
from app.retrieve import get_top_chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Yerel RAG soru-cevap asistani.")
    parser.add_argument("--top-k", type=int, default=TOP_K, help="Getirilecek kaynak parca sayisi")
    parser.add_argument(
        "--hide-sources",
        action="store_true",
        help="Cevaptan sonra kaynak skorlarini yazdirma",
    )
    parser.add_argument(
        "--no-foundry",
        action="store_true",
        help="Foundry Local modelini baslatmadan retrieval/fallback modunda calistir",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Foundry Local chat model alias'i, orn: qwen2.5-0.5b",
    )
    args = parser.parse_args()
    if args.model:
        os.environ["FOUNDRY_CHAT_MODEL"] = args.model

    conn = connect(DB_PATH)
    init_db(conn)

    if count_chunks(conn) == 0:
        print("Veritabani bos. Once su komutu calistir:")
        print("python -m app.ingest")
        return

    embedder = EmbeddingClient()
    generator = AnswerGenerator(use_foundry=not args.no_foundry)

    print("Local RAG Assistant hazir. Cikmak icin 'q' yaz.")
    print(f"Embedding provider: {embedder.provider}")
    print(f"Answer provider: {generator.provider}")
    while True:
        question = input("\nSoru> ").strip()
        if question.lower() in {"q", "quit", "exit"}:
            break
        if not question:
            print("Bos soru gonderme; bir sey sor bakalim.")
            continue

        chunks = get_top_chunks(conn, question, embedder, args.top_k)
        answer = generator.answer(question, chunks)
        print(f"\nCevap:\n{answer}")

        if not args.hide_sources:
            print("\nKaynak skorlari:")
            for chunk in chunks:
                print(f"- {chunk.source} / parca {chunk.chunk_index}: {chunk.score:.3f}")


if __name__ == "__main__":
    main()
