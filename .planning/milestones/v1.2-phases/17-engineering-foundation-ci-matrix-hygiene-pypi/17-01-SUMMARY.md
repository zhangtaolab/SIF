---
phase: 17-engineering-foundation-ci-matrix-hygiene-pypi
plan: 01
subsystem: hygiene
tags: [dead-code-removal, hygiene-guards, makefile, rrf, pytest]

# Dependency graph
requires: []
provides:
  - "Deletion of the three verified-dead layers (sif.models.search, sif.search.strategy, sif.database.migrations)"
  - "tests/test_hygiene.py Wave 0 absence/import/Makefile guard suite (10 guards)"
  - "pre-commit-free Makefile and orphan-free sif.search.rrf / sif.config.constants"
  - "Runnable examples/quickstart.py against live Database/BM25Searcher APIs"
affects: [17-02, 17-03, 17-08, 17-09, 20-metadata-filtering, 21-scale-maintenance]

# Actuals (#2632)
actuals:
  tokens: 12849
  tasks: 3
  commits: 3
  plan_head_before: e78a7d5d712cc311d68fe8135fe548acdd1bce65
  plan_head_after: 223e395be39efd43f96227d78f4ec03904016c82

tech-stack:
  added: []
  patterns:
    - "Text-level absence guards with rglob scans and pytest.fail offender lists"
    - "py_compile subprocess guard for example scripts"

key-files:
  created:
    - tests/test_hygiene.py
  modified:
    - src/sif/models/__init__.py
    - src/sif/database/__init__.py
    - src/sif/config/constants.py
    - src/sif/search/rrf.py
    - tests/conftest.py
    - examples/quickstart.py
    - Makefile
  deleted:
    - src/sif/models/search.py
    - src/sif/search/strategy.py
    - src/sif/database/migrations.py
    - tests/unit/test_search.py
    - tests/unit/database/test_migrations.py
    - tests/factories.py

key-decisions:
  - "Deleted modules, package exports, importers, fixtures, and dependent tests together so the suite keeps collecting"
  - "Removed CURRENT_SCHEMA_VERSION with the dead migration layer (research open question 5)"
  - "Left docs, pyproject/black, and tracked junk untouched — owned by plans 17-08/17-09 and 17-02"
  - "No windows-smoke Makefile target added (plan 17-04 owns it)"

patterns-established:
  - "Absence guard: rglob *.py under src/tests/examples, skip the guard test by resolved path, pytest.fail with every offender"
  - "Example guard: py_compile via subprocess plus source-text assertions on live API names"

requirements-completed: [ENG-04]

coverage:
  - id: D1
    description: "Three dead layers deleted end-to-end with no surviving importers or package exports"
    requirement: ENG-04
    verification:
      - kind: unit
        ref: "tests/test_hygiene.py#test_dead_layers_are_not_importable"
        status: pass
      - kind: unit
        ref: "tests/test_hygiene.py#test_no_dead_search_model_imports"
        status: pass
      - kind: integration
        ref: "env -u FORCE_COLOR NO_COLOR=1 pytest (1622 passed, 1 skipped, 95.04%)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Orphan compute_rrf_score export removed while RRFFusion fusion behavior is unchanged"
    requirement: ENG-04
    verification:
      - kind: unit
        ref: "tests/test_hygiene.py#test_compute_rrf_score_removed"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_rrf.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Phantom pre-commit Makefile flow removed and absent .pre-commit-config.yaml guarded"
    requirement: ENG-04
    verification:
      - kind: unit
        ref: "tests/test_hygiene.py#test_makefile_has_no_pre_commit_target"
        status: pass
      - kind: unit
        ref: "tests/test_hygiene.py#test_pre_commit_config_absent"
        status: pass
    human_judgment: false
  - id: D4
    description: "examples/quickstart.py runs against live Database/BM25Searcher APIs instead of deleted layers"
    requirement: ENG-04
    verification:
      - kind: unit
        ref: "tests/test_hygiene.py#test_quickstart_example_compiles"
        status: pass
    human_judgment: false
  - id: D5
    description: "Orphaned CURRENT_SCHEMA_VERSION constant removed with the migration layer"
    requirement: ENG-04
    verification:
      - kind: unit
        ref: "tests/test_hygiene.py#test_current_schema_version_removed"
        status: pass
    human_judgment: false

