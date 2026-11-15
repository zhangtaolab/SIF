"""End-to-end metadata filter through the real CLI/index path (Plan 20-01).

The tracer proves the whole vertical slice on a real index: YAML frontmatter
becomes typed kv rows in the same transaction as the document row, the
compiled predicate lands in the BM25 outer WHERE, and ``sif search --filter``
returns only matching documents while the unfiltered run returns both
(Pitfall 5: an empty match must never degrade to "no filter").

Plan 20-04 extends the battery to the full CLI option surface: all three
result commands expose ``--filter``, validate it before any database open or
pre-search refresh, compose it by AND with collection/offset/min-score, and
keep ``--json`` stdout machine-clean.
"""

from __future__ import annotations

import contextlib
import json
import sqlite3
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner, Result

from sif.cli.commands.search import query_cmd, search_cmd, vsearch_cmd
from sif.cli.main import cli
from sif.config.settings import get_settings
from sif.core.filters import parse_filter
from sif.core.models import Collection


_ACTIVE_FILTER = '{"field": "status", "operator": "eq", "value": "active"}'
_NO_MATCH_FILTER = '{"field": "status", "operator": "eq", "value": "missing"}'
_BAD_AST_FILTER = '{"field": "tags", "operator": "gt", "value": "x"}'

# (name, command) for the three result commands; D-01 requires the same flag
# name, grammar, and semantics on every one of them.
_RESULT_COMMANDS = (
    pytest.param(search_cmd, id="search"),
    pytest.param(vsearch_cmd, id="vsearch"),
    pytest.param(query_cmd, id="query"),
)


def _settings_mock() -> MagicMock:
    """Explicit settings mock with the fields query/vsearch read as ints/floats."""
    return MagicMock(
        model_name="test",
        rerank_enabled=False,
        rerank_candidate_limit=20,
        rrf_k=60,
        bm25_weight=1.0,
        vector_weight=1.0,
        default_search_type="hybrid",
    )


def _index_path() -> MagicMock:
    """An existing-index stand-in so commands skip their not-found early return."""
    return MagicMock(exists=lambda: True)


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


class TestFilterOptionMatrix:
    """D-01: the same ``--filter`` flag and error taxonomy on all three commands."""

    @pytest.mark.parametrize("cmd", _RESULT_COMMANDS)
    def test_all_result_commands_expose_filter(self, cmd: object) -> None:
        """Click exposes ``--filter`` (``cmd.params`` holds Parameter objects)."""
        assert "--filter" in {opt for param in cmd.params for opt in param.opts}

    @pytest.mark.parametrize("cmd", _RESULT_COMMANDS)
    def test_invalid_json_is_a_user_error_before_any_index_work(self, cmd: object) -> None:
        """Invalid JSON names the filter, and no DB open or drift walk happens."""
        opened = MagicMock()
        refresh = MagicMock()
        with (
            patch("sif.cli.commands.search.open_initialized_database", opened),
            patch("sif.cli.commands.search._pre_search_refresh", refresh),
        ):
            result = CliRunner().invoke(
                cmd,
                ["needle", "--filter", "{not json"],
                obj={"index_path": _index_path()},
            )

        assert result.exit_code != 0
        assert "filter: invalid JSON" in result.output
        opened.assert_not_called()
        refresh.assert_not_called()

    @pytest.mark.parametrize("cmd", _RESULT_COMMANDS)
    def test_invalid_ast_names_operator_field_and_path(self, cmd: object) -> None:
        """A semantic violation reports its AST path/operator/field (D-17)."""
        opened = MagicMock()
        refresh = MagicMock()
        with (
            patch("sif.cli.commands.search.open_initialized_database", opened),
            patch("sif.cli.commands.search._pre_search_refresh", refresh),
        ):
            result = CliRunner().invoke(
                cmd,
                ["needle", "--filter", _BAD_AST_FILTER],
                obj={"index_path": _index_path()},
            )

        assert result.exit_code != 0
        # The message names the AST path (``filter.<operator path>``), the
        # operator, and the offending field (D-17).
        assert "filter.gt" in result.output
        assert '"gt" requires a numeric value' in result.output
        assert "tags" in result.output
        opened.assert_not_called()
        refresh.assert_not_called()

    @pytest.mark.parametrize("cmd", _RESULT_COMMANDS)
    def test_unbounded_integer_operand_is_a_user_error(self, cmd: object) -> None:
        """WR-01: a huge JSON integer names the filter path, never overflows raw."""
        opened = MagicMock()
        refresh = MagicMock()
        payload = '{"field": "priority", "operator": "gt", "value": ' + "9" * 400 + "}"
        with (
            patch("sif.cli.commands.search.open_initialized_database", opened),
            patch("sif.cli.commands.search._pre_search_refresh", refresh),
        ):
            result = CliRunner().invoke(
                cmd,
                ["needle", "--filter", payload],
                obj={"index_path": _index_path()},
            )

        assert result.exit_code != 0
        assert "filter.gt" in result.output
        assert "OverflowError" not in result.output
        opened.assert_not_called()
        refresh.assert_not_called()

    @pytest.mark.parametrize("cmd", _RESULT_COMMANDS)
    def test_filtered_json_output_is_clean_json(self, cmd: object) -> None:
        """``--json`` stays machine-parseable with no notice text on stdout."""
        with (
            patch("sif.cli.commands.search.Database", return_value=MagicMock()),
            patch("sif.cli.commands.search.CollectionRepository", return_value=MagicMock()),
            patch("sif.cli.commands.search.BM25Searcher", return_value=MagicMock()),
            patch("sif.cli.commands.search.SearchPipeline", return_value=MagicMock()),
            patch(
                "sif.embedding.manager.EmbeddingManager.from_settings",
                return_value=MagicMock(),
            ),
            patch("sif.config.settings.get_settings", return_value=_settings_mock()),
            patch("sif.cli.commands.search._pre_search_refresh"),
        ):
            result = CliRunner().invoke(
                cmd,
                ["needle", "--json", "--filter", _ACTIVE_FILTER],
                obj={"index_path": _index_path()},
            )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        rows = payload["results"] if isinstance(payload, dict) else payload
        assert rows == []
        assert "refreshed" not in result.stdout
        assert "selective" not in result.stdout.lower()


