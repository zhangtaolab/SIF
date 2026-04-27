"""Database connection management."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import sqlite_vec


class DatabaseConnection:
    """Manages SQLite database connections.

    Provides connection pooling and ensures proper setup of
    required extensions (FTS5, sqlite-vec).
    """

    def __init__(self, db_path: Path | str) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection with extensions loaded."""
        conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row

        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")

        # Load sqlite-vec extension
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)

        return conn

    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a database connection as a context manager."""
        conn = self._create_connection()
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Execute operations within a transaction."""
        conn = self._create_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute(
        self,
        query: str,
        parameters: tuple | dict | None = None,
    ) -> sqlite3.Cursor:
        """Execute a query and return the cursor."""
        with self.connect() as conn:
            if parameters:
                cursor = conn.execute(query, parameters)
            else:
                cursor = conn.execute(query)
            conn.commit()
            return cursor

    def executemany(
        self,
        query: str,
        parameters: list[tuple | dict],
    ) -> sqlite3.Cursor:
        """Execute a query multiple times."""
        with self.connect() as conn:
            cursor = conn.executemany(query, parameters)
            conn.commit()
            return cursor

    def fetchone(
        self,
        query: str,
        parameters: tuple | dict | None = None,
    ) -> sqlite3.Row | None:
        """Fetch a single row."""
        with self.connect() as conn:
            cursor = conn.execute(query, parameters or ())
            return cursor.fetchone()

    def fetchall(
        self,
        query: str,
        parameters: tuple | dict | None = None,
    ) -> list[sqlite3.Row]:
        """Fetch all rows."""
        with self.connect() as conn:
            cursor = conn.execute(query, parameters or ())
            return cursor.fetchall()


class ConnectionPool:
    """Simple connection pool for database connections.

    Note: For SQLite, this is primarily useful for read-heavy workloads.
    Writes should use a single connection to avoid locking issues.
    """

    def __init__(
        self,
        db_path: Path | str,
        max_connections: int = 5,
    ) -> None:
        self._db_path = Path(db_path)
        self._max_connections = max_connections
        self._connections: list[sqlite3.Connection] = []

    def get_connection(self) -> sqlite3.Connection:
        """Get a connection from the pool or create a new one."""
        if self._connections:
            return self._connections.pop()

        conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def release_connection(self, conn: sqlite3.Connection) -> None:
        """Return a connection to the pool."""
        if len(self._connections) < self._max_connections:
            self._connections.append(conn)
        else:
            conn.close()

    def close_all(self) -> None:
        """Close all connections in the pool."""
        for conn in self._connections:
            conn.close()
        self._connections.clear()
