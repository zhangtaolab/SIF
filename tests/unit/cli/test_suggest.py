"""CliRunner battery for the ``sif suggest`` command (Phase 15 QUAL-04).

Real tmp-path DBs from the production DDL: the command opens its own
Database and reads the vocab shadow plus ``query_log``, so mocks would not
exercise the contract. The table mode labels three sections in fixed order
(D-11); ``--json`` carries exactly the three arrays (D-12); ``--clear-history``
is the single clear entry point and is mutually exclusive with QUERY (D-10);
a missing index never materializes a DB, and --json stays parseable there
(WR-05); a quiet run prints no table.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from sif.cli.commands.suggest import suggest_cmd
from sif.config.settings import Settings, get_settings
from sif.core.models import QueryLogEntry
from sif.database.database import Database
from sif.database.repositories import QueryLogRepository


_DOCS = [
    ("d1", "quantum machine learning algorithms"),
    ("d2", "quantum computing quick quantifiers"),
    ("d3", "studies of machine learning contexts"),
]


def _seed_index(
    tmp_path: Path,
    history: tuple[str, ...] = (),
    docs: list[tuple[str, str]] = _DOCS,
) -> Path:
    """Real index DB (production DDL) with a quant/machine vocabulary."""
    settings = Settings(_env_file=None, embedding_dim=8, model_name="test", cache_embeddings=False)
    db_path = tmp_path / "suggest.db"
    with patch("sif.config.settings.get_settings", return_value=settings):
        db = Database(db_path)
        db.init_schema()
        now = datetime.now(timezone.utc).isoformat()
        with db.connection:
            conn = db.connection
            conn.execute(
                "INSERT INTO collections (id, name, path, created_at, updated_at)"
                " VALUES ('c1', 'notes', '/vault', ?, ?)",
                (now, now),
            )
            conn.executemany(
                "INSERT INTO documents (id, collection_id, path, filename, title,"
                " content, checksum, mtime, created_at, updated_at)"
                " VALUES (?, 'c1', ?, ?, ?, ?, ?, 1.0, ?, ?)",
                [
                    (
                        doc_id,
                        f"/vault/{doc_id}.md",
                        f"{doc_id}.md",
                        doc_id,
                        body,
                        f"ck-{doc_id}",
                        now,
                        now,
                    )
                    for doc_id, body in docs
                ],
            )
        if history:
            with db.transaction() as conn:
                repo = QueryLogRepository(conn)
                for query in history:
                    repo.add(QueryLogEntry(query=query, collections=["notes"]), keep=500)
        db.close()
    return db_path


def _history_count(db_path: Path) -> int:
    conn = sqlite3.connect(db_path)
    try:
        return int(conn.execute("SELECT COUNT(*) FROM query_log").fetchone()[0])
    finally:
        conn.close()


@pytest.fixture(autouse=True)
def isolated_settings():
    """Hermetic Settings plus quiet-state cleanup around each invocation."""
    from sif.utils.logging import set_quiet

    settings = Settings(_env_file=None, embedding_dim=8, model_name="test", cache_embeddings=False)
    get_settings.cache_clear()
    with (
        patch("sif.config.settings.get_settings", return_value=settings),
        patch("sif.search.suggest.get_settings", lambda: Settings(_env_file=None)),
    ):
        yield
    get_settings.cache_clear()
    set_quiet(False)


class TestSuggestSections:
    """D-11: three independently ranked, labeled sections."""

    def test_table_shows_three_labeled_sections_in_fixed_order(self, tmp_path: Path) -> None:
        db_path = _seed_index(tmp_path, history=("quantum notes",))

        result = CliRunner().invoke(suggest_cmd, ["quant"], obj={"index_path": db_path})

        assert result.exit_code == 0, result.output
        output = result.output
        assert output.index("Prefix completions") < output.index("Did you mean")
        assert output.index("Did you mean") < output.index("History")
        assert "quantum" in output

    def test_json_has_exactly_three_arrays(self, tmp_path: Path) -> None:
        db_path = _seed_index(tmp_path, history=("quantum notes",))

        result = CliRunner().invoke(suggest_cmd, ["quant", "--json"], obj={"index_path": db_path})

        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        assert set(payload) == {"completions", "did_you_mean", "history"}
        assert all(isinstance(payload[key], list) for key in payload)
        assert payload["completions"]
        assert all(term.startswith("quant") for term in payload["completions"])
        assert payload["history"] == ["quantum notes"]

    def test_json_did_you_mean_carries_the_rewritten_query(self, tmp_path: Path) -> None:
        db_path = _seed_index(tmp_path)

        result = CliRunner().invoke(
            suggest_cmd, ["quantm machin", "--json"], obj={"index_path": db_path}
        )

        assert result.exit_code == 0, result.output
        assert json.loads(result.stdout)["did_you_mean"] == ["quantum machin"]

    def test_cold_start_history_section_is_empty_not_an_error(self, tmp_path: Path) -> None:
        db_path = _seed_index(tmp_path)

        json_result = CliRunner().invoke(
            suggest_cmd, ["quant", "--json"], obj={"index_path": db_path}
        )
        table_result = CliRunner().invoke(suggest_cmd, ["quant"], obj={"index_path": db_path})

        assert json_result.exit_code == 0
        assert json.loads(json_result.stdout)["history"] == []
        assert table_result.exit_code == 0
        assert "History" in table_result.output

    def test_limit_caps_did_you_mean_section(self, tmp_path: Path) -> None:
        """WR-02: --limit is "Maximum entries per section" — DYM included.

        Three equal-ratio close matches for ``cornex`` exist (one per doc);
        ``--limit 1`` must emit one, ``--limit 10`` all three.
        """
        docs = [("d1", "corner"), ("d2", "cornet"), ("d3", "cornel")]
        db_path = _seed_index(tmp_path, docs=docs)

        def dym(limit: int) -> list[str]:
            result = CliRunner().invoke(
                suggest_cmd,
                ["cornex", "--json", "--limit", str(limit)],
                obj={"index_path": db_path},
            )
            assert result.exit_code == 0, result.output
            return json.loads(result.stdout)["did_you_mean"]

        one = dym(1)
        assert len(one) == 1
        assert one[0] in {"corner", "cornel", "cornet"}
        assert dym(10) == ["cornel", "corner", "cornet"]


class TestClearHistory:
    """D-10: one clear entry point, mutually exclusive with QUERY."""

    def test_clear_history_deletes_all_rows_and_confirms(self, tmp_path: Path) -> None:
        db_path = _seed_index(
            tmp_path,
            history=("quantum notes", "machine learning", "quantum notes"),
        )
        assert _history_count(db_path) == 3

        result = CliRunner().invoke(suggest_cmd, ["--clear-history"], obj={"index_path": db_path})

        assert result.exit_code == 0, result.output
        assert "Cleared" in result.output
        assert _history_count(db_path) == 0

    def test_clear_history_is_mutually_exclusive_with_query(self, tmp_path: Path) -> None:
        db_path = _seed_index(tmp_path)

        result = CliRunner().invoke(
            suggest_cmd, ["quant", "--clear-history"], obj={"index_path": db_path}
        )

        assert result.exit_code != 0
        assert "mutually exclusive" in result.output + result.stderr

    def test_query_is_required_without_clear_history(self, tmp_path: Path) -> None:
        db_path = _seed_index(tmp_path)

        result = CliRunner().invoke(suggest_cmd, [], obj={"index_path": db_path})

        assert result.exit_code != 0
        assert "QUERY" in result.output + result.stderr


class TestGuardsAndQuiet:
    """Missing-index guard (never materialize) and -q suppression."""

    def test_missing_index_prints_notice_and_materializes_nothing(self, tmp_path: Path) -> None:
        index_path = tmp_path / "absent.db"

        result = CliRunner().invoke(suggest_cmd, ["quant"], obj={"index_path": index_path})

        assert result.exit_code == 0
        assert "No index found" in result.output
        assert not index_path.exists()

    def test_missing_index_json_is_parseable_empty_document(self, tmp_path: Path) -> None:
        """WR-05: --json on a fresh install is JSON, never human text on stdout."""
        index_path = tmp_path / "absent.db"

        result = CliRunner().invoke(
            suggest_cmd, ["quant", "--json"], obj={"index_path": index_path}
        )

        assert result.exit_code == 0
        assert json.loads(result.stdout) == {
            "completions": [],
            "did_you_mean": [],
            "history": [],
        }
        assert "No index found" not in result.output
        assert not index_path.exists()

    def test_missing_index_quiet_suppresses_notice(self, tmp_path: Path) -> None:
        """WR-05: -q silences the human notice on the missing-index path."""
        index_path = tmp_path / "absent.db"

        result = CliRunner().invoke(suggest_cmd, ["quant", "-q"], obj={"index_path": index_path})

        assert result.exit_code == 0
        assert "No index found" not in result.output

    def test_quiet_suppresses_table_and_suggest_never_writes_history(self, tmp_path: Path) -> None:
        db_path = _seed_index(tmp_path, history=("quantum notes", "machine learning"))

        result = CliRunner().invoke(suggest_cmd, ["quant", "-q"], obj={"index_path": db_path})

        assert result.exit_code == 0
        assert "Prefix completions" not in result.output
        assert "Did you mean" not in result.output
        assert _history_count(db_path) == 2


class TestDbFailurePresentation:
    """15-IN-06 (traceback half): DB open/schema failures are clean Click errors.

    The ``--clear-history`` quiet-leak half is explicitly out of scope (16.1
    D-01) — the preservation pin below keeps it byte-identical, not fixed.
    """

    def test_schema_failure_exits_1_with_remedy(self, tmp_path: Path) -> None:
        """A failing init_schema renders Error: + path + remedy, never a traceback."""
        db_path = tmp_path / "suggest.db"
        db_path.touch()

        class SchemaFailureDatabase(Database):
            def init_schema(self) -> None:
                raise sqlite3.OperationalError("database disk image is malformed")

        with patch("sif.cli.commands.suggest.Database", SchemaFailureDatabase):
            result = CliRunner().invoke(suggest_cmd, ["quant"], obj={"index_path": db_path})

        assert result.exit_code == 1
        assert "Error:" in result.output
        assert str(db_path) in result.output
        assert "permissions" in result.output
        assert "disk" in result.output
        assert "corrupted" in result.output
        assert "Traceback" not in result.output
        assert not isinstance(result.exception, sqlite3.Error)

    def test_clear_history_constructor_failure_exits_1_with_remedy(self, tmp_path: Path) -> None:
        """--clear-history: a constructor OSError gets the same clean presentation."""
        db_path = tmp_path / "suggest.db"
        db_path.touch()

        class ConstructorFailureDatabase(Database):
            def __init__(self, _db_path: str | Path) -> None:
                raise OSError("Permission denied")

        with patch("sif.cli.commands.suggest.Database", ConstructorFailureDatabase):
            result = CliRunner().invoke(
                suggest_cmd, ["--clear-history"], obj={"index_path": db_path}
            )

        assert result.exit_code == 1
        assert "Error:" in result.output
        assert str(db_path) in result.output
        assert "permissions" in result.output
        assert "Traceback" not in result.output
        assert not isinstance(result.exception, OSError)

    def test_clear_history_quiet_confirmation_is_unchanged(self, tmp_path: Path) -> None:
        """Preservation pin: -q still prints the confirmation (quiet leak stays open)."""
        db_path = _seed_index(tmp_path, history=("quantum notes",))

        result = CliRunner().invoke(
            suggest_cmd, ["--clear-history", "-q"], obj={"index_path": db_path}
        )

        assert result.exit_code == 0, result.output
        assert "Cleared 1 query history row(s)." in result.output
        assert _history_count(db_path) == 0
