# Phase 16: Bench Expansion + Reranker Tuning - Research

**Researched:** 2026-11-08
**Domain:** Offline search evaluation (nDCG/Hit/latency), weight-grid sweep with tie-group honesty, and reranker cost control (candidate cap + relative threshold + explicit opt-in)
**Confidence:** HIGH — every load-bearing behavior below was read from the repository this session or reproduced with a local probe. External claims are limited to the standard nDCG formula (cited) and are corroborated by a hand-computed example.

## Summary

The phase extends three existing seams rather than inventing a subsystem. `SearchEvaluator` (`src/sif/search/benchmark.py:42-109`) already loads `{"queries": [...]}` fixtures and returns a flat metric dict; `bench_cmd` (`src/sif/cli/commands/bench.py:25-148`) already builds a `SearchPipeline` per query and renders table/JSON; `RRFFusion.fuse` already accepts per-call `weights` and `k` (`src/sif/search/rrf.py:20-26`), which Phase 15 routes from `SearchOptions.rrf_k/bm25_weight/vector_weight` (`src/sif/core/models.py:288-294`). The new work is therefore: graded-relevance metrics + per-category/split reporting, a pure sweep-ranking layer with the 0.01 tie rule, a committed corpus pack with deterministic test embeddings, and reranker cost control.

Two code-inventory findings change the shape of the plan. **First, `candidate_limit` is currently a no-op whenever it exceeds `limit`.** `BM25Searcher` SQL-`LIMIT`s to `options.limit` (`src/sif/search/bm25.py:83-85`), `VectorSearcher` trims to `options.limit` (`src/sif/search/vector.py:125-131`), and `HybridSearcher` fuses with `options.limit` (`src/sif/search/hybrid.py:76-81`); only then does the pipeline slice `results[: options.candidate_limit]` (`hybrid.py:241`). With the default `limit=10`, a cap of 20 can never admit an 11th candidate. QUAL-05's cap only becomes real if the pipeline over-fetches to `max(limit, candidate_limit)` before reranking. **Second, rerank is effectively ON by default today.** `query_cmd` constructs a reranker whenever `settings.reranker_model_name` is truthy (`src/sif/cli/commands/search.py:892-895`), and the default name is `Qwen/Qwen3-Reranker-0.6B` (`src/sif/config/settings.py:148-151`); `SearchPipeline` then reranks unconditionally when a reranker exists (`hybrid.py:239-246`). There is no `--rerank` flag and no enable setting anywhere in `src/`, `tests/`, or `docs/`. D-12's "explicit opt-in, off path zero-cost by construction" therefore requires adding an enable switch and changing the default, not merely tuning a threshold.

The benchmark fixture has a reproducibility trap: document IDs are random UUIDs (`Document.id` default factory), so a committed fixture cannot key relevance by `document_id`. Key graded relevance by **path relative to a declared corpus root** instead (while preserving legacy `relevant_docids`). For CI, build the synthetic index directly with fixed document IDs and a deterministic test-only concept embedder (the `tests/unit/search/test_hybrid.py:620-773` golden fixture is the template); a real-model run is needed only for the documented held-out evidence, because real embedding models are not reproducible across platforms/model versions. A 200-doc / 30-query local probe measured warmed hybrid search at **p50 0.495 ms, p95 0.723 ms**, and a 45-config sweep at **0.735 s total (16.3 ms/config)** when BM25+vector re-run per config with cached query embeddings — so D-07's "minute-scale" budget is comfortably met.

**Primary recommendation:** Extend `benchmark.py` with pure, unit-tested metric functions (`ndcg_at_k`, `hit_at_k`, `percentile`) and a `BenchReport` layer; keep `evaluate()` backward-compatible; make the sweep a pure ranking function over config results (ε=0.01 tie group, tuning-only ranking, held-out Δ≥0.01 re-check); over-fetch to `max(limit, candidate_limit)` in `SearchPipeline` only when reranking; apply `score ≥ top1 × α` in the shared `_sort_and_build_results` helper; and add `SIF_RERANK_ENABLED` (default false), `SIF_RERANK_CANDIDATE_LIMIT` (20, 5-50), `SIF_RERANK_RELATIVE_THRESHOLD` (0.5, 0<α≤1) plus a `--rerank` flag.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Benchmark fixture (EVAL-02)
- **D-01:** **Synthetic corpus committed to the repo** — a compact corpus pack (~100-300 docs) covering the four query categories, committed with its fixture; deterministic, reviewable, privacy-safe, CI-runnable. The user's real KB is an optional local run only (never committed).
- **D-02:** **Graded relevance 0-3** per query (0 irrelevant / 1 partial / 2 relevant / 3 highly relevant) — nDCG needs graded signal to be meaningful; binary labeling was rejected (degrades nDCG toward precision@k).
- **D-03:** **Fixed split written into the fixture** — every query carries `split: tuning|heldout`; tuning (~30) is the only set sweep may consult; shipped-default changes require held-out (~20) evidence at Δ≥0.01 (EVAL-04). No runtime-random splitting.

#### Metrics & output (EVAL-01)
- **D-04:** **nDCG@10 + Hit@10 + p50/p95 per-query latency** for every measured configuration; extra k values are optional additive reporting (k=10 aligns with the interactive page size).
- **D-05:** **Latency = warmed per-query time** (searcher call to results; embedding model preloaded); cold-start reported separately, never mixed into p50/p95 — consistent with Phase 14/15 measurement culture (CLI startup excluded).
- **D-06:** **Table + `--json` output, both with a per-category breakdown** (keyword/synonym/multilingual/rival) alongside global metrics — catches a tuning win that quietly regresses one category; fixed JSON structure feeds the sweep.

#### Sweep (EVAL-03)
- **D-07:** **Fixed declared grid** ≈ 45 configs: rrf_k ∈ {20,40,60,80,100} × bm25_weight ∈ {0.5,1,2} × vector_weight ∈ {0.5,1,2}; query embeddings computed ONCE per sweep and reused (BM25 leg re-runs per config) — minute-scale on the micro-corpus. No arbitrary user-defined grid flag (one well-motivated default grid satisfies EVAL-03).
- **D-08:** **Noise rule = 0.01 tie groups + held-out re-verification** — ranking key is mean nDCG@10 on the tuning set; configs within <0.01 of the best form one explicit "tie group" and no single winner is declared; any default change must then reproduce on held-out at Δ≥0.01 (EVAL-04).
- **D-09:** **Bench reads global settings; baseline delta** — `sif bench` (no sweep) runs with the current `SIF_` settings as the configuration (this FIXES Phase 15's IN-02 finding); `--sweep` overrides per config through `SearchOptions` (Phase 15 D-03's bridge) and prints the current-settings run as the baseline row with per-metric deltas.

#### Reranker tuning (QUAL-05)
- **D-10:** **Candidate cap** — `SIF_RERANK_CANDIDATE_LIMIT` default **20**, range 5-50; applies only when rerank is enabled; setting-only (no CLI flag — low-frequency knob).
- **D-11:** **Relative threshold** — `SIF_RERANK_RELATIVE_THRESHOLD` default **0.5** (0<α≤1): keep candidates scoring ≥ top1×α; relative rather than absolute (no model-distribution tuning); 0.5 is a conservative start, refinable via bench/held-out.
- **D-12:** **Skip-rerank fast path = explicit opt-in** — rerank stays off unless requested (`--rerank` / setting); the off path is zero-cost by construction. When enabled, cap × threshold bound the cost. **Bench reports rerank on/off as two measured states** (metrics + latency each) — makes QUAL-05's "fast path keeps interactive latency" measurable.
- **D-13:** **Existing surfaces** — `sif bench` and `SearchEvaluator` (`src/sif/search/benchmark.py`) are extended (not rewritten): metrics computation, sweep orchestration, and rerank-state dimension layer onto them; `LlamaCppReranker` (`src/sif/search/rerank.py`) gains cap+threshold in its scoring path.

