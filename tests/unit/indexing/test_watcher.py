"""Fold semantics and per-path update proofs for the Phase 12 watch pipeline.

Synthetic-event, zero-timing culture (D-15): watchdog event objects are
constructed positionally and driven directly into ``fold_events`` /
``update_paths`` — no observer threads, no sleeps. The real-observer
end-to-end proof lives in ``tests/integration/test_watch_e2e.py``.
"""

from __future__ import annotations

import errno
import logging
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

from watchdog.events import (
    DirCreatedEvent,
    DirDeletedEvent,
    DirModifiedEvent,
    DirMovedEvent,
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
)

from sif.config.settings import Settings
from sif.core.models import Collection
from sif.database.database import Database
from sif.database.repositories import DocumentChunkRepository, DocumentRepository
from sif.indexing import watcher as watcher_module
from sif.indexing.incremental import IncrementalIndexer, IncrementalResult
from sif.indexing.scanner import FileScanner
from sif.indexing.watcher import FileWatcher, FoldResult, WatchConfig, fold_events


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
    db = Database(db_path)
    with patch("sif.config.settings.get_settings", return_value=_test_settings()):
        db.init_schema()
        with db.connection:
            from sif.database.repositories import CollectionRepository

            coll_repo = CollectionRepository(db.connection)
            coll = Collection(name="notes", path=str(notes))
            coll_repo.create(coll)
            coll_id = coll.id
    db.close()
    return coll_id


def _open_indexer(db_path: Path) -> tuple[IncrementalIndexer, Database, Collection]:
    """Open the DB, load the seeded collection, and build an indexer."""
    db = Database(db_path)
    from sif.database.repositories import CollectionRepository

    coll_repo = CollectionRepository(db.connection)
    coll = coll_repo.get_by_name("notes")
    assert coll is not None
    return IncrementalIndexer(db.connection), db, coll


def _doc_paths(db_path: Path) -> set[str]:
    """Read document paths through a fresh connection (query, not files)."""
    conn = sqlite3.connect(str(db_path))
    try:
        return {row[0] for row in conn.execute("SELECT path FROM documents")}
    finally:
        conn.close()


def _seed_collections(db_path: Path, roots: dict[str, Path]) -> None:
    """Init schema, register one collection per name->root, index one doc each."""
    db = Database(db_path)
    with patch("sif.config.settings.get_settings", return_value=_test_settings()):
        db.init_schema()
        with db.connection:
            from sif.database.repositories import CollectionRepository

            repo = CollectionRepository(db.connection)
            for name, root in roots.items():
                repo.create(Collection(name=name, path=str(root)))
        repo = CollectionRepository(db.connection)
        indexer = IncrementalIndexer(db.connection)
        for name in roots:
            coll = repo.get_by_name(name)
            assert coll is not None
            indexer.update_collection(coll)
    db.close()


class _CheckpointSpy:
    """Connection proxy counting PRAGMA wal_checkpoint(TRUNCATE) executions.

    Non-checkpoint statements (and the transaction protocol the indexer's
    ``with conn:`` blocks need) delegate to the wrapped real connection, so
    the watcher can run real burst jobs through the spy.
    """

    def __init__(self, conn: sqlite3.Connection, busy: bool = False) -> None:
        self._conn = conn
        self._busy = busy
        self.calls = 0

    def execute(self, sql: str, *args: object) -> sqlite3.Cursor:
        if sql == "PRAGMA wal_checkpoint(TRUNCATE)":
            self.calls += 1
            cursor = MagicMock()
            cursor.fetchone.return_value = (1 if self._busy else 0, 0, 0)
            return cursor
        return self._conn.execute(sql, *args)

    def __enter__(self) -> sqlite3.Connection:
        return self._conn.__enter__()

    def __exit__(self, *args: object) -> object:
        return self._conn.__exit__(*args)

    def __getattr__(self, name: str) -> object:
        return getattr(self._conn, name)


def _should_track(root: Path, path: Path) -> bool:
    """The collection's shared scanner predicate (D-07)."""
    return FileScanner.matches(root, path, pattern="**/*.md")


class TestFoldEvents:
    """Folding a settled burst into candidate path sets (D-06/D-07/D-08)."""

    def test_temp_noise_dropped_and_real_md_kept(self, tmp_path: Path) -> None:
        """Editor-noise paths never become candidates; real .md paths do."""
        root = tmp_path / "notes"
        real = root / "note.md"
        noise = [
            root / "note.md.sb-ABCD1234",
            root / ".swp.tmp",
            root / "4913",
            root / ".#b.md",
            root / "c.tmp",
            root / "d.swp",
            root / ".DS_Store",
        ]
        events = [FileCreatedEvent(str(p)) for p in [real, *noise]]

        folded = fold_events(events, should_track=lambda p: _should_track(root, p))

        assert folded.index_candidates == {real.resolve()}
        assert folded.remove_candidates == set()
        assert folded.needs_reconcile is False

    def test_atomic_save_chain_folds_to_final_path_only(self, tmp_path: Path) -> None:
        """The probe's 5-event macOS atomic-save chain yields exactly the final path.

        Includes the trailing ``deleted`` on the final path after ``moved`` —
        the trailing delete must NOT turn the burst into a removal (D-06:
        disk is truth; the index candidate's stat decides).
        """
        root = tmp_path / "notes"
        final = root / "file.md"
        temp = root / "file.md.sb-ABCD1234"
        burst = [
            FileCreatedEvent(str(temp)),
            FileModifiedEvent(str(temp)),
            FileMovedEvent(str(temp), str(final)),
            FileModifiedEvent(str(final)),
            FileDeletedEvent(str(final)),
        ]

        folded = fold_events(burst, should_track=lambda p: _should_track(root, p))

        assert folded.index_candidates == {final.resolve()}
        assert folded.remove_candidates == set()
        assert folded.needs_reconcile is False

    def test_moved_event_contributes_dest_index_src_remove(self, tmp_path: Path) -> None:
        """A moved event indexes the dest and removes the src (D-07 dest rule)."""
        root = tmp_path / "notes"
        src = root / "old.md"
        dest = root / "new.md"

        folded = fold_events(
            [FileMovedEvent(str(src), str(dest))],
            should_track=lambda p: _should_track(root, p),
        )

        assert folded.index_candidates == {dest.resolve()}
        assert folded.remove_candidates == {src.resolve()}

    def test_directory_events_ignored_and_dir_moved_flags_reconcile(self, tmp_path: Path) -> None:
        """Dir created/modified/deleted are ignored; dir moved needs a reconcile."""
        root = tmp_path / "notes"
        sub = root / "sub"

        plain = fold_events(
            [
                DirCreatedEvent(str(sub)),
                DirModifiedEvent(str(sub)),
                DirDeletedEvent(str(sub)),
            ],
            should_track=lambda p: _should_track(root, p),
        )
        assert plain == FoldResult()

        moved = fold_events(
            [DirMovedEvent(str(sub), str(root / "renamed"))],
            should_track=lambda p: _should_track(root, p),
        )
        assert moved.needs_reconcile is True
        assert moved.index_candidates == set()
        assert moved.remove_candidates == set()

    def test_fold_is_order_independent(self, tmp_path: Path) -> None:
        """A burst and its reverse fold to identical candidate sets (edge: ordering)."""
        root = tmp_path / "notes"
        final = root / "file.md"
        temp = root / "file.md.sb-ABCD1234"
        other = root / "other.md"
        burst = [
            FileCreatedEvent(str(temp)),
            FileModifiedEvent(str(temp)),
            FileMovedEvent(str(temp), str(final)),
            FileModifiedEvent(str(final)),
            FileDeletedEvent(str(final)),
            FileDeletedEvent(str(other)),
        ]

        def track(path: Path) -> bool:
            return _should_track(root, path)

        forward = fold_events(burst, should_track=track)
        backward = fold_events(list(reversed(burst)), should_track=track)

        assert forward == backward


