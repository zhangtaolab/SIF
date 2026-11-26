---
phase: 17-engineering-foundation-ci-matrix-hygiene-pypi
verified: 2026-11-24T15:46:05Z
status: passed
score: 59/60 must-haves verified
covered_files:
  - ".github/workflows/publish.yml"
  - ".github/workflows/test-matrix.yml"
  - ".planning/milestones/v1.2-phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-01-PLAN.md"
  - ".planning/milestones/v1.2-phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-01-SUMMARY.md"
  - ".planning/milestones/v1.2-phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-02-PLAN.md"
  - ".planning/milestones/v1.2-phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-02-SUMMARY.md"
  - ".planning/milestones/v1.2-phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-03-PLAN.md"
  - ".planning/milestones/v1.2-phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-03-SUMMARY.md"
  - ".planning/milestones/v1.2-phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-04-PLAN.md"
  - ".planning/milestones/v1.2-phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-04-SUMMARY.md"
  - ".planning/milestones/v1.2-phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-05-PLAN.md"
  - ".planning/milestones/v1.2-phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-05-SUMMARY.md"
  - ".planning/milestones/v1.2-phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-06-PLAN.md"
  - ".planning/milestones/v1.2-phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-06-SUMMARY.md"
  - ".planning/milestones/v1.2-phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-07-PLAN.md"
  - ".planning/milestones/v1.2-phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-07-SUMMARY.md"
  - ".planning/milestones/v1.2-phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-08-PLAN.md"
  - ".planning/milestones/v1.2-phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-08-SUMMARY.md"
  - ".planning/milestones/v1.2-phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-09-PLAN.md"
  - ".planning/milestones/v1.2-phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-09-SUMMARY.md"
  - ".planning/milestones/v1.2-phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-10-PLAN.md"
  - ".planning/milestones/v1.2-phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-10-SUMMARY.md"
  - "DESIGN.md"
  - "Makefile"
  - "README.md"
  - "docs/api-reference.md"
  - "docs/architecture.md"
  - "docs/changelog.md"
  - "docs/contributing.md"
  - "docs/development.md"
  - "docs/installation.md"
  - "docs/models.md"
  - "docs/testing.md"
  - "examples/quickstart.py"
  - "pyproject.toml"
  - "scripts/windows_smoke.py"
  - "src/sif/_version.py"
  - "src/sif/cli/commands/index.py"
  - "src/sif/cli/commands/watch.py"
  - "src/sif/config/constants.py"
  - "src/sif/database/__init__.py"
  - "src/sif/models/__init__.py"
  - "src/sif/search/rerank.py"
  - "src/sif/search/rrf.py"
  - "src/sif/utils/daemon.py"
  - "src/sif/utils/progress.py"
  - "tests/conftest.py"
  - "tests/test_ci_workflows.py"
  - "tests/test_docs.py"
  - "tests/test_hygiene.py"
  - "tests/test_release_metadata.py"
  - "tests/test_version_identity.py"
  - "tests/test_windows_smoke_script.py"
  - "tests/unit/cli/test_index.py"
  - "tests/unit/cli/test_watch_cmd.py"
  - "tests/unit/search/test_rrf.py"
  - "tests/unit/utils/test_daemon.py"
  - "tests/unit/utils/test_progress.py"
  - "uv.lock"
covered_digest: "v4:sha256:0767bc8bc072d48673884255703f60bb73a9d7860977127dea3a54b3315e31d4"
behavior_unverified: 1
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 54/55
  gaps_closed:
    - "Every push to a branch and every pull_request runs the full suite on exactly 8 test cells - Python 3.10, 3.11, 3.12, 3.13 x ubuntu-latest, macos-latest - with fail-fast: false so every cell reports."
  gaps_remaining: []
  regressions: []
advisory:
  - finding: "The workflow-reading guards in tests/test_ci_workflows.py accept 14 narrowed workflow shapes, so CI can be narrowed without a guard failing"
    category: other
    reason: "Durability gap in the regression guards, not a defect in the workflow: the file at HEAD contains none of these shapes and no must-have truth as worded claims the guards are exhaustive. Whether to add a follow-up guard is an open maintainer decision (17-VALIDATION.md Manual-Only row 8, 17-SECURITY.md T-17-32 note, 17-REVIEW.md IN-12)"
    evidence_status: "reproduced this round in a scratch directory with a mutation probe over the six workflow-reading guards"
  - finding: "Local type check reports 10 diagnostics in both local environments (miniconda py3.13 and the project .venv py3.10)"
    category: other
    reason: "Third-party typing diagnostics in embedder.py, download.py, and rerank.py from locally installed packages; CI's Type check step is green at d8b1404c, whose src/ is byte-identical to HEAD"
    evidence_status: "local environments only; CI lint job success in run 45311060690"
behavior_unverified_items:
  - truth: "Real GitHub Actions execution of the restored 8 cells cannot be verified locally; the post-merge branch-push confirmation stays a manual follow-up with a named failure path for a cancelled or red restored cell (plan 17-10, verification: backstop)"
    test: "Push a branch that carries the restored workflow, or update an open pull request, and open the Test Matrix run"
    expected: "Exactly 8 py jobs (py3.10-3.13 x ubuntu-latest, macos-latest) plus the lint job, all success, each cell passing the fail_under=90 coverage gate; a capacity-cancelled cell is re-run once, a recurrence needs a new recorded decision, a red cell is fixed forward without dropping a cell or weakening coverage"
    why_human: "GitHub Actions execution is external and nothing has been pushed: no run exists for the restored workflow, and the macOS py3.11 and py3.12 cells have not run on the current product tree (last green at 673b8e76 on 2026-11-18)"
human_verification:
  - test: "Push a branch that carries the restored workflow (any commit from 10a9685 onward), or update an open pull request, then open the Test Matrix run"
    expected: "Exactly 8 py<version> / <os> jobs (py3.10-3.13 x ubuntu-latest, macos-latest) plus lint / py3.12 / ubuntu-latest, all success, each cell logging the 90% coverage gate passing; record the run id and job conclusions"
    why_human: "GitHub Actions execution is external; nothing has been pushed, so no run exists for the restored eight-cell workflow (the newest run, 45311060690, exercised the six-cell shape)"
  - test: "Review the 17 judgment-tier prohibition verdicts in the Prohibitions table"
    expected: "Each verdict is confirmed, or the reviewer names the prohibition that is actually violated"
    why_human: "These are non-authoritative reviewer judgments of must-NOT statements, not test-backed results; human review is recommended, not a gate"
---

# Phase 17: Engineering Foundation (CI Matrix + Hygiene + PyPI) Verification Report

**Phase Goal:** Contributors get a green regression net on every push and a proven release pipeline — every later schema migration and the MCP shell swap land against a verified matrix, and `docsif` is on PyPI before the MCP Registry needs it.
**Verified:** 2026-11-24T15:46:05Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (plan 17-10), against the current tree at HEAD `13c7703` (branch `gsd/phase-24-reverify`), replacing the 2026-11-24T05:05:33Z report (`gaps_found`, 54/55). All 60 must-haves were re-derived from the ten PLAN frontmatters merged with the ROADMAP success criteria and checked against the current files and live external state. No evidence from the prior report was carried forward without a re-check this round, except where a row says so.

**What changed since the prior report.** Commits `ae1225e`..`13c7703` on top of `d3f3b8d`. Outside `.planning/`, exactly five files changed, all declared by plan 17-10: `.github/workflows/test-matrix.yml`, `tests/test_ci_workflows.py`, `docs/development.md`, `docs/contributing.md`, `docs/testing.md`. `publish.yml`, `pyproject.toml`, `uv.lock`, `src/`, and `17-CONTEXT.md` are byte-identical to the plan base `ae1225e`.

## Goal Achievement

60 must-have truths (47 outcome truths + 13 `verification: backstop` scope/residual declarations). **59/60 verified.** Truth 11, the single failed truth of the prior report, is closed: the workflow again declares the eight-cell, every-push matrix. One truth abstains: truth 60, the plan's own declaration that the restored matrix has not run on GitHub Actions.

### Observable Truths

