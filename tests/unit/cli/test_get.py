"""Tests for get CLI commands."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from docsift.cli.commands.get import get_group
from docsift.core.models import Collection, Document


class TestMultiGet:
    """Tests for multi-get command."""

    def test_multi_get_comma_separated(self):
        """Test multi-get with comma-separated IDs."""
        runner = CliRunner()

        doc1 = Document(id="doc1", path="/notes/a.md", collection_id="coll1", content="content a")
        doc2 = Document(id="doc2", path="/notes/b.md", collection_id="coll1", content="content b")

        mock_db = MagicMock()
        mock_doc_repo = MagicMock()
        mock_coll_repo = MagicMock()

        def mock_get_by_id(doc_id):
            if doc_id == "doc1":
                return doc1
            if doc_id == "doc2":
                return doc2
            return None

        mock_doc_repo.get_by_id.side_effect = mock_get_by_id
        mock_coll_repo.list_all.return_value = []

        with (
            patch("docsift.cli.commands.get.Database", return_value=mock_db),
            patch(
                "docsift.cli.commands.get.DocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch(
                "docsift.database.repositories.CollectionRepository",
                return_value=mock_coll_repo,
            ),
        ):
            result = runner.invoke(
                get_group,
                ["multi-get", "doc1,doc2"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        assert "Found 2 matching document(s)" in result.output
        assert "/notes/a.md" in result.output
        assert "/notes/b.md" in result.output

    def test_multi_get_glob_pattern(self):
        """Test multi-get with glob pattern."""
        runner = CliRunner()

        doc1 = Document(id="doc1", path="notes/a.md", collection_id="coll1", content="content a")
        doc2 = Document(id="doc2", path="notes/b.md", collection_id="coll1", content="content b")
        doc3 = Document(id="doc3", path="other/c.md", collection_id="coll1", content="content c")

        mock_db = MagicMock()
        mock_doc_repo = MagicMock()
        mock_coll_repo = MagicMock()

        coll = Collection(id="coll1", name="notes", path="/notes")
        mock_coll_repo.list_all.return_value = [coll]
        mock_doc_repo.list_by_collection.return_value = [doc1, doc2, doc3]

        with (
            patch("docsift.cli.commands.get.Database", return_value=mock_db),
            patch(
                "docsift.cli.commands.get.DocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch(
                "docsift.database.repositories.CollectionRepository",
                return_value=mock_coll_repo,
            ),
        ):
            result = runner.invoke(
                get_group,
                ["multi-get", "notes/*.md"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        assert "notes/a.md" in result.output
        assert "notes/b.md" in result.output

    def test_multi_get_single_docid(self):
        """Test multi-get with a single document ID."""
        runner = CliRunner()

        doc1 = Document(id="doc1", path="/notes/a.md", collection_id="coll1", content="content a")

        mock_db = MagicMock()
        mock_doc_repo = MagicMock()
        mock_coll_repo = MagicMock()

        mock_doc_repo.get_by_id.return_value = doc1

        with (
            patch("docsift.cli.commands.get.Database", return_value=mock_db),
            patch(
                "docsift.cli.commands.get.DocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch(
                "docsift.database.repositories.CollectionRepository",
                return_value=mock_coll_repo,
            ),
        ):
            result = runner.invoke(
                get_group,
                ["multi-get", "doc1"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        assert "Found 1 matching document(s)" in result.output
        assert "/notes/a.md" in result.output

    def test_multi_get_no_match(self):
        """Test multi-get with no matching documents."""
        runner = CliRunner()

        mock_db = MagicMock()
        mock_doc_repo = MagicMock()
        mock_coll_repo = MagicMock()

        mock_doc_repo.get_by_id.return_value = None
        mock_doc_repo.get_by_path.return_value = None
        mock_coll_repo.list_all.return_value = []

        with (
            patch("docsift.cli.commands.get.Database", return_value=mock_db),
            patch(
                "docsift.cli.commands.get.DocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch(
                "docsift.database.repositories.CollectionRepository",
                return_value=mock_coll_repo,
            ),
        ):
            result = runner.invoke(
                get_group,
                ["multi-get", "nonexistent"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        assert "No documents matching pattern" in result.output


class TestGetLineNumbers:
    """Tests for --line-numbers flag on get commands."""

    def test_get_with_line_numbers(self):
        """Test get command with --line-numbers flag."""
        runner = CliRunner()

        doc = Document(
            id="doc1",
            path="/notes/a.md",
            collection_id="coll1",
            content="line1\nline2",
        )

        mock_db = MagicMock()
        mock_doc_repo = MagicMock()
        mock_doc_repo.get_by_id.return_value = doc

        with (
            patch("docsift.cli.commands.get.Database", return_value=mock_db),
            patch(
                "docsift.cli.commands.get.DocumentRepository",
                return_value=mock_doc_repo,
            ),
        ):
            result = runner.invoke(
                get_group,
                ["get", "doc1", "--line-numbers"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        assert "   1: line1" in result.output
        assert "   2: line2" in result.output

    def test_multi_get_with_line_numbers(self):
        """Test multi-get command with --line-numbers flag."""
        runner = CliRunner()

        doc = Document(
            id="doc1",
            path="/notes/a.md",
            collection_id="coll1",
            content="line1\nline2",
        )

        mock_db = MagicMock()
        mock_doc_repo = MagicMock()
        mock_coll_repo = MagicMock()

        mock_doc_repo.get_by_id.return_value = doc
        mock_coll_repo.list_all.return_value = []

        with (
            patch("docsift.cli.commands.get.Database", return_value=mock_db),
            patch(
                "docsift.cli.commands.get.DocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch(
                "docsift.database.repositories.CollectionRepository",
                return_value=mock_coll_repo,
            ),
        ):
            result = runner.invoke(
                get_group,
                ["multi-get", "doc1", "--line-numbers"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        assert "   1: line1" in result.output
        assert "   2: line2" in result.output
