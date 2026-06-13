# SIF MCP Server

Model Context Protocol (MCP) server implementation for SIF.

## Features

- **Dual Transport Support**: stdio (for Claude Desktop) and HTTP (for web clients)
- **Four Search Tools**:
  - `query` - Hybrid search (BM25 + Vector + Reranking)
  - `get` - Get document by path or doc_id
  - `multi_get` - Batch get documents by glob pattern
  - `status` - Get index status
- **JSON-RPC 2.0 Protocol**: Compliant with MCP specification
- **Streamable HTTP**: Session-aware `/mcp` endpoint with POST/GET support

## Installation

Install SIF with the MCP extra:

```bash
pip install -e ".[mcp]"
```

## Usage

### CLI (recommended)

```bash
# stdio mode (Claude Desktop)
sif mcp stdio

# HTTP mode
sif mcp http --host 127.0.0.1 --port 8080
```

### Programmatic

```python
from sif.mcp.cli import run_stdio_server, run_http_server

DB_PATH = "/Users/forrest/.sif/index.sqlite"

# stdio
run_stdio_server(DB_PATH)

# HTTP
run_http_server(DB_PATH, host="127.0.0.1", port=8080)
```

To assemble the server manually:

```python
from sif.mcp.backend import SearchBackend
from sif.mcp.handlers import create_default_tools
from sif.mcp.server import MCPServer
from sif.mcp.transports.http import HTTPTransport

backend = SearchBackend("/Users/forrest/.sif/index.sqlite")
server = MCPServer(backend)
server.register_tools(create_default_tools())

transport = HTTPTransport(server, host="127.0.0.1", port=8080)
transport.run()
```

## API Endpoints (HTTP Mode)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/mcp` | POST | JSON-RPC message endpoint |
| `/mcp` | GET | Server-Sent Events (SSE) stream |

## Tools

### query

Hybrid search combining full-text search (BM25), vector semantic search, and reranking.

**Input:**
```json
{
  "query": "search terms",
  "collections": ["default"],
  "limit": 10,
  "min_score": 0.0
}
```

**Output:**
```json
{
  "results": [
    {
      "doc_id": "doc_1",
      "path": "/docs/file.md",
      "title": "Document Title",
      "content": "...",
      "score": 0.95,
      "highlights": ["..."],
      "metadata": {}
    }
  ]
}
```

### get

Get a document by its path or document ID, with optional line range.

**Input:**
```json
{
  "path_or_docid": "/docs/file.md",
  "from_line": 0,
  "max_lines": 100
}
```

### multi_get

Batch get documents matching a glob pattern.

**Input:**
```json
{
  "pattern": "/docs/*.md",
  "max_bytes": 1048576
}
```

### status

Get the current status of all document collections.

**Input:** `{}`

**Output:**
```json
{
  "collections": [
    {
      "name": "default",
      "document_count": 100,
      "last_updated": "2024-01-01T00:00:00"
    }
  ],
  "total_documents": 100
}
```

## Protocol Flow

1. **initialize**: Client sends `initialize` request
2. Server responds with capabilities
3. **notifications/initialized**: Client sends initialized notification
4. **tools/list**: Client requests available tools
5. **tools/call**: Client calls tools as needed

## Example JSON-RPC Messages

### Initialize Request
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {
      "name": "claude-desktop",
      "version": "1.0.0"
    }
  }
}
```

### Tools/List Request
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list",
  "params": {}
}
```

### Tools/Call Request
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "query",
    "arguments": {
      "query": "machine learning",
      "limit": 5
    }
  }
}
```

## Custom Tool Handler

```python
from typing import Any, ClassVar

from sif.mcp.backend import SearchBackend
from sif.mcp.handlers import ToolHandler, create_default_tools
from sif.mcp.protocol import ToolContentItem, ToolsCallResult
from sif.mcp.server import MCPServer


class PingToolHandler(ToolHandler):
    name: ClassVar[str] = "ping"
    description: ClassVar[str] = "Return server status."
    input_schema: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    async def handle(self, params: dict[str, Any], backend: SearchBackend) -> ToolsCallResult:
        return ToolsCallResult(
            content=[ToolContentItem(type="text", text='{"status":"ok"}')],
        )


backend = SearchBackend("/Users/forrest/.sif/index.sqlite")
server = MCPServer(backend)
server.register_tools(create_default_tools() + [PingToolHandler()])
```

## License

MIT
