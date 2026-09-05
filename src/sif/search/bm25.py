"""BM25 full-text search implementation."""

from __future__ import annotations

import os
import re
import sqlite3

from sif.core.models import SearchOptions, SearchResult
from sif.search.term_match import find_first_match


_SNIPPET_MAX_LEN = 200

# Characters with special meaning in FTS5 MATCH expressions; they cannot be
# escaped, so they are stripped from user tokens before quoting.
_FTS_METACHARS = re.compile(r'["*():^]')


def _sanitize_term(term: str) -> str:
    """Sanitize a raw query token into a safe FTS5 phrase.

    Metacharacters are replaced with spaces (the tokenizer then treats the
    remainder as plain phrase text) and the result is wrapped in double
    quotes so the token is matched literally instead of being parsed as
    FTS5 query syntax. A trailing ``*`` outside the quotes keeps prefix
    matching. Returns an empty string for tokens with nothing left.
    """
    cleaned = _FTS_METACHARS.sub(" ", term).strip()
    if not cleaned:
        return ""
    return f'"{cleaned}"*'


class BM25Searcher:
    """BM25 full-text search using SQLite FTS5."""

    def __init__(self, db: sqlite3.Connection) -> None:
        """Initialize the BM25 searcher."""
        self.db = db

    def search(self, query: str, options: SearchOptions | None = None) -> list[SearchResult]:
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
                    row["document_id"],
                    query,
                    options.max_highlights,
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
        # Normalize keys for cross-platform matching (macOS /private/tmp, etc.)
        context_map = {
            os.path.realpath(row["target_id"]): row["content"] for row in cursor.fetchall()
        }
        for result in results:
            result.context_description = context_map.get(os.path.realpath(result.path))
        return results

    def search_chunks(
        self,
        query: str,
        options: SearchOptions | None = None,
    ) -> list[tuple[str, str, float]]:
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
        """Build a safe FTS5 query from raw user input.

        Each whitespace-separated token is sanitized into a quoted prefix
        phrase and tokens are joined with AND, so ordinary input like
        ``e-mail``, ``don't``, or ``c++`` cannot be parsed as FTS5 query
        syntax. A query with no usable terms yields an empty phrase, which
        matches nothing instead of raising sqlite3.OperationalError.
        """
        terms = [t for t in (_sanitize_term(tok) for tok in query.split()) if t]
        if not terms:
            return '""'
        return " AND ".join(terms)

    def _get_document_content(self, document_id: str) -> str | None:
        """Get document content."""
        cursor = self.db.execute("SELECT content FROM documents WHERE id = ?", (document_id,))
        row = cursor.fetchone()
        return row[0] if row else None

    def _get_highlights(self, document_id: str, query: str, max_highlights: int = 3) -> list[str]:
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
            if find_first_match(chunk, query_terms) is not None:
                # Extract snippet around the match
                snippet = self._extract_snippet(chunk, query_terms)
                if snippet:
                    highlights.append(snippet)
                    if len(highlights) >= max_highlights:
                        break

        return highlights

    def _extract_snippet(self, text: str, query_terms: list[str], context: int = 50) -> str:
        """Extract a snippet around the first query term match."""
        match = find_first_match(text, query_terms)
        if match is not None:
            pos, match_len = match
            start = max(0, pos - context)
            end = min(len(text), pos + match_len + context)
            snippet = text[start:end]

            # Add ellipsis if truncated
            if start > 0:
                snippet = "..." + snippet
            if end < len(text):
                snippet = snippet + "..."

            return snippet.strip()

        # Return first part if no match found
        if len(text) > _SNIPPET_MAX_LEN:
            return text[:_SNIPPET_MAX_LEN].strip() + "..."
        return text.strip()
