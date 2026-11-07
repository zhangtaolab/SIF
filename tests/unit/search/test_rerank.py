"""Tests for reranker model-dir resolution in the ModelScope download layout (G-04-2)."""

import json
import math
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sif.core.models import SearchResult
from sif.search.rerank import CrossEncoderReranker, LlamaCppReranker, _resolve_model_dir


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
