# Phase 22: MCP SDK v2 Modernization + Agent Packaging - Pattern Map

**Mapped:** 2026-11-16
**Files analyzed:** 41 (created/modified/deleted across the 7 plans) + 13 test modules
**Analogs found:** 36 with in-repo analogs / 41 (5 have no same-shape analog — flagged)
**Source snapshots:** HEAD `3a3c4ef` (dev); all analog paths verified git-tracked with `git ls-files`

## File Classification

`.` = repo root. Wave assignment from `22-RESEARCH.md` §Plan Decomposition.

| New/Modified File | Plan / Wave | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|-------------|------|-----------|----------------|---------------|
| `src/sif/mcp/app.py` (new) | 01/W1 | composition root (provider) | request-response + lifespan/event-driven | `src/sif/mcp/transports/http.py:149-209` (`create_app`) + `src/sif/mcp/watch_host.py:189-213` (`mcp_watch_lifespan`) | role+flow match |
| `src/sif/mcp/tools.py` (new) | 01/W1, 02/W2, 05/W4 | controller (tool surface) | request-response | `src/sif/mcp/handlers.py:48-316` + `src/sif/cli/commands/search.py:1122-1198` | exact role, flow match |
| `src/sif/mcp/backend.py` (mod) | 01/W1, 02/W2, 04/W3, 05/W4 | service | request-response, read-CRUD | itself (`backend.py:98-475`) + `src/sif/indexing/watcher.py:190-231` (lazy latch) | exact |
| `src/sif/mcp/protocol.py` (mod) | 01/W1, 02/W2, 05/W4 | model (schemas) | transform | itself — keep `196-437`, delete `18-194` + `439-461` | exact |
| `src/sif/mcp/watch_host.py` (mod) | 01/W1 | lifecycle provider | event-driven | itself (`watch_host.py:189-213`) | exact |
| `src/sif/mcp/__init__.py` (rewrite) | 01/W1 | package config | — | itself (current 14-line barrel) | exact |
| `src/sif/mcp/cli.py` (mod) | 01/W1, 03/W2 | provider (runners) | request-response | `src/sif/mcp/transports/http.py:242-264` (`run_http_server`) + `transports/stdio.py:128-150` | exact |
| `src/sif/cli/commands/mcp.py` (mod) | 01/W1, 03/W2 | route (Click command) | request-response, process lifecycle | `src/sif/cli/commands/watch.py:306-428` (daemon arm/stop) + itself | role match, flow match |
| `src/sif/utils/daemon.py` (mod) | 03/W2 | utility (process lifecycle) | event-driven / batch | itself (`daemon.py:43-333`) | exact |
| `src/sif/search/snippets.py` (mod) | 05/W4 | utility | transform | itself (`snippets.py:40-160`) | exact |
| `src/sif/search/hybrid.py` (mod) | 05/W4 | service | request-response | itself (`hybrid.py:486-508`) | exact |
| `src/sif/core/models.py` (mod) | 05/W4 | model (dataclass) | transform | itself (`models.py:294-339`) | exact |
| `src/sif/database/repositories.py` (mod) | 05/W4 | repository | read-CRUD / batch | itself (`repositories.py:221-331`) | exact |
| `pyproject.toml` (mod) | 01/W1 | config | — | itself (`pyproject.toml:28-61`) | exact |
| `uv.lock` (regen) | 01/W1 | generated config | — | no analog (tool output) | none |
| `.claude-plugin/plugin.json` (new) | 06/W5 | config (manifest) | — | `src/sif/mcp/claude_desktop_config.json` (JSON manifest shape only) | partial |
| `.claude-plugin/marketplace.json` (new) | 06/W5 | config (manifest) | — | none in repo | none |
| `.mcp.json` (new) | 06/W5 | config | — | `src/sif/mcp/claude_desktop_config.json` | exact shape |
| `skills/sif-search/SKILL.md` (new) | 06/W5 | doc asset (skill) | — | `.claude/skills/sif-search/SKILL.md` | exact (MCP retarget) |
| `skills/sif-get/SKILL.md` (new) | 06/W5 | doc asset (skill) | — | `.claude/skills/sif-get/SKILL.md` | exact (MCP retarget) |
| `skills/sif-cite/SKILL.md` (new) | 06/W5 | doc asset (skill) | — | `.claude/skills/sif-search/SKILL.md` frontmatter + discipline prose | role match |
| `server.json` (new) | 07/W6 | config (manifest) | — | none in repo (schema from research) | none |
| `scripts/publish_registry.py` (new) | 07/W6 | script / utility | request-response (HTTP) + file-I/O | `scripts/generate_config_ref.py:1-19,499-527` + `scripts/windows_smoke.py:27,140-141` | role match |
| `README.md` (mod) | 06/W5, 07/W6 | doc | — | itself (`README.md:1-2` marker) | exact |
| `docs/mcp-server.md` (rewrite) | 06/W5, 07/W6 | doc (hand-written) | — | itself; validated by `tests/test_docs.py` | exact |
| `src/sif/mcp/README.md` (rewrite) | 06/W5 | doc | — | itself | exact |
| `src/sif/mcp/server.py` (delete) | 01/W1 | shell | — | — | delete |
| `src/sif/mcp/handlers.py` (delete) | 01/W1 | shell | — | — | delete |
| `src/sif/mcp/transports/` (delete) | 01/W1 | shell | — | — | delete |
| `docs/cli-reference.md` (regen) | 07/W6 | generated doc | — | `Makefile:73-76` | generator-owned |
| `tests/unit/mcp/test_app.py` (new) | 01/W1 | test | — | `tests/unit/mcp/test_mcp_watch_host.py:39-80` | role match |
| `tests/unit/mcp/test_wire_transcripts.py` (new) | 01/W1 | test (integration) | — | `tests/unit/mcp/test_integration.py:25-82` | role match |
| `tests/unit/mcp/test_sdk_clients.py` (new) | 01/W1 | test | — | `test_integration.py` HTTP client battery | role match |
| `tests/unit/mcp/test_transport_security.py` (new) | 01/W1, 03/W2 | test (HTTP) | — | `tests/unit/mcp/test_transports_http.py:18-48` | role match |
| `tests/unit/mcp/test_stdout_purity.py` (new) | 01/W1, 04/W3 | test (subprocess) | — | `tests/unit/mcp/test_transports_stdio.py:1-70` | partial (new shape) |
| `tests/unit/mcp/test_tools.py` (new) | 02/W2 | test | — | `tests/unit/mcp/test_backend.py:29-90` | role match |
| `tests/unit/mcp/test_lazy_embedder.py` (new) | 04/W3 | test | — | `test_mcp_watch_host.py` patch-at-boundary style | role match |
| `tests/unit/mcp/test_citations.py` (new) | 05/W4 | test | — | `test_integration.py:34-73` (envelope fixture) | role match |
| `tests/unit/mcp/test_daemon.py` (new) | 03/W2 | test | — | `test_mcp_watch_host.py` real-tmp-DB helper | role match |
| `tests/unit/mcp/test_plugin.py` (new) | 06/W5 | test | — | `tests/test_docs.py` file-invariant style | role match |
| `tests/unit/mcp/test_registry_script.py` (new) | 07/W6 | test | — | `tests/unit/mcp` mocked-HTTP style | role match |
| `tests/unit/mcp/test_backend.py` (adapt) | 02/W2 | test | — | itself (1950 lines, keep) | exact |
| `tests/unit/mcp/test_mcp_watch_host.py` (keep) | — | test | — | itself (keep intact) | exact |
| `tests/unit/mcp/test_server.py`, `test_transports_http.py`, `test_transports_stdio.py` (delete) | 01/W1 | test shell | — | — | delete |

