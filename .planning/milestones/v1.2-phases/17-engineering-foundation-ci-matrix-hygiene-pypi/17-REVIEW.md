---
phase: 17-engineering-foundation-ci-matrix-hygiene-pypi
reviewed: 2026-11-14T09:56:48Z
depth: standard
files_reviewed: 36
files_reviewed_list:
  - .github/workflows/publish.yml
  - .github/workflows/test-matrix.yml
  - DESIGN.md
  - Makefile
  - README.md
  - docs/api-reference.md
  - docs/architecture.md
  - docs/changelog.md
  - docs/contributing.md
  - docs/development.md
  - docs/installation.md
  - docs/models.md
  - docs/testing.md
  - examples/quickstart.py
  - pyproject.toml
  - scripts/windows_smoke.py
  - src/sif/_version.py
  - src/sif/cli/commands/index.py
  - src/sif/cli/commands/watch.py
  - src/sif/config/constants.py
  - src/sif/database/__init__.py
  - src/sif/models/__init__.py
  - src/sif/search/rerank.py
  - src/sif/search/rrf.py
  - src/sif/utils/daemon.py
  - src/sif/utils/progress.py
  - tests/conftest.py
  - tests/test_ci_workflows.py
  - tests/test_docs.py
  - tests/test_hygiene.py
  - tests/test_release_metadata.py
  - tests/test_windows_smoke_script.py
  - tests/unit/cli/test_watch_cmd.py
  - tests/unit/utils/test_daemon.py
  - tests/unit/utils/test_progress.py
  - uv.lock
findings:
  critical: 1
  warning: 9
  info: 6
  total: 16
  necessity: 1
status: issues_found
---

# Phase 17: Code Review Report

**Reviewed:** 2026-11-14T09:56:48Z
**Depth:** standard
**Files Reviewed:** 36
**Status:** issues_found

## Summary

Phase 17 delivers the CI matrix, the build-once Publish workflow, the Windows degradation smoke, the CPU-torch packaging change, the dead-layer hygiene deletions, and the 1.1.2 release identity. I verified the positive claims: the full suite passes locally (1669 passed, 1 skipped), the coverage gate passes (95.07% vs `fail_under = 90`), `ruff check src tests`, `ruff format --check src tests`, and `ty check src/sif` all pass, `uv lock --check` reports the lock in sync despite the version bump, and the workflows parse as valid YAML with the structural properties the new guard tests assert.

The submission nevertheless contains one machine-modifying defect in the new Windows smoke, plus a cluster of documentation defects that directly contradict this phase's own deliverables (the new Test Matrix workflow and the deleted test infrastructure), a runtime-markup bug the phase's own IN-01 fix missed in a shared code path, and two release-workflow hardening gaps. The theme is that several of the new guard tests assert the *text* rather than the *property*, so the docs/example/workflow drift they were meant to prevent survives a green suite.

No `## Structural Findings (fallow)` section is included because no structural pre-pass was provided.

## Narrative Findings (AI reviewer)

All findings below were produced by direct code review of the submitted files; no external reviewer evidence was supplied.

## Critical Issues

### CR-01: Windows smoke has no platform guard — an accidental POSIX run installs a persistent launchd/systemd service and forks a daemon

**File:** `scripts/windows_smoke.py:207-243`, `scripts/windows_smoke.py:246-276`
**Issue:** `_run_table()` unconditionally executes the last two "refusal" steps — `sif watch --detach` and `sif watch --install-service` — and `main()` never checks the host platform. Those invocations are expected to *fail* only on Windows, where `_run_detach` refuses at `src/sif/cli/commands/watch.py:359-366` and `_service_manager` refuses at `src/sif/cli/commands/watch.py:432-437`. On macOS/Linux the same commands succeed and leave persistent side effects:

- `--detach` double-forks a real watch daemon (`src/sif/utils/daemon.py:241-292`). The script then deletes the `TemporaryDirectory` while the daemon keeps running, so the daemon survives with a vanished collection root and its PID file already deleted.
- `--install-service` generates and installs a real OS service: on macOS `_install_launchd` writes `~/Library/LaunchAgents/com.docsif.watch.plist` and `launchctl bootstrap gui/<uid>` it (`src/sif/utils/service.py:170-173`, `:288-293`, with `RunAtLoad: True, KeepAlive: True` at `:131-132`); on Linux `_install_systemd` writes `~/.config/systemd/user/sif-watch.service` and runs `systemctl --user enable --now` (`src/sif/utils/service.py:175-177`, `:318-342`). The script never uninstalls it, so the service starts at every login and restarts forever against a deleted temp database path.

The assertion at `scripts/windows_smoke.py:203` merely records a FAIL for those steps; the side effects are already committed. `tests/test_windows_smoke_script.py` only exercises pure matcher functions, so nothing catches this. A developer running `python scripts/windows_smoke.py` locally (a natural way to validate edits to the script) silently modifies their machine.
**Fix:** Refuse to run off Windows before any step executes (and make the intent explicit in the Makefile target), or gate only the refusal steps:
```python
def main() -> int:
    if sys.platform != "win32":
        _emit("REFUSED: the Windows degradation smoke only runs on Windows "
              "(the detach/service steps would install real services elsewhere)")
        return 2
    ...
```
If cross-platform dry-runs are wanted, add a `--dry-run` that stops before the `watch` invocations. Add a unit test that `main()` returns non-zero on a non-win32 platform without invoking `_run_table`.

## Warnings

### WR-01: Shared progress renderer passes user data through Rich markup unescaped — silent text loss and `MarkupError` crashes

**File:** `src/sif/cli/commands/index.py:159-168` (also `:89`, `:122`, `:290`, `:332`, `:372`)
**Issue:** `_render_index_event` prints event payloads (file names) with `console.print(f"  [dim]Unchanged: {payload}[/dim]")` and `console.print(f"  [red]{payload}[/red]")`, but `payload` is user-controlled file data. Rich parses it as markup: a file named `report[v2].md` renders as `report.md` (text silently dropped — verified), and a file name containing a malformed closing tag such as `report[/dim].md` raises `rich.errors.MarkupError` (verified), which propagates through `IncrementalIndexer._notify` (`src/sif/indexing/incremental.py:270-274`) and aborts `sif index update` with a raw traceback. `watch.py` imports this exact function (`src/sif/cli/commands/watch.py:47`, used at `:203`), so `sif watch`'s startup reconcile crashes the same way. The phase fixed this class of bug in `_render_watch_event`/`_render_batch` (`watch.py:276-303`, IN-01) but left the shared renderer, plus `coll.name` (`:89`, `:290`, `:372`), `doc.path` (`:332`), and `coll.pre_update_cmd` (`:122`) unescaped.
**Fix:**
```python
from rich.markup import escape
...
def _on_event(event: str) -> None:
    code, _, payload = event.partition(" ")
    safe = escape(payload)
    if code == "scan":
        progress.update(task, total=int(payload))
        console.print(f"  Found {safe} files")
    elif code == "unchanged":
        console.print(f"  [dim]Unchanged: {safe}[/dim]")
    elif code == "error":
        console.print(f"  [red]{safe}[/red]")
    progress.advance(task)
```
Apply `escape()` to every user-derived value interpolated into a `console.print` markup string in `index.py` (collection names, document paths, pre-update commands).

### WR-02: CI documentation states the opposite of the workflow this phase added

**File:** `docs/testing.md:198`; `docs/development.md:699`; `docs/contributing.md:363`, `docs/contributing.md:378`
**Issue:** Three documents edited by this phase still tell contributors that the repository's only workflow is "Docs Validation" and that CI does not run the test suite or linters. That is false as of `.github/workflows/test-matrix.yml`: it runs the full 8-cell suite plus the lint job (`ruff check`, `ruff format --check`, `ty check`) on every push and pull request. Concrete contradictory text:

- `docs/testing.md:198`: "The only test workflow is `.github/workflows/docs.yml` ... It does **not** run the full pytest suite".
- `docs/development.md:699`: "No workflow runs the full test suite or linters on PRs, so run `make ci` locally before pushing."
- `docs/contributing.md:363`: "The repository has one GitHub Actions workflow, `.github/workflows/docs.yml`", and `:378`: "CI does **not** currently run the lint, format, type-check, or test suite".

`tests/test_docs.py` excludes these three files from `DOCS_FILES`, and `test_hygiene.py` only scans for dead-code literals, so the drift is invisible to the suite.
**Fix:** Rewrite the CI sections to describe both workflows: the Test Matrix (push on all branches + pull requests; 4 Python versions x ubuntu/macos; lint job with the three repo gates; coverage enforced via `addopts`/`fail_under`) and Docs Validation (docs-only paths, generation-drift gate). Add these three files to a documentation assertion (or extend `tests/test_docs.py::DOCS_FILES`) so a removed/renamed workflow fails the suite.

### WR-03: Docs still describe test infrastructure deleted by this phase

**File:** `docs/testing.md:81`, `:99`, `:115`, `:138`, `:146-164`; `docs/development.md:72`, `:85`, `:252`, `:255`, `:331`, `:335`
**Issue:** This phase deleted `tests/factories.py` and the `sample_search_options`/`sample_search_result(s)` fixtures, but both guides still present them as available:

- `docs/testing.md:81` and `docs/development.md:85`, `:252` list `factories.py` in the test tree; `docs/testing.md:146-164` and `docs/development.md:335` document `CollectionFactory`, `DocumentFactory`, `SearchOptionsFactory`, etc., and the import example `from tests.factories import DocumentFactory, SearchOptionsFactory` (which now raises ImportError). `tests/test_hygiene.py:112-114` asserts the file is gone, so the docs contradict a passing test.
- `docs/testing.md:138` and `docs/development.md:331` list `sample_search_options`, `sample_search_result(s)` as conftest fixtures; all three were removed from `tests/conftest.py` in this phase.
- `docs/testing.md:99` and `docs/development.md:255` list `tests/unit/test_search.py`, which was deleted.
- `docs/testing.md:115` and `docs/development.md:72` still describe "migrations" modules, deleted with the `MigrationManager` layer.

`test_hygiene.py:138-147` scans docs only for the literal strings `migrations.py`, `strategy.py`, `sif.models.search`, etc.; it does not catch `factories.py`, `sample_search_*`, `test_search.py`, or the bare word "migrations".
**Fix:** Remove the factories section and the `factories.py`/`test_search.py`/`sample_search_*`/migrations references from both docs, update the fixture table, and extend the hygiene doc scan (or add doc assertions) to cover `factories.py`, `sample_search_options`, `test_search.py`, and "migrations".

### WR-04: `examples/quickstart.py` is broken at runtime and prints commands that do not exist

**File:** `examples/quickstart.py:208-224`, `:271-302`, `:311-320`, `:352-357`
**Issue:** The phase updated examples 1 and 3 but left two examples and the CLI cheat-sheet broken. Running `python examples/quickstart.py` (verified) prints:

- Example 2: `Error: Collection.__init__() got an unexpected keyword argument 'path'` — `sif.core.Collection` (`src/sif/core/collection.py:8-26`) requires `id` and `name` and has no `path`; the live entity is `sif.core.models.Collection` with `path: str` (`src/sif/core/models.py:33-54`). `collection.scan_documents()` (`:223`) does not exist anywhere in `src/`.
- Example 5: `Import error: No module named 'sif.cli.config'` — that module and a `Config` class do not exist.
- Example 4 prints `sif update` (`:284`), `sif search "machine learning"` (`:287`), `sif vsearch` (`:291`), and `sif get /path/to/document.md` (`:294`); all four fail with Click usage errors (verified: `sif update`/`sif vsearch` are not registered commands, `search`/`get` are groups requiring a subcommand). The file also contradicts itself: example 3 correctly says `sif index update` and `sif search search`.

