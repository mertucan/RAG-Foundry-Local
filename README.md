# Academic Library Local RAG - Python Foundry Local Assistant

A fully local Retrieval-Augmented Generation (RAG) assistant for searching personal academic notes, research summaries, course materials, project briefs, and markdown/text exports of PDF notes. The app ingests documents, creates local embeddings with Microsoft Foundry Local, stores vectors in SQLite, retrieves relevant chunks for a question, and sends the grounded prompt to a local Foundry chat model.

The browser UI is still a single static HTML file in `public/`, but the application backend is now Python to match the summer school project plan.

## What This Project Covers

- Local Python RAG application structure
- Foundry Local chat model loading through the Python SDK
- Foundry Local embedding model usage for document and query embeddings
- SQLite-backed vector store
- Markdown ingestion with YAML front-matter
- Local web UI with streaming responses over Server-Sent Events
- Runtime `.md` / `.txt` / `.pdf` document upload
- Source previews and relevance scores in the web UI
- PDF page references in source results
- Course, topic, semester, source-type, and tag filters
- Document delete and reindex actions
- Duplicate upload warnings
- User-editable Foundry Local chat model alias
- Suggested questions after runtime uploads
- CLI chat mode for terminal demos
- Retrieval evaluation with a curated question set
- `.env`-based configuration
- Unit tests using Python's built-in `unittest`

## Prerequisites

- Python 3.11 or later
- Foundry Local installed
- Node.js is no longer required for the app backend

Install Foundry Local on Windows:

```powershell
winget install Microsoft.FoundryLocal
```

Optional OCR support for scanned PDFs:

```powershell
winget install UB-Mannheim.TesseractOCR
```

If Tesseract is not on PATH, set `RAG_TESSERACT_CMD` in `.env` to the installed `tesseract.exe` path.

Create and activate a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

If your machine does not have the `py` launcher, install Python from `python.org` and make sure it is added to PATH.

## Quick Start

Ingest documents with Foundry Local embeddings:

```powershell
python -m app.ingest
```

Start the web app:

```powershell
python -m app.server
```

Open:

```text
http://127.0.0.1:3000
```

Use the terminal chat interface:

```powershell
python -m app.cli
```

For shorter answers on slower machines:

```powershell
python -m app.cli --compact
```

For a fast smoke test without downloading an embedding model, use deterministic local fallback embeddings:

```powershell
python -m app.ingest --no-foundry
```

The production path for the summer school plan is `python -m app.ingest` without `--no-foundry`.

## Models

Default models are configured in [app/config.py](app/config.py):

- Chat model: `phi-3.5-mini`
- Embedding model: `qwen3-embedding-0.6b`

Foundry Local downloads and caches these models locally on first use. The model files are not stored in this repository and are ignored by Git.

## Document Format

Add markdown, text, or PDF documents to `docs/`. Markdown supports optional front-matter:

```markdown
---
title: Troubleshooting Widget Errors
category: Support
id: KB-001
course: Example Course
topic: Troubleshooting
semester: Summer 2026
source_type: note
tags: widget, errors
---

# Troubleshooting Widget Errors

...your content here...
```

Run `python -m app.ingest` again after replacing the corpus. For PDFs, the app extracts embedded text. Scanned image-only PDFs need OCR first.

## Runtime Upload

The UI upload button accepts `.md`, `.txt`, and `.pdf` files while the server is running. Uploaded files are saved to `docs/`, text is extracted when needed, and the content is chunked, embedded, and indexed immediately without restarting the server. After upload, the web UI shows suggested study questions that can be clicked immediately.

PDF behavior:

- Text-based PDFs are parsed with `pypdf`.
- Scanned/image-only PDFs fall back to OCR when Tesseract is installed.
- OCR can be configured with `RAG_ENABLE_OCR`, `RAG_OCR_LANGUAGE`, `RAG_OCR_DPI`, `RAG_OCR_MAX_PAGES`, and `RAG_TESSERACT_CMD`.

## Library Controls

The web UI includes:

- Filters for course, topic, semester, source type, and tag.
- Document delete and reindex buttons in the upload/document modal.
- Duplicate upload warnings when a document ID or filename already exists.
- A chat model input in the header. Enter a Foundry Local chat model alias and click `Load`.

Changing the chat model affects generation only. If you change the embedding model in `.env`, run `python -m app.ingest` again so stored vectors and query vectors match.

## RAG Pipeline

1. `app.ingest` reads every supported file in `docs/`: `.md`, `.txt`, and `.pdf`.
2. `app.chunker` parses front-matter and splits documents into overlapping chunks.
3. Foundry Local generates an embedding for each chunk.
4. `app.vector_store` stores chunk text and embedding vectors in SQLite.
5. A user question is embedded with the same embedding model.
6. SQLite rows are ranked by cosine similarity.
7. Top chunks are injected into the system prompt.
8. Foundry Local generates a grounded answer with the local chat model.
9. Retrieval and generation status events stream to the browser.
10. The answer streams back to the browser through SSE.
11. Source references include document ID, chunk number, relevance score, and a short chunk preview.

