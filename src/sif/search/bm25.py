"""BM25 full-text search implementation."""

from __future__ import annotations

import re
import sqlite3

from sif.core.models import SearchOptions, SearchResult
from sif.search.filters import compile_filter
from sif.search.term_match import find_first_match


_SNIPPET_MAX_LEN = 200

# CORR-04 / D-11: BM25 column weights for documents_fts(content, title).
# The weight vector maps left-to-right by declared column order, so these two
# constants are bound as the bm25(documents_fts, ?, ?) parameters. At 1.0/1.0
# the weighted expression reproduces the unweighted `rank` column exactly.
# The title weight stays an internal constant — deliberately not a setting or
# a CLI flag. Plan 19-09's D-12 sweep measured 2.0/3.0/4.0 against B1 and
# rejected the band: the held-out title leg was already at its 1.0 ceiling and
# no candidate's ranks moved, so the pinned value stays 1.0. The evidence is
# .planning/phases/19-search-correctness/bench/d12-verdict.json.
_CONTENT_WEIGHT = 1.0
_TITLE_WEIGHT = 1.0

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


def bm25_display_score(raw: float) -> float:
    """Map an FTS5 bm25 value to the displayed BM25 score ``|bm25|/(1+|bm25|)``.

    FTS5 returns the bm25 value of a matching row as a negative number whose
    magnitude grows with relevance. Dividing that magnitude by one plus itself
    gives a result that lies in the open interval from 0 to 1 and rises with
    relevance, so a better match shows the higher score (UAT gap G-19-2, plan
    19-12).
    """
    magnitude = abs(raw)
    return magnitude / (1.0 + magnitude)


