from __future__ import annotations

import hashlib
import math
from typing import Callable

from .chunker import term_frequency


class HashEmbeddingProvider:
    """Deterministic offline fallback used only when Foundry embeddings are unavailable."""

    def __init__(self, dimensions: int = 384):
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for term, freq in term_frequency(text).items():
            digest = hashlib.sha256(term.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[idx] += sign * float(freq)

        norm = math.sqrt(sum(v * v for v in vector))
        return [v / norm for v in vector] if norm else vector


class FoundryEmbeddingProvider:
    def __init__(self, model_alias: str, status: Callable[[str, str, float | None], None] | None = None):
        self.model_alias = model_alias
        self.status = status
        self.model = None
        self.client = None

    def init(self, manager) -> None:
        self._emit("embedding", f"Discovering embedding model: {self.model_alias}", None)
        self.model = manager.catalog.get_model(self.model_alias)
        if not self.model.is_cached:
            self._emit("embedding_download", f"Downloading embedding model {self.model_alias}...", 0)
            self.model.download(lambda progress: self._emit_progress(progress))
        else:
            self._emit("embedding_cached", f"Embedding model {self.model_alias} is already cached.", None)
        self._emit("embedding_loading", f"Loading embedding model {self.model_alias}...", None)
        self.model.load()
        self.client = self.model.get_embedding_client()
        self._emit("embedding_ready", f"Embedding model ready: {self.model_alias}", None)

    def embed(self, text: str) -> list[float]:
        if self.client is None:
            raise RuntimeError("Embedding client is not initialized.")
        response = self.client.generate_embedding(text)
        item = response.data[0]
        return list(item.embedding)

    def close(self) -> None:
        if self.model is not None:
            try:
                self.model.unload()
            except Exception:
                pass

    def _emit_progress(self, progress: float) -> None:
        normalized = max(0.0, min(1.0, progress / 100 if progress > 1 else progress))
        self._emit("embedding_download", f"Downloading embedding model {self.model_alias}... {round(normalized * 100)}%", normalized)

    def _emit(self, phase: str, message: str, progress: float | None) -> None:
        if self.status:
            self.status(phase, message, progress)
