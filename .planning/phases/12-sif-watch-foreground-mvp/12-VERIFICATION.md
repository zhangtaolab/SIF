---
phase: 12-sif-watch-foreground-mvp
verified: 2026-11-07T11:47:04Z
status: passed
score: 12/12 must-haves verified
covered_files:
  [
    ".planning/phases/12-sif-watch-foreground-mvp/12-01-PLAN.md",
    ".planning/phases/12-sif-watch-foreground-mvp/12-01-SUMMARY.md",
    ".planning/phases/12-sif-watch-foreground-mvp/12-02-PLAN.md",
    ".planning/phases/12-sif-watch-foreground-mvp/12-02-SUMMARY.md",
    ".planning/phases/12-sif-watch-foreground-mvp/12-03-PLAN.md",
    ".planning/phases/12-sif-watch-foreground-mvp/12-03-SUMMARY.md",
    "docs/cli-reference.md",
    "docs/configuration.md",
    "pyproject.toml",
    "scripts/generate_config_ref.py",
    "src/sif/cli/commands/watch.py",
    "src/sif/cli/main.py",
    "src/sif/config/settings.py",
    "src/sif/indexing/incremental.py",
    "src/sif/indexing/scanner.py",
    "src/sif/indexing/watcher.py",
    "tests/integration/test_watch_e2e.py",
    "tests/unit/cli/test_watch_cmd.py",
    "tests/unit/indexing/test_incremental.py",
    "tests/unit/indexing/test_scanner.py",
    "tests/unit/indexing/test_watcher.py",
    "uv.lock",
  ]
covered_digest: "v4:sha256:1641e43c98e57bd643eb1702fbef5824d637698caf5572e403005b1d56120fa8"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Run `sif watch` on a real notes collection in a terminal, save a file from a real editor, and watch the output for a minute; then Ctrl-C once and confirm the exit feel"
    expected: "Banner (roots, depth mode, debounce) is readable; each settled save produces exactly one `indexed N · removed M · unchanged K` line; `--verbose` per-file lines are legible; a single Ctrl-C exits cleanly and promptly"
    why_human: "Terminal output wording/readability and live-update feel are visual/UX judgment — automated tests assert exit codes and DB state only (executor-deferred D6 in 12-01 and 12-02 SUMMARYs)"
  - test: "With `sif watch --embed` running on a small real collection, make 3-4 rapid saves of the same note in a real editor (Vim/Emacs/VSCode) and search for the newest content afterwards"
    expected: "Each save storm coalesces to one summary line (no line flooding), the final content is searchable via `sif search`, and no temp-file rows ever appear"
    why_human: "Real-editor event storms on the developer's own machine are the LIVE-02 end-user reality; e2e covers the probed os.replace chain and synthetic bursts, but real editor timing/feel cannot be asserted programmatically"
---

# Phase 12: `sif watch` Foreground MVP — Verification Report

**Phase Goal:** Running `sif watch` in a terminal keeps the index current as files change — the first complete host of the live-index loop, proving events → incremental reindex end-to-end.
**Verified:** 2026-11-07T11:47:04Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

Merged must-haves: the 5 ROADMAP success criteria (non-negotiable contract) plus the plans' distinct truths (deduplicated; plan wording that restates an SC rolls up under the SC). Behavior-dependent truths were verified by RUNNING the named test that exercises the transition/invariant (single named tests, never the full suite), not by symbol presence.

