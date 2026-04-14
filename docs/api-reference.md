# Python API Reference

Complete reference for DocSift's Python API.

## Core Module

### Collection

Domain entity representing a document collection.

```python
from docsift import Collection
```

#### Class: `Collection`

```python
@dataclass
class Collection:
    id: str
    name: str
    description: str | None = None
    paths: list[str] = field(default_factory=list)
    document_count: int = 0
    chunk_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_indexed_at: datetime | None = None
```

#### Methods

##### `add_path(path: str) -> None`

Add a path to the collection.

```python
collection = Collection(id="uuid", name="my-notes")
collection.add_path("~/Documents/notes")
collection.add_path("~/Documents/ideas")
```

##### `remove_path(path: str) -> None`

Remove a path from the collection.

```python
collection.remove_path("~/Documents/old-notes")
```

##### `update_metadata(**kwargs: Any) -> None`

Update collection metadata.

```python
collection.update_metadata(category="programming", priority="high")
```

##### `mark_indexed() -> None`

Mark the collection as indexed.

```python
collection.mark_indexed()
```

### CollectionManager

High-level manager for collection operations.

```python
from docsift import CollectionManager
from docsift.database.repository import SQLiteCollectionRepository

# Create manager with repository
repository = SQLiteCollectionRepository(db_connection)
manager = CollectionManager(repository)
```

#### Methods

##### `create_collection(name: str, description: str | None = None, paths: list[str] | None = None, metadata: dict[str, Any] | None = None) -> Collection`

Create a new collection.

```python
collection = manager.create_collection(
    name="my-notes",
    description="Personal notes",
    paths=["~/Documents/notes"],
    metadata={"category": "personal"}
)
```

**Raises:**
- `ValueError`: If collection name already exists

##### `get_collection(collection_id: str) -> Collection | None`

Get a collection by ID.

```python
collection = manager.get_collection("uuid-string")
if collection:
    print(f"Found: {collection.name}")
```

##### `list_collections() -> list[Collection]`

List all collections.

```python
collections = manager.list_collections()
for collection in collections:
    print(f"{collection.name}: {collection.document_count} documents")
```

##### `update_collection(collection_id: str, name: str | None = None, description: str | None = None) -> Collection`

Update a collection.

```python
updated = manager.update_collection(
    collection_id="uuid-string",
    description="Updated description"
)
```

**Raises:**
- `ValueError`: If collection not found

##### `delete_collection(collection_id: str) -> bool`

Delete a collection.

```python
success = manager.delete_collection("uuid-string")
```

##### `add_path(collection_id: str, path: str) -> Collection`

Add a path to a collection.

```python
collection = manager.add_path("uuid-string", "~/Documents/more-notes")
```

##### `remove_path(collection_id: str, path: str) -> Collection`

Remove a path from a collection.

```python
collection = manager.remove_path("uuid-string", "~/Documents/old-notes")
```

### Document

Domain entity representing an indexed document.

```python
from docsift import Document
```

#### Class: `Document`

```python
@dataclass
class Document:
    id: str
    collection_id: str
    path: str
    content: str
    checksum: str
    file_size: int
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    indexed_at: datetime | None = None
```

### DocumentChunk

Represents a chunk of a document.

```python
from docsift import DocumentChunk
```

#### Class: `DocumentChunk`

```python
@dataclass
class DocumentChunk:
    id: str
    document_id: str
    content: str
    start_line: int
    end_line: int
    token_count: int
    embedding_id: str | None = None
```

### Context

Domain entity representing search context.

```python
from docsift import Context, ContextManager
```

#### Class: `Context`

```python
@dataclass
class Context:
    id: str
    content: str
    context_type: str  # 'collection', 'path', 'document', 'global'
    target_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
```

## Models Module

### Search Models

```python
from docsift.models.search import SearchQuery, SearchResult, SearchOptions, SearchType
```

#### Enum: `SearchType`

```python
class SearchType(str, Enum):
    BM25 = "bm25"
    VECTOR = "vector"
    HYBRID = "hybrid"
```

#### Class: `SearchOptions`

