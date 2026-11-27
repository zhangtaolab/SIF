---
phase: 19-search-correctness
plan: 13
subsystem: search
tags: [bm25, min-score, exact-threshold, displayed-score, sql-predicate, gap-closure, uat, corr-03, g-19-8, evidence, changelog]

requires:
  - phase: 19-search-correctness
    provides: "19-12: the monotone displayed-score map |bm25|/(1+|bm25|) and its -M/(1-M) bound, with the plan base byte-identical to the v1.2.4 tag 6089078; the committed bench corpus and saved runs b0.json/b1.json; CONTEXT D-06 and the locked rule that BM25 min_score is applied before pagination"
provides:
  - "BM25Searcher.search binds AND abs(m.score) / (1.0 + abs(m.score)) >= ? with min_score as given, in the outer WHERE of both SQL branches ahead of LIMIT/OFFSET; the converted bound and bm25_rank_threshold are gone"
  - "tests/unit/cli/test_search_exact_threshold.py: UAT test 8 through the real CLI on the committed bench corpus, plus the 56-query sweep through BM25Searcher"
  - "Re-pinned and new searcher tests: SQL text and binding, real FTS rows in both branches at two title weights, edge values 0/negative/NaN/1/2.5/infinity, and bit-for-bit SQL-vs-Python agreement over 100,189 finite doubles"
  - "bench/g19-8-exact-threshold.json: 40 of 84 bench rows dropped at their own displayed score before and 0 after, with identical scores, one-step outcomes, fixed-threshold counts and B0/B1 deltas"
  - "The Unreleased/Fixed changelog entry naming 1.2.4 and the four-decimal limit, and the fourth truth of 19-05-PLAN.md amended once more with a dated 19-13 note"
affects: ["19 (UAT gap G-19-8; the phase re-verification and UAT)", "17, 18, 20, 21, 22, 24 (their verifications re-stale)"]

# Actuals (#2632): tokens are chars/4 over the unified diff from the plan base to the last task commit,
# 24,133 chars in the five files outside .planning/ and 7,202 in the two planning artifacts (31,335 in all).
# commits is measured from the ledger (.git/gsd-plan-head-before-19-13), seeded from the plan base record.
actuals:
  tokens: 7834
  tasks: 3
  commits: 3
  plan_head_before: 54acb111968c11f34e16cf0dde0701e95d82d119
  plan_head_after: 0902b28715020f71dae203b33e508407e802b16b

tech-stack:
  added: []
  patterns:
    - "A threshold on a displayed value compares the displayed expression itself in SQL and binds the user's value unchanged, so equality cannot be lost to a recomputed inverse"
    - "An exactness claim is pinned bit-for-bit over a deterministic finite sample beside a before/after artifact captured on the base and changed searchers"

key-files:
  created:
    - tests/unit/cli/test_search_exact_threshold.py
    - .planning/milestones/v1.2-phases/19-search-correctness/bench/g19-8-exact-threshold.json
  modified:
    - src/sif/search/bm25.py
    - tests/unit/search/test_bm25.py
    - tests/unit/search/test_filters_sql.py
    - docs/changelog.md
    - .planning/milestones/v1.2-phases/19-search-correctness/19-05-PLAN.md

key-decisions:
  - "min_score is bound as given, not converted: the SQL predicate compares |m.score|/(1+|m.score|) with ?, and a NaN is never bound because NULL would drop every row."
  - "bm25_rank_threshold is removed with its table test: it shipped in 1.2.4, but its only caller was the replaced line and no option, output field or MCP field exposes it."
  - "The Task 3 human check was not performed by the executor under end-of-phase harvest; it is WINDOWS entry 14, with the two CLI tests and the evidence artifact as the automated backstop."

patterns-established:
  - "Threshold tests may sit exactly on a row's displayed score now; the earlier mid-point-only rule existed because the converted bound could miss the boundary."
  - "A scope gate that scans untracked files must account for pre-existing local tool directories; the executor excluded one through .git/info/exclude rather than editing tracked files."

