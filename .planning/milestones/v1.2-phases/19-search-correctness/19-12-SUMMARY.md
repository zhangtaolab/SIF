---
phase: 19-search-correctness
plan: 12
subsystem: search
tags: [bm25, min-score, score-map, monotone, hybrid, rrf, sc1-golden, evidence, help-text, changelog, gap-closure, uat, corr-03, g-19-2]

# Dependency graph
requires:
  - phase: 19-search-correctness
    provides: "19-11: the operator's decision monotone-map, on a Decision line of that SUMMARY and in the decision field of bench/g19-2-min-score.json, and the before half of that artifact; 19-10, after whose commits this plan's base lies; 19-05: the min_score predicate its fourth truth recorded and the B0 comparison command the capture follows; the committed saved runs bench/b0.json and bench/b1.json (corpus fingerprint 8c006123784348d1); CONTEXT D-06 and the locked rule that BM25 min_score is applied before pagination"
provides:
  - "bm25_display_score(raw) = abs(raw)/(1+abs(raw)) and bm25_rank_threshold(min_score) = -M/(1-M): the one score map and the one bound that the SQL predicate and the Python filter of BM25Searcher share"
  - "BM25Searcher.search binds AND m.score <= ? in the outer WHERE of both SQL branches, ahead of the metadata filter and of LIMIT ? OFFSET ?; every displayed BM25 score rises with relevance"
  - "tests/unit/cli/test_search_min_score.py: the direction proof through the real CLI on a real temporary BM25 index"
  - "TestHybridMinScoreLeg in tests/unit/search/test_hybrid.py: min_score on the BM25 leg of the hybrid path, which sif search query --min-score and MCP query share"
  - "The after half of bench/g19-2-min-score.json (probe rows, both threshold outcomes, the hybrid BM25 leg at 0.3 and 0.5, B0 and B1 deltas) and the dated rationale on the SC1 golden"
  - "The written contract in line with the code: the search --min-score help text, the regenerated CLI reference, the changelog entry, the benchmarking notes and the amended fourth truth of 19-05-PLAN.md"
  - "Plan base record left in place so the red-derivation, numstat and scope gates can be re-run"
affects: ["19 (UAT test 2, and the Task 3 human check that is pending for the end-of-phase verifier)", "22 (the min_score item of the Phase 22 UI review)", "18 and 24 (their verifications go stale after this change)"]

# Actuals (#2632): tokens are chars/4 over the unified diff of every file changed from the plan base to the last task commit,
# 9,508 in the nine files outside .planning/ (source, tests, docs) and 1,394 in the two planning artifacts. The estimate was 60,000.
# commits is measured from the ledger (.git/gsd-plan-head-before-19-12); this SUMMARY is committed after them.
actuals:
  tokens: 10903
  tasks: 3
  commits: 3
  plan_head_before: 0744e83b5308f2c2235d81dee59b96ca02d453d3
  plan_head_after: 38f45512b0148464b8018c634211fa2ea710a0c6

tech-stack:
  added: []
  patterns:
    - "A published score map and its matching threshold live in two named pure functions (bm25_display_score, bm25_rank_threshold) that both the SQL predicate and the Python filter call, so the two cannot drift apart"
    - "A one-way change to a published output contract runs as two plans: a decision plan commits the before-evidence and the operator's choice, and the implementing plan gates on both records, appends an after half and pins it with a validator"

key-files:
  created:
    - tests/unit/cli/test_search_min_score.py
  modified:
    - src/sif/search/bm25.py
    - src/sif/cli/commands/search.py
    - tests/unit/search/test_bm25.py
    - tests/unit/search/test_filters_sql.py
    - tests/unit/search/test_hybrid.py
    - docs/cli-reference.md
    - docs/changelog.md
    - docs/benchmarking.md
    - .planning/milestones/v1.2-phases/19-search-correctness/bench/g19-2-min-score.json
    - .planning/milestones/v1.2-phases/19-search-correctness/19-05-PLAN.md

key-decisions:
  - "The fourth red run (searcher wired, golden stale) was observed in a reproduced state and not in sequence: the executor had already written the two regenerated values when it ran that file, so it put them back to their committed values, ran the file (5 failed, 69 passed) and restored them. No value was chosen to fit a result; the order is recorded under Deviations."
  - "test_search_applies_min_score asserts the place of the predicate ahead of LIMIT ? OFFSET ? as well as its text, so the acceptance criterion about both SQL branches is asserted for the unfiltered branch too; the scoped branch is pinned by the parameter-order test."
  - "The comment in test_min_score_applies_before_offset_with_global_ranks was rewritten. At 0.76 the surviving rows are a prefix of the list, so a filter applied after pagination would return the same row; what the test distinguishes is the global rank 2 against a renumbered rank 1."
  - "The golden's docstring says why its values were regenerated and not derived by subtracting the old ones from 1: the subtraction loses digits and gives 1.3749981094823838e-06 and 1.3134311107609875e-06 instead."
  - "The Task 3 human check is recorded as not performed, here and as entry 13 of .planning/WINDOWS.md, and was not self-approved; under human_verify_mode end-of-phase the verifier harvests it."

patterns-established:
  - "Thresholds in direction tests sit midway between two rows' scores and never on a row's score, because the bound is recomputed in floating point and can miss a row whose score equals the threshold to the last bit; where a test uses a row's own score it asserts only what holds on either side of that boundary"
  - "A re-pinned test is seen red for the reason the plan names before the code changes, and a gate re-derives that red state from the plan base for as long as the base record exists"
  - "A plan whose gates are multi-line shell is run from blocks extracted from the plan file itself, never retyped"

