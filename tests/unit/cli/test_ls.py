"""Tests for top-level ls CLI command."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner, Result

from sif.cli.commands.ls import ls_cmd


class TestLsCommand:
    """Tests for sif ls command."""

    def test_ls_no_index(self):
        """Test ls when index does not exist."""
        runner = CliRunner()

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = False

        result = runner.invoke(ls_cmd, obj={"index_path": mock_index_path})

        assert result.exit_code == 0
        assert "No index found" in result.output

    def test_ls_all_collections(self):
        """Test ls lists all collections and documents."""
        runner = CliRunner()

        mock_coll_a = MagicMock()
        mock_coll_a.id = "coll-a"
        mock_coll_a.name = "notes"

        mock_coll_b = MagicMock()
        mock_coll_b.id = "coll-b"
        mock_coll_b.name = "docs"

        mock_doc_a = MagicMock()
        mock_doc_a.path = "notes/a.md"

        mock_doc_b = MagicMock()
        mock_doc_b.path = "notes/b.md"

        mock_doc_c = MagicMock()
        mock_doc_c.path = "docs/readme.md"

        def mock_list_by_collection(coll_id):
            if coll_id == "coll-a":
                return [mock_doc_a, mock_doc_b]
            if coll_id == "coll-b":
                return [mock_doc_c]
            return []

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = True

        with (
            patch("sif.cli.commands.ls.Database") as mock_db_cls,
            patch("sif.cli.commands.ls.DocumentRepository") as mock_doc_repo_cls,
            patch("sif.cli.commands.ls.CollectionRepository") as mock_coll_repo_cls,
        ):
            mock_db = MagicMock()
            mock_db.connection.__enter__ = MagicMock(return_value=mock_db.connection)
            mock_db.connection.__exit__ = MagicMock(return_value=False)
            mock_db_cls.return_value = mock_db

            mock_coll_repo = MagicMock()
            mock_coll_repo.list_all.return_value = [mock_coll_a, mock_coll_b]
            mock_coll_repo_cls.return_value = mock_coll_repo

            mock_doc_repo = MagicMock()
            mock_doc_repo.list_by_collection.side_effect = mock_list_by_collection
            mock_doc_repo_cls.return_value = mock_doc_repo

            result = runner.invoke(ls_cmd, obj={"index_path": mock_index_path})

        assert result.exit_code == 0
        assert "notes" in result.output
        assert "docs" in result.output
        assert "a.md" in result.output
        assert "b.md" in result.output
        assert "readme.md" in result.output

    def test_ls_specific_collection(self):
        """Test ls with a specific collection name."""
        runner = CliRunner()

        mock_coll = MagicMock()
        mock_coll.id = "coll-notes"
        mock_coll.name = "notes"

        mock_doc = MagicMock()
        mock_doc.path = "ideas/x.md"

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = True

        with (
            patch("sif.cli.commands.ls.Database") as mock_db_cls,
            patch("sif.cli.commands.ls.DocumentRepository") as mock_doc_repo_cls,
            patch("sif.cli.commands.ls.CollectionRepository") as mock_coll_repo_cls,
        ):
            mock_db = MagicMock()
            mock_db.connection.__enter__ = MagicMock(return_value=mock_db.connection)
            mock_db.connection.__exit__ = MagicMock(return_value=False)
            mock_db_cls.return_value = mock_db

            mock_coll_repo = MagicMock()
            mock_coll_repo.get_by_name.return_value = mock_coll
            mock_coll_repo_cls.return_value = mock_coll_repo

            mock_doc_repo = MagicMock()
            mock_doc_repo.list_by_collection.return_value = [mock_doc]
            mock_doc_repo_cls.return_value = mock_doc_repo

            result = runner.invoke(ls_cmd, ["notes"], obj={"index_path": mock_index_path})

        assert result.exit_code == 0
        assert "notes" in result.output
        assert "x.md" in result.output

    def test_ls_with_subpath_filter(self):
        """Test ls with collection and subpath filter."""
        runner = CliRunner()

        mock_coll = MagicMock()
        mock_coll.id = "coll-notes"
        mock_coll.name = "notes"
        mock_coll.path = "/data/notes"

        mock_doc_x = MagicMock()
        mock_doc_x.path = "/data/notes/ideas/x.md"

        mock_doc_y = MagicMock()
        mock_doc_y.path = "/data/notes/done/y.md"

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = True

        with (
            patch("sif.cli.commands.ls.Database") as mock_db_cls,
            patch("sif.cli.commands.ls.DocumentRepository") as mock_doc_repo_cls,
            patch("sif.cli.commands.ls.CollectionRepository") as mock_coll_repo_cls,
        ):
            mock_db = MagicMock()
            mock_db.connection.__enter__ = MagicMock(return_value=mock_db.connection)
            mock_db.connection.__exit__ = MagicMock(return_value=False)
            mock_db_cls.return_value = mock_db

            mock_coll_repo = MagicMock()
            mock_coll_repo.get_by_name.return_value = mock_coll
            mock_coll_repo_cls.return_value = mock_coll_repo

            mock_doc_repo = MagicMock()
            mock_doc_repo.list_by_collection.return_value = [mock_doc_x, mock_doc_y]
            mock_doc_repo_cls.return_value = mock_doc_repo

            result = runner.invoke(ls_cmd, ["notes", "ideas"], obj={"index_path": mock_index_path})

        assert result.exit_code == 0
        assert "x.md" in result.output
        assert "y.md" not in result.output

    def test_ls_collection_not_found(self):
        """Test ls with a non-existent collection name."""
        runner = CliRunner()

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = True

        with (
            patch("sif.cli.commands.ls.Database") as mock_db_cls,
            patch("sif.cli.commands.ls.CollectionRepository") as mock_coll_repo_cls,
        ):
            mock_db = MagicMock()
            mock_db.connection.__enter__ = MagicMock(return_value=mock_db.connection)
            mock_db.connection.__exit__ = MagicMock(return_value=False)
            mock_db_cls.return_value = mock_db

            mock_coll_repo = MagicMock()
            mock_coll_repo.get_by_name.return_value = None
            mock_coll_repo_cls.return_value = mock_coll_repo

            result = runner.invoke(ls_cmd, ["missing"], obj={"index_path": mock_index_path})

        assert result.exit_code != 0
        assert "not found" in result.output

    def _invoke_ls(self, root: str, doc_paths: list[str], args: list[str]) -> Result:
        """Invoke ls with one mocked collection rooted at root and absolute doc paths."""
        runner = CliRunner()

        mock_coll = MagicMock()
        mock_coll.id = "coll-notes"
        mock_coll.name = "notes"
        mock_coll.path = root

        mock_docs = []
        for path in doc_paths:
            mock_doc = MagicMock()
            mock_doc.path = path
            mock_docs.append(mock_doc)

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = True

        with (
            patch("sif.cli.commands.ls.Database") as mock_db_cls,
            patch("sif.cli.commands.ls.DocumentRepository") as mock_doc_repo_cls,
            patch("sif.cli.commands.ls.CollectionRepository") as mock_coll_repo_cls,
        ):
            mock_db = MagicMock()
            mock_db.connection.__enter__ = MagicMock(return_value=mock_db.connection)
            mock_db.connection.__exit__ = MagicMock(return_value=False)
            mock_db_cls.return_value = mock_db

            mock_coll_repo = MagicMock()
            mock_coll_repo.get_by_name.return_value = mock_coll
            mock_coll_repo_cls.return_value = mock_coll_repo

            mock_doc_repo = MagicMock()
            mock_doc_repo.list_by_collection.return_value = mock_docs
            mock_doc_repo_cls.return_value = mock_doc_repo

            return runner.invoke(ls_cmd, args, obj={"index_path": mock_index_path})

    def test_ls_subpath_is_segment_aligned(self) -> None:
        """Relative subpath resolves against the collection root, whole segments only."""
        result = self._invoke_ls(
            "/data/notes",
            ["/data/notes/python/a.md", "/data/notes/python2/b.md"],
            ["notes", "python"],
        )

        assert result.exit_code == 0
        assert "a.md" in result.output
        assert "b.md" not in result.output

    def test_ls_subpath_absolute_is_segment_aligned(self) -> None:
        """Absolute subpath matches whole segments, never a sibling prefix like python2."""
        result = self._invoke_ls(
            "/data/notes",
            ["/data/notes/python/a.md", "/data/notes/python2/b.md"],
            ["notes", "/data/notes/python"],
        )

        assert result.exit_code == 0
        assert "a.md" in result.output
        assert "b.md" not in result.output

    def test_ls_subpath_exact_file(self) -> None:
        """An exact-file subpath selects that document only."""
        result = self._invoke_ls(
            "/data/notes",
            ["/data/notes/python/a.md", "/data/notes/python2/b.md"],
            ["notes", "python/a.md"],
        )

        assert result.exit_code == 0
        assert "a.md" in result.output
        assert "b.md" not in result.output

    def test_ls_subpath_trailing_slash(self) -> None:
        """A trailing-slash subpath selects the same documents as the bare form."""
        result = self._invoke_ls(
            "/data/notes",
            ["/data/notes/python/a.md", "/data/notes/python2/b.md"],
            ["notes", "python/"],
        )

        assert result.exit_code == 0
        assert "a.md" in result.output
        assert "b.md" not in result.output

    def test_ls_subpath_no_match_lists_nothing(self) -> None:
        """A subpath matching nothing exits 0 and lists no documents."""
        result = self._invoke_ls(
            "/data/notes",
            ["/data/notes/python/a.md", "/data/notes/python2/b.md"],
            ["notes", "missing"],
        )

        assert result.exit_code == 0
        assert "a.md" not in result.output
        assert "b.md" not in result.output
