"""Database lifecycle closure tests for converted CLI commands (WR-01).

Every CLI command module converted by plan 10.1-04 (collection, context,
index, ls, bench, main) owns its Database via ``with Database(...) as db:``
so the handle closes on success and on exception. ``TrackingDatabase``
records each construction; after a ``CliRunner`` invocation every captured
instance must report ``_connection is None``.

The ``get`` and ``search`` modules are deliberately NOT asserted here:
plans 10.1-01 and 10.1-03 own those conversions and add their own closure
assertions in parallel Wave-1 runs — a cross-plan assertion would race.
"""

from __future__ import annotations

import json
from collections.abc import Generator
from pathlib import Path
from typing import ClassVar
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner, Result

from sif.cli import main as main_mod
from sif.cli.commands import (
    bench as bench_mod,
    collection as collection_mod,
    context as context_mod,
    index as index_mod,
    ls as ls_mod,
)
from sif.cli.main import cli
from sif.config.settings import get_settings
from sif.core.models import Collection
from sif.database.database import Database
from sif.database.repositories import CollectionRepository


class TrackingDatabase(Database):
    """Database double recording constructed instances for closure assertions."""

    created: ClassVar[list[Database]] = []

    def __init__(self, db_path: str | Path) -> None:
        """Record each construction so tests can assert every handle closed."""
        super().__init__(db_path)
        TrackingDatabase.created.append(self)


@pytest.fixture(autouse=True)
def isolated_settings() -> Generator[None, None, None]:
    """Database schema creation never inherits cached Settings."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def tracking() -> type[TrackingDatabase]:
    """Reset the construction log and hand out the tracking double."""
    TrackingDatabase.created = []
    return TrackingDatabase


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    """A real, schema-initialized index so missing-index guards do not short-circuit."""
    db_path = tmp_path / "sif.db"
    with Database(db_path) as db:
        db.init_schema()
    return db_path


def _assert_all_closed(tracking: type[TrackingDatabase]) -> None:
    """Every captured instance must be closed — and at least one must exist."""
    assert tracking.created, "no TrackingDatabase captured: patch target missed the command"
    for db in tracking.created:
        assert db._connection is None


def _invoke(db_path: Path, *args: str, input_text: str | None = None) -> Result:
    """Invoke through the top-level CLI with --index pinned to the temp DB."""
    return CliRunner().invoke(cli, ["--index", str(db_path), *args], input=input_text)


class TestSuccessClosure:
    """Each converted module closes its Database after a successful command."""

    def test_collection_list_closes_database(
        self, temp_db: Path, tracking: type[TrackingDatabase], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """collection list closes its Database on the no-collections success path."""
        monkeypatch.setattr(collection_mod, "Database", tracking)
        result = _invoke(temp_db, "collection", "list")
        assert result.exit_code == 0, result.output
        _assert_all_closed(tracking)

    def test_context_list_closes_database(
        self, temp_db: Path, tracking: type[TrackingDatabase], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """context list closes its Database on the no-contexts success path."""
        monkeypatch.setattr(context_mod, "Database", tracking)
        result = _invoke(temp_db, "context", "list")
        assert result.exit_code == 0, result.output
        _assert_all_closed(tracking)

    def test_ls_closes_database(
        self, temp_db: Path, tracking: type[TrackingDatabase], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ls closes its Database after listing (empty) collections."""
        monkeypatch.setattr(ls_mod, "Database", tracking)
        result = _invoke(temp_db, "ls")
        assert result.exit_code == 0, result.output
        _assert_all_closed(tracking)

    def test_index_update_closes_database(
        self,
        tmp_path: Path,
        tracking: type[TrackingDatabase],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """index update closes its Database across a full scan-and-index run."""
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "alpha.md").write_text("# Alpha\n\nalpha body\n", encoding="utf-8")
        db_path = tmp_path / "sif.db"
        with Database(db_path) as db:
            db.init_schema()
            with db.transaction() as conn:
                CollectionRepository(conn).create(
                    Collection(id="coll-index", name="notes", path=str(notes))
                )
        monkeypatch.setattr(index_mod, "Database", tracking)
        result = _invoke(db_path, "index", "update")
        assert result.exit_code == 0, result.output
        _assert_all_closed(tracking)

    def test_status_closes_database(
        self, temp_db: Path, tracking: type[TrackingDatabase], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """status closes its Database inside its try scope."""
        monkeypatch.setattr(main_mod, "Database", tracking)
        result = _invoke(temp_db, "status")
        assert result.exit_code == 0, result.output
        _assert_all_closed(tracking)

    def test_cleanup_closes_database(
        self, temp_db: Path, tracking: type[TrackingDatabase], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """cleanup closes its Database after the confirmed cleanup transaction."""
        monkeypatch.setattr(main_mod, "Database", tracking)
        result = _invoke(temp_db, "cleanup", input_text="y")
        assert result.exit_code == 0, result.output
        _assert_all_closed(tracking)

    def test_bench_closes_database(
        self,
        tmp_path: Path,
        tracking: type[TrackingDatabase],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """bench closes its Database across fixture load and evaluation output."""
        db_path = tmp_path / "sif.db"
        with Database(db_path) as db:
            db.init_schema()
        fixture_path = tmp_path / "fixture.json"
        fixture_path.write_text(
            json.dumps({"queries": [{"query": "alpha", "relevant_docids": ["doc-1"]}]}),
            encoding="utf-8",
        )
        mock_manager_cls = MagicMock()
        mock_manager_cls.from_settings.return_value.embed_single.return_value = [0.0] * 8
        mock_evaluator_cls = MagicMock()
        mock_evaluator_cls.return_value.evaluate.return_value = {"num_queries": 1, "mrr": 1.0}
        monkeypatch.setattr(bench_mod, "EmbeddingManager", mock_manager_cls)
        monkeypatch.setattr(bench_mod, "SearchEvaluator", mock_evaluator_cls)
        monkeypatch.setattr(bench_mod, "Database", tracking)
        result = _invoke(db_path, "bench", str(fixture_path))
        assert result.exit_code == 0, result.output
        _assert_all_closed(tracking)


class TestExceptionClosure:
    """An exception inside the ownership scope still closes the Database."""

    def test_collection_list_failure_closes_database(
        self,
        temp_db: Path,
        tracking: type[TrackingDatabase],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A repository failure inside the scope exits nonzero with the handle closed."""
        monkeypatch.setattr(collection_mod, "Database", tracking)

        def _explode(*_args: object) -> list[Collection]:
            raise RuntimeError("repository exploded")

        monkeypatch.setattr(CollectionRepository, "list_all", _explode)
        result = _invoke(temp_db, "collection", "list")
        assert result.exit_code != 0
        _assert_all_closed(tracking)
