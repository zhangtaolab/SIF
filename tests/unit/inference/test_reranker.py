"""Tests for result reranker."""

import math
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import torch

from sif.core.models import SearchResult
from sif.search.rerank import (
    CrossEncoderReranker,
    LlamaCppReranker,
    Qwen3Reranker,
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

        fake_llama_cpp = MagicMock()
        with patch.dict("sys.modules", {"llama_cpp": fake_llama_cpp}):
            mock_llama = fake_llama_cpp.Llama
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

        fake_llama_cpp = MagicMock()
        with patch.dict("sys.modules", {"llama_cpp": fake_llama_cpp}):
            mock_llama = fake_llama_cpp.Llama
            mock_model = MagicMock()
            mock_model.embed.return_value = [0.1, 0.2, 0.3]
            mock_llama.return_value = mock_model

            results = reranker.rerank("query", sample_search_results, top_k=10)

        assert isinstance(results, list)
        assert len(results) <= 10

    def test_rerank_limits_top_k(self, sample_search_results: list[SearchResult]):
        """Test that rerank respects top_k limit."""
        reranker = LlamaCppReranker(model_path="/path/to/model.gguf")

        fake_llama_cpp = MagicMock()
        with patch.dict("sys.modules", {"llama_cpp": fake_llama_cpp}):
            mock_llama = fake_llama_cpp.Llama
            mock_model = MagicMock()
            mock_model.embed.return_value = [0.1, 0.2, 0.3]
            mock_llama.return_value = mock_model

            results = reranker.rerank("query", sample_search_results, top_k=3)

        assert len(results) <= 3

    def test_rerank_preserves_result_type(self, sample_search_results: list[SearchResult]):
        """Test that rerank returns SearchResult objects."""
        reranker = LlamaCppReranker(model_path="/path/to/model.gguf")

        fake_llama_cpp = MagicMock()
        with patch.dict("sys.modules", {"llama_cpp": fake_llama_cpp}):
            mock_llama = fake_llama_cpp.Llama
            mock_model = MagicMock()
            mock_model.embed.return_value = [0.1, 0.2, 0.3]
            mock_llama.return_value = mock_model

            results = reranker.rerank("query", sample_search_results, top_k=10)

        assert all(isinstance(r, SearchResult) for r in results)

    def test_rerank_sorts_by_score(self, sample_search_results: list[SearchResult]):
        """Test that rerank sorts results by score."""
        reranker = LlamaCppReranker(model_path="/path/to/model.gguf")

        fake_llama_cpp = MagicMock()
        with patch.dict("sys.modules", {"llama_cpp": fake_llama_cpp}):
            mock_llama = fake_llama_cpp.Llama
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

        fake_llama_cpp = MagicMock()
        with patch.dict("sys.modules", {"llama_cpp": fake_llama_cpp}):
            mock_llama = fake_llama_cpp.Llama
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

        fake_sentence_transformers = MagicMock()
        with patch.dict("sys.modules", {"sentence_transformers": fake_sentence_transformers}):
            mock_ce = fake_sentence_transformers.CrossEncoder
            mock_ce.return_value = MagicMock()
            reranker.load()

        assert reranker._model is not None

    def test_load_local_quiet_and_already_loaded(self, tmp_path: Path) -> None:
        model_dir = tmp_path / "cross-encoder"
        model_dir.mkdir()
        fake_sentence_transformers = MagicMock()
        reranker = CrossEncoderReranker(model_path=str(model_dir), device="cpu")

        with (
            patch.dict("sys.modules", {"sentence_transformers": fake_sentence_transformers}),
            patch("sif.search.rerank.is_quiet", return_value=True),
        ):
            reranker.load()
            reranker.load()

        fake_sentence_transformers.CrossEncoder.assert_called_once_with(
            str(model_dir),
            device="cpu",
            max_length=512,
        )

    def test_load_uses_mocked_download(self, tmp_path: Path) -> None:
        model_dir = tmp_path / "downloaded-cross-encoder"
        model_dir.mkdir()
        (model_dir / "config.json").write_text('{"model_type": "bert"}', encoding="utf-8")
        fake_sentence_transformers = MagicMock()
        downloader = MagicMock()
        downloader.return_value.download.return_value = model_dir
        reranker = CrossEncoderReranker(
            model_name="org/reranker",
            cache_dir=str(tmp_path / "cache"),
        )

        with (
            patch.dict("sys.modules", {"sentence_transformers": fake_sentence_transformers}),
            patch("sif.models.download.ModelDownloader", downloader),
        ):
            reranker.load()

        downloader.assert_called_once_with(str(tmp_path / "cache"))
        fake_sentence_transformers.CrossEncoder.assert_called_once_with(
            str(model_dir),
            device=None,
            max_length=512,
        )

    def test_download_failure_falls_back_to_model_id(self, tmp_path: Path) -> None:
        fake_sentence_transformers = MagicMock()
        downloader = MagicMock()
        downloader.return_value.download.side_effect = OSError("offline")
        reranker = CrossEncoderReranker(
            model_name="org/reranker",
            cache_dir=str(tmp_path / "cache"),
        )

        with (
            patch.dict("sys.modules", {"sentence_transformers": fake_sentence_transformers}),
            patch("sif.models.download.ModelDownloader", downloader),
        ):
            reranker.load()

        fake_sentence_transformers.CrossEncoder.assert_called_once_with(
            "org/reranker",
            device=None,
            max_length=512,
        )

    """Tests for CrossEncoderReranker reranking."""

    def test_rerank_empty_results(self):
        """Test reranking empty results."""
        reranker = CrossEncoderReranker()

        results = reranker.rerank("query", [], top_k=10)

        assert results == []

    def test_rerank_returns_results(self, sample_search_results: list[SearchResult]):
        """CrossEncoder scores are sigmoid-normalized, sorted, and truncated."""
        reranker = CrossEncoderReranker(batch_size=2)

        fake_sentence_transformers = MagicMock()
        with patch.dict("sys.modules", {"sentence_transformers": fake_sentence_transformers}):
            mock_ce = fake_sentence_transformers.CrossEncoder
            mock_model = MagicMock()
            mock_model.predict.return_value = [-1.0, 1.0, 0.0, 2.0, -2.0]
            mock_ce.return_value = mock_model

            results = reranker.rerank("query", sample_search_results, top_k=3)

        assert [result.document_id for result in results] == ["doc-3", "doc-1", "doc-2"]
        assert results[0].scores["reranker_score"] == pytest.approx(1.0 / (1.0 + math.exp(-2.0)))
        pairs = mock_model.predict.call_args.args[0]
        assert pairs[0] == ("query", "Result 0\n\nPreview of result 0...")
        assert mock_model.predict.call_args.kwargs == {"batch_size": 2}

    def test_rerank_limits_top_k(self, sample_search_results: list[SearchResult]):
        """Test that rerank respects top_k limit."""
        reranker = CrossEncoderReranker()

        fake_sentence_transformers = MagicMock()
        with patch.dict("sys.modules", {"sentence_transformers": fake_sentence_transformers}):
            mock_ce = fake_sentence_transformers.CrossEncoder
            mock_model = MagicMock()
            mock_model.predict.return_value = [0.5, 0.3, 0.8, 0.2, 0.9]
            mock_ce.return_value = mock_model

            results = reranker.rerank("query", sample_search_results, top_k=3)

        assert len(results) <= 3

    def test_rerank_adds_reranker_score(self, sample_search_results: list[SearchResult]):
        """Test that rerank adds reranker_score to scores dict."""
        reranker = CrossEncoderReranker()

        fake_sentence_transformers = MagicMock()
        with patch.dict("sys.modules", {"sentence_transformers": fake_sentence_transformers}):
            mock_ce = fake_sentence_transformers.CrossEncoder
            mock_model = MagicMock()
            mock_model.predict.return_value = [0.5, 0.3, 0.8, 0.2, 0.9]
            mock_ce.return_value = mock_model

            results = reranker.rerank("query", sample_search_results, top_k=10)

        assert all("reranker_score" in r.scores for r in results)


# =============================================================================
# Qwen3Reranker Tests
# =============================================================================


class TestQwen3Reranker:
    """Qwen3 loading and scoring use deterministic local ML boundaries."""

    @staticmethod
    def _model_directory(tmp_path: Path) -> Path:
        model_dir = tmp_path / "qwen3-model"
        model_dir.mkdir()
        (model_dir / "config.json").write_text('{"model_type": "qwen3"}', encoding="utf-8")
        return model_dir

    @staticmethod
    def _tokenizer(batch_logits: list[list[float]]) -> MagicMock:
        tokenizer = MagicMock()
        tokenizer.convert_tokens_to_ids.side_effect = lambda token: {"no": 0, "yes": 1}[token]

        def tokenize(batch: list[str], **_kwargs: object) -> dict[str, torch.Tensor]:
            start = tokenizer.current_batch * len(batch)
            tokenizer.active_logits = tokenizer.batch_logits[start : start + len(batch)]
            tokenizer.current_batch += 1
            attention = torch.ones((len(batch), 2), dtype=torch.long)
            return {"input_ids": attention.clone(), "attention_mask": attention}

        tokenizer.side_effect = tokenize
        tokenizer.batch_logits = batch_logits
        tokenizer.active_logits = []
        tokenizer.current_batch = 0
        return tokenizer

    @staticmethod
    def _model(tokenizer: MagicMock) -> MagicMock:
        model = MagicMock()
        model.device = torch.device("cpu")
        model.eval.return_value = model
        model.to.return_value = model

        def predict(**_inputs: torch.Tensor) -> SimpleNamespace:
            logits = torch.zeros((len(tokenizer.active_logits), 2, 2))
            for row, (no_logit, yes_logit) in enumerate(tokenizer.active_logits):
                logits[row, -1, 0] = no_logit
                logits[row, -1, 1] = yes_logit
            return SimpleNamespace(logits=logits)

        model.side_effect = predict
        return model

    def _patch_ml(self, tokenizer: MagicMock, model: MagicMock) -> tuple[MagicMock, MagicMock]:
        transformers = MagicMock()
        transformers.AutoTokenizer.from_pretrained.return_value = tokenizer
        transformers.AutoModelForCausalLM.from_pretrained.return_value = model
        modules = patch.dict("sys.modules", {"transformers": transformers})
        return modules, transformers

    def test_load_to_ranked_results_uses_yes_no_softmax(
        self,
        tmp_path: Path,
        sample_search_results: list[SearchResult],
    ) -> None:
        """Pinned yes/no logits rank actual SearchResult objects and honor top_k."""
        model_dir = self._model_directory(tmp_path)
        tokenizer = self._tokenizer([[2.0, 0.0], [0.0, 2.0]])
        model = self._model(tokenizer)
        modules, _ = self._patch_ml(tokenizer, model)
        reranker = Qwen3Reranker(model_path=str(model_dir), device="cpu")

        with modules:
            reranker.load()
            ranked = reranker.rerank("local search", sample_search_results[:2], top_k=1)

        assert [result.document_id for result in ranked] == ["doc-1"]
        assert ranked[0].scores["reranker_score"] == pytest.approx(
            math.exp(2.0) / (math.exp(2.0) + 1.0),
        )
        assert ranked[0].rank == 1
        assert reranker._token_false_id == 0
        assert reranker._token_true_id == 1

    def test_local_load_cpu_quiet_and_already_loaded(self, tmp_path: Path) -> None:
        """Quiet CPU loading moves the model once and later load calls are no-ops."""
        model_dir = self._model_directory(tmp_path)
        tokenizer = self._tokenizer([])
        model = self._model(tokenizer)
        modules, transformers = self._patch_ml(tokenizer, model)
        reranker = Qwen3Reranker(model_path=str(model_dir), cache_dir=str(tmp_path / "cache"))

        with modules, patch("sif.search.rerank.is_quiet", return_value=True):
            reranker.load()
            reranker.load()

        model.to.assert_called_once_with("cpu")
        transformers.AutoTokenizer.from_pretrained.assert_called_once_with(
            str(model_dir),
            padding_side="left",
        )
        assert (
            transformers.AutoModelForCausalLM.from_pretrained.call_args.kwargs["torch_dtype"]
            == torch.float32
        )

    def test_local_load_nonquiet_explicit_device_ignores_cuda_probe(self, tmp_path: Path) -> None:
        """An explicit device wins even when CUDA is reported available."""
        model_dir = self._model_directory(tmp_path)
        tokenizer = self._tokenizer([])
        model = self._model(tokenizer)
        modules, transformers = self._patch_ml(tokenizer, model)
        reranker = Qwen3Reranker(model_path=str(model_dir), device="mps")

        with modules, patch("torch.cuda.is_available", return_value=True):
            reranker.load()

        model.to.assert_called_once_with("mps")
        assert (
            transformers.AutoModelForCausalLM.from_pretrained.call_args.kwargs["torch_dtype"]
            == torch.bfloat16
        )

    def test_mocked_download_and_automatic_cuda_selection(self, tmp_path: Path) -> None:
        """Remote IDs resolve through the patched downloader into a local model directory."""
        model_dir = self._model_directory(tmp_path)
        tokenizer = self._tokenizer([])
        model = self._model(tokenizer)
        modules, transformers = self._patch_ml(tokenizer, model)
        downloader = MagicMock()
        downloader.return_value.download.return_value = model_dir
        reranker = Qwen3Reranker(model_name="Qwen/Qwen3-Reranker-0.6B")

        with (
            modules,
            patch("sif.models.download.ModelDownloader", downloader),
            patch("torch.cuda.is_available", return_value=True),
        ):
            reranker.load()

        downloader.assert_called_once_with(None)
        downloader.return_value.download.assert_called_once_with("Qwen/Qwen3-Reranker-0.6B")
        model.to.assert_called_once_with("cuda")
        transformers.AutoTokenizer.from_pretrained.assert_called_once_with(
            str(model_dir),
            padding_side="left",
        )

    def test_empty_results_do_not_load_model(self) -> None:
        reranker = Qwen3Reranker()

        with patch.object(reranker, "load") as load:
            assert reranker.rerank("anything", []) == []

        load.assert_not_called()

    def test_format_prompt_default_and_explicit_instruction(self) -> None:
        default = Qwen3Reranker._format_prompt(None, "query", "document")
        explicit = Qwen3Reranker._format_prompt("Rank exact matches", "query", "document")

        assert "Given a web search query" in default
        assert "<Query>: query\n<Document>: document" in default
        assert explicit.startswith("<Instruct>: Rank exact matches")

    def test_content_highlight_title_composition_and_batching(
        self,
        sample_search_results: list[SearchResult],
    ) -> None:
        """The tokenizer receives real composed prompts once per deterministic batch."""
        tokenizer = self._tokenizer([[0.0, 1.0], [0.0, 2.0]])
        model = self._model(tokenizer)
        reranker = Qwen3Reranker(batch_size=1)
        reranker._model = model
        reranker._tokenizer = tokenizer
        reranker._token_true_id = 1
        reranker._token_false_id = 0
        results = sample_search_results[:2]
        results[0].content = None
        results[0].highlights = ["fallback highlight"]
        results[0].title = "Highlight title"
        results[1].content = ""
        results[1].highlights = []
        results[1].title = "Title only"

        ranked = reranker.rerank("query", results)

        assert tokenizer.call_count == 2
        first_prompt = tokenizer.call_args_list[0].args[0][0]
        second_prompt = tokenizer.call_args_list[1].args[0][0]
        assert "<Document>: Highlight title\n\nfallback highlight" in first_prompt
        assert "<Document>: Title only" in second_prompt
        assert [result.document_id for result in ranked] == ["doc-1", "doc-0"]
        assert ranked[0].scores["reranker_score"] > ranked[1].scores["reranker_score"]


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

    @pytest.mark.parametrize("model_name", ["Qwen/Qwen3-Reranker-0.6B", "local_qwen3_reranker"])
    def test_create_reranker_auto_detects_qwen3(self, model_name: str, tmp_path: Path) -> None:
        settings = MagicMock()
        settings.reranker_model_type = "sentence_transformers"
        settings.reranker_model_name = model_name
        settings.reranker_model_path = tmp_path / "model"
        settings.reranker_batch_size = 4
        settings.get_cache_dir.return_value = tmp_path / "cache"

        reranker = create_reranker(settings)

        assert isinstance(reranker, Qwen3Reranker)
        assert reranker._model_path == str(tmp_path / "model")
        assert reranker._batch_size == 4
        assert reranker._cache_dir == str(tmp_path / "cache")

    def test_create_reranker_sentence_transformers_cache_dir(self, tmp_path: Path) -> None:
        settings = MagicMock()
        settings.reranker_model_type = "sentence_transformers"
        settings.reranker_model_name = "cross-encoder"
        settings.reranker_model_path = None
        settings.reranker_batch_size = 8
        settings.get_cache_dir.return_value = tmp_path / "cache"

        reranker = create_reranker(settings)

        assert isinstance(reranker, CrossEncoderReranker)
        assert reranker._cache_dir == str(tmp_path / "cache")

    def test_create_reranker_without_cache_accessor(self) -> None:
        settings = SimpleNamespace(
            reranker_model_type="sentence_transformers",
            reranker_model_name="cross-encoder",
            reranker_model_path=None,
            reranker_batch_size=8,
        )

        reranker = create_reranker(settings)

        assert isinstance(reranker, CrossEncoderReranker)
        assert reranker._cache_dir is None

    @pytest.mark.parametrize(
        ("model_type", "model_name"),
        [
            ("gguf", "model.gguf"),
            ("sentence_transformers", "cross-encoder/ms-marco-MiniLM-L-6-v2"),
            ("sentence_transformers", "Qwen/Qwen3-Reranker-0.6B"),
        ],
    )
    def test_create_reranker_forwards_relative_threshold(
        self,
        model_type: str,
        model_name: str,
    ) -> None:
        """SIF_RERANK_RELATIVE_THRESHOLD reaches every backend constructor (D-11)."""
        settings = MagicMock()
        settings.reranker_model_type = model_type
        settings.reranker_model_name = model_name
        settings.reranker_model_path = None
        settings.reranker_batch_size = 8
        settings.rerank_relative_threshold = 0.7

        reranker = create_reranker(settings)

        assert reranker._relative_threshold == 0.7

    def test_create_reranker_magic_settings_threshold_falls_back_to_zero(self) -> None:
        """A wide-open MagicMock settings object resolves to 0.0, never a MagicMock."""
        settings = MagicMock()
        settings.reranker_model_type = "gguf"
        settings.reranker_model_name = "model.gguf"
        settings.reranker_model_path = None
        settings.reranker_batch_size = 8
        # rerank_relative_threshold stays an auto-MagicMock attribute (Pitfall 10).

        reranker = create_reranker(settings)

        assert isinstance(reranker._relative_threshold, float)
        assert reranker._relative_threshold == 0.0


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

        fake_llama_cpp = MagicMock()
        with patch.dict("sys.modules", {"llama_cpp": fake_llama_cpp}):
            mock_llama = fake_llama_cpp.Llama
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

        fake_llama_cpp = MagicMock()
        with patch.dict("sys.modules", {"llama_cpp": fake_llama_cpp}):
            mock_llama = fake_llama_cpp.Llama
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

        fake_llama_cpp = MagicMock()
        with patch.dict("sys.modules", {"llama_cpp": fake_llama_cpp}):
            mock_llama = fake_llama_cpp.Llama
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

        fake_sentence_transformers = MagicMock()
        with patch.dict("sys.modules", {"sentence_transformers": fake_sentence_transformers}):
            mock_ce = fake_sentence_transformers.CrossEncoder
            mock_model = MagicMock()
            mock_model.predict.return_value = [0.5]
            mock_ce.return_value = mock_model

            results = reranker.rerank("query", results_with_none_content, top_k=10)

        assert len(results) == 1
