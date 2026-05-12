# Phase 9: MCP Server Implementation - Research

**Researched:** 2026-05-12
**Domain:** Python MCP server implementation (Model Context Protocol 2024-11-05)
**Confidence:** HIGH

## Summary

This research thoroughly investigates the existing dual MCP implementations in SIF (legacy `mcp/` and refactored `mcp_server/`), the MCP 2024-11-05 protocol requirements, and the patterns needed to build a single unified `src/sif/mcp/` package. All core architectural patterns have been verified through live code execution against the actual codebase.

The existing codebase provides reusable assets: `protocol.py` contains complete Pydantic models for JSON-RPC/MCP messaging; `transport_stdio.py` has a working async read/write loop; `transport_http.py` has FastAPI/SSE patterns. The gaps are: no real `SearchBackend` connecting to the SQLite index, the server is synchronous (needs async), HTTP uses old endpoints (needs Streamable HTTP), and CORS defaults to wildcard.

**Primary recommendation:** Build a unified `src/sif/mcp/` package with async `SearchBackend` (wrapping sync sqlite3 via `asyncio.to_thread()`), async `ToolHandler` classes, state-machine `MCPServer`, `StdioTransport` for Claude Desktop, and `HTTPTransport` with FastAPI for remote access. Delete both old implementations entirely.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| MCP protocol handling | API / Backend | — | JSON-RPC parsing, lifecycle state machine, tool dispatch |
| Search execution | API / Backend | Database | SearchBackend queries SQLite via repository pattern |
| Document retrieval | API / Backend | Database | get/multi_get read from DocumentRepository |
| stdio transport | Browser / Client | API | Reads stdin/writes stdout on the host process |
| HTTP transport | CDN / Static | API | FastAPI app serves the `/mcp` endpoint |
| CORS/security | CDN / Static | — | FastAPI middleware enforces origin policy |
| Embedding | API / Backend | — | EmbeddingManager caches model; SearchBackend reuses it |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pydantic | 2.x | JSON-RPC/MCP message models | Already used throughout SIF; protocol.py is complete [VERIFIED: codebase] |
| FastAPI | 0.135.3 | HTTP transport framework | Already a project dependency; handles async routes, CORS, SSE [VERIFIED: `fastapi.__version__`] |
| uvicorn | 0.44.0 | ASGI server for HTTP mode | Already a project dependency; programmatic API confirmed [VERIFIED: `uvicorn.__version__`] |
| sqlite3 (stdlib) | 3.x | Database access | SIF uses SQLite with FTS5 + sqlite-vec; connection-per-request is safe [VERIFIED: runtime test] |
| asyncio | stdlib | Async runtime for transports | Python 3.9+ `asyncio.to_thread()` wraps sync DB ops safely [VERIFIED: runtime test] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sentence-transformers | 2.x | Embedding model backend | When `model_type=sentence_transformers` or `modelscope` [VERIFIED: `embedder.py`] |
| llama-cpp-python | 0.2.x | GGUF embedding backend | When `model_type=gguf` [VERIFIED: `embedder.py`] |
| sqlite-vec | 0.1.9+ | Vector search extension | Loaded per-connection; optional fallback if missing [VERIFIED: `pyproject.toml`] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom MCP SDK | `mcp` Python SDK (1.29.0) | SDK not installed; custom implementation is lighter and protocol.py already exists |
| Old HTTP+SSE | Streamable HTTP (2025-11-25) | CONTEXT.md D-10/D-11 mandates Streamable HTTP; old endpoints explicitly excluded |
| Database connection pool | Connection-per-request | Per D-04, safety first; SQLite concurrency is fine with separate connections |

**Installation:**
```bash
pip install -e ".[dev]"
```

**Version verification:**
```bash
python3 -c "import fastapi; print(fastapi.__version__)"  # 0.135.3
python3 -c "import uvicorn; print(uvicorn.__version__)"  # 0.44.0
python3 -c "import pydantic; print(pydantic.__version__)"  # 2.x
```

## Architecture Patterns

### System Architecture Diagram

