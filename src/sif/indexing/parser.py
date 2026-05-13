"""Document parsing utilities."""

from __future__ import annotations

import hashlib
import re
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import frontmatter


@dataclass
class ParsedDocument:
    """Result of parsing a document."""

    path: str
    content: str
    title: str
    metadata: dict[str, Any]
    checksum: str
    mtime: float


class MarkdownParser:
    """Parser for Markdown documents."""

    def __init__(self) -> None:
        """Initialize the markdown parser."""
        self.title_pattern = re.compile(r"^#\s+(.+)$", re.MULTILINE)

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a markdown file.

        Args:
            file_path: Path to the markdown file

        Returns:
            Parsed document
        """
        # Read file
        content = file_path.read_text(encoding="utf-8")

        # Get file stats
        stat = file_path.stat()
        mtime = stat.st_mtime

        # Parse frontmatter
        try:
            post = frontmatter.loads(content)
            body = post.content
            metadata = dict(post.metadata)
        except Exception:
            body = content
            metadata = {}

        # Extract title
        title = metadata.get("title", "")
        if not title:
            # Try to extract from first H1
            match = self.title_pattern.search(body)
            title = match.group(1).strip() if match else file_path.stem

        # Calculate checksum
        checksum = hashlib.sha256(content.encode()).hexdigest()

        return ParsedDocument(
            path=str(file_path.resolve()),
            content=body,
            title=title,
            metadata=metadata,
            checksum=checksum,
            mtime=mtime,
        )


class TextParser:
    """Parser for plain text documents."""

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a text file."""
        content = file_path.read_text(encoding="utf-8")
        stat = file_path.stat()

        # Use first line as title if not too long
        lines = content.split("\n")
        title = ""
        for line in lines:
            stripped = line.strip()
            if stripped and len(stripped) < 100:
                title = stripped
                break

        if not title:
            title = file_path.stem

        checksum = hashlib.sha256(content.encode()).hexdigest()

        return ParsedDocument(
            path=str(file_path.resolve()),
            content=content,
            title=title,
            metadata={},
            checksum=checksum,
            mtime=stat.st_mtime,
        )


class CodeParser:
    """Parser for code files."""

    # File extensions to language mapping
    LANGUAGE_MAP = types.MappingProxyType({
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "jsx",
        ".tsx": "tsx",
        ".rs": "rust",
        ".go": "go",
        ".java": "java",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "c",
        ".hpp": "cpp",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".kt": "kotlin",
        ".scala": "scala",
        ".r": "r",
        ".sh": "bash",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".json": "json",
        ".toml": "toml",
        ".xml": "xml",
        ".sql": "sql",
    })

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a code file."""
        content = file_path.read_text(encoding="utf-8")
        stat = file_path.stat()

        # Detect language
        ext = file_path.suffix.lower()
        language = self.LANGUAGE_MAP.get(ext, "text")

        # Try to extract title from comments
        title = file_path.stem

        # For Python, look for module docstring
        if language == "python":
            match = re.search(r'^[\'"]{3}(.+?)[\'"]{3}', content, re.MULTILINE | re.DOTALL)
            if match:
                docstring = match.group(1).strip()
                first_line = docstring.split("\n")[0].strip()
                if first_line:
                    title = first_line[:100]

        checksum = hashlib.sha256(content.encode()).hexdigest()

        return ParsedDocument(
            path=str(file_path.resolve()),
            content=content,
            title=title,
            metadata={"language": language},
            checksum=checksum,
            mtime=stat.st_mtime,
        )


def create_parser(file_path: Path) -> MarkdownParser | TextParser | CodeParser | None:
    """Create appropriate parser for a file.

    Args:
        file_path: Path to the file

    Returns:
        Parser instance or None
    """
    ext = file_path.suffix.lower()

    if ext in [".md", ".markdown", ".mdx"]:
        return MarkdownParser()
    if ext in CodeParser.LANGUAGE_MAP:
        return CodeParser()
    if ext in [".txt", ".rst", ".adoc"]:
        return TextParser()

    return None
