---
phase: 10-raise-pytest-coverage-to-90
plan: 05
subsystem: testing
tags: [pytest, coverage, core, downloader, utils]

requires:
  - phase: 10-raise-pytest-coverage-to-90
    plan: 01
    provides: Post-deletion coverage baseline and test isolation conventions.
provides:
  - ContextManager and CollectionManager behavioral coverage through repository Protocol doubles.
  - ModelDownloader cache and ModelScope boundary coverage without network or real home writes.
  - Logging, path, progress, and surviving text helper coverage with process-state restoration.
affects:
  - Phase 10 plan 10-07 coverage tollgate.
  - Custom logging handler formatting and indeterminate Rich progress lifecycle.

actuals:
  tokens: 13123
  tasks: 3
  commits: 3
plan_head_before: ccfb9c97da43a0b2d60f1af0428cf8952166ed70
plan_head_after: eae592b

tech-stack:
  added: []
  patterns: [DI-with-mocks (Pattern 5), mocked network, scoped process-state restoration]

key-files:
  created:
    - tests/unit/core/__init__.py
    - tests/unit/core/test_context.py
    - tests/unit/core/test_collection_entity.py
    - tests/unit/models/__init__.py
    - tests/unit/models/test_download.py
    - tests/unit/utils/__init__.py
    - tests/unit/utils/test_logging.py
    - tests/unit/utils/test_paths.py
    - tests/unit/utils/test_progress.py
    - tests/unit/utils/test_text.py
  modified:
    - src/sif/utils/logging.py
    - src/sif/utils/progress.py

key-decisions:
  - "Use real Context and Collection entities with Protocol-conforming repository doubles so tests assert state transitions and aggregates rather than mock echoes."
  - "Inject ModelScope modules with explicit teardown and place every downloader cache beneath tmp_path, including the HOME-monkeypatched default."
  - "Apply computed formatters to custom logging handlers and omit Rich bar/percentage columns for indeterminate progress; both are narrow defect repairs exposed by new behavior tests."

requirements-completed: [T-10-1]

coverage:
  - id: D1
    description: ContextManager create/update/list/search aggregation and CollectionManager/entity behavior use repository Protocol doubles and real domain entities.
    requirement: T-10-1
    verification:
      - kind: integration
        ref: "tests/unit/core: 25 passed; deterministic global/collection/path ordering and missing-ID errors asserted"
        status: pass
      - kind: other
        ref: ".planning/tmp/10-05-context.xml and 10-05-collection.xml: both line-rate=1; thresholds >= 0.80"
        status: pass
    human_judgment: false
  - id: D2
    description: ModelDownloader cached/force/revision/quiet/error behavior, convenience methods, metadata, listing, and clearing execute with mocked ModelScope and tmp_path caches.
    requirement: T-10-1
    verification:
      - kind: integration
        ref: "tests/unit/models/test_download.py: 16 passed; exact snapshot_download and HubApi interactions asserted"
        status: pass
      - kind: other
        ref: ".planning/tmp/10-05-download.xml models/download.py line-rate=1; threshold >= 0.80"
        status: pass
    human_judgment: false
  - id: D3
    description: Logging, paths, progress, and surviving text helpers have observable edge coverage with environment, handler, and module isolation.
    requirement: T-10-1
    verification:
      - kind: integration
        ref: "tests/unit/utils: 37 passed; empty/Unicode text, zero-total progress, quiet logging, and real symlink paths asserted"
        status: pass
      - kind: other
        ref: ".planning/tmp/10-05-{logging,paths,progress,text}.xml: all four line-rate=1; thresholds >= 0.85"
        status: pass
    human_judgment: false
  - id: D4
    description: The full quality suite remains green and coverage improves without pyproject coverage configuration changes.
    requirement: T-10-1
    verification:
      - kind: other
        ref: "ruff check src tests; ruff format --check src tests: PASS (146 files)"
        status: pass
      - kind: integration
        ref: "env -u FORCE_COLOR NO_COLOR=1 pytest --cov=src/sif: 875 passed, 0 failed; .planning/tmp/10-05-full.xml TOTAL line-rate=0.9348"
        status: pass
    human_judgment: false

duration: 11min
completed: 2026-11-05
status: complete
---

# Phase 10 Plan 05: Core Services, Downloader, and Utils Coverage Summary

