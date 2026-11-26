"""End-to-end direction proof for BM25 ``--min-score`` (UAT gap G-19-2, plan 19-12).

The tests drive the real CLI (``cli`` from ``sif.cli.main``, through
``CliRunner``) over a real temporary index and read the displayed scores from
``--json`` output. The index is BM25-only: no embedding model is loaded.

UAT test 2 found that a better BM25 match showed the lower number, so
``--min-score`` removed the best matches first, the opposite of its help text.
The corpus here has one strong document (many repetitions of the query words),
three weak notes (one mention each) and sixteen unrelated fillers that keep the
query words rare enough for the scores to spread.
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


_QUERY = "saltiv protocol notes"
_STRONG_DOCUMENT = "saltiv-protocol-notes.md"
_NOTES = 3
_FILLERS = 16

# The module is imported by the red-derivation gate in an overlay that carries
# only this file beside the package, so it imports no sibling test module.


@pytest.fixture(autouse=True)
def _isolated_settings() -> Generator[None, None, None]:
    """Database initialization must not inherit another test's settings."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _write_corpus(root: Path) -> None:
    """Write the probe corpus under ``root``: one strong note, weak notes, fillers.

    Every file holds a heading line and a body line. The strong document's body
    is four copies, joined by single spaces, of a block in which each query word
    appears twelve times.
    """
    root.mkdir(parents=True)
    block = " ".join(_QUERY.split() * 12)
    strong_body = " ".join([block] * 4)
    (root / _STRONG_DOCUMENT).write_text(
        f"# Saltiv Protocol Notes\n\n{strong_body}\n", encoding="utf-8"
    )
    for index in range(_NOTES):
        (root / f"note-{index}.md").write_text(
            f"# Note {index}\n\nsaltiv protocol notes number {index}\n", encoding="utf-8"
        )
    for index in range(_FILLERS):
        (root / f"filler-{index}.md").write_text(
            f"# Filler {index}\n\nunrelated banana filler document number {index}\n",
            encoding="utf-8",
        )


def _indexed(tmp_path: Path) -> Path:
    """Add and index the probe corpus into a temporary database; return its path."""
    corpus = tmp_path / "corpus"
    _write_corpus(corpus)
    index = tmp_path / "sif.db"
    runner = CliRunner()
    added = runner.invoke(
        cli, ["--index", str(index), "collection", "add", str(corpus), "--name", "probe"]
    )
    assert added.exit_code == 0, added.output
    updated = runner.invoke(cli, ["--index", str(index), "index", "update"])
    assert updated.exit_code == 0, updated.output
    return index


def _search(runner: CliRunner, index: Path, *extra: str) -> list[dict[str, Any]]:
    """Run the probe query through ``sif search search --json`` and return its rows."""
    result = runner.invoke(
        cli,
        [
            "--index",
            str(index),
            "search",
            "search",
            _QUERY,
            "-c",
            "probe",
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


def test_min_score_keeps_the_best_match_and_drops_weaker_ones(tmp_path: Path) -> None:
    """The best match shows the highest score and is the one a threshold keeps."""
    runner = CliRunner()
    index = _indexed(tmp_path)

    rows = _search(runner, index)
    assert len(rows) == 4
    assert Path(rows[0]["path"]).name == _STRONG_DOCUMENT
    scores = [row["score"] for row in rows]
    assert scores == sorted(scores, reverse=True)

    # Midway between the two best scores: only the best match clears it.
    midway = (scores[0] + scores[1]) / 2
    kept = _search(runner, index, "--min-score", repr(midway))
    assert [Path(row["path"]).name for row in kept] == [_STRONG_DOCUMENT]
    assert [row["rank"] for row in kept] == [1]

    # At the second score the best match is still first, whatever the boundary
    # does with the row that sits exactly on the threshold.
    at_second = _search(runner, index, "--min-score", repr(scores[1]))
    assert Path(at_second[0]["path"]).name == _STRONG_DOCUMENT


def test_min_score_of_one_returns_no_results(tmp_path: Path) -> None:
    """No BM25 score reaches 1, so ``--min-score 1`` returns the empty list."""
    runner = CliRunner()
    index = _indexed(tmp_path)

    assert _search(runner, index, "--min-score", "1") == []
