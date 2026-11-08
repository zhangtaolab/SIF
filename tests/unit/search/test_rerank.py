"""Tests for reranker model-dir resolution in the ModelScope download layout (G-04-2)."""

import json
import math
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sif.core.models import SearchResult
from sif.search.rerank import (
    CrossEncoderReranker,
    LlamaCppReranker,
    _resolve_model_dir,
    _sort_and_build_results,
)


class TestModelScopeRootLayout:
    """Real model files at the download root must win over aux subdirs (G-04-2)."""

    def test_root_config_with_model_type_beats_aux_subdir(self, tmp_path: Path) -> None:
        """Qwen3 layout: root config.json has model_type; 1_LogitScore/ does not."""
        (tmp_path / "config.json").write_text(json.dumps({"model_type": "qwen3"}))
        (tmp_path / "model.safetensors").write_text("weights")
        (tmp_path / "tokenizer.json").write_text("{}")
        aux = tmp_path / "1_LogitScore"
        aux.mkdir()
        (aux / "config.json").write_text(
            json.dumps({"true_token_id": 9693, "false_token_id": 2152}),
        )

        assert _resolve_model_dir(tmp_path) == tmp_path

    def test_qualifying_subdir_wins_over_sorted_order(self, tmp_path: Path) -> None:
        """2_Weights qualifies via model_type even though 1_LogitScore sorts first."""
        aux = tmp_path / "1_LogitScore"
        aux.mkdir()
        (aux / "config.json").write_text(
            json.dumps({"true_token_id": 9693, "false_token_id": 2152}),
        )
        weights = tmp_path / "2_Weights"
        weights.mkdir()
        (weights / "config.json").write_text(json.dumps({"model_type": "qwen3"}))

        assert _resolve_model_dir(tmp_path) == weights


class TestWeightsFallback:
    """Without a qualifying config, weights files pick the model directory."""

    def test_root_safetensors_wins_when_no_model_type_config(self, tmp_path: Path) -> None:
        """Root model.safetensors resolves to the root despite the aux subdir."""
        (tmp_path / "model.safetensors").write_text("weights")
        (tmp_path / "1_LogitScore").mkdir()

        assert _resolve_model_dir(tmp_path) == tmp_path

    def test_subdir_weights_when_root_has_none(self, tmp_path: Path) -> None:
        """A subdir holding .bin weights resolves when the root has no weights."""
        (tmp_path / "1_LogitScore").mkdir()
        weights = tmp_path / "2_Weights"
        weights.mkdir()
        (weights / "pytorch_model.bin").write_text("weights")

        assert _resolve_model_dir(tmp_path) == weights


class TestFinalFallback:
    """Resolution never returns None for a genuinely downloaded model."""

    def test_empty_download_dir_resolves_to_root(self, tmp_path: Path) -> None:
        """Even an empty download dir returns the root itself as a Path."""
        result = _resolve_model_dir(tmp_path)

        assert isinstance(result, Path)
        assert result == tmp_path


class TestDefensiveParsing:
    """A corrupt or adversarial config.json must not crash resolution (T-260905k-01)."""

    def test_invalid_json_root_config_does_not_raise(self, tmp_path: Path) -> None:
        """Malformed root config.json is skipped; subdir config with model_type wins."""
        (tmp_path / "config.json").write_text("{ not valid json !!")
        weights = tmp_path / "2_Weights"
        weights.mkdir()
        (weights / "config.json").write_text(json.dumps({"model_type": "qwen3"}))

        assert _resolve_model_dir(tmp_path) == weights

    def test_non_dict_json_root_config_does_not_qualify(self, tmp_path: Path) -> None:
        """A JSON array config parses but is not a dict, so it cannot qualify."""
        (tmp_path / "config.json").write_text("[1, 2, 3]")

        assert _resolve_model_dir(tmp_path) == tmp_path


