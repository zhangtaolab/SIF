---
phase: 17-engineering-foundation-ci-matrix-hygiene-pypi
verified: 2026-11-18T09:59:10Z
status: passed
score: 55/55 must-haves verified
covered_files:
  - ".github/workflows/publish.yml"
  - ".github/workflows/test-matrix.yml"
  - ".planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-01-PLAN.md"
  - ".planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-01-SUMMARY.md"
  - ".planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-02-PLAN.md"
  - ".planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-02-SUMMARY.md"
  - ".planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-03-PLAN.md"
  - ".planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-03-SUMMARY.md"
  - ".planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-04-PLAN.md"
  - ".planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-04-SUMMARY.md"
  - ".planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-05-PLAN.md"
  - ".planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-05-SUMMARY.md"
  - ".planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-06-PLAN.md"
  - ".planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-06-SUMMARY.md"
  - ".planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-07-PLAN.md"
  - ".planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-07-SUMMARY.md"
  - ".planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-08-PLAN.md"
  - ".planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-08-SUMMARY.md"
  - ".planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-09-PLAN.md"
  - ".planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-09-SUMMARY.md"
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
covered_digest: "v4:sha256:fea056d66237c33df6d4e06fb454fcc7f765595d8d914cbf6b761701710e42f8"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 55/55
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 17: Engineering Foundation (CI Matrix + Hygiene + PyPI) Verification Report

**Phase Goal:** Contributors get a green regression net on every push and a proven release pipeline — every later schema migration and the MCP shell swap land against a verified matrix, and `docsif` is on PyPI before the MCP Registry needs it.
**Verified:** 2026-11-18T09:59:10Z
**Status:** passed
**Re-verification:** Yes — regeneration. Every must-have was re-derived from the current tree (plans + ROADMAP success criteria), not carried forward from the prior report's claims. The tree changed since the previous verification (2026-11-18T03:37:14Z) by exactly one commit set: the v1.2 milestone version bump `d97838c` (2026-11-18), which rotated the release identity 1.1.2 → 1.2.0 across `src/sif/_version.py`, `server.json`, `.claude-plugin/*`, `tests/test_release_metadata.py`, `tests/test_windows_smoke_script.py`, `docs/changelog.md`, `docs/installation.md`. Every version-suffixed must-have was therefore re-checked AT 1.2.0, and every external (immutable) release fact was re-confirmed live.

## Goal Achievement

55 must-have truths (43 outcome truths + 12 `verification: backstop` scope/residual declarations), re-derived from the nine PLAN frontmatters merged with the ROADMAP success criteria (no roadmap SC is reduced by any plan; ENG-01..ENG-04 all claimed). Evidence below was collected against the current tree at HEAD `8f38c24` on branch `dev`, at version 1.2.0.

The full regression gate was NOT re-run: the quick task that produced `d97838c` ran the full suite at current HEAD — **3233 passed, 1 skipped @ 95.03% coverage, ruff/format green** — and no task commits followed it, so that fresh full-suite evidence is cited instead. Targeted guard batteries were re-run live in this verification (fast named-test runs, not the suite):

- Phase guard battery (`tests/test_hygiene.py tests/test_ci_workflows.py tests/test_release_metadata.py tests/test_windows_smoke_script.py tests/test_version_identity.py`): **58 passed** in 1.16 s — includes the release-metadata guards re-pinned to 1.2.0 (pins `== "1.2.0"`, changelog `## [1.2.0]` / `[1.2.0]:` / `compare/v1.2.0...HEAD`).
- Watch/daemon guard battery (`tests/unit/cli/test_watch_cmd.py::TestDaemonFlagGuards tests/unit/utils/test_daemon.py`): **45 passed** — exercises the detach-without-fork refusal and the Windows service refusal (behavior-dependent truths 19/20).
- RRF fusion battery (`tests/unit/search/test_rrf.py`): **43 passed**.
- `uv lock --check`: exit 0 ("Resolved 106 packages"). `ruff check src tests`: clean. `ruff format --check src tests`: 236 files already formatted. `ty check src/sif`: clean.
- Local version surface: `python -m sif.cli.main --version` → **`sif, version 1.2.0`** (single-sourced from `_version.py`).

### Observable Truths

