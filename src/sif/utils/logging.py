"""Logging utilities."""

from __future__ import annotations

import contextlib
import logging
import os
import sys
import warnings
from typing import Optional

# Default logging format
DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
SIMPLE_FORMAT = "%(levelname)s: %(message)s"

# Noisy third-party loggers to suppress in quiet mode
_NOISY_LOGGERS = [
    "modelscope",
    "transformers",
    "sentence_transformers",
    "torch",
    "urllib3",
    "huggingface_hub",
    "auto_gptq",
    "bitsandbytes",
]

# Global quiet mode flag
_quiet_mode = False


def is_quiet() -> bool:
    """Check if quiet mode is enabled."""
    return _quiet_mode


def set_quiet(quiet: bool = True) -> None:
    """Set quiet mode globally.

    Use this when quiet mode is triggered after setup_logging has already run.
    """
    global _quiet_mode
    _quiet_mode = quiet
    if quiet:
        _apply_quiet_mode()


def _apply_quiet_mode() -> None:
    """Apply quiet mode side effects (logging, env vars, warnings)."""
    logging.disable(logging.INFO)
    for name in _NOISY_LOGGERS:
        lib_logger = logging.getLogger(name)
        lib_logger.setLevel(logging.WARNING)
        for h in lib_logger.handlers[:]:
            lib_logger.removeHandler(h)
        lib_logger.propagate = False

    os.environ.setdefault("TQDM_DISABLE", "1")
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

    try:
        from transformers import logging as transformers_logging

        transformers_logging.set_verbosity_error()
    except ImportError:
        pass

    warnings.filterwarnings("ignore")


@contextlib.contextmanager
def suppress_output():
    """Suppress both stdout and stderr output within the context block."""
    with open(os.devnull, "w") as devnull:
        with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
            yield


@contextlib.contextmanager
def suppress_stdout():
    """Suppress stdout output within the context block."""
    with open(os.devnull, "w") as devnull, contextlib.redirect_stdout(devnull):
        yield


@contextlib.contextmanager
def suppress_stderr():
    """Suppress stderr output within the context block."""
    with open(os.devnull, "w") as devnull, contextlib.redirect_stderr(devnull):
        yield


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
    global _quiet_mode
    _quiet_mode = level.upper() == "WARNING"

    if format_str is None:
        format_str = SIMPLE_FORMAT if level in ("INFO", "WARNING") else DEFAULT_FORMAT

    # Create formatter
    formatter = logging.Formatter(format_str)

    # Create handler if not provided
    if handler is None:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger("sif")
    root_logger.setLevel(getattr(logging, level.upper()))
    root_logger.handlers = []
    root_logger.addHandler(handler)

    # Don't propagate to parent
    root_logger.propagate = False

    # In quiet mode, suppress noisy third-party libraries and progress bars
    if _quiet_mode:
        _apply_quiet_mode()


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(f"sif.{name}")
