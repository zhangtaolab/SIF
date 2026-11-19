---
phase: quick-261119-fww
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/support.py
  - tests/unit/cli/test_index_locking.py
  - tests/unit/utils/test_service.py
  - tests/unit/cli/test_watch_cmd.py
  - tests/unit/indexing/test_drift.py
  - tests/unit/utils/test_daemon.py
  - tests/unit/cli/test_context.py
  - tests/unit/cli/test_get.py
  - tests/unit/database/test_repositories.py
  - tests/unit/database/test_maintenance.py
  - tests/unit/search/test_context_attach.py
  - tests/unit/utils/test_paths.py
  - tests/unit/mcp/test_backend.py
  - tests/unit/mcp/test_daemon.py
  - tests/unit/cli/test_search.py
  - tests/unit/search/test_benchmark_metrics.py
  - tests/unit/scripts/test_harrier_eval.py
  - tests/integration/test_watch_daemon_e2e.py
  - tests/integration/test_watch_e2e.py
  - src/sif/cli/commands/ls.py
  - src/sif/cli/commands/collection.py
  - tests/test_ci_workflows.py
  - pyproject.toml
  - uv.lock
  - docs/installation.md
  - docs/changelog.md
autonomous: true
requirements: [QUICK-WIN-PORTABILITY-FOLLOWUPS]
estimate:
  tokens: 110000
  raw_tokens: 70000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "On Windows with `PYTHONUTF8=1` and a fresh `--basetemp`, `python -m pytest --collect-only -q --no-cov` (no `--ignore`) exits 0, and the final full `python -m pytest -q` run reports 0 failed and 0 errors with every skip carrying a Windows-only reason."
    - "`tests/unit/cli/test_index_locking.py` guards its POSIX flock dependency with a module-level `pytest.importorskip(\"fcntl\")`, so collecting it on Windows is a skip instead of an ImportError."
    - "Every test that creates a symlink goes through `tests/support.py::symlink_or_skip`: a privileged Windows host (Developer Mode) still runs the test, and an unprivileged host skips it with a WinError 1314 reason."
    - "The `ls` and `collection ls` subpath filters compare `Path.as_posix()` forms on both sides, so the five `test_ls` and five `test_collection` subpath tests pass on Windows with no POSIX-encoding skips."
    - "Every baseline failure and error is mapped to a classification-table row in the SUMMARY: POSIX-only flock/fork/service/signals, symlink privilege, POSIX path semantics, or POSIX permission bits; the one unfixed genuine product defect (signal.SIGKILL in the daemon stop escalation) is recorded with file and line."
    - "(`embed` and `all`) require `torch>=2.11`; uv.lock keeps `revision = 5`, resolves the same torch builds (2.14.1 / 2.14.1+cpu / 2.15.0 / 2.15.0+cpu), and its only content change is the four torch requires-dist specifiers; `uv run --frozen --extra dev --extra embed` still resolves."
    - "docs/installation.md states `torch>=2.11` in both inventory mentions and recommends torch 2.14 or newer; tests/test_ci_workflows.py pins the new floor; ruff check, ruff format --check, and the full pytest suite are green."
  artifacts:
    - "tests/support.py — shared `symlink_or_skip` helper that skips only when the host forbids symlink creation"
    - "tests/unit/cli/test_index_locking.py — fcntl importorskip guard"
    - "POSIX-only service/daemon/e2e test modules — targeted Windows-only skipif markers and module-level pytestmark"
    - "src/sif/cli/commands/ls.py and src/sif/cli/commands/collection.py — as_posix-normalized subpath filtering"
    - "tests/unit/cli/test_search.py — platform-neutral truncation assertions"
    - "pyproject.toml, uv.lock, tests/test_ci_workflows.py, docs/installation.md, docs/changelog.md — torch floor lowered to >=2.11 with 2.14+ recommendation"
    - ".planning/quick/261119-fww-windows-portability-follow-ups-guard-fcn/261119-fww-SUMMARY.md — completed classification table with actual counts and final suite totals"
  key_links:
    - "tests/support.py::symlink_or_skip -> alias_pair fixtures and inline symlink call sites in the eight affected modules"
    - "src/sif/cli/commands/ls.py and src/sif/cli/commands/collection.py as_posix comparison -> test_ls and test_collection subpath tests"
    - "pyproject torch floor -> uv.lock docsif requires-dist rows -> tests/test_ci_workflows.py::test_pyproject_extras_floors and ::test_installation_docs_match_extras"
    - "Task 1 baseline full-suite output -> classification table rows -> Task 3 final zero-failure proof in the SUMMARY"
---

<objective>
Make SIF's Windows test run honest and complete: guard the POSIX-only `fcntl` import so the suite collects, mark only the tests that exercise behaviour Windows intentionally does not support (or that encode POSIX path/permission semantics), fix the two small genuine Windows defects the failures expose, and lower the torch extra floor to the verified minimum 2.11 while keeping 2.14+ as the recommendation.