---

## Pattern Assignments

### `src/sif/mcp/app.py` (composition root, request-response + lifespan)

**Analogs:** `src/sif/mcp/transports/http.py` (FastAPI assembly), `src/sif/mcp/watch_host.py` (lifespan factory shape), `src/sif/mcp/transports/stdio.py` (construction order), + verified SDK snippet in `22-RESEARCH.md` §Code Examples.

**FastAPI assembly pattern to copy** (`transports/http.py:165-209`):
```python
    if FastAPI is None:
        raise ImportError("FastAPI is required for HTTP transport")

    origins = cors_origins if cors_origins is not None else DEFAULT_CORS_ORIGINS

    app = FastAPI(lifespan=lifespan)

    assert CORSMiddleware is not None
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    ...
    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
```
Keep `DEFAULT_CORS_ORIGINS` (`http.py:39-44`, no `*`) as the origin allowlist source (D-13), and `DEFAULT_HOST`/`DEFAULT_PORT` (`:45-46`).

**Lifespan factory shape to compose** (`watch_host.py:189-213`) — the SDK lifespan must nest **inside** the watch lifespan per D-18 (session manager enter → watcher start → yield → watcher stop → session exit):
```python
def mcp_watch_lifespan(db_path: str) -> Callable[[Any], Any]:
    @asynccontextmanager
    async def _lifespan(_app: Any) -> AsyncGenerator[None, None]:
        watch = start_embedded_watch(db_path)
        try:
            yield
        finally:
            stop_embedded_watch(watch)

    return _lifespan
```
The CR-01 comment at `:195-202` is load-bearing: never hand FastAPI an already-invoked context manager, and never hand `MCPServer` an invoked one either — build a new `@asynccontextmanager` that does `async with mcp.session_manager.run():` around the watch start/stop.

**Composition order to copy from `transports/stdio.py:128-145`** (backend first, then server, then watch teardown in `finally`):
```python
    watch = start_embedded_watch(db_path)
    try:
        backend = SearchBackend(db_path)
        server = MCPServer(backend)
        server.register_tools(create_default_tools())
        transport = StdioTransport(server)
        await transport.run()
    finally:
        if watch is not None:
            stop_embedded_watch(watch)
```
For the SDK root this becomes: build `SearchBackend` **inside** the lifespan (post-stdio fd diversion, research Pitfall 8), register the seven tools in fixed order (`query, get, multi_get, status, metadata, lex_search, vec_search`), register the `docs://` resource, then mount `streamable_http_app(streamable_http_path="/mcp", json_response=True, transport_security=security)` at `/` after `/health`.

**Transport security constant** (D-13; never `None`, research Pitfall 4):
```python
SECURITY = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=["127.0.0.1", "127.0.0.1:*", "localhost", "localhost:*", "[::1]", "[::1]:*"],
    allowed_origins=[...existing DEFAULT_CORS_ORIGINS...],
)
```
**`/health` Host guard** (C2): a narrow dependency/middleware comparing `Host` against the same allowlist; the current `validate_origin` middleware (`http.py:181-191`) is the shape to mirror, then delete it after the spoofed-header tests pass (D-14).

---

### `src/sif/mcp/tools.py` (controller, request-response)

