"""Path utilities for SIF."""

from pathlib import Path

from platformdirs import user_cache_dir, user_config_dir, user_data_dir

from sif.config.constants import APP_NAME


def get_data_dir() -> Path:
    """Get the application data directory.

    Returns:
        Path to the data directory
    """
    path = Path(user_data_dir(APP_NAME))
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_cache_dir() -> Path:
    """Get the application cache directory.

    Returns:
        Path to the cache directory
    """
    path = Path(user_cache_dir(APP_NAME))
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_config_dir() -> Path:
    """Get the application config directory.

    Returns:
        Path to the config directory
    """
    path = Path(user_config_dir(APP_NAME))
    path.mkdir(parents=True, exist_ok=True)
    return path


def expand_path(path: str | Path) -> Path:
    """Expand a path, resolving ~ and environment variables.

    Args:
        path: Path to expand

    Returns:
        Expanded absolute path
    """
    return Path(path).expanduser().resolve()


def normalize_path(path: str | Path) -> str:
    """Normalize a path to its canonical string form.

    This is the single canonical definition of "same file" shared by search
    context attachment, ``context add``, and prune: two paths denote the same
    document iff ``normalize_path`` maps them to the same string. It expands
    ``~`` and resolves symlinks (e.g. ``/tmp`` -> ``/private/tmp`` on macOS)
    via :func:`expand_path`, while preserving non-existent tail components
    (``Path.resolve`` strict=False semantics) so context targets for
    not-yet-indexed files still normalize.

    Total function: a path that cannot be expanded (e.g. a ``~user`` form
    whose account no longer resolves, in a row stored before normalization
    existed or after a DB moved machines) degrades to the raw string instead
    of raising — a malformed stored row must never crash search or prune; it
    simply matches nothing, the same effective outcome minus the crash.

    Args:
        path: Path to normalize

    Returns:
        Canonical absolute path string, or the raw string form when the
        path cannot be expanded or resolved.
    """
    try:
        return str(expand_path(path))
    except (RuntimeError, OSError, ValueError):
        return str(path)


def is_markdown_file(path: Path) -> bool:
    """Check if a file is a markdown file.

    Args:
        path: File path to check

    Returns:
        True if the file has a markdown extension
    """
    from sif.config.constants import MARKDOWN_EXTENSIONS  # noqa: PLC0415

    return path.suffix.lower() in MARKDOWN_EXTENSIONS


def get_relative_path(path: Path, base: Path) -> Path:
    """Get path relative to a base directory.

    Args:
        path: Absolute path
        base: Base directory

    Returns:
        Relative path from base to path
    """
    try:
        return path.relative_to(base)
    except ValueError:
        return path
