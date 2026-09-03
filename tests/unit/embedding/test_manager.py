"""Unit tests for EmbeddingManager."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sif.config.settings import Settings
from sif.embedding.cache import EmbeddingCache
from sif.embedding.manager import EmbeddingManager
from sif.models.embedding import EmbeddingConfig, ModelType


class TestEmbeddingManager:
    def test_from_settings_passes_api_key_and_api_base(self) -> None:
        settings = Settings(
            model_type="openai",
            model_name="text-embedding-3-small",
            api_key="sk-test",
            api_base="https://api.example.com/v1",
            embedding_dim=256,
        )
        manager = EmbeddingManager.from_settings(settings)
        assert manager._config.model_type == ModelType.OPENAI
        assert manager._config.api_key == "sk-test"
        assert manager._config.api_base == "https://api.example.com/v1"
        assert manager._config.embedding_dim == 256

    def test_embedding_config_api_key_never_leaks(self) -> None:
        """api_key must be absent from both repr() and model_dump()."""
        config = EmbeddingConfig(api_key="sk-secret")
        assert config.api_key == "sk-secret"
        assert "sk-secret" not in repr(config)
        assert "api_key" not in config.model_dump()
        assert "sk-secret" not in str(config.model_dump())

    def test_cache_is_segmented_by_model(self, tmp_path: Path) -> None:
        """Same text under two models must not share cached embeddings."""
        cache = EmbeddingCache(tmp_path)

        def make_manager(model_name: str) -> tuple[EmbeddingManager, MagicMock]:
            mock_embedder = MagicMock()
            mock_embedder.embed_batch.return_value = [[0.1, 0.2]]
            mock_embedder.dimension = 2
            mock_factory = MagicMock()
            mock_factory.create_model.return_value = mock_embedder
            config = EmbeddingConfig(
                model_type=ModelType.SENTENCE_TRANSFORMERS,
                model_name=model_name,
                cache_embeddings=True,
                cache_dir=str(tmp_path),
            )
            return (
                EmbeddingManager(config=config, factory=mock_factory, cache=cache),
                mock_embedder,
            )

        manager_a, embedder_a = make_manager("model-a")
        response_a = manager_a.embed(["hello"])
        embedder_a.embed_batch.assert_called_once_with(["hello"])
        assert response_a.embeddings == [[0.1, 0.2]]

        # A different model reading the same text must miss the shared bucket.
        manager_b, embedder_b = make_manager("model-b")
        response_b = manager_b.embed(["hello"])
        embedder_b.embed_batch.assert_called_once_with(["hello"])
        assert response_b.embeddings == [[0.1, 0.2]]

        # The same model re-embedding must hit the cache (no backend call).
        manager_a2, embedder_a2 = make_manager("model-a")
        response_a2 = manager_a2.embed(["hello"])
        embedder_a2.embed_batch.assert_not_called()
        assert response_a2.embeddings == [[0.1, 0.2]]

    def test_load_model_uses_factory(self) -> None:
        mock_embedder = MagicMock()
        mock_embedder.dimension = 384
        mock_factory = MagicMock()
        mock_factory.create_model.return_value = mock_embedder
        config = EmbeddingConfig(model_type=ModelType.SENTENCE_TRANSFORMERS, model_name="test")
        manager = EmbeddingManager(config=config, factory=mock_factory)
        manager.load_model()
        assert manager._model is mock_embedder
        mock_factory.create_model.assert_called_once()
        call_kwargs = mock_factory.create_model.call_args.kwargs
        assert call_kwargs["model_type"] == ModelType.SENTENCE_TRANSFORMERS

    def test_embed_uses_embed_batch(self) -> None:
        mock_embedder = MagicMock()
        mock_embedder.embed_batch.return_value = [[0.1, 0.2], [0.3, 0.4]]
        mock_embedder.dimension = 2
        mock_factory = MagicMock()
        mock_factory.create_model.return_value = mock_embedder
        config = EmbeddingConfig(model_type=ModelType.SENTENCE_TRANSFORMERS, model_name="test")
        manager = EmbeddingManager(config=config, factory=mock_factory)
        response = manager.embed(["hello", "world"])
        assert len(response.embeddings) == 2
        assert response.dimensions == 2
        assert response.model_id == "test"
        mock_embedder.embed_batch.assert_called_once_with(["hello", "world"])

    def test_embed_single_returns_first_embedding(self) -> None:
        mock_embedder = MagicMock()
        mock_embedder.embed_batch.return_value = [[0.1, 0.2]]
        mock_embedder.dimension = 2
        mock_factory = MagicMock()
        mock_factory.create_model.return_value = mock_embedder
        config = EmbeddingConfig(model_type=ModelType.SENTENCE_TRANSFORMERS, model_name="test")
        manager = EmbeddingManager(config=config, factory=mock_factory)
        result = manager.embed_single("hello")
        assert result == [0.1, 0.2]

    def test_embed_fails_fast_on_short_backend_response(self) -> None:
        """A backend returning fewer vectors than inputs must fail fast."""
        mock_embedder = MagicMock()
        mock_embedder.embed_batch.return_value = [[0.1, 0.2]]  # 1 vector for 2 texts
        mock_embedder.dimension = 2
        mock_factory = MagicMock()
        mock_factory.create_model.return_value = mock_embedder
        config = EmbeddingConfig(model_type=ModelType.SENTENCE_TRANSFORMERS, model_name="test")
        manager = EmbeddingManager(config=config, factory=mock_factory)
        with pytest.raises(RuntimeError, match="1 embeddings for 2 inputs"):
            manager.embed(["hello", "world"])

    def test_unload_model_clears_reference(self) -> None:
        mock_embedder = MagicMock()
        mock_factory = MagicMock()
        mock_factory.create_model.return_value = mock_embedder
        config = EmbeddingConfig(model_type=ModelType.SENTENCE_TRANSFORMERS, model_name="test")
        manager = EmbeddingManager(config=config, factory=mock_factory)
        manager.load_model()
        manager.unload_model()
        assert manager._model is None

    def test_get_model_info_when_loaded(self) -> None:
        mock_embedder = MagicMock()
        mock_embedder.dimension = 512
        mock_factory = MagicMock()
        mock_factory.create_model.return_value = mock_embedder
        config = EmbeddingConfig(
            model_type=ModelType.SENTENCE_TRANSFORMERS,
            model_name="test-model",
            max_tokens=256,
        )
        manager = EmbeddingManager(config=config, factory=mock_factory)
        manager.load_model()
        info = manager.get_model_info()
        assert info["loaded"] is True
        assert info["model_id"] == "test-model"
        assert info["embedding_dim"] == 512
        assert info["max_tokens"] == 256
