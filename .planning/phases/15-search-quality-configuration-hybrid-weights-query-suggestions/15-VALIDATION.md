---
phase: "15"
slug: "search-quality-configuration-hybrid-weights-query-suggestions"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-08"
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-cov (`--cov=src/sif`, `fail_under=90`) + ruff + ruff-format + ty |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`, `[tool.ruff]`) |
| **Quick run command** | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/search/test_rrf.py -x -q` |
| **Full suite command** | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` |
| **Estimated runtime** | ~60–120 seconds full suite; quick runs seconds |

Env prefix per project memory: agent shells must **unset** `FORCE_COLOR` (`env -u`) and set `NO_COLOR=1`.

---

## Sampling Rate

- **After every task commit:** targeted quick run for the touched area
- **After every plan wave:** full suite + `ruff check src tests` + `ruff format --check src tests` + `ty check src/sif`
- **Before `/gsd-verify-work`:** full suite green; docs regenerated (`make docs-generate`) when settings/flags land, `tests/test_docs.py` green
- **Max feedback latency:** ~120 seconds (full suite)

---

## Per-Task Verification Map

Seeded from RESEARCH.md's requirement→test map at requirement level; task IDs to be filled by the validate-phase audit after execution.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | QUAL-01 (SC1) | — | N/A | unit (default weights byte-identical — golden snapshot captured BEFORE implementation) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/search/test_rrf.py -k byte_identical -x -q --no-cov` | ✅ extend | ⬜ pending |
| TBD | TBD | TBD | QUAL-01 | — | N/A | unit (weights reorder fusion; k honored; multiply-form not normalized) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/search/test_rrf.py -k weighted -x -q --no-cov` | ✅ extend | ⬜ pending |
| TBD | TBD | TBD | QUAL-01 | — | N/A | integration (CliRunner: CLI flags > SIF_ > default precedence) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/cli/test_search.py -k rrf -x -q --no-cov` | ✅ extend | ⬜ pending |
| TBD | TBD | TBD | QUAL-01 (D-04) | — | N/A | unit (MCP QueryInput weights → options; settings default) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/mcp -k weight -x -q --no-cov` | ✅ extend | ⬜ pending |
| TBD | TBD | TBD | QUAL-02 | — | suggestions never rewrite; stdout purity per output mode | integration (zero-result DYM on all three commands) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/cli/test_search.py -k did_you_mean -x -q --no-cov` | ✅ extend | ⬜ pending |
| TBD | TBD | 0 | QUAL-02 (SC2 pin) | — | N/A | integration (every emitted suggestion run as a real query → ≥1 hit) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/search/test_suggest.py -k hit -x -q --no-cov` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | QUAL-03 | — | local-only; fail-soft (history never breaks search) | unit (query_log write/trim-in-write/opt-out/clear) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/database/test_query_log_repo.py -x -q --no-cov` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | QUAL-03 | — | N/A | unit (history ranking frequency × recency) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/search/test_suggest.py -k history -x -q --no-cov` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | QUAL-04 | — | N/A | integration (suggest three sections + --json shape + --clear-history + no-index guard) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/cli/test_suggest.py -x -q --no-cov` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | QUAL-04 (SC4) | — | N/A | perf-ish unit (100 ms core budget on fixture vocab; perf_counter, generous headroom, no wall-clock races) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/search/test_suggest.py -k budget -x -q --no-cov` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/search/test_suggest.py` — engine: DYM, prefix, history, budget, ≥1-hit pin (QUAL-02/04)
- [ ] `tests/unit/database/test_query_log_repo.py` — repository CRUD + trim-in-write + clear (QUAL-03)
- [ ] `tests/unit/cli/test_suggest.py` — CliRunner table/`--json`/`--clear-history`/no-index guard (QUAL-04)
- [ ] Golden snapshot capture for SC1 — capture today's fused output BEFORE implementation lands (red-then-green ordering in the same plan)
- [ ] `.claude/skills/sif-search/SKILL.md` — zero-result JSON contract note update once the shape is chosen
- [ ] No new framework/config needed — existing infrastructure covers the phase

---

## Manual-Only Verifications

All phase behaviors have automated verification (100 ms budget asserted on the core function; CLI cold start excluded per CONTEXT D-14).

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
