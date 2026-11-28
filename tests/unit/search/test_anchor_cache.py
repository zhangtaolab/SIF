"""Deterministic anchor cache (Phase 26, GEN-02/GEN-03/D-09..D-11/D-14).

Every test uses a real SQLite connection and the real ``LLMCacheRepository``;
nothing mocks the cache. The cross-connection case is the regression that
pins the "commit before returning" contract: a same-connection hit passes even
when the write was never committed, while a second independent connection only
sees the row if ``AnchorResolver.resolve`` committed its own write.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from sif.config.settings import Settings
from sif.database.schema import SchemaManager
from sif.search.anchor import (
    AnchorBudgetExceeded,
    AnchorGenerationFailed,
    AnchorResolver,
    derive_rule_anchors,
)
from sif.search.benchmark import iter_grid


QUERIES = ("machine learning", "deep learning", "route planning")


class FakeGenerator:
    """Counts calls and returns (or raises) a scripted response."""

    model_id = "fake-1"

    def __init__(
        self,
        response: str = "alpha\nbeta\nAlpha\n",
        error: Exception | None = None,
    ) -> None:
        self.response = response
        self.error = error
        self.calls = 0

    def generate(self, _prompt: str) -> str:
        self.calls += 1
        if self.error is not None:
            raise self.error
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
    """File-backed real schema (a second connection must read the same rows)."""
    connection = sqlite3.connect(str(tmp_path / "sif.db"), isolation_level="IMMEDIATE")
    connection.row_factory = sqlite3.Row
    SchemaManager(connection, embedding_dim=8).create_all()
    try:
        yield connection
    finally:
        connection.close()


def _row_count(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM llm_cache").fetchone()[0])


def test_same_resolver_second_resolve_hits_cache(conn: sqlite3.Connection) -> None:
    """GEN-02: the second resolution of the same query costs zero generations."""
    fake = FakeGenerator()
    resolver = AnchorResolver(conn, _settings(anchor_backend="gguf"), generator=fake)

    first = resolver.resolve("Machine Learning")
    second = resolver.resolve("Machine Learning")

    assert fake.calls == 1
    assert first.generator_calls == 1
    assert first.cache_hits == 0
    assert second.generator_calls == 0
    assert second.cache_hits == 1
    assert first.terms == second.terms == ["alpha", "beta"]


def test_second_resolver_instance_hits_cache(conn: sqlite3.Connection) -> None:
    """D-11: a new resolver on the same DB does not share in-process state."""
    first_fake = FakeGenerator()
    AnchorResolver(conn, _settings(anchor_backend="gguf"), generator=first_fake).resolve(
        "Machine Learning"
    )

    second_fake = FakeGenerator()
    resolution = AnchorResolver(
        conn, _settings(anchor_backend="gguf"), generator=second_fake
    ).resolve("Machine Learning")

    assert first_fake.calls == 1
    assert second_fake.calls == 0
    assert resolution.cache_hits == 1
    assert resolution.generator_calls == 0


def test_second_independent_connection_hits_the_committed_row(
    conn: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    """BLOCKER-2 regression: the cache row is committed for another process.

    A missing ``conn.commit()`` in the resolver leaves the row in the first
    connection's transaction; the same-connection hit above would still pass,
    but this second ``sqlite3.Connection`` cannot see the row.
    """
    first_fake = FakeGenerator()
    AnchorResolver(conn, _settings(anchor_backend="gguf"), generator=first_fake).resolve(
        "Machine Learning"
    )

    second_conn = sqlite3.connect(str(tmp_path / "sif.db"), isolation_level="IMMEDIATE")
    second_conn.row_factory = sqlite3.Row
    try:
        count = second_conn.execute(
            "SELECT COUNT(*) FROM llm_cache WHERE model_name = 'anchor::gguf::fake-1'"
        ).fetchone()[0]
        assert count >= 1

        second_fake = FakeGenerator()
        resolution = AnchorResolver(
            second_conn, _settings(anchor_backend="gguf"), generator=second_fake
        ).resolve("Machine Learning")

        assert resolution.generator_calls == 0
        assert resolution.cache_hits == 1
        assert second_fake.calls == 0
        assert resolution.terms == ["alpha", "beta"]
    finally:
        second_conn.close()


def test_grid_sweep_generates_once_per_query(conn: sqlite3.Connection) -> None:
    """GEN-02: 45 configurations x 3 queries is N generations, never 45N."""
    fake = FakeGenerator()
    resolver = AnchorResolver(conn, _settings(anchor_backend="gguf"), generator=fake)

    hits = 0
    configs = 0
    for _config in iter_grid():
        configs += 1
        for query in QUERIES:
            hits += resolver.resolve(query).cache_hits

    assert configs == 45
    assert fake.calls == len(QUERIES)
    assert hits == 45 * len(QUERIES) - len(QUERIES)


def test_expired_cache_row_regenerates(conn: sqlite3.Connection) -> None:
    """GEN-02/TTL: an expired row is a miss, so the next resolution regenerates."""
    fake = FakeGenerator()
    resolver = AnchorResolver(
        conn,
        _settings(anchor_backend="gguf", anchor_cache_ttl=1),
        generator=fake,
    )
    resolver.resolve("machine learning")

    conn.execute("UPDATE llm_cache SET expires_at = '2000-01-01T00:00:00+00:00'")
    conn.commit()

    resolution = resolver.resolve("machine learning")
    assert fake.calls == 2
    assert resolution.generator_calls == 1


def test_generation_failure_writes_no_row_and_latches(conn: sqlite3.Connection) -> None:
    """GEN-03/D-13: a failed generation writes nothing and is not retried."""
    fake = FakeGenerator(error=AnchorGenerationFailed("timeout"))
    resolver = AnchorResolver(conn, _settings(anchor_backend="gguf"), generator=fake)

    first = resolver.resolve("machine learning")
    assert first.terms == []
    assert first.generator_calls == 1
    assert first.fallback_reason == "timeout"
    assert _row_count(conn) == 0

    second = resolver.resolve("machine learning")
    assert fake.calls == 1
    assert second.fallback_reason == "timeout"
    assert second.terms == []


def test_namespace_is_anchor_prefixed(conn: sqlite3.Connection) -> None:
    """D-09: anchor rows live under their own ``anchor::<backend>::<model>``."""
    resolver = AnchorResolver(conn, _settings(anchor_backend="gguf"), generator=FakeGenerator())
    resolver.resolve("machine learning")

    names = {row[0] for row in conn.execute("SELECT DISTINCT model_name FROM llm_cache").fetchall()}
    assert names == {"anchor::gguf::fake-1"}


def test_rules_backend_never_reads_or_writes_cache(conn: sqlite3.Connection) -> None:
    """Open Question 3: the zero-model backend is a pure function, never cached."""
    fake = FakeGenerator()
    resolver = AnchorResolver(conn, _settings(), generator=fake)

    resolution = resolver.resolve("machine learning")

    assert resolution.backend == "rules"
    assert resolution.terms == derive_rule_anchors("machine learning")
    assert fake.calls == 0
    assert _row_count(conn) == 0


def test_unconfigured_generator_falls_back_to_rule_anchors(
    conn: sqlite3.Connection,
) -> None:
    """D-14: no configured generator is a rule fallback, not an empty anchor set."""
    resolver = AnchorResolver(conn, _settings(anchor_backend="gguf"))

    resolution = resolver.resolve("machine learning")

    assert resolution.backend == "rules"
    assert resolution.fallback_reason == "unconfigured"
    assert resolution.terms == derive_rule_anchors("machine learning")
    assert _row_count(conn) == 0


def test_budget_exceeded_is_a_hard_failure(conn: sqlite3.Connection) -> None:
    """D-14: the per-instance budget raises instead of silently falling back."""
    fake = FakeGenerator()
    resolver = AnchorResolver(
        conn,
        _settings(anchor_backend="gguf", anchor_max_calls=1),
        generator=fake,
    )
    resolver.resolve("machine learning")

    with pytest.raises(AnchorBudgetExceeded) as excinfo:
        resolver.resolve("deep learning")

    assert isinstance(excinfo.value, RuntimeError)
    assert fake.calls == 1


def test_open_caller_transaction_is_never_committed(conn: sqlite3.Connection) -> None:
    """The resolver must not end a transaction its caller already owned."""
    conn.execute(
        "INSERT INTO llm_cache (id, model_name, prompt_hash, prompt, response, created_at)"
        " VALUES ('other', 'other', 'h', 'p', 'r', '2026-01-01T00:00:00+00:00')"
    )
    assert conn.in_transaction is True

    resolver = AnchorResolver(conn, _settings(anchor_backend="gguf"), generator=FakeGenerator())
    resolver.resolve("machine learning")

    assert conn.in_transaction is True
    conn.rollback()
    assert conn.in_transaction is False
    assert _row_count(conn) == 0
