---
phase: 22-mcp-sdk-v2-modernization-agent-packaging
plan: 01
subsystem: mcp
tags: [mcp, sdk-v2, mcpserver, streamable-http, transport-security, golden-transcripts, lazy-embedder, uvicorn, fastapi, packaging]

# Dependency graph
requires:
  - phase: 21-scale-maintenance-embedder-identity
    provides: "settings-only embedder identity at schema open (retained) and the prompt-scheme contract the future lazy loaded identity consumes"
  - phase: 20-metadata-filtering-discovery
    provides: "frozen MetadataOutput envelope (surfaced unchanged in 22-02)"
  - phase: 19-search-correctness
    provides: "SearchBackend startup schema migration and the explicit boundary field re-map"
provides:
  - "mcp>=2.3.0,<3 as a core runtime dependency plus a regenerated uv.lock"
  - "src/sif/mcp/app.py composition root: SERVER_NAME, build_transport_security, build_server, create_http_app, run_stdio, run_http, run_http_app"
  - "src/sif/mcp/tools.py: dual-channel _result builder, TOOL_ANNOTATIONS, TOOL_DESCRIPTIONS, register_tools (status), register_resource (docs://)"
  - "SearchBackend model-free construction plus the lazy-load lock/attempt/failure skeleton"
  - "mcp_session_lifespan: D-18 session-manager/watch ordering helper"
  - "five normalized era goldens with a re-runnable SIF_UPDATE_WIRE_GOLDENS=1 writer"
  - "composition-root, SDK-client, transport-security, stdout-purity, packaging, and watch-ordering test batteries"
affects: [22-02, 22-03, 22-04, 22-05, 22-06, 22-07]

# Actuals (#2632) - pairs with the plan's `estimate` (100000 tokens, 3 tasks).
actuals:
  tokens: 49704
  tasks: 3
  commits: 2
plan_head_before: b5881fa510ec9a8e91541cc3f8d9b86b6fe43779
plan_head_after: 771fb99d285a3441da34dd4c2f291973ccf2403d

tech-stack:
  added: ["mcp>=2.3.0,<3", "mcp-types 2.3.0 (transitive, never declared)", "httpx2 2.16 (transitive)"]
  patterns:
    - "One MCPServer, one streamable_http_app() call, one root mount with inner path /mcp"
    - "SearchBackend constructed inside the SDK lifespan, never at import"
    - "Explicit CallToolResult builder emitting legacy compact JSON text plus structuredContent"
    - "Always-explicit TransportSecuritySettings (never None, never a wildcard)"
    - "Re-runnable golden writer guarded by an environment flag"
    - "Watch host composed under session_manager.run() in the D-18 order"

key-files:
  created:
    - src/sif/mcp/app.py
    - src/sif/mcp/tools.py
    - tests/unit/mcp/test_app.py
    - tests/unit/mcp/test_sdk_clients.py
    - tests/unit/mcp/test_wire_transcripts.py
    - tests/unit/mcp/test_transport_security.py
    - tests/unit/mcp/test_stdout_purity.py
    - tests/unit/mcp/test_packaging.py
    - tests/unit/mcp/goldens/2024-11-05.json
    - tests/unit/mcp/goldens/2025-03-26.json
    - tests/unit/mcp/goldens/2025-06-18.json
    - tests/unit/mcp/goldens/2025-11-25.json
    - tests/unit/mcp/goldens/2026-07-28.json
  modified:
    - pyproject.toml
    - uv.lock
    - src/sif/mcp/__init__.py
    - src/sif/mcp/cli.py
    - src/sif/mcp/backend.py
    - src/sif/mcp/watch_host.py
    - src/sif/cli/main.py
    - tests/unit/mcp/test_backend.py
    - tests/unit/mcp/test_mcp_watch_host.py
    - tests/integration/test_mcp_watch_e2e.py

key-decisions:
  - "Tool functions use Annotated[CallToolResult, OutputModel] return annotations, so outputSchema derives from the preserved Pydantic model while the explicit builder controls both channels. This avoids a type: ignore and the SDK's indent=2 auto text."
  - "Tools and the docs:// resource are registered inside the SDK lifespan (where SearchBackend is constructed) behind a one-registration guard, so repeated test lifespans never duplicate the surface."
  - "build_server records its resolved TransportSecuritySettings on the server (sif_transport_security); create_http_app reuses it unless the caller overrides an allowlist."
  - "The docs:// resource raises ResourceNotFoundError for an unknown id, which the SDK maps to -32602 (the SEP-2164 not-found variant)."
  - "The watch e2e bridge skips the three query-dependent proofs and the drift test's query tail with a module-level reason naming 22-02's seven-tool battery; no watch assertion was deleted."
  - "The stdout-purity regression drives the subprocess interactively (initialize, then status) because batching every line and closing stdin races the SDK connection."
  - "uv.lock regeneration expanded Python 3.14 resolution markers (uv 0.13.7) and added only mcp's dependency closure; no existing package version changed."

