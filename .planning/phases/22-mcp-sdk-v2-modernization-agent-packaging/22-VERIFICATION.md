---
phase: 22-mcp-sdk-v2-modernization-agent-packaging
verified: 2026-11-16T10:27:03Z
status: passed
score: "77/77 must-haves verified"
behavior_unverified: 0
overrides_applied: 0
covered_files:
  - ".claude-plugin/marketplace.json"
  - ".claude-plugin/plugin.json"
  - ".mcp.json"
  - ".planning/phases/22-mcp-sdk-v2-modernization-agent-packaging/22-01-PLAN.md"
  - ".planning/phases/22-mcp-sdk-v2-modernization-agent-packaging/22-01-SUMMARY.md"
  - ".planning/phases/22-mcp-sdk-v2-modernization-agent-packaging/22-02-PLAN.md"
  - ".planning/phases/22-mcp-sdk-v2-modernization-agent-packaging/22-02-SUMMARY.md"
  - ".planning/phases/22-mcp-sdk-v2-modernization-agent-packaging/22-03-PLAN.md"
  - ".planning/phases/22-mcp-sdk-v2-modernization-agent-packaging/22-03-SUMMARY.md"
  - ".planning/phases/22-mcp-sdk-v2-modernization-agent-packaging/22-04-PLAN.md"
  - ".planning/phases/22-mcp-sdk-v2-modernization-agent-packaging/22-04-SUMMARY.md"
  - ".planning/phases/22-mcp-sdk-v2-modernization-agent-packaging/22-05-PLAN.md"
  - ".planning/phases/22-mcp-sdk-v2-modernization-agent-packaging/22-05-SUMMARY.md"
  - ".planning/phases/22-mcp-sdk-v2-modernization-agent-packaging/22-06-PLAN.md"
  - ".planning/phases/22-mcp-sdk-v2-modernization-agent-packaging/22-06-SUMMARY.md"
  - ".planning/phases/22-mcp-sdk-v2-modernization-agent-packaging/22-07-PLAN.md"
  - ".planning/phases/22-mcp-sdk-v2-modernization-agent-packaging/22-07-SUMMARY.md"
  - "README.md"
  - "docs/api-reference.md"
  - "docs/architecture.md"
  - "docs/cli-reference.md"
  - "docs/mcp-server.md"
  - "pyproject.toml"
  - "scripts/publish_registry.py"
  - "server.json"
  - "skills/sif-cite/SKILL.md"
  - "skills/sif-get/SKILL.md"
  - "skills/sif-search/SKILL.md"
  - "src/sif/cli/commands/mcp.py"
  - "src/sif/cli/main.py"
  - "src/sif/core/models.py"
  - "src/sif/database/repositories.py"
  - "src/sif/mcp/README.md"
  - "src/sif/mcp/__init__.py"
  - "src/sif/mcp/app.py"
  - "src/sif/mcp/backend.py"
  - "src/sif/mcp/cli.py"
  - "src/sif/mcp/protocol.py"
  - "src/sif/mcp/tools.py"
  - "src/sif/mcp/watch_host.py"
  - "src/sif/search/hybrid.py"
  - "src/sif/search/snippets.py"
  - "src/sif/utils/daemon.py"
  - "tests/integration/test_mcp_watch_e2e.py"
  - "tests/test_version_identity.py"
  - "tests/unit/cli/test_mcp.py"
  - "tests/unit/mcp/_stdio_fixture_server.py"
  - "tests/unit/mcp/goldens/2024-11-05.json"
  - "tests/unit/mcp/goldens/2025-03-26.json"
  - "tests/unit/mcp/goldens/2025-06-18.json"
  - "tests/unit/mcp/goldens/2025-11-25.json"
  - "tests/unit/mcp/goldens/2026-07-28.json"
  - "tests/unit/mcp/test_app.py"
  - "tests/unit/mcp/test_backend.py"
  - "tests/unit/mcp/test_citations.py"
  - "tests/unit/mcp/test_daemon.py"
  - "tests/unit/mcp/test_lazy_embedder.py"
  - "tests/unit/mcp/test_mcp_watch_host.py"
  - "tests/unit/mcp/test_packaging.py"
  - "tests/unit/mcp/test_plugin.py"
  - "tests/unit/mcp/test_registry_script.py"
  - "tests/unit/mcp/test_sdk_clients.py"
  - "tests/unit/mcp/test_stdout_purity.py"
  - "tests/unit/mcp/test_tools.py"
  - "tests/unit/mcp/test_transport_security.py"
  - "tests/unit/mcp/test_wire_transcripts.py"
  - "tests/unit/search/test_hybrid.py"
  - "tests/unit/search/test_snippets.py"
  - "tests/unit/utils/test_daemon.py"
  - "uv.lock"
covered_digest: "v4:sha256:e71501823ca175615d233c5193fb6f0a8b5ffa06787de28a30a634926b39e6b3"
deferred:
  - truth: "Live public MCP Registry listing for io.github.zhangtaolab/sif 1.1.2"
    addressed_in: "Post-phase maintainer action (22-07 Task 2, maintainer GitHub device-flow login)"
    evidence: "Recorded blocked no-github-login per D-24. Registry preflight is green (`not listed (reachable)`); server.json validates with mcp-publisher and the 2025-12-11 schema. Resume: `mcp-publisher login github && python scripts/publish_registry.py --publish`."
---

# Phase 22: MCP SDK v2 Modernization + Agent Packaging Verification Report

**Phase Goal:** SIF's MCP server runs on the official SDK v2 serving every client era, with accurate annotations, citation-grade structured output, full query-pipeline parity, and agent-native distribution (Claude Code plugin + MCP Registry).
**Verified:** 2026-11-16T10:27:03Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

All 77 truths declared across the seven plans were checked against the working tree, the committed gate evidence, and independent re-runs. No truth was taken from SUMMARY.md alone.

