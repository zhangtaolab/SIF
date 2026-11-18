# Phase 15: Search Quality Configuration (Hybrid Weights + Query Suggestions) - Pattern Map

**Mapped:** 2026-11-08
**Files analyzed:** 20 (12 modified source, 2 new source, 4 new/2 extended tests, 1 skill doc, 1 generator)
**Analogs found:** 20 / 20 (all git-tracked; every one verified via `git ls-files`)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/sif/search/rrf.py` | service (fusion math) | transform | itself — `fuse()` lines 20-91; `fuse_with_weights` lines 93-175 is the documented ANTI-pattern | exact |
| `src/sif/search/hybrid.py` | service | transform | itself — fuse call site hybrid.py:74 (the ONLY weights site; :228 is cross-query, weights forbidden there) | exact |
| `src/sif/core/models.py` | model | request-response (per-query transport) | itself — `SearchOptions` lines 246-261 | exact |
| `src/sif/config/settings.py` | config | request-response | `watch_*` field block settings.py:43-85 + `watch_update_depth` validator :216-230 | exact |
| `src/sif/cli/commands/search.py` | controller | request-response (CRUD write hook) | itself — flags block :632-660, options build :701-709, zero-result sites :446-449/599-602/831-834, fail-soft `_pre_search_refresh` :144-218 | exact |
| `src/sif/database/schema.py` | migration | CRUD (DDL) | `_create_llm_cache_table` schema.py:133-146 (plain table); `_create_vector_tables` :315-348 (virtual table — nearest `CREATE VIRTUAL TABLE` precedent) | role-match |
| `src/sif/database/repositories.py` | model (repository) | CRUD | `ContextRepository` repositories.py:381-511 (ctor `sqlite3.Connection`, create/list/delete, `_row_to_X`) | exact |
| `src/sif/cli/commands/suggest.py` (NEW) | controller | request-response | `src/sif/cli/commands/context.py` (module shape, Database open, table output, missing-index guard) + `watch.py:515` (top-level `@click.command`) | role-match |
| `src/sif/search/suggest.py` (NEW) | service | transform (read + in-memory) | `src/sif/search/bm25.py` — `BM25Searcher.__init__(db: sqlite3.Connection)` + `_sanitize_term` token rules bm25.py:18-33 | role-match |
| `src/sif/cli/main.py` | route | request-response | itself — import + `add_command` block main.py:87-108 | exact |
| `src/sif/mcp/protocol.py` | model | request-response | itself — `QueryInput`/`QueryOutput` protocol.py:238-250 | exact |
| `src/sif/mcp/backend.py` | service | request-response | itself — `hybrid_search` backend.py:73-123 | exact |
| `src/sif/mcp/handlers.py` | controller | request-response | itself — `QueryToolHandler` handlers.py:45-85 (hand-written `input_schema` MUST change with the pydantic model) | exact |
| `scripts/generate_config_ref.py` | config (docs generator) | transform | itself — `SECTIONS` allowlist generate_config_ref.py:150-198 | exact |
| `tests/unit/search/test_rrf.py` | test | transform | itself — fixtures :21-102, `TestRRFWeightedFusion` class :336 | exact |
| `tests/unit/cli/test_search.py` | test | request-response | itself — patch scaffold :58-78; real-DB `TestSearchOutputBranches` :1326+ | exact |
| `tests/unit/search/test_suggest.py` (NEW) | test | transform | `tests/unit/search/test_rrf.py` fixture style + `tests/unit/database/test_repositories.py` real-SQL db fixture :31-45 | role-match |
| `tests/unit/database/test_query_log_repo.py` (NEW) | test | CRUD | `tests/unit/database/test_repositories.py` — real in-memory SQLite from production DDL :31-45 | exact |
| `tests/unit/cli/test_suggest.py` (NEW) | test | request-response | `tests/unit/cli/test_search.py` CliRunner patterns (:41-78, :1326-1388) | role-match |
| `.claude/skills/sif-search/SKILL.md` | doc (skill contract) | n/a | itself — "Error handling" zero-result contract :69-74 | exact |

## Pattern Assignments

### `src/sif/search/rrf.py` (service, transform) — weighted `fuse()`

**Analog:** itself. Extend `fuse()` (lines 20-91) with optional `weights`/`k` parameters in **multiply form**. Do NOT route the default path through `fuse_with_weights`.

**Current core arithmetic — the line SC1 pins byte-identical (line 42):**
```python
# src/sif/search/rrf.py:37-42
for list_idx, results in enumerate(results_lists):
    for rank, result in enumerate(results, 1):
        doc_id = result.document_id

        # Calculate RRF score: 1 / (k + rank)
        rrf_score = 1.0 / (self.k + rank)
