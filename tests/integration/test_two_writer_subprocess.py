"""Deterministic two-writer subprocess proofs for ``sif index update`` (SC2).

The parent holds/releases the derived lock file and asserts the child's
outcome — never timing races (D-08b/D-09). Both the incumbent and the waiting
loser must exit 0 (D-01/D-02); "each file indexed exactly once" is asserted
from database row state after the children exit, never from file listings
(Pitfall 5) or timing.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import time
from collections.abc import Generator
from pathlib import Path

import pytest

from sif.config.settings import get_settings
from sif.core.models import Collection
from sif.database.database import Database
from sif.database.repositories import CollectionRepository


fcntl = pytest.importorskip("fcntl", reason="flock arbitration is POSIX-only (A2)")

_NOTE_TAGS = ("alpha", "bravo", "charlie")


@pytest.fixture(autouse=True)
def hermetic_settings(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Seeding runs on default Settings; no developer-shell SIF_ vars leak in."""
    for key in [k for k in os.environ if k.startswith("SIF_")]:
        monkeypatch.delenv(key, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _lock_path(db_path: Path) -> Path:
    """Derive the lock path exactly as production code does (one per DB)."""
    return db_path.with_name(db_path.name + ".lock")


def _seed_db_with_collection(db_path: Path, notes_dir: Path) -> None:
    """Build a real index with one collection pointing at a 3-file tree."""
    notes_dir.mkdir(parents=True, exist_ok=True)
    for name, tag in zip(("a", "b", "c"), _NOTE_TAGS, strict=True):
        (notes_dir / f"{name}.md").write_text(
            f"# Note {name}\n\nBody text for note {tag}. " * 20, encoding="utf-8"
        )
    db = Database(db_path)
    try:
        db.init_schema()
        with db.connection:
            coll_repo = CollectionRepository(db.connection)
            coll_repo.create(Collection(name="notes", path=str(notes_dir)))
    finally:
        db.close()


def _child_env() -> dict[str, str]:
    """Child environment: SIF_-stripped (hermetic defaults) and colorless."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("SIF_")}
    env["NO_COLOR"] = "1"
    return env


def _update_argv(db_path: Path) -> list[str]:
    """Real ``sif index update`` invocation (module form, venv-independent)."""
    return [
        sys.executable,
        "-m",
        "sif.cli.main",
        "-q",
        "--index",
        str(db_path),
        "index",
        "update",
    ]


def _run_update(db_path: Path, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run one ``sif index update`` child to completion against the index."""
    return subprocess.run(
        _update_argv(db_path),
        cwd=cwd,
        env=_child_env(),
        capture_output=True,
        text=True,
        timeout=30,  # generous vs expected <5s (D-09)
        check=False,
    )


class TestSecondWriterWaitsThenRuns:
    """D-02: the loser waits while the lock is held, then runs its own pass."""

    def test_second_writer_waits_then_runs(self, tmp_path: Path) -> None:
        db_path = tmp_path / "sif.db"
        _seed_db_with_collection(db_path, tmp_path / "notes")

        fd = os.open(_lock_path(db_path), os.O_RDWR | os.O_CREAT, 0o600)
        child: subprocess.Popen[str] | None = None
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)  # parent = incumbent writer
            child = subprocess.Popen(
                _update_argv(db_path),
                cwd=tmp_path,
                env=_child_env(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            time.sleep(0.5)  # deterministic: the child cannot pass a held lock
            assert child.poll() is None, "child exited while the lock was still held"
            assert os.stat(_lock_path(db_path)).st_mode & 0o777 == 0o600
            fcntl.flock(fd, fcntl.LOCK_UN)  # release -> the waiting child proceeds
        finally:
            os.close(fd)

        assert child is not None
        out, err = child.communicate(timeout=30)
        assert child.returncode == 0, f"child stdout:\n{out}\nchild stderr:\n{err}"


class TestTwoUpdatesNoDuplicates:
    """SC2: two sequential updates leave every file indexed exactly once."""

    def test_two_updates_leave_exactly_three_unique_documents(self, tmp_path: Path) -> None:
        db_path = tmp_path / "sif.db"
        _seed_db_with_collection(db_path, tmp_path / "notes")

        first = _run_update(db_path, tmp_path)
        assert first.returncode == 0, f"first stderr:\n{first.stderr}"
        second = _run_update(db_path, tmp_path)
        assert second.returncode == 0, f"second stderr:\n{second.stderr}"

        # The lock file was created by the children (0600 per T-11-01).
        assert os.stat(_lock_path(db_path)).st_mode & 0o777 == 0o600

        # DB state via a fresh connection opened AFTER the children exited.
        conn = sqlite3.connect(str(db_path))
        try:
            rows = conn.execute("SELECT path FROM documents").fetchall()
        finally:
            conn.close()
        paths = [row[0] for row in rows]
        assert len(paths) == 3, f"expected 3 document rows, got {paths}"
        assert len(set(paths)) == 3, f"duplicate document paths: {paths}"


class TestWalModePersistsAfterUpdate:
    """The child-written database reports WAL mode on a fresh connection."""

    def test_journal_mode_wal_after_child_update(self, tmp_path: Path) -> None:
        db_path = tmp_path / "sif.db"
        _seed_db_with_collection(db_path, tmp_path / "notes")

        result = _run_update(db_path, tmp_path)
        assert result.returncode == 0, f"stderr:\n{result.stderr}"

        conn = sqlite3.connect(str(db_path))
        try:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        finally:
            conn.close()
        assert mode == "wal"
