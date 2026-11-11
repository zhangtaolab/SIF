---
phase: 11-live-index-foundation-concurrent-db-incremental-core
reviewed: 2026-11-11T03:10:26Z
depth: standard
files_reviewed: 1
files_reviewed_list:
  - src/sif/indexing/watcher.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
  necessity: 0
status: issues_found
---

# Phase 11: Code Review Report (incremental re-review)

**Reviewed:** 2026-11-11T03:10:26Z
**Depth:** standard
**Files Reviewed:** 1 (`src/sif/indexing/watcher.py` at HEAD)
**Status:** issues_found

## Summary

Incremental re-review of `src/sif/indexing/watcher.py` as it stands at HEAD —
the phase-11 covered file (flock-aware watcher repointed onto the shared
incremental core) as subsequently extended by phase 12's watch MVP
(FileWatcher/WatchConfig/debounce/fold) and the phase 13/16 long-lived-host
opt-ins (rescope, idle WAL checkpoint, D-17 schedule-failure retry).

The core is genuinely solid. Verified against the dependencies and the
installed watchdog 6.0.0 source: `fold_events` is order-independent with
correct created/modified/deleted/moved semantics and the atomic-save
touched-then-deleted case handled by disk-truth stat inside `update_paths`;
the FSEvents realpath Pitfall-2 resolution and the shared `scanner.matches`
predicate keep watch and scan membership identical; the per-collection
`_WatchState`/debouncer lifecycle fixes the prior phase-11 multi-collection
lifecycle defect (a leaked/stale debouncer per disappear/return and per
rescope cycle is now stopped and joined, WR-02 of that era); the
`_EmbedSession` fail-soft contract (backend/model/dimension failures disable
embed for the session with one error event, BM25 freshness continues) and the
per-path pending-retry set are coherent with `IncrementalIndexer`'s
chunk/embedding purge behavior; `stop()`'s skip-flush-on-live-worker gate and
`worker_joined()` correctly prevent same-connection racing with the shutdown
WAL checkpoint; the `IndexingEventHandler` on_any_event single-forward claim
and the `EventDebouncer` positional-arg/float-timeout claims both check out
against the installed watchdog source; all SQL is parameterized (no injection
surface); `ruff check` and `ruff format --check` pass.

Two warnings remain, both in the stop/tick concurrency seam the class itself
identifies as Pitfall 6, plus three info-level quality items. No critical
issues; no necessity findings — every defensive construct checked (D-11
missing-root guards, D-17 OSError schedule retry, embed pending-retry, the
injectable tick clock as a test seam) defends a reachable state.

## Warnings

### WR-01: Worker tick is not exception-guarded — one tick exception permanently kills live indexing

**File:** `src/sif/indexing/watcher.py:710-715` (trigger ground truth at `514-515`)
**Issue:** `_worker_loop` wraps `_run_job` in `except Exception` + `logger.exception`
(lines 721-726), but the `_on_tick()` call at line 714 (inside the
`except queue.Empty` arm) has no guard. Any exception escaping a tick kills
the worker thread for the rest of the process lifetime: the host banner still
says "Watching", events keep being enqueued by debouncers, and nothing ever
consumes them — live indexing silently stops.

