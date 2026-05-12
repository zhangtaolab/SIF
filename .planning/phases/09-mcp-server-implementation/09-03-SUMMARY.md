---
phase: 09-mcp-server-implementation
plan: 03
status: complete
executed: 2026-05-12
---

# Plan 09-03: Tool Handlers and Server Dispatch

## Objective

Implement four MCP tool handlers and wire tool registration, dispatch, and resources/read into MCPServer.

## What Was Built

### Files Updated
- `src/sif/mcp/handlers.py` — 4 concrete ToolHandler classes
  - `QueryToolHandler`: hybrid search with QueryInput validation
  - `GetToolHandler`: document retrieval with GetInput validation, returns isError=True for not found
  - `MultiGetToolHandler`: batch get with MultiGetInput validation, fnmatch pattern matching
  - `StatusToolHandler`: collection status with no required params
  - `create_default_tools(backend)`: helper returning all 4 handler instances

- `src/sif/mcp/server.py` — MCPServer dispatch logic
  - `register_tools`: Populates `self._tools` dict keyed by handler name
  - `tools/list`: Returns `ToolsListResult` with `MCPTool` definitions
  - `tools/call`: Looks up handler by name, calls `await handler.handle(arguments, self.backend)`, catches exceptions and returns `isError=True`
  - `resources/read`: Parses `docs://` URI with optional `from_line`/`max_lines` query params
  - Unknown tool returns `MCPErrorCode.UNKNOWN_TOOL` (-32601)
  - Request before initialize returns `SERVER_NOT_INITIALIZED` (-32002)

- `src/sif/mcp/__init__.py` — Updated exports

## Key Decisions

- resources/read is inline in server.py (no ResourceHandler ABC) per D-02 refinement
- All tool output is JSON-serialized via `json.dumps(..., ensure_ascii=False)` wrapped in `ToolContentItem(type="text", ...)`
- Handler exceptions caught at server level and returned as `isError=True` ToolsCallResult

## Self-Check

- [x] `python -c "from sif.mcp.handlers import create_default_tools; from sif.mcp.server import MCPServer; ..."` verifies registration
- [x] 4 tools registered by default
- [x] `ruff check src/sif/mcp/handlers.py src/sif/mcp/server.py` passes

## Deviations

- No separate `test_handlers.py` or `test_server.py` files created at this time — handler and server logic tested indirectly via backend tests and transport tests. Integration tests in 09-06 will cover full lifecycle.