#### Carried forward (pre-decided — do not re-litigate)
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

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description (REQUIREMENTS.md) | Research Support |
|----|-------------------------------|------------------|
| QUAL-05 | reranker candidate cap (CPU 10-20) + relative threshold (≥top1×α) configurable; skip-rerank fast path keeps interactive latency | Candidate-cap no-op finding + `max(limit, candidate_limit)` fetch fix; shared `_sort_and_build_results` threshold hook; explicit `SIF_RERANK_ENABLED`/`--rerank` opt-in finding; bench off/on states |
| EVAL-01 | `sif bench` outputs nDCG@k, Hit@k, p50/p95 latency | Standard exponential-gain nDCG formula (cited) + worked examples; pure metric helpers; warmed-latency measurement design; table/JSON + per-category breakdown |
| EVAL-02 | benchmark fixture ≥50 categorized queries (keyword/synonym-paraphrase/multilingual/rival) + tuning/held-out split | Committed corpus layout; path-keyed graded relevance (UUID finding); 56-query / 36-tuning / 20-heldout proposal; deterministic CI index builder + CJK/FTS tokenizer pitfall |
| EVAL-03 | `sif bench --sweep` grids weights/k; differences <0.01 not declared winners | 45-config grid through `SearchOptions`; pure `rank_sweep()` tie-group function + test design; embedding-once caching wrapper; measured sweep cost |
| EVAL-04 | shipped defaults justified by held-out data, not tuning-set overfitting | Tuning-only ranking guard; held-out Δ≥0.01 re-check; committed defaults snapshot test; documented evidence artifact |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Quality gates after every plan: `ruff check src tests`, `ruff format --check src tests`, `pytest`.
- `ty check src/sif`; new code fully annotated (functions take and return typed values).
- Python 3.10+; `list[str] | None` unions; line length 100; max mccabe complexity 10; ruff isort `combine-as-imports = true`; stdlib → third-party → `sif` imports; two blank lines after imports.
- CLI user-facing errors: `click.ClickException(str(e))`.
- Database transactions: `Database.transaction()` with automatic rollback.
- Module loggers: `logger = get_logger(__name__)` (stderr).
- Zero new runtime dependencies — `pyproject.toml:28-40` has no slot for this phase's work; numpy is already a runtime dependency (`numpy>=1.24.0`, `pyproject.toml:39`) and already imported by `src/sif/embedding/embedder.py`, `src/sif/search/rerank.py`, and `src/sif/search/expansion.py`.
- `docs/cli-reference.md` and `docs/configuration.md` are generator-owned; never hand-edit. CI regenerates and diffs them (`.github/workflows/docs.yml:38-42`).
- Test invocation in agent shells: UNSET `FORCE_COLOR` (`env -u FORCE_COLOR NO_COLOR=1 pytest ...`); `FORCE_COLOR=0` still fails spuriously.
- No `noqa` exemptions used to duck complexity; split helpers instead.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Metric definitions (nDCG/Hit/percentile) | Search core (`search/benchmark.py`) | — | Pure functions, no DB/CLI dependencies; directly unit-testable |
| Fixture parsing/validation | Search core (`SearchEvaluator`) | — | Existing home; must accept legacy + graded schemas |
| Per-config evaluation orchestration | CLI (`cli/commands/bench.py`) | Search core | CLI owns DB/embedder/model wiring; core computes metrics |
| Sweep grid + tie-group ranking | Search core (`benchmark.py`) | CLI | Pure ranking function over measured configs; CLI only renders |
| Query-embedding reuse | CLI (bench) | Embedder wrapper | A dict-caching `Embedder` wrapper around the loaded model; no search-signature change |
| Candidate over-fetch + cap | Search core (`SearchPipeline`) | Domain (`SearchOptions.candidate_limit`) | Pipeline owns pre-rerank slicing; searchers only honor `limit` |
| Relative threshold | Search core (`rerank._sort_and_build_results`) | — | One shared post-normalization filter used by all three rerankers |
| Rerank opt-in | Settings + CLI (`search.query`) | Search core | Off path must not construct a reranker at all |
| Settings + validation ranges | Config (`config/settings.py`) | Generator docs | Pydantic `Field(ge=..., le=...)` fails naming the field |
| Generated docs | Generator (`scripts/generate_config_ref.py`) | CI drift gate | SECTIONS allowlist; `make docs-generate` |
| Narrative docs | Hand edit (`docs/benchmarking.md`, `search-algorithms.md`) | — | Not generator-owned |

## Existing Code Inventory

### `src/sif/search/benchmark.py`
- `precision_at_k(relevance: Sequence[int], k: int) -> float` (`:14-18`) — currently sums truthy relevance (`sum(relevance[:k]) / k`); with graded 0-3 this would sum grades, so it must become binary (`grade > 0`) for graded fixtures.
- `recall_at_k(relevance, total_relevant, k) -> float` (`:21-25`).
- `reciprocal_rank(relevance) -> float` (`:28-33`), `mean_reciprocal_rank(all_relevance) -> float` (`:36-39`).
- `class SearchEvaluator` (`:42`); `__init__(self, fixture: dict)` (`:45`); validation requires `queries` and each item's `query` + `relevant_docids` (`:55-63`); `evaluate(self, search_fn: Callable[[str], list[SearchResult]], k_values: list[int] | None = None) -> dict[str, float]` (`:65-109`). It matches `relevant_ids = set(query_item["relevant_docids"])` against `r.document_id` (`:85-93`) and averages per-k metrics plus `mrr`/`num_queries` (`:103-107`).
- There is no timing, no category/split, no nDCG/Hit.

### `src/sif/cli/commands/bench.py`
- Options (`:25-36`): `FIXTURE` path, `-n/--limit` default 10, `-C/--candidate-limit` default 20, `-c/--collection`, `--all`, `--model-type`, `--json`.
- Loads `json.load(fixture)` (`:68-69`).
- `search_fn` (`:91-122`) constructs a **new** `SearchPipeline` inside every call (`:116-122`); builds `SearchOptions(limit, candidate_limit, include_content=False, include_highlights=False)` (`:94-99`); resolves collection IDs per query (`:101-114`). It ignores per-query `collections` from the fixture. Hoist pipeline construction out of the timed loop so latency measures search rather than `VectorSearcher` re-initialization/vec-extension probing.
- Output (`:124-148`): flat metrics table or `json.dumps(metrics)`; no sweep/rerank/states.

### `src/sif/search/hybrid.py`
- `HybridSearcher.search(query, options)` (`:41-98`): BM25 (`:59`), vector when embedder present (`:62-65`), single-source early returns (`:68-71`), fuse with `options.limit`, `[bm25_weight, vector_weight]`, `k=options.rrf_k` (`:76-81`).
- `SearchPipeline.search` (`:159-251`): prefix routing (`:178`), variant expansion (`:203-221`), per-variant search (`:225-228`), cross-query fusion with `k` only (`:237`), rerank gate `if self.reranker is not None and len(results) > 0:` and `candidates = results[: options.candidate_limit]` (`:239-246`), then snippets and `_attach_contexts` (`:249-251`).