class TestUpdatePaths:
    """The per-path targeted update API (D-06/D-10/D-11), real DB culture."""

    def test_new_file_added_and_document_row_exists(self, tmp_path, monkeypatch) -> None:
        """A new on-disk path is added: added == 1 and the row is durable."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            result = indexer.update_paths(coll, [doc_file])
        finally:
            db.close()

        assert result == IncrementalResult(added=1, updated=0, removed=0, unchanged=0)
        assert str(doc_file) in _doc_paths(db_path)

    def test_edited_file_updated_with_fresh_checksum(self, tmp_path, monkeypatch) -> None:
        """A content edit through update_paths reports updated == 1."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            assert indexer.update_collection(coll) == IncrementalResult(1, 0, 0, 0)
        finally:
            db.close()

        doc_file.write_text(BODY_BETA, encoding="utf-8")
        indexer, db, coll = _open_indexer(db_path)
        try:
            result = indexer.update_paths(coll, [doc_file])
        finally:
            db.close()

        assert result == IncrementalResult(added=0, updated=1, removed=0, unchanged=0)

    def test_deleted_path_removed_with_purge_before_delete(self, tmp_path, monkeypatch) -> None:
        """A vanished path is removed and its embeddings purge BEFORE the row delete (WR-01)."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            assert indexer.update_collection(coll) == IncrementalResult(1, 0, 0, 0)
        finally:
            db.close()

        doc_file.unlink()

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
            result = indexer.update_paths(coll, [doc_file])
        finally:
            db.close()

        assert result == IncrementalResult(added=0, updated=0, removed=1, unchanged=0)
        assert _doc_paths(db_path) == set()
        assert [kind for kind, _ in calls] == ["purge", "delete"]

    def test_missing_root_returns_zero_emits_missing_and_preserves_docs(
        self, tmp_path, monkeypatch
    ) -> None:
        """D-11: a missing collection root never sweeps — both update paths."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            assert indexer.update_collection(coll) == IncrementalResult(1, 0, 0, 0)
        finally:
            db.close()

        # The collection root disappears (unmounted/renamed drive).
        notes.rename(tmp_path / "notes-gone")

        indexer, db, coll = _open_indexer(db_path)
        try:
            events: list[str] = []
            result = indexer.update_paths(coll, [doc_file], progress=events.append)
            assert result == IncrementalResult(added=0, updated=0, removed=0, unchanged=0)
            assert "missing notes" in events

            events = []
            result = indexer.update_collection(coll, progress=events.append)
            assert result == IncrementalResult(added=0, updated=0, removed=0, unchanged=0)
            assert "missing notes" in events
        finally:
            db.close()

        # Every existing document of that collection survives.
        assert _doc_paths(db_path) == {str(doc_file)}

    def test_unchanged_path_counted_as_unchanged(self, tmp_path, monkeypatch) -> None:
        """A checksum-equal path maps the skip outcome to unchanged += 1."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            assert indexer.update_collection(coll) == IncrementalResult(1, 0, 0, 0)
            events: list[str] = []
            result = indexer.update_paths(coll, [doc_file], progress=events.append)
        finally:
            db.close()

        assert result == IncrementalResult(added=0, updated=0, removed=0, unchanged=1)
        assert any(e.startswith("unchanged a.md") for e in events)


class TestWatchPipeline:
    """Settled-burst → worker → flock → update_paths, driven synthetically (D-15).

    The settled callback is invoked directly and the queue drained with
    ``_drain_once`` — no observer threads, no timing anywhere.
    """

    def test_save_burst_coalesces_to_one_update_paths_call(self, tmp_path, monkeypatch) -> None:
        """LIVE-02: a 5-event save burst yields exactly one update_paths invocation."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "file.md").write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        calls: list[frozenset] = []

        class SpyIndexer:
            """Records update_paths invocations without touching the DB."""

            def __init__(self, conn) -> None:
                self.conn = conn

            def update_paths(self, collection, paths, *, force=False, progress=None):
                _ = (collection, force, progress)
                calls.append(frozenset(paths))
                return IncrementalResult(added=1)

            def update_collection(self, collection, *, force=False, progress=None):
                _ = (collection, force, progress)
                raise AssertionError("burst must not trigger a full reconcile")

        monkeypatch.setattr(watcher_module, "IncrementalIndexer", SpyIndexer)

        db = Database(db_path)
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            watcher = FileWatcher([coll], db.connection, db_path)
            burst = [
                FileCreatedEvent(str(notes / "file.md")),
                FileModifiedEvent(str(notes / "file.md")),
                FileModifiedEvent(str(notes / "file.md")),
                FileCreatedEvent(str(notes / "file.md")),
                FileModifiedEvent(str(notes / "file.md")),
            ]
            watcher._settled_callback(coll)(burst)
            watcher._drain_once()
        finally:
            db.close()

        assert len(calls) == 1
        assert calls[0] == frozenset({(notes / "file.md").resolve()})
        assert len(calls[0]) == 1

    def test_atomic_save_chain_one_index_op_removed_zero(self, tmp_path, monkeypatch) -> None:
        """LIVE-03: the full probe atomic-save chain indexes once, removes nothing."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        final = notes / "file.md"
        final.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            assert indexer.update_collection(coll) == IncrementalResult(1, 0, 0)
        finally:
            db.close()

        # Real atomic save: new content lands in a .sb- temp, then replaces.
        temp = notes / "file.md.sb-ABCD1234"
        temp.write_text(BODY_BETA, encoding="utf-8")
        os.replace(temp, final)
        burst = [
            FileCreatedEvent(str(temp)),
            FileModifiedEvent(str(temp)),
            FileMovedEvent(str(temp), str(final)),
            FileModifiedEvent(str(final)),
            FileDeletedEvent(str(final)),
        ]

        results: list[IncrementalResult] = []
        db = Database(db_path)
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            watcher = FileWatcher(
                [coll],
                db.connection,
                db_path,
                WatchConfig(on_batch=lambda _coll, result: results.append(result)),
            )
            watcher._settled_callback(coll)(burst)
            watcher._drain_once()
        finally:
            db.close()

        assert len(results) == 1
        assert results[0].removed == 0
        assert results[0].added + results[0].updated == 1
        conn = sqlite3.connect(str(db_path))
        try:
            row = conn.execute(
                "SELECT content FROM documents WHERE path = ?", (str(final),)
            ).fetchone()
        finally:
            conn.close()
        assert row is not None
        assert "Beta paragraph text" in row[0]

    def test_plain_rename_removes_old_adds_new_only(self, tmp_path, monkeypatch) -> None:
        """LIVE-03: a rename reconciles to removed=1 + added=1, others untouched."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        old = notes / "old.md"
        other = notes / "other.md"
        old.write_text(BODY_ALPHA, encoding="utf-8")
        other.write_text("# Other\n\n" + ("Other body text. " * 20), encoding="utf-8")
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            assert indexer.update_collection(coll) == IncrementalResult(2, 0, 0)
        finally:
            db.close()

        renamed = notes / "renamed.md"
        os.rename(old, renamed)
        burst = [
            FileModifiedEvent(str(old)),
            FileMovedEvent(str(old), str(renamed)),
        ]

        results: list[IncrementalResult] = []
        db = Database(db_path)
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            watcher = FileWatcher(
                [coll],
                db.connection,
                db_path,
                WatchConfig(on_batch=lambda _coll, result: results.append(result)),
            )
            watcher._settled_callback(coll)(burst)
            watcher._drain_once()
        finally:
            db.close()

        assert len(results) == 1
        assert results[0] == IncrementalResult(added=1, updated=0, removed=1, unchanged=0)
        assert _doc_paths(db_path) == {str(other), str(renamed)}

    def test_empty_fold_never_calls_update_paths_single_event_works(
        self, tmp_path, monkeypatch
    ) -> None:
        """Edge: a pure-noise burst never reaches update_paths; one event does."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "file.md").write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        calls: list[frozenset] = []

        class SpyIndexer:
            """Records update_paths invocations without touching the DB."""

            def __init__(self, conn) -> None:
                self.conn = conn

            def update_paths(self, collection, paths, *, force=False, progress=None):
                _ = (collection, force, progress)
                calls.append(frozenset(paths))
                return IncrementalResult()

        monkeypatch.setattr(watcher_module, "IncrementalIndexer", SpyIndexer)

        db = Database(db_path)
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            watcher = FileWatcher([coll], db.connection, db_path)
            noise_burst = [
                FileCreatedEvent(str(notes / "scratch.tmp")),
                FileDeletedEvent(str(notes / "d.swp")),
            ]
            watcher._settled_callback(coll)(noise_burst)
            watcher._drain_once()
            assert calls == []

            watcher._settled_callback(coll)([FileModifiedEvent(str(notes / "file.md"))])
            watcher._drain_once()
        finally:
            db.close()

        assert len(calls) == 1

    def test_lock_acquired_per_job_never_held_for_lifetime(self, tmp_path, monkeypatch) -> None:
        """Edge/D-04: index_lock enters and exits around EACH job, never the loop."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "file.md").write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        lock_events: list[str] = []

        @contextmanager
        def recording_lock(_db_path, _timeout_s, _on_wait=None):
            lock_events.append("enter")
            try:
                yield
            finally:
                lock_events.append("exit")

        monkeypatch.setattr(watcher_module, "index_lock", recording_lock)

        class SpyIndexer:
            """No-op indexer; the lock shape is what this test observes."""

            def __init__(self, conn) -> None:
                self.conn = conn

            def update_paths(self, collection, paths, *, force=False, progress=None):
                _ = (collection, paths, force, progress)
                return IncrementalResult()

        monkeypatch.setattr(watcher_module, "IncrementalIndexer", SpyIndexer)

        db = Database(db_path)
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            watcher = FileWatcher([coll], db.connection, db_path)
            for _ in range(2):
                watcher._settled_callback(coll)([FileModifiedEvent(str(notes / "file.md"))])
                watcher._drain_once()
        finally:
            db.close()

        assert lock_events == ["enter", "exit", "enter", "exit"]

    def test_startup_created_burst_absorbed_as_unchanged(self, tmp_path, monkeypatch) -> None:
        """Pitfall 1: pre-existing files' created burst is all checksum-skips."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        files = []
        for name in ("a.md", "b.md"):
            path = notes / name
            path.write_text(f"# {name}\n\nBody text for {name}. ", encoding="utf-8")
            files.append(path)
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            assert indexer.update_collection(coll) == IncrementalResult(2, 0, 0)
        finally:
            db.close()

        burst = [FileCreatedEvent(str(p)) for p in files] + [FileModifiedEvent(str(files[0]))]
        results: list[IncrementalResult] = []
        db = Database(db_path)
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            watcher = FileWatcher(
                [coll],
                db.connection,
                db_path,
                WatchConfig(on_batch=lambda _coll, result: results.append(result)),
            )
            watcher._settled_callback(coll)(burst)
            watcher._drain_once()
        finally:
            db.close()

        assert len(results) == 1
        assert results[0] == IncrementalResult(added=0, updated=0, removed=0, unchanged=2)


class TestStopFlushGate:
    """CR-01: the bounded flush runs only once the worker thread has exited.

    ``Thread.join(timeout=...)`` returns silently when the thread is still
    alive, and a job can legitimately outlast the join (flock wait up to
    lock_timeout, first-use model load at embed depth). Draining then would
    run jobs on the calling thread concurrently with the still-live worker
    on the SAME connection — two threads interleaving BEGIN IMMEDIATE
    transactions breaks per-file atomicity (D-04). Synthetic worker fakes,
    zero timing (D-15).
    """

    def _make_watcher(self, conn: sqlite3.Connection, db_path: Path) -> FileWatcher:
        """Build a FileWatcher over the seeded 'notes' collection (never started)."""
        from sif.database.repositories import CollectionRepository

        coll = CollectionRepository(conn).get_by_name("notes")
        assert coll is not None
        return FileWatcher([coll], conn, db_path)

    def test_stop_skips_flush_when_worker_join_times_out(
        self, tmp_path, monkeypatch, caplog
    ) -> None:
        """A still-alive worker after the join: flush skipped, ONE warning logged."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "a.md").write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        drained: list[bool] = []
        db = Database(db_path)
        try:
            watcher = self._make_watcher(db.connection, db_path)
            monkeypatch.setattr(watcher, "_drain_once", lambda: drained.append(True))

            class BusyWorker:
                """join() returns with the thread still 'alive' (timed out)."""

                def join(self, timeout: float | None = None) -> None:  # noqa: ARG002
                    return None

                def is_alive(self) -> bool:
                    return True

            watcher._worker = BusyWorker()  # type: ignore[assignment]
            with caplog.at_level(logging.WARNING, logger="sif.indexing.watcher"):
                watcher.stop(flush=True)
        finally:
            db.close()

        assert drained == []
        busy = [r for r in caplog.records if "still busy" in r.message]
        assert len(busy) == 1

    def test_stop_flushes_once_worker_exited(self, tmp_path, monkeypatch) -> None:
        """A joined (dead) worker: the bounded flush runs exactly once."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "a.md").write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        drained: list[bool] = []
        db = Database(db_path)
        try:
            watcher = self._make_watcher(db.connection, db_path)
            monkeypatch.setattr(watcher, "_drain_once", lambda: drained.append(True))

            class DoneWorker:
                """join() returns with the thread exited."""

                def join(self, timeout: float | None = None) -> None:  # noqa: ARG002
                    return None

                def is_alive(self) -> bool:
                    return False

            watcher._worker = DoneWorker()  # type: ignore[assignment]
            watcher.stop(flush=True)
        finally:
            db.close()

        assert drained == [True]

    def test_worker_joined_tracks_worker_liveness(self, tmp_path, monkeypatch) -> None:
        """WR-01 gate for the hosts' shutdown checkpoint: True when no worker
        was ever started or the thread exited; False while it runs (the
        timed-out-join state that must skip same-connection work)."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "a.md").write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        db = Database(db_path)
        try:
            watcher = self._make_watcher(db.connection, db_path)
            assert watcher.worker_joined() is True  # never started

            class BusyWorker:
                """join() returns with the thread still 'alive' (timed out)."""

                def join(self, timeout: float | None = None) -> None:  # noqa: ARG002
                    return None

                def is_alive(self) -> bool:
                    return True

            class DoneWorker:
                """join() returns with the thread exited."""

                def join(self, timeout: float | None = None) -> None:  # noqa: ARG002
                    return None

                def is_alive(self) -> bool:
                    return False

            watcher._worker = BusyWorker()  # type: ignore[assignment]
            assert watcher.worker_joined() is False
            watcher._worker = DoneWorker()  # type: ignore[assignment]
            assert watcher.worker_joined() is True
        finally:
            db.close()


