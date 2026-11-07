---
phase: 12-sif-watch-foreground-mvp
plan: 01
subsystem: indexing
tags: [watch, watchdog, event-debouncer, incremental-indexing, flock, click-cli, sqlite]

requires:
  - phase: 11-02
    provides: IncrementalIndexer shared core (per-file BEGIN IMMEDIATE transactions, progress-event protocol) and index_lock per-DB flock
provides:
  - Working `sif watch` foreground command — startup reconcile (D-03), live observer pipeline, SIGINT/SIGTERM graceful exit 0
  - IncrementalIndexer.update_paths(collection, paths, ...) — the per-path targeted update API (D-06) consumed by Phase 13/14 hosts
  - D-11 missing-root guard in update_collection AND update_paths — the verified latent mass-delete bug is closed
  - FileScanner.matches — the ONE shared scan/watch exclusion predicate (D-07), DEFAULT_IGNORE_PATTERNS gains editor-noise entries (D-08)
  - Rewritten sif.indexing.watcher — fold_events/FoldResult/WatchConfig/IndexingEventHandler/FileWatcher with per-burst flock (D-04)
  - watch_debounce_interval + watch_ignore_patterns settings fields
affects: [12-02, 12-03, 13-daemon-mcp, 14-precommand]

actuals:
  tokens: 24760   # chars/4 over the realized 0099159..10d652a diff (99043 chars, uv.lock churn included)
  tasks: 2
  commits: 4      # MEASURED: git rev-list --count 0099159..10d652a

plan_head_before: 0099159a0c30407e882f0f3b458456f384b803b5
plan_head_after: 10d652a1e0ba66212fd58ee11416883b87f32d69

tech-stack:
  added: []   # zero-new-deps lock held; watchdog range tightened to >=4.0.0,<7.0.0 only
  patterns:
    - "Settled-callback contract: the EventDebouncer callback runs under its condition lock, so it only folds + enqueues; one worker thread owns all DB access"
    - "Fold algebra is order-independent: created/modified -> index set, deleted -> remove set, moved -> dest index + src remove, then remove -= index (a both-touched-and-deleted path stays an index candidate; update_paths' stat decides)"
    - "Disk is truth, events are hints: every candidate is stat-checked; a gone index candidate is still removed by the stat, so cancellation never loses a removal"

key-files:
  created:
    - src/sif/cli/commands/watch.py
    - tests/integration/test_watch_e2e.py
  modified:
    - src/sif/indexing/watcher.py
    - src/sif/indexing/incremental.py
    - src/sif/indexing/scanner.py
    - src/sif/config/settings.py
    - src/sif/cli/main.py
    - tests/unit/indexing/test_watcher.py
    - tests/unit/indexing/test_incremental.py
    - tests/unit/indexing/test_scanner.py
    - pyproject.toml
    - uv.lock

key-decisions:
  - "FileWatcher keyword tunables bundled into a WatchConfig dataclass: the plan's 8-parameter constructor trips ruff PLR0913 (max-args 5) and the project has a no-noqa culture; 12-02 flags extend the struct without touching call sites"
  - "fold_events resolves a path present in both candidate sets toward the INDEX candidate (remove_candidates -= index_candidates): the plan's atomic-save truth demands empty remove_candidates, order-independence rules out last-event-wins, and update_paths' stat still removes the path if it is gone — nothing is lost"
  - "The e2e test waits for the banner line printed AFTER watcher.start() (subprocess runs python -u): polling the seed row alone leaves a lost-event window between the per-file reconcile commit and observer arming"
  - "EventDebouncer interval wrapped in cast(int, ...): upstream 6.0.0 annotates int but the value only flows into Condition.wait(timeout=...), which accepts floats (source-verified)"
  - "Docs regeneration (make docs-generate) deliberately NOT run here: the research constraint assigns the docs-regen step to the final plan (12-03), so the full-suite docs gate stays red until 12-03 — recorded in the WINDOWS ledger"

patterns-established:
  - "Watch hosts construct FileWatcher(collections, conn, db_path, WatchConfig(...)) and render progress events themselves; the core stays Rich-free"
  - "update_paths is the targeted-update seam for every host: stat-decides semantics, cost proportional to burst size, never a collection scan"

requirements-completed: [LIVE-01, LIVE-02, LIVE-03, LIVE-04, LIVE-11]  # shared IDs: REQUIREMENTS.md checkboxes stay unchecked until 12-02/12-03 finish (shared-ID gate); LIVE-11 watcher-level recovery (D-12) is 12-02 scope

