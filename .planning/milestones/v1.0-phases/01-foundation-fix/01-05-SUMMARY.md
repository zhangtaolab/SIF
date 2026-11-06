---
phase: 01-foundation-fix
plan: 05
subsystem: search
tags: [vector-search, sqlite-vec, fail-fast, cli]
dependency_graph:
  requires: [01-01, 01-04]
  provides: []
  affects: [src/docsift/search/vector.py, src/docsift/search/hybrid.py, src/docsift/cli/commands/search.py]
tech_stack:
  added: []
  patterns: []
key_files:
  created: []
  modified:
    - src/docsift/search/vector.py
    - src/docsift/search/hybrid.py
    - src/docsift/cli/commands/search.py
decisions: []
metrics:
  duration_minutes: ~15
  completed_date: "2026-04-15"
---

# Phase 01 Plan 05: Remove Vector Search Python Fallback Summary

**One-liner:** Made sqlite-vec a hard requirement for vector search, removed all Python brute-force fallbacks, and rewrote the vsearch CLI to fail fast with clear errors.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Remove fallback and make sqlite-vec mandatory in VectorSearcher | 46be2b7 |
| 2 | Remove vector error suppression from HybridSearcher | b251e6b |
| 3 | Make vsearch_cmd fail fast instead of falling back to BM25 | e9852a4 |

## Changes Made

### src/docsift/search/vector.py
- `__init__` now raises `RuntimeError` immediately if `sqlite-vec` is unavailable.
- Removed `_search_fallback`, `_cosine_similarity`, `_add_embedding_fallback`, and `_blob_to_embedding`.
- `search()` now directly returns `self._search_with_vec(query_embedding, options)`.
- `add_embedding()` now directly calls `self._add_embedding_vec(...)`.
- Cleaned up unused `struct` and `Tuple` imports.

### src/docsift/search/hybrid.py
- Removed the `try/except` block around vector search in `HybridSearcher.search()` so errors propagate instead of being silently ignored.
- Eliminated the "Warning: Vector search failed" fallback-to-BM25 behavior.

### src/docsift/cli/commands/search.py
- Rewrote `vsearch_cmd` to perform actual vector search using `SentenceTransformerEmbedder` and `VectorSearcher`.
- Added explicit `click.ClickException` handling for embedder loading failures (`ImportError` and general `Exception`).
- Removed the BM25 fallback path and the `ctx.invoke(search_cmd, ...)` call.

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- `pytest tests/test_docsift_complete.py -x` passes.
- `grep "RuntimeError" src/docsift/search/vector.py` succeeds.
- `! grep "Falling back to BM25 search" src/docsift/cli/commands/search.py` succeeds.
- `! grep "Warning: Vector search failed" src/docsift/search/hybrid.py` succeeds.

## Threat Flags

No new security-relevant surface introduced beyond what was already modeled in the plan's threat register.

## Self-Check: PASSED
