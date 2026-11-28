"""ANC-05 vocabulary guard: a default-off A/B that drops OOV anchor terms.

The probe and the guard share the same ``documents_fts MATCH`` expression the
BM25 leg uses, so a porter-stemmed inflected word and a contiguous CJK run are
judged the way retrieval judges them. The guard filters at read time: the
resolver still caches the generator's raw terms, so flipping the A/B never
changes what ``llm_cache`` stores.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

import pytest

from sif.config.settings import Settings
from sif.database.schema import SchemaManager
from sif.search.anchor import (
    AnchorResolver,
    derive_rule_anchors,
    normalize_query,
)
from sif.search.bm25 import BM25Searcher


class FakeGenerator:
    """Return a fixed term list and count calls."""

    model_id = "fake-1"

    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0

    def generate(self, _prompt: str) -> str:
        self.calls += 1
        return self.response


def _settings(**overrides: object) -> Settings:
    return Settings(
        _env_file=None,
        embedding_dim=8,
        cache_embeddings=False,
        **overrides,
    )


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    """Real schema plus one document whose text carries stemmed and CJK terms."""
    connection = sqlite3.connect(str(tmp_path / "sif.db"))
    connection.row_factory = sqlite3.Row
    SchemaManager(connection, embedding_dim=8).create_all()
    now = datetime.now(timezone.utc).isoformat()
    connection.execute(
        "INSERT INTO collections (id, name, path, created_at, updated_at)"
        " VALUES ('c1', 'notes', '/vault', ?, ?)",
        (now, now),
    )
    connection.execute(
        "INSERT INTO documents (id, collection_id, path, filename, title,"
        " content, checksum, mtime, created_at, updated_at)"
        " VALUES ('d1', 'c1', '/vault/seed.md', 'seed.md', 'Seed',"
        " 'starter cultures and 机器学习 notes', 'ck-1', 1.0, ?, ?)",
        (now, now),
    )
    connection.commit()
    try:
        yield connection
    finally:
        connection.close()


def test_term_in_index_uses_porter_stems_and_cjk_tokens(
    conn: sqlite3.Connection,
) -> None:
    """The probe speaks the index tokenizer: stems match, CJK matches, junk does not."""
    searcher = BM25Searcher(conn)
    assert searcher.term_in_index("culture") is True
    assert searcher.term_in_index("cultures") is True
    assert searcher.term_in_index("机器学习") is True
    assert searcher.term_in_index("zzzznotaterm") is False
    assert searcher.term_in_index('":*()"') is False


def test_guard_defaults_off_and_keeps_rule_baseline(
    conn: sqlite3.Connection,
) -> None:
    """ANC-05: the default-off path is byte-identical to ``derive_rule_anchors``."""
    resolver = AnchorResolver(conn, _settings())
    expected = derive_rule_anchors(normalize_query("machine learning"))

    first = resolver.resolve("machine learning")
    second = resolver.resolve("machine learning")

    assert first.terms == expected
    assert second.terms == expected
    # The zero-model rules backend never writes a cache row (Open Question 3).
    assert conn.execute("SELECT COUNT(*) FROM llm_cache").fetchone()[0] == 0


def test_guard_on_filters_rule_anchors_to_known_terms(
    conn: sqlite3.Connection,
) -> None:
    """Turning the A/B on drops exactly the terms absent from the FTS vocabulary."""
    default_terms = derive_rule_anchors(normalize_query("machine learning"))
    searcher = BM25Searcher(conn)

    terms = (
        AnchorResolver(conn, _settings(anchor_vocab_guard=True)).resolve("machine learning").terms
    )

    assert set(terms) <= set(default_terms)
    assert terms == [term for term in default_terms if searcher.term_in_index(term)]
    assert "机器学习" in terms
    assert "statistical learning" not in terms


def test_guard_on_filters_cached_terms_without_changing_cache(
    conn: sqlite3.Connection,
) -> None:
    """Both first-read and cached reads are filtered; ``llm_cache`` keeps raw terms."""
    fake = FakeGenerator("cultures\nzzzznotaterm\n")
    resolver = AnchorResolver(
        conn,
        _settings(anchor_backend="gguf", anchor_vocab_guard=True),
        generator=fake,
    )

    first = resolver.resolve("starter culture")
    second = resolver.resolve("starter culture")

    assert fake.calls == 1
    assert first.terms == ["cultures"]
    assert second.terms == ["cultures"]
    assert second.cache_hits == 1
    cached = conn.execute("SELECT response FROM llm_cache").fetchone()[0]
    assert json.loads(cached)["terms"] == ["cultures", "zzzznotaterm"]
