"""Logging utilities."""

from __future__ import annotations

import logging
import sys
from typing import Optional

# Default logging format
DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
SIMPLE_FORMAT = "%(levelname)s: %(message)s"


def setup_logging(
    level: str = "INFO",
    format_str: Optional[str] = None,
    handler: Optional[logging.Handler] = None,
) -> None:
    """Setup logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        format_str: Log format string
        handler: Custom log handler
    """
    if format_str is None:
        format_str = SIMPLE_FORMAT if level in ("INFO", "WARNING") else DEFAULT_FORMAT
    
    # Create formatter
    formatter = logging.Formatter(format_str)
    
    # Create handler if not provided
    if handler is None:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger("docsift")
    root_logger.setLevel(getattr(logging, level.upper()))
    root_logger.handlers = []
    root_logger.addHandler(handler)
    
    # Don't propagate to parent
    root_logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(f"docsift.{name}")
