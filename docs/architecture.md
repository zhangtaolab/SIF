<!-- generated-by: gsd-doc-writer -->
# SIF Architecture

## System Overview

SIF (DocSIF) is a local-first hybrid search engine for personal knowledge bases: it indexes Markdown notes and other text documents into one SQLite index database, then answers free-text queries with BM25 keyword search (SQLite FTS5), semantic vector search (sqlite-vec), or RRF-fused hybrid ranking. Its primary inputs are local files registered as named collections, optional user-authored contexts (path descriptions that enrich results at search time, plus collection and global descriptions that are stored and listed but not applied to results), and a configured embedding model; its primary outputs are ranked search results with snippets and attached context descriptions, served through two front ends — a Click CLI (`sif`) and an MCP server exposing the `query`, `get`, `multi_get`, and `status` tools over stdio or streamable HTTP transports. A live-indexing component, `sif watch`, keeps the index fresh as files change (foreground, detached daemon, OS service, or an opt-in watcher embedded in the MCP server). The architectural style is layered with protocol-based seams (see the component diagram and dependency graph below): the domain package defines the `Embedder` protocol and the repository protocols that infrastructure implements, `Chunker` (`sif/indexing/chunker.py`) is an ABC local to the layer that uses it, the index lives in one SQLite file (`sif.db`) with an optional separate embedding-cache database and model files on disk, and everything runs locally with no server dependency beyond optional external embedding APIs.

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Entry points                                                             │
│   CLI (Click + Rich)                    MCP server (JSON-RPC 2.0)        │
│   sif <command>                         stdio | streamable HTTP          │
├──────────────────────────────────────────────────────────────────────────┤
│ Orchestration                                                            │
│   SearchPipeline                        IncrementalIndexer + FileWatcher │
│   prefix routing, expansion, hybrid     one per-file update loop;        │
│   RRF, rerank, snippets, drift refresh  watch hosts (CLI/daemon/service, │
│                                         MCP) drive it                    │
├──────────────────────────────────────────────────────────────────────────┤
│ Domain                                                                   │
│   core                                  models                           │
│   entities, protocol seams, domain      Pydantic boundary schemas        │
│   services (CollectionManager, ...)                                      │
├──────────────────────────────────────────────────────────────────────────┤
│ Infrastructure                                                           │
│   database        embedding        config            utils               │
│   connection      factory,         Pydantic          logging, paths,     │
│   factory, lock,  manager,         Settings          progress, daemon,   │
│   schema, repos,  identity,                          service             │
│   maintenance     prompts, roles,                                        │
│                   embedders, cache                                       │
└──────────────────────────────────────────────────────────────────────────┘
```

## Layer Descriptions

### Entry Points

Both entry points sit at the top of the dependency graph and are never imported by lower layers:

- **CLI**: Click commands with Rich console output. The groups are `collection`, `context`, `index`, `search`, `get`, and `mcp`, plus the top-level `ls`, `pull`, `bench`, `suggest`, `watch`, `status`, and `cleanup` commands.
- **MCP server**: `MCPServer` (`sif/mcp/server.py`) handles JSON-RPC 2.0 requests and notifications over pluggable transports — `StdioTransport` and a FastAPI-based streamable HTTP transport. One `ToolHandler` subclass per tool (`query`, `get`, `multi_get`, `status`) delegates to `SearchBackend`, which wires the database, repositories, embedding factory, and `SearchPipeline` together per call. With `SIF_MCP_WATCH=1`, the server also starts an embedded `FileWatcher` via `sif/mcp/watch_host.py`.

### Orchestration

- **`SearchPipeline`** (`sif/search/hybrid.py`): parses query prefixes (`lex:`, `vec:`, `hyde:`, `expand:`, default hybrid), optionally expands the query, runs `HybridSearcher` (BM25 + vector + `RRFFusion`), optionally reranks, extracts snippets, and attaches contexts and vector-staleness markers. It also evaluates the injected embedder-identity check once per instance, and only on vector-touching exits (see [Embedder Identity and Vector-Space Enforcement](#embedder-identity-and-vector-space-enforcement)).
- **`StreamingEmbedWriter`** (`sif/indexing/embed_writer.py`): the single chunk → embed → persist pipeline. It chunks one document, embeds in bounded batches **outside any transaction**, validates each batch (`validate_batch`), then commits the document's chunks, vectors, `embedded_documents` shadow row, and (on the index's first vector write) its embedder identity in one short `with conn:` block. `sif index embed` and the watcher's embed leg both route through it, so completeness, sanity, and shadow maintenance cannot diverge.
- **`IncrementalIndexer`** (`sif/indexing/incremental.py`): the single per-file update loop shared by every host — `sif index update` delegates to it, and the watch hosts drive it as events arrive. It scans, parses, writes or updates document rows (purging stale chunks and embeddings on update), and commits each file as one short `BEGIN IMMEDIATE` transaction.
- **`FileWatcher`** (`sif/indexing/watcher.py`): host-agnostic observer → debouncer → worker pipeline for live indexing. It imports no UI; hosts pass rendering callbacks. Its `_EmbedSession` adopts/checks the embedder identity at first embed use and delegates each path to `StreamingEmbedWriter`.
- **Pre-search drift** (`sif/indexing/drift.py`): stat-walks searched collections and performs a bounded, BM25-only refresh before the CLI search trio runs.

### Domain

- **`core/`**: plain `@dataclass` entities (`Collection`, `Document`, `DocumentChunk`, `SearchResult`, `SearchOptions`, `PathContext`, `QueryLogEntry`, `IndexStats`) and the protocol seams (`Embedder`, plus repository protocols; `Reranker` and `QueryExpander` are defined here but no production code imports them). Domain services such as `CollectionManager` and `ContextManager` also live here.
- **`models/`**: Pydantic models for data arriving at the edges — request/response and search schemas, embedding configuration, and ModelScope model downloads. CLI arguments are Click parameters and MCP tool payloads are defined in `sif/mcp/protocol.py`, so neither entry point imports this package.

### Infrastructure

- **`database/`**: the shared connection factory, per-database index write lock, `SchemaManager`, `Database` and `DatabaseConnection` wrappers, abstract repository interfaces, and the concrete SQLite repositories. `maintenance.py` owns the destructive operations (`vacuum_index`, `backup_index`) and the derived-shadow repair (`reconcile_embedded_documents`); it opens its own connection, runs outside `Database.transaction()`, and leaves locking/error translation to the CLI host. It never imports `search/` or `indexing/`.
- **`embedding/`**: `EmbeddingModelFactory` creates an `Embedder` per `ModelType`; `EmbeddingManager` lazy-loads and caches the model and fronts the embedding cache. `identity.py` owns the persisted `embedder.identity` record, its deterministic fingerprint, the single `FLOAT[n]` schema read, and the mode-aware `check_identity(init|embed|search)`; `prompts.py` resolves the effective query/document prompt scheme (Settings override plus a small known-model table); `roles.py` dispatches `embed_query`/`embed_queries`/`embed_documents` to concrete role methods and falls back to `embed`/`embed_batch` for protocol-only doubles.
- **`config/` and `utils/`**: cross-cutting foundation. `config/` holds Pydantic `Settings` (environment variables prefixed `SIF_`, cached via `get_settings()`); `utils/` provides logging, path, progress, text, daemon, and service helpers.

## Design Patterns

### Repository Pattern

**Purpose**: Abstract data access layer, decouple domain logic from storage

**Location**: `sif/database/repository.py` (abstract interfaces) and `sif/database/repositories.py` (concrete SQLite implementations). The domain also declares consumer-facing protocols in `sif/core/collection.py`, `sif/core/document.py`, and `sif/core/context.py`.

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
- `SearchPipeline`: Adds prefix routing, query expansion, reranking, snippet extraction, and context/staleness attachment

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
- Sentence Transformers (`SentenceTransformerEmbedder`)
- OpenAI-compatible API
- ModelScope models

`ModelType.HUGGINGFACE` is a recognized enum value, but `_create_huggingface_model()` raises `NotImplementedError`; the `model_type` settings validator deliberately rejects it, so it cannot be selected through configuration.

**Benefits**:
- Provider-specific imports and model loading stay isolated in one package
- New backends plug in without touching search or indexing code
- Tests can substitute a fake `Embedder`

### Dependency Injection

**Purpose**: Manage dependencies and enable testing

**Example**: `CollectionManager` receives `CollectionRepository` in its constructor (`sif/core/collection.py`):

```python
class CollectionManager:
    def __init__(self, repository: CollectionRepository) -> None:
        self._repository = repository
