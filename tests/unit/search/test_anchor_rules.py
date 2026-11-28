"""Zero-model rule anchor derivation (Phase 26, ANC-01/GEN-01).

The derivation is a pure function of the query string and the embedded table,
so these assertions pin the table semantics without any database or model.
"""

from __future__ import annotations

import subprocess
import sys

from sif.search.anchor import (
    ANCHOR_TABLE,
    ANCHOR_TABLE_VERSION,
    MAX_ANCHORS_PER_QUERY,
    derive_rule_anchors,
    normalize_query,
)


def test_anchor_table_version() -> None:
    assert ANCHOR_TABLE_VERSION == 1
    rules = ANCHOR_TABLE["rules"]
    assert isinstance(rules, dict)
    assert rules["max_anchors_per_query"] == MAX_ANCHORS_PER_QUERY == 6


def test_normalize_query() -> None:
    """NFKC + casefold + whitespace collapse, CJK preserved."""
    assert normalize_query("  Machine   Learning ") == "machine learning"
    assert normalize_query("MACHINE\tlearning\n") == "machine learning"
    assert normalize_query("机器学习") == "机器学习"


def test_phrase_expansion_is_capped_at_six() -> None:
    """Phrase + token expansion hits the frozen cap in table order."""
    assert derive_rule_anchors("machine learning") == [
        "statistical learning",
        "机器学习",
        "computer",
        "automated",
        "training",
        "education",
    ]


def test_derivation_is_case_insensitive() -> None:
    assert derive_rule_anchors("MACHINE Learning") == derive_rule_anchors("machine learning")


def test_candidates_are_deduplicated() -> None:
    anchors = derive_rule_anchors("machine machine learning")
    assert len(anchors) == len(set(anchors))


def test_cjk_reverse_mapping() -> None:
    """A CJK query token expands to its English form."""
    assert derive_rule_anchors("机器学习") == ["machine learning"]


def test_compound_expands_into_parts() -> None:
    assert derive_rule_anchors("pathfinding") == ["path", "finding"]


def test_query_terms_are_excluded() -> None:
    """A candidate whose tokens are all in the query never repeats them."""
    anchors = derive_rule_anchors("machine learning 机器学习")
    assert "机器学习" not in anchors
    assert "machine learning" not in anchors
    assert anchors == [
        "statistical learning",
        "computer",
        "automated",
        "training",
        "education",
    ]


def test_cap_never_exceeded() -> None:
    anchors = derive_rule_anchors("machine learning deep learning neural networks")
    assert len(anchors) == MAX_ANCHORS_PER_QUERY


def test_module_import_is_stdlib_only() -> None:
    """ANC-01/D-05: importing the module never pulls in optional model deps."""
    code = (
        "import sys;"
        "import sif.search.anchor;"
        "assert 'llama_cpp' not in sys.modules;"
        "assert 'jinja2' not in sys.modules"
    )
    subprocess.run([sys.executable, "-c", code], check=True)
