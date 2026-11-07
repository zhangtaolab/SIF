---
phase: 11-live-index-foundation-concurrent-db-incremental-core
plan: 03
subsystem: database
tags: [dead-code-retirement, flock, index-lock, embed-cmd, d-07, published-api-break, sqlite]

requires:
  - phase: 11-01
    provides: shared connection factory, index_lock per-DB flock with D-02 wait-then-run, update_cmd under the lock, Settings.lock_wait_timeout
  - phase: 11-02
    provides: IncrementalIndexer — the single shared incremental core the dead DocumentIndexer is retired in favor of
provides:
  - D-07 complete — ConnectionPool, the duplicate legacy DatabaseConnection, and the dead DocumentIndexer module retired across source AND tests; sif.database.__all__ carries only the surviving nine names
  - D-01 complete — embed_cmd acquires the same per-DB flock around its collection loop (model load and dimension checks outside the lock), so update + embed arbitrate on one lock
  - Deterministic lock-acquisition proofs (spy + held-lock wait-then-proceed) and retired-name import assertions
  - SC4 — the phase's full quality gate is green (1030 passed @ 96.20%, ruff/format/ty clean)
affects: [12-watch, 13-daemon-mcp, 14-precommand]

actuals:
  tokens: 15862   # chars/4 over the realized 3c8b125..c0cfa00 diff (63449 chars)
  tasks: 2
  commits: 3      # MEASURED: git rev-list --count 3c8b125..HEAD

plan_head_before: 3c8b125a54059f66c8f572e74bd028aca83c3256
plan_head_after: c0cfa00c367d97a2517d1e0ab5b31c1a5f4b1a49

tech-stack:
  added: []   # deletions + stdlib locking only; zero new dependencies (locked)
  patterns:
    - "Retirement is executed src-first, test-cleanup-in-the-same-RED-commit: the suite never collects against deleted symbols"
    - "embed_cmd mirrors update_cmd's lock-wrap shape exactly (same on_wait wording) — one arbitration surface for Phases 12-14 hosts"

key-files:
  created:
    - tests/unit/cli/test_index_locking.py
  modified:
    - src/sif/cli/commands/index.py
    - src/sif/database/__init__.py
    - src/sif/database/connection.py
    - src/sif/database/database.py
    - src/sif/indexing/watcher.py
    - tests/unit/database/test_database.py
    - tests/unit/database/test_factory.py
    - tests/unit/db/test_database.py
  deleted:
    - src/sif/indexing/indexer.py
    - tests/unit/indexing/test_indexer.py

key-decisions:
  - "Dead-test cleanup landed inside the RED commit (not before it): the deleted test files import the symbols deleted in Task 1, so removing them in the same commit that adds the failing lock tests is what lets the suite collect at all — the RED target fails on its assertion, never on an import error"
  - "Commit-on-clean-exit for the surviving DatabaseConnection is now proven via transaction(); the retired duplicate's connect() was the only connect() that committed, so the two repointed tests moved their write paths to transaction() (D-07 consequence, not a behavior change in the surviving class)"
  - "The held-lock test pins get_settings to a Settings(lock_wait_timeout=0.2) instead of the SIF_LOCK_WAIT_TIMEOUT env var — the plan's 'or patches get_settings accordingly' option; deterministic and immune to env hermeticity issues"
  - "REFACTOR skipped: the lock-wrap boilerplate duplicated between update_cmd and embed_cmd mirrors 11-01's committed shape; extracting a helper would rework prior-plan code against D-05's 'change NOTHING else in embed_cmd's structure'"

patterns-established:
  - "Both long-running index writers (update, embed) must hold sif.database.locking.index_lock around their work — future write jobs (Phase 12-14 hosts) follow the same wrap"
  - "Retired-name regression locks: pytest.raises(ImportError) assertions in TestRetiredImports keep deleted public API deleted"

requirements-completed: [LIVE-06, LIVE-07]

coverage:
  - id: D1
    description: "D-07 retirement total: pool class, duplicate wrapper, dead orchestrator + their test suites gone; exports clean; watcher repointed to IncrementalIndexer"
    requirement: LIVE-07
    verification:
      - kind: unit
        ref: "tests/unit/database/test_factory.py#TestRetiredImports"
        status: pass
      - kind: automated
        ref: "task-1 <verify>: imports + sif.database.__all__ audit + ruff check src + ty check src/sif (all pass)"
        status: pass
    human_judgment: false
  - id: D2
    description: "embed_cmd acquires the per-DB flock exactly once per invocation around its collection loop, model loading outside the lock"
    requirement: LIVE-07
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_index_locking.py#TestLockAcquisitionSpy (update 1/1, embed 1/1)"
        status: pass
    human_judgment: false
  - id: D3
    description: "D-02 loser path under the lock: waiter prints the notice, waits out the 0.2s deadline, runs its own pass, exits 0 with work done"
    requirement: LIVE-07
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_index_locking.py#TestHeldLockProceeds"
        status: pass
    human_judgment: false
  - id: D4
    description: "Dead tests removed cleanly: pool fixture/class gone (db test method count 20 -> 14), duplicate-wrapper tests repointed to the surviving class and passing"
    verification:
      - kind: unit
        ref: "tests/unit/db/test_database.py (14 methods) + tests/unit/database/test_database.py — 35 passed across the task's four test files"
        status: pass
    human_judgment: false
  - id: D5
    description: "SC4 phase gate: full default suite incl. subprocess tests green at the coverage floor"
    verification:
      - kind: automated
        ref: "env -u FORCE_COLOR NO_COLOR=1 pytest -> 1030 passed @ 96.20% (fail_under=90) && ruff check src tests && ruff format --check src tests && ty check src/sif"
        status: pass
    human_judgment: false

