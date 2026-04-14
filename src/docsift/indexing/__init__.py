"""Document indexing functionality for DocSift.

This package provides document indexing capabilities:
- File system scanning
- Markdown parsing and chunking
- Document metadata extraction
"""

from docsift.indexing.scanner import FileScanner, ScanResult
from docsift.indexing.parser import MarkdownParser, ParsedDocument
from docsift.indexing.chunker import Chunker, create_chunker

__all__ = [
    "FileScanner",
    "ScanResult",
    "MarkdownParser",
    "ParsedDocument",
    "Chunker",
    "create_chunker",
]
