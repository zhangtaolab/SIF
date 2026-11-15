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
dcg_at_k(sorted(ideal, reverse=True), 10)   # 8.892789260714373
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

## Personal Bench (`sif eval --personal`)

The committed fixture pack remains the defaults gate. The personal bench is a third instrument for measuring search quality on your own indexed corpus with no manual relevance labels.

### The three query legs

| Leg | Source | Semantics |
|-----|--------|-----------|
| `title` | each sampled document's title/H1 | Exact-term known-item: the query IS the title, so this leg is exempt from the paraphrase budget |
| `body` | one later prose sentence from the document | Paraphrased known-item: rejected when token Jaccard against the target's title plus first 200 characters exceeds `0.60` |
| `replay` | normalized `query_log` history | Stability, not quality: no labels, no splits, never gates defaults; only CLI searches are logged, so it is a CLI-biased sample |

Known-item labels are binary: the target document is grade 1 and every other document grade 0, using the same legacy fixture schema as `sif bench`. NDCG@10 is therefore a rank-sensitive known-item metric, not a graded-relevance score. Empty, duplicate, and overlap rejections are counted per leg so a query set never shrinks silently.

### Deterministic sampling and the tuning/held-out split

A personal run requires at least 50 indexed documents in scope and at least 50 accepted queries; below either floor it exits non-zero with the counts and the `sif index update` remedy. Documents are ordered by `sha256(path + NUL + checksum)`, then path, then id, so the same index yields the same query set on every machine; mtime is not part of the identity. Queries split 50/50 by `sha256(normalized query)[0] < 128` (NFC + casefold + whitespace collapse first). The held-out floor is 25, so the sampler widens from the initial 50 documents toward `min(corpus, 250)` until both the accepted-query and held-out floors hold; a widened sample is a superset of the previous prefix.

### Saved runs: location, schema, privacy

Every run auto-saves one JSON file under the SIF cache directory unless `--no-save`:

```
<cache_dir>/eval/eval-<corpus-fingerprint[:12]>-<UTC timestamp>.json
```

`<cache_dir>` is the platform cache directory (for example `~/Library/Caches/sif/eval/` on macOS or `~/.cache/sif/eval/` on Linux; `SIF_CACHE_DIR` overrides it). The run is versioned (`version: 1`) and holds query text, target/retrieved paths and document ids, leg/language/length/split, grade, retrieval depth (`top_k`), corpus fingerprint and document counts, model identity, and replay paths. The document-derived text in the file is the query text itself: the title-leg query is the document title, and the body-leg query is a short normalized excerpt of the sampled document's later prose (at most 10 tokens, markup- and punctuation-stripped), stored so `--compare` can replay it. The file never contains full document bodies, snippets, or embeddings; it lives only on the local machine and is never uploaded. With a remote-capable embedding backend (`openai`/`modelscope`), document titles, body-sentence excerpts, and replay query history (when query history is enabled) are sent to that provider for embedding; the run discloses this on stderr and in the report notes, and `--bm25-only` keeps the run local. The `--json` payload carries `run_path`; the path itself is announced on stderr so stdout stays pipe-clean.

### Comparing against a saved run (`--compare`)

`sif eval --personal --compare <saved-run.json>` re-evaluates exactly the saved run's query set, in saved order, against the current engine. It performs no synthesis, no overlap filtering, and no split reassignment: the two arms answer the same queries over the same corpus by construction.

- **Corpus guard.** The current corpus fingerprint is recomputed from all in-scope document metadata and must equal the saved fingerprint. A mismatch refuses the comparison, naming both values; a silently compared different corpus would manufacture a delta.
- **Target identity.** Each saved target resolves by document id first, with an exact-path fallback only when exactly one current document has that path. Zero or multiple path matches refuse rather than guess (the same file may be indexed in two collections).
- **Id-keyed grading for both arms.** The baseline arm recomputes nDCG@10/Hit@10 from the saved `retrieved_doc_ids` against the saved `target_doc_id`; the current arm grades `evaluate_per_query` keys against the resolved current id. Repeated ids are deduped by first occurrence, so a path duplicated across collections cannot turn one arm's retrieval into a hit for the other and baseline nDCG@10 never exceeds 1.0.
- **Saved depth wins.** Both arms evaluate at the saved `top_k`; a different `-n` is reported on stderr and ignored. A saved-vs-current retrieval-mode difference warns on stderr and is recorded in the comparison JSON, as is a model-identity mismatch; only the corpus fingerprint refuses a comparison.
- **Auto-save.** The comparison auto-saves a new run built from the current arm (same query texts, count, and order as the compared run) unless `--no-save`.

### The paired-bootstrap noise gate

For every query the comparison computes the paired delta `round(current - baseline, 6)`. The mean delta is bootstrapped with `random.Random(0)` and exactly 10,000 resamples; the 95% interval uses the house `percentile` (linear interpolation). A winner is declared only when all four hold:

1. at least 10 paired queries (the same `SUPPRESS_BELOW` floor used for group suppression),
2. the 95% CI excludes zero,
3. `round(mean_delta, 6) >= 0.01`, and
4. the absolute mean delta is strictly above the displayed `1/N` noise floor.

Exactly 0.01 clears the tie rule when the floor is below it (N > 100); 0.0099 does not; a CI that includes zero never declares a winner. The floor is a real veto: at N=25 it is 0.04, so a 0.01 mean delta cannot win, and at N≈71 it is ~0.014. A gate below either floor is still reported with its N and `sufficient`/`winner` flags — `sufficient` is false below 10 paired queries — but can never set `warrants_default_change`.