coverage:
  - id: D1
    description: "LIVE-01 tracer: a real `sif watch` subprocess indexes a file created after startup reconcile with no manual update; SIGINT exits 0"
    requirement: LIVE-01
    verification:
      - kind: integration
        ref: "tests/integration/test_watch_e2e.py#test_watch_indexes_new_file_end_to_end"
        status: pass
    human_judgment: false
  - id: D2
    description: "Fold semantics: temp-noise exclusion through the shared predicate, atomic-save 5-event chain -> final path only with zero remove-candidates, moved dest/src rule, dir-moved reconcile flag, order-independence"
    requirement: LIVE-02
    verification:
      - kind: unit
        ref: "tests/unit/indexing/test_watcher.py#TestFoldEvents"
        status: pass
      - kind: unit
        ref: "tests/unit/indexing/test_watcher.py#TestWatchPipeline#test_atomic_save_chain_one_index_op_removed_zero"
        status: pass
    human_judgment: false
  - id: D3
    description: "Per-path update API (D-06/D-10): add/update/remove via stat, checksum-skip as unchanged, WR-01 purge-before-delete, stats tail; D-11 missing-root guard on both update paths preserves every document"
    requirement: LIVE-11
    verification:
      - kind: unit
        ref: "tests/unit/indexing/test_watcher.py#TestUpdatePaths"
        status: pass
      - kind: unit
        ref: "tests/unit/indexing/test_incremental.py#TestUpdatePathsReplay#test_replaying_settled_batch_is_all_unchanged"
        status: pass
    human_judgment: false
  - id: D4
    description: "LIVE-04 exclusion parity: DEFAULT_IGNORE_PATTERNS editor-noise entries; scan() membership equals matches() truth over a parametrized tree incl. root-level files; watch_ignore_patterns extends BOTH"
    requirement: LIVE-04
    verification:
      - kind: unit
        ref: "tests/unit/indexing/test_scanner.py#TestSharedPredicate"
        status: pass
    human_judgment: false
  - id: D5
    description: "LIVE-02 burst coalescing + D-04 per-burst flock: 5-event burst -> exactly one update_paths call; index_lock enter/exit around each job, never a lifetime hold"
    requirement: LIVE-02
    verification:
      - kind: unit
        ref: "tests/unit/indexing/test_watcher.py#TestWatchPipeline#test_save_burst_coalesces_to_one_update_paths_call"
        status: pass
      - kind: unit
        ref: "tests/unit/indexing/test_watcher.py#TestWatchPipeline#test_lock_acquired_per_job_never_held_for_lifetime"
        status: pass
    human_judgment: false
  - id: D6
    description: "Foreground watch UX (D-13): startup reconcile output, live banner, per-batch summary lines — wording and feel need human eyes"
    verification: []
    human_judgment: true
    rationale: "Banner/summary wording and foreground feel are visual/UX judgment; automated tests assert exit codes and DB state only"

duration: 42 min
completed: 2026-11-07
status: complete
---

# Phase 12 Plan 01: `sif watch` Foreground MVP — Tracer Summary

**End-to-end `sif watch` slice: observer -> EventDebouncer -> fold -> worker -> per-burst flock -> update_paths, proven by a real-subprocess e2e test plus the shared-predicate, missing-root-guard, and watchdog-cap landings**

## Performance

- **Duration:** 42 min (08:59–09:42 UTC)
- **Started:** 2026-11-07T08:59:56Z
- **Completed:** 2026-11-07T09:42:25Z
- **Tasks:** 2/2
- **Files modified:** 12
- **Suite:** 1022 passed @ 94.72% coverage (fail_under=90 honored); ruff, format, ty all green; ONE planned docs-gate failure deferred to 12-03 (see Issues)

## TDD Gate Compliance

Task 1 (`type="tracer" tdd="true"`) ran the full RED→GREEN cycle with machine-verified RED evidence (`gsd_run check tdd-red-evidence` → `RED_EVIDENCE_OK`; record in `.planning/tmp/tdd-red-12-01-task1.json`, JUnit report embedded):

| Task | RED commit | RED failure (target test, planned reason) | GREEN commit |
|------|-----------|-------------------------------------------|--------------|
| 1 | `b356b23` test(12-01) | `test_watch_indexes_new_file_end_to_end`: seed-row poll deadline fired — the registered-but-zero-behavior watch command performs no reconcile; all 10 battery tests failed on their own assertions (no import errors, by design) | `4d46711` feat(12-01) |
| 2 | `b2c03ea` test(12-01) | Battery observed GREEN on arrival — see note below | (no implementation delta; dep cap in `10d652a` chore) |

**Task 2 unexpected-green investigation (tdd.md error-handling rule 1):** the battery was written and run BEFORE any Task 2 change; all 33 tests passed. Investigation outcome: every battery behavior was implemented by Task 1's GREEN in this same plan (`4d46711`) — Task 2's file list contains no src files by design; it is the proof battery plus the dependency cap. The plan-level RED/GREEN gate is satisfied by Task 1's `test`→`feat` sequence (ancestry verified: `b356b23` is an ancestor of `4d46711`).

