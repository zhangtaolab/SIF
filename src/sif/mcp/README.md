# SIF MCP Server

Model Context Protocol (MCP) server implementation for SIF.

## Features

- **Dual Transport Support**: stdio (for Claude Desktop) and HTTP (for web clients)
- **Six Search Tools**:
  - `query` - Hybrid search (FTS + Vector + Reranking)
  - `lex_search` - BM25 full-text search
  - `vec_search` - Vector semantic search
  - `get` - Get document by path or doc_id
  - `multi_get` - Batch get documents by pattern
  - `status` - Get index status
- **JSON-RPC 2.0 Protocol**: Full compliance with MCP specification
- **Server-Sent Events**: Real-time streaming for HTTP transport
- **FastAPI Integration**: Modern async web framework

## Installation

```bash
pip install fastapi uvicorn pydantic
```

## Usage

### Stdio Mode (Claude Desktop)

```python
from sif.mcp.transport_stdio import run_stdio
run_stdio()
```

Or run directly:
```bash
python -m sif.mcp.transport_stdio
```

### HTTP Mode

```python
from sif.mcp.transport_http import run_http_server

async def main():
    await run_http_server(host="0.0.0.0", port=8080)

import asyncio
asyncio.run(main())
```

Or run directly:
```bash
python -m sif.mcp.transport_http --host 0.0.0.0 --port 8080
```

## API Endpoints (HTTP Mode)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/mcp/v1/sse` | GET | Server-Sent Events stream |
| `/mcp/v1/messages` | POST | JSON-RPC message endpoint |
| `/mcp/v1/batch` | POST | Batch JSON-RPC messages |
| `/mcp/v1/tools` | GET | List available tools |
| `/mcp/v1/status` | GET | Get server status |

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

### lex_search

BM25 full-text search for keyword-based document retrieval.

**Input:**
```json
{
  "query": "search terms",
  "collections": ["default"],
  "limit": 10
}
```

### vec_search

Vector semantic search for finding documents with similar meaning.

**Input:**
```json
{
  "query": "search terms",
  "collections": ["default"],
  "limit": 10
}
```

### get

Get a document by its path or document ID.

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
      "last_updated": "2024-01-01T00:00:00",
      "size_bytes": 1024000
    }
  ],
  "total_documents": 100
}
```

## Protocol Flow

1. **Initialize**: Client sends `initialize` request
2. **Ready**: Server responds with capabilities
3. **Notification**: Client sends `notifications/initialized`
4. **Tools/List**: Client requests available tools
5. **Tools/Call**: Client calls tools as needed

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

## Configuration

### ServerConfig

```python
from sif.mcp import ServerConfig

config = ServerConfig(
    name="my-mcp-server",
    version="1.0.0",
    protocol_version="2024-11-05",
    enable_logging=True,
    max_concurrent_requests=100
)
```

### Custom Search Backend

```python
from sif.mcp import ToolRegistry, SearchBackend

class MySearchBackend(SearchBackend):
    async def hybrid_search(self, query, collections=None, limit=10, min_score=0.0):
        # Your implementation
        pass
    
    # ... implement other methods

tool_registry = ToolRegistry(backend=MySearchBackend())
```

## License

MIT
