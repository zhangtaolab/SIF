---
phase: "12"
slug: "sif-watch-foreground-mvp"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-11-07"
validated: "2026-11-12"
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Reconciled by /gsd-validate-phase 12 on 2026-11-12: seeded requirement-level rows mapped to the
> shipped task/test layout, all commands re-run green at HEAD e18648a (105-test phase battery, 20.01s).
> Re-audited by /gsd-validate-phase 12 on 2026-11-12 at HEAD 37e65bc: all 8 rows still COVERED, 0 gaps;
> battery now 108 passed in 19.46s (grew by 3 from Phase 16.1's enqueue_reconcile tests, all green).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-cov (addopts: `--cov=src/sif --cov-report=term-missing --cov-report=html --cov-report=xml`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (testpaths `tests`; `fail_under=90` in `[tool.coverage.report]`) |
| **Quick run command** | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/test_watcher.py -x -q --no-cov` |
| **Full suite command** | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` |
| **Estimated runtime** | ~60–120 seconds full suite (1500+ tests); quick runs seconds |

Env prefix per project memory: agent shells must **unset** `FORCE_COLOR` (setting `"0"` still fails) and set `NO_COLOR=1`.
Scoped runs MUST carry `--no-cov` — the `fail_under=90` gate applies to total coverage and a scoped run cannot reach it (WINDOWS id 8 lesson).

---

## Sampling Rate

- **After every task commit:** `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/ tests/unit/cli/ -x -q --no-cov` (+ the touched files' targeted runs)
- **After every plan wave:** `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` + `ruff check src tests` + `ruff format --check src tests` + `ty check src/sif`
- **Before `/gsd-verify-work`:** full suite green; docs regenerated (`make docs-generate`) with diff reviewed
- **Max feedback latency:** ~120 seconds (full suite)

---

## Per-Task Verification Map

Reconciled 2026-11-12 against the shipped plans (6 tasks, 2 per plan) and test layout. Two seeded
file pointers were corrected: `TestUpdatePaths` (incl. the missing-root guard test) landed in
`tests/unit/indexing/test_watcher.py`, not `test_incremental.py`; `test_incremental.py` kept the
replay/purge legs (`TestUpdatePathsReplay`). All selectors below re-collected and run green this pass.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 12-01 T1 (tracer) + 12-03 T1 | 12-01, 12-03 | 1, 3 | LIVE-01 | T-12-01 | path intake via fsdecode/resolve + shared predicate | unit (`TestUpdatePaths`, 5 tests) + integration (real FS tracer/edit/delete) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/test_watcher.py::TestUpdatePaths tests/integration/test_watch_e2e.py -x --no-cov` | ✅ | ✅ green (2026-11-12) |
| 12-01 T2 | 12-01 | 1 | LIVE-02 | T-12-02 | debounce coalesces storms; bounded queue | unit (burst fold; `update_paths` invocation counts) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/test_watcher.py -k burst -x --no-cov` (7 tests) | ✅ | ✅ green (2026-11-12) |
| 12-01 T2 | 12-01 | 1 | LIVE-03 | T-12-01 | moved src+dest resolved, predicate-checked | unit (atomic-save chain incl. trailing delete; moved/rename algebra) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/test_watcher.py -k "atomic or moved or rename" -x --no-cov` (7 tests) | ✅ | ✅ green (2026-11-12) |
| 12-01 T2 | 12-01 | 1 | LIVE-04 | T-12-01 | ONE shared scanner predicate, no extension-only bypass | unit (parametrized noise + scan-vs-matches parity) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/test_scanner.py tests/unit/indexing/test_watcher.py -k "ignore or temp or parity" -x --no-cov` (7 tests) | ✅ | ✅ green (2026-11-12) |
| 12-02 T2 (+ 12-01 T2 default leg) | 12-02 | 2 | LIVE-05 | T-12-07, T-12-08 | embed compute outside any write transaction; depth inversion impossible by default | unit (embed battery 8 tests + CLI depth matrix) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/test_watcher.py -k embed tests/unit/cli/test_watch_cmd.py::TestDepthMatrix -x --no-cov` | ✅ | ✅ green (2026-11-12) |
| 12-01 T2 (guard) + 12-02 T1 (recovery) | 12-01, 12-02 | 1, 2 | LIVE-11 | T-12-05 | missing root never read as mass deletion; warn-once + recovery | unit (D-11 guard + `TestRecoveryTick`) + e2e recovery | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest "tests/unit/indexing/test_watcher.py::TestUpdatePaths::test_missing_root_returns_zero_emits_missing_and_preserves_docs" tests/unit/indexing/test_watcher.py::TestRecoveryTick -x --no-cov` | ✅ | ✅ green (2026-11-12) |
| 12-03 T1 | 12-03 | 3 | SC1–SC5 (roadmap) | T-12-10 | deadline-bounded outcome polling, never raw event sequences | integration (real Observer + `os.replace` + recovery + exit codes, 6 tests) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/integration/test_watch_e2e.py -x --no-cov` | ✅ | ✅ green (2026-11-12) |
| 12-02 T1 | 12-02 | 2 | D-14 shutdown | T-12-06 | bounded flush; second signal exits 130; checkpoint in try/finally | unit (shutdown machinery, 3 tests) + e2e WAL-truncate exit proof | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/cli/test_watch_cmd.py -k shutdown -x --no-cov` | ✅ | ✅ green (2026-11-12) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Evidence this pass: full phase battery `pytest tests/unit/indexing/test_watcher.py tests/unit/indexing/test_incremental.py tests/unit/indexing/test_scanner.py tests/unit/cli/test_watch_cmd.py tests/integration/test_watch_e2e.py --no-cov -q` → **105 passed in 20.01s** (includes Phase 11 IN-04 concurrency-guard regressions and Phase 13 CLI additions that grew these files). Threat refs closed per 12-SECURITY.md (verified, threats_open 0).

---

## Wave 0 Requirements

- [x] `tests/unit/indexing/test_watcher.py` — **REWRITE** done (12-01): stub-surface tests replaced; now 46 tests incl. `TestUpdatePaths`, `TestRecoveryTick`, `TestEmbedDepth`, `TestConcurrencyGuardRegressions`
- [x] `tests/unit/indexing/test_incremental.py` — **EXTEND** done: `TestUpdatePathsReplay` (replay idempotency + purge-before-delete); per-path stat-decides battery lives in `test_watcher.py::TestUpdatePaths`
- [x] `tests/unit/indexing/test_scanner.py` — **EXTEND** done: `DEFAULT_IGNORE_PATTERNS` entries + shared-predicate parity test
- [x] `tests/integration/test_watch_e2e.py` — **NEW** done (12-01 tracer, 12-03 battery): 6 real-FS tests, deadline-bounded outcome polls
- [x] `tests/unit/cli/test_watch_cmd.py` — **NEW** done (12-02): flag/depth/banner/shutdown battery (35 tests at HEAD incl. Phase 13 additions)
- [x] No framework install needed — pytest/pytest-cov already configured

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real-editor save while watch runs (TextEdit/Obsidian) | LIVE-01/LIVE-03 | Automated `os.replace` chain covers the mechanism; a real editor validates the user-visible story | Run `sif watch` on a collection; save an open note in a real macOS editor; confirm one reindex line appears and search returns the new text without `sif index update` — **exercised: 12-UAT.md item 2 (real-editor save storm with `--embed`), result pass; UX item 1 also pass (2/2, 0 issues)** |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (6/6 tasks carry automated verify commands)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (all five test files shipped; zero MISSING rows remain)
- [x] No watch-mode flags
- [x] Feedback latency < 120s (phase battery 20s; full suite ~60–120s)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-11-12 by /gsd-validate-phase 12 — 8/8 rows COVERED, 0 gaps, 0 manual-only outstanding (UAT exercised)

## Validation Audit 2026-11-12

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
