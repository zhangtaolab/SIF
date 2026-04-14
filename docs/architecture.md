# DocSift Architecture

## Overview

DocSift follows a layered architecture with clean separation of concerns, designed for modularity, testability, and extensibility. The architecture is inspired by Domain-Driven Design (DDD) principles and implements several well-known design patterns.

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

**Location**: `docsift/database/repository.py`

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

**Location**: `docsift/search/strategy.py`

```python
class SearchStrategy(ABC):
    @abstractmethod
    def search(
        self,
        context: SearchContext,
        options: SearchOptions,
    ) -> list[SearchResult]: ...
```

**Implementations**:
- `BM25SearchStrategy`: Full-text search via SQLite FTS5
- `VectorSearchStrategy`: Semantic search via embeddings
- `HybridSearchStrategy`: Combined BM25 + Vector with RRF fusion

**Benefits**:
- Easy to add new search algorithms
- Can switch strategies at runtime
- Each strategy is independently testable

### Factory Pattern

**Purpose**: Create embedding model instances based on configuration

**Location**: `docsift/embedding/factory.py`

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
- OpenAI API (planned)
- HuggingFace models (planned)

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
1. User: docsift index add my-collection ~/notes
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
1. User: docsift search "machine learning"
   │
   ▼
2. CLI: Parse query, build SearchQuery
   │
   ▼
3. SearchService: Select search strategy
   │
   ▼
4. QueryExpansion (optional): Expand query
   │
   ▼
5. BM25SearchStrategy: Search FTS index
   │
   ▼
6. VectorSearchStrategy: Search vector index
   │
   ▼
7. HybridSearchStrategy: Combine results (RRF)
   │
   ▼
8. Reranker (optional): Rerank results
   │
   ▼
9. Repository: Fetch document details
   │
   ▼
10. CLI: Format and display results
```

## Module Structure

```
docsift/
├── __init__.py              # Package exports
├── _version.py              # Version information
├── core/                    # Domain entities and business logic
│   ├── __init__.py
│   ├── collection.py        # Collection entity and manager
│   ├── document.py          # Document and DocumentChunk entities
│   └── context.py           # Context entity and manager
├── models/                  # Pydantic models for validation
│   ├── __init__.py
│   ├── collection.py        # Collection request/response models
│   ├── document.py          # Document request/response models
│   ├── context.py           # Context request/response models
│   ├── search.py            # Search query and result models
│   └── embedding.py         # Embedding configuration models
├── database/                # Data access layer
│   ├── __init__.py
│   ├── connection.py        # Database connection management
│   ├── repository.py        # Repository interfaces
│   └── migrations.py        # Database migrations
├── search/                  # Search functionality
│   ├── __init__.py
│   ├── strategy.py          # Search strategy interface
│   ├── bm25.py              # BM25 search implementation
│   ├── vector.py            # Vector search implementation
│   ├── hybrid.py            # Hybrid search implementation
│   ├── rrf.py               # Reciprocal Rank Fusion
│   ├── expansion.py         # Query expansion
│   └── rerank.py            # Result reranking
├── indexing/                # Document indexing
│   ├── __init__.py
│   ├── scanner.py           # File system scanning
│   ├── parser.py            # Markdown parsing
│   ├── chunker.py           # Document chunking
│   ├── indexer.py           # Index orchestration
│   └── watcher.py           # File system watching
├── embedding/               # Embedding generation
│   ├── __init__.py
│   ├── manager.py           # Embedding model management
│   ├── model.py             # Model interface
│   ├── factory.py           # Model factory
│   └── cache.py             # Embedding cache
├── mcp_server/              # MCP server implementation
│   ├── __init__.py
│   ├── server.py            # MCP server
│   ├── transport.py         # Transport implementations
│   ├── handlers.py          # Request handlers
│   └── tools.py             # MCP tool definitions
├── cli/                     # Command-line interface
│   ├── __init__.py
│   ├── main.py              # CLI entry point
│   ├── config.py            # CLI configuration
│   ├── formatters.py        # Output formatters
│   └── commands/            # CLI command implementations
│       ├── __init__.py
│       ├── collection.py    # Collection commands
│       ├── context.py       # Context commands
│       ├── index.py         # Index commands
│       ├── search.py        # Search commands
│       └── mcp.py           # MCP commands
└── utils/                   # Utilities
    ├── __init__.py
    ├── logging.py           # Logging setup
    ├── paths.py             # Path utilities
    ├── text.py              # Text processing
    └── progress.py          # Progress indicators
```

## Database Schema

### Collections Table

```sql
CREATE TABLE collections (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    paths TEXT,  -- JSON array
    document_count INTEGER DEFAULT 0,
    chunk_count INTEGER DEFAULT 0,
    metadata TEXT,  -- JSON
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_indexed_at DATETIME
);
```

### Documents Table

```sql
CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    collection_id TEXT NOT NULL,
    path TEXT NOT NULL,
    content TEXT NOT NULL,
    checksum TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    metadata TEXT,  -- JSON
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    indexed_at DATETIME,
    FOREIGN KEY (collection_id) REFERENCES collections(id),
    UNIQUE(collection_id, path)
);
```

### Chunks Table

```sql
CREATE TABLE chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    content TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    token_count INTEGER NOT NULL,
    embedding_id TEXT,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);
```

### Contexts Table

```sql
CREATE TABLE contexts (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    context_type TEXT NOT NULL,  -- 'collection', 'path', 'document', 'global'
    target_id TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(context_type, target_id)
);
```

### FTS5 Virtual Table

```sql
CREATE VIRTUAL TABLE documents_fts USING fts5(
    content,
    content_rowid=rowid,
    tokenize='porter'
);
```

### sqlite-vec Vector Table

```sql
CREATE VIRTUAL TABLE chunk_embeddings USING vec0(
    embedding_id TEXT PRIMARY KEY,
    embedding FLOAT[{dim}]  -- dimension from model
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
class EmbeddingModel(ABC):
    @abstractmethod
    def load(self) -> None: ...
    
    @abstractmethod
    def embed(
        self,
        texts: list[str],
        normalize: bool = True,
    ) -> list[list[float]]: ...
    
    @property
    @abstractmethod
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

1. **Incremental Indexing**: Only index changed documents
2. **Real-time Watching**: File system watcher for auto-indexing
3. **Plugin System**: Custom parsers and search strategies
4. **Web UI**: Browser-based search interface
5. **Multi-language Support**: Non-English document support
6. **Advanced Reranking**: Cross-encoder reranking
7. **Query Suggestions**: Auto-complete and related queries
