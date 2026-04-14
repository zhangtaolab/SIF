# Phase 01: Foundation Fix - Pattern Map

**Mapped:** 2026-04-14
**Files analyzed:** 14
**Analogs found:** 14 / 14

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `pyproject.toml` | config | static | `pyproject.toml` (self) | exact |
| `src/docsift/database/schema.py` | service | CRUD | `src/docsift/database/schema.py` (self) | exact |
| `src/docsift/database/repositories.py` | repository | CRUD | `src/docsift/database/repositories.py` (self) | exact |
| `src/docsift/database/sqlite_repository.py` | repository | CRUD | `src/docsift/database/repositories.py` | role-match |
| `src/docsift/database/connection.py` | service | request-response | `src/docsift/database/connection.py` (self) | exact |
| `src/docsift/database/__init__.py` | config | static | `src/docsift/database/__init__.py` (self) | exact |
| `src/docsift/search/vector.py` | service | CRUD | `src/docsift/search/vector.py` (self) | exact |
| `src/docsift/search/hybrid.py` | service | CRUD | `src/docsift/search/hybrid.py` (self) | exact |
| `src/docsift/search/bm25.py` | service | CRUD | `src/docsift/search/bm25.py` (self) | exact |
| `src/docsift/embedding/factory.py` | service | transform | `src/docsift/embedding/embedder.py` | role-match |
| `src/docsift/embedding/model.py` | model | static | `src/docsift/models/embedding.py` | role-match |
| `src/docsift/cli/commands/index.py` | controller | request-response | `src/docsift/cli/commands/index.py` (self) | exact |
| `src/docsift/cli/commands/search.py` | controller | request-response | `src/docsift/cli/commands/search.py` (self) | exact |
| `src/docsift/mcp/server.py` | controller | request-response | `src/docsift/mcp/server.py` (self) | exact |
| `src/docsift/mcp/server_http.py` | controller | request-response | `src/docsift/mcp/server_http.py` (self) | exact |

## Pattern Assignments

### `pyproject.toml` (config)

**Analog:** `pyproject.toml` (existing)

**Dependencies pattern** (lines 29-50):
```toml
dependencies = [
    "click>=8.0.0",
    "rich>=13.0.0",
    "python-frontmatter>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
]
embed = [
    "sentence-transformers>=2.2.0",
    "numpy>=1.24.0",
]
all = [
    "sentence-transformers>=2.2.0",
    "numpy>=1.24.0",
]
```

**Ruff isort pattern** (lines 148-153):
```toml
[tool.ruff.lint.isort]
known-first-party = ["docsift"]
known-third-party = ["click", "rich", "sentence_transformers", "numpy"]
combine-as-imports = true
split-on-trailing-comma = true
lines-after-imports = 2
```

---

### `src/docsift/database/schema.py` (service, CRUD)

**Analog:** `src/docsift/database/schema.py` (existing)

**FTS5 table creation pattern** (lines 111-127):
```python
def _create_fts_tables(self) -> None:
    """Create FTS5 virtual tables for full-text search."""
    # Documents FTS table with external content
    self.db.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
            content,
            tokenize='porter'
        )
    """)
    
    # Chunks FTS table
    self.db.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            content,
            tokenize='porter'
        )
    """)
```

**Vector table pattern** (lines 129-157):
```python
def _create_vector_tables(self) -> None:
    """Create vector tables using sqlite-vec."""
    try:
        self.db.execute("SELECT vec_version()")
        vec_available = True
    except sqlite3.OperationalError:
        vec_available = False
    
    if vec_available:
        self.db.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS document_embeddings USING vec0(
                embedding_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                chunk_id TEXT,
                embedding FLOAT[768]
            )
        """)
```

**Schema migration / drop pattern** (lines 198-215):
```python
def drop_all(self) -> None:
    """Drop all tables (for testing/reset)."""
    tables = [
        "document_embeddings",
        "chunks_fts",
        "documents_fts",
        "document_chunks",
        "documents",
        "path_contexts",
        "llm_cache",
        "collections",
    ]
    for table in tables:
        try:
            self.db.execute(f"DROP TABLE IF EXISTS {table}")
        except sqlite3.OperationalError:
            pass
    self.db.commit()
```

---

### `src/docsift/database/repositories.py` (repository, CRUD)

**Analog:** `src/docsift/database/repositories.py` (existing)

**Repository constructor pattern** (lines 19-23, 132-136, 285-289):
```python
class CollectionRepository:
    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db
```

