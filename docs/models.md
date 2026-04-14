# Data Models

This document describes all data models used in DocSift.

## Overview

DocSift uses Pydantic models for data validation and serialization. Models are organized by domain:

- **Collection Models**: Collection management
- **Document Models**: Document and chunk entities
- **Context Models**: Search context
- **Search Models**: Search queries and results
- **Embedding Models**: Embedding configuration

## Collection Models

### Collection (Domain Entity)

Core domain entity representing a document collection.

```python
from docsift import Collection
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

@dataclass
class Collection:
    id: str                          # Unique identifier (UUID)
    name: str                        # Collection name (unique)
    description: str | None = None   # Optional description
    paths: list[str] = field(default_factory=list)  # Indexed paths
    document_count: int = 0          # Number of documents
    chunk_count: int = 0             # Number of chunks
    metadata: dict[str, Any] = field(default_factory=dict)  # Custom metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_indexed_at: datetime | None = None
```

**Example:**
```python
collection = Collection(
    id="550e8400-e29b-41d4-a716-446655440000",
    name="my-notes",
    description="Personal programming notes",
    paths=["~/Documents/notes", "~/Documents/ideas"],
    document_count=42,
    metadata={"category": "personal", "priority": "high"}
)
```

### CollectionCreate (Pydantic Model)

Model for creating a new collection.

```python
from docsift.models.collection import CollectionCreate

class CollectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    paths: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
```

**Validation:**
- `name`: Required, 1-100 characters
- `description`: Optional, max 500 characters
- `paths`: List of valid directory paths
- `metadata`: Any JSON-serializable data

**Example:**
```python
create_data = CollectionCreate(
    name="work-docs",
    description="Work documentation",
    paths=["~/Work/docs"],
    metadata={"team": "engineering"}
)
```

### CollectionUpdate (Pydantic Model)

Model for updating an existing collection.

```python
from docsift.models.collection import CollectionUpdate

class CollectionUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    paths: list[str] | None = None
    metadata: dict[str, Any] | None = None
```

**Example:**
```python
update_data = CollectionUpdate(
    description="Updated description",
    metadata={"status": "active"}
)
```

### CollectionResponse (Pydantic Model)

Model for collection API responses.

```python
from docsift.models.collection import CollectionResponse

class CollectionResponse(BaseModel):
    id: str
    name: str
    description: str | None
    paths: list[str]
    document_count: int
    chunk_count: int
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    last_indexed_at: datetime | None
```

**Example:**
```python
response = CollectionResponse(
    id="550e8400-e29b-41d4-a716-446655440000",
    name="my-notes",
    description="Personal notes",
    paths=["~/Documents/notes"],
    document_count=42,
    chunk_count=156,
    metadata={},
    created_at=datetime(2024, 1, 15, 10, 30, 0),
    updated_at=datetime(2024, 1, 20, 14, 22, 0),
    last_indexed_at=datetime(2024, 1, 20, 14, 22, 0)
)
```

## Document Models

### Document (Domain Entity)

Core domain entity representing an indexed document.

```python
from docsift import Document
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

@dataclass
class Document:
    id: str                    # Unique identifier (UUID)
    collection_id: str         # Parent collection ID
    path: str                  # File system path
    content: str               # Document content
    checksum: str              # Content checksum (SHA-256)
    file_size: int             # File size in bytes
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    indexed_at: datetime | None = None
```

**Example:**
```python
document = Document(
    id="doc_abc123",
    collection_id="550e8400-e29b-41d4-a716-446655440000",
    path="~/Documents/notes/python/decorators.md",
    content="# Python Decorators\n\nDecorators are...",
    checksum="a1b2c3d4e5f6...",
    file_size=2048,
    metadata={
        "title": "Python Decorators",
        "tags": ["python", "advanced"],
        "author": "John Doe"
    }
)
```

### DocumentChunk (Domain Entity)

Represents a chunk of a document for embedding and search.

```python
from docsift import DocumentChunk
from dataclasses import dataclass

@dataclass
class DocumentChunk:
    id: str                    # Unique identifier
    document_id: str           # Parent document ID
    content: str               # Chunk content
    start_line: int            # Start line in document
    end_line: int              # End line in document
    token_count: int           # Number of tokens
    embedding_id: str | None = None  # Reference to embedding
```

