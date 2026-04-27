"""MCP server implementation."""

from __future__ import annotations

import json
import sys
from typing import Any

from sif.database.connection import DatabaseConnection
from sif.search.bm25 import BM25Searcher
from sif.search.hybrid import HybridSearcher
from sif.utils.logging import get_logger


logger = get_logger(__name__)


class MCPServer:
    """Model Context Protocol server."""

    def __init__(self, index_path: str) -> None:
        self.index_path = index_path

    def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle an MCP request."""
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")

        try:
            if method == "initialize":
                return self._handle_initialize(request_id)
            if method == "tools/list":
                return self._handle_tools_list(request_id)
            if method == "tools/call":
                return self._handle_tools_call(request_id, params)
            if method == "resources/list":
                return self._handle_resources_list(request_id)
            if method == "resources/read":
                return self._handle_resources_read(request_id, params)
            return self._error_response(request_id, -32601, f"Method not found: {method}")
        except Exception as e:
            logger.exception("Error handling request")
            return self._error_response(request_id, -32603, str(e))

    def _handle_initialize(self, request_id: Any) -> dict[str, Any]:
        """Handle initialize request."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {},
                },
                "serverInfo": {
                    "name": "sif-mcp",
                    "version": "0.1.0",
                },
            },
        }

    def _handle_tools_list(self, request_id: Any) -> dict[str, Any]:
        """Handle tools/list request."""
        tools = [
            {
                "name": "query",
                "description": "Search documents using hybrid search (BM25 + Vector + RRF)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "collections": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Collection names to search",
                        },
                        "limit": {"type": "integer", "description": "Maximum number of results"},
                        "min_score": {"type": "number", "description": "Minimum score threshold"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "lex_search",
                "description": "Search documents using BM25 full-text search",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "collections": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Collection names to search",
                        },
                        "limit": {"type": "integer", "description": "Maximum number of results"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "vec_search",
                "description": "Search documents using vector similarity",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "collections": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Collection names to search",
                        },
                        "limit": {"type": "integer", "description": "Maximum number of results"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "get",
                "description": "Get a document by path or ID",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path_or_docid": {"type": "string", "description": "Document path or ID"},
                        "from_line": {"type": "integer", "description": "Start from line number"},
                        "max_lines": {"type": "integer", "description": "Maximum number of lines"},
                    },
                    "required": ["path_or_docid"],
                },
            },
            {
                "name": "multi_get",
                "description": "Get multiple documents matching a pattern",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "File pattern to match"},
                        "max_bytes": {"type": "integer", "description": "Maximum bytes per file"},
                    },
                    "required": ["pattern"],
                },
            },
            {
                "name": "status",
                "description": "Get index status",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": tools},
        }

    def _handle_tools_call(self, request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name == "query":
            return self._tool_query(request_id, arguments)
        if tool_name == "lex_search":
            return self._tool_lex_search(request_id, arguments)
        if tool_name == "vec_search":
            return self._tool_vec_search(request_id, arguments)
        if tool_name == "get":
            return self._tool_get(request_id, arguments)
        if tool_name == "multi_get":
            return self._tool_multi_get(request_id, arguments)
        if tool_name == "status":
            return self._tool_status(request_id)
        return self._error_response(request_id, -32602, f"Unknown tool: {tool_name}")

    def _tool_query(self, request_id: Any, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute query tool."""
        query = arguments.get("query", "")
        collections = arguments.get("collections", [])
        limit = arguments.get("limit", 10)
        min_score = arguments.get("min_score", 0.0)

        from sif.core.models import SearchOptions  # noqa: PLC0415
        from sif.database.repositories import CollectionRepository  # noqa: PLC0415
        from sif.database.schema import SchemaManager  # noqa: PLC0415

        with DatabaseConnection(self.index_path).transaction() as conn:
            SchemaManager(conn).create_all()
            options = SearchOptions(limit=limit, min_score=min_score)

            if collections:
                coll_repo = CollectionRepository(conn)
                options.collection_ids = []
                for name in collections:
                    coll = coll_repo.get_by_name(name)
                    if coll:
                        options.collection_ids.append(coll.id)

            searcher = HybridSearcher(conn)
            results = searcher.search(query, options)

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps([r.to_dict() for r in results], indent=2),
                    }
                ],
            },
        }

    def _tool_lex_search(self, request_id: Any, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute lex_search tool."""
        query = arguments.get("query", "")
        collections = arguments.get("collections", [])
        limit = arguments.get("limit", 10)

        from sif.core.models import SearchOptions  # noqa: PLC0415
        from sif.database.repositories import CollectionRepository  # noqa: PLC0415
        from sif.database.schema import SchemaManager  # noqa: PLC0415

        with DatabaseConnection(self.index_path).transaction() as conn:
            SchemaManager(conn).create_all()
            options = SearchOptions(limit=limit)

            if collections:
                coll_repo = CollectionRepository(conn)
                options.collection_ids = []
                for name in collections:
                    coll = coll_repo.get_by_name(name)
                    if coll:
                        options.collection_ids.append(coll.id)

            searcher = BM25Searcher(conn)
            results = searcher.search(query, options)

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps([r.to_dict() for r in results], indent=2),
                    }
                ],
            },
        }

    def _tool_vec_search(self, request_id: Any, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute vec_search tool."""
        # For now, fall back to BM25
        return self._tool_lex_search(request_id, arguments)

    def _tool_get(self, request_id: Any, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute get tool."""
        path_or_docid = arguments.get("path_or_docid", "")
        from_line = arguments.get("from_line", 1)
        max_lines = arguments.get("max_lines")

        from sif.database.repositories import (  # noqa: PLC0415
            CollectionRepository,
            DocumentRepository,
        )
        from sif.database.schema import SchemaManager  # noqa: PLC0415

        with DatabaseConnection(self.index_path).transaction() as conn:
            SchemaManager(conn).create_all()
            doc_repo = DocumentRepository(conn)
            doc = doc_repo.get_by_id(path_or_docid)

            if not doc:
                # Try by path
                coll_repo = CollectionRepository(conn)
                for coll in coll_repo.list_all():
                    doc = doc_repo.get_by_path(path_or_docid, coll.id)
                    if doc:
                        break

        if not doc:
            return self._error_response(request_id, -32602, f"Document not found: {path_or_docid}")

        # Get content with line filtering
        content = doc.content
        lines = content.split("\n")
        start = from_line - 1
        end = len(lines) if max_lines is None else start + max_lines
        filtered_content = "\n".join(lines[start:end])

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": filtered_content,
                    }
                ],
            },
        }

    def _tool_multi_get(self, request_id: Any, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute multi_get tool."""
        pattern = arguments.get("pattern", "")
        max_bytes = arguments.get("max_bytes", 100000)

        import fnmatch  # noqa: PLC0415

        from sif.database.repositories import (  # noqa: PLC0415
            CollectionRepository,
            DocumentRepository,
        )
        from sif.database.schema import SchemaManager  # noqa: PLC0415

        documents = []
        errors = []

        with DatabaseConnection(self.index_path).transaction() as conn:
            SchemaManager(conn).create_all()
            coll_repo = CollectionRepository(conn)
            doc_repo = DocumentRepository(conn)

            for coll in coll_repo.list_all():
                for doc in doc_repo.list_by_collection(coll.id):
                    if fnmatch.fnmatch(doc.path, pattern) or fnmatch.fnmatch(doc.filename, pattern):
                        content = doc.content
                        if len(content.encode()) > max_bytes:
                            content = content[:max_bytes] + "\n... [truncated]"

                        documents.append(
                            {
                                "path": doc.path,
                                "title": doc.title,
                                "content": content,
                            }
                        )

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "documents": documents,
                                "errors": errors,
                            },
                            indent=2,
                        ),
                    }
                ],
            },
        }

    def _tool_status(self, request_id: Any) -> dict[str, Any]:
        """Execute status tool."""
        from sif.database.schema import SchemaManager  # noqa: PLC0415

        with DatabaseConnection(self.index_path).transaction() as conn:
            SchemaManager(conn).create_all()
            stats = SchemaManager(conn).get_stats()

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(stats, indent=2),
                    }
                ],
            },
        }

    def _handle_resources_list(self, request_id: Any) -> dict[str, Any]:
        """Handle resources/list request."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"resources": []},
        }

    def _handle_resources_read(self, request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Handle resources/read request."""
        return self._error_response(request_id, -32602, "Resources not implemented")

    def _error_response(self, request_id: Any, code: int, message: str) -> dict[str, Any]:
        """Create an error response."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message,
            },
        }


def run_stdio_server(index_path: str) -> None:
    """Run MCP server in stdio mode."""
    server = MCPServer(index_path)

    logger.info("MCP server started in stdio mode")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
            response = server.handle_request(request)
            print(json.dumps(response), flush=True)
        except json.JSONDecodeError as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {e}",
                },
            }
            print(json.dumps(error_response), flush=True)