**Analogs:** `src/sif/mcp/handlers.py` (descriptions, error semantics, JSON text), `src/sif/cli/commands/search.py:1122-1198` (pipeline wiring), `src/sif/utils/json_output.py` (`json_dumps_strict`).

**Tool registration / description-pattern** (`handlers.py:48-58` — copy the "reviewed constant description" discipline, and fix the rerank overclaim here):
```python
class QueryToolHandler(ToolHandler):
    name: ClassVar[str] = "query"
    description: ClassVar[str] = (
        "Hybrid search combining full-text search (BM25), "
        "vector semantic search, and reranking for the most relevant results."
    )
```
D-07: this description must be rewritten to state rerank is opt-in; every tool gets `ToolAnnotations(read_only_hint=True, open_world_hint=False)`.

**Explicit dual-channel builder** (D-05/D-10, research C7/C8 — mandatory for all seven):
```python
def _result(output: BaseModel, *, exclude_none: bool = False) -> CallToolResult:
    text = json_dumps_strict(output.model_dump(exclude_none=exclude_none), ensure_ascii=False)
    structured = output.model_dump(mode="json", by_alias=True, exclude_none=exclude_none)
    return CallToolResult(
        content=[TextContent(type="text", text=text)], structured_content=structured
    )
```
This reproduces exactly what handlers do today: compact text at `handlers.py:123-130`, and `exclude_none=True` only for metadata at `handlers.py:296-305`:
```python
        output = MetadataOutput(**discovery)
        return ToolsCallResult(
            content=[
                ToolContentItem(
                    type="text",
                    text=json_dumps_strict(
                        output.model_dump(exclude_none=True), ensure_ascii=False
                    ),
                ),
            ],
        )
```

**Expected-error → `ToolError`** (D-08). Today's tool-execution-error shape at `handlers.py:96-102` is the message source; the SDK version raises:
```python
        try:
            filter_node = None if input_data.filter is None else parse_filter(input_data.filter)
        except FilterValidationError as exc:
            return ToolsCallResult(
                content=[ToolContentItem(type="text", text=str(exc))],
                isError=True,
            )
```
Becomes `raise ToolError(str(exc))`, and `Document not found` (`handlers.py:162-166`) / unknown collection / vec-unavailable become `ToolError`s. Preserve the handler-side `QueryInput(**params)` coercion (D-08) — the SDK's arg model does not run SIF's validators.

**Argument constraints** (research-verified): `Annotated[int, Field(ge=1)] = 10`, `Annotated[int, Field(ge=0)] = 0`; mirror every field of `QueryInput` (`protocol.py:240-264`), `GetInput` (`:325-330`), `MultiGetInput` (`:339-343`), `MetadataInput` (`:401-416`) — the input models are the source of truth, and the tool signature is now the schema (delete the hand-written `input_schema` dicts at `handlers.py:56-83`).

**Resource (D-09)** — shape from `server.py:138-177` (`docs://`, `from_line`/`max_lines`, markdown/plain mime) converted to the SDK template:
```python
@mcp.resource(
    "docs://{doc_id}{?from_line,max_lines}",
    name="document",
    mime_type="text/markdown",
)
def read_doc(doc_id: str, from_line: int | None = None, max_lines: int | None = None) -> str: ...
```
Query variables require defaults (research Pitfall 11). Mime type is template-level; pick one and document (Open Q4).

---

### `src/sif/mcp/backend.py` (service, request-response)

**Analog:** itself + `src/sif/indexing/watcher.py:190-231` (one-attempt lazy latch) + `src/sif/embedding/manager.py:60-128`.

**Eager-construction block to replace** (`backend.py:145-177`): the constructor currently calls `EmbeddingModelFactory().create_model(...)` directly and swallows failures. Move that into `_ensure_embedder()`; keep the schema-open identity block (`:114-143`) exactly as-is.

**One-attempt latch to copy** (`watcher.py:216-231`):
```python
    def ensure_ready(self, on_event: Callable[[str], None] | None) -> bool:
        """Load the model once and validate its dimension (fail-soft)."""
        if self._attempted:
            return self._ready
        self._attempted = True
        try:
            ...
            manager = EmbeddingManager.from_settings(settings)
            manager.load_model()
```
Difference to honor: the watcher is single-threaded; the MCP backend serves concurrent requests, so add `threading.Lock` around construct + `load_model()` + `get_identity()` and latch failure (`_attempted`/`_ready`), per research Pitfall 10 / Pattern 3.

**Manager contracts** (`manager.py`): `load_model()` idempotent, not thread-safe (`:97-121`); `get_identity()` calls `load_model()` (`:225-230`) — only call it **after** `_ensure_embedder()` succeeds (Pitfall 9). `EmbeddingManager.from_settings` constructs the cache dir/DB — never call at import/`__init__` (`manager.py:60-90`).

**Fresh-connection per request** — keep unchanged (`backend.py:179-186`):
```python
    async def _run_in_db(self, callback: Callable[[Any], T]) -> T:
        def _run() -> T:
            with DatabaseConnection(self.db_path).transaction() as conn:
                return callback(conn)

        return await asyncio.to_thread(_run)
```

**Parity wiring to copy from CLI `query`** (`cli/commands/search.py:1148-1198`): hoist `QueryExpansion(embedding_manager=manager)`, the `partial(check_identity, current=identity, mode="search")` closure, `create_reranker(settings)` behind `rerank or settings.rerank_enabled` (zero-cost gate before construction), and `SmartSnippetExtractor(max_length=options.snippet_max_length)` (`SearchOptions.snippet_max_length` default 300, `core/models.py:367`). Construct `SearchPipeline(...)` **per request** inside `_run_in_db` (D-17).
```python
        current_identity = _current_identity(manager)
        identity_check: Callable[[sqlite3.Connection], IdentityCheck] | None = (
            partial(check_identity, current=current_identity, mode="search")
            if current_identity is not None
            else None
        )
        query_expander = QueryExpansion(embedding_manager=manager)

        reranker = None
        rerank_requested = rerank or settings.rerank_enabled
        if rerank_requested:
            try:
                reranker = create_reranker(settings)
```

