# Phase 22: MCP SDK v2 Modernization + Agent Packaging - Research

**Researched:** 2026-11-16
**Domain:** MCP Python SDK v2 shell replacement, structured output, transport security, lazy embedder, daemon lifecycle, Claude Code plugin + MCP Registry
**Confidence:** HIGH for SDK behavior and in-repo integration (verified by install/import and live ASGI/stdio probes against `mcp==2.3.0` on Python 3.10.22, plus direct source reads at HEAD `3a3c4ef`); MEDIUM for plugin/registry external flows (official docs read; `claude plugin validate` exercised locally; `mcp-publisher` not installed and live publish not attempted)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Shell replacement, dependency gate, and compatibility (MCP-01)**
- **D-01:** **Tracer-first full shell replacement, no dual stack.** Replace the hand-rolled `MCPServer`/JSON-RPC/transports with the official SDK `MCPServer` and delete the old shell (`src/sif/mcp/server.py`, the wire-type half of `src/sif/mcp/protocol.py`, `src/sif/mcp/transports/stdio.py`, `src/sif/mcp/transports/http.py`); preserve `SearchBackend`, `watch_host.py`, and the SIF tool I/O Pydantic models as the tool contract. Migrate one tool (`status`) end-to-end through both transports first, locking golden wire transcripts, then expand tool-by-tool. No parallel implementation or feature flag (research Anti-Pattern 8). — **Reversibility:** costly — the wire contract and client behavior are public; reverting after release would re-open client-compatibility validation.
- **D-02:** **Python 3.10 install/import smoke is the first gate.** Resolve `mcp>=2.3.0,<3` in a Python 3.10 scratch venv, install the project, and import `mcp.server.MCPServer` + `sif.mcp.app` before detailed planning of the swap. The Phase 22 research gap in STATE.md is this exact check (PyPI metadata says >=3.10 while the SDK README says 3.11+). If 2.x cannot run on 3.10, STOP and surface a user decision before raising SIF's floor or shipping a `mcp<2` compatibility pin — either is a one-way packaging change. — **Reversibility:** costly — a Python-floor change or dual-version pin changes the published package contract and the CI matrix.
- **D-03:** **`mcp` becomes a core dependency; extras stay as compatibility aliases.** Add `mcp>=2.3.0,<3` to `[project].dependencies`; keep the `mcp` and `http` extras as thin deprecated aliases (uvicorn only) so existing `pip install docsif[mcp]` commands keep working; do not pin `mcp-types` directly (SDK transitive); no other new runtime dependency. Refresh `uv.lock`; tolerate the py3.10/3.11+ resolution fleets without asserting exact transitive versions. — **Reversibility:** costly — the dependency set is a published packaging contract.
- **D-04:** **Dual-era compatibility is proven, not assumed.** Lock golden JSON-RPC wire transcripts for a 2024-11-05 `initialize` handshake, a 2025-11-25 handshake, and a 2026-07-28 stateless request (no `initialize`, `MCP-Protocol-Version` header), plus SDK-client tests for both eras. Add one real Claude Code smoke (temporary config; `claude mcp` tool listing + one `query`) recorded in SUMMARY. Delegate protocol negotiation to the SDK; never hand-roll version logic. Use `json_response=True` on the mounted HTTP app to preserve SIF's JSON responses; use SDK cache hints when exposed, otherwise assert the SDK's 2026-era defaults in the transcript. — **Reversibility:** costly — the supported-era claim is what existing clients depend on.
- **D-05:** **Legacy text content stays alongside structured output.** Every tool keeps the serialized JSON text payload legacy clients parse today and adds `structuredContent` plus `outputSchema` from the same Pydantic model. New fields are additive; existing field names and values do not change. If the SDK's auto-wrapping changes the text payload (for example a `{"result": ...}` wrapper), use an explicit result builder returning both channels rather than accepting the change. — **Reversibility:** costly — the text payload is the backward-compatibility contract for 2024/2025-era clients.

**Tool surface, annotations, errors, resources (MCP-02)**
- **D-06:** **Seven read-capable tools; no mutation tools in Phase 22.** Register `query`, `get`, `multi_get`, `status`, `metadata`, `lex_search`, `vec_search`. Do NOT add `index update/embed`, `vacuum`, `backup`, or collection-mutation tools; those stay CLI/watch surfaces. `metadata` surfaces the Phase 20 frozen envelope unchanged. — **Reversibility:** costly — the tool list is a public MCP contract; adding tools later is additive, but shipping a mutation surface is a security commitment.
- **D-07:** **Annotations reflect actual behavior, never auto-approval.** All seven tools carry `read_only_hint=True`, `open_world_hint=False`; `idempotent_hint`/`destructive_hint` are omitted for read-only tools because they are only meaningful for non-read-only tools. Never claim prompt-free execution — documented Claude Code effects are parallel read-only calls plus one retry only. Tool descriptions are reviewed constants; fix the `query` description's rerank overclaim (rerank is opt-in). A test enumerates the registered tools, asserts every tool is read-only and every description matches backend behavior, and encodes the future-write-tool policy (`read_only_hint=False` + `destructive_hint=True` where applicable). — **Reversibility:** costly — hosts consume annotations for approval UX and security posture.
- **D-08:** **Expected tool errors are `ToolError`s.** Filter/match AST validation, input validation, unknown collection, vector-unavailable for `vec_search`, and identity dimension mismatches raise `ToolError` with the existing remedy text so the model can self-correct (SEP-1303); unexpected exceptions propagate and are sanitized by the SDK to `-32603`. Never return `INVALID_PARAMS` for tool-input semantics. Preserve the handler-side Pydantic validation the SDK's low-level path no longer performs. — **Reversibility:** costly — error semantics are an agent-facing contract.
- **D-09:** **Preserve the `docs://` resource capability.** Register an SDK resource for `docs://{doc_id}` backed by `SearchBackend.get_document`; return the full document by default and honor `from_line`/`max_lines` when present in the URI. The `get` tool remains the citation-grade line-range surface. The resource is read-only and subject to the same transport security. — **Reversibility:** costly — removing a resource would break clients that read documents via resources.

**Structured output and citation contract (MCP-03)**
- **D-10:** **The preserved Pydantic output models are the schemas.** Tool functions return `QueryOutput`/`GetOutput`/`MultiGetOutput`/`StatusOutput`/`MetadataOutput`/`LexSearchOutput`/`VecSearchOutput`; the SDK derives `outputSchema` and `structuredContent` from the return annotation. `MetadataOutput` is returned as the model (unwrapped), so the Phase 20 envelope (`documents`, `filteredDocuments`, `totalKeys`, `remainingKeys`, `skippedKeys`, `builtIns`, `keys`) stays byte-compatible. Avoid dict returns for frozen envelopes; if the SDK's auto text differs, use the D-05 builder. — **Reversibility:** costly — output schemas are a public contract.
- **D-11:** **Citation-grade fields are distributed per tool.** Extend the MCP `SearchResult` with `snippet`, `content_hash` (from `documents.checksum` via one batched page lookup), `line_start`, and `line_end`; keep `docid`, `path`, `title`, `score`, `chunk_id`, `sequence`, `chunk_matches`, and `vectors_stale`. Line ranges come from the snippet window the pipeline already computes for `SmartSnippetExtractor` (extend the extractor to report its selected document-line window; no extra content scan, no new chunk columns). Extend `Document` with `content_hash` and always populate `line_start`/`line_end` on `get`/`multi_get` (full document = 1..N; ranged request = requested range). Do NOT add these fields to `SearchResult.to_dict()` — CLI JSON stays byte-identical; the MCP boundary maps the dataclass fields explicitly. The `sif-cite` skill must call `get` and cite docid + line numbers; never cite a snippet alone (two-stage citation). — **Reversibility:** costly — the citation schema and agent workflow are public.
- **D-12:** **Frozen envelopes win; changes elsewhere are additive.** The Phase 20 `metadata` envelope is surfaced unchanged, including `builtIns`, mixed camelCase, and exact remainders. Query/get output changes are additive only; no `schemaVersion` field in Phase 22. Contract versioning lives in docs/tests and the golden transcripts. — **Reversibility:** costly — the metadata envelope is a cross-phase contract consumed by later agents.

**Transport security (MCP-04)**
- **D-13:** **Host/Origin validation comes from the SDK, configured through CLI flags.** Use the SDK `transport_security` settings with loopback defaults (`127.0.0.1`, `localhost`, `[::1]`) and the existing CORS origin list. Add `--allowed-hosts` to `mcp http` and `mcp daemon` (repeatable or comma-separated; planner's choice); keep `--cors-origins` as the origin allowlist. No new Settings fields. Never default to `*`; a non-loopback bind without explicit allowed hosts prints a warning and does not silently widen the allowlist. — **Reversibility:** costly — the flags and security behavior are public.
- **D-14:** **Prove before deleting the hand-rolled middleware.** Add spoofed-header tests (bad `Host` → 403, bad `Origin` → 403, allowed → 200) against the mounted SDK app; only then delete the custom `validate_origin` middleware. Keep `CORSMiddleware` for browser preflight/response headers. `/health` stays unauthenticated but is subject to Host validation. — **Reversibility:** costly — deleting a defense layer requires the proof to remain in the test suite.

**Lazy embedder, stdout purity, and query/watch parity (MCP-05/06)**
- **D-15:** **The embedder loads lazily, once, and failure degrades honestly.** Use `EmbeddingManager` lazily on the first vector/hybrid need; one thread-safe load attempt per process. On failure, `query` degrades to BM25 with one warning (the WR-08 MCP carve-out), `vec_search` returns a `ToolError` naming the install/model remedy, and `lex_search`/`status`/`metadata`/`get`/`multi_get` never load a model. After load, the pipeline uses the loaded identity's dimension (Phase 21's loaded-model truth), not the settings value. The schema-open settings identity remains as Phase 21 left it. — **Reversibility:** costly — the failure behavior is an agent-visible contract.
- **D-16:** **Force quiet at the MCP composition root.** Call `set_quiet(True)` and the existing `_apply_quiet_mode` environment recipe (`TQDM_DISABLE`, `HF_HUB_DISABLE_PROGRESS_BARS`, `TRANSFORMERS_VERBOSITY`) before constructing the backend or importing any model, at stdio, HTTP, and daemon entrypoints. All diagnostics go to stderr/logs. Add a cold-first-query stdout-purity regression (every stdout line is JSON-RPC; no progress bars/ANSI). Do not hand-roll stdout redirection unless that regression proves the SDK insufficient; if needed, write protocol frames to the saved real stdout. — **Reversibility:** reversible — the regression and quiet call can be adjusted without a migration.
- **D-17:** **MCP `query` gets full CLI pipeline parity; `lex_search`/`vec_search` mirror the CLI one-shot search commands.** Wire `QueryExpansion` (same default-on hybrid expansion as CLI), `SmartSnippetExtractor`, and the reranker as an opt-in `rerank: bool | None = None` parameter (None follows `SIF_RERANK_ENABLED`; True/False overrides). Hoist heavyweight components (manager, expander, reranker, snippet extractor) at backend level; construct `SearchPipeline` per request because `_run_in_db` opens a fresh connection per request and the pipeline is connection-bound. `lex_search`/`vec_search` call `BM25Searcher`/`VectorSearcher` directly with the same options, filter, offset, per-chunk, identity check, and one `enrich_results`, matching CLI `search`/`vsearch`; they do not use prefix routing. Expansion/rerank failures degrade softly with a warning, exactly as CLI. Identity mismatches follow Phase 21 D-03 (warn + mark on search; fail-fast on embed). — **Reversibility:** costly — the query parameter surface and latency behavior are public.
- **D-18:** **The watch host survives the shell swap with its invariants intact.** Compose the SDK lifespan with `mcp_watch_lifespan`: enter `mcp.session_manager.run()`, start the watcher, yield, stop the watcher, then exit the session manager. Preserve `SIF_MCP_WATCH` opt-in, the literal `bm25` depth, logger-only callbacks, serve-first reconcile, and the D-14 `stop(flush=True)` → WAL checkpoint → close order. Stdio and HTTP hosts both retain the watch wiring. — **Reversibility:** costly — the live-index contract and shutdown ordering are user-visible.

