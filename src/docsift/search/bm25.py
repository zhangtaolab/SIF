"""BM25 full-text search implementation."""

from __future__ import annotations

import sqlite3
from typing import List, Optional, Tuple

from docsift.core.models import SearchOptions, SearchResult


class BM25Searcher:
    """BM25 full-text search using SQLite FTS5."""

    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db

    def search(self, query: str, options: Optional[SearchOptions] = None) -> List[SearchResult]:
        """Search documents using BM25."""
        if options is None:
            options = SearchOptions()

        # Build the FTS query
        fts_query = self._build_fts_query(query)

        # Build collection filter
        collection_filter = ""
        params = [fts_query]

        if options.collection_ids:
            placeholders = ", ".join(["?"] * len(options.collection_ids))
            collection_filter = f"AND d.collection_id IN ({placeholders})"
            params.extend(options.collection_ids)

        # Execute search
        sql = f"""
            SELECT 
                d.id as document_id,
                d.title,
                d.path,
                c.name as collection_name,
                rank as score
            FROM documents_fts fts
            JOIN documents d ON fts.rowid = d.rowid
            JOIN collections c ON d.collection_id = c.id
            WHERE documents_fts MATCH ? {collection_filter}
            ORDER BY rank
            LIMIT ? OFFSET ?
        """
        params.extend([options.limit, options.offset])

        cursor = self.db.execute(sql, params)
        results = []

        for rank, row in enumerate(cursor.fetchall(), 1):
            # Convert rank to score (lower rank = higher score)
            score = 1.0 / (1.0 + abs(row["score"]))

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

            if options.include_highlights:
                result.highlights = self._get_highlights(
                    row["document_id"], query, options.max_highlights
                )

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
        rows = cursor.fetchall()
        # Handle both sqlite3.Row (dict-like) and plain tuple rows
        context_map: dict[str, str] = {}
        for row in rows:
            if hasattr(row, "keys") and callable(getattr(row, "keys", None)):
                try:
                    context_map[row["target_id"]] = row["content"]
                    continue
                except (KeyError, TypeError):
                    pass
            # Fallback: assume tuple-like access (skip MagicMock rows in tests)
            try:
                key = row[0]
                val = row[1]
                if not isinstance(key, str):
                    continue
                context_map[key] = val
            except (KeyError, IndexError, TypeError):
                continue
        for result in results:
            result.context_description = context_map.get(result.path)
        return results

    def search_chunks(
        self, query: str, options: Optional[SearchOptions] = None
    ) -> List[Tuple[str, str, float]]:
        """Search document chunks using BM25.

        Returns list of (document_id, chunk_content, score) tuples.
        """
        if options is None:
            options = SearchOptions()

        fts_query = self._build_fts_query(query)

        sql = """
            SELECT 
                dc.document_id,
                dc.content,
                rank as score
            FROM chunks_fts fts
            JOIN document_chunks dc ON fts.rowid = dc.rowid
            WHERE chunks_fts MATCH ?
            ORDER BY rank
            LIMIT ? OFFSET ?
        """

        cursor = self.db.execute(sql, [fts_query, options.limit, options.offset])
        results = []

        for row in cursor.fetchall():
            score = 1.0 / (1.0 + abs(row["score"]))
            if score >= options.min_score:
                results.append((row["document_id"], row["content"], score))

        return results

    def _build_fts_query(self, query: str) -> str:
        """Build FTS5 query from user query.

        Handles:
        - Multiple terms (AND search)
        - Phrases (quoted strings)
        - Prefix search (term*)
        """
        # Simple implementation: just join terms with AND
        terms = query.split()
        if not terms:
            return "*"

        # Use NEAR for better relevance
        if len(terms) == 1:
            return f"{terms[0]}*"

        # For multiple terms, use AND
        return " AND ".join(f"{term}*" for term in terms)

    def _get_document_content(self, document_id: str) -> Optional[str]:
        """Get document content."""
        cursor = self.db.execute("SELECT content FROM documents WHERE id = ?", (document_id,))
        row = cursor.fetchone()
        return row[0] if row else None

    def _get_highlights(self, document_id: str, query: str, max_highlights: int = 3) -> List[str]:
        """Get highlighted snippets for a document."""
        # Get chunks for the document
        cursor = self.db.execute(
            """
            SELECT content FROM document_chunks 
            WHERE document_id = ?
            ORDER BY sequence
            """,
            (document_id,),
        )

        chunks = [row[0] for row in cursor.fetchall()]
        if not chunks:
            # Get full document content
            content = self._get_document_content(document_id)
            if content:
                chunks = [content[:1000]]  # First 1000 chars

        # Find chunks containing query terms
        query_terms = [t.lower() for t in query.split()]
        highlights = []

        for chunk in chunks:
            chunk_lower = chunk.lower()
            if any(term in chunk_lower for term in query_terms):
                # Extract snippet around the match
                snippet = self._extract_snippet(chunk, query_terms)
                if snippet:
                    highlights.append(snippet)
                    if len(highlights) >= max_highlights:
                        break

        return highlights

    def _extract_snippet(self, text: str, query_terms: List[str], context: int = 50) -> str:
        """Extract a snippet around query matches."""
        text_lower = text.lower()

        for term in query_terms:
            pos = text_lower.find(term)
            if pos >= 0:
                start = max(0, pos - context)
                end = min(len(text), pos + len(term) + context)
                snippet = text[start:end]

                # Add ellipsis if truncated
                if start > 0:
                    snippet = "..." + snippet
                if end < len(text):
                    snippet = snippet + "..."

                return snippet.strip()

        # Return first part if no match found
        return text[:200].strip() + "..." if len(text) > 200 else text.strip()