requirements-completed: [CORR-03]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "sif search search --min-score keeps a row whose displayed score equals the threshold to the last bit; 0, a negative value and NaN omit the predicate; 1, 2.5 and infinity keep no row; the converted bound and its helper are gone"
    requirement: CORR-03
    verification:
      - kind: unit
        ref: "tests/unit/search/test_bm25.py#TestBM25Searcher.test_search_applies_min_score + test_min_score_binding_table (7 cases) + test_values_not_above_zero_keep_every_row (3) + test_min_score_at_or_above_one_keeps_nothing (3) + TestExactMinScore.test_real_rows_are_kept_at_their_own_displayed_score[scoped|unfiltered] + test_weighted_rows_are_kept_at_their_own_displayed_score[weight-1|weight-10] + test_sql_score_expression_matches_the_display_map_bit_for_bit"
        status: pass
      - kind: integration
        ref: "tests/unit/cli/test_search_exact_threshold.py#test_the_cli_keeps_a_row_at_its_own_displayed_score + test_every_bench_row_survives_its_own_displayed_score"
        status: pass
      - kind: other
        ref: "Task 1 verify block: five-file gate 252 passed; base-overlay red-derivation 5 failed, 1 passed, 54 deselected; ty/ruff clean; greps for the old predicate and the removed helper empty"
        status: pass
    human_judgment: false
  - id: D2
    description: "The before/after evidence artifact: 40 of 84 bench rows dropped at their own displayed score on the base searcher over 37 queries and 0 after, with identical scores, one-step outcomes, fixed-threshold counts, oracle matches and B0/B1 deltas on both sides; the Kelpri probe keeps rank 1 only after"
    verification:
      - kind: other
        ref: "bench/g19-8-exact-threshold.json validated by the plan's pinned-value validator (exact-threshold evidence OK); each side import-checked (before: base copy; after: checkout)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The written contract agrees with the code: the Unreleased/Fixed changelog entry names 1.2.4 and the four-decimal limit, every released section is byte-identical, and the fourth truth of 19-05-PLAN.md carries the displayed-score predicate with one added and one removed line and both dated notes"
    verification:
      - kind: other
        ref: "Task 3 verify block: changelog phrase count 1; released-section byte comparison clean; 19-13 and 19-12 notes once each; predicate once; numstat 1 1; five-file and plan/summary scope gates green; docs-generate no diff; full suite 3314 passed, 1 skipped at 95.16%"
        status: pass
    human_judgment: false
  - id: D4
    description: "The Task 3 human check: on an index of the checker's own choosing, a row survives --min-score equal to its --json score and keeps its rank"
    verification: []
    human_judgment: true
    rationale: "UAT test 8 was a human CLI test; the automated tests reproduce it on the committed corpus, and this check confirms the behaviour on a live index of the checker's choice. The executor did not run it (end-of-phase harvest); it is recorded as WINDOWS entry 14."

# Metrics
duration: 12min
completed: 2026-11-27
status: complete
---

# Phase 19 Plan 13: Exact `--min-score` Summary

**`sif search search --min-score` now keeps a row whose displayed score equals the threshold to the last bit: the SQL predicate compares `abs(m.score)/(1.0+abs(m.score))` with `min_score` bound as given, replacing the converted `-M/(1-M)` bound that dropped 40 of 84 bench rows at apparent equality.**

## Performance

- **Duration:** 12 min (739 s)
- **Started:** 2026-11-27T09:23:00Z
- **Completed:** 2026-11-27T09:35:19Z
- **Tasks:** 3
- **Files modified:** 7 (1 source, 3 test of which 1 is new, 1 doc, 2 planning artifacts), plus this SUMMARY and `.planning/WINDOWS.md`

## Accomplishments

