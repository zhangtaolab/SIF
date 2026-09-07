"""Shared path-context attachment for search results.

05-VERIFICATION.md gap 1 root cause: ``contexts.target_id`` stores the
verbatim user-typed path while ``documents.path`` stores the resolved path
(indexing uses ``Path(file_path).resolve()``). The previous implementations
pre-filtered with a SQL membership clause on the raw ``target_id`` strings
built from the result paths, which returned ZERO rows for mismatched forms
(macOS ``/tmp/...`` vs ``/private/tmp/...``) and made the Python-side
realpath normalization dead code — realpath is not invertible, so no
exact-match pre-filter on resolved strings can ever match a verbatim legacy
row. The fix is this single shared helper: one batch query of all path-type
contexts (constant SQL, no interpolated values) with normalization of both
sides in Python (D-06 preserved: Python-layer batch, no SQL JOIN, no N+1).
"""

from __future__ import annotations

import sqlite3

from sif.core.models import SearchResult
from sif.utils.paths import normalize_path


def attach_path_contexts(
    db: sqlite3.Connection,
    results: list[SearchResult],
) -> list[SearchResult]:
    """Attach path-context descriptions to search results.

    Executes one query for all path-type contexts and matches them to result
    paths by normalizing both sides with :func:`normalize_path`. Existing
    verbatim context rows (stored before normalization existed) match on read
    — no backfill migration is needed. A result's ``context_description`` is
    set ONLY when a match is found, so descriptions already carried by the
    result (e.g. through RRF fusion or reranking) are never clobbered.

    Args:
        db: SQLite connection (rows must support ``row["target_id"]`` /
            ``row["content"]`` access, i.e. sqlite3.Row or dict rows).
        results: Search results to enrich.

    Returns:
        The same results list, with ``context_description`` filled on matches.
    """
    if not results:
        return results

    # Ordered by updated_at ascending so that when two rows normalize to the
    # same key the newest updated_at deterministically wins (dict
    # later-row-wins semantics). The query is a constant string with zero
    # interpolated values — deliberately no path pre-filter (see module
    # docstring).
    cursor = db.execute(
        "SELECT target_id, content FROM contexts WHERE context_type = 'path' ORDER BY updated_at"
    )
    context_map = {normalize_path(row["target_id"]): row["content"] for row in cursor.fetchall()}

    for result in results:
        key = normalize_path(result.path)
        if key in context_map:
            result.context_description = context_map[key]
    return results
