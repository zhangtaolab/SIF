---
phase: 16-bench-expansion-reranker-tuning
verified: 2026-11-12T07:49:17Z
status: passed
score: 20/20 must-haves verified
covered_files:
  - .planning/phases/16-bench-expansion-reranker-tuning/16-01-PLAN.md
  - .planning/phases/16-bench-expansion-reranker-tuning/16-01-SUMMARY.md
  - .planning/phases/16-bench-expansion-reranker-tuning/16-02-PLAN.md
  - .planning/phases/16-bench-expansion-reranker-tuning/16-02-SUMMARY.md
  - .planning/phases/16-bench-expansion-reranker-tuning/16-03-PLAN.md
  - .planning/phases/16-bench-expansion-reranker-tuning/16-03-SUMMARY.md
  - .planning/phases/16-bench-expansion-reranker-tuning/16-04-PLAN.md
  - .planning/phases/16-bench-expansion-reranker-tuning/16-04-SUMMARY.md
  - .planning/phases/16-bench-expansion-reranker-tuning/16-05-PLAN.md
  - .planning/phases/16-bench-expansion-reranker-tuning/16-05-SUMMARY.md
  - .planning/phases/16-bench-expansion-reranker-tuning/16-06-PLAN.md
  - .planning/phases/16-bench-expansion-reranker-tuning/16-06-SUMMARY.md
  - .planning/phases/16-bench-expansion-reranker-tuning/16-UAT.md
  - docs/api-reference.md
  - docs/benchmarking.md
  - docs/cli-reference.md
  - docs/configuration.md
  - docs/search-algorithms.md
  - scripts/generate_bench_fixture.py
  - scripts/generate_config_ref.py
  - src/sif/cli/commands/bench.py
  - src/sif/cli/commands/search.py
  - src/sif/cli/error_handling.py
  - src/sif/config/settings.py
  - src/sif/database/repositories.py
  - src/sif/embedding/manager.py
  - src/sif/search/benchmark.py
  - src/sif/search/hybrid.py
  - src/sif/search/rerank.py
  - tests/fixtures/bench/README.md
  - tests/fixtures/bench/corpus/keyword/kw-000.md
  - tests/fixtures/bench/corpus/keyword/kw-001.md
  - tests/fixtures/bench/corpus/keyword/kw-002.md
  - tests/fixtures/bench/corpus/keyword/kw-003.md
  - tests/fixtures/bench/corpus/keyword/kw-004.md
  - tests/fixtures/bench/corpus/keyword/kw-005.md
  - tests/fixtures/bench/corpus/keyword/kw-006.md
  - tests/fixtures/bench/corpus/keyword/kw-007.md
  - tests/fixtures/bench/corpus/keyword/kw-008.md
  - tests/fixtures/bench/corpus/keyword/kw-009.md
  - tests/fixtures/bench/corpus/keyword/kw-010.md
  - tests/fixtures/bench/corpus/keyword/kw-011.md
  - tests/fixtures/bench/corpus/keyword/kw-012.md
  - tests/fixtures/bench/corpus/keyword/kw-013.md
  - tests/fixtures/bench/corpus/keyword/kw-014.md
  - tests/fixtures/bench/corpus/keyword/kw-015.md
  - tests/fixtures/bench/corpus/keyword/kw-016.md
  - tests/fixtures/bench/corpus/keyword/kw-017.md
  - tests/fixtures/bench/corpus/keyword/kw-018.md
  - tests/fixtures/bench/corpus/keyword/kw-019.md
  - tests/fixtures/bench/corpus/keyword/kw-020.md
  - tests/fixtures/bench/corpus/keyword/kw-021.md
  - tests/fixtures/bench/corpus/keyword/kw-022.md
  - tests/fixtures/bench/corpus/keyword/kw-023.md
  - tests/fixtures/bench/corpus/keyword/kw-024.md
  - tests/fixtures/bench/corpus/keyword/kw-025.md
  - tests/fixtures/bench/corpus/keyword/kw-026.md
  - tests/fixtures/bench/corpus/keyword/kw-027.md
  - tests/fixtures/bench/corpus/keyword/kw-028.md
  - tests/fixtures/bench/corpus/keyword/kw-029.md
  - tests/fixtures/bench/corpus/keyword/kw-030.md
  - tests/fixtures/bench/corpus/keyword/kw-031.md
  - tests/fixtures/bench/corpus/keyword/kw-032.md
  - tests/fixtures/bench/corpus/keyword/kw-033.md
  - tests/fixtures/bench/corpus/keyword/kw-034.md
  - tests/fixtures/bench/corpus/keyword/kw-035.md
  - tests/fixtures/bench/corpus/keyword/kw-036.md
  - tests/fixtures/bench/corpus/keyword/kw-037.md
  - tests/fixtures/bench/corpus/keyword/kw-038.md
  - tests/fixtures/bench/corpus/keyword/kw-039.md
  - tests/fixtures/bench/corpus/multilingual/ml-000.md
  - tests/fixtures/bench/corpus/multilingual/ml-001.md
  - tests/fixtures/bench/corpus/multilingual/ml-002.md
  - tests/fixtures/bench/corpus/multilingual/ml-003.md
  - tests/fixtures/bench/corpus/multilingual/ml-004.md
  - tests/fixtures/bench/corpus/multilingual/ml-005.md
  - tests/fixtures/bench/corpus/multilingual/ml-006.md
  - tests/fixtures/bench/corpus/multilingual/ml-007.md
  - tests/fixtures/bench/corpus/multilingual/ml-008.md
  - tests/fixtures/bench/corpus/multilingual/ml-009.md
  - tests/fixtures/bench/corpus/multilingual/ml-010.md
  - tests/fixtures/bench/corpus/multilingual/ml-011.md
  - tests/fixtures/bench/corpus/multilingual/ml-012.md
  - tests/fixtures/bench/corpus/multilingual/ml-013.md
  - tests/fixtures/bench/corpus/multilingual/ml-014.md
  - tests/fixtures/bench/corpus/multilingual/ml-015.md
  - tests/fixtures/bench/corpus/multilingual/ml-016.md
  - tests/fixtures/bench/corpus/multilingual/ml-017.md
  - tests/fixtures/bench/corpus/multilingual/ml-018.md
  - tests/fixtures/bench/corpus/multilingual/ml-019.md
  - tests/fixtures/bench/corpus/multilingual/ml-020.md
  - tests/fixtures/bench/corpus/multilingual/ml-021.md
  - tests/fixtures/bench/corpus/multilingual/ml-022.md
  - tests/fixtures/bench/corpus/multilingual/ml-023.md
  - tests/fixtures/bench/corpus/multilingual/ml-024.md
  - tests/fixtures/bench/corpus/multilingual/ml-025.md
  - tests/fixtures/bench/corpus/multilingual/ml-026.md
  - tests/fixtures/bench/corpus/multilingual/ml-027.md
  - tests/fixtures/bench/corpus/multilingual/ml-028.md
  - tests/fixtures/bench/corpus/multilingual/ml-029.md
  - tests/fixtures/bench/corpus/multilingual/ml-030.md
  - tests/fixtures/bench/corpus/multilingual/ml-031.md
  - tests/fixtures/bench/corpus/multilingual/ml-032.md
  - tests/fixtures/bench/corpus/multilingual/ml-033.md
  - tests/fixtures/bench/corpus/multilingual/ml-034.md
  - tests/fixtures/bench/corpus/multilingual/ml-035.md
  - tests/fixtures/bench/corpus/rival/riv-000-a.md
  - tests/fixtures/bench/corpus/rival/riv-000-b.md
  - tests/fixtures/bench/corpus/rival/riv-001-a.md
  - tests/fixtures/bench/corpus/rival/riv-001-b.md
  - tests/fixtures/bench/corpus/rival/riv-002-a.md
  - tests/fixtures/bench/corpus/rival/riv-002-b.md
  - tests/fixtures/bench/corpus/rival/riv-003-a.md
  - tests/fixtures/bench/corpus/rival/riv-003-b.md
  - tests/fixtures/bench/corpus/rival/riv-004-a.md
  - tests/fixtures/bench/corpus/rival/riv-004-b.md
  - tests/fixtures/bench/corpus/rival/riv-005-a.md
  - tests/fixtures/bench/corpus/rival/riv-005-b.md
  - tests/fixtures/bench/corpus/rival/riv-006-a.md
  - tests/fixtures/bench/corpus/rival/riv-006-b.md
  - tests/fixtures/bench/corpus/rival/riv-007-a.md
  - tests/fixtures/bench/corpus/rival/riv-007-b.md
  - tests/fixtures/bench/corpus/rival/riv-008-a.md
  - tests/fixtures/bench/corpus/rival/riv-008-b.md
  - tests/fixtures/bench/corpus/rival/riv-009-a.md
  - tests/fixtures/bench/corpus/rival/riv-009-b.md
  - tests/fixtures/bench/corpus/rival/riv-010-a.md
  - tests/fixtures/bench/corpus/rival/riv-010-b.md
  - tests/fixtures/bench/corpus/rival/riv-011-a.md
  - tests/fixtures/bench/corpus/rival/riv-011-b.md
  - tests/fixtures/bench/corpus/rival/riv-012-a.md
  - tests/fixtures/bench/corpus/rival/riv-012-b.md
  - tests/fixtures/bench/corpus/rival/riv-013-a.md
  - tests/fixtures/bench/corpus/rival/riv-013-b.md
  - tests/fixtures/bench/corpus/rival/riv-014-a.md
  - tests/fixtures/bench/corpus/rival/riv-014-b.md
  - tests/fixtures/bench/corpus/rival/riv-015-a.md
  - tests/fixtures/bench/corpus/rival/riv-015-b.md
  - tests/fixtures/bench/corpus/rival/riv-016-a.md
  - tests/fixtures/bench/corpus/rival/riv-016-b.md
  - tests/fixtures/bench/corpus/rival/riv-017-a.md
  - tests/fixtures/bench/corpus/rival/riv-017-b.md
  - tests/fixtures/bench/corpus/synonym/syn-000.md
  - tests/fixtures/bench/corpus/synonym/syn-001.md
  - tests/fixtures/bench/corpus/synonym/syn-002.md
  - tests/fixtures/bench/corpus/synonym/syn-003.md
  - tests/fixtures/bench/corpus/synonym/syn-004.md
  - tests/fixtures/bench/corpus/synonym/syn-005.md
  - tests/fixtures/bench/corpus/synonym/syn-006.md
  - tests/fixtures/bench/corpus/synonym/syn-007.md
  - tests/fixtures/bench/corpus/synonym/syn-008.md
  - tests/fixtures/bench/corpus/synonym/syn-009.md
  - tests/fixtures/bench/corpus/synonym/syn-010.md
  - tests/fixtures/bench/corpus/synonym/syn-011.md
  - tests/fixtures/bench/corpus/synonym/syn-012.md
  - tests/fixtures/bench/corpus/synonym/syn-013.md
  - tests/fixtures/bench/corpus/synonym/syn-014.md
  - tests/fixtures/bench/corpus/synonym/syn-015.md
  - tests/fixtures/bench/corpus/synonym/syn-016.md
  - tests/fixtures/bench/corpus/synonym/syn-017.md
  - tests/fixtures/bench/corpus/synonym/syn-018.md
  - tests/fixtures/bench/corpus/synonym/syn-019.md
  - tests/fixtures/bench/corpus/synonym/syn-020.md
  - tests/fixtures/bench/corpus/synonym/syn-021.md
  - tests/fixtures/bench/corpus/synonym/syn-022.md
  - tests/fixtures/bench/corpus/synonym/syn-023.md
  - tests/fixtures/bench/corpus/synonym/syn-024.md
  - tests/fixtures/bench/corpus/synonym/syn-025.md
  - tests/fixtures/bench/corpus/synonym/syn-026.md
  - tests/fixtures/bench/corpus/synonym/syn-027.md
  - tests/fixtures/bench/corpus/synonym/syn-028.md
  - tests/fixtures/bench/corpus/synonym/syn-029.md
  - tests/fixtures/bench/corpus/synonym/syn-030.md
  - tests/fixtures/bench/corpus/synonym/syn-031.md
  - tests/fixtures/bench/corpus/synonym/syn-032.md
  - tests/fixtures/bench/corpus/synonym/syn-033.md
  - tests/fixtures/bench/corpus/synonym/syn-034.md
  - tests/fixtures/bench/corpus/synonym/syn-035.md
  - tests/fixtures/bench/corpus/synonym/syn-036.md
  - tests/fixtures/bench/corpus/synonym/syn-037.md
  - tests/fixtures/bench/heldout_defaults.json
  - tests/fixtures/bench/queries.json
  - tests/support/__init__.py
  - tests/support/bench.py
  - tests/test_docs.py
  - tests/unit/cli/test_bench.py
  - tests/unit/cli/test_database_lifecycle.py
  - tests/unit/cli/test_error_conventions.py
  - tests/unit/cli/test_search.py
  - tests/unit/config/test_settings.py
  - tests/unit/database/test_repositories.py
  - tests/unit/embedding/test_manager.py
  - tests/unit/inference/test_reranker.py
  - tests/unit/search/test_bench_fixture.py
  - tests/unit/search/test_bench_snapshot.py
  - tests/unit/search/test_benchmark.py
  - tests/unit/search/test_benchmark_metrics.py
  - tests/unit/search/test_hybrid.py
  - tests/unit/search/test_rerank.py
  - tests/unit/search/test_sweep.py