`tests/test_hygiene.py:186-199` claims the example "targets only live APIs" but only runs `py_compile` and checks two identifiers, so the breakage passes CI. This is user-facing documentation in the sdist.
**Fix:** Rewrite examples 2 and 5 against live APIs (construct `sif.core.models.Collection(name=..., path=str(tmpdir))` and scan with `FileScanner`, or drop the examples), align the printed commands with the real tree (`sif index update`, `sif search search ...`, `sif search vsearch ...`, `sif get get ...`), and add a test that executes the example with `SIF_DB_PATH` pointing at a temp dir.

### WR-05: Documented local quality gates fail on a clean checkout

**File:** `Makefile:90-92`, `:102-104`, `:161-165`; `docs/development.md:663-682`; `docs/changelog.md:43`
**Issue:** `make lint` (`ruff check .`), `make format-check` (`ruff format --check .`), `make all`, `make ci`, and `make dev-check` operate on the whole tree, but `examples/quickstart.py` — edited by this phase — violates the configured rules. Verified on the current commit: `ruff check .` exits 1 with 96 errors, all in `examples/quickstart.py` among tracked files; `ruff format --check .` exits 1 and would reformat `examples/quickstart.py`. The scoped commands CI actually runs (`ruff check src tests`, `ruff format --check src tests`) exit 0, so the divergence is invisible in CI. `docs/development.md:682` documents `make ci` as the full local CI-equivalent run and the 1.1.2 changelog claims "`make ci` covers format, lint, type, and tests"; both are false on a clean checkout.
**Fix:** Pick one scope and apply it everywhere: either fix/reformat `examples/quickstart.py` and add `examples scripts` to the CI ruff scope, or change the Makefile targets to the CI scope (`ruff check src tests`, `ruff format --check src tests`). Add a test asserting the Makefile's ruff invocations match the workflow's.

### WR-06: Publish jobs have no job-level `timeout-minutes`

**File:** `.github/workflows/publish.yml:50-70`, `:72-89`
**Issue:** Only the `build` job sets `timeout-minutes: 15` (`:14`). `publish-testpypi` and `publish-pypi` have `runs-on` but no timeout, so a hung OIDC exchange or upload holds a runner for the 6-hour default on a release path. Confirmed by parsing the YAML: both publish jobs report `timeout: None`.
**Fix:**
```yaml
  publish-testpypi:
    timeout-minutes: 10
...
  publish-pypi:
    timeout-minutes: 10
```

### WR-07: Publish workflow has no concurrency guard

**File:** `.github/workflows/publish.yml:1-10`
**Issue:** The release workflow is a deploy workflow (tag trigger, `environment: testpypi`/`pypi`, publishes artifacts) but declares no `concurrency:` group. Two tag pushes for the same ref (e.g., deleting and re-pushing a tag, or a re-run racing a push) execute two publish pipelines in parallel; the older run can finish last and upload stale artifacts to TestPyPI after the newer one. `test-matrix.yml` has a concurrency group; `publish.yml` does not.
**Fix:** Add a group keyed on the ref. Do **not** use `cancel-in-progress: true` for a publish workflow — cancelling an in-flight upload can leave the index in an ambiguous state:
```yaml
concurrency:
  group: publish-${{ github.ref }}
  cancel-in-progress: false
```

### WR-08: `sif watch --stop` can crash with `PermissionError` instead of failing closed

