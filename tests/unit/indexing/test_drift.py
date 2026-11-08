"""Unit tests for the pre-search drift check (LIVE-10, D-01..D-07).

Deterministic battery: drift is created with explicit ``os.utime``
timestamps, content writes, and ``unlink`` — never ``sleep()``. Clean-path
assertions are structural (no lock file, stored rows unchanged), not
latency (11-D08/D-09, 12-D15 culture).
"""

from __future__ import annotations

import os
import shutil
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from sif.config.settings import Settings
from sif.core.models import Collection
from sif.database.database import Database
from sif.database.repositories import CollectionRepository
from sif.indexing.drift import DriftReport, detect_drift, refresh_drifted
from sif.indexing.incremental import IncrementalIndexer, IncrementalResult


BODY_ALPHA = "# Heading One\n\n" + ("Alpha paragraph text. " * 50)
BODY_BETA = "# Heading Two\n\n" + ("Beta paragraph text. " * 50)

TOUCH_MTIME = 1_700_000_000


def _delenv_settings_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep Settings construction hermetic against a developer shell."""
    for var in ("SIF_EMBEDDING_DIM", "SIF_MODEL_TYPE", "SIF_MODEL_NAME"):
        monkeypatch.delenv(var, raising=False)


def _test_settings() -> Settings:
    """Build hermetic test settings."""
    return Settings(embedding_dim=8, model_name="test", cache_embeddings=False)


def _seed_and_index(db_path: Path, notes: Path) -> None:
    """Init schema, create the notes collection, and index it once."""
    db = Database(db_path)
    with patch("sif.config.settings.get_settings", return_value=_test_settings()):
        db.init_schema()
        with db.connection:
            CollectionRepository(db.connection).create(Collection(name="notes", path=str(notes)))
        coll = CollectionRepository(db.connection).get_by_name("notes")
        assert coll is not None
        IncrementalIndexer(db.connection).update_collection(coll)
    db.close()


def _open(db_path: Path) -> tuple[Database, Collection]:
    """Open the DB and load the seeded notes collection."""
    db = Database(db_path)
    coll = CollectionRepository(db.connection).get_by_name("notes")
    assert coll is not None
    return db, coll


def _doc_paths(db_path: Path) -> set[str]:
    """Read document paths through a fresh connection (query, not files)."""
    conn = sqlite3.connect(str(db_path))
    try:
        return {row[0] for row in conn.execute("SELECT path FROM documents")}
    finally:
        conn.close()


def _doc_stats(db_path: Path) -> dict[str, float]:
    """Read {path: mtime} through a fresh connection."""
    conn = sqlite3.connect(str(db_path))
    try:
        return {row[0]: row[1] for row in conn.execute("SELECT path, mtime FROM documents")}
    finally:
        conn.close()


def _doc_content(db_path: Path, path: str) -> str | None:
    """Read one document's stored content through a fresh connection."""
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute("SELECT content FROM documents WHERE path = ?", (path,)).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


