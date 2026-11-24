---
phase: 17-engineering-foundation-ci-matrix-hygiene-pypi
verified: 2026-11-24T05:05:33Z
status: gaps_found
score: 54/55 must-haves verified
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
covered_digest: "v4:sha256:4556bc1024284d7ff14dfc93d1d355b7b15d58970cdee95a82de46f65dad87e8"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 55/55
  gaps_closed: []
  gaps_remaining:
    - "SC1/ENG-01 is no longer literally true at HEAD: the Test Matrix is a six-cell matrix (macOS 3.11/3.12 excluded) and push CI runs on main only, not every branch push on the 8-cell py3.10-3.13 x ubuntu/macos cross product."
  regressions:
    - "Post-phase quick task 261118-lmm (commits 14d7d245, e8ab1148, f665eee1) reduced .github/workflows/test-matrix.yml from 8 to 6 cells and moved the push trigger to main only, reversing CONTEXT decisions D-01 and D-03. The 8-cell matrix did run green at the phase release HEAD c819f67 (run 43561542242)."
gaps:
  - truth: "Every push to a branch and every pull_request runs the full suite on exactly 8 test cells - Python 3.10, 3.11, 3.12, 3.13 x ubuntu-latest, macos-latest - with fail-fast: false so every cell reports."
    status: failed
    reason: "At HEAD the workflow declares a six-cell matrix (macos 3.11 and 3.12 are explicit exclude entries) and the push trigger is branches: [main] only. This was a deliberate POST-PHASE reduction by quick task 261118-lmm, not a phase-execution defect: the 8-cell matrix ran green at the phase release HEAD c819f67 (Test Matrix run 43561542242, 8 py cells + lint all success). The reduction also reverses CONTEXT D-01 ('every push/PR runs the full 8-cell matrix; no PR-vs-push split') and D-03 ('8 cells total')."
    artifacts:
      - path: ".github/workflows/test-matrix.yml"
        issue: "matrix is 2 OS x 4 Python minus 2 macOS cells (lines 22-29) and push is branches: [main] (line 5)"
      - path: "tests/test_ci_workflows.py"
        issue: "guard renamed to test_matrix_declares_six_cells and test_matrix_push_trigger_is_main_only now pins the reduced shape (lines 182-261)"
    missing:
      - "Restore the 8-cell py3.10-3.13 x ubuntu/macos cross product on every push and every pull_request, or record a formal scope reduction against SC1/ENG-01 (and D-01/D-03) in REQUIREMENTS/ROADMAP."
advisory:
  - finding: "Local frozen .venv (Python 3.10) reports 1 ty error at src/sif/embedding/embedder.py:870; CI lints on Python 3.12 and was not reproduced there."
    category: other
    reason: "Embedder normalization landed in a later release (1.2.1); not a Phase 17 must-have. Reproduced only in the local py3.10 frozen environment; the current CI lint target is py3.12."
    evidence_status: "local py3.10 frozen env only; py3.12 CI environment not reproduced"
---

# Phase 17: Engineering Foundation (CI Matrix + Hygiene + PyPI) Verification Report

**Phase Goal:** Contributors get a green regression net on every push and a proven release pipeline — every later schema migration and the MCP shell swap land against a verified matrix, and `docsif` is on PyPI before the MCP Registry needs it.
**Verified:** 2026-11-24T05:05:33Z
**Status:** gaps_found
**Re-verification:** Yes — regeneration against the current tree at HEAD `ba87980` (branch `gsd/phase-24-reverify`), replacing the 2026-11-18T09:59:10Z report. All 55 must-haves were re-derived from the nine PLAN frontmatters merged with the ROADMAP success criteria and checked against the current files and live external state; the prior report was not carried forward.