**File:** `src/sif/utils/daemon.py:190-197`, `:343-349`, `:352-367`; `src/sif/cli/commands/watch.py:408-422`
**Issue:** `corroborate_pid` deliberately falls through to the `ps` identity check when `os.kill(pid, 0)` raises a non-`ProcessLookupError` `OSError`, explicitly to handle "another user's process" (`daemon.py:191-195`). A process owned by another user can therefore be corroborated if its command line matches (`sif.cli.main` or basename `sif`, plus the `watch` token). `stop_daemon` then calls `_signal_or_confirm_gone`, which catches only `ProcessLookupError`; `os.kill(pid, SIGTERM)` on that corroborated foreign process raises `PermissionError`, which propagates uncaught through `stop_daemon` and `_run_stop` and turns `sif watch --stop` into a raw traceback. `_wait_gone` likewise catches only `ProcessLookupError`. This violates the module's stated fail-closed contract ("an uncorroborated PID is never signalled"; the failure should be reported, not crash). The scenario requires a shared index between users (e.g., root's `sif watch` plus a user's `--stop`), but the code itself documents the cross-user probe as reachable.
**Fix:** Handle the permission case explicitly and report it instead of raising:
```python
def _signal_or_confirm_gone(pid: int, sig: int) -> bool:
    try:
        os.kill(pid, sig)
    except ProcessLookupError:
        return True
    except PermissionError:
        logger.warning("Not permitted to signal PID %s; leaving it running", pid)
        return True  # caller must not claim "stopped"
    return False
```
Add a `StopOutcome` status such as `"not_permitted"` (and a `_run_stop` ClickException) so the CLI does not print "stopped" for an un-signalled process; catch `OSError` in `_wait_gone` as well.

### WR-09: Impossible-state guard — unreachable `if not coll: continue` in both index commands

**File:** `src/sif/cli/commands/index.py:86-87`, `:287-288`
**Category:** necessity
**Issue:** In `update_cmd`, `collections` is either `[found]` after `if not found: raise click.ClickException(...)` (`:65-68`) or `coll_repo.list_all()`, whose return type is `list[Collection]` built unconditionally from rows (`src/sif/database/repositories.py:64-67`). In `embed_cmd`, `collections[0]` is explicitly checked and raised on (`:262-264`), and the else branch is again `list_all()`. `Collection` (`src/sif/core/models.py:33-54`) defines neither `__bool__` nor `__len__`, so a `Collection` instance is always truthy: the guarded state (a falsey element in a `list[Collection]`) cannot occur. The same pattern in `watch.py` is different because its `_select_collections` helper is a separate call site, but here both lists are proven non-`None` in the same function.
**Fix:** Remove the two branches. If a future repository may return `None`, widen the element type to `Collection | None` and keep the check — do not leave a dead branch that implies the repository can return `None` when it cannot.

## Info

### IN-01: New CI guards assert text, not the properties their names claim

**File:** `tests/test_ci_workflows.py:181-201`, `:159-178`, `:232-240`; `tests/test_hygiene.py:186-199`
**Issue:** Several new guards give false confidence:
- `test_matrix_declares_eight_cells` (name and docstring say "fixed literal 4 x 2") only checks that the four version tokens and two OS tokens appear somewhere, and that the exact `PYTHON_VERSION_MATRIX` string occurs once; it never counts the cartesian product or asserts the `os:` list, so a regression to a 4-cell or 1-OS matrix can pass.
- `test_installation_docs_match_extras` asserts `"torch" in text`, which is satisfied by any occurrence of the word and does not verify the extras block it claims to guard.
- `test_setup_uv_is_sha_pinned` covers only `setup-uv`; it does not inspect the other `uses:` lines, so its name overstates the policy.
- `test_hygiene.py::test_quickstart_example_compiles` claims the example "targets only live APIs" while only compiling it (see WR-04).
**Fix:** Parse the matrix lists and assert `len(python_versions) * len(os_list) == 8`; assert the exact `torch` entry line inside the `embed` block; iterate every `uses:` line and require a 40-hex SHA except for a documented allowlist; and make the quickstart guard execute the example.

### IN-02: The documentation command guard is blind to most top-level commands and lists a nonexistent group

**File:** `tests/test_docs.py:243-263`, `:265-290`, `:21-32`
**Issue:** `_SUBCOMMANDS` contains `"config": ["show"]`, but no `config` command exists in `src/sif/cli/main.py`; conversely `watch`, `status`, `ls`, `pull`, `bench`, `suggest`, and `cleanup` are absent, so `_verify_sif_command` silently skips their tokens and appends only `--help`. Every `sif watch --detach` / `--install-service` line newly documented in `README.md` and `docs/installation.md` is therefore never validated, and `examples/quickstart.py` is not in `DOCS_FILES` at all. This is why the broken commands in WR-04 survive.
**Fix:** Derive the known command tree from the live Click group at test time instead of hard-coding `_SUBCOMMANDS`, drop the phantom `config` entry, and add `examples/quickstart.py` to the validated set.

