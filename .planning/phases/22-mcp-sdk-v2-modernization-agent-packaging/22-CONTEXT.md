# Phase 22: MCP SDK v2 Modernization + Agent Packaging - Context

**Gathered:** 2026-11-16
**Status:** Ready for planning

<domain>
## Phase Boundary

The milestone's agent-experience phase — put SIF's MCP server on the official Python SDK v2 while preserving every existing client contract, make the tool surface citation-grade and honestly annotated, close the query-pipeline parity gap, and ship agent-native distribution (Claude Code plugin + MCP Registry). Delivers exactly MCP-01..MCP-09:

1. **SDK v2 shell swap (MCP-01)** — replace the hand-rolled `MCPServer`/JSON-RPC/transports with the official SDK `MCPServer`; dual-era serving (2024-11-05 → 2026-07-28 + stateless) proven tracer-first with golden wire transcripts and a real-client matrix; `SearchBackend`/`watch_host`/SIF I/O models preserved; protocol shell deleted; Python 3.10 install/import smoke at phase start.
2. **Accurate annotations (MCP-02)** — every registered tool annotated for its actual behavior; read-only tools get `read_only_hint=True`/`open_world_hint=False`; no auto-approval claims; descriptions match the backend (the current `query` rerank overclaim is fixed).
3. **Citation-grade structured output (MCP-03)** — `structuredContent`/`outputSchema` from the preserved Pydantic models, carrying docid, path, line range, content hash, snippet, and staleness, with the legacy JSON text kept alongside.
4. **DNS-rebinding protection (MCP-04)** — Host/Origin validation via the SDK's `transport_security`, proven with spoofed headers before the hand-rolled Origin middleware is deleted.
5. **Query pipeline parity (MCP-05)** — expander/snippets wired, rerank opt-in and documented, pipeline components hoisted; lex/vec tools registered.
6. **Clean stdout + lazy embedder (MCP-06)** — the model loads on first vector need (never at startup), forced quiet before any model import, and a cold-first-query stdout-purity regression.
7. **Real daemon (MCP-07)** — `sif mcp daemon` un-stubbed via the existing `utils/daemon.py` lifecycle.
8. **Claude Code plugin (MCP-08)** — plugin + marketplace + MCP config + citation-discipline skill; `claude plugin validate` passes.
9. **MCP Registry (MCP-09)** — scripted, preflighted, re-runnable listing via `mcp-publisher`, after the Phase 17 PyPI prerequisite (v1.1.2 is published).

NOT in scope: new MCP mutation tools (index/vacuum/backup stay CLI/watch), OAuth/elicitation/MRTR/tasks/sampling/roots/logging, full Windows support (POSIX daemon refuses cleanly; stdio/HTTP work), a v1.2 release cut, Phase 23 Harrier evaluation, Phase 24 models/install-doc UX. No new runtime dependencies beyond the already-locked `mcp>=2.3.0,<3`; plugin assets are Markdown/JSON only.

</domain>

<decisions>
## Implementation Decisions

### Shell replacement, dependency gate, and compatibility (MCP-01)
- **D-01:** **Tracer-first full shell replacement, no dual stack.** Replace the hand-rolled `MCPServer`/JSON-RPC/transports with the official SDK `MCPServer` and delete the old shell (`src/sif/mcp/server.py`, the wire-type half of `src/sif/mcp/protocol.py`, `src/sif/mcp/transports/stdio.py`, `src/sif/mcp/transports/http.py`); preserve `SearchBackend`, `watch_host.py`, and the SIF tool I/O Pydantic models as the tool contract. Migrate one tool (`status`) end-to-end through both transports first, locking golden wire transcripts, then expand tool-by-tool. No parallel implementation or feature flag (research Anti-Pattern 8). — **Reversibility:** costly — the wire contract and client behavior are public; reverting after release would re-open client-compatibility validation.
- **D-02:** **Python 3.10 install/import smoke is the first gate.** Resolve `mcp>=2.3.0,<3` in a Python 3.10 scratch venv, install the project, and import `mcp.server.MCPServer` + `sif.mcp.app` before detailed planning of the swap. The Phase 22 research gap in STATE.md is this exact check (PyPI metadata says >=3.10 while the SDK README says 3.11+). If 2.x cannot run on 3.10, STOP and surface a user decision before raising SIF's floor or shipping a `mcp<2` compatibility pin — either is a one-way packaging change. — **Reversibility:** costly — a Python-floor change or dual-version pin changes the published package contract and the CI matrix.
- **D-03:** **`mcp` becomes a core dependency; extras stay as compatibility aliases.** Add `mcp>=2.3.0,<3` to `[project].dependencies`; keep the `mcp` and `http` extras as thin deprecated aliases (uvicorn only) so existing `pip install docsif[mcp]` commands keep working; do not pin `mcp-types` directly (SDK transitive); no other new runtime dependency. Refresh `uv.lock`; tolerate the py3.10/3.11+ resolution fleets without asserting exact transitive versions. — **Reversibility:** costly — the dependency set is a published packaging contract.
- **D-04:** **Dual-era compatibility is proven, not assumed.** Lock golden JSON-RPC wire transcripts for a 2024-11-05 `initialize` handshake, a 2025-11-25 handshake, and a 2026-07-28 stateless request (no `initialize`, `MCP-Protocol-Version` header), plus SDK-client tests for both eras. Add one real Claude Code smoke (temporary config; `claude mcp` tool listing + one `query`) recorded in SUMMARY. Delegate protocol negotiation to the SDK; never hand-roll version logic. Use `json_response=True` on the mounted HTTP app to preserve SIF's JSON responses; use SDK cache hints when exposed, otherwise assert the SDK's 2026-era defaults in the transcript. — **Reversibility:** costly — the supported-era claim is what existing clients depend on.
- **D-05:** **Legacy text content stays alongside structured output.** Every tool keeps the serialized JSON text payload legacy clients parse today and adds `structuredContent` plus `outputSchema` from the same Pydantic model. New fields are additive; existing field names and values do not change. If the SDK's auto-wrapping changes the text payload (for example a `{"result": ...}` wrapper), use an explicit result builder returning both channels rather than accepting the change. — **Reversibility:** costly — the text payload is the backward-compatibility contract for 2024/2025-era clients.

