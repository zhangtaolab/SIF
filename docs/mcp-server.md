# MCP Server

SIF includes a Model Context Protocol (MCP) server for integration with AI assistants and other MCP-compatible tools.

## Overview

The Model Context Protocol (MCP) is an open protocol that enables seamless integration between AI systems and external data sources. SIF's MCP server allows AI assistants to:

- Search your document collections
- Retrieve specific documents
- List available collections
- Get indexing status

## Architecture

```
+-----------------+      +------------------+      +--------------+
|   AI Assistant  |<---->|   MCP Server     |<---->|   SIF    |
|  (Claude, etc.) |      |  (stdio/http)    |      |   Backend    |
+-----------------+      +------------------+      +--------------+
```

## Implementation Note

SIF has two MCP implementations:
- **Legacy**: `sif/mcp/` — functional style (deprecated)
- **Refactored**: `sif/mcp_server/` — OOP with `Transport` ABC

The CLI commands use the legacy implementation for backward compatibility.

## Transport Types

SIF's MCP server supports two transport methods:

### stdio Transport (Default)

Uses standard input/output for communication. Ideal for local AI assistants.

```bash
sif mcp stdio
```

**Use cases:**
- Claude Desktop
- Local AI assistants
- Command-line integrations

### HTTP Transport

Uses HTTP for communication. Ideal for remote or distributed setups.

```bash
sif mcp http --host 127.0.0.1 --port 8080
```

**Use cases:**
- Remote AI services
- Web-based assistants
- Distributed systems

### Daemon Transport

Runs the MCP server as a background daemon.

```bash
# Start daemon
sif mcp daemon --host 127.0.0.1 --port 3000

# Stop daemon
sif mcp daemon --stop
```

## Available Tools

### search

Search indexed documents using various search strategies.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Search query |
| `collection` | string | No | Collection name to search |
| `search_type` | string | No | Search type: "bm25", "vector", "hybrid" |
| `limit` | integer | No | Maximum results (default: 10) |

**Example:**
```json
{
  "name": "search",
  "arguments": {
    "query": "python decorators",
    "collection": "my-notes",
    "search_type": "hybrid",
    "limit": 5
  }
}
```

**Response:**
```json
{
  "results": [
    {
      "document_id": "doc_abc123",
      "document_path": "/notes/python/decorators.md",
      "document_title": "Python Decorators",
      "score": 0.89,
      "content_preview": "Python decorators are a powerful feature...",
      "highlights": ["decorators are a powerful"]
    }
  ],
  "total": 23,
  "search_time_ms": 45
}
```

### get_document

Retrieve a specific document by ID.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document_id` | string | Yes | Document ID |

**Example:**
```json
{
  "name": "get_document",
  "arguments": {
    "document_id": "doc_abc123"
  }
}
```

**Response:**
```json
{
  "document": {
    "id": "doc_abc123",
    "path": "/notes/python/decorators.md",
    "title": "Python Decorators",
    "content": "Full document content...",
    "metadata": {
      "tags": ["python", "advanced"]
    }
  }
}
```

### list_collections

List all available collections.

**Parameters:**
None

**Example:**
```json
{
  "name": "list_collections"
}
```

**Response:**
```json
{
  "collections": [
    {
      "id": "col_xyz789",
      "name": "my-notes",
      "description": "Personal notes",
      "document_count": 42,
      "paths": ["~/Documents/notes"]
    },
    {
      "id": "col_abc456",
      "name": "work-docs",
      "description": "Work documentation",
      "document_count": 156,
      "paths": ["~/Work/docs"]
    }
  ]
}
```

### get_collection

Get details about a specific collection.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Collection name |

**Example:**
```json
{
  "name": "get_collection",
  "arguments": {
    "name": "my-notes"
  }
}
```

**Response:**
```json
{
  "collection": {
    "id": "col_xyz789",
    "name": "my-notes",
    "description": "Personal notes",
    "document_count": 42,
    "chunk_count": 156,
    "paths": ["~/Documents/notes"],
    "created_at": "2024-01-15T10:30:00Z",
    "last_indexed_at": "2024-01-20T14:22:00Z"
  }
}
```

### get_status

Get indexing status.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `collection` | string | No | Collection name (optional) |

**Example:**
```json
{
  "name": "get_status",
  "arguments": {
    "collection": "my-notes"
  }
}
```

**Response:**
```json
{
  "status": {
    "collections": 3,
    "total_documents": 523,
    "total_chunks": 2456,
    "collection_status": {
      "name": "my-notes",
      "documents": 42,
      "chunks": 156,
      "last_indexed": "2024-01-20T14:22:00Z"
    }
  }
}
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SIF_MCP_HOST` | `127.0.0.1` | HTTP server host |
| `SIF_MCP_PORT` | `8080` | HTTP server port |
| `SIF_MCP_TRANSPORT` | `stdio` | Default transport type |

### .env File Example

```bash
# MCP Server Configuration
SIF_MCP_HOST=127.0.0.1
SIF_MCP_PORT=8080
SIF_MCP_TRANSPORT=stdio

