"""Configuration settings for SIF."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from sif.config.constants import APP_NAME, DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE


class Settings(BaseSettings):
    """Application settings using Pydantic Settings.

    Settings are loaded from environment variables and .env files.
    Environment variables should be prefixed with SIF_.
    """

    model_config = SettingsConfigDict(
        env_prefix="SIF_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application settings
    app_name: str = Field(default=APP_NAME, description="Application name")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # Database settings
    db_path: Path | None = Field(
        default=None,
        description="Path to SQLite database file",
    )

    # Model settings
    model_path: Path | None = Field(
        default=None,
        description="Path to embedding model file",
    )
    model_name: str = Field(
        default="Qwen/Qwen3-Embedding-0.6B",
        description="Embedding model name",
    )
    embedding_dim: int = Field(
        default=1024,
        ge=1,
        description="Embedding dimension",
    )
    max_tokens: int = Field(
        default=512,
        ge=1,
        description="Maximum tokens per input",
    )
    batch_size: int = Field(
        default=32,
        ge=1,
        description="Batch size for inference",
    )
    model_type: str = Field(
        default="modelscope",
        description="Embedding model type (gguf, sentence_transformers, openai, huggingface, modelscope)",
    )
    n_gpu_layers: int = Field(
        default=0,
        ge=0,
        description="Number of GPU layers for GGUF models",
    )
    api_key: str | None = Field(
        default=None,
        description="API key for remote embedding models",
        repr=False,
    )
    api_base: str | None = Field(
        default=None,
        description="Base URL for remote embedding API",
    )

    # Reranker settings
    reranker_model_name: str = Field(
        default="Qwen/Qwen3-Reranker-0.6B",
        description="Reranker model name",
    )
    reranker_model_path: Path | None = Field(
        default=None,
        description="Path to local reranker model file",
    )
    reranker_model_type: str = Field(
        default="sentence_transformers",
        description="Reranker model type (gguf, sentence_transformers)",
    )
    reranker_batch_size: int = Field(
        default=32,
        ge=1,
        description="Batch size for reranker inference",
    )

    # Chunking settings
    chunk_size: int = Field(
        default=DEFAULT_CHUNK_SIZE,
        ge=100,
        description="Default chunk size in tokens",
    )
    chunk_overlap: int = Field(
        default=DEFAULT_CHUNK_OVERLAP,
        ge=0,
        description="Default chunk overlap in tokens",
    )

    # Search settings
    default_search_type: str = Field(
        default="hybrid",
        description="Default search type (bm25, vector, hybrid)",
    )
    default_limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Default search result limit",
    )

    # MCP server settings
    mcp_host: str = Field(
        default="127.0.0.1",
        description="MCP HTTP server host",
    )
    mcp_port: int = Field(
        default=8080,
        ge=1,
        le=65535,
        description="MCP HTTP server port",
    )
    mcp_transport: str = Field(
        default="stdio",
        description="MCP transport type (stdio, http)",
    )

    # Cache settings
    cache_dir: Path | None = Field(
        default=None,
        description="Cache directory path",
    )
    cache_embeddings: bool = Field(
        default=True,
        description="Whether to cache embeddings",
    )

    @field_validator("model_type")
    @classmethod
    def validate_model_type(cls, v: str) -> str:
        """Validate model_type is one of the supported backends."""
        valid_types = {"sentence_transformers", "gguf", "openai", "modelscope", "huggingface"}
        if v not in valid_types:
            raise ValueError(f"Invalid model_type: {v}. Must be one of {sorted(valid_types)}")
        return v

    @field_validator("api_base")
    @classmethod
    def validate_api_base(cls, v: str | None) -> str | None:
        """Validate api_base is an HTTP or HTTPS URL."""
        if v is None:
            return None
        v_lower = v.lower()
        if not v_lower.startswith("http://") and not v_lower.startswith("https://"):
            raise ValueError("api_base must be an HTTP or HTTPS URL")
        return v

    @field_validator("db_path", "cache_dir", mode="before")
    @classmethod
    def expand_path(cls, v: str | Path | None) -> Path | None:
        """Expand user home directory in paths."""
        if v is None:
            return None
        path = Path(v).expanduser()
        return path

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v_upper

    def get_db_path(self) -> Path:
        """Get the database path, creating default if not set."""
        if self.db_path:
            return self.db_path

        from platformdirs import user_data_dir  # noqa: PLC0415

        data_dir = Path(user_data_dir(self.app_name))
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / "sif.db"

    def get_cache_dir(self) -> Path:
        """Get the cache directory, creating default if not set."""
        if self.cache_dir:
            return self.cache_dir

        from platformdirs import user_cache_dir  # noqa: PLC0415

        cache_dir = Path(user_cache_dir(self.app_name))
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Uses lru_cache to ensure settings are loaded only once.
    """
    return Settings()