patterns-established:
  - "Composition order: quiet -> server -> lifespan backend -> tool/resource registration -> mount -> serve"
  - "Golden writer: SIF_UPDATE_WIRE_GOLDENS=1 rewrites sorted-key JSON with a trailing newline; the default path compares and fails on drift"
  - "Loopback-only allowlists in tests: base_url=http://localhost or an explicit Host header; testserver is never allowlisted"
  - "Dual-channel parity assertion: json.loads(text) == structured_content for every tool result"

requirements-completed: [MCP-01, MCP-04, MCP-06]

coverage:
  - id: D1
    description: "Official MCP SDK v2 composition root serves /health, /mcp without a redirect, and the status tool with dual-channel parity"
    requirement: MCP-01
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_app.py#test_http_health_and_mcp_mount_serve_without_a_redirect"
        status: pass
      - kind: integration
        ref: "tests/unit/mcp/test_sdk_clients.py#test_asgi_http_client_modes"
        status: pass
    human_judgment: false
  - id: D2
    description: "Five protocol revisions are locked by normalized golden transcripts, including outputSchema/structuredContent on the 2024-era response"
    requirement: MCP-01
    verification:
      - kind: integration
        ref: "tests/unit/mcp/test_wire_transcripts.py#test_wire_transcript_matches_golden"
        status: pass
    human_judgment: false
  - id: D3
    description: "SDK transport security rejects spoofed Host (421) and Origin (403), allows loopback and absent Origin, and rejects non-JSON Content-Type (400)"
    requirement: MCP-04
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_transport_security.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "A cold sif mcp stdio process emits only JSON-RPC frames on stdout, including with the legacy docsift migration fixture present"
    requirement: MCP-06
    verification:
      - kind: e2e
        ref: "tests/unit/mcp/test_stdout_purity.py#test_cold_stdio_stdout_emits_only_json_rpc_frames"
        status: pass
    human_judgment: false
  - id: D5
    description: "The runtime dependency list is frozen at 13 entries, mcp is the only addition, mcp-types is never declared, and the extras stay uvicorn-only aliases"
    requirement: MCP-01
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_packaging.py"
        status: pass
    human_judgment: false
  - id: D6
    description: "The watch host runs under the SDK lifespan in the D-18 order while SIF_MCP_WATCH off leaves serving unchanged"
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_mcp_watch_host.py#test_session_lifespan_orders_session_manager_around_the_watcher"
        status: pass
    human_judgment: false
  - id: D7
    description: "The docs:// resource serves the full Markdown document and the requested inclusive line window, and errors on an unknown id"
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_app.py#test_docs_resource_serves_full_and_ranged_documents"
        status: pass
    human_judgment: false
  - id: D8
    description: "Package legitimacy for mcp==2.3.0 was confirmed by the maintainer before install"
    verification: []
    human_judgment: true
    rationale: "Supply-chain approval is a one-time human judgment; the record is in this SUMMARY and the install is separately proven by the Python 3.10 smoke."

# Metrics
duration: 24min
completed: 2026-11-16
status: complete
---

# Phase 22 Plan 01: MCP SDK v2 Tracer Summary

**Official MCP SDK v2 shell serving status end-to-end, with five locked era transcripts, loopback transport security, and a model-free lazy backend**

## Performance

- **Duration:** ~24 min
- **Started:** 2026-11-16T06:47:00Z (approx.)
- **Completed:** 2026-11-16T07:11:00Z
- **Tasks:** 3 (1 human checkpoint approved + 2 execution tasks)
- **Files modified:** 23 (8 source, 10 test, 5 goldens; `uv.lock` regenerated)

## Package-Legitimacy Approval (Task 1)

- **Approved:** 2026-11-16 by the user/maintainer.
- **Confirmed version:** `mcp==2.3.0`.
- **Confirmed items:**
  1. PyPI project `mcp` version 2.3.0 is the official Model Context Protocol Python SDK (`summary: Model Context Protocol SDK`, `Requires-Python >=3.10`, not yanked, uploaded 2026-10-02).
  2. The project links to `github.com/modelcontextprotocol/python-sdk` and is MIT-licensed.
  3. No new runtime dependency other than `mcp` is added; `mcp-types==2.3.0` is transitive and never declared directly (D-03).
