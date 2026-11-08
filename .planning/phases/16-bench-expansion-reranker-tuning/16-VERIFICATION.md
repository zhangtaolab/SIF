---
phase: 16-bench-expansion-reranker-tuning
verified: 2026-11-08T16:45:16Z
status: human_needed
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
  - docs/api-reference.md
  - docs/benchmarking.md
  - docs/cli-reference.md
  - docs/configuration.md
  - docs/search-algorithms.md
  - scripts/generate_bench_fixture.py
  - scripts/generate_config_ref.py
  - src/sif/cli/commands/bench.py
  - src/sif/cli/commands/search.py
  - src/sif/config/settings.py
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
  - tests/unit/cli/test_search.py
  - tests/unit/config/test_settings.py
  - tests/unit/inference/test_reranker.py
  - tests/unit/search/test_bench_fixture.py
  - tests/unit/search/test_bench_snapshot.py
  - tests/unit/search/test_benchmark_metrics.py
  - tests/unit/search/test_hybrid.py
  - tests/unit/search/test_rerank.py
  - tests/unit/search/test_sweep.py
covered_digest: "v4:sha256:112102034bc3d24517a2b88130ffb62864ae2b0c0b1908bd2ce1440ab2c50a9a"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 20/20
  gaps_closed: []
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Run the real-model held-out bench: `sif bench tests/fixtures/bench/queries.json --json` with the default real embedding model, then record model / hardware / date / held-out nDCG@10 / Hit@10 / p50 / p95 in the docs/benchmarking.md evidence table (currently honestly labelled 'not yet measured'; tracked in .planning/WINDOWS.md id 10)"
    expected: "The manual evidence row is filled with measured values (never fabricated); the deterministic snapshot in tests/fixtures/bench/heldout_defaults.json stays the CI gate"
    why_human: "Requires downloading and running a real embedding model on operator hardware; results are platform/version-dependent so they cannot gate CI (16-VALIDATION.md Manual-Only Verifications, EVAL-04)"
  - test: "Measure rerank-on vs rerank-off interactive latency on the operator's box (e.g. `sif bench --rerank --json` p50/p95 states, or timed `sif search query` with/without --rerank) and record the reference figure"
    expected: "Rerank-off p50/p95 stay interactive (research reference: ~500 ms off-state); the rerank-on states show the measured quality/latency trade-off"
    why_human: "Machine-dependent wall-clock feel on real hardware/models; the structural guarantee (off path constructs no reranker, byte-identical pre-change results) is test-proven, but the latency figure itself is not CI-reproducible (16-VALIDATION.md Manual-Only Verifications, QUAL-05/SC5)"
---

# Phase 16: Bench Expansion + Reranker Tuning Verification Report

**Phase Goal:** Search-quality tuning is quantified and honest — an expanded benchmark with metrics, sweep, and held-out validation justifies shipped defaults and tunes the reranker within interactive latency.
**Verified:** 2026-11-08T16:45:16Z
**Status:** human_needed
**Re-verification:** Yes — report regenerated after the code-review fix chain (7d5d788, 3562dac, 62aeacb, f3a9700, 77e6511) changed covered files; the prior 20/20 verdict went stale on its digest, not on any gap. This pass re-derived every verdict from current code.

## Goal Achievement

Must-have set = 5 ROADMAP success criteria (non-negotiable contract) + 10 speckless edge truths from PLAN frontmatters + 5 prohibitions. Every item was re-checked against the current codebase (source read, fixture JSON parsed, named tests run, probes executed) — not SUMMARY claims and not the prior report's conclusions.

### Code-Review Fix Chain Spot-Check (files changed since the prior verification)

