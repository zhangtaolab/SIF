"""Tests for embedder implementations in sif.embedding.embedder."""

from __future__ import annotations

import math
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from sif.embedding.embedder import (
    LlamaCppEmbedder,
    ModelScopeEmbedder,
    SentenceTransformerEmbedder,
    SimpleEmbedder,
    create_embedder,
)


# =============================================================================
# SimpleEmbedder Tests
# =============================================================================


class TestSimpleEmbedder:
    """Tests for SimpleEmbedder (hash-based fallback embedder)."""

    def test_init_default_dimension(self) -> None:
        """Test default dimension is 384."""
        embedder = SimpleEmbedder()
        assert embedder.dimension == 384

    def test_init_custom_dimension(self) -> None:
        """Test custom dimension can be set."""
        embedder = SimpleEmbedder(dimension=512)
        assert embedder.dimension == 512

    def test_embed_returns_list_of_floats(self) -> None:
        """Test embed returns a list of floats."""
        embedder = SimpleEmbedder(dimension=128)
        result = embedder.embed("hello world")
        assert isinstance(result, list)
        assert len(result) == 128
        assert all(isinstance(v, float) for v in result)

    def test_embed_deterministic(self) -> None:
        """Test same text produces same embedding."""
        embedder = SimpleEmbedder(dimension=128)
        result1 = embedder.embed("test text")
        result2 = embedder.embed("test text")
        assert result1 == result2

    def test_embed_different_texts(self) -> None:
        """Test different texts produce different embeddings."""
        embedder = SimpleEmbedder(dimension=128)
        result1 = embedder.embed("text one")
        result2 = embedder.embed("text two")
        assert result1 != result2

    def test_embed_normalized(self) -> None:
        """Test embedding is L2-normalized."""
        embedder = SimpleEmbedder(dimension=128)
        result = embedder.embed("any text")
        norm = math.sqrt(sum(v * v for v in result))
        assert abs(norm - 1.0) < 1e-6

    def test_embed_empty_string(self) -> None:
        """Test embedding empty string does not crash."""
        embedder = SimpleEmbedder(dimension=128)
        result = embedder.embed("")
        assert len(result) == 128
        assert all(isinstance(v, float) for v in result)

    def test_embed_batch(self) -> None:
        """Test batch embedding returns correct count."""
        embedder = SimpleEmbedder(dimension=128)
        texts = ["first", "second", "third"]
        results = embedder.embed_batch(texts)
        assert len(results) == 3
        for r in results:
            assert len(r) == 128

    def test_embed_batch_empty(self) -> None:
        """Test batch embedding with empty list."""
        embedder = SimpleEmbedder(dimension=128)
        results = embedder.embed_batch([])
        assert results == []

    def test_embed_batch_consistent_with_single(self) -> None:
        """Test batch results match individual embed calls."""
        embedder = SimpleEmbedder(dimension=128)
        texts = ["alpha", "beta"]
        batch_results = embedder.embed_batch(texts)
        single_results = [embedder.embed(t) for t in texts]
        assert batch_results == single_results

    def test_dimension_property(self) -> None:
        """Test dimension property returns expected value."""
        embedder = SimpleEmbedder(dimension=256)
        assert embedder.dimension == 256

    def test_vocabulary_and_doc_count_initialized(self) -> None:
        """Test internal state is initialized."""
        embedder = SimpleEmbedder()
        assert embedder.vocabulary == {}
        assert embedder._doc_count == 0


# =============================================================================
# Factory Tests
# =============================================================================


