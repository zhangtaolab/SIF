# Phase 20: Metadata Filtering + Discovery - Pattern Map

**Mapped:** 2026-11-15
**Files analyzed:** 30 (7 new, 13 modified production/generated/docs, 10 extended tests)
**Analogs found:** 29 / 30 files (1 partial — see "No Direct Analog" below)

**The three patterns this phase must not reinvent**
1. **Placeholder/parameter building** — `bm25.py` / `vector.py` already build filter fragments with a `params` list appended in SQL order; the compiler emits fragments, never values.
2. **Transaction boundaries** — the caller owns the transaction (`Database.transaction()`, `with self._conn`); repositories never commit. The kv sync runs inside `DocumentRepository.create/update` on the caller's transaction; the backfill commits one short transaction per document.
3. **Detection-gated migrations** — `SchemaManager` gates every migration on `sqlite_master`/`PRAGMA` reads plus the `index_meta` kv table; fresh and already-migrated DBs pay zero cost. The backfill marker goes in `index_meta` (there is no `schema_meta` table), and the pass is resumable by construction.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/sif/core/filters.py` (new) | domain model + validator | transform (parse/validate AST) | `src/sif/mcp/protocol.py` + `src/sif/config/settings.py` | partial (pydantic conventions; no union analog) |
| `src/sif/search/filters.py` (new) | service (SQL compiler) | transform (predicate build) | `src/sif/search/bm25.py` | role-match |
| `src/sif/database/metadata_repository.py` (new) | repository | CRUD + batch aggregate | `src/sif/database/repositories.py` | exact |
| `src/sif/core/models.py` | model | request-response | itself (`SearchOptions`, `canonical_metadata_json`) | exact |
| `src/sif/search/bm25.py` | search leg (service) | request-response | itself (filter-fragment + outer WHERE) | exact |
| `src/sif/search/vector.py` | search leg (service) | batch/KNN loop | itself (escalation loop, post-KNN JOIN) | exact |
| `src/sif/search/hybrid.py` | orchestrator | request-response | itself (`replace()` fan-out, early returns) | exact |
| `src/sif/database/schema.py` | migration/DDL | batch | itself (`index_meta`, index gates, savepoint, `drop_all`) | exact |
| `src/sif/database/repositories.py` | repository | CRUD | itself (`DocumentRepository.create/update`) | exact |
| `src/sif/database/__init__.py` | package export | config | itself | exact |
| `src/sif/cli/commands/search.py` | controller | request-response | itself (option blocks, `ClickException`) | exact |
| `src/sif/cli/commands/collection.py` | controller | request-response | itself (`collection list`/`show`) | exact |
| `src/sif/mcp/protocol.py` | schema model | request-response | itself (`QueryInput`, `ToolsCallResult`) | exact |
| `src/sif/mcp/handlers.py` | adapter/controller | request-response | itself (`QueryToolHandler`) | exact |
| `src/sif/mcp/backend.py` | facade/service | request-response | itself (`hybrid_search`, `_run_in_db`) | exact |
| `tests/unit/core/test_filters.py` (new) | test | — | `tests/unit/config/test_settings.py` | role-match |
| `tests/unit/search/test_filters_sql.py` (new) | test | — | `tests/unit/search/test_collection_filter.py` | exact |
| `tests/unit/database/test_metadata_values.py` (new) | test | — | `tests/unit/database/test_repositories.py` | exact |
| `tests/integration/test_metadata_filtering.py` (new) | test | — | `tests/integration/test_search_correctness.py` | exact |
| `tests/support/bench.py` | test utility | batch fixture | itself (`build_bench_db`) | exact |
| `tests/unit/search/test_bm25.py` | test | — | itself | exact |
| `tests/unit/search/test_vector.py` | test | — | itself (`TestVectorFilteredRecall`) | exact |
| `tests/unit/search/test_hybrid.py` | test | — | itself | exact |
| `tests/unit/indexing/test_incremental.py` | test | — | itself (`TestMetadataFastPath`) | exact |
| `tests/unit/database/test_schema.py` | test | — | itself (`TestIndexMetaTable`) | exact |
| `tests/unit/cli/test_search.py` | test | — | itself | exact |
| `tests/unit/cli/test_collection.py` | test | — | itself | exact |
| `tests/unit/mcp/test_backend.py` | test | — | itself (schema-sync tests) | exact |
| `tests/unit/mcp/test_integration.py` | test | — | itself (exact tool-set assertions) | exact |
| `docs/cli-reference.md` | generated docs | — | `scripts/generate_cli_ref.py` | exact |

**Verify-only, do not modify** (recorded so the planner does not "fix" them):
- `src/sif/indexing/parser.py` — D-19: `qmd.metadata` resolution happens in the derived view over the canonicalized mapping, never in the parser or the checksum path.
- `src/sif/indexing/incremental.py` — both write paths (metadata fast path `incremental.py:437-446`, full body path `incremental.py:451-487`) and `added` (`incremental.py:485-486`) already funnel through `DocumentRepository`; the mtime-only convergence `incremental.py:422-427` touches metadata not at all. No structural change expected.
- `src/sif/search/__init__.py` / `src/sif/core/__init__.py` — new modules are imported directly; no public class changes (optional export only if the planner wants symmetry).

## Pattern Assignments

### `src/sif/core/filters.py` (new — domain model + validator, transform)

**Analog:** `src/sif/mcp/protocol.py` (pydantic v2 conventions) and `src/sif/config/settings.py` (validator/error style). There is **no existing discriminated union** in the repo; use RESEARCH.md Code Example 1 (`20-RESEARCH.md:668-747`) for the union itself and imitate the conventions below.

**Imports / model conventions** — `src/sif/mcp/protocol.py:10-16, 96-117, 170-174`:
```python
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from sif._version import __version__