class TestRecoveryTick:
    """D-12 missing-root recovery, zero timing: the tick is invoked directly.

    A watched root that disappears is marked missing with ONE warning per
    transition (never per poll), its watch handle unscheduled, and its
    documents preserved; when the root returns, the watch is rescheduled and
    one full-reconcile job is enqueued.
    """

    def _seed_one_doc(self, tmp_path, monkeypatch) -> Path:
        """Seed db + collection + one indexed document; returns the db path."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "a.md").write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            assert indexer.update_collection(coll) == IncrementalResult(1, 0, 0)
        finally:
            db.close()
        return db_path

    def test_disappear_marks_missing_warns_once_preserves_docs(
        self, tmp_path, monkeypatch, caplog
    ) -> None:
        db_path = self._seed_one_doc(tmp_path, monkeypatch)
        notes = tmp_path / "notes"
        doc_file = notes / "a.md"

        observer_cls = MagicMock()
        monkeypatch.setattr(watcher_module, "Observer", observer_cls)

        db = Database(db_path)
        watcher = None
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            watcher = FileWatcher([coll], db.connection, db_path)
            watcher.start()
            observer = observer_cls.return_value
            assert observer.schedule.call_count == 1
            first_debouncer = watcher._watch_states["notes"].debouncer
            assert first_debouncer is not None

            # The root disappears (unmounted/renamed drive); two ticks run.
            notes.rename(tmp_path / "notes-gone")
            with caplog.at_level(logging.WARNING, logger="sif.indexing.watcher"):
                watcher.recovery_tick()
                watcher.recovery_tick()

            # Marked missing: handle unscheduled, exactly ONE warning across
            # two ticks, and every document preserved (never swept).
            assert observer.unschedule.call_count == 1
            observer.unschedule.assert_called_once_with(observer.schedule.return_value)
            disappeared = [r for r in caplog.records if "disappeared" in r.message]
            assert len(disappeared) == 1
            assert _doc_paths(db_path) == {str(doc_file)}
            # WR-02: the debouncer is stopped, joined, and cleared — never a
            # leaked live thread per disappear cycle.
            state = watcher._watch_states["notes"]
            assert state.missing is True
            assert state.debouncer is None
            assert first_debouncer.is_alive() is False
        finally:
            if watcher is not None:
                watcher.stop(flush=False)
            db.close()

    def test_disappear_return_cycle_stops_each_debouncer(self, tmp_path, monkeypatch) -> None:
        """WR-02 regression: a disappear/return cycle replaces the state's
        debouncer, so the disappear branch must stop the old one — otherwise
        each cycle leaks one live EventDebouncer thread in a host designed
        to run for months (the D-12 flaky-mount scenario)."""
        db_path = self._seed_one_doc(tmp_path, monkeypatch)
        notes = tmp_path / "notes"
        gone = tmp_path / "notes-gone"

        observer_cls = MagicMock()
        monkeypatch.setattr(watcher_module, "Observer", observer_cls)

        db = Database(db_path)
        watcher = None
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            watcher = FileWatcher([coll], db.connection, db_path)
            watcher.start()
            observer = observer_cls.return_value
            state = watcher._watch_states["notes"]

            debouncers = []
            for _ in range(3):
                debouncers.append(state.debouncer)
                notes.rename(gone)
                watcher.recovery_tick()
                assert state.debouncer is None
                assert debouncers[-1].is_alive() is False
                gone.rename(notes)
                watcher.recovery_tick()
                assert state.debouncer is not None
                assert state.debouncer is not debouncers[-1]

            # Three full cycles: every previously armed debouncer is dead;
            # only the currently installed (fresh) one is live.
            assert observer.schedule.call_count == 4
            assert all(d.is_alive() is False for d in debouncers)
        finally:
            if watcher is not None:
                watcher.stop(flush=False)
            db.close()

    def test_return_reschedules_and_enqueues_full_reconcile(
        self, tmp_path, monkeypatch, caplog
    ) -> None:
        db_path = self._seed_one_doc(tmp_path, monkeypatch)
        notes = tmp_path / "notes"

        observer_cls = MagicMock()
        monkeypatch.setattr(watcher_module, "Observer", observer_cls)

        db = Database(db_path)
        watcher = None
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            watcher = FileWatcher([coll], db.connection, db_path)
            watcher.start()
            observer = observer_cls.return_value

            # Lose the root, then bring it back.
            notes.rename(tmp_path / "notes-gone")
            watcher.recovery_tick()
            (tmp_path / "notes-gone").rename(notes)
            with caplog.at_level(logging.WARNING, logger="sif.indexing.watcher"):
                watcher.recovery_tick()

            # Rescheduled (second schedule call), warned exactly once on the
            # return transition, and one full-reconcile job enqueued (D-12).
            assert observer.schedule.call_count == 2
            returned = [r for r in caplog.records if "returned" in r.message]
            assert len(returned) == 1
            assert watcher._queue.qsize() == 1
            job_collection, folded = watcher._queue.get_nowait()
            watcher._queue.task_done()
            assert job_collection.name == "notes"
            assert folded.needs_reconcile is True
            assert folded.index_candidates == set()
            assert folded.remove_candidates == set()
        finally:
            if watcher is not None:
                watcher.stop(flush=False)
            db.close()

    def test_burst_for_missing_root_hits_d11_guard_no_sweep(self, tmp_path, monkeypatch) -> None:
        """Edge (adjacency): a burst for a vanished root is a missing event, zero counts."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
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

        notes.rename(tmp_path / "notes-gone")
        events: list[str] = []
        results: list[IncrementalResult] = []
        db = Database(db_path)
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            watcher = FileWatcher(
                [coll],
                db.connection,
                db_path,
                WatchConfig(on_event=events.append, on_batch=lambda _c, r: results.append(r)),
            )
            watcher._settled_callback(coll)([FileModifiedEvent(str(doc_file))])
            watcher._drain_once()
        finally:
            db.close()

        assert "missing notes" in events
        assert results == [IncrementalResult()]
        assert _doc_paths(db_path) == {str(doc_file)}


