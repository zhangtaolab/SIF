"""End-to-end proof that ``--min-score`` keeps a row at its own displayed score.

UAT gap G-19-8 (UAT test 8, plan 19-13): on the committed bench corpus, 40 of
84 matching rows disappeared when ``--min-score`` equalled their own displayed
score. These tests drive the real CLI (``cli`` from ``sif.cli.main``, through
``CliRunner``) over the committed 56-query bench fixture and read the displayed
scores from ``--json`` output. The index is BM25-only: no embedding model is
loaded.

The module is imported by the red-derivation gate in an overlay that carries
only this file beside the package and the bench fixtures, so it imports no
sibling test module.
"""

from __future__ import annotations

import json
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from sif.cli.main import cli
from sif.config.settings import get_settings
from sif.core.models import SearchOptions
from sif.database.database import Database
from sif.database.repositories import CollectionRepository
from sif.search.bm25 import BM25Searcher


_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "bench"
_CORPUS = _FIXTURES / "corpus"
_QUERIES = _FIXTURES / "queries.json"
_COLLECTION = "bench-fixture"
_UAT_QUERY = "kelpri protocol"
_QUERY_COUNT = 56
_ROW_COUNT = 84


@pytest.fixture(autouse=True)
def _isolated_settings() -> Generator[None, None, None]:
    """Database initialization must not inherit another test's settings."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _indexed_corpus(tmp_path: Path) -> Path:
    """Add and index the committed bench corpus; return the temporary index path."""
    index = tmp_path / "sif.db"
    runner = CliRunner()
    added = runner.invoke(
        cli,
        [
            "--index",
            str(index),
            "collection",
            "add",
            str(_CORPUS),
            "--name",
            _COLLECTION,
            "--pattern",
            "**/*.md",
        ],
    )
    assert added.exit_code == 0, added.output
    updated = runner.invoke(cli, ["--index", str(index), "index", "update", "-c", _COLLECTION])
    assert updated.exit_code == 0, updated.output
    return index


def _search(runner: CliRunner, index: Path, query: str, *extra: str) -> list[dict[str, Any]]:
    """Run ``sif search search --json`` and return its rows."""
    result = runner.invoke(
        cli,
        [
            "--index",
            str(index),
            "search",
            "search",
            query,
            "-c",
            _COLLECTION,
            "--no-refresh",
            "--json",
            "-n",
            "10",
            *extra,
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    return payload["results"] if isinstance(payload, dict) else payload


def _options(collection_ids: list[str], min_score: float = 0.0) -> SearchOptions:
    """Return the options the search command builds for the committed limit."""
    return SearchOptions(limit=10, offset=0, min_score=min_score, collection_ids=collection_ids)


def test_the_cli_keeps_a_row_at_its_own_displayed_score(tmp_path: Path) -> None:
    """UAT test 8: the threshold equal to a row's ``--json`` score keeps that row."""
    runner = CliRunner()
    index = _indexed_corpus(tmp_path)

    rows = _search(runner, index, _UAT_QUERY)
    assert len(rows) >= 2
    assert rows[0]["title"] == "Kelpri Protocol Notes"
    threshold = rows[0]["score"]

    kept = _search(runner, index, _UAT_QUERY, "--min-score", repr(threshold))
    expected_ids = [row["document_id"] for row in rows if row["score"] >= threshold]
    assert [row["document_id"] for row in kept] == expected_ids
    assert kept[0]["score"] == threshold
    assert rows[0]["rank"] == kept[0]["rank"] == 1
    assert [row["rank"] for row in kept] == list(range(1, len(kept) + 1))
    assert all(row["score"] >= threshold for row in kept)


def test_every_bench_row_survives_its_own_displayed_score(tmp_path: Path) -> None:
    """Every row of the 56 committed queries survives a search at its own score."""
    queries = json.loads(_QUERIES.read_text(encoding="utf-8"))["queries"]
    assert len(queries) == _QUERY_COUNT

    index = _indexed_corpus(tmp_path)

    db = Database(index)
    try:
        connection = db.connection
        collection_ids = [
            collection.id
            for collection in CollectionRepository(connection).list_all()
            if collection.name == _COLLECTION
        ]
        assert len(collection_ids) == 1
        searcher = BM25Searcher(connection)
        checked = 0
        for item in queries:
            page = searcher.search(item["query"], _options(collection_ids))
            for row in page:
                survived = searcher.search(
                    item["query"], _options(collection_ids, min_score=row.score)
                )
                scores = [
                    result.score for result in survived if result.document_id == row.document_id
                ]
                assert scores == [row.score], (item["query"], row.document_id)
                checked += 1
        assert checked == _ROW_COUNT
    finally:
        db.close()
