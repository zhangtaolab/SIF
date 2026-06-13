# MCP Server

SIF includes a Model Context Protocol (MCP) server for integration with AI assistants and other MCP-compatible tools.

## Overview

The Model Context Protocol (MCP) is an open protocol that enables seamless integration between AI systems and external data sources. SIF's MCP server allows AI assistants to:

- Search your document collections
- Retrieve specific documents
- Get indexing status

## Architecture

```
+-----------------+      +------------------+      +--------------+
|   AI Assistant  |<---->|   MCP Server     |<---->|   SIF Index  |
|  (Claude, etc.) |      |  (stdio/http)    |      |   (SQLite)   |
+-----------------+      +------------------+      +--------------+
```

The MCP implementation lives in `src/sif/mcp/` and provides:

- `MCPServer` — JSON-RPC request handler and tool registry
- `SearchBackend` — async wrapper around SIF search/retrieval
- `ToolHandler` — pluggable tool handlers
- `StdioTransport` — stdio transport for Claude Desktop
- `HTTPTransport` — FastAPI-based HTTP transport with SSE

## Transport Types

### stdio Transport

Uses standard input/output for communication. Ideal for Claude Desktop.

```bash
sif mcp stdio
```

**Use cases:**
- Claude Desktop
- Local AI assistants
- Command-line integrations

### HTTP Transport

Uses HTTP for communication. Supports Streamable HTTP with a single `/mcp` endpoint.

```bash
sif mcp http --host 127.0.0.1 --port 8080
```

**Use cases:**
- Remote AI services
- Web-based assistants
- Distributed systems

**HTTP Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/mcp` | POST | JSON-RPC message endpoint |
| `/mcp` | GET | Server-Sent Events (SSE) stream |

## Available Tools

### query

Hybrid search combining BM25 full-text search, vector semantic search, and reranking.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Search query |
| `collections` | array | No | Collection names to search |
| `limit` | integer | No | Maximum results (default: 10) |
| `min_score` | number | No | Minimum score threshold (default: 0.0) |

**Example:**
```json
{
  "name": "query",
  "arguments": {
    "query": "python decorators",
    "collections": ["my-notes"],
    "limit": 5
  }
}
```

**Response:**
```json
{
  "results": [
    {
      "doc_id": "doc_abc123",
      "path": "/notes/python/decorators.md",
      "title": "Python Decorators",
      "score": 0.89,
      "content": "Full document content...",
      "highlights": ["decorators are a powerful"],
      "metadata": {}
    }
  ]
}
```

### get

Retrieve a specific document by path or document ID.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path_or_docid` | string | Yes | Document path or ID |
| `from_line` | integer | No | Start line (1-based) |
| `max_lines` | integer | No | Maximum lines to return |

**Example:**
```json
{
  "name": "get",
  "arguments": {
    "path_or_docid": "/notes/python/decorators.md",
    "max_lines": 50
  }
}
```

### multi_get

Batch retrieve documents matching a glob pattern.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `pattern` | string | Yes | Glob pattern (e.g. `/notes/*.md`) |
| `max_bytes` | integer | No | Maximum total bytes to return |

**Example:**
```json
{
  "name": "multi_get",
  "arguments": {
    "pattern": "/notes/*.md"
  }
}
```

### status

Get indexing status for all collections.

**Parameters:** None

**Example:**
```json
{
  "name": "status",
  "arguments": {}
}
```

**Response:**
```json
{
  "collections": [
    {
      "name": "my-notes",
      "document_count": 42,
      "last_updated": "2024-01-20T14:22:00Z"
    }
  ],
  "total_documents": 42
}
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SIF_DB_PATH` | `~/.sif/index.sqlite` | Path to SQLite database |
| `SIF_MCP_HOST` | `127.0.0.1` | HTTP server host |
| `SIF_MCP_PORT` | `8080` | HTTP server port |

### .env File Example

```bash
# MCP Server Configuration
SIF_MCP_HOST=127.0.0.1
SIF_MCP_PORT=8080

# Database
SIF_DB_PATH=~/.sif/index.sqlite

# Model
SIF_MODEL_NAME=Qwen/Qwen3-Embedding-0.6B
```

## Integration Examples

### Claude Desktop

Add to Claude Desktop configuration:

```json
{
  "mcpServers": {
    "sif": {
      "command": "sif",
      "args": ["mcp", "stdio"],
      "env": {
        "SIF_DB_PATH": "/Users/forrest/.sif/index.sqlite"
      }
    }
  }
}
```

Location:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

### HTTP Client

```python
import requests

# Start server: sif mcp http --host 127.0.0.1 --port 8080

# 1. initialize
response = requests.post(
    "http://127.0.0.1:8080/mcp",
    json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2024-11-05"}
    }
)

# 2. tools/list
response = requests.post(
    "http://127.0.0.1:8080/mcp",
    json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
)

# 3. tools/call
response = requests.post(
    "http://127.0.0.1:8080/mcp",
    json={
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "query",
            "arguments": {
                "query": "python decorators",
                "limit": 5
            }
        }
    }
)

print(response.json())
```

### Custom Tool Handler

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

    async def handle(
        self,
        params: dict[str, Any],
        backend: SearchBackend,
    ) -> ToolsCallResult:
        return ToolsCallResult(
            content=[ToolContentItem(type="text", text='{"status":"ok"}')],
        )


backend = SearchBackend("/Users/forrest/.sif/index.sqlite")
server = MCPServer(backend)
server.register_tools(create_default_tools() + [PingToolHandler()])
```

## Security Considerations

### Local-First Design

- All data stays on your machine
- No data sent to external services by default
- AI assistant only accesses indexed documents

### Network Security (HTTP Transport)

- Default binds to localhost only
- CORS defaults to `http://localhost:3000` and `http://127.0.0.1:3000`
- Use firewall rules for remote access
- Consider authentication for production use

```bash
# Bind to localhost only (default)
sif mcp http --host 127.0.0.1

# Bind to all interfaces (use with caution)
sif mcp http --host 0.0.0.0
```

## Troubleshooting

### Server Won't Start

```bash
# Check if port is in use
lsof -i :8080

# Use different port
sif mcp http --port 8081
```

### Connection Issues

```bash
# Test stdio transport
sif mcp stdio

# Test HTTP transport
sif mcp http
curl http://127.0.0.1:8080/health
```

### Tool Not Found

```bash
# List available MCP commands
sif mcp --help
```

## Best Practices

1. **Use stdio for local AI assistants** — More secure, no network exposure
2. **Use HTTP for distributed systems** — Better for remote access
3. **Monitor logs** — Check for errors and performance issues
4. **Regular indexing** — Keep index up to date for accurate results
