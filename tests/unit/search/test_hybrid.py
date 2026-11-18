"""Unit tests for hybrid search and search pipeline."""

import logging
import sqlite3
from typing import ClassVar
from unittest.mock import MagicMock, create_autospec

import pytest

from sif.core.filters import parse_filter
from sif.core.models import SearchOptions, SearchResult, SearchType
from sif.embedding.identity import EmbedderIdentity
from sif.search.bm25 import BM25Searcher
from sif.search.hybrid import HybridSearcher, SearchPipeline
from sif.search.rerank import _sort_and_build_results
from sif.search.rrf import chunk_key, fuse_key_for
from sif.search.snippets import SmartSnippetExtractor
from sif.search.vector import VectorSearcher
from tests.support.bench import EMBEDDING_DIM, ConceptEmbedder


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_db():
    """Create a mock sqlite3 connection."""
    return MagicMock()


def test_default_search_type_bm25_routes_unprefixed_query(mock_db):
    """SIF_DEFAULT_SEARCH_TYPE=bm25 routes an unprefixed query to BM25."""
    pipeline = SearchPipeline(mock_db, default_search_type="bm25")
    pipeline.hybrid.bm25.search = MagicMock(return_value=[])

    pipeline.search("plain query", SearchOptions())

    pipeline.hybrid.bm25.search.assert_called_once()


def test_default_search_type_hybrid_keeps_unprefixed_query_hybrid(mock_db):
    """The default hybrid fallback still goes through HybridSearcher."""
    pipeline = SearchPipeline(mock_db)
    pipeline.hybrid.search = MagicMock(return_value=[])

    pipeline.search("plain query", SearchOptions())

    pipeline.hybrid.search.assert_called_once()


@pytest.fixture
def mock_embedder():
    """Create a mock embedder."""
    embedder = MagicMock()
    embedder.embed.return_value = [0.1] * 384
    embedder.dimension = 384
    return embedder


@pytest.fixture
def sample_search_options() -> SearchOptions:
    """Create sample search options."""
    return SearchOptions(limit=10)


@pytest.fixture
def bm25_results() -> list[SearchResult]:
    """Create sample BM25 search results."""
    return [
        SearchResult(
            document_id="doc-A",
            path="/path/to/doc_a.md",
            title="Document A",
            collection_name="default",
            score=0.95,
        ),
        SearchResult(
            document_id="doc-B",
            path="/path/to/doc_b.md",
            title="Document B",
            collection_name="default",
            score=0.87,
        ),
    ]


@pytest.fixture
def vector_results() -> list[SearchResult]:
    """Create sample vector search results."""
    return [
        SearchResult(
            document_id="doc-A",
            path="/path/to/doc_a.md",
            title="Document A",
            collection_name="default",
            score=0.92,
        ),
        SearchResult(
            document_id="doc-C",
            path="/path/to/doc_c.md",
            title="Document C",
            collection_name="default",
            score=0.88,
        ),
    ]


# =============================================================================
# HybridSearcher Tests
# =============================================================================


class TestHybridSearcher:
    """Test HybridSearcher basic functionality."""

    def test_hybrid_search_with_embedder(
        self,
        mock_db: MagicMock,
        mock_embedder: MagicMock,
    ) -> None:
        """Test that hybrid search uses both BM25 and vector when embedder available."""
        hybrid = HybridSearcher(mock_db, embedder=mock_embedder, embedding_dim=384)
        assert hybrid.embedder is mock_embedder
        assert hybrid.bm25 is not None
        assert hybrid.vector is not None

    def test_hybrid_search_without_embedder(
        self,
        mock_db: MagicMock,
    ) -> None:
        """Test that hybrid search falls back to BM25 without embedder."""
        hybrid = HybridSearcher(mock_db, embedder=None, embedding_dim=384)
        assert hybrid.embedder is None

    def test_hybrid_searcher_has_search_method(
        self,
        mock_db: MagicMock,
    ) -> None:
        """Test that HybridSearcher has search method."""
        hybrid = HybridSearcher(mock_db)
        assert hasattr(hybrid, "search")
        assert callable(hybrid.search)


# =============================================================================
# SearchPipeline Tests
# =============================================================================


class TestSearchPipelinePrefixRouting:
    """Test SearchPipeline query prefix routing."""

    def test_parse_query_prefix_lex(self) -> None:
        """Test lex: prefix routes to BM25."""
        pipeline = SearchPipeline(MagicMock())
        query, search_type = pipeline._parse_query_prefix("lex: python tutorial")
        assert query == "python tutorial"
        assert search_type == SearchType.BM25

    def test_parse_query_prefix_vec(self) -> None:
        """Test vec: prefix routes to vector."""
        pipeline = SearchPipeline(MagicMock())
        query, search_type = pipeline._parse_query_prefix("vec: neural networks")
        assert query == "neural networks"
        assert search_type == SearchType.VECTOR

    def test_parse_query_prefix_hyde(self) -> None:
        """Test hyde: prefix routes to HyDE."""
        pipeline = SearchPipeline(MagicMock())
        query, search_type = pipeline._parse_query_prefix("hyde: machine learning")
        assert query == "machine learning"
        assert search_type == SearchType.HYDE

    def test_parse_query_prefix_expand(self) -> None:
        """Test expand: prefix routes to expansion."""
        pipeline = SearchPipeline(MagicMock())
        query, search_type = pipeline._parse_query_prefix("expand: search tips")
        assert query == "search tips"
        assert search_type == SearchType.EXPAND

    def test_parse_query_prefix_default(self) -> None:
        """Test default query routes to hybrid."""
        pipeline = SearchPipeline(MagicMock())
        query, search_type = pipeline._parse_query_prefix("python tutorial")
        assert query == "python tutorial"
        assert search_type == SearchType.HYBRID

    def test_pipeline_prefix_lex_routes_to_bm25(
        self,
        mock_db: MagicMock,
    ) -> None:
        """Test that lex: prefix uses BM25Searcher only."""
        pipeline = SearchPipeline(mock_db)
        pipeline.hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        pipeline.hybrid.bm25.search.return_value = [
            SearchResult(
                document_id="doc-1",
                path="/test.md",
                title="Test",
                collection_name="default",
                score=0.9,
            ),
        ]

        results = pipeline.search("lex: test query")

        pipeline.hybrid.bm25.search.assert_called_once()
        assert len(results) == 1
        assert results[0].document_id == "doc-1"

    def test_pipeline_prefix_vec_raises_without_embedder(
        self,
        mock_db: MagicMock,
    ) -> None:
        """Test that vec: prefix raises when embedder is missing."""
        pipeline = SearchPipeline(mock_db)

        with pytest.raises(RuntimeError, match="Vector search requires an embedder"):
            pipeline.search("vec: test query")

    def test_pipeline_prefix_hyde_raises_without_generate(
        self,
        mock_db: MagicMock,
    ) -> None:
        """Test that hyde: prefix raises when embedder lacks generation."""
        mock_embedder = MagicMock(spec=["embed", "dimension"])
        mock_embedder.embed.return_value = [0.1] * 384
        mock_embedder.dimension = 384

        pipeline = SearchPipeline(mock_db, embedder=mock_embedder)

        with pytest.raises(
            RuntimeError,
            match="HyDE search requires a text-generation-capable model",
        ):
            pipeline.search("hyde: test query")


class TestSearchPipelineExpansion:
    """Test SearchPipeline query expansion."""

    def test_pipeline_with_expansion(
        self,
        mock_db: MagicMock,
        mock_embedder: MagicMock,
    ) -> None:
        """Test pipeline with query expansion fuses multiple queries."""
        mock_expander = MagicMock()
        mock_expander.expand.return_value = ["query", "query variant"]

        pipeline = SearchPipeline(
            mock_db,
            embedder=mock_embedder,
            query_expander=mock_expander,
        )
        pipeline.hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        pipeline.hybrid.bm25.search.return_value = [
            SearchResult(
                document_id="doc-1",
                path="/test.md",
                title="Test",
                collection_name="default",
                score=0.9,
            ),
        ]

        _results = pipeline.search("query", SearchOptions(limit=5))

        assert mock_expander.expand.called
        assert pipeline.hybrid.bm25.search.call_count == 2

    def test_pipeline_expansion_deduplicates(
        self,
        mock_db: MagicMock,
        mock_embedder: MagicMock,
    ) -> None:
        """Test that expansion deduplicates repeated variants."""
        mock_expander = MagicMock()
        mock_expander.expand.return_value = ["query", "query", "QUERY", "variant"]

        pipeline = SearchPipeline(
            mock_db,
            embedder=mock_embedder,
            query_expander=mock_expander,
        )
        pipeline.hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        pipeline.hybrid.bm25.search.return_value = []

        pipeline.search("query")

        # Should only search twice (original + one truly unique variant)
        assert pipeline.hybrid.bm25.search.call_count == 2

    def test_pipeline_expansion_without_original_echo(
        self,
        mock_db: MagicMock,
        mock_embedder: MagicMock,
    ) -> None:
        """A conforming expander that does not echo the original keeps all variants."""
        mock_expander = MagicMock()
        mock_expander.expand.return_value = ["variant1", "variant2"]

        pipeline = SearchPipeline(
            mock_db,
            embedder=mock_embedder,
            query_expander=mock_expander,
        )
        pipeline.hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        pipeline.hybrid.bm25.search.return_value = []

        pipeline.search("query")

        # Original + both variants: none of the variants is dropped.
        assert pipeline.hybrid.bm25.search.call_count == 3