class InitializeParams(BaseModel):
    protocolVersion: str = "2024-11-05"  # noqa: N815
    capabilities: dict[str, Any] = Field(default_factory=dict)
```
- camelCase wire names are written verbatim with a trailing `# noqa: N815` (`protocol.py:99,101,115,138,151,167,174`). The AST's `caseInsensitive` and the discovery remainders `totalKeys`/`remainingKeys`/`remainingValues` follow this exact convention.
- `model_validator(mode="after")` exists at `protocol.py:54-59`; `settings.py` uses `field_validator` (e.g. `settings.py:291,307`). Both are established.
- Model docstrings name the phase decision they implement (e.g. `protocol.py:246-248` "Pagination (CORR-03/D-05)…"). Every new decision-bearing field/class should carry a `D-xx` comment.

**Validation error style** — `src/sif/config/settings.py:307-322` raises `ValueError("Invalid model_type: …")` naming the field; tests assert the message with `pytest.raises(ValidationError, match="<field>")` (`tests/unit/config/test_settings.py:28-37, 83-90`). The AST validator must instead raise a project error naming the AST path (e.g. `filter.tags.gt: "gt" requires a numeric value`), so wrap `ValidationError` at the single entry point — do not leak pydantic `loc` tuples to CLI/MCP users.

**Budget pre-walk pattern** (research-verified; no analog): iterative dict walk before `model_validate` so over-budget errors name the budget instead of surfacing pydantic's `recursion_loop` (~900 depth). Structure `_check_budgets` per `20-RESEARCH.md:725-744`.

**Single shared entry point:** one `parse_filter(payload: Any) -> FilterNode` used by CLI, MCP inputs, and discovery; it owns budgets, `mtime` ISO parsing (D-12), and error formatting.

---

### `src/sif/search/filters.py` (new — SQL compiler, role-match)

**Analog:** `src/sif/search/bm25.py` — the `collection_filter` builder is the exact pattern: build a fragment string, append params in SQL order, interpolate the fragment into a fixed SQL template.

**Placeholder builder** — `src/sif/search/bm25.py:86-96`:
```python
params = [content_weight, title_weight, fts_query]
collection_filter = ""
if options.collection_ids:
    placeholders = ", ".join(["?"] * len(options.collection_ids))
    params.extend(options.collection_ids)
    collection_filter = f"AND d.collection_id IN ({placeholders})"

min_score_filter = ""
if options.min_score > 0:
    params.append(1.0 - 1.0 / options.min_score)
    min_score_filter = "AND m.score >= ?"
```
- The fragment is **never parameterized**; only values are. This compiler's contract is `tuple[str, list[Any]]`; callers append only when the returned SQL is non-empty, and params go in SQL order.
- Variable-length `IN` placeholder: `", ".join(["?"] * n)` (`bm25.py:89`, `vector.py:89`, and `repositories.py:637-641` for a batched DELETE). Reuse it; never f-string a value.
- Alias comes from the caller (`d` in both legs). The vector leg's fragment slots into the post-KNN JOIN WHERE (`vector.py:87-90, 118`).

**Two scopes** (research-measured): correlated `EXISTS` for search legs, `IN (SELECT document_id …)` for the pre-count/discovery. Shape per `20-RESEARCH.md:751-759`; per-operator SQL table at `20-RESEARCH.md:389-405`.

**Hard rules from research:**
- `prefix` on built-ins compiles to a half-open range, not `LIKE` (`20-RESEARCH.md:411-422`); `contains`/`suffix` use `instr()`/BLOB `substr()` so there is no wildcard escaping and no LIKE.
- Return `("", [])` only for `None`. A non-`None` filter always yields a predicate; an empty-match filter must compile to an always-false predicate, never to "no filter" (extends the sentinel contract at `bm25.py:70-71` / `vector.py:58-59`).
- `ne`/`nin` compile as presence-`EXISTS` + `NOT EXISTS`, never bare `NOT IN`.

---

### `src/sif/database/metadata_repository.py` (new — repository, exact)

