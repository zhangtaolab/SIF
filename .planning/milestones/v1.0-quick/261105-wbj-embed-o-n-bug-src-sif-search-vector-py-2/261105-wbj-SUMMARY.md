---
phase: 261105-wbj-embed-o-n-bug-src-sif-search-vector-py-2
plan: 01
subsystem: search
tags: [sqlite-vec, vec0, performance, embeddings, cli]

requires:
  - phase: 03-embedding-pipeline
    provides: embed_cmd completeness check with _needs_embedding and delete-before-insert idempotency (G-03-3)
provides:
  - VectorSearcher.get_all_embedded_chunk_ids batch read (one unfiltered SELECT, dict[doc_id, set[chunk_id]])
  - embed_cmd prefetches the batch map once per collection — O(N^2) per-document vec0 scans eliminated
  - O(N^2) regression guard in the skip/heal embed tests (batch called once, per-document never called)
affects: [10-raise-pytest-coverage-to-90, embed re-runs, vector search maintenance]

actuals:
  tokens: 2000
  tasks: 2
  commits: 4
plan_head_before: 28f677b7106bf28d471868a6a0f81595cdbf6a5f
plan_head_after: 16b7b25aedd2ef543b44fef85e0aad0cdb676601

tech-stack:
  added: []
  patterns:
    - "Batch-prefetch pattern for unindexed vec0 metadata reads: one unfiltered SELECT + Python grouping replaces per-document filtered scans"

key-files:
  created: []
  modified:
    - src/sif/search/vector.py
    - src/sif/cli/commands/index.py
    - tests/unit/search/test_vector.py
    - tests/unit/cli/test_index.py

key-decisions:
  - "Real-vec0 equivalence test inserts no NULL chunk_id row — sqlite-vec v0.1.9 rejects NULL for TEXT metadata columns on INSERT and UPDATE, so such rows cannot exist in a production table; NULL-skip contract for both lookup forms is pinned by the mock tests"
  - "Mock batch test resets mock_db.execute after construction so assert_called_once covers the method alone (the constructor's vec_version probe consumes one execute)"

patterns-established:
  - "Prefetch unindexed vec0 metadata once per collection before the transaction; judge each document against the in-memory map via .get(doc.id, set())"

requirements-completed: [QUICK-PERF-EMBED-PREFETCH]

coverage:
  - id: D1
    description: "VectorSearcher.get_all_embedded_chunk_ids — one unfiltered parameter-free SELECT grouped into dict[str, set[str]], NULL chunk_id rows skipped, per-document-equivalent on a real vec0 table"
    requirement: QUICK-PERF-EMBED-PREFETCH
    verification:
      - kind: unit
        ref: tests/unit/search/test_vector.py#TestVectorEmbeddingDeletion::test_get_all_embedded_chunk_ids_groups_and_skips_none
        status: pass
      - kind: unit
        ref: tests/unit/search/test_vector.py#TestVectorEmbeddingDeletion::test_get_all_embedded_chunk_ids_matches_per_document_lookup_on_real_vec0
        status: pass
    human_judgment: false
  - id: D2
    description: "embed_cmd prefetches the batch map once per collection (first statement of the per-collection try, before the transaction) and judges each document via .get(doc.id, set()); zero per-document completeness lookups remain; skip/heal/force semantics unchanged"
    requirement: QUICK-PERF-EMBED-PREFETCH
    verification:
      - kind: unit
        ref: tests/unit/cli/test_index.py#TestEmbedCommand::test_embed_cmd_default_skips_fully_embedded_document
        status: pass
      - kind: unit
        ref: tests/unit/cli/test_index.py#TestEmbedCommand::test_embed_cmd_default_heals_stale_embedding_state
        status: pass
      - kind: unit
        ref: tests/unit/cli/test_index.py#TestEmbedCommand::test_embed_cmd_force_reembeds_fully_embedded_document
        status: pass
    human_judgment: false

duration: 7min
completed: 2026-11-05
status: complete
---

# Quick Task 261105-wbj: Embed O(N^2) Completeness Check Fix Summary

**Batch-prefetched embed completeness check: one unfiltered vec0 metadata read per collection replaces ~40k per-document full scans (~10h -> ~2s of scan time), _needs_embedding semantics byte-unchanged**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-11-05T15:28:43Z
- **Completed:** 2026-11-05T15:36:54Z
- **Tasks:** 2 (both tdd, RED -> GREEN)
- **Files modified:** 4

## Accomplishments