**Post-verification drift.** `verification.status` reported the prior report stale because 15 covered source files changed after it was written: `.github/workflows/test-matrix.yml`, `docs/changelog.md`, `docs/contributing.md`, `docs/development.md`, `docs/installation.md`, `docs/testing.md`, `pyproject.toml`, `src/sif/_version.py`, `tests/conftest.py`, `tests/test_ci_workflows.py`, `tests/test_docs.py`, `tests/test_release_metadata.py`, `tests/unit/cli/test_watch_cmd.py`, `tests/unit/utils/test_daemon.py`, `uv.lock` (matching the CLI's `moved_files` exactly). Each was re-read at HEAD; the only must-have they falsify is truth 11 (SC1/ENG-01). Two additional covered files changed in the same window but do not affect a truth: `README.md` (torch-backend prose; the mcp-name marker is still line 2) and `src/sif/search/rerank.py` (embedder renormalization; no dead-layer reference). All version-suffixed truths were re-derived at the current 1.2.3 literal.

## Goal Achievement

55 must-have truths (43 outcome truths + 12 `verification: backstop` scope/residual declarations). **54/55 verified**; truth 11 (the literal 8-cell every-push matrix) fails at HEAD because of a deliberate post-phase reduction.

### Observable Truths

| # | Plan | Truth | Status | Evidence |
|---|------|-------|--------|----------|
| 1 | 17-01 | Three dead layers (`models/search.py`, `search/strategy.py`, `database/migrations.py`) deleted with no surviving importer; suite collects and passes | ✓ VERIFIED | All three files absent; dead-literal greps hit only the guard's own literals (`tests/test_hygiene.py:37-128`); full suite 3260 passed / 1 skipped at HEAD |
| 2 | 17-01 | Orphan `compute_rrf_score` removed while `RRFFusion` fusion behavior is byte-identical | ✓ VERIFIED | No `compute_rrf_score` in `src`/`tests`/`examples` outside the guard; `tests/unit/search/test_rrf.py` 43 passed |
| 3 | 17-01 | Makefile has no pre-commit target/install/autoupdate; `.pre-commit-config.yaml` absent | ✓ VERIFIED | `grep pre-commit Makefile` empty; config file absent; `test_makefile_has_no_pre_commit_target` + `test_pre_commit_config_absent` pass |
| 4 | 17-01 | Backstop: docs sweep, tracked-junk removal, and repo-wide zero-reference scan are out of this plan's scope | ✓ VERIFIED (scope honored) | 17-08 and 17-09 verified below; repo-wide unknown-junk scan remains deferred per D-09/D-12 |
| 5 | 17-02 | `uv.lock` resolves CPU-tagged torch from `download.pytorch.org/whl/cpu` on Linux, keeps a PyPI torch for macOS/Windows, contains no nvidia-*/triton | ✓ VERIFIED | `2.14.1+cpu` (py<3.11) / `2.15.0+cpu` (py>=3.11) with the CPU registry (`uv.lock:524-526,2934-3012`); `nvidia` = 0, `triton` = 0 |
| 6 | 17-02 | No black dev dependency, no `[tool.black]`, no black in the lock | ✓ VERIFIED | No `black` in `pyproject.toml`; 0 `"black"` entries in `uv.lock`; guard tests pass |
| 7 | 17-02 | embed/all floor sentence-transformers >=5.4.1 and declare torch directly; all floors llama-cpp-python >=0.3.35; fastapi/uvicorn stay core | ✓ VERIFIED | `pyproject.toml:54-55,72-74`; `fastapi>=0.100.0`/`uvicorn>=0.20.0` core at `:37-38`; guard passes |
| 8 | 17-02 | `pytorch-cpu` index is `explicit = true`; torch source marker-scoped to `sys_platform == 'linux'` | ✓ VERIFIED | `pyproject.toml:95-101`; `test_pyproject_cpu_index_is_explicit` passes |
| 9 | 17-02 | `uv lock --check` exits 0 on the committed lock | ✓ VERIFIED | Re-run: exit 0, "Resolved 106 packages" |
| 10 | 17-02 | Backstop: fleet tolerance asserted structurally; actual per-fleet resolution proven only by the 8-cell matrix | ✓ VERIFIED | Guards assert structure; historical run 43561542242 green across all 8 cells (live API read) |
| 11 | 17-03 | Every branch push and pull_request runs exactly 8 cells (3.10-3.13 x ubuntu/macos) with `fail-fast: false` | ✗ FAILED | At HEAD: 6 cells (`test-matrix.yml:22-29`, macOS 3.11/3.12 excluded) and push `branches: [main]` (`:5`). Post-phase deliberate reduction; see Gaps Summary |
| 12 | 17-03 | Each cell runs bare pytest (no `--no-cov`) and syncs `uv sync --frozen --extra dev --extra embed` | ✓ VERIFIED | `test-matrix.yml:46` (sync), `:49` (`uv run --frozen pytest`, no `--no-cov`); `pyproject.toml:226` addopts, `:229` fail_under 90 |
| 13 | 17-03 | Workflow-level `contents: read`, `pull_request` (not `pull_request_target`), no secrets, setup-uv SHA-pinned | ✓ VERIFIED | `test-matrix.yml:8-9`, `:6`, `:35` SHA `68559e99...`; guard tests pass |
| 14 | 17-03 | Per-ref concurrency with `cancel-in-progress: true`; tag pushes excluded | ✓ VERIFIED | `test-matrix.yml:11-13`; push declares `branches: [main]`, so tag pushes cannot match |
| 15 | 17-03 | One lint/type job on ubuntu-latest/py3.12 runs `ruff check src tests`, `ruff format --check src tests`, `ty check src/sif` | ✓ VERIFIED | `test-matrix.yml:51-79`; guard `test_lint_job_runs_repo_gates` passes |
| 16 | 17-03 | The workflow run for the phase HEAD is green on 8 cells + lint | ✓ VERIFIED | `gh run view 43561542242` (live): conclusion success, headSha `c819f67`, 8 py jobs + lint all success |
| 17 | 17-03 | Backstop: matrix is a fixed literal list; an empty/dynamic/partial matrix is not guard-exercised | ✓ VERIFIED (scope honored) | Still a fixed literal list (now 6 cells via two explicit excludes after the post-phase change); no dynamic matrix |
| 18 | 17-03 | Backstop: the 8 cells compare equal in outcome; only the aggregate is asserted | ✓ VERIFIED (scope honored) | Historical run: all 8 py cell conclusions success; no ordering contract asserted |
| 19 | 17-04 | Detach on a platform without `os.fork` exits non-zero naming POSIX fork + foreground remedy, never a raw AttributeError | ✓ VERIFIED | Library guard `daemon.py:253-258`, CLI guard `watch.py:360-366`; `test_detach_requires_fork` + `test_detach_without_fork_is_refused` pass |
| 20 | 17-04 | Windows install/uninstall-service refuse with a Windows-specific message before any systemctl probe | ✓ VERIFIED | `_service_manager()` win32 guard `watch.py:438-442` raises before any probe; `test_windows_refuses_the_service_with_the_foreground_remedy` passes |
| 21 | 17-04 | Smoke uses explicit argv lists (never a shell), temp `SIF_DB_PATH`, and no model-loading command | ✓ VERIFIED | `scripts/windows_smoke.py:65-84` argv table; `:286` temp `SIF_DB_PATH`; no query/vsearch/embed command; tests pass |
| 22 | 17-04 | Smoke asserts version, collection add, index update Added:1 + fcntl warning, BM25 JSON result, status, Removed:0 + preserved warning, detach/service refusals | ✓ VERIFIED | Assertion table in `scripts/windows_smoke.py`; version read from `_version.py` so it holds at 1.2.3; matcher battery passes |
| 23 | 17-04 | `make windows-smoke` runs HEAD/dirty preflight, `uv python install`, frozen sync, smoke over `hc exec` | ✓ VERIFIED | `Makefile:81-87`; `.PHONY` `:4`, help `:26`; preflight refuses dirty and prints HEAD |
| 24 | 17-04 | Smoke completes green on the synced yoga checkout and records the tested git HEAD | ✓ VERIFIED (recorded external run) | Recorded 8/8 PASS at `48759e2`. `hc ls` today: yoga `state: unreachable` (ssh timeout), so the remote smoke was not re-executed; the committed script/matchers pass locally |
| 25 | 17-04 | Backstop: smoke is not evidence of full Windows support; parity deferred to v2 | ✓ VERIFIED | `docs/development.md:607` degradation-only; `docs/installation.md:332-336`; script docstring agree |
| 26 | 17-04 | Backstop: yoga sync is a human step; script refuses a dirty tree and prints HEAD | ✓ VERIFIED | `_preflight_head()` prints HEAD and returns 1 on dirty output; script unchanged since the recorded run |
| 27 | 17-05 | `_version.py` holds the single version literal and all runtime surfaces derive it | ✓ VERIFIED (re-derived at 1.2.3) | `src/sif/_version.py:3` single literal `"1.2.3"`; `tests/test_version_identity.py` passes; local CLI prints `sif, version 1.2.3` |
| 28 | 17-05 | README contains the exact mcp-name marker line; PyPI description derives from README | ✓ VERIFIED | `README.md:2` exact marker; `pyproject.toml:9` `readme = "README.md"`; live PyPI description contains the marker |
| 29 | 17-05 | Changelog has a release section and footer link; `[Unreleased]` compares the current tag...HEAD | ✓ VERIFIED (re-derived at 1.2.3) | `docs/changelog.md:38` `## [1.2.3]`, `:291` `compare/v1.2.3...HEAD`, `:292` `[1.2.3]`; `[1.1.2]` retained at `:297` |
| 30 | 17-05 | `publish.yml` is v*-tag-gated, builds once on ubuntu with `contents: read`, gates `GITHUB_REF_NAME` against `_version.py`, uploads dist, then TestPyPI → PyPI with job-scoped OIDC and environments | ✓ VERIFIED | Workflow re-read: `tags: ['v*']`, `contents: read`, runpy tag gate `:29-35`, `uv build` once + upload-artifact, download-artifact in both publish jobs, `environment: testpypi`/`pypi`, job-scoped `id-token: write` |
| 31 | 17-05 | PyPI publish has no `skip-existing`; both publish jobs consume the same dist artifact; attestations at trusted-publishing default | ✓ VERIFIED | `skip-existing: true` only on TestPyPI (`:70`); both jobs download `dist`; no `uv build` in publish jobs |
| 32 | 17-05 | 3.13 classifier appears only after a green matrix | ✓ VERIFIED | `pyproject.toml:24` classifier; `git merge-base --is-ancestor f6092f8 9164e4f` → yes |
| 33 | 17-05 | Release Process and installation docs document `make windows-smoke`; no `twine upload` primary path | ✓ VERIFIED | `docs/development.md:607,705`; `docs/installation.md:335`; `grep "twine upload" docs` empty |
| 34 | 17-05 | Backstop: tag/version equality is exact ASCII string equality | ✓ VERIFIED | Build job runs `test "v${VERSION}" = "${GITHUB_REF_NAME}"` — version-agnostic, holds at 1.2.3 |
| 35 | 17-05 | Backstop: mcp-name marker must match future server.json byte-for-byte; Registry check is Phase 22 | ✓ VERIFIED (Phase 22 portion deferred) | Marker is one complete README line; Registry ownership check is Phase 22 scope |
| 36 | 17-06 | GitHub environments `pypi` and `testpypi` exist | ✓ VERIFIED | `gh api repos/zhangtaolab/sif/environments` (live): `pypi` 27264851535, `testpypi` 27264859642 |
| 37 | 17-06 | Maintainer registered the PyPI trusted publisher and TestPyPI pending publisher with the exact identity fields | ✓ VERIFIED (end-to-end) | Publish run 43562577065 published through `publish.yml` + environments `pypi`/`testpypi` (live conclusion success); successful OIDC mint is the only end-to-end proof |
| 38 | 17-06 | The Test Matrix run for the release HEAD is green across 8 cells + lint | ✓ VERIFIED | Run 43561542242 on `c819f67`: 9/9 jobs success (live API read) |
| 39 | 17-06 | No runtime source changed between the smoke commit and the release HEAD except `src/sif/_version.py` | ✓ VERIFIED | `git diff --name-only 48759e2..c819f67 -- src/sif` → exactly `src/sif/_version.py` |
| 40 | 17-06 | 3.13 classifier, README marker, version literal, changelog, and publish workflow all present at release HEAD | ✓ VERIFIED | `git show c819f67:<path>` confirms each artifact at the tagged commit |
| 41 | 17-06 | Backstop: publisher registration is not readable via public API; a successful OIDC publish is the only end-to-end proof | ✓ VERIFIED | Publish run 43562577065: Build, TestPyPI, PyPI all success (live) |
| 42 | 17-07 | Tag v1.1.2 exists and the Publish run has build + publish-testpypi + publish-pypi all successful | ✓ VERIFIED | `git ls-remote --tags origin v1.1.2` (live): tag `fcca22f8` peels to `c819f67`; run 43562577065 3/3 jobs success |
| 43 | 17-07 | PyPI serves docsif 1.1.2 with the exact mcp-name marker in `info.description` | ✓ VERIFIED | Live `pypi.org/pypi/docsif/1.1.2/json`: version 1.1.2, marker present, 220225 / 3108000 bytes |
| 44 | 17-07 | PEP 740 attestations verify for 1.1.2 against the repository | ✓ VERIFIED | Reproduced this round: `uvx pypi-attestations verify pypi --repository https://github.com/zhangtaolab/SIF docsif-1.1.2-py3-none-any.whl` → `OK`, exit 0 |
| 45 | 17-07 | A fresh venv installs docsif==1.1.2 from PyPI and reports the released version | ✓ VERIFIED | Reproduced this round: fresh `/tmp/sif-verif-17` venv → `sif, version 1.1.2` |
| 46 | 17-07 | A fresh venv installs docsif==1.1.2 from TestPyPI (with the PyPI extra index) and reports the same | ✓ VERIFIED | Reproduced this round: fresh `/tmp/sif-testpypi-17` venv from TestPyPI → `sif, version 1.1.2`; TestPyPI JSON serves 1.1.2 with identical sizes |
| 47 | 17-07 | Backstop: PyPI versions are immutable, so a partial upload requires a new patch version | ✓ VERIFIED | No partial upload occurred; attempt 4 published 1.1.2 completely |
| 48 | 17-08 | No non-changelog doc or DESIGN.md names a deleted layer/export, a bare `migrations.py`/`strategy.py` tree entry, or the "legacy migration module" phrase | ✓ VERIFIED | Direct grep over `docs/*.md` + `DESIGN.md` (changelog excluded) returns nothing; `test_docs_do_not_describe_dead_layers` passes |
| 49 | 17-08 | Live-layer documentation survives (core SearchOptions/SearchResult/SearchType, Chunker ABC, Embedder/Reranker/QueryExpander) | ✓ VERIFIED | `docs/models.md:175-230`; `docs/api-reference.md` protocol hits; re-grepped this round |
| 50 | 17-08 | `docs/development.md` "New Search Strategy" describes the live extension path with no ABC and no `search_batch` | ✓ VERIFIED | Section at `docs/development.md:527`; `grep -c search_batch docs/development.md` = 0 |
| 51 | 17-08 | No docs pre-commit instructions; exactly one VERIFY marker remains and it is the bandit one | ✓ VERIFIED | `grep "make pre-commit\|pre-commit install\|pre-commit autoupdate" docs` empty; `grep "VERIFY:" docs` → exactly `docs/testing.md:242` (bandit) |
| 52 | 17-08 | Backstop: doc correctness is asserted by scans, not prose review; an unscanned stale concept can survive | ✓ VERIFIED | Scans exist and pass; limitation is a true declaration of the method |
| 53 | 17-09 | Seven tracked junk paths removed from the index and working tree; no `MagicMock/` path tracked | ✓ VERIFIED | `git ls-files -- "MagicMock/" quick_test.py simple_test.py verify_imports.py` prints nothing; none exists on disk |
| 54 | 17-09 | No source/test/example references the junk paths and the committed suite is green | ✓ VERIFIED | Guard's literal list is the only reference; full suite 3260 passed / 1 skipped at HEAD |
| 55 | 17-09 | Backstop: only the seven named paths are removed; the repo-wide unknown-junk audit stays deferred | ✓ VERIFIED | Guard limits the removal set; unknown-junk audit remains deferred per D-12/CONTEXT |

**Score:** 54/55 truths verified (0 present-but-behavior-unverified; 12 are `verification: backstop` declarations resolved with direct evidence or scope confirmation). Truth 11 is the single FAILED must-have.

### Roadmap Success Criteria

Scored with a non-overlapping truth partition (the prior report's row ranges overlap).

| # | Success Criterion | Status | Covering Truths | Note |
|---|-------------------|--------|-----------------|------|
| 1 | Every push/PR runs the full suite green on py3.10-3.13 x ubuntu/macos — fail_under=90 per cell, CPU torch on Linux, both fleets tolerated | ✗ FAILED | 11-18 | 7/8: row 11 fails literally at HEAD (6 cells, main-only push). The 8-cell matrix was green at release HEAD c819f67 |
| 2 | A Windows smoke run on hc remote yoga proves fork/systemd/flock degrade honestly — degradation, not full support | ✓ VERIFIED | 19-26 | 8/8; recorded 8/8 PASS at `48759e2`; yoga unreachable today |
| 3 | `docsif` v1.1.x installable from PyPI via trusted publishing — TestPyPI dry run, version single-sourced, PEP 740 attestations, README marker before publish | ✓ VERIFIED | 27-31, 33-47 | 20/20; 1.1.2 is still live and installs from both indexes; mechanism re-derived at 1.2.3 |
| 4 | Repo is hygienic — dead layers deleted, tracked junk removed, Makefile/extras/pre-commit cleaned, black dropped, fastapi/uvicorn kept; 3.13 classifier only once green | ✓ VERIFIED | 1-10, 32, 48-55 | 19/19 |

### SC1/ENG-01 Adjudication

**SC1/ENG-01 is NOT literally satisfied at HEAD.** At HEAD `.github/workflows/test-matrix.yml` declares 6 test cells (Linux 3.10-3.13; macOS only 3.10 and 3.13) and triggers push CI only on `main`. SC1 and ENG-01 both require the 8-cell py3.10-3.13 x ubuntu/macos cross product on every push/PR. This is recorded as the phase's single gap above. The cause is the deliberate post-phase quick task 261118-lmm (commits 14d7d245, e8ab1148, f665eee1), which also reversed CONTEXT D-01 ("every push/PR runs the full 8-cell matrix; no PR-vs-push split") and D-03 ("8 cells total"). It is **not** a phase-execution failure: the 8-cell matrix did run green at the phase release HEAD `c819f67` (run 43561542242), and the phase's own guard battery was subsequently renamed to pin the six-cell shape (`test_matrix_declares_six_cells`, `test_matrix_push_trigger_is_main_only`).

### SC3 Adjudication

**SC3's "v1.1.x installable from PyPI" wording is literally satisfied at HEAD.** `docsif==1.1.2` is still served by PyPI and TestPyPI with the exact mcp-name marker and identical 220225/3108000-byte artifacts, and a fresh venv installs it from each index today. PyPI has since accumulated 1.2.0, 1.2.1, and 1.2.2 (latest published), and the local tree is at 1.2.3 (not yet published); that version progression is normal post-phase release maintenance and does not falsify the v1.1.x clause. The single-sourcing mechanism the phase built is re-verified at 1.2.3 (`_version.py` literal → version-identity battery → release-metadata pins → tag gate → docs sample → CLI `1.2.3`).

### Decision Coverage

At phase time the prior report recorded 15/15 CONTEXT decisions honored. **At HEAD 13/15 remain honored**: D-01 (every push/PR, 8 cells, no PR-vs-push split) and D-03 (8 cells total) are reversed by the post-phase six-cell/main-only change that causes the SC1 gap. The other 13 decisions (D-02, D-04..D-15) remain honored. The `decision-coverage-verify` verb is not exposed in this runtime, so this is a direct read of `17-CONTEXT.md` against the current tree rather than a verb re-run.

### Required Artifacts

`gsd_run query verify.artifacts` at HEAD: plans 01 (6/6), 02 (4/4), 04 (5/5), 08 (9/9), 09 (1/1) all pass; plan 03 is 1/2; plan 05 is 6/8; plans 06 and 07 are 0/1. No artifact is missing, stub, or orphan.

| Artifact | Plan | Expected | Status | Details |
|----------|------|----------|--------|---------|
| `tests/test_hygiene.py` | 01/08/09 | Absence/import/Makefile/doc/junk guards | ✓ VERIFIED | All guards pass |
| `src/sif/models/__init__.py` | 01 | Dead search exports removed | ✓ VERIFIED | `__all__` holds only live models |
| `src/sif/database/__init__.py` | 01 | No MigrationManager export | ✓ VERIFIED | Live repos/helpers only |
| `src/sif/search/rrf.py` | 01 | RRFFusion only | ✓ VERIFIED | 43 fusion tests pass |
| `examples/quickstart.py` | 01 | Live API example | ✓ VERIFIED | Compile guard passes |
| `Makefile` | 01/04 | pre-commit-free; windows-smoke target | ✓ VERIFIED | No pre-commit token; `windows-smoke` at `:81` |
| `pyproject.toml` | 02/05 | CPU index/sources/floors; 3.13 classifier | ✓ VERIFIED | `explicit = true` index; Linux-marker torch; classifier `:24` |
| `uv.lock` | 02 | CPU torch, no CUDA/black | ✓ VERIFIED | 0 nvidia/triton/black; `uv lock --check` exit 0 |
| `tests/test_ci_workflows.py` | 02/03 | Lock/packaging/workflow guards | ⚠️ INTENTIONAL DRIFT | Plan expects `test_matrix_declares_eight_cells`; file now has `test_matrix_declares_six_cells` + `test_matrix_push_trigger_is_main_only` (post-phase reduction) |
| `docs/installation.md` | 02/05 | Extras aligned; version sample | ✓ VERIFIED | `sif, version 1.2.3` sample at `:352`; windows-smoke at `:335` |
| `.github/workflows/test-matrix.yml` | 03 | 8-cell matrix + lint job | ⚠️ INTENTIONAL DRIFT | Now 6 cells + main-only push (post-phase); lint job intact |
| `scripts/windows_smoke.py` | 04 | Degradation smoke with matchers | ✓ VERIFIED | Version read from `_version.py`; platform guard; recorded 8/8 PASS |
| `tests/test_windows_smoke_script.py` | 04 | Matcher battery | ✓ VERIFIED | 8 tests pass |
| `src/sif/utils/daemon.py` | 04 | POSIX-fork guard | ✓ VERIFIED | `hasattr(os, "fork")` at `:253` |
| `src/sif/cli/commands/watch.py` | 04 | Detach + win32 service guard | ✓ VERIFIED | Guards at `:360-366` and `:438-442` |
| `src/sif/_version.py` | 05 | Single-sourced release version | ✓ VERIFIED at 1.2.3 | Single literal `"1.2.3"`; plan's `contains: "1.1.2"` is a stale snapshot |
| `README.md` | 05 | mcp-name marker | ✓ VERIFIED | Exact line 2 |
| `docs/changelog.md` | 05 | Release entry + compare links | ✓ VERIFIED | `[1.2.3]` section + links; `[1.1.2]` retained |
| `tests/test_release_metadata.py` | 05 | Release identity/marker/changelog/workflow guards | ✓ VERIFIED at 1.2.3 | Pins retargeted to 1.2.3; all pass |
| `.github/workflows/publish.yml` | 05 | Tag-gated build/publish | ✓ VERIFIED | Re-read in full; run 43562577065 success |
| `docs/development.md` | 05/08 | Release Process rewrite; live how-to | ✓ VERIFIED | windows-smoke at `:607,705`; New Search Strategy at `:527` |
| `17-06-SUMMARY.md` | 06 | Release-gate evidence | ✓ VERIFIED (archived) | Recorded at the archived path; environments, run id, diff, release_head re-confirmed live |
| `17-07-SUMMARY.md` | 07 | Published-release evidence | ✓ VERIFIED (archived) | Tag/PyPI/TestPyPI/attestation/install proofs re-confirmed live or reproduced |
| `tests/test_docs.py` | 08 | `SKIP_COMMAND_PATTERNS` without pre-commit install | ✓ VERIFIED | Doc guards pass |
| `docs/architecture.md`, `docs/models.md`, `docs/api-reference.md`, `DESIGN.md`, `docs/testing.md`, `docs/contributing.md` | 08 | Dead prose removed, live docs kept, one bandit marker | ✓ VERIFIED | Direct greps + guards |
| `tests/test_hygiene.py` junk guard | 09 | `test_tracked_junk_removed` | ✓ VERIFIED | Passes non-vacuously |

The plan 06/07 "File not found" flags are path-resolution artifacts: those plan artifacts name the pre-archive live path `.planning/phases/...`; the summaries exist at `.planning/milestones/v1.2-phases/...`. The plan 03/05 flags are the version/guard renames described above; all are re-verified as satisfied at HEAD.

### Key Link Verification

20 declared key links: 11 verify programmatically via `verify.key-links`; the 9 flagged links all fail only because their `from` value is a component description rather than a relative file path (parser limitation). Each was verified manually on the current tree or against live external state.

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/test_hygiene.py` | deleted module paths | rglob text scan + existence assertions | ✓ WIRED | Guard passes; a surviving importer would fail it |
| `src/sif/models/__init__.py` | `sif.models` consumers | `__all__` no dead names | ✓ WIRED | Test asserts disjunction |
| `examples/quickstart.py` | `database.py` / `bm25.py` | `Database`/`BM25Searcher` usage | ✓ WIRED | Compile guard + direct inspection |
| `pyproject.toml [tool.uv.sources]` | `uv.lock` torch entries | marker-scoped CPU index materialized | ✓ WIRED (manual) | `+cpu` entries + explicit index re-read |
| `tests/test_ci_workflows.py` | `uv.lock` + `pyproject.toml` | text-level guards | ✓ WIRED | All guards pass |
| `test-matrix.yml` | `uv.lock` | `cache-dependency-glob` + `uv sync --frozen` | ✓ WIRED | Workflow text + historical green run |
| `test-matrix.yml` | pyproject pytest/coverage config | bare pytest inherits addopts/fail_under | ✓ WIRED | No `--no-cov`; `fail_under = 90` at `pyproject.toml:229` |
| `Makefile windows-smoke` | `scripts/windows_smoke.py` on yoga | `hc exec --on yoga … uv run --frozen` | ✓ WIRED (manual) | Target text + recorded 8/8 PASS run |
| `watch.py` | `utils/daemon.py` | library guard before `detach()` | ✓ WIRED | Guards at `:360-366` / `:253` |
| `tests/test_windows_smoke_script.py` | `scripts/windows_smoke.py` | direct matcher imports | ✓ WIRED | Tests pass |
| `README.md marker` | PyPI project description | hatchling reads README | ✓ WIRED (manual) | Live PyPI JSON contains the marker |
| `publish.yml build job` | `src/sif/_version.py` | `runpy` + `GITHUB_REF_NAME` gate | ✓ WIRED (manual) | Gate re-read; version-agnostic at 1.2.3 |
| `publish.yml publish jobs` | environments `pypi`/`testpypi` | environment-scoped OIDC | ✓ WIRED (manual) | Environment blocks + both envs exist (live API) |
| `publish.yml environments` | GitHub environments + publisher registration | exact identity fields | ✓ WIRED (manual) | Provenance records `publish.yml` + `pypi`; publish succeeded |
| `17-04-SUMMARY smoke HEAD` | release HEAD | `git diff -- src/sif` limited to `_version.py` | ✓ WIRED (manual) | Diff re-run: exactly `src/sif/_version.py` |
| `tag v1.1.2` | `publish.yml` | tag push is the only trigger | ✓ WIRED (manual) | Tag peels to `c819f67` (live ls-remote); `tags: ['v*']` |
| `PyPI artifact` | MCP Registry ownership marker | `info.description` contains marker | ✓ WIRED (manual) | Fresh PyPI JSON check |
| `tests/test_hygiene.py` | docs + DESIGN.md | dead literal + VERIFY scans | ✓ WIRED | Guards pass; direct grep confirms |
| `docs/development.md` | `src/sif/search/` + `sif.core.models` | live searcher how-to | ✓ WIRED | Section verified |
| `tests/test_hygiene.py` | git index | `git ls-files` + sentinel | ✓ WIRED | Guard passes non-vacuously |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `src/sif/_version.py` | `__version__` | single literal → hatchling wheel METADATA → PyPI JSON → installed CLI | Yes: PyPI serves 1.1.2 (installed CLI prints it); local tree prints `1.2.3` through the same path | ✓ FLOWING |
| `README.md` | PyPI `info.description` | hatchling `readme = "README.md"` at build time | Yes: marker present in live PyPI and TestPyPI JSON | ✓ FLOWING |
| `uv.lock` | torch resolution | explicit CPU index + Linux marker | Yes: `+cpu` entries; historical 8-cell matrix green | ✓ FLOWING |
| `scripts/windows_smoke.py` | CLI outputs | temp `SIF_DB_PATH` SQLite DB → CLI stdout/stderr → matchers | Yes: recorded run produced all PASS lines; matchers exercised locally | ✓ FLOWING |
| `publish.yml` build job | dist artifact | `uv build` → upload-artifact → both publish jobs | Yes: identical file sizes on both indexes | ✓ FLOWING |
| render surfaces | — | none introduced by this phase | N/A | N/A |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Full regression suite | `pytest -q` | 3260 passed, 1 skipped @ 95.12% in 203.52 s | ✓ PASS |
| Phase guard battery | `pytest tests/test_hygiene.py tests/test_ci_workflows.py tests/test_release_metadata.py tests/test_windows_smoke_script.py tests/test_version_identity.py -q --no-cov` | 58 passed in 1.01 s | ✓ PASS |
| Watch/daemon guards (truths 19/20) | `pytest tests/unit/cli/test_watch_cmd.py::TestDaemonFlagGuards tests/unit/utils/test_daemon.py -q --no-cov` | 45 passed in 0.27 s | ✓ PASS |
| RRF fusion behavior | `pytest tests/unit/search/test_rrf.py -q --no-cov` | 43 passed | ✓ PASS |
| Lock freshness | `uv lock --check` | exit 0, Resolved 106 packages | ✓ PASS |
| Ruff gates | `ruff check src tests` / `ruff format --check src tests` | All checks passed / 237 files already formatted | ✓ PASS |
| Type gate (local py3.10 frozen) | `uv run --frozen --extra dev ty check src/sif` | exit 1, 1 diagnostic at `embedding/embedder.py:870` | ⚠️ OBSERVED (post-phase, see Advisory) |
| Type gate (local miniconda py3.13) | `ty check src/sif` | exit 1, 10 diagnostics | ⚠️ OBSERVED (environment drift) |
| Local version surface | `python -m sif.cli.main --version` | `sif, version 1.2.3` | ✓ PASS |
| PyPI JSON (1.1.2) | `curl https://pypi.org/pypi/docsif/1.1.2/json` | version 1.1.2; marker present; 220225/3108000 | ✓ PASS |
| TestPyPI JSON (1.1.2) | `curl https://test.pypi.org/pypi/docsif/1.1.2/json` | version 1.1.2; marker present; identical sizes | ✓ PASS |
| PyPI install (fresh venv) | `uv pip install docsif==1.1.2` → `sif --version` | `sif, version 1.1.2` | ✓ PASS |
| TestPyPI install (fresh venv) | TestPyPI index + PyPI extra index → `sif --version` | `sif, version 1.1.2` | ✓ PASS |
| PEP 740 attestation | `uvx pypi-attestations verify pypi --repository https://github.com/zhangtaolab/SIF docsif-1.1.2-py3-none-any.whl` | `OK`, exit 0 | ✓ PASS |
| Test Matrix on release HEAD | `gh run view 43561542242` | conclusion success; headSha `c819f67`; 8 py cells + lint success | ✓ PASS |
| Publish workflow | `gh run view 43562577065` | conclusion success; Build, TestPyPI, PyPI all success | ✓ PASS |
| Release tag | `git ls-remote --tags origin v1.1.2 'v1.1.2^{}'` | `v1.1.2` peels to `c819f67` | ✓ PASS |
| GitHub environments | `gh api repos/zhangtaolab/sif/environments` | `pypi` (27264851535) + `testpypi` (27264859642) | ✓ PASS |
| Classifier-after-green ordering | `git merge-base --is-ancestor f6092f8 9164e4f` | yes | ✓ PASS |
| Windows degradation smoke | recorded `make windows-smoke` (hc yoga, `48759e2`) | 8/8 PASS at `48759e2`; yoga unreachable today | ✓ PASS (recorded) |

### Probe Execution

None applicable. No probe scripts are declared or conventionally present (`find scripts -path '*/tests/probe-*.sh'` returns nothing; no probe reference appears in any phase PLAN/SUMMARY).

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|----------------|-------------|--------|----------|
| ENG-01 | 17-02, 17-03, 17-05 | Full suite green on py3.10-3.13 x ubuntu/macos, fail_under=90 per cell, CPU torch on Linux, both fleets tolerated, every push/PR | ✗ BLOCKED | The 8-cell matrix was green at release HEAD `c819f67` (run 43561542242), but at HEAD the workflow is 6 cells and push-main-only; see the SC1 gap |
| ENG-02 | 17-04, 17-05 | Windows degradation verified by a CI smoke on hc remote yoga (uv python install first; fork/systemd/flock degrade honestly) | ✓ SATISFIED | Guards + committed smoke + matcher battery + Makefile target; recorded 8/8 PASS at `48759e2`; docs document the on-demand step |
| ENG-03 | 17-05, 17-06, 17-07 | Maintainer can publish docsif to PyPI via trusted publishing (marker before publish, TestPyPI dry run, version single-sourced, PEP 740 attestations) | ✓ SATISFIED | PyPI + TestPyPI serve 1.1.2; marker live; fresh installs from both indexes; attestation verifies; single-sourcing now carries 1.2.3 |
| ENG-04 | 17-01, 17-02, 17-05, 17-08, 17-09 | Hygienic repo: dead layers deleted, tracked junk removed, Makefile/extras/pre-commit cleaned, black dropped, fastapi/uvicorn kept, 3.13 classifier only when green | ✓ SATISFIED | All deletions/guards verified; 0 junk tracked; no pre-commit/black tokens; core deps intact; classifier after green run |

No orphaned requirements: `.planning/milestones/v1.2-REQUIREMENTS.md` maps exactly ENG-01..ENG-04 to Phase 17 (lines 24-27, traceability lines 141-144 all Complete), every ID is claimed by at least one plan's `requirements:` frontmatter, and no requirement mapped to Phase 17 is unclaimed.

### Prohibitions (must-NOT checks)

14 plan-declared prohibitions re-evaluated. 13 are satisfied at HEAD; the 17-03 "no removed cell" clause is now violated by the post-phase six-cell reduction (not a coverage-gate weakening — `fail_under` stays 90 and no `--no-cov`).

| Plan | Prohibition | Status | Evidence |
|------|-------------|--------|----------|
| 17-01 | MUST NOT delete code on a runtime path | ✓ SATISFIED | Deletions limited to the three verified-dead modules and the orphan RRF function; full suite green |
| 17-01 | MUST NOT leave examples/Makefile describing deleted layers or phantom pre-commit | ✓ SATISFIED | Compile guard + Makefile guard; dead-literal greps clean |
| 17-02 | MUST NOT add a package or trust a third-party index beyond the explicit CPU index | ✓ SATISFIED | Single `explicit = true` index serving torch only, marker-scoped |
| 17-03 | MUST NOT weaken the coverage gate to make the matrix green — no `--no-cov`, no lowered fail_under, no skipped or removed cell | ⚠️ PARTIALLY VIOLATED AT HEAD | No `--no-cov`; `fail_under = 90` unchanged; but two macOS cells were removed post-phase (not to mask a red cell, but the literal "no removed cell" clause no longer holds) |
| 17-04 | MUST NOT present the smoke as full Windows support | ✓ SATISFIED | `docs/development.md:607` degradation-only; WIN-F1 deferred |
| 17-04 | MUST NOT touch the user's real index/collections/model cache on yoga | ✓ SATISFIED | Temp `SIF_DB_PATH`; BM25-only argv; script unchanged since the recorded run |
| 17-05 | MUST NOT publish a release without the mcp-name marker | ✓ SATISFIED | Published 1.1.2 `info.description` contains the exact marker (live) |
| 17-05 | MUST NOT publish from a mismatched tag or a red matrix | ✓ SATISFIED | Tag gate in build job; run 43561542242 green on `c819f67`; tag peels to `c819f67` |
| 17-06 | MUST NOT weaken publisher identity or disable OIDC | ✓ SATISFIED | Workflow uses `publish.yml` + environments `pypi`/`testpypi` + job-scoped `id-token: write`; successful OIDC publish |
| 17-07 | MUST NOT rebuild in publish jobs or re-upload under a mutated version | ✓ SATISFIED | No `uv build` in publish jobs; both download artifact `dist`; identical published sizes |
| 17-07 | MUST NOT reuse credentials/environment between TestPyPI and PyPI | ✓ SATISFIED | Separate jobs, separate environments, separate repository URLs; no secrets |
| 17-08 | MUST NOT delete documentation of live layers | ✓ SATISFIED | Live models/protocols present in `docs/models.md` and `docs/api-reference.md` |
| 17-08 | MUST NOT hand-edit generator-owned `docs/cli-reference.md` / `docs/configuration.md` | ✓ SATISFIED | `.github/workflows/docs.yml` regenerates and fails on `git diff --exit-code`; neither file is in the phase's changed set |
| 17-09 | MUST NOT remove any path not on the seven-path verified list | ✓ SATISFIED | `git show --stat 8e4090d`: exactly the seven junk paths plus the guard |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/placeholder prose in the covered implementation files | ℹ️ Info | Debt-marker gate clean |
| `src/sif/embedding/embedder.py` | 870 | `ty` invalid-return-type (local py3.10 frozen env); 10 diagnostics under local py3.13 miniconda | ℹ️ Info — post-phase drift | Introduced by later release work (1.2.1 normalization); not a Phase 17 truth. CI lints on py3.12 and was not reproduced there |
| `.github/workflows/publish.yml` | publish jobs | No job-level `timeout-minutes` on publish jobs (WR-06); no concurrency guard (WR-07) | ℹ️ Info — open review findings | Plan 17-05 requires build-once/tag-gate/OIDC, not these hardening items |
| `docs/testing.md` | 4, 202 | Collected/passed counts (3,234 / 3,233) are stale at HEAD (3,260 passed / 1 skipped) (IN-09) | ℹ️ Info — open review finding | No must-have impact |
| review dispositions | — | 19 of 24 review rows remain `open` (3 Warning, 5 Info in the current review) | ℹ️ Info — user-accepted | None falsifies a must-have as worded |

### Advisory (New Scope, Unevidenced)

| # | Finding | Category | Why Advisory |
|---|---------|----------|--------------|
| 1 | Local frozen `.venv` (Python 3.10) reports 1 `ty` error at `src/sif/embedding/embedder.py:870`; the local py3.13 miniconda reports 10. | other | Post-phase code from a later release; reproduced only in local environments, not the py3.12 CI lint environment |

### Human Verification Required

None blocking. The Windows degradation smoke is a recorded external run (`48759e2`, 8/8 PASS) and was not re-executed because `hc ls` reports yoga `state: unreachable` (ssh timeout). Re-running `make windows-smoke` when yoga is reachable would refresh that evidence; it does not block the phase verdict.

### Gaps Summary

One gap, caused by a deliberate post-phase change rather than phase execution:

- **SC1/ENG-01 no longer holds literally at HEAD.** `.github/workflows/test-matrix.yml` is a six-cell matrix (macOS 3.11 and 3.12 excluded) and pushes trigger it only on `main`. The phase shipped and proved the original contract: the 8-cell py3.10-3.13 x ubuntu/macos matrix plus lint ran green at the release HEAD `c819f67` (run 43561542242). Quick task 261118-lmm later reduced the matrix and moved push CI to main, also reversing CONTEXT D-01 and D-03. The 17-03 prohibition's literal "no removed cell" clause is consequently violated at HEAD, though the coverage gate itself (`fail_under = 90`, no `--no-cov`) was not weakened.

Everything else the phase promised is verified at HEAD: the Windows degradation guards/smoke/Makefile target (recorded green; yoga currently unreachable), the trusted-publishing release (`docsif` 1.1.2 still installable from PyPI and TestPyPI, marker present, PEP 740 attestation OK, single-sourcing now carrying 1.2.3), and repo hygiene (dead layers, orphan export, tracked junk, pre-commit/black removal, live docs preserved, classifier after green).

---

_Verified: 2026-11-24T05:05:33Z_
_Verifier: Claude (gsd-verifier)_
