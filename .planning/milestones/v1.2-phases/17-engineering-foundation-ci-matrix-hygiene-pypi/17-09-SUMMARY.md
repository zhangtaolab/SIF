---
phase: 17-engineering-foundation-ci-matrix-hygiene-pypi
plan: 09
subsystem: repository-hygiene
tags: [hygiene, junk-removal, git-index, absence-guards, pytest]

# Dependency graph
requires:
  - phase: 17-08
    provides: "Documentation sweep complete; tests/test_hygiene.py absence-guard suite established (14 tests)"
provides:
  - "Seven tracked junk paths removed from the git index and working tree (4 MagicMock SQLite blobs + 3 stale docsift scratch scripts)"
  - "test_tracked_junk_removed guard over disk existence and `git ls-files`, non-vacuous by construction"
  - "Final ENG-04 gate record: ruff/format/ty green, full suite 1669 passed / 1 skipped @ 95.07% coverage"
affects: [17]

# Actuals (#2632)
actuals:
  tokens: 4968
  tasks: 2
  commits: 1
  plan_head_before: d1382af32832ab61bd7a89e8c55ef555e511fb5b
  plan_head_after: 8e4090dc1fa52b0c5447b31c6adae523d445e203

tech-stack:
  added: []
  patterns:
    - "Git-index absence guard: subprocess `git ls-files` requires a `pyproject.toml` sentinel in the listing so an empty or misrooted result cannot pass vacuously; git-unavailable/unusable skips are explicit, never silent passes"

key-files:
  created: []
  modified:
    - tests/test_hygiene.py
  deleted:
    - MagicMock/mock/4398091296
    - MagicMock/mock/4419046432
    - MagicMock/mock/4419497200
    - MagicMock/mock/4426075504
    - quick_test.py
    - simple_test.py
    - verify_imports.py

key-decisions:
  - "Guard asserts a `pyproject.toml` sentinel in `git ls-files` output so an empty listing cannot satisfy the junk assertions vacuously"
  - "`pytest.skip` with a named reason (not a pass) when git is missing or `git ls-files` fails; disk-existence assertions still run before the skip"
  - "Task 2 is verification-only (no files), so it produced no code commit — consistent with the phase's verification-task convention"

patterns-established:
  - "Tracked-junk guard: literal seven-path list checked on disk, then against the real git index with a project-file sentinel"

requirements-completed: [ENG-04]

coverage:
  - id: D1
    description: "The four MagicMock SQLite blobs and quick_test.py, simple_test.py, verify_imports.py are absent from disk and from `git ls-files`; no `MagicMock/` entry is tracked"
    requirement: ENG-04
    verification:
      - kind: unit
        ref: "tests/test_hygiene.py#test_tracked_junk_removed"
        status: pass
      - kind: integration
        ref: "git ls-files | grep -E '^(MagicMock/|quick_test\\.py$|simple_test\\.py$|verify_imports\\.py$)' (no output)"
        status: pass
      - kind: integration
        ref: "env -u FORCE_COLOR NO_COLOR=1 pytest (1669 passed, 1 skipped, 95.07%)"
        status: pass
    human_judgment: false
  - id: D2
    description: "No live source, test, example, Makefile, or workflow reference imports or invokes the three removed root scratch scripts; the only mentions are the guard's own literal list"
    requirement: ENG-04
    verification:
      - kind: integration
        ref: "git grep -n -E '(quick_test|simple_test|verify_imports)' -- ':!.planning' (only tests/test_hygiene.py literals)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The complete ENG-04 hygiene tree passes every CLAUDE.md quality gate: ruff check, ruff format --check, ty check, and pytest at fail_under=90"
    requirement: ENG-04
    verification:
      - kind: integration
        ref: "ruff check src tests scripts; ruff format --check src tests scripts; ty check src/sif (all green)"
        status: pass
      - kind: integration
        ref: "env -u FORCE_COLOR NO_COLOR=1 pytest (coverage 95.07%, fail_under=90 reached)"
        status: pass
    human_judgment: false

duration: 3min
completed: 2026-11-14
status: complete
---

# Phase 17 Plan 09: Tracked Junk Removal Summary

**Removed the four tracked MagicMock SQLite blobs and the three stale docsift-era scratch scripts, then pinned their absence with a git-index guard that cannot pass vacuously.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-11-14T01:54:50Z
- **Completed:** 2026-11-14T01:58:00Z
- **Tasks:** 2/2
- **Files modified:** 1 (`tests/test_hygiene.py`); 7 deleted

