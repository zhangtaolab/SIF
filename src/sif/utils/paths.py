"""Path utilities for DocSift."""

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


def is_markdown_file(path: Path) -> bool:
    """Check if a file is a markdown file.

    Args:
        path: File path to check

    Returns:
        True if the file has a markdown extension
    """
    from sif.config.constants import MARKDOWN_EXTENSIONS

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