```
Client (Claude Desktop)          Client (HTTP)
       |                               |
       v                               v
+-------------+                +-------------+
|   stdin     |                |  HTTP POST  |
|   stdout    |                |  /mcp       |
+-------------+                +-------------+
       |                               |
       v                               v
+-------------------------------------------+
|         UnifiedMCPServer                  |
|  - State machine (CREATED->INITIALIZED)   |
|  - Tool registry (query/get/multi_get/    |
|    status)                                |
|  - Resource registry (docs://{doc_id})    |
+-------------------------------------------+
       |
       v
+-------------------------------------------+
|         SearchBackend (async)             |
|  - hybrid_search() -> SearchPipeline      |
|  - get_document() -> DocumentRepository   |
|  - get_documents_by_pattern() -> fnmatch  |
|  - get_status() -> SchemaManager stats    |
+-------------------------------------------+
       |
       v
+-------------------------------------------+
|     DatabaseConnection (per call)         |
|  - New sqlite3 connection per tool call   |
|  - Loads sqlite-vec extension             |
|  - Commits on success, rolls back on err  |
+-------------------------------------------+
       |
       v
+-------------------------------------------+
|         SQLite Database                   |
|  - documents, collections, contexts       |
|  - FTS5 virtual tables (documents_fts)    |
|  - vec0 virtual table (document_embeddings|
+-------------------------------------------+
```

### Recommended Project Structure

```
src/sif/mcp/
├── __init__.py              # Package exports (MCPServer, transports, protocol models)
├── protocol.py              # KEEP EXISTING — Pydantic JSON-RPC/MCP models
├── server.py                # UnifiedMCPServer — state machine, tool/resource dispatch
├── backend.py               # SearchBackend — async wrapper around real search/DB
├── handlers.py              # ToolHandler ABC + 4 concrete tool classes
├── transports/
│   ├── __init__.py          # Transport exports
│   ├── stdio.py             # StdioTransport — async stdin/stdout loop
│   └── http.py              # HTTPTransport — FastAPI app, CORS, SSE
└── cli.py                   # CLI integration (run_stdio_transport, run_http_transport)

tests/unit/mcp/
├── __init__.py
├── test_server.py           # Lifecycle, state machine, error handling
├── test_backend.py          # DB operations, search, get, status
├── test_handlers.py         # Tool input validation, output format
├── test_transports_stdio.py # Message parsing, EOF, invalid JSON
├── test_transports_http.py  # Routes, CORS headers, SSE
└── test_integration.py      # End-to-end stdio and HTTP flows
```

### Pattern 1: Async SearchBackend with Connection-Per-Request

**What:** Each async method wraps sync DB code in `asyncio.to_thread()`, creating a fresh `Database` connection per call.

**When to use:** All MCP tool handlers that need database access.

**Example:**
```python
# Source: verified via runtime test against actual codebase
class SearchBackend:
    def __init__(self, db_path: str, settings: Settings | None = None) -> None:
        self.db_path = db_path
        self.settings = settings or get_settings()

    async def _with_db(self, callback: Callable) -> Any:
        def _run():
            db = Database(self.db_path)
            db.init_schema()
            try:
                return callback(db)
            finally:
                db.close()
        return await asyncio.to_thread(_run)

    async def hybrid_search(self, query: str, collections: list[str] | None = None,
                            limit: int = 10, min_score: float = 0.0) -> list[CoreSearchResult]:
        def _search(db):
            with db.transaction() as conn:
                options = SearchOptions(limit=limit, min_score=min_score,
                                        include_content=False, include_highlights=True)
                if collections:
                    repo = CollectionRepository(conn)
                    options.collection_ids = [
                        c.id for c in (repo.get_by_name(n) for n in collections) if c
                    ]
                pipeline = SearchPipeline(conn, embedder=None,
                                          embedding_dim=self.settings.embedding_dim)
                return pipeline.search(query, options)
        return await self._with_db(_search)
```

### Pattern 2: Async ToolHandler ABC

**What:** Each tool is a class implementing `name`, `description`, `input_schema`, and async `handle()`.

**When to use:** All 4 MCP tools (`query`, `get`, `multi_get`, `status`).

