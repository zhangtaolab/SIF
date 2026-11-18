---
phase: quick-261112-qtm
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/sif/utils/daemon.py
  - tests/unit/utils/test_daemon.py
  - tests/integration/test_watch_daemon_e2e.py
autonomous: true
must_haves:
  truths:
    - "A daemon launched through the installed console-script argv shape (`python <prefix>/sif --index <db> watch --detach`) is corroborated: `sif watch --stop` prints 'Watch daemon stopped (PID n)', the daemon exits, and the PID file is removed."
    - "`sif status` against that console-script daemon prints a Watch row containing 'running' and the live PID, does not report 'stale', and leaves the PID file in place instead of deleting it."
    - "The module form `<python> -m sif.cli.main ... watch --detach` remains corroborated; the existing daemon e2e suite stays green."
    - "A ps command line carrying a bare `watch` token but neither the sif module marker nor a token whose basename is exactly `sif` never corroborates; lookalike basenames (`not-sif`, `sif-tools`) never corroborate (fail-closed preserved)."
  artifacts:
    - src/sif/utils/daemon.py
    - tests/unit/utils/test_daemon.py
    - tests/integration/test_watch_daemon_e2e.py
  key_links:
    - "daemon.corroborate_pid -> accepted argv shapes -> stop_daemon signal decision (never signal an uncorroborated PID)"
    - "daemon.corroborate_pid -> sif.cli.main._watch_status_text -> sif status Watch row and PID-file cleanup"
    - "e2e console-script wrapper body <-> pyproject.toml [project.scripts] sif = \"sif.cli.main:main\""
---

<objective>
Fix detached-daemon identity corroboration for console-script installs: a daemon started as the installed `sif` entry point must be recognized by `sif watch --stop` and `sif status`, not only when started as `python -m sif.cli.main`.

Today `daemon.corroborate_pid` requires the literal `sif.cli.main` marker (plus a positive `watch` token) in the target's ps command line. The installed console script runs as `<python> <prefix>/bin/sif --index <db> watch --detach`, whose ps line never contains `sif.cli.main` — verified live against `.venv/bin/sif`. Consequences: `sif watch --stop` reports "not running (stale PID file removed)" without signalling, and `sif status` reports the same AND deletes the healthy daemon's PID file.

Purpose: make the daemon lifecycle honest for the entry point real users invoke, while keeping every signal decision fail-closed.
Output: a broadened identity check accepting the exact console-script basename `sif` (keeping the positive `watch` subcommand token), unit tests pinning both accepted shapes and the rejection cases, and a real-subprocess e2e proving `status` + `--stop` corroborate a console-script-launched daemon.
</objective>

<execution_context>
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@pyproject.toml

