---
phase: 05
slug: agent-context-experience
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-18
---

# Phase 05 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest tests/unit/cli/test_context.py tests/unit/database/test_schema.py -x` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/unit/cli/test_context.py tests/unit/database/test_schema.py -x`
- **After every plan wave:** Run `pytest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | CTX-01 | — | N/A | unit | `pytest tests/unit/database/test_schema.py -k migration` | ⬜ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | CTX-01 | — | N/A | unit | `pytest tests/unit/database/test_repositories.py -k context` | ⬜ W0 | ⬜ pending |
| 05-02-01 | 02 | 1 | CTX-02 | — | N/A | unit | `pytest tests/unit/cli/test_context.py -k add` | ⬜ W0 | ⬜ pending |
| 05-02-02 | 02 | 1 | CTX-02 | — | N/A | unit | `pytest tests/unit/cli/test_context.py -k list` | ⬜ W0 | ⬜ pending |
| 05-02-03 | 02 | 1 | CTX-02 | — | N/A | unit | `pytest tests/unit/cli/test_context.py -k remove` | ⬜ W0 | ⬜ pending |
| 05-02-04 | 02 | 1 | CTX-02 | — | N/A | unit | `pytest tests/unit/cli/test_context.py -k prune` | ⬜ W0 | ⬜ pending |
| 05-03-01 | 03 | 2 | CTX-03 | — | N/A | unit | `pytest tests/unit/search/test_bm25.py -k context` | ⬜ W0 | ⬜ pending |
| 05-03-02 | 03 | 2 | CTX-03 | — | N/A | unit | `pytest tests/unit/search/test_vector.py -k context` | ⬜ W0 | ⬜ pending |
| 05-03-03 | 03 | 2 | CTX-03 | — | N/A | unit | `pytest tests/unit/search/test_hybrid.py -k context` | ⬜ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/cli/test_context.py` — stubs for CTX-02 CLI tests
- [ ] `tests/unit/database/test_repositories.py` — extend with ContextRepository tests
- [ ] `tests/unit/database/test_schema.py` — extend with migration tests

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Migration rollback on failure | CTX-01 | Requires corrupting SQLite state mid-transaction | Create a DB with path_contexts, inject a fault (e.g., drop write permissions), run schema init, verify old table still exists |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
