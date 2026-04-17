# Phase 5: Agent Context Experience - Pattern Map

**Mapped:** 2026-04-18
**Files analyzed:** 10
**Analogs found:** 10 / 10

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/docsift/database/schema.py` | config | migration | `src/docsift/database/schema.py` (existing `_create_path_contexts_table`) | exact |
| `src/docsift/database/repositories.py` | repository | CRUD | `src/docsift/database/repositories.py` (existing `PathContextRepository`) | exact |
| `src/docsift/cli/commands/context.py` | controller | request-response | `src/docsift/cli/commands/context.py` (existing) | exact |
| `src/docsift/core/models.py` | model | transform | `src/docsift/core/models.py` (existing `SearchResult`) | exact |
| `src/docsift/search/bm25.py` | service | request-response | `src/docsift/search/bm25.py` (existing `search()`) | exact |
| `src/docsift/search/vector.py` | service | request-response | `src/docsift/search/vector.py` (existing `search()`) | exact |
| `src/docsift/search/hybrid.py` | service | request-response | `src/docsift/search/hybrid.py` (existing `HybridSearcher.search()`) | exact |
| `src/docsift/cli/main.py` | config | request-response | `src/docsift/cli/main.py` (existing command registration) | exact |
| `tests/unit/cli/test_context.py` | test | request-response | `tests/unit/cli/test_collection.py` | role-match |
| `tests/unit/database/test_schema.py` | test | migration | `tests/unit/database/test_schema.py` (existing) | exact |

## Pattern Assignments

### `src/docsift/database/schema.py` (config, migration)

**Analog:** `src/docsift/database/schema.py` (self)

**Existing table creation pattern** (lines 92-104):
```python
def _create_path_contexts_table(self) -> None:
    """Create path contexts table."""
    self.db.execute("""
        CREATE TABLE IF NOT EXISTS path_contexts (
            id TEXT PRIMARY KEY,
            collection_id TEXT,
            path TEXT NOT NULL,
            context TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE SET NULL
        )
    """)
```

**Index creation pattern** (lines 257-293):
```python
def _create_indexes(self) -> None:
    """Create database indexes."""
    # Documents indexes
    self.db.execute("""
        CREATE INDEX IF NOT EXISTS idx_documents_collection 
        ON documents(collection_id)
    """)
    # ... more indexes ...
```

**SchemaManager initialization pattern** (lines 17-26):
```python
def create_all(self) -> None:
    """Create all database tables and indexes."""
    self._create_collections_table()
    self._create_documents_table()
    self._create_document_chunks_table()
    self._create_path_contexts_table()
    self._create_llm_cache_table()
    self._create_fts_tables()
    self._create_vector_tables()
    self._create_indexes()
