---
phase: 17-engineering-foundation-ci-matrix-hygiene-pypi
plan: 06
subsystem: release
tags: [github-environments, pypi, testpypi, trusted-publishing, oidc, release-gate, checkpoint, halted]

# Dependency graph
requires: ["17-03", "17-04", "17-05", "17-08", "17-09"]
provides:
  - "GitHub environments pypi (id 27264851535) and testpypi (id 27264859642) on zhangtaolab/sif, zero protection rules (no required reviewers, no wait timer), no branch policy"
  - "Verified via `gh api repos/zhangtaolab/sif/environments` that both names match .github/workflows/publish.yml job environments exactly"
  - "Checkpoint package for the UI-only publisher registrations (exact fields for PyPI project docsif and the TestPyPI pending publisher)"
affects: [17-07]

# Actuals (#2632) — partial: plan halted at Task 2's blocking human-action checkpoint
actuals:
  tokens: 4550
  tasks: 1
  commits: 2
  plan_head_before: 5215d8bd7a9eecf3a3420b7651560425c783bc1a
  plan_head_after: 661caff0c2ec71488d8ec83c185003b210abd42a

tech-stack:
  added: []
  patterns:
    - "Environment creation as a tracer step: `gh api --method PUT repos/<owner>/<repo>/environments/<name>` then verify the names through the list endpoint before any publisher registration"
    - "Designed stop at a UI-only external action: record the exact registration fields and evidence in a `status: halted` SUMMARY so dependents are blocked until the human acts (#2830)"

key-files:
  created: []
  modified:
    - .planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-06-SUMMARY.md

key-decisions:
  - "Created both environments with an empty PUT body so the API defaults apply (no required reviewers, no wait timer), honoring D-15's tag-as-release-intent"
  - "Recorded the exact environment ids and the zero-protection state rather than only the names, so the later OIDC proof in 17-07 can be tied to these records"
  - "Stopped at Task 2 instead of improvising: PyPI/TestPyPI publisher configuration has no public API and cannot be verified or created from here"
  - "Marked the SUMMARY `status: halted` (not complete) so 17-07 is reported as blocked by this halt until the registrations land and the pre-tag gate runs (#2830)"

patterns-established:
  - "A checkpoint SUMMARY records the completed tasks table plus the exact external fields the human must enter; no field is invented and no registration is claimed"

requirements-completed: []

coverage:
  - id: D1
    description: "GitHub environments pypi and testpypi exist on zhangtaolab/sif with no required reviewers and with names identical to the publish.yml job environments"
    requirement: ENG-03
    verification:
      - kind: e2e
        ref: "gh api repos/zhangtaolab/sif/environments --jq '([.environments[].name] | index(\"pypi\")) != null and ([.environments[].name] | index(\"testpypi\")) != null' | grep -qx true — exit 0"
        status: pass
      - kind: e2e
        ref: "gh api repos/zhangtaolab/sif/environments --jq '.environments[] | {name, id, protection_rules: (.protection_rules | length), deployment_branch_policy}' — pypi id 27264851535, testpypi id 27264859642, protection_rules 0, policy null"
        status: pass
    human_judgment: false
  - id: D2
    description: "Maintainer has registered the PyPI trusted publisher on the existing docsif project (owner zhangtaolab, repo sif, workflow filename publish.yml, environment pypi) and the TestPyPI pending publisher (project docsif, same owner/repo/workflow, environment testpypi)"
    requirement: ENG-03
    verification: []
    human_judgment: true
    rationale: "Both registrations are browser-only PyPI/TestPyPI account settings with no public API; Claude can neither create nor read them. The end-to-end proof is the 17-07 OIDC publish, not any local check."
  - id: D3
    description: "Pre-tag release gate: a green Test Matrix run on the release HEAD (8 py cells + lint), src/sif diff since the recorded smoke limited to _version.py, and every release artifact present, with release_head recorded"
    requirement: ENG-03
    verification:
      - kind: e2e
        ref: "not yet run — Task 3 is blocked on Task 2; read-only pre-check only (see Evidence Preview)"
        status: unknown
    human_judgment: false

# Metrics
duration: 3min
completed: 2026-11-14
status: halted
---

# Phase 17 Plan 06: Release Prerequisites + Pre-Tag Gate Summary