duration: 9 min
completed: 2026-11-07
status: complete
---

# Phase 11 Plan 03: Dead-Code Retirement + embed_cmd Lock Summary

**Dead third copy of the indexing loop retired (DocumentIndexer module + ConnectionPool + duplicate DatabaseConnection, D-07) and embed_cmd brought under the same per-DB flock as update_cmd (D-01), closing the phase with the full quality gate green (SC4)**

## Performance

- **Duration:** 9 min (06:39–06:49 UTC)
- **Started:** 2026-11-07T06:39:51Z
- **Completed:** 2026-11-07T06:49:49Z
- **Tasks:** 2/2
- **Files modified:** 11 (1 created, 8 modified, 2 deleted)
- **Suite:** 1030 passed @ 96.20% (fail_under=90 honored); ruff, format, ty all green
- **Delta vs 11-02:** −22 tests (35-test dead DocumentIndexer suite + 6 pool tests removed, 6 regression locks added); coverage 96.34% → 96.20% because the deleted tests covered now-deleted source

## TDD Gate Compliance

Task 2 (`tdd="true"`) ran the task-scoped RED→GREEN cycle with machine-verified RED evidence (`gsd_run check tdd-red-evidence` → `RED_EVIDENCE_OK`; record in `.planning/tmp/tdd-red-11-03-task2.json`):