There is a concrete, reproducible trigger grounded in the installed watchdog
6.0.0 source: `FileWatcher.stop()` (line 448) calls `observer.stop()`, which
synchronously runs `on_thread_stop() -> unschedule_all()` and clears every
watch registration — while a tick already in flight (the worker checks
`_stop_event` only at the loop top, line 710) can still execute
`recovery_tick`'s `observer.unschedule(state.handle)` (line 515) /
`_unschedule_removed`'s `observer.unschedule` (line 573). Watchdog's
`BaseObserver.unschedule` indexes `self._emitter_for_watch[watch]` directly
and raises `KeyError` when the registration was just cleared — `KeyError` is
not caught anywhere (only `OSError` is handled, at line 421). The result is a
raw threading-excepthook traceback at shutdown, the rest of that tick
(rescope, checkpoint, remaining roots' recovery) skipped, and any reconcile
jobs the tick had enqueued left unprocessed if the worker dies before
consuming them.

**Fix:** Guard the tick the same way jobs are guarded, and harden the
unschedule sites against the stop-cleared registry:

```python
except queue.Empty:
    try:
        self._on_tick()
    except Exception:
        logger.exception("watch tick failed; continuing next interval")
    continue
```

plus, in `recovery_tick`/`_unschedule_removed`, tolerate a watch already
removed by `observer.stop()` (e.g. `try: observer.unschedule(handle) except
KeyError: pass`, or check `state.handle in observer._watches`-equivalent via a
public means such as `observer.emitters`), so one cleared registration skips a
single root instead of aborting the whole tick.


### WR-02: stop() mutates and iterates worker-owned state before quiescing the worker — races the rescope diff

**File:** `src/sif/indexing/watcher.py:447-457` (vs `569-579`, `589-605`)
**Issue:** The class documents `rescope`/`recovery_tick` as worker-thread-only
because "mutating `_watch_states` or the observer from any other thread races
the tick's own iteration (Pitfall 6)" (lines 543-547). `stop()` nevertheless
touches all of it from the host thread *before* signaling the worker:
`observer.stop()` at line 448 (which synchronously clears every registration —
the WR-01 KeyError trigger), then iteration of
`self._watch_states.values()` at lines 449-451, with `_stop_event.set()`
coming only at line 457. A concurrently running tick can `del
self._watch_states[name]` (`_unschedule_removed`, line 579) or insert a new
state (`_schedule_added`, line 594) mid-iteration, raising `RuntimeError:
dictionary changed size during iteration` out of `stop()` and into the host's
shutdown path (uncaught there). Reachable only with the rescope opt-in armed
(daemon host, MCP watch host) and a stop landing inside a set-changing
rescope tick — narrow timing, but it is a crash during shutdown of exactly
the long-lived hosts that opt in.

**Fix:** Quiesce the worker before touching worker-owned structures: set
`_stop_event` and put the sentinel first, complete the bounded join, then
stop/join the observer and debouncers from the now-quiet state (draining
afterward exactly as today). At minimum, iterate a snapshot
(`list(self._watch_states.values())`) and accept that a late worker mutation
leaves a just-armed debouncer stopped only by process exit.

## Info

### IN-01: Inert busy-check branch in _checkpoint_if_idle (dead code that implies behavior it does not have)

**File:** `src/sif/indexing/watcher.py:679-680`
**Issue:** `if row is not None and row[0]: return` is the last statement of
the function — both the busy and non-busy paths are behaviorally identical,
so the branch is dead. The comment ("A busy result row means another
connection holds the WAL: skip silently") reads as if a distinct skip action
exists; a maintainer could reasonably believe busy is handled specially. In
reality a busy TRUNCATE result needs no action here only because the deadline
was already reset in `_checkpoint_if_due` (line 660) — worth stating in code,
not in a dead branch.
**Fix:** Replace the branch with a comment (or a `logger.debug` on busy) that
says the deadline reset in the caller is what postpones the retry, and delete
the no-op `if`.

### IN-02: WAL-checkpoint PRAGMA constant triplicated across modules

**File:** `src/sif/indexing/watcher.py:57`, `src/sif/cli/commands/watch.py:62`, `src/sif/mcp/watch_host.py:45`
**Issue:** `_WAL_CHECKPOINT_TRUNCATE = "PRAGMA wal_checkpoint(TRUNCATE)"` is
defined identically in three modules. A future change to the checkpoint
spelling (e.g. `PASSIVE` vs `TRUNCATE`, or adding `PRAGMA wal_autocheckpoint`
interplay) would have to be made in three places that are deliberately
designed to share the same shutdown contract.
**Fix:** Define it once (e.g. in `sif/database/` alongside the other SQLite
recipe strings) and import it in the three call sites.

### IN-03: "Bounded" stop flush is not time-bounded at embed depth

**File:** `src/sif/indexing/watcher.py:818-831` (`_drain_once` via `stop`, 470-471)
**Issue:** `stop()` carefully bounds the worker join at 10s and skips the
flush when the worker is still alive, yet once the worker is dead the flush
itself runs `_run_job` on the stop-caller's thread — and at embed depth the
first flushed job can trigger the lazy `manager.load_model()` (the exact
first-use hazard the join timeout warns about) or a `lock_timeout`-long flock
wait per job. The docstring's "drain queued work once (bounded)" is bounded
in count, not in time. The CLI second-signal escape (exit 130) and the
daemon SIGKILL fallback mitigate this, so it is a documentation/robustness
gap rather than a hang bug.
**Fix:** Either note explicitly in the `stop()`/`_drain_once` docstrings that
the flush is count-bounded only and may legitimately perform first-use model
load, or skip embed-depth jobs in the flush when their lock-window cost would
exceed the join budget (leaving them to the next run's reconcile).

---

_Reviewed: 2026-11-11T03:10:26Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
