---
phase: 05-agent-context-experience
plan: "11"
subsystem: cli
tags: [rich, markup-escaping, click, cli, regression-tests, cr-01]

# Dependency graph
requires:
  - phase: 05-agent-context-experience
    provides: 05-REVIEW CR-01 finding, TestSearchOutputBranches harness, context_description in --json (CTX-03)
provides:
  - Literal rendering of markup-bearing user data in all three search commands' default Rich tables, line-numbers content cells, and --explain prints (CR-01 closed)
  - Five *_renders_markup_literally regression tests locking the escaping contract
affects: [05-agent-context-experience verification, ui-review]

# Actuals (#2632) — same estimateTokens scale (chars/4 over the realized diff).
actuals:
  tokens: 2087     # 8348 diff chars / 4 over 31e29ef..63bca7e (estimate was 38000 — display-layer-only scope, no schema/pipeline changes)
  tasks: 2
  commits: 2       # MEASURED: git rev-list --count 31e29ef..HEAD

plan_head_before: 31e29ef82bfe66fb8d66205242b4a931c7de4aa8
plan_head_after: 63bca7e432ec30568f40e4f85201bea2d364bdd4

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "rich.markup.escape wraps EVERY user-derived string crossing Table(title)/add_row/console.print markup — extends the 04-06 snippet-column and 05-10 context-list precedents to all search display sites"
    - "Escape after truncation (title cell, line-numbers content) so the display cap applies to raw text and the ellipsis stays inside the escaped string"

key-files:
  created: []
  modified:
    - src/sif/cli/commands/search.py
    - tests/unit/cli/test_search.py

key-decisions:
  - "CR-01 closed by escape() at 12 sites: 3 Table title f-strings, 3 truncated-title cells (whole expression, both branches), 3 collection cells, 3 content appends, plus both explain prints — display-layer only; machine outputs (--json/--csv/--md/--xml/--files) byte-unchanged"
  - "Table tests renamed to the *_renders_markup_literally suffix because the plan's long prescribed names did not contain its own required -k \"markup_literal\" selector substring"

patterns-established:
  - "Escape-after-truncation display contract: truncate raw text first, then escape the whole displayed expression"

requirements-completed: [CTX-03]

coverage:
  - id: D1
    description: "All three search commands' default Rich tables render markup-bearing query, title, collection name, and content literally (exit 0, no MarkupError)"
    requirement: CTX-03
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestSearchOutputBranches::test_search_table_renders_markup_literally"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestSearchOutputBranches::test_query_table_renders_markup_literally"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestSearchOutputBranches::test_vsearch_table_renders_markup_literally"
        status: pass
    human_judgment: false
  - id: D2
    description: "Line-numbers content cells and --explain diagnostic prints render markup-bearing content, query, and title literally"
    requirement: CTX-03
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestSearchOutputBranches::test_line_numbers_content_cell_renders_markup_literally"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestSearchOutputBranches::test_explain_output_renders_markup_literally"
        status: pass
    human_judgment: false
  - id: D3
    description: "Machine-output paths unchanged: --json (context_description byte-identical), --csv, --md, --xml, --files still emit via click.echo and strict-parse"
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestSearchOutputBranches + TestMachineOutputNoWrap (90 search CLI tests, all green post-fix)"
        status: pass
      - kind: unit
        ref: "env -u FORCE_COLOR NO_COLOR=1 pytest --no-cov tests/unit/search/test_hybrid.py tests/unit/search/test_bm25.py tests/unit/search/test_vector.py -k context (6 passed)"
        status: pass
    human_judgment: false

# Metrics
duration: 12min
completed: 2026-11-06
status: complete
---

# Phase 5 Plan 11: CR-01 Rich Markup Escaping in Search Tables Summary

**escape() on every user-derived string crossing Rich in the search/vsearch/query tables and both explain prints — markup-bearing queries, titles, collection names, and content render literally instead of crashing with rich.errors.MarkupError**

## Performance

- **Duration:** 12 min
- **Started:** 2026-11-06T08:20:25Z
- **Completed:** 2026-11-06T08:32:36Z
- **Tasks:** 2 (TDD: 1 RED commit, 1 GREEN commit)
- **Files modified:** 2

## Accomplishments

- CR-01 closed at every cited site: `escape(query)` in all three Table title f-strings and the search explain `Query:` print; `escape(r.title)` in the query explain print; the truncated-title cell expression escaped as a whole (both branches) plus `escape(r.collection_name)` in all three row builders; `row.append(escape(content))` after `prepend_line_numbers`/truncation in all three line-numbers paths
- Five fail-first regression tests in `TestSearchOutputBranches` covering the three tables, the content cell, and both explain prints — all RED (exit-1 MarkupError) on the pre-fix tree, all GREEN after
- Machine-output contract intact: no change to `--json/--csv/--md/--xml/--files` paths, `_field`, `_display_snippet`, `_xml_sanitize`, or query/pipeline logic; context attachment untouched (6 searcher context tests green)

## TDD Gate Compliance

RED → GREEN executed in ancestry order (`test` commit precedes and is an ancestor of the `feat` commit):

### Task 1 — RED (markup-literal regression tests)

