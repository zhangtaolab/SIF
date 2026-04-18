# Data Models

This document describes all data models used in DocSift.

## Overview

DocSift uses a mix of dataclasses for domain entities and Pydantic models for data validation and serialization. Models are organized by domain:

- **Collection Models**: Collection management
- **Document Models**: Document and chunk entities
- **Context Models**: Search context
- **Search Models**: Search queries and results
- **Embedding Models**: Embedding configuration

## Collection Models

### Collection (Domain Entity)

Core domain entity representing a document collection.

```python
from docsift.core.models import Collection
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

@dataclass
class Collection:
    name: str                        # Collection name (unique)
    path: str                        # Indexed path (single directory)
    pattern: str = "**/*.md"         # File glob pattern
    ignore_patterns: list[str] = field(default_factory=list)  # Patterns to ignore
    include_by_default: bool = True  # Include in default searches
    description: str | None = None   # Optional description
    pre_update_cmd: str | None = None  # Command to run before indexing
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    document_count: int = 0          # Number of documents
    chunk_count: int = 0             # Number of chunks
    last_indexed_at: datetime | None = None
```

**Example:**
```python
collection = Collection(
    id="550e8400-e29b-41d4-a716-446655440000",
    name="my-notes",
    description="Personal programming notes",
    path="~/Documents/notes",
    document_count=42,
)
```

**Note:** `path` is a single string, not a list. Each collection maps to one directory.

## Document Models

### Document (Domain Entity)

Core domain entity representing an indexed document.

```python
from docsift.core.models import Document
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

@dataclass
class Document:
    path: str                  # File system path
    collection_id: str         # Parent collection ID
    content: str               # Document content
    title: str | None = None   # Document title (defaults to filename)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    filename: str = field(init=False)   # Computed from path
    checksum: str = field(init=False)   # SHA-256 of content
    file_size: int = field(init=False)  # Content size in bytes
    mtime: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    chunks: list[DocumentChunk] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
```

**Example:**
```python
document = Document(
    id="doc_abc123",
    collection_id="550e8400-e29b-41d4-a716-446655440000",
    path="~/Documents/notes/python/decorators.md",
    content="# Python Decorators\n\nDecorators are...",
    metadata={
        "tags": ["python", "advanced"],
    }
)
```

### DocumentChunk (Domain Entity)

Represents a chunk of a document for embedding and search.

```python
from docsift.core.models import DocumentChunk
from dataclasses import dataclass, field
from typing import Any

@dataclass
class DocumentChunk:
    content: str               # Chunk content
    sequence: int              # Sequence number in document
    start_pos: int             # Start position in document
    end_pos: int               # End position in document
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str | None = None
    token_count: int = 0
    embedding: list[float] | None = None
    embedding_id: str | None = None
```

**Example:**
```python
chunk = DocumentChunk(
    id="chunk_xyz789",
    document_id="doc_abc123",
    content="Decorators are a powerful feature...",
    sequence=0,
    start_pos=0,
    end_pos=256,
    token_count=128,
    embedding_id="emb_def456"
)
```

## Context Models

### PathContext (Domain Entity)

Domain entity representing search context for a path.

```python
from docsift.core.models import PathContext
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class PathContext:
    path: str                  # File or directory path
    context: str               # Context text
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    collection_id: str | None = None
    context_type: str = "path"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
```

**Context Types:**
- `global`: Applies to all searches (target_id="*")
- `collection`: Applies to searches in a specific collection
- `path`: Applies to searches in a specific path

**Example:**
```python
# Path context
path_ctx = PathContext(
    id="ctx_path",
    path="~/Documents/notes/python",
    context="These are my Python programming notes.",
    context_type="path"
)
```

## Search Models

### SearchType (Enum)

```python
from docsift.core.models import SearchType
from enum import Enum

class SearchType(str, Enum):
    BM25 = "bm25"       # Full-text search
    VECTOR = "vector"   # Semantic search
    HYBRID = "hybrid"   # Combined search
    HYDE = "hyde"       # Hypothetical document embedding
    EXPAND = "expand"   # Query expansion
```

### SearchOptions (Dataclass)

Options for controlling search behavior.

```python
from docsift.core.models import SearchOptions
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class SearchOptions:
    limit: int = 10
    offset: int = 0
    collection_ids: list[str] | None = None
    min_score: float = 0.0
    include_content: bool = False
    include_highlights: bool = True
    max_highlights: int = 3
    explain: bool = False
    candidate_limit: int = 20
    intent: str | None = None
    snippet_max_length: int = 300
```

**Example:**
```python
options = SearchOptions(
    limit=20,
    min_score=0.5,
    include_content=True,
    candidate_limit=50
)
```

### SearchResult (Dataclass)

A single search result.

