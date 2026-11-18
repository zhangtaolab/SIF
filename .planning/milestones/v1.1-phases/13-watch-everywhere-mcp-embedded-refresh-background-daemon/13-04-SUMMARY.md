---
phase: 13-watch-everywhere-mcp-embedded-refresh-background-daemon
plan: 04
subsystem: infra
tags: [launchd, systemd, plist, service-install, docs-generation, watch-lifecycle]

requires:
  - phase: 13-02
    provides: [daemon flags, watch_cmd flag family, run_watch_host body the service replays]
  - phase: 13-01
    provides: [watch settings fields surfaced in regenerated docs]
provides:
  - src/sif/utils/service.py — cross-platform launchd plist (plistlib) + systemd unit (template) generation, install (write-temp-then-rename 0644 + explicit-argv bootstrap/enable + verify + Pitfall-5 bootout-retry), uninstall (stop-then-remove), missing-manager typed errors
  - watch_cmd --install-service / --uninstall-service — SC3 service path with baked install-time flags, artifact/log/verify output, Linux linger note
  - tests/integration/test_service_live_launchd.py — opt-in real-bootstrap round-trip proof (scratch label, tmp everything, finally-bootout safety net)
  - Regenerated generator-owned docs: --detach/--stop/--log-file/--install-service/--uninstall-service in cli-reference.md; SIF_MCP_WATCH / SIF_WATCH_RESCOPE_INTERVAL / SIF_WATCH_CHECKPOINT_INTERVAL in configuration.md
affects: [LIVE-09 closure, docs, future sif mcp daemon service reuse]

actuals:
  tokens: 12914   # chars/4 over the realized 681ab4c..1a98e9e diff (51657 chars, 1117 insertions / 9 deletions across 8 files)
  tasks: 2
  commits: 4      # measured: git rev-list --count 681ab4c..1a98e9e
plan_head_before: 681ab4cb38bb2c13e35f636b2e1dde8b633b9b6e
plan_head_after: 1a98e9e6adfea88bb2323310e208c92be06a985f

tech-stack:
  added: []       # zero new deps — stdlib plistlib/subprocess/shutil + existing platformdirs
  patterns:
    - "Service artifacts are pure text generated on any platform and asserted there (D-13): plist parsed back via plistlib, unit asserted as text — live manager invocation only where the manager exists"
    - "Manager invocation = bare binary name after a shutil.which gate, always an explicit argv list, never a shell (D-12); AST-level test pins the discipline against regressions"
    - "Install-time flag baking (D-11): the service replays exactly -c names + --embed-iff-embed-depth with an absolute interpreter and resolved --index path — no user PATH or cwd dependence"
    - "launchd bootout is asynchronous: gone-state is deadline-polled in tests; production uninstall returns after issuing bootout and a re-install's bootout-then-bootstrap retry covers the still-loaded window"

key-files:
  created:
    - src/sif/utils/service.py
    - tests/unit/utils/test_service.py
    - tests/integration/test_service_live_launchd.py
  modified:
    - src/sif/cli/commands/watch.py - --install-service/--uninstall-service options, _check_lifecycle_guards extraction (C901), _service_manager/_service_argv_tail/_run_install_service/_run_uninstall_service
    - scripts/generate_config_ref.py - SECTIONS: watch_rescope_interval + watch_checkpoint_interval (Watch Settings), mcp_watch (MCP Server Settings)
    - docs/cli-reference.md - regenerated (five watch lifecycle flags + live-rescope docstring)
    - docs/configuration.md - regenerated (three new SIF_ settings)
    - tests/unit/cli/test_watch_cmd.py - TestServiceFlags battery (8 tests)

key-decisions:
  - "The service argv tail bakes exactly the -c names (order-preserving dedupe) plus --embed iff the effective install-time depth is embed — SIF_WATCH_UPDATE_DEPTH=embed in the installing shell also lands as --embed so the supervised process (which sees no user env) replays the same depth"
  - "Manager binaries are invoked by bare name (launchctl/systemctl) after a shutil.which gate rather than by which-resolved absolute path — presence is checked once, the argv stays the documented ['launchctl', 'bootstrap', 'gui/<uid>', <plist>] form, and the fake-runner tests assert it exactly"
  - "ServiceManagerMissing keeps the plan-named spelling under a targeted noqa: N818 (the type is named in the 13-04 action text); it surfaces through the CLI as click.ClickException naming the binary and remedy"
  - "Production uninstall issues bootout and returns (launchd semantics); it does not wait for the SIGTERM'd watcher's graceful exit — the async gone-state matters only to tests, and a re-install inside the window is handled by the Pitfall-5 bootout-then-bootstrap retry"
  - "The plist logs (watch.log / watch.err.log) land under the same platformdirs user_log_dir('sif') tree as the raw daemon (D-07), so supervised and unsupervised daemons share one log tree; systemd's log location is the journal command"

