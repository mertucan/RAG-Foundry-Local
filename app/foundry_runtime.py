from __future__ import annotations

import atexit
import os
from typing import Any


class FoundryUnavailable(RuntimeError):
    pass


class FoundryRuntime:
    def __init__(self, app_name: str = "rag_foundry_local") -> None:
        self.app_name = app_name
        self._manager: Any | None = None
        self._loaded_models: dict[str, Any] = {}

    def load_chat_client(self, alias: str | None = None) -> tuple[Any, str]:
        alias = alias or os.getenv("FOUNDRY_CHAT_MODEL", "qwen2.5-0.5b")
        manager = self._get_manager()
        model = self._loaded_models.get(alias)

        if model is None:
            print(f"Foundry model seciliyor: {alias}")
            model = manager.catalog.get_model(alias)
            if model is None:
                raise FoundryUnavailable(f"Foundry model bulunamadi: {alias}")
            _download_model(model)
            print("Foundry model yukleniyor...")
            model.load()
            self._loaded_models[alias] = model

        client = model.get_chat_client()
        model_id = getattr(model, "id", alias)
        return client, model_id

    def close(self) -> None:
        for model in self._loaded_models.values():
            try:
                model.unload()
            except Exception:
                pass
        self._loaded_models.clear()

    def _get_manager(self) -> Any:
        if self._manager is not None:
            return self._manager

        try:
            from foundry_local_sdk import Configuration, FoundryLocalManager  # type: ignore
        except Exception as exc:
            raise FoundryUnavailable(
                "foundry-local-sdk paketi kurulu degil. `pip install -r requirements.txt` calistir."
            ) from exc

        config = Configuration(app_name=self.app_name)
        FoundryLocalManager.initialize(config)
        manager = FoundryLocalManager.instance
        print("Foundry execution provider'lari hazirlaniyor...")
        try:
            manager.download_and_register_eps(progress_callback=None)
        except TypeError:
            manager.download_and_register_eps()
        self._manager = manager
        return manager


def _download_model(model: Any) -> None:
    is_cached = getattr(model, "is_cached", False)
    if callable(is_cached):
        is_cached = is_cached()
    if is_cached:
        return

    try:
        model.download(lambda progress: print(f"\rModel indiriliyor: {progress:.1f}%", end=""))
        print()
    except TypeError:
        model.download()


runtime = FoundryRuntime()
atexit.register(runtime.close)
