from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import ROOT, config
from .embeddings import FoundryEmbeddingProvider, HashEmbeddingProvider
from .foundry_runtime import init_manager
from .vector_store import VectorStore


def evaluate_question(store: VectorStore, embedder, question: dict, top_k: int) -> dict:
    retrieved = store.search(embedder.embed(question["question"]), top_k)
    retrieved_doc_ids = [row["doc_id"] for row in retrieved]
    expected = set(question.get("expected_doc_ids", []))
    hit = bool(expected.intersection(retrieved_doc_ids))
    return {
        "id": question["id"],
        "question": question["question"],
        "expected_doc_ids": sorted(expected),
        "retrieved_doc_ids": retrieved_doc_ids,
        "hit": hit,
        "top_score": round(float(retrieved[0]["score"]), 4) if retrieved else 0,
    }


def summarize(results: list[dict]) -> dict:
    total = len(results)
    hits = sum(1 for item in results if item["hit"])
    return {
        "total": total,
        "hits": hits,
        "hit_rate": round(hits / total, 3) if total else 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate whether retrieval returns expected source documents.")
    parser.add_argument("--questions", default=str(ROOT / "eval" / "questions.json"), help="Path to evaluation set.")
    parser.add_argument("--top-k", type=int, default=config.top_k, help="Number of retrieved chunks to inspect.")
    parser.add_argument("--no-foundry", action="store_true", help="Use deterministic fallback embeddings for smoke tests.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    questions_path = Path(args.questions)
    questions = json.loads(questions_path.read_text(encoding="utf-8"))
    store = VectorStore(config.db_path)
    embedder = HashEmbeddingProvider() if args.no_foundry else FoundryEmbeddingProvider(config.embedding_model)
    if not args.no_foundry:
        embedder.init(init_manager())

    try:
        results = [evaluate_question(store, embedder, question, args.top_k) for question in questions]
        summary = summarize(results)
    finally:
        close = getattr(embedder, "close", None)
        if close:
            close()
        store.close()

    if args.json:
        print(json.dumps({"summary": summary, "results": results}, indent=2))
        return

    print("=== Retrieval Evaluation ===")
    print(f"Questions: {summary['total']}")
    print(f"Hits: {summary['hits']}")
    print(f"Hit rate: {summary['hit_rate'] * 100:.1f}%")
    print()
    for item in results:
        status = "PASS" if item["hit"] else "FAIL"
        print(f"{status} {item['id']}: {item['question']}")
        print(f"  expected: {', '.join(item['expected_doc_ids'])}")
        print(f"  retrieved: {', '.join(item['retrieved_doc_ids']) or 'none'}")


if __name__ == "__main__":
    main()
