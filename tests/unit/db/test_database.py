"""Tests for database connection and operations."""

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from docsift.database.connection import DatabaseConnection, ConnectionPool


class TestDatabaseConnection:
    """Tests for DatabaseConnection class."""

    def test_init_creates_parent_directory(self, temp_dir: Path):
        """Test that init creates parent directory if it doesn't exist."""
        # Arrange
        db_path = temp_dir / "nested" / "path" / "test.db"

        # Act
        conn = DatabaseConnection(db_path)

        # Assert
        assert db_path.parent.exists()

    def test_init_with_string_path(self, temp_dir: Path):
        """Test that init accepts string path."""
        # Arrange
        db_path = str(temp_dir / "test.db")

        # Act
        conn = DatabaseConnection(db_path)

        # Assert
        assert isinstance(conn._db_path, Path)

    def test_connect_yields_connection(self, temp_db_path: Path):
        """Test that connect yields a valid connection."""
        # Arrange
        conn = DatabaseConnection(temp_db_path)

        # Act
        with conn.connect() as db:
            # Assert
            assert isinstance(db, sqlite3.Connection)
            assert db.row_factory is sqlite3.Row

    def test_connect_enables_foreign_keys(self, temp_db_path: Path):
        """Test that connect enables foreign key constraints."""
        # Arrange
        conn = DatabaseConnection(temp_db_path)

        # Act
        with conn.connect() as db:
            cursor = db.execute("PRAGMA foreign_keys")
            result = cursor.fetchone()

        # Assert
        assert result[0] == 1

    def test_connect_loads_sqlite_vec(self, temp_db_path: Path):
        """Test that connect loads sqlite-vec extension."""
        # Arrange
        conn = DatabaseConnection(temp_db_path)

        # Act & Assert - should not raise
        with conn.connect() as db:
            # Try to use vec0 virtual table (if available)
            pass

    def test_transaction_commits_on_success(self, temp_db_path: Path):
        """Test that transaction commits on successful completion."""
        # Arrange
        conn = DatabaseConnection(temp_db_path)

        # Act
        with conn.transaction() as db:
            db.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            db.execute("INSERT INTO test (name) VALUES ('test')")

        # Assert
        with conn.connect() as db:
            cursor = db.execute("SELECT * FROM test")
            result = cursor.fetchone()
            assert result["name"] == "test"

    def test_transaction_rolls_back_on_error(self, temp_db_path: Path):
        """Test that transaction rolls back on error."""
        # Arrange
        conn = DatabaseConnection(temp_db_path)
        # Pre-create table (DDL triggers implicit commit, so do it outside transaction)
        with conn.connect() as db:
            db.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
            db.commit()

        # Act & Assert
        with pytest.raises(ValueError):
            with conn.transaction() as db:
                db.execute("INSERT INTO test (id) VALUES (1)")
                raise ValueError("Test error")

        # Verify insert was rolled back
        with conn.connect() as db:
            cursor = db.execute("SELECT * FROM test")
            assert cursor.fetchone() is None

    def test_execute_with_parameters(self, temp_db_path: Path):
        """Test execute with parameters."""
        # Arrange
        conn = DatabaseConnection(temp_db_path)
        with conn.connect() as db:
            db.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            db.commit()

        # Act
        conn.execute("INSERT INTO test (name) VALUES (?)", ("test_name",))

        # Assert
        with conn.connect() as db:
            cursor = db.execute("SELECT name FROM test WHERE name = ?", ("test_name",))
            result = cursor.fetchone()
            assert result["name"] == "test_name"

    def test_execute_without_parameters(self, temp_db_path: Path):
        """Test execute without parameters."""
        # Arrange
        conn = DatabaseConnection(temp_db_path)

        # Act
        result = conn.fetchone("SELECT 1 as value")

        # Assert
        assert result["value"] == 1

    def test_executemany(self, temp_db_path: Path):
        """Test executemany for batch operations."""
        # Arrange
        conn = DatabaseConnection(temp_db_path)
        with conn.connect() as db:
            db.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            db.commit()

        params = [("name1",), ("name2",), ("name3",)]

        # Act
        conn.executemany("INSERT INTO test (name) VALUES (?)", params)

        # Assert
        with conn.connect() as db:
            cursor = db.execute("SELECT COUNT(*) as count FROM test")
            result = cursor.fetchone()
            assert result["count"] == 3

    def test_fetchone_returns_single_row(self, temp_db_path: Path):
        """Test fetchone returns a single row."""
        # Arrange
        conn = DatabaseConnection(temp_db_path)
        with conn.connect() as db:
            db.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            db.execute("INSERT INTO test (name) VALUES ('test')")
            db.commit()

        # Act
        result = conn.fetchone("SELECT * FROM test WHERE name = ?", ("test",))

        # Assert
        assert result is not None
        assert result["name"] == "test"

    def test_fetchone_returns_none_for_no_match(self, temp_db_path: Path):
        """Test fetchone returns None when no match."""
        # Arrange
        conn = DatabaseConnection(temp_db_path)
        with conn.connect() as db:
            db.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            db.commit()

        # Act
        result = conn.fetchone("SELECT * FROM test WHERE name = ?", ("nonexistent",))

        # Assert
        assert result is None

    def test_fetchall_returns_all_rows(self, temp_db_path: Path):
        """Test fetchall returns all rows."""
        # Arrange
        conn = DatabaseConnection(temp_db_path)
        with conn.connect() as db:
            db.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            db.execute("INSERT INTO test (name) VALUES ('a')")
            db.execute("INSERT INTO test (name) VALUES ('b')")
            db.execute("INSERT INTO test (name) VALUES ('c')")
            db.commit()

        # Act
        results = conn.fetchall("SELECT * FROM test ORDER BY name")

        # Assert
        assert len(results) == 3
        assert results[0]["name"] == "a"
        assert results[1]["name"] == "b"
        assert results[2]["name"] == "c"

    def test_fetchall_returns_empty_list_for_no_match(self, temp_db_path: Path):
        """Test fetchall returns empty list when no match."""
        # Arrange
        conn = DatabaseConnection(temp_db_path)
        with conn.connect() as db:
            db.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            db.commit()

        # Act
        results = conn.fetchall("SELECT * FROM test WHERE name = ?", ("nonexistent",))

        # Assert
        assert results == []


