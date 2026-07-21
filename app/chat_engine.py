from __future__ import annotations

from collections.abc import Generator
import re
from typing import Callable

from .config import config
from .embeddings import HashEmbeddingProvider
from .foundry_runtime import init_manager, normalize_progress
from .prompts import SYSTEM_PROMPT, SYSTEM_PROMPT_COMPACT
from .vector_store import VectorStore


StatusCallback = Callable[[dict], None]


class ChatEngine:
    def __init__(self) -> None:
        self.status_callback: StatusCallback | None = None
        self.store: VectorStore | None = None
        self.compact_mode = False
        self.manager = None
        self.chat_model = None
        self.embedding_model = None
        self.chat_client = None
        self.embedding_client = None
        self.fallback_embedder = HashEmbeddingProvider()

    def on_status(self, callback: StatusCallback) -> None:
        self.status_callback = callback

    def init(self) -> None:
        self._emit("init", "Initializing Foundry Local SDK...")
        self.manager = init_manager()

        self._init_embedding_model()
        self._init_chat_model()

        self.store = VectorStore(config.db_path)
        self._emit("ready", f"Vector store ready: {self.store.count()} chunks indexed.")

    def set_compact_mode(self, enabled: bool) -> None:
        self.compact_mode = enabled
        print(f"[ChatEngine] Compact mode: {'ON' if enabled else 'OFF'}")

    def retrieve(self, query: str) -> list[dict]:
        if self.store is None:
            raise RuntimeError("Vector store is not initialized.")
        top_k = config.compact_top_k if self.compact_mode else config.top_k
        return self.store.search(self._embed(query), top_k)

    def query(self, user_message: str, history: list[dict] | None = None) -> dict:
        chunks = self.retrieve(user_message)
        messages = self._build_messages(user_message, chunks, history or [])
        if self.chat_client is None:
            return {"text": self._fallback_answer(chunks), "sources": self._sources(chunks)}

        self._apply_generation_settings()
        response = self.chat_client.complete_chat(messages)
        text = response.choices[0].message.content
        return {"text": text, "sources": self._sources(chunks)}

    def query_stream(self, user_message: str, history: list[dict] | None = None) -> Generator[dict, None, None]:
        yield {"type": "status", "phase": "retrieving", "data": "Retrieving relevant local context..."}
        chunks = self.retrieve(user_message)
        yield {"type": "sources", "data": self._sources(chunks)}
        yield {"type": "status", "phase": "generating", "data": "Generating answer with the local model..."}
        messages = self._build_messages(user_message, chunks, history or [])

        if self.chat_client is None:
            yield {"type": "text", "data": self._fallback_answer(chunks)}
            return

        self._apply_generation_settings()
        for chunk in self.chat_client.complete_streaming_chat(messages):
            if not getattr(chunk, "choices", None):
                continue
            delta = getattr(chunk.choices[0], "delta", None)
            content = getattr(delta, "content", None)
            if content:
                yield {"type": "text", "data": content}

    def close(self) -> None:
        for model in (self.chat_model, self.embedding_model):
            if model is not None:
                try:
                    model.unload()
                except Exception:
                    pass
        if self.store is not None:
            self.store.close()

    def _init_embedding_model(self) -> None:
        self._emit("embedding", f"Discovering embedding model: {config.embedding_model}")
        self.embedding_model = self.manager.catalog.get_model(config.embedding_model)
        if not self.embedding_model.is_cached:
            self._emit("embedding_download", f"Downloading embedding model {config.embedding_model}...", 0)
            self.embedding_model.download(
                lambda progress: self._emit(
                    "embedding_download",
                    f"Downloading embedding model {config.embedding_model}... {round(normalize_progress(progress) * 100)}%",
                    normalize_progress(progress),
                )
            )
        else:
            self._emit("embedding_cached", f"Embedding model {config.embedding_model} is already cached.")
        self._emit("embedding_loading", f"Loading embedding model {config.embedding_model}...")
        self.embedding_model.load()
        self.embedding_client = self.embedding_model.get_embedding_client()
        self._emit("embedding_ready", f"Embedding model ready: {config.embedding_model}")

    def _init_chat_model(self) -> None:
        self._emit("catalog", "Discovering available chat models...")
        self.chat_model = self.manager.catalog.get_model(config.chat_model)
        self._emit("variant", f"Selected chat model: {self.chat_model.alias}")
        if not self.chat_model.is_cached:
            self._emit("download", f"Downloading {self.chat_model.alias}...", 0)
            self.chat_model.download(
                lambda progress: self._emit(
                    "download",
                    f"Downloading {self.chat_model.alias}... {round(normalize_progress(progress) * 100)}%",
                    normalize_progress(progress),
                )
            )
        else:
            self._emit("cached", f"Model {self.chat_model.alias} is already cached.")
        self._emit("loading", f"Loading {self.chat_model.alias} into memory...")
        self.chat_model.load()
        self.chat_client = self.chat_model.get_chat_client()
        self._apply_generation_settings()
        self._emit("ready", f"Model ready: {self.chat_model.alias}")

    def _apply_generation_settings(self) -> None:
        if self.chat_client is None:
            return
        self.chat_client.settings.max_tokens = (
            config.compact_max_output_tokens if self.compact_mode else config.max_output_tokens
        )
        self.chat_client.settings.temperature = config.temperature
        self.chat_client.settings.top_p = config.top_p

    def _embed(self, text: str) -> list[float]:
        if self.embedding_client is None:
            return self.fallback_embedder.embed(text)
        response = self.embedding_client.generate_embedding(text)
        return list(response.data[0].embedding)

    def _build_messages(self, user_message: str, chunks: list[dict], history: list[dict]) -> list[dict]:
        context = "\n\n".join(
            f"--- Document {i + 1}: {chunk['title']} [{chunk['category']}] ---\n{chunk['content']}"
            for i, chunk in enumerate(chunks)
        ) or "No relevant documents found in local knowledge base."
        prompt = SYSTEM_PROMPT_COMPACT if self.compact_mode else SYSTEM_PROMPT
        return [
            {"role": "system", "content": prompt},
            {"role": "system", "content": f"Retrieved context from local knowledge base:\n\n{context}"},
            *history,
            {"role": "user", "content": user_message},
        ]

    def _sources(self, chunks: list[dict]) -> list[dict]:
        return [
            {
                "title": chunk["title"],
                "category": chunk["category"],
                "docId": chunk["doc_id"],
                "chunkIndex": chunk["chunk_index"],
                "score": round(float(chunk["score"]), 2),
                "preview": self._preview(chunk["content"]),
            }
            for chunk in chunks
        ]

    def _preview(self, content: str, limit: int = 320) -> str:
        text = re.sub(r"\s+", " ", content).strip()
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."

    def _fallback_answer(self, chunks: list[dict]) -> str:
        if not chunks:
            return "This information is not available in the local knowledge base."
        return (
            "**Summary**\n"
            "Foundry Local chat model is unavailable, so this fallback shows the most relevant retrieved context.\n\n"
            "**Reference**\n"
            f"{chunks[0]['title']} [{chunks[0]['category']}]\n\n"
            f"{chunks[0]['content'][:1200]}"
        )

    def _emit(self, phase: str, message: str, progress: float | None = None) -> None:
        status = {"phase": phase, "message": message}
        if progress is not None:
            status["progress"] = progress
        print(f"[ChatEngine] {message}")
        if self.status_callback:
            self.status_callback(status)
