---
phase: "17"
slug: "engineering-foundation-ci-matrix-hygiene-pypi"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-14"
verified: "2026-11-14"
---

# Phase 17 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Verified by /gsd-secure-phase 17 on 2026-11-14 at HEAD `443b909` (ASVS L1, block_on high).
> Register authored at plan time: all nine PLANs carry STRIDE `<threat_model>` blocks. L1
> grep-depth verification confirmed every mitigation present; `threats_open: 0`.

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

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-17-01 | Tampering | dead-layer deletion (`models/search.py`, `search/strategy.py`, `database/migrations.py`) | medium | mitigate | Modules, package exports, dependent tests, and fixtures deleted atomically in 17-01; `tests/test_hygiene.py` scans for dead import strings; full suite collects 1670 tests. | closed |
| T-17-02 | Repudiation | Makefile divergence after deletion | low | mitigate | `test_makefile_has_no_pre_commit_target` and `test_pre_commit_config_absent`; docs sweep pinned by 17-08. | closed |
| T-17-04 | Tampering | extra index `pytorch-cpu` (dependency confusion) | high | mitigate | `explicit = true` on the index; `[tool.uv.sources] torch` marker-scoped to Linux (`pyproject.toml:90-96`); `test_pyproject_cpu_index_is_explicit`. | closed |
| T-17-05 | Tampering | `uv.lock` integrity | medium | mitigate | Lock committed and regenerated in one commit; `uv lock --check`; guards assert no nvidia/triton/black (`test_lock_has_no_cuda_stack`, `test_lock_has_no_black`). | closed |
| T-17-06 | Supply Chain | floor changes (sentence-transformers, llama-cpp-python, torch) | low | mitigate | Floors are pre-existing locked deps; no first-time install; package-legitimacy audit approved. | closed |
| T-17-07 | Information Disclosure | PR-triggered workflow | high | mitigate | `pull_request` (never `pull_request_target`), workflow-level `contents: read`, no `secrets.`, no `id-token` (`test_matrix_has_least_privilege`, `test_matrix_excludes_tag_pushes`). | closed |
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

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above `workflow.security_block_on` count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-17-01 | T-17-21 | D-15 treats a pushed tag as the release intent, so the `pypi`/`testpypi` environments carry no required reviewers or wait timer. Residual: repository write access is the release capability. | Maintainer (D-15) | 2026-11-14 |
| AR-17-02 | T-17-26 | PyPI versions are immutable; a partial upload failure consumes the version and requires a new patch release. The plan documents the one-way decision rather than mutating artifacts. | Maintainer (D-13/D-14) | 2026-11-14 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-14 | 37 | 37 | 0 | Claude (gsd-secure-phase, ASVS L1, block_on high) |

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