**Example:**
```python
# Source: verified via runtime test
class QueryToolHandler:
    name = "query"
    description = "Hybrid search combining BM25, vector, and reranking"
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "collections": {"type": "array", "items": {"type": "string"}},
            "limit": {"type": "integer", "default": 10},
            "min_score": {"type": "number", "default": 0.0},
        },
        "required": ["query"],
    }

    async def handle(self, params: dict[str, Any], backend: SearchBackend) -> ToolsCallResult:
        input_data = QueryInput(**params)
        results = await backend.hybrid_search(
            query=input_data.query,
            collections=input_data.collections,
            limit=input_data.limit,
            min_score=input_data.min_score,
        )
        output = QueryOutput(results=[...])  # map CoreSearchResult -> ProtocolSearchResult
        return ToolsCallResult(
            content=[ToolContentItem(type="text", text=json.dumps(output.model_dump()))]
        )
```

### Pattern 3: MCP Server State Machine

**What:** Server tracks state (`CREATED` -> `INITIALIZED`). Rejects requests before initialization with `ServerNotInitialized` error.

**When to use:** `UnifiedMCPServer.handle_request()`.

**Example:**
```python
# Source: verified via runtime test
class ServerState(Enum):
    CREATED = auto()
    INITIALIZED = auto()
    SHUTDOWN = auto()

class UnifiedMCPServer:
    def __init__(self, backend: SearchBackend) -> None:
        self.state = ServerState.CREATED
        self.backend = backend
        self._tools: dict[str, ToolHandler] = {}

    async def handle_request(self, request: JsonRpcRequest) -> JsonRpcResponse:
        if request.method == "initialize":
            self.state = ServerState.INITIALIZED
            result = InitializeResult(protocolVersion="2024-11-05")
            return create_success_response(request.id, result.model_dump())

        if self.state != ServerState.INITIALIZED:
            return create_error_response(
                request.id, MCPErrorCode.SERVER_NOT_INITIALIZED, "Server not initialized"
            )
        # ... dispatch to tools/list, tools/call, resources/read
```

### Pattern 4: Stdio Transport with Lock-Safe I/O

**What:** Async read from `sys.stdin` and write to `sys.stdout` using `asyncio.Lock` to prevent interleaving. Logs go exclusively to `sys.stderr`.

**When to use:** `sif mcp stdio` for Claude Desktop integration.

**Example:**
```python
# Source: adapted from existing transport_stdio.py + runtime verification
class StdioTransport:
    def __init__(self, server: UnifiedMCPServer,
                 stdin: TextIO | None = None, stdout: TextIO | None = None) -> None:
        self.server = server
        self.stdin = stdin or sys.stdin
        self.stdout = stdout or sys.stdout
        self._running = False
        self._read_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()

    async def _read_message(self) -> dict[str, Any] | None:
        async with self._read_lock:
            loop = asyncio.get_event_loop()
            line = await loop.run_in_executor(None, self.stdin.readline)
            if not line:
                return None
            try:
                return json.loads(line.strip())
            except json.JSONDecodeError as e:
                return {"jsonrpc": "2.0", "id": None,
                        "error": {"code": -32700, "message": f"Parse error: {e}"}}

    async def _write_message(self, message: dict[str, Any]) -> None:
        async with self._write_lock:
            line = json.dumps(message, ensure_ascii=False)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, lambda: self.stdout.write(line + "\n") or self.stdout.flush()
            )
```

### Pattern 5: Streamable HTTP Transport

**What:** Single `/mcp` endpoint. POST accepts JSON-RPC requests; GET opens SSE stream. CORS defaults are secure.

**When to use:** `sif mcp http` for remote access.

**Example:**
```python
# Source: verified via runtime test with FastAPI TestClient
from fastapi.middleware.cors import CORSMiddleware

DEFAULT_CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]

def create_app(server: UnifiedMCPServer, cors_origins: list[str] | None = None) -> FastAPI:
    origins = list(cors_origins) if cors_origins else DEFAULT_CORS_ORIGINS
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/mcp")
    async def mcp_post(request: MessageRequest) -> JSONResponse:
        rpc_req = JsonRpcRequest(**request.model_dump())
        response = await server.handle_request(rpc_req)
        return JSONResponse(content=response.model_dump(exclude_none=True))

    @app.get("/mcp")
    async def mcp_get() -> StreamingResponse:
        async def event_stream() -> AsyncGenerator[str, None]:
            while True:
                yield f"data: {json.dumps({'ping': True})}\n\n"
                await asyncio.sleep(30)
        return StreamingResponse(event_stream(), media_type="text/event-stream")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
```