| # | Plan | Truth | Status | Evidence |
|---|------|-------|--------|----------|
| 1 | 17-01 | Three dead layers (`models/search.py`, `search/strategy.py`, `database/migrations.py`) deleted with no surviving importer; suite collects and passes | ✓ VERIFIED | All three files absent (`ls` fails); `grep -rn "sif\.models\.search\|sif\.search\.strategy\|MigrationManager\|compute_rrf_score" src tests examples` returns nothing outside the guard's own literals; hygiene guards pass; full suite 3233 passed / 1 skipped at `d97838c` |
| 2 | 17-01 | Orphan `compute_rrf_score` removed while `RRFFusion` fusion behavior is byte-identical | ✓ VERIFIED | No `compute_rrf_score` anywhere in `src`/`tests`/`examples`; `tests/unit/search/test_rrf.py` 43 passed (re-run this round) |
| 3 | 17-01 | Makefile has no pre-commit target/install/autoupdate; `.pre-commit-config.yaml` absent | ✓ VERIFIED | `grep pre-commit Makefile` → no match; config file absent; `test_makefile_has_no_pre_commit_target` + `test_pre_commit_config_absent` pass in the 58-test battery |
| 4 | 17-01 | Backstop: docs sweep, tracked-junk removal, and repo-wide zero-reference scan are out of this plan's scope | ✓ VERIFIED (scope honored) | 17-08 and 17-09 verified below; the repo-wide unknown-junk/zero-reference scan remains deferred per D-09/D-12 |
| 5 | 17-02 | `uv.lock` resolves CPU-tagged torch from `download.pytorch.org/whl/cpu` on Linux, keeps a PyPI torch for macOS/Windows, contains no nvidia-*/triton | ✓ VERIFIED | `+cpu` entries `2.14.1+cpu` (py<3.11) / `2.15.0+cpu` (py>=3.11) with the CPU registry; `grep -c nvidia uv.lock` = 0, `triton` = 0; `uv lock --check` exit 0 |
| 6 | 17-02 | No black dev dependency, no `[tool.black]`, no black in the lock | ✓ VERIFIED | No `black` in `pyproject.toml`; 0 `name = "black"` entries in `uv.lock`; `test_lock_has_no_black`/`test_pyproject_has_no_black_section` pass |
| 7 | 17-02 | embed/all floor sentence-transformers >=5.4.1 and declare torch directly; all floors llama-cpp-python >=0.3.35; fastapi/uvicorn stay core | ✓ VERIFIED | `pyproject.toml:54-55` (embed), `:72-74` (all); `fastapi>=0.100.0`/`uvicorn>=0.20.0` core at `:37-38`; guard tests pass |
| 8 | 17-02 | `pytorch-cpu` index is `explicit = true`; torch source marker-scoped to `sys_platform == 'linux'` | ✓ VERIFIED | `pyproject.toml:95-101`; `test_pyproject_cpu_index_is_explicit` passes |
| 9 | 17-02 | `uv lock --check` exits 0 on the committed lock | ✓ VERIFIED | Re-run this round: exit 0, "Resolved 106 packages" |
| 10 | 17-02 | Backstop: fleet tolerance asserted structurally; actual per-fleet resolution proven only by the 8-cell matrix | ✓ VERIFIED | Guards assert structure (a `+cpu` torch, a PyPI torch, no CUDA stack); run 43561542242 green across all 8 cells (re-read live from the GitHub API this round) |
| 11 | 17-03 | Every branch push and pull_request runs exactly 8 cells (3.10-3.13 × ubuntu/macos) with `fail-fast: false` | ✓ VERIFIED | `test-matrix.yml:3-6,22-24` — literal 2×4 matrix, `fail-fast: false`; run 43561542242 reports 8 `py*` jobs + lint, all success (live API read) |
| 12 | 17-03 | Each cell runs bare pytest (no `--no-cov`) and syncs `uv sync --frozen --extra dev --extra embed` | ✓ VERIFIED | `test-matrix.yml:41-44` (`uv run --frozen pytest`, no `--no-cov`); `pyproject.toml:226` addopts `--cov=src/sif ...`, `:229` `fail_under = 90`; guard passes |
| 13 | 17-03 | Workflow-level `contents: read`, `pull_request` (not `pull_request_target`), no secrets, setup-uv SHA-pinned | ✓ VERIFIED | `test-matrix.yml:8-9` (permissions), `:5` (`pull_request:`), `:30` SHA `68559e99cc807c1eb7e9238fd43a15bba460eec2`; guard tests pass |
| 14 | 17-03 | Per-ref concurrency with `cancel-in-progress: true`; tag pushes excluded | ✓ VERIFIED | `test-matrix.yml:11-13`; push trigger declares `branches: ['**']` — tag pushes do not match `branches`, so they cannot trigger the matrix |
| 15 | 17-03 | One lint/type job on ubuntu-latest/py3.12 runs `ruff check src tests`, `ruff format --check src tests`, `ty check src/sif` | ✓ VERIFIED | `test-matrix.yml:46-74`; run 43561542242 lint job `success` (live API read); local ruff/format/ty re-run clean this round |
| 16 | 17-03 | The workflow run for the phase HEAD is green on 8 cells + lint | ✓ VERIFIED | `gh run view 43561542242` (live): headSha `c819f67`, conclusion `success`, all 9 jobs `success` |
| 17 | 17-03 | Backstop: matrix is a fixed literal list; an empty/dynamic/partial matrix is not guard-exercised | ✓ VERIFIED | Literal `os` × `python-version` lists in the workflow; the observed run shows 8 distinct cells, covering the residual concern |
| 18 | 17-03 | Backstop: 8 cells compare equal in outcome; only the aggregate is asserted | ✓ VERIFIED | All 8 cell conclusions are `success` (live job list); no ordering contract asserted |
| 19 | 17-04 | Detach on a platform without `os.fork` exits non-zero naming POSIX fork + foreground remedy, never a raw AttributeError | ✓ VERIFIED | Library guard `daemon.py:253` and CLI guard `watch.py:359` both `hasattr(os, "fork")`; `test_detach_requires_fork` + `test_detach_without_fork_is_refused` pass in the 45-test battery (re-run this round) |
| 20 | 17-04 | Windows install/uninstall-service refuse with a Windows-specific message before any systemctl probe | ✓ VERIFIED | `_service_manager()` win32 guard (`watch.py:438-442`) raises `ClickException` before any probe; `test_windows_refuses_the_service_with_the_foreground_remedy` passes |
| 21 | 17-04 | Smoke uses explicit argv lists (never a shell), temp `SIF_DB_PATH`, and no query/vsearch/embed model-loading command | ✓ VERIFIED | `scripts/windows_smoke.py` `build_cli_invocations` builds argv lists and rejects an empty version literal (`:65-76`); BM25-only invocations; `test_commands_are_argv_lists_without_model_loading` passes |
| 22 | 17-04 | Smoke asserts version, collection add, index update Added:1 + fcntl warning, BM25 JSON result, status, Removed:0 + preserved warning, detach/service refusals | ✓ VERIFIED | Assertion table in `scripts/windows_smoke.py`; the version step reads the repo's single-sourced literal via `_expected_version()` (`:138-141`), so it holds at 1.2.0 without script edits; matcher battery 8 tests green (re-run); recorded live run printed all 8 PASS lines |
| 23 | 17-04 | `make windows-smoke` runs HEAD/dirty preflight, `uv python install`, frozen sync, and the smoke over `hc exec` | ✓ VERIFIED | `Makefile:81-87` target present (windows-smoke in `.PHONY` at `:4`, help at `:26`); preflight refuses a dirty tree and prints HEAD |
| 24 | 17-04 | Smoke completes green on the synced yoga checkout and records the tested git HEAD | ✓ VERIFIED (recorded) | Recorded run at HEAD `48759e2c532d01d92a0deef08520a58c41115378`: 8/8 PASS, independently reproduced by the 2026-11-14 verifier and re-confirmed by the 2026-11-18T03:37Z re-verification. Yoga remains unreachable at this regeneration (`hc ls`: "cannot reach Yoga" — desktop-session SSH refusal), so the remote smoke was not re-executed; the committed script/matchers and their unit battery were re-verified locally |
| 25 | 17-04 | Backstop: smoke is not evidence of full Windows support; parity deferred to v2 | ✓ VERIFIED | `docs/development.md:607` states degradation-only ("not a claim of full Windows support, which remains deferred"); script docstring + `docs/installation.md:308` agree; WIN-F1 remains deferred |
| 26 | 17-04 | Backstop: yoga sync is a human step; script refuses a dirty tree and prints HEAD | ✓ VERIFIED | `_preflight_head()` prints HEAD and returns 1 on dirty output; `git status --porcelain` gate present; script unchanged since the recorded run (not in the since-prior-verification change set) |
| 27 | 17-05 | `_version.py` holds the single version literal and all runtime surfaces derive it — **re-derived at 1.2.0** | ✓ VERIFIED | `src/sif/_version.py` contains the single literal `"1.2.0"` (one `__version__` assignment, nothing else); `tests/test_version_identity.py` battery passes (asserts `sif.__version__`, `sif._version.__version__`, `sif.cli.__version__`, `APP_VERSION`, MCP `serverInfo`); local CLI prints `sif, version 1.2.0`; `server.json` both version fields `"1.2.0"` |
| 28 | 17-05 | README contains the exact mcp-name marker line; PyPI description derives from README | ✓ VERIFIED | `README.md:2` exact `<!-- mcp-name: io.github.zhangtaolab/sif -->` on its own line; hatchling `readme = "README.md"`; live PyPI JSON `info.description` contains the marker (re-fetched this round) |
| 29 | 17-05 | Changelog has a release section and footer link; `[Unreleased]` compares the current tag...HEAD — **re-derived at 1.2.0** | ✓ VERIFIED | `docs/changelog.md:38` `## [1.2.0] - 2026-11-18`, `:262` `[Unreleased]: .../compare/v1.2.0...HEAD`, `:264` `[1.2.0]` release link; the `[1.1.2]` section/link retained at `:57,265`; the retargeted release-metadata guard asserts exactly these pins and passes |
| 30 | 17-05 | `publish.yml` is v*-tag-gated, builds once on ubuntu with `contents: read`, gates `GITHUB_REF_NAME` against `_version.py`, uploads dist, then TestPyPI → PyPI with job-scoped OIDC and environments | ✓ VERIFIED | Workflow text re-read on current tree: `tags: ['v*']`, `permissions: contents: read`, runpy tag gate `test "v${VERSION}" = "${GITHUB_REF_NAME}"`, `uv build` once + `upload-artifact`, `download-artifact` in both publish jobs, `environment: testpypi`/`pypi` with job-scoped `id-token: write`; all workflow guards pass; Publish run 43562577065 succeeded through this exact path (live API read) |
| 31 | 17-05 | PyPI publish has no `skip-existing`; both publish jobs consume the same dist artifact; attestations stay at the trusted-publishing default | ✓ VERIFIED | `skip-existing: true` only on TestPyPI; both jobs `download-artifact name: dist`, no `uv build` in publish jobs; published wheel/sdist sizes identical on both indexes (220225/3108000; PyPI re-fetched live, TestPyPI per prior same-day reproduction) |
| 32 | 17-05 | 3.13 classifier appears only after a green matrix | ✓ VERIFIED | `pyproject.toml:24` classifier after 3.12; commit ancestry re-checked this round: green-run commit `f6092f8` IS an ancestor of classifier commit `9164e4f` (`git merge-base --is-ancestor` → yes) |
| 33 | 17-05 | Release Process and installation docs document `make windows-smoke`; no `twine upload` primary path | ✓ VERIFIED | `docs/development.md:607,705`; `docs/installation.md:308`; `grep "twine upload" docs` → empty |
| 34 | 17-05 | Backstop: tag/version equality is exact ASCII string equality | ✓ VERIFIED | Build job runs `test "v${VERSION}" = "${GITHUB_REF_NAME}"` (re-read in workflow text this round) — version-agnostic gate that holds at 1.2.0 |
| 35 | 17-05 | Backstop: mcp-name marker must match future server.json byte-for-byte and sit on a line boundary; Registry check is Phase 22 | ✓ VERIFIED (Phase 22 portion deferred) | Marker is one complete README line at `:2`; `server.json` version identity already aligned at 1.2.0 by the bump; Registry ownership check is Phase 22 scope |
| 36 | 17-06 | GitHub environments `pypi` and `testpypi` exist | ✓ VERIFIED | `gh api repos/zhangtaolab/sif/environments` (live this round): `pypi` id 27264851535, `testpypi` id 27264859642 |
| 37 | 17-06 | Maintainer registered the PyPI trusted publisher and TestPyPI pending publisher with the exact identity fields | ✓ VERIFIED (end-to-end) | Signed provenance publisher record: kind GitHub, repository `zhangtaolab/SIF`, workflow `publish.yml`, environment `pypi`; Publish run 43562577065 published to both indexes (live conclusion read this round); TestPyPI pending publisher proven by the successful first publish |
| 38 | 17-06 | The Test Matrix run for the release HEAD is green across 8 cells + lint | ✓ VERIFIED | Run 43561542242 on `c819f67`: 9/9 jobs `success` (live API read this round) |
| 39 | 17-06 | No runtime source changed between the smoke commit and the release HEAD except `src/sif/_version.py` | ✓ VERIFIED | Re-run this round: `git diff --name-only 48759e2..c819f67 -- src/sif` prints exactly `src/sif/_version.py` |
| 40 | 17-06 | 3.13 classifier, README marker, version literal, changelog, and publish workflow all present at release HEAD | ✓ VERIFIED | `git show c819f67:<path>` confirms each artifact at the tagged commit (immutable history; release facts unchanged); current tree additionally holds the same artifacts rotated to 1.2.0 |
| 41 | 17-06 | Backstop: publisher registration is not readable via public API; a successful OIDC publish is the only end-to-end proof | ✓ VERIFIED | Publish run 43562577065: Build, TestPyPI, and PyPI all `success` (live API read this round) |
| 42 | 17-07 | Tag v1.1.2 exists and the Publish run has build + publish-testpypi + publish-pypi all successful | ✓ VERIFIED | `git ls-remote --tags origin v1.1.2 'v1.1.2^{}'` (live this round): tag object `fcca22f8` peels to `c819f67`; `gh run view 43562577065` (live): conclusion `success`, 3/3 jobs success |
| 43 | 17-07 | PyPI serves docsif 1.1.2 with the exact mcp-name marker in `info.description` | ✓ VERIFIED | Fresh `curl https://pypi.org/pypi/docsif/1.1.2/json` this round: version 1.1.2, marker present, files 220225 (wheel) / 3108000 (sdist) — identical to the published bytes |
| 44 | 17-07 | PEP 740 attestations verify for 1.1.2 against the repository | ✓ VERIFIED | Reproduced by the 2026-11-18T03:37Z re-verification earlier today (`uvx pypi-attestations verify pypi --repository https://github.com/zhangtaolab/SIF docsif-1.1.2-py3-none-any.whl` → OK, exit 0); the published artifacts are immutable, and none of the five files changed since touch the publish path, so the proof stands unchanged |
| 45 | 17-07 | A fresh venv installs docsif==1.1.2 from PyPI and reports the released version | ✓ VERIFIED | Fresh venv install re-executed this round: `/tmp/sif-verif-regen-17` + `uv pip install docsif==1.1.2` → **`sif, version 1.1.2`** |
| 46 | 17-07 | A fresh venv installs docsif==1.1.2 from TestPyPI (with the PyPI extra index) and reports the same | ✓ VERIFIED (recorded) | Independently reproduced by the 2026-11-18T03:37Z re-verification earlier today (fresh venv + TestPyPI index → `sif, version 1.1.2`; TestPyPI JSON served 1.1.2 with identical sizes). This round's re-fetch was blocked by a transient sandbox DNS failure for `test.pypi.org` (nslookup resolves; `pypi.org` returns 200 in the same session); the index is immutable and no covered file touching the publish path changed, so the same-day proof stands |
| 47 | 17-07 | Backstop: PyPI versions are immutable, so a partial upload requires a new patch version | ✓ VERIFIED | No partial upload occurred; attempts 1-3 failed at OIDC mint before upload; attempt 4 published 1.1.2 completely; version legitimately consumed by success |
| 48 | 17-08 | No non-changelog doc or DESIGN.md names a deleted layer/export, a bare `migrations.py`/`strategy.py` tree entry, or the "legacy migration module" phrase | ✓ VERIFIED | Direct grep over `docs/*.md` + `DESIGN.md` (changelog excluded) for the full literal list returns nothing (re-run this round); `test_docs_do_not_describe_dead_layers` passes |
| 49 | 17-08 | Live-layer documentation survives (core SearchOptions/SearchResult/SearchType, Chunker ABC, Embedder/Reranker/QueryExpander) | ✓ VERIFIED | `docs/models.md:175+` (SearchType/SearchOptions sections), `docs/api-reference.md` (6 Embedder/Reranker/QueryExpander hits; SearchOptions/SearchResult/SearchType present) — re-grepped this round |
| 50 | 17-08 | `docs/development.md` "New Search Strategy" describes the live extension path with no ABC and no `search_batch` | ✓ VERIFIED | Section at `docs/development.md:527`; `grep -c search_batch docs/development.md` = 0 |
| 51 | 17-08 | No docs pre-commit instructions; exactly one VERIFY marker remains and it is the bandit one | ✓ VERIFIED | Guards pass; `grep "VERIFY:" docs` → exactly `docs/testing.md:242` (bandit marker) |
| 52 | 17-08 | Backstop: doc correctness is asserted by scans, not prose review; an unscanned stale concept can survive | ✓ VERIFIED | Scans exist and pass; the limitation is a true declaration of the method |
| 53 | 17-09 | Seven tracked junk paths removed from the index and working tree; no `MagicMock/` path tracked | ✓ VERIFIED | `git ls-files -- "MagicMock/" quick_test.py simple_test.py verify_imports.py` prints nothing; none exists on disk; `test_tracked_junk_removed` passes non-vacuously |
| 54 | 17-09 | No source/test/example references the junk paths and the committed suite is green | ✓ VERIFIED | Guard's literal list is the only reference; full suite 3233 passed / 1 skipped at `d97838c` |
| 55 | 17-09 | Backstop: only the seven named paths are removed; the repo-wide unknown-junk audit stays deferred | ✓ VERIFIED | `git show --stat 8e4090d` shows exactly the four MagicMock blobs, three scratch scripts, and the guard; unknown-junk audit remains deferred per D-12/CONTEXT |

