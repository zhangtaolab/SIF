---
phase: 17-engineering-foundation-ci-matrix-hygiene-pypi
plan: 02
subsystem: packaging
tags: [uv-lock, torch-cpu, pytorch-index, extras-floors, black-removal, pytest-guards, documentation]

# Dependency graph
requires: []
provides:
  - "uv.lock resolving CPU-tagged torch from https://download.pytorch.org/whl/cpu on Linux (2.14.1+cpu py3.10, 2.15.0+cpu py3.11+) with no nvidia-*/triton package"
  - "PyPI torch resolution for macOS/Windows aligned to the same 2.14.1/2.15.0 fleets"
  - "pyproject.toml explicit pytorch-cpu index + Linux-marker torch source + direct torch extras"
  - "Research-locked extras floors (sentence-transformers>=5.4.1, llama-cpp-python>=0.3.35) and black/[tool.black] removal"
  - "tests/test_ci_workflows.py Wave 0 lock/packaging/docs guard suite (8 guards) for plan 17-03 to extend"
  - "docs/installation.md extras aligned with pyproject (black gone, torch and floors present)"
affects: [17-03, 17-04, 17-05, 17-06, 17-07, 17-08, 17-09]

# Actuals (#2632)
actuals:
  tokens: 25523
  tasks: 2
  commits: 2
  plan_head_before: 7b19944584b5ed06d8c5340f59aecd87334daff2
  plan_head_after: f33f389c5da06e99083a3034cf7fa426b23490be

tech-stack:
  added: []
  patterns:
    - "uv index/source tuple: [[tool.uv.index]] explicit=true + [tool.uv.sources] marker-scoped to Linux, paired with a direct torch declaration in extras"
    - "Text-level lock/packaging guards with REPO_ROOT constants and Py3.10-safe TOML section fallback"
    - "Docs absence guard scanning docs/**/*.md while excluding generator-owned files"

key-files:
  created:
    - tests/test_ci_workflows.py
  modified:
    - pyproject.toml
    - uv.lock
    - docs/installation.md

key-decisions:
  - "Ran uv lock --upgrade-package torch after the initial lock (research open question 1) so macOS/Windows PyPI torch aligns to the documented 2.14.1/2.15.0 fleets instead of lagging at 2.11.0"
  - "Completed all three installation doc lists (pytest-asyncio, modelscope, openai, full all-extra set) rather than only the named floor/black edits, so docs match the post-Task-1 pyproject exactly as instructed"
  - "Guards assert structure (a +cpu torch from the CPU index, no CUDA stack, explicit index, marker scope) and never exact transitive patch versions, per D-02 and the plan's fleet-tolerance backstop"

patterns-established:
  - "Lock guard: read uv.lock as text, assert CPU registry presence + +cpu version regex + absence of nvidia-/triton/black package lines"
  - "Extras guard: extract each optional-dependency array body from raw TOML text and assert floors/entries without a TOML parser"

requirements-completed: [ENG-01, ENG-04]

coverage:
  - id: D1
    description: "uv.lock resolves CPU-tagged torch from the explicit CPU index on Linux and carries no nvidia-*/triton packages"
    requirement: ENG-01
    verification:
      - kind: unit
        ref: "tests/test_ci_workflows.py#test_lock_has_cpu_torch"
        status: pass
      - kind: unit
        ref: "tests/test_ci_workflows.py#test_lock_has_no_cuda_stack"
        status: pass
      - kind: integration
        ref: "uv lock --check"
        status: pass
    human_judgment: false
  - id: D2
    description: "pyproject.toml has the explicit Linux-scoped CPU index, direct torch extras, corrected floors, and no black dependency or [tool.black] section"
    requirement: ENG-04
    verification:
      - kind: unit
        ref: "tests/test_ci_workflows.py#test_pyproject_cpu_index_is_explicit"
        status: pass
      - kind: unit
        ref: "tests/test_ci_workflows.py#test_pyproject_extras_floors"
        status: pass
      - kind: unit
        ref: "tests/test_ci_workflows.py#test_pyproject_has_no_black_section"
        status: pass
      - kind: unit
        ref: "tests/test_ci_workflows.py#test_lock_has_no_black"
        status: pass
      - kind: unit
        ref: "tests/test_ci_workflows.py#test_core_deps_keep_fastapi_uvicorn"
        status: pass
    human_judgment: false
  - id: D3
    description: "docs/installation.md advertises the new extras (no black dev requirement) and no non-generator doc lists black as a dev dependency"
    requirement: ENG-04
    verification:
      - kind: unit
        ref: "tests/test_ci_workflows.py#test_installation_docs_match_extras"
        status: pass
    human_judgment: false
  - id: D4
    description: "The committed lock is consumable exactly as CI consumes it (uv sync --frozen) and the local full suite is green at the coverage gate"
    requirement: ENG-01
    verification:
      - kind: integration
        ref: "uv sync --frozen --extra dev --extra embed --dry-run"
        status: pass
      - kind: integration
        ref: "env -u FORCE_COLOR NO_COLOR=1 pytest (1630 passed, 1 skipped, 95.04% coverage)"
        status: pass
      - kind: integration
        ref: "ruff check src tests && ruff format --check src tests"
        status: pass
    human_judgment: false