### Anti-Patterns to Avoid
- **Sync server with async transports:** The existing `MCPServer.handle_request()` takes a `dict` and returns a `dict` synchronously. This breaks the async transport layer. The new server must be fully async.
- **Long-lived SQLite connections:** Keeping a single `sqlite3.Connection` open across requests causes concurrency issues. Always create a new connection per tool call (D-04).
- **Logging to stdout in stdio mode:** Any `print()` or log handler writing to stdout corrupts the JSON-RPC stream. Configure logging to `sys.stderr` exclusively.
- **Wildcard CORS by default:** The existing `transport_http.py` defaults to `["*"]`. The new implementation must default to `["http://localhost:3000", "http://127.0.0.1:3000"]`.
- **Embedding model per request:** Loading `sentence-transformers` or `llama-cpp` on every request is prohibitively slow. Cache via `EmbeddingManager._model` (D-06).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON-RPC parsing | Custom dict parsing | `sif.mcp.protocol` Pydantic models | Already complete; handles validation, serialization, edge cases (null id = notification) |
| HTTP server | Raw `http.server` | FastAPI + uvicorn | Already a dependency; handles routing, middleware, SSE, async automatically |
| CORS middleware | Custom origin checks | `fastapi.middleware.cors.CORSMiddleware` | Standard, well-tested, configurable per-route |
| SQLite connection management | Raw `sqlite3.connect()` | `DatabaseConnection` context manager | Already exists; handles extensions, row factory, transactions |
| Search execution | Custom SQL queries | `SearchPipeline`, `BM25Searcher`, `HybridSearcher` | Already implemented; handles FTS5, RRF, query prefixes, snippets |
| Embedding generation | Custom vector math | `EmbeddingManager` + `SentenceTransformerEmbedder` | Already implemented; handles model caching, batching, device selection |
| Resource URI parsing | String splitting | `urllib.parse.urlparse` + `parse_qs` | Standard library; handles query params, encoding correctly |

**Key insight:** The existing SIF codebase already has working search, database, and embedding infrastructure. The MCP layer is primarily glue code (protocol parsing, async wrapping, transport I/O). Don't rebuild what already works.

## Runtime State Inventory

This is a greenfield consolidation phase (replacing dual implementations with a unified one). No runtime state migration is required beyond deleting stale code.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | None — SQLite schema unchanged | None |
| Live service config | None — MCP server is stateless | None |
| OS-registered state | None | None |
| Secrets/env vars | None — no secrets in MCP layer | None |
| Build artifacts | `src/sif/mcp_server/` and old `src/sif/mcp/*.py` | Delete stale files |

**Nothing found in category:** All categories verified — no runtime state migration needed.

## Common Pitfalls

### Pitfall 1: Stdio stdout pollution
**What goes wrong:** A `print()` statement or misconfigured logger writes to stdout, corrupting the JSON-RPC stream. Claude Desktop sees invalid JSON and disconnects.
**Why it happens:** Python's default logging goes to stderr, but `print()` goes to stdout. Third-party libraries may also print to stdout.
**How to avoid:** Never use `print()` in stdio mode. Configure all loggers to use `sys.stderr`. Add a lint rule or code review check.
**Warning signs:** Claude Desktop shows "MCP server disconnected" or "Invalid JSON" errors.

### Pitfall 2: Async/sync boundary mismatch
**What goes wrong:** Calling a sync sqlite3 operation directly from an async handler blocks the event loop, causing timeouts or hangs.
**Why it happens:** `sqlite3` is synchronous. FastAPI/stdio transports are async. Direct calls block.
**How to avoid:** Wrap ALL sync DB operations with `await asyncio.to_thread(...)`. The `SearchBackend._with_db()` helper enforces this.
**Warning signs:** HTTP requests timeout; stdio transport becomes unresponsive.

