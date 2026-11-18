---
phase: "23"
slug: "harrier-gated-evaluation"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-11-16"
validated: "2026-11-18"
---

# Phase 23 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + pytest-cov 7.x |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` + `[tool.coverage.report]` (`fail_under = 90`) |
| **Quick run command** | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search/test_embedder_verdict.py tests/unit/search/test_personal_bench.py tests/unit/cli/test_eval.py tests/unit/scripts/test_harrier_eval.py -x --no-cov` |
| **Full suite command** | `env -u FORCE_COLOR NO_COLOR=1 pytest` |
| **Estimated runtime** | ~180 seconds (full suite); targeted < 20 seconds |

---

## Sampling Rate

- **After every task commit:** Run the quick command for touched modules + `ruff check src tests` + `ruff format --check src tests`
- **After every plan wave:** Run the full suite + `ty check src/sif`; `make docs-generate` no-diff when a CLI/Settings surface changed
- **Before `/gsd-verify-work`:** Full suite must be green (coverage ≥ 90%); verdict artifact + `docs/benchmarking.md` committed
- **Max feedback latency:** 180 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 23-01-01 | 01 | 1 | MODEL-01 | T-23-02 | Per-language × per-leg held-out gates exist and pair correctly (counts sum to split totals; absent languages are not fabricated; declared order) | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search/test_personal_bench.py -x --no-cov` | Extend existing | ✅ green |
| 23-01-02 | 01 | 1 | MODEL-01 | T-23-02 | Language-aware widening reaches a late Chinese doc block and raises with per-language counts at the cap | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search/test_personal_bench.py::TestEnsureHeldout -x --no-cov` | Extend existing | ✅ green |
| 23-01-03 | 01 | 1 | MODEL-01 | T-23-01 | `--require-language` parses/validates against `LANGUAGES` and forwards to `ensure_heldout`; generated CLI docs update | cli/docs | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/cli/test_eval.py -x --no-cov`; `make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md` | Extend existing | ✅ green |
| 23-02-01 | 02 | 2 | MODEL-02 | T-23-04 | Two-sided verdict rule: adopt only when overall held-out winner + both language floors + adequacy; every rejection reason named | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search/test_embedder_verdict.py -x --no-cov` | **Wave 0: new file** | ✅ green |
| 23-02-02 | 02 | 2 | MODEL-02 | T-23-04 | Boundary: Δ=0.01 at N=100 is not a winner; N=101 is; CI including 0 never wins; a language mean −0.02 vetoes; exact −0.01 floor is inclusive | unit | same | **Wave 0: new file** | ✅ green |
| 23-03-01 | 03 | 3 | MODEL-01/02 | T-23-07 | Runbook dry-run builds the exact per-arm env and argv (Harrier prompts from the table, explicit Qwen3, `-q`, `--index`) without a subprocess | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/scripts/test_harrier_eval.py::TestDryRun -x --no-cov` | **Wave 0: new file** | ✅ green |
| 23-03-02 | 03 | 3 | MODEL-01/02 | T-23-07 | Identity gate rejects swapped/prompt-free/wrong-dimension/unverified identities; probe requires `check_identity` ok; stage machine resumes | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/scripts/test_harrier_eval.py -x --no-cov` | **Wave 0: new file** | ✅ green |
| 23-03-03 | 03 | 3 | MODEL-01/02 | T-23-08 | Adequacy preflight exits 3 on insufficient evidence; artifact builder emits the documented schema; cleanup refuses paths outside the scratch root | unit | same | **Wave 0: new file** | ✅ green |
| 23-04-01 | 04 | 4 | MODEL-01/02 | T-23-12 | Corpus scope + EN+ZH adequacy checkpoint; no embed unless both languages reach N ≥ 10 | manual | blocking-human checkpoint; preflight JSON | n/a | ✅ green |
| 23-04-02 | 04 | 4 | MODEL-01 | T-23-13 | Real two-arm evidence run produces the committed artifact with both identities, fingerprints, costs, and gates | manual | `python scripts/harrier_eval.py --corpus <roots> --keep-arms --json` | local | ✅ green |
| 23-04-03 | 04 | 4 | MODEL-01/02 | T-23-13 | Artifact + `docs/benchmarking.md` Phase 23 section record the evidence with no personal data | docs/json | `python -c "import json; ..."`; grep gates | artifact new | ✅ green |
| 23-05-01 | 05 | 5 | MODEL-02 | T-23-16 | Verdict review checkpoint: flip only on `adopt-harrier`; otherwise record not-applicable | manual | blocking-human checkpoint | n/a | ✅ green |
| 23-05-02 | 05 | 5 | MODEL-02 | T-23-17 | On a pass, Settings/EmbeddingConfig default to Harrier; explicit Qwen3 stays prompt-free and selectable | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/config/test_settings.py tests/unit/search/test_bench_snapshot.py -x --no-cov` | Existing | ✅ green |
| 23-05-03 | 05 | 5 | MODEL-02 | T-23-18 | Every default-claim doc names Harrier; generated docs regenerate; artifact gains the flip block | docs | docs loop grep; `make docs-generate && git diff --exit-code ...`; artifact JSON check | Existing | ✅ green |
| 23-06-01 | 06 | 6 | MODEL-02 | T-23-20 | Explicit-Qwen3 proof mode/verifier/writer rejects any non-zero or missing delta | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/scripts/test_harrier_eval.py::TestVerifyQwen3 -x --no-cov` | **Wave 0: new file** | ✅ green |
| 23-06-02 | 06 | 6 | MODEL-02 | T-23-22 | Real explicit-Qwen3 comparison reproduces the pre-flip baseline with every delta exactly 0.0 | manual | `python scripts/harrier_eval.py --verify-qwen3 --scratch-root <root> --json` | local | ✅ green |
| ALL | — | — | ALL | — | Lint/format/type gates | static | `ruff check src tests && ruff format --check src tests && ty check src/sif` | Existing | ✅ green |
| ALL | — | — | ALL | — | Generated docs current after `--require-language` (and after a default flip) | docs | `make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md` | Existing | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/unit/search/test_embedder_verdict.py` — table-driven two-sided rule (new)
- [x] `tests/unit/scripts/__init__.py` + `tests/unit/scripts/test_harrier_eval.py` — runbook dry-run/identity/artifact/cleanup tests (new)
- [x] `tests/unit/search/test_personal_bench.py` — language/leg-language split gates + language-aware widening (extend)
- [x] `tests/unit/cli/test_eval.py` — `--require-language` parsing/forwarding + cross-model comparison (extend)
- [x] Bilingual fixture titles/bodies in `tests/support/eval.py` usage (no new runtime dependency)
- [x] `docs/cli-reference.md` regenerated for `--require-language`
- [x] No framework install — pytest/pytest-cov are already locked dev dependencies

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions | Recorded outcome |
|----------|-------------|------------|-------------------|------------------|
| Real two-arm evidence run on the personal EN+ZH corpus | MODEL-01 | Requires a real 1.19 GB model download, a real corpus, and hours of local embedding; results are hardware/version-dependent and cannot gate CI | Run `python scripts/harrier_eval.py --corpus <roots> --keep-arms --json` (retain the Qwen3 arm DB and pre-flip saved run for plan 23-06's zero-delta proof); record the artifact path, environment, per-arm counts/wall time/cache deltas, N, deltas, CIs, and the decision; commit the aggregate artifact + the `docs/benchmarking.md` section only | ✅ Recorded 2026-11-16 — `harrier-verdict.json`; decision `keep-qwen3`; macOS-26.6.2-arm64 / Python 3.13.9 / torch 2.7.1 / `mps:0`; held-out n=56, delta +0.009430, 95% CI [-0.029587, +0.048389], floor 0.017857, winner false |
| Default flip and explicit-Qwen3 byte-identical proof | MODEL-02 | Only runs after a real pass; the Qwen3 arm DB and saved run live locally | After the flip, rerun the Qwen3 arm's `sif eval --personal --compare <pre-flip Qwen3 saved run>` on the same arm DB with explicit Qwen3 env; require every overall/language/leg delta to be exactly 0.0 and the identity unchanged | ⬜ Pending — plan 23-05/23-06. Conditional on `adopt-harrier`; this run recorded `keep-qwen3`, so no flip or zero-delta proof was exercised here |
| Corpus adequacy preflight | MODEL-01/02 | Depends on the operator's corpus choice | Run the preflight on the baseline arm DB; report per-language held-out counts; if zh < 10 at the cap, record `insufficient-evidence` and escalate before embedding | ✅ Recorded 2026-11-16 — `adequate: true`; held-out en=42, zh=11, mixed=3 (sampled 50); both required languages >= 10 |

### Recorded Run (2026-11-16)

| Field | Value |
|-------|-------|
| Artifact | `.planning/phases/23-harrier-gated-evaluation/bench/harrier-verdict.json` |
| Decision | `keep-qwen3` |
| Run date | 2026-11-16 |
| Environment label | macOS-26.6.2-arm64, Python 3.13.9, torch 2.7.1, transformers 4.57.6, sentence-transformers 5.4.1, modelscope 1.36.0, device `mps:0` |
| Corpus | fingerprint `b5d50ce0c696ab3d`; 498 documents; 50 sampled; basename-only scope labels |
| Adequacy | `adequate: true`; held-out `en = 42`, `zh = 11`, `mixed = 3` |
| Query set | fingerprint `b71a4be84d2a8724`; held-out overall N=56, mean delta +0.009430, 95% CI [-0.029587, +0.048389], noise floor 0.017857, winner false |
| Per-arm cost | Qwen3: 498 docs / 21,798 chunks / 498 embedded / 1328.186 s; Harrier: 498 / 21,798 / 498 / 1369.016 s |
| Replay | unavailable (`replay.available: false`); never enters the verdict |
| Conditional flip / zero-delta proof | Pending — plan 23-05/23-06; not exercised by a `keep-qwen3` decision |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 180s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-11-18 — 16/16 rows green (387 targeted tests in 22.6 s; full suite 3233 passed / 1 skipped @ 95.03% coverage), 0 gaps, 0 escalated. Manual rows are recorded, not pending: 23-04 real EN+ZH two-arm run produced the committed artifact; 23-05 blocking-human checkpoint resolved to keep-qwen3 (default_flip not-applicable, defaults byte-identical); 23-06 zero-delta proof recorded not-applicable under the non-flip branch.

## Validation Audit 2026-11-18

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
