# Python API Reference

Complete reference for SIF's Python API.

## Core Module

### Collection

Domain entity representing a document collection.

```python
from sif.core.collection import Collection
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
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
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
from sif.core.collection import CollectionManager

# Create manager with a CollectionRepository implementation
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
from sif.core.document import Document
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
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    chunks: list[DocumentChunk] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    indexed_at: datetime | None = None
```

### DocumentChunk

Represents a chunk of a document.

```python
from sif.core.document import DocumentChunk
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
    embedding: list[float] | None = None
```

### Context

Domain entity representing search context.

```python
from sif.core.context import Context, ContextManager
```

#### Class: `Context`

```python
@dataclass
class Context:
    id: str
    content: str
    context_type: ContextType
    target_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
```

## Models Module

### Search Models

```python
from sif.models.search import SearchQuery, SearchResult, SearchOptions, SearchType
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
from sif.core.models import SearchOptions
from dataclasses import dataclass

@dataclass
class SearchOptions:
    limit: int = 10
    offset: int = 0
    # None = no collection filter; [] = exclude all collections
    collection_ids: list[str] | None = None
    min_score: float = 0.0
    include_content: bool = False
    include_highlights: bool = True
    max_highlights: int = 3
    explain: bool = False
    # Reranker candidate pool (over-fetch target, clamped 5-50; default 20)
    candidate_limit: int = 20
    intent: str | None = None
    snippet_max_length: int = 300
    # Hybrid fusion tunables (Phase 15): settings/flags resolve INTO these
    rrf_k: int = 60
    bm25_weight: float = 1.0
    vector_weight: float = 1.0
```

**Usage:**
```python
# Equal weights and k=60 reproduce the unweighted default (byte-identical)
options = SearchOptions(limit=10, include_highlights=False)

# Weighted fusion, resolved from SIF_ settings or per-query flags
options = SearchOptions(limit=10, rrf_k=40, bm25_weight=0.7, vector_weight=0.3)

# Reranker over-fetch pool (used only on the enabled --rerank path)
options = SearchOptions(limit=10, candidate_limit=30)
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
from sif.models.collection import CollectionCreate, CollectionUpdate, CollectionResponse
```

#### Class: `CollectionCreate`

```python
class CollectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None)
    paths: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
```

#### Class: `CollectionUpdate`

```python
class CollectionUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
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
from sif.search.strategy import SearchStrategy, SearchContext
from sif.search.bm25 import BM25Searcher
from sif.search.vector import VectorSearcher
from sif.search.hybrid import HybridSearcher
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

#### Class: `BM25Searcher`

BM25 full-text search implementation using SQLite FTS5. Takes a `sqlite3.Connection`.

```python
searcher = BM25Searcher(conn)

options = SearchOptions(limit=10)

results = searcher.search("python decorators", options)
```

#### Class: `VectorSearcher`

Vector similarity search implementation using sqlite-vec. Takes a `sqlite3.Connection` and the embedding dimension; raises `RuntimeError` when the sqlite-vec extension is unavailable.

```python
searcher = VectorSearcher(conn, embedding_dim)

# Query embedding must be provided (embedder implements the Embedder protocol)
query_embedding = embedder.embed("python decorators")

results = searcher.search(query_embedding, options)
```

#### Class: `HybridSearcher`

Combined BM25 and vector search with RRF fusion. Constructs its own `BM25Searcher` and `VectorSearcher` from the shared connection and fuses them with `RRFFusion(k=60)`.

```python
searcher = HybridSearcher(conn, embedder=embedder, embedding_dim=384)

results = searcher.search("python decorators", options)
```

### RRF (Reciprocal Rank Fusion)

```python
from sif.search.rrf import RRFFusion, compute_rrf_score
```

#### Class: `RRFFusion`

```python
class RRFFusion:
    def __init__(self, k: int = 60) -> None: ...

    def fuse(
        self,
        results_lists: list[list[SearchResult]],
        limit: int = 10,
        weights: list[float] | None = None,
        k: int | None = None,
    ) -> list[SearchResult]: ...
