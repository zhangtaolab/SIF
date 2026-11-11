---
phase: 11-live-index-foundation-concurrent-db-incremental-core
reviewed: 2026-11-11T04:43:51Z
depth: standard
files_reviewed: 1
files_reviewed_list:
  - src/sif/indexing/watcher.py
findings:
  critical: 0
  warning: 0
  info: 0
  total: 0
  necessity: 0
status: clean
---

# Phase 11: Code Review Report (iteration 3 — post-IN-fix re-review)

**Reviewed:** 2026-11-11T04:43:51Z
**Depth:** standard
**Files Reviewed:** 1 (`src/sif/indexing/watcher.py` at HEAD `d6412fb`, clean working tree)
**Status:** clean

## Summary

Third re-review of `src/sif/indexing/watcher.py`, verifying the four info-item
fixes from commits `1a577bc` (IN-01), `2444fa0` (IN-02), `1bfd7c5` (IN-03), and
`d6412fb` (IN-04) against the actual source, then running a fresh adversarial
pass over the fix deltas and the full file. All four fixes are verified
complete; no new defects were introduced. All reviewed files meet quality
standards. No issues found.

Supporting files consulted for verification (not in the reviewed scope):
`src/sif/database/factory.py`, `src/sif/cli/commands/watch.py`,
`src/sif/mcp/watch_host.py`, `tests/unit/indexing/test_watcher.py`,
`tests/unit/cli/test_watch_cmd.py`.

**IN-01 — VERIFIED FIXED, finding drops.** The inert
`if row is not None and row[0]: return` tail of `_checkpoint_if_idle`
(`src/sif/indexing/watcher.py:715-719`) is now a `logger.debug("Idle WAL
checkpoint busy (WAL held elsewhere); retrying next interval")` with an inline
comment stating the caller's deadline reset is what postpones the retry, and
the docstring (`:697-706`) was rewritten to match ("nothing to do here — the
deadline reset in :meth:`_checkpoint_if_due` is what postpones the retry,
surfaced at debug only"). The branch now has observable behavior and no longer
implies a skip action it does not take. The log call introduces no behavior
change at the default INFO level.

**IN-02 — VERIFIED FIXED, finding drops.** `WAL_CHECKPOINT_TRUNCATE` is now
defined exactly once, at `src/sif/database/factory.py:45` with a comment naming
its three consumers, and imported at all three former definition sites:
`src/sif/indexing/watcher.py:33` (use at `:711`),
`src/sif/cli/commands/watch.py:49` (use at `:113`), and
`src/sif/mcp/watch_host.py:37` (use at `:181`). Repo-wide grep confirms zero
remaining module-local copies. No circular import: `factory.py` imports only
stdlib, `sqlite_vec`, and `sif.utils.logging`. The independent literal in
`tests/unit/cli/test_watch_cmd.py:43` is deliberate test-pinning of the pragma
value (importing the production constant would make the assertion tautological)
— not residual duplication.

**IN-03 — VERIFIED FIXED, finding drops.** `stop()`'s docstring
(`src/sif/indexing/watcher.py:454-467`) now states explicitly that "The flush
bound is a COUNT bound — every job already queued at stop time, dequeued
without blocking — not a time bound," naming the two real unbounded-time
hazards (lazy first-use `manager.load_model()`, per-job `lock_timeout` flock
wait) and the hosts' second-signal escapes as the time-bounded way out.
`_drain_once`'s docstring (`:864-872`) carries the matching "Count-bounded and
non-blocking on dequeue only — NOT time-bounded" statement. The documentation
no longer implies time-boundedness it does not have.

**IN-04 — VERIFIED FIXED, finding drops.** New
`TestConcurrencyGuardRegressions` (`tests/unit/indexing/test_watcher.py:837-1035`,
commit `d6412fb`, +202 lines) delivers the prescribed regression coverage:

- `test_real_worker_loop_survives_raising_tick` (`:848`) drives the REAL
  `_worker_loop` thread with `_on_tick` monkeypatched to raise, then asserts a
  job enqueued after the failure is still processed — pinning the WR-01 tick
  guard against the silent-live-indexing-death revert.
- `test_recovery_tick_tolerates_stop_cleared_observer_registry` (`:906`) sets
  `observer.unschedule.side_effect = KeyError` (a stop-cleared registry) and
  asserts `recovery_tick` processes BOTH disappeared roots (`call_count == 2`,
  both `missing is True`, documents preserved) — pinning the
  `_unschedule_quietly` suppression and iteration continuation.
- `test_stop_quiesces_worker_and_snapshot_survives_mid_iteration_mutation`
  (`:965`) mutates `_watch_states` mid-iteration via a debouncer-stop side
  effect and asserts ordering (`worker.join` before `observer.stop` and
  debouncer stops; both debouncers stopped before the drain; drain before
  `observer.join`) — pinning the WR-02 quiesce-then-snapshot shape.

The tests are deadline-bounded (5s/10s waits, no fixed sleeps), assert on
structure rather than timing, and clean up in `finally` blocks.

**No new defects from the fixes.** Adversarially traced every fix delta: the
debug log is a pure constant-string call; the import move adds no cycle and no
meaningful import cost (every watcher entry point already opens a factory
connection); both docstring rewrites are accurate against the code they
describe (`index_lock(lock_timeout)` per job, lazy `load_model()` in
`ensure_ready`, CLI second-signal exit and daemon SIGKILL fallback); and the
new tests use the file's established `_delenv_settings_vars`/`_seed_*` helpers
without disturbing existing coverage.

**Necessity review performed** (rubric read at standard depth): every defensive
construct in the file defends a reachable state — the KeyError suppression is
grounded in the installed watchdog source, the tick guard and `list()`
snapshots defend real interleavings, and the `rescope_provider`/
`checkpoint_interval` opt-ins are instantiated by actual hosts
(`src/sif/mcp/watch_host.py:149-151` and the daemon wiring at
`src/sif/cli/commands/watch.py:383-385`), so they are not generality without
instantiation. Zero necessity findings.

**Quality gates:** `ruff check` and `ruff format --check` pass on all five
touched files; `pytest tests/unit/indexing/test_watcher.py
tests/unit/cli/test_watch_cmd.py tests/unit/mcp/test_mcp_watch_host.py` — 92
passed; `TestConcurrencyGuardRegressions` — 3 passed;
`tests/integration/test_watch_e2e.py` — 6 passed. (The 90% coverage-gate FAIL
on subset runs is the documented single-subset artifact, identical pre-fix.)

Result: all four info findings verified fixed and dropped; no new findings.

---

_Reviewed: 2026-11-11T04:43:51Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