**Analog:** `src/sif/database/repositories.py`. Standalone class wrapping the shared `sqlite3.Connection`; **does not inherit** the abstract interfaces in `src/sif/database/repository.py` (CLAUDE.md; those are only `create_autospec` mocks).

**Class shape** — `src/sif/database/repositories.py:646-669` (`IndexMetaRepository`, the marker repo the backfill calls):
```python
class IndexMetaRepository:
    """Repository for the key/value ``index_meta`` table (D-09 convention marker).
    ...
    """

    def __init__(self, db: sqlite3.Connection) -> None:
        """Initialize the index metadata repository."""
        self.db = db

    def get(self, key: str) -> str | None:
        """Get a metadata value; a missing key returns None."""
        cursor = self.db.execute("SELECT value FROM index_meta WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else None

    def set(self, key: str, value: str) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO index_meta (key, value) VALUES (?, ?)",
            (key, value),
        )
```
- `__init__`/method docstrings on every public method; a missing row returns `None`; mutations never commit.
- Write methods return `cursor.rowcount > 0` / `cursor.rowcount` (`repositories.py:98-101, 240-249, 474-477`).
- Private `_row_to_*` mapper for row → model (`repositories.py:115-133, 293-309`), if the repository returns typed rows/dataclasses.
- Parameterized SQL only; `executemany` for batch inserts (`vector.py:232-250` is the batch precedent).

**Derivation helper (same module or a sibling):** one function
`typed_rows(canonical_json: str) -> tuple[list[TypedRow], list[SkippedKey]]`
derived from `json.loads(canonical_json)` — never from the in-memory dict (YAML dates diverge; `20-RESEARCH.md:323-329`). `qmd.metadata` resolution (`20-RESEARCH.md:333-349`) and reserved-name shadowing sit in this derived view, after canonicalization, with no parser/checksum change (D-19).

**Delete-then-insert** is the idempotent rebuild shape; PK `(document_id, key, ordinal)` makes it safe. FK cascade needs `PRAGMA foreign_keys = ON`, already set by `create_connection` (`src/sif/database/factory.py:63-73`); bare `sqlite3.connect()` test fixtures must enable it or delete kv rows explicitly.

**Aggregates:** the closest existing aggregate is `QueryLogRepository.history` (`repositories.py:709-720`, one `GROUP BY` returning tuples). The median/window queries in `20-RESEARCH.md:541-552` have no codebase analog — copy the research SQL, keep integer division, compute the midpoint in Python.

---

### `src/sif/core/models.py` — `SearchOptions.filter` (modified, exact)

**Analog:** itself. Add one field beside `collection_ids` with the sentinel/optional conventions and a decision comment.

`src/sif/core/models.py:329-361`:
```python
@dataclass
class SearchOptions:
    """Options for search."""

    limit: int = 10
    offset: int = 0
    per_chunk: bool = False
    # Sentinel contract: None = no collection filter (unfiltered, incl. --all);
    # [] = exclude-all — every collection excluded, searchers return zero results.
    collection_ids: list[str] | None = None
    min_score: float = 0.0
```
- Add `filter: FilterNode | None = None` with the same "None = unfiltered, never a sentinel" comment. `HybridSearcher.search` / `SearchPipeline.search` use `dataclasses.replace(...)` (`hybrid.py:82-86, 295-306`), so the field rides through untouched — **no fusion changes**.
- `core/filters.py` must not import `models.py`, so the `models.py → filters.py` import is acyclic.
- `canonical_metadata_json` (`models.py:32-48`) stays the one serializer; the kv payload is derived from its output.

---

### `src/sif/search/bm25.py` (modified, exact)

**Analog:** itself. The filter is one more fragment in the outer WHERE — after `min_score_filter`, before `LIMIT/OFFSET`.

`src/sif/search/bm25.py:110-129` (scoped branch; the `--all` branch at `130-151` has the same slot):
```python
if options.collection_ids:
    sql = f"""
        WITH matched AS MATERIALIZED (
            SELECT rowid, bm25(documents_fts, ?, ?) AS score
            FROM documents_fts
            WHERE documents_fts MATCH ?
        )
        SELECT
            d.id as document_id,
            ...
        FROM matched m
        JOIN documents d ON m.rowid = d.rowid
        JOIN collections c ON d.collection_id = c.id
        WHERE 1 = 1 {collection_filter} {min_score_filter}
        ORDER BY m.score
        LIMIT ? OFFSET ?
    """
```
- Append `{filter_clause}` in that outer WHERE and its params **after** the min-score param and **before** `params.extend([options.limit, options.offset])` (`bm25.py:152`). Both branches get the same slot.
- **Never** put the predicate inside the CTE — the CTE exists to evaluate MATCH once; the measured filtered plan keeps `MATERIALIZE matched` (`bm25.py:98-109`; research ANTI-PATTERN 2).
- `search_chunks()` (`bm25.py:186-220`) has no production caller; research recommends leaving it filter-free and documenting that.

---

### `src/sif/search/vector.py` (modified, exact)

