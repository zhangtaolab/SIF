"""Configuration management for SIF.

This package provides configuration handling:
- Settings management via Pydantic Settings
- Environment variable support
- Configuration file handling
- Default values and validation
"""

from sif.config.constants import (
    APP_NAME,
    APP_VERSION,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_DB_PATH,
    DEFAULT_MODEL_PATH,
)
from sif.config.settings import Settings, get_settings


__all__ = [
    "APP_NAME",
    "APP_VERSION",
    "DEFAULT_CHUNK_OVERLAP",
    "DEFAULT_CHUNK_SIZE",
    "DEFAULT_DB_PATH",
    "DEFAULT_MODEL_PATH",
    "Settings",
    "get_settings",
]