**Example:**
```python
chunk = DocumentChunk(
    id="chunk_xyz789",
    document_id="doc_abc123",
    content="Decorators are a powerful feature...",
    start_line=10,
    end_line=25,
    token_count=128,
    embedding_id="emb_def456"
)
```

### DocumentCreate (Pydantic Model)

Model for creating a document.

```python
from docsift.models.document import DocumentCreate

class DocumentCreate(BaseModel):
    collection_id: str
    path: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
```

### DocumentResponse (Pydantic Model)

Model for document API responses.

```python
from docsift.models.document import DocumentResponse

class DocumentResponse(BaseModel):
    id: str
    collection_id: str
    path: str
    content: str
    file_size: int
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    indexed_at: datetime | None
    chunks: list[DocumentChunkResponse] | None = None
```

## Context Models

### Context (Domain Entity)

Domain entity representing search context.

```python
from docsift import Context
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Context:
    id: str                    # Unique identifier
    content: str               # Context text
    context_type: str          # 'collection', 'path', 'document', 'global'
    target_id: str             # ID of target entity
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
```

**Context Types:**
- `global`: Applies to all searches
- `collection`: Applies to searches in a specific collection
- `path`: Applies to searches in a specific path
- `document`: Applies to searches for a specific document

**Example:**
```python
# Global context
global_ctx = Context(
    id="ctx_global",
    content="I am a software engineer interested in Python.",
    context_type="global",
    target_id="*"
)

# Collection context
collection_ctx = Context(
    id="ctx_col",
    content="These are my personal programming notes.",
    context_type="collection",
    target_id="550e8400-e29b-41d4-a716-446655440000"
)
```

### ContextCreate (Pydantic Model)

```python
from docsift.models.context import ContextCreate

class ContextCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    context_type: str = Field(..., pattern="^(global|collection|path|document)$")
    target_id: str
```

### ContextResponse (Pydantic Model)

```python
from docsift.models.context import ContextResponse

class ContextResponse(BaseModel):
    id: str
    content: str
    context_type: str
    target_id: str
    created_at: datetime
    updated_at: datetime
```

## Search Models

### SearchType (Enum)

```python
from docsift.models.search import SearchType
from enum import Enum

class SearchType(str, Enum):
    BM25 = "bm25"       # Full-text search
    VECTOR = "vector"   # Semantic search
    HYBRID = "hybrid"   # Combined search
```

### SearchOptions (Pydantic Model)

Comprehensive search options model.

```python
from docsift.models.search import SearchOptions

class SearchOptions(BaseModel):
    # General options
    limit: int = Field(10, ge=1, le=100, description="Maximum results")
    offset: int = Field(0, ge=0, description="Result offset")
    threshold: float = Field(0.0, ge=0, le=1, description="Minimum score")
    include_chunks: bool = True
    include_metadata: bool = True
    highlight_matches: bool = True
    
    # BM25 parameters
    bm25_k1: float = Field(1.5, ge=0.1, le=3.0)
    bm25_b: float = Field(0.75, ge=0.1, le=1.0)
    
    # Vector parameters
    vector_weight: float = Field(0.7, ge=0, le=1)
    
    # Hybrid parameters
    bm25_weight: float = Field(0.3, ge=0, le=1)
    rrf_k: int = Field(60, ge=1, description="RRF fusion constant")
    
    # Query expansion
    expand_query: bool = False
    expansion_factor: int = Field(3, ge=1, le=10)
    
    # Reranking
    rerank: bool = False
    rerank_top_k: int = Field(20, ge=1, le=100)
```

**Example:**
```python
options = SearchOptions(
    limit=20,
    threshold=0.5,
    expand_query=True,
    rerank=True,
    bm25_k1=2.0,
    rrf_k=40
)
```

### SearchQuery (Pydantic Model)

```python
from docsift.models.search import SearchQuery

class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1, description="Search query")
    collection_ids: list[str] | None = None
    search_type: SearchType = SearchType.HYBRID
    options: SearchOptions = Field(default_factory=SearchOptions)
    filters: dict[str, Any] = Field(default_factory=dict)
```

**Example:**
```python
query = SearchQuery(
    query="python decorators",
    collection_ids=["550e8400-e29b-41d4-a716-446655440000"],
    search_type=SearchType.HYBRID,
    options=SearchOptions(limit=15, expand_query=True),
    filters={"tags": ["python"]}
)
```

