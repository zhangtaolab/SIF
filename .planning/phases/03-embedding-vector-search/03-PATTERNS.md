# Phase 03: Embedding & Vector Search - Pattern Map

**Mapped:** 2026-04-16
**Files analyzed:** 18
**Analogs found:** 16 / 18

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/docsift/config/settings.py` | config | request-response | `src/docsift/config/settings.py` (self) | exact |
| `src/docsift/models/embedding.py` | model | request-response | `src/docsift/models/embedding.py` (self) | exact |
| `src/docsift/embedding/factory.py` | factory | request-response | `src/docsift/embedding/factory.py` (self) | exact |
| `src/docsift/embedding/embedder.py` | service | transform | `src/docsift/embedding/embedder.py` (self) | exact |
| `src/docsift/embedding/manager.py` | service | transform | `src/docsift/embedding/manager.py` (self) | exact |
| `src/docsift/database/schema.py` | service | CRUD | `src/docsift/database/schema.py` (self) | exact |
| `src/docsift/database/repositories.py` | repository | CRUD | `src/docsift/database/repositories.py` (self) | exact |
| `src/docsift/search/vector.py` | service | CRUD | `src/docsift/search/vector.py` (self) | exact |
| `src/docsift/search/hybrid.py` | service | request-response | `src/docsift/search/hybrid.py` (self) | exact |
| `src/docsift/cli/commands/search.py` | controller | request-response | `src/docsift/cli/commands/search.py` (self) | exact |
| `src/docsift/cli/commands/index.py` | controller | batch | `src/docsift/cli/commands/index.py` (self) | exact |
| `src/docsift/indexing/indexer.py` | service | batch | `src/docsift/indexing/indexer.py` (self) | exact |
| `tests/unit/config/test_settings.py` | test | request-response | `tests/unit/inference/test_embedder.py` | role-match |
| `tests/unit/embedding/test_factory.py` | test | request-response | `tests/unit/inference/test_embedder.py` | role-match |
| `tests/unit/database/test_schema.py` | test | CRUD | `tests/unit/db/test_database.py` | role-match |
| `tests/unit/search/test_vector.py` | test | request-response | `tests/unit/search/test_vector.py` (self) | exact |
| `tests/unit/cli/test_search.py` | test | request-response | `tests/unit/cli/test_search_commands.py` | role-match |
| `tests/unit/cli/test_index.py` | test | batch | `tests/unit/cli/test_index_commands.py` | role-match |

## Pattern Assignments

### `src/docsift/config/settings.py` (config, request-response)

**Analog:** `src/docsift/config/settings.py` (existing file)

**Imports pattern** (lines 1-11):
```python
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from docsift.config.constants import APP_NAME, DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE
```

**Settings class pattern** (lines 13-26):
```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DOCSIFT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
```

**Field definition pattern** (lines 43-61):
```python
model_name: str = Field(
    default="all-MiniLM-L6-v2",
    description="Embedding model name",
)
embedding_dim: int = Field(
    default=384,
    ge=1,
    description="Embedding dimension",
)
batch_size: int = Field(
    default=32,
    ge=1,
    description="Batch size for inference",
)
```

**Path validator pattern** (lines 118-126):
```python
@field_validator("db_path", "cache_dir", mode="before")
@classmethod
def expand_path(cls, v: str | Path | None) -> Path | None:
    if v is None:
        return None
    path = Path(v).expanduser()
    return path
```

**Cached getter pattern** (lines 158-164):
```python
@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

---

### `src/docsift/models/embedding.py` (model, request-response)

**Analog:** `src/docsift/models/embedding.py` (existing file)

**Enum pattern** (lines 9-16):
```python
class ModelType(str, Enum):
    GGUF = "gguf"
    SENTENCE_TRANSFORMERS = "sentence_transformers"
    OPENAI = "openai"
    HUGGINGFACE = "huggingface"
```

**Pydantic config model pattern** (lines 18-41):
```python
class EmbeddingConfig(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    model_type: ModelType = Field(ModelType.GGUF, description="Model type")
    model_path: str | None = Field(None, description="Path to model file")
    model_name: str = Field("all-MiniLM-L6-v2", description="Model name or identifier")
    embedding_dim: int = Field(384, ge=1, description="Embedding dimension")
    api_key: str | None = Field(None, exclude=True)
    api_base: str | None = None
```

---