class TestCreateEmbedder:
    """Tests for create_embedder factory function."""

    def test_create_simple(self) -> None:
        """Test factory creates SimpleEmbedder."""
        result = create_embedder("simple", dimension=128)
        assert isinstance(result, SimpleEmbedder)
        assert result.dimension == 128

    def test_create_unknown_type_raises(self) -> None:
        """Test factory raises ValueError for unknown type."""
        with pytest.raises(ValueError, match="Unknown embedder type: invalid"):
            create_embedder("invalid")

    def test_create_unknown_type_message(self) -> None:
        """Test error message includes the unknown type."""
        with pytest.raises(ValueError, match="Unknown embedder type: not_a_type"):
            create_embedder("not_a_type")

    def test_create_sentence_transformer(self) -> None:
        """Test factory creates SentenceTransformerEmbedder."""
        mock_st = MagicMock()
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_mps = MagicMock()
        mock_mps.is_available.return_value = False
        mock_torch.backends.mps = mock_mps

        mock_module = MagicMock()
        mock_module.SentenceTransformer = mock_st

        modules = {
            "sentence_transformers": mock_module,
            "torch": mock_torch,
        }
        with patch.dict("sys.modules", modules):
            mock_st.return_value.get_sentence_embedding_dimension.return_value = 384
            result = create_embedder("sentence_transformer", model_name="test")
            assert isinstance(result, SentenceTransformerEmbedder)

    def test_create_llama_cpp(self) -> None:
        """Test factory creates LlamaCppEmbedder."""
        mock_llama = MagicMock()
        mock_llama.return_value.n_embd.return_value = 512

        mock_module = MagicMock()
        mock_module.Llama = mock_llama

        with patch.dict("sys.modules", {"llama_cpp": mock_module}):
            with patch("os.cpu_count", return_value=4):
                result = create_embedder("llama_cpp", model_path="/model.gguf")
                assert isinstance(result, LlamaCppEmbedder)

    def test_create_modelscope(self) -> None:
        """Test factory creates ModelScopeEmbedder."""
        mock_st = MagicMock()
        mock_st.return_value.get_sentence_embedding_dimension.return_value = 768

        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_mps = MagicMock()
        mock_mps.is_available.return_value = False
        mock_torch.backends.mps = mock_mps

        st_module = MagicMock()
        st_module.SentenceTransformer = mock_st

        mock_downloader_class = MagicMock()
        mock_downloader = MagicMock()
        mock_downloader.download.return_value = Path("/tmp/model")
        mock_downloader_class.return_value = mock_downloader

        modules = {
            "sentence_transformers": st_module,
            "torch": mock_torch,
        }
        with patch.dict("sys.modules", modules):
            with patch("sif.embedding.embedder.ModelDownloader", mock_downloader_class):
                result = create_embedder("modelscope", model_id="test-model")
                assert isinstance(result, ModelScopeEmbedder)


# =============================================================================
# SentenceTransformerEmbedder Mocked Tests
# =============================================================================


