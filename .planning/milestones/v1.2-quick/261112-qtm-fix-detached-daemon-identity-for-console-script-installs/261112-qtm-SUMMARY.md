---
phase: quick-261112-qtm
plan: 01
subsystem: daemon-lifecycle
tags: [click, console-script, process-identity, ps, subprocess, pytest]

# Dependency graph
requires:
  - phase: 13-02 (detached daemon lifecycle)
    provides: daemon.corroborate_pid / stop_daemon / PID-file metadata contract
  - phase: 13-04 (console-script / service install)
    provides: "[project.scripts] sif = sif.cli.main:main — the installed argv shape this fix corroborates"
provides:
  - "corroborate_pid accepts the installed console-script argv shape (exact basename 'sif') alongside the sif.cli.main module marker"
  - "ps invoked with -ww so a long interpreter/script/--index prefix cannot clip the trailing watch token"
  - "real-subprocess e2e proving sif status and sif watch --stop corroborate a console-script-launched daemon"
affects: [daemon-lifecycle, status, watch-stop, packaging, console-script-installs]

actuals:
  tokens: 3753
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Program-shape corroboration: accept an exact-basename token OR the module marker, and never relax the positive subcommand token requirement"
    - "ps -ww in identity probes so default width clipping cannot hide trailing argv evidence"
    - "E2E launcher parametrization: helpers default to the module form and take an optional launcher for the installed console-script shape"

key-files:
  created: []
  modified:
    - src/sif/utils/daemon.py
    - tests/unit/utils/test_daemon.py
    - tests/integration/test_watch_daemon_e2e.py

key-decisions:
  - "Match the console-script token by exact basename equality only (os.path.basename(token) == 'sif'); lookalikes (not-sif, sif-tools, sif.exe, sif-script.py) stay rejected, preserving the fail-closed contract"
  - "Keep the positive 'watch' whitespace token requirement unchanged — identity alone never corroborates, so watch.db path fragments still fail closed"
  - "Add -ww as the first ps argument; the console-script shape places 'watch' after interpreter, script path, and --index value where default width could clip it"
  - "No changes needed in sif/cli/main.py or sif/cli/commands/watch.py — both status and --stop route through daemon.corroborate_pid"
  - "Quick-batch atomic commit policy: one commit per task (code + tests together); the Task 1 TDD RED was verified locally (planned assertion failed) before GREEN rather than committed separately"
  - "E2E stand-in console script imports main from sif.cli.main and calls sys.exit(main()), byte-matching the [project.scripts] entry point body"

patterns-established:
  - "Launcher-parametrized daemon e2e: _detach/_run_stop/_detached_daemon/_run_status resolve [sys.executable, '-u', '-m', 'sif.cli.main'] by default and forward an explicit launcher to the safety net"
  - "PID-file survival after status is the regression proof for a false-stale verdict, because a stale verdict deletes the file"

requirements-completed: []

coverage:
  - id: D1
    description: "corroborate_pid accepts the installed console-script argv shape and still accepts the module form"
    verification:
      - kind: unit
        ref: "tests/unit/utils/test_daemon.py#TestCorroboratePid::test_console_script_ps_line_corroborates"
        status: pass
      - kind: unit
        ref: "tests/unit/utils/test_daemon.py#TestCorroboratePid::test_ps_argv_with_sif_watch_markers_corroborates"
        status: pass
    human_judgment: false
  - id: D2
    description: "Fail-closed rejection preserved: no watch token, lookalike basenames, dead process, wrong-typed pid, missing ps, ps failure"
    verification:
      - kind: unit
        ref: "tests/unit/utils/test_daemon.py#TestCorroboratePid (console-script/mcp-stdio, lookalike parametrization, process-gone, ps failure, wrong-typed pid)"
        status: pass
    human_judgment: false
  - id: D3
    description: "ps invocation carries -ww so long argv prefixes cannot clip the trailing watch token"
    verification:
      - kind: unit
        ref: "tests/unit/utils/test_daemon.py#TestCorroboratePid::test_ps_invocation_requests_unlimited_width"
        status: pass
    human_judgment: false
  - id: D4
    description: "A console-script-launched daemon is reported running by sif status (PID shown, no stale verdict, PID file preserved) and stopped gracefully by sif watch --stop (PID gone, PID file removed)"
    verification:
      - kind: e2e
        ref: "tests/integration/test_watch_daemon_e2e.py#test_console_script_daemon_corroborated_by_status_and_stop"
        status: pass
      - kind: integration
        ref: "pytest tests/integration/test_watch_daemon_e2e.py --no-cov (6 passed, no leaked daemon)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Repo quality contract stays green: ruff check, ruff format --check, ty check, full pytest with 90% coverage gate"
    verification:
      - kind: other
        ref: "ruff check src tests && ruff format --check src tests && ty check src/sif && pytest (1605 passed, 1 skipped, 95.20% coverage)"
        status: pass
    human_judgment: false

