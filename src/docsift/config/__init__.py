"""Configuration management for DocSift.

This package provides configuration handling:
- Settings management via Pydantic Settings
- Environment variable support
- Configuration file handling
- Default values and validation
"""

from docsift.config.settings import Settings, get_settings
from docsift.config.constants import (
    DEFAULT_DB_PATH,
    DEFAULT_MODEL_PATH,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CHUNK_OVERLAP,
    APP_NAME,
    APP_VERSION,
)

__all__ = [
    "Settings",
    "get_settings",
    "DEFAULT_DB_PATH",
    "DEFAULT_MODEL_PATH",
    "DEFAULT_CHUNK_SIZE",
    "DEFAULT_CHUNK_OVERLAP",
    "APP_NAME",
    "APP_VERSION",
]