```python
class SearchOptions(BaseModel):
    limit: int = Field(10, ge=1, le=100)
    offset: int = Field(0, ge=0)
    threshold: float = Field(0.0, ge=0, le=1)
    include_chunks: bool = True
    include_metadata: bool = True
    highlight_matches: bool = True
    
    # BM25 options
    bm25_k1: float = Field(1.5, ge=0.1, le=3.0)
    bm25_b: float = Field(0.75, ge=0.1, le=1.0)
    
    # Vector options
    vector_weight: float = Field(0.7, ge=0, le=1)
    
    # Hybrid options
    bm25_weight: float = Field(0.3, ge=0, le=1)
    rrf_k: int = Field(60, ge=1)
    
    # Query expansion
    expand_query: bool = False
    expansion_factor: int = Field(3, ge=1, le=10)
    
    # Reranking
    rerank: bool = False
    rerank_top_k: int = Field(20, ge=1, le=100)
```

**Usage:**
```python
options = SearchOptions(
    limit=20,
    threshold=0.5,
    expand_query=True,
    rerank=True
)
```

#### Class: `SearchQuery`

```python
class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1)
    collection_ids: list[str] | None = None
    search_type: SearchType = SearchType.HYBRID
    options: SearchOptions = Field(default_factory=SearchOptions)
    filters: dict[str, Any] = Field(default_factory=dict)
```

**Usage:**
```python
query = SearchQuery(
    query="python decorators",
    collection_ids=["collection-uuid"],
    search_type=SearchType.HYBRID,
    options=SearchOptions(limit=15)
)
```

#### Class: `SearchResult`

```python
class SearchResult(BaseModel):
    document_id: str
    document_path: str
    document_title: str | None = None
    score: float
    bm25_score: float | None = None
    vector_score: float | None = None
    content_preview: str | None = None
    matched_chunks: list[dict[str, Any]] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
```

#### Class: `SearchResponse`

```python
class SearchResponse(BaseModel):
    query: str
    search_type: SearchType
    total: int
    results: list[SearchResult]
    search_time_ms: float
    expanded_query: str | None = None
    expansion_terms: list[str] = Field(default_factory=list)
```

### Collection Models

```python
from docsift.models.collection import CollectionCreate, CollectionUpdate, CollectionResponse
```

#### Class: `CollectionCreate`

```python
class CollectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    paths: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
```

#### Class: `CollectionUpdate`

```python
class CollectionUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    paths: list[str] | None = None
    metadata: dict[str, Any] | None = None
```

#### Class: `CollectionResponse`

```python
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

## Search Module

### Search Strategies

```python
from docsift.search.strategy import SearchStrategy, SearchContext
from docsift.search.bm25 import BM25SearchStrategy
from docsift.search.vector import VectorSearchStrategy
from docsift.search.hybrid import HybridSearchStrategy
```

#### Class: `SearchContext`

```python
@dataclass
class SearchContext:
    query: str
    query_embedding: list[float] | None = None
    expanded_query: str | None = None
    collection_ids: list[str] | None = None
    context_string: str = ""
    filters: dict[str, Any] | None = None
```

#### Class: `SearchStrategy` (Abstract)

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

#### Class: `BM25SearchStrategy`

BM25 full-text search implementation.

```python
strategy = BM25SearchStrategy(repository)

context = SearchContext(query="python decorators")
options = SearchOptions(limit=10)

results = strategy.search(context, options)
```

#### Class: `VectorSearchStrategy`

Vector similarity search implementation.

```python
strategy = VectorSearchStrategy(repository, embedding_model)

# Query embedding must be provided
context = SearchContext(
    query="python decorators",
    query_embedding=embedding_model.embed(["python decorators"])[0]
)

results = strategy.search(context, options)
```

#### Class: `HybridSearchStrategy`

Combined BM25 and vector search with RRF fusion.

```python
strategy = HybridSearchStrategy(
    bm25_strategy=BM25SearchStrategy(repository),
    vector_strategy=VectorSearchStrategy(repository, embedding_model),
    rrf_k=60
)

