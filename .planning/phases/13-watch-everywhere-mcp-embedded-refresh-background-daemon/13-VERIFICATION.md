---
phase: 13-watch-everywhere-mcp-embedded-refresh-background-daemon
verified: 2026-11-07T17:43:24Z
status: human_needed
score: 38/40 must-haves verified
covered_files: [".planning/phases/13-watch-everywhere-mcp-embedded-refresh-background-daemon/13-01-PLAN.md", ".planning/phases/13-watch-everywhere-mcp-embedded-refresh-background-daemon/13-01-SUMMARY.md", ".planning/phases/13-watch-everywhere-mcp-embedded-refresh-background-daemon/13-02-PLAN.md", ".planning/phases/13-watch-everywhere-mcp-embedded-refresh-background-daemon/13-02-SUMMARY.md", ".planning/phases/13-watch-everywhere-mcp-embedded-refresh-background-daemon/13-03-PLAN.md", ".planning/phases/13-watch-everywhere-mcp-embedded-refresh-background-daemon/13-03-SUMMARY.md", ".planning/phases/13-watch-everywhere-mcp-embedded-refresh-background-daemon/13-04-PLAN.md", ".planning/phases/13-watch-everywhere-mcp-embedded-refresh-background-daemon/13-04-SUMMARY.md", "docs/cli-reference.md", "docs/configuration.md", "scripts/generate_config_ref.py", "src/sif/cli/commands/watch.py", "src/sif/cli/main.py", "src/sif/config/settings.py", "src/sif/indexing/watcher.py", "src/sif/mcp/transports/http.py", "src/sif/mcp/transports/stdio.py", "src/sif/mcp/watch_host.py", "src/sif/utils/daemon.py", "src/sif/utils/service.py", "tests/integration/test_mcp_watch_e2e.py", "tests/integration/test_service_live_launchd.py", "tests/integration/test_watch_daemon_e2e.py", "tests/unit/cli/test_status.py", "tests/unit/cli/test_watch_cmd.py", "tests/unit/indexing/test_watcher.py", "tests/unit/mcp/test_mcp_watch_host.py", "tests/unit/mcp/test_transports_http.py", "tests/unit/utils/test_daemon.py", "tests/unit/utils/test_service.py"]
covered_digest: "v4:sha256:b398406fd20c628a1a15337eb67f3c80ba168dafb7dacc53e9c380e86fbc9295"
behavior_unverified: 2
overrides_applied: 0
behavior_unverified_items:
  - truth: "A search served while a burst is mid-flight never exposes a partially-applied burst — readers observe either the pre-burst or the post-burst state (WAL transaction atomicity; 13-03 backstop-tagged truth)"
    test: "Run an MCP server with SIF_MCP_WATCH=1, issue repeated searches while a large multi-file burst is settling, and inspect result consistency per document"
    expected: "Every response shows each document either fully pre-burst or fully post-burst (per-document transactional consistency); no document appears with partially-applied chunk state"
    why_human: "verification: backstop — non-inferable. No test asserts non-exposure of partial state: the burst e2e (test_stdio_watch_query_responsive_during_burst) asserts responsiveness and eventual refresh, not read-side atomicity; Phase 11 rollback unit tests cover exception paths, not concurrent mid-burst reads. Presence + wiring cannot qualify"
  - truth: "Opt-in live launchd proof: with SIF_TEST_LIVE_LAUNCHD=1 on the macOS dev box, a scratch-label install round-trip (bootstrap -> running -> file change indexed -> bootout -> artifact removed) runs against a tmp DB (13-04)"
    test: "SIF_TEST_LIVE_LAUNCHD=1 env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/integration/test_service_live_launchd.py"
    expected: "Test passes (scratch-label agent really bootstrapped, indexes a file change, boots out, artifact gone, no leaked services)"
    why_human: "Opt-in live proof skipped in this verification (verifier no-state-mutation constraint — bootstrapping a real launchd agent mutates OS service state). SUMMARY claims it passed twice on this box; that is not verifier evidence"