- `VectorSearcher.get_all_embedded_chunk_ids()` — single unfiltered, parameter-free SELECT of `document_id, chunk_id`; row-by-row cursor iteration (no fetchall); `setdefault(...).add(...)` grouping; NULL chunk_id rows skipped with the same contract as the single-document lookup.
- `embed_cmd` now prefetches the map once per collection (first statement of the per-collection `try:`, before `with db.connection:` — so a read failure follows the existing failed-collection path and the snapshot precedes any write) and the loop computes `embedded = embedded_by_doc.get(doc.id, set())`. Grep gates at HEAD after switch: single-document literal 0 (baseline 1), batch literal 1 (baseline 0).
- O(N^2) regression guard: skip and heal tests assert `get_all_embedded_chunk_ids` called exactly once and `get_embedded_chunk_ids` never called — RED at HEAD, GREEN after the switch.
- Full quality suite green: ruff check clean, ruff format --check clean (133 files), `env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q` = 690 passed, 0 failed (baseline 676+; delta includes intervening commits since 261105-eev).

## Task Commits

TDD — each task has a RED (test) and GREEN (feat) commit:

1. **Task 1 RED: failing batch-method tests** - `2943755` (test)
2. **Task 1 GREEN: get_all_embedded_chunk_ids implementation** - `6ba83e1` (feat)
3. **Task 2 RED: O(N^2) regression assertions + batch stub swap** - `5a6e55b` (test)
4. **Task 2 GREEN: embed_cmd call-site switch** - `16b7b25` (feat)

## TDD Cycle Evidence

- **Task 1 RED:** both target tests failed with `AttributeError: 'VectorSearcher' object has no attribute 'get_all_embedded_chunk_ids'` — the planned missing-feature failure, on the planned assertions; no unrelated failures.
- **Task 1 GREEN:** 20 passed in tests/unit/search/test_vector.py (18 baseline + 2 new).
- **Task 2 RED:** skip test failed on its existing no-embed assertions (per-document path re-embeds the unconfigured-mock doc) and heal test failed precisely on `get_all_embedded_chunk_ids.assert_called_once()` (0 calls at HEAD); force test stayed green (8 passed / 2 failed).
- **Task 2 GREEN:** 10 passed in tests/unit/cli/test_index.py; both grep gates hold.
- **REFACTOR:** none needed — implementation is minimal and matches surrounding style.

## Files Created/Modified

- `src/sif/search/vector.py` - new `get_all_embedded_chunk_ids()` at end of class, directly after the single-document lookup
- `src/sif/cli/commands/index.py` - prefetch + `.get(doc.id, set())` lookup inside embed_cmd; method-name-free cost comment
- `tests/unit/search/test_vector.py` - mock test (one unfiltered SELECT, no WHERE, no params, NULL skipped) + real-vec0 equivalence test
- `tests/unit/cli/test_index.py` - `_make_embed_mocks` batch stub swap; regression assertions in skip/heal tests

## Decisions Made

- Real-vec0 test carries no NULL chunk_id row (see Deviation 1) — the extension makes such rows unrepresentable; mock tests pin the Python-side NULL contract for both forms.
- Mock batch test uses `mock_db.execute.reset_mock()` after construction so `assert_called_once()` is the method's own round trip (the constructor's `vec_version()` probe consumes one execute).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Real-vec0 test cannot insert a NULL chunk_id row**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Plan's test spec inserts `("e3", "d1", None, ...)` into a real vec0 table; sqlite-vec v0.1.9 raises `OperationalError: Expected text for TEXT metadata column chunk_id, received NULL` on INSERT and on UPDATE-to-NULL, so a NULL chunk_id row cannot exist in any production table on this version.
- **Fix:** Dropped the NULL row from the real-vec0 test data (3 insertable rows across d1/d2); kept the load-bearing equivalence assertion (`batch_result[doc] == get_embedded_chunk_ids(doc)` for every document) and added a comment in the test explaining why. NULL-skip remains fully covered by the batch mock test (iterates a `("d1", None)` row) and the existing single-lookup mock test (`(None,)` row).
- **Files modified:** tests/unit/search/test_vector.py
- **Verification:** `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/search/test_vector.py -q` = 20 passed.
- **Committed in:** 6ba83e1 (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug — plan fact unsatisfiable on installed extension)
**Impact on plan:** None on the fix itself or any truth gate; the NULL-skip truth is satisfied by the mock tests for both forms, real-vec0 equivalence proven on all insertable rows.

## Issues Encountered

None beyond Deviation 1.

## User Setup Required

None.

## Next Phase Readiness

- `sif index embed` on the reporter's ~40k-doc index should drop from ~10h to minutes (one ~1.9s metadata scan per collection). Optional user-run spot-check: `time sif index embed` — same documents must be skipped/embedded as before.

## Self-Check: PASSED

All 4 modified files present; all 4 task commits (2943755, 6ba83e1, 5a6e55b, 16b7b25) are ancestors of HEAD (16b7b25); `git rev-list --count 28f677b..HEAD` = 4, matching the `commits:` actual.

---
*Quick task: 261105-wbj*
*Completed: 2026-11-05*
