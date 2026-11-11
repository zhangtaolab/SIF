"""Tests for get CLI commands."""

import os
from collections.abc import Generator
from pathlib import Path
from typing import ClassVar
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner, Result

from sif.cli.commands.get import get_group
from sif.cli.main import cli
from sif.config.settings import get_settings
from sif.core.models import Collection, Document
from sif.database.database import Database
from sif.database.repositories import CollectionRepository, DocumentRepository
from sif.utils.paths import normalize_path


class TrackingDatabase(Database):
    """Database double recording constructed instances for closure assertions."""

    created: ClassVar[list[Database]] = []

    def __init__(self, db_path: str | Path) -> None:
        """Record each construction so tests can assert every handle closed."""
        super().__init__(db_path)
        TrackingDatabase.created.append(self)


class RealDatabaseTestCase:
    """Production-schema retrieval fixtures confined to temporary storage."""

    @pytest.fixture(autouse=True)
    def isolated_settings(self) -> Generator[None, None, None]:
        """Database schema creation never inherits cached Settings."""
        get_settings.cache_clear()
        yield
        get_settings.cache_clear()

    @pytest.fixture
    def indexed_documents(self, tmp_path: Path) -> tuple[Path, list[Document]]:
        """Create two indexed files and their corresponding database rows."""
        notes = tmp_path / "notes"
        notes.mkdir()
        documents = [
            Document(
                id="doc-1",
                path=str(notes / "alpha.md"),
                collection_id="collection-1",
                title="Alpha",
                content="first line\nsecond line\nthird line",
            ),
            Document(
                id="doc-2",
                path=str(notes / "beta.txt"),
                collection_id="collection-1",
                title=None,
                content="beta content",
            ),
        ]
        for document in documents:
            Path(document.path).write_text(document.content, encoding="utf-8")
        db_path = tmp_path / "sif.db"
        with Database(db_path) as db:
            db.init_schema()
            with db.transaction() as conn:
                CollectionRepository(conn).create(
                    Collection(id="collection-1", name="notes", path=str(notes))
                )
                for document in documents:
                    DocumentRepository(conn).create(document)
        return db_path, documents

    @pytest.fixture
    def alias_documents(self, tmp_path: Path) -> tuple[Path, Path, list[Document]]:
        """Index files under a real directory, then expose a symlink alias of it.

        Stored rows carry the resolved real strings (mirroring the scanner,
        which stores ``normalize_path`` forms), while lookups arrive through
        the alias — the exact asymmetry DEBT-PN describes.
        """
        notes_real = tmp_path / "notes_real"
        notes_real.mkdir()
        documents = [
            Document(
                id="doc-1",
                path=normalize_path(notes_real / "alpha.md"),
                collection_id="collection-1",
                title="Alpha",
                content="first line\nsecond line\nthird line",
            ),
            Document(
                id="doc-2",
                path=normalize_path(notes_real / "beta.txt"),
                collection_id="collection-1",
                title=None,
                content="beta content",
            ),
        ]
        for document in documents:
            Path(document.path).write_text(document.content, encoding="utf-8")
        notes_alias = tmp_path / "notes_alias"
        os.symlink(notes_real, notes_alias)
        db_path = tmp_path / "sif.db"
        with Database(db_path) as db:
            db.init_schema()
            with db.transaction() as conn:
                CollectionRepository(conn).create(
                    Collection(id="collection-1", name="notes", path=str(notes_real))
                )
                for document in documents:
                    DocumentRepository(conn).create(document)
        return db_path, notes_alias, documents

    def _invoke(self, db_path: Path, command: str, argument: str, *options: str) -> Result:
        """Invoke retrieval through the top-level CLI and a tmp_path index."""
        return CliRunner().invoke(
            cli,
            ["--index", str(db_path), "get", command, argument, *options],
            env={"COLUMNS": "200"},
        )


