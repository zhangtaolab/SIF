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
DOCS_ROOT = REPO_ROOT / "docs"
DESIGN_PATH = REPO_ROOT / "DESIGN.md"
CHANGELOG_PATH = (DOCS_ROOT / "changelog.md").resolve()
SELF_PATH = Path(__file__).resolve()


DEAD_DOC_LITERALS = (
    "sif.models.search",
    "sif/search/strategy.py",
    "sif/search/strategy",
    "sif/database/migrations.py",
    "MigrationManager",
    "SearchStrategy",
    "SearchContext",
    "Searchable",
    "compute_rrf_score",
    "CURRENT_SCHEMA_VERSION",
    "migrations.py",
    "strategy.py",
    "legacy migration module",
)


def _python_files() -> list[Path]:
    """Return every Python file the dead-reference scan covers (self excluded)."""
    files: list[Path] = []
    for root in (SRC_ROOT, TESTS_ROOT, EXAMPLES_ROOT):
        for path in sorted(root.rglob("*.py")):
            if path.resolve() == SELF_PATH:
                continue
            files.append(path)
    return files


def _doc_files() -> list[Path]:
    """Return every hand-maintained doc the absence scan covers (self/changelog excluded)."""
    files = [DESIGN_PATH]
    for path in sorted(DOCS_ROOT.rglob("*.md")):
        if path.resolve() in (CHANGELOG_PATH, SELF_PATH):
            continue
        files.append(path)
    return files


def _docs_without_changelog() -> list[Path]:
    """Return every docs page except the changelog (release history is exempt)."""
    return [path for path in sorted(DOCS_ROOT.rglob("*.md")) if path.resolve() != CHANGELOG_PATH]


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


def test_docs_do_not_describe_dead_layers() -> None:
    """Hand-maintained docs describe only the surviving layers."""
    offenders = [
        f"{literal!r} in {path.relative_to(REPO_ROOT)}"
        for literal in DEAD_DOC_LITERALS
        for path in _doc_files()
        if literal in path.read_text(encoding="utf-8")
    ]
    if offenders:
        pytest.fail("dead-layer documentation survives:\n" + "\n".join(offenders))


def test_docs_do_not_mention_pre_commit_target() -> None:
    """No docs page promises a pre-commit target the repository does not have."""
    offenders = [
        f"{token!r} in {path.relative_to(REPO_ROOT)}"
        for token in ("make pre-commit", "pre-commit install", "pre-commit autoupdate")
        for path in _docs_without_changelog()
        if token in path.read_text(encoding="utf-8")
    ]
    if offenders:
        pytest.fail("phantom pre-commit guidance survives:\n" + "\n".join(offenders))


def test_pre_commit_verify_markers_cleared() -> None:
    """No VERIFY marker about the phantom pre-commit flow survives."""
    offenders = [
        str(path.relative_to(REPO_ROOT))
        for path in _docs_without_changelog()
        for line in path.read_text(encoding="utf-8").splitlines()
        if "VERIFY:" in line and "pre-commit" in line
    ]
    if offenders:
        pytest.fail("pre-commit VERIFY markers survive in: " + ", ".join(offenders))


def test_bandit_verify_marker_retained() -> None:
    """Exactly one docs VERIFY marker survives, and it is the bandit marker."""
    markers = [
        f"{path.relative_to(REPO_ROOT)}: {line.strip()}"
        for path in _docs_without_changelog()
        for line in path.read_text(encoding="utf-8").splitlines()
        if "VERIFY:" in line
    ]
    assert len(markers) == 1, f"expected exactly one docs VERIFY marker, found: {markers}"
    assert "bandit" in markers[0], f"surviving VERIFY marker is not the bandit one: {markers[0]}"


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


def test_makefile_has_no_pre_commit_target() -> None:
    """The Makefile never invokes a tool the repository does not configure."""
    makefile_text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    assert "pre-commit" not in makefile_text


def test_pre_commit_config_absent() -> None:
    """No pre-commit configuration was introduced by the cleanup."""
    assert not (REPO_ROOT / ".pre-commit-config.yaml").exists()
