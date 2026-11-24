---
phase: "17"
slug: "engineering-foundation-ci-matrix-hygiene-pypi"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-14"
verified: "2026-11-24"
---

# Phase 17 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Verified by /gsd-secure-phase 17 on 2026-11-14 at HEAD `443b909` (ASVS L1, block_on high).
> Register authored at plan time: all nine PLANs carry STRIDE `<threat_model>` blocks. L1
> grep-depth verification confirmed every mitigation present; `threats_open: 0`.
> Re-verified by /gsd-secure-phase 17 on 2026-11-24 at HEAD `e2b9fd1` (ASVS L1, block_on high)
> against the post-audit CI/packaging tree: six-cell matrix, main-only push CI, torch>=2.11,
> release metadata 1.2.3. All 37 threats re-confirmed; `threats_open: 0`.
> Re-verified again by /gsd-secure-phase 17 on 2026-11-24 at HEAD `def16da` (ASVS L1, block_on high)
> after gap-closure plan 17-10 (`10a9685`, `a321eaa`): the eight-cell matrix and the all-branch push
> trigger are restored, so the six-cell / main-only description above is superseded. All ten PLANs
> carry STRIDE `<threat_model>` blocks; 41 threats re-confirmed; `threats_open: 0`.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Git working tree → import surface | Deleted modules and exports must disappear from the package and from every importer | Source code, import strings |
| Dependency index → `uv.lock` / build | The explicit PyTorch CPU index and lockfile determine exactly which packages the build consumes | Package names, versions, wheel hashes |
| Pull request → CI workflow | Untrusted PR content runs under a GitHub token in the matrix | PR code, workflow token, cache |
| Local orchestrator → hc yoga (Windows) | Remote shell argv on a user machine, with a temporary database | CLI argv, temporary notes, no personal data |
| Tag → build → PyPI | A pushed tag authorizes the artifact that reaches the public index | Wheel/sdist bytes, version identity |
| GitHub OIDC → PyPI/TestPyPI | Short-lived, job-scoped tokens minted per publish job; no long-lived credentials | OIDC claims, no secrets |
| Hand-maintained docs → deleted code | Documentation must not keep describing removed layers | Markdown text |
| Git index → repository | Only intended tracked files remain | Paths, index entries |
| Contributor branch push → Actions runner | Widening the trigger back to `['**']` means every branch push executes repository code in CI; the job must stay read-only and secret-free (17-10) | Branch commits, workflow token, runner capacity |
| Repository workflow file → CI supply chain | The workflow decides which action SHAs and which locked environment run; an unguarded edit could substitute a mutable action or unpinned dependency (17-10) | Workflow YAML, action SHAs, `uv.lock` |
| Guard tests → CI contract | The guards are the only thing preventing silent re-reduction of the matrix; a guard that encodes the wrong shape would bless drift (17-10) | `tests/test_ci_workflows.py`, workflow text |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-17-01 | Tampering | dead-layer deletion (`models/search.py`, `search/strategy.py`, `database/migrations.py`) | medium | mitigate | Modules, package exports, dependent tests, and fixtures deleted atomically in 17-01; `tests/test_hygiene.py` scans for dead import strings; full suite collects 1670 tests. | closed |
| T-17-02 | Repudiation | Makefile divergence after deletion | low | mitigate | `test_makefile_has_no_pre_commit_target` and `test_pre_commit_config_absent`; docs sweep pinned by 17-08. | closed |
| T-17-04 | Tampering | extra index `pytorch-cpu` (dependency confusion) | high | mitigate | `explicit = true` on the index; `[tool.uv.sources] torch` marker-scoped to Linux (`pyproject.toml:94-102`); `test_pyproject_cpu_index_is_explicit`. | closed |
| T-17-05 | Tampering | `uv.lock` integrity | medium | mitigate | Lock committed and regenerated in one commit; `uv lock --check`; guards assert no nvidia/triton/black (`test_lock_has_no_cuda_stack`, `test_lock_has_no_black`). | closed |
| T-17-06 | Supply Chain | floor changes (sentence-transformers, llama-cpp-python, torch) | low | mitigate | Floors are pre-existing locked deps; no first-time install; package-legitimacy audit approved. | closed |
| T-17-07 | Information Disclosure | PR-triggered workflow | high | mitigate | `pull_request` (never `pull_request_target`), workflow-level `contents: read`, no `secrets.`, no `id-token` (`test_matrix_has_least_privilege`); trigger is every branch push plus a bare `pull_request:`, never tags (`test_matrix_push_trigger_covers_all_branches`). | closed |
| T-17-08 | Elevation of Privilege | workflow token | high | mitigate | Least privilege at workflow level; no `write` permission; guards reject `id-token` and credential surfaces. | closed |
| T-17-09 | Tampering | third-party actions (checkout, setup-uv) | medium | mitigate | `setup-uv` pinned to `68559e99…` with a version comment; `test_setup_uv_is_sha_pinned` rejects floating tags. | closed |
| T-17-10 | Tampering | dependency install in CI | medium | mitigate | `uv sync --frozen` consumes the committed lock; `cache-dependency-glob: uv.lock`; per-version cache suffix. | closed |
| T-17-11 | Elevation of Privilege | hc exec on yoga | high | mitigate | `make windows-smoke` pins host `yoga`, cwd `D:\Github\SIF`, and fixed argv; no user input; script refuses a dirty tree. | closed |
| T-17-12 | Tampering | smoke deleting or mutating user data | high | mitigate | Every `sif` invocation uses `SIF_DB_PATH` inside `tempfile.TemporaryDirectory`; only the temp docs dir is removed; missing-root assertion proves documents survive. | closed |
| T-17-13 | Information Disclosure | smoke output | low | mitigate | Script prints CLI output and HEAD SHA only; no env values, tokens, or document content. | closed |
| T-17-14 | Denial of Service | model download / long command on user machine | medium | mitigate | BM25-only commands, no query/vsearch/embed; `timeout=120` on every call; no HuggingFace cache interaction. | closed |
| T-17-15 | Spoofing | PyPI package/version identity | high | mitigate | `name = "docsif"` fixed; build job requires `v${_version.py}` == `GITHUB_REF_NAME`; `test_publish_workflow_version_gate` and `test_version_literal_is_single_sourced`. | closed |
| T-17-16 | Tampering | artifact between build and publish | high | mitigate | Build once; `upload-artifact@v7` (`if-no-files-found: error`); both publish jobs `download-artifact@v8`; no rebuild (`test_publish_workflow_uses_artifact_handoff`). | closed |
| T-17-17 | Elevation of Privilege | OIDC token scope | high | mitigate | Workflow-level `contents: read`; `id-token: write` job-scoped to the two publish jobs; environments `pypi`/`testpypi`; no secrets (`test_publish_workflow_scopes_id_token`, `test_publish_workflow_has_no_secrets`). | closed |
| T-17-18 | Repudiation | absent provenance | medium | mitigate | Trusted-publishing attestations enabled; verified by `pypi-attestations` → `OK: docsif-1.1.2-py3-none-any.whl` (17-07). | closed |
| T-17-19 | Spoofing | TestPyPI vs PyPI confusion | medium | mitigate | Separate jobs, environments, and repository URLs; `skip-existing` is TestPyPI-only; `test_publish_workflow_orders_testpypi_first`. | closed |
| T-17-20 | Spoofing | trusted-publisher identity mismatch | high | mitigate | Exact publisher fields required (owner `zhangtaolab`, repository `SIF` canonical case, workflow `publish.yml`, environments `pypi`/`testpypi`); proven end-to-end by Publish run `43562577065` attempt 4, where both OIDC mints succeeded. | closed |
| T-17-21 | Elevation of Privilege | environment token minting scope | medium | accept | D-15 locks tag-as-release-intent, so no required reviewers; the environment still restricts which workflow may mint. Residual risk: anyone with repository write access can push a `v*` tag and release; controlled by repository write access. | closed |
| T-17-22 | Tampering | tagging an unverified or drifted commit | high | mitigate | Pre-tag gate: Test Matrix run `43561542242` green on release HEAD `c819f67` (8 py cells + lint); `src/sif` diff since smoke `48759e2` is exactly `_version.py`; tag pushed only after the gate. | closed |
| T-17-23 | Tampering | published wheel bytes | high | mitigate | Build-once workflow; same artifact id `14100657070` reused from attempt 1 through the successful publish; PEP 740 attestation verified against `https://github.com/zhangtaolab/SIF`. | closed |
| T-17-24 | Spoofing | install-resolution confusion | medium | mitigate | Install proofs pin `docsif==1.1.2` and use official indexes; TestPyPI leg adds the PyPI extra index; scratch venvs only. | closed |
| T-17-25 | Repudiation | unattested or mislabeled release | medium | mitigate | PyPI JSON `info.version == 1.1.2` plus the exact `mcp-name` marker; attestation verification `OK`; both are required and both passed. | closed |
| T-17-26 | Denial of Service | immutable version consumed by a failed partial upload | medium | accept | PyPI immutability means a partial failure needs a new patch version; the one-way decision is documented instead of attempting an artifact mutation. | closed |
| T-17-27 | Tampering | hand-edited documentation diverging from deleted code | medium | mitigate | Literal absence scans in `tests/test_hygiene.py` over `docs/**` plus `DESIGN.md`; docs code-block tests stay green (`test_docs_do_not_describe_dead_layers`). | closed |
| T-17-28 | Repudiation | over-deletion of live guidance or the bandit marker | low | mitigate | Guards assert live `SearchOptions` docs survive and exactly one bandit VERIFY marker remains (`test_bandit_verify_marker_retained`, `test_docs_do_not_mention_pre_commit_target`). | closed |
| T-17-29 | Tampering | tracked junk removal | low | mitigate | `git rm` of only the seven verified paths; `test_tracked_junk_removed` asserts absence and no `MagicMock/` prefix. | closed |
| T-17-SC-01 | Tampering | npm/pip/cargo installs (17-01) | high | mitigate | No package installed/added/removed; `uv.lock` untouched in that plan; no new install subject. | closed |
| T-17-SC-02 | Tampering | npm/pip/cargo installs (17-02) | high | mitigate | No new package names; only floors and a direct torch declaration; package-legitimacy gate not triggered. | closed |
| T-17-SC-03 | Tampering | npm/pip/cargo installs (17-03) | high | mitigate | CI installs only from the committed lock; no step names a package directly. | closed |
| T-17-SC-04 | Tampering | npm/pip/cargo installs (17-04) | high | mitigate | Yoga sync uses the committed frozen lock; no new package; dev extra pre-existing. | closed |
| T-17-SC-05 | Tampering | npm/pip/cargo installs (17-05) | high | mitigate | No new package; `uvx twine` / `uvx pypi-attestations` are ephemeral tools, not project dependencies. | closed |
| T-17-SC-06 | Tampering | npm/pip/cargo installs (17-06) | high | mitigate | No package install; the gate reads CI state and git only. | closed |
| T-17-SC-07 | Tampering | npm/pip/cargo installs (17-07) | high | mitigate | Test installs use official indexes with a pinned version; no package added to the project. | closed |
| T-17-SC-08 | Tampering | npm/pip/cargo installs (17-08) | high | mitigate | No package install/add/removal; only markdown and test text change. | closed |
| T-17-SC-09 | Tampering | npm/pip/cargo installs (17-09) | high | mitigate | No package install/add/removal; no dependency or lockfile change. | closed |
| T-17-30 | Denial of Service | restored 8-cell matrix on every branch push and every pull request (`.github/workflows/test-matrix.yml`) | medium | accept | Accepted risk AR-17-03: the restore re-exposes both causes recorded for the `14d7d245` reduction (hosted macOS arm64 capacity cancellations on PRs; a feature-branch commit with an open PR running the matrix twice); `cancel-in-progress: true` bounds neither. No new secrets, write permissions, or OIDC surface. Failure path recorded in AR-17-03. | closed |
| T-17-31 | Tampering | workflow configuration integrity (`test-matrix.yml`, `tests/test_ci_workflows.py`) | high | mitigate | Workflow byte-identical to `14d7d245^` (`git diff --quiet` exit 0, 74 lines); untouched-module gate: the 303 lines outside the two rewritten guard slots and the freed constant block are byte-identical to plan base `ae1225e`; base-anchored scope gate: exactly the five declared files changed; `publish.yml`, `pyproject.toml`, `uv.lock`, and `src/` untouched. Surviving guards pin `fail-fast: false`, `cancel-in-progress: true`, `contents: read`, the `setup-uv` SHA, and `uv sync --frozen`, and reject `--no-cov`, `secrets.`, and `id-token`. No `git revert`. | closed |
| T-17-32 | Repudiation | guard-test truthfulness in `tests/test_ci_workflows.py` | medium | mitigate | `test_matrix_declares_eight_cells` derives the 2 x 4 product from the declared axis lists and rejects `exclude`, `include`, `if`, and `continue-on-error` in the `test` job; `test_matrix_push_trigger_covers_all_branches` pins the exact `on:` / `push:` / `branches: ['**']` lines, a bare `pull_request:`, and no `tags:`. Rejection re-observed at HEAD `def16da`: both guards fail on their own `AssertionError` against `14d7d245:.github/workflows/test-matrix.yml`. The guards are literal-text checks and not exhaustive: see the 2026-11-24 re-audit notes at `def16da`. | closed |
| T-17-SC-10 | Tampering | npm/pip/cargo installs (17-10) | high | mitigate | No package installed, added, or removed; `uv.lock` and `pyproject.toml` are byte-identical to plan base `ae1225e`; no dependency manifest changed. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above `workflow.security_block_on` count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-17-01 | T-17-21 | D-15 treats a pushed tag as the release intent, so the `pypi`/`testpypi` environments carry no required reviewers or wait timer. Residual: repository write access is the release capability. | Maintainer (D-15) | 2026-11-14 |
| AR-17-02 | T-17-26 | PyPI versions are immutable; a partial upload failure consumes the version and requires a new patch release. The plan documents the one-way decision rather than mutating artifacts. | Maintainer (D-13/D-14) | 2026-11-14 |
| AR-17-03 | T-17-30 | Plan 17-10 restored the 8-cell matrix on every branch push and every pull request, reversing the `14d7d245` reduction (quick task 261118-lmm) and bringing back both causes it recorded: (1) hosted macOS arm64 runner capacity repeatedly cancelled PR jobs (in the v1.2.1 PR two attempts lost the py3.10 and py3.13 macOS cells before a third passed); (2) with both triggers on the all-branch form, a feature-branch commit with an open pull request fires a `push` event and a `pull_request` event on different refs and runs the full matrix twice. `cancel-in-progress: true` bounds neither cause: it discards only superseded runs on the same ref, and a capacity cancellation is runner supply. Accepted because the operator chose restore over amending D-01, whose text already accepts the 8 x ~5 min cost and forbids a PR-vs-push split. Residual: no GitHub Actions run exists yet for the restored shape (`17-VALIDATION.md`, Manual-Only row 7). Failure path: re-run a capacity-cancelled cell once; a recurring cancellation goes back to a new recorded decision that reverses workflow, guards, and docs together with the recurrence evidence, never a silent shrink; a red cell is fixed forward without dropping the cell, adding `--no-cov`, or lowering `fail_under`. | Maintainer (D-01; operator choice recorded in 17-10-PLAN.md) | 2026-11-24 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-14 | 37 | 37 | 0 | Claude (gsd-secure-phase, ASVS L1, block_on high) |
| 2026-11-24 | 37 | 37 | 0 | Claude (gsd-secure-phase, ASVS L1, block_on high) |
| 2026-11-24 | 41 | 41 | 0 | ZCode (gsd-secure-phase, ASVS L1, block_on high; auditor run inline; after plan 17-10, HEAD `def16da`) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-14 — 37/37 threats closed at L1; 0 open at or above `high`.