## Project Structure

```text
app/
  chunker.py          Markdown parsing, chunking, cosine similarity
  config.py           Paths, models, chunk settings, server settings
  document_loader.py  Markdown, text, PDF, and OCR text extraction
  embeddings.py       Foundry embedding provider and fallback provider
  foundry_runtime.py  Foundry Local SDK initialization helpers
  ingest.py           Batch ingestion script
  evaluate.py         Retrieval evaluation command
  cli.py              Terminal chat interface
  vector_store.py     SQLite vector store
  chat_engine.py      Retrieval + prompt + chat orchestration
  server.py           FastAPI web server and API endpoints
  prompts.py          Full and compact system prompts
public/
  index.html          Static browser UI
docs/
  *.md/.txt/.pdf      Local academic knowledge base
tests/
  test_*.py           Unit tests
eval/
  questions.json      Retrieval evaluation set
data/
  rag.db              Generated SQLite vector database, ignored by Git
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Model/server status |
| `GET` | `/api/status` | SSE status stream for model loading |
| `GET` | `/api/docs` | Indexed document list |
| `DELETE` | `/api/docs/{doc_id}` | Delete an indexed document and its stored file |
| `POST` | `/api/docs/{doc_id}/reindex` | Rebuild one document from disk |
| `POST` | `/api/chat` | Non-streaming chat response |
| `POST` | `/api/chat/stream` | Streaming chat response |
| `POST` | `/api/upload` | Runtime document upload |
| `GET` | `/api/settings` | Current runtime settings |
| `POST` | `/api/settings/model` | Load a different Foundry Local chat model |

## Testing

```powershell
python -m unittest discover -s tests
```

The tests cover chunking, vector-store behavior, API validation, chat endpoints, SSE response shape, document upload, document listing, health checks, and static UI serving. Endpoint tests use a mocked engine so they do not need to load Foundry Local models.

Run retrieval evaluation against the indexed SQLite database:

```powershell
python -m app.evaluate
```

For JSON output:

```powershell
python -m app.evaluate --json
```

For a quick command smoke test without loading Foundry Local embeddings:

```powershell
python -m app.evaluate --no-foundry
```

Use `--no-foundry` only to verify that the command runs. Retrieval quality should be measured with `python -m app.evaluate` against a database ingested with the same Foundry embedding model.

See [reports/test-evaluation-report.md](reports/test-evaluation-report.md) for the test and evaluation report.

## Configuration

Runtime settings can be changed with a local `.env` file. Start from:

```powershell
Copy-Item .env.example .env
```

Common settings:

| Variable | Purpose |
|---|---|
| `RAG_CHAT_MODEL` | Foundry Local chat model alias |
| `RAG_EMBEDDING_MODEL` | Foundry Local embedding model alias |
| `RAG_TOP_K` | Number of chunks retrieved in normal mode |
| `RAG_COMPACT_TOP_K` | Number of chunks retrieved in Edge Mode |
| `RAG_MAX_OUTPUT_TOKENS` | Normal answer token limit |
| `RAG_COMPACT_MAX_OUTPUT_TOKENS` | Edge Mode answer token limit |
| `RAG_PORT` | Local web server port |
| `RAG_ENABLE_OCR` | Enable OCR fallback for scanned PDFs |
| `RAG_OCR_LANGUAGE` | Tesseract language code, for example `eng` or `tur` |
| `RAG_TESSERACT_CMD` | Optional path to `tesseract.exe` |

## Improvement Ideas

- Add a document detail view with full chunk previews.
- Add answer feedback buttons to mark useful or weak responses.
- Add saved chats for study sessions.
- Add automatic evaluation reports after every ingest.
- Add OCR language presets for English and Turkish scanned PDFs.
- Add duplicate content hashing, not just duplicate filename/document ID checks.

## Adapting This Library

1. Replace files in `docs/` with your own notes, summaries, and project documents.
2. Edit [app/prompts.py](app/prompts.py) if you want a different academic tone or answer format.
3. Tune `RAG_CHUNK_SIZE`, `RAG_CHUNK_OVERLAP`, and `RAG_TOP_K` in `.env`.
4. Change `RAG_CHAT_MODEL` or `RAG_EMBEDDING_MODEL` in `.env` to another Foundry Local catalog model.
5. Update [eval/questions.json](eval/questions.json) with representative questions and expected document IDs.

## Performance Tuning

The default settings are tuned for local responsiveness:

- `top_k = 2`: full mode retrieves two chunks.
- `compact_top_k = 1`: Edge Mode retrieves one chunk.
- `max_output_tokens = 512`: full mode caps generated output.
- `compact_max_output_tokens = 256`: Edge Mode gives shorter, faster answers.
- `temperature = 0.1`: keeps answers deterministic and focused.

If answers are still slow, enable Edge Mode in the UI or reduce `max_output_tokens` further.

## Privacy

The app is designed for local execution. Documents, prompts, generated answers, SQLite data, and downloaded model weights remain on the machine. Git ignores generated databases, model caches, virtual environments, logs, and environment files.

## License

MIT