**lex/vec direct-searcher recipes** — copy CLI shapes verbatim.
- BM25: `cli/commands/search.py:604-617` — `BM25Searcher(db.connection).search(query, options)` then exactly one `enrich_results(db.connection, results)`.
- Vector: `cli/commands/search.py:812-875` — identity check **before** `manager.embed_query(query)`, `VectorSearcher(db.connection, len(query_embedding))`, then one enrichment with `vectors_untrusted=True` when untrusted.

**Citation mapping** (D-11): extend the explicit field re-map at `backend.py:282-308` (`doc_id, path, title, content, score, highlights, metadata{rank, collection_name, vectors_stale, chunk_id, sequence, chunk_matches}`) with `snippet, content_hash, line_start, line_end`; the comment there ("an unlisted field is silently dropped") is the reason. `get_document` (`:363-407`) already computes a line window — populate `line_start=1/line_end=N` for a full read and the requested range for a ranged read; add `content_hash` from the batched checksum lookup.

---

### `src/sif/mcp/protocol.py` (model, transform)

**Analog:** itself. Delete exactly the JSON-RPC/wire half (`protocol.py:18-194`: `JsonRpcVersion` … `ToolsCallResult` and the notification models) plus helpers (`:439-461`), and keep `SearchResult` (`:201-211`), `Document` (`:213-223`), `CollectionInfo` (`:226-232`), all tool input/output models (`:240-436`) — including the frozen `MetadataOutput` (`:419-436`).

**Citation fields to add** (mirror existing field style, `protocol.py:201-223`):
```python
class SearchResult(BaseModel):
    doc_id: str
    path: str
    title: str | None = None
    content: str | None = None
    score: float
    highlights: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
```
Add `snippet`, `content_hash`, `line_start`, `line_end` with `None` defaults; `Document` gets `content_hash` (and already has `line_start`/`line_end`). Additive-only (D-12). The frozen camelCase alias notes at `:419-428` must not change.

---

### `src/sif/mcp/watch_host.py` (lifecycle provider, event-driven)

**Analog:** itself. Do not rewrite the start/stop internals; add a composition helper so `app.py` can nest `mcp.session_manager.run()` around the existing start/yield/stop. Keep `_MCP_WATCH_DEPTH = "bm25"` (`:46-48`), logger-only renderers (`:64-89`), serve-first reconcile (`:103-163`), and the D-14 teardown order in `stop_embedded_watch` (`:166-186`).

**Note for the planner:** `mcp_watch_lifespan` currently has no session-manager parameter. Either add an optional `session_manager` argument or add a sibling `sif_lifespan(db_path, mcp_server)` that wraps it; `test_mcp_watch_host.py`'s lifespan test must keep passing (15 tests intact per D-25).

---

### `src/sif/mcp/cli.py` (provider, request-response)

**Analog:** itself (9 lines) + `transports/http.py:242-264`.

Current:
```python
from sif.mcp.transports.http import run_http_server
from sif.mcp.transports.stdio import run_stdio_server_sync as run_stdio_server

__all__ = ["run_http_server", "run_stdio_server"]
```
New wrappers call `app.py` (`build_server`/`run_stdio`/`run_http`), keep the same names so `cli/commands/mcp.py` and `src/sif/mcp/README.md` imports stay valid, and add a `run_daemon`/`run_http_host` for plan 03. The lazy-import note at `transports/http.py:250-256` (uvicorn imported inside `run`) is the convention to copy.

---

### `src/sif/cli/commands/mcp.py` (route, request-response + process lifecycle)

**Analogs:** itself (stdio/http/daemon skeleton) + `src/sif/cli/commands/watch.py` daemon path.

**Click option shape to copy** (`mcp.py:70-106`): `--host/-h`, `--port/-p`, `--cors-origins multiple=True`, `_default_mcp_host()`/`_default_mcp_port()` ValidationError fallbacks (`:18-31`). Add `--allowed-hosts` as `multiple=True` (Open Q5) on both `http` and `daemon`.