```

Becomes `weight * (1.0 / (self.k + rank))` with `weight = 1.0` when `weights is None` — RESEARCH experiment E1 verified `1.0 * x == x` is repr-exact, so defaults stay bit-identical. Keep signature extension minimal:

```python
# Extend (rrf.py:20-24 current):
def fuse(
    self,
    results_lists: list[list[SearchResult]],
    limit: int = 10,
    weights: list[float] | None = None,   # NEW — multiply form, no normalization
    k: int | None = None,                 # NEW — None falls back to self.k (recommended option (a))
) -> list[SearchResult]:
```

**ANTI-pattern — the normalization trap (lines 112-114, inside `fuse_with_weights`):**
```python
# src/sif/search/rrf.py:112-114 — DO NOT reuse for the default path
# Normalize weights
total_weight = sum(weights)
normalized_weights = [w / total_weight for w in weights]
```
At defaults (1.0, 1.0) this halves every score (RESEARCH E2) — SC1 fails silently. `fuse_with_weights` has zero call sites today; repurpose or delete per planner, but never let the default path route through it.

Also note the merge/sort tail to preserve (lines 54-91): `scores[doc_id] = (existing_score + rrf_score, ...)`, sort by score desc, and `result.scores["rrf_score"] = score` at line 88 — the golden test asserts on exactly this field.

---

### `src/sif/search/hybrid.py` (service, transform) — read options, pass to fuse

**Analog:** itself. Two existing construction/fuse sites:

```python
# src/sif/search/hybrid.py:39 (HybridSearcher.__init__)
self.rrf = RRFFusion(k=60)

# src/sif/search/hybrid.py:74 (the ONE weights call site)
fused_results = self.rrf.fuse([bm25_results, vector_results], options.limit)
```

Change :74 only:
```python
fused_results = self.rrf.fuse(
    [bm25_results, vector_results],
    options.limit,
    weights=[options.bm25_weight, options.vector_weight],
    k=options.rrf_k,
)
```

**Do not touch (Pitfall 9):** (1) single-source early returns at hybrid.py:67-71 — weights are a semantic no-op there, preserve behavior; (2) `SearchPipeline.search` second fuse at :228 is cross-query VARIANT fusion — `k` may flow there, weights must NOT. `SearchPipeline` construction (:136-150) needs no change; options already flow through `pipeline.search(query, options)`.

---

### `src/sif/core/models.py` (model, request-response) — SearchOptions fields

**Analog:** itself. Append three fields to `SearchOptions` (lines 246-261), defaults equal today's hardcoded behavior so every existing construction site (search.py:377/558/701, backend.py:83) stays byte-identical with zero edits:

```python
# src/sif/core/models.py:245-261 — current tail of the dataclass
@dataclass
class SearchOptions:
    """Options for search."""

    limit: int = 10
    offset: int = 0
    # Sentinel contract: None = no collection filter ...
    collection_ids: list[str] | None = None
    min_score: float = 0.0
    ...
    snippet_max_length: int = 300
    # ADD (defaults = today's behavior):
    # rrf_k: int = 60
    # bm25_weight: float = 1.0
    # vector_weight: float = 1.0
```

If a `QueryLogEntry` dataclass is added for the repository, copy the `PathContext` shape (models.py:182-204): `id: str = field(default_factory=lambda: str(uuid.uuid4()))`, `created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))`, plus `to_dict()` — **aware UTC only** (WR-03 cautionary finding; see Shared Patterns).

---

### `src/sif/config/settings.py` (config) — new SIF_ fields

**Analog:** the `watch_*` block (Field with `ge`/`gt` + long description) and the `watch_update_depth` validator.

```python
# src/sif/config/settings.py:43-49 — Field style to copy
# Watch settings (Phase 12 live index)
watch_debounce_interval: float = Field(
    default=0.5,
    gt=0,
    description="Quiet window in seconds a filesystem event burst must "
    "settle for before `sif watch` runs one incremental update",
)

