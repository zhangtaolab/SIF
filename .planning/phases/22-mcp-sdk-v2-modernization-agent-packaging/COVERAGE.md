# API Coverage — MCP Python SDK v2 (`mcp>=2.3.0,<3`)

> Full coverage by default. Opt-outs are explicit, reasoned decisions.

**Scope:** Phase 22 integrates the official MCP Python SDK v2 (`mcp==2.3.0` verified on Python 3.10.22) to serve every supported client era, expose seven read-only tools, one resource template, stdio + streamable HTTP transports, transport security, and the Claude Code plugin / MCP Registry distribution surfaces.

| capability | decision | reason |
|---|---|---|
| protocol negotiation / era routing | INTEGRATE | The SDK routes `2024-11-05` through `2026-07-28`; SIF delegates all version logic and proves the matrix with golden transcripts (MCP-01). |
| initialize / handshake | INTEGRATE | All four handshake revisions (`2024-11-05`, `2025-03-26`, `2025-06-18`, `2025-11-25`) are served by the SDK and locked by tests. |
| sessions (2025-era) | INTEGRATE | The SDK session manager mints `Mcp-Session-Id`; SIF composes its lifecycle and tests the 2025 handshakes. |
| stateless requests (`2026-07-28`) | INTEGRATE | Requests carrying `MCP-Protocol-Version` + `Mcp-Method` + `Mcp-Name` + `_meta` are served without `initialize`; tested. |
| tools/list | INTEGRATE | Seven tools are registered with generated input schemas and deterministic order. |
| tools/call | INTEGRATE | Every tool returns the explicit dual-channel result (compact text + `structuredContent`). |
| tool input schemas | INTEGRATE | Function signatures + `Annotated[..., Field(...)]` replace the hand-written `input_schema` dicts. |
| tool annotations | INTEGRATE | Every tool carries `read_only_hint=True` / `open_world_hint=False`; honesty test enumerates them (MCP-02). |
| structuredContent / outputSchema | INTEGRATE | Derived from the preserved Pydantic output models and emitted by the explicit builder (MCP-03). |
| tool error semantics (SEP-1303) | INTEGRATE | Expected input/filter/identity failures raise `ToolError`; unexpected exceptions are sanitized by the SDK (MCP-02). |
| cache hints (`ttlMs` / `cacheScope`) | INTEGRATE | The SDK's 2026-era defaults are exercised and asserted in the transcripts; per-tool tuning is deferred. |
| resources/list | INTEGRATE | The `docs://` template is registered and listable by clients. |
| resources/read | INTEGRATE | `docs://{doc_id}` returns full or ranged document text backed by `SearchBackend.get_document` (D-09). |
| resource templates | INTEGRATE | One RFC 6570 template `docs://{doc_id}{?from_line,max_lines}` with `text/markdown`. |
| prompts | OPT-OUT | not needed — agent workflows are encoded in plugin skills; no prompt surface is requested or promised. |
| stdio transport | INTEGRATE | `sif mcp stdio` runs through the SDK stdio server and remains the plugin default. |
| streamable HTTP transport | INTEGRATE | `sif mcp http` and `sif mcp daemon` mount `streamable_http_app()` at `/mcp`. |
| legacy SSE transport | OPT-OUT | not needed — `json_response=True` plus streamable HTTP covers the supported clients; no standalone SSE endpoint is mounted. |
| JSON response mode | INTEGRATE | `json_response=True` preserves SIF's existing JSON HTTP responses. |
| session manager lifecycle | INTEGRATE | `session_manager.run()` is entered before the watcher starts and exited after it stops (D-18). |
| transport security (Host / Origin) | INTEGRATE | Explicit `TransportSecuritySettings` on every bind; Host 421 / Origin 403 proven before the old middleware is deleted (MCP-04). |
| content-type validation | INTEGRATE | The SDK rejects non-JSON POST bodies with 400; covered by the transport-security battery. |
| client APIs (SDK `Client`) | INTEGRATE | Used by the real-client matrix in `mode="legacy"` and `mode="auto"` over in-process, ASGI, and stdio. |
| auth / OAuth | OPT-OUT | explicitly out of scope — loopback personal server; OAuth is a recorded anti-feature (REQUIREMENTS.md). |
| sampling | OPT-OUT | explicitly out of scope — recorded anti-feature for this loopback server. |
| elicitation | OPT-OUT | explicitly out of scope — recorded anti-feature for this loopback server. |
| roots | OPT-OUT | explicitly out of scope — recorded anti-feature for this loopback server. |
| logging capability | OPT-OUT | explicitly out of scope — SIF diagnostics go to stderr / `mcp.log`; the MCP logging capability is not implemented. |
| completion | OPT-OUT | not needed — no argument-completion surface is requested in v1.2. |
| progress notifications | OPT-OUT | not needed — tool calls are short request/response operations; no progress tokens are emitted. |
| tasks | OPT-OUT | explicitly out of scope — recorded anti-feature. |
| subscriptions | OPT-OUT | not needed — watch events are logs, not resource-update notifications. |
| ping | INTEGRATE | SDK-owned; exercised by the SDK client matrix on both protocol modes. |
| pagination / cursors (MCP list cursors) | OPT-OUT | not needed — seven tools and one resource template fit one page; result pagination uses tool-level `limit`/`offset`. |
| server discovery (`serverInfo`, registry) | INTEGRATE | `serverInfo.name` stays `sif-mcp-server`; `server.json` + `scripts/publish_registry.py` provide Registry discovery (MCP-09). |
| lifespan hooks | INTEGRATE | The SDK lifespan hosts schema-open backend construction and the watch host with the D-18 teardown order. |
| per-tool cache TTL / cacheScope tuning | OPT-OUT | not needed yet — SDK defaults are shipped; revisit only if a client needs different caching. |
