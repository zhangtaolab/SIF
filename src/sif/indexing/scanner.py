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

    def __post_init__(self) -> None:
        """Initialize file_count from files list."""
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
        # Editor/atomic-save temp noise (D-08): macOS .sb-* sidecars, Vim's
        # 4913 buffer-housekeeping file, Emacs .# lock files, and generic
        # .tmp scratch. Shared by scan and watch so live events can never
        # index what a scan would skip.
        "*.sb-*",
        "4913",
        ".#*",
        "*.tmp",
    )

    def __init__(self) -> None:
        """Initialize the file scanner."""

    @staticmethod
    def matches(
        root_path: Path,
        file_path: Path,
        pattern: str = "**/*.md",
        ignore_patterns: list[str] | None = None,
    ) -> bool:
        """Shared scan/watch membership predicate (D-07).

        True exactly when ``file_path`` would appear in ``scan(root_path)``
        output: under the resolved root, matching ``pattern`` with rglob
        semantics (a ``**/`` prefix also matches zero directories), and not
        ignored by the combined default + settings + per-call ignore list.
        Watch-side event filtering consumes this same predicate so live
        events can never index what a scan would skip.

        Args:
            root_path: Collection root directory
            file_path: Candidate file path
            pattern: Glob pattern to match (rglob semantics)
            ignore_patterns: Per-collection ignore patterns

        Returns:
            True if the path is indexable under this root and pattern
        """
        root = Path(root_path).resolve()
        candidate = Path(file_path).resolve()
        if not candidate.is_relative_to(root):
            return False

        rel_path = str(candidate.relative_to(root))
        # rglob semantics: "**/p" also matches zero directories, so a
        # root-level file matches "**/*.md" exactly as rglob would.
        pattern_forms = [pattern]
        if pattern.startswith("**/"):
            pattern_forms.append(pattern[3:])
        if not any(fnmatch.fnmatch(rel_path, form) for form in pattern_forms):
            return False

        all_ignore_patterns = FileScanner._combined_ignore_patterns(ignore_patterns)
        return not FileScanner._should_ignore(candidate, root, all_ignore_patterns)

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

        # Combine default, settings-global, and custom ignore patterns so the
        # scan and the watch predicate share one list by construction (D-07).
        all_ignore_patterns = self._combined_ignore_patterns(ignore_patterns)

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

    @staticmethod
    def _combined_ignore_patterns(ignore_patterns: list[str] | None) -> list[str]:
        """Assemble the one ignore list shared by scan() and matches() (D-07/A4).

        The ``watch_ignore_patterns`` setting extends the SHARED predicate —
        it affects scan and watch alike, so the two can never diverge.
        """
        from sif.config.settings import get_settings  # noqa: PLC0415

        combined = list(FileScanner.DEFAULT_IGNORE_PATTERNS)
        combined.extend(get_settings().watch_ignore_patterns)
        if ignore_patterns:
            combined.extend(ignore_patterns)
        return combined

    @staticmethod
    def _should_ignore(
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