**Daemon (MCP-07)**
- **D-19:** **`mcp daemon` is a real HTTP daemon.** Implement it with the existing `utils/daemon.py` double-fork/arming machinery; run the HTTP transport detached; support `--stop`; reject stdio daemon mode. On Windows, refuse with the existing POSIX-fork cause/remedy (foreground `mcp http` remains available). — **Reversibility:** costly — the command and lifecycle are public.
- **D-20:** **The MCP daemon has its own PID artifact.** Use `<db>.mcp.pid` (with `--pid-file` override), payload `mode: "mcp"`, distinct from the watch daemon's `<db>.watch.pid`, so a watch daemon and an MCP daemon can run on one index concurrently. `sif status`'s watch section remains unchanged; `mcp daemon --stop` targets only the MCP daemon. — **Reversibility:** reversible — PID naming is internal metadata.
- **D-21:** **Arm on readiness; do not warm the model at startup.** The arm callback opens the DB, runs schema initialization, constructs the backend, and writes the PID; the HTTP bind happens after arming, and a bind failure exits the daemon, removes the PID file, and is logged. No startup model load (keeps startup cheap and quiet); the first vector query loads lazily and the process keeps the model warm. Default log `mcp.log` in the platform log dir; `--log-file` overrides. — **Reversibility:** reversible — the lifecycle can be tuned additively.

