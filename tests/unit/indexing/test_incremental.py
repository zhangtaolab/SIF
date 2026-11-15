"""Unit tests for the shared IncrementalIndexer core (roadmap SC3 / D-04).

The indexer is the one incremental loop extracted from ``update_cmd``: same
scan → checksum-diff → parse → write behavior, but each file's writes commit
as one short BEGIN IMMEDIATE transaction so a mid-run failure keeps completed
files durable (D-04) instead of rolling back the whole run.

CORR-01/D-08: parser selection is per file (``create_parser(file_path)`` with a
``TextParser`` fallback) and the create path stores the parser's checksum —
body plus canonical full frontmatter. The old body-only convention is
intentionally retired.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sif.config.settings import Settings
from sif.core.filters import parse_filter
from sif.core.models import Collection, Document, DocumentChunk, compute_checksum
from sif.database.database import Database
from sif.database.repositories import (
    CollectionRepository,
    DocumentChunkRepository,
    DocumentRepository,
    IndexMetaRepository,
)
from sif.indexing.incremental import IncrementalIndexer, IncrementalResult
from sif.indexing.parser import CONVENTION_VERSION
from sif.indexing.scanner import FileScanner
from sif.search.filters import count_matching_documents


BODY_ALPHA = "# Heading One\n\n" + ("Alpha paragraph text. " * 50)
BODY_BETA = "# Heading Two\n\n" + ("Beta paragraph text. " * 50)


def _delenv_settings_vars(monkeypatch) -> None:
    """Keep Settings construction hermetic against a developer shell."""
    for var in ("SIF_EMBEDDING_DIM", "SIF_MODEL_TYPE", "SIF_MODEL_NAME"):
        monkeypatch.delenv(var, raising=False)


def _test_settings() -> Settings:
    """Build hermetic test settings."""
    return Settings(embedding_dim=8, model_name="test", cache_embeddings=False)


def _seed_collection(db_path: Path, notes: Path, pattern: str = "**/*.md") -> str:
    """Init schema and create one collection pointing at ``notes``; return its id."""
    from sif.core.models import Collection as Coll

    db = Database(db_path)
    with patch("sif.config.settings.get_settings", return_value=_test_settings()):
        db.init_schema()
        with db.connection:
            coll_repo = CollectionRepository(db.connection)
            coll = Coll(name="notes", path=str(notes), pattern=pattern)
            coll_repo.create(coll)
            coll_id = coll.id
    db.close()
    return coll_id


def _open_indexer(db_path: Path) -> tuple[IncrementalIndexer, Database, Collection]:
    """Open the DB, load the seeded collection, and build an indexer."""
    db = Database(db_path)
    coll_repo = CollectionRepository(db.connection)
    coll = coll_repo.get_by_name("notes")
    assert coll is not None
    return IncrementalIndexer(db.connection), db, coll


def _doc_paths(db_path: Path) -> set[str]:
    """Read document paths through a fresh connection (Pitfall 5: query, not files)."""
    conn = sqlite3.connect(str(db_path))
    try:
        return {row[0] for row in conn.execute("SELECT path FROM documents")}
    finally:
        conn.close()


def _doc_row(db_path: Path, path: str) -> tuple[str, str, str]:
    """Return (title, content, checksum) for one document path via a fresh connection."""
    conn = sqlite3.connect(str(db_path))
    try:
        return conn.execute(
            "SELECT title, content, checksum FROM documents WHERE path = ?", (path,)
        ).fetchone()
    finally:
        conn.close()


def _doc_metadata(db_path: Path, path: str) -> str:
    """Return the raw stored metadata JSON for one document path."""
    conn = sqlite3.connect(str(db_path))
    try:
        return conn.execute("SELECT metadata FROM documents WHERE path = ?", (path,)).fetchone()[0]
    finally:
        conn.close()


def _doc_fields(db_path: Path, path: str) -> dict[str, object]:
    """Return the metadata-bearing document columns for one path."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT title, content, checksum, file_size, mtime, metadata "
            "FROM documents WHERE path = ?",
            (path,),
        ).fetchone()
        assert row is not None
        return dict(row)
    finally:
        conn.close()


def _metadata_values(db_path: Path, path: str) -> dict[str, list[object]]:
    """Read the typed kv view for one document path via a fresh connection.

    Values are returned per key in ``ordinal`` order. This reads the table the
    ``MetadataValueRepository`` write path maintains — never the metadata blob —
    so it proves the filterable view moved with the document row.
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT v.key, v.value_type, v.text_value, v.number_value, v.boolean_value "
            "FROM document_metadata_values v "
            "JOIN documents d ON v.document_id = d.id "
            "WHERE d.path = ? ORDER BY v.key, v.ordinal",
            (path,),
        ).fetchall()
    finally:
        conn.close()

    values: dict[str, list[object]] = {}
    for row in rows:
        if row["value_type"] == "string":
            value: object = row["text_value"]
        elif row["value_type"] == "number":
            value = row["number_value"]
        else:
            value = bool(row["boolean_value"])
        values.setdefault(row["key"], []).append(value)
    return values


def _metadata_skips(db_path: Path, path: str) -> dict[str, str]:
    """Read the D-07 skip sidecar for one document path via a fresh connection."""
    conn = sqlite3.connect(str(db_path))
    try:
        return {
            row[0]: row[1]
            for row in conn.execute(
                "SELECT s.key, s.reason FROM document_metadata_skips s "
                "JOIN documents d ON s.document_id = d.id WHERE d.path = ?",
                (path,),
            )
        }
    finally:
        conn.close()


def _reject_json_constant(token: str) -> None:
    """``json.loads`` parse_constant hook that refuses NaN/Infinity tokens."""
    raise AssertionError(f"non-standard JSON token: {token}")


def _seed_chunk_and_embedding(db: Database, collection_id: str, doc_path: str) -> None:
    """Simulate a prior embed pass: one chunk row plus one vec0 vector."""
    from sif.search.vector import VectorSearcher

    doc = DocumentRepository(db.connection).get_by_path(doc_path, collection_id)
    assert doc is not None
    with db.connection:
        DocumentChunkRepository(db.connection).create(
            DocumentChunk(
                content="chunk of the stored body",
                sequence=0,
                start_pos=0,
                end_pos=10,
                document_id=doc.id,
            )
        )
        VectorSearcher(db.connection, embedding_dim=8).add_embedding(
            f"e-{doc.id}", doc.id, f"c-{doc.id}", [0.1] * 8
        )


def _marker(db_path: Path, collection_id: str) -> str | None:
    """Read the persisted convention marker through a fresh connection."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        return IndexMetaRepository(conn).get(f"convention:{collection_id}")
    finally:
        conn.close()


