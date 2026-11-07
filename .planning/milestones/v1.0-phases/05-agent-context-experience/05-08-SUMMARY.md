---
phase: 05-agent-context-experience
plan: "08"
subsystem: search/context-attachment
tags: [search, context, path-normalization, gap-closure, testing]
requires:
  phase: 05
provides:
  - "normalize_path(path) — single canonical same-file definition in sif.utils.paths"
  - "attach_path_contexts(db, results) — shared path-context attachment helper (sif.search.context_attach)"
  - "Real-SQL regression suite proving symlink-alias context attachment end to end"
affects:
  - src/sif/search/bm25.py
  - src/sif/search/vector.py
  - src/sif/search/hybrid.py
tech-stack:
  added: []
  patterns:
    - "Normalize both sides in Python over one constant-SQL batch query; never pre-filter paths in SQL (realpath is not invertible)"
    - "Set-only-on-match attachment so upstream descriptions (RRF/rerank) are never clobbered"
key-files:
  created:
    - src/sif/search/context_attach.py
    - tests/unit/search/test_context_attach.py
  modified:
    - src/sif/utils/paths.py
    - src/sif/search/bm25.py
    - src/sif/search/vector.py
    - src/sif/search/hybrid.py
    - tests/unit/search/test_bm25.py
    - tests/unit/search/test_vector.py
    - tests/unit/search/test_hybrid.py
key-decisions:
  - "Read-side normalization replaces the raw-string SQL pre-filter: one batch query of all path contexts, both sides normalized in Python (D-06 batch shape preserved; realpath not invertible means no SQL pre-filter can ever be correct)"
  - "Legacy verbatim context rows match on read — no backfill migration of the contexts table (05-VERIFICATION missing item 2, re-normalize-on-read option)"
  - "context_description set ONLY on match, preserving RRF/rerank-carried descriptions (truths 14/16) and the existing MagicMock-DB tests"
  - "ORDER BY updated_at ascending gives deterministic newest-wins for duplicate-normalizing targets (CTX-02 ordering edge)"
  - "Hybrid's test-coupled MagicMock/tuple fallback deleted (REVIEW IN-03); production code no longer shaped by test doubles"
patterns-established:
  - "Real-symlink fixture pattern (tmp_path alias) for path-form-mismatch tests — portable across macOS/Linux, fails against any exact-match pre-filter"
requirements-completed:
  - CTX-03
coverage:
  - id: normalize-path-helper
    description: "normalize_path() in utils/paths.py reusing expand_path; ~ expansion, symlink resolution, missing-tail preservation"
    requirement: CTX-03
    verification:
      - kind: unit
        ref: "tests/unit/search/test_context_attach.py::TestAttachPathContextsRealSQL::test_normalize_path_edges"
        status: pass
    human_judgment: false
  - id: attach-path-contexts-helper
    description: "attach_path_contexts() — one constant-SQL batch query, normalize both sides, set-only-on-match"
    requirement: CTX-03
    verification:
      - kind: unit
        ref: "tests/unit/search/test_context_attach.py::TestAttachPathContextsRealSQL (8 tests, real sqlite3 :memory: + production DDL)"
        status: pass
    human_judgment: false
  - id: searcher-delegation
    description: "BM25/Vector/Hybrid _attach_contexts delegate to the shared helper; SearchPipeline call site unchanged; hybrid fallback gone"
    requirement: CTX-03
    verification:
      - kind: unit
        ref: "tests/unit/search/test_context_attach.py::test_vector_and_hybrid_delegate + test_bm25_searcher_method_on_real_db; tests/unit/search/ 161 passed"
        status: pass
    human_judgment: false
  - id: mock-test-replacement
    description: "Three mock-bypassed normalized-path tests deleted; coverage superseded by real-SQL suite"
    requirement: CTX-03
    verification:
      - kind: automated
        ref: "grep gates: test_search_attaches_context_with_normalized_path count 0 in test_bm25/test_vector, hybrid twin gone"
        status: pass
    human_judgment: false
  - id: live-symlink-attach
    description: "End-to-end: index under symlinked vault, context add with unresolved alias form, search --json shows non-null context_description"
    requirement: CTX-03
    verification:
      - kind: e2e
        ref: "Live CLI run (scratch SIF_DB_PATH): context stored '/tmp/.../alias/doc1.md', document '/private/tmp/.../vault/doc1.md' -> context_description: Live-falsification context note (pre-fix: null)"
        status: pass
    human_judgment: false