### Tool surface, annotations, errors, resources (MCP-02)
- **D-06:** **Seven read-capable tools; no mutation tools in Phase 22.** Register `query`, `get`, `multi_get`, `status`, `metadata`, `lex_search`, `vec_search`. Do NOT add `index update/embed`, `vacuum`, `backup`, or collection-mutation tools; those stay CLI/watch surfaces. `metadata` surfaces the Phase 20 frozen envelope unchanged. — **Reversibility:** costly — the tool list is a public MCP contract; adding tools later is additive, but shipping a mutation surface is a security commitment.
- **D-07:** **Annotations reflect actual behavior, never auto-approval.** All seven tools carry `read_only_hint=True`, `open_world_hint=False`; `idempotent_hint`/`destructive_hint` are omitted for read-only tools because they are only meaningful for non-read-only tools. Never claim prompt-free execution — documented Claude Code effects are parallel read-only calls plus one retry only. Tool descriptions are reviewed constants; fix the `query` description's rerank overclaim (rerank is opt-in). A test enumerates the registered tools, asserts every tool is read-only and every description matches backend behavior, and encodes the future-write-tool policy (`read_only_hint=False` + `destructive_hint=True` where applicable). — **Reversibility:** costly — hosts consume annotations for approval UX and security posture.
- **D-08:** **Expected tool errors are `ToolError`s.** Filter/match AST validation, input validation, unknown collection, vector-unavailable for `vec_search`, and identity dimension mismatches raise `ToolError` with the existing remedy text so the model can self-correct (SEP-1303); unexpected exceptions propagate and are sanitized by the SDK to `-32603`. Never return `INVALID_PARAMS` for tool-input semantics. Preserve the handler-side Pydantic validation the SDK's low-level path no longer performs. — **Reversibility:** costly — error semantics are an agent-facing contract.
- **D-09:** **Preserve the `docs://` resource capability.** Register an SDK resource for `docs://{doc_id}` backed by `SearchBackend.get_document`; return the full document by default and honor `from_line`/`max_lines` when present in the URI. The `get` tool remains the citation-grade line-range surface. The resource is read-only and subject to the same transport security. — **Reversibility:** costly — removing a resource would break clients that read documents via resources.

### Structured output and citation contract (MCP-03)
- **D-10:** **The preserved Pydantic output models are the schemas.** Tool functions return `QueryOutput`/`GetOutput`/`MultiGetOutput`/`StatusOutput`/`MetadataOutput`/`LexSearchOutput`/`VecSearchOutput`; the SDK derives `outputSchema` and `structuredContent` from the return annotation. `MetadataOutput` is returned as the model (unwrapped), so the Phase 20 envelope (`documents`, `filteredDocuments`, `totalKeys`, `remainingKeys`, `skippedKeys`, `builtIns`, `keys`) stays byte-compatible. Avoid dict returns for frozen envelopes; if the SDK's auto text differs, use the D-05 builder. — **Reversibility:** costly — output schemas are a public contract.
- **D-11:** **Citation-grade fields are distributed per tool.** Extend the MCP `SearchResult` with `snippet`, `content_hash` (from `documents.checksum` via one batched page lookup), `line_start`, and `line_end`; keep `docid`, `path`, `title`, `score`, `chunk_id`, `sequence`, `chunk_matches`, and `vectors_stale`. Line ranges come from the snippet window the pipeline already computes for `SmartSnippetExtractor` (extend the extractor to report its selected document-line window; no extra content scan, no new chunk columns). Extend `Document` with `content_hash` and always populate `line_start`/`line_end` on `get`/`multi_get` (full document = 1..N; ranged request = requested range). Do NOT add these fields to `SearchResult.to_dict()` — CLI JSON stays byte-identical; the MCP boundary maps the dataclass fields explicitly. The `sif-cite` skill must call `get` and cite docid + line numbers; never cite a snippet alone (two-stage citation). — **Reversibility:** costly — the citation schema and agent workflow are public.
- **D-12:** **Frozen envelopes win; changes elsewhere are additive.** The Phase 20 `metadata` envelope is surfaced unchanged, including `builtIns`, mixed camelCase, and exact remainders. Query/get output changes are additive only; no `schemaVersion` field in Phase 22. Contract versioning lives in docs/tests and the golden transcripts. — **Reversibility:** costly — the metadata envelope is a cross-phase contract consumed by later agents.

