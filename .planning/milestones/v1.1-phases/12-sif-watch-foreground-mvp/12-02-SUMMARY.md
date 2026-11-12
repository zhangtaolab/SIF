---
phase: 12-sif-watch-foreground-mvp
plan: 02
subsystem: indexing
tags: [watch, click-cli, signals, wal-checkpoint, embedding, sqlite-vec, flock, recovery]

requires:
  - phase: 12-01
    provides: FileWatcher/WatchConfig pipeline with per-burst flock, update_paths targeted API, D-11 missing-root guard, fold_events/FoldResult needs_reconcile shape
provides:
  - Complete `sif watch` CLI surface — repeatable -c/--collection filter, --embed/--no-embed depth matrix (LIVE-05), --verbose per-file rendering, D-02 restart-documented help
  - Full D-14 shutdown machinery — SignalState/make_signal_handler (first signal graceful, second SystemExit 130 no flush), shutdown_watcher (ONE bounded flush + PRAGMA wal_checkpoint(TRUNCATE) on the quiesced worker connection, try/finally), SIGINT/SIGTERM sharing one routine
  - D-12 missing-root recovery in the watcher — per-collection _WatchState, recovery_tick warn-once transitions, unschedule/reschedule, full-reconcile job on return, worker idle queue.get(timeout=restat_interval) as the re-stat cadence
  - Inline embed depth (D-09) in the watch worker — lazy EmbeddingManager, probe-free first-use dimension check (fail-soft disable + error event), chunk+embed OUTSIDE any write transaction, one short vector-write txn, whole leg inside the same per-burst flock window
  - Settings fields watch_update_depth (validated {bm25, embed}) and watch_restat_interval (5.0s, ge=0.1)
affects: [12-03, 13-daemon-mcp, 14-precommand]

actuals:
  tokens: 15700   # chars/4 over the realized f0d2ada..b222831 src+tests diff (62816 chars)
  tasks: 2
  commits: 4      # MEASURED: git rev-list --count f0d2ada..b222831

plan_head_before: f0d2ada0b02deff063ed8656fca33cb3bce336cc
plan_head_after: b222831a23b8d2b3a37365591ceac13b218a51e0

tech-stack:
  added: []   # zero new dependencies; stdlib signal/queue/re only
  patterns:
    - "D-09 embed-outside-txn host shape: BM25 commit -> checksum-diff changed set -> chunk+embed with no txn -> one short vector-write txn, all inside the per-burst flock"
    - "Depth precedence: --embed > --no-embed > settings.watch_update_depth; no flag + default setting never embeds (LIVE-05 invariant, unit-pinned)"
    - "Bounded shutdown independent of tunables: a stop sentinel wakes the worker's re-stat-timeout idle wait so the D-14 join never waits out the interval"
    - "Recovery as idle cadence: the worker's queue.get(timeout=restat_interval) doubles as the D-12 re-stat loop; transitions warn once, never per poll"

key-files:
  created:
    - tests/unit/cli/test_watch_cmd.py
  modified:
    - src/sif/cli/commands/watch.py
    - src/sif/indexing/watcher.py
    - src/sif/config/settings.py
    - tests/unit/indexing/test_watcher.py

key-decisions:
  - "Reconcile jobs (dir moves, returning missing roots) stay BM25-only at embed depth: the per-file embed leg needs a computable changed-path set, which only burst jobs have; a returning root reaches BM25-fresh immediately and vectors catch up on the next per-file burst or a manual sif embed"
  - "Changed paths are detected by checksum before/after snapshots around the BM25 leg (added: None->checksum, updated: old->new) — precise classification without touching IncrementalIndexer's Phase 11 contract"
  - "Worker stop sentinel: with the re-stat interval as the idle wait, an env-tuned long restat would otherwise delay the D-14 bounded stop past the join timeout; the sentinel keeps shutdown bounded for any setting"
  - "RED-evidence targetTest must be the bare method name: pytest's JUnit splits class into classname, so a dotted class.method target reads as no_target_test_failure"
  - "Partial-suite verify runs use --no-cov (same as 12-01): the project-wide coverage addopts + fail_under=90 make single-dir runs fail on the coverage floor, not on tests; the full suite with coverage ran green at plan level"

patterns-established:
  - "Watch hosts render depth mode in the banner ('BM25-only' / 'embed') and pass effective depth + restat interval into WatchConfig; the worker owns what depth means"
  - "Signal machinery is module-level and directly invocable (SignalState/make_signal_handler/shutdown_watcher) so unit tests drive D-14 semantics without real signals"

