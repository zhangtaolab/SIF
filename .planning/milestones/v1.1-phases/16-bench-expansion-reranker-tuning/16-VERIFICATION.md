---
phase: 16-bench-expansion-reranker-tuning
verified: 2026-11-12T10:42:35Z
status: passed
score: 20/20 must-haves verified
covered_files:
  - .planning/WINDOWS.md
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
covered_digest: "v4:sha256:f18fb8d6e30ad4fe6a3b4ca84b54965bda9b8170af20e086d3eb3c31a940265e"
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
advisory: []
---

# Phase 16: Bench Expansion + Reranker Tuning Verification Report

**Phase Goal:** Search-quality tuning is quantified and honest — an expanded benchmark with metrics, sweep, and held-out validation justifies shipped defaults and tunes the reranker within interactive latency.
**Verified:** 2026-11-12T10:42:35Z at HEAD `353fe339ab361b91396670452df9007072698354`
**Status:** passed
**Re-verification:** Yes — final pass. The prior report was `passed` 20/20 with no gaps. Since its `verified` timestamp (`2026-11-12T10:37:54Z`) the only functional change is the `16-UAT.md` frontmatter correction (`status: passed` → canonical `status: complete`, updated timestamp) in commit `353fe33`; `git log --since=2026-11-12T10:37:54Z --oneline -- src tests scripts` is empty, so no implementation, fixture, or test input changed. This pass nonetheless re-derived every verdict from current source, fixture data, a live sweep recomputation, and the focused test suites rather than carrying the prior verdict forward.

## Goal Achievement

