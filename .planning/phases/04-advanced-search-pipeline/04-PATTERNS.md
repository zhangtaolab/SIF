# Phase 04: Advanced Search Pipeline - Pattern Map

**Mapped:** 2026-04-17
**Files analyzed:** 16
**Analogs found:** 14 / 16

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/docsift/search/rerank.py` | service | transform | `src/docsift/embedding/embedder.py` | role-match |
| `src/docsift/search/expansion.py` | service | transform | `src/docsift/search/expansion.py` (existing) | exact |
| `src/docsift/search/snippets.py` | utility | transform | `src/docsift/search/bm25.py` | role-match |
| `src/docsift/search/benchmark.py` | utility | batch | `src/docsift/search/rrf.py` | role-match |
| `src/docsift/search/hybrid.py` | service | CRUD | `src/docsift/search/hybrid.py` (existing) | exact |
| `src/docsift/search/rrf.py` | service | transform | `src/docsift/search/rrf.py` (existing) | exact |
| `src/docsift/core/models.py` | model | config | `src/docsift/core/models.py` (existing) | exact |
| `src/docsift/config/settings.py` | config | config | `src/docsift/config/settings.py` (existing) | exact |
| `src/docsift/cli/commands/search.py` | controller | request-response | `src/docsift/cli/commands/search.py` (existing) | exact |
| `src/docsift/cli/commands/bench.py` | controller | request-response | `src/docsift/cli/commands/search.py` | role-match |
| `src/docsift/cli/main.py` | config | config | `src/docsift/cli/main.py` (existing) | exact |
| `tests/unit/inference/test_reranker.py` | test | batch | `tests/unit/inference/test_reranker.py` (existing) | exact |
| `tests/unit/inference/test_query_expander.py` | test | batch | `tests/unit/inference/test_query_expander.py` (existing) | exact |
| `tests/unit/search/test_snippets.py` | test | batch | `tests/unit/search/test_bm25.py` | role-match |
| `tests/unit/search/test_benchmark.py` | test | batch | `tests/unit/search/test_rrf.py` | role-match |
| `tests/unit/cli/test_bench.py` | test | request-response | `tests/unit/cli/test_search.py` | role-match |

## Pattern Assignments

### `src/docsift/search/rerank.py` (service, transform)

**Analog:** `src/docsift/embedding/embedder.py` (SentenceTransformerEmbedder / LlamaCppEmbedder)

**Imports pattern** (lines 1-15):
```python
"""Embedding model implementation."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import List, Optional, Union

import numpy as np

from docsift.core.models import Embedder
from docsift.models.download import ModelDownloader
from docsift.utils.logging import get_logger

logger = get_logger(__name__)
```

**Optional heavy ML import pattern** (lines 34-38):
```python
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    logger.error("sentence-transformers not installed. Install with: pip install sentence-transformers")
    raise
```

**Core pattern - lazy model loading** (lines 74-95):
```python
def load_model(self) -> None:
    """Load the embedding model."""
    if self._model is not None:
        return
    logger.info(f"Loading embedding model: {self._config.model_name}")
    self._model = self._factory.create_model(...)
    logger.info("Embedding model loaded successfully")
```

**Error handling pattern** (from `src/docsift/cli/commands/search.py` lines 409-416):
```python
try:
    manager = EmbeddingManager.from_settings(settings)
    manager.load_model()
    embedding_dim = len(manager.embed_single("probe"))
except ImportError as e:
    raise click.ClickException(f"Embedding backend not installed: {e}")
except Exception as e:
    raise click.ClickException(f"Failed to load embedding model: {e}")
```

**Note:** The current `Reranker` in `rerank.py` imports from `docsift.models.search` (Pydantic) but must be unified to use `docsift.core.models` (dataclass) `SearchResult` per RESEARCH.md Pitfall 1.

---

### `src/docsift/search/expansion.py` (service, transform)

**Analog:** `src/docsift/search/expansion.py` (existing placeholder)

**Imports pattern** (lines 1-5):
```python
"""Query expansion for improving search recall."""

from docsift.utils.logging import get_logger

logger = get_logger(__name__)
```

**Core pattern - embedding-based expansion** (lines 8-82):
```python
class QueryExpansion:
    """Query expansion to improve search recall."""

    def __init__(
        self,
        embedding_manager: "EmbeddingManager | None" = None,
        expansion_factor: int = 3,
    ) -> None:
        self._embedding_manager = embedding_manager
        self._expansion_factor = expansion_factor

    def expand(self, query: str) -> str:
        """Expand a query with related terms."""
        expansion_terms = self._get_expansion_terms(query)
        if expansion_terms:
            expanded = f"{query} {' '.join(expansion_terms)}"
            logger.debug(f"Expanded query: '{query}' -> '{expanded}'")
            return expanded
        return query

    def _get_expansion_terms(self, query: str) -> list[str]:
        """Get expansion terms for a query."""
        return []

    def expand_batch(self, queries: list[str]) -> list[str]:
        """Expand multiple queries."""
        return [self.expand(q) for q in queries]
```

**Protocol to implement** (from `src/docsift/core/models.py` lines 259-264):
```python
class QueryExpander(Protocol):
    """Protocol for query expansion."""

    def expand(self, query: str) -> List[str]:
        """Expand a query into multiple variants."""
        ...
```

**Note:** The protocol returns `List[str]` (multiple variants), but the current `QueryExpansion.expand()` returns a single `str`. The real implementation should return `List[str]` to match the protocol, with the original query as the first element.

---

### `src/docsift/search/snippets.py` (utility, transform)

**Analog:** `src/docsift/search/bm25.py` (highlight/snippet extraction logic)

**Imports pattern** (lines 1-8):
```python
"""BM25 full-text search implementation."""

from __future__ import annotations

import sqlite3
from typing import List, Optional, Tuple

from docsift.core.models import SearchOptions, SearchResult
```

**Core snippet extraction pattern** (lines 151-211):
```python
def _get_highlights(
    self,
    document_id: str,
    query: str,
    max_highlights: int = 3
) -> List[str]:
    """Get highlighted snippets for a document."""
    # Get chunks for the document
    cursor = self.db.execute(
        """
        SELECT content FROM document_chunks
        WHERE document_id = ?
        ORDER BY sequence
        """,
        (document_id,)
    )
    chunks = [row[0] for row in cursor.fetchall()]
    if not chunks:
        content = self._get_document_content(document_id)
        if content:
            chunks = [content[:1000]]

    # Find chunks containing query terms
    query_terms = [t.lower() for t in query.split()]
    highlights = []

    for chunk in chunks:
        chunk_lower = chunk.lower()
        if any(term in chunk_lower for term in query_terms):
            snippet = self._extract_snippet(chunk, query_terms)
            if snippet:
                highlights.append(snippet)
                if len(highlights) >= max_highlights:
                    break

    return highlights

def _extract_snippet(self, text: str, query_terms: List[str], context: int = 50) -> str:
    """Extract a snippet around query matches."""
    text_lower = text.lower()
    for term in query_terms:
        pos = text_lower.find(term)
        if pos >= 0:
            start = max(0, pos - context)
            end = min(len(text), pos + len(term) + context)
            snippet = text[start:end]
            if start > 0:
                snippet = "..." + snippet
            if end < len(text):
                snippet = snippet + "..."
            return snippet.strip()
    return text[:200].strip() + "..." if len(text) > 200 else text.strip()
```

---

### `src/docsift/search/benchmark.py` (utility, batch)

**Analog:** `src/docsift/search/rrf.py` (pure computation over lists)

**Imports pattern** (lines 1-7):
```python
"""Reciprocal Rank Fusion (RRF) implementation."""

from __future__ import annotations

from typing import Dict, List, Tuple

from docsift.core.models import SearchResult
```

**Core computation pattern** (from RESEARCH.md Code Examples):
```python
from typing import List, Dict, Sequence

def precision_at_k(relevance: Sequence[int], k: int) -> float:
    """Precision@K: relevant items in top-K / K."""
    if k == 0:
        return 0.0
    return sum(relevance[:k]) / k

def recall_at_k(relevance: Sequence[int], total_relevant: int, k: int) -> float:
    """Recall@K: relevant items retrieved / total relevant."""
    if total_relevant == 0:
        return 0.0
    return sum(relevance[:k]) / total_relevant

def reciprocal_rank(relevance: Sequence[int]) -> float:
    """Reciprocal rank: 1 / rank of first relevant item."""
    for i, rel in enumerate(relevance, start=1):
        if rel:
            return 1.0 / i
    return 0.0

def mean_reciprocal_rank(all_relevance: List[Sequence[int]]) -> float:
    """Mean Reciprocal Rank across queries."""
    rr_scores = [reciprocal_rank(r) for r in all_relevance]
    return sum(rr_scores) / len(rr_scores) if rr_scores else 0.0
```

---

### `src/docsift/search/hybrid.py` (service, CRUD)

**Analog:** `src/docsift/search/hybrid.py` (existing)

**Core SearchPipeline pattern** (lines 143-229):
```python
class SearchPipeline:
    """Complete search pipeline with expansion, search, and reranking."""

    def __init__(
        self,
        db: sqlite3.Connection,
        embedder: Optional[Embedder] = None,
        query_expander=None,
        reranker=None,
        embedding_dim: int = 768,
    ) -> None:
        self.db = db
        self.hybrid = HybridSearcher(db, embedder, embedding_dim)
        self.query_expander = query_expander
        self.reranker = reranker

    def search(
        self,
        query: str,
        options: Optional[SearchOptions] = None,
    ) -> List[SearchResult]:
        """Execute full search pipeline."""
        if options is None:
            options = SearchOptions()

        # Expand query if expander is available
        queries = [query]
        if self.query_expander is not None:
            try:
                expanded = self.query_expander.expand(query)
                queries.extend(expanded)
            except Exception as e:
                print(f"Warning: Query expansion failed: {e}")

        # Search with each query
        all_results = []
        for q in queries:
            results = self.hybrid.search(q, options)
            if results:
                all_results.append(results)

        # If only one query or no expansion, return results
        if len(all_results) <= 1:
            results = all_results[0] if all_results else []
        else:
            # Fuse results from multiple queries
            results = self.hybrid.rrf.fuse(all_results, options.limit)

        # Apply final reranking
        if self.reranker is not None and len(results) > 0:
            try:
                documents = []
                for result in results:
                    content = result.content or self._get_document_content(result.document_id)
                    documents.append(content or "")

                reranked = self.reranker.rerank(query, documents)

                reordered = []
                for idx, score in reranked:
                    result = results[idx]
                    result.score = score
                    reordered.append(result)

                for rank, result in enumerate(reordered, 1):
                    result.rank = rank

                return reordered
            except Exception as e:
                print(f"Warning: Final reranking failed: {e}")

        return results
```

**Note:** The current `search_with_reranking()` silently catches exceptions (line 119-120). Per RESEARCH.md Anti-Patterns, optional components should fail fast with `click.ClickException` at the CLI layer, not silently degrade.

---

### `src/docsift/search/rrf.py` (service, transform)

**Analog:** `src/docsift/search/rrf.py` (existing)

**Core RRF fusion pattern** (lines 22-77):
```python
def fuse(
    self,
    results_lists: List[List[SearchResult]],
    limit: int = 10,
) -> List[SearchResult]:
    """Fuse multiple ranked lists using RRF."""
    scores: Dict[str, Tuple[float, SearchResult]] = {}

    for results in results_lists:
        for rank, result in enumerate(results, 1):
            doc_id = result.document_id
            rrf_score = 1.0 / (self.k + rank)

            if doc_id in scores:
                existing_score, existing_result = scores[doc_id]
                scores[doc_id] = (existing_score + rrf_score, existing_result)
            else:
                scores[doc_id] = (rrf_score, result)

    sorted_scores = sorted(
        scores.items(),
        key=lambda x: x[1][0],
        reverse=True
    )

    fused_results = []
    for rank, (doc_id, (score, result)) in enumerate(sorted_scores[:limit], 1):
        fused_result = SearchResult(
            document_id=result.document_id,
            title=result.title,
            path=result.path,
            collection_name=result.collection_name,
            score=score,
            content=result.content,
            highlights=result.highlights,
            rank=rank,
        )
        fused_results.append(fused_result)

    return fused_results
```

**Note:** RRF currently loses original BM25/vector scores. For `--explain`, `RRFFusion.fuse()` needs to preserve intermediate scores in a `scores` dict on each `SearchResult`.

---

### `src/docsift/core/models.py` (model, config)

**Analog:** `src/docsift/core/models.py` (existing)

**SearchResult dataclass pattern** (lines 177-199):
```python
@dataclass
class SearchResult:
    """A search result."""
    document_id: str
    title: str
    path: str
    collection_name: str
    score: float
    content: Optional[str] = None
    highlights: List[str] = field(default_factory=list)
    rank: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "document_id": self.document_id,
            "title": self.title,
            "path": self.path,
            "collection_name": self.collection_name,
            "score": self.score,
            "content": self.content,
            "highlights": self.highlights,
            "rank": self.rank,
        }
```

**SearchOptions dataclass pattern** (lines 202-211):
```python
@dataclass
class SearchOptions:
    """Options for search."""
    limit: int = 10
    offset: int = 0
    collection_ids: Optional[List[str]] = None
    min_score: float = 0.0
    include_content: bool = False
    include_highlights: bool = True
    max_highlights: int = 3
```

**Protocol definitions** (lines 234-264):
```python
class Embedder(Protocol):
    """Protocol for embedding models."""
    def embed(self, text: str) -> List[float]: ...
    def embed_batch(self, texts: List[str]) -> List[List[float]]: ...
    @property
    def dimension(self) -> int: ...

class Reranker(Protocol):
    """Protocol for reranking models."""
    def rerank(self, query: str, documents: List[str]) -> List[tuple[int, float]]: ...

class QueryExpander(Protocol):
    """Protocol for query expansion."""
    def expand(self, query: str) -> List[str]: ...
```

**New fields to add** (per RESEARCH.md Pattern 2):
```python
@dataclass
class SearchResult:
    document_id: str
    title: str
    path: str
    collection_name: str
    score: float
    content: Optional[str] = None
    highlights: List[str] = field(default_factory=list)
    rank: int = 0
    scores: Dict[str, Optional[float]] = field(default_factory=dict)  # NEW
    snippet: Optional[str] = None  # NEW for SRCH-07
```

**New SearchOptions fields**:
```python
@dataclass
class SearchOptions:
    limit: int = 10
    offset: int = 0
    collection_ids: Optional[List[str]] = None
    min_score: float = 0.0
    include_content: bool = False
    include_highlights: bool = True
    max_highlights: int = 3
    explain: bool = False  # NEW for SRCH-04
    candidate_limit: int = 20  # NEW for SRCH-05
    intent: Optional[str] = None  # NEW for SRCH-06
```

---

### `src/docsift/config/settings.py` (config, config)

**Analog:** `src/docsift/config/settings.py` (existing)

**Pydantic Settings pattern** (lines 12-176):
```python
class Settings(BaseSettings):
    """Application settings using Pydantic Settings."""

    model_config = SettingsConfigDict(
        env_prefix="DOCSIFT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Model settings
    model_path: Path | None = Field(default=None, description="Path to embedding model file")
    model_name: str = Field(default="all-MiniLM-L6-v2", description="Embedding model name")
    model_type: str = Field(default="sentence_transformers")

    @field_validator("db_path", "cache_dir", mode="before")
    @classmethod
    def expand_path(cls, v: str | Path | None) -> Path | None:
        if v is None:
            return None
        path = Path(v).expanduser()
        return path
```

**Settings override pattern** (from `src/docsift/cli/commands/search.py` lines 405-407):
```python
settings = get_settings()
if model_type:
    settings = settings.model_copy(update={"model_type": model_type})
```

**New reranker settings to add**:
```python
# Reranker settings (NEW for SRCH-01)
reranker_model_name: str = Field(
    default="cross-encoder/ms-marco-MiniLM-L-6-v2",
    description="Reranker model name",
)
reranker_model_path: Path | None = Field(
    default=None,
    description="Path to local reranker model file",
)
reranker_model_type: str = Field(
    default="sentence_transformers",
    description="Reranker model type (sentence_transformers, gguf)",
)
reranker_batch_size: int = Field(
    default=32,
    ge=1,
    description="Batch size for reranker inference",
)
```

---

### `src/docsift/cli/commands/search.py` (controller, request-response)

**Analog:** `src/docsift/cli/commands/search.py` (existing)

**CLI command pattern** (lines 330-491):
```python
@search_group.command("query")
@click.argument("query")
@click.option("-n", "--limit", default=10, help="Number of results")
@click.option("-c", "--collection", multiple=True, help="Collection to search")
@click.option("--all", "search_all", is_flag=True, help="Search all collections")
@click.option("--min-score", default=0.0, help="Minimum score threshold")
@click.option("--full", is_flag=True, help="Include full content")
@click.option("--line-numbers", is_flag=True, help="Show line numbers in content")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option(
    "--model-type",
    type=click.Choice(["sentence_transformers", "gguf", "openai", "modelscope"]),
    help="Embedding model type override",
)
@click.pass_context
def query_cmd(
    ctx: click.Context,
    query: str,
    limit: int,
    collection: tuple,
    search_all: bool,
    min_score: float,
    full: bool,
    line_numbers: bool,
    output_json: bool,
    model_type: str | None = None,
) -> None:
    """Search documents using hybrid approach (BM25 + Vector + RRF)."""
    index_path = ctx.obj["index_path"]

    if not index_path.exists():
        console.print("[yellow]No index found. Run 'docsift update' first.[/yellow]")
        return

    db = Database(index_path)
    db.init_schema()

    # Build options
    options = SearchOptions(
        limit=limit,
        min_score=min_score,
        include_content=full,
        include_highlights=True,
    )

    # Get collection IDs if specified
    if collection:
        with db.connection:
            repo = CollectionRepository(db.connection)
            options.collection_ids = []
            for name in collection:
                coll = repo.get_by_name(name)
                if coll:
                    options.collection_ids.append(coll.id)
    elif not search_all:
        with db.connection:
            repo = CollectionRepository(db.connection)
            enabled = repo.list_enabled()
            options.collection_ids = [c.id for c in enabled]

    # Load embedder for hybrid search
    from docsift.config.settings import get_settings
    from docsift.embedding.manager import EmbeddingManager

    settings = get_settings()
    if model_type:
        settings = settings.model_copy(update={"model_type": model_type})

    try:
        manager = EmbeddingManager.from_settings(settings)
        manager.load_model()
        embedding_dim = len(manager.embed_single("probe"))
    except ImportError as e:
        raise click.ClickException(f"Embedding backend not installed: {e}")
    except Exception as e:
        raise click.ClickException(f"Failed to load embedding model: {e}")

    # Search using hybrid approach
    with db.connection:
        searcher = HybridSearcher(
            db.connection, embedder=manager._model, embedding_dim=embedding_dim
        )
        results = searcher.search(query, options)

    # Output results
    if output_json:
        console.print(format_results_json(results))
    else:
        # Rich table output
        table = Table(title=f'Hybrid Search Results: "{query}"')
        table.add_column("#", style="cyan", justify="right")
        table.add_column("Score", style="green", justify="right")
        table.add_column("Title", style="yellow")
        table.add_column("Collection", style="blue")
        for r in results:
            row = [
                str(r.rank),
                f"{r.score:.4f}",
                r.title[:50] + "..." if len(r.title) > 50 else r.title,
                r.collection_name,
            ]
            table.add_row(*row)
        console.print(table)
```

**New CLI options to add to `query_cmd`**:
```python
@click.option("--explain", is_flag=True, help="Show score breakdowns")
@click.option("-C", "--candidate-limit", default=20, help="Reranker candidate pool size")
@click.option("--intent", help="Search intent for query expansion")
```

---

### `src/docsift/cli/commands/bench.py` (controller, request-response)

**Analog:** `src/docsift/cli/commands/search.py`

**CLI command registration pattern** (from `src/docsift/cli/main.py` lines 67-85):
```python
# Import and register subcommands
from docsift.cli.commands.collection import collection_group
from docsift.cli.commands.search import search_group

cli.add_command(collection_group)
cli.add_command(search_group)
```

**Benchmark command pattern** (new file, following search.py structure):
```python
"""Benchmark commands."""

from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from docsift.search.benchmark import SearchEvaluator
from docsift.utils.logging import get_logger

logger = get_logger(__name__)
console = Console()


@click.command("bench")
@click.argument("fixture", type=click.Path(exists=True))
@click.option("-n", "--limit", default=10, help="Number of results per query")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def bench_cmd(
    ctx: click.Context,
    fixture: str,
    limit: int,
    output_json: bool,
) -> None:
    """Run benchmark evaluation against a fixture file."""
    index_path = ctx.obj["index_path"]

    if not index_path.exists():
        console.print("[yellow]No index found. Run 'docsift update' first.[/yellow]")
        return

    # Load fixture
    with open(fixture) as f:
        fixture_data = json.load(f)

    evaluator = SearchEvaluator(fixture_data)
    # ... run evaluation and output results
```

---

### `tests/unit/search/test_reranker.py` (test, batch)

**Analog:** `tests/unit/inference/test_reranker.py` (existing)

**Test pattern** (lines 1-189):
```python
"""Tests for result reranker."""

from unittest.mock import MagicMock, patch

import pytest

from docsift.models.search import SearchResult
from docsift.search.rerank import Reranker


class TestRerankerInit:
    """Tests for Reranker initialization."""

    def test_default_init(self):
        reranker = Reranker()
        assert reranker._model_name == "cross-encoder/ms-marco-MiniLM-L-6-v2"
        assert reranker._batch_size == 32
        assert reranker._model_path is None


class TestRerankerRerank:
    """Tests for reranking results."""

    def test_rerank_empty_results(self):
        reranker = Reranker()
        results = reranker.rerank("query", [], top_k=10)
        assert results == []

    def test_rerank_limits_top_k(self, sample_search_results: list[SearchResult]):
        reranker = Reranker()
        results = reranker.rerank("query", sample_search_results, top_k=3)
        assert len(results) <= 3

    def test_rerank_sorts_by_score(self, sample_search_results: list[SearchResult]):
        reranker = Reranker()
        results = reranker.rerank("query", sample_search_results, top_k=10)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)
```

**Note:** Tests currently use `docsift.models.search.SearchResult` (Pydantic). Must be updated to use `docsift.core.models.SearchResult` (dataclass) per RESEARCH.md Pitfall 1.

---

### `tests/unit/search/test_expansion.py` (test, batch)

**Analog:** `tests/unit/inference/test_query_expander.py` (existing)

**Test pattern** (lines 1-199):
```python
"""Tests for query expansion."""

from unittest.mock import MagicMock

import pytest

from docsift.search.expansion import QueryExpansion


class TestQueryExpansionInit:
    """Tests for QueryExpansion initialization."""

    def test_default_init(self):
        expander = QueryExpansion()
        assert expander._embedding_manager is None
        assert expander._expansion_factor == 3

    def test_init_with_embedding_manager(self, mock_embedding_manager: MagicMock):
        expander = QueryExpansion(embedding_manager=mock_embedding_manager)
        assert expander._embedding_manager is mock_embedding_manager


class TestQueryExpansionExpand:
    """Tests for query expansion."""

    def test_expand_returns_original_when_no_terms(self):
        expander = QueryExpansion()
        result = expander.expand("test query")
        assert result == "test query"

    def test_expand_appends_expansion_terms(self):
        expander = QueryExpansion()
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(expander, '_get_expansion_terms', lambda q: ["term1", "term2"])
            result = expander.expand("test query")
            assert "test query" in result
            assert "term1" in result
```

---

### `tests/unit/search/test_snippets.py` (test, batch)

**Analog:** `tests/unit/search/test_bm25.py`

**Test pattern** (from `tests/unit/search/test_bm25.py` style, inferred):
```python
"""Tests for smart snippet extraction."""

import pytest

from docsift.search.snippets import SmartSnippetExtractor


class TestSmartSnippetExtractor:
    """Tests for smart snippet extraction."""

    def test_extract_snippet_with_query_terms(self):
        extractor = SmartSnippetExtractor()
        text = "This is a long document about machine learning and neural networks."
        query_terms = ["machine", "learning"]
        snippet = extractor.extract(text, query_terms)
        assert "machine learning" in snippet.lower()

    def test_extract_snippet_fallback(self):
        extractor = SmartSnippetExtractor()
        text = "Some unrelated text without matching terms."
        query_terms = ["quantum"]
        snippet = extractor.extract(text, query_terms)
        assert snippet  # Should return beginning of text
```

---

### `tests/unit/search/test_benchmark.py` (test, batch)

**Analog:** `tests/unit/search/test_rrf.py`

**Test pattern** (from `tests/unit/search/test_rrf.py` lines 112-160):
```python
class TestRRFBasicFusion:
    """Test basic RRF fusion functionality."""

    def test_fuse_single_list(self, rrf_fusion: RRFFusion, sample_search_results: list[SearchResult]) -> None:
        result_lists = [sample_search_results]
        fused = rrf_fusion.fuse(result_lists)
        assert len(fused) == len(sample_search_results)
        assert fused[0].score > 0
```

---

### `tests/unit/cli/test_bench.py` (test, request-response)

**Analog:** `tests/unit/cli/test_search.py`

**Test pattern** (lines 1-50):
```python
"""Tests for search CLI commands."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from docsift.cli.commands.search import query_cmd, search_cmd, vsearch_cmd
from docsift.core.models import Collection


