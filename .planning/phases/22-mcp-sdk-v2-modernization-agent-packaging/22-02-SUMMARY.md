---
phase: 22-mcp-sdk-v2-modernization-agent-packaging
plan: 02
subsystem: mcp
tags: [mcp, sdk-v2, tool-surface, annotations, toolerror, lex-search, vec-search, lazy-embedder, watch-e2e, golden-transcripts, shell-deletion]

# Dependency graph
requires:
  - phase: 22-mcp-sdk-v2-modernization-agent-packaging
    provides: "22-01 SDK composition root, dual-channel _result builder, status tool, era goldens, lazy-load skeleton"
  - phase: 21-scale-maintenance-embedder-identity
    provides: "identity check semantics (search mode warns/marks, dimension mismatch refuses) and the loaded-identity contract"
  - phase: 20-metadata-filtering-discovery
    provides: "frozen MetadataOutput envelope and the shared filter/match grammar"
  - phase: 19-search-correctness
    provides: "one enrich_results per direct search exit and SearchOptions offset/min_score semantics"
provides:
  - "Seven registered read-only tools: query, get, multi_get, status, metadata, lex_search, vec_search"
  - "TOOL_ANNOTATIONS (read_only_hint=True/open_world_hint=False) and reviewed TOOL_DESCRIPTIONS for all seven"
  - "ToolError boundary: filter/match validation, Pydantic validation, unknown collection, missing document, embedder/dimension/vec unavailability"
  - "SearchBackend.lex_search/vec_search direct CLI-parity paths with exactly one enrich_results"
  - "SearchBackend._ensure_embedder: one thread-safe lazy load, latched failure, settings-derived loaded identity"
  - "LexSearchInput/VecSearchInput.min_score additive fields"
  - "Seven-tool contract battery: ordered enumeration, annotation/description honesty, outputSchema presence, empty-index status, seven-tool idempotency, wire-level isError proofs, _METADATA_ENVELOPE oracle"
  - "Five era goldens regenerated for the seven-tool tools/list surface (initialize/status byte-identical)"
  - "Deleted hand-rolled shell: server.py, handlers.py, transports/, JSON-RPC wire types, four replaced test modules"
affects: [22-03, 22-04, 22-05, 22-06, 22-07]

# Actuals (#2632) — pairs with the plan's `estimate` (92000 tokens, 3 tasks).
actuals:
  tokens: 103598
  tasks: 3
  commits: 3
plan_head_before: 9471f2f9565e17f66fafe59e84246668015cbbb7
plan_head_after: 48d5a98145cabd9b616903858f2959f6758df3f4

tech-stack:
  added: []
  patterns:
    - "Per-tool registration helper with one nested @mcp.tool function (keeps mccabe <= 10 while preserving deterministic order)"
    - "Annotated[CallToolResult, OutputModel] return annotation: SDK derives outputSchema, explicit builder controls both channels"
    - "Shared _resolve_collection_ids/_map_core_results helpers so hybrid/lex/vec cannot drift"
    - "RuntimeError-to-ToolError mapping at the vec_search tool boundary for the D-15 remedy surface"
    - "Golden regeneration verified by structural diff: only tools/list changes, handshake/status sections byte-identical"

key-files:
  created:
    - tests/unit/mcp/test_tools.py
  modified:
    - src/sif/mcp/tools.py
    - src/sif/mcp/backend.py
    - src/sif/mcp/protocol.py
    - tests/unit/mcp/test_backend.py
    - tests/unit/mcp/test_app.py
    - tests/unit/mcp/test_sdk_clients.py
    - tests/unit/mcp/test_wire_transcripts.py
    - tests/test_version_identity.py
    - tests/integration/test_mcp_watch_e2e.py
    - tests/unit/mcp/goldens/2024-11-05.json
    - tests/unit/mcp/goldens/2025-03-26.json
    - tests/unit/mcp/goldens/2025-06-18.json
    - tests/unit/mcp/goldens/2025-11-25.json
    - tests/unit/mcp/goldens/2026-07-28.json
  deleted:
    - src/sif/mcp/server.py
    - src/sif/mcp/handlers.py
    - src/sif/mcp/transports/__init__.py
    - src/sif/mcp/transports/stdio.py
    - src/sif/mcp/transports/http.py
    - tests/unit/mcp/test_server.py
    - tests/unit/mcp/test_transports_http.py
    - tests/unit/mcp/test_transports_stdio.py
    - tests/unit/mcp/test_integration.py

