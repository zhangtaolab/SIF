"""Tests for embedder implementations in sif.embedding.embedder."""

from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from sif.embedding.embedder import (
    LlamaCppEmbedder,
    ModelScopeEmbedder,
    SentenceTransformerEmbedder,
    SimpleEmbedder,
    _pooling_mode,
    create_embedder,
)
from sif.embedding.identity import dimension_mismatch_text


class TestDimensionMismatchWording:
    """D-05/T-21-27: one shared sentence for every dimension disagreement."""

    def test_shared_wording_matches_the_pre_change_openai_sentence(self) -> None:
        assert (
            dimension_mismatch_text(
                "model 'text-embedding-3-small'",
                1536,
                "SIF_EMBEDDING_DIM",
                8,
                "Set SIF_EMBEDDING_DIM to the endpoint model's dimension.",
            )
            == "Embedding dimension mismatch: model 'text-embedding-3-small' produces "
            "1536-dimensional embeddings but SIF_EMBEDDING_DIM is set to 8. "
            "Set SIF_EMBEDDING_DIM to the endpoint model's dimension."
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
        """Test embed returns exact unit vectors unchanged (renormalization is idempotent)."""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([1.0, 0.0, 0.0])
        mock_model.get_sentence_embedding_dimension.return_value = 3

        modules, _mock_st = self._make_modules(mock_model)
        with patch.dict("sys.modules", modules):
            with patch("sif.embedding.embedder.is_quiet", return_value=True):
                with patch("sif.embedding.embedder.suppress_output"):
                    embedder = SentenceTransformerEmbedder()

        result = embedder.embed("hello")
        mock_model.encode.assert_called_once_with("hello", normalize_embeddings=True)
        assert result == [1.0, 0.0, 0.0]

    def test_embed_batch(self) -> None:
        """Test embed_batch encodes multiple texts; unit rows pass through byte-stable."""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[1.0, 0.0], [0.0, 1.0]])
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
        assert result == [[1.0, 0.0], [0.0, 1.0]]

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

    def test_init_forwards_n_gpu_layers(self) -> None:
        """WR-08: n_gpu_layers reaches the Llama constructor instead of being dropped."""
        mock_model = MagicMock()
        mock_model.n_embd.return_value = 512

        modules, mock_llama = self._make_module(mock_model)
        with patch.dict("sys.modules", modules), patch("os.cpu_count", return_value=4):
            LlamaCppEmbedder(model_path="/model.gguf", n_gpu_layers=7)

        call_kwargs = mock_llama.call_args.kwargs
        assert call_kwargs["n_gpu_layers"] == 7

    def test_init_defaults_to_cpu_only(self) -> None:
        """WR-08: without n_gpu_layers the constructor still gets an explicit 0."""
        mock_model = MagicMock()
        mock_model.n_embd.return_value = 512

        modules, mock_llama = self._make_module(mock_model)
        with patch.dict("sys.modules", modules), patch("os.cpu_count", return_value=4):
            LlamaCppEmbedder(model_path="/model.gguf")

        call_kwargs = mock_llama.call_args.kwargs
        assert call_kwargs["n_gpu_layers"] == 0

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

    def test_embed_token_level_shape_mean_pools(self) -> None:
        """G-04-4: token-level (pooling NONE) output mean-pools to a flat unit vector."""
        mock_model = MagicMock()
        mock_model.n_embd.return_value = 2
        mock_model.embed.return_value = [[3.0, 4.0], [6.0, 8.0]]

        modules, _mock_llama = self._make_module(mock_model)
        with patch.dict("sys.modules", modules), patch("os.cpu_count", return_value=4):
            embedder = LlamaCppEmbedder(model_path="/model.gguf")

        result = embedder.embed("hello")
        # Mean of [[3,4],[6,8]] over the token axis is [4.5, 6.0]; norm 7.5 -> [0.6, 0.8].
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(v, float) for v in result)
        assert abs(result[0] - 0.6) < 1e-6
        assert abs(result[1] - 0.8) < 1e-6
        assert abs(math.sqrt(sum(v * v for v in result)) - 1.0) < 1e-6

    def test_embed_wrapped_pooled_shape(self) -> None:
        """G-04-4: a (1, D) wrapped pooled vector unwraps to exactly its single row."""
        mock_model = MagicMock()
        mock_model.n_embd.return_value = 3
        mock_model.embed.return_value = [[3.0, 4.0, 0.0]]

        modules, _mock_llama = self._make_module(mock_model)
        with patch.dict("sys.modules", modules), patch("os.cpu_count", return_value=4):
            embedder = LlamaCppEmbedder(model_path="/model.gguf")

        result = embedder.embed("hello")
        # Mean over a single row is that row exactly; norm 5 -> [0.6, 0.8, 0.0].
        assert len(result) == 3
        assert all(isinstance(v, float) for v in result)
        assert abs(result[0] - 0.6) < 1e-6
        assert abs(result[1] - 0.8) < 1e-6
        assert abs(result[2] - 0.0) < 1e-6

    def test_embed_fully_wrapped_token_level_shape(self) -> None:
        """G-04-4: a fully-wrapped (1, T, D) token payload unwraps and mean-pools."""
        mock_model = MagicMock()
        mock_model.n_embd.return_value = 2
        mock_model.embed.return_value = [[[3.0, 4.0], [6.0, 8.0]]]

        modules, _mock_llama = self._make_module(mock_model)
        with patch.dict("sys.modules", modules), patch("os.cpu_count", return_value=4):
            embedder = LlamaCppEmbedder(model_path="/model.gguf")

        result = embedder.embed("hello")
        # Unwrap to (T, D)=[[3,4],[6,8]], mean [4.5, 6.0], norm 7.5 -> [0.6, 0.8].
        assert len(result) == 2
        assert all(isinstance(v, float) for v in result)
        assert abs(result[0] - 0.6) < 1e-6
        assert abs(result[1] - 0.8) < 1e-6

    def test_embed_call_passthrough_preserved(self) -> None:
        """G-04-4: embed still passes the bare string to model.embed, unchanged."""
        mock_model = MagicMock()
        mock_model.n_embd.return_value = 2
        mock_model.embed.return_value = [[3.0, 4.0], [6.0, 8.0]]

        modules, _mock_llama = self._make_module(mock_model)
        with patch.dict("sys.modules", modules), patch("os.cpu_count", return_value=4):
            embedder = LlamaCppEmbedder(model_path="/model.gguf")

        embedder.embed("hello")
        mock_model.embed.assert_called_once_with("hello")

    def test_embed_empty_payload_raises(self) -> None:
        """G-04-4: an empty payload raises ValueError instead of returning garbage."""
        mock_model = MagicMock()
        mock_model.n_embd.return_value = 3
        mock_model.embed.return_value = []

        modules, _mock_llama = self._make_module(mock_model)
        with patch.dict("sys.modules", modules), patch("os.cpu_count", return_value=4):
            embedder = LlamaCppEmbedder(model_path="/model.gguf")

        with pytest.raises(ValueError, match="empty"):
            embedder.embed("hello")

    def test_embed_empty_vector_payload_raises(self) -> None:
        """G-04-4: a [[]] payload (zero-length vector) raises ValueError."""
        mock_model = MagicMock()
        mock_model.n_embd.return_value = 3
        mock_model.embed.return_value = [[]]

        modules, _mock_llama = self._make_module(mock_model)
        with patch.dict("sys.modules", modules), patch("os.cpu_count", return_value=4):
            embedder = LlamaCppEmbedder(model_path="/model.gguf")

        with pytest.raises(ValueError, match="empty"):
            embedder.embed("hello")

    def test_embed_malformed_3d_payload_raises(self) -> None:
        """G-04-4: outer axis != 1 on a 3-D payload raises ValueError naming the shape."""
        mock_model = MagicMock()
        mock_model.n_embd.return_value = 2
        mock_model.embed.return_value = [[[1.0, 2.0]], [[3.0, 4.0]]]

        modules, _mock_llama = self._make_module(mock_model)
        with patch.dict("sys.modules", modules), patch("os.cpu_count", return_value=4):
            embedder = LlamaCppEmbedder(model_path="/model.gguf")

        with pytest.raises(ValueError, match="single text"):
            embedder.embed("hello")

    def test_embed_batch_rows_are_flat_float_lists(self) -> None:
        """G-04-4: embed_batch rows are flat float lists (persistence-path contract)."""
        mock_model = MagicMock()
        mock_model.n_embd.return_value = 2
        mock_model.embed.side_effect = [
            [[3.0, 4.0], [6.0, 8.0]],
            [[6.0, 8.0], [3.0, 4.0]],
        ]

        modules, _mock_llama = self._make_module(mock_model)
        with patch.dict("sys.modules", modules), patch("os.cpu_count", return_value=4):
            embedder = LlamaCppEmbedder(model_path="/model.gguf")

        rows = embedder.embed_batch(["a", "b"])
        assert len(rows) == 2
        for row in rows:
            assert isinstance(row, list)
            assert all(isinstance(v, float) for v in row)
            assert not any(isinstance(v, list) for v in row)

    def test_create_completion_forwards_prompt_and_kwargs(self) -> None:
        """G-04-3: create_completion forwards prompt positionally with kwargs verbatim."""
        mock_model = MagicMock()
        mock_model.n_embd.return_value = 512

        modules, _mock_llama = self._make_module(mock_model)
        with patch.dict("sys.modules", modules), patch("os.cpu_count", return_value=4):
            embedder = LlamaCppEmbedder(model_path="/model.gguf")

        embedder.create_completion(
            "Answer the question",
            max_tokens=128,
            temperature=0.7,
            stop=["\n\n"],
        )
        mock_model.create_completion.assert_called_once_with(
            "Answer the question",
            max_tokens=128,
            temperature=0.7,
            stop=["\n\n"],
        )

    def test_create_completion_defaults_and_stop_normalization(self) -> None:
        """G-04-3: omitted kwargs default to 256/0.3 and stop=None normalizes to []."""
        mock_model = MagicMock()
        mock_model.n_embd.return_value = 512

        modules, _mock_llama = self._make_module(mock_model)
        with patch.dict("sys.modules", modules), patch("os.cpu_count", return_value=4):
            embedder = LlamaCppEmbedder(model_path="/model.gguf")

        embedder.create_completion("p")
        mock_model.create_completion.assert_called_once_with(
            "p",
            max_tokens=256,
            temperature=0.3,
            stop=[],
        )

    def test_create_completion_returns_openai_style_dict_unchanged(self) -> None:
        """G-04-3: the openai-style completion dict propagates unchanged."""
        mock_model = MagicMock()
        mock_model.n_embd.return_value = 512
        mock_model.create_completion.return_value = {
            "choices": [{"text": "hypothetical doc"}],
            "id": "cmpl-1",
        }

        modules, _mock_llama = self._make_module(mock_model)
        with patch.dict("sys.modules", modules), patch("os.cpu_count", return_value=4):
            embedder = LlamaCppEmbedder(model_path="/model.gguf")

        result = embedder.create_completion("p")
        assert result == {"choices": [{"text": "hypothetical doc"}], "id": "cmpl-1"}
        # Exactly how the HyDE call site in hybrid.py consumes it.
        assert result["choices"][0]["text"].strip() == "hypothetical doc"

    def test_create_completion_satisfies_hyde_capability_gate(self) -> None:
        """G-04-3 regression: hasattr(embedder, 'create_completion') must be True."""
        mock_model = MagicMock()
        mock_model.n_embd.return_value = 512

        modules, _mock_llama = self._make_module(mock_model)
        with patch.dict("sys.modules", modules), patch("os.cpu_count", return_value=4):
            embedder = LlamaCppEmbedder(model_path="/model.gguf")

        # The exact gate SearchPipeline._generate_hypothetical_document checks.
        assert hasattr(embedder, "create_completion") is True


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
        """Test embed delegates to model.encode and returns exact unit vectors unchanged."""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([1.0, 0.0, 0.0])
        mock_model.get_sentence_embedding_dimension.return_value = 3

        modules, mock_downloader_class = self._make_modules(mock_model)
        with patch.dict("sys.modules", modules):
            with patch("sif.embedding.embedder.ModelDownloader", mock_downloader_class):
                with patch("sif.embedding.embedder.is_quiet", return_value=True):
                    with patch("sif.embedding.embedder.suppress_output"):
                        embedder = ModelScopeEmbedder(model_id="test")

        result = embedder.embed("hello")
        mock_model.encode.assert_called_once_with("hello", normalize_embeddings=True)
        assert result == [1.0, 0.0, 0.0]

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


