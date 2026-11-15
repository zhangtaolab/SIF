"""Index maintenance helpers (CORR-06, D-10).

These helpers may scan: they run only from explicit maintenance paths
(``sif cleanup``, ``sif index vacuum``) inside the caller's transaction, never
from the search path. The search path reads the derived shadow through
display-gate probes plus indexed primary-key lookups and must never
reintroduce a full ``document_embeddings`` scan.
"""

from __future__ import annotations

import sqlite3


_SHADOW_EXISTS_SQL = "SELECT 1 FROM sqlite_master WHERE type='table' AND name='embedded_documents'"
_SHADOW_DELETE_STALE_SQL = (
    "DELETE FROM embedded_documents "
    "WHERE document_id NOT IN (SELECT id FROM documents) "
    "   OR document_id NOT IN (SELECT document_id FROM document_embeddings)"
)
_SHADOW_INSERT_MISSING_SQL = (
    "INSERT OR IGNORE INTO embedded_documents(document_id) "
    "SELECT DISTINCT de.document_id FROM document_embeddings de "
    "JOIN documents d ON d.id = de.document_id"
)


def reconcile_embedded_documents(conn: sqlite3.Connection) -> tuple[int, int]:
    """Reconcile the derived ``embedded_documents`` shadow with its sources.

    Deletes shadow rows whose document or embeddings are gone, then inserts
    missing rows for documents that still exist and still have embeddings
    (the join means a deleted document is never resurrected). Returns
    ``(deleted, inserted)``.

    No commit: the caller owns the transaction, so a cleanup/vacuum failure
    rolls the reconciliation back with the rest of the maintenance work. Both
    statements scan by design — maintenance paths may; the search path must
    not (CORR-06).
    """
    row = conn.execute(_SHADOW_EXISTS_SQL).fetchone()
    if row is None:
        return 0, 0

    deleted = conn.execute(_SHADOW_DELETE_STALE_SQL).rowcount
    inserted = conn.execute(_SHADOW_INSERT_MISSING_SQL).rowcount
    return deleted, inserted