- `BM25Searcher.search` compares the displayed score itself, `AND abs(m.score) / (1.0 + abs(m.score)) >= ?`, bound with `min_score` as given, in the outer WHERE of both SQL branches ahead of the metadata filter and of `LIMIT ? OFFSET ?`. A row whose displayed score equals the threshold is kept with the same score and rank; the score map, ordering, the rows kept at any other threshold and `search_chunks` are unchanged.
- The threshold helper `bm25_rank_threshold` and its converted bound are gone from `src/` and `tests/`; `bm25_display_score`, both score conversions and `search_chunks` are untouched.
- Edge values have defined outcomes: 0, a negative value and NaN omit the predicate (a NaN would reach SQLite as NULL and drop every row); 1, 2.5 and infinity are bound like any other value and keep no row by arithmetic.
- The re-pinned and new tests hold the contract on the executed SQL text and bound value, on real FTS rows in both branches at title weights 1.0 and 10.0, at each row's own score and one float step either side, and on the SQL expression vs `bm25_display_score` bit for bit over 100,189 finite doubles.
- The before/after evidence is committed as `bench/g19-8-exact-threshold.json`, captured with a copy of the package whose searcher is the one at the plan base and with the checkout's own package; a validator pins every value.
- The changelog records the fix under `[Unreleased]`/`Fixed`, naming 1.2.4 as the release whose behaviour changes and the four-decimal display limit, with every released section byte-identical; the fourth truth of `19-05-PLAN.md` is amended once more, one line added and one removed, keeping the 19-12 note.

## Plan Base

`54acb111968c11f34e16cf0dde0701e95d82d119` — HEAD before Task 1, recorded at `.git/gsd-plan-19-13-base` and left in place. The searcher at that base is byte-identical to the v1.2.4 tag `6089078`.

## Task Commits

Each task was committed atomically:

1. **Task 1: A row survives `--min-score` equal to its own displayed score** — `1ed9030` (fix)
2. **Task 2: Record the before and after evidence** — `5ad35b1` (chore)
3. **Task 3: Changelog entry and the amended 19-05 truth** — `0902b28` (docs)

**Plan metadata:** this SUMMARY's own commit (the metadata commit that follows it).

## Files Created/Modified

- `src/sif/search/bm25.py` — displayed-score predicate bound with `min_score`; the threshold helper removed; comment rewritten.
- `tests/unit/search/test_bm25.py` — `_MIN_SCORE_PREDICATE`, the binding table, edge-value tests, `TestExactMinScore` (real rows, weighted rows, bit-for-bit), the 100,189-value sample; re-pinned tests.
- `tests/unit/search/test_filters_sql.py` — parameter order with `min_score` bound as given, ahead of the filter parameters and `LIMIT/OFFSET`.
- `tests/unit/cli/test_search_exact_threshold.py` — new: UAT test 8 through the real CLI on the committed corpus and the 56-query sweep.
- `docs/changelog.md` — the `[Unreleased]`/`Fixed` entry; nothing under a released heading changed.
- `.planning/milestones/v1.2-phases/19-search-correctness/19-05-PLAN.md` — fourth truth amended in place.
- `.planning/milestones/v1.2-phases/19-search-correctness/bench/g19-8-exact-threshold.json` — new evidence artifact.

## Red Run

Both red runs were observed on 2026-11-27 against the unchanged searcher, after the tests were written.

**Red run 1** — `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/cli/test_search_exact_threshold.py -q --no-cov -p no:cacheprovider`:

```text
FAILED tests/unit/cli/test_search_exact_threshold.py::test_the_cli_keeps_a_row_at_its_own_displayed_score
FAILED tests/unit/cli/test_search_exact_threshold.py::test_every_bench_row_survives_its_own_displayed_score
2 failed in 0.78s
```

The first failed on the equality of the kept document ids with an empty kept list; the second on the surviving-score assertion for the Kelpri row (`[] == [0.8942969341194331]`).

**Red run 2** — `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search/test_bm25.py tests/unit/cli/test_search_min_score.py tests/unit/search/test_filters_sql.py tests/unit/search/test_hybrid.py tests/unit/cli/test_search_exact_threshold.py -q --no-cov -p no:cacheprovider`:

```text
FAILED tests/unit/search/test_bm25.py::TestBM25Searcher::test_search_applies_min_score
FAILED tests/unit/search/test_bm25.py::TestBM25Searcher::test_min_score_binding_table[0.5-0.5]
FAILED tests/unit/search/test_bm25.py::TestBM25Searcher::test_min_score_binding_table[0.8-0.8]
FAILED tests/unit/search/test_bm25.py::TestBM25Searcher::test_min_score_binding_table[1.0-1.0]
FAILED tests/unit/search/test_bm25.py::TestBM25Searcher::test_min_score_binding_table[1.5-1.5]
FAILED tests/unit/search/test_bm25.py::TestExactMinScore::test_real_rows_are_kept_at_their_own_displayed_score[scoped]
FAILED tests/unit/search/test_bm25.py::TestExactMinScore::test_real_rows_are_kept_at_their_own_displayed_score[unfiltered]
FAILED tests/unit/search/test_bm25.py::TestExactMinScore::test_weighted_rows_are_kept_at_their_own_displayed_score[weight-10]
FAILED tests/unit/search/test_filters_sql.py::TestBm25ParamOrder::test_weights_match_collection_min_score_filter_limit_offset
FAILED tests/unit/cli/test_search_exact_threshold.py::test_the_cli_keeps_a_row_at_its_own_displayed_score
FAILED tests/unit/cli/test_search_exact_threshold.py::test_every_bench_row_survives_its_own_displayed_score
11 failed, 241 passed in 1.25s
```

**Red derivation on the base searcher** — the plan's overlay gate (base `54acb11`, only `src/sif/search/bm25.py` replaced) reported `5 failed, 1 passed, 54 deselected` with these five by name: the two CLI tests, `test_real_rows_are_kept_at_their_own_displayed_score[scoped]`, `[unfiltered]`, and `test_weighted_rows_are_kept_at_their_own_displayed_score[weight-10]`. The `weight-1` case passes on the base searcher by design.

## Before and After Evidence

`bench/g19-8-exact-threshold.json` (captured with the base-searcher copy on the before side and the checkout on the after side; each side import-checked):

```json
{
  "gap": "G-19-8",
  "plan": "19-13",
  "uat_test": 8,
  "index": "tests/fixtures/bench/corpus as collection bench-fixture (150 documents, BM25 only)",
  "heads": {
    "before": "54acb111968c11f34e16cf0dde0701e95d82d119",
    "after": "1ed9030d1a3ee286cf878133e3920b5dd54d0bac"
  },
  "sweep": {
    "command": "the 56 queries of tests/fixtures/bench/queries.json at limit 10 through BM25Searcher.search, scoped to bench-fixture: for every row of every unfiltered page, a search whose min_score is that row displayed score, then one float step below it and one above",
    "before": {
      "dropped_at_own_score": 40,
      "dropped_one_ulp_above": 84,
      "highest_score": 0.9649301719152716,
      "kept_one_ulp_below": 84,
      "lowest_score": 0.8472891154288171,
      "oracle_mismatches_at_fixed_thresholds": 0,
      "queries": 56,
      "queries_with_a_dropped_row": 37,
      "rows": 84,
      "rows_kept_at_fixed_thresholds": {
        "0.12": 84,
        "0.23": 84,
        "0.3": 84,
        "0.5": 84,
        "0.85": 70,
        "0.89": 70
      },
      "sqlite": "3.51.0"
    },
    "after": {
      "dropped_at_own_score": 0,
      "dropped_one_ulp_above": 84,
      "highest_score": 0.9649301719152716,
      "kept_one_ulp_below": 84,
      "lowest_score": 0.8472891154288171,
      "oracle_mismatches_at_fixed_thresholds": 0,
      "queries": 56,
      "queries_with_a_dropped_row": 0,
      "rows": 84,
      "rows_kept_at_fixed_thresholds": {
        "0.12": 84,
        "0.23": 84,
        "0.3": 84,
        "0.5": 84,
        "0.85": 70,
        "0.89": 70
      },
      "sqlite": "3.51.0"
    }
  },
  "probe": {
    "query": "sif search search kelpri protocol -c bench-fixture -n 10 --json, then the same with --min-score set to the score of rank 1 as --json printed it",
    "before": {
      "rows": [
        [
          1,
          "Kelpri Protocol Notes",
          0.8942969341194331
        ],
        [
          2,
          "Talven Protocol Notes",
          0.8482321063105717
        ]
      ],
      "min_score_own_displayed_score": []
    },
    "after": {
      "rows": [
        [
          1,
          "Kelpri Protocol Notes",
          0.8942969341194331
        ],
        [
          2,
          "Talven Protocol Notes",
          0.8482321063105717
        ]
      ],
      "min_score_own_displayed_score": [
        [
          1,
          "Kelpri Protocol Notes",
          0.8942969341194331
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
  }
}
```

