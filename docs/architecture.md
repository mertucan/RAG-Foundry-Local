# Local RAG Architecture

This project follows the document plan's local RAG flow:

```text
Documents
  -> loader (.txt, .md, .docx)
  -> chunker
  -> embedding client
  -> SQLite chunk store
  -> query embedding
  -> cosine similarity retrieval
  -> prompt builder
  -> Foundry Local chat model
  -> answer with source names
```

## Components

- `app/document_loader.py`: Reads supported files from `data/documents` or explicit `--file` inputs.
- `app/chunking.py`: Splits long documents into overlapping chunks.
- `app/embeddings.py`: Uses a Foundry embedding model if `FOUNDRY_EMBEDDING_MODEL` is set and supported; otherwise uses deterministic local hash embeddings.
- `app/db.py`: Stores chunks and serialized embeddings in SQLite.
- `app/retrieve.py`: Embeds the user query and ranks chunks by cosine similarity.
- `app/generate.py`: Sends retrieved context to Foundry Local chat. If Foundry Local is not ready, it uses an extractive fallback so retrieval can still be debugged.
- `app/main.py`: CLI Q&A loop.

## Foundry Local

The current Foundry Local Python SDK uses:

```python
from foundry_local_sdk import Configuration, FoundryLocalManager

config = Configuration(app_name="rag_foundry_local")
FoundryLocalManager.initialize(config)
manager = FoundryLocalManager.instance
model = manager.catalog.get_model("qwen2.5-0.5b")
model.download(...)
model.load()
client = model.get_chat_client()
```

The default chat model alias is `qwen2.5-0.5b`, because Microsoft uses it in the official quickstart. You can override it:

```powershell
$env:FOUNDRY_CHAT_MODEL="qwen2.5-0.5b"
```

If your Foundry Local catalog exposes a supported embedding model through an OpenAI-compatible embeddings client, set:

```powershell
$env:FOUNDRY_EMBEDDING_MODEL="your-embedding-model-alias"
```

If not set, retrieval still works with deterministic local hash embeddings. This keeps the full RAG pipeline testable before adding a better local embedding model.

## Quality Checklist

- Add several real documents, not only one sample file.
- Run ingestion after every document change.
- Ask answerable and unanswerable questions.
- Check source scores after each answer.
- Tune `CHUNK_SIZE`, `CHUNK_OVERLAP`, and `--top-k` if retrieval is weak.
- Prefer concise source-grounded answers; the model should say when context is insufficient.
