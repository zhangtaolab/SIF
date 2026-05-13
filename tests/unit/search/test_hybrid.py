"""Unit tests for hybrid search and search pipeline."""

from unittest.mock import MagicMock, create_autospec

import pytest

from sif.core.models import SearchOptions, SearchResult, SearchType
from sif.search.bm25 import BM25Searcher
from sif.search.hybrid import HybridSearcher, SearchPipeline
from sif.search.vector import VectorSearcher


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_db():
    """Create a mock sqlite3 connection."""
    return MagicMock()


@pytest.fixture
def mock_embedder():
    """Create a mock embedder."""
    embedder = MagicMock()
    embedder.embed.return_value = [0.1] * 384
    embedder.dimension = 384
    return embedder


@pytest.fixture
def sample_search_options() -> SearchOptions:
    """Create sample search options."""
    return SearchOptions(limit=10)


@pytest.fixture
def bm25_results() -> list[SearchResult]:
    """Create sample BM25 search results."""
    return [
        SearchResult(
            document_id="doc-A",
            path="/path/to/doc_a.md",
            title="Document A",
            collection_name="default",
            score=0.95,
        ),
        SearchResult(
            document_id="doc-B",
            path="/path/to/doc_b.md",
            title="Document B",
            collection_name="default",
            score=0.87,
        ),
    ]


@pytest.fixture
def vector_results() -> list[SearchResult]:
    """Create sample vector search results."""
    return [
        SearchResult(
            document_id="doc-A",
            path="/path/to/doc_a.md",
            title="Document A",
            collection_name="default",
            score=0.92,
        ),
        SearchResult(
            document_id="doc-C",
            path="/path/to/doc_c.md",
            title="Document C",
            collection_name="default",
            score=0.88,
        ),
    ]


# =============================================================================
# HybridSearcher Tests
# =============================================================================


class TestHybridSearcher:
    """Test HybridSearcher basic functionality."""

    def test_hybrid_search_with_embedder(
        self,
        mock_db: MagicMock,
        mock_embedder: MagicMock,
    ) -> None:
        """Test that hybrid search uses both BM25 and vector when embedder available."""
        hybrid = HybridSearcher(mock_db, embedder=mock_embedder, embedding_dim=384)
        assert hybrid.embedder is mock_embedder
        assert hybrid.bm25 is not None
        assert hybrid.vector is not None

    def test_hybrid_search_without_embedder(
        self,
        mock_db: MagicMock,
    ) -> None:
        """Test that hybrid search falls back to BM25 without embedder."""
        hybrid = HybridSearcher(mock_db, embedder=None, embedding_dim=384)
        assert hybrid.embedder is None

    def test_hybrid_searcher_has_search_method(
        self,
        mock_db: MagicMock,
    ) -> None:
        """Test that HybridSearcher has search method."""
        hybrid = HybridSearcher(mock_db)
        assert hasattr(hybrid, "search")
        assert callable(hybrid.search)


# =============================================================================
# SearchPipeline Tests
# =============================================================================


class TestSearchPipelinePrefixRouting:
    """Test SearchPipeline query prefix routing."""

    def test_parse_query_prefix_lex(self) -> None:
        """Test lex: prefix routes to BM25."""
        pipeline = SearchPipeline(MagicMock())
        query, search_type = pipeline._parse_query_prefix("lex: python tutorial")
        assert query == "python tutorial"
        assert search_type == SearchType.BM25

    def test_parse_query_prefix_vec(self) -> None:
        """Test vec: prefix routes to vector."""
        pipeline = SearchPipeline(MagicMock())
        query, search_type = pipeline._parse_query_prefix("vec: neural networks")
        assert query == "neural networks"
        assert search_type == SearchType.VECTOR

    def test_parse_query_prefix_hyde(self) -> None:
        """Test hyde: prefix routes to HyDE."""
        pipeline = SearchPipeline(MagicMock())
        query, search_type = pipeline._parse_query_prefix("hyde: machine learning")
        assert query == "machine learning"
        assert search_type == SearchType.HYDE

    def test_parse_query_prefix_expand(self) -> None:
        """Test expand: prefix routes to expansion."""
        pipeline = SearchPipeline(MagicMock())
        query, search_type = pipeline._parse_query_prefix("expand: search tips")
        assert query == "search tips"
        assert search_type == SearchType.EXPAND

    def test_parse_query_prefix_default(self) -> None:
        """Test default query routes to hybrid."""
        pipeline = SearchPipeline(MagicMock())
        query, search_type = pipeline._parse_query_prefix("python tutorial")
        assert query == "python tutorial"
        assert search_type == SearchType.HYBRID

    def test_pipeline_prefix_lex_routes_to_bm25(
        self,
        mock_db: MagicMock,
    ) -> None:
        """Test that lex: prefix uses BM25Searcher only."""
        pipeline = SearchPipeline(mock_db)
        pipeline.hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        pipeline.hybrid.bm25.search.return_value = [
            SearchResult(
                document_id="doc-1",
                path="/test.md",
                title="Test",
                collection_name="default",
                score=0.9,
            ),
        ]

        results = pipeline.search("lex: test query")

        pipeline.hybrid.bm25.search.assert_called_once()
        assert len(results) == 1
        assert results[0].document_id == "doc-1"

    def test_pipeline_prefix_vec_raises_without_embedder(
        self,
        mock_db: MagicMock,
    ) -> None:
        """Test that vec: prefix raises when embedder is missing."""
        pipeline = SearchPipeline(mock_db)

        with pytest.raises(RuntimeError, match="Vector search requires an embedder"):
            pipeline.search("vec: test query")

    def test_pipeline_prefix_hyde_raises_without_generate(
        self,
        mock_db: MagicMock,
    ) -> None:
        """Test that hyde: prefix raises when embedder lacks generation."""
        mock_embedder = MagicMock(spec=["embed", "dimension"])
        mock_embedder.embed.return_value = [0.1] * 384
        mock_embedder.dimension = 384

        pipeline = SearchPipeline(mock_db, embedder=mock_embedder)

        with pytest.raises(
            RuntimeError, match="HyDE search requires a text-generation-capable model"
        ):
            pipeline.search("hyde: test query")


