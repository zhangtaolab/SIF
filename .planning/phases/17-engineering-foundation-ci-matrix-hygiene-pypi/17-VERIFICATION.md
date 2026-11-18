---
phase: 17-engineering-foundation-ci-matrix-hygiene-pypi
verified: 2026-11-18T03:37:14Z
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
covered_digest: "v4:sha256:2953eb8b96c8c6e5b7f05da2ddbd601734d22e4fa7b325c5b6b3654e01d19278"
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
**Verified:** 2026-11-18T03:37:14Z
**Status:** passed
**Re-verification:** Yes — full re-verification. The previous 17-VERIFICATION.md (2026-11-14) was stale: covered source files changed after it was written, so every must-have was re-checked against the current tree and every external result was re-fetched live.

## Goal Achievement

55 must-have truths (43 outcome truths + 12 `verification: backstop` scope/residual declarations). Each row was checked against the current codebase or an independently reproduced external result, not against SUMMARY prose. Full suite: **3233 passed, 1 skipped** (exit 0, 130.68 s); phase guard battery: **58 passed**; watch/daemon guard battery: **45 passed**; `uv lock --check` exit 0; ruff/format/ty clean.

### Observable Truths

| # | Plan | Truth | Status | Evidence |
|---|------|-------|--------|----------|
| 1 | 17-01 | Three dead layers (`models/search.py`, `search/strategy.py`, `database/migrations.py`) deleted with no surviving importer; suite collects and passes | ✓ VERIFIED | All three files absent; `grep -rn "sif\.models\.search\|sif\.search\.strategy\|MigrationManager" src tests examples` returns nothing outside the guard's own literals; `tests/test_hygiene.py` guards pass; full suite 3233 passed, 1 skipped |
| 2 | 17-01 | Orphan `compute_rrf_score` removed while `RRFFusion` fusion behavior is byte-identical | ✓ VERIFIED | `git show 4f6506f -- src/sif/search/rrf.py` deletes only the standalone function; the `RRFFusion` class body is untouched; `tests/unit/search/test_rrf.py` 43 passed |
| 3 | 17-01 | Makefile has no pre-commit target/install/autoupdate; `.pre-commit-config.yaml` absent | ✓ VERIFIED | `grep pre-commit Makefile` → no match (only absent from `.PHONY` too); config file absent; `test_makefile_has_no_pre_commit_target` and `test_pre_commit_config_absent` pass |
| 4 | 17-01 | Backstop: docs sweep, tracked-junk removal, and repo-wide zero-reference scan are out of this plan's scope | ✓ VERIFIED (scope honored) | 17-08 and 17-09 are verified below; the repo-wide unknown-junk/zero-reference scan remains deferred per D-09/D-12 |
| 5 | 17-02 | `uv.lock` resolves CPU-tagged torch from `download.pytorch.org/whl/cpu` on Linux, keeps a PyPI torch for macOS/Windows, contains no nvidia-*/triton | ✓ VERIFIED | CPU entries `2.14.1+cpu` (py<3.11) / `2.15.0+cpu` (py>=3.11); PyPI entries `2.14.1`/`2.15.0` for `sys_platform != 'linux'`; `grep -c nvidia` = 0, `triton` = 0 |
| 6 | 17-02 | No black dev dependency, no `[tool.black]`, no black in the lock | ✓ VERIFIED | `pyproject.toml` dev extra has no black; no `[tool.black]`; 0 `name = "black"` entries in `uv.lock`; `test_lock_has_no_black` and `test_pyproject_has_no_black_section` pass |
| 7 | 17-02 | embed/all floor sentence-transformers >=5.4.1 and declare torch directly; all floors llama-cpp-python >=0.3.35; fastapi/uvicorn stay core | ✓ VERIFIED | `pyproject.toml:54,72-74`; `fastapi>=0.100.0`/`uvicorn>=0.20.0` in core deps; `test_pyproject_extras_floors` and `test_core_deps_keep_fastapi_uvicorn` pass |
| 8 | 17-02 | `pytorch-cpu` index is `explicit = true`; torch source marker-scoped to `sys_platform == 'linux'` | ✓ VERIFIED | `pyproject.toml:95-101`; single `[[tool.uv.index]]` entry, referenced only by the torch source; `test_pyproject_cpu_index_is_explicit` passes |
| 9 | 17-02 | `uv lock --check` exits 0 on the committed lock | ✓ VERIFIED | Exit 0, "Resolved 106 packages" (lock grew in later phases; freshness is the claim) |
| 10 | 17-02 | Backstop: fleet tolerance asserted structurally; actual per-fleet resolution proven only by the 8-cell matrix | ✓ VERIFIED | Guards assert structure (a `+cpu` torch, a PyPI torch, no CUDA stack), never exact transitive versions; run 43561542242 green across all 8 cells |
| 11 | 17-03 | Every branch push and pull_request runs exactly 8 cells (3.10-3.13 × ubuntu/macos) with `fail-fast: false` | ✓ VERIFIED | `test-matrix.yml:3-6,20-24`; run 43561542242 reports exactly 8 `py*` jobs plus lint, all success |
| 12 | 17-03 | Each cell runs bare pytest (no `--no-cov`) and syncs `uv sync --frozen --extra dev --extra embed` | ✓ VERIFIED | `test-matrix.yml:41-44`; `grep --no-cov` absent; `test_matrix_runs_full_suite_with_coverage` passes; pyproject addopts + `fail_under=90` apply |
| 13 | 17-03 | Workflow-level `contents: read`, `pull_request` (not `pull_request_target`), no secrets, setup-uv SHA-pinned | ✓ VERIFIED | `test-matrix.yml:6-9,30`; SHA `68559e99cc807c1eb7e9238fd43a15bba460eec2`; `test_matrix_has_least_privilege` and `test_setup_uv_is_sha_pinned` pass |
| 14 | 17-03 | Per-ref concurrency with `cancel-in-progress: true`; tag pushes excluded | ✓ VERIFIED | `test-matrix.yml:11-13`; push trigger declares `branches: ['**']`, no `tags:`; guard passes |
| 15 | 17-03 | One lint/type job on ubuntu-latest/py3.12 runs `ruff check src tests`, `ruff format --check src tests`, `ty check src/sif` | ✓ VERIFIED | `test-matrix.yml:46-74`; run 43561542242 lint job success; `test_lint_job_runs_repo_gates` passes; local ruff/format/ty all clean |
| 16 | 17-03 | The workflow run for the phase HEAD is green on 8 cells + lint | ✓ VERIFIED | `gh run view 43561542242`: headSha `c819f67`, conclusion `success`, 8 `py*` jobs + 1 lint job all `success` |
| 17 | 17-03 | Backstop: matrix is a fixed literal list; an empty/dynamic/partial matrix is not guard-exercised | ✓ VERIFIED | Literal `os` × `python-version` lists present; the observed run shows 8 distinct cells, covering the residual concern |
| 18 | 17-03 | Backstop: 8 cells compare equal in outcome; only the aggregate is asserted | ✓ VERIFIED | All 8 cell conclusions are `success`; no ordering contract is asserted or required |
| 19 | 17-04 | Detach on a platform without `os.fork` exits non-zero naming POSIX fork + foreground remedy, never a raw AttributeError | ✓ VERIFIED | `daemon.py:253-258` RuntimeError guard; `watch.py:361-366` ClickException guard; `test_detach_requires_fork` + `test_detach_without_fork_is_refused` pass (45-test daemon/watch battery) |
| 20 | 17-04 | Windows install/uninstall-service refuse with a Windows-specific message before any systemctl probe | ✓ VERIFIED | `_service_manager()` win32 guard (`watch.py:438-442`) is the shared site for both commands; `test_windows_refuses_the_service_with_the_foreground_remedy` passes |
| 21 | 17-04 | Smoke uses explicit argv lists (never a shell), temp `SIF_DB_PATH`, and no query/vsearch/embed model-loading command | ✓ VERIFIED | `scripts/windows_smoke.py:65-84,92-102,285-289`; `build_cli_invocations` uses `search search`; temp dir env; `test_commands_are_argv_lists_without_model_loading` passes |
| 22 | 17-04 | Smoke asserts version, collection add, index update Added:1 + fcntl warning, BM25 JSON result, status, Removed:0 + preserved warning, detach/service refusals | ✓ VERIFIED | Assertion table `scripts/windows_smoke.py:157-243`; matcher battery 8 tests green; recorded live run printed all 8 PASS lines |
| 23 | 17-04 | `make windows-smoke` runs HEAD/dirty preflight, `uv python install`, frozen sync, and the smoke over `hc exec` | ✓ VERIFIED | `Makefile:81-87`; target executed end-to-end in the phase run; preflight prints HEAD and refuses a dirty tree |
| 24 | 17-04 | Smoke completes green on the synced yoga checkout and records the tested git HEAD | ✓ VERIFIED | Recorded run at HEAD `48759e2c532d01d92a0deef08520a58c41115378`: 8/8 PASS, final "PASS all assertions"; previously independently reproduced by the 2026-11-14 verifier. The yoga host was **unreachable at this re-check** (`hc ls`: "cannot reach Yoga"), so this run did not re-execute the remote smoke; the committed script/matchers and their unit tests were re-verified locally |
| 25 | 17-04 | Backstop: smoke is not evidence of full Windows support; parity deferred to v2 | ✓ VERIFIED | Script docstring, docs/installation.md and docs/development.md state degradation-only; WIN-F1 remains deferred |
| 26 | 17-04 | Backstop: yoga sync is a human step; script refuses a dirty tree and prints HEAD | ✓ VERIFIED | `_preflight_head()` prints HEAD and returns 1 on dirty output (`scripts/windows_smoke.py:118-135`); `git status --porcelain` gate present |
| 27 | 17-05 | `_version.py` holds the single literal 1.1.2 and all runtime surfaces derive it | ✓ VERIFIED | `src/sif/_version.py` single literal; `tests/test_version_identity.py` 4 tests pass (asserts `sif.__version__`, `sif._version.__version__`, `sif.cli.__version__`, `APP_VERSION`, MCP `serverInfo`); local `python -m sif.cli.main --version` → `sif, version 1.1.2` |
| 28 | 17-05 | README contains the exact mcp-name marker line before the tag; PyPI description derives from README | ✓ VERIFIED | `README.md:2` exact line on its own line; hatchling `readme = "README.md"`; live PyPI JSON `info.description` contains the marker |
| 29 | 17-05 | Changelog has a 1.1.2 section and footer link; `[Unreleased]` compares `v1.1.2...HEAD` | ✓ VERIFIED | `docs/changelog.md:38,243,245`; `test_changelog_has_1_1_2` passes |
| 30 | 17-05 | `publish.yml` is v*-tag-gated, builds once on ubuntu with `contents: read`, gates `GITHUB_REF_NAME` against `_version.py`, uploads dist, then TestPyPI → PyPI with job-scoped OIDC and environments | ✓ VERIFIED | `publish.yml:4-5,10-48,50-89`; all workflow guards pass; Publish run 43562577065 succeeded through this exact path |
| 31 | 17-05 | PyPI publish has no `skip-existing`; both publish jobs consume the same dist artifact; attestations stay at the trusted-publishing default | ✓ VERIFIED | Workflow text: `skip-existing` only on TestPyPI; both jobs use `download-artifact@v8 name: dist`, no `uv build`; published wheel/sdist sizes identical on both indexes (220225/3108000); live attestation verifies |
| 32 | 17-05 | 3.13 classifier appears only after a green matrix | ✓ VERIFIED | `pyproject.toml:24` after 3.12; green run 43399300651 (`f6092f8`, success) predates classifier commit `9164e4f` (`git merge-base --is-ancestor f6092f8 9164e4f` → YES) |
| 33 | 17-05 | Release Process and installation docs document `make windows-smoke`; no `twine upload` primary path | ✓ VERIFIED | `docs/development.md:607,705`; `docs/installation.md:308`; `grep "twine upload" docs` empty; `test_release_process_docs_name_the_workflow` and `test_windows_smoke_is_documented` pass |
| 34 | 17-05 | Backstop: tag/version equality is exact ASCII string equality | ✓ VERIFIED | Build job runs `test "v${VERSION}" = "${GITHUB_REF_NAME}"` (`publish.yml:31-35`) |
| 35 | 17-05 | Backstop: mcp-name marker must match future server.json byte-for-byte and sit on a line boundary; Registry check is Phase 22 | ✓ VERIFIED (Phase 22 portion deferred) | Marker is one complete README line, no trailing period; `test_readme_has_mcp_name_marker` asserts the exact line; Registry ownership check is Phase 22 scope |
| 36 | 17-06 | GitHub environments `pypi` and `testpypi` exist | ✓ VERIFIED | `gh api repos/zhangtaolab/sif/environments`: `pypi` id 27264851535, `testpypi` id 27264859642 |
| 37 | 17-06 | Maintainer registered the PyPI trusted publisher and TestPyPI pending publisher with the exact identity fields | ✓ VERIFIED (end-to-end) | Signed provenance publisher record: kind GitHub, repository `zhangtaolab/SIF`, workflow `publish.yml`, environment `pypi`; Publish run 43562577065 published to both indexes (TestPyPI pending publisher proven by the successful first publish) |
| 38 | 17-06 | The Test Matrix run for the release HEAD is green across 8 cells + lint | ✓ VERIFIED | Run 43561542242 on `c819f67`: 9/9 jobs success |
| 39 | 17-06 | No runtime source changed between the smoke commit and the release HEAD except `src/sif/_version.py` | ✓ VERIFIED | `git diff --name-only 48759e2..c819f67 -- src/sif` prints exactly `src/sif/_version.py` |
| 40 | 17-06 | 3.13 classifier, README marker, 1.1.2 literal, changelog, and publish workflow all present at release HEAD | ✓ VERIFIED | `git show c819f67:<path>` confirms each artifact at the tagged commit |
| 41 | 17-06 | Backstop: publisher registration is not readable via public API; a successful OIDC publish is the only end-to-end proof | ✓ VERIFIED | Publish run 43562577065 attempt 4: Build, TestPyPI, and PyPI all success |
| 42 | 17-07 | Tag v1.1.2 exists and the Publish run has build + publish-testpypi + publish-pypi all successful | ✓ VERIFIED | Local and remote tag peel to `c819f67`; `gh run view 43562577065`: attempt 4, conclusion success, 3/3 jobs success |
| 43 | 17-07 | PyPI serves docsif 1.1.2 with the exact mcp-name marker in `info.description` | ✓ VERIFIED | Fresh `curl https://pypi.org/pypi/docsif/1.1.2/json`: version 1.1.2, marker present, files 220225/3108000 bytes |
| 44 | 17-07 | PEP 740 attestations verify for 1.1.2 against the repository | ✓ VERIFIED | Downloaded the published wheel and ran `uvx pypi-attestations verify pypi --repository https://github.com/zhangtaolab/SIF docsif-1.1.2-py3-none-any.whl` → `OK: docsif-1.1.2-py3-none-any.whl`, exit 0. The plan's lowercase URL fails only on pypi-attestations' case-sensitive comparison; signed provenance records the canonical `zhangtaolab/SIF` |
| 45 | 17-07 | A fresh venv installs docsif==1.1.2 from PyPI and reports `sif, version 1.1.2` | ✓ VERIFIED | Fresh `uv venv /tmp/sif-verif-pypi-17` + `uv pip install docsif==1.1.2` → `sif, version 1.1.2` |
| 46 | 17-07 | A fresh venv installs docsif==1.1.2 from TestPyPI (with the PyPI extra index) and reports the same | ✓ VERIFIED | Fresh `uv venv /tmp/sif-verif-testpypi-17`, TestPyPI index + PyPI extra index → `sif, version 1.1.2`; TestPyPI JSON serves 1.1.2 with identical sizes |
| 47 | 17-07 | Backstop: PyPI versions are immutable, so a partial upload requires a new patch version | ✓ VERIFIED | No partial upload occurred; attempts 1-3 failed at OIDC mint before upload; attempt 4 published 1.1.2 completely; version legitimately consumed by success |
| 48 | 17-08 | No non-changelog doc or DESIGN.md names a deleted layer/export, a bare `migrations.py`/`strategy.py` tree entry, or the "legacy migration module" phrase | ✓ VERIFIED | `test_docs_do_not_describe_dead_layers` passes; direct grep over `docs/*.md` + `DESIGN.md` (changelog excluded) for the full literal list returns nothing |
| 49 | 17-08 | Live-layer documentation survives (core SearchOptions/SearchResult/SearchType, Chunker ABC, Embedder/Reranker/QueryExpander) | ✓ VERIFIED | `docs/models.md:175-264`, `docs/api-reference.md:593,766,825`; `test_docs_do_not_describe_dead_layers` covers only dead literals, and the live names are present |
| 50 | 17-08 | `docs/development.md` "New Search Strategy" describes the live extension path with no ABC and no `search_batch` | ✓ VERIFIED | `docs/development.md` section "New Search Strategy" uses `sif.core.models` + `HybridSearcher`/`SearchPipeline`; `grep search_batch docs` empty |
| 51 | 17-08 | No docs pre-commit instructions; exactly one VERIFY marker remains and it is the bandit one | ✓ VERIFIED | `test_docs_do_not_mention_pre_commit_target` / `test_pre_commit_verify_markers_cleared` pass; `grep "VERIFY:" docs` → exactly `docs/testing.md:242` bandit marker; the only `make pre-commit` text in docs is the changelog's removal note (excluded) |
| 52 | 17-08 | Backstop: doc correctness is asserted by scans, not prose review; an unscanned stale concept can survive | ✓ VERIFIED | Scans exist and pass; the limitation is a true declaration of the method |
| 53 | 17-09 | Seven tracked junk paths removed from the index and working tree; no `MagicMock/` path tracked | ✓ VERIFIED | `git ls-files -- MagicMock quick_test.py simple_test.py verify_imports.py` prints nothing; none exists on disk; commit `8e4090d` changes exactly those seven paths plus the guard; `test_tracked_junk_removed` passes non-vacuously |
| 54 | 17-09 | No source/test/example references the junk paths and the committed suite is green | ✓ VERIFIED | `git grep quick_test/simple_test/verify_imports` outside planning finds only the guard's own literal list; full suite 3233 passed, 1 skipped |
| 55 | 17-09 | Backstop: only the seven named paths are removed; the repo-wide unknown-junk audit stays deferred | ✓ VERIFIED | `git show --stat 8e4090d` shows exactly the four MagicMock blobs, three scratch scripts, and the guard file; no other path removed; unknown-junk audit remains deferred per D-12/CONTEXT |

