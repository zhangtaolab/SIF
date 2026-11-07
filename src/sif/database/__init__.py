"""Database access layer for SIF."""

from sif.database.connection import DatabaseConnection
from sif.database.factory import create_connection
from sif.database.locking import index_lock
from sif.database.migrations import MigrationManager
from sif.database.repositories import (
    CollectionRepository,
    DocumentChunkRepository,
    DocumentRepository,
    LLMCacheRepository,
    PathContextRepository,
)


__all__ = [
    "CollectionRepository",
    "DatabaseConnection",
    "DocumentChunkRepository",
    "DocumentRepository",
    "LLMCacheRepository",
    "MigrationManager",
    "PathContextRepository",
    "create_connection",
    "index_lock",
]