**Analog:** itself — but the stop condition is the measured bug this phase must fix.

**Current loop** — `src/sif/search/vector.py:122-135`:
```python
target = max(1, options.limit + options.offset)
fetch_k = min(max(target * 4, 50), _MAX_FETCH_K)
while True:
    params = [embedding_str, fetch_k, *(options.collection_ids or [])]
    rows = self.db.execute(sql, params).fetchall()
    candidates = self._candidates(rows, options)
    if len(candidates) >= target or len(rows) < fetch_k or fetch_k >= _MAX_FETCH_K:
        break
    fetch_k = min(fetch_k * 2, _MAX_FETCH_K)
```
- `len(rows)` is post-JOIN; any selective JOIN filter makes it `< fetch_k` on batch one (reproduced: 100 docs / 2-doc collection / `limit=10` → one document). Replace with the corrected loop in `20-RESEARCH.md:469-493`: stop on target, `found >= pre_count`, `fetch_k >= total_vectors`, or `_MAX_FETCH_K`. Keep `_MAX_FETCH_K = 2048` (`vector.py:11-15`) as the independent ceiling.
- Inject `{filter_clause}` beside `{collection_filter}` in the post-KNN JOIN WHERE (`vector.py:105-120`); params order: embedding, fetch_k, collection ids, filter params.
- Empty-match short-circuit: pre-count 0 → `return []` before any KNN; never degrade to unfiltered (sentinel precedent `vector.py:58-59`).
- Use distinct-document count for the "all matches seen" test (per-chunk safe).
- Warning: module logger, once, stderr-only; preconditions exactly `pre_count >= page_target AND fetch_k == _MAX_FETCH_K AND len(candidates) < page_target` (`20-RESEARCH.md:516-518`).

---

### `src/sif/search/hybrid.py` (modified — pass-through + contract notes, exact)

**Analog:** itself. `src/sif/search/hybrid.py:82-102`:
```python
fetch_options = replace(
    options,
    limit=max(1, options.limit + options.offset),
    offset=0,
)

bm25_results = self.bm25.search(query, fetch_options)

vector_results: list[SearchResult] = []
if self.embedder is not None:
    query_embedding = self.embedder.embed(query)
    vector_results = self.vector.search(query_embedding, fetch_options)

if not vector_results:
    return _paginate(bm25_results, options)
```
- `replace()` carries the new `filter` field automatically; both legs receive it, so pre-RRF is structural. No fusion/dedup/slice change; keep the ONE attach at pipeline exit.
- Early returns paginate the single leg's already-filtered window.
- Update docstrings/contract notes only (per-chunk `chunk_matches` counts filtered vector rows).

---

### `src/sif/database/schema.py` (modified — detection-gated DDL + backfill, exact)

**Analog:** itself. Three sub-patterns to copy.

1. **One `_create_*` per table, called from `create_all`** — `schema.py:18-43`. Add `_create_metadata_tables()` and call it before `_create_fts_tables()` (order irrelevant except FK target `documents` must exist — it is created first). Use `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS` exactly like `_create_index_meta_table` (`schema.py:186-199`) and `_create_indexes` (`schema.py:501-539`).
2. **Detection gate** — `_add_column_if_missing` reads `PRAGMA table_info` before DDL (`schema.py:45-50`); `_create_vector_tables` reads `sqlite_master` before acting (`schema.py:475-490`). The backfill gate reads `IndexMetaRepository.get("metadata_values_version")` and returns if equal; **fresh DB** with zero documents writes the marker after a no-op pass, so later opens cost one kv read.
3. **Atomic migration wrapper** — `_create_fts_tables` wraps DDL+population in `SAVEPOINT sp_fts_tables` and rolls DDL back on failure with `contextlib.suppress(sqlite3.Error)` (`schema.py:315-317, 453-462`). Use the same savepoint shape if the backfill is invoked from `create_all`; the pass itself must commit **one short transaction per document** so it is resumable, and the marker is written only after a fully successful pass.

**`drop_all`** — add both new tables to the list at `schema.py:541-559` (before `documents`, after `document_chunks`, any order works; the existing order drops children first). Tests rely on `drop_all` for isolation (`tests/unit/database/test_schema.py:569-626`).

**No `schema_meta`:** the marker lives in `index_meta` (`schema.py:186-199`). Never create a second kv table (research Pitfall 4).

**Backfill loop shape** — `20-RESEARCH.md:775-791`: gate → `SELECT id, metadata FROM documents` → announce once via `logger.warning` (stderr, quiet-suppressible) → `with self.db:` per document → `marker.set(...)` last. A partial store must never enable filtering; an interrupted pass leaves the marker unwritten and re-runs idempotently.

---

### `src/sif/database/repositories.py` (modified — kv sync at the two write sites, exact)

**Analog:** itself. Both write sites already compute the canonical string; call the derivation helper there, inside the caller's transaction.

