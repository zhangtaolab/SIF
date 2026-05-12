# Phase 9: MCP Server Implementation - Pattern Map

**Mapped:** 2026-05-12
**Files analyzed:** 15
**Analogs found:** 14 / 15

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/sif/mcp/__init__.py` | config | pub-sub | `src/sif/mcp_server/__init__.py` | partial |
| `src/sif/mcp/protocol.py` | model | request-response | `src/sif/mcp/protocol.py` (existing) | exact (keep) |
| `src/sif/mcp/server.py` | controller | request-response | `src/sif/mcp/server.py` (existing) | exact (rewrite async) |
| `src/sif/mcp/backend.py` | service | CRUD | `src/sif/mcp/tools.py` (MockSearchBackend) | role-match |
| `src/sif/mcp/handlers.py` | component | request-response | `src/sif/mcp_server/handlers.py` | exact |
| `src/sif/mcp/transports/__init__.py` | config | pub-sub | `src/sif/mcp_server/__init__.py` | partial |
| `src/sif/mcp/transports/stdio.py` | transport | streaming | `src/sif/mcp/transport_stdio.py` | exact |
| `src/sif/mcp/transports/http.py` | transport | request-response | `src/sif/mcp/transport_http.py` | exact |
| `src/sif/mcp/cli.py` | controller | request-response | `src/sif/cli/commands/mcp.py` | exact |
| `src/sif/cli/commands/mcp.py` | controller | request-response | `src/sif/cli/commands/search.py` | role-match |
| `tests/unit/mcp/__init__.py` | config | — | `tests/unit/search/__init__.py` | partial |
| `tests/unit/mcp/test_server.py` | test | request-response | `tests/unit/search/test_hybrid.py` | role-match |
| `tests/unit/mcp/test_backend.py` | test | CRUD | `tests/unit/cli/test_search.py` | role-match |
| `tests/unit/mcp/test_handlers.py` | test | request-response | `tests/unit/search/test_hybrid.py` | role-match |
| `tests/unit/mcp/test_transports_stdio.py` | test | streaming | `tests/unit/cli/test_search.py` | partial |
| `tests/unit/mcp/test_transports_http.py` | test | request-response | `tests/unit/cli/test_search.py` | partial |
| `tests/unit/mcp/test_integration.py` | test | request-response | `tests/integration/test_search_pipeline.py` | role-match |

## Pattern Assignments

### `src/sif/mcp/server.py` (controller, request-response)

**Analog:** `src/sif/mcp/server.py` (existing sync server to be rewritten as async)

**Imports pattern** (lines 1-15):
```python
from __future__ import annotations

import json
import sys
from typing import Any

from sif.database.connection import DatabaseConnection
from sif.search.bm25 import BM25Searcher
from sif.search.hybrid import HybridSearcher
from sif.utils.logging import get_logger


logger = get_logger(__name__)
```

**Core pattern - sync request dispatch** (lines 24-44):
```python
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
```

**Error response pattern** (lines 397-406):
```python
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
```

**What to change for new async server:**
- Convert `handle_request` to `async def`
- Add state machine (`CREATED` -> `INITIALIZED` -> `SHUTDOWN`)
- Reject requests before initialization with `MCPErrorCode.SERVER_NOT_INITIALIZED`
- Use Pydantic models (`JsonRpcRequest`, `JsonRpcResponse`) instead of raw dicts
- Register `ToolHandler` instances instead of inline method dispatch
- Handle `notifications/initialized`, `notifications/cancelled`

---

### `src/sif/mcp/backend.py` (service, CRUD)

**Analog:** `src/sif/mcp/tools.py` (MockSearchBackend) + `src/sif/mcp/server.py` (real DB access)

**Imports pattern** (from `src/sif/mcp/tools.py`, lines 1-35):
```python
"""MCP Tool Implementations"""

import fnmatch
import logging
from datetime import datetime
from typing import Any, Optional, Protocol

from .protocol import (
    CollectionInfo,
    Document,
    GetInput,
    GetOutput,
    # ... etc
)