class TestRerankerBehavior:
    """Scoped ML mocks exercise real content selection and score construction."""

    @staticmethod
    def _result(content: str | None, title: str = "") -> SearchResult:
        return SearchResult(
            document_id="doc-1",
            path="note.md",
            title=title,
            collection_name="notes",
            score=0.5,
            content=content,
            highlights=["highlight text"],
            scores={"bm25_score": 0.5},
        )

    def test_cross_encoder_content_title_and_metadata(self) -> None:
        model = MagicMock()
        model.predict.return_value = [0.0]
        reranker = CrossEncoderReranker()
        reranker._model = model
        source = self._result("body", "heading")

        ranked = reranker.rerank("query", [source])

        assert model.predict.call_args.args[0] == [("query", "heading\n\nbody")]
        assert ranked[0].score == pytest.approx(0.5)
        assert ranked[0].scores == {"bm25_score": 0.5, "reranker_score": 0.5}
        assert ranked[0].content == "body"
        assert source.scores == {"bm25_score": 0.5}

    def test_llama_cpp_empty_content_uses_title_only(self) -> None:
        model = MagicMock()
        model.embed.side_effect = [[1.0, 0.0], [1.0, 0.0]]
        reranker = LlamaCppReranker()
        reranker._model = model
        source = self._result(None, "heading")
        source.highlights = []

        ranked = reranker.rerank("query", [source])

        assert model.embed.call_args_list[1].args[0] == "heading"
        assert ranked[0].scores["reranker_score"] == pytest.approx(
            1.0 / (1.0 + math.exp(-(1.0 / (1.0 + 1e-8)))),
        )


class TestRelativeThreshold:
    """D-11 (Phase 16): keep candidates scoring >= top1 * alpha.

    The threshold applies after the descending stable sort and before the
    top_k truncation, with a raw >= comparison (no epsilon).
    """

    @staticmethod
    def _result(doc_id: str, score: float = 0.1) -> SearchResult:
        return SearchResult(
            document_id=doc_id,
            path=f"/path/to/{doc_id}.md",
            title=doc_id,
            collection_name="notes",
            score=score,
            content=f"content of {doc_id}",
        )

    def test_relative_threshold_retains_exact_half_drops_below(self) -> None:
        """[0.9, 0.45, 0.44] with alpha=0.5 keeps the exact half 0.45, drops 0.44."""
        results = [self._result("low"), self._result("top"), self._result("half")]

        ranked = _sort_and_build_results(results, [0.44, 0.9, 0.45], 10, relative_threshold=0.5)

        assert [r.document_id for r in ranked] == ["top", "half"]
        assert [r.score for r in ranked] == [0.9, 0.45]

    def test_relative_threshold_zero_and_one_boundaries(self) -> None:
        """alpha=0.0 keeps everything; alpha=1.0 keeps only scores equal to top1."""
        results = [self._result("a"), self._result("b"), self._result("c"), self._result("d")]

        zero = _sort_and_build_results(results, [0.5, 0.9, 0.9, 0.1], 10, relative_threshold=0.0)
        one = _sort_and_build_results(results, [0.5, 0.9, 0.9, 0.1], 10, relative_threshold=1.0)

        assert [r.document_id for r in zero] == ["b", "c", "a", "d"]
        assert [r.document_id for r in one] == ["b", "c"]

    def test_relative_threshold_zero_reproduces_default_output(self) -> None:
        """An explicit 0.0 threshold is byte-identical to the default (no filtering)."""
        results = [self._result(f"doc-{i}") for i in range(4)]
        scores = [0.8, 0.2, 0.6, 0.4]

        default_call = _sort_and_build_results(results, scores, 3)
        zero_call = _sort_and_build_results(results, scores, 3, relative_threshold=0.0)

        assert [r.to_dict() for r in zero_call] == [r.to_dict() for r in default_call]

    def test_relative_threshold_filters_before_top_k_truncation(self) -> None:
        """3 survivors with top_k=2 return 2 survivors; the dropped score never returns."""
        results = [self._result(f"doc-{i}") for i in range(4)]
        scores = [0.9, 0.6, 0.5, 0.44]  # cutoff 0.45 -> survivors 0.9, 0.6, 0.5

        capped = _sort_and_build_results(results, scores, 2, relative_threshold=0.5)
        uncapped = _sort_and_build_results(results, scores, 5, relative_threshold=0.5)

        assert [r.document_id for r in capped] == ["doc-0", "doc-1"]
        assert [r.document_id for r in uncapped] == ["doc-0", "doc-1", "doc-2"]

    def test_relative_threshold_end_to_end_cross_encoder(self) -> None:
        """The constructor kwarg reaches the rerank scoring path end-to-end."""
        model = MagicMock()
        model.predict.return_value = [6.0, 0.0, -6.0]  # sigmoid: ~0.9975, 0.5, ~0.0025
        reranker = CrossEncoderReranker(relative_threshold=0.5)
        reranker._model = model
        results = [self._result(f"doc-{i}") for i in range(3)]

        ranked = reranker.rerank("query", results, top_k=10)

        assert reranker._relative_threshold == 0.5
        assert [r.document_id for r in ranked] == ["doc-0", "doc-1"]
        assert all("reranker_score" in r.scores for r in ranked)
