"""End-to-end metadata filter through the real CLI/index path (Plan 20-01).

The tracer proves the whole vertical slice on a real index: YAML frontmatter
becomes typed kv rows in the same transaction as the document row, the
compiled predicate lands in the BM25 outer WHERE, and ``sif search --filter``
returns only matching documents while the unfiltered run returns both
(Pitfall 5: an empty match must never degrade to "no filter").
"""

from __future__ import annotations

import contextlib
import json
import sqlite3
from collections.abc import Generator
from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from sif.cli.main import cli
from sif.config.settings import get_settings


_ACTIVE_FILTER = '{"field": "status", "operator": "eq", "value": "active"}'
_NO_MATCH_FILTER = '{"field": "status", "operator": "eq", "value": "missing"}'


class TestFilterEndToEnd:
    """`sif search --filter` on an index built by the real indexing path."""

    @pytest.fixture(autouse=True)
    def isolated_settings(self) -> Generator[None, None, None]:
        """Database initialization must not inherit another test's settings."""
        get_settings.cache_clear()
        yield
        get_settings.cache_clear()

    @pytest.fixture
    def index_path(self, tmp_path: Path) -> Path:
        """Two notes containing ``needle``; only one is status=active."""
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "active.md").write_text(
            "---\nstatus: active\n---\n# Active note\n\nneedle in the active note\n",
            encoding="utf-8",
        )
        (notes / "archived.md").write_text(
            "---\nstatus: archived\n---\n# Archived note\n\nneedle in the archived note\n",
            encoding="utf-8",
        )
        db_path = tmp_path / "index.db"
        runner = CliRunner()
        added = runner.invoke(
            cli,
            ["--index", str(db_path), "collection", "add", str(notes), "--name", "notes"],
        )
        assert added.exit_code == 0, added.output
        updated = runner.invoke(cli, ["--index", str(db_path), "index", "update"])
        assert updated.exit_code == 0, updated.output
        return db_path

    def _search(self, index_path: Path, *args: str) -> Result:
        """Invoke ``sif search search needle`` with every database path isolated."""
        return CliRunner().invoke(
            cli,
            ["--index", str(index_path), "search", "search", "needle", *args],
        )

    def test_eq_filter_returns_only_matching_documents(self, index_path: Path) -> None:
        """Unfiltered returns both notes; the eq filter returns exactly the active one."""
        unfiltered = self._search(index_path, "--json")
        assert unfiltered.exit_code == 0, unfiltered.output
        unfiltered_rows = json.loads(unfiltered.output)
        assert {Path(row["path"]).name for row in unfiltered_rows} == {
            "active.md",
            "archived.md",
        }

        filtered = self._search(index_path, "--json", "--filter", _ACTIVE_FILTER)
        assert filtered.exit_code == 0, filtered.output
        filtered_rows = json.loads(filtered.output)
        assert len(filtered_rows) == 1
        assert Path(filtered_rows[0]["path"]).name == "active.md"

    def test_empty_match_returns_empty_page_not_unfiltered(self, index_path: Path) -> None:
        """A filter matching nothing returns no results (never the unfiltered set)."""
        result = self._search(index_path, "--json", "--filter", _NO_MATCH_FILTER)
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        rows = payload["results"] if isinstance(payload, dict) else payload
        assert rows == []

    def test_invalid_filter_is_a_user_error(self, index_path: Path) -> None:
        """Invalid JSON/AST raises a ClickException naming the filter, not a traceback."""
        bad_json = self._search(index_path, "--filter", "{not json")
        assert bad_json.exit_code != 0
        assert "filter: invalid JSON" in bad_json.output

        bad_ast = self._search(
            index_path,
            "--filter",
            '{"field": "status", "operator": "bogus", "value": "x"}',
        )
        assert bad_ast.exit_code != 0
        assert "filter:" in bad_ast.output

    def test_typed_rows_written_for_both_documents(self, index_path: Path) -> None:
        """The kv store holds a string status row for each indexed note (FILT-04)."""
        with contextlib.closing(sqlite3.connect(index_path)) as conn:
            rows = conn.execute(
                "SELECT document_id, text_value FROM document_metadata_values "
                "WHERE key = 'status' AND value_type = 'string'"
            ).fetchall()
        assert len(rows) == 2
        assert {value for _, value in rows} == {"active", "archived"}
