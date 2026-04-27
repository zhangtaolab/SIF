"""Utility functions and helpers for DocSift.

This package provides various utility functions:
- Logging configuration
- File path utilities
- Text processing helpers
- Progress indicators
"""

from docsift.utils.logging import setup_logging, get_logger
from docsift.utils.paths import get_data_dir, get_cache_dir, get_config_dir
from docsift.utils.text import normalize_text, truncate_text, count_tokens
from docsift.utils.progress import ProgressTracker

__all__ = [
    "setup_logging",
    "get_logger",
    "get_data_dir",
    "get_cache_dir",
    "get_config_dir",
    "normalize_text",
    "truncate_text",
    "count_tokens",
    "ProgressTracker",
]