### SearchResult (Pydantic Model)

```python
from docsift.models.search import SearchResult

class SearchResult(BaseModel):
    document_id: str
    document_path: str
    document_title: str | None = None
    score: float = Field(..., ge=0, le=1)
    
    # Component scores (for hybrid search)
    bm25_score: float | None = None
    vector_score: float | None = None
    
    # Result data
    content_preview: str | None = None
    matched_chunks: list[dict[str, Any]] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
```

**Example:**
```python
result = SearchResult(
    document_id="doc_abc123",
    document_path="~/notes/python/decorators.md",
    document_title="Python Decorators",
    score=0.89,
    bm25_score=0.85,
    vector_score=0.92,
    content_preview="Python decorators are a powerful feature...",
    highlights=["decorators are a powerful"],
    metadata={"tags": ["python", "advanced"]}
)
```

### SearchResponse (Pydantic Model)

```python
from docsift.models.search import SearchResponse

class SearchResponse(BaseModel):
    query: str
    search_type: SearchType
    total: int = Field(..., ge=0)
    results: list[SearchResult] = Field(default_factory=list)
    search_time_ms: float = Field(..., ge=0)
    expanded_query: str | None = None
    expansion_terms: list[str] = Field(default_factory=list)
```

**Example:**
```python
response = SearchResponse(
    query="python decorators",
    search_type=SearchType.HYBRID,
    total=23,
    results=[result1, result2, result3],
    search_time_ms=45.2,
    expanded_query="python decorators wrapper function",
    expansion_terms=["wrapper", "function"]
)
```

## Embedding Models

### ModelType (Enum)

```python
from docsift.models.embedding import ModelType
from enum import Enum

class ModelType(str, Enum):
    SENTENCE_TRANSFORMERS = "sentence_transformers"
    GGUF = "gguf"
    OPENAI = "openai"
    HUGGINGFACE = "huggingface"
```

### ModelConfig (Pydantic Model)

```python
from docsift.models.embedding import ModelConfig

class ModelConfig(BaseModel):
    model_type: ModelType
    model_name: str | None = None
    model_path: str | None = None
    dimension: int = Field(384, ge=1)
    device: str = "cpu"
    batch_size: int = Field(32, ge=1)
```

**Example:**
```python
# Sentence Transformer config
st_config = ModelConfig(
    model_type=ModelType.SENTENCE_TRANSFORMERS,
    model_name="all-MiniLM-L6-v2",
    dimension=384
)

# GGUF config
gguf_config = ModelConfig(
    model_type=ModelType.GGUF,
    model_path="~/models/embedding.gguf",
    dimension=768
)
```

### EmbeddingCacheEntry (Pydantic Model)

```python
from docsift.models.embedding import EmbeddingCacheEntry

class EmbeddingCacheEntry(BaseModel):
    text_hash: str
    embedding: list[float]
    created_at: datetime
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
    context_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(context_type, target_id)
);
```

## Model Relationships

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│ Collection  │◄──────│  Document   │◄──────│    Chunk    │
│             │  1:N  │             │  1:N  │             │
└─────────────┘       └─────────────┘       └─────────────┘
       ▲                                            │
       │                                            │
       │              ┌─────────────┐               │
       └──────────────│   Context   │◄──────────────┘
              N:M     │             │         N:M
                      └─────────────┘
```

## Validation Rules

### Collection
- `name`: Unique, 1-100 characters
- `description`: Max 500 characters
- `paths`: Must be valid directory paths

### Document
- `path`: Must be valid file path
- `content`: Non-empty string
- `checksum`: Valid SHA-256 hash

### Search
- `query`: 1-1000 characters
- `limit`: 1-100
- `threshold`: 0.0-1.0

### Context
- `content`: 1-5000 characters
- `context_type`: Must be one of defined types

## Serialization

All models support JSON serialization:

```python
from docsift.models.search import SearchResponse
import json

# Serialize
response = SearchResponse(...)
json_str = response.model_dump_json(indent=2)

# Deserialize
response = SearchResponse.model_validate_json(json_str)

# To dict
data = response.model_dump()
```

## Related Documentation

- [API Reference](api-reference.md) - Python API usage
- [Architecture](architecture.md) - Data flow and storage
- [Search Algorithms](search-algorithms.md) - Search model usage