Must-haves are the five ROADMAP success criteria plus the plan-must-have edge cases and prohibitions consolidated to 20 items. SUMMARY.md statements were used only to locate evidence, never as proof.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | [SC-1] `sif bench` reports nDCG@k, Hit@k, and p50/p95 latency for each measured configuration | VERIFIED | `benchmark.py:78-112` (dcg/ndcg/hit/percentile with linear interpolation), `search` report at `benchmark.py:575-657` (global + per-category + warmed p50/p95 via `measure_query_times`), `ConfigResult` carries `p50_ms`/`p95_ms` per swept config (`benchmark.py:279-292`), and `bench.py:440-474` renders nDCG@10, Hit@10, p50, p95. 65 snapshot/sweep/bench-CLI tests pass. |
| 2 | [SC-2] Fixture contains ≥50 categorized queries split into tuning and held-out | VERIFIED | Direct `json` parse at HEAD: 56 queries; 14 each for keyword/synonym/multilingual/rival; 36 tuning + 20 held-out (9/5 per category); grades are integers 0-3; every query has max grade ≥2; all 56 relevance keys resolve under `corpus/`. Generator drift gate passes (151 files). |
| 3 | [SC-3] Fixed sweep grids weights and k; differences within noise (<0.01) are not declared winners | VERIFIED | `GRID_RRF_K`/`GRID_WEIGHTS` (`benchmark.py:31-33`) yield 45 unique configs via `iter_grid()`; `rank_sweep()` applies `round(best - ndcg, 6) < 0.01` and sets `winner_declared = len(tie_group) == 1`. Live recomputation at HEAD over the 36 tuning queries: 45 unique configs, winner `20/1.0/0.5` at nDCG@10 `0.8679671304`, tie group 30/45, `winner_declared=false`; an exact-0.01 pair is correctly declared a winner. 14 sweep tests pass. |
| 4 | [SC-4] Shipped defaults are justified and locked by held-out evidence | VERIFIED | `heldout_defaults.json` records defaults 60/1.0/1.0, held-out nDCG@10 `0.8120158986791898` over 20 queries, per-category `0.9735/0.2746/1.0000/1.0000`, candidate `20/1.0/0.5` at held-out `0.8186413`, delta `+0.0066254`, verdict `unchanged`. `Settings` defaults remain 60/1.0/1.0 (`settings.py:228-245`). `test_metrics_reproduce_and_defaults_lock_in_one_test` recomputes and asserts the lock in the same test; 13 snapshot tests pass. |
| 5 | [SC-5] Reranker honors candidate cap and relative threshold; off path remains cheap | VERIFIED | `rerank.py:24-48` stable-sorts, then filters `score >= top1 * alpha`, then truncates to `top_k`; `hybrid.py:233-262` over-fetches to `max(limit + offset, candidate_limit)` and slices `[: candidate_limit]` before rerank; `search.py:915-920` gates `create_reranker` behind flag/setting. `Settings` defaults cap 20 (5..50) and α 0.5 ((0,1]). Live: rerank/hybrid/reranker/settings/search suites pass. |
| 6 | [Edge] Cap and threshold boundary validation | VERIFIED | `settings.py:158-182` Pydantic bounds; `resolve_candidate_limit` (`settings.py:399-415`) clamps to 5..50 and falls back to 20 for non-int injection. `test_rerank_candidate_limit_accepts_boundaries`/`_rejects_out_of_range` and `test_rerank_relative_threshold_*` pass. |
| 7 | [Edge] Deterministic equal-score rerank and sweep ordering | VERIFIED | Stable Python sort in `rerank.py:40-48`; sweep key is nDCG descending then declared grid order (`benchmark.py:375-383`). `test_equal_scores_deterministic_across_runs`, `test_ranking_is_descending_with_grid_order_tiebreak`, and `test_winner_ranking_is_deterministic` pass. |
| 8 | [Edge] Tuning/held-out isolation | VERIFIED | `_tuning_evaluator` (`bench.py:237-258`) filters to `split == "tuning"` before constructing the evaluator, raising on no tuning queries. `test_bench_sweep_never_searches_heldout_queries` passes (sentinel never reaches the searcher). |
| 9 | [Edge] Empty fixtures fail instead of producing zero-valued metrics | VERIFIED | `benchmark.py:456-459` raises `ValueError` on missing/empty queries; `bench.py:683-686` maps measurement failures to `ClickException`; malformed JSON maps to `ClickException` (`bench.py:630-634`). `test_validate_fixture_missing_queries`, `test_empty_queries_list_rejected`, `test_bench_empty_queries_exits_nonzero`, and `test_bench_malformed_fixture_exits_nonzero` pass. |
| 10 | [Edge] Fixed category order in every report/config | VERIFIED | `CATEGORIES` fixed tuple (`benchmark.py:21`); `BenchReport.to_dict()` and `ConfigResult.to_dict()` iterate it. `test_to_dict_serializes_categories_in_declared_order` and JSON narrow-width tests pass. |
| 11 | [Edge] Held-out delta ≥0.01 is inclusive with rounded arithmetic | VERIFIED | `warrants_default_change` uses `round(candidate - baseline, 6) >= delta` (`benchmark.py:394-407`). `TestWarrantsDefaultChange` covers exactly 0.01, representation noise (`0.29-0.28`), 0.0099, zero, and negative — all pass. |
| 12 | [Edge] No evidence means no default change | VERIFIED | `snapshot_verdict` (`test_bench_snapshot.py:111-124`) returns `unchanged-no-evidence` when held-out or candidate is absent; both missing-evidence tests and the committed-verdict consistency test pass. |
| 13 | [Edge] Sweep output ordering is deterministic | VERIFIED | `TestIterGrid`/`TestRankSweep`, `test_winner_ranking_is_deterministic`, and the live recomputation (45 unique configs) confirm stable ordering. |
| 14 | [Edge] k=10 and empty-result zero scores | VERIFIED | `DEFAULT_K = 10`; `ndcg_at_k` returns 0.0 for zero ideal DCG; `hit_at_k` returns 0.0 with no positive retrieved grade. Hand-value and edge tests in `test_benchmark_metrics.py` pass. |
| 15 | [Edge] Strict <0.01 tie boundary | VERIFIED | `TestRankSweepTieBoundary`: exactly 0.01 is signal, 0.0099 is noise, and the raw `0.29 - 0.28 = 0.009999999999999953` case is not misclassified. Live exact-0.01 check confirmed. |
| 16 | [Prohibition] No real-KB data committed; synthetic fixture only | VERIFIED (must-NOT did not happen) | `python -I scripts/generate_bench_fixture.py --check` returned `OK ... matches generator output (151 files)`, so the pack is byte-identical to seeded synthetic generator output. The real-model row measures that same synthetic corpus. |
| 17 | [Prohibition] No unbounded rerank fan-out | VERIFIED (must-NOT did not happen) | Shared clamp 5..50 in `resolve_candidate_limit` + pipeline slice. `test_candidate_limit_200_clamps_to_50`, `test_resolve_candidate_limit_clamps_explicit_into_bounds`, and `test_over_cap_never_parses_candidates` pass. |
| 18 | [Prohibition] No tuning-only default changes | VERIFIED (must-NOT did not happen) | `Settings` defaults remain 60/1.0/1.0; measured held-out candidate delta is +0.0066 < 0.01; snapshot verdict remains `unchanged`, reproduced by the live lock test. |
| 19 | [Prohibition] No held-out leakage into sweep ranking | VERIFIED (must-NOT did not happen) | Tuning-only fixture filtering is structural (`bench.py:249-258`) and `test_bench_sweep_never_searches_heldout_queries` passes with a sentinel. |
| 20 | [Prohibition] No reranker construction on the off path | VERIFIED (must-NOT did not happen) | `search.py:915-920` checks opt-in before `create_reranker`; `bench.py:184-203` returns `None` before the factory unless `--rerank`. `test_off_by_default_constructs_no_reranker`, `test_bench_off_only_json_states_additive_no_reranker`, and the off-path snapshot test pass. |