key-decisions:
  - "Every tool keeps the 22-01 Annotated[CallToolResult, OutputModel] return annotation instead of the plan's literal output-model + type: ignore: outputSchema derivation is unchanged, both channels stay explicit, and ty needs no suppression."
  - "Registration is split into one helper per tool; one monolithic register_tools exceeded mccabe 10 because nested tool bodies count toward the outer complexity."
  - "The frozen `filter` wire name is preserved with a parameter-line noqa: A002; renaming it would silently change the published input schema."
  - "vec_search maps RuntimeError (no embedder, identity dimension mismatch, missing sqlite-vec) to ToolError with the shared remedy; other exceptions on other tools stay unexpected and SDK-sanitized."
  - "_ensure_embedder stores the loaded identity only when it is a real EmbedderIdentity (21-04 injected-double precedent), and caches self._manager for reuse."
  - "The ported metadata oracle records the real Phase 20 envelope for the two-document fixture, including typed path/mtime builtIn summaries; the old integration oracle mocked the backend and carried empty types."
  - "Deletion happened only after the seven-tool battery, version identity, watch e2e, and regenerated goldens were green; the golden diff was verified structurally before committing."

patterns-established:
  - "Read-only honesty battery: exact ordered tool set, annotation fields, description constants, non-empty outputSchema, future-write policy helper"
  - "Idempotency proof: every tool called twice on a real tmp DB with unchanged PRAGMA data_version and table counts"
  - "Wire error proof: expected failures are HTTP-200 results with isError=True and no JSON-RPC error member"
  - "Golden review: parse HEAD:golden vs working golden and assert every exchange except tools/list is byte-identical"

requirements-completed: [MCP-02, MCP-05]

coverage:
  - id: D1
    description: "Seven read-only tools registered in the exact deterministic order with read_only_hint=True, open_world_hint=False, omitted idempotent/destructive hints, reviewed descriptions, and a non-empty outputSchema each"
    requirement: MCP-02
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_tools.py#TestSevenToolEnumeration"
        status: pass
      - kind: integration
        ref: "tests/unit/mcp/test_wire_transcripts.py#test_wire_transcript_matches_golden"
        status: pass
    human_judgment: false
  - id: D2
    description: "Expected tool-input failures surface as ToolError at the function boundary and isError=True at the wire, never as JSON-RPC protocol errors"
    requirement: MCP-02
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_tools.py#test_expected_errors_are_iserror_results_not_protocol_errors"
        status: pass
      - kind: unit
        ref: "tests/unit/mcp/test_tools.py#TestMetadataTool"
        status: pass
    human_judgment: false
  - id: D3
    description: "lex_search/vec_search mirror the CLI one-shot commands with filter/offset/per_chunk/min_score, one enrich_results, identity-before-embed, and an additive min_score schema field"
    requirement: MCP-05
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_backend.py#TestLexSearchDirectPath"
        status: pass
      - kind: unit
        ref: "tests/unit/mcp/test_backend.py#TestVecSearchDirectPath"
        status: pass
      - kind: unit
        ref: "tests/unit/mcp/test_tools.py#TestLexAndVecSearchTools"
        status: pass
    human_judgment: false
  - id: D4
    description: "All seven tools deep-compare parsed text to structuredContent and are idempotent on a real tmp DB; the frozen metadata envelope matches the ported oracle in both channels"
    requirement: MCP-02
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_tools.py#test_all_seven_tools_are_dual_channel_and_idempotent"
        status: pass
      - kind: unit
        ref: "tests/unit/mcp/test_tools.py#test_envelope_oracle_matches_both_channels"
        status: pass
    human_judgment: false
  - id: D5
    description: "The dormant hand-rolled shell, JSON-RPC wire types, and four replaced test modules are deleted; no Python import or reference survives"
    requirement: MCP-02
    verification:
      - kind: other
        ref: "test ! -e src/sif/mcp/server.py && test ! -e src/sif/mcp/handlers.py && test ! -d src/sif/mcp/transports; grep -rn --include='*.py' 'from sif.mcp.server|from sif.mcp.handlers|from sif.mcp.transports' src tests (exit 1)"
        status: pass
    human_judgment: false
  - id: D6
    description: "The five era goldens are regenerated for the seven-tool tools/list surface with the initialize handshake and tools/call status sections byte-identical"
    requirement: MCP-02
    verification:
      - kind: integration
        ref: "tests/unit/mcp/test_wire_transcripts.py"
        status: pass
      - kind: other
        ref: "structural golden diff: changed exchanges == ['tools/list'] for all five eras"
        status: pass
    human_judgment: false
  - id: D7
    description: "The 22-01 watch bridge is gone and all four watch e2e proofs pass live against the seven-tool surface, including the lex: watch-refresh and responsiveness proofs"
    requirement: MCP-05
    verification:
      - kind: e2e
        ref: "tests/integration/test_mcp_watch_e2e.py"
        status: pass
    human_judgment: false
  - id: D8
    description: "The MCP release-identity surface asserts the app.py composition seam and points at the SDK client's serverInfo.version wire assertion"
    verification:
      - kind: unit
        ref: "tests/test_version_identity.py#test_runtime_version_surfaces_agree"
        status: pass
      - kind: integration
        ref: "tests/unit/mcp/test_sdk_clients.py#test_in_process_client_modes"
        status: pass
    human_judgment: false

