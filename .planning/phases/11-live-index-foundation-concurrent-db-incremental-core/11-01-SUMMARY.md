---
phase: 11-live-index-foundation-concurrent-db-incremental-core
plan: 01
subsystem: database
tags: [sqlite, wal, busy-timeout, begin-immediate, flock, concurrency, connection-factory]

requires:
  - phase: 10.1
    provides: CLI Database lifecycle (with Database(...) as db held for the whole command body)
provides:
  - create_connection(db_path) shared factory with locked pragma recipe (busy_timeout=5000 first, bounded-retry WAL switch, synchronous=NORMAL, isolation_level=IMMEDIATE, sqlite-vec swallow+lazy-detect)
  - index_lock(db_path, timeout_s, on_wait) kernel-flock per-DB single-writer arbitration with D-02 wait-then-run expiry
  - Settings.lock_wait_timeout (env SIF_LOCK_WAIT_TIMEOUT, default 30.0)
  - sif.database exports create_connection + index_lock
  - update_cmd writes under the flock with a dim waiting notice; winner and loser both exit 0
affects: [11-02, 11-03, 12-watch, 13-daemon-mcp, 14-precommand]

actuals:
  tokens: 11794   # chars/4 over the realized 4f5c830..b7c386d diff (47174 chars)
  tasks: 3
  commits: 6      # MEASURED: git rev-list --count 4f5c830..HEAD

plan_head_before: 4f5c8300d888ad44438f0bff7596d40d4efaba1a
plan_head_after: b7c386d246697d8807ab080fde8a0595c5fd66e2

tech-stack:
  added: []   # stdlib only (sqlite3, fcntl) per the zero-new-deps lock
  patterns:
    - "ONE shared connection factory — no connection site can forget the pragma recipe (D-06)"
    - "isolation_level=IMMEDIATE at connect time: every existing with-conn block becomes BEGIN IMMEDIATE with identical commit/rollback semantics"
    - "Bounded for-else retry around only the WAL switch (the one pragma whose lock upgrade ignores busy_timeout)"
    - "Kernel flock per-DB lock file (0600) with deadline; expiry proceeds with the loser's own pass (D-02)"

key-files:
  created:
    - src/sif/database/factory.py
    - src/sif/database/locking.py
    - tests/unit/database/test_factory.py
    - tests/unit/database/test_locking.py
    - tests/integration/test_concurrency.py
    - tests/integration/test_two_writer_subprocess.py
  modified:
    - src/sif/database/database.py
    - src/sif/database/connection.py
    - src/sif/database/__init__.py
    - src/sif/config/settings.py
    - src/sif/cli/commands/index.py
    - tests/unit/database/test_database.py
    - tests/unit/cli/test_collection.py

key-decisions:
  - "Legacy duplicate DatabaseConnection (database.py) routed through the factory ahead of its 11-03 retirement — the plan's delete-the-sqlite_vec-import instruction would otherwise break ruff F821 and two patch-target tests"
  - "index_lock deadline expiry breaks to the yield instead of returning — a pre-yield return from a @contextmanager raises RuntimeError('generator didn't yield') and crashes the D-02 loser path"
  - "WAL retry uses a for-else with an unguarded final attempt: persistent contention surfaces the original OperationalError; a non-wal returned row degrades with a warning (network FS)"
  - "Busy-timeout wait test implemented deterministically (holder commits at 0.3s, waiter at the factory's 5000ms waits and succeeds, elapsed >= 0.2s) — the plan's busy_timeout=200 numbers could not simultaneously wait >= 0.2s and succeed"
  - "index_lock canonicalizes db_path (expanduser().resolve) like Database so equivalent path spellings share exactly one lock file per DB"

patterns-established:
  - "Connection creation goes through sif.database.factory.create_connection — new connection sites must not call sqlite3.connect directly"
  - "Long-running index writes wrap their work in sif.database.locking.index_lock with a user-facing on_wait notice"

requirements-completed: [LIVE-06, LIVE-07]

