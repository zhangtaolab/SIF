---
phase: "17"
slug: "engineering-foundation-ci-matrix-hygiene-pypi"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: false
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
| **Full suite command** | `env -u FORCE_COLOR NO_COLOR=1 pytest` (3261 tests collected at HEAD `49454bf`; 3260 passed, 1 skipped, 95.12% coverage) |
| **Estimated runtime** | ~198 s full suite with coverage (measured 2026-11-24 at HEAD `49454bf`: 197.96 s; ~122 s for the quick run, which is the whole suite without coverage; ≈1 s for the 58-test guard subset) |

---

## Sampling Rate

- **After every task commit:** Run `env -u FORCE_COLOR NO_COLOR=1 pytest -x -q --no-cov` plus `ruff check src tests` and `ruff format --check src tests`
- **After every plan wave:** Run `env -u FORCE_COLOR NO_COLOR=1 pytest` + `ty check src/sif` + `uv lock --check`
- **Before `/gsd-verify-work`:** Full suite green at HEAD `49454bf` (3260 passed, 1 skipped @ 95.12%); guard subset 58/58 green in ≈1 s; CI Test Matrix — **no run exists yet for the restored 8-cell workflow** (the newest run, `45311060690` on main `d8b1404`, exercised the six-cell shape); see Manual-Only rows 7 and 8
- **Max feedback latency:** ~198 seconds (full suite with coverage); ~122 seconds (quick run)

---

## Per-Task Verification Map

Requirement-level map from `17-RESEARCH.md` §Validation Architecture, re-audited 2026-11-24 against HEAD `49454bf` after gap-closure plan 17-10 (earlier audits: 2026-11-24 at HEAD `1e43785`, 2026-11-14 at HEAD `3348284`):

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 17-03 | 17-03 | 2 | ENG-01 | T-17-* | Workflow is PR-triggered (`pull_request:`, never `pull_request_target`), `contents: read`, no secrets/OIDC in the matrix, push CI on every branch (`push: branches: ['**']`) plus every pull request, no tag trigger | unit (text-level YAML guard) | `pytest tests/test_ci_workflows.py -x` (18 tests) | ✅ | ✅ green |
| 17-10 T1 | 17-10 | 1 | ENG-01 | T-17-30 / T-17-31 / T-17-32 | The `test` job declares the full 8-cell product (py3.10–3.13 × `ubuntu-latest` / `macos-latest`) with no skip entry (`exclude`, `include`, `if`, `continue-on-error`); `push: branches: ['**']` and a bare `pull_request:`, no `tags:`; workflow byte-identical to `14d7d245^`; the reduced-shape guards and `MATRIX_EXCLUSION` are gone | unit (text-level YAML guard) | `pytest tests/test_ci_workflows.py -x` (18 tests, including `test_matrix_declares_eight_cells` and `test_matrix_push_trigger_covers_all_branches`); red-derivation gate (both guards fail on `14d7d245:.github/workflows/test-matrix.yml`); `git diff --quiet 14d7d245^ -- .github/workflows/test-matrix.yml` | ✅ | ✅ green, PARTIAL coverage — filters nested under either trigger are unguarded (Manual-Only row 8) |
| 17-10 T2 | 17-10 | 1 | ENG-01 | — | `docs/development.md`, `docs/contributing.md`, and `docs/testing.md` state eight cells and the every-branch push plus `pull_request` trigger in all thirteen restored statements; no residual six-cell or main-only wording; the `0cdd69de` attestation line survives | unit (text-level doc gates from the plan verify block — not a pytest test) | Task 2 doc gates in `17-10-PLAN.md`: three negative greps over the three docs files (reduced cell count, `push: branches: [main]`, main-only or PR-reliance phrasing); eight-cell counts 4 / 3 / 2; `git diff --quiet e8ab1148^ -- docs/contributing.md docs/testing.md`; battery `pytest tests/test_ci_workflows.py tests/test_docs.py tests/test_hygiene.py tests/test_release_metadata.py -x` (67 tests) | — plan gates | ✅ green (plan gates, re-run at HEAD; no test in the suite pins the docs wording) |
| 17-02 | 17-02 | 1 | ENG-01 | — | Lock resolves the CPU torch fleet (no CUDA/nvidia/triton); CPU index explicit and marker-scoped to Linux | unit (parse `uv.lock` / `pyproject.toml`) | `pytest tests/test_ci_workflows.py::test_lock_has_cpu_torch -x` | ✅ | ✅ green |
| 17-04 | 17-04 | 2 | ENG-02 | — | Smoke matchers recognize the flock warning, missing-root warning, and detach/service refusal; raw tracebacks rejected; 8 argv steps, model-free; POSIX host refuses | unit | `pytest tests/test_windows_smoke_script.py -x` (8 tests) | ✅ | ✅ green |
| 17-05 | 17-05 | 3 | ENG-03 | — | Job-scoped `id-token: write` on publish jobs only; tag↔version gate; build-once artifact handoff; TestPyPI ordered first | unit (existing) | `pytest tests/test_version_identity.py -x` (4 tests) | ✅ | ✅ green |
| 17-05 | 17-05 | 3 | ENG-03 | — | README mcp-name marker present; changelog carries the current version (1.2.3 at this audit; 1.1.2 at phase close); publish-workflow guards; 3.13 classifier | unit | `pytest tests/test_release_metadata.py -x` (13 tests) | ✅ | ✅ green |
| 17-01 | 17-01 | 1 | ENG-04 | — | Dead modules not importable; no source/test imports them; `compute_rrf_score` and `CURRENT_SCHEMA_VERSION` gone | unit | `pytest tests/test_hygiene.py -x` (15 tests) | ✅ | ✅ green |
| 17-01/17-02/17-09 | 17-01,17-02,17-09 | 1,3 | ENG-04 | — | Makefile has no `pre-commit` target; `.pre-commit-config.yaml` absent; pyproject has no black/`[tool.black]`; extras floors correct (torch>=2.11, sentence-transformers>=5.4.1, llama-cpp-python>=0.3.35); fastapi/uvicorn stay core; junk paths absent | unit | `pytest tests/test_hygiene.py tests/test_ci_workflows.py -x` (33 tests) | ✅ | ✅ green |
| 17-08 | 17-08 | 2 | ENG-04 | — | Hand-maintained docs carry no dead-layer prose and no phantom pre-commit guidance; documented Python blocks parse; nav/installation/model docs consistent | unit | `pytest tests/test_hygiene.py tests/test_docs.py -x` (36 tests) | ✅ | ✅ green |
| 17-01…17-10 | all | 1–5 | ENG-04 | — | Full suite + ruff + ty green after deletion | integration | `ruff check src tests && ruff format --check src tests && ty check src/sif && pytest` (3260 passed, 1 skipped @ 95.12%); CI lint job green on run `45311060690` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky. "PARTIAL coverage" means the guard is green but does not detect every way the requirement can be broken (Manual-Only row 8).*

