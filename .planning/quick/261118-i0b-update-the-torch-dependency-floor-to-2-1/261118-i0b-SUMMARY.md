---
phase: quick-261118-i0b
plan: 01
subsystem: packaging
tags: [torch, uv-lock, optional-dependencies, pytorch-cpu-index, install-docs]

# Dependency graph
requires:
  - phase: 17
    provides: explicit Linux pytorch-cpu index and the packaging contract tests (test_ci_workflows.py)
  - phase: 24
    provides: platform verification that torch 2.14.1+cu130 runs on the RTX 5090 D (sm_120) host
provides:
  - torch>=2.14 floor in the embed and all extras
  - uv.lock regenerated against the unchanged explicit Linux CPU index with all four torch rows carrying the specifier
  - packaging contract tests and install docs pinned to the new floor
affects: [release, packaging, install-docs]

# Actuals (#2632) — same chars/4 scale as the plan estimate.
actuals:
  tokens: 3898
  tasks: 3
  commits: 1
plan_head_before: 5d6fac3c07344c71facd2b2389922f1e43381892
plan_head_after: a13b134c9600929ad904898032d1f5e7254b9fd6

tech-stack:
  added: []
  patterns:
    - "Dependency-floor bump lands as pyproject change + regenerated lock + contract-test/doc pins in one atomic commit"

key-files:
  created: []
  modified:
    - pyproject.toml
    - uv.lock
    - tests/test_ci_workflows.py
    - docs/installation.md

key-decisions:
  - "Raise the floor only to >=2.14, the version verified installing and running on the RTX 5090 D host; no upper bound added"
  - "Regenerate uv.lock with plain uv lock (no --upgrade/--refresh) so the four resolved torch builds stay 2.14.1 / 2.14.1+cpu / 2.15.0 / 2.15.0+cpu"
  - "Keep [tool.uv.sources] and the explicit pytorch-cpu index byte-identical so Linux installs stay CPU-only and the lock keeps zero nvidia-*/triton entries"
  - "Contract-test literal count is held at exactly two by naming the extra and block in the failure message without repeating the floor string"

patterns-established:
  - "Floor bumps are proven by literal counts in pyproject/lock/docs plus a lock-diff gate that forbids any name/version/source line change"

requirements-completed: [QUICK-TORCH-FLOOR]

coverage:
  - id: D1
    description: "embed and all extras declare torch>=2.14"
    requirement: QUICK-TORCH-FLOOR
    verification:
      - kind: unit
        ref: "tests/test_ci_workflows.py#test_pyproject_extras_floors"
        status: pass
      - kind: other
        ref: "grep -c '^    \"torch>=2.14\",$' pyproject.toml -> 2"
        status: pass
    human_judgment: false
  - id: D2
    description: "uv.lock regenerated with the floor on all four torch rows, unchanged resolved versions, no CUDA stack, CPU index intact"
    requirement: QUICK-TORCH-FLOOR
    verification:
      - kind: unit
        ref: "tests/test_ci_workflows.py#test_lock_has_cpu_torch, #test_lock_has_no_cuda_stack, #test_pyproject_cpu_index_is_explicit"
        status: pass
      - kind: other
        ref: "uv lock --check; lock-diff gate (no name/version/source changes); specifier count 4; no nvidia-*/triton"
        status: pass
    human_judgment: false
  - id: D3
    description: "Packaging contract tests and docs/installation.md pin torch>=2.14"
    requirement: QUICK-TORCH-FLOOR
    verification:
      - kind: unit
        ref: "tests/test_ci_workflows.py#test_installation_docs_match_extras"
        status: pass
      - kind: other
        ref: "grep -cF 'torch>=2.14' docs/installation.md -> 2; tests/test_ci_workflows.py -> 2"
        status: pass
    human_judgment: false
  - id: D4
    description: "Full quality suite green under the frozen lock with dev and embed extras"
    requirement: QUICK-TORCH-FLOOR
    verification:
      - kind: other
        ref: "uv run --frozen --extra dev --extra embed ruff check src tests; ruff format --check src tests; pytest -q"
        status: pass
    human_judgment: false

duration: 8min
completed: 2026-11-18
status: complete
---

# Quick 261118-i0b: Raise the Torch Dependency Floor Summary

**`embed` and `all` now require `torch>=2.14`, with uv.lock regenerated against the unchanged explicit Linux CPU index and both packaging contract tests plus the install docs pinned to the new floor**

## Performance

