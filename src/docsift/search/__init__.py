"""Search functionality for DocSift.

This package implements various search strategies:
- BM25 full-text search via SQLite FTS5
- Vector semantic search via sqlite-vec
- Hybrid search combining multiple strategies
- RRF (Reciprocal Rank Fusion) for result merging
"""

from docsift.search.bm25 import BM25Searcher
from docsift.search.vector import VectorSearcher
from docsift.search.hybrid import HybridSearcher, SearchPipeline
from docsift.search.rrf import RRFFusion

__all__ = [
    "BM25Searcher",
    "VectorSearcher",
    "HybridSearcher",
    "SearchPipeline",
    "RRFFusion",
]
