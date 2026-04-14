---
phase: 01
slug: foundation-fix
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-14
---

# Phase 01 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest tests/ -x --tb=short` |
| **Full suite command** | `pytest tests/ --tb=short` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x --tb=short`
- **After every plan wave:** Run `pytest tests/ --tb=short`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | FND-01 | — | Dependencies declared without leaking secrets | unit | `python -c "import docsift.database"` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 1 | FND-05 | — | FTS5 rows match document table | integration | `pytest tests/ -k fts --tb=short` | ❌ W0 | ⬜ pending |
| 01-03-01 | 03 | 1 | FND-02 | — | Checksum comparison correctly skips unchanged | unit | `pytest tests/test_indexing.py -k checksum --tb=short` | ❌ W0 | ⬜ pending |
| 01-04-01 | 04 | 1 | FND-03 | — | Real embeddings returned for supported models | unit | `pytest tests/test_embedding.py --tb=short` | ❌ W0 | ⬜ pending |
| 01-05-01 | 05 | 1 | FND-06 | — | Vector search raises on missing embedder | unit | `pytest tests/test_search.py -k vector --tb=short` | ❌ W0 | ⬜ pending |
| 01-06-01 | 06 | 1 | FND-08 | — | SQLite connections safe across threads | unit | `pytest tests/test_database.py -k thread --tb=short` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/` — existing test stubs cover FND requirements
- [ ] `pyproject.toml` — dependencies and pytest config already present
- [ ] `ruff` / `mypy` — type and lint checks configured

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Fresh install in clean venv | FND-01 | Requires isolated environment | `pip install -e ".[dev]"` in new venv, verify no import errors |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