`src/sif/database/repositories.py:143-168` (`create`) and `:216-238` (`update`) both pass `canonical_metadata_json(document.metadata)`. Pattern:
```python
def create(self, document: Document) -> Document:
    """Create a new document."""
    self.db.execute(
        """
        INSERT INTO documents (...)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (... canonical_metadata_json(document.metadata)),
    )
    return document
```
- After the row write, delete-then-insert kv rows and skip rows via the new repository, using the **same canonical string** (compute once, pass to both). No commit — `IncrementalIndexer` owns `with self._conn:` (`incremental.py:423, 438, 451, 485`).
- `delete`/`delete_by_collection` (`repositories.py:240-268`) need nothing extra thanks to FK cascade (provided the pragma is on).
- Keep the existing docstring style; no new abstract interface.

---

### `src/sif/cli/commands/search.py` (modified — `--filter` on three commands, exact)

**Analog:** itself. The `--offset` option block is the flag template, and the existing validate-before-refresh ordering is the placement rule.

**Option block** — `search.py:461-466`:
```python
@click.option(
    "--offset",
    type=click.IntRange(min=0),
    default=0,
    help="Result offset for pagination (default: 0)",
)
```
Add `@click.option("--filter", "filter_json", default=None, help=...)` to `search_cmd` (decorators at 450-479), `vsearch_cmd` (637-664), `query_cmd` (829-894), then thread the parameter into each signature (e.g. `search_cmd` at 481-499).

**Placement / error boundary** — `search.py:512-541`:
```python
with open_initialized_database(index_path, Database) as db:
    options = SearchOptions(...)
    collections = _resolve_collections(db, collection, search_all)
    options.collection_ids = None if search_all else [c.id for c in collections]

    _pre_search_refresh(...)

    with db.connection:
        searcher = BM25Searcher(db.connection)
```
Parse with `json.loads` + `parse_filter` **before** `_pre_search_refresh` so a bad filter never pays a drift walk; wrap parse/validate in `try/except` and `raise click.ClickException(str(e)) from e` — the same mapping as `search.py:712-716, 964, 1022-1024`.

**Renderers:** `format_results_csv`/`format_results_md`/`format_results_xml` at `search.py:360-441` show the output-mode conventions (JSON via `format_results_json`, one `click.echo` per mode, machine output on stdout). Discovery's `--json` follows the same `click.echo(json.dumps(...))` discipline.

---

### `src/sif/cli/commands/collection.py` (modified — `collection metadata`, exact)

**Analog:** `collection list` / `collection show`.

`src/sif/cli/commands/collection.py:138-182` (table rendering) and `:185-213` (detail rendering):
```python
@collection_group.command("show")
@click.argument("name")
@click.pass_context
def collection_show(ctx: click.Context, name: str) -> None:
    """Show collection details."""
    index_path = ctx.obj["index_path"]

    with open_initialized_database(index_path, Database) as db:
        with db.connection:
            repo = CollectionRepository(db.connection)
            collection = repo.get_by_name(name)

        if not collection:
            raise click.ClickException(f"Collection '{name}' not found")
```
- Command lands on the existing group (`collection_group` decorator at `collection.py:21-25`); open with `open_initialized_database`; reads wrapped in `with db.connection:`.
- Default output is a Rich `Table` with styled `add_column`s (`collection.py:168-182`); JSON follows `click.echo(json.dumps(...))`.
- Optional `NAME` argument: compare with `collection_list` (no argument) vs `collection_show` (required). D-14 wins: no NAME means all collections.
- `--filter` and `--match` both validate through the shared `parse_filter` entry point; invalid input → `click.ClickException`.
- New command is auto-discovered by `scripts/generate_cli_ref.py` (Click introspection); regenerate docs, never hand-edit.

---

### `src/sif/mcp/protocol.py` (modified — `filter` fields + metadata models, exact)

**Analog:** itself.

**Input models** — `protocol.py:240-304`:
```python
class QueryInput(BaseModel):
    """Input for query tool."""

    query: str
    collections: list[str] | None = None
    limit: int = Field(default=10, ge=1)
    # Pagination (CORR-03/D-05): offset is an absolute row skip; a past-the-end
    # offset returns an empty page, never an error.
    offset: int = Field(default=0, ge=0)
    per_chunk: bool = False
    ...
```
- Add `filter: dict[str, Any] | None = None` to `QueryInput`, `LexSearchInput` (272-284), `VecSearchInput` (292-304), with a D-02 comment. Type it as a raw dict and validate explicitly in the handler so the MCP error is a tool execution error with a controlled message (research §CLI/MCP Surface Mechanics).
- New `MetadataInput`/`MetadataOutput` models: snake_case inputs per D-15 (`collections`, `filter`, `match`, `min_count`, `sort`, `limit`, `value_limit`); the three remainder names stay camelCase with `# noqa: N815` (the frozen Phase 22 contract).
- `ToolsCallResult.isError` already exists (`protocol.py:170-174`) — reuse; no new error type.

---

### `src/sif/mcp/handlers.py` (modified — metadata handler + schema sync, exact)