**Score:** 55/55 truths verified (0 present-but-behavior-unverified; 12 are `verification: backstop` declarations resolved with direct evidence or scope confirmation).

### Roadmap Success Criteria

| # | Success Criterion | Status | Covering Truth Rows |
|---|-------------------|--------|---------------------|
| 1 | Every push/PR runs the full suite green on py3.10-3.13 × ubuntu/macos — fail_under=90 per cell, CPU torch on Linux, both resolution fleets tolerated | ✓ VERIFIED | 5-18 |
| 2 | A Windows smoke run on hc remote yoga proves fork/systemd/flock degrade honestly — degradation, not full Windows support | ✓ VERIFIED | 19-26 |
| 3 | `docsif` v1.1.x installable from PyPI via trusted publishing — TestPyPI dry run, version single-sourced, PEP 740 attestations, README marker landed before publish | ✓ VERIFIED | 27-47 |
| 4 | Repo is hygienic — dead layers deleted, tracked junk removed, Makefile/extras/pre-commit cleaned, black dropped, fastapi/uvicorn kept; 3.13 classifier only once green | ✓ VERIFIED | 1-10, 32, 48-55 |

### Deferred Items

None from Step 9b — no gaps were found, so nothing needed filtering against later milestone phases. Out-of-scope residuals recorded in `deferred-items.md` (WR-03 stale test-helper references) have since been reconciled by the phase-24 documentation regeneration; the remaining open review findings are recorded under Anti-Patterns.

