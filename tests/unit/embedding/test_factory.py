"""Tests for EmbeddingModelFactory dispatch (Wave-0 artifact)."""

from __future__ import annotations

import types
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from sif.config.settings import Settings
from sif.embedding.embedder import (
    LlamaCppEmbedder,
    ModelScopeEmbedder,
    OpenAIEmbedder,
    SentenceTransformerEmbedder,
)
from sif.embedding.factory import EmbeddingModelFactory
from sif.embedding.manager import EmbeddingManager
from sif.models.embedding import ModelType


VEC8 = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]


def _fake_openai_module() -> tuple[types.ModuleType, list[dict]]:
    """Build a fake openai module returning 8-dim vectors, recording calls."""
    constructor_calls: list[dict] = []

    class _FakeEmbeddings:
        def create(self, **kwargs: object) -> SimpleNamespace:
            texts = list(kwargs["input"])
            return SimpleNamespace(
                data=[SimpleNamespace(index=i, embedding=list(VEC8)) for i, _ in enumerate(texts)]
            )

    class _FakeClient:
        def __init__(self) -> None:
            self.embeddings = _FakeEmbeddings()

    def _openai_constructor(**kwargs: object) -> _FakeClient:
        constructor_calls.append(kwargs)
        return _FakeClient()

    module = types.ModuleType("openai")
    module.OpenAI = _openai_constructor
    return module, constructor_calls


def _sentence_transformers_modules() -> dict[str, MagicMock]:
    """Mock sentence_transformers + torch modules (test_embedder_impl pattern)."""
    mock_model = MagicMock()
    mock_model.get_sentence_embedding_dimension.return_value = 384
    mock_st = MagicMock()
    mock_st.return_value = mock_model

    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = False
    mock_mps = MagicMock()
    mock_mps.is_available.return_value = False
    mock_torch.backends.mps = mock_mps

    st_module = MagicMock()
    st_module.SentenceTransformer = mock_st
    return {"sentence_transformers": st_module, "torch": mock_torch}


def _assert_working_embedder(model: Any) -> None:
    """Assert the object satisfies the working-Embedder surface."""
    assert callable(model.embed)
    assert callable(model.embed_batch)
    assert isinstance(model.dimension, int)


class TestEmbeddingModelFactoryDispatch:
    """Dispatch matrix: every Settings-advertised backend constructs."""

    def test_sentence_transformers_dispatch(self) -> None:
        with patch.dict("sys.modules", _sentence_transformers_modules()):
            model = EmbeddingModelFactory().create_model(
                ModelType.SENTENCE_TRANSFORMERS, None, "test-st"
            )

        assert isinstance(model, SentenceTransformerEmbedder)
        _assert_working_embedder(model)
        assert model.dimension == 384

    def test_openai_dispatch_captures_client_kwargs(self) -> None:
        fake_module, constructor_calls = _fake_openai_module()

        with patch.dict("sys.modules", {"openai": fake_module}):
            model = EmbeddingModelFactory().create_model(
                ModelType.OPENAI,
                None,
                "test-openai",
                api_key="k",
                api_base="https://api.example.com/v1",
                embedding_dim=8,
            )

        assert isinstance(model, OpenAIEmbedder)
        _assert_working_embedder(model)
        assert len(constructor_calls) == 1
        assert constructor_calls[0]["api_key"] == "k"
        assert constructor_calls[0]["base_url"] == "https://api.example.com/v1"

    def test_gguf_dispatch(self) -> None:
        factory = EmbeddingModelFactory()

        with pytest.raises(ValueError, match="model_path"):
            factory.create_model(ModelType.GGUF, None, "test-gguf")

        mock_llama = MagicMock()
        mock_llama.return_value.n_embd.return_value = 512
        llama_module = MagicMock()
        llama_module.Llama = mock_llama

        with (
            patch.dict("sys.modules", {"llama_cpp": llama_module}),
            patch("os.cpu_count", return_value=4),
        ):
            model = factory.create_model(ModelType.GGUF, "/model.gguf", "test-gguf")

        assert isinstance(model, LlamaCppEmbedder)
        _assert_working_embedder(model)
        assert model.dimension == 512

    def test_modelscope_dispatch(self) -> None:
        mock_downloader_class = MagicMock()
        mock_downloader_class.return_value.download.return_value = Path("/tmp/model")

        with (
            patch.dict("sys.modules", _sentence_transformers_modules()),
            patch("sif.embedding.embedder.ModelDownloader", mock_downloader_class),
        ):
            model = EmbeddingModelFactory().create_model(ModelType.MODELSCOPE, None, "test-ms")

        assert isinstance(model, ModelScopeEmbedder)
        _assert_working_embedder(model)
        mock_downloader_class.return_value.download.assert_called_once_with("test-ms", force=False)

    def test_unknown_type_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unsupported model type"):
            EmbeddingModelFactory().create_model("nonsense", None, "x")  # type: ignore[arg-type]

    def test_env_var_model_type_openai_dispatches(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SIF_MODEL_TYPE", "openai")
        monkeypatch.setenv("SIF_EMBEDDING_DIM", "8")
        monkeypatch.setenv("SIF_CACHE_EMBEDDINGS", "false")
        for var in ("SIF_MODEL_NAME", "SIF_API_KEY", "SIF_API_BASE"):
            monkeypatch.delenv(var, raising=False)

        settings = Settings()
        assert settings.model_type == "openai"
        assert ModelType(settings.model_type) is ModelType.OPENAI

        fake_module, _constructor_calls = _fake_openai_module()
        with patch.dict("sys.modules", {"openai": fake_module}):
            manager = EmbeddingManager.from_settings(settings)
            manager.load_model()

        assert isinstance(manager._model, OpenAIEmbedder)
        _assert_working_embedder(manager._model)

    def test_advertised_backends_construct_invariant(self) -> None:
        """Companion invariant: no Settings-advertised backend dead-ends at load."""
        factory = EmbeddingModelFactory()

        with patch.dict("sys.modules", _sentence_transformers_modules()):
            st_model = factory.create_model(ModelType.SENTENCE_TRANSFORMERS, None, "inv-st")
        assert isinstance(st_model, SentenceTransformerEmbedder)
        _assert_working_embedder(st_model)

        mock_llama = MagicMock()
        mock_llama.return_value.n_embd.return_value = 512
        llama_module = MagicMock()
        llama_module.Llama = mock_llama
        with (
            patch.dict("sys.modules", {"llama_cpp": llama_module}),
            patch("os.cpu_count", return_value=4),
        ):
            gguf_model = factory.create_model(ModelType.GGUF, "/model.gguf", "inv-gguf")
        assert isinstance(gguf_model, LlamaCppEmbedder)
        _assert_working_embedder(gguf_model)

        fake_module, _constructor_calls = _fake_openai_module()
        with patch.dict("sys.modules", {"openai": fake_module}):
            openai_model = factory.create_model(ModelType.OPENAI, None, "inv-openai")
        assert isinstance(openai_model, OpenAIEmbedder)
        _assert_working_embedder(openai_model)