**Claude Code plugin, marketplace, Registry (MCP-08/09)**
- **D-22:** **The repo root is the Claude Code plugin.** Add `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` with `source: "./"`, root `.mcp.json`, and `skills/` (`sif-search`, `sif-get`, new `sif-cite`). Plugin and marketplace names are `sif` (no `claude-`/`anthropic-` prefix); plugin version mirrors `src/sif/_version.py`. `claude plugin validate` is a phase gate (Claude Code 2.1.325 is installed). — **Reversibility:** costly — marketplace/distribution identity is public.
- **D-23:** **The plugin targets the installed `sif` command; skills are MCP-first.** `.mcp.json` runs `sif mcp stdio` by default. Installation docs make `uv tool install 'docsif[embed]'` the primary path (base install is BM25-only), with the Linux CPU-torch index and the installed-vs-zero-install distinction documented; `uvx --from ${CLAUDE_PLUGIN_ROOT} sif mcp stdio` is documented as the zero-install BM25-only fallback. Plugin skills call the MCP tools (`query`, `get`, `metadata`, `lex_search`, `vec_search`), not the CLI; `sif-cite` encodes the search→get→cite discipline: discover metadata before filtering, retrieve with `get`, cite docid + line numbers from `get`, never cite a snippet alone, and surface `vectors_stale`/`content_hash` caveats. — **Reversibility:** costly — the agent workflow and install path are user-facing.
- **D-24:** **Registry listing is scripted, preflighted, and re-runnable; Phase 22 does not cut a v1.2 release.** Check in `server.json` with name `io.github.zhangtaolab/sif`, package `docsif`, transport stdio, and version read from `src/sif/_version.py` (currently 1.1.2, already published). Add `scripts/publish_registry.py` with `--check` (README `mcp-name` marker exact match, PyPI JSON version exists, `server.json` schema/name/version consistency, registry idempotency) and `--publish` (runs `mcp-publisher publish` after the maintainer's `mcp-publisher login github` device flow). Never store credentials. The live publish is a maintainer checkpoint if the login is unavailable; record the exact command and registry verification URL. Re-run the script after the v1.2 release to advance the listed version. — **Reversibility:** costly — Registry names/versions are public and version-immutable.

**Quality gates and documentation**
- **D-25:** **The MCP rewrite carries its own regression net.** Rewrite/replace the MCP server and transport tests around the SDK composition root and tool functions; keep `SearchBackend`/watch-host tests. Add golden wire transcripts for the three eras, SDK-client tests for both eras, spoofed Host/Origin tests, cold-first-query stdout purity, lazy-load no-model tests, metadata-envelope parity, plugin JSON/skill tests, and registry-script preflight tests. The 90% coverage gate, ruff/format/ty gates, and `make docs-generate` must stay green. Update `docs/mcp-server.md`, `src/sif/mcp/README.md`, `README.md` (plugin/registry sections), and the generated CLI docs; never hand-edit generated docs. No new runtime deps beyond `mcp`; plugin assets are Markdown/JSON only. — **Reversibility:** reversible — tests/docs can evolve without a migration.

### Claude's Discretion

CONTEXT.md records no separate `## Claude's Discretion` section. The planner's freedom is bounded by the per-decision `Reversibility` annotations and the items D-25 marks as evolvable (tests/docs); anything marked **costly** above is a public contract.

### Deferred Ideas (OUT OF SCOPE)

- **MCP mutation tools** (`index update/embed`, `vacuum`, `backup`, collection mutation) — stay CLI/watch in Phase 22. If exposed later: `read_only_hint=False`, `destructive_hint=True` where applicable, and no caller-supplied target paths (PITFALLS 11/19). A future phase, not a clarification of this one.
- **qmd-style `searches` array / HyDE sub-query parameter** on the MCP `query` tool — not required for parity; additive later.
- **OAuth / elicitation / MRTR / tasks / sampling / roots / logging** — rejected for the loopback personal server (REQUIREMENTS Out of Scope).
- **Full Windows daemon/service parity** — v2; Phase 22 keeps the clean POSIX-fork refusal and foreground `mcp http`.
- **Registry CI OIDC automation and automatic re-listing on release** — the scripted local/device-flow path ships first; a workflow is additive later.
- **Additional marketplace hosts, plugin hooks/commands, or a separate plugin repository** — the repo-root plugin is v1.2 deliverable.
- **Line ranges in CLI JSON output** — kept out of `SearchResult.to_dict()` in Phase 22 to preserve CLI byte-identical output; the MCP boundary carries them.
- **Per-tool TTL/cacheScope tuning beyond SDK defaults** — revisit if a client needs a shorter/longer cache.
</user_constraints>

## Project Constraints (from CLAUDE.md)

Actionable directives from `./CLAUDE.md` that the planner and executor must satisfy:

- **Python 3.10+**; use `list[str] | None` union syntax. New code fully annotated (`ty check src/sif`), including tool functions and helpers.
- **Quality suite** after every plan: `ruff check src tests`, `ruff format --check src tests`, `pytest` (coverage `fail_under = 90` [VERIFIED: `pyproject.toml:225`]). `ty check src/sif` is the type gate.
- **Style:** line length 100, max complexity 10, ruff isort with `combine-as-imports = true`, order stdlib/third-party/first-party (`sif`), two blank lines after imports. CLI modules keep Click decorators as-is.
- **Exactly two new runtime deps in v1.2:** `rapidfuzz` (landed) and `mcp` (this phase). No others; plugin assets are Markdown/JSON only.
- **Generator-owned docs:** `docs/cli-reference.md` and `docs/configuration.md` are regenerated by `make docs-generate` (`scripts/generate_cli_ref.py` + `scripts/generate_config_ref.py`) under a CI diff gate — never hand-edit them. New `mcp http`/`mcp daemon` flags must flow through it.
- **Logging:** module loggers via `get_logger(__name__)`; output to stderr. stdout stays machine-clean.
- **Errors:** CLI raises `click.ClickException(str(e))`; DB work uses `Database.transaction()` with rollback. MCP expected errors use `ToolError` (D-08).
- **MCP error carve-out:** core `HybridSearcher.search()` stays fail-fast; only the MCP `SearchBackend` boundary degrades to BM25 for a missing sqlite-vec extension and (D-15) an embedder load failure.
- **Repository pattern:** entity CRUD through `src/sif/database/repositories.py`; search strategies and the embedding cache may execute SQL directly. New checksum batch lookup belongs in `DocumentRepository`.
- **GSD workflow:** phase work runs through `/gsd-execute-phase`; small fixes use `/gsd-quick`, investigations `/gsd-debug`.

## Summary

The phase is buildable as specified, and the one gate that could have forced a user decision has passed: `mcp==2.3.0` installs and imports on **Python 3.10.22**, alongside the full SIF dependency set, and exposes `mcp.server.MCPServer`, `ToolAnnotations`, `ToolError`, `TransportSecuritySettings`, `streamable_http_app()`, `session_manager.run()`, `run(transport=...)`, and `CacheHint` [VERIFIED: /tmp/sif-mcp310-venv install of `-e .` + `mcp==2.3.0`]. The SDK's protocol registry explicitly covers every handshake era — `KNOWN_PROTOCOL_VERSIONS = ("2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25", "2026-07-28")`, `OLDEST_SUPPORTED_VERSION = "2024-11-05"` [VERIFIED: `mcp_types/version.py` in the venv] — and a live probe negotiated 2024-11-05, 2025-03-26, 2025-06-18, and 2025-11-25 handshakes and served a stateless 2026-07-28 request. The research gap in STATE.md (2025-06-18 clients) and PITFALLS P9 are closed.

Three implementation facts shape the plan more than the CONTEXT anticipated. First, the SDK's automatic text channel is **pretty-printed with `indent=2`** and a `list[...]` return is unrolled into one text block per element [VERIFIED: `_convert_to_content` source + live wire probe], so D-05's "explicit result builder" is mandatory for every tool, not an edge case. Second, the SDK's Host rejection status is **421 Misdirected Request**, not 403, and its Origin rejection is 403 [VERIFIED: live probe and `transport_security.py` source]; `/health` on the FastAPI parent is outside the SDK transport and is **not** Host-validated (bad Host returned 200) [VERIFIED: live probe]. Third, the daemon's PID corroboration is hardcoded to the literal `watch` token [VERIFIED: `src/sif/utils/daemon.py:58,217`], so D-20's "add only an MCP PID-path helper" is insufficient: `corroborate_pid`/`stop_daemon` must learn an MCP marker or `mcp daemon --stop` will classify a live daemon as stale and never signal it.

**Primary recommendation:** Adopt `mcp>=2.3.0,<3` now; build one composition root (`src/sif/mcp/app.py`) that constructs `MCPServer("sif-mcp-server", version=__version__, lifespan=...)`, always passes an explicit `TransportSecuritySettings` (never `None`), mounts `streamable_http_app(streamable_http_path="/mcp", json_response=True, transport_security=...)` at the parent app root after `/health`, and returns every tool result through one explicit `CallToolResult` builder that emits today's compact `json_dumps_strict` text plus a model-derived `structured_content`. Prove the three eras with raw JSON-RPC transcripts (2024-11-05 / 2025-06-18 / 2025-11-25 via session headers; 2026-07-28 via `MCP-Protocol-Version` + `Mcp-Method` + `Mcp-Name` + `_meta`), plus SDK `Client` tests in `mode="legacy"` and `mode="auto"` over both stdio and an in-process ASGI transport, then delete the 623-line shell.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Protocol negotiation, sessions, era routing | API / Backend (SDK `MCPServer` + session manager) | — | The SDK routes by `MCP-Protocol-Version` before user code; hand-rolling any of it is Anti-Pattern 8 [VERIFIED: live era matrix] |
| Tool input validation | API / Backend (tool-layer Pydantic models + `Annotated` constraints) | — | SDK arg models validate the signature; SIF's `QueryInput`/`FilterAst` validators stay in the handler layer (D-08) [VERIFIED: arg-validation probe] |
| Tool result shaping (text + structuredContent + outputSchema) | API / Backend (explicit `CallToolResult` builder) | — | SDK auto-wrapping changes text bytes; the builder is the only way to keep both channels exact (D-05/D-10) [VERIFIED] |
| Query semantics (hybrid, expansion, rerank, snippets) | API / Backend (`SearchBackend` + `SearchPipeline`) | Search layer | `SearchBackend` is the preserved seam; pipeline is connection-bound and built per request (D-17) |
| Embedder lifecycle | API / Backend (`SearchBackend` lazy manager) | Embedding layer (`EmbeddingManager`) | Startup must stay model-free; load on first vector/hybrid need with one thread-safe attempt (D-15) |
| DNS-rebinding protection | Edge (SDK `TransportSecuritySettings`) | FastAPI parent (CORS + `/health` guard) | SDK validates Host/Origin inside the mount; `/health` needs a narrow parent-level Host guard (D-14) [VERIFIED: split behavior] |
| Watch host lifecycle | API / Backend (SDK lifespan) | Watch layer (`FileWatcher`) | `session_manager.run()` must be entered before the watcher starts and exited after it stops (D-18) |
| Daemon lifecycle | CLI / OS (double-fork + PID artifact) | API / Backend (HTTP host) | Reuse `utils/daemon.py`; arm before bind; separate `<db>.mcp.pid` (D-19..D-21) |
| Plugin + marketplace + skills | Distribution (repo-root assets) | — | Markdown/JSON only; `.mcp.json` runs the installed `sif` (D-22/D-23) |
| Registry listing | Distribution (scripted preflight) | PyPI (published package) | `server.json` + README marker + `mcp-publisher`; idempotency must be implemented in the script (D-24) |
| Citation fields (docid/path/lines/hash) | Search layer (core dataclasses) | MCP boundary mapping | CLI JSON stays byte-identical; MCP maps fields explicitly (D-11) |



<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MCP-01 | Official SDK v2 migration; dual-era 2024-11-05 → 2026-07-28 + stateless; tracer-first with golden transcripts + client matrix; py3.10 smoke; backend/watch/I-O models preserved; shell deleted | D-02 gate passed on Python 3.10.22; era matrix probed live; composition root pattern; deletion inventory; test module map |
| MCP-02 | Accurate annotations on all tools; no auto-approval claims; descriptions match backend | `ToolAnnotations` verified; generated wire annotations observed; annotation honesty test design; seven-tool surface |
| MCP-03 | Citation-grade structuredContent/outputSchema with docid, path, line range, hash, staleness; text kept | Structured-output mechanics verified; explicit builder required; extractor line-window extension; batched checksum lookup; `Document`/`SearchResult` field map |
| MCP-04 | Loopback DNS-rebinding protection via SDK `transport_security`; spoofed-header proof before deleting middleware | Exact settings shape/defaults; 421/403 behavior; loopback auto-enable; non-loopback disables protection unless explicit; `/health` gap |
| MCP-05 | Full query pipeline parity; rerank opt-in; pipeline hoisted; lex/vec wired; overclaim fixed | CLI wiring recipe at `search.py:1155-1197`; per-request pipeline constraint; lex/vec direct-searcher recipes; identity-check closure |
| MCP-06 | Clean stdout; lazy embedder; forced quiet; cold-first-query purity; lex/vec wiring | SDK stdio fd diversion verified; lifespan runs post-diversion; `set_quiet`/`_apply_quiet_mode`; lazy manager + lock; pre-run stdout hazards |
| MCP-07 | Real `mcp daemon` via existing daemon machinery | `detach`/arm/stop contract; PID payload requirements; corroboration marker blocker; bind-after-arm cleanup; Windows refusal |
| MCP-08 | Claude Code plugin + marketplace + citation skill; `claude plugin validate` passes | Manifest schemas read; validate exercised (exit codes, warnings, `--json`); skills frontmatter rules; repo-root caveats |
| MCP-09 | MCP Registry listing via mcp-publisher, scripted/preflighted/re-runnable | `server.json` schema/pyPI marker rules; PyPI 1.1.2 + marker verified; registry duplicate-version rejection verified at source; preflight design |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `mcp` (official Python SDK v2) | **2.3.0** (pin `>=2.3.0,<3`) | Replace the hand-rolled MCP protocol/transports with `MCPServer`; dual-era serving; annotations; structured output; transport security | Locked decision (D-03). MIT; `Requires-Python: >=3.10` verified from installed metadata and PyPI JSON; pure-Python wheel; official `modelcontextprotocol/python-sdk` [VERIFIED: PyPI JSON + install] |
| `mcp-types` | 2.3.0 (auto, exact-pinned by `mcp`) | Wire types (`ToolAnnotations`, `CallToolResult`, `TextContent`) | Transitive — never declare directly (D-03). `mcp.types` is a permanent alias [VERIFIED: venv] |
| FastAPI / Starlette / uvicorn | project-locked 0.136.0 / 1.0.0 / 0.44.0 | Parent app + SDK ASGI mount | Already core deps. mcp 2.3.0 requires `starlette>=0.27`, `uvicorn>=0.31.1`, `sse-starlette>=3` (which needs `starlette>=0.49.1`); the locked 1.0.0/0.44.0 satisfy all [VERIFIED: venv resolution + `uv.lock`] |
| Pydantic | lock 2.13.1 (venv resolved 2.14.3) | Tool I/O models and generated schemas | mcp 2.3.0 requires `pydantic>=2.12`; project floor `>=2.0.0` resolves fine [VERIFIED: `uv pip install -e . mcp==2.3.0`] |

### Supporting (transitive, do not declare)

| Library | Version resolved on py3.10 | Purpose | Note |
|---------|---------------------------|---------|------|
| `httpx2` | 2.14.0 | SDK HTTP client | PyPI download signal unknown (see audit); rides mcp |
| `truststore` | 0.10.5 | OS trust store for httpx2 TLS | Transitive |
| `sse-starlette` | 3.5.1 | SSE transport | Transitive |
| `pyjwt[crypto]` / `cryptography` | 2.15.1 / 50.0.2 | Auth scaffolding (unused by SIF) | Transitive; compiled wheel |
| `opentelemetry-api` | 1.45.2 | SDK telemetry hooks (unused) | Transitive |

### Development / verification tools

| Tool | Version | Purpose | Notes |
|------|---------|---------|-------|
| `uv` | 0.13.7 | lock/install/venv | Used for the D-02 gate |
| `claude` (Claude Code) | **2.1.325** | `claude plugin validate` | Installed; `--json`, `--strict`, `--profile directory` verified |
| `mcp-publisher` | not installed | Registry publish | `brew install mcp-publisher`; login device flow; maintainer checkpoint |
| pytest / pytest-asyncio / ruff / ty | project-locked | Quality gates | `fail_under = 90` [VERIFIED: `pyproject.toml:225`] |

**Installation (pyproject delta):**
```toml
[project]
dependencies = [
    # ... existing ...
    "mcp>=2.3.0,<3",
]
# mcp / http extras stay as thin deprecated aliases (uvicorn only), now redundant.
```

**Version verification commands (recorded output):**
```bash
uv python install 3.10                      # Installed Python 3.10.22
uv venv --python 3.10 /tmp/sif-mcp310-venv
uv pip install --python /tmp/sif-mcp310-venv/bin/python "mcp==2.3.0"
#   mcp==2.3.0  mcp-types==2.3.0  pydantic==2.14.3  starlette==1.0.0  uvicorn==0.54.0
#   sse-starlette==3.5.1  httpx2==2.14.0  cryptography==50.0.2 ...
uv pip install --python /tmp/sif-mcp310-venv/bin/python -e . "mcp==2.3.0"
#   resolves with rapidfuzz==3.14.5, numpy==2.2.6, pydantic-settings==2.15.0, sqlite-vec==0.1.9
/tmp/sif-mcp310-venv/bin/python -c "import mcp; from mcp.server import MCPServer; import sif, sif.mcp.backend, sif.mcp.watch_host"
#   OK on Python 3.10.22; sif.mcp.app is the only missing module (planned)
```

## Package Legitimacy Audit

> `mcp` is the only new **direct** runtime dependency; everything else in this table is transitive. No SLOP verdicts. Verdicts come from `gsd-tools query package-legitimacy check --ecosystem pypi` run 2026-11-16.

| Package | Registry | Project evidence | Verdict | Disposition |
|---------|----------|------------------|---------|-------------|
| `mcp` | PyPI | Official MCP SDK; 73 releases since 2024-11-20; repo `github.com/modelcontextprotocol/python-sdk`; MIT; 2.3.0 uploaded 2026-10-02 | **SUS** (`unknown-downloads`) | Approved as the locked dependency (D-03), but the planner MUST insert one `checkpoint:human-verify` before the `uv lock`/install task because the seam cannot see PyPI download counts |
| `mcp-types` | PyPI | Exact-pinned by `mcp==2.3.0`; same publisher/repo | **SUS** (`unknown-downloads`) | Transitive; no direct declaration |
| `httpx2` | PyPI | Repo `github.com/pydantic/httpx2`; latest 2.14.0 on py3.10 | **SUS** (`too-new`, `unknown-downloads`) | Transitive; the seam's `publishedAt` is the latest release upload time, not project age |
| `truststore` | PyPI | Repo `github.com/sethmlarson/truststore` | **SUS** (`unknown-downloads`) | Transitive |
| `sse-starlette` | PyPI | Required by `mcp>=2.3.0` | **SUS** (`too-new`, `unknown-downloads`) | Transitive |
| `pyjwt` | PyPI | Required by `mcp` | **SUS** (`unknown-downloads`) | Transitive |
| `opentelemetry-api` | PyPI | Required by `mcp` | **SUS** (`too-new`, `unknown-downloads`) | Transitive |

**Packages removed due to SLOP verdict:** none.
**Packages flagged suspicious [SUS]:** `mcp` (direct, locked) plus its transitive chain. The `unknown-downloads` reason is a PyPI signal gap, not a risk finding; the seam reports no `deprecated` or `postinstall` signals. The single human checkpoint covers the direct install; do not add checkpoints for the transitive chain.

## Architecture Patterns

### System Architecture Diagram

```
                          CLIENTS BY ERA
  ┌───────────────┐  ┌──────────────────┐  ┌───────────────────────────┐
  │ 2024-11-05 /  │  │ 2025-03-26 /     │  │ 2026-07-28 stateless      │
  │ 2025-06-18    │  │ 2025-06-18 /     │  │ POST + MCP-Protocol-Version│
  │ initialize    │  │ 2025-11-25 init  │  │ + Mcp-Method [+ Mcp-Name]  │
  │ + session id  │  │ + session id     │  │ + params._meta (version,   │
  └──────┬────────┘  └────────┬─────────┘  │   clientCapabilities)      │
         │                    │            └─────────────┬─────────────┘
         └──────────┬─────────┴──────────────────────────┘
                    ▼
        ┌──────────────────────────────────────────────────────┐
        │ FastAPI parent app (lifespan: session_manager.run()) │
        │  CORS middleware          /health (Host guard)       │
        │  └─ mount "/" → SDK streamable_http_app("/mcp",      │
        │        json_response=True, transport_security=...)   │
        │     └─ TransportSecurityMiddleware (Host 421,        │
        │        Origin 403, Content-Type 400)                 │
        └──────────────────────────┬───────────────────────────┘
                                   ▼
        ┌──────────────────────────────────────────────────────┐
        │ MCPServer("sif-mcp-server", version=__version__,     │
        │   lifespan=sif_lifespan, cache_hints={...})          │
        │  @mcp.tool query/get/multi_get/status/metadata/      │
        │           lex_search/vec_search  → explicit          │
        │           CallToolResult(text=compact JSON,          │
        │                          structured_content=model)   │
        │  @mcp.resource docs://{doc_id}{?from_line,max_lines} │
        └──────────────────────────┬───────────────────────────┘
                                   ▼
        ┌──────────────────────────────────────────────────────┐
        │ SearchBackend (preserved)                            │
        │  lazy EmbeddingManager (one lock, one attempt)       │
        │  hoisted expander / reranker / snippet extractor     │
        │  per-request SearchPipeline (fresh connection)       │
        │  identity check closure (Phase 21 contract)          │
        └──────────────────────────┬───────────────────────────┘
                                   ▼
   ┌───────────────────────────────┴────────────────────────────────┐
   │ BM25Searcher / VectorSearcher / Hybrid+RRF / enrich_results    │
   │ SQLite: documents(+FTS, checksum) · vec0 · index_meta          │
   └────────────────────────────────────────────────────────────────┘

   DISTRIBUTION: `.claude-plugin/{plugin,marketplace}.json` + `.mcp.json`
   + `skills/{sif-search,sif-get,sif-cite}` → `sif mcp stdio`
   `server.json` + `scripts/publish_registry.py` → PyPI `docsif` → Registry
```

### Recommended Project Structure (deltas only)

```
src/sif/mcp/
├── app.py            # NEW: composition root (MCPServer, tools, resource, lifespan, mount, runners)
├── tools.py          # NEW: seven @mcp.tool functions + explicit result builder
├── backend.py        # MODIFIED: lazy manager, parity components, lex/vec, citation mapping
├── protocol.py       # MODIFIED: wire types deleted; SIF I/O models + citation fields preserved
├── watch_host.py     # MODIFIED: lifespan composed under session_manager.run()
├── __init__.py       # REWRITTEN: export MCPServer/SearchBackend (or minimal)
├── server.py         # DELETED
├── handlers.py       # DELETED (rewritten as tools.py)
└── transports/       # DELETED (stdio.py, http.py, __init__.py)

.claude-plugin/plugin.json        # NEW
.claude-plugin/marketplace.json   # NEW
.mcp.json                         # NEW
skills/sif-search/SKILL.md        # NEW (MCP-first)
skills/sif-get/SKILL.md           # NEW (MCP-first)
skills/sif-cite/SKILL.md          # NEW (search→get→cite discipline)
server.json                       # NEW
scripts/publish_registry.py       # NEW
```

### Pattern 1: One MCPServer, One Session Manager, One Mount

**What:** Build the `MCPServer` once per process; call `streamable_http_app()` exactly once (it creates `_session_manager` as a side effect); mount it at the parent app root (`app.mount("/", sub)` with inner `streamable_http_path="/mcp"`), after registering `/health`; drive the lifespan with `async with mcp.session_manager.run():`.

**When to use:** Always for `sif mcp http` and `sif mcp daemon`.

**Verified constraints:**
- Calling `streamable_http_app()` twice on one `MCPServer` and mounting the first app orphans its manager; the lifespan then raises `RuntimeError: Task group is not initialized. Make sure to use run().` [VERIFIED: live probe; `session_manager` property returns the last manager].
- Mounting at `/mcp` with the inner default path `/mcp` produces a 307 `/mcp` → `/mcp/`; mounting at the root with inner path `/mcp` serves exactly `/mcp` [VERIFIED: live probe]. SIF's existing clients use `/mcp`, so root-mount is the correct composition.
- `session_manager.run()` enters the SDK lifespan **before** its `yield`, and exits it **after**: observed order `app-enter → SDK lifespan-enter → session-manager-entered` and `lifespan-exit → app-exit` [VERIFIED: live probe]. D-18's ordering is therefore expressible exactly.

**Example:**
```python
# Source: live probe against mcp==2.3.0
@asynccontextmanager
async def _app_lifespan(app: FastAPI):
    async with mcp.session_manager.run():   # enters the SDK lifespan
        watch = start_embedded_watch(db_path)
        try:
            yield
        finally:
            stop_embedded_watch(watch)

app = FastAPI(lifespan=_app_lifespan)
@app.get("/health")
async def health(): return {"status": "ok"}
app.mount("/", mcp.streamable_http_app(
    streamable_http_path="/mcp", json_response=True,
    transport_security=security,
))
```

### Pattern 2: Explicit Result Builder for Dual-Channel Output

**What:** Every tool is annotated with its Pydantic output model (so `outputSchema` is derived) but returns an explicitly constructed `CallToolResult` with `content=[TextContent(text=json_dumps_strict(model_dump_flags))]` and `structured_content=<dict>`.

**Why:** the SDK's automatic channel is not byte-compatible:
- Returning a BaseModel auto-produces text = `pydantic_core.to_json(result, fallback=str, indent=2)` — pretty-printed, no spaces after separators. SIF today emits `json_dumps_strict(output.model_dump(), ensure_ascii=False)` — compact `", "`/`": "` separators [VERIFIED: `handlers.py:127` and live wire probe].
- Returning `list[Hit]` auto-produces **one text block per element**, not a JSON array [VERIFIED: live probe].
- Returning `CallToolResult` passes through unchanged, and the SDK validates `structured_content` against the annotated model (non-error results) [VERIFIED: `convert_result` source + probe].
- A structured tool returning `CallToolResult` **without** conforming `structured_content` yields `isError=True` with generic "Error executing tool <name>" [VERIFIED: probe]. The builder must always supply it for non-error results; error results set `is_error=True` (validation skipped).

**When to use:** All seven tools. Recommended dump flags: mirror each tool's current text dump (`MetadataOutput` uses `exclude_none=True`; others do not); `structured_content` uses `model_dump(mode="json", by_alias=True)` with `exclude_none=True` for `MetadataOutput` only, preserving the frozen Phase 20 envelope.

### Pattern 3: Lazy Embedder, One Thread-Safe Attempt

**What:** `SearchBackend.__init__` keeps only schema init (`db.init_schema(...)`) and settings; construct `EmbeddingManager.from_settings(...)` on the first vector/hybrid need under a `threading.Lock`, call `load_model()`, cache `manager.model` and `manager.get_identity()`, and latch failure so later requests do not retry.

**Verified mechanics:** `EmbeddingManager.from_settings` constructs an `EmbeddingCache`, which creates the cache dir and DB (`mkdir` + `_init_db`) — a side effect that must not run at startup [VERIFIED: `manager.py:61-102`, `cache.py:41-66`]. `load_model()` is **not** thread-safe (plain `if self._model is not None` check) and logs at INFO; `get_identity()` calls `load_model()` and must not be invoked at init [VERIFIED: `manager.py:93-128,225-230`]. With `embedder=None`, `HybridSearcher.search` skips the vector leg, so the BM25 degrade is structural [VERIFIED: `hybrid.py:70-84,130`].

**Degradation contract:** first load failure → one warning, `query` and hybrid continue BM25-only; `vec_search` raises `ToolError` naming the install/model remedy; `lex_search`/`status`/`metadata`/`get`/`multi_get` never construct the manager.

### Pattern 4: Always Pass Explicit Transport Security

**What:** Build `TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=[...], allowed_origins=[...])` at the composition root for every host, loopback or not.

**Verified mechanics:**
- Settings shape: `enable_dns_rebinding_protection: bool = True`, `allowed_hosts: list[str] = []`, `allowed_origins: list[str] = []` [VERIFIED: `mcp/server/transport_security.py:20-40`].
- Host matching: exact value ([including port]) or a `:*` suffix wildcard; Origin: absent is allowed, exact or `:*`. Bad Host → **421** "Invalid Host header"; bad Origin → **403**; POST without `application/json` Content-Type → **400** [VERIFIED: source + live probe].
- Loopback auto-enable happens **only** when `transport_security is None` and `host in ("127.0.0.1","localhost","::1")` [VERIFIED: `lowlevel/server.py:732-753`]. With `host="0.0.0.0"` and no settings, protection is **disabled** — a spoofed Host reached the session handler [VERIFIED: live probe].
- Include bare forms (`127.0.0.1`, `localhost`, `[::1]`) alongside `:*` forms so default-port requests match.

### Pattern 5: Resource Template with RFC 6570 Query Variables

**What:** Register `docs://{doc_id}{?from_line,max_lines}` with defaulted query parameters; the SDK's `UriTemplate` parses `/` and `?` and coerces the annotated parameter types.

**Verified mechanics:** `@mcp.resource("docs://{doc_id}")` with extra function params raises `ValueError: Mismatch between URI parameters ...` [VERIFIED: live probe]. With `{?from_line,max_lines}`, `docs://abc?from_line=2&max_lines=5` matched and passed `from_line=2` as `int` [VERIFIED: live probe]. Resource functions must return `str` or `bytes`; the template's `mime_type` is applied to all reads (per-document mime types are not expressible at the high-level API) [VERIFIED: live probe + `read_resource` source]. `MCPServer.resource(..., security=...)` defaults to `ResourceSecurity(reject_path_traversal=True, reject_absolute_paths=True, reject_null_bytes=True)` [VERIFIED: `MCPServer.__init__` signature].

### Anti-Patterns to Avoid

- **Keeping the hand-rolled server alongside the SDK** — name collision, two state machines, double negotiation (research Anti-Pattern 8; D-01 forbids it).
- **Relying on `MCPServer.run(transport="streamable-http")` for the D-13 flags** — `run()` builds its own uvicorn config; SIF mounts the app so `/health` and CORS can coexist. Use `streamable_http_app()` + uvicorn explicitly.
- **Returning the Pydantic model directly and hoping text stays the same** — verified text formatting and list unrolling diverge.
- **Calling `get_identity()` at backend construction to pre-check the identity** — it loads the model, defeating D-15.
- **Assuming the SDK validates `/health`** — it does not; the mount boundary is the security boundary.
- **Assuming a duplicate Registry publish is idempotent** — the registry rejects an existing name+version (`<name>@<version> already exists`) [VERIFIED: `internal/service/registry_service.go` createServerInTransaction].

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Protocol negotiation / era routing | Version allowlists, handshake state machine | SDK `MCPServer` | SDK routes 2024-11-05 → 2026-07-28; hand-rolling is the debt the phase removes |
| Tool input JSON Schema | Hand-written `input_schema` dicts kept in sync by comments | Function signatures + `Annotated[..., Field(...)]` | Generated schema cannot drift; `Annotated[int, Field(ge=0)]` reproduced `"minimum": 0` [VERIFIED] |
| Tool result serialization | `json.dumps` in each handler + hoping the SDK matches | One `CallToolResult` builder | Two channels must stay exact; SDK auto text is not byte-compatible |
| Host/Origin validation | A new middleware replicating `validate_origin` | `TransportSecuritySettings` | SDK validates before user code on both eras; includes Content-Type |
| stdout redirection in stdio | `os.dup2` by hand | SDK `stdio_server()` fd diversion | Verified: prints after startup land on stderr; zero client parse failures |
| Lazy loading machinery | A new model loader | `EmbeddingManager` + `load_model()` + a `threading.Lock` | Manager already has idempotent load, identity, role methods, cache |
| Query pipeline | A second pipeline implementation for MCP | `SearchPipeline` + `QueryExpansion` + `create_reranker` + `SmartSnippetExtractor` | CLI parity by construction |
| PID file lifecycle | New daemon code | `utils/daemon.py` `detach`/`write_pid_file`/`stop_daemon` | Double-fork + arming + corroborated stop + Windows refusal already proven |
| Plugin manifest validation | A bespoke JSON checker | `claude plugin validate --json` + tiny structural tests | Authoritative schema check, machine-readable |
| Registry publish | A hand-rolled HTTP client | `mcp-publisher publish` + a preflight script | Device-flow auth and schema validation are the CLI's job; the script owns idempotency |

**Key insight:** the SDK supplies every protocol-level behavior; SIF's work is composition, result shaping, and the business-layer parity/lazy/citation changes.

## Runtime State Inventory

> This is a refactor/migration phase (protocol shell replacement + packaging). All five categories are answered explicitly.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| **Stored data** | The SQLite index (documents, FTS, vec0, `index_meta`, `embedded_documents`, `query_log`, `llm_cache`) and the embedding cache carry **no protocol strings** — no rename. New `documents.checksum` reads only (no write). No schema migration in Phase 22. | None. Citation fields are read-only projections. |
| **Live service config** | (1) Claude Code user/project MCP config entries naming a `sif` server (`command: sif`, `args: [mcp, stdio]`) — the phase adds a plugin-provided `.mcp.json` that may duplicate an existing manual entry; users must remove the old manual entry or accept two registrations. (2) Running `sif mcp http`/`sif mcp daemon` processes and in-memory 2025-era sessions — a process restart is required to serve the SDK shell. (3) Plugin cache copies created by `claude plugin marketplace add`/install must be refreshed after version changes. | Document the manual-entry conflict in the plugin install section; restart running servers; re-install/re-enable the plugin after changes. |
| **OS-registered state** | None for MCP: no launchd/systemd unit is generated for `mcp daemon` (unlike `sif watch` service install). The new `<db>.mcp.pid` is the only OS-adjacent artifact; it is removed on graceful exit and on `--stop`. | None beyond implementing `--stop` cleanup. |
| **Secrets and env vars** | No new secret or env var is introduced. Existing `SIF_*` settings are unchanged (`SIF_MCP_HOST`, `SIF_MCP_PORT`, `SIF_MCP_TRANSPORT`, `SIF_MCP_WATCH`, `SIF_RERANK_ENABLED`, prompt names). No Registry credentials are stored (D-24). | None. Do not add Settings fields (D-13). |
| **Build artifacts** | Installed `docsif` wheel/site-packages must be reinstalled to pick up `mcp` as a core dependency; `uv.lock` must be regenerated; the dev environment currently has `mcp==1.27.0` installed transitively — `ty`/tests must run against 2.3.0 after reinstall. The plugin cache and `claude` session state are separate artifacts. | Refresh `uv.lock`; reinstall the dev environment; reconfigure the plugin after the assets land. |

## Common Pitfalls

### Pitfall 1: SDK auto text is not the legacy text
**What goes wrong:** Returning the Pydantic model directly changes the text channel to pretty-printed JSON; a list return becomes multiple text blocks.
**Why:** `_convert_to_content` uses `pydantic_core.to_json(..., indent=2)` and unrolls lists/tuples.
**How to avoid:** Explicit `CallToolResult` builder for all tools (D-05).
**Warning signs:** Golden transcripts show `{\n  "documents": ...` instead of compact `{"documents": ...`; a results array arrives as N text blocks.

### Pitfall 2: `structured_content` validation turns a good result into a generic error
**What goes wrong:** A structured tool returning `CallToolResult` without a conforming `structured_content` yields `isError=True`, text "Error executing tool <name>".
**Why:** `convert_result` validates `result.structured_content` against the annotated output model for every non-error result.
**How to avoid:** Builder always derives `structured_content` from the same model; error paths set `is_error=True`.
**Warning signs:** All tool calls "succeed" but return isError with no internal detail; tests using `MCPServer.call_tool` see the same.

### Pitfall 3: Task group not initialized
**What goes wrong:** `RuntimeError: Task group is not initialized. Make sure to use run().` on the first request.
**Why:** `streamable_http_app()` was never called, or called twice (orphaning the manager), or the FastAPI lifespan does not enter `session_manager.run()`. `httpx` ASGITransport does not run lifespan events.
**How to avoid:** Build one server/app per process; run the parent lifespan in tests (`async with app.router.lifespan_context(app)`); construct the server/app in a factory used once.
**Warning signs:** Unit tests pass with `TestClient` (which runs lifespan) but raw ASGI tests fail; mounting two apps from one server.

### Pitfall 4: Non-loopback bind silently disables DNS-rebinding protection
**What goes wrong:** `SIF_MCP_HOST=0.0.0.0` with no explicit settings → Host validation off entirely.
**Why:** auto-enable is gated on `host in (127.0.0.1, localhost, ::1)`.
**How to avoid:** Always pass explicit `TransportSecuritySettings`; warn when non-loopback and no `--allowed-hosts` (D-13).
**Warning signs:** Spoofed Host reaches the session handler (400 missing session, not 421).

### Pitfall 5: `/health` is outside the SDK security boundary
**What goes wrong:** A bad Host still returns 200 on `/health` [VERIFIED].
**Why:** `/health` is a FastAPI route, not part of the mounted SDK app.
**How to avoid:** Add a narrow Host guard dependency/middleware for `/health` sharing the allowlist, or accept and document the deviation (see Conflicts §C2).
**Warning signs:** Transport-security tests cover `/mcp` only.

### Pitfall 6: Host rejection is 421, not 403
**What goes wrong:** Tests asserting 403 for a bad Host fail.
**Why:** the SDK returns 421 Misdirected Request for Host and 403 for Origin.
**How to avoid:** Assert 421 for Host (or assert `>= 400` with the exact code documented); record the deviation from D-14's wording.
**Warning signs:** A "passing" security test that only checks `status_code != 200`.

### Pitfall 7: `mcp daemon --stop` never signals the daemon
**What goes wrong:** `stop_daemon` classifies a live MCP daemon as `stale` and removes its PID file without signalling.
**Why:** `corroborate_pid` requires the literal `watch` token in the ps command line; `sif mcp daemon` has no `watch` token [VERIFIED: `daemon.py:58,217`].
**How to avoid:** Parameterize the corroboration marker by the payload's `mode` (`"daemon"` → `watch`, `"mcp"` → `mcp`) and add `pid_path_for_mcp`.
**Warning signs:** `mcp daemon --stop` prints "not running"/"stale" while the process lives; a second daemon fails to bind.

### Pitfall 8: Pre-run stdout corrupts the stdio stream
**What goes wrong:** The client logs "Failed to parse JSONRPC message ... Invalid JSON" for startup noise.
**Why:** the SDK diverts fd 1 → fd 2 only when `stdio_server()` enters; anything printed before `mcp.run()` goes to the real stdout. Verified: a print before `mcp.run()` was parsed as a frame; prints inside the lifespan and tools went to stderr with zero parse failures [VERIFIED: live stdio probe]. SIF has a real pre-run printer: `main()` prints the legacy model-cache migration message to stdout (`cli/main.py:292`, `console` at :26).
**How to avoid:** `set_quiet(True)` + no stdout writes before `mcp.run`; construct the backend inside the SDK lifespan (post-diversion); the purity regression runs the real `sif mcp stdio` subprocess with the migration fixture present.
**Warning signs:** A cold-first-query test that mocks the embedder passes while a real run fails.

### Pitfall 9: Eager identity read defeats lazy loading
**What goes wrong:** `get_identity()` at backend init loads the model (it calls `load_model()`), so `status` starts a model load.
**Why:** Phase 21's identity API assumes a loaded model.
**How to avoid:** Call `get_identity()` only after a successful `_ensure_embedder()`.
**Warning signs:** `status` triggers "Loading embedding model" in the log; startup latency jumps.

### Pitfall 10: Concurrent first queries race the load
**What goes wrong:** Two threads both construct the model; the second overwrites the first; identity/model mismatch; duplicated downloads.
**Why:** `load_model()` has no lock.
**How to avoid:** A backend `threading.Lock` around construction + load + identity; latch failure.
**Warning signs:** Duplicate "Loading embedding model" logs at startup under parallel requests.

### Pitfall 11: Resource query parameters rejected at decoration time
**What goes wrong:** `ValueError: Mismatch between URI parameters {'doc_id'} and function parameters {'doc_id','from_line','max_lines'}`.
**Why:** the resource decorator requires exact template-variable parity and defaults for query variables.
**How to avoid:** `docs://{doc_id}{?from_line,max_lines}` with `= None` defaults [VERIFIED].
**Warning signs:** Import-time failure in `app.py`.

### Pitfall 12: `claude plugin validate --strict` fails on a repo-root CLAUDE.md
**What goes wrong:** `--strict` exits 1 with "CLAUDE.md at the plugin root is not loaded as project context" (plus a marketplace-description warning if omitted).
**Why:** SIF's repo root is both the project and the plugin root (D-22) and contains `CLAUDE.md` [VERIFIED: local `claude plugin validate --strict` run, exit 1].
**How to avoid:** Gate on plain `claude plugin validate .` (exit 0, warnings) + `--json` `success:true` and zero `errors`; add a marketplace `description`; document the tolerated CLAUDE.md warning (Conflicts §C4).
**Warning signs:** CI uses `--strict` and fails on a repository file that cannot be removed.

### Pitfall 13: Duplicate Registry publish is an error, not a no-op
**What goes wrong:** A second `--publish` for a listed version exits non-zero with "already exists".
**Why:** the registry rejects an existing name+version [VERIFIED: registry source].
**How to avoid:** Preflight `GET /v0.1/servers/{urlencoded-name}/versions/{version}`; if 200, print "already listed" and exit 0 without invoking `mcp-publisher` (D-24).
**Warning signs:** The script shells out unconditionally.

### Pitfall 14: Frozen metadata envelope gains `null`s
**What goes wrong:** `filteredDocuments: null` appears in structuredContent when no filter was supplied.
**Why:** the SDK dumps with `by_alias=True` but not `exclude_none`.
**How to avoid:** Builder passes `exclude_none=True` for `MetadataOutput` (matches `handlers.py:301`), so the frozen envelope is preserved in both channels.
**Warning signs:** Envelope deep-equality tests fail only on null keys.

### Pitfall 15: `outputSchema`/`structuredContent` appear even on 2024-era responses
**What goes wrong:** A strict 2024-era client rejects unknown fields.
**Why:** the SDK does not gate these fields per era [VERIFIED: 2024 wire probe included `outputSchema` in `tools/list` and `structuredContent` in `tools/call`].
**How to avoid:** Accept as SDK behavior; the real-client matrix (Claude Code) is the proof. Keep text content so legacy parsers ignore the extra key.
**Warning signs:** Transcript normalization silently drops the fields and hides the contract.

## Code Examples

Verified patterns from the installed SDK and live probes.

### Minimal composition root (verified imports and behavior)
```python
# Verified against mcp==2.3.0 on Python 3.10.22
from contextlib import asynccontextmanager
from fastapi import FastAPI
from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from mcp.server.mcpserver.exceptions import ToolError

SECURITY = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=["127.0.0.1", "127.0.0.1:*", "localhost", "localhost:*", "[::1]", "[::1]:*"],
    allowed_origins=["http://localhost:3000", "http://127.0.0.1:*", "http://localhost:*"],
)
```

### Explicit dual-channel builder (verified)
```python
# Verified: CallToolResult passes through convert_result unchanged;
# structured_content must conform to the annotated model.
def _result(output: BaseModel, *, exclude_none: bool = False) -> CallToolResult:
    text = json_dumps_strict(output.model_dump(exclude_none=exclude_none), ensure_ascii=False)
    structured = output.model_dump(mode="json", by_alias=True, exclude_none=exclude_none)
    return CallToolResult(content=[TextContent(type="text", text=text)], structured_content=structured)

@mcp.tool(
    name="metadata",
    description=METADATA_DESCRIPTION,
    annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False),
)
async def metadata(...) -> MetadataOutput:
    return _result(output, exclude_none=True)  # type: ignore[return-value]
```

### Tool argument constraints (verified)
```python
# Annotated[int, Field(ge=0)] produced {"minimum": 0, "default": 0, ...} in inputSchema.
def query(
    query: str,
    limit: Annotated[int, Field(ge=1)] = 10,
    offset: Annotated[int, Field(ge=0)] = 0,
    ...
) -> QueryOutput: ...
```

### Era matrix (verified requests)
```python
# 2024-11-05 / 2025-03-26 / 2025-06-18 / 2025-11-25:
POST /mcp {"jsonrpc":"2.0","id":1,"method":"initialize","params":{
  "protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"...","version":"..."}}}
#   -> 200 JSON; result.protocolVersion echoes the requested revision; mcp-session-id header set.
# Subsequent calls carry mcp-session-id.

# 2026-07-28 (stateless, no initialize):
headers = {"MCP-Protocol-Version": "2026-07-28", "Mcp-Method": "tools/call", "Mcp-Name": "status"}
body = {"jsonrpc":"2.0","id":12,"method":"tools/call","params":{
  "name":"status","arguments":{},
  "_meta":{
    "io.modelcontextprotocol/protocolVersion":"2026-07-28",
    "io.modelcontextprotocol/clientCapabilities":{},
    "io.modelcontextprotocol/clientInfo":{"name":"probe","version":"1"}}}}
#   -> 200 JSON; result has resultType/ttlMs/cacheScope; no mcp-session-id.
# Missing Mcp-Name -> -32020 header mismatch; missing _meta -> -32602.
```

### SDK client matrix (verified)
```python
from mcp import Client
# In-process protocol tests:
async with Client(mcp_server, mode="legacy") as c:   # negotiates 2025-11-25
    await c.list_tools(); await c.call_tool("status", {})
async with Client(mcp_server, mode="auto") as c:     # negotiates 2026-07-28
    ...

# Real HTTP client over in-process ASGI (no sockets):
class AsgiTransport:  # wraps streamable_http_client(url, http_client=httpx2.AsyncClient(transport=ASGITransport(app)))
    ...
async with Client(AsgiTransport(app, "http://testserver/mcp"), mode="legacy") as c: ...
```

### Resource registration (verified)
```python
@mcp.resource(
    "docs://{doc_id}{?from_line,max_lines}",
    name="document",
    mime_type="text/markdown",  # template-level; cannot vary per document
)
def read_doc(doc_id: str, from_line: int | None = None, max_lines: int | None = None) -> str:
    ...
```

### Stdio host (verified)
```python
mcp.run(transport="stdio")   # SDK diverts fd 1 -> fd 2 when the transport starts
```

### Daemon arm + stop (existing contract)
```python
# Existing watch precedent (src/sif/cli/commands/watch.py:345-407):
outcome = daemon.detach(log_path, arm)
if outcome.daemon:
    try:
        run_http_host(...)          # bind happens after arming
    finally:
        daemon.remove_pid_file(pid_file)
```
```python
# Required addition: marker-aware corroboration
_PID_SUFFIX_MCP = ".mcp.pid"
_MODE_MARKERS = {"daemon": "watch", "mcp": "mcp"}
def corroborate_pid(payload, *, marker: str = "watch") -> bool: ...
def stop_daemon(pid_path, *, marker: str | None = None, ...): ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hand-rolled JSON-RPC hardcoded `2024-11-05` (`server.py:71`) | SDK `MCPServer` serving 2024-11-05…2026-07-28 + stateless | SDK v2.0.0 (2026-07-28); 2.3.0 current | Delete ~623 LOC; negotiate all eras for free |
| `FastMCP` import path | `mcp.server.MCPServer` (`mcp.server.mcpserver`) | v2 | Old path raises `ModuleNotFoundError`; no codemod applies to hand-rolled code |
| Text-only tool results | `structuredContent` + `outputSchema` + text | Spec 2025-06-18; loosened 2026-07-28 | Citation-grade agent output; text retained for legacy |
| Origin-only middleware | SDK `transport_security` Host+Origin | 2025-11-25 spec (Origin 403 MUST) | DNS-rebinding defense from the SDK |
| Eager embedder at MCP startup (`backend.py:145-177`) | Lazy manager on first vector need | Phase 22 | Fast, quiet startup; BM25-only hosts never load a model |
| `sif mcp daemon` stub (`cli/commands/mcp.py:109-129`) | Real detached HTTP daemon | Phase 22 | Persistent agent server with its own PID |
| CLI-only distribution | Plugin + marketplace + Registry | Phase 22 | Agent-native install/discovery |

**Deprecated/outdated:**
- `mcp.server.fastmcp` (removed in v2); `mount_path=`; `streamablehttp_client` import path; `except httpx.*` around MCP calls (httpx replaced by httpx2).
- `ToolError` imported from `mcp.types` (it lives at `mcp.server.mcpserver.exceptions`).

## Assumptions Log

> Every row in this table is an `[ASSUMED]` claim. The planner and discuss-phase use this section to identify decisions that need user confirmation before execution.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `uvx --from ${CLAUDE_PLUGIN_ROOT} sif mcp stdio` builds the plugin cache copy of the repo successfully | D-23 docs | The zero-install fallback needs a different command; docs fix only |
| A2 | `mcp-publisher` device-flow login and the live publish succeed for `io.github.zhangtaolab/sif` 1.1.2 | MCP-09 / D-24 | Listing blocked; maintainer checkpoint and recorded command mitigate |
| A3 | The real Claude Code smoke (`claude mcp` lists seven tools + one `query`) passes with the installed plugin | D-04 | A client-compat gap found late; the SDK client matrix still passes |
| A4 | The full test suite passes on Python 3.10 after adding `mcp` (only install/import was proven this session) | MCP-01 | A 3.10-specific failure needs a fix before the phase gate |
| A5 | The seam's SUS verdict on `mcp` is driven only by missing PyPI download data, not risk | Package audit | A real supply-chain concern; the human checkpoint covers it |
| A6 | A marker-aware `corroborate_pid` fully restores `--stop` for the MCP daemon | Daemon plan | `--stop` remains broken; tests catch it |
| A7 | Per-document resource MIME types are not expressible at the high-level API (probe returned JSON-encoded `TextResourceContents`) | D-09 | A low-level custom resource path could restore them at extra cost |
| A8 | `mcp` 2.3.0 will be the resolved version after `uv lock` (pin allows later 2.x) | Standard stack | A later 2.x changes behavior; the pin is `<3` and golden tests catch drift |

## Open Questions

1. **serverInfo name**: keep `sif-mcp-server` (current wire value) or use `sif` (plugin/marketplace identity)?
   - What we know: `MCPServer(name=...)` defaults to `"mcp-server"`; current SIF sends `"sif-mcp-server"` [VERIFIED: `protocol.py:115-117`].
   - Recommendation: pass `"sif-mcp-server"` for wire continuity; the plugin name remains `sif`.

2. **`/health` Host validation**: narrow parent-level guard vs documented deviation (D-14 says "subject to Host validation"; the SDK mount does not cover it).
   - Recommendation: a tiny `/health` dependency sharing the allowlist, tested with a spoofed Host.

3. **`lex_search`/`vec_search` `min_score` parity**: the declared inputs lack `min_score` while CLI `search`/`vsearch` have `--min-score`.
   - Recommendation: add `min_score` (additive field) to both inputs for full parity; otherwise document the gap.

4. **Resource MIME type**: one template-level type for all documents.
   - Recommendation: `text/markdown` (Markdown-first corpus) or `text/plain` (truthful for all); document the choice.

5. **`--allowed-hosts` syntax**: repeatable vs comma-separated (D-13 leaves it to the planner).
   - Recommendation: repeatable (`multiple=True`) like `--cors-origins`, for consistency.

6. **Daemon PID payload `depth`**: `read_pid_file` requires a string `depth`.
   - Recommendation: write `depth="bm25"` (the serving depth concept) or `"http"`; document the choice.

7. **structuredContent `exclude_none` policy outside metadata**: mirror each tool's text flags vs always schema-complete.
   - Recommendation: text mirrors today exactly; structuredContent uses `exclude_none=True` only for `MetadataOutput` (frozen envelope), full nulls elsewhere.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10 | D-02 gate, CI floor | Yes | 3.10.22 (uv-managed) | — |
| `uv` | lock/install/venv | Yes | 0.13.7 | pip |
| `mcp` | the whole phase | Yes (scratch venv) | 2.3.0 | — |
| FastAPI / Starlette / uvicorn | parent app | Yes | lock 0.136.0 / 1.0.0 / 0.44.0 | — |
| `httpx2` | SDK client + ASGI tests | Yes (with mcp) | 2.14.0 on py3.10 | Raw ASGI helper without httpx2 |
| `httpx` | existing `fastapi.testclient` tests | Yes (dev env) | 0.28.1 | — |
| `claude` CLI | plugin validate gate | Yes | 2.1.325 | Structural tests only; gate manual |
| `mcp-publisher` | Registry publish | **No** | — | `brew install mcp-publisher`; live publish is a checkpoint |
| Network access to PyPI/registry | preflight | Yes | — | `--check` reports the unreachable check as a failure |

**Missing dependencies with no fallback:** none that block planning. **Missing with fallback:** `mcp-publisher` (install step + maintainer checkpoint).

## Validation Architecture

> Included because `.planning/config.json` does not set `workflow.nyquist_validation: false`.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.x + pytest-asyncio (explicit `@pytest.mark.asyncio` markers), coverage `fail_under = 90` [VERIFIED: `pyproject.toml:222-225`] |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]`; no separate pytest.ini |
| Quick run command | `pytest tests/unit/mcp -x -q` |
| Full suite command | `pytest` (with `ruff check src tests`, `ruff format --check src tests`, `ty check src/sif`) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| MCP-01a | 2024-11-05 handshake + tools/list + status call; session header set | integration (raw JSON-RPC over ASGI) | `pytest tests/unit/mcp/test_wire_transcripts.py -q` | ❌ Wave 0 |
| MCP-01b | 2025-06-18 and 2025-11-25 handshakes negotiate their version | integration | same | ❌ Wave 0 |
| MCP-01c | 2026-07-28 stateless request: no init, header + `_meta`, no session; missing `Mcp-Name`/`_meta` rejected | integration | same | ❌ Wave 0 |
| MCP-01d | SDK client `legacy`/`auto` over in-process + ASGI + stdio | integration | `pytest tests/unit/mcp/test_sdk_clients.py -q` | ❌ Wave 0 |
| MCP-01e | py3.10 install/import smoke | manual/CI | `uv venv --python 3.10 ... && uv pip install -e . mcp==2.3.0 && python -c "from mcp.server import MCPServer; import sif.mcp.app"` | ✅ (performed; app module pending) |
| MCP-02 | Seven tools registered; every `read_only_hint=True`, `open_world_hint=False`, hints omitted; descriptions match constants; no rerank overclaim | unit | `pytest tests/unit/mcp/test_tools.py -q` | ❌ Wave 0 |
| MCP-03 | `outputSchema` present; `structuredContent` unwrapped; metadata envelope deep-equals; text compact and parses; citation fields present | unit | `pytest tests/unit/mcp/test_citations.py -q` | ❌ Wave 0 |
| MCP-04 | Bad Host → 421, bad Origin → 403, allowed → 200; missing Origin allowed; `/health` policy | unit | `pytest tests/unit/mcp/test_transport_security.py -q` | ❌ Wave 0 |
| MCP-05 | Query expansion parity; rerank None/True/False; lex/vec direct paths enrich once; identity mismatch marks results | unit | `pytest tests/unit/mcp/test_backend.py tests/unit/mcp/test_tools.py -q` | ✅ partial (adapt) |
| MCP-06 | No model load for status/lex/metadata/get/multi_get; one load for query/vec; failure degrades; all stdout lines JSON-RPC on cold first query | unit + integration | `pytest tests/unit/mcp/test_lazy_embedder.py tests/unit/mcp/test_stdout_purity.py -q` | ❌ Wave 0 |
| MCP-07 | `mcp daemon` arms `<db>.mcp.pid`, serves `/mcp`, `--stop` stops only MCP, Windows refusal, bind failure cleanup | unit + e2e (POSIX) | `pytest tests/unit/mcp/test_daemon.py -q` | ❌ Wave 0 |
| MCP-08 | `plugin.json`/`marketplace.json`/`.mcp.json` parse; three skills with frontmatter; `sif-cite` contains the search→get→cite rule; `claude plugin validate --json` success + zero errors (skip if CLI absent) | unit + CLI gate | `pytest tests/unit/mcp/test_plugin.py -q` + `claude plugin validate --json .` | ❌ Wave 0 |
| MCP-09 | `--check` validates marker/PyPI/server.json/registry; duplicate version → "already listed" exit 0; mismatch/404 refuse | unit (mocked HTTP) | `pytest tests/unit/mcp/test_registry_script.py -q` + `python scripts/publish_registry.py --check` | ❌ Wave 0 |
| D-11 | CLI JSON byte-identical (`SearchResult.to_dict()` unchanged); no line fields in CLI output | unit | `pytest tests/unit/cli tests/unit/search -q` | ✅ existing |
| D-25 | Docs-generate gate clean | CLI | `make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md` | ✅ existing |

### Sampling Rate

- **Per task commit:** `pytest tests/unit/mcp -x -q` plus `ruff check src tests`
- **Per wave merge:** full `pytest` (fail_under=90), `ruff format --check src tests`, `ty check src/sif`
- **Phase gate:** full suite green, `make docs-generate` clean, `claude plugin validate --json .` success with zero errors, `python scripts/publish_registry.py --check` green, and the recorded Claude Code smoke.

### Wave 0 Gaps

- [ ] `tests/unit/mcp/test_app.py` — composition root, mount path, `/health`, lifespan/session-manager wiring
- [ ] `tests/unit/mcp/test_tools.py` — seven tools, annotations, descriptions, ToolError mapping, arg constraints
- [ ] `tests/unit/mcp/test_wire_transcripts.py` — era matrix + golden transcripts with normalization
- [ ] `tests/unit/mcp/test_sdk_clients.py` — legacy/auto clients over in-process, ASGI, stdio
- [ ] `tests/unit/mcp/test_transport_security.py` — spoofed Host/Origin matrix + `/health`
- [ ] `tests/unit/mcp/test_lazy_embedder.py` — no-load/one-load/failure/lock
- [ ] `tests/unit/mcp/test_stdout_purity.py` — cold first query subprocess capture
- [ ] `tests/unit/mcp/test_citations.py` — snippet window lines, content_hash, get ranges, envelope parity
- [ ] `tests/unit/mcp/test_daemon.py` — PID path/payload, arm, stop marker, Windows, bind failure
- [ ] `tests/unit/mcp/test_plugin.py` — manifests, skills, optional CLI validate
- [ ] `tests/unit/mcp/test_registry_script.py` — preflight branches
- [ ] Rewrite `tests/unit/mcp/test_integration.py`; delete `test_server.py`, `test_transports_http.py`, `test_transports_stdio.py`
- [ ] Adapt `test_backend.py` (87 tests) and keep `test_mcp_watch_host.py` (15 tests) intact

## Security Domain

> `security_enforcement` is not disabled in config; this section is required.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Loopback single-user server; OAuth rejected as an anti-feature. SDK auth scaffolding is unused |
| V3 Session Management | Yes (2025-era only) | SDK session manager: server-minted `Mcp-Session-Id`, `max_sessions` 10000, `session_idle_timeout` 1800s; 2026 era is stateless (no session) [VERIFIED: signatures] |
| V4 Access Control | Yes | Seven read-only tools; annotations truthful; no mutation surface; Host/Origin allowlists; `/health` guard |
| V5 Input Validation | Yes | Pydantic arg models + `Annotated` constraints; `QueryInput` validators preserved in handlers; `parse_filter`/`parse_match` AST budgets (depth 8, 64 nodes, 1024-char strings, 128-element arrays); SDK `ResourceSecurity` path-traversal/absolute-path/null-byte rejection on template params |
| V6 Cryptography | No hand-rolled crypto | Content hashes are existing sha256 checksums; no new cryptographic primitive. SDK TLS (truststore) is outbound-only and unused by SIF |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| DNS rebinding against the loopback HTTP server | Spoofing | `TransportSecuritySettings` Host 421 / Origin 403; never `transport_security=None`; non-loopback requires explicit `--allowed-hosts` |
| False `read_only_hint` on a write-capable tool | Elevation of privilege | Only read-only tools registered; honesty test enumerates annotations; future write tools require `read_only_hint=False` + `destructive_hint=True` |
| Filter AST SQL injection | Tampering | Parameterized predicates only; no string interpolation (Phase 20 contract) |
| Path traversal via `docs://{doc_id}` | Tampering | SDK `ResourceSecurity` rejects `..`, absolute paths, null bytes; the backend resolves by id/path through the repository, not the filesystem |
| stdout corruption of the JSON-RPC channel | Denial of service | SDK fd diversion + forced quiet + cold-first-query purity regression |
| PID-file tampering / signalling the wrong process | Spoofing / DoS | 0600 write-temp-rename; fail-closed corroboration with a mode-aware marker |
| Registry credential leakage | Information disclosure | `mcp-publisher` device flow; the script never stores credentials |
| Annotation-driven auto-approval claims | Repudiation / misleading | Never claim prompt-free execution; docs state parallel read-only + one retry only |

## Plan Decomposition

Seven plans, tracer-first, six waves. File scopes are disjoint within a wave; `.` = repo root.

### Wave 1
**22-01 — Tracer: SDK composition root, py3.10 gate, dual-era proof, shell deletion**
- Files: `pyproject.toml`, `uv.lock`, `src/sif/mcp/app.py` (new), `src/sif/mcp/tools.py` (new; `status` only + shared builder + security settings), `src/sif/mcp/protocol.py` (delete JSON-RPC/wire types 18-194; keep I/O models), `src/sif/mcp/__init__.py` (rewrite), delete `src/sif/mcp/server.py`, `src/sif/mcp/handlers.py`, `src/sif/mcp/transports/`; `src/sif/mcp/cli.py`; `src/sif/cli/commands/mcp.py` (stdio/http only); `src/sif/mcp/backend.py` (lazy-load skeleton + lock; remove eager factory call); `src/sif/mcp/watch_host.py` (compose under session manager via helper); tests: delete `test_server.py`, `test_transports_http.py`, `test_transports_stdio.py`; rewrite `test_integration.py` as `test_wire_transcripts.py`; add `test_app.py`, `test_sdk_clients.py`, `test_transport_security.py` (baseline), `test_stdout_purity.py` (baseline).
- Depends: none. **Checkpoint:** package-legitimacy human verify before install; py3.10 smoke recorded (already performed).
- Gate: all four handshake revisions + 2026 stateless probe; `status` over stdio + HTTP; watch starts/stops under the SDK lifespan; old shell absent; ruff/ty.

### Wave 2 (parallel)
**22-02 — Tool surface: six remaining tools, annotations, descriptions, ToolError semantics**
- Files: `src/sif/mcp/tools.py`, `src/sif/mcp/backend.py` (lex/vec methods), `src/sif/mcp/protocol.py` (additive `min_score` if Q3 accepted), tests `test_tools.py`, adapt `test_backend.py`.
- Depends: 22-01.

**22-03 — Transport-security CLI surface, `/health` guard, real daemon**
- Files: `src/sif/mcp/app.py` (health guard), `src/sif/cli/commands/mcp.py` (`--allowed-hosts`, `--cors-origins` on daemon, real daemon), `src/sif/mcp/cli.py` (daemon runner), `src/sif/utils/daemon.py` (`pid_path_for_mcp`, marker-aware corroboration), tests `test_transport_security.py` (full), `test_daemon.py`.
- Depends: 22-01.

### Wave 3
**22-04 — Query parity, lazy degradation, stdout purity**
- Files: `src/sif/mcp/backend.py` (manager, expander/reranker/snippets, per-request pipeline, identity closure, lex/vec direct paths, one warning), `src/sif/mcp/app.py` (`set_quiet`), tests `test_lazy_embedder.py`, `test_stdout_purity.py` (full), parity tests in `test_backend.py`.
- Depends: 22-02.

### Wave 4
**22-05 — Citation-grade structured output**
- Files: `src/sif/search/snippets.py` (range-returning extraction), `src/sif/search/hybrid.py` (assign line fields in `_apply_snippets`), `src/sif/core/models.py` (line fields not in `to_dict`), `src/sif/mcp/protocol.py` (MCP `SearchResult`/`Document` citation fields), `src/sif/mcp/tools.py` (builder flags), `src/sif/mcp/backend.py` (mapping + get/multi_get ranges + batched checksums), `src/sif/database/repositories.py` (batch checksum lookup), tests `test_citations.py` + metadata envelope parity.
- Depends: 22-04 (snippet window wired), 22-02.

### Wave 5
**22-06 — Claude Code plugin, marketplace, skills, docs**
- Files: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.mcp.json`, `skills/sif-search/SKILL.md`, `skills/sif-get/SKILL.md`, `skills/sif-cite/SKILL.md`, `README.md` (plugin section), `docs/mcp-server.md` (rewrite), `src/sif/mcp/README.md` (rewrite/redirect), `tests/unit/mcp/test_plugin.py`.
- Depends: 22-02/22-04 final tool surface.

### Wave 6
**22-07 — Registry listing, docs-generate, phase gate**
- Files: `server.json`, `scripts/publish_registry.py`, `tests/unit/mcp/test_registry_script.py`, `README.md` (registry section), `docs/mcp-server.md` (registry section), generated `docs/cli-reference.md`, phase gate + SUMMARY.
- Depends: 22-06 (README/docs sequential). **Checkpoint:** live `mcp-publisher` login/publish (maintainer).
- Gate: full suite + coverage, ruff/format/ty, `make docs-generate` clean, `claude plugin validate --json .`, `publish_registry.py --check`, recorded Claude Code smoke.

## Conflicts Between Verified SDK/External Behavior and CONTEXT D-01..D-25

> Reported, not silently changed. Each item needs a planner note or a user decision; none invalidates the phase.

- **C1 — D-14 Host status code.** D-14 says bad `Host` → 403. The SDK returns **421 Misdirected Request** for Host and **403** for Origin [VERIFIED: live probe + `transport_security.py:110-140`]. Options: (a) accept 421 and record the deviation (recommended — 421 is the correct semantic and the rejection outcome is identical); (b) add a response-mapping middleware 421→403 (nonstandard, no security gain); (c) amend D-14's wording. Recommendation: (a) + test asserts 421.
- **C2 — D-14 `/health` Host validation.** The SDK mount does not cover FastAPI routes; a bad Host on `/health` returned **200** [VERIFIED]. Options: (a) add a narrow `/health` Host guard sharing the allowlist (satisfies D-14 literally; small hand-rolled check); (b) accept and document that `/health` returns only a static status and is not Host-validated. Recommendation: (a).
- **C3 — D-08 "unexpected exceptions … sanitized to `-32603`".** On the high-level `MCPServer` path, an unexpected exception becomes an `isError=True` tool result whose text is `"Error executing tool <name>"` (no internal detail); it is **not** a JSON-RPC -32603 error [VERIFIED: live probe]. The security intent (sanitization) holds; the mechanism differs. Recommendation: keep D-08's ToolError policy and update the wording/golden tests.
- **C4 — D-22 `claude plugin validate` gate.** Plain validate exits 0 with warnings; `--strict` exits 1 because the repo-root plugin contains `CLAUDE.md` ("CLAUDE.md at the plugin root is not loaded as project context") and, without a marketplace description, a marketplace warning [VERIFIED: Claude Code 2.1.325]. `--profile directory` exits 0 once the root README exists. Recommendation: gate on exit 0 + `--json` `success:true` + zero `errors`; add `description` to `marketplace.json`; document the tolerated CLAUDE.md warning. Do not use `--strict`.
- **C5 — D-20 "add only an MCP PID-path helper".** `corroborate_pid` hardcodes the `watch` token [VERIFIED: `daemon.py:58,217`], so `stop_daemon` would treat a live MCP daemon as stale. The daemon module must also gain a mode-aware corroboration marker. Recommendation: add it (small, backward-compatible default `watch`).
- **C6 — D-24 "second `--publish` … exits 0 with 'already listed'".** The registry rejects a duplicate name+version (`<name>@<version> already exists`) [VERIFIED: registry source], and `mcp-publisher` surfaces it as an error. The "already listed" behavior must be implemented **in the script** via a pre-publish registry lookup. Recommendation: implement exactly that; never rely on the publisher for idempotency.
- **C7 — D-05 auto-wrap.** Confirmed as anticipated: auto text differs (indent=2; list unrolling). The explicit builder is required; no decision change needed.
- **C8 — D-10 "the SDK derives structuredContent from the return annotation".** True, but with `model_dump(mode="json", by_alias=True)` and **no** `exclude_none`; the frozen metadata envelope needs the builder's `exclude_none=True`. Recommendation: builder path for metadata (D-10 already allows "if the SDK's auto text differs, use the D-05 builder").
- **C9 — D-01 "migrate one tool first".** Consistent, but note the SDK emits `outputSchema`/`structuredContent` even on 2024-era responses [VERIFIED]; the golden transcripts must record this and the real-client matrix is the compatibility proof.
- **C10 — Package legitimacy.** `mcp` is flagged **SUS** by the seam (`unknown-downloads`). The dependency is locked by D-03; per protocol a `checkpoint:human-verify` must precede the install task. Recommendation: one checkpoint on 22-01.

## Sources

### Primary (HIGH confidence)
- `/tmp/sif-mcp310-venv` (Python 3.10.22, `mcp==2.3.0`, `mcp-types==2.3.0`, project installed with `uv pip install -e .`): live import, API signature, era matrix, structured output, tool annotations, ToolError, resource template, transport security, cache hints, stdio/stdout, lifespan ordering probes (all commands and outputs recorded inline above)
- Installed SDK source: `mcp/server/mcpserver/server.py`, `mcp/server/mcpserver/tools/base.py`, `mcp/server/mcpserver/utilities/func_metadata.py`, `mcp/server/mcpserver/resources/*`, `mcp/server/transport_security.py`, `mcp/server/caching.py`, `mcp/server/lowlevel/server.py`, `mcp/server/stdio.py`, `mcp/client/client.py`, `mcp/client/streamable_http.py`, `mcp/shared/inbound.py`, `mcp_types/version.py`, `mcp_types/_types.py`, `mcp_types/methods.py`
- PyPI JSON: `mcp` 2.3.0 (MIT, `Requires-Python >=3.10`, 73 releases since 2024-11-20); `docsif` 1.1.2 (`>=3.10`, README marker present in the description)
- Registry source: `modelcontextprotocol/registry` `internal/service/registry_service.go` (duplicate version → `ErrInvalidVersion: <name>@<version> already exists`), `cmd/publisher/commands/publish.go` (accepts 200/201), `docs/reference/api/openapi.yaml` (`POST /v0.1/publish`, GET version endpoints)
- In-repo at HEAD `3a3c4ef`: `src/sif/mcp/{backend,protocol,handlers,server,watch_host,cli}.py`, `src/sif/mcp/transports/{http,stdio}.py`, `src/sif/cli/commands/{mcp,watch,search}.py`, `src/sif/cli/main.py`, `src/sif/utils/{daemon,logging}.py`, `src/sif/search/{hybrid,snippets,expansion,rerank}.py`, `src/sif/core/models.py`, `src/sif/embedding/{manager,cache,factory,embedder}.py`, `src/sif/database/{repositories,schema}.py`, `src/sif/config/settings.py`, `pyproject.toml`, `uv.lock`, `tests/unit/mcp/*`, `tests/test_docs.py`, `Makefile`, `.github/workflows/docs.yml`

### Secondary (MEDIUM confidence)
- `https://code.claude.com/docs/en/plugins-reference` — manifest fields, `.mcp.json`, `${CLAUDE_PLUGIN_ROOT}`, standard layout, validation messages
- `https://code.claude.com/docs/en/plugins/marketplace-reference` — marketplace fields, `source: "./"`, strict mode
- `https://code.claude.com/docs/en/skills` — SKILL.md frontmatter, plugin skill discovery, description truncation at 1536 chars
- `https://modelcontextprotocol.io/registry/quickstart` + `/registry/package-types` — `server.json` schema 2025-12-11, PyPI `mcp-name` marker boundary rules, `mcp-publisher` flow, verification endpoint

### Tertiary (LOW confidence — do not cite as fact)
- `uvx --from ${CLAUDE_PLUGIN_ROOT}` behavior (untested)
- `mcp-publisher` live login/publish (not installed; device flow not exercised)
- Real Claude Code plugin smoke (not run; D-04 checkpoint)

## Metadata

**Method note (confidence seam):** `gsd-tools query classify-confidence` returns `LOW` for every channel (`local`, `webfetch`, `websearch` in this runtime), so the seam cannot discriminate evidence quality here. Following the milestone-research precedent recorded in `.planning/research/STACK.md`, provenance tags are assigned on evidence quality instead: live execution in the scratch venv and direct source reads are `[VERIFIED: ...]`; official documentation reads are `[CITED: ...]`; untested flows are `[ASSUMED]`. Every `[VERIFIED]` claim is backed by a recorded command/output or a file:line quote in this document.

**Confidence breakdown:**
- Standard stack: HIGH — install/import/resolution verified on the 3.10 floor; versions read from PyPI/installed metadata
- Architecture: HIGH — every integration claim read at file:line; composition/lifespan/mount behavior probed live
- Pitfalls: HIGH — all SDK pitfalls reproduced in probes; in-repo pitfalls read from source
- Packaging/registry: MEDIUM — official docs read and `claude plugin validate` exercised; live publish not attempted

**Research date:** 2026-11-16
**Valid until:** 2027-01-15 for the SDK pin (2.x fast-moving; re-check `mcp` release notes before execution) and 30 days for the preview Registry (schema/flow may change)

## RESEARCH COMPLETE
