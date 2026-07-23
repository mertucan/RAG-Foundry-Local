---
title: Evaluation Metrics for Document Search
category: Evaluation
id: DOC-EV-001
course: Local AI Systems
topic: Evaluation
semester: Summer 2026
source_type: lecture-note
tags: evaluation, hit-rate, grounding
---

# Evaluation Metrics for Document Search

Evaluation checks whether the system retrieves useful sources and produces grounded answers. For small academic knowledge bases, a curated set of expected questions is often enough to validate the retrieval path.

## Retrieval Hit Rate

Retrieval hit rate measures whether at least one expected document appears in the top-k retrieved results for a question. For example, if six evaluation questions all retrieve the expected document, the hit rate is 100 percent.

## Source Relevance

Source relevance considers whether the retrieved chunk actually contains evidence for the answer. A high document-level hit rate is useful, but chunk-level relevance gives a more precise view.

## Answer Grounding

Answer grounding checks whether the final answer stays within the retrieved context. A grounded answer should not invent citations, deadlines, statistics, or requirements.