class TestFilterComposition:
    """D-17: the filter ANDs with collection/offset/min-score on every command."""

    def _patched_db(self) -> MagicMock:
        """Repository mock resolving ``-c notes`` to one collection."""
        repo = MagicMock()
        repo.get_by_name.return_value = Collection(id="coll1", name="notes", path="/notes")
        return repo

    @pytest.mark.parametrize("command", ["search", "vsearch", "query"])
    def test_filter_composes_with_collection_offset_and_min_score(self, command: str) -> None:
        """The SearchOptions handed to the searcher carries all four values."""
        runner = CliRunner()
        args = ["needle", "-c", "notes", "--offset", "2", "--min-score", "0.5"]
        args += ["--filter", _ACTIVE_FILTER]
        repo = self._patched_db()
        mock_db = MagicMock()

        with (
            patch("sif.cli.commands.search.Database", return_value=mock_db),
            patch("sif.cli.commands.search.CollectionRepository", return_value=repo),
            patch(
                "sif.config.settings.get_settings",
                return_value=_settings_mock(),
            ),
            patch("sif.cli.commands.search._pre_search_refresh"),
        ):
            if command == "search":
                searcher = MagicMock()
                with patch("sif.cli.commands.search.BM25Searcher", return_value=searcher):
                    result = runner.invoke(search_cmd, args, obj={"index_path": _index_path()})
            elif command == "vsearch":
                searcher = MagicMock()
                with (
                    patch(
                        "sif.embedding.manager.EmbeddingManager.from_settings",
                        return_value=MagicMock(),
                    ),
                    patch("sif.search.vector.VectorSearcher", return_value=searcher),
                ):
                    result = runner.invoke(vsearch_cmd, args, obj={"index_path": _index_path()})
            else:
                searcher = MagicMock()
                with (
                    patch(
                        "sif.embedding.manager.EmbeddingManager.from_settings",
                        return_value=MagicMock(),
                    ),
                    patch("sif.cli.commands.search.SearchPipeline", return_value=searcher),
                ):
                    result = runner.invoke(query_cmd, args, obj={"index_path": _index_path()})

        assert result.exit_code == 0, result.output
        options = searcher.search.call_args[0][1]
        assert options.collection_ids == ["coll1"]
        assert options.offset == 2
        assert options.min_score == 0.5
        assert options.filter == parse_filter(json.loads(_ACTIVE_FILTER))


class TestDocsSurface:
    """The generator-owned CLI reference documents the flag (never hand-edited)."""

    def test_cli_reference_documents_filter_flag(self) -> None:
        """``--filter`` appears for search, vsearch, and query sections."""
        cli_ref = Path("docs/cli-reference.md")
        if not cli_ref.exists():
            pytest.skip("cli-reference.md not found")
        content = cli_ref.read_text(encoding="utf-8")

        # Structural, not phrasing-dependent: one flag token per section.
        assert content.count("--filter") >= 3
        for header, next_header in (
            ("### `search query`", "### `search search`"),
            ("### `search search`", "### `search vsearch`"),
            ("### `search vsearch`", "## MCP Commands"),
        ):
            section = content.split(header, 1)[1].split(next_header, 1)[0]
            assert "--filter" in section
