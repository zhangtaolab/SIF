"""
MCP Tool Implementations

This module implements all MCP tools for DocSift:
- query: Hybrid search (FTS + Vector + Reranking)
- lex_search: BM25 full-text search
- vec_search: Vector semantic search
- get: Get document by path or doc_id
- multi_get: Batch get documents by pattern
- status: Get index status
"""

import logging
import fnmatch
from typing import Any, Optional, Protocol
from datetime import datetime

from .protocol import (
    QueryInput, QueryOutput,
    LexSearchInput, LexSearchOutput,
    VecSearchInput, VecSearchOutput,
    GetInput, GetOutput,
    MultiGetInput, MultiGetOutput,
    StatusInput, StatusOutput,
    SearchResult, Document, CollectionInfo,
    MCPTool, ToolInputSchema
)

logger = logging.getLogger(__name__)


# ============================================================================
# Search Backend Protocol
# ============================================================================

class SearchBackend(Protocol):
    """Protocol for search backend implementations."""
    
    async def hybrid_search(
        self,
        query: str,
        collections: Optional[list[str]] = None,
        limit: int = 10,
        min_score: float = 0.0
    ) -> list[SearchResult]:
        """Perform hybrid search (FTS + Vector + Reranking)."""
        ...
    
    async def lex_search(
        self,
        query: str,
        collections: Optional[list[str]] = None,
        limit: int = 10
    ) -> list[SearchResult]:
        """Perform BM25 full-text search."""
        ...
    
    async def vec_search(
        self,
        query: str,
        collections: Optional[list[str]] = None,
        limit: int = 10
    ) -> list[SearchResult]:
        """Perform vector semantic search."""
        ...
    
    async def get_document(
        self,
        path_or_docid: str,
        from_line: Optional[int] = None,
        max_lines: Optional[int] = None
    ) -> Optional[Document]:
        """Get a document by path or doc_id."""
        ...
    
    async def get_documents_by_pattern(
        self,
        pattern: str,
        max_bytes: Optional[int] = None
    ) -> tuple[list[Document], list[str]]:
        """Get documents matching a pattern."""
        ...
    
    async def get_status(self) -> tuple[list[CollectionInfo], int]:
        """Get index status."""
        ...


# ============================================================================
# Mock Search Backend (for testing/development)
# ============================================================================

