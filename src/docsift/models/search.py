"""Pydantic models for Search operations."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, ConfigDict


class SearchType(str, Enum):
    """Type of search to perform."""

    BM25 = "bm25"
    VECTOR = "vector"
    HYBRID = "hybrid"


class SearchOptions(BaseModel):
    """Options for search queries."""

    limit: int = Field(10, ge=1, le=100, description="Maximum results")
    offset: int = Field(0, ge=0, description="Result offset")
    threshold: float = Field(0.0, ge=0, le=1, description="Minimum score threshold")
    include_chunks: bool = Field(True, description="Include matched chunks")
    include_metadata: bool = Field(True, description="Include document metadata")
    highlight_matches: bool = Field(True, description="Highlight matching terms")

    # BM25 options
    bm25_k1: float = Field(1.5, ge=0.1, le=3.0)
    bm25_b: float = Field(0.75, ge=0.1, le=1.0)

    # Vector options
    vector_weight: float = Field(0.7, ge=0, le=1)

    # Hybrid options
    bm25_weight: float = Field(0.3, ge=0, le=1)
    rrf_k: int = Field(60, ge=1, description="RRF fusion parameter")

    # Query expansion
    expand_query: bool = Field(False, description="Enable query expansion")
    expansion_factor: int = Field(3, ge=1, le=10)

    # Reranking
    rerank: bool = Field(False, description="Enable reranking")
    rerank_top_k: int = Field(20, ge=1, le=100)


class SearchQuery(BaseModel):
    """Model for search query."""

    query: str = Field(..., min_length=1, description="Search query")
    collection_ids: list[str] | None = Field(None, description="Filter by collections")
    search_type: SearchType = Field(SearchType.HYBRID, description="Search type")
    options: SearchOptions = Field(default_factory=SearchOptions)
    filters: dict[str, Any] = Field(default_factory=dict, description="Additional filters")


class SearchResult(BaseModel):
    """Model for individual search result."""

    model_config = ConfigDict(from_attributes=True)

    document_id: str = Field(..., description="Document ID")
    document_path: str = Field(..., description="Document path")
    document_title: str | None = None
    score: float = Field(..., ge=0, le=1)

    # Component scores (for hybrid search)
    bm25_score: float | None = None
    vector_score: float | None = None

    # Result data
    content_preview: str | None = None
    matched_chunks: list[dict[str, Any]] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    context_description: str | None = None


class SearchResponse(BaseModel):
    """Model for search response."""

    query: str = Field(..., description="Original query")
    search_type: SearchType = Field(...)
    total: int = Field(..., ge=0, description="Total matching documents")
    results: list[SearchResult] = Field(default_factory=list)

    # Performance metrics
    search_time_ms: float = Field(..., ge=0)

    # Query expansion info
    expanded_query: str | None = None
    expansion_terms: list[str] = Field(default_factory=list)
