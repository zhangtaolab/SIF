---
phase: 11-live-index-foundation-concurrent-db-incremental-core
fixed_at: 2026-11-11T04:09:36Z
review_path: .planning/phases/11-live-index-foundation-concurrent-db-incremental-core/11-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 11: Code Review Fix Report

**Fixed at:** 2026-11-11T04:09:36Z
**Source review:** .planning/phases/11-live-index-foundation-concurrent-db-incremental-core/11-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 2 (WR-01, WR-02 — fix_scope `critical_warning`)
- Fixed: 2
- Skipped: 0
- Out of scope (Info severity, not attempted): IN-01, IN-02, IN-03 — see below

## Fixed Issues

### WR-01: Worker tick is not exception-guarded — one tick exception permanently kills live indexing

**Files modified:** `src/sif/indexing/watcher.py`
**Commit:** `224d1db`
**Status:** fixed: requires human verification (concurrency/state-handling fix; behavioral evidence below)
**Applied fix:**
- `_worker_loop`: the `_on_tick()` call in the `except queue.Empty` arm is now wrapped in
  `try/except Exception` + `logger.exception("watch tick failed; continuing next interval")`,
  matching the existing job guard — one tick failure no longer kills the worker thread for the
  process lifetime.
- New `FileWatcher._unschedule_quietly(observer, handle)` helper wrapping
  `observer.unschedule(handle)` in `contextlib.suppress(KeyError)` (ruff SIM105 required the
  `suppress` form over `try/except/pass`). Used at both unschedule sites the review cited:
  `recovery_tick`'s disappeared-root branch and `_unschedule_removed`. Verified against the
  installed watchdog 6.0.0 source that `BaseObserver.unschedule` does a bare
  `self._emitter_for_watch[watch]` lookup (raises `KeyError` once `observer.stop()` →
  `on_thread_stop()` → `unschedule_all()` has cleared the registry), so the guard targets the
  real trigger; a cleared registration now skips a single root instead of aborting the tick.

### WR-02: stop() mutates and iterates worker-owned state before quiescing the worker — races the rescope diff

**Files modified:** `src/sif/indexing/watcher.py`
**Commit:** `c210f4a`
**Status:** fixed: requires human verification (concurrency/state-handling fix; behavioral evidence below)
**Applied fix:**
- `stop()` reordered to quiesce the worker FIRST: `_stop_event.set()` + stop sentinel + the
  bounded 10s worker join + the skip-flush-on-live-worker gate all run before any
  worker-owned state is touched. Only then `observer.stop()`, the debouncer `stop()` loop,
  the flush (`_drain_once`), and the final observer/debouncer joins — from the now-quiet
  state, exactly as the review's fix prescribed.
- Both `self._watch_states` iterations in `stop()` now walk `list(...)` snapshots, so even the
  timed-out-worker edge (a late tick still mutating the dict) cannot raise
  `RuntimeError: dictionary changed size during iteration` out of `stop()` into the host's
  shutdown path. Documented trade-off (accepted by the review): a debouncer armed by a very
  late worker mutation is then stopped only by process exit.
- Public contract preserved: `stop()` then `worker_joined()` sequencing used by both hosts
  (`src/sif/cli/commands/watch.py`, `src/sif/mcp/watch_host.py`) is unchanged.

## Verification

All verification ran in the **main checkout** (`workflow.use_worktrees` is `false` in
`.planning/config.json`, so the fixer edited and committed directly on `dev`; numbers are
reproducible from this tree).

Per fix (before each commit):
- `ruff check src/sif/indexing/watcher.py` + `ruff format --check src/sif/indexing/watcher.py` — clean.
- `pytest tests/unit/indexing/` — 120 passed (coverage-gate FAIL on single-dir runs is a
  subset artifact, identical pre-fix).
- Behavioral proofs beyond syntax (throwaway scripts, not committed):
  - WR-01: drove the real `_worker_loop` with `_on_tick` raising `RuntimeError` — worker
    survived 7 consecutive failing ticks (each logged via `logger.exception`) and then
    processed an enqueued job; `_unschedule_quietly` swallowed the `KeyError` from a
    stop-cleared-registry observer while still forwarding a normal unschedule.
  - WR-02: ran `stop()` concurrently with a thread performing 400 dict insert/delete churns
    (the `_unschedule_removed`/`_schedule_added` shape) — no exception escaped `stop()`;
    both debouncers still stopped.

Post-fix integration:
- `pytest tests/integration/test_watch_e2e.py tests/integration/test_watch_daemon_e2e.py` —
  11 passed (includes the graceful-stop WAL-truncate/no-traceback path with a real observer).
- `pytest tests/integration/test_mcp_watch_e2e.py` — 4 passed.
- `ruff check src tests` + `ruff format --check src tests` — clean project-wide.
- Full unit tree: 13 failures + 1 torch-import collection error, **byte-identical to the
  pre-fix baseline** (A/B verified by temporarily restoring `5f7012d`'s watcher.py and
  diffing the failure lists) — all pre-existing full-suite ordering interference
  (they pass in directory isolation) and/or environmental (no `torch` installed), none
  caused by these fixes.

## Out of Scope (Info severity — `fix_scope: critical_warning`)

### IN-01: Inert busy-check branch in _checkpoint_if_idle
**File:** `src/sif/indexing/watcher.py:679-680`
**Reason:** Info severity, outside `critical_warning` scope; left for a human decision.

### IN-02: WAL-checkpoint PRAGMA constant triplicated across modules
**Files:** `src/sif/indexing/watcher.py:57`, `src/sif/cli/commands/watch.py:62`, `src/sif/mcp/watch_host.py:45`
**Reason:** Info severity, outside `critical_warning` scope; left for a human decision.

### IN-03: "Bounded" stop flush is not time-bounded at embed depth
**File:** `src/sif/indexing/watcher.py:818-831`
**Reason:** Info severity, outside `critical_warning` scope; left for a human decision.

---

_Fixed: 2026-11-11T04:09:36Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
