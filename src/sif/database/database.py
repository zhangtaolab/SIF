"""Database connection and management for SIF."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sif.database.factory import create_connection
from sif.database.schema import SchemaManager


class Database:
    """Main database class for SIF."""

    def __init__(self, db_path: str | Path) -> None:
        """Initialize the database connection wrapper."""
        self.db_path = Path(db_path).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: sqlite3.Connection | None = None
        self._schema: SchemaManager | None = None

    @property
    def connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._connection is None:
            self._connection = create_connection(self.db_path)
        return self._connection

    def init_schema(self) -> None:
        """Initialize database schema."""
        from sif.config.settings import get_settings  # noqa: PLC0415

        settings = get_settings()
        self._schema = SchemaManager(self.connection, embedding_dim=settings.embedding_dim)
        self._schema.create_all()

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Execute operations in a transaction."""
        conn = self.connection
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

    def __enter__(self) -> Database:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()

    def get_stats(self) -> dict:
        """Get database statistics."""
        if self._schema is None:
            from sif.config.settings import get_settings  # noqa: PLC0415

            settings = get_settings()
            self._schema = SchemaManager(self.connection, embedding_dim=settings.embedding_dim)
            self._schema.create_all()
        return self._schema.get_stats()

    def reset(self) -> None:
        """Reset database (drop all tables)."""
        if self._schema is None:
            from sif.config.settings import get_settings  # noqa: PLC0415

            settings = get_settings()
            self._schema = SchemaManager(self.connection, embedding_dim=settings.embedding_dim)
        self._schema.drop_all()
        self._schema.create_all()


class DatabaseConnection:
    """Lightweight database connection wrapper.

    .. deprecated::
        Duplicate of :class:`sif.database.connection.DatabaseConnection`;
        retired in plan 11-03 (D-07). Kept working — connections route
        through the shared factory — until then.
    """

    def __init__(self, db_path: str | Path) -> None:
        """Initialize the database connection wrapper."""
        self.db_path = Path(db_path).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Create a connection context."""
        conn = create_connection(self.db_path)

        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