Only the **held-out** summary gate can warrant a defaults change. Tuning and per-group gates are diagnostic and labeled so. Groups are leg × language × length-bucket combinations; groups with fewer than 10 queries are omitted and named on stderr, never rendered as a zero row.

### Replay stability

Replay compares each saved replay query's top-k path list with the current top-k for the same query: mean Jaccard@10 (order-insensitive) plus top-1 match (order-sensitive). With no saved replay snapshot, or no current results, the report says `available: false` with the reason rather than inventing a number. Replay never enters nDCG/Hit, splits, groups, or the gate.

### Comparability rules

- A fresh run is **not** comparable across an overlap-budget, sampling, or split change: the saved query set is the pairing contract, and a changed synthesizer produces a different set. Start a new baseline instead.
- Within the same corpus fingerprint, `--compare` is the only honest way to read a delta; the fingerprint refusal is deliberate.
- Every saved run lives under the local cache directory, never in the repository.

## CORR-02 Per-Document Dedup

CORR-02 changed the default ranking contract of the vector and hybrid paths: `VectorSearcher` now groups duplicate chunk rows by document **before** RRF fusion, keeps the best-distance chunk, and reports how many pre-dedup rows collapsed into the result as `chunk_matches`. `SearchResult` also carries `chunk_id` and `sequence` (the display form is `path#sequence`), and `--per-chunk` on `sif vsearch`/`sif query` (MCP `per_chunk` on `query`/`vec_search`) restores the ungrouped chunk rows. `sif search` and MCP `lex_search` stay document-level and expose no per-chunk flag.

This is a correctness contract change, not a tuning win: no default weight, `rrf_k`, or `top_k` moved. The change is recorded here rather than hidden, with before/after evidence below.

### B0 → B1 is the BM25 no-drift check

Both saved runs use `--bm25-only` on the same 150-document fixture corpus and scratch index (corpus fingerprint `8c006123784348d1`), with the same 100 auto-synthesized known-item queries at `top_k=10`. The dedup change lives in the vector leg, which `--bm25-only` never constructs, so a zero delta here is the **expected** outcome and proves the CLI/MCP surface work introduced no ranking drift; it is not evidence that dedup changed ranking. B1 (`bench/b1.json`) is the post-dedup, pre-title saved run that the title work is measured against.

`--compare bench/b0.json`: overall n=100, nDCG@10 `0.948330165500004 → 0.948330165500004` (delta `0.0`, 95% CI `[0.0, 0.0]`), Hit@10 `1.0 → 1.0`, 100 unchanged, 0 helped, 0 hurt. The tuning split (n=51) and held-out split (n=49) are likewise unchanged at `0.9493432995098079` and `0.9472756790816368`. The two groups that clear the N ≥ 10 floor are unchanged: title/en/medium (n=39) `1.0 → 1.0` and body/en/long (n=46) `0.8876742728260958 → 0.8876742728260958`, both deltas `0.0` with CI `[0.0, 0.0]`. Three groups stay below the floor, so they are suppressed from the table and named on stderr rather than rendered as zero rows: title/en/short, title/mixed/long, body/mixed/long. `--compare bench/b1.json` (self-comparison) reports the same n=100 and mean delta `0.0`, confirming B1 is a stable saved baseline. Raw reports and the scratch database stay untracked.

### Where the dedup effect is recorded

The committed held-out snapshot (`tests/fixtures/bench/heldout_defaults.json`) was regenerated for CORR-02 and records the before and after numbers in its `rationale`. On this deterministic fixture corpus every document has exactly one chunk, so there are no duplicate chunk rows to collapse and the numbers are identical:

- defaults (`rrf_k=60`, `bm25_weight=1.0`, `vector_weight=1.0`), held-out: nDCG@10 `0.8120158986791898 → 0.8120158986791898`, Hit@10 `0.85 → 0.85`; per-category nDCG@10/Hit@10 (the snapshot's actual dimension): keyword `0.9734983536077081/1.0 → same`, synonym `0.2745652411090509/0.4 → same`, multilingual `1.0/1.0 → same`, rival `1.0/1.0 → same`.
- sweep candidate (`rrf_k=20`, `bm25_weight=1.0`, `vector_weight=0.5`): tuning nDCG@10 `0.8186413102772627 → 0.8186413102772627`, Hit@10 `0.85 → 0.85`; the verdict stays `unchanged` with held-out delta `0.00662541159807295`.

The regenerated SC1 hybrid golden (`tests/unit/search/test_hybrid.py::TestHybridSC1PipelineGolden`) records the other half of the evidence: its old→new `bm25_score`/`rrf_score` values are byte-identical (d3 `0.9999989753435158` / `0.03252247488101534`; d1 `0.9999990673325406` / `0.031754032258064516`), proving the vector/hybrid scoring math did not move while the result contract gained `chunk_id`/`sequence`/`chunk_matches`. The behavioral dedup evidence is the chunky-document regression in `tests/integration/test_search_correctness.py`: a six-chunk document can no longer starve a `limit=10` default page below ten distinct documents, and its six chunk rows are individually addressable under `--per-chunk`.

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

# 5. Personal bench on your own index (auto-saves under <cache_dir>/eval/)
sif eval --personal
sif eval --personal --json

# 6. Compare a later run against a saved baseline (both arms at its top_k)
sif eval --personal --compare <cache_dir>/eval/eval-<fingerprint>-<timestamp>.json
```

Use `--no-save` on a diagnostic run that should not become a comparison substrate, and `--bm25-only` when the embed extra is unavailable (the default hybrid path fails loudly with an install remedy). Hybrid is the default and also requires the scoped index to contain embeddings: if it has none, the run fails with the `sif index embed` remedy instead of silently reporting BM25 results as `hybrid`. Pass `--bm25-only` to measure the BM25 path explicitly.

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