class TestSearchPipelineExpansion:
    """Test SearchPipeline query expansion."""

    def test_pipeline_with_expansion(
        self,
        mock_db: MagicMock,
        mock_embedder: MagicMock,
    ) -> None:
        """Test pipeline with query expansion fuses multiple queries."""
        mock_expander = MagicMock()
        mock_expander.expand.return_value = ["query", "query variant"]

        pipeline = SearchPipeline(
            mock_db,
            embedder=mock_embedder,
            query_expander=mock_expander,
        )
        pipeline.hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        pipeline.hybrid.bm25.search.return_value = [
            SearchResult(
                document_id="doc-1",
                path="/test.md",
                title="Test",
                collection_name="default",
                score=0.9,
            ),
        ]

        _results = pipeline.search("query", SearchOptions(limit=5))

        assert mock_expander.expand.called
        assert pipeline.hybrid.bm25.search.call_count == 2

    def test_pipeline_expansion_deduplicates(
        self,
        mock_db: MagicMock,
        mock_embedder: MagicMock,
    ) -> None:
        """Test that expansion deduplicates repeated variants."""
        mock_expander = MagicMock()
        mock_expander.expand.return_value = ["query", "query", "QUERY", "variant"]

        pipeline = SearchPipeline(
            mock_db,
            embedder=mock_embedder,
            query_expander=mock_expander,
        )
        pipeline.hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        pipeline.hybrid.bm25.search.return_value = []

        pipeline.search("query")

        # Should only search twice (original + one truly unique variant)
        assert pipeline.hybrid.bm25.search.call_count == 2


class TestSearchPipelineReranking:
    """Test SearchPipeline reranking."""

    def test_pipeline_with_reranker(
        self,
        mock_db: MagicMock,
    ) -> None:
        """Test pipeline with reranker reorders results."""
        mock_reranker = MagicMock()
        mock_reranker.rerank.return_value = [
            SearchResult(
                document_id="doc-2",
                path="/b.md",
                title="B",
                collection_name="default",
                score=0.99,
                rank=1,
            ),
            SearchResult(
                document_id="doc-1",
                path="/a.md",
                title="A",
                collection_name="default",
                score=0.95,
                rank=2,
            ),
        ]

        pipeline = SearchPipeline(mock_db, reranker=mock_reranker)
        pipeline.hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        pipeline.hybrid.bm25.search.return_value = [
            SearchResult(
                document_id="doc-1",
                path="/a.md",
                title="A",
                collection_name="default",
                score=0.9,
            ),
            SearchResult(
                document_id="doc-2",
                path="/b.md",
                title="B",
                collection_name="default",
                score=0.8,
            ),
        ]

        results = pipeline.search("test", SearchOptions(candidate_limit=10))

        mock_reranker.rerank.assert_called_once()
        assert results[0].document_id == "doc-2"
        assert results[0].rank == 1

    def test_pipeline_candidate_limit(
        self,
        mock_db: MagicMock,
    ) -> None:
        """Test that only candidate_limit results go to reranker."""
        mock_reranker = MagicMock()
        mock_reranker.rerank.return_value = []

        pipeline = SearchPipeline(mock_db, reranker=mock_reranker)
        pipeline.hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        pipeline.hybrid.bm25.search.return_value = [
            SearchResult(
                document_id=f"doc-{i}",
                path=f"/{i}.md",
                title=f"Doc {i}",
                collection_name="default",
                score=0.9 - i * 0.01,
            )
            for i in range(10)
        ]

        pipeline.search("test", SearchOptions(candidate_limit=5))

        # Reranker should only receive 5 candidates
        passed_results = mock_reranker.rerank.call_args[0][1]
        assert len(passed_results) == 5