**CRUD create pattern** (lines 25-48):
```python
def create(self, collection: Collection) -> Collection:
    self.db.execute(
        """
        INSERT INTO collections (
            id, name, path, pattern, ignore_patterns, include_by_default,
            description, created_at, updated_at, document_count, chunk_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            collection.id,
            collection.name,
            collection.path,
            collection.pattern,
            json.dumps(collection.ignore_patterns),
            int(collection.include_by_default),
            collection.description,
            collection.created_at.isoformat(),
            collection.updated_at.isoformat(),
            collection.document_count,
            collection.chunk_count,
        )
    )
    return collection
```

**CRUD update pattern** (lines 73-98):
```python
def update(self, collection: Collection) -> Collection:
    collection.updated_at = datetime.utcnow()
    self.db.execute(
        """
        UPDATE collections SET
            name = ?, path = ?, pattern = ?, ignore_patterns = ?,
            include_by_default = ?, description = ?, updated_at = ?,
            document_count = ?, chunk_count = ?, last_indexed_at = ?
        WHERE id = ?
        """,
        (
            collection.name,
            collection.path,
            collection.pattern,
            json.dumps(collection.ignore_patterns),
            int(collection.include_by_default),
            collection.description,
            collection.updated_at.isoformat(),
            collection.document_count,
            collection.chunk_count,
            collection.last_indexed_at.isoformat() if collection.last_indexed_at else None,
            collection.id,
        )
    )
    return collection
```

**Row-to-model mapping pattern** (lines 116-129):
```python
def _row_to_collection(self, row: sqlite3.Row) -> Collection:
    return Collection(
        id=row["id"],
        name=row["name"],
        path=row["path"],
        pattern=row["pattern"],
        ignore_patterns=json.loads(row["ignore_patterns"]),
        include_by_default=bool(row["include_by_default"]),
        description=row["description"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        last_indexed_at=datetime.fromisoformat(row["last_indexed_at"]) if row["last_indexed_at"] else None,
    )
```

**DocumentChunkRepository with manual FTS sync** (lines 291-319):
```python
def create(self, chunk: DocumentChunk) -> DocumentChunk:
    self.db.execute(
        """
        INSERT INTO document_chunks (
            id, document_id, sequence, content, start_pos, end_pos,
            token_count, embedding_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (...)
    )
    
    # Also insert into FTS table
    self.db.execute(
        "INSERT INTO chunks_fts (rowid, content) VALUES (?, ?)",
        (chunk.id, chunk.content)
    )
    
    return chunk
```

---

### `src/docsift/database/sqlite_repository.py` (repository, CRUD) - TO BE DELETED

**Analog:** `src/docsift/database/repositories.py`

This file is stale, completely unused, and has an incompatible schema (e.g., `collections.paths` instead of `collections.path`/`pattern`). No patterns should be copied from it. Simply delete it per D-02.

---

### `src/docsift/database/connection.py` (service, request-response)

**Analog:** `src/docsift/database/connection.py` (existing)

**Connection-per-request pattern** (lines 22-57):
```python
class DatabaseConnection:
    def __init__(self, db_path: Path | str) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _create_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return conn
    
    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        conn = self._create_connection()
        try:
            yield conn
        finally:
            conn.close()
    
    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        conn = self._create_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
```

---

### `src/docsift/database/__init__.py` (config, static)

**Analog:** `src/docsift/database/__init__.py` (existing)

**Package export pattern** (lines 11-30):
```python
from docsift.database.connection import DatabaseConnection, ConnectionPool
from docsift.database.repository import (
    Repository,
    CollectionRepository,
    DocumentRepository,
    ContextRepository,
    SearchRepository,
)
from docsift.database.migrations import MigrationManager

__all__ = [
    "DatabaseConnection",
    "ConnectionPool",
    "Repository",
    "CollectionRepository",
    "DocumentRepository",
    "ContextRepository",
    "SearchRepository",
    "MigrationManager",
]
```

**Note:** This file currently imports from `docsift.database.repository` (singular), which is a stale module. After consolidation, it should export from `docsift.database.repositories` (plural).

---

### `src/docsift/search/vector.py` (service, CRUD)

**Analog:** `src/docsift/search/vector.py` (existing)