**Daemon arm/stop pattern to copy** (`watch.py:345-405`), including Windows refusal and cleanup:
```python
    if not hasattr(os, "fork"):
        raise click.ClickException(
            "--detach requires POSIX fork support and is not available on Windows; "
            "run `sif watch` in the foreground instead."
        )
    log_path = _daemon_log_path(log_file)
    pid_file = daemon.pid_path_for(params.index_path)
    ...
    def arm() -> None:
        db = open_initialized_database_unmanaged(params.index_path, Database)
        ...  # schema + backend + write PID
        daemon.write_pid_file(pid_file, pid=os.getpid(), mode="mcp", depth="bm25")

    outcome = daemon.detach(log_path, arm)
    if outcome.daemon:
        try:
            run_http_host(...)          # bind happens AFTER arming (D-21)
        finally:
            daemon.remove_pid_file(pid_file)
```
Log default via `_daemon_log_path` (`watch.py:306-319`) with `user_log_dir("sif") / "mcp.log"` and eager `parent.mkdir` (needed before the fork's stdio redirect). `_run_stop` (`watch.py:408-428`) is the messaging template; it must call `stop_daemon(ci.pid_path_for_mcp(...), marker="mcp")` (or equivalent signature).

---

### `src/sif/utils/daemon.py` (utility, process lifecycle)

**Analog:** itself. Two surgical additions; do not touch detach/arming.

**Parallel PID path** — mirror `pid_path_for` (`daemon.py:88-95`) and the suffix constant (`:43`):
```python
_PID_SUFFIX = ".watch.pid"

def pid_path_for(db_path: str | Path) -> Path:
    resolved = Path(db_path).expanduser().resolve()
    return resolved.with_name(resolved.name + _PID_SUFFIX)
```
Add `_PID_SUFFIX_MCP = ".mcp.pid"` and `pid_path_for_mcp` (`resolved.name + _PID_SUFFIX_MCP`).

**Hardcoded marker to parameterize** — `_WATCH_MARKER = "watch"` (`:58`) is used at `corroborate_pid` return (`:217`):
```python
    return _identifies_sif_cli(result.stdout) and _WATCH_MARKER in result.stdout.split()
```
Change to a `marker: str = "watch"` keyword parameter (fail-closed default preserves watch behavior, C5), thread it through `stop_daemon` (`:299-333`), and map payload mode → marker (`"daemon" → "watch"`, `"mcp" → "mcp"`). `read_pid_file` (`:129-152`) already accepts any string `mode`/`depth`, so no payload-schema change.

---

### `src/sif/search/snippets.py` (utility, transform)

**Analog:** itself. `_build_window` already returns the inclusive `(start, end)` line indices (`snippets.py:100-117`) and `_render_window` renders them (`:153-160`) — the line-range reporting is a return-value change, not new scanning logic.

Current public entry (`:40-65`):
```python
    def extract(self, text: str, query_terms: list[str]) -> str:
        ...
        lines = self._split_lines(text)
        best_idx = self._best_line_index(lines, query_terms)
        if best_idx is None:
            return self._fallback_snippet(text)
        if len(lines[best_idx]) > self.max_length:
            return self._cut_long_line(lines[best_idx], query_terms)
        start, end = self._build_window(lines, best_idx)
        return self._render_window(lines, start, end)
```
Add a range-returning API (e.g. `extract_with_range(...) -> tuple[str, int, int]`) whose line numbers are 1-based document lines; keep `extract()` byte-identical for the CLI (D-11 "no extra content scan"; CLI JSON must not change). `_fallback_snippet` (`:196-206`) and `_cut_long_line` (`:162-178`) need defined ranges too.

---

### `src/sif/search/hybrid.py` (service, request-response)

**Analog:** itself. `_apply_snippets` (`hybrid.py:486-508`) is where line fields get assigned:
```python
    def _apply_snippets(self, results, parsed_query):
        if self.snippet_extractor is None:
            return results
        query_terms = parsed_query.lower().split()
        for result in results:
            if result.snippet is not None:
                continue
            text = result.content
            if not text:
                text = self.hybrid._get_document_content(result.document_id)  # noqa: SLF001
            if text:
                result.snippet = self.snippet_extractor.extract(text, query_terms)
        return results
```
Assign `result.line_start`/`result.line_end` from the new range API in the same pass (the content fetch is already transient). Leave `SearchPipeline` constructor/identity closure/`_paginate`/one-`enrich_results` contract untouched (`:231-309`, `:482-484`).

---

### `src/sif/core/models.py` (model, transform)

**Analog:** itself. Add `line_start: int | None = None` / `line_end: int | None = None` to `SearchResult` (`models.py:294-319`) — but **do not add them to `to_dict()`** (`:321-339`, the byte-identical CLI JSON contract, D-11 / deferred list). Existing fields document the pattern (defaulted, comment explains the contract):
```python
    # Chunk identity (D-02/D-03): the matched chunk's id and sequence number,
    # plus the count of pre-dedup vector rows collapsed into this row. All
    # defaulted so document-level rows (BM25) and every existing constructor
    # stay valid; they ride to_dict() into --json output and the MCP re-map.
    chunk_id: str | None = None
    sequence: int | None = None
    chunk_matches: int = 0
```
`to_dict()` must stay exactly as-is; the MCP boundary maps dataclass fields explicitly (see backend assignment above).

---

### `src/sif/database/repositories.py` (repository, read-CRUD / batch)

**Analog:** itself. Add one batched page lookup next to `get_checksum` (`repositories.py:327-331`):
```python
    def get_checksum(self, document_id: str) -> str | None:
        """Get document checksum."""
        cursor = self.db.execute("SELECT checksum FROM documents WHERE id = ?", (document_id,))
        row = cursor.fetchone()
        return row[0] if row else None
```
Batch variant must be one query (e.g. `WHERE id IN (...)` with chunked placeholders) returning `dict[str, str | None]`; `DocumentRepository.__init__` takes the connection (`:181-183`) and `_row_to_document` (`:360`) shows the row access convention. Keep it read-only; no schema change (research Runtime State Inventory).

---

### `pyproject.toml` / `uv.lock` (config)

**Analog:** `pyproject.toml:28-40` (`[project].dependencies`) and `:47-61` (extras). Add `"mcp>=2.3.0,<3"` to the dependencies list; keep `mcp = ["uvicorn>=0.20.0"]` and `http = ["uvicorn>=0.20.0"]` as deprecated aliases (D-03). `uv.lock` is regenerated, never hand-edited. Coverage gate lives at `[tool.coverage.report] fail_under = 90` (`pyproject.toml:222-225`).

---

### `.mcp.json` (config)

**Analog:** `src/sif/mcp/claude_desktop_config.json` — same `mcpServers` object shape:
```json
{
  "mcpServers": {
    "sif": {
      "command": "sif",
      "args": ["mcp", "stdio"],
      "env": { "SIF_DB_PATH": "/Users/forrest/.sif/index.sqlite" },
      "description": "SIF MCP Server for document search and retrieval",
      "disabled": false
    }
  }
}
```
For the plugin version: `command: "sif"`, `args: ["mcp", "stdio"]`, **no** hardcoded `SIF_DB_PATH` (the installed CLI resolves its own default), name `sif` (D-23). Verified not gitignored (`git check-ignore` exit 1).

---

### `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `server.json` (manifests)

**No in-repo analog** — schemas come from `22-RESEARCH.md` (plugin reference, marketplace reference, `server.json` 2025-12-11). Pattern rules to enforce in tests- plugin name and marketplace name are `sif`; plugin version mirrors `src/sif/_version.py` (`1.1.2`, `_version.py:3`).
- marketplace `source: "./"` **and** a non-empty `description` (C4).
- `server.json`: name `io.github.zhangtaolab/sif`, package `docsif`, transport stdio, version read from `_version.py`.
- Gate is `claude plugin validate --json .` (exit 0, `success:true`, zero `errors`); do not use `--strict` (Pitfall 12).

---

### `skills/sif-search`, `skills/sif-get`, `skills/sif-cite` (doc assets)

**Analog:** `.claude/skills/sif-search/SKILL.md` and `.claude/skills/sif-get/SKILL.md`. Copy the frontmatter shape (lines 1-7):
```markdown
---
name: sif-search
description: "Search documents in SIF index using BM25, vector, or hybrid search"
argument-hint: "<query> [--strategy query|search|vsearch] [--collection NAME] [--limit N] [--all]"
allowed-tools:
  - Bash(command:sif:*)
---
```
New MCP-first skills change `allowed-tools` to the MCP tool names (e.g. `mcp__sif__query`), keep the `<objective> / <process> / <example>` sections, and keep the **untrusted content** warning (both existing skills carry it — `sif-cite` needs it most). `sif-cite` adds the two-stage rule: `metadata` → filter discovery, `query` → discover, `get` → cite docid + line numbers, never cite a snippet alone, surface `vectors_stale`/`content_hash` caveats (D-23).

---

### `scripts/publish_registry.py` (script, HTTP + file I/O)

**Analogs:** `scripts/generate_config_ref.py` (script structure) + `scripts/windows_smoke.py` (version parse, refusal/exit style).

**Script skeleton** (`generate_config_ref.py:1-19,516-527`):
```python
#!/usr/bin/env python3
"""Generate configuration reference markdown from Pydantic Settings introspection."""

from __future__ import annotations

...
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

...

def main() -> int:
    ...
    sys.stderr.write(f"Generated {output_path}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```
**Version read without importing the package** (`windows_smoke.py:27,140-141`):
```python
_VERSION_FILE = PROJECT_ROOT / "src" / "sif" / "_version.py"

    namespace = runpy.run_path(str(_VERSION_FILE))
    return str(namespace["__version__"])
```
Use `runpy.run_path` (not `import sif`) so the preflight never pays an import side effect. Refusal/exit conventions from `windows_smoke.py:274-275` (`_emit(f"FAIL ...")`; return 1). `--check`/`--publish` as argparse flags; idempotency lookup must run **before** invoking `mcp-publisher` and print "already listed" + exit 0 (C6/D-24). Never store credentials.

**README marker to match** (`README.md:2`):
```markdown
<!-- mcp-name: io.github.zhangtaolab/sif -->
```

---

### `README.md`, `docs/mcp-server.md`, `src/sif/mcp/README.md` (docs)

**Analogs:** themselves. Do not hand-edit `docs/cli-reference.md` / `docs/configuration.md` — regenerate via `Makefile:73-76`:
```make
docs-generate:
	@echo "Regenerating CLI and configuration reference docs..."
	python scripts/generate_cli_ref.py
	python scripts/generate_config_ref.py
```
`docs/mcp-server.md` is hand-written and code-block-validated by `tests/test_docs.py`. Its `SKIP_COMMAND_PATTERNS` already includes `mcp http`, `mcp daemon`, `mcp stdio`, so new command examples will not execute. Rewrite the stale sections: Architecture (`docs/mcp-server.md:13-30`), Transport Types (`:30-78`, remove "daemon not yet implemented"), Available Tools (`:79-203`, four→seven), Security (`:337-359`, SDK transport security), Troubleshooting (`:360+`).

`src/sif/mcp/README.md` currently documents the **deleted** assembly (`MCPServer`+`register_tools`+`HTTPTransport`, "Four Search Tools"); rewrite to point at `docs/mcp-server.md` and the new `app.py` composition.

---

## Test File Patterns

### `tests/unit/mcp/test_app.py`, `test_transport_security.py`, `test_sdk_clients.py`, `test_wire_transcripts.py` (composition / HTTP)

**Analog:** `tests/unit/mcp/test_transports_http.py:18-48` fixtures + `test_mcp_watch_host.py:39-55` real-DB helper.

**Fixture trio to copy** (autouse global-state restore, mocked server, TestClient):
```python
@pytest.fixture(autouse=True)
def clear_http_sessions():
    """Restore the process-global session registry around every HTTP test."""
    http._sessions.clear()
    yield
    http._sessions.clear()


@pytest.fixture
def client(mock_server):
    """Create a FastAPI TestClient."""
    app = create_app(mock_server, sse_ping_interval=0.01, sse_max_events=1)
    return TestClient(app)
```
Replace the `MagicMock` server with the real SDK `MCPServer` from an app factory (one server per test — research Pitfall 3: `streamable_http_app()` must be called once; `httpx` ASGITransport does not run lifespan, so use `async with app.router.lifespan_context(app)` or `TestClient`).

**Real-schema helper to copy** (`test_mcp_watch_host.py:39-55`):
```python
def _make_db(db_path: Path, *, with_collection: bool) -> Path:
    root = db_path.parent / "notes"
    ...
    db = Database(db_path)
    try:
        db.init_schema()
        if with_collection:
            with db.connection:
                CollectionRepository(db.connection).create(Collection(name="notes", path=str(root)))
    finally:
        db.close()
    return root
```
Wire transcripts: raw JSON-RPC POSTs with `TestClient` (or `httpx` AsyncClient), asserting 2024-11-05 / 2025-06-18 / 2025-11-25 handshakes, and the 2026-07-28 stateless headers (`MCP-Protocol-Version`, `Mcp-Method`, `Mcp-Name`, `_meta`) — exact request shapes in `22-RESEARCH.md` §Code Examples §Era matrix.

### `tests/unit/mcp/test_tools.py`, `test_citations.py`, `test_lazy_embedder.py`, `test_backend.py` (unit)

**Analog:** `tests/unit/mcp/test_backend.py:29-90` (patch-at-module-boundary + MagicMock result shape) and `test_integration.py:25-73` (strict-JSON parse hook + frozen envelope).

**Backend fixture** (`test_backend.py:29-45`):
```python
@pytest.fixture
def backend(tmp_path: Path):
    """Create a SearchBackend with mocked settings."""
    with patch("sif.mcp.backend.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(embedding_dim=1024)
        return SearchBackend(str(tmp_path / "test.db"))
```
**MagicMock core-result shape** (`test_backend.py:69-90`) — extend with `snippet`, `line_start`, `line_end`, and a real `DocumentRepository`/checksum source for citation tests.

**Strict-JSON assertion hook** (`test_integration.py:25-27`) — reuse for "text parses as compact JSON, no NaN":
```python
def _reject_json_constant(token: str) -> None:
    """``json.loads`` parse_constant hook that refuses NaN/Infinity tokens."""
    raise AssertionError(f"non-standard JSON token: {token}")
```
**Frozen envelope fixture** (`test_integration.py:34-63`) — `_METADATA_ENVELOPE` is the deep-equality oracle for `structuredContent` parity (Pitfall 14 asserts on `filteredDocuments` absence).

**Hermetic embedder** — `tests/support/bench.py:42+` `ConceptEmbedder` is the deterministic no-download embedder; use it (or a mocked `EmbeddingManager`) for lazy-load tests. `test_lazy_embedder.py` must assert `load_model` call counts: zero for status/lex/metadata/get/multi_get, one for query/vec, one cached for the second call, failure → `query` BM25 + `vec_search` `ToolError`.

### `tests/unit/mcp/test_stdout_purity.py` (subprocess)

**No close analog** — `test_transports_stdio.py:1-70` only exercises in-process `StringIO`. New shape: run the real `python -m sif.cli.main mcp stdio` subprocess with a fixture DB (the legacy model-cache migration print at `src/sif/cli/main.py:284-293` is the known pre-run stdout hazard, research Pitfall 8), feed a first `query`, and assert every stdout line `json.loads`-parses as a JSON-RPC frame (no ANSI, `Downloading`, or progress bars).

### `tests/unit/mcp/test_daemon.py` (POSIX)

**Analog:** `test_mcp_watch_host.py` real-tmp-DB style. Cover: `pid_path_for_mcp` name/payload (`mode: "mcp"`, `depth: "bm25"`), marker-aware `corroborate_pid`/`stop_daemon` (a live `mcp` process is not "stale"), watch PID untouched when both daemons run, bind failure removes the PID and exits non-zero, Windows refusal message. Follow the `scripts/windows_smoke.py` refusal-assertion habit of checking cause **and** remedy tokens (`windows_smoke.py:30-38`).

### `tests/unit/mcp/test_plugin.py`, `test_registry_script.py`

**Analog:** `tests/test_docs.py` file-invariant style (read files, assert structure) and the `tmp_path` batteries. Plugin: parse the three JSON files, assert names/version parity with `_version.py`, assert three skill frontmatters, assert `sif-cite` contains the search→get→cite rule; run `claude plugin validate --json .` guarded by `shutil.which("claude")` (skip when absent). Registry: mock HTTP for `--check` branches (marker mismatch, version 404, server.json mismatch, already-listed → exit 0).

---

## Shared Patterns

### 1. Composition-root ordering (quiet → backend → server → mount → lifespan)
**Source:** `transports/stdio.py:128-150`, `transports/http.py:242-264`, `utils/logging.py:37-69`
**Apply to:** `app.py`, `cli.py`, `cli/commands/mcp.py`, daemon arm callback.
```python
set_quiet(True)        # + _apply_quiet_mode env recipe (TQDM_DISABLE, HF_HUB_DISABLE_PROGRESS_BARS, TRANSFORMERS_VERBOSITY)
backend = SearchBackend(db_path)   # inside the lifespan / after stdio diversion
```
Never construct the backend at module import or in `SearchBackend.__init__`'s model path (Pitfall 8/9).

### 2. One result builder, two channels
**Source:** `handlers.py:123-130` + `:296-305`, `src/sif/utils/json_output.py`
**Apply to:** all seven tools; error paths set `is_error=True`.
Text: `json_dumps_strict(model.model_dump(exclude_none=<metadata only>), ensure_ascii=False)`.
Structured: `model.model_dump(mode="json", by_alias=True, exclude_none=<metadata only>)`.

### 3. Fail-closed security defaults
**Source:** `tests/unit/mcp/test_transports_http.py:53-60` (`"*" not in DEFAULT_CORS_ORIGINS`), `utils/daemon.py:178-217` (corroborate before signal), `watch_host.py:113-116` (flag check inside start)
**Apply to:** `app.py` security settings (never `None`, never `*`), `daemon.py` marker (default `watch`), `/health` guard. Every refusal path must name cause + remedy.

### 4. Patch at module boundaries; real tmp DBs for schema-backed assertions
**Source:** `tests/unit/mcp/test_mcp_watch_host.py:1-10` docstring ("Patches land at module boundaries (tests/unit/mcp culture); real tmp DBs back the construction assertions")
**Apply to:** all new test modules.

### 5. Additive public output; byte-identical defaults
**Source:** `core/models.py:321-339` (`to_dict` untouched), `protocol.py:419-428` (frozen envelope), `handlers.py:296-305` (`exclude_none`)
**Apply to:** citation fields (dataclass only), `MetadataOutput`, lex/vec `min_score` (additive field). Golden transcripts must record SDK-added `outputSchema`/`structuredContent` rather than normalize them away (C9).

### 6. Generator-owned docs
**Source:** `Makefile:73-76`, `scripts/generate_cli_ref.py`
**Apply to:** any new `mcp http`/`mcp daemon` flag — run `make docs-generate` and commit the regenerated `docs/cli-reference.md`; never hand-edit it.

### 7. Logger-only diagnostics on stdio hosts
**Source:** `watch_host.py:64-89` (Pitfall 1 comment)
**Apply to:** every new log/notice in `app.py`/`tools.py`/daemon host — `get_logger(__name__)`, never `console.print`/`print`.

---

## No Analog Found

| File | Role | Data Flow | Reason / fallback |
|------|------|-----------|-------------------|
| `uv.lock` | generated config | — | Produced by `uv lock`; never hand-edited. Do not assert exact transitive versions (D-03). |
| `.claude-plugin/marketplace.json` | config manifest | — | No marketplace exists in repo; schema from `22-RESEARCH.md` §plugin/marketplace references (source `"./"`, description, name `sif`). |
| `.claude-plugin/plugin.json` | config manifest | — | No plugin manifest exists; schema from plugin reference; version must equal `_version.py`. |
| `server.json` | config manifest | — | Registry schema 2025-12-11 from research; validated by `scripts/publish_registry.py --check`. |
| SDK-era wire tests (`test_wire_transcripts.py`, `test_sdk_clients.py`) | test | raw JSON-RPC | Current tests are in-process; the era matrix request shapes are only in `22-RESEARCH.md` §Code Examples. Use `TestClient`/`httpx2` ASGI, never `httpx` SDK internals. |

---

## Deletion Inventory (no analogs; gated by proof)

| Path | Lines / contents | Gate before deletion |
|------|------------------|----------------------|
| `src/sif/mcp/server.py` | 193 lines: `ServerState`, `MCPServer`, `resources/read`, 2024-11-05 hardcode | `status` served by SDK over stdio + HTTP; golden transcripts locked (22-01) |
| `src/sif/mcp/handlers.py` | 316 lines: `ToolHandler` ABC + 5 handlers | all seven SDK tools registered + tested |
| `src/sif/mcp/transports/stdio.py` | 150 lines | SDK stdio answers 2024-era handshake |
| `src/sif/mcp/transports/http.py` | 264 lines incl. `validate_origin` | spoofed Header tests green (Host 421, Origin 403, allowed 200); then delete middleware only |
| `src/sif/mcp/transports/__init__.py` | 16 lines barrel | after both transports deleted |
| `src/sif/mcp/protocol.py:18-194, 439-461` | JSON-RPC wire types + helpers | after `app.py`/`tools.py` import only SIF I/O models |
| `tests/unit/mcp/test_server.py` | 241 lines | replaced by `test_wire_transcripts.py` |
| `tests/unit/mcp/test_transports_http.py` | 468 lines | replaced by `test_transport_security.py` (fixtures survive as the copy source) |
| `tests/unit/mcp/test_transports_stdio.py` | 236 lines | replaced by `test_stdout_purity.py` |

---

## Metadata

**Analog search scope:** `src/sif/mcp/`, `src/sif/cli/commands/`, `src/sif/utils/`, `src/sif/search/`, `src/sif/core/`, `src/sif/database/`, `src/sif/embedding/`, `src/sif/indexing/`, `scripts/`, `.claude/skills/`, `tests/`, `tests/support/`, `docs/`, `Makefile`, `pyproject.toml`, `README.md`.
**Files scanned (read in full or targeted):** 36 source/test/doc files; all analog paths confirmed tracked via `git ls-files`.
**Tracked-source gate:** every named analog is git-tracked source (verified). No `.gsd/capabilities` mirrors exist in this repo; nothing to substitute.
**Pattern extraction date:** 2026-11-16
**Conventions enforced:** ruff line length 100, mccabe 10, `list[str] | None` unions, full annotations (`ty check src/sif`), coverage `fail_under = 90`, generated docs never hand-edited.
