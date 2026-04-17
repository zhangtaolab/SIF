"""Core data models for DocSift."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol


class ChunkStrategy(Enum):
    """Document chunking strategies."""
    FIXED = "fixed"
    MARKDOWN = "markdown"
    CODE = "code"
    AUTO = "auto"


class SearchType(Enum):
    """Search types."""
    BM25 = "bm25"
    VECTOR = "vector"
    HYBRID = "hybrid"
    HYDE = "hyde"
    EXPAND = "expand"


@dataclass
class Collection:
    """A document collection."""
    name: str
    path: str
    pattern: str = "**/*.md"
    ignore_patterns: List[str] = field(default_factory=list)
    include_by_default: bool = True
    description: Optional[str] = None
    pre_update_cmd: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    document_count: int = 0
    chunk_count: int = 0
    last_indexed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "pattern": self.pattern,
            "ignore_patterns": self.ignore_patterns,
            "include_by_default": self.include_by_default,
            "description": self.description,
            "pre_update_cmd": self.pre_update_cmd,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "document_count": self.document_count,
            "chunk_count": self.chunk_count,
            "last_indexed_at": self.last_indexed_at.isoformat() if self.last_indexed_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Collection:
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data["name"],
            path=data["path"],
            pattern=data.get("pattern", "**/*.md"),
            ignore_patterns=data.get("ignore_patterns", []),
            include_by_default=data.get("include_by_default", True),
            description=data.get("description"),
            pre_update_cmd=data.get("pre_update_cmd"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.utcnow(),
            document_count=data.get("document_count", 0),
            chunk_count=data.get("chunk_count", 0),
            last_indexed_at=datetime.fromisoformat(data["last_indexed_at"]) if data.get("last_indexed_at") else None,
        )


@dataclass
class DocumentChunk:
    """A chunk of a document."""
    content: str
    sequence: int
    start_pos: int
    end_pos: int
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: Optional[str] = None
    token_count: int = 0
    embedding: Optional[List[float]] = None
    embedding_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "content": self.content,
            "sequence": self.sequence,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "token_count": self.token_count,
            "embedding_id": self.embedding_id,
        }


@dataclass
class Document:
    """A document in the index."""
    path: str
    collection_id: str
    content: str
    title: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    filename: str = field(init=False)
    checksum: str = field(init=False)
    file_size: int = field(init=False)
    mtime: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    chunks: List[DocumentChunk] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize computed fields."""
        self.filename = Path(self.path).name
        self.checksum = hashlib.sha256(self.content.encode()).hexdigest()
        self.file_size = len(self.content.encode())
        if self.title is None:
            self.title = self.filename
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "path": self.path,
            "collection_id": self.collection_id,
            "filename": self.filename,
            "title": self.title,
            "checksum": self.checksum,
            "file_size": self.file_size,
            "mtime": self.mtime,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
            "chunk_count": len(self.chunks),
        }


@dataclass
class PathContext:
    """Context information for a path."""
    path: str
    context: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    collection_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "path": self.path,
            "collection_id": self.collection_id,
            "context": self.context,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class SearchResult:
    """A search result."""
    document_id: str
    title: str
    path: str
    collection_name: str
    score: float
    content: Optional[str] = None
    highlights: List[str] = field(default_factory=list)
    rank: int = 0
    scores: Dict[str, Optional[float]] = field(default_factory=dict)
    snippet: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "document_id": self.document_id,
            "title": self.title,
            "path": self.path,
            "collection_name": self.collection_name,
            "score": self.score,
            "content": self.content,
            "highlights": self.highlights,
            "rank": self.rank,
            "scores": self.scores,
            "snippet": self.snippet,
        }


@dataclass
class SearchOptions:
    """Options for search."""
    limit: int = 10
    offset: int = 0
    collection_ids: Optional[List[str]] = None
    min_score: float = 0.0
    include_content: bool = False
    include_highlights: bool = True
    max_highlights: int = 3
    explain: bool = False
    candidate_limit: int = 20
    intent: Optional[str] = None
    snippet_max_length: int = 300


@dataclass
class IndexStats:
    """Statistics about the index."""
    collection_count: int = 0
    document_count: int = 0
    chunk_count: int = 0
    total_size_bytes: int = 0
    last_indexed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "collection_count": self.collection_count,
            "document_count": self.document_count,
            "chunk_count": self.chunk_count,
            "total_size_bytes": self.total_size_bytes,
            "last_indexed_at": self.last_indexed_at.isoformat() if self.last_indexed_at else None,
        }


class Embedder(Protocol):
    """Protocol for embedding models."""
    
    def embed(self, text: str) -> List[float]:
        """Embed a single text."""
        ...
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts."""
        ...
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        ...


class Reranker(Protocol):
    """Protocol for reranking models."""
    
    def rerank(self, query: str, documents: List[str]) -> List[tuple[int, float]]:
        """Rerank documents for a query."""
        ...


class QueryExpander(Protocol):
    """Protocol for query expansion."""
    
    def expand(self, query: str) -> List[str]:
        """Expand a query into multiple variants."""
        ...
