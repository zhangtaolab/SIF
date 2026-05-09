# Phase 9: MCP Server Implementation - Context

**Gathered:** 2026-05-09
**Status:** Ready for planning

## Phase Boundary

Replace the dual legacy/refactored MCP implementations with a single unified `src/sif/mcp/` package that exposes real search and document retrieval capabilities through stdio and HTTP transports, following the MCP 2024-11-05 protocol lifecycle and the new Streamable HTTP standard (2025-11-25) for HTTP mode.

## Requirements (locked via SPEC.md)

**8 requirements are locked.** See `09-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `09-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):**
- Unified `src/sif/mcp/` package replacing both legacy implementations
- `SearchBackend` connecting to real database and search pipeline
- 4 MCP tools: `query`, `get`, `multi_get`, `status`
- stdio transport with MCP 2024-11-05 protocol lifecycle
- HTTP transport with Streamable HTTP standard (single `/mcp` endpoint)
- Secure CORS defaults for HTTP mode
- Resources: `docs://{doc_id}` with optional line slicing
- CLI command updates to use new implementation
- Unit and integration tests for MCP tools and transports

**Out of scope (from SPEC.md):**
- `IndexTool`, `CollectionTool` (create/delete collections)
- MCP Prompts
- Real-time SSE push notifications for index changes
- OAuth or authentication layer
- Backwards compatibility with old HTTP+SSE transport (2024-11-05)

## Implementation Decisions

### Architecture Style
- **D-01:** Reuse legacy `mcp/protocol.py` Pydantic models (JsonRpcRequest, ToolsCallResult, MCPTool, SearchResult, Document, CollectionInfo, etc.)
  - Rationale: Models are well-defined, match MCP spec, and used by tools.py. Rewriting adds cost without benefit.
- **D-02:** Use OOP `ToolHandler` ABC pattern (from `mcp_server/handlers.py`)
  - Each tool is a class implementing `name`, `description`, `input_schema`, `handle()`
  - Tools register with `MCPServer` at startup
- **D-03:** Directory structure: functional layering (Option A)
  ```
  src/sif/mcp/
  ├── __init__.py
  ├── protocol.py          # Pydantic models (reused from legacy)
  ├── server.py            # MCPServer main class
  ├── handlers.py          # ToolHandler ABC + concrete tool classes
  ├── backend.py           # SearchBackend (connects to real search)
  ├── transports/
  │   ├── __init__.py
  │   ├── stdio.py         # stdio transport
  │   └── http.py          # HTTP Streamable HTTP transport
  └── cli.py               # CLI commands (sif mcp stdio/http)
  ```

### SearchBackend Lifecycle
- **D-04:** New `DatabaseConnection` per tool call (safety first)
  - Each `SearchBackend` method creates its own connection, runs query, closes
  - No long-lived connections, no concurrency issues
- **D-05:** `SearchBackend` methods are `async`
  - Internal sync sqlite3 calls wrapped with `asyncio.to_thread()` or `run_in_executor()`
  - Matches async transport layer semantics
- **D-06:** Embedder/model cached via `EmbeddingManager` singleton
  - `SearchBackend` creates new connections each call, but embedder is reused
  - `EmbeddingManager._model` already caches the loaded model instance
  - First request slow (model load), subsequent requests fast

### stdio Protocol Strictness
- **D-07:** Full MCP lifecycle implementation
  - `initialize` -> `notifications/initialized` -> `tools/list` -> `tools/call`
  - Reject requests before initialize with `ServerNotInitialized` error
  - Match Claude Desktop standard flow exactly
- **D-08:** Tiered error handling
  - Fatal errors (DB file missing, schema incompatible) -> exit process
  - Recoverable errors (query syntax error, doc not found) -> JSON-RPC error response, transport continues
- **D-09:** Full notification support
  - Handle `notifications/initialized`, `notifications/progress`, `notifications/cancelled`
  - `cancelled` interrupts in-flight tool calls

### HTTP Endpoint Design
- **D-10:** Streamable HTTP (2025-11-25 new standard)
  - Single `/mcp` endpoint supporting POST and GET
  - POST returns either `application/json` (simple response) or `text/event-stream` (SSE stream)
  - GET opens SSE stream for server-initiated messages
  - Session management via `MCP-Session-Id` header
- **D-11:** No backwards compatibility with old HTTP+SSE transport
  - Old `/mcp/v1/sse` and `/mcp/v1/messages` endpoints are NOT implemented
  - Only the new Streamable HTTP `/mcp` endpoint

