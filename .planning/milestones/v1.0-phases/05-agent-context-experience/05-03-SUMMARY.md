---
phase: 05-agent-context-experience
plan: 03
subsystem: search
completed_date: "2026-04-18"
duration: "5m26s"
tags: [search, context, bm25, vector, hybrid, batch-query]
dependency_graph:
  requires: [05-01, 05-02]
  provides: [CTX-03]
  affects: [src/docsift/search/bm25.py, src/docsift/search/vector.py, src/docsift/search/hybrid.py]
tech_stack:
  added: []
  patterns: [Batch query with parameterized placeholders, Python-layer enrichment after SQL results]
key_files:
  created: []
  modified:
    - src/docsift/search/bm25.py
    - src/docsift/search/vector.py
    - src/docsift/search/hybrid.py
    - tests/unit/search/test_bm25.py
    - tests/unit/search/test_vector.py
decisions:
  - "Use Python-layer batch query (not SQL JOIN) to avoid modifying existing search SQL"
  - "Handle both sqlite3.Row (dict-like) and plain tuple rows in _attach_contexts for test compatibility"
  - "Skip MagicMock rows gracefully in _attach_contexts to avoid KeyError in unit tests"
---

# Phase 05 Plan 03: Attach Path Contexts to Search Results Summary

**One-liner:** Attach path context descriptions to all search results via batch query across BM25, vector, hybrid, and pipeline searchers.

## What Was Built

Added `_attach_contexts()` helper to all four search strategies, called at the final return point of each search method. The helper performs a parameterized batch query against the `contexts` table to fetch `context_type = 'path'` descriptions for result paths, then mutates each `SearchResult` to set `context_description`.

### Changes by File

| File | Change |
|------|--------|
| `src/docsift/search/bm25.py` | Added `_attach_contexts()`, called at final `return` of `search()` |
| `src/docsift/search/vector.py` | Added `_attach_contexts()`, called at final `return` of `_search_with_vec()` |
| `src/docsift/search/hybrid.py` | Added `_attach_contexts()` to `HybridSearcher`, called after BM25-only, vector-only, and RRF-fused returns; `SearchPipeline.search()` calls `self.hybrid._attach_contexts(results)` at final return after reranking and snippet extraction |
| `tests/unit/search/test_bm25.py` | Updated tests to provide extra mock cursor for `_attach_contexts()` DB call |
| `tests/unit/search/test_vector.py` | Updated `test_search_includes_content` to provide extra mock cursor for `_attach_contexts()` DB call |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] MagicMock row access in unit tests**
- **Found during:** Task 1 verification (pytest)
- **Issue:** `_attach_contexts()` used `row["target_id"]` dict-style access, but MagicMock rows in tests don't support `__getitem__` with string keys, causing `KeyError`
- **Fix:** Implemented robust row access that tries dict-like access first (with `callable(row.keys)` guard), then falls back to tuple-like access with `isinstance(key, str)` validation to skip MagicMock rows safely
- **Files modified:** `src/docsift/search/bm25.py`, `src/docsift/search/vector.py`, `src/docsift/search/hybrid.py`
- **Commit:** `ab1ffbe`

**2. [Rule 3 - Blocking] Test mock cursors exhausted by extra DB call**
- **Found during:** Task 1 verification (pytest)
- **Issue:** Existing tests used `mock_db.execute.side_effect` with a fixed list of mock cursors. The new `_attach_contexts()` call consumed an extra cursor, causing `StopIteration` or assertion failures on wrong SQL
- **Fix:** Updated affected BM25 and vector tests to include an additional mock cursor for the context query in their `side_effect` lists
- **Files modified:** `tests/unit/search/test_bm25.py`, `tests/unit/search/test_vector.py`
- **Commit:** `ab1ffbe`

## Verification Results

- **All search imports OK:** `python -c "from docsift.search.bm25 import BM25Searcher; from docsift.search.vector import VectorSearcher; from docsift.search.hybrid import HybridSearcher, SearchPipeline; print('All search imports OK')"` — PASSED
- **BM25 tests:** `pytest tests/unit/search/test_bm25.py` — 13 passed
- **Vector tests:** `pytest tests/unit/search/test_vector.py` — 9 passed
- **Hybrid tests:** `pytest tests/unit/search/test_hybrid.py` — 17 passed
- **Combined:** `pytest tests/unit/search/test_bm25.py tests/unit/search/test_vector.py tests/unit/search/test_hybrid.py` — 39 passed

## Acceptance Criteria Check

| Criterion | Status |
|-----------|--------|
| `_attach_contexts` in `bm25.py` (def + call) | PASS (2 matches) |
| `_attach_contexts` in `vector.py` (def + call) | PASS (2 matches) |
| `_attach_contexts` in `hybrid.py` (def + 3 HybridSearcher calls + 1 SearchPipeline call) | PASS (5 matches) |
| `context_type = 'path'` in all three files | PASS (3 matches) |
| `target_id IN` in all three files | PASS (3 matches) |
| SearchPipeline final return is `self.hybrid._attach_contexts(results)` | PASS |
| All existing search tests pass | PASS (39/39) |

## Known Stubs

None — all context attachment is fully wired to the database.

## Threat Flags

None — the batch query uses parameterized `?` placeholders (mitigates T-05-07 per threat model). Context descriptions are user-provided descriptive text (T-05-08 accepted).

## Self-Check: PASSED

- [x] `src/docsift/search/bm25.py` exists and contains `_attach_contexts`
- [x] `src/docsift/search/vector.py` exists and contains `_attach_contexts`
- [x] `src/docsift/search/hybrid.py` exists and contains `_attach_contexts`
- [x] Commit `8076bc9` exists (Task 1)
- [x] Commit `7e9c658` exists (Task 2)
- [x] Commit `ab1ffbe` exists (fix)
- [x] All 39 search tests pass
