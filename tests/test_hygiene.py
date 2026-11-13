"""Regression guards for the ENG-04 hygiene deletions (plan 17-01)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import sif.models


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
TESTS_ROOT = REPO_ROOT / "tests"
EXAMPLES_ROOT = REPO_ROOT / "examples"
SELF_PATH = Path(__file__).resolve()


def _python_files() -> list[Path]:
    """Return every Python file the dead-reference scan covers (self excluded)."""
    files: list[Path] = []
    for root in (SRC_ROOT, TESTS_ROOT, EXAMPLES_ROOT):
        for path in sorted(root.rglob("*.py")):
            if path.resolve() == SELF_PATH:
                continue
            files.append(path)
    return files


def _offenders(literal: str) -> list[str]:
    """Return repo-relative paths whose source text contains ``literal``."""
    return [
        str(path.relative_to(REPO_ROOT))
        for path in _python_files()
        if literal in path.read_text(encoding="utf-8")
    ]


def _assert_literal_absent(literal: str) -> None:
    """Fail with every offending path when a dead literal survives."""
    hits = _offenders(literal)
    if hits:
        pytest.fail(f"dead literal {literal!r} survives in: {', '.join(hits)}")


def test_dead_search_models_module_absent() -> None:
    """The dead Pydantic search-models module is deleted outright."""
    assert not (SRC_ROOT / "sif" / "models" / "search.py").exists()


def test_no_dead_search_model_imports() -> None:
    """No source, test, or example file imports the deleted models module."""
    _assert_literal_absent("sif.models.search")


def test_models_package_does_not_export_dead_search_models() -> None:
    """``sif.models.__all__`` no longer advertises the dead search models."""
    dead = {"SearchOptions", "SearchQuery", "SearchResponse", "SearchResult", "SearchType"}
    leaked = sorted(dead & set(sif.models.__all__))
    assert not leaked, f"sif.models.__all__ still exports {leaked}"


def test_factories_module_absent() -> None:
    """The unused tests/factories.py helper is deleted outright."""
    assert not (TESTS_ROOT / "factories.py").exists()


def test_dead_layers_are_not_importable() -> None:
    """Every deleted layer is gone from the tree and from all importers."""
    for relative in ("models/search.py", "search/strategy.py", "database/migrations.py"):
        assert not (SRC_ROOT / "sif" / relative).exists(), f"{relative} still exists"
    for literal in ("sif.models.search", "sif.search.strategy", "MigrationManager"):
        _assert_literal_absent(literal)


def test_compute_rrf_score_removed() -> None:
    """The orphan RRF export is gone while RRFFusion remains the live path."""
    rrf_text = (SRC_ROOT / "sif" / "search" / "rrf.py").read_text(encoding="utf-8")
    assert "compute_rrf_score" not in rrf_text
    assert "class RRFFusion" in rrf_text


def test_current_schema_version_removed() -> None:
    """The schema-version constant leaves with the dead migration layer."""
    constants_text = (SRC_ROOT / "sif" / "config" / "constants.py").read_text(encoding="utf-8")
    assert "CURRENT_SCHEMA_VERSION" not in constants_text


def test_quickstart_example_compiles() -> None:
    """The quickstart example compiles and targets only live APIs."""
    example = EXAMPLES_ROOT / "quickstart.py"
    subprocess.run(
        [sys.executable, "-m", "py_compile", str(example)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    text = example.read_text(encoding="utf-8")
    assert "BM25Searcher" in text
    assert "BM25SearchStrategy" not in text
    assert "SearchContext" not in text
