# SIF Architecture

## Overview

SIF follows a layered architecture with clean separation of concerns, designed for modularity, testability, and extensibility. The architecture is inspired by Domain-Driven Design (DDD) principles and implements several well-known design patterns.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Presentation Layer                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐  │
│  │     CLI      │  │  MCP Server  │  │      API (Future)            │  │
│  │   (Click)    │  │   (MCP)      │  │                              │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────┤
│                        Application Layer                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐  │
│  │   Collection │  │    Index     │  │        Search                │  │
│  │   Manager    │  │   Service    │  │       Service                │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────┤
│                        Domain Layer                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐  │
│  │  Collection  │  │   Document   │  │        Context               │  │
│  │   Entity     │  │   Entity     │  │       Entity                 │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────┤
│                        Infrastructure Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐   │
│  │  Repository  │  │   Embedding  │  │   Database   │  │  Search  │   │
│  │  (SQLite)    │  │    Model     │  │  Connection  │  │  Index   │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Layer Descriptions

### Presentation Layer

The presentation layer handles user interaction and external interfaces:

- **CLI**: Command-line interface built with Click and Rich for interactive output
- **MCP Server**: Model Context Protocol server for AI assistant integration
- **API (Future)**: RESTful API for programmatic access

### Application Layer

The application layer orchestrates use cases and coordinates domain operations:

- **Collection Manager**: Manages document collections (create, update, delete)
- **Index Service**: Handles document indexing and reindexing
- **Search Service**: Coordinates search operations across different strategies

### Domain Layer

The domain layer contains core business logic and entities:

- **Collection**: Represents a document collection with metadata
- **Document**: Represents an indexed document with content and metadata
- **Context**: Provides additional context for improved search relevance

### Infrastructure Layer

The infrastructure layer provides technical capabilities:

- **Repository**: Data access layer using SQLite with FTS5
- **Embedding Model**: Interface for embedding generation
- **Database Connection**: Connection management and transactions
- **Search Index**: FTS5 and vector search indices

## Design Patterns

### Repository Pattern

**Purpose**: Abstract data access layer, decouple domain logic from storage

**Location**: `sif/database/repositories.py`

```python
class Repository(ABC, Generic[T]):
    @abstractmethod
    def get_by_id(self, entity_id: str) -> T | None: ...

    @abstractmethod
    def create(self, entity: T) -> T: ...

    @abstractmethod
    def update(self, entity: T) -> T: ...

    @abstractmethod
    def delete(self, entity_id: str) -> bool: ...
```

**Benefits**:
- Decouples domain logic from data storage
- Enables easy testing with mock repositories
- Allows switching storage backends without changing business logic

### Strategy Pattern

**Purpose**: Pluggable search algorithms that can be used interchangeably

**Location**: `sif/search/bm25.py`, `sif/search/vector.py`, `sif/search/hybrid.py`

**Implementations**:
- `BM25Searcher`: Full-text search via SQLite FTS5
- `VectorSearcher`: Semantic search via sqlite-vec
- `HybridSearcher`: Combined BM25 + Vector with RRF fusion
- `SearchPipeline`: Adds query expansion, reranking, snippet extraction

**Benefits**:
- Easy to add new search algorithms
- Can switch strategies at runtime
- Each strategy is independently testable

### Factory Pattern

**Purpose**: Create embedding model instances based on configuration

**Location**: `sif/embedding/factory.py`

```python
class EmbeddingModelFactory:
    def create_model(
        self,
        model_type: ModelType,
        model_path: str | None,
        model_name: str,
        **kwargs: Any,
    ) -> Embedder: ...
```

**Supported Models**:
- GGUF models via llama-cpp-python
- Sentence Transformers
- OpenAI-compatible API
- ModelScope models

### Dependency Injection

**Purpose**: Manage dependencies and enable testing

**Example**: `CollectionManager` receives `CollectionRepository` in constructor:

```python
class CollectionManager:
    def __init__(self, repository: CollectionRepository) -> None:
        self._repository = repository
```

**Benefits**:
- Loose coupling between components
- Easy to mock dependencies in tests
- Clear dependency graph

## Data Flow

### Indexing Flow