- **Install proof:** `uv pip install --dry-run` showed only mcp's closure (5 additions, 2 replacements, no downgrades of starlette/fastapi/pydantic/uvicorn/anyio/httpx); the install and the Python 3.10 smoke below then passed.

## Accomplishments

- `mcp>=2.3.0,<3` is a core dependency; the `mcp`/`http` extras remain uvicorn-only compatibility aliases; `uv.lock` was regenerated add-only (no existing package version changed).
- `src/sif/mcp/app.py` is the one composition root: `MCPServer(SERVER_NAME, version=__version__)`, an explicit `TransportSecuritySettings`, one `streamable_http_app(streamable_http_path="/mcp", json_response=True)` call mounted at `/` after `/health`, and D-18 watch composition under `session_manager.run()`.
- `status` is served end-to-end over in-process legacy/auto clients, the mounted ASGI app, and a real `sif mcp stdio` subprocess, always as compact legacy JSON text plus `structuredContent`.
- The `docs://{doc_id}{?from_line,max_lines}` resource returns the full Markdown document, an inclusive line window (`from_line=2&max_lines=3` -> lines 2-4), and a resource error for an unknown id.
- All five protocol revisions (2024-11-05, 2025-03-26, 2025-06-18, 2025-11-25, 2026-07-28) are locked by normalized goldens; the 2026 transcript has no `initialize` and no session, and missing `Mcp-Name`/`_meta` is rejected.
- Transport security is proven against the mounted SDK app before any deletion: bad Host 421, bad Origin 403, allowed loopback 200, absent Origin 200, non-JSON Content-Type 400.
- `SearchBackend` construction is model-free (no factory, no `load_model`, no `get_identity`), with the one-attempt lazy-load skeleton in place for 22-02/22-04.
- The cold stdio protocol channel is proven clean with the legacy `docsift` migration fixture present; the notice now prints through `console_err` on stderr.

## Task Commits

Each task was committed atomically:

1. **Task 1: Confirm package legitimacy for the official MCP SDK before install** - checkpoint only (no file changes, no commit); approved as `approved 2.3.0`.
2. **Task 2: End-to-end status through the SDK composition root over stdio and HTTP** - `23b60ee` (feat)
3. **Task 3: Lock the era matrix, compose the watch lifespan, prove transport security and stdout purity** - `771fb99` (feat)

**Plan metadata:** docs commit created after this SUMMARY (not counted in `actuals.commits`).

## Files Created/Modified

- `pyproject.toml` - `mcp>=2.3.0,<3` core dependency; deprecated extras aliases documented
- `uv.lock` - regenerated resolved graph (add-only; expanded Python 3.14 markers)
- `src/sif/mcp/app.py` - composition root, transport security, HTTP app, stdio/HTTP runners
- `src/sif/mcp/tools.py` - dual-channel builder, annotations, status tool, docs resource
- `src/sif/mcp/backend.py` - model-free constructor plus lazy-load skeleton
- `src/sif/mcp/watch_host.py` - `mcp_session_lifespan` (D-18); `mcp_watch_lifespan` intact
- `src/sif/mcp/__init__.py` - exports `MCPServer`, `SearchBackend`, `build_server`
- `src/sif/mcp/cli.py` - lazy wrappers delegating to `app.py`
- `src/sif/cli/main.py` - migration notice on the named `console_err` stderr console
- `tests/unit/mcp/test_app.py` - composition root, mount, resource, status parity
- `tests/unit/mcp/test_sdk_clients.py` - legacy/auto over in-process, ASGI, real stdio
- `tests/unit/mcp/test_wire_transcripts.py` - era matrix + re-runnable golden writer
- `tests/unit/mcp/test_transport_security.py` - spoofed Host/Origin matrix
- `tests/unit/mcp/test_stdout_purity.py` - cold stdio protocol purity
- `tests/unit/mcp/test_packaging.py` - frozen 13-entry runtime dependency gate
- `tests/unit/mcp/goldens/*.json` - five normalized era transcripts
- `tests/unit/mcp/test_backend.py` - construction-is-model-free; 12 factory patches removed; schema-open identity and legacy-assumed-row assertions retained
- `tests/unit/mcp/test_mcp_watch_host.py` - added the D-18 ordering test (existing 15 tests intact)
- `tests/integration/test_mcp_watch_e2e.py` - full 2024-11-05 initialize params + explicitly reasoned status-only bridge

## Verification Evidence

- **Python 3.10 smoke** (D-02 re-proof in-repo):
  `uv venv --python 3.10 /tmp/sif-mcp310-22 && uv pip install --python /tmp/sif-mcp310-22/bin/python -e . && /tmp/sif-mcp310-22/bin/python -c "from mcp.server import MCPServer; import sif.mcp.app"`
  -> `SMOKE OK 3.10.22 <class 'mcp.server.mcpserver.server.MCPServer'>`
