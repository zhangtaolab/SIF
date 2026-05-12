# Phase 9: MCP Server Implementation — Specification

**Created:** 2026-05-09
**Ambiguity score:** 0.13
**Requirements:** 8 locked

## Goal

Replace the dual legacy/refactored MCP implementations with a single unified `src/sif/mcp/` package that exposes real search and document retrieval capabilities through stdio and HTTP transports, following the MCP 2024-11-05 protocol.

## Background

Two parallel MCP implementations currently exist:

- **`src/sif/mcp/`** (functional style): Has complete protocol definitions (`protocol.py`), async stdio transport (`transport_stdio.py`), HTTP transport with FastAPI/SSE (`transport_http.py`), and a server framework (`server.py`). However, `tools.py` defaults to `MockSearchBackend` returning hardcoded fake data. The `server.py` `_tool_query` method attempts real database queries but the implementation is incomplete and inconsistent.
- **`src/sif/mcp_server/`** (OOP style): Has clean abstractions (`Transport` ABC, `ToolHandler` ABC) but all tool handlers (`SearchTool`, `IndexTool`, `CollectionTool`) return hardcoded placeholder responses. The transport implementations are skeletal.

Neither implementation connects to the actual SQLite index or search pipeline. The CLI commands (`sif mcp stdio`, `sif mcp http`) import from the legacy package.

## Requirements

1. **Unified package structure**: A single MCP implementation replaces both legacy directories.
   - Current: Two incomplete packages (`mcp/` and `mcp_server/`) with divergent architectures
   - Target: One `src/sif/mcp/` package with clean abstractions; `mcp_server/` is deleted; old `mcp/` code is replaced
   - Acceptance: `ls src/sif/mcp_server/` returns "No such file"; `src/sif/mcp/` contains server.py, tools.py, transports/, protocol.py with no mock/placeholder implementations

2. **Real SearchBackend**: Tool handlers query the actual SQLite index instead of returning mock data.
   - Current: `MockSearchBackend` in `tools.py` returns hardcoded documents with fake scores
   - Target: `SearchBackend` class connects to `DatabaseConnection`, instantiates real `BM25Searcher`/`HybridSearcher`/`VectorSearcher`, and returns actual search results
   - Acceptance: Running `sif mcp stdio` and sending a `tools/call` for `query` with a known query returns results whose `doc_id` values exist in the database

3. **Tool handlers**: Four tools exposed via MCP protocol with real functionality.
   - Current: Tool definitions exist in protocol but handlers return mock data or are unimplemented
   - Target:
     - `query`: Hybrid search (BM25 + vector + rerank) with `collections`, `limit`, `min_score` params
     - `get`: Get document by path or doc_id with optional `from_line`/`max_lines`
     - `multi_get`: Batch get documents matching a glob pattern with `max_bytes` limit
     - `status`: Return collection list and total document count
   - Acceptance: Each tool called via stdio JSON-RPC returns data verifiable against the SQLite index (e.g., `status` document count matches `SELECT COUNT(*) FROM documents`)

4. **stdio transport**: Full MCP 2024-11-05 protocol over stdin/stdout for Claude Desktop integration.
   - Current: `transport_stdio.py` has async read/write but the server integration is incomplete
   - Target: Line-delimited JSON-RPC 2.0 with proper `initialize` handshake, `tools/list`, `tools/call`, and `resources/read` support; logs go to stderr only
   - Acceptance: Claude Desktop configuration pointing to `sif mcp stdio` successfully initializes and lists tools; sending a `query` call returns results

5. **HTTP transport**: FastAPI-based Streamable HTTP server for remote access (2025-11-25 standard).
   - Current: `transport_http.py` has FastAPI app with old SSE and JSON-RPC endpoints but no real tool integration
   - Target: FastAPI app exposes single `/mcp` endpoint supporting POST (JSON-RPC) and GET (SSE stream); tool calls execute real searches; session management via `MCP-Session-Id` header; proper startup/shutdown lifecycle
   - Acceptance: `curl -X GET http://localhost:3000/mcp` opens SSE stream; `curl -X POST http://localhost:3000/mcp` with a `tools/call` payload returns real search results; response includes `MCP-Session-Id` header for session tracking

6. **Secure CORS defaults**: HTTP mode does not use wildcard `*` origins by default.
   - Current: `cors_origins` defaults to `["*"]` in both `transport_http.py` and CLI
   - Target: Default CORS origins is `["http://localhost:3000", "http://127.0.0.1:3000"]`; CLI `--cors-origins` accepts explicit list; `"*"` requires explicit `--cors-origins '*'`
   - Acceptance: Starting HTTP server without `--cors-origins` and checking `Access-Control-Allow-Origin` on a response shows `http://localhost:3000`, not `*`

7. **Resources support**: Expose indexed documents as MCP resources with line-range slicing.
   - Current: `_handle_resources_read` returns `"Resources not implemented"`
   - Target: `docs://{doc_id}` URI returns document content; `docs://{doc_id}?from_line=10&max_lines=20` returns sliced content; MIME type is `text/markdown` for `.md` files, `text/plain` for others
   - Acceptance: A `resources/read` request for `docs://{known_doc_id}` returns content matching the document's full text in the database; with `?from_line=0&max_lines=1` returns only the first line

