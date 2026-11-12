# Benchmarking

How SIF measures search quality: a committed synthetic fixture pack, a deterministic evaluator with graded metrics, a fixed parameter sweep with an explicit noise rule, and a held-out evidence bar that shipped defaults must clear before they can change.

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Benchmark Pipeline                            │
│                                                                      │
│  ┌─────────────┐    ┌───────────────┐    ┌────────────┐             │
│  │   Fixture   │───►│    Search     │───►│  Graded    │             │
│  │  Pack (JSON │    │  Evaluator    │    │  Metrics   │             │
│  │  + corpus)  │    │ (per query)   │    │ (nDCG/Hit) │             │
│  └─────────────┘    └───────┬───────┘    └──────┬─────┘             │
│                            │                   │                    │
│                            ▼                   ▼                    │
│                    ┌───────────────┐    ┌──────────────────┐       │
│                    │ SearchPipeline│    │  BenchReport /   │       │
│                    │ (BM25+Vector  │    │  SweepRanking    │       │
│                    │  + RRF fusion)│    │  + verdict       │       │
│                    └───────────────┘    └──────────────────┘       │
└──────────────────────────────────────────────────────────────────────┘
```

## The Committed Fixture Pack

The pack lives at `tests/fixtures/bench/`:

| Path | Contents |
|------|----------|
| `corpus/` | 150 generated Markdown documents in four category directories |
| `queries.json` | 56 graded queries — 36 `tuning`, 20 `heldout` (9 + 5 per category) |
| `heldout_defaults.json` | The committed held-out evidence snapshot for the shipped defaults |
| `README.md` | The synthetic-only rule and the regeneration workflow |

The four categories each stress a different failure mode:

| Category | Docs | What it measures |
|----------|------|------------------|
| `keyword` | 40 | Exact-term rivalry — unique codenames with successor mentions |
| `synonym` | 38 | Paraphrase pressure on the vector leg (queries share only the topic headword) |
| `multilingual` | 36 | Exact contiguous CJK runs under the porter tokenizer |
| `rival` | 36 | Near-duplicate discrimination (authoritative vs draft, graded 0 neighbors) |

The pack is **synthetic-only**: it contains no real knowledge-base content. It is generator-owned — never hand-edited. Regenerate and drift-check with:

```bash
python scripts/generate_bench_fixture.py --check
```

The `--check` gate exits non-zero on any drift (unexpected files included), and regeneration is byte-identical across runs, so snapshot drift can only come from code, never the pack.

## Fixture Format

A fixture is a JSON file with a `version`, a `corpus_root` (relative roots resolve against the fixture file's directory), `relevance_key: "path"` (relevance keys are corpus-relative POSIX paths, never document ids), and a `queries` list. Every query carries a `category`, a `split` (`tuning` or `heldout`), and a `relevance` map from corpus-relative path to a graded judgment.

Grades are integers `0-3` (3 = authoritative answer, 2 = supporting, 0 = a rival that must rank below). A query with no relevant document in the top-10 scores 0 on Hit@10 and low nDCG.

```json
{
  "category": "keyword",
  "query": "kelpri protocol",
  "relevance": {
    "keyword/kw-002.md": 2,
    "keyword/kw-003.md": 3
  },
  "split": "tuning"
}
```

A query item mixing `relevant_docids` (legacy) and `relevance`, an unknown category or split, or an out-of-range grade is rejected at load time.

## Metrics

### nDCG@10 (exponential gain)

```
DCG@k(retrieved) = Σ_i (2^grade_i - 1) / log2(i + 1)     i starts at 1
nDCG@k           = DCG@k(retrieved) / DCG@k(ideal)
```

The ideal DCG is computed from the **full** judgment set for the query (grades sorted descending), not the retrieved subset — so recall failures reduce the score even when the retrieved documents are perfectly ordered.

Worked example (judgment set: one grade-3 and one grade-2 document):

```python
from sif.search.benchmark import dcg_at_k, ndcg_at_k