covered_digest: "v4:sha256:5e48703547937295f2e18f81d7418660d5a062c813e3b6e89e500422f350fa85"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 20/20
  gaps_closed: []
  gaps_remaining: []
  regressions: []
decision_coverage:
  honored: 13
  total: 13
  not_honored: []
---

# Phase 16: Bench Expansion + Reranker Tuning Verification Report

**Phase Goal:** Search-quality tuning is quantified and honest — an expanded benchmark with metrics, sweep, and held-out validation justifies shipped defaults and tunes the reranker within interactive latency.
**Verified:** 2026-11-12T07:49:17Z at HEAD `b47f55f6c551aa61ddd124913f6fe9a2663da06a`
**Status:** passed
**Re-verification:** Yes — the prior passed report was stale because Phase 16.1 changed `bench.py`/`search.py` and WR-01 changed `repositories.py`. This pass re-derived the verdict from current source, fixture data, and live tests; no prior gap was carried forward.

## Goal Achievement

Must-have set reused from the prior verification: 5 ROADMAP success criteria, 10 edge truths, and 5 prohibitions. SUMMARY.md statements were used only to locate evidence, not as proof. All 20 items have current source and behavioral evidence.

### Post-Verification Change Review

| Change | Current Codebase Evidence | Result |
|--------|---------------------------|--------|
| Phase 16.1 database opener adoption | `bench.py:648` and `search.py:836` call `open_initialized_database(index_path, Database)`; `error_handling.py:44-66` still constructs the caller-supplied `Database`, calls `init_schema()`, and enters its context. The helper wraps only open/schema initialization, not benchmark measurement or rerank behavior. | No Phase 16 semantics changed; 38 bench CLI, 167 search CLI, 8 database-lifecycle, and 15 error-convention tests pass in their respective runs. |
| Embedding dimension/public model property | `bench.py:106-116,653` and `search.py:897-905,943` prefer model metadata and use `manager.model`; deterministic snapshot/sweep tests construct `ConceptEmbedder` directly and do not traverse this loader. | No held-out or sweep drift; 12 embedding-manager tests and all 13 snapshot tests pass. |
| Explicit fixture UTF-8 read | `bench.py:631` opens the fixture with `encoding="utf-8"` inside the existing `OSError`/`ValueError` to `ClickException` boundary. | Fixture and CLI tests pass; empty/malformed fixture behavior remains guarded. |
| WR-01 cache-expiry batching | `repositories.py:530-644` changes only `LLMCacheRepository.clear_expired`; there are no `clear_expired` references in bench, search CLI, benchmark, hybrid, or rerank modules. | Isolated from Phase 16; all 29 repository tests pass, including the 1000-row batch regression. |

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | [SC-1] `sif bench` reports nDCG@k, Hit@k, and p50/p95 latency for each measured configuration | VERIFIED | `benchmark.py:78-112` implements DCG/nDCG/Hit/percentile; `report()` at `benchmark.py:575-657` computes global/category metrics and warmed latency; `bench.py:261-300,403-475` carries them into every config/report. Live: 37 metric tests, 38 bench CLI tests, and 14 sweep tests pass. |
| 2 | [SC-2] Fixture contains at least 50 categorized queries split into tuning and held-out | VERIFIED | Direct JSON parse: 56 queries, exactly 14 each for keyword/synonym/multilingual/rival; 36 tuning and 20 held-out, with 9/5 per category. All grades are integers 0-3, every query has grade >=2 relevance, and every relevance key resolves safely beneath `corpus/`. Generator check: 151 files match. |
| 3 | [SC-3] Fixed sweep grids weights and k; differences within noise (<0.01) are not declared winners | VERIFIED | `GRID_RRF_K`/`GRID_WEIGHTS` at `benchmark.py:31-33` yield the fixed 45-config grid through `iter_grid()`; `rank_sweep()` at `benchmark.py:361-391` applies `round(best - ndcg, 6) < 0.01` and sets `winner_declared` only for a one-config tie group. All sweep and bench CLI tests pass. |
| 4 | [SC-4] Shipped defaults are justified and locked by held-out evidence | VERIFIED | `heldout_defaults.json` records defaults 60/1.0/1.0, held-out nDCG@10 `0.8120158986791898` over 20 queries, candidate delta `0.00662541159807295`, and verdict `unchanged`. `test_metrics_reproduce_and_defaults_lock_in_one_test` recomputes global and per-category values from `Settings(_env_file=None)`; all 13 snapshot tests pass at HEAD. |
| 5 | [SC-5] Reranker honors candidate cap and relative threshold; off path remains cheap | VERIFIED | `rerank.py:40-48` stable-sorts and filters raw normalized scores with `>= top1 * alpha` before `top_k`; `hybrid.py:233-261` over-fetches to `max(limit + offset, candidate_limit)` then slices to the cap; `search.py:913-930` gates factory construction on flag/setting. Settings validate 5..50 and (0,1]. Live: 15 rerank, 36 hybrid, 45 inference-reranker, 38 bench, and the full search/settings files pass. |
| 6 | [Edge] Cap and threshold boundary validation | VERIFIED | `settings.py:158-182` declares Pydantic bounds; `resolve_candidate_limit` at `settings.py:399-415` clamps every resolved value to 5..50 and rejects non-int injection by falling back to 20. All 34 settings tests pass. |
| 7 | [Edge] Deterministic equal-score rerank and sweep ordering | VERIFIED | Python stable sort in `rerank.py:40-48`; sweep key at `benchmark.py:375-383` is nDCG descending followed by declared grid dimensions. Determinism assertions in rerank, hybrid, sweep, and snapshot suites pass. |
| 8 | [Edge] Tuning/held-out isolation | VERIFIED | `_tuning_evaluator` at `bench.py:237-258` filters to `split == "tuning"` before constructing the evaluator/search path. `test_bench_sweep_never_searches_heldout_queries` is active and passed within the 38-test bench CLI run. |
| 9 | [Edge] Empty fixtures fail instead of producing zero-valued metrics | VERIFIED | `benchmark.py:453-459` raises `ValueError` on an empty query list; `bench.py:666-686` maps measurement/fixture failures to `ClickException`. Legacy metric and CLI empty-fixture tests pass. |
| 10 | [Edge] Fixed category order in every report/config | VERIFIED | `CATEGORIES` is the fixed tuple at `benchmark.py:21`; `BenchReport.to_dict()` and `ConfigResult.to_dict()` iterate that tuple. Fixture, metric, sweep, and narrow-width JSON tests pass. |
| 11 | [Edge] Held-out delta >=0.01 is inclusive with rounded arithmetic | VERIFIED | `warrants_default_change` at `benchmark.py:394-407` uses `round(candidate - baseline, 6) >= delta`; exact-0.01, representation-noise, 0.0099, zero, and negative cases pass in `TestWarrantsDefaultChange`. |
| 12 | [Edge] No evidence means no default change | VERIFIED | `snapshot_verdict` in `test_bench_snapshot.py:111-124` returns `unchanged-no-evidence` when held-out or candidate evidence is absent; both missing-evidence tests and the committed-verdict consistency test pass. |
| 13 | [Edge] Sweep output ordering is deterministic | VERIFIED | `TestIterGrid`, `TestRankSweep`, and `TestSweepWinnerEvidence::test_winner_ranking_is_deterministic` pass; the committed ranking contains all 45 unique configurations. |
| 14 | [Edge] k=10 and empty-result zero scores | VERIFIED | `DEFAULT_K = 10`; `ndcg_at_k` returns 0.0 for zero ideal DCG and `hit_at_k` returns 0.0 for no positive retrieved grade. Hand-value and edge tests in `test_benchmark_metrics.py` pass. |
| 15 | [Edge] Strict <0.01 tie boundary | VERIFIED | `TestRankSweepTieBoundary` proves exactly 0.01 is signal, 0.0099 is noise, and the raw `0.29 - 0.28 = 0.009999999999999953` case is not misclassified. All 14 sweep tests pass. |
| 16 | [Prohibition] No real-KB data committed; synthetic fixture only | VERIFIED (must-NOT did not happen) | `python -I scripts/generate_bench_fixture.py --check` returned `OK ... matches generator output (151 files)`, so the complete pack is byte-identical to seeded generator output. |
| 17 | [Prohibition] No unbounded rerank fan-out | VERIFIED (must-NOT did not happen) | Shared clamp 5..50 plus pipeline slice is present on both CLI paths; `-C 200` resolution and real-index candidate-count spies pass in search, bench, and hybrid suites. |
| 18 | [Prohibition] No tuning-only default changes | VERIFIED (must-NOT did not happen) | Settings defaults remain 60/1.0/1.0 and the measured held-out candidate delta is only +0.0066; snapshot verdict remains `unchanged`, reproduced by the live lock test. |
| 19 | [Prohibition] No held-out leakage into sweep ranking | VERIFIED (must-NOT did not happen) | Tuning-only fixture filtering is structural and the held-out-search spy test passes at HEAD. |
| 20 | [Prohibition] No reranker construction on the off path | VERIFIED (must-NOT did not happen) | `search.py:913-920` checks opt-in before `create_reranker`; `bench.py:184-208` returns `None` before the factory unless `--rerank` is set. Off-path and no-construction tests pass. |

