---
phase: 09
slug: mcp-server-implementation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-12
---

# Phase 09 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest tests/unit/mcp/ -x -q` |
| **Full suite command** | `ruff check src tests && ruff format --check src tests && pytest` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/unit/mcp/ -x -q`
- **After every plan wave:** Run `ruff check src tests && ruff format --check src tests && pytest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | MCP-01 | T-09-01 | No mock data left in mcp/tools.py | unit | `pytest tests/unit/mcp/test_unified_package.py -x -q` | ❌ W0 | ⬜ pending |
| 09-02-01 | 02 | 1 | MCP-02 | T-09-02 | SearchBackend uses real DB connection | unit | `pytest tests/unit/mcp/test_search_backend.py -x -q` | ❌ W0 | ⬜ pending |
| 09-03-01 | 03 | 2 | MCP-03 | T-09-03 | Tool handlers return real search results | unit | `pytest tests/unit/mcp/test_tool_handlers.py -x -q` | ❌ W0 | ⬜ pending |
| 09-04-01 | 04 | 2 | MCP-04 | T-09-04 | stdio transport outputs valid JSON-RPC | unit | `pytest tests/unit/mcp/test_stdio_transport.py -x -q` | ❌ W0 | ⬜ pending |
| 09-05-01 | 05 | 3 | MCP-04 | T-09-05 | HTTP transport CORS defaults are non-wildcard | unit | `pytest tests/unit/mcp/test_http_transport.py -x -q` | ❌ W0 | ⬜ pending |
| 09-06-01 | 06 | 3 | MCP-01–04 | — | Full quality suite passes | integration | `ruff check src tests && ruff format --check src tests && pytest` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/mcp/` — test package directory
- [ ] `tests/unit/mcp/__init__.py` — package init
- [ ] `tests/unit/mcp/conftest.py` — MCP test fixtures (mock transport, temp DB)
- [ ] `tests/unit/mcp/test_protocol.py` — protocol model validation tests

*Wave 0 creates the MCP test infrastructure before implementation begins.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Claude Desktop stdio integration | MCP-04 | Requires external MCP client | 1. Configure Claude Desktop with `sif mcp stdio`<br>2. Verify tools list appears<br>3. Run a query and verify results |
| HTTP transport browser CORS | MCP-04 | Requires browser origin headers | 1. Start `sif mcp http`<br>2. curl with `-H "Origin: http://evil.com"` → expect 403<br>3. curl with `-H "Origin: http://localhost:3000"` → expect 200 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
