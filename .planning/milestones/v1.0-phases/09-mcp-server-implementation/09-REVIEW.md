---
phase: 09-mcp-server-implementation
reviewed: 2026-05-12T15:45:00Z
depth: deep
files_reviewed: 9
files_reviewed_list:
  - src/sif/mcp/__init__.py
  - src/sif/mcp/backend.py
  - src/sif/mcp/handlers.py
  - src/sif/mcp/protocol.py
  - src/sif/mcp/server.py
  - src/sif/mcp/transports/http.py
  - src/sif/mcp/transports/stdio.py
  - src/sif/mcp/cli.py
  - src/sif/cli/commands/mcp.py
findings:
  critical: 3
  warning: 7
  info: 7
  total: 17
status: issues_found
---

# Phase 09: Code Review Report

**Reviewed:** 2026-05-12T15:45:00Z
**Depth:** deep
**Files Reviewed:** 9
**Status:** issues_found

## Summary

This review covers the Phase 9 MCP server implementation at deep depth, including cross-file analysis of the transport layer, protocol models, tool handlers, backend search operations, and CLI integration. The implementation provides a functional MCP server over stdio and HTTP transports with a SearchBackend wrapping SQLite operations.

Three critical issues were found: (1) the `query` tool permanently disables vector search despite advertising hybrid search, (2) invalid collection filters silently broaden to search all collections instead of returning empty results, and (3) the HTTP transport's session store grows without bound, creating a memory exhaustion vector. Seven warnings cover truncation bugs, missing input validation, malformed annotations, and incomplete state management. Seven info-level items note deprecated APIs, minor semantic issues, and model inconsistencies.

All findings are backed by traced execution paths and edge-case verification.

---

## Critical Issues

### CR-01: Vector Search Permanently Disabled — Tool Advertises Hybrid but Delivers BM25-Only

**File:** `src/sif/mcp/backend.py:67-71`
**Issue:** `SearchBackend.hybrid_search()` hardcodes `embedder=None` when constructing `SearchPipeline`. The `HybridSearcher.search()` branch for vector search is skipped entirely when `embedder is None`, causing a silent fallback to BM25-only results. The `QueryToolHandler` description explicitly advertises "vector semantic search" and "reranking," but neither is ever performed. This contradicts the project's own convention documented in `CLAUDE.md`: "vector search should fail fast instead of silently falling back."

**Fix:**
```python
# Option A: Create/embed an embedder from settings
from sif.embedding.factory import EmbeddingModelFactory

class SearchBackend:
    def __init__(self, db_path: str, settings: Settings | None = None) -> None:
        self.db_path = db_path
        self.settings = settings or get_settings()
        self._embedder = EmbeddingModelFactory.create(self.settings.model_name)

    async def hybrid_search(...):
        def _search(conn: Any) -> list[SearchResult]:
            ...
            pipeline = SearchPipeline(
                conn,
                embedder=self._embedder,
                embedding_dim=self.settings.embedding_dim,
            )
            ...
```

---

### CR-02: All-Invalid Collection Names Search All Collections

**File:** `src/sif/mcp/backend.py:62-66`
**Issue:** When the caller specifies `collections` and none of the names exist, `options.collection_ids` is set to `[]` (empty list). In the search layer, `collection_ids=[]` is treated as "search all collections" rather than "search no collections." The caller asked for a specific subset and should receive empty results, not a broader search across everything. The same bug triggers when `collections=[]` is passed explicitly.

**Fix:**
```python
# backend.py lines 62-66
if collections:
    repo = CollectionRepository(conn)
    matched = [
        c.id for c in (repo.get_by_name(n) for n in collections) if c
    ]
    if not matched:
        # All requested collections are invalid — return empty results
        return []
    options.collection_ids = matched
```

---

### CR-03: HTTP Session Store Grows Unbounded — Memory Exhaustion Vector

**File:** `src/sif/mcp/transports/http.py:41-56`
**Issue:** The global `_sessions: dict[str, Any] = {}` has no expiration, cleanup, or size limit. Every request without a valid `MCP-Session-Id` header (including health checks, CORS preflight, invalid JSON payloads, and SSE connections) creates a new UUID key and stores an empty dict. Over time this dict grows without bound, consuming memory. An attacker can exhaust memory by sending a high volume of requests without a session header.

**Fix:**
```python
import time
from collections import OrderedDict

_sessions: OrderedDict[str, dict[str, Any]] = OrderedDict()
SESSION_MAX_AGE = 3600  # 1 hour
SESSION_MAX_COUNT = 10000

def _get_session_id(request_headers: dict[str, str]) -> str:
    session_id = request_headers.get("mcp-session-id")
    now = time.time()
    # Expire old sessions
    while _sessions and len(_sessions) > SESSION_MAX_COUNT:
        _sessions.popitem(last=False)
    if session_id and session_id in _sessions:
        _sessions[session_id]["last_accessed"] = now
        return session_id
    new_id = _generate_session_id()
    _sessions[new_id] = {"created": now, "last_accessed": now}
    return new_id
```

---

## Warnings

### WR-01: `_truncate_content` Exceeds `max_size` by Suffix Length