requirements-completed: [CORR-03]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "BM25Searcher.search shows the magnitude of the bm25 value over one plus that magnitude, and applies --min-score as the bound -M/(1-M) through AND m.score <= ?, a bound parameter in the outer WHERE of both SQL branches ahead of LIMIT ? OFFSET ?; 0, a negative value and NaN omit the predicate, and 1 or more returns no row"
    requirement: CORR-03
    verification:
      - kind: unit
        ref: "tests/unit/search/test_bm25.py#TestBM25Searcher.test_search_applies_min_score + test_search_min_score_zero_omits_the_threshold_filter + test_display_score_rises_with_relevance + test_rank_threshold_table (7 cases) + test_min_score_at_or_above_one_keeps_nothing (2 cases) + test_negative_min_score_omits_the_filter"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_bm25.py#TestBM25OffsetPagination.test_scores_are_monotone_with_rank + test_min_score_removes_weaker_matches_and_keeps_the_best + test_mid_min_score_keeps_expected_documents_and_direction + test_min_score_applies_before_offset_with_global_ranks"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_bm25.py#TestWeightedBM25.test_1_0_1_0_reproduces_rank_exactly_on_real_corpus + test_min_score_thresholds_the_weighted_expression_before_pagination; tests/unit/search/test_filters_sql.py#TestBm25ParamOrder.test_weights_match_collection_min_score_filter_limit_offset"
        status: pass
      - kind: other
        ref: "Task 1 verify gates 2 to 8 of 19-12-PLAN.md: 241 passed; no lower-bound predicate and no reciprocal conversion left in the searcher; red-derivation gate exit 0; ty and ruff clean"
        status: pass
    human_judgment: false
  - id: D2
    description: "Through the real CLI on a real temporary index (UAT test 2, gap G-19-2): the best BM25 match shows the highest score and is the row a threshold keeps, with global ranks; --min-score 1 returns the empty list"
    requirement: CORR-03
    verification:
      - kind: integration
        ref: "tests/unit/cli/test_search_min_score.py#test_min_score_keeps_the_best_match_and_drops_weaker_ones + test_min_score_of_one_returns_no_results"
        status: pass
      - kind: other
        ref: "red-derivation gate against the base searcher (exit 0; inner run 3 failed, 1 passed, 72 deselected; the CLI direction test FAILED by name)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Hybrid ranking is unchanged where no threshold is set, and min_score on the BM25 leg of the hybrid path keeps the stronger matches, pinned through HybridSearcher.search: sif search query --min-score and MCP query with min_score no longer lose that leg at ordinary thresholds, while the vector leg keeps its own threshold"
    requirement: CORR-03
    verification:
      - kind: unit
        ref: "tests/unit/search/test_hybrid.py#TestHybridMinScoreLeg.test_min_score_keeps_the_stronger_match_in_the_hybrid_bm25_leg + test_min_score_keeps_the_bm25_match_fused_instead_of_dropping_the_leg"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_hybrid.py#TestHybridSC1PipelineGolden.test_default_options_match_prechange_snapshot + test_explicit_default_weights_match_prechange_snapshot; TestCandidateFetch.test_candidate_fetch_off_path_matches_sc1_snapshot"
        status: pass
      - kind: other
        ref: "after-evidence validator of Task 2 (after-evidence OK, under bash and under zsh): identical ranks and titles on both sides, B0 and B1 deltas n 100 mean 0.0 helped 0 hurt 0 unchanged 100, the hybrid BM25 leg empty before and full at 0.3 and 0.5 after"
        status: pass
    human_judgment: false
  - id: D4
    description: "The SC1 golden carries the two bm25_score values regenerated from code, 1.3749981093775994e-06 for d3 and 1.313431110717347e-06 for d1, with a dated rationale; its order, RRF scores and vector scores, the held-out snapshot with its test, and the committed bench runs are untouched"
    verification:
      - kind: other
        ref: "Task 2 verify gates 1, 2 and 4 of 19-12-PLAN.md: 89 passed; snapshot values equal the regenerated ones; held-out snapshot and its test byte-identical to the plan base; git diff --quiet of bench/b0.json, bench/b1.json and bench/d12-verdict.json against the plan base exits 0"
        status: pass
    human_judgment: false
  - id: D5
    description: "bench/g19-2-min-score.json carries its after half, captured on the changed checkout with the plan's eight capture commands: probe rows at 0.8942969490522424 and 0.8472891464061002 with ranks unchanged, both thresholds keeping both matches, the hybrid BM25 leg, B0 and B1 deltas, and the SC1 values"
    verification:
      - kind: other
        ref: "Task 2 after-evidence validator (exit 0, after-evidence OK)"
        status: pass
    human_judgment: false
  - id: D6
    description: "The written contract agrees with the code: the search --min-score help text, the generator-owned CLI reference row, the changelog entry with the query --min-score change included, the score-direction note and the SC1 values in the benchmarking notes, and the fourth truth of 19-05-PLAN.md amended in exactly one line"
    verification:
      - kind: other
        ref: "Task 3 verify gates 1 to 7 of 19-12-PLAN.md: the help phrase once and the old wording twice; make docs-generate leaves both references byte-identical; changelog phrase once; Score-direction note once; Amended 2026-11-26 by plan 19-12 once; 19-05-PLAN.md numstat 1 1"
        status: pass
      - kind: unit
        ref: "tests/test_docs.py + tests/test_hygiene.py + tests/test_release_metadata.py (49 passed)"
        status: pass
    human_judgment: false
  - id: D7
    description: "Scope and quality hold: exactly the nine declared files changed outside .planning/, sif search vsearch --min-score and src/sif/search/vector.py are untouched, no package was installed, and lint, type check, the full suite with coverage at or above 90 and the docs tests pass"
    verification:
      - kind: other
        ref: "Task 3 verify gates 8 to 11 of 19-12-PLAN.md: scope gate exit 0 with the nine declared paths; ty All checks passed! for both modules; ruff All checks passed! with 238 files already formatted; full suite 3303 passed, 1 skipped, coverage 95.16%"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_vector.py#TestVectorSearcher.test_search_applies_min_score (1 passed; the test that truth 10 of the plan names without its class segment)"
        status: pass
    human_judgment: false
  - id: D8
    description: "Task 3 human check: on an index with embedded chunks, sif search query QUERY --min-score 0.3 --json keeps the stronger BM25 matches in the page, beside their vector_score, where before the plan the page carried no bm25_score; sif search vsearch QUERY --min-score 0.3 filters on similarity as before"
    requirement: CORR-03
    verification:
      - kind: manual_procedural
        ref: "the human-check of Task 3 in 19-12-PLAN.md: not performed by the executor; left for the end-of-phase verifier harvest and recorded as entry 13 of .planning/WINDOWS.md"
        status: unknown
      - kind: unit
        ref: "automated backstop: tests/unit/search/test_hybrid.py#TestHybridMinScoreLeg (2 passed) and the hybrid_bm25_leg after rows of bench/g19-2-min-score.json"
        status: pass
    human_judgment: true
    rationale: "Whether the real sif query output reads that way on the operator's own index is a check on an embedded index that this run could not build: the dispatch rules barred loading an embedding model and pointed every capture at a scratch directory. The unit tests and the evidence artifact read the same BM25 leg through HybridSearcher.search, which is the backstop and not the judgement. The executor did not perform or approve this check."

