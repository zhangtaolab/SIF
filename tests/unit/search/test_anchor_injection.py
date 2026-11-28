"""End-to-end anchor injection tests (Phase 26, ANC-01/ANC-02/ANC-04).

The anchor arm reaches a real FTS index only through
``SearchOptions.anchor_terms``; it widens the BM25 match with OR alternatives
and leaves the default path byte-identical.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from sif.core.models import SearchOptions, SearchType
from sif.search.bm25 import BM25Searcher
from sif.search.hybrid import SearchPipeline
from tests.support.bench import ConceptEmbedder, build_bench_db


BENCH_CORPUS = Path("tests/fixtures/bench/corpus")

# A split=tuning fixture query whose rule anchors are non-empty: the phrase
# table expands "machine learning" and the token table expands both words.
TUNING_QUERY = "machine learning 机器学习"


@pytest.fixture
def bench_db():
    """Real FTS + vec0 index over the committed bench corpus (skips without vec)."""
    conn = build_bench_db(BENCH_CORPUS, ConceptEmbedder())
    try:
        yield conn
    finally:
        conn.close()


def test_search_type_anchor_value() -> None:
    """ANC-03: the anchor arm is its own search type."""
    assert SearchType.ANCHOR.value == "anchor"


def test_search_options_default_anchor_terms_is_none() -> None:
    """D-08: the injection point defaults to "no anchors supplied"."""
    assert SearchOptions().anchor_terms is None


def test_anchor_prefix_end_to_end_uses_rules(bench_db) -> None:
    """ANC-01/D-05: ``anchor:`` returns rows from the zero-model rule anchors."""
    pipeline = SearchPipeline(bench_db, parse_prefix=True)

    results = pipeline.search(f"anchor:{TUNING_QUERY}")

    assert results, "anchor: query returned no results"
    resolution = pipeline.last_anchor_resolution
    assert resolution is not None
    assert resolution.backend == "rules"
    assert resolution.terms


def test_anchor_prefix_preserves_lex_parity(bench_db) -> None:
    """The anchor arm is a BM25 single leg whose OR widening only adds rows."""
    pipeline = SearchPipeline(bench_db, parse_prefix=True)

    anchor_results = pipeline.search(f"anchor:{TUNING_QUERY}")
    lex_results = pipeline.search(f"lex:{TUNING_QUERY}")

    assert anchor_results
    assert lex_results
    assert {r.document_id for r in lex_results} <= {r.document_id for r in anchor_results}


def test_lex_query_leaves_no_anchor_resolution(bench_db) -> None:
    """Run-level metadata never leaks across calls on one pipeline."""
    pipeline = SearchPipeline(bench_db, parse_prefix=True)
    pipeline.search(f"anchor:{TUNING_QUERY}")
    assert pipeline.last_anchor_resolution is not None

    results = pipeline.search(f"lex:{TUNING_QUERY}")

    assert results
    assert pipeline.last_anchor_resolution is None


def test_bm25_or_alternative_shape(bench_db) -> None:
    """ANC-02: the default MATCH is byte-identical; anchors are OR alternatives."""
    searcher = BM25Searcher(bench_db)

    assert searcher._build_fts_query("hello world") == '"hello"* AND "world"*'
    assert searcher._build_fts_query("hello world", None) == '"hello"* AND "world"*'
    assert searcher._build_fts_query("hello world", []) == '"hello"* AND "world"*'
    assert (
        searcher._build_fts_query("hello world", ["machine learning"])
        == '("hello"* AND "world"*) OR "machine learning"*'
    )


def test_injected_anchor_terms_bypass_the_resolver(bench_db) -> None:
    """D-08: explicit terms are injected verbatim and reported as injected."""
    pipeline = SearchPipeline(bench_db, parse_prefix=True)

    pipeline.search(f"anchor:{TUNING_QUERY}", SearchOptions(anchor_terms=["_absentterm_zz"]))

    resolution = pipeline.last_anchor_resolution
    assert resolution is not None
    assert resolution.backend == "injected"
    assert resolution.terms == ["_absentterm_zz"]


def test_highlights_use_the_original_query(bench_db) -> None:
    """ANC-02: the highlight pass receives the anchor-free query text."""
    searcher = BM25Searcher(bench_db)

    with patch.object(searcher, "_get_highlights", wraps=searcher._get_highlights) as spy:
        results = searcher.search(TUNING_QUERY, SearchOptions(anchor_terms=["machine learning"]))

    assert results
    assert spy.called
    for call in spy.call_args_list:
        # (document_id, query, max_highlights) — the instance attribute is not
        # bound, so the query is the second positional argument.
        assert call.args[1] == TUNING_QUERY


class _RecordingSnippetExtractor:
    """Record ``query_terms`` and return a fixed snippet window."""

    def __init__(self) -> None:
        self.query_terms: list[list[str]] = []

    def extract_with_range(self, _text: str, query_terms: list[str]) -> tuple[str, int, int]:
        self.query_terms.append(list(query_terms))
        return "snippet", 1, 1


def test_snippets_use_the_original_query_terms(bench_db) -> None:
    """ANC-02: snippet extraction sees ``parsed_query`` terms, never anchors."""
    extractor = _RecordingSnippetExtractor()
    pipeline = SearchPipeline(bench_db, snippet_extractor=extractor, parse_prefix=True)

    results = pipeline.search(f"anchor:{TUNING_QUERY}")

    assert results
    assert extractor.query_terms
    expected = TUNING_QUERY.lower().split()
    for terms in extractor.query_terms:
        assert terms == expected


def test_empty_anchor_terms_bypass_the_resolver_and_match_lex(bench_db) -> None:
    """D-08: ``[]`` is "explicitly no anchors" and reproduces the lex page."""
    pipeline = SearchPipeline(bench_db, parse_prefix=True)

    anchor_results = pipeline.search(f"anchor:{TUNING_QUERY}", SearchOptions(anchor_terms=[]))
    resolution = pipeline.last_anchor_resolution
    assert resolution is not None
    assert resolution.backend == "injected"
    assert resolution.terms == []

    lex_results = pipeline.search(f"lex:{TUNING_QUERY}")

    assert [(result.document_id, result.score, result.rank) for result in anchor_results] == [
        (result.document_id, result.score, result.rank) for result in lex_results
    ]


def test_default_path_does_not_import_the_anchor_module() -> None:
    """ANC-01: constructing the default path never imports sif.search.anchor."""
    code = (
        "import sys;"
        "from sif.search.hybrid import SearchPipeline;"
        "from sif.core.models import SearchOptions;"
        "assert SearchOptions().anchor_terms is None;"
        "assert 'sif.search.anchor' not in sys.modules"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr


def test_anchor_module_is_imported_only_on_demand() -> None:
    """ANC-01: the module appears in sys.modules only after an explicit import."""
    code = (
        "import sys;"
        "from sif.search.hybrid import SearchPipeline;"
        "assert 'sif.search.anchor' not in sys.modules;"
        "from sif.search.anchor import derive_rule_anchors;"
        "assert 'sif.search.anchor' in sys.modules"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
