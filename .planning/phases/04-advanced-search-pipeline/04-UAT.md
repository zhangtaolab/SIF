---
status: testing
phase: 04-advanced-search-pipeline
source: [04-VERIFICATION.md]
started: 2026-09-05T01:28:09Z
updated: 2026-09-05T03:47:00Z
---

## Current Test

number: 2
name: Real-model reranking quality (SC 1)
expected: |
  Configure `reranker_model_name` (GGUF cross-encoder or
  `cross-encoder/ms-marco-MiniLM-L-6-v2`), run `sif search query <terms>`
  with and without reranking, with `--explain`. Reranked order is more
  relevant; explain output shows `reranker_score` alongside
  `bm25_score`/`vector_score`/`rrf_score`.
awaiting: user response

## Tests

### 1. Snippet relevance on your real index (04-06 backstop truth)
expected: On your real personal index, run `sif search query <terms>` (no --full) and `sif search search <terms>`; read the rendered Snippet column across several queries. The snippet reads as the most relevant excerpt for its query.
result: issue
reported: "修复不达标的问题"
severity: major
evidence: "Scratch index (23 repo docs, 1003 chunks, Qwen3-Embedding-0.6B, reranker off). Hybrid 'RRF fusion ranking' top-1 snippet correct. But 'chunk overlap tokens' and 'sqlite-vec virtual table' snippets landed on markdown section starts (## Configuration Options, CREATE TABLE collections) instead of matched rows; BM25 ~1/3 rows rendered empty Snippet cells (FTS5 stems vs literal find); substring false positive (query 'table' matched 'notable' -> changelog lead shown)."

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
issues: 1
pending: 3
skipped: 0
blocked: 0

## Gaps

- gap_id: G-04-1
  truth: "The snippet reads as the most relevant excerpt for its query (the sentence window a human would pick), not an arbitrary lead paragraph."
  status: resolved
  reason: 'User reported: "修复不达标的问题" (accepting evidence: hybrid snippets land on markdown section starts instead of matched lines; BM25 ~1/3 rows empty Snippet cells; substring false positive notable/table)'
  severity: major
  test: 1
  root_cause: "Two independent causes. (1) SmartSnippetExtractor splits sentences only on .!? — markdown headings/lists/tables/code blocks become giant pseudo-sentences; term-count scoring selects the block and _build_window renders from its start (section header) instead of the matched line. (2) BM25Searcher._get_highlights gates chunks with literal `term in chunk_lower` and _extract_snippet uses str.find, while FTS5 matches stemmed tokens (ranking<->rank), so stem-mismatched docs get zero highlights -> empty Snippet cells; literal substring matching also false-positives inside words (table inside notable)."
  artifacts:
    - path: "src/sif/search/snippets.py"
      issue: "sentence splitting blind to markdown structure; window renders block start"
    - path: "src/sif/search/bm25.py"
      issue: "literal substring term matching in _get_highlights/_extract_snippet"
  missing:
    - "Markdown line-aware snippet extraction with matched-line centering in SmartSnippetExtractor"
    - "Stem-tolerant, word-boundary term matching shared by BM25 highlights (CJK via substring)"
  debug_session: ""
  resolved_by: "quick task 260905-hc3 (commits a4887de, 2d99c86, f85747a, 89a8a5e — src/sif/search/term_match.py new; snippets.py line-aware rewrite; bm25.py routed through shared matcher)"
  resolved_at: 2026-09-05
  verification: "Rerun on same scratch index: hybrid 'chunk overlap tokens' -> SIF_CHUNK_OVERLAP/DOCSIFT_CHUNK_OVERLAP rows; 'sqlite-vec virtual table' -> CREATE VIRTUAL TABLE ... vec0 sections; BM25 'RRF fusion ranking' 9/9 rows populated (was 6/9); changelog lead-paragraph notable/table false positive gone; CJK 向量搜索 3/3 rows populated (was 0/4). Suite: ruff clean, format clean, pytest 608 passed / 11 skipped / 0 failed."