duration: 49min
completed: 2026-11-26
status: complete
---

# Phase 19 Plan 12: Monotone BM25 Score and a `--min-score` That Keeps the Best Matches Summary

**The displayed BM25 score is now the magnitude of the bm25 value over one plus that magnitude and rises with relevance, and `--min-score` keeps the stronger matches through the bound `-M/(1-M)` applied before pagination: `sif search search` and MCP `lex_search` behave as their help text says, the BM25 leg of `sif search query --min-score` is no longer emptied at ordinary thresholds (pinned through `HybridSearcher.search`), and ranking without a threshold is proven unchanged.**

## Performance

- **Duration:** 49 min
- **Started:** 2026-11-26T02:33:12Z
- **Completed:** 2026-11-26T03:22Z (the time of writing; the commit timestamp is authoritative)
- **Tasks:** 3/3
- **Files modified:** 11 (2 source, 4 test of which 1 is new, 3 docs, 2 planning artifacts), plus this SUMMARY and `.planning/WINDOWS.md`

Environment: Python 3.13.9, pytest 9.1.1, ruff 0.15.11, branch `gsd/phase-24-reverify`, main checkout, no worktree.

## Plan Base and Precondition

- Plan base: `0744e83b5308f2c2235d81dee59b96ca02d453d3`, recorded at Task 1 Step 0 in the file that `git rev-parse --git-path gsd-plan-19-12-base` prints (`.git/gsd-plan-19-12-base`). No commit carried the `(19-12)` scope, so the record holds HEAD at the start. It survived the three commits and is left in place so the red-derivation, numstat and scope gates can be re-run.
- Precondition of Task 1, checked read-only before any edit: the 19-11 SUMMARY has a line that reads `Decision: monotone-map` (grep exit 0), and the artifact's `decision` is `monotone-map` with a `probe.before` half and no after half. Task 1's first gate ran the same check again.
- Precondition of Task 2, checked read-only: `.git` is a directory, so this is the main checkout and not a worktree. Both comparisons then accepted the corpus fingerprint; neither refused.
- Tracer feedback gate: Task 1 is `type="tracer"`, carries no `gate`, its verify block is automated-only, and auto mode is active (`workflow.auto_advance` is `true`). The verify block was re-run after the Task 1 commit; all eight gates were green again at `37b6315` before Task 2 started.
- Checkpoints: the plan has no `checkpoint:*` task. Its one `<human-check>`, in the verify block of Task 3, is not a mid-flight stop under `workflow.human_verify_mode: end-of-phase`; it is recorded below as pending and not performed.

## Red Runs

Four red points of Task 1, each run with `-q --no-cov -p no:cacheprovider`. Short test summary lines, verbatim.

### 1. Step 1, the new CLI file, on the unchanged source (`0744e83`)

```
env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/cli/test_search_min_score.py -q --no-cov -p no:cacheprovider
```

Exit code 1.

```
FAILED tests/unit/cli/test_search_min_score.py::test_min_score_keeps_the_best_match_and_drops_weaker_ones
1 failed, 1 passed in 0.70s
```

- The failure is the assertion that the scores are sorted in descending order: `At index 0 diff: 0.11971839861188126 != 0.15435461494550404`. The strong document is rank 1 and shows the lower number.
- The pass is `test_min_score_of_one_returns_no_results`: the old code also returned nothing at a threshold of 1.
- The run above is on the final text of the file. A first run on the same text before one blank line was added gave the same FAILED line and `1 failed, 1 passed in 1.17s`.

### 2. Step 2, the searcher tests, with the helpers present and the searcher unwired

```
env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search/test_bm25.py tests/unit/search/test_filters_sql.py -q --no-cov -p no:cacheprovider
```

Exit code 1.

```
FAILED tests/unit/search/test_bm25.py::TestBM25Searcher::test_search_applies_min_score
FAILED tests/unit/search/test_bm25.py::TestBM25Searcher::test_display_score_rises_with_relevance
FAILED tests/unit/search/test_bm25.py::TestBM25OffsetPagination::test_scores_are_monotone_with_rank
FAILED tests/unit/search/test_bm25.py::TestBM25OffsetPagination::test_min_score_removes_weaker_matches_and_keeps_the_best
FAILED tests/unit/search/test_bm25.py::TestBM25OffsetPagination::test_mid_min_score_keeps_expected_documents_and_direction
FAILED tests/unit/search/test_bm25.py::TestBM25OffsetPagination::test_min_score_applies_before_offset_with_global_ranks
FAILED tests/unit/search/test_bm25.py::TestWeightedBM25::test_1_0_1_0_reproduces_rank_exactly_on_real_corpus
FAILED tests/unit/search/test_bm25.py::TestWeightedBM25::test_min_score_thresholds_the_weighted_expression_before_pagination
FAILED tests/unit/search/test_filters_sql.py::TestBm25ParamOrder::test_weights_match_collection_min_score_filter_limit_offset
9 failed, 156 passed in 0.26s
```

- These are the nine tests the plan names. `test_display_score_rises_with_relevance` failed with `0.16666666666666666 == 0.8333333333333334`: the mock row at -5.0 scored one sixth under the old map.
- The 156 passes include the three new tests that pass on the old searcher by design: the threshold table, the edge values 1.0 and 2.5 (the old bound also returned no row there) and the negative threshold (the old code also omitted the predicate).