# src/sif/config/settings.py:216-230 — validator precedent (fail at settings
# construction, naming the field)
@field_validator("watch_update_depth")
@classmethod
def validate_watch_update_depth(cls, v: str) -> str:
    ...
    raise ValueError(
        f"Invalid watch_update_depth: {v}. Must be one of {sorted(valid_depths)}"
    )
    return v
```

New fields (into the "Search settings" region, settings.py:178-188): `rrf_k: int = Field(default=60, ge=1, ...)`, `bm25_weight: float = Field(default=1.0, gt=0, ...)` (NO upper bound — D-03), `vector_weight` same, plus `query_history_enabled: bool = Field(default=True, ...)`, `query_history_limit: int = Field(default=500, ge=1, ...)`. Plain `ge`/`gt` constraints suffice (no custom validator needed unless a cross-field rule appears). `get_settings()` lru_cache (settings.py:317-323) is untouched.

---

### `src/sif/cli/commands/search.py` (controller, request-response + CRUD write hook)

**Analog:** itself, three distinct sub-patterns.

**(a) New flags on `query_cmd` ONLY (D-02)** — Click options default `None` so `flag > SIF_ setting > default` precedence works:

```python
# src/sif/cli/commands/search.py:640-646 — existing typed-option precedent (IntRange)
@click.option(
    "-C",
    "--candidate-limit",
    default=20,
    type=click.IntRange(1, 200),
    help="Reranker candidate pool size",
)
@click.option("--intent", help="Search intent hint for query expansion")
# ADD: --rrf-k (type=click.IntRange(1, None), default=None),
#      --bm25-weight / --vector-weight (positive float, default=None)
```

Fill options at the existing build site (search.py:701-709) using the settings touchpoint that already exists at :740-745 (`rrf_k if rrf_k is not None else settings.rrf_k`, etc. — settings is in scope by then; move the settings load above the options build if needed). `search_cmd`/`vsearch_cmd` get NO weight flags.

**(b) Zero-result DYM hooks** — hook BEFORE each early `return` (Pitfall 6). The three sites are structurally identical:

```python
# src/sif/cli/commands/search.py:446-449 (search_cmd; vsearch 599-602, query 831-834)
if not results:
    if not quiet:
        console.print("[yellow]No results found.[/yellow]")
    return
```

Mode routing per Phase 14 stdout purity: table mode → DYM line on stdout `console` after "No results found."; `--json` mode → `suggestions` key in the JSON (conditional object wrap per RESEARCH Pitfall 5 — keep plain `[]` when no suggestions); CSV/MD/XML/files modes → `console_err` (search.py:29-32) so machine output stays pure.

**(c) query_log write hook (D-08)** — after `results` is obtained, still inside the `with db.connection:` block (:401/:582/:776), guarded fail-soft exactly like `_pre_search_refresh` (D-05 precedent):

```python
# src/sif/cli/commands/search.py:166-175 — the fail-soft settings-touchpoint precedent
try:
    settings = get_settings()
except Exception:
    logger.debug("Pre-search refresh skipped: settings unavailable", exc_info=True)
    return
...
# src/sif/cli/commands/search.py:208-214 — failure never breaks the search
except Exception:
    logger.warning(
        "Pre-search drift refresh failed; searching current index",
        exc_info=True,
    )
```

Copy this shape for the history write: skip entirely when `SIF_QUERY_HISTORY_ENABLED=0`; wrap INSERT+trim in try/except + `logger.warning`. `search_cmd` has no settings object in scope today — give the hook its own best-effort `get_settings()` like :166-175.

**Do not widen WR-02 (Pitfall 7):** `SearchPipeline(...)` construction at search.py:777-784 sits outside the `try:` at :785. Weight plumbing rides `options` (built :701-709, passed at :786 — already inside the try). Do not restructure the construction ordering; the finding is tracked in the Phase 14 disposition ledger.

---

### `src/sif/database/schema.py` (migration, CRUD DDL) — query_log + documents_fts_v

**Analog (plain table):** `_create_llm_cache_table` — new `_create_query_log_table` follows it exactly:

```python
# src/sif/database/schema.py:133-146
def _create_llm_cache_table(self) -> None:
    """Create LLM cache table."""
    self.db.execute("""
        CREATE TABLE IF NOT EXISTS llm_cache (
            id TEXT PRIMARY KEY,
            ...
            expires_at TEXT,
            UNIQUE(model_name, prompt_hash)
        )
    """)