Notes (verified at planning time against the current tree):
- `[project.scripts]` declares `sif = "sif.cli.main:main"` (pyproject.toml lines 73-74). A live check of a `.venv/bin/sif` launch showed the exact ps shape `.../.venv/bin/python .../.venv/bin/sif --index <db> mcp stdio` — the module marker never appears.
- Identity check today: `src/sif/utils/daemon.py` — `_CLI_MARKER`/`_WATCH_MARKER` (lines 50-54) and the final return of `corroborate_pid` (line 188) require the module marker. `stop_daemon` (line 287) then reports stale without signalling; `_watch_status_text` (`src/sif/cli/main.py` lines 109-128) reports "not running (stale PID file removed)" and deletes the live PID file.
- Both consumers route through `daemon.corroborate_pid`, so neither `src/sif/cli/commands/watch.py` nor `src/sif/cli/main.py` needs a code change.
- The installed-service argv (`src/sif/utils/service.py` `_watch_argv`) uses `python -m sif.cli.main` and stays covered by the existing module marker.
- Focused pytest runs MUST pass `--no-cov`: the repo addopts enable coverage and `fail_under = 90`, so any subset run without it fails the coverage gate.
- E2E culture to follow: `tests/integration/test_watch_daemon_e2e.py` uses real subprocesses over seeded tmp collections, `_child_env()` (SIF_-stripped, NO_COLOR), deadline-bounded polls, and a no-leak safety net in `_detached_daemon`.
- `ps -ww` (unlimited width) is accepted by both BSD/macOS and GNU ps; verified locally.
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Accept the installed console-script argv shape in the daemon identity check</name>
  <files>src/sif/utils/daemon.py, tests/unit/utils/test_daemon.py</files>
  <behavior>
    - Console-script ps line `/venv/bin/python -u /venv/bin/sif --index /tmp/watch.db watch --detach --log-file /tmp/d.log` -> corroborates (True).
    - Module ps line `/opt/python3.13 -u -m sif.cli.main --index /tmp/watch.db watch --detach` -> still corroborates (True).
    - Console-script ps line without a `watch` token (`/venv/bin/python /venv/bin/sif --index /tmp/watch.db mcp stdio`) -> False.
    - Lookalike program paths `/opt/tools/not-sif watch` and `/usr/local/bin/sif-tools watch` -> False (exact basename only).
    - The ps invocation argv includes the wide-output flag, so a long interpreter/script/`--index` prefix can never clip the trailing `watch` token.
    - Wrong-typed pid, dead process, missing ps, and ps failure all remain False and never run ps when the process is gone.
  </behavior>
  <action>
    In `src/sif/utils/daemon.py`, broaden corroboration to the two real program shapes without weakening the fail-closed contract:

    1. Add a `_CONSOLE_SCRIPT_NAME = "sif"` constant next to `_CLI_MARKER` and `_WATCH_MARKER`; rewrite the marker comment so it documents both accepted program shapes (module form `python -m sif.cli.main` and installed console-script form `python <prefix>/sif`) and states that the console-script token's basename must be exactly `sif`.
    2. Add a module-private helper `_identifies_sif_cli(command_line: str) -> bool`: True when `_CLI_MARKER` appears in the command line as today, OR when any whitespace-split token has `os.path.basename(token) == _CONSOLE_SCRIPT_NAME`. Use only exact basename equality, so lookalikes (`not-sif`, `sif-tools`, `sif.exe`, `sif-script.py`) are rejected; this lifecycle is POSIX-only (double-fork), so no Windows script suffixes are accepted.
    3. In `corroborate_pid`, keep the existing pid probe, ps lookup, and ps failure handling unchanged; change only the final return to combine `_identifies_sif_cli(result.stdout)` with the existing positive check `_WATCH_MARKER in result.stdout.split()`. The bare `watch` token requirement is NEVER relaxed (a path fragment such as `watch.db` still must not corroborate), and nothing is signalled from this function.
    4. Add `-ww` as the first ps argument (`[ps_path, "-ww", "-p", str(pid), "-o", "command="]`) so default width clipping cannot hide the `watch` token, which sits after the interpreter, script path, and `--index` value in the console-script shape. Note this rationale in the `corroborate_pid` docstring, which must also state the accepted shapes and that every other shape, a wrong-typed pid, a dead process, a missing ps, or a ps failure stays False.

    In `tests/unit/utils/test_daemon.py`, extend `TestCorroboratePid` with hermetic fakes in the existing style (monkeypatch `daemon.os.kill` with the alive fake and `daemon.subprocess` with a run fake):
    - a test that the console-script ps line above corroborates;
    - a test that the same console-script line with `mcp stdio` instead of the watch subcommand does not corroborate;
    - a parametrized test that `not-sif` and `sif-tools` basenames with a bare `watch` token do not corroborate;
    - a test with a capturing subprocess fake that asserts the ps argv passed by `corroborate_pid` contains `-ww`.

    Leave every existing test in the file unchanged; the existing module-shape, path-fragment, process-gone, and failure tests must keep passing.
  </action>
  <verify>
    <automated>pytest tests/unit/utils/test_daemon.py -x --no-cov && ruff check src/sif/utils/daemon.py tests/unit/utils/test_daemon.py && ruff format --check src/sif/utils/daemon.py tests/unit/utils/test_daemon.py</automated>
  </verify>
  <done>
    Console-script argv shape corroborates; module argv shape still corroborates; the console-script line without a watch token and both lookalike basenames fail closed; the ps call carries `-ww`; all pre-existing unit tests in `tests/unit/utils/test_daemon.py` pass; ruff check and format check are clean on both files.
  </done>
</task>

