---
phase: 12-sif-watch-foreground-mvp
verified: 2026-11-12T07:52:11Z
status: passed
score: 12/12 must-haves verified
covered_files:
  - ".planning/phases/12-sif-watch-foreground-mvp/12-01-PLAN.md"
  - ".planning/phases/12-sif-watch-foreground-mvp/12-01-SUMMARY.md"
  - ".planning/phases/12-sif-watch-foreground-mvp/12-02-PLAN.md"
  - ".planning/phases/12-sif-watch-foreground-mvp/12-02-SUMMARY.md"
  - ".planning/phases/12-sif-watch-foreground-mvp/12-03-PLAN.md"
  - ".planning/phases/12-sif-watch-foreground-mvp/12-03-SUMMARY.md"
  - ".planning/phases/12-sif-watch-foreground-mvp/12-UAT.md"
  - "docs/cli-reference.md"
  - "docs/configuration.md"
  - "pyproject.toml"
  - "scripts/generate_config_ref.py"
  - "src/sif/cli/commands/search.py"
  - "src/sif/cli/commands/watch.py"
  - "src/sif/cli/error_handling.py"
  - "src/sif/cli/main.py"
  - "src/sif/config/settings.py"
  - "src/sif/database/factory.py"
  - "src/sif/indexing/incremental.py"
  - "src/sif/indexing/scanner.py"
  - "src/sif/indexing/watcher.py"
  - "tests/integration/test_watch_e2e.py"
  - "tests/unit/cli/test_watch_cmd.py"
  - "tests/unit/indexing/test_incremental.py"
  - "tests/unit/indexing/test_scanner.py"
  - "tests/unit/indexing/test_watcher.py"
  - "uv.lock"
covered_digest: "v4:sha256:a5059dd1becaebc088e5d6cc6281fa3720a424efe802146a2ddb36cc76889840"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 12/12
  gaps_closed: []
  gaps_remaining: []
  regressions: []
decision_coverage:
  honored: 15
  total: 15
  not_honored: []
---

# Phase 12: `sif watch` Foreground MVP — Verification Report

**Phase Goal:** Running `sif watch` in a terminal keeps the index current as files change — the first complete host of the live-index loop, proving events → incremental reindex end-to-end.
**Verified:** 2026-11-12T07:52:11Z
**Status:** passed
**HEAD:** b47f55f6c551aa61ddd124913f6fe9a2663da06a
**Re-verification:** Yes — staleness re-check after Phases 13–16.1 changed the watch host and shared indexing code. The previous frontmatter status was `passed`; its two UX items are now closed by `12-UAT.md` (2/2 passed).

## Goal Achievement

### Observable Truths

