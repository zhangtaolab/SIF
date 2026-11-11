"""Tests for search CLI commands."""

import csv
import io
import json
import os
import re
import sqlite3
import xml.etree.ElementTree as ET
from collections.abc import Generator
from contextlib import ExitStack
from datetime import datetime, timezone
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
from sif.config.settings import Settings, get_settings
from sif.core.models import Collection, SearchResult
from sif.database.database import Database
from sif.database.repositories import CollectionRepository
from sif.indexing.incremental import IncrementalIndexer


def _query_settings_mock(**overrides: object) -> MagicMock:
    """Explicit settings mock enumerating every field query_cmd reads.

    Pitfall 10 (Phase 16) guard: an unset attribute on a wide-open MagicMock
    is truthy, so a mock without ``rerank_enabled=False`` would silently flip
    the D-12 gate onto the enabled path and construct a reranker. Tests whose
    subject IS the enabled path override ``rerank_enabled=True`` explicitly.
    """
    fields: dict[str, object] = {
        "model_name": "all-MiniLM-L6-v2",
        "reranker_model_name": None,
        "reranker_model_path": None,
        "rerank_enabled": False,
        "rerank_candidate_limit": 20,
        "rerank_relative_threshold": 0.5,
        "model_dump": lambda: {"model_name": "all-MiniLM-L6-v2"},
    }
    fields.update(overrides)
    return MagicMock(**fields)


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
                return_value=_query_settings_mock(),
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
            patch("sif.cli.commands.search.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.search.CollectionRepository",
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
        # One line per result: dict rows must render identically to object rows
        # (vectors_stale column added by 14-03 D-12; False is the field default).
        assert lines[0] == "rank,score,title,path,collection,vectors_stale"
        assert lines[1:] == ['"1","0.9500","Test Doc","/notes/test.md","notes","false"'] * 2

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
        assert '  <result rank="1" score="0.9500" vectors_stale="false">' in result.output
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
                return_value=_query_settings_mock(),
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
            patch("sif.cli.commands.search.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.search.CollectionRepository",
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
                return_value=_query_settings_mock(),
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
                return_value=_query_settings_mock(),
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
                return_value=_query_settings_mock(),
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
            patch("sif.cli.commands.search.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.search.CollectionRepository",
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
            patch("sif.cli.commands.search.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.search.CollectionRepository",
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
                return_value=_query_settings_mock(),
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
                return_value=_query_settings_mock(),
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
        # rerank_enabled=True: with the D-12 default the gate would skip
        # create_reranker entirely and this side_effect would be unreachable.
        mock_settings = _query_settings_mock(
            reranker_model_name="q-reranker",
            rerank_enabled=True,
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


class TestRerankOptIn:
    """D-12 (Phase 16): `sif search query` constructs a reranker only on request.

    The off path must be zero-cost by construction — create_reranker is never
    called, so no model is loaded and no optional backend is imported — and
    SearchPipeline receives reranker=None. --rerank or SIF_RERANK_ENABLED=1
    each open the gate exactly once.
    """

    @staticmethod
    def _result() -> SearchResult:
        return SearchResult(
            document_id="doc-1",
            rank=1,
            score=0.5,
            title="T",
            path="/notes/t.md",
            collection_name="c",
        )

    def _invoke(
        self,
        tmp_path: Path,
        args: list[str],
        settings: object = None,
    ) -> tuple[object, MagicMock, MagicMock]:
        """Invoke query_cmd; return (result, SearchPipeline class, create_reranker)."""
        repo = MagicMock()
        repo.list_enabled.return_value = []
        manager = MagicMock()
        manager.embed_single.return_value = [0.0] * 4
        manager._model = MagicMock()
        pipeline = MagicMock()
        pipeline.search.return_value = [self._result()]
        create_reranker = MagicMock(return_value=MagicMock(name="reranker"))
        index = tmp_path / "index.db"
        index.touch()
        with (
            patch("sif.cli.commands.search.Database", return_value=MagicMock()),
            patch("sif.cli.commands.search.CollectionRepository", return_value=repo),
            patch("sif.cli.commands.search.SearchPipeline", return_value=pipeline) as pipeline_cls,
            patch("sif.embedding.manager.EmbeddingManager.from_settings", return_value=manager),
            patch(
                "sif.config.settings.get_settings",
                return_value=settings if settings is not None else _query_settings_mock(),
            ),
            patch("sif.search.rerank.create_reranker", new=create_reranker),
        ):
            result = CliRunner().invoke(query_cmd, args, obj={"index_path": index})
        return result, pipeline_cls, create_reranker

    def test_off_by_default_constructs_no_reranker(self, tmp_path: Path) -> None:
        """No flag + rerank_enabled=False: create_reranker never runs, pipeline gets None."""
        result, pipeline_cls, create_reranker = self._invoke(tmp_path, ["query"])

        assert result.exit_code == 0, result.output
        create_reranker.assert_not_called()
        assert pipeline_cls.call_args.kwargs["reranker"] is None

    def test_rerank_flag_constructs_reranker_once(self, tmp_path: Path) -> None:
        """--rerank opens the D-12 gate: exactly one construction, wired to the pipeline."""
        settings = _query_settings_mock()
        result, pipeline_cls, create_reranker = self._invoke(
            tmp_path, ["query", "--rerank"], settings=settings
        )

        assert result.exit_code == 0, result.output
        create_reranker.assert_called_once_with(settings)
        assert pipeline_cls.call_args.kwargs["reranker"] is create_reranker.return_value

    def test_enabled_setting_constructs_without_flag(self, tmp_path: Path) -> None:
        """SIF_RERANK_ENABLED surfaced via settings.rerank_enabled: same single call."""
        result, pipeline_cls, create_reranker = self._invoke(
            tmp_path, ["query"], settings=_query_settings_mock(rerank_enabled=True)
        )

        assert result.exit_code == 0, result.output
        create_reranker.assert_called_once()
        assert pipeline_cls.call_args.kwargs["reranker"] is create_reranker.return_value

    def test_env_setting_enables_rerank(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SIF_RERANK_ENABLED=1 through the real Settings channel opens the gate."""
        monkeypatch.setenv("SIF_RERANK_ENABLED", "1")
        repo = MagicMock()
        repo.list_enabled.return_value = []
        manager = MagicMock()
        manager.embed_single.return_value = [0.0] * 4
        manager._model = MagicMock()
        pipeline = MagicMock()
        pipeline.search.return_value = [self._result()]
        index = tmp_path / "index.db"
        index.touch()
        try:
            get_settings.cache_clear()
            with (
                patch("sif.cli.commands.search.Database", return_value=MagicMock()),
                patch("sif.cli.commands.search.CollectionRepository", return_value=repo),
                patch("sif.cli.commands.search.SearchPipeline", return_value=pipeline),
                patch(
                    "sif.embedding.manager.EmbeddingManager.from_settings",
                    return_value=manager,
                ),
                patch("sif.search.rerank.create_reranker") as create_reranker,
            ):
                result = CliRunner().invoke(query_cmd, ["query"], obj={"index_path": index})
        finally:
            get_settings.cache_clear()

        assert result.exit_code == 0, result.output
        create_reranker.assert_called_once()


class TestCandidateLimitResolution:
    """D-10 (Phase 16): -C resolves flag > SIF_RERANK_CANDIDATE_LIMIT, clamped to 5..50.

    The shipped Click range stays 1..200 (no user-visible narrowing); the
    bound is enforced where the value becomes a request — resolve_candidate_limit.
    """

    @staticmethod
    def _result() -> SearchResult:
        return SearchResult(
            document_id="doc-1",
            rank=1,
            score=0.5,
            title="T",
            path="/notes/t.md",
            collection_name="c",
        )

    def _invoke(
        self,
        tmp_path: Path,
        args: list[str],
        settings: object = None,
    ) -> tuple[object, MagicMock]:
        """Invoke query_cmd; return (result, pipeline) for SearchOptions asserts."""
        repo = MagicMock()
        repo.list_enabled.return_value = []
        manager = MagicMock()
        manager.embed_single.return_value = [0.0] * 4
        manager._model = MagicMock()
        pipeline = MagicMock()
        pipeline.search.return_value = [self._result()]
        index = tmp_path / "index.db"
        index.touch()
        with (
            patch("sif.cli.commands.search.Database", return_value=MagicMock()),
            patch("sif.cli.commands.search.CollectionRepository", return_value=repo),
            patch("sif.cli.commands.search.SearchPipeline", return_value=pipeline),
            patch("sif.embedding.manager.EmbeddingManager.from_settings", return_value=manager),
            # rerank stays off unless a test opens it via the settings mock.
            patch("sif.search.rerank.create_reranker"),
            patch(
                "sif.config.settings.get_settings",
                return_value=settings
                if settings is not None
                else _query_settings_mock(rerank_candidate_limit=33),
            ),
        ):
            result = CliRunner().invoke(query_cmd, args, obj={"index_path": index})
        return result, pipeline

    def test_omitted_flag_resolves_from_setting(self, tmp_path: Path) -> None:
        """No -C: SearchOptions.candidate_limit comes from SIF_RERANK_CANDIDATE_LIMIT."""
        result, pipeline = self._invoke(tmp_path, ["query"])

        assert result.exit_code == 0, result.output
        # 33 is non-default so the assertion cannot pass via a literal flag default.
        assert pipeline.search.call_args.args[1].candidate_limit == 33

    def test_explicit_flag_beats_setting(self, tmp_path: Path) -> None:
        """An explicit -C inside the bounds wins over the setting (D-10 precedence)."""
        result, pipeline = self._invoke(tmp_path, ["query", "-C", "7"])

        assert result.exit_code == 0, result.output
        assert pipeline.search.call_args.args[1].candidate_limit == 7

    def test_flag_range_stays_wide_but_resolution_clamps(self, tmp_path: Path) -> None:
        """-C 200 and -C 1 are accepted by Click (range 1..200) but resolve to 50 and 5."""
        wide, pipeline_wide = self._invoke(tmp_path, ["query", "-C", "200"])
        assert wide.exit_code == 0, wide.output
        assert pipeline_wide.search.call_args.args[1].candidate_limit == 50

        narrow, pipeline_narrow = self._invoke(tmp_path, ["query", "-C", "1"])
        assert narrow.exit_code == 0, narrow.output
        assert pipeline_narrow.search.call_args.args[1].candidate_limit == 5

    def test_wide_open_mock_settings_keeps_candidate_limit_int(self, tmp_path: Path) -> None:
        """Pitfall 10: a MagicMock cap can never leak into the plain SearchOptions dataclass.

        A wide-open MagicMock is truthy, so rerank_enabled opens the gate too —
        create_reranker is patched; the assertion is the int-ness of the cap.
        """
        result, pipeline = self._invoke(tmp_path, ["query"], settings=MagicMock())

        assert result.exit_code == 0, result.output
        options = pipeline.search.call_args.args[1]
        assert options.candidate_limit == 20
        assert isinstance(options.candidate_limit, int)


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
                return_value=_query_settings_mock(),
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
        assert lines[0] == "rank,score,title,path,collection,vectors_stale"
        assert lines[1:] == [f'"1","0.9500","{long_title}","{long_path}","notes","false"']


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
        settings = settings or _query_settings_mock()
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
            patch("sif.cli.commands.search.Database", return_value=MagicMock()),
            patch("sif.cli.commands.search.CollectionRepository", return_value=repo),
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
                # D-12 (14-03): the staleness column; fixture rows default False.
                "vectors_stale": "false",
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
        settings = _query_settings_mock()
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
        # rerank_enabled=True opens the D-12 gate so the patched ImportError
        # from create_reranker is actually raised on this enabled path.
        settings = _query_settings_mock(reranker_model_name="reranker", rerank_enabled=True)

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
            patch("sif.cli.commands.search.Database", return_value=MagicMock()),
            patch("sif.cli.commands.search.CollectionRepository", return_value=repo),
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
        assert "[/3]" in result.output
        assert "notes [/3] review: bm25_score=" in result.output

        plain, _ = self._invoke_bm25(tmp_path, ["[/3]-notes", "--explain"], [row])

        assert plain.exit_code == 0
        assert "Query: [/3]-notes" in plain.output


class TestStalenessFormatMarker:
    """D-12 (SC3): one crafted stale result is visibly marked in every output format.

    A vector-stale doc surfaces only via the BM25/hybrid legs (its vector
    was purged — a real vsearch hit cannot be stale), so the battery crafts
    SearchResults carrying ``vectors_stale`` through the mock scaffolds;
    vsearch's shared --json surface is covered by the same formatter code.
    """

    @staticmethod
    def _result(stale: bool, **overrides: object) -> SearchResult:
        """Craft one result; the stale flag and identity fields stay paired."""
        fields: dict[str, object] = {
            "document_id": "doc-stale" if stale else "doc-fresh",
            "rank": 1 if stale else 2,
            "score": 0.9 if stale else 0.8,
            "title": "Stale Doc" if stale else "Fresh Doc",
            "path": "/notes/stale.md" if stale else "/notes/fresh.md",
            "collection_name": "notes",
            "content": "line one\nline two",
            "vectors_stale": stale,
        }
        fields.update(overrides)
        return SearchResult(**fields)  # type: ignore[arg-type]

    @staticmethod
    def _rows() -> list[SearchResult]:
        cls = TestStalenessFormatMarker
        return [cls._result(stale=True), cls._result(stale=False)]

    @staticmethod
    def _index(tmp_path: Path) -> Path:
        index = tmp_path / "index.db"
        index.touch()
        return index

    def _invoke_bm25(self, tmp_path: Path, args: list[str]) -> object:
        """Invoke search_cmd over the mock scaffold with the crafted rows."""
        searcher = MagicMock()
        searcher.search.return_value = self._rows()
        repo = MagicMock()
        repo.list_enabled.return_value = []
        with (
            patch("sif.cli.commands.search.Database", return_value=MagicMock()),
            patch("sif.cli.commands.search.CollectionRepository", return_value=repo),
            patch("sif.cli.commands.search.BM25Searcher", return_value=searcher),
        ):
            return CliRunner().invoke(
                search_cmd,
                args,
                env={"COLUMNS": "80"},
                obj={"index_path": self._index(tmp_path)},
            )

    def _invoke_query(self, tmp_path: Path, args: list[str]) -> object:
        """Invoke query_cmd over the pipeline mock scaffold with the crafted rows."""
        repo = MagicMock()
        repo.list_enabled.return_value = []
        manager = MagicMock()
        manager.embed_single.return_value = [0.0] * 4
        manager._model = MagicMock()
        pipeline = MagicMock()
        pipeline.search.return_value = self._rows()
        settings = _query_settings_mock()
        with (
            patch("sif.cli.commands.search.Database", return_value=MagicMock()),
            patch("sif.cli.commands.search.CollectionRepository", return_value=repo),
            patch("sif.cli.commands.search.SearchPipeline", return_value=pipeline),
            patch("sif.embedding.manager.EmbeddingManager.from_settings", return_value=manager),
            patch("sif.config.settings.get_settings", return_value=settings),
        ):
            return CliRunner().invoke(
                query_cmd,
                args,
                env={"COLUMNS": "80"},
                obj={"index_path": self._index(tmp_path)},
            )

    # ------------------------------------------------------------------
    # Rich table (search_cmd + query_cmd bodies; vsearch shares the cell)
    # ------------------------------------------------------------------

    def test_table_marks_stale_result_not_fresh(self, tmp_path: Path) -> None:
        """The stale result's Title cell carries the dim annotation; fresh does not."""
        result = self._invoke_bm25(tmp_path, ["query"])

        assert result.exit_code == 0
        # stdout: the D-13 hint rides stderr (mixed into .output by click >=8.2).
        assert "(stale vectors)" in result.stdout
        # Exactly one annotation for one stale row; the fresh row stays clean.
        assert result.stdout.count("(stale vectors)") == 1
        assert "Fresh Doc" in result.stdout
        # D-12: no new column — the header row gains nothing.
        assert "vectors_stale" not in result.stdout

    def test_query_table_marks_stale_result(self, tmp_path: Path) -> None:
        """The hybrid query table renders the same annotation on the stale title."""
        result = self._invoke_query(tmp_path, ["query"])

        assert result.exit_code == 0
        assert "(stale vectors)" in result.stdout
        assert result.stdout.count("(stale vectors)") == 1

    # ------------------------------------------------------------------
    # JSON (no formatter change — to_dict() carries the key since 14-02)
    # ------------------------------------------------------------------

    def test_json_carries_vectors_stale(self, tmp_path: Path) -> None:
        """--json serializes the stale boolean for both rows."""
        result = self._invoke_bm25(tmp_path, ["query", "--json"])

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload[0]["vectors_stale"] is True
        assert payload[1]["vectors_stale"] is False

    def test_json_line_numbers_dict_shape_preserves_key(self, tmp_path: Path) -> None:
        """--line-numbers dict rows still carry vectors_stale (dual-shape reader)."""
        result = self._invoke_bm25(tmp_path, ["query", "--line-numbers", "--json"])

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload[0]["line_numbers"] != ""
        assert payload[0]["vectors_stale"] is True
        assert payload[1]["vectors_stale"] is False

    # ------------------------------------------------------------------
    # CSV (one extra column)
    # ------------------------------------------------------------------

    def test_csv_column_carries_true_and_false(self, tmp_path: Path) -> None:
        """The header gains a vectors_stale column; rows emit true/false."""
        result = self._invoke_bm25(tmp_path, ["query", "--csv"])

        assert result.exit_code == 0
        # result.stdout: crafted stale rows also trigger the D-13 stderr hint,
        # which click >=8.2 mixes into .output (14-01 JSON-purity precedent).
        lines = result.stdout.splitlines()
        assert lines[0] == "rank,score,title,path,collection,vectors_stale"
        assert lines[1:] == [
            '"1","0.9000","Stale Doc","/notes/stale.md","notes","true"',
            '"2","0.8000","Fresh Doc","/notes/fresh.md","notes","false"',
        ]

    def test_csv_line_numbers_dict_shape_renders_marker(self, tmp_path: Path) -> None:
        """Dict rows (--line-numbers path) render the same true/false column."""
        result = self._invoke_bm25(tmp_path, ["query", "--line-numbers", "--csv"])

        assert result.exit_code == 0
        lines = result.stdout.splitlines()
        assert lines[0].endswith(",vectors_stale")
        assert lines[1].endswith(',"true"')
        assert lines[2].endswith(',"false"')

    # ------------------------------------------------------------------
    # Markdown (inline annotation on the per-result title line)
    # ------------------------------------------------------------------

    def test_md_annotation_on_stale_title_only(self, tmp_path: Path) -> None:
        """The stale block's title line carries '(stale vectors)'; fresh does not."""
        result = self._invoke_bm25(tmp_path, ["query", "--md"])

        assert result.exit_code == 0
        assert "## 1. Stale Doc (stale vectors)" in result.stdout
        assert "## 2. Fresh Doc" in result.stdout
        assert result.stdout.count("(stale vectors)") == 1

    def test_md_line_numbers_dict_shape_renders_marker(self, tmp_path: Path) -> None:
        """Dict rows (--line-numbers path) render the same annotation."""
        result = self._invoke_bm25(tmp_path, ["query", "--line-numbers", "--md"])

        assert result.exit_code == 0
        assert "## 1. Stale Doc (stale vectors)" in result.stdout
        assert result.stdout.count("(stale vectors)") == 1

    # ------------------------------------------------------------------
    # XML (fixed boolean attribute on the result element)
    # ------------------------------------------------------------------

    def test_xml_attribute_true_false_and_parseable(self, tmp_path: Path) -> None:
        """The stale element carries vectors_stale="true"; output stays parseable."""
        result = self._invoke_bm25(tmp_path, ["query", "--xml"])

        assert result.exit_code == 0
        assert 'vectors_stale="true"' in result.stdout
        assert 'vectors_stale="false"' in result.stdout
        root = ET.fromstring(result.stdout)
        elements = root.findall("result")
        assert [e.get("vectors_stale") for e in elements] == ["true", "false"]

    def test_xml_line_numbers_dict_shape_renders_marker(self, tmp_path: Path) -> None:
        """Dict rows (--line-numbers path) render the same attribute."""
        result = self._invoke_bm25(tmp_path, ["query", "--line-numbers", "--xml"])

        assert result.exit_code == 0
        root = ET.fromstring(result.stdout)
        elements = root.findall("result")
        assert [e.get("vectors_stale") for e in elements] == ["true", "false"]

    # ------------------------------------------------------------------
    # D-13: the post-results stderr remedy hint
    # ------------------------------------------------------------------

    @staticmethod
    def _hint_in_stderr(result: object) -> bool:
        """Whitespace-normalized containment (Rich wraps at console width)."""
        return "have stale vectors" in re.sub(r"\s+", " ", result.stderr)  # type: ignore[attr-defined]

    def test_remedy_hint_one_stderr_line_names_count(self, tmp_path: Path) -> None:
        """>=1 stale result -> exactly one stderr line naming the count + remedy."""
        rows = [
            self._result(stale=True),
            self._result(stale=True, rank=2, title="Also Stale", path="/notes/stale2.md"),
            self._result(stale=False),
        ]
        searcher = MagicMock()
        searcher.search.return_value = rows
        repo = MagicMock()
        repo.list_enabled.return_value = []
        with (
            patch("sif.cli.commands.search.Database", return_value=MagicMock()),
            patch("sif.cli.commands.search.CollectionRepository", return_value=repo),
            patch("sif.cli.commands.search.BM25Searcher", return_value=searcher),
        ):
            result = CliRunner().invoke(
                search_cmd,
                ["query"],
                env={"COLUMNS": "80"},
                obj={"index_path": self._index(tmp_path)},
            )

        assert result.exit_code == 0
        normalized = re.sub(r"\s+", " ", result.stderr)
        assert "2 results have stale vectors — run 'sif index embed' to refresh" in normalized
        # Exactly one hint line — never one per result.
        assert result.stderr.count("have stale vectors") == 1
        # D-13: the hint never appears on stdout (the table's own D-12
        # annotation legitimately contains 'stale vectors' there — the
        # hint-specific fragments must not).
        assert "have stale vectors" not in result.stdout
        assert "run 'sif index embed'" not in result.stdout

    def test_remedy_hint_json_stdout_stays_clean(self, tmp_path: Path) -> None:
        """Under --json the hint rides stderr only; stdout parses as pure JSON."""
        result = self._invoke_bm25(tmp_path, ["query", "--json"])

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert len(payload) == 2
        assert self._hint_in_stderr(result)
        assert "stale vectors" not in result.stdout

    def test_quiet_suppresses_hint_but_json_renders(self, tmp_path: Path) -> None:
        """-q suppresses the hint while the --json results still render."""
        result = self._invoke_bm25(tmp_path, ["query", "--json", "-q"])

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert len(payload) == 2
        assert payload[0]["vectors_stale"] is True
        assert not self._hint_in_stderr(result)

    def test_zero_stale_results_no_hint(self, tmp_path: Path) -> None:
        """No stale results -> no hint line (and clean stderr)."""
        rows = [self._result(stale=False)]
        searcher = MagicMock()
        searcher.search.return_value = rows
        repo = MagicMock()
        repo.list_enabled.return_value = []
        with (
            patch("sif.cli.commands.search.Database", return_value=MagicMock()),
            patch("sif.cli.commands.search.CollectionRepository", return_value=repo),
            patch("sif.cli.commands.search.BM25Searcher", return_value=searcher),
        ):
            result = CliRunner().invoke(
                search_cmd,
                ["query"],
                env={"COLUMNS": "80"},
                obj={"index_path": self._index(tmp_path)},
            )

        assert result.exit_code == 0
        assert result.stderr == ""

    def test_remedy_hint_fires_for_query_cmd(self, tmp_path: Path) -> None:
        """The hybrid query command emits the same hint after its results."""
        result = self._invoke_query(tmp_path, ["query"])

        assert result.exit_code == 0
        assert self._hint_in_stderr(result)
        assert "have stale vectors" not in result.stdout

    def test_remedy_hint_fires_for_vsearch_cmd(self, tmp_path: Path) -> None:
        """The vsearch command body carries the same hint wiring (mocked hits)."""
        searcher = MagicMock()
        searcher.search.return_value = self._rows()
        repo = MagicMock()
        repo.list_enabled.return_value = []
        manager = MagicMock()
        manager.embed_single.return_value = [0.0] * 4
        settings = MagicMock()
        with (
            patch("sif.cli.commands.search.Database", return_value=MagicMock()),
            patch("sif.cli.commands.search.CollectionRepository", return_value=repo),
            patch("sif.search.vector.VectorSearcher", return_value=searcher),
            patch("sif.embedding.manager.EmbeddingManager.from_settings", return_value=manager),
            patch("sif.config.settings.get_settings", return_value=settings),
        ):
            result = CliRunner().invoke(
                vsearch_cmd,
                ["query"],
                env={"COLUMNS": "80"},
                obj={"index_path": self._index(tmp_path)},
            )

        assert result.exit_code == 0
        assert self._hint_in_stderr(result)
        assert "have stale vectors" not in result.stdout


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
        settings = _query_settings_mock(embedding_dim=4)
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

        vsearch_cmd uses the module-level Database import, so the double is
        installed on sif.cli.commands.search — the same namespace the other
        closure tests patch.
        """
        index = tmp_path / "index.db"
        index.touch()
        TrackingDatabase.created.clear()
        monkeypatch.setattr("sif.cli.commands.search.Database", TrackingDatabase)
        searcher = MagicMock()
        searcher.search.return_value = []
        repo = MagicMock()
        repo.list_enabled.return_value = []
        manager = MagicMock()
        manager.embed_single.return_value = [0.0] * 4
        # embedding_dim must be a real int (see query closure test note).
        settings = MagicMock(embedding_dim=4)
        with (
            patch("sif.cli.commands.search.CollectionRepository", return_value=repo),
            patch("sif.search.vector.VectorSearcher", return_value=searcher),
            patch("sif.embedding.manager.EmbeddingManager.from_settings", return_value=manager),
            patch("sif.config.settings.get_settings", return_value=settings),
        ):
            result = CliRunner().invoke(vsearch_cmd, ["query"], obj={"index_path": index})

        assert result.exit_code == 0, result.output
        assert TrackingDatabase.created, "vsearch must construct its Database"
        for instance in TrackingDatabase.created:
            assert instance._connection is None


class TestPreSearchRefresh:
    """SC1/SC2: search_cmd's pre-command drift refresh (LIVE-10, D-01..D-07).

    Real-DB CliRunner end-to-end: index a tmp_path collection, drift it
    deterministically (content writes / unlink — never sleep), and prove the
    search finds refreshed content with the notice on stderr and stdout
    clean. A clean index pays nothing: no lock file, no notice, no writes.
    """

    @pytest.fixture(autouse=True)
    def isolated_settings(self) -> Generator[None, None, None]:
        """Real Settings must not leak a cached instance between invocations."""
        get_settings.cache_clear()
        yield
        get_settings.cache_clear()

    @staticmethod
    def _seed_index(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        files: dict[str, str] | None = None,
    ) -> tuple[Path, Path, Settings]:
        """Create a real indexed collection; default one alpha-term document.

        Returns (db_path, notes, settings); every invoke must run under
        ``patch("sif.config.settings.get_settings", return_value=settings)``
        so the schema's vec0 dimension check and the drift check share the
        same hermetic settings (embedding_dim=8, TestDatabaseClosure culture)
        — unless the test drives the real env-var path instead.
        """
        for var in (
            "SIF_EMBEDDING_DIM",
            "SIF_MODEL_TYPE",
            "SIF_MODEL_NAME",
            "SIF_SEARCH_REFRESH_ENABLED",
            "SIF_SEARCH_REFRESH_MAX_FILES",
        ):
            monkeypatch.delenv(var, raising=False)
        settings = Settings(embedding_dim=8, model_name="test", cache_embeddings=False)
        db_path = tmp_path / "search.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        if files is None:
            files = {
                "a.md": "# Heading One\n\nAlpha paragraph text for search. " * 10,
            }
        for name, body in files.items():
            (notes / name).write_text(body, encoding="utf-8")
        db = Database(db_path)
        with patch("sif.config.settings.get_settings", return_value=settings):
            db.init_schema()
            with db.connection:
                CollectionRepository(db.connection).create(
                    Collection(name="notes", path=str(notes))
                )
            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            IncrementalIndexer(db.connection).update_collection(coll)
        db.close()
        return db_path, notes, settings

    def test_search_finds_modified_content_and_notifies_on_stderr(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SC1: a post-index edit is BM25-refreshed before searching; notice on stderr."""
        db_path, notes, settings = self._seed_index(tmp_path, monkeypatch)
        (notes / "a.md").write_text(
            "# Heading Two\n\nZanzibar unique new term body. " * 10, encoding="utf-8"
        )

        with patch("sif.config.settings.get_settings", return_value=settings):
            result = CliRunner().invoke(search_cmd, ["zanzibar"], obj={"index_path": db_path})

        assert result.exit_code == 0
        assert "refreshed 1 files (bm25) before search" in result.stderr
        assert "Heading Two" in result.output

        # Stat-decides no-op: the second identical search is silent, still finds it.
        with patch("sif.config.settings.get_settings", return_value=settings):
            second = CliRunner().invoke(search_cmd, ["zanzibar"], obj={"index_path": db_path})
        assert second.exit_code == 0
        assert second.stderr == ""
        assert "Heading Two" in second.output

    def test_refresh_failure_warns_and_search_proceeds(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """D-05 failure leg: a refresh exception warns on stderr, exit 0, stale results.

        The over-cap leg of the same prohibition is test-enforced elsewhere;
        this exercises the ``except`` branch itself — a refresh failure must
        never fail the search (exit 0, results from the current index).
        """

        def _boom(*_args: object, **_kwargs: object) -> None:
            raise RuntimeError("simulated refresh failure")

        db_path, notes, settings = self._seed_index(tmp_path, monkeypatch)
        (notes / "a.md").write_text(
            "# Heading Three\n\nZanzibar unique new term body. " * 10, encoding="utf-8"
        )

        with (
            patch("sif.config.settings.get_settings", return_value=settings),
            patch("sif.cli.commands.search.refresh_drifted", side_effect=_boom),
        ):
            result = CliRunner().invoke(search_cmd, ["heading"], obj={"index_path": db_path})

        assert result.exit_code == 0
        assert "Pre-search refresh failed; searching the current index" in result.stderr
        # The search proceeded on the STALE index: the pre-edit document is
        # still served (the new term exists only in the drifted content).
        assert "Heading One" in result.output
        assert "Heading Three" not in result.output

        # Recovery: with the failure gone, the next search refreshes normally.
        with patch("sif.config.settings.get_settings", return_value=settings):
            recovered = CliRunner().invoke(search_cmd, ["zanzibar"], obj={"index_path": db_path})
        assert recovered.exit_code == 0
        assert "refreshed 1 files (bm25) before search" in recovered.stderr
        assert "Heading Three" in recovered.output

    def test_touch_only_drift_converges_across_searches(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CR-01 regression: a same-content touch refreshes once, then stays clean.

        A ``git checkout`` of identical content (or archive extract / no-op
        save) moves mtimes without changing bytes. The first search
        converges the stored mtime; the second must pay nothing — no
        refresh burst (the ONLY lock acquirer), no notice, no drift.
        """
        db_path, notes, settings = self._seed_index(tmp_path, monkeypatch)
        doc = notes / "a.md"
        os.utime(doc, (1_700_000_000, 1_700_000_000))

        with patch("sif.config.settings.get_settings", return_value=settings):
            first = CliRunner().invoke(search_cmd, ["alpha"], obj={"index_path": db_path})

        assert first.exit_code == 0
        # Nothing was refreshed (checksum skip; only the mtime converged).
        assert "refreshed 0 files (bm25) before search" in first.stderr
        # The fresh mtime was persisted on the checksum-skip path.
        assert self._document_snapshot(db_path)[str(doc.resolve())][1] == 1_700_000_000.0

        with (
            patch("sif.config.settings.get_settings", return_value=settings),
            patch("sif.cli.commands.search.refresh_drifted") as spy,
        ):
            second = CliRunner().invoke(search_cmd, ["alpha"], obj={"index_path": db_path})

        assert second.exit_code == 0
        assert "Heading One" in second.output
        assert second.stderr == ""
        # No refresh burst → no index_lock window on the clean second search.
        spy.assert_not_called()

    def test_search_finds_new_file_and_drops_deleted_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SC1: a new file becomes searchable and a deleted file stops hitting."""
        db_path, notes, settings = self._seed_index(tmp_path, monkeypatch)
        (notes / "b.md").write_text(
            "# Brand New\n\nFreshnote unique new file term. " * 10, encoding="utf-8"
        )
        (notes / "a.md").unlink()

        with patch("sif.config.settings.get_settings", return_value=settings):
            result = CliRunner().invoke(search_cmd, ["freshnote"], obj={"index_path": db_path})
            gone = CliRunner().invoke(search_cmd, ["alpha"], obj={"index_path": db_path})

        assert result.exit_code == 0
        # WR-02: the notice names the actual outcome — the new file was
        # refreshed, the deleted one removed — not the raw drift count.
        assert "refreshed 1 files, removed 1 (bm25) before search" in result.stderr
        assert "Brand New" in result.output
        assert gone.exit_code == 0
        assert "No results found" in gone.output

    def test_clean_search_is_lockless_silent_and_writeless(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SC2: a clean index costs a read-only walk — no lock file, no notice, no writes."""
        db_path, _notes, settings = self._seed_index(tmp_path, monkeypatch)

        def snapshot() -> dict[str, tuple[str, float]]:
            conn = sqlite3.connect(str(db_path))
            try:
                return {
                    row[0]: (row[1], row[2])
                    for row in conn.execute("SELECT path, checksum, mtime FROM documents")
                }
            finally:
                conn.close()

        before = snapshot()
        with patch("sif.config.settings.get_settings", return_value=settings):
            result = CliRunner().invoke(search_cmd, ["alpha"], obj={"index_path": db_path})

        assert result.exit_code == 0
        assert "Heading One" in result.output
        assert result.stderr == ""
        assert "refreshed" not in result.output
        assert not Path(str(db_path) + ".lock").exists()
        assert snapshot() == before

    def test_json_stdout_stays_clean_with_refresh_notice_on_stderr(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """D-07: under --json the notice rides stderr; stdout parses as pure JSON."""
        db_path, notes, settings = self._seed_index(tmp_path, monkeypatch)
        (notes / "a.md").write_text(
            "# Heading Two\n\nZanzibar unique new term body. " * 10, encoding="utf-8"
        )

        with patch("sif.config.settings.get_settings", return_value=settings):
            result = CliRunner().invoke(
                search_cmd, ["zanzibar", "--json"], obj={"index_path": db_path}
            )

        assert result.exit_code == 0
        # result.stdout is the pure stdout stream (click >=8.2 mixes both in
        # .output); it must parse as JSON untouched by the stderr notice.
        payload = json.loads(result.stdout)
        assert len(payload) == 1
        assert payload[0]["title"] == "Heading Two"
        assert "refreshed 1 files (bm25) before search" in result.stderr

    # ------------------------------------------------------------------
    # Task 2: cap boundary, opt-outs, and the rest of the trio
    # ------------------------------------------------------------------

    THREE_FILES: ClassVar[dict[str, str]] = {
        "a.md": "# Doc A\n\nAlpha paragraph text for search. " * 10,
        "b.md": "# Doc B\n\nBravo paragraph text for search. " * 10,
        "c.md": "# Doc C\n\nCharlie paragraph text for search. " * 10,
    }

    @classmethod
    def _drift_three(cls, notes: Path) -> None:
        """Rewrite all three files so every stored mtime goes stale."""
        for name, body in cls.THREE_FILES.items():
            (notes / name).write_text(
                body.replace("paragraph text", "zanzibar drifted text"),
                encoding="utf-8",
            )

    @staticmethod
    def _stored_content(db_path: Path, doc: Path) -> str:
        """Read one document's stored content through a fresh connection."""
        conn = sqlite3.connect(str(db_path))
        try:
            row = conn.execute(
                "SELECT content FROM documents WHERE path = ?", (str(doc.resolve()),)
            ).fetchone()
            assert row is not None, f"no stored document for {doc}"
            return row[0]
        finally:
            conn.close()

    def _document_snapshot(self, db_path: Path) -> dict[str, tuple[str, float]]:
        """Snapshot {path: (checksum, mtime)} via a fresh connection."""
        conn = sqlite3.connect(str(db_path))
        try:
            return {
                row[0]: (row[1], row[2])
                for row in conn.execute("SELECT path, checksum, mtime FROM documents")
            }
        finally:
            conn.close()

    def test_ignored_stored_doc_converges_across_searches(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """WR-01 regression: a later ignore pattern converges instead of looping.

        A stored document that ``SIF_WATCH_IGNORE_PATTERNS`` retroactively
        excludes is deleted-shaped drift; the refresh must remove it the
        way ``sif index update`` would, so the SECOND search is clean —
        not an eternal drift/lock/notice loop.
        """
        db_path, notes, _settings = self._seed_index(
            tmp_path,
            monkeypatch,
            files={
                "a.md": "# Heading One\n\nAlpha paragraph text for search. " * 10,
                "secret.md": "# Secret Doc\n\nSeekrit hidden body text. " * 10,
            },
        )
        ignoring = Settings(
            embedding_dim=8,
            model_name="test",
            cache_embeddings=False,
            watch_ignore_patterns=["secret*"],
        )

        with patch("sif.config.settings.get_settings", return_value=ignoring):
            first = CliRunner().invoke(search_cmd, ["seekrit"], obj={"index_path": db_path})

        assert first.exit_code == 0
        # WR-02: nothing was refreshed — the excluded doc was REMOVED.
        assert "refreshed 0 files, removed 1 (bm25) before search" in first.stderr
        # ...and it REMOVED the excluded doc, mirroring `sif index update`.
        conn = sqlite3.connect(str(db_path))
        try:
            stored = {row[0] for row in conn.execute("SELECT path FROM documents")}
        finally:
            conn.close()
        assert stored == {str((notes / "a.md").resolve())}
        assert "No results found" in first.output

        with (
            patch("sif.config.settings.get_settings", return_value=ignoring),
            patch("sif.cli.commands.search.refresh_drifted") as spy,
        ):
            second = CliRunner().invoke(search_cmd, ["alpha"], obj={"index_path": db_path})

        assert second.exit_code == 0
        assert "Heading One" in second.output
        assert second.stderr == ""
        # No refresh burst → no index_lock window on the clean second search.
        spy.assert_not_called()

    def test_unparseable_drift_warns_each_search_and_never_converges(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """WR-01 regression: invalid-UTF-8 drift warns with a count, exit 0, results served.

        The mtime decision, made explicit: a parse-failed file deliberately
        never converges — the stored content is genuinely stale — so it
        re-warns on EVERY search until the file is fixed or removed. The fix
        makes that loop visible (a counted "failed to parse" warning) and
        honest (no "refreshed 0 files" masquerading as a clean refresh).
        """
        db_path, notes, settings = self._seed_index(tmp_path, monkeypatch)
        doc = notes / "a.md"
        # Deterministic, content-based unreadability: invalid UTF-8 bytes
        # plus a forced distinct mtime (no chmod platform flakiness).
        doc.write_bytes(b"\xff\xfe\x00 not utf-8 \xff\xfe")
        os.utime(doc, (1_700_000_000, 1_700_000_000))

        with patch("sif.config.settings.get_settings", return_value=settings):
            first = CliRunner().invoke(search_cmd, ["alpha"], obj={"index_path": db_path})

        assert first.exit_code == 0
        # The failure is named and counted in the notice — not a silent
        # "refreshed 0 files" that reads as a clean refresh.
        assert "refreshed 0 files, 1 failed to parse (bm25) before search" in first.stderr
        # The search proceeded on the current (stale) index: still served.
        assert "Heading One" in first.output

        # Deliberate non-convergence: the SECOND search re-drifts and warns
        # again — the loop is now visible instead of silent.
        with patch("sif.config.settings.get_settings", return_value=settings):
            second = CliRunner().invoke(search_cmd, ["alpha"], obj={"index_path": db_path})

        assert second.exit_code == 0
        assert "1 failed to parse" in second.stderr
        assert "Heading One" in second.output

        # The stored row was untouched: stale content, unconverged mtime.
        assert self._document_snapshot(db_path)[str(doc.resolve())][1] != 1_700_000_000.0
        assert "Alpha" in self._stored_content(db_path, doc)

        # D-07: -q suppresses the notice/warning line (the underlying
        # logger.warning may still ride stderr — logging is error output).
        with patch("sif.config.settings.get_settings", return_value=settings):
            quiet = CliRunner().invoke(
                search_cmd, ["alpha", "--quiet"], obj={"index_path": db_path}
            )

        assert quiet.exit_code == 0
        assert "failed to parse" not in quiet.stderr
        assert "(bm25) before search" not in quiet.stderr

    def test_over_cap_drift_skips_refresh_and_warns(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """D-05/D-06: 3 drifted files over cap=2 — no refresh, no lock, warn + stale hits."""
        db_path, notes, _settings = self._seed_index(
            tmp_path, monkeypatch, files=dict(self.THREE_FILES)
        )
        self._drift_three(notes)
        # Real env-var settings path: cap 2, dim 8 matching the seeded vec0.
        monkeypatch.setenv("SIF_EMBEDDING_DIM", "8")
        monkeypatch.setenv("SIF_SEARCH_REFRESH_MAX_FILES", "2")

        before = self._document_snapshot(db_path)
        result = CliRunner().invoke(search_cmd, ["alpha"], obj={"index_path": db_path})

        assert result.exit_code == 0
        # Normalize whitespace: Rich soft-wraps the warning at console width.
        flat_stderr = " ".join(result.stderr.split())
        assert "index drift: 3 changed files exceeds the pre-search refresh cap (2)" in flat_stderr
        assert "run 'sif index update' to refresh" in flat_stderr
        # Nothing was refreshed and the lock file was never created.
        assert self._document_snapshot(db_path) == before
        assert not Path(str(db_path) + ".lock").exists()
        # The stale index still answers: old content remains searchable.
        assert "Doc A" in result.output

    def test_cap_boundary_count_equal_to_cap_refreshes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """D-06 exact boundary: count == cap still refreshes (only count > cap skips)."""
        db_path, notes, _settings = self._seed_index(
            tmp_path, monkeypatch, files=dict(self.THREE_FILES)
        )
        self._drift_three(notes)
        monkeypatch.setenv("SIF_EMBEDDING_DIM", "8")
        monkeypatch.setenv("SIF_SEARCH_REFRESH_MAX_FILES", "3")

        result = CliRunner().invoke(search_cmd, ["zanzibar"], obj={"index_path": db_path})

        assert result.exit_code == 0
        assert "refreshed 3 files (bm25) before search" in result.stderr
        assert "Doc A" in result.output

    def test_over_cap_never_parses_candidates(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """D-05 count-first: the over-cap decision precedes any candidate parsing."""
        db_path, notes, _settings = self._seed_index(
            tmp_path, monkeypatch, files=dict(self.THREE_FILES)
        )
        self._drift_three(notes)
        capped = Settings(
            embedding_dim=8,
            model_name="test",
            cache_embeddings=False,
            search_refresh_max_files=2,
        )

        with (
            patch("sif.config.settings.get_settings", return_value=capped),
            patch("sif.indexing.drift.IncrementalIndexer") as mock_indexer,
        ):
            result = CliRunner().invoke(search_cmd, ["alpha"], obj={"index_path": db_path})

        assert result.exit_code == 0
        mock_indexer.assert_not_called()

    def test_setting_disabled_skips_detection_entirely(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SIF_SEARCH_REFRESH_ENABLED=0: detect_drift is never invoked; search proceeds."""
        db_path, notes, _settings = self._seed_index(tmp_path, monkeypatch)
        (notes / "a.md").write_text(
            "# Heading Two\n\nZanzibar unique new term body. " * 10, encoding="utf-8"
        )
        monkeypatch.setenv("SIF_EMBEDDING_DIM", "8")
        monkeypatch.setenv("SIF_SEARCH_REFRESH_ENABLED", "0")

        with patch("sif.cli.commands.search.detect_drift") as spy:
            result = CliRunner().invoke(search_cmd, ["alpha"], obj={"index_path": db_path})

        assert result.exit_code == 0
        spy.assert_not_called()
        assert result.stderr == ""
        # No refresh: the stale index still serves the old content.
        assert "Heading One" in result.output

    @pytest.mark.parametrize("command_name", ["search", "vsearch", "query"])
    def test_no_refresh_flag_skips_check_on_all_trio_commands(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        command_name: str,
    ) -> None:
        """--no-refresh on each trio command skips the drift check entirely."""
        db_path, notes, settings = self._seed_index(tmp_path, monkeypatch)
        (notes / "a.md").write_text(
            "# Heading Two\n\nZanzibar unique new term body. " * 10, encoding="utf-8"
        )
        command = {"search": search_cmd, "vsearch": vsearch_cmd, "query": query_cmd}[command_name]
        manager = MagicMock()
        manager.embed_single.return_value = [0.0] * 8
        manager._model = MagicMock()
        downstream = {
            "search": [],
            "vsearch": [
                patch(
                    "sif.search.vector.VectorSearcher",
                    return_value=MagicMock(search=MagicMock(return_value=[])),
                ),
            ],
            "query": [
                patch(
                    "sif.cli.commands.search.SearchPipeline",
                    return_value=MagicMock(search=MagicMock(return_value=[])),
                ),
                patch("sif.search.rerank.create_reranker", side_effect=ImportError("x")),
            ],
        }[command_name]

        with (
            patch("sif.config.settings.get_settings", return_value=settings),
            patch("sif.embedding.manager.EmbeddingManager.from_settings", return_value=manager),
            patch("sif.cli.commands.search.detect_drift") as spy,
            ExitStack() as stack,
        ):
            for patcher in downstream:
                stack.enter_context(patcher)
            result = CliRunner().invoke(
                command, ["alpha", "--no-refresh"], obj={"index_path": db_path}
            )

        assert result.exit_code == 0, result.output
        spy.assert_not_called()
        assert result.stderr == ""

    def test_quiet_suppresses_notice_but_refresh_still_happens(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """D-07: -q silences the notice while the under-cap refresh still runs."""
        db_path, notes, settings = self._seed_index(tmp_path, monkeypatch)
        (notes / "a.md").write_text(
            "# Heading Two\n\nZanzibar unique new term body. " * 10, encoding="utf-8"
        )

        with patch("sif.config.settings.get_settings", return_value=settings):
            result = CliRunner().invoke(
                search_cmd, ["zanzibar", "--quiet"], obj={"index_path": db_path}
            )

        assert result.exit_code == 0
        assert result.stderr == ""
        assert "Zanzibar" in self._stored_content(db_path, notes / "a.md")

    def test_quiet_suppresses_over_cap_warning(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """D-07: -q silences the over-cap warning too; nothing is refreshed."""
        db_path, notes, _settings = self._seed_index(
            tmp_path, monkeypatch, files=dict(self.THREE_FILES)
        )
        self._drift_three(notes)
        monkeypatch.setenv("SIF_EMBEDDING_DIM", "8")
        monkeypatch.setenv("SIF_SEARCH_REFRESH_MAX_FILES", "2")

        before = self._document_snapshot(db_path)
        result = CliRunner().invoke(search_cmd, ["alpha", "--quiet"], obj={"index_path": db_path})

        assert result.exit_code == 0
        assert result.stderr == ""
        assert self._document_snapshot(db_path) == before

    def test_vsearch_refreshes_drifted_file_before_search(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """D-01 trio: vsearch runs the same drift check before its searcher."""
        db_path, notes, settings = self._seed_index(tmp_path, monkeypatch)
        (notes / "a.md").write_text(
            "# Heading Two\n\nZanzibar unique new term body. " * 10, encoding="utf-8"
        )
        manager = MagicMock()
        manager.embed_single.return_value = [0.0] * 8
        searcher = MagicMock()
        searcher.search.return_value = []

        with (
            patch("sif.config.settings.get_settings", return_value=settings),
            patch("sif.embedding.manager.EmbeddingManager.from_settings", return_value=manager),
            patch("sif.search.vector.VectorSearcher", return_value=searcher),
        ):
            result = CliRunner().invoke(vsearch_cmd, ["zanzibar"], obj={"index_path": db_path})

        assert result.exit_code == 0, result.output
        assert "refreshed 1 files (bm25) before search" in result.stderr
        assert "Zanzibar" in self._stored_content(db_path, notes / "a.md")

    def test_query_refreshes_drifted_file_before_search(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """D-01 trio: query runs the same drift check before pipeline construction."""
        db_path, notes, settings = self._seed_index(tmp_path, monkeypatch)
        (notes / "a.md").write_text(
            "# Heading Two\n\nZanzibar unique new term body. " * 10, encoding="utf-8"
        )
        manager = MagicMock()
        manager.embed_single.return_value = [0.0] * 8
        manager._model = MagicMock()
        pipeline = MagicMock()
        pipeline.search.return_value = []

        with (
            patch("sif.config.settings.get_settings", return_value=settings),
            patch("sif.embedding.manager.EmbeddingManager.from_settings", return_value=manager),
            patch("sif.cli.commands.search.SearchPipeline", return_value=pipeline),
            patch("sif.search.rerank.create_reranker", side_effect=ImportError("x")),
        ):
            result = CliRunner().invoke(query_cmd, ["zanzibar"], obj={"index_path": db_path})

        assert result.exit_code == 0, result.output
        assert "refreshed 1 files (bm25) before search" in result.stderr
        assert "Zanzibar" in self._stored_content(db_path, notes / "a.md")


class TestQueryFusionWeightFlags:
    """--rrf-k/--bm25-weight/--vector-weight plumbing (Phase 15, D-02/D-03).

    Precedence per knob: CLI flag > SIF_ setting > default. Flags exist on
    query_cmd ONLY (hybrid fusion is the only place weights mean anything).
    """

    @staticmethod
    def _result() -> SearchResult:
        return SearchResult(
            document_id="doc-1",
            rank=1,
            score=0.5,
            title="T",
            path="/notes/t.md",
            collection_name="c",
        )

    @staticmethod
    def _index(tmp_path: Path) -> Path:
        index = tmp_path / "index.db"
        index.touch()
        return index

    def _invoke(
        self,
        tmp_path: Path,
        args: list[str],
        settings: object = None,
    ) -> tuple[object, MagicMock]:
        """Invoke query_cmd with everything mocked except (optionally) settings."""
        repo = MagicMock()
        repo.list_enabled.return_value = []
        manager = MagicMock()
        manager.embed_single.return_value = [0.0] * 4
        manager._model = MagicMock()
        pipeline = MagicMock()
        pipeline.search.return_value = [self._result()]
        patches = [
            patch("sif.cli.commands.search.Database", return_value=MagicMock()),
            patch("sif.cli.commands.search.CollectionRepository", return_value=repo),
            patch("sif.cli.commands.search.SearchPipeline", return_value=pipeline),
            patch("sif.embedding.manager.EmbeddingManager.from_settings", return_value=manager),
        ]
        if settings is not None:
            patches.append(
                patch("sif.config.settings.get_settings", return_value=settings),
            )
        with ExitStack() as stack:
            for patcher in patches:
                stack.enter_context(patcher)
            result = CliRunner().invoke(
                query_cmd,
                args,
                obj={"index_path": self._index(tmp_path)},
            )
        return result, pipeline

    def test_flags_fill_search_options(self, tmp_path: Path) -> None:
        """Explicit flags flow verbatim into the SearchOptions the pipeline gets."""
        settings = _query_settings_mock(rrf_k=99, bm25_weight=9.0, vector_weight=9.0)

        result, pipeline = self._invoke(
            tmp_path,
            [
                "query",
                "--rrf-k",
                "5",
                "--bm25-weight",
                "3.0",
                "--vector-weight",
                "0.5",
            ],
            settings=settings,
        )

        assert result.exit_code == 0, result.output
        options = pipeline.search.call_args[0][1]
        assert options.rrf_k == 5
        assert options.bm25_weight == 3.0
        assert options.vector_weight == 0.5

    def test_settings_fill_when_no_flag(self, tmp_path: Path) -> None:
        """Absent flags fall back to the SIF_ settings layer (patched here)."""
        settings = _query_settings_mock(rrf_k=7, bm25_weight=2.0, vector_weight=0.5)

        result, pipeline = self._invoke(tmp_path, ["query"], settings=settings)

        assert result.exit_code == 0, result.output
        options = pipeline.search.call_args[0][1]
        assert options.rrf_k == 7
        assert options.bm25_weight == 2.0
        assert options.vector_weight == 0.5

    def test_env_setting_reaches_options_with_real_settings(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """SIF_RRF_K=7 with no flag yields options.rrf_k == 7 (real Settings)."""
        monkeypatch.setenv("SIF_RRF_K", "7")
        # Keep the real settings off the reranker path (default name is truthy).
        monkeypatch.setenv("SIF_RERANKER_MODEL_NAME", "")
        monkeypatch.setenv("SIF_RERANKER_MODEL_PATH", "")
        repo = MagicMock()
        repo.list_enabled.return_value = []
        manager = MagicMock()
        manager.embed_single.return_value = [0.0] * 4
        manager._model = MagicMock()
        pipeline = MagicMock()
        pipeline.search.return_value = [self._result()]

        try:
            get_settings.cache_clear()
            with (
                patch("sif.cli.commands.search.Database", return_value=MagicMock()),
                patch("sif.cli.commands.search.CollectionRepository", return_value=repo),
                patch("sif.cli.commands.search.SearchPipeline", return_value=pipeline),
                patch(
                    "sif.embedding.manager.EmbeddingManager.from_settings",
                    return_value=manager,
                ),
                patch("sif.search.rerank.create_reranker", side_effect=ImportError("x")),
            ):
                result = CliRunner().invoke(
                    query_cmd,
                    ["query"],
                    obj={"index_path": self._index(tmp_path)},
                )
        finally:
            get_settings.cache_clear()

        assert result.exit_code == 0, result.output
        options = pipeline.search.call_args[0][1]
        assert options.rrf_k == 7
        assert options.bm25_weight == 1.0
        assert options.vector_weight == 1.0

    def test_flag_beats_env_setting(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """--rrf-k 5 overrides SIF_RRF_K=7 (flag > SIF_ > default, D-03)."""
        monkeypatch.setenv("SIF_RRF_K", "7")
        monkeypatch.setenv("SIF_RERANKER_MODEL_NAME", "")
        monkeypatch.setenv("SIF_RERANKER_MODEL_PATH", "")
        repo = MagicMock()
        repo.list_enabled.return_value = []
        manager = MagicMock()
        manager.embed_single.return_value = [0.0] * 4
        manager._model = MagicMock()
        pipeline = MagicMock()
        pipeline.search.return_value = [self._result()]

        try:
            get_settings.cache_clear()
            with (
                patch("sif.cli.commands.search.Database", return_value=MagicMock()),
                patch("sif.cli.commands.search.CollectionRepository", return_value=repo),
                patch("sif.cli.commands.search.SearchPipeline", return_value=pipeline),
                patch(
                    "sif.embedding.manager.EmbeddingManager.from_settings",
                    return_value=manager,
                ),
                patch("sif.search.rerank.create_reranker", side_effect=ImportError("x")),
            ):
                result = CliRunner().invoke(
                    query_cmd,
                    ["query", "--rrf-k", "5", "--bm25-weight", "3.0"],
                    obj={"index_path": self._index(tmp_path)},
                )
        finally:
            get_settings.cache_clear()

        assert result.exit_code == 0, result.output
        options = pipeline.search.call_args[0][1]
        assert options.rrf_k == 5
        assert options.bm25_weight == 3.0
        assert options.vector_weight == 1.0  # untouched knob keeps the SIF_/default value

    @pytest.mark.parametrize(
        "flag",
        [
            ["--rrf-k", "0"],
            ["--bm25-weight", "0"],
            ["--bm25-weight", "-1"],
            ["--vector-weight", "0"],
            ["--vector-weight", "-0.5"],
        ],
    )
    def test_invalid_flag_values_rejected(self, tmp_path: Path, flag: list[str]) -> None:
        """Out-of-range flags die as Click usage errors (non-zero exit)."""
        settings = _query_settings_mock(rrf_k=60, bm25_weight=1.0, vector_weight=1.0)

        result, pipeline = self._invoke(tmp_path, ["query", *flag], settings=settings)

        assert result.exit_code != 0
        pipeline.search.assert_not_called()

    def test_invalid_env_rrf_k_surfaces_clean_error(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """SIF_RRF_K=0 fails Pydantic validation naming rrf_k, as a ClickException."""
        monkeypatch.setenv("SIF_RRF_K", "0")
        monkeypatch.setenv("SIF_RERANKER_MODEL_NAME", "")
        monkeypatch.setenv("SIF_RERANKER_MODEL_PATH", "")
        repo = MagicMock()
        repo.list_enabled.return_value = []
        manager = MagicMock()
        manager.embed_single.return_value = [0.0] * 4
        manager._model = MagicMock()
        pipeline = MagicMock()
        pipeline.search.return_value = [self._result()]

        try:
            get_settings.cache_clear()
            with (
                patch("sif.cli.commands.search.Database", return_value=MagicMock()),
                patch("sif.cli.commands.search.CollectionRepository", return_value=repo),
                patch("sif.cli.commands.search.SearchPipeline", return_value=pipeline),
                patch(
                    "sif.embedding.manager.EmbeddingManager.from_settings",
                    return_value=manager,
                ),
            ):
                result = CliRunner().invoke(
                    query_cmd,
                    ["query"],
                    obj={"index_path": self._index(tmp_path)},
                )
        finally:
            get_settings.cache_clear()

        assert result.exit_code == 1
        assert "rrf_k" in result.stderr or "rrf_k" in result.output
        assert "Traceback" not in result.output

    @pytest.mark.parametrize("command", ["search", "vsearch"])
    def test_single_source_commands_have_no_weight_flags(self, command: str) -> None:
        """search/vsearch reject the weight flags (D-02 — no-op flags mislead)."""
        from sif.cli.commands.search import search_cmd as bm25_cmd, vsearch_cmd as vec_cmd

        cmd = bm25_cmd if command == "search" else vec_cmd
        for flag in ("--rrf-k", "--bm25-weight", "--vector-weight"):
            result = CliRunner().invoke(cmd, ["foo", flag, "1.0"])
            assert result.exit_code != 0, f"{command} accepted {flag}"


_SUGGEST_DOCS = [
    ("d1", "quantum machine learning algorithms"),
    ("d2", "quantum computing quick quantifiers"),
    ("d3", "studies of machine learning contexts"),
]


def _seed_suggestion_index(tmp_path: Path) -> tuple[Path, Settings]:
    """Real index DB whose porter vocabulary anchors the zero-result battery.

    ``quantm machin`` is a DYM case (quantm has no prefix hit; machin is a
    porter stem); ``quantum studi`` returns nothing while both tokens are
    retrievable — the no-forced-DYM case (D-07).
    """
    settings = Settings(_env_file=None, embedding_dim=8, model_name="test", cache_embeddings=False)
    db_path = tmp_path / "search-suggest.db"
    with patch("sif.config.settings.get_settings", return_value=settings):
        db = Database(db_path)
        db.init_schema()
        now = datetime.now(timezone.utc).isoformat()
        with db.connection:
            conn = db.connection
            conn.execute(
                "INSERT INTO collections (id, name, path, created_at, updated_at)"
                " VALUES ('c1', 'notes', '/vault', ?, ?)",
                (now, now),
            )
            conn.executemany(
                "INSERT INTO documents (id, collection_id, path, filename, title,"
                " content, checksum, mtime, created_at, updated_at)"
                " VALUES (?, 'c1', ?, ?, ?, ?, ?, 1.0, ?, ?)",
                [
                    (
                        doc_id,
                        f"/vault/{doc_id}.md",
                        f"{doc_id}.md",
                        doc_id,
                        body,
                        f"ck-{doc_id}",
                        now,
                        now,
                    )
                    for doc_id, body in _SUGGEST_DOCS
                ],
            )
        db.close()
    return db_path, settings


def _query_log_rows(db_path: Path) -> list[sqlite3.Row]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(
            "SELECT query, result_count, collections FROM query_log ORDER BY created_at"
        ).fetchall()
    finally:
        conn.close()


class TestZeroResultSuggestions:
    """SC2/D-05: zero-result DYM on all three commands, stdout stays pure."""

    @pytest.fixture(autouse=True)
    def isolate_quiet_state(self) -> Generator[None, None, None]:
        """Do not leak process-global quiet/settings state between tests."""
        from sif.utils.logging import set_quiet

        set_quiet(False)
        get_settings.cache_clear()
        yield
        set_quiet(False)
        get_settings.cache_clear()

    @staticmethod
    def _invoke_bm25(
        db_path: Path,
        settings: Settings,
        args: list[str],
        *,
        env: dict[str, str] | None = None,
    ) -> object:
        with patch("sif.config.settings.get_settings", return_value=settings):
            return CliRunner().invoke(search_cmd, args, obj={"index_path": db_path}, env=env)

    @staticmethod
    def _invoke_vsearch(db_path: Path, settings: Settings, args: list[str]) -> object:
        manager = MagicMock()
        manager.embed_single.return_value = [0.0] * 8
        manager._model = MagicMock()
        searcher = MagicMock()
        searcher.search.return_value = []
        with (
            patch("sif.config.settings.get_settings", return_value=settings),
            patch("sif.embedding.manager.EmbeddingManager.from_settings", return_value=manager),
            patch("sif.search.vector.VectorSearcher", return_value=searcher),
        ):
            return CliRunner().invoke(vsearch_cmd, args, obj={"index_path": db_path})

    @staticmethod
    def _invoke_query(db_path: Path, settings: Settings, args: list[str]) -> object:
        manager = MagicMock()
        manager.embed_single.return_value = [0.0] * 8
        manager._model = MagicMock()
        pipeline = MagicMock()
        pipeline.search.return_value = []
        with (
            patch("sif.config.settings.get_settings", return_value=settings),
            patch("sif.embedding.manager.EmbeddingManager.from_settings", return_value=manager),
            patch("sif.cli.commands.search.SearchPipeline", return_value=pipeline),
        ):
            return CliRunner().invoke(query_cmd, args, obj={"index_path": db_path})

    def test_table_mode_shows_dym_after_no_results(self, tmp_path: Path) -> None:
        """sif search: 'No results found.' then 'Did you mean: quantum machin'."""
        db_path, settings = _seed_suggestion_index(tmp_path)

        result = self._invoke_bm25(db_path, settings, ["quantm machin", "--no-refresh"])

        assert result.exit_code == 0, result.output
        assert "No results found." in result.stdout
        assert "Did you mean: quantum machin" in result.stdout

    def test_vsearch_table_mode_shows_dym(self, tmp_path: Path) -> None:
        """vsearch shares the zero-result hook (vocab source, no embedder needed)."""
        db_path, settings = _seed_suggestion_index(tmp_path)

        result = self._invoke_vsearch(db_path, settings, ["quantm machin", "--no-refresh"])

        assert result.exit_code == 0, result.output
        assert "Did you mean: quantum machin" in result.stdout

    def test_query_table_mode_shows_dym(self, tmp_path: Path) -> None:
        """query shares the zero-result hook after the pipeline returns nothing."""
        db_path, settings = _seed_suggestion_index(tmp_path)

        result = self._invoke_query(db_path, settings, ["quantm machin", "--no-refresh"])

        assert result.exit_code == 0, result.output
        assert "Did you mean: quantum machin" in result.stdout

    @pytest.mark.parametrize("flag", ["--csv", "--md", "--xml", "--files"])
    def test_machine_modes_keep_suggestions_off_stdout(self, tmp_path: Path, flag: str) -> None:
        """CSV/MD/XML/files route the suggestion to stderr only (stdout purity)."""
        db_path, settings = _seed_suggestion_index(tmp_path)

        result = self._invoke_bm25(db_path, settings, ["quantm machin", "--no-refresh", flag])

        assert result.exit_code == 0, result.output
        assert "Did you mean" not in result.stdout
        assert "Did you mean" in result.stderr

    def test_zero_result_json_wraps_suggestions_or_keeps_plain_array(self, tmp_path: Path) -> None:
        """Conditional object with suggestions; plain [] when no DYM (Pitfall 5)."""
        db_path, settings = _seed_suggestion_index(tmp_path)

        with_suggestions = self._invoke_bm25(
            db_path, settings, ["quantm machin", "--json", "--no-refresh"]
        )
        without_suggestions = self._invoke_bm25(
            db_path, settings, ["quantum studi", "--json", "--no-refresh"]
        )

        assert with_suggestions.exit_code == 0, with_suggestions.output
        payload = json.loads(with_suggestions.stdout)
        assert payload["query"] == "quantm machin"
        assert payload["results"] == []
        assert payload["suggestions"] == ["quantum machin"]

        assert without_suggestions.exit_code == 0, without_suggestions.output
        assert json.loads(without_suggestions.stdout) == []

    def test_quiet_zero_result_prints_no_dym(self, tmp_path: Path) -> None:
        """-q gates the DYM line exactly like 'No results found.'."""
        db_path, settings = _seed_suggestion_index(tmp_path)

        result = self._invoke_bm25(db_path, settings, ["quantm machin", "-q", "--no-refresh"])

        assert result.exit_code == 0
        assert "Did you mean" not in result.output


class TestQueryHistoryWrite:
    """D-08/D-09: executed CLI searches log one row; opt-out and failures are safe."""

    @pytest.fixture(autouse=True)
    def isolate_quiet_state(self) -> Generator[None, None, None]:
        from sif.utils.logging import set_quiet

        set_quiet(False)
        get_settings.cache_clear()
        yield
        set_quiet(False)
        get_settings.cache_clear()

    def test_search_writes_one_row_with_results_and_collections(self, tmp_path: Path) -> None:
        """sif search 'quantum' logs (query, result count, collections)."""
        db_path, settings = _seed_suggestion_index(tmp_path)

        result = TestZeroResultSuggestions._invoke_bm25(
            db_path, settings, ["quantum", "--no-refresh"]
        )

        assert result.exit_code == 0, result.output
        rows = _query_log_rows(db_path)
        assert len(rows) == 1
        assert rows[0]["query"] == "quantum"
        assert rows[0]["result_count"] == 2
        assert json.loads(rows[0]["collections"]) == ["notes"]

    @pytest.mark.parametrize("command", ["vsearch", "query"])
    def test_vsearch_and_query_write_a_row(self, tmp_path: Path, command: str) -> None:
        """The other two executed searches log exactly one row as well."""
        db_path, settings = _seed_suggestion_index(tmp_path)
        invoke = (
            TestZeroResultSuggestions._invoke_vsearch
            if command == "vsearch"
            else TestZeroResultSuggestions._invoke_query
        )

        result = invoke(db_path, settings, ["quantum", "--no-refresh"])

        assert result.exit_code == 0, result.output
        rows = _query_log_rows(db_path)
        assert len(rows) == 1
        assert rows[0]["query"] == "quantum"
        assert json.loads(rows[0]["collections"]) == ["notes"]

    def test_quiet_search_still_writes(self, tmp_path: Path) -> None:
        """-q only silences display; the search executed, so history logs."""
        db_path, settings = _seed_suggestion_index(tmp_path)

        result = TestZeroResultSuggestions._invoke_bm25(
            db_path, settings, ["quantum", "-q", "--no-refresh"]
        )

        assert result.exit_code == 0
        assert len(_query_log_rows(db_path)) == 1

    def test_history_disabled_writes_nothing(self, tmp_path: Path) -> None:
        """SIF_QUERY_HISTORY_ENABLED=0 skips the write entirely (D-10)."""
        db_path, _settings = _seed_suggestion_index(tmp_path)
        env = {
            "SIF_EMBEDDING_DIM": "8",
            "SIF_MODEL_NAME": "test",
            "SIF_QUERY_HISTORY_ENABLED": "0",
        }
        try:
            get_settings.cache_clear()
            result = CliRunner().invoke(
                search_cmd,
                ["quantum", "--no-refresh"],
                obj={"index_path": db_path},
                env=env,
            )
        finally:
            get_settings.cache_clear()

        assert result.exit_code == 0, result.output
        assert _query_log_rows(db_path) == []

    def test_history_write_failure_never_fails_search(self, tmp_path: Path) -> None:
        """A raising QueryLogRepository is fail-soft (Pitfall 10)."""
        db_path, settings = _seed_suggestion_index(tmp_path)
        broken = MagicMock()
        broken.return_value.add.side_effect = RuntimeError("history unavailable")

        with patch("sif.cli.commands.search.QueryLogRepository", broken):
            result = TestZeroResultSuggestions._invoke_bm25(
                db_path, settings, ["quantum", "--no-refresh"]
            )

        assert result.exit_code == 0, result.output
        assert "quantum" in result.stdout

    def test_suggestion_failure_never_fails_zero_result_search(self, tmp_path: Path) -> None:
        """An exploding engine degrades to no DYM; the notice still prints."""
        db_path, settings = _seed_suggestion_index(tmp_path)

        with patch("sif.cli.commands.search.SuggestionEngine", side_effect=RuntimeError("boom")):
            result = TestZeroResultSuggestions._invoke_bm25(
                db_path, settings, ["quantm machin", "--no-refresh"]
            )

        assert result.exit_code == 0, result.output
        assert "No results found." in result.stdout
        assert "Did you mean" not in result.stdout