class TestSearchPipelineReranking:
    """Test SearchPipeline reranking."""

    def test_pipeline_with_reranker(
        self,
        mock_db: MagicMock,
    ) -> None:
        """Test pipeline with reranker reorders results."""
        mock_reranker = MagicMock()
        mock_reranker.rerank.return_value = [
            SearchResult(
                document_id="doc-2",
                path="/b.md",
                title="B",
                collection_name="default",
                score=0.99,
                rank=1,
            ),
            SearchResult(
                document_id="doc-1",
                path="/a.md",
                title="A",
                collection_name="default",
                score=0.95,
                rank=2,
            ),
        ]

        pipeline = SearchPipeline(mock_db, reranker=mock_reranker)
        pipeline.hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        pipeline.hybrid.bm25.search.return_value = [
            SearchResult(
                document_id="doc-1",
                path="/a.md",
                title="A",
                collection_name="default",
                score=0.9,
            ),
            SearchResult(
                document_id="doc-2",
                path="/b.md",
                title="B",
                collection_name="default",
                score=0.8,
            ),
        ]

        results = pipeline.search("test", SearchOptions(candidate_limit=10))

        mock_reranker.rerank.assert_called_once()
        assert results[0].document_id == "doc-2"
        assert results[0].rank == 1

    def test_pipeline_candidate_limit(
        self,
        mock_db: MagicMock,
    ) -> None:
        """Test that only candidate_limit results go to reranker."""
        mock_reranker = MagicMock()
        mock_reranker.rerank.return_value = []

        pipeline = SearchPipeline(mock_db, reranker=mock_reranker)
        pipeline.hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        pipeline.hybrid.bm25.search.return_value = [
            SearchResult(
                document_id=f"doc-{i}",
                path=f"/{i}.md",
                title=f"Doc {i}",
                collection_name="default",
                score=0.9 - i * 0.01,
            )
            for i in range(10)
        ]

        pipeline.search("test", SearchOptions(candidate_limit=5))

        # Reranker should only receive 5 candidates
        passed_results = mock_reranker.rerank.call_args[0][1]
        assert len(passed_results) == 5


class TestSearchPipelineExplain:
    """Test SearchPipeline explainability / score preservation."""

    def test_explain_preserves_scores(
        self,
        mock_db: MagicMock,
        mock_embedder: MagicMock,
    ) -> None:
        """Test that scores dict contains bm25_score and vector_score via RRF."""
        pipeline = SearchPipeline(mock_db, embedder=mock_embedder)
        pipeline.hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        pipeline.hybrid.bm25.search.return_value = [
            SearchResult(
                document_id="doc-1",
                path="/a.md",
                title="A",
                collection_name="default",
                score=0.95,
            ),
        ]
        pipeline.hybrid.vector = create_autospec(VectorSearcher, instance=True)
        pipeline.hybrid.vector.search.return_value = [
            SearchResult(
                document_id="doc-1",
                path="/a.md",
                title="A",
                collection_name="default",
                score=0.92,
            ),
        ]

        results = pipeline.search("test", SearchOptions(explain=True))

        assert len(results) == 1
        assert "bm25_score" in results[0].scores
        assert "vector_score" in results[0].scores
        assert "rrf_score" in results[0].scores


class TestSearchPipelineIntent:
    """Test SearchPipeline intent propagation."""

    def test_intent_prepended_to_query(
        self,
        mock_db: MagicMock,
    ) -> None:
        """Test that intent is prepended to parsed query."""
        pipeline = SearchPipeline(mock_db)
        pipeline.hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        pipeline.hybrid.bm25.search.return_value = []

        pipeline.search("test", SearchOptions(intent="code"))

        call_args = pipeline.hybrid.bm25.search.call_args
        assert call_args is not None
        passed_query = call_args[0][0]
        assert passed_query == "code: test"


class TestHybridContextAttachment:
    """Single-owner enrichment: the searcher is raw, the pipeline attaches once."""

    def test_hybrid_search_returns_raw_results(self, mock_db: MagicMock) -> None:
        """HybridSearcher.search does not attach contexts or staleness itself."""
        embedder = MagicMock()
        embedder.embed.return_value = [0.1, 0.2]
        hybrid = HybridSearcher(mock_db, embedder=embedder, embedding_dim=384)
        hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        hybrid.bm25.search.return_value = [
            SearchResult(
                document_id="doc-1",
                path="/a.md",
                title="A",
                collection_name="default",
                score=0.95,
                context_description="BM25 context",
            ),
        ]
        hybrid.vector = create_autospec(VectorSearcher, instance=True)
        hybrid.vector.search.return_value = [
            SearchResult(
                document_id="doc-1",
                path="/a.md",
                title="A",
                collection_name="default",
                score=0.92,
                context_description="Vector context",
            ),
        ]
        mock_db.reset_mock()

        results = hybrid.search("test")

        assert len(results) == 1
        # Fused source fields survive untouched; no attach scan runs here.
        assert results[0].context_description in ("BM25 context", "Vector context")
        assert not hasattr(hybrid, "_attach_contexts")
        mock_db.execute.assert_not_called()

    def test_pipeline_search_attaches_context_after_reranking(
        self,
        mock_db: MagicMock,
        monkeypatch,
    ) -> None:
        """The pipeline user sees reranked contexts after exactly one enrichment."""
        reranked = [
            SearchResult(
                document_id="doc-1",
                path="/a.md",
                title="A",
                collection_name="default",
                score=0.99,
                rank=1,
                context_description="Reranked context",
            ),
        ]
        mock_reranker = MagicMock()
        mock_reranker.rerank.return_value = reranked

        calls: list[tuple[object, list[SearchResult]]] = []

        def recording_enrich(db, results):
            calls.append((db, results))
            return results

        monkeypatch.setattr("sif.search.hybrid.enrich_results", recording_enrich)

        pipeline = SearchPipeline(mock_db, reranker=mock_reranker)
        pipeline.hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        pipeline.hybrid.bm25.search.return_value = [
            SearchResult(
                document_id="doc-1",
                path="/a.md",
                title="A",
                collection_name="default",
                score=0.9,
                context_description="Original context",
            ),
        ]

        results = pipeline.search("test", SearchOptions(candidate_limit=10))

        mock_reranker.rerank.assert_called_once()
        assert len(calls) == 1
        assert calls[0][0] is mock_db
        # CORR-03: the pipeline owns the one offset slice, so enrichment sees
        # the sliced page list (same rows at offset=0) rather than the raw
        # reranker list object.
        assert calls[0][1] is results
        assert [r.document_id for r in calls[0][1]] == [r.document_id for r in reranked]
        assert results[0].context_description == "Reranked context"

    def test_pipeline_hybrid_exit_enriches_contexts_and_staleness(self) -> None:
        """Hybrid pipeline exit attaches legacy-verbatim contexts and staleness.

        The context row stores the verbatim target (normalized on read, never
        pre-filtered in SQL); the purged d4 embedding arms the derived marker
        for a BM25-only hit while the still-embedded docs stay unmarked.
        """
        conn = TestHybridSC1PipelineGolden._build_db()
        try:
            conn.execute(
                "INSERT INTO contexts (id, target_id, context_type, content,"
                " created_at, updated_at) VALUES ('ctx-1', '/notes/gardening.md', 'path',"
                " 'Garden project notes', '2026-01-01T00:00:00', '2026-01-01T00:00:00')"
            )
            # d4 still matches BM25 but has no embedding row: the real lag
            # state. Route the delete through the searcher so the derived
            # shadow stays truthful (CORR-06 D-09), never raw vec0 SQL.
            VectorSearcher(conn, embedding_dim=2).delete_embeddings_by_document("d4")

            pipeline = SearchPipeline(conn, embedder=_FakeEmbedder(), embedding_dim=2)
            results = pipeline.search("gardening", SearchOptions(limit=5))

            hit = next(r for r in results if r.document_id == "d4")
            assert hit.context_description == "Garden project notes"
            assert hit.vectors_stale is True
            assert all(r.vectors_stale is False for r in results if r.document_id != "d4")
        finally:
            conn.close()