# =============================================================================
# Role-aware prompt plumbing (EMB-02, D-06/D-07)
# =============================================================================


class _RecordingModel:
    """Minimal sentence-transformers double that records every encode call."""

    def __init__(self, dimension: int = 4, prompts: dict[str, str] | None = None) -> None:
        self.prompts = prompts if prompts is not None else {}
        self._dim = dimension
        self.encode_calls: list[tuple[object, dict]] = []
        self.max_seq_length = 32

    def get_sentence_embedding_dimension(self) -> int:
        return self._dim

    def encode(self, texts: object, **kwargs: object) -> np.ndarray:
        self.encode_calls.append((texts, kwargs))
        if isinstance(texts, str):
            return np.array([0.1] * self._dim)
        return np.array([[0.1] * self._dim for _ in texts])


class _IndexableModel(_RecordingModel):
    """ST double exposing the ``model[0].auto_model.config`` revision seam."""

    def __init__(self, commit_hash: str | None = None, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._commit_hash = commit_hash

    def __getitem__(self, index: int) -> object:
        config = SimpleNamespace(_commit_hash=self._commit_hash)
        return SimpleNamespace(auto_model=SimpleNamespace(config=config))


def _st_embedder(model: object, **kwargs: object) -> SentenceTransformerEmbedder:
    """Construct a real ST embedder over a fake sentence-transformers model."""
    st_module = MagicMock()
    st_module.SentenceTransformer.return_value = model
    torch_module = MagicMock()
    torch_module.cuda.is_available.return_value = False
    mps = MagicMock()
    mps.is_available.return_value = False
    torch_module.backends.mps = mps
    modules = {"sentence_transformers": st_module, "torch": torch_module}
    with (
        patch.dict("sys.modules", modules),
        patch("sif.embedding.embedder.is_quiet", return_value=False),
    ):
        return SentenceTransformerEmbedder(**kwargs)


def _modelscope_embedder(model: object, **kwargs: object) -> ModelScopeEmbedder:
    """Construct a real ModelScope embedder over a fake ST model + downloader."""
    st_module = MagicMock()
    st_module.SentenceTransformer.return_value = model
    torch_module = MagicMock()
    torch_module.cuda.is_available.return_value = False
    mps = MagicMock()
    mps.is_available.return_value = False
    torch_module.backends.mps = mps
    downloader = MagicMock()
    downloader.return_value.download.return_value = Path("/tmp/model")
    modules = {"sentence_transformers": st_module, "torch": torch_module}
    with patch.dict("sys.modules", modules):
        with patch("sif.embedding.embedder.ModelDownloader", downloader):
            with patch("sif.embedding.embedder.is_quiet", return_value=False):
                return ModelScopeEmbedder(model_id="test-model", **kwargs)


class _ScaledEmbeddingModel:
    """ST double returning caller-supplied arrays for single and batch inputs."""

    def __init__(self, single: np.ndarray, batch: np.ndarray) -> None:
        self.prompts = {"q": "q: ", "d": "d: "}
        self._single = single
        self._batch = batch
        self.max_seq_length = 32

    def get_sentence_embedding_dimension(self) -> int:
        return int(self._single.shape[-1])

    def encode(self, texts: object, **_kwargs: object) -> np.ndarray:
        return self._single if isinstance(texts, str) else self._batch


class TestUnitRenormalization:
    """Issue #4: off-unit encoder output becomes unit length on every encode path."""

    OFF_UNIT_SCALES = (0.9985, 1.0036)

    @staticmethod
    def _scaled_arrays(scale: float) -> tuple[np.ndarray, np.ndarray]:
        base = np.array([0.2, -0.3, 0.7, 0.54])
        unit = base / np.linalg.norm(base)
        return unit * scale, np.stack([unit * scale, -unit * scale])

    @staticmethod
    def _assert_unit(vector: list[float], raw: np.ndarray) -> None:
        values = np.asarray(vector, dtype=np.float64)
        assert abs(float(np.linalg.norm(values)) - 1.0) <= 1e-12
        np.testing.assert_allclose(values, raw / np.linalg.norm(raw), rtol=1e-12, atol=0.0)

    @pytest.mark.parametrize("scale", OFF_UNIT_SCALES)
    @pytest.mark.parametrize(
        "build", [_st_embedder, _modelscope_embedder], ids=["st", "modelscope"]
    )
    def test_every_public_encode_path_returns_unit_norm(self, build, scale) -> None:
        single, batch = self._scaled_arrays(scale)
        embedder = build(
            _ScaledEmbeddingModel(single, batch),
            query_prompt_name="q",
            document_prompt_name="d",
        )

        self._assert_unit(embedder.embed("hello"), single)
        self._assert_unit(embedder.embed_query("hello"), single)

        for path in (embedder.embed_batch, embedder.embed_queries, embedder.embed_documents):
            vectors = path(["alpha", "beta"])
            assert len(vectors) == 2
            for vector, raw in zip(vectors, batch, strict=True):
                self._assert_unit(vector, raw)

    @pytest.mark.parametrize(
        "build", [_st_embedder, _modelscope_embedder], ids=["st", "modelscope"]
    )
    def test_zero_vectors_pass_through_for_validate_batch(self, build) -> None:
        embedder = build(_ScaledEmbeddingModel(np.zeros(4), np.zeros((2, 4))))

        assert embedder.embed("hello") == [0.0, 0.0, 0.0, 0.0]
        assert embedder.embed_batch(["alpha", "beta"]) == [[0.0] * 4, [0.0] * 4]


class TestRoleAwareEmbedding:
    def test_no_prompt_single_keeps_legacy_encode_kwargs(self) -> None:
        model = _RecordingModel()
        embedder = _st_embedder(model)

        embedder.embed("hello")
        embedder.embed_query("hello")

        assert model.encode_calls[0] == ("hello", {"normalize_embeddings": True})
        assert model.encode_calls[1] == ("hello", {"normalize_embeddings": True})

    def test_no_prompt_batch_keeps_legacy_encode_kwargs(self) -> None:
        model = _RecordingModel()
        embedder = _st_embedder(model)
        texts = ["alpha", "beta"]
        expected = (texts, {"normalize_embeddings": True, "show_progress_bar": False})

        embedder.embed_batch(texts)
        embedder.embed_queries(texts)
        embedder.embed_documents(texts)

        assert model.encode_calls == [expected, expected, expected]

    def test_query_prompt_never_leaks_onto_documents(self) -> None:
        model = _RecordingModel(prompts={"web_search_query": "q: ", "document": "d: "})
        embedder = _st_embedder(model, query_prompt_name="web_search_query")

        embedder.embed_queries(["a", "b"])
        embedder.embed_documents(["a", "b"])

        assert model.encode_calls[0][1]["prompt_name"] == "web_search_query"
        assert "prompt_name" not in model.encode_calls[1][1]

    def test_document_prompt_applies_to_document_role(self) -> None:
        model = _RecordingModel(prompts={"document": "d: "})
        embedder = _st_embedder(model, document_prompt_name="document")

        embedder.embed_documents(["a"])

        assert model.encode_calls[0][1]["prompt_name"] == "document"

    def test_prompted_single_never_requests_a_progress_bar(self) -> None:
        model = _RecordingModel(prompts={"q": "q: "})
        embedder = _st_embedder(model, query_prompt_name="q")

        embedder.embed_query("hello")

        assert model.encode_calls[0][1]["show_progress_bar"] is False
        assert model.encode_calls[0][1]["prompt_name"] == "q"

    def test_prompted_batch_preserves_progress_bar_rule(self) -> None:
        model = _RecordingModel(prompts={"q": "q: "})
        embedder = _st_embedder(model, query_prompt_name="q")

        embedder.embed_queries(["text"] * 101)

        assert model.encode_calls[0][1]["show_progress_bar"] is True

    def test_prompt_name_properties(self) -> None:
        embedder = _st_embedder(
            _RecordingModel(prompts={"q": "q: ", "d": "d: "}),
            query_prompt_name="q",
            document_prompt_name="d",
        )
        assert embedder.query_prompt_name == "q"
        assert embedder.document_prompt_name == "d"

    def test_unknown_prompt_raises_with_available_keys(self) -> None:
        model = _RecordingModel(prompts={"passage": "p: ", "query": "q: "})
        with pytest.raises(ValueError, match="available prompt names") as excinfo:
            _st_embedder(model, query_prompt_name="missing")
        message = str(excinfo.value)
        assert "missing" in message
        assert "passage" in message
        assert "query" in message

    def test_model_without_prompts_raises_explicit_message(self) -> None:
        model = _RecordingModel(prompts={})
        with pytest.raises(ValueError, match="exposes no prompts"):
            _st_embedder(model, document_prompt_name="document")

    def test_modelscope_role_methods_use_prompt(self) -> None:
        model = _RecordingModel(prompts={"q": "q: "})
        embedder = _modelscope_embedder(model, query_prompt_name="q")

        embedder.embed_query("hello")
        embedder.embed_documents(["doc"])

        assert model.encode_calls[0][1]["prompt_name"] == "q"
        assert "prompt_name" not in model.encode_calls[1][1]

    def test_modelscope_unknown_prompt_raises(self) -> None:
        model = _RecordingModel(prompts={"q": "q: "})
        with pytest.raises(ValueError, match="missing"):
            _modelscope_embedder(model, query_prompt_name="missing")


class TestPoolingMode:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("lasttoken", "last_token"),
            ("mean", "mean"),
            ("cls", "cls"),
            ("weightedmean", "weightedmean"),
            (("mean", "max"), "mixed:mean+max"),
        ],
    )
    def test_maps_sentence_transformer_pooling_values(self, raw: object, expected: str) -> None:
        module = SimpleNamespace(pooling_mode=raw)
        model = SimpleNamespace(_modules={"0": module})
        assert _pooling_mode(model) == expected

    def test_absent_pooling_module_is_unknown(self) -> None:
        assert _pooling_mode(SimpleNamespace(_modules={})) == "unknown"
        assert _pooling_mode(SimpleNamespace()) == "unknown"
        assert _pooling_mode(MagicMock()) == "unknown"

    def test_embedder_properties_read_the_loaded_model(self) -> None:
        module = SimpleNamespace(pooling_mode="lasttoken")
        model = _IndexableModel(commit_hash="abc123")
        model._modules = {"0": module}  # type: ignore[attr-defined]
        embedder = _st_embedder(model)
        assert embedder.pooling_mode == "last_token"
        assert embedder.revision == "abc123"

    def test_revision_absent_when_model_exposes_none(self) -> None:
        assert _st_embedder(_RecordingModel()).revision is None
        assert _st_embedder(_IndexableModel(commit_hash=None)).revision is None