### Required Artifacts

`gsd_run query verify.artifacts` reports `all_passed: true` for all nine plans (37/37 artifacts exist and pass). No artifact is a stub or orphan: every newly created module is imported/exercised, and every config/doc change is read by a guard or a live run.

| Artifact | Plan | Expected | Status | Details |
|----------|------|----------|--------|---------|
| `tests/test_hygiene.py` | 01 | Absence/import/Makefile guards | ✓ VERIFIED | 15 guards; all pass |
| `src/sif/models/__init__.py` | 01 | Dead search exports removed | ✓ VERIFIED | `__all__` holds only live models |
| `src/sif/database/__init__.py` | 01 | No MigrationManager export | ✓ VERIFIED | `__all__` holds only live repos/helpers |
| `src/sif/search/rrf.py` | 01 | RRFFusion only | ✓ VERIFIED | `class RRFFusion`; no `compute_rrf_score` |
| `examples/quickstart.py` | 01 | Live API example | ✓ VERIFIED | Compiles under the guard; targets `Database`/`BM25Searcher` |
| `Makefile` | 01 | pre-commit-free target set | ✓ VERIFIED | No pre-commit token; windows-smoke present |
| `pyproject.toml` | 02 | CPU index/sources/floors | ✓ VERIFIED | `[[tool.uv.index]]` explicit; Linux-marker torch; floors correct |
| `uv.lock` | 02 | CPU torch, no CUDA/black | ✓ VERIFIED | 0 nvidia/triton/black; `+cpu` entries; `uv lock --check` exit 0 |
| `tests/test_ci_workflows.py` | 02 | Lock/packaging guards | ✓ VERIFIED | 18 guards; all pass |
| `docs/installation.md` | 02 | Extras aligned | ✓ VERIFIED | Floors/torch match pyproject; `test_installation_docs_match_extras` passes |
| `.github/workflows/test-matrix.yml` | 03 | 8-cell matrix + lint job | ✓ VERIFIED | 8 cells; lint job; green run 43561542242 |
| `tests/test_ci_workflows.py` | 03 | Workflow guards | ✓ VERIFIED | Workflow guards pass |
| `scripts/windows_smoke.py` | 04 | Degradation smoke with matchers | ✓ VERIFIED | 8-step table; matchers unit-tested; recorded 8/8 PASS |
| `tests/test_windows_smoke_script.py` | 04 | Matcher battery | ✓ VERIFIED | 8 tests; all pass |
| `src/sif/utils/daemon.py` | 04 | POSIX-fork guard | ✓ VERIFIED | `hasattr(os, "fork")` at `detach()` |
| `src/sif/cli/commands/watch.py` | 04 | Detach + win32 service guard | ✓ VERIFIED | Both guards present before probes |
| `Makefile` | 04 | windows-smoke target | ✓ VERIFIED | `hc exec --on yoga` recipe |
| `src/sif/_version.py` | 05 | 1.1.2 literal | ✓ VERIFIED | Single literal |
| `README.md` | 05 | mcp-name marker | ✓ VERIFIED | Exact line 2 |
| `docs/changelog.md` | 05 | 1.1.2 section + links | ✓ VERIFIED | Section + footer links |
| `tests/test_release_metadata.py` | 05 | Release/workflow guards | ✓ VERIFIED | 13 guards; all pass |
| `.github/workflows/publish.yml` | 05 | Tag-gated build/publish | ✓ VERIFIED | 3 jobs; TestPyPI then PyPI |
| `pyproject.toml` | 05 | 3.13 classifier | ✓ VERIFIED | Line 24, after 3.12 |
| `docs/development.md` | 05 | Release Process rewrite | ✓ VERIFIED | Automated pipeline documented |
| `docs/installation.md` | 05 | Version sample + Windows note | ✓ VERIFIED | windows-smoke documented at line 308 |
| `17-06-SUMMARY.md` | 06 | Release-gate evidence | ✓ VERIFIED | environments, publishers, run id, diff, release_head |
| `17-07-SUMMARY.md` | 07 | Published-release evidence | ✓ VERIFIED | Independently reproduced |
| `tests/test_hygiene.py` | 08 | Doc guards | ✓ VERIFIED | 4 doc guards pass |
| `docs/architecture.md` | 08 | Dead-layer prose removed | ✓ VERIFIED | No dead literals; live layers kept |
| `docs/development.md` | 08 | Live how-to; pre-commit removed | ✓ VERIFIED | Verified directly |
| `docs/api-reference.md` | 08 | Live SearchOptions kept; dead docs removed | ✓ VERIFIED | Core SearchOptions retained |
| `docs/models.md` | 08 | Live core models only | ✓ VERIFIED | No `sif.models.search` claims |
| `DESIGN.md` | 08 | Dead tree entries/interface removed | ✓ VERIFIED | No dead literals |
| `docs/testing.md` | 08 | Pre-commit guidance removed; bandit marker kept | ✓ VERIFIED | One bandit marker |
| `docs/contributing.md` | 08 | Pre-commit text/marker removed | ✓ VERIFIED | No pre-commit mention |
| `tests/test_docs.py` | 08 | `SKIP_COMMAND_PATTERNS` without pre-commit install | ✓ VERIFIED | Pattern list clean |
| `tests/test_hygiene.py` | 09 | Tracked-junk guard | ✓ VERIFIED | `test_tracked_junk_removed` passes non-vacuously |