coverage:
  - id: D1
    description: "Shared connection factory: every connection carries busy_timeout=5000, WAL, synchronous=NORMAL, foreign_keys, implicit BEGIN IMMEDIATE"
    requirement: LIVE-06
    verification:
      - kind: unit
        ref: "tests/unit/database/test_factory.py#test_pragma_audit_on_every_connection"
        status: pass
      - kind: unit
        ref: "tests/unit/database/test_factory.py#test_wal_mode_persists_across_connections"
        status: pass
      - kind: unit
        ref: "tests/unit/database/test_factory.py#test_wal_switch_retry_absorbs_first_open_contention"
        status: pass
      - kind: unit
        ref: "tests/unit/database/test_factory.py#test_non_wal_result_degrades_with_warning"
        status: pass
      - kind: unit
        ref: "tests/unit/database/test_factory.py#test_wal_switch_exhaustion_raises_original_error"
        status: pass
      - kind: unit
        ref: "tests/unit/database/test_factory.py#test_sqlite_vec_load_failure_is_swallowed"
        status: pass
    human_judgment: false
  - id: D2
    description: "flock single-writer arbitration semantics: contention blocks, wait-then-run, expiry proceeds with own pass, holder death releases, 0600 lock file"
    requirement: LIVE-07
    verification:
      - kind: unit
        ref: "tests/unit/database/test_locking.py#TestIndexLock"
        status: pass
    human_judgment: false
  - id: D3
    description: "Two-writer end-to-end: second sif index update waits for a held lock then completes exit 0; two sequential updates leave 3 unique document rows; WAL persists"
    requirement: LIVE-07
    verification:
      - kind: integration
        ref: "tests/integration/test_two_writer_subprocess.py#TestSecondWriterWaitsThenRuns"
        status: pass
      - kind: integration
        ref: "tests/integration/test_two_writer_subprocess.py#TestTwoUpdatesNoDuplicates"
        status: pass
      - kind: integration
        ref: "tests/integration/test_two_writer_subprocess.py#TestWalModePersistsAfterUpdate"
        status: pass
    human_judgment: false
  - id: D4
    description: "MCP path (DatabaseConnection) inherits the full factory recipe via _create_connection delegation; package exports create_connection + index_lock"
    requirement: LIVE-06
    verification:
      - kind: unit
        ref: "tests/unit/database/test_factory.py#test_mcp_style_connection_inherits_factory_pragmas"
        status: pass
      - kind: unit
        ref: "tests/unit/database/test_factory.py#test_database_package_exports_factory_and_lock"
        status: pass
      - kind: unit
        ref: "tests/unit/mcp/test_backend.py (unmodified, passing)"
        status: pass
    human_judgment: false
  - id: D5
    description: "SC1 in-suite: CLI-style and MCP-style readers query during an open BEGIN IMMEDIATE write txn with zero lock errors; second writer busy-waits; threaded interleave clean"
    requirement: LIVE-06
    verification:
      - kind: integration
        ref: "tests/integration/test_concurrency.py#TestReaderDuringWriter"
        status: pass
      - kind: integration
        ref: "tests/integration/test_concurrency.py#TestBusyTimeoutWait"
        status: pass
      - kind: integration
        ref: "tests/integration/test_concurrency.py#TestThreadedInterleave"
        status: pass
    human_judgment: false
  - id: D6
    description: "Settings.lock_wait_timeout field (env SIF_LOCK_WAIT_TIMEOUT, default 30.0) consumed by update_cmd's lock wait"
    verification: []
    human_judgment: true
    rationale: "Env-var wiring relies on the existing pydantic SIF_ env_prefix (no dedicated test asserts SIF_LOCK_WAIT_TIMEOUT parsing); the default path is exercised end-to-end by the subprocess tests."

duration: 27 min
completed: 2026-11-07
status: complete
---

# Phase 11 Plan 01: Concurrent DB Foundation Summary

**One shared SQLite connection factory (busy_timeout→WAL→synchronous + implicit BEGIN IMMEDIATE) for both CLI and MCP paths, plus kernel-flock per-DB single-writer arbitration proven end-to-end with deterministic two-writer subprocess tests**

## Performance

- **Duration:** 27 min (05:44–06:11 UTC)
- **Started:** 2026-11-07T05:44:15Z
- **Completed:** 2026-11-07T06:11:44Z
- **Tasks:** 3/3
- **Files modified:** 13 (6 created, 7 modified)
- **Suite:** 1041 passed @ 96.30% (fail_under=90 honored); ruff, format, ty all green

## TDD Gate Compliance

Both `tdd="true"` tasks ran the full task-scoped RED→GREEN cycle with machine-verified RED evidence (`gsd_run check tdd-red-evidence` → `RED_EVIDENCE_OK` both times; records in `.planning/tmp/tdd-red-11-01-task{2,3}.json`):

| Task | RED commit | RED failure (target test, planned reason) | GREEN commit |
|------|-----------|-------------------------------------------|--------------|
| 2 | `ff033fb` test(11-01) | MCP-path pragma test: `assert 'delete' == 'wal'` (no delegation yet); exports test: ImportError from sif.database | `f6587d5` feat(11-01) |
| 3 | `464f711` test(11-01) | expiry test: `RuntimeError: generator didn't yield` — real D-02 bug in the Task 1 tracer code | `7b27635` fix(11-01) |

Task 3's RED caught a genuine production bug: the committed `index_lock` returned from the `@contextmanager` generator on deadline expiry before yielding, which would crash any 30s+ lock waiter with `RuntimeError` instead of running its own pass. Task 2's REFACTOR step made no changes (the delegation is already minimal).