### 3. Step 2, the hybrid-leg tests, same state

```
env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search/test_hybrid.py -k TestHybridMinScoreLeg -q --no-cov -p no:cacheprovider
```

Exit code 1.

```
FAILED tests/unit/search/test_hybrid.py::TestHybridMinScoreLeg::test_min_score_keeps_the_stronger_match_in_the_hybrid_bm25_leg
FAILED tests/unit/search/test_hybrid.py::TestHybridMinScoreLeg::test_min_score_keeps_the_bm25_match_fused_instead_of_dropping_the_leg
2 failed, 72 deselected in 0.12s
```

- The first failed on the descending-scores assertion (`0.1693331053339983 != 0.6765093877752076` at index 0).
- The second failed with `AssertionError: assert 'bm25_score' in {}`: `d4` was on the page without a `bm25_score`, because the threshold had emptied the BM25 leg.

### 4. The searcher wired and the golden still stale

```
env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search/test_hybrid.py -q --no-cov -p no:cacheprovider
```

Exit code 1.

```
FAILED tests/unit/search/test_hybrid.py::TestHybridSC1PipelineGolden::test_default_options_match_prechange_snapshot
FAILED tests/unit/search/test_hybrid.py::TestHybridSC1PipelineGolden::test_explicit_default_weights_match_prechange_snapshot
FAILED tests/unit/search/test_hybrid.py::TestCandidateFetch::test_candidate_fetch_off_path_matches_sc1_snapshot
FAILED tests/unit/search/test_hybrid.py::TestSearchPipelineIdentity::test_protocol_only_embedder_keeps_the_plain_embed_path
FAILED tests/unit/search/test_hybrid.py::TestSearchPipelineIdentity::test_default_no_prompt_query_role_reproduces_the_sc1_golden
5 failed, 69 passed in 0.38s
```

- The five failures are the five tests that compare against `TestHybridSC1PipelineGolden.SNAPSHOT`. The first one shows the `d3` row with `bm25_score` `1.3749981093775994e-06` and an unchanged rank 1, `score` `0.03252247488101534` and `vector_score` `0.6464466154575348`.
- The two `TestHybridMinScoreLeg` tests pass in this state: they are among the 69.
- Through Task 1's gate command, which stops at the first failure, the same state gave `1 failed, 197 passed in 0.92s`: the plan's validation note for that gate records the same figure.
- **Order of observation.** The plan's truth 6 and acceptance criterion 8 place this red point before the golden is regenerated. The executor ran the regeneration command and wrote the two values before running this file, so it reproduced the state instead: the two values were put back to their committed ones, the file was run, and the values were restored. Nothing else in the file differed. See Deviations.

## Accomplishments

- `bm25_display_score(raw)` returns the magnitude over one plus the magnitude, and `bm25_rank_threshold(min_score)` returns `None` for a value not above 0 (which covers NaN), negative infinity for 1 or above, and otherwise `-M/(1-M)`.
- `BM25Searcher.search` binds the threshold with `AND m.score <= ?` in the outer WHERE clause of both SQL branches, ahead of the metadata filter suffix and of `LIMIT ? OFFSET ?`. Every value stays a bound parameter. Both score conversions, in `search` and in `search_chunks`, call `bm25_display_score`.
- On the real FTS fixture the five rows now score `0.7746412854760848` down to `0.7355778480479579`, best first. A threshold of 0.76 keeps `doc-4`, `doc-3`, `doc-2` with ranks 1, 2, 3, and limit 1 offset 1 returns `doc-3` with rank 2.
- `tests/unit/cli/test_search_min_score.py` drives the real CLI over a real temporary index of 20 Markdown files. With no threshold the four matching rows fall in score; a threshold midway between the two best scores leaves the strong document alone at rank 1; a threshold of 1 returns the empty list.
- `TestHybridMinScoreLeg` pins `min_score` on the BM25 leg of the hybrid path: the stronger match survives at 0.5, and a lexical-only match stays fused instead of losing its leg.
- The SC1 golden carries `1.3749981093775994e-06` (d3) and `1.313431110717347e-06` (d1), regenerated by the plan's command, with a dated paragraph on the class docstring.
- `bench/g19-2-min-score.json` has its after half. The probe keeps rank 1 `Saltiv Protocol Notes` and rank 2 `Qelron Protocol Notes`; both scores now read as one minus the old value, and each pair sums to 1 exactly.
- The `search` `--min-score` help text, the regenerated CLI reference, the changelog entry, the benchmarking notes and the fourth truth of `19-05-PLAN.md` describe the monotone score and its upper bound.

## After evidence

The committed artifact, byte for byte (unchanged since `d08f93c`). SHA-256 of the file: `9da7c7373ea16aac008628dc56fbf10207ee7aee358d28edeef16a0915638a2a`.

