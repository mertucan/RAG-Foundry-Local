# Test and Evaluation Report

## Scope

This report evaluates the Python Foundry Local RAG assistant against the summer school project goals:

- ingest local documents,
- generate and store embeddings,
- retrieve relevant chunks from SQLite,
- construct grounded prompts,
- answer through a local Foundry chat model,
- serve a usable local web UI,
- support runtime document upload,
- expose source chunk previews and suggested upload questions,
- provide CLI chat mode,
- measure retrieval quality with a curated evaluation set,
- handle basic API validation and edge cases.

## Test Environment

- OS: Windows
- Python environment: local `.venv`
- Backend: FastAPI / Uvicorn
- Embedding model: `qwen3-embedding-0.6b`
- Chat model: `phi-3.5-mini`
- Vector store: SQLite at `data/rag.db`
- Knowledge base: 20 markdown gas engineering documents in `docs/`

Generated runtime artifacts such as `.venv`, `data/rag.db`, logs, and model caches are ignored by Git.

## Automated Tests

Run:

```powershell
python -m unittest discover -s tests
```

Current automated coverage:

| Area | Covered |
|---|---|
| Front-matter parsing | Yes |
| Chunking with overlap | Yes |
| Term frequency / cosine similarity utility | Yes |
| SQLite vector-store insert/search/list behavior | Yes |
| `/api/health` | Yes |
| `/api/docs` | Yes |
| `/api/chat` success and validation | Yes |
| `/api/chat/stream` SSE shape | Yes |
| `/api/upload` success and validation | Yes |
| Static root UI route | Yes |

The endpoint tests use a mocked engine so they run quickly and do not require loading local AI models.

## Manual / Integration Evaluation

### Retrieval Evaluation

Command:

```powershell
python -m app.evaluate
```

Evaluation set:

```text
eval/questions.json
```

The command embeds each evaluation question, retrieves the configured top-k chunks from SQLite, and checks whether at least one expected document ID appears in the retrieved set. It reports total questions, hits, hit rate, expected document IDs, retrieved document IDs, and the top retrieval score.

Use JSON output for saved reports or CI parsing:

```powershell
python -m app.evaluate --json
```

Result target: pass when the hit rate is high enough for the current corpus and demo goals. For this teaching corpus, the expected target is 80% or higher.

Observed result after rebuilding the vector store from the 20 gas engineering markdown files:

- Questions: 6
- Hits: 6
- Hit rate: 100.0%

Result: Pass.

### Ingestion

Command:

```powershell
python -m app.ingest
```

Observed result:

- 20 markdown documents processed.
- 42 chunks generated.
- Embeddings were generated through Foundry Local.
- SQLite database was written to `data/rag.db`.

Result: Pass.

### Server Startup

Command:

```powershell
python -m app.server
```

Observed result:

- Server available at `http://127.0.0.1:3000`.
- `/api/health` returned `status: ok`.
- Foundry Local loaded the chat model.
- Vector store reported indexed chunks.

Result: Pass.

### Grounded Question Answering

Test question:

```text
How do I detect a gas leak?
```

Observed result:

- The model returned safety-first guidance.
- The answer referenced leak detection procedure content.
- Source metadata was returned with document titles, categories, IDs, and relevance scores.

Result: Pass.

### Runtime Upload

Expected behavior:

- `.md` and `.txt` documents are accepted.
- Invalid extensions are rejected.
- Missing filename headers are rejected.
- Uploaded documents are saved to `docs/`, chunked, embedded, and indexed without restarting the server.
- The upload response returns suggested questions.
- The web UI renders suggested questions as clickable prompts.

Automated endpoint tests cover this behavior with a mocked embedding path.

Result: Pass.

### CLI Mode

Command:

```powershell
python -m app.cli
```

Expected behavior:

- Loads the same Foundry Local chat and embedding models.
- Uses the same SQLite vector store and prompts as the web app.
- Prints the grounded answer and source references in the terminal.
- Supports faster short-answer mode with `python -m app.cli --compact`.

Result: Pass when the server-independent terminal chat returns a grounded answer and source list.

## Known Limitations

- Endpoint tests mock the model engine. They validate API behavior, not live model quality.
- Live model response quality should be evaluated with an expanded curated question set for each new domain.
- The current retrieval uses brute-force cosine similarity over SQLite rows, which is appropriate for a small teaching corpus. Larger corpora may need an approximate nearest-neighbor index or a vector database extension.
- No final presentation slide deck is included; the application and README are ready for demo use.

## Recommended Evaluation Set

Use at least these categories when adapting the project:

| Category | Example |
|---|---|
| Answerable procedural question | "How do I detect a gas leak?" |
| Safety-critical question | "What should I do before confined space entry?" |
| Fault diagnosis | "What causes low outlet pressure?" |
| Equipment maintenance | "How do I calibrate a sensor?" |
| Unanswerable question | "What is the company holiday policy?" |
| Empty / invalid input | Empty string or malformed JSON |
| Upload workflow | Upload a new `.md` document and ask about it |

## Status

The project satisfies the technical implementation requirements for a Python local RAG assistant with Foundry Local, SQLite, embeddings, web UI, runtime upload, CLI mode, retrieval evaluation, tests, and documentation.