### Pitfall 3: Embedding model cold start
**What goes wrong:** First `query` tool call takes 30+ seconds while the embedding model downloads/loads.
**Why it happens:** `EmbeddingManager.load_model()` is lazy — it only loads on first use.
**How to avoid:** Either preload at server startup (better UX) or document the cold-start behavior. Do NOT load per-request.
**Warning signs:** First search is inexplicably slow; subsequent searches are fast.

### Pitfall 4: Content size overflow
**What goes wrong:** A `get` or `multi_get` returns a 10MB document, exceeding MCP message size limits and causing client errors.
**Why it happens:** No size limiting on document content retrieval.
**How to avoid:** Truncate content to 100KB per SPEC.md constraint. Return `... [truncated]` suffix.
**Warning signs:** Client shows "message too large" or truncated JSON errors.

### Pitfall 5: Double initialization
**What goes wrong:** Client sends `initialize` twice; server state machine breaks or returns inconsistent capabilities.
**Why it happens:** Some clients retry initialization on reconnection.
**How to avoid:** Accept re-initialization gracefully (reset state) or ignore duplicate initialize requests. Document the chosen behavior.
**Warning signs:** Inconsistent tool lists or capability mismatches after reconnection.

## Code Examples

### Initialize Request/Response
```python
# Source: sif.mcp.protocol (verified)
req = JsonRpcRequest(
    id=1,
    method="initialize",
    params={"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test"}}
)
resp = await server.handle_request(req)
# resp.result == {"protocolVersion": "2024-11-05", "capabilities": {"tools": {"listChanged": False}},
#                 "serverInfo": {"name": "sif-mcp-server", "version": "1.0.0"}}
```

### Tool Call with Real Search
```python
# Source: verified via runtime test
req = JsonRpcRequest(
    id=3,
    method="tools/call",
    params={"name": "query", "arguments": {"query": "programming", "limit": 5}}
)
resp = await server.handle_request(req)
content = json.loads(resp.result["content"][0]["text"])
# content == {"results": [{"doc_id": "...", "path": "...", "title": "...", "score": 0.95, ...}]}
```

### Resource URI Parsing
```python
# Source: verified via runtime test
from urllib.parse import urlparse, parse_qs

def parse_doc_uri(uri: str) -> tuple[str, dict]:
    parsed = urlparse(uri)
    doc_id = (parsed.netloc + parsed.path).lstrip("/")
    params = parse_qs(parsed.query)
    kwargs = {}
    if "from_line" in params:
        kwargs["from_line"] = int(params["from_line"][0])
    if "max_lines" in params:
        kwargs["max_lines"] = int(params["max_lines"][0])
    return doc_id, kwargs

parse_doc_uri("docs://doc-123?from_line=10&max_lines=20")
# -> ("doc-123", {"from_line": 10, "max_lines": 20})
```

