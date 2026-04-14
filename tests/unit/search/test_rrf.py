"""Unit tests for Reciprocal Rank Fusion (RRF) algorithm.

This module tests the RRF fusion implementation including:
- Basic fusion of multiple result lists
- Different k values and their effects
- Weighted fusion
- Edge cases and boundary conditions
"""

import uuid
from typing import Any

import pytest

from docsift.models.search import SearchResult
from docsift.search.rrf import RRFFusion


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def rrf_fusion() -> RRFFusion:
    """Create a default RRF fusion instance."""
    return RRFFusion(default_k=60)


@pytest.fixture
def sample_search_results() -> list[SearchResult]:
    """Create sample search results for testing."""
    return [
        SearchResult(
            document_id=f"doc-{i}",
            document_path=f"/path/to/doc_{i}.md",
            document_title=f"Document {i}",
            score=0.95 - (i * 0.05),
            content_preview=f"Preview {i}",
        )
        for i in range(5)
    ]


@pytest.fixture
def bm25_results() -> list[SearchResult]:
    """Create BM25 search results for testing."""
    return [
        SearchResult(
            document_id="doc-A",
            document_path="/path/to/doc_a.md",
            document_title="Document A",
            score=0.95,
            bm25_score=0.95,
            content_preview="Preview A",
        ),
        SearchResult(
            document_id="doc-B",
            document_path="/path/to/doc_b.md",
            document_title="Document B",
            score=0.87,
            bm25_score=0.87,
            content_preview="Preview B",
        ),
        SearchResult(
            document_id="doc-C",
            document_path="/path/to/doc_c.md",
            document_title="Document C",
            score=0.82,
            bm25_score=0.82,
            content_preview="Preview C",
        ),
    ]


@pytest.fixture
def vector_results() -> list[SearchResult]:
    """Create vector search results for testing."""
    return [
        SearchResult(
            document_id="doc-A",
            document_path="/path/to/doc_a.md",
            document_title="Document A",
            score=0.92,
            vector_score=0.92,
            content_preview="Preview A",
        ),
        SearchResult(
            document_id="doc-C",
            document_path="/path/to/doc_c.md",
            document_title="Document C",
            score=0.88,
            vector_score=0.88,
            content_preview="Preview C",
        ),
        SearchResult(
            document_id="doc-D",
            document_path="/path/to/doc_d.md",
            document_title="Document D",
            score=0.85,
            vector_score=0.85,
            content_preview="Preview D",
        ),
    ]


# =============================================================================
# Basic Fusion Tests
# =============================================================================


