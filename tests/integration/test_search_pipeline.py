"""Integration tests for the complete search pipeline."""

from unittest.mock import MagicMock

import pytest

from sif.core.models import SearchOptions, SearchResult
from sif.search.bm25 import BM25Searcher
from sif.search.hybrid import SearchPipeline
from sif.search.rrf import RRFFusion
from sif.search.vector import VectorSearcher


@pytest.fixture
def mock_db():
    """Create a mock sqlite3 connection."""
    return MagicMock()


class TestSearchPipelineIntegration:
    """Integration tests for the complete search pipeline."""

    def test_bm25_search_pipeline(self, mock_db: MagicMock) -> None:
        """Test BM25-only search via pipeline with lex: prefix."""
        pipeline = SearchPipeline(mock_db)
        pipeline.hybrid.bm25 = MagicMock(spec=BM25Searcher)
        pipeline.hybrid.bm25.search.return_value = [
            SearchResult(
                document_id="doc-1",
                path="/test.md",
                title="Test",
                collection_name="default",
                score=0.9,
            ),
        ]

        results = pipeline.search("lex: machine learning")

        assert isinstance(results, list)
        assert all(isinstance(r, SearchResult) for r in results)
        pipeline.hybrid.bm25.search.assert_called_once()

    def test_vector_search_pipeline(self, mock_db: MagicMock) -> None:
        """Test vector-only search via pipeline with vec: prefix."""
        mock_embedder = MagicMock()
        mock_embedder.embed.return_value = [0.1] * 384

        pipeline = SearchPipeline(mock_db, embedder=mock_embedder)
        pipeline.hybrid.vector = MagicMock(spec=VectorSearcher)
        pipeline.hybrid.vector.search.return_value = [
            SearchResult(
                document_id="doc-1",
                path="/test.md",
                title="Test",
                collection_name="default",
                score=0.85,
            ),
        ]

        results = pipeline.search("vec: neural networks")

        assert isinstance(results, list)
        assert all(isinstance(r, SearchResult) for r in results)
        pipeline.hybrid.vector.search.assert_called_once()

    def test_hybrid_search_pipeline(self, mock_db: MagicMock) -> None:
        """Test default hybrid search via pipeline."""
        mock_embedder = MagicMock()
        mock_embedder.embed.return_value = [0.1] * 384

        pipeline = SearchPipeline(mock_db, embedder=mock_embedder)
        pipeline.hybrid.bm25 = MagicMock(spec=BM25Searcher)
        pipeline.hybrid.bm25.search.return_value = [
            SearchResult(
                document_id="doc-1",
                path="/a.md",
                title="A",
                collection_name="default",
                score=0.95,
            ),
        ]
        pipeline.hybrid.vector = MagicMock(spec=VectorSearcher)
        pipeline.hybrid.vector.search.return_value = [
            SearchResult(
                document_id="doc-1",
                path="/a.md",
                title="A",
                collection_name="default",
                score=0.92,
            ),
        ]

        results = pipeline.search("deep learning")

        assert isinstance(results, list)
        assert all(isinstance(r, SearchResult) for r in results)

    def test_search_with_query_expansion(self, mock_db: MagicMock) -> None:
        """Test search with query expansion via pipeline."""
        mock_expander = MagicMock()
        mock_expander.expand.return_value = ["python tutorial", "python tutorial guide"]

        pipeline = SearchPipeline(mock_db, query_expander=mock_expander)
        pipeline.hybrid.bm25 = MagicMock(spec=BM25Searcher)
        pipeline.hybrid.bm25.search.return_value = []

        results = pipeline.search("expand: python tutorial")

        assert isinstance(results, list)
        assert mock_expander.expand.called

    def test_search_with_reranking(self, mock_db: MagicMock) -> None:
        """Test search with reranking via pipeline."""
        mock_reranker = MagicMock()
        mock_reranker.rerank.return_value = [
            SearchResult(
                document_id="doc-1",
                path="/a.md",
                title="A",
                collection_name="default",
                score=0.99,
                rank=1,
            ),
        ]

        pipeline = SearchPipeline(mock_db, reranker=mock_reranker)
        pipeline.hybrid.bm25 = MagicMock(spec=BM25Searcher)
        pipeline.hybrid.bm25.search.return_value = [
            SearchResult(
                document_id="doc-1",
                path="/a.md",
                title="A",
                collection_name="default",
                score=0.9,
            ),
        ]

        results = pipeline.search("test query")

        assert len(results) <= 1
        assert all(isinstance(r, SearchResult) for r in results)

    def test_full_pipeline_with_all_components(self, mock_db: MagicMock) -> None:
        """Test full search pipeline with all components."""
        mock_embedder = MagicMock()
        mock_embedder.embed.return_value = [0.1] * 384

        mock_expander = MagicMock()
        mock_expander.expand.return_value = ["machine learning"]

        mock_reranker = MagicMock()
        mock_reranker.rerank.return_value = [
            SearchResult(
                document_id="doc-1",
                path="/a.md",
                title="A",
                collection_name="default",
                score=0.99,
                rank=1,
            ),
        ]

        pipeline = SearchPipeline(
            mock_db,
            embedder=mock_embedder,
            query_expander=mock_expander,
            reranker=mock_reranker,
        )
        pipeline.hybrid.bm25 = MagicMock(spec=BM25Searcher)
        pipeline.hybrid.bm25.search.return_value = [
            SearchResult(
                document_id="doc-1",
                path="/a.md",
                title="A",
                collection_name="default",
                score=0.95,
            ),
        ]
        pipeline.hybrid.vector = MagicMock(spec=VectorSearcher)
        pipeline.hybrid.vector.search.return_value = [
            SearchResult(
                document_id="doc-1",
                path="/a.md",
                title="A",
                collection_name="default",
                score=0.92,
            ),
        ]

        options = SearchOptions(limit=20, candidate_limit=10)
        results = pipeline.search("machine learning", options)

        assert isinstance(results, list)
        assert len(results) <= options.limit


class TestRRFIntegration:
    """Integration tests for RRF fusion."""

    def test_rrf_fuses_bm25_and_vector_results(self) -> None:
        """Test that RRF correctly fuses BM25 and vector results."""
        rrf = RRFFusion()

        bm25_results = [
            SearchResult(
                document_id="doc-A",
                path="/a.md",
                title="A",
                collection_name="default",
                score=0.95,
            ),
            SearchResult(
                document_id="doc-B",
                path="/b.md",
                title="B",
                collection_name="default",
                score=0.87,
            ),
        ]
        vector_results = [
            SearchResult(
                document_id="doc-A",
                path="/a.md",
                title="A",
                collection_name="default",
                score=0.92,
            ),
            SearchResult(
                document_id="doc-C",
                path="/c.md",
                title="C",
                collection_name="default",
                score=0.88,
            ),
        ]

        fused = rrf.fuse([bm25_results, vector_results])

        assert isinstance(fused, list)
        bm25_ids = {r.document_id for r in bm25_results}
        vector_ids = {r.document_id for r in vector_results}
        fused_ids = {r.document_id for r in fused}

        assert fused_ids.issubset(bm25_ids | vector_ids)


class TestSearchOptionsIntegration:
    """Integration tests for search options."""

    def test_search_options_propagation(self) -> None:
        """Test that search options propagate correctly."""
        options = SearchOptions(
            limit=5,
            offset=10,
            min_score=0.5,
            explain=True,
            candidate_limit=20,
            intent="code",
        )

        assert options.limit == 5
        assert options.offset == 10
        assert options.min_score == 0.5
        assert options.explain is True
        assert options.candidate_limit == 20
        assert options.intent == "code"
