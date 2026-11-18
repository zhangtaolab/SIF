---
phase: 17-engineering-foundation-ci-matrix-hygiene-pypi
plan: 05
subsystem: release
tags: [pypi, trusted-publishing, oidc, pep740, github-actions, changelog, readme-marker, classifiers, release-docs]

# Dependency graph
requires: ["17-01", "17-02", "17-03", "17-04", "17-08"]
provides:
  - "src/sif/_version.py single literal 1.1.2; all six runtime surfaces derive it (tests/test_version_identity.py)"
  - "README.md mcp-name ownership marker, baked into the docsif-1.1.2 wheel METADATA at build time"
  - "docs/changelog.md 1.1.2 section with v1.1.2 compare link and release footer link"
  - ".github/workflows/publish.yml: v* tag -> build once -> TestPyPI -> PyPI, trusted publishing with job-scoped id-token"
  - "tests/test_release_metadata.py: 13 release metadata/workflow guards (4 identity + 9 workflow/docs)"
  - "Programming Language :: Python :: 3.13 classifier, added only on green matrix run 43399300651"
  - "docs/development.md Release Process rewritten around the automated pipeline; docs/installation.md 1.1.2 sample plus Windows degradation smoke note"
affects: [17-06, 17-07, 17-09, 22]

# Actuals (#2632)
actuals:
  tokens: 4041
  tasks: 3
  commits: 3
  plan_head_before: 9bd9e127596ccb171d1ef522742d8a28fbd3c545
  plan_head_after: 9164e4f40453daeec2fc736740d7655b659e8755

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Workflow text guard: split the YAML into top-level blocks and per-job blocks with string operations, then assert permissions/commands inside the exact job that owns them (no PyYAML)"
    - "Build-once publish: one build job uploads the dist artifact; both publish jobs download the same bytes; TestPyPI first with skip-existing, PyPI never skips"
    - "Tag gate: build job compares v + the _version.py literal to GITHUB_REF_NAME with exact string equality before uv build"

key-files:
  created:
    - tests/test_release_metadata.py
    - .github/workflows/publish.yml
  modified:
    - src/sif/_version.py
    - README.md
    - docs/changelog.md
    - pyproject.toml
    - docs/development.md
    - docs/installation.md

key-decisions:
  - "Kept src/sif/_version.py as the only version literal; the build-job gate requires exact ASCII equality of `v` + literal to GITHUB_REF_NAME, so pre-release suffixes, leading zeros, or whitespace fail before building"
  - "Placed the mcp-name marker on its own README line immediately after the generated-by comment and verified it is baked into the wheel METADATA before any tag exists"
  - "TestPyPI is the only index with skip-existing: true; both publish jobs are job-scoped id-token: write with environments testpypi/pypi; the build job has no id-token and no secrets are referenced"
  - "Added the 3.13 classifier only after `gh run view 43399300651 --exit-status` returned 0 (8 py cells + lint job green)"
  - "Removed the literal `twine upload` path from the release guide rather than describing it as unused, so the guard forbidding it as a release step is unambiguous"

patterns-established:
  - "Release guards stay dependency-free: pathlib/runpy reads plus a minimal job-block splitter, following tests/test_version_identity.py"
  - "Release docs describe the automated pipeline end to end: bump, changelog, windows-smoke, green matrix, annotated tag, trusted publish, attestation + JSON + scratch-venv verification"

requirements-completed: [ENG-01, ENG-02, ENG-03, ENG-04]

