---
phase: quick-261111-kn2
plan: 01
subsystem: testing
tags: [pytest, sqlite, resource-warning, deferred-items]
requires:
  - phase: 13-watch-everywhere-mcp-embedded-refresh-background-daemon
    provides: TestIdleCheckpoint watcher coverage and its deferred ResourceWarning record
  - phase: 16-bench-expansion-reranker-tuning
    provides: Deferred Search Models audit record
provides:
  - Deterministic test-owned SQLite connection cleanup after watcher shutdown
  - Parser-recognized resolutions for the Phase 13 and Phase 16 deferred records
affects: [phase-13, phase-16, milestone-audit]
actuals:
  tokens: 1486
  tasks: 2
  commits: 2
plan_head_before: be7ec6cf421876ec54395f292b21bfc57a02ec42
plan_head_after: c018a6837b5e75ac114898cb883ca25bfd3ef59f
tech-stack:
  added: []
  patterns:
    - Nested try/finally cleanup guarantees Database.close after watcher.stop, including failed stops
key-files:
  created: []
  modified:
    - tests/unit/indexing/test_watcher.py
    - .planning/phases/13-watch-everywhere-mcp-embedded-refresh-background-daemon/deferred-items.md
    - .planning/phases/16-bench-expansion-reranker-tuning/deferred-items.md
key-decisions:
  - Preserve watcher.stop as the first cleanup operation because the watcher shares the Database connection through _CheckpointSpy.
  - Close the Phase 16 record as stale using live import evidence rather than changing docs/api-reference.md.
patterns-established:
  - "Exception-safe test cleanup: nest watcher shutdown inside try/finally with connection closure in the inner finally."
requirements-completed:
  - PHASE13-DEFERRED-RESOURCEWARN
  - PHASE16-DEFERRED-SEARCH-MODELS
coverage:
  - id: D1
    description: All TestIdleCheckpoint tests retain and close their Database after watcher shutdown without promoted ResourceWarning or unraisable-warning failures.
    requirement: PHASE13-DEFERRED-RESOURCEWARN
    verification:
      - kind: unit
        ref: tests/unit/indexing/test_watcher.py::TestIdleCheckpoint with PYTHONTRACEMALLOC=5 and strict warning gates
        status: pass
      - kind: other
        ref: env -u FORCE_COLOR NO_COLOR=1 python -m pytest
        status: pass
    human_judgment: false
  - id: D2
    description: Phase 13 deferred ResourceWarning record has one exact resolved status and cleanup evidence.
    requirement: PHASE13-DEFERRED-RESOURCEWARN
    verification:
      - kind: other
        ref: Deferred-record parser-status assertion for both phase ledgers
        status: pass
    human_judgment: false
  - id: D3
    description: Phase 16 Search Models record is resolved as stale with successful isolated imports and no API-reference or model-source changes.
    requirement: PHASE16-DEFERRED-SEARCH-MODELS
    verification:
      - kind: other
        ref: Isolated imports of SearchOptions, SearchQuery, SearchResult, and SearchType from sif.models.search
        status: pass
      - kind: other
        ref: git diff --exit-code -- docs/api-reference.md src/sif/models/search.py
        status: pass
    human_judgment: false
duration: 5 min
completed: 2026-11-11
status: complete
---

# Quick Task 261111-kn2: Idle-Checkpoint Resource Cleanup Summary

**Closed all four idle-checkpoint test database leaks and resolved both affected deferred records without changing production behavior.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-11-11T07:04:32Z
- **Completed:** 2026-11-11T07:09:54Z
- **Tasks:** 2
- **Files modified:** 3
- **Commits:** 2

## Accomplishments

- Updated all four `TestIdleCheckpoint` tests to retain their `Database` and close it after watcher shutdown, including when `watcher.stop()` raises.
- Passed the strict targeted gate: 4 passed with `PYTHONTRACEMALLOC=5`, `ResourceWarning` errors, and pytest unraisable-warning errors enabled.
- Resolved the Phase 13 deferred record with cleanup evidence and the Phase 16 record as stale after successful isolated search-model imports.
- Passed the full quality suite: ruff, formatting, and 1504 tests passed with 1 skipped and 95.00% coverage.

## Task Commits

1. **Task 1: Close every idle-checkpoint test-owned Database deterministically** — `a6b92fc` (test)
2. **Task 2: Resolve the Phase 13 and stale Phase 16 deferred records** — `c018a68` (docs)

Plan metadata was intentionally not committed; the orchestrator owns the quick-task documentation and state commit.

## Files Created/Modified

- `tests/unit/indexing/test_watcher.py` — returns the existing `Database` from `_make` and uses nested `try/finally` cleanup in all four idle-checkpoint tests.
- `.planning/phases/13-watch-everywhere-mcp-embedded-refresh-background-daemon/deferred-items.md` — records exact resolved status and strict-gate evidence.
- `.planning/phases/16-bench-expansion-reranker-tuning/deferred-items.md` — replaces duplicate open statuses with one resolved status and documents the stale missing-module premise.

## Verification

- Targeted `TestIdleCheckpoint` strict warning gate: **PASS** — 4 passed.
- Task-scoped ruff check and format check: **PASS**.
- Deferred-record exact status/open-status assertions: **PASS**.
- Isolated `SearchOptions`, `SearchQuery`, `SearchResult`, and `SearchType` imports: **PASS**.
- `ruff check src tests`: **PASS**.
- `ruff format --check src tests`: **PASS** — 187 files already formatted.
- Full pytest suite: **PASS** — 1504 passed, 1 skipped; 95.00% coverage.
- `git diff --exit-code -- docs/api-reference.md src/sif`: **PASS** — no production source or excluded API-reference changes.
- Committed scope review: **PASS** — exactly the three planned files changed across two commits.

## Decisions Made

- Kept `watcher.stop(flush=False)` before `db.close()` because the watcher uses the same underlying connection through `_CheckpointSpy`.
- Treated the Phase 16 item as a stale audit premise only; no documentation rewrite or production-model edit was needed.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Both deferred records are machine-readably resolved, the test resource leaks are eliminated, and no production or documentation follow-up is required for this task.

## Self-Check: PASSED

- All three planned files and this SUMMARY exist.
- Commits `a6b92fc` and `c018a68` are ancestors of HEAD.
- SUMMARY frontmatter contains `status: complete`.
- Task-owned tracked files have no uncommitted changes; production source and `docs/api-reference.md` remain unchanged.
- Measured commit count from `plan_head_before` to HEAD is 2.