```

`weights` is a per-list multiplier in multiply form — `weight * 1/(k + rank)`
— and is never normalized. `weights=None` means `1.0` for every list (the
byte-identical default). `k=None` falls back to the constructor `k`; a
per-call `k` overrides it without mutating the instance.

#### Function: `compute_rrf_score`

```python
def compute_rrf_score(rank: int, k: int = 60) -> float:
    """Compute the RRF score 1 / (k + rank) for a single 1-indexed rank."""
```

**Usage:**
```python
from sif.search.rrf import RRFFusion

rrf = RRFFusion(k=60)
# Default: equal weights, k=60 — byte-identical to plain RRF
fused = rrf.fuse([bm25_results, vector_results], limit=10)
# Weighted fusion (multiply form, never normalized)
fused = rrf.fuse(
    [bm25_results, vector_results],
    limit=10,
    weights=[0.7, 0.3],
    k=40,
)
```

## Benchmark Module

```python
from sif.search.benchmark import (
    BenchReport, ConfigResult, QueryItem, SearchEvaluator, SweepRanking,
    dcg_at_k, hit_at_k, iter_grid, ndcg_at_k, percentile, rank_sweep,
    warrants_default_change,
)
```

Graded metric helpers (pure functions):

```python
# Exponential-gain DCG/nDCG; the ideal comes from the FULL judgment set
dcg_at_k([3, 0, 2], 10)          # 8.5
ndcg_at_k([3, 0, 2], [3, 2], 10)  # 0.95583058934618

# Hit@k: 1.0 iff any of the top-k grades is positive
hit_at_k([0, 3], 10)             # 1.0

# Linear-interpolation percentile; p in [0, 100]
percentile([10.0, 20.0, 30.0, 40.0], 50)  # 25.0
```

The held-out defaults rule (inclusive at exactly 0.01 on the delta rounded to
6 decimals — the same arithmetic the sweep tie rule uses):

```python
warrants_default_change(0.500, 0.510)    # True  (delta exactly 0.01)
warrants_default_change(0.500, 0.5099)   # False (sub-delta noise)
```

#### Class: `SearchEvaluator`

```python
evaluator = SearchEvaluator(fixture, fixture_path=Path("tests/fixtures/bench/queries.json"))
report = evaluator.report(lambda query: pipeline.search(query, options), k=10)
# report.ndcg_at_10 / report.hit_at_10 / report.num_queries
# report.categories["keyword"].ndcg_at_10  (per-category breakdown)
# report.p50_ms / report.p95_ms warmed; report.cold_start_ms separate
```

`fixture_path` (never a bare corpus root) lets `resolve_corpus_root` join the
fixture's declared `corpus_root` so path-keyed relevance joins result paths.

#### Dataclasses: `QueryItem`, `BenchReport`, `ConfigResult`, `SweepRanking`

- `QueryItem` — one query with category, split, and its grade map
- `BenchReport` — graded report with per-category `CategoryMetrics` and legacy
  flat metrics merged by `to_dict()`
- `ConfigResult` — one measured sweep configuration (four-category breakdown,
  optional rerank `states`); `to_dict()` serializes all four category keys
- `SweepRanking` — ranked configs plus the explicit tie group and
  `winner_declared` honesty flag

#### Sweep Engine

```python
results = [...]  # list[ConfigResult], measured on the tuning split only
ranking = rank_sweep(results)   # strict < 0.01 tie rule on round(delta, 6)
ranking.ranked[0]               # best: declared grid order breaks ties
ranking.tie_group               # configs within 0.01 of the best
ranking.winner_declared         # False whenever the tie group is plural

