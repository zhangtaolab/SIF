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
    @staticmethod
    def create_model(
        model_type: ModelType,
        config: ModelConfig,
    ) -> EmbeddingModel: ...
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
│   ├── config.py            # CLI configuration management
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