```
1. User: sif collection add ~/notes --name my-collection
   │
   ▼
2. CLI: Parse command, validate inputs
   │
   ▼
3. CollectionManager: Create/update collection
   │
   ▼
4. FileScanner: Scan directory for markdown files
   │
   ▼
5. MarkdownParser: Parse each file, extract metadata
   │
   ▼
6. Chunker: Split content into chunks
   │
   ▼
7. EmbeddingModel: Generate embeddings for chunks
   │
   ▼
8. Repository: Store documents, chunks, embeddings
   │
   ▼
9. FTS Index: Update full-text search index
   │
   ▼
10. Vector Index: Update vector search index
```

### Search Flow

```
1. User: sif search query "machine learning"
   │
   ▼
2. CLI: Parse query, build SearchQuery
   │
   ▼
3. SearchPipeline: Select search strategy via prefix routing
   │
   ▼
4. QueryExpansion (optional): Expand query
   │
   ▼
5. BM25Searcher: Search FTS index
   │
   ▼
6. VectorSearcher: Search vector index
   │
   ▼
7. HybridSearcher: Combine results (RRF)
   │
   ▼
8. Reranker (optional): Rerank results
   │
   ▼
9. SmartSnippetExtractor: Extract relevant snippets
   │
   ▼
10. Repository: Fetch document details
   │
   ▼
11. CLI: Format and display results
```

## Module Structure

```
sif/
├── __init__.py              # Package exports
├── _version.py              # Version information
├── core/                    # Domain entities and business logic
│   ├── __init__.py
│   ├── models.py            # Domain entities (Collection, Document, PathContext, SearchResult, etc.)
│   ├── collection.py        # Collection entity
│   ├── document.py          # Document and DocumentChunk entities
│   └── context.py           # Context entity
├── models/                  # Pydantic models for validation
│   ├── __init__.py
│   ├── collection.py        # Collection request/response models
│   ├── document.py          # Document request/response models
│   ├── context.py           # Context request/response models
│   ├── search.py            # Search query and result models
│   ├── embedding.py         # Embedding configuration models
│   └── download.py          # Model download from ModelScope
├── database/                # Data access layer
│   ├── __init__.py
│   ├── database.py          # Database class with schema init
│   ├── schema.py            # SchemaManager
│   ├── repositories.py      # Repository implementations
│   ├── repository.py        # Abstract repository interfaces
│   ├── connection.py        # DatabaseConnection
│   └── migrations.py        # Database migrations
├── search/                  # Search functionality
│   ├── __init__.py
│   ├── strategy.py          # Search strategy interface
│   ├── bm25.py              # BM25Searcher
│   ├── vector.py            # VectorSearcher
│   ├── hybrid.py            # HybridSearcher, SearchPipeline
│   ├── rrf.py               # RRFFusion
│   ├── expansion.py         # QueryExpansion
│   ├── rerank.py            # Reranker implementations
│   ├── snippets.py          # SmartSnippetExtractor
│   ├── context_attach.py    # Path-context attachment for search results
│   ├── term_match.py        # Shared stem-tolerant term matching
│   └── benchmark.py         # SearchEvaluator
├── indexing/                # Document indexing
│   ├── __init__.py
│   ├── scanner.py           # File system scanning
│   ├── parser.py            # Markdown parsing
│   ├── chunker.py           # Document chunking
│   ├── indexer.py           # Index orchestration
│   └── watcher.py           # File system watcher for auto-indexing
├── embedding/               # Embedding generation
│   ├── __init__.py
│   ├── manager.py           # EmbeddingManager
│   ├── factory.py           # EmbeddingModelFactory
│   ├── model.py             # Embedding model interface
│   ├── embedder.py          # Embedding model implementations
│   └── cache.py             # Embedding cache
├── mcp/                     # Unified MCP server
│   ├── __init__.py
│   ├── server.py            # MCPServer
│   ├── backend.py           # SearchBackend for tool handlers
│   ├── handlers.py          # ToolHandler implementations
│   ├── protocol.py          # MCP protocol (JSON-RPC 2.0) definitions
│   ├── cli.py               # MCP server CLI helpers
│   └── transports/          # Transport implementations
│       ├── __init__.py
│       ├── stdio.py         # StdioTransport
│       └── http.py          # HTTPTransport (streamable HTTP)
├── cli/                     # Command-line interface
│   ├── __init__.py
│   ├── main.py              # CLI entry point
│   ├── formatters.py        # Output formatters
│   └── commands/            # CLI command implementations
│       ├── __init__.py
│       ├── collection.py    # Collection commands
│       ├── context.py       # Context commands
│       ├── get.py           # get group (get, multi-get)
│       ├── index.py         # Index commands
│       ├── search.py        # Search commands
│       ├── mcp.py           # MCP commands
│       ├── ls.py            # List command
│       ├── bench.py         # Benchmark command
│       └── pull.py          # Pull command
├── config/                  # Application configuration
│   ├── __init__.py
│   ├── constants.py         # Application constants and defaults
│   └── settings.py          # Pydantic Settings
└── utils/                   # Utilities
    ├── __init__.py
    ├── logging.py           # Logging setup
    ├── paths.py             # Path utilities
    ├── progress.py          # Progress tracking
    └── text.py              # Text processing utilities
```

