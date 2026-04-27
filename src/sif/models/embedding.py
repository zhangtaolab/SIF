"""Pydantic models for Embedding operations."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ModelType(str, Enum):
    """Type of embedding model."""

    GGUF = "gguf"
    SENTENCE_TRANSFORMERS = "sentence_transformers"
    OPENAI = "openai"
    HUGGINGFACE = "huggingface"
    MODELSCOPE = "modelscope"


class EmbeddingConfig(BaseModel):
    """Configuration for embedding models."""

    model_type: ModelType = Field(ModelType.MODELSCOPE, description="Model type")
    model_path: str | None = Field(None, description="Path to model file")
    model_name: str = Field("Qwen/Qwen3-Embedding-0.6B", description="Model name or identifier")

    # Model parameters
    embedding_dim: int = Field(1024, ge=1, description="Embedding dimension")
    max_tokens: int = Field(512, ge=1, description="Maximum tokens per input")
    batch_size: int = Field(32, ge=1, description="Batch size for inference")

    # GGUF specific
    n_gpu_layers: int = Field(0, ge=0, description="Number of GPU layers")
    n_ctx: int = Field(2048, ge=512, description="Context size")

    # API keys (for remote models)
    api_key: str | None = Field(None, exclude=True)
    api_base: str | None = None

    # Caching
    cache_embeddings: bool = Field(True, description="Cache embeddings")
    cache_dir: str | None = None


class EmbeddingModelInfo(BaseModel):
    """Information about an embedding model."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Model ID")
    name: str = Field(..., description="Model name")
    model_type: ModelType = Field(...)
    embedding_dim: int = Field(..., ge=1)
    max_tokens: int = Field(..., ge=1)
    loaded: bool = Field(False, description="Whether model is loaded")
    device: str | None = None


class EmbeddingRequest(BaseModel):
    """Request for generating embeddings."""

    texts: list[str] = Field(..., min_length=1, description="Texts to embed")
    normalize: bool = Field(True, description="Normalize embeddings")


class EmbeddingResponse(BaseModel):
    """Response with generated embeddings."""

    embeddings: list[list[float]] = Field(..., description="Generated embeddings")
    model_id: str = Field(..., description="Model used")
    dimensions: int = Field(..., ge=1)
    total_tokens: int = Field(..., ge=0)
    processing_time_ms: float = Field(..., ge=0)
