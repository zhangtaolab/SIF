---
phase: 04-advanced-search-pipeline
plan: "06"
subsystem: search
tags: [search, snippets, cli, rich-tables, sqlite, tdd, gap-closure]

requires:
  - phase: 04-advanced-search-pipeline (plans 01-05)
    provides: SmartSnippetExtractor, SearchPipeline prefix routing, query/search rich tables
provides:
  - Snippet column in query_cmd and search_cmd rich tables with first-highlight fallback
  - SearchPipeline._apply_snippets transient content feed (snippet extraction without --full)
  - Snippet coverage on the lex:/vec:/hyde: prefix routes before returning
  - Real-sqlite integration, pipeline unit, and CLI unit tests asserting the snippet flow end to end
affects: [phase-04 verification (SC 7 / SRCH-07), future UI or MCP snippet surfacing]

actuals:
  tokens: 5322
  tasks: 3
  commits: 6

tech-stack:
  added: []
  patterns:
    - "Transient content fetch: pipeline stages read document content for derived fields without mutating SearchResult.content"
    - "rich.markup.escape on document-derived table cells so bracket sequences render literally"

key-files:
  created: []
  modified:
    - src/sif/search/hybrid.py
    - src/sif/cli/commands/search.py
    - tests/unit/search/test_hybrid.py
    - tests/unit/cli/test_search.py
    - tests/integration/test_search_pipeline.py

key-decisions:
  - "_display_snippet guards both snippet and highlights with getattr so dict-shaped rows cannot crash rendering"
  - "TestSnippetDisplay class was created in Task 1 (the plan named it for Task 3, but Task 1's CLI test needed the scaffold) and extended with the three Task 3 behaviors"
  - "Fetched document text is assigned only to a local variable feeding the extractor; result.content stays None without --full (CLI-07 contract preserved by construction)"

patterns-established:
  - "Transient fetch pattern: derived-field pipeline stages may read document content without persisting it into result payloads"

requirements-completed: [SRCH-07]

coverage:
  - id: D1
    description: "Snippet column rendered in query_cmd and search_cmd rich tables, with first-highlight fallback and literal bracket rendering"
    requirement: SRCH-07
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestSnippetDisplay::test_query_table_shows_snippet_column"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestSnippetDisplay::test_query_table_falls_back_to_first_highlight"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestSnippetDisplay::test_search_table_shows_snippet_column"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestSnippetDisplay::test_query_files_output_has_no_table_headers"
        status: pass
    human_judgment: false
  - id: D2
    description: "Default hybrid route extracts snippets without --full via transient content fetch (content stays None; CLI-07 preserved)"
    requirement: SRCH-07
    verification:
      - kind: integration
        ref: "tests/integration/test_search_pipeline.py#TestSnippetExtractionIntegration::test_default_route_snippet_without_content"
        status: pass
      - kind: integration
        ref: "tests/integration/test_search_pipeline.py#TestSnippetExtractionIntegration::test_default_route_snippet_with_content"
        status: pass
      - kind: other
        ref: "E2E smoke inversion (executor run, real sqlite): default route without content returns non-None snippet with content=None"
        status: pass
    human_judgment: false
  - id: D3
    description: "lex:/vec:/hyde: prefix routes apply the snippet stage before returning; no-extractor pipelines and idempotent skip unchanged"
    requirement: SRCH-07
    verification:
      - kind: unit
        ref: "tests/unit/search/test_hybrid.py#TestPipelineSnippetRoutes (5 tests: lex, vec, hyde, idempotent skip, no-extractor no-op)"
        status: pass
      - kind: other
        ref: "E2E smoke inversion (executor run, real sqlite): lex:-with-content and lex:-without-content both return non-None snippets"
        status: pass
    human_judgment: false
  - id: D4
    description: "On the maintainer's real personal index, the rendered snippet reads as the most relevant excerpt for its query"
    requirement: SRCH-07
    verification: []
    human_judgment: true
    rationale: "Backstop truth from the plan: snippet relevance is a human judgment; automated tests prove extraction mechanics (term-frequency window selection) only"

duration: 9min
completed: 2026-09-05
status: complete
---

# Phase 4 Plan 6: SC 7 Snippet Gap Closure Summary

**Snippet column in query/search CLI tables fed by transient content fetch and prefix-route snippet coverage.**

## Performance

- **Duration:** 9min
- **Started:** 2026-09-05T00:52:36Z
- **Completed:** 2026-09-05T01:01:52Z
- **Tasks:** 3/3
- **Files modified:** 5

## Accomplishments