results = strategy.search(context, options)
```

### RRF (Reciprocal Rank Fusion)

```python
from docsift.search.rrf import reciprocal_rank_fusion
```

#### Function: `reciprocal_rank_fusion`

```python
def reciprocal_rank_fusion(
    results_list: list[list[tuple[str, float]]],
    k: int = 60,
) -> list[tuple[str, float]]:
    """Fuse multiple ranked lists using RRF.
    
    Args:
        results_list: List of ranked result lists, each containing
                     (document_id, score) tuples
        k: RRF constant (default: 60)
    
    Returns:
        Fused and sorted results
    """
```

**Usage:**
```python
from docsift.search.rrf import reciprocal_rank_fusion

bm25_results = [("doc1", 0.9), ("doc2", 0.8)]
vector_results = [("doc2", 0.95), ("doc1", 0.85)]

fused = reciprocal_rank_fusion([bm25_results, vector_results], k=60)
# Result: [("doc2", 0.0325), ("doc1", 0.0321)]
```

## Database Module

### Repository

```python
from docsift.database.repository import SQLiteCollectionRepository
```

#### Class: `SQLiteCollectionRepository`

```python
class SQLiteCollectionRepository:
    def __init__(self, connection: DatabaseConnection) -> None: ...
    
    def get_by_id(self, collection_id: str) -> Collection | None: ...
    def get_by_name(self, name: str) -> Collection | None: ...
    def list_all(self) -> list[Collection]: ...
    def create(self, collection: Collection) -> Collection: ...
    def update(self, collection: Collection) -> Collection: ...
    def delete(self, collection_id: str) -> bool: ...
    def exists(self, name: str) -> bool: ...
```

### Connection

```python
from docsift.database.connection import DatabaseConnection
```

#### Class: `DatabaseConnection`

```python
class DatabaseConnection:
    def __init__(self, db_path: str) -> None: ...
    
    def connect(self) -> None: ...
    def close(self) -> None: ...
    def execute(self, query: str, parameters: tuple = ()) -> sqlite3.Cursor: ...
    def executemany(self, query: str, parameters: list) -> sqlite3.Cursor: ...
    def commit(self) -> None: ...
```

**Usage:**
```python
from docsift.database.connection import DatabaseConnection

conn = DatabaseConnection("~/.local/share/docsift/docsift.db")
conn.connect()

cursor = conn.execute("SELECT * FROM collections WHERE name = ?", ("my-notes",))
rows = cursor.fetchall()

conn.close()
```

## Embedding Module

### Embedding Model

```python
from docsift.embedding.model import EmbeddingModel
from docsift.embedding.factory import EmbeddingModelFactory
```

#### Class: `EmbeddingModel` (Abstract)

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

#### Class: `EmbeddingModelFactory`

```python
class EmbeddingModelFactory:
    @staticmethod
    def create_sentence_transformer(model_name: str) -> EmbeddingModel: ...
    
    @staticmethod
    def create_gguf(model_path: str) -> EmbeddingModel: ...
```

**Usage:**
```python
from docsift.embedding.factory import EmbeddingModelFactory

# Sentence Transformer
model = EmbeddingModelFactory.create_sentence_transformer("all-MiniLM-L6-v2")
model.load()

embeddings = model.embed([
    "First document",
    "Second document"
])

print(f"Dimension: {model.dimension}")  # 384
```

### Embedding Manager

```python
from docsift.embedding.manager import EmbeddingManager
```

#### Class: `EmbeddingManager`

```python
class EmbeddingManager:
    def __init__(self, model: EmbeddingModel, cache: EmbeddingCache | None = None) -> None: ...
    
    def embed_documents(
        self,
        documents: list[Document],
        batch_size: int = 32,
    ) -> dict[str, list[float]]: ...
    
    def embed_query(self, query: str) -> list[float]: ...
```

## MCP Server Module

### MCPServer

```python
from docsift.mcp_server.server import MCPServer
from docsift.mcp_server.transport import StdioTransport, HttpTransport
```

#### Class: `MCPServer`

```python
class MCPServer:
    def __init__(self, transport: Transport) -> None: ...
    def start(self) -> None: ...
    def stop(self) -> None: ...
    @property
    def is_running(self) -> bool: ...
```

**Usage:**
```python
from docsift.mcp_server.server import MCPServer
from docsift.mcp_server.transport import StdioTransport