human_verification:
  - test: "Inspect search results for partial-state exposure during a live burst (backstop truth above)"
    expected: "No document is ever observable in a partially-applied (mid-reindex) state while queries run during a burst"
    why_human: "WAL transaction atomicity under concurrent mid-burst reads is asserted by no automated test; grep/presence checks cannot see it"
  - test: "Run the opt-in live launchd round-trip on the macOS dev box"
    expected: "tests/integration/test_service_live_launchd.py passes; no scratch services leak"
    why_human: "Live OS-service invocation was not exercised by the verifier (state-mutation constraint)"
  - test: "Confirm the WR-01 shutdown design decision: the WAL checkpoint is SKIPPED (with a warning) when the worker thread outlives the stop join, rather than attempted anyway"
    expected: "Human confirms gating (not attempting) the checkpoint on worker_joined() is the desired D-14 behavior (flagged 'requires human verification' in 13-REVIEW-FIX.md)"
    why_human: "Explicit review-fix decision request on a shutdown path — a design-intent confirmation, not a code check"
  - test: "Confirm the WR-04 process-kill design decision: handshake timeout SIGKILLs the whole detached process group via killpg on the intermediate child's pid"
    expected: "Human confirms killpg-on-intermediate-pid is acceptable in the rare PID-recycling window (flagged 'requires human verification' in 13-REVIEW-FIX.md)"
    why_human: "Explicit review-fix decision request on process-kill logic — a design-intent confirmation, not a code check"
  - test: "Review the 12 flagged-unverified prohibitions (see Prohibition Review below): confirm the autonomous judge verdicts"
    expected: "Human concurs all 12 must-NOT contracts hold (zero new deps, no cross-host protocol, foreground unchanged, PID file never gates, fail-closed corroboration, no self-restart, BM25-forced depth, stdout clean, env-only opt-in, no fork under supervisor, no shell invocation, generator-only docs)"
    why_human: "All prohibitions carry verification: flagged-unverified (judgment-tier); autonomous verdicts are non-authoritative by contract"
---

# Phase 13: Watch Everywhere (MCP-Embedded Refresh + Background Daemon) Verification Report

**Phase Goal:** The index stays fresh with no terminal window open — the proven watch loop hosted inside the MCP server and as an installable background daemon.
**Verified:** 2026-11-07T17:43:24Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

Verified against the CURRENT codebase (including the 6 post-SUMMARY code-review fix commits 9acfd69/e3156da/8039a3e/191aa05/cd33b21/9756321 — CR-01 lifespan factory, WR-01 worker_joined checkpoint gate, WR-02 debouncer-join fix, WR-03 --no-embed baking, WR-04 killpg-on-timeout, lint cleanup; all confirmed present in the source and covered by tests).

### Observable Truths