**Both publish environments (`pypi`, `testpypi`) now exist on `zhangtaolab/sif` with zero protection rules; the plan stopped at the blocking human-action checkpoint for the browser-only PyPI/TestPyPI publisher registrations, so the pre-tag gate has NOT run and no tag exists.**

## Performance

- **Duration:** ~3 min to the checkpoint
- **Started:** 2026-11-14T02:03:06Z
- **Stopped:** 2026-11-14T02:05:41Z (checkpoint; plan intentionally left unfinished)
- **Tasks:** 1 of 3 complete (Task 2 awaiting human action; Task 3 not started)
- **Files modified:** 1 (this SUMMARY; no product or test files changed — the external environment records are not in git)

## Task Status

| Task | Name | Status | Evidence / Blocker |
|------|------|--------|--------------------|
| 1 | Create the GitHub environments `pypi` and `testpypi` (D-14) | Complete | Both PUT calls returned 201-created records; list-endpoint verify exited 0 |
| 2 | Register the PyPI trusted publisher and TestPyPI pending publisher for `docsif` | Blocked — blocking human-action checkpoint | UI-only account settings; exact fields below |
| 3 | Pre-tag release gate — matrix green on release HEAD plus smoke coverage (D-14, D-15) | Not started | Precondition requires Task 2's confirmation; must not run before it |

## Task 1 Evidence (GitHub environments)

`gh api --method PUT repos/zhangtaolab/sif/environments/pypi` returned:

```json
{"id":27264851535,"name":"pypi","can_admins_bypass":true,"protection_rules":[],"deployment_branch_policy":null,"created_at":"2026-11-14T02:03:29Z"}
```

`gh api --method PUT repos/zhangtaolab/sif/environments/testpypi` returned:

```json
{"id":27264859642,"name":"testpypi","can_admins_bypass":true,"protection_rules":[],"deployment_branch_policy":null,"created_at":"2026-11-14T02:03:38Z"}
```

Post-creation state:

```text
$ gh api repos/zhangtaolab/sif/environments --jq '.environments[] | {name, id, protection_rules: (.protection_rules | length), deployment_branch_policy}'
{"deployment_branch_policy":null,"id":27264851535,"name":"pypi","protection_rules":0}
{"deployment_branch_policy":null,"id":27264859642,"name":"testpypi","protection_rules":0}
```

The plan's automated verify (`... | index("pypi")) != null and (... | index("testpypi")) != null' | grep -qx true`) exited 0. No required reviewers, wait timers, or secrets were added (D-15: the tag is the release intent; the environment still scopes which workflow may mint OIDC tokens). The names match `.github/workflows/publish.yml` exactly: `environment: name: testpypi` (publish-testpypi job, line 55) and `environment: name: pypi` (publish-pypi job, line 77).

## Checkpoint — Task 2 (blocking human action)

Nothing below has been registered. PyPI and TestPyPI expose no public API for trusted-publisher configuration, so these two entries must be added by the maintainer in the browser. Exact values, matching the publish workflow and the created environments:

**1. PyPI — existing project `docsif` → Publishing**

- URL: https://pypi.org/manage/project/docsif/publishing/
- Pitcher (trusted publisher) fields:
  - **Owner:** `zhangtaolab`
  - **Repository name:** `sif`
  - **Workflow filename:** `publish.yml` ← the FILE name, NOT the workflow display name `Publish`
  - **Environment name:** `pypi`

**2. TestPyPI — pending publisher (project does not exist yet; TestPyPI returns 404 for `docsif`)**

- URL: https://testpypi.org/manage/account/publishing/
- Pending publisher fields:
  - **Project name:** `docsif`
  - **Owner:** `zhangtaolab`
  - **Repository name:** `sif`
  - **Workflow filename:** `publish.yml`
  - **Environment name:** `testpypi`

Verification: both entries visible on the two pages above (project `docsif` → Publishing; TestPyPI account → Publishing). No local command can read them; the true end-to-end proof is a successful OIDC mint during plan 17-07's tag publish. A pending TestPyPI publisher does not reserve the `docsif` name until the first successful upload.

**Resume signal:** reply `registered` (or paste the visible publisher entries). A continuation agent then executes Task 3 (push the branch, wait for the Test Matrix run on the resulting HEAD, assert 8 py cells + lint green, assert the smoke-coverage diff, record `release_head: <40-hex-sha>`), and only then may 17-07 tag that exact commit.

## Evidence Preview for Task 3 (read-only, NOT the gate)

Task 3 has not run. The following was checked read-only at HEAD `5215d8b` to give the continuation agent a baseline:

- `17-04-SUMMARY.md` records `smoke_head: 48759e2c532d01d92a0deef08520a58c41115378`; the plan's `sed` extraction pattern yields exactly this SHA.
- `git diff --name-only 48759e2c532d01d92a0deef08520a58c41115378..HEAD -- src/sif` prints exactly `src/sif/_version.py` (31 files changed overall since the smoke, all outside `src/sif`).
- `runpy.run_path('src/sif/_version.py')['__version__']` → `1.1.2`.
- `README.md` line 2 contains `<!-- mcp-name: io.github.zhangtaolab/sif -->`.
- `pyproject.toml` line 24 contains `"Programming Language :: Python :: 3.13"`.
- `docs/changelog.md` line 38 contains `## [1.1.2] - 2026-11-13`.
- `.github/workflows/publish.yml` exists with the three jobs (`build`, `publish-testpypi`, `publish-pypi`).