The five ROADMAP success criteria remain the non-negotiable contract, merged with the plans' distinct truths. Every behavior-dependent truth below was exercised by the verifier's fresh 108-test focused run at HEAD, not inferred from file presence or SUMMARY claims.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC1/LIVE-01: With `sif watch` running, add, edit, and delete are reflected without `sif index update` | VERIFIED | Fresh run of all six real-subprocess e2e tests passed, including `test_watch_indexes_new_file_end_to_end` and `test_watch_edit_and_delete_reflected_end_to_end`: real Observer/EventDebouncer, post-arming create, changed content+checksum, deleted row, fresh-connection assertions, SIGINT rc 0. `12-UAT.md` also records the new content as a real BM25 search hit. The Phase 16.1 `search.py` diff changed DB-open/constructor error boundaries, not search execution. |
| 2 | SC2a/LIVE-02: A 2–5 event editor-save burst coalesces into exactly one index operation | VERIFIED | `TestWatchPipeline::test_save_burst_coalesces_to_one_update_paths_call` and `test_atomic_save_chain_one_index_op_removed_zero` passed in the fresh run: five events produce one settled queue job and one `update_paths` invocation/result. Production path remains positional `EventDebouncer` → `_settled_callback` → one fold/enqueue (`watcher.py:398-437,735-754`). UAT item 2 separately observed one summary line for four rapid saves. |
| 3 | SC2b/LIVE-03: Atomic-save chains and moves/renames reconcile to the right document without a missed save or spurious rebuild | VERIFIED | Fresh fold, pipeline, and e2e proofs passed: `test_atomic_save_chain_folds_to_final_path_only`, `test_atomic_save_chain_one_index_op_removed_zero`, `test_plain_rename_removes_old_adds_new_only`, and real `os.replace` e2e. Fold still maps moved→dest index+src remove and subtracts index candidates from removals (`watcher.py:122-166`); atomic e2e retains exactly one final-path row with new content. |
| 4 | SC3/LIVE-04: Temp files never enter the index and watch exclusions are identical to scanner exclusions | VERIFIED | All 8 scanner tests and all watch temp-noise tests passed. `FileScanner.matches` and `scan()` both call `_combined_ignore_patterns` (`scanner.py:61-101,103-155`); the watch fold consumes that exact predicate (`watcher.py:742-752`). Defaults probe confirmed `*.swp`, `*.sb-*`, `4913`, `.#*`, `*.tmp`, `.DS_Store`, and `*~`. Real e2e indexed a control while never indexing noise. |
| 5 | SC4/LIVE-05: Default depth is BM25/FTS-only; `--embed` explicitly opts into vector updates | VERIFIED | Fresh CLI depth-matrix and eight-test embed battery passed. Defaults probe returned `bm25 / 0.5s / 5.0s / []`; bogus depth was rejected. Default burst wrote a document and zero chunks/vectors; embed bursts wrote both; lazy model load occurred only on first embed work. `_effective_depth` precedence remains flags then setting (`watch.py:255-266`). |
| 6 | SC5/LIVE-11: A missing root is not mass deletion; the index survives and recovers on return | VERIFIED | Both `update_collection` and `update_paths` retain early missing-root guards returning zero results (`incremental.py:106-115,198-206`). Fresh unit tests proved preservation/warn-once/rescheduling; real e2e renamed the root away and back, kept the process and rows alive, warned once, and indexed a new file after return. Phase 16.1's `enqueue_reconcile` routes the identical `FoldResult(needs_reconcile=True)` payload (`watcher.py:525-537,574-586`). |
| 7 | D-14 shutdown: first SIGINT/SIGTERM stops intake, performs one bounded flush and WAL truncate checkpoint, exits 0; second signal exits 130 | VERIFIED | Fresh signal/shutdown units and real e2e passed for both signals. E2e first proved non-empty WAL, then observed rc 0 and a 0-byte WAL with a parent reader held. `shutdown_watcher` stops once with `flush=True` and checkpoints only after `worker_joined()` (`watch.py:99-119`); second-signal `SystemExit(130)` remains at `watch.py:74-89`. Later liveness guards strengthen rather than weaken the invariant. |
| 8 | D-09: Embedding compute is outside write transactions; chunks+vectors commit in one short transaction inside the per-burst flock | VERIFIED | `test_embed_compute_runs_outside_any_write_transaction`, `test_embed_runs_inside_the_same_per_burst_lock_window`, and `test_reconcile_at_embed_depth_rewrites_purged_vectors` passed. Embed-time `conn.in_transaction` flags are all False; chunk-write flags are all True. `manager.embed` precedes `with self._conn` (`watcher.py:283-304`), and burst/reconcile embed legs remain inside `index_lock` (`watcher.py:787-848`). |
| 9 | D-04: Per-DB flock is acquired per settled burst/reconcile, never for process lifetime | VERIFIED | `test_lock_acquired_per_job_never_held_for_lifetime` passed with exact enter/exit, enter/exit observations. Current `_run_job` locks non-empty bursts and `_run_reconcile` locks each reconcile independently (`watcher.py:787-833`); no lock surrounds the worker loop. |
| 10 | CLI surface: repeatable `-c`, unknown-name error, depth flags, verbose/banner/batch output, zero-collections exit 0 | VERIFIED | Fresh 35-test CLI file passed. `watch --help` exited 0 and rendered `-c/--collection`, `--embed`, `--no-embed`, `--verbose` plus later lifecycle options; main help lists `watch`. `_select_collections` dedupes and raises `Collection 'name' not found`; zero collections returns before watcher construction. The shared opener still initializes the DB before selection (`watch.py:632-640`). |
| 11 | `IncrementalIndexer.update_paths` is targeted, stat-decides add/update/unchanged/delete, purges vectors before document delete, and never collection-scans | VERIFIED | All 10 incremental tests plus the watcher `TestUpdatePaths` battery passed. Current method resolves/dedupes only supplied paths, predicate-checks and stats each, uses `_process_file` or `_remove_document`, and has no `scan()` call (`incremental.py:162-267`). `_remove_document` retains vector-purge-before-delete in one transaction (`incremental.py:373-384`); replay remains all unchanged. |
| 12 | Docs/settings/dependency and full quality contract remains green | VERIFIED | Docs probes found `sif watch` and all four Phase 12 `SIF_WATCH_*` settings; generator still owns the Watch Settings section. Watchdog remains `>=4.0.0,<7.0.0`; `uv lock --check` passed. Verifier-run ruff check, format check, and `ty check src/sif` were clean. Orchestrator-confirmed full suite at this HEAD: 1591 passed, 1 skipped, 95.18% coverage; ruff/format/ty clean. |

