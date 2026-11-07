"""Database connection management."""

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sif.database.factory import create_connection


class DatabaseConnection:
    """Manages SQLite database connections.

    Provides connection pooling and ensures proper setup of
    required extensions (FTS5, sqlite-vec).
    """

    def __init__(self, db_path: Path | str) -> None:
        """Initialize the database connection."""
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection with extensions loaded."""
        return create_connection(self._db_path)

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
        parameters: tuple[Any, ...] | dict[str, Any] | None = None,
    ) -> sqlite3.Cursor:
        """Execute a query and return the cursor."""
        with self.connect() as conn:
            cursor = conn.execute(query, parameters) if parameters else conn.execute(query)
            conn.commit()
            return cursor

    def executemany(
        self,
        query: str,
        parameters: list[tuple[Any, ...] | dict[str, Any]],
    ) -> sqlite3.Cursor:
        """Execute a query multiple times."""
        with self.connect() as conn:
            cursor = conn.executemany(query, parameters)
            conn.commit()
            return cursor

    def fetchone(
        self,
        query: str,
        parameters: tuple[Any, ...] | dict[str, Any] | None = None,
    ) -> sqlite3.Row | None:
        """Fetch a single row."""
        with self.connect() as conn:
            cursor = conn.execute(query, parameters or ())
            row: sqlite3.Row | None = cursor.fetchone()
            return row

    def fetchall(
        self,
        query: str,
        parameters: tuple[Any, ...] | dict[str, Any] | None = None,
    ) -> list[sqlite3.Row]:
        """Fetch all rows."""
        with self.connect() as conn:
            cursor = conn.execute(query, parameters or ())
            return cursor.fetchall()