requirements-completed: [LIVE-01, LIVE-05, LIVE-11]

coverage:
  - id: D1
    description: "CLI surface (D-01/D-02/D-13): repeatable -c filter with update_cmd unknown-name wording, zero-collections notice + exit 0 + no watcher, --help lists all flags with the restart note"
    requirement: LIVE-01
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_watch_cmd.py#TestHelpSurface"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_watch_cmd.py#TestCollectionFilter"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_watch_cmd.py#TestZeroCollections"
        status: pass
    human_judgment: false
  - id: D2
    description: "LIVE-05 depth matrix: default bm25; --embed forces on; --no-embed forces off over the setting; SIF_WATCH_UPDATE_DEPTH=embed activates embed; invalid values fail settings validation"
    requirement: LIVE-05
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_watch_cmd.py#TestDepthMatrix"
        status: pass
    human_judgment: false
  - id: D3
    description: "D-14 shutdown: first SIGINT/SIGTERM sets the stop flag, second raises SystemExit 130; shutdown does one bounded flush then executes PRAGMA wal_checkpoint(TRUNCATE); both signals share one routine and the TERM path exits 0"
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_watch_cmd.py#TestSignalMachinery"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_watch_cmd.py#TestShutdownRoutine"
        status: pass
    human_judgment: false
  - id: D4
    description: "D-12 recovery: vanished root marked missing (warn once across ticks, handle unscheduled, documents never swept); return reschedules + enqueues one full-reconcile job (warn once); a burst for a missing root hits the D-11 guard with zero counts"
    requirement: LIVE-11
    verification:
      - kind: unit
        ref: "tests/unit/indexing/test_watcher.py#TestRecoveryTick"
        status: pass
    human_judgment: false
  - id: D5
    description: "D-09/D-10 embed depth: default burst writes document + zero chunks/vectors; embed depth writes chunks (document_id/sequence) + vectors; embed() observes conn.in_transaction False while chunk writes observe the open txn closing after; dimension mismatch fails soft (one error event, session-disabled, BM25 continues); model lazy-loads once; the leg spans the same lock window as BM25"
    requirement: LIVE-05
    verification:
      - kind: unit
        ref: "tests/unit/indexing/test_watcher.py#TestEmbedDepth"
        status: pass
    human_judgment: false
  - id: D6
    description: "Foreground watch UX wording (D-13): banner depth/debounce lines and --verbose per-file lines — wording and feel need human eyes"
    verification: []
    human_judgment: true
    rationale: "Banner/verbose wording and foreground feel are visual/UX judgment; automated tests assert flags, depth plumbing, and exit codes only"

duration: 34 min
completed: 2026-11-07
status: complete
---

# Phase 12 Plan 02: `sif watch` Foreground MVP — Full Host Summary

**Complete foreground host around the 12-01 pipeline: tiered --embed depth with embedding computed outside any write transaction, signal-driven shutdown with WAL truncate checkpoint, repeatable -c filtering, and missing-root recovery — all unit-proven with machine-verified TDD gates**

## Performance

- **Duration:** 34 min (09:59–10:33 UTC)
- **Started:** 2026-11-07T09:59:17Z
- **Completed:** 2026-11-07T10:33:01Z
- **Tasks:** 2/2
- **Files modified:** 5
- **Suite:** 1044 passed @ 95.79% coverage (fail_under=90 honored); ruff, format, ty all green; ONE planned docs-gate failure unchanged from 12-01 (ledgered, 12-03 owns the regen)

## TDD Gate Compliance

Both tasks ran the full RED→GREEN cycle with machine-verified RED evidence (`gsd_run check tdd-red-evidence` → `RED_EVIDENCE_OK`):

| Task | RED commit | RED failure (target test, planned reason) | GREEN commit |
|------|-----------|-------------------------------------------|--------------|
| 1 | `9c4f5bb` test(12-02) | `test_shutdown_stops_once_with_flush_and_checkpoints`: PRAGMA wal_checkpoint(TRUNCATE) never executed — 11 battery tests failed on their own assertions against the importable skeleton (records: `.planning/tmp/tdd-red-12-02-task1.json`) | `66ad67a` feat(12-02) |
| 2 | `e423a00` test(12-02) | `test_embed_depth_writes_chunks_and_vectors`: zero chunk/vector rows — the worker ignores depth; 5 of 6 failed, the LIVE-05 default invariant legitimately green pre-implementation (record: `.planning/tmp/tdd-red-12-02-task2.json`) | `b222831` feat(12-02) |

