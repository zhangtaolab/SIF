# Phase 22: MCP SDK v2 Modernization + Agent Packaging - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-16
**Phase:** 22-MCP SDK v2 Modernization + Agent Packaging
**Areas discussed:** SDK adoption & shell disposal, Dual-era proof & compatibility, Tool surface/annotations/resources, Structured output & citation, Transport security, Lazy embedder & query parity, Daemon lifecycle, Plugin/marketplace/Registry, Quality gates & docs

**Mode:** `--auto` — all gray areas selected; the recommended option was chosen for every question. No AskUserQuestion was used.

---

## SDK adoption & shell disposal

| Option | Description | Selected |
|--------|-------------|----------|
| Tracer-first full replacement | Migrate one tool end-to-end, then replace the shell; delete the old server/transports/wire types; preserve the backend/watch host/I/O models; no dual stack. | ✓ |
| Parallel SDK server behind a flag | Keep both servers and switch at runtime. | |
| Thin adapter over the hand-rolled server | Keep the JSON-RPC shell and adapt the SDK around it. | |

**Auto's choice:** Tracer-first full replacement.
**Notes:** Research Anti-Pattern 8 rejects keeping both. The backend is the stable seam. Python 3.10 install/import smoke is the first gate; if mcp 2.x is incompatible, stop and escalate before changing the floor or pinning mcp<2. `mcp>=2.3.0,<3` becomes a core dep; `mcp`/`http` extras stay as deprecated aliases; no direct `mcp-types` pin.

---

## Dual-era proof & compatibility

| Option | Description | Selected |
|--------|-------------|----------|
| Golden transcripts + SDK clients + real-client smoke | Lock 2024-11-05, 2025-11-25, and 2026-07-28 wire transcripts; test both SDK client eras; run one Claude Code smoke; SDK owns negotiation. | ✓ |
| SDK client tests only | Trust the SDK's own client for both eras. | |
| Real-client smoke only | Test with one real client and skip transcripts. | |

**Auto's choice:** Three-layer proof.
**Notes:** Keep the serialized JSON text payload alongside structuredContent; additive fields only; explicit result builder if the SDK's auto-wrap changes the text. `json_response=True` preserves SIF's JSON HTTP responses.

---

## Tool surface, annotations, resources

| Option | Description | Selected |
|--------|-------------|----------|
| Seven read-capable tools, no mutations | query, get, multi_get, status, metadata, lex_search, vec_search; index/vacuum/backup stay CLI/watch. | ✓ |
| Add index update/embed write tools | Expose indexing as MCP write tools with readOnly false/idempotent true. | |
| Add index + vacuum/backup tools | Expose the full maintenance surface with destructive hints. | |

**Auto's choice:** Seven read-capable tools, no mutations.
**Notes:** All seven get `read_only_hint=True`, `open_world_hint=False`; no auto-approval claims; descriptions are reviewed and the rerank overclaim is fixed; a test encodes the future-write-tool policy. Expected user errors become `ToolError`s; unexpected exceptions sanitize to `-32603`. The `docs://` resource is preserved (full doc by default; line ranges via `get`).

---

## Structured output & citation

| Option | Description | Selected |
|--------|-------------|----------|
| Pydantic return models, distributed citation fields | SDK derives outputSchema/structuredContent; search results gain content_hash/snippet/line_start/line_end from the existing snippet window; get always populates line ranges; metadata envelope unchanged. | ✓ |
| Hand-written JSON schemas | Maintain schemas separately from the models. | |
| Extra content scan for query line ranges | Fetch document content for every query result to compute lines. | |

**Auto's choice:** Pydantic return models + distributed citation fields.
**Notes:** The snippet extractor already fetches document content for snippets; reporting its selected line window adds line ranges with no extra scan. `SearchResult.to_dict()` stays unchanged so CLI JSON is byte-identical; the MCP boundary maps the new dataclass fields. `metadata` is returned unwrapped and stays frozen. No `schemaVersion` field in Phase 22.

---

## Transport security

| Option | Description | Selected |
|--------|-------------|----------|
| SDK transport_security + CLI flags | Loopback defaults plus existing CORS origins; `--allowed-hosts` on http/daemon; keep `--cors-origins`; no new Settings; no wildcard default. | ✓ |
| Add Settings fields | Expose allowed hosts/origins via `SIF_MCP_ALLOWED_*`. | |
| SDK defaults only | No override surface. | |

**Auto's choice:** SDK transport_security + CLI flags.
**Notes:** Prove bad Host/Origin → 403 and allowed → 200 before deleting the custom Origin middleware; keep `CORSMiddleware`; `/health` stays unauthenticated but Host-validated. Non-loopback binds warn unless allowed hosts are explicit.

---

## Lazy embedder & query parity

