---
phase: 01-foundation-fix
plan: 06
subsystem: mcp
tags: [mcp, sqlite, connection-per-request, concurrency]
dependencies:
  requires: [01-02, 01-05]
  provides: []
  affects: [src/docsift/mcp/server.py, src/docsift/mcp/server_http.py]
tech-stack:
  added: []
  patterns: [connection-per-request, context-manager]
key-files:
  created: []
  modified:
    - src/docsift/mcp/server.py
    - src/docsift/mcp/server_http.py
decisions: []
metrics:
  duration: "0h 10m"
  completed_date: "2026-04-15"
---

# Phase 01 Plan 06: MCP Connection-Per-Request Refactor Summary

Refactored the MCP server to create a fresh SQLite connection per request, eliminating cached connection sharing across async and multi-threaded contexts.

## What Was Done

- Replaced persistent `Database` instance in `MCPServer` with on-demand `DatabaseConnection` usage in every tool handler.
- Removed `self.db` attribute and `initialize()` method from `MCPServer`.
- Updated `_tool_query`, `_tool_lex_search`, `_tool_get`, `_tool_multi_get`, and `_tool_status` to open a new `DatabaseConnection(self.index_path).transaction()` context, initialize schema, execute the query, and close the connection automatically.
- Removed `server.initialize()` calls from `run_stdio_server` and the HTTP server setup.

## Commits

| Hash | Message |
|------|---------|
| cc4c7d1 | feat(01-06): refactor MCPServer to use connection-per-request |
| ffd8496 | feat(01-06): update MCP HTTP server to avoid persistent Database |

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- [x] `src/docsift/mcp/server.py` imports `DatabaseConnection`
- [x] `src/docsift/mcp/server.py` contains no `self.db` references
- [x] `src/docsift/mcp/server.py` contains no `initialize` method
- [x] `src/docsift/mcp/server_http.py` contains no `server.initialize()` call
- [x] Import verification passed for both modules
