---
phase: 17-engineering-foundation-ci-matrix-hygiene-pypi
plan: 03
subsystem: ci
tags: [github-actions, test-matrix, uv-frozen, coverage-gate, lint-job, logging-isolation, caplog]

# Dependency graph
requires: ["17-01", "17-02"]
provides:
  - ".github/workflows/test-matrix.yml: 8-cell full suite (py3.10-3.13 x ubuntu/macos) with per-cell fail_under=90, frozen uv sync, dependency-only cache, per-ref cancellation, SHA-pinned setup-uv, least-privilege permissions"
  - "lint job on ubuntu-latest/py3.12 running ruff check, ruff format --check, and ty check src/sif from the frozen environment"
  - "six workflow text guards in tests/test_ci_workflows.py (14 guards total in the module)"
  - "green Test Matrix run 43399300651 for phase HEAD f6092f8: 8 py cells + lint all successful"
  - "test-order-independent caplog isolation via an autouse conftest logging fixture (locked pytest 9.0.3 safe)"
affects: [17-05, 17-09, 18, 19, 20, 21, 22]

# Actuals (#2632)
actuals:
  tokens: 2751
  tasks: 3
  commits: 3
  plan_head_before: 0c5837e7baf73b184b6a866c8b967d9874ae0a12
  plan_head_after: f6092f8dbf7059264a95dd69eb66dd153bf4b073

tech-stack:
  added: []
  patterns:
    - "Fixed literal 8-cell matrix: os x python-version lists, fail-fast false, quote every Python version"
    - "Job-block text guard: split the workflow on top-level job keys before asserting command scope"
    - "Repository-wide hermetic sif logger reset (setLevel NOTSET, propagate True, handlers [], logging.disable NOTSET) so pytest 9.0.x caplog sees SIF records regardless of test order"

key-files:
  created:
    - .github/workflows/test-matrix.yml
  modified:
    - tests/test_ci_workflows.py
    - tests/conftest.py
    - src/sif/search/rerank.py

key-decisions:
  - "Implemented D-01..D-04 exactly: every push/PR runs all 8 cells, dependency-only caching (no HF model cache), macos-latest arm64 only, per-ref cancel with fail-fast false"
  - "Kept the pytest step bare (`env -u FORCE_COLOR NO_COLOR=1 uv run --frozen pytest`) so pyproject addopts and fail_under=90 apply per cell; guards forbid --no-cov"
  - "Added a repository-wide conftest logging-isolation fixture instead of per-module fixtures after the first run proved 13 caplog assertion failures were order-dependent under the locked pytest 9.0.3"
  - "Moved LlamaCppReranker's missing-path validation ahead of the llama_cpp import so a clean dev+embed environment raises the documented ValueError, not ModuleNotFoundError"

patterns-established:
  - "Workflow guard: read the YAML as text, assert literal cells/permissions/SHA pin, and scope job-specific assertions with a top-level job-block splitter (no PyYAML dependency)"
  - "CI-environment parity: reproduce clean-env failures in a scratch uv venv pinned to locked versions before changing code"

requirements-completed: [ENG-01]