```

CLI command functions typically construct the concrete repositories directly over the command's shared connection (for example `CollectionRepository(db.connection)`), which keeps the wiring explicit and testable through the same constructor seam.

**Benefits**:
- Loose coupling between components
- Easy to mock dependencies in tests
- Clear dependency graph

## Data Flow

### Indexing Flow

Indexing is split into two stages: `sif index update` builds the BM25/FTS side, and `sif index embed` adds vectors. Registering a collection does not read any files.

```
1. User: sif collection add ~/notes --name my-collection
   │
   ▼
2. CLI: Validate path, write the collection row (path, pattern, ignore patterns)
   │
   ▼
3. User: sif index update [-c NAME] [--force]
   │
   ▼
4. open_initialized_database(): construct Database and run SchemaManager.create_all()
   │
   ▼
5. index_lock(): hold the per-database flock for the write pass
   │
   ▼
6. IncrementalIndexer.update_collection()
   │
   ▼
7. FileScanner: scan the collection root with the shared membership predicate
   │
   ▼
8. MarkdownParser: parse changed files (checksum skip unless --force)
   │
   ▼
9. DocumentRepository: write the document row; an update also purges its
   │  stale chunks and embeddings (one short BEGIN IMMEDIATE transaction per file)
   ▼
10. FTS triggers: keep documents_fts synchronized for document-level BM25
   │
   ▼
11. User: sif index embed [-c NAME] [--force] [--chunk-strategy ...]
   │
   ▼
12. EmbeddingManager: load the configured model (loaded up front here and cached)
   │  resolve the effective prompt scheme; compare the persisted identity
   │  (init/embed mode) before any vector write; a legacy populated index is
   │  assumed once, a same-width model swap fails fast
   ▼
13. StreamingEmbedWriter, per document: chunk (dropping empty/whitespace text),
   │  embed in settings.batch_size batches OUTSIDE any transaction, validate
   │  count/dimension/finiteness/L2 norm per batch
   ▼
14. One short `with conn:` per document: delete-before-insert chunks, vectors
    (which maintain the embedded_documents shadow in the same transaction),
    collection stats, and — on the index's first vector write — the identity
    row. A mid-run failure keeps every prior document committed and resumable.
```

The watch hosts run steps 7–10 continuously as filesystem events settle, and optionally run the embed leg when started with `--embed` (or `SIF_WATCH_UPDATE_DEPTH=embed`).

### Search Flow

```
1. User: sif search query "machine learning"      (hybrid, default)
   or:   sif search search "machine learning"     (BM25 only)
   or:   sif search vsearch "machine learning"    (vector only)
   │
   ▼
2. CLI: optional pre-search drift check (--no-refresh disables)
   │  stat-walk collections; bounded BM25 refresh under the cap
   ▼
3. SearchPipeline.search(): parse query prefix
   │  lex: -> BM25, vec: -> vector, hyde: -> HyDE,
   │  expand: -> hybrid + expansion, default -> hybrid
   │  evaluate the injected embedder-identity check once, only on a
   │  vector-touching route (BM25 is check-free)
   ▼
4. QueryExpansion (optional): produce query variants
   │  query and candidate legs embed through the query role
   ▼
5. HybridSearcher: BM25Searcher (FTS5) + VectorSearcher (sqlite-vec)
   │  the query embeds through the query role (prompt-aware when effective)
   ▼
6. RRFFusion: fuse result lists using weighted reciprocal rank fusion
   │
   ▼
7. Reranker (optional): rerank the candidate-capped list
   │
   ▼
8. SmartSnippetExtractor: extract relevant snippets
   │
   ▼
9. attach_path_contexts + mark_vector_staleness:
   │  attach context descriptions and staleness markers; a same-dimension
   │  identity swap warns once per process and marks every row stale, while
   │  a width mismatch degrades hybrid to BM25 or refuses vec:/hyde:
   ▼
10. QueryLogRepository: record query history (when enabled)
   │
   ▼
