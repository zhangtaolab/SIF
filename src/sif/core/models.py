"""Core data models for SIF."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Protocol


def _canonicalize_metadata(value: Any) -> Any:
    """Recursively string-coerce mapping keys so canonical JSON is total.

    ``json.dumps(..., default=str)`` handles non-serializable *values* only;
    a mixed-key mapping still raises ``TypeError`` because ``sort_keys=True``
    compares keys before the default hook runs. Coercing keys at every
    nesting depth makes the serializer total over anything frontmatter can
    produce (D-08).
    """
    if isinstance(value, Mapping):
        return {str(key): _canonicalize_metadata(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonicalize_metadata(item) for item in value]
    return value


def canonical_metadata_json(metadata: Mapping[str, Any]) -> str:
    """Serialize metadata to the one canonical JSON form (D-08).

    The returned string is both the persisted ``documents.metadata`` value
    and the frontmatter half of the change-detection checksum, so stored and
    hashed forms can never diverge after a JSON round trip.
    ``default=str`` keeps typed YAML values (dates, datetimes) storable
    instead of raising ``TypeError``; ``ensure_ascii=False`` keeps Unicode
    values byte-stable rather than escaped.
    """
    return json.dumps(
        _canonicalize_metadata(metadata),
        sort_keys=True,
        default=str,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def compute_checksum(content: str, metadata: Mapping[str, Any]) -> str:
    """Hash the body plus the canonical full frontmatter (D-08).

    A frontmatter-only edit changes this checksum, so Phase 20's metadata
    filters can never serve a stale tag/title value from an unchanged body.
    """
    return hashlib.sha256(
        content.encode() + b"\x00" + canonical_metadata_json(metadata).encode()
    ).hexdigest()


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
    ignore_patterns: list[str] = field(default_factory=list)
    include_by_default: bool = True
    description: str | None = None
    pre_update_cmd: str | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    document_count: int = 0
    chunk_count: int = 0
    last_indexed_at: datetime | None = None

    def mark_indexed(self) -> None:
        """Mark collection as indexed, updating timestamps."""
        self.last_indexed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
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
    def from_dict(cls, data: dict[str, Any]) -> Collection:
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
            created_at=datetime.fromisoformat(data["created_at"])
            if "created_at" in data
            else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(data["updated_at"])
            if "updated_at" in data
            else datetime.now(timezone.utc),
            document_count=data.get("document_count", 0),
            chunk_count=data.get("chunk_count", 0),
            last_indexed_at=datetime.fromisoformat(data["last_indexed_at"])
            if data.get("last_indexed_at")
            else None,
        )


@dataclass
class DocumentChunk:
    """A chunk of a document."""

    content: str
    sequence: int
    start_pos: int
    end_pos: int
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str | None = None
    token_count: int = 0
    embedding: list[float] | None = None
    embedding_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
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
    title: str | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    filename: str = field(init=False)
    checksum: str | None = None
    file_size: int | None = None
    mtime: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    chunks: list[DocumentChunk] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize computed fields."""
        self.filename = Path(self.path).name
        if self.checksum is None:
            self.checksum = hashlib.sha256(self.content.encode()).hexdigest()
        if self.file_size is None:
            self.file_size = len(self.content.encode())
        if self.title is None:
            self.title = self.filename

    def add_chunk(self, chunk: DocumentChunk) -> None:
        """Add a chunk to the document."""
        self.chunks.append(chunk)

    def clear_chunks(self) -> None:
        """Remove all chunks from the document."""
        self.chunks.clear()

    def to_dict(self) -> dict[str, Any]:
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
    collection_id: str | None = None
    context_type: str = "path"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "path": self.path,
            "collection_id": self.collection_id,
            "context_type": self.context_type,
            "context": self.context,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class QueryLogEntry:
    """A logged executed search (Phase 15, D-08).

    Stores the query string, its result count, and the collections searched —
    never document content (T-15-04). ``created_at`` is aware UTC (WR-03 is
    the cautionary naive-local finding); ranking and trim order depend on it.
    """

    query: str
    result_count: int = 0
    collections: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "query": self.query,
            "result_count": self.result_count,
            "collections": list(self.collections),
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class SearchResult:
    """A search result."""

    document_id: str
    title: str
    path: str
    collection_name: str
    score: float
    content: str | None = None
    highlights: list[str] = field(default_factory=list)
    rank: int = 0
    scores: dict[str, float | None] = field(default_factory=dict)
    snippet: str | None = None
    context_description: str | None = None
    # Derived at query time (D-08): True when this result's document has no
    # rows in document_embeddings — the tiered-depth vector lag. Defaulted so
    # every constructor stays valid; rides to_dict() into --json output.
    vectors_stale: bool = False
    # Chunk identity (D-02/D-03): the matched chunk's id and sequence number,
    # plus the count of pre-dedup vector rows collapsed into this row. All
    # defaulted so document-level rows (BM25) and every existing constructor
    # stay valid; they ride to_dict() into --json output and the MCP re-map.
    chunk_id: str | None = None
    sequence: int | None = None
    chunk_matches: int = 0

    def to_dict(self) -> dict[str, Any]:
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
            "context_description": self.context_description,
            "vectors_stale": self.vectors_stale,
            "chunk_id": self.chunk_id,
            "sequence": self.sequence,
            "chunk_matches": self.chunk_matches,
        }


@dataclass
class SearchOptions:
    """Options for search."""

    limit: int = 10
    offset: int = 0
    # CORR-02/D-01 escape hatch: the default False groups vector rows to one
    # row per document (chunk_matches carries the collapsed count); True
    # returns the ungrouped chunk rows and fuses them by chunk identity.
    per_chunk: bool = False
    # Sentinel contract: None = no collection filter (unfiltered, incl. --all);
    # [] = exclude-all — every collection excluded, searchers return zero results.
    collection_ids: list[str] | None = None
    min_score: float = 0.0
    include_content: bool = False
    include_highlights: bool = True
    max_highlights: int = 3
    explain: bool = False
    candidate_limit: int = 20
    intent: str | None = None
    snippet_max_length: int = 300
    # Fusion tunables (Phase 15, D-03): defaults equal today's hardcoded
    # behavior (k=60, equal weights), so every existing construction site and
    # unconfigured query stays byte-identical (SC1). CLI flags and MCP request
    # fields resolve INTO these fields; settings never bypass SearchOptions.
    rrf_k: int = 60
    bm25_weight: float = 1.0
    vector_weight: float = 1.0


@dataclass
class IndexStats:
    """Statistics about the index."""

    collection_count: int = 0
    document_count: int = 0
    chunk_count: int = 0
    total_size_bytes: int = 0
    last_indexed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
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

    def embed(self, text: str) -> list[float]:
        """Embed a single text."""
        ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts."""
        ...

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        ...


class Reranker(Protocol):
    """Protocol for reranking models."""

    def rerank(self, query: str, documents: list[str]) -> list[tuple[int, float]]:
        """Rerank documents for a query."""
        ...


class QueryExpander(Protocol):
    """Protocol for query expansion."""

    def expand(self, query: str) -> list[str]:
        """Expand a query into multiple variants."""
        ...
