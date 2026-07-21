from __future__ import annotations

import math
import re
from collections import Counter


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    match = re.match(r"^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$", text)
    if not match:
        return {}, text

    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    return meta, match.group(2)


def chunk_text(text: str, max_tokens: int = 400, overlap_tokens: int = 50) -> list[str]:
    words = [w for w in re.split(r"\s+", text.strip()) if w]
    if not words:
        return []
    if len(words) <= max_tokens:
        return [text]

    chunks: list[str] = []
    start = 0
    step = max(1, max_tokens - overlap_tokens)
    while start < len(words):
        end = min(start + max_tokens, len(words))
        chunks.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        start += step
    return chunks


def term_frequency(text: str) -> dict[str, int]:
    tokens = re.sub(r"[^a-z0-9\-']", " ", text.lower()).split()
    return dict(Counter(t for t in tokens if len(t) > 1))


def cosine_similarity(a: list[float] | dict[str, int], b: list[float] | dict[str, int]) -> float:
    if isinstance(a, dict) and isinstance(b, dict):
        if not a or not b:
            return 0.0
        dot = sum(freq * b.get(term, 0) for term, freq in a.items())
        norm_a = math.sqrt(sum(freq * freq for freq in a.values()))
        norm_b = math.sqrt(sum(freq * freq for freq in b.values()))
        return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

    if not isinstance(a, list) or not isinstance(b, list) or not a or not b:
        return 0.0
    limit = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(limit))
    norm_a = math.sqrt(sum(x * x for x in a[:limit]))
    norm_b = math.sqrt(sum(x * x for x in b[:limit]))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0