## Module Dependency Graph

```mermaid
graph TD

    cli[CLI<br/>(Click)]
    config[Config<br/>(Settings)]
    core[Core<br/>(Domain Models)]
    database[Database<br/>(SQLite)]
    embedding[Embedding<br/>(Models)]
    indexing[Indexing<br/>(Pipeline)]
    mcp[MCP<br/>(Server)]
    models[Models<br/>(Pydantic)]
    search[Search<br/>(Strategies)]
    utils[Utils<br/>(Helpers)]

    cli --> config
    cli --> core
    cli --> database
    cli --> embedding
    cli --> indexing
    cli --> mcp
    cli --> search
    cli --> utils
    database --> config
    database --> core
    database --> utils
    embedding --> config
    embedding --> core
    embedding --> models
    embedding --> utils
    indexing --> core
    indexing --> database
    indexing --> embedding
    indexing --> utils
    mcp --> config
    mcp --> core
    mcp --> database
    mcp --> embedding
    mcp --> search
    mcp --> utils
    models --> utils
    search --> core
    search --> embedding
    search --> models
    search --> utils
    utils --> config
```

_Generated by `scripts/generate_arch_diagram.py` from actual source imports._

## Database Schema

### Collections Table

```sql
CREATE TABLE collections (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    path TEXT NOT NULL,
    pattern TEXT DEFAULT '**/*.md',
    ignore_patterns TEXT DEFAULT '[]',
    include_by_default INTEGER DEFAULT 1,
    description TEXT,
    pre_update_cmd TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_indexed_at TEXT,
    document_count INTEGER DEFAULT 0,
    chunk_count INTEGER DEFAULT 0
);
```

### Documents Table

```sql
CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    collection_id TEXT NOT NULL,
    path TEXT NOT NULL,
    filename TEXT NOT NULL,
    title TEXT,
    content TEXT NOT NULL,
    checksum TEXT NOT NULL,
    file_size INTEGER DEFAULT 0,
    mtime REAL NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    metadata TEXT DEFAULT '{}',
    FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE
);
```

### Document Chunks Table

```sql
CREATE TABLE document_chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    content TEXT NOT NULL,
    start_pos INTEGER DEFAULT 0,
    end_pos INTEGER DEFAULT 0,
    token_count INTEGER DEFAULT 0,
    embedding_id TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);
```

### Contexts Table

```sql
CREATE TABLE contexts (
    id TEXT PRIMARY KEY,
    target_id TEXT NOT NULL,
    context_type TEXT NOT NULL CHECK(context_type IN ('path', 'collection', 'global')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

### FTS5 Virtual Tables

```sql
CREATE VIRTUAL TABLE documents_fts USING fts5(
    content,
    content='documents',
    content_rowid='rowid',
    tokenize='porter'
);

CREATE VIRTUAL TABLE chunks_fts USING fts5(
    content,
    content='document_chunks',
    content_rowid='rowid',
    tokenize='porter'
);
```

### sqlite-vec Vector Table

```sql
CREATE VIRTUAL TABLE document_embeddings USING vec0(
    embedding_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    chunk_id TEXT,
    embedding FLOAT[{dim}]  -- dimension from model (default: 1024)
);
```

## Key Interfaces

### Search Strategy Interface

```python
class SearchStrategy(ABC):
    @abstractmethod
    def search(
        self,
        context: SearchContext,
        options: SearchOptions,
    ) -> list[SearchResult]: ...

    @abstractmethod
    def search_batch(
        self,
        contexts: list[SearchContext],
        options: SearchOptions,
    ) -> list[list[SearchResult]]: ...
