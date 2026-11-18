"""SIF - Search / Index / Find - Local document search engine."""

from sif._version import __version__ as __version__
from sif.core.models import (
    Collection,
    Document,
    DocumentChunk,
    PathContext,
    SearchOptions,
    SearchResult,
)


__author__ = "SIF Team"
__description__ = "Local document search engine (SIF: Search / Index / Find)"

__all__ = [
    "Collection",
    "Document",
    "DocumentChunk",
    "PathContext",
    "SearchOptions",
    "SearchResult",
]