## Accomplishments

- Ran `git ls-files -- MagicMock quick_test.py simple_test.py verify_imports.py` to confirm all seven paths were tracked, then removed exactly those seven with `git rm` (D-12 scope: genuinely tracked junk only). No other path was touched.
- Removed the now-empty `MagicMock/mock` and `MagicMock/` working-tree directories so no untracked residue survives.
- Added `test_tracked_junk_removed` to `tests/test_hygiene.py`: asserts none of the seven paths exists on disk, and asserts the real `git ls-files` listing contains none of them and no `MagicMock/` entry. The listing must contain `pyproject.toml`, so an empty or misrooted result fails instead of passing vacuously; if git is unavailable/unusable the test skips with a named reason.
- Proved the end-to-end ENG-04 baseline on the final tree: ruff check, ruff format --check, ty check, and the full suite all green.

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove the seven tracked junk paths and guard their absence (D-12)** - `8e4090d` (chore)
2. **Task 2: Prove the ENG-04 hygiene baseline end-to-end** - verification-only task (no files); evidence recorded below

**Plan metadata:** committed separately after this summary (docs: complete 17-09 plan)

## Verification Evidence (Task 2)

All commands run from the repo root at HEAD `8e4090d`, dev branch:

| Command | Outcome |
|---------|---------|
| `test -z "$(git ls-files -- MagicMock quick_test.py simple_test.py verify_imports.py)"` | exit 0, no output |
| `git ls-files \| grep -E '^(MagicMock/\|quick_test\.py$\|simple_test\.py$\|verify_imports\.py$)'` | no output (grep exit 1 = no match) |
| `git grep -n -E "(quick_test\|simple_test\|verify_imports)" -- ':!.planning'` | only the guard's own literal list in `tests/test_hygiene.py`; no live import or invocation |
| `env -u FORCE_COLOR NO_COLOR=1 pytest tests/test_hygiene.py -x -q --no-cov` | 15 passed |
| `ruff check src tests scripts` | All checks passed |
| `ruff format --check src tests scripts` | 195 files already formatted |
| `ty check src/sif` | All checks passed |
| `env -u FORCE_COLOR NO_COLOR=1 pytest` | 1669 passed, 1 skipped, 95.07% coverage (fail_under=90 reached) |

## Files Created/Modified

- `tests/test_hygiene.py` - `JUNK_PATHS` literal list, `_tracked_files()` helper (explicit skip when git cannot report), and `test_tracked_junk_removed`
- `MagicMock/mock/{4398091296,4419046432,4419497200,4426075504}` - deleted (4 x 128 KB identical tracked SQLite snapshots; blob evidence in 17-RESEARCH.md)
- `quick_test.py`, `simple_test.py` - deleted (stale docsift-era scripts; `simple_test.py` referenced nonexistent `.pre-commit-config.yaml` and `.github/workflows/ci.yml`)
- `verify_imports.py` - deleted (stale docsift import list including removed classes)

## Decisions Made

- The git-index half of the guard asserts a `pyproject.toml` sentinel is present in `git ls-files` output. Without it, a mistargeted cwd or empty listing would satisfy "no junk tracked" vacuously.
- Git absence is handled by `pytest.skip` with a named reason rather than `return`, so a skip is visibly reported and never counted as a pass. Disk-existence assertions run first and always execute.
- Task 2 changed no files by design, so it has no code commit; its evidence is the table above, matching the phase's prior verification-task convention (17-03, 17-04).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- ENG-04 is now fully proven on the hygiene tree: dead layers absent (17-01), phantom pre-commit/docs references gone (17-04/17-08), tracked junk removed and guarded, and every CLAUDE.md gate green.
- Full gate state: 1669 passed, 1 skipped @ 95.07% coverage (fail_under=90); `ruff check src tests scripts`, `ruff format --check src tests scripts`, and `ty check src/sif` all green.
- Remaining phase-17 plans without summaries: 17-06, 17-07. This plan depends only on 17-08 and did not touch their surfaces.

---
*Phase: 17-engineering-foundation-ci-matrix-hygiene-pypi*
*Completed: 2026-11-14*

## Self-Check: PASSED

- tests/test_hygiene.py: FOUND
- 17-09-SUMMARY.md: FOUND
- Commit 8e4090d: FOUND