class TestSearchFiltering:
    """Tests for search collection filtering."""

    def test_search_respects_include_by_default(self):
        runner = CliRunner()
        enabled_coll = Collection(
            id="coll1", name="enabled", path="/notes", include_by_default=True
        )
        mock_repo = MagicMock()
        mock_repo.list_enabled.return_value = [enabled_coll]
        mock_searcher = MagicMock()
        mock_searcher.search.return_value = []
        mock_db = MagicMock()

        with (
            patch("docsift.cli.commands.search.Database", return_value=mock_db),
            patch("docsift.cli.commands.search.CollectionRepository", return_value=mock_repo),
            patch("docsift.cli.commands.search.BM25Searcher", return_value=mock_searcher),
        ):
            result = runner.invoke(
                search_cmd,
                ["foo"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )
        assert result.exit_code == 0
```

## Shared Patterns

### Authentication / Authorization
Not applicable for this phase (local-first tool, no auth layer).

### Error Handling
**Source:** `src/docsift/cli/commands/search.py` (lines 409-416)
**Apply to:** All CLI commands that load optional ML backends
```python
try:
    manager = EmbeddingManager.from_settings(settings)
    manager.load_model()
    embedding_dim = len(manager.embed_single("probe"))
except ImportError as e:
    raise click.ClickException(f"Embedding backend not installed: {e}")
except Exception as e:
    raise click.ClickException(f"Failed to load embedding model: {e}")
```

**Source:** `src/docsift/database/database.py` (lines 67-76)
**Apply to:** All database operations
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

### Logging
**Source:** `src/docsift/utils/logging.py` (lines 47-56)
**Apply to:** All new modules
```python
from docsift.utils.logging import get_logger

logger = get_logger(__name__)
```

### Optional Heavy ML Import
**Source:** `src/docsift/embedding/embedder.py` (lines 34-38) and RESEARCH.md Pattern 1
**Apply to:** `rerank.py` (sentence-transformers CrossEncoder, llama-cpp-python)
```python
try:
    from sentence_transformers import CrossEncoder
except ImportError:
    logger.error("sentence-transformers not installed. Install with: pip install -e '.[embed]'")
    raise
```

### Settings Override Pattern
**Source:** `src/docsift/cli/commands/search.py` (lines 405-407) and RESEARCH.md Pattern 4
**Apply to:** All CLI options that override Settings fields
```python
settings = get_settings()
if model_type:
    settings = settings.model_copy(update={"model_type": model_type})
```

### Query Prefix Router
**Source:** RESEARCH.md Pattern 3
**Apply to:** `query_cmd` in `src/docsift/cli/commands/search.py`
```python
PREFIX_MAP = {
    "lex:": SearchType.BM25,
    "vec:": SearchType.VECTOR,
    "hyde:": SearchType.HYDE,
    "expand:": SearchType.EXPAND,
}

def parse_query_prefix(query: str) -> tuple[str, SearchType]:
    for prefix, search_type in PREFIX_MAP.items():
        if query.startswith(prefix):
            return query[len(prefix):].strip(), search_type
    return query, SearchType.HYBRID
```

### Score Tracking Across Pipeline Stages
**Source:** RESEARCH.md Pattern 2
**Apply to:** `SearchResult` in `core/models.py`, `RRFFusion.fuse()`, `HybridSearcher.search()`, `Reranker.rerank()`
```python
@dataclass
class SearchResult:
    document_id: str
    title: str
    path: str
    collection_name: str
    score: float
    content: Optional[str] = None
    highlights: List[str] = field(default_factory=list)
    rank: int = 0
    scores: Dict[str, Optional[float]] = field(default_factory=dict)
    snippet: Optional[str] = None
```

### Result Formatter Pattern
**Source:** `src/docsift/cli/commands/search.py` (lines 22-72)
**Apply to:** All output formatters in `search.py` and `bench.py`
```python
def format_results_json(results: list) -> str:
    return json.dumps(
        [r.to_dict() if hasattr(r, "to_dict") else r for r in results],
        indent=2,
        ensure_ascii=False,
    )
```

### CLI Command Registration
**Source:** `src/docsift/cli/main.py` (lines 67-85)
**Apply to:** New `bench.py` command
```python
# In main.py:
from docsift.cli.commands.bench import bench_cmd
cli.add_command(bench_cmd)
```

### Rich Table Output
**Source:** `src/docsift/cli/commands/search.py` (lines 189-215)
**Apply to:** All CLI commands with table output
```python
table = Table(title=f'Search Results: "{query}"')
table.add_column("#", style="cyan", justify="right")
table.add_column("Score", style="green", justify="right")
table.add_column("Title", style="yellow")
table.add_column("Collection", style="blue")
for r in results:
    row = [
        str(r.rank),
        f"{r.score:.4f}",
        r.title[:50] + "..." if len(r.title) > 50 else r.title,
        r.collection_name,
    ]
    table.add_row(*row)
console.print(table)
```

## No Analog Found

Files with no close match in the codebase (planner should use RESEARCH.md patterns instead):

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/docsift/search/snippets.py` | utility | transform | No existing snippet extraction utility; closest is BM25 highlight logic which is embedded in `BM25Searcher` |
| `src/docsift/search/benchmark.py` | utility | batch | No existing benchmark/evaluation module; pure Python metrics from RESEARCH.md |

## Metadata

**Analog search scope:** `src/docsift/search/`, `src/docsift/cli/commands/`, `src/docsift/core/`, `src/docsift/config/`, `src/docsift/embedding/`, `tests/unit/search/`, `tests/unit/cli/`, `tests/unit/inference/`, `tests/integration/`
**Files scanned:** 25
**Pattern extraction date:** 2026-04-17

## Key Patterns Identified

1. **All search services use `docsift.core.models` dataclasses** (`SearchResult`, `SearchOptions`) except the current `Reranker` which uses Pydantic from `docsift.models.search`. Must unify.

2. **Optional ML backends import at runtime** with clear error messages pointing to install command (`pip install -e '.[embed]'`).

3. **CLI commands raise `click.ClickException`** for user-facing errors; database uses `transaction()` context manager with automatic rollback.

4. **Settings overrides use `settings.model_copy(update={...})`** to avoid Pydantic v2 duplicate-keyword errors.

5. **Search formatters** (`format_results_json`, `format_results_csv`, etc.) accept both dataclass objects and plain dicts via `hasattr(r, "to_dict")` check.

6. **RRF fusion currently loses intermediate scores.** For `--explain`, `RRFFusion.fuse()` needs to preserve `bm25_score` and `vector_score` in a `scores` dict.

7. **Tests use `CliRunner` with extensive mocking** (`patch` for Database, Repository, Searcher, EmbeddingManager).

8. **The `QueryExpander` protocol returns `List[str]`** but the current `QueryExpansion.expand()` returns `str`. The real implementation must align with the protocol.