- **RED run:** `env -u FORCE_COLOR NO_COLOR=1 pytest --no-cov tests/unit/cli/test_search.py -k "markup_literal"` → **5 failed, 85 deselected** (exit 1), every failure on the planned `assert result.exit_code == 0` with CliRunner capturing `MarkupError` — `closing tag '[/3]' ... doesn't match any open tag` (three tables + explain) and `closing tag '[/]' ... has nothing to close` (line-numbers content cell).
- **Machine evidence:** `gsd_run check tdd-red-evidence .planning/tmp/05-11-red-evidence-task1.json` → **RED_EVIDENCE_OK** (`target_test_failed`, JUnit format, 5/5 failed, no report errors). GREEN authorized.
- **Semantic assessment:** all five target tests executed and failed on the planned assertion for the CR-01 reason — the raw user-derived string interpolated into markup-parsed Rich output. No import, fixture, collection, or syntax faults; JUnit reports failures=5, errors=0. Observation for the record: on the installed rich 14.3.3 an unknown opening tag like `[WIP]` renders literally (the reviewer's silent-swallow repro used a different rich line), so the crash-class failures come from the closing-tag sequences — the escape fix covers both classes regardless.

### Task 2 — GREEN (escape call sites + full quality suite)

- `env -u FORCE_COLOR NO_COLOR=1 pytest --no-cov tests/unit/cli/test_search.py -x` → **90 passed** (85 existing + 5 new).
- `ruff check src tests` and `ruff format --check src tests` → exit 0.
- `COVERAGE_FILE=.coverage.05-11 env -u FORCE_COLOR NO_COLOR=1 pytest -q` → **1008 passed, TOTAL coverage 96.22%** (fail_under=90 gate satisfied).

### REFACTOR

Not performed — the GREEN diff is minimal escape call sites (ruff-format line wrapping only); no cleanup warranted.

## Task Commits

Each task was committed atomically:

1. **Task 1: RED — markup-literal regression tests for all three search tables** - `2d6cee2` (test)
2. **Task 2: GREEN — escape every user-derived string crossing Rich in search.py** - `63bca7e` (feat)

## Files Created/Modified

- `src/sif/cli/commands/search.py` - 12 escape call sites across the three table blocks and both explain prints (display layer only)
- `tests/unit/cli/test_search.py` - five `*markup_literal`-selectable regression tests in `TestSearchOutputBranches`

## Decisions Made

- Escape-after-truncation ordering for the title cell and line-numbers content: the display cap (`_TITLE_MAX_LEN`/`_CONTENT_MAX_LEN`) applies to the raw text, then the whole displayed expression (including the `...` ellipsis) is escaped — mirroring the 05-10 context-list precedent.
- The three table tests use the `_renders_markup_literally` name suffix (see Deviations) so the plan's `-k "markup_literal"` selector gate is satisfiable.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Renamed the three table tests to satisfy the plan's own -k selector**
- **Found during:** Task 1 (RED run)
- **Issue:** The plan's prescribed names (`test_search_table_renders_markup_query_title_collection_literally` and query/vsearch analogues) do not contain the substring `markup_literal`, so the plan's verify command `pytest -k "markup_literal"` selected only 2 of 5 tests — its own acceptance criterion ("reports 5 failed") and `fails_when` ("fewer than 5 failed") could not both hold.
- **Fix:** Renamed the three table tests to the `*_renders_markup_literally` suffix pattern already used by the plan's other two test names; all other plan-specified attributes (location in `TestSearchOutputBranches`, fixtures, assertions, markup payloads) unchanged.
- **Files modified:** tests/unit/cli/test_search.py
- **Verification:** `-k "markup_literal"` → 5 failed pre-fix, 5 passed post-fix.
- **Committed in:** 2d6cee2

**2. [Rule 1 - Bug] Fixed explain test's wrong-command assertion**
- **Found during:** Task 2 (GREEN run)
- **Issue:** The explain test asserted `Query: [/3]-notes` against `query_cmd`, but that line is printed by `search_cmd`'s explain; `query_cmd`'s explain prints per-result `title: scores` lines. The assertion could never pass for `_invoke_query` even with a correct implementation.
- **Fix:** Assert query_cmd's actual explain line (`notes [/3] review: bm25_score=`) and added a `_invoke_bm25 --explain` invocation asserting `Query: [/3]-notes`, so both explain sites (:306 and :690 post-fix) are behaviorally locked.
- **Files modified:** tests/unit/cli/test_search.py
- **Verification:** Full search CLI suite 90 passed. Pre-fix RED fidelity retained — both invocations exit 1 on MarkupError (the committed RED evidence's exit-code failure mode is unchanged).
- **Committed in:** 63bca7e

---

**Total deviations:** 2 auto-fixed (1 blocking naming inconsistency, 1 test-assertion bug)
**Impact on plan:** No scope change. Both fixes reconcile the plan's internal inconsistencies; the delivered behavior matches the plan's must_haves exactly.

## Issues Encountered

None — other than the documented deviations, the plan executed exactly as written.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CR-01 closed; with 05-10 complete, all critical review findings for Phase 05 are addressed. WR-02/WR-03 remain OPEN warnings in 05-REVIEW-DISPOSITION.md by design (out of scope, classified as warnings).
- The flagged assumption from the frontmatter (CTX-03 unclassified edge, edge-probe row 10) remains carried for the next verify/human pass; nothing in this plan changed its status.

## Self-Check: PASSED

All key files exist on disk; both task commits (`2d6cee2`, `63bca7e`) are ancestors of HEAD on this branch; `gsd_run check evaluation-scope --plan 05-11 --commits-only` resolves 2 commits.

