# SIF MCP Server

The Model Context Protocol server for SIF, built on the official Python SDK
(`mcp>=2.3.0,<3`).

## Where to look

- **[`docs/mcp-server.md`](../../docs/mcp-server.md)** — the user guide:
  architecture, transports, the seven tools, configuration, plugin install,
  transport security, and troubleshooting.
- **`app.py`** — the composition root: `build_server`, `create_http_app`,
  `run_stdio`, `run_http`, and the transport-security resolution.
- **`tools.py`** — `register_tools(mcp, backend)` and `register_resource`:
  the seven tool definitions, descriptions, annotations, and dual-channel
  results.
- **`backend.py`** — `SearchBackend`, the transport-independent service the
  tools call.
- **`protocol.py`** — the SIF tool input/output models that drive
  `outputSchema`.
- **`watch_host.py`** — the optional embedded watcher lifespan
  (`SIF_MCP_WATCH=1`).

## At a glance

```python
from sif.mcp.app import build_server, create_http_app, run_stdio

# stdio host (model-free until the first vector query)
run_stdio("/path/to/sif.db")

# HTTP host: /mcp (Streamable HTTP) and /health on the parent app
app = create_http_app("/path/to/sif.db")

# The one MCPServer for this process; tools/resources register in its lifespan
server = build_server("/path/to/sif.db")
```

One `MCPServer` per process and exactly one `streamable_http_app()` call;
`app.py` owns that rule. `SearchBackend` is constructed inside the SDK
lifespan, never at import time.

## CLI

```bash
sif mcp stdio
sif mcp http --host 127.0.0.1 --port 8080
sif mcp daemon
```

## License

MIT
