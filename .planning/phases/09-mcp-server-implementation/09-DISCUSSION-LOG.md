# Phase 9: MCP Server Implementation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-09
**Phase:** 09-mcp-server-implementation
**Areas discussed:** Architecture Style, SearchBackend Lifecycle, stdio Protocol Strictness, HTTP Endpoint Design

---

## Architecture Style

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse protocol.py | Keep Pydantic models from legacy mcp/protocol.py | ✓ |
| Rewrite models | Define simplified models from scratch | |
| OOP ToolHandler ABC | Each tool is a class with name/desc/schema/handle | ✓ |
| Functional handlers | Each tool is a function mapped name→callable | |
| Directory A (functional) | handlers.py + backend.py + transports/ | ✓ |
| Directory B (by role) | tools/ subdir with query.py, get.py, etc. | |
| Directory C (flat) | Single tools.py, no subdirs | |

**User's choice:** Reuse protocol.py + OOP ToolHandler ABC + Directory A (functional layering)
**Notes:** User explicitly chose "C — Complete rewrite" for overall approach, but agreed to reuse protocol.py models as they are SIF-specific (SearchResult, Document, etc.) rather than generic MCP. OOP pattern chosen for testability and clarity.

---

## SearchBackend Lifecycle

| Option | Description | Selected |
|--------|-------------|----------|
| New connection per call | Each tool call creates fresh DatabaseConnection | ✓ |
| Cached connection | Single long-lived connection | |
| Lazy init + health check | Create on first call, with health monitoring | |
| async SearchBackend | async methods wrapping sync sqlite3 | ✓ |
| sync SearchBackend | sync methods, transport wraps in executor | |
| Cache embedder | EmbeddingManager singleton, new DB each call | ✓ |
| Cache SearchBackend | Reuse searcher instances | |
| Lazy load + timeout | Load on first use, timeout and release | |

**User's choice:** New connection per call + async SearchBackend + cache embedder
**Notes:** User requested detailed analysis of all three embedder caching options before deciding. Chose A (cache embedder) because it balances safety (new DB connections) with performance (cached models), and aligns with existing EmbeddingManager._model caching.

---

## stdio Protocol Strictness

| Option | Description | Selected |
|--------|-------------|----------|
| Full MCP lifecycle | initialize → initialized → tools/list → tools/call | ✓ |
| Minimal | Skip handshake, handle any request directly | |
| JSON-RPC error | Return error response, transport continues | |
| isError result | Return isError=true in tool result | |
| Tiered error handling | Fatal→exit, recoverable→error response | ✓ |
| Ignore notifications | Drop all notifications silently | |
| Handle initialized only | Only process notifications/initialized | |
| Full notification support | Handle initialized, progress, cancelled | ✓ |

**User's choice:** Full MCP lifecycle + Tiered error handling + Full notification support
**Notes:** User consistently chose the most complete/strict option for stdio protocol handling.

---

## HTTP Endpoint Design

| Option | Description | Selected |
|--------|-------------|----------|
| Streamable HTTP (new) | Single /mcp endpoint, POST/GET, session-aware | ✓ |
| Old HTTP+SSE | Separate /sse and /messages endpoints | |
| Keep old endpoints | Support both old and new | |
| Drop old endpoints | Only new standard, no backwards compat | ✓ |

**User's choice:** Streamable HTTP (2025-11-25 new standard) + No backwards compatibility
**Notes:** User provided the URL https://modelcontextprotocol.io/specification/2025-11-25/basic/transports and explicitly stated "SSE 已经弃用" (SSE is deprecated). After reviewing the new spec, confirmed adoption of Streamable HTTP with single /mcp endpoint.

---

## Claude's Discretion

- Error message wording and exact JSON-RPC error codes
- Whether to add non-standard convenience endpoints (e.g., /health)
- Async executor strategy specifics (to_thread vs run_in_executor)
- Resource URI format beyond docs://{doc_id}

## Deferred Ideas

- IndexTool for triggering re-indexing via MCP — use CLI instead
- CollectionTool for collection management via MCP — use CLI instead
- MCP Prompts support — not needed for search/retrieval
- OAuth/authentication for HTTP mode — local tool, host-level trust
- Real-time file watching and push notifications
- Resource listing beyond docs:// (e.g., collection://)
- Backwards compatibility with old HTTP+SSE endpoints

---

*Phase: 09-mcp-server-implementation*
*Discussion log generated: 2026-05-09*