- **Duration:** 8 min
- **Started:** 2026-11-18T13:07:07Z
- **Completed:** 2026-11-18T13:15:05Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Raised the torch floor to `>=2.14` in both optional-dependency extras; every other dependency line is byte-identical and the marker-scoped `pytorch-cpu` index is untouched.
- Regenerated uv.lock with plain `uv lock`: exactly the four docsif `requires-dist` torch rows gained `specifier = ">=2.14"` (the two Linux rows keep `index = "https://download.pytorch.org/whl/cpu"`), plus cosmetic `resolution-markers` reordering in seven package entries. No package name, version, source, hash, or dependency-list line changed; resolved torch remains 2.14.1 / 2.14.1+cpu / 2.15.0 / 2.15.0+cpu and the lock still carries zero nvidia-*/triton entries.
- `test_pyproject_extras_floors` now requires `"torch>=2.14"` in both extras (the old bare-entry regex is gone) and `test_installation_docs_match_extras` requires `torch>=2.14` in docs/installation.md; both inventory mentions in the docs state the floor.
- Full quality suite green under `uv run --frozen --extra dev --extra embed`: ruff check, ruff format --check, and 3,234 passed / 1 skipped at 95.03% coverage (fail_under=90).

## Task Commits

The plan specified one atomic commit for all four files (Task 3), so Task 1 and Task 2 changes were staged together at the end:

1. **Tasks 1-3: floor bump, lock regeneration, contract tests, docs, full suite** - `a13b134` (chore)

**Plan metadata:** handled by the orchestrator (SUMMARY/STATE/PLAN docs commit, Step 8).

## Files Created/Modified

- `pyproject.toml` - `"torch"` -> `"torch>=2.14"` in the `embed` and `all` extras (2 lines)
- `uv.lock` - regenerated against the unchanged CPU index; four torch rows gain the specifier (46 changed lines; versions unchanged)
- `tests/test_ci_workflows.py` - extras-floor assertion and install-docs required tuple pin `torch>=2.14`
- `docs/installation.md` - Optional Dependencies table and Embedding Support paragraph state `torch>=2.14`

## Verification Evidence

- `grep -c '^    "torch>=2.14",$' pyproject.toml` = 2; `grep -c '^    "torch' pyproject.toml` = 2
- `grep -c 'specifier = ">=2.14"' uv.lock` = 4; torch 2.14.1 x2 and 2.15.0 x2 still in the lock
- `uv lock --check` exits 0; lock diff contains no `name = ` / `version = ` / `source = ` changes; nvidia-*/triton count 0; CPU index URL and Linux marker present
- `grep -cF 'torch>=2.14' docs/installation.md` = 2; same for tests/test_ci_workflows.py = 2
- `uv run --frozen --extra dev python -m pytest tests/test_ci_workflows.py tests/test_docs.py -q --no-cov` -> 38 passed
- Full suite: `3234 passed, 1 skipped, 27 warnings in 323.45s` at 95.03% coverage; ruff check and format --check clean

## Decisions Made

- Floor set to `>=2.14` exactly (no upper bound), matching the runtime-verified torch 2.14.1+cu130 on the RTX 5090 D (sm_120) host.
- Plain `uv lock` only — no `--upgrade`, `--refresh`, or `-P` — so the existing multi-Python torch fleet is preserved.
- Test failure messages name the extra and the block but avoid repeating the floor literal, keeping the plan's exact literal count of two in the test file.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- A plain `curl` GET of the full PyPI simple index page for torch timed out at 20 s while still returning HTTP 200; a HEAD probe returned 200 in 0.76 s and `uv lock` resolved 106 packages in about 4 s, so the precondition was satisfied and no workaround was needed.

## Known Stubs

None.

## Threat Flags

None - no new trust boundary. T-i0b-01 (lock tampering/accidental upgrade) and T-i0b-02 (CPU-index scoping) mitigations were verified by the lock-diff gate, the version greps, the zero nvidia-*/triton count, and `test_pyproject_cpu_index_is_explicit`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Supported environments resolving the `embed`/`all` extras now get torch >= 2.14, so CUDA 13 / current MPS backends are available.
- `uv sync --frozen` and CI installs remain consistent with pyproject; no tag, publish, or unrelated dependency upgrade was performed.

## Self-Check: PASSED

Verified: `pyproject.toml`, `uv.lock`, `tests/test_ci_workflows.py`, `docs/installation.md` all exist with the expected content; commit `a13b134` is an ancestor of HEAD (`git merge-base --is-ancestor a13b134 HEAD`).