### Transport security (MCP-04)
- **D-13:** **Host/Origin validation comes from the SDK, configured through CLI flags.** Use the SDK `transport_security` settings with loopback defaults (`127.0.0.1`, `localhost`, `[::1]`) and the existing CORS origin list. Add `--allowed-hosts` to `mcp http` and `mcp daemon` (repeatable or comma-separated; planner's choice); keep `--cors-origins` as the origin allowlist. No new Settings fields. Never default to `*`; a non-loopback bind without explicit allowed hosts prints a warning and does not silently widen the allowlist. — **Reversibility:** costly — the flags and security behavior are public.
- **D-14:** **Prove before deleting the hand-rolled middleware.** Add spoofed-header tests (bad `Host` → 403, bad `Origin` → 403, allowed → 200) against the mounted SDK app; only then delete the custom `validate_origin` middleware. Keep `CORSMiddleware` for browser preflight/response headers. `/health` stays unauthenticated but is subject to Host validation. — **Reversibility:** costly — deleting a defense layer requires the proof to remain in the test suite.

### Lazy embedder, stdout purity, and query/watch parity (MCP-05/06)
- **D-15:** **The embedder loads lazily, once, and failure degrades honestly.** Use `EmbeddingManager` lazily on the first vector/hybrid need; one thread-safe load attempt per process. On failure, `query` degrades to BM25 with one warning (the WR-08 MCP carve-out), `vec_search` returns a `ToolError` naming the install/model remedy, and `lex_search`/`status`/`metadata`/`get`/`multi_get` never load a model. After load, the pipeline uses the loaded identity's dimension (Phase 21's loaded-model truth), not the settings value. The schema-open settings identity remains as Phase 21 left it. — **Reversibility:** costly — the failure behavior is an agent-visible contract.
- **D-16:** **Force quiet at the MCP composition root.** Call `set_quiet(True)` and the existing `_apply_quiet_mode` environment recipe (`TQDM_DISABLE`, `HF_HUB_DISABLE_PROGRESS_BARS`, `TRANSFORMERS_VERBOSITY`) before constructing the backend or importing any model, at stdio, HTTP, and daemon entrypoints. All diagnostics go to stderr/logs. Add a cold-first-query stdout-purity regression (every stdout line is JSON-RPC; no progress bars/ANSI). Do not hand-roll stdout redirection unless that regression proves the SDK insufficient; if needed, write protocol frames to the saved real stdout. — **Reversibility:** reversible — the regression and quiet call can be adjusted without a migration.
- **D-17:** **MCP `query` gets full CLI pipeline parity; `lex_search`/`vec_search` mirror the CLI one-shot search commands.** Wire `QueryExpansion` (same default-on hybrid expansion as CLI), `SmartSnippetExtractor`, and the reranker as an opt-in `rerank: bool | None = None` parameter (None follows `SIF_RERANK_ENABLED`; True/False overrides). Hoist heavyweight components (manager, expander, reranker, snippet extractor) at backend level; construct `SearchPipeline` per request because `_run_in_db` opens a fresh connection per request and the pipeline is connection-bound. `lex_search`/`vec_search` call `BM25Searcher`/`VectorSearcher` directly with the same options, filter, offset, per-chunk, identity check, and one `enrich_results`, matching CLI `search`/`vsearch`; they do not use prefix routing. Expansion/rerank failures degrade softly with a warning, exactly as CLI. Identity mismatches follow Phase 21 D-03 (warn + mark on search; fail-fast on embed). — **Reversibility:** costly — the query parameter surface and latency behavior are public.
- **D-18:** **The watch host survives the shell swap with its invariants intact.** Compose the SDK lifespan with `mcp_watch_lifespan`: enter `mcp.session_manager.run()`, start the watcher, yield, stop the watcher, then exit the session manager. Preserve `SIF_MCP_WATCH` opt-in, the literal `bm25` depth, logger-only callbacks, serve-first reconcile, and the D-14 `stop(flush=True)` → WAL checkpoint → close order. Stdio and HTTP hosts both retain the watch wiring. — **Reversibility:** costly — the live-index contract and shutdown ordering are user-visible.