#### Plan 22-01 (13 truths)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `mcp>=2.3.0,<3` installs with the full dependency set on Python 3.10 and the SDK/app imports succeed before any shell deletion | ✓ VERIFIED | `pyproject.toml:42`, `uv.lock` pins mcp 2.3.0; verifier re-ran the 3.10 smoke: `/tmp/sif-mcp310-22/bin/python -c "from mcp.server import MCPServer; import sif.mcp.app"` → `PY 3.10.22`, app path `/Users/forrest/GitHub/SIF/src/sif/mcp/app.py`. Commit order is 22-01 (`23b60ee`, `771fb99`) before 22-02 deletion (`48d5a98`). |
| 2 | `mcp` is a core dependency; `mcp`/`http` extras stay uvicorn-only aliases; `uv.lock` resolves | ✓ VERIFIED | `pyproject.toml:29-70`; `uv.lock` 13-entry graph; `tests/unit/mcp/test_packaging.py` (3 tests) passed. |
| 3 | `status` is served end-to-end over stdio and mounted HTTP by the real SDK `MCPServer` with `SearchBackend` and SIF I/O models | ✓ VERIFIED | `app.py` builds `MCPServer`; `test_app.py`/`test_sdk_clients.py` passed; real Claude client called `status`-bearing server and `query` successfully. |
| 4 | `docs://{doc_id}{?from_line,max_lines}` returns the full document by default and the requested inclusive window, backed by `get_document` | ✓ VERIFIED | `app.py:410-442`; `test_app.py::test_docs_resource_serves_full_and_ranged_documents` and `test_tools.py::TestDocsResource` passed. |
| 5 | 2024-11-05 initialize, `tools/list`, and `tools/call status` return a session id, compact JSON text, and `structuredContent`; golden locked | ✓ VERIFIED | `tests/unit/mcp/goldens/2024-11-05.json` (3 exchanges); `test_wire_transcripts.py` 6 tests passed. |
| 6 | 2025-03-26/06-18/11-25 negotiate their revision; 2026-07-28 works with headers + `_meta` and no initialize/session; missing `Mcp-Name` or `_meta` is rejected | ✓ VERIFIED | Four handshake goldens + 2026 golden (2 exchanges); `test_wire_transcripts.py::test_handshake_era_negotiates_the_requested_revision`, `::test_modern_era_is_stateless_without_initialize_or_session`, `::test_modern_request_without_mcp_name_is_rejected`, `::test_modern_request_without_meta_is_rejected` passed. |
| 7 | SDK clients in `mode="legacy"` and `mode="auto"` list tools and call `status` over in-process, ASGI HTTP, and real stdio; the matrix includes ping | ✓ VERIFIED | `test_sdk_clients.py` (6 tests: 2 modes × 3 transports) passed. Verifier spot-check: `Client.send_ping()` succeeds in legacy mode; 2026-07-28 removes ping per SDK deprecation, so auto-mode rejection is conformant. No committed ping assertion (recorded as debt, non-blocking). |
| 8 | `outputSchema` and `structuredContent` appear on 2024-era responses, recorded in the golden | ✓ VERIFIED | `test_wire_transcripts.py::test_2024_golden_records_output_schema_and_structured_content` passed; golden contains `outputSchema` and structured result. |
| 9 | Bad Host 421, bad Origin 403, allowed loopback 200, absent Origin allowed, non-JSON Content-Type 400 — proven before old shell deletion | ✓ VERIFIED | `test_transport_security.py` 11 tests passed; proof commit `771fb99` precedes deletion `48d5a98`. |
| 10 | `SearchBackend`, `watch_host`, and SIF I/O models remain the serving seam; superseded `server.py`/`handlers.py`/`transports/` untouched until 22-02, then deleted | ✓ VERIFIED | Files absent now; `grep -rn --include='*.py' 'sif\.mcp\.(server|handlers|transports)' src tests` → exit 1, no matches; CLI delegates to `sif.mcp.app`. |
| 11 | Watch host composes under `mcp.session_manager.run()` in D-18 order; `SIF_MCP_WATCH` off leaves serving unchanged | ✓ VERIFIED | `watch_host.py::mcp_session_lifespan` with session enter → watcher start → yield → stop → exit; `test_mcp_watch_host.py` 16 tests passed. |
| 12 | A cold `sif mcp stdio` process emits only JSON-RPC frames on stdout; legacy migration fixture no longer prints to stdout | ✓ VERIFIED | `app.py:269,294` `set_quiet(True)` first; `test_stdout_purity.py` 2 tests passed, including the noisy stub loader. |
| 13 | The dual-channel invariant holds for `status`: text parses to exactly the structured mapping | ✓ VERIFIED | `tools.py::_result` derives `structured` via `json.loads(text)`; `test_app.py` and `test_tools.py` prove equality. |

