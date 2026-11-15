"""Unit tests for the D-08 checksum convention shared by every parser.

D-08 retired the old body-only convention: change detection hashes the body
plus the FULL canonical frontmatter dict (``sif.core.models.compute_checksum``),
so a frontmatter-only edit is visible to the incremental loop and Phase 20's
metadata filters can never serve a stale tag/title value. The canonical
serializer (``sort_keys=True``, ``default=str``, recursively string-coerced
keys, compact separators) is also the persisted metadata form, so the hashed
and stored strings agree across a JSON round trip.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from sif.core.models import canonical_metadata_json, compute_checksum
from sif.indexing.parser import MarkdownParser


DOC_WITH_FM = (
    '---\ntitle: "Probe"\nauthor: "T"\ntags: [a, b]\n---\n\n# Probe\n\nBody paragraph text.\n'
)
DOC_NO_FM = "# No Frontmatter\n\nPlain body text.\n"


def test_checksum_covers_body_and_full_frontmatter(tmp_path: Path) -> None:
    """Checksum equals sha256(body ‖ NUL ‖ canonical(frontmatter))."""
    parser = MarkdownParser()
    doc_file = tmp_path / "a.md"
    doc_file.write_text(DOC_WITH_FM, encoding="utf-8")

    parsed = parser.parse(doc_file)

    assert parsed.checksum == compute_checksum(parsed.content, parsed.metadata)
    assert parsed.metadata == {"title": "Probe", "author": "T", "tags": ["a", "b"]}

    # D-08 inversion: a frontmatter-only edit MUST change the checksum. The
    # old body-only convention deliberately kept it stable, which is what
    # served stale metadata to later consumers.
    doc_file.write_text(
        DOC_WITH_FM.replace('author: "T"', 'author: "Someone Else"'), encoding="utf-8"
    )
    reparsed = parser.parse(doc_file)
    assert reparsed.checksum != parsed.checksum
    assert reparsed.content == parsed.content  # the stored body path is unchanged


def test_checksum_without_frontmatter_hashes_body_and_empty_mapping(tmp_path: Path) -> None:
    """No frontmatter -> the canonical metadata input is the empty mapping."""
    parser = MarkdownParser()
    doc_file = tmp_path / "b.md"
    doc_file.write_text(DOC_NO_FM, encoding="utf-8")

    parsed = parser.parse(doc_file)
    # python-frontmatter strips only the trailing newline when no FM exists;
    # the checksum must use the stored body either way.
    assert parsed.content.rstrip("\n") == DOC_NO_FM.rstrip("\n")
    assert parsed.checksum == compute_checksum(parsed.content, {})


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


def test_compute_checksum_contract_is_body_nul_canonical_metadata() -> None:
    """The exact input is content bytes ‖ one NUL byte ‖ canonical JSON bytes."""
    assert compute_checksum("body", {}) == hashlib.sha256(b"body\x00{}").hexdigest()
    # Key order must not matter: the canonical serializer sorts keys.
    assert compute_checksum("body", {"a": 1, "b": 2}) == compute_checksum("body", {"b": 2, "a": 1})


def test_canonical_json_is_key_order_independent_and_unicode_preserving() -> None:
    """sort_keys + ensure_ascii=False make the canonical form stable and literal."""
    assert canonical_metadata_json({"b": 2, "a": 1}) == '{"a":1,"b":2}'
    assert canonical_metadata_json({"b": 2, "a": 1}) == canonical_metadata_json({"a": 1, "b": 2})
    assert canonical_metadata_json({"title": "本地"}) == '{"title":"本地"}'


def test_canonical_json_coerces_keys_at_every_nesting_depth() -> None:
    """A nested mixed-key mapping serializes instead of raising TypeError.

    ``default=str`` only covers values, so key coercion must recurse through
    nested mappings (and sequences of mappings) for the serializer to be total.
    """
    assert canonical_metadata_json({"outer": {1: "a", "b": 2}}) == ('{"outer":{"1":"a","b":2}}')
    assert canonical_metadata_json({"items": [{1: "a"}, {2: "b"}]}) == (
        '{"items":[{"1":"a"},{"2":"b"}]}'
    )
