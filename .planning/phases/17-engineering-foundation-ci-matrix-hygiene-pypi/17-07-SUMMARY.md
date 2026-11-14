---
phase: 17-engineering-foundation-ci-matrix-hygiene-pypi
plan: 07
subsystem: release
tags: [pypi, testpypi, trusted-publishing, oidc, attestations, release, checkpoint, halted]
status: halted

# Dependency graph
requires: ["17-06"]
provides:
  - "Annotated tag v1.1.2 created and pushed on release_head c819f67228152f2544e79a864b9a9e12dbc79f69 — the release intent is live"
  - "Publish run 43562577065: Build distributions success; Publish to TestPyPI failure (invalid-publisher); Publish to PyPI skipped"
  - "Proof that no artifact reached either index: TestPyPI still 404 for docsif, PyPI still serves only 1.0.1 and has no 1.1.2 release"
affects: []

# Actuals (#2632) — partial: plan halted at Task 1's external publisher-config blocker
actuals:
  tokens: 4186
  tasks: 0
  commits: 0
  plan_head_before: b0b4258535d50f552c5957ee5a28bb7999059f97
  plan_head_after: b0b4258535d50f552c5957ee5a28bb7999059f97

tech-stack:
  added: []
  patterns:
    - "A tag push is release intent but not consumption: a trusted-publisher claim mismatch fails at token exchange, before any upload, so the immutable version is still available"
    - "Diagnose invalid-publisher from the OIDC claim dump in the action log; warehouse matches repository_name exactly (case-sensitive) and lowercases only environment names"

key-files:
  created:
    - .planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-07-SUMMARY.md
  modified:
    - .planning/STATE.md
    - .planning/ROADMAP.md

key-decisions:
  - "Tagged exactly release_head c819f67228152f2544e79a864b9a9e12dbc79f69 (never the later metadata commit b0b4258) and verified tag^{commit} equals it"
  - "Halted instead of retrying blindly: the claim dump proves the TestPyPI publisher lookup failed before any upload, and the fix is a browser-only TestPyPI/PyPI publisher edit"
  - "Kept tag v1.1.2 in place; re-running the failed jobs after the publisher fix is safe because TestPyPI uses skip-existing and the PyPI job never ran"
---

# Phase 17 Plan 07: Tag + Publish Checkpoint Summary — HALTED at TestPyPI trusted-publisher mismatch

**Tag `v1.1.2` is pushed on the gate-verified release commit `c819f67228152f2544e79a864b9a9e12dbc79f69`; Publish run `43562577065` built the distributions successfully but the TestPyPI token exchange failed with `invalid-publisher` (no publisher matched the OIDC claims), so the PyPI job was skipped. No file reached either index and version 1.1.2 is NOT consumed; the blocker is a case-sensitive publisher registration mismatch that only the maintainer can fix in the TestPyPI/PyPI UI.**

## Task Status

| Task | Name | Status | Evidence / Blocker |
|------|------|--------|--------------------|
| 1 | Push tag v1.1.2 and drive build -> TestPyPI -> PyPI to success (D-13, D-14, D-15) | Blocked | Tag pushed on `c819f67`; run `43562577065`: build `success`, publish-testpypi `failure` (`invalid-publisher`), publish-pypi `skipped` |
| 2 | Post-publish provenance and install proofs | Not started | Precondition unmet: Task 1 did not publish |

## Task 1 Evidence

### Tag

```text
$ git tag -a v1.1.2 c819f67228152f2544e79a864b9a9e12dbc79f69 -m "Release version 1.1.2"
$ git rev-parse 'v1.1.2^{commit}'
c819f67228152f2544e79a864b9a9e12dbc79f69
$ git push origin v1.1.2
To github.com:zhangtaolab/SIF.git
 * [new tag]         v1.1.2 -> v1.1.2
```

The tag target equals `release_head` from `17-06-SUMMARY.md`; the later metadata commit `b0b4258` was not tagged. `runpy` on `src/sif/_version.py` at `c819f67` reads `1.1.2`.

### Publish run

```text
$ gh run list --workflow=publish.yml --commit c819f67228152f2544e79a864b9a9e12dbc79f69 --limit 1 --json databaseId,status,conclusion
[{"conclusion":"failure","databaseId":43562577065,"status":"completed"}]
```

Run URL: https://github.com/zhangtaolab/SIF/actions/runs/43562577065 (event `push`, `headBranch` `v1.1.2`, `headSha` `c819f67228152f2544e79a864b9a9e12dbc79f69`).

Job conclusions:

| Job | Conclusion | Timing |
|-----|-----------|--------|
| Build distributions | success | 05:39:24Z -> 05:39:38Z |
| Publish to TestPyPI | **failure** | 05:39:41Z -> 05:39:53Z |
| Publish to PyPI | skipped | 05:39:53Z |

The build job's tag↔version gate passed and `uv build` + `uvx twine check` succeeded; the distributions were built once and never rebuilt.

### Failure excerpt