list(iter_grid())               # the 45 declared configurations, grid order
```

CLI surfaces: `sif bench FIXTURE --json` (current-settings baseline),
`sif bench FIXTURE --sweep --json` (tuning-only grid ranking), and
`sif bench FIXTURE --sweep --rerank --json` (off/on rerank states per
configuration). See [Benchmarking](benchmarking.md) for the measurement
contract and the committed evidence snapshot.

## Database Module

### Repository

```python
from sif.database.repository import CollectionRepository
```

#### Class: `CollectionRepository` (Abstract)

Abstract base class. Concrete SQLite implementations live in `sif.database.repositories` and take a `sqlite3.Connection`.

```python
class CollectionRepository(Repository[Collection], ABC):
    @abstractmethod
    def get_by_id(self, entity_id: str) -> Collection | None: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Collection | None: ...

    @abstractmethod
    def list_all(self) -> list[Collection]: ...

    @abstractmethod
    def create(self, entity: Collection) -> Collection: ...

    @abstractmethod
    def update(self, entity: Collection) -> Collection: ...

    @abstractmethod
    def delete(self, entity_id: str) -> bool: ...

    @abstractmethod
    def exists(self, name: str) -> bool: ...
```

### Connection

```python
from sif.database.connection import DatabaseConnection
```

#### Class: `DatabaseConnection`

```python
class DatabaseConnection:
    def __init__(self, db_path: Path | str) -> None: ...

    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]: ...

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]: ...

    def execute(
        self, query: str, parameters: tuple | dict | None = None
    ) -> sqlite3.Cursor: ...

    def executemany(
        self, query: str, parameters: list[tuple | dict]
    ) -> sqlite3.Cursor: ...

    def fetchone(
        self, query: str, parameters: tuple | dict | None = None
    ) -> sqlite3.Row | None: ...

    def fetchall(
        self, query: str, parameters: tuple | dict | None = None
    ) -> list[sqlite3.Row]: ...
```

`connect()` and `transaction()` are context managers. There are no `close()` or `commit()` methods: a connection is opened and closed per call, and `transaction()` commits on success and rolls back on exception.

**Usage:**
```python
from pathlib import Path

from sif.database.connection import DatabaseConnection

conn = DatabaseConnection(Path("~/.local/share/sif/sif.db").expanduser())

with conn.connect() as db:
    cursor = db.execute("SELECT * FROM collections WHERE name = ?", ("my-notes",))
    rows = cursor.fetchall()
```

## Embedding Module

### Embedding Model

```python
from sif.embedding.model import EmbeddingModel
from sif.embedding.factory import EmbeddingModelFactory
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
    def embedding_dim(self) -> int: ...
```

#### Class: `EmbeddingModelFactory`

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

Supported `ModelType` values: `SENTENCE_TRANSFORMERS`, `GGUF`, `OPENAI`, `MODELSCOPE` (`HUGGINGFACE` raises `NotImplementedError`). GGUF models require `model_path`.

**Usage:**
```python
from sif.embedding.factory import EmbeddingModelFactory
from sif.models.embedding import ModelType

factory = EmbeddingModelFactory()
embedder = factory.create_model(
    model_type=ModelType.SENTENCE_TRANSFORMERS,
    model_path=None,
    model_name="all-MiniLM-L6-v2",
)

embeddings = embedder.embed_batch([
    "First document",
    "Second document"
])

print(f"Dimension: {embedder.dimension}")  # 384
```

### Embedding Manager

```python
from sif.embedding.manager import EmbeddingManager
```

#### Class: `EmbeddingManager`

```python
class EmbeddingManager:
    def __init__(
        self,
        config: EmbeddingConfig | None = None,
        factory: EmbeddingModelFactory | None = None,
        cache: EmbeddingCache | None = None,
    ) -> None: ...

    @classmethod
    def from_settings(cls, settings: Settings) -> EmbeddingManager: ...

    def load_model(self) -> None: ...

    def unload_model(self) -> None: ...

    def embed(
        self,
        texts: list[str],
        normalize: bool = True,
        use_cache: bool = True,
    ) -> EmbeddingResponse: ...

    def embed_single(
        self,
        text: str,
        normalize: bool = True,
        use_cache: bool = True,
    ) -> list[float]: ...