**Raised full-suite coverage from 90.89% to 93.48% with 78 new behavior tests; all seven target files reached 100%, ModelScope/network/home boundaries remained isolated, and the tests exposed and proved fixes for custom logging formatter and indeterminate Rich progress defects.**

## Performance

- **Duration:** 11 minutes (661 seconds)
- **Started:** 2026-11-05T19:35:02Z
- **Completed:** 2026-11-05T19:46:03Z
- **Tasks:** 3/3
- **Files modified:** 10 new test files/package markers plus 2 production utility modules (12 code/test files), plus planning state.
- **Realized code/test diff:** 52,491 characters across current file content (13,123 chars/4 actual tokens); 1,161 insertions and 7 deletions.
- **Full suite:** 875 passed, 0 failed in 13.97 seconds.

## Accomplishments

- Added the `tests/unit/core` package with 25 tests covering ContextManager create/update/list/search aggregation and CollectionManager/entity behavior using real entities and Protocol doubles.
- Proved the tracer end-to-end before expansion by rerunning core behavior and both focused 80% source gates; context and collection each reached 100%.
- Added 16 ModelDownloader tests covering default/custom cache paths, cached short circuit, force/revision/quiet/error branches, all convenience methods, Hub metadata, listing, and clearing.
- Added 37 utility tests for logging configurations and suppression, real path normalization and overridden directories, Rich/Null progress lifecycles, and tokenizer/code-block edge behavior.
- Restored logging handlers/global quiet state and scoped ModelScope/transformers injections under D-07; no real network client, real home cache, or persistent path outside tmp_path was used.
- Fixed custom logging handler formatting and invalid Rich `None` columns, then passed all seven focused gates at 100% and the complete quality suite.

## Measured Coverage Movement

| File | 10-04 full suite | 10-05 full suite | Missed change |
|---|---:|---:|---:|
| `src/sif/core/context.py` | 49% (37 missed / 73) | **100%** (0 missed / 73) | -37 |
| `src/sif/core/collection.py` | 69% (23 missed / 74) | **100%** (0 missed / 74) | -23 |
| `src/sif/models/download.py` | 49% (35 missed / 69) | **100%** (0 missed / 69) | -35 |
| `src/sif/utils/logging.py` | 58% (26 missed / 62) | **100%** (0 missed / 62) | -26 |
| `src/sif/utils/paths.py` | 50% (15 missed / 30) | **100%** (0 missed / 30) | -15 |
| `src/sif/utils/progress.py` | 55% (14 missed / 31) | **100%** (0 missed / 34) | -14 |
| `src/sif/utils/text.py` | 31% (9 missed / 13) | **100%** (0 missed / 13) | -9 |
| **TOTAL** | **90.89%** (486 missed / 5337) | **93.48%** (348 missed / 5340) | **-138** |

The denominator increased by three statements because the narrow Rich progress repair replaced conditional `None` columns with explicit column construction. The canonical XML records 5,340 valid lines, 4,992 covered lines, and `line-rate=0.9348`; terminal output displays TOTAL as 93%.

## Task Commits

1. **Task 1: Prove context service flow and expand collection/entity behavior** — `632f5f7` (test)
2. **Task 2: Cover ModelDownloader with temporary caches and mocked ModelScope** — `9822976` (test)
3. **Task 3: Cover logging, paths, progress, and surviving text helpers** — `eae592b` (test, including two narrow production repairs)

## Files Created/Modified

- `tests/unit/core/__init__.py` — package marker preventing same-basename context collection collisions.
- `tests/unit/core/test_context.py` — ContextManager service flows, exact aggregate ordering, error paths, and entity updates.
- `tests/unit/core/test_collection_entity.py` — CollectionManager CRUD/path operations and entity metadata/indexing transitions.
- `tests/unit/models/__init__.py` — downloader test package marker.
- `tests/unit/models/test_download.py` — temporary-cache and scoped-mocked-ModelScope downloader suite.
- `tests/unit/utils/__init__.py` — utility test package marker.
- `tests/unit/utils/test_logging.py` — environment/quiet/handler/suppression behavior with complete state restoration.
- `tests/unit/utils/test_paths.py` — real symlink/relative/error paths and temporary platform directory overrides.
- `tests/unit/utils/test_progress.py` — determinate, zero-total, indeterminate, inactive, and disabled progress behavior.
- `tests/unit/utils/test_text.py` — tokenizer/fallback, empty/Unicode, and fenced-code extraction behavior.
- `src/sif/utils/logging.py` — applies computed formatters to caller-provided handlers as well as default handlers.
- `src/sif/utils/progress.py` — constructs only valid Rich columns for indeterminate tasks.