<task type="auto">
  <name>Task 2: Subprocess e2e proving a console-script daemon is corroborated by status and stop</name>
  <files>tests/integration/test_watch_daemon_e2e.py</files>
  <action>
    In `tests/integration/test_watch_daemon_e2e.py`, add real-subprocess coverage for the console-script shape without disturbing the existing module-form tests:

    1. Add a `_console_script(tmp_path: Path) -> Path` helper that writes `tmp_path / "bin" / "sif"` with a shebang naming `sys.executable` and the body an installed entry point receives for `[project.scripts] sif = "sif.cli.main:main"`: inside the `if __name__ == '__main__'` guard, import `main` from `sif.cli.main` and call `sys.exit(main())`. Create the parent directory and chmod the script 0o755.
    2. Generalize the three existing helpers with an optional keyword `launcher: list[str] | None = None`: `_detach`, `_run_stop`, and the `_detached_daemon` context manager. When `launcher` is None, resolve it to today's value `[sys.executable, "-u", "-m", "sif.cli.main"]`, so every existing test and call site stays byte-identical in behavior. The safety net in `_detached_daemon` must forward the launcher to its `_run_stop` call and keep the SIGKILL + `_wait_pid_gone` fallbacks.
    3. Add `_run_status(db_path: Path, cwd: Path, launcher: list[str] | None = None) -> subprocess.CompletedProcess[str]` building `[*launcher, "--index", str(db_path), "status"]` with `_child_env()`, `capture_output=True`, `text=True`, the existing `_STOP_TIMEOUT_S` timeout, and `check=False`.
    4. Add one test, `test_console_script_daemon_corroborated_by_status_and_stop`: seed the DB with one collection via `_seed_db`, build the console script, set `launcher = [sys.executable, "-u", str(script)]`, and detach through `_detached_daemon(db_path, tmp_path, log_path, launcher=launcher)`. After the seed row and the log's `Watching` marker confirm steady state (existing deadlines), run status through the same console-script launcher and assert: exit 0; whitespace-normalized stdout contains `running` and `PID {pid}`; it does NOT contain `stale`; and the PID file still exists (a stale verdict deletes it, so survival is the regression proof that the file was not treated as stale). Then run `--stop` through the same launcher and assert: exit 0; stdout contains `Watch daemon stopped`; stdout does NOT contain `stale`; the daemon PID is gone within `_SHUTDOWN_DEADLINE_S`; and the PID file is removed.

    Do not change the existing five tests or the helper output contracts they depend on.
  </action>
  <verify>
    <automated>pytest tests/integration/test_watch_daemon_e2e.py -x --no-cov && ruff check tests/integration/test_watch_daemon_e2e.py && ruff format --check tests/integration/test_watch_daemon_e2e.py</automated>
  </verify>
  <done>
    The new e2e launches a detached watch through the console-script argv shape, proves `sif status` reports it as running (PID shown, no stale verdict, PID file preserved) and `sif watch --stop` stops it (graceful stopped message, PID gone, PID file removed), and all five pre-existing daemon e2e tests still pass with no leaked process.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| PID file -> signal decision | `<db>.watch.pid` is same-user-writable metadata; a stale, tampered, or PID-reused payload crosses into a kill decision. |
| process argv -> identity decision | Any local process can choose a command line; the ps command line is the only identity evidence available. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-qtm-01 | Tampering | `daemon.corroborate_pid` / stale PID file | high | mitigate | Corroborate identity before any signal: exact basename `sif` or the module marker, PLUS a positive `watch` token; dead process, missing ps, ps failure, wrong-typed pid, or any mismatch fails closed and `stop_daemon` never signals. The broadened shape adds no signal path with weaker evidence. |
| T-qtm-02 | Spoofing | `daemon.corroborate_pid` / PID reuse | low | accept | Residual risk: an unrelated process whose argv is exactly `<python> <path>/sif ... watch ...` could be matched after PID reuse. It requires a same-user PID-file pointer plus an exact program-name collision with the operator's own CLI; this is the intended shape acceptance and cannot be tightened without a signed identity channel. |
| T-qtm-03 | Denial of service | `_watch_status_text` / PID-file cleanup | medium | mitigate | The e2e pins that a corroborated console-script daemon's PID file survives `sif status`; only an uncorroborated payload triggers cleanup, so the fix removes the current false-stale deletion of a live daemon's metadata. |
| T-qtm-SC | Tampering | npm/pip/cargo installs | high | accept | No package installs and no dependency changes in this plan; the change is limited to the existing stdlib-based daemon module and its tests. |
</threat_model>

<verification>
Focused:
```
pytest tests/unit/utils/test_daemon.py tests/integration/test_watch_daemon_e2e.py -x --no-cov
```

Repo contract (from CLAUDE.md) — run after both tasks:
```
ruff check src tests
ruff format --check src tests
ty check src/sif
pytest
```

All commands assume cwd at the repository root. The final `pytest` is the full suite with the repo's coverage addopts and the 90% gate.
</verification>

<success_criteria>
- `daemon.corroborate_pid` returns True for both accepted program shapes (module form and installed console-script form) with the positive `watch` token present, and False for a missing watch token, lookalike basenames, a dead process, a wrong-typed pid, a missing ps, or a ps failure.
- The ps invocation carries `-ww` so long interpreter/script/index prefixes cannot clip the trailing `watch` token.
- The new subprocess e2e proves `sif status` reports a console-script-launched daemon as running without deleting its PID file, and `sif watch --stop` stops it through the corroborated graceful path.
- All pre-existing unit and e2e tests pass unchanged; the full quality suite (`ruff check`, `ruff format --check`, `ty check`, `pytest`) is green.
</success_criteria>

<output>
Create `.planning/quick/261112-qtm-fix-detached-daemon-identity-for-console-script-installs/261112-qtm-SUMMARY.md` when done
</output>