class TestGetRetrieval(RealDatabaseTestCase):
    """Single-get behavior over real document repositories and temporary files."""

    def test_get_by_id_path_and_filename(
        self, indexed_documents: tuple[Path, list[Document]]
    ) -> None:
        """ID, exact path, and short filename resolve to the same stored content."""
        db_path, documents = indexed_documents
        document = documents[0]

        by_id = self._invoke(db_path, "get", document.id)
        by_path = self._invoke(db_path, "get", document.path)
        by_filename = self._invoke(db_path, "get", document.filename)

        for result in (by_id, by_path, by_filename):
            assert result.exit_code == 0, result.output
            assert "Alpha" in result.output
            assert "first line" in result.output
            assert "second line" in result.output

    def test_get_from_line_and_numbered_markdown(
        self, indexed_documents: tuple[Path, list[Document]]
    ) -> None:
        """From-line filtering precedes Markdown rendering and line numbering."""
        db_path, documents = indexed_documents

        result = self._invoke(
            db_path,
            "get",
            documents[0].id,
            "--from-line",
            "2",
            "--line-numbers",
        )

        assert result.exit_code == 0, result.output
        assert "first line" not in result.output
        assert "   1: second line" in result.output
        assert "   2: third line" in result.output

    def test_get_line_range_and_non_markdown(
        self, indexed_documents: tuple[Path, list[Document]]
    ) -> None:
        """A bounded range uses the non-Markdown branch and omits other lines."""
        db_path, documents = indexed_documents

        result = self._invoke(
            db_path,
            "get",
            documents[0].id,
            "--from-line",
            "2",
            "--lines",
            "1",
        )
        plain = self._invoke(db_path, "get", documents[1].id)

        assert result.exit_code == 0, result.output
        assert "second line" in result.output
        assert "first line" not in result.output
        assert "third line" not in result.output
        assert plain.exit_code == 0, plain.output
        assert "beta.txt" in plain.output
        assert "beta content" in plain.output

    def test_get_no_index_and_missing_document(self, tmp_path: Path) -> None:
        """No-index and missing-document cases keep their distinct outcomes."""
        db_path = tmp_path / "sif.db"
        with Database(db_path) as db:
            db.init_schema()

        no_index = self._invoke(tmp_path / "absent.db", "get", "missing.md")
        missing = self._invoke(db_path, "get", "missing.md")

        assert no_index.exit_code == 0, no_index.output
        assert "No index found." in no_index.output
        assert missing.exit_code != 0
        assert "Document not found: missing.md" in missing.stderr

    def test_local_file_fallback_and_read_failure(
        self, indexed_documents: tuple[Path, list[Document]], tmp_path: Path
    ) -> None:
        """Unindexed local files render directly and read errors become Click errors."""
        db_path, _ = indexed_documents
        local_file = tmp_path / "local.md"
        local_file.write_text("local file content", encoding="utf-8")

        fallback = self._invoke(db_path, "get", str(local_file))
        with patch.object(Path, "read_text", side_effect=OSError("simulated read failure")):
            failure = self._invoke(db_path, "get", str(local_file))

        assert fallback.exit_code == 0, fallback.output
        assert "local file content" in fallback.output
        assert failure.exit_code != 0
        assert "Cannot read file: simulated read failure" in failure.stderr

    def test_disk_fallback_honors_line_options(
        self, indexed_documents: tuple[Path, list[Document]], tmp_path: Path
    ) -> None:
        """--lines/--line-numbers apply on the disk-fallback path too (CR-02)."""
        db_path, _ = indexed_documents
        local_file = tmp_path / "five_lines.md"
        local_file.write_text(
            "line one\nline two\nline three\nline four\nline five", encoding="utf-8"
        )

        result = self._invoke(db_path, "get", str(local_file), "--lines", "2", "--line-numbers")

        assert result.exit_code == 0, result.output
        assert "   1: line one" in result.output
        assert "   2: line two" in result.output
        assert "line three" not in result.output
        assert "line five" not in result.output


