"""Derived vector-staleness marking for search results (QUAL-06).

D-08 (corrected formula, RESEARCH Pitfall 3): a result is vector-stale when
its document has NO rows in ``document_embeddings`` — not "has chunks but no
embeddings". BM25-only updates purge chunks AND embeddings together
(Phase 12 D-10), so the real tiered-depth lag state is embeddings-free; the
signal is derived at query time and never persisted (a maintained flag is the
silent-lie bug class Phase 10.1 hunted — 4+ write paths must keep it
truthful).

D-09: invoked from every searcher's ``_attach_contexts`` (one code path), so
BM25/vector/hybrid exits — and therefore the CLI search trio, MCP, and
(benignly, read-only) bench — mark consistently.

Display gate (14-02 objective): markers activate ONLY when the index has at
least one embedding. Pure-BM25 users who never opted into vectors see no
markers and no embed nagging; the moment embeddings exist, every lagging
document is marked.

Batching rule (the vector.py ``get_all_embedded_chunk_ids`` precedent): the
vec0 virtual table has no index on its metadata columns, so each per-document
filtered lookup costs a full table scan — staleness must be judged from ONE
constant scan of ``document_embeddings``, iterated one row at a time (never
fetchall), never per-result queries.
"""

from __future__ import annotations

import sqlite3

from sif.core.models import SearchResult


def embedded_document_ids(db: sqlite3.Connection) -> set[str] | None:
    """Return the ids of documents having rows in ``document_embeddings``.

    One constant scan, iterated one row at a time (the vec0 memory rule —
    never fetchall). Returns ``None`` when the vec0 table is missing
    (sqlite-vec absent — schema creation is conditional): callers treat that
    as "no markers", never an error (degrade-never-crash).
    """
    embedded: set[str] = set()
    try:
        cursor = db.execute("SELECT document_id FROM document_embeddings")
        for row in cursor:
            embedded.add(row[0])
    except sqlite3.OperationalError:
        return None
    return embedded


def mark_vector_staleness(
    db: sqlite3.Connection,
    results: list[SearchResult],
) -> list[SearchResult]:
    """Mark each result's ``vectors_stale`` from the derived embedding scan.

    Early-returns on an empty result list without touching the DB. When the
    index has no embeddings at all (empty set — the display gate) or the vec0
    table is missing (``None`` — degradation), results return unmarked;
    otherwise each result is marked ``vectors_stale = document_id not in``
    the embedded set, in place. Idempotent: the flag is recomputed from the
    same scan, so re-marking yields identical values and mutates nothing
    else. Never a per-result query — one batched scan per result set (the
    vec0 batching rule; per-document filtered lookups cost full scans).
    """
    if not results:
        return results
    embedded = embedded_document_ids(db)
    if not embedded:
        # None → vec0 missing (degrade); set() → display gate: the index has
        # no embeddings at all, so nothing lags — pure-BM25 users see no
        # markers and no embed nagging. Either way, unmarked.
        return results
    for result in results:
        result.vectors_stale = result.document_id not in embedded
    return results