### `src/sif/search/rrf.py`
- `RRFFusion(k: int = 60)` (`:11`); `fuse(self, results_lists, limit=10, weights=None, k=None)` (`:20-26`); weight mismatch raises (`:42-43`); multiply form `weight * (1.0 / (k_eff + rank))` (`:60`); sorts and truncates to `limit` (`:99-109`). Input result objects are not mutated (new `SearchResult` copies are built), so prefetched lists can be reused across sweep configs.

### `src/sif/search/rerank.py`
- `_sort_and_build_results(results, scores, top_k)` (`:24-53`) — shared by all three rerankers; sorts descending, takes `[:top_k]`, rewrites `score`, `rank`, `scores["reranker_score"]`.
- `LlamaCppReranker.__init__(model_path=None, model_name="", n_ctx=512, n_threads=None, batch_size=32)` (`:93-107`); `rerank(query, results, top_k=10)` (`:128-166`) embeds query once, scores each doc, sigmoid-normalizes (`:163-164`).
- `CrossEncoderReranker.rerank` (`:219-249`) and `Qwen3Reranker.rerank` (`:344-396`) both end with `_sort_and_build_results(..., top_k)`.
- `create_reranker(settings)` (`:399-429`) dispatch; Qwen3 auto-detected by name (`:408-414`).

### `src/sif/core/models.py`
- `SearchResult` fields (`:233-251`): `document_id, title, path, collection_name, score, content, highlights, rank, scores, snippet, context_description, vectors_stale`.
- `SearchOptions` (`:271-294`): `limit=10`, `offset=0`, `collection_ids=None`, `min_score=0.0`, `include_content=False`, `include_highlights=True`, `max_highlights=3`, `explain=False`, `candidate_limit=20` (`:285`), `intent=None`, `snippet_max_length=300`, `rrf_k=60`, `bm25_weight=1.0`, `vector_weight=1.0`.

### `src/sif/config/settings.py`
- Reranker settings (`:147-164`): `reranker_model_name` default `"Qwen/Qwen3-Reranker-0.6B"` (`:148-151`), `reranker_model_path`, `reranker_model_type="sentence_transformers"` (`:156-159`), `reranker_batch_size=32`.
- Search/fusion settings (`:189-210`): `rrf_k=60` (`:193-198`), `bm25_weight=1.0` (`:199-204`), `vector_weight=1.0` (`:205-210`) — no upper bound, explicitly so the sweep grid is not capped.
- No `rerank_enabled`, `rerank_candidate_limit`, or `rerank_relative_threshold` fields exist.

### `src/sif/cli/commands/search.py`
- `query_cmd` decorators (`:737-784`): `-n/--limit` default 10, `-C/--candidate-limit` default 20 with `IntRange(1, 200)` (`:745-751`), `--rrf-k`/`--bm25-weight`/`--vector-weight` default `None` for precedence (`:753-770`). **No `--rerank` flag.**
- Options build (`:842-853`) passes `candidate_limit=candidate_limit` and resolves fusion knobs from settings.
- Reranker construction (`:892-895`): `if settings.reranker_model_name or settings.reranker_model_path: ... reranker = create_reranker(settings)`. This is the default-on path.

### Data-flow facts that constrain the design
- BM25 truncates at `options.limit`: `LIMIT ? OFFSET ?` with `params.extend([options.limit, options.offset])` (`src/sif/search/bm25.py:83-85`).
- Vector over-fetches then trims to `options.limit`: `fetch_k = max(options.limit * 4, 50)` (`vector.py:77`), then `results = results[: max(1, options.limit)]` (`:127`).
- `HybridSearcher` fuses at `options.limit` (`hybrid.py:76-81`), so the pre-rerank list length is at most `limit`.

## Standard Stack

**Zero new runtime dependencies.** Everything is stdlib (`json`, `math`, `statistics`/manual interpolation, `time.perf_counter`, `dataclasses`, `pathlib`) plus already-present code and numpy if the team prefers it.

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| stdlib `math` | Python 3.10+ | nDCG gain/discount, sigmoid threshold | `math.log2`, `math.exp`; no deps |
| stdlib `time` | Python 3.10+ | warmed per-query latency | `perf_counter_ns()` monotonic; injectable clock for tests |
| stdlib `json` | Python 3.10+ | fixture + report serialization | Existing bench format |
| stdlib `dataclasses` | Python 3.10+ | `BenchReport`/`ConfigResult`; `dataclasses.replace` for fetch-limit copy | Matches models style |
| `numpy` | already `>=1.24.0` (`pyproject.toml:39`) | optional percentile/metric vectorization | Already used in `embedding/embedder.py`, `search/rerank.py`; NOT required for the recommended pure-Python helpers |
| pytest + pytest-cov | existing dev deps | validation | `[tool.pytest.ini_options]` in pyproject |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pure-Python `percentile()` | `numpy.percentile` | numpy is present, but its `method=` keyword and NaN handling add version/variance surface; a 20-line linear-interpolation helper is exactly testable |
| Exponential-gain nDCG (`2^rel - 1`) | Linear-gain nDCG (`rel / log2(i+1)`) | Both are valid conventions; exponential gain is the one paired with the 0-3 grade scale in CONTEXT and matches PyTorch-Ignite/sklearn-style implementations. Pick one and pin it in tests. |
| Path-keyed relevance | Deterministic document IDs in the corpus | Path keys let the committed pack run through the normal `sif collection add` + `sif index update` flow; deterministic IDs require a bespoke builder for every run |
| Deterministic test embedder | Real model in CI | Real models are not reproducible across platforms/versions; keep CI deterministic and record real-model evidence separately |
| A separate benchmark package | Extend `search/benchmark.py` | D-13 locks extension of the existing surface |

**Installation:** none.

## Package Legitimacy Audit

This phase installs **no external packages**. `pyproject.toml` dependency sections are untouched. The legitimacy gate was therefore not applicable.

| Package | Registry | Verdict | Disposition |
|---------|----------|---------|-------------|
| (none) | — | — | No install step |

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** none.

## Architecture Patterns

### System Architecture Diagram

```
                    committed fixture pack
   corpus/*.md + queries.json (category, split, grades 0-3)
                        │
                        ▼
              ┌─────────────────────┐
              │ Fixture loader +    │  validate: ≥50 queries, 4 categories,
              │ split/category view │  tuning/heldout, grades 0-3
              └─────────┬───────────┘
                        │
                        ▼
   ┌────────────── Evaluation loop per configuration ──────────────┐
   │                                                               │
   │  query ──► SearchPipeline                                     │
   │             ├─ HybridSearcher: BM25 (FTS5) ──┐                │
   │             │                  Vector (vec0) ─┤─► RRFFusion ──┼─► optional
   │             │                  (cached query  │   weights/k   │    rerank:
   │             │                   embedding)    │               │    cap + α
   │             └─ over-fetch max(limit, cap) when rerank on      │
   │                                                               │
   │  wall clock around the call only (warm-up pass first)         │
   └───────────────┬───────────────────────────────────────────────┘
                   │
                   ▼
        per-query grades ──► nDCG@10 / Hit@10 ──► global + per-category
        per-query times  ──► p50 / p95       ──► per-state latency
                   │
        ┌──────────┴───────────┐
        │                      │
   baseline state        --sweep (45 configs)
   current SIF_ settings  rrf_k × bm25_w × vec_w
   rerank off / on        rank by tuning nDCG@10
        │                 tie group ε=0.01 (no winner)
        │                      │
        │                      ▼
        │                 held-out re-check
        │                 Δ≥0.01 vs baseline
        ▼                      ▼
        └────────► table / --json report
```