11. CLI: format and display results (or emit --json)
```

The MCP `query` tool takes the same path without the CLI's drift check: `SearchBackend.hybrid_search()` builds a `SearchPipeline` per call on a fresh `DatabaseConnection` inside an `asyncio.to_thread` worker.

Quality is measured alongside this path rather than inside it: `sif bench` scores the committed synthetic fixture, while `sif eval --personal` (`sif/search/personal_bench.py`) synthesizes deterministic known-item queries from the user's own indexed documents and gates comparisons between saved runs on a paired-bootstrap confidence interval.

## Watch Hosts and Index Freshness

Live indexing is built on one host-agnostic core. `FileWatcher` (`sif/indexing/watcher.py`) owns the observer → debouncer → `fold_events` → worker-thread → per-burst `index_lock` → `IncrementalIndexer` pipeline. Hosts supply `on_event`/`on_batch` callbacks, so the core imports no UI. Depth is tiered: updates are BM25-only by default, and `--embed` (or `SIF_WATCH_UPDATE_DEPTH=embed`) opts into an inline embed leg. That leg adopts the embedder identity at first use (one short transaction: assume legacy, then check embed mode), delegates each changed path to the shared `StreamingEmbedWriter`, and fails soft on a mismatch — one error event, embedding disabled for the session, BM25 freshness unchanged.

Three CLI hosts share the same foreground body:

- **Foreground**: `sif watch [-c NAME] [--embed|--no-embed]`. Shutdown is signal-driven — the first SIGINT/SIGTERM runs one bounded flush plus a WAL truncate checkpoint and exits 0; a second signal exits immediately with code 130.
- **Detached daemon**: `sif watch --detach` double-forks before any thread exists and prints the armed daemon's PID; logs go to the platform log directory unless `--log-file` is given. `sif watch --stop` corroborates the PID file's identity, then escalates SIGTERM → bounded wait → SIGKILL.
- **OS service**: `sif watch --install-service` generates and installs a launchd LaunchAgent (macOS) or systemd user unit (Linux) whose argv runs the foreground command with the install-time flags baked in; `--uninstall-service` stops and removes it.

The PID file managed by `sif/utils/daemon.py` is management metadata only. Single-writer arbitration remains the per-database `index_lock` (`sif/database/locking.py`): an exclusive `fcntl.flock` on `{db_path}.lock` held for each write burst. A waiter blocks up to `lock_wait_timeout` (default 30 seconds) and then runs its own pass anyway; the kernel releases the lock on process death, so stale locks are impossible. On platforms without `fcntl`, the lock degrades to a warning and indexing runs unlocked under WAL + `busy_timeout`.

The MCP embedded host (`sif/mcp/watch_host.py`) is opt-in via `SIF_MCP_WATCH=1`. It is deliberately BM25-only regardless of ambient depth, opens its own `Database` (and initializes the schema), reconciles each collection at startup, rescopes on the collections table, and renders only through the logger because stdout is the stdio JSON-RPC channel.

Two freshness signals sit outside the watcher:

- **Pre-search drift refresh**: the CLI search trio stat-walks the requested collections via `FileScanner` before searching (`sif/indexing/drift.py`). Up to `SIF_SEARCH_REFRESH_MAX_FILES` (default 100) drifted files are re-indexed BM25-only inside one `index_lock` window; above the cap nothing is refreshed and a warning is printed. `--no-refresh` or `SIF_SEARCH_REFRESH_ENABLED=0` disables the check. `sif bench` and the MCP server bypass it by construction.
- **Vector staleness**: `sif/search/staleness.py` derives (never stores) a marker for results whose document has no row in the derived `embedded_documents` shadow. The vector writer maintains that shadow in the same transaction as every embedding write/delete, `SchemaManager` backfills it once for legacy indexes, and `sif cleanup` / `sif index vacuum` reconcile it. Markers appear only once the index holds at least one embedding, so pure-BM25 users see no nagging; the same bounded, indexed derivation backs the `sif status` vector-lag row (one `NOT EXISTS` anti-join).

## Module Structure

```
sif/
├── __init__.py              # Package exports (version, core models)
├── _version.py              # Version string
├── core/                    # Domain entities, protocols, domain services
│   ├── __init__.py
│   ├── models.py            # Dataclass entities and protocol seams (Embedder, Reranker, QueryExpander)
│   ├── collection.py        # Collection entity, CollectionRepository protocol, CollectionManager
│   ├── document.py          # DocumentMetadata, Document, DocumentChunk, DocumentRepository protocol
│   └── context.py           # Context entity, ContextType, ContextRepository protocol, ContextManager
├── models/                  # Pydantic models for validation and serialization
│   ├── __init__.py
│   ├── collection.py        # Collection request/response models
│   ├── document.py          # Document request/response models
│   ├── context.py           # Context request/response models
│   ├── embedding.py         # Embedding configuration models
│   └── download.py          # Model download from ModelScope
├── database/                # Data access layer
│   ├── __init__.py
│   ├── database.py          # Database class (command-scoped connection)
│   ├── connection.py        # DatabaseConnection (per-operation connection)
│   ├── factory.py           # Shared connection factory: pragma recipe + sqlite-vec
│   ├── locking.py           # Cross-process index write lock (fcntl.flock)
│   ├── schema.py            # SchemaManager (idempotent DDL and in-place repair)
│   ├── maintenance.py       # vacuum/backup helpers + embedded_documents reconcile
│   ├── repositories.py      # Concrete SQLite repositories (incl. LLM/query-log)
│   └── repository.py        # Abstract repository interfaces
├── search/                  # Search functionality
│   ├── __init__.py
│   ├── bm25.py              # BM25Searcher
│   ├── vector.py            # VectorSearcher, embedding purger
│   ├── hybrid.py            # HybridSearcher, SearchPipeline
│   ├── rrf.py               # RRFFusion
│   ├── expansion.py         # QueryExpansion
│   ├── rerank.py            # Reranker implementations
│   ├── snippets.py          # SmartSnippetExtractor
│   ├── context_attach.py    # Path-context attachment for search results
│   ├── staleness.py         # Derived vector-staleness markers
│   ├── term_match.py        # Shared stem-tolerant term matching
│   ├── suggest.py           # SuggestionEngine (vocabulary + query history)
│   └── benchmark.py         # SearchEvaluator
├── indexing/                # Document indexing
│   ├── __init__.py
│   ├── scanner.py           # FileScanner
│   ├── parser.py            # MarkdownParser, TextParser, CodeParser
│   ├── chunker.py           # Chunker hierarchy and create_chunker()
│   ├── embed_writer.py      # StreamingEmbedWriter: sanity + per-document commit
│   ├── incremental.py       # IncrementalIndexer: the one per-file update loop
│   ├── drift.py             # Pre-search drift detection and bounded BM25 refresh
│   └── watcher.py           # FileWatcher: observer/debouncer/worker pipeline
├── embedding/               # Embedding generation
│   ├── __init__.py
│   ├── manager.py           # EmbeddingManager
│   ├── factory.py           # EmbeddingModelFactory
│   ├── identity.py          # Persisted embedder identity + mode-aware checks
│   ├── prompts.py           # Effective query/document prompt-scheme resolver
│   ├── roles.py             # Role-aware embed dispatch with protocol fallback
│   ├── model.py             # EmbeddingModel interface
│   ├── embedder.py          # Embedding model implementations
│   └── cache.py             # Embedding cache
├── mcp/                     # Unified MCP server
│   ├── __init__.py
│   ├── server.py            # MCPServer
│   ├── backend.py           # SearchBackend for tool handlers
│   ├── handlers.py          # ToolHandler implementations
│   ├── protocol.py          # MCP protocol (JSON-RPC 2.0) definitions
│   ├── cli.py               # MCP server CLI helpers
│   ├── watch_host.py        # Embedded watch host (SIF_MCP_WATCH opt-in)
│   └── transports/          # Transport implementations
│       ├── __init__.py
│       ├── stdio.py         # StdioTransport
│       └── http.py          # HTTPTransport (streamable HTTP)
├── cli/                     # Command-line interface
│   ├── __init__.py
│   ├── main.py              # CLI entry point
│   ├── formatters.py        # Output formatters
│   ├── error_handling.py    # Shared database-open/schema-init error boundary
│   └── commands/            # CLI command implementations
│       ├── __init__.py
│       ├── collection.py    # Collection commands
│       ├── context.py       # Context commands
│       ├── get.py           # get group (get, multi-get)
│       ├── index.py         # Index commands (update, embed, vacuum, backup, status)
│       ├── search.py        # Search commands (search, vsearch, query)
│       ├── mcp.py           # MCP commands
│       ├── ls.py            # List command
│       ├── bench.py         # Benchmark command
│       ├── pull.py          # Pull command
│       ├── suggest.py       # Suggest command
│       └── watch.py         # Watch command (foreground, daemon, service)
├── config/                  # Application configuration
│   ├── __init__.py
│   ├── constants.py         # Application constants and defaults
│   └── settings.py          # Pydantic Settings
└── utils/                   # Utilities
    ├── __init__.py
    ├── logging.py           # Logging setup
    ├── paths.py             # Path utilities and normalize_path
    ├── progress.py          # Progress tracking
    ├── text.py              # Text processing utilities
    ├── daemon.py            # Detached-daemon lifecycle and PID metadata
    └── service.py           # launchd/systemd service install/uninstall
