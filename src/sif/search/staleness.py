"""Derived vector-staleness marking for search results (QUAL-06, D-08/D-11).

D-08 (corrected formula, RESEARCH Pitfall 3): a result is vector-stale when
its document has NO rows in ``document_embeddings`` — not "has chunks but no
embeddings". BM25-only updates purge chunks AND embeddings together
(Phase 12 D-10), so the real tiered-depth lag state is embeddings-free; the
signal is derived at query time and never persisted (a maintained flag is the
silent-lie bug class Phase 10.1 hunted — 4+ write paths must keep it
truthful).

D-09: invoked through the single ``enrich_results`` composition in
``sif.search.context_attach`` (the only code path), which every search entry
point calls exactly once at its exit — the search pipeline's BM25, vector,
HyDE, and hybrid routes (and therefore CLI ``query`` and MCP ``query``, plus
the read-only bench), and the direct CLI ``search``/``vsearch`` and MCP BM25
fallback entry points. Searchers themselves return raw, unenriched results.

Display gate (14-02 objective): markers activate ONLY when the index has at
least one embedding. Pure-BM25 users who never opted into vectors see no
markers and no embed nagging; the moment embeddings exist, every lagging
document is marked.

Bounded read (CORR-06, D-11): the signal is read from the derived
``embedded_documents`` shadow, which the vector writer maintains in the same
transaction as every embedding write/delete. ``embedded_document_ids`` stays
the set form (bounded by document count) for status/compat, while
``mark_vector_staleness`` runs one display-gate probe followed by indexed
primary-key lookups — O(results · log N), never a full ``document_embeddings``
scan. The old batching rule still applies to vec0's unindexed metadata
columns; the shadow's primary key is an ordinary index, so per-result probes
are the correct shape here. The only remaining full ``document_embeddings``
scan is ``VectorSearcher.get_all_embedded_chunk_ids`` (the resume path).
"""

from __future__ import annotations

import sqlite3

from sif.core.models import SearchResult


# Constant query strings: the shadow is a regular table with an ordinary
# primary-key index, so per-result probes are indexed point lookups.
_DISPLAY_GATE_SQL = "SELECT 1 FROM embedded_documents LIMIT 1"
_DOCUMENT_EMBEDDED_SQL = "SELECT 1 FROM embedded_documents WHERE document_id = ?"


def embedded_document_ids(db: sqlite3.Connection) -> set[str] | None:
    """Return the ids of documents having at least one stored embedding.

    Reads the derived ``embedded_documents`` shadow (one row per embedded
    document), iterated one row at a time (never fetchall). Returns ``None``
    when the shadow table is missing (sqlite-vec absent — schema creation is
    conditional): callers treat that as "no markers", never an error
    (degrade-never-crash).
    """
    embedded: set[str] = set()
    try:
        cursor = db.execute("SELECT document_id FROM embedded_documents")
        for row in cursor:
            embedded.add(row[0])
    except sqlite3.OperationalError:
        return None
    return embedded


def mark_vector_staleness(
    db: sqlite3.Connection,
    results: list[SearchResult],
) -> list[SearchResult]:
    """Mark each result's ``vectors_stale`` from the derived shadow.

    Early-returns on an empty result list without touching the DB. One
    display-gate probe detects an index with no embeddings at all (empty
    shadow — no markers for pure-BM25 users) and a missing shadow/vec0 table
    (``sqlite3.OperationalError`` — degradation); either way results return
    unmarked. Otherwise each result is marked ``vectors_stale`` by one
    indexed primary-key lookup on ``embedded_documents``, in place.
    Idempotent: the flag is recomputed from the same shadow, so re-marking
    yields identical values and mutates nothing else. Never a full
    ``document_embeddings`` scan — the shadow is the search-path read
    contract (CORR-06).
    """
    if not results:
        return results
    try:
        any_embedded = db.execute(_DISPLAY_GATE_SQL).fetchone()
    except sqlite3.OperationalError:
        # None → shadow (and hence vec0) missing: degrade, unmarked.
        return results
    if any_embedded is None:
        # Display gate: the index has no embeddings at all, so nothing lags —
        # pure-BM25 users see no markers and no embed nagging.
        return results
    for result in results:
        row = db.execute(_DOCUMENT_EMBEDDED_SQL, (result.document_id,)).fetchone()
        result.vectors_stale = row is None
    return results
