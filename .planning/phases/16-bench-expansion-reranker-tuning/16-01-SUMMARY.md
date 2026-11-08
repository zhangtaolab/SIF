---
phase: 16-bench-expansion-reranker-tuning
plan: "01"
subsystem: search
tags: [benchmark, ndcg, hit-rate, latency, pytest, click, rich]

# Dependency graph
requires:
  - phase: 15-search-quality-configuration-hybrid-weights-query-suggestions
    provides: SearchOptions.rrf_k/bm25_weight/vector_weight fields and SIF_ settings (the baseline bench now resolves)
provides:
  - dcg_at_k/ndcg_at_k/hit_at_k/percentile pure metric helpers in sif.search.benchmark
  - resolve_corpus_root/result_key path-keyed relevance rule (corpus-relative POSIX keys)
  - SearchEvaluator.report -> BenchReport with global + per-category (CATEGORIES order) nDCG@10/Hit@10, warmed p50/p95, separate cold start, and legacy flat metrics merged by to_dict()
  - measure_query_times warmed-latency primitive (injectable clock)
  - bench_cmd helpers _load_embedder/_resolve_collection_ids/_build_options/_measure_state/_render_report that later --sweep/--rerank plans extend
  - _settings_mock(**overrides) CLI test helper (rerank fields land in later plans)
affects: [16-03 fixture pack, 16-04 sweep, 16-05 snapshot, rerank-state bench plans]

# Actuals (#2632) — same estimateTokens scale (chars/4 over the realized diff).
actuals:
  tokens: 15611
  tasks: 3
  commits: 5

# Tech tracking
tech-stack:
  added: []  # stdlib only: math, time, dataclasses, pathlib
  patterns:
    - "Injectable clock for latency logic (structural asserts, no wall-clock races)"
    - "Graded report layers beside legacy evaluate() — flat keys merged at top level for backward compat"
    - "Zero-behavior skeletons in the RED commit so the suite collects (Phase 11 house pattern)"

key-files:
  created:
    - tests/unit/search/test_benchmark_metrics.py
  modified:
    - src/sif/search/benchmark.py
    - src/sif/cli/commands/bench.py
    - tests/unit/cli/test_bench.py
    - tests/unit/cli/test_database_lifecycle.py

key-decisions:
  - "report(clock=...) measures warmed latency via measure_query_times; cold start is the single first warm-up call and never a p50/p95 sample (D-05)"
  - "Bench baseline resolves fusion knobs from current SIF_ settings (D-09, fixes Phase 15 IN-02); SearchPipeline built once per state inside the connection context; collection ids resolved once before the loop"
  - "precision_at_k/recall_at_k binarize internally (grade > 0) so graded fixtures never exceed 1.0 while legacy 0/1 fixtures are byte-unchanged (Pitfall 8)"
  - "Path-keyed relevance: corpus_root resolved once (relative declared root joins the fixture dir, absolute as-is, explicit ctor arg wins); result keys are corpus-relative POSIX with an absolute-path fallback"

patterns-established:
  - "Pattern: report() computes every metric from one search_fn result list per query; the CLI never computes formulas inline"
  - "Pattern: _settings_mock(**overrides) for every get_settings patch in bench CLI tests (Pitfall 10 wrong-reason-pass guard)"

requirements-completed: [EVAL-01, EVAL-02]

coverage:
  - id: D1
    description: "Graded metric spine: dcg_at_k/ndcg_at_k/hit_at_k/percentile/resolve_corpus_root/result_key pure helpers + SearchEvaluator.report with per-category breakdown"
    requirement: EVAL-01
    verification:
      - kind: unit
        ref: "tests/unit/search/test_benchmark_metrics.py#TestNdcgAtK/TestHitAtK/TestResolveCorpusRoot/TestResultKey/TestReportGradedFixture/TestReportLegacyFixture"
        status: pass
    human_judgment: false
  - id: D2
    description: "sif bench table and --json render NDCG@10, Hit@10, MRR, precision@k/recall@k, per-category rows; JSON strict-parses at COLUMNS=80 with legacy flat keys preserved"
    requirement: EVAL-01
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_bench.py#test_bench_json_graded_metrics/test_bench_json_output/test_bench_json_parses_at_narrow_width"
        status: pass
    human_judgment: false
  - id: D3
    description: "Warmed p50/p95 latency and separately-reported cold start through an injectable clock (warm-up pass discarded, first call captured as cold start)"
    requirement: EVAL-01
    verification:
      - kind: unit
        ref: "tests/unit/search/test_benchmark_metrics.py#TestPercentile/TestMeasureQueryTimes/TestReportLatency + tests/unit/cli/test_bench.py#test_bench_json_latency_metrics"
        status: pass
    human_judgment: false
  - id: D4
    description: "Bench baseline runs current SIF_ fusion settings (IN-02 fixed) with one hoisted SearchPipeline per state; invalid settings surface as ClickException"
    requirement: EVAL-01
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_bench.py#test_bench_settings_baseline_and_single_pipeline/test_bench_invalid_settings_click_exception"
        status: pass
    human_judgment: false
  - id: D5
    description: "Legacy relevant_docids fixtures keep working through evaluate() and report(); binary precision/recall cap graded fixtures at 1.0; empty-queries and malformed-JSON fixtures exit non-zero"
    requirement: EVAL-02
    verification:
      - kind: unit
        ref: "tests/unit/search/test_benchmark_metrics.py#TestBinaryPrecisionRecall/TestEvaluateGradedFixture/TestEmptyQueriesGuard + tests/unit/cli/test_bench.py#test_bench_empty_queries_exits_nonzero/test_bench_malformed_fixture_exits_nonzero + tests/unit/search/test_benchmark.py (byte-unmodified, green)"
        status: pass
    human_judgment: false