class TestDetectDrift:
    """The read-only stat walk: new/edited/touched/deleted files are drift."""

    def test_clean_collection_yields_empty_report(self, tmp_path, monkeypatch) -> None:
        """A freshly indexed collection reports zero drift (SC2 clean path)."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "drift.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "a.md").write_text(BODY_ALPHA, encoding="utf-8")
        _seed_and_index(db_path, notes)

        db, coll = _open(db_path)
        try:
            report = detect_drift(db.connection, [coll])
        finally:
            db.close()

        assert report.paths_by_collection == {}
        assert report.total_count == 0

    def test_touch_drift_detected_via_os_utime(self, tmp_path, monkeypatch) -> None:
        """A pure mtime move (content unchanged) is drift — deterministic timestamp."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "drift.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc = notes / "a.md"
        doc.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_and_index(db_path, notes)
        os.utime(doc, (TOUCH_MTIME, TOUCH_MTIME))

        db, coll = _open(db_path)
        try:
            report = detect_drift(db.connection, [coll])
        finally:
            db.close()

        assert {str(p) for p in report.paths_by_collection[coll.id]} == {str(doc.resolve())}
        assert report.total_count == 1

    def test_content_edit_drift_detected(self, tmp_path, monkeypatch) -> None:
        """A content write moves mtime and is drift."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "drift.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc = notes / "a.md"
        doc.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_and_index(db_path, notes)
        doc.write_text(BODY_BETA, encoding="utf-8")

        db, coll = _open(db_path)
        try:
            report = detect_drift(db.connection, [coll])
        finally:
            db.close()

        assert {str(p) for p in report.paths_by_collection[coll.id]} == {str(doc.resolve())}

    def test_new_file_detected(self, tmp_path, monkeypatch) -> None:
        """A file created after indexing is drift."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "drift.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "a.md").write_text(BODY_ALPHA, encoding="utf-8")
        _seed_and_index(db_path, notes)
        (notes / "b.md").write_text(BODY_BETA, encoding="utf-8")

        db, coll = _open(db_path)
        try:
            report = detect_drift(db.connection, [coll])
        finally:
            db.close()

        assert {str(p) for p in report.paths_by_collection[coll.id]} == {
            str((notes / "b.md").resolve())
        }

    def test_deleted_file_detected(self, tmp_path, monkeypatch) -> None:
        """A stored file gone from disk is drift (deletion candidate)."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "drift.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc = notes / "a.md"
        doc.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_and_index(db_path, notes)
        doc.unlink()

        db, coll = _open(db_path)
        try:
            report = detect_drift(db.connection, [coll])
        finally:
            db.close()

        assert {str(p) for p in report.paths_by_collection[coll.id]} == {str(doc.resolve())}

    def test_missing_root_skips_collection_without_phantom_deletion(
        self, tmp_path, monkeypatch
    ) -> None:
        """A vanished collection root skips the walk — never mass-delete drift (12-D11 mirror)."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "drift.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "a.md").write_text(BODY_ALPHA, encoding="utf-8")
        _seed_and_index(db_path, notes)
        shutil.rmtree(notes)

        db, coll = _open(db_path)
        try:
            report = detect_drift(db.connection, [coll])
        finally:
            db.close()

        # Every stored doc would look deleted if the walk ran on the missing
        # root; the guard must report nothing instead.
        assert report.paths_by_collection == {}
        assert report.total_count == 0

    def test_detect_never_creates_lock_file(self, tmp_path, monkeypatch) -> None:
        """Detection is read-only: even with drift present, no lock file appears (SC2)."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "drift.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "a.md").write_text(BODY_ALPHA, encoding="utf-8")
        _seed_and_index(db_path, notes)
        os.utime(notes / "a.md", (TOUCH_MTIME, TOUCH_MTIME))

        db, coll = _open(db_path)
        try:
            report = detect_drift(db.connection, [coll])
        finally:
            db.close()

        assert report.total_count == 1
        assert not Path(str(db_path) + ".lock").exists()


class TestRefreshDrifted:
    """The flock-wrapped BM25 burst over the drifted path set."""

    def test_refresh_updates_content_and_converges_mtime(self, tmp_path, monkeypatch) -> None:
        """An edited file is re-indexed; the stored mtime then matches disk (no re-drift)."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "drift.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc = notes / "a.md"
        doc.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_and_index(db_path, notes)
        doc.write_text(BODY_BETA, encoding="utf-8")

        db, coll = _open(db_path)
        try:
            report = detect_drift(db.connection, [coll])
            assert report.total_count == 1
            result = refresh_drifted(
                db_path, db.connection, {coll.id: coll}, report, lock_timeout=5.0
            )
        finally:
            db.close()

        assert result.updated == 1
        stored = _doc_stats(db_path)
        assert stored[str(doc.resolve())] == doc.stat().st_mtime
        assert _doc_content(db_path, str(doc.resolve())) == BODY_BETA.rstrip()

        # Stat-decides no-op: a fresh walk after the refresh finds zero drift.
        db2, coll2 = _open(db_path)
        try:
            assert detect_drift(db2.connection, [coll2]).total_count == 0
        finally:
            db2.close()

    def test_refresh_converges_touch_only_drift(self, tmp_path, monkeypatch) -> None:
        """CR-01 regression: a touched-but-unchanged file converges after ONE refresh.

        ``detect_drift`` is mtime-primary, so the checksum-skip path must
        persist the fresh mtime — otherwise a same-content touch (git
        checkout, archive extract, no-op save) is re-detected as drift on
        every subsequent search forever (the eternal lock+notice loop).
        """
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "drift.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc = notes / "a.md"
        doc.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_and_index(db_path, notes)
        os.utime(doc, (TOUCH_MTIME, TOUCH_MTIME))

        db, coll = _open(db_path)
        try:
            report = detect_drift(db.connection, [coll])
            assert report.total_count == 1
            result = refresh_drifted(
                db_path, db.connection, {coll.id: coll}, report, lock_timeout=5.0
            )
        finally:
            db.close()

        # Checksum skip (content unchanged), but the fresh mtime was persisted.
        assert result == IncrementalResult(added=0, updated=0, removed=0, unchanged=1)
        assert _doc_stats(db_path)[str(doc.resolve())] == float(TOUCH_MTIME)

        # Convergence: a fresh walk after the refresh finds zero drift.
        db2, coll2 = _open(db_path)
        try:
            assert detect_drift(db2.connection, [coll2]).total_count == 0
        finally:
            db2.close()

    def test_refresh_adds_new_and_removes_deleted_documents(self, tmp_path, monkeypatch) -> None:
        """A drifted set mixing new and deleted paths lands both outcomes."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "drift.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "a.md").write_text(BODY_ALPHA, encoding="utf-8")
        _seed_and_index(db_path, notes)
        (notes / "a.md").unlink()
        (notes / "b.md").write_text(BODY_BETA, encoding="utf-8")

        db, coll = _open(db_path)
        try:
            report = detect_drift(db.connection, [coll])
            assert report.total_count == 2
            result = refresh_drifted(
                db_path, db.connection, {coll.id: coll}, report, lock_timeout=5.0
            )
        finally:
            db.close()

        assert result.added == 1
        assert result.removed == 1
        assert _doc_paths(db_path) == {str((notes / "b.md").resolve())}

    def test_predicate_excluded_stored_doc_removed_and_converges(
        self, tmp_path, monkeypatch
    ) -> None:
        """WR-01 regression: a doc the shared predicate later excludes converges.

        ``detect_drift`` counts a stored-but-unseen path as deleted drift;
        the refresh must REMOVE it (mirroring ``_sweep_removed`` / ``sif
        index update``) instead of skipping it at the ``matches`` gate —
        otherwise the path is drift on every search forever.
        """
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "drift.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "a.md").write_text(BODY_ALPHA, encoding="utf-8")
        (notes / "secret.md").write_text(BODY_BETA, encoding="utf-8")
        _seed_and_index(db_path, notes)

        ignoring = Settings(
            embedding_dim=8,
            model_name="test",
            cache_embeddings=False,
            watch_ignore_patterns=["secret*"],
        )
        with patch("sif.config.settings.get_settings", return_value=ignoring):
            db, coll = _open(db_path)
            try:
                report = detect_drift(db.connection, [coll])
                assert report.total_count == 1
                result = refresh_drifted(
                    db_path, db.connection, {coll.id: coll}, report, lock_timeout=5.0
                )
                # Converged within the same settings regime: zero drift left.
                assert detect_drift(db.connection, [coll]).total_count == 0
            finally:
                db.close()

        assert result.removed == 1
        assert _doc_paths(db_path) == {str((notes / "a.md").resolve())}

    def test_refresh_creates_the_lock_file_only_when_working(self, tmp_path, monkeypatch) -> None:
        """index_lock lives inside refresh_drifted: present after a real burst, absent on empty."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "drift.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "a.md").write_text(BODY_ALPHA, encoding="utf-8")
        _seed_and_index(db_path, notes)

        db, coll = _open(db_path)
        try:
            # Empty report (clean index): the defensive guard must not lock.
            empty = refresh_drifted(
                db_path, db.connection, {coll.id: coll}, DriftReport(), lock_timeout=5.0
            )
        finally:
            db.close()
        assert empty == IncrementalResult()
        assert not Path(str(db_path) + ".lock").exists()

        (notes / "a.md").write_text(BODY_BETA, encoding="utf-8")
        db2, coll2 = _open(db_path)
        try:
            report = detect_drift(db2.connection, [coll2])
            refresh_drifted(db_path, db2.connection, {coll2.id: coll2}, report, lock_timeout=5.0)
        finally:
            db2.close()
        assert Path(str(db_path) + ".lock").exists()
