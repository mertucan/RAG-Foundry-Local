---
title: Local RAG Architecture Notes
category: System Architecture
id: DOC-SA-001
course: Local AI Systems
topic: Architecture
semester: Summer 2026
source_type: architecture-note
tags: architecture, fastapi, sqlite
---

# Local RAG Architecture Notes

The local RAG application has four main parts: ingestion, vector storage, retrieval, and answer generation. The browser UI communicates with a Python FastAPI server, and the server communicates with Foundry Local for embedding and chat generation.

## Components

- `app.ingest` reads markdown documents and builds the vector database.
- `app.vector_store` stores chunks and vectors in SQLite.
- `app.chat_engine` retrieves relevant chunks and builds prompts.
- `app.server` exposes chat, upload, status, and document listing endpoints.
- `public/index.html` provides the browser interface without a frontend build step.

## Runtime Upload

Runtime upload adds markdown or text files to the local knowledge base without restarting the server. The uploaded content is chunked, embedded, stored, and immediately searchable.