### Daemon (MCP-07)
- **D-19:** **`mcp daemon` is a real HTTP daemon.** Implement it with the existing `utils/daemon.py` double-fork/arming machinery; run the HTTP transport detached; support `--stop`; reject stdio daemon mode. On Windows, refuse with the existing POSIX-fork cause/remedy (foreground `mcp http` remains available). — **Reversibility:** costly — the command and lifecycle are public.
- **D-20:** **The MCP daemon has its own PID artifact.** Use `<db>.mcp.pid` (with `--pid-file` override), payload `mode: "mcp"`, distinct from the watch daemon's `<db>.watch.pid`, so a watch daemon and an MCP daemon can run on one index concurrently. `sif status`'s watch section remains unchanged; `mcp daemon --stop` targets only the MCP daemon. — **Reversibility:** reversible — PID naming is internal metadata.
- **D-21:** **Arm on readiness; do not warm the model at startup.** The arm callback opens the DB, runs schema initialization, constructs the backend, and writes the PID; the HTTP bind happens after arming, and a bind failure exits the daemon, removes the PID file, and is logged. No startup model load (keeps startup cheap and quiet); the first vector query loads lazily and the process keeps the model warm. Default log `mcp.log` in the platform log dir; `--log-file` overrides. — **Reversibility:** reversible — the lifecycle can be tuned additively.