class TestPipelineSnippetRoutes:
    """Snippet extraction on the lex:/vec:/hyde: prefix routes.

    Inverts the 04-VERIFICATION.md E2E failure where lex: with content
    returned snippet=None because the early-return routes bypassed the
    snippet stage entirely.
    """

    CONTENT = (
        "Python decorators wrap functions. Decorators use the @ syntax. "
        "A decorator takes a callable and returns a callable."
    )

    def _stub_content_feed(self, pipeline: SearchPipeline) -> MagicMock:
        """Stub the transient content feed so no real database is needed."""
        feed = MagicMock(return_value=self.CONTENT)
        pipeline.hybrid._get_document_content = feed
        return feed

    def _result(self) -> SearchResult:
        """Build a content-less SearchResult as the searchers return it."""
        return SearchResult(
            document_id="doc-1",
            path="/test.md",
            title="Test",
            collection_name="default",
            score=0.9,
        )

    def test_lex_route_applies_snippets(self, mock_db: MagicMock) -> None:
        """lex: returns a snippet extracted from the fetched content."""
        pipeline = SearchPipeline(mock_db, snippet_extractor=SmartSnippetExtractor())
        self._stub_content_feed(pipeline)
        pipeline.hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        pipeline.hybrid.bm25.search.return_value = [self._result()]

        results = pipeline.search("lex: decorators")

        assert results[0].snippet is not None
        assert "decorator" in results[0].snippet.lower()
        assert results[0].content is None  # include_content defaults to False

    def test_vec_route_applies_snippets(
        self,
        mock_db: MagicMock,
        mock_embedder: MagicMock,
    ) -> None:
        """vec: returns a snippet extracted from the fetched content."""
        pipeline = SearchPipeline(
            mock_db,
            embedder=mock_embedder,
            snippet_extractor=SmartSnippetExtractor(),
        )
        self._stub_content_feed(pipeline)
        pipeline.hybrid.vector = create_autospec(VectorSearcher, instance=True)
        pipeline.hybrid.vector.search.return_value = [self._result()]

        results = pipeline.search("vec: decorators")

        assert results[0].snippet is not None
        assert "decorator" in results[0].snippet.lower()
        assert results[0].content is None

    def test_hyde_route_applies_snippets(self, mock_db: MagicMock) -> None:
        """hyde: returns a snippet extracted from the fetched content."""
        mock_embedder = MagicMock(spec=["embed", "generate", "dimension"])
        mock_embedder.embed.return_value = [0.1] * 384
        mock_embedder.generate.return_value = "Decorators wrap a function call."

        pipeline = SearchPipeline(
            mock_db,
            embedder=mock_embedder,
            snippet_extractor=SmartSnippetExtractor(),
        )
        self._stub_content_feed(pipeline)
        pipeline.hybrid.vector = create_autospec(VectorSearcher, instance=True)
        pipeline.hybrid.vector.search.return_value = [self._result()]

        results = pipeline.search("hyde: decorators")

        assert results[0].snippet is not None
        assert "decorator" in results[0].snippet.lower()
        assert results[0].content is None

    def test_existing_snippet_not_reextracted(self, mock_db: MagicMock) -> None:
        """A result already carrying a snippet skips extractor invocation."""
        extractor = MagicMock(spec=SmartSnippetExtractor)
        pipeline = SearchPipeline(mock_db, snippet_extractor=extractor)
        self._stub_content_feed(pipeline)
        pipeline.hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        preset = self._result()
        preset.snippet = "preexisting snippet"
        pipeline.hybrid.bm25.search.return_value = [preset]

        results = pipeline.search("lex: decorators")

        extractor.extract_with_range.assert_not_called()
        extractor.extract.assert_not_called()
        assert results[0].snippet == "preexisting snippet"

    def test_apply_snippets_fills_snippet_and_line_fields_together(
        self, mock_db: MagicMock
    ) -> None:
        """D-11: one pass assigns the snippet bytes and its line window.

        Ordering and scores are untouched, and the assigned snippet is
        byte-identical to the extractor's own output.
        """
        extractor = SmartSnippetExtractor()
        pipeline = SearchPipeline(mock_db, snippet_extractor=extractor)
        self._stub_content_feed(pipeline)
        pipeline.hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        first = self._result()
        second = SearchResult(
            document_id="doc-2",
            path="/other.md",
            title="Other",
            collection_name="default",
            score=0.5,
        )
        pipeline.hybrid.bm25.search.return_value = [first, second]

        results = pipeline.search("lex: decorators")
        expected = extractor.extract(self.CONTENT, ["decorators"])

        for result in results:
            assert result.snippet == expected
            assert result.line_start == 1
            assert result.line_end == 1
        assert [r.document_id for r in results] == ["doc-1", "doc-2"]
        assert [r.score for r in results] == [0.9, 0.5]

    def test_empty_snippet_leaves_line_fields_unset(self, mock_db: MagicMock) -> None:
        """An empty snippet keeps CLI bytes but never claims a line window."""
        pipeline = SearchPipeline(mock_db, snippet_extractor=SmartSnippetExtractor())
        pipeline.hybrid._get_document_content = MagicMock(return_value="\n\n```")
        pipeline.hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        pipeline.hybrid.bm25.search.return_value = [self._result()]

        results = pipeline.search("lex: decorators")

        assert results[0].snippet == ""
        assert results[0].line_start is None
        assert results[0].line_end is None

    def test_no_extractor_leaves_routes_unchanged(self, mock_db: MagicMock) -> None:
        """Without an extractor the snippet stage is a no-op on prefix routes."""
        pipeline = SearchPipeline(mock_db)
        feed = self._stub_content_feed(pipeline)
        pipeline.hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        pipeline.hybrid.bm25.search.return_value = [self._result()]

        results = pipeline.search("lex: decorators")

        assert results[0].snippet is None
        feed.assert_not_called()


# =============================================================================
# SC1 Pipeline Golden Tests (Phase 15 — byte-identical default fusion)
# =============================================================================


class _FakeEmbedder:
    """Deterministic embedder keyed on exact text (SC1 golden fixture)."""

    DOC_EMBEDDINGS: ClassVar[dict[str, list[float]]] = {
        "d1": [0.20, 0.90],
        "d2": [0.95, 0.10],
        "d3": [0.50, 0.50],
        "d4": [0.10, 0.20],
    }
    QUERY = "apple"
    QUERY_EMBEDDING: ClassVar[list[float]] = [1.0, 0.0]

    def embed(self, text: str) -> list[float]:
        """Map the fixture query to [1.0, 0.0]; docs to their fixed vectors."""
        if text == self.QUERY:
            return self.QUERY_EMBEDDING
        return self.DOC_EMBEDDINGS.get(text, [0.0, 1.0])