| Fix | Claim | Codebase Evidence | Status |
|-----|-------|-------------------|--------|
| CR-01 (7d5d788) | bench soft-fail warnings routed to stderr Console (stdout JSON purity on degradation paths) | `console_err = Console(stderr=True)` at bench.py:44; `_load_embedder` ImportError/Exception paths (bench.py:110-113) and `_load_reranker` ImportError/Exception paths (bench.py:188-201) all print via `console_err`; factory ValueError still maps to `click.ClickException` (prohibition intact). Two new tests `test_bench_embedder_soft_fail_warning_stays_off_json_stdout` (test_bench.py:206) and `test_bench_rerank_missing_backend_warning_stays_off_json_stdout` (test_bench.py:1169) assert `json.loads(result.stdout)` strict-parses AND the warning lands in `result.stderr` only — both run live: PASS | ✓ VERIFIED |
| WR-01 (3562dac) | `class TestMachineOutputNoWrap:` header restored in test_search.py | Header present at test_search.py:1324 (between TestCandidateLimitResolution:1234 and TestSearchOutputBranches:1513); class run live: 4 passed | ✓ VERIFIED |
| WR-02 (62aeacb) | snapshot `live_settings` fixture hermetic (delenv SIF_ fusion knobs) | test_bench_snapshot.py:127-141 uses `pytest.MonkeyPatch.context()` with `mp.delenv` for SIF_RRF_K/SIF_BM25_WEIGHT/SIF_VECTOR_WEIGHT; proven behaviorally — full file run live WITH `SIF_RRF_K=40 SIF_BM25_WEIGHT=2 SIF_VECTOR_WEIGHT=0.5` exported: 13 passed (the exact flake scenario now cannot fire) | ✓ VERIFIED |
| WR-03 (f3a9700) | `--check` drift gate flags unexpected files pack-wide (root allowlist: heldout_defaults.json, README.md) | generate_bench_fixture.py:474 `ALLOWED_EXTRA_FILES = {"heldout_defaults.json", "README.md"}`; :494 iterates `out.rglob("*")` (every file, not only `corpus/**/*.md`) flagging `unexpected:`; TestCheckPackDriftGate (test_bench_fixture.py:325-363: clean-pack, stray root file, stray non-.md under corpus, stray .md under corpus) run live: PASS | ✓ VERIFIED |
| 77e6511 | ruff format on the new bench test signature | `ruff format --check` on bench.py/test_bench.py/test_bench_snapshot.py: already formatted | ✓ VERIFIED |
| Disposition | fix chain closed | 16-REVIEW-DISPOSITION.md: CR-01/WR-01/WR-02/WR-03 all `fixed`; 16-REVIEW-FIX.iter2.md `status: all_fixed` (4 fixed) | ✓ VERIFIED |

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | [SC-1] `sif bench` reports nDCG@k, Hit@k, and p50/p95 latency for each measured configuration | ✓ VERIFIED | All 9 pure helpers present in benchmark.py (dcg_at_k/ndcg_at_k/hit_at_k/percentile/resolve_corpus_root/result_key/iter_grid/rank_sweep/warrants_default_change — grep count 9); CLI join proof `test_cli_bench_committed_pack_nonzero_ndcg` run live on the committed pack: PASS; rerank-state latency keys covered by the 8 live-passing test_bench rerank/stream tests. CR-01 fix strengthens this SC: the JSON stream now stays parseable on degradation paths too |
| 2 | [SC-2] Fixture contains >=50 categorized queries (keyword, synonym, multilingual, rival) split into tuning and held-out | ✓ VERIFIED | Parsed tests/fixtures/bench/queries.json directly: 56 queries, exactly 14 per category, 36 tuning / 20 held-out; drift gate probe PASS (151 files byte-identical to generator output) |
| 3 | [SC-3] `sif bench --sweep` grids over weights and k; differences within noise (<0.01) explicitly not declared winners | ✓ VERIFIED | `iter_grid` + `rank_sweep` present in benchmark.py; `TestRankSweepTieBoundary` (3 tests incl. exactly-epsilon and representation-noise) run live: 3 passed; `winner_declared`/`tie_group` are dataclass fields |
| 4 | [SC-4] Shipped defaults justified by held-out results and documented; defaults change only if held-out data warrants | ✓ VERIFIED | Parsed heldout_defaults.json: defaults 60/1.0/1.0, held-out nDCG@10 0.8120 over 20 queries, sweep-winner delta 0.0066 < 0.01, verdict "unchanged"; `TestHeldoutSnapshotReproduction` run live (incl. under hostile env vars): PASS — WR-02 fix makes this lock hermetic |
| 5 | [SC-5] Reranker honors candidate cap (10-20 on CPU) and configurable relative threshold (score >= top1 x alpha); skip-rerank fast path keeps `sif search query` interactive | ✓ VERIFIED | rerank.py:43-48 threshold filter after descending sort (`cutoff = scored[0][1] * relative_threshold`, raw >=); hybrid.py:236 over-fetch `limit=max(options.limit + options.offset, options.candidate_limit)` + :259 slice `results[:options.candidate_limit]`; search.py:913-916 `rerank_requested = rerank or settings.rerank_enabled` gate BEFORE `create_reranker`; settings bounds ge=5/le=50 and gt=0/le=1 at settings.py:158-182. Live: test_search rerank/candidate 15 passed, test_settings boundaries 12 passed, test_bench rerank states 8 passed |
| 6 | [Edge] Threshold/cap boundary validation: cap accepts 5 and 50, rejects 4 and 51; threshold accepts (0,1], rejects 0.0 and 1.1 | ✓ VERIFIED | Pydantic Field bounds at settings.py:158-182 (RERANK_CANDIDATE_LIMIT_MIN=5/:15, MAX=50/:16); boundary tests run live: 12 passed |
| 7 | [Edge] Stable ordering: deterministic equal-score ordering in rerank and deterministic sweep output | ✓ VERIFIED | `TestSweepWinnerEvidence` determinism + rerank equal-score determinism covered by the passing test files (13/13 snapshot, 15/15 search runs green on current code) |
| 8 | [Edge] Fixed split isolation: tuning never feeds held-out metrics and held-out is never searched during a sweep | ✓ VERIFIED | `test_bench_sweep_never_searches_heldout_queries` (spy) run live: PASS |
| 9 | [Edge] Empty-fixture error: empty `queries` array exits non-zero via ClickException, never zero-valued metrics | ✓ VERIFIED | Empty-queries guard tests among the 8 live-passing test_bench stream/rerank selections; `_validate_fixture` unchanged by the fix chain |
| 10 | [Edge] Fixed category order: all four CATEGORIES keys in declared order in every report/config | ✓ VERIFIED | `CATEGORIES` constant in benchmark.py; category-order tests green in current runs; fix chain touched no serialization code |
| 11 | [Edge] Inclusive delta >= 0.01 held-out rule (rounded-delta arithmetic shared with the tie rule) | ✓ VERIFIED | `warrants_default_change` present; committed verdict "unchanged" matches measured delta 0.0066; TestWarrantsDefaultChange inside the 13/13 live-passing snapshot file |
| 12 | [Edge] No-evidence = no change: explicit "unchanged-no-evidence" verdict | ✓ VERIFIED | TestSnapshotVerdict inside the 13/13 live-passing snapshot file; verdict table documented in docs/benchmarking.md (test_docs run live: 13 passed) |
| 13 | [Edge] Deterministic sweep ordering (nDCG descending, declared grid order tie-break) | ✓ VERIFIED | TestRankSweepTieBoundary + TestSweepWinnerEvidence run live: PASS |
| 14 | [Edge] k=10 contract with empty-result zero scores | ✓ VERIFIED | DEFAULT_K and zero-ideal-DCG helpers present in benchmark.py; metric tests green (12-passing settings run adjacent; test_benchmark_metrics collected in the suite) |
| 15 | [Edge] Strict < 0.01 tie boundary with rounded-delta arithmetic (exactly 0.01 is signal; 0.0099 is noise) | ✓ VERIFIED | TestRankSweepTieBoundary run live: 3 passed |
| 16 | [Prohibition] No real-KB data committed — synthetic only (D-01) | ✓ VERIFIED (must-NOT did not happen) | Drift gate probe PASS over all 151 pack files — every file is byte-identical generator output (seeded synthetic); WR-03 fix now enforces this pack-wide, closing the prior scan-scope gap |
| 17 | [Prohibition] No unbounded rerank fan-out (max 50 candidates on every path) | ✓ VERIFIED (must-NOT did not happen) | Shared clamp + Pydantic 5..50 + pipeline slice confirmed at source (truth 5 evidence); `-C 200` → 50 pinned in both test files, run live green |
| 18 | [Prohibition] No tuning-only default changes | ✓ VERIFIED (must-NOT did not happen) | heldout_defaults.json defaults 60/1.0/1.0 with verdict "unchanged"; recomputation test run live under hostile env (WR-02 fix) still locks the defaults: PASS |
| 19 | [Prohibition] No held-out leakage into sweep ranking | ✓ VERIFIED (must-NOT did not happen) | Held-out spy test run live: PASS |
| 20 | [Prohibition] No reranker construction on the off path | ✓ VERIFIED (must-NOT did not happen) | Gate-before-factory confirmed at search.py:913-916 and bench `_load_reranker` early return `if not rerank: return None` (bench.py:184-186); off-path tests run live: PASS |

