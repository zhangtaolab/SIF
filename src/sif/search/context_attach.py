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

Per-process context-map cache (CORR-06, D-12): the scan result is cached for
the resolved main database path so two attachments on the same file database
issue exactly one ``SELECT ... FROM contexts``. Invalidation is conservative
and trigger-based — any ``ContextRepository`` write in this process (the
generation counter in ``sif.database.repositories``), any commit observed by
a dedicated sentinel connection's ``PRAGMA data_version`` (same-process or
another process), and an inode change (backup restore / file replacement).
The cache is keyed by the resolved path, never by a connection object:
``sqlite3.Connection`` is neither attribute-able nor weak-referenceable. A
``:memory:`` database bypasses the cache entirely (a second connection cannot
observe its writes), and a connection with an open transaction bypasses it
too — caching a snapshot read would freeze stale rows behind an unchanged
``data_version``. Every sentinel failure degrades to the verbatim scan; no
search fails because of the cache.
"""

from __future__ import annotations

import atexit
import os
import sqlite3
import threading
from dataclasses import dataclass

from sif.core.models import SearchResult
from sif.database.repositories import context_write_generation
from sif.search.staleness import mark_vector_staleness
from sif.utils.logging import get_logger
from sif.utils.paths import normalize_path


logger = get_logger(__name__)

# The verbatim scan (no path pre-filter — see the module docstring). Ordering
# by updated_at ascending makes dict later-row-wins pick the newest row when
# two rows normalize to the same key.
_CONTEXTS_SQL = (
    "SELECT target_id, content FROM contexts WHERE context_type = 'path' ORDER BY updated_at"
)


@dataclass(frozen=True)
class _ContextCacheEntry:
    """One cached normalized context map plus its invalidation-trigger samples.

    ``data_version``, ``generation``, and ``inode`` are all sampled *before*
    the map is built, so a concurrent commit or write can never be recorded
    as already-seen by the entry.
    """

    sentinel: sqlite3.Connection
    data_version: int
    generation: int
    inode: tuple[int, int]
    context_map: dict[str, str]


_context_cache: dict[str, _ContextCacheEntry] = {}
_cache_lock = threading.Lock()


def _file_inode(path: str) -> tuple[int, int] | None:
    """Return ``(st_dev, st_ino)`` for ``path``, or ``None`` when stat fails."""
    try:
        stat = os.stat(path)
    except OSError:
        return None
    return (stat.st_dev, stat.st_ino)


def _resolved_main_path(db: sqlite3.Connection) -> str | None:
    """Return the resolved main database file path, or ``None`` for ``:memory:``.

    ``PRAGMA database_list`` reports the empty string as the file for an
    in-memory database. Unreadable or unexpected row shapes also degrade to
    ``None`` (cache bypass), never an error.
    """
    try:
        rows = db.execute("PRAGMA database_list").fetchall()
    except sqlite3.Error:
        return None
    for row in rows:
        try:
            name = row[1]
            file = row[2]
        except (IndexError, KeyError, TypeError):
            continue
        if name == "main":
            return str(file) if file else None
    return None


def _build_context_map(db: sqlite3.Connection) -> dict[str, str]:
    """Run the verbatim contexts scan and normalize the stored targets."""
    cursor = db.execute(_CONTEXTS_SQL)
    return {normalize_path(row["target_id"]): row["content"] for row in cursor.fetchall()}


def _open_sentinel(path: str) -> sqlite3.Connection | None:
    """Open the cache's dedicated invalidation connection, or ``None``.

    The sentinel only ever reads ``PRAGMA data_version``: no sqlite-vec, no
    journal-mode switch, no writes. Opening a second connection to a database
    on a read-only or odd filesystem is allowed to fail — the caller then
    bypasses the cache with a fresh scan.
    """
    try:
        sentinel = sqlite3.connect(path, timeout=5.0, check_same_thread=False)
    except (sqlite3.Error, OSError) as exc:
        logger.debug("Context cache sentinel unavailable for %s: %s", path, exc)
        return None
    try:
        sentinel.execute("PRAGMA busy_timeout=5000")
    except sqlite3.Error as exc:
        logger.debug("Context cache sentinel setup failed for %s: %s", path, exc)
        _close_sentinel(sentinel)
        return None
    return sentinel


def _sample_data_version(sentinel: sqlite3.Connection) -> int | None:
    """Read the sentinel's ``PRAGMA data_version``, or ``None`` on any error."""
    try:
        row = sentinel.execute("PRAGMA data_version").fetchone()
        if row is None:
            return None
        return int(row[0])
    except (sqlite3.Error, IndexError, KeyError, TypeError, ValueError):
        return None


def _close_sentinel(sentinel: sqlite3.Connection) -> None:
    """Close a sentinel, tolerating an already-closed connection."""
    try:
        sentinel.close()
    except sqlite3.Error as exc:  # pragma: no cover - close() is idempotent
        logger.debug("Error closing context cache sentinel: %s", exc)


def _close_sentinels_locked() -> None:
    """Close every cached sentinel and clear the cache (lock must be held)."""
    for entry in _context_cache.values():
        _close_sentinel(entry.sentinel)
    _context_cache.clear()


def _drop_entry(path: str) -> None:
    """Close and remove the cached entry for ``path`` (lock must be held)."""
    entry = _context_cache.pop(path, None)
    if entry is not None:
        _close_sentinel(entry.sentinel)


def _close_sentinels() -> None:
    """Close every cached sentinel (``atexit`` hook)."""
    with _cache_lock:
        _close_sentinels_locked()