**Analog:** `QueryToolHandler`.

`src/sif/mcp/handlers.py:45-111`:
```python
class QueryToolHandler(ToolHandler):
    """Handler for query tool."""

    name: ClassVar[str] = "query"
    description: ClassVar[str] = (...)
    input_schema: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "collections": {"type": "array", "items": {"type": "string"}},
            "limit": {"type": "integer", "default": 10},
            # CORR-03/D-05 pagination: the hand-written schema and the
            # QueryInput.offset field (Field(ge=0)) must stay in sync.
            "offset": {"type": "integer", "minimum": 0, "default": 0},
            ...
        },
        "required": ["query"],
    }

    async def handle(self, params, backend) -> ToolsCallResult:
        input_data = QueryInput(**params)
        ...
```
- Add `"filter": {"type": "object"}` to `QueryToolHandler.input_schema` and to the metadata tool schema; a property absent from `input_schema` is invisible to tool discovery (Pitfall 12).
- Controlled error path: validate inside `handle`, and return `ToolsCallResult(content=[...], isError=True)` for invalid filters (the explicit `isError=True` precedent is `GetToolHandler` at `handlers.py:143-147`). Raising works via the generic catch (`server.py:127-134`) but logs a stack trace; prefer the explicit return.
- Register `MetadataToolHandler()` in `create_default_tools()` (`handlers.py:224-231`); update the exact tool-set assertions (`tests/unit/mcp/test_integration.py:103-104, 304-305`).
- Serialize outputs with `json.dumps(output.model_dump(), ensure_ascii=False)` exactly as the other handlers (e.g. `handlers.py:104-110`).

---

### `src/sif/mcp/backend.py` (modified — filter threading + `metadata(...)`, exact)

**Analog:** `hybrid_search` / `get_status`.

**Thread `filter`** — `backend.py:143-191`: add a `filter: dict[str, Any] | None` parameter, validate/compile inside `_search`, and set `options.filter = ...` beside `options.collection_ids = matched` (`backend.py:186-191`). Invalid filter must surface as an exception the handler converts, or be returned as a controlled error — decide once and keep it out of `INVALID_PARAMS` (`server.py:110-117` is only the envelope parse).

**New `metadata(...)`** — copy the callback shape at `backend.py:134-141`:
```python
async def _run_in_db(self, callback: Callable[[Any], T]) -> T:
    """Run a callback with a fresh database connection in a thread."""

    def _run() -> T:
        with DatabaseConnection(self.db_path).transaction() as conn:
            return callback(conn)

    return await asyncio.to_thread(_run)
```
and the `get_status` callback structure (`backend.py:340-362`): build repos on the callback connection, return a plain tuple/model, `await self._run_in_db(_fn)`.

---

### `tests/unit/core/test_filters.py` (new — role-match)

**Analog:** `tests/unit/config/test_settings.py` (pydantic error assertions) + `tests/unit/search/test_collection_filter.py` (class/parametrize style).

`tests/unit/config/test_settings.py:28-37`:
```python
def test_model_type_validation_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="Invalid model_type"):
        ...
```
- One class per concern (`TestNodeShapes`, `TestOperatorSemantics`, `TestBudgets`, `TestMtimeParsing`); every test has a one-line docstring.
- Assert validation *messages* (operator/field/path), not just that an exception occurred.
- `pytest.mark.parametrize` for the 17 operators and both branches of each semantic rule (D-10/D-11/D-13 tables in `20-RESEARCH.md:188-216`).

### `tests/unit/search/test_filters_sql.py` (new — exact)

**Analog:** `tests/unit/search/test_collection_filter.py`.

**Recording connection** — lines 241-255:
```python
class _RecordingConnection:
    """Connection proxy recording every statement BM25Searcher executes."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.calls: list[tuple[str, Sequence[object]]] = []

    def execute(self, sql: str, parameters: Sequence[object] = ()) -> sqlite3.Cursor:
        """Record the statement, then delegate to the wrapped connection."""
        self.calls.append((sql, parameters))
        return self.conn.execute(sql, parameters)
```
- **Plan assertions** — lines 268-293: locate the statement via `next(call for call in recorder.calls if "MATCH" in call[0])`, then `EXPLAIN QUERY PLAN` it and assert `MATERIALIZE` present, no `:=`, and `idx_documents_path`/`idx_documents_mtime` used for the range forms.
- **Injection regression:** run the same filter with values containing `'`, `;`, `--`, `%`; assert the SQL string is byte-identical in shape and the params carry the literal.
- Assert params order (weights → match → collection → min_score → filter → limit/offset) with the recorder, per research Pitfall 9.
- Compiler unit tests can call `compile_filter(...)` directly and compare `(sql, params)` for each operator/scope.

### `tests/unit/database/test_metadata_values.py` (new — exact)

**Analog:** `tests/unit/database/test_repositories.py`.