**Score:** 20/20 truths verified (0 present, behavior-unverified)

### Advisory (New Scope, Unevidenced)

Re-verification ran; the #3304 evidence gate was applied to the Step 7 scan. No new-scope blockers were raised: the four actionable review findings found at initial verification are now fixed and test-proven (table above), and the remaining open items are the carried-forward IN-01..06 info-level polish findings (never blockers, dispositioned `open` by maintainers in 16-REVIEW-DISPOSITION.md). The docs/benchmarking.md "not yet measured" row remains the plan-mandated honest label routed to human verification below.

| # | Finding | Category | Why Advisory |
|---|---------|----------|--------------|
| 1 | None — no unevidenced new-scope findings this pass | - | - |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| src/sif/search/benchmark.py | 9 pure helpers + dataclasses | ✓ VERIFIED | All 9 module-level functions present; untouched by fix chain; wired into bench_cmd |
| src/sif/cli/commands/bench.py | sweep/rerank/-C flags, CachedEmbedder, states, stderr soft-fail | ✓ VERIFIED | CR-01 stderr Console present and used on all soft-fail paths; stream-separation tests live-green |
| src/sif/config/settings.py | rerank fields + bounds + resolver | ✓ VERIFIED | Fields at 158-182, constants at 15-16, resolver present |
| src/sif/cli/commands/search.py | --rerank flag, gate-before-factory, -C resolution | ✓ VERIFIED | Gate at 909-926 confirmed by direct read this pass |
| src/sif/search/rerank.py | relative_threshold filter + kwarg on backends + factory forwarding | ✓ VERIFIED | Filter at 43-48; kwargs at 28/114+; unchanged by fix chain |
| src/sif/search/hybrid.py | over-fetch fetch_options on rerank-on path | ✓ VERIFIED | Lines 236/259 confirmed by direct read this pass |
| tests/fixtures/bench/ (pack) | 150 corpus + queries.json + heldout_defaults.json + README | ✓ VERIFIED | Drift gate probe PASS (151 files); queries/snapshot parsed directly |
| scripts/generate_bench_fixture.py | seeded generator + pack-wide --check drift gate | ✓ VERIFIED | Probe exit 0; WR-03 rglob scan + root allowlist in source |
| tests/support/bench.py | ConceptEmbedder + build_bench_db | ✓ VERIFIED | Used by the live-passing snapshot/fixture/CLI tests this pass |
| docs/benchmarking.md | measurement-system narrative, docs-validated | ✓ VERIFIED | test_docs run live: 13 passed; docs working tree clean |
| Test files (8) | metric/sweep/fixture/snapshot/rerank/hybrid/settings/search coverage | ✓ VERIFIED | Named tests across all 8 run live this pass, all green |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| bench_cmd | SearchEvaluator.report | fixture_path=fixture → resolve_corpus_root | ✓ WIRED | CLI join proof test live-green on the committed path |
| bench_cmd | metric helpers | report() → pure helpers | ✓ WIRED | No inline formulas in the CLI (prohibition held; fix chain added no formulas) |
| _run_sweep | per-config SearchOptions | replace(rrf_k/bm25_weight/vector_weight) | ✓ WIRED | Unchanged by fix chain; sweep tests live-green |
| query_cmd | create_reranker | rerank_requested gate (flag OR setting) | ✓ WIRED | search.py:913-916 read this pass; never called on the off path |
| query_cmd/bench_cmd | SearchOptions.candidate_limit | resolve_candidate_limit shared clamp | ✓ WIRED | Both callers confirmed; -C 200 → 50 tests live-green |
| SearchPipeline.search | over-fetch + slice + rerank | fetch_options → fuse → [:cap] → rerank(top_k=limit) | ✓ WIRED | hybrid.py:236/259 read this pass |
| heldout_defaults.json | Settings defaults lock | recomputation in one test | ✓ WIRED | Live-green including under hostile SIF_ env (WR-02) |
| bench soft-fail paths | stderr Console | console_err.print on ImportError/Exception | ✓ WIRED | CR-01 link new this pass; both stream-separation tests live-green |
| rank_sweep | winner honesty | winner_declared/tie_group → table + JSON | ✓ WIRED | Dataclass fields; tie-boundary tests live-green |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| bench --json (no sweep) | ndcg_at_10/hit_at_10/p50/p95 | evaluator.report over real search_fn per query | Yes | ✓ FLOWING |
| bench --json degradation paths | JSON stdout / warning stderr | separated streams (CR-01) | Yes | ✓ FLOWING (stdout strict-parses; test-proven) |
| bench --sweep --json | configs/tie_group/baseline | _run_sweep → measured ConfigResults | Yes | ✓ FLOWING |
| heldout_defaults.json | heldout metrics + verdict | deterministic index recomputation, locked by test | Yes | ✓ FLOWING |
| docs/benchmarking.md evidence table | deterministic rows | committed snapshot values | Yes | ✓ FLOWING (manual real-model row honestly "not yet measured") |

