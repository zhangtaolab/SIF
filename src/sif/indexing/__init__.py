"""Document indexing functionality for DocSift.

This package provides document indexing capabilities:
- File system scanning
- Markdown parsing and chunking
- Document metadata extraction
"""

from sif.indexing.scanner import FileScanner, ScanResult
from sif.indexing.parser import MarkdownParser, ParsedDocument
from sif.indexing.chunker import Chunker, create_chunker

__all__ = [
    "FileScanner",
    "ScanResult",
    "MarkdownParser",
    "ParsedDocument",
    "Chunker",
    "create_chunker",
]