class TestRRFBasicFusion:
    """Test basic RRF fusion functionality."""
    
    def test_fuse_single_list(self, rrf_fusion: RRFFusion, sample_search_results: list[SearchResult]) -> None:
        """Test fusing a single result list.
        
        Arrange: Create single result list
        Act: Call fuse with single list
        Assert: Returns results with RRF scores
        """
        # Arrange
        result_lists = [sample_search_results]
        
        # Act
        fused = rrf_fusion.fuse(result_lists)
        
        # Assert
        assert len(fused) == len(sample_search_results)
        # With single list, RRF score = 1/(k + rank)
        # For k=60, rank 1: 1/61 ≈ 0.0164
        assert fused[0].score > 0
        assert fused[0].document_id == sample_search_results[0].document_id
    
    def test_fuse_multiple_lists(self, rrf_fusion: RRFFusion, bm25_results: list[SearchResult], vector_results: list[SearchResult]) -> None:
        """Test fusing multiple result lists.
        
        Arrange: Create two result lists with overlapping documents
        Act: Call fuse with both lists
        Assert: Returns combined results ordered by fused score
        """
        # Arrange
        result_lists = [bm25_results, vector_results]
        
        # Act
        fused = rrf_fusion.fuse(result_lists)
        
        # Assert
        # doc-A appears in both lists (rank 1 in both)
        # doc-C appears in both lists (rank 3 in BM25, rank 2 in vector)
        # doc-B appears only in BM25
        # doc-D appears only in vector
        assert len(fused) == 4  # Unique documents
        
        # doc-A should be first (appears in both at rank 1)
        assert fused[0].document_id == "doc-A"
        
        # All scores should be positive
        assert all(r.score > 0 for r in fused)
    
    def test_fuse_preserves_document_info(self, rrf_fusion: RRFFusion, bm25_results: list[SearchResult], vector_results: list[SearchResult]) -> None:
        """Test that fusion preserves document metadata.
        
        Arrange: Create result lists with full metadata
        Act: Call fuse
        Assert: Preserved document path, title, etc.
        """
        # Arrange
        result_lists = [bm25_results, vector_results]
        
        # Act
        fused = rrf_fusion.fuse(result_lists)
        
        # Assert
        doc_a = next(r for r in fused if r.document_id == "doc-A")
        assert doc_a.document_path == "/path/to/doc_a.md"
        assert doc_a.document_title == "Document A"
        assert doc_a.content_preview == "Preview A"
    
    def test_fuse_empty_lists(self, rrf_fusion: RRFFusion) -> None:
        """Test fusing empty result lists.
        
        Arrange: Create empty result lists
        Act: Call fuse
        Assert: Returns empty list
        """
        # Arrange
        result_lists: list[list[SearchResult]] = [[], []]
        
        # Act
        fused = rrf_fusion.fuse(result_lists)
        
        # Assert
        assert fused == []
    
    def test_fuse_single_empty_list(self, rrf_fusion: RRFFusion, sample_search_results: list[SearchResult]) -> None:
        """Test fusing with one empty list.
        
        Arrange: Create one empty and one non-empty list
        Act: Call fuse
        Assert: Returns results from non-empty list
        """
        # Arrange
        result_lists = [[], sample_search_results]
        
        # Act
        fused = rrf_fusion.fuse(result_lists)
        
        # Assert
        assert len(fused) == len(sample_search_results)


# =============================================================================
# K Value Tests
# =============================================================================


class TestRRFKValues:
    """Test RRF with different k values."""
    
    def test_default_k_value(self) -> None:
        """Test default k value is 60.
        
        Arrange: Create RRF fusion without specifying k
        Act: Check default_k attribute
        Assert: Default k is 60
        """
        # Arrange & Act
        fusion = RRFFusion()
        
        # Assert
        assert fusion._default_k == 60
    
    def test_custom_k_value(self) -> None:
        """Test custom k value in constructor.
        
        Arrange: Create RRF fusion with custom k
        Act: Check default_k attribute
        Assert: Custom k is set correctly
        """
        # Arrange & Act
        fusion = RRFFusion(default_k=100)
        
        # Assert
        assert fusion._default_k == 100
    
    def test_k_value_effect_on_scores(self, bm25_results: list[SearchResult], vector_results: list[SearchResult]) -> None:
        """Test that k value affects score distribution.
        
        Arrange: Create two RRF instances with different k values
        Act: Fuse same results with both
        Assert: Lower k produces more differentiated scores
        """
        # Arrange
        fusion_low_k = RRFFusion(default_k=10)
        fusion_high_k = RRFFusion(default_k=100)
        result_lists = [bm25_results, vector_results]
        
        # Act
        fused_low_k = fusion_low_k.fuse(result_lists, k=10)
        fused_high_k = fusion_high_k.fuse(result_lists, k=100)
        
        # Assert
        # With lower k, top rank scores are higher relative to others
        # Score spread should be larger with lower k
        low_k_spread = fused_low_k[0].score - fused_low_k[-1].score
        high_k_spread = fused_high_k[0].score - fused_high_k[-1].score
        assert low_k_spread > high_k_spread
    
    def test_override_k_in_fuse(self, rrf_fusion: RRFFusion, bm25_results: list[SearchResult]) -> None:
        """Test overriding k value in fuse method.
        
        Arrange: Create RRF with default k, override in fuse
        Act: Call fuse with different k
        Assert: Uses overridden k value
        """
        # Arrange
        result_lists = [bm25_results]
        
        # Act
        fused_default = rrf_fusion.fuse(result_lists, k=60)
        fused_override = rrf_fusion.fuse(result_lists, k=10)
        
        # Assert
        # With k=10, rank 1 score = 1/11 ≈ 0.0909
        # With k=60, rank 1 score = 1/61 ≈ 0.0164
        assert fused_override[0].score > fused_default[0].score
    
    @pytest.mark.parametrize("k", [1, 10, 60, 100, 1000])
    def test_various_k_values(self, k: int, bm25_results: list[SearchResult]) -> None:
        """Test RRF works with various k values.
        
        Arrange: Create RRF with different k values
        Act: Fuse results
        Assert: Returns valid results for all k values
        """
        # Arrange
        fusion = RRFFusion(default_k=k)
        result_lists = [bm25_results]
        
        # Act
        fused = fusion.fuse(result_lists)
        
        # Assert
        assert len(fused) == len(bm25_results)
        assert all(r.score > 0 for r in fused)