Purpose: a Windows host must be able to run the entire suite without `--ignore` and without hiding real defects; `torch>=2.14` currently rejects the three verified vendor builds (`2.11.0+cpu`, `2.11.0+cu130`, `2.11.0+xpu`).

Output: one shared symlink helper, targeted Windows-only skips with precise reasons, two platform-neutral product fixes, a complete failure-classification table, one lock regeneration with a four-line content diff, updated install docs and packaging contract tests, and a green full quality suite.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/WINDOWS.md
@.planning/quick/261119-bl9-windows-conda-env-verification-for-sif-c/261119-bl9-env-matrix.md
@pyproject.toml
@tests/unit/cli/test_index_locking.py
@tests/unit/database/test_locking.py
@tests/unit/utils/test_service.py
@tests/unit/cli/test_watch_cmd.py
@src/sif/cli/commands/ls.py
@src/sif/cli/commands/collection.py
@src/sif/utils/daemon.py
@docs/installation.md
@tests/test_ci_workflows.py

Do NOT @-reference uv.lock (3,000+ lines); inspect it with the targeted grep commands below.

Planning-time observations (live, 2026-11-19, HEAD 7093fb1, clean tree, repo venv via `uv run --frozen --extra dev --extra embed`):

- Baseline full suite on Windows at 82df76b: 3148 passed, 63 failed, 27 errors, 10 skipped, coverage gate green at 94.23%. Collection additionally fails outright unless `tests/unit/cli/test_index_locking.py` is ignored, because that module has a top-level `fcntl` import.
- The 27 errors were reproduced exactly by planning probes and all come from symlink-creating fixtures: `test_context` 4, `test_get` 4, `test_repositories` 9, `test_context_attach` 10. The host lacks the symlink privilege (WinError 1314).
- Planning probes reproduced 60 of the 63 baseline failures. Exact probes (PYTHONUTF8=1, `--no-cov`, fresh `--basetemp`):
  - `test_context` 5 failures: 2 alias/self-heal (symlink), 1 un-expandable `~user`, 2 bracket-named targets whose filename contains `/`.
  - `test_context_attach` 1 failure: un-expandable `~user` (`ntpath` maps `~user` to `C:\Users\<user>` instead of raising, and `normalize_path` returns that expanded form).
  - `test_maintenance` 4: 2 symlink, 2 `0600` mode assertions (Windows stats report 0666).
  - `test_daemon` 6: 1 symlink, 1 `0600` mode assertion, 1 real `signal.SIGKILL` escalation, 3 `os.killpg` mocks.
  - `test_backend` 2 symlink; `test_paths` 1 symlink; `test_drift` 1 lock-file assertion.
  - `test_service` 6: launchd `os.getuid`, systemd/launchd file-mode and ExecStart quoting over Windows paths.
  - `test_watch_cmd` 6: CLI service install/uninstall success paths, which Windows refuses.
  - `test_ls` 5 and `test_collection` 5: subpath filtering compares `str(Path)`/`startswith(target + "/")`, so Windows backslashes never match.
  - `test_search` 2: Rich allocates one column cell narrower on Windows, so exact `"A" * 15` / `"B" * 34` truncation literals miss while the full 55-char strings are correctly truncated.
  - `test_benchmark_metrics` 1: drive-less `/tmp/...` root is not absolute on Windows.
  - `test_harrier_eval` 2: `Path("/")` is not the Windows drive root.
  - `tests/integration/test_watch_daemon_e2e.py` 5 and `tests/integration/test_watch_e2e.py` 6: POSIX double-fork detach and `Popen.send_signal(SIGINT)` (Windows subprocess rejects SIGINT).
  - `tests/unit/mcp/test_daemon.py::TestMcpDaemonEndToEnd::test_daemon_bind_failure_removes_pid_and_propagates` 1: `mcp daemon` refuses on Windows before the patched detach.
- Genuine product defects found: (1) `src/sif/cli/commands/ls.py` and `collection.py` subpath separator comparison (small fix, in scope); (2) `src/sif/utils/daemon.py::_terminate_corroborated` uses `signal.SIGKILL`, which does not exist on Windows, so a `watch --stop` that outlives the SIGTERM wait would raise AttributeError — record it, do not fix (it changes signal semantics and has no Windows-reachable regression).
- Lock regeneration tooling matters. The host `uv` is 0.8.12; running `uv lock` with it rewrites `revision = 5` to `revision = 3` and rewrites dependency marker metadata (102 non-torch lines). Using `uvx --from uv==0.13.8 uv lock` produces exactly the intended 10-line diff: the four torch requires-dist specifiers change from 2.14 to 2.11 and nothing else. Resolved torch builds stay 2.14.1 / 2.14.1+cpu / 2.15.0 / 2.15.0+cpu.
- `uv lock --check` with the host 0.8.12 currently passes on the revision-5 lock, and `uv run --frozen --extra dev --extra embed` resolves torch 2.15.0+cpu on this Windows host.
- `tests/unit/cli/test_index_locking.py` mirrors `tests/unit/database/test_locking.py`, which already uses `fcntl = pytest.importorskip("fcntl", reason="flock arbitration is POSIX-only (A2)")`.
- `tests/unit/mcp/test_daemon.py` already uses `@pytest.mark.skipif(not hasattr(os, "fork"), reason="POSIX double-fork daemon(s)")` for its real daemon tests; reuse that exact style.
- `tests/unit/scripts/test_harrier_eval.py` already catches `(NotImplementedError, OSError)` around its one symlink and skips; leave it.
- `tests/test_docs.py` needs `PYTHONUTF8=1` under the GBK locale; every pytest command below sets it.
- `uv run` keeps the coverage addopts; scoped runs use `--no-cov`, the final full run deliberately does not, so the `fail_under = 90` gate stays active.