## Accomplishments

- `create_connection()` factory (D-06): locked pragma order (busy_timeout=5000 FIRST, bounded-retry WAL switch with non-wal degrade, synchronous=NORMAL), `isolation_level="IMMEDIATE"` so every existing `with conn:` block is now BEGIN IMMEDIATE with unchanged commit/rollback semantics, sqlite-vec swallow + lazy-detect (OQ3)
- `index_lock()` (D-01..D-03): per-DB `sif.db.lock` (0600, T-11-01), flock try-loop with 50ms polling against a monotonic deadline, one-shot `on_wait` notice, kernel death-release, non-POSIX degrade-and-warn (A2); expiry proceeds with the loser's own pass (D-02)
- Both production connection paths route through the factory: `Database.connection` (CLI) and `DatabaseConnection._create_connection` (MCP); `transaction()` byte-identical; `sif.database` exports `create_connection`/`index_lock`
- `update_cmd` write work wrapped in the lock with a dim "Another index writer is running; waiting up to 30s..." notice; winner and loser both exit 0
- Four new test files: pragma audit + retry/degrade/swallow/exhaustion unit proofs, flock semantics incl. holder-SIGKILL release, in-suite SC1 (readers-during-writer both styles, busy-wait, threaded interleave), and deterministic parent-holds-lock SC2 subprocess proofs

## Task Commits

1. **Task 1 (tracer): shared factory + flock + update_cmd wrap** - `ab843e4` (feat)
2. **Task 2 RED: MCP delegation + exports failing tests** - `ff033fb` (test)
3. **Task 2 GREEN: MCP path through the factory** - `f6587d5` (feat)
4. **Task 3 RED: flock + SC1 proofs (expiry fails)** - `464f711` (test)
5. **Task 3 GREEN: expiry falls through to yield (D-02)** - `7b27635` (fix)
6. **Coverage completion: WAL-switch exhaustion raise** - `b7c386d` (test)

**Plan metadata:** final docs commit (below)

## Files Created/Modified

- `src/sif/database/factory.py` - NEW: the one shared connection factory + `_set_wal_with_retry` (for-else, unguarded final attempt) + `_load_sqlite_vec`
- `src/sif/database/locking.py` - NEW: `index_lock` context manager; path canonicalization; expiry-breaks-to-yield
- `src/sif/database/database.py` - `Database.connection` delegates to factory; `_enable_extensions` and `sqlite_vec` import deleted; `transaction()` verbatim; legacy duplicate `DatabaseConnection.connect` delegates until 11-03
- `src/sif/database/connection.py` - `_create_connection` is a single `return create_connection(...)`; class shapes verbatim; `ConnectionPool` untouched until 11-03
- `src/sif/database/__init__.py` - exports `create_connection`, `index_lock` (alphabetical `__all__`)
- `src/sif/config/settings.py` - `lock_wait_timeout: float = Field(default=30.0, ge=0)` (env `SIF_LOCK_WAIT_TIMEOUT`)
- `src/sif/cli/commands/index.py` - `update_cmd` wraps write work in `index_lock` with waiting notice; loop body unchanged (extraction is Plan 02)
- `tests/unit/database/test_factory.py`, `tests/unit/database/test_locking.py`, `tests/integration/test_concurrency.py`, `tests/integration/test_two_writer_subprocess.py` - NEW proofs (LIVE-06/LIVE-07)
- `tests/unit/database/test_database.py`, `tests/unit/cli/test_collection.py` - patch targets / mocked index paths updated for the rewiring

## Decisions Made

- See key-decisions in frontmatter (legacy-class delegation, expiry break-to-yield, for-else retry with unguarded final attempt, deterministic busy-wait test, lock-path canonicalization).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Legacy duplicate `DatabaseConnection` routed through the factory (plan said "stays untouched")**
- **Found during:** Task 1
- **Issue:** The plan mandates deleting `import sqlite_vec` from `database.py` while keeping the legacy duplicate class until Plan 03 — but that class's body references `sqlite_vec`, so deleting the import breaks ruff F821 and two existing tests patching `sif.database.database.sqlite_vec.load`
- **Fix:** The legacy class's `connect()` delegates to `create_connection` (marked deprecated, deleted in 11-03); the two patch targets moved to `sif.database.factory.sqlite_vec.load`
- **Files modified:** src/sif/database/database.py, tests/unit/database/test_database.py
- **Verification:** Full suite green; both vec-failure tests pass against the factory's swallow
- **Committed in:** ab843e4

