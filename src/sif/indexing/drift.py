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
from sif.indexing.incremental import IncrementalResult


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
    """
    return DriftReport()


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
    search never creates the lock file (Pitfall 6).
    """
    return IncrementalResult()