```

### Embedding Model Interface

```python
class Embedder(Protocol):
    def embed(self, text: str) -> list[float]: ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]: ...

    @property
    def dimension(self) -> int: ...
```

### Repository Protocol

```python
class CollectionRepository(Protocol):
    def get_by_id(self, collection_id: str) -> Collection | None: ...
    def get_by_name(self, name: str) -> Collection | None: ...
    def list_all(self) -> list[Collection]: ...
    def create(self, collection: Collection) -> Collection: ...
    def update(self, collection: Collection) -> Collection: ...
    def delete(self, collection_id: str) -> bool: ...
    def exists(self, name: str) -> bool: ...
```

## Performance Considerations

1. **Indexing**: Batch operations for efficient database writes
2. **Search**: Pre-computed embeddings and FTS5 indices
3. **Caching**: Embedding cache to avoid redundant computation
4. **Chunking**: Configurable chunk size for optimal retrieval
5. **Connection Pooling**: Reuse database connections

## Security Considerations

1. **Local-First**: All data stays on user's machine
2. **No External Calls**: No data sent to external services (unless using external embedding models)
3. **Path Validation**: Validate all paths before operations
4. **SQL Injection**: Use parameterized queries throughout

## Future Enhancements

1. **Real-time Watching**: File system watcher for auto-indexing (watcher.py exists but is not yet wired to any CLI/MCP surface)
2. **Plugin System**: Custom parsers and search strategies
3. **Web UI**: Browser-based search interface
4. **Query Suggestions**: Auto-complete and related queries

## Directory Structure Rationale

The package layout under `src/sif/` maps one-to-one onto the layers: every layer is a top-level package, and the import direction follows the layering — entry points (`cli/`, `mcp/`) may import anything below them, infrastructure (`database/`, `embedding/`) may import the domain, and the domain (`core/`) imports nothing from other SIF layers. The rationale for each package:

- **`core/` — dependency-free domain.** Plain `@dataclass` entities (`Collection`, `Document`, `DocumentChunk`) and `Protocol` interfaces (`Embedder`, `Reranker`, `QueryExpander` in `core/models.py`; repository protocols in `core/collection.py` and `core/document.py`) with no imports from any other SIF layer. This keeps domain logic free of I/O and framework coupling, so search and indexing code can be exercised without a database or a loaded model.
- **`config/` and `utils/` — cross-cutting foundation.** `config/` holds Pydantic `Settings` (environment variables prefixed `SIF_`, cached via `get_settings()`) and constants; `utils/` provides logging, path, progress, and text helpers and depends only on `config/`. Every other layer may use both.
- **`models/` — Pydantic boundary schemas.** Validation and serialization models (`ModelType`, `EmbeddingConfig`, request/response models, `ModelDownloader`) live apart from `core/` so domain entities stay plain dataclasses while Pydantic handles input arriving at the edges: CLI arguments, MCP tool payloads, and model configuration. This package depends only on `utils/`.
- **`database/` — infrastructure behind the repository protocols.** SQLite connection management, `SchemaManager`, migrations, and the concrete repositories. It depends on `core/` (entity types), `config/`, and `utils/` — never on `search/` or `indexing/`.
- **`embedding/` — provider isolation.** Two abstractions split the concern: the `Embedder` protocol from `core/` is what callers use, and the `EmbeddingModel` ABC in `embedding/model.py` is what providers implement. `EmbeddingModelFactory` builds instances from `ModelType` and `EmbeddingManager` loads and caches them, so switching GGUF, Sentence Transformers, OpenAI-compatible, or ModelScope backends touches only this package.
- **`search/` — strategies over the indices.** Strategies query SQLite directly (e.g., `bm25.py` uses the stdlib `sqlite3` module and imports nothing from `embedding/` or `database/` at module level). Embedding dependencies are deliberately lazy: `expansion.py` imports `EmbeddingManager` only under `TYPE_CHECKING`, and `rerank.py` defers `ModelDownloader` and its ML-library imports to call time, so BM25 search works without an embedding stack present.
- **`indexing/` — pipeline orchestration.** scanner → parser → chunker → indexer (plus `watcher.py`, reserved for auto-indexing). Besides the two entry points, it is the only layer that combines `database/` and `embedding/` in a single flow, which is why it sits above both.
- **`cli/` and `mcp/` — the two entry points.** Both sit at the top of the dependency graph: they may import every layer below them, and nothing imports them. `mcp/` is self-contained by design: `MCPServer` plus JSON-RPC 2.0 protocol handling (`server.py`, `protocol.py`), a `SearchBackend` that wires the database, repositories, embedding factory, and `SearchPipeline` together (`backend.py`), one `ToolHandler` subclass per tool (`handlers.py`), and a `transports/` subpackage (`StdioTransport`, `HTTPTransport`) so a new transport can be added without touching server logic.

Two conventions reinforce the layout. Deferred imports (marked `# noqa: PLC0415`, e.g. `get_settings()` inside `database/database.py` or `ModelDownloader` inside `search/rerank.py`) keep heavy or cycle-prone dependencies out of module import time. And sibling layers never import each other sideways — `search/` does not import `indexing/`, `database/` does not import `embedding/` — so each layer can be understood and replaced in isolation.

