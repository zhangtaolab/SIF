# SIF Architecture Design Document

## Overview

SIF is a local CLI search engine for indexing and searching markdown documents. It is a Python reimplementation of the original TypeScript QMD (Query Markup Documents) project.

## Design Goals

1. **Modularity**: Clean separation of concerns with well-defined interfaces
2. **Testability**: Dependency injection and protocol-based design for easy testing
3. **Extensibility**: Plugin architecture for search strategies and embedding models
4. **Performance**: Efficient indexing and search using SQLite FTS5 and vector search
5. **Type Safety**: Full type hints and Pydantic validation

## Architecture Patterns

### 1. Layered Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Presentation Layer                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │     CLI      │  │  MCP Server  │  │  API (Future)    │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                      Application Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Collection │  │    Index     │  │     Search       │  │
│  │   Manager    │  │   Service    │  │    Service       │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                      Domain Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Collection  │  │   Document   │  │     Context      │  │
│  │   Entity     │  │   Entity     │  │     Entity       │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                      Infrastructure Layer                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Repository  │  │   Embedding  │  │    Database      │  │
│  │  (SQLite)    │  │    Model     │  │   Connection     │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 2. Design Patterns Used

#### Repository Pattern
- **Purpose**: Abstract data access layer
- **Location**: `src/sif/database/repository.py`
- **Benefits**: 
  - Decouples domain logic from data storage
  - Enables easy testing with mock repositories
  - Allows switching storage backends

#### Strategy Pattern
- **Purpose**: Pluggable search algorithms
- **Location**: `src/sif/search/strategy.py`
- **Implementations**:
  - `BM25Searcher`: Full-text search via SQLite FTS5
  - `VectorSearcher`: Semantic search via embeddings
  - `HybridSearcher`: Combined BM25 + Vector with RRF fusion

#### Factory Pattern
- **Purpose**: Create embedding model instances
- **Location**: `src/sif/embedding/factory.py`
- **Supported Models**:
  - GGUF models via llama-cpp-python
  - Sentence Transformers
  - OpenAI API
  - ModelScope models
  - HuggingFace models (future)

#### Dependency Injection
- **Purpose**: Manage dependencies and enable testing
- **Location**: Throughout the codebase
- **Example**: `CollectionManager` receives `CollectionRepository` in constructor

## Module Structure

```
src/sif/
├── __init__.py              # Package exports
├── _version.py              # Version information
├── core/                    # Domain entities and business logic
│   ├── __init__.py
│   ├── collection.py        # Collection entity and manager
│   ├── document.py          # Document and DocumentChunk entities
│   ├── context.py           # Context entity and manager
│   └── models.py            # Core data models and protocols
├── models/                  # Pydantic models for validation
│   ├── __init__.py
│   ├── collection.py        # Collection request/response models
│   ├── document.py          # Document request/response models
│   ├── context.py           # Context request/response models
│   ├── search.py            # Search query and result models
│   ├── embedding.py         # Embedding configuration models
│   └── download.py          # Model download models
├── database/                # Data access layer
│   ├── __init__.py
│   ├── connection.py        # Database connection management
│   ├── database.py          # Database facade and transactions
│   ├── repository.py        # Repository interfaces
│   ├── repositories.py      # Repository implementations
│   ├── schema.py            # Schema creation (tables, FTS5, vectors)
│   └── migrations.py        # Database migrations
├── search/                  # Search functionality
│   ├── __init__.py
│   ├── strategy.py          # Search strategy interface
│   ├── bm25.py              # BM25 search implementation
│   ├── vector.py            # Vector search implementation
│   ├── hybrid.py            # Hybrid search and search pipeline
│   ├── rrf.py               # Reciprocal Rank Fusion
│   ├── expansion.py         # Query expansion
│   ├── rerank.py            # Result reranking
│   ├── snippets.py          # Snippet extraction
│   ├── term_match.py        # Stem-tolerant term matching
│   ├── context_attach.py    # Path-context attachment for results
│   └── benchmark.py         # Search quality benchmarks
├── indexing/                # Document indexing
│   ├── __init__.py
│   ├── scanner.py           # File system scanning
│   ├── parser.py            # Markdown parsing
│   ├── chunker.py           # Document chunking
│   ├── incremental.py       # Incremental index orchestration
│   └── watcher.py           # File system watching
├── embedding/               # Embedding generation
│   ├── __init__.py
│   ├── manager.py           # Embedding model management
│   ├── model.py             # Model interface
│   ├── embedder.py          # Embedding model implementations
│   ├── factory.py           # Model factory
│   └── cache.py             # Embedding cache
├── mcp/                     # MCP server implementation
│   ├── __init__.py
│   ├── server.py            # MCP server
│   ├── backend.py           # SearchBackend for MCP tools
│   ├── protocol.py          # MCP protocol definitions
│   ├── handlers.py          # Request handlers
│   ├── cli.py               # MCP server CLI helpers
│   └── transports/          # Transport implementations
│       ├── __init__.py
│       ├── stdio.py         # stdio transport
│       └── http.py          # HTTP transport (FastAPI)
├── cli/                     # Command-line interface
│   ├── __init__.py
│   ├── main.py              # CLI entry point
│   ├── formatters.py        # Output formatters
│   └── commands/            # CLI command implementations
│       ├── __init__.py
│       ├── collection.py    # Collection commands
│       ├── context.py       # Context commands
│       ├── index.py         # Index commands
│       ├── search.py        # Search commands
│       ├── get.py           # Document retrieval commands
│       ├── ls.py            # Indexed document listing
│       ├── pull.py          # Model download command
│       ├── bench.py         # Benchmark commands
│       └── mcp.py           # MCP commands
├── config/                  # Configuration
│   ├── __init__.py
│   ├── settings.py          # Pydantic settings
│   └── constants.py         # Constants
└── utils/                   # Utilities
    ├── __init__.py
    ├── logging.py           # Logging setup
    ├── paths.py             # Path utilities
    ├── text.py              # Text processing
    └── progress.py          # Progress indicators
```

