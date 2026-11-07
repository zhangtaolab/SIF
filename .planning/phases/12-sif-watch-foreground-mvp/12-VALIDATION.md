---
phase: "12"
slug: "sif-watch-foreground-mvp"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-07"
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-cov (addopts: `--cov=src/sif --cov-report=term-missing --cov-report=html --cov-report=xml`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (testpaths `tests`; `fail_under=90` in `[tool.coverage.report]`) |
| **Quick run command** | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/test_watcher.py -x -q --no-cov` |
| **Full suite command** | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` |
| **Estimated runtime** | ~60–120 seconds full suite (1015+ tests); quick runs seconds |

Env prefix per project memory: agent shells must **unset** `FORCE_COLOR` (setting `"0"` still fails) and set `NO_COLOR=1`.

---

## Sampling Rate

- **After every task commit:** `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/ tests/unit/cli/ -x -q --no-cov` (+ the touched files' targeted runs)
- **After every plan wave:** `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` + `ruff check src tests` + `ruff format --check src tests` + `ty check src/sif`
- **Before `/gsd-verify-work`:** full suite green; docs regenerated (`make docs-generate`) with diff reviewed
- **Max feedback latency:** ~120 seconds (full suite)

---

## Per-Task Verification Map

Seeded from RESEARCH.md's requirement→test map at requirement level; the planner assigns task IDs (plans not yet created at seeding time).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD (planner) | TBD | TBD | LIVE-01 | T-12-xx / — | N/A | unit (synthetic events → `update_paths`) + integration (real FS) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/test_incremental.py -k update_paths -x` ; `... pytest tests/integration/test_watch_e2e.py -x` | ❌ W0 | ⬜ pending |
| TBD (planner) | TBD | TBD | LIVE-02 | T-12-xx / — | N/A | unit (burst fold; count `update_paths` invocations / summed counts) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/test_watcher.py -k burst -x` | ❌ W0 (rewrite) | ⬜ pending |
| TBD (planner) | TBD | TBD | LIVE-03 | T-12-xx / — | N/A | unit (probe-sequence fixture incl. trailing delete; moved `dest_path` filtering) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/test_watcher.py -k "atomic or moved or rename" -x` | ❌ W0 | ⬜ pending |
| TBD (planner) | TBD | TBD | LIVE-04 | T-12-xx / — | N/A | unit (parametrized `.swp/.sb-*/4913/.DS_Store/.#*/.tmp` + scan-vs-predicate parity) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/test_scanner.py tests/unit/indexing/test_watcher.py -k "ignore or temp or parity" -x` | ❌ W0 | ⬜ pending |
| TBD (planner) | TBD | TBD | LIVE-05 | T-12-xx / — | embed compute outside any write transaction | unit (default: no chunks/vectors; `--embed`: chunks+vectors; txn-boundary via mocked embedder) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/test_watcher.py -k embed -x` | ❌ W0 | ⬜ pending |
| TBD (planner) | TBD | TBD | LIVE-11 | T-12-xx / — | N/A | unit (missing-root guard in `update_collection` + per-path) + unit (watcher re-stat transition, warn-once) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/test_incremental.py -k missing -x` | ❌ W0 | ⬜ pending |
| TBD (planner) | TBD | TBD | SC1–SC5 (roadmap) | T-12-xx / — | N/A | integration (real Observer + `os.replace` atomic save in `tmp_path`, serialized, deadline-bounded; outcome-asserting not sequence-asserting) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/integration/test_watch_e2e.py -x` | ❌ W0 (new) | ⬜ pending |
| TBD (planner) | TBD | TBD | D-14 shutdown | T-12-xx / — | N/A | unit (drive stop-flag shutdown path; optional subprocess signal test) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/cli/test_watch_cmd.py -k shutdown -x` | ❌ W0 (new) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/indexing/test_watcher.py` — **REWRITE**: current 396 lines are mock-based against the stub surface (`_extensions`, MagicMock events, Observer patching); rewrite deletes/replaces them per Phase 11 11-03's same-commit RED culture (deleted tests must not import removed symbols)
- [ ] `tests/unit/indexing/test_incremental.py` — **EXTEND**: `update_paths` + missing-root guard + per-path remove cases
- [ ] `tests/unit/indexing/test_scanner.py` — **EXTEND**: new `DEFAULT_IGNORE_PATTERNS` entries + shared-predicate parity test
- [ ] `tests/integration/test_watch_e2e.py` — **NEW**: 1–2 real-FS tests (real Observer, `os.replace` chain, deadline-bounded polling for the indexed outcome, serialized)
- [ ] `tests/unit/cli/test_watch_cmd.py` — **NEW**: banner/flag surface + shutdown machinery
- [ ] No framework install needed — pytest/pytest-cov already configured

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real-editor save while watch runs (TextEdit/Obsidian) | LIVE-01/LIVE-03 | Automated `os.replace` chain covers the mechanism; a real editor validates the user-visible story | Run `sif watch` on a collection; save an open note in a real macOS editor; confirm one reindex line appears and search returns the new text without `sif index update` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
