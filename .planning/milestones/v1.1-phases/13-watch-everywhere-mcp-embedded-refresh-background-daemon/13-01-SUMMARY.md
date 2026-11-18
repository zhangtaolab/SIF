---
phase: 13-watch-everywhere-mcp-embedded-refresh-background-daemon
plan: 01
subsystem: indexing
tags: [watcher, rescope, wal-checkpoint, inotify, watchdog, settings, tick]

requires:
  - phase: 12-sif-watch-foreground-mvp
    provides: FileWatcher core (observer/debouncer/queue/worker, recovery_tick, _schedule_watch) grown by this plan
provides:
  - FileWatcher.rescope(collections) public API — exact-set live diff of the watched collection set (D-15)
  - WatchConfig.rescope_provider / rescope_interval / checkpoint_interval / now opt-ins — the seam 13-02's daemon and 13-03's MCP host wire
  - Tick-side idle WAL checkpoint (PRAGMA wal_checkpoint(TRUNCATE)) with busy-row and recent-burst skips, disabled by default (D-16)
  - Schedule-failure handling: OSError from observer.schedule warns once per failure episode with errno cause + fs.inotify.max_user_watches remedy; other roots keep watching; tick retries (D-17)
  - Settings fields mcp_watch (SIF_MCP_WATCH opt-in, inert until 13-03), watch_rescope_interval=60.0 (ge=1), watch_checkpoint_interval=300.0 (ge=0)
affects: [13-02 daemon host, 13-03 MCP watch host, 13-04 docs regeneration]

actuals:
  tokens: 10833   # chars/4 over the realized production diff (805 insertions / 22 deletions across 3 files)
  tasks: 2
  commits: 4      # measured: git rev-list --count 90e620b..HEAD
plan_head_before: 90e620b162ce85a8d60398b13635b4633bc82539
plan_head_after: 8b8e5f52396bb2c76645b10b8f92135c99eb1004

tech-stack:
  added: []       # zero new dependencies (milestone lock held)
  patterns:
    - "Long-lived host behaviors ride the existing idle tick (_on_tick helper) behind interval guards — default config performs zero extra work"
    - "Injectable monotonic clock (WatchConfig.now) makes deadline machinery zero-timing testable"
    - "Warn-once-per-failure-episode flags on _WatchState for retry loops that must not spam"
    - "Per-state debouncer on _WatchState (parallel list removed) enables clean unschedule on rescope removal"

key-files:
  created: []
  modified:
    - src/sif/indexing/watcher.py - rescope/_unschedule_removed/_schedule_added, _on_tick/_rescope_if_due/_checkpoint_if_due/_checkpoint_if_idle, _schedule_watch->bool with D-17 warn, _last_job_at tracking
    - src/sif/config/settings.py - mcp_watch, watch_rescope_interval, watch_checkpoint_interval fields
    - tests/unit/indexing/test_watcher.py - TestLiveRescope, TestWatchSettings, TestIdleCheckpoint, TestScheduleFailure batteries

key-decisions:
  - "rescope is an exact-set diff: the provider embodies the host's eligible set (a -c filter withholds names), resolving open question 1 as rescope-within-the-filter"
  - "Deadline machinery seeds lazily on the first tick (one full interval of grace) and resets on every due fire — busy/recent-burst skips postpone a full interval, never retry inside the tick"
  - "D-17 callers treat a failed schedule like a missing root (state.missing stays True) so the existing D-12 tick retries without warning spam; the recovery 'returned' warning moved inside the success branch"
  - "mcp_watch lands as a Settings field only and stays inert until 13-03 wires the MCP watch host (plan-scoped)"
  - "Worker-thread protection: provider() and the checkpoint pragma are guarded so one failure cannot kill the months-long daemon's worker thread"

patterns-established:
  - "Tick riders: recovery + rescope-if-due + checkpoint-if-due all on the worker thread, each behind an opt-in interval guard (Pitfall 6 discipline)"
  - "Quiesced-worker unit pattern: monkeypatch instance _worker_loop to a no-op before start() so direct tick/queue assertions are deterministic"

requirements-completed: [LIVE-08, LIVE-09]   # declared by this plan; REQUIREMENTS.md marking goes through the shared-ID gate (LIVE-08 shared with 13-03, LIVE-09 with 13-02/13-04)

