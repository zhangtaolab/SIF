"""Document chunking strategies."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod

from sif.core.models import DocumentChunk


# The chunkers operate on characters while SIF_CHUNK_SIZE/SIF_CHUNK_OVERLAP
# are documented in tokens. Four characters per token is the usual English
# approximation; converting at the call site keeps the chunkers themselves
# character-based and backward compatible.
CHARS_PER_TOKEN = 4


def token_size_to_chars(tokens: int) -> int:
    """Convert a token budget to an approximate character count."""
    return max(1, int(tokens) * CHARS_PER_TOKEN)


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

            # Move start with overlap. Consume the final window instead of
            # reprocessing a suffix that is entirely within the last chunk.
            if end >= len(text):
                break
            start = max(start + 1, end - self.overlap)

        return chunks


class MarkdownChunker(Chunker):
    """Chunk markdown documents by headings."""

    def __init__(self, max_chunk_size: int = 2000, overlap: int | None = None) -> None:
        """Initialize markdown chunker.

        Args:
            max_chunk_size: Maximum chunk size in characters
            overlap: Overlap between split sub-chunks in characters; None keeps
                the historical defaults (100 for heading-free fallback, 0 for
                oversized-section subdivision)
        """
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        self.heading_pattern = re.compile(r"^(#{1,6}\s+.+)$", re.MULTILINE)

    def chunk(self, text: str) -> list[DocumentChunk]:
        """Split markdown by headings."""
        # Find all headings
        headings = list(self.heading_pattern.finditer(text))

        if not headings:
            # No headings, use fixed-size chunking
            return FixedSizeChunker(
                self.max_chunk_size,
                overlap=self.overlap if self.overlap is not None else 100,
            ).chunk(text)

        chunks = []
        sequence = 0

        for i, match in enumerate(headings):
            start = match.start()
            end = headings[i + 1].start() if i + 1 < len(headings) else len(text)

            chunk_text = text[start:end].strip()

            # If chunk is too large, split it further
            if len(chunk_text) > self.max_chunk_size:
                sub_chunks = FixedSizeChunker(
                    self.max_chunk_size,
                    overlap=self.overlap if self.overlap is not None else 0,
                ).chunk(chunk_text)
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

    def __init__(
        self, max_chunk_size: int = 2000, language: str = "python", overlap: int | None = None
    ) -> None:
        """Initialize code chunker.

        Args:
            max_chunk_size: Maximum chunk size in characters
            language: Programming language
            overlap: Overlap between split sub-chunks in characters; None keeps
                the historical defaults (100 for fallback, 0 for subdivision)
        """
        self.max_chunk_size = max_chunk_size
        self.language = language
        self.overlap = overlap

    def chunk(self, text: str) -> list[DocumentChunk]:
        """Split code by functions/classes."""
        # Simple regex-based approach for Python
        if self.language == "python":
            pattern = re.compile(r"^(def\s+|class\s+)", re.MULTILINE)
        else:
            # Fallback to fixed-size for other languages
            return FixedSizeChunker(
                self.max_chunk_size,
                overlap=self.overlap if self.overlap is not None else 100,
            ).chunk(text)

        matches = list(pattern.finditer(text))

        if not matches:
            return FixedSizeChunker(
                self.max_chunk_size,
                overlap=self.overlap if self.overlap is not None else 100,
            ).chunk(text)

        chunks = []
        sequence = 0

        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

            chunk_text = text[start:end].strip()

            if len(chunk_text) > self.max_chunk_size:
                sub_chunks = FixedSizeChunker(
                    self.max_chunk_size,
                    overlap=self.overlap if self.overlap is not None else 0,
                ).chunk(chunk_text)
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

    def __init__(self, max_chunk_size: int = 2000, overlap: int | None = None) -> None:
        """Initialize auto chunker.

        Args:
            max_chunk_size: Maximum chunk size in characters
            overlap: Overlap between split sub-chunks in characters
        """
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[DocumentChunk]:
        """Automatically select and apply chunking strategy."""
        # Check if markdown
        if "#" in text and re.search(r"^#+\s+", text, re.MULTILINE):
            return MarkdownChunker(self.max_chunk_size, overlap=self.overlap).chunk(text)

        # Check if code (has function/class definitions)
        if re.search(r"^(def\s+|class\s+)", text, re.MULTILINE):
            return CodeChunker(self.max_chunk_size, overlap=self.overlap).chunk(text)

        # Default to fixed-size
        return FixedSizeChunker(
            self.max_chunk_size,
            overlap=self.overlap if self.overlap is not None else 100,
        ).chunk(text)


def create_chunker(strategy: str, **kwargs) -> Chunker:
    """Create a chunker by strategy name.

    Args:
        strategy: Chunking strategy ("fixed", "markdown", "code", "auto")
        **kwargs: Additional arguments for the chunker. ``chunk_size`` and
            ``max_chunk_size`` are accepted as aliases; ``overlap`` is
            forwarded to every strategy.

    Returns:
        Chunker instance
    """
    chunk_size = kwargs.pop("chunk_size", None)
    max_chunk_size = kwargs.pop("max_chunk_size", None)
    overlap = kwargs.pop("overlap", None)
    size = chunk_size or max_chunk_size
    if strategy == "fixed":
        return FixedSizeChunker(
            chunk_size=size or 1000,
            overlap=overlap if overlap is not None else 100,
        )
    if strategy == "markdown":
        return MarkdownChunker(max_chunk_size=size or 2000, overlap=overlap)
    if strategy == "code":
        return CodeChunker(
            max_chunk_size=size or 2000,
            language=kwargs.pop("language", "python"),
            overlap=overlap,
        )
    if strategy == "auto":
        return AutoChunker(max_chunk_size=size or 2000, overlap=overlap)
    raise ValueError(f"Unknown chunking strategy: {strategy}")