# Metrics
duration: 15min
completed: 2026-11-16
status: complete
---

# Phase 22 Plan 02: Seven-Tool MCP Surface + Shell Deletion Summary

**Seven honestly annotated read-only MCP tools with CLI-parity lex/vec search and ToolError semantics, proven dual-channel and idempotent before the 623-line hand-rolled shell, its wire types, and four replaced test modules were deleted**

## Performance

- **Duration:** 15 min
- **Started:** 2026-11-16T07:20:32Z
- **Completed:** 2026-11-16T07:36:29Z
- **Tasks:** 3
- **Files modified:** 24 (5 source, 10 test, 5 goldens, 4 deleted test modules)

## Accomplishments

- `query`, `get`, `multi_get`, `status`, `metadata`, `lex_search`, and `vec_search` are registered in the exact D-06 order, each with `read_only_hint=True`/`open_world_hint=False`, no idempotent/destructive hints, a reviewed description constant, and an `outputSchema` derived from its preserved Pydantic model.
- Every tool coerces through its preserved input model and maps expected failures to `ToolError`: invalid filter/match ASTs, Pydantic validation, an unknown collection, a missing document, and the vec embedder/dimension/vec-unavailability remedy. The wire shows `isError=True` inside a successful JSON-RPC envelope.
- `lex_search` calls `BM25Searcher` with filter/offset/min_score and exactly one `enrich_results`; `vec_search` ensures the lazy manager, evaluates the Phase 21 identity check before `embed_query`, constructs `VectorSearcher` from the embedding length, and enriches once with the correct untrusted flag. Neither expands nor reranks.
- The lazy embedder loads once under `_load_lock`, latches failure, forwards the backend settings, and stores the loaded identity; the hybrid path keeps its BM25 degradation.
- The seven-tool battery proves the ordered set, annotation/description honesty, non-empty output schemas, empty-index status, dual-channel deep equality, repeated-read idempotency (`PRAGMA data_version` + row counts unchanged), wire-level `isError`, and the ported frozen-envelope oracle.
- The 22-01 watch bridge is removed; all four real-subprocess watch proofs pass live on the seven-tool surface, including the `lex:` refresh and responsiveness assertions.
- The five era goldens are regenerated for the seven-tool `tools/list`; a structural diff confirms only `tools/list` changed and the `initialize`/`tools/call status` sections stay byte-identical.
- `src/sif/mcp/{server,handlers,transports}`, the JSON-RPC wire types/helpers, and the four replaced test modules are deleted; the SDK composition root is the only serving path.

## Task Commits

Each task was committed atomically:

1. **Task 1: Register the five read-capable tools with reviewed descriptions and ToolError semantics** - `087dd18` (feat)
2. **Task 2: Wire `lex_search`/`vec_search` direct paths with additive `min_score`** - `63b9580` (feat)
3. **Task 3: Prove the seven-tool contract, restore the watch e2e, delete the superseded shell** - `48d5a98` (feat)