class TestHybridSC1PipelineGolden:
    """SC1: the post-dedup default contract, pinned field-for-field.

    The snapshot below was regenerated from the post-CORR-02 code on this
    exact fixture (real schema + FTS + vec0, deterministic fake embedder) on
    2026-11-15. The default contract changed from pre-dedup fusion to one row
    per document: the vector leg now dedups before fusion, so duplicate chunk
    hits can no longer consume result slots or inflate RRF scores. On this
    one-chunk-per-document fixture the scores are unchanged from the previous
    golden; the chunk_id/sequence/chunk_matches fields record the new
    per-document contract, and dual-leg rows adopt the vector leg's chunk
    identity through the RRF metadata merge. Both the implicit defaults and
    the explicit ``SearchOptions(rrf_k=60, bm25_weight=1.0, vector_weight=1.0)``
    must reproduce it field-for-field.

    CORR-04 title-column baseline (2026-11-15): the documents FTS index gained
    a ``title`` column and BM25 now binds equal 1.0/1.0 column weights, so
    title terms participate in lexical matching at the same weight as body
    terms. On this fixture only the two BM25-bearing rows moved
    (d3 0.9999989753435158 -> 0.9999986250018905, d1 0.9999990673325406 ->
    0.9999986865688892); the ranking, RRF scores, and vector scores are
    unchanged (title text repeats the body terms on these documents). The
    post-title-column values below are the new pinned contract; later
    weight changes (19-09) regenerate them again with their own rationale.

    D-12 outcome (19-09, 2026-11-15): the measured 2.0/3.0/4.0 title-weight
    candidates were rejected against B1 — the held-out title leg was already
    at its 1.0 ceiling and the body held-out leg did not move — so the pinned
    ``_TITLE_WEIGHT`` stays 1.0. This snapshot is therefore unchanged from the
    title-column values above; the verdict and per-candidate GateResult
    fields live in
    ``.planning/phases/19-search-correctness/bench/d12-verdict.json``.
    """

    SNAPSHOT: ClassVar[list[dict[str, object]]] = [
        {
            "document_id": "d3",
            "title": "Apple Quantum",
            "path": "/notes/apple-quantum.md",
            "collection_name": "notes",
            "score": 0.03252247488101534,
            "content": None,
            "highlights": ["apple quantum entangled fruit"],
            "rank": 1,
            "scores": {
                "bm25_score": 0.9999986250018905,
                "vector_score": 0.6464466154575348,
                "rrf_score": 0.03252247488101534,
            },
            "snippet": None,
            "context_description": None,
            "vectors_stale": False,
            "chunk_id": "chunk-d3",
            "sequence": 0,
            "chunk_matches": 1,
        },
        {
            "document_id": "d1",
            "title": "Apple Pie",
            "path": "/notes/apple-pie.md",
            "collection_name": "notes",
            "score": 0.031754032258064516,
            "content": None,
            "highlights": ["apple pie recipe sweet dessert"],
            "rank": 2,
            "scores": {
                "bm25_score": 0.9999986865688892,
                "vector_score": 0.39792025089263916,
                "rrf_score": 0.031754032258064516,
            },
            "snippet": None,
            "context_description": None,
            "vectors_stale": False,
            "chunk_id": "chunk-d1",
            "sequence": 0,
            "chunk_matches": 1,
        },
        {
            "document_id": "d2",
            "title": "Quantum Physics",
            "path": "/notes/quantum.md",
            "collection_name": "notes",
            "score": 0.01639344262295082,
            "content": None,
            "highlights": [],
            "rank": 3,
            "scores": {
                "vector_score": 0.9440982975065708,
                "rrf_score": 0.01639344262295082,
            },
            "snippet": None,
            "context_description": None,
            "vectors_stale": False,
            "chunk_id": "chunk-d2",
            "sequence": 0,
            "chunk_matches": 1,
        },
        {
            "document_id": "d4",
            "title": "Gardening",
            "path": "/notes/gardening.md",
            "collection_name": "notes",
            "score": 0.015873015873015872,
            "content": None,
            "highlights": [],
            "rank": 4,
            "scores": {
                "vector_score": 0.5390227735042572,
                "rrf_score": 0.015873015873015872,
            },
            "snippet": None,
            "context_description": None,
            "vectors_stale": False,
            "chunk_id": "chunk-d4",
            "sequence": 0,
            "chunk_matches": 1,
        },
    ]

    @staticmethod
    def _build_db() -> sqlite3.Connection:
        """Real in-memory DB: full schema, FTS via triggers, vec0 embeddings."""
        import sqlite_vec

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        try:
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)
        except Exception:
            conn.close()
            pytest.skip("sqlite-vec not available")

        from sif.database.schema import SchemaManager

        SchemaManager(conn, embedding_dim=2).create_all()
        now = "2026-11-08T00:00:00+00:00"
        conn.execute(
            "INSERT INTO collections (id, name, path, created_at, updated_at)"
            " VALUES ('c1', 'notes', '/notes', ?, ?)",
            (now, now),
        )
        docs = [
            ("d1", "Apple Pie", "/notes/apple-pie.md", "apple pie recipe sweet dessert"),
            ("d2", "Quantum Physics", "/notes/quantum.md", "quantum physics computing theory"),
            ("d3", "Apple Quantum", "/notes/apple-quantum.md", "apple quantum entangled fruit"),
            ("d4", "Gardening", "/notes/gardening.md", "unrelated gardening tips soil"),
        ]
        for did, title, path, content in docs:
            conn.execute(
                "INSERT INTO documents (id, collection_id, path, filename, title, content,"
                " checksum, mtime, created_at, updated_at) VALUES (?, 'c1', ?, ?, ?, ?, 'x',"
                " 1.0, ?, ?)",
                (did, path, path.split("/")[-1], title, content, now, now),
            )
            conn.execute(
                "INSERT INTO document_chunks (id, document_id, sequence, content, created_at)"
                " VALUES (?, ?, 0, ?, ?)",
                (f"chunk-{did}", did, content, now),
            )
        searcher = VectorSearcher(conn, embedding_dim=2)
        searcher.add_embeddings_batch(
            [
                (f"e-{did}", did, f"chunk-{did}", vec)
                for did, vec in _FakeEmbedder.DOC_EMBEDDINGS.items()
            ]
        )
        return conn

    def _search(self, options: SearchOptions) -> list[dict[str, object]]:
        conn = self._build_db()
        try:
            results = HybridSearcher(conn, embedder=_FakeEmbedder(), embedding_dim=2).search(
                _FakeEmbedder.QUERY,
                options,
            )
            return [r.to_dict() for r in results]
        finally:
            conn.close()

    def test_default_options_match_prechange_snapshot(self) -> None:
        """SC1: plain SearchOptions() reproduces the captured pre-change output."""
        assert self._search(SearchOptions()) == self.SNAPSHOT

    def test_explicit_default_weights_match_prechange_snapshot(self) -> None:
        """SC1: explicit rrf_k=60/bm25_weight=1.0/vector_weight=1.0 reproduces it too."""
        options = SearchOptions(rrf_k=60, bm25_weight=1.0, vector_weight=1.0)

        assert self._search(options) == self.SNAPSHOT

    def test_pipeline_weights_visibly_reorder_fused_ranking(self) -> None:
        """Weights honored end-to-end: heavy BM25 lifts the bm25-only doc.

        At limit=2 the sides are bm25=[d3,d1], vector=[d2,d3]. Defaults give
        d2 (vector rank 1) the second spot; bm25-heavy 5.0/0.2 lifts d1
        (bm25-only, 5/62) over d2 (0.2/61) — a visible reorder vs defaults
        and vs the vector-heavy ordering.
        """
        default_ids = [r["document_id"] for r in self._search(SearchOptions(limit=2))]
        bm25_heavy = [
            r["document_id"]
            for r in self._search(SearchOptions(limit=2, bm25_weight=5.0, vector_weight=0.2))
        ]
        vector_heavy = [
            r["document_id"]
            for r in self._search(SearchOptions(limit=2, bm25_weight=0.2, vector_weight=5.0))
        ]

        assert default_ids == ["d3", "d2"]
        assert bm25_heavy == ["d3", "d1"]
        assert bm25_heavy != vector_heavy

    def test_pipeline_k_changes_fused_scores_per_formula(self) -> None:
        """rrf_k honored end-to-end: d3 fuses to 1/2 + 1/3 at k=1 (accumulation order)."""
        k60 = self._search(SearchOptions(limit=2))
        k1 = self._search(SearchOptions(limit=2, rrf_k=1))

        assert k1[0]["document_id"] == "d3"
        assert k1[0]["scores"]["rrf_score"] == 1 / 2 + 1 / 3
        assert k60[0]["scores"]["rrf_score"] == 1 / 61 + 1 / 62


# =============================================================================
# Candidate fetch tests (Phase 16, D-10 — the cap must actually bind)
# =============================================================================


class _SpyReranker:
    """Record the query/candidate count/top_k a reranker receives, pass results through."""

    def __init__(self) -> None:
        self.query = ""
        self.seen = 0
        self.top_k = -1

    def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int = 10,
    ) -> list[SearchResult]:
        self.query = query
        self.seen = len(results)
        self.top_k = top_k
        return results[:top_k]


class TestCandidateFetch:
    """The rerank path over-fetches to max(limit + offset, candidate_limit).

    Before Phase 16 the fused list was at most options.limit (BM25 SQL-LIMITs
    to it, vector trims to it, RRF truncates at it), so a candidate_limit
    above limit could never bind — research Pitfall 1.
    """

    @staticmethod
    def _build_candidate_db() -> sqlite3.Connection:
        """Real in-memory DB with 20 apple-matching documents (BM25-only)."""
        import sqlite_vec

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        try:
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)
        except Exception:
            conn.close()
            pytest.skip("sqlite-vec not available")

        from sif.database.schema import SchemaManager

        SchemaManager(conn, embedding_dim=2).create_all()
        now = "2026-11-08T00:00:00+00:00"
        conn.execute(
            "INSERT INTO collections (id, name, path, created_at, updated_at)"
            " VALUES ('c1', 'notes', '/notes', ?, ?)",
            (now, now),
        )
        for i in range(20):
            did = f"d{i}"
            conn.execute(
                "INSERT INTO documents (id, collection_id, path, filename, title, content,"
                " checksum, mtime, created_at, updated_at) VALUES (?, 'c1', ?, ?, ?, ?, 'x',"
                " 1.0, ?, ?)",
                (
                    did,
                    f"/notes/n{i}.md",
                    f"n{i}.md",
                    f"Note {i}",
                    f"apple note number {i}",
                    now,
                    now,
                ),
            )
            conn.execute(
                "INSERT INTO document_chunks (id, document_id, sequence, content, created_at)"
                " VALUES (?, ?, 0, ?, ?)",
                (f"chunk-{did}", did, f"apple note number {i}", now),
            )
        return conn

    def test_candidate_fetch_reranker_receives_full_cap(self) -> None:
        """20 indexed docs, limit=3, candidate_limit=20 -> reranker receives 20, top_k=3."""
        conn = self._build_candidate_db()
        try:
            spy = _SpyReranker()
            pipeline = SearchPipeline(conn, reranker=spy)

            results = pipeline.search("apple", SearchOptions(limit=3, candidate_limit=20))

            assert spy.seen == 20
            assert spy.top_k == 3
            assert len(results) == 3
        finally:
            conn.close()

    def test_candidate_window_is_max_of_limit_offset_and_cap(
        self,
        mock_db: MagicMock,
    ) -> None:
        """Window = max(limit+offset, cap) for offset>0; cap alone at offset=0.

        The fetch limit reaches the searchers at offset=0; the reranker
        receives exactly the window and top_k = limit + offset.
        """
        cases = [
            # (limit, offset, cap) -> (fetch limit, candidate window, top_k)
            ((3, 2, 20), 20, 20, 5),
            ((10, 5, 12), 15, 15, 15),
            ((10, 20, 20), 30, 30, 30),
            ((10, 0, 20), 20, 20, 10),
        ]
        for (limit, offset, cap), fetch_limit, window, top_k in cases:
            spy = MagicMock()
            spy.rerank.return_value = []
            pipeline = SearchPipeline(mock_db, reranker=spy)
            pipeline.hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
            pipeline.hybrid.bm25.search.return_value = [
                SearchResult(
                    document_id=f"doc-{i}",
                    path=f"/{i}.md",
                    title=f"Doc {i}",
                    collection_name="default",
                    score=0.9 - i * 0.01,
                )
                for i in range(40)
            ]
            options = SearchOptions(limit=limit, offset=offset, candidate_limit=cap)

            pipeline.search("test", options)

            passed = pipeline.hybrid.bm25.search.call_args[0][1]
            assert passed.limit == fetch_limit
            assert passed.offset == 0
            handed = spy.rerank.call_args.args[1]
            assert len(handed) == window
            assert spy.rerank.call_args.kwargs["top_k"] == top_k
            # dataclasses.replace copies: the caller's options object is untouched.
            assert options.limit == limit
            assert options.offset == offset

    def test_candidate_fetch_cross_query_fuse_uses_fetch_limit(
        self,
        mock_db: MagicMock,
    ) -> None:
        """The cross-query variant fusion truncates at the fetch limit, not options.limit."""
        mock_expander = MagicMock()
        mock_expander.expand.return_value = ["variant"]
        spy = MagicMock()
        spy.rerank.return_value = []
        pipeline = SearchPipeline(
            mock_db,
            query_expander=mock_expander,
            reranker=spy,
        )
        variant_results = [
            SearchResult(
                document_id=f"doc-{i}",
                path=f"/{i}.md",
                title=f"Doc {i}",
                collection_name="default",
                score=0.9 - i * 0.01,
            )
            for i in range(5)
        ]
        pipeline.hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        pipeline.hybrid.bm25.search.return_value = variant_results
        pipeline.hybrid.rrf = MagicMock()
        pipeline.hybrid.rrf.fuse.return_value = variant_results

        pipeline.search("test", SearchOptions(limit=3, candidate_limit=20))

        assert pipeline.hybrid.rrf.fuse.call_args.args[1] == 20
        # CORR-02: the variant fuse always selects its grouping key through the
        # shared helper — None means the default document key.
        assert pipeline.hybrid.rrf.fuse.call_args.kwargs == {"k": 60, "key": None}

    def test_candidate_fetch_off_path_matches_sc1_snapshot(self) -> None:
        """reranker=None: no over-fetch, pipeline output equals the SC1 pre-change golden."""
        conn = TestHybridSC1PipelineGolden._build_db()
        try:
            pipeline = SearchPipeline(conn, embedder=_FakeEmbedder(), embedding_dim=2)

            results = pipeline.search(_FakeEmbedder.QUERY, SearchOptions())

            assert [r.to_dict() for r in results] == TestHybridSC1PipelineGolden.SNAPSHOT
        finally:
            conn.close()


