"""Search functionality for SIF.

This package implements various search strategies:
- BM25 full-text search via SQLite FTS5
- Vector semantic search via sqlite-vec
- Hybrid search combining multiple strategies
- RRF (Reciprocal Rank Fusion) for result merging
"""

from sif.search.bm25 import BM25Searcher
from sif.search.hybrid import HybridSearcher, SearchPipeline
from sif.search.rrf import RRFFusion
from sif.search.vector import VectorSearcher


__all__ = [
    "BM25Searcher",
    "HybridSearcher",
    "RRFFusion",
    "SearchPipeline",
    "VectorSearcher",
]
