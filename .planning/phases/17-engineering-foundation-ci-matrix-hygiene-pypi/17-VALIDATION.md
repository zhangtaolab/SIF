---
phase: "17"
slug: "engineering-foundation-ci-matrix-hygiene-pypi"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-11-13"
validated: "2026-11-14"
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 + pytest-cov 7.1.0 (locked) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` + `[tool.coverage.report]` (`fail_under = 90`) |
| **Quick run command** | `env -u FORCE_COLOR NO_COLOR=1 pytest -x -q --no-cov` |
| **Full suite command** | `env -u FORCE_COLOR NO_COLOR=1 pytest` (1670 tests collected at HEAD `3348284`; 1669 passed, 1 skipped, 95.07% coverage) |
| **Estimated runtime** | ~77 s full suite (measured 2026-11-14 at HEAD `3348284`; quick run ≤ 30 s) |

---

## Sampling Rate

- **After every task commit:** Run `env -u FORCE_COLOR NO_COLOR=1 pytest -x -q --no-cov` plus `ruff check src tests` and `ruff format --check src tests`
- **After every plan wave:** Run `env -u FORCE_COLOR NO_COLOR=1 pytest` + `ty check src/sif` + `uv lock --check`
- **Before `/gsd-verify-work`:** Full suite green at HEAD `3348284` (1669 passed, 1 skipped @ 95.07%); Test Matrix run `43561542242` green on release HEAD `c819f67` (8 py cells + lint); Windows smoke 8/8 at `48759e2`
- **Max feedback latency:** ~77 seconds (full suite); ≤ 30 seconds (quick run)

---

## Per-Task Verification Map

Requirement-level map from `17-RESEARCH.md` §Validation Architecture, audited 2026-11-14 against the executed plans and the guard suite:

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 17-03 | 17-03 | 2 | ENG-01 | T-17-* | Workflow uses `pull_request` (not `pull_request_target`), `contents: read`, no secrets in matrix | unit (text-level YAML guard) | `pytest tests/test_ci_workflows.py -x` (14 tests) | ✅ | ✅ green |
| 17-02 | 17-02 | 1 | ENG-01 | — | Lock resolves CPU torch fleet, no CUDA/nvidia/triton | unit (parse `uv.lock`) | `pytest tests/test_ci_workflows.py::test_lock_has_cpu_torch -x` | ✅ | ✅ green |
| 17-04 | 17-04 | 2 | ENG-02 | — | Smoke script matchers recognize flock warning, missing-root warning, detach refusal | unit | `pytest tests/test_windows_smoke_script.py -x` (7 tests) | ✅ | ✅ green |
| 17-05 | 17-05 | 3 | ENG-03 | — | Job-scoped `id-token: write` on publish jobs only; tag↔version gate | unit (existing) | `pytest tests/test_version_identity.py -x` (4 tests) | ✅ | ✅ green |
| 17-05 | 17-05 | 3 | ENG-03 | — | README mcp-name marker present; changelog 1.1.2; publish workflow guards | unit | `pytest tests/test_release_metadata.py -x` (13 tests) | ✅ | ✅ green |
| 17-01 | 17-01 | 1 | ENG-04 | — | Dead modules not importable; no source/test imports them; `compute_rrf_score` gone | unit | `pytest tests/test_hygiene.py -x` (15 tests) | ✅ | ✅ green |
| 17-01/17-02/17-09 | 17-01,17-02,17-09 | 1,3 | ENG-04 | — | Makefile has no `pre-commit` target; pyproject no black/`[tool.black]`; extras floors correct; junk paths absent | unit | `pytest tests/test_hygiene.py -x` (15 tests) | ✅ | ✅ green |
| 17-01…17-09 | all | 1–5 | ENG-04 | — | Full suite + ruff + ty green after deletion | integration | `ruff check src tests && ruff format --check src tests && ty check src/sif && pytest`; matrix run `43561542242` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Guard inventory (measured 2026-11-14, HEAD `3348284`):** 53 tests across `test_ci_workflows.py` (14), `test_release_metadata.py` (13), `test_hygiene.py` (15), `test_windows_smoke_script.py` (7), and `test_version_identity.py` (4) — all green in 0.94 s with `--no-cov`.

---

## Wave 0 Requirements

- [x] `tests/test_ci_workflows.py` — ENG-01 workflow + lock guards (no new dependency)
- [x] `tests/test_release_metadata.py` — ENG-03 README marker/changelog/publish-workflow guards
- [x] `tests/test_hygiene.py` — ENG-04 deletion and config guards
- [x] `tests/test_windows_smoke_script.py` — ENG-02 message-matcher tests (imported via `importlib.util`)
- [x] Deleted `tests/unit/test_search.py`, `tests/unit/database/test_migrations.py`, `tests/factories.py` with the module deletions (suite collects: 1670 tests)
- [x] Framework install: none — pytest/pytest-cov are already locked dev deps

---

## Manual-Only Verifications

All six items were **executed** on 2026-11-14; evidence is recorded in `17-04-SUMMARY.md`, `17-06-SUMMARY.md`, and `17-07-SUMMARY.md`.

| Behavior | Requirement | Why Manual | Test Instructions | Verified |
|----------|-------------|------------|-------------------|----------|
| PyPI trusted publisher registered for existing `docsif` project | ENG-03 | Maintainer-only PyPI UI/account action; cannot be automated from the repo | PyPI → project `docsif` → **Settings → Publishing** (`https://pypi.org/manage/project/docsif/settings/publishing/`) → publisher with owner `zhangtaolab`, repository `SIF`, workflow `publish.yml`, environment `pypi`; proof is a successful tagged publish | ✅ Publish run `43562577065` attempt 4, `publish-pypi` success |
| TestPyPI pending publisher registered | ENG-03 | TestPyPI has no `docsif` project (404); maintainer account action | `https://test.pypi.org/manage/account/publishing/` → pending publisher project `docsif`, repository `zhangtaolab/SIF`, workflow `publish.yml`, environment `testpypi`; first tag publish creates the project | ✅ Same run, `publish-testpypi` success |
| GitHub environments `pypi` / `testpypi` exist | ENG-03 | Repo settings action | `gh api -X PUT repos/zhangtaolab/sif/environments/<name>` (or UI); names must match the publish jobs | ✅ Created 2026-11-14: `pypi` id `27264851535`, `testpypi` id `27264859642` |
| 8-cell GitHub matrix green on the release commit | ENG-01 | GitHub Actions execution is external | Observe the push run; each cell's pytest output shows the coverage gate passing | ✅ Run `43561542242` on `c819f67`: 8 py cells + lint, all success |
| Windows degradation smoke on hc yoga | ENG-02 | Remote user machine; requires repo sync to the release commit | `hc exec --on yoga --cwd 'D:\Github\SIF' "<smoke script>"` after `git fetch/checkout`; expect flock warning, missing-root warning, detach refusal messages | ✅ 8/8 PASS at `48759e2` (17-04); GBK spinner bug fixed on the same run |
| Build + TestPyPI + PyPI + PEP 740 attestations | ENG-03 | External release pipeline | `uv build`, `uvx twine check dist/*`, tag push, then `uvx pypi-attestations verify pypi --repository https://github.com/zhangtaolab/SIF pypi:docsif-1.1.2-py3-none-any.whl` | ✅ Run `43562577065` attempt 4 (build reused); attestation `OK`; PyPI + TestPyPI installs report `sif, version 1.1.2` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 180s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-11-14 — 8/8 requirement rows covered by automated guards, 53/53 guard tests green, 0 gaps, 0 escalated.

## Validation Audit 2026-11-14

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