coverage:
  - id: D1
    description: "The matrix declares exactly 8 cells (4 Pythons x ubuntu/macos) with fail-fast false, per-ref cancellation, and no tag trigger"
    requirement: ENG-01
    verification:
      - kind: unit
        ref: "tests/test_ci_workflows.py#test_matrix_declares_eight_cells"
        status: pass
      - kind: unit
        ref: "tests/test_ci_workflows.py#test_matrix_excludes_tag_pushes"
        status: pass
    human_judgment: false
  - id: D2
    description: "Each cell syncs the frozen lock with dev+embed extras and runs bare pytest with the coverage gate; --no-cov is forbidden"
    requirement: ENG-01
    verification:
      - kind: unit
        ref: "tests/test_ci_workflows.py#test_matrix_runs_full_suite_with_coverage"
        status: pass
      - kind: e2e
        ref: "gh run 43399300651: all 8 cells reported 'Required test coverage of 90.0% reached' at 95.04-95.07% with 1636 passed, 1 skipped"
        status: pass
    human_judgment: false
  - id: D3
    description: "The workflow is least-privilege and secret-free, with setup-uv pinned to the verified commit SHA"
    requirement: ENG-01
    verification:
      - kind: unit
        ref: "tests/test_ci_workflows.py#test_matrix_has_least_privilege"
        status: pass
      - kind: unit
        ref: "tests/test_ci_workflows.py#test_setup_uv_is_sha_pinned"
        status: pass
    human_judgment: false
  - id: D4
    description: "A py3.12 lint job runs the repo gates verbatim and the guard proves the commands live in the lint job, not the matrix job"
    requirement: ENG-01
    verification:
      - kind: unit
        ref: "tests/test_ci_workflows.py#test_lint_job_runs_repo_gates"
        status: pass
      - kind: e2e
        ref: "gh run 43399300651: lint / py3.12 / ubuntu-latest succeeded in 9s"
        status: pass
    human_judgment: false
  - id: D5
    description: "The phase HEAD runs green on GitHub Actions: exactly 8 successful py jobs plus exactly 1 successful lint job"
    requirement: ENG-01
    verification:
      - kind: e2e
        ref: "plan Task 3 automated verify (gh run list/view + job-count assertions) exited 0 for HEAD f6092f8, run 43399300651"
        status: pass
    human_judgment: false

duration: 21min
completed: 2026-11-13
status: complete
---

# Phase 17 Plan 03: CI Matrix + Lint Job Summary

**An 8-cell GitHub Actions matrix (py3.10-3.13 x ubuntu/macos) now runs the unchanged full suite with per-cell fail_under=90 on every push/PR, plus a py3.12 ruff/format/ty lint job; the phase HEAD is proven green in run 43399300651.**

## Performance

- **Duration:** 21 min
- **Started:** 2026-11-13T09:00:44Z
- **Completed:** 2026-11-13T09:21:55Z
- **Tasks:** 3/3
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments

- Created `.github/workflows/test-matrix.yml`: `push` on all branches + `pull_request`, workflow-level `contents: read`, per-ref `cancel-in-progress`, `fail-fast: false`, and a fixed literal matrix of `[ubuntu-latest, macos-latest]` x `['3.10', '3.11', '3.12', '3.13']`.
- Each cell uses `actions/checkout@v7`, SHA-pinned `astral-sh/setup-uv@68559e99...` (v10.3.3) with `cache-dependency-glob: uv.lock` and a per-version `cache-suffix`, `uv python install`, `uv sync --frozen --extra dev --extra embed`, and bare `env -u FORCE_COLOR NO_COLOR=1 uv run --frozen pytest` so pyproject's addopts and `fail_under=90` apply per cell.
- Added the `lint` job (`lint / py3.12 / ubuntu-latest`, 15-minute timeout, no secrets/id-token) running `ruff check src tests`, `ruff format --check src tests`, and `ty check src/sif` from the frozen dev environment.
- Extended `tests/test_ci_workflows.py` with six dependency-free text guards: eight cells, full-suite coverage, least privilege, SHA pin, no tag trigger, and lint-job gates scoped via a top-level job-block splitter.
- Pushed `dev` and proved the phase HEAD green on real runners: run **43399300651** (commit `f6092f8`) completed with 8 successful py cells and 1 successful lint job; every cell reported the coverage gate passing.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create the 8-cell test matrix workflow and its guards** - `3bbb80e` (feat)
2. **Task 2: Add the lint/type job so repo gates run remotely** - `6217898` (feat)
3. **Task 3: Push the phase branch and prove the 8-cell matrix green** - verification-only task (no files); CI fixes landed as `f6092f8` (fix)

**Plan metadata:** committed separately after this summary (docs: complete 17-03 plan)

## CI Evidence