### Claude Code plugin, marketplace, Registry (MCP-08/09)
- **D-22:** **The repo root is the Claude Code plugin.** Add `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` with `source: "./"`, root `.mcp.json`, and `skills/` (`sif-search`, `sif-get`, new `sif-cite`). Plugin and marketplace names are `sif` (no `claude-`/`anthropic-` prefix); plugin version mirrors `src/sif/_version.py`. `claude plugin validate` is a phase gate (Claude Code 2.1.325 is installed). — **Reversibility:** costly — marketplace/distribution identity is public.
- **D-23:** **The plugin targets the installed `sif` command; skills are MCP-first.** `.mcp.json` runs `sif mcp stdio` by default. Installation docs make `uv tool install 'docsif[embed]'` the primary path (base install is BM25-only), with the Linux CPU-torch index and the installed-vs-zero-install distinction documented; `uvx --from ${CLAUDE_PLUGIN_ROOT} sif mcp stdio` is documented as the zero-install BM25-only fallback. Plugin skills call the MCP tools (`query`, `get`, `metadata`, `lex_search`, `vec_search`), not the CLI; `sif-cite` encodes the search→get→cite discipline: discover metadata before filtering, retrieve with `get`, cite docid + line numbers from `get`, never cite a snippet alone, and surface `vectors_stale`/`content_hash` caveats. — **Reversibility:** costly — the agent workflow and install path are user-facing.
- **D-24:** **Registry listing is scripted, preflighted, and re-runnable; Phase 22 does not cut a v1.2 release.** Check in `server.json` with name `io.github.zhangtaolab/sif`, package `docsif`, transport stdio, and version read from `src/sif/_version.py` (currently 1.1.2, already published). Add `scripts/publish_registry.py` with `--check` (README `mcp-name` marker exact match, PyPI JSON version exists, `server.json` schema/name/version consistency, registry idempotency) and `--publish` (runs `mcp-publisher publish` after the maintainer's `mcp-publisher login github` device flow). Never store credentials. The live publish is a maintainer checkpoint if the login is unavailable; record the exact command and registry verification URL. Re-run the script after the v1.2 release to advance the listed version. — **Reversibility:** costly — Registry names/versions are public and version-immutable.

### Quality gates and documentation
- **D-25:** **The MCP rewrite carries its own regression net.** Rewrite/replace the MCP server and transport tests around the SDK composition root and tool functions; keep `SearchBackend`/watch-host tests. Add golden wire transcripts for the three eras, SDK-client tests for both eras, spoofed Host/Origin tests, cold-first-query stdout purity, lazy-load no-model tests, metadata-envelope parity, plugin JSON/skill tests, and registry-script preflight tests. The 90% coverage gate, ruff/format/ty gates, and `make docs-generate` must stay green. Update `docs/mcp-server.md`, `src/sif/mcp/README.md`, `README.md` (plugin/registry sections), and the generated CLI docs; never hand-edit generated docs. No new runtime deps beyond `mcp`; plugin assets are Markdown/JSON only. — **Reversibility:** reversible — tests/docs can evolve without a migration.

### Locked upstream (roadmap/research — do not re-litigate)
- SDK v2 dual-era serving is automatic: one `streamable_http_app()` serves 2026-07-28 and handshake-era clients up to 2025-11-25; `OLDEST_SUPPORTED_VERSION="2024-11-05"` was verified at source level. `FastMCP` → `MCPServer`; old import path is gone; `mcp-types` fields are snake_case with camelCase wire JSON via `by_alias`.
- `SearchBackend` is the stable seam; `watch_host` D-14 teardown, `SIF_MCP_WATCH`, literal `bm25` depth, and logger-only callbacks survive. The ~623-line hand-rolled shell is deleted, not kept.
- Annotations do **not** auto-approve in Claude Code; documented effects are parallel read-only calls + one retry. Never claim prompt-free execution (open request claude-code#87452).
- `metadata` tool envelope is frozen by Phase 20 D-15/D-20 (`builtIns`, mixed camelCase, exact remainders) and is surfaced unchanged.
- Phase 21 EMB-01/EMB-02 contracts are consumed as-is: `index_meta` identity, role-aware `embed_query`/`embed_documents`, prompt-aware cache keys, Qwen3 default path byte-identical until Phase 23.
- Exactly two new runtime deps in v1.2: `rapidfuzz` (Phase 18) and `mcp` (Phase 22). No others.
- PyPI `docsif` v1.1.2 is published with the `<!-- mcp-name: io.github.zhangtaolab/sif -->` README marker; Registry listing may target that version now.
- OAuth/elicitation/MRTR/tasks/sampling/roots/logging are rejected for this loopback personal server; full Windows support is deferred to v2.
- Every new CLI flag/command flows through `make docs-generate`; `docs/cli-reference.md` and `docs/configuration.md` are never hand-edited.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements, roadmap, and project state
- `.planning/REQUIREMENTS.md` — MCP-01..MCP-09; Out of Scope table (OAuth/elicitation/etc., auto-approval, faceted UI, full Windows); traceability
- `.planning/ROADMAP.md` §Phase 22 — goal + five success criteria; §Phase 23/24 — consumers of the MCP contract; §Cross-Phase Contracts — embedder identity/role-aware embed, frozen `metadata` schema, docs-generate gate
- `.planning/PROJECT.md` §Current Milestone + §Key Decisions + §Constraints — v1.2 scope, exactly two new deps, local-first, qmd interface parity, Python 3.10+ / ty-only type checking
- `.planning/STATE.md` — current position and accumulated decisions; Blockers/Concerns research gaps: "MCP py3.10 install/import smoke at Phase 22 start; transport_security spoofed-header proof before deleting custom middleware"

### Milestone research
- `.planning/research/SUMMARY.md` §"Phase 6: MCP SDK v2 Modernization + Agent Packaging" (deliverables and rationale), §Critical Pitfalls, §Research Flags (Phase 6 HIGH — `transport_security`, lifespan composition, structured-output wrapping, real-client matrix)
- `.planning/research/PITFALLS.md` §P8 (big-bang MCP migration), §P9 (dual-era gap / client matrix), §P10 (stdout pollution under the SDK + lazy embedder), §P11 (annotation dishonesty and the rerank overclaim), §Security Mistakes, §"Looks Done But Isn't" (MCP SDK / annotations), §Recovery Strategies (SDK migration), §Pitfall-to-Phase Mapping
- `.planning/research/FEATURES.md` §C "MCP modernization (loopback, read-mostly)" — SDK v2, annotations, structuredContent, Host validation, pipeline parity, lex/vec, cache hints, daemon; §E "Engineering and distribution" — plugin, Registry, PyPI; §Differentiators — citation-grade structuredContent + skill-encoded citation discipline; §Anti-Features — OAuth/etc., auto-approval, index-mutating tools without destructiveHint
- `.planning/research/ARCHITECTURE.md` §Pattern 3 "MCP SDK v2 Migration — Preserve the Backend, Replace the Protocol Shell" (migration mapping and parity/lazy notes); §Data Flow — "MCP v2 Request Flow"; §Anti-Pattern 8 "Keeping the Hand-Rolled MCP Server Alongside the SDK"; §Suggested Build Order
- `.planning/research/STACK.md` §(a) "MCP SDK v2 adoption" — target shape, dual-era, structured output, transport security, dependency weight, migration traps; §(g) "MCP Registry listing + Claude Code skill/plugin" — server.json, mcp-name marker, plugin layout, `${CLAUDE_PLUGIN_ROOT}`; §Installation — pyproject deltas and extras aliases; §Version Compatibility

### Prior phase decisions (carry forward, do not re-litigate)
- `.planning/phases/21-scale-maintenance-embedder-identity/21-CONTEXT.md` — D-02/D-03/D-04 identity lifecycle and mismatch policy; D-06/D-07/D-08 role-aware embed, prompt scheme, cache key; D-19 Qwen3 byte-identical baseline. The MCP lazy embedder consumes these contracts.
- `.planning/phases/20-metadata-filtering-discovery/20-CONTEXT.md` — D-02/D-15/D-20 frozen `metadata` discovery envelope; D-17 invalid filters are tool execution errors (`isError`), never protocol errors.
- `.planning/phases/19-search-correctness/19-CONTEXT.md` — D-02/D-03 chunk identity fields; D-05 offset on all three MCP search inputs; CORR-05 single attach at pipeline exit.

### Code and data surfaces (verified this session at HEAD 0319bbf)
- `src/sif/mcp/server.py` — hand-rolled `MCPServer` state machine, initialize/tools/resources; DELETE.
- `src/sif/mcp/protocol.py` — JSON-RPC/wire types (DELETE) vs SIF I/O models `SearchResult`, `Document`, `CollectionInfo`, `QueryInput/Output`, `GetInput/Output`, `MultiGetInput/Output`, `StatusInput/Output`, `LexSearchInput/Output`, `VecSearchInput/Output`, `MetadataInput/Output` (PRESERVE).
- `src/sif/mcp/handlers.py` — `ToolHandler` ABC + 5 handlers, hand-written `input_schema`; rewrite as SDK tool functions.
- `src/sif/mcp/backend.py` — `SearchBackend`, `_run_in_db` fresh-connection pattern, WR-08 BM25 degradation, suggestions wrapper, boundary remap, Phase 21 identity/prompt handling; preserve + add lazy embedder and parity.
- `src/sif/mcp/watch_host.py` — `start_embedded_watch`, `stop_embedded_watch`, `mcp_watch_lifespan`; preserve and compose under the SDK lifespan.
- `src/sif/mcp/transports/stdio.py`, `src/sif/mcp/transports/http.py` — line-delimited stdio, FastAPI Streamable HTTP, in-memory sessions, custom `validate_origin` middleware; DELETE after proof.
- `src/sif/mcp/cli.py` — `run_stdio_server` / `run_http_server` wrappers; rewire to the new composition root.
- `src/sif/cli/commands/mcp.py` — `mcp` group, `stdio`/`http` commands, `--cors-origins`, `daemon` stub; MODIFY.
- `src/sif/utils/daemon.py` — `pid_path_for` (`.watch.pid`), `write_pid_file`, `read_pid_file`, `corroborate_pid`, `detach`, `stop_daemon`; reuse for the MCP daemon.
- `src/sif/utils/logging.py` — `set_quiet`, `is_quiet`, `_apply_quiet_mode` (TQDM/HF/TRANSFORMERS env recipe); use at the composition root.
- `src/sif/search/hybrid.py` — `SearchPipeline`, `_apply_snippets` (transient content fetch), prefix routing, identity-check closure, ONE `enrich_results`; parity changes.
- `src/sif/search/expansion.py` — `QueryExpansion` using `embed_query`/`embed_queries`; wire into MCP query.
- `src/sif/search/rerank.py` — `create_reranker`; opt-in path.
- `src/sif/search/snippets.py` — `SmartSnippetExtractor` line-aware window; extend to report the selected line range.
- `src/sif/embedding/manager.py` — `EmbeddingManager.from_settings`, idempotent `load_model`, `model`, `embed_query`/`embed_queries`/`embed_documents`, `get_identity`, prompt-aware cache bucket; use for lazy load and expansion.
- `src/sif/embedding/identity.py`, `src/sif/embedding/roles.py`, `src/sif/embedding/prompts.py` — Phase 21 identity and role contracts.
- `src/sif/config/settings.py` — `mcp_host`, `mcp_port`, `mcp_transport`, `mcp_watch`, `rerank_enabled`, `rerank_candidate_limit`, `rrf_k`, `bm25_weight`, `vector_weight`, `default_search_type`, `lock_wait_timeout`.
- `src/sif/database/repositories.py` — `DocumentRepository` and `documents.checksum` (citation content hash source).
- `pyproject.toml` — dependencies/extras/scripts; `uv.lock` — dependency resolution.
- `.claude/skills/sif-search/SKILL.md`, `.claude/skills/sif-get/SKILL.md` — existing CLI skills; the plugin adds MCP-first `skills/` copies, not replacements.
- `README.md` line 2 — `<!-- mcp-name: io.github.zhangtaolab/sif -->` marker (Registry ownership proof).
- `docs/mcp-server.md` — currently documents 4 tools and a daemon stub; rewrite.
- `src/sif/mcp/README.md` — stale hand-rolled assembly instructions; rewrite or point to `docs/mcp-server.md`.
- `Makefile`, `scripts/generate_cli_ref.py`, `scripts/generate_config_ref.py` — docs-generate gate.
- `tests/unit/mcp/` — `test_server.py`, `test_transports_http.py`, `test_transports_stdio.py` (rewrite); `test_backend.py`, `test_integration.py`, `test_mcp_watch_host.py` (preserve/adapt).

### External primary sources (verified by the milestone research; re-check at plan time)
- `https://github.com/modelcontextprotocol/python-sdk` — SDK v2 `MCPServer`, `streamable_http_app`, `session_manager.run()`, `transport_security`, structured-output return annotations, `ToolAnnotations`, era support.
- `https://modelcontextprotocol.io/specification/` — changelogs for 2024-11-05, 2025-06-18, 2025-11-25, 2026-07-28; annotations, structuredContent/outputSchema, cache hints, error semantics (SEP-1303).
- `https://code.claude.com/docs/en/plugins-reference` — `.claude-plugin/plugin.json`, skills layout, `.mcp.json`, marketplace, `claude plugin validate`, `${CLAUDE_PLUGIN_ROOT}`.
- `https://modelcontextprotocol.io/registry/quickstart` — `server.json` schema, `mcp-publisher`, README `mcp-name` marker, namespace ownership.
- `https://code.claude.com/docs/en/mcp` — Claude Code MCP client behavior; annotations do not auto-approve (parallel read-only calls + one retry).
- `https://pypi.org/pypi/docsif/json` and `https://pypi.org/pypi/mcp/json` — published version and SDK metadata checks used by the Registry/dependency preflights.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`SearchBackend` is already the stable seam.** It is async, transport-agnostic, uses a fresh DB connection per request (`_run_in_db`), and owns the WR-08 BM25-degradation carve-out, suggestions wrapper, and Phase 21 identity/prompt handling. The SDK swap replaces the shell around it, not the backend.
- **`EmbeddingManager` already has lazy semantics.** `load_model()` is idempotent, `model` is a property, `get_identity()` caches the full identity, and `embed_query`/`embed_queries`/`embed_documents` carry the role/prompt contract. The lazy embedder is a backend-level `EmbeddingManager` usage change, not a new model loader.
- **`start_embedded_watch`/`stop_embedded_watch`/`mcp_watch_lifespan`** already implement the watch host with the D-14 teardown order and logger-only callbacks; compose them under the SDK lifespan.
- **`utils/daemon.py`** already provides double-fork, arming handshake, PID payload/corroboration, stop escalation, and Windows refusal. Reuse it for `mcp daemon`; add only an MCP PID-path helper and log default.
- **`utils/logging.py`** already has `set_quiet`/`_apply_quiet_mode` with the TQDM/HF/TRANSFORMERS environment recipe; call it at the composition root.
- **`QueryExpansion`, `create_reranker`, `SmartSnippetExtractor`** are the exact CLI parity components; wire them into the backend/pipeline rather than reimplementing.
- **The SIF I/O Pydantic models** are the tool contract; their return annotations can drive the SDK's `outputSchema`/`structuredContent` with no schema rewrite.
- **`documents.checksum`** is the content hash for citation drift; `DocumentRepository` already exposes it. `SmartSnippetExtractor` already fetches document content transiently for snippets, so line ranges can ride that same window.

### Established Patterns
- Tracer-first migration with golden wire transcripts; never big-bang without a one-tool end-to-end proof.
- Preserve the backend/watch host/I/O models; delete the protocol shell; do not keep both servers (Anti-Pattern 8).
- Byte-identical defaults and additive-only public output changes; CLI JSON stays unchanged in this phase.
- Warnings/notices on stderr; stdout/JSON stays machine-clean. Cold-first-query stdout purity is a regression, not a convention.
- Pydantic validation stays in the tool layer because the SDK's low-level validation is gone; expected user errors become `ToolError`s.
- The frozen Phase 20 `metadata` envelope wins over SDK auto-wrapping; return the model unwrapped.
- Generator-owned docs: new CLI flags run `make docs-generate`; never hand-edit `docs/cli-reference.md`/`docs/configuration.md`.
- Deterministic tests: `tmp_path` batteries, `ConceptEmbedder`/mock managers for hermetic embeddings, no wall-clock races; golden transcripts normalize voluntary fields.

### Integration Points
- `src/sif/mcp/app.py` (new) — composition root: build `MCPServer`, register the seven tools, force quiet, compose the SDK lifespan with watch start/stop, mount `streamable_http_app()` at `/mcp` on the existing FastAPI app, keep `/health`, and run stdio/HTTP.
- `src/sif/mcp/tools.py` (new, name planner's) — `@mcp.tool` functions for query/get/multi_get/status/metadata/lex_search/vec_search, return-type annotations, annotations, descriptions, `ToolError` mapping.
- `src/sif/mcp/protocol.py` — delete JSON-RPC/wire types; keep/move the SIF I/O models.
- `src/sif/mcp/backend.py` — lazy `EmbeddingManager`, parity components, citation fields, checksum lookup, lex/vec methods.
- `src/sif/mcp/watch_host.py` — lifespan composition under `session_manager.run()`.
- `src/sif/mcp/server.py`, `src/sif/mcp/transports/*` — deleted.
- `src/sif/cli/commands/mcp.py` — `mcp http`/`mcp daemon` use the new app, `--allowed-hosts`, real daemon lifecycle.
- `src/sif/utils/daemon.py` — add an MCP PID-path helper (`<db>.mcp.pid`) without changing watch behavior.
- `src/sif/search/hybrid.py` — `SearchResult` line fields and snippet-window reporting; no CLI JSON change.
- `src/sif/search/snippets.py` — line-range-returning extraction API.
- `src/sif/mcp/protocol.py` — MCP `SearchResult`/`Document` citation fields.
- `pyproject.toml` + `uv.lock` — `mcp>=2.3.0,<3` core; extras aliases.
- `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.mcp.json`, `skills/sif-search`, `skills/sif-get`, `skills/sif-cite` — new plugin assets.
- `server.json`, `scripts/publish_registry.py` — Registry surface.
- `docs/mcp-server.md`, `src/sif/mcp/README.md`, `README.md`, generated docs — documentation sweep.
- Tests: `tests/unit/mcp/` rewrite plus new wire/transport-security/lazy/daemon/plugin/registry test modules; keep `tests/unit/mcp/test_backend.py`/`test_mcp_watch_host.py` adapted.

</code_context>

<specifics>
## Specific Ideas

- **Golden wire proof:** a 2024-11-05 `initialize` handshake then `tools/list` then one `tools/call status`; a 2025-11-25 handshake; a 2026-07-28 request with `MCP-Protocol-Version: 2026-07-28` and no `initialize`. Normalize `serverInfo.version`/session IDs; assert the result text parses as JSON and `structuredContent` is present.
- **Real-client matrix:** SDK legacy client + SDK modern client in tests; one Claude Code smoke in a temporary config (`claude mcp` lists the seven tools, one `query` returns results) recorded in SUMMARY. If the CLI cannot be automated safely, record the exact command and observed output.
- **Host/Origin proof:** bad `Host` → 403, bad `Origin` → 403, allowed loopback → 200, `/health` with bad Host → 403. Delete `validate_origin` only after these pass.
- **Cold-query purity:** an embedder stub that prints to stdout on load; run the stdio server, issue a first `query` that triggers lazy load, and assert every stdout line is a JSON-RPC frame (no `Downloading`, ANSI, or progress bars).
- **Lazy-load proof:** `status`, `lex_search`, `metadata`, `get`, `multi_get` never call `EmbeddingManager.load_model`; first `query`/`vec_search` calls it once; second call reuses; load failure degrades `query` to BM25 and makes `vec_search` a `ToolError`.
- **Citation proof:** a multi-line fixture document; a query result's `line_start`/`line_end` bracket the snippet window; `get` full document returns 1..N; `get` with `from_line`/`max_lines` returns the requested range; `content_hash` equals the stored checksum; `vectors_stale` rides through.
- **Frozen envelope proof:** `metadata` structuredContent deep-equals the Phase 20 envelope (including `builtIns` and remained camelCase); text content parses to the same model; no wrapper key.
- **Annotation honesty:** enumerate the seven tools; every `read_only_hint` is true, every `open_world_hint` false; no description contains an unconditional rerank/auto-approval claim; no tool accepts a filesystem target path.
- **Daemon proof:** `mcp daemon` arms, writes `<db>.mcp.pid`, serves `/mcp`, and `--stop` stops it; a watch daemon started on the same index keeps running and its `<db>.watch.pid` is untouched; a port conflict exits non-zero and removes the PID.
- **Plugin proof:** `claude plugin validate` passes; `.mcp.json` parses and names `sif`; the three skills exist with valid frontmatter; `sif-cite` contains the search→get→cite rule and forbids snippet-only citations.
- **Registry proof:** `scripts/publish_registry.py --check` passes for the published 1.1.2, refuses a README marker mismatch, refuses a `_version.py`/server.json mismatch, and refuses a PyPI version 404; a second `--publish` for an already-listed version exits 0 with "already listed".
- **Parity proof:** with a mock expander, `query` produces the same expansion variants as CLI; `rerank` defaults to `SIF_RERANK_ENABLED`, `rerank=true` constructs the reranker and changes ordering, `rerank=false` overrides a true setting; `lex_search`/`vec_search` do not expand or rerank.
- **Watch proof:** with `SIF_MCP_WATCH=1`, a file change during an HTTP serve is indexed; shutdown stops the watcher before the session manager exits and the WAL checkpoint runs; with the flag off, serving is unchanged.
- **SDK swap proof:** `sif mcp stdio` still answers the old 2024-era handshake; `sif mcp http` serves both eras on `/mcp`; no `Mcp-Session-Id` is required for a 2026 request; `tools/list` order is deterministic.

</specifics>

<deferred>
## Deferred Ideas

- **MCP mutation tools** (`index update/embed`, `vacuum`, `backup`, collection mutation) — stay CLI/watch in Phase 22. If exposed later: `read_only_hint=False`, `destructive_hint=True` where applicable, and no caller-supplied target paths (PITFALLS 11/19). A future phase, not a clarification of this one.
- **qmd-style `searches` array / HyDE sub-query parameter** on the MCP `query` tool — not required for parity; additive later.
- **OAuth / elicitation / MRTR / tasks / sampling / roots / logging** — rejected for the loopback personal server (REQUIREMENTS Out of Scope).
- **Full Windows daemon/service parity** — v2; Phase 22 keeps the clean POSIX-fork refusal and foreground `mcp http`.
- **Registry CI OIDC automation and automatic re-listing on release** — the scripted local/device-flow path ships first; a workflow is additive later.
- **Additional marketplace hosts, plugin hooks/commands, or a separate plugin repository** — the repo-root plugin is v1.2 deliverable.
- **Line ranges in CLI JSON output** — kept out of `SearchResult.to_dict()` in Phase 22 to preserve CLI byte-identical output; the MCP boundary carries them.
- **Per-tool TTL/cacheScope tuning beyond SDK defaults** — revisit if a client needs a shorter/longer cache.

</deferred>

---

*Phase: 22-MCP SDK v2 Modernization + Agent Packaging*
*Context gathered: 2026-11-16*
