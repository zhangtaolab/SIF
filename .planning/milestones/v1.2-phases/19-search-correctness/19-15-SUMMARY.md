---
phase: 19-search-correctness
plan: 15
subsystem: testing
tags: [per-chunk, rich-markup, bm25, search-chunks, score-map, mutation-gate, gap-closure, uat, g-19-10, t-19-45, t-19-46, corr-02, corr-03]

requires:
  - phase: 19-search-correctness
    provides: "19-10: the per-chunk Chunk cell as a plain Text, the document-level-row formatter conditions, and the five-row per-chunk page fixtures in TestPerChunkSurfaces"
  - phase: 19-search-correctness
    provides: "19-12: the displayed-score map |bm25|/(1+|bm25|) in search and search_chunks; the raw bm25 values far from -1 this plan pins"
  - phase: 19-search-correctness
    provides: "19-13 and 19-14: the plan base 091d7a4 (HEAD after their metadata commits), plan 19-13's 253-test gate command and the docs/hygiene/release count of 51"
provides:
  - "tests/unit/cli/test_search.py: test_per_chunk_markdown_and_xml_give_a_document_level_row_no_sequence and test_per_chunk_chunk_cell_renders_a_markup_bearing_path_literally (two cases)"
  - "tests/unit/search/test_bm25.py: _build_chunk_fts_db and TestBM25Searcher.test_search_chunks_scores_use_the_display_map"
  - "Three mutation gates proving each test fails without the behaviour it guards, each run on a throwaway mktemp -d copy"
affects: ["19 (UAT gap G-19-10; the phase re-verification and UAT)", "17, 18, 20, 21, 22, 24 (their verifications re-stale)"]

# Actuals (#2632): chars/4 over the realized diff from the plan base to the last task commit,
# 6,864 chars across the two changed test files; no planning artifact changed by a task.
actuals:
  tokens: 1716
  tasks: 2
  commits: 2
  plan_head_before: 091d7a4a072c1c1b3e193b9f506ac9dacc83d3a5
  plan_head_after: f844c798906f4154eeb88d16d91aa70a01636d2f

tech-stack:
  added: []
  patterns:
    - "A guard for an already-correct behaviour is proven non-vacuous by a mutation gate that copies the package and the test into mktemp -d, applies the mutant there and requires the test to fail by count"
    - "A markup-bearing fixture is chosen by what Rich actually parses (a tag starting with a letter, a number sign, a slash or an at sign), not by what merely looks like markup"

key-files:
  created: []
  modified:
    - tests/unit/cli/test_search.py
    - tests/unit/search/test_bm25.py

key-decisions:
  - "The markup-bearing paths are /notes/[red]evil[/red].md and /notes/[/3]-review.md, not the UAT session's r[3]eview-notes (v2).md: Rich reads a bracketed tag only when it starts with a letter, a number sign, a slash or an at sign, so a test on that name would pass on a markup-parsing mutant."
  - "The score-map test reads raw bm25 values from a real FTS5 chunk index at about -4.72 and -0.77, far from -1 where the earlier reciprocal map and the displayed-score map agree; the thirty filler chunks keep the term rare."
  - "No source file changed: the three behaviours of UAT test 10 were right and only their failing-without-them guards were missing; the base-anchored scope gate holds the tree to the two declared test files."

patterns-established:
  - "Each gate fails when the mutation anchor is not found, so a later change to the mutated lines cannot turn a gate into a silent pass."
  - "A guard is checked by its negative: the mutated copy must fail by an exact count, and the earlier tests that passed on the mutant are named to show why they were not guards."