## Security Audit 2026-11-18

| Metric | Count |
|---|---|
| Threats found | 37 |
| Closed | 37 |
| Open | 0 |

## Security Audit 2026-11-24

| Metric | Count |
|---|---|
| Threats found | 37 |
| Closed | 37 |
| Open | 0 |

### Re-audit notes (2026-11-24, HEAD `e2b9fd1`)

- **Scope:** re-verified the 37 registered threats against the post-2026-11-14 tree after the
  CI/packaging changes (six-cell matrix, main-only push CI, torch>=2.11, release metadata 1.2.3).
  Verification depth L1 (grep-level), `block_on: high`, ASVS level 1.
- **Result:** 37/37 closed, 0 open. No threat changed status. 17-07's `## Threat Flags` remains
  "None", and 21/26 remain documented accepted risks (AR-17-01, AR-17-02).
- **Post-audit changes judged:** none widens a registered threat. The matrix reduction narrows
  test coverage (macOS 3.11/3.12 dropped) but adds no attack surface, and the release-process
  gate in `docs/development.md` now names the six cells. Main-only push CI still runs on
  `pull_request` for feature branches and on `main`; the matrix still never triggers on tags
  (`test_matrix_push_trigger_is_main_only`). The torch floor (`>=2.11`) resolves from the
  explicit CPU index with no nvidia/triton/black in `uv.lock`. The version literal is
  single-sourced at `1.2.3` and its guards were updated in lockstep.