coverage:
  - id: D1
    description: "Live rescope of the watched collection set (D-15): added root schedules + reconciles (file under new root indexed), removed root unschedules with documents preserved and no further jobs, provider set respected exactly, no-provider default never changes the watch set"
    requirement: LIVE-08
    verification:
      - kind: unit
        ref: "tests/unit/indexing/test_watcher.py#TestLiveRescope::test_rescope_added_collection_schedules_and_reconciles (pass)"
        status: pass
      - kind: unit
        ref: "tests/unit/indexing/test_watcher.py#TestLiveRescope::test_rescope_removed_collection_unschedules_and_preserves_documents (pass)"
        status: pass
      - kind: unit
        ref: "tests/unit/indexing/test_watcher.py#TestLiveRescope::test_rescope_adds_exactly_the_providers_set_nothing_more (pass)"
        status: pass
      - kind: unit
        ref: "tests/unit/indexing/test_watcher.py#TestLiveRescope::test_no_provider_default_never_changes_watch_set (pass)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Tick integration + settings fields: rescope fires exactly once per elapsed interval via the injectable clock; mcp_watch/watch_rescope_interval/watch_checkpoint_interval defaults and SIF_ env spellings resolve (D-04)"
    requirement: LIVE-09
    verification:
      - kind: unit
        ref: "tests/unit/indexing/test_watcher.py#TestLiveRescope::test_rescope_adds_exactly_the_providers_set_nothing_more (tick cadence assertions, pass)"
        status: pass
      - kind: unit
        ref: "tests/unit/indexing/test_watcher.py#TestWatchSettings (defaults + env spellings, pass)"
        status: pass
      - kind: other
        ref: "python -c \"from sif.config.settings import Settings; s = Settings(); assert s.mcp_watch is False and s.watch_rescope_interval == 60.0 and s.watch_checkpoint_interval == 300.0\" (pass)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Idle WAL checkpoint on the tick (D-16): one PRAGMA wal_checkpoint(TRUNCATE) per elapsed interval on the worker connection; busy row skips silently with deadline reset; recent-burst postponement; zero executions when disabled by default"
    requirement: LIVE-09
    verification:
      - kind: unit
        ref: "tests/unit/indexing/test_watcher.py#TestIdleCheckpoint (4 tests: due-once, busy-skip-no-warnings, recent-burst postponement, disabled-default zero executions — all pass)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Schedule-failure warn with remedy (D-17): ENOSPC at start or via rescope logs exactly one warning carrying errno cause + fs.inotify.max_user_watches remedy, sibling roots keep watching, failed root retried by the tick without spam, no reconcile enqueued for unwatched root"
    requirement: LIVE-08
    verification:
      - kind: unit
        ref: "tests/unit/indexing/test_watcher.py#TestScheduleFailure (2 tests: start-path retry cycle, rescope-add isolation — pass)"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-11-07
status: complete
---

# Phase 13 Plan 01: Watch-Core Growth (Rescope / Checkpoint / Schedule-Failure) Summary

**FileWatcher grown into the long-lived-host substrate: live rescope of the watched collection set (exact-set diff, reconcile-on-add, documents preserved on removal), idle PRAGMA wal_checkpoint(TRUNCATE) riding the tick with busy/recent-burst skips, and ENOSPC schedule failures that warn once with the inotify remedy — plus the mcp_watch/rescope/checkpoint settings fields.**

## Performance
- **Duration:** 25min | **Started:** 2026-11-07T14:39:09Z | **Completed:** 2026-11-07T15:04:56Z | **Tasks:** 2 | **Files modified:** 3
- **Suite:** 1071 passed @ 95.95% coverage (fail_under=90); ruff check/format green; ty check src/sif 0 diagnostics
- **Estimate vs actual:** 35000 tokens estimated, 10833 actual (chars/4 over the realized diff) — estimate confidence was "low"; the Phase 12 core's analogs were closer than expected

## Accomplishments
- **D-15 live rescope:** `FileWatcher.rescope(collections)` diffs the host's eligible set exactly — added roots arm a debouncer + watch handle and enqueue the recovery-return-shaped reconcile job (verified end-to-end: a file under the new root becomes indexed); removed roots unschedule, stop their debouncer, and keep every document row. Foreground host untouched (`src/sif/cli/commands/watch.py` has zero diff) — restart-on-change behavior preserved because rescope is opt-in via `rescope_provider`.
- **D-16 idle checkpoint:** `_checkpoint_if_due`/`_checkpoint_if_idle` run the TRUNCATE pragma on the worker's own connection only when `checkpoint_interval > 0` and the deadline elapsed; a busy result row skips silently (zero warning records asserted), a job completed within the restat window postpones a full interval, and the default configuration executes zero checkpoints across driven ticks (shutdown checkpoint from 12-D14 stays the final word).
- **D-17 schedule-failure handling:** `_schedule_watch` returns bool; an OSError (ENOSPC class) logs one warning per failure episode carrying `[errno] strerror` plus the `fs.inotify.max_user_watches` remedy, and every caller (start, recovery return-path, rescope add) treats False like a missing root — state stays retryable, no reconcile for a root that is not actually watched, tick retries without spam.
- **D-04 settings:** `mcp_watch=False` (inert until 13-03 wires the MCP host), `watch_rescope_interval=60.0` (ge=1), `watch_checkpoint_interval=300.0` (ge=0); SIF_ env spellings verified.

## Task Commits
Each task followed RED → GREEN with machine-validated RED evidence (`gsd_run check tdd-red-evidence` → RED_EVIDENCE_OK, junit format):

1. **Task 1: Live rescope end-to-end (tracer)** — `3148535` (test: failing rescope/settings battery) → `8406715` (feat: rescope + tick integration + settings)
   - Tracer feedback gate: all three `<verify>` commands re-run end-to-end after the tracer commit — 6/6 selection green, settings defaults green, 98 indexing tests green. `⚡ Tracer verified end-to-end — expanding.`