## Connection Management

Two connection wrappers cover the two entry-point lifetimes, and repositories are deliberately agnostic of both: every repository takes a raw `sqlite3.Connection`, so either wrapper can host the same repository code.

### Database (command-scoped)

`Database` (`sif/database/database.py`) holds one lazily created connection for the lifetime of the object. The connection opens on first access with `sqlite3.Row` rows, `PRAGMA foreign_keys = ON`, and sqlite-vec loaded best-effort, and is released by `close()` or the context-manager protocol. Every CLI command that touches the index follows the same pattern — `with Database(index_path) as db:` — so a connection never outlives the command that opened it.

### DatabaseConnection (per-operation)

`DatabaseConnection` (`sif/database/connection.py`, re-exported from `sif.database`) opens a fresh connection per operation: `connect()` and `transaction()` are context managers that close the connection in a `finally`, and the convenience methods (`execute`, `executemany`, `fetchone`, `fetchall`) wrap single statements the same way. The MCP server uses this wrapper exclusively — `SearchBackend._run_in_db()` executes each tool call inside `DatabaseConnection(...).transaction()` on an `asyncio.to_thread` worker, so the event loop is never blocked and connections are never shared across threads. The MCP server does not create schema; it relies on the database already existing (created by the CLI).

### ConnectionPool

`ConnectionPool` (`sif/database/connection.py`) is a small idle-connection pool (default capacity 5) intended for read-heavy workloads; writes are expected to go through a single connection to avoid SQLite locking. Both wrappers set `check_same_thread=False` so work can move onto threads — safety comes from the ownership discipline above, not from locking.

## Schema Management and Evolution

There is no versioned migration runner on the active path. `SchemaManager.create_all()` (`sif/database/schema.py`) is idempotent, and each CLI command invokes it via `db.init_schema()` right after opening the database. Besides `CREATE ... IF NOT EXISTS`, it adapts older layouts in place:

- **Column additions**: `_add_column_if_missing()` inspects `PRAGMA table_info` and issues `ALTER TABLE` when needed (e.g. the `pre_update_cmd` column on `collections`).
- **Table merges**: legacy `path_contexts` rows are folded into the unified `contexts` table inside a savepoint (`SAVEPOINT sp_migration`) that rolls back atomically on failure.
- **FTS repair**: external-content FTS5 tables must be maintained through the documented `'delete'`-command trigger form. `CREATE TRIGGER IF NOT EXISTS` cannot replace an existing broken trigger, so triggers whose `sqlite_master` SQL writes directly to the FTS tables are dropped and recreated; when a legacy direct-DELETE trigger is detected, the index is rebuilt (`INSERT INTO documents_fts(documents_fts) VALUES('rebuild')`) to purge entries orphaned by past deletes. FTS tables with a misconfigured `content=` setting are dropped and recreated.
- **Dimension guard**: before creating `document_embeddings`, the existing `FLOAT[dim]` declaration is compared with `settings.embedding_dim`; a mismatch raises `RuntimeError` (rebuild via `sif cleanup` or delete the database file) instead of silently corrupting vector search.
- **Optional vector support**: if the sqlite-vec extension is unavailable (`SELECT vec_version()` fails), vector tables are skipped and BM25 keeps working.