- **Task 2 verifies:** `pytest tests/unit/mcp/test_app.py tests/unit/mcp/test_sdk_clients.py` (14 passed), `pytest tests/unit/mcp/test_backend.py` (99 passed), `pytest tests/integration/test_mcp_watch_e2e.py` (4 skipped: 3 marked + 1 runtime bridge), both greps.
- **Task 3 verifies:** `test_wire_transcripts + test_transport_security + test_stdout_purity` (18 passed), `test_mcp_watch_host + test_app + test_cli_mcp` (28 passed), `test_packaging` (3 passed), all three source greps (console_err present, writer present, no version literal in `app.py`).
- **Full phase gate:** `pytest` -> **2781 passed, 5 skipped, 95.06% coverage** (fail_under 90); `ruff check src tests`, `ruff format --check src tests`, `ty check src/sif` all green.

## Decisions Made

- See frontmatter `key-decisions`. The two most load-bearing: the `Annotated[CallToolResult, Model]` return annotation (schema without sacrificing the explicit builder) and registering tools/resources inside the lifespan where the backend is constructed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Golden/status schema assertion used `required` where defaulted fields produce none**
- **Found during:** Task 2 (`test_status_output_schema_is_published_from_the_output_model`)
- **Issue:** `StatusOutput` fields have defaults, so Pydantic emits no `required` array in `outputSchema`.
- **Fix:** Assert the published `properties` instead; the schema-presence contract is unchanged.
- **Files modified:** `tests/unit/mcp/test_app.py`
- **Committed in:** `23b60ee`

**2. [Rule 1 - Bug] Batched stdin + immediate EOF raced the SDK stdio connection**
- **Found during:** Task 3 (`test_stdout_purity.py`)
- **Issue:** Writing initialize, initialized, and status as one burst then closing stdin produced `-32000 Connection closed` for the status call.
- **Fix:** Drive the subprocess interactively (initialize, await response, then status), mirroring a real client.
- **Files modified:** `tests/unit/mcp/test_stdout_purity.py`
- **Committed in:** `771fb99`

**3. [Rule 3 - Blocking] pytest-flask's autouse fixture collided with a test fixture named `app`**
- **Found during:** Task 3 (`test_transport_security.py`)
- **Issue:** pytest-flask's `_monkeypatch_response_class` autouse fixture runs whenever a fixture named `app` exists and assumes Flask's `response_class`.
- **Fix:** Renamed the fixture to `mounted_app` (client depends on it).
- **Files modified:** `tests/unit/mcp/test_transport_security.py`
- **Committed in:** `771fb99`

### Plan Notes (not deviations)

- `src/sif/cli/commands/mcp.py` needed no edit: the preserved wrapper names (`run_stdio_server`, `run_http_server`) now delegate to `app.py`, so the CLI rewiring is entirely in `src/sif/mcp/cli.py`; the five existing CLI behavior tests stayed green.
- `test_mcp_watch_host.py` gained one additive test for the new helper; its existing 15 tests are untouched.
- The intermediate SDK surface registers only `status`. **This is a development-branch state: no release or PyPI publish may be cut from it.** 22-02's seven-tool battery is the gate that closes the gap before any release.
- `--allowed-hosts`, the `/health` Host guard, and the real daemon remain 22-03 scope; the `/health` bad-Host 200 behavior observed here is the documented C2 gap this plan does not close.

## Issues Encountered

- `uv lock` under uv 0.13.7 expanded `resolution-markers` blocks for Python 3.14 in addition to adding mcp's closure. Verified add-only (`git diff` shows no removed package version); D-03 forbids asserting exact transitive versions.
- The SDK emits `outputSchema`/`structuredContent` on 2024-era responses (C9). The goldens record this rather than normalizing it away; the real-client matrix is the compatibility proof.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 22-02 can now add the remaining six tools (`query`, `get`, `multi_get`, `metadata`, `lex_search`, `vec_search`) on the proven composition root, delete the dormant shell (`server.py`, `handlers.py`, `transports/`, the JSON-RPC wire types), and remove the e2e bridge.
- The five goldens must be regenerated with `SIF_UPDATE_WIRE_GOLDENS=1 pytest tests/unit/mcp/test_wire_transcripts.py` whenever the tool surface changes (22-02, 22-04, 22-05).
- 22-04 owns the actual lazy load, BM25 degradation on failure, and the cold-first-query purity extension; this plan only guarantees startup is model-free.
- No blockers introduced.

## Self-Check: PASSED

All 13 created source/test/golden files exist; both task commits (`23b60ee`, `771fb99`) are ancestors of HEAD.