requirements-completed: [CORR-02, CORR-03]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "A document-level row of the five-row per-chunk page gets no sequence field: in Markdown its Path line is followed directly by its Collection line and exactly four Sequence lines exist; in XML its children are title, path and collection"
    requirement: CORR-02
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestPerChunkSurfaces.test_per_chunk_markdown_and_xml_give_a_document_level_row_no_sequence"
        status: pass
      - kind: other
        ref: "Task 1 mutation gate 1 (both formatter conditions widened to `if per_chunk:` on a throwaway copy): 1 failed in 0.30s, assertion '- **Sequence:** ' == '- **Collection:** notes'"
        status: pass
    human_judgment: false
  - id: D2
    description: "A markup-bearing path renders literally in the Chunk cell of both per-chunk tables at 200 columns: /notes/[red]evil[/red].md and /notes/[/3]-review.md each render as path#0 with exit code 0"
    requirement: CORR-02
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestPerChunkSurfaces.test_per_chunk_chunk_cell_renders_a_markup_bearing_path_literally[/notes/[red]evil[/red].md|/notes/[/3]-review.md]"
        status: pass
      - kind: other
        ref: "Task 1 mutation gate 2 (cell yields Text.from_markup, then a plain string, on throwaway copies): 2 failed in 0.31s for each mutation"
        status: pass
    human_judgment: false
  - id: D3
    description: "BM25Searcher.search_chunks maps each raw bm25 value with bm25_display_score, on a real FTS5 chunk index whose two matches sit near -4.72 and -0.77, and the scores fall with rank"
    requirement: CORR-03
    verification:
      - kind: unit
        ref: "tests/unit/search/test_bm25.py#TestBM25Searcher.test_search_chunks_scores_use_the_display_map"
        status: pass
      - kind: other
        ref: "Task 2 mutation gate (search_chunks converts with the reciprocal map on a throwaway copy): 1 failed, 2 passed, 56 deselected in 0.09s, the failure being the new test (0.1749425030493316 != 0.8250574969506684)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Only the two declared test files differ from the plan base outside .planning/: no file under src/, docs/ or scripts/ changed, no existing test was weakened, and no other plan or SUMMARY of the phase directory was edited"
    verification:
      - kind: other
        ref: "Base-anchored scope gate at f844c79: exactly tests/unit/cli/test_search.py and tests/unit/search/test_bm25.py; plan/summary gate clean; diff 2 files changed, 113 insertions(+), 0 deletions(-)"
        status: pass
    human_judgment: false

# Metrics
duration: 7min
completed: 2026-11-27
status: complete
---

# Phase 19 Plan 15: Three Guards for UAT Test 10 Summary

**Three tests now guard the per-chunk document-level row, the literal Chunk cell and the `search_chunks` score map, each proven non-vacuous by a mutation gate on a throwaway copy; no source file changed.**

## Performance

- **Duration:** 7 min (417 s)
- **Started:** 2026-11-27T09:59:16Z
- **Completed:** 2026-11-27T10:06:13Z
- **Tasks:** 2
- **Files modified:** 2 (both test files), plus this SUMMARY and the planning records

## Accomplishments

- `test_per_chunk_markdown_and_xml_give_a_document_level_row_no_sequence` renders the five-row per-chunk page through the real `query` command with `--per-chunk --md` and with `--per-chunk --xml`: the document-level row's Path line is followed directly by its Collection line, exactly four `Sequence` lines exist (those of the chunk rows), and the fifth XML result carries children `title`, `path` and `collection` with the plain path. The mutation gate widens both formatter conditions to `if per_chunk:` and the test fails with `'- **Sequence:** ' == '- **Collection:** notes'`.
- `test_per_chunk_chunk_cell_renders_a_markup_bearing_path_literally` (two cases) renders `/notes/[red]evil[/red].md` and `/notes/[/3]-review.md` at a 200-column console through both `vsearch` and `query`, asserting exit code 0 and a Chunk cell equal to `path#0`. Both mutation gates (a cell yielding `Text.from_markup`, then a plain string) make both cases fail.
- `_build_chunk_fts_db()` builds a real FTS5 chunk index whose two `apple` matches score near -4.72 and -0.77, far from -1; `test_search_chunks_scores_use_the_display_map` pins each returned score to `bm25_display_score` of the raw rank and the descending order. The reciprocal-map mutant fails only the new test (`1 failed, 2 passed, 56 deselected`): the earlier chunk test and SQL-text test pass on it, which is why they were not guards.
- `TestPerChunkSurfaces` reports 33 passed (the 30 existing tests unchanged) and `tests/unit/search/test_bm25.py` 59; plan 19-13's gate command reports 253 passed; the full suite reads 3320 passed and 1 skipped at 95.16% coverage; the docs, hygiene and release-metadata tests read 51 passed; ruff is clean with 239 files formatted.
- No source, doc, script, dependency or existing test changed. The base-anchored scope gate shows exactly the two declared test files and the plan/summary gate is clean.

## Plan Base