### `src/docsift/embedding/factory.py` (factory, request-response)

**Analog:** `src/docsift/embedding/factory.py` (existing file)

**Imports pattern** (lines 1-6):
```python
from docsift.embedding.embedder import LlamaCppEmbedder, SentenceTransformerEmbedder
from docsift.embedding.model import EmbeddingModel, ModelType
from docsift.utils.logging import get_logger

logger = get_logger(__name__)
```

**Factory method pattern** (lines 14-30):
```python
class EmbeddingModelFactory:
    def create_model(
        self,
        model_type: ModelType,
        model_path: str | None,
        model_name: str,
        **kwargs: dict[str, any],
    ) -> EmbeddingModel:
        if model_type == ModelType.SENTENCE_TRANSFORMERS:
            return self._create_sentence_transformers_model(model_name, **kwargs)
        if model_type == ModelType.GGUF:
            return self._create_gguf_model(model_path, **kwargs)
        if model_type == ModelType.OPENAI:
            return self._create_openai_model(model_name, **kwargs)
        raise ValueError(f"Unsupported model type: {model_type}")
```

**Backend creator pattern** (lines 32-58):
```python
def _create_sentence_transformers_model(
    self,
    model_name: str,
    **kwargs: dict[str, any],
) -> EmbeddingModel:
    return SentenceTransformerEmbedder(
        model_name=model_name,
        device=kwargs.get("device"),
        cache_dir=kwargs.get("cache_dir"),
    )
```

---

### `src/docsift/embedding/embedder.py` (service, transform)

**Analog:** `src/docsift/embedding/embedder.py` (existing file)

**Optional import + clear error pattern** (lines 34-38):
```python
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    logger.error("sentence-transformers not installed. Install with: pip install sentence-transformers")
    raise
```

**Embedder protocol implementation pattern** (lines 18-89):
```python
class SentenceTransformerEmbedder(Embedder):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: Optional[str] = None, cache_dir: Optional[str] = None) -> None:
        # ... import, load model, set dimension ...
        self._dimension = self.model.get_sentence_embedding_dimension()

    def embed(self, text: str) -> List[float]:
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=len(texts) > 100)
        return embeddings.tolist()

    @property
    def dimension(self) -> int:
        return self._dimension
```

**ModelScope embedder pattern** (lines 157-226):
```python
class ModelScopeEmbedder(Embedder):
    def __init__(self, model_id: str = "iic/gte_Qwen2-7B-instruct", device: Optional[str] = None, cache_dir: Optional[str] = None, force_download: bool = False) -> None:
        downloader = ModelDownloader(cache_dir)
        model_path = downloader.download(model_id, force=force_download)
        # ... find actual model directory, load SentenceTransformer ...
```

---

### `src/docsift/embedding/manager.py` (service, transform)

**Analog:** `src/docsift/embedding/manager.py` (existing file)

**from_settings factory pattern** (lines 41-66):
```python
@classmethod
def from_settings(cls, settings: Settings) -> "EmbeddingManager":
    config = EmbeddingConfig(
        model_name=settings.model_name,
        model_path=str(settings.model_path) if settings.model_path else None,
        embedding_dim=settings.embedding_dim,
        max_tokens=settings.max_tokens,
        batch_size=settings.batch_size,
        n_gpu_layers=settings.n_gpu_layers,
        cache_embeddings=settings.cache_embeddings,
        cache_dir=str(settings.get_cache_dir()) if settings.cache_embeddings else None,
    )
    cache = None
    if config.cache_embeddings and config.cache_dir:
        cache = EmbeddingCache(config.cache_dir)
    return cls(config=config, cache=cache)
```

**Cache-aware embed pattern** (lines 95-156):
```python
def embed(self, texts: list[str], normalize: bool = True, use_cache: bool = True) -> EmbeddingResponse:
    self.load_model()
    # ... check cache, batch embed uncached, store in cache ...
    return EmbeddingResponse(
        embeddings=[e for e in embeddings if e is not None],
        model_id=self._model.model_id if self._model else "unknown",
        dimensions=self._config.embedding_dim,
        total_tokens=total_tokens,
        processing_time_ms=processing_time,
    )
```

**Single embed convenience pattern** (lines 158-175):
```python
def embed_single(self, text: str, normalize: bool = True, use_cache: bool = True) -> list[float]:
    response = self.embed([text], normalize=normalize, use_cache=use_cache)
    return response.embeddings[0]
```

