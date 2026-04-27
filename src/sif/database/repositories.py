"""Repository implementations for DocSift database."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import List, Optional

from docsift.core.models import (
    Collection,
    Document,
    DocumentChunk,
    PathContext,
)


class CollectionRepository:
    """Repository for collection operations."""

    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db

    def create(self, collection: Collection) -> Collection:
        """Create a new collection."""
        self.db.execute(
            """
            INSERT INTO collections (
                id, name, path, pattern, ignore_patterns, include_by_default,
                description, pre_update_cmd, created_at, updated_at, document_count, chunk_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                collection.id,
                collection.name,
                collection.path,
                collection.pattern,
                json.dumps(collection.ignore_patterns),
                int(collection.include_by_default),
                collection.description,
                collection.pre_update_cmd,
                collection.created_at.isoformat(),
                collection.updated_at.isoformat(),
                collection.document_count,
                collection.chunk_count,
            ),
        )
        return collection

    def get_by_id(self, collection_id: str) -> Optional[Collection]:
        """Get collection by ID."""
        cursor = self.db.execute("SELECT * FROM collections WHERE id = ?", (collection_id,))
        row = cursor.fetchone()
        return self._row_to_collection(row) if row else None

    def get_by_name(self, name: str) -> Optional[Collection]:
        """Get collection by name."""
        cursor = self.db.execute("SELECT * FROM collections WHERE name = ?", (name,))
        row = cursor.fetchone()
        return self._row_to_collection(row) if row else None

    def list_all(self) -> List[Collection]:
        """List all collections."""
        cursor = self.db.execute("SELECT * FROM collections ORDER BY name")
        return [self._row_to_collection(row) for row in cursor.fetchall()]

    def update(self, collection: Collection) -> Collection:
        """Update a collection."""
        collection.updated_at = datetime.utcnow()
        self.db.execute(
            """
            UPDATE collections SET
                name = ?, path = ?, pattern = ?, ignore_patterns = ?,
                include_by_default = ?, description = ?, pre_update_cmd = ?, updated_at = ?,
                document_count = ?, chunk_count = ?, last_indexed_at = ?
            WHERE id = ?
            """,
            (
                collection.name,
                collection.path,
                collection.pattern,
                json.dumps(collection.ignore_patterns),
                int(collection.include_by_default),
                collection.description,
                collection.pre_update_cmd,
                collection.updated_at.isoformat(),
                collection.document_count,
                collection.chunk_count,
                collection.last_indexed_at.isoformat() if collection.last_indexed_at else None,
                collection.id,
            ),
        )
        return collection

    def delete(self, collection_id: str) -> bool:
        """Delete a collection."""
        cursor = self.db.execute("DELETE FROM collections WHERE id = ?", (collection_id,))
        return cursor.rowcount > 0

    def exists(self, name: str) -> bool:
        """Check if collection exists."""
        cursor = self.db.execute("SELECT 1 FROM collections WHERE name = ?", (name,))
        return cursor.fetchone() is not None

    def list_enabled(self) -> List[Collection]:
        """List all collections enabled for default searches."""
        cursor = self.db.execute(
            "SELECT * FROM collections WHERE include_by_default = 1 ORDER BY name"
        )
        return [self._row_to_collection(row) for row in cursor.fetchall()]

    def _row_to_collection(self, row: sqlite3.Row) -> Collection:
        """Convert database row to Collection."""
        return Collection(
            id=row["id"],
            name=row["name"],
            path=row["path"],
            pattern=row["pattern"],
            ignore_patterns=json.loads(row["ignore_patterns"]),
            include_by_default=bool(row["include_by_default"]),
            description=row["description"],
            pre_update_cmd=row["pre_update_cmd"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            last_indexed_at=datetime.fromisoformat(row["last_indexed_at"])
            if row["last_indexed_at"]
            else None,
        )


class DocumentRepository:
    """Repository for document operations."""

    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db

    def create(self, document: Document) -> Document:
        """Create a new document."""
        self.db.execute(
            """
            INSERT INTO documents (
                id, collection_id, path, filename, title, content,
                checksum, file_size, mtime, created_at, updated_at, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document.id,
                document.collection_id,
                document.path,
                document.filename,
                document.title,
                document.content,
                document.checksum,
                document.file_size,
                document.mtime,
                document.created_at.isoformat(),
                document.updated_at.isoformat(),
                json.dumps(document.metadata) if document.metadata else "{}",
            ),
        )

        return document

    def get_by_id(self, document_id: str) -> Optional[Document]:
        """Get document by ID."""
        cursor = self.db.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
        row = cursor.fetchone()
        return self._row_to_document(row) if row else None

    def get_by_path(self, path: str, collection_id: str) -> Optional[Document]:
        """Get document by path and collection."""
        cursor = self.db.execute(
            "SELECT * FROM documents WHERE path = ? AND collection_id = ?", (path, collection_id)
        )
        row = cursor.fetchone()
        return self._row_to_document(row) if row else None

    def list_by_collection(self, collection_id: str) -> List[Document]:
        """List documents in a collection."""
        cursor = self.db.execute(
            "SELECT * FROM documents WHERE collection_id = ? ORDER BY filename", (collection_id,)
        )
        return [self._row_to_document(row) for row in cursor.fetchall()]

    def update(self, document: Document) -> Document:
        """Update a document."""
        document.updated_at = datetime.utcnow()
        self.db.execute(
            """
            UPDATE documents SET
                title = ?, content = ?, checksum = ?, file_size = ?,
                mtime = ?, updated_at = ?, metadata = ?
            WHERE id = ?
            """,
            (
                document.title,
                document.content,
                document.checksum,
                document.file_size,
                document.mtime,
                document.updated_at.isoformat(),
                json.dumps(document.metadata) if document.metadata else "{}",
                document.id,
            ),
        )

        return document

    def delete(self, document_id: str) -> bool:
        """Delete a document."""
        # Delete document chunks first
        from docsift.database.repositories import DocumentChunkRepository

        chunk_repo = DocumentChunkRepository(self.db)
        chunk_repo.delete_by_document(document_id)

        cursor = self.db.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        return cursor.rowcount > 0

    def delete_by_collection(self, collection_id: str) -> int:
        """Delete all documents in a collection."""
        # Get document IDs
        cursor = self.db.execute(
            "SELECT id FROM documents WHERE collection_id = ?", (collection_id,)
        )
        doc_ids = [row[0] for row in cursor.fetchall()]

        # Delete chunks for each document
        from docsift.database.repositories import DocumentChunkRepository

        chunk_repo = DocumentChunkRepository(self.db)
        for doc_id in doc_ids:
            chunk_repo.delete_by_document(doc_id)

        cursor = self.db.execute("DELETE FROM documents WHERE collection_id = ?", (collection_id,))
        return cursor.rowcount

    def get_checksum(self, document_id: str) -> Optional[str]:
        """Get document checksum."""
        cursor = self.db.execute("SELECT checksum FROM documents WHERE id = ?", (document_id,))
        row = cursor.fetchone()
        return row[0] if row else None

    def exists(self, path: str, collection_id: str) -> bool:
        """Check if document exists."""
        cursor = self.db.execute(
            "SELECT 1 FROM documents WHERE path = ? AND collection_id = ?", (path, collection_id)
        )
        return cursor.fetchone() is not None

    def _row_to_document(self, row: sqlite3.Row) -> Document:
        """Convert database row to Document."""
        doc = Document(
            id=row["id"],
            path=row["path"],
            collection_id=row["collection_id"],
            content=row["content"],
            title=row["title"],
        )
        doc.filename = row["filename"]
        doc.checksum = row["checksum"]
        doc.file_size = row["file_size"]
        doc.mtime = row["mtime"]
        doc.created_at = datetime.fromisoformat(row["created_at"])
        doc.updated_at = datetime.fromisoformat(row["updated_at"])
        doc.metadata = json.loads(row["metadata"])
        return doc


class DocumentChunkRepository:
    """Repository for document chunk operations."""

    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db

    def create(self, chunk: DocumentChunk) -> DocumentChunk:
        """Create a new chunk."""
        self.db.execute(
            """
            INSERT INTO document_chunks (
                id, document_id, sequence, content, start_pos, end_pos,
                token_count, embedding_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chunk.id,
                chunk.document_id,
                chunk.sequence,
                chunk.content,
                chunk.start_pos,
                chunk.end_pos,
                chunk.token_count,
                chunk.embedding_id,
                datetime.utcnow().isoformat(),
            ),
        )

        return chunk

    def create_many(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Create multiple chunks."""
        for chunk in chunks:
            self.create(chunk)
        return chunks

    def get_by_document(self, document_id: str) -> List[DocumentChunk]:
        """Get chunks for a document."""
        cursor = self.db.execute(
            """
            SELECT * FROM document_chunks 
            WHERE document_id = ? 
            ORDER BY sequence
            """,
            (document_id,),
        )
        return [self._row_to_chunk(row) for row in cursor.fetchall()]

    def delete_by_document(self, document_id: str) -> int:
        """Delete all chunks for a document."""
        cursor = self.db.execute(
            "DELETE FROM document_chunks WHERE document_id = ?", (document_id,)
        )
        return cursor.rowcount

    def _row_to_chunk(self, row: sqlite3.Row) -> DocumentChunk:
        """Convert database row to DocumentChunk."""
        return DocumentChunk(
            id=row["id"],
            document_id=row["document_id"],
            content=row["content"],
            sequence=row["sequence"],
            start_pos=row["start_pos"],
            end_pos=row["end_pos"],
            token_count=row["token_count"],
            embedding_id=row["embedding_id"],
        )


class ContextRepository:
    """Repository for context operations."""

    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db

    def create(self, context: PathContext) -> PathContext:
        """Create a new context."""
        now = datetime.utcnow().isoformat()
        self.db.execute(
            """
            INSERT INTO contexts (id, target_id, context_type, content, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (context.id, context.path, context.context_type, context.context, now, now),
        )
        return context

    def get_by_target(self, target_id: str, context_type: str = "path") -> Optional[PathContext]:
        """Get context by target_id and context_type."""
        cursor = self.db.execute(
            "SELECT * FROM contexts WHERE target_id = ? AND context_type = ?",
            (target_id, context_type),
        )
        row = cursor.fetchone()
        return self._row_to_context(row) if row else None

    def get_by_path(self, path: str) -> Optional[PathContext]:
        """Get context by path (backward-compatible alias)."""
        return self.get_by_target(path, "path")

    def list_all(self) -> List[PathContext]:
        """List all contexts."""
        cursor = self.db.execute("SELECT * FROM contexts ORDER BY context_type, target_id")
        return [self._row_to_context(row) for row in cursor.fetchall()]

    def list_by_type(self, context_type: str) -> List[PathContext]:
        """List contexts by type."""
        cursor = self.db.execute(
            "SELECT * FROM contexts WHERE context_type = ? ORDER BY target_id", (context_type,)
        )
        return [self._row_to_context(row) for row in cursor.fetchall()]

    def list_by_collection(self, collection_id: str) -> List[PathContext]:
        """List contexts for a collection."""
        cursor = self.db.execute(
            "SELECT * FROM contexts WHERE context_type = 'collection' AND target_id = ? ORDER BY target_id",
            (collection_id,),
        )
        return [self._row_to_context(row) for row in cursor.fetchall()]

    def update(self, context: PathContext) -> PathContext:
        """Update a context."""
        self.db.execute(
            """
            UPDATE contexts
            SET content = ?, updated_at = ?
            WHERE id = ?
            """,
            (context.context, datetime.utcnow().isoformat(), context.id),
        )
        return context

    def delete(self, context_id: str) -> bool:
        """Delete a context."""
        cursor = self.db.execute("DELETE FROM contexts WHERE id = ?", (context_id,))
        return cursor.rowcount > 0

    def delete_orphaned_paths(self) -> int:
        """Delete path contexts whose target_id no longer exists in documents table."""
        cursor = self.db.execute("""
            DELETE FROM contexts
            WHERE context_type = 'path'
            AND target_id NOT IN (SELECT path FROM documents)
        """)
        return cursor.rowcount

    def _row_to_context(self, row: sqlite3.Row) -> PathContext:
        """Convert database row to PathContext."""
        return PathContext(
            id=row["id"],
            path=row["target_id"],
            collection_id=None,  # No longer stored; acceptable for transition
            context_type=row["context_type"],
            context=row["content"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


# Backward-compatible alias
PathContextRepository = ContextRepository


class LLMCacheRepository:
    """Repository for LLM cache operations."""

    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db

    def get(self, model_name: str, prompt_hash: str) -> Optional[str]:
        """Get cached response."""
        cursor = self.db.execute(
            """
            SELECT response FROM llm_cache 
            WHERE model_name = ? AND prompt_hash = ?
            AND (expires_at IS NULL OR expires_at > ?)
            """,
            (model_name, prompt_hash, datetime.utcnow().isoformat()),
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def set(
        self,
        model_name: str,
        prompt_hash: str,
        prompt: str,
        response: str,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Cache a response."""
        expires_at = None
        if ttl_seconds:
            expires_at = datetime.utcnow().timestamp() + ttl_seconds
            expires_at = datetime.fromtimestamp(expires_at).isoformat()

        self.db.execute(
            """
            INSERT OR REPLACE INTO llm_cache 
            (id, model_name, prompt_hash, prompt, response, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"{model_name}:{prompt_hash}",
                model_name,
                prompt_hash,
                prompt,
                response,
                datetime.utcnow().isoformat(),
                expires_at,
            ),
        )

    def clear_expired(self) -> int:
        """Clear expired cache entries."""
        cursor = self.db.execute(
            "DELETE FROM llm_cache WHERE expires_at IS NOT NULL AND expires_at <= ?",
            (datetime.utcnow().isoformat(),),
        )
        return cursor.rowcount