### Key Link Verification

20 declared key links. `gsd_run query verify.key-links` verifies 11 directly and flags 9 whose `from` value is a component description rather than a relative path; each flagged link was verified manually below.

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/test_hygiene.py` | deleted module paths | rglob text scan + existence assertions | ✓ WIRED | Guard passes; a surviving importer would fail it |
| `src/sif/models/__init__.py` | `sif.models` consumers | `__all__` no dead names | ✓ WIRED | Test asserts disjunction |
| `examples/quickstart.py` | `database.py` / `bm25.py` | `Database`/`BM25Searcher` usage | ✓ WIRED | Compile guard + direct inspection |
| `pyproject.toml [tool.uv.sources]` | `uv.lock` torch entries | marker-scoped CPU index materialized | ✓ WIRED (manual; `from` is a component description) | `+cpu` entries and PyPI entries present; guard passes |
| `tests/test_ci_workflows.py` | `uv.lock` + `pyproject.toml` | text-level guards | ✓ WIRED | 18 guards pass |
| `test-matrix.yml` | `uv.lock` | `cache-dependency-glob` + `uv sync --frozen` | ✓ WIRED | Workflow text + green run |
| `test-matrix.yml` | `pyproject.toml` pytest/coverage config | bare pytest inherits addopts/fail_under | ✓ WIRED | No `--no-cov`; fail_under=90 present |
| `Makefile windows-smoke` | `scripts/windows_smoke.py` on yoga | `hc exec --on yoga … uv run --frozen` | ✓ WIRED (manual) | Target text + recorded run |
| `watch.py` | `utils/daemon.py` | library guard before `detach()` | ✓ WIRED | Both guards present; 45 tests pass |
| `tests/test_windows_smoke_script.py` | `scripts/windows_smoke.py` | direct matcher imports | ✓ WIRED | Tests pass |
| `README.md marker` | PyPI project description | hatchling reads README | ✓ WIRED (manual) | Live PyPI JSON contains the marker |
| `publish.yml build job` | `src/sif/_version.py` | `runpy` + `GITHUB_REF_NAME` gate | ✓ WIRED (manual) | Gate present; release tag matched |
| `publish.yml publish jobs` | environments `pypi`/`testpypi` | environment-scoped OIDC | ✓ WIRED (manual) | Both environments exist; both OIDC mints succeeded |
| `publish.yml environments` | GitHub environments + publisher registration | exact identity fields | ✓ WIRED (manual) | Provenance records `publish.yml` + `pypi`; publish succeeded |
| `17-04-SUMMARY smoke HEAD` | release HEAD | `git diff -- src/sif` limited to `_version.py` | ✓ WIRED (manual) | Diff is exactly `src/sif/_version.py` |
| `tag v1.1.2` | `publish.yml` | tag push is the only trigger | ✓ WIRED (manual) | Tag exists; run triggered |
| `PyPI artifact` | MCP Registry ownership marker | `info.description` contains marker | ✓ WIRED (manual) | Fresh PyPI JSON check |
| `tests/test_hygiene.py` | docs + DESIGN.md | dead literal + VERIFY scans | ✓ WIRED | Guards pass; direct grep confirms |
| `docs/development.md` | `src/sif/search/` + `sif.core.models` | live searcher how-to | ✓ WIRED | Section verified |
| `tests/test_hygiene.py` | git index | `git ls-files` + sentinel | ✓ WIRED | Guard passes non-vacuously |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `src/sif/_version.py` | `__version__` | single literal → hatchling wheel METADATA → PyPI JSON → installed CLI | Yes: PyPI reports 1.1.2 and both fresh venvs print `sif, version 1.1.2` | ✓ FLOWING |
| `README.md` | PyPI `info.description` | hatchling `readme = "README.md"` at build time | Yes: marker present in the live PyPI JSON for 1.1.2 | ✓ FLOWING |
| `uv.lock` | torch resolution | explicit CPU index + Linux marker | Yes: `+cpu` entries; 8-cell matrix green | ✓ FLOWING |
| `scripts/windows_smoke.py` | CLI outputs | temp `SIF_DB_PATH` SQLite DB → CLI stdout/stderr → matchers | Yes: recorded run produced all PASS lines | ✓ FLOWING |
| `publish.yml` build job | dist artifact | `uv build` → upload-artifact → both publish jobs | Yes: identical file sizes on both indexes; attestation OK | ✓ FLOWING |
| render surfaces | — | none introduced by this phase | N/A | N/A |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q --no-cov` | 3233 passed, 1 skipped in 130.68 s, exit 0 | ✓ PASS |
| Phase guard battery | `pytest tests/test_hygiene.py tests/test_ci_workflows.py tests/test_release_metadata.py tests/test_windows_smoke_script.py tests/test_version_identity.py -q --no-cov` | 58 passed in 1.64 s | ✓ PASS |
| Watch/daemon guards | `pytest tests/unit/cli/test_watch_cmd.py::TestDaemonFlagGuards tests/unit/utils/test_daemon.py -q --no-cov` | 45 passed in 0.54 s | ✓ PASS |
| RRF fusion behavior | `pytest tests/unit/search/test_rrf.py -q --no-cov` | 43 passed | ✓ PASS |
| Repo-wide lint/format/type | `ruff check src tests` / `ruff format --check src tests` / `ty check src/sif` | All checks passed / 236 files formatted / All checks passed | ✓ PASS |
| Lock freshness | `uv lock --check` | Resolved 106 packages, exit 0 | ✓ PASS |
| Local version surface | `python -m sif.cli.main --version` | `sif, version 1.1.2` | ✓ PASS |
| PyPI JSON | `curl https://pypi.org/pypi/docsif/1.1.2/json` | version 1.1.2; marker present; files 220225/3108000 | ✓ PASS |
| TestPyPI JSON | `curl https://test.pypi.org/pypi/docsif/1.1.2/json` | version 1.1.2; marker present; identical sizes | ✓ PASS |
| PEP 740 attestation | `uvx pypi-attestations verify pypi --repository https://github.com/zhangtaolab/SIF docsif-1.1.2-py3-none-any.whl` | `OK: docsif-1.1.2-py3-none-any.whl`, exit 0 | ✓ PASS |
| PyPI install | fresh `/tmp/sif-verif-pypi-17` venv, `uv pip install docsif==1.1.2` | `sif, version 1.1.2` | ✓ PASS |
| TestPyPI install | fresh `/tmp/sif-verif-testpypi-17` venv, TestPyPI index + PyPI extra index | `sif, version 1.1.2` | ✓ PASS |
| Windows degradation smoke | recorded `make windows-smoke` (hc yoga, clean checkout at `48759e2`) | 8/8 PASS at HEAD `48759e2c532d01d92a0deef08520a58c41115378` (recorded; yoga unreachable at this re-check) | ✓ PASS (recorded) |
| Test Matrix on release HEAD | `gh run view 43561542242 --json …` | conclusion success; headSha `c819f67`; 8 py + 1 lint job success | ✓ PASS |
| Publish workflow | `gh run view 43562577065 --json …` | attempt 4; conclusion success; Build, TestPyPI, PyPI all success | ✓ PASS |
| Release tag | `git ls-remote --tags origin v1.1.2 'v1.1.2^{}'` | `v1.1.2` peels to `c819f672…` on origin (tag object `fcca22f8…`) | ✓ PASS |
| GitHub environments | `gh api repos/zhangtaolab/sif/environments` | `pypi` + `testpypi` present | ✓ PASS |