---

### `src/docsift/database/schema.py` (service, CRUD)

**Analog:** `src/docsift/database/schema.py` (existing file)

**SchemaManager init pattern** (lines 9-14):
```python
class SchemaManager:
    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db
```

**Dynamic column addition pattern** (lines 26-31):
```python
def _add_column_if_missing(self, table: str, column: str, dtype: str) -> None:
    cursor = self.db.execute(f"PRAGMA table_info({table})")
    columns = {row["name"] for row in cursor.fetchall()}
    if column not in columns:
        self.db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {dtype}")
```

**FTS5 introspection + rebuild pattern** (lines 122-141):
```python
def _fts_is_misconfigured(table_name: str, expected_content: str) -> bool:
    cursor = self.db.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    row = cursor.fetchone()
    if not row:
        return False
    sql = row[0] or ""
    return f"content='{expected_content}'" not in sql

if needs_rebuild_docs:
    self.db.execute("DROP TABLE IF EXISTS documents_fts")
```

**Vector table creation pattern** (lines 220-249):
```python
def _create_vector_tables(self) -> None:
    try:
        self.db.execute("SELECT vec_version()")
        vec_available = True
    except sqlite3.OperationalError:
        vec_available = False

    if vec_available:
        self.db.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS document_embeddings USING vec0(
                embedding_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                chunk_id TEXT,
                embedding FLOAT[768]
            )
        """)
```

---

### `src/docsift/database/repositories.py` (repository, CRUD)

**Analog:** `src/docsift/database/repositories.py` (existing file)

**Repository init pattern** (lines 19-24):
```python
class CollectionRepository:
    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db
```

**CRUD create pattern** (lines 25-49):
```python
def create(self, collection: Collection) -> Collection:
    self.db.execute(
        """
        INSERT INTO collections (
            id, name, path, pattern, ignore_patterns, include_by_default,
            description, pre_update_cmd, created_at, updated_at, document_count, chunk_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (collection.id, collection.name, ...)
    )
    return collection
```

**Cascade delete pattern** (lines 225-236):
```python
def delete(self, document_id: str) -> bool:
    from docsift.database.repositories import DocumentChunkRepository
    chunk_repo = DocumentChunkRepository(self.db)
    chunk_repo.delete_by_document(document_id)
    cursor = self.db.execute("DELETE FROM documents WHERE id = ?", (document_id,))
    return cursor.rowcount > 0
```

**Row-to-model conversion pattern** (lines 276-292):
```python
def _row_to_document(self, row: sqlite3.Row) -> Document:
    doc = Document(
        id=row["id"],
        path=row["path"],
        collection_id=row["collection_id"],
        content=row["content"],
        title=row["title"],
    )
    doc.filename = row["filename"]
    doc.checksum = row["checksum"]
    doc.mtime = row["mtime"]
    doc.created_at = datetime.fromisoformat(row["created_at"])
    return doc
```

---

### `src/docsift/search/vector.py` (service, CRUD)

**Analog:** `src/docsift/search/vector.py` (existing file)

**sqlite-vec fail-fast pattern** (lines 14-22):
```python
def __init__(self, db: sqlite3.Connection, embedding_dim: int = 768) -> None:
    self.db = db
    self.embedding_dim = embedding_dim
    self._vec_available = self._check_vec_extension()
    if not self._vec_available:
        raise RuntimeError(
            "sqlite-vec extension is not available. "
            "Install sqlite-vec to use vector search."
        )
```

**vec_f32 insert pattern** (lines 117-144):
```python
def add_embedding(self, embedding_id: str, document_id: str, chunk_id: Optional[str], embedding: List[float]) -> None:
    embedding_str = self._embedding_to_vec(embedding)
    self.db.execute(
        """
        INSERT OR REPLACE INTO document_embeddings
        (embedding_id, document_id, chunk_id, embedding)
        VALUES (?, ?, ?, vec_f32(?))
        """,
        (embedding_id, document_id, chunk_id, embedding_str)
    )
```

**JSON array serialization pattern** (lines 103-107):
```python
def _embedding_to_vec(self, embedding: List[float]) -> str:
    return str(embedding).replace("'", '"')
```

---

### `src/docsift/search/hybrid.py` (service, request-response)

**Analog:** `src/docsift/search/hybrid.py` (existing file)