class TestMarkupLiteralContent(RealDatabaseTestCase):
    """CR-01 regressions: document content prints raw, never as Rich markup."""

    @pytest.fixture
    def markup_documents(self, tmp_path: Path) -> tuple[Path, list[Document]]:
        """Index documents whose content contains markup-hostile bracket sequences."""
        notes = tmp_path / "notes"
        notes.mkdir()
        documents = [
            Document(
                id="doc-m1",
                path=str(notes / "hostile.md"),
                collection_id="collection-1",
                title="Hostile",
                content="see [/bold] and [link](https://example.com) here",
            ),
            Document(
                id="doc-m2",
                path=str(notes / "plain.md"),
                collection_id="collection-1",
                title="Plain",
                content="plain second document",
            ),
            Document(
                id="doc-m3",
                path=str(notes / "note [draft].md"),
                collection_id="collection-1",
                title="Hostile [/bold] title",
                content="bracketed header document",
            ),
        ]
        for document in documents:
            Path(document.path).write_text(document.content, encoding="utf-8")
        db_path = tmp_path / "sif.db"
        with Database(db_path) as db:
            db.init_schema()
            with db.transaction() as conn:
                CollectionRepository(conn).create(
                    Collection(id="collection-1", name="notes", path=str(notes))
                )
                for document in documents:
                    DocumentRepository(conn).create(document)
        return db_path, documents

    def test_single_get_bracket_content_renders_literally(
        self, markup_documents: tuple[Path, list[Document]]
    ) -> None:
        """Unmatched closing tags must not crash and link syntax must not be consumed."""
        db_path, documents = markup_documents

        result = self._invoke(db_path, "get", documents[0].id)

        assert result.exit_code == 0, result.output
        assert "[/bold]" in result.output
        assert "[link](https://example.com)" in result.output

    def test_multi_get_batch_survives_markup_hostile_document(
        self, markup_documents: tuple[Path, list[Document]]
    ) -> None:
        """One markup-hostile document must not abort the rest of the batch."""
        db_path, documents = markup_documents

        result = self._invoke(db_path, "multi-get", f"{documents[0].id},{documents[1].id}")

        assert result.exit_code == 0, result.output
        assert "[/bold]" in result.output
        assert "plain second document" in result.output

    def test_hostile_title_and_bracketed_filename_render_literally(
        self, markup_documents: tuple[Path, list[Document]]
    ) -> None:
        """10-delta CR-01: header lines escape user-derived title/path text."""
        db_path, documents = markup_documents
        hostile = documents[2]

        single = self._invoke(db_path, "get", hostile.id)
        batch = self._invoke(db_path, "multi-get", hostile.id)

        # Single get prints the title header; multi-get prints only the
        # `=== path ===` header — assert each surface's own literals.
        assert single.exit_code == 0, single.output
        assert "Hostile [/bold] title" in single.output
        assert "note [draft].md" in single.output
        assert batch.exit_code == 0, batch.output
        assert "note [draft].md" in batch.output


class TestMultiGetRetrieval(RealDatabaseTestCase):
    """Batch selection and output behavior against real SQLite."""

    @pytest.fixture
    def multibyte_documents(self, tmp_path: Path) -> tuple[Path, list[Document]]:
        """Index CJK and emoji documents for byte-boundary truncation tests."""
        notes = tmp_path / "notes"
        notes.mkdir()
        documents = [
            Document(
                id="doc-cjk",
                path=str(notes / "cjk.md"),
                collection_id="collection-1",
                title="CJK",
                content="中" * 20,
            ),
            Document(
                id="doc-emoji",
                path=str(notes / "emoji.md"),
                collection_id="collection-1",
                title="Emoji",
                content="😀" * 10,
            ),
        ]
        for document in documents:
            Path(document.path).write_text(document.content, encoding="utf-8")
        db_path = tmp_path / "sif.db"
        with Database(db_path) as db:
            db.init_schema()
            with db.transaction() as conn:
                CollectionRepository(conn).create(
                    Collection(id="collection-1", name="notes", path=str(notes))
                )
                for document in documents:
                    DocumentRepository(conn).create(document)
        return db_path, documents

    def test_multi_get_max_bytes_cjk_respects_byte_budget(
        self, multibyte_documents: tuple[Path, list[Document]]
    ) -> None:
        """CJK truncation drops a partial character at the byte boundary."""
        db_path, documents = multibyte_documents

        result = self._invoke(
            db_path, "multi-get", documents[0].id, "--max-bytes", "10"
        )

        assert result.exit_code == 0, result.output
        assert result.output.count("中") == 3
        assert "... [truncated]" in result.output
        assert "中" * 4 not in result.output

    def test_multi_get_max_bytes_emoji_respects_byte_budget(
        self, multibyte_documents: tuple[Path, list[Document]]
    ) -> None:
        """Emoji truncation never emits a split or replacement character."""
        db_path, documents = multibyte_documents

        result = self._invoke(
            db_path, "multi-get", documents[1].id, "--max-bytes", "6"
        )

        assert result.exit_code == 0, result.output
        assert result.output.count("😀") == 1
        assert "... [truncated]" in result.output
        assert "😀" * 2 not in result.output
        assert "�" not in result.output

    def test_multi_get_under_limit_content_unchanged(
        self, multibyte_documents: tuple[Path, list[Document]]
    ) -> None:
        """Multibyte content below the byte budget passes through unchanged."""
        db_path, documents = multibyte_documents

        result = self._invoke(
            db_path, "multi-get", documents[0].id, "--max-bytes", "1000"
        )

        assert result.exit_code == 0, result.output
        assert result.output.count("中") == 20
        assert "... [truncated]" not in result.output

    def test_comma_separated_lookup_deduplicates_documents(
        self, indexed_documents: tuple[Path, list[Document]]
    ) -> None:
        """Comma lookup resolves IDs/paths/names but returns each document once."""
        db_path, documents = indexed_documents
        document = documents[0]
        pattern = f"{document.id},{document.path},{document.filename},{documents[1].id}"

        result = self._invoke(db_path, "multi-get", pattern)

        assert result.exit_code == 0, result.output
        assert "Found 2 matching document(s)" in result.output
        assert result.output.count("=== ") == 2
        assert "first line" in result.output
        assert "beta content" in result.output

    def test_glob_and_single_item_lookup(
        self, indexed_documents: tuple[Path, list[Document]]
    ) -> None:
        """Glob matching and a single item both return exact indexed content."""
        db_path, documents = indexed_documents

        globbed = self._invoke(db_path, "multi-get", "*.md")
        single = self._invoke(db_path, "multi-get", documents[1].filename)
        empty = self._invoke(db_path, "multi-get", "*.rst")

        assert globbed.exit_code == 0, globbed.output
        assert "Found 1 matching document(s)" in globbed.output
        assert documents[0].path in globbed.output
        assert "beta content" not in globbed.output
        assert single.exit_code == 0, single.output
        assert "beta content" in single.output
        assert empty.exit_code == 0, empty.output
        assert "No documents matching pattern: *.rst" in empty.output

    def test_max_bytes_truncation_and_line_numbers(
        self, indexed_documents: tuple[Path, list[Document]]
    ) -> None:
        """Batch output honors byte limits and numbering in one command path."""
        db_path, documents = indexed_documents

        result = self._invoke(
            db_path,
            "multi-get",
            documents[0].id,
            "--max-bytes",
            "5",
            "--line-numbers",
        )

        assert result.exit_code == 0, result.output
        assert "   1: first" in result.output
        assert "   2: ..." in result.output
        assert "second line" not in result.output

    def test_multi_get_no_index(self, tmp_path: Path) -> None:
        """Batch lookup also returns early when its temporary index is absent."""
        result = self._invoke(tmp_path / "absent.db", "multi-get", "*.md")

        assert result.exit_code == 0, result.output
        assert "No index found." in result.output