- Closed the single Phase 04 verification gap (SC 7 / SRCH-07, 04-VERIFICATION.md status
  gaps_found 7/8): search results now show the extracted snippet in both human-facing rich
  tables, on all four pipeline routes, with or without `--full`.
- `SearchPipeline._apply_snippets` fetches document content transiently for extraction when
  `include_content` is False — the fetched text never lands in `SearchResult.content`, so the
  CLI-07 `--full` contract and the `--json` shape for default searches are unchanged.
- The `lex:`/`vec:`/`hyde:` early-return routes now run the snippet stage before returning;
  routing targets, guards, and ordering are untouched (04-REVIEW CR-03 dedup stays advisory).
- Snippet cells are wrapped in `rich.markup.escape` (threat T-04-06-02 mitigated), so bracket
  sequences in document text render literally instead of parsing as console markup.
- Inverted both empirical E2E failures recorded in 04-VERIFICATION.md against a real sqlite
  index: default hybrid without `--full` now returns a non-None snippet (content None), and
  `lex:` with content now returns a non-None snippet.

## Task Commits

Each task followed RED → GREEN (TDD):

1. **Task 1: End-to-end snippet on the default query path** — `2b26138` (test), `cea6a83` (feat)
2. **Task 2: Prefix-route snippet coverage** — `12ebda7` (test), `5eeae8b` (feat)
3. **Task 3: search_cmd Snippet column + fallback tests + quality gate** — `5d19f74` (test), `5608cc6` (feat)

**Plan metadata:** recorded below in the final docs commit.

_TDD gate compliance: every task has a `test(04-06)` RED commit preceding its `feat(04-06)`
GREEN commit; the tracer gate re-ran Task 1's full verify chain end-to-end before expansion
(all pass)._

## Files Created/Modified

- `src/sif/search/hybrid.py` — new `_apply_snippets` method; default-route tail and the three
  prefix early returns routed through it; content fetch is transient
- `src/sif/cli/commands/search.py` — `_display_snippet` helper (snippet → first-highlight
  fallback), Snippet column in query_cmd and search_cmd tables, `escape` from rich.markup,
  `SearchResult` import
- `tests/integration/test_search_pipeline.py` — `TestSnippetExtractionIntegration` (real
  sqlite, with/without content)
- `tests/unit/search/test_hybrid.py` — `TestPipelineSnippetRoutes` (lex/vec/hyde, idempotent
  skip, no-extractor no-op)
- `tests/unit/cli/test_search.py` — `TestSnippetDisplay` (query column, highlight fallback,
  search_cmd column, --files shape)

## Decisions Made

- `_display_snippet` uses `getattr` for both `snippet` and `highlights` (the plan required the
  guard only for highlights) so dict-shaped rows cannot raise during rendering.
- The `TestSnippetDisplay` class was created during Task 1 (its CLI test needed the scaffold)
  and extended in Task 3 with the plan's three behaviors — net class content matches the plan.
- Truncation of snippet/highlight display text reuses `_CONTENT_MAX_LEN` (200) via a default
  parameter, mirroring the existing Content-cell convention.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Verification Evidence

- Targeted: `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search/test_hybrid.py
  tests/unit/cli/test_search.py tests/integration/test_search_pipeline.py -x` → 54 passed.
- Full CLAUDE.md gate: `ruff check src tests` clean, `ruff format --check src tests` clean,
  `env -u FORCE_COLOR NO_COLOR=1 pytest` → **583 passed, 11 skipped** (pre-plan regression
  baseline 572 passed + 11 new tests; zero new failures or skips).
- E2E smoke inversions (real sqlite, executor-run): default-no-content → snippet populated /
  content None; lex:-with-content → snippet populated; lex:-no-content → snippet populated /
  content None.
- Symbol checks: `_apply_snippets` in hybrid.py, `_display_snippet` + two Snippet columns +
  rich.markup.escape import in search.py.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 04 is complete (6/6 plans). Ready for `/gsd-execute-phase 04 --gaps-only` re-verification —
expected score 8/8 with no overrides entry for SC 7. The plan's backstop truth (snippet relevance
judgment on a real personal index, coverage item D4) remains a human-verification item alongside
the three carried over from 04-VERIFICATION.md.

## Self-Check: PASSED

- SUMMARY file exists at `.planning/phases/04-advanced-search-pipeline/04-06-SUMMARY.md` — FOUND
- Task commits `2b26138`, `cea6a83`, `12ebda7`, `5eeae8b`, `5d19f74`, `5608cc6` — all FOUND in git log
- Metadata commit `0df289f` (SUMMARY + STATE + ROADMAP + REQUIREMENTS) — FOUND
- No file deletions in any task commit; no untracked artifacts left behind