class TestGgufRevision:
    def _llama_embedder(self, model_path: Path) -> LlamaCppEmbedder:
        mock_llama = MagicMock()
        mock_llama.return_value.n_embd.return_value = 2
        module = MagicMock()
        module.Llama = mock_llama
        with patch.dict("sys.modules", {"llama_cpp": module}):
            with patch("os.cpu_count", return_value=4):
                return LlamaCppEmbedder(model_path=str(model_path))

    def test_revision_hashes_file_once_and_detects_bytes_change(self, tmp_path: Path) -> None:
        model_file = tmp_path / "model.gguf"
        model_file.write_bytes(b"gguf-bytes")
        embedder = self._llama_embedder(model_file)

        first = embedder.revision
        assert first is not None
        assert re.fullmatch(r"sha256:[0-9a-f]{64}", first)
        assert first == f"sha256:{hashlib.sha256(b'gguf-bytes').hexdigest()}"

        model_file.write_bytes(b"swapped-bytes")
        assert embedder.revision == first
        assert self._llama_embedder(model_file).revision != first

    def test_pooling_mode_is_unknown(self, tmp_path: Path) -> None:
        model_file = tmp_path / "model.gguf"
        model_file.write_bytes(b"bytes")
        assert self._llama_embedder(model_file).pooling_mode == "unknown"

    def test_missing_file_has_no_revision(self, tmp_path: Path) -> None:
        embedder = self._llama_embedder(tmp_path / "absent.gguf")
        assert embedder.revision is None