### Probe Execution

None applicable. No probe scripts are declared or conventionally present (`find scripts -path '*/tests/probe-*.sh'` returns nothing; no probe reference appears in any phase PLAN/SUMMARY), so Step 7c was not triggered. The smoke script is exercised through `make windows-smoke`; its recorded run is listed above.

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|----------------|-------------|--------|----------|
| ENG-01 | 17-02, 17-03, 17-05 | Full suite green on py3.10-3.13 × ubuntu/macos, fail_under=90 per cell, CPU torch on Linux, both resolution fleets tolerated, on every push/PR | ✓ SATISFIED | 8-cell workflow + lint job; run 43561542242 green on `c819f67`; CPU torch in lock; guards forbid `--no-cov` and version pinning |
| ENG-02 | 17-04, 17-05 | Windows degradation verified by a CI smoke on hc remote yoga (uv python install first; fork/systemd/flock degrade honestly) | ✓ SATISFIED | Guards + committed smoke + unit battery + Makefile target; recorded 8/8 PASS at `48759e2`; docs document the on-demand step |
| ENG-03 | 17-05, 17-06, 17-07 | Maintainer can publish docsif to PyPI via trusted publishing (marker before publish, TestPyPI dry run, version single-sourced, PEP 740 attestations) | ✓ SATISFIED | PyPI + TestPyPI serve 1.1.2; marker in `info.description`; attestation verifies; fresh-venv installs from both indexes; tag on release_head |
| ENG-04 | 17-01, 17-02, 17-05, 17-08, 17-09 | Hygienic repo: dead layers deleted, tracked junk removed, Makefile/extras/pre-commit cleaned, black dropped, fastapi/uvicorn kept, 3.13 classifier only when green | ✓ SATISFIED | All deletions/guards verified; 0 junk tracked; no pre-commit/black tokens; core deps intact; classifier present after green run |

