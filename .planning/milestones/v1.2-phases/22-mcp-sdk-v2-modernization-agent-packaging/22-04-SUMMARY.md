---
phase: 22-mcp-sdk-v2-modernization-agent-packaging
plan: 04
subsystem: mcp
tags: [mcp, lazy-embedder, prefix-routing, query-parity, rerank, snippets, stdout-purity, goldens]

# Dependency graph
requires:
  - phase: 22-mcp-sdk-v2-modernization-agent-packaging
    provides: "22-02 lazy-load skeleton, lex/vec direct paths, seven-tool surface"
  - phase: 22-mcp-sdk-v2-modernization-agent-packaging
    provides: "22-03 daemon arm-path quiet call and the composed HTTP roots"
  - phase: 19-search-correctness
    provides: "single enrichment owner and SearchOptions offset/min_score semantics"
  - phase: 21-scale-maintenance-embedder-identity
    provides: "loaded identity contract and identity-check semantics"
provides:
  - "One-attempt lazy embedder: _load_lock/_load_attempted/_load_failed, loaded identity dimension, latched failure with exactly one warning"
  - "Prefix-first query routing: lex:/BM25 direct BM25 with prefix stripped and zero loader calls; stripped-term BM25 degrade on latched load failure"
  - "Full CLI query parity: hoisted QueryExpansion/SmartSnippetExtractor/reranker, per-request SearchPipeline, one pipeline enrichment"
  - "rerank: bool | None on hybrid_search and the query tool (None follows SIF_RERANK_ENABLED; True/False override)"
  - "Soft-degraded rerank construction (ImportError/ValueError, latched, one warning) and execution (unranked page retry)"
  - "Cold-first-query stdio purity proof with a deliberately noisy stub loader, including the legacy docsift migration notice on stderr"
  - "Five era goldens regenerated for the additive rerank query parameter (only tools/list changed)"
affects: [22-05, 22-06, 22-07]

# Actuals (#2632) — pairs with the plan's `estimate` (98000 tokens, 3 tasks).
actuals:
  tokens: 16055
  tasks: 3
  commits: 3
plan_head_before: 0871ce05f25967018c3d300a2f26fb71007fe393
plan_head_after: 0bd57b7a56e2ef561e7793b55739321d3955118e

tech-stack:
  added: []
  patterns:
    - "Prefix-first load decision: split the query with the pipeline's own map, route BM25 directly, and only consult the loader for vector-touching routes"
    - "Hoisted heavy components + connection-bound pipeline constructed per request inside _run_in_db"
    - "Gate-before-construct rerank: the off path never imports the optional backend; construction failures latch with one warning"
    - "Execution-time rerank failure retries the same options with reranker=None instead of surfacing a tool error"
    - "Subprocess fixture drives the real CLI entrypoint with a patched lazy loader so the noisy load and migration notice share the production path"

key-files:
  created:
    - tests/unit/mcp/test_lazy_embedder.py
    - tests/unit/mcp/_stdio_fixture_server.py
  modified:
    - src/sif/mcp/backend.py
    - src/sif/mcp/tools.py
    - tests/unit/mcp/test_backend.py
    - tests/unit/mcp/test_tools.py
    - tests/unit/mcp/test_stdout_purity.py
    - tests/unit/mcp/goldens/2024-11-05.json
    - tests/unit/mcp/goldens/2025-03-26.json
    - tests/unit/mcp/goldens/2025-06-18.json
    - tests/unit/mcp/goldens/2025-11-25.json
    - tests/unit/mcp/goldens/2026-07-28.json

