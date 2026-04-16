"""Database connection and management for DocSift."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from docsift.database.schema import SchemaManager


class Database:
    """Main database class for DocSift."""
    
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: Optional[sqlite3.Connection] = None
        self._schema: Optional[SchemaManager] = None
    
    @property
    def connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._connection is None:
            self._connection = sqlite3.connect(
                str(self.db_path),
                detect_types=sqlite3.PARSE_DECLTYPES,
                check_same_thread=False,
            )
            self._connection.row_factory = sqlite3.Row
            self._enable_extensions()
        return self._connection
    
    def _enable_extensions(self) -> None:
        """Enable SQLite extensions."""
        # Enable FTS5
        self._connection.execute("PRAGMA foreign_keys = ON")
        
        # Try to load sqlite-vec extension
        try:
            self._connection.enable_load_extension(True)
            # Try common paths for sqlite-vec
            vec_paths = [
                "vec0",
                "libvec0",
                "/usr/lib/sqlite3/vec0",
                "/usr/local/lib/sqlite3/vec0",
            ]
            for path in vec_paths:
                try:
                    self._connection.load_extension(path)
                    break
                except sqlite3.OperationalError:
                    continue
        except Exception:
            pass  # sqlite-vec is optional
    
    def init_schema(self) -> None:
        """Initialize database schema."""
        from docsift.config.settings import get_settings
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
            from docsift.config.settings import get_settings
            settings = get_settings()
            self._schema = SchemaManager(self.connection, embedding_dim=settings.embedding_dim)
        return self._schema.get_stats()

    def reset(self) -> None:
        """Reset database (drop all tables)."""
        if self._schema is None:
            from docsift.config.settings import get_settings
            settings = get_settings()
            self._schema = SchemaManager(self.connection, embedding_dim=settings.embedding_dim)
        self._schema.drop_all()
        self._schema.create_all()


class DatabaseConnection:
    """Lightweight database connection wrapper."""
    
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Create a connection context."""
        conn = sqlite3.connect(
            str(self.db_path),
            detect_types=sqlite3.PARSE_DECLTYPES,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        
        # Try to enable extensions
        try:
            conn.enable_load_extension(True)
            try:
                conn.load_extension("vec0")
            except sqlite3.OperationalError:
                pass
        except Exception:
            pass
        
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