**Guard inventory (measured 2026-11-24, HEAD `49454bf`):** 58 tests across `test_ci_workflows.py` (18), `test_release_metadata.py` (13), `test_hygiene.py` (15), `test_windows_smoke_script.py` (8), and `test_version_identity.py` (4) — all green in ≈1 s with `--no-cov`. The count is unchanged from HEAD `1e43785` (plan 17-10 rewrote two guards in place); the 2026-11-14 inventory was 53 tests (14/13/15/7/4).

**Re-anchors applied by the 2026-11-24 audits (files moved or changed after the phase closed):**

- `.github/workflows/test-matrix.yml` + `tests/test_ci_workflows.py`: the post-phase reduction in `14d7d245` (`quick-261118-lmm`) — six cells, push CI on `main` only — was reversed by gap-closure plan 17-10 (commit `10a9685`). The workflow is again byte-identical to its `14d7d245^` body (8 cells: py3.10–3.13 × `ubuntu-latest` / `macos-latest`; `push: branches: ['**']` plus `pull_request:`), and the two reduced-shape guards were replaced by `test_matrix_declares_eight_cells` (derives the 2 × 4 product and rejects skip entries) and `test_matrix_push_trigger_covers_all_branches`. Still 18 guards.
- `tests/test_windows_smoke_script.py`: gained `test_main_refuses_on_non_windows` (CR-01) — 7 → 8 tests.
- `tests/test_release_metadata.py`: assertions re-pointed from 1.1.2 to the current literal — `test_changelog_has_1_2_3` / `test_version_literal_is_1_2_3`; still 13 guards.
- `pyproject.toml` + `tests/test_ci_workflows.py`: the embed/all torch floor was lowered `>=2.14` → `>=2.11` in `848e6b6a` (`quick-261119-fww-03`); `test_pyproject_extras_floors` follows the current floor.
- The 17-01/17-02/17-09 row's automated command now cites `tests/test_ci_workflows.py` as well as `tests/test_hygiene.py`: the extras-floor, black, and fastapi/uvicorn-core guards live in the former, not the latter.
- Row for 17-08 (documentation sweep) added; it was previously only implied by the catch-all row.
- `docs/changelog.md`, `docs/contributing.md`, `docs/development.md`, `docs/installation.md`, `tests/conftest.py`, `tests/test_docs.py`, `tests/unit/cli/test_watch_cmd.py`, `tests/unit/utils/test_daemon.py`, `src/sif/_version.py`, `uv.lock` also changed after close; every guard that reads them is green, and the docs guards pass with the new nav/installation prose (21 `test_docs.py` tests).

