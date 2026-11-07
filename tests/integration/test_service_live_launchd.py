"""Opt-in live launchd round-trip proof for the installed watch service (13-04).

Runs ONLY when all of: ``SIF_TEST_LIVE_LAUNCHD=1``, macOS, and launchctl on
PATH (D-13 live-invocation clause). The round-trip uses a SCRATCH label and
tmp destinations — the user's real agents (~/Library/LaunchAgents/
com.docsif.watch) are never touched, the DB is a tmp file, and a
finally-bootout safety net means a failing assertion can never leave a
scratch service loaded.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest

from sif.core.models import Collection
from sif.database.database import Database
from sif.database.repositories import CollectionRepository
from sif.utils import service


_LIVE = os.environ.get("SIF_TEST_LIVE_LAUNCHD") == "1"
_ON_MAC = sys.platform == "darwin"
_HAS_LAUNCHCTL = shutil.which("launchctl") is not None

pytestmark = pytest.mark.skipif(
    not (_LIVE and _ON_MAC and _HAS_LAUNCHCTL),
    reason="opt-in live launchd proof: set SIF_TEST_LIVE_LAUNCHD=1 on macOS with launchctl",
)

SCRATCH_LABEL = "com.docsif.watch.scratch-test"

_SEED_BODY = "# Seed Note\n\n" + ("Live service proof seed paragraph. " * 30)
_LIVE_BODY = "# Live Note\n\n" + ("Written while the installed service watched. " * 30)

_BANNER_DEADLINE_S = 30.0
_INDEX_DEADLINE_S = 60.0
_POLL_INTERVAL_S = 0.2


def _poll_until_row(db_path: Path, sql: str, params: tuple[str, ...]) -> tuple | None:
    """Deadline-bounded row poll through fresh sqlite connections (D-15)."""
    deadline = time.monotonic() + _INDEX_DEADLINE_S
    while time.monotonic() < deadline:
        conn = sqlite3.connect(str(db_path))
        try:
            row = conn.execute(sql, params).fetchone()
        finally:
            conn.close()
        if row is not None:
            return row
        time.sleep(_POLL_INTERVAL_S)
    return None


def _poll_log_text(log_path: Path, needle: str) -> bool:
    """Deadline-bounded wait for the post-arm banner in the service log."""
    deadline = time.monotonic() + _BANNER_DEADLINE_S
    while time.monotonic() < deadline:
        if log_path.exists() and needle in log_path.read_text(encoding="utf-8", errors="replace"):
            return True
        time.sleep(_POLL_INTERVAL_S)
    return False


def _service_gone() -> bool:
    """True once launchd no longer knows the scratch label.

    ``bootout`` is asynchronous: the job leaves the domain only after the
    SIGTERM'd watcher finishes its graceful flush + checkpoint, so the
    not-loaded outcome must be polled, never assumed.
    """
    result = subprocess.run(
        ["launchctl", "print", f"gui/{os.getuid()}/{SCRATCH_LABEL}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode != 0


def _poll_service_gone() -> bool:
    deadline = time.monotonic() + _BANNER_DEADLINE_S
    while time.monotonic() < deadline:
        if _service_gone():
            return True
        time.sleep(_POLL_INTERVAL_S)
    return False


def test_live_launchd_install_round_trip_indexes_a_change(tmp_path: Path) -> None:
    """SC3 live proof: real bootstrap runs the foreground watcher under
    launchd; a file change written after the Watching banner becomes indexed;
    bootout + uninstall remove the service and its artifact cleanly."""
    db_path = tmp_path / "service.db"
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "seed.md").write_text(_SEED_BODY, encoding="utf-8")
    db = Database(db_path)
    try:
        db.init_schema()
        with db.connection:
            CollectionRepository(db.connection).create(
                Collection(name="notes", path=str(notes_dir))
            )
    finally:
        db.close()

    dest_dir = tmp_path / "agents"
    log_dir = tmp_path / "logs"
    plist_path = dest_dir / f"{SCRATCH_LABEL}.plist"
    log_path = log_dir / "watch.log"

    try:
        result = service.install_watch_service(
            db_path,
            ["-c", "notes"],
            manager="launchd",
            label=SCRATCH_LABEL,
            dest_dir=dest_dir,
            log_dir=log_dir,
        )

        assert result.artifact_path == plist_path
        assert plist_path.exists()
        assert result.log_location == str(log_path)

        # The banner prints AFTER the observer arms (Phase 12 discipline), so
        # waiting for it closes the reconcile->arm gap before we mutate.
        assert _poll_log_text(log_path, "Watching"), "service never armed its observer"

        live_note = notes_dir / "live.md"
        live_note.write_text(_LIVE_BODY, encoding="utf-8")
        row = _poll_until_row(db_path, "SELECT id FROM documents WHERE path = ?", (str(live_note),))
        assert row is not None, "installed service never indexed the live change"
    finally:
        # Safety net: a failing assertion must never leave a scratch service
        # loaded (bootout directly if the uninstall helper itself blows up).
        try:
            service.uninstall_watch_service(
                manager="launchd", label=SCRATCH_LABEL, dest_dir=dest_dir
            )
        except Exception:
            subprocess.run(
                ["launchctl", "bootout", f"gui/{os.getuid()}/{SCRATCH_LABEL}"],
                capture_output=True,
                check=False,
            )

    assert not plist_path.exists(), "uninstall left the scratch artifact behind"
    # bootout is async — the job leaves the domain once the SIGTERM'd watcher
    # completes its graceful flush + checkpoint, so poll for the gone state.
    assert _poll_service_gone(), "scratch service still loaded after bootout"