```

## Module Dependency Graph

```mermaid
graph TD

    _version[_version]
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
    config --> _version
    database --> config
    database --> core
    database --> utils
    embedding --> config
    embedding --> core
    embedding --> database
    embedding --> models
    embedding --> utils
    indexing --> config
    indexing --> core
    indexing --> database
    indexing --> embedding
    indexing --> search
    indexing --> utils
    mcp --> _version
    mcp --> config
    mcp --> core
    mcp --> database
    mcp --> embedding
    mcp --> indexing
    mcp --> search
    mcp --> utils
    models --> utils
    search --> config
    search --> core
    search --> database
    search --> models
    search --> utils
    utils --> config
```

_Generated by `scripts/generate_arch_diagram.py` from actual source imports at the top-level package granularity. TYPE_CHECKING-only imports are excluded; deferred function-local imports are included, so a few edges represent intentional lazy seams._

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
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_indexed_at TEXT,
    document_count INTEGER DEFAULT 0,
    chunk_count INTEGER DEFAULT 0
);
```

The `pre_update_cmd` column used by `sif index update` is added by `SchemaManager._add_column_if_missing()` on first schema init, so it does not appear in the literal `CREATE TABLE` above.

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

CREATE INDEX idx_contexts_target ON contexts(target_id, context_type);
```

### LLM Cache Table

```sql
CREATE TABLE llm_cache (
    id TEXT PRIMARY KEY,
    model_name TEXT NOT NULL,
    prompt_hash TEXT NOT NULL,
    prompt TEXT NOT NULL,
    response TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT,
    UNIQUE(model_name, prompt_hash)
);