**File:** `src/sif/mcp/backend.py:20-26`
**Issue:** The function truncates to `max_size` bytes, then appends `\n... [truncated]` (16 bytes). The result can exceed `max_size` by up to 16 bytes. For a 100KB limit, the result is 100KB + 16 bytes.

**Fix:**
```python
def _truncate_content(content: str, max_size: int = 100 * 1024) -> str:
    """Truncate content to max_size bytes."""
    suffix = "\n... [truncated]"
    encoded = content.encode("utf-8")
    if len(encoded) <= max_size:
        return content
    truncated = encoded[: max_size - len(suffix.encode("utf-8"))].decode("utf-8", errors="ignore")
    return truncated + suffix
```

---

### WR-02: `get_document` Truncates Before Line Slicing

**File:** `src/sif/mcp/backend.py:107-116`
**Issue:** `_truncate_content(doc.content)` is called before line slicing. For documents larger than 100KB, the truncation removes roughly half the content, and subsequent `from_line` values refer to the truncated content rather than the original. A caller requesting line 5000 of a 200KB document will receive empty content because line 5000 no longer exists after truncation.

**Fix:** Apply line slicing to the original content, then truncate the sliced result:
```python
def _get(conn: Any) -> Document | None:
    ...
    content = doc.content  # Do NOT truncate yet
    line_start: int | None = None
    line_end: int | None = None
    if from_line is not None:
        lines = content.split("\n")
        start = max(0, from_line - 1)
        end = len(lines) if max_lines is None else start + max_lines
        content = "\n".join(lines[start:end])
        line_start = start + 1
        line_end = start + len(content.split("\n"))
    content = _truncate_content(content)
    return Document(...)
```

---

### WR-03: No Input Validation for Numeric Parameters

**File:** `src/sif/mcp/backend.py:46-52,88-93,129-133`
**Issue:** `limit`, `min_score`, `from_line`, `max_lines`, and `max_bytes` accept negative values and produce unexpected results:
- `max_lines=-1` on a 4-line document returns 3 lines (Python slice semantics).
- `max_bytes=0` is treated as "use default" (`100 * 1024`) instead of "zero bytes."
- `from_line=-5` is silently clamped to 1.
- `from_line` beyond content length returns empty string with misleading `line_start=line_end=from_line`.

**Fix:** Add validation at the backend entry points or in Pydantic input models:
```python
# In protocol.py QueryInput
limit: int = Field(default=10, ge=1)
min_score: float = Field(default=0.0, ge=0.0)

# In protocol.py GetInput
from_line: Optional[int] = Field(default=None, ge=1)
max_lines: Optional[int] = Field(default=None, ge=1)

# In protocol.py MultiGetInput
max_bytes: Optional[int] = Field(default=None, ge=0)
```

---

### WR-04: Malformed Type Annotation with `noqa` Inside

**File:** `src/sif/mcp/handlers.py:212`
**Issue:** The line reads:
```python
def create_default_tools(backend: SearchBackend) -> list[ToolHandler]:  # noqa: ARG001 -> list[ToolHandler]:
```
The `# noqa: ARG001 -> list[ToolHandler]:` comment contains text that looks like a second return type annotation. While Python ignores comments, this is confusing to readers and may break tools that strip comments to parse annotations (e.g., some type checkers or documentation generators).

**Fix:**
```python
def create_default_tools(backend: SearchBackend) -> list[ToolHandler]:  # noqa: ARG001
```

---

### WR-05: Server State Machine Incomplete — `SHUTDOWN` Never Used

**File:** `src/sif/mcp/server.py:32-37`
**Issue:** `ServerState` defines `SHUTDOWN`, but `MCPServer` has no method to transition to it, and no code checks for it. The state machine is incomplete. A client that sends a shutdown notification or expects graceful termination will find the server still accepting requests.

**Fix:** Add shutdown handling:
```python
class MCPServer:
    async def handle_request(self, request: JsonRpcRequest) -> JsonRpcResponse:
        if self.state == ServerState.SHUTDOWN:
            return create_error_response(
                request.id,
                MCPErrorCode.INTERNAL_ERROR,
                "Server is shutting down",
            )
        ...

    async def handle_notification(self, notification: JsonRpcNotification) -> None:
        if notification.method == "notifications/initialized":
            ...
        elif notification.method == "notifications/shutdown":
            self.state = ServerState.SHUTDOWN
```

---

### WR-06: Double CORS Validation Is Redundant

**File:** `src/sif/mcp/transports/http.py:147-163`
**Issue:** `CORSMiddleware` is added with `allow_origins=origins`, and a custom `validate_origin` middleware performs the same check. The duplication adds complexity and risk of divergence. If `origins` is modified after `CORSMiddleware` is added but before `validate_origin` runs, they could disagree.

**Fix:** Remove the custom `validate_origin` middleware and rely solely on `CORSMiddleware`, or remove `CORSMiddleware` and handle CORS manually (including preflight OPTIONS):
```python
# Option A: Remove custom middleware, keep CORSMiddleware
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Remove validate_origin middleware
```

---