No orphaned requirements: `REQUIREMENTS.md` maps exactly ENG-01..ENG-04 to Phase 17, all four are claimed by at least one plan (`requirements:` frontmatter), and all four are marked Complete in traceability. No requirement mapped to Phase 17 is unclaimed.

### Prohibitions (must-NOT checks)

All 14 plan-declared prohibitions were evaluated against the current tree and live evidence; each was satisfied (the plans' frontmatter still carries `status: unresolved` because the planner never updated it).

| Plan | Prohibition | Status | Evidence |
|------|-------------|--------|----------|
| 17-01 | MUST NOT delete code on a runtime path | ✓ SATISFIED | Deletions limited to the three verified-dead modules, the orphan RRF function, and their tests/factories; full suite + 8-cell matrix green |
| 17-01 | MUST NOT leave examples/Makefile describing deleted layers or phantom pre-commit | ✓ SATISFIED | `test_quickstart_example_compiles`, `test_makefile_has_no_pre_commit_target`, dead-literal greps |
| 17-02 | MUST NOT add a package or trust a third-party index beyond the explicit CPU index | ✓ SATISFIED | `git diff 7b19944..f33f389 -- pyproject.toml` shows only floor changes + a direct `torch` declaration (already transitive); single `explicit = true` index |
| 17-03 | MUST NOT weaken the coverage gate to make the matrix green | ✓ SATISFIED | `fail_under = 90` unchanged; workflow forbids `--no-cov`; 8 cells intact |
| 17-04 | MUST NOT present the smoke as full Windows support | ✓ SATISFIED | Script docstring + docs/installation.md + docs/development.md state degradation-only; WIN-F1 deferred |
| 17-04 | MUST NOT touch the user's real index, collections, or model cache on yoga | ✓ SATISFIED | `SIF_DB_PATH` inside `tempfile.TemporaryDirectory`; only the temp docs dir is removed; BM25-only argv |
| 17-05 | MUST NOT publish a release without the mcp-name marker | ✓ SATISFIED | Published 1.1.2 `info.description` contains the exact marker |
| 17-05 | MUST NOT publish from a mismatched tag or a red matrix | ✓ SATISFIED | Tag gate in build job; run 43561542242 green on `c819f67`; tag peels to `c819f67` |
| 17-06 | MUST NOT weaken publisher identity or disable OIDC | ✓ SATISFIED | Workflow uses `publish.yml` + environments `pypi`/`testpypi` + job-scoped `id-token: write`; successful OIDC publish |
| 17-07 | MUST NOT rebuild in publish jobs or re-upload under a mutated version | ✓ SATISFIED | No `uv build` in publish jobs; both download artifact `dist`; identical published sizes |
| 17-07 | MUST NOT reuse credentials/environment between TestPyPI and PyPI | ✓ SATISFIED | Separate jobs, separate environments, separate repository URLs; no secrets anywhere |
| 17-08 | MUST NOT delete documentation of live layers | ✓ SATISFIED | `docs/models.md` and `docs/api-reference.md` retain SearchOptions/SearchResult/SearchType, Chunker, Embedder/Reranker/QueryExpander |
| 17-08 | MUST NOT hand-edit generator-owned `docs/cli-reference.md` / `docs/configuration.md` | ✓ SATISFIED | `.github/workflows/docs.yml:40-42` regenerates and fails on `git diff --exit-code`; committed reference docs pass the gate |
| 17-09 | MUST NOT remove any path not on the seven-path verified list | ✓ SATISFIED | `git show --stat 8e4090d`: exactly the seven junk paths plus the guard file |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No `TBD`/`FIXME`/`XXX` in any covered file (37-file scan) | ℹ️ Info | Debt-marker gate clean |
| — | — | No `TODO`/`HACK`/`PLACEHOLDER` or placeholder prose in covered files | ℹ️ Info | No stub/empty implementation; `scripts/windows_smoke.py` fully implemented and unit-tested |
| `.github/workflows/publish.yml` | 50-89 | No job-level `timeout-minutes` on publish jobs (WR-06); no concurrency guard (WR-07) | ℹ️ Info — open review findings, user-accepted | Plan 17-05 must-have requires build-once/tag-gate/OIDC, not these hardening items |
| `Makefile`/`index.py` etc. | — | WR-09, IN-01..IN-06 remain open by explicit user decision (11 findings) | ℹ️ Info — accepted | None contradicts a plan must-have; the five fixed findings (CR-01, WR-01, WR-04, WR-05, WR-08) are present in `b0d45bf` |
| `docs/testing.md`, `docs/development.md` | — | WR-02/WR-03 (stale CI/test-helper prose) were open phase verification; the phase-24 doc regeneration reconciled them (`docs/testing.md:131,142` now describe the removed factories; `docs/development.md:751` now describes CI correctly) | ℹ️ Info — resolved upstream | No must-have impact |

### Human Verification Required

None. All external-service and runtime claims were independently reproduced in this run: the 8-cell matrix run and Publish run were read from GitHub Actions, PyPI/TestPyPI JSON and PEP 740 provenance were fetched live, both fresh-venv installs were performed, the release tag was resolved from origin, and the environments were listed via the GitHub API. The single item not re-executed is the remote Windows smoke, because the yoga host was unreachable (`hc ls`: "cannot reach Yoga"); it remains evidenced by the recorded 8/8 PASS at `48759e2` and the prior verifier's independent reproduction.

### Gaps Summary

No gaps. The phase goal is achieved in the codebase and on the external services it names:

- **Green regression net:** `.github/workflows/test-matrix.yml` declares a fixed 8-cell matrix (py3.10-3.13 × ubuntu/macos) plus a py3.12 ruff/format/ty lint job, least-privilege and secret-free, and Test Matrix run 43561542242 is green on the release HEAD `c819f67` (8 py cells + lint). The workflow has no `--no-cov` and inherits `fail_under=90` per cell.
- **Proven release pipeline / docsif on PyPI:** tag `v1.1.2` peels to the gate-verified `c819f67`; Publish run 43562577065 completed `success` (build reused, TestPyPI, PyPI); PyPI and TestPyPI serve 1.1.2 with the mcp-name marker; PEP 740 attestation verifies; fresh venvs install 1.1.2 from both indexes. The marker commit precedes the tag.
- **Windows degradation:** the guards, committed smoke, unit battery, and Makefile target all exist, and the recorded independent run on yoga returned 8/8 PASS at HEAD `48759e2` with no traceback and no model download.
- **Hygiene:** the three dead layers, orphan RRF export, `CURRENT_SCHEMA_VERSION`, phantom pre-commit flow, black, and seven tracked junk paths are gone, with guards; live-layer docs survive; exactly one docs VERIFY marker (bandit) remains.

Accepted residuals (not must-have gaps): 11 lower-severity review findings remain open by explicit user decision, and the previously deferred stale test-helper references have been reconciled by later documentation regeneration. These do not contradict any plan `must_haves` and are explicitly out of the phase's locked scope.

---

_Verified: 2026-11-18T03:37:14Z_
_Verifier: Claude (gsd-verifier)_
