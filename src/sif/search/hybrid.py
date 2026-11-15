"""Hybrid search combining BM25 and vector search with RRF."""

from __future__ import annotations

import sqlite3
from dataclasses import replace
from typing import TYPE_CHECKING, cast

from sif.core.models import Embedder, SearchOptions, SearchResult, SearchType
from sif.search.bm25 import BM25Searcher
from sif.search.context_attach import enrich_results
from sif.search.rrf import RRFFusion
from sif.search.vector import VectorSearcher
from sif.utils.logging import get_logger


if TYPE_CHECKING:
    from sif.search.expansion import QueryExpansion
    from sif.search.rerank import CrossEncoderReranker, LlamaCppReranker, Qwen3Reranker
    from sif.search.snippets import SmartSnippetExtractor

logger = get_logger(__name__)


def _paginate(results: list[SearchResult], options: SearchOptions) -> list[SearchResult]:
    """Apply the one offset slice and global rank numbering for a query path.

    CORR-03/D-06: every path has exactly one slice owner, and ranks are global
    across pages (``options.offset + position``) so page 2 of a 10-row page
    carries ranks 11-20. ``max(1, limit)`` keeps the historical non-positive
    limit clamp (one row) instead of producing an empty page.
    """
    page_limit = max(1, options.limit)
    page = results[options.offset : options.offset + page_limit]
    for position, result in enumerate(page, 1):
        result.rank = options.offset + position
    return page


class HybridSearcher:
    """Hybrid search combining multiple search strategies."""

    def __init__(
        self,
        db: sqlite3.Connection,
        embedder: Embedder | None = None,
        embedding_dim: int = 768,
    ) -> None:
        """Initialize the hybrid searcher."""
        self.db = db
        self.embedder = embedder
        self.bm25 = BM25Searcher(db)
        self.vector = VectorSearcher(db, embedding_dim)
        self.rrf = RRFFusion(k=60)

    def search(
        self,
        query: str,
        options: SearchOptions | None = None,
    ) -> list[SearchResult]:
        """Search using hybrid approach (BM25 + Vector + RRF).

        Args:
            query: Search query
            options: Search options

        Returns:
            Ranked list of search results, raw and unenriched (the pipeline
            exit owns the single context/staleness enrichment).

        ``HybridSearcher.search`` is the single offset slice owner for direct
        callers (CORR-03): both legs are called with ``offset=0`` and
        ``limit+offset``, and this method slices one page afterwards. The
        pipeline always calls it with ``offset=0`` and slices itself.
        """
        if options is None:
            options = SearchOptions()

        # Offset-free fetch window shared by both legs (research Pitfall 12):
        # applying the caller's offset here as well as in the legs would
        # double-apply it and under-fetch the page.
        fetch_options = replace(
            options,
            limit=max(1, options.limit + options.offset),
            offset=0,
        )

        # Get BM25 results
        bm25_results = self.bm25.search(query, fetch_options)

        # Get vector results if embedder is available
        vector_results: list[SearchResult] = []
        if self.embedder is not None:
            query_embedding = self.embedder.embed(query)
            vector_results = self.vector.search(query_embedding, fetch_options)

        # If only one method returned results, paginate that leg's window too
        # (its searcher already fetched limit+offset rows at offset 0).
        if not vector_results:
            return _paginate(bm25_results, options)
        if not bm25_results:
            return _paginate(vector_results, options)

        # Fuse results using RRF (Phase 15: per-query weights/k ride options —
        # the ONLY weights call site; k also flows to the pipeline's
        # cross-query variant fusion, weights must NOT (Pitfall 9/A7))
        fused_results = self.rrf.fuse(
            [bm25_results, vector_results],
            fetch_options.limit,
            weights=[options.bm25_weight, options.vector_weight],
            k=options.rrf_k,
        )

        # Re-fetch content and highlights if needed
        if options.include_content or options.include_highlights:
            for result in fused_results:
                if options.include_content and result.content is None:
                    result.content = self._get_document_content(result.document_id)
                if options.include_highlights and not result.highlights:
                    result.highlights = self._get_highlights(
                        result.document_id,
                        query,
                        options.max_highlights,
                    )

        # Deduplicate by document_id, keeping highest score, then slice the
        # caller's page once with global rank numbering.
        return _paginate(self._deduplicate_results(fused_results), options)

    @staticmethod
    def _deduplicate_results(results: list[SearchResult]) -> list[SearchResult]:
        """Deduplicate results by document_id, keeping the highest score.

        Vector search operates at chunk level, so the same document may appear
        multiple times. We keep the best-scoring entry per document and
        reassign sequential ranks.
        """
        best: dict[str, SearchResult] = {}
        for result in results:
            doc_id = result.document_id
            if doc_id not in best or result.score > best[doc_id].score:
                best[doc_id] = result

        deduped = list(best.values())
        deduped.sort(key=lambda r: r.score, reverse=True)
        for rank, result in enumerate(deduped, 1):
            result.rank = rank
        return deduped

    def _get_document_content(self, document_id: str) -> str | None:
        """Get document content."""
        cursor = self.db.execute("SELECT content FROM documents WHERE id = ?", (document_id,))
        row = cursor.fetchone()
        return row[0] if row else None

    def _get_highlights(
        self,
        document_id: str,
        query: str,
        max_highlights: int = 3,
    ) -> list[str]:
        """Get highlighted snippets."""
        return self.bm25._get_highlights(document_id, query, max_highlights)  # noqa: SLF001


