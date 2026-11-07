"""Shared per-file incremental indexing core (roadmap SC3).

Extracted from ``update_cmd`` so every host (CLI update, the MCP index tool,
the Phase 12-14 watch hosts) runs exactly one incremental loop. Each file's
document + chunk-purge + FTS-trigger writes commit as one short BEGIN
IMMEDIATE transaction (D-04): a mid-run failure keeps completed files durable
(resumable) instead of rolling back the whole run, and short lock holds let
searches and other writers interleave (LIVE-06).

The core is presentation-free: hosts pass a ``progress`` callback and render
events themselves — Rich/console output stays in the CLI (Pattern 5). The
loop is BM25-only; embedding work stays in ``embed_cmd`` (Phase 03 lock).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from sif.core.models import Collection, Document
from sif.database.repositories import (
    CollectionRepository,
    DocumentChunkRepository,
    DocumentRepository,
)
from sif.indexing.parser import MarkdownParser
from sif.indexing.scanner import FileScanner
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


def _embedding_purger(conn: sqlite3.Connection) -> VectorSearcher | None:
    """Return a VectorSearcher for purging embeddings, or None without sqlite-vec.

    A missing sqlite-vec extension also means no vec0 table — hence no stored
    embeddings — so callers treat None as "nothing to purge".
    """
    from sif.search.vector import VectorSearcher  # noqa: PLC0415

    try:
        return VectorSearcher(conn)
    except RuntimeError:
        return None


class IncrementalIndexer:
    """The single shared incremental update loop (roadmap SC3).

    Processing order is FileScanner's existing scan order, so final index
    content is deterministic and identical to the pre-extraction CLI loop.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        """Initialize the indexer from a factory-created connection.

        Args:
            conn: Connection whose implicit write transactions are BEGIN
                IMMEDIATE (the Plan 01 factory recipe); per-file ``with conn:``
                blocks are the per-file commits.
        """
        self._conn = conn
        self._coll_repo = CollectionRepository(conn)
        self._doc_repo = DocumentRepository(conn)
        self._chunk_repo = DocumentChunkRepository(conn)
        self._parser = MarkdownParser()
        self._vector_purger = _embedding_purger(conn)

    def update_collection(
        self,
        collection: Collection,
        *,
        force: bool = False,
        progress: Callable[[str], None] | None = None,
    ) -> IncrementalResult:
        """Incrementally update one collection from its directory tree.

        Args:
            collection: The collection to scan and update.
            force: Re-index files whose stored checksum already matches.
            progress: Optional presentation callback. Invoked with short
                ``"code payload"`` events (single-space separator) so hosts
                render without the core importing any UI library:
                ``"scan <n>"`` (scan finished with n files),
                ``"unchanged <name>"`` (checksum-skip fired),
                ``"error <message>"`` (per-file parse failure, file skipped),
                ``"indexed <name>"`` (file added or updated).

        Returns:
            Counts of added, updated, and removed documents.
        """
        scanner = FileScanner()
        scan_result = scanner.scan(
            Path(collection.path),
            pattern=collection.pattern,
            ignore_patterns=collection.ignore_patterns,
        )
        self._notify(progress, f"scan {scan_result.file_count}")

        # Snapshot existing documents once per collection: with per-file
        # commits a concurrent short CRUD writer could in principle make this
        # stale mid-collection, but flock arbitration means only one index
        # writer at a time, so this exposure is no worse than pre-extraction.
        existing_docs = {d.path: d for d in self._doc_repo.list_by_collection(collection.id)}
        scanned_paths: set[str] = set()

        added = 0
        updated = 0

        for file_path in scan_result.files:
            scanned_paths.add(str(file_path))
            outcome = self._process_file(
                file_path,
                collection=collection,
                existing=existing_docs.get(str(file_path)),
                force=force,
                progress=progress,
            )
            if outcome == "added":
                added += 1
            elif outcome == "updated":
                updated += 1

        removed = self._sweep_removed(existing_docs, scanned_paths)

        # Update collection stats — its own short transaction.
        with self._conn:
            collection.document_count = len(self._doc_repo.list_by_collection(collection.id))
            collection.last_indexed_at = datetime.now(timezone.utc)
            self._coll_repo.update(collection)

        return IncrementalResult(added=added, updated=updated, removed=removed)

    @staticmethod
    def _notify(progress: Callable[[str], None] | None, event: str) -> None:
        """Forward an event to the presentation callback, if any."""
        if progress is not None:
            progress(event)

    def _process_file(
        self,
        file_path: Path,
        *,
        collection: Collection,
        existing: Document | None,
        force: bool,
        progress: Callable[[str], None] | None,
    ) -> str:
        """Process one scanned file; returns "added", "updated", or "skipped"."""
        # Parse document
        try:
            parsed = self._parser.parse(file_path)
        except Exception as e:
            self._notify(progress, f"error Error parsing {file_path}: {e}")
            return "skipped"

        if existing:
            # Check if changed
            if existing.checksum == parsed.checksum and not force:
                self._notify(progress, f"unchanged {file_path.name}")
                return "skipped"

            # One short BEGIN IMMEDIATE transaction per file (D-04) so this
            # file's writes commit atomically and earlier files stay durable
            # when a later one fails.
            with self._conn:
                # Content changed (or --force): drop stale chunks and
                # embeddings so the next `embed` run re-chunks the new
                # content instead of trusting the chunk-id-set
                # completeness check against stale rows (CR-01).
                self._chunk_repo.delete_by_document(existing.id)
                if self._vector_purger is not None:
                    self._vector_purger.delete_embeddings_by_document(existing.id)

                # Update document
                existing.content = parsed.content
                existing.title = parsed.title
                existing.metadata = parsed.metadata
                existing.mtime = parsed.mtime
                # Persist the fresh checksum, or the next update run compares
                # the new content against the pre-edit hash and rewrites this
                # document again every run.
                existing.checksum = parsed.checksum
                self._doc_repo.update(existing)
            outcome = "updated"
        else:
            # Create new document
            doc = Document(
                path=str(file_path),
                collection_id=collection.id,
                content=parsed.content,
                title=parsed.title,
                metadata=parsed.metadata,
                mtime=parsed.mtime,
            )
            with self._conn:
                self._doc_repo.create(doc)
            outcome = "added"

        self._notify(progress, f"indexed {file_path.name}")
        return outcome

    def _sweep_removed(
        self,
        existing_docs: dict[str, Document],
        scanned_paths: set[str],
    ) -> int:
        """Remove stored documents whose files vanished; one short transaction."""
        removed = 0
        with self._conn:
            for path, doc in existing_docs.items():
                if path not in scanned_paths:
                    # Purge embeddings before the document row (WR-01): vec0
                    # rows cannot carry the FK cascade, so orphaned vectors
                    # would otherwise occupy KNN top-k slots and crowd live
                    # documents out of vector search results.
                    if self._vector_purger is not None:
                        self._vector_purger.delete_embeddings_by_document(doc.id)
                    self._doc_repo.delete(doc.id)
                    removed += 1
        return removed