# =============================================================================
# Weighted Fusion Tests
# =============================================================================


class TestRRFWeightedFusion:
    """Test RRF with weighted result lists."""
    
    def test_equal_weights(self, rrf_fusion: RRFFusion, bm25_results: list[SearchResult], vector_results: list[SearchResult]) -> None:
        """Test fusion with equal weights.
        
        Arrange: Create result lists with equal weights
        Act: Call fuse with equal weights
        Assert: Results ordered by combined score
        """
        # Arrange
        result_lists = [bm25_results, vector_results]
        weights = [1.0, 1.0]
        
        # Act
        fused = rrf_fusion.fuse(result_lists, weights=weights)
        
        # Assert
        assert len(fused) == 4
        # doc-A appears in both at rank 1, should be first
        assert fused[0].document_id == "doc-A"
    
    def test_unequal_weights(self, rrf_fusion: RRFFusion, bm25_results: list[SearchResult], vector_results: list[SearchResult]) -> None:
        """Test fusion with unequal weights.
        
        Arrange: Create result lists with different weights
        Act: Call fuse with weighted scores
        Assert: Higher weighted list has more influence
        """
        # Arrange
        result_lists = [bm25_results, vector_results]
        # Give BM25 much higher weight
        weights = [10.0, 1.0]
        
        # Act
        fused = rrf_fusion.fuse(result_lists, weights=weights)
        
        # Assert
        # With high BM25 weight, BM25 ranking should dominate
        # doc-A appears in both at rank 1, should be first
        # doc-B (rank 2 in BM25) gets high weight: 10/(60+2) = 0.161
        # doc-C (rank 3 in BM25, rank 2 in vector) gets: 10/(60+3) + 1/(60+2) = 0.175
        # So doc-C should rank higher than doc-B due to appearing in both lists
        assert fused[0].document_id == "doc-A"  # Always first (rank 1 in both)
        # Verify that weights affect scores (doc-C has higher fused score than doc-B)
        doc_c = next(r for r in fused if r.document_id == "doc-C")
        doc_b = next(r for r in fused if r.document_id == "doc-B")
        assert doc_c.score > doc_b.score
    
    def test_zero_weight(self, rrf_fusion: RRFFusion, bm25_results: list[SearchResult], vector_results: list[SearchResult]) -> None:
        """Test fusion with zero weight for one list.
        
        Arrange: Create result lists, one with zero weight
        Act: Call fuse with zero weight
        Assert: Zero-weighted list has no effect on scores
        """
        # Arrange
        result_lists = [bm25_results, vector_results]
        weights = [1.0, 0.0]
        
        # Act
        fused = rrf_fusion.fuse(result_lists, weights=weights)
        
        # Assert
        # With zero weight for vector, vector-only docs (doc-D) get 0 score from vector list
        # But doc-A, doc-B, doc-C still appear from BM25
        # doc-D appears only in vector list with weight 0, so score = 0
        # Note: Documents with 0 score may still appear in results
        bm25_doc_ids = {"doc-A", "doc-B", "doc-C"}
        fused_doc_ids = {r.document_id for r in fused}
        
        # All BM25 docs should be in results
        assert bm25_doc_ids.issubset(fused_doc_ids)
        
        # doc-D should have 0 score (only appears in zero-weighted list)
        doc_d = next((r for r in fused if r.document_id == "doc-D"), None)
        if doc_d:
            assert doc_d.score == 0.0
    
    def test_weights_length_mismatch(self, rrf_fusion: RRFFusion, bm25_results: list[SearchResult]) -> None:
        """Test fusion with mismatched weights length.
        
        Arrange: Create result lists with fewer weights than lists
        Act: Call fuse
        Assert: Uses default weights for missing entries
        """
        # Arrange
        result_lists = [bm25_results]
        # Provide more weights than lists (should still work)
        weights = [1.0, 2.0, 3.0]
        
        # Act
        fused = rrf_fusion.fuse(result_lists, weights=weights)
        
        # Assert
        assert len(fused) == len(bm25_results)


