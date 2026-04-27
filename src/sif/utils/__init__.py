"""Utility functions and helpers for SIF.

This package provides various utility functions:
- Logging configuration
- File path utilities
- Text processing helpers
- Progress indicators
"""

from sif.utils.logging import get_logger, setup_logging
from sif.utils.paths import get_cache_dir, get_config_dir, get_data_dir
from sif.utils.progress import ProgressTracker
from sif.utils.text import count_tokens, normalize_text, truncate_text


__all__ = [
    "ProgressTracker",
    "count_tokens",
    "get_cache_dir",
    "get_config_dir",
    "get_data_dir",
    "get_logger",
    "normalize_text",
    "setup_logging",
    "truncate_text",
]