| Task | RED commit | RED failure (target test, planned reason) | GREEN commit |
|------|-----------|-------------------------------------------|--------------|
| 2 | `a87e657` test(11-03) | `test_embed_cmd_enters_index_lock_once`: `assert 0 == 1` — the recording spy saw zero lock entries (embed_cmd's collection loop ran without the flock); exit-code/output assertions passed, isolating the failure to the missing lock | `c0cfa00` feat(11-03) |

REFACTOR: skipped with rationale (see key-decisions) — no commit. Task 1 is a pure deletion task and not TDD-marked.

## Accomplishments

- **D-07 total:** `src/sif/indexing/indexer.py` deleted (DocumentIndexer + IndexStatus + IndexResult); the duplicate legacy `DatabaseConnection` deleted from `database.py`; `ConnectionPool` deleted from `connection.py`; `sif.database.__all__` now exactly `CollectionRepository, DatabaseConnection, DocumentChunkRepository, DocumentRepository, LLMCacheRepository, MigrationManager, PathContextRepository, create_connection, index_lock`; watcher.py TYPE_CHECKING + both string annotations repointed to `IncrementalIndexer` (ruff/ty clean)
- **D-01 completion:** embed_cmd wraps its collection loop in `index_lock(Path(index_path), settings.lock_wait_timeout, on_wait=...)` — acquired after the embedder load and the vec0 dimension check so the lock is never held across model loading; the on_wait notice matches update_cmd's wording; per-collection with-conn blocks keep their exact commit points (D-05)
- Dead tests retired with their code: the ~660-line DocumentIndexer suite deleted; `TestConnectionPool` + fixture removed (method count 20 → 14); the two duplicate-wrapper tests repointed to the surviving class with commit-on-clean-exit proven via `transaction()`
- New deterministic proofs: lock-acquisition spies (exactly one `index_lock` entry per invocation for BOTH commands — no timing races, the spy wraps the real context manager), the D-02 held-lock wait-then-proceed test (parent holds the flock; child waits out 0.2s, prints the notice, runs its own pass, exit 0), and `TestRetiredImports` import assertions
- **SC4:** full default suite (subprocess tests included) green at 96.20% with fail_under=90 honored

## Task Commits

1. **Task 1: retire dead connection code + dead indexer (D-07)** - `0d0767e` (refactor)
2. **Task 2 RED: failing embed_cmd lock spy + dead-test removal + retired-name assertions** - `a87e657` (test)
3. **Task 2 GREEN: embed_cmd under the per-DB lock (D-01)** - `c0cfa00` (feat)

**Plan metadata:** final docs commit (below)

## Files Created/Modified

- `src/sif/indexing/indexer.py` - DELETED: the dead document-indexer orchestrator, its status enum, and result dataclass
- `src/sif/indexing/watcher.py` - TYPE_CHECKING import and both constructor annotations reference `IncrementalIndexer` (the Plan-02 core)
- `src/sif/database/database.py` - duplicate legacy `DatabaseConnection` wrapper deleted; `Database` untouched
- `src/sif/database/connection.py` - `ConnectionPool` deleted; the surviving `DatabaseConnection` untouched
- `src/sif/database/__init__.py` - final export surface (nine surviving names, alphabetical)
- `src/sif/cli/commands/index.py` - embed_cmd's collection loop under `index_lock` (+103/−84, the re-indentation); nothing else changed
- `tests/unit/cli/test_index_locking.py` - NEW: spy + held-lock proofs (D-01/D-02)
- `tests/unit/indexing/test_indexer.py` - DELETED: the dead orchestrator's test suite
- `tests/unit/db/test_database.py` - pool fixture + `TestConnectionPool` removed (20 → 14 test methods)
- `tests/unit/database/test_database.py` - imports repointed to the surviving classes; the two lightweight tests use `transaction()`
- `tests/unit/database/test_factory.py` - extended with `TestRetiredImports` (D-07 row of the validation map)

## Decisions Made

- See key-decisions in frontmatter (RED-commit-carries-cleanup ordering, transaction()-based commit proof, patched-settings held-lock test, REFACTOR skip rationale).

## Deviations from Plan

### Auto-fixed Issues

**1. [Plan-spec adjustment] Stale line anchors from 11-01's interim changes**
- **Found during:** Task 1 (read_first)
- **Issue:** The plan cites the duplicate wrapper at database.py:108-143 and the pool at connection.py:105-143 — 11-01's factory routing moved both classes up (actual: 85-112 and 94-133). Similarly "embed_cmd lines 240-420" and the test-file line anchors had drifted.
- **Fix:** Located every target by its class/content rather than line number ("the duplicate wrapper class at the bottom of database.py", etc.); blast-radius grep re-verified before committing (zero deleted-symbol references left in src/). Two lines inside embed_cmd's loop re-wrapped for the 100-char limit after the lock indentation (the `zip(...)` and `coll.chunk_count = sum(...)` lines — formatting only, logic identical).
- **Files modified:** none beyond the planned set
- **Verification:** Task 1 verify green; ruff/ty clean on the re-wrapped lines
- **Committed in:** 0d0767e / c0cfa00

---

**Total deviations:** 1 auto-fixed (1 plan-spec adjustment)
**Impact on plan:** None — anchors were informational; every action matched the plan's named targets.

## Issues Encountered

- `ty` is not installed in `.venv/bin` (it lives on PATH at the user level) — invoke as `ty check src/sif` rather than `.venv/bin/ty`; result identical (0 diagnostics).
- PLC0415 is not enabled in the tests ruff scope, so the import assertions carry only `# noqa: F401` (RUF100 flagged the extra code).
- Single-file `pytest` runs trip the project-wide coverage addopts — partial suites ran with the project-standard `--no-cov`; the full-suite gate ran on plain `pytest` (96.20%).

## Authentication Gates

None — no external services in this plan.

## User Setup Required

None - no external service configuration required.

## Release-Notes-Worthy Behavior Change (per plan `<verification>`)

- **Published package API break (D-07, acknowledged):** `sif.database.ConnectionPool` and the duplicate `sif.database.database.DatabaseConnection` are gone; external importers of those two re-exported names must switch to `sif.database.connection.DatabaseConnection` / `create_connection`.
- User DBs auto-convert to WAL on first open with the Phase-11 factory (`-wal`/`-shm` sidecars appear while connections are open and vanish on last close), and `<db>.lock` files (0600) appear next to databases during index writes.

## Next Phase Readiness

- Phase 11 is complete (3/3 plans): concurrent DB foundation (11-01), the single incremental core (11-02), and total dead-code retirement + full lock coverage (11-03). Ready for `/gsd-verify-work 11` and then Phase 12 (watch hosts), which reuse `IncrementalIndexer(conn).update_collection(...)` and arbitrate through the same `index_lock`.
- Watcher's remaining stubs (`IndexingEventHandler` callbacks log but do not index) are Phase 12 wiring, deliberately untouched here.

## Self-Check: PASSED

All key files exist on disk (test_index_locking.py created; the deleted files confirmed gone in the Task 1/2 verifies); all 3 task commits (0d0767e, a87e657, c0cfa00) are ancestors of HEAD; `plan_head_before=3c8b125`, commits measured = 3; SC4 gate re-run green (1030 passed @ 96.20%, ruff/format/ty clean).

---
*Phase: 11-live-index-foundation-concurrent-db-incremental-core*
*Completed: 2026-11-07*
