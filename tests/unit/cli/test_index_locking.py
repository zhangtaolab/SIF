"""Deterministic lock-acquisition proofs for ``sif index update``/``embed`` (D-01/D-02).

Both long-running writers must arbitrate on the one per-database flock. The
spy tests prove each command enters the ``index_lock`` context exactly once
per invocation (update_cmd since 11-01, embed_cmd since this plan), and the
held-lock test proves the D-02 loser path: a writer that finds the lock held
waits out the short deadline, prints the waiting notice, then runs its own
pass — exit 0 with its work done, never silently dropped.

No timing races: the test process owns the lock for the whole invocation
(D-08/D-09 discipline). The only wall-clock assertion is a lower bound on
the loser's wait, forced by the held lock.
"""

from __future__ import annotations

import fcntl
import os
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from sif.cli.commands.index import embed_cmd, update_cmd
from sif.config.settings import Settings, get_settings
from sif.core.models import Collection, Document
from sif.database.database import Database
from sif.database.repositories import CollectionRepository, DocumentRepository


DIM = 8


@pytest.fixture(autouse=True)
def isolated_settings() -> Generator[None, None, None]:
    """Lock tests never inherit cached Settings."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _delenv_settings_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep Settings construction hermetic against a developer shell."""
    for var in ("SIF_EMBEDDING_DIM", "SIF_MODEL_TYPE", "SIF_MODEL_NAME"):
        monkeypatch.delenv(var, raising=False)


def _test_settings(**overrides: object) -> Settings:
    """Build hermetic test settings (optionally overriding lock_wait_timeout)."""
    return Settings(embedding_dim=DIM, model_name="test", cache_embeddings=False, **overrides)  # type: ignore[arg-type]


def _seed_collection_with_file(db_path: Path, settings: Settings, root: Path) -> None:
    """Init schema and create one collection pointing at a one-file tree."""
    body = "# Lock Note\n\nBody text for the lock test. " * 10
    (root / "a.md").write_text(body, encoding="utf-8")
    db = Database(db_path)
    with patch("sif.config.settings.get_settings", return_value=settings):
        db.init_schema()
        with db.connection:
            CollectionRepository(db.connection).create(Collection(name="notes", path=str(root)))
    db.close()


def _seed_collection_with_document(db_path: Path, settings: Settings) -> None:
    """Init schema and create one collection with one embedded-able document."""
    db = Database(db_path)
    with patch("sif.config.settings.get_settings", return_value=settings):
        db.init_schema()  # creates the vec0 table with the test embedding_dim
        with db.connection:
            coll_repo = CollectionRepository(db.connection)
            doc_repo = DocumentRepository(db.connection)
            coll_repo.create(Collection(name="notes", path="/notes"))
            doc_repo.create(
                Document(
                    path="/notes/a.md",
                    collection_id=coll_repo.get_by_name("notes").id,  # type: ignore[union-attr]
                    content="# One\n\nParagraph text for section one. " * 20
                    + "# Two\n\nParagraph text for section two. " * 20,
                    title="A",
                )
            )
    db.close()


def _make_manager_mock() -> MagicMock:
    """Build a mocked EmbeddingManager producing deterministic DIM-length vectors."""
    manager = MagicMock()
    manager.get_model_info.return_value = {"loaded": True, "embedding_dim": DIM}

    def fake_embed(texts: list[str], **_kwargs: object) -> MagicMock:
        vectors = []
        for i in range(len(texts)):
            vec = [0.0] * DIM
            vec[i % DIM] = 1.0
            vectors.append(vec)
        return MagicMock(embeddings=vectors)

    manager.embed.side_effect = fake_embed
    return manager


def _recording_lock(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Replace index_lock in the CLI module with a recording wrapper (D-01 spy)."""
    import sif.cli.commands.index as index_mod

    real_lock = index_mod.index_lock
    events: list[str] = []

    @contextmanager
    def recording_lock(
        db_path: Path,
        timeout_s: float,
        on_wait: Callable[[], None] | None = None,
    ) -> Generator[None, None, None]:
        events.append("acquire")
        with real_lock(db_path, timeout_s, on_wait=on_wait):
            events.append("enter")
            yield
        events.append("release")

    monkeypatch.setattr(index_mod, "index_lock", recording_lock)
    return events


class TestLockAcquisitionSpy:
    """D-01: both long-running writers enter the per-DB lock exactly once."""

    def test_update_cmd_enters_index_lock_once(self, tmp_path: Path, monkeypatch) -> None:
        """update_cmd wraps its work in exactly one index_lock context per run."""
        events = _recording_lock(monkeypatch)
        _delenv_settings_vars(monkeypatch)
        settings = _test_settings()
        db_path = tmp_path / "update-lock.db"
        root = tmp_path / "notes"
        root.mkdir()
        _seed_collection_with_file(db_path, settings, root)

        runner = CliRunner()
        with patch("sif.config.settings.get_settings", return_value=settings):
            result = runner.invoke(update_cmd, [], obj={"index_path": db_path})

        assert result.exit_code == 0
        assert events.count("enter") == 1
        assert events.count("release") == 1
        assert "Added: 1" in result.output

    def test_embed_cmd_enters_index_lock_once(self, tmp_path: Path, monkeypatch) -> None:
        """embed_cmd wraps its collection loop in exactly one index_lock context."""
        events = _recording_lock(monkeypatch)
        _delenv_settings_vars(monkeypatch)
        settings = _test_settings()
        db_path = tmp_path / "embed-lock.db"
        _seed_collection_with_document(db_path, settings)
        manager = _make_manager_mock()

        runner = CliRunner()
        with (
            patch("sif.config.settings.get_settings", return_value=settings),
            patch("sif.embedding.manager.EmbeddingManager.from_settings", return_value=manager),
        ):
            result = runner.invoke(embed_cmd, [], obj={"index_path": db_path})

        assert result.exit_code == 0
        assert events.count("enter") == 1
        assert events.count("release") == 1
        assert "chunks embedded" in result.output


class TestHeldLockProceeds:
    """D-02: a lock waiter never drops its distinct work — it waits, then runs."""

    def test_update_cmd_waits_out_deadline_then_proceeds(
        self,
        tmp_path: Path,
        monkeypatch,
    ) -> None:
        """With the lock held and a 0.2s wait setting, update_cmd waits, notices, proceeds."""
        _delenv_settings_vars(monkeypatch)
        settings = _test_settings(lock_wait_timeout=0.2)
        db_path = tmp_path / "held-lock.db"
        root = tmp_path / "notes"
        root.mkdir()
        _seed_collection_with_file(db_path, settings, root)

        # The test process is the incumbent writer: same lock-file derivation
        # as production (canonicalized db path + ".lock"), held for the whole
        # invocation, so the loser's wait is forced, not raced.
        resolved = db_path.expanduser().resolve()
        lock_path = resolved.with_name(resolved.name + ".lock")
        fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            runner = CliRunner()
            started = time.monotonic()
            with patch("sif.config.settings.get_settings", return_value=settings):
                result = runner.invoke(update_cmd, [], obj={"index_path": db_path})
            elapsed = time.monotonic() - started
        finally:
            os.close(fd)

        assert result.exit_code == 0
        assert "Another index writer is running; waiting up to" in result.output
        # The full 0.2s deadline was waited out before the loser's own pass.
        assert elapsed >= 0.19
        # D-02: the loser proceeded with its own work — nothing was dropped.
        assert "Added: 1" in result.output