**Fixture** — lines 39-53:
```python
@pytest.fixture
def db():
    """Real in-memory SQLite with the production documents/contexts DDL."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    manager = SchemaManager(conn)
    manager._create_collections_table()
    manager._create_documents_table()
    ...
    yield conn
    conn.close()
```
- **Canonical-derivation parity** — copy the structure of `TestDocumentMetadataCanonicalStorage` (`test_repositories.py:534-593`): write via `DocumentRepository`, then compare the kv rows derived live against rows derived from the stored canonical JSON string (the date-valued key regression, research Pitfall 3/15).
- **FK cascade:** either use `SchemaManager` + `PRAGMA foreign_keys = ON`, or delete kv rows explicitly in bare `sqlite3.connect` fixtures (research §Typed KV Storage).
- **Backfill:** populated DB → marker absent; interrupt mid-pass → marker absent; re-run → no duplicate rows; complete pass → marker present; reopen → zero work. Mirror `TestIndexMetaTable` isolation style (`test_schema.py:569-626`).
- **Discovery:** odd/even numeric cohorts for median, array elements each counting, exact `totalKeys`/`remainingKeys`/`remainingValues`, `min_count`, skipped-key count, and the `match` grammar rejecting `exists`/`all`.

### `tests/integration/test_metadata_filtering.py` (new — exact)

**Analog:** `tests/integration/test_search_correctness.py`.

**Fixture builder** — lines 23-76: real `SchemaManager(...).create_all()`, one collection, `ConceptEmbedder` (`tests/support/bench.py:40-96`), one chunk + one vec0 row per document, skip when sqlite-vec is absent. Reuse `_options(**overrides)` (lines 79-86) for page options.
- **Containment invariant:** `filtered-hybrid ⊆ unfiltered-hybrid ∩ filter-set`; a filter admitting everything reproduces the unfiltered page exactly.
- **2 %-selectivity recall:** the Pitfall 13 regression — matching documents must return, not an empty page.
- **Composition:** filter × collection × pagination; empty match returns an empty page on both legs (never unfiltered).
- **Discovery parity:** every reported key is filterable and every filterable key appears; a non-indexable key is counted, not silently dropped.
- Raw SQL inserts bypass the kv write path (research Pitfall 10): route fixture documents through `DocumentRepository` or insert kv rows explicitly; add one test that builds via `IncrementalIndexer`.

### `tests/support/bench.py` (modified — fixture support, exact)

**Analog:** itself. `build_bench_db` (`bench.py:98-167`) inserts documents with raw `INSERT INTO documents`, so it has no kv rows. Extend it to insert kv rows from the same canonical JSON, or route through `DocumentRepository`; keep `ConceptEmbedder` as the hermetic embedder.

### Existing test files to extend (exact — follow their own conventions)

| File | Anchor to extend | What the pattern enforces |
|------|------------------|---------------------------|
| `tests/unit/search/test_bm25.py` | classes at 14/407/540 | Filtered outer WHERE + params order; unfiltered statement set unchanged |
| `tests/unit/search/test_vector.py` | `TestVectorFilteredRecall` 253-339 | Add large-corpus case proving beyond-ceiling recall and both warning branches |
| `tests/unit/search/test_hybrid.py` | 112/1135/1204 | Filter rides both legs; pagination/containment; no fusion change |
| `tests/unit/indexing/test_incremental.py` | `TestMetadataFastPath` 739-903 | Frontmatter-only edit updates kv rows in the same command; body edit leaves no stale rows |
| `tests/unit/database/test_schema.py` | `TestIndexMetaTable` 569-626; mtime index 319-350 | New tables/indexes exist, are dropped by `drop_all`, marker survives reopen |
| `tests/unit/cli/test_search.py` | `CliRunner` + `patch` setup at 1-80 | `--filter` parse/validate before refresh; `ClickException` message names operator/field/path; JSON stdout clean |
| `tests/unit/cli/test_collection.py` | `TestCollectionRealDatabase` setup 39-60 | `collection metadata` table/JSON output; options; invalid filter error |
| `tests/unit/mcp/test_backend.py` | schema-sync tests 557-561, 897-900 | `filter` appears in `input_schema` and rides `SearchOptions`; `metadata` tool registered; isError on invalid filter |
| `tests/unit/mcp/test_integration.py` | tool-set assertions 103-104, 304-305 | Update the exact set to include `metadata` |

### `docs/cli-reference.md` (generated — never hand-edit)

Run `make docs-generate` (wraps `scripts/generate_cli_ref.py`). The CI diff gate and `tests/test_docs.py::test_cli_reference_has_all_commands` (lines 422-433) fail until regenerated. No settings are added by this phase, so `docs/configuration.md` should not change.

## Shared Patterns

### Parameterized SQL (all new/modified SQL)
**Source:** `src/sif/search/bm25.py:86-96, 152`; `src/sif/database/repositories.py:635-641`
**Apply to:** `search/filters.py`, `metadata_repository.py`, all leg modifications.
- Values are always `?` params appended in SQL order; only identifiers/aliases and `?", ".join` placeholder lists are interpolated. Weights/thresholds are bound parameters (T-19-19 precedent, `bm25.py:83-96`).
- Return `("", [])` for `None`; a non-`None` filter must never disappear.

