# Phase 16: Bench Expansion + Reranker Tuning - Pattern Map

**Mapped:** 2026-11-08
**Files analyzed:** 21 (7 source, 1 script, 10 test, 3 docs)
**Analogs found:** 20 / 21 (the committed fixture pack is genuinely new)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/sif/search/benchmark.py` | service (search core) | transform + batch | itself (`:14-39`, `:42-109`) + `src/sif/search/rrf.py` | exact (extension) |
| `src/sif/cli/commands/bench.py` | controller (CLI command) | batch / request-response | itself (`:25-148`) + `src/sif/cli/commands/search.py` (`:830-853`) | exact (extension) |
| `src/sif/search/rerank.py` | service | transform (score + filter) | itself `_sort_and_build_results` (`:24-53`) | exact |
| `src/sif/search/hybrid.py` | service (pipeline orchestrator) | request-response | itself (`:76-81`, `:239-246`) | exact |
| `src/sif/config/settings.py` | config | — | itself (`:147-164`, `:189-210`, `:215-226`) | exact |
| `src/sif/cli/commands/search.py` | controller (CLI command) | request-response | itself (`:745-751`, `:830-853`, `:892-905`) | exact |
| `scripts/generate_config_ref.py` | config generator | transform | itself (`SECTIONS:150-203`, `:321-357`, `:359-403`) | exact |
| `tests/support/bench.py` *(new)* | test utility / fixture builder | batch, direct file→DB | `tests/unit/search/test_hybrid.py:620-773` | role-match |
| `tests/fixtures/bench/**` *(new)* | fixture (data) | batch | none — see "No Analog Found" | none |
| `tests/unit/search/test_benchmark_metrics.py` *(new)* | test (unit) | — | `tests/unit/search/test_benchmark.py` | exact |
| `tests/unit/search/test_sweep.py` *(new)* | test (unit) | — | `tests/unit/search/test_benchmark.py` + golden style `test_hybrid.py:639-794` | role-match |
| `tests/unit/search/test_bench_fixture.py` *(new)* | test (integration-lite) | — | `tests/unit/search/test_hybrid.py:724-773` | role-match |
| `tests/unit/search/test_bench_snapshot.py` *(new)* | test (snapshot) | — | `tests/unit/search/test_hybrid.py:620-794` | role-match |
| `tests/unit/cli/test_bench.py` | test (CLI) | — | itself | exact |
| `tests/unit/config/test_settings.py` | test (unit) | — | itself (`:38-49`) | exact |
| `tests/unit/inference/test_reranker.py` | test (unit) | — | itself (`:113-160`) | exact |
| `tests/unit/search/test_rerank.py` | test (unit) | — | itself | exact |
| `tests/unit/cli/test_search.py` | test (CLI) | — | itself (`:150-163` settings mock) | exact |
| `docs/benchmarking.md` *(new)* | docs (narrative) | — | `docs/search-algorithms.md` | role-match |
| `tests/test_docs.py` | test (docs validation) | — | itself (`DOCS_FILES:21-31`) | exact |
| `docs/search-algorithms.md` / `docs/api-reference.md` | docs (narrative) | — | itself | exact |

> Tracked-source gate: every analog path above was verified with `git ls-files -- <path>` (all tracked). `tests/fixtures/` and `tests/support/` do not exist yet and are not gitignored.

---

## Pattern Assignments

### `src/sif/search/benchmark.py` (service, transform + batch)

**Analog:** itself — extend, do not rewrite (D-13). Pure-helper style also matches `src/sif/search/rrf.py`.

**Imports / module header** (`benchmark.py:1-11`):
```python
from __future__ import annotations

from collections.abc import Callable, Sequence

from sif.core.models import SearchResult
from sif.utils.logging import get_logger


logger = get_logger(__name__)
```
New imports go stdlib-first (ruff isort): `dataclasses`, `math`, `time` (for the injectable clock), then `collections.abc`, then `sif.*`. Two blank lines after imports.

**Pure metric-function pattern** (`benchmark.py:14-39`) — copy this shape for `dcg_at_k` / `ndcg_at_k` / `hit_at_k` / `percentile`:
```python
def precision_at_k(relevance: Sequence[int], k: int) -> float:
    """Precision@K: relevant items in top-K / K."""
    if k == 0:
        return 0.0
    return sum(relevance[:k]) / k


def recall_at_k(relevance: Sequence[int], total_relevant: int, k: int) -> float:
    """Recall@K: relevant items retrieved / total relevant."""
    if total_relevant == 0:
        return 0.0
    return sum(relevance[:k]) / total_relevant


def mean_reciprocal_rank(all_relevance: list[Sequence[int]]) -> float:
    """Mean Reciprocal Rank across queries."""
    rr_scores = [reciprocal_rank(r) for r in all_relevance]
    return sum(rr_scores) / len(rr_scores) if rr_scores else 0.0
```
Guard-before-divide and "empty list → 0.0" are the house style; preserve them. Pitfall 8: `precision_at_k`/`recall_at_k` must switch to binary `grade > 0` (legacy 0/1 fixtures are unchanged by that switch).

**Fixture-validation pattern** (`benchmark.py:55-63`) — extend rather than replace:
```python
def _validate_fixture(self) -> None:
    """Validate fixture format."""
    if "queries" not in self.fixture:
        raise ValueError("Fixture must contain 'queries' key")
    for i, item in enumerate(self.fixture["queries"]):
        if "query" not in item:
            raise ValueError(f"Query {i} missing 'query' field")
        if "relevant_docids" not in item:
            raise ValueError(f"Query {i} missing 'relevant_docids' field")
```
Named-error style: `raise ValueError(f"Query {i} missing ...")`. New graded-schema validation (split ∈ {tuning, heldout}, category ∈ four names, grades ∈ 0-3) uses the same indexed-message shape; legacy `relevant_docids` keys remain valid (grade 1).

**Evaluation-accumulation pattern** (`benchmark.py:79-109`):
```python
k_values = k_values or [1, 5, 10]
metrics: dict[str, list[float]] = {}
all_relevance: list[Sequence[int]] = []

for query_item in self.fixture["queries"]:
    query = query_item["query"]
    relevant_ids = set(query_item["relevant_docids"])
    results = search_fn(query)
    result_ids = [r.document_id for r in results]
    relevance = [1 if rid in relevant_ids else 0 for rid in result_ids]
    all_relevance.append(relevance)
    for k in k_values:
        metrics.setdefault(f"precision@{k}", []).append(precision_at_k(relevance, k))
        ...
# Average across queries
averaged: dict[str, float] = {}
for key, values in metrics.items():
    averaged[key] = sum(values) / len(values) if values else 0.0
averaged["mrr"] = mean_reciprocal_rank(all_relevance)
averaged["num_queries"] = float(len(self.fixture["queries"]))
```
Keep `evaluate()`'s flat `dict[str, float]` return backward-compatible; layer a `BenchReport` dataclass on top.

**Dataclass style** (`src/sif/core/models.py:233-251`): plain `@dataclass` with `field(default_factory=...)`; `ConfigResult`/`BenchReport` should use the same style, `@dataclass(frozen=True)` for pure sweep results, and a `to_dict()` for JSON output mirroring `SearchResult.to_dict` (`models.py:253-268`).

**Path-keyed relevance helper** — no existing analog; research Pattern 2 gives the body. Keep it a module-level pure function in `benchmark.py` so the CLI never computes keys itself.

---

### `src/sif/cli/commands/bench.py` (controller, batch)

**Analog:** itself for wiring/rendering; `src/sif/cli/commands/search.py` for settings resolution.

**Click decorator + signature style** (`bench.py:25-47`):
```python
@click.command("bench")
@click.argument("fixture", type=click.Path(exists=True, path_type=Path))
@click.option("-n", "--limit", default=10, help="Number of results per query")
@click.option("-C", "--candidate-limit", default=20, help="Reranker candidate pool size")
...
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def bench_cmd(  # noqa: C901, PLR0913, PLR0915
    ctx: click.Context,
    ...
) -> None:
```
New flags follow the same shape: `--sweep`/`--rerank` as `is_flag=True`, snake_case param names. **Do not add more `noqa` codes** — extract `_build_options()`, `_measure_state()`, `_render_report()`, `_run_sweep()` (Pitfall 9; the project splits helpers rather than suppressing).

**Settings resolution + user-facing validation errors** (`search.py:830-853`):
```python
from pydantic import ValidationError  # noqa: PLC0415

from sif.config.settings import get_settings  # noqa: PLC0415

try:
    settings = get_settings()
except ValidationError as e:
    raise click.ClickException(str(e)) from e

# Flag defaults are None (never the literal) or precedence dies.
options = SearchOptions(
    limit=limit,
    ...
    candidate_limit=candidate_limit,
    rrf_k=rrf_k if rrf_k is not None else settings.rrf_k,
    bm25_weight=bm25_weight if bm25_weight is not None else settings.bm25_weight,
    vector_weight=(vector_weight if vector_weight is not None else settings.vector_weight),
)
```
D-09/M-02: bench's no-sweep run must build its config from `settings.rrf_k/bm25_weight/vector_weight` with exactly this precedence shape. `-C/--candidate-limit` default must become `None` so `settings.rerank_candidate_limit` can apply (research assumption A3).

**Current search-function shape to hoist** (`bench.py:91-122`):
```python
def search_fn(query: str):
    from sif.core.models import SearchOptions  # noqa: PLC0415

    options = SearchOptions(limit=limit, candidate_limit=candidate_limit, ...)
    ...
    with db.connection:
        pipeline = SearchPipeline(
            db.connection,
            embedder=manager._model if manager else None,  # noqa: SLF001
            embedding_dim=embedding_dim,
        )
        return pipeline.search(query, options)
```
The `SearchPipeline` construction is inside the timed loop today. Phase 16 must hoist it (one pipeline per state), wrap the embedder in the caching wrapper for `--sweep`, and pass `SearchOptions` variants per config.

**Error handling** (`bench.py:126-129`) — keep the single wrapping point:
```python
try:
    metrics = evaluator.evaluate(search_fn)
except Exception as e:
    raise click.ClickException(f"Benchmark failed: {e}") from e
```

**Output pattern** (`bench.py:132-148`):
```python
if output_json:
    click.echo(json.dumps(metrics, indent=2))
else:
    table = Table(title=f"Benchmark Results: {fixture.name}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green", justify="right")
    for key in sorted(metrics.keys()):
        ...
    console.print(table)
```
Use `click.echo(json.dumps(...))` (not Rich) for `--json` — `Rich` word-wrapping would corrupt the JSON (see `test_bench_json_parses_at_narrow_width`). Table/JSON must both carry the per-category breakdown (D-06).

---

### `src/sif/search/rerank.py` (service, transform)

**Analog:** itself — the shared post-sort helper is the one place cap/α belongs (D-13, research "Don't Hand-Roll").

**Shared helper to extend** (`rerank.py:24-53`):
```python
def _sort_and_build_results(
    results: list[SearchResult],
    scores: list[float],
    top_k: int,
) -> list[SearchResult]:
    """Sort results by score descending and rebuild SearchResult objects."""
    scored = list(zip(results, scores, strict=True))
    scored.sort(key=lambda x: x[1], reverse=True)

    reranked: list[SearchResult] = []
    for rank, (result, score) in enumerate(scored[:top_k], 1):
        new_scores = dict(result.scores) if result.scores else {}
        new_scores["reranker_score"] = score
        reranked.append(SearchResult(..., score=score, ..., rank=rank, scores=new_scores, ...))
    return reranked
```
Add `relative_threshold: float = 0.0`, filter **after** the descending sort and before `[:top_k]`; keep `top_k` semantics unchanged so every existing test (`top_k=3`, `top_k=1`) still passes.

**Constructor defaults pattern** (`rerank.py:93-107`, `:172-186`, `:260-279`):
```python
def __init__(
    self,
    model_path: str | None = None,
    model_name: str = "",
    n_ctx: int = 512,
    n_threads: int | None = None,
    batch_size: int = 32,
) -> None:
    ...
    self._batch_size = batch_size
    self._model: Llama | None = None
```
Add `relative_threshold: float = 0.0` to each constructor with the same keyword/default style; store as `self._relative_threshold` and forward it at the `_sort_and_build_results(...)` call (`:166`, `:249`, `:396`). Default `0.0` means no filtering for direct construction/tests.

**Factory wiring** (`rerank.py:399-429`):
```python
def create_reranker(
    settings: Settings,
) -> LlamaCppReranker | CrossEncoderReranker | Qwen3Reranker:
    """Factory: create a reranker based on settings."""
    model_type = getattr(settings, "reranker_model_type", "gguf")
    model_name = getattr(settings, "reranker_model_name", "")
    ...
    if "qwen3-reranker" in model_name.lower() or "qwen3_reranker" in model_name.lower():
        return Qwen3Reranker(...)
```
Pass `relative_threshold=settings.rerank_relative_threshold` from here so production defaults to 0.5 while tests can construct with 0.0. Keep `getattr(settings, ...)` defensiveness for MagicMock settings (Pitfall 10).

---

### `src/sif/search/hybrid.py` (pipeline orchestrator, request-response)

**Analog:** itself.

**Current rerank gate** (`hybrid.py:239-246`):
```python
# Apply candidate limit before reranking
if self.reranker is not None and len(results) > 0:
    candidates = results[: options.candidate_limit]
    try:
        reranked = self.reranker.rerank(parsed_query, candidates, top_k=options.limit)
        results = reranked
    except Exception as e:
        raise RuntimeError(f"Reranking failed: {e}") from e
```
Over-fetch must happen **upstream of** this block: the fused list is currently at most `options.limit` because `HybridSearcher.search` fuses at `options.limit` (`hybrid.py:76-81`) and the cross-query fusion does the same (`:237`). Pattern: when a reranker exists, compute `fetch_limit = max(options.limit, options.candidate_limit)` (research notes `max(limit + offset, candidate_limit)` if offset must stay meaningful), build `fetch_options = replace(options, limit=fetch_limit)` via `dataclasses.replace`, pass it to `self.hybrid.search(q, fetch_options)` (`:226`) and to `self.hybrid.rrf.fuse(all_results, fetch_options.limit, k=options.rrf_k)` (`:237`), then slice `results[: options.candidate_limit]`. Non-rerank paths must stay byte-identical (the SC1 golden in `test_hybrid.py:639-794` pins this).

**Fusion call site** (`hybrid.py:76-81`) — leave alone; the fetch limit rides in via `SearchOptions.limit`:
```python
fused_results = self.rrf.fuse(
    [bm25_results, vector_results],
    options.limit,
    weights=[options.bm25_weight, options.vector_weight],
    k=options.rrf_k,
)
```
Confirmed by data flow: BM25 `LIMIT ?` (`bm25.py:83-85`), vector trims to `options.limit` (`vector.py:125-131`), so `replace(options, limit=...)` is sufficient — no signature change.

---

### `src/sif/config/settings.py` (config)

**Analog:** itself — Phase 15's fusion block is the template for a new phase-owned settings group.

**Existing reranker block to extend** (`settings.py:147-164`):
```python
# Reranker settings
reranker_model_name: str = Field(
    default="Qwen/Qwen3-Reranker-0.6B",
    description="Reranker model name",
)
reranker_model_path: Path | None = Field(
    default=None,
    description="Path to local reranker model file",
)
reranker_model_type: str = Field(
    default="sentence_transformers",
    description="Reranker model type (gguf, sentence_transformers)",
)
reranker_batch_size: int = Field(
    default=32,
    ge=1,
    description="Batch size for reranker inference",
)
```

**Range-validation style** (`settings.py:183-188`) — use `Field(ge=..., le=...)` so Pydantic names the field:
```python
default_limit: int = Field(
    default=10,
    ge=1,
    le=100,
    description="Default search result limit",
)
```
New fields: `rerank_candidate_limit: int = Field(default=20, ge=5, le=50, ...)`, `rerank_relative_threshold: float = Field(default=0.5, gt=0, le=1, ...)`, `rerank_enabled: bool = Field(default=False, ...)`.

**Boolean-setting style** (`settings.py:215-220`):
```python
query_history_enabled: bool = Field(
    default=True,
    description="Log executed searches ...; 0 disables both the write and the read side globally",
)
```
Use the same pattern for `rerank_enabled`, but default `False` (D-12). Also note Phase 15's comment convention above a setting group (`:189-192`) — document *why* the cap/range exists and the D-decision it implements.

---

### `src/sif/cli/commands/search.py` (controller, request-response)

**Analog:** itself.

**Option decorator style** (`search.py:745-751`, `:782`):
```python
@click.option(
    "-C",
    "--candidate-limit",
    default=20,
    type=click.IntRange(1, 200),
    help="Reranker candidate pool size",
)
...
@click.option("-q", "--quiet", is_flag=True, help="Suppress non-error output")
```
Add `--rerank` as an `is_flag=True` option with a short help line naming `SIF_RERANK_ENABLED` (same "default: SIF_X or Y" phrasing used at `:757-770`).

**Reranker construction to gate** (`search.py:892-905`):
```python
reranker = None
if settings.reranker_model_name or settings.reranker_model_path:
    try:
        reranker = create_reranker(settings)
    except ImportError:
        if not quiet:
            console.print(
                "[yellow]Reranker not available. "
                "Install with: pip install -e '.[embed]'[/yellow]",
            )
    # Defense in depth (REVIEW WR-09): a factory ValueError for an
    # unknown model_type must not escape as a raw traceback.
    except ValueError as e:
        raise click.ClickException(str(e)) from e
```
Change the guard to `rerank_requested = rerank or settings.rerank_enabled` **before** `create_reranker` (Pitfall 2: zero-cost means never constructing). Preserve the ImportError soft-fail and the ValueError→ClickException mapping. Options build (`:842-853`) resolves `candidate_limit` the same "flag > setting > default" way.

---

### `scripts/generate_config_ref.py` (config generator, transform)

**Analog:** itself. Generator-owned: `docs/configuration.md` must never be hand-edited; run `make docs-generate` and commit the diff.

**SECTIONS registration** (`generate_config_ref.py:160-175`):
```python
(
    "Reranker Settings",
    [
        "reranker_model_name",
        "reranker_model_path",
        "reranker_model_type",
        "reranker_batch_size",
    ],
),
```
Append `rerank_enabled`, `rerank_candidate_limit`, `rerank_relative_threshold` to this list (order determines doc row order; put `rerank_enabled` first).

**Env-example block** (`generate_config_ref.py:359-403`):
```python
lines.append("# Reranker")
lines.append("SIF_RERANKER_MODEL_NAME=Qwen/Qwen3-Reranker-0.6B")
lines.append(f"SIF_RERANKER_MODEL_TYPE={reranker_type_default}")
lines.append("SIF_RERANKER_BATCH_SIZE=32")
```
Add the three `SIF_RERANK_*` lines here.

**Validation-rules table** (`generate_config_ref.py:321-357`): this table is partly derived from live validators and partly handwritten ("format and range rules stay handwritten"). Add rows for `rerank_candidate_limit` (5 to 50) and `rerank_relative_threshold` (greater than 0, at most 1) alongside the existing `default_limit` row:
```python
lines.append(
    "| `default_limit` | 1 to 100 | `ensure this value is less than or equal to 100` |"
)
```

**Gate:** `make docs-generate` then `git diff --exit-code docs/cli-reference.md docs/configuration.md` must be clean (`.github/workflows/docs.yml:38-42`).

---

### `tests/support/bench.py` (test utility, deterministic DB builder)

**Analog:** `tests/unit/search/test_hybrid.py:620-773` — the only deterministic schema+FTS+vec0 fixture in the repo.

**Deterministic embedder pattern** (`test_hybrid.py:620-636`):
```python
class _FakeEmbedder:
    """Deterministic embedder keyed on exact text (SC1 golden fixture)."""

    DOC_EMBEDDINGS: ClassVar[dict[str, list[float]]] = {
        "d1": [0.20, 0.90],
        ...
    }
    QUERY = "apple"
    QUERY_EMBEDDING: ClassVar[list[float]] = [1.0, 0.0]

    def embed(self, text: str) -> list[float]:
        if text == self.QUERY:
            return self.QUERY_EMBEDDING
        return self.DOC_EMBEDDINGS.get(text, [0.0, 1.0])
```

**Direct DB builder pattern** (`test_hybrid.py:724-773`) — copy the whole shape:
```python
conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row
try:
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
except Exception:
    conn.close()
    pytest.skip("sqlite-vec not available")

SchemaManager(conn, embedding_dim=2).create_all()
conn.execute(
    "INSERT INTO collections (id, name, path, created_at, updated_at)"
    " VALUES ('c1', 'notes', '/notes', ?, ?)",
    (now, now),
)
...
searcher = VectorSearcher(conn, embedding_dim=2)
searcher.add_embeddings_batch(
    [(f"e-{did}", did, f"chunk-{did}", vec) for did, vec in _FakeEmbedder.DOC_EMBEDDINGS.items()]
)
```
`build_bench_db()` should generalize this: fixed doc IDs, `embedding_dim` computed from the concept embedder, collection path = the fixture `corpus_root` so `SearchResult.path` stays under it (path-keyed relevance). Add `tests/support/__init__.py` so `from tests.support.bench import build_bench_db` imports cleanly (`tests/__init__.py` exists).

**`ConceptEmbedder`** = the hash-of-known-terms→fixed-vector idea from `_FakeEmbedder`, but corpus-scale; it must implement the `Embedder` protocol (`embed`, plus `dimension`/`embed_batch` if declared — check `src/sif/core/models.py` protocol before writing).

**Note:** `tests/conftest.py:17` inserts `src/` on `sys.path`; no new path plumbing is needed.

---

### `tests/fixtures/bench/**` (fixture data, batch)

**No existing analog** — see "No Analog Found". Recommended shape (research Structure section):

```
tests/fixtures/bench/
├── corpus/{keyword,synonym,multilingual,rival}/*.md
├── queries.json              # version, corpus_root, relevance_key, queries[]
├── heldout_defaults.json     # committed held-out evidence snapshot
└── README.md
```
Nearest conventions to imitate: inline fixture dicts `{"queries": [{"query": ..., "relevant_docids": [...]}]}` in `tests/unit/cli/test_bench.py:26-32` and `tests/unit/search/test_benchmark.py:80-84`; on-disk markdown creation in `tests/conftest.py:550-605` (`docs_test_db` writes `.md` files under `tmp_path`). `pytest` will not collect a non-`test_` module under `tests/support/`.

---

### `tests/unit/search/test_benchmark_metrics.py` (unit test)

**Analog:** `tests/unit/search/test_benchmark.py` — one class per function, one assertion per behavior.

**Test-style excerpt** (`test_benchmark.py:15-33`):
```python
class TestPrecisionAtK:
    def test_perfect_precision(self) -> None:
        relevance = [1, 1, 1, 1, 1]
        assert precision_at_k(relevance, 3) == 1.0

    def test_k_zero(self) -> None:
        assert precision_at_k([1, 1], 0) == 0.0
```
Use `pytest.approx` for the verified nDCG values (0.9926195041747018, 0.6806060567602009) and percentile values (p50 of 1..10 == 5.5, p95 == 9.55). Add binary-graded precision/recall cases and the injected-clock latency test (see below). Avoid asserting absolute wall-clock values.

**Latency-clock precedent** (`tests/unit/search/test_suggest.py:312-321`) — only a generous upper bound is ever asserted:
```python
start = time.perf_counter()
completions = engine.prefix_completions("m0", 5)
engine.did_you_mean("mzzzzz9 xzzzzz9")
elapsed = time.perf_counter() - start
...
assert elapsed < 1.0
```
For `measure()` unit tests, inject a fake clock instead (research Pattern "warmed per-query latency with an injectable clock") and assert structural properties (`p50 <= p95`, sample count, warm-up not counted).

---

### `tests/unit/search/test_sweep.py` (unit test)

**Analog:** `tests/unit/search/test_benchmark.py` (fabricated values) plus the golden-assertion style of `tests/unit/search/test_hybrid.py:639-794`.

**Snapshot/golden assertion style** (`test_hybrid.py:786-794`):
```python
def test_default_options_match_prechange_snapshot(self) -> None:
    """SC1: plain SearchOptions() reproduces the captured pre-change output."""
    assert self._search(SearchOptions()) == self.SNAPSHOT
```
Test the pure `rank_sweep()` with fabricated `ConfigResult`s: 0.500 vs 0.505 → tie (no winner); 0.500 vs 0.520 → winner; 0.500 vs 0.510 → **not** a tie (strict `< 0.01`); grid has exactly 45 configs and contains the `(60, 1.0, 1.0)` baseline. Add the tuning-only guard (held-out split must never be consulted) and the embedder-called-once spy.

---

### `tests/unit/search/test_bench_fixture.py` / `test_bench_snapshot.py` (integration-lite)

**Analog:** `tests/unit/search/test_hybrid.py:620-794` — build a real in-memory DB with the deterministic embedder, then assert.

- Fixture-contract tests: ≥50 queries, ≥20 held-out, all four categories, grades 0-3, every relevance key resolves to a corpus file, every query returns ≥1 result on the deterministic index.
- Snapshot tests: `DEFAULTS_SNAPSHOT` dict asserted equal to a committed `heldout_defaults.json`; a "default-lock" test that fails when a default changes without the snapshot update. Model the `_build_db()` / `_search()` split at `test_hybrid.py:724-784`.

---

### `tests/unit/cli/test_bench.py` (CLI test)

**Analog:** itself.

**Mock/patch style** (`test_bench.py:44-57`):
```python
with (
    patch("sif.cli.commands.bench.Database", return_value=mock_db),
    patch(
        "sif.cli.commands.bench.EmbeddingManager.from_settings",
        return_value=mock_manager,
    ),
    patch("sif.cli.commands.bench.SearchPipeline", return_value=mock_pipeline),
    patch("sif.cli.commands.bench.get_settings", return_value=MagicMock()),
):
    result = runner.invoke(
        bench_cmd,
        [str(fixture_path)],
        obj={"index_path": MagicMock(exists=lambda: True)},
    )
```
Patch targets are the `sif.cli.commands.bench.<name>` module attributes. `--json` tests must `json.loads(result.output.strip())`. New tests: `--sweep`, `--rerank` (states), category breakdown keys, and baseline delta row.

---

### `tests/unit/config/test_settings.py` (unit test)

**Analog:** itself (`:38-49`):
```python
def test_reranker_model_type_validation_rejects_invalid_values() -> None:
    """WR-09: an unsupported reranker backend fails at settings-validation time."""
    with pytest.raises(ValueError, match="Invalid reranker_model_type"):
        Settings(reranker_model_type="cross-encoder")
```
Add cap boundary tests (`5`, `50` accepted; `4`, `51` raise `ValidationError`) and α boundary tests (`0` rejected, `1` accepted, `1.1` rejected). Use `Settings(_env_file=None)` where env hermeticity matters (see `:13-16`).

---

### `tests/unit/inference/test_reranker.py` and `tests/unit/search/test_rerank.py` (unit tests)

**Analog:** themselves. Reranker tests patch the optional backend module rather than loading a model (`test_reranker.py:113-138`):
```python
fake_llama_cpp = MagicMock()
with patch.dict("sys.modules", {"llama_cpp": fake_llama_cpp}):
    mock_llama = fake_llama_cpp.Llama
    mock_model = MagicMock()
    mock_model.embed.return_value = [0.1, 0.2, 0.3]
    mock_llama.return_value = mock_model
    results = reranker.rerank("query", sample_search_results, top_k=10)
```
`sample_search_results` is a `conftest.py` fixture (`tests/conftest.py:398-412`). Add α tests: with normalized top1 = s, a candidate at `s*0.5 - ε` is dropped while `s*0.5` is kept; top1 always survives; `relative_threshold=0.0` reproduces today's output exactly.

---

### `tests/unit/cli/test_search.py` (CLI test)

**Analog:** itself. **Real churn warning (Pitfall 10)** — the settings mocks enumerate fields explicitly (`test_search.py:150-163`):
```python
patch(
    "sif.config.settings.get_settings",
    return_value=MagicMock(
        model_name="all-MiniLM-L6-v2",
        reranker_model_name=None,
        reranker_model_path=None,
        model_dump=lambda: {"model_name": "all-MiniLM-L6-v2"},
    ),
),
```
Every mock feeding `query_cmd` needs `rerank_enabled=False`, `rerank_candidate_limit=20`, `rerank_relative_threshold=0.5`, or the new reads return `MagicMock` and leak into `SearchOptions`. Follow the existing explicit-kwarg mock style rather than `MagicMock()` wide-open where the fields are consumed. Add tests: `--rerank` off constructs no reranker (`create_reranker` not called) and results identical; `--rerank` on constructs one.

---

### `docs/benchmarking.md` (new) + `tests/test_docs.py` (docs validation)

**Analog:** `docs/search-algorithms.md` for narrative structure (H1 title, one-paragraph overview, ASCII pipeline diagram, `##` subsections with formulas in fenced blocks). Add the path to `DOCS_FILES` (`tests/test_docs.py:21-31`):
```python
DOCS_FILES = [
    Path("README.md"),
    Path("docs/index.md"),
    ...
    Path("docs/search-algorithms.md"),
    Path("docs/architecture.md"),
    Path("docs/models.md"),
]
```
This opts the new doc into JSON-validity, Python-syntax, shell-command, and phantom-field checks. Note `SKIP_COMMAND_PATTERNS` already contains `"bench "` (`tests/test_docs.py:44`), so `sif bench ...` examples are not executed but must still be valid command paths if written as `sif ...`. Update `docs/search-algorithms.md` (rerank threshold/over-fetch) and `docs/api-reference.md` where signatures change.

---

## Shared Patterns

### User-facing errors
**Source:** `src/sif/cli/commands/bench.py:126-129`, `src/sif/cli/commands/search.py:834-837`
**Apply to:** every CLI/bench failure path
```python
except ValidationError as e:
    raise click.ClickException(str(e)) from e
...
except Exception as e:
    raise click.ClickException(f"Benchmark failed: {e}") from e
```

### Settings → options precedence
**Source:** `src/sif/cli/commands/search.py:839-853`
**Apply to:** `bench.py` options build and `search.py` rerank flag
```python
rrf_k=rrf_k if rrf_k is not None else settings.rrf_k,
```
Flags default to `None`, never a literal. Rerank: `--rerank` OR `settings.rerank_enabled`; `candidate_limit` flag default `None` → `settings.rerank_candidate_limit`.

### Module logger
**Source:** `src/sif/search/benchmark.py:11`, every `sif` module
**Apply to:** all new source modules
```python
logger = get_logger(__name__)
```

### Dataclasses for result/report structs
**Source:** `src/sif/core/models.py:233-294`
**Apply to:** `ConfigResult`, `BenchReport`, `QueryItem`
Plain `@dataclass`; `field(default_factory=...)` for mutable defaults; `@dataclass(frozen=True)` for sweep rows; a `to_dict()` for JSON.

### Deterministic-test discipline
**Source:** `tests/unit/search/test_hybrid.py:639-794`, `tests/unit/search/test_suggest.py:312-321`
**Apply to:** every new test
Fixed IDs and vectors, real schema+FTS+vec0 in memory, `pytest.skip` when sqlite-vec is absent, no wall-clock assertions beyond a generous bound, inject a clock for latency logic.

### Generator-owned docs
**Source:** `scripts/generate_config_ref.py:150-203`, `:321-357`, `:359-403`
**Apply to:** any `Settings` field change
Never hand-edit `docs/cli-reference.md` or `docs/configuration.md`; register fields in `SECTIONS`, env example, and (for range rules) the validation table, then run `make docs-generate` and check the diff.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `tests/fixtures/bench/**` | fixture (data) | batch | Repo has no `tests/fixtures/` directory and no committed corpus; all fixtures today are inline dicts or `tmp_path` writers. Planner must use RESEARCH.md "Recommended Project Structure" + Pattern 2 (path-keyed relevance). |

Partial gaps (analog exists, behavior new):
- Latency measurement with an injected clock — no production precedent; use RESEARCH "warmed per-query latency" example.
- nDCG/percentile formulas — no in-repo precedent; pin to RESEARCH worked values and textbook formula.
- Sweep tie-group ranking — no in-repo precedent; pure function per RESEARCH Pattern 3.

---

## Project Conventions the Planner Must Honor

- `ruff check src tests` + `ruff format --check src tests` after every plan; line length **100**; mccabe **10**; no new `noqa` to duck complexity — split helpers.
- `ty check src/sif`: fully annotated functions (params + return), `list[str] | None` unions, Python 3.10+.
- **Zero new runtime dependencies.** Stdlib + existing `numpy` only; `pyproject.toml` dependency sections untouched.
- Test invocation in agent shells: `env -u FORCE_COLOR NO_COLOR=1 pytest ...` (`FORCE_COLOR=0` still fails).
- Import order: stdlib → third-party → `sif`; two blank lines after imports; ruff isort `combine-as-imports = true`.
- `docs/cli-reference.md` and `docs/configuration.md` are generator-owned — never hand-edit; CI diffs them.
- CLI user errors via `click.ClickException(str(e))`; DB transactions via `Database.transaction()`.
- Fixture JSON validation: named `ValueError` messages; resolve `corpus_root` and constrain it to the fixture directory (Security V5/path traversal); never interpolate fixture text into SQL (query strings already flow through `_sanitize_term` in `bm25.py:21-33`).
- Complexity budget for `bench_cmd`: it already carries `# noqa: C901, PLR0913, PLR0915` — extract `_build_options`, `_measure_state`, `_render_report`, `_run_sweep` before adding `--sweep`/`--rerank`.

## Metadata

**Analog search scope:** `src/sif/{search,cli/config,database,core,embedding}`, `scripts/`, `tests/{unit,integration}`, `docs/`, `tests/test_docs.py`, `pyproject.toml`, `mkdocs.yml`
**Files scanned:** 25+ (all analogs read with line anchors; all verified tracked via `git ls-files`)
**Pattern extraction date:** 2026-11-08