```

Register in `create_all()` (schema.py:18-28) and add `query_log` + `documents_fts_v` to `drop_all` tables list (schema.py:384-395) for test isolation.

**Analog (virtual table):** `_create_vector_tables` is the only `CREATE VIRTUAL TABLE IF NOT EXISTS` precedent — the vocab table joins `_create_fts_tables` (schema.py:194) with:

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts_v USING fts5vocab(documents_fts, 'row')
```

Place it right after the `documents_fts` DDL (schema.py:220-227, whose `tokenize='porter'` is why vocab terms are stems). Idempotent and main-schema-only (verified in RESEARCH Pattern 4/Pitfall 8); also add a lazy ensure in the suggest engine because MCP backend connections never run `init_schema`.

---

### `src/sif/database/repositories.py` (model/repository, CRUD) — QueryLogRepository

**Analog:** `ContextRepository` (repositories.py:381-511). Conventions to copy verbatim: ctor takes `sqlite3.Connection`; parameterized SQL only; `_row_to_X` row mapper; `cursor.rowcount > 0` on deletes; aware-UTC `datetime.now(timezone.utc).isoformat()` timestamps (ContextRepository.create, repositories.py:390-397):

```python
# src/sif/database/repositories.py:384-398 — ctor + create shape
class ContextRepository:
    """Repository for context operations."""

    def __init__(self, db: sqlite3.Connection) -> None:
        """Initialize the context repository."""
        self.db = db

    def create(self, context: PathContext) -> PathContext:
        """Create a new context."""
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            """
            INSERT INTO contexts (id, target_id, context_type, content, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (context.id, context.path, context.context_type, context.context, now, now),
        )
        return context
```

Trim-in-write (D-09): INSERT then `DELETE FROM query_log WHERE id NOT IN (SELECT id FROM query_log ORDER BY created_at DESC LIMIT ?)` in the same short transaction — the Phase 11 D-01 short-CRUD-outside-the-flock class, no flock. History read (D-13): one aggregate SQL `SELECT query, COUNT(*), MAX(created_at) FROM query_log GROUP BY query`; decay applied in Python. `clear()` mirrors `ContextRepository.delete` rowcount idiom (repositories.py:472-475). JSON-array column (`collections`) follows the `ignore_patterns` `json.dumps` convention (repositories.py:39).

---

### `src/sif/search/suggest.py` (NEW — service, transform)

**Analog:** `BM25Searcher` for the connection-taking, read-only engine shape:

```python
# src/sif/search/bm25.py:36-46 — engine ctor + options-optional search
class BM25Searcher:
    """BM25 full-text search using SQLite FTS5."""

    def __init__(self, db: sqlite3.Connection) -> None:
        """Initialize the BM25 searcher."""
        self.db = db

    def search(self, query: str, options: SearchOptions | None = None) -> list[SearchResult]:
        if options is None:
            options = SearchOptions()
```

**Tokenization must match the searcher's rules** (Pitfall 4 — in-vocab membership tested the way the searcher matches):

```python
# src/sif/search/bm25.py:16-33 — the sanitizer every token passes through
_FTS_METACHARS = re.compile(r'["*():^]')

def _sanitize_term(term: str) -> str:
    cleaned = _FTS_METACHARS.sub(" ", term).strip()
    if not cleaned:
        return ""
    return f'"{cleaned}"*'
```

Import and reuse `_sanitize_term`/`_FTS_METACHARS` (or re-derive token rules identically) in `SuggestionEngine` — never build MATCH strings from vocab terms by hand. Module header follows the house style: `"""..."""`, `from __future__ import annotations`, `logger = get_logger(__name__)` (hybrid.py:1-22). Core primitives (verified measured in RESEARCH): one `SELECT term, doc FROM documents_fts_v` scan; `bisect` prefix completion over the sorted term list; per-word `difflib.get_close_matches` over a first-letter±1 bucket; history aggregate from `QueryLogRepository`. Degrade to empty suggestions on `sqlite3.OperationalError` (read-only DB / missing table) — never crash a search command.

---

### `src/sif/cli/commands/suggest.py` (NEW — controller, request-response)

**Analog:** `src/sif/cli/commands/context.py` for module shape and `watch.py:515` for the top-level command decorator.