def reset_context_cache() -> None:
    """Close cached sentinels and clear the map; the write generation is kept.

    Public test hook, wired to the autouse ``reset_context_cache`` fixture in
    ``tests/conftest.py`` so no test inherits a sentinel or map from a
    previous test.
    """
    with _cache_lock:
        _close_sentinels_locked()


atexit.register(_close_sentinels)


def _lookup_cached(path: str, inode: tuple[int, int]) -> tuple[dict[str, str] | None, bool]:
    """Return ``(cached_map, sentinel_healthy)`` for the entry at ``path``.

    Caller must hold :data:`_cache_lock`. ``(None, True)`` is an ordinary miss
    (no entry, or a stale-but-healthy entry the caller may rebuild with the
    same sentinel). ``(None, False)`` means a sentinel operation failed: the
    broken entry is closed and dropped and the caller must bypass to a fresh
    scan without caching this call's result. An inode change also closes and
    drops the entry so the caller reopens the sentinel instead of reusing a
    handle to the replaced file.
    """
    entry = _context_cache.get(path)
    if entry is None:
        return None, True
    data_version = _sample_data_version(entry.sentinel)
    if data_version is None:
        _drop_entry(path)
        return None, False
    if inode != entry.inode:
        _drop_entry(path)
        return None, True
    if data_version != entry.data_version or context_write_generation() != entry.generation:
        return None, True
    return dict(entry.context_map), True


def _store_entry(
    db: sqlite3.Connection,
    path: str,
    inode: tuple[int, int],
) -> dict[str, str]:
    """Scan on ``db`` and cache the result, sampling every trigger first.

    Caller must hold :data:`_cache_lock`. The generation and the sentinel's
    ``data_version`` are sampled before the build so a write or commit that
    lands mid-build is detected by the next attachment. A missing or broken
    sentinel degrades to a fresh scan and caches nothing.
    """
    entry = _context_cache.get(path)
    sentinel = entry.sentinel if entry is not None else _open_sentinel(path)
    if sentinel is None:
        return _build_context_map(db)

    generation = context_write_generation()
    data_version = _sample_data_version(sentinel)
    if data_version is None:
        if entry is not None:
            _drop_entry(path)
        else:
            _close_sentinel(sentinel)
        return _build_context_map(db)

    context_map = _build_context_map(db)
    _context_cache[path] = _ContextCacheEntry(
        sentinel=sentinel,
        data_version=data_version,
        generation=generation,
        inode=inode,
        context_map=context_map,
    )
    return dict(context_map)


def get_context_map(db: sqlite3.Connection) -> dict[str, str]:
    """Return ``{normalize_path(target_id): content}`` for path-type contexts.

    The map is cached per process per resolved main database path with three
    invalidation triggers (repository write generation, sentinel
    ``PRAGMA data_version``, inode change). ``:memory:`` databases and
    connections with an open transaction bypass the cache and re-query every
    time. The returned dict is a copy, so callers cannot mutate the cache.
    """
    if db.in_transaction:
        # A map built from an open transaction is a snapshot: caching it
        # would freeze stale rows behind an unchanged data_version (and could
        # cache uncommitted rows that later roll back).
        return _build_context_map(db)

    path = _resolved_main_path(db)
    if path is None:
        # ``:memory:`` (or unreadable database_list): no second connection
        # can observe this database's writes, so always scan.
        return _build_context_map(db)

    with _cache_lock:
        inode = _file_inode(path)
        if inode is None:
            return _build_context_map(db)
        cached, sentinel_healthy = _lookup_cached(path, inode)
        if cached is not None:
            return cached
        if not sentinel_healthy:
            return _build_context_map(db)
        return _store_entry(db, path, inode)


def attach_path_contexts(
    db: sqlite3.Connection,
    results: list[SearchResult],
) -> list[SearchResult]:
    """Attach path-context descriptions to search results.

    Matches results to the cached (or freshly built) normalized context map by
    normalizing both sides with :func:`normalize_path`. Existing verbatim
    context rows (stored before normalization existed) match on read — no
    backfill migration is needed. A result's ``context_description`` is set
    ONLY when a match is found, so descriptions already carried by the result
    (e.g. through RRF fusion or reranking) are never clobbered.

    Args:
        db: SQLite connection (rows must support ``row["target_id"]`` /
            ``row["content"]`` access, i.e. sqlite3.Row or dict rows).
        results: Search results to enrich.

    Returns:
        The same results list, with ``context_description`` filled on matches.
    """
    if not results:
        return results

    context_map = get_context_map(db)

    for result in results:
        key = normalize_path(result.path)
        if key in context_map:
            result.context_description = context_map[key]
    return results


def enrich_results(
    db: sqlite3.Connection,
    results: list[SearchResult],
    *,
    vectors_untrusted: bool = False,
) -> list[SearchResult]:
    """Apply both search-result trust signals exactly once.

    The single enrichment owner for every public search exit: path-context
    attachment followed by derived vector-staleness marking. Searchers return
    raw results; this composition runs once at the search pipeline's exit and
    once at each direct CLI/MCP entry point.

    Args:
        db: SQLite connection.
        results: Search results to enrich.
        vectors_untrusted: When true, every result is additionally marked
            ``vectors_stale`` after the normal staleness pass (the identity
            warning path consumes this; existing two-argument callers are
            untouched).

    Returns:
        The same results list, with ``context_description`` filled on matches
        and ``vectors_stale`` marked from the derived embedding scan.
    """
    enriched = mark_vector_staleness(db, attach_path_contexts(db, results))
    if vectors_untrusted:
        for result in enriched:
            result.vectors_stale = True
    return enriched
