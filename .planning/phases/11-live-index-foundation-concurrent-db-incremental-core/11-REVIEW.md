---
phase: 11-live-index-foundation-concurrent-db-incremental-core
reviewed: 2026-11-11T04:24:37Z
depth: standard
files_reviewed: 1
files_reviewed_list:
  - src/sif/indexing/watcher.py
findings:
  critical: 0
  warning: 0
  info: 4
  total: 4
  necessity: 0
status: issues_found
---

# Phase 11: Code Review Report (incremental re-review, post-fix)

**Reviewed:** 2026-11-11T04:24:37Z
**Depth:** standard
**Files Reviewed:** 1 (`src/sif/indexing/watcher.py` at HEAD `2adc456`)
**Status:** issues_found

## Summary

Second incremental re-review of `src/sif/indexing/watcher.py`, focused on
verifying the WR-01/WR-02 fixes from commits `224d1db` and `c210f4a` against
the actual source, re-assessing IN-01/IN-02/IN-03 with fresh line references,
and running a fresh adversarial pass over the changed code for new defects.

**WR-01 — VERIFIED FIXED, finding drops.** Both halves of the fix are present
and grounded in the installed watchdog 6.0.0 source:

- The `_on_tick()` call in `_worker_loop`'s `except queue.Empty` arm is now
  wrapped in `try/except Exception` + `logger.exception("watch tick failed;
  continuing next interval")` (`src/sif/indexing/watcher.py:741-747`), exactly
  the recommended shape. One tick exception can no longer kill the worker
  thread for the process lifetime.
- New `_unschedule_quietly` helper (`src/sif/indexing/watcher.py:441-453`)
  wraps `observer.unschedule(handle)` in `contextlib.suppress(KeyError)` and
  is used at BOTH previously-bare call sites: `recovery_tick`'s
  disappeared-root branch (line 542) and `_unschedule_removed` (line 600).
  Grep confirms no bare `observer.unschedule` call site remains. Verified
  against the installed watchdog (`observers/api.py:362-376`):
  `unschedule` does a bare `self._emitter_for_watch[watch]` lookup, and
  `observer.stop()` -> `on_thread_stop()` -> `unschedule_all()` ->
  `_clear_emitters()` clears that map (`observers/api.py:241-248`), so
  `KeyError` is provably the exception a stop-cleared registry raises, and
  every statement in the unschedule body that could raise in this race raises
  `KeyError` (the whole body runs under the observer lock). The suppression
  targets the real trigger.

**WR-02 — VERIFIED FIXED, finding drops.** `stop()`
(`src/sif/indexing/watcher.py:455-503`) now quiesces the worker before
touching any worker-owned state, exactly as prescribed: `_stop_event.set()`
(469) and the stop sentinel (472) come first, then the bounded 10s worker
join with the skip-flush-on-live-worker gate (478-486), and only then
`observer.stop()` (493) and the debouncer stops (494-496), the flush
(497-498), and the final joins (500-503). Both `_watch_states` iterations now
walk `list(...)` snapshots (lines 494, 501), so even the timed-out-join edge
(a late worker tick still mutating the dict) cannot raise
`RuntimeError: dictionary changed size during iteration` out of `stop()`.

The documented trade-off of the timed-out edge — a debouncer armed by a very
late worker mutation is missed by the stop snapshot — is process-exit-safe:
watchdog's `BaseThread.__init__` sets `daemon = True`
(`utils/__init__.py:38-43`), and the watcher's own worker thread is
`daemon=True` (line 396), so no leaked thread can hang interpreter exit.