patterns-established:
  - "Opt-in live manager proof: module-level skipif on env+platform+binary, scratch label + tmp dest overrides so the real bootstrap path runs without touching user state, finally-bootout safety net, deadline-polled outcomes (banner, DB row, service-gone)"
  - "AST source-discipline test: parse the module once and fail on any shell=True keyword or string passed to the invocation helper — prose in docstrings cannot false-positive"

requirements-completed: [LIVE-09]

coverage:
  - id: D1
    description: "Cross-platform artifact generation (D-13): plist round-trip via plistlib carries Label com.docsif.watch, exact absolute-interpreter ProgramArguments with baked tail, RunAtLoad/KeepAlive true, ThrottleInterval 10, log-dir Standard paths; unit text carries [Unit]/[Service]/[Install], Type=simple, Restart=on-failure, RestartSec=5, WantedBy=default.target, quoted ExecStart"
    requirement: LIVE-09
    verification:
      - kind: unit
        ref: "tests/unit/utils/test_service.py#TestPlistGeneration::test_round_trip_carries_label_argv_supervision_and_logs (pass)"
        status: pass
      - kind: unit
        ref: "tests/unit/utils/test_service.py#TestUnitGeneration (2 tests incl. whitespace quoting, pass)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Install = write + enable + start + verify with exact explicit argv (D-12): launchd bootstrap gui/<uid> <plist> then print gui/<uid>/<label> verify, artifact 0644; systemd daemon-reload, enable --now sif-watch, is-active verify, unit 0644 at the injected dir; never forks, never a shell"
    requirement: LIVE-09
    verification:
      - kind: unit
        ref: "tests/unit/utils/test_service.py#TestInstallArgvLaunchd + TestInstallArgvSystemd (exact call-list asserts, pass)"
        status: pass
      - kind: unit
        ref: "tests/unit/utils/test_service.py#TestInvocationDiscipline (AST: no shell=True, no string argv, pass)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Re-install conflict + missing manager (Pitfall 5, D-12 friendly errors): first bootstrap non-zero runs bootout gui/<uid>/<label> then retries bootstrap, replacing a stale artifact; shutil.which=None raises typed ServiceManagerMissing before any write, surfaced by the CLI as a ClickException naming the binary and remedy"
    requirement: LIVE-09
    verification:
      - kind: unit
        ref: "tests/unit/utils/test_service.py#TestReinstallConflict + TestMissingManager (3 tests, pass)"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_watch_cmd.py#TestServiceFlags::test_missing_manager_surfaces_as_click_error (pass)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Uninstall stop-then-remove both managers (D-11/D-12): launchd bootout then unlink; systemd disable --now, unlink, daemon-reload; returns the removed artifact path which the CLI reports"
    requirement: LIVE-09
    verification:
      - kind: unit
        ref: "tests/unit/utils/test_service.py#TestUninstallArgv (2 tests, pass)"
        status: pass
    human_judgment: false
  - id: D5
    description: "CLI surface (D-11): --help lists both flags; install prints artifact path + log location + verify command with the -c/--embed tail baked and absolute --index; Linux output documents loginctl enable-linger (D-13); uninstall reports stop-then-remove; guards reject install+uninstall and any service flag combined with --detach/--stop (SC3)"
    requirement: LIVE-09
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_watch_cmd.py#TestServiceFlags (8 tests: help, install output+tail, linger, uninstall report, 3 guards, missing manager — all pass)"
        status: pass
    human_judgment: false
  - id: D6
    description: "SC3 live proof (D-13 live-invocation clause): real launchctl bootstrap of a scratch-label agent runs the FOREGROUND sif watch against a tmp DB; a file change written after the post-arm Watching banner becomes indexed; bootout + uninstall remove artifact and service; finally-bootout safety net"
    requirement: LIVE-09
    verification:
      - kind: integration
        ref: "tests/integration/test_service_live_launchd.py#test_live_launchd_install_round_trip_indexes_a_change (SIF_TEST_LIVE_LAUNCHD=1 on this macOS dev box: passed twice, 2.0s and 1.7s, no leaked services; skips cleanly without the opt-in env)"
        status: pass
    human_judgment: false
  - id: D7
    description: "Docs regenerated solely by make docs-generate (12-03 precedent): SIF_MCP_WATCH, SIF_WATCH_RESCOPE_INTERVAL, SIF_WATCH_CHECKPOINT_INTERVAL present in configuration.md (env-var spellings); --install-service/--uninstall-service (plus the deferred --detach/--stop/--log-file) in cli-reference.md; docs gate green"
    requirement: LIVE-09
    verification:
      - kind: other
        ref: "grep counts: SIF_MCP_WATCH=1, SIF_WATCH_RESCOPE_INTERVAL=1, SIF_WATCH_CHECKPOINT_INTERVAL=1 in docs/configuration.md; --install-service=1, --uninstall-service=1, --detach=3 in docs/cli-reference.md; git diff shows generator output only"
        status: pass
      - kind: unit
        ref: "tests/test_docs.py (13 passed)"
        status: pass
    human_judgment: false
  - id: D8
    description: "Phase-closing quality gate: full suite green with the coverage floor honored, ruff check/format clean, ty clean"
    requirement: LIVE-09
    verification:
      - kind: other
        ref: "env -u FORCE_COLOR NO_COLOR=1 python -m pytest -> 1149 passed, 1 skipped (the opt-in live test), 94.34% coverage (fail_under=90); ruff check src tests + ruff format --check + ty check src/sif all exit 0"
        status: pass
    human_judgment: false