| # | Plan | Truth | Status | Evidence |
|---|------|-------|--------|----------|
| 1 | 17-01 | Three dead layers (`models/search.py`, `search/strategy.py`, `database/migrations.py`) deleted with no surviving importer; suite collects and passes | ✓ VERIFIED | All three files absent (also `tests/factories.py`, `tests/unit/test_search.py`, `tests/unit/database/test_migrations.py`); dead-literal grep hits only the guard's own literals (`tests/test_hygiene.py:37-128`); full suite 3260 passed / 1 skipped at HEAD |
| 2 | 17-01 | Orphan `compute_rrf_score` removed while `RRFFusion` fusion behavior is byte-identical | ✓ VERIFIED | No `compute_rrf_score` in `src`/`tests`/`examples` outside the guard; `src/sif/search/rrf.py:50` `class RRFFusion`; `tests/unit/search/test_rrf.py` passes |
| 3 | 17-01 | Makefile has no pre-commit target/install/autoupdate; `.pre-commit-config.yaml` absent | ✓ VERIFIED | `grep -i 'pre-commit\|black' Makefile` empty; config file absent; `test_makefile_has_no_pre_commit_target` + `test_pre_commit_config_absent` pass |
| 4 | 17-01 | Backstop: docs sweep, tracked-junk removal, and repo-wide zero-reference scan are out of this plan's scope | ✓ VERIFIED (scope honored) | 17-08 and 17-09 verified below (truths 48-55); repo-wide unknown-junk scan remains deferred per D-09/D-12 |
| 5 | 17-02 | `uv.lock` resolves CPU-tagged torch from `download.pytorch.org/whl/cpu` on Linux, keeps a PyPI torch for macOS/Windows, contains no nvidia-*/triton | ✓ VERIFIED | `2.14.1+cpu` / `2.15.0+cpu` from the CPU registry with `sys_platform == 'linux'` markers (`uv.lock:524,526,2933-2935,3010-3012`); PyPI `2.14.1` / `2.15.0` entries (`:2902`, `:2974`); `nvidia` = 0, `triton` = 0 |
| 6 | 17-02 | No black dev dependency, no `[tool.black]`, no black in the lock | ✓ VERIFIED | No `black` token in `pyproject.toml`; 0 `"black"` package lines in `uv.lock`; guard tests pass |
| 7 | 17-02 | embed/all floor sentence-transformers >=5.4.1 and declare torch directly; all floors llama-cpp-python >=0.3.35; fastapi/uvicorn stay core | ✓ VERIFIED | `pyproject.toml:54-55,72-74`; `fastapi>=0.100.0`/`uvicorn>=0.20.0` core at `:37-38`. The torch floor is `>=2.11` since post-phase commit `848e6b6a`; the truth names no number |
| 8 | 17-02 | `pytorch-cpu` index is `explicit = true`; torch source marker-scoped to `sys_platform == 'linux'` | ✓ VERIFIED | `pyproject.toml:94-101`; `test_pyproject_cpu_index_is_explicit` passes |
| 9 | 17-02 | `uv lock --check` exits 0 on the committed lock | ✓ VERIFIED | Re-run: exit 0, "Resolved 106 packages"; lock unchanged on disk afterwards |
| 10 | 17-02 | Backstop: fleet tolerance asserted structurally; actual per-fleet resolution proven only by the 8-cell matrix | ✓ VERIFIED | Guards assert structure, never exact transitive versions. Per-fleet resolution observed on GitHub: 8/8 cells at `673b8e76` (run `44333232391`) with the same resolved package versions as today's lock (only the docsif torch specifier lines differ since), and 6/6 cells at `d8b1404c` (run `45311060690`) with byte-identical `uv.lock` |
| 11 | 17-03 | Every branch push and pull_request runs exactly 8 cells (3.10-3.13 x ubuntu/macos) with `fail-fast: false` | ✓ VERIFIED (gap closed) | `test-matrix.yml:3-6` (`push: branches: ['**']`, bare `pull_request:`), `:20-24` (2 x 4 product, no `exclude`/`include`/`if`/`continue-on-error`); YAML-parsed to exactly 8 cells. Blob `cb340cbe` is byte-identical to the file GitHub ran 8/8 green at `c819f67` and `f6092f8`. Both rewritten guards pass at HEAD and fail on the six-cell workflow. No GitHub run exists yet for the restored file; that half is carried by truth 60 |
| 12 | 17-03 | Each cell runs bare pytest (no `--no-cov`) and syncs `uv sync --frozen --extra dev --extra embed` | ✓ VERIFIED | `test-matrix.yml:41` (sync), `:44` (`uv run --frozen pytest`, no `--no-cov`); `pyproject.toml:226` addopts, `:229` fail_under 90 |
| 13 | 17-03 | Workflow-level `contents: read`, `pull_request` (not `pull_request_target`), no secrets, setup-uv SHA-pinned | ✓ VERIFIED | `test-matrix.yml:8-9`, `:6`, SHA `68559e99...` at `:30` and `:55`; forbidden-token grep over the file is empty; guard tests pass |
| 14 | 17-03 | Per-ref concurrency with `cancel-in-progress: true`; tag pushes excluded | ✓ VERIFIED | `test-matrix.yml:11-13`; the push trigger is a `branches` filter, so tag pushes cannot match (`:5`) |
| 15 | 17-03 | One lint/type job on ubuntu-latest/py3.12 runs `ruff check src tests`, `ruff format --check src tests`, `ty check src/sif` | ✓ VERIFIED | `test-matrix.yml:46-74`; `test_lint_job_runs_repo_gates` passes; the lint job succeeded on GitHub at product-identical `d8b1404c` (run `45311060690`) |
| 16 | 17-03 | The workflow run for the phase HEAD is green on 8 cells + lint | ✓ VERIFIED | `gh run view 43399300651` (live): conclusion success, headSha `f6092f8`, 8 py jobs + lint all success, `--exit-status` 0 |
| 17 | 17-03 | Backstop: matrix is a fixed literal list; an empty/dynamic/partially expanded matrix is not guard-exercised | ✓ VERIFIED (scope honored; limitation now narrower) | Still a fixed literal list. Since `10a9685` the guard also rejects `exclude`, `include`, step- and job-level `if`, `continue-on-error`, and a non-list axis (mutation probe variants V4d-V4k: all rejected), so this declaration under-claims what the guard covers; nothing over-claims |
| 18 | 17-03 | Backstop: the 8 cells compare equal in outcome; only the aggregate is asserted | ✓ VERIFIED (scope honored) | Runs `43399300651` and `43561542242`: all 8 py conclusions success; no ordering contract asserted |
| 19 | 17-04 | Detach on a platform without `os.fork` exits non-zero naming POSIX fork + foreground remedy, never a raw AttributeError | ✓ VERIFIED | Library guard `daemon.py:253-257`, CLI guard `watch.py:359-364`; `TestDetachPlatformGuard::test_detach_requires_fork` + `TestDaemonFlagGuards::test_detach_without_fork_is_refused` exist and pass |
| 20 | 17-04 | Windows install/uninstall-service refuse with a Windows-specific message before any probe | ✓ VERIFIED | `_service_manager()` win32 guard `watch.py:438-440` precedes the probe; `TestServiceFlags::test_windows_refuses_the_service_with_the_foreground_remedy` passes |
| 21 | 17-04 | Smoke uses explicit argv lists (never a shell), temp `SIF_DB_PATH`, and no model-loading command | ✓ VERIFIED | `scripts/windows_smoke.py:65-82` argv table; `:94` `subprocess.run(argv, ...)` with no `shell=`; `:286` temp `SIF_DB_PATH`; no query/vsearch/embed/pull command |
| 22 | 17-04 | Smoke asserts version, collection add, index update Added:1 + fcntl warning, BM25 JSON result, status, Removed:0 + preserved warning, detach/service refusals | ✓ VERIFIED | `scripts/windows_smoke.py:147` (version), `:166` (Added: 1), `:170` (Removed: 0), `:190` (Index Status / Documents); version read from `_version.py` (`:27`) so it holds at 1.2.3; matcher battery passes (8 tests) |
| 23 | 17-04 | `make windows-smoke` runs HEAD/dirty preflight, `uv python install`, frozen sync, smoke over `hc exec` | ✓ VERIFIED | `Makefile:81-87`; `.PHONY` `:4`; `YOGA_DIR` `:7`, `YOGA_PYTHON` `:8` |
| 24 | 17-04 | Smoke completes green on the synced yoga checkout and records the tested git HEAD | ✓ VERIFIED (recorded external run) | Recorded 8/8 PASS, exit 0, `smoke_head: 48759e2...` in `17-04-SUMMARY.md`. `hc ls` today: yoga `state: unreachable` (ssh timeout), so not re-executed. The script changed after that run only by the CR-01 non-Windows refusal (`b0d45bfa`, +20 lines, inert on Windows); the assertion table and matchers are unchanged |
| 25 | 17-04 | Backstop: smoke is not evidence of full Windows support; parity deferred to v2 | ✓ VERIFIED (scope honored) | `docs/development.md:607,737`; `docs/installation.md:7,332`; script docstring agrees |
| 26 | 17-04 | Backstop: yoga sync is a human step; script refuses a dirty tree and prints HEAD | ✓ VERIFIED (scope honored) | `git rev-parse HEAD` + `git status --porcelain` preflight at `scripts/windows_smoke.py:121-129` |
| 27 | 17-05 | `_version.py` holds the single version literal and all runtime surfaces derive it | ✓ VERIFIED (re-derived at 1.2.3) | `src/sif/_version.py:3` single literal `"1.2.3"`; `tests/test_version_identity.py` passes (4 tests); local CLI prints `sif, version 1.2.3` |
| 28 | 17-05 | README contains the exact mcp-name marker line; PyPI description derives from README | ✓ VERIFIED | `README.md:2` exact marker; `pyproject.toml:9` `readme = "README.md"`; live PyPI description carries the marker as one complete line (description line 2) |
| 29 | 17-05 | Changelog has a release section and footer link; `[Unreleased]` compares the current tag...HEAD | ✓ VERIFIED (re-derived at 1.2.3) | `docs/changelog.md:38` `## [1.2.3]`, `:291` `compare/v1.2.3...HEAD`; the `[1.1.2]` section and its footer link are retained (`:86`) |
| 30 | 17-05 | `publish.yml` is v*-tag-gated, builds once on ubuntu with `contents: read`, gates `GITHUB_REF_NAME` against `_version.py`, uploads dist, then TestPyPI → PyPI with job-scoped OIDC and environments | ✓ VERIFIED | `publish.yml:5` `tags: ['v*']`, `:7-8` `contents: read`, runpy tag gate `:29-35`, `uv build` once `:38` + upload-artifact `:43-48`, download-artifact in both publish jobs (`:60-64`, `:82-86`), `environment` `testpypi`/`pypi` (`:54-56`, `:76-78`), job-scoped `id-token: write` (`:57-58`, `:79-80`) |
| 31 | 17-05 | PyPI publish has no `skip-existing`; both publish jobs consume the same dist artifact; attestations at trusted-publishing default | ✓ VERIFIED | `skip-existing: true` only at `:70` (TestPyPI); no `uv build` in publish jobs; no `attestations:` override |
| 32 | 17-05 | 3.13 classifier appears only after a green matrix | ✓ VERIFIED | `pyproject.toml:24`; `git merge-base --is-ancestor f6092f8 9164e4f` → yes (the classifier commit `9164e4f` is a one-line pyproject change) |
| 33 | 17-05 | Release Process and installation docs document `make windows-smoke`; no `twine upload` primary path | ✓ VERIFIED | `docs/development.md:607,705,737`; `docs/installation.md:335`; `docs/contributing.md:364,436`; `grep 'twine upload' docs README.md DESIGN.md` → exit 1 (none) |
| 34 | 17-05 | Backstop: tag/version equality is exact ASCII string equality | ✓ VERIFIED (scope honored) | `publish.yml:32` `test "v${VERSION}" = "${GITHUB_REF_NAME}"` — version-agnostic |
| 35 | 17-05 | Backstop: mcp-name marker must match future server.json byte-for-byte; Registry check is Phase 22 | ✓ VERIFIED (Phase 22 portion deferred) | Marker is one complete README line and one complete line of the live PyPI description. For context only: the tracked `server.json` now records `name: io.github.zhangtaolab/sif`, equal to the marker's value. The Registry ownership check is Phase 22 scope |
| 36 | 17-06 | GitHub environments `pypi` and `testpypi` exist | ✓ VERIFIED | `gh api repos/zhangtaolab/sif/environments` (live): `pypi` 27264851535, `testpypi` 27264859642, 0 protection rules each |
| 37 | 17-06 | Maintainer registered the PyPI trusted publisher and TestPyPI pending publisher with the exact identity fields | ✓ VERIFIED (end-to-end) | Publish run `43562577065` (live): attempt 4 success through `publish.yml` and environments `pypi`/`testpypi`; a successful OIDC mint is the only end-to-end proof |
| 38 | 17-06 | The Test Matrix run for the release HEAD is green across 8 cells + lint | ✓ VERIFIED | Run `43561542242` on `c819f67` (live): 8/8 py + lint success, `--exit-status` 0 |
| 39 | 17-06 | No runtime source changed between the smoke commit and the release HEAD except `src/sif/_version.py` | ✓ VERIFIED | `git diff --name-only 48759e2..c819f67 -- src/sif` → exactly `src/sif/_version.py` |
| 40 | 17-06 | 3.13 classifier, README marker, version literal, changelog, and publish workflow all present at release HEAD | ✓ VERIFIED | `git show c819f67:<path>`: `_version.py` `1.1.2`, README marker line 2, classifier line 24, `## [1.1.2]` line 38, three publish jobs at 11/50/72 |
| 41 | 17-06 | Backstop: publisher registration is not readable via public API; a successful OIDC publish is the only end-to-end proof | ✓ VERIFIED | Publish run `43562577065`: Build, TestPyPI, PyPI all success (live) |
| 42 | 17-07 | Tag v1.1.2 exists and the Publish run has build + publish-testpypi + publish-pypi all successful | ✓ VERIFIED | `git ls-remote --tags origin` (live): `v1.1.2` `fcca22f8` peels to `c819f67`; run `43562577065` attempt 4, 3/3 jobs success |
| 43 | 17-07 | PyPI serves docsif 1.1.2 with the exact mcp-name marker in `info.description` | ✓ VERIFIED | Live `pypi.org/pypi/docsif/1.1.2/json`: version 1.1.2, marker present, wheel 220225 / sdist 3108000 bytes |
| 44 | 17-07 | PEP 740 attestations verify for 1.1.2 against the repository | ✓ VERIFIED | Reproduced this round: `uvx pypi-attestations verify pypi --repository https://github.com/zhangtaolab/SIF pypi:docsif-1.1.2-py3-none-any.whl` → `OK`, exit 0; repeated on the downloaded 220225-byte wheel → `OK`, exit 0 |
| 45 | 17-07 | A fresh venv installs docsif==1.1.2 from PyPI and reports the released version | ✓ VERIFIED | Reproduced this round: fresh venv (CPython 3.12.12), `uv pip install docsif==1.1.2` → exit 0, 27 packages, `sif, version 1.1.2` |
| 46 | 17-07 | A fresh venv installs docsif==1.1.2 from TestPyPI (with the PyPI extra index for dependencies) and reports the same | ✓ VERIFIED | Reproduced this round: the wheel TestPyPI serves (sha256 identical to PyPI's) installed into a fresh venv by its `test-files.pythonhosted.org` URL, with the 27 dependencies resolved from PyPI → exit 0, `sif, version 1.1.2`, `import sif` 1.1.2. The plan's literal command (`--index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple`) also reports 1.1.2, but under uv 0.9.8 its debug log shows `docsif` resolved from `pypi.org`, so that form does not exercise TestPyPI once PyPI carries the same version |
| 47 | 17-07 | Backstop: PyPI versions are immutable, so a partial upload requires a new patch version | ✓ VERIFIED (scope honored) | No partial upload occurred; attempt 4 published 1.1.2 completely (live JSON lists both files) |
| 48 | 17-08 | No non-changelog doc or DESIGN.md names a deleted layer/export, a bare `migrations.py`/`strategy.py` tree entry, or the "legacy migration module" phrase | ✓ VERIFIED | Direct grep over `docs/*.md` + `DESIGN.md` (changelog excluded) returns nothing for the dotted, identifier, bare tree-entry, and phrase literals; `test_docs_do_not_describe_dead_layers` passes. Re-checked after `a321eaa` edited three of these files |
| 49 | 17-08 | Live-layer documentation survives (core SearchOptions/SearchResult/SearchType, Chunker ABC, Embedder/Reranker/QueryExpander) | ✓ VERIFIED | `docs/models.md:181,200,240`; `docs/api-reference.md` protocol hits; re-grepped this round |
| 50 | 17-08 | `docs/development.md` "New Search Strategy" describes the live extension path with no ABC and no `search_batch` | ✓ VERIFIED | Section at `docs/development.md:527`; `grep -c search_batch docs/development.md` = 0; imports from `sif.core.models` |
| 51 | 17-08 | No docs pre-commit instructions; exactly one VERIFY marker remains and it is the bandit one | ✓ VERIFIED | `grep 'make pre-commit\|pre-commit install\|pre-commit autoupdate' docs` → only the changelog history line `docs/changelog.md:91`, which does not instruct anything; `grep 'VERIFY:' docs` → exactly `docs/testing.md:242` (bandit); no pre-commit in `SKIP_COMMAND_PATTERNS` |
| 52 | 17-08 | Backstop: doc correctness is asserted by scans, not prose review; an unscanned stale concept can survive | ✓ VERIFIED (scope honored) | Scans exist and pass (21 `test_docs.py` tests + 4 doc guards); limitation is a true declaration of the method |
| 53 | 17-09 | Seven tracked junk paths removed from the index and working tree; no `MagicMock/` path tracked | ✓ VERIFIED | `git ls-files -- "MagicMock/" quick_test.py simple_test.py verify_imports.py` prints nothing; none exists on disk |
| 54 | 17-09 | No source/test/example references the junk paths and the committed suite is green | ✓ VERIFIED | Guard's literal list (`tests/test_hygiene.py:30-32`) is the only reference; full suite 3260 passed / 1 skipped at HEAD |
| 55 | 17-09 | Backstop: only the seven named paths are removed; the repo-wide unknown-junk audit stays deferred | ✓ VERIFIED (scope honored) | `git show --stat 8e4090d`: exactly the seven junk paths plus the guard; unknown-junk audit remains deferred per D-12/CONTEXT |
| 56 | 17-10 | `test-matrix.yml` declares the full 8-cell cross product with no matrix skip entries and `fail-fast: false`, restoring CONTEXT D-01 and D-03 | ✓ VERIFIED | YAML-parsed at HEAD: `strategy.matrix` keys are exactly `os` (2 values) and `python-version` (4 values) → 8 cells; skip-entry grep over the whole file → no match; `:21` `fail-fast: false`. D-01 (every push/PR, 8 cells, no split) and D-03 (macos-latest only, 8 cells) read true against `:3-6` and `:22-24`; `git diff --quiet 14d7d245^ -- .github/workflows/test-matrix.yml` exit 0 |
| 57 | 17-10 | `on.push.branches` is `['**']` and a top-level `pull_request:` trigger is present, so every branch push and every pull request runs the matrix while tag pushes still do not | ✓ VERIFIED | Parsed `on` has exactly two children: `push` → `{branches: ['**']}` with no nested filter, and a bare `pull_request:` beside it; the `branches: ['**']` line occurs exactly once (`:5`); a `branches` filter excludes tag pushes; `test_matrix_push_trigger_covers_all_branches` passes |
| 58 | 17-10 | `tests/test_ci_workflows.py` asserts exactly that shape: one guard rebuilds the 8 combinations and rejects any matrix skip entry, another requires the all-branch push trigger plus `pull_request:`; the two reduced-shape guards no longer exist | ✓ VERIFIED | `test_matrix_declares_eight_cells` (`:190`) rebuilds the 2 x 4 product and rejects `exclude`, `include`, `if`, `continue-on-error`; `test_matrix_push_trigger_covers_all_branches` (`:284`); grep for the two reduced-shape guards and `MATRIX_EXCLUSION` → absent; module 18 passed. Red-derivation reproduced: against `14d7d245:.github/workflows/test-matrix.yml` both guards fail on `AssertionError` (`:238` `assert ['exclude'] == []`, `:288` `assert None is not None`). The guards are not exhaustive (14 narrowed shapes pass them); that is a durability gap, not a defect in this truth as worded — see Anti-Patterns |
| 59 | 17-10 | `docs/development.md`, `docs/contributing.md`, and `docs/testing.md` all state eight cells and an every-branch push plus pull-request trigger in every location that described the reduced matrix | ✓ VERIFIED | Read all thirteen statements: `docs/development.md:609,732,751,769`; `docs/contributing.md:365,400,402,405,407`; `docs/testing.md:130,212,214`. Negative gates empty (no `six`, no `push: branches: [main]`, no main-only or PR-reliance phrasing); `docs/contributing.md` and `docs/testing.md` equal their `e8ab1148^` bodies; `docs/development.md` differs only at `:626` (the `0cdd69de` attestation line) |
| 60 | 17-10 | Backstop: Real GitHub Actions execution of the restored 8 cells cannot be verified locally; the post-merge branch-push confirmation stays a manual follow-up with a named failure path; the restore re-exposes both recorded causes; run 43561542242 is cited as history, never as evidence for this change | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED (backstop abstention — insufficient_spec) | The declaration is accurate: no Test Matrix run exists for the restored workflow (newest run `45311060690`, six-cell shape on main `d8b1404c`; `gsd/phase-24-reverify` has no upstream); the follow-up and failure path are recorded (`17-10-PLAN.md` Verification, `17-10-SUMMARY.md` Manual Follow-Up, AR-17-03); both recorded causes are in the quick task's Purpose. But the behavior it covers has no explicit evidence: the macOS py3.11 and py3.12 cells last ran green at `673b8e76` (2026-11-18, run `44333232391`) on a product tree 32 files (+442/−70) different from HEAD's, and today's lock ran on GitHub on only 6 of 8 cells. Abstains; see Human Verification |

**Score:** 59/60 truths verified (1 present-but-behavior-unverified: truth 60, a `verification: backstop` declaration that abstains because no GitHub Actions run exists for the restored matrix; the other 12 backstop declarations are resolved with direct evidence or scope confirmation).

### Roadmap Success Criteria

Scored with a non-overlapping truth partition.

| # | Success Criterion | Status | Covering Truths | Note |
|---|-------------------|--------|-----------------|------|
| 1 | Every push/PR runs the full suite green on py3.10-3.13 x ubuntu/macos — fail_under=90 per cell, CPU torch on Linux, both fleets tolerated | ⚠️ DECLARED HALF VERIFIED; runs-green half unconfirmed | 11-18, 56-60 | 12/13. The workflow again declares the 8-cell every-push/PR matrix and is blob-identical to the file that ran 8/8 green at `c819f67`; 6 of 8 cells plus lint are green on GitHub at product-identical `d8b1404c`. Truth 60 abstains: no run exists for the restored file and macOS 3.11/3.12 have not run on the current tree |
| 2 | A Windows smoke run on hc remote yoga proves fork/systemd/flock degrade honestly — degradation, not full support | ✓ VERIFIED | 19-26 | 8/8; recorded 8/8 PASS at `48759e2`; yoga unreachable today |
| 3 | `docsif` v1.1.x installable from PyPI via trusted publishing — TestPyPI dry run, version single-sourced, PEP 740 attestations, README marker before publish | ✓ VERIFIED | 27-31, 33-47 | 20/20; 1.1.2 is still live and served by both indexes; fresh installs from both reproduced this round; mechanism re-derived at 1.2.3 |
| 4 | Repo is hygienic — dead layers deleted, tracked junk removed, Makefile/extras/pre-commit cleaned, black dropped, fastapi/uvicorn kept; 3.13 classifier only once green | ✓ VERIFIED | 1-10, 32, 48-55 | 19/19 |

### SC1/ENG-01 Adjudication

**The declaration half of SC1/ENG-01 holds again at HEAD; the runs-green half is not yet confirmed.**

`.github/workflows/test-matrix.yml` at HEAD declares the full 8-cell cross product — Python 3.10, 3.11, 3.12, 3.13 on both `ubuntu-latest` and `macos-latest` — with no `exclude` or other matrix skip entry and with `fail-fast: false`. `on.push.branches` is `['**']` and a bare `pull_request:` sits beside `push:` under `on:`. Neither trigger carries a nested filter. The file's blob (`cb340cbe`) is byte-identical to the workflow at `c819f67` and `f6092f8`, the two commits where GitHub Actions expanded it into 8 py jobs plus lint on a branch push and every job succeeded. So truth 11 now holds as worded, and the prior report's single gap is closed. CONTEXT decisions D-01 and D-03 read true again.

What has not been observed is the restored matrix running on the current tree:

- **No run exists for the restored workflow.** Nothing has been pushed. The newest Test Matrix run, `45311060690` (2026-11-24, main `d8b1404c`), exercised the six-cell shape.
- **Six of eight cells are green on the current product tree.** Outside `.planning/`, the tree at `d8b1404c` differs from HEAD only in the five files plan 17-10 changed, so run `45311060690` (6 py cells + lint, all success) is evidence for HEAD's `src/`, `tests/` (except the guard module), `pyproject.toml`, and `uv.lock` on ubuntu py3.10-3.13 and macOS py3.10/3.13.
- **The two restored cells have not run on the current tree.** macOS py3.11 and py3.12 last ran green at `673b8e76` (run `44333232391`, 2026-11-18, attempt 3). Since then `src/`, `tests/`, `pyproject.toml`, and `uv.lock` changed by 32 files (+442/−70); the lock's resolved versions are unchanged, only the docsif torch specifier moved.
- **Locally** the full suite passes on one cell (macOS arm64, Python 3.13.9): 3260 passed, 1 skipped, 95.12% coverage.

This is recorded as truth 60's abstention and as the phase's one gating human-verification item, not as a failed truth: nothing contradicts SC1, and the plan itself declares this half unverified locally. A green eight-cell run on a pushed branch resolves it.

### SC3 Adjudication

**SC3's "v1.1.x installable from PyPI" wording is still satisfied at HEAD.** `docsif==1.1.2` is served by PyPI and TestPyPI with the exact mcp-name marker and byte-identical artifacts (same sha256 for the wheel and the sdist on both indexes), the attestation on the published wheel verifies today, and a fresh venv installs it from each index and reports `sif, version 1.1.2`. PyPI's latest release is 1.2.2 and the local tree is at 1.2.3; that progression is normal post-phase release maintenance. The single-sourcing mechanism is re-verified at 1.2.3 (`_version.py` literal → version-identity battery → release-metadata pins → tag gate → CLI `1.2.3`).

### Decision Coverage

All trackable CONTEXT.md decisions are honored by shipped artifacts.

`check.decision-coverage-verify` ran this round (exit 0): `total: 15, honored: 15, not_honored: []`. The prior report's 13/15 becomes 15/15 because D-01 and D-03 are true again after the restore.

### Required Artifacts

`gsd_run query verify.artifacts` at HEAD: plans 01 (6/6), 02 (4/4), 03 (2/2), 04 (5/5), 08 (9/9), 09 (1/1), 10 (5/5) all pass; plan 05 is 6/8; plans 06 and 07 are 0/1. No artifact is missing, stub, or orphan. The four verb flags are resolved as follows.

| Artifact | Plan | Expected | Status | Details |
|----------|------|----------|--------|---------|
| `tests/test_hygiene.py` | 01/08/09 | Absence/import/Makefile/doc/junk guards | ✓ VERIFIED | All guards pass (15) |
| `src/sif/models/__init__.py` | 01 | Dead search exports removed | ✓ VERIFIED | `__all__` holds only live models |
| `src/sif/database/__init__.py` | 01 | No MigrationManager export | ✓ VERIFIED | Live repos/helpers only |
| `src/sif/search/rrf.py` | 01 | RRFFusion only | ✓ VERIFIED | Fusion tests pass |
| `examples/quickstart.py` | 01 | Live API example | ✓ VERIFIED | Compile guard passes |
| `Makefile` | 01/04 | pre-commit-free; windows-smoke target | ✓ VERIFIED | No pre-commit token; `windows-smoke` at `:81` |
| `pyproject.toml` | 02/05 | CPU index/sources/floors; 3.13 classifier | ✓ VERIFIED | `explicit = true` index; Linux-marker torch; classifier `:24` |
| `uv.lock` | 02 | CPU torch, no CUDA/black | ✓ VERIFIED | 0 nvidia/triton/black; `uv lock --check` exit 0 |
| `tests/test_ci_workflows.py` | 02/03/10 | Lock/packaging/workflow guards; `test_matrix_declares_eight_cells`, `test_matrix_push_trigger_covers_all_branches` | ✓ VERIFIED | Both exports present (`:190`, `:284`); 18 guards pass. The prior "intentional drift" flag is cleared |
| `docs/installation.md` | 02/05 | Extras aligned; version sample | ✓ VERIFIED | `sif, version 1.2.3` sample; windows-smoke at `:335` |
| `.github/workflows/test-matrix.yml` | 03/10 | 8-cell matrix + lint job; `python-version: ['3.10', '3.11', '3.12', '3.13']` | ✓ VERIFIED | Byte-identical to `14d7d245^`; 8 cells, every-branch push, bare `pull_request:` |
| `docs/development.md`, `docs/contributing.md`, `docs/testing.md` | 08/10 | Dead prose removed; eight-cell and every-branch wording | ✓ VERIFIED | Thirteen statements read; negative gates empty |
| `scripts/windows_smoke.py` | 04 | Degradation smoke with matchers | ✓ VERIFIED | Version read from `_version.py`; platform guard; recorded 8/8 PASS |
| `tests/test_windows_smoke_script.py` | 04 | Matcher battery | ✓ VERIFIED | 8 tests pass |
| `src/sif/utils/daemon.py` | 04 | POSIX-fork guard | ✓ VERIFIED | `hasattr(os, "fork")` at `:253` |
| `src/sif/cli/commands/watch.py` | 04 | Detach + win32 service guard | ✓ VERIFIED | Guards at `:359-364` and `:438-440` |
| `src/sif/_version.py` | 05 | Single-sourced release version | ✓ VERIFIED at 1.2.3 | Single literal `"1.2.3"`; the plan's `contains: "1.1.2"` is a stale snapshot of the phase-time version |
| `README.md` | 05 | mcp-name marker | ✓ VERIFIED | Exact line 2 |
| `docs/changelog.md` | 05 | Release entry + compare links | ✓ VERIFIED | `[1.2.3]` section + links; `[1.1.2]` retained |
| `tests/test_release_metadata.py` | 05 | Release identity/marker/changelog/workflow guards | ✓ VERIFIED at 1.2.3 | `test_changelog_has_1_1_2` was re-pointed to `test_changelog_has_1_2_3` by post-phase releases; 13 guards pass |
| `.github/workflows/publish.yml` | 05 | Tag-gated build/publish | ✓ VERIFIED | Re-read in full; run `43562577065` success; unchanged since `ae1225e` |
| `17-06-SUMMARY.md` | 06 | Release-gate evidence | ✓ VERIFIED (archived path) | The plan names the pre-archive path `.planning/phases/...`; the file exists in this phase directory. Environments, run id, diff, and release_head re-confirmed live |
| `17-07-SUMMARY.md` | 07 | Published-release evidence | ✓ VERIFIED (archived path) | Same path artifact. Tag, PyPI/TestPyPI JSON, attestation, and installs re-confirmed live |
| `docs/architecture.md`, `docs/models.md`, `docs/api-reference.md`, `DESIGN.md` | 08 | Dead prose removed, live docs kept | ✓ VERIFIED | Direct greps + guards |
| `tests/test_docs.py` | 08 | `SKIP_COMMAND_PATTERNS` without pre-commit install | ✓ VERIFIED | Doc guards pass (21) |

### Key Link Verification

22 declared key links: 13 verify programmatically via `verify.key-links` (plans 01: 3/3, 02: 1/2, 03: 2/2, 04: 2/3, 08: 2/2, 09: 1/1, 10: 2/2); the 9 flagged links (plans 02, 04, 05, 06, 07) fail only because their `from` value is a component description rather than a relative file path (parser limitation). Each was verified manually on the current tree or against live external state.

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/test_hygiene.py` | deleted module paths | rglob text scan + existence assertions | ✓ WIRED | Guard passes; a surviving importer would fail it |
| `src/sif/models/__init__.py` | `sif.models` consumers | `__all__` no dead names | ✓ WIRED | Test asserts disjunction |
| `examples/quickstart.py` | `database.py` / `bm25.py` | `Database`/`BM25Searcher` usage | ✓ WIRED | Compile guard + direct inspection |
| `pyproject.toml [tool.uv.sources]` | `uv.lock` torch entries | marker-scoped CPU index materialized | ✓ WIRED (manual) | `pyproject.toml:99-101` → `+cpu` entries sourced from the CPU registry (`uv.lock:2935`, `:3012`) |
| `tests/test_ci_workflows.py` | `uv.lock` + `pyproject.toml` | text-level guards | ✓ WIRED | All guards pass |
| `test-matrix.yml` | `uv.lock` | `cache-dependency-glob` + `uv sync --frozen` | ✓ WIRED | `:34`, `:41`; run `45311060690` synced this exact lock on 6 cells |
| `test-matrix.yml` | pyproject pytest/coverage config | bare pytest inherits addopts/fail_under | ✓ WIRED | No `--no-cov`; `fail_under = 90` at `pyproject.toml:229` |
| `Makefile windows-smoke` | `scripts/windows_smoke.py` on yoga | `hc exec --on yoga … uv run --frozen` | ✓ WIRED (manual) | `Makefile:81-87` + recorded 8/8 PASS run |
| `watch.py` | `utils/daemon.py` | library guard before `detach()` | ✓ WIRED | Guards at `:359-364` / `:253` |
| `tests/test_windows_smoke_script.py` | `scripts/windows_smoke.py` | direct matcher imports | ✓ WIRED | Tests pass |
| `README.md marker` | PyPI project description | hatchling reads README | ✓ WIRED (manual) | Live PyPI JSON: marker at description line 2 |
| `publish.yml build job` | `src/sif/_version.py` | `runpy` + `GITHUB_REF_NAME` gate | ✓ WIRED (manual) | `:29-35`; version-agnostic |
| `publish.yml publish jobs` | environments `pypi`/`testpypi` | environment-scoped OIDC | ✓ WIRED (manual) | Environment blocks + both environments exist (live API) |
| `publish.yml environments` | GitHub environments + publisher registration | exact identity fields | ✓ WIRED (manual) | Successful OIDC publish, run `43562577065` |
| `17-04-SUMMARY smoke HEAD` | release HEAD | `git diff -- src/sif` limited to `_version.py` | ✓ WIRED (manual) | Diff re-run: exactly `src/sif/_version.py` |
| `tag v1.1.2` | `publish.yml` | tag push is the only trigger | ✓ WIRED (manual) | Tag peels to `c819f67` (live ls-remote); `tags: ['v*']` |
| `PyPI artifact` | MCP Registry ownership marker | `info.description` contains marker | ✓ WIRED (manual) | Fresh PyPI and TestPyPI JSON checks |
| `tests/test_hygiene.py` | docs + DESIGN.md | dead literal + VERIFY scans | ✓ WIRED | Guards pass; direct grep confirms |
| `docs/development.md` | `src/sif/search/` + `sif.core.models` | live searcher how-to | ✓ WIRED | Section verified |
| `tests/test_hygiene.py` | git index | `git ls-files` + sentinel | ✓ WIRED | Guard passes non-vacuously |
| `tests/test_ci_workflows.py` | `.github/workflows/test-matrix.yml` | guards parse the matrix lists, rebuild the 2 x 4 product, assert no skip entry + all-branch push trigger | ✓ WIRED | 18 passed; red-derivation rejects the six-cell shape |
| `docs/development.md` | `.github/workflows/test-matrix.yml` | prose states eight cells on every branch push and every pull request | ✓ WIRED | `:609,732,751,769` match the workflow keys |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `src/sif/_version.py` | `__version__` | single literal → hatchling wheel METADATA → PyPI JSON → installed CLI | Yes: fresh venvs install 1.1.2 from both indexes and print it; local tree prints `1.2.3` through the same path | ✓ FLOWING |
| `README.md` | PyPI `info.description` | hatchling `readme = "README.md"` at build time | Yes: marker present in live PyPI and TestPyPI JSON | ✓ FLOWING |
| `uv.lock` | torch resolution | explicit CPU index + Linux marker | Yes: `+cpu` entries; lock synced by GitHub run `45311060690` (6 cells) | ✓ FLOWING |
| `.github/workflows/test-matrix.yml` | matrix cells | `strategy.matrix` `os` x `python-version` literal lists | Yes: 8-cell product parsed at HEAD; the same blob expanded to 8 jobs in runs `43399300651` and `43561542242` | ✓ FLOWING (no run yet for the restored file on the current tree) |
| `scripts/windows_smoke.py` | CLI outputs | temp `SIF_DB_PATH` SQLite DB → CLI stdout/stderr → matchers | Yes: recorded run produced all PASS lines; matchers exercised locally | ✓ FLOWING |
| `publish.yml` build job | dist artifact | `uv build` → upload-artifact → both publish jobs | Yes: identical sha256 digests on both indexes | ✓ FLOWING |
| render surfaces | — | none introduced by this phase | N/A | N/A |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Full regression suite, as each CI cell runs it | `pytest -q` (`pytest` from PATH: 9.1.1, miniconda Python 3.13.9, macOS arm64) | 3260 passed, 1 skipped, 27 warnings @ 95.12% in 210.45 s; `Required test coverage of 90.0% reached`; exit 0 | ✓ PASS |
| Phase guard battery | `pytest tests/test_ci_workflows.py tests/test_release_metadata.py tests/test_hygiene.py tests/test_windows_smoke_script.py tests/test_version_identity.py -q --no-cov` | 58 passed in 1.03 s | ✓ PASS |
| Workflow guard module | `pytest tests/test_ci_workflows.py -q --no-cov` | 18 passed in 0.02 s | ✓ PASS |
| Guards reject the recorded reduction (plan 17-10 red-derivation gate) | committed guards run against `14d7d245:.github/workflows/test-matrix.yml` in a temp dir | inner pytest exit 1; both guards `FAILED … AssertionError` (`:238`, `:288`); `2 failed, 4 passed`; gate exit 0 | ✓ PASS |
| Workflow shape at HEAD | YAML parse of `.github/workflows/test-matrix.yml` | `on` = {push: {branches: ['**']}, pull_request: null}; matrix keys `os`, `python-version`; 8 cells; skip-entry grep empty | ✓ PASS |
| Workflow unchanged since the phase release | `git diff --quiet 14d7d245^ -- .github/workflows/test-matrix.yml`; blob ids at HEAD, `c819f67`, `f6092f8` | exit 0; all three blobs `cb340cbe` | ✓ PASS |
| Guard module untouched outside the two guard slots | plan's sed-cut diff, plan base `ae1225e` vs HEAD | 303 remainder lines on both sides, no diff | ✓ PASS |
| Guard mutation probe (six workflow-reading guards, scratch dir) | 25 workflow versions: the HEAD control and 24 variants | control passes; 10 reduction and matrix-skip shapes rejected; 14 narrowed shapes accepted (see Anti-Patterns) | ⚠️ OBSERVED (guard completeness) |
| Docs gates (plan 17-10 Task 2) | three negative greps + positive counts + `git diff --quiet e8ab1148^` | negatives empty; counts 4/3/2 and 1/1/1; contributing and testing byte-equal; development differs only at `:626` | ✓ PASS |
| Watch/daemon guards, smoke matchers, RRF | `pytest tests/test_windows_smoke_script.py tests/unit/cli/test_watch_cmd.py::TestDaemonFlagGuards tests/unit/utils/test_daemon.py tests/unit/search/test_rrf.py -q --no-cov` | 96 passed in 0.31 s | ✓ PASS |
| Release, version, docs, hygiene guards | `pytest tests/test_release_metadata.py tests/test_version_identity.py tests/test_docs.py tests/test_hygiene.py -q --no-cov` | 53 passed in 1.12 s | ✓ PASS |
| Lock freshness | `uv lock --check` | exit 0, Resolved 106 packages | ✓ PASS |
| Ruff gates | `ruff check src tests` / `ruff format --check src tests` | All checks passed / 237 files already formatted | ✓ PASS |
| Type gate (local miniconda py3.13) | `ty check src/sif` | exit 1, 10 diagnostics | ⚠️ OBSERVED (environment drift, see Advisory) |
| Type gate (local project `.venv` py3.10, run directly without sync) | `.venv/bin/ty check src/sif` | exit 1, 10 diagnostics | ⚠️ OBSERVED (environment drift) |
| Type gate in CI | lint job of run `45311060690` at `d8b1404c` (`src/` identical to HEAD) | success | ✓ PASS |
| Local version surface | `python -m sif.cli.main --version` | `sif, version 1.2.3` | ✓ PASS |
| PyPI JSON (1.1.2) | `curl https://pypi.org/pypi/docsif/1.1.2/json` | version 1.1.2; marker at description line 2; 220225 / 3108000 | ✓ PASS |
| TestPyPI JSON (1.1.2) | `curl https://test.pypi.org/pypi/docsif/1.1.2/json` | version 1.1.2; marker present; same sizes and sha256 digests as PyPI | ✓ PASS |
| PEP 740 attestation | `uvx pypi-attestations verify pypi --repository https://github.com/zhangtaolab/SIF pypi:docsif-1.1.2-py3-none-any.whl` | `OK: docsif-1.1.2-py3-none-any.whl`, exit 0 | ✓ PASS |
| Fresh install from PyPI | fresh venv (CPython 3.12.12): `uv pip install docsif==1.1.2` → `sif --version` | exit 0, 27 packages; `sif, version 1.1.2` | ✓ PASS |
| Fresh install from TestPyPI | fresh venv: `uv pip install <test-files.pythonhosted.org URL of docsif-1.1.2-py3-none-any.whl>` (dependencies from PyPI) → `sif --version` | exit 0, 27 packages, `+ docsif==1.1.2 (from https://test-files.pythonhosted.org/...)`; `sif, version 1.1.2` | ✓ PASS |
| Plan's literal TestPyPI command | `uv pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple docsif==1.1.2` with `-v` | reports `sif, version 1.1.2`, but the debug log resolves `docsif` from `pypi.org` | ℹ️ OBSERVED (does not exercise TestPyPI under uv 0.9.8) |
| Test Matrix on the 17-03 phase HEAD | `gh run view 43399300651` | success; headSha `f6092f8`; 8 py + lint success | ✓ PASS |
| Test Matrix on the release HEAD | `gh run view 43561542242` | success; headSha `c819f67`; 8 py + lint success | ✓ PASS |
| Last eight-cell run on a later tree | `gh run view 44333232391` | success; headSha `673b8e76`; 8 py + lint success; 2026-11-18 | ✓ PASS (context) |
| Newest Test Matrix run | `gh run view 45311060690` | success; headSha `d8b1404c`; 6 py + lint success; six-cell shape | ✓ PASS (context for 6 of 8 cells) |
| Test Matrix on the restored workflow | `gh run list --workflow=test-matrix.yml --limit 25` | no run after `10a9685`; branch `gsd/phase-24-reverify` has no upstream | ? SKIP (see Human Verification) |
| Publish workflow | `gh run view 43562577065` | success, attempt 4; Build, TestPyPI, PyPI all success | ✓ PASS |
| Release tag | `git ls-remote --tags origin v1.1.2 'v1.1.2^{}'` | `v1.1.2` peels to `c819f67`; equals `release_head` | ✓ PASS |
| GitHub environments | `gh api repos/zhangtaolab/sif/environments` | `pypi` (27264851535) + `testpypi` (27264859642) | ✓ PASS |
| Classifier-after-green ordering | `git merge-base --is-ancestor f6092f8 9164e4f` | yes | ✓ PASS |
| Windows degradation smoke | recorded `make windows-smoke` (hc yoga, `48759e2`); `hc ls` today | 8/8 PASS at `48759e2`; yoga `state: unreachable` (ssh timeout) | ✓ PASS (recorded) |

### Probe Execution

None applicable. No probe scripts are declared or conventionally present (`find scripts -path '*/tests/probe-*.sh'` returns nothing; no probe reference appears in any phase PLAN/SUMMARY).

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|----------------|-------------|--------|----------|
| ENG-01 | 17-02, 17-03, 17-05, 17-10 | Full suite on a green CI matrix (py3.10-3.13 × ubuntu/macos, fail_under=90 per cell, CPU torch on Linux, both resolution fleets tolerated) on every push/PR | ? NEEDS HUMAN — declared contract verified; first GitHub run of the restored matrix pending | Workflow restored byte-exact and guarded; 6 of 8 cells + lint green on GitHub at product-identical `d8b1404c`; macOS 3.11/3.12 unexercised on the current tree; see truth 60 |
| ENG-02 | 17-04, 17-05 | Windows degradation verified by a CI smoke on hc remote yoga (uv python install first; fork/systemd/flock degrade honestly) | ✓ SATISFIED | Guards + committed smoke + matcher battery + Makefile target; recorded 8/8 PASS at `48759e2`; docs document the on-demand step |
| ENG-03 | 17-05, 17-06, 17-07 | Maintainer can publish docsif to PyPI via trusted publishing (marker before publish, TestPyPI dry run, version single-sourced, PEP 740 attestations) | ✓ SATISFIED | PyPI + TestPyPI serve 1.1.2 with identical digests; marker live; attestation verifies today; fresh installs from both indexes; single-sourcing carries 1.2.3 |
| ENG-04 | 17-01, 17-02, 17-05, 17-08, 17-09 | Hygienic repo: dead layers deleted, tracked junk removed, Makefile/extras/pre-commit cleaned, black dropped, fastapi/uvicorn kept, 3.13 classifier only when green | ✓ SATISFIED | All deletions/guards verified; 0 junk tracked; no pre-commit/black tokens; core deps intact; classifier after green run |

No orphaned requirements: `.planning/milestones/v1.2-REQUIREMENTS.md` maps exactly ENG-01..ENG-04 to Phase 17 (lines 24-27, traceability lines 141-144), every ID is claimed by at least one plan's `requirements:` frontmatter, and no requirement mapped to Phase 17 is unclaimed. The checkboxes remain `[x]` from the original close; this report does not edit REQUIREMENTS.md.

### Prohibitions (must-NOT checks)

17 plan-declared prohibitions re-evaluated. All 17 are judged satisfied at HEAD. These are reviewer judgments of must-NOT statements, not test-backed results: human review is recommended, and the table is the evidence to review.

| Plan | Prohibition | Status | Evidence |
|------|-------------|--------|----------|
| 17-01 | MUST NOT delete code on a runtime path | ✓ SATISFIED | Deletions limited to the three verified-dead modules and the orphan RRF function; full suite green |
| 17-01 | MUST NOT leave examples/Makefile describing deleted layers or phantom pre-commit | ✓ SATISFIED | Compile guard + Makefile guard; dead-literal greps clean |
| 17-02 | MUST NOT add a package or trust a third-party index beyond the explicit CPU index | ✓ SATISFIED | Single `explicit = true` index serving torch only, marker-scoped |
| 17-03 | MUST NOT weaken the coverage gate to make the matrix green — no `--no-cov`, no lowered fail_under, no skipped or removed cell | ✓ SATISFIED (was partially violated) | No `--no-cov`; `fail_under = 90` unchanged; all 8 cells declared again with no skip entry |
| 17-04 | MUST NOT present the smoke as full Windows support | ✓ SATISFIED | `docs/development.md:607,737`; WIN-F1 deferred |
| 17-04 | MUST NOT touch the user's real index/collections/model cache on yoga | ✓ SATISFIED | Temp `SIF_DB_PATH`; BM25-only argv; the only post-run script change is the CR-01 refusal that makes the script exit before running anything on a non-Windows host |
| 17-05 | MUST NOT publish a release without the mcp-name marker | ✓ SATISFIED | Published 1.1.2 `info.description` contains the exact marker (live) |
| 17-05 | MUST NOT publish from a mismatched tag or a red matrix | ✓ SATISFIED | Tag gate in build job; run `43561542242` green on `c819f67`; tag peels to `c819f67` |
| 17-06 | MUST NOT weaken publisher identity or disable OIDC | ✓ SATISFIED | Workflow uses `publish.yml` + environments `pypi`/`testpypi` + job-scoped `id-token: write`; successful OIDC publish |
| 17-07 | MUST NOT rebuild in publish jobs or re-upload under a mutated version | ✓ SATISFIED | No `uv build` in publish jobs; both download artifact `dist`; identical sha256 digests on both indexes |
| 17-07 | MUST NOT reuse credentials/environment between TestPyPI and PyPI | ✓ SATISFIED | Separate jobs, separate environments, separate repository URLs; no secrets |
| 17-08 | MUST NOT delete documentation of live layers | ✓ SATISFIED | Live models/protocols present in `docs/models.md` and `docs/api-reference.md` |
| 17-08 | MUST NOT hand-edit generator-owned `docs/cli-reference.md` / `docs/configuration.md` | ✓ SATISFIED | Neither file is in the phase's changed set; `.github/workflows/docs.yml` regenerates them |
| 17-09 | MUST NOT remove any path not on the seven-path verified list | ✓ SATISFIED | `git show --stat 8e4090d`: exactly the seven junk paths plus the guard |
| 17-10 | MUST NOT weaken the coverage gate or drop a cell (standing 17-03 prohibition) | ✓ SATISFIED | Same evidence as the 17-03 row |
| 17-10 | MUST NOT revert commit 14d7d245 with git; later commits must survive | ✓ SATISFIED | No revert commit in `d3f3b8d..HEAD`; `f665eee1`, `848e6b6a`, and `0cdd69de` remain ancestors and their lines survive (`tests/test_ci_workflows.py:139,172`; `docs/development.md:626`). The three docs hunks of `e8ab1148` are the reduction's own wording and were replaced by design |
| 17-10 | MUST NOT touch `publish.yml`, `pyproject.toml`, `uv.lock`, any product source, or 17-CONTEXT.md D-01/D-03 | ✓ SATISFIED | `git diff --quiet ae1225e HEAD` over those paths: exit 0 |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK` marker in the 39 covered implementation files (positive control: the same grep finds `fail-fast` in the workflow and guards) | ℹ️ Info | Debt-marker gate clean |
| `tests/test_ci_workflows.py` | 190-299 | Guards accept 14 narrowed workflow shapes: seven nested trigger filters (`paths`, `paths-ignore`, `branches-ignore` under `push:`; `branches: [main]`, `paths`, `paths-ignore`, `types` under `pull_request:`), three pytest-step narrowings (`--collect-only -q`, a path argument, `-k`), job-level `contents: write` on the test job, `if: false` and `continue-on-error: true` on the lint job, and a hardcoded `runs-on` (IN-12) | ⚠️ Warning — guard completeness | No truth as worded is falsified: the HEAD workflow contains none of these shapes, and the guards reject every recorded reduction shape and every matrix-skip shape probed. This limits how long the contract stays true, not whether it is true. Whether to add `test_matrix_triggers_are_unfiltered` (row 8 recipe) and extend it to the other shapes is a maintainer decision |
| `17-07-SUMMARY.md` | Task 2, TestPyPI install proof | The recorded command (`--index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple`) resolves `docsif` from PyPI under uv 0.9.8, because extra indexes take priority over the default index | ℹ️ Info — evidence method | The truth holds: the TestPyPI artifact is sha256-identical to PyPI's and installs when sourced from TestPyPI (truth 46). The recorded proof does not distinguish the two indexes |
| `docs/development.md`, `docs/testing.md` | development 91, 291, 714; testing 128 | "placeholder" prose describing `tests/e2e/` and `make docs` | ℹ️ Info — pre-existing, outside Phase 17 | Honest description of existing repo state |
| `docs/testing.md` | 4, 202 | Stated counts (3,234 collected / 3,233 passed) are stale at HEAD (3,261 / 3,260) (IN-09) | ℹ️ Info — open review finding | No must-have impact |
| `.github/workflows/publish.yml` | publish jobs | No job-level `timeout-minutes` on the publish jobs (WR-06); no concurrency guard (WR-07) | ℹ️ Info — open review finding | Plan 17-05 requires build-once/tag-gate/OIDC, not these hardening items |
| `src/sif/embedding/embedder.py`, `src/sif/embedding/download.py`, `src/sif/search/rerank.py` | — | 10 `ty` diagnostics in local environments | ℹ️ Info — environment drift | CI lint job green at product-identical `d8b1404c` |
| review dispositions | — | 17 of 25 review rows remain `open` (0 Critical, 0 Warning in the current review; IN-12 is the one new Info) | ℹ️ Info — user-tracked | None falsifies a must-have as worded |

### Guard Coverage Limitation (decision for the maintainer)

The workflow-reading guards are literal-text checks. A mutation probe in a scratch directory ran the six guards that read `.github/workflows/test-matrix.yml` against 25 workflow versions (the HEAD control and 24 variants):

- **Rejected (10):** the recorded six-cell reduction (`14d7d245`), `exclude`, `include`, a dropped Python version, a dropped OS, a step-level `if`, `fail-fast: true`, `--no-cov`, a dynamic `${{ fromJSON(...) }}` axis, and `pull_request_target`.
- **Accepted (14):** the seven nested trigger filters, the three pytest-step narrowings, job-level `contents: write` on the test job, `if: false` and `continue-on-error: true` on the lint job, and a hardcoded `runs-on: ubuntu-latest` on the test job.

Effect on this verification: none of the truths depends on the guards being exhaustive. Truths 57, 58, and 14 assert what the guards check and what the workflow declares, and all hold; the workflow at HEAD contains none of the accepted shapes. The limitation is recorded in `17-VALIDATION.md` Manual-Only row 8 (seven shapes), `17-SECURITY.md` (four more), and `17-REVIEW.md` IN-12 (`runs-on`). It is not converted into a truth failure, and it is not ignored: without a follow-up guard, CI can be narrowed to one Ubuntu cell eight times over, or to docs-only triggers, with every guard green.

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| `tests/test_ci_workflows.py` | ENG-01, ENG-04 | 18 | 0 | No | Value (exact strings, product equality) | OK; not exhaustive (see above) |
| `tests/test_release_metadata.py` | ENG-03 | 13 | 0 | No | Value (job-block scoped workflow text) | OK |
| `tests/test_version_identity.py` | ENG-03 | 4 | 0 | No | Behavioral (runtime surfaces agree) | OK |
| `tests/test_hygiene.py` | ENG-04 | 15 | 0 on this machine (explicit named skip only if git is unusable) | No | Value / existence with offender lists | OK |
| `tests/test_windows_smoke_script.py` | ENG-02 | 8 | 0 | No | Behavioral (positive and negative matcher cases) | OK |
| `tests/unit/cli/test_watch_cmd.py`, `tests/unit/utils/test_daemon.py` | ENG-02 | all | 0 on this machine (`skipif` platform guards only) | No | Behavioral (exit code, message, no traceback) | OK |

**Disabled tests on requirements:** 0. **Circular patterns detected:** 0. **Insufficient assertions:** 0 (the non-exhaustive workflow guards are reported above as a coverage warning, not as weak assertions). The suite's one skip is the opt-in `tests/integration/test_service_live_launchd.py:98` (set `SIF_TEST_LIVE_LAUNCHD=1`), unrelated to Phase 17.

### Advisory (New Scope, Unevidenced)

New-scope findings from Step 7 that do not block and do not revert a completed must-have.

| # | Finding | Category | Why Advisory |
|---|---------|----------|--------------|
| 1 | The workflow-reading guards accept 14 narrowed workflow shapes (details above). | other | Reported, not blocking: reproduced with deterministic evidence, but no truth as worded is falsified and the workflow at HEAD is correct. The fix is a follow-up guard and is the maintainer's decision |
| 2 | Local `ty check src/sif` reports 10 diagnostics in the miniconda py3.13 environment and 10 in the project `.venv` (py3.10). | other | Environment drift from locally installed third-party packages; CI's lint job is green at `d8b1404c`, whose `src/` is byte-identical to HEAD. Not a Phase 17 truth |

### Human Verification Required

### 1. First GitHub Actions run of the restored eight-cell matrix (the runs-green half of SC1/ENG-01; `17-VALIDATION.md` Manual-Only row 7; T-17-30 failure path)

**Test:** Push a branch that carries the restored workflow (any commit from `10a9685` onward), or update an open pull request, then open the Test Matrix run.
**Expected:** Exactly 8 `py<version> / <os>` jobs (py3.10-3.13 on `ubuntu-latest` and `macos-latest`) plus `lint / py3.12 / ubuntu-latest`, all success, each cell logging `Required test coverage of 90.0% reached`. Record the run id and the job conclusions. If a macOS cell is capacity-cancelled, re-run it once; if the cancellation recurs, take a new recorded decision rather than shrinking the matrix by hand; if a cell is red, fix forward without dropping the cell, adding `--no-cov`, or lowering `fail_under`.
**Why human:** GitHub Actions execution is external, and nothing has been pushed: no run exists for the restored workflow, and the macOS py3.11/py3.12 cells have not run on the current product tree.

### 2. Review the judgment-tier prohibition verdicts

**Test:** Read the Prohibitions table and confirm each of the 17 verdicts.
**Expected:** Each verdict is confirmed, or the reviewer names the prohibition that is actually violated.
**Why human:** The verdicts are reviewer judgments of must-NOT statements, not test-backed results. Review is recommended; it is not a gate on its own.

Not a verification item: the Windows degradation smoke is a recorded external run (`48759e2`, 8/8 PASS). Yoga is unreachable today (`hc ls`: ssh timeout), so it was not re-executed; re-running `make windows-smoke` on a synced checkout when yoga is reachable would refresh that evidence and does not affect this verdict.

### Gaps Summary

No truth fails. The prior report's single gap is closed, and nothing regressed.

- **Closed:** truth 11. The workflow again declares the 8-cell py3.10-3.13 × ubuntu/macos matrix on every branch push and every pull request, byte-identical to the file that ran 8/8 green at the phase release. The guards pin that shape and were observed rejecting the six-cell workflow; the three guides agree with it in all thirteen statements; CONTEXT D-01 and D-03 hold again; the 17-03 "no removed cell" prohibition holds again.
- **Open, not a failure:** truth 60 abstains. The restored matrix has not run on GitHub Actions, and two of its cells (macOS py3.11, py3.12) have not run on the current product tree. The declaration is restored and verified; its first real run is the one remaining confirmation, and it needs a push.

Everything else the phase promised is verified at HEAD: the Windows degradation guards, smoke, and Makefile target (recorded green), the trusted-publishing release (`docsif` 1.1.2 still served by PyPI and TestPyPI, marker present, PEP 740 attestation OK, fresh installs from both indexes, single-sourcing now carrying 1.2.3), and repo hygiene.

A re-verification after a green eight-cell run on a pushed branch resolves truth 60 with directly observed behavior; no other truth depends on it.

---

_Verified: 2026-11-24T15:46:05Z_
_Verifier: Claude (gsd-verifier)_
