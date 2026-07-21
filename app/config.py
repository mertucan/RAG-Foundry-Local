from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional during very early setup
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(ROOT / ".env")


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value else default


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value else default


def _path_env(name: str, default: Path) -> Path:
    value = os.getenv(name)
    if not value:
        return default
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


class Config:
    app_name = "gas-field-local-rag-python"
    chat_model = os.getenv("RAG_CHAT_MODEL", "phi-3.5-mini")
    embedding_model = os.getenv("RAG_EMBEDDING_MODEL", "qwen3-embedding-0.6b")

    docs_dir = _path_env("RAG_DOCS_DIR", ROOT / "docs")
    public_dir = ROOT / "public"
    db_path = _path_env("RAG_DB_PATH", ROOT / "data" / "rag.db")

    chunk_size = _int_env("RAG_CHUNK_SIZE", 200)
    chunk_overlap = _int_env("RAG_CHUNK_OVERLAP", 25)
    top_k = _int_env("RAG_TOP_K", 2)
    compact_top_k = _int_env("RAG_COMPACT_TOP_K", 1)
    max_output_tokens = _int_env("RAG_MAX_OUTPUT_TOKENS", 512)
    compact_max_output_tokens = _int_env("RAG_COMPACT_MAX_OUTPUT_TOKENS", 256)
    temperature = _float_env("RAG_TEMPERATURE", 0.1)
    top_p = _float_env("RAG_TOP_P", 0.9)

    host = os.getenv("RAG_HOST", "127.0.0.1")
    port = _int_env("RAG_PORT", 3000)
    max_upload_bytes = _int_env("RAG_MAX_UPLOAD_BYTES", 2 * 1024 * 1024)


config = Config()
