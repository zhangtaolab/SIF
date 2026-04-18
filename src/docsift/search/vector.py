"""Vector similarity search implementation."""

from __future__ import annotations

import json
import os
import sqlite3
from typing import List, Optional

from docsift.core.models import SearchOptions, SearchResult


class VectorSearcher:
    """Vector similarity search using sqlite-vec or fallback."""

    def __init__(self, db: sqlite3.Connection, embedding_dim: int = 768) -> None:
        self.db = db
        self.embedding_dim = embedding_dim
        self._vec_available = self._check_vec_extension()
        if not self._vec_available:
            raise RuntimeError(
                "sqlite-vec extension is not available. Install sqlite-vec to use vector search."
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
        query_embedding: List[float],
        options: Optional[SearchOptions] = None,
    ) -> List[SearchResult]:
        """Search documents by vector similarity."""
        if options is None:
            options = SearchOptions()
        return self._search_with_vec(query_embedding, options)

    def _search_with_vec(
        self,
        query_embedding: List[float],
        options: SearchOptions,
    ) -> List[SearchResult]:
        """Search using sqlite-vec."""
        # Convert embedding to vec format
        embedding_str = self._embedding_to_vec(query_embedding)

        # Build collection filter
        collection_filter = ""
        params = [embedding_str]

        if options.collection_ids:
            placeholders = ", ".join(["?"] * len(options.collection_ids))
            collection_filter = f"AND d.collection_id IN ({placeholders})"
            params.extend(options.collection_ids)

        sql = f"""
            SELECT 
                d.id as document_id,
                d.title,
                d.path,
                c.name as collection_name,
                distance as score
            FROM document_embeddings de
            JOIN documents d ON de.document_id = d.id
            JOIN collections c ON d.collection_id = c.id
            WHERE embedding MATCH ? {collection_filter}
            ORDER BY distance
            LIMIT ? OFFSET ?
        """
        params.extend([options.limit, options.offset])

        cursor = self.db.execute(sql, params)
        results = []

        for rank, row in enumerate(cursor.fetchall(), 1):
            # Convert distance to score (lower distance = higher score)
            # Cosine distance is 0-2, convert to 0-1 score
            score = 1.0 - (row["score"] / 2.0)

            if score < options.min_score:
                continue

            result = SearchResult(
                document_id=row["document_id"],
                title=row["title"] or "",
                path=row["path"],
                collection_name=row["collection_name"],
                score=score,
                rank=rank,
            )

            if options.include_content:
                result.content = self._get_document_content(row["document_id"])

            results.append(result)

        return self._attach_contexts(results)

    def _attach_contexts(self, results: list[SearchResult]) -> list[SearchResult]:
        """Attach path context descriptions to search results via batch query."""
        if not results:
            return results
        paths = list({r.path for r in results})
        placeholders = ", ".join(["?"] * len(paths))
        sql = f"""
            SELECT target_id, content FROM contexts
            WHERE context_type = 'path' AND target_id IN ({placeholders})
        """
        cursor = self.db.execute(sql, paths)
        # Normalize keys for cross-platform matching (macOS /private/tmp, etc.)
        context_map = {
            os.path.realpath(row["target_id"]): row["content"]
            for row in cursor.fetchall()
        }
        for result in results:
            result.context_description = context_map.get(os.path.realpath(result.path))
        return results

    def _embedding_to_vec(self, embedding: List[float]) -> str:
        """Convert embedding to sqlite-vec format."""
        return json.dumps(embedding)

    def _get_document_content(self, document_id: str) -> Optional[str]:
        """Get document content."""
        cursor = self.db.execute("SELECT content FROM documents WHERE id = ?", (document_id,))
        row = cursor.fetchone()
        return row[0] if row else None

    def add_embedding(
        self,
        embedding_id: str,
        document_id: str,
        chunk_id: Optional[str],
        embedding: List[float],
    ) -> None:
        """Add an embedding to the index."""
        self._add_embedding_vec(embedding_id, document_id, chunk_id, embedding)

    def _add_embedding_vec(
        self,
        embedding_id: str,
        document_id: str,
        chunk_id: Optional[str],
        embedding: List[float],
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
        items: List[tuple[str, str, Optional[str], List[float]]],
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
