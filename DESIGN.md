# DocSift Architecture Design Document

## Overview

DocSift is a local CLI search engine for indexing and searching markdown documents. It is a Python reimplementation of the original TypeScript QMD (Query Markup Documents) project.

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
- **Location**: `docsift/database/repository.py`
- **Benefits**: 
  - Decouples domain logic from data storage
  - Enables easy testing with mock repositories
  - Allows switching storage backends

#### Strategy Pattern
- **Purpose**: Pluggable search algorithms
- **Location**: `docsift/search/strategy.py`
- **Implementations**:
  - `BM25SearchStrategy`: Full-text search via SQLite FTS5
  - `VectorSearchStrategy`: Semantic search via embeddings
  - `HybridSearchStrategy`: Combined BM25 + Vector with RRF fusion

#### Factory Pattern
- **Purpose**: Create embedding model instances
- **Location**: `docsift/embedding/factory.py`
- **Supported Models**:
  - GGUF models via llama-cpp-python
  - Sentence Transformers
  - OpenAI API (future)
  - HuggingFace models (future)

#### Dependency Injection
- **Purpose**: Manage dependencies and enable testing
- **Location**: Throughout the codebase
- **Example**: `CollectionManager` receives `CollectionRepository` in constructor

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
│   └── commands/            # CLI command implementations
│       ├── __init__.py
│       ├── collection.py    # Collection commands
│       ├── context.py       # Context commands
│       ├── index.py         # Index commands
│       ├── search.py        # Search commands
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
10. Vector Index: Update vector search index (sqlite-vec)
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

## Configuration

Settings are managed via Pydantic Settings with environment variable support:

| Variable | Default | Description |
|----------|---------|-------------|
| DOCSIFT_DB_PATH | ~/.local/share/docsift/docsift.db | Database path |
| DOCSIFT_MODEL_PATH | None | Embedding model path |
| DOCSIFT_MODEL_NAME | all-MiniLM-L6-v2 | Model name |
| DOCSIFT_EMBEDDING_DIM | 384 | Embedding dimension |
| DOCSIFT_CHUNK_SIZE | 512 | Chunk size in tokens |
| DOCSIFT_CHUNK_OVERLAP | 128 | Chunk overlap in tokens |
| DOCSIFT_LOG_LEVEL | INFO | Logging level |
| DOCSIFT_MCP_HOST | 127.0.0.1 | MCP HTTP server host |
| DOCSIFT_MCP_PORT | 8080 | MCP HTTP server port |

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

1. **Incremental Indexing**: Only index changed documents
2. **Real-time Watching**: File system watcher for auto-indexing
3. **Plugin System**: Custom parsers and search strategies
4. **Web UI**: Browser-based search interface
5. **Multi-language Support**: Non-English document support
6. **Advanced Reranking**: Cross-encoder reranking
7. **Query Suggestions**: Auto-complete and related queries