- **Evidence refresh:** `pyproject.toml:90-96` -> `pyproject.toml:94-102`;
  `test_matrix_excludes_tag_pushes` -> `test_matrix_push_trigger_is_main_only`. All other
  citations still resolve.
- **Tests:** targeted suites (ci_workflows, release_metadata, hygiene, version_identity,
  windows_smoke_script, docs) 79 passed; full `pytest` 3260 passed, 1 skipped, 95.12% coverage;
  `uv lock --check` resolved 106 packages.

## Security Audit 2026-11-24

| Metric | Count |
|---|---|
| Threats found | 41 |
| Closed | 41 |
| Open | 0 |

### Re-audit notes (2026-11-24, HEAD `def16da`)

- **Scope:** re-verified the registered threats against the tree after gap-closure plan 17-10
  (commits `10a9685`, `a321eaa`; summary `49454bf`). Verification depth L1 (grep-level),
  `block_on: high`, ASVS level 1. The register is still authored at plan time: all ten PLANs
  carry STRIDE `<threat_model>` blocks.
- **Supersedes the six-cell / main-only statements above.** The post-2026-11-14 reduction
  (`14d7d245`, quick task 261118-lmm) is reversed. `.github/workflows/test-matrix.yml` is again
  byte-identical to its `14d7d245^` body: 8 cells (py3.10-3.13 x ubuntu-latest/macos-latest),
  `push: branches: ['**']` plus a bare `pull_request:`, no tag trigger. The header paragraph and
  the 2026-11-24 notes written at `e2b9fd1` are left as written, as the record of that audit.