duration: 18min
completed: 2026-11-08
status: complete
---

# Phase 13 Plan 04: Watch Service Install (launchd/systemd) + Docs Seal Summary

**`sif watch --install-service/--uninstall-service` generates a launchd LaunchAgent or systemd user unit that runs the FOREGROUND watcher under the OS supervisor with the install-time `-c/--embed` flags baked into an absolute-interpreter argv (SC3, never forks), installs it with explicit-argv manager calls (bootstrap/bootout-retry or daemon-reload/enable --now, verified, friendly missing-binary errors), and the generator-owned docs are regenerated to tell the whole LIVE-09 story — with a real launchd round-trip proven live twice on this machine.**

## Performance

- **Duration:** 18min | **Started:** 2026-11-07T16:30:32Z | **Completed:** 2026-11-07T16:48:00Z | **Tasks:** 2 | **Files:** 8 (3 created, 5 modified)
- **Suite:** 1149 passed, 1 skipped (opt-in live proof), 94.34% coverage (fail_under=90); ruff check/format green; ty check src/sif 0 diagnostics; live launchd round-trip passed twice (2.0s / 1.7s)
- **Estimate vs actual:** 40000 tokens estimated (confidence: low), 12914 actual (chars/4 over the realized diff) — the 13-02 flag-family/daemon precedents and the pure-text generation carried more than the estimate assumed

## Accomplishments

- **SC3 install path (D-11/D-12/D-13):** `utils/service.py` generates both artifacts as pure text — the plist via `plistlib` (Label `com.docsif.watch`, `RunAtLoad`/`KeepAlive` true, `ThrottleInterval=10`, absolute-interpreter `ProgramArguments`, log paths under the shared `user_log_dir("sif")` tree) and the systemd unit from a fixed template (`Type=simple`, `Restart=on-failure`, `RestartSec=5`, `WantedBy=default.target`, whitespace-quoted `ExecStart`). Install writes atomically (temp-then-rename, 0644), gates `shutil.which` with a typed friendly error, invokes the manager with explicit argv lists only (launchd `bootstrap gui/<uid>` with bootout-then-retry on conflict per Pitfall 5, verified via `print`; systemd `daemon-reload` + `enable --now`, verified via `is-active`), and hands the CLI the artifact path, log location, and verify command. Uninstall is stop-then-remove on both managers.
- **CLI surface:** `--install-service`/`--uninstall-service` join the 13-02 lifecycle-flag family with guards (mutual exclusion; any service flag with `--detach`/`--stop` rejected — the supervised watcher never forks). The argv tail bakes exactly the invocation's `-c` names plus `--embed` iff the effective depth embeds, over a resolved absolute `--index` path. Linux installs print the `loginctl enable-linger` survive-logout note (D-13: surfaced, never silently assumed).
- **Live proof (D-13 live clause):** the opt-in integration test really bootstraps a scratch-label agent against a tmp DB on this macOS box — waits for the post-arm Watching banner, writes a file, polls the DB until the supervised watcher indexed it, then boots out and proves the artifact and service are gone. Passed twice; no leaked services; skips (never fails) without `SIF_TEST_LIVE_LAUNCHD=1`.
- **Docs seal:** the three 13-01 settings registered in the generator's SECTIONS allowlist; `make docs-generate` produced configuration.md with `SIF_MCP_WATCH`/`SIF_WATCH_RESCOPE_INTERVAL`/`SIF_WATCH_CHECKPOINT_INTERVAL` and cli-reference.md with all five lifecycle flags (`--detach`/`--stop`/`--log-file` regeneration deliberately deferred from 13-02 to this plan). Zero hand edits.
- **Phase gate:** full suite 1149 passed @ 94.34%, ruff/format/ty green — Phase 13's closing gate.

