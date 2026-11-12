---
phase: "15"
slug: "search-quality-configuration-hybrid-weights-query-suggestions"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-11-08"
updated: "2026-11-12"
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
- **Max feedback latency:** ~120 seconds (full suite; measured 67.5 s on 2026-11-12)

---

## Per-Task Verification Map

Audited 2026-11-08 by /gsd-validate-phase (post-execution): all seeded batteries green; 1 gap found and fixed — the seeded DYM selector `-k did_you_mean` selected 0 tests (real names use `dym`), corrected to `-k "dym or suggest"`.

Re-audited 2026-11-12 by /gsd-validate-phase on `a8438c3` (post quick-batch 261111-wh6: WR-07/WR-08/IN-05/IN-07 touched search/MCP surfaces): all 10 seeded batteries re-run green with identical counts (byte_identical 1 · weighted 9 · -k rrf 1 · mcp -k weight 10 · -k "dym or suggest" 10 · SC2 -k hit 2 · repo 5 · -k history 7 · CLI suggest 12 · -k budget 1). **Test-coverage gaps: 0.** Map-completeness gaps: 7 rows added for tasks whose automated tests existed but were unmapped — pipeline golden (test_hybrid.py 36), Settings validation (test_settings.py 34), vocab shadow (test_schema.py -k vocab 2), engine full battery (test_suggest.py 27), CLI history writes (test_search.py -k history 7), MCP zero-result suggestions (test_backend.py -k suggest 5), docs gate (test_docs.py 13) — all green. Phase gate re-verified: full suite **1545 passed / 1 skipped @ 95.06%** (fail_under=90), ruff check + format green, ty green, `make docs-generate` idempotent. Resolved 7, Escalated 0.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 15-01 T1 | 15-01 | 1 | QUAL-01 (SC1) | — | N/A | unit (default weights byte-identical — golden snapshot captured BEFORE implementation) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/search/test_rrf.py -k byte_identical -x -q --no-cov` | ✅ extend | ✅ green (1) |
| 15-01 T1/T2 | 15-01 | 1 | QUAL-01 | — | N/A | unit (weights reorder fusion; k honored; multiply-form not normalized) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/search/test_rrf.py -k weighted -x -q --no-cov` | ✅ extend | ✅ green (9) |
| 15-01 T1 | 15-01 | 1 | QUAL-01 (SC1 pipeline) | — | N/A | unit (pipeline golden to_dict snapshot on real-DB fixture + weight/k reorder pins) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/search/test_hybrid.py -x -q --no-cov` | ✅ extend | ✅ green (36) |
| 15-01 T2 | 15-01 | 1 | QUAL-01 | — | N/A | integration (CliRunner: CLI flags > SIF_ > default precedence) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/cli/test_search.py -k rrf -x -q --no-cov` | ✅ extend | ✅ green (1) |
| 15-01 T2 | 15-01 | 1 | QUAL-01 (D-04) | — | N/A | unit (MCP QueryInput weights → options; settings default) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/mcp -k weight -x -q --no-cov` | ✅ extend | ✅ green (10) |
| 15-01 T1 / 15-02 T3 | 15-01, 15-02 | 1–2 | QUAL-01/03 (D-03) | — | N/A | unit (Settings ge/gt validation naming the field, no upper bound, env reach, defaults) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/config/test_settings.py -x -q --no-cov` | ✅ extend | ✅ green (34) |
| 15-02 T1 | 15-02 | 2 | QUAL-02/04 (D-06) | — | N/A | unit (documents_fts_v vocab shadow: create_all enumerates porter stems; drop_all isolates) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/database/test_schema.py -k vocab -x -q --no-cov` | ✅ extend | ✅ green (2) |
| 15-02 T1/T2 | 15-02 | 2 | QUAL-02/04 | T-15-03 | vocab terms re-enter search only via _sanitize_term/_build_fts_query | unit (engine full battery: prefix, DYM shape, degradation, determinism) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/search/test_suggest.py -x -q --no-cov` | ✅ new | ✅ green (27) |
| 15-02 T2 | 15-02 | 2 | QUAL-02 (SC2 pin) | — | N/A | integration (every emitted suggestion run as a real query → ≥1 hit) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/search/test_suggest.py -k hit -x -q --no-cov` | ✅ new | ✅ green (2) |
| 15-02 T2 | 15-02 | 2 | QUAL-04 (SC4) | — | N/A | perf-ish unit (100 ms core budget on fixture vocab; perf_counter, generous headroom, no wall-clock races) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/search/test_suggest.py -k budget -x -q --no-cov` | ✅ new | ✅ green (1) |
| 15-02 T3 | 15-02 | 2 | QUAL-03 | T-15-04/05 | local-only; fail-soft (history never breaks search); trim cap | unit (query_log write/trim-in-write/opt-out/clear) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/database/test_query_log_repo.py -x -q --no-cov` | ✅ new | ✅ green (5) |
| 15-02 T3 | 15-02 | 2 | QUAL-03 | — | N/A | unit (history ranking frequency × recency; D-10 read gate) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/search/test_suggest.py -k history -x -q --no-cov` | ✅ new | ✅ green (7) |
| 15-03 T1 | 15-03 | 3 | QUAL-04 | — | N/A | integration (suggest three sections + --json shape + --clear-history + no-index guard) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/cli/test_suggest.py -x -q --no-cov` | ✅ new | ✅ green (12) |
| 15-03 T2 | 15-03 | 3 | QUAL-02 | — | suggestions never rewrite; stdout purity per output mode | integration (zero-result DYM on all three commands) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/cli/test_search.py -k "dym or suggest" -x -q --no-cov` | ✅ extend | ✅ green (10) |
| 15-03 T2 | 15-03 | 3 | QUAL-03 (D-08/D-10 write) | T-15-04 | one row per executed search; opt-out writes nothing; fail-soft | integration (CLI history writes: gate, -q still logs, write failure never fails search) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/cli/test_search.py -k history -x -q --no-cov` | ✅ extend | ✅ green (7) |
| 15-03 T3 | 15-03 | 3 | QUAL-02 (D-05/D-08 MCP) | T-15-07 | MCP never writes query_log; explicit boundary remap | unit (MCP zero-result suggestions; empty when results exist; engine failure degrades) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/mcp/test_backend.py -k suggest -x -q --no-cov` | ✅ extend | ✅ green (5) |
| 15-01 T3 / 15-02 T3 / 15-03 T1 | 15-01–03 | 1–3 | QUAL-01/03/04 (docs) | — | N/A | docs gate (no phantom env vars; generated refs current; `--no-cov` for docs-only subset — full suite carries the coverage gate) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/test_docs.py -x -q --no-cov` | ✅ extend | ✅ green (13) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠ flaky — all rows verified green on `a8438c3`, 2026-11-12.*

---

## Wave 0 Requirements

- [x] `tests/unit/search/test_suggest.py` — engine: DYM, prefix, history, budget, ≥1-hit pin (QUAL-02/04) — delivered, 27 tests
- [x] `tests/unit/database/test_query_log_repo.py` — repository CRUD + trim-in-write + clear (QUAL-03) — delivered, 5 tests
- [x] `tests/unit/cli/test_suggest.py` — CliRunner table/`--json`/`--clear-history`/no-index guard (QUAL-04) — delivered, 12 tests
- [x] Golden snapshot capture for SC1 — captured pre-implementation, red-then-green in 15-01 (`3b29164` RED → `04e4e48` GREEN)
- [x] `.claude/skills/sif-search/SKILL.md` — zero-result JSON contract updated for both shapes (`28faa08`; verified present 2026-11-12)
- [x] No new framework/config needed — existing infrastructure covers the phase

---

## Manual-Only Verifications

One deliberate manual check (D-14): the **product-level 100 ms sanity** for `sif suggest --json` end-to-end minus a `--help` startup baseline — measured 717.7 ms vs 706.3 ms baseline = **11.4 ms** of actual work on a 20,000-term synthetic index (recorded in 15-03 SUMMARY, coverage D6, human_judgment: true). No wall-clock CLI test by design; the engine's core cost stays pinned deterministically by the automated budget test (15-02, `-k budget`). All other phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 120s (full suite 67.5 s measured 2026-11-12)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-11-12 — re-audit on `a8438c3`, all 17 map rows green, phase quality gate green (1545 passed / 1 skipped @ 95.06%, ruff/format/ty clean, docs regen idempotent).

## Validation Audit 2026-11-08

| Metric | Count |
|---|---|
| Gaps found | 1 |
| Resolved | 1 |
| Escalated | 0 |

## Validation Audit 2026-11-12

| Metric | Count |
|---|---|
| Gaps found | 7 |
| Resolved | 7 |
| Escalated | 0 |