- **Result:** 41/41 closed, 0 open. Four rows added from plan 17-10. No existing row changed
  status or ID. T-17-30 (`accept`, medium) closes as documented accepted risk AR-17-03.
  T-17-31, T-17-32, and T-17-SC-10 (`mitigate`) were verified against the tests and workflow.
- **T-17-31 evidence:** `git diff --quiet 14d7d245^ -- .github/workflows/test-matrix.yml` exit 0
  (74 lines). Untouched-module gate exit 0: the 303 remainder lines carry the same SHA-256 on
  both sides. Base-anchored scope gate: the changed set since plan base `ae1225e` is exactly
  `.github/workflows/test-matrix.yml`, `tests/test_ci_workflows.py`, `docs/development.md`,
  `docs/contributing.md`, and `docs/testing.md`. `f665eee1`, `848e6b6a`, and `0cdd69de` are
  ancestors of HEAD and their lines survive (`tests/test_ci_workflows.py:139` and `:172`,
  `docs/development.md:626`).
- **T-17-32 evidence and limit:** reproduced in a scratch copy at HEAD. Against
  `14d7d245:.github/workflows/test-matrix.yml` both rewritten guards fail on their own
  `AssertionError` (`2 failed, 4 passed`): the eight-cell guard on its skip-entry assertion, the
  trigger guard on its all-branch regex. Against HEAD they pass. The guards are literal-text
  checks and are **not exhaustive**. Seven nested-filter shapes pass all six workflow-reading
  guards: `paths`, `paths-ignore`, and `branches-ignore` under `push:`, and `branches: [main]`,
  `paths`, `paths-ignore`, and `types` under `pull_request:` (the open gap in
  `17-VALIDATION.md`, Manual-Only row 8). Four more shapes also pass and are not tracked there:
  an option appended to the pytest step (`--collect-only -q`), a job-level
  `permissions: contents: write` on the `test` job, and `if: false` or `continue-on-error: true`
  on the `lint` job. The guards therefore reject the recorded reduction shapes but do not
  prevent every silent narrowing of CI. The workflow text at HEAD is correct and contains none
  of these shapes. Whether to add a follow-up guard is an open maintainer decision; the
  `test_matrix_triggers_are_unfiltered` sketched in row 8 targets the seven trigger shapes only,
  not the four listed after them.
