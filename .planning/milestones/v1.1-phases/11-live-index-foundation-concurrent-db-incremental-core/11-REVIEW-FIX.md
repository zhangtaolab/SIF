---
phase: 11-live-index-foundation-concurrent-db-incremental-core
fixed_at: 2026-11-11T04:37:47Z
review_path: .planning/phases/11-live-index-foundation-concurrent-db-incremental-core/11-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 11: Code Review Fix Report

**Fixed at:** 2026-11-11T04:37:47Z
**Source review:** .planning/phases/11-live-index-foundation-concurrent-db-incremental-core/11-REVIEW.md
**Iteration:** 1 (re-review at HEAD `2adc456`; supersedes the previous fix report, which covered the pre-fix WR-01/WR-02 iteration)

**Summary:**
- Findings in scope: 4 (IN-01 … IN-04 — fix_scope `all`)
- Fixed: 4
- Skipped: 0

**Environment note:** `workflow.use_worktrees=false`, so all edits, commits, and
verification gates below ran directly in the main checkout (`/Users/forrest/GitHub/SIF`,
branch `dev`) — the numbers are reproducible from that tree as-is.

## Fixed Issues

### IN-01: Inert busy-check branch in `_checkpoint_if_idle`

**Files modified:** `src/sif/indexing/watcher.py`
**Commit:** `1a577bc`
**Applied fix:** Took the review's `logger.debug`-on-busy option: the dead
`if row is not None and row[0]: return` tail is now a live branch that logs
busy at DEBUG ("Idle WAL checkpoint busy (WAL held elsewhere); retrying next
interval") with an adjacent comment stating that the caller's deadline reset in
`_checkpoint_if_due` — not anything done in this function — is what postpones
the retry. The docstring's "skip silently" sentence was rewritten to say the
same, so the code no longer implies a distinct skip action it does not have.
DEBUG level keeps the existing
`test_busy_row_skips_silently_and_resets_deadline` warning-silence contract
intact (caplog at WARNING never sees it), and it fires at most once per
checkpoint interval, respecting Pitfall 7.

### IN-02: WAL-checkpoint PRAGMA constant triplicated across modules

**Files modified:** `src/sif/database/factory.py`, `src/sif/indexing/watcher.py`,
`src/sif/cli/commands/watch.py`, `src/sif/mcp/watch_host.py`
**Commit:** `2444fa0`
**Applied fix:** Defined the constant once as public
`WAL_CHECKPOINT_TRUNCATE = "PRAGMA wal_checkpoint(TRUNCATE)"` in
`sif/database/factory.py` (alongside the other locked SQLite recipe strings,
with the 12-D14/D-16 provenance comment carried over) and imported it at all
three former definition sites (`watcher.py` idle tick, `cli/commands/watch.py`
`shutdown_watcher`, `mcp/watch_host.py` `stop_embedded_watch`). Grep confirms a
single definition and three import sites; no underscore-prefixed copies remain.
No circular imports (factory.py imports only stdlib + sqlite_vec +
`sif.utils.logging`).

### IN-03: "Bounded" stop flush is not time-bounded at embed depth

**Files modified:** `src/sif/indexing/watcher.py`
**Commit:** `1bfd7c5`
**Applied fix:** Took the review's recommended documentation option (the
behavioral alternative — skipping embed-depth jobs in the flush — would change
the shutdown data contract and was not warranted for an Info finding).
`stop()`'s docstring now says "count-bounded" in the summary line and adds a
paragraph explaining the bound is a COUNT bound with non-blocking dequeue, not
a time bound: once the worker join has quiesced, each flushed job runs on the
stop-caller's thread and at embed depth may legitimately take unbounded time
(lazy first-use `manager.load_model()`, a `lock_timeout`-long flock wait per
job), with the hosts' second-signal escapes (CLI exit 130, daemon SIGKILL
fallback) as the time-bounded way out. `_drain_once`'s docstring makes the same
count-bounded-not-time-bounded distinction explicitly.

### IN-04: WR-01/WR-02 concurrency fixes have no committed regression test

**Files modified:** `tests/unit/indexing/test_watcher.py`
**Commit:** `d6412fb`
**Applied fix:** Added `TestConcurrencyGuardRegressions` with one test per
guard (plus the stop-ordering proof the review's fix text asked for):
- `test_real_worker_loop_survives_raising_tick` — starts the REAL
  `_worker_loop` thread with `_on_tick` monkeypatched to raise, waits (bounded
  poll, restat_interval=0.05) for the failure to actually fire, then enqueues a
  real reconcile job and asserts the same surviving worker processes it
  (`on_batch` fires). A reverted tick guard kills the thread and fails here.
- `test_recovery_tick_tolerates_stop_cleared_observer_registry` —
  `observer.unschedule` raises `KeyError` at every attempt (what a
  `stop()`-cleared `_emitter_for_watch` map does per the watchdog 6.0.0
  source); two roots both disappear and `recovery_tick` must not raise, must
  unschedule-attempt BOTH roots (iteration did not abort at alpha's KeyError),
  must mark both missing with cleared handles, and must preserve documents.
- `test_stop_quiesces_worker_and_snapshot_survives_mid_iteration_mutation` —
  recording fakes prove `worker.join` precedes `observer.stop` and the
  debouncer teardown (quiesce-before-touch, WR-02), and alpha's debouncer
  teardown pops beta from `_watch_states` MID-iteration (the timed-out-join
  edge): `stop()` must return without "dictionary changed size during
  iteration", the snapshot must still stop BOTH debouncers, and the flush must
  run only after intake is fully stopped (before the final observer join).
Mutation-verified: temporarily reverting each guard in `src/sif/indexing/watcher.py`
(tick try/except removed; `contextlib.suppress(KeyError)` removed; `list()`
snapshots removed) made exactly the corresponding test fail; the committed
guards were restored via `git checkout` afterward and all tests went green.

## Verification

All gates ran in the main checkout (no worktree; `workflow.use_worktrees=false`):

- Per fix: `ast.parse` + `ruff check` + `ruff format --check` on every touched
  file (Tier 1 + Tier 2), plus targeted pytest runs after each commit.
- Final combined gates on HEAD `d6412fb`:
  - `ruff check src tests` — pass; `ruff format --check src tests` — 187 files clean.
  - `ty check src/sif` — pass.
  - `pytest tests/unit/indexing/test_watcher.py tests/unit/mcp/test_mcp_watch_host.py
    tests/unit/cli/test_watch_cmd.py tests/integration/test_watch_e2e.py` —
    98 passed (43 pre-existing watcher tests + 3 new; 54 in the MCP/watcher
    subset; 41 CLI/e2e).
  - New tests additionally run 3x consecutively (threaded test stability) and
    once against each reverted guard (all three fail as expected).
- Full-tree pytest intentionally not used as a gate: ~13 pre-existing failures
  from suite-ordering interference unrelated to this phase (per session
  baseline); all phase-relevant files were run targeted instead.

## Skipped Issues

None — all four in-scope findings were fixed.

---

_Fixed: 2026-11-11T04:37:47Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