```

**Migration pattern (SAVEPOINT)** — from RESEARCH.md, verified via direct testing:
```python
def _migrate_path_contexts(self) -> None:
    """Migrate path_contexts -> contexts atomically."""
    cursor = self.db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='path_contexts'"
    )
    if not cursor.fetchone():
        return  # Nothing to migrate

    self.db.execute("SAVEPOINT sp_migration")
    try:
        self._create_contexts_table()
        self.db.execute("""
            INSERT INTO contexts (id, target_id, context_type, content, created_at, updated_at)
            SELECT id, path, 'path', context, created_at, updated_at
            FROM path_contexts
        """)
        self.db.execute("DROP TABLE path_contexts")
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_contexts_target
            ON contexts(target_id, context_type)
        """)
        self.db.execute("RELEASE SAVEPOINT sp_migration")
    except Exception as e:
        self.db.execute("ROLLBACK TO SAVEPOINT sp_migration")
        print(f"Migration failed: {e}", file=sys.stderr)
        raise
```

**Stats pattern** (lines 314-339):
```python
def get_stats(self) -> dict:
    """Get database statistics."""
    stats = {}
    cursor = self.db.execute("SELECT COUNT(*) FROM path_contexts")
    stats["path_contexts"] = cursor.fetchone()[0]
    return stats
```

---

### `src/docsift/database/repositories.py` (repository, CRUD)

**Analog:** `src/docsift/database/repositories.py` (existing `PathContextRepository`, lines 365-434)

**Repository class pattern** (lines 365-434):
```python
class PathContextRepository:
    """Repository for path context operations."""
    
    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db
    
    def create(self, context: PathContext) -> PathContext:
        """Create a new path context."""
        now = datetime.utcnow().isoformat()
        self.db.execute(
            """
            INSERT INTO path_contexts (id, collection_id, path, context, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (context.id, context.collection_id, context.path, context.context, now, now)
        )
        return context
    
    def get_by_path(self, path: str) -> Optional[PathContext]:
        """Get context by path."""
        cursor = self.db.execute(
            "SELECT * FROM path_contexts WHERE path = ?",
            (path,)
        )
        row = cursor.fetchone()
        return self._row_to_context(row) if row else None
    
    def list_all(self) -> List[PathContext]:
        """List all path contexts."""
        cursor = self.db.execute("SELECT * FROM path_contexts ORDER BY path")
        return [self._row_to_context(row) for row in cursor.fetchall()]
    
    def list_by_collection(self, collection_id: str) -> List[PathContext]:
        """List contexts for a collection."""
        cursor = self.db.execute(
            "SELECT * FROM path_contexts WHERE collection_id = ? ORDER BY path",
            (collection_id,)
        )
        return [self._row_to_context(row) for row in cursor.fetchall()]
    
    def update(self, context: PathContext) -> PathContext:
        """Update a path context."""
        self.db.execute(
            """
            UPDATE path_contexts 
            SET context = ?, updated_at = ?
            WHERE id = ?
            """,
            (context.context, datetime.utcnow().isoformat(), context.id)
        )
        return context
    
    def delete(self, context_id: str) -> bool:
        """Delete a path context."""
        cursor = self.db.execute(
            "DELETE FROM path_contexts WHERE id = ?",
            (context_id,)
        )
        return cursor.rowcount > 0
    
    def _row_to_context(self, row: sqlite3.Row) -> PathContext:
        """Convert database row to PathContext."""
        return PathContext(
            id=row["id"],
            path=row["path"],
            collection_id=row["collection_id"],
            context=row["context"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
```

**CollectionRepository name resolution pattern** (lines 60-67):
```python
def get_by_name(self, name: str) -> Optional[Collection]:
    """Get collection by name."""
    cursor = self.db.execute(
        "SELECT * FROM collections WHERE name = ?",
        (name,)
    )
    row = cursor.fetchone()
    return self._row_to_collection(row) if row else None
```

---

### `src/docsift/cli/commands/context.py` (controller, request-response)

**Analog:** `src/docsift/cli/commands/context.py` (self, lines 1-138)

**Click group pattern** (lines 19-22):
```python
@click.group("context")
def context_group() -> None:
    """Manage path contexts."""
    pass
```

**Command with ctx.obj pattern** (lines 25-70):
```python
@context_group.command("add")
@click.argument("path")
@click.argument("context_text")
@click.option("--collection", "-c", help="Associate with a collection")
@click.pass_context
def context_add(
    ctx: click.Context,
    path: str,
    context_text: str,
    collection: Optional[str],
) -> None:
    """Add context for a path."""
    index_path = ctx.obj["index_path"]
    db = Database(index_path)
    db.init_schema()
    
    with db.transaction() as conn:
        repo = PathContextRepository(conn)
        # ... operations ...
        console.print(f"[green]Context added for '{path}'[/green]")
```

**Click exception pattern** (lines 51-52):
```python
if not coll:
    raise click.ClickException(f"Collection '{collection}' not found")
```

**Rich table output pattern** (lines 126-137):
```python
table = Table(title="Path Contexts")
table.add_column("Path", style="cyan")
table.add_column("Context", style="green")

for ctx_item in contexts:
    context_text = ctx_item.context
    if len(context_text) > 50:
        context_text = context_text[:47] + "..."
    table.add_row(ctx_item.path, context_text)

console.print(table)
```

**Alias registration pattern** — from RESEARCH.md, verified via direct Click testing:
```python
@context_group.command("remove")
@click.argument("context_id")
def context_remove(context_id: str) -> None:
    """Remove a context by ID."""
    ...

# Register alias
context_group.add_command(context_remove, name="rm")
```

---

### `src/docsift/core/models.py` (model, transform)

**Analog:** `src/docsift/core/models.py` (self, lines 178-205)

**SearchResult dataclass pattern** (lines 178-205):
```python
@dataclass
class SearchResult:
    """A search result."""
    document_id: str
    title: str
    path: str
    collection_name: str
    score: float
    content: Optional[str] = None
    highlights: List[str] = field(default_factory=list)
    rank: int = 0
    scores: Dict[str, Optional[float]] = field(default_factory=dict)
    snippet: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "document_id": self.document_id,
            "title": self.title,
            "path": self.path,
            "collection_name": self.collection_name,
            "score": self.score,
            "content": self.content,
            "highlights": self.highlights,
            "rank": self.rank,
            "scores": self.scores,
            "snippet": self.snippet,
        }
```

**New field addition pattern** (add at end with `default=None`):
```python
@dataclass
class SearchResult:
    # ... existing fields ...
    snippet: Optional[str] = None
    context_description: Optional[str] = None  # NEW - added at end with default
```

---

### `src/docsift/search/bm25.py` (service, request-response)

**Analog:** `src/docsift/search/bm25.py` (self, lines 11-84)

**Search result construction pattern** (lines 58-82):
```python
for rank, row in enumerate(cursor.fetchall(), 1):
    score = 1.0 / (1.0 + abs(row["score"]))
    
    if score < options.min_score:
        continue
    
    result = SearchResult(
        document_id=row["document_id"],
        title=row["title"] or "",
        path=row["path"],
        collection_name=row["collection_name"],
        score=score,
        rank=rank,
    )
    
    if options.include_content:
        result.content = self._get_document_content(row["document_id"])
    
    if options.include_highlights:
        result.highlights = self._get_highlights(
            row["document_id"], query, options.max_highlights
        )
    
    results.append(result)

return results
```

**Batch context enrichment pattern** — from RESEARCH.md, to add at final return point:
```python
def _attach_contexts(self, results: list[SearchResult]) -> list[SearchResult]:
    if not results:
        return results
    paths = list({r.path for r in results})
    placeholders = ", ".join(["?"] * len(paths))
    sql = f"""
        SELECT target_id, content FROM contexts
        WHERE context_type = 'path' AND target_id IN ({placeholders})
    """
    cursor = self.db.execute(sql, paths)
    context_map = {row["target_id"]: row["content"] for row in cursor.fetchall()}
    for result in results:
        result.context_description = context_map.get(result.path)
    return results
```

---

### `src/docsift/search/vector.py` (service, request-response)

**Analog:** `src/docsift/search/vector.py` (self, lines 12-116)

**Vector search result construction** (lines 80-100):
```python
for rank, row in enumerate(cursor.fetchall(), 1):
    score = 1.0 - (row["score"] / 2.0)

    if score < options.min_score:
        continue

    result = SearchResult(
        document_id=row["document_id"],
        title=row["title"] or "",
        path=row["path"],
        collection_name=row["collection_name"],
        score=score,
        rank=rank,
    )

    if options.include_content:
        result.content = self._get_document_content(row["document_id"])

    results.append(result)

return results
```

---

### `src/docsift/search/hybrid.py` (service, request-response)

**Analog:** `src/docsift/search/hybrid.py` (self, lines 22-101)

**Hybrid search final return pattern** (lines 54-82):
```python
# Get BM25 results
bm25_results = self.bm25.search(query, options)

# Get vector results if embedder is available
vector_results: List[SearchResult] = []
if self.embedder is not None:
    query_embedding = self.embedder.embed(query)
    vector_results = self.vector.search(query_embedding, options)

# If only one method returned results, return those
if not vector_results:
    return bm25_results
if not bm25_results:
    return vector_results

# Fuse results using RRF
fused_results = self.rrf.fuse([bm25_results, vector_results], options.limit)

# Re-fetch content and highlights if needed
if options.include_content or options.include_highlights:
    for result in fused_results:
        if options.include_content and result.content is None:
            result.content = self._get_document_content(result.document_id)
        if options.include_highlights and not result.highlights:
            result.highlights = self._get_highlights(
                result.document_id, query, options.max_highlights
            )

return fused_results
```

**SearchPipeline final return pattern** (lines 180-214):
```python
# Apply candidate limit before reranking
if self.reranker is not None and len(results) > 0:
    candidates = results[: options.candidate_limit]
    try:
        reranked = self.reranker.rerank(
            parsed_query, candidates, top_k=options.limit
        )
        results = reranked
    except Exception as e:
        raise RuntimeError(f"Reranking failed: {e}")

# Extract smart snippets if not already present
if self.snippet_extractor is not None:
    for result in results:
        if result.snippet is None and result.content:
            query_terms = parsed_query.lower().split()
            result.snippet = self.snippet_extractor.extract(
                result.content, query_terms
            )

return results
```

**Critical:** `_attach_contexts()` must be called at the **final** return point of each searcher, AFTER any fusion or reranking. RRF and rerankers create brand-new `SearchResult` objects.

---

### `src/docsift/cli/main.py` (config, request-response)

**Analog:** `src/docsift/cli/main.py` (self, lines 67-87)

**Command registration pattern** (lines 67-87):
```python
# Import and register subcommands
from docsift.cli.commands.collection import collection_group
from docsift.cli.commands.context import context_group
from docsift.cli.commands.get import get_group
from docsift.cli.commands.index import index_group
from docsift.cli.commands.ls import ls_cmd
from docsift.cli.commands.mcp import mcp_group
from docsift.cli.commands.bench import bench_cmd
from docsift.cli.commands.pull import pull_cmd
from docsift.cli.commands.search import search_group


cli.add_command(collection_group)
cli.add_command(context_group)
cli.add_command(index_group)
cli.add_command(search_group)
cli.add_command(get_group)
cli.add_command(mcp_group)
cli.add_command(ls_cmd)
cli.add_command(pull_cmd)
cli.add_command(bench_cmd)
```

---

### `tests/unit/cli/test_context.py` (test, request-response)

**Analog:** `tests/unit/cli/test_collection.py` (role-match)

**Test pattern from test_hybrid.py** (lines 19-40):
```python
@pytest.fixture
def mock_db():
    """Create a mock sqlite3 connection."""
    return MagicMock()


@pytest.fixture
def sample_search_options() -> SearchOptions:
    """Create sample search options."""
    return SearchOptions(limit=10)
```

**Test pattern from test_bm25.py** (lines 9-17):
```python
class TestBM25Searcher:
    """Tests for BM25Searcher class."""

    def _make_mock_db(self, rows=None):
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = rows or []
        mock_db.execute.return_value = mock_cursor
        return mock_db
```

**CLI test pattern** — from `tests/unit/cli/test_collection_commands.py` (inferred from collection.py structure):
- Use `click.testing.CliRunner` to invoke commands
- Mock `Database` and repositories
- Assert on exit codes and output

---

### `tests/unit/database/test_schema.py` (test, migration)

**Analog:** `tests/unit/database/test_schema.py` (self, lines 33-74)

**Schema test pattern** (lines 33-52):
```python
class TestSchemaManagerVectorTables:
    def test_creates_vector_table_with_default_dimension(self, vec_db):
        manager = SchemaManager(vec_db, embedding_dim=384)
        manager._create_vector_tables()
        cursor = vec_db.execute(
            "SELECT sql FROM sqlite_master WHERE name='document_embeddings'"
        )
        row = cursor.fetchone()
        assert row is not None
        assert "FLOAT[384]" in row[0]
```

**In-memory DB fixture pattern** (lines 22-30):
```python
@pytest.fixture
def vec_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        if not _load_vec(conn):
            pytest.skip("sqlite-vec not available")
        yield conn
    finally:
        conn.close()
```

## Shared Patterns

### Click CLI Error Handling
**Source:** `src/docsift/cli/commands/context.py` (lines 51-52, 87-88)
**Apply to:** All CLI command files
```python
if not coll:
    raise click.ClickException(f"Collection '{collection}' not found")
```

### Database Transaction Pattern
**Source:** `src/docsift/cli/commands/context.py` (lines 42-70)
**Apply to:** All CLI command files
```python
index_path = ctx.obj["index_path"]
db = Database(index_path)
db.init_schema()

with db.transaction() as conn:
    repo = PathContextRepository(conn)
    # ... operations ...
```

### Repository Row Mapping Pattern
**Source:** `src/docsift/database/repositories.py` (lines 425-434)
**Apply to:** All repository classes
```python
def _row_to_context(self, row: sqlite3.Row) -> PathContext:
    """Convert database row to PathContext."""
    return PathContext(
        id=row["id"],
        path=row["path"],
        collection_id=row["collection_id"],
        context=row["context"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )
```

### SearchResult Construction Pattern
**Source:** `src/docsift/search/bm25.py` (lines 65-82), `src/docsift/search/vector.py` (lines 88-100)
**Apply to:** All search strategy files
```python
result = SearchResult(
    document_id=row["document_id"],
    title=row["title"] or "",
    path=row["path"],
    collection_name=row["collection_name"],
    score=score,
    rank=rank,
)
```

### Reranker SearchResult Reconstruction Pattern
**Source:** `src/docsift/search/rerank.py` (lines 97-108, 178-189)
**Apply to:** When adding fields to SearchResult, must also update rerankers
```python
new_result = SearchResult(
    document_id=result.document_id,
    title=result.title,
    path=result.path,
    collection_name=result.collection_name,
    score=score,
    content=result.content,
    highlights=result.highlights,
    rank=rank,
    scores=new_scores,
    snippet=result.snippet,
)
```

### RRF SearchResult Reconstruction Pattern
**Source:** `src/docsift/search/rrf.py` (lines 67-78, 151-162)
**Apply to:** When adding fields to SearchResult
```python
new_result = SearchResult(
    document_id=result.document_id,
    title=result.title,
    path=result.path,
    collection_name=result.collection_name,
    score=rrf_score,
    content=result.content,
    highlights=result.highlights,
    rank=rank,
    scores=doc_scores,
)
```

## No Analog Found

No files in this phase lack an analog. All files have strong matches in the existing codebase.

## Metadata

**Analog search scope:**
- `src/docsift/cli/commands/` — CLI command patterns
- `src/docsift/database/` — Schema and repository patterns
- `src/docsift/core/` — Domain model patterns
- `src/docsift/search/` — Search strategy patterns
- `tests/unit/` — Test patterns

**Files scanned:** 15
**Pattern extraction date:** 2026-04-18

**Key warnings for planner:**
1. **Reranker/RRF field loss:** `SearchResult.context_description` will be lost when rerankers or RRF create new `SearchResult` objects. The `_attach_contexts()` helper must be called at the **final** return point of each searcher, AFTER any fusion or reranking.
2. **Positional arg compatibility:** Add `context_description` at the **end** of `SearchResult` dataclass with `default=None`. Tests use positional args: `SearchResult("doc1", "Doc 1", "/path/1", "coll", 0.9, rank=1)`.
3. **SAVEPOINT for DDL:** SQLite's default mode auto-commits DDL. Use `SAVEPOINT` + `ROLLBACK TO SAVEPOINT` for atomic migration, not `BEGIN`/`ROLLBACK`.
4. **Two SearchResult classes:** There are two `SearchResult` definitions — `core/models.py` (dataclass, used by search strategies) and `models/search.py` (Pydantic, used by MCP/API). Both need the new field.
5. **ContextFactory bug:** `tests/factories.py` `ContextFactory.create()` passes `metadata` to `Context` dataclass, but `Context` does not have a `metadata` field. Fix when touching tests.