- **Rows touched by the stale references:** T-17-07 now cites
  `test_matrix_push_trigger_covers_all_branches`; the deleted guard is no longer named in the
  register. T-17-08's "no `write` permission" is true of the workflow at HEAD and is not pinned
  by a guard, which asserts only that `contents: read` is present.
- **Threat flags:** 17-07's `## Threat Flags` remains "None". `17-10-SUMMARY.md` has no
  `## Threat Flags` heading; its Threat Model Disposition section records none. No unregistered
  flag.
- **Evidence refresh:** `test_matrix_push_trigger_is_main_only` ->
  `test_matrix_push_trigger_covers_all_branches` (`tests/test_ci_workflows.py:284`);
  `test_matrix_declares_eight_cells` at `tests/test_ci_workflows.py:190`. `pyproject.toml:94-102`
  still resolves. The "1670 tests" in T-17-01's row is the 2026-11-14 collection count; HEAD
  collects 3261 (3260 passed, 1 skipped).
- **Tests (HEAD `def16da`, `pytest` 9.1.1 from PATH):** `pytest tests/test_ci_workflows.py`
  18 passed; phase guard battery 67 passed; `make test` 3260 passed, 1 skipped, 95.12% coverage
  in 204.71s; `ruff check src tests` clean; `ruff format --check src tests` 237 files already
  formatted; `uv lock --check` resolved 106 packages. NOT run: the restored workflow on GitHub
  Actions. Nothing was pushed in this audit and no run exists yet for the eight-cell shape.
- **Method:** the auditor ran inline from `gsd-security-auditor.md` because this runtime has no
  Agent tool. Implementation files were read-only; no source, workflow, or test was modified.
