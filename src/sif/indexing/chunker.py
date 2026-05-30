"""Document chunking strategies."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod

from sif.core.models import DocumentChunk


class Chunker(ABC):
    """Base class for document chunkers."""

    @abstractmethod
    def chunk(self, text: str) -> list[DocumentChunk]:
        """Split text into chunks.

        Args:
            text: Text to chunk

        Returns:
            List of chunks
        """
        pass


class FixedSizeChunker(Chunker):
    """Chunk text into fixed-size pieces with overlap."""

    def __init__(self, chunk_size: int = 1000, overlap: int = 100) -> None:
        """Initialize fixed-size chunker.

        Args:
            chunk_size: Target chunk size in characters
            overlap: Overlap between chunks in characters
        """
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[DocumentChunk]:
        """Split text into fixed-size chunks."""
        chunks = []
        start = 0
        sequence = 0

        while start < len(text):
            end = start + self.chunk_size

            # Try to find a good break point
            if end < len(text):
                # Look for newline or space
                for i in range(min(end + 100, len(text)) - 1, end - 1, -1):
                    if text[i] in "\n ":
                        end = i + 1
                        break

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(
                    DocumentChunk(
                        content=chunk_text,
                        sequence=sequence,
                        start_pos=start,
                        end_pos=end,
                    ),
                )
                sequence += 1

            # Move start with overlap
            start = end - self.overlap
            start = min(end, start)

        return chunks


class MarkdownChunker(Chunker):
    """Chunk markdown documents by headings."""

    def __init__(self, max_chunk_size: int = 2000) -> None:
        """Initialize markdown chunker.

        Args:
            max_chunk_size: Maximum chunk size in characters
        """
        self.max_chunk_size = max_chunk_size
        self.heading_pattern = re.compile(r"^(#{1,6}\s+.+)$", re.MULTILINE)

    def chunk(self, text: str) -> list[DocumentChunk]:
        """Split markdown by headings."""
        # Find all headings
        headings = list(self.heading_pattern.finditer(text))

        if not headings:
            # No headings, use fixed-size chunking
            return FixedSizeChunker(self.max_chunk_size).chunk(text)

        chunks = []
        sequence = 0

        for i, match in enumerate(headings):
            start = match.start()
            end = headings[i + 1].start() if i + 1 < len(headings) else len(text)

            chunk_text = text[start:end].strip()

            # If chunk is too large, split it further
            if len(chunk_text) > self.max_chunk_size:
                sub_chunks = FixedSizeChunker(self.max_chunk_size, 100).chunk(chunk_text)
                for sub_chunk in sub_chunks:
                    sub_chunk.sequence = sequence
                    chunks.append(sub_chunk)
                    sequence += 1
            else:
                chunks.append(
                    DocumentChunk(
                        content=chunk_text,
                        sequence=sequence,
                        start_pos=start,
                        end_pos=end,
                    ),
                )
                sequence += 1

        return chunks


class CodeChunker(Chunker):
    """Chunk code files by functions/classes."""

    def __init__(self, max_chunk_size: int = 2000, language: str = "python") -> None:
        """Initialize code chunker.

        Args:
            max_chunk_size: Maximum chunk size in characters
            language: Programming language
        """
        self.max_chunk_size = max_chunk_size
        self.language = language

    def chunk(self, text: str) -> list[DocumentChunk]:
        """Split code by functions/classes."""
        # Simple regex-based approach for Python
        if self.language == "python":
            pattern = re.compile(r"^(def\s+|class\s+)", re.MULTILINE)
        else:
            # Fallback to fixed-size for other languages
            return FixedSizeChunker(self.max_chunk_size).chunk(text)

        matches = list(pattern.finditer(text))

        if not matches:
            return FixedSizeChunker(self.max_chunk_size).chunk(text)

        chunks = []
        sequence = 0

        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

            chunk_text = text[start:end].strip()

            if len(chunk_text) > self.max_chunk_size:
                sub_chunks = FixedSizeChunker(self.max_chunk_size, 100).chunk(chunk_text)
                for sub_chunk in sub_chunks:
                    sub_chunk.sequence = sequence
                    chunks.append(sub_chunk)
                    sequence += 1
            else:
                chunks.append(
                    DocumentChunk(
                        content=chunk_text,
                        sequence=sequence,
                        start_pos=start,
                        end_pos=end,
                    ),
                )
                sequence += 1

        return chunks


class AutoChunker(Chunker):
    """Automatically select chunking strategy based on content."""

    def __init__(self, max_chunk_size: int = 2000) -> None:
        """Initialize auto chunker.

        Args:
            max_chunk_size: Maximum chunk size in characters
        """
        self.max_chunk_size = max_chunk_size

    def chunk(self, text: str) -> list[DocumentChunk]:
        """Automatically select and apply chunking strategy."""
        # Check if markdown
        if "#" in text and re.search(r"^#+\s+", text, re.MULTILINE):
            return MarkdownChunker(self.max_chunk_size).chunk(text)

        # Check if code (has function/class definitions)
        if re.search(r"^(def\s+|class\s+)", text, re.MULTILINE):
            return CodeChunker(self.max_chunk_size).chunk(text)

        # Default to fixed-size
        return FixedSizeChunker(self.max_chunk_size).chunk(text)


def create_chunker(strategy: str, **kwargs) -> Chunker:
    """Create a chunker by strategy name.

    Args:
        strategy: Chunking strategy ("fixed", "markdown", "code", "auto")
        **kwargs: Additional arguments for the chunker

    Returns:
        Chunker instance
    """
    if strategy == "fixed":
        return FixedSizeChunker(**kwargs)
    if strategy == "markdown":
        return MarkdownChunker(**kwargs)
    if strategy == "code":
        return CodeChunker(**kwargs)
    if strategy == "auto":
        return AutoChunker(**kwargs)
    raise ValueError(f"Unknown chunking strategy: {strategy}")