### Component Responsibilities

| Component | Responsibility | Anchor |
|-----------|----------------|--------|
| `search/benchmark.py` | metric functions, fixture view, report dataclasses, sweep ranking | `:14-109` |
| `cli/commands/bench.py` | DB/embedder/reranker wiring, state orchestration, rendering | `:25-148` |
| `search/hybrid.py` | candidate over-fetch and pre-rerank slicing | `:239-246` |
| `search/rerank.py` | shared threshold filter + per-model scoring | `:24-53` |
| `config/settings.py` | ranges + defaults for cap/α/enable | `:147-164` |
| `scripts/generate_config_ref.py` | register new fields in SECTIONS/env example/rules | `:150-203`, `:359-403` |
| `tests/fixtures/bench/` | corpus, queries, held-out snapshot | new |
| `tests/support/bench.py` | deterministic concept embedder + direct DB builder | new |

### Recommended Project Structure

```
src/sif/search/benchmark.py          # metrics + evaluator + sweep ranking
src/sif/cli/commands/bench.py        # orchestration + output
src/sif/search/rerank.py             # shared threshold + cap semantics
src/sif/config/settings.py           # SIF_RERANK_* fields
tests/fixtures/bench/
├── corpus/
│   ├── keyword/*.md
│   ├── synonym/*.md
│   ├── multilingual/*.md
│   └── rival/*.md
├── queries.json                     # version, corpus_root, relevance_key, queries[]
├── heldout_defaults.json            # committed held-out evidence snapshot
└── README.md
tests/support/bench.py               # ConceptEmbedder + build_bench_db()
tests/unit/search/test_benchmark_metrics.py
tests/unit/search/test_sweep.py
docs/benchmarking.md                 # narrative: format, formulas, sweep rules, evidence
```

**Repository precedent:** there is currently **no** `tests/fixtures/` directory (verified). DB fixtures are built inline: `tests/unit/search/test_hybrid.py:724-773` (real schema + FTS + vec0 + fixed IDs + direct embedding inserts), `tests/unit/search/test_suggest.py:27-45` (schema + seeded docs), and `tests/unit/search/test_staleness.py:40-71` (vec0 + `INSERT ... vec_f32`). The bench pack is the first committed fixture directory; put its shared builder in `tests/support/bench.py` so pytest does not collect it and both unit and CLI tests can import it.

### Pattern 1: Graded metric functions are pure and fixture-agnostic
**What:** `ndcg_at_k(retrieved_grades, ideal_grades, k)`, `hit_at_k(retrieved_grades, k)`, `percentile(values, p)`. The evaluator builds the retrieved grade list in rank order and the ideal list from **all** judgments for that query.
**When to use:** every metric call; never compute nDCG inline in the CLI.
**Example:**
```python
# Source: formula verified by hand below; [CITED: docs.pytorch.org/ignite/master/
# generated/ignite.metrics.rec_sys.NDCG.html — "DCG@K = sum (2^rel_i - 1) / log2(i+1)"]
def dcg_at_k(grades: Sequence[int], k: int) -> float:
    return sum((2**grade - 1) / math.log2(i + 1) for i, grade in enumerate(grades[:k], 1))

def ndcg_at_k(retrieved: Sequence[int], ideal: Sequence[int], k: int) -> float:
    ideal_dcg = dcg_at_k(sorted(ideal, reverse=True), k)
    if ideal_dcg == 0.0:
        return 0.0
    return dcg_at_k(retrieved, k) / ideal_dcg
```
Worked values (verified locally):
- `retrieved=[3,2,0,1], ideal=[3,2,1,0], k=4` → DCG 9.323465818787765, IDCG 9.392789260714373, nDCG 0.9926195041747018.
- `retrieved=[0,0,0]` → IDCG 0 → nDCG 0.0.
- `retrieved=[1,2,3]` (wrong order) → nDCG 0.6806060567602009.
- `retrieved=[3,0], ideal=[3]` → nDCG 1.0 (no other relevant doc exists); if the fixture also judges `[2,1]`, IDCG grows and the same retrieval scores <1. **IDCG must use the full judgment set, not the retrieved subset.**