`MigrationManager` (`sif/database/migrations.py`, a `schema_version`-table approach) predates this layout and is no longer on the runtime path — `SchemaManager` owns schema creation and evolution.

## Caching

Two independent SQLite-backed caches keep expensive computation off the hot path:

- **Embedding cache** (`sif/embedding/cache.py`): stores embeddings in a separate database (`embeddings_cache.db`) under the cache directory (`Settings.get_cache_dir()`, the platformdirs user cache dir, overridable via `SIF_CACHE_DIR`). Entries are keyed `(SHA-256 content hash, model_id)` with vectors serialized as JSON, so cached embeddings survive restarts and models never read each other's vectors; a cache written before per-model keying existed is detected and rebuilt on first open. Enabled by the `cache_embeddings` setting; `EmbeddingManager` owns the cache and consults it around embed calls, bucketing entries by a model identifier of the form `{model_type}:{model_name}` (suffixed with the API base when one is configured).
- **LLM cache** (`llm_cache` table, `LLMCacheRepository` in `sif/database/repositories.py`): caches LLM responses keyed `(model_name, prompt_hash)` with an optional `expires_at` TTL and a lookup index on the key pair. Expired rows are purged by `sif cleanup`.

## Context System

Contexts are user-authored descriptions attached to paths or collections (or globally); they enrich results at read time rather than influencing indexing.

- **Storage**: the unified `contexts` table (see Database Schema), with `context_type` restricted by CHECK constraint to `path`, `collection`, and `global`.
- **Domain model**: `sif/core/context.py` defines the `Context` entity, the `ContextType` enum, the `ContextRepository` protocol, and `ContextManager`, a domain service whose `build_search_context()` aggregates global, collection, and path-prefix contexts into a single string. The concrete `ContextRepository` (`sif/database/repositories.py`) persists `PathContext` records (`sif/core/models.py`) and includes a self-heal path: re-adding a path whose legacy row still holds the verbatim pre-normalization spelling re-points that row to the canonical form instead of duplicating it.
- **Path matching contract**: `normalize_path` (`sif/utils/paths.py`) is the single canonical definition of "same file", shared by the CLI (`context add`, `get`), the MCP backend, repositories, and search-time attachment. It expands `~` and resolves symlinks (e.g. `/tmp` → `/private/tmp` on macOS) while preserving non-existent tail components, and degrades to the raw string when a stored path cannot be resolved — a malformed row matches nothing rather than crashing search.
- **Search-time attachment**: `attach_path_contexts` (`sif/search/context_attach.py`) is the shared final step of all three searchers (`BM25Searcher`, `VectorSearcher`, `HybridSearcher`). It runs one constant batch query over path-type contexts and matches in Python by normalizing both sides — necessary because `contexts.target_id` stores the verbatim user-typed path while `documents.path` stores the resolved path, and since realpath is not invertible no exact-match SQL pre-filter can bridge the two. Rows are read in `updated_at` order so the newest context wins a normalization collision, and `context_description` is only set on a match — a description already carried through fusion or reranking is never clobbered.

## Error Handling

The error strategy is fail fast at construction, degrade gracefully in optional pipelines, and translate at the edges:

- **CLI boundary**: commands catch exceptions and re-raise as `click.ClickException(str(e))`, so Click prints a clean message and exits non-zero.
- **Transactions**: `Database.transaction()` and `DatabaseConnection.transaction()` commit on success and roll back with a re-raise on any exception — repository failures never leave partial writes.
- **Fail fast**: `VectorSearcher.__init__` raises `RuntimeError` when the sqlite-vec extension is missing rather than returning empty vector results; `SchemaManager` raises on embedding-dimension mismatch; `SearchPipeline` raises on reranking failure and on vector/HyDE search without an embedder. In `HybridSearcher.search()`, embedder and vector exceptions propagate uncaught — BM25-only results are returned only when vector search yields zero results, which is a no-results path, not failure handling.
- **Degrade gracefully**: optional stages log and continue — query-expansion failures are logged at warning level and search proceeds with the original query; the MCP `SearchBackend` logs a warning and serves BM25-only when the embedder fails to load; `Database` loads sqlite-vec best-effort so the database opens even without it.