key-decisions:
  - "hybrid_search resolves the prefix with the pipeline's exact map (including the configured default_search_type) before any load; BM25 routes go straight to BM25Searcher so a lex: query cannot touch the loader."
  - "A latched load failure takes the direct BM25 fallback over the prefix-free text and never constructs SearchPipeline; the loader owns the single warning (D-15)."
  - "The lex:/BM25 direct route intentionally skips _apply_snippets; the documented deviation keeps snippet/line-range fields unset there, matching the dedicated lex_search tool, with citation served by get."
  - "Reranker construction is deferred to the first request that actually asks for one (including rerank=None following a true setting); the off path is zero-cost and never calls create_reranker."
  - "ImportError/ValueError reranker construction failures latch _reranker_failed and warn once; execution-time 'Reranking failed' RuntimeErrors warn and retry the same options with reranker=None."
  - "The stdout fixture drives sif.cli.main (via sys.argv) rather than app.run_stdio directly, so the pre-run docsift migration notice and the SDK fd diversion are both exercised on the production entrypoint."
  - "The MCP SearchResult model gains snippet in 22-05, so this plan proves the extractor is invoked on the query pipeline path rather than asserting a boundary field that does not exist yet."

patterns-established:
  - "Lazy-path seeding helper for tests: _load_attempted + stub manager/embedder/identity/dimension, no real model"
  - "Prefix/test split: zero-loader lex: proof with a failing _ensure_embedder patch, plus stripped-term degrade proof"
  - "Golden review gate re-run after regeneration: changed exchanges must be exactly ['tools/list'] for all five eras"

requirements-completed: [MCP-05, MCP-06]

coverage:
  - id: D1
    description: "Construction and status/lex/metadata/get/multi_get never call from_settings/load_model/get_identity; first query or vec_search loads once, reuses, and concurrent first requests share one attempt; loaded identity dimension governs the pipeline"
    requirement: MCP-05
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_lazy_embedder.py#TestNoLoadSurfaces"
        status: pass
      - kind: unit
        ref: "tests/unit/mcp/test_lazy_embedder.py#TestOneAttempt"
        status: pass
      - kind: unit
        ref: "tests/unit/mcp/test_lazy_embedder.py#TestLoadedDimension"
        status: pass
    human_judgment: false
  - id: D2
    description: "A lex:-prefixed query performs zero loader calls, BM25Searcher sees the stripped terms, and one enrichment runs; a vec:-prefixed query on a load-failure host degrades to BM25 over the stripped terms with exactly one warning"
    requirement: MCP-05
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_lazy_embedder.py#TestPrefixFirstRouting"
        status: pass
      - kind: e2e
        ref: "tests/integration/test_mcp_watch_e2e.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "A load failure warns once the install/model remedy, query returns BM25 rows, vec_search raises the remedy without retrying"
    requirement: MCP-06
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_lazy_embedder.py#TestHonestFailure"
        status: pass
      - kind: unit
        ref: "tests/unit/mcp/test_backend.py#TestHybridSearchIdentity::test_no_identity_passes_no_closure"
        status: pass
    human_judgment: false
  - id: D4
    description: "query uses QueryExpansion, SmartSnippetExtractor, and per-request SearchPipeline with hoisted components; rerank None/True/False follows the setting or overrides it; the off path never calls create_reranker; execution and construction failures soft-degrade with one warning and no retry"
    requirement: MCP-05
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_backend.py#TestQueryPipelineParity"
        status: pass
      - kind: unit
        ref: "tests/unit/mcp/test_backend.py#TestRerankOption"
        status: pass
      - kind: unit
        ref: "tests/unit/mcp/test_tools.py#TestQueryRerankOption"
        status: pass
    human_judgment: false
  - id: D5
    description: "A cold first query that triggers a noisy lazy load leaves stdout JSON-RPC only (noise on stderr), and the first query returns a real non-error page"
    requirement: MCP-06
    verification:
      - kind: e2e
        ref: "tests/unit/mcp/test_stdout_purity.py#test_cold_first_query_lazy_load_keeps_stdout_protocol_only"
        status: pass
      - kind: e2e
        ref: "tests/unit/mcp/test_stdout_purity.py#test_cold_stdio_stdout_emits_only_json_rpc_frames"
        status: pass
    human_judgment: false
  - id: D6
    description: "All five era goldens carry the additive optional rerank parameter in the query schema; the structural diff changes only tools/list"
    requirement: MCP-05
    verification:
      - kind: integration
        ref: "tests/unit/mcp/test_wire_transcripts.py"
        status: pass
      - kind: other
        ref: "structural golden diff: changed exchanges == ['tools/list'] for all five eras"
        status: pass
    human_judgment: false

# Metrics
duration: 12min
completed: 2026-11-16
status: complete
---