duration: 11min
completed: 2026-11-13
status: complete
---

# Phase 17 Plan 01: Repo Hygiene Core Summary

**Deleted three verified-dead layers (search models, search strategy, MigrationManager), the orphan RRF export, and the phantom pre-commit Makefile flow, all pinned by a new 10-test hygiene guard suite.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-11-13T08:37:50Z
- **Completed:** 2026-11-13T08:48:49Z
- **Tasks:** 3/3
- **Files modified:** 14 (8 modified/created, 6 deleted)

## Accomplishments

- Removed `src/sif/models/search.py`, `src/sif/search/strategy.py`, and `src/sif/database/migrations.py` together with every export, importer, fixture, and dependent test, so the suite collects and passes end-to-end.
- Cleared the `__all__` surfaces in `sif.models` and `sif.database`, deleted the orphan `compute_rrf_score`, and removed the now-orphaned `CURRENT_SCHEMA_VERSION`.
- Created `tests/test_hygiene.py` with 10 absence/import/compile/Makefile guards that fail loudly with every offending path on reintroduction.
- Rewrote `examples/quickstart.py` database and search demos against the live `Database` and `BM25Searcher` APIs (the old import never resolved).
- Left the Makefile honest: no `pre-commit` target, install hook, autoupdate, or help line; `black` dropped from the info grep.

## Task Commits

Each task was committed atomically:

1. **Task 1: Delete sif.models.search and sif.search.strategy end-to-end and create the hygiene guard suite** - `d44f5d8` (refactor)
2. **Task 2: Delete the remaining dead layer, orphan RRF export, and dead example code** - `4f6506f` (refactor)
3. **Task 3: Remove the phantom pre-commit Makefile target** - `223e395` (chore)

**Plan metadata:** committed separately after this summary (docs: complete 17-01 plan)

## Files Created/Modified

- `tests/test_hygiene.py` - NEW: 10 ENG-04 absence/import/compile/Makefile guards
- `src/sif/models/__init__.py` - five dead Pydantic search names removed from imports and `__all__`
- `src/sif/database/__init__.py` - `MigrationManager` import and `__all__` entry removed
- `src/sif/config/constants.py` - `CURRENT_SCHEMA_VERSION` and its comment removed
- `src/sif/search/rrf.py` - orphan `compute_rrf_score` deleted; `RRFFusion` untouched
- `tests/conftest.py` - dead `sif.models.search` import and three fixtures removed; color-hermetic block untouched
- `examples/quickstart.py` - database/search examples rewritten against `Database`/`BM25Searcher`
- `Makefile` - pre-commit target/install/autoupdate/help/.PHONY entries and `black` grep removed
- `src/sif/models/search.py` - DELETED
- `src/sif/search/strategy.py` - DELETED
- `src/sif/database/migrations.py` - DELETED
- `tests/unit/test_search.py` - DELETED
- `tests/unit/database/test_migrations.py` - DELETED
- `tests/factories.py` - DELETED

## Decisions Made

- Followed locked decisions D-08 (delete dead layers outright; git history is the archive), D-09 (zero-risk bundle only), and D-12 scope split (docs and tracked junk stay with plans 17-08/17-09).
- Resolved research open question 5 in favor of removing `CURRENT_SCHEMA_VERSION` alongside `migrations.py`.
- No `windows-smoke` Makefile target added — plan 17-04 owns it.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `ruff check` flagged the first `_offenders` helper implementation with PERF401 (manual list comprehension); rewrote it as a comprehension in Task 2. No behavior change; the guard suite was re-run green afterward.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- ENG-04 hygiene base is complete for the plan's scope; plans 17-08 (documentation sweep) and 17-09 (tracked junk) remain explicitly out of this plan's scope.
- `tests/test_hygiene.py` is ready for further guard expansion by later plans (e.g. pyproject/black guards belong to plan 17-02's scope).
- Full gate state: 1622 passed, 1 skipped @ 95.04% coverage (fail_under=90); ruff check, ruff format --check, and `ty check src/sif` all green.

---
*Phase: 17-engineering-foundation-ci-matrix-hygiene-pypi*
*Completed: 2026-11-13*

## Self-Check: PASSED

- tests/test_hygiene.py: FOUND
- 17-01-SUMMARY.md: FOUND
- Commits: d44f5d8, 4f6506f, 223e395 all FOUND