| #   | Truth                                                                                                                                                                                                                                                                                                                              | Status     | Evidence                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | SC1/LIVE-01: With `sif watch` running, adding, editing, and deleting files are reflected in the index without `sif index update`                                                                                                                                                                                                  | ✓ VERIFIED | e2e `test_watch_indexes_new_file_end_to_end` RUN by verifier — passed in 1.49s (real CLI subprocess, real Observer, fresh-connection row/content poll, SIGINT rc 0). Edit/delete leg: `test_watch_edit_and_delete_reflected_end_to_end` exists (collected), asserts checksum change + content + row removal; full-suite green (1050 passed @ 95.79%) on this exact tree per pre-dispatch run; working tree clean (git status empty for src/tests/docs)                                                                                                                                                                                                                                                                                                              |
| 2   | SC2a/LIVE-02: A 2-5 event editor-save burst coalesces into exactly one index operation                                                                                                                                                                                                                                             | ✓ VERIFIED | `TestWatchPipeline::test_atomic_save_chain_one_index_op_removed_zero` RUN by verifier — passed; asserts exactly one `update_paths` invocation through a wrapping spy on the settled-callback path. `test_save_burst_coalesces_to_one_update_paths_call` and `test_empty_fold_never_calls_update_paths_single_event_works` also present (16-test battery)                                                                                                                                                                                                                                                                                                                                                                                                           |
| 3   | SC2b/LIVE-03: macOS atomic-save rename chains plus moves/renames reconcile to the right document (no missed saves, no spurious delete + rebuild)                                                                                                                                                                                  | ✓ VERIFIED | `test_plain_rename_removes_old_adds_new_only` RUN by verifier — passed (removed=1 + added=1, no other docs touched). Fold algebra verified in `src/sif/indexing/watcher.py:100-144` (moved → dest index + src remove; `remove_candidates -= index_candidates`; order-independent). e2e `test_watch_atomic_save_leaves_exactly_one_row` (real `os.replace`, exactly one row, never observed wiped) exists and passed in the green suite                                                                                                                                                                                                                                                                                                                           |
| 4   | SC3/LIVE-04: Temp files (`.swp`, `.sb-*`, `4913`, `.DS_Store`, etc.) never enter the index — exclusions identical to scanner ignore_patterns                                                                                                                                                                                        | ✓ VERIFIED | `TestSharedPredicate::test_scan_membership_equals_matches_over_parametrized_tree` RUN by verifier — passed (scan() membership == matches() truth incl. root-level files). `DEFAULT_IGNORE_PATTERNS` contains `*.sb-*`/`4913`/`.#*`/`*.tmp`/`.DS_Store`/`*.swp` confirmed via `python -c`. `watch_ignore_patterns` extends BOTH scan and matches via `_combined_ignore_patterns` (`scanner.py:142-155`). e2e `test_watch_temp_noise_never_indexed` (control file indexed, noise never) exists, green in suite                                                                                                                                                                                                                                              |
| 5   | SC4/LIVE-05: Default update depth is BM25/FTS only; `--embed` explicitly opts into vector updates (embedding never runs as a background default)                                                                                                                                                                                  | ✓ VERIFIED | `TestEmbedDepth::test_default_depth_writes_document_but_zero_chunks_and_vectors` RUN by verifier — passed (doc row written, 0 chunks, 0 vectors). Depth matrix unit-pinned in `tests/unit/cli/test_watch_cmd.py::TestDepthMatrix` (default bm25, --embed on, --no-embed over setting, SIF_WATCH_UPDATE_DEPTH=embed); verifier additionally confirmed `SIF_WATCH_UPDATE_DEPTH=bogus` is rejected by settings validation, and `Settings()` defaults are bm25/5.0/0.5/[]                                                                                                                                                                                                                            |
| 6   | SC5/LIVE-11: A collection root that disappears is not treated as mass deletion — the index survives and recovers when the root returns                                                                                                                                                                                            | ✓ VERIFIED | Three legs, two RUN by verifier: `TestUpdatePaths::test_missing_root_returns_zero_emits_missing_and_preserves_docs` — passed (D-11 guard in `incremental.py:111-120,191-199` on BOTH update paths); e2e `test_watch_missing_root_recovery` — passed in 6.01s (real subprocess: rows intact, process alive, `disappeared` warned exactly once across 2+ re-stat ticks, reindex on return). `TestRecoveryTick::test_disappear_marks_missing_warns_once_preserves_docs` also RUN — passed. Recovery loop code: `watcher.py:392-424`                                                                                                                                                    |
| 7   | D-14 shutdown: first SIGINT/SIGTERM → stop flag → ONE bounded flush → `PRAGMA wal_checkpoint(TRUNCATE)` → exit 0; second signal exits 130 immediately                                                                                                                                                                             | ✓ VERIFIED | `TestSignalMachinery::test_second_signal_raises_system_exit_130` RUN by verifier — passed. `shutdown_watcher` (`watch.py:77-88`) verified: stop(flush=True) then checkpoint in try/finally. e2e `test_watch_clean_exits_truncate_wal` (both signals rc 0, pre-proven non-empty WAL → 0-byte after exit, parent-held reader) exists, green in suite. Single `wal_checkpoint` occurrence in src/ — shutdown only, no periodic checkpoint                                                                                                                                                                                                                                                                                                                            |
| 8   | D-09: Embedding compute never runs inside an open write transaction; chunks+vectors persist in one short closing txn; whole leg inside the per-burst flock window                                                                                                                                                                 | ✓ VERIFIED | `TestEmbedDepth::test_embed_compute_runs_outside_any_write_transaction` RUN by verifier — passed with behavioral assertions (embed-time `conn.in_transaction` flags all False; chunk-write-time flags all True; txn closed after). Code: `watcher.py:248-268` — embed at line 256 outside the `with self._conn:` block at line 258; `embed_documents` called inside `_run_burst`'s `index_lock` window (`watcher.py:489-509`)                                                                                                                                                                                                                                                                               |
| 9   | D-04: The per-DB flock is acquired per settled burst, never held for the process lifetime                                                                                                                                                                                                                                         | ✓ VERIFIED | `TestWatchPipeline::test_lock_acquired_per_job_never_held_for_lifetime` RUN by verifier — passed (lock enter/exit observed around each job, zero lifetime hold). Code: `index_lock` wraps `_run_job` (`watcher.py:484,489`)                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 10  | CLI surface: `-c/--collection` repeatable with update_cmd's unknown-name error, `--embed`/`--no-embed`/`--verbose`, zero-collections notice + exit 0, banner (roots/depth/debounce), per-batch summary lines                                                                                                                                                       | ✓ VERIFIED | `watch --help` RUN by verifier — renders all four options + restart note, rc 0; `--help` command list includes `watch`. `watch.py:153-278` verified: `multiple=True` on -c, `ClickException(f"Collection '{name}' not found")`, banner after `watcher.start()` (D-03 arming marker), `_render_batch` prints `indexed N · removed M · unchanged K`. Unit battery `tests/unit/cli/test_watch_cmd.py` (13 tests) covers filter/zero-collections/depth/signals/shutdown                                                                                                                                                                                              |
| 11  | `IncrementalIndexer.update_paths`: stat-decides per path (exists+changed → re-index, unchanged → skipped/unchanged, gone → vector-purge-then-doc-delete), cost proportional to len(paths), never a collection scan                                                                                                                                                                                | ✓ VERIFIED | Code `incremental.py:164-247` verified line-by-line: predicate skip, per-path stat branch, `_remove_document` (WR-01 purge-before-delete preserved), stats tail; no `scan()` call anywhere in the method. Unit battery `TestUpdatePaths` (5 tests) + `TestUpdatePathsReplay::test_replaying_settled_batch_is_all_unchanged` (idempotency) present; missing-root leg RUN by verifier — passed                                                                                                                                                                                                                                                                                                       |
| 12  | Docs regenerated by `make docs-generate` only (`sif watch` + options in cli-reference.md; four watch_* settings in configuration.md); full quality gate green (pytest fail_under=90, ruff, format, ty)                                                                                                                              | ✓ VERIFIED | Verifier re-ran greps: `sif watch` in cli-reference.md → 1 (line 656, options table); `SIF_WATCH_*` settings in configuration.md → 4 (lines 107-110). Docs changed only in commit `64efc8c` (regenerate + generator script `scripts/generate_config_ref.py` SECTIONS/default_factory fixes) — no hand edits. Gate: full suite 1050 passed @ 95.79% pre-dispatch on this tree (working tree clean); verifier re-ran `ruff check` on phase files (clean) and `uv lock --check` (clean); 12 individual tests + 2 `python -c` probes + 3 CLI invocations all green                                                                                                                                                     |