### WR-07: `mcp_daemon_cmd` Is a Stub

**File:** `src/sif/cli/commands/mcp.py:82-99`
**Issue:** The `mcp_daemon_cmd` accepts `--pid-file`, `--log-file`, and `--stop` flags but ignores the first two and makes `--stop` a no-op (it just prints messages). The command claims to run as a daemon but does not daemonize, write a PID file, or support stopping.

**Fix:** Either implement daemon functionality or remove the command until it is implemented:
```python
@mcp_group.command("daemon")
@click.option("--host", "-h", default="127.0.0.1")
@click.option("--port", "-p", type=int, default=3000)
@click.option("--pid-file", help="PID file path")
@click.option("--log-file", help="Log file path")
@click.option("--stop", is_flag=True, help="Stop the daemon")
@click.pass_context
def mcp_daemon_cmd(...) -> None:
    """Run MCP server as a daemon."""
    raise click.ClickException(
        "Daemon mode is not yet implemented. Use 'mcp http' instead."
    )
```

---

## Info

### IN-01: Deprecated `asyncio.get_event_loop()` Usage

**File:** `src/sif/mcp/transports/stdio.py:45,71`
**Issue:** `asyncio.get_event_loop()` is deprecated in Python 3.10+. Should use `asyncio.get_running_loop()` instead.

**Fix:**
```python
loop = asyncio.get_running_loop()
```

---

### IN-02: SSE Events Lack Event Type

**File:** `src/sif/mcp/transports/http.py:122`
**Issue:** The SSE generator yields `data: {json}\n\n` without an `event:` field. Per SSE spec, the default event type is `message`, not `ping`. Clients expecting `event: ping` will not match.

**Fix:**
```python
yield f"event: ping\ndata: {json.dumps({'ping': True})}\n\n"
```

---

### IN-03: `get_status` Uses Raw SQL Instead of Repository

**File:** `src/sif/mcp/backend.py:173-188`
**Issue:** `get_status` executes raw `SELECT COUNT(*) FROM documents WHERE collection_id = ?` queries directly, bypassing the `DocumentRepository`. This breaks the repository pattern abstraction established in the codebase.

**Fix:** Add a `count_by_collection()` method to `DocumentRepository` and use it:
```python
# In DocumentRepository:
def count_by_collection(self, collection_id: str) -> int:
    cursor = self.db.execute(
        "SELECT COUNT(*) FROM documents WHERE collection_id = ?",
        (collection_id,),
    )
    return cursor.fetchone()[0]

# In SearchBackend.get_status:
count = doc_repo.count_by_collection(coll.id)
```

---

### IN-04: Trailing Newline Causes Off-by-One in Line Count

**File:** `src/sif/mcp/backend.py:116`
**Issue:** For content ending with `\n`, `content.split("\n")` produces an extra empty string element. `line_end` is then 1 greater than the actual number of lines. For example, a 3-line file with trailing newline reports `line_end=4`.

**Fix:** Strip trailing newline before counting, or use `splitlines()`:
```python
line_end = start + len(content.split("\n"))
# If content ends with newline, subtract 1
if content.endswith("\n"):
    line_end -= 1
```

---

### IN-05: Protocol `Document` Model Lacks `collection_id`

**File:** `src/sif/mcp/protocol.py:204-214`
**Issue:** The MCP `Document` model does not include `collection_id`, while the core `Document` model does. When `get_document` finds a document by path across multiple collections, the caller cannot determine which collection it came from.

**Fix:** Add `collection_id` to the protocol model:
```python
class Document(BaseModel):
    doc_id: str
    path: str
    title: Optional[str] = None
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    collection_id: Optional[str] = None  # Added
```

---

### IN-06: Unused `backend` Parameter in `create_default_tools`

**File:** `src/sif/mcp/handlers.py:212`
**Issue:** `create_default_tools` accepts `backend: SearchBackend` but never uses it. The `# noqa: ARG001` suppresses the linter warning but does not fix the design issue. The parameter should either be removed or used (e.g., passed to tool handlers that need it).

**Fix:**
```python
def create_default_tools() -> list[ToolHandler]:
    """Create default tool handlers."""
    return [
        QueryToolHandler(),
        GetToolHandler(),
        MultiGetToolHandler(),
        StatusToolHandler(),
    ]
```

---

### IN-07: `JsonRpcResponse` Allows Both `result` and `error`

**File:** `src/sif/mcp/protocol.py:44-50`
**Issue:** The Pydantic model allows both `result` and `error` to be set simultaneously, which violates the JSON-RPC 2.0 spec (only one may be present). The helper functions (`create_success_response`, `create_error_response`) correctly set only one, but the model itself does not enforce mutual exclusivity.

**Fix:** Add a Pydantic validator:
```python
from pydantic import model_validator

class JsonRpcResponse(BaseModel):
    ...

    @model_validator(mode="after")
    def check_mutual_exclusivity(self) -> "JsonRpcResponse":
        if self.result is not None and self.error is not None:
            raise ValueError("result and error are mutually exclusive")
        return self
```

---

_Reviewed: 2026-05-12T15:45:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