class TestSentenceTransformerEmbedder:
    """Tests for SentenceTransformerEmbedder with mocked dependencies."""

    def _make_modules(self, mock_st_instance: MagicMock | None = None) -> tuple[dict, MagicMock]:
        """Create mock modules for sentence-transformers and torch."""
        mock_st = MagicMock()
        if mock_st_instance is not None:
            mock_st.return_value = mock_st_instance
        mock_st_instance = mock_st_instance or MagicMock()
        mock_st.return_value = mock_st_instance

        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_mps = MagicMock()
        mock_mps.is_available.return_value = False
        mock_torch.backends.mps = mock_mps

        st_module = MagicMock()
        st_module.SentenceTransformer = mock_st

        modules = {
            "sentence_transformers": st_module,
            "torch": mock_torch,
        }
        return modules, mock_st

    def test_import_error_raises(self) -> None:
        """Test ImportError is raised when sentence_transformers is missing."""
        original_import = __builtins__["__import__"]

        def fail_import(name, *args, **kwargs):
            if name == "sentence_transformers":
                raise ImportError("No module named 'sentence_transformers'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", fail_import), pytest.raises(ImportError):
            SentenceTransformerEmbedder()

    def test_init_loads_model(self) -> None:
        """Test initialization loads model with correct parameters."""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384

        modules, _mock_st = self._make_modules(mock_model)
        with patch.dict("sys.modules", modules):
            with patch("sif.embedding.embedder.is_quiet", return_value=False):
                embedder = SentenceTransformerEmbedder(
                    model_name="all-MiniLM-L6-v2",
                    cache_dir="/tmp/cache",
                )

        assert embedder.model is mock_model
        assert embedder.dimension == 384
        assert embedder.model_name == "all-MiniLM-L6-v2"

    def test_embed_single(self) -> None:
        """Test embed returns normalized embedding."""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([0.1, 0.2, 0.3])
        mock_model.get_sentence_embedding_dimension.return_value = 3

        modules, _mock_st = self._make_modules(mock_model)
        with patch.dict("sys.modules", modules):
            with patch("sif.embedding.embedder.is_quiet", return_value=True):
                with patch("sif.embedding.embedder.suppress_output"):
                    embedder = SentenceTransformerEmbedder()

        result = embedder.embed("hello")
        mock_model.encode.assert_called_once_with("hello", normalize_embeddings=True)
        assert result == [0.1, 0.2, 0.3]

    def test_embed_batch(self) -> None:
        """Test embed_batch encodes multiple texts."""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1, 0.2], [0.3, 0.4]])
        mock_model.get_sentence_embedding_dimension.return_value = 2

        modules, _mock_st = self._make_modules(mock_model)
        with patch.dict("sys.modules", modules):
            with patch("sif.embedding.embedder.is_quiet", return_value=True):
                with patch("sif.embedding.embedder.suppress_output"):
                    embedder = SentenceTransformerEmbedder()

        result = embedder.embed_batch(["hello", "world"])
        mock_model.encode.assert_called_once_with(
            ["hello", "world"],
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        assert result == [[0.1, 0.2], [0.3, 0.4]]

    def test_embed_batch_with_progress_bar(self) -> None:
        """Test embed_batch shows progress bar for large batches."""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1]] * 101)
        mock_model.get_sentence_embedding_dimension.return_value = 1

        modules, _mock_st = self._make_modules(mock_model)
        with patch.dict("sys.modules", modules):
            with patch("sif.embedding.embedder.is_quiet", return_value=True):
                with patch("sif.embedding.embedder.suppress_output"):
                    embedder = SentenceTransformerEmbedder()

        texts = ["text"] * 101
        embedder.embed_batch(texts)
        mock_model.encode.assert_called_once_with(
            texts,
            normalize_embeddings=True,
            show_progress_bar=True,
        )

    def test_device_selection_cpu(self) -> None:
        """Test CPU is selected when no GPU available."""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384

        modules, mock_st = self._make_modules(mock_model)
        with patch.dict("sys.modules", modules):
            with patch("sif.embedding.embedder.is_quiet", return_value=False):
                embedder = SentenceTransformerEmbedder()

        assert embedder.model is mock_model
        call_kwargs = mock_st.call_args.kwargs
        assert call_kwargs["device"] == "cpu"


# =============================================================================
# LlamaCppEmbedder Mocked Tests
# =============================================================================


