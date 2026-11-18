---
phase: quick-261118-jbj
plan: 01
subsystem: release
tags: [release, version-bump, torch-backend, uv, install-docs]

# Dependency graph
requires: []
provides:
  - v1.2.1 release metadata across the single version literal, server.json, plugin/marketplace manifests, changelog, and release-metadata tests
  - Driver-aware install matrix (--torch-backend=auto / cpu / no flag on macOS) in README and all install docs
  - pip CPU-vs-CUDA index matrix with the no-auto-detection note
affects: [release v1.2.1 tagging/publishing]

# Actuals (#2632) — pairs with the plan's estimate to calibrate future estimates.
actuals:
  tokens: 4612
  tasks: 3
  commits: 3

plan_head_before: 06a6c09ffb55c62791373d63f90424b9d6bfac58
plan_head_after: 62c5d99361d4f0f13d1d6df022adb35289bf43d3

tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - src/sif/_version.py
    - server.json
    - .claude-plugin/plugin.json
    - .claude-plugin/marketplace.json
    - docs/changelog.md
    - tests/test_release_metadata.py
    - README.md
    - docs/installation.md
    - tests/test_docs.py
    - tests/test_ci_workflows.py
    - docs/index.md
    - docs/quickstart.md
    - docs/mcp-server.md

key-decisions:
  - "The Linux GPU path is --torch-backend=auto (uv selects the CUDA build for the driver) and the CPU-only path keeps --torch-backend=cpu; macOS installs with no backend flag because the macOS wheel includes MPS and the CPU backend has no macOS wheel for torch 2.15.0"
  - "pip users get an explicit CPU-vs-CUDA index matrix (whl/cpu vs whl/cu132) because pip cannot auto-detect the GPU"
  - "The 1.2.1 changelog section is inserted between Unreleased and 1.2.0; Unreleased now compares v1.2.1...HEAD and a [1.2.1] tag link is added, with historical entries untouched"

requirements-completed: [QUICK-RELEASE-1-2-1]

# Metrics
duration: 8min
completed: 2026-11-18
status: complete
---

# Quick Task 261118-jbj: Release v1.2.1 Bump and Install Backend Matrix Summary

**docsif 1.2.1 is consistent across the single version literal, all three parity manifests, the changelog, and the release-metadata tests, and every install doc now presents the verified auto/cpu/macOS torch matrix plus a pip CPU-vs-CUDA index matrix.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-11-18T13:58:53Z
- **Completed:** 2026-11-18T14:06:48Z
- **Tasks:** 3/3
- **Files modified:** 13

## Accomplishments

