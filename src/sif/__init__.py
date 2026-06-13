"""SIF - Search / Index / Find - Local document search engine."""

__version__ = "0.2.1"
__author__ = "SIF Team"
__description__ = "Local document search engine (SIF: Search / Index / Find)"

from sif.core.models import (
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