The gate itself must be re-run after Task 2 because the branch push and the release HEAD change when this SUMMARY's commit lands.

## Task Commits

No commits for Task 1: it created external GitHub state only and modified no files. The plan's metadata commit (this SUMMARY, STATE.md, ROADMAP.md) is the only commit from this run.

Measured commit count from the plan ledger (`plan_head_before` `5215d8b`): 2 metadata commits (`1d95846`, `661caff`), 0 task commits — no product or test file changed in this run.

## Files Created/Modified

- `.planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-06-SUMMARY.md` — this halted/checkpoint record.

## Decisions Made

- Used an empty PUT body for both environments: GitHub's defaults are exactly the locked configuration (no required reviewers, no wait timer, no branch policy). Adding reviewers would contradict D-15.
- Recorded the environment ids and the zero-protection response, not just the names, so 17-07's OIDC result can be tied to these exact records.
- Stopped at Task 2 rather than attempting any workaround: publisher registration is outside git, outside the API, and outside anything Claude can verify locally.
- Set `status: halted` so the dependency graph reports 17-07 as blocked by this designed stop until the registrations land and Task 3's gate passes.

## Deviations from Plan

None - Task 1 executed exactly as written; the plan itself designed the stop at Task 2.

## Issues Encountered

None. The `gh` CLI was already authenticated as `forrestzhang` with `repo` scope, and the repo endpoint returned `zhangtaolab/SIF` (public, default branch `main`), satisfying the task precondition.

## User Setup Required

**Two browser-only registrations (Task 2).** See the Checkpoint section for the exact fields:

1. PyPI project `docsif` → Publishing: owner `zhangtaolab`, repository `sif`, workflow filename `publish.yml`, environment `pypi`.
2. TestPyPI account → Publishing → pending publisher: project `docsif`, owner `zhangtaolab`, repository `sif`, workflow filename `publish.yml`, environment `testpypi`.

Do not use the workflow display name `Publish`; the registered value must be the file name `publish.yml`.

## Next Phase Readiness

- Ready: GitHub environments `pypi`/`testpypi` exist with the exact names the publish jobs reference.
- Blocked: Task 3's pre-tag gate and all of plan 17-07 (tag `v1.1.2`, OIDC publish, attestation/install proofs) until the two registrations are confirmed.
- The release tree's artifact evidence and smoke coverage already look correct at `5215d8b` but are NOT gate-verified; no `release_head:` is recorded yet by design.

## Self-Check: PASSED (partial run)

- Both environments exist, were re-read from the API after creation, and match `publish.yml`'s job environments.
- `.planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-06-SUMMARY.md` exists on disk.
- Commits `1d95846` (this SUMMARY) and `661caff` (STATE + ROADMAP checkpoint record) are ancestors of HEAD; the measured ledger count is 2 metadata commits and 0 task commits (no product/test file changed).
- No registration is claimed; the checkpoint explicitly states nothing was registered.

---
*Phase: 17-engineering-foundation-ci-matrix-hygiene-pypi*
*Halted at Task 2 checkpoint: 2026-11-14*
