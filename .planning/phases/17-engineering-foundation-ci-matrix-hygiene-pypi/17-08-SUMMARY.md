---
phase: 17-engineering-foundation-ci-matrix-hygiene-pypi
plan: 08
subsystem: documentation
tags: [documentation, hygiene, absence-guards, pytest, pre-commit, verify-markers]

# Dependency graph
requires:
  - phase: 17-01
    provides: "Deleted sif.models.search / sif.search.strategy / sif.database.migrations and the tests/test_hygiene.py absence-guard shape"
provides:
  - "Dead-layer prose removed from docs/architecture.md, docs/development.md, docs/models.md, docs/api-reference.md, and DESIGN.md"
  - "docs/development.md New Search Strategy how-to rewritten around live searchers and sif.core.models"
  - "Phantom pre-commit guidance and its three VERIFY markers removed; bandit VERIFY marker retained"
  - "Four documentation guards in tests/test_hygiene.py (dead literals, pre-commit target text, VERIFY markers, bandit retention)"
affects: [17-09, 20-metadata-filtering, 21-scale-maintenance, 22-mcp-sdk-v2]

# Actuals (#2632)
actuals:
  tokens: 8718
  tasks: 2
  commits: 2
  plan_head_before: f9984355dde7ff6282a46e03a2a5de17bf891616
  plan_head_after: 2926b9f1696d1f63a4a3e6d5164398cb0f5da34a

tech-stack:
  added: []
  patterns:
    - "Documentation absence guard: scan docs/**/*.md (changelog excluded) plus DESIGN.md, skip the guard by resolved path, fail with every literal/path offender"

key-files:
  created: []
  modified:
    - docs/architecture.md
    - docs/development.md
    - docs/models.md
    - docs/api-reference.md
    - docs/testing.md
    - docs/contributing.md
    - DESIGN.md
    - tests/test_docs.py
    - tests/test_hygiene.py

key-decisions:
  - "Extended the plan-17-01 resolved-path absence helper to docs rather than duplicating a scan; docs/changelog.md is exempt by resolved path"
  - "Strengthened test_bandit_verify_marker_retained to assert exactly one docs VERIFY marker remains and that it names bandit"
  - "Removed the stale models/search.py tree entries in docs/architecture.md and DESIGN.md alongside the migrations.py/strategy.py entries, since that module was also deleted in 17-01"

patterns-established:
  - "Docs absence guard: literal list covers dotted imports, slash paths, and bare name.py tree entries in one scan"

requirements-completed: [ENG-04]

coverage:
  - id: D1
    description: "Hand-maintained docs no longer name a deleted layer: no sif.models.search, sif.search.strategy, MigrationManager, SearchStrategy, SearchContext, Searchable, compute_rrf_score, CURRENT_SCHEMA_VERSION, bare migrations.py/strategy.py tree entry, or 'legacy migration module' in docs (changelog exempt) or DESIGN.md"
    requirement: ENG-04
    verification:
      - kind: unit
        ref: "tests/test_hygiene.py#test_docs_do_not_describe_dead_layers"
        status: pass
      - kind: integration
        ref: "env -u FORCE_COLOR NO_COLOR=1 pytest (1655 passed, 1 skipped, 95.07%)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Live-layer documentation survives and the search-extension how-to points at the live path: sif.core.models SearchOptions docs remain, and docs/development.md describes a searcher module returning SearchResult and wired through SearchPipeline/HybridSearcher with no ABC/search_batch contract"
    requirement: ENG-04
    verification:
      - kind: unit
        ref: "tests/test_docs.py#TestDocsCodeBlocks::test_python_blocks_are_valid_syntax"
        status: pass
      - kind: unit
        ref: "tests/test_hygiene.py#test_docs_do_not_describe_dead_layers"
        status: pass
    human_judgment: false
  - id: D3
    description: "No docs file instructs a contributor to run make pre-commit, pre-commit install, or pre-commit autoupdate; tests/test_docs.py SKIP_COMMAND_PATTERNS drops pre-commit install"
    requirement: ENG-04
    verification:
      - kind: unit
        ref: "tests/test_hygiene.py#test_docs_do_not_mention_pre_commit_target"
        status: pass
      - kind: unit
        ref: "tests/test_docs.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "Exactly one docs VERIFY marker remains and it is the bandit marker in docs/testing.md; all three pre-commit VERIFY markers are cleared"
    requirement: ENG-04
    verification:
      - kind: unit
        ref: "tests/test_hygiene.py#test_pre_commit_verify_markers_cleared"
        status: pass
      - kind: unit
        ref: "tests/test_hygiene.py#test_bandit_verify_marker_retained"
        status: pass
    human_judgment: false

duration: 9min
completed: 2026-11-14
status: complete
---

# Phase 17 Plan 08: Documentation Sweep Summary

**Removed every dead-layer reference from the seven hand-maintained docs, rewrote the search-extension how-to around the live searchers, deleted the phantom pre-commit guidance and its VERIFY markers, and pinned all of it with four documentation guards.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-11-14T01:27:04Z
- **Completed:** 2026-11-14T01:36:00Z
- **Tasks:** 2/2
- **Files modified:** 9

## Accomplishments