REFACTOR: no separate commits — the extract-shaped work (`_run_burst`, `_checksums`/`_path_changed`, `_schedule_watch`, `_EmbedSession`) landed inside GREEN as part of satisfying the complexity/lint gates; nothing changed after GREEN that needed one.

Tracer feedback gate (12-01) does not apply — both tasks are `type="auto" tdd="true"`; auto mode was active and every `<verify>` block was re-run end-to-end after GREEN (targeted suites, sibling CLI suite, full indexing suite, e2e, ruff, ty).

## Accomplishments

- Full CLI surface (D-01/D-02/D-13): repeatable `-c/--collection` with update_cmd's unknown-name ClickException, zero-collections notice + exit 0 without starting the watcher, `--verbose` per-file lines vs default per-batch `indexed N · removed M · unchanged K`, banner listing roots + depth mode + debounce, help documenting the restart requirement
- LIVE-05 depth matrix unit-pinned: `--embed` forces on, `--no-embed` forces off, else `SIF_WATCH_UPDATE_DEPTH` (validated to {bm25, embed}); no flag + default setting never embeds
- D-14 shutdown machinery: module-level, directly invocable signal state/handler (first signal graceful, second SystemExit 130 without flush), `shutdown_watcher` performing ONE bounded flush then `PRAGMA wal_checkpoint(TRUNCATE)` on the quiesced worker connection inside try/finally; SIGINT and SIGTERM share the routine; the exception path stops intake with no flush
- D-12 recovery: `_WatchState` per collection; `recovery_tick` marks a vanished root missing (one warning per transition, watch unscheduled, documents never swept) and on return reschedules + enqueues one full-reconcile job; the worker's idle `queue.get(timeout=restat_interval)` doubles as the re-stat cadence
- D-09 embed leg in the worker (IncrementalIndexer untouched): lazy `EmbeddingManager` load at first embed work, probe-free dimension check against the vec0 FLOAT[n] schema with fail-soft session disable, checksum-diff changed-path detection, chunk+embed with NO write transaction open, one short vector-write txn (chunk rows + `add_embeddings_batch`), all inside the same per-burst flock window as the BM25 leg
- The 12-01 e2e proof still passes unchanged (banner arming marker + SIGINT exit 0) — the new shutdown path is a strict extension

## Task Commits

1. **Task 1 RED: failing watch host battery + importable skeleton** - `9c4f5bb` (test)
2. **Task 1 GREEN: CLI surface, D-14 shutdown, D-12 missing-root recovery** - `66ad67a` (feat)
3. **Task 2 RED: failing embed-depth battery** - `e423a00` (test)
4. **Task 2 GREEN: inline embed depth outside write transactions** - `b222831` (feat)

**Plan metadata:** final docs commit (below)

## Files Created/Modified

- `tests/unit/cli/test_watch_cmd.py` - NEW: 13 CLI tests (help surface, filter, zero-collections, depth matrix, signal machinery, shutdown routine incl. command-level TERM proof)
- `src/sif/cli/commands/watch.py` - full host: flags, depth matrix helpers, banner depth mode, verbose rendering, D-14 signal/shutdown machinery
- `src/sif/indexing/watcher.py` - D-12 recovery (_WatchState/_schedule_watch/recovery_tick, restat cadence, stop sentinel), D-09 embed leg (_EmbedSession, _run_burst, checksum change detection)
- `src/sif/config/settings.py` - watch_update_depth (validated) + watch_restat_interval fields
- `tests/unit/indexing/test_watcher.py` - +8 tests (2 recovery, 6 embed-depth battery)

## Decisions Made

See key-decisions in frontmatter (reconcile-stays-BM25 scoping, checksum-snapshot change detection, stop sentinel, JUnit targetTest form, --no-cov partial runs).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Partial-suite verify commands run with --no-cov**
- **Found during:** Task 1 verify
- **Issue:** The plan's literal `python -m pytest tests/unit/cli/test_watch_cmd.py ...` inherits the project-wide `--cov` addopts and `fail_under=90`, so single-dir runs fail the coverage floor even with all tests passing (established 12-01 issue)
- **Fix:** Targeted/sibling runs use `--no-cov`; the full suite WITH coverage ran at plan level: 1044 passed @ 95.79%
- **Files modified:** none (execution detail)
- **Verification:** full-suite green above
- **Committed in:** n/a (process)