DIM = 8


def _embed_manager_mock(
    dim: int = DIM,
    conn: sqlite3.Connection | None = None,
    embed_txn_flags: list[bool] | None = None,
    sequence: list[str] | None = None,
) -> MagicMock:
    """Build a mocked EmbeddingManager producing deterministic dim-length vectors.

    ``conn``/``embed_txn_flags``: when both given, every embed() call records
    ``conn.in_transaction`` at call time (the D-09 boundary proof).
    ``sequence``: when given, every embed() call appends "embed" (lock-order proof).
    """
    manager = MagicMock()
    manager.get_model_info.return_value = {
        "loaded": True,
        "model_id": "test-model",
        "embedding_dim": dim,
    }

    def fake_embed(texts: list[str], **_kwargs: object) -> MagicMock:
        if conn is not None and embed_txn_flags is not None:
            embed_txn_flags.append(conn.in_transaction)
        if sequence is not None:
            sequence.append("embed")
        vectors = [[0.1] * dim for _ in texts]
        return MagicMock(embeddings=vectors)

    manager.embed.side_effect = fake_embed
    return manager


def _chunk_rows(check: sqlite3.Connection, path: Path) -> list[tuple]:
    """Chunk rows (sequence + LEFT JOINed vector id) for one document path."""
    return check.execute(
        """
        SELECT c.sequence, e.chunk_id
        FROM document_chunks c
        LEFT JOIN document_embeddings e ON e.chunk_id = c.id
        WHERE c.document_id = (SELECT id FROM documents WHERE path = ?)
        ORDER BY c.sequence
        """,
        (str(path.resolve()),),
    ).fetchall()


