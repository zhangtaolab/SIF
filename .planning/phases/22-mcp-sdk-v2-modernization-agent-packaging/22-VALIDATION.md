---
phase: "22"
slug: "mcp-sdk-v2-modernization-agent-packaging"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-11-16"
validated: "2026-11-18"
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
| 22-01-T1 | 01 | 1 | MCP-01 | T-22-01 | Package legitimacy checkpoint before install; pinned `mcp>=2.3.0,<3`; no extra runtime deps | manual + unit | `uv lock --check` / `uv tree` | ✅ | ✅ green |
| 22-01-T2 | 01 | 1 | MCP-01 | T-22-02 | SDK shell serves status over stdio + HTTP; backend/watch/I-O preserved; old shell left dormant for 22-02 | integration | `pytest tests/unit/mcp/test_app.py -q` | ✅ | ✅ green |
| 22-01-T3 | 01 | 1 | MCP-01 | T-22-03 | 2024-11-05 / 2025-03-26 / 2025-06-18 / 2025-11-25 handshakes + 2026-07-28 stateless; session/headers exact | integration | `pytest tests/unit/mcp/test_wire_transcripts.py tests/unit/mcp/test_sdk_clients.py -q` | ✅ | ✅ green |
| 22-01-T4 | 01 | 1 | MCP-06 | T-22-04 | Cold-first-query stdout is pure JSON-RPC; pre-run stdout hazard closed | integration | `pytest tests/unit/mcp/test_stdout_purity.py -q` | ✅ | ✅ green |
| 22-02-T1 | 02 | 2 | MCP-02 | T-22-05 | Five read-capable tools; annotations truthful; descriptions match backend; no mutation tools; outputSchema present | unit | `pytest tests/unit/mcp/test_tools.py -q` | ✅ | ✅ green |
| 22-02-T2 | 02 | 2 | MCP-05 | T-22-06 | lex/vec direct paths, filters/offset/per_chunk/min_score, one enrich, outputSchema | unit | `pytest tests/unit/mcp/test_tools.py tests/unit/mcp/test_backend.py -q` | ✅ | ✅ green |
| 22-02-T3 | 02 | 2 | MCP-02 | T-22-24 | Seven-tool battery green first; `_METADATA_ENVELOPE` ported into test_tools.py; old shell/wire types/replaced tests deleted; no Python import survives | unit + absence gate | `pytest tests/unit/mcp/test_tools.py tests/unit/mcp/test_backend.py -q`; `test ! -e src/sif/mcp/server.py`; `grep -rn --include='*.py' "from sif.mcp.server\|from sif.mcp.handlers\|from sif.mcp.transports" src tests` (no match) | ✅ | ✅ green |
| 22-03-T1 | 03 | 2 | MCP-04 | T-22-07 | Explicit `TransportSecuritySettings`; Host 421 / Origin 403 / allowed 200; `/health` Host guard; no wildcard; hand-rolled middleware removed with the shell in 22-02 | unit | `pytest tests/unit/mcp/test_transport_security.py -q` | ✅ | ✅ green |
| 22-03-T2 | 03 | 2 | MCP-07 | T-22-08 | Real detached daemon; `<db>.mcp.pid`; mode-aware stop; bind-failure cleanup; Windows refusal | unit + e2e | `pytest tests/unit/mcp/test_daemon.py -q` | ✅ | ✅ green |
| 22-04-T1 | 04 | 3 | MCP-05 | T-22-09 | Lazy manager one load; query BM25 degrade; vec ToolError; lex/status/metadata/get/multi_get no load; identity dimension | unit | `pytest tests/unit/mcp/test_lazy_embedder.py tests/unit/mcp/test_backend.py -q` | ✅ | ✅ green |
| 22-04-T2 | 04 | 3 | MCP-05 | T-22-10 | Expansion/snippets/rerank parity; rerank None/True/False; soft-degrade failures | unit | `pytest tests/unit/mcp/test_backend.py tests/unit/mcp/test_tools.py -q` | ✅ | ✅ green |
| 22-05-T1 | 05 | 4 | MCP-03 | T-22-11 | Snippet-window line ranges; content_hash batch; no CLI JSON change | unit | `pytest tests/unit/mcp/test_citations.py tests/unit/cli tests/unit/search -q` | ✅ | ✅ green |
| 22-05-T2 | 05 | 4 | MCP-03 | T-22-12 | Frozen metadata envelope parity; compact text + structuredContent; no wrapper/nulls | unit | `pytest tests/unit/mcp/test_citations.py -q` | ✅ | ✅ green |
| 22-06-T1 | 06 | 5 | MCP-08 | T-22-13 | Plugin/marketplace/.mcp.json schemas; three skills; citation discipline; validate passes | unit + CLI | `pytest tests/unit/mcp/test_plugin.py -q`; `claude plugin validate --json .` | ✅ | ✅ green |
| 22-06-T2 | 06 | 5 | MCP-05/06 | T-22-14 | Docs match actual tool surface, lazy behavior, daemon, plugin install | docs check | `make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md` | ✅ | ✅ green |
| 22-07-T1 | 07 | 6 | MCP-09 | T-22-15 | Registry preflight marker/PyPI/server.json/duplicate; no credentials | unit | `pytest tests/unit/mcp/test_registry_script.py -q`; `python scripts/publish_registry.py --check` | ✅ | ✅ green |
| 22-07-T2 | 07 | 6 | MCP-01..09 | T-22-16 | Phase gate: full suite, coverage, docs, plugin validate, registry check, Claude Code smoke recorded | aggregate | `pytest`; `ruff check src tests`; `ruff format --check src tests`; `ty check src/sif` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/unit/mcp/test_app.py` — composition root, mount path, `/health`, lifespan/session-manager wiring
- [x] `tests/unit/mcp/test_tools.py` — seven tools, annotations, descriptions, `ToolError` mapping, arg constraints
- [x] `tests/unit/mcp/test_wire_transcripts.py` — era matrix + golden transcripts with normalization
- [x] `tests/unit/mcp/test_sdk_clients.py` — legacy/auto clients over in-process, ASGI, stdio
- [x] `tests/unit/mcp/test_transport_security.py` — spoofed Host/Origin matrix + `/health`
- [x] `tests/unit/mcp/test_lazy_embedder.py` — no-load/one-load/failure/lock
- [x] `tests/unit/mcp/test_stdout_purity.py` — cold first-query subprocess capture
- [x] `tests/unit/mcp/test_citations.py` — snippet window lines, content_hash, get ranges, envelope parity
- [x] `tests/unit/mcp/test_daemon.py` — PID path/payload, arm, stop marker, Windows, bind failure
- [x] `tests/unit/mcp/test_plugin.py` — manifests, skills, optional CLI validate
- [x] `tests/unit/mcp/test_registry_script.py` — preflight branches
- [x] 22-01 keeps the old MCP test modules; 22-02 ports `_METADATA_ENVELOPE` into `test_tools.py`, then rewrites/deletes `test_integration.py`, `test_server.py`, `test_transports_http.py`, `test_transports_stdio.py`
- [x] Adapt `test_backend.py`; keep `test_mcp_watch_host.py` intact

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions | Verified |
|----------|-------------|------------|-------------------|----------|
| Real Claude Code client smoke | MCP-01 | A real host process is the only proof beyond raw transcripts; no headless CI client is available | With a temp config and the installed plugin/server, `claude mcp` lists the seven tools and one `query` returns results; record the exact command/output in SUMMARY | ✅ recorded in 22-07-SUMMARY: temporary local-scope `sif-smoke` entry over `/tmp/sif-stdio-smoke/sif.db` listed the seven tools and returned results; entry removed afterwards |
| `mcp-publisher` login + live Registry publish | MCP-09 | Requires the maintainer's GitHub device-flow identity; credentials are never stored | `mcp-publisher login github`; `python scripts/publish_registry.py --publish`; verify the registry URL; record if blocked | ⛔ blocked by maintainer — user chose `blocked no-github-login` on 2026-11-16; no login or credential storage attempted (D-24 permits this outcome). Preflight `--check` is green: `not listed (reachable) io.github.zhangtaolab/sif 1.1.2` |
| Package legitimacy confirmation for `mcp` | MCP-01 / T-22-01 | The seam reports `unknown-downloads`; a human confirms the official SDK | Confirm PyPI project `mcp` / repo `modelcontextprotocol/python-sdk` / MIT before `uv lock`; record the confirmation | ✅ maintainer-confirmed before install: PyPI `mcp` 2.3.0, official Model Context Protocol Python SDK, not yanked (22-01-SUMMARY) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 180s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-11-18 — 17/17 task rows green (1761 targeted tests in 49.2 s; full suite 3233 passed / 1 skipped @ 95.03% coverage), 0 gaps, 0 escalated. The Registry publish remains maintainer-blocked and is recorded as such, not as a validation gap.

## Validation Audit 2026-11-18

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