def _downgrade_to_legacy(db_path: Path, collection_id: str, doc_path: str) -> None:
    """Simulate a pre-D-08 index: body-only checksum and no convention marker."""
    _title, stored_content, _checksum = _doc_row(db_path, doc_path)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "UPDATE documents SET checksum = ? WHERE path = ?",
            (hashlib.sha256(stored_content.encode()).hexdigest(), doc_path),
        )
        conn.execute("DELETE FROM index_meta WHERE key = ?", (f"convention:{collection_id}",))
        conn.commit()
    finally:
        conn.close()


def _chunk_contents(db_path: Path, doc_path: str) -> list[str]:
    """Return chunk contents for a document path via a fresh connection."""
    conn = sqlite3.connect(str(db_path))
    try:
        return [
            row[0]
            for row in conn.execute(
                "SELECT dc.content FROM document_chunks dc "
                "JOIN documents d ON dc.document_id = d.id "
                "WHERE d.path = ? ORDER BY dc.sequence",
                (doc_path,),
            )
        ]
    finally:
        conn.close()


def _embedding_count(db_path: Path) -> int:
    """Count document_embeddings rows via a fresh connection.

    The vec0 virtual table needs the sqlite-vec module loaded on the reading
    connection; the count skips only when the extension itself is absent
    (the same best-effort contract as the rest of the suite).
    """
    try:
        import sqlite_vec
    except ImportError:
        pytest.skip("sqlite-vec not available")
    conn = sqlite3.connect(str(db_path))
    try:
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return conn.execute("SELECT COUNT(*) FROM document_embeddings").fetchone()[0]
    finally:
        conn.close()