**sqlite-vec search pattern** (lines 42-101):
```python
def _search_with_vec(
    self,
    query_embedding: List[float],
    options: SearchOptions,
) -> List[SearchResult]:
    embedding_str = self._embedding_to_vec(query_embedding)
    
    collection_filter = ""
    params = [embedding_str]
    
    if options.collection_ids:
        placeholders = ", ".join(["?"] * len(options.collection_ids))
        collection_filter = f"AND d.collection_id IN ({placeholders})"
        params.extend(options.collection_ids)
    
    sql = f"""
        SELECT 
            d.id as document_id,
            d.title,
            d.path,
            c.name as collection_name,
            distance as score
        FROM document_embeddings de
        JOIN documents d ON de.document_id = d.id
        JOIN collections c ON d.collection_id = c.id
        WHERE embedding MATCH ? {collection_filter}
        ORDER BY distance
        LIMIT ? OFFSET ?
    """
    params.extend([options.limit, options.offset])
    
    cursor = self.db.execute(sql, params)
    results = []
    
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
        results.append(result)
    
    return results
```

**Fallback to remove** (lines 103-157): `_search_fallback()` and `_cosine_similarity()` must be deleted entirely per D-06/D-07.

**Add embedding pattern** (lines 192-222):
```python
def _add_embedding_vec(
    self,
    embedding_id: str,
    document_id: str,
    chunk_id: Optional[str],
    embedding: List[float],
) -> None:
    embedding_str = self._embedding_to_vec(embedding)
    
    self.db.execute(
        """
        INSERT OR REPLACE INTO document_embeddings 
        (embedding_id, document_id, chunk_id, embedding)
        VALUES (?, ?, ?, vec_f32(?))
        """,
        (embedding_id, document_id, chunk_id, embedding_str)
    )
```

---

### `src/docsift/search/hybrid.py` (service, CRUD)

**Analog:** `src/docsift/search/hybrid.py` (existing)

**Hybrid search composition pattern** (lines 29-78):
```python
def search(
    self,
    query: str,
    options: Optional[SearchOptions] = None,
) -> List[SearchResult]:
    if options is None:
        options = SearchOptions()
    
    bm25_results = self.bm25.search(query, options)
    
    vector_results: List[SearchResult] = []
    if self.embedder is not None:
        try:
            query_embedding = self.embedder.embed(query)
            vector_results = self.vector.search(query_embedding, options)
        except Exception as e:
            # Log error but continue with BM25 only
            print(f"Warning: Vector search failed: {e}")
    
    if not vector_results:
        return bm25_results
    if not bm25_results:
        return vector_results
    
    fused_results = self.rrf.fuse([bm25_results, vector_results], options.limit)
    return fused_results
```

**Pattern change:** Remove the `try/except` around vector search per D-07. Let vector errors propagate (fail fast).

---

### `src/docsift/search/bm25.py` (service, CRUD)

**Analog:** `src/docsift/search/bm25.py` (existing)

**FTS5 JOIN pattern (BUG)** (lines 39-53):
```python
sql = f"""
    SELECT 
        d.id as document_id,
        d.title,
        d.path,
        c.name as collection_name,
        rank as score
    FROM documents_fts fts
    JOIN documents d ON fts.rowid = d.id
    JOIN collections c ON d.collection_id = c.id
    WHERE documents_fts MATCH ? {collection_filter}
    ORDER BY rank
    LIMIT ? OFFSET ?
"""
```

**Fix:** Change `JOIN documents d ON fts.rowid = d.id` to `JOIN documents d ON fts.rowid = d.rowid`.

**Chunk search pattern** (lines 100-110):
```python
sql = """
    SELECT 
        dc.document_id,
        dc.content,
        rank as score
    FROM chunks_fts fts
    JOIN document_chunks dc ON fts.rowid = dc.id
    WHERE chunks_fts MATCH ?
    ORDER BY rank
    LIMIT ? OFFSET ?
"""
```

**Fix:** Change `JOIN document_chunks dc ON fts.rowid = dc.id` to `JOIN document_chunks dc ON fts.rowid = dc.rowid`.

---

### `src/docsift/embedding/factory.py` (service, transform)

**Analog:** `src/docsift/embedding/embedder.py`

**Factory delegation pattern** (lines 275-297 in embedder.py):
```python
def create_embedder(
    embedder_type: str = "sentence_transformer",
    **kwargs,
) -> Embedder:
    if embedder_type == "sentence_transformer":
        return SentenceTransformerEmbedder(**kwargs)
    elif embedder_type == "llama_cpp":
        return LlamaCppEmbedder(**kwargs)
    elif embedder_type == "modelscope":
        return ModelScopeEmbedder(**kwargs)
    elif embedder_type == "simple":
        return SimpleEmbedder(**kwargs)
    else:
        raise ValueError(f"Unknown embedder type: {embedder_type}")
```