---

## Wave 0 Requirements

- [x] `tests/test_ci_workflows.py` — ENG-01 workflow + lock guards (no new dependency)
- [x] `tests/test_release_metadata.py` — ENG-03 README marker/changelog/publish-workflow guards
- [x] `tests/test_hygiene.py` — ENG-04 deletion and config guards
- [x] `tests/test_windows_smoke_script.py` — ENG-02 message-matcher tests (imported via `importlib.util`)
- [x] Deleted `tests/unit/test_search.py`, `tests/unit/database/test_migrations.py`, `tests/factories.py` with the module deletions (suite collects 3261 tests at HEAD `49454bf`; 1670 at phase close)
- [x] Framework install: none — pytest/pytest-cov are already locked dev deps

---

## Manual-Only Verifications

The six original items were **executed** on 2026-11-14; evidence is recorded in `17-04-SUMMARY.md`, `17-06-SUMMARY.md`, and `17-07-SUMMARY.md`. The re-audit after plan 17-10 (2026-11-24) added rows 7 and 8, which are still open (⬜).

| Behavior | Requirement | Why Manual | Test Instructions | Verified |
|----------|-------------|------------|-------------------|----------|
| PyPI trusted publisher registered for existing `docsif` project | ENG-03 | Maintainer-only PyPI UI/account action; cannot be automated from the repo | PyPI → project `docsif` → **Settings → Publishing** (`https://pypi.org/manage/project/docsif/settings/publishing/`) → publisher with owner `zhangtaolab`, repository `SIF`, workflow `publish.yml`, environment `pypi`; proof is a successful tagged publish | ✅ Publish run `43562577065` attempt 4, `publish-pypi` success |
| TestPyPI pending publisher registered | ENG-03 | TestPyPI has no `docsif` project (404); maintainer account action | `https://test.pypi.org/manage/account/publishing/` → pending publisher project `docsif`, repository `zhangtaolab/SIF`, workflow `publish.yml`, environment `testpypi`; first tag publish creates the project | ✅ Same run, `publish-testpypi` success |
| GitHub environments `pypi` / `testpypi` exist | ENG-03 | Repo settings action | `gh api -X PUT repos/zhangtaolab/sif/environments/<name>` (or UI); names must match the publish jobs | ✅ Created 2026-11-14: `pypi` id `27264851535`, `testpypi` id `27264859642` |
| CI matrix green on the release commit (release-time record, 8 cells) | ENG-01 | GitHub Actions execution is external | Observe the push/PR run; each cell's pytest output shows the coverage gate passing | ✅ Release: run `43561542242` on `c819f67`, 8 py cells + lint all success |
| Windows degradation smoke on hc yoga | ENG-02 | Remote user machine; requires repo sync to the release commit | `hc exec --on yoga --cwd 'D:\Github\SIF' "<smoke script>"` after `git fetch/checkout`; expect flock warning, missing-root warning, detach refusal messages | ✅ 8/8 PASS at `48759e2` (17-04); GBK spinner bug fixed on the same run |
| Build + TestPyPI + PyPI + PEP 740 attestations | ENG-03 | External release pipeline | `uv build`, `uvx twine check dist/*`, tag push, then `uvx pypi-attestations verify pypi --repository https://github.com/zhangtaolab/SIF pypi:docsif-1.1.2-py3-none-any.whl` | ✅ Run `43562577065` attempt 4 (build reused); attestation `OK`; PyPI + TestPyPI installs report `sif, version 1.1.2` |
| Restored 8-cell matrix green on GitHub Actions on a real branch push (the runs-green half of SC1/ENG-01; T-17-30 failure path) | ENG-01 | GitHub Actions execution is external, and `gsd/phase-24-reverify` has not been pushed: it has no Test Matrix run | After the push, open the Test Matrix run and record the run id plus every job conclusion; expect 8 `py<version> / <os>` jobs and the lint job, all successful. A capacity-cancelled cell is re-run once; a recurrence needs a new recorded decision, never a silent shrink; a red cell is fixed forward without dropping the cell or weakening coverage (protocol: `17-10-SUMMARY.md`, Manual Follow-Up) | ⬜ pending — no run exists for the restored workflow; the newest run, `45311060690` on main `d8b1404` (2026-11-24), exercised the six-cell shape |
| Trigger guards reject filters nested under `push:` and `pull_request:` (the every-push/PR clause of ENG-01) | ENG-01 | Open Nyquist gap: this audit may not modify tests, and `17-10-SUMMARY.md` left the scope as a maintainer decision | Add `test_matrix_triggers_are_unfiltered` to `tests/test_ci_workflows.py`: slice the block from `on:` to `permissions:` and assert it equals the four lines `on:`, `push:`, `branches: ['**']`, `pull_request:` exactly; run `pytest tests/test_ci_workflows.py -x`. Checked on a temp copy at HEAD `49454bf`: it passes on the current workflow and rejects all seven nested-filter shapes listed in the last column | ⬜ open — observed at HEAD `49454bf`: `paths`, `paths-ignore`, and `branches-ignore` under `push:`, and `branches: [main]`, `paths`, `paths-ignore`, and `types` under `pull_request:` all pass the six workflow-reading guards |

