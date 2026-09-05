---
status: testing
phase: 04-advanced-search-pipeline
source: [04-VERIFICATION.md]
started: 2026-09-05T01:28:09Z
updated: 2026-09-05T01:28:09Z
---

## Current Test

number: 1
name: Snippet relevance on your real index (04-06 backstop truth)
expected: |
  The snippet reads as the most relevant excerpt for its query (the sentence
  window a human would pick), not an arbitrary lead paragraph.
awaiting: user response

## Tests

### 1. Snippet relevance on your real index (04-06 backstop truth)
expected: On your real personal index, run `sif search query <terms>` (no --full) and `sif search search <terms>`; read the rendered Snippet column across several queries. The snippet reads as the most relevant excerpt for its query.
result: [pending]

### 2. Real-model reranking quality (SC 1)
expected: Configure `reranker_model_name` (GGUF cross-encoder or `cross-encoder/ms-marco-MiniLM-L-6-v2`), run `sif search query <terms>` with and without reranking, with `--explain`. Reranked order is more relevant; explain output shows `reranker_score` alongside `bm25_score`/`vector_score`/`rrf_score`.
result: [pending]

### 3. HyDE end-to-end with a generation-capable model (SC 2)
expected: Run `sif search query hyde: <question>` with a generation-capable GGUF embedder. A hypothetical document is generated, embedded, vector-searched; no RuntimeError; snippet populated.
result: [pending]

### 4. bench on a real corpus (SC 8)
expected: Author a fixture with real queries and judged relevant docids from your index; run `sif bench fixture.json` and `--json`. Table/JSON metrics (precision@k, recall, MRR) are consistent with your manual relevance judgments.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
