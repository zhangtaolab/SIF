"""Tests for embedding model."""

from unittest.mock import MagicMock, patch

import pytest

from docsift.embedding.model import EmbeddingModel, ModelType


class TestModelType:
    """Tests for ModelType enum."""

    def test_gguf_type_exists(self):
        """Test that GGUF type exists."""
        assert ModelType.GGUF is not None

    def test_sentence_transformers_type_exists(self):
        """Test that SENTENCE_TRANSFORMERS type exists."""
        assert ModelType.SENTENCE_TRANSFORMERS is not None

    def test_openai_type_exists(self):
        """Test that OPENAI type exists."""
        assert ModelType.OPENAI is not None

    def test_huggingface_type_exists(self):
        """Test that HUGGINGFACE type exists."""
        assert ModelType.HUGGINGFACE is not None


class TestEmbeddingModelInterface:
    """Tests for EmbeddingModel abstract interface."""

    def test_embedding_model_is_abstract(self):
        """Test that EmbeddingModel is an abstract base class."""
        assert hasattr(EmbeddingModel, "__abstractmethods__")

    def test_embedding_model_requires_load(self):
        """Test that EmbeddingModel requires load method."""
        assert "load" in EmbeddingModel.__abstractmethods__

    def test_embedding_model_requires_unload(self):
        """Test that EmbeddingModel requires unload method."""
        assert "unload" in EmbeddingModel.__abstractmethods__

    def test_embedding_model_requires_embed(self):
        """Test that EmbeddingModel requires embed method."""
        assert "embed" in EmbeddingModel.__abstractmethods__

    def test_embedding_model_requires_embed_single(self):
        """Test that EmbeddingModel requires embed_single method."""
        assert "embed_single" in EmbeddingModel.__abstractmethods__


class TestMockEmbeddingModel:
    """Tests using mocked embedding model."""

    def test_mock_embedder_can_embed_batch(self, mock_embedder: MagicMock):
        """Test that mock embedder can embed multiple texts."""
        # Arrange
        texts = ["text 1", "text 2", "text 3"]

        # Act
        embeddings = mock_embedder.embed(texts)

        # Assert
        assert len(embeddings) == 3
        assert all(len(e) == 384 for e in embeddings)

    def test_mock_embedder_can_embed_single(self, mock_embedder: MagicMock):
        """Test that mock embedder can embed single text."""
        # Act
        embedding = mock_embedder.embed_single("test text")

        # Assert
        assert len(embedding) == 384

    def test_mock_embedder_consistent_for_same_text(self, mock_embedder: MagicMock):
        """Test that mock embedder produces consistent embeddings."""
        # Act
        embedding1 = mock_embedder.embed_single("same text")
        embedding2 = mock_embedder.embed_single("same text")

        # Assert
        assert embedding1 == embedding2

    def test_mock_embedder_different_for_different_texts(self, mock_embedder: MagicMock):
        """Test that mock embedder produces different embeddings for different texts."""
        # Act
        embedding1 = mock_embedder.embed_single("text one")
        embedding2 = mock_embedder.embed_single("text two")

        # Assert
        assert embedding1 != embedding2

    def test_mock_embedder_returns_expected_properties(self, mock_embedder: MagicMock):
        """Test that mock embedder returns expected properties."""
        # Assert
        assert mock_embedder.model_id == "test-model"
        assert mock_embedder.embedding_dim == 384
        assert mock_embedder.max_tokens == 512
        assert mock_embedder.loaded is True


