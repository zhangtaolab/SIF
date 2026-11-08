---
phase: "14"
slug: "freshness-floor-pre-command-refresh-staleness-marking"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-11-08"
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-cov (`--cov=src/sif`, `fail_under=90` in `[tool.coverage.report]`) + ruff + ruff-format + ty |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`, `[tool.ruff]`) |
| **Quick run command** | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/cli/test_search.py -x -q` |
| **Full suite command** | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` |
| **Estimated runtime** | ~60–120 seconds full suite; quick runs seconds |

Env prefix per project memory: agent shells must **unset** `FORCE_COLOR` (`env -u`, setting `"0"` still fails) and set `NO_COLOR=1`.

---

## Sampling Rate

- **After every task commit:** targeted quick run for the touched area (see per-task commands) — `env -u FORCE_COLOR NO_COLOR=1 python -m pytest <files> -x -q --no-cov` when cheap
- **After every plan wave:** `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` + `ruff check src tests` + `ruff format --check src tests` + `ty check src/sif`
- **Before `/gsd-verify-work`:** full suite green; docs regenerated (`make docs-generate`) with diff reviewed when new settings/flags land, `tests/test_docs.py` green (generator-owned docs, never hand-edited)
- **Max feedback latency:** ~120 seconds (full suite)

---

## Per-Task Verification Map

Audited 2026-11-08 by /gsd-validate-phase (post-execution): task IDs resolved from the executed plans, every battery re-run green on the final tree (post code-review fixes bd63c78/c30bc22/b39164d, post-validation additions 1062afc/2307ba8). Post-seed coverage additions ride inside the counted batteries: D-05 refresh-failure leg (1062afc), WR-01 parse-failure surfacing (2307ba8), CR-01/WR-01/WR-02 convergence regressions (bd63c78/c30bc22/b39164d).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 14-01 T1/T2 | 14-01 | 1 | LIVE-10 | T-14-01 / T-14-02 | resolved-path compare; walk scoped to registered roots | unit (drift helper: mtime/new/deleted detection; missing-root skip; cap boundary N/N+1 count-first; touch-only + predicate-excluded + parse-fail convergence) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/test_drift.py -x -q --no-cov` | ✅ | ✅ green (13 passed) |
| 14-01 T1 | 14-01 | 1 | LIVE-10 (SC2) | T-14-02 | clean search never creates/touches the lock file | unit (clean index: zero writes, no lock file, no notice — lock spy) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/cli/test_search.py -k refresh -x -q --no-cov` | ✅ | ✅ green (19 passed) |
| 14-01 T2 | 14-01 | 1 | LIVE-10 | T-14-03 | notices on stderr, never stdout (JSON/CSV piping stays clean) | unit (CliRunner: trio integration, `-q` suppression, setting/flag opt-out, stderr separation, D-05 refresh-failure leg) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/cli/test_search.py -x -q --no-cov` | ✅ | ✅ green (125 passed) |
| 14-01 T2 | 14-01 | 1 | LIVE-10 | — | N/A | unit (refresh burst under flock vs held lock — 11-D08 parent-holds-lock pattern) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/cli/test_index_locking.py -x -q --no-cov` | ✅ | ✅ green (5 passed) |
| 14-02 T1 | 14-02 | 1 | QUAL-06 | T-14-04 / T-14-05 | computed boolean + count only; vec0-missing degrade | unit (staleness enrichment: embedded→unmarked; never-embedded/BM25-refreshed→marked; vec0-missing→no markers) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/search/test_staleness.py -x -q --no-cov` | ✅ | ✅ green (12 passed) |
| 14-03 T1 | 14-03 | 2 | QUAL-06 (SC3) | T-14-06 | XML/CSV marker is a fixed boolean literal, never document-derived text | unit (format battery: JSON key incl. `--line-numbers`, CSV column, MD/XML annotation, table render) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/cli/test_search.py -k stale -x -q --no-cov` | ✅ | ✅ green (16 passed) |
| 14-02 T2 | 14-02 | 1 | QUAL-06 | — | N/A | unit (MCP forwarding: backend.hybrid_search metadata carries `vectors_stale`; selector corrected at audit — the seeded `-k stale` selected nothing) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest "tests/unit/mcp/test_backend.py::test_hybrid_search_mocks" -x -q --no-cov` | ✅ | ✅ green (1 passed; assert at test_backend.py:86) |
| 14-02 T2 | 14-02 | 1 | QUAL-06 (D-08 invariant) | T-14-05 | N/A | unit (regression: BM25-only update leaves doc embeddings-free — the invariant the derived signal rests on) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/test_incremental.py -x -q --no-cov` | ✅ | ✅ green (10 passed) |
| 14-02 T2 | 14-02 | 1 | QUAL-06 (D-10) | — | N/A | unit (`sif status` Vector lag row; degraded rendering when vec0 missing) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/cli/test_status.py -x -q --no-cov` | ✅ | ✅ green (11 passed) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/unit/indexing/test_drift.py` — drift helper + cap behavior (LIVE-10; created by 14-01 T1, 13 tests)
- [x] `tests/unit/search/test_staleness.py` — staleness enrichment seam (QUAL-06; created by 14-02 T1, 12 tests)
- [ ] No new framework/config needed — existing infrastructure covers the phase

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

## Validation Audit 2026-11-08

| Metric | Count |
|---|---|
| Gaps found | 1 |
| Resolved | 1 |
| Escalated | 0 |