**2. [Rule 1 - Bug] Mocked `index_path` created repo-root lock-file litter**
- **Found during:** Task 1 (full-suite run)
- **Issue:** Three existing pre-update-hook tests pass `MagicMock()` as `index_path`; update_cmd's new `Path(index_path)` materializes mock paths (`MagicMock/mock/<id>`) and the lock code created untracked `.lock` files in the repo root on every run (new ids each run → unbounded accumulation; the project hit committed mock-path artifacts once before, ba8a440)
- **Fix:** The three tests now pass `tmp_path / "sif.db"`; the three stray `.lock` files removed (pre-existing April artifacts left alone)
- **Files modified:** tests/unit/cli/test_collection.py
- **Verification:** Re-run leaves no litter; 22 affected tests pass
- **Committed in:** ab843e4

**3. [Rule 1 - Bug] `index_lock` expiry returned before yield — D-02 loser path crashed**
- **Found during:** Task 3 (RED run, by design of the tdd task)
- **Issue:** Deadline expiry did `return` from the `@contextmanager` generator before yielding → `RuntimeError: generator didn't yield` at with-entry; a 30s+ lock waiter would crash instead of running its own pass
- **Fix:** Expiry `break`s to the `yield` so the body runs unlocked; fd still closed in `finally`
- **Files modified:** src/sif/database/locking.py (+ test assertion-ordering fix in tests/unit/database/test_locking.py)
- **Verification:** `test_deadline_expiry_proceeds_without_lock_and_notifies_once` passes; incumbent-still-owns-lock asserted while holder fd is open
- **Committed in:** 7b27635

**4. [Plan-spec adjustment] Busy-timeout wait test numbers were internally inconsistent**
- **Found during:** Task 3 (test design)
- **Issue:** The plan specified busy_timeout=200 with elapsed >= 0.2s AND no exception — a 200ms timeout raises at ~0.26s (research baseline), so success with elapsed >= 0.2s requires the holder to commit inside a ~60ms window (a race, violating D-09)
- **Fix:** Deterministic variant: holder commits at 0.3s while the waiter (factory default 5000ms) busy-waits; asserts `elapsed >= 0.2`, success, and `"ok" not in result` before release; last-set-wins pinned separately via a PRAGMA round-trip on another connection
- **Files modified:** tests/integration/test_concurrency.py
- **Verification:** `test_second_writer_waits_out_short_holder` passes deterministically
- **Committed in:** 464f711

**5. [Scope addition] WAL-switch retry-exhaustion proof beyond the plan's test list**
- **Found during:** Task 3 close-out (coverage review)
- **Issue:** The retry's exhaustion-raise branch was the only uncovered factory path, and the OQ1 contract says in-suite tests carry coverage
- **Fix:** Added `test_wal_switch_exhaustion_raises_original_error` (direct helper invocation, incumbent never commits, attempts=2/backoff=0.01 — deterministic, ~0.02s)
- **Files modified:** tests/unit/database/test_factory.py
- **Verification:** 8 factory tests pass; coverage 96.30%
- **Committed in:** b7c386d

---

**Total deviations:** 5 auto-fixed (2 Rule 1 bugs, 1 Rule 3 blocker, 1 plan-spec adjustment, 1 coverage-completing scope addition)
**Impact on plan:** All fixes required for correctness/consistency of the plan's own instructions. No scope creep beyond the coverage-completing test (18 lines). Plan intent (D-01..D-06) fully preserved.

## Issues Encountered

- Single-file `pytest` runs trip the project-wide coverage addopts (`fail_under=90` over a partial run) — plan `<verify>` commands run with the project-standard `--no-cov` escape for partial suites; the full-suite gate runs on plain `pytest` as required.
- Pre-existing untracked `MagicMock/mock/` artifacts from April 2026 (real SQLite files from mocked paths in older sessions) were left untouched; logged here for awareness.

## Authentication Gates

None — no external services in this plan.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Ready for Plan 02 (IncrementalIndexer extraction): factory + lock are in place; `update_cmd`'s loop body is untouched and awaiting extraction into per-file transactions
- Runtime files that begin appearing next to user DBs (release-notes item per plan): `<db>.lock` (0600) and `-wal`/`-shm` sidecars while connections are open (removed on last close); existing DBs auto-convert to WAL on first open
- Plan 03 will retire `ConnectionPool`, the duplicate legacy `DatabaseConnection` (already factory-routed and marked deprecated), and dead `DocumentIndexer`

## Self-Check: PASSED

All 6 key files exist on disk; all 6 task commits (ab843e4, ff033fb, f6587d5, 464f711, 7b27635, b7c386d) are ancestors of HEAD; `plan_head_before=4f5c830`, `plan_head_after=b7c386d`, commits measured = 6.

---
*Phase: 11-live-index-foundation-concurrent-db-incremental-core*
*Completed: 2026-11-07*
