"""CORR-03: CLI `--offset` parsing, threading, and global rank rendering.

The searcher is mocked here; real-corpus pagination semantics are covered in
``tests/unit/search/test_bm25.py`` (and the vector/hybrid/integration suites).
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from sif.cli.commands.search import query_cmd, search_cmd, vsearch_cmd
from sif.core.models import SearchResult


def _page_searcher() -> MagicMock:
    """Fake BM25 searcher honoring the offset/limit/global-rank contract.

    The real searcher assigns ``rank = offset + position``; this fake mirrors
    that so option threading and JSON rendering are exercised end to end.
    """
    searcher = MagicMock()

    def _search(_query: str, options) -> list[SearchResult]:
        return [
            SearchResult(
                document_id=f"doc-{options.offset + i + 1}",
                title=f"Doc {options.offset + i + 1}",
                path=f"/doc-{options.offset + i + 1}.md",
                collection_name="notes",
                score=1.0 - (options.offset + i) * 0.01,
                rank=options.offset + i + 1,
            )
            for i in range(options.limit)
        ]

    searcher.search.side_effect = _search
    return searcher


def _invoke(args: list[str]) -> tuple[object, MagicMock]:
    """Invoke search_cmd with the database and searcher mocked out."""
    searcher = _page_searcher()
    with (
        patch("sif.cli.commands.search.Database", return_value=MagicMock()),
        patch("sif.cli.commands.search.CollectionRepository", return_value=MagicMock()),
        patch("sif.cli.commands.search.BM25Searcher", return_value=searcher),
    ):
        result = CliRunner().invoke(
            search_cmd,
            args,
            obj={"index_path": MagicMock(exists=lambda: True)},
        )
    return result, searcher


class TestSearchCommandOffset:
    """`sif search --offset` is a validated, globally numbered page."""

    def test_offset_five_limit_five_json_ranks_six_to_ten(self) -> None:
        """--offset 5 -n 5 threads into SearchOptions and renders ranks 6-10."""
        result, searcher = _invoke(["apple", "--offset", "5", "-n", "5", "--json", "--no-refresh"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert [row["rank"] for row in payload] == [6, 7, 8, 9, 10]
        assert [row["document_id"] for row in payload] == [f"doc-{i}" for i in range(6, 11)]

        options = searcher.search.call_args[0][1]
        assert options.offset == 5
        assert options.limit == 5

    def test_negative_offset_rejected_by_click(self) -> None:
        """--offset -1 is a parse-time error (IntRange(min=0)); the search never runs."""
        result, searcher = _invoke(["apple", "--offset", "-1", "--no-refresh"])

        assert result.exit_code == 2
        assert "Invalid value" in result.output
        searcher.search.assert_not_called()

    def test_default_offset_is_zero(self) -> None:
        """Omitting --offset keeps the pre-change offset-0 behavior."""
        result, searcher = _invoke(["apple", "--json", "--no-refresh"])

        assert result.exit_code == 0, result.output
        assert searcher.search.call_args[0][1].offset == 0


def _settings_mock() -> MagicMock:
    """Settings stub enumerating the fields the query path reads."""
    return MagicMock(
        model_name="all-MiniLM-L6-v2",
        model_dump=lambda: {"model_name": "all-MiniLM-L6-v2"},
        rerank_enabled=False,
        default_search_type="hybrid",
        rrf_k=60,
        bm25_weight=1.0,
        vector_weight=1.0,
        query_history_enabled=False,
    )


class TestVsearchCommandOffset:
    """`sif vsearch --offset` threads into SearchOptions and ranks globally."""

    def test_offset_threads_into_options(self) -> None:
        searcher = _page_searcher()
        manager = MagicMock()
        manager.embed_single.return_value = [0.0] * 8
        with (
            patch("sif.cli.commands.search.Database", return_value=MagicMock()),
            patch(
                "sif.cli.commands.search.CollectionRepository",
                return_value=MagicMock(),
            ),
            patch("sif.search.vector.VectorSearcher", return_value=searcher),
            patch(
                "sif.embedding.manager.EmbeddingManager.from_settings",
                return_value=manager,
            ),
            patch("sif.config.settings.get_settings", return_value=_settings_mock()),
        ):
            result = CliRunner().invoke(
                vsearch_cmd,
                ["apple", "--offset", "5", "-n", "5", "--json", "--no-refresh"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert [row["rank"] for row in payload] == [6, 7, 8, 9, 10]
        options = searcher.search.call_args[0][1]
        assert options.offset == 5
        assert options.limit == 5

    def test_negative_offset_rejected_by_click(self) -> None:
        result = CliRunner().invoke(
            vsearch_cmd,
            ["apple", "--offset", "-1"],
            obj={"index_path": MagicMock(exists=lambda: True)},
        )

        assert result.exit_code == 2
        assert "Invalid value" in result.output


class TestQueryCommandOffset:
    """`sif query --offset` threads into SearchOptions and ranks globally."""

    def test_offset_threads_into_options(self) -> None:
        page = _page_searcher()
        pipeline = MagicMock()
        pipeline.search.side_effect = page.search
        manager = MagicMock()
        manager.embed_single.return_value = [0.0] * 8
        manager.get_model_info.return_value = {"embedding_dim": 8}

        with (
            patch("sif.cli.commands.search.Database", return_value=MagicMock()),
            patch(
                "sif.cli.commands.search.CollectionRepository",
                return_value=MagicMock(),
            ),
            patch("sif.cli.commands.search.SearchPipeline", return_value=pipeline),
            patch(
                "sif.embedding.manager.EmbeddingManager.from_settings",
                return_value=manager,
            ),
            patch("sif.config.settings.get_settings", return_value=_settings_mock()),
        ):
            result = CliRunner().invoke(
                query_cmd,
                ["apple", "--offset", "5", "-n", "5", "--json", "--no-refresh"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert [row["rank"] for row in payload] == [6, 7, 8, 9, 10]
        options = pipeline.search.call_args[0][1]
        assert options.offset == 5
        assert options.limit == 5

    def test_negative_offset_rejected_by_click(self) -> None:
        result = CliRunner().invoke(
            query_cmd,
            ["apple", "--offset", "-1"],
            obj={"index_path": MagicMock(exists=lambda: True)},
        )

        assert result.exit_code == 2
        assert "Invalid value" in result.output


class TestPerChunkPageContinuity:
    """CORR-02/D-01: per-chunk pages count chunk rows and keep global ranks.

    The fake searcher mirrors the real per-chunk contract (ungrouped chunk
    rows, ``chunk_matches`` left at 0, ``rank = offset + position``); the
    real search semantics live in the vector/hybrid/integration suites.
    """

    def _chunk_searcher(self) -> MagicMock:
        searcher = MagicMock()

        def _search(_query: str, options) -> list[SearchResult]:
            return [
                SearchResult(
                    document_id="doc-1",
                    title="Chunky Doc",
                    path="/notes/chunky.md",
                    collection_name="notes",
                    score=0.9 - index * 0.01,
                    rank=options.offset + index + 1,
                    chunk_id=f"chunk-{options.offset + index}",
                    sequence=options.offset + index,
                    chunk_matches=0,
                )
                for index in range(options.limit)
            ]

        searcher.search.side_effect = _search
        return searcher

    def test_per_chunk_page_continuity(self) -> None:
        """--per-chunk --offset 5 -n 5 renders chunk rows with ranks 6-10."""
        searcher = self._chunk_searcher()
        manager = MagicMock()
        manager.embed_single.return_value = [0.0] * 8
        with (
            patch("sif.cli.commands.search.Database", return_value=MagicMock()),
            patch(
                "sif.cli.commands.search.CollectionRepository",
                return_value=MagicMock(),
            ),
            patch("sif.search.vector.VectorSearcher", return_value=searcher),
            patch(
                "sif.embedding.manager.EmbeddingManager.from_settings",
                return_value=manager,
            ),
            patch("sif.config.settings.get_settings", return_value=_settings_mock()),
        ):
            result = CliRunner().invoke(
                vsearch_cmd,
                [
                    "apple",
                    "--per-chunk",
                    "--offset",
                    "5",
                    "-n",
                    "5",
                    "--json",
                    "--no-refresh",
                ],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0, result.output
        options = searcher.search.call_args[0][1]
        assert options.per_chunk is True
        assert options.offset == 5
        assert options.limit == 5
        payload = json.loads(result.output)
        assert [row["rank"] for row in payload] == [6, 7, 8, 9, 10]
        # Page size counts chunk rows, not distinct documents.
        assert len(payload) == 5
        assert [row["chunk_id"] for row in payload] == [f"chunk-{i}" for i in range(5, 10)]
        assert [row["sequence"] for row in payload] == [5, 6, 7, 8, 9]


class TestLimitLowerBound:
    """WR-02: -n/--limit below 1 is a parse error on every search command.

    Pre-fix ``sif search -n -1`` reached ``LIMIT -1`` (SQLite's "no limit")
    and dumped the whole match set, while vsearch/query clamped to one row.
    The shared ``click.IntRange(min=1)`` makes the flag mean one thing.
    """

    @pytest.mark.parametrize("command", [search_cmd, vsearch_cmd, query_cmd])
    @pytest.mark.parametrize("value", ["0", "-1"])
    def test_limit_below_one_is_rejected(self, command, value: str) -> None:
        """0 and negative limits exit 2 before any search work starts."""
        result = CliRunner().invoke(
            command,
            ["apple", "-n", value],
            obj={"index_path": MagicMock(exists=lambda: True)},
        )

        assert result.exit_code == 2, result.output
        assert "Invalid value" in result.output
        assert "not in the range" in result.output
