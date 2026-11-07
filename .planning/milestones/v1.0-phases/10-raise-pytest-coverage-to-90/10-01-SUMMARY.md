---
phase: 10-raise-pytest-coverage-to-90
plan: 01
subsystem: testing
tags: [pytest, coverage, dead-code, cleanup]

requires:
  - phase: 09-mcp-server-implementation
    provides: Unified MCP and CLI implementation whose regression suite protects this deletion.
provides:
  - Measured post-deletion coverage baseline of 81.48% (5320 statements, 985 missed).
  - Pruned cli/formatters.py and utils/text.py with only approved live symbols.
  - Verified Wave-2 per-file gaps and unchanged live CLI imports.
affects:
  - All Wave-2 coverage plans, especially 10-02 CLI coverage.
  - Final 10-07 fail_under gate.

actuals:
  tokens: 6703
  tasks: 2
  commits: 2
plan_head_before: 119e60423326a6129e5325956c4218a43e8b5cd4
plan_head_after: ed4ad73156931b71526da60d851f1e97ec4f0183

tech-stack:
  added: []
  patterns: [dead-code evidence-gated deletion (Pattern 4)]

key-files:
  created: []
  modified:
    - src/sif/cli/formatters.py
    - src/sif/utils/text.py
    - src/sif/utils/__init__.py

key-decisions:
  - "Apply D-01 exactly: remove the approved dead-code cluster without adding tests for deleted symbols or changing live behavior."
  - "Keep pyproject.toml free of fail_under and coverage exclusions; only 10-07 may install the final gate."

patterns-established:
  - "Pattern 4: delete only the evidence-approved cluster, then prove live imports, the full suite, coverage, and generated docs."

requirements-completed: [T-10-1]

coverage:
  - id: D1
    description: Delete the approved D-01 dead-code cluster while preserving live formatter imports and utility exports.
    requirement: T-10-1
    verification:
      - kind: integration
        ref: "D-01 import/AST probe plus env -u FORCE_COLOR NO_COLOR=1 pytest -q"
        status: pass
      - kind: other
        ref: "ruff check src tests && ruff format --check src tests"
        status: pass
    human_judgment: false
  - id: D2
    description: Re-baseline full-suite line coverage at or above 81% with unchanged generated docs and coverage configuration.
    requirement: T-10-1
    verification:
      - kind: integration
        ref: "env -u FORCE_COLOR NO_COLOR=1 pytest --cov=src/sif (690 passed, 0 failed)"
        status: pass
      - kind: other
        ref: "python -m coverage report --fail-under=81 (5320 statements, 985 missed, 81.48%)"
        status: pass
      - kind: other
        ref: "make docs-generate && test -z \"$(git status --porcelain -- docs/cli-reference.md docs/configuration.md)\""
        status: pass
    human_judgment: false

duration: 6min
completed: 2026-11-05
status: complete
---

# Phase 10 Plan 01: Dead-Code Deletion and Coverage Re-Baseline Summary

**Deleted the D-01 dead-code cluster and re-baselined coverage from 78% to 81.48% (5320 statements, 985 missed), with 690 tests passing and live CLI imports intact.**

## Performance

- **Duration:** 6 minutes
- **Started:** 2026-11-05T17:50:54Z
- **Completed:** 2026-11-05T17:56:23Z
- **Tasks:** 2/2
- **Files modified:** 4 source files (one deleted, three pruned), plus this summary and planning state.
- **Source diff:** 1 insertion, 548 deletions.

## Accomplishments

- Deleted `src/sif/cli/config.py` outright and removed its unused configuration classes and global accessors.
- Reduced `src/sif/cli/formatters.py` to `prepend_line_numbers` and `add_line_numbers_to_results`; both live CLI consumers still import successfully.
- Reduced `src/sif/utils/text.py` to `count_tokens` and `extract_code_blocks`; `sif.utils` now re-exports only `count_tokens` from that module.
- Passed the tracer feedback gate with a second complete verification run before starting Task 2.
- Measured the canonical full suite at **690 passed, 0 failed**, with **5320 statements, 985 missed, 81.48% line coverage** (displayed TOTAL: 81%).
- Kept `pyproject.toml`, all test files, and both generator-owned documents unchanged; `make docs-generate` produced no diff.

## Measured Coverage Baseline

| Metric | Pre-deletion planner baseline | Measured post-deletion |
|---|---:|---:|
| Passed / failed | 690 / 0 | **690 / 0** |
| Statements | 5596 | **5320** |
| Missed | 1220 | **985** |
| TOTAL | 78% | **81% displayed; 81.48% precise** |

The denominator shrank by 276 statements and missed lines by 235. The `python -m coverage report --fail-under=81` and `--format=total` commands both passed, the latter reporting `81`.

## Wave-2 Per-File Gaps

These are the measured live gaps from the post-deletion full-suite report, in descending missed-statement order. They replace the pre-deletion inventory for Wave 2.