**Hybrid searcher init pattern** (lines 14-27):
```python
class HybridSearcher:
    def __init__(self, db: sqlite3.Connection, embedder: Optional[Embedder] = None, embedding_dim: int = 768) -> None:
        self.db = db
        self.embedder = embedder
        self.bm25 = BM25Searcher(db)
        self.vector = VectorSearcher(db, embedding_dim)
        self.rrf = RRFFusion(k=60)
```

**Conditional vector search pattern** (lines 49-59):
```python
vector_results: List[SearchResult] = []
if self.embedder is not None:
    query_embedding = self.embedder.embed(query)
    vector_results = self.vector.search(query_embedding, options)

if not vector_results:
    return bm25_results
```

---

### `src/docsift/cli/commands/search.py` (controller, request-response)

**Analog:** `src/docsift/cli/commands/search.py` (existing file)

**Click command pattern** (lines 222-239):
```python
@search_group.command("vsearch")
@click.argument("query")
@click.option("-n", "--limit", default=10, help="Number of results")
@click.pass_context
def vsearch_cmd(ctx: click.Context, query: str, limit: int) -> None:
    index_path = ctx.obj["index_path"]
    if not index_path.exists():
        console.print("[yellow]No index found. Run 'docsift update' and 'docsift embed' first.[/yellow]")
        return
```

**Hardcoded embedder anti-pattern** (lines 249-259):
```python
from docsift.embedding.embedder import SentenceTransformerEmbedder
settings = get_settings()
try:
    embedder = SentenceTransformerEmbedder(model_name=settings.model_name)
except ImportError as e:
    raise click.ClickException(f"sentence-transformers not installed: {e}")
```

**Collection filter pattern** (lines 265-278):
```python
if collection:
    with db.connection:
        repo = CollectionRepository(db.connection)
        options.collection_ids = []
        for name in collection:
            coll = repo.get_by_name(name)
            if coll:
                options.collection_ids.append(coll.id)
```

---

### `src/docsift/cli/commands/index.py` (controller, batch)

**Analog:** `src/docsift/cli/commands/index.py` (existing file)

**Progress bar pattern** (lines 236-240):
```python
with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    console=console,
) as progress:
    task = progress.add_task(f"Embedding {coll.name}...", total=len(documents))
```

**Per-document loop anti-pattern** (lines 243-280):
```python
for doc in documents:
    chunk_repo.delete_by_document(doc.id)
    chunks = chunker.chunk(doc.content)
    chunk_texts = [c.content for c in chunks]
    if chunk_texts:
        embeddings = embedder.encode(chunk_texts, normalize_embeddings=True, show_progress_bar=False)
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk.document_id = doc.id
            chunk.sequence = i
            chunk_repo.create(chunk)
            vector_searcher.add_embedding(embedding_id=chunk.id, document_id=doc.id, chunk_id=chunk.id, embedding=embedding.tolist())
```

**Error handling pattern** (lines 277-278):
```python
except Exception as e:
    console.print(f"  [red]Error embedding {doc.filename}: {e}[/red]")
```

---

### `src/docsift/indexing/indexer.py` (service, batch)

**Analog:** `src/docsift/indexing/indexer.py` (existing file)

**Stale import anti-pattern** (lines 7-9):
```python
from docsift.core.document import Document, DocumentChunk
from docsift.database.repository import DocumentRepository
```

**Field mismatch anti-pattern** (lines 171-199):
```python
document = Document(
    id=str(uuid.uuid4()) if not existing else existing.id,
    collection_id=collection_id,
    path=str(file_path),
    content=parse_result.content,
    checksum=checksum,
    file_size=file_path.stat().st_size,
    metadata=parse_result.metadata,
)
# Document lacks mtime; DocumentChunk uses start_line/end_line instead of start_pos/end_pos
```

**Embedding manager usage pattern** (lines 184-200):
```python
chunk_texts = [c.content for c in chunks]
embedding_response = self._embedding_manager.embed(chunk_texts)
for i, (chunk, embedding) in enumerate(zip(chunks, embedding_response.embeddings)):
    doc_chunk = DocumentChunk(
        id=str(uuid.uuid4()),
        document_id=document.id,
        content=chunk.content,
        start_line=chunk.start_line,
        end_line=chunk.end_line,
        token_count=chunk.token_count,
        embedding=embedding,
    )
    document.add_chunk(doc_chunk)
```