**Plan metadata:** docs commit created after this SUMMARY (not counted in `actuals.commits`).

## Files Created/Modified

- `src/sif/mcp/tools.py` - seven `@mcp.tool` registrations via per-tool helpers, shared `_result`/`_parse_filter_node`, reviewed descriptions, ToolError mapping, docs resource intact
- `src/sif/mcp/backend.py` - `_ensure_embedder`, `lex_search`, `vec_search`, shared `_resolve_collection_ids`/`_map_core_results`, `VECTOR_SEARCH_REMEDY`
- `src/sif/mcp/protocol.py` - `min_score` added to Lex/Vec inputs; JSON-RPC wire types and helper factories deleted, SIF I/O models retained
- `tests/unit/mcp/test_tools.py` - 52-test contract battery (five-tool forwarding/errors, lex/vec parity, seven-tool enumeration, idempotency, wire error proof, envelope oracle)
- `tests/unit/mcp/test_backend.py` - lex/vec direct-path and `_ensure_embedder` tests added; superseded handler blocks deleted (79 tests)
- `tests/unit/mcp/test_app.py`, `test_sdk_clients.py` - surface assertions extended to the seven-tool order; status looked up by name
- `tests/unit/mcp/test_wire_transcripts.py` - 2024 golden assertion finds `status` by name and asserts seven tools
- `tests/test_version_identity.py` - MCP release identity asserts `build_server` name/version and references the SDK-client wire assertion
- `tests/integration/test_mcp_watch_e2e.py` - bridge removed, all four proofs live, lazy/prefix-routed model comment corrected
- `tests/unit/mcp/goldens/*.json` - five regenerated seven-tool `tools/list` transcripts
- Deleted: `src/sif/mcp/server.py`, `handlers.py`, `transports/`, `tests/unit/mcp/test_{server,transports_http,transports_stdio,integration}.py`

## Decisions Made

