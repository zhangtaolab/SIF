---
phase: "25"
slug: "contract-freeze-feasibility-spike"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-28"
---

# Phase 25 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Honest framing (from 25-RESEARCH.md `## Validation Architecture`): this phase adds
> **no pytest guards and no `src/sif` code**, so most verification is artifact / command-output based.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.2.0 + pytest-cov 7.17.5 |
| **Config file** | `pyproject.toml` → `[tool.pytest.ini_options]` (`addopts` include `--cov=src/sif`; `[tool.coverage.report]` `fail_under=90`) |
| **Quick run command** | `python -m pytest tests/unit/mcp/test_wire_transcripts.py tests/unit/mcp/test_packaging.py -q --no-cov` |
| **Full suite command** | `python -m pytest -q` (a few thousand tests; not required for this phase) |
| **Estimated runtime** | ~0.60 s (measured: 13 passed for the two contract files with `--no-cov`) |

---

## Sampling Rate

- **After every task commit:** `shasum -a 256` over any touched freeze file (expect no change); run the quick pytest command when a CTR task is in scope.
- **After every plan wave:** recompute the full 11-file SHA-256 manifest and diff against the start manifest; quick pytest command green.
- **Before `/gsd-verify-work`:** start manifest == end manifest; both pytest files green; `git status --porcelain` shows only `M .planning/STATE.md` (session record) + the 3 D-16-whitelisted untracked planning docs; `src/`, `tests/`, `pyproject.toml`, `uv.lock` zero diff.
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| {N}-01-01 | 01 | 1 | SPK-01 | T-25-01 | `--model-path` validated as an existing absolute `.gguf`; load in subprocess, stderr captured | manual / artifact | `python spike_compat.py --model-path <abs .gguf>` (tmp) | ❌ W0 N/A — artifact-based | ⬜ pending |
| {N}-01-02 | 01 | 1 | SPK-02 | T-25-02 | tuning-only split; no gold/title reads; `SIF_DB_PATH` under `.planning/tmp/phase-25/` | manual / artifact | `python spike_delta.py` (tmp) | ❌ W0 N/A — artifact-based | ⬜ pending |
| {N}-01-03 | 01 | 1 | SPK-03 | T-25-03 | clean working tree proof; no half-finished product code | manual / artifact | `git status --porcelain`; `git diff --stat v1.2.5..HEAD -- <contract paths>`; `gsd_run state record-session` | ❌ W0 N/A — artifact-based | ⬜ pending |
| {N}-02-01 | 02 | 2 | CTR-01 / CTR-02 | T-25-04 | 5 goldens + 7 tools + `QueryInput` + 13 deps byte-identical | unit (existing) | `python -m pytest tests/unit/mcp/test_wire_transcripts.py tests/unit/mcp/test_packaging.py -q --no-cov` | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

**None — existing infrastructure covers all phase requirements.** This phase deliberately adds no test files, no fixtures, and no `src/sif` code. The only "framework" needs are `shasum`, `git`, the existing pytest pair, and `gsd_run state.record-session`, all present.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| GGUF availability + actual generation text | SPK-01 | D-01 forbids download; file is human-supplied | Human provides absolute `--model-path`; runbook records SHA-256, chat template, one greedy generation output |
| Isolated-venv 0.3.37 upgrade + success/failure transcript | SPK-01 | D-03 confines the upgrade to a throwaway venv | Create venv, install pinned wheel, run load, capture stderr, delete venv; record effect on `LlamaCppEmbedder` / GGUF rerank |
| Verdict rule applied literally (mean paired delta > 0 AND helped > hurt) | SPK-02 | D-08 is a judgment rule, not an automated gate | Inspect `bench/spike-delta.csv` and `bench/spike-verdict.json` side by side; confirm fixed-seed reproducibility |
| No-signal stop-loss session record | SPK-03 | D-15 writes STATE/ROADMAP session notes | Confirm `25-SPIKE-VERDICT.md` + verdict JSON + `state record-session`, ROADMAP Phase 25 checkbox unticked |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
