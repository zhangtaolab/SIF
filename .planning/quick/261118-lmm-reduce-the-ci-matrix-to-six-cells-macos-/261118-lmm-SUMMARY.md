---
phase: quick-261118-lmm
plan: 01
subsystem: infra
tags: [github-actions, ci-matrix, macos, pytest, documentation]

# Dependency graph
requires:
  - phase: quick-261118-jbj
    provides: v1.2.1 release prep (the release-history context for the documented six-cell gate)
provides:
  - "Test Matrix workflow: push on main only plus every pull request, six cells via two macOS exclusions"
  - "Contract tests pinning the six-cell shape and the main-only push trigger"
  - "Developer docs and the conftest caplog comment describing the six-cell, main-push shape"
affects: [release-process, ci-contract-tests, developer-documentation]

# Actuals (#2632) — chars/4 over the realized diff, same scale as the plan estimate.
actuals:
  tokens: 4690
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "GitHub Actions matrix exclusion pairs (os + python-version) keep macOS to boundary Pythons while Linux keeps all four"
    - "Text-level workflow contract tests with a compiled MATRIX_EXCLUSION regex pinning exact excludes"

key-files:
  created: []
  modified:
    - .github/workflows/test-matrix.yml
    - tests/test_ci_workflows.py
    - docs/development.md
    - docs/contributing.md
    - docs/testing.md
    - tests/conftest.py

key-decisions:
  - "Push CI runs on main only; feature branches are covered by their pull_request run, so each commit runs the matrix once"
  - "macOS keeps only the boundary Python versions 3.10 and 3.13 (Linux keeps 3.10-3.13), yielding six cells through two explicit exclude entries rather than a rewritten os/python list"
  - "Contract tests assert the exact exclusion pair order so any further reduction or re-expansion fails"

patterns-established:
  - "Matrix exclusions are pinned as exact (os, python-version) tuples in tests/test_ci_workflows.py"

requirements-completed: [QUICK-CI-SIX-CELL]

coverage:
  - id: D1
    description: "Test Matrix workflow runs six cells (Linux 3.10-3.13; macOS 3.10/3.13) and push CI triggers on main only"
    requirement: QUICK-CI-SIX-CELL
    verification:
      - kind: unit
        ref: "tests/test_ci_workflows.py#test_matrix_declares_six_cells"
        status: pass
      - kind: unit
        ref: "tests/test_ci_workflows.py#test_matrix_push_trigger_is_main_only"
        status: pass
      - kind: other
        ref: "uv run --frozen python -c '<PyYAML structural check: push.branches == [main], pull_request present, fail-fast false, derived cell set == 6>'"
        status: pass
    human_judgment: false
  - id: D2
    description: "docs/development.md, docs/contributing.md, docs/testing.md, and the tests/conftest.py comment all state six cells and push-on-main plus every pull request with no stale count"
    requirement: QUICK-CI-SIX-CELL
    verification:
      - kind: other
        ref: "positive greps ('six cells', 'six test cells', 'six-cell') plus negative grep for eight-cell/all-eight/any-branch/double-star patterns over the four files"
        status: pass
    human_judgment: true
    rationale: "No test pins the prose of these three docs files (tests/test_docs.py DOCS_FILES excludes them); grep proves the shape vocabulary but a human should confirm the sentences read correctly."

# Metrics
duration: 7min
completed: 2026-11-18
status: complete
plan_head_before: d5f7afb027ec2c3497b9b7983b875ddcfd6495ed
plan_head_after: f665eee153c535d51b5cbb04e103bf04a0b99b00
commits: 3
---

# Quick Task 261118-lmm: Six-Cell CI Matrix and Main-Only Push CI Summary

**Test Matrix cut to six cells (Linux 3.10-3.13, macOS 3.10/3.13) with push CI on main only, contract tests re-pinned, and every CI doc aligned**

## Performance