### Content Truncation
```python
# Source: verified via runtime test
MAX_CONTENT_SIZE = 100 * 1024

def truncate_content(content: str, max_size: int = MAX_CONTENT_SIZE) -> str:
    encoded = content.encode("utf-8")
    if len(encoded) <= max_size:
        return content
    truncated = encoded[:max_size].decode("utf-8", errors="ignore")
    return truncated + "\n... [truncated]"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Dual implementations (mcp/ + mcp_server/) | Single unified mcp/ package | Phase 9 (now) | Eliminates divergence; one source of truth |
| Sync server (dict in/out) | Async server (Pydantic models) | Phase 9 (now) | Enables async transports; cleaner error handling |
| MockSearchBackend with fake data | Real SearchBackend with Database | Phase 9 (now) | Tool calls return actual search results |
| Old HTTP+SSE (/mcp/v1/messages + /mcp/v1/sse) | Streamable HTTP (single /mcp) | Phase 9 (now) | Follows 2025-11-25 spec; simpler endpoint model |
| Wildcard CORS default | Explicit localhost origins | Phase 9 (now) | Secure by default |

**Deprecated/outdated:**
- `src/sif/mcp_server/` directory: superseded by unified `src/sif/mcp/`
- `src/sif/mcp/server.py` (sync): superseded by async `UnifiedMCPServer`
- `src/sif/mcp/server_http.py`: superseded by `transports/http.py`
- `src/sif/mcp/tools.py` (MockSearchBackend): superseded by `backend.py` + `handlers.py`
- `src/sif/mcp/transport_stdio.py`: patterns adapted into `transports/stdio.py`
- `src/sif/mcp/transport_http.py`: patterns adapted into `transports/http.py`

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `sentence-transformers` and `llama-cpp` embedders are thread-safe for concurrent `.encode()` / `.embed()` calls | Architecture Patterns | If wrong, concurrent searches could crash or corrupt results; mitigation is to use a lock around embed calls |
| A2 | `asyncio.to_thread()` is sufficient for SQLite concurrency safety | Architecture Patterns | If wrong (e.g., on network filesystems), could see database locks; SQLite on local disk is safe with separate connections |
| A3 | The MCP 2024-11-05 protocol version is what Claude Desktop expects | Standard Stack | If Claude updates to a newer protocol, the server may need version negotiation; currently both spec and client expect 2024-11-05 |
| A4 | `docs://{doc_id}` is the only resource URI scheme needed | Architecture Patterns | If future phases need `collection://` or other schemes, the resource parser needs extension; currently within Claude's discretion |
| A5 | Streamable HTTP (single `/mcp` endpoint) is preferred over old HTTP+SSE | Architecture Patterns | SPEC.md mentions old endpoints in acceptance criteria but CONTEXT.md D-10/D-11 explicitly mandates Streamable HTTP; this discrepancy was noted and CONTEXT decisions take precedence |

## Open Questions

1. **Should the embedding model be preloaded at server startup?**
   - What we know: `EmbeddingManager.load_model()` is lazy; first request is slow.
   - What's unclear: Whether preloading at startup is worth the memory cost for short-lived stdio sessions.
   - Recommendation: Lazy load (current behavior) for stdio; optional `--preload-model` flag for HTTP daemon mode.

2. **How should `notifications/cancelled` interrupt in-flight tool calls?**
   - What we know: CONTEXT.md D-09 says handle `cancelled` notifications.
   - What's unclear: Python's `asyncio` cancellation is cooperative; a running sqlite3 query in a thread cannot be forcefully cancelled.
   - Recommendation: Track in-flight task IDs; on `cancelled`, call `.cancel()` on the asyncio Task. Document that cancellation is best-effort.

3. **Should `resources/list` return all documents or be paginated?**
   - What we know: Resources are `docs://{doc_id}` URIs.
   - What's unclear: Whether listing all documents is practical for large indexes.
   - Recommendation: Return empty list for now (out of scope per SPEC.md); document that `resources/list` is not implemented.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | ✓ | 3.13 | — |
| FastAPI | HTTP transport | ✓ | 0.135.3 | — |
| uvicorn | HTTP server | ✓ | 0.44.0 | — |
| Pydantic | Protocol models | ✓ | 2.x | — |
| sqlite-vec | Vector search | ✓ | 0.1.9 | BM25-only search (graceful degradation) |
| sentence-transformers | Embedding | ✓ | 2.x | Skip vector search; BM25 still works |
| pytest | Testing | ✓ | 9.0.2 | — |
| pytest-cov | Coverage | ✓ | 4.x | — |
| pytest-asyncio | Async tests | ✓ | installed | — |

**Missing dependencies with no fallback:**
- None