class TestEmbedDepth:
    """The --embed inline depth (D-09/D-10, LIVE-05), mocked at the manager boundary.

    Real tmp DB with a FLOAT[8] vec0 table; chunk/embedding rows are asserted
    through fresh connections. Embedding compute must never run inside an
    open write transaction.
    """

    def _run_burst(
        self,
        watcher: FileWatcher,
        coll: Collection,
        file_path: Path,
    ) -> None:
        """Fold one modified-file burst and drain it on the calling thread."""
        watcher._settled_callback(coll)([FileModifiedEvent(str(file_path))])
        watcher._drain_once()

    @staticmethod
    def _check_conn(db_path: Path) -> sqlite3.Connection:
        """Fresh factory connection (sqlite-vec loaded) for vector-table reads."""
        from sif.database.factory import create_connection

        return create_connection(Path(db_path))

    def _prepare_two_changed_docs(self, tmp_path, monkeypatch) -> tuple[Path, Path, Path]:
        """Seed two indexed docs, edit both; returns (db_path, doc_a, doc_b)."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_a = notes / "a.md"
        doc_b = notes / "b.md"
        doc_a.write_text(BODY_ALPHA, encoding="utf-8")
        doc_b.write_text(BODY_BETA, encoding="utf-8")
        _seed_collection(db_path, notes)
        indexer, db, coll = _open_indexer(db_path)
        try:
            assert indexer.update_collection(coll) == IncrementalResult(2, 0, 0)
        finally:
            db.close()
        doc_a.write_text("# A2\n\n" + ("Alpha two text. " * 40), encoding="utf-8")
        doc_b.write_text("# B2\n\n" + ("Beta two text. " * 40), encoding="utf-8")
        return db_path, doc_a, doc_b

    def test_default_depth_writes_document_but_zero_chunks_and_vectors(
        self, tmp_path, monkeypatch
    ) -> None:
        """LIVE-05/D-10: a burst without embed depth purges/writes nothing vector-side."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        db = Database(db_path)
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            watcher = FileWatcher([coll], db.connection, db_path)
            self._run_burst(watcher, coll, doc_file)
        finally:
            db.close()

        check = self._check_conn(db_path)
        try:
            doc = check.execute(
                "SELECT id FROM documents WHERE path = ?", (str(doc_file.resolve()),)
            ).fetchone()
            assert doc is not None
            assert check.execute("SELECT COUNT(*) FROM document_chunks").fetchone()[0] == 0
            assert check.execute("SELECT COUNT(*) FROM document_embeddings").fetchone()[0] == 0
        finally:
            check.close()

    def test_embed_depth_writes_chunks_and_vectors(self, tmp_path, monkeypatch) -> None:
        """D-09: embed depth chunks the changed doc and persists vectors."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        manager = _embed_manager_mock()
        db = Database(db_path)
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            with (
                patch("sif.config.settings.get_settings", return_value=_test_settings()),
                patch(
                    "sif.embedding.manager.EmbeddingManager.from_settings",
                    return_value=manager,
                ),
            ):
                watcher = FileWatcher([coll], db.connection, db_path, WatchConfig(depth="embed"))
                self._run_burst(watcher, coll, doc_file)
        finally:
            db.close()

        check = self._check_conn(db_path)
        try:
            rows = check.execute(
                """
                SELECT c.document_id, c.sequence, e.chunk_id
                FROM document_chunks c
                LEFT JOIN document_embeddings e ON e.chunk_id = c.id
                WHERE c.document_id = (SELECT id FROM documents WHERE path = ?)
                ORDER BY c.sequence
                """,
                (str(doc_file.resolve()),),
            ).fetchall()
        finally:
            check.close()

        assert len(rows) >= 1
        assert [row[1] for row in rows] == list(range(len(rows)))
        assert all(row[2] is not None for row in rows)

    def test_embed_compute_runs_outside_any_write_transaction(self, tmp_path, monkeypatch) -> None:
        """D-09/Pitfall 5: conn.in_transaction is False at every embed() call.

        The vector-write transaction opens only AFTER embed returns — proven
        by recording in_transaction at chunk-create time and observing it
        True there while the embed-time flags are all False, with the
        transaction closed again once the leg finishes.
        """
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        embed_txn_flags: list[bool] = []
        write_txn_flags: list[bool] = []
        original_create = DocumentChunkRepository.create

        def recording_create(self: DocumentChunkRepository, chunk: object) -> object:
            result = original_create(self, chunk)  # type: ignore[arg-type]
            # Recorded AFTER the insert: the legacy implicit BEGIN fires on
            # the first DML, so pre-insert flags would read autocommit.
            write_txn_flags.append(self.db.in_transaction)
            return result

        monkeypatch.setattr(DocumentChunkRepository, "create", recording_create)

        db = Database(db_path)
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            manager = _embed_manager_mock(conn=db.connection, embed_txn_flags=embed_txn_flags)
            with (
                patch("sif.config.settings.get_settings", return_value=_test_settings()),
                patch(
                    "sif.embedding.manager.EmbeddingManager.from_settings",
                    return_value=manager,
                ),
            ):
                watcher = FileWatcher([coll], db.connection, db_path, WatchConfig(depth="embed"))
                self._run_burst(watcher, coll, doc_file)
                assert db.connection.in_transaction is False
        finally:
            db.close()

        assert len(embed_txn_flags) >= 1
        assert all(flag is False for flag in embed_txn_flags)
        assert len(write_txn_flags) >= 1
        assert all(flag is True for flag in write_txn_flags)

    def test_dimension_mismatch_fails_soft_and_disables_embed_for_session(
        self, tmp_path, monkeypatch
    ) -> None:
        """First-use check: 768-dim model vs FLOAT[8] schema -> one error event,
        embed disabled for the session, BM25 freshness continues."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        manager = _embed_manager_mock(dim=768)
        events: list[str] = []
        results: list[IncrementalResult] = []
        db = Database(db_path)
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            with (
                patch("sif.config.settings.get_settings", return_value=_test_settings()),
                patch(
                    "sif.embedding.manager.EmbeddingManager.from_settings",
                    return_value=manager,
                ) as from_settings,
            ):
                watcher = FileWatcher(
                    [coll],
                    db.connection,
                    db_path,
                    WatchConfig(
                        depth="embed",
                        on_event=events.append,
                        on_batch=lambda _c, result: results.append(result),
                    ),
                )
                doc_file.write_text(BODY_BETA, encoding="utf-8")
                self._run_burst(watcher, coll, doc_file)
                doc_file.write_text("# Third\n\n" + ("Gamma text. " * 40), encoding="utf-8")
                self._run_burst(watcher, coll, doc_file)
                assert from_settings.call_count == 1
        finally:
            db.close()

        errors = [e for e in events if e.startswith("error ")]
        assert len(errors) == 1
        assert "768" in errors[0]
        assert "8" in errors[0]
        # BM25 freshness continued through both bursts.
        assert [r.added + r.updated for r in results] == [1, 1]
        manager.embed.assert_not_called()
        check = sqlite3.connect(str(db_path))
        try:
            assert check.execute("SELECT COUNT(*) FROM document_chunks").fetchone()[0] == 0
        finally:
            check.close()

    def test_model_lazy_loads_on_first_embed_burst_and_stays_cached(
        self, tmp_path, monkeypatch
    ) -> None:
        """D-09: from_settings/load_model run at first embed work, not at
        construction; one cached load across bursts."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        manager = _embed_manager_mock()
        db = Database(db_path)
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            with (
                patch("sif.config.settings.get_settings", return_value=_test_settings()),
                patch(
                    "sif.embedding.manager.EmbeddingManager.from_settings",
                    return_value=manager,
                ) as from_settings,
            ):
                watcher = FileWatcher([coll], db.connection, db_path, WatchConfig(depth="embed"))
                assert from_settings.call_count == 0
                assert manager.load_model.call_count == 0

                self._run_burst(watcher, coll, doc_file)
                assert from_settings.call_count == 1
                assert manager.load_model.call_count == 1

                doc_file.write_text(BODY_BETA, encoding="utf-8")
                self._run_burst(watcher, coll, doc_file)
                assert from_settings.call_count == 1
                assert manager.load_model.call_count == 1
        finally:
            db.close()

    def test_embed_runs_inside_the_same_per_burst_lock_window(self, tmp_path, monkeypatch) -> None:
        """D-09: one index_lock enter/exit spans the BM25 leg AND the embed leg."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        sequence: list[str] = []

        @contextmanager
        def recording_lock(_db_path: Path, _timeout_s: float, _on_wait=None):
            sequence.append("enter")
            try:
                yield
            finally:
                sequence.append("exit")

        monkeypatch.setattr(watcher_module, "index_lock", recording_lock)

        manager = _embed_manager_mock(sequence=sequence)
        db = Database(db_path)
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            with (
                patch("sif.config.settings.get_settings", return_value=_test_settings()),
                patch(
                    "sif.embedding.manager.EmbeddingManager.from_settings",
                    return_value=manager,
                ),
            ):
                watcher = FileWatcher([coll], db.connection, db_path, WatchConfig(depth="embed"))
                self._run_burst(watcher, coll, doc_file)
        finally:
            db.close()

        assert sequence == ["enter", "embed", "exit"]

    def test_embed_failure_emits_error_continues_and_retries_next_burst(
        self, tmp_path, monkeypatch
    ) -> None:
        """WR-01: a per-path embed failure emits one error event, the burst's
        remaining candidate still embeds, and a later burst — whose checksum
        diff alone would never re-select the failed path — retries it to
        completion."""
        db_path, doc_a, doc_b = self._prepare_two_changed_docs(tmp_path, monkeypatch)

        def flaky_embed(texts: list[str], **_kwargs: object) -> MagicMock:
            if manager.embed.call_count == 1:
                raise RuntimeError("provider 503")
            return MagicMock(embeddings=[[0.1] * DIM for _ in texts])

        manager = _embed_manager_mock()
        manager.embed.side_effect = flaky_embed

        events: list[str] = []
        db = Database(db_path)
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            with (
                patch("sif.config.settings.get_settings", return_value=_test_settings()),
                patch(
                    "sif.embedding.manager.EmbeddingManager.from_settings",
                    return_value=manager,
                ),
            ):
                watcher = FileWatcher(
                    [coll],
                    db.connection,
                    db_path,
                    WatchConfig(depth="embed", on_event=events.append),
                )
                # Burst 1: both changed; a.md (sorted first) fails embed,
                # b.md — the remaining candidate — still embeds.
                watcher._settled_callback(coll)(
                    [FileModifiedEvent(str(doc_a)), FileModifiedEvent(str(doc_b))]
                )
                watcher._drain_once()
                assert manager.embed.call_count == 2

                # Burst 2: a.md touched WITHOUT a content change — the
                # checksum diff is empty; only the retry set can heal it.
                watcher._settled_callback(coll)([FileModifiedEvent(str(doc_a))])
                watcher._drain_once()
                assert manager.embed.call_count == 3
        finally:
            db.close()

        errors = [e for e in events if e.startswith("error ")]
        assert len(errors) == 1
        assert str(doc_a.resolve()) in errors[0]
        assert "provider 503" in errors[0]

        check = self._check_conn(db_path)
        try:
            rows_a = _chunk_rows(check, doc_a)
            rows_b = _chunk_rows(check, doc_b)
        finally:
            check.close()

        # Burst 1 kept b.md fully embedded; burst 2's retry healed a.md.
        assert len(rows_a) >= 1
        assert all(row[1] is not None for row in rows_a)
        assert len(rows_b) >= 1
        assert all(row[1] is not None for row in rows_b)

    def test_reconcile_at_embed_depth_rewrites_purged_vectors(self, tmp_path, monkeypatch):
        """IN-04: a reconcile job (directory move, returning root) at embed
        depth re-embeds the documents its BM25 pass changed — without the
        checksum-diff feed, the update branch's chunk+vector purge would
        strand them vector-less under fresh checksums that no later burst's
        change detector ever re-selects."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        manager = _embed_manager_mock()
        db = Database(db_path)
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            with (
                patch("sif.config.settings.get_settings", return_value=_test_settings()),
                patch(
                    "sif.embedding.manager.EmbeddingManager.from_settings",
                    return_value=manager,
                ),
            ):
                watcher = FileWatcher([coll], db.connection, db_path, WatchConfig(depth="embed"))

                # Reconcile 1 (startup drift): the new doc's checksum
                # appears (None -> fresh) and the embed leg writes vectors.
                watcher._run_job((coll, FoldResult(needs_reconcile=True)))
                assert manager.embed.call_count == 1

                # Drift while unwatched, then reconcile 2: the BM25 update
                # branch purges chunks and embeddings, and the embed leg
                # must rewrite them in the same job.
                doc_file.write_text("# Drifted\n\n" + ("Changed text. " * 60), encoding="utf-8")
                watcher._run_job((coll, FoldResult(needs_reconcile=True)))
                assert manager.embed.call_count == 2
        finally:
            db.close()

        check = self._check_conn(db_path)
        try:
            rows = _chunk_rows(check, doc_file)
        finally:
            check.close()

        assert len(rows) >= 1
        assert all(row[1] is not None for row in rows)


class TestLiveRescope:
    """D-15 live rescope of the watched collection set, zero timing.

    ``rescope`` is invoked directly on the test thread with the worker
    quiesced (a no-op ``_worker_loop`` is patched in before ``start``), so
    every queue/state assertion is deterministic. The observer is the
    battery's usual MagicMock; debouncers stay real.
    """

    def _seed(self, tmp_path, monkeypatch) -> tuple[Path, Path, Path]:
        """Seed alpha+beta collections with one indexed doc each."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        alpha = tmp_path / "alpha"
        beta = tmp_path / "beta"
        alpha.mkdir()
        beta.mkdir()
        (alpha / "a.md").write_text(BODY_ALPHA, encoding="utf-8")
        (beta / "b.md").write_text(BODY_BETA, encoding="utf-8")
        _seed_collections(db_path, {"alpha": alpha, "beta": beta})
        return db_path, alpha, beta

    def _start_watcher(
        self,
        db_path: Path,
        names: tuple[str, ...],
        monkeypatch,
        config: WatchConfig | None = None,
        extra_registered: tuple[str, ...] = (),
    ) -> tuple[FileWatcher, MagicMock, dict[str, object], Database]:
        """Open the DB, build+start a quiesced-worker watcher over ``names``.

        ``extra_registered`` names must exist in the DB but stay unwatched —
        the provider-scoping probe. Returns (watcher, observer, colls, db).
        """
        observer_cls = MagicMock()
        monkeypatch.setattr(watcher_module, "Observer", observer_cls)
        db = Database(db_path)
        from sif.database.repositories import CollectionRepository

        repo = CollectionRepository(db.connection)
        colls: dict[str, object] = {}
        for name in (*names, *extra_registered):
            coll = repo.get_by_name(name)
            assert coll is not None
            colls[name] = coll
        watcher = FileWatcher([colls[n] for n in names], db.connection, db_path, config)
        monkeypatch.setattr(watcher, "_worker_loop", lambda: None)
        watcher.start()
        return watcher, observer_cls.return_value, colls, db

    @staticmethod
    def _teardown(watcher: FileWatcher | None, db: Database) -> None:
        if watcher is not None:
            watcher.stop(flush=False)
        db.close()

    def test_rescope_added_collection_schedules_and_reconciles(self, tmp_path, monkeypatch) -> None:
        """An added collection arms its debouncer, schedules a watch handle,
        and gets one reconcile job that indexes a file under the new root."""
        db_path, _alpha, beta = self._seed(tmp_path, monkeypatch)
        # A NEW file lands under beta's root before the rescope.
        new_file = beta / "new.md"
        new_file.write_text("# New note\n\n" + ("New body text. " * 30), encoding="utf-8")

        watcher, observer, colls, db = self._start_watcher(
            db_path, ("alpha",), monkeypatch, extra_registered=("beta",)
        )
        try:
            assert observer.schedule.call_count == 1
            watcher.rescope([colls["alpha"], colls["beta"]])

            beta_state = watcher._watch_states["beta"]
            assert beta_state.debouncer is not None
            assert observer.schedule.call_count == 2
            # The exact recovery-return job shape for the added root.
            assert watcher._queue.qsize() == 1
            job_coll, folded = watcher._queue.get_nowait()
            watcher._queue.task_done()
            assert job_coll.name == "beta"
            assert folded == FoldResult(needs_reconcile=True)
            # Drive the job: the file under beta's root becomes indexed.
            watcher._queue.put((job_coll, folded))
            watcher._drain_once()
        finally:
            self._teardown(watcher, db)

        assert str(new_file.resolve()) in _doc_paths(db_path)

    def test_rescope_removed_collection_unschedules_and_preserves_documents(
        self, tmp_path, monkeypatch
    ) -> None:
        """A removed collection is unscheduled (handle released, debouncer
        stopped), its document rows survive, and changes under its root no
        longer produce jobs."""
        db_path, alpha, beta = self._seed(tmp_path, monkeypatch)

        handle_alpha, handle_beta = MagicMock(), MagicMock()
        observer_cls = MagicMock()
        monkeypatch.setattr(watcher_module, "Observer", observer_cls)
        observer = observer_cls.return_value
        observer.schedule.side_effect = [handle_alpha, handle_beta]

        db = Database(db_path)
        watcher = None
        try:
            from sif.database.repositories import CollectionRepository

            repo = CollectionRepository(db.connection)
            coll_a = repo.get_by_name("alpha")
            coll_b = repo.get_by_name("beta")
            assert coll_a is not None
            assert coll_b is not None
            watcher = FileWatcher([coll_a, coll_b], db.connection, db_path)
            monkeypatch.setattr(watcher, "_worker_loop", lambda: None)
            watcher.start()
            assert observer.schedule.call_count == 2

            beta_debouncer = watcher._watch_states["beta"].debouncer
            assert beta_debouncer is not None
            watcher.rescope([coll_a])

            observer.unschedule.assert_called_once_with(handle_beta)
            assert beta_debouncer.is_alive() is False
            assert set(watcher._watch_states) == {"alpha"}
            # Documents of the removed collection are never touched.
            assert _doc_paths(db_path) == {
                str((alpha / "a.md").resolve()),
                str((beta / "b.md").resolve()),
            }
            # A change under beta's root no longer produces a job: the
            # stopped debouncer accepts the event but its thread is gone.
            beta_debouncer.handle_event(FileModifiedEvent(str(beta / "b.md")))
            assert watcher._queue.qsize() == 0
        finally:
            self._teardown(watcher, db)

    def test_rescope_adds_exactly_the_providers_set_nothing_more(
        self, tmp_path, monkeypatch
    ) -> None:
        """A registered-but-withheld collection is never pulled in: the tick's
        rescope consults the provider once per interval and adds exactly its
        return value — the -c-filter subtlety."""
        db_path, _alpha, _beta = self._seed(tmp_path, monkeypatch)
        # gamma: registered in the DB, outside the host's eligible set.
        gamma = tmp_path / "gamma"
        gamma.mkdir()
        (gamma / "g.md").write_text(BODY_ALPHA, encoding="utf-8")
        db = Database(db_path)
        with patch("sif.config.settings.get_settings", return_value=_test_settings()):
            with db.connection:
                from sif.database.repositories import CollectionRepository

                CollectionRepository(db.connection).create(
                    Collection(name="gamma", path=str(gamma))
                )
        db.close()

        provider_calls: list[float] = []
        clock = {"now": 100.0}

        def provider() -> list[object]:
            provider_calls.append(clock["now"])
            return [colls["alpha"]]

        config = WatchConfig(
            rescope_provider=provider,
            rescope_interval=60.0,
            now=lambda: clock["now"],
        )

        watcher, observer, colls, db = self._start_watcher(
            db_path, ("alpha",), monkeypatch, config, extra_registered=("beta", "gamma")
        )
        try:
            watcher._on_tick()  # seeds the deadline; provider not yet called
            assert provider_calls == []
            clock["now"] = 159.9
            watcher._on_tick()  # not due yet
            assert provider_calls == []
            clock["now"] = 160.0
            watcher._on_tick()  # due: provider consulted once
            clock["now"] = 219.9
            watcher._on_tick()
            clock["now"] = 220.0
            watcher._on_tick()

            assert provider_calls == [160.0, 220.0]
            assert set(watcher._watch_states) == {"alpha"}
            assert observer.schedule.call_count == 1
        finally:
            self._teardown(watcher, db)

    def test_no_provider_default_never_changes_watch_set(self, tmp_path, monkeypatch) -> None:
        """Opt-in default: with no rescope_provider, ticks (recovery and the
        full tick body) never change _watch_states membership — the
        foreground MVP host keeps its restart-on-change behavior (D-15)."""
        db_path, _alpha, _beta = self._seed(tmp_path, monkeypatch)

        watcher, observer, _colls, db = self._start_watcher(db_path, ("alpha", "beta"), monkeypatch)
        try:
            assert watcher._config.rescope_provider is None
            before = set(watcher._watch_states)
            watcher.recovery_tick()
            watcher.recovery_tick()
            watcher._on_tick()
            watcher._on_tick()
            assert set(watcher._watch_states) == before == {"alpha", "beta"}
            assert observer.unschedule.call_count == 0
            assert observer.schedule.call_count == 2
        finally:
            self._teardown(watcher, db)