class TestLlamaCppEmbedder:
    """Tests for LlamaCppEmbedder with mocked dependencies."""

    def _make_module(self, mock_instance: MagicMock | None = None) -> tuple[dict, MagicMock]:
        """Create mock module for llama_cpp."""
        mock_llama = MagicMock()
        if mock_instance is not None:
            mock_llama.return_value = mock_instance

        mock_module = MagicMock()
        mock_module.Llama = mock_llama
        return {"llama_cpp": mock_module}, mock_llama

    def test_import_error_raises(self) -> None:
        """Test ImportError is raised when llama_cpp is missing."""
        original_import = __builtins__["__import__"]

        def fail_import(name, *args, **kwargs):
            if name == "llama_cpp":
                raise ImportError("No module named 'llama_cpp'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", fail_import), pytest.raises(ImportError):
            LlamaCppEmbedder(model_path="/path/to/model.gguf")

    def test_init_loads_model(self) -> None:
        """Test initialization loads model with correct parameters."""
        mock_model = MagicMock()
        mock_model.n_embd.return_value = 4096

        modules, _mock_llama = self._make_module(mock_model)
        with patch.dict("sys.modules", modules), patch("os.cpu_count", return_value=8):
            embedder = LlamaCppEmbedder(
                model_path="/path/to/model.gguf",
                n_ctx=4096,
                verbose=True,
            )

        assert embedder.model is mock_model
        assert embedder.dimension == 4096
        assert embedder.model_path == Path("/path/to/model.gguf")

    def test_init_auto_threads(self) -> None:
        """Test n_threads defaults to CPU count."""
        mock_model = MagicMock()
        mock_model.n_embd.return_value = 512

        modules, mock_llama = self._make_module(mock_model)
        with patch.dict("sys.modules", modules), patch("os.cpu_count", return_value=4):
            LlamaCppEmbedder(model_path="/model.gguf")

        call_kwargs = mock_llama.call_args.kwargs
        assert call_kwargs["n_threads"] == 4

    def test_init_fallback_threads(self) -> None:
        """Test n_threads falls back to 4 when cpu_count is None."""
        mock_model = MagicMock()
        mock_model.n_embd.return_value = 512

        modules, mock_llama = self._make_module(mock_model)
        with patch.dict("sys.modules", modules), patch("os.cpu_count", return_value=None):
            LlamaCppEmbedder(model_path="/model.gguf")

        call_kwargs = mock_llama.call_args.kwargs
        assert call_kwargs["n_threads"] == 4

    def test_embed_single(self) -> None:
        """Test embed normalizes the embedding."""
        mock_model = MagicMock()
        mock_model.n_embd.return_value = 3
        mock_model.embed.return_value = np.array([3.0, 4.0, 0.0])

        modules, _mock_llama = self._make_module(mock_model)
        with patch.dict("sys.modules", modules), patch("os.cpu_count", return_value=4):
            embedder = LlamaCppEmbedder(model_path="/model.gguf")

        result = embedder.embed("hello")
        mock_model.embed.assert_called_once_with("hello")
        # Should be normalized: [3, 4, 0] / 5 = [0.6, 0.8, 0.0]
        assert abs(result[0] - 0.6) < 1e-6
        assert abs(result[1] - 0.8) < 1e-6
        assert abs(result[2] - 0.0) < 1e-6

    def test_embed_zero_norm(self) -> None:
        """Test embed handles zero norm gracefully."""
        mock_model = MagicMock()
        mock_model.n_embd.return_value = 3
        mock_model.embed.return_value = np.array([0.0, 0.0, 0.0])

        modules, _mock_llama = self._make_module(mock_model)
        with patch.dict("sys.modules", modules), patch("os.cpu_count", return_value=4):
            embedder = LlamaCppEmbedder(model_path="/model.gguf")

        result = embedder.embed("hello")
        assert result == [0.0, 0.0, 0.0]

    def test_embed_batch(self) -> None:
        """Test embed_batch processes each text individually."""
        mock_model = MagicMock()
        mock_model.n_embd.return_value = 2
        mock_model.embed.side_effect = [
            np.array([1.0, 0.0]),
            np.array([0.0, 1.0]),
        ]

        modules, _mock_llama = self._make_module(mock_model)
        with patch.dict("sys.modules", modules), patch("os.cpu_count", return_value=4):
            embedder = LlamaCppEmbedder(model_path="/model.gguf")

        result = embedder.embed_batch(["hello", "world"])
        assert len(result) == 2
        assert mock_model.embed.call_count == 2


# =============================================================================
# ModelScopeEmbedder Mocked Tests
# =============================================================================


