"""Embedding cache for storing and retrieving embeddings."""

import hashlib
import json
from pathlib import Path

import sqlite3

from docsift.utils.logging import get_logger

logger = get_logger(__name__)


class EmbeddingCache:
    """Cache for embeddings to avoid recomputation.
    
    Uses SQLite for persistent storage of embeddings keyed by
    content hash. This allows embeddings to be reused across
    application restarts.
    """
    
    def __init__(self, cache_dir: Path | str) -> None:
        """Initialize embedding cache.
        
        Args:
            cache_dir: Directory for cache storage
        """
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        
        self._db_path = self._cache_dir / "embeddings_cache.db"
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize the cache database."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    content_hash TEXT PRIMARY KEY,
                    embedding TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index for faster lookups
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_model 
                ON embeddings(model_id)
            """)
            
            conn.commit()
    
    def _hash_content(self, content: str) -> str:
        """Create a hash of the content.
        
        Args:
            content: Content to hash
            
        Returns:
            SHA-256 hash of the content
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
    
    def get(self, content: str, model_id: str = "default") -> list[float] | None:
        """Get cached embedding for content.
        
        Args:
            content: Content to look up
            model_id: Model identifier for cache segmentation
            
        Returns:
            Cached embedding or None if not found
        """
        content_hash = self._hash_content(content)
        
        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.execute(
                    "SELECT embedding FROM embeddings WHERE content_hash = ? AND model_id = ?",
                    (content_hash, model_id),
                )
                row = cursor.fetchone()
                
                if row:
                    return json.loads(row[0])
        except Exception as e:
            logger.warning(f"Error reading from cache: {e}")
        
        return None
    
    def set(
        self,
        content: str,
        embedding: list[float],
        model_id: str = "default",
    ) -> None:
        """Store embedding in cache.
        
        Args:
            content: Content that was embedded
            embedding: The embedding vector
            model_id: Model identifier for cache segmentation
        """
        content_hash = self._hash_content(content)
        embedding_json = json.dumps(embedding)
        
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO embeddings 
                    (content_hash, embedding, model_id) 
                    VALUES (?, ?, ?)
                    """,
                    (content_hash, embedding_json, model_id),
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"Error writing to cache: {e}")
    
    def get_batch(
        self,
        contents: list[str],
        model_id: str = "default",
    ) -> list[list[float] | None]:
        """Get cached embeddings for multiple contents.
        
        Args:
            contents: List of contents to look up
            model_id: Model identifier
            
        Returns:
            List of embeddings (None if not in cache)
        """
        return [self.get(c, model_id) for c in contents]
    
    def set_batch(
        self,
        contents: list[str],
        embeddings: list[list[float]],
        model_id: str = "default",
    ) -> None:
        """Store multiple embeddings in cache.
        
        Args:
            contents: List of contents
            embeddings: List of embeddings
            model_id: Model identifier
        """
        for content, embedding in zip(contents, embeddings):
            self.set(content, embedding, model_id)
    
    def clear(self, model_id: str | None = None) -> int:
        """Clear cached embeddings.
        
        Args:
            model_id: If specified, only clear for this model
            
        Returns:
            Number of entries cleared
        """
        try:
            with sqlite3.connect(self._db_path) as conn:
                if model_id:
                    cursor = conn.execute(
                        "DELETE FROM embeddings WHERE model_id = ?",
                        (model_id,),
                    )
                else:
                    cursor = conn.execute("DELETE FROM embeddings")
                
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.warning(f"Error clearing cache: {e}")
            return 0
    
    def get_stats(self) -> dict:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*), model_id FROM embeddings GROUP BY model_id"
                )
                rows = cursor.fetchall()
                
                return {
                    "total_entries": sum(r[0] for r in rows),
                    "by_model": {r[1]: r[0] for r in rows},
                }
        except Exception as e:
            logger.warning(f"Error getting cache stats: {e}")
            return {"total_entries": 0, "by_model": {}}