# =============================================================================
# Composition proofs (Phase 16 — cap -> threshold -> top_k ordering)
# =============================================================================


# =============================================================================
# Offset pagination (CORR-03 — one slice owner, global ranks)
# =============================================================================


class TestHybridOffsetPagination:
    """HybridSearcher is the single slice owner for direct callers."""

    @staticmethod
    def _results(count: int) -> list[SearchResult]:
        return [
            SearchResult(
                document_id=f"doc-{i}",
                path=f"/{i}.md",
                title=f"Doc {i}",
                collection_name="default",
                score=0.9 - i * 0.01,
            )
            for i in range(count)
        ]

    def test_bm25_only_early_return_is_paginated(self, mock_db: MagicMock) -> None:
        """The BM25-only early return slices and ranks globally too."""
        hybrid = HybridSearcher(mock_db, embedder=None, embedding_dim=2)
        hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        hybrid.bm25.search.return_value = self._results(10)

        results = hybrid.search("test", SearchOptions(limit=2, offset=2))

        passed = hybrid.bm25.search.call_args[0][1]
        assert passed.limit == 4
        assert passed.offset == 0
        assert [r.document_id for r in results] == ["doc-2", "doc-3"]
        assert [r.rank for r in results] == [3, 4]

    def test_vector_only_early_return_is_paginated(self, mock_db: MagicMock) -> None:
        """The vector-only early return slices and ranks globally too."""
        embedder = MagicMock()
        embedder.embed.return_value = [0.1, 0.2]
        hybrid = HybridSearcher(mock_db, embedder=embedder, embedding_dim=2)
        hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        hybrid.bm25.search.return_value = []
        hybrid.vector = create_autospec(VectorSearcher, instance=True)
        hybrid.vector.search.return_value = self._results(10)

        results = hybrid.search("test", SearchOptions(limit=2, offset=2))

        passed = hybrid.vector.search.call_args[0][1]
        assert passed.limit == 4
        assert passed.offset == 0
        assert [r.document_id for r in results] == ["doc-2", "doc-3"]
        assert [r.rank for r in results] == [3, 4]

    def test_fused_path_slices_once_and_ranks_globally(self, mock_db: MagicMock) -> None:
        """Both legs fetch the offset-free window; one slice follows fusion."""
        embedder = MagicMock()
        embedder.embed.return_value = [0.1, 0.2]
        hybrid = HybridSearcher(mock_db, embedder=embedder, embedding_dim=2)
        hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        hybrid.bm25.search.return_value = self._results(6)
        hybrid.vector = create_autospec(VectorSearcher, instance=True)
        hybrid.vector.search.return_value = self._results(6)
        hybrid.rrf = MagicMock()
        hybrid.rrf.fuse.return_value = self._results(6)

        results = hybrid.search("test", SearchOptions(limit=2, offset=2))

        assert hybrid.rrf.fuse.call_args.args[1] == 4
        assert hybrid.bm25.search.call_args[0][1].offset == 0
        assert hybrid.vector.search.call_args[0][1].offset == 0
        assert [r.document_id for r in results] == ["doc-2", "doc-3"]
        assert [r.rank for r in results] == [3, 4]


class TestPipelineOffsetPagination:
    """The pipeline calls hybrid with offset=0 and owns the caller's slice."""

    def test_pipeline_passes_offset_zero_and_slices_with_original_offset(
        self,
        mock_db: MagicMock,
    ) -> None:
        pipeline = SearchPipeline(mock_db)
        pipeline.hybrid.search = MagicMock(return_value=TestHybridOffsetPagination._results(6))

        results = pipeline.search("test", SearchOptions(limit=2, offset=2))

        passed = pipeline.hybrid.search.call_args[0][1]
        assert passed.limit == 4
        assert passed.offset == 0
        assert [r.document_id for r in results] == ["doc-2", "doc-3"]
        assert [r.rank for r in results] == [3, 4]


class _ThresholdRerankSpy:
    """Apply the production relative-threshold filter, recording the hand-off."""

    def __init__(self, alpha: float) -> None:
        self.alpha = alpha
        self.query = ""
        self.received = 0
        self.top_k = -1

    def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int = 10,
    ) -> list[SearchResult]:
        self.query = query
        self.received = len(results)
        self.top_k = top_k
        return _sort_and_build_results(
            results,
            [float(r.score) for r in results],
            top_k,
            self.alpha,
        )


class TestRerankComposition:
    """Pin the layer ordering end-to-end: cap first, threshold second, top_k last."""

    @staticmethod
    def _results(scores: list[float]) -> list[SearchResult]:
        return [
            SearchResult(
                document_id=f"doc-{i}",
                path=f"/{i}.md",
                title=f"Doc {i}",
                collection_name="default",
                score=score,
            )
            for i, score in enumerate(scores)
        ]

    def _pipeline_with_spy(
        self,
        mock_db: MagicMock,
        spy: _ThresholdRerankSpy,
        scores: list[float],
    ) -> SearchPipeline:
        pipeline = SearchPipeline(mock_db, reranker=spy)
        pipeline.hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        pipeline.hybrid.bm25.search.return_value = self._results(scores)
        return pipeline

    def test_cap_then_threshold_then_top_k_ordering(self, mock_db: MagicMock) -> None:
        """Equal-score candidates: cap hands exactly candidate_limit, threshold keeps
        >= top1 * alpha, and the final count is min(top_k, survivors)."""
        # 25 candidates; first 10 carry equal scores (doc-1/doc-2 both 0.8).
        scores = [1.0, 0.8, 0.8, 0.7, 0.6, *([0.1] * 20)]
        spy = _ThresholdRerankSpy(alpha=0.5)
        pipeline = self._pipeline_with_spy(mock_db, spy, scores)

        results = pipeline.search("test", SearchOptions(limit=3, candidate_limit=10))

        assert spy.received == 10  # cap: exactly candidate_limit candidates handed over
        assert spy.top_k == 3
        assert len(results) == 3  # min(top_k=3, survivors=5)
        assert [r.document_id for r in results] == ["doc-0", "doc-1", "doc-2"]

    def test_threshold_survivors_below_top_k_return_all_survivors(
        self,
        mock_db: MagicMock,
    ) -> None:
        """Fewer survivors than top_k: the final count is min(top_k, survivors)."""
        scores = [1.0, 0.6, *([0.1] * 23)]  # cutoff 0.5 -> survivors doc-0, doc-1
        spy = _ThresholdRerankSpy(alpha=0.5)
        pipeline = self._pipeline_with_spy(mock_db, spy, scores)

        results = pipeline.search("test", SearchOptions(limit=3, candidate_limit=10))

        assert len(results) == 2  # min(top_k=3, survivors=2)
        assert [r.document_id for r in results] == ["doc-0", "doc-1"]

    def test_off_path_passes_offset_zero_window_without_overfetch(
        self,
        mock_db: MagicMock,
    ) -> None:
        """reranker=None: hybrid is called with a copy at offset=0, caller untouched."""
        pipeline = SearchPipeline(mock_db)
        pipeline.hybrid.search = MagicMock(return_value=[])
        options = SearchOptions(limit=3, candidate_limit=20)

        pipeline.search("test", options)

        passed = pipeline.hybrid.search.call_args[0][1]
        assert passed is not options
        assert passed.limit == 3
        assert passed.offset == 0
        assert options.limit == 3
        assert options.offset == 0


# =============================================================================
# Per-chunk fusion (CORR-02 — chunk identity through both fuse sites)
# =============================================================================


class _VariantExpander:
    """Stub QueryExpander that returns the original plus one variant."""

    def expand(self, _query: str) -> list[str]:
        """Return a deterministic two-variant expansion."""
        return ["alpha", "alpha beta"]


