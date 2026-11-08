"""Pre-search drift detection and bounded BM25-only refresh (LIVE-10).

Presentation-free companion to :mod:`sif.indexing.incremental`, consumed by
the CLI search trio only (D-01: the check lives in the command layer so
``sif bench`` and the MCP server bypass it by construction).

- ``detect_drift`` stat-walks the requested collections via ``FileScanner``
  (the ONE membership predicate) and compares each file's ``st_mtime``
  against the ``documents`` table — read-only, lock-free, no writes when
  clean (D-02: stateless, every invocation; SC2).
- ``refresh_drifted`` wraps ``IncrementalIndexer.update_paths`` — the same
  per-path seam the watcher uses — inside ONE ``index_lock`` window
  (wait-then-run, 11-D02/12-D04). BM25-only by construction: the embedder
  is never invoked here (LIVE-05, 13-D02).
- Drift never becomes a search error: the caller (CLI) decides cap vs.
  refresh and surfaces outcomes as stderr notices/warnings (D-05, D-07).

Drift compare is **mtime-primary** (research correction to SC1's
"mtime/size"): ``documents.file_size`` is the frontmatter-stripped body
byte length and is never refreshed on update, so a size compare would
false-positive forever. The stat-based derivation intent is preserved —
content changes always move mtime — and the float compare is bit-exact
(``os.stat().st_mtime`` is a C double; SQLite REAL round-trips it exactly).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from sif.core.models import Collection
from sif.database.locking import index_lock
from sif.database.repositories import DocumentRepository
from sif.indexing.incremental import IncrementalIndexer, IncrementalResult
from sif.indexing.scanner import FileScanner
from sif.utils.logging import get_logger


logger = get_logger(__name__)


@dataclass
class DriftReport:
    """Drifted paths per collection id, as found by one stat walk.

    New files (on disk, not stored), mtime-mismatched files, and deleted
    files (stored, not seen on the walk) all count as drift — each is a
    candidate path for ``IncrementalIndexer.update_paths``, whose own stat
    pass decides the real outcome per path.
    """

    paths_by_collection: dict[str, set[Path]] = field(default_factory=dict)

    @property
    def total_count(self) -> int:
        """Total drifted paths across all collections (the cap decision input)."""
        return sum(len(paths) for paths in self.paths_by_collection.values())


def detect_drift(conn: sqlite3.Connection, collections: list[Collection]) -> DriftReport:
    """Stat-walk ``collections`` and report drifted paths per collection.

    Never writes and never touches the index lock (SC2: a clean search pays
    one read-only walk). A collection whose root is missing is skipped with
    a warning instead of reporting every stored document as deleted drift
    (the 12-D11 phantom-mass-delete guard, applied in the walk).

    Walk paths are resolved before comparing because stored ``documents``
    .path`` values are resolved — an unresolved compare mismatches on
    symlinked roots (macOS ``/tmp`` vs ``/private/tmp``).
    """
    if not collections:
        return DriftReport()

    report = DriftReport()
    doc_repo = DocumentRepository(conn)
    scanner = FileScanner()

    for collection in collections:
        root = Path(collection.path)
        # D-11 mirror: rglob on a missing root yields nothing, which the
        # deleted-file branch below would read as "every file vanished".
        if not root.exists():
            logger.warning(
                "Collection root %s does not exist; skipping drift walk (all documents preserved)",
                collection.path,
            )
            continue

        scan_result = scanner.scan(
            root,
            pattern=collection.pattern,
            ignore_patterns=collection.ignore_patterns,
        )
        stored = doc_repo.list_stat_by_collection(collection.id)
        seen: set[str] = set()

        for file_path in scan_result.files:
            try:
                mtime = file_path.stat().st_mtime
            except OSError:
                # Vanished between walk and stat: leave it unseen so the
                # deleted branch decides its fate from the stored side.
                continue
            key = str(file_path.resolve())
            seen.add(key)
            # Covers new files (path not stored → None != mtime) and
            # mtime-mismatched files in one bit-exact float compare.
            if stored.get(key) != mtime:
                report.paths_by_collection.setdefault(collection.id, set()).add(file_path)

        for key in stored:
            if key not in seen:
                report.paths_by_collection.setdefault(collection.id, set()).add(Path(key))

    return report


def refresh_drifted(
    db_path: Path,
    conn: sqlite3.Connection,
    collections_by_id: dict[str, Collection],
    report: DriftReport,
    lock_timeout: float,
) -> IncrementalResult:
    """BM25-refresh the drifted paths under one index lock window.

    The ONLY place the pre-search check acquires ``index_lock``; the caller
    invokes it solely when ``0 < report.total_count <= cap`` so a clean
    search never creates the lock file (Pitfall 6). One window covers all
    drifted collections; inside it, each collection's paths go through
    ``IncrementalIndexer.update_paths`` — never a second write path.
    """
    totals = IncrementalResult()
    if report.total_count == 0:
        return totals

    with index_lock(db_path, lock_timeout):
        indexer = IncrementalIndexer(conn)
        for coll_id in sorted(report.paths_by_collection):
            collection = collections_by_id.get(coll_id)
            if collection is None:
                logger.warning("Drift report names unknown collection %s; skipping", coll_id)
                continue
            result = indexer.update_paths(collection, report.paths_by_collection[coll_id])
            totals.added += result.added
            totals.updated += result.updated
            totals.removed += result.removed
            totals.unchanged += result.unchanged
            totals.failed += result.failed

    return totals