```python
from docsift.core.models import SearchResult
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class SearchResult:
    document_id: str
    title: str
    path: str
    collection_name: str
    score: float
    content: str | None = None
    highlights: list[str] = field(default_factory=list)
    rank: int = 0
    scores: dict[str, float | None] = field(default_factory=dict)
    snippet: str | None = None
    context_description: str | None = None
```

**Example:**
```python
result = SearchResult(
    document_id="doc_abc123",
    title="Python Decorators",
    path="~/notes/python/decorators.md",
    collection_name="my-notes",
    score=0.89,
    highlights=["decorators are a powerful"],
    snippet="Python decorators are a powerful feature..."
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
    MODELSCOPE = "modelscope"
```

### EmbeddingConfig (Pydantic Model)

```python
from docsift.models.embedding import EmbeddingConfig
from pydantic import BaseModel, Field

class EmbeddingConfig(BaseModel):
    model_type: ModelType = Field(ModelType.GGUF, description="Model type")
    model_path: str | None = Field(None, description="Path to model file")
    model_name: str = Field("all-MiniLM-L6-v2", description="Model name or identifier")

    # Model parameters
    embedding_dim: int = Field(1024, ge=1, description="Embedding dimension")
    max_tokens: int = Field(512, ge=1, description="Maximum tokens per input")
    batch_size: int = Field(32, ge=1, description="Batch size for inference")

    # GGUF specific
    n_gpu_layers: int = Field(0, ge=0, description="Number of GPU layers")
    n_ctx: int = Field(2048, ge=512, description="Context size")

    # API keys (for remote models)
    api_key: str | None = Field(None, exclude=True)
    api_base: str | None = None

    # Caching
    cache_embeddings: bool = Field(True, description="Cache embeddings")
    cache_dir: str | None = None
```

**Example:**
```python
# Sentence Transformer config
st_config = EmbeddingConfig(
    model_type=ModelType.SENTENCE_TRANSFORMERS,
    model_name="all-MiniLM-L6-v2",
    embedding_dim=384
)

# GGUF config
gguf_config = EmbeddingConfig(
    model_type=ModelType.GGUF,
    model_path="~/models/embedding.gguf",
    embedding_dim=1024
)

# ModelScope config
modelscope_config = EmbeddingConfig(
    model_type=ModelType.MODELSCOPE,
    model_name="Qwen/Qwen3-Embedding-0.6B",
    embedding_dim=1024
)
```

### EmbeddingModelInfo (Pydantic Model)

```python
from docsift.models.embedding import EmbeddingModelInfo
from pydantic import BaseModel, Field, ConfigDict

class EmbeddingModelInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Model ID")
    name: str = Field(..., description="Model name")
    model_type: ModelType = Field(...)
    embedding_dim: int = Field(..., ge=1)
    max_tokens: int = Field(..., ge=1)
    loaded: bool = Field(False, description="Whether model is loaded")
    device: str | None = None
```

### EmbeddingRequest / EmbeddingResponse (Pydantic Models)

```python
from docsift.models.embedding import EmbeddingRequest, EmbeddingResponse
from pydantic import BaseModel, Field

class EmbeddingRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, description="Texts to embed")
    normalize: bool = Field(True, description="Normalize embeddings")

class EmbeddingResponse(BaseModel):
    embeddings: list[list[float]] = Field(..., description="Generated embeddings")
    model_id: str = Field(..., description="Model used")
    dimensions: int = Field(..., ge=1)
    total_tokens: int = Field(..., ge=0)
    processing_time_ms: float = Field(..., ge=0)
```

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
- `path`: Must be a valid directory path

### Document
- `path`: Must be valid file path
- `content`: Non-empty string
- `checksum`: Valid SHA-256 hash (computed automatically)

### Search
- `query`: 1-1000 characters
- `limit`: 1-100
- `min_score`: 0.0-1.0

### Context
- `content`: 1-5000 characters
- `context_type`: Must be one of defined types

## Serialization

All domain models support JSON serialization via `to_dict()` and `from_dict()`:

```python
from docsift.core.models import Collection, SearchResult
import json

# Serialize
collection = Collection(name="my-notes", path="~/notes")
data = collection.to_dict()
json_str = json.dumps(data, indent=2)

# Deserialize
restored = Collection.from_dict(data)
```

Pydantic models support standard Pydantic serialization:

```python
from docsift.models.embedding import EmbeddingConfig

# Serialize
config = EmbeddingConfig(model_type=ModelType.GGUF)
json_str = config.model_dump_json(indent=2)

# Deserialize
restored = EmbeddingConfig.model_validate_json(json_str)

# To dict
data = config.model_dump()
```

## Related Documentation

- [API Reference](api-reference.md) - Python API usage
- [Architecture](architecture.md) - Data flow and storage
- [Search Algorithms](search-algorithms.md) - Search model usage
