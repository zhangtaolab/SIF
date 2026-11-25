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
| 18-01 T1 | 18-01 | 1 | EVAL-01 | — | Legacy fixture + `SearchEvaluator` known-item metrics (target=1, others=0) | unit | `pytest tests/unit/cli/test_eval.py::TestEvaluatePerQuery -x --no-cov` | ✅ | ✅ green |
| 18-02 T3 | 18-02 | 2 | EVAL-01 | — | query_log replay: rows replayed, no-baseline recorded, baseline stability computed, CLI-only bias present | unit | `pytest tests/unit/search/test_personal_bench.py::TestReplay -x --no-cov` | ✅ | ✅ green |
| 18-01 T1/T2 + 18-03 T1 | 18-01,18-03 | 1,3 | EVAL-01 | T-18-07 | `sif eval --personal` table + `--json`, saved path, `--no-save`, thresholds, embed remedy, `--bm25-only` | cli | `pytest tests/unit/cli/test_eval.py -x --no-cov` | ✅ | ✅ green |
| 18-02 T1 | 18-02 | 2 | EVAL-02 | — | Per-leg overlap budget: title/H1 exact-term, body Jaccard ≤0.60, rejection counts reported | unit | `pytest tests/unit/search/test_personal_bench.py::TestOverlapBudget -x --no-cov` | ✅ | ✅ green |
| 18-02 T2 | 18-02 | 2 | EVAL-02 | — | Per-leg × per-language × length-bucket groups; <10 suppression + names | unit | `pytest tests/unit/search/test_personal_bench.py::TestGroups -x --no-cov` | ✅ | ✅ green |
| 18-02 T2 | 18-02 | 2 | EVAL-02 | — | sha256 50/50 split stable; held-out ≥25; widen sampling | unit | `pytest tests/unit/search/test_personal_bench.py::TestSplit -x --no-cov` | ✅ | ✅ green |
| 18-03 T2 | 18-03 | 3 | EVAL-02 | T-18-10 | Paired deltas, seeded bootstrap CI, 0.01 gate, 1/N floor, helped/hurt/unchanged | unit | `pytest tests/unit/search/test_personal_bench.py::TestNoiseGate -x --no-cov` | ✅ | ✅ green |
| 18-03 T1/T2 | 18-03 | 3 | EVAL-02 | T-18-07/08/09 | Corpus fingerprint + `--compare` mismatch refusal + saved-run envelope validation + id-keyed grading | unit + cli | `pytest tests/unit/search/test_personal_bench.py::TestSavedRunContract tests/unit/search/test_personal_bench.py::TestCorpusFingerprint tests/unit/search/test_personal_bench.py::TestCompareSavedRun tests/unit/cli/test_eval.py -x --no-cov` | ✅ | ✅ green |
| 18-04 T3 | 18-04 | 2 | QUAL-01 | T-18-SC | Full-vocabulary rapidfuzz scan; no first-letter bucket; first-letter typo recall | unit | `pytest tests/unit/search/test_suggest.py::TestDidYouMean tests/unit/search/test_suggest.py::TestCoreBudget -x --no-cov` | ✅ | ✅ green |
| 18-04 T3 | 18-04 | 2 | QUAL-01 | — | Cutoff 75 boundary + below-cutoff behavior + deterministic tie-break | unit | `pytest tests/unit/search/test_suggest.py -x --no-cov` | ✅ | ✅ green |
| 18-04 T3 | 18-04 | 2 | QUAL-01 | — | Probe/hit contracts and prefix/history sections unchanged | unit + cli | `pytest tests/unit/search/test_suggest.py tests/unit/cli/test_suggest.py -x --no-cov` | ✅ | ✅ green |
| 18-04 T3 | 18-04 | 2 | QUAL-01 | — | ≤10 ms core budget with generous CI headroom; measured p50 recorded | unit + manual | `pytest tests/unit/search/test_suggest.py::TestCoreBudget -x --no-cov` + SUMMARY evidence | ✅ | ✅ green |
| 18-01…18-04 | all | 1–3 | ALL | — | Lint/format/type gates | static | `ruff check src tests && ruff format --check src tests && ty check src/sif` | ✅ | ⚠️ green except `ty` |
| 18-01 T3 + 18-03 T3 | 18-01,18-03 | 1,3 | ALL | — | Generated docs are current | docs | `make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md` | ✅ | ✅ green |
| 18-01…18-04 | all | 1–3 | ALL | — | Committed bench fixture untouched | drift | `python scripts/generate_bench_fixture.py --check` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Guard inventory (measured 2026-11-14, HEAD `b6078d3`):** 172 test functions across `test_personal_bench.py` (80), `test_eval.py` (45), `test_suggest.py` (32), and `test_suggest.py` CLI (15); 226 targeted tests collected and green in 7.91 s; full suite 1858 passed / 1 skipped @ 95.17%.