**Real embedder instantiation pattern** (lines 18-55 in embedder.py):
```python
class SentenceTransformerEmbedder(Embedder):
    def __init__(
        self,
        model_name: str = "BAAI/bge-small-zh-v1.5",
        device: Optional[str] = None,
        cache_dir: Optional[str] = None,
    ) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            logger.error("sentence-transformers not installed...")
            raise
        
        if device is None:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        
        self.model = SentenceTransformer(
            model_name,
            device=device,
            cache_folder=cache_dir,
        )
        self._dimension = self.model.get_sentence_embedding_dimension()
```

**LlamaCpp embedder pattern** (lines 91-132 in embedder.py):
```python
class LlamaCppEmbedder(Embedder):
    def __init__(
        self,
        model_path: str | Path,
        n_ctx: int = 8192,
        n_threads: Optional[int] = None,
        verbose: bool = False,
    ) -> None:
        try:
            from llama_cpp import Llama
        except ImportError:
            logger.error("llama-cpp-python not installed...")
            raise
        
        self.model = Llama(
            model_path=str(model_path),
            n_ctx=n_ctx,
            n_threads=n_threads,
            embedding=True,
            verbose=verbose,
        )
        self._dimension = self.model.n_embd()
```

---

### `src/docsift/embedding/model.py` (model, static)

**Analog:** `src/docsift/models/embedding.py`

**Canonical ModelType pattern** (lines 9-15 in models/embedding.py):
```python
class ModelType(str, Enum):
    GGUF = "gguf"
    SENTENCE_TRANSFORMERS = "sentence_transformers"
    OPENAI = "openai"
    HUGGINGFACE = "huggingface"
```

**Pydantic config pattern** (lines 18-41 in models/embedding.py):
```python
class EmbeddingConfig(BaseModel):
    model_type: ModelType = Field(ModelType.GGUF, description="Model type")
    model_path: str | None = Field(None, description="Path to model file")
    model_name: str = Field("all-MiniLM-L6-v2", description="Model name or identifier")
    embedding_dim: int = Field(384, ge=1, description="Embedding dimension")
    max_tokens: int = Field(512, ge=1, description="Maximum tokens per input")
    batch_size: int = Field(32, ge=1, description="Batch size for inference")
    n_gpu_layers: int = Field(0, ge=0, description="Number of GPU layers")
    n_ctx: int = Field(2048, ge=512, description="Context size")
```

---

### `src/docsift/cli/commands/index.py` (controller, request-response)

**Analog:** `src/docsift/cli/commands/index.py` (existing)

**Checksum comparison pattern (BUG)** (lines 106-111):
```python
if existing.checksum != parsed.checksum and not force:
    console.print(f"  [dim]Unchanged: {file_path.name}[/dim]")
    progress.advance(task)
    continue
```

**Fix:** Change `!=` to `==` so unchanged documents are skipped.

**Click command pattern** (lines 31-35):
```python
@index_group.command("update")
@click.option("--collection", "-c", help="Update specific collection only")
@click.option("--force", "-f", is_flag=True, help="Force re-index all documents")
@click.pass_context
def update_cmd(ctx: click.Context, collection: str | None, force: bool) -> None:
```

**Database usage pattern** (lines 37-44):
```python
index_path = ctx.obj["index_path"]

db = Database(index_path)
db.init_schema()

with db.connection:
    coll_repo = CollectionRepository(db.connection)
    doc_repo = DocumentRepository(db.connection)
```

**Hardcoded model pattern (BUG)** (lines 183-188):
```python
embedder = SentenceTransformer("BAAI/bge-small-zh-v1.5")
```

**Fix:** Use `Settings.model_name` and accept a `--model` CLI override.

---

### `src/docsift/cli/commands/search.py` (controller, request-response)

**Analog:** `src/docsift/cli/commands/search.py` (existing)

**vsearch fallback pattern (BUG)** (lines 190-200):
```python
console.print("[yellow]Vector search requires embeddings. Run 'docsift embed' first.[/yellow]")
console.print("[dim]Falling back to BM25 search...[/dim]")

# Fall back to BM25
ctx.invoke(
    search_cmd,
    query=query,
    limit=limit,
    collection=collection,
    json=output_json,
)
```

**Fix:** Remove fallback. If vector search prerequisites are missing, raise `click.ClickException(...)`.