CREATE INDEX idx_llm_cache_lookup ON llm_cache(model_name, prompt_hash);
```

### Query Log Table

```sql
CREATE TABLE query_log (
    id TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    result_count INTEGER NOT NULL DEFAULT 0,
    collections TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE INDEX idx_query_log_created ON query_log(created_at DESC);
```

### Index Metadata Table

```sql
CREATE TABLE index_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

A generic key/value store for index-wide markers. Phase 20 writes `metadata_values_version` for the typed-metadata backfill; Phase 21 adds the global `embedder.identity` JSON record and the `embedded_documents_version` shadow marker. Per-collection parser/convention markers stay in the `convention:<collection_id>` namespace.

### Derived Embedded Documents Shadow

```sql
CREATE TABLE embedded_documents (
    document_id TEXT PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE
);
```

`embedded_documents` is a transactionally maintained, rebuildable shadow: a row means the document has at least one `document_embeddings` row. It is created only when sqlite-vec is available (vec0-conditional DDL), backfilled once from `document_embeddings` joined to `documents` (orphan vec0 rows never enter), maintained by `VectorSearcher` inside every embedding write/delete transaction, and repaired by `reconcile_embedded_documents` from `sif cleanup` / `sif index vacuum`. Staleness reads use it as an indexed primary-key lookup; it is never independently authoritative.

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

CREATE VIRTUAL TABLE documents_fts_v USING fts5vocab(documents_fts, 'row');
```

The two external-content FTS tables are kept synchronized with their base tables by AFTER INSERT/UPDATE/DELETE triggers using the documented `'delete'`-command form. `documents_fts_v` is the FTS5 vocabulary shadow (one row per porter-stem term with its document frequency) that feeds the suggestion engine; it is derived from the index and needs no sync maintenance.

### sqlite-vec Vector Table

```sql
CREATE VIRTUAL TABLE document_embeddings USING vec0(
    embedding_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    chunk_id TEXT,
    embedding FLOAT[{dim}]  -- dimension from SIF_EMBEDDING_DIM (default: 1024)
);
```

## Key Interfaces

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

1. **Indexing**: Per-file `BEGIN IMMEDIATE` transactions keep write locks short, make runs resumable, and let searches interleave. Embedding is streamed per document: model batches run outside every transaction, and one short transaction per document carries its chunks, vectors, shadow row, and stats, so memory is bounded by one document's chunks and a mid-run failure keeps prior work durable.
2. **Search**: Pre-computed embeddings and FTS5/vec0 indices; candidate-capped over-fetch only when a reranker is enabled; the identity check is evaluated once per pipeline instance and only on vector-touching routes, and staleness marking is one display-gate probe plus indexed shadow primary-key lookups.
3. **Caching**: Embedding cache to avoid redundant computation.
4. **Chunking**: Configurable chunk size and strategy for optimal retrieval.
5. **Connection lifecycle**: One reused connection per CLI command, fresh per-operation connections in the MCP server, WAL journaling plus `busy_timeout` for reader/writer coexistence, and a per-database flock to serialize index write bursts.

## Security Considerations

1. **Local-First**: All data stays on user's machine
2. **No External Calls**: No data sent to external services (unless using external embedding models)
3. **Path Validation**: Validate all paths before operations; `normalize_path` is the single canonical path-identity function
4. **SQL Injection**: Use parameterized queries throughout, and sanitize/quote user tokens before building FTS5 `MATCH` expressions

## Future Enhancements

1. **Plugin System**: Custom parsers and search strategies
2. **Web UI**: Browser-based search interface

## Directory Structure Rationale

The package layout under `src/sif/` maps closely onto the layers: each layer is a top-level package, and the import direction follows the layering — entry points (`cli/`, `mcp/`) may import anything below them, infrastructure (`database/`, `embedding/`) may import the domain, and the domain (`core/`) imports nothing from other SIF layers. The rationale for each package:

- **`core/` — dependency-free domain.** Plain `@dataclass` entities (`Collection`, `Document`, `DocumentChunk`, `SearchResult`, `SearchOptions`, `PathContext`, `QueryLogEntry`) and `Protocol` interfaces (`Embedder`, `Reranker`, `QueryExpander` in `core/models.py`; repository protocols in `core/collection.py`, `core/document.py`, and `core/context.py`) with no imports from any other SIF layer. This keeps domain logic free of I/O and framework coupling, so search and indexing code can be exercised without a database or a loaded model. `CollectionManager` and `ContextManager` are domain services over those repository protocols.
- **`config/` and `utils/` — cross-cutting foundation.** `config/` holds Pydantic `Settings` (environment variables prefixed `SIF_`, cached via `get_settings()`) and constants; `utils/` provides logging, path, progress, text, daemon, and service helpers. `utils/` may import `config/`; `config/` depends only on `sif._version` (through `config/constants.py`) and its own modules. Every other layer may use both.
- **`models/` — Pydantic boundary schemas.** Validation and serialization models (`ModelType`, `EmbeddingConfig`, request/response models, `ModelDownloader`) live apart from `core/` so domain entities stay plain dataclasses while Pydantic handles boundary schemas: request/response and search models, embedding configuration, and model downloads. CLI arguments are Click parameters and MCP tool payloads live in `sif/mcp/protocol.py`, so neither entry point imports this package; its production consumers are `embedding/` and `search/`. This package depends only on `utils/`.
- **`database/` — infrastructure behind the repository protocols.** The connection factory, per-database index lock, `SchemaManager`, and the concrete repositories. It depends on `core/` (entity types), `config/`, and `utils/` — never on `search/` or `indexing/`.
- **`embedding/` — provider isolation.** Two abstractions split the concern: the `Embedder` protocol from `core/` is what callers use, and the provider embedders in `embedding/embedder.py` implement it; the `EmbeddingModel` ABC in `embedding/model.py` remains defined but is not implemented by any production embedder. `EmbeddingModelFactory` builds instances from `ModelType` and `EmbeddingManager` loads and caches them, so switching GGUF, Sentence Transformers, OpenAI-compatible, or ModelScope backends touches only this package. The one infrastructure touch is `embedding/cache.py`, which opens its cache database through `database/factory.create_connection` for the same pragma recipe.
- **`search/` — strategies over the indices.** Strategies query SQLite directly (e.g., `bm25.py` uses the stdlib `sqlite3` module). Dependencies on `database/` and `config/` are limited to cross-cutting storage services: `suggest.py` uses `QueryLogRepository` and `Settings`, while embedding dependencies stay lazy — `expansion.py` imports `EmbeddingManager` only under `TYPE_CHECKING`, and `rerank.py` defers `ModelDownloader` and its ML-library imports to call time, so BM25 search works without an embedding stack present.
- **`indexing/` — pipeline orchestration.** scanner → parser → chunker, with `incremental.py` as the single per-file update loop, `drift.py` for pre-search freshness, and `watcher.py` for live indexing. It combines `database/` and `embedding/` in one flow, and reaches into `search/vector.py` through a deferred `create_embedding_purger` import so BM25-only paths do not require the vector stack.
- **`cli/` and `mcp/` — the two entry points.** Both sit at the top of the dependency graph: they may import every layer below them, and nothing imports them. `mcp/` is self-contained by design: `MCPServer` plus JSON-RPC 2.0 protocol handling (`server.py`, `protocol.py`), a `SearchBackend` that wires the database, repositories, embedding factory, and `SearchPipeline` together (`backend.py`), one `ToolHandler` subclass per tool (`handlers.py`), an optional embedded watcher (`watch_host.py`), and a `transports/` subpackage (`StdioTransport`, `HTTPTransport`) so a new transport can be added without touching server logic.

Two conventions reinforce the layout. Deferred imports (marked `# noqa: PLC0415`, e.g. `get_settings()` inside `database/database.py` or `ModelDownloader` inside `search/rerank.py`) keep heavy or cycle-prone dependencies out of module import time. Cross-layer imports that do exist are deliberately narrow and one-directional at the package level: `indexing/` reaches into `search/` only for vector writes and types (the deferred embedding purger in `incremental.py`, a function-local `VectorSearcher` import in `watcher.py` for the watch embed leg, and `TYPE_CHECKING`-only `VectorSearcher` imports in both modules), `embedding/` reaches into `database/` only for the connection factory, and `search/` reaches into `database/` only for the query-log repository used by suggestions.

## Connection Management

Every connection the application opens goes through `create_connection()` (`sif/database/factory.py`), so no connection site can forget the locked pragma recipe:

1. `PRAGMA busy_timeout = 5000` first — the WAL switch itself needs a write lock and does not honor a busy handler.
2. `PRAGMA journal_mode = WAL` behind a bounded retry — the mode persists in the database header, so the retry cost is paid only on the true first open.
3. `PRAGMA synchronous = NORMAL` — WAL's default remains FULL, and synchronous is per-connection.
4. `PRAGMA foreign_keys = ON`, `row_factory = sqlite3.Row`, and best-effort sqlite-vec loading.
5. `isolation_level="IMMEDIATE"` and `check_same_thread=False` — every `with conn:` block is a `BEGIN IMMEDIATE` transaction with commit/rollback semantics, and connections may move onto worker threads. Safety comes from the ownership discipline below, not from locking.

### Database (command-scoped)

`Database` (`sif/database/database.py`) holds one lazily created connection for the lifetime of the object, opened through the factory. `init_schema()` constructs a `SchemaManager` and runs `create_all()`. The connection is released by `close()` or the context-manager protocol. Foreground CLI commands that touch the index follow the same pattern — `with open_initialized_database(index_path, Database) as db:` — so a connection never outlives the command that opened it. The one exception is `sif watch --detach`, which arms through `open_initialized_database_unmanaged` because the daemon keeps its handle for the whole daemon lifetime. Commands may use `Database.transaction()` or the connection's own `with conn:` blocks.

### DatabaseConnection (per-operation)

`DatabaseConnection` (`sif/database/connection.py`, re-exported from `sif.database`) opens a fresh factory-configured connection per operation: `connect()` and `transaction()` are context managers that close the connection in a `finally`, and the convenience methods (`execute`, `executemany`, `fetchone`, `fetchall`) wrap single statements the same way. The MCP server uses this wrapper exclusively — `SearchBackend._run_in_db()` executes each tool call inside `DatabaseConnection(...).transaction()` on an `asyncio.to_thread` worker, so the event loop is never blocked and connections are never shared across threads. The ordinary MCP serving path does not create schema; it relies on the database already existing (created by the CLI). The opt-in embedded watch host is the exception: it opens its own `Database` and calls `init_schema()` before arming.

### Index Write Lock

`index_lock()` (`sif/database/locking.py`) serializes long-running index writes across processes with an exclusive `fcntl.flock` on a per-database lock file (`{db_path}.lock`, created `0600`). A loser waits up to `lock_wait_timeout` (default 30 seconds) and then runs its own pass anyway; checksum skipping makes overlapping passes no-ops. Kernel release on process death eliminates stale locks. On non-POSIX platforms the lock degrades to a warning.

## Schema Management and Evolution

There is no versioned migration runner on the active path. `SchemaManager.create_all()` (`sif/database/schema.py`) is idempotent, and the shared CLI database boundary (`sif/cli/error_handling.py`) invokes it via `db.init_schema()` for every command that opens the index. Besides `CREATE ... IF NOT EXISTS`, it adapts older layouts in place:

- **Column additions**: `_add_column_if_missing()` inspects `PRAGMA table_info` and issues `ALTER TABLE` when needed (e.g. the `pre_update_cmd` column on `collections`).
- **Table merges**: legacy `path_contexts` rows are folded into the unified `contexts` table inside a savepoint (`SAVEPOINT sp_migration`) that rolls back atomically on failure.
- **FTS repair**: external-content FTS5 tables must be maintained through the documented `'delete'`-command trigger form. `CREATE TRIGGER IF NOT EXISTS` cannot replace an existing broken trigger, so triggers whose `sqlite_master` SQL writes directly to the FTS tables are dropped and recreated; when a legacy direct-DELETE trigger is detected, the index is rebuilt (`INSERT INTO documents_fts(documents_fts) VALUES('rebuild')`) to purge entries orphaned by past deletes. FTS tables with a misconfigured `content=` setting are dropped, recreated, and reseeded from their base tables.
- **Suggestion vocabulary**: `documents_fts_v` is created with `fts5vocab(documents_fts, 'row')`; the suggestion engine re-ensures it on first use for connections that never ran `init_schema`.
- **Dimension guard**: before creating `document_embeddings`, the existing `FLOAT[dim]` declaration is read by `sif/embedding/identity.py::schema_embedding_dim` (the single `FLOAT[n]` read; the CLI embed command, the watcher, and the schema guard all delegate to it). A mismatch raises `IdentityDimensionError` whose remedy is to restore the model and `SIF_EMBEDDING_DIM` that match the stored dimension, or delete the database file and rebuild the index. When the host supplies an identity, the guard is the init-mode facet of `check_identity`.
- **Derived shadow backfill**: `create_all()` creates `embedded_documents` when vec0 is available and runs a marker-gated one-time backfill (`embedded_documents_version`). The pass derives existing documents only, warns with the count, and writes the marker after a complete pass; a table that did not pre-exist forces a rebuild even behind a surviving marker. A vec0-free database issues no shadow SQL and writes no marker.
- **Embedder identity adoption**: `create_all()` also calls `ensure_legacy_identity` for a host-supplied settings identity. A populated index with vectors but no `embedder.identity` row is written once as `source="legacy-assumed"` with one warning per process; a fresh/embeddings-empty index writes nothing, so its first successful vector write owns the identity.
- **Optional vector support**: if the sqlite-vec extension is unavailable (`SELECT vec_version()` fails), vector tables are skipped and BM25 keeps working.

## Caching

Two SQLite-backed cache surfaces exist:

- **Embedding cache** (`sif/embedding/cache.py`): stores embeddings in a separate database (`embeddings_cache.db`) under the cache directory (`Settings.get_cache_dir()`, the platformdirs user cache dir, overridable via `SIF_CACHE_DIR`). Entries are keyed `(SHA-256 content hash, model_id)` with vectors serialized as JSON, so cached embeddings survive restarts and models never read each other's vectors; a cache written before per-model keying existed is detected and rebuilt on first open. Enabled by the `cache_embeddings` setting; `EmbeddingManager` owns the cache and consults it around embed calls. The bucket is `{model_type}:{model_name}` (suffixed with `@{api_base}` when an API base is configured), then `|rev@<revision>` when the identity carries a revision, then `|q@<prompt>` / `|d@<prompt>` when that role's prompt is effective. With default ModelScope Qwen3 settings (no prompt, no revision) the bucket is exactly the pre-Phase-21 value.
- **LLM cache** (`llm_cache` table, `LLMCacheRepository` in `sif/database/repositories.py`): stores LLM responses keyed `(model_name, prompt_hash)` with an optional `expires_at` TTL and a lookup index on the key pair. Expired rows are purged by `sif cleanup`. No current search or reranking path populates or reads this table; it is a prepared cache surface.

## Suggestions and Query History

`sif suggest QUERY` and the did-you-mean path share one `SuggestionEngine` (`sif/search/suggest.py`) that ranks three display-only sections: prefix completions and did-you-mean rewrites from the `documents_fts_v` vocabulary, and history from the `query_log` table. Prefix completions are a bisect over the sorted stems; did-you-mean scores every out-of-vocab token against the full vocabulary with rapidfuzz's Indel ratio (`fuzz.ratio`, 0-100 scale, internal cutoff 75.0 — no setting or flag) and orders matches by score, then term, then document frequency. The engine never rewrites or re-executes a user's query, every emitted rewrite still probes the index and returns at least one hit, and every `sqlite3.OperationalError` path degrades to empty suggestions with a warning rather than failing the command.

- **History writes**: the CLI search trio records `(query, result count, collections)` through `QueryLogRepository.add()`, which trims to the most recent `SIF_QUERY_HISTORY_LIMIT` rows (default 500) in the same transaction. `SIF_QUERY_HISTORY_ENABLED=0` disables both writes and reads; `sif suggest --clear-history` empties the table.
- **Ranking**: history weight halves every 14 days of age; suggestions are truncated and escaped before display so bracketed text renders literally.
- **Tokenizer-bounded recall**: did-you-mean candidates come from the FTS5 porter vocabulary, so CJK lexical recall stays bounded by the tokenizer (a contiguous CJK run is one term). The rapidfuzz swap fixes Latin-script first-letter typos; it does not claim a Chinese did-you-mean improvement.

## Context System

Contexts are user-authored descriptions attached to paths or collections (or globally); only path-type contexts are read at search time, where they enrich results rather than influencing indexing. Collection and global contexts are stored and listed but never applied to search results — `ContextManager.build_search_context()` has no production callers.

- **Storage**: the unified `contexts` table (see Database Schema), with `context_type` restricted by CHECK constraint to `path`, `collection`, and `global`.
- **Domain model**: `sif/core/context.py` defines the `Context` entity, the `ContextType` enum, the `ContextRepository` protocol, and `ContextManager`, a domain service whose `build_search_context()` aggregates global, collection, and path-prefix contexts into a single string. The concrete `ContextRepository` (`sif/database/repositories.py`) persists `PathContext` records (`sif/core/models.py`) and includes a self-heal path: re-adding a path whose legacy row still holds the verbatim pre-normalization spelling re-points that row to the canonical form instead of duplicating it.
- **Path matching contract**: `normalize_path` (`sif/utils/paths.py`) is the single canonical definition of "same file", shared by the CLI (`context add`, `get`), the MCP backend, repositories, and search-time attachment. It expands `~` and resolves symlinks (e.g. `/tmp` → `/private/tmp` on macOS) while preserving non-existent tail components, and degrades to the raw string when a stored path cannot be resolved — a malformed row matches nothing rather than crashing search.
- **Search-time attachment**: `attach_path_contexts` (`sif/search/context_attach.py`) is the shared final step of all three searchers (`BM25Searcher`, `VectorSearcher`, `HybridSearcher`). It runs one constant batch query over path-type contexts and matches in Python by normalizing both sides — necessary because `contexts.target_id` stores the verbatim user-typed path while `documents.path` stores the resolved path, and since realpath is not invertible no exact-match SQL pre-filter can bridge the two. Rows are read in `updated_at` order so the newest context wins a normalization collision, and `context_description` is only set on a match — a description already carried through fusion or reranking is never clobbered.

## Embedder Identity and Vector-Space Enforcement

The index knows which embedder produced its vectors. `sif/embedding/identity.py` owns the contract:

- **Payload**: one JSON record under `index_meta['embedder.identity']` with schema version, `cache_model_id` (`{model_type}:{model_name}[@{api_base}]`, reusing the cache bucket format), model name/type, `api_base`, dimension, effective pooling (`mean`/`last_token`/`unknown`), normalization flag, effective query/document prompt scheme, prompt support, and a best-effort `revision` (GGUF model-file SHA-256; a Sentence Transformers commit hash when the loaded model exposes one; otherwise `null`). The record also carries `source` (`verified` or `legacy-assumed`) and a deterministic `fingerprint` (canonical-JSON SHA-256) used for display and diagnostics.
- **Comparison is field-wise, never fingerprint equality.** A field that is `unknown` (or a `null` revision) on either side is not evidence of a swap, so a legacy-assumed identity does not warn against the same model loaded later; a known-vs-known difference does.
- **Prompt scheme**: `sif/embedding/prompts.py` resolves `Settings.query_prompt_name` / `Settings.document_prompt_name` (env `SIF_QUERY_PROMPT_NAME` / `SIF_DOCUMENT_PROMPT_NAME`) over a small known-model table (Harrier → `web_search_query`). Qwen3 has no table entry, so the default path is prompt-free and byte-identical to pre-Phase-21 output. The effective scheme is part of the identity and of the cache bucket (`|q@…` / `|d@…`) only when a prompt is set.
- **Role-aware embed**: `sif/embedding/roles.py` dispatches `embed_query` / `embed_queries` / `embed_documents` to a backend's concrete role methods and falls back to `embed` / `embed_batch` for protocol-only doubles. Every query-side consumer (hybrid, `vec:`, `hyde:`, vsearch, expansion, bench/eval) uses the query role; the streaming writer and watcher use the document role.
- **Mode matrix** (`check_identity(conn, identity, mode=...)`): `init` is width-only and may write the legacy assumption; `embed` fails fast on a mismatch and writes no vectors; `search` never writes, warns once per process per identity pair, and marks every returned row `vectors_stale=True` via the existing derived marker (no new result field, no schema change).
- **Enforcement points**: `sif index embed` (`cli/commands/index.py`) and the watcher's `_EmbedSession` enforce embed mode; the schema open enforces init mode; `SearchPipeline`, `sif query`, `sif vsearch`, bench, eval, and MCP `hybrid_search` enforce search mode. BM25-only commands (`sif search`) never construct or evaluate the check, so they neither warn nor mark.
- **Legacy lifecycle**: a populated index with vectors but no identity record is written once as `source="legacy-assumed"` with one warning per process; search is never blocked on it. A complete, unfiltered, zero-failure `sif index embed --force` rewrites it as `source="verified"` (a fresh index's first vector write does so implicitly). A scoped `--force` or any failed document keeps the assumed marker.
- **Switching embedders intentionally**: use a fresh index (`sif --index <new.db> ...`) or rebuild the database. `--force` certifies against the stored identity — it never bypasses a same-width mismatch; a mismatch still fails fast naming the stored and current identities. `sif index vacuum` and `sif index backup` are CLI-only in Phase 21 (no MCP tool registration) and run on their own connection under the index flock.

## Error Handling

The error strategy is fail fast at construction, degrade gracefully in optional pipelines, and translate at the edges:

- **CLI database boundary**: `open_initialized_database()` (`sif/cli/error_handling.py`) owns the `Database(...)` + `init_schema()` pair. Known `OSError`/`sqlite3.Error` failures become remedy-bearing `click.ClickException`s; unexpected exceptions propagate unchanged with the handle closed. Command bodies translate their own user-facing failures the same way, so Click prints a clean message and exits non-zero.
- **Transactions**: `Database.transaction()` and `DatabaseConnection.transaction()` commit on success and roll back with a re-raise on any exception — repository failures never leave partial writes. The incremental indexer instead commits each file in its own short `BEGIN IMMEDIATE` transaction, so a mid-run failure keeps completed files durable and the run resumable.
- **Fail fast**: `VectorSearcher.__init__` raises `RuntimeError` when the sqlite-vec extension is missing rather than returning empty vector results; `SchemaManager` raises on embedding-dimension mismatch; `SearchPipeline` raises on reranking failure and on vector/HyDE search without an embedder. In `HybridSearcher.search()`, embedder and vector exceptions propagate uncaught — BM25-only results are returned only when vector search yields zero results, which is a no-results path, not failure handling.
- **Degrade gracefully**: optional stages log and continue — query-expansion failures are logged at warning level and search proceeds with the original query; the MCP `SearchBackend` logs a warning and serves BM25-only when the embedder fails to load or when `SearchPipeline` construction finds sqlite-vec unavailable; the connection factory loads sqlite-vec best-effort so the database opens even without it; pre-search drift refresh and suggestion generation warn and leave search results intact.

## Key Abstractions

The seams that make the layering work, as a quick index. Code for several of these appears in [Key Interfaces](#key-interfaces); deeper discussion lives in the sections above.

| Abstraction | Location | Role |
| --- | --- | --- |
| `Embedder`, `Reranker`, `QueryExpander` (protocols) | `sif/core/models.py` | Capability seams declared for embedding, reranking, and query expansion. Only `Embedder` is imported by production code; `Reranker` and `QueryExpander` are unused (the pipeline types its reranker as the concrete `LlamaCppReranker`/`CrossEncoderReranker`/`Qwen3Reranker` union and its expander as the concrete `QueryExpansion` class). |
| Domain entities: `Collection`, `Document`, `DocumentChunk`, `SearchResult`, `SearchOptions`, `PathContext`, `QueryLogEntry` | `sif/core/models.py`, `sif/core/collection.py`, `sif/core/document.py` | Plain dataclasses exchanged across every layer, free of I/O and framework coupling. |
| Repository protocols (`CollectionRepository`, `DocumentRepository`, `ContextRepository`) and the `Repository` ABC | `sif/core/collection.py`, `sif/core/document.py`, `sif/core/context.py`, `sif/database/repository.py` | Callers use the concrete SQLite repositories (`sif/database/repositories.py`) directly; those classes provide the operations but do not inherit these protocols, and the `Repository` ABC is exercised only by tests. |
| `SearchPipeline` / `HybridSearcher` | `sif/search/hybrid.py` | Orchestration: prefix routing (`lex:`, `vec:`, `hyde:`, `expand:`), RRF fusion, optional query expansion and reranking, snippet extraction, context and staleness attachment. |
| `SuggestionEngine` | `sif/search/suggest.py` | Display-only prefix completions, did-you-mean rewrites scored with the full-vocabulary rapidfuzz Indel ratio (`fuzz.ratio`, 0-100, cutoff 75.0), and history ranking over the FTS vocabulary and `query_log`. |
| `PersonalBench` (personal eval) | `sif/search/personal_bench.py` | Deterministic personal-corpus known-item bench: title/body synthesis, per-leg overlap budget, sha256 sampling and split, grouped reports, saved-run comparison, and a paired-bootstrap noise gate. |
| `Chunker` hierarchy and `create_chunker()` | `sif/indexing/chunker.py` | Chunking strategies (`FixedSizeChunker`, `MarkdownChunker`, `CodeChunker`, `AutoChunker`) selected by a factory function. |
| `IncrementalIndexer`, `FileWatcher`, `drift` helpers | `sif/indexing/incremental.py`, `sif/indexing/watcher.py`, `sif/indexing/drift.py` | The one per-file update loop, the host-agnostic live-index pipeline, and bounded pre-search refresh. |
| `EmbeddingModel` (ABC), `EmbeddingModelFactory`, `EmbeddingManager` | `sif/embedding/model.py`, `sif/embedding/factory.py`, `sif/embedding/manager.py` | Provider isolation: the factory builds an embedder per `ModelType` (llama.cpp GGUF, Sentence Transformers, OpenAI-compatible, ModelScope); the manager lazy-loads and caches the instance and fronts the embedding cache. |
| `EmbedderIdentity`, `check_identity`, `ensure_legacy_identity`, `certify_identity` | `sif/embedding/identity.py` | The persisted vector-space contract: deterministic fingerprint, field-wise unknown-tolerant comparison, the single `FLOAT[n]` read, the init/embed/search mode matrix, and the legacy-assumed → verified lifecycle. |
| `PromptScheme`, `resolve_prompt_scheme` | `sif/embedding/prompts.py` | The effective query/document prompt names from Settings overrides plus a known-model table; Qwen3 stays prompt-free (D-19). |
| `StreamingEmbedWriter`, `validate_batch`, `SystemicEmbedError` | `sif/indexing/embed_writer.py` | Streaming per-document embed: chunk/embed outside transactions, bounded batches, count/dimension/finiteness/norm sanity, one short transaction carrying chunks, vectors, shadow, and first-write identity. |
| `vacuum_index`, `backup_index`, `reconcile_embedded_documents` | `sif/database/maintenance.py` | CLI-only maintenance: TRUNCATE checkpoint + 2× disk precheck + `VACUUM`; online-API backup verified by `integrity_check`; derived-shadow repair in the caller's transaction. |
| `MCPServer`, `SearchBackend`, `ToolHandler` (ABC) | `sif/mcp/server.py`, `sif/mcp/backend.py`, `sif/mcp/handlers.py` | The MCP surface: a JSON-RPC 2.0 server core over pluggable transports, a backend that wires database, repositories, factory, and `SearchPipeline` together per call, and one handler subclass per tool (`query`, `get`, `multi_get`, `status`). |
| `create_connection`, `Database`, `DatabaseConnection`, `index_lock`, `SchemaManager` | `sif/database/factory.py`, `sif/database/database.py`, `sif/database/connection.py`, `sif/database/locking.py`, `sif/database/schema.py` | Storage lifecycle: the shared pragma recipe, command-scoped and per-operation connection wrappers over raw `sqlite3.Connection` (repositories stay agnostic), cross-process write arbitration, and idempotent schema creation and in-place adaptation. |
| `Settings` / `get_settings()` | `sif/config/settings.py` | Pydantic Settings with `SIF_`-prefixed environment variables, cached via `@lru_cache`; the single source for database/cache paths, model selection, watch depth, search refresh, query history, and defaults. |

Two supporting abstractions have their own sections: `Context` / `ContextManager` (`sif/core/context.py`), which aggregates global, collection, and path contexts into a single search-context string, and `normalize_path` (`sif/utils/paths.py`), the canonical path-identity function — both under [Context System](#context-system).
