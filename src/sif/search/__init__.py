"""Search functionality for DocSift.

This package implements various search strategies:
- BM25 full-text search via SQLite FTS5
- Vector semantic search via sqlite-vec
- Hybrid search combining multiple strategies
- RRF (Reciprocal Rank Fusion) for result merging
"""

from sif.search.bm25 import BM25Searcher
from sif.search.vector import VectorSearcher
from sif.search.hybrid import HybridSearcher, SearchPipeline
from sif.search.rrf import RRFFusion

__all__ = [
    "BM25Searcher",
    "VectorSearcher",
    "HybridSearcher",
    "SearchPipeline",
    "RRFFusion",
]