```json
{
  "gap": "G-19-2",
  "plans": [
    "19-11",
    "19-12"
  ],
  "decision": "monotone-map",
  "score_map": {
    "before": "1/(1+|bm25|)",
    "after": "|bm25|/(1+|bm25|)"
  },
  "probe": {
    "query": "Saltiv Protocol Notes",
    "index": "tests/fixtures/bench/corpus as collection bench-fixture (150 documents, BM25 only)",
    "before": {
      "head": "4ac6262d506f8441bcbb69fb207f3cabcc57f4e9",
      "rows": [
        [
          1,
          "Saltiv Protocol Notes",
          0.10570305094775757
        ],
        [
          2,
          "Qelron Protocol Notes",
          0.1527108535938998
        ]
      ],
      "min_score_0_12": [
        [
          1,
          "Qelron Protocol Notes",
          0.1527108535938998
        ]
      ],
      "min_score_0_23": []
    },
    "after": {
      "head": "37b6315f43e38cd8c9a3d4b7f8ec9d3ba606a938",
      "rows": [
        [
          1,
          "Saltiv Protocol Notes",
          0.8942969490522424
        ],
        [
          2,
          "Qelron Protocol Notes",
          0.8472891464061002
        ]
      ],
      "min_score_0_12": [
        [
          1,
          "Saltiv Protocol Notes",
          0.8942969490522424
        ],
        [
          2,
          "Qelron Protocol Notes",
          0.8472891464061002
        ]
      ],
      "min_score_0_23": [
        [
          1,
          "Saltiv Protocol Notes",
          0.8942969490522424
        ],
        [
          2,
          "Qelron Protocol Notes",
          0.8472891464061002
        ]
      ]
    }
  },
  "hybrid_bm25_leg": {
    "command": "sif search query --min-score: the BM25 leg of the hybrid path, read through HybridSearcher.search without a vector leg (limit 10)",
    "before": {
      "rows": [
        [
          1,
          "Saltiv Protocol Notes",
          0.10570305094775757
        ],
        [
          2,
          "Qelron Protocol Notes",
          0.1527108535938998
        ]
      ],
      "min_score_0_3": [],
      "min_score_0_5": []
    },
    "after": {
      "rows": [
        [
          1,
          "Saltiv Protocol Notes",
          0.8942969490522424
        ],
        [
          2,
          "Qelron Protocol Notes",
          0.8472891464061002
        ]
      ],
      "min_score_0_3": [
        [
          1,
          "Saltiv Protocol Notes",
          0.8942969490522424
        ],
        [
          2,
          "Qelron Protocol Notes",
          0.8472891464061002
        ]
      ],
      "min_score_0_5": [
        [
          1,
          "Saltiv Protocol Notes",
          0.8942969490522424
        ],
        [
          2,
          "Qelron Protocol Notes",
          0.8472891464061002
        ]
      ]
    }
  },
  "bench_compare": {
    "b0": {
      "before": {
        "mean": 0.0,
        "helped": 0,
        "hurt": 0,
        "unchanged": 100,
        "n": 100,
        "noise_floor": 0.01
      },
      "after": {
        "mean": 0.0,
        "helped": 0,
        "hurt": 0,
        "unchanged": 100,
        "n": 100,
        "noise_floor": 0.01
      }
    },
    "b1": {
      "before": {
        "mean": 0.0,
        "helped": 0,
        "hurt": 0,
        "unchanged": 100,
        "n": 100,
        "noise_floor": 0.01
      },
      "after": {
        "mean": 0.0,
        "helped": 0,
        "hurt": 0,
        "unchanged": 100,
        "n": 100,
        "noise_floor": 0.01
      }
    }
  },
  "sc1_golden_bm25_score": {
    "d3": {
      "before": 0.9999986250018905,
      "after": 1.3749981093775994e-06
    },
    "d1": {
      "before": 0.9999986865688892,
      "after": 1.313431110717347e-06
    }
  }
}
```

- **Probe.** Rank 1 is still `Saltiv Protocol Notes`, now at `0.8942969490522424`, and rank 2 is still `Qelron Protocol Notes`, now at `0.8472891464061002`. The better match shows the higher score. Each new value is one minus the old one to the last bit.
- **Thresholds.** `--min-score 0.12` and `--min-score 0.23` both keep the two matches, in the same order. Before, 0.12 kept only the weaker match and 0.23 kept nothing.
- **BM25 leg of the hybrid path.** With no threshold it returns the same two rows; at 0.3 and at 0.5 it now returns both, where before it returned no row.
- **Bench comparisons.** Against the committed B0 and B1 runs, both comparisons report n 100, mean 0.0, helped 0, hurt 0 and unchanged 100, the same as the before half. No rank moved, which is the evidence that fusion by list position did not change.
- **SC1 golden.** The artifact's two values equal the snapshot's, which the validator checks against the test module itself.
- `probe.after.head` is `37b6315f43e38cd8c9a3d4b7f8ec9d3ba606a938`, the Task 1 commit, which is the tree the eight capture commands ran on.

## Task Commits

Each task was committed atomically, by explicit path, on `gsd/phase-24-reverify`:

1. **Task 1: BM25 score rises with relevance and `--min-score` keeps the best matches (G-19-2)** - `37b6315` (fix)
2. **Task 2: Document the SC1 golden change and record the after-evidence** - `d08f93c` (docs)
3. **Task 3: Bring the written contract in line** - `38f4551` (docs)

**Plan metadata:** this SUMMARY and `.planning/WINDOWS.md` are committed separately, immediately after this file is written (docs: complete 19-12 plan).

## Gate Evidence

All commands ran in the main checkout with the checkout root as working directory. The multi-line gates of Task 2 and Task 3 were run from blocks extracted from the plan file; the eight capture commands and the write command of Task 2 were compared with the plan text and are byte-identical.