**Score:** 12/12 truths verified (0 present, behavior-unverified)

### Required Artifacts

All artifact levels checked manually (the plans' frontmatter artifacts/key_links are string-form, which `verify.artifacts`/`verify.key-links` could not parse — total 0; manual L1-L4 verification performed instead).

| Artifact                                                          | Expected                                                        | Status      | Details                                                                                                                            |
| ----------------------------------------------------------------- | --------------------------------------------------------------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `src/sif/cli/commands/watch.py`                                   | The `sif watch` foreground host                                 | ✓ VERIFIED  | 279 lines, substantive (flags, depth matrix, signal machinery, shutdown, banner); registered in `main.py:106`; renders via `_render_batch` |
| `src/sif/indexing/watcher.py` (rewritten)                         | Host-agnostic pipeline: fold/debouncer/worker/recovery/embed leg | ✓ VERIFIED  | 541 lines; old stub surface (`_should_handle`, `extensions=`) gone (grep clean); imported by watch.py and 1143-line test battery     |
| `tests/integration/test_watch_e2e.py`                             | Real-FS e2e battery (SC1-5)                                     | ✓ VERIFIED  | 420 lines, 6 tests collected; deadline-bounded outcome polls; no watchdog event-sequence assertions; verifier ran 2 of 6 (passed)   |
| `tests/unit/indexing/test_watcher.py` (rewritten)                 | Fold + pipeline + recovery + embed unit battery                 | ✓ VERIFIED  | 1143 lines, 22 tests across 5 classes; verifier ran 6 individually (all passed)                                                     |
| `tests/unit/cli/test_watch_cmd.py`                                | CLI unit battery                                                | ✓ VERIFIED  | 243 lines, 13 tests; verifier ran the 130-path test (passed)                                                                        |
| `settings` fields watch_update_depth / watch_restat_interval (+ 12-01's watch_debounce_interval / watch_ignore_patterns) | Validated settings fields                          | ✓ VERIFIED  | `settings.py:44-65,181-194`; defaults and validation re-executed by verifier (bm25/5.0/0.5/[]; bogus depth rejected)                 |
| Expanded e2e battery / docs / generator script                    | 12-03 artifacts                                                 | ✓ VERIFIED  | See truth 12; `scripts/generate_config_ref.py` carries the Watch Settings SECTIONS entry                                            |

### Key Link Verification

| From                          | To                                                    | Via                                                                                                 | Status    | Details                                                                                                        |
| ----------------------------- | ----------------------------------------------------- | --------------------------------------------------------------------------------------------------- | --------- | -------------------------------------------------------------------------------------------------------------- |
| Observer                      | IndexingEventHandler → EventDebouncer (positional)    | `watcher.py:357-364`, `on_any_event` → `handle_event`                                               | ✓ WIRED   | Single-intake forwarder; positional EventDebouncer construction (D-05) verified in source                       |
| Debounced events              | fold_events → queue → single worker thread            | `_settled_callback` → `fold_events` → `queue.put` (`watcher.py:442-445`) → `_worker_loop`           | ✓ WIRED   | Callback only folds + enqueues (condition-lock safe); worker owns all DB access                                 |
| Worker                        | index_lock → IncrementalIndexer.update_paths          | `_run_job` → `index_lock` → `_run_burst` → `update_paths` (`watcher.py:484-510`)                   | ✓ WIRED   | Per-burst lock proven by named test; per-file txn inside `update_paths` (Phase 11 core)                          |
| FileScanner.matches           | both scan() and the watch fold                        | fold `should_track` partial (`watcher.py:435-440`), `update_paths` predicate (`incremental.py:212`) | ✓ WIRED   | One shared predicate; no extension-only check anywhere in watcher.py (grep verified); parity test passed        |
| cli.main                      | watch_cmd registration; reconcile BEFORE observer arms| `main.py:94,106`; `watch.py:218-258` (reconcile loop precedes `watcher.start()`)                   | ✓ WIRED   | D-03 ordering verified in source; e2e "Watching" marker printed after arming                                    |
| Signal handler                | stop flag → stop(flush=True) → wal_checkpoint → exit  | `watch.py:52-88,268-273`                                                                            | ✓ WIRED   | try/finally checkpoint; second-signal 130 test passed; exception path stops intake without flush               |
| Worker embed leg              | BM25 commit → embed outside txn → short vector-write txn | `_run_burst` → `_EmbedSession.embed_documents` (`watcher.py:497-510,248-268`)                     | ✓ WIRED   | D-09 boundary behaviorally proven (test passed); same per-burst lock window spans both legs                     |
| Worker idle wait              | D-12 re-stat loop                                     | `queue.get(timeout=restat_interval)` → `recovery_tick()` (`watcher.py:453-458`)                    | ✓ WIRED   | Stop sentinel keeps shutdown bounded; recovery e2e passed                                                       |
| Real CLI subprocess           | real Observer → real DB → fresh-connection assertions | e2e spawner (`test_watch_e2e.py:76-141`)                                                            | ✓ WIRED   | Verifier ran 2 e2e tests end-to-end (tracer, recovery) — real subprocesses, real FSEvents                        |
| make docs-generate            | docs/cli-reference.md + docs/configuration.md         | `Makefile` target + `scripts/generate_config_ref.py`                                                | ✓ WIRED   | Generator carries watch surface; docs changed only in the regenerate commit                                     |

### Data-Flow Trace (Level 4)

| Artifact                          | Data Variable        | Source                                        | Produces Real Data | Status      |
| --------------------------------- | -------------------- | --------------------------------------------- | ------------------ | ----------- |
| e2e assertions                    | documents rows       | real subprocess writes via update_paths       | Yes                | ✓ FLOWING   |
| fold candidates                   | index/remove sets    | real watchdog events → fold_events            | Yes                | ✓ FLOWING   |
| CLI batch summary lines           | added/updated/removed/unchanged | IncrementalResult returned by update_paths | Yes                | ✓ FLOWING   |
| banner depth/debounce             | settings fields      | Pydantic Settings (env-overridable)          | Yes                | ✓ FLOWING   |
| docs watch sections               | CLI/settings surface | generator script reading click/pyproject     | Yes                | ✓ FLOWING   |

No static returns, hardcoded data, or mocks anywhere in the production path (mocks exist only at the EmbeddingManager boundary in unit tests, by design).

### Behavioral Spot-Checks

| Behavior                                                        | Command                                                                                                                    | Result            | Status  |
| --------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- | ----------------- | ------- |
| LIVE-01 tracer: post-startup file indexed, SIGINT rc 0          | `pytest tests/integration/test_watch_e2e.py::test_watch_indexes_new_file_end_to_end` (verifier-run)                        | 1 passed, 1.49s   | ✓ PASS  |
| SC5/LIVE-11 recovery: docs survive, warn-once, reindex on return| `pytest tests/integration/test_watch_e2e.py::test_watch_missing_root_recovery` (verifier-run)                              | 1 passed, 6.01s   | ✓ PASS  |
| LIVE-02 coalescing: one index op for a 5-event atomic-save burst| `pytest ...::test_atomic_save_chain_one_index_op_removed_zero` (verifier-run)                                              | 1 passed          | ✓ PASS  |
| LIVE-03 rename: removed=1 + added=1, no other docs              | `pytest ...::test_plain_rename_removes_old_adds_new_only` (verifier-run)                                                    | 1 passed          | ✓ PASS  |
| LIVE-04 parity: scan() == matches() over parametrized tree      | `pytest ...::TestSharedPredicate::test_scan_membership_equals_matches_over_parametrized_tree` (verifier-run)                | 1 passed          | ✓ PASS  |
| LIVE-05 default: doc row, zero chunks/vectors                   | `pytest ...::test_default_depth_writes_document_but_zero_chunks_and_vectors` (verifier-run)                                | 1 passed          | ✓ PASS  |
| LIVE-11 guard: missing root → zero counts, docs preserved       | `pytest ...::TestUpdatePaths::test_missing_root_returns_zero_emits_missing_and_preserves_docs` (verifier-run)               | 1 passed          | ✓ PASS  |
| D-09: embed() never inside a write txn                          | `pytest ...::test_embed_compute_runs_outside_any_write_transaction` (verifier-run)                                          | 1 passed          | ✓ PASS  |
| D-04: lock per job, never lifetime                              | `pytest ...::test_lock_acquired_per_job_never_held_for_lifetime` (verifier-run)                                            | 1 passed          | ✓ PASS  |
| D-12: disappear marks missing, warns once, preserves docs       | `pytest ...::TestRecoveryTick::test_disappear_marks_missing_warns_once_preserves_docs` (verifier-run)                       | 1 passed          | ✓ PASS  |
| D-14: second signal → SystemExit 130                            | `pytest ...::TestSignalMachinery::test_second_signal_raises_system_exit_130` (verifier-run)                                 | 1 passed          | ✓ PASS  |
| CLI surface renders                                             | `python -m sif.cli.main watch --help`; `--help` command list                                                                | rc 0; watch listed | ✓ PASS  |
| Settings defaults + validation                                  | `python -c` Settings probes (defaults; `SIF_WATCH_UPDATE_DEPTH=bogus` rejected)                                             | OK                | ✓ PASS  |
| Scanner noise patterns                                          | `python -c` DEFAULT_IGNORE_PATTERNS probe                                                                                   | OK                | ✓ PASS  |
| Docs content                                                    | greps: `sif watch` → 1; `SIF_WATCH_*` → 4                                                                                   | 1 / 4             | ✓ PASS  |
| Lint + lock                                                     | `ruff check` (phase files); `uv lock --check`                                                                               | clean / clean     | ✓ PASS  |

12 single named tests + 6 command probes executed by the verifier, all green. The full 1050-test suite result is supplied by the orchestrator's pre-dispatch run on this identical tree (working tree verified clean); it was not re-run per the at-most-once rule.

### Probe Execution

Step 7c: SKIPPED — no `scripts/*/tests/probe-*.sh` probes are declared by the plans or exist in the repo for this phase (probe-exact event sequences from 12-RESEARCH.md were encoded as synthetic test fixtures instead, per D-15).

### Requirements Coverage

| Requirement | Source Plan             | Description                                                                                  | Status      | Evidence                                                                                                    |
| ----------- | ----------------------- | -------------------------------------------------------------------------------------------- | ----------- | ----------------------------------------------------------------------------------------------------------- |
| LIVE-01     | 12-01, 12-02, 12-03     | add/edit/delete auto-reindex without manual `sif index update`                                | ✓ SATISFIED | e2e tracer + edit/delete tests; tracer RUN by verifier                                                       |
| LIVE-02     | 12-01, 12-03            | 2-5 event save storm coalesces to one index operation                                         | ✓ SATISFIED | coalescing spy test RUN by verifier; burst battery                                                            |
| LIVE-03     | 12-01, 12-03            | atomic-save rename chains + moves/renames reconcile correctly                                 | ✓ SATISFIED | fold algebra + rename test RUN by verifier; e2e single-row proof in green suite                               |
| LIVE-04     | 12-01, 12-03            | temp files excluded identically to scanner ignore_patterns                                    | ✓ SATISFIED | parity test RUN by verifier; patterns probe; e2e noise test                                                   |
| LIVE-05     | 12-02                   | BM25-only default; `--embed` explicit opt-in                                                  | ✓ SATISFIED | default-depth test RUN by verifier; depth matrix unit-pinned; settings validation probe                      |
| LIVE-11     | 12-01, 12-02, 12-03     | missing root never read as mass deletion; recovery on return                                  | ✓ SATISFIED | guard test + recovery tick test + e2e recovery all RUN by verifier (3/3 passed)                               |

No orphaned requirements: REQUIREMENTS.md maps exactly LIVE-01..05 + LIVE-11 to Phase 12; every ID appears in at least one plan's `requirements` frontmatter, and REQUIREMENTS.md marks all six `[x] Complete`. (LIVE-06/07 → Phase 11, LIVE-08/09 → Phase 13, LIVE-10 → Phase 14 — correctly out of scope.)

### Decision Coverage

All trackable CONTEXT.md decisions are honored by shipped artifacts: 15/15 honored, 0 not honored (gate output appended; non-blocking by design).

### Prohibitions Verification (LLM-judge, non-authoritative)

All plan prohibitions are judgment-tier (`flagged-unverified` at plan time). Deterministic enforcement evidence was gathered for each; verdicts below are verifier judgments backed by that evidence — `unverified-prohibition — human review recommended` if any is disputed.

| Prohibition                                                                            | Verdict          | Enforcement evidence                                                                                                           |
| -------------------------------------------------------------------------------------- | ---------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Never hold the per-DB flock for the process lifetime (D-04)                            | NOT VIOLATED     | Named test RUN and passed (lock enter/exit per job); `index_lock` scopes `_run_job` only                                       |
| No extension-only event filtering bypassing the shared predicate (D-07)                | NOT VIOLATED     | Zero `.suffix`/`endswith` checks in watcher.py (grep); fold consumes `partial(scanner.matches, ...)`                            |
| Never watch broader than registered collection roots (D-01)                            | NOT VIOLATED     | `observer.schedule` only on `Path(coll.path).resolve()` of registered collections (`watcher.py:360-362`)                       |
| Missing root never interpreted as mass deletion (D-11)                                  | NOT VIOLATED     | Guards on both update paths (`incremental.py:111-120,191-199`); 3 passing tests incl. e2e recovery RUN by verifier             |
| Embedding compute never inside an open write transaction (D-09)                        | NOT VIOLATED     | Behavioral test RUN and passed (in_transaction flags); code shape verified line-by-line                                        |
| No live rescope of the collection set while watch runs (D-02)                          | NOT VIOLATED     | Collections snapshot at construction; recovery_tick only re-stats tracked `_watch_state`s; no repository re-read loop          |
| No new runtime dependencies (zero-new-deps lock)                                        | NOT VIOLATED     | `git diff 0099159..HEAD -- pyproject.toml`: only `watchdog>=3.0.0` → `>=4.0.0,<7.0.0`; `uv lock --check` clean                |
| docs/cli-reference.md + configuration.md never hand-edited                              | NOT VIOLATED     | Docs touched only in `64efc8c` (regenerate commit, generator script co-modified); content matches generator output shapes      |
| Embed compute not split outside the flock window (12-02)                                | NOT VIOLATED     | `embed_documents` invoked inside `_run_burst`'s `index_lock` window (`watcher.py:489-509`)                                     |
| No periodic wal_checkpoint during long runs (12-02)                                     | NOT VIOLATED     | Single `wal_checkpoint` occurrence in src/ — the shutdown routine only (grep)                                                  |
| E2e never sleep-polls without a deadline / never asserts raw event sequences (12-03)   | NOT VIOLATED     | Test file review: all waits via `_poll_until` (deadline); fixed sleeps are bounded post-outcome settles; zero watchdog imports  |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| —    | —    | No TBD/FIXME/XXX, no TODO/HACK/PLACEHOLDER, no stub phrases, no empty implementations, no skipped tests in any phase-modified file | —        | None   |

Working tree clean for all phase files (no uncommitted drift); all 10 task commits across the three plans exist and are ancestors of HEAD.

### Test Quality Audit

| Test File                        | Linked Req                  | Active | Skipped | Circular | Assertion Level    | Verdict    |
| -------------------------------- | --------------------------- | ------ | ------- | -------- | ------------------ | ---------- |
| tests/integration/test_watch_e2e.py | LIVE-01/02/03/04/11, D-14 | 6      | 0       | 0        | Behavioral (row content, checksums, exit codes, WAL bytes) | PASS |
| tests/unit/indexing/test_watcher.py | LIVE-02/03/04/05/11, D-04/09 | 22   | 0       | 0        | Value/Behavioral (call counts, in_transaction flags, row counts) | PASS |
| tests/unit/cli/test_watch_cmd.py    | LIVE-01/05, D-13/14        | 13     | 0       | 0        | Value (depth values, exit codes, checkpoint capture)  | PASS       |
| tests/unit/indexing/test_scanner.py | LIVE-04                     | +3     | 0       | 0        | Value (set equality, pattern membership)              | PASS       |
| tests/unit/indexing/test_incremental.py | LIVE-11 (replay edge)    | +1     | 0       | 0        | Value (zero counts)                                  | PASS       |

**Disabled tests on requirements:** 0. **Circular patterns detected:** 0 (expected values are independently authored file bodies and checksum comparisons — nothing regenerated from the system under test). **Insufficient assertions:** 0. The D-09 boundary test is the strongest shape observed: it records `conn.in_transaction` at both the embed boundary (asserted False) and the chunk-write boundary (asserted True), proving the txn ordering rather than mere code shape.

### Human Verification Required

All 12 functional must-have truths are verified with behavioral evidence. Two user-facing items remain — the phase is a terminal host whose output and live feel are visible to end users, and the executors deliberately deferred UX judgment (D6 in the 12-01 and 12-02 SUMMARYs):

### 1. Foreground watch UX (banner, summary lines, Ctrl-C feel)

**Test:** Run `sif watch` on a real notes collection in a terminal, save a file from a real editor, and watch the output for a minute; then press Ctrl-C once.
**Expected:** Banner (watched roots, depth mode, debounce) is readable; each settled save produces exactly one `indexed N · removed M · unchanged K` line; `--verbose` per-file lines are legible; a single Ctrl-C exits cleanly and promptly.
**Why human:** Terminal output wording/readability and live-update feel are visual/UX judgment — automated tests assert exit codes and DB state only.

### 2. Real-editor save storm with `--embed`

**Test:** With `sif watch --embed` on a small real collection, make 3-4 rapid saves of the same note in a real editor (Vim/Emacs/VSCode), then search for the newest content.
**Expected:** Each save storm coalesces to one summary line (no line flooding); the final content is findable via `sif search`; no temp-file rows ever appear.
**Why human:** Real-editor event storms on the developer's own machine are the LIVE-02 end-user reality; e2e covers the probed os.replace chain and synthetic bursts, but real editor timing and feel cannot be asserted programmatically.

### Gaps Summary

No gaps. Every roadmap success criterion, every plan truth, every artifact (existence, substance, wiring, data flow), every key link, and every requirement ID checks out against the actual codebase — with 12 named tests executed by the verifier directly, all passing, plus the orchestrator-supplied full-suite green on this identical tree. All prohibitions carry deterministic not-violated evidence. The only outstanding items are the two human UX checks above; `sif watch` is a user-facing terminal host, so those route to the end-of-phase human checkpoint rather than being absorbed into a silent pass.

Info (no action): reconcile jobs (directory moves, returning roots) intentionally stay BM25-only at embed depth — documented 12-02 scoping decision, not a violation of any stated truth.

---

_Verified: 2026-11-07T11:47:04Z_
_Verifier: Claude (gsd-verifier)_