# Metrics
duration: 17 min
completed: 2026-11-08
status: complete
---

# Phase 16 Plan 01: Graded Bench Report Summary

**nDCG@10/Hit@10 with per-category breakdown, warmed p50/p95 latency, and a settings-resolved baseline layered onto `SearchEvaluator`/`sif bench` — legacy flat metrics byte-compatible**

## Performance

- **Duration:** 17 min
- **Started:** 2026-11-08T13:21:38Z
- **Completed:** 2026-11-08T13:38:13Z
- **Tasks:** 3 (Task 2 executed as TDD: RED -> GREEN, REFACTOR not needed)
- **Files modified:** 5 (1 created, 4 modified)

## Accomplishments

- Pure graded-metric helpers (`dcg_at_k`, `ndcg_at_k`, `hit_at_k`, `percentile`) pinned to hand-verified reference values; `BenchReport.to_dict()` keeps `mrr`/`precision@<k>`/`recall@<k>` flat keys beside `ndcg_at_10`/`hit_at_10` and all four CATEGORIES keys in declared order
- Path-keyed graded relevance: `resolve_corpus_root` (relative root joins the fixture dir, absolute as-is, explicit constructor argument wins) and `result_key` (corpus-relative POSIX, absolute fallback, never opens paths); legacy `relevant_docids` fixtures map to grade 1 and still work through both `evaluate()` and `report()`
- Warmed latency: `measure_query_times` discards one warm-up pass then times each query; `report(clock=...)` fills `p50_ms`/`p95_ms` and reports the single first warm-up call as `cold_start_ms`, never mixed into the percentile samples (D-05)
- `bench_cmd` reworked into `_load_embedder`/`_resolve_collection_ids`/`_build_options`/`_measure_state`/`_render_report`: one hoisted `SearchPipeline` per state inside the connection context, collection ids resolved once, options carry `settings.rrf_k/bm25_weight/vector_weight` (D-09, fixes Phase 15 IN-02), `pydantic.ValidationError` and malformed fixture JSON surface as `ClickException`
- Fixture validation: indexed ValueErrors for missing both relevance fields (message names `relevant_docids`, keeping the byte-unmodified legacy test reachable), mixed schemas, unknown category/split, out-of-range grades, and empty `queries` lists

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end graded bench report** - `092ba97` (feat, tracer; verify re-run passed, auto mode active -> expanded without checkpoint)
2. **Task 2 RED: failing latency/settings tests + zero-behavior skeletons** - `073f7cb` (test)
3. **Task 2 GREEN: warmed p50/p95, cold start, hoisted pipeline, settings baseline** - `19aa889` (feat; REFACTOR skipped — no cleanup needed, so no third commit)
4. **Task 3: binary precision/recall, graded evaluate(), empty-fixture guard** - `f72935d` (feat)
5. **Rule 2 fix: malformed fixture JSON -> ClickException (T-16-02)** - `8e78a1c` (fix)

## Files Created/Modified

- `src/sif/search/benchmark.py` - graded metrics, constants, dataclasses, corpus-root/key rules, schema parsing, `report()`, `measure_query_times`, `percentile`, binary precision/recall, empty-queries guard
- `src/sif/cli/commands/bench.py` - helper-extracted bench_cmd consuming `report()`; settings-resolved baseline; warmed clock; table/JSON rendering with per-category rows; noqa shrunk from C901/PLR0913/PLR0915 to PLR0913 only
- `tests/unit/search/test_benchmark_metrics.py` - new: 44 tests covering metrics, roots, schemas, report, latency clock, binary caps, empty guard
- `tests/unit/cli/test_bench.py` - graded JSON test, settings-baseline/pipeline-once, latency keys, empty/malformed fixtures, invalid settings; `_settings_mock` helper; narrow-width stub moved to `report().to_dict()`
- `tests/unit/cli/test_database_lifecycle.py` - bench stub switched to a real `BenchReport` (assertions unchanged; Database-ownership subject intact)
- `tests/unit/search/test_benchmark.py` - **byte-unmodified** (preservation contract honored)