- Per-tool registration helpers keep one nested tool function each, so `register_tools` stays under mccabe 10 without a suppression while preserving deterministic registration order.
- `Annotated[CallToolResult, OutputModel]` (22-01's pattern) is used for every return annotation rather than the plan's literal model + `type: ignore`; `outputSchema` derivation and the explicit dual-channel builder are unchanged.
- The frozen `filter` wire name keeps a parameter-line `# noqa: A002`; renaming it would change the published schema.
- `vec_search` converts only `RuntimeError` to `ToolError` (missing embedder, identity dimension mismatch, missing sqlite-vec); unexpected exceptions on other tools remain SDK-sanitized.
- `_ensure_embedder` stores only a real `EmbedderIdentity` (21-04 injected-double precedent), keeping double-driven tests policy-free.
- The ported metadata oracle records the real two-document envelope, including typed path/mtime builtIn summaries; the old mocked oracle's empty `types` would have made a "deep equality" test untruthful.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Existing tests pinned the intermediate one-tool SDK surface**
- **Found during:** Task 1 (five-tool registration)
- **Issue:** `test_app.py` and `test_sdk_clients.py` asserted `tools/list == ["status"]`, the 22-01 dev-branch state; the plan's `files_modified` did not list them.
- **Fix:** Extended both assertions to the ordered five-tool set in Task 1 and the seven-tool set in Task 2; the status schema test now finds `status` by name.
- **Files modified:** `tests/unit/mcp/test_app.py`, `tests/unit/mcp/test_sdk_clients.py`
- **Verification:** Both modules pass in the full suite.
- **Committed in:** `087dd18`, `63b9580`

**2. [Rule 1 - Bug] SDK wraps ToolError text with the tool name**
- **Found during:** Task 1 (invalid-filter tool test)
- **Issue:** The high-level SDK prefixes `ToolError` messages with `Error executing tool <name>: `, so a `startswith("filter.")` assertion failed even though the remedy text was intact.
- **Fix:** Assert the remedy substrings (`filter.gt:` / `filter.<op>:`) rather than the absolute prefix.
- **Files modified:** `tests/unit/mcp/test_tools.py`
- **Verification:** ToolError mapping tests pass for query and metadata.
- **Committed in:** `087dd18`

**3. [Rule 1 - Bug] Ported metadata oracle had empty builtIn type summaries**
- **Found during:** Task 1 (envelope oracle)
- **Issue:** The old `test_integration.py` oracle mocked the backend, so its `builtIns` carried `types: []`; the real Phase 20 discovery emits typed path/mtime summaries, making deep equality fail on the same fixture.
- **Fix:** Recorded the real Phase 20 envelope for the two-document fixture as the oracle (typed builtIns, exact counts, no nulls) and rely on the real backend for the deep comparison.
- **Files modified:** `tests/unit/mcp/test_tools.py`
- **Verification:** `test_envelope_oracle_matches_both_channels` passes against the real backend.
- **Committed in:** `087dd18`

**4. [Rule 1 - Bug] Monolithic register_tools tripped mccabe 10 and A002 placement**
- **Found during:** Task 1 (ruff gate)
- **Issue:** Five nested tool bodies pushed `register_tools` to complexity 13, and the `# noqa: A002` on the `def` line did not suppress the parameter diagnostic.
- **Fix:** Split registration into one helper per tool and moved the A002 suppression onto the frozen `filter` parameter line.
- **Files modified:** `src/sif/mcp/tools.py`
- **Verification:** `ruff check src tests` and `ty check src/sif` green; the published schema is unchanged.
- **Committed in:** `087dd18`

**5. [Rule 3 - Blocking] 2024 golden test assumed `status` was the first tool**
- **Found during:** Task 3 (golden regeneration)
- **Issue:** The seven-tool expansion makes `status` the fourth `tools/list` entry, so the `tools[0]["name"] == "status"` assertion would fail after regeneration.
- **Fix:** Look `status` up by name and assert the seven-entry surface; the C9 structured-output intent is unchanged.
- **Files modified:** `tests/unit/mcp/test_wire_transcripts.py`
- **Verification:** Wire transcript tests pass against the regenerated goldens.
- **Committed in:** `48d5a98`

### Plan Notes (not deviations)

- The plan's Task 2 text asked for "the same localized `# type: ignore[return-value]` used by the other tools"; the other tools do not use one. 22-01's `Annotated[CallToolResult, OutputModel]` pattern was used consistently instead, which keeps `outputSchema` derivation and avoids suppressions.
- The handler-test disposition list named five port blocks and three deletions; all 20 `sif.mcp.handlers` imports are gone from `test_backend.py`, and the ported assertions live in `test_tools.py` before the handlers module was deleted.

---

**Total deviations:** 5 auto-fixed (3 bugs, 2 blocking)
**Impact on plan:** All fixes were necessary to keep the suite green and the ported oracle truthful; no scope creep and no public-contract change.

## Issues Encountered

- The full suite pass count changed from 2781 to 2744 because four replaced test modules were deleted and the new batteries are more consolidated; coverage remains above the 90% gate (94.94%).
- The test PostgreSQL/Flask-style fixtures were unaffected; the only environment wrinkle was sqlite-vec needing to be loaded into the idempotency monitor connection before counting `document_embeddings`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 22-03 can add `--allowed-hosts`, the `/health` Host guard, and the real daemon on the one surviving composition root; the old middleware is gone, so transport security has a single SDK-owned path.
- 22-04 owns the hardened lazy policy: warning/BM25-degrade on load failure, loaded-dimension use after success, and the cold-first-query stdout purity extension. The `_ensure_embedder` seam and `_load_*` latches are in place.
- 22-05 must add citation fields (`snippet`, `content_hash`, `line_start`, `line_end`) to the MCP `SearchResult`/`Document` and re-run the golden writer; the current descriptions already state the intended citation fields.
- The five goldens must be regenerated with `SIF_UPDATE_WIRE_GOLDENS=1 pytest tests/unit/mcp/test_wire_transcripts.py` whenever the tool surface changes (22-04, 22-05).
- No blockers introduced.

## Self-Check: PASSED

All seven registered tool names are present in `tests/unit/mcp/test_tools.py`, the four task-3 absence gates pass, the three task commits (`087dd18`, `63b9580`, `48d5a98`) are ancestors of HEAD, and the full suite is green at 2744 passed / 1 skipped / 94.94% coverage.
