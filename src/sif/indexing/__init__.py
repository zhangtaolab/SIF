"""Document indexing functionality for SIF.

This package provides document indexing capabilities:
- File system scanning
- Markdown parsing and chunking
- Document metadata extraction
"""

from sif.indexing.chunker import Chunker, create_chunker
from sif.indexing.parser import MarkdownParser, ParsedDocument
from sif.indexing.scanner import FileScanner, ScanResult


__all__ = [
    "Chunker",
    "FileScanner",
    "MarkdownParser",
    "ParsedDocument",
    "ScanResult",
    "create_chunker",
]