# Phase 22 Plan 04: Lazy Embedder, Query Pipeline Parity, and Cold-First-Query Purity Summary

**A single-attempt lazy embedder with prefix-first routing, full CLI query-pipeline parity with an opt-in soft-degrading reranker, and a cold-first-query stdio proof that a noisy model load stays off the protocol channel**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-11-16T15:58:00Z (approx.)
- **Completed:** 2026-11-16T16:10:00Z (approx.)
- **Tasks:** 3
- **Files changed:** 12 (2 source, 5 test/golden set, 5 goldens)

## Accomplishments

- `SearchBackend._ensure_embedder` is now the full D-15 policy: one lock, one attempt, `from_settings` -> `load_model` -> `get_identity`, cached manager/embedder/identity, and `_dimension` taken from the loaded identity (with the model dimension as the protocol-only-double fallback). A failure latches `_load_failed` and logs exactly one warning naming the `docsif[embed]` install and `SIF_MODEL_*` remedy; later requests never retry.
- `hybrid_search` routes prefixes before any load decision with the pipeline's own map. `lex:` (and a BM25-configured default) goes straight to `BM25Searcher` over the stripped terms with zero loader calls and exactly one `enrich_results`. Every vector-touching route calls `_ensure_embedder()`; on a latched failure it degrades to BM25 over the prefix-free text (so `vec:` is never ANDed into FTS) with the loader's single warning. On success the raw query goes to `SearchPipeline`, preserving its own routing.
- The direct BM25 route's snippet deviation is documented in the `hybrid_search` docstring: enriched BM25 rows with highlights, staleness, and suggestions, but no `_apply_snippets`; `lex_search` has none by design and `get` serves citation.
- Query now has full CLI parity: `QueryExpansion` attaches after a successful load, `SmartSnippetExtractor` is hoisted at construction, and a settings-driven reranker is built on the first request that asks for one. `SearchPipeline` is constructed per request over the fresh `_run_in_db` connection with `embedding_dim=self._dimension`, the identity closure, and exactly one pipeline enrichment.
- `rerank: bool | None = None` is additive on the backend and the `query` tool. `None` follows `SIF_RERANK_ENABLED`, `True`/`False` override, and the gate is checked before `create_reranker` so the off path is zero-cost. Construction failures (`ImportError` missing backend, `ValueError` unknown model type) warn once naming the cause/remedy, latch `_reranker_failed`, and return the unranked page. Execution failures (`Reranking failed: ...`) warn once and retry the same options with `reranker=None`.
- `set_quiet(True)` was already at both composition roots from 22-01; this plan proves the cold-first-query path with a new subprocess fixture whose stub loader deliberately prints a progress-bar line to stdout. Every stdout line is JSON-RPC, the noise lands on stderr, the legacy `docsift` migration notice stays on stderr, and the first query returns a real page.
- The five era goldens were regenerated for the additive `rerank` schema field; a structural diff confirms only `tools/list` changed and every initialize/status exchange stays byte-identical.

## Task Commits

Each task was committed atomically:

1. **Task 1: Lazy, single-attempt embedder with prefix-first routing** - `2672e38` (feat)
2. **Task 2: Full query pipeline parity, opt-in rerank, regenerated goldens** - `ee410e1` (feat)
3. **Task 3: Cold-first-query stdout purity and quiet lazy loads** - `0bd57b7` (feat)

**Plan metadata:** docs commit created after this SUMMARY (not counted in `actuals.commits`).

## Files Created/Modified

- `src/sif/mcp/backend.py` - `_split_query_prefix`, hardened `_ensure_embedder`, `_reranker_for`, `_build_pipeline`, prefix-first `hybrid_search`, loaded dimension
- `src/sif/mcp/tools.py` - additive `rerank` on `query`, reviewed opt-in description
- `tests/unit/mcp/test_lazy_embedder.py` - no-load/one-load/concurrency/failure/dimension/prefix matrix
- `tests/unit/mcp/_stdio_fixture_server.py` - seeded temp index, noisy stub loader, real CLI entrypoint
- `tests/unit/mcp/test_stdout_purity.py` - cold-first-query subprocess purity proof
- `tests/unit/mcp/test_backend.py` - lazy-path seeding, adapted identity/no-load tests, parity/rerank batteries
- `tests/unit/mcp/test_tools.py` - rerank forwarding and optional-schema proof
- `tests/unit/mcp/goldens/*.json` - regenerated `tools/list` for the rerank parameter

