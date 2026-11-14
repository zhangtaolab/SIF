---
phase: 17-engineering-foundation-ci-matrix-hygiene-pypi
verified: 2026-11-14T10:22:21Z
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
  - "tests/test_windows_smoke_script.py"
  - "tests/unit/cli/test_index.py"
  - "tests/unit/cli/test_watch_cmd.py"
  - "tests/unit/utils/test_daemon.py"
  - "tests/unit/utils/test_progress.py"
  - "uv.lock"
covered_digest: "v4:sha256:44f63afb1c3a782cf4b5ff993e1350c8b5af2c291e6af8d9f8391def15b757ea"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 17: Engineering Foundation (CI Matrix + Hygiene + PyPI) Verification Report

**Phase Goal:** Contributors get a green regression net on every push and a proven release pipeline — every later schema migration and the MCP shell swap land against a verified matrix, and `docsif` is on PyPI before the MCP Registry needs it.
**Verified:** 2026-11-14T10:22:21Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

55 must-have truths (43 outcome truths + 12 `verification: backstop` scope/residual declarations). Every row was checked against the codebase or an independently reproduced external result, not against SUMMARY prose.

| # | Plan | Truth | Status | Evidence |
|---|------|-------|--------|----------|
| 1 | 17-01 | Three dead layers (`models/search.py`, `search/strategy.py`, `database/migrations.py`) deleted with no surviving importer; suite collects and passes | ✓ VERIFIED | All three files absent; `grep -rn` for `sif.models.search\|sif.search.strategy\|MigrationManager` over `src tests examples` (excluding the guard's own literals) returns nothing; full suite 1674 passed, 1 skipped |
| 2 | 17-01 | Orphan `compute_rrf_score` removed while `RRFFusion` fusion behavior is byte-identical | ✓ VERIFIED | `git show 4f6506f -- src/sif/search/rrf.py` removes only the standalone function; the class body is untouched; `tests/unit/search/test_rrf.py` green in the full suite |
| 3 | 17-01 | Makefile has no pre-commit target/install/autoupdate; `.pre-commit-config.yaml` absent | ✓ VERIFIED | `grep pre-commit Makefile` → no match; file absent; `test_makefile_has_no_pre_commit_target` passes |
| 4 | 17-01 | Backstop: docs sweep, tracked-junk removal, and repo-wide zero-reference scan are out of this plan's scope | ✓ VERIFIED (scope honored) | 17-08 and 17-09 executed and are verified below; the repo-wide unknown-junk/zero-reference scan remains deferred per D-09/D-12 |
| 5 | 17-02 | `uv.lock` resolves CPU-tagged torch from `download.pytorch.org/whl/cpu` on Linux, keeps a PyPI torch for macOS/Windows, and contains no nvidia-*/triton | ✓ VERIFIED | `grep -c 'name = "nvidia-'` = 0, triton = 0; `2.14.1+cpu` / `2.15.0+cpu` entries from the CPU registry; PyPI `2.14.1` / `2.15.0` entries for non-Linux |
| 6 | 17-02 | No black dev dependency, no `[tool.black]`, no black in the lock | ✓ VERIFIED | `pyproject.toml` dev extra has no black; no `[tool.black]`; 0 black package lines in `uv.lock`; guards pass |
| 7 | 17-02 | embed/all floor sentence-transformers >=5.4.1 and declare torch directly; all floors llama-cpp-python >=0.3.35; fastapi/uvicorn stay core | ✓ VERIFIED | `pyproject.toml:51-73`; `test_pyproject_extras_floors` and `test_core_deps_keep_fastapi_uvicorn` pass |
| 8 | 17-02 | `pytorch-cpu` index is `explicit = true`; torch source marker-scoped to `sys_platform == 'linux'` | ✓ VERIFIED | `pyproject.toml:89-97`; the index is referenced only by the torch source; `test_pyproject_cpu_index_is_explicit` passes |
| 9 | 17-02 | `uv lock --check` exits 0 on the committed lock | ✓ VERIFIED | Exit 0, "Resolved 89 packages" |
| 10 | 17-02 | Backstop: fleet tolerance asserted structurally; actual per-fleet resolution proven only by the 8-cell matrix | ✓ VERIFIED | Run 43561542242 green across all 8 cells; guards assert structure (a `+cpu` torch, a PyPI torch, no CUDA stack), never exact transitive versions |
| 11 | 17-03 | Every branch push and pull_request runs exactly 8 cells (3.10-3.13 × ubuntu/macos) with `fail-fast: false` | ✓ VERIFIED | `test-matrix.yml:3-6,20-24`; run 43561542242 reports exactly 8 `py*` jobs, all success |
| 12 | 17-03 | Each cell runs bare pytest (no `--no-cov`) and syncs `uv sync --frozen --extra dev --extra embed` | ✓ VERIFIED | `test-matrix.yml:41-44`; `grep --no-cov` absent; `test_matrix_runs_full_suite_with_coverage` passes |
| 13 | 17-03 | Workflow-level `contents: read`, `pull_request` (not `pull_request_target`), no secrets, setup-uv SHA-pinned | ✓ VERIFIED | `test-matrix.yml:6-9,30`; `test_matrix_has_least_privilege` and `test_setup_uv_is_sha_pinned` pass |
| 14 | 17-03 | Per-ref concurrency with `cancel-in-progress: true`; tag pushes excluded | ✓ VERIFIED | `test-matrix.yml:11-13`; push trigger declares `branches: ['**']`, no `tags:`; guard passes |
| 15 | 17-03 | One lint/type job on ubuntu-latest/py3.12 runs `ruff check src tests`, `ruff format --check src tests`, `ty check src/sif` | ✓ VERIFIED | `test-matrix.yml:46-74`; run 43561542242 lint job success; `test_lint_job_runs_repo_gates` passes |
| 16 | 17-03 | The workflow run for the phase HEAD is green on 8 cells + lint | ✓ VERIFIED | `gh run view 43561542242`: headSha `c819f67`, conclusion success, 8 py jobs + 1 lint job all success |
| 17 | 17-03 | Backstop: matrix is a fixed literal list; an empty/dynamic/partial matrix is not guard-exercised | ✓ VERIFIED | Literal `os` × `python-version` lists present; direct run evidence shows 8 distinct cells, so the residual concern is covered by the observed run |
| 18 | 17-03 | Backstop: 8 cells compare equal in outcome; only the aggregate is asserted | ✓ VERIFIED | All 8 cell conclusions are `success`; no ordering contract is asserted or required |
| 19 | 17-04 | Detach on a platform without `os.fork` exits non-zero naming POSIX fork + foreground remedy, never a raw AttributeError | ✓ VERIFIED | `daemon.detach` RuntimeError guard at `daemon.py:239` and CLI guard at `watch.py:359`; `test_detach_requires_fork` + `test_detach_without_fork_is_refused` pass; no traceback asserted |
| 20 | 17-04 | Windows install/uninstall-service refuse with a Windows-specific message before any systemctl probe | ✓ VERIFIED | `_service_manager()` win32 guard (`watch.py:438`) is the shared site used by both `_run_install_service` and `_run_uninstall_service`; unit test passes |
| 21 | 17-04 | Smoke uses explicit argv lists (never a shell), temp `SIF_DB_PATH`, and no query/vsearch/embed model-loading command | ✓ VERIFIED | `scripts/windows_smoke.py:92-102,285-289`; `build_cli_invocations` uses `search search`; `test_commands_are_argv_lists_without_model_loading` passes |
| 22 | 17-04 | Smoke asserts version, collection add, index update Added:1 + fcntl warning, BM25 JSON result, status, Removed:0 + preserved warning, detach/service refusals | ✓ VERIFIED | Assertion table `scripts/windows_smoke.py:207-243`; live run printed all 8 PASS lines |
| 23 | 17-04 | `make windows-smoke` runs HEAD/dirty preflight, `uv python install`, frozen sync, and the smoke over `hc exec` | ✓ VERIFIED | `Makefile:78-87`; independently executed: preflight printed HEAD, uv sync checked 36 packages, script ran |
| 24 | 17-04 | Smoke completes green on the synced yoga checkout and records the tested git HEAD | ✓ VERIFIED | Independent re-run on yoga: HEAD `48759e2…`, 8/8 PASS, final "PASS all assertions"; yoga `git rev-parse HEAD` matches and `git status --porcelain` is empty |
| 25 | 17-04 | Backstop: smoke is not evidence of full Windows support; parity deferred to v2 | ✓ VERIFIED | Script docstring and docs/installation.md state degradation-only; WIN-F1 remains deferred |
| 26 | 17-04 | Backstop: yoga sync is a human step; script refuses a dirty tree and prints HEAD | ✓ VERIFIED | `_preflight_head()` prints HEAD and returns 1 on dirty output; yoga was clean at the recorded HEAD when checked |
| 27 | 17-05 | `_version.py` holds the single literal 1.1.2 and all runtime surfaces derive it | ✓ VERIFIED | `src/sif/_version.py`; `tests/test_version_identity.py` asserts `sif.__version__`, `sif._version.__version__`, `sif.cli.__version__`, `APP_VERSION`, MCP `serverInfo`; all pass |
| 28 | 17-05 | README contains the exact mcp-name marker line before the tag; PyPI description derives from README | ✓ VERIFIED | `README.md:2` exact line; commit `e5d836d` is an ancestor of `c819f67`; PyPI JSON `info.description` contains the marker |
| 29 | 17-05 | Changelog has a 1.1.2 section and footer link; `[Unreleased]` compares `v1.1.2...HEAD` | ✓ VERIFIED | `docs/changelog.md:38,255,257`; `test_changelog_has_1_1_2` passes |
| 30 | 17-05 | `publish.yml` is v*-tag-gated, builds once on ubuntu with `contents: read`, gates `GITHUB_REF_NAME` against `_version.py`, uploads dist, then TestPyPI → PyPI with job-scoped OIDC and environments | ✓ VERIFIED | `publish.yml:4-5,10-48,50-89`; guards for tag gating, id-token scoping, artifact handoff, ordering, version gate all pass |
| 31 | 17-05 | PyPI publish has no `skip-existing`; both publish jobs consume the same dist artifact; attestations stay at the trusted-publishing default | ✓ VERIFIED | Workflow text: skip-existing only on TestPyPI; both jobs use `download-artifact@v8 name: dist`, no `uv build`; published wheel/sdist sizes identical on both indexes (220225/3108000); attestation verifies |
| 32 | 17-05 | 3.13 classifier appears only after a green matrix | ✓ VERIFIED | `pyproject.toml:24` after 3.12; green run 43399300651 (`f6092f8`) predates classifier commit `9164e4f` (merge-base check) |
| 33 | 17-05 | Release Process and installation docs document `make windows-smoke`; no `twine upload` primary path | ✓ VERIFIED | `docs/development.md:572,583`; `docs/installation.md:144`; `grep twine upload docs` empty; guards pass |
| 34 | 17-05 | Backstop: tag/version equality is exact ASCII string equality | ✓ VERIFIED | Build job runs `test "v${VERSION}" = "${GITHUB_REF_NAME}"` (`publish.yml:31-35`) |
| 35 | 17-05 | Backstop: mcp-name marker must match future server.json byte-for-byte and sit on a line boundary; Registry check is Phase 22 | ✓ VERIFIED (Phase 22 portion deferred) | Marker is one complete README line, no trailing period; `test_readme_has_mcp_name_marker` passes; Registry ownership check is explicitly Phase 22 |
| 36 | 17-06 | GitHub environments `pypi` and `testpypi` exist | ✓ VERIFIED | `gh api repos/zhangtaolab/sif/environments`: `pypi` id 27264851535, `testpypi` id 27264859642, 0 protection rules each |
| 37 | 17-06 | Maintainer registered the PyPI trusted publisher and TestPyPI pending publisher with the exact identity fields | ✓ VERIFIED (end-to-end) | The only end-to-end proof is a successful OIDC mint: Publish run 43562577065 published to both TestPyPI and PyPI |
| 38 | 17-06 | The Test Matrix run for the release HEAD is green across 8 cells + lint after the release-artifact commit set | ✓ VERIFIED | Run 43561542242 on `c819f67`: 9/9 jobs success |
| 39 | 17-06 | No runtime source changed between the smoke commit and the release HEAD except `src/sif/_version.py` | ✓ VERIFIED | `git diff --name-only 48759e2..c819f67 -- src/sif` prints exactly `src/sif/_version.py` |
| 40 | 17-06 | 3.13 classifier, README marker, 1.1.2 literal, changelog, and publish workflow all present at release HEAD | ✓ VERIFIED | `git show c819f67:<path>` confirms each artifact at the tagged commit |
| 41 | 17-06 | Backstop: publisher registration is not readable via public API; a successful OIDC publish is the only end-to-end proof | ✓ VERIFIED | Publish run 43562577065 attempt 4: build, TestPyPI, and PyPI all success |
| 42 | 17-07 | Tag v1.1.2 exists and the Publish run has build + publish-testpypi + publish-pypi all successful | ✓ VERIFIED | Local and remote tag peel to `c819f67`; `gh run view 43562577065`: attempt 4, conclusion success, 3/3 jobs success |
| 43 | 17-07 | PyPI serves docsif 1.1.2 with the exact mcp-name marker in `info.description` | ✓ VERIFIED | Independent `curl https://pypi.org/pypi/docsif/1.1.2/json`: version 1.1.2, marker present |
| 44 | 17-07 | PEP 740 attestations verify for 1.1.2 against the repository | ✓ VERIFIED | Independent `uvx pypi-attestations verify pypi --repository https://github.com/zhangtaolab/SIF …` → `OK: docsif-1.1.2-py3-none-any.whl`. The plan's lowercase URL fails only on pypi-attestations' case-sensitive comparison; the SUMMARY records both outputs and the canonical-case success |
| 45 | 17-07 | A fresh venv installs docsif==1.1.2 from PyPI and reports `sif, version 1.1.2` | ✓ VERIFIED | Independent `/tmp/sif-verif-pypi-venv` install → `sif, version 1.1.2` |
| 46 | 17-07 | A fresh venv installs docsif==1.1.2 from TestPyPI (with the PyPI extra index) and reports the same | ✓ VERIFIED | Independent `/tmp/sif-verif-testpypi-venv` install → `sif, version 1.1.2` |
| 47 | 17-07 | Backstop: PyPI versions are immutable, so a partial upload requires a new patch version | ✓ VERIFIED | No partial upload occurred; attempts 1-3 never uploaded (invalid-publisher), attempt 4 published 1.1.2 completely; version legitimately consumed by success |
| 48 | 17-08 | No non-changelog doc or DESIGN.md names a deleted layer/export, carries a bare `migrations.py`/`strategy.py` tree entry, or the "legacy migration module" phrase | ✓ VERIFIED | `test_docs_do_not_describe_dead_layers` passes; direct `grep` over `docs/*.md` + `DESIGN.md` (changelog excluded) for the full literal list returns nothing |
| 49 | 17-08 | Live-layer documentation survives (core SearchOptions/SearchResult/SearchType, Chunker ABC, Embedder/Reranker/QueryExpander) | ✓ VERIFIED | `docs/models.md:175-253`, `docs/api-reference.md:229-265`; `docs/architecture.md:6,315,706`; protocol list `docs/api-reference.md:771` |
| 50 | 17-08 | `docs/development.md` "New Search Strategy" describes the live extension path with no ABC and no `search_batch` | ✓ VERIFIED | `docs/development.md:492-518` uses `sif.core.models` + `HybridSearcher`/`SearchPipeline`; `grep search_batch` empty |
| 51 | 17-08 | No docs pre-commit instructions; exactly one VERIFY marker remains and it is the bandit one | ✓ VERIFIED | `grep "make pre-commit\|pre-commit install\|pre-commit autoupdate" docs` empty; `grep "VERIFY:" docs` → exactly `docs/testing.md:213` bandit marker |
| 52 | 17-08 | Backstop: doc correctness is asserted by scans, not prose review; an unscanned stale concept can survive | ✓ VERIFIED | Scans exist and pass; the deferred `docs/testing.md` test-helper drift (WR-03) is exactly such a surviving unscanned concept, confirming the stated limitation rather than refuting it |
| 53 | 17-09 | Seven tracked junk paths removed from the index and working tree; no `MagicMock/` path tracked | ✓ VERIFIED | `git ls-files -- MagicMock quick_test.py simple_test.py verify_imports.py` prints nothing; none exists on disk; `test_tracked_junk_removed` passes with the `pyproject.toml` sentinel |
| 54 | 17-09 | No source/test/example references the junk paths and the committed suite is green | ✓ VERIFIED | `git grep quick_test/simple_test/verify_imports` outside `.planning` finds only the guard's own literal list; full suite green |
| 55 | 17-09 | Backstop: only the seven named paths are removed; the repo-wide unknown-junk audit stays deferred | ✓ VERIFIED | Exactly those seven deletions in `8e4090d`; no other path removed; unknown-junk audit remains deferred per D-12/CONTEXT |

**Score:** 55/55 truths verified (0 present-but-behavior-unverified; 12 are `verification: backstop` declarations resolved with direct evidence or scope confirmation).

### Deferred Items

None from Step 9b — no gaps were found, so nothing needed filtering against later milestone phases. Out-of-scope residuals already recorded in `deferred-items.md` and the review disposition are listed under Anti-Patterns / Notes below; they are not roadmap-deferred gaps.

### Required Artifacts

`gsd_run query verify.artifacts` reports `all_passed: true` for all nine plans (37/37 artifacts exist and pass). No artifact is a stub or orphan: every newly created module is imported/exercised, and every config/doc change is read by a guard or a live run.

| Artifact | Plan | Expected | Status | Details |
|----------|------|----------|--------|---------|
| `tests/test_hygiene.py` | 01 | Absence/import/Makefile guards | ✓ VERIFIED | 15 guards; all pass |
| `src/sif/models/__init__.py` | 01 | Dead search exports removed | ✓ VERIFIED | `__all__` holds only live models |
| `src/sif/database/__init__.py` | 01 | No MigrationManager export | ✓ VERIFIED | `__all__` holds only live repos/helpers |
| `src/sif/search/rrf.py` | 01 | RRFFusion only | ✓ VERIFIED | `class RRFFusion`; no `compute_rrf_score` |
| `examples/quickstart.py` | 01 | Live API example | ✓ VERIFIED | Compiles and runs to exit 0 against a temp DB |
| `Makefile` | 01 | pre-commit-free + windows-smoke | ✓ VERIFIED | No pre-commit/black token; windows-smoke target present |
| `pyproject.toml` | 02 | CPU index/sources/floors/classifier | ✓ VERIFIED | All contract items present |
| `uv.lock` | 02 | CPU torch, no CUDA/black | ✓ VERIFIED | 0 nvidia/triton/black; `+cpu` entries |
| `tests/test_ci_workflows.py` | 02 | Lock/packaging guards | ✓ VERIFIED | 14 guards; all pass |
| `docs/installation.md` | 02 | Extras aligned + 1.1.2 sample + windows-smoke | ✓ VERIFIED | Matches pyproject; line 144/160 |
| `.github/workflows/test-matrix.yml` | 03 | 8-cell matrix + lint job | ✓ VERIFIED | 8 cells; lint job; green run |
| `tests/test_ci_workflows.py` | 03 | Workflow guards | ✓ VERIFIED | All workflow guards pass |
| `scripts/windows_smoke.py` | 04 | Degradation smoke with matchers | ✓ VERIFIED | 8-step table; live run 8/8 PASS |
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
| `docs/installation.md` | 05 | 1.1.2 sample + Windows note | ✓ VERIFIED | Lines 144/160 |
| `17-06-SUMMARY.md` | 06 | Release-gate evidence | ✓ VERIFIED | environments, publishers, run id, diff, release_head |
| `17-07-SUMMARY.md` | 07 | Published-release evidence | ✓ VERIFIED | Independently reproduced below |
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

20 declared key links. The `verify.key-links` verb reports 8 verified and flags the remaining `from` values that are component descriptions rather than relative paths (e.g. `Makefile windows-smoke`, `README.md marker`); each flagged link was verified manually below.

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/test_hygiene.py` | deleted module paths | rglob text scan + existence assertions | ✓ WIRED | Guard passes; a surviving importer would fail it |
| `src/sif/models/__init__.py` | `sif.models` consumers | `__all__` no dead names | ✓ WIRED | Test asserts disjunction |
| `examples/quickstart.py` | `database.py` / `bm25.py` | `Database`/`BM25Searcher` usage | ✓ WIRED | Example executes exit 0 |
| `pyproject.toml [tool.uv.sources]` | `uv.lock` torch entries | marker-scoped CPU index materialized | ✓ WIRED | `+cpu` entries present; guard passes |
| `tests/test_ci_workflows.py` | `uv.lock` + `pyproject.toml` | text-level guards | ✓ WIRED | 14 guards pass |
| `test-matrix.yml` | `uv.lock` | `cache-dependency-glob` + `uv sync --frozen` | ✓ WIRED | Workflow text + green run |
| `test-matrix.yml` | `pyproject.toml` pytest/coverage config | bare pytest inherits addopts/fail_under | ✓ WIRED | No `--no-cov`; full suite gate reached |
| `Makefile windows-smoke` | `scripts/windows_smoke.py` on yoga | `hc exec --on yoga … uv run --frozen` | ✓ WIRED | Target executed end-to-end |
| `watch.py` | `utils/daemon.py` | library guard before `detach()` | ✓ WIRED | Both guards present; tests pass |
| `tests/test_windows_smoke_script.py` | `scripts/windows_smoke.py` | direct matcher imports | ✓ WIRED | Tests pass |
| `README.md marker` | PyPI project description | hatchling reads README | ✓ WIRED | PyPI JSON contains the marker |
| `publish.yml build job` | `src/sif/_version.py` | `runpy` + `GITHUB_REF_NAME` gate | ✓ WIRED | Gate present; release tag matched |
| `publish.yml publish jobs` | environments `pypi`/`testpypi` | environment-scoped OIDC | ✓ WIRED | Both environments exist; both OIDC mints succeeded |
| `publish.yml environments` | GitHub environments + publisher registration | exact identity fields | ✓ WIRED | Publish run 43562577065 published both |
| `17-04-SUMMARY smoke HEAD` | release HEAD | `git diff -- src/sif` limited to `_version.py` | ✓ WIRED | Diff exactly `src/sif/_version.py` |
| `tag v1.1.2` | `publish.yml` | tag push is the only trigger | ✓ WIRED | Tag exists; run triggered |
| `PyPI artifact` | MCP Registry ownership marker | `info.description` contains marker | ✓ WIRED | Independent PyPI JSON check |
| `tests/test_hygiene.py` | docs + DESIGN.md | dead literal + VERIFY scans | ✓ WIRED | Guards pass; direct grep confirms |
| `docs/development.md` | `src/sif/search/` + `sif.core.models` | live searcher how-to | ✓ WIRED | Section 492-518 |
| `tests/test_hygiene.py` | git index | `git ls-files` + sentinel | ✓ WIRED | Guard passes non-vacuously |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `src/sif/_version.py` | `__version__` | single literal → hatchling wheel METADATA → PyPI JSON → installed CLI | Yes: PyPI reports 1.1.2 and both venvs print `sif, version 1.1.2` | ✓ FLOWING |
| `README.md` | PyPI `info.description` | hatchling `readme = "README.md"` at build time | Yes: marker present in PyPI JSON | ✓ FLOWING |
| `uv.lock` | torch resolution | explicit CPU index + Linux marker | Yes: `+cpu` entries; 8-cell matrix green | ✓ FLOWING |
| `scripts/windows_smoke.py` | CLI outputs | temp `SIF_DB_PATH` SQLite DB → CLI stdout/stderr → matchers | Yes: live yoga run produced all PASS lines | ✓ FLOWING |
| `publish.yml` build job | dist artifact | `uv build` → upload-artifact → both publish jobs | Yes: identical file sizes on both indexes; attestation OK | ✓ FLOWING |
| `evaluator`-style render surfaces | — | none introduced by this phase | N/A | N/A |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite + coverage gate | `env -u FORCE_COLOR NO_COLOR=1 pytest -q` | 1674 passed, 1 skipped; 95.07% (fail_under=90 reached) | ✓ PASS |
| Phase guard battery | `pytest tests/test_hygiene.py tests/test_ci_workflows.py tests/test_release_metadata.py tests/test_windows_smoke_script.py tests/test_version_identity.py -q --no-cov` | 54 passed in 0.98 s | ✓ PASS |
| Hygiene guards alone | `pytest tests/test_hygiene.py -q --no-cov` | 15 passed | ✓ PASS |
| Repo-wide lint/format/type | `ruff check .` / `ruff format --check .` / `ty check src/sif` | All checks passed / 196 files formatted / All checks passed | ✓ PASS |
| Lock freshness | `uv lock --check` | Resolved 89 packages, exit 0 | ✓ PASS |
| Frozen sync consumable | `uv sync --frozen --extra dev --extra embed --dry-run` | Resolves from the committed lock; torch 2.15.0 on macOS | ✓ PASS |
| Quickstart runtime | `python examples/quickstart.py` | Exit 0; collection add, index update, BM25 search, status all work | ✓ PASS |
| PyPI JSON | `curl https://pypi.org/pypi/docsif/1.1.2/json` | version 1.1.2; marker present; files 220225/3108000 | ✓ PASS |
| TestPyPI JSON | `curl https://test.pypi.org/pypi/docsif/1.1.2/json` | version 1.1.2; marker present; identical sizes | ✓ PASS |
| PEP 740 attestation | `uvx pypi-attestations verify pypi --repository https://github.com/zhangtaolab/SIF …` | `OK: docsif-1.1.2-py3-none-any.whl`, exit 0 | ✓ PASS |
| PyPI install | fresh `/tmp` venv, `uv pip install docsif==1.1.2` | `sif, version 1.1.2` | ✓ PASS |
| TestPyPI install | fresh `/tmp` venv, TestPyPI index + PyPI extra index | `sif, version 1.1.2` | ✓ PASS |
| Windows degradation smoke | `make windows-smoke` (hc yoga, clean checkout at `48759e2`) | 8/8 PASS at HEAD `48759e2c532d01d92a0deef08520a58c41115378` | ✓ PASS |
| Test Matrix on release HEAD | `gh run view 43561542242 --json …` | conclusion success; headSha `c819f67`; 8 py + 1 lint job success | ✓ PASS |
| Publish workflow | `gh run view 43562577065 --json …` | attempt 4; conclusion success; Build, TestPyPI, PyPI all success | ✓ PASS |
| Release tag | `git ls-remote --tags origin v1.1.2 v1.1.2^{}` | `v1.1.2` peels to `c819f672…` on origin | ✓ PASS |
| GitHub environments | `gh api repos/zhangtaolab/sif/environments` | `pypi` + `testpypi`, 0 protection rules | ✓ PASS |

### Probe Execution

None applicable. No probe scripts are declared or conventionally present (`find scripts -path '*/tests/probe-*.sh'` returns nothing; no probe reference appears in any phase PLAN/SUMMARY), so Step 7c was not triggered. The smoke script is exercised through `make windows-smoke`, which was re-run and is recorded above.

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|----------------|-------------|--------|----------|
| ENG-01 | 17-02, 17-03, 17-05 | Full suite green on py3.10-3.13 × ubuntu/macos, fail_under=90 per cell, CPU torch on Linux, both resolution fleets tolerated, on every push/PR | ✓ SATISFIED | 8-cell workflow + lint job; run 43561542242 green on `c819f67`; CPU torch in lock; guards forbid `--no-cov` and version pinning |
| ENG-02 | 17-04, 17-05 | Windows degradation verified by a CI smoke on hc remote yoga (uv python install first; fork/systemd/flock degrade honestly) | ✓ SATISFIED | Independent `make windows-smoke` run: 8/8 PASS at `48759e2`; guards + smoke committed and unit-tested; docs document the on-demand step |
| ENG-03 | 17-05, 17-06, 17-07 | Maintainer can publish docsif to PyPI via trusted publishing (marker before publish, TestPyPI dry run, version single-sourced, PEP 740 attestations) | ✓ SATISFIED | PyPI + TestPyPI serve 1.1.2; marker in `info.description`; attestation verifies; fresh-venv installs from both indexes; tag on release_head |
| ENG-04 | 17-01, 17-02, 17-05, 17-08, 17-09 | Hygienic repo: dead layers deleted, tracked junk removed, Makefile/extras/pre-commit cleaned, black dropped, fastapi/uvicorn kept, 3.13 classifier only when green | ✓ SATISFIED | All deletions/guards verified; 0 junk tracked; no pre-commit/black tokens; core deps intact; classifier present after green run |

No orphaned requirements: `REQUIREMENTS.md` maps exactly ENG-01..ENG-04 to Phase 17, all four are claimed by at least one plan, and all four are marked Complete in traceability. No requirement mapped to Phase 17 is unclaimed.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No `TBD`/`FIXME`/`XXX` in any of the 50 files changed by the phase | ℹ️ Info | Debt-marker gate clean |
| — | — | No stub/empty implementation in new artifacts; `scripts/windows_smoke.py` is fully implemented and live-run; quickstart executes | ℹ️ Info | No stub blocks the goal |
| `docs/testing.md`, `docs/development.md` | 81/99/138/146, 85/252/255/331/335 | Stale references to `tests/factories.py`, `tests/unit/test_search.py`, `sample_search_*` (deleted in 17-01) | ℹ️ Info — recorded deferred (WR-03) | Not a must-have: these are test helpers, not one of the three deleted layers; `deferred-items.md` records them and the prohibition list does not include them |
| `docs/testing.md`, `docs/development.md`, `docs/contributing.md` | 198 / 699 / 363,378 | CI documentation still says CI does not run the suite/linters (WR-02) | ℹ️ Info — open review finding, user-accepted | Does not contradict a plan must-have; the workflow itself is correct and green |
| `.github/workflows/publish.yml` | 50-89 | No job-level `timeout-minutes` on publish jobs (WR-06), no concurrency guard (WR-07) | ℹ️ Info — open review findings, user-accepted | Plan 17-05 must-have requires build-once/tag-gate/OIDC, not these hardening items |
| `Makefile`/`index.py` etc. | — | WR-09, IN-01..IN-06 remain open by explicit user decision (11 findings) | ℹ️ Info — accepted | None contradicts a plan must-have; the five fixed findings (CR-01, WR-01, WR-04, WR-05, WR-08) are present in `b0d45bf` and were re-checked: platform guard + test, escaped index rendering, runnable quickstart, repo-wide ruff clean, `PermissionError` handling |

### Human Verification Required

None. All external-service and runtime claims were independently reproduced: the 8-cell matrix run and Publish run were read from GitHub Actions, PyPI/TestPyPI JSON and attestations were fetched live, both fresh-venv installs were performed, and the Windows smoke was re-run on hc yoga. No item remains that requires human judgment.

### Gaps Summary

No gaps. The phase goal is achieved in the codebase and on the external services it names:

- **Green regression net:** `.github/workflows/test-matrix.yml` declares a fixed 8-cell matrix (py3.10-3.13 × ubuntu/macos) plus a py3.12 ruff/format/ty lint job, least-privilege and secret-free, and Test Matrix run 43561542242 is green on the release HEAD `c819f67` (8 py cells + lint). The workflow has no `--no-cov` and inherits `fail_under=90` per cell.
- **Proven release pipeline / docsif on PyPI:** tag `v1.1.2` peels to the gate-verified `c819f67`; Publish run 43562577065 completed `success` (build reused, TestPyPI, PyPI); PyPI and TestPyPI serve 1.1.2 with the mcp-name marker; PEP 740 attestations verify; fresh venvs install 1.1.2 from both indexes. The marker commit precedes the tag.
- **Windows degradation:** the guards, committed smoke, unit battery, and Makefile target all exist, and an independent `make windows-smoke` run on yoga returned 8/8 PASS at HEAD `48759e2` with no traceback and no model download.
- **Hygiene:** the three dead layers, orphan RRF export, `CURRENT_SCHEMA_VERSION`, phantom pre-commit flow, black, and seven tracked junk paths are gone, with guards; live-layer docs survive; exactly one docs VERIFY marker (bandit) remains.

Accepted residuals (not must-have gaps): 11 lower-severity review findings remain open by explicit user decision, and `deferred-items.md` records stale test-helper references in `docs/testing.md`/`docs/development.md`. These are recorded for a follow-up docs/hardening pass; they do not contradict any plan `must_haves` and are explicitly out of the phase's locked scope.

---

_Verified: 2026-11-14T10:22:21Z_
_Verifier: Claude (gsd-verifier)_