REFACTOR: no separate commit — the refactor-shaped extractions (`_remove_document`, `_combined_ignore_patterns`, `WatchConfig`) landed inside GREEN as part of satisfying the lint gates; nothing changed after GREEN that needed one.

Tracer feedback gate: auto mode active → all three `<verify>` blocks re-run end-to-end after GREEN (targeted suites 10/10, `watch --help` rc 0, ruff rc 0) — ⚡ verified, expanded to Task 2.

## Accomplishments

- `sif watch` works end-to-end: startup reconcile per collection (D-03) BEFORE the observer arms, live banner, per-batch `indexed N · removed M · unchanged K` lines (D-13), first SIGINT/SIGTERM drains gracefully and exits 0, a second signal exits 130
- `IncrementalIndexer.update_paths` — the D-06 per-path API for Phase 13/14 hosts: stat-decides, cost proportional to burst, never scans the tree, checksum skips counted as `unchanged`, WR-01 purge-before-delete preserved via the extracted `_remove_document`
- D-11 missing-root guard in BOTH update paths: the verified latent mass-delete bug (`rglob` on a missing root sweeps every document) is regression-tested closed — `missing <name>` event added to the progress protocol
- One shared exclusion predicate: `FileScanner.matches` + `DEFAULT_IGNORE_PATTERNS` editor-noise entries (`*.sb-*`, `4913`, `.#*`, `*.tmp`) + `watch_ignore_patterns` settings extension applied to scan AND watch alike (A4) — parity proven by a parametrized-tree test
- Watcher rewritten as a host-agnostic pipeline: positional `EventDebouncer` (D-05), cheap under-lock settled callback, order-independent fold with dir-moved reconcile flag, single worker thread, per-burst `index_lock` (D-04)
- Watchdog capped `>=4.0.0,<7.0.0` (7.x dropped Python 3.10), `uv lock` refreshed, `uv lock --check` clean

## Task Commits

1. **Task 1 RED: failing tracer battery + importable skeleton** - `b356b23` (test)
2. **Task 1 GREEN: implement sif watch end-to-end pipeline** - `4d46711` (feat)
3. **Task 2: LIVE-02/03/04 proof battery and edge tests** - `b2c03ea` (test)
4. **Task 2: watchdog cap + uv.lock refresh** - `10d652a` (chore)

**Plan metadata:** final docs commit (below)

## Files Created/Modified

- `src/sif/cli/commands/watch.py` - NEW: watch_cmd host — reconcile→arm→banner→signal loop→stop; renders missing/error events and batch summaries
- `src/sif/indexing/watcher.py` - REWRITTEN: fold_events/FoldResult/WatchConfig/IndexingEventHandler (single-intake forwarder)/FileWatcher (debouncers, queue, worker, per-burst flock, bounded drain)
- `src/sif/indexing/incremental.py` - update_paths, unchanged field, _remove_document extraction, D-11 guard in update_collection + update_paths
- `src/sif/indexing/scanner.py` - matches() shared predicate, _combined_ignore_patterns (settings-extended), four noise patterns, _should_ignore → staticmethod
- `src/sif/config/settings.py` - watch_debounce_interval (0.5s, gt=0), watch_ignore_patterns (global shared-predicate extension)
- `src/sif/cli/main.py` - watch_cmd import + registration
- `tests/unit/indexing/test_watcher.py` - REWRITTEN: 16 tests (fold semantics + pipeline battery)
- `tests/integration/test_watch_e2e.py` - NEW: the LIVE-01 tracer proof
- `tests/unit/indexing/test_incremental.py` - replay idempotency test
- `tests/unit/indexing/test_scanner.py` - parity + settings-extension + patterns tests
- `pyproject.toml` / `uv.lock` - watchdog range cap + lock refresh

## Decisions Made

See key-decisions in frontmatter (WatchConfig bundling, fold cancellation algebra, e2e arming marker, EventDebouncer cast, docs-regen deferral).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking lint] WatchConfig dataclass replaces the plan's 8-parameter FileWatcher constructor**
- **Found during:** Task 1 (GREEN)
- **Issue:** `FileWatcher.__init__(collections, conn, db_path, *, debounce_interval, lock_timeout, depth, on_event, on_batch)` trips ruff PLR0913 (max-args 5); the project has a no-noqa exemption culture
- **Fix:** Bundled the keyword tunables/callbacks into `WatchConfig` (4-arg constructor); all plan semantics preserved, 12-02 flags extend the struct
- **Files modified:** src/sif/indexing/watcher.py, src/sif/cli/commands/watch.py
- **Verification:** ruff check + format clean; all pipeline tests pass
- **Committed in:** 4d46711