Interpretation: only the count of rows dropped at their own displayed score changes, from 40 of 84 over 37 queries to 0 of 84 over 0 queries. Displayed scores, the one-ULP outcomes, the fixed-threshold row counts, the oracle comparison and the B0/B1 deltas are identical before and after, so nothing else moved.

## Decisions Made

- **Bind `min_score` as given.** The predicate compares the displayed expression `abs(m.score)/(1.0+abs(m.score))` with `?`; no Python-side inverse is computed. Edge gate: `if options.min_score > 0` binds, so 0, negatives and NaN omit the predicate; a value of 1 or more keeps no row by arithmetic.
- **Remove `bm25_rank_threshold` with its table test.** Released in 1.2.4, but its only caller was the replaced line; no public surface exposed it. Behaviour change against 1.2.4 is recorded in the changelog (a row at exact equality is now kept).
- **`test_search_applies_min_score` pins both text and place**, so the unfiltered branch is covered too; the scoped branch is pinned by the parameter-order test in `test_filters_sql.py`.
- **The new CLI test module stands alone** (no sibling test imports) so the plan's base overlay can run it with only the package and bench fixtures.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pre-existing untracked `.codebuddy/` local config broke the five-file scope gate**
- **Found during:** Task 3 (scope gates)
- **Issue:** `.codebuddy/settings.local.json` existed untracked before this plan (present at session start, created hours earlier) and is not matched by `.gitignore`, so `git ls-files --others --exclude-standard` reported it outside the declared five-file scope, failing the gate.
- **Fix:** added `.codebuddy/` to `.git/info/exclude` (local-only, never committed; no tracked file touched). `.gitignore` itself was left alone because it is outside the plan's declared scope.
- **Files modified:** `.git/info/exclude` (git metadata, untracked)
- **Verification:** the five-file scope gate and the plan/summary scope gate both pass; the five declared files are the only changes outside `.planning/`.
- **Committed in:** none (no tracked change).

**2. [Rule 3 - Blocking] ruff F841 on an unused local in the second CLI test**
- **Found during:** Task 1 Step 4 (lint)
- **Issue:** the second CLI test built a `CliRunner` it never used, because `_indexed_corpus` drives the CLI itself.
- **Fix:** removed the unused assignment.
- **Files modified:** `tests/unit/cli/test_search_exact_threshold.py`
- **Verification:** `ruff check` and `ruff format --check` clean; the test still passes.
- **Committed in:** `1ed9030`

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** No scope creep. Both were necessary to satisfy the plan's own gates; neither touches product behaviour.

## Issues Encountered

None.

## Authentication Gates

None.

## Human Check

Task 3's `<human-check>` was not performed by this executor. Under `workflow.human_verify_mode: end-of-phase` it is not a mid-flight stop; the automated backstop is the two CLI tests on the committed corpus plus `bench/g19-8-exact-threshold.json`. It is recorded as **WINDOWS entry 14** (`unrun-verify`, open) for the end-of-phase verifier harvest: on an isolated index of the checker's choosing, `--min-score` equal to a row's `--json` score keeps that row with the same score and rank, and a score copied from the four-decimal formats can still round above the exact score (R2-04, not changed here).

Note on the plan-level verification list: `make docs-generate && git diff --exit-code docs/` reports the intentional `docs/changelog.md` change. The Task 3 gate narrows the same check to the two generated documents, which are byte-identical after a generator run; that is the form recorded as passing.

## Threat Model Disposition