**2. [Rule 2 - Bounded shutdown] Worker stop sentinel added**
- **Found during:** Task 1 GREEN (worker loop rewrite)
- **Issue:** Making the idle wait `queue.get(timeout=watch_restat_interval)` per the plan means the D-14 stop join could wait out the full interval; an env-tuned long restat (ge=0.1, no max) would exceed the join timeout and risk worker/drain overlap
- **Fix:** `stop()` enqueues a None sentinel that wakes the parked worker immediately; `_drain_once` skips sentinels — bounded shutdown now independent of the restat value (T-12-06 mitigation strengthened)
- **Files modified:** src/sif/indexing/watcher.py
- **Verification:** all recovery/pipeline tests green; stop(flush=False) used in recovery tests exercises the path
- **Committed in:** 66ad67a

**3. [Rule 1 - Test determinism] Write-txn spy records after the DML**
- **Found during:** Task 2 GREEN (txn-boundary test)
- **Issue:** The first `DocumentChunkRepository.create` spy recorded `in_transaction=False` — Python's legacy sqlite3 defers the implicit BEGIN to the first DML, so a pre-insert read still sees autocommit
- **Fix:** Spy records after calling the original create; assertion still proves the write txn is open at chunk-write time and that embed-time flags (pre-DML) are all False
- **Files modified:** tests/unit/indexing/test_watcher.py
- **Verification:** test_embed_compute_runs_outside_any_write_transaction green
- **Committed in:** b222831 (amended to fold the spy fix into the GREEN commit)

---

**Total deviations:** 3 auto-fixed (1 Rule 3 blocker, 1 Rule 2 shutdown-correctness, 1 Rule 1 determinism)
**Impact on plan:** All within task scope; no architectural change. Every must-have truth, artifact, key_link, and prohibition is honored (embed never inside a txn; flock per burst only; no live rescope; embed not split outside the flock; no periodic checkpoint; docs untouched).

## Issues Encountered

- Full-suite docs gate red by plan (unchanged from 12-01): `tests/test_docs.py::test_cli_reference_has_all_commands` stays red until 12-03 runs `make docs-generate`; hand-editing is CI-prohibited. Already ledgered in `.planning/WINDOWS.md` (entry #9, open). Everything else: 1044 passed @ 95.79%.
- RED-evidence classifier rejected the first Task 1 record (`no_target_test_failure`) because the targetTest used dotted `class.method` while pytest's JUnit puts the class in `classname` — bare method name validated on retry; recorded as a key decision for future plans.

## Authentication Gates

None — no external services in this plan.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None — no placeholder bodies shipped. (Reconcile jobs at embed depth intentionally stay BM25-only; see Decisions — that is D-09 scoping, not a stub.)

## Threat Flags

None — no security-relevant surface beyond the plan's threat model. All register rows mitigated and tested: T-12-06 bounded shutdown (sentinel + try/finally checkpoint + 130 path), T-12-07 depth inversion (LIVE-05 matrix unit-pinned incl. the settings-validation failure), T-12-08 error-event payloads carry model/dimension messages and paths only — document content never enters event payloads.

## Next Phase Readiness

- Ready for 12-03: the CLI surface is final (flags, settings fields all landed), so `make docs-generate` will pick up `sif watch` with -c/--collection, --embed, --no-embed, --verbose and the four watch_* settings; e2e + shutdown + recovery all proven at unit/e2e level for the SC5 verification pass
- Phase 13 hosts inherit: `WatchConfig` (depth/restat tunables), the D-14 shutdown precedent (bounded flush + WAL checkpoint + 130), and the D-09 embed-leg discipline (per-burst inline, compute outside txn)
- D-10's accepted lock-hold trade-off and the embed-outside-flock split remain deferred Phase 13 revisits, per the plan's prohibitions

---
*Phase: 12-sif-watch-foreground-mvp*
*Completed: 2026-11-07*

## Self-Check: PASSED

All 5 key files exist on disk; all 4 task commits (9c4f5bb, 66ad67a, e423a00, b222831) are ancestors of HEAD; plan_head_before=f0d2ada, plan_head_after=b222831, commits measured = 4; full suite 1044 passed @ 95.79% with only the ledgered docs-gate failure; requirements.ready-ids correctly released LIVE-05 (sole declarer) and held LIVE-01/LIVE-11 (shared with 12-03, no SUMMARY yet).
