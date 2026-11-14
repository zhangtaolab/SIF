---
phase: "18"
slug: "quality-instrument-personal-bench-rapidfuzz-dym"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-14"
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 (CI-locked; local 9.1.1) + pytest-cov 7.1.0 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` + `[tool.coverage.report]` (`fail_under = 90`) |
| **Quick run command** | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search/test_personal_bench.py tests/unit/cli/test_eval.py tests/unit/search/test_suggest.py -x --no-cov` |
| **Full suite command** | `env -u FORCE_COLOR NO_COLOR=1 pytest` |
| **Estimated runtime** | ~90 s full suite (Phase 17 measured 77 s; new tests add a few seconds) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command + `ruff check src tests` + `ruff format --check src tests`
- **After every plan wave:** Run `env -u FORCE_COLOR NO_COLOR=1 pytest` + `ty check src/sif`
- **Before `/gsd-verify-work`:** Full suite green; `make docs-generate` diff clean; `python scripts/generate_bench_fixture.py --check` clean; DYM ≤10 ms p50 evidence recorded
- **Max feedback latency:** ~120 seconds (full suite); ≤ 30 seconds (quick run)

---

## Per-Task Verification Map

Task IDs are assigned at plan time; requirement-level map from `18-RESEARCH.md` §Validation Architecture:

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD (plan-time) | TBD | TBD | EVAL-01 | T-18-* / — | Title/H1 and body-snippet synthesis is deterministic and label-free | unit | `pytest tests/unit/search/test_personal_bench.py -x --no-cov` | ❌ W0 | ⬜ pending |
| TBD (plan-time) | TBD | TBD | EVAL-01 | — | Legacy fixture + `SearchEvaluator` known-item metrics (target=1, others=0) | unit | `pytest tests/unit/search/test_personal_bench.py::TestKnownItemFixture -x --no-cov` | ❌ W0 | ⬜ pending |
| TBD (plan-time) | TBD | TBD | EVAL-01 | — | query_log replay: rows replayed, no-baseline recorded, baseline stability computed, CLI-only bias present | unit | `pytest tests/unit/search/test_personal_bench.py::TestReplay -x --no-cov` | ❌ W0 | ⬜ pending |
| TBD (plan-time) | TBD | TBD | EVAL-01 | — | `sif eval --personal` table + `--json`, saved path, `--no-save`, thresholds, embed remedy, `--bm25-only` | cli | `pytest tests/unit/cli/test_eval.py -x --no-cov` | ❌ W0 | ⬜ pending |
| TBD (plan-time) | TBD | TBD | EVAL-02 | — | Per-leg overlap budget: title/H1 exact-term, body Jaccard ≤0.60, rejection counts reported | unit | `pytest tests/unit/search/test_personal_bench.py::TestOverlapBudget -x --no-cov` | ❌ W0 | ⬜ pending |
| TBD (plan-time) | TBD | TBD | EVAL-02 | — | Per-leg × per-language × length-bucket groups; <10 suppression + names | unit | `pytest tests/unit/search/test_personal_bench.py::TestGroups -x --no-cov` | ❌ W0 | ⬜ pending |
| TBD (plan-time) | TBD | TBD | EVAL-02 | — | sha256 50/50 split stable; held-out ≥25; widen sampling | unit | `pytest tests/unit/search/test_personal_bench.py::TestSplit -x --no-cov` | ❌ W0 | ⬜ pending |
| TBD (plan-time) | TBD | TBD | EVAL-02 | — | Paired deltas, seeded bootstrap CI, 0.01 gate, 1/N floor, helped/hurt/unchanged | unit | `pytest tests/unit/search/test_personal_bench.py::TestNoiseGate -x --no-cov` | ❌ W0 | ⬜ pending |
| TBD (plan-time) | TBD | TBD | EVAL-02 | — | Corpus fingerprint + `--compare` mismatch refusal + saved-run validation | unit + cli | `pytest tests/unit/search/test_personal_bench.py::TestSavedRun tests/unit/cli/test_eval.py -x --no-cov` | ❌ W0 | ⬜ pending |
| TBD (plan-time) | TBD | TBD | QUAL-01 | T-18-* | Full-vocabulary rapidfuzz scan; no first-letter bucket; first-letter typo recall | unit | `pytest tests/unit/search/test_suggest.py::TestDidYouMean tests/unit/search/test_suggest.py::TestCoreBudget -x --no-cov` | ✅ update | ⬜ pending |
| TBD (plan-time) | TBD | TBD | QUAL-01 | — | Cutoff 75 boundary + below-cutoff behavior + deterministic tie-break | unit | `pytest tests/unit/search/test_suggest.py -x --no-cov` | ✅ update | ⬜ pending |
| TBD (plan-time) | TBD | TBD | QUAL-01 | — | Probe/hit contracts and prefix/history sections unchanged | unit + cli | `pytest tests/unit/search/test_suggest.py tests/unit/cli/test_suggest.py -x --no-cov` | ✅ existing | ⬜ pending |
| TBD (plan-time) | TBD | TBD | QUAL-01 | — | ≤10 ms core budget with generous CI headroom; measured p50 recorded | unit + manual | `pytest tests/unit/search/test_suggest.py::TestCoreBudget -x --no-cov` + SUMMARY evidence | ✅ update | ⬜ pending |
| TBD (plan-time) | TBD | TBD | ALL | — | Lint/format/type gates | static | `ruff check src tests && ruff format --check src tests && ty check src/sif` | ✅ | ⬜ pending |
| TBD (plan-time) | TBD | TBD | ALL | — | Generated docs are current | docs | `make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md` | ✅ after changes | ⬜ pending |
| TBD (plan-time) | TBD | TBD | ALL | — | Committed bench fixture untouched | drift | `python scripts/generate_bench_fixture.py --check` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/support/eval.py` — personal corpus DB builder (documents with title/content/checksum) + query_log seeding + hermetic cache dir
- [ ] `tests/unit/search/test_personal_bench.py` — EVAL-01/EVAL-02 domain behavior
- [ ] `tests/unit/cli/test_eval.py` — CLI surface and saved-run path
- [ ] `tests/unit/search/test_suggest.py` — rewrite the difflib spy/budget test; add first-letter recall and cutoff-boundary tests
- [ ] `docs/cli-reference.md` — regenerate after adding the `eval` group (and any generator leaf-group fix)
- [ ] `uv.lock` — regenerate after adding `rapidfuzz`
- [ ] Framework install: none — pytest/pytest-cov are already locked dev deps

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| DYM core function ≤10 ms with measured p50 | QUAL-01 | Machine-dependent timing; the automated test asserts a generous ceiling, the real evidence is a recorded measurement | Run the `SuggestionEngine.did_you_mean` timing probe on the 73k-term vocabulary; record p50/p95 in the SUMMARY next to the automated test result |
| Personal eval report is interpretable on a real corpus | EVAL-02 | Requires a human judgment about whether the report's groups/noise warnings communicate trust honestly | Run `sif eval --personal` on a local corpus ≥50 docs; inspect the table + JSON for group names, suppressed groups, N, 1/N floor, and CLI-only bias note |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