Roadmap success criteria (the contract) plus plan must-haves, deduplicated (13-02 T6 = SC4; 13-03 T1/T2 = SC1).

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC1: SIF_MCP_WATCH=1 MCP server keeps the index current while serving; searches responsive during a burst (LIVE-08) | ✓ VERIFIED | Real stdio subprocess e2e run by verifier: `test_stdio_watch_refreshes_index_while_serving` (1.63s), `test_stdio_watch_query_responsive_during_burst` + `test_stdio_stdout_protocol_clean_during_burst` (5.30s) — all pass; wiring at src/sif/mcp/transports/stdio.py:136-145 |
| 2 | SC2: `sif watch --detach` backgrounds with lifecycle controls (PID reported, --stop clean, status reports) | ✓ VERIFIED | `test_detach_backgrounds_watcher_and_indexes_live_changes` (3.12s) + `test_stop_terminates_gracefully_with_wal_truncate` + `test_stop_without_daemon_prints_not_running` pass; status Watch row at src/sif/cli/main.py:110-173; 5 TestWatchSection unit tests pass |
| 3 | SC3: launchd LaunchAgent / systemd user unit generatable and installable; no fork under supervisor | ✓ VERIFIED | tests/unit/utils/test_service.py 12 tests pass (cross-platform plist round-trip + unit text, exact install/uninstall argv, bootout-retry, missing-manager, AST no-shell); `_watch_argv` = foreground `watch` (src/sif/utils/service.py:97-98); guard rejects --detach+--install-service (watch.py:516-521); live invocation deferred (see #40) |
| 4 | SC4: SIGKILLed daemon leaves no stale lock; immediate re-detach succeeds (flock, not PID-file) | ✓ VERIFIED | `test_sigkill_then_immediate_redetach_succeeds` run by verifier (pass, in 6.08s batch); PID file is metadata only (daemon.py module contract, never read on the detach path) |
| 5 | 13-01 T1: rescope added collection schedules + reconciles; file under new root indexed, no restart | ✓ VERIFIED | `TestLiveRescope::test_rescope_added_collection_schedules_and_reconciles` run by verifier (pass); watcher.py:582-605 |
| 6 | 13-01 T2: removed collection unscheduled (handle released, debouncer stopped), documents preserved | ✓ VERIFIED | `test_rescope_removed_collection_unschedules_and_preserves_documents` run by verifier (pass); watcher.py:564-580 logs "documents preserved", never touches rows |
| 7 | 13-01 T3: rescope opt-in via provider; default never changes watch set (foreground restart-on-change kept) | ✓ VERIFIED | `test_no_provider_default_never_changes_watch_set` run by verifier (pass); `_rescope_if_due` returns when provider None (watcher.py:628-630); foreground host passes no provider (WatchHostParams default None) |
| 8 | 13-01 T4: rescope exact-set — only provider's returns watched | ✓ VERIFIED | `test_rescope_adds_exactly_the_providers_set_nothing_more` run by verifier (pass) |
| 9 | 13-01 T5: idle checkpoint due on tick; busy row skips silently; recent burst postpones | ✓ VERIFIED | `test_checkpoint_runs_once_when_due` + `test_recent_burst_postpones_checkpoint` run by verifier; busy-skip + full battery green in the verifier's full-suite run; watcher.py:644-680 |
| 10 | 13-01 T6: checkpoint disabled by default (interval=0 → zero executions) | ✓ VERIFIED | `test_disabled_by_default_never_checkpoints` run by verifier (pass); guard at watcher.py:653 |
| 11 | 13-01 T7: schedule-failure warns once (errno cause + fs.inotify.max_user_watches remedy), others keep watching, tick retries | ✓ VERIFIED | `test_schedule_failure_at_start_warns_once_others_watch_and_tick_retries` + `test_rescope_add_with_schedule_failure_rest_of_diff_proceeds` run by verifier (pass); watcher.py:399-438 |
| 12 | 13-01 T8: settings mcp_watch=False, watch_rescope_interval=60.0 (ge=1), watch_checkpoint_interval=300.0 (ge=0); SIF_ env spellings resolve | ✓ VERIFIED | settings.py:67-85 (defaults + bounds match); `TestWatchSettings` run by verifier (pass) |
| 13 | 13-02 T1: --detach stdlib double-fork, PID printed before parent exit 0; daemon runs exact foreground host body incl. rescope + checkpoint from settings | ✓ VERIFIED | daemon.py:177-247 (fork→setsid→fork, no chdir); watch.py:346-399 (`_run_detach` fork-first, `replace()`-derived params, `run_watch_host` shared verbatim); e2e pass |
| 14 | 13-02 T2: deterministic handshake — armed/error via pipe, never silent maybe-detach | ✓ VERIFIED | `_read_pipe_message` bounded select; arm-failure → error message → ClickException; WR-04 timeout → killpg + reported failure (daemon.py:196-247, 325-356); `test_detach_arm_timeout_kills_grandchild_session` green in full suite |
| 15 | 13-02 T3: --stop corroborates → SIGTERM → bounded poll → SIGKILL → unlink; daemon exits via D-14 graceful path | ✓ VERIFIED | stop_daemon escalation (daemon.py:250-322); graceful-stop e2e (WAL truncated, no traceback) run by verifier |
| 16 | 13-02 T4: stale PID file → not-running + cleanup, no signal to uncorroborated PID | ✓ VERIFIED | corroborate_pid fail-closed (daemon.py:140-174: ProcessLookup/ps-missing/mismatch/token-based watch marker); 24-test hermetic battery run by verifier (pass) |
| 17 | 13-02 T5: `sif status` Watch section (running/PID/mode/depth) on both surfaces incl. `sif index status` alias | ✓ VERIFIED | main.py:110-173 single `_watch_status_text` path; tests/unit/cli/test_status.py TestWatchSection (running/stale x2/missing/alias) green in verifier run |
| 18 | 13-02 T7: logs default platformdirs user_log_dir('sif') with --log-file override; PID file 0600 metadata, never a lock | ✓ VERIFIED | `_daemon_log_path` (watch.py:307-320); write_pid_file os.open 0600 (daemon.py:89-103); detach path never reads a PID file before starting |
| 19 | 13-02 T8: daemon -c filter semantics; rescope provider returns only filtered collections | ✓ VERIFIED | `_daemon_rescope_provider` (watch.py:323-343) withholds non-`-c` names; e2e runs a filtered daemon |
| 20 | 13-02 T9: coexistence — daemon/foreground/MCP watchers serialize via per-burst flock, no host-added protocol | ✓ VERIFIED | No cross-host protocol code exists in watcher.py/daemon.py/watch_host.py (verifier grep); all writer paths use locking.index_lock per burst (Phase 11 substrate, unchanged — pyproject/git clean) |
| 21 | 13-03 T3: embedded watcher BM25-only always — depth forced even under SIF_WATCH_UPDATE_DEPTH=embed | ✓ VERIFIED | `_MCP_WATCH_DEPTH = "bm25"` literal (watch_host.py:49); no `watch_update_depth` reference in module (grep clean); `test_depth_forced_bm25_even_when_settings_say_embed` run by verifier (pass) |
| 22 | 13-03 T4: opt-in env var only; flag off → no watcher, no watch Database, serving byte-identical | ✓ VERIFIED | start_embedded_watch returns None before Database construction (watch_host.py:114-117); `test_flag_off_returns_none_and_never_opens_database` run by verifier; no --watch flags on mcp commands (grep empty) |
| 23 | 13-03 T5: every stdout line during watch parses as JSON; callbacks log to stderr only | ✓ VERIFIED | protocol-clean e2e run by verifier (pass); `test_renderers_log_only_and_never_touch_stdout` run by verifier (caplog records, stdout empty) |
| 24 | 13-03 T6: initialize handshake never blocked by startup reconcile (serve-first, queued jobs) | ✓ VERIFIED | `_enqueue_startup_reconcile` queue.put (watch_host.py:93-101); `test_stdio_initialize_not_blocked_by_pending_drift` + `test_startup_reconcile_is_queued_not_inline` run by verifier (pass) |
| 25 | 13-03 T7: zero collections → no-op with logged notice, server serves | ✓ VERIFIED | watch_host.py:126-131; `test_zero_collections_returns_none_with_notice` run by verifier (pass) |
| 26 | 13-03 T8: HTTP lifespan — create_app optional lifespan param, existing call sites unchanged, start-before-requests/stop-after | ✓ VERIFIED | http.py:150-166 (`lifespan: Any = None` → FastAPI(lifespan=...)); mcp_watch_lifespan is a FACTORY (post-CR-01, watch_host.py:190-214); `test_mcp_watch_lifespan_boots_a_real_app` + TestWatchLifespanThreading green in verifier runs; no on_event handlers (grep) |
| 27 | 13-03 T9: MCP rescope provider returns all registered collections on the 13-01 tick seam | ✓ VERIFIED | `_registered_collections` provider wired (watch_host.py:135-137, 150) |
| 28 | 13-03 T10: coexistence via same per-burst flock, no duplicated embed work | ✓ VERIFIED | Same evidence as #20; depth bm25 makes embed duplication moot on this host |
| 29 | 13-04 T1+T2: --install-service generates AND installs; plist carries Label com.docsif.watch/RunAtLoad/KeepAlive/ThrottleInterval=10/absolute-interpreter ProgramArguments/log paths | ✓ VERIFIED | build_plist (service.py:103-137); `test_round_trip_carries_label_argv_supervision_and_logs` run by verifier (plistlib round-trip) |
| 30 | 13-04 T3: systemd unit Type=simple/Restart=on-failure/RestartSec=5/WantedBy=default.target/absolute ExecStart | ✓ VERIFIED | render_unit (service.py:139-160); TestUnitGeneration (2 tests incl. quoting) run by verifier on macOS (cross-platform pin held) |
| 31 | 13-04 T4+T5: install = write 0644 + gate + explicit-argv bootstrap/enable --now + verify; missing manager → friendly ClickException | ✓ VERIFIED | TestInstallArgvLaunchd (bootstrap gui/uid then print verify), TestInstallArgvSystemd (daemon-reload, enable --now, is-active), TestMissingManager (3) all run by verifier (pass); ServiceManagerMissing → ClickException (watch.py:470-471) |
| 32 | 13-04 T6: generation cross-platform pure text, asserted on any platform | ✓ VERIFIED | Both platform batteries ran green on this macOS box (no skip-if-platform guards) |
| 33 | 13-04 T7: --uninstall-service stops then removes, reports | ✓ VERIFIED | TestUninstallArgv (launchd bootout+unlink; systemd disable --now+unlink+daemon-reload) run by verifier (pass) |
| 34 | 13-04 T8: survive-logout surfaced — Linux output documents loginctl enable-linger | ✓ VERIFIED | watch.py:476-482 prints the linger note for systemd manager; TestServiceFlags linger test green |
| 35 | 13-04 T9: docs regenerated solely by generator — SIF_MCP_WATCH/SIF_WATCH_RESCOPE_INTERVAL/SIF_WATCH_CHECKPOINT_INTERVAL in configuration.md; five flags in cli-reference.md | ✓ VERIFIED | Verifier grep counts: 1/1/1 in configuration.md; --install-service 1, --uninstall-service 1, --detach 3 in cli-reference.md; SECTIONS registered (generate_config_ref.py:171-175); docs commits are generator regenerations (1a98e9e, and WR-03's 191aa05 diff is exactly the one generator-emitted help line); tests/test_docs.py green in verifier run |
| 36 | 13-04 T10: full quality gate green (pytest fail_under=90, ruff, format, ty) | ✓ VERIFIED | Verifier's own full run: 1161 passed, 1 skipped, 94.59% coverage in 63.47s; ruff check "All checks passed", format "172 files already formatted", ty "All checks passed" |
| 37 | 13-04 prohibitions source: no shell=True / no string command lines anywhere in the service path | ✓ VERIFIED | AST-pinning test `test_no_shell_true_or_string_command_lines_in_module` run by verifier (pass); verifier grep of service.py: no shell= |
| 38 | 13-02/13-04 service replays install-time flags (WR-03: --no-embed baked when installer depth is bm25 against embed ambient) | ✓ VERIFIED | `_service_argv_tail` (watch.py:424-452) bakes --embed iff depth embed, --no-embed when no_embed or ambient embed; depth-matrix unit tests green in full suite |
| 39 | 13-03 backstop: a search during a mid-flight burst never exposes a partially-applied burst (WAL atomicity) | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | Present + wired (WAL mode, per-file transactions from Phase 11; burst e2e proves responsiveness) but NO test asserts read-side non-exposure of partial state — non-inferable backstop truth, abstaining per contract (see Human Verification) |
| 40 | 13-04 T11: opt-in live launchd round-trip proof (SIF_TEST_LIVE_LAUNCHD=1) | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | Test exists with scratch label + tmp dest + finally-bootout safety net and skips cleanly without the env (the 1 skip in the full suite); NOT exercised by the verifier (no-OS-state-mutation constraint); SUMMARY's "passed twice" is not verifier evidence (see Human Verification) |

**Score:** 38/40 truths verified (2 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| src/sif/indexing/watcher.py | rescope/checkpoint/schedule-failure growth | ✓ VERIFIED | 831 lines; rescope/_unschedule_removed/_schedule_added/_on_tick/_rescope_if_due/_checkpoint_if_due/_checkpoint_if_idle/_schedule_watch→bool with warn-once remedy; substantive and exercised |
| src/sif/config/settings.py | mcp_watch + 2 interval fields | ✓ VERIFIED | Lines 67-85, defaults/bounds exactly as planned |
| src/sif/utils/daemon.py | double-fork, PID file, corroborate, stop escalation | ✓ VERIFIED | 389 lines, full implementation incl. WR-04 killpg; 24-test hermetic battery green |
| src/sif/utils/service.py | plist/unit builders, install/uninstall, manager gating | ✓ VERIFIED | 358 lines, all D-12/D-13 keys, AST-pinned argv discipline |
| src/sif/mcp/watch_host.py | start/stop pair + lifespan factory | ✓ VERIFIED | 214 lines; post-CR-01 factory shape; 11 unit tests green |
| src/sif/mcp/transports/stdio.py | watcher wiring around serve loop | ✓ VERIFIED | run_stdio_server:136-145 start/finally-stop; signature unchanged |
| src/sif/mcp/transports/http.py | lifespan threading | ✓ VERIFIED | create_app/HTTPTransport/run_http_server all thread default-None lifespan |
| src/sif/cli/commands/watch.py | lifecycle + service flags, shared host body | ✓ VERIFIED | All 5 new Click options; run_watch_host shared; guards; WR-03 tail |
| src/sif/cli/main.py | status Watch section | ✓ VERIFIED | _watch_status_text + Watch row, guarded probe |
| scripts/generate_config_ref.py | SECTIONS registration | ✓ VERIFIED | Lines 171-175 |
| docs/cli-reference.md / docs/configuration.md | regenerated, generator-owned | ✓ VERIFIED | Content greps pass; git provenance generator-only |
| 7 test files (unit x6 + integration x3) | claimed batteries | ✓ VERIFIED | All exist with claimed test names; verifier ran 70+ of them directly plus the full suite |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| watch_cmd --detach | daemon.detach → PID file → run_watch_host | fork-first, pipe handshake, replace()-wired rescope/checkpoint | ✓ WIRED | watch.py:346-399; no Database/thread before fork |
| watch_cmd --stop | read_pid_file → corroborate_pid → SIGTERM→SIGKILL → unlink | stop_daemon | ✓ WIRED | watch.py:402-416 → daemon.py:250-278 |
| status_cmd | utils.daemon read + corroborate → Watch row | _watch_status_text, both surfaces | ✓ WIRED | main.py:110-173 |
| run_stdio_server | start_embedded_watch → transport.run → finally stop | try/finally around serve loop | ✓ WIRED | stdio.py:128-145 |
| run_http_server | mcp_watch_lifespan → HTTPTransport → create_app → FastAPI | lifespan kwarg threading | ✓ WIRED | http.py:217-258; factory shape (post CR-01) |
| watch callbacks | logger (stderr) | get_logger renderers; never console/print | ✓ WIRED | watch_host.py:65-90; unit + e2e pinned |
| worker tick | recovery_tick → rescope-if-due → checkpoint-if-due | _on_tick, all worker-thread | ✓ WIRED | watcher.py:607-619 |
| watch_cmd --install-service | utils.service install (write → gate → argv → verify) | explicit argv only, no fork | ✓ WIRED | watch.py:455-482 → service.py:212-327 |
| Settings fields | generator SECTIONS → docs | make docs-generate | ✓ WIRED | generate_config_ref.py:171-175; docs content verified |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| status Watch row | payload | read_pid_file + corroborate_pid (real file + ps) | Yes | ✓ FLOWING |
| detach PID print | outcome.pid | real fork + pipe handshake | Yes | ✓ FLOWING |
| watch_host collections | collections / rescope set | CollectionRepository.list_all (real query) | Yes | ✓ FLOWING |
| service InstallResult | artifact/log/verify | real subprocess argv to launchctl/systemctl (mocked in tests, live deferred) | Yes | ✓ FLOWING |
| daemon rescope | registered collections | collections-table read via shared connection | Yes | ✓ FLOWING |

No static/hardcoded data sources found.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Rescope add/remove/exact-set/default-off | pytest TestLiveRescope (4 named) | 4 passed | ✓ PASS |
| Checkpoint due/burst/disabled + schedule-failure (start + rescope paths) + settings | pytest named tests + TestWatchSettings | 7 passed | ✓ PASS |
| Daemon/service/MCP-host unit batteries | pytest 3 files | 52 passed | ✓ PASS |
| SC2 detach e2e (real daemon subprocess) | pytest test_detach_backgrounds_watcher_and_indexes_live_changes | 1 passed (3.12s) | ✓ PASS |
| SC4 + graceful stop e2e | pytest sigkill + wal_truncate tests | 2 passed (6.08s) | ✓ PASS |
| SC1 refresh e2e (real stdio server) | pytest test_stdio_watch_refreshes_index_while_serving | 1 passed (1.63s) | ✓ PASS |
| SC1 responsiveness + protocol-clean | pytest 2 burst tests | 2 passed (5.30s) | ✓ PASS |
| Handshake-unblocked + remaining watcher pins | pytest initialize_not_blocked + 6 more | 7 passed (1.21s) | ✓ PASS |
| Docs + status + watch-cmd batteries | pytest tests/test_docs.py test_status.py test_watch_cmd.py | 55 passed | ✓ PASS |
| Full phase gate (once) | pytest (full) | 1161 passed, 1 skipped, 94.59% | ✓ PASS |
| ruff / format / ty | all three | All checks passed | ✓ PASS |
| Live launchd round-trip | opt-in env not set | skipped by design | ? SKIP → human |

### Probe Execution

No phase-declared probes and no `scripts/*/tests/probe-*.sh` exist — Step 7c not applicable.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| LIVE-08 | 13-01, 13-03 | SIF_MCP_WATCH=1 embedded MCP refresh, queries never starved | ✓ SATISFIED | Truths #1, #21-#28; REQUIREMENTS.md marked Complete |
| LIVE-09 | 13-01, 13-02, 13-04 | --detach (PID/stop/status) + launchd/systemd service install | ✓ SATISFIED | Truths #2-#4, #13-#20, #29-#38; REQUIREMENTS.md marked Complete |

Orphaned requirements: none — REQUIREMENTS.md maps exactly LIVE-08 and LIVE-09 to Phase 13; both are declared across the plans and satisfied.

### Decision Coverage

All trackable CONTEXT.md decisions are honored by shipped artifacts (17/17 honored, 0 not honored; non-blocking gate).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | - | No TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER markers in any of the 9 phase production files; no stub returns (read_pid_file's None returns are the documented defensive contract); no console-only implementations | - | - |

Known open (Info, pre-existing, tracked in deferred-items.md): ResourceWarning from an unclosed sqlite connection in 13-01's TestIdleCheckpoint — test hygiene only, no production impact (one of the 4 warnings in the full-suite run; suite exits 0).

### Prohibition Review (judgment-tier, `flagged-unverified` — autonomous verdicts NON-AUTHORITATIVE)

`unverified-prohibition — human review recommended`: all 12 plan prohibitions were evaluated by the verifier against the current code and found honored, but their tier makes these verdicts non-authoritative:

| Plan | Prohibition (abridged) | Judge verdict | Key evidence |
|------|------------------------|---------------|--------------|
| 13-01 | No new runtime dependencies | Honored | git log 90e620b..HEAD -- pyproject.toml is empty |
| 13-01 | No stand-down/discovery protocol between watch forms | Honored | No such code exists; per-burst flock only (verifier grep) |
| 13-01 | Foreground host keeps restart-on-change | Honored | Foreground passes rescope_provider=None; pinned by test |
| 13-02 | PID file never gates startup / arbitrates | Honored | Detach path never reads a PID file; flock is sole arbitration |
| 13-02 | --stop never signals uncorroborated PID | Honored | Fail-closed corroborate_pid; unit-pinned every branch |
| 13-02 | No self-restart loop in the raw daemon | Honored | Daemon child runs run_watch_host once (watch.py:387-393) |
| 13-03 | MCP watcher never embeds | Honored | Literal bm25 constant; grep-clean of watch_update_depth; unit-pinned |
| 13-03 | Watch-host never writes stdout | Honored | Logger-only renderers; caplog/stdout-empty unit + e2e corpus pinned |
| 13-03 | Never starts unconditionally; env-only opt-in | Honored | settings.mcp_watch gate before any Database; no mcp --watch flags |
| 13-04 | Installed service never forks | Honored | argv runs foreground `watch`; guard rejects --detach combination |
| 13-04 | launchctl/systemctl never via shell | Honored | No shell=True (grep + AST-pinning test) |
| 13-04 | Docs never hand-edited | Honored | Docs commits are generator regenerations; WR-03 docs diff is exactly the one generated help line |

### Human Verification Required

1. **Burst read-side atomicity (backstop truth)**
   **Test:** Run an MCP server with SIF_MCP_WATCH=1 and issue repeated searches while a large multi-file burst settles; inspect per-document consistency.
   **Expected:** No document is ever observable in a partially-applied (mid-reindex) state.
   **Why human:** No automated test asserts non-exposure of partial state; presence + wiring cannot verify a runtime invariant of this kind.

2. **Live launchd round-trip**
   **Test:** `SIF_TEST_LIVE_LAUNCHD=1 env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/integration/test_service_live_launchd.py` on the macOS dev box.
   **Expected:** Passes; scratch agent bootstraps, indexes a change, boots out; no leaked services.
   **Why human:** Opt-in live OS-service invocation; verifier constrained from mutating system service state.

3. **WR-01 shutdown design decision**
   **Test:** Confirm skipping (not attempting) the shutdown WAL checkpoint when the worker outlives the join is the intended D-14 behavior.
   **Expected:** Human sign-off on the gating design (flagged in 13-REVIEW-FIX.md).
   **Why human:** Explicit review-fix decision request on a shutdown path.

4. **WR-04 killpg design decision**
   **Test:** Confirm SIGKILLing the detached process group (killpg on the intermediate child's pid) on handshake timeout is acceptable in the rare PID-recycling window.
   **Expected:** Human sign-off on the kill semantics (flagged in 13-REVIEW-FIX.md).
   **Why human:** Explicit review-fix decision request on process-kill logic.

5. **Prohibition sign-off**
   **Test:** Review the 12 judgment-tier prohibitions in the table above.
   **Expected:** Human concurs with the autonomous honored verdicts.
   **Why human:** flagged-unverified tier — verifier verdicts are non-authoritative by contract.

### Gaps Summary

No gaps. Every roadmap success criterion and every plan must-have is present, substantive, wired, and data-flowing in the current code; the full quality gate was independently re-run green by the verifier (1161 passed, 1 skipped @ 94.59%; ruff/format/ty clean); all 22 documented commits exist; no debt markers; no orphaned requirements; decision coverage 17/17. The status is human_needed solely because two truths are present-but-not-behaviorally-exercised (the backstop-tagged WAL-atomicity truth and the opt-in live launchd proof), two review-fix design decisions explicitly request human confirmation (WR-01, WR-04), and the 12 judgment-tier prohibitions require human sign-off — none of these indicate missing or broken functionality.

---

_Verified: 2026-11-07T17:43:24Z_
_Verifier: Claude (gsd-verifier)_