# =============================================================================
# Edge Cases and Boundary Tests
# =============================================================================


class TestRRFEdgeCases:
    """Test RRF edge cases and boundary conditions."""
    
    def test_identical_result_lists(self, rrf_fusion: RRFFusion, sample_search_results: list[SearchResult]) -> None:
        """Test fusing identical result lists.
        
        Arrange: Create two identical result lists
        Act: Call fuse
        Assert: Documents get double the score
        """
        # Arrange
        result_lists = [sample_search_results, sample_search_results]
        
        # Act
        fused = rrf_fusion.fuse(result_lists)
        
        # Assert
        assert len(fused) == len(sample_search_results)
        # Each document appears twice, so score should be doubled
        # For rank 1 with k=60: 2 * (1/61) ≈ 0.0328
        expected_score = 2 * (1 / (60 + 1))
        assert abs(fused[0].score - expected_score) < 0.0001
    
    def test_completely_disjoint_lists(self, rrf_fusion: RRFFusion) -> None:
        """Test fusing completely disjoint result lists.
        
        Arrange: Create two lists with no common documents
        Act: Call fuse
        Assert: All documents appear in result
        """
        # Arrange
        list1 = [
            SearchResult(document_id="doc-1", document_path="/a/1.md", score=0.9),
            SearchResult(document_id="doc-2", document_path="/a/2.md", score=0.8),
        ]
        list2 = [
            SearchResult(document_id="doc-3", document_path="/b/3.md", score=0.85),
            SearchResult(document_id="doc-4", document_path="/b/4.md", score=0.75),
        ]
        result_lists = [list1, list2]
        
        # Act
        fused = rrf_fusion.fuse(result_lists)
        
        # Assert
        assert len(fused) == 4
        doc_ids = {r.document_id for r in fused}
        assert doc_ids == {"doc-1", "doc-2", "doc-3", "doc-4"}
    
    def test_single_document_lists(self, rrf_fusion: RRFFusion) -> None:
        """Test fusing lists with single documents.
        
        Arrange: Create lists with single documents
        Act: Call fuse
        Assert: Correctly fuses single-item lists
        """
        # Arrange
        list1 = [SearchResult(document_id="doc-A", document_path="/a.md", score=1.0)]
        list2 = [SearchResult(document_id="doc-B", document_path="/b.md", score=1.0)]
        result_lists = [list1, list2]
        
        # Act
        fused = rrf_fusion.fuse(result_lists)
        
        # Assert
        assert len(fused) == 2
        # Both have rank 1, so both get same score: 1/(60+1)
        assert fused[0].score == fused[1].score
    
    def test_large_number_of_lists(self, rrf_fusion: RRFFusion) -> None:
        """Test fusing many result lists.
        
        Arrange: Create many identical result lists
        Act: Call fuse
        Assert: Correctly handles many lists
        """
        # Arrange
        base_list = [
            SearchResult(document_id=f"doc-{i}", document_path=f"/{i}.md", score=0.9)
            for i in range(5)
        ]
        result_lists = [base_list.copy() for _ in range(10)]
        
        # Act
        fused = rrf_fusion.fuse(result_lists)
        
        # Assert
        assert len(fused) == 5
        # Score should be 10 * (1/(60+rank))
        expected_first_score = 10 * (1 / 61)
        assert abs(fused[0].score - expected_first_score) < 0.0001
    
    def test_very_large_k(self, sample_search_results: list[SearchResult]) -> None:
        """Test with very large k value.
        
        Arrange: Create RRF with large k
        Act: Fuse results
        Assert: Scores are small but positive
        """
        # Arrange
        fusion = RRFFusion(default_k=10000)
        result_lists = [sample_search_results]
        
        # Act
        fused = fusion.fuse(result_lists)
        
        # Assert
        assert len(fused) == len(sample_search_results)
        assert all(r.score > 0 for r in fused)
        # With k=10000, rank 1 score = 1/10001 ≈ 0.0001
        assert fused[0].score < 0.001
    
    def test_result_ordering_stability(self, rrf_fusion: RRFFusion) -> None:
        """Test that result ordering is stable.
        
        Arrange: Create lists where ties might occur
        Act: Call fuse multiple times
        Assert: Ordering is consistent
        """
        # Arrange
        list1 = [
            SearchResult(document_id="doc-1", document_path="/1.md", score=0.9),
            SearchResult(document_id="doc-2", document_path="/2.md", score=0.8),
        ]
        list2 = [
            SearchResult(document_id="doc-2", document_path="/2.md", score=0.85),
            SearchResult(document_id="doc-1", document_path="/1.md", score=0.75),
        ]
        
        # Act
        results = [rrf_fusion.fuse([list1, list2]) for _ in range(5)]
        
        # Assert
        # Both docs appear in both lists, so they get same score
        # doc-1: rank 1 in list1, rank 2 in list2
        # doc-2: rank 2 in list1, rank 1 in list2
        # Both get: 1/61 + 1/62 = same score
        for fused in results:
            assert len(fused) == 2
            # Scores should be equal (within floating point precision)
            assert abs(fused[0].score - fused[1].score) < 0.0001


