---
phase: 261112-qtk-fix-scoped-default-bm25-query-plan
plan: 01
subsystem: search
tags: [sqlite, fts5, bm25, query-plan, materialized-cte, regression-test]
requires: []
provides:
  - "Scoped BM25 statement using WITH matched AS MATERIALIZED so the FTS match is evaluated once for non-empty collection filters"
  - "Plan-shape regression test pinned to the exact executed SQL (MATERIALIZED present, no per-document ':=' FTS scan)"
  - "Score-equivalence regression test: scoped ids/scores exactly equal unfiltered results restricted to the scope"
affects: [search, cli-search, mcp-search, bench]
actuals:
  tokens: 2038
  tasks: 2
  commits: 2
  plan_head_before: 1e0eac56f991ffb79b18c1b5d101ecca57cf5d9e
  plan_head_after: 2c7efc6b3628c4c43567e264c3156565bbd0ae07
tech-stack:
  added: []
  patterns:
    - "MATERIALIZED CTE to pin FTS match evaluation before the collection join"
    - "Recording connection proxy so EXPLAIN runs against the exact statement the searcher executed"
key-files:
  created: []
  modified:
    - src/sif/search/bm25.py
    - tests/unit/search/test_collection_filter.py
key-decisions:
  - "Filtered branch only: the unfiltered SQL is kept byte-identical (materializing it would add a needless sort)"
  - "Collection predicate applied outside the CTE so the join consumes the matched rowid set"
  - "Regression test captures and EXPLAINs the recorded executed SQL with its own bound parameters, so the assertion cannot drift from the shipped statement"
metrics:
  duration: 9min
  completed: 2026-11-12
status: complete
---

# Quick Task 261112-qtk: Fix Scoped Default BM25 Query Plan Summary

**Scoped BM25 now materializes the FTS match once before joining collections, removing the per-document `:=M1` FTS scan while keeping the unfiltered SQL and every score value byte-identical.**

## Performance

- **Duration:** ~9 min
- **Started:** 2026-11-12T11:24:34Z (plan mtime)
- **Completed:** 2026-11-12T11:32:38Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `BM25Searcher.search` now branches: a non-empty `collection_ids` builds `WITH matched AS MATERIALIZED (SELECT rowid, rank FROM documents_fts WHERE documents_fts MATCH ?)` joined to `documents`/`collections` with `WHERE d.collection_id IN (...)` outside the CTE and `ORDER BY m.rank`; `collection_ids=None` keeps the original statement byte-for-byte.
- Plan shape re-established at HEAD before the fix and verified after: pre-fix filtered plan was `SEARCH c` -> `SEARCH d USING INDEX idx_documents_collection` -> `SCAN fts VIRTUAL TABLE INDEX 32:=M1`; post-fix plan is `MATERIALIZE matched` -> `SCAN documents_fts VIRTUAL TABLE INDEX 0:M1` then the join/filter, for both one-collection and multi-collection filters. Unfiltered plan stays `SCAN fts VIRTUAL TABLE INDEX 32:M1`.
- `_build_search_db` now creates `idx_documents_collection` (the real-schema planner input, `src/sif/database/schema.py:391`) and `TestBM25ScopedQueryPlan` pins the plan shape on the exact executed SQL plus exact score equivalence against unfiltered results keyed by document id.
- Verified the regression test genuinely fails pre-fix (old module from HEAD: `MATERIALIZED in SQL: False`, plan contains `:=M1`).
- Full merge gate green: `ruff check src tests`, `ruff format --check src tests`, and `env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q` -> **1595 passed, 1 skipped**, coverage **95.18%** (planner baseline 1591 + 4 new parametrized cases).

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace the collection-filtered FTS join with a MATERIALIZED match CTE** - `2457abc` (fix)
2. **Task 2: Add the multi-collection plan-shape and scoring regression tests** - `2c7efc6` (test)

**Plan metadata:** none — SUMMARY/PLAN/STATE/ROADMAP artifacts are committed by the batch orchestrator, not by this executor.

## Files Created/Modified

- `src/sif/search/bm25.py` - filtered branch builds the MATERIALIZED match CTE; unfiltered branch unchanged; params order and `1.0/(1.0+abs(rank))` scoring untouched.
- `tests/unit/search/test_collection_filter.py` - fixture gains `idx_documents_collection`; new `_RecordingConnection` proxy and `TestBM25ScopedQueryPlan` (plan shape + score equivalence, parametrized over `["c1"]` and `["c1", "c2"]`).

## Decisions Made

- Filtered branch only: the unfiltered (`--all`) statement and plan were already correct, so materializing it would only add a sort step.
- The collection predicate stays outside the CTE and the collection ids stay bound `?` placeholders; only static SQL text was added (T-qtk-01 mitigation held).
- Score equivalence is compared as dictionaries keyed by document id because FTS rank ties are not order-stable across plan shapes.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. `ruff format` adjusted line wrapping of the new test signatures only; no semantic change.

## User Setup Required

None - no external service configuration required.

## Threat Flags

None - no new security-relevant surface. The only new SQL text is static (CTE name, keywords, fixed column list); user query and collection ids remain bound parameters.

## Next Phase Readiness

The default scoped CLI paths (`sif search search` direct, `sif search query` via SearchPipeline -> HybridSearcher -> BM25Searcher) now execute the MATERIALIZED match CTE. Optional user-run confirmation on a large real index (item reports 72.7s -> 0.03s on 20k documents); the automated gate is plan shape, not timing.

---

## Self-Check: PASSED

- `src/sif/search/bm25.py` exists; `tests/unit/search/test_collection_filter.py` exists; SUMMARY.md written.
- Commit `2457abc` is an ancestor of HEAD; commit `2c7efc6` is an ancestor of HEAD.
- Commits measured from ledger: `1e0eac5..2c7efc6` = 2.
- Full suite: 1595 passed, 1 skipped; ruff check/format clean.