**Score:** 20/20 truths verified (0 present-but-behavior-unverified).

### Post-Verification Change Review

The only change since the prior pass is the UAT frontmatter correction; no source, fixture, script, or test file changed.

| Change | Current Codebase Evidence | Result |
|--------|---------------------------|--------|
| `16-UAT.md` frontmatter `status: passed` → `complete` (commit `353fe33`) | UAT `status: complete`; tests section still shows both scenarios `result: passed`; summary 2 passed / 0 pending / 0 blocked; item 1 carries the recorded 2026-11-12 real-model measurement, item 2 the operator-hardware latency pass. | Consistent with the canonical UAT status vocabulary. |
| `docs/benchmarking.md` deterministic evidence table | Held-out 0.8120; per-category 0.9735/0.2746/1.0000/1.0000; tuning winner 20/1.0/0.5 at 0.8680 with a 30/45 tie group and no winner; held-out candidate 0.8186, delta +0.0066, verdict unchanged. Live recomputation reproduced the winner and 30/45 tie group; the snapshot reproduces 0.8120 and the category values. | Consistent; snapshot remains the CI gate. |
| `docs/benchmarking.md` manual real-model row | Records Qwen/Qwen3-Embedding-0.6B (modelscope, dim 1024), macOS arm64 single-thread CPU, 2026-11-12, held-out nDCG@10 0.9233 / Hit@10 1.0, p50/p95 94.3/117.6 ms, explicitly labeled "a separate manual step, not a CI gate". Model identity matches `settings.py` defaults. | CORROBORATION — not consumed by any test; no code contradicts it. This verifier cannot independently re-run the real model, so it is recorded as manual evidence, not a gate. |
| `.planning/WINDOWS.md` id 10 | Row is `fixed` with `resolved_at 2026-11-12T10:33:55.806Z`; frontmatter `open_count: 6`, `fixed_count: 4`. | Consistent; the Broken Window was closed only after the measurement was recorded. |

### Advisory (New Scope, Unevidenced)

Re-verification evidence gating was applied. The only post-pass change is a planning-document status correction with no implementation input; it was inspected directly. No new-scope blocker or unevidenced advisory finding was raised.

