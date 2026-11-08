# Phase 16: Bench Expansion + Reranker Tuning - Context

**Gathered:** 2026-11-08
**Status:** Ready for planning

<domain>
## Phase Boundary

The milestone's final phase — make search-quality tuning quantified and honest:

1. **Expanded benchmark (EVAL-01/02)** — `sif bench` reports nDCG@10, Hit@10, p50/p95 per-query latency; a committed synthetic fixture with ≥50 categorized queries (keyword / synonym-paraphrase / multilingual / rival-notes) split into fixed tuning vs held-out sets.
2. **Sweep (EVAL-03)** — `sif bench --sweep` grids rrf_k × bm25_weight × vector_weight; differences within noise (<0.01 mean nDCG@10) are not declared winners.
3. **Shipped defaults justified (EVAL-04)** — default changes only when held-out data (Δ≥0.01) warrants it.
4. **Reranker tuning (QUAL-05)** — candidate cap (default 20, 5-50) + relative threshold α (default 0.5) configurable; the skip-rerank fast path keeps `sif query` interactive.

NOT in scope: new retrieval algorithms, new dependencies, LLM-assisted weight tuning (FUTR-02), spellfix1/symspellpy (FUTR-01/03), any watch/host work.

</domain>

<decisions>
## Implementation Decisions

### Benchmark fixture (EVAL-02)
- **D-01:** **Synthetic corpus committed to the repo** — a compact corpus pack (~100-300 docs) covering the four query categories, committed with its fixture; deterministic, reviewable, privacy-safe, CI-runnable. The user's real KB is an optional local run only (never committed).
- **D-02:** **Graded relevance 0-3** per query (0 irrelevant / 1 partial / 2 relevant / 3 highly relevant) — nDCG needs graded signal to be meaningful; binary labeling was rejected (degrades nDCG toward precision@k).
- **D-03:** **Fixed split written into the fixture** — every query carries `split: tuning|heldout`; tuning (~30) is the only set sweep may consult; shipped-default changes require held-out (~20) evidence at Δ≥0.01 (EVAL-04). No runtime-random splitting.

### Metrics & output (EVAL-01)
- **D-04:** **nDCG@10 + Hit@10 + p50/p95 per-query latency** for every measured configuration; extra k values are optional additive reporting (k=10 aligns with the interactive page size).
- **D-05:** **Latency = warmed per-query time** (searcher call to results; embedding model preloaded); cold-start reported separately, never mixed into p50/p95 — consistent with Phase 14/15 measurement culture (CLI startup excluded).
- **D-06:** **Table + `--json` output, both with a per-category breakdown** (keyword/synonym/multilingual/rival) alongside global metrics — catches a tuning win that quietly regresses one category; fixed JSON structure feeds the sweep.

### Sweep (EVAL-03)
- **D-07:** **Fixed declared grid** ≈ 45 configs: rrf_k ∈ {20,40,60,80,100} × bm25_weight ∈ {0.5,1,2} × vector_weight ∈ {0.5,1,2}; query embeddings computed ONCE per sweep and reused (BM25 leg re-runs per config) — minute-scale on the micro-corpus. No arbitrary user-defined grid flag (one well-motivated default grid satisfies EVAL-03).
- **D-08:** **Noise rule = 0.01 tie groups + held-out re-verification** — ranking key is mean nDCG@10 on the tuning set; configs within <0.01 of the best form one explicit "tie group" and no single winner is declared; any default change must then reproduce on held-out at Δ≥0.01 (EVAL-04).
- **D-09:** **Bench reads global settings; baseline delta** — `sif bench` (no sweep) runs with the current `SIF_` settings as the configuration (this FIXES Phase 15's IN-02 finding); `--sweep` overrides per config through `SearchOptions` (Phase 15 D-03's bridge) and prints the current-settings run as the baseline row with per-metric deltas.

### Reranker tuning (QUAL-05)
- **D-10:** **Candidate cap** — `SIF_RERANK_CANDIDATE_LIMIT` default **20**, range 5-50; applies only when rerank is enabled; setting-only (no CLI flag — low-frequency knob).
- **D-11:** **Relative threshold** — `SIF_RERANK_RELATIVE_THRESHOLD` default **0.5** (0<α≤1): keep candidates scoring ≥ top1×α; relative rather than absolute (no model-distribution tuning); 0.5 is a conservative start, refinable via bench/held-out.
- **D-12:** **Skip-rerank fast path = explicit opt-in** — rerank stays off unless requested (`--rerank` / setting); the off path is zero-cost by construction. When enabled, cap × threshold bound the cost. **Bench reports rerank on/off as two measured states** (metrics + latency each) — makes QUAL-05's "fast path keeps interactive latency" measurable.
- **D-13:** **Existing surfaces** — `sif bench` and `SearchEvaluator` (`src/sif/search/benchmark.py`) are extended (not rewritten): metrics computation, sweep orchestration, and rerank-state dimension layer onto them; `LlamaCppReranker` (`src/sif/search/rerank.py`) gains cap+threshold in its scoring path.