class TestAliasPathResolution(RealDatabaseTestCase):
    """Symlink-alias paths resolve to indexed documents stored under real paths."""

    def test_get_by_alias_path_hits_index(
        self, alias_documents: tuple[Path, Path, list[Document]]
    ) -> None:
        """An alias path is canonicalized to the stored real path before lookup.

        The ``Collection:`` header proves the index row matched — the disk
        fallback prints no collection line.
        """
        db_path, notes_alias, documents = alias_documents

        result = self._invoke(db_path, "get", str(notes_alias / "alpha.md"))

        assert result.exit_code == 0, result.output
        assert "first line" in result.output
        assert "Collection: collection-1" in result.output
        assert f"Path: {documents[0].path}" in result.output

    def test_multi_get_alias_list_and_raw_id(
        self, alias_documents: tuple[Path, Path, list[Document]]
    ) -> None:
        """A comma list resolves an alias path and a raw document ID together."""
        db_path, notes_alias, documents = alias_documents

        result = self._invoke(db_path, "multi-get", f"{notes_alias / 'alpha.md'},{documents[1].id}")

        assert result.exit_code == 0, result.output
        assert "Found 2 matching document(s)" in result.output
        assert "first line" in result.output
        assert "beta content" in result.output

    def test_multi_get_alias_glob_pattern(
        self, alias_documents: tuple[Path, Path, list[Document]]
    ) -> None:
        """An absolute glob with a symlinked directory prefix matches stored paths."""
        db_path, notes_alias, documents = alias_documents

        result = self._invoke(db_path, "multi-get", str(notes_alias / "*.md"))

        assert result.exit_code == 0, result.output
        assert "Found 1 matching document(s)" in result.output
        assert documents[0].path in result.output
        assert "beta content" not in result.output

    def test_id_and_filename_lookups_unchanged(
        self, alias_documents: tuple[Path, Path, list[Document]]
    ) -> None:
        """ID-first and bare-filename lookups keep resolving (control)."""
        db_path, _notes_alias, documents = alias_documents

        by_id = self._invoke(db_path, "get", documents[0].id)
        by_filename = self._invoke(db_path, "multi-get", documents[1].filename)

        assert by_id.exit_code == 0, by_id.output
        assert "first line" in by_id.output
        assert by_filename.exit_code == 0, by_filename.output
        assert "beta content" in by_filename.output


