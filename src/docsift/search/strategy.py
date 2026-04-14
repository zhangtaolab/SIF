"""Search strategy interface using the Strategy pattern."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Protocol

from docsift.models.search import SearchQuery, SearchResult, SearchOptions


@dataclass
class SearchContext:
    """Context passed to search strategies.
    
    Contains all necessary information for performing a search,
    including pre-computed embeddings and context strings.
    """
    
    query: str
    query_embedding: list[float] | None = None
    expanded_query: str | None = None
    collection_ids: list[str] | None = None
    context_string: str = ""
    filters: dict[str, Any] | None = None


class SearchStrategy(ABC):
    """Abstract base class for search strategies.
    
    Implements the Strategy pattern to allow different search
    algorithms to be used interchangeably.
    """
    
    @abstractmethod
    def search(
        self,
        context: SearchContext,
        options: SearchOptions,
    ) -> list[SearchResult]:
        """Execute search and return results.
        
        Args:
            context: Search context with query and embeddings
            options: Search options and parameters
            
        Returns:
            List of search results ordered by relevance
        """
        ...
    
    @abstractmethod
    def search_batch(
        self,
        contexts: list[SearchContext],
        options: SearchOptions,
    ) -> list[list[SearchResult]]:
        """Execute batch search.
        
        Args:
            contexts: List of search contexts
            options: Search options and parameters
            
        Returns:
            List of search results for each context
        """
        ...


class Searchable(Protocol):
    """Protocol for searchable repositories."""
    
    def search_fts(
        self,
        query: str,
        collection_ids: list[str] | None,
        limit: int,
        offset: int,
    ) -> list[tuple[str, float]]:
        """Search using full-text search.
        
        Returns:
            List of (document_id, score) tuples
        """
        ...
    
    def search_vector(
        self,
        embedding: list[float],
        collection_ids: list[str] | None,
        limit: int,
        offset: int,
    ) -> list[tuple[str, float]]:
        """Search using vector similarity.
        
        Returns:
            List of (document_id, score) tuples
        """
        ...
