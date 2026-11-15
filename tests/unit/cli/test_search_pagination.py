"""CORR-03: CLI `--offset` parsing, threading, and global rank rendering.

The searcher is mocked here; real-corpus pagination semantics are covered in
``tests/unit/search/test_bm25.py`` (and the vector/hybrid/integration suites).
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from sif.cli.commands.search import search_cmd
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