### IN-03: Stale counts and a stale "search models" claim remain in the docs

**File:** `docs/testing.md:4`, `:192`; `docs/architecture.md:54`, `:621`; `docs/api-reference.md:227-232`
**Issue:** `docs/testing.md:4` says "three root-level suites" and "1629 tests in total"; the tree now has seven root-level test modules and the suite reports 1669 tests. `docs/testing.md:192` reports "95.06% coverage (7615 statements, 376 missed)"; the current run is 95.07% with 7509 statements/370 missed. `docs/architecture.md:54` and `:621` still say the `models/` package holds "search schemas"/"search models" even though `src/sif/models/search.py` was deleted in this phase. `docs/api-reference.md:227-232` now documents `SearchOptions` under "## Models Module" while the shown class is imported from `sif.core.models` (`src/sif/core/models.py:272`), so the section placement misattributes it to `sif.models`.
**Fix:** Update the counts (or remove volatile numbers in favor of a command), delete "search models" from the `models/` descriptions, and move the `SearchOptions` block under a core-domain heading.

### IN-04: Release-path inputs are not reproducible or hard-pinned

**File:** `.github/workflows/publish.yml:19-24`, `:41`, `:67`, `:89`
**Issue:** `pypa/gh-action-pypi-publish@release/v1` is a mutable branch ref used in the two jobs that hold `id-token: write` (`:57-58`, `:79-80`), so the code that receives the OIDC token can change without any commit in this repository; `uvx twine check` (`:41`) and `setup-uv` without a `version:` input install latest-by-default tools, so the metadata gate and the build toolchain drift over time. Version tags such as `actions/checkout@v7` are accepted pins under the CI/CD rubric, so those are not findings; the pypa branch ref is a branch, not a tag.
**Fix:** SHA-pin `pypa/gh-action-pypi-publish`, pass an explicit uv `version:` to `setup-uv`, and pin twine (e.g., `uvx twine@6.1.0 check dist/*`). Extend the existing SHA-pin guard test to every `uses:` line with a documented allowlist.

### IN-05: No automated gate ties the published tag to a green Test Matrix run

**File:** `.github/workflows/publish.yml:29-35`; `docs/development.md:574`, `:583`
**Issue:** The only pre-publish correctness gate is the tag-equals-`_version.py` shell check; nothing verifies that the tagged commit passed the Test Matrix, and there is no automated smoke install of the TestPyPI artifact before PyPI. `docs/development.md` makes confirming green CI a manual step, so a tag pushed on a red commit publishes. The build-once/promote structure is otherwise correct.
**Fix:** Add a job that queries the commit's check runs (for example `gh api repos/${{ github.repository }}/commits/${{ github.sha }}/check-runs` and fails unless the Test Matrix conclusion is `success`) and make `publish-pypi` depend on it; optionally add a `pip install --index-url https://test.pypi.org/simple --extra-index-url https://pypi.org/simple docsif==<version>` smoke between the two publishes.

### IN-06: `--embed` and `--no-embed` together are accepted; embed silently wins

**File:** `src/sif/cli/commands/watch.py:253-264`, `:540-549`
**Issue:** `_effective_depth` checks `--embed` first and returns `"embed"`, so `sif watch --embed --no-embed` (and the same pair passed to `--install-service`, whose baked depth comes from `params.depth`) silently ignores `--no-embed` instead of rejecting the contradictory request. Neither help text documents the precedence, and `_check_lifecycle_guards` does not cover this pair.
**Fix:** Reject the combination in `_check_lifecycle_guards`:
```python
if embed and no_embed:
    raise click.ClickException("--embed and --no-embed are mutually exclusive.")
```
or document the precedence explicitly in both help strings.

---

_Reviewed: 2026-11-14T09:56:48Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