| Gate | Outcome |
|------|---------|
| **Task 1, before the commit** | |
| Precondition, read-only | met: `Decision: monotone-map` on its own line; artifact decision `monotone-map`, before half present, no after half |
| Gate 1, decision on record | `monotone-map on record in both`, exit 0 |
| Gate 2, four test files with `-x` | 241 passed in 1.12s |
| Gates 3 and 4, leftovers in the searcher | exit 0 and exit 0: no `m.score >= ?`, no `1.0 / (1.0 + abs(` |
| Gate 5, leftovers in the tests | exit 0: no lower-bound predicate and no `"m.score >=" not in sql` |
| Gate 6, red-derivation against the plan base | exit 0; the overlay's inner run: `3 failed, 1 passed, 72 deselected in 0.85s`, the CLI direction test and both `TestHybridMinScoreLeg` tests FAILED by name |
| Gate 7, `ty check src/sif/search/bm25.py` | All checks passed! |
| Gate 8, ruff on the five files | All checks passed!; 5 files already formatted |
| Acceptance criteria 1 to 9 | each PASS with its own command: predicate in the outer WHERE ahead of `LIMIT ? OFFSET ?` in both branches; threshold table; two conversion call sites; 0.76 keeps `doc-4`, `doc-3`, `doc-2`; limit 1 offset 1 gives `doc-3` rank 2; 24 named tests passed; snapshot values; red-derivation; ty |
| Search, CLI, MCP and integration subset | 1834 passed in 50.28s |
| **Tracer feedback gate, after the commit (`37b6315`)** | |
| Gates 1 to 8, re-run | all eight green again (241 passed in 1.02s) |
| **Task 2** | |
| Step 1, regeneration command | `[('d3', '1.3749981093775994e-06'), ('d1', '1.313431110717347e-06')]` |
| Captures 1 to 8, with the plan's prefix | all exit 0; neither comparison refused on the corpus fingerprint |
| Gate 1, `test_hybrid.py` and `test_bench_snapshot.py` | 89 passed (before the commit 1.58s, after it 1.50s) |
| Gate 2, snapshot values | exit 0 |
| Gate 3, after-evidence validator | `after-evidence OK`, exit 0, under bash and under zsh; exit 0 again at `d08f93c` |
| Gate 4, held-out snapshot and its test | exit 0, byte-identical to the plan base |
| Artifact diff against HEAD before the commit | 103 lines added, 0 removed; the before half identical to the committed one; valid JSON with one closing newline |
| `test_hybrid.py` against the Task 1 commit | 13 lines added, 0 removed: the docstring paragraph only |
| **Task 3** | |
| Gates 1 to 10 and 12, before the commit and again at `38f4551` | all exit 0; gate 10: All checks passed!, 238 files already formatted; gate 12: 49 passed |
| `make docs-generate` | rewrote one row of `docs/cli-reference.md` (the `search` `--min-score` row); `docs/configuration.md` byte-identical, SHA-256 `6dfa4c17d4a58db2529967a50bf7e8030bc73ad019c05ba07353d1d4bb3b2cd5` before and after; `docs/cli-reference.md` `38239d902a2182e61666554cf98ed3f87bd08227ec6124ef81adf119cfec454b` then `70bb9238bb7493e3ddd90ccaba12c0192fefd913aab3b9dea9be3425edf7af5d` |
| Gate 8, scope | exit 0: exactly the nine declared files differ from the plan base outside `.planning/` |
| Gate 11, full suite, before the commit | exit 0: 3303 passed, 1 skipped, 27 warnings in 207.04s; coverage 95.16%; `Required test coverage of 90.0% reached` |
| `--help` as the CLI renders it | `search` shows the new text; `vsearch` and `query` still show `Minimum score threshold` |
| **Plan-level verification, at `38f4551`** | |
| `pytest tests/unit/search tests/unit/cli tests/unit/mcp tests/integration/test_search_correctness.py -x --no-cov` | 1834 passed in 49.79s |
| `ruff check src tests && ruff format --check src tests` and `ty check` on both modules | All checks passed!; 238 files already formatted; All checks passed! twice |
| `make docs-generate && git diff --exit-code docs/` | exit 0, no diff; both reference hashes unchanged |
| Full suite, `env -u FORCE_COLOR NO_COLOR=1 pytest` | exit 0: 3303 passed, 1 skipped, 27 warnings in 212.39s; coverage 95.16%; `fail_under=90` reached |
| After-evidence validator, Task 2 gates | `after-evidence OK`, exit 0; 89 passed; snapshot values exit 0; held-out snapshot exit 0 |
| Task 1 gates 2 to 8 | all green again: 241 passed in 1.18s; no leftovers; red-derivation exit 0; ty and ruff clean |
| Task 1 gate 1, re-run after Task 2 | exit 1 on `AssertionError: after half present`, as its design requires once Task 2 has added the after half; its two decision clauses still hold |
| `gsd-tools check evaluation-scope --plan 19-12 --commits-only --raw` | `status: resolved`, `source: plan-subjects`, the three commits above; `changedFiles` is empty |
| Paths that differ from the plan base | eleven: the nine declared files and two planning artifacts (`bench/g19-2-min-score.json`, `19-05-PLAN.md`) |

The 27 warnings are the same pre-existing `ResourceWarning: unclosed database` messages that the summaries of 19-10 and 19-11 record. The one skipped test is the same single skip as in those records; none of the 17 tests this plan adds is skipped. The pass count moved from 3286 to 3303, which is those 17 tests.

## Files Created/Modified

- `src/sif/search/bm25.py` - `bm25_display_score` and `bm25_rank_threshold` above `class BM25Searcher`; the threshold bound through `AND m.score <= ?` in both SQL branches; the rewritten threshold comment; both score conversions call `bm25_display_score`. `search_chunks` is otherwise unchanged.
- `src/sif/cli/commands/search.py` - the `--min-score` help text of `search_cmd`, written as two adjacent literals. The `vsearch_cmd` and `query_cmd` copies are untouched.
- `tests/unit/cli/test_search_min_score.py` - new: `_write_corpus`, `_indexed`, `_search` and the two tests, on a corpus of one strong document, three notes and sixteen fillers.
- `tests/unit/search/test_bm25.py` - `bm25_rank_threshold` imported; six re-pinned tests; six new tests.
- `tests/unit/search/test_filters_sql.py` - the upper-bound predicate in the parameter-order assertion.
- `tests/unit/search/test_hybrid.py` - `_build_strong_weak_fts_db`, `TestHybridMinScoreLeg`, the two regenerated `bm25_score` values and the dated paragraph on the golden's docstring.
- `docs/cli-reference.md` - one row, regenerated by `make docs-generate`.
- `docs/changelog.md` - the `[Unreleased]` / `Changed` entry, directly after the entry of plan 19-10.
- `docs/benchmarking.md` - the SC1 values brought up to date in the CORR-02 paragraph; the `Score-direction note` after the clause that ends `weighting titles cannot improve a perfect ranking.`
- `.planning/milestones/v1.2-phases/19-search-correctness/19-05-PLAN.md` - the fourth truth amended in place, one line replaced by one line.
- `.planning/milestones/v1.2-phases/19-search-correctness/bench/g19-2-min-score.json` - the after half and `sc1_golden_bm25_score`; no before value changed.
- `.planning/WINDOWS.md` - entry 13, `unrun-verify`, for the Task 3 human check.
- `.planning/milestones/v1.2-phases/19-search-correctness/19-12-SUMMARY.md` - this file.