class MockSearchBackend:
    """Mock search backend for testing and development."""
    
    def __init__(self):
        self._documents: dict[str, Document] = {}
        self._collections: dict[str, CollectionInfo] = {}
        self._init_mock_data()
    
    def _init_mock_data(self):
        """Initialize mock data."""
        # Add some mock documents
        for i in range(10):
            doc = Document(
                doc_id=f"doc_{i}",
                path=f"/docs/document_{i}.md",
                title=f"Document {i}",
                content=f"This is the content of document {i}. It contains information about various topics.",
                metadata={"category": "general", "index": i}
            )
            self._documents[doc.doc_id] = doc
            self._documents[doc.path] = doc
        
        # Add mock collections
        self._collections["default"] = CollectionInfo(
            name="default",
            document_count=10,
            last_updated=datetime.now().isoformat(),
            size_bytes=102400
        )
    
    async def hybrid_search(
        self,
        query: str,
        collections: Optional[list[str]] = None,
        limit: int = 10,
        min_score: float = 0.0
    ) -> list[SearchResult]:
        """Mock hybrid search."""
        logger.info(f"Hybrid search: query='{query}', limit={limit}")
        results = []
        query_lower = query.lower()
        
        for doc in list(self._documents.values())[:limit]:
            score = 0.5
            if query_lower in doc.content.lower():
                score = 0.9
            if score >= min_score:
                results.append(SearchResult(
                    doc_id=doc.doc_id,
                    path=doc.path,
                    title=doc.title,
                    content=doc.content[:200] + "..." if len(doc.content) > 200 else doc.content,
                    score=score,
                    highlights=[f"Match found in {doc.title}"]
                ))
        
        return sorted(results, key=lambda x: x.score, reverse=True)[:limit]
    
    async def lex_search(
        self,
        query: str,
        collections: Optional[list[str]] = None,
        limit: int = 10
    ) -> list[SearchResult]:
        """Mock BM25 search."""
        logger.info(f"BM25 search: query='{query}', limit={limit}")
        results = []
        query_lower = query.lower()
        
        for doc in list(self._documents.values())[:limit]:
            score = 0.3
            if query_lower in doc.content.lower():
                score = 0.8
            results.append(SearchResult(
                doc_id=doc.doc_id,
                path=doc.path,
                title=doc.title,
                content=doc.content[:200] + "..." if len(doc.content) > 200 else doc.content,
                score=score,
                highlights=[f"BM25 match in {doc.title}"]
            ))
        
        return sorted(results, key=lambda x: x.score, reverse=True)[:limit]
    
    async def vec_search(
        self,
        query: str,
        collections: Optional[list[str]] = None,
        limit: int = 10
    ) -> list[SearchResult]:
        """Mock vector search."""
        logger.info(f"Vector search: query='{query}', limit={limit}")
        results = []
        
        for doc in list(self._documents.values())[:limit]:
            results.append(SearchResult(
                doc_id=doc.doc_id,
                path=doc.path,
                title=doc.title,
                content=doc.content[:200] + "..." if len(doc.content) > 200 else doc.content,
                score=0.7,  # Mock semantic similarity
                highlights=[f"Semantic match in {doc.title}"]
            ))
        
        return sorted(results, key=lambda x: x.score, reverse=True)[:limit]
    
    async def get_document(
        self,
        path_or_docid: str,
        from_line: Optional[int] = None,
        max_lines: Optional[int] = None
    ) -> Optional[Document]:
        """Get a document by path or doc_id."""
        logger.info(f"Get document: path_or_docid='{path_or_docid}'")
        doc = self._documents.get(path_or_docid)
        
        if doc and (from_line is not None or max_lines is not None):
            # Simulate line-based extraction
            lines = doc.content.split('\n')
            start = from_line or 0
            end = start + max_lines if max_lines else len(lines)
            content = '\n'.join(lines[start:end])
            return Document(
                doc_id=doc.doc_id,
                path=doc.path,
                title=doc.title,
                content=content,
                metadata=doc.metadata,
                line_start=start,
                line_end=end
            )
        
        return doc
    
    async def get_documents_by_pattern(
        self,
        pattern: str,
        max_bytes: Optional[int] = None
    ) -> tuple[list[Document], list[str]]:
        """Get documents matching a pattern."""
        logger.info(f"Multi-get: pattern='{pattern}', max_bytes={max_bytes}")
        documents = []
        errors = []
        total_bytes = 0
        
        for doc_id, doc in self._documents.items():
            if fnmatch.fnmatch(doc.path, pattern) or fnmatch.fnmatch(doc.doc_id, pattern):
                doc_bytes = len(doc.content.encode('utf-8'))
                
                if max_bytes and total_bytes + doc_bytes > max_bytes:
                    errors.append(f"Max bytes limit reached, skipping {doc.path}")
                    continue
                
                documents.append(doc)
                total_bytes += doc_bytes
        
        return documents, errors
    
    async def get_status(self) -> tuple[list[CollectionInfo], int]:
        """Get index status."""
        logger.info("Get status")
        total_docs = len(set(d.doc_id for d in self._documents.values()))
        return list(self._collections.values()), total_docs


# ============================================================================
# Tool Registry
# ============================================================================