---

### `tests/unit/inference/test_embedder.py` (test, request-response)

**Analog:** `tests/unit/inference/test_embedder.py` (existing file)

**Test class pattern** (lines 10-27):
```python
class TestModelType:
    def test_gguf_type_exists(self):
        assert ModelType.GGUF is not None
```

**Mock embedder fixture pattern** (from `tests/conftest.py`, lines 419-443):
```python
@pytest.fixture
def mock_embedder() -> MagicMock:
    mock = MagicMock()
    mock.model_id = "test-model"
    mock.embedding_dim = 384
    mock.max_tokens = 512
    mock.loaded = True
    def mock_embed(texts: list[str], normalize: bool = True) -> list[list[float]]:
        import random
        random.seed(42)
        return [[random.random() for _ in range(384)] for _ in texts]
    mock.embed.side_effect = mock_embed
    return mock
```

**CliRunner test pattern** (from `tests/unit/cli/test_search_commands.py`, lines 28-45):
```python
class TestSearchQuery:
    def test_query_basic(self):
        runner = CliRunner()
        result = runner.invoke(search_query, ["test query"])
        assert result.exit_code == 0
        assert "test query" in result.output
```

---

## Shared Patterns

### Optional Dependency Import with Clear Error
**Source:** `src/docsift/embedding/embedder.py` (lines 34-38), `src/docsift/cli/commands/pull.py` (lines 12-20)
**Apply to:** All embedder implementations, CLI commands using optional backends
```python
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    logger.error("sentence-transformers not installed. Install with: pip install sentence-transformers")
    raise
```

### Click Exception for User-Facing Errors
**Source:** `src/docsift/cli/commands/search.py` (lines 256-259), `src/docsift/cli/commands/pull.py` (lines 30-36)
**Apply to:** All CLI controller files
```python
raise click.ClickException(f"sentence-transformers not installed: {e}")
```

### Pydantic Settings with DOCSIFT_ Prefix
**Source:** `src/docsift/config/settings.py` (lines 20-25)
**Apply to:** All new settings fields
```python
model_config = SettingsConfigDict(
    env_prefix="DOCSIFT_",
    env_file=".env",
    env_file_encoding="utf-8",
    extra="ignore",
)
```

### sqlite-vec Batch Insert
**Source:** `src/docsift/search/vector.py` (lines 117-144) + RESEARCH.md pattern
**Apply to:** `VectorSearcher.add_embeddings_batch`, `embed_cmd` batch path
```python
rows = [(eid, doc_id, chunk_id, json.dumps(vec)) for ...]
self.db.executemany(
    "INSERT INTO document_embeddings VALUES (?, ?, ?, vec_f32(?))",
    rows,
)
```

### Database Transaction Context Manager
**Source:** `src/docsift/database/database.py` (lines 65-74)
**Apply to:** Any service needing explicit transactions
```python
@contextmanager
def transaction(self) -> Generator[sqlite3.Connection, None, None]:
    conn = self.connection
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
```

### Module-Level Logger
**Source:** `src/docsift/embedding/factory.py` (lines 8-9)
**Apply to:** All new Python modules
```python
from docsift.utils.logging import get_logger
logger = get_logger(__name__)
```

### Import Ordering
**Source:** `src/docsift/config/settings.py`
**Apply to:** All new files
```python
from __future__ import annotations

# stdlib
from functools import lru_cache
from pathlib import Path

# third-party
from pydantic import Field, field_validator

# first-party
from docsift.config.constants import APP_NAME
```

## No Analog Found

Files with no close match in the codebase (planner should use RESEARCH.md patterns instead):

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/docsift/embedding/embedder.py` - `OpenAIEmbedder` | service | transform | No OpenAI embedder exists yet; must be created from scratch using `openai` client |
| `src/docsift/embedding/manager.py` - protocol alignment | service | transform | `EmbeddingManager` currently expects `EmbeddingModel` ABC but factory returns `Embedder` protocol objects; needs architectural fix without direct analog |

## Metadata

**Analog search scope:** `src/docsift/config/`, `src/docsift/embedding/`, `src/docsift/database/`, `src/docsift/search/`, `src/docsift/cli/commands/`, `src/docsift/indexing/`, `tests/unit/`
**Files scanned:** 30+
**Pattern extraction date:** 2026-04-16