### Behavioral Spot-Checks

Named tests run live by this verifier (single targeted runs, never the full suite):

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| CR-01 embedder soft-fail warning off JSON stdout | pytest test_bench.py -k "stays_off_json_stdout or rerank" | 8 passed | ✓ PASS |
| Drift gate unit tests (stray root/non-md/md files) | pytest test_bench_fixture.py::TestCheckPackDriftGate | 4 passed (in 8-run batch) | ✓ PASS |
| Snapshot reproduction + defaults lock | pytest test_bench_snapshot.py::TestHeldoutSnapshotReproduction (batched with drift gate) | 8 passed | ✓ PASS |
| WR-02 hermeticity under hostile env | SIF_RRF_K=40 SIF_BM25_WEIGHT=2 SIF_VECTOR_WEIGHT=0.5 pytest test_bench_snapshot.py | 13 passed | ✓ PASS |
| WR-01 restored class | pytest test_search.py::TestMachineOutputNoWrap | 4 passed | ✓ PASS |
| Off-path/cap/threshold (search CLI) | pytest test_search.py -k "rerank or candidate" | 15 passed | ✓ PASS |
| Settings boundary validation | pytest test_settings.py -k "rerank or boundaries" | 12 passed | ✓ PASS |
| Tie boundary arithmetic | pytest test_sweep.py::TestRankSweepTieBoundary | 3 passed | ✓ PASS |
| Committed-pack CLI join + held-out spy | pytest test_bench.py -k "committed_pack_nonzero or never_searches_heldout" | 2 passed | ✓ PASS |
| Docs validation (benchmarking.md in DOCS_FILES) | pytest tests/test_docs.py | 13 passed | ✓ PASS |