actuals:
  tokens: 5781
  tasks: 2
  commits: 3
plan_head_before: fbb7811542539148d7c40e26cdd13d4761ea40b0
duration: 17min
completed: 2026-09-07
status: complete
---

# Phase 05 Plan 08: Shared Context-Attach Helper Summary

Replaced the broken raw-string SQL pre-filter in context attachment with a shared `attach_path_contexts()` that normalizes both sides in Python over one constant-SQL batch query — closing 05-VERIFICATION's four failed truths (SC-3, 05-06 truths 11/12/13) and swapping the three mock-bypassed tests that blessed the bug for a real-SQL suite that would have caught it.

## Performance

- **Duration:** 17min (started 2026-09-07T03:32:47Z)
- **Tasks completed:** 2/2
- **Files:** 9 (2 created, 7 modified)
- **Test delta:** +8 real-SQL tests, -3 mock-bypassed tests; full suite 634 passed, 11 skipped, 0 failed (was 629)

## Accomplishments

- `normalize_path()` added to `src/sif/utils/paths.py`, reusing the existing `expand_path` — the single canonical "same file" definition for attach, `context add`, and prune, with strict=False semantics so not-yet-indexed targets still normalize.
- New `src/sif/search/context_attach.py`: `attach_path_contexts(db, results)` executes ONE query (`SELECT target_id, content FROM contexts WHERE context_type = 'path' ORDER BY updated_at` — constant string, zero interpolated values), normalizes both sides in Python, and sets `context_description` ONLY on match.
- All three searchers (`BM25Searcher`, `VectorSearcher`, `HybridSearcher`) now one-line delegates; hybrid's `hasattr(row, "keys")`/tuple MagicMock fallback (REVIEW IN-03) deleted; `SearchPipeline.search()` call site at hybrid.py unchanged; now-unused `import os` removed from all three.
- `tests/unit/search/test_context_attach.py`: 8-test suite against a real `sqlite3 :memory:` connection with the production `SchemaManager._create_contexts_table()` DDL and a REAL symlink fixture (tmp_path alias — portable, no hardcoded /private/tmp), covering the mismatch regression, mixed-batch None, preserve-on-miss, newest-updated_at-wins (newest inserted first so only ORDER BY can pass), BM25 method-level attach, vector/hybrid delegation wiring, normalize_path edges, and empty-results-no-query.
- The three mock-bypassed normalized-path tests deleted from test_bm25.py / test_vector.py (hybrid twin removed with the fallback — see Deviations).
- Live falsification now PASSES: context stored under `/tmp/.../alias/doc1.md`, document under `/private/tmp/.../vault/doc1.md`, `search search --json` returns the description (05-VERIFICATION reproduced `null` pre-fix).

## Task Commits

| Task | Commit | Type | Summary |
|------|--------|------|---------|
| 1 RED | 726f448 | test | Failing real-SQL regression tests (gate verdict RED_EVIDENCE_OK) |
| 1 GREEN | 73ef3e1 | feat | Shared normalize_path + attach_path_contexts; all three searchers delegate |
| 2 | 38a43c1 | test | Full 8-test real-SQL suite; mock-bypassed tests deleted |

TDD gate: Task 1 ran RED → GREEN → REFACTOR (no refactor commit — implementation already minimal, ruff-clean). Task 2 is the test-replacement task itself; its assertions were proven fail-first by Task 1's RED against the pre-fix searcher code.

## TDD Gate Compliance