**No new defects from the fixes.** Adversarially traced the changed code
paths: double-`stop()` is idempotent (the second sentinel is skipped by
`_drain_once`'s `job is not None` check at line 859); a sentinel left in the
queue when the worker exits via the loop-top stop flag is likewise skipped;
`stop()` re-ordered intake-stop before the drain makes the flush see a
quiesced queue (strictly better than the old order). I also chased one
candidate the previous review did not address — `rescope`'s identity-by-name
diff ignoring a same-name path change — and rejected it as unreachable: no
CLI or MCP surface mutates a collection's `path` after creation
(`src/sif/cli/commands/collection.py` offers only add/remove/rename/
enable/disable/update-cmd/include/exclude; `CollectionRepository.update`
accepts a path but no caller changes it), and remove+re-add changes the name
set, which the diff handles correctly.

**Quality gates:** `ruff check` and `ruff format --check` on the file pass;
`pytest tests/unit/indexing/test_watcher.py tests/unit/mcp/test_mcp_watch_host.py
tests/integration/test_watch_e2e.py` — 60 passed (the 90% coverage-gate FAIL
is a single-subset artifact, identical pre-fix).

**Necessity review performed** (rubric read at standard depth): every
defensive construct in the changed code defends a reachable state — the
KeyError suppression is grounded in the watchdog source, the tick guard and
snapshots defend the timed-out-join/tick-in-flight interleavings. Zero
necessity findings.

Result: both warnings drop as verified-fixed; the three info items remain
(fresh line references below), plus one new info item: the two concurrency
fixes ship with no committed regression test.

## Info

### IN-01: Inert busy-check branch in `_checkpoint_if_idle` (dead code that implies behavior it does not have)

**File:** `src/sif/indexing/watcher.py:706-707`
**Issue:** `if row is not None and row[0]: return` is the last statement of
the function — both the busy and non-busy paths are behaviorally identical,
so the branch is dead. The docstring ("A busy result row means another
connection holds the WAL: skip silently") reads as if a distinct skip action
exists; a maintainer could reasonably believe busy is handled specially. In
reality a busy TRUNCATE result needs no action here only because the deadline
was already reset in `_checkpoint_if_due` (line 687) — worth stating in code,
not in a dead branch. Unchanged since the previous review.
**Fix:** Replace the branch with a comment (or a `logger.debug` on busy)
saying the deadline reset in the caller is what postpones the retry, and
delete the no-op `if`.

### IN-02: WAL-checkpoint PRAGMA constant triplicated across modules

**File:** `src/sif/indexing/watcher.py:58`, `src/sif/cli/commands/watch.py:62`, `src/sif/mcp/watch_host.py:45`
**Issue:** `_WAL_CHECKPOINT_TRUNCATE = "PRAGMA wal_checkpoint(TRUNCATE)"` is
defined identically in three modules. A future change to the checkpoint
spelling (e.g. `PASSIVE` vs `TRUNCATE`, or `wal_autocheckpoint` interplay)
would have to be made in three places that are deliberately designed to share
the same shutdown contract. Unchanged since the previous review.
**Fix:** Define it once (e.g. in `sif/database/` alongside the other SQLite
recipe strings) and import it at the three call sites.

### IN-03: "Bounded" stop flush is not time-bounded at embed depth

**File:** `src/sif/indexing/watcher.py:457` (docstring), `851-864` (`_drain_once`)
**Issue:** `stop()` carefully bounds the worker join at 10s and skips the
flush when the worker is still alive, yet once the worker is dead the flush
itself runs `_run_job` on the stop-caller's thread — and at embed depth the
first flushed job can trigger the lazy `manager.load_model()` (the exact
first-use hazard the join-timeout comment at lines 475-477 warns about) or a
`lock_timeout`-long flock wait per job. The docstring's "drain queued work
once (bounded)" (line 457) and `_drain_once`'s "bounded, no waiting" (line
852) are bounded in count and dequeue-blocking, not in time. The CLI
second-signal escape (exit 130) and the daemon SIGKILL fallback mitigate, so
this is a documentation/robustness gap rather than a hang bug. Unchanged
since the previous review.
**Fix:** Note explicitly in the `stop()`/`_drain_once` docstrings that the
flush is count-bounded only and may legitimately perform first-use model
load, or skip embed-depth jobs in the flush when their lock-window cost
would exceed the join budget (leaving them to the next run's reconcile).

### IN-04: WR-01/WR-02 concurrency fixes have no committed regression test

**File:** `src/sif/indexing/watcher.py:741-747`, `441-453`, `469-503` (uncovered guards); tests at `tests/unit/indexing/test_watcher.py`
**Issue:** The fixer's behavioral proofs (a real `_worker_loop` surviving a
raising `_on_tick`; `_unschedule_quietly` swallowing a stop-cleared-registry
`KeyError`; `stop()` under dict churn) were throwaway scripts, per
`11-REVIEW-FIX.md`. The committed suite never drives the real `_worker_loop`
with a raising tick — every `_on_tick` test (e.g. lines 1713-1744, 1825-1862)
invokes it directly with the worker quiesced, and the only `RuntimeError`
raise in the file (line 1424) exercises the pre-existing rescope-provider
guard. Likewise no test covers a `stop()`-cleared observer registry hitting
`_unschedule_quietly`, or the `list()` snapshot under a concurrent mutation.
A future refactor could silently revert either guard without any test
failing — the exact silent-live-indexing-death failure mode WR-01 described.
The test file was last touched in phase 13 (`8039a3e`), before both fixes.
**Fix:** Commit one test per guard: (a) run the real `_worker_loop` with
`_on_tick` monkeypatched to raise, assert the worker survives and processes a
subsequently enqueued job; (b) call `recovery_tick` against an observer whose
registry was cleared by `stop()` and assert no exception and remaining roots
still processed.

---

_Reviewed: 2026-11-11T04:24:37Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