class TestModelScopeEmbedder:
    """Tests for ModelScopeEmbedder with mocked dependencies."""

    def _make_modules(
        self,
        mock_st_instance: MagicMock | None = None,
    ) -> tuple[dict, MagicMock]:
        """Create mock modules for ModelScopeEmbedder dependencies."""
        mock_st = MagicMock()
        if mock_st_instance is not None:
            mock_st.return_value = mock_st_instance
        mock_st_instance = mock_st_instance or MagicMock()
        mock_st.return_value = mock_st_instance

        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_mps = MagicMock()
        mock_mps.is_available.return_value = False
        mock_torch.backends.mps = mock_mps

        st_module = MagicMock()
        st_module.SentenceTransformer = mock_st

        mock_downloader_class = MagicMock()
        mock_downloader = MagicMock()
        mock_downloader.download.return_value = Path("/tmp/model")
        mock_downloader_class.return_value = mock_downloader

        modules = {
            "sentence_transformers": st_module,
            "torch": mock_torch,
        }
        return modules, mock_downloader_class

    def test_import_error_raises(self) -> None:
        """Test ImportError is raised when sentence_transformers is missing."""
        mock_downloader_class = MagicMock()
        mock_downloader = MagicMock()
        mock_downloader.download.return_value = Path("/tmp/model")
        mock_downloader_class.return_value = mock_downloader

        original_import = __builtins__["__import__"]

        def fail_import(name, *args, **kwargs):
            if name == "sentence_transformers":
                raise ImportError("No module named 'sentence_transformers'")
            return original_import(name, *args, **kwargs)

        with patch("sif.embedding.embedder.ModelDownloader", mock_downloader_class):
            with patch("builtins.__import__", fail_import):
                with pytest.raises(ImportError):
                    ModelScopeEmbedder(model_id="iic/gte_Qwen2-7B-instruct")

    def test_init_downloads_and_loads(self) -> None:
        """Test initialization downloads model and loads with ST."""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 1024

        modules, mock_downloader_class = self._make_modules(mock_model)
        with patch.dict("sys.modules", modules):
            with patch("sif.embedding.embedder.ModelDownloader", mock_downloader_class):
                with patch("sif.embedding.embedder.is_quiet", return_value=False):
                    embedder = ModelScopeEmbedder(
                        model_id="iic/gte_Qwen2-7B-instruct",
                    )

        mock_downloader = mock_downloader_class.return_value
        mock_downloader.download.assert_called_once_with(
            "iic/gte_Qwen2-7B-instruct",
            force=False,
        )
        assert embedder.model is mock_model
        assert embedder.dimension == 1024
        assert embedder.model_id == "iic/gte_Qwen2-7B-instruct"

    def test_embed_single(self) -> None:
        """Test embed delegates to model.encode."""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([0.1, 0.2, 0.3])
        mock_model.get_sentence_embedding_dimension.return_value = 3

        modules, mock_downloader_class = self._make_modules(mock_model)
        with patch.dict("sys.modules", modules):
            with patch("sif.embedding.embedder.ModelDownloader", mock_downloader_class):
                with patch("sif.embedding.embedder.is_quiet", return_value=True):
                    with patch("sif.embedding.embedder.suppress_output"):
                        embedder = ModelScopeEmbedder(model_id="test")

        result = embedder.embed("hello")
        mock_model.encode.assert_called_once_with("hello", normalize_embeddings=True)
        assert result == [0.1, 0.2, 0.3]

    def test_embed_batch(self) -> None:
        """Test embed_batch with progress bar threshold."""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1]] * 50)
        mock_model.get_sentence_embedding_dimension.return_value = 1

        modules, mock_downloader_class = self._make_modules(mock_model)
        with patch.dict("sys.modules", modules):
            with patch("sif.embedding.embedder.ModelDownloader", mock_downloader_class):
                with patch("sif.embedding.embedder.is_quiet", return_value=True):
                    with patch("sif.embedding.embedder.suppress_output"):
                        embedder = ModelScopeEmbedder(model_id="test")

        texts = ["t"] * 50
        embedder.embed_batch(texts)
        mock_model.encode.assert_called_once_with(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

    def test_force_download(self) -> None:
        """Test force_download parameter is passed to downloader."""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 768

        modules, mock_downloader_class = self._make_modules(mock_model)
        with patch.dict("sys.modules", modules):
            with patch("sif.embedding.embedder.ModelDownloader", mock_downloader_class):
                with patch("sif.embedding.embedder.is_quiet", return_value=False):
                    ModelScopeEmbedder(
                        model_id="test-model",
                        force_download=True,
                    )

        mock_downloader = mock_downloader_class.return_value
        mock_downloader.download.assert_called_once_with("test-model", force=True)