coverage:
  - id: D1
    description: "Release identity: 1.1.2 is the single version literal, every runtime surface derives it, README carries the exact mcp-name marker line, and the changelog has the 1.1.2 section with compare/release links"
    requirement: ENG-03
    verification:
      - kind: unit
        ref: "tests/test_release_metadata.py#test_readme_has_mcp_name_marker"
        status: pass
      - kind: unit
        ref: "tests/test_release_metadata.py#test_changelog_has_1_1_2"
        status: pass
      - kind: unit
        ref: "tests/test_release_metadata.py#test_version_literal_is_1_1_2"
        status: pass
      - kind: unit
        ref: "tests/test_version_identity.py (5 tests: runtime surfaces agree on 1.1.2)"
        status: pass
      - kind: integration
        ref: "uv build + wheel METADATA: Version: 1.1.2 and the mcp-name marker line present"
        status: pass
    human_judgment: false
  - id: D2
    description: "Tag-gated build-once publish workflow: v* only, workflow contents: read, build gates GITHUB_REF_NAME against _version.py, uploads dist, then job-scoped OIDC publish jobs for TestPyPI and PyPI"
    requirement: ENG-03
    verification:
      - kind: unit
        ref: "tests/test_release_metadata.py#test_publish_workflow_is_tag_gated"
        status: pass
      - kind: unit
        ref: "tests/test_release_metadata.py#test_publish_workflow_scopes_id_token"
        status: pass
      - kind: unit
        ref: "tests/test_release_metadata.py#test_publish_workflow_uses_artifact_handoff"
        status: pass
      - kind: unit
        ref: "tests/test_release_metadata.py#test_publish_workflow_orders_testpypi_first"
        status: pass
      - kind: unit
        ref: "tests/test_release_metadata.py#test_publish_workflow_version_gate"
        status: pass
      - kind: unit
        ref: "tests/test_release_metadata.py#test_publish_workflow_has_no_secrets"
        status: pass
      - kind: integration
        ref: "uv build --out-dir /tmp/sif-dist-check + uvx twine check: docsif-1.1.2 wheel and sdist PASSED"
        status: pass
    human_judgment: false
  - id: D3
    description: "Python 3.13 classifier declared after 3.12, justified by the recorded green 8-cell matrix run"
    requirement: ENG-01
    verification:
      - kind: unit
        ref: "tests/test_release_metadata.py#test_3_13_classifier_present"
        status: pass
      - kind: e2e
        ref: "gh run view 43399300651 --exit-status (8 py3.10-3.13 ubuntu/macos cells + lint green)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Release docs rewritten around the tag-triggered Publish workflow with attestation verification, no twine upload path, and make windows-smoke documented as the pre-release Windows step"
    requirement: ENG-03
    verification:
      - kind: unit
        ref: "tests/test_release_metadata.py#test_release_process_docs_name_the_workflow"
        status: pass
      - kind: unit
        ref: "tests/test_release_metadata.py#test_windows_smoke_is_documented"
        status: pass
      - kind: unit
        ref: "tests/test_docs.py (13 passed)"
        status: pass
    human_judgment: false

# Metrics
duration: 7min
completed: 2026-11-14
status: complete
---

# Phase 17 Plan 05: Release Artifacts + Publish Workflow Summary

**1.1.2 is single-sourced end-to-end (literal -> runtime surfaces -> README mcp-name marker -> changelog -> changelog links), a tag-triggered build-once workflow publishes to TestPyPI then PyPI via job-scoped OIDC, and the 3.13 classifier landed only on green matrix run 43399300651.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-11-14T01:42:28Z
- **Completed:** 2026-11-14T01:49:22Z
- **Tasks:** 3/3
- **Files modified:** 8 (2 created, 6 modified)

## Accomplishments

- Bumped `src/sif/_version.py` to the single literal `1.1.2`; the existing `tests/test_version_identity.py` proves every runtime surface (`sif.__version__`, `sif.cli.__version__`, `APP_VERSION`, MCP `serverInfo`) derives it.
- Inserted `<!-- mcp-name: io.github.zhangtaolab/sif -->` on its own README line and confirmed the built `docsif-1.1.2` wheel METADATA contains it (`Version: 1.1.2` plus the marker), so the PyPI description will carry Registry ownership from the first publish.
- Added the 1.1.2 changelog section, updated `[Unreleased]` to `compare/v1.1.2...HEAD`, and added the `[1.1.2]` release link.
- Created `.github/workflows/publish.yml`: `v*` tag only, workflow-level `contents: read`, a build job (checkout@v7, SHA-pinned setup-uv v10.3.3, tag/version gate, `uv build`, `uvx twine check`, upload-artifact@v7 `dist`), then `publish-testpypi` (TestPyPI legacy URL + skip-existing, environment `testpypi`) and `publish-pypi` (no skip-existing, environment `pypi`), both downloading the same artifact with job-scoped `id-token: write`.
- Created `tests/test_release_metadata.py` with 13 guards: identity/marker/changelog/readme plus job-block-scoped workflow guards (tag gating, id-token scoping, artifact handoff, TestPyPI ordering, version gate, no secrets).
- Added the `Programming Language :: Python :: 3.13` classifier after 3.12, gated on `gh run view 43399300651 --exit-status` returning 0 for all 8 cells plus lint.
- Rewrote `docs/development.md` Release Process (bump, changelog, windows-smoke, green matrix, annotated tag, Publish workflow, attestation/JSON/scratch-venv verification); updated `docs/installation.md` to `sif, version 1.1.2` and added the Windows degradation-smoke note.

## Task Commits

