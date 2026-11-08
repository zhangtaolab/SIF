"""Unit tests for hybrid search and search pipeline."""

import sqlite3
from typing import ClassVar
from unittest.mock import MagicMock, create_autospec

import pytest

from sif.core.models import SearchOptions, SearchResult, SearchType
from sif.search.bm25 import BM25Searcher
from sif.search.hybrid import HybridSearcher, SearchPipeline
from sif.search.snippets import SmartSnippetExtractor
from sif.search.vector import VectorSearcher


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_db():
    """Create a mock sqlite3 connection."""
    return MagicMock()


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
    """Tests for context_description attachment in hybrid search results."""

    def test_hybrid_search_attaches_context_after_rrf(self, mock_db: MagicMock) -> None:
        """Test that hybrid search attaches context descriptions after RRF fusion."""
        hybrid = HybridSearcher(mock_db, embedder=None, embedding_dim=384)
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

        results = hybrid.search("test")

        assert len(results) == 1
        # After RRF fusion, context_description should be preserved from one of the sources
        assert results[0].context_description is not None

    def test_pipeline_search_attaches_context_after_reranking(self, mock_db: MagicMock) -> None:
        """Test that SearchPipeline preserves context_description after reranking."""
        mock_reranker = MagicMock()
        mock_reranker.rerank.return_value = [
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
        assert len(results) == 1
        assert results[0].context_description == "Reranked context"


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

        extractor.extract.assert_not_called()
        assert results[0].snippet == "preexisting snippet"

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
    """SC1: HybridSearcher defaults stay byte-identical across the weights change.

    The snapshot below was captured from the PRE-change code on this exact
    fixture (real schema + FTS + vec0, deterministic fake embedder). BM25
    ranks d3,d1 (both contain "apple"); vector ranks d2,d3,d1,d4 — the two
    sources disagree, so the snapshot exercises real RRF merging on two
    both-sources documents. Post-change, both the implicit defaults and the
    explicit ``SearchOptions(rrf_k=60, bm25_weight=1.0, vector_weight=1.0)``
    must reproduce it field-for-field.
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
                "bm25_score": 0.9999989753435158,
                "vector_score": 0.6464466154575348,
                "rrf_score": 0.03252247488101534,
            },
            "snippet": None,
            "context_description": None,
            "vectors_stale": False,
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
                "bm25_score": 0.9999990673325406,
                "vector_score": 0.39792025089263916,
                "rrf_score": 0.031754032258064516,
            },
            "snippet": None,
            "context_description": None,
            "vectors_stale": False,
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
    """Record the candidate count/top_k a reranker receives, pass results through."""

    def __init__(self) -> None:
        self.seen = 0
        self.top_k = -1

    def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int = 10,
    ) -> list[SearchResult]:
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

    def test_candidate_fetch_limit_is_max_of_limit_offset_and_cap(
        self,
        mock_db: MagicMock,
    ) -> None:
        """fetch limit = max(limit + offset, candidate_limit) reaches the searchers."""
        cases = [((3, 2, 20), 20), ((10, 5, 12), 15)]
        for (limit, offset, cap), expected_fetch in cases:
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
                for i in range(25)
            ]
            options = SearchOptions(limit=limit, offset=offset, candidate_limit=cap)

            pipeline.search("test", options)

            passed = pipeline.hybrid.bm25.search.call_args[0][1]
            assert passed.limit == expected_fetch
            assert spy.rerank.call_args.kwargs["top_k"] == limit
            # dataclasses.replace copies: the caller's options object is untouched.
            assert options.limit == limit

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
        assert pipeline.hybrid.rrf.fuse.call_args.kwargs == {"k": 60}

    def test_candidate_fetch_off_path_matches_sc1_snapshot(self) -> None:
        """reranker=None: no over-fetch, pipeline output equals the SC1 pre-change golden."""
        conn = TestHybridSC1PipelineGolden._build_db()
        try:
            pipeline = SearchPipeline(conn, embedder=_FakeEmbedder(), embedding_dim=2)

            results = pipeline.search(_FakeEmbedder.QUERY, SearchOptions())

            assert [r.to_dict() for r in results] == TestHybridSC1PipelineGolden.SNAPSHOT
        finally:
            conn.close()