- RED commit `test(05-08)` (726f448) precedes `feat(05-08)` (73ef3e1): verified via `git log`.
- RED evidence record at `.planning/tmp/tdd-red-evidence-05-08-task1.json`; `gsd-tools check tdd-red-evidence` verdict **RED_EVIDENCE_OK** (reason: target_test_failed) — 3 target assertion failures (`assert None == 'Project notes'` x2, `assert None == 'Reranked context'`) against real SQLite, not a collection/import error.
- The gate consumes TAP output; pytest emits none natively, so the record's output is a faithful mechanical transcription of the real `pytest -v` run (same test ids, statuses, and counts), noted inside the record.
- GREEN: 70 passed after implementation; REFACTOR: no change needed, tests stayed green.

## Files Created/Modified

**Created:** `src/sif/search/context_attach.py`, `tests/unit/search/test_context_attach.py`

**Modified:** `src/sif/utils/paths.py`, `src/sif/search/bm25.py`, `src/sif/search/vector.py`, `src/sif/search/hybrid.py`, `tests/unit/search/test_bm25.py`, `tests/unit/search/test_vector.py`, `tests/unit/search/test_hybrid.py`

## Decisions Made

- Read-side re-normalization over write-side backfill: existing verbatim context rows match on read with NO migration of the contexts table (05-VERIFICATION missing item 2's "re-normalize on read" option; write-side normalization is companion plan 05-09's scope).
- No SQL path pre-filter ever again — realpath is not invertible, so an IN-list built from resolved result paths can never contain a verbatim legacy row; full path-context scan is one batch query over a user-authored, personal-KB-scale table (threat register T-05-08-03 accepted).
- Query text is a constant string with zero interpolated values (T-05-08-04 mitigated — strictly safer than the previous placeholder-built IN-list).

## Deviations from Plan

**1. [Rule 3 - Blocking/ordering conflict] Hybrid tuple-row mock test deleted in Task 1's GREEN commit instead of Task 2**
- **Found during:** Task 1 GREEN verification
- **Issue:** Task 1 action 5 deletes hybrid's MagicMock/tuple fallback, but `test_hybrid_search_attaches_context_with_normalized_path` feeds plain tuple rows that ONLY worked via that fallback — it fails with `TypeError: tuple indices must be integers` the moment the fallback is removed. Task 1's done criteria ("existing searcher test files all pass unmodified") and verify gate conflict with deleting the fallback while the test exists.
- **Fix:** Applied the plan's own Task 2 action 5 instruction early — the test is deleted in the GREEN commit (73ef3e1), superseded immediately by the real-SQL coverage in test_context_attach.py.
- **Files modified:** tests/unit/search/test_hybrid.py
- **Verification:** 70 passed at GREEN; 161 passed for tests/unit/search/ at Task 2 close.
- **Commit:** 73ef3e1

**2. [Cosmetic - gate literal] Module docstring reworded to avoid the `target_id IN` substring**
- **Found during:** Task 1 acceptance criteria run
- **Issue:** The prohibition grep gate (`grep -c 'target_id IN' context_attach.py == 0`) counts prose too — the module docstring's description of the old broken pattern tripped it.
- **Fix:** Reworded to "a SQL membership clause on the raw target_id strings". No code change.
- **Commit:** included in 73ef3e1

**Total deviations:** 2 auto-fixed (1 ordering, 1 cosmetic). **Impact:** none on behavior or coverage; both resolved within the plan's own instructions.

## Issues Encountered

None. All plan verification steps passed: adjacent suites 182 passed/11 skipped (pre-existing env-skips documented in 05-VERIFICATION), ruff check + format clean, `context add --help` OK, full suite 634 passed/11 skipped/0 failed, live symlink falsification attaches the description.

## User Setup Required

None.

## Next Phase Readiness

- CTX-03 search-side gap closed; the write side (`context add` normalization, `delete_orphaned_paths` alignment — CR-02) is companion plan 05-09, whose artifacts this plan intentionally does not touch.
- Threat model dispositions: T-05-08-04 mitigated (constant SQL); T-05-08-01/02/03 accepted as analyzed.
- No stubs, no skipped tests introduced, no unrun verify steps.

## Self-Check: PASSED

- Created files exist: src/sif/search/context_attach.py, tests/unit/search/test_context_attach.py (FOUND)
- Task commits exist: 726f448, 73ef3e1, 38a43c1 (FOUND)
- commits measured from ledger fbb7811..HEAD = 3 (matches actuals.commits)