2. **Task 2: Idle checkpoint + schedule-failure warn** — `09229b2` (test: failing checkpoint/schedule-failure battery) → `8b8e5f5` (feat: D-16 checkpoint + D-17 warn)

**Plan metadata:** `see final docs commit below` (docs(13-01): complete watch-core growth plan)

## Files Created/Modified
- `src/sif/indexing/watcher.py` — rescope/_unschedule_removed/_schedule_added; _on_tick/_rescope_if_due/_checkpoint_if_due/_checkpoint_if_idle; _schedule_watch → bool with warn-once OSError handling; _WatchState gains debouncer + schedule_warned; stop() iterates states' debouncers; _run_job records _last_job_at
- `src/sif/config/settings.py` — mcp_watch, watch_rescope_interval, watch_checkpoint_interval (Watch settings block)
- `tests/unit/indexing/test_watcher.py` — TestLiveRescope (4), TestWatchSettings (2), TestIdleCheckpoint (4), TestScheduleFailure (2); module helpers _seed_collections/_CheckpointSpy

## Decisions Made
- Rescope-within-the-filter (open question 1): the provider returns only the host's eligible set; `rescope` is an exact-set diff so a `-c` host can never gain an excluded collection — pinned by test (gamma registered-but-withheld never scheduled).
- Deadline machinery seeds lazily on the first tick and resets on every due fire — skips postpone a full interval, never retry inside the tick (Pitfall 7 discipline generalized).
- The recovery-tick "returned" warning moved inside the successful-reschedule branch: with D-17 failures persisting, warning before the attempt would repeat every tick while `state.missing` stays True.
- `WatchConfig.now` (default `time.monotonic`) is the injectable clock seam — the whole tick battery is zero-timing (no sleeps anywhere in the new tests).
- Warn-once is per failure episode: `schedule_warned` resets on a successful schedule so a later exhaustion warns again.

## Deviations from Plan
**[Rule 2 - Missing critical functionality] Worker-thread failure guards** — Found during: Tasks 1-2 | Issue: an exception from `rescope_provider()` or the checkpoint pragma propagates out of `_on_tick` and silently kills the worker thread of a months-long daemon (the tick call site has no try/except) | Fix: provider call wrapped (warning + keep current watch set), checkpoint pragma wrapped (sqlite3.Error → one warning); happy path unchanged | Files: src/sif/indexing/watcher.py | Verification: full suite green; provider failure path exercised by guard structure | Commit: 8406715 (provider guard), 8b8e5f5 (checkpoint guard)

**Total deviations:** 1 auto-fixed (Rule 2, two guards). **Impact:** none on planned behavior; protects the long-lived-host invariant that the worker thread cannot die from one tick-side failure.

## TDD Gate Compliance

| Task | RED commit | RED evidence | GREEN commit | REFACTOR |
|------|-----------|--------------|--------------|----------|
| 1 (tracer) | `3148535` | RED_EVIDENCE_OK (junit; target: test_rescope_added_collection_schedules_and_reconciles, AttributeError on missing rescope API) | `8406715` | none needed |
| 2 | `09229b2` | RED_EVIDENCE_OK (junit; target: test_checkpoint_runs_once_when_due, assert 0 == 1 — zero checkpoint executions) | `8b8e5f5` | none needed |

Both GREEN commits are preceded by their RED commits; every RED was machine-validated before production edits. No violations.

## Issues Encountered
- Test-authoring bugs found and fixed inside the RED/GREEN loops (not production deviations): the added-root test consumed its own job via `get_nowait` before draining (re-queued); the removed-root test initially double-started the watcher (rebuilt cleanly with distinct handles); the busy-skip test skipped the deadline-seeding tick (added it). One `-k` selector near-miss: the D-17 start test was renamed to `test_schedule_failure_at_start_...` so the plan's `-k "checkpoint or schedule_failure or inotify"` verify selects it.
- RED evidence classifier rejects pytest's plain/quiet text output ("Unsupported report format"); pytest's built-in `--junit-xml` is the working evidence format for this project.

## User Setup Required
None - no external service configuration required. (All new behavior is opt-in via WatchConfig/Settings; nothing changes for existing users until 13-02/13-03 wire hosts.)

## Known Stubs
None. `mcp_watch` is intentionally inert until 13-03 consumes it — this is the plan's declared scope ("the field is inert until then; no MCP behavior changes in this plan"), not a stub: the field, default, and SIF_MCP_WATCH env spelling are delivered and verified here.

## Next Phase Readiness
Ready for 13-02/13-03 (Wave 2): both hosts construct `WatchConfig(rescope_provider=<filter-respecting collections-table read>, rescope_interval=settings.watch_rescope_interval, checkpoint_interval=settings.watch_checkpoint_interval)` and embed the unchanged start/stop contract. The foreground host needs no change (restart-on-change preserved). 13-04 must register the three new settings fields in the generator's SECTIONS allowlist and regenerate docs (fields are deliberately unregistered here so the docs gate stays green until that plan).

---
*Phase: 13-watch-everywhere-mcp-embedded-refresh-background-daemon*
*Completed: 2026-11-07*