**Map corrections (2026-11-25 re-audit, HEAD `46f597b`).** Two rows cited class selectors that never existed, so both commands exited 4 (`ERROR: not found`) and ran no test, including the `tests/unit/cli/test_eval.py` half of the second. The names are the planned classes from `18-RESEARCH.md` §Validation Architecture and `18-PATTERNS.md`, not the implemented ones, and the test files involved are byte-identical to `b817ebb`, so this predates the delta described at the end of this file. The `TestKnownItemFixture` row (18-01 T1) now points at `tests/unit/cli/test_eval.py::TestEvaluatePerQuery`, which pins target-at-rank-1 → 1.0 and target-absent → 0.0 (`grades == [1]` / `[0]`) on a legacy fixture. The `TestSavedRun` row (18-03 T1/T2) now points at the implemented `TestSavedRunContract`, plus `TestCorpusFingerprint` and `TestCompareSavedRun`, which carry the fingerprint and id-keyed grading halves of that row's stated behaviour. Both corrected commands exit 0 (2 passed; 97 passed). `build_legacy_fixture` has no test naming it; it is pinned through `compare_saved_run` (`TestCompareSavedRun::test_unique_path_is_the_only_fallback` asserts the current arm's nDCG@10 is 1.0 for the id-resolved target) and runs on every `sif eval --personal` and `--compare` path.

**Gate note (2026-11-25 re-audit):** `ruff check src tests` and `ruff format --check src tests` are green. `ty check src/sif` exits 1 locally with 10 diagnostics, all in `src/sif/embedding/embedder.py` (5), `src/sif/models/download.py` (1) and `src/sif/search/rerank.py` (4) and none in a Phase 18 file. The diagnostic set is identical at `b817ebb` and HEAD in the same local environment, whose `transformers` 4.57.6, `huggingface-hub` 0.36.2 and `torch` 2.7.1 differ from the locked 5.5.4, 1.10.2 and 2.14.1. CI's `Type check` step is green (run `45522236981`), but its lint job installs `--extra dev` only and `[tool.ty.rules]` sets `import-not-found = "ignore"`, so the third-party symbols behind those diagnostics are unresolved there. Not a Phase 18 regression and not a requirement-coverage gap.

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

**Incremental re-audit (2026-11-25, HEAD `46f597b`).** Three Phase 18-covered inputs changed since the 2026-11-14 audit (last committed `b817ebb`): `pyproject.toml` and `uv.lock` at `848e6b6` (only the two `torch` extra floors, `"torch"` → `"torch>=2.11"`, plus the lock's torch specifiers and resolution-marker ordering), and `tests/test_docs.py` (+16/−2 at `9d85c9cd` and `6b409030`: installation-doc guards for the torch backend matrix, and `docs/machine-migration.md` registered in `DOCS_FILES`). No row cites the torch extras, and Phase 18's own pin in `tests/test_docs.py` (`"eval": []` in `_SUBCOMMANDS`) has no changed line, so the delta invalidates nothing.

- **Re-verified:** The config-file row holds: `[tool.pytest.ini_options]` and `[tool.coverage.report]` (`fail_under = 90`) are byte-identical to `b817ebb`, and no other pytest or coverage config file exists. The `uv.lock` note holds: `"rapidfuzz>=3.14.5,<4"` at `pyproject.toml:41` is untouched, the lock still splits 3.14.5 (`python_full_version < '3.11'`) from 3.14.6 (`>= '3.11'`), and the 18-04 Task 2 gate exits 0 on all three legs (`uv lock --check`, `uv sync --frozen --extra dev --extra embed --dry-run`, `rapidfuzz 3.14.6` on py3.13). The rapidfuzz 3.14.6 block is not byte-identical, though: two of its `resolution-markers` strings were reordered (same marker set), as uv also did in nine other package blocks and the lock header. `tests/test_docs.py` passes 21, and the docs gate exits 0 with both generated docs byte-identical, also through `scripts/generate_config_ref.py`, which changed after `b817ebb` but is not a Phase 18 file. The quick run passes 281 in 17.94 s, every other pytest row exits 0 (159, 7, 75, 7, 3, 2, 10, 17, 32, 47 and 1 passed), and the bench fixture check is clean (151 files).
- **Result:** 0 requirement-coverage gaps, so `nyquist_compliant: true` is retained and no test was generated. `verification.append-audit` skipped a duplicate audit block (0 found, 0 resolved, 0 escalated). `gsd-nyquist-auditor` was not spawned, because the workflow skips that step when there are no gaps. Three rows predate the delta and are recorded above: the two map commands corrected, and the `ty` leg of the ALL gate.
- **Full suite:** not re-run locally; 3261 tests collect at HEAD with `pytest` from PATH (9.1.1, `pytest-cov` 7.0.0, miniconda py3.13.9). Test Matrix run `45522236981` on `a25eb07` (an ancestor of HEAD; `a25eb07..HEAD` differs only under `.planning/`) passed all 9 jobs: 8/8 cells with 3259 passed, 2 skipped and 95.12% coverage against the enforced 90% floor, plus the lint job.
- **Carried forward, not re-run:** the Manual-Only rows, the DYM p50 measurement, and the guard inventory figures dated 2026-11-14, which stay as stamped.