**Score:** 20/20 truths verified (0 present-but-behavior-unverified).

### Advisory (New Scope, Unevidenced)

Re-verification evidence gating was applied. No new-scope blockers or unevidenced advisory findings were raised. The only changes since the prior report were directly inspected and exercised by named test files above.

| # | Finding | Category | Why Advisory |
|---|---------|----------|--------------|
| 1 | None | - | - |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/sif/search/benchmark.py` | Metrics, category reports, fixed grid, tie ranking, held-out rule | VERIFIED | Substantive implementations at lines 21-657; consumed by CLI and deterministic snapshot. |
| `src/sif/cli/commands/bench.py` | Report/sweep/rerank states, tuning guard, clamp, cached embedder | VERIFIED | Full orchestration present; Phase 16.1 opener/model-property changes preserve behavior; 38 tests pass. |
| `src/sif/config/settings.py` | Opt-in rerank, validated cap/threshold, shared resolver | VERIFIED | Fields and resolver present; 34 tests pass. |
| `src/sif/cli/commands/search.py` | Rerank opt-in and bounded candidate options | VERIFIED | Gate and resolver wiring intact after opener/model changes; full CLI test file passes. |
| `src/sif/search/rerank.py` | Relative threshold on all backends | VERIFIED | Shared post-normalization filter plus factory forwarding present; rerank/reranker tests pass. |
| `src/sif/search/hybrid.py` | Binding over-fetch and candidate slice | VERIFIED | `fetch_options` reaches hybrid search/fusion and `results[:candidate_limit]` precedes rerank; 36 tests pass. |
| `src/sif/cli/error_handling.py` | Equivalent initialized database opener | VERIFIED | Caller-supplied `Database` construction + `init_schema()` + context management; 15 error-convention tests pass. |
| `src/sif/database/repositories.py` | WR-01 cache fix isolated from Phase 16 | VERIFIED | Only LLM cache expiry deletion changed; 29 repository tests pass. |
| `tests/fixtures/bench/` | Synthetic categorized pack and held-out snapshot | VERIFIED | 150 corpus docs, 56 queries, snapshot; direct integrity parse and 151-file drift check pass. |
| `scripts/generate_bench_fixture.py` | Deterministic generator and pack-wide drift gate | VERIFIED | Probe exit 0; fixture contract suite passes. |
| `tests/support/bench.py` | Deterministic ConceptEmbedder and real-schema index builder | VERIFIED | Used by live fixture/snapshot/CLI tests at HEAD. |
| `docs/benchmarking.md` and related docs | Honest measurement/tuning documentation | VERIFIED | Documents 45-config tuning-only grid, rounded 0.01 rules, cap/alpha/opt-in, snapshot values and verdict; all 13 docs tests pass. |

The plans use legacy free-form strings for `must_haves.artifacts` and `key_links`; the structured `verify.artifacts`/`verify.key-links` verbs therefore returned zero machine-parseable entries. They were not treated as evidence. The tables above and below record the manual existence/substance/wiring checks instead.

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `bench_cmd` | `SearchEvaluator.report` | Fixture path -> corpus root -> measured search function | WIRED | Exact committed-pack CLI join test passes with non-zero nDCG/Hit. |
| `bench_cmd` | Metric helpers | `report()` / `_measure_config()` | WIRED | No metric formulas inline in CLI; pure helpers tested independently. |
| `_run_sweep` | Per-config `SearchOptions` | `dataclasses.replace` of rrf_k/BM25/vector weights | WIRED | 45-config grid and baseline reuse present; sweep tests pass. |
| `_tuning_evaluator` | Sweep ranking | Tuning-only filtered fixture | WIRED | Held-out spy test passes. |
| `query_cmd` | `create_reranker` | `--rerank` OR `SIF_RERANK_ENABLED` gate | WIRED | Gate precedes factory; off-path tests pass. |
| `query_cmd`/`bench_cmd` | `SearchOptions.candidate_limit` | Shared `resolve_candidate_limit` | WIRED | Both callers resolve through the same clamp. |
| `SearchPipeline.search` | Reranker | Over-fetch -> fusion -> cap slice -> `rerank(top_k=limit)` | WIRED | Real-index candidate-count and composition tests pass. |
| `heldout_defaults.json` | Settings defaults | Same-test recomputation and equality lock | WIRED | Snapshot reproduction/default-lock test passes. |
| Rerank scoring | Relative threshold | Stable descending sort -> `>= top1*alpha` -> top_k | WIRED | Exact-half and threshold-before-truncation tests pass. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `bench --json` | nDCG/Hit/p50/p95/categories | `SearchEvaluator.report` over measured `SearchPipeline` results | Yes | FLOWING |
| `bench --sweep --json` | 45 configs, tie group, baseline/deltas | `_run_sweep` over tuning-only measured reports | Yes | FLOWING |
| `heldout_defaults.json` | Defaults, held-out metrics, candidate, delta, verdict | Deterministic real SQLite/FTS/vector fixture index | Yes | FLOWING; recomputed by live test |
| Rerank output | Candidate list and retained scores | Hybrid over-fetch/fusion -> cap -> normalized rerank scores | Yes | FLOWING; real-index and scoring tests pass |
| Benchmarking docs | Deterministic evidence table | Committed snapshot and ranking | Yes | FLOWING; values match parsed snapshot |

### Behavioral Spot-Checks

All commands below were run by this verifier at HEAD `b47f55f` with `env -u FORCE_COLOR NO_COLOR=1` for pytest.

| Behavior | Command / Scope | Result | Status |
|----------|-----------------|--------|--------|
| Held-out lock, sweep, bench CLI, rerank scoring | `pytest tests/unit/search/test_bench_snapshot.py tests/unit/search/test_sweep.py tests/unit/cli/test_bench.py tests/unit/search/test_rerank.py --no-cov` | 80 passed in 4.36s | PASS |
| Metric correctness, legacy compatibility, fixture integrity, pipeline cap, factory forwarding | `pytest test_benchmark_metrics.py test_benchmark.py test_bench_fixture.py test_hybrid.py test_reranker.py --no-cov` (full unit paths) | 167 passed in 10.47s | PASS |
| Search CLI opt-in/clamp, settings bounds, DB lifecycle, docs | `pytest test_search.py test_settings.py test_database_lifecycle.py tests/test_docs.py --no-cov` (full unit paths) | 222 passed in 1.88s | PASS |
| Phase 16.1 opener/model property and WR-01 regression | `pytest test_error_conventions.py test_manager.py test_repositories.py --no-cov` (full unit paths) | 56 passed in 0.34s | PASS |
| Fixture shape and evidence values | Direct `json` parse of `queries.json` and `heldout_defaults.json` | 56/36/20; 14 per category; safe paths/grades; defaults and verdict as recorded | PASS |
| Current source quality | `ruff check` and `ruff format --check` on eight current source files | All checks passed; 8 files formatted | PASS |
| HEAD full-suite gate | Supplied by orchestrator for `b47f55f`; not re-run by this verifier | 1591 passed, 1 skipped, coverage 95.18%; ruff/format/ty clean | PASS (confirmed HEAD gate) |

Total live focused evidence: 525 tests passed across disjoint phase-linked files, with zero skips in these runs.

### Probe Execution

No `scripts/*/tests/probe-*.sh` files or plan-declared shell probes exist for this phase. The phase's actual structural probe is the deterministic fixture drift gate.

| Probe | Command | Result | Status |
|-------|---------|--------|--------|
| Synthetic fixture drift gate | `python -I scripts/generate_bench_fixture.py --check` | `OK: .../tests/fixtures/bench matches generator output (151 files)`, exit 0 | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| QUAL-05 | 16-02, 16-04, 16-06 | Reranker cap + relative threshold; interactive skip-rerank path | SATISFIED | Truths 5-7, 17, 20; source wiring and live CLI/rerank/hybrid tests. |
| EVAL-01 | 16-01, 16-05 | nDCG@k, Hit@k, p50/p95 benchmark output | SATISFIED | Truth 1; pure helpers, rendering, and CLI tests. |
| EVAL-02 | 16-01, 16-03, 16-05 | At least 50 categorized queries with tuning/held-out split | SATISFIED | Truth 2; direct 56-query parse, integrity tests, drift gate. |
| EVAL-03 | 16-04, 16-05 | Fixed weight/k sweep and honest 0.01 noise rule | SATISFIED | Truths 3, 8, 13, 15; grid/tie/split tests. |
| EVAL-04 | 16-05 | Defaults justified by held-out evidence, not tuning overfit | SATISFIED | Truths 4, 11, 12, 18; snapshot recomputation and defaults lock pass. |

No orphaned requirements: REQUIREMENTS.md maps exactly QUAL-05 and EVAL-01..04 to Phase 16, and every ID is claimed by at least one plan.

### Decision Coverage

`check.decision-coverage-verify`: 13/13 trackable CONTEXT.md decisions honored, 0 not honored (non-blocking gate).

### Test Quality Audit

| Test File(s) | Linked Req | Active | Disabled | Circular | Assertion Level | Verdict |
|--------------|------------|--------|----------|----------|-----------------|---------|
| `test_benchmark_metrics.py`, `test_benchmark.py` | EVAL-01/02 | Active | 0 | 0 | Hand-calculated values + behavior | OK |
| `test_bench_fixture.py`, `test_bench.py` | EVAL-01/02/03, QUAL-05 | Active | 0 | 0 | Real DB, JSON shape/value, spies | OK |
| `test_sweep.py` | EVAL-03 | Active | 0 | 0 | Exact boundary values + deterministic ordering | OK |
| `test_bench_snapshot.py` | EVAL-04 | Active | 0 | 0 | Recomputed values + default-lock mutation probes | OK |
| `test_search.py`, `test_settings.py`, `test_hybrid.py`, `test_rerank.py`, `test_reranker.py` | QUAL-05 | Active | 0 | 0 | Boundary values, real-index candidate counts, off-path proofs | OK |

The only disabled-test grep hits are conditional sqlite-vec runtime guards in `test_hybrid.py`; sqlite-vec is available here and all 36 tests ran, so no requirement is hidden by a skip. Snapshot values are a regression lock recomputed from the deterministic index, not the sole correctness oracle: metric correctness is independently pinned by hand-calculated metric tests. No insufficient assertions or disabled requirement proofs found.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | - | No TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER markers, placeholder implementations, or unwired stubs in phase source/test/script/docs files | - | - |

### Human Verification

N/A for this re-verification. The two planned manual-only items (real-model held-out corroboration and operator-hardware rerank latency) are already dispositioned `passed` in `16-UAT.md` (2/2, 0 pending). The current opener/model-property/cache changes introduce no new human-only acceptance criterion, and no truth is behavior-unverified.

### Gaps Summary

No gaps and no regressions. The Phase 16 goal remains achieved at HEAD `b47f55f`: the categorized fixture is intact and generator-reproducible; the fixed sweep remains tuning-only with the strict rounded 0.01 tie rule; the held-out snapshot still recomputes and locks shipped defaults; rerank opt-in, candidate bounding, and relative-threshold behavior remain wired and test-proven. Phase 16.1's opener/model-loading edits and WR-01's isolated cache-expiry batching did not alter those contracts.

---

_Verified: 2026-11-12T07:49:17Z_
_Verifier: Claude (gsd-verifier)_