| Option | Description | Selected |
|--------|-------------|----------|
| Lazy load + honest degradation + CLI parity | EmbeddingManager loads once on first vector/hybrid need; query degrades to BM25; vec_search errors; lex/status/metadata/get/multi_get never load. Wire expansion/snippets/opt-in rerank; lex/vec mirror CLI one-shot search. | ✓ |
| Keep the eager load | Load the model at backend construction. | |
| Make expansion and rerank opt-in / default rerank on | Change the parity defaults. | |

**Auto's choice:** Lazy load + honest degradation + CLI parity.
**Notes:** Force quiet at the composition root before any model import; cold-first-query stdout-purity regression. Rerank is `rerank: bool | None = None` (None follows `SIF_RERANK_ENABLED`). Heavy components hoisted; `SearchPipeline` stays per request because it is connection-bound. Watch host composed under the SDK lifespan with the D-14 teardown order.

---

## Daemon lifecycle

| Option | Description | Selected |
|--------|-------------|----------|
| HTTP-only real daemon, separate PID | `mcp daemon` runs HTTP via utils/daemon.py; `--stop`; `<db>.mcp.pid` coexists with `<db>.watch.pid`; no startup model warm-up. | ✓ |
| Daemonize stdio too | Support both transports detached. | |
| Share one PID and make daemons mutually exclusive | One daemon per index. | |

**Auto's choice:** HTTP-only real daemon with a separate PID artifact.
**Notes:** Arm on DB/schema/backend readiness + PID write; bind after arm, failure logs and removes the PID. First vector query loads lazily and stays warm. Windows refuses with the POSIX-fork cause/remedy.

---

## Plugin, marketplace, Registry

| Option | Description | Selected |
|--------|-------------|----------|
| Repo-root plugin, installed `sif` primary, scripted Registry | `.claude-plugin/` + marketplace + root `.mcp.json` + `skills/`; `sif mcp stdio` primary with install docs and a uvx BM25 fallback; `sif-cite` skill; `server.json` + preflighted publish script targeting published 1.1.2. | ✓ |
| uvx zero-install primary | Plugin always uses `uvx --from ${CLAUDE_PLUGIN_ROOT}` (BM25-only). | |
| Cut a v1.2 release first | Publish v1.2.0 before listing/plugin packaging. | |

**Auto's choice:** Repo-root plugin, installed `sif` primary, scripted Registry.
**Notes:** Plugin/marketplace names are `sif`; version mirrors `_version.py`; `claude plugin validate` is a gate. Installation docs make `uv tool install 'docsif[embed]'` primary (base is BM25-only). The Registry script preflights the README marker, PyPI version, server.json consistency, and idempotency; live publish is a maintainer checkpoint if the device-flow login is unavailable. No v1.2 release in Phase 22.

---

## Quality gates & docs

| Option | Description | Selected |
|--------|-------------|----------|
| Full MCP-specific regression net + docs sweep | Tool-function/SDK-client tests, golden transcripts, spoof tests, cold-query purity, lazy no-model, metadata parity, plugin/registry tests, 90% coverage; rewrite docs and run docs-generate. | ✓ |
| Keep only backend tests | Skip the protocol/transport regression net. | |
| Defer docs to Phase 24 | Ship without updating MCP docs. | |

**Auto's choice:** Full regression net + docs sweep.
**Notes:** Rewrite/replace the server/transport tests around the composition root; keep backend/watch-host tests. No new runtime deps; plugin assets are Markdown/JSON only.

---

## Claude's Discretion

- Exact SDK import path (`mcp.server.mcpserver` vs `mcp.server`) after the 3.10 smoke.
- `ToolAnnotations` field names/casing and cache-hint values.
- How the explicit text+structured result builder is implemented if the SDK auto-wrap changes the payload.
- The snippet-extractor line-range API shape and whether the core `SearchResult` line fields are dataclass fields or a boundary wrapper.
- `--allowed-hosts` spelling (repeatable vs comma-separated) and the exact non-loopback warning wording.
- `server.json` description text (<100 chars) and the Registry script's exact flags/output.
- Plugin skill copy, SKILL.md descriptions, and the install-doc wording.
- Daemon log filename, PID payload `depth` value, and bind-failure cleanup details.
- Wire-transcript fixture layout and normalization rules.
- Whether `lex_search` also returns zero-result suggestions (additive; not required).
- Whether `/health` stays at `/health` (it should) and its exact response.

## Deferred Ideas

- MCP mutation tools (index update/embed, vacuum, backup) — stay CLI/watch; future phase with destructive annotations and target restrictions.
- qmd-style `searches` array / HyDE sub-query parameter.
- OAuth/elicitation/MRTR/tasks/sampling/roots/logging.
- Full Windows daemon/service parity.
- Registry CI OIDC automation / automatic re-listing.
- Additional marketplace hosts, plugin hooks/commands, separate plugin repo.
- Line ranges in CLI JSON output (kept byte-identical in Phase 22).
- Per-tool cache TTL tuning beyond SDK defaults.
