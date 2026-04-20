"""Model download from ModelScope."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Optional

from docsift.utils.logging import get_logger, is_quiet, suppress_output

logger = get_logger(__name__)


class ModelDownloader:
    """Download models from ModelScope."""

    DEFAULT_MODELS = {
        "embedding": {
            "model_id": "iic/gte_Qwen2-7B-instruct",
            "description": "General text embedding model",
        },
        "reranker": {
            "model_id": "iic/gte_Qwen2-7B-instruct",
            "description": "Reranking model",
        },
        "query_expansion": {
            "model_id": "qwen/Qwen2.5-0.5B-Instruct",
            "description": "Query expansion model",
        },
    }

    def __init__(self, cache_dir: Optional[str | Path] = None) -> None:
        """Initialize model downloader.

        Args:
            cache_dir: Directory to cache downloaded models
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".docsift" / "models"
        self.cache_dir = Path(cache_dir).expanduser().resolve()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def download(
        self,
        model_id: str,
        revision: Optional[str] = None,
        force: bool = False,
    ) -> Path:
        """Download a model from ModelScope.

        Args:
            model_id: ModelScope model ID (e.g., "iic/gte_Qwen2-7B-instruct")
            revision: Model revision to download
            force: Force re-download even if cached

        Returns:
            Path to downloaded model directory
        """
        try:
            from modelscope import snapshot_download
        except ImportError:
            logger.error("modelscope not installed. Install with: pip install modelscope")
            raise

        # Create cache subdirectory for this model
        model_hash = hashlib.md5(model_id.encode()).hexdigest()[:8]
        model_cache_dir = self.cache_dir / model_hash

        # Check if already cached
        if not force and model_cache_dir.exists():
            # Check if model files exist
            if any(model_cache_dir.iterdir()):
                logger.info(f"Using cached model: {model_id}")
                return model_cache_dir

        # Download model
        logger.info(f"Downloading model from ModelScope: {model_id}")

        download_kwargs = {
            "model_id": model_id,
            "cache_dir": str(self.cache_dir),
        }

        if revision:
            download_kwargs["revision"] = revision

        try:
            if is_quiet():
                with suppress_output():
                    model_path = snapshot_download(**download_kwargs)
            else:
                model_path = snapshot_download(**download_kwargs)
            logger.info(f"Model downloaded to: {model_path}")
            return Path(model_path)
        except Exception as e:
            logger.error(f"Failed to download model {model_id}: {e}")
            raise

    def download_embedding_model(
        self,
        model_id: Optional[str] = None,
        force: bool = False,
    ) -> Path:
        """Download embedding model.

        Args:
            model_id: ModelScope model ID (uses default if None)
            force: Force re-download

        Returns:
            Path to downloaded model
        """
        if model_id is None:
            model_id = self.DEFAULT_MODELS["embedding"]["model_id"]

        return self.download(model_id, force=force)

    def download_reranker_model(
        self,
        model_id: Optional[str] = None,
        force: bool = False,
    ) -> Path:
        """Download reranker model.

        Args:
            model_id: ModelScope model ID (uses default if None)
            force: Force re-download

        Returns:
            Path to downloaded model
        """
        if model_id is None:
            model_id = self.DEFAULT_MODELS["reranker"]["model_id"]

        return self.download(model_id, force=force)

    def download_query_expansion_model(
        self,
        model_id: Optional[str] = None,
        force: bool = False,
    ) -> Path:
        """Download query expansion model.

        Args:
            model_id: ModelScope model ID (uses default if None)
            force: Force re-download

        Returns:
            Path to downloaded model
        """
        if model_id is None:
            model_id = self.DEFAULT_MODELS["query_expansion"]["model_id"]

        return self.download(model_id, force=force)

    def get_model_info(self, model_id: str) -> dict:
        """Get information about a model.

        Args:
            model_id: ModelScope model ID

        Returns:
            Model information dictionary
        """
        try:
            from modelscope.hub.api import HubApi

            api = HubApi()
            info = api.get_model_info(model_id)
            return {
                "model_id": model_id,
                "name": info.get("Name", ""),
                "description": info.get("Description", ""),
                "tags": info.get("Tags", []),
            }
        except Exception as e:
            logger.error(f"Failed to get model info for {model_id}: {e}")
            return {"model_id": model_id, "error": str(e)}

    def list_cached_models(self) -> list:
        """List all cached models.

        Returns:
            List of cached model directories
        """
        if not self.cache_dir.exists():
            return []

        models = []
        for item in self.cache_dir.iterdir():
            if item.is_dir():
                models.append(
                    {
                        "path": str(item),
                        "name": item.name,
                    }
                )

        return models

    def clear_cache(self) -> None:
        """Clear all cached models."""
        import shutil

        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Model cache cleared")
