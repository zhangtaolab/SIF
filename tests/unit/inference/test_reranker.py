"""Tests for result reranker."""

import sys
from unittest.mock import MagicMock, patch

import pytest


# Mock optional dependencies before importing modules that use them
if "llama_cpp" not in sys.modules:
    sys.modules["llama_cpp"] = MagicMock()
if "sentence_transformers" not in sys.modules:
    sys.modules["sentence_transformers"] = MagicMock()

from docsift.core.models import SearchResult
from docsift.search.rerank import (
    CrossEncoderReranker,
    LlamaCppReranker,
    Reranker,
    create_reranker,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_search_results() -> list[SearchResult]:
    """Return sample search results for testing."""
    return [
        SearchResult(
            document_id=f"doc-{i}",
            path=f"/path/to/result_{i}.md",
            title=f"Result {i}",
            collection_name="test",
            score=max(0.0, 0.95 - (i * 0.05)),
            content=f"Preview of result {i}...",
            highlights=["matched term"],
        )
        for i in range(5)
    ]


# =============================================================================
# LlamaCppReranker Tests
# =============================================================================


class TestLlamaCppRerankerInit:
    """Tests for LlamaCppReranker initialization."""

    def test_default_init(self):
        """Test default reranker initialization."""
        reranker = LlamaCppReranker()

        assert reranker._model_name == ""
        assert reranker._batch_size == 32
        assert reranker._model_path is None
        assert reranker._model is None
        assert reranker._n_ctx == 512

    def test_custom_init(self):
        """Test reranker with custom parameters."""
        reranker = LlamaCppReranker(
            model_path="/path/to/model.gguf",
            model_name="custom-model",
            batch_size=64,
            n_ctx=1024,
        )

        assert reranker._model_path == "/path/to/model.gguf"
        assert reranker._model_name == "custom-model"
        assert reranker._batch_size == 64
        assert reranker._n_ctx == 1024


class TestLlamaCppRerankerLoad:
    """Tests for loading LlamaCppReranker model."""

    def test_load_sets_model(self):
        """Test that load sets the model."""
        reranker = LlamaCppReranker(model_path="/path/to/model.gguf")

        with patch("llama_cpp.Llama") as mock_llama:
            mock_llama.return_value = MagicMock()
            reranker.load()

        assert reranker._model is not None

    def test_load_raises_without_path(self):
        """Test that load raises when no model path is provided."""
        reranker = LlamaCppReranker()

        with pytest.raises(ValueError, match="No model_path or model_name"):
            reranker.load()


class TestLlamaCppRerankerRerank:
    """Tests for LlamaCppReranker reranking."""

    def test_rerank_empty_results(self):
        """Test reranking empty results."""
        reranker = LlamaCppReranker()

        results = reranker.rerank("query", [], top_k=10)

        assert results == []

    def test_rerank_returns_results(self, sample_search_results: list[SearchResult]):
        """Test that rerank returns results."""
        reranker = LlamaCppReranker(model_path="/path/to/model.gguf")

        with patch("llama_cpp.Llama") as mock_llama:
            mock_model = MagicMock()
            mock_model.embed.return_value = [0.1, 0.2, 0.3]
            mock_llama.return_value = mock_model

            results = reranker.rerank("query", sample_search_results, top_k=10)

        assert isinstance(results, list)
        assert len(results) <= 10

    def test_rerank_limits_top_k(self, sample_search_results: list[SearchResult]):
        """Test that rerank respects top_k limit."""
        reranker = LlamaCppReranker(model_path="/path/to/model.gguf")

        with patch("llama_cpp.Llama") as mock_llama:
            mock_model = MagicMock()
            mock_model.embed.return_value = [0.1, 0.2, 0.3]
            mock_llama.return_value = mock_model

            results = reranker.rerank("query", sample_search_results, top_k=3)

        assert len(results) <= 3

    def test_rerank_preserves_result_type(self, sample_search_results: list[SearchResult]):
        """Test that rerank returns SearchResult objects."""
        reranker = LlamaCppReranker(model_path="/path/to/model.gguf")

        with patch("llama_cpp.Llama") as mock_llama:
            mock_model = MagicMock()
            mock_model.embed.return_value = [0.1, 0.2, 0.3]
            mock_llama.return_value = mock_model

            results = reranker.rerank("query", sample_search_results, top_k=10)

        assert all(isinstance(r, SearchResult) for r in results)

    def test_rerank_sorts_by_score(self, sample_search_results: list[SearchResult]):
        """Test that rerank sorts results by score."""
        reranker = LlamaCppReranker(model_path="/path/to/model.gguf")

        with patch("llama_cpp.Llama") as mock_llama:
            mock_model = MagicMock()
            # Return different embeddings to create different scores
            # Need len(results) + 1 embeddings (query + each document)
            embeddings = [
                [i * 0.1, i * 0.2, i * 0.3] for i in range(len(sample_search_results) + 1)
            ]
            mock_model.embed.side_effect = embeddings
            mock_llama.return_value = mock_model

            results = reranker.rerank("query", sample_search_results, top_k=10)

        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_rerank_adds_reranker_score(self, sample_search_results: list[SearchResult]):
        """Test that rerank adds reranker_score to scores dict."""
        reranker = LlamaCppReranker(model_path="/path/to/model.gguf")

        with patch("llama_cpp.Llama") as mock_llama:
            mock_model = MagicMock()
            mock_model.embed.return_value = [0.1, 0.2, 0.3]
            mock_llama.return_value = mock_model

            results = reranker.rerank("query", sample_search_results, top_k=10)

        assert all("reranker_score" in r.scores for r in results)


# =============================================================================
# CrossEncoderReranker Tests
# =============================================================================


class TestCrossEncoderRerankerInit:
    """Tests for CrossEncoderReranker initialization."""

    def test_default_init(self):
        """Test default cross-encoder reranker initialization."""
        reranker = CrossEncoderReranker()

        assert reranker._model_name == "cross-encoder/ms-marco-MiniLM-L-6-v2"
        assert reranker._batch_size == 32
        assert reranker._model_path is None
        assert reranker._model is None

    def test_custom_init(self):
        """Test cross-encoder reranker with custom parameters."""
        reranker = CrossEncoderReranker(
            model_name="custom-model",
            model_path="/path/to/model",
            device="cpu",
            batch_size=64,
        )

        assert reranker._model_name == "custom-model"
        assert reranker._model_path == "/path/to/model"
        assert reranker._device == "cpu"
        assert reranker._batch_size == 64


class TestCrossEncoderRerankerLoad:
    """Tests for loading CrossEncoderReranker model."""

    def test_load_sets_model(self):
        """Test that load sets the model."""
        reranker = CrossEncoderReranker()

        with patch("sentence_transformers.CrossEncoder") as mock_ce:
            mock_ce.return_value = MagicMock()
            reranker.load()

        assert reranker._model is not None


class TestCrossEncoderRerankerRerank:
    """Tests for CrossEncoderReranker reranking."""

    def test_rerank_empty_results(self):
        """Test reranking empty results."""
        reranker = CrossEncoderReranker()

        results = reranker.rerank("query", [], top_k=10)

        assert results == []

    def test_rerank_returns_results(self, sample_search_results: list[SearchResult]):
        """Test that rerank returns results."""
        reranker = CrossEncoderReranker()

        with patch("sentence_transformers.CrossEncoder") as mock_ce:
            mock_model = MagicMock()
            mock_model.predict.return_value = [0.5, 0.3, 0.8, 0.2, 0.9]
            mock_ce.return_value = mock_model

            results = reranker.rerank("query", sample_search_results, top_k=10)

        assert isinstance(results, list)
        assert len(results) <= 10

    def test_rerank_limits_top_k(self, sample_search_results: list[SearchResult]):
        """Test that rerank respects top_k limit."""
        reranker = CrossEncoderReranker()

        with patch("sentence_transformers.CrossEncoder") as mock_ce:
            mock_model = MagicMock()
            mock_model.predict.return_value = [0.5, 0.3, 0.8, 0.2, 0.9]
            mock_ce.return_value = mock_model

            results = reranker.rerank("query", sample_search_results, top_k=3)

        assert len(results) <= 3

    def test_rerank_adds_reranker_score(self, sample_search_results: list[SearchResult]):
        """Test that rerank adds reranker_score to scores dict."""
        reranker = CrossEncoderReranker()

        with patch("sentence_transformers.CrossEncoder") as mock_ce:
            mock_model = MagicMock()
            mock_model.predict.return_value = [0.5, 0.3, 0.8, 0.2, 0.9]
            mock_ce.return_value = mock_model

            results = reranker.rerank("query", sample_search_results, top_k=10)

        assert all("reranker_score" in r.scores for r in results)


# =============================================================================
# Factory Tests
# =============================================================================


class TestCreateReranker:
    """Tests for create_reranker factory function."""

    def test_create_reranker_gguf_default(self):
        """Test factory creates LlamaCppReranker for gguf type."""
        settings = MagicMock()
        settings.reranker_model_type = "gguf"
        settings.reranker_model_name = "model.gguf"
        settings.reranker_model_path = None
        settings.reranker_batch_size = 32

        reranker = create_reranker(settings)

        assert isinstance(reranker, LlamaCppReranker)
        assert reranker._model_name == "model.gguf"

    def test_create_reranker_sentence_transformers(self):
        """Test factory creates CrossEncoderReranker for sentence_transformers type."""
        settings = MagicMock()
        settings.reranker_model_type = "sentence_transformers"
        settings.reranker_model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        settings.reranker_model_path = None
        settings.reranker_batch_size = 32

        reranker = create_reranker(settings)

        assert isinstance(reranker, CrossEncoderReranker)
        assert reranker._model_name == "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def test_create_reranker_unknown_type_raises(self):
        """Test factory raises ValueError for unknown type."""
        settings = MagicMock()
        settings.reranker_model_type = "unknown"

        with pytest.raises(ValueError, match="Unknown reranker model_type"):
            create_reranker(settings)

    def test_create_reranker_uses_model_path(self):
        """Test factory passes model_path to reranker."""
        settings = MagicMock()
        settings.reranker_model_type = "gguf"
        settings.reranker_model_name = ""
        settings.reranker_model_path = "/path/to/model.gguf"
        settings.reranker_batch_size = 16

        reranker = create_reranker(settings)

        assert isinstance(reranker, LlamaCppReranker)
        assert reranker._model_path == "/path/to/model.gguf"
        assert reranker._batch_size == 16


# =============================================================================
# Backwards Compatibility Tests
# =============================================================================


class TestRerankerAlias:
    """Tests for backwards-compatible Reranker alias."""

    def test_reranker_alias_is_llama_cpp(self):
        """Test that Reranker alias points to LlamaCppReranker."""
        assert Reranker is LlamaCppReranker

    def test_reranker_alias_init(self):
        """Test that Reranker alias can be instantiated."""
        reranker = Reranker(model_path="/path/to/model.gguf")

        assert isinstance(reranker, LlamaCppReranker)


# =============================================================================
# Edge Cases
# =============================================================================


class TestRerankerEdgeCases:
    """Tests for reranker edge cases."""

    def test_rerank_single_result(self):
        """Test reranking single result."""
        reranker = LlamaCppReranker(model_path="/path/to/model.gguf")
        single_result = [
            SearchResult(
                document_id="doc-1",
                path="/path/1.md",
                title="T1",
                collection_name="c",
                score=0.95,
                content="content",
            ),
        ]

        with patch("llama_cpp.Llama") as mock_llama:
            mock_model = MagicMock()
            mock_model.embed.return_value = [0.1, 0.2, 0.3]
            mock_llama.return_value = mock_model

            results = reranker.rerank("query", single_result, top_k=10)

        assert len(results) == 1

    def test_rerank_with_missing_content(self):
        """Test reranking results with missing content."""
        reranker = LlamaCppReranker(model_path="/path/to/model.gguf")
        results_with_none_content = [
            SearchResult(
                document_id="doc-1",
                path="/path/1.md",
                title="T1",
                collection_name="c",
                score=0.95,
                content=None,
                highlights=["highlight"],
            ),
        ]

        with patch("llama_cpp.Llama") as mock_llama:
            mock_model = MagicMock()
            mock_model.embed.return_value = [0.1, 0.2, 0.3]
            mock_llama.return_value = mock_model

            results = reranker.rerank("query", results_with_none_content, top_k=10)

        assert len(results) == 1

    def test_rerank_handles_large_result_sets(self):
        """Test that rerank handles large result sets."""
        reranker = LlamaCppReranker(model_path="/path/to/model.gguf", batch_size=32)
        large_results = [
            SearchResult(
                document_id=f"doc-{i}",
                path=f"/path/{i}.md",
                title=f"T{i}",
                collection_name="c",
                score=max(0.0, 0.9 - i * 0.01),
                content=f"content {i}",
            )
            for i in range(100)
        ]

        with patch("llama_cpp.Llama") as mock_llama:
            mock_model = MagicMock()
            mock_model.embed.return_value = [0.1, 0.2, 0.3]
            mock_llama.return_value = mock_model

            results = reranker.rerank("query", large_results, top_k=50)

        assert len(results) <= 50

    def test_cross_encoder_rerank_with_missing_content(self):
        """Test CrossEncoder reranking with missing content."""
        reranker = CrossEncoderReranker()
        results_with_none_content = [
            SearchResult(
                document_id="doc-1",
                path="/path/1.md",
                title="T1",
                collection_name="c",
                score=0.95,
                content=None,
                highlights=["highlight"],
            ),
        ]

        with patch("sentence_transformers.CrossEncoder") as mock_ce:
            mock_model = MagicMock()
            mock_model.predict.return_value = [0.5]
            mock_ce.return_value = mock_model

            results = reranker.rerank("query", results_with_none_content, top_k=10)

        assert len(results) == 1