- **Duration:** 7 min
- **Started:** 2026-11-18T15:39:59Z
- **Completed:** 2026-11-18T15:47:23Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- `.github/workflows/test-matrix.yml` now triggers on `push: branches: [main]` plus `pull_request`, and the test job's matrix carries two `exclude` entries (macOS 3.11 and 3.12), producing exactly six cells: Linux 3.10-3.13 and macOS 3.10/3.13.
- `tests/test_ci_workflows.py` pins the new shape: `test_matrix_declares_six_cells` asserts the exact exclusion tuple order via the new `MATRIX_EXCLUSION` regex, and `test_matrix_push_trigger_is_main_only` requires the exact `branches: [main]` flow sequence while still forbidding `tags:`.
- `docs/development.md` (4 statements), `docs/contributing.md` (5 statements incl. the trigger snippet and release gate), `docs/testing.md` (contract bullet, trigger sentence, job description), and the `tests/conftest.py` caplog comment all state six cells and push-on-main plus every pull request.
- Every preserved invariant is byte-unchanged: `fail-fast: false`, per-ref `cancel-in-progress: true`, `timeout-minutes: 30`, `permissions: contents: read`, the SHA-pinned `astral-sh/setup-uv`, the frozen sync with both extras, the color-stripping full-suite run, and the Python 3.12 lint job.
- Full quality gates green under `uv run --frozen --extra dev --extra embed`: ruff check, ruff format --check, and the full pytest suite (3251 passed, 1 skipped, 95.08% coverage).

## Task Commits

Each task was committed atomically:

1. **Task 1: Switch push CI to main only and declare the six-cell matrix, then re-pin the contract tests** - `14d7d24` (chore)
2. **Task 2: Bring every doc and code comment in line with the six-cell, main-push shape** - `e8ab114` (docs)
3. **Task 3: Run the full quality gates and audit scope** - `f665eee` (style)

**Plan metadata:** handled by the orchestrator docs commit (SUMMARY.md left uncommitted per instructions).

_Note: no TDD tasks; commit count measured from the plan ledger (`d5f7afb..f665eee` = 3)._

## Files Created/Modified

- `.github/workflows/test-matrix.yml` - push trigger narrowed to `branches: [main]`; two macOS `exclude` entries added to the test matrix
- `tests/test_ci_workflows.py` - `MATRIX_EXCLUSION` regex; `test_matrix_declares_six_cells` (exact exclusions); `test_matrix_push_trigger_is_main_only` (exact trigger, tags still forbidden)
- `docs/development.md` - release step, workflow table row, PR CI bullet, and coverage note updated to six cells / main-only push
- `docs/contributing.md` - release step, Test Matrix intro, Test bullet cell list, trigger/tag sentence, and release gate updated
- `docs/testing.md` - test_ci_workflows contract bullet, Test Matrix trigger sentence, and `test` job description updated
- `tests/conftest.py` - `_hermetic_sif_logging` docstring no longer cites a cell count

## Decisions Made

- Kept `macos-latest` in the `os:` list and expressed the reduction via `exclude` pairs, so the matrix diff is two small entries and the Linux four-version coverage stays literal.
- The trigger assertion matches the exact contiguous `on:` / `push:` / `branches: [main]` text rather than only requiring a `branches:` key, so a return of the every-branch glob fails the guard.
- Tasks were committed atomically (chore, docs, style) per the executor protocol; the plan's note about leaving the tree for a single quick commit was superseded by the caller's per-task commit instruction.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Formatted the new push-trigger assertion to satisfy ruff format**
- **Found during:** Task 3 (Run the full quality gates and audit scope)
- **Issue:** `ruff format --check` reported `tests/test_ci_workflows.py` would be reformatted; the multi-line `assert (...)` added in Task 1 wrapped one line too far.
- **Fix:** Ran `ruff format tests/test_ci_workflows.py`, collapsing the condition onto the `assert` line while keeping the failure message wrapped.
- **Files modified:** `tests/test_ci_workflows.py`
- **Verification:** `ruff format --check src tests` (237 files already formatted) and `ruff check src tests` (All checks passed); full pytest suite re-ran green afterward.
- **Committed in:** `f665eee` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Formatting-only correction to code produced by this plan; no behavior, scope, or contract change.

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None — the change narrows CI surface (no new endpoints, auth paths, file access, or dependencies; no lock, packaging, or other workflow change).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CI now runs six cells and push-on-main plus pull requests; macOS hosted-runner exposure drops from four cells to two while Linux keeps all four Python versions.
- The six-cell contract is test-pinned, so a future re-expansion or a return of the every-branch push glob fails `tests/test_ci_workflows.py`.
- Constraints honored: publish.yml, docs.yml, pyproject.toml, uv.lock, and milestone archives untouched; no tag, push, publish, or issue edit.

---

*Phase: quick-261118-lmm*
*Completed: 2026-11-18*

## Self-Check: PASSED