**2. [Rule 1 - Plan-spec reconciliation] Fold resolves both-set paths toward the index candidate**
- **Found during:** Task 1 (RED authoring)
- **Issue:** The plan's action text says "a path in both sets is correct and allowed", but its atomic-save truth/Test 3 demand `remove_candidates == set()` after the 5-event chain (which contains a trailing delete of the final path) — naive both-sets output would leave the final path in remove_candidates
- **Fix:** `remove_candidates -= index_candidates` after predicate filtering: order-independent, satisfies the truth, and lossless — update_paths stats index candidates and REMOVES them when gone (the plain-rename probe chain still yields removed=1 + added=1)
- **Files modified:** src/sif/indexing/watcher.py
- **Verification:** test_atomic_save_chain_folds_to_final_path_only, test_plain_rename_removes_old_adds_new_only, test_fold_is_order_independent
- **Committed in:** b356b23 (RED contract) / 4d46711 (behavior)

**3. [Rule 3 - Blocking] ty diagnostics on GREEN**
- **Found during:** Task 1 (GREEN gates)
- **Issue:** (a) `_should_ignore` is an instance method, called unbound from the static `matches`; (b) signal handler annotated `FrameType` but the stdlib stub says `FrameType | None`; (c) `EventDebouncer`'s 6.0.0 annotation says `int`, we pass a float
- **Fix:** (a) `_should_ignore` → `@staticmethod` (behavior-neutral; existing caller tests unaffected); (b) `FrameType | None`; (c) `cast(int, ...)` with a source-verified comment (runtime accepts floats)
- **Files modified:** src/sif/indexing/scanner.py, src/sif/cli/commands/watch.py, src/sif/indexing/watcher.py
- **Verification:** `ty check src/sif` 0 diagnostics
- **Committed in:** 4d46711

**4. [Rule 1 - Determinism] e2e waits for an explicit arming marker, not just the seed row**
- **Found during:** Task 1 (RED authoring)
- **Issue:** The plan's "poll seed row, then create the file" has a race: the seed row commits per-file BEFORE the stats tail/banner/observer.start() complete, so a file created in that window is missed by both the finished scan and the un-armed observer — a flaky LIVE-01 proof
- **Fix:** The banner prints AFTER `watcher.start()`; the subprocess runs `python -u` and the test polls stdout for "Watching" before creating the file
- **Files modified:** src/sif/cli/commands/watch.py, tests/integration/test_watch_e2e.py
- **Verification:** e2e passes deterministically (~2s wall)
- **Committed in:** b356b23 / 4d46711

---

**Total deviations:** 4 auto-fixed (2 Rule 3 blockers, 2 plan-spec/determinism adjustments)
**Impact on plan:** All within task scope; no architectural change, no scope creep. The plan's contracts (must_haves truths, artifacts, prohibitions) are all honored.

## Issues Encountered

- **Full-suite docs gate red by plan:** `tests/test_docs.py::test_cli_reference_has_all_commands` fails because `docs/cli-reference.md` does not yet list `watch`. The research constraint and 12-03's task list assign `make docs-generate` to the FINAL plan (12-03 owns the flags and the two remaining settings, then regenerates once); hand-editing is CI-gate-prohibited. Recorded in the WINDOWS ledger so it cannot be forgotten at ship time. Everything else: 1022 passed, coverage 94.72%.
- Single-file pytest runs trip the project-wide coverage addopts — partial suites run with `--no-cov` (established Phase 11 practice); the full-suite gate ran clean on plain pytest.

## Authentication Gates

None — no external services in this plan.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None — no placeholder bodies shipped. (The `depth` WatchConfig field is stored but BM25-only behavior is the plan's LIVE-05 default leg; `--embed` depth arrives in 12-02 by design.)

## Threat Flags

None — no security-relevant surface beyond the plan's threat model. All T-12-01..T-12-SC mitigations landed as specified (fsdecode/resolve/predicate intake, debounced+set-deduped bursts, no content in logs/output, resolved-root scheduling, D-11 guard, capped range with no new packages).

## Next Phase Readiness

- Ready for 12-02 (full D-14 shutdown machinery, --embed depth, -c filter, verbose, D-12 watcher-level recovery): FileWatcher's start/stop(flush=) contract and WatchConfig are the extension points
- Phase 13/14 hosts consume `update_paths(collection, paths, progress=...)` and the fold seam directly
- docs/cli-reference.md + docs/configuration.md regeneration is 12-03's first task (windows ledger entry open until then)

---
*Phase: 12-sif-watch-foreground-mvp*
*Completed: 2026-11-07*

## Self-Check: PASSED

All 12 key files exist on disk; all 4 task commits (b356b23, 4d46711, b2c03ea, 10d652a) are ancestors of HEAD; plan_head_before=0099159, plan_head_after=10d652a, commits measured = 4; evaluation-scope resolved 4 commits on this branch; requirements.ready-ids correctly blocks all five shared LIVE IDs pending 12-02/12-03 SUMMARYs.
