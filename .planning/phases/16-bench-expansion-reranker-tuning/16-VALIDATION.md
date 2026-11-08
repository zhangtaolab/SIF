---
phase: "16"
slug: "bench-expansion-reranker-tuning"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-08"
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-cov (`[tool.pytest.ini_options]`, `pyproject.toml`) |
| **Config file** | `pyproject.toml` (no separate pytest.ini) |
| **Quick run command** | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search/test_benchmark_metrics.py tests/unit/search/test_sweep.py -x --no-cov` |
| **Full suite command** | `env -u FORCE_COLOR NO_COLOR=1 pytest` |
| **Estimated runtime** | ~90 seconds (full suite: 1015 tests @ 96.2%, `fail_under=90`) |

---

## Sampling Rate

- **After every task commit:** Run `env -u FORCE_COLOR NO_COLOR=1 pytest <touched-module> -x --no-cov`
- **After every plan wave:** Run `ruff check src tests && ruff format --check src tests && env -u FORCE_COLOR NO_COLOR=1 pytest`
- **Before `/gsd-verify-work`:** Full suite must be green, plus `make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md`
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 1 | EVAL-01 | — | N/A | unit | `pytest tests/unit/search/test_benchmark_metrics.py -x --no-cov` | ❌ W0 | ⬜ pending |
| 16-01-02 | 01 | 1 | EVAL-01 | — | N/A | unit | `pytest tests/unit/search/test_benchmark_metrics.py -k percentile -x --no-cov` | ❌ W0 | ⬜ pending |
| 16-01-03 | 01 | 1 | EVAL-01 | — | N/A | integration | `pytest tests/unit/cli/test_bench.py -k metrics -x --no-cov` | ✅ extend | ⬜ pending |
| 16-02-01 | 02 | 1 | EVAL-02 | — | N/A | unit | `pytest tests/unit/search/test_benchmark_metrics.py -k fixture_contract -x --no-cov` | ❌ W0 | ⬜ pending |
| 16-02-02 | 02 | 1 | EVAL-02 | — | N/A | integration | `pytest tests/unit/search/test_bench_fixture.py -x --no-cov` | ❌ W0 | ⬜ pending |
| 16-03-01 | 03 | 2 | EVAL-03, SC3 | — | N/A | unit | `pytest tests/unit/search/test_sweep.py -k tie -x --no-cov` | ❌ W0 | ⬜ pending |
| 16-03-02 | 03 | 2 | EVAL-03 | — | N/A | unit (spy) | `pytest tests/unit/search/test_sweep.py -k split -x --no-cov` | ❌ W0 | ⬜ pending |
| 16-04-01 | 04 | 2 | EVAL-04 | — | N/A | integration | `pytest tests/unit/search/test_bench_snapshot.py -x --no-cov` | ❌ W0 | ⬜ pending |
| 16-04-02 | 04 | 2 | EVAL-04 | — | N/A | integration | `pytest tests/unit/search/test_bench_snapshot.py -k default_lock -x --no-cov` | ❌ W0 | ⬜ pending |
| 16-05-01 | 05 | 3 | QUAL-05 | T-16-01 | Reranker receives bounded `candidate_limit` (5-50) — no unbounded candidate fan-out | unit | `pytest tests/unit/search/test_hybrid.py -k candidate_fetch -x --no-cov` | ✅ extend | ⬜ pending |
| 16-05-02 | 05 | 3 | QUAL-05 | — | N/A | unit | `pytest tests/unit/inference/test_reranker.py -k relative_threshold -x --no-cov` | ✅ extend | ⬜ pending |
| 16-05-03 | 05 | 3 | QUAL-05 | — | N/A | unit | `pytest tests/unit/config/test_settings.py -k rerank -x --no-cov` | ✅ extend | ⬜ pending |
| 16-05-04 | 05 | 3 | QUAL-05 | — | N/A | integration | `pytest tests/unit/cli/test_search.py -k rerank_off -x --no-cov` | ✅ extend | ⬜ pending |
| 16-06-01 | 06 | 3 | EVAL-01, QUAL-05 | — | N/A | structural | `pytest tests/unit/search/test_benchmark_metrics.py -k latency -x --no-cov` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/search/test_benchmark_metrics.py` — nDCG/Hit/percentile/precision-binary/latency injection
- [ ] `tests/unit/search/test_sweep.py` — grid enumeration, tie groups, boundary, tuning-only guard, embedding-once spy
- [ ] `tests/unit/search/test_bench_fixture.py` — fixture contract + corpus/relevance integrity
- [ ] `tests/unit/search/test_bench_snapshot.py` — deterministic DB + held-out snapshot/default lock
- [ ] `tests/support/bench.py` — `ConceptEmbedder` + `build_bench_db()` (direct `SchemaManager` + fixed IDs + vec0 inserts, modeled on `tests/unit/search/test_hybrid.py:620-773`)
- [ ] `tests/fixtures/bench/{corpus,queries.json,heldout_defaults.json}` — the committed pack
- [ ] `docs/benchmarking.md` — format, formulas, sweep rule, evidence table; add to `DOCS_FILES` in `tests/test_docs.py:20-31`
- [ ] Extend `tests/unit/cli/test_bench.py` for `--sweep`, `--rerank`, rerank states, categories, JSON schema
- [ ] Extend `tests/unit/inference/test_reranker.py`, `tests/unit/search/test_hybrid.py`, `tests/unit/config/test_settings.py`, `tests/unit/cli/test_search.py` for cap/α/opt-in

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real-model held-out evidence (the committed `heldout_defaults.json` snapshot is deterministic-test evidence, not a real-embedder measurement) | EVAL-04 | Requires downloading a real embedding model; results are not reproducible across platforms/versions, so it cannot gate CI | Run `sif bench --json` against the committed corpus with the default real model; record nDCG@10/Hit@10/p50/p95 in `docs/benchmarking.md`'s evidence table and in the phase artifact |
| Interactive-latency claim on the evaluator's actual hardware | QUAL-05, SC5 | Machine-dependent | Record rerank-on vs rerank-off p50/p95 from `sif bench` on the operator's box; document the reference figure (research recommends a 500 ms off-state reference, not a CI gate) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