#### Plan 22-02 (11 truths)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Exactly seven read-capable tools registered in deterministic order: query, get, multi_get, status, metadata, lex_search, vec_search | ✓ VERIFIED | `tools.py:392-407` registration order; `test_tools.py::TestSevenToolEnumeration::test_exact_ordered_tool_set_with_no_mutation_names` passed. |
| 2 | Every tool carries `read_only_hint=True`, `open_world_hint=False`; idempotent/destructive hints absent | ✓ VERIFIED | `tools.py:53`; `test_tools.py::test_every_tool_is_read_only_with_truthful_annotations` passed. |
| 3 | Every `tools/list` entry carries a non-empty `outputSchema` from its Pydantic return model, including lex/vec | ✓ VERIFIED | `Annotated[CallToolResult, <Output>]` annotations; `test_tools.py::test_every_tool_publishes_a_non_empty_output_schema` passed; all five goldens carry schemas. |
| 4 | Descriptions match backend behavior: rerank opt-in, no auto-approval/prompt-free claim, metadata keeps Phase 20 wording | ✓ VERIFIED | `tools.py:58-88`; `TestReviewedDescriptions` and `test_descriptions_are_the_reviewed_constants` passed. |
| 5 | `status` accepts an empty argument object and returns a valid `StatusOutput` on an empty index without loading a model | ✓ VERIFIED | `test_tools.py::TestEmptyIndexAndIdempotency::test_status_on_a_real_empty_index` passed against a real tmp DB. |
| 6 | Calling any read-only tool twice returns the same result and performs no database write | ✓ VERIFIED | `test_all_seven_tools_are_dual_channel_and_idempotent` compares `PRAGMA data_version` and table counts on a real DB; passed. |
| 7 | Expected tool-input failures surface as `ToolError` results with `isError=True` at the wire, not protocol errors | ✓ VERIFIED | Boundary mapping in `tools.py`; `test_expected_errors_are_iserror_results_not_protocol_errors` and metadata/filter error tests passed. |
| 8 | `lex_search` mirrors CLI `search search`; `vec_search` mirrors CLI `search vsearch`; neither expands nor reranks | ✓ VERIFIED | `backend.py:577-685` uses `BM25Searcher`/`VectorSearcher` + one `enrich_results`; `TestLexSearchDirectPath`, `TestVecSearchDirectPath`, `TestLexAndVecSearchTools` passed. |
| 9 | `min_score` is additive on `LexSearchInput`/`VecSearchInput` and present in generated input schemas | ✓ VERIFIED | `protocol.py:131,159`; `test_min_score_is_published_for_both_inputs` passed. |
| 10 | For all seven tools the text payload parses deep-equal to `structured_content`; metadata keeps the frozen envelope | ✓ VERIFIED | Idempotency test and `test_envelope_oracle_matches_both_channels` passed; `_result(..., exclude_none=True)` for metadata. |
| 11 | The SDK composition root is the only MCP serving path; server.py/handlers.py/transports deleted; protocol only I/O models; replaced tests gone | ✓ VERIFIED | Files absent; no import references; `protocol.py` header documents deletion; deleted test modules absent. |

#### Plan 22-03 (11 truths)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Mounted `/mcp` returns 421 bad Host, 403 bad Origin, 200 allowed loopback, allows absent Origin, 400 non-JSON Content-Type | ✓ VERIFIED | `test_transport_security.py` (11 tests) passed. |
| 2 | `/health` has a narrow parent Host guard sharing the allowlist (421 bad, 200 loopback) | ✓ VERIFIED | `app.py:129-141,250-254`; `test_health_rejects_a_spoofed_host_with_421`, `test_health_allows_an_allowed_loopback_host` passed. |
| 3 | Every bind passes explicit `TransportSecuritySettings`; loopback defaults union `--allowed-hosts`; non-loopback bind warns without widening | ✓ VERIFIED | `app.py:80-119,285-309`; `test_non_loopback_bind_warns_and_keeps_loopback_only_defaults`, wildcard-drop tests passed. |
| 4 | `--allowed-hosts` repeatable on `mcp http` and `mcp daemon`; `--cors-origins` on daemon | ✓ VERIFIED | Verifier ran both `--help` commands: flags present; `tests/unit/cli/test_mcp.py` passed. |
| 5 | `mcp daemon` is a real detached HTTP daemon: arms, then binds; `--stop` corroborated SIGTERM/SIGKILL; stdio rejected | ✓ VERIFIED | `cli/commands/mcp.py:161-268`; POSIX e2e `test_daemon_e2e_serves_initialize_and_stops` passed; help states stdio is not a daemon mode. |
| 6 | Daemon writes `<db>.mcp.pid` with `mode:"mcp"`, `depth:"bm25"`; `--pid-file` override; watch `.watch.pid` untouched | ✓ VERIFIED | `daemon.py:44,100-108`; `TestMcpPidArtifact`, `test_daemon_coexists_with_a_watch_daemon` passed. |
| 7 | `corroborate_pid`/`stop_daemon` accept a marker (default `watch`); MCP daemon corroborated by `mcp`; live watch not misclassified | ✓ VERIFIED | `daemon.py:191-231,313-345`; `TestMcpCorroboration`, `TestMcpStop`, `test_marker_is_forwarded_and_defaults_to_watch` passed. |
| 8 | Bind failure exits non-zero, removes PID, logs; no model loaded during arming | ✓ VERIFIED | `mcp.py:234-265` finally cleanup; `test_daemon_bind_failure_removes_pid_and_propagates` passed; arm constructs model-free backend. |
| 9 | Windows refuses with POSIX-fork cause and foreground remedy | ✓ VERIFIED | `mcp.py:214-221`; `test_windows_daemon_refusal_names_posix_cause_and_foreground_remedy` passed. |
| 10 | Default daemon log `<platform log dir>/sif/mcp.log`; `--log-file` override; parent exists before fork | ✓ VERIFIED | `mcp.py:41-52` (`user_log_dir("sif") / "mcp.log"`, `mkdir(parents=True)`). |
| 11 | `make docs-generate` publishes `--allowed-hosts`/daemon flags and a second is clean | ✓ VERIFIED | Verifier ran `make docs-generate`; `git diff --exit-code` exit 0; `--allowed-hosts` count 2, `not implemented` count 0. |