class ToolRegistry:
    """Registry for MCP tools."""
    
    def __init__(self, backend: Optional[SearchBackend] = None):
        self.backend = backend or MockSearchBackend()
        self._tools: dict[str, MCPTool] = {}
        self._handlers: dict[str, callable] = {}
        self._register_tools()
    
    def _register_tools(self):
        """Register all MCP tools."""
        # query - Hybrid search
        self._tools["query"] = MCPTool(
            name="query",
            description="Hybrid search combining full-text search (BM25), vector semantic search, and reranking for the most relevant results.",
            inputSchema=ToolInputSchema(
                type="object",
                properties={
                    "query": {
                        "type": "string",
                        "description": "The search query string"
                    },
                    "collections": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of collection names to search"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10)",
                        "default": 10
                    },
                    "min_score": {
                        "type": "number",
                        "description": "Minimum relevance score threshold (default: 0.0)",
                        "default": 0.0
                    }
                },
                required=["query"]
            )
        )
        self._handlers["query"] = self._handle_query
        
        # lex_search - BM25 search
        self._tools["lex_search"] = MCPTool(
            name="lex_search",
            description="BM25 full-text search for keyword-based document retrieval.",
            inputSchema=ToolInputSchema(
                type="object",
                properties={
                    "query": {
                        "type": "string",
                        "description": "The search query string"
                    },
                    "collections": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of collection names to search"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10)",
                        "default": 10
                    }
                },
                required=["query"]
            )
        )
        self._handlers["lex_search"] = self._handle_lex_search
        
        # vec_search - Vector search
        self._tools["vec_search"] = MCPTool(
            name="vec_search",
            description="Vector semantic search for finding documents with similar meaning.",
            inputSchema=ToolInputSchema(
                type="object",
                properties={
                    "query": {
                        "type": "string",
                        "description": "The search query string"
                    },
                    "collections": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of collection names to search"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10)",
                        "default": 10
                    }
                },
                required=["query"]
            )
        )
        self._handlers["vec_search"] = self._handle_vec_search
        
        # get - Get document
        self._tools["get"] = MCPTool(
            name="get",
            description="Get a document by its path or document ID, with optional line range.",
            inputSchema=ToolInputSchema(
                type="object",
                properties={
                    "path_or_docid": {
                        "type": "string",
                        "description": "Document path or document ID"
                    },
                    "from_line": {
                        "type": "integer",
                        "description": "Optional starting line number (0-indexed)"
                    },
                    "max_lines": {
                        "type": "integer",
                        "description": "Optional maximum number of lines to return"
                    }
                },
                required=["path_or_docid"]
            )
        )
        self._handlers["get"] = self._handle_get
        
        # multi_get - Batch get documents
        self._tools["multi_get"] = MCPTool(
            name="multi_get",
            description="Batch get documents matching a glob pattern.",
            inputSchema=ToolInputSchema(
                type="object",
                properties={
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern to match document paths or IDs (e.g., '/docs/*.md', 'doc_*')"
                    },
                    "max_bytes": {
                        "type": "integer",
                        "description": "Optional maximum total bytes to return"
                    }
                },
                required=["pattern"]
            )
        )
        self._handlers["multi_get"] = self._handle_multi_get
        
        # status - Get index status
        self._tools["status"] = MCPTool(
            name="status",
            description="Get the current status of all document collections.",
            inputSchema=ToolInputSchema(
                type="object",
                properties={},
                required=[]
            )
        )
        self._handlers["status"] = self._handle_status
    
    def list_tools(self) -> list[MCPTool]:
        """List all registered tools."""
        return list(self._tools.values())
    
    def get_tool(self, name: str) -> Optional[MCPTool]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool by name with arguments."""
        handler = self._handlers.get(name)
        if not handler:
            raise ValueError(f"Unknown tool: {name}")
        
        return await handler(arguments)
    
    # -------------------------------------------------------------------------
    # Tool Handlers
    # -------------------------------------------------------------------------
    
    async def _handle_query(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle query tool."""
        input_data = QueryInput(**arguments)
        results = await self.backend.hybrid_search(
            query=input_data.query,
            collections=input_data.collections,
            limit=input_data.limit,
            min_score=input_data.min_score
        )
        return QueryOutput(results=results).model_dump()
    
    async def _handle_lex_search(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle lex_search tool."""
        input_data = LexSearchInput(**arguments)
        results = await self.backend.lex_search(
            query=input_data.query,
            collections=input_data.collections,
            limit=input_data.limit
        )
        return LexSearchOutput(results=results).model_dump()
    
    async def _handle_vec_search(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle vec_search tool."""
        input_data = VecSearchInput(**arguments)
        results = await self.backend.vec_search(
            query=input_data.query,
            collections=input_data.collections,
            limit=input_data.limit
        )
        return VecSearchOutput(results=results).model_dump()
    
    async def _handle_get(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle get tool."""
        input_data = GetInput(**arguments)
        document = await self.backend.get_document(
            path_or_docid=input_data.path_or_docid,
            from_line=input_data.from_line,
            max_lines=input_data.max_lines
        )
        return GetOutput(document=document).model_dump()
    
    async def _handle_multi_get(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle multi_get tool."""
        input_data = MultiGetInput(**arguments)
        documents, errors = await self.backend.get_documents_by_pattern(
            pattern=input_data.pattern,
            max_bytes=input_data.max_bytes
        )
        return MultiGetOutput(documents=documents, errors=errors).model_dump()
    
    async def _handle_status(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle status tool."""
        collections, total = await self.backend.get_status()
        return StatusOutput(collections=collections, total_documents=total).model_dump()


# ============================================================================
# Global Tool Registry Instance
# ============================================================================

_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry(backend: Optional[SearchBackend] = None) -> ToolRegistry:
    """Get or create the global tool registry."""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry(backend)
    return _tool_registry


def set_tool_registry(registry: ToolRegistry):
    """Set the global tool registry."""
    global _tool_registry
    _tool_registry = registry