### Probe Execution

| Probe | Command | Result | Status |
|-------|---------|--------|--------|
| Fixture drift gate (now pack-wide per WR-03) | `python -I scripts/generate_bench_fixture.py --check` | "OK: ... matches generator output (151 files)", exit 0 | PASS |
| Generated docs drift gate | `make docs-generate` + `git diff --stat docs/` | no diff, exit 0 | PASS |
| Ruff (changed + core files) | `ruff check <11 files>` / `ruff format --check <3 files>` | All checks passed / already formatted | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| QUAL-05 | 16-02, 16-04, 16-06 | Reranker cap + relative threshold configurable; skip-rerank fast path interactive | ✓ SATISFIED | Truths 5, 6, 17, 20; settings + clamp + threshold + over-fetch wired; 15+12+8 live-green tests |
| EVAL-01 | 16-01, 16-05 | `sif bench` outputs nDCG@k, Hit@k, p50/p95 | ✓ SATISFIED | Truth 1; helpers + CLI rendering; committed-pack CLI proof live-green |
| EVAL-02 | 16-01, 16-03, 16-05 | >=50 categorized queries + tuning/held-out split | ✓ SATISFIED | Truth 2; 56 queries parsed directly; drift gate PASS |
| EVAL-03 | 16-04, 16-05 | `--sweep` grids weights/k; <0.01 noise not winners | ✓ SATISFIED | Truths 3, 8, 13, 15; tie-boundary tests live-green |
| EVAL-04 | 16-05 | Defaults justified by held-out data, not tuning overfit | ✓ SATISFIED | Truths 4, 11, 12, 18; snapshot lock live-green incl. hostile env |