## Core Interfaces

### Repository Interface

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

### Search Strategy Interface

```python
class SearchStrategy(ABC):
    @abstractmethod
    def search(
        self,
        context: SearchContext,
        options: SearchOptions,
    ) -> list[SearchResult]: ...
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
```

## Data Flow

### Indexing Flow

```
1. User: sif collection add ~/notes --name my-collection
   │     sif index update -c my-collection
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
7. EmbeddingModel: Chunk embeddings are generated by the separate sif index embed command
   │
   ▼
8. Repository: Store documents, chunks, embeddings
   │
   ▼
9. FTS Index: Update full-text search index
   │
   ▼
10. Vector Index: Update vector search index (sqlite-vec)
```

### Search Flow

```
1. User: sif search query "machine learning"
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
9. Repository: Fetch document details
   │
   ▼
10. CLI: Format and display results
```

## Database Schema

### Collections Table
```sql
CREATE TABLE collections (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    path TEXT NOT NULL,
    pattern TEXT DEFAULT '**/*.md',
    ignore_patterns TEXT DEFAULT '[]',  -- JSON array
    include_by_default INTEGER DEFAULT 1,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_indexed_at TEXT,
    document_count INTEGER DEFAULT 0,
    chunk_count INTEGER DEFAULT 0,
    pre_update_cmd TEXT  -- added by migration
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
    metadata TEXT DEFAULT '{}',  -- JSON
    FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE
);
-- Lookups use non-unique indexes on collection_id, path, and checksum.
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
-- Lookups use a non-unique index on (target_id, context_type).
```

### FTS5 Virtual Table
```sql
CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
    content,
    content='documents',
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
    embedding FLOAT[{dim}]  -- dimension from model
);
```

## Configuration

Settings are managed via Pydantic Settings with environment variable support:

| Variable | Default | Description |
|----------|---------|-------------|
| SIF_DB_PATH | platformdirs user_data_dir/sif/sif.db | Database path |
| SIF_MODEL_PATH | None | Embedding model path |
| SIF_MODEL_NAME | Qwen/Qwen3-Embedding-0.6B | Model name |
| SIF_EMBEDDING_DIM | 1024 | Embedding dimension |
| SIF_CHUNK_SIZE | 512 | Chunk size in tokens |
| SIF_CHUNK_OVERLAP | 128 | Chunk overlap in tokens |
| SIF_LOG_LEVEL | INFO | Logging level |
| SIF_MCP_HOST | 127.0.0.1 | MCP HTTP server host |
| SIF_MCP_PORT | 8080 | MCP HTTP server port |

## Testing Strategy

### Unit Tests
- Test individual components in isolation
- Use mock repositories and services
- Focus on business logic

### Integration Tests
- Test database interactions
- Test search strategies with real data
- Test CLI commands

### End-to-End Tests
- Full indexing and search workflows
- MCP server functionality

## Future Enhancements

1. **Plugin System**: Custom parsers and search strategies
2. **Web UI**: Browser-based search interface
3. **Multi-language Support**: Non-English document support