class TestEmbeddingModelProperties:
    """Tests for embedding model properties."""

    def test_model_id_property(self):
        """Test model_id property."""

        # Create a concrete implementation for testing
        class TestModel(EmbeddingModel):
            def load(self):
                pass

            def unload(self):
                pass

            def embed(self, texts, normalize=True):
                return []

            def embed_single(self, text, normalize=True):
                return []

        model = TestModel("test-id", 384, 512)

        assert model.model_id == "test-id"

    def test_embedding_dim_property(self):
        """Test embedding_dim property."""

        class TestModel(EmbeddingModel):
            def load(self):
                pass

            def unload(self):
                pass

            def embed(self, texts, normalize=True):
                return []

            def embed_single(self, text, normalize=True):
                return []

        model = TestModel("test-id", 768, 512)

        assert model.embedding_dim == 768

    def test_max_tokens_property(self):
        """Test max_tokens property."""

        class TestModel(EmbeddingModel):
            def load(self):
                pass

            def unload(self):
                pass

            def embed(self, texts, normalize=True):
                return []

            def embed_single(self, text, normalize=True):
                return []

        model = TestModel("test-id", 384, 1024)

        assert model.max_tokens == 1024

    def test_loaded_property_initial(self):
        """Test loaded property initial value."""

        class TestModel(EmbeddingModel):
            def load(self):
                pass

            def unload(self):
                pass

            def embed(self, texts, normalize=True):
                return []

            def embed_single(self, text, normalize=True):
                return []

        model = TestModel("test-id", 384, 512)

        assert model.loaded is False


class TestEmbeddingModelCountTokens:
    """Tests for token counting."""

    def test_count_tokens_estimate(self):
        """Test token count estimation."""

        class TestModel(EmbeddingModel):
            def load(self):
                pass

            def unload(self):
                pass

            def embed(self, texts, normalize=True):
                return []

            def embed_single(self, text, normalize=True):
                return []

        model = TestModel("test-id", 384, 512)

        # Rough estimate: 1 token ~= 4 characters
        assert model.count_tokens("aaaa") == 1
        assert model.count_tokens("a" * 40) == 10

    def test_count_tokens_empty(self):
        """Test token count for empty string."""

        class TestModel(EmbeddingModel):
            def load(self):
                pass

            def unload(self):
                pass

            def embed(self, texts, normalize=True):
                return []

            def embed_single(self, text, normalize=True):
                return []

        model = TestModel("test-id", 384, 512)

        assert model.count_tokens("") == 0


class TestEmbeddingBatching:
    """Tests for embedding batching behavior."""

    def test_embed_returns_same_count_as_input(self, mock_embedder: MagicMock):
        """Test that embed returns one embedding per input text."""
        # Arrange
        texts = ["text 1", "text 2", "text 3", "text 4", "text 5"]

        # Act
        embeddings = mock_embedder.embed(texts)

        # Assert
        assert len(embeddings) == len(texts)

    def test_embed_empty_list(self, mock_embedder: MagicMock):
        """Test embed with empty list."""
        # Act
        embeddings = mock_embedder.embed([])

        # Assert
        assert embeddings == []

    def test_embed_single_vs_batch(self, mock_embedder: MagicMock):
        """Test that embed_single matches batch embed."""
        # Act
        single_embedding = mock_embedder.embed_single("test")
        batch_embeddings = mock_embedder.embed(["test"])

        # Assert
        assert single_embedding == batch_embeddings[0]


class TestEmbeddingNormalization:
    """Tests for embedding normalization."""

    def test_embed_accepts_normalize_parameter(self, mock_embedder: MagicMock):
        """Test that embed accepts normalize parameter."""
        # Act & Assert - should not raise
        mock_embedder.embed(["test"], normalize=True)
        mock_embedder.embed(["test"], normalize=False)

    def test_embed_single_accepts_normalize_parameter(self, mock_embedder: MagicMock):
        """Test that embed_single accepts normalize parameter."""
        # Act & Assert - should not raise
        mock_embedder.embed_single("test", normalize=True)
        mock_embedder.embed_single("test", normalize=False)


class TestEmbeddingModelFactory:
    """Tests for embedding model factory protocol."""

    def test_factory_protocol_exists(self):
        """Test that EmbeddingModelFactory protocol exists."""
        from docsift.embedding.model import EmbeddingModelFactory

        assert EmbeddingModelFactory is not None