class TestHybridChunkFusion:
    """Chunk identity survives both fuse sites; per-chunk mode restores rows."""

    @staticmethod
    def _doc_result(document_id: str, score: float) -> SearchResult:
        return SearchResult(
            document_id=document_id,
            title=f"Doc {document_id}",
            path=f"/{document_id}.md",
            collection_name="c",
            score=score,
        )

    @staticmethod
    def _chunk_result(
        document_id: str,
        chunk_id: str,
        sequence: int,
        score: float,
        chunk_matches: int = 1,
    ) -> SearchResult:
        return SearchResult(
            document_id=document_id,
            title=f"Doc {document_id}",
            path=f"/{document_id}.md",
            collection_name="c",
            score=score,
            chunk_id=chunk_id,
            sequence=sequence,
            chunk_matches=chunk_matches,
        )

    @staticmethod
    def _hybrid_with_stub_legs(
        bm25_results: list[SearchResult],
        vector_results: list[SearchResult],
    ) -> HybridSearcher:
        embedder = MagicMock()
        embedder.embed.return_value = [0.1, 0.2]
        hybrid = HybridSearcher(MagicMock(), embedder=embedder, embedding_dim=2)
        hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        hybrid.bm25.search.return_value = bm25_results
        hybrid.vector = create_autospec(VectorSearcher, instance=True)
        hybrid.vector.search.return_value = vector_results
        return hybrid

    def test_dual_leg_document_keeps_vector_chunk_identity(self) -> None:
        """A document found by both legs adopts the vector chunk and max count."""
        hybrid = self._hybrid_with_stub_legs(
            [self._doc_result("d1", 0.9)],
            [self._chunk_result("d1", "chunk-2", 2, 0.8, chunk_matches=5)],
        )

        results = hybrid.search("q", SearchOptions(limit=10, include_highlights=False))

        assert len(results) == 1
        assert results[0].chunk_id == "chunk-2"
        assert results[0].sequence == 2
        assert results[0].chunk_matches == 5

    def test_per_chunk_mode_keeps_chunk_rows_and_document_row(self) -> None:
        """per_chunk=True fuses by chunk identity; BM25 rows stay document-keyed."""
        hybrid = self._hybrid_with_stub_legs(
            [self._doc_result("d1", 0.9)],
            [
                self._chunk_result("d1", "c1", 0, 0.8),
                self._chunk_result("d1", "c2", 1, 0.7),
            ],
        )

        results = hybrid.search(
            "q", SearchOptions(limit=10, per_chunk=True, include_highlights=False)
        )

        assert {(r.document_id, r.chunk_id) for r in results} == {
            ("d1", None),
            ("d1", "c1"),
            ("d1", "c2"),
        }

    def test_source_fusion_selects_the_shared_key_helper(self) -> None:
        """The source fuse gets key=None by default and chunk_key in per-chunk mode."""
        for per_chunk, expected in ((False, None), (True, chunk_key)):
            hybrid = self._hybrid_with_stub_legs(
                [self._doc_result("d1", 0.9)],
                [self._chunk_result("d1", "c1", 0, 0.8)],
            )
            hybrid.rrf = MagicMock()
            hybrid.rrf.fuse.return_value = []

            hybrid.search("q", SearchOptions(per_chunk=per_chunk, include_highlights=False))

            assert hybrid.rrf.fuse.call_args.kwargs["key"] is expected

    def test_pipeline_variant_fusion_selects_the_shared_key_helper(self) -> None:
        """The cross-query variant fuse receives the same per-chunk key."""
        for per_chunk, expected in ((False, None), (True, chunk_key)):
            pipeline = SearchPipeline(MagicMock(), query_expander=_VariantExpander())
            pipeline.hybrid.search = MagicMock(return_value=[self._doc_result("d1", 0.9)])
            pipeline.hybrid.rrf = MagicMock()
            pipeline.hybrid.rrf.fuse.return_value = []

            pipeline.search("alpha", SearchOptions(per_chunk=per_chunk))

            kwargs = pipeline.hybrid.rrf.fuse.call_args.kwargs
            assert kwargs["key"] is expected
            assert "weights" not in kwargs

    def test_fuse_key_for_is_the_shared_selection_point(self) -> None:
        """The helper is the single selector both fuse sites import."""
        assert fuse_key_for(False) is None
        assert fuse_key_for(True) is chunk_key

    def test_safety_net_merges_chunk_metadata(self) -> None:
        """The post-fusion dedup adopts a loser's chunk identity and max count."""
        winner = self._doc_result("d1", 0.02)
        loser = self._chunk_result("d1", "c2", 1, 0.01, chunk_matches=3)

        deduped = HybridSearcher._deduplicate_results([winner, loser])

        assert len(deduped) == 1
        assert deduped[0].chunk_id == "c2"
        assert deduped[0].sequence == 1
        assert deduped[0].chunk_matches == 3

    def test_safety_net_does_not_clear_existing_identity(self) -> None:
        """A loser without chunk identity never erases the winner's fields."""
        winner = self._chunk_result("d1", "c1", 0, 0.02, chunk_matches=3)
        loser = self._doc_result("d1", 0.01)

        deduped = HybridSearcher._deduplicate_results([winner, loser])

        assert deduped[0].chunk_id == "c1"
        assert deduped[0].sequence == 0
        assert deduped[0].chunk_matches == 3


class TestPerChunkPipelineMultiVariant:
    """A multi-variant pipeline search keeps chunk rows only in per-chunk mode."""

    @staticmethod
    def _build_db() -> sqlite3.Connection:
        """Real DB: one two-chunk document plus two single-chunk documents."""
        import sqlite_vec

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        try:
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)
        except Exception:
            conn.close()
            pytest.skip("sqlite-vec not available")

        from sif.database.schema import SchemaManager

        SchemaManager(conn, embedding_dim=EMBEDDING_DIM).create_all()
        now = "2026-11-15T00:00:00+00:00"
        conn.execute(
            "INSERT INTO collections (id, name, path, created_at, updated_at)"
            " VALUES ('c1', 'notes', '/notes', ?, ?)",
            (now, now),
        )
        embedder = ConceptEmbedder()
        docs = [
            (
                "d1",
                "alpha beta",
                [("chunk-d1-a", 0, "alpha"), ("chunk-d1-b", 1, "alpha beta")],
            ),
            ("d2", "alpha", [("chunk-d2-a", 0, "alpha")]),
            ("d3", "beta", [("chunk-d3-a", 0, "beta")]),
        ]
        embeddings: list[tuple[str, str, str, list[float]]] = []
        for doc_id, content, chunks in docs:
            conn.execute(
                "INSERT INTO documents (id, collection_id, path, filename, title, content,"
                " checksum, mtime, created_at, updated_at)"
                " VALUES (?, 'c1', ?, ?, ?, ?, 'x', 1.0, ?, ?)",
                (
                    doc_id,
                    f"/notes/{doc_id}.md",
                    f"{doc_id}.md",
                    f"Doc {doc_id}",
                    content,
                    now,
                    now,
                ),
            )
            for chunk_id, sequence, chunk_content in chunks:
                conn.execute(
                    "INSERT INTO document_chunks (id, document_id, sequence, content, created_at)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (chunk_id, doc_id, sequence, chunk_content, now),
                )
                embeddings.append(
                    (f"e-{chunk_id}", doc_id, chunk_id, embedder.embed(chunk_content))
                )
        VectorSearcher(conn, embedding_dim=EMBEDDING_DIM).add_embeddings_batch(embeddings)
        return conn

    @staticmethod
    def _options(per_chunk: bool) -> SearchOptions:
        return SearchOptions(
            limit=10,
            include_highlights=False,
            collection_ids=["c1"],
            per_chunk=per_chunk,
        )

    def test_multi_variant_per_chunk_keeps_both_chunk_rows(self) -> None:
        """Both chunk rows of the two-chunk document survive variant fusion."""
        conn = self._build_db()
        try:
            pipeline = SearchPipeline(
                conn,
                embedder=ConceptEmbedder(),
                query_expander=_VariantExpander(),
                embedding_dim=EMBEDDING_DIM,
            )

            per_chunk = pipeline.search("alpha", self._options(per_chunk=True))

            d1_chunk_ids = {
                r.chunk_id for r in per_chunk if r.document_id == "d1" and r.chunk_id is not None
            }
            assert {"chunk-d1-a", "chunk-d1-b"} <= d1_chunk_ids
            assert all(r.chunk_matches == 0 for r in per_chunk if r.chunk_id is not None)
        finally:
            conn.close()

    def test_multi_variant_default_returns_one_row_per_document(self) -> None:
        """The default multi-variant page is per-document and carries chunk identity."""
        conn = self._build_db()
        try:
            pipeline = SearchPipeline(
                conn,
                embedder=ConceptEmbedder(),
                query_expander=_VariantExpander(),
                embedding_dim=EMBEDDING_DIM,
            )

            results = pipeline.search("alpha", self._options(per_chunk=False))

            ids = [r.document_id for r in results]
            assert len(ids) == len(set(ids))
            d1 = next(r for r in results if r.document_id == "d1")
            assert d1.chunk_id is not None
            assert d1.chunk_matches >= 2
        finally:
            conn.close()


