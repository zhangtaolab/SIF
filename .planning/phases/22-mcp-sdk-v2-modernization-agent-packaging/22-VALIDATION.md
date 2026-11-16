---
phase: "22"
slug: "mcp-sdk-v2-modernization-agent-packaging"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-16"
---

# Phase 22 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + pytest-asyncio (explicit `@pytest.mark.asyncio` markers), coverage `fail_under = 90` |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/mcp -x -q` |
| **Full suite command** | `env -u FORCE_COLOR NO_COLOR=1 pytest` + `ruff check src tests` + `ruff format --check src tests` + `ty check src/sif` |
| **Estimated runtime** | ~90–180 seconds (full suite; MCP subset <30s) |

---

## Sampling Rate

- **After every task commit:** Run the task's `<automated>` command, plus `ruff check src tests` for touched files
- **After every plan wave:** Run `pytest` (coverage gate), `ruff format --check src tests`, `ty check src/sif`
- **Before `/gsd-verify-work`:** Full suite must be green; `make docs-generate` clean; `claude plugin validate --json .` success; `python scripts/publish_registry.py --check` green
- **Max feedback latency:** 180 seconds

---

## Per-Task Verification Map

> Rows are plan/requirement-level until the planner assigns task IDs. The executor must keep each row's command/failure direction attached to its task.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 22-01-T1 | 01 | 1 | MCP-01 | T-22-01 | Package legitimacy checkpoint before install; pinned `mcp>=2.3.0,<3`; no extra runtime deps | manual + unit | `uv lock --check` / `uv tree` | ❌ W0 | ⬜ pending |
| 22-01-T2 | 01 | 1 | MCP-01 | T-22-02 | SDK shell serves status over stdio + HTTP; backend/watch/I-O preserved; old shell left dormant for 22-02 | integration | `pytest tests/unit/mcp/test_app.py -q` | ❌ W0 | ⬜ pending |
| 22-01-T3 | 01 | 1 | MCP-01 | T-22-03 | 2024-11-05 / 2025-03-26 / 2025-06-18 / 2025-11-25 handshakes + 2026-07-28 stateless; session/headers exact | integration | `pytest tests/unit/mcp/test_wire_transcripts.py tests/unit/mcp/test_sdk_clients.py -q` | ❌ W0 | ⬜ pending |
| 22-01-T4 | 01 | 1 | MCP-06 | T-22-04 | Cold-first-query stdout is pure JSON-RPC; pre-run stdout hazard closed | integration | `pytest tests/unit/mcp/test_stdout_purity.py -q` | ❌ W0 | ⬜ pending |
| 22-02-T1 | 02 | 2 | MCP-02 | T-22-05 | Five read-capable tools; annotations truthful; descriptions match backend; no mutation tools; outputSchema present | unit | `pytest tests/unit/mcp/test_tools.py -q` | ❌ W0 | ⬜ pending |
| 22-02-T2 | 02 | 2 | MCP-05 | T-22-06 | lex/vec direct paths, filters/offset/per_chunk/min_score, one enrich, outputSchema | unit | `pytest tests/unit/mcp/test_tools.py tests/unit/mcp/test_backend.py -q` | ✅ partial | ⬜ pending |
| 22-02-T3 | 02 | 2 | MCP-02 | T-22-24 | Seven-tool battery green first; `_METADATA_ENVELOPE` ported into test_tools.py; old shell/wire types/replaced tests deleted; no Python import survives | unit + absence gate | `pytest tests/unit/mcp/test_tools.py tests/unit/mcp/test_backend.py -q`; `test ! -e src/sif/mcp/server.py`; `grep -rn --include='*.py' "from sif.mcp.server\|from sif.mcp.handlers\|from sif.mcp.transports" src tests` (no match) | ❌ W0 | ⬜ pending |
| 22-03-T1 | 03 | 2 | MCP-04 | T-22-07 | Explicit `TransportSecuritySettings`; Host 421 / Origin 403 / allowed 200; `/health` Host guard; no wildcard; hand-rolled middleware removed with the shell in 22-02 | unit | `pytest tests/unit/mcp/test_transport_security.py -q` | ❌ W0 | ⬜ pending |
| 22-03-T2 | 03 | 2 | MCP-07 | T-22-08 | Real detached daemon; `<db>.mcp.pid`; mode-aware stop; bind-failure cleanup; Windows refusal | unit + e2e | `pytest tests/unit/mcp/test_daemon.py -q` | ❌ W0 | ⬜ pending |
| 22-04-T1 | 04 | 3 | MCP-05 | T-22-09 | Lazy manager one load; query BM25 degrade; vec ToolError; lex/status/metadata/get/multi_get no load; identity dimension | unit | `pytest tests/unit/mcp/test_lazy_embedder.py tests/unit/mcp/test_backend.py -q` | ❌ W0 | ⬜ pending |
| 22-04-T2 | 04 | 3 | MCP-05 | T-22-10 | Expansion/snippets/rerank parity; rerank None/True/False; soft-degrade failures | unit | `pytest tests/unit/mcp/test_backend.py tests/unit/mcp/test_tools.py -q` | ❌ W0 | ⬜ pending |
| 22-05-T1 | 05 | 4 | MCP-03 | T-22-11 | Snippet-window line ranges; content_hash batch; no CLI JSON change | unit | `pytest tests/unit/mcp/test_citations.py tests/unit/cli tests/unit/search -q` | ❌ W0 | ⬜ pending |
| 22-05-T2 | 05 | 4 | MCP-03 | T-22-12 | Frozen metadata envelope parity; compact text + structuredContent; no wrapper/nulls | unit | `pytest tests/unit/mcp/test_citations.py -q` | ❌ W0 | ⬜ pending |
| 22-06-T1 | 06 | 5 | MCP-08 | T-22-13 | Plugin/marketplace/.mcp.json schemas; three skills; citation discipline; validate passes | unit + CLI | `pytest tests/unit/mcp/test_plugin.py -q`; `claude plugin validate --json .` | ❌ W0 | ⬜ pending |
| 22-06-T2 | 06 | 5 | MCP-05/06 | T-22-14 | Docs match actual tool surface, lazy behavior, daemon, plugin install | docs check | `make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md` | ✅ | ⬜ pending |
| 22-07-T1 | 07 | 6 | MCP-09 | T-22-15 | Registry preflight marker/PyPI/server.json/duplicate; no credentials | unit | `pytest tests/unit/mcp/test_registry_script.py -q`; `python scripts/publish_registry.py --check` | ❌ W0 | ⬜ pending |
| 22-07-T2 | 07 | 6 | MCP-01..09 | T-22-16 | Phase gate: full suite, coverage, docs, plugin validate, registry check, Claude Code smoke recorded | aggregate | `pytest`; `ruff check src tests`; `ruff format --check src tests`; `ty check src/sif` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/mcp/test_app.py` — composition root, mount path, `/health`, lifespan/session-manager wiring
- [ ] `tests/unit/mcp/test_tools.py` — seven tools, annotations, descriptions, `ToolError` mapping, arg constraints
- [ ] `tests/unit/mcp/test_wire_transcripts.py` — era matrix + golden transcripts with normalization
- [ ] `tests/unit/mcp/test_sdk_clients.py` — legacy/auto clients over in-process, ASGI, stdio
- [ ] `tests/unit/mcp/test_transport_security.py` — spoofed Host/Origin matrix + `/health`
- [ ] `tests/unit/mcp/test_lazy_embedder.py` — no-load/one-load/failure/lock
- [ ] `tests/unit/mcp/test_stdout_purity.py` — cold first-query subprocess capture
- [ ] `tests/unit/mcp/test_citations.py` — snippet window lines, content_hash, get ranges, envelope parity
- [ ] `tests/unit/mcp/test_daemon.py` — PID path/payload, arm, stop marker, Windows, bind failure
- [ ] `tests/unit/mcp/test_plugin.py` — manifests, skills, optional CLI validate
- [ ] `tests/unit/mcp/test_registry_script.py` — preflight branches
- [ ] 22-01 keeps the old MCP test modules; 22-02 ports `_METADATA_ENVELOPE` into `test_tools.py`, then rewrites/deletes `test_integration.py`, `test_server.py`, `test_transports_http.py`, `test_transports_stdio.py`
- [ ] Adapt `test_backend.py`; keep `test_mcp_watch_host.py` intact

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real Claude Code client smoke | MCP-01 | A real host process is the only proof beyond raw transcripts; no headless CI client is available | With a temp config and the installed plugin/server, `claude mcp` lists the seven tools and one `query` returns results; record the exact command/output in SUMMARY |
| `mcp-publisher` login + live Registry publish | MCP-09 | Requires the maintainer's GitHub device-flow identity; credentials are never stored | `mcp-publisher login github`; `python scripts/publish_registry.py --publish`; verify the registry URL; record if blocked |
| Package legitimacy confirmation for `mcp` | MCP-01 / T-22-01 | The seam reports `unknown-downloads`; a human confirms the official SDK | Confirm PyPI project `mcp` / repo `modelcontextprotocol/python-sdk` / MIT before `uv lock`; record the confirmation |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 180s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