class TestIncrementalIndexer:
    """The per-file incremental loop extracted from update_cmd (SC3, D-04)."""

    def test_new_file_added_and_document_row_exists(self, tmp_path, monkeypatch) -> None:
        """A new file on disk is added: result.added == 1 and the row is durable."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "incr.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "a.md").write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            events: list[str] = []
            result = indexer.update_collection(coll, progress=events.append)
        finally:
            db.close()

        assert result == IncrementalResult(added=1, updated=0, removed=0)
        assert str(notes / "a.md") in _doc_paths(db_path)
        title, content, checksum = _doc_row(db_path, str(notes / "a.md"))
        assert title == "Heading One"
        # frontmatter.loads normalizes the body's trailing whitespace, matching
        # the pre-extraction loop (the stored content is parsed.content).
        assert content == BODY_ALPHA.rstrip()
        # D-08: the create path stores the parser's checksum, which covers the
        # body plus canonical frontmatter (empty for this fixture).
        assert checksum == compute_checksum(content, {})
        # The scan event reaches the presentation callback before per-file events.
        assert events[0].startswith("scan ")

    def test_unrepresentable_frontmatter_numbers_never_abort_the_pass(
        self, tmp_path, monkeypatch
    ) -> None:
        """CR-01: a 400-digit integer and ``.nan`` index as per-key skips/strings.

        Before the fix the huge integer raised OverflowError (uncaught, so the
        whole pass aborted) and ``.nan`` either violated the typed-column
        CHECK or wrote a bare ``NaN`` token into ``documents.metadata``.
        """
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "incr.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        # Sorted first, so a fatal error here would hide the healthy trailing file.
        (notes / "aa-huge.md").write_text(
            "---\nbig: " + "9" * 400 + "\nstatus: ok\n---\n# Huge\n\nBody text.\n",
            encoding="utf-8",
        )
        (notes / "ab-nan.md").write_text(
            "---\nbad: .nan\nstatus: ok\n---\n# Nan\n\nBody text.\n",
            encoding="utf-8",
        )
        (notes / "after.md").write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            events: list[str] = []
            result = indexer.update_collection(coll, progress=events.append)
        finally:
            db.close()

        assert result == IncrementalResult(added=3, updated=0, removed=0)
        assert not any(event.startswith("error ") for event in events)
        assert _doc_paths(db_path) == {
            str(notes / "aa-huge.md"),
            str(notes / "ab-nan.md"),
            str(notes / "after.md"),
        }
        # The out-of-range integer is a bounded per-key skip; the healthy key
        # on the same document stays filterable.
        assert _metadata_values(db_path, str(notes / "aa-huge.md")) == {"status": ["ok"]}
        assert _metadata_skips(db_path, str(notes / "aa-huge.md")) == {"big": "cap_number"}
        # The non-finite float is stringified by the canonical serializer, so
        # the stored blob is strict JSON and the typed row is a string.
        stored = _doc_metadata(db_path, str(notes / "ab-nan.md"))
        assert json.loads(stored, parse_constant=_reject_json_constant)["bad"] == "nan"
        assert _metadata_values(db_path, str(notes / "ab-nan.md")) == {
            "bad": ["nan"],
            "status": ["ok"],
        }
        assert _metadata_skips(db_path, str(notes / "ab-nan.md")) == {}

    def test_non_string_frontmatter_title_indexes_via_fallback_and_continues(
        self, tmp_path, monkeypatch
    ) -> None:
        """CR-02: list/mapping titles never abort the pass or reach SQLite."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "incr.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        # The two bad-title files sort before after.md, so a fatal error on
        # either would leave the healthy trailing file unprocessed.
        (notes / "aa-listy.md").write_text(
            "---\ntitle: [not, a, string]\n---\n# Listy Heading\n\nBody text.\n",
            encoding="utf-8",
        )
        (notes / "ab-mappy.md").write_text(
            "---\ntitle: {a: b}\n---\n# Mappy Heading\n\nBody text.\n",
            encoding="utf-8",
        )
        (notes / "after.md").write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            events: list[str] = []
            result = indexer.update_collection(coll, progress=events.append)
        finally:
            db.close()

        # Every file was processed: the non-string titles never raised.
        assert result == IncrementalResult(added=3, updated=0, removed=0)
        assert result.failed == 0
        assert _doc_row(db_path, str(notes / "aa-listy.md"))[0] == "Listy Heading"
        assert _doc_row(db_path, str(notes / "ab-mappy.md"))[0] == "Mappy Heading"
        assert _doc_row(db_path, str(notes / "after.md"))[0] == "Heading One"
        assert not any(event.startswith("error ") for event in events)

    def test_document_write_failure_is_counted_not_fatal(self, tmp_path, monkeypatch) -> None:
        """D-04: a per-document write error is a counted failure, not a fatal pass."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "incr.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "aa-bad.md").write_text(BODY_ALPHA, encoding="utf-8")
        (notes / "zz-good.md").write_text(BODY_BETA, encoding="utf-8")
        _seed_collection(db_path, notes)

        real_create = DocumentRepository.create

        def _create(repo, doc):
            """Fail the first document's insert, delegate otherwise."""
            if doc.path.endswith("aa-bad.md"):
                raise TypeError("Error binding parameter: type 'list' is not supported")
            return real_create(repo, doc)

        indexer, db, coll = _open_indexer(db_path)
        try:
            events: list[str] = []
            with patch.object(DocumentRepository, "create", _create):
                result = indexer.update_collection(coll, progress=events.append)
        finally:
            db.close()

        assert result.failed == 1
        assert result.added == 1
        assert any(event.startswith("error Error indexing") for event in events)
        # The later file was still processed after the failed write.
        assert str(notes / "zz-good.md") in _doc_paths(db_path)
        assert str(notes / "aa-bad.md") not in _doc_paths(db_path)

    def test_per_file_parser_dispatch_with_text_fallback(self, tmp_path, monkeypatch) -> None:
        """Each extension selects its parser; unknown suffixes fall back to TextParser.

        CORR-01: the single incremental loop no longer hardcodes MarkdownParser.
        `.yaml` goes through CodeParser (so a leading `---` is content, not
        frontmatter), `.txt` through TextParser, and an unmapped suffix through
        the TextParser fallback. `.md` keeps the frontmatter-stripping body.
        """
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "incr.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        markdown_doc = "---\ntitle: Markdown Title\n---\n# Heading\n\nBody text.\n"
        yaml_doc = "---\nfirst: doc\n---\nsecond: doc\n"
        text_doc = "Plain text title\nbody line\n"
        unknown_doc = "Mystery title\nbody line\n"
        (notes / "a.md").write_text(markdown_doc, encoding="utf-8")
        (notes / "config.yaml").write_text(yaml_doc, encoding="utf-8")
        (notes / "notes.txt").write_text(text_doc, encoding="utf-8")
        (notes / "mystery.zzz").write_text(unknown_doc, encoding="utf-8")
        _seed_collection(db_path, notes, pattern="**/*")

        indexer, db, coll = _open_indexer(db_path)
        try:
            result = indexer.update_collection(coll)
        finally:
            db.close()

        assert result == IncrementalResult(added=4, updated=0, removed=0)

        md_title, md_content, md_checksum = _doc_row(db_path, str(notes / "a.md"))
        assert md_title == "Markdown Title"
        assert not md_content.startswith("---")
        assert md_checksum == compute_checksum(md_content, {"title": "Markdown Title"})

        yaml_title, yaml_content, yaml_checksum = _doc_row(db_path, str(notes / "config.yaml"))
        assert yaml_title == "config"
        assert yaml_content == yaml_doc
        assert yaml_checksum == compute_checksum(yaml_doc, {"language": "yaml"})

        text_title, text_content, _ = _doc_row(db_path, str(notes / "notes.txt"))
        assert text_title == "Plain text title"
        assert text_content == text_doc

        unknown_title, unknown_content, _ = _doc_row(db_path, str(notes / "mystery.zzz"))
        assert unknown_title == "Mystery title"
        assert unknown_content == unknown_doc

    def test_yaml_date_frontmatter_indexes_without_type_error(self, tmp_path, monkeypatch) -> None:
        """A `date:` frontmatter value persists as ISO text and never raises (Pitfall 10).

        Before canonical storage, ``json.dumps(metadata)`` raised TypeError on
        the parsed ``datetime.date`` and aborted the update. The stored body
        must stay the frontmatter-stripped parsed body, byte for byte, and the
        stored metadata string must reproduce the checksum input exactly.
        """
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "incr.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "dated.md"
        doc_file.write_text(
            "---\ntitle: Dated\ndate: 2024-01-01\n---\n# Dated\n\nBody text.\n",
            encoding="utf-8",
        )
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            result = indexer.update_collection(coll)
        finally:
            db.close()

        assert result == IncrementalResult(added=1, updated=0, removed=0)
        title, stored_content, checksum = _doc_row(db_path, str(doc_file))
        assert title == "Dated"
        assert stored_content == "# Dated\n\nBody text."
        stored_metadata = _doc_metadata(db_path, str(doc_file))
        assert json.loads(stored_metadata) == {"title": "Dated", "date": "2024-01-01"}
        # The round-tripped string form hashes to the stored checksum: the
        # parse-time date object and the persisted ISO text canonicalize alike.
        assert checksum == compute_checksum(stored_content, json.loads(stored_metadata))

    def test_modified_file_purges_stale_chunks_and_persists_fresh_checksum(
        self, tmp_path, monkeypatch
    ) -> None:
        """A content edit updates the row, drops stale chunks, and stores the new hash."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "incr.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        # Index once, then simulate a prior embed by storing chunks of the old body.
        indexer, db, coll = _open_indexer(db_path)
        try:
            assert indexer.update_collection(coll) == IncrementalResult(1, 0, 0)
            doc_repo = DocumentRepository(db.connection)
            doc = doc_repo.get_by_path(str(doc_file), coll.id)
            assert doc is not None
            with db.connection:
                chunk_repo = DocumentChunkRepository(db.connection)
                chunk_repo.create(
                    DocumentChunk(
                        content="stale chunk of the old body",
                        sequence=0,
                        start_pos=0,
                        end_pos=10,
                        document_id=doc.id,
                    )
                )
        finally:
            db.close()
        assert _chunk_contents(db_path, str(doc_file)) == ["stale chunk of the old body"]

        # Edit the file, then update again.
        doc_file.write_text(BODY_BETA, encoding="utf-8")
        indexer, db, coll = _open_indexer(db_path)
        try:
            result = indexer.update_collection(coll)
        finally:
            db.close()

        assert result == IncrementalResult(0, 1, 0)
        # Stale chunks are purged (nothing from the old body survives).
        assert _chunk_contents(db_path, str(doc_file)) == []
        # The fresh checksum is persisted against the new content...
        _title, content, checksum = _doc_row(db_path, str(doc_file))
        assert "Beta paragraph text" in content
        assert checksum == compute_checksum(content, {})
        # ...so a second pass converges instead of rewriting again.
        indexer, db, coll = _open_indexer(db_path)
        try:
            assert indexer.update_collection(coll) == IncrementalResult(0, 0, 0)
        finally:
            db.close()

    def test_unchanged_file_skipped_without_rewrite(self, tmp_path, monkeypatch) -> None:
        """A checksum-equal file is skipped: zero counts and no updated_at rewrite."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "incr.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "a.md").write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            assert indexer.update_collection(coll) == IncrementalResult(1, 0, 0)
            doc_repo = DocumentRepository(db.connection)
            doc = doc_repo.get_by_path(str(notes / "a.md"), coll.id)
            assert doc is not None
            first_updated_at = doc.updated_at
        finally:
            db.close()

        events: list[str] = []
        indexer, db, coll = _open_indexer(db_path)
        try:
            result = indexer.update_collection(coll, progress=events.append)
            doc_repo = DocumentRepository(db.connection)
            doc = doc_repo.get_by_path(str(notes / "a.md"), coll.id)
            assert doc is not None
            second_updated_at = doc.updated_at
        finally:
            db.close()

        assert result == IncrementalResult(0, 0, 0)
        assert second_updated_at == first_updated_at  # skipped, not rewritten
        assert any(e.startswith("unchanged a.md") for e in events)

    def test_force_rewrites_despite_matching_checksum(self, tmp_path, monkeypatch) -> None:
        """force=True re-indexes a file whose stored checksum already matches."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "incr.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "a.md").write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            assert indexer.update_collection(coll) == IncrementalResult(1, 0, 0)
        finally:
            db.close()

        indexer, db, coll = _open_indexer(db_path)
        try:
            result = indexer.update_collection(coll, force=True)
        finally:
            db.close()

        assert result == IncrementalResult(0, 1, 0)

    def test_removed_file_purges_embeddings_before_document_delete(
        self, tmp_path, monkeypatch
    ) -> None:
        """A vanished file is removed and its embeddings purge BEFORE the row delete (WR-01)."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "incr.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            assert indexer.update_collection(coll) == IncrementalResult(1, 0, 0)
        finally:
            db.close()

        doc_file.unlink()

        # Record call order across the purger and the document delete.
        calls: list[tuple[str, str]] = []
        purger = MagicMock()
        purger.delete_embeddings_by_document.side_effect = lambda doc_id: calls.append(
            ("purge", doc_id)
        )
        original_delete = DocumentRepository.delete

        def recording_delete(self: DocumentRepository, document_id: str) -> bool:
            calls.append(("delete", document_id))
            return original_delete(self, document_id)

        monkeypatch.setattr(DocumentRepository, "delete", recording_delete)

        indexer, db, coll = _open_indexer(db_path)
        try:
            indexer._vector_purger = purger
            result = indexer.update_collection(coll)
        finally:
            db.close()

        assert result == IncrementalResult(0, 0, 1)
        assert _doc_paths(db_path) == set()
        assert _chunk_contents(db_path, str(doc_file)) == []
        # Embeddings are purged before the document row delete (WR-01 ordering).
        assert [kind for kind, _ in calls][:2] == ["purge", "delete"]

    def test_mid_run_failure_keeps_completed_files_durable(self, tmp_path, monkeypatch) -> None:
        """D-04: a failing file aborts the pass but earlier files stay committed."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "incr.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        for name in ("one.md", "two.md", "three.md"):
            (notes / name).write_text(f"# {name}\n\nBody text for {name}. ", encoding="utf-8")
        _seed_collection(db_path, notes)

        # The indexer processes files in FileScanner's scan order; fail the middle one.
        scan_order = [str(p) for p in FileScanner().scan(notes).files]
        assert len(scan_order) == 3
        failing_path = scan_order[1]

        original_create = DocumentRepository.create

        def failing_create(self: DocumentRepository, document: Document) -> Document:
            if document.path == failing_path:
                raise RuntimeError("simulated mid-run failure")
            return original_create(self, document)

        monkeypatch.setattr(DocumentRepository, "create", failing_create)

        indexer, db, coll = _open_indexer(db_path)
        try:
            with pytest.raises(RuntimeError, match="simulated mid-run failure"):
                indexer.update_collection(coll)
        finally:
            db.close()

        # A fresh connection proves the first file committed durably...
        committed = _doc_paths(db_path)
        assert committed == {scan_order[0]}
        # ...the failing file is not half-written...
        assert failing_path not in committed
        assert _chunk_contents(db_path, failing_path) == []
        # ...and the third file was never touched.
        assert scan_order[2] not in committed

    def test_collection_stats_updated_after_run(self, tmp_path, monkeypatch) -> None:
        """document_count and last_indexed_at are recounted and persisted."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "incr.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        for name in ("a.md", "b.md"):
            (notes / name).write_text(f"# {name}\n\nBody text for {name}. ", encoding="utf-8")
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            assert coll.document_count == 0
            assert coll.last_indexed_at is None
            indexer.update_collection(coll)
        finally:
            db.close()

        # Read the persisted stats through a fresh handle.
        db = Database(db_path)
        try:
            stored = CollectionRepository(db.connection).get_by_name("notes")
        finally:
            db.close()
        assert stored is not None
        assert stored.document_count == 2
        assert stored.last_indexed_at is not None

    def test_empty_scan_reports_zero_counts(self, tmp_path, monkeypatch) -> None:
        """A collection whose directory has no matching files reports all zeros."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "incr.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "not-markdown.txt").write_text("ignored by the *.md pattern", encoding="utf-8")
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            events: list[str] = []
            result = indexer.update_collection(coll, progress=events.append)
        finally:
            db.close()

        assert result == IncrementalResult(0, 0, 0)
        assert events[0] == "scan 0"


class TestUpdatePathsReplay:
    """Replay semantics of the per-path API (Phase 12 D-06 edge: idempotency)."""

    def test_replaying_settled_batch_is_all_unchanged(self, tmp_path, monkeypatch) -> None:
        """A second update_paths over the same settled paths writes nothing."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "incr.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        paths = []
        for name in ("one.md", "two.md"):
            path = notes / name
            path.write_text(f"# {name}\n\nBody text for {name}. ", encoding="utf-8")
            paths.append(path)
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            first = indexer.update_paths(coll, paths)
            second = indexer.update_paths(coll, paths)
        finally:
            db.close()

        assert first == IncrementalResult(added=2, updated=0, removed=0, unchanged=0)
        assert second == IncrementalResult(added=0, updated=0, removed=0, unchanged=2)

    def test_update_paths_purges_embeddings_of_modified_doc(self, tmp_path, monkeypatch) -> None:
        """D-08 invariant regression (14-02): a BM25-only update leaves the modified
        document embeddings-free AND chunk-free through a fresh connection.

        The derived staleness signal (stale = no rows in document_embeddings)
        rests on this purge: a future write path that kept stale embeddings
        behind would silently un-mark lagging documents. Mirrors the chunk
        purge test above, plus a real vec0 embedding seeded and asserted gone.
        """
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "incr.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        # Index once, then seed a real embedding for the document.
        indexer, db, coll = _open_indexer(db_path)
        try:
            assert indexer.update_collection(coll) == IncrementalResult(1, 0, 0)
            doc_repo = DocumentRepository(db.connection)
            doc = doc_repo.get_by_path(str(doc_file), coll.id)
            assert doc is not None
            from sif.search.vector import VectorSearcher

            with db.connection:
                VectorSearcher(db.connection, embedding_dim=8).add_embedding(
                    f"e-{doc.id}", doc.id, f"c-{doc.id}", [0.1] * 8
                )
        finally:
            db.close()
        assert _embedding_count(db_path) == 1

        # BM25-only refresh of the modified file: chunks AND embeddings purge.
        doc_file.write_text(BODY_BETA, encoding="utf-8")
        indexer, db, coll = _open_indexer(db_path)
        try:
            result = indexer.update_paths(coll, [doc_file])
        finally:
            db.close()

        assert result == IncrementalResult(0, 1, 0)
        assert _chunk_contents(db_path, str(doc_file)) == []
        assert _embedding_count(db_path) == 0

        # A frontmatter-only edit through the per-path API counts as updated
        # but never purges the preserved chunk/vector rows (D-07).
        indexer, db, coll = _open_indexer(db_path)
        try:
            _seed_chunk_and_embedding(db, coll.id, str(doc_file))
        finally:
            db.close()
        doc_file.write_text("---\ntitle: Beta Renamed\n---\n" + BODY_BETA, encoding="utf-8")
        indexer, db, coll = _open_indexer(db_path)
        try:
            metadata_result = indexer.update_paths(coll, [doc_file])
        finally:
            db.close()

        assert metadata_result.updated == 1
        assert metadata_result.metadata_only == 1
        assert metadata_result.reindexed_paths == set()
        assert _chunk_contents(db_path, str(doc_file)) == ["chunk of the stored body"]
        assert _embedding_count(db_path) == 1


