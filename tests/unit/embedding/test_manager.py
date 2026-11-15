"""Unit tests for EmbeddingManager."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sif.config.settings import Settings
from sif.embedding.cache import EmbeddingCache
from sif.embedding.manager import EmbeddingManager
from sif.models.embedding import EmbeddingConfig, EmbeddingOutputError, ModelType


# D-19: the pre-Phase-21 default ``_cache_model_id()`` for the shipped
# ModelScope Qwen3 settings. This literal is the byte-identical baseline the
# Phase 23 Harrier gate compares against; it must never be regenerated from
# the current code, only asserted.
DEFAULT_QWEN3_CACHE_MODEL_ID = "modelscope:Qwen/Qwen3-Embedding-0.6B"
DEFAULT_QWEN3_MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"


class TestEmbeddingManager:
    def test_from_settings_passes_api_key_and_api_base(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Keep the test hermetic: no real cache DB under ~/.Caches/SIF.
        monkeypatch.delenv("SIF_CACHE_EMBEDDINGS", raising=False)
        settings = Settings(
            model_type="openai",
            model_name="text-embedding-3-small",
            api_key="sk-test",
            api_base="https://api.example.com/v1",
            embedding_dim=256,
            cache_embeddings=False,
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

    def test_load_model_passes_batch_size(self) -> None:
        """EmbeddingConfig.batch_size must reach the factory/model."""
        mock_embedder = MagicMock()
        mock_embedder.dimension = 4
        mock_factory = MagicMock()
        mock_factory.create_model.return_value = mock_embedder
        config = EmbeddingConfig(
            model_type=ModelType.OPENAI,
            model_name="test-openai",
            batch_size=5,
        )
        manager = EmbeddingManager(config=config, factory=mock_factory)
        manager.load_model()
        assert mock_factory.create_model.call_args.kwargs["batch_size"] == 5

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

    def test_model_property_reflects_load_state(self) -> None:
        """Phase 10 IN-03: model exposes the loaded embedder lifecycle."""
        mock_embedder = MagicMock()
        mock_factory = MagicMock()
        mock_factory.create_model.return_value = mock_embedder
        config = EmbeddingConfig(model_type=ModelType.SENTENCE_TRANSFORMERS, model_name="test")
        manager = EmbeddingManager(config=config, factory=mock_factory)

        assert manager.model is None
        manager.load_model()
        assert manager.model is mock_embedder
        manager.unload_model()
        assert manager.model is None

    def test_model_property_is_read_only(self) -> None:
        """Phase 10 IN-03: model rejects assignment because it has no setter."""
        mock_embedder = MagicMock()
        mock_factory = MagicMock()
        mock_factory.create_model.return_value = mock_embedder
        config = EmbeddingConfig(model_type=ModelType.SENTENCE_TRANSFORMERS, model_name="test")
        manager = EmbeddingManager(config=config, factory=mock_factory)

        with pytest.raises(AttributeError):
            manager.model = mock_embedder


# =============================================================================
# Role-aware embedding + prompt/revision cache buckets (EMB-02, D-06/D-08)
# =============================================================================


class _RecordingEmbedder:
    """Fake embedder with class-level role methods recording every call."""

    def __init__(self, dimension: int = 2, revision: str | None = None) -> None:
        self.dimension = dimension
        self.revision = revision
        self.batch_calls: list[list[str]] = []
        self.query_calls: list[list[str]] = []
        self.document_calls: list[list[str]] = []

    def embed(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self.batch_calls.append(list(texts))
        return [[0.1] * self.dimension for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_queries([text])[0]

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        self.query_calls.append(list(texts))
        return [[0.2] * self.dimension for _ in texts]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.document_calls.append(list(texts))
        return [[0.3] * self.dimension for _ in texts]


def _make_manager(
    tmp_path: Path,
    embedder: object,
    cache: EmbeddingCache | None = None,
    **config_kwargs: object,
) -> EmbeddingManager:
    factory = MagicMock()
    factory.create_model.return_value = embedder
    config = EmbeddingConfig(
        model_type=ModelType.SENTENCE_TRANSFORMERS,
        model_name="models/test",
        embedding_dim=getattr(embedder, "dimension", 2),
        cache_embeddings=cache is not None,
        cache_dir=str(tmp_path) if cache is not None else None,
        **config_kwargs,
    )
    return EmbeddingManager(config=config, factory=factory, cache=cache)


class TestCacheBuckets:
    def test_default_bucket_is_the_legacy_cache_model_id(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path, _RecordingEmbedder())
        expected = "sentence_transformers:models/test"
        assert manager._cache_bucket("query") == expected
        assert manager._cache_bucket("document") == expected
        assert manager._cache_model_id() == expected

    def test_default_qwen3_buckets_are_the_pre_phase_baseline(self) -> None:
        """D-19: default ModelScope Qwen3 keeps the exact pre-Phase-21 bucket.

        Both role buckets must equal the recorded pre-phase ``_cache_model_id()``
        string, no revision suffix may appear, and the role methods must route
        through the unchanged plain ``embed_batch`` call (Qwen3 has no prompt).
        """
        embedder = _RecordingEmbedder(dimension=1024)
        factory = MagicMock()
        factory.create_model.return_value = embedder
        config = EmbeddingConfig(
            model_type=ModelType.MODELSCOPE,
            model_name=DEFAULT_QWEN3_MODEL_NAME,
            embedding_dim=1024,
            cache_embeddings=False,
        )
        manager = EmbeddingManager(config=config, factory=factory)

        assert manager._cache_model_id() == DEFAULT_QWEN3_CACHE_MODEL_ID
        assert manager._cache_bucket("query") == DEFAULT_QWEN3_CACHE_MODEL_ID
        assert manager._cache_bucket("document") == DEFAULT_QWEN3_CACHE_MODEL_ID
        assert "|rev@" not in manager._cache_bucket("query")

        manager.embed_query("same text")
        manager.embed_documents(["same text"])

        assert embedder.batch_calls == [["same text"], ["same text"]]
        assert embedder.query_calls == []
        assert embedder.document_calls == []

    def test_prompts_produce_distinct_role_buckets(self, tmp_path: Path) -> None:
        manager = _make_manager(
            tmp_path,
            _RecordingEmbedder(),
            query_prompt_name="web_search_query",
            document_prompt_name="doc-passage",
        )
        base = "sentence_transformers:models/test"
        assert manager._cache_bucket("query") == f"{base}|q@web_search_query"
        assert manager._cache_bucket("document") == f"{base}|d@doc-passage"

    def test_revision_suffix_precedes_role_suffix(self, tmp_path: Path) -> None:
        manager = _make_manager(
            tmp_path,
            _RecordingEmbedder(revision="sha256:abc"),
            query_prompt_name="q",
        )
        base = "sentence_transformers:models/test"
        assert manager._cache_bucket("document") == f"{base}|rev@sha256:abc"
        assert manager._cache_bucket("query") == f"{base}|rev@sha256:abc|q@q"

    def test_unknown_role_raises(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path, _RecordingEmbedder())
        with pytest.raises(ValueError, match="Unknown embedding role"):
            manager._cache_bucket("bogus")


class TestRoleMethods:
    def test_default_roles_call_embed_batch_like_embed(self, tmp_path: Path) -> None:
        embedder = _RecordingEmbedder()
        manager = _make_manager(tmp_path, embedder)

        manager.embed(["same"])
        manager.embed_queries(["same"])
        manager.embed_documents(["same"])

        assert embedder.batch_calls == [["same"], ["same"], ["same"]]
        assert embedder.query_calls == []
        assert embedder.document_calls == []

    def test_prompted_roles_use_concrete_role_methods(self, tmp_path: Path) -> None:
        embedder = _RecordingEmbedder()
        manager = _make_manager(
            tmp_path,
            embedder,
            query_prompt_name="query-prompt",
            document_prompt_name="document-prompt",
        )

        assert manager.embed_query("same text") == [0.2, 0.2]
        assert manager.embed_documents(["same text"]).embeddings == [[0.3, 0.3]]
        assert embedder.query_calls == [["same text"]]
        assert embedder.document_calls == [["same text"]]
        assert embedder.batch_calls == []

    def test_prompted_roles_never_share_cache_rows(self, tmp_path: Path) -> None:
        cache = EmbeddingCache(tmp_path)
        manager = _make_manager(
            tmp_path,
            _RecordingEmbedder(),
            cache=cache,
            query_prompt_name="q",
            document_prompt_name="d",
        )

        query_vector = manager.embed_query("same text")
        document_vector = manager.embed_documents(["same text"]).embeddings[0]

        assert query_vector != document_vector
        query_bucket = manager._cache_bucket("query")
        document_bucket = manager._cache_bucket("document")
        assert cache.get("same text", model_id=query_bucket) == query_vector
        assert cache.get("same text", model_id=document_bucket) == document_vector

    def test_role_response_matches_embed_shape(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path, _RecordingEmbedder())
        response = manager.embed_queries(["alpha", "beta"])
        assert response.model_id == "models/test"
        assert response.dimensions == 2
        assert len(response.embeddings) == 2
        assert response.total_tokens == sum(len(t) // 4 for t in ["alpha", "beta"])

    def test_role_methods_keep_the_count_guard(self, tmp_path: Path) -> None:
        class _ShortEmbedder(_RecordingEmbedder):
            def embed_batch(self, _texts: list[str]) -> list[list[float]]:
                return [[0.1] * self.dimension]

        manager = _make_manager(tmp_path, _ShortEmbedder())
        with pytest.raises(RuntimeError, match="1 embeddings for 2 inputs"):
            manager.embed_queries(["alpha", "beta"])

    def test_get_identity_records_effective_prompts(self, tmp_path: Path) -> None:
        manager = _make_manager(
            tmp_path,
            _RecordingEmbedder(revision="sha256:abc"),
            query_prompt_name="q",
        )
        identity = manager.get_identity()
        assert identity.query_prompt == "q"
        assert identity.document_prompt is None
        assert identity.revision == "sha256:abc"

    def test_get_identity_is_cached_until_unload(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path, _RecordingEmbedder())
        first = manager.get_identity()
        assert manager.get_identity() is first
        manager.unload_model()
        assert manager._identity is None
        second = manager.get_identity()
        assert second is not first
        assert second == first


class TestCacheSafety:
    def test_non_finite_and_wrong_length_entries_are_recomputed(self, tmp_path: Path) -> None:
        cache = EmbeddingCache(tmp_path)
        embedder = _RecordingEmbedder()
        manager = _make_manager(tmp_path, embedder, cache=cache)
        bucket = manager._cache_bucket("document")
        cache.set("nan text", [float("nan"), 0.1], model_id=bucket)
        cache.set("short text", [0.1], model_id=bucket)

        response = manager.embed_documents(["nan text", "short text"])

        assert embedder.batch_calls == [["nan text", "short text"]]
        assert response.embeddings == [[0.1, 0.1], [0.1, 0.1]]
        assert cache.get("nan text", model_id=bucket) == [0.1, 0.1]
        assert cache.get("short text", model_id=bucket) == [0.1, 0.1]

    def test_non_finite_model_output_raises_naming_bucket_and_position(
        self, tmp_path: Path
    ) -> None:
        class _NonFiniteEmbedder(_RecordingEmbedder):
            def embed_batch(self, _texts: list[str]) -> list[list[float]]:
                return [[0.1, 0.1], [float("inf"), 0.1]]

        manager = _make_manager(tmp_path, _NonFiniteEmbedder())
        with pytest.raises(RuntimeError, match="non-finite vector at position 1") as excinfo:
            manager.embed_documents(["alpha", "beta"])
        assert "sentence_transformers:models/test" in str(excinfo.value)

    def test_wrong_dimension_model_output_raises(self, tmp_path: Path) -> None:
        class _WrongDimEmbedder(_RecordingEmbedder):
            def embed_batch(self, _texts: list[str]) -> list[list[float]]:
                return [[0.1, 0.1, 0.1] for _ in _texts]

        manager = _make_manager(tmp_path, _WrongDimEmbedder())
        with pytest.raises(RuntimeError, match="3-dim vector at position 0; expected 2 dims"):
            manager.embed_documents(["alpha"])

    def test_from_settings_forwards_prompt_names(self) -> None:
        settings = Settings(
            model_type="sentence_transformers",
            model_name="models/test",
            embedding_dim=2,
            cache_embeddings=False,
            query_prompt_name="q",
            document_prompt_name="d",
        )
        manager = EmbeddingManager.from_settings(settings)
        assert manager._config.query_prompt_name == "q"
        assert manager._config.document_prompt_name == "d"
        assert manager._prompt_scheme.query_prompt == "q"
        assert manager._prompt_scheme.document_prompt == "d"


class TestSystemicOutputErrors:
    """WR-02: model-output defects raise the dedicated systemic exception."""

    def test_wrong_dimension_raises_embedding_output_error(self, tmp_path: Path) -> None:
        class _WrongDimEmbedder(_RecordingEmbedder):
            def embed_batch(self, _texts: list[str]) -> list[list[float]]:
                return [[0.1, 0.1, 0.1] for _ in _texts]

        manager = _make_manager(tmp_path, _WrongDimEmbedder())
        with pytest.raises(EmbeddingOutputError, match="3-dim vector at position 0"):
            manager.embed_documents(["alpha"])

    def test_count_mismatch_raises_embedding_output_error(self, tmp_path: Path) -> None:
        class _ShortEmbedder(_RecordingEmbedder):
            def embed_batch(self, _texts: list[str]) -> list[list[float]]:
                return [[0.1] * self.dimension]

        manager = _make_manager(tmp_path, _ShortEmbedder())
        with pytest.raises(EmbeddingOutputError, match="1 embeddings for 2 inputs"):
            manager.embed_queries(["alpha", "beta"])

    def test_non_finite_output_raises_embedding_output_error(self, tmp_path: Path) -> None:
        class _NonFiniteEmbedder(_RecordingEmbedder):
            def embed_batch(self, _texts: list[str]) -> list[list[float]]:
                return [[float("nan")] * self.dimension for _ in _texts]

        manager = _make_manager(tmp_path, _NonFiniteEmbedder())
        with pytest.raises(EmbeddingOutputError, match="non-finite vector at position 0"):
            manager.embed_documents(["alpha"])


class TestRoleHelpers:
    def test_concept_embedder_falls_back_to_embed(self) -> None:
        from sif.embedding import roles
        from tests.support.bench import ConceptEmbedder

        embedder = ConceptEmbedder()
        assert roles.embed_query(embedder, "hello") == embedder.embed("hello")
        assert roles.embed_queries(embedder, ["hello"]) == [embedder.embed("hello")]

    def test_magicmock_falls_back_to_embed_without_phantom_role_call(self) -> None:
        from sif.embedding import roles

        embedder = MagicMock()
        embedder.embed.return_value = [0.5]
        embedder.embed_batch.return_value = [[0.5]]

        assert roles.embed_query(embedder, "x") == [0.5]
        embedder.embed.assert_called_once_with("x")
        embedder.embed_query.assert_not_called()

        assert roles.embed_documents(embedder, ["x"]) == [[0.5]]
        embedder.embed_batch.assert_called_once_with(["x"])
        embedder.embed_documents.assert_not_called()

    def test_concrete_role_methods_are_preferred(self) -> None:
        from sif.embedding import roles

        embedder = _RecordingEmbedder()
        assert roles.embed_queries(embedder, ["x"]) == [[0.2, 0.2]]
        assert roles.embed_documents(embedder, ["x"]) == [[0.3, 0.3]]
        assert embedder.query_calls == [["x"]]
        assert embedder.document_calls == [["x"]]