**Score:** 55/55 truths verified (0 present-but-behavior-unverified; 12 are `verification: backstop` declarations resolved with direct evidence or scope confirmation).

**Version-bump reconciliation.** The v1.2 bump (`d97838c`) is exactly the five covered files listed above plus three uncovered identity manifests (`server.json`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` — all now `"1.2.0"`). `gsd_run query verify.artifacts` on 17-05 flags two artifacts purely on version-suffixed literals the bump legitimately rotated: `src/sif/_version.py` `contains: "1.1.2"` (now holds the single literal `"1.2.0"`; the release-metadata guard pins `== "1.2.0"` and passes) and `tests/test_release_metadata.py` export `test_changelog_has_1_1_2` (retargeted to `test_changelog_has_1_2_0`, present and passing in the 58-test battery). Both are re-verified as satisfied at 1.2.0 per the milestone context — not gaps. `verify.key-links` flags 9 links whose `from` is a component description rather than a relative file path (tool parser limitation, unchanged from the prior pass); each is verified manually above (rows 5/23/28/30/34/36/37/39/42/43).

### Roadmap Success Criteria

| # | Success Criterion | Status | Covering Truth Rows |
|---|-------------------|--------|---------------------|
| 1 | Every push/PR runs the full suite green on py3.10-3.13 × ubuntu/macos — fail_under=90 per cell, CPU torch on Linux, both resolution fleets tolerated | ✓ VERIFIED | 5-18 |
| 2 | A Windows smoke run on hc remote yoga proves fork/systemd/flock degrade honestly — degradation, not full Windows support | ✓ VERIFIED | 19-26 |
| 3 | `docsif` v1.1.x installable from PyPI via trusted publishing — TestPyPI dry run, version single-sourced, PEP 740 attestations, README marker landed before publish | ✓ VERIFIED | 27-47 |
| 4 | Repo is hygienic — dead layers deleted, tracked junk removed, Makefile/extras/pre-commit cleaned, black dropped, fastapi/uvicorn kept; 3.13 classifier only once green | ✓ VERIFIED | 1-10, 32, 48-55 |

### Decision Coverage

All trackable CONTEXT.md decisions are honored by shipped artifacts: **15/15 honored, 0 not honored** (`check.decision-coverage-verify`, non-blocking gate).

### Required Artifacts

`gsd_run query verify.artifacts` reports `all_passed: true` for plans 01-04 and 06-09 (29/29 artifacts); plan 05 reports 6/8, where the two flags are the version-suffixed literals rotated by the 1.2.0 bump (re-verified as satisfied at 1.2.0 — see Version-bump reconciliation). No artifact is a stub or orphan: every newly created module is imported/exercised, and every config/doc change is read by a guard or a live run.

| Artifact | Plan | Expected | Status | Details |
|----------|------|----------|--------|---------|
| `tests/test_hygiene.py` | 01/08/09 | Absence/import/Makefile/doc/junk guards | ✓ VERIFIED | All guards pass in the 58-test battery |
| `src/sif/models/__init__.py` | 01 | Dead search exports removed | ✓ VERIFIED | `__all__` holds only live models |
| `src/sif/database/__init__.py` | 01 | No MigrationManager export | ✓ VERIFIED | `__all__` holds only live repos/helpers |
| `src/sif/search/rrf.py` | 01 | RRFFusion only | ✓ VERIFIED | 43 fusion tests pass |
| `examples/quickstart.py` | 01 | Live API example | ✓ VERIFIED | Compile guard passes |
| `Makefile` | 01/04 | pre-commit-free; windows-smoke target | ✓ VERIFIED | No pre-commit token; `windows-smoke` at `:81` |
| `pyproject.toml` | 02/05 | CPU index/sources/floors; 3.13 classifier | ✓ VERIFIED | `explicit = true` index; Linux-marker torch; classifier at `:24` |
| `uv.lock` | 02 | CPU torch, no CUDA/black | ✓ VERIFIED | 0 nvidia/triton/black; `uv lock --check` exit 0 |
| `tests/test_ci_workflows.py` | 02/03 | Lock/packaging/workflow guards | ✓ VERIFIED | All pass |
| `docs/installation.md` | 02/05 | Extras aligned; version sample | ✓ VERIFIED | `sif, version 1.2.0` sample at `:325`; windows-smoke documented at `:308` |
| `.github/workflows/test-matrix.yml` | 03 | 8-cell matrix + lint job | ✓ VERIFIED | Re-read in full; green run 43561542242 |
| `scripts/windows_smoke.py` | 04 | Degradation smoke with matchers | ✓ VERIFIED | Version read from `_version.py` (holds at 1.2.0); recorded 8/8 PASS |
| `tests/test_windows_smoke_script.py` | 04 | Matcher battery | ✓ VERIFIED | 8 tests pass; fixture literal retargeted to 1.2.0 |
| `src/sif/utils/daemon.py` | 04 | POSIX-fork guard | ✓ VERIFIED | `hasattr(os, "fork")` at `:253` |
| `src/sif/cli/commands/watch.py` | 04 | Detach + win32 service guard | ✓ VERIFIED | Guards at `:359` and `:438-442` |
| `src/sif/_version.py` | 05 | Single-sourced release version | ✓ VERIFIED at 1.2.0 | Single literal `"1.2.0"` (plan's `contains: "1.1.2"` rotated by the bump) |
| `README.md` | 05 | mcp-name marker | ✓ VERIFIED | Exact line 2 |
| `docs/changelog.md` | 05 | Release entry + compare links | ✓ VERIFIED | `[1.2.0]` section + links; `[1.1.2]` retained |
| `tests/test_release_metadata.py` | 05 | Release identity/marker/changelog/workflow guards | ✓ VERIFIED | Pins retargeted to 1.2.0; all pass |
| `.github/workflows/publish.yml` | 05 | Tag-gated build/publish | ✓ VERIFIED | Re-read in full; run 43562577065 success |
| `docs/development.md` | 05/08 | Release Process rewrite; live how-to | ✓ VERIFIED | windows-smoke documented at `:607,705`; New Search Strategy at `:527` |
| `17-06-SUMMARY.md` | 06 | Release-gate evidence | ✓ VERIFIED | Environments, publishers, run id, diff, release_head all re-confirmed live |
| `17-07-SUMMARY.md` | 07 | Published-release evidence | ✓ VERIFIED | Tag/PyPI/install proofs re-confirmed live or by same-day reproduction |
| `tests/test_docs.py` | 08 | `SKIP_COMMAND_PATTERNS` without pre-commit install | ✓ VERIFIED | Doc guards pass |
| `docs/architecture.md`, `docs/models.md`, `docs/api-reference.md`, `DESIGN.md`, `docs/testing.md`, `docs/contributing.md` | 08 | Dead prose removed, live docs kept, one bandit marker | ✓ VERIFIED | Direct greps + guards |
| `tests/test_hygiene.py` junk guard | 09 | `test_tracked_junk_removed` | ✓ VERIFIED | Passes non-vacuously |

### Key Link Verification

20 declared key links. 11 verify directly via `gsd_run query verify.key-links`; the 9 flagged links all fail only because their `from` value is a component description rather than a relative file path (parser limitation) — each was verified manually on the current tree or against live external state:

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/test_hygiene.py` | deleted module paths | rglob text scan + existence assertions | ✓ WIRED | Guard passes; a surviving importer would fail it |
| `src/sif/models/__init__.py` | `sif.models` consumers | `__all__` no dead names | ✓ WIRED | Test asserts disjunction |
| `examples/quickstart.py` | `database.py` / `bm25.py` | `Database`/`BM25Searcher` usage | ✓ WIRED | Compile guard + direct inspection |
| `pyproject.toml [tool.uv.sources]` | `uv.lock` torch entries | marker-scoped CPU index materialized | ✓ WIRED (manual) | `+cpu` entries + explicit index re-read this round |
| `tests/test_ci_workflows.py` | `uv.lock` + `pyproject.toml` | text-level guards | ✓ WIRED | 18 guards pass |
| `test-matrix.yml` | `uv.lock` | `cache-dependency-glob` + `uv sync --frozen` | ✓ WIRED | Workflow text + green run |
| `test-matrix.yml` | pyproject pytest/coverage config | bare pytest inherits addopts/fail_under | ✓ WIRED | No `--no-cov`; `fail_under = 90` at `pyproject.toml:229` |
| `Makefile windows-smoke` | `scripts/windows_smoke.py` on yoga | `hc exec --on yoga … uv run --frozen` | ✓ WIRED (manual) | Target text + recorded 8/8 PASS run |
| `watch.py` | `utils/daemon.py` | library guard before `detach()` | ✓ WIRED | Both guards re-read at `:359` / `:253` |
| `tests/test_windows_smoke_script.py` | `scripts/windows_smoke.py` | direct matcher imports | ✓ WIRED | Tests pass |
| `README.md marker` | PyPI project description | hatchling reads README | ✓ WIRED (manual) | Live PyPI JSON contains the marker (re-fetched) |
| `publish.yml build job` | `src/sif/_version.py` | `runpy` + `GITHUB_REF_NAME` gate | ✓ WIRED (manual) | Gate re-read in workflow text; version-agnostic at 1.2.0 |
| `publish.yml publish jobs` | environments `pypi`/`testpypi` | environment-scoped OIDC | ✓ WIRED (manual) | Environment blocks + both envs exist (live API) |
| `publish.yml environments` | GitHub environments + publisher registration | exact identity fields | ✓ WIRED (manual) | Provenance records `publish.yml` + `pypi`; publish succeeded |
| `17-04-SUMMARY smoke HEAD` | release HEAD | `git diff -- src/sif` limited to `_version.py` | ✓ WIRED (manual) | Diff re-run this round: exactly `src/sif/_version.py` |
| `tag v1.1.2` | `publish.yml` | tag push is the only trigger | ✓ WIRED (manual) | Tag peels to `c819f67` (live ls-remote); `tags: ['v*']` trigger |
| `PyPI artifact` | MCP Registry ownership marker | `info.description` contains marker | ✓ WIRED (manual) | Fresh PyPI JSON check |
| `tests/test_hygiene.py` | docs + DESIGN.md | dead literal + VERIFY scans | ✓ WIRED | Guards pass; direct grep confirms |
| `docs/development.md` | `src/sif/search/` + `sif.core.models` | live searcher how-to | ✓ WIRED | Section verified |
| `tests/test_hygiene.py` | git index | `git ls-files` + sentinel | ✓ WIRED | Guard passes non-vacuously |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `src/sif/_version.py` | `__version__` | single literal → hatchling wheel METADATA → PyPI JSON → installed CLI | Yes: PyPI serves 1.1.2 (installed CLI prints it); local tree prints `1.2.0` through the same path | ✓ FLOWING |
| `README.md` | PyPI `info.description` | hatchling `readme = "README.md"` at build time | Yes: marker present in live PyPI JSON | ✓ FLOWING |
| `uv.lock` | torch resolution | explicit CPU index + Linux marker | Yes: `+cpu` entries; 8-cell matrix green | ✓ FLOWING |
| `scripts/windows_smoke.py` | CLI outputs | temp `SIF_DB_PATH` SQLite DB → CLI stdout/stderr → matchers | Yes: recorded run produced all PASS lines | ✓ FLOWING |
| `publish.yml` build job | dist artifact | `uv build` → upload-artifact → both publish jobs | Yes: identical file sizes on both indexes | ✓ FLOWING |
| render surfaces | — | none introduced by this phase | N/A | N/A |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Phase guard battery (58 guards incl. 1.2.0 release pins) | `pytest tests/test_hygiene.py tests/test_ci_workflows.py tests/test_release_metadata.py tests/test_windows_smoke_script.py tests/test_version_identity.py -q --no-cov` | 58 passed in 1.16 s | ✓ PASS |
| Watch/daemon guards (behavior-dependent truths 19/20) | `pytest tests/unit/cli/test_watch_cmd.py::TestDaemonFlagGuards tests/unit/utils/test_daemon.py -q --no-cov` | 45 passed in 0.19 s | ✓ PASS |
| RRF fusion behavior | `pytest tests/unit/search/test_rrf.py -q --no-cov` | 43 passed | ✓ PASS |
| Lock freshness | `uv lock --check` | exit 0, Resolved 106 packages | ✓ PASS |
| Local version surface | `python -m sif.cli.main --version` | `sif, version 1.2.0` | ✓ PASS |
| Repo gates | `ruff check src tests` / `ruff format --check src tests` / `ty check src/sif` | All clean / 236 files formatted / All checks passed | ✓ PASS |
| Full regression gate | (not re-run by policy) | 3233 passed / 1 skipped @ 95.03% coverage at `d97838c` (run by the bump quick task; no task commits since) | ✓ PASS (fresh cited evidence) |
| PyPI install (fresh venv) | `uv venv /tmp/sif-verif-regen-17` + `uv pip install docsif==1.1.2` → `sif --version` | `sif, version 1.1.2` | ✓ PASS |
| PyPI JSON | `curl https://pypi.org/pypi/docsif/1.1.2/json` | version 1.1.2; marker present; 220225/3108000 | ✓ PASS |
| TestPyPI JSON/install | re-fetch blocked (transient sandbox DNS for `test.pypi.org`) | same-day independent reproduction at 2026-11-18T03:37Z; immutable index | ✓ PASS (recorded) |
| Windows degradation smoke | recorded `make windows-smoke` (hc yoga, clean checkout at `48759e2`) | 8/8 PASS at `48759e2` (recorded; yoga unreachable this round) | ✓ PASS (recorded) |
| Test Matrix on release HEAD | `gh run view 43561542242` | conclusion success; headSha `c819f67`; 9/9 jobs success | ✓ PASS |
| Publish workflow | `gh run view 43562577065` | conclusion success; Build, TestPyPI, PyPI all success | ✓ PASS |
| Release tag | `git ls-remote --tags origin v1.1.2 'v1.1.2^{}'` | `v1.1.2` peels to `c819f672…` on origin | ✓ PASS |
| GitHub environments | `gh api repos/zhangtaolab/sif/environments` | `pypi` (27264851535) + `testpypi` (27264859642) | ✓ PASS |
| Classifier-after-green ordering | `git merge-base --is-ancestor f6092f8 9164e4f` | yes (green run commit precedes classifier commit) | ✓ PASS |

### Probe Execution

None applicable. No probe scripts are declared or conventionally present (`find scripts -path '*/tests/probe-*.sh'` returns nothing; no probe reference appears in any phase PLAN/SUMMARY). The smoke script is exercised through `make windows-smoke`; its recorded run is listed above.

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|----------------|-------------|--------|----------|
| ENG-01 | 17-02, 17-03, 17-05 | Full suite green on py3.10-3.13 × ubuntu/macos, fail_under=90 per cell, CPU torch on Linux, both resolution fleets tolerated, on every push/PR | ✓ SATISFIED | 8-cell workflow + lint job; run 43561542242 green on `c819f67` (live read); CPU torch in lock; guards forbid `--no-cov` and version pinning |
| ENG-02 | 17-04, 17-05 | Windows degradation verified by a CI smoke on hc remote yoga (uv python install first; fork/systemd/flock degrade honestly) | ✓ SATISFIED | Guards + committed smoke + unit battery (45 green) + Makefile target; recorded 8/8 PASS at `48759e2`; docs document the on-demand step |
| ENG-03 | 17-05, 17-06, 17-07 | Maintainer can publish docsif to PyPI via trusted publishing (marker before publish, TestPyPI dry run, version single-sourced, PEP 740 attestations) | ✓ SATISFIED | PyPI + TestPyPI serve 1.1.2; marker in `info.description` (live); fresh venv installs from PyPI re-executed; tag on release_head; single-sourcing now at 1.2.0 with guards |
| ENG-04 | 17-01, 17-02, 17-05, 17-08, 17-09 | Hygienic repo: dead layers deleted, tracked junk removed, Makefile/extras/pre-commit cleaned, black dropped, fastapi/uvicorn kept, 3.13 classifier only when green | ✓ SATISFIED | All deletions/guards verified on the current tree; 0 junk tracked; no pre-commit/black tokens; core deps intact; classifier present after green run |

No orphaned requirements: `REQUIREMENTS.md` maps exactly ENG-01..ENG-04 to Phase 17 (lines 15-18, traceability table lines 132-135 all Complete), every ID is claimed by at least one plan's `requirements:` frontmatter, and no requirement mapped to Phase 17 is unclaimed.

### Prohibitions (must-NOT checks)

All 14 plan-declared prohibitions re-evaluated against the current tree and live evidence; each satisfied (plans' frontmatter still carries `status: unresolved` — planner bookkeeping, not a violation):

| Plan | Prohibition | Status | Evidence |
|------|-------------|--------|----------|
| 17-01 | MUST NOT delete code on a runtime path | ✓ SATISFIED | Deletions limited to the three verified-dead modules, the orphan RRF function, and their tests; full suite green at `d97838c`; no surviving importer |
| 17-01 | MUST NOT leave examples/Makefile describing deleted layers or phantom pre-commit | ✓ SATISFIED | Compile guard + `test_makefile_has_no_pre_commit_target`; dead-literal greps clean |
| 17-02 | MUST NOT add a package or trust a third-party index beyond the explicit CPU index | ✓ SATISFIED | Single `explicit = true` index serving torch only, marker-scoped |
| 17-03 | MUST NOT weaken the coverage gate to make the matrix green | ✓ SATISFIED | `fail_under = 90` unchanged (`pyproject.toml:229`); no `--no-cov` in workflow; 8 cells intact |
| 17-04 | MUST NOT present the smoke as full Windows support | ✓ SATISFIED | `docs/development.md:607` degradation-only; WIN-F1 deferred |
| 17-04 | MUST NOT touch the user's real index, collections, or model cache on yoga | ✓ SATISFIED | Temp `SIF_DB_PATH`; BM25-only argv; script unchanged since the recorded run |
| 17-05 | MUST NOT publish a release without the mcp-name marker | ✓ SATISFIED | Published 1.1.2 `info.description` contains the exact marker (live) |
| 17-05 | MUST NOT publish from a mismatched tag or a red matrix | ✓ SATISFIED | Tag gate in build job; run 43561542242 green on `c819f67`; tag peels to `c819f67` |
| 17-06 | MUST NOT weaken publisher identity or disable OIDC | ✓ SATISFIED | Workflow uses `publish.yml` + environments `pypi`/`testpypi` + job-scoped `id-token: write`; successful OIDC publish |
| 17-07 | MUST NOT rebuild in publish jobs or re-upload under a mutated version | ✓ SATISFIED | No `uv build` in publish jobs; both download artifact `dist`; identical published sizes |
| 17-07 | MUST NOT reuse credentials/environment between TestPyPI and PyPI | ✓ SATISFIED | Separate jobs, separate environments, separate repository URLs; no secrets anywhere |
| 17-08 | MUST NOT delete documentation of live layers | ✓ SATISFIED | Live models/protocols present in `docs/models.md` and `docs/api-reference.md` (re-grepped) |
| 17-08 | MUST NOT hand-edit generator-owned `docs/cli-reference.md` / `docs/configuration.md` | ✓ SATISFIED | `.github/workflows/docs.yml` regenerates and fails on `git diff --exit-code`; neither file is in the phase's changed set |
| 17-09 | MUST NOT remove any path not on the seven-path verified list | ✓ SATISFIED | `git show --stat 8e4090d`: exactly the seven junk paths plus the guard file |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/placeholder prose in the covered implementation files (re-scanned this round, including the five bump-touched files) | ℹ️ Info | Debt-marker gate clean |
| `.github/workflows/publish.yml` | publish jobs | `timeout-minutes` present only on the build job (`:14`); publish jobs lack it (WR-06); no concurrency guard (WR-07) | ℹ️ Info — open review findings, user-accepted | Plan 17-05 must-have requires build-once/tag-gate/OIDC, not these hardening items |
| `Makefile`/`index.py` etc. | — | WR-09, IN-01..IN-06 remain open by explicit user decision (11 findings total) | ℹ️ Info — accepted | None contradicts a plan must-have; the five fixed findings are present in `b0d45bf` |
| `docs/testing.md`, `docs/development.md` | — | WR-02/WR-03 stale prose was reconciled upstream by the phase-24 doc regeneration | ℹ️ Info — resolved | No must-have impact |

### Advisory (New Scope, Unevidenced)

None. The re-verification scan produced no new-scope findings beyond the user-accepted review residuals already recorded above.

### Human Verification Required

N/A — Infrastructure/foundation phase with no user-facing elements. All acceptance criteria are verifiable programmatically, and all external-service claims were re-read live from GitHub/PyPI or rest on same-day independent reproduction of immutable artifacts (TestPyPI install, PEP 740 attestation) plus the recorded Windows smoke run (yoga unreachable, desktop-session SSH refusal). No ⚠️ PRESENT_BEHAVIOR_UNVERIFIED truths: every behavior-dependent invariant (fork/service refusals, smoke matchers, RRF fusion) is exercised by a green named-test battery re-run in this verification.

### Gaps Summary

No gaps. The phase goal is achieved in the codebase and on the external services it names, holding at the post-bump version:

- **Green regression net:** `.github/workflows/test-matrix.yml` declares a fixed 8-cell matrix (py3.10-3.13 × ubuntu/macos) plus a py3.12 ruff/format/ty lint job, least-privilege and secret-free, and Test Matrix run 43561542242 is green on the release HEAD `c819f67` (8 py cells + lint, live API read). Bare pytest inherits `--cov` addopts and `fail_under=90` per cell.
- **Proven release pipeline / docsif on PyPI:** tag `v1.1.2` peels to the gate-verified `c819f67` (live ls-remote); Publish run 43562577065 completed `success` (build reused, TestPyPI, PyPI — live API read); PyPI serves 1.1.2 with the mcp-name marker (live fetch); a fresh venv installs it today. The version single-sourcing mechanism the phase built now carries 1.2.0 end-to-end (`_version.py` literal → version-identity battery → release-metadata guards → tag gate → docs sample → server.json), verified green at the new version.
- **Windows degradation:** the guards, committed smoke, unit battery (45 green), and Makefile target all exist; the recorded independent run on yoga returned 8/8 PASS at HEAD `48759e2`. The yoga host remains unreachable (unchanged from the prior re-check), and the script is unchanged since the recorded run.
- **Hygiene:** the three dead layers, orphan RRF export, `CURRENT_SCHEMA_VERSION`, phantom pre-commit flow, black, and seven tracked junk paths are gone, with guards re-run green; live-layer docs survive; exactly one docs VERIFY marker (bandit) remains.

Accepted residuals (not must-have gaps): 11 lower-severity review findings remain open by explicit user decision (including WR-06 publish-job timeouts / WR-07 concurrency guard). None contradicts any plan `must_haves`; the scope is locked by the phase CONTEXT decisions.

---

_Verified: 2026-11-18T09:59:10Z_
_Verifier: Claude (gsd-verifier)_
