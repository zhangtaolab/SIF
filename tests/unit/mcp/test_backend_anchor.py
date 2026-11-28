"""MCP ``anchor:`` route: read-only rule anchors, no embedder, no cache write.

Phase 26 (D-05/T-26-03): the MCP surface has seven read-only tools, so the
anchor route is isomorphic to ``lex:`` — it derives the zero-model rule
anchors, runs one BM25 leg, and returns before any embedder load or cache
write.
"""

from __future__ import annotations

import asyncio
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from sif.config.settings import Settings
from sif.core.models import SearchType
from sif.database.schema import SchemaManager
from sif.mcp.backend import SearchBackend, _split_query_prefix
from sif.search.hybrid import PREFIX_ROUTES


def _settings(**overrides: object) -> Settings:
    return Settings(
        _env_file=None,
        embedding_dim=8,
        model_name="test",
        cache_embeddings=False,
        **overrides,
    )


def _seed_db(tmp_path: Path) -> Path:
    """Real schema plus one document whose text carries an anchor-table token."""
    db_path = tmp_path / "anchor.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        SchemaManager(conn, embedding_dim=8).create_all()
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO collections (id, name, path, created_at, updated_at)"
            " VALUES ('c1', 'notes', '/vault', ?, ?)",
            (now, now),
        )
        conn.execute(
            "INSERT INTO documents (id, collection_id, path, filename, title,"
            " content, checksum, mtime, created_at, updated_at)"
            " VALUES ('d1', 'c1', '/vault/seed.md', 'seed.md', 'Seed',"
            " 'seed paragraph quantum machine', 'ck-1', 1.0, ?, ?)",
            (now, now),
        )
        conn.commit()
    finally:
        conn.close()
    return db_path


def test_anchor_query_returns_rows_without_loading_embedder(tmp_path: Path) -> None:
    """T-26-03: ``anchor:`` returns BM25 rows and never calls _ensure_embedder."""
    backend = SearchBackend(str(_seed_db(tmp_path)), settings=_settings())

    with patch.object(
        backend,
        "_ensure_embedder",
        side_effect=AssertionError("anchor: route must not load an embedder"),
    ):
        results = asyncio.run(backend.hybrid_search("anchor:quantum"))

    assert results
    assert any(result.doc_id == "d1" for result in results)


def test_anchor_query_writes_no_llm_cache(tmp_path: Path) -> None:
    """T-26-03: the MCP anchor route stays read-only — no llm_cache rows."""
    db_path = _seed_db(tmp_path)
    backend = SearchBackend(str(db_path), settings=_settings())

    asyncio.run(backend.hybrid_search("anchor:quantum"))

    conn = sqlite3.connect(db_path)
    try:
        count = conn.execute("SELECT COUNT(*) FROM llm_cache").fetchone()[0]
    finally:
        conn.close()
    assert count == 0


def test_prefix_routes_include_anchor_exactly_once() -> None:
    """ANC-03: pipeline and MCP share one table with a single anchor mapping."""
    assert set(PREFIX_ROUTES) == {"lex:", "vec:", "hyde:", "expand:", "anchor:"}
    assert PREFIX_ROUTES["anchor:"] is SearchType.ANCHOR


def test_split_query_prefix_strips_only_the_first_prefix() -> None:
    """D-03: ``anchor:lex:foo`` is literal text, not a nested route."""
    assert _split_query_prefix("anchor:quantum", "hybrid") == ("quantum", SearchType.ANCHOR)
    assert _split_query_prefix("anchor:lex:foo", "hybrid") == ("lex:foo", SearchType.ANCHOR)


def _capture_anchor_terms(db_path: Path, settings: Settings) -> list[str] | None:
    """Run the MCP anchor route with a spied BM25 leg; return its anchor terms."""
    backend = SearchBackend(str(db_path), settings=settings)
    with (
        patch.object(
            backend,
            "_ensure_embedder",
            side_effect=AssertionError("anchor: route must not load an embedder"),
        ),
        patch("sif.mcp.backend.BM25Searcher") as mock_bm25,
    ):
        mock_bm25.return_value.search.return_value = []
        asyncio.run(backend.hybrid_search("anchor:cloud computing"))
    options = mock_bm25.return_value.search.call_args.args[1]
    return options.anchor_terms


def _llm_cache_count(db_path: Path) -> int:
    conn = sqlite3.connect(db_path)
    try:
        return int(conn.execute("SELECT COUNT(*) FROM llm_cache").fetchone()[0])
    finally:
        conn.close()


def test_vocab_guard_off_keeps_oov_rule_anchors(tmp_path: Path) -> None:
    """ANC-05: with the A/B off, rule anchors absent from the corpus survive."""
    db_path = _seed_db(tmp_path)

    terms = _capture_anchor_terms(db_path, _settings())

    assert terms is not None
    assert "云计算" in terms
    assert _llm_cache_count(db_path) == 0


def test_vocab_guard_on_drops_oov_rule_anchors_read_only(tmp_path: Path) -> None:
    """ANC-05/T-26-13: the guard filters in memory and writes no cache row."""
    db_path = _seed_db(tmp_path)

    terms = _capture_anchor_terms(db_path, _settings(anchor_vocab_guard=True))

    assert terms is None
    assert _llm_cache_count(db_path) == 0
