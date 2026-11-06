"""Tests for search CLI commands."""

import csv
import io
import json
import xml.etree.ElementTree as ET
from collections.abc import Generator
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner
from pydantic import ValidationError

from sif.cli.commands.search import (
    _xml_sanitize,
    format_results_md,
    format_results_xml,
    query_cmd,
    search_cmd,
    vsearch_cmd,
)
from sif.config.settings import get_settings
from sif.core.models import Collection, SearchResult
from sif.database.database import Database


class TestSearchFiltering:
    """Tests for search collection filtering."""

    def test_search_respects_include_by_default(self):
        """search_cmd filters to enabled collections without --all."""
        runner = CliRunner()

        enabled_coll = Collection(
            id="coll1",
            name="enabled",
            path="/notes",
            include_by_default=True,
        )

        mock_repo = MagicMock()
        mock_repo.list_enabled.return_value = [enabled_coll]

        mock_searcher = MagicMock()
        mock_searcher.search.return_value = []

        mock_db = MagicMock()

        with (
            patch("sif.cli.commands.search.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.search.CollectionRepository",
                return_value=mock_repo,
            ),
            patch(
                "sif.cli.commands.search.BM25Searcher",
                return_value=mock_searcher,
            ),
        ):
            result = runner.invoke(
                search_cmd,
                ["foo"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        call_args = mock_searcher.search.call_args
        options = call_args[0][1]
        assert options.collection_ids == ["coll1"]

    def test_search_all_bypasses_include_by_default(self):
        """search_cmd bypasses enabled filter when --all is passed."""
        runner = CliRunner()

        mock_repo = MagicMock()

        mock_searcher = MagicMock()
        mock_searcher.search.return_value = []

        mock_db = MagicMock()

        with (
            patch("sif.cli.commands.search.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.search.CollectionRepository",
                return_value=mock_repo,
            ),
            patch(
                "sif.cli.commands.search.BM25Searcher",
                return_value=mock_searcher,
            ),
        ):
            result = runner.invoke(
                search_cmd,
                ["foo", "--all"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        mock_repo.list_enabled.assert_not_called()
        call_args = mock_searcher.search.call_args
        options = call_args[0][1]
        assert options.collection_ids is None

    def test_query_respects_include_by_default(self):
        """query_cmd filters to enabled collections without --all."""
        runner = CliRunner()

        enabled_coll = Collection(
            id="coll1",
            name="enabled",
            path="/notes",
            include_by_default=True,
        )

        mock_repo = MagicMock()
        mock_repo.list_enabled.return_value = [enabled_coll]

        mock_searcher = MagicMock()
        mock_searcher.search.return_value = []

        mock_manager = MagicMock()
        mock_manager.embed_single.return_value = [0.0] * 384
        mock_manager._model = MagicMock()

        mock_db = MagicMock()

        with (
            patch("sif.cli.commands.search.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.search.CollectionRepository",
                return_value=mock_repo,
            ),
            patch(
                "sif.cli.commands.search.SearchPipeline",
                return_value=mock_searcher,
            ),
            patch(
                "sif.embedding.manager.EmbeddingManager.from_settings",
                return_value=mock_manager,
            ),
            patch(
                "sif.config.settings.get_settings",
                return_value=MagicMock(
                    model_name="all-MiniLM-L6-v2",
                    reranker_model_name=None,
                    reranker_model_path=None,
                    model_dump=lambda: {"model_name": "all-MiniLM-L6-v2"},
                ),
            ),
        ):
            result = runner.invoke(
                query_cmd,
                ["foo"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        call_args = mock_searcher.search.call_args
        options = call_args[0][1]
        assert options.collection_ids == ["coll1"]

    def test_vsearch_respects_include_by_default(self):
        """vsearch_cmd filters to enabled collections without --all."""
        runner = CliRunner()

        enabled_coll = Collection(
            id="coll1",
            name="enabled",
            path="/notes",
            include_by_default=True,
        )

        mock_repo = MagicMock()
        mock_repo.list_enabled.return_value = [enabled_coll]

        mock_searcher = MagicMock()
        mock_searcher.search.return_value = []

        mock_manager = MagicMock()
        mock_manager.embed_single.return_value = [0.0] * 384
        mock_manager._model = MagicMock()

        mock_db = MagicMock()

        with (
            patch("sif.database.database.Database", return_value=mock_db),
            patch(
                "sif.database.repositories.CollectionRepository",
                return_value=mock_repo,
            ),
            patch(
                "sif.embedding.manager.EmbeddingManager.from_settings",
                return_value=mock_manager,
            ),
            patch(
                "sif.search.vector.VectorSearcher",
                return_value=mock_searcher,
            ),
            patch(
                "sif.config.settings.get_settings",
                return_value=MagicMock(
                    model_name="all-MiniLM-L6-v2",
                    model_dump=lambda: {"model_name": "all-MiniLM-L6-v2"},
                ),
            ),
        ):
            result = runner.invoke(
                vsearch_cmd,
                ["foo"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        call_args = mock_searcher.search.call_args
        options = call_args[0][1]
        assert options.collection_ids == ["coll1"]


class TestSearchLineNumbers:
    """Tests for --line-numbers flag on search commands."""

    def _make_search_result(self, content="foo\nbar"):
        """Create a mock SearchResult with content."""
        from sif.core.models import SearchResult

        return SearchResult(
            document_id="doc1",
            rank=1,
            score=0.95,
            title="Test Doc",
            path="/notes/test.md",
            collection_name="notes",
            content=content,
            highlights=["foo", "bar"],
        )

    def test_search_line_numbers_table(self):
        """Test search_cmd --line-numbers in table output."""
        runner = CliRunner()

        mock_repo = MagicMock()
        mock_repo.list_enabled.return_value = []

        mock_searcher = MagicMock()
        mock_searcher.search.return_value = [self._make_search_result()]

        mock_db = MagicMock()

        with (
            patch("sif.cli.commands.search.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.search.CollectionRepository",
                return_value=mock_repo,
            ),
            patch(
                "sif.cli.commands.search.BM25Searcher",
                return_value=mock_searcher,
            ),
        ):
            result = runner.invoke(
                search_cmd,
                ["query", "--line-numbers"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        assert "Content" in result.output
        assert "   1: foo" in result.output
        assert "   2: bar" in result.output

    def test_search_line_numbers_json(self):
        """Test search_cmd --line-numbers with JSON output."""
        runner = CliRunner()

        mock_repo = MagicMock()
        mock_repo.list_enabled.return_value = []

        mock_searcher = MagicMock()
        mock_searcher.search.return_value = [self._make_search_result()]

        mock_db = MagicMock()

        with (
            patch("sif.cli.commands.search.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.search.CollectionRepository",
                return_value=mock_repo,
            ),
            patch(
                "sif.cli.commands.search.BM25Searcher",
                return_value=mock_searcher,
            ),
        ):
            result = runner.invoke(
                search_cmd,
                ["query", "--line-numbers", "--json"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        assert '"line_numbers": "1\\n2"' in result.output

    def test_search_line_numbers_csv(self):
        """CR-01 regression: --line-numbers --csv exits 0, one line per result.

        The --line-numbers path feeds dict rows (from SearchResult.to_dict via
        add_line_numbers_to_results) into format_results_csv, which previously
        did bare attribute access and crashed with AttributeError.
        """
        runner = CliRunner()

        mock_repo = MagicMock()
        mock_repo.list_enabled.return_value = []

        mock_searcher = MagicMock()
        mock_searcher.search.return_value = [
            self._make_search_result(),
            self._make_search_result(),
        ]

        mock_db = MagicMock()

        with (
            patch("sif.cli.commands.search.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.search.CollectionRepository",
                return_value=mock_repo,
            ),
            patch(
                "sif.cli.commands.search.BM25Searcher",
                return_value=mock_searcher,
            ),
        ):
            result = runner.invoke(
                search_cmd,
                ["query", "--line-numbers", "--csv"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        lines = result.output.splitlines()
        assert lines[0] == "rank,score,title,path,collection"
        # One line per result: dict rows must render identically to object rows
        assert lines[1:] == ['"1","0.9500","Test Doc","/notes/test.md","notes"'] * 2

    def test_search_line_numbers_md(self):
        """CR-02 regression: --line-numbers --md exits 0.

        The --line-numbers path feeds dict rows (from SearchResult.to_dict via
        add_line_numbers_to_results) into format_results_md, which previously
        did bare attribute access and crashed with AttributeError.
        """
        runner = CliRunner()

        mock_repo = MagicMock()
        mock_repo.list_enabled.return_value = []

        mock_searcher = MagicMock()
        mock_searcher.search.return_value = [self._make_search_result()]

        mock_db = MagicMock()

        with (
            patch("sif.cli.commands.search.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.search.CollectionRepository",
                return_value=mock_repo,
            ),
            patch(
                "sif.cli.commands.search.BM25Searcher",
                return_value=mock_searcher,
            ),
        ):
            result = runner.invoke(
                search_cmd,
                ["query", "--line-numbers", "--md"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        assert "## 1. Test Doc" in result.output
        assert "- **Score:** 0.9500" in result.output
        assert "- **Path:** `/notes/test.md`" in result.output
        assert "- **Collection:** notes" in result.output

    def test_search_line_numbers_xml(self):
        """CR-02 regression: --line-numbers --xml exits 0.

        The --line-numbers path feeds dict rows (from SearchResult.to_dict via
        add_line_numbers_to_results) into format_results_xml, which previously
        did bare attribute access and crashed with AttributeError.
        """
        runner = CliRunner()

        mock_repo = MagicMock()
        mock_repo.list_enabled.return_value = []

        mock_searcher = MagicMock()
        mock_searcher.search.return_value = [self._make_search_result()]

        mock_db = MagicMock()

        with (
            patch("sif.cli.commands.search.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.search.CollectionRepository",
                return_value=mock_repo,
            ),
            patch(
                "sif.cli.commands.search.BM25Searcher",
                return_value=mock_searcher,
            ),
        ):
            result = runner.invoke(
                search_cmd,
                ["query", "--line-numbers", "--xml"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        assert '  <result rank="1" score="0.9500">' in result.output
        assert "<title>Test Doc</title>" in result.output
        assert "<path>/notes/test.md</path>" in result.output
        assert "<collection>notes</collection>" in result.output

    def test_query_line_numbers_flag(self):
        """Test query_cmd --line-numbers in table output."""
        runner = CliRunner()

        mock_repo = MagicMock()
        mock_repo.list_enabled.return_value = []

        mock_searcher = MagicMock()
        mock_searcher.search.return_value = [self._make_search_result()]

        mock_manager = MagicMock()
        mock_manager.embed_single.return_value = [0.0] * 384
        mock_manager._model = MagicMock()

        mock_db = MagicMock()

        with (
            patch("sif.cli.commands.search.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.search.CollectionRepository",
                return_value=mock_repo,
            ),
            patch(
                "sif.cli.commands.search.SearchPipeline",
                return_value=mock_searcher,
            ),
            patch(
                "sif.embedding.manager.EmbeddingManager.from_settings",
                return_value=mock_manager,
            ),
            patch(
                "sif.config.settings.get_settings",
                return_value=MagicMock(
                    model_name="all-MiniLM-L6-v2",
                    reranker_model_name=None,
                    reranker_model_path=None,
                    model_dump=lambda: {"model_name": "all-MiniLM-L6-v2"},
                ),
            ),
        ):
            result = runner.invoke(
                query_cmd,
                ["query", "--line-numbers"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        assert "Content" in result.output
        assert "   1: foo" in result.output

    def test_vsearch_line_numbers_flag(self):
        """Test vsearch_cmd --line-numbers with JSON output."""
        runner = CliRunner()

        mock_repo = MagicMock()
        mock_repo.list_enabled.return_value = []

        mock_searcher = MagicMock()
        mock_searcher.search.return_value = [self._make_search_result()]

        mock_manager = MagicMock()
        mock_manager.embed_single.return_value = [0.0] * 384
        mock_manager._model = MagicMock()

        mock_db = MagicMock()

        with (
            patch("sif.database.database.Database", return_value=mock_db),
            patch(
                "sif.database.repositories.CollectionRepository",
                return_value=mock_repo,
            ),
            patch(
                "sif.embedding.manager.EmbeddingManager.from_settings",
                return_value=mock_manager,
            ),
            patch(
                "sif.search.vector.VectorSearcher",
                return_value=mock_searcher,
            ),
            patch(
                "sif.config.settings.get_settings",
                return_value=MagicMock(
                    model_name="all-MiniLM-L6-v2",
                    model_dump=lambda: {"model_name": "all-MiniLM-L6-v2"},
                ),
            ),
        ):
            result = runner.invoke(
                vsearch_cmd,
                ["query", "--line-numbers", "--json"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        assert '"line_numbers": "1\\n2"' in result.output


class TestQueryNewFlags:
    """Tests for new query_cmd flags: --explain, --candidate-limit, --intent."""

    def _make_pipeline_mock(self):
        """Create a mock SearchPipeline with a scored result."""
        from sif.core.models import SearchResult

        result = SearchResult(
            document_id="doc1",
            rank=1,
            score=0.95,
            title="Test Doc",
            path="/notes/test.md",
            collection_name="notes",
            content="test content",
            scores={"bm25_score": 0.95, "vector_score": 0.92, "rrf_score": 0.033},
        )

        mock_pipeline = MagicMock()
        mock_pipeline.search.return_value = [result]
        return mock_pipeline

    def test_query_with_explain(self):
        """Test query_cmd --explain shows score breakdowns."""
        runner = CliRunner()

        mock_repo = MagicMock()
        mock_repo.list_enabled.return_value = []

        mock_manager = MagicMock()
        mock_manager.embed_single.return_value = [0.0] * 384
        mock_manager._model = MagicMock()

        mock_db = MagicMock()

        with (
            patch("sif.cli.commands.search.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.search.CollectionRepository",
                return_value=mock_repo,
            ),
            patch(
                "sif.cli.commands.search.SearchPipeline",
                return_value=self._make_pipeline_mock(),
            ),
            patch(
                "sif.embedding.manager.EmbeddingManager.from_settings",
                return_value=mock_manager,
            ),
            patch(
                "sif.config.settings.get_settings",
                return_value=MagicMock(
                    model_name="all-MiniLM-L6-v2",
                    reranker_model_name=None,
                    reranker_model_path=None,
                    model_dump=lambda: {"model_name": "all-MiniLM-L6-v2"},
                ),
            ),
        ):
            result = runner.invoke(
                query_cmd,
                ["query", "--explain"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        assert "bm25_score=" in result.output

    def test_query_with_candidate_limit(self):
        """Test query_cmd -C is passed to SearchOptions."""
        runner = CliRunner()

        mock_repo = MagicMock()
        mock_repo.list_enabled.return_value = []

        mock_manager = MagicMock()
        mock_manager.embed_single.return_value = [0.0] * 384
        mock_manager._model = MagicMock()

        mock_db = MagicMock()

        mock_pipeline = self._make_pipeline_mock()

        with (
            patch("sif.cli.commands.search.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.search.CollectionRepository",
                return_value=mock_repo,
            ),
            patch(
                "sif.cli.commands.search.SearchPipeline",
                return_value=mock_pipeline,
            ),
            patch(
                "sif.embedding.manager.EmbeddingManager.from_settings",
                return_value=mock_manager,
            ),
            patch(
                "sif.config.settings.get_settings",
                return_value=MagicMock(
                    model_name="all-MiniLM-L6-v2",
                    reranker_model_name=None,
                    reranker_model_path=None,
                    model_dump=lambda: {"model_name": "all-MiniLM-L6-v2"},
                ),
            ),
        ):
            result = runner.invoke(
                query_cmd,
                ["query", "-C", "50"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        call_args = mock_pipeline.search.call_args
        options = call_args[0][1]
        assert options.candidate_limit == 50

    def test_query_with_intent(self):
        """Test query_cmd --intent is passed to SearchOptions."""
        runner = CliRunner()

        mock_repo = MagicMock()
        mock_repo.list_enabled.return_value = []

        mock_manager = MagicMock()
        mock_manager.embed_single.return_value = [0.0] * 384
        mock_manager._model = MagicMock()

        mock_db = MagicMock()

        mock_pipeline = self._make_pipeline_mock()

        with (
            patch("sif.cli.commands.search.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.search.CollectionRepository",
                return_value=mock_repo,
            ),
            patch(
                "sif.cli.commands.search.SearchPipeline",
                return_value=mock_pipeline,
            ),
            patch(
                "sif.embedding.manager.EmbeddingManager.from_settings",
                return_value=mock_manager,
            ),
            patch(
                "sif.config.settings.get_settings",
                return_value=MagicMock(
                    model_name="all-MiniLM-L6-v2",
                    reranker_model_name=None,
                    reranker_model_path=None,
                    model_dump=lambda: {"model_name": "all-MiniLM-L6-v2"},
                ),
            ),
        ):
            result = runner.invoke(
                query_cmd,
                ["query", "--intent", "code"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        call_args = mock_pipeline.search.call_args
        options = call_args[0][1]
        assert options.intent == "code"

    def test_query_candidate_limit_out_of_range(self):
        """Test query_cmd -C outside 1-200 is rejected."""
        runner = CliRunner()

        result = runner.invoke(
            query_cmd,
            ["query", "-C", "0"],
            obj={"index_path": MagicMock(exists=lambda: True)},
        )

        assert result.exit_code != 0
        assert "Invalid value" in result.output or "range" in result.output.lower()


class TestVsearchNewFlags:
    """Tests for new vsearch_cmd flags: --min-score, --full."""

    def test_vsearch_with_min_score(self):
        """Test vsearch_cmd --min-score filters results."""
        runner = CliRunner()

        mock_repo = MagicMock()
        mock_repo.list_enabled.return_value = []

        mock_searcher = MagicMock()
        mock_searcher.search.return_value = []

        mock_manager = MagicMock()
        mock_manager.embed_single.return_value = [0.0] * 384
        mock_manager._model = MagicMock()

        mock_db = MagicMock()

        with (
            patch("sif.database.database.Database", return_value=mock_db),
            patch(
                "sif.database.repositories.CollectionRepository",
                return_value=mock_repo,
            ),
            patch(
                "sif.embedding.manager.EmbeddingManager.from_settings",
                return_value=mock_manager,
            ),
            patch(
                "sif.search.vector.VectorSearcher",
                return_value=mock_searcher,
            ),
            patch(
                "sif.config.settings.get_settings",
                return_value=MagicMock(
                    model_name="all-MiniLM-L6-v2",
                    model_dump=lambda: {"model_name": "all-MiniLM-L6-v2"},
                ),
            ),
        ):
            result = runner.invoke(
                vsearch_cmd,
                ["query", "--min-score", "0.5"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        call_args = mock_searcher.search.call_args
        options = call_args[0][1]
        assert options.min_score == 0.5

    def test_vsearch_with_full(self):
        """Test vsearch_cmd --full includes content."""
        runner = CliRunner()

        mock_repo = MagicMock()
        mock_repo.list_enabled.return_value = []

        mock_searcher = MagicMock()
        mock_searcher.search.return_value = []

        mock_manager = MagicMock()
        mock_manager.embed_single.return_value = [0.0] * 384
        mock_manager._model = MagicMock()

        mock_db = MagicMock()

        with (
            patch("sif.database.database.Database", return_value=mock_db),
            patch(
                "sif.database.repositories.CollectionRepository",
                return_value=mock_repo,
            ),
            patch(
                "sif.embedding.manager.EmbeddingManager.from_settings",
                return_value=mock_manager,
            ),
            patch(
                "sif.search.vector.VectorSearcher",
                return_value=mock_searcher,
            ),
            patch(
                "sif.config.settings.get_settings",
                return_value=MagicMock(
                    model_name="all-MiniLM-L6-v2",
                    model_dump=lambda: {"model_name": "all-MiniLM-L6-v2"},
                ),
            ),
        ):
            result = runner.invoke(
                vsearch_cmd,
                ["query", "--full"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        call_args = mock_searcher.search.call_args
        options = call_args[0][1]
        assert options.include_content is True


class TestSnippetDisplay:
    """Tests for Snippet column rendering in query/search rich tables (SRCH-07)."""

    def _make_result(self, **overrides):
        """Create a SearchResult with snippet/highlights overrides."""
        from sif.core.models import SearchResult

        fields = {
            "document_id": "doc1",
            "rank": 1,
            "score": 0.95,
            "title": "Test Doc",
            "path": "/notes/test.md",
            "collection_name": "notes",
        }
        fields.update(overrides)
        return SearchResult(**fields)

    def _invoke_query(self, mock_pipeline, args=None):
        """Invoke query_cmd with the standard patch scaffold; return CliRunner result."""
        runner = CliRunner()
        if args is None:
            args = ["query"]

        mock_repo = MagicMock()
        mock_repo.list_enabled.return_value = []

        mock_manager = MagicMock()
        mock_manager.embed_single.return_value = [0.0] * 384
        mock_manager._model = MagicMock()

        mock_db = MagicMock()

        with (
            patch("sif.cli.commands.search.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.search.CollectionRepository",
                return_value=mock_repo,
            ),
            patch(
                "sif.cli.commands.search.SearchPipeline",
                return_value=mock_pipeline,
            ),
            patch(
                "sif.embedding.manager.EmbeddingManager.from_settings",
                return_value=mock_manager,
            ),
            patch(
                "sif.config.settings.get_settings",
                return_value=MagicMock(
                    model_name="all-MiniLM-L6-v2",
                    reranker_model_name=None,
                    reranker_model_path=None,
                    model_dump=lambda: {"model_name": "all-MiniLM-L6-v2"},
                ),
            ),
        ):
            return runner.invoke(
                query_cmd,
                args,
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

    def test_query_table_shows_snippet_column(self):
        """Default query_cmd table renders the Snippet header and snippet text."""
        mock_pipeline = MagicMock()
        mock_pipeline.search.return_value = [
            self._make_result(snippet="unique snippet marker text"),
        ]

        result = self._invoke_query(mock_pipeline)

        assert result.exit_code == 0
        assert "Snippet" in result.output
        assert "unique snippet marker text" in result.output

    def test_query_table_falls_back_to_first_highlight(self):
        """With no snippet, the Snippet column shows the first highlight only."""
        mock_pipeline = MagicMock()
        mock_pipeline.search.return_value = [
            self._make_result(highlights=["first highlight text", "second highlight"]),
        ]

        result = self._invoke_query(mock_pipeline)

        assert result.exit_code == 0
        assert "first highlight text" in result.output
        assert "second highlight" not in result.output

    def test_search_table_shows_snippet_column(self):
        """search_cmd (BM25) table renders the Snippet header with highlight fallback."""
        runner = CliRunner()

        mock_repo = MagicMock()
        mock_repo.list_enabled.return_value = []

        mock_searcher = MagicMock()
        mock_searcher.search.return_value = [
            self._make_result(highlights=["bm25 highlight marker"]),
        ]

        mock_db = MagicMock()

        with (
            patch("sif.cli.commands.search.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.search.CollectionRepository",
                return_value=mock_repo,
            ),
            patch(
                "sif.cli.commands.search.BM25Searcher",
                return_value=mock_searcher,
            ),
        ):
            result = runner.invoke(
                search_cmd,
                ["query"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        assert "Snippet" in result.output
        assert "bm25 highlight marker" in result.output

    def test_query_files_output_has_no_table_headers(self):
        """--files prints paths only, keeping the path-only branch shape."""
        mock_pipeline = MagicMock()
        mock_pipeline.search.return_value = [
            self._make_result(path="/notes/decorators.md"),
        ]

        result = self._invoke_query(mock_pipeline, args=["query", "--files"])

        assert result.exit_code == 0
        assert "/notes/decorators.md" in result.output
        assert "Score" not in result.output


class TestQueryPipelineErrorHandling:
    """Tests for pipeline.search error surfacing in query_cmd (G-04-2)."""

    def _invoke_query(self, mock_pipeline):
        """Invoke query_cmd with the standard patch scaffold; return CliRunner result."""
        runner = CliRunner()

        mock_repo = MagicMock()
        mock_repo.list_enabled.return_value = []

        mock_manager = MagicMock()
        mock_manager.embed_single.return_value = [0.0] * 384
        mock_manager._model = MagicMock()

        mock_db = MagicMock()

        with (
            patch("sif.cli.commands.search.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.search.CollectionRepository",
                return_value=mock_repo,
            ),
            patch(
                "sif.cli.commands.search.SearchPipeline",
                return_value=mock_pipeline,
            ),
            patch(
                "sif.embedding.manager.EmbeddingManager.from_settings",
                return_value=mock_manager,
            ),
            patch(
                "sif.config.settings.get_settings",
                return_value=MagicMock(
                    model_name="all-MiniLM-L6-v2",
                    reranker_model_name=None,
                    reranker_model_path=None,
                    model_dump=lambda: {"model_name": "all-MiniLM-L6-v2"},
                ),
            ),
        ):
            return runner.invoke(
                query_cmd,
                ["query"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

    def test_pipeline_runtime_error_becomes_click_exception(self):
        """A reranker RuntimeError renders as a one-line Error with exit code 1."""
        mock_pipeline = MagicMock()
        mock_pipeline.search.side_effect = RuntimeError("Reranking failed: boom")

        result = self._invoke_query(mock_pipeline)

        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "Reranking failed" in result.output
        assert not isinstance(result.exception, RuntimeError)

    def test_other_exceptions_propagate_uncaught(self):
        """Only RuntimeError is wrapped — a ValueError still escapes the CLI."""
        mock_pipeline = MagicMock()
        mock_pipeline.search.side_effect = ValueError("unexpected value")

        result = self._invoke_query(mock_pipeline)

        assert isinstance(result.exception, ValueError)


class TestQueryRerankerConfigError:
    """WR-09: invalid reranker config surfaces as a clean ClickException."""

    def _scaffold_patches(self):
        """Standard query_cmd patch scaffold: DB, repo, pipeline, embedder."""
        mock_repo = MagicMock()
        mock_repo.list_enabled.return_value = []
        mock_manager = MagicMock()
        mock_manager.embed_single.return_value = [0.0] * 384
        mock_manager._model = MagicMock()
        mock_db = MagicMock()
        return [
            patch("sif.cli.commands.search.Database", return_value=mock_db),
            patch("sif.cli.commands.search.CollectionRepository", return_value=mock_repo),
            patch("sif.cli.commands.search.SearchPipeline", return_value=MagicMock()),
            patch(
                "sif.embedding.manager.EmbeddingManager.from_settings",
                return_value=mock_manager,
            ),
        ]

    def test_env_invalid_reranker_type_clean_error(self, monkeypatch) -> None:
        """Real get_settings + bad env renders a one-line error, no traceback.

        The env var must reach an uncached Settings() call: cache_clear after
        setenv, and again in finally (lru_cache does not cache raising calls,
        so no poisoned entry persists).
        """
        runner = CliRunner()
        monkeypatch.setenv("SIF_RERANKER_MODEL_TYPE", "cross-encoder")
        get_settings.cache_clear()
        try:
            with ExitStack() as stack:
                for p in self._scaffold_patches():
                    stack.enter_context(p)
                result = runner.invoke(
                    query_cmd,
                    ["query"],
                    obj={"index_path": MagicMock(exists=lambda: True)},
                )
        finally:
            get_settings.cache_clear()

        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "reranker_model_type" in result.output
        assert "Traceback" not in result.output

    def test_vsearch_env_invalid_reranker_type_clean_error(self, monkeypatch) -> None:
        """vsearch_cmd: same bad env renders a one-line error, no traceback.

        vsearch_cmd calls get_settings() itself (the group default never runs
        with an explicit --index), so it needs its own ValidationError guard.
        get_settings() raises before any embedding/DB work, so no scaffolding
        patches are needed.
        """
        runner = CliRunner()
        monkeypatch.setenv("SIF_RERANKER_MODEL_TYPE", "cross-encoder")
        get_settings.cache_clear()
        try:
            result = runner.invoke(
                vsearch_cmd,
                ["query"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )
        finally:
            get_settings.cache_clear()

        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "reranker_model_type" in result.output
        assert "Traceback" not in result.output

    def test_factory_value_error_becomes_click_exception(self):
        """Defense in depth: a create_reranker ValueError renders as a clean error."""
        runner = CliRunner()
        mock_settings = MagicMock(
            model_name="all-MiniLM-L6-v2",
            reranker_model_name="q-reranker",
            reranker_model_path=None,
        )
        # create_reranker is imported inside query_cmd's body, so patch the
        # module attribute — the function-local import resolves it at call time.
        with ExitStack() as stack:
            for p in self._scaffold_patches():
                stack.enter_context(p)
            stack.enter_context(
                patch("sif.config.settings.get_settings", return_value=mock_settings)
            )
            stack.enter_context(
                patch(
                    "sif.search.rerank.create_reranker",
                    side_effect=ValueError("Unknown reranker model_type: cross-encoder"),
                )
            )
            result = runner.invoke(
                query_cmd,
                ["query"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "Unknown reranker model_type" in result.output
        assert not isinstance(result.exception, ValueError)


class TestMachineOutputNoWrap:
    """Machine-format output must be byte-faithful regardless of width (CLI-JSON-WRAP).

    Rich console.print word-wraps at the terminal width and inserts REAL newline
    characters inside JSON string values, and interprets Rich markup, so bracket
    sequences in document text can be swallowed. Machine formats are consumed by
    scripts/agents/jq and must strict-parse under any COLUMNS width.
    """

    # 120 chars with spaces so Rich word-wrapping bites pre-fix
    LONG_TEXT = "lorem ipsum " * 10
    # 145-char path with spaces, like macOS "Application Support" paths
    LONG_PATH = "/Users/forrest/notes archive/" * 5 + "deeply nested doc.md"

    def _make_result(self, **overrides):
        """Create a SearchResult with field overrides."""
        from sif.core.models import SearchResult

        fields = {
            "document_id": "doc1",
            "rank": 1,
            "score": 0.95,
            "title": "Test Doc",
            "path": "/notes/test.md",
            "collection_name": "notes",
        }
        fields.update(overrides)
        return SearchResult(**fields)

    def _invoke_query(self, mock_pipeline, args):
        """Invoke query_cmd with the standard patch scaffold; return CliRunner result."""
        runner = CliRunner()

        mock_repo = MagicMock()
        mock_repo.list_enabled.return_value = []

        mock_manager = MagicMock()
        mock_manager.embed_single.return_value = [0.0] * 384
        mock_manager._model = MagicMock()

        mock_db = MagicMock()

        with (
            patch("sif.cli.commands.search.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.search.CollectionRepository",
                return_value=mock_repo,
            ),
            patch(
                "sif.cli.commands.search.SearchPipeline",
                return_value=mock_pipeline,
            ),
            patch(
                "sif.embedding.manager.EmbeddingManager.from_settings",
                return_value=mock_manager,
            ),
            patch(
                "sif.config.settings.get_settings",
                return_value=MagicMock(
                    model_name="all-MiniLM-L6-v2",
                    reranker_model_name=None,
                    reranker_model_path=None,
                    model_dump=lambda: {"model_name": "all-MiniLM-L6-v2"},
                ),
            ),
        ):
            return runner.invoke(
                query_cmd,
                args,
                env={"COLUMNS": "80"},
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

    def test_search_json_parses_at_narrow_width(self):
        """search_cmd --json strict-parses even when a highlight exceeds the width."""
        runner = CliRunner()
        highlight = self.LONG_TEXT

        mock_repo = MagicMock()
        mock_repo.list_enabled.return_value = []

        mock_searcher = MagicMock()
        mock_searcher.search.return_value = [self._make_result(highlights=[highlight])]

        mock_db = MagicMock()

        with (
            patch("sif.cli.commands.search.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.search.CollectionRepository",
                return_value=mock_repo,
            ),
            patch(
                "sif.cli.commands.search.BM25Searcher",
                return_value=mock_searcher,
            ),
        ):
            result = runner.invoke(
                search_cmd,
                ["query", "--json"],
                env={"COLUMNS": "80"},
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data[0]["highlights"][0] == highlight

    def test_query_json_parses_at_narrow_width(self):
        """query_cmd --json strict-parses and round-trips a long snippet value."""
        snippet = self.LONG_TEXT

        mock_pipeline = MagicMock()
        mock_pipeline.search.return_value = [self._make_result(snippet=snippet)]

        result = self._invoke_query(mock_pipeline, ["query", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data[0]["snippet"] == snippet

    def test_search_files_long_path_single_line(self):
        """search_cmd --files emits each path as one unbroken line."""
        runner = CliRunner()
        long_path = self.LONG_PATH

        mock_repo = MagicMock()
        mock_repo.list_enabled.return_value = []

        mock_searcher = MagicMock()
        mock_searcher.search.return_value = [self._make_result(path=long_path)]

        mock_db = MagicMock()

        with (
            patch("sif.cli.commands.search.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.search.CollectionRepository",
                return_value=mock_repo,
            ),
            patch(
                "sif.cli.commands.search.BM25Searcher",
                return_value=mock_searcher,
            ),
        ):
            result = runner.invoke(
                search_cmd,
                ["query", "--files"],
                env={"COLUMNS": "80"},
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        lines = result.output.splitlines()
        assert long_path in lines

    def test_search_csv_rows_single_line(self):
        """search_cmd --csv keeps every result row on exactly one line."""
        runner = CliRunner()
        long_title = " ".join(["document title that keeps going and going"] * 3)
        long_path = self.LONG_PATH

        mock_repo = MagicMock()
        mock_repo.list_enabled.return_value = []

        mock_searcher = MagicMock()
        mock_searcher.search.return_value = [self._make_result(title=long_title, path=long_path)]

        mock_db = MagicMock()

        with (
            patch("sif.cli.commands.search.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.search.CollectionRepository",
                return_value=mock_repo,
            ),
            patch(
                "sif.cli.commands.search.BM25Searcher",
                return_value=mock_searcher,
            ),
        ):
            result = runner.invoke(
                search_cmd,
                ["query", "--csv"],
                env={"COLUMNS": "80"},
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        lines = result.output.splitlines()
        assert lines[0] == "rank,score,title,path,collection"
        assert lines[1:] == [f'"1","0.9500","{long_title}","{long_path}","notes"']


class TestSearchOutputBranches:
    """Output formats, diagnostics, and clean errors use isolated temp indexes."""

    @pytest.fixture(autouse=True)
    def isolate_quiet_state(self):
        """Do not leak the CLI's process-global quiet mode between tests."""
        from sif.utils.logging import set_quiet

        set_quiet(False)
        yield
        set_quiet(False)

    @staticmethod
    def _result(**overrides: object) -> SearchResult:
        fields = {
            "document_id": "doc-1",
            "rank": 1,
            "score": 0.5,
            "title": "知识 <笔记> & notes",
            "path": "/notes/知识 & more.md",
            "collection_name": "研究 & notes",
            "content": "第一行\nsecond line",
            "highlights": ["匹配 <高亮>"],
            "snippet": "中文检索摘要",
            "scores": {
                "bm25_score": 2.5,
                "vector_score": 0.75,
                "rrf_score": 0.033,
                "reranker_score": 0.5,
                "unused": None,
            },
        }
        fields.update(overrides)
        return SearchResult(**fields)

    @staticmethod
    def _index(tmp_path: Path) -> Path:
        index = tmp_path / "index.db"
        index.touch()
        return index

    def _invoke_bm25(
        self,
        tmp_path: Path,
        args: list[str],
        results: list[SearchResult] | None = None,
    ) -> tuple[object, MagicMock]:
        searcher = MagicMock()
        searcher.search.return_value = results if results is not None else [self._result()]
        repo = MagicMock()
        repo.list_enabled.return_value = []
        with (
            patch("sif.cli.commands.search.Database", return_value=MagicMock()),
            patch("sif.cli.commands.search.CollectionRepository", return_value=repo),
            patch("sif.cli.commands.search.BM25Searcher", return_value=searcher),
        ):
            result = CliRunner().invoke(
                search_cmd,
                args,
                env={"COLUMNS": "80"},
                obj={"index_path": self._index(tmp_path)},
            )
        return result, searcher

    def _invoke_query(
        self,
        tmp_path: Path,
        args: list[str],
        results: list[SearchResult] | None = None,
        *,
        manager: MagicMock | None = None,
        settings: MagicMock | None = None,
        pipeline: MagicMock | None = None,
        reranker_error: Exception | None = None,
        settings_error: Exception | None = None,
    ) -> tuple[object, MagicMock]:
        repo = MagicMock()
        repo.list_enabled.return_value = []
        manager = manager or MagicMock()
        manager.embed_single.return_value = [0.0] * 4
        manager._model = MagicMock()
        pipeline = pipeline or MagicMock()
        if results is not None:
            pipeline.search.return_value = results
        elif not pipeline.search.side_effect:
            pipeline.search.return_value = [self._result()]
        settings = settings or MagicMock(
            reranker_model_name=None,
            reranker_model_path=None,
        )
        patches = [
            patch("sif.cli.commands.search.Database", return_value=MagicMock()),
            patch("sif.cli.commands.search.CollectionRepository", return_value=repo),
            patch("sif.cli.commands.search.SearchPipeline", return_value=pipeline),
            patch("sif.embedding.manager.EmbeddingManager.from_settings", return_value=manager),
            patch(
                "sif.config.settings.get_settings",
                return_value=settings,
                side_effect=settings_error,
            ),
        ]
        if reranker_error is not None:
            patches.append(patch("sif.search.rerank.create_reranker", side_effect=reranker_error))
        with ExitStack() as stack:
            for patcher in patches:
                stack.enter_context(patcher)
            result = CliRunner().invoke(
                query_cmd,
                args,
                env={"COLUMNS": "80"},
                obj={"index_path": self._index(tmp_path)},
            )
        return result, pipeline

    def _invoke_vsearch(
        self,
        tmp_path: Path,
        args: list[str],
        results: list[SearchResult] | None = None,
        *,
        manager: MagicMock | None = None,
        settings: MagicMock | None = None,
        settings_error: Exception | None = None,
    ) -> tuple[object, MagicMock]:
        searcher = MagicMock()
        searcher.search.return_value = results if results is not None else [self._result()]
        repo = MagicMock()
        repo.list_enabled.return_value = []
        manager = manager or MagicMock()
        manager.embed_single.return_value = [0.0] * 4
        settings = settings or MagicMock()
        with (
            patch("sif.database.database.Database", return_value=MagicMock()),
            patch("sif.database.repositories.CollectionRepository", return_value=repo),
            patch("sif.search.vector.VectorSearcher", return_value=searcher),
            patch("sif.embedding.manager.EmbeddingManager.from_settings", return_value=manager),
            patch(
                "sif.config.settings.get_settings",
                return_value=settings,
                side_effect=settings_error,
            ),
        ):
            result = CliRunner().invoke(
                vsearch_cmd,
                args,
                env={"COLUMNS": "80"},
                obj={"index_path": self._index(tmp_path)},
            )
        return result, searcher

    def test_query_json_cjk_and_score_traces_parse(self, tmp_path: Path) -> None:
        result, pipeline = self._invoke_query(tmp_path, ["知识 检索", "--json"])

        assert result.exit_code == 0
        payload = json.loads(result.output)[0]
        assert payload["title"] == "知识 <笔记> & notes"
        assert payload["scores"]["rrf_score"] == pytest.approx(0.033)
        assert pipeline.search.call_args.args[0] == "知识 检索"

    @pytest.mark.parametrize("command", ["search", "query"])
    def test_csv_escapes_content_fields(self, command: str, tmp_path: Path) -> None:
        if command == "search":
            result, _ = self._invoke_bm25(tmp_path, ["query", "--csv"])
        else:
            result, _ = self._invoke_query(tmp_path, ["query", "--csv"])

        assert result.exit_code == 0
        rows = list(csv.DictReader(io.StringIO(result.output)))
        assert rows == [
            {
                "rank": "1",
                "score": "0.5000",
                "title": "知识 <笔记> & notes",
                "path": "/notes/知识 & more.md",
                "collection": "研究 & notes",
            },
        ]

    @pytest.mark.parametrize("command", ["search", "query"])
    def test_markdown_delimiters_and_query_heading(self, command: str, tmp_path: Path) -> None:
        if command == "search":
            result, _ = self._invoke_bm25(tmp_path, ["知识", "--md"])
        else:
            result, _ = self._invoke_query(tmp_path, ["知识", "--md"])

        assert result.exit_code == 0
        assert result.output.startswith("# Search Results: 知识\n\n## 1. 知识 <笔记> & notes")
        assert "- **Score:** 0.5000" in result.output
        assert "> 匹配 <高亮>" in result.output

    @pytest.mark.parametrize("command", ["search", "query"])
    def test_xml_escapes_markup_sensitive_text(self, command: str, tmp_path: Path) -> None:
        if command == "search":
            result, _ = self._invoke_bm25(tmp_path, ['知识 "检索" & <xml>', "--xml"])
        else:
            result, _ = self._invoke_query(tmp_path, ['知识 "检索" & <xml>', "--xml"])

        assert result.exit_code == 0
        root = ET.fromstring(result.output)
        assert root.attrib["query"] == '知识 "检索" & <xml>'
        assert root.findtext("result/title") == "知识 <笔记> & notes"
        assert root.findtext("result/path") == "/notes/知识 & more.md"
        assert root.findtext("result/collection") == "研究 & notes"

    def test_format_results_xml_strips_forbidden_control_characters(self) -> None:
        row = SimpleNamespace(
            rank=1,
            score=0.5,
            title="ti\x0btle\x00",
            path="/pa\x0cth\x1f",
            collection_name="co\x0bl\x00ection",
            line_numbers="1\x0b2\x003",
        )

        output = format_results_xml([row], "qu\x0bery\x00")

        root = ET.fromstring(output)
        for code_point in ("\x0b", "\x00", "\x1f", "\x0c"):
            assert code_point not in output
        assert root.attrib["query"] == "query"
        assert root.findtext("result/title") == "title"
        assert root.findtext("result/path") == "/path"
        assert root.findtext("result/collection") == "colection"
        assert root.findtext("result/line_numbers") == "123"

    def test_format_results_xml_strips_dict_row_control_characters(self) -> None:
        row = {
            "rank": 2,
            "score": 0.25,
            "title": "dt\x0b",
            "path": "/d\x00",
            "collection_name": "dc\x1f",
            "line_numbers": "4\x0c5",
        }

        output = format_results_xml([row], "q\x0b")

        ET.fromstring(output)
        for code_point in ("\x0b", "\x00", "\x1f", "\x0c"):
            assert code_point not in output

    @pytest.mark.parametrize(
        "forbidden",
        ["\x00", "\x08", "\x0b", "\x0c", "\x0e", "\x1f", "\ufffe", "\uffff", "\ud800"],
    )
    def test_xml_sanitize_removes_forbidden_code_points(self, forbidden: str) -> None:
        assert _xml_sanitize(f"a{forbidden}b") == "ab"

    @pytest.mark.parametrize("legal", ["\x09", "\x0a", "\x0d", "\x7f", "知识检索"])
    def test_xml_sanitize_preserves_legal_code_points(self, legal: str) -> None:
        assert _xml_sanitize(f"a{legal}b") == f"a{legal}b"

    @pytest.mark.parametrize("command", ["search", "query"])
    def test_xml_strips_forbidden_control_characters(self, command: str, tmp_path: Path) -> None:
        row = self._result(
            title="bad\x0btitle\x00",
            path="/notes/bad\x0bpath\x00.md",
            collection_name="co\x0bllection\x00",
        )
        if command == "search":
            result, _ = self._invoke_bm25(tmp_path, ["bad\x0bquery", "--xml"], [row])
        else:
            result, _ = self._invoke_query(tmp_path, ["bad\x0bquery", "--xml"], [row])

        assert result.exit_code == 0
        root = ET.fromstring(result.output)
        assert "\x0b" not in result.output
        assert "\x00" not in result.output
        assert root.attrib["query"] == "badquery"
        assert root.findtext("result/title") == "badtitle"

    @pytest.mark.parametrize("command", ["search", "query"])
    def test_files_output_is_one_path_per_line(self, command: str, tmp_path: Path) -> None:
        if command == "search":
            result, _ = self._invoke_bm25(tmp_path, ["query", "--files"])
        else:
            result, _ = self._invoke_query(tmp_path, ["query", "--files"])

        assert result.exit_code == 0
        assert result.output.splitlines() == ["/notes/知识 & more.md"]

    def test_query_markdown_dict_line_numbers(self) -> None:
        rendered = format_results_md(
            [{"rank": 1, "score": 0.5, "title": "T", "path": "p", "line_numbers": "1\n2"}],
            "query",
        )

        assert "- **Line Numbers:** `1\n2`" in rendered

    def test_query_xml_object_line_numbers(self) -> None:
        row = SimpleNamespace(
            rank=1,
            score=0.5,
            title="T",
            path="p",
            collection_name="c",
            line_numbers="1\n2",
        )

        root = ET.fromstring(format_results_xml([row], "query"))

        assert root.findtext("result/line_numbers") == "1\n2"

    def test_search_explicit_collection_and_min_score_boundary(self, tmp_path: Path) -> None:
        repo = MagicMock()
        repo.get_by_name.side_effect = [Collection(id="c1", name="known", path="notes"), None]
        searcher = MagicMock()
        searcher.search.return_value = []
        with (
            patch("sif.cli.commands.search.Database", return_value=MagicMock()),
            patch("sif.cli.commands.search.CollectionRepository", return_value=repo),
            patch("sif.cli.commands.search.BM25Searcher", return_value=searcher),
        ):
            result = CliRunner().invoke(
                search_cmd,
                ["query", "--collection", "known", "--collection", "missing", "--min-score", "0.5"],
                obj={"index_path": self._index(tmp_path)},
            )

        assert result.exit_code == 0
        options = searcher.search.call_args.args[1]
        assert options.collection_ids == ["c1"]
        assert options.min_score == 0.5

    @pytest.mark.parametrize("command", ["search", "query"])
    def test_explain_and_line_numbers_render_diagnostics(
        self,
        command: str,
        tmp_path: Path,
    ) -> None:
        if command == "search":
            result, _ = self._invoke_bm25(
                tmp_path,
                ["知识", "--explain", "--line-numbers"],
            )
        else:
            result, _ = self._invoke_query(
                tmp_path,
                ["知识", "--explain", "--line-numbers"],
            )

        assert result.exit_code == 0
        assert "Content" in result.output
        assert "1: 第一行" in result.output
        assert "Results: 1" in result.output or "bm25_score=" in result.output
        assert "reranker_score=" in result.output or command == "search"
        assert "unused=" not in result.output

    def test_search_snippet_fallback_and_truncation(self, tmp_path: Path) -> None:
        row = self._result(
            title="A" * 55,
            content="line\n" * 100,
            snippet=None,
            highlights=["x" * 205],
        )

        result, _ = self._invoke_bm25(tmp_path, ["query", "--line-numbers"], [row])

        assert result.exit_code == 0
        assert "A" * 15 in result.output
        assert "A" * 55 not in result.output
        assert "..." in result.output
        assert "Content" in result.output

    def test_empty_query_is_accepted_and_empty_results_are_rendered(self, tmp_path: Path) -> None:
        result, pipeline = self._invoke_query(tmp_path, ["", "--explain"], [])

        assert result.exit_code == 0
        assert pipeline.search.call_args.args[0] == ""
        assert "No results found" in result.output

    def test_quiet_empty_results_emit_nothing(self, tmp_path: Path) -> None:
        result, _ = self._invoke_bm25(tmp_path, ["query", "--quiet"], [])

        assert result.exit_code == 0
        assert result.output == ""

    @pytest.mark.parametrize("command", ["search", "vsearch", "query"])
    def test_missing_index_does_not_open_database(self, command: str, tmp_path: Path) -> None:
        cli_command = {"search": search_cmd, "vsearch": vsearch_cmd, "query": query_cmd}[command]
        with patch("sif.cli.commands.search.Database") as database:
            result = CliRunner().invoke(
                cli_command,
                ["query"],
                obj={"index_path": tmp_path / "missing.db"},
            )

        assert result.exit_code == 0
        assert "No index found" in result.output
        database.assert_not_called()

    @pytest.mark.parametrize("command", ["search", "vsearch", "query"])
    def test_missing_index_quiet_is_silent(self, command: str, tmp_path: Path) -> None:
        cli_command = {"search": search_cmd, "vsearch": vsearch_cmd, "query": query_cmd}[command]

        result = CliRunner().invoke(
            cli_command,
            ["query", "--quiet"],
            obj={"index_path": tmp_path / "missing.db"},
        )

        assert result.exit_code == 0
        assert result.output == ""

    def test_query_explicit_collection_and_model_override(self, tmp_path: Path) -> None:
        settings = MagicMock(reranker_model_name=None, reranker_model_path=None)
        settings.model_copy.return_value = settings
        repo = MagicMock()
        repo.get_by_name.side_effect = [Collection(id="c1", name="known", path="notes"), None]
        pipeline = MagicMock()
        pipeline.search.return_value = []
        manager = MagicMock()
        manager.embed_single.return_value = [0.0] * 4
        with (
            patch("sif.cli.commands.search.Database", return_value=MagicMock()),
            patch("sif.cli.commands.search.CollectionRepository", return_value=repo),
            patch("sif.cli.commands.search.SearchPipeline", return_value=pipeline),
            patch("sif.embedding.manager.EmbeddingManager.from_settings", return_value=manager),
            patch("sif.config.settings.get_settings", return_value=settings),
        ):
            result = CliRunner().invoke(
                query_cmd,
                [
                    "query",
                    "--collection",
                    "known",
                    "--collection",
                    "missing",
                    "--model-type",
                    "openai",
                ],
                obj={"index_path": self._index(tmp_path)},
            )

        assert result.exit_code == 0
        assert pipeline.search.call_args.args[1].collection_ids == ["c1"]
        settings.model_copy.assert_called_once_with(update={"model_type": "openai"})

    def test_query_optional_reranker_import_error_warns(self, tmp_path: Path) -> None:
        settings = MagicMock(reranker_model_name="reranker", reranker_model_path=None)

        result, _ = self._invoke_query(
            tmp_path,
            ["query"],
            [],
            settings=settings,
            reranker_error=ImportError("missing ML extra"),
        )

        assert result.exit_code == 0
        assert "Reranker not available" in result.output

    @pytest.mark.parametrize(
        ("error", "expected"),
        [
            (ImportError("not installed"), "Embedding backend not installed"),
            (RuntimeError("bad weights"), "Failed to load embedding model"),
        ],
    )
    def test_query_embedder_errors_are_clean(
        self,
        error: Exception,
        expected: str,
        tmp_path: Path,
    ) -> None:
        manager = MagicMock()
        manager.load_model.side_effect = error

        result, _ = self._invoke_query(tmp_path, ["query"], manager=manager)

        assert result.exit_code == 1
        assert expected in result.stderr
        assert "Traceback" not in result.output

    @pytest.mark.parametrize(
        ("error", "expected"),
        [
            (ImportError("not installed"), "Embedding backend not installed"),
            (RuntimeError("bad weights"), "Failed to load embedding model"),
        ],
    )
    def test_vsearch_embedder_errors_are_clean(
        self,
        error: Exception,
        expected: str,
        tmp_path: Path,
    ) -> None:
        manager = MagicMock()
        manager.embed_single.side_effect = error

        result, _ = self._invoke_vsearch(tmp_path, ["query"], manager=manager)

        assert result.exit_code == 1
        assert expected in result.stderr
        assert "Traceback" not in result.output

    @pytest.mark.parametrize("command", ["vsearch", "query"])
    def test_settings_validation_errors_are_clean(self, command: str, tmp_path: Path) -> None:
        error = ValidationError.from_exception_data("Settings", [])
        try:
            get_settings.cache_clear()
            if command == "query":
                result, _ = self._invoke_query(tmp_path, ["query"], settings_error=error)
            else:
                result, _ = self._invoke_vsearch(tmp_path, ["query"], settings_error=error)
        finally:
            get_settings.cache_clear()

        assert result.exit_code == 1
        assert "Error:" in result.stderr or "Error:" in result.output
        assert "Traceback" not in result.output

    def test_vsearch_json_collection_model_override_and_boundary(self, tmp_path: Path) -> None:
        settings = MagicMock()
        settings.model_copy.return_value = settings
        repo = MagicMock()
        repo.get_by_name.return_value = Collection(id="c1", name="known", path="notes")
        searcher = MagicMock()
        searcher.search.return_value = [self._result()]
        manager = MagicMock()
        manager.embed_single.return_value = [0.0] * 4
        with (
            patch("sif.database.database.Database", return_value=MagicMock()),
            patch("sif.database.repositories.CollectionRepository", return_value=repo),
            patch("sif.search.vector.VectorSearcher", return_value=searcher),
            patch("sif.embedding.manager.EmbeddingManager.from_settings", return_value=manager),
            patch("sif.config.settings.get_settings", return_value=settings),
        ):
            result = CliRunner().invoke(
                vsearch_cmd,
                [
                    "query",
                    "--collection",
                    "known",
                    "--model-type",
                    "openai",
                    "--min-score",
                    "0.5",
                    "--json",
                ],
                obj={"index_path": self._index(tmp_path)},
            )

        assert result.exit_code == 0
        assert json.loads(result.output)[0]["document_id"] == "doc-1"
        options = searcher.search.call_args.args[1]
        assert options.collection_ids == ["c1"]
        assert options.min_score == 0.5
        settings.model_copy.assert_called_once_with(update={"model_type": "openai"})

    def test_vsearch_quiet_files_and_empty_results(self, tmp_path: Path) -> None:
        result, _ = self._invoke_vsearch(tmp_path, ["query", "--quiet"])

        assert result.exit_code == 0
        assert result.output.splitlines() == ["/notes/知识 & more.md"]

        empty, _ = self._invoke_vsearch(tmp_path, ["query"], [])

        assert empty.exit_code == 0
        assert "No results found" in empty.output

    def test_vsearch_table_line_numbers_and_truncation(self, tmp_path: Path) -> None:
        row = self._result(title="B" * 55, content="line\n" * 100)

        result, _ = self._invoke_vsearch(tmp_path, ["query", "--line-numbers"], [row])

        assert result.exit_code == 0
        assert "Vector Search Results" in result.output
        assert "Content" in result.output
        assert "B" * 34 in result.output
        assert "B" * 55 not in result.output
        assert "..." in result.output

    def test_search_table_renders_markup_literally(self, tmp_path: Path) -> None:
        """CR-01: markup-bearing query/title/collection render literally in the table."""
        row = self._result(title="notes [/3] review", collection_name="[WIP] col")

        result, _ = self._invoke_bm25(tmp_path, ["[/3]-notes"], [row])

        assert result.exit_code == 0
        assert "[/3]" in result.output
        assert "[WIP]" in result.output

    def test_query_table_renders_markup_literally(self, tmp_path: Path) -> None:
        """CR-01: the hybrid query table escapes markup-bearing user data."""
        row = self._result(title="notes [/3] review", collection_name="[WIP] col")

        result, _ = self._invoke_query(tmp_path, ["[/3]-notes"], [row])

        assert result.exit_code == 0
        assert "[/3]" in result.output
        assert "[WIP]" in result.output

    def test_vsearch_table_renders_markup_literally(self, tmp_path: Path) -> None:
        """CR-01: the vector search table escapes markup-bearing user data."""
        row = self._result(title="notes [/3] review", collection_name="[WIP] col")

        result, _ = self._invoke_vsearch(tmp_path, ["[/3]-notes"], [row])

        assert result.exit_code == 0
        assert "[/3]" in result.output
        assert "[WIP]" in result.output

    def test_line_numbers_content_cell_renders_markup_literally(self, tmp_path: Path) -> None:
        """CR-01: the --line-numbers Content cell escapes bracket sequences in content."""
        row = self._result(content="line one\n[/] marker line")

        result, _ = self._invoke_bm25(tmp_path, ["notes", "--line-numbers"], [row])

        assert result.exit_code == 0
        assert "[/]" in result.output

    def test_explain_output_renders_markup_literally(self, tmp_path: Path) -> None:
        """CR-01: --explain prints escape the interpolated query and result titles."""
        row = self._result(title="notes [/3] review")

        result, _ = self._invoke_query(tmp_path, ["[/3]-notes", "--explain"], [row])

        assert result.exit_code == 0
        assert "Query: [/3]-notes" in result.output
        assert "[/3]" in result.output


class TrackingDatabase(Database):
    """Database double recording constructed instances for closure assertions."""

    created: ClassVar[list[Database]] = []

    def __init__(self, db_path: str | Path) -> None:
        """Record each construction so tests can assert every handle closed."""
        super().__init__(db_path)
        TrackingDatabase.created.append(self)


class TestDatabaseClosure:
    """search and query own their Database lifecycle end to end."""

    @pytest.fixture(autouse=True)
    def isolated_settings(self) -> Generator[None, None, None]:
        """Real schema creation never inherits cached Settings."""
        get_settings.cache_clear()
        yield
        get_settings.cache_clear()

    def test_search_closes_database_on_success(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Every Database constructed by search is closed after a successful run."""
        index = tmp_path / "index.db"
        index.touch()
        TrackingDatabase.created.clear()
        monkeypatch.setattr("sif.cli.commands.search.Database", TrackingDatabase)
        searcher = MagicMock()
        searcher.search.return_value = []
        repo = MagicMock()
        repo.list_enabled.return_value = []
        with (
            patch("sif.cli.commands.search.CollectionRepository", return_value=repo),
            patch("sif.cli.commands.search.BM25Searcher", return_value=searcher),
        ):
            result = CliRunner().invoke(search_cmd, ["query"], obj={"index_path": index})

        assert result.exit_code == 0, result.output
        assert TrackingDatabase.created, "search must construct its Database"
        for instance in TrackingDatabase.created:
            assert instance._connection is None

    def test_query_closes_database_on_pipeline_error(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A pipeline failure still closes every Database query constructed."""
        index = tmp_path / "index.db"
        index.touch()
        TrackingDatabase.created.clear()
        monkeypatch.setattr("sif.cli.commands.search.Database", TrackingDatabase)
        pipeline = MagicMock()
        pipeline.search.side_effect = RuntimeError("boom")
        repo = MagicMock()
        repo.list_enabled.return_value = []
        manager = MagicMock()
        manager.embed_single.return_value = [0.0] * 4
        manager._model = MagicMock()
        # embedding_dim must be a real int: init_schema() resolves get_settings
        # lazily per call, so this mock feeds the real SchemaManager's vec0 DDL.
        settings = MagicMock(
            reranker_model_name=None,
            reranker_model_path=None,
            embedding_dim=4,
        )
        with (
            patch("sif.cli.commands.search.CollectionRepository", return_value=repo),
            patch("sif.cli.commands.search.SearchPipeline", return_value=pipeline),
            patch("sif.embedding.manager.EmbeddingManager.from_settings", return_value=manager),
            patch("sif.config.settings.get_settings", return_value=settings),
        ):
            result = CliRunner().invoke(query_cmd, ["query"], obj={"index_path": index})

        assert result.exit_code != 0
        assert "boom" in result.output, result.output
        assert TrackingDatabase.created, "query must construct its Database"
        for instance in TrackingDatabase.created:
            assert instance._connection is None

    def test_vsearch_closes_database_on_success(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Every Database constructed by vsearch is closed after a successful run.

        vsearch_cmd imports Database inside its function body, so the double
        must be installed on sif.database.database (the import source), not
        on the sif.cli.commands.search namespace the other closure tests patch.
        """
        index = tmp_path / "index.db"
        index.touch()
        TrackingDatabase.created.clear()
        monkeypatch.setattr("sif.database.database.Database", TrackingDatabase)
        searcher = MagicMock()
        searcher.search.return_value = []
        repo = MagicMock()
        repo.list_enabled.return_value = []
        manager = MagicMock()
        manager.embed_single.return_value = [0.0] * 4
        # embedding_dim must be a real int (see query closure test note).
        settings = MagicMock(embedding_dim=4)
        with (
            patch("sif.database.repositories.CollectionRepository", return_value=repo),
            patch("sif.search.vector.VectorSearcher", return_value=searcher),
            patch("sif.embedding.manager.EmbeddingManager.from_settings", return_value=manager),
            patch("sif.config.settings.get_settings", return_value=settings),
        ):
            result = CliRunner().invoke(vsearch_cmd, ["query"], obj={"index_path": index})

        assert result.exit_code == 0, result.output
        assert TrackingDatabase.created, "vsearch must construct its Database"
        for instance in TrackingDatabase.created:
            assert instance._connection is None