Failure classification table (planning expectation — the executor must replace "expected" with actual counts from Task 1's baseline run and add a row for any unlisted failure; a skipped test that is not in this table is a defect, not a pass):

| # | Group | Baseline evidence (probe) | Files / test IDs | Classification | Planned action | Expected count |
|---|-------|---------------------------|------------------|----------------|----------------|----------------|
| A | Collection blocker | collection ImportError without `--ignore` | `tests/unit/cli/test_index_locking.py` (whole module) | POSIX-only flock | module-level `pytest.importorskip("fcntl")` | 5 skipped |
| B | Symlink fixtures | 27 errors at fixture setup, WinError 1314 | `test_context` 4, `test_get` 4, `test_repositories` 9, `test_context_attach` 10 | host symlink privilege | `symlink_or_skip` in each fixture | 27 skipped |
| C | Symlink inline | WinError 1314 | `test_context` 2, `test_paths` 1, `test_maintenance` 2, `test_daemon` 1, `test_backend` 2 | host symlink privilege | `symlink_or_skip` at each call site | 8 skipped |
| D | POSIX service management | `os.getuid` AttributeError, 0644 vs 0666, ExecStart quoting | `test_service` 6, `test_watch_cmd` 6 | Windows refuses service installs; POSIX managers | targeted `skipif(sys.platform == "win32")`; platform-guard the systemd mode assertion | 11 skipped + 1 runs |
| E | POSIX daemon & signals | missing `SIGKILL`, `killpg`, fork detach, SIGINT subprocess | `test_drift` 1, `test_daemon` 4, `test mcp daemon` 1, `test_watch_daemon_e2e` 5, `test_watch_e2e` 6 | POSIX-only process/signal control | targeted skipif / module `pytestmark` | 17 skipped |
| F | POSIX path semantics | drive-less roots, `Path("/")`, `~user`, `/` in filename | `test_context` 3, `test_context_attach` 1, `test_benchmark_metrics` 1, `test_harrier_eval` 2 | POSIX semantics | targeted `skipif(sys.platform == "win32")` | 7 skipped |
| G | POSIX permission bits | 0600/0644 vs 0666 | `test_daemon` 1, `test_maintenance` 2, `test_service` 1 | Windows has no POSIX mode bits | guard the mode assertions with `sys.platform != "win32"`; the functional assertions still run | 4 run, 0 skipped |
| H | Subpath separator defect | Windows backslashes never match `/` suffix | `test_ls` 5, `test_collection` 5 | genuine Windows defect | normalize both sides with `Path.as_posix()` in `ls.py` and `collection.py` | 10 fixed |
| I | Rich layout brittleness | title cell truncates one char narrower on Windows | `test_search` 2 | console layout difference, not a product defect | relax the exact width literals to platform-neutral truncation checks | 2 fixed |
| J | Genuine defect recorded | `signal.SIGKILL` absent on Windows | `src/sif/utils/daemon.py::_terminate_corroborated` | genuine product defect | record file/line in SUMMARY and do not fix | 1 recorded |
| K | Reconciliation | baseline 63 failed / 27 errors | full suite at 82df76b | — | run the pre-change baseline in Task 1; identify every unlisted failure and add a row | 60/63 reproduced by probes |

</context>

<tasks>

<task type="auto">
  <name>Task 1: Capture the baseline, unblock collection, and mark POSIX-only service/daemon/signal behaviour</name>
  <files>tests/unit/cli/test_index_locking.py, tests/unit/utils/test_service.py, tests/unit/cli/test_watch_cmd.py, tests/unit/indexing/test_drift.py, tests/unit/utils/test_daemon.py, tests/unit/mcp/test_daemon.py, tests/integration/test_watch_daemon_e2e.py, tests/integration/test_watch_e2e.py</files>
  <precondition>The repo venv works via `uv run --frozen --extra dev --extra embed`, `PYTHONUTF8=1` is set for every pytest run, and pyproject still declares the torch floor at 2.14 (so the baseline matches the recorded 63-failure state).</precondition>
  <action>
    0. Baseline evidence first. Run the full suite with the collection blocker excluded: `PYTHONUTF8=1 uv run --frozen --extra dev --extra embed python -m pytest -q --no-cov --tb=no -rfE -p no:cacheprovider --ignore=tests/unit/cli/test_index_locking.py --basetemp="C:/Users/forre/AppData/Local/Temp/gsd-fww-baseline-$$"`. Record the summary line and every FAILED/ERROR test ID in your notes for the Task 3 SUMMARY table. Expect 63 failed / 27 errors at this HEAD; if a failure is not in the classification table, add a row with its classification before editing anything.

    1. `tests/unit/cli/test_index_locking.py`: remove the top-level `import fcntl` line and, after the import block, add the same guard the sibling `tests/unit/database/test_locking.py` uses: bind `fcntl = pytest.importorskip("fcntl", reason="flock arbitration is POSIX-only (A2)")`. Do not wrap the tests individually; the whole module exercises POSIX flock semantics and on Windows the production `index_lock` degrades to a warning with no lock file, so every test in the module is POSIX-only.

    2. `tests/unit/utils/test_service.py`: add targeted `@pytest.mark.skipif(sys.platform == "win32", reason=...)` markers (import `sys` if absent). Skip these five with reasons naming the POSIX cause: `TestUnitGeneration::test_rendered_text_carries_sections_and_exec_start` (systemd ExecStart quoting over a Windows drive path; systemd units are POSIX-only), `TestInstallArgvLaunchd::test_bootstrap_then_print_with_domain_target_and_mode` (launchd domain target uses `os.getuid`), `TestReinstallConflict::test_first_bootstrap_failure_runs_bootout_then_retries` (same), `TestRunTimeout::test_timeout_maps_to_service_command_error` (launchd install reaches `os.getuid`), `TestUninstallArgv::test_launchd_bootout_then_unlink` (same). In `TestInstallArgvSystemd::test_reload_enable_now_then_is_active` keep the test running and guard only its `_mode_of(unit_path) == 0o644` assertion with `if sys.platform != "win32":`; Windows reports 0666 and cannot enforce POSIX modes.

    3. `tests/unit/cli/test_watch_cmd.py`: add a Windows-only skipif to the six service success-path tests whose behaviour Windows intentionally refuses: `test_install_prints_artifact_log_and_verify_and_bakes_tail`, `test_install_on_linux_documents_linger`, `test_uninstall_reports_stop_then_remove`, `test_install_bakes_no_embed_flag_under_ambient_embed_setting`, `test_install_plain_bm25_still_bakes_no_embed`, `test_missing_manager_surfaces_as_click_error`. Use a reason naming the degradation-only contract ("the watch service is refused on Windows; service install/uninstall is POSIX-only"). Leave the rejection tests and `test_windows_refuses_the_service_with_the_foreground_remedy` untouched.

    4. `tests/unit/indexing/test_drift.py`: skip only `TestRefreshDrifted::test_refresh_creates_the_lock_file_only_when_working` on Windows with a reason naming POSIX flock and the degrade-without-lock-file behaviour.

    5. `tests/unit/utils/test_daemon.py`: skip `TestStopEscalation::test_alive_at_deadline_sends_term_then_kill_and_unlinks` with a reason naming the absent POSIX SIGKILL (and reference the recorded daemon defect), and skip the three `TestDetachTimeout` tests that mock `os.killpg` with a reason naming POSIX process-group kill and the Windows detach refusal. Keep `test_detach_requires_fork` untouched — it is the Windows refusal proof.

    6. `tests/unit/mcp/test_daemon.py`: add the existing style `@pytest.mark.skipif(not hasattr(os, "fork"), reason="POSIX double-fork daemons")` to `TestMcpDaemonEndToEnd::test_daemon_bind_failure_removes_pid_and_propagates`, because the CLI refuses daemon arming on Windows before the patched detach runs.

    7. `tests/integration/test_watch_daemon_e2e.py`: add a module-level `pytestmark = pytest.mark.skipif(not hasattr(os, "fork"), reason="POSIX double-fork daemon e2e; Windows refuses detached watch")`. Every test in the module uses the detached daemon lifecycle, so a module marker is the narrowest correct mechanism.

    8. `tests/integration/test_watch_e2e.py`: add a module-level `pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="the e2e harness stops the watcher with Popen.send_signal(SIGINT), unsupported on Windows; foreground watch stays covered by the Windows smoke")`. Confirm first that all six tests in the module share the SIGINT stop helper; if one does not, move the marker to the tests that do.

    Scope discipline: only skip tests whose behaviour Windows intentionally does not support or whose harness is POSIX-only. Never skip a test whose failure reveals a product bug; such a test belongs in the classification table as a genuine defect.
  </action>
  <verify>
    <automated>
      set -e
      grep -q 'pytest.importorskip("fcntl"' tests/unit/cli/test_index_locking.py
      test "$(grep -c '^import fcntl' tests/unit/cli/test_index_locking.py)" = "0"  # [HEAD=1 EXPECT==0; no $ anchor because the worktree is CRLF]
      grep -q 'hasattr(os, "fork")' tests/integration/test_watch_daemon_e2e.py
      grep -q 'sys.platform == "win32"' tests/integration/test_watch_e2e.py
      PYTHONUTF8=1 uv run --frozen --extra dev --extra embed python -m pytest tests/unit/cli/test_index_locking.py tests/unit/utils/test_service.py tests/unit/cli/test_watch_cmd.py tests/unit/indexing/test_drift.py tests/unit/utils/test_daemon.py tests/unit/mcp/test_daemon.py tests/integration/test_watch_daemon_e2e.py tests/integration/test_watch_e2e.py -q --no-cov --basetemp="C:/Users/forre/AppData/Local/Temp/gsd-fww-t1-$$"
    </automated>
  </verify>
  <done>
    - The baseline full-suite summary and every FAILED/ERROR ID are captured for the SUMMARY table, and any ID missing from the table has a new classification row
    - `test_index_locking.py` collects on Windows as a skip, never an ImportError
    - The scoped run above exits 0 with zero failures and zero errors; every new skip is Windows-only and names its POSIX/degradation cause
    - No test was skipped merely to hide a product defect
  </done>
</task>

<task type="auto">
  <name>Task 2: Symlink helper, POSIX path-semantics marks, and the two small genuine Windows fixes</name>
  <files>tests/support.py, tests/unit/cli/test_context.py, tests/unit/cli/test_get.py, tests/unit/database/test_repositories.py, tests/unit/database/test_maintenance.py, tests/unit/search/test_context_attach.py, tests/unit/utils/test_paths.py, tests/unit/mcp/test_backend.py, tests/unit/utils/test_daemon.py, tests/unit/search/test_benchmark_metrics.py, tests/unit/scripts/test_harrier_eval.py, tests/unit/cli/test_search.py, src/sif/cli/commands/ls.py, src/sif/cli/commands/collection.py</files>
  <precondition>Task 1 is complete; the classification table's groups B, C, F, G, H, and I are the only remaining unhandled failures in these modules.</precondition>
  <action>
    1. Create `tests/support.py` with one shared helper and a Google-style docstring: `symlink_or_skip(link: Path, target: Path, *, target_is_directory: bool = False) -> None`. It calls `link.symlink_to(target, target_is_directory=target_is_directory)` inside a try block and, on `(NotImplementedError, OSError)`, raises `pytest.skip(...)` with a message naming Windows Developer Mode / elevation and WinError 1314. Skips must be per call site, so a privileged Windows host still runs the test.

    2. Replace every raw symlink creation in the affected tests with `symlink_or_skip` (import it with `from tests.support import symlink_or_skip`), preserving the existing target/directory semantics:
      - `tests/unit/cli/test_context.py`: the `alias_pair` fixture and every remaining inline alias site (five symlink-creation occurrences total, including the self-heal class).
      - `tests/unit/cli/test_get.py`: the alias fixture (directory target).
      - `tests/unit/database/test_repositories.py`: the `alias_pair` fixture (directory target).
      - `tests/unit/search/test_context_attach.py`: the alias fixture (directory target).
      - `tests/unit/utils/test_paths.py`: the symlink normalization test (directory target).
      - `tests/unit/database/test_maintenance.py`: the parametrized symlink target case and the exclusive-creation symlink test.
      - `tests/unit/utils/test_daemon.py`: the preplanted PID-file symlink test (file target).
      - `tests/unit/mcp/test_backend.py`: both alias tests (directory target; note the argument order differs from `Path.symlink_to`).
      Do not touch `tests/unit/scripts/test_harrier_eval.py`; its symlink test already handles the OSError itself.

    3. POSIX path-semantics skips, all `@pytest.mark.skipif(sys.platform == "win32", reason=...)` with a precise cause (import `sys` where absent):
      - `tests/unit/cli/test_context.py`: `TestContextAddNormalizedPaths::test_add_path_unexpandable_tilde_clean_error` (ntpath maps an unknown `~user` to `C:\Users\<user>` instead of failing) and both `TestContextConfirmationMarkupLiteral` bracket tests (a filename containing `/` is POSIX-only; on Windows `/` is a separator).
      - `tests/unit/search/test_context_attach.py`: `TestAttachPathContextsRealSQL::test_normalize_path_unexpandable_tilde_degrades_to_raw_form` (same ntpath `~user` semantics).
      - `tests/unit/search/test_benchmark_metrics.py`: `TestResolveCorpusRoot::test_absolute_declared_root_resolves_as_is` (a drive-less `/tmp/...` root is not absolute on Windows).
      - `tests/unit/scripts/test_harrier_eval.py`: `TestCleanupGuard::test_refuses_the_filesystem_root` and `TestCleanupGuard::test_refuses_a_nested_target_under_the_filesystem_root` (POSIX filesystem-root semantics; `Path("/")` is not the Windows drive root).

    4. POSIX permission-bit guards (the tests keep running; only the mode assertion is platform-conditional): in `tests/unit/utils/test_daemon.py::TestPidPayload::test_write_read_round_trip_with_0600_mode` and the two `tests/unit/database/test_maintenance.py` mode assertions (`test_backup_opens_verifies_and_contains_committed_rows`, `test_copy_is_owner_only_before_the_backup_api_writes`, including the recorded-modes assertion in that test), wrap the `st_mode & 0o777 == 0o600` check in `if sys.platform != "win32":`. Keep every functional assertion unconditional.

    5. Fix the genuine subpath separator defect with one platform-neutral normalization in both commands. In `src/sif/cli/commands/ls.py`, build `target = resolved.as_posix().rstrip("/")` and compare each document path's `Path(d.path).as_posix()` against `target` and `target + "/"`. Apply the identical change in `src/sif/cli/commands/collection.py` for the `FileScanner` results (`f.as_posix()`). On POSIX the strings are unchanged, so behaviour is byte-identical; on Windows both sides become forward-slash forms and the five `test_ls` plus five `test_collection` subpath tests pass. Do not change the tree-rendering code.

    6. `tests/unit/cli/test_search.py`: replace the exact width literals in `TestSearchOutputBranches::test_search_snippet_fallback_and_truncation` and `::test_vsearch_table_line_numbers_and_truncation` with a platform-neutral truncation proof — assert a short prefix is present (for example ten repeated characters) and keep the existing full 55-character absence assertion and the ellipsis assertion. The product truncates correctly; only the exact cell width differs on Windows.

    7. Run `ruff format` on the touched test files before the verify step.
  </action>
  <verify>
    <automated>
      set -e
      grep -q "def symlink_or_skip" tests/support.py
      test "$(grep -rn 'os\.symlink\|symlink_to' tests/unit tests/integration --include='*.py' | grep -v 'tests/support.py' | grep -v 'test_harrier_eval.py' | wc -l)" = "0"  # [HEAD=14 EXPECT==0]
      grep -q "as_posix" src/sif/cli/commands/ls.py
      grep -q "as_posix" src/sif/cli/commands/collection.py
      PYTHONUTF8=1 uv run --frozen --extra dev --extra embed python -m pytest tests/unit/cli/test_ls.py tests/unit/cli/test_collection.py tests/unit/cli/test_context.py tests/unit/cli/test_get.py tests/unit/database/test_repositories.py tests/unit/database/test_maintenance.py tests/unit/search/test_context_attach.py tests/unit/utils/test_paths.py tests/unit/utils/test_daemon.py tests/unit/mcp/test_backend.py tests/unit/cli/test_search.py tests/unit/search/test_benchmark_metrics.py tests/unit/scripts/test_harrier_eval.py -q --no-cov --basetemp="C:/Users/forre/AppData/Local/Temp/gsd-fww-t2-$$"
    </automated>
  </verify>
  <done>
    - `symlink_or_skip` is the only symlink-creation path in the touched tests, and the scoped run exits 0 with zero failures and zero errors
    - Groups B, C, F, and G of the classification table are handled exactly as planned; every skip names its Windows-unsupported cause
    - The five `test_ls` and five `test_collection` subpath tests pass on Windows with no skip, proving the as_posix fix
    - The two `test_search` truncation tests pass on Windows while still proving the 55-character title is truncated
    - No raw symlink call, no mode assertion, and no POSIX-semantics test is left unguarded
  </done>
</task>

<task type="auto">
  <name>Task 3: Lower the torch floor, regenerate uv.lock, update docs/contracts, and prove the full Windows suite</name>
  <files>pyproject.toml, uv.lock, tests/test_ci_workflows.py, docs/installation.md, docs/changelog.md</files>
  <precondition>Tasks 1 and 2 are complete; PyPI and https://download.pytorch.org/whl/cpu are reachable; `uvx` can run the pinned uv 0.13.8 (already used at planning time).</precondition>
  <action>
    1. In `pyproject.toml`, change the torch floor from 2.14 to 2.11 in exactly the `embed` and `all` extras, using the standard `>=` specifier and the unchanged 4-space-indented array form. Leave `sentence-transformers>=5.4.1`, `modelscope>=1.36.0`, `numpy>=1.24.0`, `llama-cpp-python>=0.3.35`, `openai>=2.0.0`, the explicit `pytorch-cpu` index, and the marker-scoped `[tool.uv.sources]` table byte-identical.

    2. Regenerate the lock with the version that produced revision 5: run `uvx --from uv==0.13.8 uv lock` from the repo root. Do not use the host 0.8.12 `uv lock` (planning proved it downgrades `revision = 5` to revision 3 and rewrites unrelated dependency markers). Do not pass `--upgrade`, `--refresh`, or package pins.

    3. Accept exactly this lock diff: the four torch rows in the docsif `requires-dist` metadata change their specifier to 2.11 (the two Linux rows keep the CPU index URL and the two non-Linux rows only change the specifier). No package name, version, source, revision, or dependency-list line may change; torch stays 2.14.1 / 2.14.1+cpu / 2.15.0 / 2.15.0+cpu. If any other change appears, stop and record the diff rather than accepting it. Never hand-edit uv.lock.

    4. `tests/test_ci_workflows.py`: update the extras-floor assertion in `test_pyproject_extras_floors` and the required tuple in `test_installation_docs_match_extras` from the old floor to the new 2.11 floor. Keep the sentence-transformers and llama-cpp-python assertions byte-identical.

    5. `docs/installation.md`: exactly two inventory mentions change to `torch>=2.11` — the Optional Dependencies table's `embed` row and the Embedding Support paragraph beginning "This installs ...". Immediately after the inventory sentence, state that torch 2.14 or newer is recommended for the widest backend compatibility and that 2.11 is the minimum supported floor (verified with the vendor cpu, cu130, and xpu builds). Do not touch README.md, docs/index.md, docs/quickstart.md, docs/mcp-server.md, or the historical 1.2.1 changelog entry.

    6. `docs/changelog.md`: add one bullet under the Unreleased "Changed" section recording that the `embed` and `all` extras now declare `torch>=2.11` (minimum supported; 2.14+ recommended) and that uv.lock was regenerated with the same resolved torch builds.

    7. Fill the classification table with the actual baseline counts from Task 1 and the post-change outcome, and write the completed table into `261119-fww-SUMMARY.md`. Record the genuine defect in `src/sif/utils/daemon.py::_terminate_corroborated` (missing `signal.SIGKILL` on Windows) with its file and line, and explicitly state that no other genuine product defect remains.

    8. Run the gates in order and stop at the first failure:
       a. Target the docs/packaging tests first: `PYTHONUTF8=1 uv run --frozen --extra dev python -m pytest tests/test_ci_workflows.py tests/test_docs.py -q --no-cov` with a fresh `--basetemp`.
       b. Collection proof without `--ignore`: `PYTHONUTF8=1 uv run --frozen --extra dev --extra embed python -m pytest --collect-only -q --no-cov` with a fresh `--basetemp`; it must exit 0.
       c. Full quality suite per CLAUDE.md, keeping the coverage gate: `PYTHONUTF8=1 uv run --frozen --extra dev --extra embed ruff check src tests`, then `... ruff format --check src tests`, then `... python -m pytest -q` with a fresh `--basetemp`. The full run must report 0 failed and 0 errors. Any remaining failure must be added to the table as a genuine defect and reported; never skip it to force green.
       d. Scope audit: `git status --porcelain` must show only the planned paths plus `.planning/` artifacts; coverage outputs (`.coverage`, `coverage.xml`, `htmlcov/`, `.venv/`) stay untracked and unstaged.

    Explicit non-goals: no torch/torchvision/torchaudio upgrade or replacement in any conda env, no `uv lock --upgrade`, no change to the CPU index or `[tool.uv.sources]`, no `ty` cleanup (22 pre-existing diagnostics stay), no tag, no push, no publish.
  </action>
  <verify>
    <automated>
      set -e
      test "$(grep -c '^    "torch>=2.11",' pyproject.toml)" = "2"  # [HEAD=0 EXPECT==2; no $ anchor because the worktree is CRLF]
      test "$(grep -c '^    "torch' pyproject.toml)" = "2"  # [HEAD=2 EXPECT==2 GUARD MUTATION: add a third indented torch item]
      test "$(grep -c 'specifier = ">=2.11"' uv.lock)" = "4"  # [HEAD=0 EXPECT==4]
      test "$(grep -c '^revision = 5' uv.lock)" = "1"  # [HEAD=1 EXPECT==1 GUARD MUTATION: regenerate with host uv 0.8.12; no $ anchor]
      test -z "$(git diff -U0 -- uv.lock | grep -E '^[+-](revision|name|version|source) = ')"  # [HEAD=0 EXPECT==0]
      uvx --from uv==0.13.8 uv lock --check
      test "$(grep -cF 'torch>=2.11' tests/test_ci_workflows.py)" = "2"  # [HEAD=0 EXPECT==2]
      test "$(grep -cF 'torch>=2.11' docs/installation.md)" = "2"  # [HEAD=0 EXPECT==2]
      grep -qF 'torch 2.14 or newer is recommended' docs/installation.md
      uv run --frozen --extra dev --extra embed python -c "import sif, torch; print(torch.__version__)"
      PYTHONUTF8=1 uv run --frozen --extra dev python -m pytest tests/test_ci_workflows.py tests/test_docs.py -q --no-cov --basetemp="C:/Users/forre/AppData/Local/Temp/gsd-fww-t3a-$$"
      PYTHONUTF8=1 uv run --frozen --extra dev --extra embed python -m pytest --collect-only -q --no-cov --basetemp="C:/Users/forre/AppData/Local/Temp/gsd-fww-collect-$$"
      PYTHONUTF8=1 uv run --frozen --extra dev --extra embed ruff check src tests
      PYTHONUTF8=1 uv run --frozen --extra dev --extra embed ruff format --check src tests
      PYTHONUTF8=1 uv run --frozen --extra dev --extra embed python -m pytest -q --basetemp="C:/Users/forre/AppData/Local/Temp/gsd-fww-full-$$"
      STATUS_OUT=$(git status --porcelain)
      test -z "$(printf '%s\n' "$STATUS_OUT" | grep -vE '^.. \.planning/' | grep -vE '^.. (tests/support\.py|tests/unit/cli/test_index_locking\.py|tests/unit/utils/test_service\.py|tests/unit/cli/test_watch_cmd\.py|tests/unit/indexing/test_drift\.py|tests/unit/utils/test_daemon\.py|tests/unit/cli/test_context\.py|tests/unit/cli/test_get\.py|tests/unit/database/test_repositories\.py|tests/unit/database/test_maintenance\.py|tests/unit/search/test_context_attach\.py|tests/unit/utils/test_paths\.py|tests/unit/mcp/test_backend\.py|tests/unit/mcp/test_daemon\.py|tests/unit/cli/test_search\.py|tests/unit/search/test_benchmark_metrics\.py|tests/unit/scripts/test_harrier_eval\.py|tests/integration/test_watch_daemon_e2e\.py|tests/integration/test_watch_e2e\.py|src/sif/cli/commands/ls\.py|src/sif/cli/commands/collection\.py|tests/test_ci_workflows\.py|pyproject\.toml|uv\.lock|docs/installation\.md|docs/changelog\.md)$')"  # [HEAD=0 EXPECT==0]
    </automated>
  </verify>
  <done>
    - `embed` and `all` declare `torch>=2.11`; uv.lock keeps revision 5 and the same four torch builds, with only the four specifier rows changed
    - `uvx --from uv==0.13.8 uv lock --check` and `uv run --frozen --extra dev --extra embed` both succeed
    - docs/installation.md, docs/changelog.md, and tests/test_ci_workflows.py carry the new floor, and the docs recommend 2.14 or newer
    - `pytest --collect-only` without `--ignore` exits 0, and the full pytest run reports 0 failed, 0 errors, with the coverage gate green
    - The SUMMARY contains the completed classification table with actual counts, the recorded genuine daemon defect, and the final suite totals
    - `ruff check src tests` and `ruff format --check src tests` are green; the scope audit shows only the planned paths plus `.planning/`
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| package indexes -> uv.lock | PyPI and the explicit pytorch-cpu index supply the resolved artifacts recorded in the lock |
| lockfile -> developer/CI environment | `uv run --frozen` installs exactly the locked resolution; a wrongly regenerated lock changes every environment |
| Windows host -> test suite | Skips can silently hide product defects; every skip must be classified and justified |
| test harness -> production code | A POSIX-only test must never be allowed to drive a production change intended only to make it pass |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-fww-01 | Tampering | uv.lock regeneration | high | mitigate | Regenerate only with `uvx --from uv==0.13.8 uv lock`; gates assert revision 5, four 2.11 specifiers, unchanged torch builds, and no name/version/source/revision diff lines; wrong-version churn is a documented stop condition |
| T-fww-02 | Repudiation | Test skips hiding defects | high | mitigate | Task 1 captures the baseline full-suite IDs; every skip maps to a classification row; Task 3's full run must report zero failures and the SUMMARY records the one genuine unfixed defect |
| T-fww-03 | Tampering | Subpath filtering change | medium | mitigate | The as_posix normalization is byte-identical on POSIX; the five `test_ls` and five `test_collection` subpath tests prove the Windows path, and the 90% coverage gate stays active |
| T-fww-04 | Denial of service | Full-suite runs and lock resolution | low | accept | Fresh `--basetemp` per run avoids the stale pytest temp-directory WinError 5; network failure during `uv lock` is reported as a stop condition, not a pass |
| T-fww-SC | Tampering | Package-manager installs | low | accept | No new package is introduced; the change only lowers an existing floor already satisfied by the locked torch builds, and no conda env is mutated |
</threat_model>

<verification>
1. Task 1: baseline full-suite IDs captured; `test_index_locking.py` collects as a skip; POSIX service/daemon/signal tests are Windows-only skipped; scoped run exits 0.
2. Task 2: one shared symlink helper covers every symlink call site; POSIX path/permission semantics are guarded; `ls`/`collection ls` subpath tests pass on Windows; scoped 13-module run exits 0.
3. Task 3: four lock specifier rows change to 2.11 with revision and torch builds unchanged; docs and contract tests pin 2.11 with a 2.14+ recommendation; `--collect-only` without `--ignore` exits 0; the full coverage-gated suite reports 0 failed / 0 errors; ruff check and format are green; the SUMMARY table is complete.
</verification>

<success_criteria>
- Windows collects the whole suite with no `--ignore`, and the final full run has zero failures and zero errors.
- Every skip is Windows-only, narrowly scoped, and mapped to a classification row; the one genuine unfixed product defect is recorded with file and line.
- Symlink tests skip only where the host forbids symlink creation; Developer Mode users still run them.
- The subpath separator defect is fixed platform-neutrally and the ten subpath tests pass on Windows.
- `embed` and `all` require `torch>=2.11`, the lock's only content change is the four torch specifiers, and `uv run --frozen --extra dev --extra embed` still resolves.
- Install docs recommend 2.14+ while stating 2.11 as the minimum supported floor; packaging contract tests pin the new floor.
- The full quality suite (ruff check, ruff format --check, pytest with the 90% coverage gate) is green.
</success_criteria>

<output>
Create `.planning/quick/261119-fww-windows-portability-follow-ups-guard-fcn/261119-fww-SUMMARY.md` when done, including the completed failure-classification table with actual counts and the final suite totals.
</output>