8. **CLI integration**: Existing `sif mcp stdio` and `sif mcp http` commands work with the new implementation.
   - Current: CLI imports from legacy `sif.mcp.server` and `sif.mcp.server_http`
   - Target: CLI imports from new unified `sif.mcp` package; command signatures unchanged; `sif mcp daemon` also uses new implementation
   - Acceptance: `sif mcp stdio --help` and `sif mcp http --help` work without ImportError; `sif mcp stdio` starts the stdio server; `sif mcp http --port 3000` starts the HTTP server

## Boundaries

**In scope:**
- Unified `src/sif/mcp/` package replacing both legacy implementations
- `SearchBackend` connecting to real database and search pipeline
- 4 MCP tools: `query`, `get`, `multi_get`, `status`
- stdio transport with MCP 2024-11-05 protocol
- HTTP transport with FastAPI and Streamable HTTP (single `/mcp` endpoint)
- Secure CORS defaults for HTTP mode
- Resources: `docs://{doc_id}` with optional line slicing
- CLI command updates to use new implementation
- Unit and integration tests for MCP tools and transports

**Out of scope:**
- `IndexTool` (trigger re-indexing) — use CLI `sif index` instead; indexing is a heavy operation that doesn't fit MCP tool call semantics
- `CollectionTool` (create/delete collections) — use CLI `sif collection` instead; collection management requires filesystem operations beyond MCP scope
- MCP Prompts — not needed for search/retrieval use case
- Real-time SSE push notifications for index changes — request-response model is sufficient
- OAuth or authentication layer — local tool, trust boundary is the host machine
- Windows-specific compatibility fixes for sqlite-vec — tracked as POL-04 in v2 requirements
- Web UI or dashboard for MCP server — MCP is an API protocol, not a user interface

## Constraints

- MCP protocol version: 2024-11-05 (current stable)
- HTTP framework: FastAPI (already a project dependency)
- HTTP transport standard: Streamable HTTP (2025-11-25) — single `/mcp` endpoint, POST for JSON-RPC, GET for SSE, `MCP-Session-Id` header for session tracking
- stdio transport: Line-delimited JSON-RPC 2.0; stdout must never contain non-JSON output (logs to stderr)
- SearchBackend must use `DatabaseConnection` context manager for safe connection handling
- Tool handler response format must match MCP `ToolsCallResult` schema (list of content items with `type: "text"`)
- Maximum document content returned in a single tool call: 100KB (to prevent oversized responses)
- CORS: No wildcard `*` by default; explicit opt-in required

## Acceptance Criteria

- [ ] `src/sif/mcp_server/` directory does not exist (deleted)
- [ ] `sif mcp stdio` starts without error and responds to `initialize` request with protocolVersion "2024-11-05"
- [ ] Claude Desktop configured with `sif mcp stdio` successfully lists 4 tools (query, get, multi_get, status)
- [ ] `curl -X GET http://localhost:3000/mcp` opens SSE stream with `text/event-stream` content type
- [ ] `curl -X POST http://localhost:3000/mcp` with a `tools/call` payload returns real search results and includes `MCP-Session-Id` header
- [ ] `tools/call` for `query` with a known search term returns results whose doc_ids exist in the database
- [ ] `tools/call` for `status` returns document count matching `SELECT COUNT(*) FROM documents`
- [ ] `resources/read` for `docs://{known_doc_id}` returns content matching the database
- [ ] HTTP server started without `--cors-origins` responds with `Access-Control-Allow-Origin: http://localhost:3000` (not `*`)
- [ ] `pytest tests/unit/mcp/` passes with >=80% coverage of `src/sif/mcp/`
- [ ] `ruff check src/sif/mcp/` passes with zero errors
- [ ] Full quality suite passes: `ruff check src tests`, `ruff format --check src tests`, `pytest`

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                              |
|--------------------|-------|------|--------|------------------------------------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | Complete rewrite, dual transports  |
| Boundary Clarity   | 0.90  | 0.70 | ✓      | Explicit 5-item out-of-scope list  |
| Constraint Clarity | 0.80  | 0.65 | ✓      | Protocol version, CORS, size limit |
| Acceptance Criteria| 0.85  | 0.70 | ✓      | 11 pass/fail checkboxes            |
| **Ambiguity**      | 0.13  | ≤0.20| ✓      | Gate passed after 3 rounds         |

## Interview Log

| Round | Perspective     | Question summary                          | Decision locked                                    |
|-------|-----------------|------------------------------------------|----------------------------------------------------|
| 1     | Researcher      | Which implementation to keep as base?    | **C — Complete rewrite**; neither base is adequate |
| 1     | Researcher      | Index/Collection tools in scope?         | **No** — only search/retrieval tools (4 total)     |
| 1     | Researcher      | Resources in scope?                      | **Yes** — basic Resources with line slicing        |
| 2     | Simplifier      | Irreducible core if 50% cut?             | **stdio + HTTP + all 4 tools**                     |
| 2     | Simplifier      | What does "basic Resources" mean?        | **docs://{doc_id} with from_line/max_lines**       |
| 2     | Simplifier      | Minimum success criteria?                | **Claude Desktop stdio + curl HTTP /mcp**          |
| 3     | Boundary Keeper | Confirm exclusions?                      | **All 5 exclusions confirmed**, no additions       |
| 3     | Boundary Keeper | Handle old implementations?              | **Delete old directories directly**                |
| 3     | Boundary Keeper | New implementation directory?            | **src/sif/mcp/**                                   |

---

*Phase: 09-mcp-server-implementation*
*Spec created: 2026-05-09*
*Next step: /gsd-discuss-phase 9 — implementation decisions (how to build what's specified above)*