## Decisions Made

- Kept core tests at the domain-service layer rather than duplicating existing CLI context tests; repository doubles return real domain entities.
- Used source-module ModelScope patches through a fixture that restores every injected module key, including when an optional dependency was already present.
- Documented Unicode behavior as Python code-point length divided by four and code extraction as regex text semantics; no grapheme or normalization rules were redefined.
- Used real Rich progress instances to expose lifecycle defects instead of asserting mock interactions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Applied computed formatters to custom logging handlers**
- **Found during:** Task 3.
- **Issue:** `setup_logging` constructed the requested formatter but only installed it on internally created handlers, leaving caller-provided handlers unformatted.
- **Fix:** Moved `setFormatter(formatter)` outside the default-handler branch while preserving custom handler identity.
- **Files modified:** `src/sif/utils/logging.py`, `tests/unit/utils/test_logging.py`.
- **Verification:** INFO, DEBUG, and custom-format tests now assert the actual handler formatter; all 37 utility tests and the full suite pass.
- **Commit:** `eae592b`.

**2. [Rule 1 - Bug] Omitted invalid Rich columns for indeterminate progress**
- **Found during:** Task 3.
- **Issue:** Zero or `None` totals supplied `None` bar/percentage columns, causing Rich to raise `AttributeError` during task rendering.
- **Fix:** Built the column list conditionally and passed only real columns to `RichProgress`.
- **Files modified:** `src/sif/utils/progress.py`, `tests/unit/utils/test_progress.py`.
- **Verification:** Zero and unknown totals start, advance actual counts, and finish without errors; all utility and full-suite tests pass.
- **Commit:** `eae592b`.

**Total deviations:** 2 auto-fixed production behavior defects.
**Impact on plan:** Narrow, test-proven repairs completed the required behavior coverage without API redesign, coverage suppression, new dependencies, or architectural changes. Both were recorded in `.planning/WINDOWS.md` and marked fixed after the full suite passed.

## Issues Encountered

- The full suite emitted 73 warnings, including existing SQLite resource warnings; no new failure or unresolved warning was introduced by this plan. Unrelated warnings were left unchanged under the scope boundary.
- No authentication gates, package installs, blockers, known stubs, skipped tests, unrun verification commands, generator-owned doc edits, or user setup occurred.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The next measured starting point is **93.48% (348 missed / 5340 statements)** with **875 passing tests**. All focused thresholds passed: context/collection/download 100% >= 80%, and logging/paths/progress/text 100% >= 85%. `requirements.ready-ids` returned `ready: []`; `T-10-1` remains unmarked because the seven-plan shared-ID gate has not released it. `pyproject.toml` remains untouched and the permanent `fail_under=90` gate remains reserved for plan 10-07.

## Self-Check: PASSED

- Required package markers and test classes exist: `TestContextManager`, `TestCollectionManager`, `TestCollectionEntity`, `TestModelDownloader`, `TestLoggingConfiguration`, `TestPathHelpers`, `TestProgressTracker`, and `TestTextHelpers`.
- Task commits `632f5f7`, `9822976`, and `eae592b` are ancestors of HEAD; the measured ledger records exactly 3 commits from `ccfb9c9` through `eae592b`.
- The automatic tracer feedback gate reran all core behavior and both focused coverage gates before expansion: PASS.
- Focused context, collection, downloader, logging, paths, progress, and text coverage: all 100%; `ruff check src tests`: PASS; `ruff format --check src tests`: PASS (146 files).
- Canonical `env -u FORCE_COLOR NO_COLOR=1 pytest --cov=src/sif`: PASS (875 passed, 0 failed; TOTAL 93.48%).
- `pyproject.toml` unchanged; no business-logic pragmas, coverage exclusions, generator-owned doc edits, new dependencies, real downloads, or persistent paths outside tmp_path.
- Requirement readiness returned `ready: []`; `T-10-1` was not prematurely marked complete.

---
*Phase: 10-raise-pytest-coverage-to-90*
*Completed: 2026-11-05*