| # | Finding | Category | Why Advisory |
|---|---------|----------|--------------|
| 1 | None | - | - |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/sif/search/benchmark.py` | Metrics, category reports, fixed grid, tie ranking, held-out rule | VERIFIED | 657 lines of substantive implementation; consumed by the CLI and the deterministic snapshot. |
| `src/sif/cli/commands/bench.py` | Report/sweep/rerank states, tuning guard, clamp, cached embedder | VERIFIED | 687 lines; orchestration and rendering present; 38 bench CLI tests pass. |
| `src/sif/config/settings.py` | Opt-in rerank, validated cap/threshold, shared resolver | VERIFIED | Fields, bounds, and `resolve_candidate_limit` present. |
| `src/sif/cli/commands/search.py` | Rerank opt-in and bounded candidate options | VERIFIED | Gate and shared resolver wired; search CLI tests pass. |
| `src/sif/search/rerank.py` | Relative threshold on all backends | VERIFIED | Shared post-sort filter and factory forwarding present. |
| `src/sif/search/hybrid.py` | Binding over-fetch and candidate slice | VERIFIED | `fetch_options` reaches search/fusion and `results[: candidate_limit]` precedes rerank. |
| `src/sif/cli/error_handling.py` | Equivalent initialized database opener | VERIFIED | Caller-supplied `Database` construction + `init_schema()`; error-convention tests pass. |
| `src/sif/database/repositories.py` | WR-01 cache fix isolated from Phase 16 | VERIFIED | Phase-unrelated cache-expiry change; repository tests pass. |
| `tests/fixtures/bench/` | Synthetic categorized pack and held-out snapshot | VERIFIED | 150 corpus docs + 56 queries + snapshot; 151-file drift check passes. |
| `scripts/generate_bench_fixture.py` | Deterministic generator and pack-wide drift gate | VERIFIED | Probe exit 0. |
| `tests/support/bench.py` | Deterministic ConceptEmbedder and real-schema index builder | VERIFIED | Used by the live snapshot/fixture/CLI tests. |
| `docs/benchmarking.md` and related docs | Honest measurement/tuning documentation | VERIFIED | Documents the grid, 0.01 rule, held-out rule, cap/alpha/opt-in, deterministic values/verdict, and the manual real-model corroboration row; `tests/test_docs.py` passes with `docs/benchmarking.md` in `DOCS_FILES`. |

The plans use legacy free-form strings for `must_haves.artifacts` and `key_links`, so the structured `verify.artifacts`/`verify.key-links` verbs return no machine-parseable entries. Those verbs were not treated as evidence; the manual level-1/2/3 checks above and below are the evidence.

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `bench_cmd` | `SearchEvaluator.report` | Fixture path -> declared `corpus_root` -> measured search function | WIRED | `test_cli_bench_committed_pack_nonzero_ndcg` runs the exact committed pack and asserts non-zero nDCG/Hit. |
| `bench_cmd` | Metric helpers | `report()` / `_measure_config()` | WIRED | No metric formula inline in the CLI; helpers tested independently. |
| `_run_sweep` | Per-config `SearchOptions` | `dataclasses.replace` of rrf_k/BM25/vector weights | WIRED | 45-config grid plus settings baseline reuse; sweep tests pass. |
| `_tuning_evaluator` | Sweep ranking | Tuning-only filtered fixture | WIRED | Held-out sentinel spy test passes. |
| `query_cmd` | `create_reranker` | `--rerank` OR `SIF_RERANK_ENABLED` gate | WIRED | Gate precedes factory; off-path tests pass. |
| `query_cmd`/`bench_cmd` | `SearchOptions.candidate_limit` | Shared `resolve_candidate_limit` clamp | WIRED | Both callers resolve through the same 5..50 clamp. |
| `SearchPipeline.search` | Reranker | Over-fetch -> fusion -> cap slice -> `rerank(top_k=limit)` | WIRED | Real-index candidate-count and composition tests pass. |
| `heldout_defaults.json` | Settings defaults | Same-test recomputation and equality lock | WIRED | Snapshot reproduction/default-lock test passes. |
| Rerank scoring | Relative threshold | Stable descending sort -> `>= top1*alpha` -> top_k | WIRED | Exact-half, threshold-before-truncation, and off-path snapshot tests pass. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `bench --json` | nDCG/Hit/p50/p95/categories | `SearchEvaluator.report` over measured `SearchPipeline` results | Yes | FLOWING |
| `bench --sweep --json` | 45 configs, tie group, baseline/deltas | `_run_sweep` over tuning-only measured reports | Yes | FLOWING |
| `heldout_defaults.json` | Defaults, held-out metrics, candidate, delta, verdict | Deterministic real SQLite/FTS/vector fixture index | Yes | FLOWING; recomputed by the live lock test |
| Rerank output | Candidate list and retained scores | Hybrid over-fetch/fusion -> cap -> normalized rerank scores | Yes | FLOWING; real-index and scoring tests pass |
| Benchmarking docs (deterministic table) | Deterministic evidence values | Committed snapshot and live sweep ranking | Yes | FLOWING; values match a fresh live recomputation |
| Benchmarking docs (real-model row) | Manual corroboration values | External real-model run (manual, uncommitted) | Manual only | CORROBORATION — correctly not wired into CI; the deterministic snapshot remains the gate |

### Behavioral Spot-Checks

All commands below were run by this verifier at HEAD `353fe33` with `env -u FORCE_COLOR NO_COLOR=1`.

| Behavior | Command / Scope | Result | Status |
|----------|-----------------|--------|--------|
| Held-out lock, sweep, bench CLI | `pytest tests/unit/search/test_bench_snapshot.py tests/unit/search/test_sweep.py tests/unit/cli/test_bench.py --no-cov` | 65 passed in 4.11s | PASS |
| Docs gate, metric correctness, fixture integrity, rerank scoring, pipeline cap, factory forwarding, settings bounds, search CLI opt-in | `pytest tests/test_docs.py tests/unit/search/test_benchmark.py tests/unit/search/test_benchmark_metrics.py tests/unit/search/test_bench_fixture.py tests/unit/search/test_rerank.py tests/unit/search/test_hybrid.py tests/unit/inference/test_reranker.py tests/unit/config/test_settings.py tests/unit/cli/test_search.py --no-cov` | 396 passed in 21.56s | PASS |
| Docs deterministic sweep figures | Live `iter_grid` + `SearchEvaluator` + `rank_sweep` over the 36 tuning queries on the deterministic index | 45 unique configs; best `20/1.0/0.5`, nDCG@10 `0.867967130407773`; tie group 30; `winner_declared=False`; exact-0.01 pair declared a winner | PASS |
| Fixture shape and evidence values | Direct `json` parse of `queries.json` and `heldout_defaults.json` | 56/36/20; 14 per category; 9/5 split per category; grades 0-3; every max grade ≥2; all relevance keys resolve; defaults/verdict as recorded | PASS |
| HEAD full-suite gate | Supplied by orchestrator for HEAD: 1591 passed, 1 skipped @ 95.18% | PASS (confirmed; the only commits since are planning/documentation and cannot affect it, and all phase-linked tests re-ran green) | PASS |

Total live focused evidence this pass: 461 tests passed across the phase-linked files, with zero skips in these runs.

### Probe Execution

No `scripts/*/tests/probe-*.sh` files or plan-declared shell probes exist for this phase. The phase's structural probe is the deterministic fixture drift gate.

| Probe | Command | Result | Status |
|-------|---------|--------|--------|
| Synthetic fixture drift gate | `python -I scripts/generate_bench_fixture.py --check` | `OK: .../tests/fixtures/bench matches generator output (151 files)`, exit 0 | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| QUAL-05 | 16-02, 16-04, 16-06 | Reranker cap + relative threshold; interactive skip-rerank path | SATISFIED | Truths 5-7, 17, 20; source wiring and live CLI/rerank/hybrid tests. |
| EVAL-01 | 16-01, 16-05 | nDCG@k, Hit@k, p50/p95 benchmark output | SATISFIED | Truth 1; pure helpers, rendering, and CLI tests. |
| EVAL-02 | 16-01, 16-03, 16-05 | At least 50 categorized queries with tuning/held-out split | SATISFIED | Truth 2; direct 56-query parse, integrity tests, drift gate. |
| EVAL-03 | 16-04, 16-05 | Fixed weight/k sweep and honest 0.01 noise rule | SATISFIED | Truths 3, 8, 13, 15; grid/tie/split tests plus live sweep recomputation. |
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

The only skip-pattern hits are conditional sqlite-vec runtime guards in `test_hybrid.py`; sqlite-vec is available here and all tests ran, so no requirement is hidden by a skip. Snapshot values are a regression lock recomputed from the deterministic index, not the sole correctness oracle: metric correctness is independently pinned by hand-calculated metric tests. The manual real-model row is not a test oracle. No insufficient assertions or disabled requirement proofs found.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | - | No TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER markers, placeholder implementations, or unwired stubs in the phase source, tests, scripts, fixtures, docs, or changed ledger files | - | - |

### Human Verification

None pending. The two planned manual-only items are dispositioned `passed` in `16-UAT.md` (2/2, 0 pending, frontmatter now canonical `status: complete`): item 2 (operator-hardware rerank latency) was already passed, and item 1 (real-model held-out evidence) is backed by the recorded 2026-11-12 measurement and the corresponding Broken Window closure. The deterministic snapshot remains the CI gate; no truth is behavior-unverified.

### Gaps Summary

No gaps and no regressions. The Phase 16 goal holds at HEAD `353fe33`: the categorized synthetic fixture is intact and generator-reproducible; the fixed 45-configuration sweep remains tuning-only and applies the strict rounded 0.01 tie rule (a fresh live recomputation reproduced the `20/1.0/0.5` winner, nDCG@10 0.8680, and the 30/45 tie group with no winner); the held-out snapshot still recomputes and locks the shipped 60/1.0/1.0 defaults at nDCG@10 0.8120; and rerank opt-in, candidate bounding, and relative-threshold behavior remain wired and test-proven. The only post-pass change is the UAT status-vocabulary correction, backed by the recorded real-model measurement.

---

_Verified: 2026-11-12T10:42:35Z_
_Verifier: Claude (gsd-verifier)_
