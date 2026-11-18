"""Real-SQL tests for QueryLogRepository (Phase 15 QUAL-03).

Real in-memory SQLite from the production DDL (no mocks against SQL) — the
repository is the storage half of history suggestions: INSERT + trim-in-write
cap (D-09), one GROUP BY aggregate (D-13), and a single clear path (D-10).
Explicit ``created_at`` values drive deterministic trim/aggregate assertions.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from sif.core.models import QueryLogEntry
from sif.database.repositories import QueryLogRepository
from sif.database.schema import SchemaManager


@pytest.fixture
def db():
    """Real in-memory SQLite with the production query_log DDL."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    manager = SchemaManager(conn)
    manager._create_query_log_table()
    yield conn
    conn.close()


def _entry(
    query: str,
    result_count: int = 0,
    created_at: datetime | None = None,
) -> QueryLogEntry:
    return QueryLogEntry(
        query=query,
        result_count=result_count,
        collections=["notes"],
        created_at=created_at or datetime.now(timezone.utc),
    )


class TestSchemaRegistration:
    """create_all registers query_log + its index; drop_all removes them."""

    def test_create_all_registers_query_log_and_index(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        try:
            manager = SchemaManager(conn)
            manager.create_all()
            names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master")}
            assert "query_log" in names
            assert "idx_query_log_created" in names

            manager.drop_all()
            names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master")}
            assert "query_log" not in names
        finally:
            conn.close()


class TestAddPersistence:
    def test_add_persists_row_with_aware_utc_stamp(self, db):
        """add() stores the metadata columns; created_at round-trips as aware UTC."""
        repo = QueryLogRepository(db)
        entry = _entry("quantum notes", result_count=3)

        repo.add(entry, keep=500)

        row = db.execute(
            "SELECT query, result_count, collections, created_at FROM query_log"
        ).fetchone()
        assert row["query"] == "quantum notes"
        assert row["result_count"] == 3
        assert json.loads(row["collections"]) == ["notes"]
        assert datetime.fromisoformat(row["created_at"]).tzinfo is not None


class TestTrimInWrite:
    def test_inserting_beyond_keep_leaves_exactly_keep_oldest_gone(self, db):
        """D-09 trim boundary: keep+2 inserts leave keep rows, oldest removed."""
        repo = QueryLogRepository(db)
        base = datetime.now(timezone.utc) - timedelta(days=10)
        for index in range(5):
            repo.add(
                _entry(f"q{index}", created_at=base + timedelta(minutes=index)),
                keep=3,
            )
        db.commit()

        rows = db.execute("SELECT query FROM query_log ORDER BY created_at").fetchall()
        assert [row["query"] for row in rows] == ["q2", "q3", "q4"]


class TestHistoryAggregate:
    def test_history_aggregates_count_and_last_used_per_query(self, db):
        """D-13: one GROUP BY returns (query, count, last_used) per string."""
        repo = QueryLogRepository(db)
        first = datetime(2026, 1, 1, tzinfo=timezone.utc)
        latest = datetime(2026, 1, 3, tzinfo=timezone.utc)
        repo.add(_entry("quantum notes", created_at=first), keep=500)
        repo.add(_entry("quantum notes", created_at=latest), keep=500)
        repo.add(_entry("machine learning", created_at=latest), keep=500)
        db.commit()

        aggregate = {query: (count, last) for query, count, last in repo.history()}

        assert aggregate["quantum notes"][0] == 2
        assert datetime.fromisoformat(aggregate["quantum notes"][1]) == latest
        assert aggregate["machine learning"][0] == 1
        assert datetime.fromisoformat(aggregate["machine learning"][1]) == latest


class TestClear:
    def test_clear_deletes_all_rows_and_reports_count(self, db):
        """D-10: the single clear path empties the table and returns rowcount."""
        repo = QueryLogRepository(db)
        repo.add(_entry("a"), keep=500)
        repo.add(_entry("b"), keep=500)
        db.commit()

        assert repo.clear() == 2
        assert db.execute("SELECT COUNT(*) FROM query_log").fetchone()[0] == 0
        assert repo.clear() == 0