**Score:** 12/12 truths verified (0 present-but-behavior-unverified, 0 overrides, 0 coincidental-reliance flags).

### Required Artifacts

The plan artifact/key-link entries are string-form; `verify.artifacts` and `verify.key-links` therefore returned `total: 0` for all three plans. Manual L1–L4 verification was performed instead, as in the prior report.

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/sif/cli/commands/watch.py` | Foreground host and CLI lifecycle | VERIFIED | 640 lines, substantive; real startup reconcile, watcher construction, banner, signal loop, shutdown, rendering. Later daemon/service options are additive. Registered at `main.py:93,106`. |
| `src/sif/indexing/watcher.py` | Observer→debounce→fold→worker→flock→incremental pipeline | VERIFIED | 898 lines; full implementation, no old log-only stub surface. Consumed by foreground and MCP hosts; 49 watcher tests passed. |
| `src/sif/indexing/incremental.py` | Shared targeted update core and missing-root guard | VERIFIED | 384 lines; real DB writes and stat-driven updates; 10 incremental + 5 targeted watcher tests passed. |
| `src/sif/indexing/scanner.py` | One shared scan/watch exclusion predicate | VERIFIED | 212 lines; `scan()` and `matches()` share pattern assembly and ignore evaluation; 8 scanner tests passed. |
| `src/sif/cli/error_handling.py` | Phase 16.1 shared DB opener adopted by watch | VERIFIED | 71 lines; constructs the caller's `Database`, initializes schema, translates only known open failures. Real e2e and zero-collection CLI paths passed through it. |
| `tests/integration/test_watch_e2e.py` | Real-FS acceptance battery | VERIFIED | 420 lines, six tests; all six passed in 20.28s together with the watch units. Real subprocesses, deadline-bounded fresh-connection outcome polls. |
| `tests/unit/indexing/test_watcher.py` | Fold/pipeline/recovery/embed/concurrency battery | VERIFIED | 2399 lines, 49 active tests; all passed, including new enqueue-routing and regression tests. |
| `tests/unit/cli/test_watch_cmd.py` | CLI/depth/signal/shutdown battery | VERIFIED | 688 lines, 35 active tests; all passed. |
| Watch settings and generated docs | Four Phase 12 settings plus current docs | VERIFIED | Defaults/validation probed directly; docs contain command/options and all four settings; tracked docs/source have no uncommitted drift. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| Observer | `IndexingEventHandler` → positional `EventDebouncer` | `_schedule_watch` and `on_any_event` | WIRED | `watcher.py:169-187,398-437`; each collection schedules only its resolved registered root. |
| Settled events | `fold_events` → queue → single worker | `_settled_callback`, `_worker_loop` | WIRED | `watcher.py:735-785`; callback only folds/enqueues, worker owns DB work. |
| Worker | `index_lock` → `update_paths` / `update_collection` | `_run_job`, `_run_burst`, `_run_reconcile` | WIRED | `watcher.py:787-848`; empty folds do no DB work; per-job lock proven behaviorally. |
| `FileScanner.matches` | Scan and watch fold | `_combined_ignore_patterns` and `partial(scanner.matches, ...)` | WIRED | `scanner.py:100-155`; `watcher.py:742-752`; parity and e2e noise proofs passed. |
| CLI startup | Reconcile before observer arming | `run_watch_host` | WIRED | `watch.py:162-225`; all startup reconciles complete before `watcher.start()` and the post-arming banner. |
| Phase 16.1 opener | Initialized DB → collection selection → same host body | `open_initialized_database` | WIRED | `watch.py:632-640`; helper still invokes `init_schema()` (`error_handling.py:31-66`). No event/update invariant changed by the diff. |
| Recovery return | Public `enqueue_reconcile` → full reconcile job | `recovery_tick` | WIRED | `watcher.py:525-537,574-586`; routing spies, FIFO/payload test, and real recovery e2e passed. Payload is unchanged. |
| Signal handler | Stop flag → bounded flush → worker-liveness gate → WAL checkpoint | `run_watch_host`, `shutdown_watcher` | WIRED | `watch.py:74-119,221-231`; both signal e2e cases and second-signal 130 unit passed. |
| Embed worker | BM25 commit → embed outside txn → chunk/vector txn | `_run_burst`, `_EmbedSession.embed_documents` | WIRED | `watcher.py:249-310,835-848`; transaction and lock ordering tests passed. |
| Real CLI subprocess | Real Observer/Debouncer/DB → fresh assertions | e2e spawner | WIRED | `test_watch_e2e.py:76-141`; six real end-to-end outcomes passed on Darwin/FSEvents at HEAD. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| e2e assertions | document content/checksum/rows | Real watch subprocess through `update_paths` | Yes | FLOWING |
| Fold candidates | index/remove path sets | Real or synthetic watchdog events through `fold_events` | Yes | FLOWING |
| CLI batch lines | added/updated/removed/unchanged | `IncrementalResult` returned by the active indexer | Yes | FLOWING |
| Banner depth/debounce | effective settings and flags | Pydantic Settings plus `_effective_depth` | Yes | FLOWING |
| Recovery jobs | collection + reconcile intent | Root re-stat transitions through `enqueue_reconcile` | Yes | FLOWING |
| Docs watch sections | Click options and Settings fields | `make docs-generate` generator inputs | Yes | FLOWING |

No static result, hardcoded document data, or disconnected production path was found. Embedding mocks exist only at the external model boundary in unit tests; the real e2e and DB assertions use actual indexing code.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Complete watch unit + real-FS acceptance battery | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/test_watcher.py tests/unit/cli/test_watch_cmd.py tests/integration/test_watch_e2e.py --no-cov` | 90 passed in 20.28s (49 watcher, 35 CLI, 6 e2e) | PASS |
| Shared predicate + incremental core | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/test_scanner.py tests/unit/indexing/test_incremental.py --no-cov` | 18 passed in 0.16s | PASS |
| CLI help and registration | `python -m sif.cli.main watch --help`; main `--help` | rc 0; all Phase 12 options visible; `watch` listed | PASS |
| Defaults and invalid settings | Direct `Settings()` / `WatchConfig()` probes | bm25 defaults; foreground rescope+periodic checkpoint disabled; bogus depth rejected | PASS |
| Shared editor-noise patterns | Direct `DEFAULT_IGNORE_PATTERNS` probe | All required patterns present | PASS |
| Lint/format/types | Focused `ruff check`, `ruff format --check`; `ty check src/sif` | All clean | PASS |
| Lockfile | `uv lock --check` | Passed | PASS |
| Docs and dependency surface | Grep docs and `pyproject.toml` | Watch command present; four settings present; watchdog cap intact | PASS |
| Working-tree drift | `git diff --exit-code -- <covered source/tests/docs>` | No tracked drift | PASS |

The full workspace suite was not re-run by this verifier. Its supplied HEAD result is 1591 passed, 1 skipped at 95.18%; the verifier independently ran the 108 phase-relevant tests above.

### Probe Execution

SKIPPED — no `scripts/*/tests/probe-*.sh` files exist and no Phase 12 plan or summary declares one. The acceptance evidence is the pytest unit/integration battery above.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| LIVE-01 | 12-01, 12-02, 12-03 | Add/edit/delete automatically reindex without manual update | SATISFIED | Fresh create/edit/delete e2e plus search UAT |
| LIVE-02 | 12-01, 12-03 | Save storm coalesces to one operation | SATISFIED | Fresh invocation-count tests; UAT one-line storm observation |
| LIVE-03 | 12-01, 12-03 | Atomic-save and rename/move reconciliation | SATISFIED | Fresh fold, rename, and real `os.replace` tests |
| LIVE-04 | 12-01, 12-03 | Temp exclusions identical to scanner | SATISFIED | Fresh parity and e2e noise tests |
| LIVE-05 | 12-02 | BM25 default; explicit embed opt-in | SATISFIED | Fresh depth matrix and embed/default tests |
| LIVE-11 | 12-01, 12-02, 12-03 | Missing root preserved and recovered | SATISFIED | Fresh guard, recovery, enqueue-routing, and e2e tests |

No orphaned requirements: REQUIREMENTS.md maps exactly LIVE-01..05 and LIVE-11 to Phase 12, and every ID is declared by at least one plan.

### Decision Coverage

All trackable CONTEXT.md decisions are honored by shipped artifacts: 15/15 honored, 0 not honored. Gate result: `All trackable CONTEXT.md decisions are honored by shipped artifacts.` This gate is non-blocking.

### Prohibitions Verification

The plans' prohibitions are judgment-tier (`flagged-unverified`). Current deterministic evidence supports the following non-authoritative verifier judgments; none was silently treated as a test-tier gate.

| Prohibition | Verdict | Current evidence |
|-------------|---------|------------------|
| Never hold the per-DB flock for process lifetime | NOT VIOLATED | Per-job enter/exit test passed; no loop-lifetime lock in source |
| No extension-only event filtering bypassing the scanner predicate | NOT VIOLATED | Fold receives `scanner.matches`; parity/e2e tests passed |
| Never watch broader than registered roots | NOT VIOLATED | `observer.schedule` uses each selected collection's resolved root only |
| Missing root never means mass deletion | NOT VIOLATED | Both core guards plus fresh unit/e2e preservation proofs |
| Embedding compute never inside an open write transaction | NOT VIOLATED | Runtime `conn.in_transaction` assertions passed |
| No live rescope in the foreground MVP | NOT VIOLATED | Foreground passes no provider; `WatchConfig` default is None/0 and no-provider test passed. Later daemon opt-in is Phase 13 scope. |
| No new runtime dependencies introduced by Phase 12 | NOT VIOLATED | Phase 12 commit `10d652a` changed only watchdog's existing range; current cap and lock check pass. Later-phase dependencies are out of scope. |
| Generator-owned docs never hand-edited | NOT VIOLATED | Generator carries Watch Settings; docs/source tracked diff is empty and full docs gate is green |
| Embed leg not split outside the per-burst flock | NOT VIOLATED | Burst and reconcile lock-window tests passed |
| No periodic checkpoint in the foreground MVP | NOT VIOLATED | Foreground leaves `checkpoint_interval=0`; disabled-by-default test passed. Phase 13 daemon opt-in does not alter foreground behavior. |
| E2E never uses unbounded sleep-polling or raw event-sequence assertions | NOT VIOLATED | Test review: outcome polls have deadlines; fixed sleeps are bounded post-outcome settles; assertions concern DB/output/WAL outcomes |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No TBD/FIXME/XXX, TODO/HACK/PLACEHOLDER, stub phrases, empty production implementations, or disabled requirement tests in the current phase files | — | None |

`tests/unit/indexing/test_incremental.py:117` contains a conditional `pytest.skip` only when sqlite-vec cannot be imported. It did not skip in this environment: all 18 scanner/incremental tests ran and passed, so it is not a disabled requirement proof.

### Advisory (New Scope, Unevidenced)

None. Re-verification produced no new unevidenced blocker or advisory finding.

### Test Quality Audit

| Test File | Linked Requirement | Active | Skipped in Fresh Run | Circular | Assertion Level | Verdict |
|-----------|--------------------|--------|----------------------|----------|-----------------|---------|
| `tests/integration/test_watch_e2e.py` | LIVE-01/02/03/04/11, D-14 | 6 | 0 | 0 | Behavioral: real process, content/checksum/rows, exit codes, WAL bytes | PASS |
| `tests/unit/indexing/test_watcher.py` | LIVE-02/03/04/05/11, D-04/09 | 49 | 0 | 0 | Value/behavioral: call counts, queue payloads, transaction flags, lock ordering | PASS |
| `tests/unit/cli/test_watch_cmd.py` | LIVE-01/05, D-13/14 | 35 | 0 | 0 | Value/behavioral: depth, selection, signal state, checkpoint/liveness | PASS |
| `tests/unit/indexing/test_scanner.py` | LIVE-04 | 8 | 0 | 0 | Value: exact set equality and pattern membership | PASS |
| `tests/unit/indexing/test_incremental.py` | LIVE-01/05/11 and replay | 10 | 0 | 0 | Value/behavioral: real rows, counts, replay and purge behavior | PASS |

Disabled requirement proofs: 0. Circular expected-value generation: 0; file bodies and expected counts are independently authored, while fresh DB connections observe actual results. Insufficient assertions: 0. The transaction-boundary, per-job lock, FIFO reconcile, and real signal/WAL tests directly exercise ordering and cleanup invariants rather than merely checking symbols.

### Human Verification Required

None outstanding. `12-UAT.md` is complete with 2/2 passed and 0 issues:

1. Foreground banner, batch/verbose output, coalesced real saves, and Ctrl-C behavior passed.
2. A four-save `--embed` storm produced one summary line; final content was both the top BM25 hit and a vector hit; no temp rows appeared; SIGINT exited 0.

These previously manual-only items are evidence for UX/search closure, not substitutes for the fresh code and test checks above.

### Gaps Summary

No gaps and no regressions. The Phase 16.1 opener substitution preserves `Database` construction + schema initialization and the existing command body; the reconcile-helper substitution enqueues the same needs-reconcile payload. All five ROADMAP success criteria, all seven additional plan/lock/CLI/docs truths, all artifacts, key links, data flows, and all six requirement IDs hold at HEAD b47f55f. Independent evidence: 108 focused tests passed, plus CLI/settings/docs probes and clean ruff/format/ty/lock checks. Supplied full-suite evidence at the same HEAD is also green. The phase goal remains achieved.

---

_Verified: 2026-11-12T07:52:11Z_
_Verifier: Claude (gsd-verifier)_
