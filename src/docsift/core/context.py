"""Context domain entity and manager."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Protocol


class ContextType(Enum):
    """Type of context."""
    
    COLLECTION = auto()
    PATH = auto()
    DOCUMENT = auto()
    GLOBAL = auto()


@dataclass
class Context:
    """Domain entity representing contextual information.
    
    Context provides descriptive metadata that can be attached to
    collections, paths, or documents to improve search relevance.
    """
    
    id: str
    content: str
    context_type: ContextType
    target_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def update_content(self, content: str) -> None:
        """Update the context content."""
        self.content = content
        self.updated_at = datetime.utcnow()


class ContextRepository(Protocol):
    """Protocol for context repository operations."""
    
    def get_by_id(self, context_id: str) -> Context | None:
        """Get a context by ID."""
        ...
    
    def get_by_target(
        self, target_id: str, context_type: ContextType
    ) -> Context | None:
        """Get context by target ID and type."""
        ...
    
    def list_by_type(self, context_type: ContextType) -> list[Context]:
        """List all contexts of a specific type."""
        ...
    
    def list_all(self) -> list[Context]:
        """List all contexts."""
        ...
    
    def create(self, context: Context) -> Context:
        """Create a new context."""
        ...
    
    def update(self, context: Context) -> Context:
        """Update an existing context."""
        ...
    
    def delete(self, context_id: str) -> bool:
        """Delete a context by ID."""
        ...
    
    def delete_by_target(self, target_id: str) -> bool:
        """Delete all contexts for a target."""
        ...


class ContextManager:
    """Manager for context operations.
    
    Provides high-level operations for managing contextual information
    attached to collections, paths, and documents.
    """
    
    def __init__(self, repository: ContextRepository) -> None:
        self._repository = repository
    
    def add_context(
        self,
        target_id: str,
        content: str,
        context_type: ContextType,
    ) -> Context:
        """Add context to a target."""
        import uuid
        
        # Check if context already exists for this target
        existing = self._repository.get_by_target(target_id, context_type)
        if existing:
            existing.update_content(content)
            return self._repository.update(existing)
        
        context = Context(
            id=str(uuid.uuid4()),
            content=content,
            context_type=context_type,
            target_id=target_id,
        )
        return self._repository.create(context)
    
    def get_context(self, context_id: str) -> Context | None:
        """Get context by ID."""
        return self._repository.get_by_id(context_id)
    
    def get_context_for_target(
        self, target_id: str, context_type: ContextType
    ) -> Context | None:
        """Get context for a specific target."""
        return self._repository.get_by_target(target_id, context_type)
    
    def update_context(self, context_id: str, content: str) -> Context:
        """Update context content."""
        context = self._repository.get_by_id(context_id)
        if not context:
            raise ValueError(f"Context '{context_id}' not found")
        
        context.update_content(content)
        return self._repository.update(context)
    
    def remove_context(self, context_id: str) -> bool:
        """Remove a context."""
        return self._repository.delete(context_id)
    
    def list_contexts(self, context_type: ContextType | None = None) -> list[Context]:
        """List contexts, optionally filtered by type."""
        if context_type:
            return self._repository.list_by_type(context_type)
        return self._repository.list_all()
    
    def build_search_context(
        self,
        collection_ids: list[str] | None = None,
        path_prefixes: list[str] | None = None,
    ) -> str:
        """Build a combined context string for search.
        
        This aggregates all relevant contexts for the given collections
        and paths to provide additional context for search queries.
        """
        contexts: list[str] = []
        
        # Get global context
        global_contexts = self._repository.list_by_type(ContextType.GLOBAL)
        contexts.extend([c.content for c in global_contexts])
        
        # Get collection contexts
        if collection_ids:
            for collection_id in collection_ids:
                ctx = self._repository.get_by_target(
                    collection_id, ContextType.COLLECTION
                )
                if ctx:
                    contexts.append(ctx.content)
        
        # Get path contexts
        if path_prefixes:
            all_path_contexts = self._repository.list_by_type(ContextType.PATH)
            for ctx in all_path_contexts:
                for prefix in path_prefixes:
                    if ctx.target_id.startswith(prefix):
                        contexts.append(ctx.content)
                        break
        
        return "\n\n".join(contexts) if contexts else ""