# =============================================================================
# Score Calculation Tests
# =============================================================================


class TestRRFScoreCalculation:
    """Test RRF score calculation accuracy."""
    
    def test_rrf_formula_correctness(self, rrf_fusion: RRFFusion) -> None:
        """Test that RRF formula is calculated correctly.
        
        Arrange: Create known result lists
        Act: Call fuse
        Assert: Scores match expected RRF values
        """
        # Arrange
        list1 = [
            SearchResult(document_id="doc-X", document_path="/x.md", score=0.9),
        ]
        list2 = [
            SearchResult(document_id="doc-X", document_path="/x.md", score=0.8),
        ]
        k = 60
        
        # Act
        fused = rrf_fusion.fuse([list1, list2], k=k)
        
        # Assert
        # doc-X has rank 1 in both lists
        # RRF score = 1/(60+1) + 1/(60+1) = 2/61
        expected_score = 2 / (k + 1)
        assert len(fused) == 1
        assert abs(fused[0].score - expected_score) < 0.0001
    
    def test_rrf_with_different_ranks(self, rrf_fusion: RRFFusion) -> None:
        """Test RRF with documents at different ranks.
        
        Arrange: Create list with documents at different ranks
        Act: Call fuse
        Assert: Higher ranked documents have higher scores
        """
        # Arrange
        results = [
            SearchResult(document_id=f"doc-{i}", document_path=f"/{i}.md", score=0.9 - i * 0.1)
            for i in range(5)
        ]
        k = 60
        
        # Act
        fused = rrf_fusion.fuse([results], k=k)
        
        # Assert
        # Scores should decrease as rank increases
        for i in range(len(fused) - 1):
            assert fused[i].score > fused[i + 1].score
        
        # Verify exact values
        # Rank 1: 1/61, Rank 2: 1/62, etc.
        for i, result in enumerate(fused):
            expected_score = 1 / (k + i + 1)
            assert abs(result.score - expected_score) < 0.0001
    
    def test_rrf_score_bounds(self, rrf_fusion: RRFFusion, sample_search_results: list[SearchResult]) -> None:
        """Test that RRF scores are within expected bounds.
        
        Arrange: Create result lists
        Act: Call fuse
        Assert: All scores are positive and within bounds
        """
        # Arrange
        result_lists = [sample_search_results]
        
        # Act
        fused = rrf_fusion.fuse(result_lists)
        
        # Assert
        # With k=60, max score for rank 1 is 1/61 ≈ 0.0164
        # Min score approaches 0 as rank increases
        assert all(r.score > 0 for r in fused)
        assert all(r.score < 1 for r in fused)
        assert fused[0].score < 0.02  # Upper bound for rank 1 with k=60