class BM25Searcher:
    """BM25 full-text search using SQLite FTS5."""

    def __init__(self, db: sqlite3.Connection) -> None:
        """Initialize the BM25 searcher."""
        self.db = db

    def search(self, query: str, options: SearchOptions | None = None) -> list[SearchResult]:
        """Search documents using BM25.

        ``min_score`` is applied inside the FTS scan (before LIMIT/OFFSET), so
        pagination always slices the filtered ranking, and returned ranks are
        global across pages (``options.offset + position``).
        """
        if options is None:
            options = SearchOptions()

        # Exclude-all sentinel: an empty list means every collection is
        # excluded (the CLI emits [] when its enabled-collections resolution
        # comes back empty — search.py ~163/329/468, bench.py ~105) and must
        # return zero results; None means unfiltered. The truthiness check
        # below would otherwise treat [] as "no filter" and leak all
        # documents, and an empty list must never reach the placeholder
        # builder because IN () is invalid SQLite syntax.
        if options.collection_ids is not None and not options.collection_ids:
            return []

        # Build the FTS query
        fts_query = self._build_fts_query(query)

        # min_score thresholding happens BEFORE LIMIT/OFFSET (CORR-03, research
        # Pitfall 4/P15). The predicate compares the displayed score itself,
        # computed in SQL from the same WEIGHTED bm25 expression that projects
        # `score`, with min_score bound as it was given, so a raised title
        # weight moves threshold and ordering together and a row whose
        # displayed score equals min_score to the last bit is kept (G-19-8,
        # plan 19-13). The earlier form, released in 1.2.4, compared the raw
        # value with a bound recomputed from min_score, which was not the exact
        # inverse of the score map and dropped about half of the rows at what
        # the user saw as equality. A value not above 0 (0, a negative value,
        # NaN) omits the predicate, because with a NaN bound the comparison is
        # NULL and would drop every row. A value of 1 or more keeps no row by
        # arithmetic, because the displayed score lies strictly between 0 and
        # 1.
        content_weight = _CONTENT_WEIGHT
        title_weight = _TITLE_WEIGHT if options.title_weight is None else options.title_weight

        params = [content_weight, title_weight, fts_query]
        collection_filter = ""
        if options.collection_ids:
            placeholders = ", ".join(["?"] * len(options.collection_ids))
            params.extend(options.collection_ids)
            collection_filter = f"AND d.collection_id IN ({placeholders})"

        min_score_filter = ""
        if options.min_score > 0:
            params.append(options.min_score)
            min_score_filter = "AND abs(m.score) / (1.0 + abs(m.score)) >= ?"

        # Metadata filter (Phase 20, D-02/D-17): the compiled predicate is one
        # more fragment in the OUTER WHERE of the materialized CTE (never
        # inside it — the CTE exists to evaluate MATCH once). None is the only
        # unfiltered signal, so the suffix is empty for the byte-identical
        # default path; a non-None AST always yields a non-empty predicate.
        # Params land after the min-score parameter and before limit/offset,
        # matching placeholder order (T-20-01: values are always bound).
        filter_clause, filter_params = compile_filter(options.filter, alias="d", scope="candidates")
        params.extend(filter_params)
        filter_suffix = f" AND {filter_clause}" if filter_clause else ""

        # Keep the FTS match evaluated once for scoped searches. The scoped
        # default CLI path always carries a non-empty collection filter; with
        # a bare join (or a plain, flattened CTE) SQLite drives from
        # `documents` via idx_documents_collection and re-runs the match per
        # candidate document (`SCAN fts VIRTUAL TABLE INDEX 32:=M1`). AS
        # MATERIALIZED computes the match once before the join; the keyword
        # needs SQLite >= 3.35.0 (2021-03), newer than supported CPython
        # 3.10+. The weighted expression names the real table (an FTS5 alias
        # is rejected — Pitfall 5); weights and the min_score threshold are
        # bound parameters, never interpolated (T-19-19). Every projection is
        # the same weighted expression, so a raised title weight moves both
        # ordering and thresholding together.
        if options.collection_ids:
            sql = f"""
                WITH matched AS MATERIALIZED (
                    SELECT rowid, bm25(documents_fts, ?, ?) AS score
                    FROM documents_fts
                    WHERE documents_fts MATCH ?
                )
                SELECT
                    d.id as document_id,
                    d.title,
                    d.path,
                    c.name as collection_name,
                    m.score as score
                FROM matched m
                JOIN documents d ON m.rowid = d.rowid
                JOIN collections c ON d.collection_id = c.id
                WHERE 1 = 1 {collection_filter} {min_score_filter}{filter_suffix}
                ORDER BY m.score
                LIMIT ? OFFSET ?
            """
        else:
            # Unfiltered (--all) SQL uses the same materialized weighted match;
            # the min_score predicate still applies before LIMIT/OFFSET.
            sql = f"""
                WITH matched AS MATERIALIZED (
                    SELECT rowid, bm25(documents_fts, ?, ?) AS score
                    FROM documents_fts
                    WHERE documents_fts MATCH ?
                )
                SELECT
                    d.id as document_id,
                    d.title,
                    d.path,
                    c.name as collection_name,
                    m.score as score
                FROM matched m
                JOIN documents d ON m.rowid = d.rowid
                JOIN collections c ON d.collection_id = c.id
                WHERE 1 = 1 {min_score_filter}{filter_suffix}
                ORDER BY m.score
                LIMIT ? OFFSET ?
            """
        params.extend([options.limit, options.offset])

        cursor = self.db.execute(sql, params)
        results = []

        for position, row in enumerate(cursor.fetchall(), 1):
            # Convert the bm25 value to the displayed score, which rises with
            # relevance (a more negative value is a better match).
            score = bm25_display_score(row["score"])

            result = SearchResult(
                document_id=row["document_id"],
                title=row["title"] or "",
                path=row["path"],
                collection_name=row["collection_name"],
                score=score,
                # Ranks are global across pages (D-06): page 2 at offset 5
                # carries ranks 6-10, matching overall ordering.
                rank=options.offset + position,
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

        return results

    def search_chunks(
        self,
        query: str,
        options: SearchOptions | None = None,
    ) -> list[tuple[str, str, float]]:
        """Search document chunks using BM25.

        Returns list of (document_id, chunk_content, score) tuples.

        Metadata filters apply to document-level search only; this chunk-level
        helper stays filter-free and has no production caller.
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
            score = bm25_display_score(row["score"])
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