## Decisions Made

- See frontmatter `key-decisions`. The load-bearing ones: prefix-first routing mirrors the pipeline exactly, a failure degrades directly to BM25 (never constructing a pipeline), and rerank stays gate-before-construct with latched construction failure and retry-without-reranker on execution failure.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] The MCP `SearchResult` model has no `snippet` field until 22-05**
- **Found during:** Task 2 (snippet parity test)
- **Issue:** The plan asked for a test asserting snippets are present for query results, but `src/sif/mcp/protocol.py`'s `SearchResult` does not carry `snippet`/citation fields; 22-02's readiness note assigns those fields to 22-05, and `protocol.py` is not in this plan's files.
- **Fix:** The parity test asserts the CLI `SmartSnippetExtractor` is wired and actually invoked on the pipeline path (`extract` called), which is what this plan can prove without pre-empting 22-05's boundary fields. The extractor is still passed to every per-request pipeline.
- **Files modified:** `tests/unit/mcp/test_backend.py`
- **Verification:** `TestQueryPipelineParity::test_query_path_invokes_the_smart_snippet_extractor` passes against a real pipeline and seeded DB.
- **Committed in:** `ee410e1`

### Plan Notes (not deviations)

- `src/sif/mcp/app.py` needed no edit: `set_quiet(True)` was already the first statement in both `run_stdio` and `run_http` from 22-01, and the daemon arm path owns its own call from 22-03. The `grep -c "set_quiet(True)"` gate is satisfied at 2, and no `print(` exists in the module.
- The stdout fixture drives the real `sif.cli.main` entrypoint (via `sys.argv`) instead of calling `sif.mcp.app.run_stdio` directly. This exercises the production composition path, including the pre-run docsift migration notice; the patched lazy loader still intercepts the first query's load.
- The backend's parity/rerank wiring and its lazy-loader hardening live in one module and were finished before the first commit, so the `2672e38` snapshot already contains `_reranker_for`/`_build_pipeline`; Task 2's commit carries the tool surface, tests, and goldens.
- Ruff formatting of the touched MCP modules landed with Task 3's commit; no behavior changed.
- `_seed_loaded_embedder` seeds `_load_attempted`/stub manager/embedder/identity/dimension in existing pipeline-patching tests so they never reach the real ModelScope path, as the plan's adaptation note required.

---

**Total deviations:** 1 auto-fixed (blocking)
**Impact on plan:** The only adaptation was deferring a boundary-field assertion to 22-05; every behavior the plan specifies is implemented and tested.

## Issues Encountered

- The existing backend tests patched `SearchPipeline` while constructing model-free backends; once `hybrid_search` consulted the lazy loader, they needed a seeded loaded state. A shared `_seed_loaded_embedder` helper keeps them model-free and deterministic, and the no-identity test now exercises the real failed-load warning path.
- The fragment golden diff initially looked large because headers were re-serialized; the structural exchange comparison confirmed only `tools/list` payloads changed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 22-05 can add citation fields (`snippet`, `content_hash`, `line_start`, `line_end`) to the MCP `SearchResult`/`Document`; the pipeline already produces snippets, so 22-05 only needs the boundary remap and a golden re-run.
- Any tool-surface change must re-run `SIF_UPDATE_WIRE_GOLDENS=1 env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/mcp/test_wire_transcripts.py` and re-check that only `tools/list` exchanges changed.
- The lazy policy is now complete: startup and the no-load tools are model-free, failures are latched and honest, and cold-first-query stdout is proven clean.
- No blockers introduced.

## Self-Check: PASSED

All created files exist on disk; all three task commits (`2672e38`, `ee410e1`, `0bd57b7`) are ancestors of HEAD; the full suite is green at 2791 passed / 1 skipped / 95.09% coverage, with ruff check, ruff format --check, and ty check green.