`091d7a4a072c1c1b3e193b9f506ac9dacc83d3a5` — HEAD before Task 1 (the metadata commit of plan 19-14), recorded at `.git/gsd-plan-19-15-base` and kept across re-runs. Both changed files were byte-identical to the v1.2.4 tag `6089078` before this plan.

## Task Commits

Each task was committed atomically:

1. **Task 1: The document-level row and the markup-bearing Chunk cell** — `0452dfb` (test)
2. **Task 2: The `search_chunks` score map and the plan gates** — `f844c79` (test)

**Plan metadata:** this SUMMARY's own commit (the metadata commit that follows it; it also carries `STATE.md` and `.planning/state.json`).

## Mutation runs

Every gate copied `src/sif` and the needed test files into a `mktemp -d` directory, applied one mutation, ran pytest there and removed the directory; the working tree was never mutated. The summary line each mutated copy printed:

| Gate | Mutation | Summary line |
|------|----------|--------------|
| Task 1 gate 1 | `if per_chunk and sequence:` → `if per_chunk:` in both formatters (2 anchor substitutions) | `1 failed in 0.30s` (first run 0.27 s); the failure is `'- **Sequence:** ' == '- **Collection:** notes'` |
| Task 1 gate 2a | the Chunk cell yields `Text.from_markup(_fit_head(...))` | `2 failed in 0.31s` (first run 0.29 s) — both path cases |
| Task 1 gate 2b | the Chunk cell yields the plain string `_fit_head(...)` | `2 failed in 0.31s` (first run 0.30 s) — both path cases |
| Task 2 gate | `score = bm25_display_score(row["score"])` → `score = 1.0 / (1.0 + abs(row["score"]))` | `1 failed, 2 passed, 56 deselected in 0.09s`; the failure is the new test at `0.1749425030493316 != 0.8250574969506684`, and the two earlier `search_chunks` tests pass |

The Task 1 gates were re-run end-to-end after the Task 1 commit (the tracer feedback gate under active auto mode): `1 failed in 0.30s`, `2 failed in 0.31s`, `2 failed in 0.31s`. Each gate exits 1 when its mutation anchor is not found exactly once, so a later change to the mutated lines cannot silently turn a gate into a pass.

## Files Created/Modified

- `tests/unit/cli/test_search.py` — two new tests inside `TestPerChunkSurfaces`, inserted directly before `test_per_chunk_files_and_quiet_list_each_path_once`; 55 insertions, no existing line changed.
- `tests/unit/search/test_bm25.py` — `_build_chunk_fts_db()` above `_build_title_body_db`, and `test_search_chunks_scores_use_the_display_map` after `test_search_chunks_returns_tuples`; 58 insertions, no existing line changed.

## Decisions Made

- **Choose the markup paths by what Rich parses, not by what looks like markup.** Rich reads a bracketed tag only when it starts with a letter, a number sign, a slash or an at sign; the UAT session's `r[3]eview-notes (v2).md` starts with `r` after the bracket (`[3]`), so it renders literally even in a markup-parsing cell. `/notes/[red]evil[/red].md` loses its tags and `/notes/[/3]-review.md` raises `MarkupError` under such a cell, so both reject the mutant.
- **Pin the score map where the two maps disagree.** At a raw bm25 value of -1 both the earlier reciprocal map and `bm25_display_score` give 0.5, which is why `test_search_chunks_returns_tuples` could not catch the regression. The new corpus puts the two matches at about -4.72 and -0.77, and the reciprocal-map mutant changes both the values and the order.
- **Guard only; change nothing.** All three behaviours were correct by prior probe, so the plan adds no source change and no red run on the working tree; the mutation gates are the evidence that the guards are not vacuous. The plan's Task 1 precondition (`git diff --quiet 6089078 -- tests/unit/cli/test_search.py`) exited 0.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. `TestPerChunkSurfaces` reported 30 passed before the change and 33 after; `tests/unit/search/test_bm25.py` reported 59 with the new test, matching the plan.

## Authentication Gates

None.

## Human Checks

None. This plan carries no `checkpoint:*` task and no `<human-check>` block; every `<verify>` command is automated and ran.

## Threat Model Disposition