class TestWatchSettings:
    """The three Phase 13 host-behavior settings (D-04 + interval discretion)."""

    _VARS = ("SIF_MCP_WATCH", "SIF_WATCH_RESCOPE_INTERVAL", "SIF_WATCH_CHECKPOINT_INTERVAL")

    def test_defaults_off_and_minutes_scale(self, monkeypatch) -> None:
        """Defaults: MCP watch off, rescope 60s, checkpoint 300s (disabled at 0
        is the WatchConfig default; the settings default is the cadence)."""
        _delenv_settings_vars(monkeypatch)
        for var in self._VARS:
            monkeypatch.delenv(var, raising=False)
        settings = Settings(embedding_dim=8, model_name="test", cache_embeddings=False)
        assert settings.mcp_watch is False
        assert settings.watch_rescope_interval == 60.0
        assert settings.watch_checkpoint_interval == 300.0

    def test_sif_env_spellings_resolve(self, monkeypatch) -> None:
        """SIF_MCP_WATCH / SIF_WATCH_RESCOPE_INTERVAL / SIF_WATCH_CHECKPOINT_INTERVAL
        env spellings resolve through the standard SIF_ prefix (D-04)."""
        _delenv_settings_vars(monkeypatch)
        for var in self._VARS:
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("SIF_MCP_WATCH", "1")
        monkeypatch.setenv("SIF_WATCH_RESCOPE_INTERVAL", "2")
        monkeypatch.setenv("SIF_WATCH_CHECKPOINT_INTERVAL", "0")
        settings = Settings()
        assert settings.mcp_watch is True
        assert settings.watch_rescope_interval == 2.0
        assert settings.watch_checkpoint_interval == 0.0