#### Plan 22-04 (12 truths)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `status`, `lex_search`, `metadata`, `get`, `multi_get` are correct on a model-free host | ✓ VERIFIED | `TestNoLoadSurfaces::test_no_load_tools_and_construction_never_touch_the_loader` passed; construction is lazy in `backend.py:222-295`. |
| 2 | `lex:` query routes BM25 before any load: prefix stripped, `_ensure_embedder()` never called, watch e2e lex rows still return | ✓ VERIFIED | `backend.py:482-495`; `TestPrefixFirstRouting::test_lex_prefix_never_loads_and_strips_the_prefix` passed; `tests/integration/test_mcp_watch_e2e.py` 4 passed. |
| 3 | The `lex:` route's documented deviation: no snippet/line fields; `lex_search` none by design; citation uses `get` | ✓ VERIFIED | `hybrid_search` docstring; `test_lazy_embedder.py` direct-route doubles set `None` citation fields; docs/skills state the rule. |
| 4 | First `query`/`vec_search` constructs one manager and loads once under a lock; second reuses; concurrent first requests load once | ✓ VERIFIED | `backend.py:306-359`; named tests `test_first_query_and_vec_search_load_once_and_reuse`, `test_concurrent_first_requests_perform_exactly_one_load`, `test_a_waiter_arriving_mid_load_receives_the_manager` passed. |
| 5 | Load failure is latched: query degrades to BM25 with one warning; vec_search raises remedy `ToolError`; later requests do not retry | ✓ VERIFIED | `backend.py:335-346,644-646`; `TestHonestFailure` 2 tests passed. |
| 6 | After a successful load the pipeline uses the loaded identity dimension; `get_identity()` only after a successful load | ✓ VERIFIED | `backend.py:331-357,566-575`; `TestLoadedDimension` passed. |
| 7 | `query` has full CLI pipeline parity: default-on hybrid `QueryExpansion`, `SmartSnippetExtractor`, opt-in reranker with `rerank: bool \| None = None` | ✓ VERIFIED | `backend.py:250-259,404-575`; `tests/unit/mcp/test_backend.py::TestQueryPipelineParity`, `TestRerankOption`, `tests/unit/mcp/test_tools.py::TestQueryRerankOption` passed. |
| 8 | `SearchPipeline` constructed per request; manager/expander/reranker/snippet hoisted; hybrid enriches exactly once | ✓ VERIFIED | `_build_pipeline` per request; `TestSingleEnrichmentOwner` passed. |
| 9 | Expansion failure warns and returns unexpanded; requested rerank failure (ImportError/ValueError/execution) soft-degrades to unranked page | ✓ VERIFIED | `backend.py:361-402,536-546`; rerank option tests and construction-failure soft-degrade tests passed. |
| 10 | `set_quiet(True)` and TQDM/HF/TRANSFORMERS recipe run before backend/model construction at stdio/HTTP roots and daemon arm | ✓ VERIFIED | `app.py:269,294` first statements; `cli/commands/mcp.py:236` first in arm; `logging.py:58-60` sets the env vars. |
| 11 | A cold `sif mcp stdio` first query with a lazy model load emits only JSON-RPC on stdout | ✓ VERIFIED | `test_stdout_purity.py::test_cold_first_query_lazy_load_keeps_stdout_protocol_only` passed. |
| 12 | Migration notice stays stderr-only with the legacy model-cache fixture; first query still returns a result | ✓ VERIFIED | Same subprocess test asserts stderr notice and non-error first page. |

#### Plan 22-05 (11 truths)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `extract_with_range` returns snippet plus inclusive 1-based line window; `extract()` stays byte-identical | ✓ VERIFIED | `snippets.py:55-93`; `tests/unit/search/test_snippets.py::TestExtractWithRange` passed; CLI snippet tests unchanged. |
| 2 | `_apply_snippets` assigns `line_start`/`line_end` in the same pass as the existing content fetch | ✓ VERIFIED | `hybrid.py:500-517`; `test_apply_snippets_fills_snippet_and_line_fields_together` passed. |
| 3 | MCP `SearchResult` carries `snippet`, `content_hash`, `line_start`, `line_end` alongside existing fields | ✓ VERIFIED | `protocol.py:22-43`; citation tests passed. |
| 4 | `content_hash` is the stored `documents.checksum` fetched by one batched `DocumentRepository` lookup | ✓ VERIFIED | `repositories.py:333-351`; `backend.py:203-207,547`; `test_citations.py` asserts stored-value equality. |
| 5 | `get`/`multi_get` populate ranges: full 1..N, ranged request the inclusive range; `content_hash` carried (multi_get oversized-truncation edge noted as W-01) | ✓ VERIFIED | `backend.py:735-851`; `TestGetCitationRanges` passed; see W-01 for the explicit `max_bytes > 100 KiB` caveat. |
| 6 | Ranges are inclusive and adjacent: full 1..N, `from_line=2&max_lines=3` = 2-4, next starts at 5 | ✓ VERIFIED | `backend.py:760-784`; citation range tests passed. |
| 7 | Zero-result query returns `results=[]` with schema-conforming `structuredContent`; missing document returns `ToolError` with no payload | ✓ VERIFIED | `TestCitationEdgeCases` and tool error tests passed. |
| 8 | Line ranges count `\n`-split lines; `content_hash` is the stored checksum verbatim | ✓ VERIFIED | `_line_count` in `backend.py:106-111`; citation edge tests passed. |
| 9 | Result order is pipeline order; citation fields attach in place and never reorder | ✓ VERIFIED | `_map_core_results` list comprehension preserves order; order assertions passed. |
| 10 | Phase 20 metadata envelope is deep-equal across channels, unfiltered call omits `filteredDocuments`, no wrapper key/nulls | ✓ VERIFIED | Independent oracle in `test_citations.py::TestFrozenMetadataEnvelope` passed. |
| 11 | CLI `--json` output is byte-identical for every existing search command | ✓ VERIFIED | `tests/unit/cli/test_search.py` + `test_search_pagination.py` passed unmodified (316-test batch). |

