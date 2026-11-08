---
phase: "14"
slug: "freshness-floor-pre-command-refresh-staleness-marking"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
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

Seeded from RESEARCH.md's requirement→test map at requirement level; task IDs to be filled by the validate-phase audit after execution.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | 0 | LIVE-10 | — | N/A | unit (drift helper: mtime/new/deleted detection; missing-root skip; resolve-consistent compares) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/test_drift.py -x -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | LIVE-10 | — | N/A | unit (cap boundary: N refreshed / N+1 skipped+warned; count-first — no parse when over cap) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/test_drift.py -x -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LIVE-10 (SC2) | — | clean search never creates/touches the lock file | unit (clean index: zero writes, no lock file, no notice) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/cli/test_search.py -k refresh -x -q` | ✅ extend | ⬜ pending |
| TBD | TBD | TBD | LIVE-10 | — | notices on stderr, never stdout (JSON/CSV piping stays clean) | unit (CliRunner: trio integration, `-q` suppression, setting/flag opt-out, stderr separation) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/cli/test_search.py -x -q` | ✅ extend | ⬜ pending |
| TBD | TBD | TBD | LIVE-10 | — | N/A | subprocess/unit (refresh burst under flock vs held lock — 11-D08 parent-holds-lock pattern) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/cli/test_index_locking.py -x -q` | ✅ extend | ⬜ pending |
| TBD | TBD | 0 | QUAL-06 | — | N/A | unit (staleness enrichment: embedded→unmarked; never-embedded/BM25-refreshed→marked; vec0-missing→no markers) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/search/test_staleness.py -x -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | QUAL-06 (SC3) | — | N/A | unit (format battery: JSON key incl. `--line-numbers`, CSV column, MD/XML annotation, table render) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/cli/test_search.py -k stale -x -q` | ✅ extend | ⬜ pending |
| TBD | TBD | TBD | QUAL-06 | — | N/A | unit (MCP forwarding: backend.hybrid_search mapping carries the flag) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/mcp -k stale -x -q` | ✅ extend | ⬜ pending |
| TBD | TBD | TBD | QUAL-06 (D-08 invariant) | — | N/A | unit (regression: BM25-only update leaves doc embeddings-free — the invariant the derived signal rests on) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/test_incremental.py -x -q` | ✅ extend | ⬜ pending |
| TBD | TBD | TBD | QUAL-06 (D-10) | — | N/A | unit (`sif status` Vector lag row; degraded rendering when vec0 missing) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/cli/test_status.py -x -q` | ✅ extend | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/indexing/test_drift.py` — drift helper + cap behavior stubs (LIVE-10)
- [ ] `tests/unit/search/test_staleness.py` — staleness enrichment seam stubs (QUAL-06)
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