```

## MCP Server Module

### MCPServer

```python
from sif.mcp.server import MCPServer
from sif.mcp.transports.stdio import StdioTransport
from sif.mcp.transports.http import HTTPTransport
```

#### Class: `MCPServer`

```python
class MCPServer:
    def __init__(self, backend: SearchBackend) -> None: ...

    def register_tools(self, tools: list[ToolHandler]) -> None: ...

    async def handle_request(self, request: JsonRpcRequest) -> JsonRpcResponse: ...

    async def handle_notification(self, notification: JsonRpcNotification) -> None: ...
```

Transports wrap a server: `StdioTransport(server, stdin=None, stdout=None)` runs a stdin/stdout loop via `await transport.run()`, and `HTTPTransport(server, host="127.0.0.1", port=3000, cors_origins=None)` serves it with FastAPI via `transport.run()`.

**Usage:**
```python
from pathlib import Path

from sif.mcp.backend import SearchBackend
from sif.mcp.handlers import create_default_tools
from sif.mcp.server import MCPServer
from sif.mcp.transports.stdio import StdioTransport

server = MCPServer(SearchBackend(str(Path("~/.local/share/sif/sif.db").expanduser())))
server.register_tools(create_default_tools())

transport = StdioTransport(server)
```

Module-level runners wire everything together: `run_stdio_server_sync(db_path)` (also `run_stdio_server`) and `run_http_server(db_path, host, port, cors_origins)`.

## Examples

### Complete Search Example

```python
import sqlite3
from pathlib import Path

from sif.core.models import SearchOptions
from sif.embedding.factory import EmbeddingModelFactory
from sif.models.embedding import ModelType
from sif.search.hybrid import HybridSearcher

# Create embedding model (implements the Embedder protocol)
factory = EmbeddingModelFactory()
embedder = factory.create_model(
    model_type=ModelType.SENTENCE_TRANSFORMERS,
    model_path=None,
    model_name="all-MiniLM-L6-v2",
)

db_path = Path("~/.local/share/sif/sif.db").expanduser()
with sqlite3.connect(str(db_path)) as db:
    # HybridSearcher builds BM25Searcher + VectorSearcher and fuses via RRF
    searcher = HybridSearcher(db, embedder=embedder, embedding_dim=384)

    # Search
    options = SearchOptions(limit=10, include_content=True)
    results = searcher.search("python decorators", options)

    # Display results
    for result in results:
        print(f"[{result.score:.2f}] {result.path}")
        if result.content:
            print(f"    {result.content[:100]}...")
```

### Collection Management Example

```python
from sif.core.collection import CollectionManager

# repository is any CollectionRepository implementation
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
```

### Custom Search Strategy Example

```python
from sif.search.strategy import SearchStrategy, SearchContext
from sif.models.search import SearchOptions, SearchResult

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

SIF uses full type hints throughout. Entity IDs are plain `str` values, embeddings are `list[float]`, and search methods return `list[SearchResult]`; the codebase defines no type aliases for these. Extensibility is provided by `Protocol` types such as `Embedder`, `Reranker`, and `QueryExpander` in `sif.core.models`.

## Error Handling

SIF defines no custom exception hierarchy; it raises built-in exceptions:

- `CollectionManager.create_collection` raises `ValueError` when a collection name already exists.
- `CollectionManager.update_collection`, `add_path`, and `remove_path` raise `ValueError` when the collection ID is not found; `get_collection` returns `None` instead of raising.
- `VectorSearcher.__init__` raises `RuntimeError` when the sqlite-vec extension is unavailable.

**Usage:**
```python
from sif.core.collection import CollectionManager

try:
    collection = manager.create_collection(name="my-notes")
except ValueError as e:
    print(f"Error: {e}")  # e.g. "Collection 'my-notes' already exists"
```