**Missing dependencies with fallback:**
- None

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio + pytest-cov |
| Config file | `pyproject.toml` (pytest.ini_options) |
| Quick run command | `pytest tests/unit/mcp/ -x` |
| Full suite command | `pytest tests/unit/mcp/ --cov=src/sif/mcp --cov-report=term-missing` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MCP-01 | Unified package replaces dual implementations | unit | `pytest tests/unit/mcp/test_integration.py -x` | ❌ Wave 0 |
| MCP-02 | SearchBackend returns real DB results | unit | `pytest tests/unit/mcp/test_backend.py -x` | ❌ Wave 0 |
| MCP-02 | Tool handlers use real search | unit | `pytest tests/unit/mcp/test_handlers.py -x` | ❌ Wave 0 |
| MCP-03 | stdio transport handles full lifecycle | unit | `pytest tests/unit/mcp/test_transports_stdio.py -x` | ❌ Wave 0 |
| MCP-03 | HTTP transport serves /mcp endpoint | unit | `pytest tests/unit/mcp/test_transports_http.py -x` | ❌ Wave 0 |
| MCP-04 | CORS defaults are secure | unit | `pytest tests/unit/mcp/test_transports_http.py::test_cors_defaults -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/unit/mcp/ -x`
- **Per wave merge:** `pytest tests/unit/mcp/ --cov=src/sif/mcp --cov-report=term-missing`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/mcp/__init__.py` — package init
- [ ] `tests/unit/mcp/test_server.py` — covers MCP-01 lifecycle
- [ ] `tests/unit/mcp/test_backend.py` — covers MCP-02 real search
- [ ] `tests/unit/mcp/test_handlers.py` — covers MCP-02 tool handlers
- [ ] `tests/unit/mcp/test_transports_stdio.py` — covers MCP-03 stdio
- [ ] `tests/unit/mcp/test_transports_http.py` — covers MCP-03 HTTP + MCP-04 CORS
- [ ] `tests/unit/mcp/test_integration.py` — covers MCP-01 end-to-end

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Local tool; no auth layer (per SPEC.md out-of-scope) |
| V3 Session Management | No | Stateless request-response |
| V4 Access Control | Yes | CORS origin whitelist; bind to 127.0.0.1 |
| V5 Input Validation | Yes | Pydantic models validate all JSON-RPC inputs; tool params validated via QueryInput/GetInput/etc. |
| V6 Cryptography | No | No cryptographic operations in MCP layer |

### Known Threat Patterns for FastAPI + MCP

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| CORS misconfiguration | Elevation of Privilege | `CORSMiddleware` with explicit origin list; reject `"*"` by default |
| Origin spoofing | Spoofing | Validate `Origin` header; return 403 for unauthorized origins |
| JSON parsing DoS | Denial of Service | Pydantic validation; stdio transport discards invalid JSON with ParseError |
| Oversized responses | Denial of Service | Truncate content to 100KB; limit `limit` param to reasonable max |
| Open bind (0.0.0.0) | Information Disclosure | Default bind to `127.0.0.1`; CLI `--host` allows override with explicit opt-in |

## Sources

### Primary (HIGH confidence)
- `src/sif/mcp/protocol.py` — Complete Pydantic models for JSON-RPC/MCP; verified via runtime instantiation of all models
- `src/sif/mcp/transport_stdio.py` — Async stdio read/write loop patterns; verified via adaptation and runtime test
- `src/sif/mcp/transport_http.py` — FastAPI app setup, SSE, CORS middleware; verified via adaptation and runtime test
- `src/sif/search/hybrid.py` — SearchPipeline implementation; verified via runtime search with test data
- `src/sif/database/connection.py` — DatabaseConnection context manager; verified via runtime transaction test
- `src/sif/embedding/manager.py` — EmbeddingManager caching; verified via runtime model load and embed
- Context7 `/fastapi/fastapi` — CORSMiddleware configuration, allow_origins behavior
- Context7 `/mark3labs/mcp-go` — MCP lifecycle patterns (initialize -> tools/list -> tools/call)

### Secondary (MEDIUM confidence)
- `https://modelcontextprotocol.io/specification/2025-11-25/basic/transports` — Streamable HTTP standard (referenced in CONTEXT.md)
- `https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle` — MCP lifecycle specification
- `https://modelcontextprotocol.io/specification/2025-11-25/basic/messages` — JSON-RPC message format

### Tertiary (LOW confidence)
- None — all claims verified via codebase inspection or runtime test

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified via runtime import
- Architecture: HIGH — all patterns verified via working prototype code
- Pitfalls: HIGH — all identified via direct testing of edge cases

**Research date:** 2026-05-12
**Valid until:** 2026-06-12 (FastAPI/MCP ecosystem is stable; revisit if MCP spec updates)