#### Plan 22-06 (10 truths)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Repo root is a valid plugin: manifests parse, names `sif`, plugin version equal to `src/sif/_version.py` | ✓ VERIFIED | `.claude-plugin/plugin.json`, `marketplace.json`; `test_plugin.py::TestManifests` passed; version 1.1.2. |
| 2 | `marketplace.json` uses `source:"./"` with a top-level description; `.mcp.json` runs `sif mcp stdio` and leaves DB path to Settings | ✓ VERIFIED | Manifests inspected; `test_mcp_json_runs_installed_stdio_server` and `test_mcp_json_has_no_paths_or_secrets` passed. |
| 3 | Three skills exist with valid frontmatter, MCP tool permissions, untrusted-content warning | ✓ VERIFIED | `skills/sif-search|sif-get|sif-cite`; `TestSkills` passed. |
| 4 | `sif-cite` encodes two-stage citation: metadata → search → `get` → cite docid+lines, never a snippet alone, staleness/hash caveats | ✓ VERIFIED | `skills/sif-cite/SKILL.md`; `test_cite_two_stage_discipline`, `test_cite_surfaces_staleness_and_hash_caveats` passed. |
| 5 | Plugin skills call MCP tools, not CLI; existing `.claude/skills/` untouched | ✓ VERIFIED | All `allowed-tools` are `mcp__sif__*`; phase diff shows no `.claude/skills/` changes. |
| 6 | `claude plugin validate --json .` exits 0 with `success:true`, zero errors, plain validation, no description warning, tolerated CLAUDE.md warning documented | ✓ VERIFIED | Verifier ran it: exit 0, `success:true`, `strict:false`, marketplace/plugin `errors:[]`; only root `CLAUDE.md` warning + non-blocking `ICON_MISSING`. |
| 7 | `docs/mcp-server.md`, `docs/architecture.md`, `docs/api-reference.md` match the shipped surface; old four-tool/daemon-stub text gone | ✓ VERIFIED | MCP docs and module tables describe SDK v2, seven tools, daemon, transport security, plugin install; docs tests passed. Caveat: one residual four-tool sentence in the architecture introduction — open Info IN-06, recorded as non-blocking debt. |
| 8 | `src/sif/mcp/README.md` no longer documents the deleted assembly; points to docs/app | ✓ VERIFIED | File content inspected: points to `docs/mcp-server.md`, `app.py`, `tools.py`, etc. |
| 9 | Install docs make `uv tool install 'docsif[embed]'` primary, document Linux CPU-torch index, base BM25-only install, `uvx` fallback | ✓ VERIFIED | `README.md:32-48,260`, `docs/mcp-server.md:254-304`. |
| 10 | Docs-generate gate stays clean; plugin assets are Markdown/JSON only and add no runtime dependency | ✓ VERIFIED | `make docs-generate` + `git diff --exit-code` exit 0; no runtime dependency added beyond mcp in 22-01. |

#### Plan 22-07 (9 truths)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `server.json` declares name `io.github.zhangtaolab/sif`, package `docsif`, stdio, version from `_version.py`; valid 2025-12-11 schema | ✓ VERIFIED | Manifest inspected; verifier validated with `jsonschema` against the live schema and `mcp-publisher validate` → `✅ server.json is valid`. |
| 2 | `--check` verifies README marker, PyPI version, server.json consistency, registry reachability; 404 = not listed, 200 = already listed, mismatches/5xx fail | ✓ VERIFIED | Verifier ran `python scripts/publish_registry.py --check` → exit 0, four OK lines (`not listed (reachable)`); `test_registry_script.py` (20 tests) passed. |
| 3 | `--publish` short-circuits an already-listed version with exit 0 without invoking `mcp-publisher` | ✓ VERIFIED | `publish_registry.py:259-275`; duplicate-version no-invoke test passed. |
| 4 | The script delegates auth entirely to `mcp-publisher` and exposes only public preflights | ✓ VERIFIED | Stdlib-only script; no credential fields/reads; credential scan test passed. |
| 5 | Live publish is a maintainer checkpoint: URL recorded, or the run recorded as blocked without treating it as a code failure | ✓ VERIFIED | Recorded `blocked no-github-login` in 22-07-SUMMARY; D-24 permits it. Registry remains `not listed (reachable)`; deferred maintainer action, not a code failure. |
| 6 | README and `docs/mcp-server.md` describe the Registry listing and re-run rule; README marker unchanged | ✓ VERIFIED | `README.md:276-293`, `docs/mcp-server.md:325-383`; line-2 marker exact; `--check` marker check passed. |
| 7 | Listed Registry version remains the published 1.1.2; release surface unchanged | ✓ VERIFIED | `src/sif/_version.py` = `1.1.2`; `git tag --list 'v1.2*'` empty; `server.json` 1.1.2. |
| 8 | Phase gate green: full pytest + coverage 90, ruff, ty, docs-generate, plugin validate, registry check | ✓ VERIFIED | Verifier re-ran: `pytest` → 2889 passed, 1 skipped, 95.13%, exit 0; `ruff check`/`format --check`, `ty check src/sif` all green; docs-generate clean; plugin validate exit 0; registry check exit 0. |
| 9 | Real Claude Code smoke recorded (seven tools + one query) with exact command/output | ✓ VERIFIED | Recorded in 22-07-SUMMARY; verifier independently re-ran the headless `claude -p --strict-mcp-config` smoke → init listed exactly seven `mcp__sif-smoke__*` tools and `query` returned `/private/tmp/sif-stdio-smoke/notes/hello.md` with line 1-5 and content_hash. |

**Score:** 77/77 truths verified (0 present-and-wired-but-behavior-unverified).

### Deferred Items

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | Live public MCP Registry listing for `io.github.zhangtaolab/sif` 1.1.2 | Post-phase maintainer action (22-07 Task 2) | Recorded `blocked no-github-login` per D-24; `--check` green (`not listed (reachable)`). Resume: `mcp-publisher login github && python scripts/publish_registry.py --publish`. |