## Task Commits

1. **Task 1 (tracer, TDD): service install/uninstall module + CLI flags** — `f011a9d` (test: 17-test failing battery + zero-behavior skeleton; RED_EVIDENCE_OK, target `test_round_trip_carries_label_argv_supervision_and_logs` failing KeyError 'Label' on the planned assertion) → `f0bf62f` (feat: full module + watch flags)
   - Tracer feedback gate: all four `<verify>` commands re-run end-to-end after the production commit — 12 passed, 105 passed (flag-family regression), plist round-trip OK, ruff/format clean. `⚡ Tracer verified end-to-end — expanding.`
2. **Task 2: live proof + docs + phase gate** — `d35ce0d` (test: opt-in live launchd round-trip) + `1a98e9e` (docs: SECTIONS registration + regenerated docs)

**Plan metadata:** `see final docs commit below`

## Files Created/Modified

- `src/sif/utils/service.py` — NEW: SERVICE_LABEL/UNIT_NAME, ServiceManagerMissing/ServiceCommandError, InstallResult, build_plist/render_unit (+_watch_argv/_systemd_quote), launchd_plist_path/systemd_unit_path, _write_artifact (temp-then-rename 0644), _gate_manager, install_watch_service → _install_launchd/_install_systemd, uninstall_watch_service
- `src/sif/cli/commands/watch.py` — _check_lifecycle_guards (extracted; C901), _service_manager, _service_argv_tail, _run_install_service, _run_uninstall_service; the two new options; module docstring SC3 note
- `tests/unit/utils/test_service.py` — NEW: 12 tests (generation ×3, install argv ×2, conflict, missing manager ×3, uninstall argv ×2, AST discipline)
- `tests/unit/cli/test_watch_cmd.py` — +8 TestServiceFlags tests
- `tests/integration/test_service_live_launchd.py` — NEW: opt-in live round-trip with scratch label + safety net
- `scripts/generate_config_ref.py` — SECTIONS: three new settings registered
- `docs/cli-reference.md`, `docs/configuration.md` — regenerated output only

## Decisions Made

- The baked tail records `--embed` whenever the effective install-time depth is embed (flag or `SIF_WATCH_UPDATE_DEPTH`) — the supervised process sees no user environment, so baking the flag is the only way the service replays the depth the user installed with.
- Manager argv uses the bare binary name after a `shutil.which` presence gate: the gate owns friendliness, the argv stays the documented literal form (`["launchctl", "bootstrap", "gui/<uid>", <plist>]`), and fake-runner tests assert it exactly.
- `ServiceManagerMissing` keeps the plan-named spelling under a targeted `noqa: N818`; two `noqa: PLR0913` mark the plan-specified test-seam signatures (the WatchHostParams bundling precedent does not fit five test-seam keywords).
- Production uninstall issues `bootout` and returns without waiting for the SIGTERM'd watcher's graceful exit — launchd semantics; a re-install inside the async window is covered by the bootout-then-bootstrap retry (Pitfall 5), and the live test deadline-polls the gone state.
- The plist's `StandardOutPath`/`StandardErrorPath` point into the same `user_log_dir("sif")` tree the raw daemon logs to (D-07), so `--detach` and `--install-service` daemons are diagnosable from one directory; systemd's reported log location is the journalctl command.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Determinism] Live-test gone-state assertion was racy**
- **Found during:** Task 2 (first live run)
- **Issue:** The plan's "bootout -> artifact removed" sequence implies the service is unloaded when bootout returns, but `launchctl bootout` is asynchronous — the job leaves the gui domain only after the SIGTERM'd watcher completes its graceful flush + checkpoint, so an immediate `launchctl print` still succeeds
- **Fix:** The test deadline-polls `launchctl print` for the not-loaded outcome (`_poll_service_gone`, 30s bound); production uninstall unchanged (correct launchctl semantics)
- **Files modified:** tests/integration/test_service_live_launchd.py
- **Verification:** live round-trip passed twice (2.0s / 1.7s), no leaked services
- **Commit:** d35ce0d