class TestFilterPassthrough:
    """Phase 20 (D-02/D-17): one AST reaches both legs before RRF.

    Filtering is structural in the hybrid path — ``dataclasses.replace``
    carries ``SearchOptions.filter`` into both leg calls, so no fusion or
    early-return branch can observe an unfiltered row.
    """

    @staticmethod
    def _results(ids: list[str]) -> list[SearchResult]:
        return [
            SearchResult(
                document_id=doc_id,
                path=f"/{doc_id}.md",
                title=doc_id,
                collection_name="default",
                score=0.9,
            )
            for doc_id in ids
        ]

    @staticmethod
    def _filter_node():
        """A representative selective AST (identity is what the tests assert)."""
        return parse_filter({"field": "tag", "operator": "eq", "value": "rare"})

    def test_both_legs_receive_the_same_ast_object(self, mock_db: MagicMock) -> None:
        """Each leg sees the caller's FilterNode instance, not a copy or None."""
        embedder = MagicMock()
        embedder.embed.return_value = [0.1, 0.2]
        hybrid = HybridSearcher(mock_db, embedder=embedder, embedding_dim=2)
        hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        hybrid.bm25.search.return_value = self._results(["doc-a"])
        hybrid.vector = create_autospec(VectorSearcher, instance=True)
        hybrid.vector.search.return_value = self._results(["doc-a"])
        hybrid.rrf = MagicMock()
        hybrid.rrf.fuse.return_value = self._results(["doc-a"])
        node = self._filter_node()

        hybrid.search("needle", SearchOptions(limit=5, filter=node))

        bm25_options = hybrid.bm25.search.call_args[0][1]
        vector_options = hybrid.vector.search.call_args[0][1]
        assert bm25_options.filter is node
        assert vector_options.filter is node

    def test_vector_empty_early_return_paginates_filtered_bm25_window(
        self, mock_db: MagicMock
    ) -> None:
        """The BM25-only early return slices the already-filtered window."""
        embedder = MagicMock()
        embedder.embed.return_value = [0.1, 0.2]
        hybrid = HybridSearcher(mock_db, embedder=embedder, embedding_dim=2)
        hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        hybrid.bm25.search.return_value = self._results(
            ["doc-0", "doc-1", "doc-2", "doc-3", "doc-4"]
        )
        hybrid.vector = create_autospec(VectorSearcher, instance=True)
        hybrid.vector.search.return_value = []
        node = self._filter_node()

        results = hybrid.search("needle", SearchOptions(limit=2, offset=2, filter=node))

        bm25_options = hybrid.bm25.search.call_args[0][1]
        assert bm25_options.filter is node
        assert bm25_options.limit == 4  # limit + offset, never widened
        assert bm25_options.offset == 0
        assert [r.document_id for r in results] == ["doc-2", "doc-3"]
        assert [r.rank for r in results] == [3, 4]

    def test_bm25_empty_early_return_paginates_filtered_vector_window(
        self, mock_db: MagicMock
    ) -> None:
        """The vector-only early return slices the already-filtered window."""
        embedder = MagicMock()
        embedder.embed.return_value = [0.1, 0.2]
        hybrid = HybridSearcher(mock_db, embedder=embedder, embedding_dim=2)
        hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        hybrid.bm25.search.return_value = []
        hybrid.vector = create_autospec(VectorSearcher, instance=True)
        hybrid.vector.search.return_value = self._results(
            ["doc-0", "doc-1", "doc-2", "doc-3", "doc-4"]
        )
        node = self._filter_node()

        results = hybrid.search("needle", SearchOptions(limit=2, offset=2, filter=node))

        vector_options = hybrid.vector.search.call_args[0][1]
        assert vector_options.filter is node
        assert vector_options.limit == 4  # limit + offset, never widened
        assert vector_options.offset == 0
        assert [r.document_id for r in results] == ["doc-2", "doc-3"]

    def test_fused_page_contains_only_filter_admitted_rows(self, mock_db: MagicMock) -> None:
        """Both stubbed legs honor the AST, so every fused row satisfies it."""
        embedder = MagicMock()
        embedder.embed.return_value = [0.1, 0.2]
        hybrid = HybridSearcher(mock_db, embedder=embedder, embedding_dim=2)
        corpus = self._results(["doc-a", "doc-b", "doc-c", "doc-d"])
        admitted = {"doc-a", "doc-b", "doc-c"}

        def _leg(_query: str, options: SearchOptions) -> list[SearchResult]:
            if options.filter is None:
                return list(corpus)
            return [result for result in corpus if result.document_id in admitted]

        hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        hybrid.bm25.search.side_effect = _leg
        hybrid.vector = create_autospec(VectorSearcher, instance=True)
        hybrid.vector.search.side_effect = _leg
        node = self._filter_node()

        results = hybrid.search("needle", SearchOptions(limit=10, filter=node))

        assert {r.document_id for r in results} <= admitted
        assert "doc-d" not in {r.document_id for r in results}

    def test_pipeline_propagates_filter_to_every_variant_and_enriches_once(
        self, mock_db: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Every query variant carries the AST; the exit still enriches once."""
        pipeline = SearchPipeline(mock_db)
        node = self._filter_node()
        seen: list[tuple[str, object]] = []

        def _hybrid_search(query: str, options: SearchOptions) -> list[SearchResult]:
            seen.append((query, options.filter))
            return self._results([f"doc-{query.replace(' ', '-')}"])

        pipeline.hybrid.search = MagicMock(side_effect=_hybrid_search)
        pipeline.query_expander = MagicMock()
        pipeline.query_expander.expand.return_value = ["variant one", "variant two"]
        enrich_calls: list[list[SearchResult]] = []

        def _enrich(_db, results: list[SearchResult]) -> list[SearchResult]:
            enrich_calls.append(results)
            return results

        monkeypatch.setattr("sif.search.hybrid.enrich_results", _enrich)

        pipeline.search("needle", SearchOptions(limit=2, filter=node))

        assert [query for query, _ in seen] == ["needle", "variant one", "variant two"]
        assert all(seen_filter is node for _, seen_filter in seen)
        assert len(enrich_calls) == 1

    def test_per_chunk_mode_keeps_filtered_chunk_rows(self, mock_db: MagicMock) -> None:
        """Per-chunk pages keep chunk rows; chunk_matches reflects filtered rows."""
        embedder = MagicMock()
        embedder.embed.return_value = [0.1, 0.2]
        hybrid = HybridSearcher(mock_db, embedder=embedder, embedding_dim=2)
        hybrid.bm25 = create_autospec(BM25Searcher, instance=True)
        hybrid.bm25.search.return_value = []
        chunk_rows = [
            SearchResult(
                document_id="doc-a",
                path="/a.md",
                title="a",
                collection_name="default",
                score=0.9,
                chunk_id="chunk-a1",
                sequence=0,
            ),
            SearchResult(
                document_id="doc-a",
                path="/a.md",
                title="a",
                collection_name="default",
                score=0.8,
                chunk_id="chunk-a2",
                sequence=1,
            ),
            SearchResult(
                document_id="doc-b",
                path="/b.md",
                title="b",
                collection_name="default",
                score=0.7,
                chunk_id="chunk-b1",
                sequence=0,
            ),
        ]
        hybrid.vector = create_autospec(VectorSearcher, instance=True)
        hybrid.vector.search.return_value = chunk_rows
        node = self._filter_node()

        results = hybrid.search("needle", SearchOptions(limit=10, per_chunk=True, filter=node))

        assert [(r.document_id, r.sequence) for r in results] == [
            ("doc-a", 0),
            ("doc-a", 1),
            ("doc-b", 0),
        ]
        # Per-chunk mode keeps rows ungrouped, so no row carries a group count;
        # the count only ever reflects the filtered vector rows it came from.
        assert all(result.chunk_matches == 0 for result in results)


# =============================================================================
# Embedder-identity enforcement (EMB-01/EMB-02, D-03/D-06)
# =============================================================================


def _identity(
    model_name: str = "model-a",
    *,
    dimension: int = 2,
    pooling: str = "mean",
    source: str = "verified",
) -> EmbedderIdentity:
    """Build a deterministic identity for the identity-policy tests."""
    from sif.embedding.identity import EmbedderIdentity

    return EmbedderIdentity(
        schema_version=1,
        cache_model_id=f"sentence_transformers:{model_name}",
        model_name=model_name,
        model_type="sentence_transformers",
        api_base=None,
        dimension=dimension,
        pooling=pooling,
        normalized=True,
        query_prompt=None,
        document_prompt=None,
        prompt_supported=False,
        revision=None,
        source=source,
    )


def _index_with_identity(identity: EmbedderIdentity) -> sqlite3.Connection:
    """Real schema + vectors + one stored identity (the swap fixture)."""
    from sif.embedding.identity import write_identity

    conn = TestHybridSC1PipelineGolden._build_db()
    with conn:
        write_identity(conn, identity)
    return conn


def _identity_warnings(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    """Identity-mismatch warnings captured from the identity logger."""
    return [
        record for record in caplog.records if "identity mismatch" in record.getMessage().lower()
    ]


class _RoleRecordingEmbedder:
    """Role-capable embedder: records query-role and plain embeds separately."""

    def __init__(self) -> None:
        self.query_calls: list[str] = []
        self.embed_calls: list[str] = []
        self.generated: list[str] = []

    def embed(self, text: str) -> list[float]:
        self.embed_calls.append(text)
        return [1.0, 0.0]

    def embed_query(self, text: str) -> list[float]:
        self.query_calls.append(text)
        return [1.0, 0.0]

    def generate(self, prompt: str) -> str:
        self.generated.append(prompt)
        return "apple answer"


class _PlainRecordingEmbedder(_FakeEmbedder):
    """Protocol-only double (no role method): records through plain ``embed``."""

    def __init__(self) -> None:
        self.embed_calls: list[str] = []

    def embed(self, text: str) -> list[float]:
        self.embed_calls.append(text)
        return super().embed(text)


class TestSearchPipelineIdentity:
    """EMB-01: one warning + all-stale marks on vector-touching exits, BM25 silent."""

    @staticmethod
    def _pipeline(
        conn: sqlite3.Connection,
        current: EmbedderIdentity,
        embedder: object | None = None,
    ) -> SearchPipeline:
        from sif.embedding.identity import check_identity

        return SearchPipeline(
            conn,
            embedder=embedder if embedder is not None else _FakeEmbedder(),
            embedding_dim=2,
            identity_check=lambda db: check_identity(db, current, mode="search"),
        )

    def test_same_dimension_mismatch_warns_once_and_marks_every_row(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """One warning for the identity pair, every returned row vectors_stale."""
        conn = _index_with_identity(_identity("model-a"))
        try:
            pipeline = self._pipeline(conn, _identity("model-b"))
            with caplog.at_level(logging.WARNING, logger="sif.embedding.identity"):
                first = pipeline.search(_FakeEmbedder.QUERY, SearchOptions())
                second = pipeline.search(_FakeEmbedder.QUERY, SearchOptions())
        finally:
            conn.close()

        assert first
        assert second
        assert all(result.vectors_stale for result in first)
        assert all(result.vectors_stale for result in second)
        warnings = _identity_warnings(caplog)
        assert len(warnings) == 1
        message = warnings[0].getMessage()
        assert "model-a" in message
        assert "model-b" in message
        assert "sif index embed --force" in message

    def test_a_new_identity_pair_produces_a_new_warning(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Warn-once is per pair, not per process: a third model warns again."""
        conn = _index_with_identity(_identity("model-a"))
        try:
            with caplog.at_level(logging.WARNING, logger="sif.embedding.identity"):
                self._pipeline(conn, _identity("model-b")).search(
                    _FakeEmbedder.QUERY, SearchOptions()
                )
                self._pipeline(conn, _identity("model-c")).search(
                    _FakeEmbedder.QUERY, SearchOptions()
                )
        finally:
            conn.close()

        assert len(_identity_warnings(caplog)) == 2

    def test_assumed_identity_matching_the_model_stays_silent(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """D-04: an unknown-vs-known assumed identity is not a swap."""
        conn = _index_with_identity(
            _identity("model-a", pooling="unknown", source="legacy-assumed")
        )
        try:
            pipeline = self._pipeline(conn, _identity("model-a", pooling="mean"))
            with caplog.at_level(logging.WARNING, logger="sif.embedding.identity"):
                results = pipeline.search(_FakeEmbedder.QUERY, SearchOptions())
        finally:
            conn.close()

        assert results
        assert not any(result.vectors_stale for result in results)
        assert _identity_warnings(caplog) == []

    def test_bm25_exit_never_evaluates_identity_and_marks_nothing(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """BM25 stays check-free; the first vector route evaluates once, cached."""
        from sif.embedding.identity import check_identity

        conn = _index_with_identity(_identity("model-a"))
        calls: list[object] = []
        current = _identity("model-b")

        def _closure(db: sqlite3.Connection) -> object:
            calls.append(db)
            return check_identity(db, current, mode="search")

        try:
            pipeline = SearchPipeline(
                conn,
                embedder=_FakeEmbedder(),
                embedding_dim=2,
                identity_check=_closure,
            )
            with caplog.at_level(logging.WARNING, logger="sif.embedding.identity"):
                bm25_results = pipeline.search("lex: apple", SearchOptions())
                assert calls == []
                assert bm25_results
                assert not any(result.vectors_stale for result in bm25_results)

                hybrid_results = pipeline.search(_FakeEmbedder.QUERY, SearchOptions())
                assert len(calls) == 1
                assert all(result.vectors_stale for result in hybrid_results)

                pipeline.search(_FakeEmbedder.QUERY, SearchOptions())
                assert len(calls) == 1
        finally:
            conn.close()

        assert len(_identity_warnings(caplog)) == 1

    def test_hybrid_dimension_mismatch_degrades_to_marked_bm25(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """A width disagreement skips the vector leg but still returns marked rows."""
        conn = _index_with_identity(_identity("model-a", dimension=2))

        class _ExplodingEmbedder(_FakeEmbedder):
            def embed(self, _text: str) -> list[float]:
                raise AssertionError("the vector leg must not run on a width mismatch")

        try:
            pipeline = self._pipeline(
                conn,
                _identity("model-a", dimension=3),
                embedder=_ExplodingEmbedder(),
            )
            with caplog.at_level(logging.WARNING, logger="sif.embedding.identity"):
                results = pipeline.search(_FakeEmbedder.QUERY, SearchOptions())
        finally:
            conn.close()

        assert {result.document_id for result in results} == {"d1", "d3"}
        assert all(result.vectors_stale for result in results)
        assert len(_identity_warnings(caplog)) == 1

    @pytest.mark.parametrize("prefix", ["vec:", "hyde:"])
    def test_prefix_routes_raise_identity_dimension_error(self, prefix: str) -> None:
        """vec:/hyde: cannot produce a vector result, so they fail with the remedy."""
        from sif.embedding.identity import IdentityDimensionError

        conn = _index_with_identity(_identity("model-a", dimension=2))
        try:
            pipeline = self._pipeline(conn, _identity("model-a", dimension=3))
            with pytest.raises(IdentityDimensionError) as exc_info:
                pipeline.search(f"{prefix} apple", SearchOptions())
        finally:
            conn.close()

        message = str(exc_info.value)
        assert "FLOAT[2]" in message
        assert "FLOAT[3]" in message
        assert "sif index embed --force" in message

    def test_hybrid_query_uses_the_query_role_for_every_variant(self) -> None:
        """A role-capable embedder records embed_query, never plain embed."""
        conn = TestHybridSC1PipelineGolden._build_db()
        embedder = _RoleRecordingEmbedder()
        try:
            pipeline = SearchPipeline(conn, embedder=embedder, embedding_dim=2)
            results = pipeline.search(_FakeEmbedder.QUERY, SearchOptions())
        finally:
            conn.close()

        assert results
        assert embedder.query_calls == [_FakeEmbedder.QUERY]
        assert embedder.embed_calls == []

    def test_vec_prefix_uses_the_query_role(self) -> None:
        """The vec: leg embeds through embed_query exactly once."""
        conn = TestHybridSC1PipelineGolden._build_db()
        embedder = _RoleRecordingEmbedder()
        try:
            pipeline = SearchPipeline(conn, embedder=embedder, embedding_dim=2)
            results = pipeline.search(f"vec: {_FakeEmbedder.QUERY}", SearchOptions())
        finally:
            conn.close()

        assert results
        assert embedder.query_calls == [_FakeEmbedder.QUERY]
        assert embedder.embed_calls == []

    def test_hyde_prefix_uses_the_query_role_on_the_generated_document(self) -> None:
        """The hyde: leg embeds the generated document through embed_query."""
        conn = TestHybridSC1PipelineGolden._build_db()
        embedder = _RoleRecordingEmbedder()
        try:
            pipeline = SearchPipeline(conn, embedder=embedder, embedding_dim=2)
            pipeline.search(f"hyde: {_FakeEmbedder.QUERY}", SearchOptions())
        finally:
            conn.close()

        assert embedder.generated
        assert embedder.query_calls == ["apple answer"]
        assert embedder.embed_calls == []

    def test_protocol_only_embedder_keeps_the_plain_embed_path(self) -> None:
        """No class-level role method: plain embed and the unchanged SC1 golden."""
        conn = TestHybridSC1PipelineGolden._build_db()
        embedder = _PlainRecordingEmbedder()
        try:
            pipeline = SearchPipeline(conn, embedder=embedder, embedding_dim=2)
            results = pipeline.search(_FakeEmbedder.QUERY, SearchOptions())
        finally:
            conn.close()

        assert embedder.embed_calls == [_FakeEmbedder.QUERY]
        assert not hasattr(type(embedder), "embed_query")
        assert [result.to_dict() for result in results] == TestHybridSC1PipelineGolden.SNAPSHOT

    def test_default_no_prompt_query_role_reproduces_the_sc1_golden(self) -> None:
        """D-19: the query role with no prompt is the pre-phase plain path.

        A role-capable embedder (class-level ``embed_query``) routes the default
        query through the query role, yet with no prompt effective it returns
        the same vector as the plain path — so the recorded SC1 page must
        reproduce byte-for-byte. This pins the D-19 baseline for Phase 23.
        """
        conn = TestHybridSC1PipelineGolden._build_db()
        embedder = _RoleRecordingEmbedder()
        try:
            pipeline = SearchPipeline(conn, embedder=embedder, embedding_dim=2)
            results = pipeline.search(_FakeEmbedder.QUERY, SearchOptions())
        finally:
            conn.close()

        assert embedder.query_calls == [_FakeEmbedder.QUERY]
        assert embedder.embed_calls == []
        assert [result.to_dict() for result in results] == TestHybridSC1PipelineGolden.SNAPSHOT
