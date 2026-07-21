[![JavaScript](https://img.shields.io/badge/JavaScript-ES2022-F7DF1E?logo=javascript&logoColor=000)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)
[![Node.js](https://img.shields.io/badge/Node.js-%E2%89%A5%2020-339933?logo=node.js&logoColor=fff)](https://nodejs.org/)
[![Foundry Local](https://img.shields.io/badge/Foundry%20Local-On--Device%20AI-0078D4?logo=microsoft&logoColor=fff)](https://foundrylocal.ai)
[![Phi-3.5 Mini](https://img.shields.io/badge/Model-Phi--3.5%20Mini%20Instruct-6B21A8)](https://huggingface.co/microsoft/Phi-3.5-mini-instruct)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Offline](https://img.shields.io/badge/Connectivity-100%25%20Offline-brightgreen)]()

# Gas Field Local RAG – Offline Support Agent

A fully offline, on-device **Retrieval-Augmented Generation (RAG)** support agent for gas field inspection and maintenance engineers. Built with **[Foundry Local](https://foundrylocal.ai)** and **Phi-3.5 Mini Instruct**, this sample shows you how to build a production-style RAG application that runs entirely on your machine: no cloud, no API keys, no internet required.

![Landing Page – Desktop](screenshots/01-landing-page.png)

> **New to RAG?** Retrieval-Augmented Generation is a pattern where an AI model's answers are grounded in a specific set of documents. Instead of relying solely on what the model learned during training, RAG retrieves relevant chunks from your own documents and feeds them to the model as context. This dramatically reduces hallucination and makes the AI useful for domain-specific tasks.

## What You'll Learn

If you're a developer getting started with AI-powered applications, this project demonstrates:

1. **How RAG works end-to-end** – document ingestion, chunking, vector storage, retrieval, and generation
2. **Running AI models locally** with [Foundry Local](https://foundrylocal.ai) (no GPU required, works on CPU/NPU)
3. **Building a mobile-responsive web UI** that works in the field (large touch targets, high contrast, PWA-ready)
4. **Streaming AI responses** using Server-Sent Events (SSE)
5. **TF-IDF vector search** with SQLite: no external vector database needed

## Architecture

![Architecture Diagram](screenshots/07-architecture-diagram.png)

**How a query flows:**

![RAG Query Flow](screenshots/08-rag-flow-sequence.png)

1. The user types a question in the browser
2. The Express server receives it and searches the SQLite vector store for the most relevant document chunks
3. Those chunks are injected into the prompt as context
4. Foundry Local generates a response using Phi-3.5 Mini, grounded in the retrieved context
5. The response streams back to the browser via SSE

## Features

- **100% offline** – no internet, no cloud, no outbound calls
- **Safety-first prompting** – safety warnings surface before any procedure
- **RAG retrieval** – answers grounded in local gas engineering documents
- **Streaming responses** – real-time SSE streaming to the UI
- **Mobile responsive** – works on phones, tablets, and desktops in the field
- **Edge/compact mode** – toggle for extreme latency / constrained devices
- **Document upload** – add new `.md`/`.txt` documents from the UI at runtime
- **Field-ready UI** – high contrast, large touch targets, works with gloves/PPE

| Desktop | Mobile |
|---------|--------|
| ![Desktop view](screenshots/01-landing-page.png) | ![Mobile view](screenshots/02-mobile-view.png) |

## Prerequisites

Before you begin, make sure you have:

- **Node.js** ≥ 20: [Download here](https://nodejs.org/)
- **Foundry Local**: Microsoft's on-device AI runtime
  ```
  winget install Microsoft.FoundryLocal
  ```
- The **phi-3.5-mini** model (auto-downloaded on first run via the SDK, approximately 2 GB)

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/leestott/local-rag.git
cd local-rag

# 2. Install dependencies
npm install

# 3. Ingest the 20 gas engineering documents into the local vector store
npm run ingest

# 4. Start the server (starts Foundry Local automatically)
npm start
```

Open **http://127.0.0.1:3000** in a browser. You should see the landing page with quick-action buttons and the chat input.

### What Happens at Startup

1. **`npm run ingest`** reads every `.md` file in `docs/`, splits them into overlapping chunks, computes TF-IDF vectors, and stores everything in `data/rag.db` (SQLite).
2. **`npm start`** uses the Foundry Local SDK to discover and load the Phi-3.5 Mini model from the local catalog, opens the vector store, and starts the Express server on port 3000.

## Chatting with the Agent

Type a question or tap one of the quick-action buttons. The agent retrieves relevant document chunks and generates a safety-first response:

![Chat response with safety warnings and step-by-step guidance](screenshots/03-chat-response.png)

Every response includes expandable source references so you can verify which documents the answer came from:

![Sources panel showing retrieved documents and relevance scores](screenshots/04-sources-panel.png)

### Mobile Chat

The UI is fully responsive: the same interface works on mobile devices with appropriately sized touch targets:

![Mobile chat view](screenshots/06-mobile-chat.png)

## Uploading Documents

You can expand the knowledge base without restarting the server. Click the 📄 button to open the upload modal:

![Upload document modal with indexed document list](screenshots/05-upload-document.png)

Drag-and-drop or browse for `.md`/`.txt` files. They are chunked and indexed immediately.

### Via File System

1. Add `.md` files to the `docs/` folder (with optional YAML front-matter for title/category/id).
2. Run `npm run ingest` to re-index all documents.

### Document Format

```markdown
---
title: My Procedure Title
category: Inspection Procedures
id: DOC-CUSTOM-001
---

# My Procedure Title

## Safety Warning
- Important safety note here.

## Procedure
1. Step one.
2. Step two.
```

## Runtime Document Upload

Unlike a context-augmented generation approach where context is fixed at startup, this RAG app supports adding documents without restarting the server. Click the document upload button to open the upload modal:

![Upload document modal with indexed document list](screenshots/05-upload-document.png)

Drag-and-drop or browse for `.md`/`.txt` files. The server saves the file, parses optional YAML front-matter, chunks the content, vectorises it, and indexes it immediately in SQLite. The modal also lists indexed documents with their chunk counts so you can verify what is available to the agent.

## Project Structure

```
LOCAL-RAG/
├── docs/                     # 20 gas engineering RAG documents
│   ├── 01-gas-leak-detection.md
│   ├── 02-regulator-fault-low-pressure.md
│   ├── 03-emergency-shutdown.md
│   ├── ...
│   └── 20-no-gas-flow-decision-tree.md
├── public/
│   └── index.html            # Field engineer web UI (single-file, no build step)
├── src/
│   ├── chatEngine.js         # Foundry Local + RAG orchestration
│   ├── chunker.js            # Document chunking + TF-IDF vector computation
│   ├── config.js             # App configuration (model, paths, chunk sizes)
│   ├── ingest.js             # Batch document ingestion script
│   ├── prompts.js            # System prompts (full + compact/edge)
│   ├── server.js             # Express server + API endpoints
│   └── vectorStore.js        # SQLite-backed local vector store
├── screenshots/              # App screenshots
├── test/                     # Unit tests (Node.js test runner)
├── data/                     # Generated at runtime
│   └── rag.db                # SQLite vector database
├── package.json
└── README.md
```

## How the RAG Pipeline Works

Let us trace what happens when a user asks: **"How do I detect a gas leak?"**

![RAG query flow from browser to model and back](screenshots/08-rag-flow-sequence.png)

### 1. Documents are ingested and indexed

When you run `npm run ingest`, every `.md` file in the `docs/` folder is read, parsed with optional YAML front-matter for title, category, and ID, split into overlapping chunks of approximately 200 tokens, and stored in SQLite with TF-IDF vectors.

### 2. The model is loaded through the SDK

The Foundry Local SDK discovers the model in the local catalog and loads it into memory. If the model is not already cached, it downloads it first, with progress streamed to the browser through Server-Sent Events.

### 3. The user sends a question

The question arrives at the Express server. The chat engine converts it into a TF-IDF vector, uses an inverted index to find candidate chunks, and scores them with cosine similarity. The top 3 chunks are returned for prompt construction.

### 4. The prompt is constructed

The engine builds a messages array containing the system prompt, retrieved chunks as context, conversation history, and the user's question.

### 5. The model generates a grounded response

The prompt is sent to the locally loaded model through the Foundry Local SDK's native chat client. The response streams back token by token through Server-Sent Events to the browser. Source references with relevance scores are included so the user can inspect which chunks grounded the answer.

![Chat response with safety warnings and step-by-step guidance](screenshots/03-chat-response.png)

![Sources panel showing referenced chunks and relevance scores](screenshots/04-sources-panel.png)

## Key Code Walkthrough

### The Vector Store: TF-IDF + SQLite

The vector store persists document chunks in SQLite alongside their TF-IDF vectors. At query time, an inverted index finds chunks that share terms with the query, then cosine similarity ranks only those candidates:

```js
// src/vectorStore.js
search(query, topK = 5) {
  const queryTf = termFrequency(query);
  this._ensureCache(); // Build in-memory cache on first access

  // Use inverted index to find candidates sharing at least one term
  const candidateIndices = new Set();
  for (const term of queryTf.keys()) {
    const indices = this._invertedIndex.get(term);
    if (indices) {
      for (const idx of indices) candidateIndices.add(idx);
    }
  }

  // Score only candidates, not all rows
  const scored = [];
  for (const idx of candidateIndices) {
    const row = this._rowCache[idx];
    const score = cosineSimilarity(queryTf, row.tf);
    if (score > 0) scored.push({ ...row, score });
  }

  scored.sort((a, b) => b.score - a.score);
  return scored.slice(0, topK);
}
```

The inverted index, in-memory row cache, and prepared SQL statements keep retrieval fast for typical local query loads.

### Why TF-IDF Instead of Embeddings?

Most RAG tutorials use embedding models for retrieval. This project uses TF-IDF because:

- **Fully offline:** no embedding model needs to be downloaded or run.
- **Low latency:** vectorisation is simple maths over word frequencies.
- **Good enough for this corpus:** 20 domain-specific documents are small enough for keyword-weighted retrieval to work reliably.
- **Transparent:** vocabulary and weights can be inspected directly, unlike neural embeddings.

For larger collections, or when semantic similarity matters more than keyword overlap, you can swap in an embedding model. For this use case, TF-IDF keeps the stack simple and dependency-light.

### The System Prompt

For a safety-critical domain, the system prompt prioritises safety, prevents hallucinated procedures, and enforces structured responses:

```js
// src/prompts.js
export const SYSTEM_PROMPT = `You are a local, offline support agent
for gas field inspection and maintenance engineers.

Behaviour Rules:
- Always prioritise safety. If a procedure involves risk,
  explicitly call it out.
- Do not hallucinate procedures, measurements, or tolerances.
- If the answer is not in the provided context, say:
  "This information is not available in the local knowledge base."

Response Format:
- Summary (1-2 lines)
- Safety Warnings (if applicable)
- Step-by-step Guidance
- Reference (document name + section)`;
```

This pattern is transferable to other safety-critical domains such as medical devices, electrical work, aviation maintenance, or chemical handling.

## Chunking Strategy

The chunking approach is one of the most important design decisions in any RAG system: it directly affects retrieval accuracy, response quality, and performance. This project uses a **fixed-size sliding window with overlap**, and that choice is deliberate.

### How It Works

Documents are split into chunks of **~200 whitespace-delimited tokens** with a **25-token overlap** between consecutive chunks (configured in [`src/config.js`](src/config.js)). The core logic lives in [`src/chunker.js`](src/chunker.js):

1. YAML front-matter (title, category, id) is stripped and stored as metadata
2. The body text is tokenized by whitespace
3. A sliding window walks through the tokens, emitting one chunk per step
4. Each new window starts 25 tokens before the previous one ended, creating overlap
5. Documents shorter than 200 tokens are kept as a single chunk

### Why Fixed-Size Sliding Window?

| Design constraint | How fixed-size chunking helps |
|---|---|
| **Small local model (Phi-3.5 Mini)** | 200-token chunks keep retrieved context compact, leaving room in the model's context window for the system prompt, conversation, and generated output |
| **NPU/CPU execution** | No embedding model needed for chunking: just string operations. All compute budget stays with the LLM |
| **Zero dependencies** | No tokenizer library, no embedding runtime, no vector database. Chunking is pure JavaScript |
| **Predictable memory** | Every chunk is roughly the same size, so retrieval cost and context usage are consistent and predictable |

### Why Not Other Strategies?

| Alternative | Trade-off |
|---|---|
| **Sentence-based** | Chunk sizes vary unpredictably; some safety procedures are single long sentences that wouldn't split well |
| **Section-aware** (split on `##` headings) | Section lengths vary widely across the 20 docs: some would be too small (wasting retrieval slots), others too large for the model's context window |
| **Recursive** (LangChain-style) | Better boundary handling, but adds complexity and dependencies for marginal gain on short documents |
| **Semantic** (embedding-based topic detection) | Best retrieval quality, but requires a second model in memory alongside Phi-3.5 Mini: risky on constrained NPU/CPU hardware with 8–16 GB shared memory |

### Performance Benefits

**For the system:**
- **~1ms retrieval**: TF-cosine similarity over fixed-size chunks is near-instant, compared to ~100–500ms if an embedding model had to encode each query
- **Fast ingestion**: all 20 documents are chunked and indexed in under a second; no embedding computation required
- **Single model in memory**: no embedding model competing with the LLM for limited NPU/RAM resources
- **Minimal storage**: chunks stored as plain text in SQLite with lightweight TF-IDF vectors; no high-dimensional embedding arrays

**For the end user:**
- **Instant search results**: the retrieval step adds negligible latency, so the user only waits for the LLM to generate
- **Higher-quality generation**: compact 200-token chunks mean the model receives focused, relevant context rather than large noisy blocks
- **Consistent response times**: uniform chunk sizes mean retrieval and generation latency is predictable regardless of which documents are matched
- **Works on modest hardware**: the lightweight pipeline runs on laptops and field devices without a dedicated GPU

### When to Consider Switching

If you adapt this project for larger or more complex document sets, consider upgrading the chunking strategy:

- **Hundreds of long documents** → recursive or section-aware chunking to better respect document structure
- **Embedding-based retrieval** → semantic chunking becomes worthwhile when paired with vector similarity search
- **Mixed content types** (tables, code, prose) → format-aware chunking to keep logical units intact
- **Higher precision requirements** → sentence-level chunking to avoid partial-match noise

For the current use case: 20 short procedural guides on constrained local hardware: fixed-size sliding window delivers the best balance of simplicity, speed, and retrieval quality.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | Non-streaming chat completion |
| `POST` | `/api/chat/stream` | Streaming chat via SSE |
| `POST` | `/api/upload` | Upload a document to the knowledge base |
| `GET` | `/api/docs` | List indexed documents |
| `GET` | `/api/health` | Health check |

## RAG Document Categories

The 20 included documents cover:

| # | Category | Documents |
|---|----------|-----------|
| 1 | Safety & Compliance | Emergency shutdown, PPE, confined space, hot work permits |
| 2 | Inspection Procedures | Leak detection, pressure testing, valve inspection, pipeline integrity, pre-inspection checklist |
| 3 | Fault Diagnosis | Regulator faults, gas detector fault codes, no-gas-flow decision tree |
| 4 | Repair & Maintenance | Gasket replacement, cathodic protection, corrosion treatment, purging |
| 5 | Equipment Manuals | Compressor maintenance, sensor calibration, relief valve testing, meter installation |

## Edge / Compact Mode

Toggle **Edge Mode** in the UI header for constrained devices:

| Setting | Full Mode | Edge Mode |
|---------|-----------|-----------|
| System prompt | ~300 tokens | ~80 tokens |
| Max output tokens | 1024 | 512 |
| Retrieved chunks | 5 | 3 |

## Key Concepts for New Developers

### What is Foundry Local?

[Foundry Local](https://foundrylocal.ai) is Microsoft's on-device AI runtime. It lets you run small language models (SLMs) like Phi-3.5 Mini directly on your laptop or workstation, with no GPU required and no cloud dependency. The SDK manages model discovery, downloading, loading, and inference entirely programmatically.

```js
import { FoundryLocalManager } from "foundry-local-sdk";

// Create the manager and discover models via the catalog
const manager = FoundryLocalManager.create();
const model = manager.catalog.getModel("phi-3.5-mini");
await model.load();

// Create a chat client and start generating
const chatClient = model.createChatClient();
const response = await chatClient.completeChat([
  { role: "user", content: "How do I detect a gas leak?" }
]);
console.log(response.choices[0].message.content);
```

### What is TF-IDF?

TF-IDF (Term Frequency–Inverse Document Frequency) is a classic information retrieval technique. Each document chunk is converted into a numeric vector based on how important each word is within that chunk relative to all chunks. At query time, the user's question is vectorized the same way and compared against all stored vectors using cosine similarity.

This project uses TF-IDF instead of embedding models to keep everything lightweight and offline: no embedding API or large model needed for retrieval.

### Why SQLite for Vectors?

For small-to-medium document collections (hundreds to low thousands of chunks), SQLite is fast enough for brute-force cosine similarity search and adds zero infrastructure. No need for Pinecone, Qdrant, or Chroma: just a single `.db` file on disk.

## Building a Field-Ready UI

The front end is a single HTML file with inline CSS: no React, no bundler, and no build tooling. This keeps the project approachable for beginners and easy to run on constrained field machines.

Design decisions that matter for field use:

- **Dark, high-contrast theme:** improves readability in bright or inconsistent lighting.
- **Large touch targets:** buttons and controls are sized for operation with gloves or PPE.
- **Quick-action buttons:** common field questions are available with one tap and wrap on mobile.
- **Responsive layout:** the UI works from small phone screens through desktop monitors.
- **Streaming responses:** Server-Sent Events show tokens as they arrive instead of waiting for the full answer.
- **Runtime upload:** engineers can add `.md` or `.txt` field notes without restarting the server.

![Mobile chat experience optimised for field use](screenshots/06-mobile-chat.png)

## Testing

```bash
# Run all tests
npm test
```

Tests use the built-in Node.js test runner (no extra dependencies). They cover the chunker, vector store, config, and server endpoints.

## Scripts

| Script | Command | Description |
|--------|---------|-------------|
| Ingest | `npm run ingest` | Chunk and index all docs into SQLite |
| Start | `npm start` | Start the server (production) |
| Dev | `npm run dev` | Start with auto-restart on file changes |
| Test | `npm test` | Run unit tests |

## Adapting This for Your Own Domain

This sample is designed to be forked and adapted. Here is how to make it yours in four steps:

1. **Replace the documents**

Delete the gas engineering documents in `docs/` and add your own markdown files. The ingestion pipeline handles any markdown content with optional YAML front-matter:

```markdown
---
title: Troubleshooting Widget Errors
category: Support
id: KB-001
---

# Troubleshooting Widget Errors

...your content here...
```

2. **Edit the system prompt**

Open `src/prompts.js` and rewrite the system prompt for your domain. Keep the response structure, such as summary, safety or caveats, steps, and reference, then update the language to match your users' expectations.

3. **Tune the retrieval**

Open `src/config.js` and adjust:

- `chunkSize: 200`: smaller chunks give more precise retrieval but less context per chunk.
- `chunkOverlap: 25`: overlap prevents important information from falling between chunks.
- `topK: 3`: controls how many chunks are retrieved per query. More chunks give the model more context but can slow generation.

4. **Swap the model**

Change `config.model` in `src/config.js` to any model available in the Foundry Local catalog. Smaller models give faster responses on constrained devices; larger models can improve answer quality.

The UI can also be customised directly in `public/index.html`, since the front end is intentionally kept as a single-file app.

## License

MIT – This solution is a scenario sample for learning and experimentation.
