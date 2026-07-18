from __future__ import annotations

import json
import math
import re
import sqlite3
from dataclasses import dataclass

from app.db import iter_chunks
from app.embeddings import EmbeddingClient


@dataclass(frozen=True)
class RetrievedChunk:
    source: str
    chunk_index: int
    content: str
    score: float


def get_top_chunks(
    conn: sqlite3.Connection,
    question: str,
    embedder: EmbeddingClient,
    top_k: int,
) -> list[RetrievedChunk]:
    query_embedding = embedder.embed(question)
    scored: list[RetrievedChunk] = []

    for row in iter_chunks(conn):
        embedding = json.loads(row["embedding"])
        vector_score = cosine_similarity(query_embedding, embedding)
        lexical_score = _lexical_score(question, row["content"])
        score = (0.72 * vector_score) + (0.28 * lexical_score)
        scored.append(
            RetrievedChunk(
                source=row["source"],
                chunk_index=row["chunk_index"],
                content=row["content"],
                score=score,
            )
        )

    scored.sort(key=lambda chunk: chunk.score, reverse=True)
    return scored[:top_k]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0

    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def _lexical_score(question: str, content: str) -> float:
    query_tokens = _expanded_tokens(question)
    content_tokens = _expanded_tokens(content)
    if not query_tokens or not content_tokens:
        return 0.0

    overlap = len(query_tokens & content_tokens) / len(query_tokens)
    boost = _section_boost(question, content)
    return min(1.0, overlap + boost)


def _section_boost(question: str, content: str) -> float:
    q = question.lower()
    c = content.lower()
    numbers = set(re.findall(r"\d+", q))
    asks_week = any(word in q for word in ["hafta", "week"])

    if asks_week:
        for number in numbers:
            if f"week {number}" in c or f"weeks {number}" in c or f"hafta {number}" in c:
                return 0.45
    return 0.0


def _expanded_tokens(text: str) -> set[str]:
    raw = re.findall(r"[a-zA-ZğüşöçıİĞÜŞÖÇ]+|\d+", text.lower())
    expansions = {
        "hafta": {"week"},
        "haftasi": {"week"},
        "haftası": {"week"},
        "teslim": {"deliverable", "milestone", "documentation", "presentation"},
        "edilecek": {"deliverable"},
        "sonunda": {"end"},
        "kullaniliyor": {"use", "used"},
        "kullanılıyor": {"use", "used"},
        "dokuman": {"document"},
        "doküman": {"document"},
    }
    tokens: set[str] = set()
    for token in raw:
        if len(token) <= 2 and not token.isdigit():
            continue
        tokens.add(token)
        tokens.update(expansions.get(token, set()))
    return tokens
