---
phase: "18"
slug: "quality-instrument-personal-bench-rapidfuzz-dym"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-11-14"
validated: "2026-11-14"
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 (CI-locked; local 9.1.1) + pytest-cov 7.1.0 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` + `[tool.coverage.report]` (`fail_under = 90`) |
| **Quick run command** | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search/test_personal_bench.py tests/unit/cli/test_eval.py tests/unit/search/test_suggest.py tests/unit/cli/test_suggest.py -x --no-cov` |
| **Full suite command** | `env -u FORCE_COLOR NO_COLOR=1 pytest` (1859 tests collected at HEAD `b6078d3`; 1858 passed, 1 skipped, 95.17% coverage) |
| **Estimated runtime** | ~100 s full suite (measured 2026-11-14 at HEAD `b6078d3`); ≤ 8 s targeted |

---

## Sampling Rate

- **After every task commit:** Run the quick run command + `ruff check src tests` + `ruff format --check src tests`
- **After every plan wave:** Run `env -u FORCE_COLOR NO_COLOR=1 pytest` + `ty check src/sif`
- **Before `/gsd-verify-work`:** Full suite green; `make docs-generate` diff clean; `python scripts/generate_bench_fixture.py --check` clean; DYM ≤10 ms p50 evidence recorded
- **Max feedback latency:** ~120 seconds (full suite); ≤ 10 seconds (targeted)

---

## Per-Task Verification Map

Task IDs assigned at execution time; requirement-level map from `18-RESEARCH.md` §Validation Architecture, audited 2026-11-14:

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 18-01 T1 | 18-01 | 1 | EVAL-01 | T-18-01/02/15 | Title/H1 and body-snippet synthesis is deterministic and label-free | unit | `pytest tests/unit/search/test_personal_bench.py -x --no-cov` | ✅ | ✅ green |
| 18-01 T1 | 18-01 | 1 | EVAL-01 | — | Legacy fixture + `SearchEvaluator` known-item metrics (target=1, others=0) | unit | `pytest tests/unit/search/test_personal_bench.py::TestKnownItemFixture -x --no-cov` | ✅ | ✅ green |
| 18-02 T3 | 18-02 | 2 | EVAL-01 | — | query_log replay: rows replayed, no-baseline recorded, baseline stability computed, CLI-only bias present | unit | `pytest tests/unit/search/test_personal_bench.py::TestReplay -x --no-cov` | ✅ | ✅ green |
| 18-01 T1/T2 + 18-03 T1 | 18-01,18-03 | 1,3 | EVAL-01 | T-18-07 | `sif eval --personal` table + `--json`, saved path, `--no-save`, thresholds, embed remedy, `--bm25-only` | cli | `pytest tests/unit/cli/test_eval.py -x --no-cov` | ✅ | ✅ green |
| 18-02 T1 | 18-02 | 2 | EVAL-02 | — | Per-leg overlap budget: title/H1 exact-term, body Jaccard ≤0.60, rejection counts reported | unit | `pytest tests/unit/search/test_personal_bench.py::TestOverlapBudget -x --no-cov` | ✅ | ✅ green |
| 18-02 T2 | 18-02 | 2 | EVAL-02 | — | Per-leg × per-language × length-bucket groups; <10 suppression + names | unit | `pytest tests/unit/search/test_personal_bench.py::TestGroups -x --no-cov` | ✅ | ✅ green |
| 18-02 T2 | 18-02 | 2 | EVAL-02 | — | sha256 50/50 split stable; held-out ≥25; widen sampling | unit | `pytest tests/unit/search/test_personal_bench.py::TestSplit -x --no-cov` | ✅ | ✅ green |
| 18-03 T2 | 18-03 | 3 | EVAL-02 | T-18-10 | Paired deltas, seeded bootstrap CI, 0.01 gate, 1/N floor, helped/hurt/unchanged | unit | `pytest tests/unit/search/test_personal_bench.py::TestNoiseGate -x --no-cov` | ✅ | ✅ green |
| 18-03 T1/T2 | 18-03 | 3 | EVAL-02 | T-18-07/08/09 | Corpus fingerprint + `--compare` mismatch refusal + saved-run envelope validation + id-keyed grading | unit + cli | `pytest tests/unit/search/test_personal_bench.py::TestSavedRun tests/unit/cli/test_eval.py -x --no-cov` | ✅ | ✅ green |
| 18-04 T3 | 18-04 | 2 | QUAL-01 | T-18-SC | Full-vocabulary rapidfuzz scan; no first-letter bucket; first-letter typo recall | unit | `pytest tests/unit/search/test_suggest.py::TestDidYouMean tests/unit/search/test_suggest.py::TestCoreBudget -x --no-cov` | ✅ | ✅ green |
| 18-04 T3 | 18-04 | 2 | QUAL-01 | — | Cutoff 75 boundary + below-cutoff behavior + deterministic tie-break | unit | `pytest tests/unit/search/test_suggest.py -x --no-cov` | ✅ | ✅ green |
| 18-04 T3 | 18-04 | 2 | QUAL-01 | — | Probe/hit contracts and prefix/history sections unchanged | unit + cli | `pytest tests/unit/search/test_suggest.py tests/unit/cli/test_suggest.py -x --no-cov` | ✅ | ✅ green |
| 18-04 T3 | 18-04 | 2 | QUAL-01 | — | ≤10 ms core budget with generous CI headroom; measured p50 recorded | unit + manual | `pytest tests/unit/search/test_suggest.py::TestCoreBudget -x --no-cov` + SUMMARY evidence | ✅ | ✅ green |
| 18-01…18-04 | all | 1–3 | ALL | — | Lint/format/type gates | static | `ruff check src tests && ruff format --check src tests && ty check src/sif` | ✅ | ✅ green |
| 18-01 T3 + 18-03 T3 | 18-01,18-03 | 1,3 | ALL | — | Generated docs are current | docs | `make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md` | ✅ | ✅ green |
| 18-01…18-04 | all | 1–3 | ALL | — | Committed bench fixture untouched | drift | `python scripts/generate_bench_fixture.py --check` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Guard inventory (measured 2026-11-14, HEAD `b6078d3`):** 172 test functions across `test_personal_bench.py` (80), `test_eval.py` (45), `test_suggest.py` (32), and `test_suggest.py` CLI (15); 226 targeted tests collected and green in 7.91 s; full suite 1858 passed / 1 skipped @ 95.17%.