FRONT_BODY = "# Front Heading\n\n" + ("Frontmatter body text. " * 40)
# frontmatter.loads strips the body's trailing whitespace, so the parsed body
# (what the index stores and hashes) is the rstripped form.
PARSED_FRONT_BODY = FRONT_BODY.rstrip()


class TestMetadataFastPath:
    """D-07: frontmatter-only edits preserve chunks/embeddings; bodies purge.

    ``reindexed_paths`` is the explicit embed signal (RESEARCH Pattern 4e):
    added and body-changed paths appear, metadata-only paths never do.
    """

    def _seed_frontmatter_doc(self, tmp_path, monkeypatch) -> tuple[Path, Path]:
        """Seed a collection with one indexed frontmatter document."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "incr.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "front.md"
        doc_file.write_text("---\ntitle: Original\n---\n" + FRONT_BODY, encoding="utf-8")
        _seed_collection(db_path, notes)
        indexer, db, coll = _open_indexer(db_path)
        try:
            assert indexer.update_collection(coll) == IncrementalResult(1, 0, 0)
            _seed_chunk_and_embedding(db, coll.id, str(doc_file))
            before = _doc_fields(db_path, str(doc_file))
        finally:
            db.close()
        assert before["title"] == "Original"
        return db_path, doc_file

    def test_frontmatter_edit_keeps_chunks_and_embeddings(self, tmp_path, monkeypatch) -> None:
        """A title+tag edit rewrites the row but keeps chunk and vector rows."""
        db_path, doc_file = self._seed_frontmatter_doc(tmp_path, monkeypatch)
        before = _doc_fields(db_path, str(doc_file))

        # Frontmatter-only edit: title and tag move; the parsed body does not.
        os.utime(doc_file, (1_000_000_000, 1_000_000_000))
        doc_file.write_text(
            "---\ntitle: Renamed\ntags: [fresh]\n---\n" + FRONT_BODY, encoding="utf-8"
        )
        doc_file.touch()
        os.utime(doc_file, (1_000_000_100, 1_000_000_100))

        indexer, db, coll = _open_indexer(db_path)
        try:
            events: list[str] = []
            result = indexer.update_collection(coll, progress=events.append)
        finally:
            db.close()

        assert result.updated == 1
        assert result.metadata_only == 1
        assert result.reindexed_paths == set()
        assert any(e.startswith("indexed front.md") for e in events)

        after = _doc_fields(db_path, str(doc_file))
        assert after["title"] == "Renamed"
        assert json.loads(after["metadata"]) == {"title": "Renamed", "tags": ["fresh"]}
        assert after["checksum"] == compute_checksum(
            PARSED_FRONT_BODY, {"title": "Renamed", "tags": ["fresh"]}
        )
        assert after["content"] == before["content"] == PARSED_FRONT_BODY
        assert after["mtime"] != before["mtime"]
        assert after["file_size"] == len(PARSED_FRONT_BODY.encode("utf-8"))
        # The whole point of D-07: the chunk/vector rows did not move.
        assert _chunk_contents(db_path, str(doc_file)) == ["chunk of the stored body"]
        assert _embedding_count(db_path) == 1

    def test_body_edit_purges_chunks_and_embeddings(self, tmp_path, monkeypatch) -> None:
        """A body change takes the full path: chunks and vectors are purged."""
        db_path, doc_file = self._seed_frontmatter_doc(tmp_path, monkeypatch)

        doc_file.write_text("---\ntitle: Original\n---\n" + BODY_BETA, encoding="utf-8")
        indexer, db, coll = _open_indexer(db_path)
        try:
            result = indexer.update_collection(coll)
        finally:
            db.close()

        assert result.updated == 1
        assert result.metadata_only == 0
        assert result.reindexed_paths == {str(doc_file)}
        assert _chunk_contents(db_path, str(doc_file)) == []
        assert _embedding_count(db_path) == 0
        _title, content, _checksum = _doc_row(db_path, str(doc_file))
        assert "Beta paragraph text" in content
        # The full path refreshes file_size along with the body (the fast path
        # does the same), so a size filter can never read the old length.
        assert _doc_fields(db_path, str(doc_file))["file_size"] == len(BODY_BETA.rstrip().encode())

    def test_force_with_unchanged_body_takes_the_fast_path(self, tmp_path, monkeypatch) -> None:
        """--force skips the checksum shortcut but still preserves chunk/vector rows."""
        db_path, doc_file = self._seed_frontmatter_doc(tmp_path, monkeypatch)

        indexer, db, coll = _open_indexer(db_path)
        try:
            result = indexer.update_collection(coll, force=True)
        finally:
            db.close()

        assert result.updated == 1
        assert result.metadata_only == 1
        assert result.reindexed_paths == set()
        assert _chunk_contents(db_path, str(doc_file)) == ["chunk of the stored body"]
        assert _embedding_count(db_path) == 1

    def test_checksum_equal_moved_mtime_converges_mtime_only(self, tmp_path, monkeypatch) -> None:
        """A touched-but-unchanged file persists only its moved mtime."""
        db_path, doc_file = self._seed_frontmatter_doc(tmp_path, monkeypatch)
        before = _doc_fields(db_path, str(doc_file))

        os.utime(doc_file, (2_000_000_000, 2_000_000_000))

        indexer, db, coll = _open_indexer(db_path)
        try:
            result = indexer.update_collection(coll)
        finally:
            db.close()

        assert result == IncrementalResult()
        after = _doc_fields(db_path, str(doc_file))
        assert after["mtime"] == 2_000_000_000.0
        assert after["checksum"] == before["checksum"]
        assert after["content"] == before["content"]
        # The skip path touches mtime only, never the chunk/vector rows.
        assert _chunk_contents(db_path, str(doc_file)) == ["chunk of the stored body"]
        assert _embedding_count(db_path) == 1

    def test_reindexed_paths_track_added_and_body_changed_only(self, tmp_path, monkeypatch) -> None:
        """reindexed_paths = added + body-changed; metadata-only is excluded."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "incr.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_a = notes / "a.md"
        doc_a.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            first = indexer.update_collection(coll)
        finally:
            db.close()
        assert first.reindexed_paths == {str(doc_a)}

        # Body edit on a.md plus a brand-new b.md: both purged/created.
        doc_a.write_text(BODY_BETA, encoding="utf-8")
        doc_b = notes / "b.md"
        doc_b.write_text(BODY_ALPHA, encoding="utf-8")
        indexer, db, coll = _open_indexer(db_path)
        try:
            second = indexer.update_collection(coll)
        finally:
            db.close()
        assert second.added == 1
        assert second.updated == 1
        assert second.reindexed_paths == {str(doc_a), str(doc_b)}

        # Frontmatter-only edit: updated, but not a reindex candidate.
        doc_a.write_text("---\ntitle: Beta Renamed\n---\n" + BODY_BETA, encoding="utf-8")
        indexer, db, coll = _open_indexer(db_path)
        try:
            third = indexer.update_collection(coll)
        finally:
            db.close()
        assert third.updated == 1
        assert third.metadata_only == 1
        assert third.reindexed_paths == set()

    def test_frontmatter_only_edit_refreshes_typed_rows(self, tmp_path, monkeypatch) -> None:
        """D-05: a frontmatter-only edit updates the kv view in the same command."""
        db_path, doc_file = self._seed_frontmatter_doc(tmp_path, monkeypatch)
        assert _metadata_values(db_path, str(doc_file)) == {"title": ["Original"]}

        os.utime(doc_file, (1_000_000_000, 1_000_000_000))
        doc_file.write_text(
            "---\ntitle: Renamed\ntags: [fresh]\n---\n" + FRONT_BODY, encoding="utf-8"
        )
        doc_file.touch()
        os.utime(doc_file, (1_000_000_100, 1_000_000_100))

        indexer, db, coll = _open_indexer(db_path)
        try:
            result = indexer.update_collection(coll)
        finally:
            db.close()

        assert result.updated == 1
        assert result.metadata_only == 1
        assert _metadata_values(db_path, str(doc_file)) == {
            "tags": ["fresh"],
            "title": ["Renamed"],
        }

        # A subsequent filtered search sees the new value, never the old one.
        conn = sqlite3.connect(str(db_path))
        try:
            renamed = count_matching_documents(
                conn,
                parse_filter({"field": "title", "operator": "eq", "value": "Renamed"}),
                None,
            )
            original = count_matching_documents(
                conn,
                parse_filter({"field": "title", "operator": "eq", "value": "Original"}),
                None,
            )
            tagged = count_matching_documents(
                conn,
                parse_filter({"field": "tags", "operator": "contains", "value": "fresh"}),
                None,
            )
        finally:
            conn.close()
        assert (renamed, original, tagged) == (1, 0, 1)

    def test_body_edit_removes_typed_rows_for_dropped_keys(self, tmp_path, monkeypatch) -> None:
        """D-05: a body edit rebuilds the kv view with no row for a removed key."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "incr.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "front.md"
        doc_file.write_text(
            "---\ntitle: Original\nstatus: active\n---\n" + FRONT_BODY, encoding="utf-8"
        )
        _seed_collection(db_path, notes)
        indexer, db, coll = _open_indexer(db_path)
        try:
            assert indexer.update_collection(coll) == IncrementalResult(1, 0, 0)
        finally:
            db.close()
        assert _metadata_values(db_path, str(doc_file)) == {
            "status": ["active"],
            "title": ["Original"],
        }

        doc_file.write_text("---\ntitle: Renamed\n---\n" + BODY_BETA, encoding="utf-8")
        indexer, db, coll = _open_indexer(db_path)
        try:
            result = indexer.update_collection(coll)
        finally:
            db.close()

        assert result.updated == 1
        assert result.metadata_only == 0
        values = _metadata_values(db_path, str(doc_file))
        assert values == {"title": ["Renamed"]}
        assert "status" not in values

        conn = sqlite3.connect(str(db_path))
        try:
            stale = count_matching_documents(
                conn,
                parse_filter({"field": "status", "operator": "exists", "value": True}),
                None,
            )
        finally:
            conn.close()
        assert stale == 0


class TestConventionMigration:
    """D-09: one forced re-parse pass per collection, announced exactly once.

    The marker is written only after a pass in which no STORED document
    failed; a failure on stored data leaves it absent so the next pass
    retries instead of presenting old-convention data as migrated. Failures
    on scanned files that were never stored stay reported but cannot block
    convergence (WR-01, 19 REVIEW).
    """

    def test_fresh_collection_marks_convention_and_second_pass_skips(
        self, tmp_path, monkeypatch
    ) -> None:
        """First pass writes the marker silently; the second pass is all-skipped."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "incr.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "a.md").write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            events: list[str] = []
            first = indexer.update_collection(coll, progress=events.append)
        finally:
            db.close()

        assert first.added == 1
        assert not any(e.startswith("migrate ") for e in events)
        assert _marker(db_path, coll.id) == str(CONVENTION_VERSION)

        indexer, db, coll = _open_indexer(db_path)
        try:
            second_events: list[str] = []
            second = indexer.update_collection(coll, progress=second_events.append)
        finally:
            db.close()

        assert second == IncrementalResult()
        assert not any(e.startswith("migrate ") for e in second_events)
        assert any(e.startswith("unchanged a.md") for e in second_events)

    def test_legacy_marker_forces_one_reparse_and_preserves_chunks(
        self, tmp_path, monkeypatch
    ) -> None:
        """An absent/old marker re-parses once, moves checksums, keeps vectors.

        The marker must stay absent for the whole pass (observations are
        recorded synchronously from the progress callback) and is written only
        after a clean pass.
        """
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "incr.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        # First pass establishes the document, then simulate the pre-D-08
        # world: legacy body-only checksum, chunk/vector present, no marker.
        indexer, db, coll = _open_indexer(db_path)
        try:
            assert indexer.update_collection(coll) == IncrementalResult(1, 0, 0)
            _seed_chunk_and_embedding(db, coll.id, str(doc_file))
        finally:
            db.close()
        _downgrade_to_legacy(db_path, coll.id, str(doc_file))

        observations: list[tuple[str, str | None]] = []

        def progress(event: str) -> None:
            observations.append((event, _marker(db_path, coll.id)))

        indexer, db, coll = _open_indexer(db_path)
        try:
            result = indexer.update_collection(coll, progress=progress)
        finally:
            db.close()

        migrate_events = [
            event for event, _marker_value in observations if event.startswith("migrate")
        ]
        assert migrate_events == ["migrate 1"]
        # No marker existed at any event boundary: the write happens after the
        # per-file loop, never before or during it.
        assert all(marker_value is None for _event, marker_value in observations)
        assert result.updated == 1
        assert result.metadata_only == 1
        assert result.reindexed_paths == set()
        # The failure path would be retried; here the marker cleared cleanly.
        assert _marker(db_path, coll.id) == str(CONVENTION_VERSION)
        # Unchanged body: chunk/vector rows survive, checksum moved.
        assert _chunk_contents(db_path, str(doc_file)) == ["chunk of the stored body"]
        assert _embedding_count(db_path) == 1
        _title, content, checksum = _doc_row(db_path, str(doc_file))
        assert checksum == compute_checksum(content, {})
        assert checksum != hashlib.sha256(content.encode()).hexdigest()

        # A second pass is all-skipped: the migration ran exactly once.
        indexer, db, coll = _open_indexer(db_path)
        try:
            second_events: list[str] = []
            second = indexer.update_collection(coll, progress=second_events.append)
        finally:
            db.close()
        assert second == IncrementalResult()
        assert not any(e.startswith("migrate ") for e in second_events)

    def test_persistently_unparseable_scanned_file_does_not_strand_the_marker(
        self, tmp_path, monkeypatch
    ) -> None:
        """WR-01: a never-stored failing file cannot block migration convergence.

        A binary/non-UTF-8 file matched by a broad pattern fails on every run.
        Pre-fix that kept ``failed`` nonzero forever, so the marker was never
        written and every update re-parsed and rewrote every healthy document.
        """
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "incr.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "good.md").write_text(BODY_ALPHA, encoding="utf-8")
        (notes / "bad.bin").write_bytes(b"\xff\xfe\x00not utf-8")
        _seed_collection(db_path, notes, pattern="**/*")

        indexer, db, coll = _open_indexer(db_path)
        try:
            events: list[str] = []
            first = indexer.update_collection(coll, progress=events.append)
        finally:
            db.close()

        assert first.added == 1
        assert first.failed == 1  # still reported
        assert not any(e.startswith("migrate ") for e in events)  # no prior docs
        # Converged: the failure was never stored, so it cannot strand the
        # migration.
        assert _marker(db_path, coll.id) == str(CONVENTION_VERSION)
        healthy_before = _doc_fields(db_path, str(notes / "good.md"))

        indexer, db, coll = _open_indexer(db_path)
        try:
            second_events: list[str] = []
            second = indexer.update_collection(coll, progress=second_events.append)
        finally:
            db.close()

        # The permanent failure is still counted, but no migration notice and
        # no rewrite of the healthy document: run 2 is not a re-parse pass.
        assert second.failed == 1
        assert second.updated == 0
        assert second.added == 0
        assert second.metadata_only == 0
        assert not any(e.startswith("migrate ") for e in second_events)
        assert any(e.startswith("unchanged good.md") for e in second_events)
        assert _doc_fields(db_path, str(notes / "good.md")) == healthy_before

    def test_stored_document_failure_keeps_marker_unwritten_until_fixed(
        self, tmp_path, monkeypatch
    ) -> None:
        """D-09: a failure on already-stored data still blocks the marker."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "incr.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        # First pass stores the document and writes the marker.
        indexer, db, coll = _open_indexer(db_path)
        try:
            assert indexer.update_collection(coll) == IncrementalResult(added=1)
        finally:
            db.close()
        assert _marker(db_path, coll.id) == str(CONVENTION_VERSION)

        # Simulate the pre-D-08 world (body-only checksum, no marker) and a
        # stored file that has since become unreadable.
        _downgrade_to_legacy(db_path, coll.id, str(doc_file))
        doc_file.write_bytes(b"\xff\xfe\x00not utf-8")

        indexer, db, coll = _open_indexer(db_path)
        try:
            events: list[str] = []
            failing = indexer.update_collection(coll, progress=events.append)
        finally:
            db.close()

        assert failing.failed == 1
        assert [e for e in events if e.startswith("migrate ")] == ["migrate 1"]
        # The stored row would still carry the old convention: retry next time.
        assert _marker(db_path, coll.id) is None

        # Restore the file: the next pass completes the migration.
        doc_file.write_text(BODY_ALPHA, encoding="utf-8")
        indexer, db, coll = _open_indexer(db_path)
        try:
            third = indexer.update_collection(coll)
        finally:
            db.close()

        assert third.failed == 0
        assert third.updated == 1
        assert third.metadata_only == 1
        assert _marker(db_path, coll.id) == str(CONVENTION_VERSION)

    def test_empty_collection_writes_marker_without_migrate_event(
        self, tmp_path, monkeypatch
    ) -> None:
        """An empty collection has nothing to migrate: silent marker write."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "incr.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            events: list[str] = []
            result = indexer.update_collection(coll, progress=events.append)
        finally:
            db.close()

        assert result == IncrementalResult()
        assert events == ["scan 0"]
        assert _marker(db_path, coll.id) == str(CONVENTION_VERSION)

    def test_update_paths_never_reads_or_writes_the_marker(self, tmp_path, monkeypatch) -> None:
        """Watch bursts / drift refresh never start a migration (D-09)."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "incr.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            with patch.object(
                IndexMetaRepository,
                "get",
                side_effect=AssertionError("update_paths must not read the marker"),
            ):
                result = indexer.update_paths(coll, [doc_file])
        finally:
            db.close()

        assert result.added == 1
        assert _marker(db_path, coll.id) is None