```python
# src/sif/cli/commands/context.py:1-22 — module header conventions
"""Context management commands."""

from __future__ import annotations
...
import click
from rich.console import Console
from rich.markup import escape
from rich.table import Table
...
console = Console()

# src/sif/cli/commands/context.py:150-158 — missing-index guard + Database open
index_path = ctx.obj["index_path"]
# Missing-index guard ... never materialize a fresh empty DB for a write command.
if not index_path.exists():
    console.print("[yellow]No index found.[/yellow]")
    return

with Database(index_path) as db:
    db.init_schema()
```

```python
# src/sif/cli/commands/watch.py:515-516 — top-level command (not a group subcommand)
@click.command("watch")
@click.option(...)
@click.pass_context
def watch_cmd(...):
```

Shape: `sif suggest QUERY [--limit N] [--json] [-q]` / `sif suggest --clear-history` (mutually exclusive with QUERY — `click.ClickException` or `click.UsageError`). `--json` emits `{"completions": [...], "did_you_mean": [...], "history": [...]}` via `click.echo(json.dumps(..., ensure_ascii=False))` mirroring `format_results_json` (search.py:70-76). Table mode: three labeled sections, each cell `escape()`d like context_list (context.py:285-289). `--clear-history` confirmation print outside the transaction (context.py:213-216 precedent: "a display failure must not roll back a write that already committed"). Reads use `with db.connection:` (context.py:262-264); the clear uses `with db.transaction() as conn` (context.py:307-309).

---

### `src/sif/cli/main.py` (route) — register suggest_cmd

**Analog:** itself, mechanical extension of the existing block:

```python
# src/sif/cli/main.py:87-108
from sif.cli.commands.search import search_group  # noqa: E402
from sif.cli.commands.watch import watch_cmd  # noqa: E402
...
cli.add_command(search_group)
...
cli.add_command(watch_cmd)
# ADD: from sif.cli.commands.suggest import suggest_cmd  +  cli.add_command(suggest_cmd)
```

---

### `src/sif/mcp/protocol.py` + `backend.py` + `handlers.py` (model + service + controller, request-response)

Three coordinated edits — the boundary has BOTH hand-written JSON schema and pydantic models.

```python
# src/sif/mcp/protocol.py:238-250 — extend both models
class QueryInput(BaseModel):
    """Input for query tool."""

    query: str
    collections: list[str] | None = None
    limit: int = Field(default=10, ge=1)
    min_score: float = Field(default=0.0, ge=0.0)
    # ADD: rrf_k: int | None = Field(default=None, ge=1)
    #      bm25_weight: float | None = Field(default=None, gt=0.0)
    #      vector_weight: float | None = Field(default=None, gt=0.0)

class QueryOutput(BaseModel):
    """Output for query tool."""

    results: list[SearchResult] = Field(default_factory=list)
    # ADD: suggestions: list[str] = Field(default_factory=list)
```

```python
# src/sif/mcp/handlers.py:53-62 — the hand-written schema MUST gain the same
# properties (forgetting hides them from MCP tool discovery)
input_schema: ClassVar[dict[str, Any]] = {
    "type": "object",
    "properties": {
        "query": {"type": "string"},
        "collections": {"type": "array", "items": {"type": "string"}},
        "limit": {"type": "integer", "default": 10},
        "min_score": {"type": "number", "default": 0.0},
    },
    "required": ["query"],
}
# handler passes new fields through: handlers.py:70-77 (QueryInput(**params) → backend.hybrid_search(...))
```

```python
# src/sif/mcp/backend.py:73-99 — extend hybrid_search signature; None falls back
# to self.settings (D-04 — backend already holds settings, backend.py:44)
async def hybrid_search(
    self,
    query: str,
    collections: list[str] | None = None,
    limit: int = 10,
    min_score: float = 0.0,
) -> list[SearchResult]:
    def _search(conn: Any) -> list[SearchResult]:
        options = SearchOptions(
            limit=limit,
            min_score=min_score,
            ...
        )
```

Boundary-remap pitfall (backend.py:109-118, documented in-code): "this boundary re-maps core fields one by one, so an unlisted field is silently dropped" — the new `suggestions` field must be explicitly populated on the zero-result path. MCP queries do NOT write query_log (D-08). `SearchBackend.__init__` fail-soft embedder load (backend.py:46-62) is the precedent for any engine-construction degradation.

