from __future__ import annotations

import hashlib
import math
import os
import re
from typing import Any

from app.foundry_runtime import FoundryUnavailable, runtime


class EmbeddingClient:
    def __init__(self) -> None:
        self._foundry = _try_create_foundry_embedding_client()
        self.provider = "foundry" if self._foundry is not None else "local-hash"

    def embed(self, text: str) -> list[float]:
        if self._foundry is not None:
            try:
                return self._foundry.embed(text)
            except Exception as exc:
                print(f"Foundry embedding kullanilamadi, fallback kullaniliyor: {exc}")
                self._foundry = None
                self.provider = "local-hash"

        return _hash_embedding(text)


class _FoundryEmbeddingClient:
    def __init__(self) -> None:
        self.alias = os.getenv("FOUNDRY_EMBEDDING_MODEL", "")
        if not self.alias:
            raise FoundryUnavailable("FOUNDRY_EMBEDDING_MODEL ayarlanmadi")

        self.client, self.model = _try_get_embedding_client(self.alias)

    def embed(self, text: str) -> list[float]:
        response = self.client.embeddings.create(model=self.model, input=text)
        return list(response.data[0].embedding)


def _try_get_embedding_client(alias: str) -> tuple[Any, str]:
    # Some Foundry Local builds expose an OpenAI-compatible embeddings client for
    # embedding-capable models. If the installed SDK does not, the hashed local
    # embedding keeps the RAG pipeline usable and deterministic.
    manager = runtime._get_manager()
    model = manager.catalog.get_model(alias)
    if model is None:
        raise FoundryUnavailable(f"Embedding modeli bulunamadi: {alias}")
    _download_if_needed(model)
    model.load()
    if hasattr(model, "get_openai_client"):
        return model.get_openai_client(), getattr(model, "id", alias)
    if hasattr(manager, "get_openai_client"):
        return manager.get_openai_client(), getattr(model, "id", alias)
    raise FoundryUnavailable("Bu Foundry SDK embeddings client saglamiyor")


def _download_if_needed(model: Any) -> None:
    is_cached = getattr(model, "is_cached", False)
    if callable(is_cached):
        is_cached = is_cached()
    if not is_cached:
        model.download()


def _try_create_foundry_embedding_client() -> _FoundryEmbeddingClient | None:
    try:
        return _FoundryEmbeddingClient()
    except Exception:
        return None


def _hash_embedding(text: str, dimensions: int = 384) -> list[float]:
    vector = [0.0] * dimensions
    tokens = _expanded_tokens(text)

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def _expanded_tokens(text: str) -> list[str]:
    raw_tokens = re.findall(r"[a-zA-ZğüşöçıİĞÜŞÖÇ]+|\d+", text.lower())
    expansions = {
        "hafta": ["week"],
        "haftasi": ["week"],
        "haftası": ["week"],
        "teslim": ["deliverable", "milestone", "documentation", "presentation"],
        "edilecek": ["deliverable"],
        "sonunda": ["end"],
        "nedir": ["what"],
        "nasil": ["how"],
        "nasıl": ["how"],
        "neden": ["why"],
        "kullaniliyor": ["use", "used"],
        "kullanılıyor": ["use", "used"],
        "dokuman": ["document"],
        "doküman": ["document"],
        "cevap": ["answer"],
        "soru": ["question"],
    }

    tokens: list[str] = []
    for token in raw_tokens:
        tokens.append(token)
        tokens.extend(expansions.get(token, []))
    return tokens