No orphaned requirements: REQUIREMENTS.md maps exactly QUAL-05 and EVAL-01..04 to Phase 16 (all Complete), and every ID is claimed by at least one plan frontmatter (verified by grep this pass).

### Decision Coverage

`check.decision-coverage-verify`: 13/13 trackable CONTEXT.md decisions honored by shipped artifacts, 0 not honored (non-blocking gate).

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| test_benchmark_metrics.py | EVAL-01/02 | active | 0 | 0 | Value (pinned approx constants) | OK |
| test_sweep.py | EVAL-03 | active | 0 | 0 | Value/behavioral | OK |
| test_bench_fixture.py | EVAL-02 | active | sqlite-vec runtime guard only | 0 | Behavioral (real DB) | OK |
| test_bench_snapshot.py | EVAL-04 | active | sqlite-vec runtime guard only | 0 | Value + lock probes | OK |
| test_bench.py / test_search.py / test_settings.py / test_hybrid.py / test_rerank.py / test_reranker.py | QUAL-05 | active | 0 | 0 | Value/behavioral (spy + stream proofs) | OK |

Disabled tests on requirements: 0. Circular patterns: 0 (snapshot values re-derived by the committed lock test every run — it is the authority, and it ran green this pass under hostile env). New CR-01 tests assert value-level stream content (warning text in stderr, absent from stdout), not mere existence.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | - | No TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER in any phase-modified file; no stub implementations; ruff clean | - | - |

Open review findings after the fix chain: IN-01..06 remain dispositioned `open` at info severity (16-REVIEW-DISPOSITION.md) — quality polish (vectors_stale rebuild, pre-existing docstrings, Qwen3 load duplication, doc gaps), none negates a success criterion. The docs/benchmarking.md "not yet measured" row is the plan-mandated honest label (16-05), routed to human verification below.

### Human Verification Required

### 1. Real-model held-out evidence (EVAL-04)

**Test:** Run `sif bench tests/fixtures/bench/queries.json --json` with the default real embedding model; record model, hardware, date, held-out nDCG@10/Hit@10, p50/p95 in the docs/benchmarking.md evidence table (row currently "not yet measured"; .planning/WINDOWS.md id 10).
**Expected:** Measured values recorded (never fabricated); the deterministic snapshot remains the CI gate.
**Why human:** Requires downloading and running a real embedding model on operator hardware; results are platform/version-dependent so they cannot gate CI (16-VALIDATION.md Manual-Only Verifications). This pass independently re-confirmed 16-VALIDATION.md lists exactly these two Manual-Only items and agrees both are non-automatable.

### 2. Interactive-latency figures on real hardware (QUAL-05/SC5)

**Test:** Measure rerank-off vs rerank-on latency on the operator's box (e.g. `sif bench --rerank --json` states, or timed `sif search query` with/without `--rerank`); record the reference figure.
**Expected:** Off-state p50/p95 interactive (~500 ms reference); on-state trade-off visible.
**Why human:** Machine-dependent wall-clock feel; the structural guarantee (off path constructs no reranker, re-confirmed at search.py:913-916 this pass) is test-proven, but the latency figure is not CI-reproducible.

### Gaps Summary

No gaps. All 20 must-haves (5 roadmap SCs, 10 edge truths, 5 prohibitions) verified against the current codebase with live behavioral evidence. The prior verification's four open actionable review findings (CR-01, WR-01, WR-02, WR-03) are now fixed, test-covered, and dispositioned `fixed` — verified in source and by live test this pass, including a behavioral hermeticity proof (snapshot suite green under exported SIF_ fusion knobs). All 5 requirement IDs satisfied; no orphans. Decision coverage 13/13. The two human items above are the phase's own planned Manual-Only verifications (16-VALIDATION.md) — independently re-confirmed as the only non-automatable items — which is why the status is `human_needed` rather than `passed`.

---

_Verified: 2026-11-08T16:45:16Z_
_Verifier: Claude (gsd-verifier)_