- **Run:** 43399300651 (https://github.com/zhangtaolab/SIF/actions/runs/43399300651), HEAD `f6092f8dbf7059264a95dd69eb66dd153bf4b073`, trigger push to `dev`.
- **Jobs:** lint success (9s); py3.10 py3.11 py3.12 py3.13 on ubuntu-latest success (2m00s-2m43s); py3.10 py3.11 py3.12 py3.13 on macos-latest success (2m11s-3m50s).
- **Per-cell gate:** every cell logged `Required test coverage of 90.0% reached. Total coverage: 95.04%` (ubuntu py3.10 and macos py3.11: 95.07%) with `1636 passed, 1 skipped`; no cell ran with `--no-cov`.
- **Earlier failed run:** 43398080664 exposed 14 clean-environment failures (see Deviations); the fix commit re-ran to the green result above.

## Files Created/Modified

- `.github/workflows/test-matrix.yml` - NEW: 8-cell matrix plus py3.12 lint job
- `tests/test_ci_workflows.py` - six workflow guards added to the existing lock/packaging guards (module now 14 guards)
- `tests/conftest.py` - autouse `_hermetic_sif_logging` fixture resetting leaked `sif` logger state before each test
- `src/sif/search/rerank.py` - `LlamaCppReranker.load()` validates the missing model path before importing `llama_cpp`

## Decisions Made

- Followed locked D-01..D-04 verbatim: full matrix on every push/PR, dependency-only caching, `macos-latest` arm64 only, per-ref cancellation with `fail-fast: false`.
- Kept the pytest step bare and added guards that reject `--no-cov` and `-p no:`, so the coverage gate cannot be muted to make a cell green (plan prohibition).
- Chose a repository-wide conftest logging-isolation fixture over per-module fixtures: the leak is process-global and the per-module approach already existed in one module while 13 other assertions failed.
- Reproduced the red cells in a scratch uv venv pinned to the locked pytest 9.0.3 before changing code, confirming both root causes rather than guessing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] LlamaCppReranker imported llama_cpp before validating the model path**
- **Found during:** Task 3 (first matrix run, all 8 cells)
- **Issue:** `LlamaCppReranker.load()` executed `from llama_cpp import Llama` before the missing-path check. On a clean `dev+embed` environment (no llama-cpp-python), `test_load_raises_without_path` raised `ModuleNotFoundError` instead of the documented `ValueError`.
- **Fix:** moved the `path`/`ValueError` validation above the lazy import.
- **Files modified:** `src/sif/search/rerank.py`
- **Commit:** `f6092f8`

**2. [Rule 2 - Missing critical functionality] Test isolation for leaked `sif` logger state**
- **Found during:** Task 3 (first matrix run, all 8 cells)
- **Issue:** The root CLI callback runs `setup_logging`, which sets `propagate = False` and replaces handlers on the `sif` logger. pytest 9.0.3 (the locked version) attaches caplog's capture handler to the root logger only, so once a CLI test polluted the logger, 13 caplog assertions in later modules silently saw empty output. Local pytest 9.1.1 masks this by attaching capture handlers to non-propagating loggers, so the suite was green only outside CI.
- **Fix:** added an autouse `_hermetic_sif_logging` fixture in `tests/conftest.py` that resets the `sif` logger (level, propagate, disabled, handlers) and the global `logging.disable` level before every test.
- **Verification:** reproduced 13 failures under pytest 9.0.3 in a scratch venv, then 578/578 passing after the fix; full local suite 1636 passed, 1 skipped at 95.04%.
- **Files modified:** `tests/conftest.py` (Commit `f6092f8`)

## Issues Encountered

- The first matrix run (43398080664) failed on all 8 cells with the same 14 tests, exposing exactly the clean-environment gaps the matrix exists to find. Diagnosed via `gh run view --log-failed`, fixed, and re-ran to green. No cell was muted, no `--no-cov`, no lowered `fail_under`.
- GitHub macOS arm64 runner capacity delayed the final cell queue; the run still completed well inside the 30-minute bound.

## User Setup Required

None - no external service configuration required for this plan. (PyPI/TestPyPI publisher registration and the `pypi`/`testpypi` environments belong to later plans.)

## Next Phase Readiness

- ENG-01's CI half is proven: the green run 43399300651 gates the 3.13 classifier work in plan 17-05.
- The matrix consumes the frozen lock exactly as CI will (`uv sync --frozen`), and the lint job mirrors the local repo gates.
- Full gate state: 1636 passed, 1 skipped @ 95.04% (fail_under=90); ruff check, ruff format --check, and `ty check src/sif` green locally.

---
*Phase: 17-engineering-foundation-ci-matrix-hygiene-pypi*
*Completed: 2026-11-13*

## Self-Check: PASSED