---

## Wave 0 Requirements

- [x] `tests/support/eval.py` — personal corpus DB builder (documents with title/content/checksum) + query_log seeding + hermetic cache dir
- [x] `tests/unit/search/test_personal_bench.py` — EVAL-01/EVAL-02 domain behavior
- [x] `tests/unit/cli/test_eval.py` — CLI surface and saved-run path
- [x] `tests/unit/search/test_suggest.py` — full-vocabulary spy, first-letter recall, cutoff boundary, tie-break
- [x] `docs/cli-reference.md` — regenerated after the `eval` group and the generator leaf-group fix
- [x] `uv.lock` — regenerated after adding `rapidfuzz` (3.14.5 / 3.14.6 split)
- [x] Framework install: none — pytest/pytest-cov are already locked dev deps

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions | Verified |
|----------|-------------|------------|-------------------|----------|
| DYM core function ≤10 ms with measured p50 | QUAL-01 | Machine-dependent timing; the automated test asserts a generous ceiling, the real evidence is a recorded measurement | Run the `SuggestionEngine.did_you_mean` timing probe on the 73k-term vocabulary; record p50/p95 in the SUMMARY | ✅ p50 1.513 ms / p95 1.629 ms @ 73,040 terms (rapidfuzz 3.14.6, Python 3.13.9) |
| Personal eval report is interpretable on a real corpus | EVAL-02 | Requires a human judgment about whether the report's groups/noise warnings communicate trust honestly | Run `sif eval --personal` on a local corpus ≥50 docs; inspect the table + JSON for group names, suppressed groups, N, 1/N floor, and CLI-only bias note | ✅ exercised against the 60-document fixture in `tests/support/eval.py`; real personal-corpus interpretation remains a user action |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-11-14 — 16/16 requirement rows covered, 226/226 targeted tests green, 0 gaps, 0 escalated.

## Validation Audit 2026-11-14

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