class SearchPipeline:
    """Complete search pipeline with prefix routing, expansion, and reranking."""

    def __init__(  # noqa: PLR0913
        self,
        db: sqlite3.Connection,
        embedder: Embedder | None = None,
        query_expander: QueryExpansion | None = None,
        reranker: LlamaCppReranker | CrossEncoderReranker | Qwen3Reranker | None = None,
        snippet_extractor: SmartSnippetExtractor | None = None,
        embedding_dim: int = 768,
        default_search_type: str = "hybrid",
        parse_prefix: bool = True,
    ) -> None:
        """Initialize search pipeline with optional components.

        ``parse_prefix=False`` makes ``search()`` treat every query as
        literal text and route it through ``default_search_type``: the
        personal eval uses this so a document title (or logged replay query)
        that happens to start with ``vec:``/``hyde:``/``lex:``/``expand:`` is
        measured as text instead of being reinterpreted as an operator.
        """
        self.db = db
        self.hybrid = HybridSearcher(db, embedder, embedding_dim)
        self.query_expander = query_expander
        self.reranker = reranker
        self.snippet_extractor = snippet_extractor
        self._default_search_type = default_search_type
        self._parse_prefix = parse_prefix

    def search(  # noqa: C901, PLR0912, PLR0915
        self,
        query: str,
        options: SearchOptions | None = None,
    ) -> list[SearchResult]:
        """Execute full search pipeline with optional prefix routing.

        1. Parse query prefix to determine search mode (unless literal mode)
        2. Route to appropriate search mode (BM25, vector, HyDE, hybrid)
        3. Expand query (optional, for expand: prefix or default hybrid)
        4. Search with each query variant
        5. Fuse results with RRF
        6. Apply reranking with candidate capping
        7. Extract smart snippets
        8. Apply the single offset slice with global rank numbering
        9. Enrich results exactly once (path contexts + derived staleness)
        """
        if options is None:
            options = SearchOptions()

        # Literal mode (personal eval): never reinterpret query text as an
        # operator prefix; use the configured default mode directly.
        if self._parse_prefix:
            parsed_query, search_type = self._parse_query_prefix(query)
        else:
            parsed_query, search_type = query, self._default_search_type_enum()

        # Apply intent if provided
        if options.intent:
            parsed_query = f"{options.intent}: {parsed_query}"

        # Route to appropriate search mode
        if search_type == SearchType.BM25:
            results = self.hybrid.bm25.search(parsed_query, options)
            return enrich_results(self.db, self._apply_snippets(results, parsed_query))
        if search_type == SearchType.VECTOR:
            if self.hybrid.embedder is None:
                raise RuntimeError("Vector search requires an embedder")
            query_embedding = self.hybrid.embedder.embed(parsed_query)
            results = self.hybrid.vector.search(query_embedding, options)
            return enrich_results(self.db, self._apply_snippets(results, parsed_query))
        if search_type == SearchType.HYDE:
            hyde_doc = self._generate_hypothetical_document(parsed_query)
            if self.hybrid.embedder is None:
                raise RuntimeError("HyDE search requires an embedder")
            hyde_embedding = self.hybrid.embedder.embed(hyde_doc)
            results = self.hybrid.vector.search(hyde_embedding, options)
            return enrich_results(self.db, self._apply_snippets(results, parsed_query))

        # Default: hybrid search with optional expansion
        queries = [parsed_query]

        # Expand query if expander is available and prefix is expand: or default
        if self.query_expander is not None and search_type in (
            SearchType.HYBRID,
            SearchType.EXPAND,
        ):
            try:
                expanded = self.query_expander.expand(parsed_query)
                # Deduplicate against the original without assuming the
                # expander echoes it: the QueryExpander contract only promises
                # multiple variants, not element-0 echo.
                seen = {parsed_query.lower()}
                for variant in expanded:
                    if variant.lower() not in seen:
                        seen.add(variant.lower())
                        queries.append(variant)
            except Exception as e:
                logger.warning(f"Query expansion failed: {e}")

        # Offset-0 fetch window (CORR-03 / research Pitfall 12): the pipeline
        # owns the single offset slice for its own path, so it always calls
        # the hybrid searcher with offset=0 and a window of at least
        # limit+offset. With a reranker that window is raised to
        # candidate_limit as well — and when the page reaches past the cap, to
        # limit+offset — so the pre-rerank truncation can never starve the
        # page. Phase 16's cap still binds: at offset=0 the window stays
        # exactly candidate_limit (the off path stays byte-identical).
        if self.reranker is not None:
            fetch_options = replace(
                options,
                limit=max(options.limit + options.offset, options.candidate_limit),
                offset=0,
            )
        else:
            fetch_options = replace(
                options,
                limit=max(1, options.limit + options.offset),
                offset=0,
            )

        # Search with each query
        all_results = []
        for q in queries:
            results = self.hybrid.search(q, fetch_options)
            if results:
                all_results.append(results)

        # If only one query or no expansion, return results
        if len(all_results) <= 1:
            results = all_results[0] if all_results else []
        else:
            # Fuse results from multiple queries (cross-query VARIANT fusion —
            # not source fusion: k rides options, weights are meaningless here
            # and must never be passed (Pitfall 9 / assumption A7))
            results = self.hybrid.rrf.fuse(all_results, fetch_options.limit, k=options.rrf_k)

        # Apply the pre-rerank candidate window, then rerank to the window
        # depth. offset=0 keeps exactly candidate_limit (Phase 16 cap and the
        # byte-identical default path); a paged request widens the window to
        # max(candidate_limit, limit+offset) so the page slice below cannot
        # come back short or empty when that many candidates exist.
        if self.reranker is not None and len(results) > 0:
            if options.offset > 0:
                candidate_window = max(options.candidate_limit, options.limit + options.offset)
            else:
                candidate_window = options.candidate_limit
            candidates = results[:candidate_window]
            try:
                reranked = self.reranker.rerank(
                    parsed_query,
                    candidates,
                    top_k=options.limit + options.offset,
                )
                results = reranked
            except Exception as e:
                raise RuntimeError(f"Reranking failed: {e}") from e

        # Extract smart snippets if not already present
        results = self._apply_snippets(results, parsed_query)

        # One slice with the caller's original offset, then exactly one
        # enrichment on the page (CORR-03 offset ownership + CORR-05).
        return enrich_results(self.db, _paginate(results, options))

    def _apply_snippets(
        self,
        results: list[SearchResult],
        parsed_query: str,
    ) -> list[SearchResult]:
        """Extract smart snippets for results that do not carry one yet.

        The content fetch is transient: when include_content is False, the
        document text feeds snippet extraction only and is never written into
        SearchResult.content (--full stays the only content-returning path).
        """
        if self.snippet_extractor is None:
            return results
        query_terms = parsed_query.lower().split()
        for result in results:
            if result.snippet is not None:
                continue
            text = result.content
            if not text:
                text = self.hybrid._get_document_content(result.document_id)  # noqa: SLF001
            if text:
                result.snippet = self.snippet_extractor.extract(text, query_terms)
        return results

    def _default_search_type_enum(self) -> SearchType:
        """Resolve the configured default type for unprefixed/literal queries."""
        return {
            "bm25": SearchType.BM25,
            "vector": SearchType.VECTOR,
        }.get(self._default_search_type, SearchType.HYBRID)

    def _parse_query_prefix(self, query: str) -> tuple[str, SearchType]:
        """Parse query prefix to determine search mode.

        An explicit ``lex:``/``vec:``/``hyde:``/``expand:`` prefix always
        wins. Unprefixed queries fall back to the configured default search
        type (``hybrid`` unless ``SIF_DEFAULT_SEARCH_TYPE`` says otherwise).
        """
        prefix_map = {
            "lex:": SearchType.BM25,
            "vec:": SearchType.VECTOR,
            "hyde:": SearchType.HYDE,
            "expand:": SearchType.EXPAND,
        }
        for prefix, search_type in prefix_map.items():
            if query.startswith(prefix):
                return query[len(prefix) :].strip(), search_type
        return query, self._default_search_type_enum()

    def _generate_hypothetical_document(self, query: str) -> str:
        """Generate a hypothetical ideal answer document for HyDE search.

        Uses a lightweight prompt template approach. If the embedder supports text
        generation (e.g., GGUF models with .generate() or .create_completion()),
        it generates a short answer. Otherwise raises RuntimeError since HyDE
        requires text generation capability.
        """
        embedder = self.hybrid.embedder
        if embedder is None:
            raise RuntimeError("HyDE search requires an embedder")

        # Check if embedder has generate capability
        if hasattr(embedder, "generate"):
            prompt = (
                f"Answer the following question concisely and directly. "
                f"Provide only the answer, no preamble.\n\n"
                f"Question: {query}\n\nAnswer:"
            )
            generate = getattr(embedder, "generate")  # noqa: B009
            return cast(str, generate(prompt))

        # Check for llama-cpp style completion API
        if hasattr(embedder, "create_completion"):
            prompt = (
                f"Answer the following question concisely and directly. "
                f"Provide only the answer, no preamble.\n\n"
                f"Question: {query}\n\nAnswer:"
            )
            create_completion = getattr(embedder, "create_completion")  # noqa: B009
            result = create_completion(
                prompt,
                max_tokens=256,
                temperature=0.3,
                stop=["\n\n"],
            )
            return result["choices"][0]["text"].strip()

        # No text generation capability available
        raise RuntimeError(
            "HyDE search requires a text-generation-capable model (e.g., GGUF). "
            "The current embedder does not support .generate() or .create_completion(). "
            "Use vec: prefix for vector-only search instead.",
        )