ideal = [3, 2]
# Ideal ranking: 7/log2(2) + 3/log2(3) = 8.8928 (the denominator)
dcg_at_k(sorted(ideal, reverse=True), 10)   # 8.892789260914245
# Retrieved [3, 0, 2]: 7/1 + 0 + 3/2 = 8.5
ndcg_at_k([3, 0, 2], ideal, 10)             # 0.95583058934618
# Retrieved [2, 3, 0]: 3/1 + 7/log2(3) = 7.4165 (right docs, worse order)
ndcg_at_k([2, 3, 0], ideal, 10)             # 0.8339912323981488
```

### Hit@10

`1.0` iff any of the top-10 retrieved grades is positive, else `0.0`. Averaged over queries it reads as "share of queries with at least one relevant result on the first page".

### Warmed p50/p95 latency

Percentiles use linear interpolation between closest ranks: for sorted samples, position `(n-1) * p/100`, interpolating between the two adjacent samples. Worked: samples `[10, 20, 30, 40]` ms give p50 = 25.0 ms (position 1.5) and p95 = 38.5 ms (position 2.85).

Latency is **warmed per-query time** (searcher call to results, embedding model preloaded). One full warm-up pass is discarded before timing; the very first warm-up call's duration is reported separately as `cold_start_ms` and never enters the percentile samples. CLI startup is excluded.

## Parameter Sweep and the Tie Rule

`sif bench --sweep` measures a fixed declared grid of 45 configurations — `rrf_k` in {20, 40, 60, 80, 100} × `bm25_weight` in {0.5, 1.0, 2.0} × `vector_weight` in {0.5, 1.0, 2.0} — on the **tuning split only**. Held-out queries are filtered out of the fixture before any search call, so the sweep can never consult them while ranking.

Ranking key: mean nDCG@10 on tuning, descending, with declared grid order as the deterministic tie-break. The noise rule is strict: a configuration is in the tie group iff

```
round(best_ndcg - config_ndcg, 6) < 0.01
```

- **Exactly 0.01 is signal, not a tie.** A nominal 0.01 difference whose raw float subtraction yields 0.009999… still counts as 0.01 (the round-to-6-decimals happens before the comparison).
- **0.0099 and below is noise** — those configurations join the tie group.

A tie group larger than one configuration declares **no single winner** (`winner_declared: false` in the JSON). Query embeddings are computed once per sweep invocation and reused across all 45 configurations.

The current `SIF_` settings run is measured first and printed as the baseline row with per-metric deltas (exactly zero for its own grid slot); a no-sweep `sif bench` run *is* the current-settings baseline.

## Held-Out Evidence and the Defaults Rule

Tuning-set results alone never change shipped defaults. The sweep's best tuning configuration (declared-order first within any tie group) is re-evaluated on the **held-out** split, and only a held-out improvement clears the bar:

```
warrants_default_change(baseline_ndcg, candidate_ndcg)
    = round(candidate_ndcg - baseline_ndcg, 6) >= 0.01
