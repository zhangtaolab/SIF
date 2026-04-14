"""DocSift - Local AI-powered document search engine."""

__version__ = "0.1.0"
__author__ = "DocSift Team"
__description__ = "Local AI-powered document search engine"

from docsift.core.models import (
    Collection,
    Document,
    DocumentChunk,
    PathContext,
    SearchOptions,
    SearchResult,
)

__all__ = [
    "Collection",
    "Document",
    "DocumentChunk",
    "PathContext",
    "SearchOptions",
    "SearchResult",
]
