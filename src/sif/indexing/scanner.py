"""File scanning utilities."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ScanResult:
    """Result of scanning a directory."""

    files: list[Path] = field(default_factory=list)
    scanned_dirs: set[Path] = field(default_factory=set)
    file_count: int = 0

    def __post_init__(self):
        self.file_count = len(self.files)


class FileScanner:
    """Scanner for finding files matching patterns."""

    DEFAULT_IGNORE_PATTERNS = (
        "node_modules",
        ".git",
        ".svn",
        ".hg",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".tox",
        ".venv",
        "venv",
        "env",
        ".env",
        "dist",
        "build",
        "*.egg-info",
        ".DS_Store",
        "Thumbs.db",
        "*.swp",
        "*.swo",
        "*~",
        ".idea",
        ".vscode",
    )

    def __init__(self) -> None:
        """Initialize the file scanner."""

    def scan(
        self,
        root_path: Path,
        pattern: str = "**/*.md",
        ignore_patterns: list[str] | None = None,
    ) -> ScanResult:
        """Scan a directory for files matching a pattern.

        Args:
            root_path: Root directory to scan
            pattern: Glob pattern to match files
            ignore_patterns: Patterns to ignore

        Returns:
            Scan result with matching files
        """
        root_path = Path(root_path).resolve()

        # Combine default and custom ignore patterns
        all_ignore_patterns = list(self.DEFAULT_IGNORE_PATTERNS)
        if ignore_patterns:
            all_ignore_patterns.extend(ignore_patterns)

        result = ScanResult()
        result.scanned_dirs.add(root_path)

        # Use rglob for recursive matching
        for file_path in root_path.rglob(pattern):
            if not file_path.is_file():
                continue

            # Check if file should be ignored
            if self._should_ignore(file_path, root_path, all_ignore_patterns):
                continue

            result.files.append(file_path)

        result.file_count = len(result.files)
        return result

    def _should_ignore(
        self,
        file_path: Path,
        root_path: Path,
        ignore_patterns: list[str],
    ) -> bool:
        """Check if a file should be ignored.

        Args:
            file_path: Path to check
            root_path: Root directory
            ignore_patterns: Patterns to ignore

        Returns:
            True if file should be ignored
        """
        # Get relative path from root
        try:
            rel_path = file_path.relative_to(root_path)
        except ValueError:
            return False

        # Check each part of the path against ignore patterns
        for part in rel_path.parts:
            for pattern in ignore_patterns:
                if fnmatch.fnmatch(part, pattern):
                    return True
                if fnmatch.fnmatch(str(rel_path), pattern):
                    return True

        # Check filename
        return any(fnmatch.fnmatch(file_path.name, pattern) for pattern in ignore_patterns)

    def get_stats(self, scan_result: ScanResult) -> dict:
        """Get statistics about a scan result.

        Args:
            scan_result: Scan result

        Returns:
            Statistics dictionary
        """
        total_size = sum(f.stat().st_size for f in scan_result.files if f.exists())

        # Count by extension
        extensions = {}
        for f in scan_result.files:
            ext = f.suffix.lower() or "(no extension)"
            extensions[ext] = extensions.get(ext, 0) + 1

        return {
            "file_count": scan_result.file_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "extensions": extensions,
        }
