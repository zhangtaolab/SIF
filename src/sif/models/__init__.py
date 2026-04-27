"""Pydantic models for data validation and serialization.

This package contains all Pydantic models used for:
- Request/response validation
- Configuration management
- Data serialization/deserialization
- API schema definitions
"""

from sif.models.collection import (
    CollectionCreate,
    CollectionListResponse,
    CollectionResponse,
    CollectionUpdate,
)
from sif.models.context import (
    ContextCreate,
    ContextResponse,
    ContextUpdate,
)
from sif.models.document import (
    ChunkResponse,
    DocumentCreate,
    DocumentResponse,
    DocumentSearchResult,
    DocumentUpdate,
)
from sif.models.embedding import (
    EmbeddingConfig,
    EmbeddingModelInfo,
    EmbeddingRequest,
    EmbeddingResponse,
)
from sif.models.search import (
    SearchOptions,
    SearchQuery,
    SearchResponse,
    SearchResult,
    SearchType,
)


__all__ = [
    # Collection models
    "CollectionCreate",
    "CollectionUpdate",
    "CollectionResponse",
    "CollectionListResponse",
    # Document models
    "DocumentCreate",
    "DocumentUpdate",
    "DocumentResponse",
    "DocumentSearchResult",
    "ChunkResponse",
    # Context models
    "ContextCreate",
    "ContextUpdate",
    "ContextResponse",
    # Search models
    "SearchQuery",
    "SearchResult",
    "SearchResponse",
    "SearchOptions",
    "SearchType",
    # Embedding models
    "EmbeddingConfig",
    "EmbeddingModelInfo",
    "EmbeddingRequest",
    "EmbeddingResponse",
]