- **T-19-37 (tampering, SQL construction):** mitigated. `min_score` is appended to `params` as given and bound through one `?` in the constant fragment; no value is interpolated. `test_search_applies_min_score` pins the text, position 3 and its place before `LIMIT ? OFFSET ?`; the parameter-order test pins the scoped branch.
- **T-19-38 (tampering, `--min-score` input):** mitigated. 0, a negative value and NaN omit the predicate (`test_values_not_above_zero_keep_every_row`, the binding table, the zero/negative mock tests); a value between 0 and 1 is bound as given; 1, 2.5 and infinity are bound like any other value and keep no row (`test_min_score_at_or_above_one_keeps_nothing`, `test_min_score_of_one_returns_no_results` through the CLI). A NaN is never bound.
- **T-19-39 (repudiation, agreement of plan, truth, tests and evidence):** mitigated. The fourth 19-05 truth carries the predicate and a dated 19-13 note with `numstat 1 1`; the artifact was captured on the base searcher and the changed searcher, and its validator compares every pinned value including the SQLite build; the base-overlay gate re-derives the five behavioural red tests. No pinned value failed.
- **T-19-40 (information disclosure, consumers from 1.2.4):** accepted, as the plan records. A script that relied on the drop at exact equality now receives the row, which the help text has promised; no score, ranking or other-threshold row changes. The changelog entry names 1.2.4, and lowering the threshold by one float step drops the row, as the artifact shows.
- **T-19-41 (denial of service, default database and caches during capture):** mitigated. Every capture command ran as written with its scratch prefix (`SIF_DB_PATH`/`SIF_CACHE_DIR` under the scratch directory); the checkout fingerprint and both import-side checks passed; no `models` directory appeared in the scratch cache; no command needed an embedder; the scratch directory was removed after the verify block.
- **T-19-SC (supply chain):** no package was installed, added or removed; `pyproject.toml` and `uv.lock` are untouched.

No threat flags: no file adds an endpoint, auth path, file-access pattern or schema change beyond what the threat model records.

## Known Stubs

None. No test is skipped by this plan and every automated `<verify>` command ran. The one unrun human check is tracked in the coverage block (D4) and in WINDOWS entry 14.

## Next Phase Readiness

- UAT gap G-19-8 is closed in the automated sense at `0902b28`: `sif search search --min-score` keeps a row at its own displayed score end to end through the real CLI, on real FTS rows in both SQL branches and at two title weights, and the SQL expression agrees with `bm25_display_score` bit for bit over the committed sample. MCP `lex_search` and the BM25 leg of `sif search query --min-score` and MCP `query` share the same searcher.
- The evidence a later verifier needs is committed: `bench/g19-8-exact-threshold.json` on both sides of the change, and the base-overlay gate, which can be re-run while `.git/gsd-plan-19-13-base` exists.
- Review items R2-04 (four-decimal printed scores) and R2-01 (threshold discoverability) remain open; the `search_chunks` post-window filter (IN-05) and the vector leg's threshold are untouched.
- Executing this plan re-stales the verifications of Phases 17, 18, 20, 21, 22 and 24; Phase 19 is re-verified after this round.

---
*Phase: 19-search-correctness*
*Completed: 2026-11-27*

## Self-Check: PASSED

Run at `0902b28`, before this SUMMARY was committed:

- Every file this plan declares is present on disk (the searcher, the three test files, the changelog, the amended `19-05-PLAN.md`, the evidence artifact and this SUMMARY).
- Commits `1ed9030`, `5ad35b1` and `0902b28` are ancestors of HEAD; `git rev-list --count 54acb11..HEAD` is 3.
- `gsd_run check evaluation-scope --plan 19-13 --commits-only` resolves the same three commits by subject.
- Plan base record present and equal to `54acb111968c11f34e16cf0dde0701e95d82d119`; the ledger `.git/gsd-plan-head-before-19-13` holds the same base.
- Frontmatter parses with `status: complete` and four coverage entries; `actuals.commits` is the measured 3.
- Automated gates: the red runs and the base-overlay gate (5 failed, 1 passed, 54 deselected) as recorded above; Task 1's remaining gates (`252 passed`, greps, `ty`, `ruff`); Task 2's four gates including the validator (`exact-threshold evidence OK`); Task 3's gates including the full suite (`3314 passed, 1 skipped` at 95.16%).
- The one unchecked item is the Task 3 `<human-check>`, recorded as WINDOWS entry 14 for the end-of-phase harvest and classified `human_judgment: true` in the coverage block.