| File | Statements | Missed | Coverage |
|---|---:|---:|---:|
| `src/sif/cli/commands/collection.py` | 234 | 131 | 44% |
| `src/sif/search/rerank.py` | 214 | 82 | 62% |
| `src/sif/cli/commands/search.py` | 356 | 76 | 79% |
| `src/sif/database/repositories.py` | 173 | 47 | 73% |
| `src/sif/indexing/parser.py` | 78 | 38 | 51% |
| `src/sif/cli/main.py` | 123 | 38 | 69% |
| `src/sif/core/context.py` | 73 | 37 | 49% |
| `src/sif/models/download.py` | 69 | 35 | 49% |
| `src/sif/cli/commands/get.py` | 122 | 34 | 72% |
| `src/sif/database/database.py` | 85 | 32 | 62% |
| `src/sif/embedding/cache.py` | 77 | 31 | 60% |
| `src/sif/indexing/chunker.py` | 98 | 28 | 71% |
| `src/sif/utils/logging.py` | 62 | 26 | 58% |
| `src/sif/mcp/transports/http.py` | 114 | 26 | 77% |
| `src/sif/database/migrations.py` | 37 | 24 | 35% |
| `src/sif/cli/commands/index.py` | 216 | 24 | 89% |
| `src/sif/core/collection.py` | 74 | 23 | 69% |
| `src/sif/mcp/server.py` | 77 | 22 | 71% |
| `src/sif/cli/commands/mcp.py` | 46 | 20 | 57% |
| `src/sif/utils/paths.py` | 30 | 15 | 50% |

The remaining files account for 139 missed statements. Reaching 90% requires at most 532 missed statements at the current denominator, so Wave 2/3 must eliminate at least 453 additional missed statements through behavioral tests or separately evidence-gated D-02 deletions.

## Task Commits

1. **Task 1: Delete the complete D-01 dead-code cluster and prove the live CLI path** — `caaf0a5c58cc203ac365903ab3b3a3d8f0af7752` (refactor)
2. **Task 2: Re-baseline coverage and verify deletion guardrails** — `ed4ad73156931b71526da60d851f1e97ec4f0183` (test; empty atomic verification commit because Task 2 changed no source files)

## Files Created/Modified

- `src/sif/cli/config.py` — **deleted** as the approved D-01 unused configuration module.
- `src/sif/cli/formatters.py` — retained only the two live line-number helpers and `typing.Any`; now 13 statements at 100% coverage.
- `src/sif/utils/text.py` — retained only `count_tokens`, `extract_code_blocks`, `re`, and `Any`.
- `src/sif/utils/__init__.py` — limited the text import and exports to live symbols.
- `.planning/phases/10-raise-pytest-coverage-to-90/10-01-SUMMARY.md` — measured baseline and Wave-2 handoff.

No test files were created or modified.

## Decisions Made

- Followed D-01 exactly, including the intentional deletion of `src/sif/cli/config.py`; no additional D-02 deletion candidates were pursued.
- Preserved the surviving helper implementations and `tests/unit/cli/test_formatters.py` unchanged.
- Left coverage configuration untouched under D-04: there is no `[tool.coverage.report]`, `fail_under`, `exclude_lines`, or `exclude_also`.

## Deviations from Plan

None - plan executed exactly as written. The plan sanctioned deletion of `src/sif/cli/config.py`; the deletion was verified as the only removed file in Task 1.

## Issues Encountered

The full suite emitted 18 existing `ResourceWarning` messages about unclosed SQLite connections. They did not fail the suite and are outside this deletion-only plan's scope; no source or test changes were made for them.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Wave 2 can start from the measured **81.48% / 5320 statements / 985 missed** baseline. Plan 10-02's immediate targets remain `collection.py` (131 missed), `main.py` (38), and `get.py` (34). No blockers, stubs, coverage exemptions, package installs, authentication gates, or manual setup are outstanding from this plan.

## Self-Check: PASSED

- Key surviving files exist: `src/sif/cli/formatters.py`, `src/sif/utils/text.py`, `src/sif/utils/__init__.py`; `src/sif/cli/config.py` is absent.
- Both task commits are ancestors of HEAD; the measured ledger records 2 commits from `119e604` through `ed4ad73`.
- Task 1 AST/export/import acceptance checks: PASS; full `pytest -q`: PASS (690 passed, 0 failed); no test-file changes: PASS.
- Task 2 `ruff check`, `ruff format --check`, canonical `pytest --cov=src/sif`, `coverage report --fail-under=81`, and `coverage report --format=total`: PASS.
- Generated docs after `make docs-generate`: empty scoped porcelain result. Coverage configuration and `pyproject.toml`: unchanged, no report section or exclusions.
- Requirement readiness was checked explicitly: `T-10-1` remains blocked by the shared-ID gate because all seven Phase 10 plans declare it; it was not prematurely marked complete.

---
*Phase: 10-raise-pytest-coverage-to-90*
*Completed: 2026-11-05*
