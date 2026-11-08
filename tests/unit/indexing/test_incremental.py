"""Unit tests for the shared IncrementalIndexer core (roadmap SC3 / D-04).

The indexer is the one incremental loop extracted from ``update_cmd``: same
scan → checksum-diff → parse → write behavior, but each file's writes commit
as one short BEGIN IMMEDIATE transaction so a mid-run failure keeps completed
files durable (D-04) instead of rolling back the whole run.
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sif.config.settings import Settings
from sif.core.models import Collection, Document, DocumentChunk
from sif.database.database import Database
from sif.database.repositories import (
    CollectionRepository,
    DocumentChunkRepository,
    DocumentRepository,
)
from sif.indexing.incremental import IncrementalIndexer, IncrementalResult
from sif.indexing.scanner import FileScanner


BODY_ALPHA = "# Heading One\n\n" + ("Alpha paragraph text. " * 50)
BODY_BETA = "# Heading Two\n\n" + ("Beta paragraph text. " * 50)


def _delenv_settings_vars(monkeypatch) -> None:
    """Keep Settings construction hermetic against a developer shell."""
    for var in ("SIF_EMBEDDING_DIM", "SIF_MODEL_TYPE", "SIF_MODEL_NAME"):
        monkeypatch.delenv(var, raising=False)


def _test_settings() -> Settings:
    """Build hermetic test settings."""
    return Settings(embedding_dim=8, model_name="test", cache_embeddings=False)


def _seed_collection(db_path: Path, notes: Path) -> str:
    """Init schema and create one collection pointing at ``notes``; return its id."""
    from sif.core.models import Collection as Coll

    db = Database(db_path)
    with patch("sif.config.settings.get_settings", return_value=_test_settings()):
        db.init_schema()
        with db.connection:
            coll_repo = CollectionRepository(db.connection)
            coll = Coll(name="notes", path=str(notes))
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
        assert checksum == hashlib.sha256(content.encode()).hexdigest()
        # The scan event reaches the presentation callback before per-file events.
        assert events[0].startswith("scan ")

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
        assert checksum == hashlib.sha256(content.encode()).hexdigest()
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