class TestIdleCheckpoint:
    """D-16 idle WAL checkpoint riding the tick, zero timing.

    The tick is driven directly with an injectable clock; the connection is
    a _CheckpointSpy wrapping a real DB connection so burst jobs stay real.
    """

    def _make(self, tmp_path, monkeypatch, *, checkpoint_interval, busy=False):
        """Seed alpha, start a quiesced-worker watcher over the spy connection."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        alpha = tmp_path / "alpha"
        alpha.mkdir()
        (alpha / "a.md").write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collections(db_path, {"alpha": alpha})

        clock = {"now": 100.0}
        observer_cls = MagicMock()
        monkeypatch.setattr(watcher_module, "Observer", observer_cls)
        db = Database(db_path)
        spy = _CheckpointSpy(db.connection, busy=busy)
        from sif.database.repositories import CollectionRepository

        coll = CollectionRepository(spy).get_by_name("alpha")
        assert coll is not None
        watcher = FileWatcher(
            [coll],
            spy,
            db_path,
            WatchConfig(checkpoint_interval=checkpoint_interval, now=lambda: clock["now"]),
        )
        monkeypatch.setattr(watcher, "_worker_loop", lambda: None)
        watcher.start()
        return watcher, spy, clock, alpha, coll

    def test_checkpoint_runs_once_when_due(self, tmp_path, monkeypatch) -> None:
        """Deadline elapsed + idle -> exactly one TRUNCATE checkpoint on the
        worker connection; one per interval, never two inside one tick."""
        watcher, spy, clock, _alpha, _coll = self._make(
            tmp_path, monkeypatch, checkpoint_interval=300.0
        )
        try:
            watcher._on_tick()  # t=100: seeds the deadline at 400
            assert spy.calls == 0
            clock["now"] = 399.9
            watcher._on_tick()  # not due yet
            assert spy.calls == 0
            clock["now"] = 400.0
            watcher._on_tick()  # due and idle
            assert spy.calls == 1
            clock["now"] = 699.9
            watcher._on_tick()  # deadline was reset: not due yet
            assert spy.calls == 1
            clock["now"] = 700.0
            watcher._on_tick()
            assert spy.calls == 2
        finally:
            watcher.stop(flush=False)

    def test_busy_row_skips_silently_and_resets_deadline(
        self, tmp_path, monkeypatch, caplog
    ) -> None:
        """A busy result row means contention: no retry inside the tick, NO
        warning log records, and the deadline still resets for the next
        interval (Pitfall 7)."""
        watcher, spy, clock, _alpha, _coll = self._make(
            tmp_path, monkeypatch, checkpoint_interval=300.0, busy=True
        )
        try:
            watcher._on_tick()  # t=100: seeds the deadline at 400
            assert spy.calls == 0
            with caplog.at_level(logging.WARNING, logger="sif.indexing.watcher"):
                clock["now"] = 400.0
                watcher._on_tick()
                assert spy.calls == 1
                clock["now"] = 401.0
                watcher._on_tick()  # deadline reset: no immediate retry
                assert spy.calls == 1
                clock["now"] = 700.0
                watcher._on_tick()  # next interval attempts again
                assert spy.calls == 2
            assert [r for r in caplog.records if "checkpoint" in r.message] == []
        finally:
            watcher.stop(flush=False)

    def test_recent_burst_postpones_checkpoint(self, tmp_path, monkeypatch) -> None:
        """A job completed within the recent window (restat_interval) means
        the writer was active: the due checkpoint is postponed a full
        interval, then runs once the burst is stale."""
        watcher, spy, clock, alpha, coll = self._make(
            tmp_path, monkeypatch, checkpoint_interval=300.0
        )
        try:
            watcher._on_tick()  # t=100: deadline 400
            # A real burst job completes at t=398 (content untouched: the
            # job is real worker activity even though it indexes nothing).
            clock["now"] = 398.0
            watcher._settled_callback(coll)([FileModifiedEvent(str(alpha / "a.md"))])
            watcher._drain_once()
            clock["now"] = 400.0
            watcher._on_tick()  # due, but 400-398 < restat window (5s)
            assert spy.calls == 0
            clock["now"] = 700.0  # deadline was reset; burst now stale
            watcher._on_tick()
            assert spy.calls == 1
        finally:
            watcher.stop(flush=False)

    def test_disabled_by_default_never_checkpoints(self, tmp_path, monkeypatch) -> None:
        """checkpoint_interval=0 (the WatchConfig default): driven ticks never
        execute a checkpoint — shutdown checkpointing stays the final word."""
        assert WatchConfig().checkpoint_interval == 0.0
        watcher, spy, clock, _alpha, _coll = self._make(
            tmp_path, monkeypatch, checkpoint_interval=0.0
        )
        try:
            for now in (100.0, 1e6, 1e9):
                clock["now"] = now
                watcher._on_tick()
            assert spy.calls == 0
        finally:
            watcher.stop(flush=False)


class TestScheduleFailure:
    """D-17: an OSError from observer.schedule warns once with the inotify
    remedy, other roots keep watching, and the tick retries silently."""

    _REMEDY = "fs.inotify.max_user_watches"

    def test_schedule_failure_at_start_warns_once_others_watch_and_tick_retries(
        self, tmp_path, monkeypatch, caplog
    ) -> None:
        """One root failing to schedule at start: exactly one warning with
        the cause and the max_user_watches remedy, the sibling root watches
        on, the failed root stays tracked (missing) and the tick retries it
        without a second warning."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        alpha = tmp_path / "alpha"
        beta = tmp_path / "beta"
        alpha.mkdir()
        beta.mkdir()
        (alpha / "a.md").write_text(BODY_ALPHA, encoding="utf-8")
        (beta / "b.md").write_text(BODY_BETA, encoding="utf-8")
        _seed_collections(db_path, {"alpha": alpha, "beta": beta})

        observer_cls = MagicMock()
        monkeypatch.setattr(watcher_module, "Observer", observer_cls)
        observer = observer_cls.return_value
        observer.schedule.side_effect = [
            OSError(errno.ENOSPC, "No space left on device"),
            MagicMock(),
        ]

        db = Database(db_path)
        watcher = None
        try:
            from sif.database.repositories import CollectionRepository

            repo = CollectionRepository(db.connection)
            coll_a = repo.get_by_name("alpha")
            coll_b = repo.get_by_name("beta")
            assert coll_a is not None
            assert coll_b is not None
            watcher = FileWatcher([coll_a, coll_b], db.connection, db_path)
            monkeypatch.setattr(watcher, "_worker_loop", lambda: None)
            with caplog.at_level(logging.WARNING, logger="sif.indexing.watcher"):
                watcher.start()
                assert observer.schedule.call_count == 2  # alpha raised, beta armed
                assert watcher._watch_states["alpha"].missing is True
                assert watcher._watch_states["beta"].handle is not None

                # The tick retries the failed root; schedule now succeeds.
                observer.schedule.side_effect = MagicMock()
                watcher.recovery_tick()
                watcher.recovery_tick()  # second retry-target is a no-op

            remedy = [r for r in caplog.records if self._REMEDY in r.message]
            assert len(remedy) == 1
            assert "No space left on device" in remedy[0].message
            assert "28" in remedy[0].message  # errno cause carried
            assert observer.schedule.call_count == 3
            assert watcher._watch_states["alpha"].missing is False
            # The successful retry enqueued exactly one reconcile for alpha.
            assert watcher._queue.qsize() == 1
            job_coll, folded = watcher._queue.get_nowait()
            watcher._queue.task_done()
            assert job_coll.name == "alpha"
            assert folded.needs_reconcile is True
        finally:
            if watcher is not None:
                watcher.stop(flush=False)
            db.close()

    def test_rescope_add_with_schedule_failure_rest_of_diff_proceeds(
        self, tmp_path, monkeypatch, caplog
    ) -> None:
        """Rescope adding two roots where one fails to schedule: one warning
        with the remedy, the failed root stays missing, the sibling add
        completes with its reconcile job."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        alpha = tmp_path / "alpha"
        beta = tmp_path / "beta"
        gamma = tmp_path / "gamma"
        for root in (alpha, beta, gamma):
            root.mkdir()
        (alpha / "a.md").write_text(BODY_ALPHA, encoding="utf-8")
        (beta / "b.md").write_text(BODY_BETA, encoding="utf-8")
        (gamma / "g.md").write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collections(db_path, {"alpha": alpha, "beta": beta, "gamma": gamma})

        observer_cls = MagicMock()
        monkeypatch.setattr(watcher_module, "Observer", observer_cls)
        observer = observer_cls.return_value
        observer.schedule.side_effect = [MagicMock()]  # alpha at start

        db = Database(db_path)
        watcher = None
        try:
            from sif.database.repositories import CollectionRepository

            repo = CollectionRepository(db.connection)
            coll_a = repo.get_by_name("alpha")
            coll_b = repo.get_by_name("beta")
            coll_g = repo.get_by_name("gamma")
            assert coll_a is not None
            assert coll_b is not None
            assert coll_g is not None
            watcher = FileWatcher([coll_a], db.connection, db_path)
            monkeypatch.setattr(watcher, "_worker_loop", lambda: None)
            watcher.start()
            assert observer.schedule.call_count == 1

            # Rescope adds beta (fails ENOSPC) then gamma (succeeds).
            observer.schedule.side_effect = [
                OSError(errno.ENOSPC, "No space left on device"),
                MagicMock(),
            ]
            with caplog.at_level(logging.WARNING, logger="sif.indexing.watcher"):
                watcher.rescope([coll_a, coll_b, coll_g])

            remedy = [r for r in caplog.records if self._REMEDY in r.message]
            assert len(remedy) == 1
            assert watcher._watch_states["beta"].missing is True
            assert watcher._watch_states["beta"].debouncer is None
            assert watcher._watch_states["gamma"].handle is not None
            assert set(watcher._watch_states) == {"alpha", "beta", "gamma"}
            # Only gamma's add produced a job; beta (not actually being
            # watched) must not get a reconcile.
            assert watcher._queue.qsize() == 1
            job_coll, _folded = watcher._queue.get_nowait()
            watcher._queue.task_done()
            assert job_coll.name == "gamma"
        finally:
            if watcher is not None:
                watcher.stop(flush=False)
            db.close()
