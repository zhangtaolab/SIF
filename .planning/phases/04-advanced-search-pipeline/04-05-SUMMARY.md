---
phase: 04-advanced-search-pipeline
plan: 05
type: execute
wave: 3
status: complete
completed_at: "2026-04-17"
---

# Plan 04-05 Summary: Test fixes + quality suite

## What Was Done

Fixed all remaining broken tests caused by structural changes in Plans 01-04 (dataclass SearchResult, new class names, new APIs) and implemented QueryExpansion. Verified the entire phase with the quality suite.

### Files Modified

- `tests/unit/search/test_bm25.py` — Completely rewritten. Replaced BM25SearchStrategy (doesn't exist) with BM25Searcher. Uses mock sqlite3 connections (MagicMock) instead of mock repositories. Tests cover FTS query execution, min_score filtering, collection IDs, pagination, content/highlights inclusion, and chunk search.
- `tests/unit/inference/test_reranker.py` — Fixed patch targets (now patches `llama_cpp.Llama` and `sentence_transformers.CrossEncoder` at module level). Added `sys.modules` mocks for optional dependencies. Uses dataclass SearchResult from `docsift.core.models`. Added factory tests for `create_reranker()`. Fixed StopIteration bug by providing `len(results) + 1` embeddings.
- `tests/unit/inference/test_query_expander.py` — Updated for `list[str]` return type from `expand()`. Added tests for intent prepending, batch deduplication, and embedding-based expansion.
- `tests/unit/search/test_benchmark.py` — Ruff auto-formatted.
- `tests/unit/cli/test_bench.py` — Ruff auto-formatted.
- `src/docsift/search/expansion.py` — Implemented QueryExpansion with synonym expansion and embedding-based expansion.
- `src/docsift/search/benchmark.py` — Ruff auto-formatted.
- `src/docsift/cli/commands/bench.py` — Ruff auto-formatted.

## Acceptance Criteria

- [x] `grep -n "BM25SearchStrategy" tests/unit/search/test_bm25.py` returns no matches
- [x] `grep -n "docsift.models.search" tests/unit/search/test_bm25.py` returns no matches
- [x] `grep -n "SearchContext" tests/unit/search/test_bm25.py` returns no matches
- [x] `pytest tests/unit/search/test_bm25.py -x` passes (12 tests)
- [x] `pytest tests/unit/inference/test_reranker.py -x` passes (21 tests)
- [x] `pytest tests/unit/inference/test_query_expander.py -x` passes (12 tests)
- [x] `pytest tests/unit/search/test_benchmark.py -x` passes (16 tests)
- [x] `pytest tests/unit/cli/test_bench.py -x` passes (4 tests)
- [x] Full phase 04 scoped suite: 83 passed in 0.71s

## Self-Check: PASSED

## Next Up

Phase verification and completion. Mark Phase 04 as done in STATE.md and ROADMAP.md.
