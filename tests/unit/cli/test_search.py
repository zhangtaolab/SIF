"""Tests for search CLI commands."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from docsift.cli.commands.search import query_cmd, search_cmd, vsearch_cmd
from docsift.core.models import Collection


class TestSearchFiltering:
    """Tests for search collection filtering."""

    def test_search_respects_include_by_default(self):
        """search_cmd filters to enabled collections without --all."""
        runner = CliRunner()

        enabled_coll = Collection(
            id="coll1", name="enabled", path="/notes", include_by_default=True
        )

        mock_repo = MagicMock()
        mock_repo.list_enabled.return_value = [enabled_coll]

        mock_searcher = MagicMock()
        mock_searcher.search.return_value = []

        mock_db = MagicMock()

        with (
            patch("docsift.cli.commands.search.Database", return_value=mock_db),
            patch(
                "docsift.cli.commands.search.CollectionRepository",
                return_value=mock_repo,
            ),
            patch(
                "docsift.cli.commands.search.BM25Searcher",
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
            patch("docsift.cli.commands.search.Database", return_value=mock_db),
            patch(
                "docsift.cli.commands.search.CollectionRepository",
                return_value=mock_repo,
            ),
            patch(
                "docsift.cli.commands.search.BM25Searcher",
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
            id="coll1", name="enabled", path="/notes", include_by_default=True
        )

        mock_repo = MagicMock()
        mock_repo.list_enabled.return_value = [enabled_coll]

        mock_searcher = MagicMock()
        mock_searcher.search.return_value = []

        mock_db = MagicMock()

        with (
            patch("docsift.cli.commands.search.Database", return_value=mock_db),
            patch(
                "docsift.cli.commands.search.CollectionRepository",
                return_value=mock_repo,
            ),
            patch(
                "docsift.cli.commands.search.HybridSearcher",
                return_value=mock_searcher,
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
            id="coll1", name="enabled", path="/notes", include_by_default=True
        )

        mock_repo = MagicMock()
        mock_repo.list_enabled.return_value = [enabled_coll]

        mock_searcher = MagicMock()
        mock_searcher.search.return_value = []

        mock_embedder = MagicMock()
        mock_embedder.dimension = 384
        mock_embedder.embed.return_value = [0.0] * 384

        mock_db = MagicMock()

        with (
            patch("docsift.database.database.Database", return_value=mock_db),
            patch(
                "docsift.database.repositories.CollectionRepository",
                return_value=mock_repo,
            ),
            patch(
                "docsift.embedding.embedder.SentenceTransformerEmbedder",
                return_value=mock_embedder,
            ),
            patch(
                "docsift.search.vector.VectorSearcher",
                return_value=mock_searcher,
            ),
            patch(
                "docsift.config.settings.get_settings",
                return_value=MagicMock(model_name="all-MiniLM-L6-v2"),
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
