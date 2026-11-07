"""Shared per-file incremental indexing core (roadmap SC3).

Extracted from ``update_cmd`` so every host (CLI update, MCP index tool, the
Phase 12-14 watch hosts) runs exactly one incremental loop. The indexer is
presentation-free: hosts pass a ``progress`` callback and render events
themselves; Rich/console output stays in the CLI.

This is the RED-phase skeleton: shapes only, no behavior yet.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sif.core.models import Collection
from sif.utils.logging import get_logger


if TYPE_CHECKING:
    from sif.search.vector import VectorSearcher


logger = get_logger(__name__)


@dataclass
class IncrementalResult:
    """Counts reported by one incremental update pass over a collection."""

    added: int = 0
    updated: int = 0
    removed: int = 0


class IncrementalIndexer:
    """Incremental indexer skeleton (RED)."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        """Initialize the indexer from a factory-created connection."""
        self._conn = conn
        self._vector_purger: VectorSearcher | None = None

    def update_collection(
        self,
        collection: Collection,
        *,
        force: bool = False,
        progress: Callable[[str], None] | None = None,
    ) -> IncrementalResult:
        """Update one collection (not implemented yet)."""
        return IncrementalResult(0, 0, 0)