Nothing was created or deleted. `pyproject.toml` and `uv.lock` are untouched.

## Decisions Made

The decisions are listed in the frontmatter. In short:

- **One map, one bound, two named functions.** The SQL predicate and the Python filter of `search_chunks` both take their arithmetic from the same two functions, so the displayed score and the threshold cannot disagree again.
- **A threshold of 1 or more binds negative infinity.** It needs no separate code path: no bm25 value can be at or below it, so no row is kept.
- **Midway thresholds in the tests.** The bound is recomputed in floating point and can miss a row whose displayed score equals the threshold to the last bit. The searcher tests therefore place their thresholds between two rows' scores. The one CLI check that uses a row's own score asserts only what holds on either side of that boundary: that the best match is still first.

## Deviations from Plan

No gate was weakened, skipped or re-run with different settings, and no product default changed.

1. **[Process, order of observation] The fourth red run was observed in a reproduced state, after the golden had been regenerated.**
   - **Found during:** Task 1, Step 4
   - **Issue:** The plan's truth 6 and acceptance criterion 8 place the fourth red point before the golden is regenerated. The executor ran the regeneration command and wrote the two values before running `tests/unit/search/test_hybrid.py`, so the state "searcher wired, golden stale" no longer existed in the tree.
   - **Fix:** The two values were put back to their committed ones, the searcher was confirmed wired (`m.score <= ?` present once, both old values present), the file was run, and the regenerated values were restored. The result is the `5 failed, 69 passed` recorded under Red Runs.
   - **Verification:** Task 1 gate 2 passed with 241 afterwards; Task 2 Step 1 printed the two values again; the Task 2 gates compare the snapshot with them.
   - **Files modified:** none by this step beyond the two golden values the plan asks for.
2. **[Addition] One assertion in `test_search_applies_min_score`.** Besides the predicate text, the bound value and the weights, it asserts that the predicate's position precedes `LIMIT ? OFFSET ?`. The acceptance criterion says "in both SQL branches"; the parameter-order test covers the scoped branch and this covers the unfiltered one.
3. **[Addition] A rewritten comment in `test_min_score_applies_before_offset_with_global_ranks`.** The inherited comment said post-pagination filtering would have returned rank 1. At 0.76 that is no longer so, because the surviving rows are a prefix of the list. The comment now says what the test distinguishes: the global rank 2 against a renumbered rank 1.
4. **[Addition] One guard assertion in the second `TestHybridMinScoreLeg` test.** `assert "bm25_score" in d4.scores` precedes the read of the value, so the red state reports an assertion and not a `KeyError`.
5. **[Addition] The reason in the golden's docstring.** The plan lists that the values were regenerated and not derived by subtraction; the paragraph also says why, which is the plan's own prohibition 6: the subtraction loses digits.
6. **[Addition] `.planning/WINDOWS.md` entry 13.** The executor contract asks for every unrun verify to be appended to the cross-phase ledger. This project has `workflow.windows_enforce` off, so the entry is informational and does not block a ship.
7. **[Clarification] The CLI corpus has three groups of files.** The plan's sentence says "four groups" and enumerates three: the strong document, the three notes and the sixteen fillers. The enumeration was followed: 20 files, of which four match the query.

**Total deviations:** 1 process deviation with no file change, 5 additions, 1 clarification. **Impact on plan:** none on scope, gates or behaviour; the scope gate shows exactly the nine declared files.

## Issues Encountered

1. A hand-typed copy of the red-derivation gate differed from the plan's block by one comment line of the executor's own. The block was then extracted from the plan file and compared: the five command lines were identical, so the gate had run verbatim. From then on every multi-line gate was run from blocks extracted from the plan file.
2. Two slips in throwaway wrapper commands, neither of which produced a recorded result: an inspection one-liner that looked for `benchb0.json` because of a missing path separator, and a wrapper that first tried a script file that did not exist (exit 127) before running the golden check inline (exit 0).
3. An edit of the two golden values was refused because the formatter had touched the file since it was last read. The file was read again and the edit applied.

## Residual Observations (not fixed - outside this plan's scope)

- **Truth 10 of the plan names the vector-leg test without its class segment.** `tests/unit/search/test_vector.py::test_search_applies_min_score` is not a node id; the test is `TestVectorSearcher::test_search_applies_min_score`. It passes, and its file and `src/sif/search/vector.py` are byte-identical to the plan base.
- **Task 1's first gate is a start-of-plan gate.** Its third clause requires the artifact to have no after half, which Task 2 exists to add. Re-run after Task 2 it fails on `after half present`, by design.
- **`search_chunks` keeps its post-window filter**, as the plan says it must (the recorded deferral IN-05). A NaN threshold there drops every row, where `search` omits the predicate. Unchanged by this plan; the method's docstring records that it has no production caller.
- **The UAT's two thresholds no longer remove a match.** After the change, `--min-score 0.12` and `--min-score 0.23` on the bench-fixture index keep both matches, at 0.8943 and 0.8473. Whether that closes UAT test 2, whose wording is "weaker matches are removed and the best match survives", is for the UAT tester; the CLI test shows removal with a threshold midway between the two scores.
- **`ty check src/sif` as a whole was not run.** Only the two modules the plan names were checked, and both are clean. The summary of 19-10 records ten pre-existing diagnostics elsewhere in the package.
- **`query` scores without a breakdown are RRF values** around 0.01 to 0.03, so the same numeric threshold means something different there. The plan lists this as an observation, out of scope.

## Human Check (pending - not performed by the executor)

Task 3's verify block carries one `<human-check>`. The executor did not perform or approve it.

