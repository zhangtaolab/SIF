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
from collections.abc import Callable, Iterable
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
    unchanged: int = 0


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
        # D-11: a missing collection root must never be read as mass
        # deletion — rglob on a missing root yields no files, which the
        # sweep below would otherwise treat as "every file vanished".
        if not Path(collection.path).exists():
            logger.warning(
                "Collection root %s does not exist; skipping update (all documents preserved)",
                collection.path,
            )
            self._notify(progress, f"missing {collection.name}")
            return IncrementalResult()

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

    def update_paths(
        self,
        collection: Collection,
        paths: Iterable[Path],
        *,
        force: bool = False,
        progress: Callable[[str], None] | None = None,
    ) -> IncrementalResult:
        """Targeted update: for each path, stat it — exists+changed → re-index, gone → remove.

        Cost is proportional to ``len(paths)``; the collection tree is never
        scanned (D-06). A path may arrive from both sides of a folded event
        burst; it is processed once and disk state decides the outcome.
        Unchanged paths (checksum skip) count as ``unchanged``. A stored
        document whose path now fails the shared scan predicate (e.g. a
        later ignore-pattern setting) is removed, mirroring the
        ``update_collection`` sweep so every writer agrees on removal
        semantics; never-indexed paths stay harmless no-ops. A missing
        collection root warns and returns zero counts without touching any
        document (D-11).

        Args:
            collection: The collection the paths belong to.
            paths: Candidate paths (index hints and remove hints unioned).
            force: Re-index files whose stored checksum already matches.
            progress: Optional presentation callback; same event protocol as
                :meth:`update_collection` plus ``"missing <name>"``.

        Returns:
            Counts of added, updated, removed, and unchanged documents.
        """
        # D-11: same missing-root guard as update_collection — a burst of
        # delete-shaped events from a vanished root must not remove anything.
        if not Path(collection.path).exists():
            logger.warning(
                "Collection root %s does not exist; skipping update (all documents preserved)",
                collection.path,
            )
            self._notify(progress, f"missing {collection.name}")
            return IncrementalResult()

        scanner = FileScanner()
        root = Path(collection.path)
        resolved: set[Path] = {Path(p).resolve() for p in paths}
        added = 0
        updated = 0
        removed = 0
        unchanged = 0

        for path in sorted(resolved):
            if not scanner.matches(
                root,
                path,
                pattern=collection.pattern,
                ignore_patterns=collection.ignore_patterns,
            ):
                # Never-indexable paths with no stored document (temp
                # noise, fold remove-hints for never-indexed paths) are
                # harmless no-ops. A STORED document the shared predicate
                # now excludes (e.g. a later SIF_WATCH_IGNORE_PATTERNS
                # entry) is removed — mirroring _sweep_removed / `sif index
                # update` — so drift refreshes converge instead of
                # re-detecting the path as deleted drift forever (WR-01).
                excluded = self._doc_repo.get_by_path(str(path), collection.id)
                if excluded is not None:
                    self._remove_document(excluded)
                    removed += 1
                continue
            existing = self._doc_repo.get_by_path(str(path), collection.id)
            if path.exists():
                outcome = self._process_file(
                    path,
                    collection=collection,
                    existing=existing,
                    force=force,
                    progress=progress,
                )
                if outcome == "added":
                    added += 1
                elif outcome == "updated":
                    updated += 1
                else:
                    # Checksum skip (or a parse failure already reported via
                    # an "error" event): nothing to write for this path.
                    unchanged += 1
            elif existing is not None:
                self._remove_document(existing)
                removed += 1

        # Update collection stats — its own short transaction, mirroring
        # update_collection's tail.
        with self._conn:
            collection.document_count = len(self._doc_repo.list_by_collection(collection.id))
            collection.last_indexed_at = datetime.now(timezone.utc)
            self._coll_repo.update(collection)

        return IncrementalResult(added=added, updated=updated, removed=removed, unchanged=unchanged)

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
                # Drift-compare convergence (14 REVIEW CR-01): detect_drift
                # is mtime-primary, so the skip must still persist a moved
                # mtime — a touched-but-unchanged file (git checkout of
                # identical content, archive extract, no-op save) would
                # otherwise be re-detected as drift on every subsequent
                # search forever. Only the mtime column: the checksum covers
                # the body alone, so a whole-row update could smuggle a new
                # frontmatter title/metadata through this skip.
                if existing.mtime != parsed.mtime:
                    with self._conn:
                        self._conn.execute(
                            "UPDATE documents SET mtime = ? WHERE id = ?",
                            (parsed.mtime, existing.id),
                        )
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
        """Remove stored documents whose files vanished."""
        removed = 0
        for path, doc in existing_docs.items():
            if path not in scanned_paths:
                self._remove_document(doc)
                removed += 1
        return removed

    def _remove_document(self, doc: Document) -> None:
        """Remove one document; vector purge BEFORE the row delete (WR-01).

        Both the collection sweep and the per-path update path share this
        body: vec0 rows cannot carry the FK cascade, so orphaned vectors
        would otherwise occupy KNN top-k slots and crowd live documents out
        of vector search results. One short BEGIN IMMEDIATE transaction.
        """
        with self._conn:
            if self._vector_purger is not None:
                self._vector_purger.delete_embeddings_by_document(doc.id)
            self._doc_repo.delete(doc.id)