---

### `scripts/generate_config_ref.py` (config, transform) — SECTIONS allowlist

**Analog:** itself. New settings must join `SECTIONS` or they never render in docs/configuration.md:

```python
# scripts/generate_config_ref.py:176-184 — the natural home
(
    "Search Settings",
    [
        "default_search_type",
        "default_limit",
        "search_refresh_enabled",
        "search_refresh_max_files",
        # ADD: rrf_k, bm25_weight, vector_weight (+ query_history_* here or own section)
    ],
),
```

Env vars render as `` `SIF_{FIELD_NAME.UPPER()}` `` (generate_config_ref.py:292) — doc-gate test greps must use `SIF_RRF_K`-style spellings, never lowercase field names. Then `make docs-generate`; never hand-edit docs. `sif suggest` lands in docs/cli-reference.md automatically via generate_cli_ref.py once the command exists.

---

### Tests

**`tests/unit/search/test_rrf.py` (extend)** — analog: itself. Fixtures :21-102 already build `bm25_results`/`vector_results`; `TestRRFWeightedFusion` (:336) is where weighted-fuse tests join. Golden test compares `repr(r.scores["rrf_score"])` for plain vs `weights=[1.0, 1.0]` (RESEARCH Code Examples has the full sketch). House test style: class-per-behavior, Arrange/Act/Assert docstrings, fully annotated.

**`tests/unit/database/test_query_log_repo.py` (NEW)** — analog: `tests/unit/database/test_repositories.py`:

```python
# tests/unit/database/test_repositories.py:31-45 — real in-memory SQLite from
# production DDL (the deterministic-test culture; no mocks against SQL)
@pytest.fixture
def db():
    """Real in-memory SQLite with the production documents/contexts DDL."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    manager = SchemaManager(conn)
    manager._create_collections_table()
    ...
    yield conn
    conn.close()
```
Call the new `manager._create_query_log_table()` in the same fixture; test add/trim/clear/history-aggregate against real SQL.

**`tests/unit/cli/test_suggest.py` (NEW)** and **`tests/unit/cli/test_search.py` (extend)** — analog: `tests/unit/cli/test_search.py`. Two flavors: (1) mocked-scaffold CliRunner for option plumbing:

```python
# tests/unit/cli/test_search.py:41-78 — patch scaffold + assert on SearchOptions
runner = CliRunner()
...
with (
    patch("sif.cli.commands.search.Database", return_value=mock_db),
    patch("sif.cli.commands.search.CollectionRepository", return_value=mock_repo),
    patch("sif.cli.commands.search.BM25Searcher", return_value=mock_searcher),
):
    result = runner.invoke(
        search_cmd,
        ["foo"],
        obj={"index_path": MagicMock(exists=lambda: True)},
    )
assert result.exit_code == 0
call_args = mock_searcher.search.call_args
options = call_args[0][1]
assert options.collection_ids == ["coll1"]   # pattern for asserting rrf_k/bm25_weight
```

(2) real-DB integration (`TestSearchOutputBranches`, test_search.py:1326-1388) with `tmp_path` index + `env={"COLUMNS": "80"}` — use for zero-result DYM, stdout purity per mode, and `--json` three-array shape. Note the autouse `isolate_quiet_state` fixture (:1329-1336) — copy it for any test invoking `-q` paths. Run with `env -u FORCE_COLOR NO_COLOR=1` (project memory).

**`tests/unit/search/test_suggest.py` (NEW)** — engine tests: fixture-vocab DYM/prefix/history, the SC2 pin test (run every suggestion as a real BM25 query, assert ≥1 hit), and the 100 ms budget test (`time.perf_counter` around the core function only, generous headroom, no wall-clock CLI races). Per-research: no timing-race assertions.

**MCP weight tests** — extend `tests/unit/mcp/test_backend.py` (fixture at :20-27 patches `get_settings`, `@pytest.mark.asyncio` async tests asserting on options/kwargs passed through `hybrid_search`).

**`.claude/skills/sif-search/SKILL.md` (doc)** — update the zero-result contract note (:69-74, "If output is `[]`: report No results found...") once the JSON wrap shape is chosen, in the same plan that changes the JSON.

## Shared Patterns

