"""Tests for search CLI commands."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from sif.cli.commands.search import query_cmd, search_cmd, vsearch_cmd
from sif.core.models import Collection


class TestSearchFiltering:
    """Tests for search collection filtering."""

    def test_search_respects_include_by_default(self):
        """search_cmd filters to enabled collections without --all."""
        runner = CliRunner()

        enabled_coll = Collection(
            id="coll1", name="enabled", path="/notes", include_by_default=True,
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
            id="coll1", name="enabled", path="/notes", include_by_default=True,
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
            id="coll1", name="enabled", path="/notes", include_by_default=True,
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