# Database
SIF_DB_PATH=~/.local/share/sif/sif.db

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
      "args": ["mcp", "stdio"]
    }
  }
}
```

Location:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

### Custom MCP Client

```python
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def use_sif_mcp():
    # Configure server parameters
    server_params = StdioServerParameters(
        command="sif",
        args=["mcp", "stdio"]
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            print(f"Available tools: {[tool.name for tool in tools.tools]}")

            # Search documents
            result = await session.call_tool(
                "search",
                arguments={
                    "query": "python decorators",
                    "limit": 5
                }
            )
            print(json.dumps(result, indent=2))

asyncio.run(use_sif_mcp())
```

### HTTP Client

```python
import requests

# Start server: sif mcp http --host 127.0.0.1 --port 8080

response = requests.post(
    "http://127.0.0.1:8080/mcp/tools/search",
    json={
        "query": "python decorators",
        "limit": 5
    }
)

results = response.json()
print(results)
```

## Security Considerations

### Local-First Design

- All data stays on your machine
- No data sent to external services
- AI assistant only accesses indexed documents

### Network Security (HTTP Transport)

- Default binds to localhost only
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
curl http://127.0.0.1:8080/mcp/health
```

### Tool Not Found

```bash
# List available MCP commands
sif mcp --help
```

## Advanced Usage

### Custom Tool Handlers

Extend the MCP server with custom tools:

```python
from sif.mcp_server.server import MCPServer
from sif.mcp_server.transport import StdioTransport
from sif.mcp_server.handlers import ToolHandler

class CustomToolHandler(ToolHandler):
    @property
    def name(self) -> str:
        return "custom_search"

    @property
    def description(self) -> str:
        return "Custom search with filters"

    def handle(self, arguments: dict) -> dict:
        # Custom implementation
        return {"results": []}

# Create server with custom handler
transport = StdioTransport()
server = MCPServer(transport, tool_handlers=[CustomToolHandler()])
server.start()
```

### Multiple Transports

Run multiple transport types simultaneously:

```bash
# Terminal 1: stdio for Claude
sif mcp stdio

# Terminal 2: HTTP for web integration
sif mcp http --port 8080
```

## Performance Tuning

### Batch Size

Adjust batch size for large collections:

```bash
export SIF_BATCH_SIZE=500
```

### Connection Pooling

The MCP server reuses database connections automatically.

## API Reference

### MCPServer

```python
class MCPServer:
    def __init__(
        self,
        transport: Transport,
        tool_handlers: list[ToolHandler] | None = None,
    ) -> None

    def start(self) -> None
    def stop(self) -> None
    @property
    def is_running(self) -> bool
```

### Transport

```python
class Transport(ABC):
    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def send(self, message: dict) -> None: ...

    @abstractmethod
    def receive(self) -> dict: ...
```

### StdioTransport

```python
class StdioTransport(Transport):
    def __init__(self) -> None: ...
```

### HttpTransport

```python
class HttpTransport(Transport):
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8080,
    ) -> None: ...
```

## Best Practices

1. **Use stdio for local AI assistants** - More secure, no network exposure
2. **Use HTTP for distributed systems** - Better for remote access
3. **Monitor logs** - Check for errors and performance issues
4. **Regular indexing** - Keep index up to date for accurate results

## Related Documentation

- [Configuration](configuration.md) - MCP configuration options
- [CLI Reference](cli-reference.md) - MCP CLI commands
- [Architecture](architecture.md) - MCP server architecture