- **T-19-45 (repudiation, the claim that the three behaviours have a failing guard):** mitigated. Each new test is paired with a gate that mutates a throwaway copy and requires the test to fail by count; the gates fail loudly when the mutation anchor is not found. The observed summary lines are recorded under "Mutation runs", and the plan's earlier scratch observations (2026-11-26, `99ee9f7`) are reproduced at this base.
- **T-19-46 (tampering, the Chunk cell):** mitigated (now tested). The cell still yields a plain `Text`; the new parametrized test renders two paths that Rich does parse as markup in a parsing cell, through both per-chunk tables, and both mutations make both cases fail. The `yield` line was found exactly once at every gate run.
- **T-19-SC (supply chain):** no package was installed, added or removed; `pyproject.toml` and `uv.lock` are untouched.

No threat flags: no file adds an endpoint, auth path, file-access pattern or schema change beyond what the threat model records.

## Known Stubs

None. No test is skipped by this plan and every automated `<verify>` command ran; no new WINDOWS entry is owed.

## Planning Record Outcomes (archived milestone)

- `gsd_run query roadmap.update-plan-progress 19` declined with `missing_phase_details` (`updated: false`, `plan_count: 15`, `summary_count: 14` at the time of the call, status `In Progress`): the active `.planning/ROADMAP.md` has no writable entry for Phase 19 because the v1.2 roadmap is archived. The archived file was left untouched, as instructed.
- `gsd_run query state.update-progress` declined with `no plans found in current-milestone phases (0 plans)` for the same reason; `STATE.md`'s progress block was left unchanged.
- `gsd_run query requirements.mark-complete CORR-02 CORR-03` reported `REQUIREMENTS.md not found`: the active scope has no REQUIREMENTS.md (it is archived at `.planning/milestones/v1.2-REQUIREMENTS.md`, which is not edited). Readiness had been confirmed first: `requirements.ready-ids` returned both IDs in `ready` with an empty `blocked` list.

## Next Phase Readiness

- UAT gap G-19-10 is closed in the automated sense at `f844c79`: the three behaviours of UAT test 10 each have a test that fails without them, and only `tests/unit/cli/test_search.py` and `tests/unit/search/test_bm25.py` differ from the plan base.
- The three gates can be re-run while `.git/gsd-plan-19-15-base` exists; each names its mutation anchor and exits 1 when the anchor is missing.
- `19-VALIDATION.md`'s gaps V19-26-1 to V19-26-3 are to be closed by that report's own re-run, not by hand; this plan edited no audit report and no plan or SUMMARY.
- Executing this plan re-stales the verifications of Phases 17, 18, 20, 21, 22 and 24 (all already `stale` after the first round); Phase 19 is re-verified after this round. With 15/15 plans now carrying a SUMMARY, Phase 19 is ready for `/gsd-verify-work 19`.

---
*Phase: 19-search-correctness*
*Completed: 2026-11-27*

## Self-Check: PASSED

Run at `f844c79`, before this SUMMARY was committed:

- Both declared files are present on disk with their new symbols: `test_per_chunk_markdown_and_xml_give_a_document_level_row_no_sequence`, `test_per_chunk_chunk_cell_renders_a_markup_bearing_path_literally` (2 cases), `_build_chunk_fts_db`, `test_search_chunks_scores_use_the_display_map`.
- Commits `0452dfb` and `f844c79` are ancestors of HEAD; `git rev-list --count 091d7a4..HEAD` is 2, matching `actuals.commits`, and the ledger `.git/gsd-plan-head-before-19-15` holds the same base.
- Base-anchored scope gate: exactly `tests/unit/cli/test_search.py` and `tests/unit/search/test_bm25.py` differ from `091d7a4` outside `.planning/` (113 insertions, 0 deletions); plan/summary gate clean.
- Automated gates: `TestPerChunkSurfaces` 33 passed (30 before); `tests/unit/search/test_bm25.py` 59 passed; plan 19-13's gate command 253 passed; combined plan verification 92 passed; ruff clean with 239 files formatted; full suite 3320 passed, 1 skipped at 95.16% (exit 0); docs/hygiene/release 51 passed.
- Mutation gates: `1 failed in 0.30s`; `2 failed in 0.31s` for each of the two cell mutations; `1 failed, 2 passed, 56 deselected in 0.09s`.
- Frontmatter parses with `status: complete` and four coverage entries, every one `human_judgment: false` with all-`pass` verification.