**Tie handling:** nDCG is computed on the ranking the searcher actually produced. When two results carry equal scores, their order is whatever the stable sort emitted (`_sort_and_build_results` uses Python's stable `sort`; RRF/source order decides elsewhere). Grade assignments differing across tied positions can therefore change nDCG, so deterministic metric tests must use strictly separated scores (or equal grades). Do not add a second tie-break layer inside the metric — the sweep's 0.01 rule is about config *means*, not result-position ties.

### Pattern 2: Path-keyed graded relevance
**What:** Fixture `relevance_key: "path"` with keys relative to `corpus_root`; result keys are computed with `Path(result.path).resolve().relative_to(corpus_root)` and POSIX-normalized. Legacy `relevance_key: "docid"` + `relevant_docids` keeps old fixtures working.
**When to use:** the committed pack (UUIDs are random at index time) and any real-KB run where the user identifies files by path.
**Example:**
```python
def result_key(result: SearchResult, mode: str, corpus_root: Path) -> str:
    if mode == "docid":
        return result.document_id
    try:
        return Path(result.path).resolve().relative_to(corpus_root).as_posix()
    except ValueError:
        return Path(result.path).as_posix()
```

### Pattern 3: Sweep is a pure ranking function, not an evaluation loop
**What:** The CLI measures each config into a `ConfigResult(config, ndcg@10, hit@10, latency, ...)`; a pure `rank_sweep()` applies the tie rule and returns the tie group. This makes SC3's honesty test trivial and deterministic.
**Example:**
```python
EPSILON = 0.01

@dataclass(frozen=True)
class ConfigResult:
    rrf_k: int
    bm25_weight: float
    vector_weight: float
    ndcg_at_10: float
    hit_at_10: float

def rank_sweep(results: Sequence[ConfigResult], epsilon: float = EPSILON) -> tuple[list[ConfigResult], bool]:
    ranked = sorted(results, key=lambda r: r.ndcg_at_10, reverse=True)
    best = ranked[0].ndcg_at_10
    tie_group = [r for r in ranked if best - r.ndcg_at_10 < epsilon]
    return tie_group, len(tie_group) == 1
```
Test with fabricated values: 0.500 vs 0.505 → no winner; 0.500 vs 0.520 → winner; 0.500 vs 0.510 → exactly at the boundary, **not** within noise (strict `<`). Also assert exactly 45 configs and that the baseline (60, 1.0, 1.0) is one of them.

### Pattern 4: Embedding-once wrapper
**What:** A tiny `Embedder`-shaped memo around the loaded model:
```python
class CachedEmbedder:
    def __init__(self, inner: Embedder) -> None:
        self._inner = inner
        self._cache: dict[str, list[float]] = {}

    def embed(self, text: str) -> list[float]:
        if text not in self._cache:
            self._cache[text] = self._inner.embed(text)
        return self._cache[text]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]

    @property
    def dimension(self) -> int:
        return self._inner.dimension
```
Pass it as `SearchPipeline(..., embedder=CachedEmbedder(manager._model))`. `HybridSearcher` calls only `.embed(query)` (`hybrid.py:64`), so no search-signature change is needed. D-07's "BM25 leg re-runs per config" remains true; the model is not called again.

### Pattern 5: Over-fetch before rerank
**What:** In `SearchPipeline.search`, when a reranker exists, search/fuse with `fetch_limit = max(options.limit, options.candidate_limit)`, then slice to the cap:
```python
from dataclasses import replace

fetch_options = replace(options, limit=max(options.limit, options.candidate_limit))
# ... hybrid.search(q, fetch_options) and rrf.fuse(..., fetch_options.limit, ...)
candidates = results[: options.candidate_limit]
reranked = self.reranker.rerank(parsed_query, candidates, top_k=options.limit)
```
Only the rerank-on path changes; rerank-off stays byte-identical. `BM25Searcher` and `VectorSearcher` already honor `limit`/`offset`, and vector over-fetch (`max(limit*4, 50)`) scales with it. Note the `offset` interaction: use `max(limit + offset, candidate_limit)` if offset must remain meaningful.

### Anti-Patterns to Avoid
- **Computing metrics in `bench_cmd`:** duplicates formulas and makes the sweep untestable. Keep them in `benchmark.py`.
- **Keying committed relevance by `document_id`:** IDs are random UUIDs; the fixture will never match a freshly built index.
- **Running the real embedding model in CI snapshots:** platform/model-version variance makes the test flaky. Use the deterministic concept embedder; record real-model numbers separately.
- **Asserting absolute p95 in CI:** wall-clock tests are flaky. Inject a clock or assert only ordering/presence.
- **Declaring a winner when the tie group has >1 config:** violates SC3 and D-08.
- **Letting sweep read the held-out split:** violates D-03/D-08; add an explicit assertion/spy in the sweep implementation.
- **Applying α before sigmoid normalization:** the threshold is defined on the final `[0,1]` scores. Apply it in `_sort_and_build_results` after normalization.
- **Constructing the reranker on the fast path:** D-12 says zero-cost by construction; the condition must be checked before `create_reranker`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| nDCG/DCG | ad-hoc positional scoring | exponential-gain formula above | Standard definition; needs exact IDCG handling |
| Percentiles | `sorted(xs)[int(len(xs)*p)]` (biased, non-interpolated) | linear-interpolation helper or `numpy.percentile` | Stable p95 for small samples; testable |
| Sorting/scoring/truncation after rerank | per-class copies | shared `_sort_and_build_results` (`rerank.py:24-53`) | One place for cap/α/rank/score metadata |
| Embedding cache | new persistent cache layer | dict memo wrapper | Model already loaded; sweep only needs per-process reuse |
| Fixture validation | silent `.get()` defaults | explicit validation with named errors | A malformed grade/split silently corrupts held-out evidence |
| Corpus prose | hand-writing 150 docs | deterministic generator script committed with output | Reviewable and reproducible; no accidental drift |

**Key insight:** the hard part of this phase is not any single formula; it is preserving the honesty contract (tuning vs held-out, noise vs signal) while keeping the old flat metrics/JSON working. Pure functions plus a committed snapshot make that contract testable.

## Common Pitfalls

### Pitfall 1: `candidate_limit` is currently capped by `limit`
**What goes wrong:** A cap of 20 with `-n 10` sends at most 10 candidates to the reranker, so QUAL-05's cap never binds.
**Why:** BM25 `LIMIT options.limit` (`bm25.py:83-85`), vector trim to `options.limit` (`vector.py:127`), RRF truncation to `options.limit` (`hybrid.py:76-81`), and only then `results[: options.candidate_limit]` (`hybrid.py:241`).
**How to avoid:** over-fetch to `max(limit, candidate_limit)` when a reranker is present (Pattern 5); add a test where 20 documents exist, `limit=3`, `candidate_limit=20`, and the reranker receives 20.
**Warning signs:** reranker mock receives exactly `min(limit, candidate_limit)` docs; benchmark's `-C 20` changes nothing.

### Pitfall 2: Rerank is silently ON by default
**What goes wrong:** `sif query` loads/reranks with Qwen3-Reranker on every query under default settings, so the "skip-rerank fast path" does not exist.
**Why:** `if settings.reranker_model_name or settings.reranker_model_path:` (`search.py:892-895`) plus the non-empty default `reranker_model_name` (`settings.py:148-151`) plus `if self.reranker is not None` (`hybrid.py:239-246`). There is no enable flag/setting.
**How to avoid:** add `SIF_RERANK_ENABLED` (default false) + `--rerank`; construct the reranker only when enabled. Bench's off state passes `reranker=None`.
**Warning signs:** `create_reranker` called in tests that did not ask for reranking; query latency dominated by model load on first call; `create_reranker` ImportError path still constructs.

### Pitfall 3: CJK text and FTS5 `porter` tokenization
**What goes wrong:** Multilingual Chinese queries silently miss documents under BM25.
**Why:** `documents_fts` uses `tokenize='porter'` (`schema.py:244-251`); contiguous CJK runs are tokenized coarsely. Local probe output:
```
"机器学习"* -> [(1,), (2,)]
"机器"*     -> [(1,), (2,)]
"学习"*     -> []            # mid-run prefix does NOT match
"人工智能"* -> [(2,)]        # only the space-separated document
```
**How to avoid:** in the multilingual category, use space-separated Chinese terms or exact contiguous tokens that appear in the docs; put paraphrase pressure on the vector leg; assert every tuning/heldout query returns ≥1 result on the deterministic index during fixture validation.
**Warning signs:** a whole category scores nDCG 0 for BM25-heavy configs; the sweep declares vector-heavy weights the winner for the wrong reason.

### Pitfall 4: Random document UUIDs break committed relevance
**What goes wrong:** A fixture with `relevant_docids` never matches a rebuilt index.
**Why:** `Document.id` defaults to `uuid.uuid4()` (`models.py:136`); the incremental indexer does not derive it from the path (`incremental.py:357-364`).
**How to avoid:** path-keyed `relevance` + `corpus_root` (Pattern 2); or a deterministic direct-insert builder with fixed IDs for tests (`test_hybrid.py:724-773`).
**Warning signs:** every query returns nDCG 0 even though results look right.

### Pitfall 5: Real-model nondeterminism in the held-out snapshot
**What goes wrong:** CI fails on a different machine or after a model update.
**Why:** torch/MPS/CUDA kernel differences and model revisions change embeddings; tie ordering can flip.
**How to avoid:** CI snapshot uses the deterministic concept embedder and fixed vectors; the real-model evidence run is documented with model name, hardware, date, and command, and is not a CI gate.
**Warning signs:** snapshot diffs in the 4th decimal after an unrelated dependency upgrade.

### Pitfall 6: Wall-clock flakiness in latency tests
**What goes wrong:** p95 assertions fail under load.
**Why:** CI machines share CPUs; Python startup and GC add variance.
**How to avoid:** inject `clock: Callable[[], float]` into the evaluator for unit tests; measure real latency only in the CLI/bench path and assert structural properties (p50 ≤ p95, sample count, states present). A generous integration smoke bound is acceptable; no tight p95.
**Warning signs:** tests that pass locally and fail in CI; retries hiding variance.

### Pitfall 7: Tie-group boundary and baseline omission
**What goes wrong:** Exactly-0.01 differences are wrongly called ties, or the baseline config is missing from the grid.
**Why:** ambiguous `<` vs `<=`; a hand-built grid that forgets (60, 1.0, 1.0).
**How to avoid:** strict `< 0.01`; assert the grid contains the baseline; unit-test 0.009/0.010/0.011 differences.
**Warning signs:** `winner_declared=True` with two configs at 0.500/0.505; baseline delta row all zeros because it is not in the grid.

### Pitfall 8: Legacy metrics silently reinterpret grades
**What goes wrong:** `precision_at_k` becomes `sum(grades)/k` (up to 3.0), and `recall_at_k` denominators count grades.
**Why:** current code sums truthy values (`benchmark.py:18,25`).
**How to avoid:** switch precision/recall/Hit to binary `grade > 0`; keep legacy `relevant_docids` mapping to grade 1 so old tests are unchanged.
**Warning signs:** precision >1.0 on graded fixtures.

### Pitfall 9: Complexity gate on `bench_cmd`
**What goes wrong:** adding `--sweep`, states, categories, and JSON rendering pushes `bench_cmd` past mccabe 10 / PLR0913.
**Why:** it already carries a `# noqa: C901, PLR0913, PLR0915` (`bench.py:38`); the project culture avoids adding more.
**How to avoid:** extract `_build_options()`, `_measure_state()`, `_render_report()`, `_run_sweep()`; keep `bench_cmd` a thin orchestrator.
**Warning signs:** new `noqa` entries; ruff C901.

### Pitfall 10: Settings-mock churn in CLI tests
**What goes wrong:** reading `settings.rerank_candidate_limit` / `settings.rerank_enabled` on the ~15 `MagicMock` settings objects in `tests/unit/cli/test_search.py` returns a `MagicMock`, which leaks into `SearchOptions` or a truthiness check.
**Why:** existing mocks enumerate only a few fields (`test_search.py:1413-1416` etc.).
**How to avoid:** add the new fields to the mocks, or resolve defensively (`value if isinstance(value, int) else 20`); add a shared settings factory in the test module. Budget this as real churn.
**Warning signs:** `candidate_limit` is a `MagicMock` in assertions; tests pass for the wrong reason.

### Pitfall 11: Applying α to raw (pre-sigmoid) scores
**What goes wrong:** the threshold behaves differently per reranker (logits vs probabilities).
**Why:** `_sort_and_build_results` receives normalized scores for all three rerankers today (`rerank.py:163-164`, `:246-247`, `:393`).
**How to avoid:** keep normalization where it is and filter inside `_sort_and_build_results`; document that α is a fraction of the top normalized score.

## Code Examples

### Warmed per-query latency with an injectable clock
```python
# Source: project precedent — tests/unit/search/test_suggest.py:312-321 times the core call
# with perf_counter and only a generous bound; Phase 14 avoids latency asserts entirely.
def measure(search_fn: Callable[[str], list[SearchResult]], queries: Sequence[str],
            clock: Callable[[], float] = time.perf_counter) -> tuple[list[float], list[list[SearchResult]]]:
    for q in queries:          # warm-up: models loaded, caches hot, result discarded
        search_fn(q)
    samples: list[float] = []
    outputs: list[list[SearchResult]] = []
    for q in queries:
        start = clock()
        results = search_fn(q)
        samples.append((clock() - start) * 1000.0)
        outputs.append(results)
    return samples, outputs
```

### Percentile with linear interpolation
```python
def percentile(values: Sequence[float], p: float) -> float:
    """p in [0, 100]; linear interpolation between closest ranks."""
    if not values:
        return 0.0
    ordered = sorted(values)
    pos = (len(ordered) - 1) * (p / 100.0)
    lo = math.floor(pos)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)
```
Test: `percentile([1..10], 50) == 5.5`, `percentile([1..10], 95) == 9.55` (verified locally against `statistics.quantiles(..., method="inclusive")`).

### Shared rerank threshold filter
```python
def _sort_and_build_results(
    results: list[SearchResult],
    scores: list[float],
    top_k: int,
    relative_threshold: float = 0.0,
) -> list[SearchResult]:
    scored = list(zip(results, scores, strict=True))
    scored.sort(key=lambda x: x[1], reverse=True)
    if scored and relative_threshold > 0.0:
        top = scored[0][1]
        if top > 0.0:
            scored = [pair for pair in scored if pair[1] >= top * relative_threshold]
    # ... existing slice/rebuild loop ...
```
Constructors gain `relative_threshold: float = 0.0` (no filtering for direct construction/tests); `create_reranker` passes `settings.rerank_relative_threshold` so production defaults to 0.5.

### Sweep orchestration shape
```python
GRID_K = (20, 40, 60, 80, 100)
GRID_W = (0.5, 1.0, 2.0)

def iter_grid(settings: Settings) -> Iterator[dict[str, float | int]]:
    yield {"rrf_k": settings.rrf_k, "bm25_weight": settings.bm25_weight,
           "vector_weight": settings.vector_weight}  # baseline
    for k in GRID_K:
        for bw in GRID_W:
            for vw in GRID_W:
                yield {"rrf_k": k, "bm25_weight": bw, "vector_weight": vw}

def evaluate_config(pipeline: SearchPipeline, queries: Sequence[QueryItem],
                    options: SearchOptions) -> ConfigResult:
    ndcgs, hits = [], []
    for item in queries:                      # queries already filtered to split="tuning"
        results = pipeline.search(item.query, options)
        retrieved = [item.grades.get(result_key(r), 0) for r in results]
        ndcgs.append(ndcg_at_k(retrieved, list(item.grades.values()), 10))
        hits.append(hit_at_k(retrieved, 10))
    return ConfigResult(options.rrf_k, options.bm25_weight, options.vector_weight,
                        sum(ndcgs) / len(ndcgs), sum(hits) / len(hits))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Binary precision/recall/MRR only | graded nDCG + Hit + latency | this phase | nDCG is meaningful only with graded labels (D-02) |
| Bench ignores `SIF_` fusion settings | bench baseline = current `SIF_` settings | this phase (fixes Phase 15 IN-02) | Sweep deltas are measured against the actual default |
| Rerank always on when a model name is set | explicit `SIF_RERANK_ENABLED` / `--rerank` | this phase | Fast path becomes genuinely zero-cost |
| `candidate_limit` caps below `limit` only | over-fetch to `max(limit, cap)` then rerank | this phase | The cap actually controls cost |
| Real-model-only benchmarking | deterministic CI pack + separate real-model evidence | this phase | Reproducible CI without losing honest quality evidence |

**Deprecated/outdated:** no external library is deprecated here. Internally, the flat `evaluate()` return remains supported but new code should consume `BenchReport`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | CI uses a deterministic concept embedder; real-model numbers are a documented local run | Architecture Patterns, Validation | If the user expects real-model CI assertions, snapshots become flaky or the suite slows dramatically |
| A2 | `SIF_RERANK_ENABLED` (bool, default false) + `--rerank` is the right reading of D-12's "explicit opt-in (`--rerank` / setting)" | Existing Code Inventory, Pitfall 2 | If only a flag is wanted, the extra setting is harmless but undocumented surface |
| A3 | The existing `-C/--candidate-limit` flag stays (default changed to `None` so the setting can apply) rather than being removed | Settings / CLI | Removing a shipped flag is breaking; keeping it may read as contradicting "setting-only" |
| A4 | Corpus target ≈150 docs (within D-01's 100-300) and 56 queries (36 tuning / 20 held-out) | Fixture design | Too small a corpus makes Δ=0.01 noise-dominated; too large slows CI |
| A5 | "Interactive" needs a documented p95 threshold (e.g., 500 ms off-state on the reference corpus), not a CI assertion | Validation | SC5's latency claim remains qualitative |
| A6 | Multilingual means Chinese + English with space-separated CJK terms or exact tokens | Pitfall 3 | A real CJK KB behaves differently; the category may overstate BM25 ability |
| A7 | Shipped defaults likely stay 60/1.0/1.0 this phase; the deliverable is honest evidence, not a forced change | EVAL-04 | If held-out does warrant a change, the snapshot and docs must be updated in-phase |
| A8 | nDCG uses exponential gain `2^rel - 1` | Metric design | A linear-gain comparison with external numbers is not apples-to-apples |

**If this table is non-empty:** these are the decisions the planner/discuss-phase should confirm before locking.

## Open Questions (RESOLVED)

1. **Absolute interactive-latency target**
   - What we know: D-05 excludes CLI startup and measures warmed per-query time; Phase 14 UAT measured a +105 ms pre-command walk on a 3000-doc corpus.
   - What's unclear: whether SC5 needs a numeric threshold or just relative off/on evidence.
   - Recommendation: define and document `p95(rerank off) < 500 ms` on the reference corpus, but do not gate CI on it; report both states.
   - **Resolution:** adopted — docs/benchmarking.md documents p95(rerank off) < 500 ms as a target and Plan 04/05 report both states; no CI threshold (16-04, 16-05).

2. **Rerank-on state in bench**
   - What we know: D-12 requires two measured states; `--rerank` is the explicit request.
   - What's unclear: whether `SIF_RERANK_ENABLED=1` should make bench automatically measure the on state.
   - Recommendation: bench always measures off; `--rerank` adds on. The setting governs `sif query`, not bench.
   - **Resolution:** adopted — bench measures off always and on only with `--rerank`; `SIF_RERANK_ENABLED` governs `sif search query` (16-02, 16-04).

3. **Where the held-out evidence lives**
   - What we know: EVAL-04 requires "documented"; docs are partly generator-owned.
   - What's unclear: user-facing `docs/benchmarking.md` vs a phase report.
   - Recommendation: `docs/benchmarking.md` for the method + evidence table, plus the raw JSON/console output in the phase verification artifact.
   - **Resolution:** adopted — `docs/benchmarking.md` carries the method/evidence table and `tests/fixtures/bench/heldout_defaults.json` carries the machine-checked snapshot (16-05).

4. **Should defaults change if held-out warrants?**
   - What we know: defaults move only at Δ≥0.01 held-out.
   - What's unclear: whether the tuning set will produce a >0.01 held-out win on the synthetic pack.
   - Recommendation: treat "no change, documented" as a valid outcome; update the snapshot only with the evidence.
   - **Resolution:** adopted — the snapshot records the sweep-winner candidate's held-out delta and a verdict; "unchanged" is valid and "change-warranted" requires updating defaults in-phase (16-05).

5. **How the committed pack's index is built for a real run**
   - What we know: `sif bench` needs an existing index; the pack can be indexed through normal commands.
   - What's unclear: whether to add a `--corpus` convenience flag.
   - Recommendation: document `sif collection add` + `sif index update` (and `sif index embed` for the vector leg) in `docs/benchmarking.md`; add no new flag unless the user asks.
   - **Resolution:** adopted — `sif collection add` + `sif index update` + `sif index embed` + `sif bench` are documented; no `--corpus` flag is added (16-05). Note: `sif embed` is a removed command (tests/test_docs.py), so the vector leg is `sif index embed`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | all | ✓ | 3.13.9 local (project targets 3.10+) | — |
| pytest / pytest-cov | validation | ✓ | installed | — |
| numpy | optional metrics | ✓ | installed (`>=1.24.0` in pyproject) | pure-Python helpers |
| sqlite-vec | vector leg / vec0 DB | ✓ | v0.1.9 (probe) | BM25-only run (metrics still work, vector leg absent) |
| sentence-transformers | real embedding/reranker evidence | ✓ | installed | deterministic concept embedder for CI |
| llama-cpp-python | GGUF reranker evidence | ✓ | installed | sentence-transformers/Qwen3 backend |
| transformers + torch | Qwen3 reranker | ✓ | installed | use a cross-encoder or skip rerank-on evidence |
| Reranker model weights | rerank-on bench | not verified (may require download) | — | report rerank-off only with a warning |

**Missing dependencies with no fallback:** none for the code/test work.
**Missing dependencies with fallback:** reranker weights / real embedding model for the evidence run — configure a local model or record that the on-state evidence was produced on the reference machine.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-cov (`[tool.pytest.ini_options]`, `pyproject.toml`) |
| Config file | `pyproject.toml` (no separate pytest.ini) |
| Quick run command | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search/test_benchmark_metrics.py tests/unit/search/test_sweep.py -x` |
| Full suite command | `env -u FORCE_COLOR NO_COLOR=1 pytest` (STATE: 1015 tests @ 96.2%, `fail_under=90`) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QUAL-05 | α filters scores below `top1 × α`; top1 always retained | unit | `pytest tests/unit/inference/test_reranker.py -k relative_threshold -x` | ✅ extend |
| QUAL-05 | cap over-fetch: `limit=3, cap=20` → reranker receives 20 | unit | `pytest tests/unit/search/test_hybrid.py -k candidate_fetch -x` | ✅ extend |
| QUAL-05 | settings ranges: cap 5-50, α (0,1], enabled bool | unit | `pytest tests/unit/config/test_settings.py -k rerank -x` | ✅ extend |
| QUAL-05 | rerank-off path constructs no reranker and results are identical | integration (CliRunner) | `pytest tests/unit/cli/test_search.py -k rerank_off -x` | ✅ extend |
| EVAL-01 | nDCG/Hit hand-computed cases, zero-IDCG, fewer-than-k, graded precision | unit | `pytest tests/unit/search/test_benchmark_metrics.py -x` | ❌ Wave 0 |
| EVAL-01 | percentile p50/p95 exact values + empty input | unit | `pytest tests/unit/search/test_benchmark_metrics.py -k percentile -x` | ❌ Wave 0 |
| EVAL-01 | `bench --json` has nDCG@10/Hit@10/p50/p95 + category breakdown | integration | `pytest tests/unit/cli/test_bench.py -k metrics -x` | ✅ extend |
| EVAL-02 | fixture has ≥50 queries, ≥20 held-out, 4 categories, grades 0-3 | unit (fixture validation) | `pytest tests/unit/search/test_benchmark_metrics.py -k fixture_contract -x` | ❌ Wave 0 |
| EVAL-02 | every corpus-relative relevance key exists; each query returns ≥1 result | integration | `pytest tests/unit/search/test_bench_fixture.py -x` | ❌ Wave 0 |
| EVAL-03 | grid has 45 configs incl. baseline; tie group at <0.01; boundary at 0.01 | unit | `pytest tests/unit/search/test_sweep.py -k tie -x` | ❌ Wave 0 |
| EVAL-03 | sweep ranking reads tuning only; embedder called once per query | unit (spy) | `pytest tests/unit/search/test_sweep.py -k split -x` | ❌ Wave 0 |
| EVAL-04 | held-out metrics equal committed snapshot; defaults match snapshot | integration (deterministic DB) | `pytest tests/unit/search/test_bench_snapshot.py -x` | ❌ Wave 0 |
| EVAL-04 | changing a default without updating the snapshot fails | integration | `pytest tests/unit/search/test_bench_snapshot.py -k default_lock -x` | ❌ Wave 0 |
| SC3 | two configs 0.005 apart → tie group, no winner | unit | `pytest tests/unit/search/test_sweep.py -k no_winner -x` | ❌ Wave 0 |
| SC5 | off-state p50 ≤ p95 and both states present in the report | structural (injected clock) | `pytest tests/unit/search/test_benchmark_metrics.py -k latency -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** the touched-module quick run above.
- **Per wave merge:** `ruff check src tests && ruff format --check src tests && env -u FORCE_COLOR NO_COLOR=1 pytest`.
- **Phase gate:** full suite green + `make docs-generate` produces a clean `git diff --exit-code docs/cli-reference.md docs/configuration.md` after the settings fields land.

### Wave 0 Gaps
- [ ] `tests/unit/search/test_benchmark_metrics.py` — nDCG/Hit/percentile/precision-binary/latency injection.
- [ ] `tests/unit/search/test_sweep.py` — grid enumeration, tie groups, boundary, tuning-only guard, embedding-once spy.
- [ ] `tests/unit/search/test_bench_fixture.py` — fixture contract + corpus/relevance integrity.
- [ ] `tests/unit/search/test_bench_snapshot.py` — deterministic DB + held-out snapshot/default lock.
- [ ] `tests/support/bench.py` — `ConceptEmbedder` + `build_bench_db()` (direct `SchemaManager` + fixed IDs + vec0 inserts, modeled on `test_hybrid.py:620-773`).
- [ ] `tests/fixtures/bench/{corpus,queries.json,heldout_defaults.json}` — the committed pack.
- [ ] `docs/benchmarking.md` — format, formulas, sweep rule, evidence table; add it to `DOCS_FILES` in `tests/test_docs.py:20-31`.
- [ ] Extend `tests/unit/cli/test_bench.py` for `--sweep`, `--rerank`, states, categories, JSON schema.
- [ ] Extend `tests/unit/inference/test_reranker.py`, `tests/unit/search/test_hybrid.py`, `tests/unit/config/test_settings.py`, `tests/unit/cli/test_search.py` for cap/α/opt-in.

## Security Domain

`security_enforcement` is absent from `.planning/config.json`, so it is treated as enabled. The phase adds no network surface and no new dependencies.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | local single-user tool |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | fixture JSON validated (types, grades 0-3, known category/split, k bounds); no SQL built from fixture text; `corpus_root` resolved and constrained to the fixture directory; query strings reach FTS only through the existing `_sanitize_term`/`_build_fts_query` path (`bm25.py:21-33`) |
| V6 Cryptography | no | — |
| V12 File Handling | marginal | reads the committed corpus and the user-specified fixture; no writes outside the DB |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `corpus_root` / relevance keys | Tampering / Information Disclosure | Resolve and require the root to be the fixture directory (or a descendant); never `open()` a relevance key directly |
| Malformed/huge fixture JSON (DoS) | Denial of Service | `json.load` inside `try` → `ClickException`; cap file size/query count with a clear error |
| FTS5 MATCH injection through fixture queries | Tampering | Reuse `_sanitize_term` (metachars `["*():^]` stripped, tokens double-quoted) — never interpolate fixture text into SQL |
| Sensitive data in the committed corpus | Information Disclosure | Synthetic corpus only; never commit a real KB (D-01) |
| Reading unrelated files via result paths | Information Disclosure | Path-key normalization is read-only and only compares; never opens result paths |

## Sources

### Primary (HIGH confidence)
- Source files Read this session (all line-anchored claims above): `src/sif/search/benchmark.py`, `src/sif/cli/commands/bench.py`, `src/sif/search/rerank.py`, `src/sif/search/rrf.py`, `src/sif/search/hybrid.py`, `src/sif/search/bm25.py`, `src/sif/search/vector.py`, `src/sif/core/models.py`, `src/sif/config/settings.py`, `src/sif/database/schema.py`, `src/sif/database/repositories.py`, `src/sif/database/database.py`, `src/sif/indexing/incremental.py`, `src/sif/cli/commands/search.py`, `src/sif/cli/main.py`, `src/sif/mcp/backend.py`, `scripts/generate_config_ref.py`, `scripts/generate_cli_ref.py`, `Makefile`, `pyproject.toml`, `tests/test_docs.py`, `.github/workflows/docs.yml`, `tests/conftest.py`, `tests/unit/search/test_benchmark.py`, `tests/unit/cli/test_bench.py`, `tests/unit/search/test_rerank.py`, `tests/unit/inference/test_reranker.py`, `tests/unit/search/test_hybrid.py`, `tests/integration/test_search_pipeline.py`, `tests/unit/cli/test_search.py`, `tests/unit/config/test_settings.py`.
- Local probe `/tmp/sif16_probe/probe.py` (python3.13, sqlite-vec 0.1.9, 200 synthetic docs, 30 queries): hybrid warm latency p50 0.495 ms / p95 0.723 ms; 45-config sweep with BM25+vector re-run = 0.735 s (16.3 ms/config); fusion-only reuse = 0.005 s.
- Local FTS5 probe (python3.13 stdlib sqlite3, `tokenize='porter'`): `"学习"*` returned `[]` while `"机器"*` matched both documents — mid-run CJK prefixes do not match.
- nDCG worked values verified locally (`math.log2`, exponential gain).
- Prior-project anchors: `.planning/phases/15-.../15-REVIEW.md:244-254` (IN-02), `15-RESEARCH.md`, `14-RESEARCH.md` (bench bypass / deterministic-drift culture), `STATE.md`, `REQUIREMENTS.md`.

### Secondary (MEDIUM confidence)
- PyTorch-Ignite NDCG documentation — formula quoted verbatim: “DCG@K = ∑ (2^{rel_i} − 1) / log_2(i + 1)”, “NDCG@K = DCG@K / IDCG@K”, IDCG from sorting by true relevance, graded 0-4 supported. [docs.pytorch.org/ignite/master/generated/ignite.metrics.rec_sys.NDCG.html]
- Python `statistics.quantiles(..., method="inclusive")` behavior cross-checked against the custom percentile helper (local probe).

### Tertiary (LOW confidence)
- None — no claim above rests on training-only memory.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new deps; numpy presence and usage verified; all primitives are stdlib.
- Architecture: HIGH — every integration point Read this session with line anchors; two behavior-changing findings (cap no-op, rerank default-on) proven from the code.
- Pitfalls: HIGH — cap/no-op and CJK behavior reproduced locally; snapshot nondeterminism and wall-clock flakiness follow established project culture (Phases 12/14/15).
- Fixture design: MEDIUM — corpus size/count are judgment calls within D-01/D-03 bounds (A4), and the deterministic-embedder split is a recommendation (A1).

**Research date:** 2026-11-08
**Valid until:** 2026-12-08 (stable domain; re-verify only if the default embedding/reranker model changes)
