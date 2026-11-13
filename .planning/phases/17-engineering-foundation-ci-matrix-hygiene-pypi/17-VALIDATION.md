---
phase: "17"
slug: "engineering-foundation-ci-matrix-hygiene-pypi"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-13"
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
| **Full suite command** | `env -u FORCE_COLOR NO_COLOR=1 pytest` (1629 tests collected at HEAD `c1d9fb3`) |
| **Estimated runtime** | ~180 s full suite (measure on first wave; quick run ≤ 30 s) |

---

## Sampling Rate

- **After every task commit:** Run `env -u FORCE_COLOR NO_COLOR=1 pytest -x -q --no-cov` plus `ruff check src tests` and `ruff format --check src tests`
- **After every plan wave:** Run `env -u FORCE_COLOR NO_COLOR=1 pytest` + `ty check src/sif` + `uv lock --check`
- **Before `/gsd-verify-work`:** Full suite must be green; the 8-cell GitHub matrix green on the release commit; Windows smoke green on yoga
- **Max feedback latency:** ~180 seconds (full suite); ≤ 30 seconds (quick run)

---

## Per-Task Verification Map

Task IDs are assigned at plan time; requirement-level verification from `17-RESEARCH.md` §Validation Architecture:

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD (plan-time) | TBD | TBD | ENG-01 | T-17-* / — | Workflow uses `pull_request` (not `pull_request_target`), `contents: read`, no secrets in matrix | unit (text-level YAML guard) | `pytest tests/test_ci_workflows.py -x` | ❌ W0 | ⬜ pending |
| TBD (plan-time) | TBD | TBD | ENG-01 | — | Lock resolves CPU torch fleet, no CUDA/nvidia/triton | unit (parse `uv.lock`) | `pytest tests/test_ci_workflows.py::test_lock_has_cpu_torch -x` | ❌ W0 | ⬜ pending |
| TBD (plan-time) | TBD | TBD | ENG-02 | — | Smoke script matchers recognize flock warning, missing-root warning, detach refusal | unit | `pytest tests/test_windows_smoke_script.py -x` | ❌ W0 | ⬜ pending |
| TBD (plan-time) | TBD | TBD | ENG-03 | — | Job-scoped `id-token: write` on publish jobs only; tag↔version gate | unit (existing) | `pytest tests/test_version_identity.py -x` | ✅ existing | ⬜ pending |
| TBD (plan-time) | TBD | TBD | ENG-03 | — | README mcp-name marker present; changelog 1.1.2; publish workflow guards | unit | `pytest tests/test_release_metadata.py -x` | ❌ W0 | ⬜ pending |
| TBD (plan-time) | TBD | TBD | ENG-04 | — | Dead modules not importable; no source/test imports them; `compute_rrf_score` gone | unit | `pytest tests/test_hygiene.py -x` | ❌ W0 | ⬜ pending |
| TBD (plan-time) | TBD | TBD | ENG-04 | — | Makefile has no `pre-commit` target; pyproject no black/`[tool.black]`; extras floors correct; junk paths absent | unit | `pytest tests/test_hygiene.py -x` | ❌ W0 | ⬜ pending |
| TBD (plan-time) | TBD | TBD | ENG-04 | — | Full suite + ruff + ty green after deletion | integration | `make ci` (local) / 8-cell matrix | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_ci_workflows.py` — ENG-01 workflow + lock guards (no new dependency)
- [ ] `tests/test_release_metadata.py` — ENG-03 README marker/changelog/publish-workflow guards
- [ ] `tests/test_hygiene.py` — ENG-04 deletion and config guards
- [ ] `tests/test_windows_smoke_script.py` — ENG-02 message-matcher tests (import the script via `importlib.util` or a small helper)
- [ ] Delete `tests/unit/test_search.py`, `tests/unit/database/test_migrations.py`, `tests/factories.py` in the same plan as the module deletions (suite must collect)
- [ ] Framework install: none — pytest/pytest-cov are already locked dev deps

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| PyPI trusted publisher registered for existing `docsif` project | ENG-03 | Maintainer-only PyPI UI/account action; cannot be automated from the repo | PyPI → project `docsif` → Publishing → add publisher (owner `zhangtaolab`, repo `sif`, workflow `publish.yml`, environment `pypi`); verify by a successful tagged publish |
| TestPyPI pending publisher registered | ENG-03 | TestPyPI has no `docsif` project (404); maintainer account action | TestPyPI → Publishing → pending publisher with the same fields; first tag publish creates the project |
| GitHub environments `pypi` / `testpypi` exist | ENG-03 | Repo settings action; `gh api` shows `total_count: 0` today | `gh api -X PUT repos/zhangtaolab/sif/environments/pypi` and `.../testpypi` (or UI); environment names must match the publish jobs |
| 8-cell GitHub matrix green on the release commit | ENG-01 | GitHub Actions execution is external | Observe the PR/push run; each cell's pytest output shows the coverage gate passing |
| Windows degradation smoke on hc yoga | ENG-02 | Remote user machine; requires repo sync to the release commit | `hc exec --on yoga --cwd 'D:\Github\SIF' "<smoke script>"` after `git fetch/checkout`; expect flock warning, missing-root warning, detach refusal messages |
| Build + TestPyPI + PyPI + PEP 740 attestations | ENG-03 | External release pipeline | `uv build`, `uvx twine check dist/*`, tag push, then `uvx pypi-attestations verify pypi --repository pypi <wheel>` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 180s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