```

Inclusive at exactly 0.01 (same rounded-delta arithmetic as the tie rule); 0.0099 never warrants. The verdict is one of:

| Verdict | Meaning |
|---------|---------|
| `unchanged` | Held-out evidence exists but the delta is below 0.01 — defaults stay |
| `unchanged-no-evidence` | No held-out measurement exists — defaults stay, and the report says so explicitly |
| `change-warranted` | Held-out delta >= 0.01 — a defaults change is justified |

A `change-warranted` verdict is recorded (snapshot + this document) and names its follow-up route: update the defaults in `src/sif/config/settings.py`, update the tests pinning them, and regenerate the snapshot and generated docs. The bench itself never mutates settings.

The committed snapshot `tests/fixtures/bench/heldout_defaults.json` locks the shipped defaults to measured evidence: `tests/unit/search/test_bench_snapshot.py` recomputes the held-out metrics from the deterministic index using the `Settings`-derived configuration, asserts they equal the committed values exactly, and asserts the snapshot's `defaults` object equals the live `Settings` defaults **in the same test** — so changing a default without regenerating the metrics, or editing the snapshot to mask a regression, fails CI.

## Rerank States

Reranking is **explicit opt-in and defaults off**: pass `--rerank` or set `SIF_RERANK_ENABLED=1`. The off path never constructs a reranker model (zero-cost by construction).

When enabled:

- The pipeline over-fetches to `max(limit + offset, candidate_limit)` candidates before fusion, so the reranker sees a deeper pool than the page it returns.
- `candidate_limit` resolves through one shared clamp **5-50** (default 20; `SIF_RERANK_CANDIDATE_LIMIT`, or `-C` as in `sif search query -C 30`).
- A **normalized-score relative threshold** keeps candidates scoring at least `top_score * alpha` (`SIF_RERANK_RELATIVE_THRESHOLD`, default 0.5, `0 < alpha <= 1`), applied on descending-sorted raw scores before truncation — relative rather than absolute, so it needs no per-model score-distribution tuning.

`sif bench --rerank` measures the off and on states as two separate states (metrics + latency each) so the quality/latency trade-off is visible; a missing backend or model-load failure degrades to the off state with a warning.

## Commands and Reproduction

The full recipe against your own corpus:

```bash
# 1. Register the corpus and build the index (BM25/FTS)
sif collection add /path/to/my-corpus -n my-corpus
sif index update

# 2. Embed for the vector leg
sif index embed

# 3. Run the bench (no sweep: current SIF_ settings as the configuration)
sif bench tests/fixtures/bench/queries.json --json

# 4. Sweep the grid on the tuning split (rerank states optional)
sif bench tests/fixtures/bench/queries.json --sweep --json
sif bench tests/fixtures/bench/queries.json --sweep --rerank --json
```

Rerank latency probe on live search:

```bash
sif search query "kelpri protocol" --rerank -C 30
```

## Evidence Table

Deterministic evidence (concept embedder, committed pack, in-memory index — reproducible in CI):

| Measurement | Value |
|-------------|-------|
| Held-out queries | 20 (5 per category) |
| Shipped defaults | `rrf_k=60`, `bm25_weight=1.0`, `vector_weight=1.0` |
| Held-out nDCG@10 (defaults) | 0.8120 |
| Held-out Hit@10 (defaults) | 0.85 |
| — keyword / synonym / multilingual / rival nDCG@10 | 0.9735 / 0.2746 / 1.0000 / 1.0000 |
| Sweep winner (tuning) | `rrf_k=20`, `bm25_weight=1.0`, `vector_weight=0.5` — tuning nDCG@10 0.8680, tie group of 30/45, no single winner declared |
| Winner on held-out | nDCG@10 0.8186, delta **+0.0066 < 0.01** |
| Verdict | `unchanged` — the shipped defaults stay |

Manual real-model evidence (a separate manual step, not a CI gate — model, hardware, and date must be recorded when run; never fabricated):

| Model | Hardware | Date | Command | Held-out nDCG@10 | p50/p95 |
|-------|----------|------|---------|-------------------|---------|
| Qwen/Qwen3-Embedding-0.6B (modelscope, dim 1024) | macOS arm64 (Apple Silicon), single-thread CPU | 2026-11-12 | In-process `SearchEvaluator` + `SearchPipeline` over the deterministic corpus index rebuilt with the real model (same evaluation path as `test_bench_snapshot`; equivalent to `sif bench` on a corpus index) | **0.9233** (Hit@10 1.0) | 94.3 / 117.6 ms |

The real model corroborates the deterministic gate: held-out nDCG@10 **0.9233 ≥ 0.8120** (no regression on the shipped defaults), with a per-category split of keyword 1.0000 / synonym 0.6933 / multilingual 1.0000 / rival 1.0000 and a 90.9 ms cold start. The synonym category is the weakest under both embedders, matching the deterministic snapshot's ordering. Latency is CPU single-thread; GPU/MPS runs will be faster.

## Related Documentation

- [Search Algorithms](search-algorithms.md) — ranking mechanics and the reranker
- [Configuration](configuration.md) — every `SIF_` setting including the fusion and rerank knobs
- [CLI Reference](cli-reference.md) — the full `sif bench` flag surface