### Carried forward (pre-decided — do not re-litigate)
- Per-query weight overrides (`SearchOptions.rrf_k/bm25_weight/vector_weight`, Phase 15 D-03) are the sweep's only injection channel.
- Zero new runtime dependencies; stdlib only (numpy already present for metrics if needed).
- Held-out overfitting is the governing risk (research PITFALLS); defaults move only on held-out Δ≥0.01.
- Docs are generator-owned where applicable; hand-edited narrative docs updated in-phase.
- `env -u FORCE_COLOR NO_COLOR=1` test invocation; full quality suite per plan.

### Claude's Discretion
- Fixture file format (JSON/JSONL) and corpus pack layout (`tests/fixtures/`-style placement)
- Exact query counts per category (≥50 total with ≥20 held-out)
- Latency percentile computation details (sample count, warm-up runs)
- Sweep output table columns and JSON schema field names
- Cold-start reporting format
- Whether IN-05 (multi-word prefix completions) is also picked up here (nice-to-have, optional)

</decisions>

<canonical_refs>
## Canonical References

- `.planning/REQUIREMENTS.md` — QUAL-05, EVAL-01..04; FUTR-02 rejection (no LLM tuning)
- `.planning/ROADMAP.md` §Phase 16 — goal and success criteria 1-5
- `.planning/phases/15-search-quality-configuration-hybrid-weights-query-suggestions/15-CONTEXT.md` — D-03 per-query override bridge; 15's disposition ledger IN-02 (bench ignores settings — fixed by D-09 here)
- `.planning/research/PITFALLS.md` §search-quality (held-out overfitting)
- `src/sif/search/benchmark.py` (`SearchEvaluator`), `src/sif/cli/commands/bench.py`, `src/sif/search/rerank.py` (`LlamaCppReranker`), `src/sif/search/rerank.py` `top_k` semantics
- `CLAUDE.md` — quality gates, zero-new-deps, generator-owned docs

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SearchEvaluator` (`src/sif/search/benchmark.py:42`) — fixture-driven evaluator to extend with the D-04 metric set; `bench_cmd` (`cli/commands/bench.py`) already loads `{"queries": [...]}` JSON.
- `SearchOptions.candidate_limit` (`core/models.py:285`, default 20) — audit note from STATE: verify its actual effect on rerank candidates and align with D-10.
- `LlamaCppReranker` (`src/sif/search/rerank.py:90`) — `top_k` + `_sort_and_build_results`; add cap/α inside its scoring path.
- Weighted `RRFFusion.fuse(weights, k)` + `SearchOptions` weight fields (Phase 15) — the sweep's injection points.
- `sif bench` JSON table rendering precedent; `--json` output helpers in the CLI commands.

### Established Patterns
- Deterministic tests (no wall-clock races; latency asserts on core functions with generous headroom); fixture-driven batteries in tmp_path.
- Settings → generator doc rows; hand-edited docs updated explicitly (Phase 15 WR-03/04 precedent).
- Fail-soft hooks; ClickException for user errors; typed, fully annotated code (ty gate).

### Integration Points
- `src/sif/search/benchmark.py` — metric functions (nDCG@10/Hit@10/percentiles) + category breakdown
- `src/sif/cli/commands/bench.py` — `--sweep` flag, configs, tie groups, rerank-state dimension, settings-as-baseline
- `src/sif/search/rerank.py` — candidate cap + relative threshold from settings
- `src/sif/config/settings.py` — SIF_RERANK_CANDIDATE_LIMIT / SIF_RERANK_RELATIVE_THRESHOLD (validation ranges)
- New fixture pack (committed corpus + queries with splits/grades)
- `scripts/generate_config_ref.py` SECTIONS + `make docs-generate`; `docs/api-reference.md`/`search-algorithms.md` narrative updates
- `pyproject.toml` — no dependency changes

</code_context>

<specifics>
## Specific Ideas

- SC3's honesty bar is testable: a dedicated test constructs two configs whose mean nDCG@10 differ by <0.01 and asserts the sweep output marks them a tie group (no winner).
- SC4's bar is testable: a test asserts the shipped defaults are asserted against a committed held-out result snapshot; changing defaults without a file update fails.
- Bench's rerank on/off dimension gives QUAL-05 quantitative teeth: the "interactive latency" claim becomes p95 numbers in the report.
- IN-02 from Phase 15's ledger is explicitly fixed by D-09 — close it in that ledger when the bench change lands.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 16-Bench Expansion + Reranker Tuning*
*Context gathered: 2026-11-08*