duration: 4min
completed: 2026-11-12
status: complete
---

# Quick Task 261112-qtm: Detached daemon identity for console-script installs

**The installed `sif` console script is now corroborated as the daemon it is: `sif status` reports it running without deleting its PID file, and `sif watch --stop` stops it gracefully instead of reporting a false stale.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-11-12T11:39:29Z
- **Completed:** 2026-11-12T11:43:04Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `daemon.corroborate_pid` now accepts both real program shapes: the module form (`python -m sif.cli.main`) and the installed console-script form (`python <prefix>/sif`), via exact-basename matching on the `sif` token.
- `ps` is invoked with `-ww` (unlimited width) so the trailing `watch` token can never be clipped by a long interpreter/script/`--index` prefix.
- Fail-closed behavior is unchanged: the positive `watch` token is still required, lookalike basenames (`not-sif`, `sif-tools`) never corroborate, and dead/missing/unsignalable processes stay False.
- A real-subprocess e2e launches a detached daemon through a stand-in installed entry point and proves `status` (running, PID, no stale verdict, PID file survives) and `--stop` (graceful stop, PID gone, PID file removed) both corroborate it.
- Both consumers (`_watch_status_text`, `_run_stop`) needed no code change because they route through `corroborate_pid`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Accept the installed console-script argv shape in the daemon identity check** - `7f90abd` (fix)
2. **Task 2: Subprocess e2e proving a console-script daemon is corroborated by status and stop** - `94099ef` (test)

**Plan metadata:** not committed by this executor — the quick-batch orchestrator commits SUMMARY/PLAN artifacts (ADR-1239 single-writer invariant).

_Note: Task 1 carried `tdd="true"`; RED was verified locally (the new console-script test failed on its assertion before the fix) and folded into the single atomic task commit per the quick-batch commit policy._

## Files Created/Modified

- `src/sif/utils/daemon.py` - added `_CONSOLE_SCRIPT_NAME`, `_identifies_sif_cli()`, broadened the final corroboration return, added `-ww` to the ps argv, updated marker/contract docs.
- `tests/unit/utils/test_daemon.py` - five new hermetic tests: console-script shape corroborates, console-script without watch token fails, lookalike basenames fail (parametrized), ps argv carries `-ww`. All 32 pre-existing tests unchanged.
- `tests/integration/test_watch_daemon_e2e.py` - `_console_script()` stand-in entry point, `_launcher_or_default()`, launcher parameter on `_detach`/`_run_stop`/`_detached_daemon`, new `_run_status()`, and `test_console_script_daemon_corroborated_by_status_and_stop`. All five pre-existing e2e tests unchanged in behavior.

## Decisions Made

- Exact basename equality only (`os.path.basename(token) == "sif"`), never substring or prefix, so `not-sif`/`sif-tools`/`sif.exe` remain rejected. The module marker path is unchanged, so the installed-service argv (`python -m sif.cli.main`) stays covered.
- `-ww` is the first ps argument; the plan's threat model accepts the residual PID-reuse spoofing risk (T-qtm-02) because the accepted shape is exactly the operator's own CLI.
- E2E helpers keep today's module-form default when `launcher` is None, so every existing call site is behaviorally byte-identical; the safety net forwards the launcher to `--stop` and still falls back to SIGKILL + `_wait_pid_gone`.
- PID-file survival after `status` is asserted as the regression proof: a stale verdict deletes the file, so survival uniquely demonstrates the daemon was corroborated.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Ruff format collapsed the new `_identifies_sif_cli` return onto one line and reflowed one over-long e2e assert; only formatting changed, no behavior. Verified with `ruff format --check`.

## User Setup Required

None - no external service configuration required.

## Verification Evidence

- `pytest tests/unit/utils/test_daemon.py -x --no-cov` — 37 passed.
- `pytest tests/integration/test_watch_daemon_e2e.py -x --no-cov` — 6 passed in 16.79s; `ps` confirmed no lingering `watch` daemon after the run.
- Full repo contract: `ruff check src tests`, `ruff format --check src tests`, `ty check src/sif` all clean; `pytest` — 1605 passed, 1 skipped, 95.20% coverage (fail_under 90 reached).

## Next Phase Readiness

The detached-daemon lifecycle is now honest for the entry point real users invoke. No follow-on work is required for this fix; the installed-service path remains on the module form and is unaffected.

---
*Quick task: 261112-qtm*
*Completed: 2026-11-12*

## Self-Check: PASSED

- SUMMARY.md, daemon.py, test_daemon.py, and test_watch_daemon_e2e.py all present.
- Commits `7f90abd` (Task 1) and `94099ef` (Task 2) both ancestors of HEAD; each touches only its planned files.
- Working tree clean under `src/` and `tests/`; no sibling batch work touched or reverted.
