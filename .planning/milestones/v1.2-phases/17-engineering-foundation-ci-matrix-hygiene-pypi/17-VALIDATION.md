---
phase: "17"
slug: "engineering-foundation-ci-matrix-hygiene-pypi"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-11-13"
validated: "2026-11-24"
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 + pytest-cov 7.1.0 (locked in `uv.lock`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` + `[tool.coverage.report]` (`fail_under = 90`) |
| **Quick run command** | `env -u FORCE_COLOR NO_COLOR=1 pytest -x -q --no-cov` |
| **Full suite command** | `env -u FORCE_COLOR NO_COLOR=1 pytest` (3261 tests collected at HEAD `1e43785`; 3260 passed, 1 skipped, 95.12% coverage) |
| **Estimated runtime** | ~212 s full suite (measured 2026-11-24 at HEAD `1e43785`; 1.75 s for the 58-test guard subset; quick run ≤ 30 s) |

---

## Sampling Rate

- **After every task commit:** Run `env -u FORCE_COLOR NO_COLOR=1 pytest -x -q --no-cov` plus `ruff check src tests` and `ruff format --check src tests`
- **After every plan wave:** Run `env -u FORCE_COLOR NO_COLOR=1 pytest` + `ty check src/sif` + `uv lock --check`
- **Before `/gsd-verify-work`:** Full suite green at HEAD `1e43785` (3260 passed, 1 skipped @ 95.12%); guard subset 58/58 green in 1.75 s; CI Test Matrix run `45311060690` green on main HEAD `d8b1404` (6 py cells + lint)
- **Max feedback latency:** ~212 seconds (full suite); ≤ 30 seconds (quick run)

---

## Per-Task Verification Map

Requirement-level map from `17-RESEARCH.md` §Validation Architecture, re-audited 2026-11-24 against HEAD `1e43785` (the 2026-11-14 audit was taken at HEAD `3348284`):

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 17-03 | 17-03 | 2 | ENG-01 | T-17-* | Workflow is PR-triggered (`pull_request:`, never `pull_request_target`), `contents: read`, no secrets/OIDC in the matrix, push CI on `main` only, no tag trigger | unit (text-level YAML guard) | `pytest tests/test_ci_workflows.py -x` (18 tests) | ✅ | ✅ green |
| 17-02 | 17-02 | 1 | ENG-01 | — | Lock resolves the CPU torch fleet (no CUDA/nvidia/triton); CPU index explicit and marker-scoped to Linux | unit (parse `uv.lock` / `pyproject.toml`) | `pytest tests/test_ci_workflows.py::test_lock_has_cpu_torch -x` | ✅ | ✅ green |
| 17-04 | 17-04 | 2 | ENG-02 | — | Smoke matchers recognize the flock warning, missing-root warning, and detach/service refusal; raw tracebacks rejected; 8 argv steps, model-free; POSIX host refuses | unit | `pytest tests/test_windows_smoke_script.py -x` (8 tests) | ✅ | ✅ green |
| 17-05 | 17-05 | 3 | ENG-03 | — | Job-scoped `id-token: write` on publish jobs only; tag↔version gate; build-once artifact handoff; TestPyPI ordered first | unit (existing) | `pytest tests/test_version_identity.py -x` (4 tests) | ✅ | ✅ green |
| 17-05 | 17-05 | 3 | ENG-03 | — | README mcp-name marker present; changelog carries the current version (1.2.3 at this audit; 1.1.2 at phase close); publish-workflow guards; 3.13 classifier | unit | `pytest tests/test_release_metadata.py -x` (13 tests) | ✅ | ✅ green |
| 17-01 | 17-01 | 1 | ENG-04 | — | Dead modules not importable; no source/test imports them; `compute_rrf_score` and `CURRENT_SCHEMA_VERSION` gone | unit | `pytest tests/test_hygiene.py -x` (15 tests) | ✅ | ✅ green |
| 17-01/17-02/17-09 | 17-01,17-02,17-09 | 1,3 | ENG-04 | — | Makefile has no `pre-commit` target; `.pre-commit-config.yaml` absent; pyproject has no black/`[tool.black]`; extras floors correct (torch>=2.11, sentence-transformers>=5.4.1, llama-cpp-python>=0.3.35); fastapi/uvicorn stay core; junk paths absent | unit | `pytest tests/test_hygiene.py tests/test_ci_workflows.py -x` (33 tests) | ✅ | ✅ green |
| 17-08 | 17-08 | 2 | ENG-04 | — | Hand-maintained docs carry no dead-layer prose and no phantom pre-commit guidance; documented Python blocks parse; nav/installation/model docs consistent | unit | `pytest tests/test_hygiene.py tests/test_docs.py -x` (36 tests) | ✅ | ✅ green |
| 17-01…17-09 | all | 1–5 | ENG-04 | — | Full suite + ruff + ty green after deletion | integration | `ruff check src tests && ruff format --check src tests && ty check src/sif && pytest` (3260 passed, 1 skipped @ 95.12%); CI lint job green on run `45311060690` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Guard inventory (measured 2026-11-24, HEAD `1e43785`):** 58 tests across `test_ci_workflows.py` (18), `test_release_metadata.py` (13), `test_hygiene.py` (15), `test_windows_smoke_script.py` (8), and `test_version_identity.py` (4) — all green in 1.75 s with `--no-cov`. The 2026-11-14 inventory was 53 tests (14/13/15/7/4).

**Re-anchors applied by the 2026-11-24 audit (files moved or changed after the phase closed):**

- `.github/workflows/test-matrix.yml` + `tests/test_ci_workflows.py`: the matrix was deliberately shrunk from 8 to 6 cells (Linux 3.10–3.13; macOS 3.10 and 3.13) and push CI moved to `main` only in `14d7d245` (`quick-261118-lmm`); the guard was retitled `test_matrix_declares_six_cells` and a main-only push guard added. 14 → 18 guards.
- `tests/test_windows_smoke_script.py`: gained `test_main_refuses_on_non_windows` (CR-01) — 7 → 8 tests.
- `tests/test_release_metadata.py`: assertions re-pointed from 1.1.2 to the current literal — `test_changelog_has_1_2_3` / `test_version_literal_is_1_2_3`; still 13 guards.
- `pyproject.toml` + `tests/test_ci_workflows.py`: the embed/all torch floor was lowered `>=2.14` → `>=2.11` in `848e6b6a` (`quick-261119-fww-03`); `test_pyproject_extras_floors` follows the current floor.
- Row 7's automated command now cites `tests/test_ci_workflows.py` as well as `tests/test_hygiene.py`: the extras-floor, black, and fastapi/uvicorn-core guards live in the former, not the latter.
- Row for 17-08 (documentation sweep) added; it was previously only implied by the catch-all row.
- `docs/changelog.md`, `docs/contributing.md`, `docs/development.md`, `docs/installation.md`, `tests/conftest.py`, `tests/test_docs.py`, `tests/unit/cli/test_watch_cmd.py`, `tests/unit/utils/test_daemon.py`, `src/sif/_version.py`, `uv.lock` also changed after close; every guard that reads them is green, and the docs guards pass with the new nav/installation prose (21 `test_docs.py` tests).

---

## Wave 0 Requirements

- [x] `tests/test_ci_workflows.py` — ENG-01 workflow + lock guards (no new dependency)
- [x] `tests/test_release_metadata.py` — ENG-03 README marker/changelog/publish-workflow guards
- [x] `tests/test_hygiene.py` — ENG-04 deletion and config guards
- [x] `tests/test_windows_smoke_script.py` — ENG-02 message-matcher tests (imported via `importlib.util`)
- [x] Deleted `tests/unit/test_search.py`, `tests/unit/database/test_migrations.py`, `tests/factories.py` with the module deletions (suite collects 3261 tests at HEAD `1e43785`; 1670 at phase close)
- [x] Framework install: none — pytest/pytest-cov are already locked dev deps

---

## Manual-Only Verifications

All six items were **executed** on 2026-11-14; evidence is recorded in `17-04-SUMMARY.md`, `17-06-SUMMARY.md`, and `17-07-SUMMARY.md`.

| Behavior | Requirement | Why Manual | Test Instructions | Verified |
|----------|-------------|------------|-------------------|----------|
| PyPI trusted publisher registered for existing `docsif` project | ENG-03 | Maintainer-only PyPI UI/account action; cannot be automated from the repo | PyPI → project `docsif` → **Settings → Publishing** (`https://pypi.org/manage/project/docsif/settings/publishing/`) → publisher with owner `zhangtaolab`, repository `SIF`, workflow `publish.yml`, environment `pypi`; proof is a successful tagged publish | ✅ Publish run `43562577065` attempt 4, `publish-pypi` success |
| TestPyPI pending publisher registered | ENG-03 | TestPyPI has no `docsif` project (404); maintainer account action | `https://test.pypi.org/manage/account/publishing/` → pending publisher project `docsif`, repository `zhangtaolab/SIF`, workflow `publish.yml`, environment `testpypi`; first tag publish creates the project | ✅ Same run, `publish-testpypi` success |
| GitHub environments `pypi` / `testpypi` exist | ENG-03 | Repo settings action | `gh api -X PUT repos/zhangtaolab/sif/environments/<name>` (or UI); names must match the publish jobs | ✅ Created 2026-11-14: `pypi` id `27264851535`, `testpypi` id `27264859642` |
| CI matrix green on the release commit (8 cells at release time; 6 cells now) | ENG-01 | GitHub Actions execution is external | Observe the push/PR run; each cell's pytest output shows the coverage gate passing | ✅ Release: run `43561542242` on `c819f67`, 8 py cells + lint all success. Current matrix: run `45311060690` on `d8b1404`, 6 py cells + lint all success |
| Windows degradation smoke on hc yoga | ENG-02 | Remote user machine; requires repo sync to the release commit | `hc exec --on yoga --cwd 'D:\Github\SIF' "<smoke script>"` after `git fetch/checkout`; expect flock warning, missing-root warning, detach refusal messages | ✅ 8/8 PASS at `48759e2` (17-04); GBK spinner bug fixed on the same run |
| Build + TestPyPI + PyPI + PEP 740 attestations | ENG-03 | External release pipeline | `uv build`, `uvx twine check dist/*`, tag push, then `uvx pypi-attestations verify pypi --repository https://github.com/zhangtaolab/SIF pypi:docsif-1.1.2-py3-none-any.whl` | ✅ Run `43562577065` attempt 4 (build reused); attestation `OK`; PyPI + TestPyPI installs report `sif, version 1.1.2` |

*Note (2026-11-24): the matrix row is retained as the release-time record; the live matrix is now six cells (`14d7d245`) and the guard asserts that shape. The 1.1.2 install/attestation rows are historical — later versions were released the same way.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 180s (quick run ≤ 30 s and the 58-test guard subset 1.75 s; the full suite is ~212 s and runs per wave)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-11-14 — 8/8 requirement rows covered by automated guards, 53/53 guard tests green, 0 gaps, 0 escalated.

**Re-audit 2026-11-24** (state A, HEAD `1e43785`): 9 map rows (17-08 added), 58/58 guard tests green in 1.75 s, full suite 3260 passed / 1 skipped @ 95.12%, 0 gaps, 0 escalated, `nyquist_compliant: true` retained. `ty check src/sif` is green in CI's dev-only resolution (lint job of run `45311060690`); a local run with the `embed` extra installed reports 1 `numpy` return-type diagnostic in `src/sif/embedding/embedder.py`, outside Phase 17's files.

## Validation Audit 2026-11-14

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