class TestDatabaseClosure(RealDatabaseTestCase):
    """get and multi-get own their Database lifecycle end to end."""

    def test_get_closes_database_on_success(
        self,
        alias_documents: tuple[Path, Path, list[Document]],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Every Database constructed by get is closed after a successful run."""
        db_path, notes_alias, _documents = alias_documents
        TrackingDatabase.created.clear()
        monkeypatch.setattr("sif.cli.commands.get.Database", TrackingDatabase)

        result = self._invoke(db_path, "get", str(notes_alias / "alpha.md"))

        assert result.exit_code == 0, result.output
        assert TrackingDatabase.created, "get must construct its Database"
        for instance in TrackingDatabase.created:
            assert instance._connection is None

    def test_get_closes_database_on_exception(
        self,
        alias_documents: tuple[Path, Path, list[Document]],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A repository failure still closes every Database get constructed."""
        db_path, _notes_alias, documents = alias_documents
        TrackingDatabase.created.clear()
        monkeypatch.setattr("sif.cli.commands.get.Database", TrackingDatabase)

        with patch.object(DocumentRepository, "get_by_id", side_effect=RuntimeError("boom")):
            result = self._invoke(db_path, "get", documents[0].id)

        assert result.exit_code != 0
        assert TrackingDatabase.created, "get must construct its Database"
        for instance in TrackingDatabase.created:
            assert instance._connection is None

    def test_multi_get_closes_database_on_success(
        self,
        alias_documents: tuple[Path, Path, list[Document]],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Every Database constructed by multi-get is closed after a successful run."""
        db_path, notes_alias, _documents = alias_documents
        TrackingDatabase.created.clear()
        monkeypatch.setattr("sif.cli.commands.get.Database", TrackingDatabase)

        result = self._invoke(db_path, "multi-get", str(notes_alias / "*.md"))

        assert result.exit_code == 0, result.output
        assert TrackingDatabase.created, "multi-get must construct its Database"
        for instance in TrackingDatabase.created:
            assert instance._connection is None

    def test_multi_get_closes_database_on_exception(
        self,
        alias_documents: tuple[Path, Path, list[Document]],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A repository failure still closes every Database multi-get constructed."""
        db_path, _notes_alias, documents = alias_documents
        TrackingDatabase.created.clear()
        monkeypatch.setattr("sif.cli.commands.get.Database", TrackingDatabase)

        with patch.object(DocumentRepository, "get_by_id", side_effect=RuntimeError("boom")):
            result = self._invoke(db_path, "multi-get", documents[0].id)

        assert result.exit_code != 0
        assert TrackingDatabase.created, "multi-get must construct its Database"
        for instance in TrackingDatabase.created:
            assert instance._connection is None


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
            patch("sif.cli.commands.get.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.get.DocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch(
                "sif.database.repositories.CollectionRepository",
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
            patch("sif.cli.commands.get.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.get.DocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch(
                "sif.database.repositories.CollectionRepository",
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
            patch("sif.cli.commands.get.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.get.DocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch(
                "sif.database.repositories.CollectionRepository",
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
        mock_doc_repo.get_by_filename.return_value = None
        mock_coll_repo.list_all.return_value = []

        with (
            patch("sif.cli.commands.get.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.get.DocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch(
                "sif.database.repositories.CollectionRepository",
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

    def test_multi_get_by_filename(self):
        """Test multi-get with short filename lookup."""
        runner = CliRunner()

        doc1 = Document(id="doc1", path="/notes/a.md", collection_id="coll1", content="content a")

        mock_db = MagicMock()
        mock_doc_repo = MagicMock()
        mock_coll_repo = MagicMock()

        mock_doc_repo.get_by_id.return_value = None
        mock_doc_repo.get_by_path.return_value = None
        mock_doc_repo.get_by_filename.return_value = doc1
        mock_coll_repo.list_all.return_value = []

        with (
            patch("sif.cli.commands.get.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.get.DocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch(
                "sif.database.repositories.CollectionRepository",
                return_value=mock_coll_repo,
            ),
        ):
            result = runner.invoke(
                get_group,
                ["multi-get", "a.md"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        assert "Found 1 matching document(s)" in result.output
        assert "/notes/a.md" in result.output


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
            patch("sif.cli.commands.get.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.get.DocumentRepository",
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
            patch("sif.cli.commands.get.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.get.DocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch(
                "sif.database.repositories.CollectionRepository",
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