*Note (2026-11-24, updated after plan 17-10): the matrix row is retained as the release-time record for `c819f67`. The post-phase reduction to six cells (`14d7d245`) was reversed by `10a9685`: the live matrix is eight cells again, the guards assert that shape, and row 7 tracks its first real run. The 1.1.2 install/attestation rows are historical — later versions were released the same way.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 180s (quick run ~122 s and the 58-test guard subset ≈1 s; the full suite with coverage is ~198 s and runs per wave)
- [ ] `nyquist_compliant: true` set in frontmatter — not met by this re-audit: one open gap (Manual-Only row 8) and one pending manual confirmation (row 7) leave it `false`

**Approval:** approved 2026-11-14 — 8/8 requirement rows covered by automated guards, 53/53 guard tests green, 0 gaps, 0 escalated.

**Re-audit 2026-11-24, before plan 17-10** (state A, HEAD `1e43785`): 9 map rows (17-08 added), 58/58 guard tests green in 1.75 s, full suite 3260 passed / 1 skipped @ 95.12%, 0 gaps, 0 escalated, `nyquist_compliant: true` retained. `ty check src/sif` is green in CI's dev-only resolution (lint job of run `45311060690`); a local run with the `embed` extra installed reports 1 `numpy` return-type diagnostic in `src/sif/embedding/embedder.py`, outside Phase 17's files.

**Re-audit 2026-11-24 after plan 17-10** (state A, HEAD `49454bf`; the auditor's work was done inline from `gsd-nyquist-auditor.md` because this runtime has no Agent tool): 11 map rows (17-10 T1 and T2 added; the 17-03 row re-pinned to the every-branch trigger), 58/58 guard tests green in ≈1 s, all 21 verify gates of plan 17-10 re-run green at HEAD (Task 1: 7 of 7, Task 2: 14 of 14), full suite 3260 passed / 1 skipped @ 95.12% in 197.96 s. **1 gap found, 0 resolved, 1 escalated, so `nyquist_compliant` moves from `true` to `false`.** The gap is the trigger guard's partial coverage (Manual-Only row 8). It is a hole in the guard, not a defect in the workflow, which is byte-identical to the body that ran green on 8 cells at `c819f67`. The restored matrix's first GitHub Actions run is still pending (row 7).

Two things are recorded but not counted as gaps. The eight-cell docs wording is held only by the plan's verify gates, so a docs regression would not fail `pytest`. `ty check src/sif` exits 1 locally with 10 third-party typing diagnostics in `embedder.py`, `download.py`, and `rerank.py`; `src/`, `pyproject.toml`, and `uv.lock` are byte-identical to `d8b1404`, where CI's `Type check` step is green. The local runs used `pytest` from PATH (9.1.1, `pytest-cov` 7.0.0, miniconda py3.13.9) rather than the locked 9.0.3 / 7.1.0. The earlier "quick run ≤ 30 s" figure was wrong and is corrected above: the quick run is the whole suite without coverage.

## Validation Audit 2026-11-14

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

## Validation Audit 2026-11-24

| Metric | Count |
|---|---|
| Gaps found | 1 |
| Resolved | 0 |
| Escalated | 1 |