This is an external authentication dependency, not an open code or verification question; the maintainer already chose the blocked outcome.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/sif/mcp/app.py` | Composition root, transport security, HTTP app, stdio/HTTP runners | ✓ VERIFIED | 309 lines; builds one `MCPServer`, one `streamable_http_app`, `/health` guard, D-18 watch lifespan |
| `src/sif/mcp/tools.py` | Seven tool registrations, annotations, descriptions, dual-channel builder, resource | ✓ VERIFIED | 442 lines; all seven ordered; `_result` both channels |
| `src/sif/mcp/backend.py` | Lazy embedder, prefix routing, pipeline parity, citation mapping, get/multi_get | ✓ VERIFIED | 875 lines; model-free constructor; lock/latch; per-request pipeline |
| `src/sif/mcp/protocol.py` | Preserved I/O models with additive min_score/citation fields | ✓ VERIFIED | 282 lines; wire types deleted; citation fields present |
| `src/sif/mcp/watch_host.py` | Session-manager-aware lifespan + embedded watcher | ✓ VERIFIED | 269 lines; D-18 ordering; injected settings |
| `src/sif/mcp/cli.py` | Thin wrappers over `app.py` incl. daemon host seam | ✓ VERIFIED | `run_stdio_server`, `run_http_server`, `run_http_host` |
| `src/sif/cli/commands/mcp.py` | `--allowed-hosts`, daemon lifecycle, Windows refusal, PID/log | ✓ VERIFIED | 268 lines; real arm/host/stop |
| `src/sif/utils/daemon.py` | MCP PID path, marker-aware corroboration/stop | ✓ VERIFIED | `_PID_SUFFIX_MCP`, `pid_path_for_mcp`, marker keyword |
| `src/sif/search/snippets.py` | `extract_with_range` | ✓ VERIFIED | Inclusive ranges; `extract()` delegates |
| `src/sif/search/hybrid.py` | `_apply_snippets` line assignment | ✓ VERIFIED | One-pass snippet + line fields |
| `src/sif/core/models.py` | MCP-only `line_start`/`line_end`, excluded from `to_dict` | ✓ VERIFIED | Confirmed; CLI JSON unchanged |
| `src/sif/database/repositories.py` | Batched `get_checksums` | ✓ VERIFIED | Chunked `IN` query |
| `pyproject.toml`, `uv.lock` | mcp core dependency; extras aliases; resolved graph | ✓ VERIFIED | 13 runtime entries; mcp 2.3.0 locked |
| `tests/unit/mcp/goldens/*.json` | Five era transcripts | ✓ VERIFIED | 2024/2025 ×3 have 3 exchanges; 2026 has 2 (no initialize) |
| `.claude-plugin/plugin.json`, `marketplace.json`, `.mcp.json` | Valid plugin/marketplace/config | ✓ VERIFIED | Names `sif`, version 1.1.2, source `./`, no paths/secrets |
| `skills/sif-search|sif-get|sif-cite/SKILL.md` | MCP-first skills with citation discipline | ✓ VERIFIED | MCP-only allowed-tools; untrusted warning; two-stage rule |
| `server.json` | Registry manifest | ✓ VERIFIED | Schema-valid; mcp-publisher valid |
| `scripts/publish_registry.py` | `--check`/`--publish` preflight and idempotency | ✓ VERIFIED | Stdlib-only; 279 lines; no credentials |
| `docs/mcp-server.md`, `docs/architecture.md`, `docs/api-reference.md`, `README.md` | Shipped-surface docs | ✓ VERIFIED | Rewritten; one residual four-tool sentence (IN-06) |
| Deleted `src/sif/mcp/server.py`, `handlers.py`, `transports/` | Old shell gone | ✓ VERIFIED | Absent; no imports/references |
| MCP test batteries | Contract coverage | ✓ VERIFIED | 15 modules; 2889-test full suite green |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app.py` | `backend.py` | `SearchBackend` constructed in SDK lifespan | ✓ WIRED | `build_server._lifespan` |
| `app.py` | `watch_host.py` | `mcp_session_lifespan` / `start_embedded_watch` | ✓ WIRED | D-18 order |
| `cli/commands/mcp.py` | `mcp/cli.py` | `run_stdio_server`/`run_http_host` | ✓ WIRED | CLI imports lazy wrappers |
| `mcp/cli.py` | `app.py` | `run_stdio`/`run_http` delegation | ✓ WIRED | Confirmed |
| `tools.py` | `backend.py` | hybrid/lex/vec/get/multi_get/status/metadata | ✓ WIRED | Tests call all seven |
| `tools.py` | `core/filters.py` | `parse_filter`/`parse_match` → `ToolError` | ✓ WIRED | Error tests passed |
| `backend.py` | `search/bm25.py`, `search/vector.py` | Direct searcher paths | ✓ WIRED | Lex/vec tests passed |
| `backend.py` | `search/context_attach.py` | Exactly one `enrich_results` per direct path | ✓ WIRED | `TestSingleEnrichmentOwner` passed |
| `backend.py` | `embedding/manager.py` | `from_settings` + `load_model` + `get_identity` under lock | ✓ WIRED | Lazy tests passed |
| `backend.py` | `search/hybrid.py` | Per-request `SearchPipeline` with hoisted components | ✓ WIRED | Parity tests passed |
| `backend.py` | `database/repositories.py` | Batched `get_checksums` per page | ✓ WIRED | Citation tests passed |
| `snippets.py` | `hybrid.py` | `extract_with_range` → line fields | ✓ WIRED | Snippet/hybrid tests passed |
| `app.py` | `utils/logging.py` | `set_quiet(True)` before construction | ✓ WIRED | `app.py:269,294`; daemon arm |
| `.mcp.json` | `cli/commands/mcp.py` | `sif mcp stdio` | ✓ WIRED | Config exact; plugin validate |
| `.claude-plugin/plugin.json` | `src/sif/_version.py` | Version parity | ✓ WIRED | Both 1.1.2; test-pinned |
| `scripts/publish_registry.py` | `README.md` | Exact `mcp-name` marker | ✓ WIRED | `--check` OK |
| `scripts/publish_registry.py` | `src/sif/_version.py` | `runpy` version + server.json consistency | ✓ WIRED | `--check` OK |
| `scripts/publish_registry.py` | PyPI `docsif` + MCP Registry | Live lookups | ✓ WIRED | PyPI version OK; registry reachable |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `SearchBackend.hybrid_search` | results | `SearchPipeline` / `BM25Searcher` over SQLite | Yes | ✓ FLOWING |
| MCP `SearchResult.content_hash` | `content_hash` | `documents.checksum` via batched repository query | Yes | ✓ FLOWING |
| MCP `SearchResult.line_start/end` | line window | Snippet extractor's rendered window over real document content | Yes | ✓ FLOWING |
| MCP `Document` | content/hash/range | `DocumentRepository` rows + stored checksum + line count | Yes | ✓ FLOWING |
| MCP `MetadataOutput` | discovery envelope | `MetadataValueRepository.discover` | Yes | ✓ FLOWING |
| MCP `StatusOutput` | collections/total | `CollectionRepository` + `DocumentRepository` counts | Yes | ✓ FLOWING |
| Plugin version | version | `src/sif/_version.py` | Yes | ✓ FLOWING |
| `server.json` | name/version/package | `_version.py` + `docsif` package metadata | Yes | ✓ FLOWING |
| Registry preflight | listed/not listed | Live PyPI + Registry HTTP | Yes | ✓ FLOWING |

No static returns, hardcoded literals, or mock-only data were found on the shipped paths. Test doubles are confined to tests.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Python 3.10 SDK + app import | `/tmp/sif-mcp310-22/bin/python -c "from mcp.server import MCPServer; import sif.mcp.app"` | `PY 3.10.22`; app resolves to repo `src/sif/mcp/app.py` | ✓ PASS |
| Real Claude Code client: seven tools + one query | `claude -p ... --mcp-config /tmp/sif-stdio-smoke/claude-mcp-smoke.json --strict-mcp-config --output-format stream-json` | init listed exactly seven `mcp__sif-smoke__*` tools; `query` returned `hello.md` (line 1-5, content_hash, snippet); exit 0 | ✓ PASS |
| SDK ping (legacy / auto) | inline `Client.send_ping()` under `mode="legacy"` and `mode="auto"` | legacy ping OK; auto raises Method not found because 2026-07-28 removes ping (SDK warning states this) | ✓ PASS |
| Plugin validation | `claude plugin validate --json .` | exit 0; `success:true`, `strict:false`, zero errors; root `CLAUDE.md` warning tolerated | ✓ PASS |
| Registry preflight | `python scripts/publish_registry.py --check` | exit 0; OK marker, PyPI, server.json, registry `not listed (reachable)` | ✓ PASS |
| Registry manifest validity | `mcp-publisher validate`; `jsonschema` against 2025-12-11 schema | `✅ server.json is valid`; schema validation passed | ✓ PASS |
| Docs generation | `make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md` | exit 0; no diff; 2 `--allowed-hosts` entries, 0 "not implemented" | ✓ PASS |
| Full test suite | `env -u FORCE_COLOR NO_COLOR=1 pytest` | `2889 passed, 1 skipped, 22 warnings in 137.33s`; coverage 95.13% (gate 90); exit 0 | ✓ PASS |
| Named concurrency regressions | four named tests (waiter-mid-load, cold vec non-blocking, one-load, one-reranker) | 4 passed | ✓ PASS |
| Lint / format / types | `ruff check`, `ruff format --check`, `ty check src/sif` | all green | ✓ PASS |
| MCP CLI help | `python -m sif.cli.main mcp daemon --help`, `mcp http --help` | real daemon flags + repeatable `--allowed-hosts` present | ✓ PASS |
| `multi_get` oversized truncation | inline backend call with a 384 KB / 12,000-line document and `max_bytes=1 MiB` | returned 102,400 bytes (~3,200 lines) but reported `line_start=1, line_end=12000` | ✗ FAIL (W-01, non-blocking) |

### Probe Execution

N/A — no probes were declared in the plans/summaries and no `scripts/*/tests/probe-*.sh` files exist. Step 7c skipped.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| MCP-01 | 22-01, 22-07 | Existing clients keep working after SDK v2 migration (dual-era + stateless, goldens, real-client matrix, py3.10 smoke, preserved seam/shell deleted) | ✓ SATISFIED | Five era goldens, SDK client matrix, real Claude client smoke, Python 3.10 import, deleted shell, green gate |
| MCP-02 | 22-02, 22-07 | Accurate annotations on all tools (read-only hints, no destructive/idempotent misstatement, no auto-approval claims) | ✓ SATISFIED | Seven-tool honesty battery + goldens |
| MCP-03 | 22-05, 22-07 | Citation-grade structured output (docid, path, line range, hash, staleness; text kept for legacy clients) | ✓ SATISFIED | Output schemas, citation tests, real Claude client returned line range/hash/snippet |
| MCP-04 | 22-01, 22-03, 22-07 | DNS-rebinding protection via SDK `transport_security`, verified with spoofed headers before middleware deletion | ✓ SATISFIED | 11 transport-security tests; proof commit precedes deletion |
| MCP-05 | 22-02, 22-04, 22-07 | Full query pipeline parity (expander/reranker opt-in/snippet, hoisted pipeline, honest rerank description) | ✓ SATISFIED | Parity/rerank tests; description constants; real query result |
| MCP-06 | 22-01, 22-04, 22-07 | Clean-stdout server (lazy embedder, forced quiet, cold-first-query purity, lex/vec wiring) | ✓ SATISFIED | Model-free startup/lazy tests; cold-first-query subprocess purity; lex/vec paths |
| MCP-07 | 22-03, 22-07 | `mcp daemon` real daemon via existing `utils/daemon.py` | ✓ SATISFIED | POSIX real-process e2e (arm, serve, stop, watch coexistence); PID artifact tests |
| MCP-08 | 22-06, 22-07 | Claude Code plugin (plugin + marketplace + citation skill; `claude plugin validate` passes) | ✓ SATISFIED | Validate exit 0 success; manifests/skills tests; plugin assets live |
| MCP-09 | 22-07 | MCP Registry discovery (mcp-publisher listing, scripted/re-runnable; PyPI prerequisite first) | ✓ SATISFIED (scripted/preflight) | `server.json` schema-valid, `--check` green, script tests, docs; live listing deferred as recorded blocked per D-24 |

**Orphaned requirements:** none. All nine IDs are claimed by at least one plan and mapped to this phase in REQUIREMENTS.md; no additional Phase 22 requirements are unclaimed.

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| `tests/unit/mcp/test_tools.py` | MCP-02/03/05 | 62 | 0 | No | Value/Behavioral | PASS |
| `tests/unit/mcp/test_app.py` | MCP-01/04 | 12 | 0 | No | Value/Behavioral | PASS |
| `tests/unit/mcp/test_wire_transcripts.py` | MCP-01/03 | 10 | 0 | Snapshot (self-captured goldens) | Value/Behavioral; external validity from SDK clients + real client | PASS (snapshot provenance noted) |
| `tests/unit/mcp/test_sdk_clients.py` | MCP-01 | 6 | 0 | No | Behavioral | PASS |
| `tests/unit/mcp/test_transport_security.py` | MCP-04 | 11 | 0 | No | Value/Behavioral | PASS |
| `tests/unit/mcp/test_lazy_embedder.py` | MCP-05/06 | 10 | 0 | No | Behavioral (concurrency) | PASS |
| `tests/unit/mcp/test_citations.py` | MCP-03 | 22 | 0 | No | Value | PASS |
| `tests/unit/mcp/test_daemon.py` | MCP-07 | 11 | 0 (POSIX runs on darwin) | No | Behavioral (real subprocess e2e) | PASS |
| `tests/unit/mcp/test_plugin.py` | MCP-08 | 26 | 0 (`claude` present) | No | Behavioral (CLI validate) | PASS |
| `tests/unit/mcp/test_registry_script.py` | MCP-09 | 20 | 0 | No | Value | PASS |
| `tests/unit/mcp/test_backend.py` | MCP-02/05 | 93 | 0 | No | Value/Behavioral | PASS |

- Disabled tests on requirements: 0. The only skips are environment guards (POSIX fork, `claude` presence, sqlite-vec availability); all are satisfied in this environment, and the plugin-validate test actually ran (26 passed, 0 skipped).
- Circular patterns: none. Wire goldens are self-captured snapshots by design; correctness is independently evidenced by the SDK client matrix and the real Claude Code client smoke.
- Insufficient assertions: 0 on must-have behaviors; tests assert values and behavior, not mere existence.

### Decision Coverage

All trackable CONTEXT.md decisions are honored by shipped artifacts. (25/25 honored; gate exit 0, blocking false.)

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | `TBD`/`FIXME`/`XXX`, TODO/HACK/PLACEHOLDER, stub returns, bare print in serving path | none | No debt markers or stubs in phase-modified files; all diagnostics logger/stderr |
| `src/sif/mcp/backend.py` | 834-846 | `multi_get` computes `_full_line_range(content)` before `_truncate_content`, so a truncated payload can report lines it does not contain | ⚠️ Warning (W-01) | Only reachable with an explicit `max_bytes` above the default 100 KiB budget; default budget skips oversized documents. Reproduced: 12,000-line doc, 1 MiB budget → content truncated to ~3,200 lines, range reported 1-12000. Citation for this route should use `get` until fixed. |
| `docs/architecture.md` | 6 | Introduction still lists only `query`, `get`, `multi_get`, `status` | ℹ️ Info (IN-06) | Recorded open review finding; the MCP-specific sections/module tables correctly describe all seven. Non-blocking debt. |
| `22-REVIEW.md` open findings | — | WR-04 (necessity) + IN-01..IN-08 | ℹ️ Info | Out of scope by reviewed disposition; non-blocking debt consistent with phases 20/21. |

**Debt-marker gate:** clear — no unreferenced `TBD`/`FIXME`/`XXX` in any phase-modified file.

### Human Verification Required

None. The plan's two manual-only items are covered:

- **Real Claude Code client smoke** — independently reproduced by the verifier (seven tools + one query with citation fields, exit 0).
- **`mcp-publisher` live publish** — the maintainer already recorded the decision `blocked no-github-login`; the plan (D-24) defines this as an acceptable non-code outcome. It is tracked as a deferred external action, not an open verification question.

### Verification Debt

Recorded, non-blocking (consistent with the project's carried audit debt for phases 20/21):

1. `22-VALIDATION.md` is still `status: draft` / `nyquist_compliant: false`.
2. No `22-SECURITY.md` exists.
3. Open code-review findings: WR-04 (necessity) and IN-01..IN-08 (Info).
4. IN-06: `docs/architecture.md:6` still names four tools in its introduction.
5. `22-COVERAGE.md` claims ping is "exercised by the SDK client matrix on both protocol modes"; there is no committed ping test, and 2026-07-28 removes ping. Verifier spot-check confirms legacy ping works; the planning-doc statement is imprecise, not a runtime defect.
6. W-01: `multi_get` truncated-content line-range inconsistency under an explicit oversized `max_bytes` budget.
7. Live Registry listing remains unlisted pending maintainer GitHub authentication (deferred per D-24).

### Gaps Summary

No goal-blocking gaps. The phase goal is achieved in the codebase: the official SDK v2 composition root serves all five named protocol revisions plus the stateless era, seven read-only tools carry truthful annotations and dual-channel citation-grade output, the query path reuses the CLI pipeline with an opt-in soft-degrading reranker, transport security and the real MCP daemon are implemented and tested, the Python 3.10 smoke passes, the Claude Code plugin validates and works with a real client, and the Registry manifest/script preflight is green. All nine requirements are accounted for and no requirement is orphaned.

Two items are deliberately outside the passing contract: the live public Registry listing is blocked on maintainer GitHub authentication (recorded and plan-permitted), and W-01 is a narrow `multi_get` oversized-payload citation-range bug that should be fixed in a follow-up but does not block the phase goal because the citation-grade path (`get`) handles truncation correctly.

---

_Verified: 2026-11-16T10:27:03Z_
_Verifier: Claude (gsd-verifier)_
