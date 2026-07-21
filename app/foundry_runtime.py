from __future__ import annotations

from typing import Callable

from .config import config
from .embeddings import FoundryEmbeddingProvider


def init_manager():
    from foundry_local_sdk import Configuration, FoundryLocalManager

    sdk_config = Configuration(app_name=config.app_name)
    FoundryLocalManager.initialize(sdk_config)
    return FoundryLocalManager.instance


def normalize_progress(progress: float) -> float:
    return max(0.0, min(1.0, progress / 100 if progress > 1 else progress))


def create_embedding_provider(status: Callable[[str, str, float | None], None] | None = None) -> FoundryEmbeddingProvider:
    manager = init_manager()
    provider = FoundryEmbeddingProvider(config.embedding_model, status)
    provider.init(manager)
    return provider
