---
phase: 09-mcp-server-implementation
plan: 01
status: complete
executed: 2026-05-12
---

# Plan 09-01: Unify MCP Package Structure

## Objective

Eliminate dual legacy/refactored MCP implementations and create a single unified `src/sif/mcp/` package with async server skeleton, ToolHandler ABC, and SearchBackend placeholder.

## What Was Built

### Files Created
- `src/sif/mcp/backend.py` — SearchBackend class with 4 async method stubs
- `src/sif/mcp/handlers.py` — ToolHandler ABC with async `handle(self, params, backend)` signature
- `src/sif/mcp/transports/__init__.py` — Transport subpackage placeholder

### Files Rewritten
- `src/sif/mcp/__init__.py` — Exports MCPServer, SearchBackend, ToolHandler
- `src/sif/mcp/server.py` — Async MCPServer with ServerState enum (CREATED, INITIALIZED, SHUTDOWN), tool registry, initialize/tools-list dispatch
- `src/sif/mcp/cli.py` — Thin CLI helpers (raise NotImplementedError pending 09-04/09-05)
- `src/sif/cli/commands/mcp.py` — Updated imports to `sif.mcp.cli`, added `--cors-origins` option

### Files Deleted
- `src/sif/mcp_server/` (entire directory)
- `src/sif/mcp/transport_stdio.py`
- `src/sif/mcp/transport_http.py`
- `src/sif/mcp/server_http.py`
- `src/sif/mcp/tools.py`
- `src/sif/mcp/test_mcp.py`

### Files Modified (Lint Fixes)
- `src/sif/mcp/protocol.py` — Added noqa comments for MCP spec camelCase field names (N815)

## Key Decisions

- Kept `protocol.py` Pydantic models (D-01)
- Changed ToolHandler.handle signature to include `backend: SearchBackend` (D-02)
- No ResourceHandler ABC — resources/read will be inline in server.py

## Self-Check

- [x] `src/sif/mcp_server/` directory does not exist
- [x] All legacy files removed
- [x] `python -c "from sif.mcp import MCPServer, SearchBackend, ToolHandler"` succeeds
- [x] `ruff check src/sif/mcp/` passes with zero errors
- [x] All Python files compile without syntax errors

## Deviations

None.
