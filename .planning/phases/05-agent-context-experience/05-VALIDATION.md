---
phase: 05
slug: agent-context-experience
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-18
validated: 2026-09-07
---

# Phase 05 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/cli/test_context.py tests/unit/database/test_schema.py -x` |
| **Full suite command** | `env -u FORCE_COLOR NO_COLOR=1 pytest` |
| **Estimated runtime** | ~15 seconds |

> Environment note (proven live, 2026-09-06/07): CLI-output assertions break under
> FORCE_COLOR — prefix test commands with `env -u FORCE_COLOR NO_COLOR=1`.

---

## Sampling Rate

- **After every task commit:** Run `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/cli/test_context.py tests/unit/database/test_schema.py -x`
- **After every plan wave:** Run `env -u FORCE_COLOR NO_COLOR=1 pytest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | CTX-01 | — | N/A | unit | `pytest tests/unit/database/test_schema.py -k migration` | ✅ | ✅ green |
| 05-01-02 | 01 | 1 | CTX-01 | — | N/A | unit | `pytest tests/unit/database/test_repositories.py -k context` | ✅ | ✅ green |
| 05-02-01 | 02 | 1 | CTX-02 | — | N/A | unit | `pytest tests/unit/cli/test_context.py -k add` | ✅ | ✅ green |
| 05-02-02 | 02 | 1 | CTX-02 | — | N/A | unit | `pytest tests/unit/cli/test_context.py -k list` | ✅ | ✅ green |
| 05-02-03 | 02 | 1 | CTX-02 | — | N/A | unit | `pytest tests/unit/cli/test_context.py -k remove` | ✅ | ✅ green |
| 05-02-04 | 02 | 1 | CTX-02 | — | N/A | unit | `pytest tests/unit/cli/test_context.py -k prune` | ✅ | ✅ green |
| 05-03-01 | 03 | 2 | CTX-03 | — | N/A | unit | `pytest tests/unit/search/test_bm25.py -k context` | ✅ | ✅ green |
| 05-03-02 | 03 | 2 | CTX-03 | — | N/A | unit | `pytest tests/unit/search/test_vector.py -k context` | ✅ | ✅ green |
| 05-03-03 | 03 | 2 | CTX-03 | — | N/A | unit | `pytest tests/unit/search/test_hybrid.py -k context` | ✅ | ✅ green |
| 05-08-01 | 08 | 1 | CTX-03 | — | N/A | unit (real-SQL) | `pytest tests/unit/search/test_context_attach.py` | ✅ | ✅ green |
| 05-08-02 | 08 | 1 | CTX-03 | — | N/A | unit (real-SQL) | `pytest tests/unit/search/test_bm25.py tests/unit/search/test_vector.py tests/unit/search/test_hybrid.py -k context` | ✅ | ✅ green |
| 05-09-01 | 09 | 2 | CTX-01 | — | N/A | unit | `pytest tests/unit/cli/test_context.py -k canonical` | ✅ | ✅ green |
| 05-09-02 | 09 | 2 | CTX-02 | — | N/A | unit (real-SQL) | `pytest tests/unit/database/test_repositories.py -k prune` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/unit/cli/test_context.py` — stubs for CTX-02 CLI tests (delivered 05-02/05-04; extended 05-09)
- [x] `tests/unit/database/test_repositories.py` — extend with ContextRepository tests (created by gap plan 05-09)
- [x] `tests/unit/database/test_schema.py` — extend with migration tests (delivered 05-01; env-skip fixed 2026-09-07)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Migration rollback on failure | CTX-01 | Requires corrupting SQLite state mid-transaction | Create a DB with path_contexts, inject a fault (e.g. drop write permissions), run schema init, verify old table still exists |

---

## Validation Audit 2026-09-07

| Metric | Count |
|--------|-------|
| Gaps found | 1 |
| Resolved | 1 |
| Escalated | 0 |

**Gap resolved:** `vec_db` fixture in `tests/unit/database/test_schema.py` loaded the
sqlite-vec extension by bare name (`load_extension("vec0")`), env-skipping all 11
extension-dependent tests (5 of them the CTX-01 migration tests) on machines where
bare-name loading fails. Fixture now loads via `sqlite_vec.load(db)` — the same
mechanism as connection setup in production. Full suite after fix: **657 passed,
0 skipped** (was 646 passed / 11 skipped). Commit: `225b9c8`.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated (auto, yolo-mode audit 2026-09-07 — no unresolved gaps)