logger = logging.getLogger(__name__)
```

**SearchBackend Protocol** (from `src/sif/mcp/tools.py`, lines 46-85):
```python
class SearchBackend(Protocol):
    """Protocol for search backend implementations."""

    async def hybrid_search(
        self,
        query: str,
        collections: Optional[list[str]] = None,
        limit: int = 10,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        """Perform hybrid search (FTS + Vector + Reranking)."""
        ...

    async def get_document(
        self, path_or_docid: str, from_line: Optional[int] = None, max_lines: Optional[int] = None
    ) -> Optional[Document]:
        """Get a document by path or doc_id."""
        ...

    async def get_documents_by_pattern(
        self, pattern: str, max_bytes: Optional[int] = None
    ) -> tuple[list[Document], list[str]]:
        """Get documents matching a pattern."""
        ...

    async def get_status(self) -> tuple[list[CollectionInfo], int]:
        """Get index status."""
        ...
```

**Real DB access pattern** (from `src/sif/mcp/server.py`, lines 179-216):
```python
def _tool_query(self, request_id: Any, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute query tool."""
    query = arguments.get("query", "")
    collections = arguments.get("collections", [])
    limit = arguments.get("limit", 10)
    min_score = arguments.get("min_score", 0.0)

    from sif.core.models import SearchOptions
    from sif.database.repositories import CollectionRepository
    from sif.database.schema import SchemaManager

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
```

**Async wrapping pattern** (from RESEARCH.md, verified via runtime test):
```python
class SearchBackend:
    def __init__(self, db_path: str, settings: Settings | None = None) -> None:
        self.db_path = db_path
        self.settings = settings or get_settings()

    async def _with_db(self, callback: Callable) -> Any:
        def _run():
            db = Database(self.db_path)
            db.init_schema()
            try:
                return callback(db)
            finally:
                db.close()
        return await asyncio.to_thread(_run)

    async def hybrid_search(self, query: str, collections: list[str] | None = None,
                            limit: int = 10, min_score: float = 0.0) -> list[CoreSearchResult]:
        def _search(db):
            with db.transaction() as conn:
                options = SearchOptions(limit=limit, min_score=min_score,
                                        include_content=False, include_highlights=True)
                if collections:
                    repo = CollectionRepository(conn)
                    options.collection_ids = [
                        c.id for c in (repo.get_by_name(n) for n in collections) if c
                    ]
                pipeline = SearchPipeline(conn, embedder=None,
                                          embedding_dim=self.settings.embedding_dim)
                return pipeline.search(query, options)
        return await self._with_db(_search)
```

---

### `src/sif/mcp/handlers.py` (component, request-response)

**Analog:** `src/sif/mcp_server/handlers.py`

**Imports pattern** (lines 1-9):
```python
"""MCP request handlers."""

from abc import ABC, abstractmethod
from typing import Any

from sif.utils.logging import get_logger


logger = get_logger(__name__)
```

**ToolHandler ABC** (lines 12-43):
```python
class ToolHandler(ABC):
    """Abstract base class for MCP tool handlers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description."""
        ...

    @property
    @abstractmethod
    def input_schema(self) -> dict[str, Any]:
        """JSON schema for tool input."""
        ...

    @abstractmethod
    def handle(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle a tool call.

        Args:
            params: Tool parameters

        Returns:
            Tool result
        """
        ...
```

**What to change for new handlers:**
- Convert `handle` to `async def handle(self, params: dict[str, Any], backend: SearchBackend) -> ToolsCallResult`
- Return `ToolsCallResult` (from protocol.py) instead of raw dict
- Each concrete handler validates params via Pydantic (`QueryInput`, `GetInput`, etc.)
- Maps `CoreSearchResult` -> protocol `SearchResult` before returning

**Concrete handler pattern** (from `src/sif/mcp/tools.py`, lines 428-437):
```python
async def _handle_query(self, arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle query tool."""
    input_data = QueryInput(**arguments)
    results = await self.backend.hybrid_search(
        query=input_data.query,
        collections=input_data.collections,
        limit=input_data.limit,
        min_score=input_data.min_score,
    )
    return QueryOutput(results=results).model_dump()
```

---

### `src/sif/mcp/transports/stdio.py` (transport, streaming)

**Analog:** `src/sif/mcp/transport_stdio.py`

**Imports pattern** (lines 1-20):
```python
"""MCP Stdio Transport"""

import asyncio
import json
import logging
import sys
from contextlib import asynccontextmanager
from typing import Optional, TextIO

from .protocol import JsonRpcNotification, JsonRpcRequest
from .server import MCPServer, ServerConfig, create_server


logger = logging.getLogger(__name__)
```

**Async read pattern** (lines 61-98):
```python
async def _read_message(self) -> Optional[dict]:
    """Read a single JSON-RPC message from stdin."""
    async with self._read_lock:
        loop = asyncio.get_event_loop()
        try:
            line = await loop.run_in_executor(None, self.stdin.readline)
        except Exception as e:
            logger.error(f"Error reading from stdin: {e}")
            return None

        if not line:
            logger.info("EOF reached on stdin")
            return None

        line = line.strip()
        if not line:
            return None

        try:
            message = json.loads(line)
            logger.debug(f"Received: {line[:200]}...")
            return message
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}, line: {line[:100]}")
            return {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {e}"},
            }
```

**Async write pattern** (lines 100-122):
```python
async def _write_message(self, message: dict) -> None:
    """Write a JSON-RPC message to stdout."""
    async with self._write_lock:
        try:
            line = json.dumps(message, ensure_ascii=False)
            logger.debug(f"Sending: {line[:200]}...")
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._write_sync, line)
        except Exception as e:
            logger.error(f"Error writing to stdout: {e}")

def _write_sync(self, line: str) -> None:
    """Synchronous write to stdout."""
    self.stdout.write(line + "\n")
    self.stdout.flush()
```

**Main loop pattern** (lines 173-218):
```python
async def run(self) -> None:
    """Run the stdio transport main loop."""
    logger.info("Starting stdio transport")
    self._running = True

    try:
        while self._running:
            message = await self._read_message()
            if message is None:
                break

            try:
                response = await self._process_message(message)
                if response is not None:
                    await self._write_message(response)
            except Exception as e:
                logger.exception("Error processing message")
                msg_id = message.get("id")
                if msg_id is not None:
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "error": {"code": -32603, "message": f"Internal error: {e!s}"},
                    }
                    await self._write_message(error_response)
    except asyncio.CancelledError:
        logger.info("Transport cancelled")
        raise
    finally:
        self._running = False
        logger.info("Stdio transport stopped")
```

**What to change:**
- Use `UnifiedMCPServer` instead of `MCPServer`
- `_process_message` should call `await self.server.handle_request()` (now async)
- Keep lock-safe I/O, logging to stderr only
- Add cancellation support for in-flight tasks

---

### `src/sif/mcp/transports/http.py` (transport, request-response)

**Analog:** `src/sif/mcp/transport_http.py`

**Imports pattern** (lines 1-35):
```python
"""MCP HTTP Transport"""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from .protocol import (
    JsonRpcNotification,
    JsonRpcRequest,
    MCPErrorCode,
    create_error_response,
)
from .server import MCPServer, ServerConfig, ServerState, create_server


logger = logging.getLogger(__name__)
```

**CORS middleware pattern** (lines 167-174):
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=self.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**SSE streaming pattern** (lines 193-236):
```python
@app.get("/mcp/v1/sse")
async def sse_endpoint(request: Request):
    queue = await self.sse_manager.connect()

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            msg = json.dumps({"message": "Connected to MCP server"})
            yield f"event: connected\ndata: {msg}\n\n"

            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    data = json.dumps(message)
                    yield f"event: message\ndata: {data}\n\n"
                except asyncio.TimeoutError:
                    yield f"event: ping\ndata: {json.dumps({'time': ...})}\n\n"
        except asyncio.CancelledError:
            logger.info("SSE connection cancelled")
        except Exception as e:
            logger.error(f"SSE error: {e}")
        finally:
            await self.sse_manager.disconnect(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

**JSON-RPC POST handler** (lines 238-276):
```python
@app.post("/mcp/v1/messages")
async def messages_endpoint(request: MessageRequest):
    if request.jsonrpc != "2.0":
        return JSONResponse(
            status_code=400,
            content=create_error_response(
                request.id, MCPErrorCode.INVALID_REQUEST, "Invalid JSON-RPC version"
            ).model_dump(),
        )

    if request.method is None:
        return JSONResponse(
            status_code=400,
            content=create_error_response(
                request.id, MCPErrorCode.INVALID_REQUEST, "Missing method field"
            ).model_dump(),
        )

    if request.id is None:
        notification = JsonRpcNotification(
            jsonrpc="2.0", method=request.method, params=request.params
        )
        await self.server.handle_notification(notification)
        return JSONResponse(status_code=202, content={})

    rpc_request = JsonRpcRequest(
        jsonrpc="2.0", id=request.id, method=request.method, params=request.params
    )
    response = await self.server.handle_request(rpc_request)
    return JSONResponse(content=response.model_dump(exclude_none=True))
```

**What to change for Streamable HTTP:**
- Replace `/mcp/v1/messages` and `/mcp/v1/sse` with single `/mcp` endpoint
- POST `/mcp` accepts JSON-RPC, returns either JSON or SSE stream
- GET `/mcp` opens SSE stream for server-initiated messages
- Add `MCP-Session-Id` header support
- Change CORS default from `["*"]` to `["http://localhost:3000", "http://127.0.0.1:3000"]`
- Validate `Origin` header, reject with 403 for unauthorized origins
- Default bind to `127.0.0.1`

---

### `src/sif/mcp/cli.py` (controller, request-response)

**Analog:** `src/sif/cli/commands/mcp.py`

**Imports pattern** (lines 1-13):
```python
"""MCP server commands."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console


console = Console()
```

**Click command group pattern** (lines 15-18):
```python
@click.group("mcp")
def mcp_group() -> None:
    """MCP server commands."""
    pass
```

**Stdio command pattern** (lines 21-38):
```python
@mcp_group.command("stdio")
@click.pass_context
def mcp_stdio_cmd(ctx: click.Context) -> None:
    """Run MCP server in stdio mode."""
    index_path = ctx.obj["index_path"]

    if not Path(index_path).exists():
        console.print(
            "[yellow]Warning: No index found. Some features may not work.[/yellow]", file=sys.stderr
        )

    try:
        from sif.mcp.server import run_stdio_server

        run_stdio_server(str(index_path))
    except ImportError as e:
        console.print(f"[red]MCP server not available: {e}[/red]")
        raise click.ClickException("Install with: pip install sif[mcp]") from None
```

**HTTP command pattern** (lines 41-63):
```python
@mcp_group.command("http")
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind to")
@click.option("--port", "-p", type=int, default=3000, help="Port to listen on")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
@click.pass_context
def mcp_http_cmd(
    ctx: click.Context,
    host: str,
    port: int,
    reload: bool,
) -> None:
    """Run MCP server in HTTP mode."""
    index_path = ctx.obj["index_path"]
    console.print(f"[green]Starting MCP HTTP server on {host}:{port}[/green]")

    try:
        from sif.mcp.server_http import run_http_server

        run_http_server(str(index_path), host=host, port=port, reload=reload)
    except ImportError as e:
        console.print(f"[red]HTTP server not available: {e}[/red]")
        raise click.ClickException("Install with: pip install sif[http]") from None
```

**What to change:**
- Import from new unified package (`sif.mcp.transports.stdio`, `sif.mcp.transports.http`)
- Add `--cors-origins` option to `http` command
- Keep `@click.pass_context` and `ctx.obj["index_path"]` pattern

---

### `tests/unit/mcp/test_server.py` (test, request-response)

**Analog:** `tests/unit/search/test_hybrid.py`

**Test structure pattern** (lines 1-13):
```python
"""Unit tests for hybrid search and search pipeline."""

from unittest.mock import MagicMock, create_autospec

import pytest

from sif.core.models import SearchOptions, SearchResult, SearchType
from sif.search.bm25 import BM25Searcher
from sif.search.hybrid import HybridSearcher, SearchPipeline
from sif.search.vector import VectorSearcher
```

**Mock fixture pattern** (lines 19-30):
```python
@pytest.fixture
def mock_db():
    """Create a mock sqlite3 connection."""
    return MagicMock()


@pytest.fixture
def mock_embedder():
    """Create a mock embedder."""
    embedder = MagicMock()
    embedder.embed.return_value = [0.1] * 384
    embedder.dimension = 384
    return embedder
```

**Test class pattern** (lines 86-99):
```python
class TestHybridSearcher:
    """Test HybridSearcher basic functionality."""

    def test_hybrid_search_with_embedder(
        self,
        mock_db: MagicMock,
        mock_embedder: MagicMock,
    ) -> None:
        """Test that hybrid search uses both BM25 and vector when embedder available."""
        hybrid = HybridSearcher(mock_db, embedder=mock_embedder, embedding_dim=384)
        assert hybrid.embedder is mock_embedder
        assert hybrid.bm25 is not None
        assert hybrid.vector is not None
```

**What to apply for test_server.py:**
- Use `pytest-asyncio` for async tests (`@pytest.mark.asyncio`)
- Mock `SearchBackend` for unit tests
- Test state machine transitions (`CREATED` -> `INITIALIZED`)
- Test `ServerNotInitialized` error for requests before initialize
- Test tool dispatch (`tools/list`, `tools/call`)
- Test notification handling (`notifications/initialized`)

---

### `tests/unit/mcp/test_backend.py` (test, CRUD)

**Analog:** `tests/unit/cli/test_search.py`

**Mock + patch pattern** (lines 31-47):
```python
def test_search_respects_include_by_default(self):
    """search_cmd filters to enabled collections without --all."""
    runner = CliRunner()

    enabled_coll = Collection(
        id="coll1", name="enabled", path="/notes", include_by_default=True
    )

    mock_repo = MagicMock()
    mock_repo.list_enabled.return_value = [enabled_coll]

    mock_searcher = MagicMock()
    mock_searcher.search.return_value = []

    mock_db = MagicMock()

    with (
        patch("sif.cli.commands.search.Database", return_value=mock_db),
        patch(
            "sif.cli.commands.search.CollectionRepository",
            return_value=mock_repo,
        ),
        patch(
            "sif.cli.commands.search.BM25Searcher",
            return_value=mock_searcher,
        ),
    ):
        result = runner.invoke(
            search_cmd,
            ["foo"],
            obj={"index_path": MagicMock(exists=lambda: True)},
        )

    assert result.exit_code == 0
```

**What to apply for test_backend.py:**
- Mock `DatabaseConnection` and `SearchPipeline`
- Mock `EmbeddingManager.from_settings` for embedder
- Test `hybrid_search`, `get_document`, `get_documents_by_pattern`, `get_status`
- Verify `asyncio.to_thread()` wrapping via async test runner
- Test content truncation (100KB limit)

---

### `tests/unit/mcp/test_transports_http.py` (test, request-response)

**Analog:** `tests/unit/cli/test_search.py` (FastAPI TestClient patterns from RESEARCH.md)

**FastAPI TestClient pattern** (from RESEARCH.md):
```python
from fastapi.testclient import TestClient

@pytest.fixture
def client():
    app = create_app(server=mock_server)
    return TestClient(app)

def test_mcp_post(client):
    response = client.post("/mcp", json={
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05"}
    })
    assert response.status_code == 200
    assert response.json()["result"]["protocolVersion"] == "2024-11-05"
```

**What to apply:**
- Test CORS defaults (verify `Access-Control-Allow-Origin` header)
- Test `Origin` validation (403 for invalid origins)
- Test SSE stream from GET `/mcp`
- Test session ID header (`MCP-Session-Id`)

---

## Shared Patterns

### Logging
**Source:** `src/sif/utils/logging.py`
**Apply to:** All MCP files
```python
from sif.utils.logging import get_logger

logger = get_logger(__name__)
```
**Critical for stdio mode:** All logging MUST go to stderr. Never use `print()` in stdio transport.

### Pydantic Model Imports
**Source:** `src/sif/mcp/protocol.py`
**Apply to:** `server.py`, `handlers.py`, `transports/stdio.py`, `transports/http.py`
```python
from .protocol import (
    JsonRpcRequest,
    JsonRpcResponse,
    JsonRpcNotification,
    JsonRpcError,
    MCPErrorCode,
    InitializeResult,
    ServerCapabilities,
    ToolsListResult,
    ToolsCallResult,
    ToolsCallParams,
    ToolContentItem,
    MCPTool,
    create_success_response,
    create_error_response,
    create_notification,
)
```

### Error Response Construction
**Source:** `src/sif/mcp/protocol.py` (lines 319-336)
**Apply to:** `server.py`, `transports/stdio.py`, `transports/http.py`
```python
def create_success_response(id: str | int | None, result: Any) -> JsonRpcResponse:
    """Create a successful JSON-RPC response."""
    return JsonRpcResponse(id=id, result=result)

def create_error_response(
    id: str | int | None,
    code: int,
    message: str,
    data: Any = None,
) -> JsonRpcResponse:
    """Create an error JSON-RPC response."""
    return JsonRpcResponse(id=id, error=JsonRpcError(code=code, message=message, data=data))
```

### Database Connection Pattern
**Source:** `src/sif/database/connection.py` (lines 37-57)
**Apply to:** `backend.py`
```python
@contextmanager
def transaction(self) -> Generator[sqlite3.Connection, None, None]:
    """Execute operations within a transaction."""
    conn = self._create_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

### Settings Access
**Source:** `src/sif/config/settings.py` (lines 211-217)
**Apply to:** `backend.py`, `transports/http.py`
```python
from sif.config.settings import get_settings

settings = get_settings()
db_path = settings.get_db_path()
```

### Async Test Decorator
**Source:** Project uses `pytest-asyncio` (verified in RESEARCH.md)
**Apply to:** All async test files
```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_call()
    assert result == expected
```

### CLI Error Handling
**Source:** `src/sif/cli/commands/mcp.py` (lines 36-38)
**Apply to:** `cli.py`, `src/sif/cli/commands/mcp.py`
```python
try:
    from sif.mcp.server import run_stdio_server
    run_stdio_server(str(index_path))
except ImportError as e:
    console.print(f"[red]MCP server not available: {e}[/red]")
    raise click.ClickException("Install with: pip install sif[mcp]") from None
```

## No Analog Found

Files with no close match in the codebase (planner should use RESEARCH.md patterns instead):

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/sif/mcp/__init__.py` | config | pub-sub | No existing package init with this export pattern |
| `src/sif/mcp/transports/__init__.py` | config | pub-sub | New subpackage, no direct analog |
| `tests/unit/mcp/test_integration.py` | test | request-response | No end-to-end MCP integration tests exist |

## Metadata

**Analog search scope:**
- `src/sif/mcp/` (legacy MCP implementation)
- `src/sif/mcp_server/` (refactored OOP MCP)
- `src/sif/cli/commands/` (CLI command patterns)
- `src/sif/search/` (search strategy patterns)
- `src/sif/database/` (DB connection and repository patterns)
- `src/sif/config/` (settings patterns)
- `src/sif/utils/logging.py` (logging patterns)
- `tests/unit/search/`, `tests/unit/cli/` (test patterns)

**Files scanned:** 18
**Pattern extraction date:** 2026-05-12
