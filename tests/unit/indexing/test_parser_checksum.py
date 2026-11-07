"""Unit tests for MarkdownParser checksum convention (t_66218b67).

The parser must hash the frontmatter-stripped body — the same convention the
storage path uses (core.models.Document hashes Document.content, which is the
body). Hashing the whole file makes the two conventions incomparable and
misreports every document as changed on `sif index update`.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from sif.indexing.parser import MarkdownParser


DOC_WITH_FM = (
    '---\ntitle: "Probe"\nauthor: "T"\ntags: [a, b]\n---\n\n# Probe\n\nBody paragraph text.\n'
)
DOC_NO_FM = "# No Frontmatter\n\nPlain body text.\n"


def test_checksum_covers_body_not_frontmatter(tmp_path: Path) -> None:
    """Checksum equals sha256(stored body); frontmatter-only edits keep it."""
    parser = MarkdownParser()
    doc_file = tmp_path / "a.md"
    doc_file.write_text(DOC_WITH_FM, encoding="utf-8")

    parsed = parser.parse(doc_file)

    # The convention under test: checksum = sha256 of the content SIF stores
    # (the body), NOT sha256 of the raw file.
    assert parsed.checksum == hashlib.sha256(parsed.content.encode()).hexdigest()
    assert parsed.checksum != hashlib.sha256(DOC_WITH_FM.encode()).hexdigest()

    # A frontmatter-only edit must not change the checksum (metadata refresh
    # alone never triggers a full document rewrite).
    doc_file.write_text(
        DOC_WITH_FM.replace('author: "T"', 'author: "Someone Else"'), encoding="utf-8"
    )
    reparsed = parser.parse(doc_file)
    assert reparsed.checksum == parsed.checksum


def test_checksum_without_frontmatter_hashes_content(tmp_path: Path) -> None:
    """No frontmatter -> checksum covers exactly what SIF stores (the body)."""
    parser = MarkdownParser()
    doc_file = tmp_path / "b.md"
    doc_file.write_text(DOC_NO_FM, encoding="utf-8")

    parsed = parser.parse(doc_file)
    # python-frontmatter strips only the trailing newline when no FM exists;
    # the checksum must match the stored body either way.
    assert parsed.content.rstrip("\n") == DOC_NO_FM.rstrip("\n")
    assert parsed.checksum == hashlib.sha256(parsed.content.encode()).hexdigest()


def test_checksum_changes_with_body_edit(tmp_path: Path) -> None:
    """A body edit does change the checksum (change detection stays intact)."""
    parser = MarkdownParser()
    doc_file = tmp_path / "c.md"
    doc_file.write_text(DOC_WITH_FM, encoding="utf-8")
    before = parser.parse(doc_file).checksum

    doc_file.write_text(
        DOC_WITH_FM.replace("Body paragraph text.", "Edited paragraph text."),
        encoding="utf-8",
    )
    after = parser.parse(doc_file).checksum
    assert before != after