**2. [Rule 1 - Plan-spec reconciliation] CLI path assertions broke on Rich's 80-column folding**
- **Found during:** Task 1 GREEN loop
- **Issue:** CliRunner output wraps at width 80, inserting newlines mid-path, so `str(artifact) in result.output` can never match long tmp paths
- **Fix:** The two path assertions compare against newline-stripped output — the assertion is about content, not wrapping
- **Files modified:** tests/unit/cli/test_watch_cmd.py
- **Verification:** TestServiceFlags 8/8 green
- **Commit:** f0bf62f

**Total deviations:** 2 auto-fixed (both Rule 1, test-side). **Impact:** none on planned behavior; every must-have truth, artifact, key_link, and prohibition is honored (no fork under the supervisor, no shell, docs generator-only, zero new deps).

## TDD Gate Compliance

| Task | RED commit | RED evidence | GREEN commit | REFACTOR |
|------|-----------|--------------|--------------|----------|
| 1 (tracer) | `f011a9d` | RED_EVIDENCE_OK (junit; target: test_round_trip_carries_label_argv_supervision_and_logs — KeyError 'Label' at the planned Label assertion; battery 17 failed / 26 pre-existing passed) | `f0bf62f` | none needed (guard extraction + lint restructuring absorbed into GREEN) |
| 2 | n/a — task type="auto" (not TDD-mandated); the live proof test ran green live twice on arrival | n/a | `d35ce0d` + `1a98e9e` | n/a |

The GREEN commit is preceded by its machine-validated RED; commit-prefix grep (`^test\(13-04\)`, `^feat\(13-04\)`, `^docs\(13-04\)`) all present. No violations.

## Issues Encountered

- Test-authoring fixes inside the RED/GREEN loops (not production deviations): the AST discipline test initially matched the skeleton docstring's prose "shell=True" (reworked to parse code, not text) and rejected pre-built list variables (tightened to forbid string constants only); watch_cmd crossed mccabe 10 after the new guards (guards extracted to `_check_lifecycle_guards`); ruff N818/D107/D205/ARG005/E501 fixed in-loop.
- The two CLI guard tests (`--install-service --uninstall-service` / with `--detach`) passed trivially during RED via exit-2 unknown-option and pass on the real guard messages in GREEN — noted in the RED record's semantic assessment.
- Pre-existing (out of scope, unchanged): ResourceWarning from 13-01's TestIdleCheckpoint (already in deferred-items.md); 4 warnings total in the full suite, all that known one.

## Authentication Gates

None — no external services or auth surfaces in this plan.

## User Setup Required

None - no external service configuration required. (`sif watch --install-service` works against any existing index; on Linux, run `loginctl enable-linger $USER` once if the service should survive logout — the install output says so.)

## Known Stubs

None — no placeholder bodies shipped. The live proof's default-machine skip is the designed opt-in gate (D-13), not a stub; it ran for real twice on this macOS dev box.

## Threat Flags

None — no security-relevant surface beyond the plan's threat model. T-13-10 (shell injection): explicit argv only, AST-pinned; T-13-11 (pre-planted artifact): atomic temp-then-rename 0644, only our own label's filename ever written/removed; T-13-12: user-scoped destinations; T-13-13 (re-install partial state): bootout-then-retry + verify + printed artifact path; T-13-SC: zero new dependencies.

## Next Phase Readiness

Phase 13 is complete — every roadmap SC is proven (SC1/SC2/SC3/SC4 plus the long-lived-host behaviors), docs tell the whole LIVE-08/LIVE-09 story, and the full quality gate is green (1149 passed @ 94.34%). Ready for `/gsd-verify-work 13`.

## Self-Check: PASSED

- Created files FOUND: src/sif/utils/service.py, tests/unit/utils/test_service.py, tests/integration/test_service_live_launchd.py
- Commits FOUND (ancestors of HEAD): f011a9d, f0bf62f, d35ce0d, 1a98e9e
- Full suite: 1149 passed, 1 skipped @ 94.34%; ruff/format/ty green; grep gates all 1+; live launchd round-trip passed twice

---
*Phase: 13-watch-everywhere-mcp-embedded-refresh-background-daemon*
*Completed: 2026-11-08*