Each task was committed atomically:

1. **Task 1: Release identity end-to-end (tracer)** - `e5d836d` (feat)
2. **Task 2: Tag-triggered build-once publish workflow** - `c5ab9ce` (feat)
3. **Task 3: Gated 3.13 classifier and release-doc rewrite** - `9164e4f` (feat)

**Plan metadata:** committed separately after this summary (docs: complete 17-05 plan)

## Verification Evidence

- `pytest tests/test_release_metadata.py tests/test_version_identity.py -x -q --no-cov`: 17 passed.
- `pytest tests/test_docs.py -x -q --no-cov`: 13 passed.
- Full suite `env -u FORCE_COLOR NO_COLOR=1 pytest`: **1668 passed, 1 skipped, 95.07% coverage** (`fail_under=90` reached).
- `ruff check src tests scripts` and `ruff format --check src tests scripts`: green; `ty check src/sif`: green.
- `uv build --out-dir /tmp/sif-dist-check`: `docsif-1.1.2.tar.gz` + `docsif-1.1.2-py3-none-any.whl`; `uvx twine check` PASSED for both; wheel METADATA line 60 contains the mcp-name marker.
- `uv lock --check`: resolved 89 packages (classifier-only pyproject change leaves the lock valid).
- Task 3 precondition: `gh run view 43399300651 --exit-status` exited 0 — lint plus py3.10/3.11/3.12/3.13 on ubuntu-latest and macos-latest all successful, the recorded evidence from 17-03.

## Files Created/Modified

- `tests/test_release_metadata.py` — NEW: 13 release metadata and publish-workflow guards.
- `.github/workflows/publish.yml` — NEW: tag-gated build -> TestPyPI -> PyPI trusted-publishing workflow.
- `src/sif/_version.py` — version literal 1.1.2.
- `README.md` — mcp-name Registry ownership marker line.
- `docs/changelog.md` — 1.1.2 section plus v1.1.2 compare/release footer links.
- `pyproject.toml` — Python 3.13 classifier.
- `docs/development.md` — Release Process rewritten around the automated pipeline.
- `docs/installation.md` — 1.1.2 version sample and Windows degradation-smoke note.

## Decisions Made

- Kept `_version.py` as the sole version literal; the build-job gate uses exact `test "v${VERSION}" = "${GITHUB_REF_NAME}"`, deliberately rejecting pre-release suffixes, leading zeros, and whitespace drift.
- Verified the marker at build time (wheel METADATA) rather than trusting the source file, because hatchling bakes the README into the description when the tagged tree is built.
- Scoped `id-token: write` per publish job and kept the workflow level at `contents: read`, matching T-17-17; the guard asserts the build job has none and that no `secrets.` reference exists.
- Used TestPyPI `skip-existing: true` only; PyPI must fail loudly on duplicate files (T-17-19).
- Confirmed the matrix run id from 17-03 before touching the classifier, satisfying the plan's precondition instead of inferring green from local tests.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The first run of `test_release_process_docs_name_the_workflow` failed because the rewritten Step 6 said "There is no `twine upload` step", and the guard forbids the literal phrase anywhere in the release docs. Reworded the step to "There is no manual upload step and no API token" before committing Task 3; no test was weakened and no extra file changed.

## User Setup Required

None at this plan level. The still-manual prerequisites belong to plan 17-06: GitHub environments `pypi`/`testpypi`, the PyPI trusted publisher for the existing `docsif` project, and the TestPyPI pending publisher. No secrets or tokens were introduced.

## Next Phase Readiness

- Plan 17-06 can create the environments/publishers and run its pre-tag gate; it can grep `smoke_head: 48759e2c532d01d92a0deef08520a58c41115378` from 17-04's SUMMARY and the green run 43399300651 from 17-03's SUMMARY.
- Tagging `v1.1.2` will build from a tree whose wheel METADATA already carries `Version: 1.1.2` and the mcp-name marker; the only remaining external risk is the manual trusted-publisher registration matching workflow `publish.yml`, repository `zhangtaolab/sif`, and environments `pypi`/`testpypi`.
- ENG-03 is complete at the artifact/workflow level; the actual upload and attestation verification are plan 17-07's scope.

---
*Phase: 17-engineering-foundation-ci-matrix-hygiene-pypi*
*Completed: 2026-11-14*

## Self-Check: PASSED

- All nine created/modified files exist on disk.
- All three plan commits (`e5d836d`, `c5ab9ce`, `9164e4f`) are ancestors of HEAD.
- The measured commit count from the plan ledger is 3.