class TestSearchPipelineExplain:
    """Test SearchPipeline explainability / score preservation."""

    def test_explain_preserves_scores(
        self,
        mock_db: MagicMock,
        mock_embedder: MagicMock,
    ) -> None:
        """Test that scores dict contains bm25_score and vector_score via RRF."""
        pipeline = SearchPipeline(mock_db, embedder=mock_embedder)
        pipeline.hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        pipeline.hybrid.bm25.search.return_value = [
            SearchResult(
                document_id="doc-1",
                path="/a.md",
                title="A",
                collection_name="default",
                score=0.95,
            ),
        ]
        pipeline.hybrid.vector = create_autospec(VectorSearcher, instance=True)
        pipeline.hybrid.vector.search.return_value = [
            SearchResult(
                document_id="doc-1",
                path="/a.md",
                title="A",
                collection_name="default",
                score=0.92,
            ),
        ]

        results = pipeline.search("test", SearchOptions(explain=True))

        assert len(results) == 1
        assert "bm25_score" in results[0].scores
        assert "vector_score" in results[0].scores
        assert "rrf_score" in results[0].scores


class TestSearchPipelineIntent:
    """Test SearchPipeline intent propagation."""

    def test_intent_prepended_to_query(
        self,
        mock_db: MagicMock,
    ) -> None:
        """Test that intent is prepended to parsed query."""
        pipeline = SearchPipeline(mock_db)
        pipeline.hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        pipeline.hybrid.bm25.search.return_value = []

        pipeline.search("test", SearchOptions(intent="code"))

        call_args = pipeline.hybrid.bm25.search.call_args
        assert call_args is not None
        passed_query = call_args[0][0]
        assert passed_query == "code: test"


class TestHybridContextAttachment:
    """Tests for context_description attachment in hybrid search results."""

    def test_hybrid_search_attaches_context_after_rrf(self, mock_db: MagicMock) -> None:
        """Test that hybrid search attaches context descriptions after RRF fusion."""
        hybrid = HybridSearcher(mock_db, embedder=None, embedding_dim=384)
        hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        hybrid.bm25.search.return_value = [
            SearchResult(
                document_id="doc-1",
                path="/a.md",
                title="A",
                collection_name="default",
                score=0.95,
                context_description="BM25 context",
            ),
        ]
        hybrid.vector = create_autospec(VectorSearcher, instance=True)
        hybrid.vector.search.return_value = [
            SearchResult(
                document_id="doc-1",
                path="/a.md",
                title="A",
                collection_name="default",
                score=0.92,
                context_description="Vector context",
            ),
        ]

        results = hybrid.search("test")

        assert len(results) == 1
        # After RRF fusion, context_description should be preserved from one of the sources
        assert results[0].context_description is not None

    def test_pipeline_search_attaches_context_after_reranking(self, mock_db: MagicMock) -> None:
        """Test that SearchPipeline preserves context_description after reranking."""
        mock_reranker = MagicMock()
        mock_reranker.rerank.return_value = [
            SearchResult(
                document_id="doc-1",
                path="/a.md",
                title="A",
                collection_name="default",
                score=0.99,
                rank=1,
                context_description="Reranked context",
            ),
        ]

        pipeline = SearchPipeline(mock_db, reranker=mock_reranker)
        pipeline.hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        pipeline.hybrid.bm25.search.return_value = [
            SearchResult(
                document_id="doc-1",
                path="/a.md",
                title="A",
                collection_name="default",
                score=0.9,
                context_description="Original context",
            ),
        ]

        results = pipeline.search("test", SearchOptions(candidate_limit=10))

        mock_reranker.rerank.assert_called_once()
        assert len(results) == 1
        assert results[0].context_description == "Reranked context"

    def test_hybrid_search_attaches_context_with_normalized_path(self, mock_db: MagicMock) -> None:
        """Test that hybrid context matches even with /private/tmp vs /tmp mismatch."""
        hybrid = HybridSearcher(mock_db, embedder=None, embedding_dim=384)
        hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        hybrid.bm25.search.return_value = [
            SearchResult(
                document_id="doc-1",
                path="/private/tmp/doc.md",
                title="A",
                collection_name="default",
                score=0.95,
            ),
        ]
        hybrid.vector = create_autospec(VectorSearcher, instance=True)
        hybrid.vector.search.return_value = []

        # Mock the context query in HybridSearcher's own _attach_contexts
        context_cursor = MagicMock()
        context_cursor.fetchall.return_value = [
            ("/tmp/doc.md", "Project notes"),
        ]
        mock_db.execute.return_value = context_cursor

        results = hybrid.search("test")

        assert len(results) == 1
        assert results[0].context_description == "Project notes"
