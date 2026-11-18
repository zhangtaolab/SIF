"""Database connection and management for SIF."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from sif.database.factory import create_connection
from sif.database.schema import SchemaManager


if TYPE_CHECKING:
    from sif.embedding.identity import EmbedderIdentity


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

    def init_schema(
        self,
        embedding_dim: int | None = None,
        identity: EmbedderIdentity | None = None,
    ) -> None:
        """Initialize database schema.

        ``embedding_dim`` overrides the process setting so a host with
        injected settings (the MCP backend) can initialize the schema at its
        own dimension. When supplied, ``get_settings()`` is never consulted;
        the no-argument form keeps resolving the process environment.

        ``identity`` is the host's settings-only embedder identity (D-04).
        With neither argument the identity is built from the process
        settings; a supplied identity supplies the width when
        ``embedding_dim`` is omitted; an injected ``embedding_dim`` with no
        identity builds none, preserving the Phase 19 "injected caller never
        reads settings" contract. The identity lets the schema open run the
        init-mode width check and write the legacy-assumed row exactly once.
        """
        if embedding_dim is None and identity is None:
            from sif.config.settings import get_settings  # noqa: PLC0415
            from sif.embedding.identity import build_settings_identity  # noqa: PLC0415
            from sif.embedding.prompts import resolve_prompt_scheme  # noqa: PLC0415

            settings = get_settings()
            scheme = resolve_prompt_scheme(
                settings.model_name,
                settings.model_type,
                settings.query_prompt_name,
                settings.document_prompt_name,
            )
            identity = build_settings_identity(settings, scheme)
        if embedding_dim is None:
            assert identity is not None
            embedding_dim = identity.dimension
        self._schema = SchemaManager(
            self.connection,
            embedding_dim=embedding_dim,
            initial_identity=identity,
        )
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
