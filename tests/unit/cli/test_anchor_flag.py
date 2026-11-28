"""Tests for the ``sif search query --anchor`` flag (Phase 26, ANC-01/ANC-03).

The flag is the CLI entry point of the ANCHOR arm. It is equivalent to the
``anchor:`` prefix (D-03), must inject that prefix exactly once, and the ANCHOR
route must construct zero embedding models (ANC-01). The ``--explain`` cost
metadata and the original-query guarantee for DYM/history live in the second
half of the file (D-12/GEN-03).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from sif.cli.commands.search import query_cmd
from sif.core.models import SearchResult
from sif.search.anchor import AnchorResolver
from tests.unit.cli.test_search import _query_settings_mock


def _settings(**overrides: object) -> MagicMock:
    """Anchor-ready settings mock (explicit whitelist + anchor defaults)."""
    return _query_settings_mock(embedding_dim=384, default_search_type="hybrid", **overrides)


def _result() -> SearchResult:
    """One scored result so the zero-result DYM path stays out of scope."""
    return SearchResult(
        document_id="doc-1",
        rank=1,
        score=0.5,
        title="T",
        path="/notes/t.md",
        collection_name="c",
    )


def _invoke(
    tmp_path: Path,
    args: list[str],
    *,
    settings: object | None = None,
    forbid_model_load: bool = False,
    forbid_reranker: bool = False,
) -> tuple[object, MagicMock, MagicMock, MagicMock, MagicMock]:
    """Invoke ``query_cmd`` with the standard patch scaffold.

    Returns ``(result, pipeline, pipeline_cls, create_reranker, from_settings)``
    so each test can assert on the exact construction site it cares about.
    ``forbid_model_load`` / ``forbid_reranker`` patch the constructors to raise
    ``AssertionError``, which proves the ANCHOR route never reaches them.
    """
    repo = MagicMock()
    repo.list_enabled.return_value = []
    manager = MagicMock()
    manager.embed_single.return_value = [0.0] * 4
    manager.embed_query.return_value = [0.0] * 4
    manager._model = MagicMock()
    pipeline = MagicMock()
    pipeline.search.return_value = [_result()]
    pipeline.last_anchor_resolution = None
    index = tmp_path / "index.db"
    index.touch()

    from_settings = MagicMock(return_value=manager)
    if forbid_model_load:
        from_settings = MagicMock(
            side_effect=AssertionError("embedder must not load on anchor route")
        )
    create_reranker = MagicMock(return_value=MagicMock(name="reranker"))
    if forbid_reranker:
        create_reranker = MagicMock(side_effect=AssertionError("reranker must not be constructed"))

    with (
        patch("sif.cli.commands.search.Database", return_value=MagicMock()),
        patch("sif.cli.commands.search.CollectionRepository", return_value=repo),
        patch("sif.cli.commands.search.SearchPipeline", return_value=pipeline) as pipeline_cls,
        patch("sif.embedding.manager.EmbeddingManager.from_settings", new=from_settings),
        patch("sif.config.settings.get_settings", return_value=settings or _settings()),
        patch("sif.search.rerank.create_reranker", new=create_reranker),
    ):
        result = CliRunner().invoke(query_cmd, args, obj={"index_path": index})
    return result, pipeline, pipeline_cls, create_reranker, from_settings


class TestAnchorFlagRouting:
    """D-02/D-03: flag == prefix, single route, single injection."""

    def test_anchor_flag_injects_the_prefix(self, tmp_path: Path) -> None:
        result, pipeline, *_ = _invoke(tmp_path, ["q", "--anchor"], forbid_model_load=True)

        assert result.exit_code == 0, result.output
        assert pipeline.search.call_args.args[0] == "anchor:q"

    def test_without_flag_query_is_verbatim(self, tmp_path: Path) -> None:
        result, pipeline, *_ = _invoke(tmp_path, ["q"])

        assert result.exit_code == 0, result.output
        assert pipeline.search.call_args.args[0] == "q"

    def test_flag_on_prefixed_query_injects_once(self, tmp_path: Path) -> None:
        result, pipeline, *_ = _invoke(tmp_path, ["anchor:q", "--anchor"], forbid_model_load=True)

        assert result.exit_code == 0, result.output
        assert pipeline.search.call_args.args[0] == "anchor:q"

    def test_anchor_route_loads_no_embedder(self, tmp_path: Path) -> None:
        result, pipeline, _, _, from_settings = _invoke(
            tmp_path, ["q", "--anchor"], forbid_model_load=True
        )

        assert result.exit_code == 0, result.output
        from_settings.assert_not_called()
        pipeline.search.assert_called_once()

    def test_anchor_resolver_is_injected(self, tmp_path: Path) -> None:
        result, _, pipeline_cls, *_ = _invoke(tmp_path, ["q", "--anchor"], forbid_model_load=True)

        assert result.exit_code == 0, result.output
        resolver = pipeline_cls.call_args.kwargs["anchor_resolver"]
        assert isinstance(resolver, AnchorResolver)

    def test_non_anchor_route_passes_no_resolver(self, tmp_path: Path) -> None:
        result, _, pipeline_cls, *_ = _invoke(tmp_path, ["q"])

        assert result.exit_code == 0, result.output
        assert pipeline_cls.call_args.kwargs["anchor_resolver"] is None


class TestAnchorRerankRejection:
    """D-01: ANCHOR is a pure BM25 single leg; a reranker is explicitly rejected."""

    @pytest.mark.parametrize("via", ["flag", "setting"])
    def test_anchor_with_rerank_is_rejected_before_construction(
        self, tmp_path: Path, via: str
    ) -> None:
        args = ["q", "--anchor"]
        settings = _settings()
        if via == "flag":
            args.append("--rerank")
        else:
            settings = _settings(rerank_enabled=True)

        result, pipeline, _, create_reranker, from_settings = _invoke(
            tmp_path,
            args,
            settings=settings,
            forbid_model_load=True,
            forbid_reranker=True,
        )

        assert result.exit_code != 0
        assert "--anchor cannot be combined" in result.output
        create_reranker.assert_not_called()
        from_settings.assert_not_called()
        pipeline.search.assert_not_called()

    def test_rerank_alone_still_constructs_reranker(self, tmp_path: Path) -> None:
        result, _, pipeline_cls, create_reranker, _ = _invoke(tmp_path, ["q", "--rerank"])

        assert result.exit_code == 0, result.output
        create_reranker.assert_called_once()
        assert pipeline_cls.call_args.kwargs["reranker"] is create_reranker.return_value