### Security
- **D-12:** Default bind to `127.0.0.1` (not `0.0.0.0`)
- **D-13:** Validate `Origin` header, reject invalid with 403
- **D-14:** CORS defaults: `["http://localhost:3000", "http://127.0.0.1:3000"]` (non-wildcard)
  - CLI `--cors-origins` accepts explicit list
  - `"*"` requires explicit `--cors-origins '*'`

### Resources
- **D-15:** Resource URI scheme: `docs://{doc_id}`
  - Optional query params: `?from_line=N&max_lines=M`
  - MIME type: `text/markdown` for `.md` files, `text/plain` for others

### Claude's Discretion
- Exact error message wording and codes
- Whether to add convenience endpoints (e.g., `/health`) beyond the standard MCP endpoint
- Specific asyncio executor strategy (to_thread vs run_in_executor)
- Resource URI format details (e.g., whether to support `collection://` in future)

## Specific Ideas

- Follow the official MCP 2025-11-25 specification for Streamable HTTP exactly
- `sif mcp stdio` should work out-of-the-box with Claude Desktop configuration
- `sif mcp http --port 3000` should start a server that passes `curl` smoke tests
- Tool responses should include score information so LLM can judge relevance

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### MCP Specification
- `https://modelcontextprotocol.io/specification/2025-11-25/basic/transports` — Streamable HTTP standard (replaces SSE)
- `https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle` — MCP lifecycle (initialize, tools/list, tools/call)
- `https://modelcontextprotocol.io/specification/2025-11-25/basic/messages` — JSON-RPC message format

### Project Requirements
- `.planning/phases/09-mcp-server-implementation/09-SPEC.md` — Locked requirements, boundaries, acceptance criteria
- `.planning/REQUIREMENTS.md` — MCP-01 through MCP-04 v2 requirements

### Existing MCP Code (to be deleted but informative)
- `src/sif/mcp/protocol.py` — Pydantic models to reuse
- `src/sif/mcp/transport_stdio.py` — stdio transport patterns
- `src/sif/mcp/transport_http.py` — HTTP transport patterns (old standard)
- `src/sif/mcp_server/handlers.py` — ToolHandler ABC to adopt
- `src/sif/mcp_server/transport.py` — Transport ABC

### Search and Database Integration
- `src/sif/search/bm25.py` — BM25Searcher
- `src/sif/search/hybrid.py` — HybridSearcher
- `src/sif/search/vector.py` — VectorSearcher
- `src/sif/database/connection.py` — DatabaseConnection
- `src/sif/database/repositories.py` — DocumentRepository, CollectionRepository
- `src/sif/embedding/embedder.py` — EmbeddingManager (model caching)

### CLI Integration
- `src/sif/cli/commands/mcp.py` — Existing CLI commands to update

## Existing Code Insights

### Reusable Assets
- `src/sif/mcp/protocol.py` — Complete Pydantic models for JSON-RPC/MCP protocol
- `src/sif/mcp_server/handlers.py` — ToolHandler and ResourceHandler ABCs
- `src/sif/mcp/transport_stdio.py` — Async stdio read/write loop with JSON parsing
- `src/sif/mcp/transport_http.py` — FastAPI app setup, CORS middleware, SSE event generation
- `src/sif/mcp/tools.py` — MockSearchBackend shows the expected tool interface

### Established Patterns
- All database access through `DatabaseConnection` context manager
- Searchers instantiated per-query with `Settings`-based configuration
- `EmbeddingManager._model` caches the loaded embedding model
- CLI commands use Click with `@click.pass_context`
- Error handling: `click.ClickException(str(e))` for CLI, JSON-RPC error codes for MCP

### Integration Points
- `sif.cli.commands.mcp` imports from `sif.mcp.server` and `sif.mcp.server_http` — must update to new package
- `sif.cli.main` registers MCP command group
- SearchBackend needs `Settings` (via `get_settings()`) for model paths and DB path
- Tool handlers need access to `SearchBackend` instance

## Deferred Ideas

- `IndexTool` for triggering re-indexing via MCP — use CLI `sif index` instead
- `CollectionTool` for creating/deleting collections via MCP — use CLI `sif collection` instead
- MCP Prompts support — not needed for search/retrieval use case
- OAuth/authentication layer for HTTP mode — local tool, trust boundary is host machine
- Real-time file watching and push notifications — request-response model is sufficient
- Resource listing (`resources/list`) beyond docs:// — could add collection:// in future

---

*Phase: 09-mcp-server-implementation*
*Context gathered: 2026-05-09*
*Next step: /gsd-plan-phase 9 — implementation planning*
