---
phase: "23"
slug: "harrier-gated-evaluation"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-16"
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
| 23-01-01 | 01 | 1 | MODEL-01 | T-23-01 | Per-language × per-leg held-out gates exist and pair correctly (counts sum to split totals; absent languages are not fabricated; declared order) | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search/test_personal_bench.py -x --no-cov` | Extend existing | ⬜ pending |
| 23-01-02 | 01 | 1 | MODEL-01 | T-23-01 | Language-aware widening reaches a late Chinese doc block and raises with per-language counts at the cap | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search/test_personal_bench.py::TestEnsureHeldout -x --no-cov` | Extend existing | ⬜ pending |
| 23-01-03 | 01 | 1 | MODEL-01/MODEL-02 | T-23-01 | `--require-language` parses/validates against `LANGUAGES` and forwards to `ensure_heldout`; generated CLI docs update | cli/docs | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/cli/test_eval.py -x --no-cov`; `make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md` | Extend existing | ⬜ pending |
| 23-02-01 | 02 | 2 | MODEL-02 | T-23-02 | Two-sided verdict rule: adopt only when overall held-out winner + both language floors + adequacy; every rejection reason named | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search/test_embedder_verdict.py -x --no-cov` | **Wave 0: new file** | ⬜ pending |
| 23-02-02 | 02 | 2 | MODEL-02 | T-23-02 | Boundary: Δ=0.01 at N=100 is not a winner; N=101 is; CI including 0 never wins; a language mean −0.02 vetoes | unit | same | **Wave 0: new file** | ⬜ pending |
| 23-02-03 | 02 | 2 | MODEL-01/02 | T-23-03 | Runbook dry-run builds the exact per-arm env (Harrier prompts from the table, explicit Qwen3, `-q`, `--index`); identity checker rejects swapped/prompt-free/wrong-dimension/unverified identities; artifact builder emits the documented schema; cleanup refuses paths outside the scratch root | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/scripts/test_harrier_eval.py -x --no-cov` | **Wave 0: new file** | ⬜ pending |
| 23-03-01 | 03 | 3 | MODEL-01 | T-23-02 | Two-arm fixture: baseline saved run + candidate comparison yields the expected verdict record; same query set/order/top_k; query-set fingerprint matches | integration (fixture DBs) | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/scripts/test_harrier_eval.py -x --no-cov` | **Wave 0: new file** | ⬜ pending |
| 23-04-01 | 04 | 4 | MODEL-02 | T-23-02 | No-win leaves settings/defaults untouched; a pass flips Settings, regenerates docs, and explicit-Qwen3 reproduces zero deltas | unit + manual | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/config/test_settings.py tests/unit/search/test_bench_snapshot.py -x --no-cov`; manual zero-delta proof | Existing + manual | ⬜ pending |
| ALL | — | — | ALL | — | Lint/format/type gates | static | `ruff check src tests && ruff format --check src tests && ty check src/sif` | Existing | ⬜ pending |
| ALL | — | — | ALL | — | Generated docs current after `--require-language` (and after a default flip) | docs | `make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md` | Existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/search/test_embedder_verdict.py` — table-driven two-sided rule (new)
- [ ] `tests/unit/scripts/__init__.py` + `tests/unit/scripts/test_harrier_eval.py` — runbook dry-run/identity/artifact/cleanup tests (new)
- [ ] `tests/unit/search/test_personal_bench.py` — language/leg-language split gates + language-aware widening (extend)
- [ ] `tests/unit/cli/test_eval.py` — `--require-language` parsing/forwarding + cross-model comparison (extend)
- [ ] Bilingual fixture titles/bodies in `tests/support/eval.py` usage (no new runtime dependency)
- [ ] `docs/cli-reference.md` regenerated for `--require-language`
- [ ] No framework install — pytest/pytest-cov are already locked dev dependencies

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real two-arm evidence run on the personal EN+ZH corpus | MODEL-01 | Requires a real 1.19 GB model download, a real corpus, and hours of local embedding; results are hardware/version-dependent and cannot gate CI | Run `python scripts/harrier_eval.py --corpus <roots> --json`; record the artifact path, environment, per-arm counts/wall time/cache deltas, N, deltas, CIs, and the decision; commit the aggregate artifact + the `docs/benchmarking.md` section only |
| Default flip and explicit-Qwen3 byte-identical proof | MODEL-02 | Only runs after a real pass; the Qwen3 arm DB and saved run live locally | After the flip, rerun the Qwen3 arm's `sif eval --personal --compare <pre-flip Qwen3 saved run>` on the same arm DB with explicit Qwen3 env; require every overall/language/leg delta to be exactly 0.0 and the identity unchanged |
| Corpus adequacy preflight | MODEL-01/02 | Depends on the operator's corpus choice | Run the preflight on the baseline arm DB; report per-language held-out counts; if zh < 10 at the cap, record `insufficient-evidence` and escalate before embedding |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 180s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