- **Test:** On an index with embedded chunks run `sif search query QUERY --min-score 0.3 --json` and the same without `--min-score`, with a query that matches documents lexically as well as semantically; compare the `scores` of the returned rows. Then run `sif search vsearch QUERY --min-score 0.3` as before.
- **Expected:** Without the threshold and with it, rows that match lexically carry a `bm25_score` beside their `vector_score`: the threshold keeps the stronger BM25 matches in the page. Before this plan the same thresholded command returned rows with no `bm25_score` at all, because its BM25 leg had been emptied. `vsearch --min-score` filters on similarity exactly as before.
- **Why a human:** The evidence artifact and the unit tests read the BM25 leg through the searcher; whether the real `sif query` output reads that way on the operator's own index is what this check confirms.
- **Status:** open. It is recorded as entry 13 of `.planning/WINDOWS.md` and is left for the end-of-phase verifier harvest, as `workflow.human_verify_mode: end-of-phase` provides.

## Model Cache and Default Database

- A read-only metadata snapshot of `/Users/forrest/Library/Caches/sif` (path, type, size and modification time of 128 entries) and of `~/Library/Application Support/sif` (3 entries) was taken before any test ran.
- After every `sif` capture of Task 2 both snapshots were identical to the baseline. The captures ran with `SIF_DB_PATH` and `SIF_CACHE_DIR` inside the plan's scratch directory; with `--bm25-only` the eval builds no embedder, and with `--no-save` it writes no run file. The scratch cache directory stayed empty.
- After each of the two full-suite runs exactly two entries of the real cache differed, by modification time only: `models/.lock/cross-encoder___ms-marco-MiniLM-L-6-v2` (0 bytes before and after) and the empty directory `models/cross-encoder`. This is the accepted T-19-36 behaviour of the project's reranker tests, which the plan's threat model records. The entry count stayed 128; no path was added or removed and no size changed, so no model was downloaded.
- The default database directory was identical to its baseline after every step. No `sif` command wrote to the default database.
- The plan's scratch directory and its record were removed with the plan's own cleanup command. `~/SynologyDrive` was not read, watched, indexed or copied. No package or model was downloaded, installed, added or removed.

## Threat Model Disposition

- T-19-31 (tampering, SQL construction): mitigated. The threshold is computed by `bm25_rank_threshold` and bound as a `?` parameter in the outer WHERE of both branches, ahead of the metadata filter parameters and of `LIMIT ? OFFSET ?`. `test_search_applies_min_score` pins the bound at position 3 and its place; the parameter-order test pins the scoped branch. Nothing is interpolated.
- T-19-32 (tampering, `--min-score` input): mitigated. 0, a negative value and NaN omit the predicate; a value between 0 and 1 binds `-M/(1-M)`; 1 or above returns no row. Each outcome has a test, and `--min-score 1` is covered through the real CLI.
- T-19-33 (repudiation, agreement of plan, truth, golden and evidence): mitigated. The fourth 19-05 truth is amended with a dated note and `numstat` is `1 1`. The golden values were regenerated from code and the validator cross-checks them against the artifact. The after half shows identical ranks and identical B0 and B1 deltas. No captured value failed its pin, so no stop was needed.
- T-19-34 (consumers of the published BM25 score): accepted, as the plan records. The change was authorised at the 19-11 checkpoint, and Task 1's first gate found both records in place before any source changed. The remedy is in the changelog entry: subtract an old threshold from 1.
- T-19-36 (real model cache during the full-suite gate): accepted, and observed exactly as described above.
- T-19-SC (package installs): no package was installed, added or removed; `pyproject.toml` and `uv.lock` are untouched.

No threat flags: no file adds an endpoint, auth path, file-access pattern or schema change beyond what the threat model records.

## Known Stubs

None. No test is skipped by this plan and every automated `<verify>` command ran. The one item not run is the human check recorded above.

## Next Phase Readiness

- UAT gap G-19-2 is closed in the automated sense at `38f4551`: `sif search search --min-score` keeps the best match, end to end through the real CLI, and the BM25 leg of `sif query --min-score` keeps its stronger matches through `HybridSearcher.search`. The human check of Task 3 is pending for the end-of-phase verifier.
- The evidence a later verifier needs is committed: `bench/g19-2-min-score.json` on both sides of the change, and the red-derivation gate, which can be re-run while `.git/gsd-plan-19-12-base` exists.
- Any script that compared BM25 scores against the old values, or selected strong matches with a low-score comparison, now reads the new map. The changelog entry says how to convert an old threshold.
- A post-push CI confirmation is a manual follow-up and is not claimed here.
- Not done by this executor, by instruction: `STATE.md` and `ROADMAP.md` are untouched. `19-UAT.md` and the other Phase 19 planning artifacts are untouched. The orchestrator owns those writes. Executing this plan re-stales the verifications of Phases 18 and 24.

## Self-Check: PASSED

Run at `38f4551`, immediately before this SUMMARY was written:

- Files: the eleven changed files are present on disk; nothing was created or deleted besides the new test file.
- Commits: `37b6315`, `d08f93c` and `38f4551` are ancestors of HEAD, and `git rev-list --count 0744e83..HEAD` is 3.
- `gsd-tools check evaluation-scope --plan 19-12 --commits-only` resolved the same three commits.
- Plan base record present and equal to `0744e83b5308f2c2235d81dee59b96ca02d453d3`.
- Every artifact, `contains` string, export and key-link pattern of the plan's `must_haves` table checked against the tree: all pass. Prohibitions 1 to 6 checked: all hold.
- All twelve automated gates of Task 3, the four of Task 2 and gates 2 to 8 of Task 1 pass at `38f4551`. Task 1 gate 1 is a start-of-plan gate: after Task 2 it exits 1 on its after-half clause by design, as recorded under Gate Evidence.
- Working tree clean outside `.planning/`; the only modified path is `.planning/WINDOWS.md`, which is committed with this file.

Not covered by that run, because this file did not exist yet. The command that makes the commit checks them first and is refused unless every one of them passes: the frontmatter parses with `status: complete` and eight coverage entries; the fenced block under After evidence equals `git show HEAD:bench/g19-2-min-score.json` byte for byte; this file carries the plan base SHA and the summary lines of the four red runs. Their outcome is in the executor's return message.

---
*Phase: 19-search-correctness*
*Completed: 2026-11-26*
