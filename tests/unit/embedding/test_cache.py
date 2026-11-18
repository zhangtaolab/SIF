"""Real-SQLite behavior and failure-boundary tests for EmbeddingCache."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from sif.database.factory import create_connection
from sif.embedding.cache import EmbeddingCache, _connection


class TestEmbeddingCache:
    """Persistent cache round trips, segmentation, batching, and corruption handling."""

    def test_miss_store_hit_replacement_and_persistence(self, tmp_path: Path):
        """A miss stores a vector, later instances hit it, and replacement updates it."""
        cache_dir = tmp_path / "cache"
        cache = EmbeddingCache(cache_dir)

        assert cache._db_path == cache_dir / "embeddings_cache.db"
        assert cache.get("persistent content", "model-a") is None
        cache.set("persistent content", [0.1, 0.2], "model-a")
        assert cache.get("persistent content", "model-a") == [0.1, 0.2]

        reopened = EmbeddingCache(cache_dir)
        assert reopened.get("persistent content", "model-a") == [0.1, 0.2]
        reopened.set("persistent content", [0.3, 0.4], "model-a")
        assert reopened.get("persistent content", "model-a") == [0.3, 0.4]

    def test_batch_round_trip_and_empty_lists(self, tmp_path: Path):
        """Batch reads preserve input order and the empty-list contract returns []."""
        cache = EmbeddingCache(tmp_path / "cache")

        assert cache.get_batch([]) == []
        cache.set_batch([], [])
        cache.set_batch(["first", "second"], [[1.0], [2.0]], "model-batch")
        assert cache.get_batch(["second", "missing", "first"], "model-batch") == [
            [2.0],
            None,
            [1.0],
        ]

    def test_batch_length_mismatch_is_strict(self, tmp_path: Path):
        """zip(strict=True) rejects an embedding count different from the content count."""
        cache = EmbeddingCache(tmp_path / "cache")

        with pytest.raises(ValueError, match="shorter"):
            cache.set_batch(["one", "two"], [[1.0]], "model-strict")

        assert cache.get("one", "model-strict") == [1.0]
        assert cache.get("two", "model-strict") is None

    def test_same_content_is_segmented_by_model(self, tmp_path: Path):
        """One content hash can hold independent vectors for separate model IDs."""
        cache = EmbeddingCache(tmp_path / "cache")
        cache.set("shared text", [1.0, 1.5], "model-a")
        cache.set("shared text", [2.0, 2.5], "model-b")

        assert cache.get("shared text", "model-a") == [1.0, 1.5]
        assert cache.get("shared text", "model-b") == [2.0, 2.5]
        assert cache.get_stats() == {
            "total_entries": 2,
            "by_model": {"model-a": 1, "model-b": 1},
        }

    def test_clear_model_and_clear_all(self, tmp_path: Path):
        """Scoped clear preserves other models; unscoped clear removes every entry."""
        cache = EmbeddingCache(tmp_path / "cache")
        cache.set_batch(["a", "b"], [[1.0], [2.0]], "model-a")
        cache.set("c", [3.0], "model-b")

        assert cache.clear("model-a") == 2
        assert cache.get("a", "model-a") is None
        assert cache.get("c", "model-b") == [3.0]
        assert cache.clear("missing") == 0
        assert cache.clear() == 1
        assert cache.get_stats() == {"total_entries": 0, "by_model": {}}
        assert cache.clear() == 0

    def test_empty_and_unicode_content_hash_contracts(self, tmp_path: Path):
        """Empty text hashes as SHA-256 input and Unicode uses UTF-8 bytes."""
        cache = EmbeddingCache(tmp_path / "cache")
        unicode_content = "知识库 café \U0001f4da"
        cache.set("", [0.0], "model-edge")
        cache.set(unicode_content, [9.0], "model-edge")

        assert cache.get("", "model-edge") == [0.0]
        assert cache.get(unicode_content, "model-edge") == [9.0]
        conn = sqlite3.connect(cache._db_path)
        try:
            rows = conn.execute(
                "SELECT content_hash FROM embeddings WHERE model_id = 'model-edge'",
            ).fetchall()
        finally:
            conn.close()
        assert {row[0] for row in rows} == {
            hashlib.sha256(b"").hexdigest(),
            hashlib.sha256(unicode_content.encode("utf-8")).hexdigest(),
        }

    def test_legacy_content_only_primary_key_is_rebuilt(self, tmp_path: Path):
        """A legacy single-key cache is replaced with a per-model segmented table."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        db_path = cache_dir / "embeddings_cache.db"
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "CREATE TABLE embeddings ("
                "content_hash TEXT PRIMARY KEY, embedding TEXT NOT NULL, "
                "model_id TEXT NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)",
            )
            conn.execute(
                "INSERT INTO embeddings (content_hash, embedding, model_id) "
                "VALUES ('legacy', '[1.0]', 'old-model')",
            )
            conn.commit()
        finally:
            conn.close()

        cache = EmbeddingCache(cache_dir)

        assert cache.get("legacy", "old-model") is None
        cache.set("shared", [1.0], "model-a")
        cache.set("shared", [2.0], "model-b")
        assert cache.get("shared", "model-a") == [1.0]
        assert cache.get("shared", "model-b") == [2.0]

    def test_corrupt_embedding_json_returns_miss_and_can_be_replaced(self, tmp_path: Path):
        """Malformed stored JSON degrades to a miss, then a normal set repairs the row."""
        cache = EmbeddingCache(tmp_path / "cache")
        content_hash = hashlib.sha256(b"corrupt").hexdigest()
        conn = sqlite3.connect(cache._db_path)
        try:
            conn.execute(
                "INSERT INTO embeddings (content_hash, embedding, model_id) "
                "VALUES (?, 'not-json', 'model-corrupt')",
                (content_hash,),
            )
            conn.commit()
        finally:
            conn.close()

        assert cache.get("corrupt", "model-corrupt") is None
        cache.set("corrupt", [4.0], "model-corrupt")
        assert cache.get("corrupt", "model-corrupt") == [4.0]

    def test_connection_uses_shared_factory_and_pragmas(self, tmp_path: Path):
        """W-1: every cache connection is acquired through the Phase 11 factory.

        Delegation is proven at the module seam (the factory is called with
        the cache DB path) and on the real file: busy_timeout 5000 and
        synchronous NORMAL are per-connection settings, so they are read on
        the cache's own factory-delegated connection; WAL persists in the
        file header and is additionally read from a plain sqlite3.connect.
        """
        cache_dir = tmp_path / "cache"
        db_path = cache_dir / "embeddings_cache.db"
        with patch("sif.embedding.cache.create_connection", wraps=create_connection) as factory:
            cache = EmbeddingCache(cache_dir)
            cache.set("content", [1.0], "model")
        assert factory.call_args is not None
        assert factory.call_args.args == (db_path,)

        with _connection(db_path) as conn:
            assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
            assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
            assert conn.execute("PRAGMA synchronous").fetchone()[0] == 1

        raw = sqlite3.connect(db_path)
        try:
            assert raw.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        finally:
            raw.close()

    def test_get_set_clear_and_stats_failure_fallbacks(self, tmp_path: Path):
        """External connection failures return documented fallbacks and do not corrupt data."""
        cache = EmbeddingCache(tmp_path / "cache")
        cache.set("survivor", [7.0], "model-safe")
        with patch("sif.embedding.cache.create_connection", side_effect=OSError("connect failed")):
            assert cache.get("survivor", "model-safe") is None
            assert cache.set("survivor", [8.0], "model-safe") is None
            assert cache.clear("model-safe") == 0
            assert cache.get_stats() == {"total_entries": 0, "by_model": {}}

        assert cache.get("survivor", "model-safe") == [7.0]
        assert cache.get_stats() == {"total_entries": 1, "by_model": {"model-safe": 1}}

    def test_corrupt_table_shape_get_stats_falls_back_then_init_repairs(self, tmp_path: Path):
        """A real malformed table triggers stats fallback and is repaired on reopen."""
        cache = EmbeddingCache(tmp_path / "cache")
        conn = sqlite3.connect(cache._db_path)
        try:
            conn.execute("ALTER TABLE embeddings RENAME TO embeddings_valid")
            conn.execute("CREATE TABLE embeddings (wrong_column TEXT)")
            conn.commit()
        finally:
            conn.close()

        assert cache.get_stats() == {"total_entries": 0, "by_model": {}}

        repaired = EmbeddingCache(tmp_path / "cache")
        repaired.set("after-repair", [1.0], "model-repaired")
        assert repaired.get("after-repair", "model-repaired") == [1.0]
        conn = sqlite3.connect(repaired._db_path)
        try:
            row = conn.execute(
                "SELECT embedding FROM embeddings WHERE model_id = 'model-repaired'",
            ).fetchone()
        finally:
            conn.close()
        assert row is not None
        assert json.loads(row[0]) == [1.0]
