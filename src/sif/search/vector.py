"""Vector similarity search implementation."""

from __future__ import annotations

import json
import sqlite3

from sif.core.models import SearchOptions, SearchResult


# Hard ceiling for the KNN over-fetch depth (CORR-03 / research Open Q8): the
# fetch window scales with limit+offset, but a huge offset must not turn into
# unbounded brute-force work. An offset past this practical cap yields an
# empty page rather than an ever-deeper KNN scan.
_MAX_FETCH_K = 2048


class VectorSearcher:
    """Vector similarity search using sqlite-vec or fallback."""

    def __init__(self, db: sqlite3.Connection, embedding_dim: int = 768) -> None:
        """Initialize vector searcher with sqlite-vec."""
        self.db = db
        self.embedding_dim = embedding_dim
        self._vec_available = self._check_vec_extension()
        if not self._vec_available:
            raise RuntimeError(
                "sqlite-vec extension is not available. Install sqlite-vec to use vector search.",
            )

    def _check_vec_extension(self) -> bool:
        """Check if sqlite-vec extension is available."""
        try:
            self.db.execute("SELECT vec_version()")
            return True
        except sqlite3.OperationalError:
            return False

    def search(
        self,
        query_embedding: list[float],
        options: SearchOptions | None = None,
    ) -> list[SearchResult]:
        """Search documents by vector similarity.

        ``offset`` slices the ranked list exactly once (this searcher is the
        slice owner for direct callers); returned ranks are global across
        pages (``offset + position``).
        """
        if options is None:
            options = SearchOptions()

        # Exclude-all sentinel: an empty list means every collection is
        # excluded (the CLI emits [] when its enabled-collections resolution
        # comes back empty) and must return zero results; None means
        # unfiltered. Without this guard the truthiness check in
        # _search_with_vec treats [] as "no filter" and leaks all documents.
        if options.collection_ids is not None and not options.collection_ids:
            return []

        return self._search_with_vec(query_embedding, options)

    def _search_with_vec(
        self,
        query_embedding: list[float],
        options: SearchOptions,
    ) -> list[SearchResult]:
        """Search using sqlite-vec.

        By default duplicate chunk hits collapse to one row per document
        (CORR-02): the best-distance row wins, carries that chunk's
        ``chunk_id``/``sequence``, and ``chunk_matches`` counts the pre-dedup
        vector rows. ``options.per_chunk`` keeps the ungrouped chunk rows.

        ``fetch_k`` starts at ``min(max(target * 4, 50), _MAX_FETCH_K)`` and
        doubles only while the batch saturated the requested k and the
        distinct target (``limit + offset``) is unmet — the independent
        ceiling bounds the work a huge offset can request. One page slice
        follows, and ranks are global across pages (``offset + position``).
        """
        # Convert embedding to vec format
        embedding_str = self._embedding_to_vec(query_embedding)

        # Build collection filter. The KNN limit is bound as a parameter
        # (WR-03) and clamped: limit <= 0 would surface as a raw
        # sqlite3.OperationalError from inside the vec0 MATCH.
        collection_filter = ""
        if options.collection_ids:
            placeholders = ", ".join(["?"] * len(options.collection_ids))
            collection_filter = f"AND d.collection_id IN ({placeholders})"

        # The KNN MATCH runs before the JOIN applies the collection filter, so
        # a tight k silently under-returns filtered searches (WR-04); the
        # window therefore starts at a bounded surplus and only grows while
        # the batch is demonstrably saturated. The LEFT JOIN supplies chunk
        # identity; legacy rows with a chunk_id that has no document_chunks
        # row (or NULL) yield None/None.
        # Audit note (261105-wwz, 2026-11-05): this KNN MATCH is the only
        # vec0 access in the search path and no WHERE filters a vec0 metadata
        # column; EXPLAIN QUERY PLAN shows the single vec0 SCAN outermost with
        # both JOINs resolved as PK lookups per KNN-emitted row, and timing is
        # flat across collection-filter sizes. vec0 v0.1.9 KNN is an inherent
        # once-per-query brute-force pass over all stored vectors regardless
        # of filter shape.
        sql = f"""
            SELECT
                d.id as document_id,
                d.title,
                d.path,
                c.name as collection_name,
                distance as score,
                de.chunk_id as chunk_id,
                dc.sequence as sequence
            FROM document_embeddings de
            JOIN documents d ON de.document_id = d.id
            JOIN collections c ON d.collection_id = c.id
            LEFT JOIN document_chunks dc ON dc.id = de.chunk_id
            WHERE embedding MATCH ? AND k = ? {collection_filter}
            ORDER BY distance
        """

        target = max(1, options.limit + options.offset)
        fetch_k = min(max(target * 4, 50), _MAX_FETCH_K)
        while True:
            params = [embedding_str, fetch_k, *(options.collection_ids or [])]
            rows = self.db.execute(sql, params).fetchall()
            candidates = self._candidates(rows, options)

            # Escalate only while the batch may have been truncated (it
            # returned exactly k rows) and the target is unmet. The module
            # constant is an independent ceiling (T-19-13): a huge offset
            # degrades to an empty page instead of unbounded KNN work.
            if len(candidates) >= target or len(rows) < fetch_k or fetch_k >= _MAX_FETCH_K:
                break
            fetch_k = min(fetch_k * 2, _MAX_FETCH_K)

        # Take the requested page once, then number ranks globally (D-06):
        # rank = offset + position. The window trim keeps the WR-03 clamp:
        # limit <= 0 still yields one row instead of an empty/raw-KNN result.
        page_limit = max(1, options.limit)
        page = candidates[options.offset : options.offset + page_limit]
        for position, result in enumerate(page, 1):
            result.rank = options.offset + position
            if options.include_content:
                result.content = self._get_document_content(result.document_id)

        return page

    def _candidates(self, rows: list[sqlite3.Row], options: SearchOptions) -> list[SearchResult]:
        """Build result rows from KNN output, deduped per document by default.

        ``min_score`` filters on converted scores before grouping. In the
        default mode a document's rows collapse onto its best-distance
        (first-seen) row, with ``chunk_matches`` counting the group; per-chunk
        mode keeps every row and leaves ``chunk_matches`` at 0 (D-01/D-02).
        """
        if options.per_chunk:
            results: list[SearchResult] = []
            for row in rows:
                result = self._row_to_result(row)
                if result.score >= options.min_score:
                    results.append(result)
            return results

        grouped: dict[str, SearchResult] = {}
        for row in rows:
            result = self._row_to_result(row)
            if result.score < options.min_score:
                continue
            existing = grouped.get(result.document_id)
            if existing is None:
                result.chunk_matches = 1
                grouped[result.document_id] = result
            else:
                existing.chunk_matches += 1
        return list(grouped.values())

    @staticmethod
    def _row_to_result(row: sqlite3.Row) -> SearchResult:
        """Convert one KNN row to a SearchResult carrying chunk identity."""
        keys = row.keys()
        return SearchResult(
            document_id=row["document_id"],
            title=row["title"] or "",
            path=row["path"],
            collection_name=row["collection_name"],
            # Cosine distance is 0-2, convert to 0-1 score
            score=1.0 - (row["score"] / 2.0),
            chunk_id=row["chunk_id"] if "chunk_id" in keys else None,
            sequence=row["sequence"] if "sequence" in keys else None,
        )

    def _embedding_to_vec(self, embedding: list[float]) -> str:
        """Convert embedding to sqlite-vec format."""
        return json.dumps(embedding)

    def _get_document_content(self, document_id: str) -> str | None:
        """Get document content."""
        cursor = self.db.execute("SELECT content FROM documents WHERE id = ?", (document_id,))
        row = cursor.fetchone()
        return row[0] if row else None

    def add_embedding(
        self,
        embedding_id: str,
        document_id: str,
        chunk_id: str | None,
        embedding: list[float],
    ) -> None:
        """Add an embedding to the index."""
        self._add_embedding_vec(embedding_id, document_id, chunk_id, embedding)

    def _add_embedding_vec(
        self,
        embedding_id: str,
        document_id: str,
        chunk_id: str | None,
        embedding: list[float],
    ) -> None:
        """Add embedding using sqlite-vec."""
        embedding_str = self._embedding_to_vec(embedding)

        self.db.execute(
            """
            INSERT OR REPLACE INTO document_embeddings
            (embedding_id, document_id, chunk_id, embedding)
            VALUES (?, ?, ?, vec_f32(?))
            """,
            (embedding_id, document_id, chunk_id, embedding_str),
        )

    def add_embeddings_batch(
        self,
        items: list[tuple[str, str, str | None, list[float]]],
    ) -> None:
        """Add multiple embeddings in a single batch operation.

        Each item is a tuple of (embedding_id, document_id, chunk_id, embedding_vector).
        """
        if not items:
            return
        rows = [(eid, doc_id, chunk_id, json.dumps(vec)) for eid, doc_id, chunk_id, vec in items]
        self.db.executemany(
            """
            INSERT OR REPLACE INTO document_embeddings
            (embedding_id, document_id, chunk_id, embedding)
            VALUES (?, ?, ?, vec_f32(?))
            """,
            rows,
        )

    def delete_embeddings_by_document(self, document_id: str) -> int:
        """Delete all stored embeddings for a document.

        Returns the number of rows removed. Plain parameterized SQL is correct
        here: sqlite-vec supports DELETE on vec0 tables by non-key columns.
        """
        cursor = self.db.execute(
            "DELETE FROM document_embeddings WHERE document_id = ?",
            (document_id,),
        )
        return cursor.rowcount

    def get_embedded_chunk_ids(self, document_id: str) -> set[str]:
        """Get the chunk ids a document currently has stored embeddings for.

        Rows whose chunk_id is NULL are skipped: NULL can never equal a live
        chunk id, so documents carrying such rows are re-embedded and cleaned.
        """
        cursor = self.db.execute(
            "SELECT chunk_id FROM document_embeddings WHERE document_id = ?",
            (document_id,),
        )
        return {row[0] for row in cursor.fetchall() if row[0] is not None}

    def get_all_embedded_chunk_ids(self) -> dict[str, set[str]]:
        """Get every document's stored-embedding chunk-id set in one table read.

        The vec0 virtual table has no index on its metadata columns, so each
        per-document filtered lookup costs a full table scan; callers judging
        every document must batch. Rows are iterated one at a time (never
        fetchall) so peak memory is the resulting map, not a row buffer.
        NULL chunk_id rows are skipped with the same contract as the
        single-document lookup directly above: NULL can never equal a live
        chunk id, so documents carrying such rows re-embed and self-heal.
        """
        result: dict[str, set[str]] = {}
        cursor = self.db.execute(
            "SELECT document_id, chunk_id FROM document_embeddings",
        )
        for document_id, chunk_id in cursor:
            if chunk_id is None:
                continue
            result.setdefault(document_id, set()).add(chunk_id)
        return result


def create_embedding_purger(conn: sqlite3.Connection) -> VectorSearcher | None:
    """Return a VectorSearcher for purging embeddings, or None without sqlite-vec.

    A missing sqlite-vec extension also means no vec0 table — hence no stored
    embeddings — so callers treat None as "nothing to purge".

    Single shared construction point for embedding purgers (WR-01): both
    IncrementalIndexer and ``collection remove`` build their purger here.
    """
    try:
        return VectorSearcher(conn)
    except RuntimeError:
        return None