### Fail-soft hooks on the search hot path
**Source:** `src/sif/cli/commands/search.py:144-218` (`_pre_search_refresh`)
**Apply to:** query_log write hook (all three commands); any DYM computation wrapper.
Best-effort `get_settings()` in try/except (never break a command that never touched settings), outer `try/except Exception` + `logger.warning(..., exc_info=True)`, user-visible degradation at most one `console_err` line. A history/suggestion failure must NEVER fail the search.

### stdout purity / stderr notices
**Source:** `src/sif/cli/commands/search.py:29-32`
**Apply to:** DYM display in CSV/MD/XML/files modes; any suggest-command notices.
```python
console = Console()
# D-07 stderr contract: refresh notices/warnings must never pollute stdout,
# which stays clean for --json/--csv piping (mcp.py console_err precedent).
console_err = Console(stderr=True)
```

### ValidationError → ClickException
**Source:** `src/sif/cli/commands/search.py:740-745` (query_cmd settings touchpoint)
**Apply to:** suggest command's settings load (weight flag handling reuses query_cmd's existing touchpoint).
```python
try:
    settings = get_settings()
except ValidationError as e:
    raise click.ClickException(str(e)) from e
```

### Missing-index guard + Database open
**Source:** `src/sif/cli/commands/context.py:150-158`, `search.py:368-374`
**Apply to:** suggest command (all modes).
`if not index_path.exists(): console.print("[yellow]No index found...[/yellow]"); return` then `with Database(index_path) as db: db.init_schema()`. Reads under `with db.connection:`; writes under `with db.transaction() as conn:` (automatic rollback per CLAUDE.md).

### Aware-UTC timestamps
**Source:** `src/sif/database/repositories.py:390` (`ContextRepository.create`), `src/sif/core/models.py:45`
**Apply to:** query_log `created_at`. Use `datetime.now(timezone.utc).isoformat()` everywhere. Do NOT copy `LLMCacheRepository.set`'s naive-local `fromtimestamp(...).isoformat()` (repositories.py:549-550) — that is open finding WR-03.

### Module logger
**Source:** `src/sif/search/hybrid.py:22`
**Apply to:** suggest engine, suggest command, QueryLogRepository call sites.
```python
logger = get_logger(__name__)
```

### Parameterized SQL only
**Source:** every repository method (e.g. repositories.py:391-397)
**Apply to:** QueryLogRepository, vocab scan. Placeholders `?` with tuple params; never f-string user/vocab-derived text into SQL or MATCH strings — vocab terms re-enter search exclusively via `_build_fts_query`/`_sanitize_term` (bm25.py:21-33).

### Rich table cells escaped
**Source:** `src/sif/cli/commands/context.py:282-289`
**Apply to:** suggest table sections. Truncate BEFORE escape; `escape()` every user/vocab-derived cell so bracket sequences render literally.

## No Analog Found

| Item | Role | Data Flow | Reason / Nearest Partial |
|------|------|-----------|--------------------------|
| `fts5vocab` virtual-table creation | migration | n/a | No fts5vocab anywhere in src (grep-verified). Nearest partial: `_create_vector_tables`' `CREATE VIRTUAL TABLE IF NOT EXISTS ... USING vec0(...)` (schema.py:341-348). DDL verified in RESEARCH Pattern 4; must be main-schema (temp impossible), plus lazy ensure in the engine |
| Performance/budget test (100 ms) | test | n/a | No perf-budget test precedent in tests/. Closest culture: deterministic real-DB batteries (test_repositories.py). Follow RESEARCH D-14: assert on the core function with `time.perf_counter` + generous headroom, no wall-clock CLI races |
| DYM/legacy cleanup of `fuse_with_weights` | service | transform | Zero call sites (grep-verified); planner decides repurpose-vs-delete. If deleted, its tests (`TestRRFWeightedFusion::test_fuse_with_weights_preserves_scores`, test_rrf.py:807) are removed/adapted in the same plan |

## Metadata

**Analog search scope:** `src/sif/` (search, cli, database, mcp, core, config), `tests/unit/` (search, cli, database, mcp), `scripts/`, `.claude/skills/sif-search/`
**Files scanned:** 20 analog files read (all ≤ 2,000 lines except tests/unit/cli/test_search.py — targeted reads only)
**Tracked-source gate:** all 21 named analog paths verified via `git ls-files -- <path>` (all tracked, none gitignored mirrors)
**Pattern extraction date:** 2026-11-08