transport = StdioTransport()
server = MCPServer(transport)
server.start()
```

## Examples

### Complete Search Example

```python
from docsift.database.connection import DatabaseConnection
from docsift.database.repository import SQLiteCollectionRepository
from docsift.embedding.factory import EmbeddingModelFactory
from docsift.search.bm25 import BM25SearchStrategy
from docsift.search.vector import VectorSearchStrategy
from docsift.search.hybrid import HybridSearchStrategy
from docsift.search.strategy import SearchContext
from docsift.models.search import SearchQuery, SearchOptions, SearchType

# Setup
conn = DatabaseConnection("~/.local/share/docsift/docsift.db")
conn.connect()

repository = SQLiteCollectionRepository(conn)

# Create embedding model
model = EmbeddingModelFactory.create_sentence_transformer("all-MiniLM-L6-v2")
model.load()

# Create search strategies
bm25 = BM25SearchStrategy(repository)
vector = VectorSearchStrategy(repository, model)
hybrid = HybridSearchStrategy(bm25, vector, rrf_k=60)

# Search
query_text = "python decorators"
query_embedding = model.embed([query_text])[0]

context = SearchContext(
    query=query_text,
    query_embedding=query_embedding,
    collection_ids=None  # Search all collections
)

options = SearchOptions(
    limit=10,
    threshold=0.3,
    expand_query=True
)

results = hybrid.search(context, options)

# Display results
for result in results:
    print(f"[{result.score:.2f}] {result.document_path}")
    print(f"    {result.content_preview[:100]}...")

conn.close()
```

### Collection Management Example

```python
from docsift import CollectionManager
from docsift.database.connection import DatabaseConnection
from docsift.database.repository import SQLiteCollectionRepository

# Setup
conn = DatabaseConnection("~/.local/share/docsift/docsift.db")
conn.connect()

repository = SQLiteCollectionRepository(conn)
manager = CollectionManager(repository)

# Create collection
collection = manager.create_collection(
    name="my-notes",
    description="Personal notes",
    paths=["~/Documents/notes"]
)

# List collections
collections = manager.list_collections()
for c in collections:
    print(f"{c.name}: {c.document_count} documents")

# Update collection
updated = manager.update_collection(
    collection_id=collection.id,
    description="Updated description"
)

# Add path
manager.add_path(collection.id, "~/Documents/ideas")

# Delete collection
manager.delete_collection(collection.id)

conn.close()
```

### Custom Search Strategy Example

```python
from docsift.search.strategy import SearchStrategy, SearchContext
from docsift.models.search import SearchOptions, SearchResult

class CustomSearchStrategy(SearchStrategy):
    """Custom search strategy example."""
    
    def __init__(self, repository):
        self._repository = repository
    
    def search(
        self,
        context: SearchContext,
        options: SearchOptions,
    ) -> list[SearchResult]:
        # Custom search logic
        results = []
        
        # ... implement custom search ...
        
        return results
    
    def search_batch(
        self,
        contexts: list[SearchContext],
        options: SearchOptions,
    ) -> list[list[SearchResult]]:
        return [self.search(ctx, options) for ctx in contexts]
```

## Type Hints

DocSift uses full type hints throughout. Key types:

```python
from typing import Any, Protocol
from datetime import datetime

# Entity IDs
CollectionId = str
DocumentId = str
ChunkId = str
ContextId = str

# Embeddings
Embedding = list[float]
EmbeddingBatch = list[Embedding]

# Search results
RawResult = tuple[str, float]  # (document_id, score)
RawResults = list[RawResult]
```

## Error Handling

DocSift uses exceptions for error handling:

```python
class DocSiftError(Exception):
    """Base exception for DocSift."""
    pass

class CollectionNotFoundError(DocSiftError):
    """Raised when a collection is not found."""
    pass

class DocumentNotFoundError(DocSiftError):
    """Raised when a document is not found."""
    pass

class IndexError(DocSiftError):
    """Raised when an indexing operation fails."""
    pass
```

**Usage:**
```python
from docsift.core.collection import CollectionManager

try:
    collection = manager.get_collection("non-existent-id")
    if not collection:
        raise CollectionNotFoundError(f"Collection not found")
except ValueError as e:
    print(f"Error: {e}")
```