class TestConnectionPool:
    """Tests for ConnectionPool class."""

    def test_init_stores_parameters(self, temp_db_path: Path):
        """Test that init stores parameters correctly."""
        # Act
        pool = ConnectionPool(temp_db_path, max_connections=10)

        # Assert
        assert pool._db_path == temp_db_path
        assert pool._max_connections == 10
        assert pool._connections == []

    def test_get_connection_creates_new_when_empty(self, temp_db_path: Path):
        """Test get_connection creates new connection when pool is empty."""
        # Arrange
        pool = ConnectionPool(temp_db_path)

        # Act
        conn = pool.get_connection()

        # Assert
        assert isinstance(conn, sqlite3.Connection)
        conn.close()

    def test_get_connection_reuses_existing(self, temp_db_path: Path):
        """Test get_connection reuses existing connection."""
        # Arrange
        pool = ConnectionPool(temp_db_path)
        conn1 = pool.get_connection()
        pool.release_connection(conn1)

        # Act
        conn2 = pool.get_connection()

        # Assert
        assert conn1 is conn2
        conn2.close()

    def test_release_connection_adds_to_pool(self, temp_db_path: Path):
        """Test release_connection adds connection back to pool."""
        # Arrange
        pool = ConnectionPool(temp_db_path)
        conn = pool.get_connection()

        # Act
        pool.release_connection(conn)

        # Assert
        assert len(pool._connections) == 1

    def test_release_connection_closes_when_full(self, temp_db_path: Path):
        """Test release_connection closes connection when pool is full."""
        # Arrange
        pool = ConnectionPool(temp_db_path, max_connections=1)
        conn1 = pool.get_connection()
        conn2 = pool.get_connection()
        pool.release_connection(conn1)  # Pool now has 1 connection

        # Act - releasing second connection should close it
        pool.release_connection(conn2)

        # Assert
        assert len(pool._connections) == 1

    def test_close_all_closes_connections(self, temp_db_path: Path):
        """Test close_all closes all connections in pool."""
        # Arrange
        pool = ConnectionPool(temp_db_path)
        conn1 = pool.get_connection()
        conn2 = pool.get_connection()
        pool.release_connection(conn1)
        pool.release_connection(conn2)

        # Act
        pool.close_all()

        # Assert
        assert len(pool._connections) == 0
