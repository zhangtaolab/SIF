---
phase: 260914-v5f
plan: 01
type: execute
subsystem: search
tags: [search, bm25, vector, hybrid, collection-filter, security, audit-blocker]
requires:
  - "Enabled-collections resolution in cli/commands/search.py + bench.py emitting [] for exclude-all"
provides:
  - "Sentinel contract on SearchOptions.collection_ids: None=unfiltered, []=exclude-all (zero results)"
  - "Exclude-all guard in BM25Searcher.search and VectorSearcher.search (audit BLOCKER 1 closed for CLI-04/CLI-05)"
  - "Regression suite tests/unit/search/test_collection_filter.py (3 exclude_all + 5 controls)"
affects:
  - "src/sif/search/hybrid.py (delegates same options object — inherits fix, no code change)"
  - "src/sif/cli/commands/bench.py (routes through SearchPipeline — inherits fix, no code change)"
tech-stack:
  added: []
  patterns:
    - "Sentinel-vs-truthiness guard: `is not None and not list` early-return before SQL construction"
key-files:
  created:
    - tests/unit/search/test_collection_filter.py
  modified:
    - src/sif/search/bm25.py
    - src/sif/search/vector.py
    - src/sif/core/models.py
decisions:
  - "Guard placed in the two SQL-building searchers (bm25/vector), not in HybridSearcher/SearchPipeline — delegating callers inherit the fix from one place"
  - "Empty list never reaches the placeholder builder: IN () is invalid SQLite syntax, so the guard also prevents a latent SQL error"
metrics:
  duration: 7min
  completed: "2026-09-14T14:40:34Z"
status: complete
commits: 2
plan_head_before: 90d4990
actuals:
  tokens: 2734
  tasks: 2
  commits: 2
---

# Quick Task 260914-v5f: Fix exclude-all collection leak (empty collection_ids) Summary

**One-liner:** Exclude-all collection state (`collection_ids=[]`) now returns zero results in BM25 and Vector searchers via an `is not None and not list` sentinel guard — closing v1.0 audit BLOCKER 1 (CLI-04/CLI-05), where excluding every collection returned ALL documents instead of none.

## What Was Built

**Problem (audit BLOCKER 1):** When a user excludes every collection (`include_by_default=0` on all), the CLI resolves enabled collections to `[]` and passes `SearchOptions(collection_ids=[])`. Both `BM25Searcher.search` (bm25.py:54) and `VectorSearcher.search` used the truthiness check `if options.collection_ids:`, treating `[]` as "no filter" — so exclude-all returned every indexed document. An explicit `-c` naming no existing collection hit the same leak. `HybridSearcher` and `SearchPipeline` delegate the same options object to both searchers, so the leak covered `search`, `vsearch`, `query`, and `bench` paths.

**Fix (GREEN, commit b7381d6):**
- `src/sif/search/bm25.py` — `search()` early-returns `[]` when `options.collection_ids is not None and not options.collection_ids`, after options normalization and before FTS query / collection-filter SQL construction. Comment documents the sentinel source (search.py ~163/329/468, bench.py ~105) and why `[]` must never reach the placeholder builder (`IN ()` is invalid SQLite syntax).
- `src/sif/search/vector.py` — identical guard in `search()` before delegating to `_search_with_vec`. The existing `*(options.collection_ids or [])` params line is unchanged and post-guard only converts None to `[]`.
- `src/sif/core/models.py` — sentinel contract documented on the `SearchOptions.collection_ids` field: None = no collection filter (unfiltered, incl. `--all`); [] = exclude-all, searchers return zero results.

**Regression tests (RED, commit b02f345):** `tests/unit/search/test_collection_filter.py` — module-level `_build_search_db(with_vec)` builder (real in-memory FTS5 external-content table with porter tokenizer + explicit `rebuild`, optional vec0 embeddings via `add_embeddings_batch`, contexts table for `attach_path_contexts`), shared by three test classes:
- `TestExcludeAllBM25.test_exclude_all_bm25_returns_nothing` — `collection_ids=[]` returns exactly `[]` (FAILED pre-fix: returned all 3 docs)
- `TestExcludeAllVector.test_exclude_all_vector_returns_nothing` — same on the vector path (FAILED pre-fix)
- `TestExcludeAllHybrid.test_exclude_all_hybrid_returns_nothing` — same through HybridSearcher with a mock embedder (FAILED pre-fix)
- Controls (passed pre- and post-fix): `collection_ids=None` returns all 3 docs on each of bm25/vector/hybrid; `collection_ids=["c1"]` returns only c1's 2 docs on bm25 and vector

**Untouched by design (plan directive):** `hybrid.py` (delegates the same options to both guarded searchers; empty results already short-circuit), `cli/commands/search.py`/`bench.py` (already emit `[]` for exclude-all, `None` for `--all`), `mcp/backend.py` (passes only None or non-empty matched lists — MCP behavior byte-identical; audit MCP-02 is a separate finding), `database/repository.py` (no callers), include_by_default semantics.

## Verification Results

- RED gate (pre-fix): `pytest tests/unit/search/test_collection_filter.py -k exclude_all` → 3 failed (leak reproduced); `-k "not exclude_all"` → 5 passed
- Post-fix: `tests/unit/search/test_collection_filter.py` → 8 passed
- Full suite: `pytest -q` single invocation → 675 passed, 0 failed; split run with `--ignore=tests/unit/embedding/test_openai_embedder.py` → 657 passed, and the ignored file in isolation → 18 passed. The 2 known caplog failures (WINDOWS.md #3/#4, order-dependent pollution) did NOT reproduce in this session — baseline is at least as good as expected (0 failures, unchanged failure count, no embedding code touched)
- `ruff check src tests` — clean; `ruff format --check src tests` — 132 files already formatted
- Searcher diff is exactly the two guards + comments + models.py field comment (21 insertions in src/, verified before commit); no other source files changed; no file deletions in either commit

## Deviations from Plan

None — plan executed exactly as written, with one fixture correction anticipated by the plan itself ("If a control fails, the fixture is wrong — fix the fixture, not the assertion"): the sqlite-vec build in this environment rejects NULL for the vec0 `chunk_id` TEXT metadata column (`Expected text for TEXT metadata column chunk_id, received NULL`), so fixture embeddings use string chunk ids (`ch1`/`ch2`/`ch3`) matching the `TestVectorFilteredRecall` convention, instead of the plan's `None` example values.

## Threat Mitigations

- **T-v5f-01 (Information Disclosure, high) — mitigated:** the sentinel guard is the planned mitigation; the RED tests locked it across bm25/vector/hybrid before the fix landed.
- **T-v5f-02 (MCP include_by_default, medium) — accepted as planned:** no MCP files touched; backend passes only None/non-empty so outcomes are identical pre/post fix. Remains tracked under audit finding MCP-02.

## Known Stubs

None.

## Self-Check: PASSED

- tests/unit/search/test_collection_filter.py — FOUND (committed b02f345)
- src/sif/search/bm25.py, src/sif/search/vector.py, src/sif/core/models.py — FOUND modified (committed b7381d6)
- Commits b02f345 and b7381d6 — FOUND in git log on main