### Transaction boundaries
**Source:** `src/sif/database/database.py:46-55`; `src/sif/indexing/incremental.py:423, 438, 451, 485`; `src/sif/mcp/backend.py:134-141`
**Apply to:** repository kv sync, backfill, MCP metadata reads.
- Repositories never commit; the caller opens `with self._conn:` / `Database.transaction()`.
- Backfill: one short transaction per document so an interrupt is resumable; marker write last, in its own transaction.

### Detection-gated migration + marker
**Source:** `src/sif/database/schema.py:45-50, 186-199, 315-317, 453-462, 541-559`; `src/sif/database/repositories.py:646-669`
**Apply to:** `_create_metadata_tables`, indexes, backfill gate, `drop_all`.
- Fresh/already-migrated DBs do zero work; the marker key is global (`metadata_values_version`) in `index_meta`.
- Never enable filtering against a half-populated store.

### Sentinel / unfiltered contract
**Source:** `src/sif/search/bm25.py:63-71`; `src/sif/search/vector.py:53-59`
**Apply to:** both legs, hybrid, CLI, MCP.
- `filter is None` is the only unfiltered signal. An empty match set returns an empty page (normal zero-result path), never "no filter applied". Empty `IN ()` is never emitted.

### Error culture
**Source:** `src/sif/cli/commands/search.py:712-716`; `src/sif/cli/error_handling.py:23-28`; `src/sif/mcp/server.py:127-136`; `src/sif/mcp/handlers.py:143-147`
**Apply to:** filter validation at both surfaces.
- CLI: `click.ClickException` naming cause + remedy; MCP: `ToolsCallResult(isError=True)` inside a successful JSON-RPC response, never `INVALID_PARAMS`.
- Message names the operator, field, and AST path.

### stderr-only notices
**Source:** `src/sif/utils/logging.py:35-42, 137`; `src/sif/search/vector.py` module logger convention
**Apply to:** too-selective warning, backfill announcement.
- `logger = get_logger(__name__)`; warnings go to stderr, quiet-suppressible; never into `--json`/MCP content or the result list.

### Byte-identical defaults
**Source:** `src/sif/search/hybrid.py:76-102`; `src/sif/search/bm25.py:86-96`
**Apply to:** every leg.
- Every filtered-only behavior (pre-count, warning, extra query) gated on `filter is not None`. Unfiltered path issues exactly the old statements and emits no new output.

### Deterministic tests
**Source:** `tests/support/bench.py:40-96`; `tests/integration/test_search_correctness.py:23-76`
**Apply to:** all new tests.
- `tmp_path`/in-memory SQLite, `ConceptEmbedder` for hermetic embeddings, no wall-clock races, `pytest.skip` when sqlite-vec is absent.

### Docs gate
**Source:** `scripts/generate_cli_ref.py`; `Makefile` `docs-generate`; `tests/test_docs.py:422-433`
**Apply to:** `--filter`, `collection metadata`.
- Generated docs only; never hand-edit `docs/cli-reference.md` / `docs/configuration.md`.

## No Direct Analog

Aspects with no existing snippet to copy; use the cited research section instead.

| Aspect | File | Role | Reason | Reference to use |
|--------|------|------|--------|------------------|
| Pydantic discriminated union on `operator` + raw-dict budget pre-walk | `src/sif/core/filters.py` | domain model | Repo has pydantic models but no union/tag or recursive AST | `20-RESEARCH.md:668-747` (prototype verified on pydantic 2.12.5/2.13.1) |
| Median via window functions (no JSON1) | `src/sif/database/metadata_repository.py` | repository | No window-function SQL exists in the repo; closest is a plain `GROUP BY` at `repositories.py:709-720` | `20-RESEARCH.md:541-552` |
| `qmd.metadata` derived-view resolution + reserved-name shadowing | `src/sif/database/metadata_repository.py` (derivation helper) | transform | New concern; D-19 forbids touching parser/checksum | `20-RESEARCH.md:333-349` |
| Typed kv DDL with `value_type` CHECK + partial covering indexes | `src/sif/database/schema.py` | migration | No existing typed-kv table (only `index_meta` key/value) | `20-RESEARCH.md:277-301` |

## Metadata

**Analog search scope:** `src/sif/{core,search,database,indexing,cli,mcp,config}`, `tests/{unit,integration,support}`, `scripts/`, root `Makefile`/`pyproject.toml`.
**Files read this session:** 30 (all listed above; every path verified git-tracked).
**Pattern extraction date:** 2026-11-15.
**Parity warning carried from CONTEXT/RESEARCH:** qmd's AST is `[Unreleased]`; pin the era and record the `abfabc5` `key`→`field` delta in the SUMMARY. Re-verify before execute.