- Scrubbed `sif.models.search`, `sif.search.strategy`, and `MigrationManager` prose from `docs/architecture.md`, `docs/api-reference.md`, `docs/models.md`, and `DESIGN.md`, including interface blocks, tree entries, the seams row, and the RRF `compute_rrf_score` subsection.
- Rewrote `docs/development.md`'s "New Search Strategy" how-to around the live path: a searcher module under `src/sif/search/` accepting `SearchOptions` and returning `SearchResult` from `sif.core.models`, wired through `HybridSearcher`/`SearchPipeline`; removed the MigrationManager schema bullet and the deleted `test_migrations.py` mention.
- Deleted the phantom `make pre-commit` / `pre-commit install` / `pre-commit autoupdate` guidance from `docs/testing.md`, `docs/development.md`, and `docs/contributing.md`, clearing three pre-commit VERIFY markers while retaining the bandit marker.
- Added `test_docs_do_not_describe_dead_layers`, `test_docs_do_not_mention_pre_commit_target`, `test_pre_commit_verify_markers_cleared`, and `test_bandit_verify_marker_retained` to `tests/test_hygiene.py`; removed `pre-commit install` from `tests/test_docs.py` `SKIP_COMMAND_PATTERNS`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove dead-layer documentation end-to-end and guard the docs** - `858f9ee` (docs)
2. **Task 2: Remove phantom pre-commit documentation and clear the VERIFY markers** - `2926b9f` (docs)

**Plan metadata:** committed separately after this summary (docs: complete 17-08 plan)

## Files Created/Modified

- `docs/architecture.md` - dead intro clause, `models/search.py`/`migrations.py`/`strategy.py` tree entries, SearchStrategy interface block, legacy migration phrase, MigrationManager paragraph, and seams row removed
- `docs/development.md` - MigrationManager bullet and `test_migrations.py` mention removed; "New Search Strategy" rewritten; pre-commit caveat, table text/row, and VERIFY paragraph removed
- `docs/models.md` - validation-rules sentence now names only surviving core models (`CollectionBase.name`, `ContextBase.content`)
- `docs/api-reference.md` - dead SearchType/SearchQuery/SearchResult/SearchResponse and SearchContext/SearchStrategy docs removed; live `sif.core.models.SearchOptions` and RRFFusion docs kept; RRF import trimmed; custom-strategy example deleted
- `docs/testing.md` - pre-commit install sentence and its VERIFY marker removed; SKIP_COMMAND_PATTERNS prose updated; bandit VERIFY marker retained
- `docs/contributing.md` - pre-commit table text and paragraph plus its VERIFY marker removed
- `DESIGN.md` - Strategy Pattern location points at the live searchers; `models/search.py`/`migrations.py`/`strategy.py` tree entries and SearchStrategy interface block removed
- `tests/test_docs.py` - `pre-commit install` dropped from `SKIP_COMMAND_PATTERNS`
- `tests/test_hygiene.py` - dead-doc literals list, docs scan helpers, and four documentation guards added

## Decisions Made

- Extended the plan-17-01 resolved-path absence scan helper to documentation files instead of duplicating a scan; `docs/changelog.md` is exempt by resolved path because release history legitimately names removed items.
- Strengthened the bandit guard to assert exactly one docs VERIFY marker remains (not merely that bandit appears), matching the acceptance criterion.
- Left `docs/cli-reference.md` and `docs/configuration.md` untouched as generator-owned files.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed stale `models/search.py` tree entries from docs/architecture.md and DESIGN.md**
- **Found during:** Task 1 (dead-layer documentation removal)
- **Issue:** Both trees still listed `search.py # Search query and result models` under `models/`, but plan 17-01 deleted `src/sif/models/search.py`; leaving the row would keep documenting a nonexistent module.
- **Fix:** Deleted the `models/search.py` tree row in both files (the plan named only the `migrations.py`/`strategy.py` rows).
- **Files modified:** docs/architecture.md, DESIGN.md
- **Verification:** `test_docs_do_not_describe_dead_layers`, `tests/test_docs.py`, and the full suite pass; grep for the scanned literals returns nothing outside docs/changelog.md.
- **Committed in:** `858f9ee` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** The extra row removal is the same dead-layer sweep; no scope creep.

## Issues Encountered

- `ruff format --check` flagged `tests/test_hygiene.py` after the Task 2 guard additions; ran `ruff format tests/test_hygiene.py`, then re-ran the hygiene/docs tests and the format check green. No behavior change.

## Deferred Items

Logged to `deferred-items.md` in the phase directory: `docs/testing.md` still describes the deleted `tests/factories.py` and `tests/unit/test_search.py` plus the removed `sample_search_options`/`SearchOptionsFactory` helpers. Those references are outside this plan's enumerated dead-layer literal sweep and pre-commit scope.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Documentation now matches the post-17-01 codebase; the four guards keep the deleted layers and phantom pre-commit flow from reappearing.
- Full gate state: 1655 passed, 1 skipped @ 95.07% coverage (fail_under=90); `ruff check src tests scripts`, `ruff format --check src tests scripts`, and `ty check src/sif` all green.
- Plan 17-09 (tracked junk) remains the last plan in the phase.

---
*Phase: 17-engineering-foundation-ci-matrix-hygiene-pypi*
*Completed: 2026-11-14*

## Self-Check: PASSED

- tests/test_hygiene.py: FOUND
- 17-08-SUMMARY.md: FOUND
- Commits: 858f9ee, 2926b9f both FOUND