```text
Publish to TestPyPI  ##[error]Trusted publishing exchange failure:
Publish to TestPyPI  Token request failed: the server refused the request for the following reasons:
Publish to TestPyPI  * `invalid-publisher`: valid token, but no corresponding publisher (Publisher with matching claims was not found)
Publish to TestPyPI  * `sub`: `repo:zhangtaolab/SIF:environment:testpypi`
Publish to TestPyPI  * `repository`: `zhangtaolab/SIF`
Publish to TestPyPI  * `repository_owner`: `zhangtaolab`
Publish to TestPyPI  * `repository_owner_id`: `21210477`
Publish to TestPyPI  * `workflow_ref`: `zhangtaolab/SIF/.github/workflows/publish.yml@refs/tags/v1.1.2`
Publish to TestPyPI  * `job_workflow_ref`: `zhangtaolab/SIF/.github/workflows/publish.yml@refs/tags/v1.1.2`
Publish to TestPyPI  * `ref`: `refs/tags/v1.1.2`
Publish to TestPyPI  * `environment`: `testpypi`
```

The failure occurred during OIDC token exchange, in the `pypa/gh-action-pypi-publish@release/v1` Docker action, before any upload request.

## Root Cause

The GitHub OIDC claim is `repository: zhangtaolab/SIF` — GitHub's canonical repository name is **`SIF` uppercase** (`gh repo view zhangtaolab/sif --json name,nameWithOwner` returns `SIF` / `zhangtaolab/SIF`; owner id `21210477` matches the claim).

Warehouse (PyPI's server) matches publishers with an exact equality filter on `repository_name` taken from the claim (`warehouse/oidc/models/github.py`, `lookup_by_claims`: `Query(cls).filter_by(repository_name=repository_name, repository_owner=..., repository_owner_id=..., workflow_filename=...)`). Unlike environment names, which are lowercased by the form, the repository name is stored as entered and compared case-sensitively.

`17-06-SUMMARY.md` records the maintainer-confirmed TestPyPI pending publisher with repository `sif` lowercase. `sif` != `SIF` under an exact match, so the publisher lookup found nothing and returned `invalid-publisher`.

Secondary fields to re-verify while editing: project name `docsif`, owner `zhangtaolab`, workflow filename `publish.yml` (file name, not the `Publish` display name), environment `testpypi` (environment matching is case-insensitive; a blank environment also acts as a general publisher, so the environment field is less likely to be the cause — but it must not be a different non-blank name such as `pypi`).

The same case mismatch is likely present on the production PyPI trusted publisher for `docsif` (recorded as repository `sif`). It must be corrected too before the PyPI leg is reached; publishing to PyPI under the wrong claims would fail the same way, but PyPI `skip-existing` is deliberately absent, so this must be right on the first successful upload.

## One-Way-Door Safety State

- No TestPyPI upload occurred: `curl https://test.pypi.org/pypi/docsif/json` still returns HTTP 404.
- No PyPI upload occurred: `https://pypi.org/pypi/docsif/json` reports latest `1.0.1` and `1.1.2` is absent from `releases`.
- Version 1.1.2 is therefore NOT consumed; no new patch version is needed.
- Tag `v1.1.2` remains in place. Re-running the failed jobs of run `43562577065` after the publisher fix is safe: TestPyPI uses `skip-existing: true`, and the build artifact from the same run is reused (no rebuild under a mutated version).

## Required Human Action (blocking, browser-only)

1. **TestPyPI** — `https://test.pypi.org/manage/account/publishing/` → edit the pending publisher for project `docsif`:
   - Owner: `zhangtaolab`
   - Repository name: **`SIF`** (uppercase — must match the OIDC claim exactly)
   - Workflow filename: `publish.yml`
   - Environment name: `testpypi`
2. **PyPI** — `https://pypi.org/manage/project/docsif/publishing/` → verify/edit the trusted publisher with the same values, except environment `pypi`.
3. Report the corrected entries. Then resume 17-07: re-run the failed jobs with
   `gh run rerun 43562577065 --failed` (or re-run the whole run), and continue with the plan's verify blocks, attestation verification, and both install proofs.

No local command can read or change these registrations; the end-to-end proof remains the next OIDC publish.

## Files Created/Modified

- `.planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-07-SUMMARY.md` — this halted checkpoint record.
- `.planning/STATE.md` — halt position, blocker, decisions.
- `.planning/ROADMAP.md` — 17-07 annotated blocked; plan count stays 8/9.
- No product or test file changed.

## Self-Check: PASSED

- `git rev-parse 'v1.1.2^{commit}'` equals the `release_head` recorded in 17-06 (`c819f67228152f2544e79a864b9a9e12dbc79f69`); tag exists locally and on origin.
- Publish run `43562577065` exists for that commit with exactly one run; build `success`, publish-testpypi `failure`, publish-pypi `skipped`.
- `--log-failed` was inspected; the failure is `invalid-publisher` at token exchange.
- Both indexes were checked and still do not serve 1.1.2, proving nothing was consumed.
- No task-level or metadata commit was made before this record; the plan remains halted.

---
*Phase: 17-engineering-foundation-ci-matrix-hygiene-pypi*
*Checkpoint: 2026-11-14*