**Search command pattern** (lines 68-82):
```python
@search_group.command("search")
@click.argument("query")
@click.option("-n", "--limit", default=10, help="Number of results")
@click.option("-c", "--collection", multiple=True, help="Collection to search")
@click.pass_context
def search_cmd(ctx: click.Context, query: str, limit: int, collection: tuple) -> None:
    index_path = ctx.obj["index_path"]
    db = Database(index_path)
    db.init_schema()
    
    with db.connection:
        searcher = BM25Searcher(db.connection)
        results = searcher.search(query, options)
```

---

### `src/docsift/mcp/server.py` (controller, request-response)

**Analog:** `src/docsift/mcp/server.py` (existing)

**Cached Database anti-pattern (BUG)** (lines 20-28):
```python
class MCPServer:
    def __init__(self, index_path: str) -> None:
        self.index_path = index_path
        self.db: Optional[Database] = None
    
    def initialize(self) -> None:
        self.db = Database(self.index_path)
        self.db.init_schema()
```

**Fix:** Do not cache `Database` instance. Create a fresh `DatabaseConnection.connect()` per handler.

**Tool handler pattern** (lines 174-213):
```python
def _tool_query(self, request_id: Any, arguments: Dict[str, Any]) -> Dict[str, Any]:
    query = arguments.get("query", "")
    collections = arguments.get("collections", [])
    limit = arguments.get("limit", 10)
    min_score = arguments.get("min_score", 0.0)
    
    if not self.db:
        return self._error_response(request_id, -32603, "Database not initialized")
    
    from docsift.core.models import SearchOptions
    from docsift.database.repositories import CollectionRepository
    
    with self.db.connection:
        options = SearchOptions(limit=limit, min_score=min_score)
        
        if collections:
            coll_repo = CollectionRepository(self.db.connection)
            options.collection_ids = []
            for name in collections:
                coll = coll_repo.get_by_name(name)
                if coll:
                    options.collection_ids.append(coll.id)
        
        searcher = HybridSearcher(self.db.connection)
        results = searcher.search(query, options)
```

**Fix:** Replace `with self.db.connection:` with `with DatabaseConnection(self.index_path).connect() as conn:`.

**Error response pattern** (lines 384-393):
```python
def _error_response(self, request_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message,
        },
    }
```

---

### `src/docsift/mcp/server_http.py` (controller, request-response)

**Analog:** `src/docsift/mcp/server_http.py` (existing)

**FastAPI endpoint pattern** (lines 24-33):
```python
def run_http_server(index_path: str, host: str = "127.0.0.1", port: int = 3000, reload: bool = False) -> None:
    app = FastAPI(title="DocSift MCP Server")
    server = MCPServer(index_path)
    server.initialize()
    
    @app.post("/mcp/v1/messages")
    async def handle_message(request: Request) -> JSONResponse:
        body = await request.json()
        response = server.handle_request(body)
        return JSONResponse(content=response)
```

**Fix:** The `server` instance should not hold a cached DB. Either refactor `MCPServer` to be stateless or instantiate a new connection inside `handle_message`.

---

## Shared Patterns

### SQLite Connection Safety
**Source:** `src/docsift/database/connection.py` (DatabaseConnection)
**Apply to:** MCP server (`server.py`, `server_http.py`)
```python
from docsift.database.connection import DatabaseConnection

def handle_request(db_path: str) -> None:
    conn = DatabaseConnection(db_path)
    with conn.connect() as db:
        db.execute("SELECT ...")
```

### Error Handling (CLI)
**Source:** `src/docsift/cli/commands/index.py` (lines 49-50)
**Apply to:** All CLI commands
```python
if not collections[0]:
    raise click.ClickException(f"Collection '{collection}' not found")
```

### Logging
**Source:** `src/docsift/utils/logging.py` (implied from usage)
**Apply to:** All modified modules
```python
from docsift.utils.logging import get_logger

logger = get_logger(__name__)
```

### Settings Access
**Source:** `src/docsift/config/settings.py` (lines 158-164)
**Apply to:** `cli/commands/index.py`, `embedding/factory.py`
```python
from docsift.config.settings import get_settings

settings = get_settings()
model_name = settings.model_name
```

### Import Order
**Source:** `pyproject.toml` ruff isort config
**Apply to:** All modified Python files
Order: stdlib, third-party, first-party (`docsift`). Two blank lines after imports.

## No Analog Found

None — all files to be modified have direct existing analogs in the codebase.

## Metadata

**Analog search scope:** `src/docsift/`, `pyproject.toml`
**Files scanned:** 20+
**Pattern extraction date:** 2026-04-14