duration: 6min
completed: 2026-11-13
status: complete
---

# Phase 17 Plan 02: CPU Torch Fleet + Packaging Hygiene Summary

**uv.lock now resolves CPU-tagged torch 2.14.1+cpu/2.15.0+cpu from the explicit PyTorch CPU index on Linux with zero nvidia/triton packages, black removed from pyproject and the lock, extras floors locked, and eight text-level guards pinning the packaging state.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-11-13T08:50:55Z
- **Completed:** 2026-11-13T08:56:41Z
- **Tasks:** 2/2
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments

- Added `[[tool.uv.index]] pytorch-cpu` (`explicit = true`) and a `[tool.uv.sources]` torch source marker-scoped to `sys_platform == 'linux'`, plus direct `torch` declarations in the `embed` and `all` extras so uv sources actually apply (Pitfall 1).
- Regenerated `uv.lock` with `uv lock` and `uv lock --upgrade-package torch`: Linux resolves `2.14.1+cpu` (py3.10) / `2.15.0+cpu` (py3.11+); macOS/Windows resolve PyPI torch `2.14.1` / `2.15.0`. Removed 36 nvidia-* entries, triton, black, and its transitive deps (mypy-extensions, pathspec, pytokens).
- Removed `black` from the `dev` extra and deleted `[tool.black]`; raised `sentence-transformers` to `>=5.4.1` and `llama-cpp-python` to `>=0.3.35`; left fastapi/uvicorn core and mcp/http extras untouched (D-11).
- Created `tests/test_ci_workflows.py` with eight text-level guards covering the CPU source, CUDA-stack absence, black absence, explicit index/marker, extras floors, core deps, and docs alignment.
- Aligned `docs/installation.md` dev/embed/all lists with the new pyproject exactly (black gone, torch and corrected floors present).

## Task Commits

Each task was committed atomically:

1. **Task 1: CPU-torch packaging slice — pyproject sources/extras -> uv.lock -> lock guards** - `a4a97c9` (chore)
2. **Task 2: Align installation docs with the new extras and prove the local gate** - `f33f389` (docs)

**Plan metadata:** committed separately after this summary (docs: complete 17-02 plan)

## Files Created/Modified

- `tests/test_ci_workflows.py` - NEW: eight lock/packaging/docs guards (Wave 0 file shared with plan 17-03)
- `pyproject.toml` - CPU index + Linux-marker torch source; torch in embed/all; floors raised; black/[tool.black] deleted
- `uv.lock` - regenerated: CPU torch on Linux, PyPI torch elsewhere, no nvidia/triton/black
- `docs/installation.md` - extras lists aligned (black removed; torch, modelscope, pytest-asyncio, openai, all-extra set documented)

## Decisions Made

- Ran `uv lock --upgrade-package torch` after the base lock (research open question 1) so macOS/Windows PyPI torch aligns to the documented 2.14.1/2.15.0 fleets rather than lagging at 2.11.0 — this makes the lock actually exercise the fleet split the milestone names.
- Completed the full dev/embed/all dependency lists in `docs/installation.md` (pytest-asyncio, modelscope, openai included) so the docs match the post-Task-1 pyproject exactly, per the plan's prose-alignment instruction.
- Guards assert structure, not exact transitive versions: a `+cpu` torch from the CPU index, a PyPI torch entry for non-Linux, no CUDA stack — D-02 forbids pinning exact patches, and per-fleet proof belongs to the 8-cell matrix in plan 17-03.

## Deviations from Plan

None - plan executed exactly as written. (The guard test needed one `ruff format` pass before its first commit; no behavior change.)

## Issues Encountered

- The first guard draft tripped ruff E501 (103-char line) and ruff format; reformatted the module and re-ran the guards, ruff, and full suite green before committing.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The lock is frozen-consumable: `uv sync --frozen --extra dev --extra embed --dry-run` resolves entirely from the committed lock (torch 2.15.0 on macOS PyPI).
- `tests/test_ci_workflows.py` is ready for plan 17-03 to extend with the matrix-workflow text guards.
- Full gate state: 1630 passed, 1 skipped @ 95.04% coverage (fail_under=90); ruff check, ruff format --check, and `ty check src/sif` all green.
- Residual risk (accepted in the plan): actual per-fleet resolution across the 8 CI cells is proven only by plan 17-03's matrix run.

---
*Phase: 17-engineering-foundation-ci-matrix-hygiene-pypi*
*Completed: 2026-11-13*

## Self-Check: PASSED

- tests/test_ci_workflows.py: FOUND
- pyproject.toml: FOUND
- uv.lock: FOUND
- docs/installation.md: FOUND
- 17-02-SUMMARY.md: FOUND
- Commits: a4a97c9, f33f389 both FOUND
