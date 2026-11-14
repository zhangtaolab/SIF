# Phase 18: Quality Instrument (Personal Bench + rapidfuzz DYM) - Pattern Map

**Mapped:** 2026-11-14
**Files analyzed:** 16 (5 new, 11 modified)
**Analogs found:** 16 / 16 (all files have at least a role-match; new synthesis/bootstrap algorithms are new but sit inside established module shapes)

All analog paths below were verified git-tracked with `git ls-files -- <path>` (non-empty output). No gitignored mirror paths are cited.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/sif/cli/commands/eval.py` | controller (CLI command group) | request-response + batch | `src/sif/cli/commands/bench.py`; group shape from `src/sif/cli/commands/mcp.py` | exact (measurement CLI) |
| `src/sif/search/personal_bench.py` | service (pure domain module) | batch / transform | `src/sif/search/benchmark.py` | role-match |
| `src/sif/search/benchmark.py` (extend `SearchEvaluator.evaluate_per_query`) | service (domain evaluator) | batch | its own `report()` loop | exact |
| `src/sif/search/suggest.py` (swap `_close_matches`) | utility (search engine) | request-response | its own current `_close_matches` + RESEARCH Pattern 6 | exact |
| `src/sif/cli/main.py` (register `eval_group`) | config / wiring | request-response | its own import + `add_command` block | exact |
| `scripts/generate_cli_ref.py` (leaf-group fix) | utility (build script) | transform | its own `traverse_commands` / `_build_tree_lines` | exact |
| `tests/support/eval.py` | test support | file-I/O + DB batch | `tests/support/bench.py` (`build_bench_db`) | role-match |
| `tests/unit/search/test_personal_bench.py` | test | batch | `tests/unit/search/test_benchmark.py`, `tests/unit/search/test_bench_snapshot.py` | role-match |
| `tests/unit/cli/test_eval.py` | test | request-response | `tests/unit/cli/test_bench.py` | exact |
| `tests/unit/search/test_suggest.py` (update) | test | request-response | its own `TestDidYouMean` / `TestCoreBudget` | exact |
| `tests/test_docs.py` (add `"eval": []`) | test | transform | its own `_SUBCOMMANDS` map | exact |
| `pyproject.toml` (add rapidfuzz) | config | — | its own `dependencies` list | exact |
| `uv.lock` (regenerated) | config (generated) | — | itself (`uv lock`) | exact |
| `docs/cli-reference.md` (regenerated) | docs (generated) | — | itself (`make docs-generate`) | exact |
| `docs/benchmarking.md` (personal-bench narrative) | docs | — | itself | exact |
| `docs/architecture.md` (DYM narrative, SuggestionEngine table) | docs | — | itself | exact |

## Pattern Assignments

### `src/sif/cli/commands/eval.py` (controller, request-response + batch)

**Primary analog:** `src/sif/cli/commands/bench.py`
**Group-shape analog:** `src/sif/cli/commands/mcp.py` (`invoke_without_command`)

**Module header + console split** (`bench.py:1-45`) — copy this shape; stdout stays pipe-clean for `--json`, warnings go to a stderr Console:

```python
"""Benchmark commands."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, replace
from pathlib import Path

import click
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from sif.cli.error_handling import open_initialized_database
from sif.config.settings import Settings, get_settings
from sif.database.database import Database
from sif.embedding.manager import EmbeddingManager
...
from sif.utils.logging import get_logger


logger = get_logger(__name__)
console = Console()
# D-07 stderr contract (search.py precedent): soft-fail warnings must never
# pollute stdout, which stays clean for --json piping (`sif bench --json | jq`).
console_err = Console(stderr=True)
```

**Group with default action** (`mcp.py:34-47`) — the only existing `invoke_without_command` group. `eval` adds options on the group (RESEARCH lines 521-547); mirror the `ctx.invoked_subcommand is None` gate:

```python
@click.group("mcp", invoke_without_command=True)
@click.pass_context
def mcp_group(ctx: click.Context) -> None:
    """MCP server commands."""
    if ctx.invoked_subcommand is not None:
        return
    try:
        transport = get_settings().mcp_transport
    except ValidationError:
        transport = "stdio"
    if transport == "http":
        ctx.invoke(mcp_http_cmd)
    else:
        ctx.invoke(mcp_stdio_cmd)
```

For `eval`: when `ctx.invoked_subcommand is None`, require `--personal` via `raise click.UsageError("--personal is required (or pass a subcommand)")`, otherwise run the personal runner (RESEARCH Pattern 7). Options declared on the group: `--personal`, `--compare PATH`, `--no-save`, `--bm25-only`, `-n/--limit`, `-c/--collection` (multiple), `--all`, `--json` (`bench.py:559-588` shows the option/type style; `bench.py:566-573` shows `click.Path`/`IntRange`/`click.Choice`).

**Index-missing divergence (D-11 vs bench):** `bench` prints a notice and returns 0 (`bench.py:622-624`). `sif eval --personal` must fail loudly — `raise click.ClickException("No index found. Run 'sif index update' first.")`.

**Collection resolution** (`bench.py:124-145`) — reuse verbatim:

```python
def _resolve_collection_ids(
    db: Database,
    collection: tuple[str, ...],
    search_all: bool,
) -> list[str] | None:
    """None = unfiltered (--all); otherwise explicit -c names, falling back to
    every enabled collection."""
    with db.connection:
        repo = CollectionRepository(db.connection)
        if collection:
            ids: list[str] = []
            for name in collection:
                coll = repo.get_by_name(name)
                if coll:
                    ids.append(coll.id)
            return ids
        if not search_all:
            return [c.id for c in repo.list_enabled()]
        return None
```

**SearchOptions build** (`bench.py:148-168`) — copy the fusion-knob sourcing from settings:

```python
def _build_options(limit, candidate_limit, settings, collection_ids) -> SearchOptions:
    return SearchOptions(
        limit=limit,
        candidate_limit=candidate_limit,
        include_content=False,
        include_highlights=False,
        collection_ids=collection_ids,
        rrf_k=settings.rrf_k,
        bm25_weight=settings.bm25_weight,
        vector_weight=settings.vector_weight,
    )
```

**Embedder loading + memoization** (`bench.py:67-121`) — `CachedEmbedder` wraps the model so each distinct query text embeds once; reuse it. **Divergence for D-11:** `_load_embedder` soft-fails to BM25; `sif eval` must instead raise a remedy-bearing `ClickException` when the embed extra is unavailable, unless `--bm25-only` was passed. Remedy wording precedent:

- `src/sif/cli/commands/mcp.py:66-67`: `raise click.ClickException("Install with: pip install docsif[mcp]") from None`
- `src/sif/cli/commands/search.py:959-962`: `'Install with: pip install "docsif[embed]"'`

**Pipeline construction inside one connection scope** (`bench.py:224-235`) — build the pipeline once per run, never per query:

```python
with harness.db.connection:
    pipeline = SearchPipeline(
        harness.db.connection,
        embedder=harness.embedder,
        embedding_dim=harness.embedding_dim,
    )
    return evaluator.report(lambda query: pipeline.search(query, options), clock=time.perf_counter)
```

The eval run does **not** need latency (RESEARCH Open Question 8): one search per query, no `clock`.

**JSON + table rendering** (`bench.py:403-475`) — JSON strictly via `click.echo(json.dumps(payload, indent=2))`, never Rich:

```python
def _render_report(report, on_report, fixture_name, output_json) -> None:
    states = _rerank_states(report, on_report)
    if output_json:
        payload = report.to_dict()
        if states:
            payload["states"] = states
        click.echo(json.dumps(payload, indent=2))
        return
    console.print(_report_table(report, on_report, states, fixture_name))
```

Table style (`bench.py:435-465`): `Table(title=...)`, `table.add_column("Metric", style="cyan")`, `table.add_column("Value", style="green", justify="right")`, four-decimal metric rows. For per-leg × per-language × length-bucket rows, use one table with grouping rows and print suppressed group names explicitly (D-08).

**Untrusted-input / failure boundary** (`bench.py:627-685`) — the exact catch discipline to reuse for saved-run JSON:

```python
try:
    with open(fixture, encoding="utf-8") as f:
        fixture_data = json.load(f)
except (OSError, ValueError) as e:
    raise click.ClickException(f"Benchmark failed: {e}") from e

try:
    settings = get_settings()
except ValidationError as e:
    raise click.ClickException(str(e)) from e
...
with open_initialized_database(index_path, Database) as db:
    ...
    try:
        ...
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"Benchmark failed: {e}") from e
```

`open_initialized_database` (`src/sif/cli/error_handling.py:59-66`) owns DB-open/schema-init translation; the command body stays outside its catch-all (D-04).

**Rich markup safety** (`suggest.py:52-56`) — truncate then escape every vocab/path/query-derived cell:

```python
def _cell(text: str) -> str:
    """Truncate then escape one vocab/user-derived cell (T-15-06)."""
    if len(text) > _CELL_MAX_LEN:
        text = text[: _CELL_MAX_LEN - 3] + "..."
    return escape(text)
```

---

### `src/sif/search/personal_bench.py` (service, batch / transform)

**Primary analog:** `src/sif/search/benchmark.py`

The module is a pure domain module: one function per stage, no Click/Rich imports. Copy the structural conventions:

**Constants + helpers at module top** (`benchmark.py:18-33`, `36-38`):

```python
CATEGORIES: tuple[str, ...] = ("keyword", "synonym", "multilingual", "rival")
SPLITS: tuple[str, ...] = ("tuning", "heldout")
DEFAULT_K = 10
EPSILON = 0.01


def _mean(values: Sequence[float]) -> float:
    """Arithmetic mean; empty input yields 0.0 (house style)."""
    return sum(values) / len(values) if values else 0.0
```

Personal bench constants: legs (`title`, `body`, `replay`), language buckets (`en`, `zh`, `mixed`), length buckets (`short`/`medium`/`long`), `OVERLAP_BUDGET = 0.60`, `MIN_QUERIES = 50`, `MAX_QUERIES = 500`, `HELDOUT_MIN = 25`, `SUPPRESS_BELOW = 10`, `BOOTSTRAP_RESAMPLES = 10_000`, `RUN_SCHEMA_VERSION = 1`.

**Dataclass + ordered `to_dict`** (`benchmark.py:226-266`) — the saved-run record and report objects should be frozen-ish dataclasses with a deterministic `to_dict` that emits keys in a fixed order:

```python
@dataclass
class BenchReport:
    ndcg_at_10: float
    hit_at_10: float
    num_queries: int
    categories: dict[str, CategoryMetrics]
    ...
    def to_dict(self) -> dict[str, Any]:
        """Serialize with categories in CATEGORIES order and legacy keys merged."""
        categories: dict[str, Any] = {}
        for category in CATEGORIES:
            metrics = self.categories.get(category)
            if metrics is None:
                continue
            categories[category] = {
                "ndcg_at_10": metrics.ndcg_at_10,
                "hit_at_10": metrics.hit_at_10,
                "count": metrics.count,
            }
        data: dict[str, Any] = {...}
        data.update(self.legacy_metrics)
        return data
```

**Bootstrap CI primitive** — reuse `benchmark.percentile` exactly (`benchmark.py:104-112`, p in 0-100, linear interpolation), and mirror the rounded-delta arithmetic of `warrants_default_change` (`benchmark.py:394-407`):

```python
def warrants_default_change(baseline_ndcg: float, candidate_ndcg: float, delta: float = EPSILON) -> bool:
    return round(candidate_ndcg - baseline_ndcg, 6) >= delta
```

The gate rule (D-07): winner only if `(ci_low > 0 or ci_high < 0)` **and** `round(mean_delta, 6) >= 0.01`. Seed `random.Random(0)`; no SciPy (RESEARCH Pattern 4, lines 297-309).

**Legacy fixture construction** — build exactly the schema the evaluator already parses (`benchmark.py:480-484`):

```python
# Legacy items: relevance maps docid -> grade 1; no category or split.
grades = {str(docid): 1 for docid in item["relevant_docids"]}
self.query_items.append(QueryItem(query=str(item["query"]), grades=grades))
```

So the synthesizer emits `{"relevance_key": "docid", "queries": [{"query": q, "relevant_docids": [target_doc_id]}]}` (D-04) and must not use `category`/`split`/`relevance` keys — `_parse_graded_item` rejects anything outside `CATEGORIES` (`benchmark.py:486-498`).

**Deterministic hashing precedent** — `hashlib.sha256` over normalized text, never `hash()`:
- `src/sif/embedding/cache.py:96`: `return hashlib.sha256(content.encode("utf-8")).hexdigest()`
- `src/sif/core/models.py:150`: `self.checksum = hashlib.sha256(self.content.encode()).hexdigest()`

Use `unicodedata.normalize("NFC", ...)` + casefold + whitespace collapse before hashing/splitting (RESEARCH Pattern 2, lines 272-280).

**Untrusted JSON validation precedent** — `src/sif/utils/daemon.py:127-152` (`read_pid_file`) is the house defensive-parse shape: catch `OSError`/decode errors, require `dict`, type-check every field, return `None` on ANY defect. For saved runs, fail with `ClickException` instead of returning `None`, and add:
- `version` equality check (`RUN_SCHEMA_VERSION`),
- record-count cap (reject > 10,000),
- reject non-finite floats (`math.isfinite`),
- never open a path read from the file (treat as opaque comparison key).

**Corpus fingerprint** (A11): sha256 over sorted `f"{path}\0{checksum}\0{file_size}"` lines, truncated hex; exclude mtime.

---

### `src/sif/search/benchmark.py` (extend: `evaluate_per_query`)

**Analog:** its own `report()` (`benchmark.py:575-657`)

Add a per-query surface that runs the same one-search-per-query loop and returns `(query, retrieved_keys, grades, ndcg_at_10, hit_at_10)` records; `report()` may consume it, but `BenchReport.to_dict()` keys must stay byte-identical (A3). The per-query loop to lift:

```python
for item, results in zip(self.query_items, results_by_query, strict=True):
    retrieved = self._grades_for(item, results)
    ideal = list(item.grades.values())
    binary = [1 if grade > 0 else 0 for grade in retrieved]
    total_relevant = sum(1 for grade in item.grades.values() if grade > 0)
    query_ndcg = ndcg_at_k(retrieved, ideal, k)
    query_hit = hit_at_k(retrieved, k)
    ...
    if item.category in category_values:
        category_ndcg, category_hit = category_values[item.category]
        category_ndcg.append(query_ndcg)
        category_hit.append(query_hit)
```

Reuse `_grades_for` (`benchmark.py:521-525`), `ndcg_at_k` (`86-96`), `hit_at_k` (`99-101`) — do not reimplement.

---

### `src/sif/search/suggest.py` (change: `_close_matches`)

**Analog:** its own current `_close_matches` (`suggest.py:250-269`) and `_ratio` helper (`272-274`), replaced per RESEARCH Pattern 6.

Current body to replace:

```python
def _close_matches(self, token: str, n: int = 3) -> list[str]:
    first = ord(token[0])
    bucket = [term for term in self._terms if abs(ord(term[0]) - first) <= 1]
    matches = difflib.get_close_matches(token, bucket, n=n, cutoff=0.75)
    if len(matches) > 1:
        matches.sort(key=lambda term: (-_ratio(term, token), term))
    return matches
```

New shape (D-14/D-15/D-16):

```python
from rapidfuzz import fuzz, process

_DYM_CUTOFF = 75.0  # internal constant (D-16); measured on the bench vocab

def _close_matches(self, token: str, n: int = 3) -> list[str]:
    if not token or not self._terms:
        return []
    matches = process.extract(
        token,
        self._terms,
        scorer=fuzz.ratio,
        limit=n,
        score_cutoff=_DYM_CUTOFF,
    )
    # process.extract is best-first; equal scores keep choice-index order,
    # and self._terms is sorted, so ties are lexical asc (D-15). The explicit
    # sort keeps the df tie-break visible and stable.
    matches.sort(key=lambda m: (-m[1], m[0], -self._df.get(m[0], 0)))
    return [term for term, _score, _index in matches]
```

Delete `_ratio` and the `difflib` import. Always pass `scorer=fuzz.ratio` (default is `WRatio`). Keep `_dym_slots` (`168-188`) unchanged — it calls `_close_matches(token, n)` and treats an empty list as "no suggestion".

**Contracts that must not change** (`suggest.py:124-166`): `_probe` stays fail-soft on `sqlite3.OperationalError`; `_hits` and `_retrievable` keep probing through `BM25Searcher(self.db)._build_fts_query(...)`; prefix completions (`86-106`) and `_rank_history` (`277-303`) untouched. The 100 ms end-to-end `sif suggest` budget remains the external guard.

---

### `src/sif/cli/main.py` (register `eval_group`)

**Analog:** its own registration block (`main.py:90-114`)

```python
# Import and register subcommands after cli group to avoid circular imports
from sif.cli.commands.bench import bench_cmd  # noqa: E402
from sif.cli.commands.collection import collection_group  # noqa: E402
from sif.cli.commands.context import context_group  # noqa: E402
from sif.cli.commands.eval import eval_group  # noqa: E402
...
cli.add_command(bench_cmd)
cli.add_command(eval_group)
...
```

Keep imports alphabetic and `# noqa: E402` on every line; add the `add_command` near `bench_cmd`.

---

### `scripts/generate_cli_ref.py` (leaf-group fix)

**Analog:** its own `traverse_commands` (`generate_cli_ref.py:90-102`) and `GROUP_ORDER` (`167-179`).

Current code drops a `click.Group` with no subcommands (the `sif eval --personal` case):

```python
def traverse_commands(cmd: click.Command, path: str = "") -> list[tuple[str, click.Command]]:
    """Recursively traverse the Click command tree."""
    results: list[tuple[str, click.Command]] = []
    if isinstance(cmd, click.Group):
        for name, subcmd in cmd.commands.items():
            new_path = f"{path} {name}".strip()
            results.extend(traverse_commands(subcmd, new_path))
    else:
        results.append((path, cmd))
    return results
```

Fix (RESEARCH Pattern 7):

```python
if isinstance(cmd, click.Group) and cmd.commands:
    for name, subcmd in cmd.commands.items():
        new_path = f"{path} {name}".strip()
        results.extend(traverse_commands(subcmd, new_path))
else:
    results.append((path, cmd))
```

Then add `("eval", "Other Commands")` to `GROUP_ORDER` (or a new "Evaluation Commands" section) and run `make docs-generate`. `_build_tree_lines` (`105-118`) already renders a leaf group's first help line in the command tree, so no tree change is needed.

**CI gate:** `.github/workflows/docs.yml` runs `python scripts/generate_cli_ref.py` then `git diff --exit-code docs/cli-reference.md docs/configuration.md`; the same workflow runs `pytest tests/test_docs.py`.

---

### `tests/support/eval.py` (test support)

**Analog:** `tests/support/bench.py` (`build_bench_db`, `ConceptEmbedder`)

Reuse/import `ConceptEmbedder` and `EMBEDDING_DIM` from `tests.support.bench` rather than duplicating. The DB-builder shape to mirror (`tests/support/bench.py:98-167`):

```python
def build_bench_db(corpus_root: Path, embedder: ConceptEmbedder, embedding_dim: int = EMBEDDING_DIM) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        conn.enable_load_extension(True)
        import sqlite_vec
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
    except Exception:
        conn.close()
        pytest.skip("sqlite-vec not available")

    root = corpus_root.resolve()
    SchemaManager(conn, embedding_dim=embedding_dim).create_all()
    now = "2026-11-08T00:00:00+00:00"
    conn.execute(
        "INSERT INTO collections (id, name, path, include_by_default, created_at, updated_at)"
        " VALUES ('bench', 'bench', ?, 1, ?, ?)",
        (str(root), now, now),
    )
    ...
    conn.execute(
        "INSERT INTO documents (id, collection_id, path, filename, title, content,"
        " checksum, mtime, created_at, updated_at) VALUES (?, 'bench', ?, ?, ?, ?, ?, 1.0, ?, ?)",
        (doc_id, str(path), path.name, title, text,
         hashlib.sha256(text.encode("utf-8")).hexdigest(), now, now),
    )
```

For the personal bench helper, add:
- seed **>= 50 documents** (D-11 threshold) with distinct titles and bodies,
- seed `query_log` rows via `QueryLogRepository.add(entry, keep=500)` (test-suggest pattern, `tests/unit/search/test_suggest.py:354-371`),
- accept a `cache_dir` (or return a Settings instance) so saved runs land in `tmp_path` — `Settings(cache_dir=tmp_path)` then `Settings.get_cache_dir()` returns it (`src/sif/config/settings.py:402-411`).

The compact in-memory builder in `tests/unit/search/test_suggest.py:27-62` (`_fixture_db`) is the smaller template when sqlite-vec is not needed.

---

### `tests/unit/search/test_personal_bench.py` (new test)

**Analog:** `tests/unit/search/test_benchmark.py::TestSearchEvaluator` (`test_benchmark.py:78-157`) and `tests/unit/search/test_bench_snapshot.py` (deterministic concept-embedder integration)

- Build `SearchResult` objects directly for metric tests, exactly as `test_benchmark.py:87-110` does (no DB needed).
- For end-to-end synthesis/evaluate tests, use `build_bench_db`/the new `tests/support/eval.py` helper with `ConceptEmbedder` (A12) — no model download.
- Class-per-concern structure matching the validation map: `TestKnownItemFixture`, `TestReplay`, `TestOverlapBudget`, `TestGroups`, `TestSplit`, `TestNoiseGate`, `TestSavedRun`.
- Determinism assertions: same corpus → same query set/split; run twice and compare exact lists. No wall-clock assertions.

---

### `tests/unit/cli/test_eval.py` (new test)

**Analog:** `tests/unit/cli/test_bench.py`

Copy the mock harness shape:

```python
def _settings_mock(**overrides: object) -> MagicMock:
    fields: dict[str, object] = {
        "rrf_k": 60,
        "bm25_weight": 1.0,
        "vector_weight": 1.0,
        ...
    }
    fields.update(overrides)
    return MagicMock(**fields)
```

and the patch seams (`test_bench.py:153-159`):

```python
patch("sif.cli.commands.bench.Database", return_value=mock_db),
patch("sif.cli.commands.bench.get_settings", return_value=_settings_mock()),
patch("sif.cli.commands.bench.SearchPipeline", return_value=mock_pipeline),
```

For `eval.py` the seams become `sif.cli.commands.eval.Database`, `...eval.SearchPipeline`, `...eval.get_settings`, and `...eval.EmbeddingManager`. Use `CliRunner().invoke(eval_group, [...], obj={"index_path": ...})` (`test_bench.py:121-130`). `_SpyPipeline` (`test_bench.py:88-107`) records queries — useful to prove `--compare` re-runs the **saved** query set (Pitfall 2). For the group dispatch itself, follow `tests/unit/cli/test_mcp.py:38-51`: construct `click.Context(mcp_mod.mcp_group)`, set `ctx.invoked_subcommand`, monkeypatch `ctx.invoke`.

---

### `tests/unit/search/test_suggest.py` (update)

**Analog:** its own `TestDidYouMean` (`141-262`) and `TestCoreBudget` (`289-324`).

`TestCoreBudget` currently spies difflib and asserts bucket size — replace with a full-vocabulary spy:

```python
calls: list[int] = []
real_extract = process.extract

def spy(...):  # patch sif.search.suggest.process.extract
    calls.append(len(choices))
    return real_extract(...)
```

Assertions become: the extract choice list is the **full** vocabulary (`max(calls) == vocab_size`), first-letter typos are recallable, and elapsed is generous-bounded (< 1.0 s, with the RESEARCH 1.7 ms p50 recorded in SUMMARY). Do **not** assert exact rapidfuzz scores across versions (3.14.5 on py3.10 vs 3.14.6 on 3.11+); assert membership/order, `pytest.approx` only for displayed scores.

Add: `xuantum` → `quantum` (first-letter typo; ~85.7 Indel) and keep the exact-75.0 boundary test `resturant` → `restaur` (`141-225`, `test_short_stem_prefix_does_not_suppress_correction`).

---

### `tests/test_docs.py` (add eval subcommand entry)

**Analog:** its own `_SUBCOMMANDS` (`tests/test_docs.py:243-263`):

```python
_SUBCOMMANDS: ClassVar[dict[str, list[str]]] = {
    "collection": [...],
    "context": ["add", "remove", "list", "prune", "rm"],
    "index": ["update", "embed", "status"],
    "search": ["search", "query", "vsearch"],
    "get": ["get", "multi-get"],
    "mcp": ["stdio", "http", "daemon"],
    "config": ["show"],
}
```

Add `"eval": []` so a generated docs example validates as `sif eval --help` (RESEARCH Pattern 7 test seam).

---

### `pyproject.toml` (add rapidfuzz)

**Analog:** its own `dependencies` list (`pyproject.toml:29-41`):

```toml
dependencies = [
    "click>=8.0.0",
    "rich>=13.0.0",
    ...
    "numpy>=1.24.0",
]
```

Add `"rapidfuzz>=3.14.5,<4"` (D-13). The lower bound must be 3.14.5 because 3.14.6 dropped Python 3.10. Then `uv lock` and commit `uv.lock` (CI uses `uv sync --frozen`).

### `uv.lock`, `docs/cli-reference.md`

Generated artifacts — do not hand-edit. `uv lock`; `make docs-generate` (`Makefile:73-76`: `python scripts/generate_cli_ref.py` + `python scripts/generate_config_ref.py`).

### `docs/benchmarking.md` and `docs/architecture.md`

Narrative updates only:
- `docs/benchmarking.md` — add `sif eval --personal` section (three legs, overlap budget, splits, bootstrap gate, saved-run comparison), following the existing `sif bench` prose/table conventions (`docs/benchmarking.md:109-175`).
- `docs/architecture.md:672-705` — the SuggestionEngine paragraph and component table row must describe rapidfuzz full-vocabulary scoring instead of difflib bucketing; add the personal-bench module to the component table.

## Shared Patterns

### DB open / error boundary
**Source:** `src/sif/cli/error_handling.py:59-66`
**Apply to:** `src/sif/cli/commands/eval.py` (every DB access)

```python
@contextmanager
def open_initialized_database(
    index_path: str | Path, database_cls: type[Database]
) -> Generator[Database, None, None]:
    """Open and initialize a CLI database, translating only foreseeable failures."""
    db = open_initialized_database_unmanaged(index_path, database_cls)
    with db:
        yield db
```

Do not add a command-body catch-all; only known failure classes translate to `ClickException` (D-04).

### Settings + ValidationError translation
**Source:** `src/sif/cli/commands/bench.py:638-641`, `src/sif/cli/main.py:39-42`
**Apply to:** `eval.py` (settings reads, cache dir resolution)

```python
try:
    settings = get_settings()
except ValidationError as e:
    raise click.ClickException(str(e)) from e
```

### stderr warnings / stdout purity
**Source:** `src/sif/cli/commands/bench.py:41-45`, `src/sif/cli/commands/suggest.py:33-34`
**Apply to:** all warnings in `eval.py` (low history, model-identity mismatch, suppressed groups)

`console = Console()` for stdout output only; `console_err = Console(stderr=True)` for every warning. `--json` goes through `click.echo`, never Rich.

### Determinism
**Source:** `src/sif/embedding/cache.py:96`, `src/sif/core/models.py:150`, `src/sif/search/benchmark.py:361-391`
**Apply to:** `personal_bench.py` sampling, splitting, fingerprint, bootstrap; tests

Use `hashlib.sha256` (never `hash()`), NFC normalization, explicit sort keys, `random.Random(seed)`, and sorted-key serialization so the same corpus yields the same query set/split on every machine (Pitfall 9).

### Test determinism
**Source:** `tests/support/bench.py:40-95`, `tests/unit/cli/test_bench.py:17-35`, `tests/unit/search/test_suggest.py:65-75`
**Apply to:** all new/updated tests

`ConceptEmbedder` for hermetic embeddings, `tmp_path` for files/cache dirs, `Settings(_env_file=None)` for env isolation, monkeypatched module seams, `pytest.skip` when sqlite-vec is unavailable, no wall-clock races.

### Rich markup escaping for user/vocab-derived text
**Source:** `src/sif/cli/commands/suggest.py:52-56`
**Apply to:** every eval table cell containing a query string, document path, or vocab term

Truncate first, then `rich.markup.escape` (T-15-06; security table "Rich markup injection").

## No Analog Found

Files/behaviors with no close existing match — planner should use RESEARCH.md patterns directly:

| Capability | Role | Data Flow | Reason |
|------------|------|-----------|--------|
| Known-item query synthesis (title/body legs, overlap budget, dedupe) | domain function in `personal_bench.py` | transform | No synthesis code exists; `benchmark.py` only consumes hand-authored fixtures. Use RESEARCH Pattern 1 + Open Questions 2/9/10. |
| Seeded paired percentile bootstrap | domain function in `personal_bench.py` | batch | `benchmark.percentile` exists but no resampling code anywhere; use RESEARCH Pattern 4. |
| Saved-run JSON schema/version validation | domain function in `personal_bench.py` | file-I/O | Only `daemon.read_pid_file` (defensive parse) and fixture `json.load` exist; use RESEARCH Pattern 5 + Security Domain caps. |
| query_log replay stability (Jaccard@10 / top-1 vs baseline) | domain function in `personal_bench.py` | batch | `QueryLogRepository.history()` is the source; no stability-comparison code exists. Use RESEARCH D-02/A6. |

## Metadata

**Analog search scope:** `src/sif/cli/`, `src/sif/search/`, `src/sif/config/`, `src/sif/database/`, `src/sif/utils/`, `tests/unit/search/`, `tests/unit/cli/`, `tests/support/`, `tests/test_docs.py`, `scripts/`, `docs/`, `pyproject.toml`
**Files scanned/read:** 20+ (bench.py, suggest.py CLI, main.py, mcp.py, search.py excerpt, error_handling.py, benchmark.py, suggest.py, settings.py excerpt, repositories.py excerpt, daemon.py excerpt, generate_cli_ref.py, Makefile, tests/support/bench.py, test_bench.py, test_benchmark.py, test_bench_snapshot.py excerpt, test_suggest.py, test_mcp.py excerpt, test_docs.py, docs/benchmarking.md excerpt, docs/architecture.md grep, pyproject.toml)
**Pattern extraction date:** 2026-11-14