- Bumped `src/sif/_version.py` to `1.2.1` and mirrored it in `server.json` (top-level and `packages[0]`), `.claude-plugin/plugin.json`, and `.claude-plugin/marketplace.json`; the plugin/marketplace parity tests and the registry-manifest test are green.
- Added the `## [1.2.1] - 2026-11-18` changelog section (torch floor + issues #4/#5 fixes), moved the `[Unreleased]` compare link to `v1.2.1...HEAD`, and added `[1.2.1]:`; the 1.2.0 section and older entries are byte-unchanged.
- Renamed and re-pinned `test_changelog_has_1_2_1` / `test_version_literal_is_1_2_1` in `tests/test_release_metadata.py`.
- Rewrote README and `docs/installation.md` install guidance to the verified matrix: `--torch-backend=auto` for Linux GPU, `--torch-backend=cpu` for Linux CPU-only, no backend flag on macOS, plus the one-line macOS warning and a pip CPU-vs-CUDA index matrix; the `sif, version` sample now reads 1.2.1.
- Extended `tests/test_docs.py` and `tests/test_ci_workflows.py` to require `--torch-backend=auto`, the CUDA index prefix, and the macOS no-flag note while retaining the CPU recipe, CPU index URL, uv 0.9.19 floor, and uv tool -> uvx -> pip ordering.
- Aligned `docs/index.md`, `docs/quickstart.md`, and `docs/mcp-server.md` with the same three-command matrix and retired the uv 0.13.7 wording.
- Full quality suite green under the frozen lock: `ruff check src tests`, `ruff format --check src tests`, and `pytest` (3251 passed, 1 skipped, 95.08% coverage).

## Task Commits

Each task was committed atomically:

1. **Task 1: Bump the release version to 1.2.1 across every parity surface, changelog, and release-metadata test** - `a1e02c0` (chore)
2. **Task 2: Rewrite the primary install guidance (README + installation.md) to the auto/cpu/macOS + pip matrix and pin it in the docs tests** - `9d85c9c` (docs)
3. **Task 3: Align the secondary install snippets with the same matrix, then run the full quality gates** - `62c5d99` (docs)

_Note: the plan's success criteria mention "one atomic commit for the plan"; the executor protocol commits per task, so the plan lands as three atomic commits instead._

## Files Created/Modified

- `src/sif/_version.py` - the single version literal is now `1.2.1`
- `server.json` - top-level and `packages[0].version` are 1.2.1
- `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` - manifest versions are 1.2.1
- `docs/changelog.md` - new 1.2.1 section plus `[Unreleased]`/`[1.2.1]` link updates
- `tests/test_release_metadata.py` - renamed 1.2.1 release-metadata tests
- `README.md` - uv tool auto/cpu/macOS matrix, pip CPU-vs-CUDA matrix, updated torch VERIFY marker
- `docs/installation.md` - Method 1 matrix, Method 3 pip matrix, Linux/macOS notes, 1.2.1 version sample
- `tests/test_docs.py` - uv-first test now requires the backend matrix; new macOS warning test
- `tests/test_ci_workflows.py` - auto backend, CUDA index, and macOS note assertions
- `docs/index.md`, `docs/quickstart.md`, `docs/mcp-server.md` - consistent three-command matrix

## Decisions Made

- Kept `src/sif/_version.py` as the only version literal; all three parity manifests mirror it in one atomic change so no intermediate state fails parity.
- Wrote the Linux GPU recommendation as `--torch-backend=auto` and kept `--torch-backend=cpu` for CPU-only, with an explicit "Do not pass `--torch-backend=cpu` on macOS" sentence in both the Method 1 and macOS sections.
- Stated the pip limitation directly (pip cannot auto-detect the GPU) and documented `whl/cpu` and `whl/cu132` index URLs so users pick the wheel for their driver.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Kept the `uv 0.9.19` literal contiguous for the docs-test floor**
- **Found during:** Task 2 (install guidance rewrite)
- **Issue:** The planned prose "`uv 0.9.19 or newer`" line-wrapped between `uv` and `0.9.19`, and `tests/test_ci_workflows.py::test_installation_docs_cpu_recipe_and_pip_alternative` requires the literal `uv 0.9.19` in `docs/installation.md`; the first rewrite dropped it and the test failed.
- **Fix:** Reworded the sentence to "resolved by `uv tool install` and `uv pip` commands from uv 0.9.19 onward" so the literal stays on one line.
- **Files modified:** docs/installation.md
- **Verification:** `pytest tests/test_docs.py tests/test_ci_workflows.py` green (39 passed)
- **Committed in:** 9d85c9c (Task 2 commit)

### Plan corrections (non-code)

**2. [Observation] README VERIFY marker count**
- **Found during:** Task 2
- **Issue:** The plan says "keep exactly the existing two README markers", but README actually carries four `<!-- VERIFY: ... -->` markers (PyPI, torch, MCP Registry, Discussions).
- **Fix:** Kept all four and updated only the torch marker's text, preserving the count; `tests/test_hygiene.py` counts only `docs/**/*.md`, so nothing is affected.
- **Files modified:** README.md
- **Committed in:** 9d85c9c (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1) plus one factual plan correction.
**Impact on plan:** No scope creep; the fix preserves an existing docs-test contract and the plan correction preserves the intended marker count.

## Issues Encountered

None beyond the uv-floor literal noted above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The tree is ready for the maintainer's release flow: the standard single commit for `.planning/` metadata is left to the orchestrator; no tag, push, publish, or GitHub issue action was performed, and `pyproject.toml`, `uv.lock`, `.github/workflows/**`, and historical v1.2.0 prose are untouched.
- v1.2.1 release metadata and install guidance are complete; tagging `v1.2.1` and publishing remain maintainer actions.

## Threat Surface Notes

- No new security-relevant surface: the plan edits docs, manifests, and text-level tests only. The mitigations in the plan's threat register (T-jbj-01 parity pinning, T-jbj-02 macOS note pinned in two test modules, T-jbj-03 auto/cpu guidance plus the pip no-auto-detection note) are all implemented.

---
*Quick task: 261118-jbj*
*Completed: 2026-11-18*

## Self-Check: PASSED

- All 13 modified files and the SUMMARY exist on disk
- Task commits a1e02c0, 9d85c9c, and 62c5d99 are ancestors of HEAD