## Decisions Made

- `report(clock=...)` cold start is captured by wrapping the first call inside the warm-up pass (`_cold_start_wrapper`), so `measure_query_times` keeps its plan-specified signature and the cold sample provably never joins the timed set
- The settings-baseline test pins NON-default values (`rrf_k=80, bm25_weight=2.0, vector_weight=0.5`) instead of the plan's literal 60/1.0/1.0, which equal `SearchOptions` defaults — the literal values would pass for the wrong reason (research Pitfall 10); the `_settings_mock()` helper itself defaults to 60/1.0/1.0 as specified
- `relevance_key` is validated to be `docid`/`path`, and path-mode fixtures without a resolvable root raise a `ValueError` naming `corpus_root` — silent all-zeros scoring is the failure these guards prevent (T-16-03)
- TDD skeletons: Task 2's RED commit carries zero-behavior `percentile`/`measure_query_times` stubs so the suite collects (assertion failures, not import errors — Phase 11 house pattern); `report(clock=...)` fails on the missing kwarg in RED

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `clock` parameter deferred from Task 1 to Task 2**
- **Found during:** Task 1
- **Issue:** The plan specifies `report(..., clock=None)` in Task 1, but Task 1 cannot use it (measurement is Task 2's TDD behavior), and ruff ARG002 rejects the unused argument (no-noqa culture)
- **Fix:** Task 1 ships `report(search_fn, k, k_values)`; Task 2's GREEN adds `clock` with its wiring. End state matches the plan exactly
- **Files modified:** src/sif/search/benchmark.py
- **Verification:** ruff clean at every commit; final signature carries clock
- **Committed in:** 092ba97 / 19aa889

**2. [Rule 3 - Blocking] Patch-target moves pulled forward from Task 3 into Task 1**
- **Found during:** Task 1
- **Issue:** The plan places the `evaluate`->`report` stub migration of `test_bench_json_parses_at_narrow_width` and `test_bench_closes_database` in Task 3, but bench consumes `report()` as of Task 1 — those tests fail immediately without the move, and the plan's own verification (four-file pytest, full-suite gate) must be green per task
- **Fix:** Both stub moves (including the real `BenchReport` per the plan's Task 3 target state) landed in Task 1
- **Files modified:** tests/unit/cli/test_bench.py, tests/unit/cli/test_database_lifecycle.py
- **Verification:** 60 tests green at Task 1 commit; assertions unchanged
- **Committed in:** 092ba97

**3. [Rule 2 - Missing Critical] Malformed fixture JSON now surfaces as ClickException (T-16-02)**
- **Found during:** plan-level verification (threat-model sweep)
- **Issue:** The threat register's T-16-02 mitigation states `json.load` runs inside a try so malformed JSON exits non-zero via ClickException; the fixture load (pre-existing structure) sat outside every try
- **Fix:** Wrapped the fixture load in `try/except (OSError, ValueError)` -> `click.ClickException(f"Benchmark failed: {e}")` with a regression test
- **Files modified:** src/sif/cli/commands/bench.py, tests/unit/cli/test_bench.py
- **Verification:** `test_bench_malformed_fixture_exits_nonzero` passes; full suite green
- **Committed in:** 8e78a1c

---

**Total deviations:** 3 auto-fixed (1 missing critical, 2 blocking)
**Impact on plan:** All fixes preserve the plan's end-state contracts (no scope creep); two are sequencing adjustments the plan's own green-suite gates require, one closes a promised threat-model mitigation.

## Issues Encountered

None beyond the deviations above. TDD RED failed for exactly the intended reasons (stub values, per-query pipeline construction `2 == 1`, missing `clock` kwarg, `cold_start_ms` None); GREEN passed first try.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Wave 2 consumers (16-03 fixture pack, 16-04 sweep, 16-05 snapshot) can build on: `BenchReport.to_dict()` flat-key contract, `resolve_corpus_root`/`result_key` path-keyed relevance, CATEGORIES order, `measure_query_times`, the `_measure_state`/`_build_options` seams, and `_settings_mock` (rerank fields extend it in 16-02)
- The graded fixture schema is implemented but no committed pack exists until Plan 03 (wave 2), as planned

## Verification Results

- `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/search/test_benchmark_metrics.py tests/unit/search/test_benchmark.py tests/unit/cli/test_bench.py tests/unit/cli/test_database_lifecycle.py -x --no-cov` — 76 passed
- `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` (full suite) — 1383 passed, 1 skipped, coverage 94.95% (fail_under=90 gate green)
- `ruff check src tests && ruff format --check src tests` — clean
- `ty check src/sif` — 0 diagnostics

## Self-Check: PASSED

All six key files exist on disk; all five task commits (092ba97, 073f7cb, 19aa889, f72935d, 8e78a1c) are ancestors of HEAD; commit count measured from the plan ledger (base 3353250) is 5, matching the Task Commits section.
