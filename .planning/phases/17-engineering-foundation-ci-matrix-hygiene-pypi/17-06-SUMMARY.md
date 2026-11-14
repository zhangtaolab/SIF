---
phase: 17-engineering-foundation-ci-matrix-hygiene-pypi
plan: 06
subsystem: release
tags: [github-environments, pypi, testpypi, trusted-publishing, oidc, release-gate, test-matrix]
release_head: c819f67228152f2544e79a864b9a9e12dbc79f69

# Dependency graph
requires: ["17-03", "17-04", "17-05", "17-08", "17-09"]
provides:
  - "GitHub environments pypi (id 27264851535) and testpypi (id 27264859642) on zhangtaolab/sif, zero protection rules (no required reviewers, no wait timer), no branch policy"
  - "Maintainer-confirmed (2026-11-14) PyPI trusted publisher on project docsif and TestPyPI pending publisher for docsif — owner zhangtaolab, repository sif, workflow filename publish.yml, environments pypi/testpypi respectively"
  - "Gate-verified release HEAD c819f67228152f2544e79a864b9a9e12dbc79f69: Test Matrix run 43561542242 success — 8 py cells (py3.10-3.13 x ubuntu-latest/macos-latest) plus the lint job, all success"
  - "Smoke-coverage proof: `git diff --name-only 48759e2c532d01d92a0deef08520a58c41115378..c819f67228152f2544e79a864b9a9e12dbc79f69 -- src/sif` printed exactly src/sif/_version.py (1.1.1 -> 1.1.2)"
affects: [17-07]

# Actuals (#2632) — measured at SUMMARY write time from the plan ledger
actuals:
  tokens: 7868
  tasks: 3
  commits: 3
  plan_head_before: 5215d8bd7a9eecf3a3420b7651560425c783bc1a
  plan_head_after: c819f67228152f2544e79a864b9a9e12dbc79f69

tech-stack:
  added: []
  patterns:
    - "Environment creation as a tracer step: `gh api --method PUT repos/<owner>/<repo>/environments/<name>` then verify the names through the list endpoint before any publisher registration"
    - "Designed stop at a UI-only external action: record the exact registration fields and evidence in a `status: halted` SUMMARY so dependents are blocked until the human acts (#2830); the continuation flips it to complete only after the pre-tag gate runs"
    - "Pre-tag gate: push the exact release tree once, bind the CI run to the pushed 40-hex HEAD, and record that SHA as the only taggable commit"

key-files:
  created: []
  modified:
    - .planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-06-SUMMARY.md

key-decisions:
  - "Created both environments with an empty PUT body so the API defaults apply (no required reviewers, no wait timer), honoring D-15's tag-as-release-intent"
  - "Recorded the exact environment ids and the zero-protection state rather than only the names, so the OIDC proof in 17-07 can be tied to these records"
  - "Task 2 is satisfied by the maintainer's confirmation (2026-11-14) that both browser-only registrations exist; no public API can create or read them, and the end-to-end proof remains the OIDC publish in 17-07"
  - "Pushed dev exactly once (48759e2..c819f67, non-force) to obtain CI evidence on the exact release tree; no tag, no publish-workflow dispatch, no PyPI/TestPyPI upload"
  - "Recorded release_head as the gate-verified commit c819f67228152f2544e79a864b9a9e12dbc79f69; the later SUMMARY/STATE/ROADMAP metadata commit has no matrix run and must never be tagged"

patterns-established:
  - "A checkpoint SUMMARY records the completed tasks table plus the exact external fields the human must enter; no field is invented and no registration is claimed before confirmation"
  - "The release gate is a single SHA-bound record: run id, headSha equality, per-job conclusions, and the smoke-coverage diff all evaluated on the exact pushed commit"

requirements-completed: [ENG-03]

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
    rationale: "Both registrations are browser-only PyPI/TestPyPI account settings with no public API; Claude can neither create nor read them. The maintainer confirmed both entries on 2026-11-14; the end-to-end proof remains the 17-07 OIDC publish."
  - id: D3
    description: "Pre-tag release gate: a green Test Matrix run on the release HEAD (8 py cells + lint), src/sif diff since the recorded smoke limited to _version.py, and every release artifact present, with release_head recorded"
    requirement: ENG-03
    verification:
      - kind: e2e
        ref: "gh run view 43561542242 --json headSha,status,conclusion,jobs — headSha c819f67228152f2544e79a864b9a9e12dbc79f69 (equals pushed HEAD), status completed, conclusion success; 8 py cells (py3.10-3.13 x ubuntu-latest/macos-latest) all success; lint / py3.12 / ubuntu-latest success; `gh run view 43561542242 --exit-status` exit 0"
        status: pass
      - kind: e2e
        ref: "git diff --name-only 48759e2c532d01d92a0deef08520a58c41115378..c819f67228152f2544e79a864b9a9e12dbc79f69 -- src/sif — exactly src/sif/_version.py (1.1.1 -> 1.1.2)"
        status: pass
      - kind: e2e
        ref: "runpy reads 1.1.2 from src/sif/_version.py; README.md line 2 mcp-name marker; pyproject.toml line 24 Python 3.13 classifier; docs/changelog.md line 38 ## [1.1.2]; .github/workflows/publish.yml jobs build/publish-testpypi/publish-pypi"
        status: pass
    human_judgment: false

# Metrics
duration: 3h30m
completed: 2026-11-14
status: complete
---

# Phase 17 Plan 06: Release Prerequisites + Pre-Tag Gate Summary

**GitHub environments `pypi`/`testpypi` exist, the maintainer confirmed both PyPI/TestPyPI publisher registrations, and Test Matrix run 43561542242 is green on the exact release HEAD `c819f67228152f2544e79a864b9a9e12dbc79f69` (8 cells + lint), whose only `src/sif` change since the recorded Windows smoke is `src/sif/_version.py`.**

## Performance

- **Duration:** 3h30m elapsed (≈3 min initial run to the Task 2 checkpoint + ≈9 min continuation for the Task 3 gate and CI wait)
- **Started:** 2026-11-14T02:03:06Z
- **Completed:** 2026-11-14T05:31:19Z (gate evidence recorded)
- **Tasks:** 3 of 3 complete (Task 2 satisfied by maintainer confirmation)
- **Files modified:** 3 planning metadata files (this SUMMARY, STATE.md, ROADMAP.md); no product or test file changed

## Accomplishments

- Created the two GitHub environments the publish jobs reference, with zero protection rules (D-15: the tag is release intent).
- Recorded the maintainer's confirmation of both browser-only publisher registrations with the exact OIDC identity fields.
- Pushed the release tree once and proved it matrix-green on the exact pushed commit — Test Matrix run `43561542242`, 8 py cells + lint, all `success`.
- Proved the recorded Windows smoke still covers the release tree: the only `src/sif` change since `48759e2` is the version bump in `src/sif/_version.py`.
- Verified all five release artifacts at the gate-verified commit and recorded `release_head` for plan 17-07 to tag.

## Task Status

| Task | Name | Status | Evidence / Blocker |
|------|------|--------|--------------------|
| 1 | Create the GitHub environments `pypi` and `testpypi` (D-14) | Complete | Both PUT calls returned created records; list-endpoint verify exited 0 |
| 2 | Register the PyPI trusted publisher and TestPyPI pending publisher for `docsif` | Complete — maintainer confirmed 2026-11-14 | UI-only account settings; exact fields recorded below; end-to-end proof is 17-07's OIDC publish |
| 3 | Pre-tag release gate — matrix green on release HEAD plus smoke coverage (D-14, D-15) | Complete | Run `43561542242` success on `c819f67228152f2544e79a864b9a9e12dbc79f69`; 8 py cells + lint; smoke diff exactly `src/sif/_version.py` |

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

## Task 2 Attestation (maintainer-confirmed)

PyPI and TestPyPI expose no public API for trusted-publisher configuration, so neither entry can be created or read from this environment. The maintainer confirmed on 2026-11-14 that both entries exist with these exact values:

**1. PyPI — existing project `docsif` → Publishing**

- **Owner:** `zhangtaolab`
- **Repository name:** `sif`
- **Workflow filename:** `publish.yml` (the FILE name, not the workflow display name `Publish`)
- **Environment name:** `pypi`

**2. TestPyPI — pending publisher**

- **Project name:** `docsif`
- **Owner:** `zhangtaolab`
- **Repository name:** `sif`
- **Workflow filename:** `publish.yml`
- **Environment name:** `testpypi`

No local command can re-verify these records. The end-to-end proof is the successful OIDC mint during plan 17-07's tag publish; a pending TestPyPI publisher does not reserve the `docsif` name until the first successful upload.

## Task 3 Release Gate Evidence

### Push and run binding

```text
$ git push origin dev
To github.com:zhangtaolab/SIF.git
   48759e2..c819f67  dev -> dev

$ git rev-parse HEAD
c819f67228152f2544e79a864b9a9e12dbc79f69
```

The push was non-force and ran no `--no-verify` bypass. It created Test Matrix run `43561542242` (`event: push`, branch `dev`):

```text
$ gh run view 43561542242 --json headSha,status,conclusion,event,workflowName,url
{"conclusion":"success","event":"push","headSha":"c819f67228152f2544e79a864b9a9e12dbc79f69","status":"completed","workflowName":"Test Matrix","url":"https://github.com/zhangtaolab/SIF/actions/runs/43561542242"}
```

`headSha` equals the pushed HEAD exactly. The run completed `success` (created 2026-11-14T05:26:31Z, updated 2026-11-14T05:29:43Z).

### Job matrix (9/9 success)

```text
$ gh run view 43561542242 --json jobs --jq '.jobs[] | "\(.conclusion)\t\(.status)\t\(.name)"'
success	completed	py3.12 / ubuntu-latest
success	completed	py3.11 / macos-latest
success	completed	py3.10 / ubuntu-latest
success	completed	py3.13 / ubuntu-latest
success	completed	py3.12 / macos-latest
success	completed	py3.10 / macos-latest
success	completed	lint / py3.12 / ubuntu-latest
success	completed	py3.11 / ubuntu-latest
success	completed	py3.13 / macos-latest
```

Counts asserted: `py` jobs = 8, all `success`; `lint` jobs = 1, `success`; total jobs = 9, `all(. == "success")` true. `gh run view 43561542242 --exit-status` exited 0 (no `--jq -e`, which does not exist in gh 2.103.3). Timings: py3.10/3.11/3.12/3.13 on ubuntu 2m21s-2m43s, on macos 2m59s-3m8s; lint 9s.

### Smoke-coverage diff

```text
$ SMOKE_SHA=48759e2c532d01d92a0deef08520a58c41115378   # from 17-04-SUMMARY.md smoke_head
$ git diff --name-only "$SMOKE_SHA"..HEAD -- src/sif
src/sif/_version.py
```

Exactly one path. The change is the version literal only:

```diff
-__version__ = "1.1.1"
+__version__ = "1.1.2"
```

The full smoke..HEAD diff spans 32 files, all outside `src/sif` (release docs/workflow, hygiene deletions, and planning metadata), so the recorded Windows degradation smoke still covers the release tree's runtime source.

### Release artifacts at the verified commit

| Artifact | Check | Result |
|----------|-------|--------|
| `src/sif/_version.py` | `runpy.run_path(...)['__version__']` | `1.1.2` |
| `README.md` | mcp-name marker line | line 2: `<!-- mcp-name: io.github.zhangtaolab/sif -->` |
| `pyproject.toml` | Python 3.13 classifier | line 24: `"Programming Language :: Python :: 3.13",` |
| `docs/changelog.md` | 1.1.2 section | line 38: `## [1.1.2] - 2026-11-13` |
| `.github/workflows/publish.yml` | three jobs present | lines 11/50/72: `build`, `publish-testpypi`, `publish-pypi` |

### Gate-verified commit

release_head: c819f67228152f2544e79a864b9a9e12dbc79f69

Plan 17-07 must tag exactly this commit, never a later HEAD. The metadata commit that carries this SUMMARY/STATE/ROADMAP update has no Test Matrix run of its own and is not a release candidate.

## Task Commits

No product or test file was modified by any task, so there are no per-task code commits:

1. **Task 1: Create the GitHub environments** — no commit (external GitHub state only).
2. **Task 2: Register the publishers** — no commit (browser-only external registrations; maintainer confirmed).
3. **Task 3: Pre-tag release gate** — no commit (read-only git/CI verification; evidence recorded here).

**Plan metadata commits (measured from the ledger `5215d8bd7a9eecf3a3420b7651560425c783bc1a`):**

- `1d95846` — docs(17-06): record release-prerequisite checkpoint
- `661caff` — docs(17-06): record release-prerequisite checkpoint in STATE and ROADMAP
- `c819f67` — docs(17-06): finalize checkpoint SUMMARY actuals and self-check

The final metadata commit carrying this SUMMARY, STATE.md, and ROADMAP.md is created after this file is written; measured count at SUMMARY-write time is 3.

## Files Created/Modified

- `.planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-06-SUMMARY.md` — this completion record with the gate evidence.
- `.planning/STATE.md` — blocker closed, plan position/metrics updated.
- `.planning/ROADMAP.md` — Phase 17 plan progress 9/9 and 17-06 marked complete.

## Decisions Made

- Used an empty PUT body for both environments: GitHub's defaults are exactly the locked configuration (no required reviewers, no wait timer, no branch policy). Adding reviewers would contradict D-15.
- Recorded the environment ids and the zero-protection response, not just the names, so 17-07's OIDC result can be tied to these exact records.
- Treated the maintainer's explicit confirmation as satisfying Task 2; no registration is claimed from a local verification that cannot exist.
- Pushed `dev` once, non-force, to bind CI evidence to the exact release tree; did not tag, dispatch the publish workflow, or upload anything.
- Recorded `release_head` as `c819f67228152f2544e79a864b9a9e12dbc79f69`, not the post-SUMMARY metadata commit, because a later commit has no matrix run of its own.

## Deviations from Plan

None - the plan executed as written. Task 2's designed stop was resolved by the maintainer's confirmation on resume; Task 3 then executed exactly as specified.

## Issues Encountered

None. `gh` was authenticated as `forrestzhang` with `repo` scope; the push was accepted without protection interference; the Test Matrix run completed green in about 3 minutes.

## User Setup Required

Both previously required browser-only registrations are now confirmed complete (see Task 2 Attestation). No further external setup is required before plan 17-07; the remaining proof is 17-07's end-to-end OIDC publish.

## Next Phase Readiness

- Ready: GitHub environments `pypi`/`testpypi` exist with the exact names the publish jobs reference, and both publisher registrations are maintainer-confirmed.
- Ready: `release_head` `c819f67228152f2544e79a864b9a9e12dbc79f69` is matrix-green (8 cells + lint), and the smoke-coverage argument holds at that commit.
- Plan 17-07 may now tag exactly `release_head`, push the tag, and prove the OIDC publish, PyPI marker, PEP 740 attestations, and fresh-venv installs.

## Self-Check: PASSED

- Run `43561542242` exists, `headSha` equals the pushed HEAD `c819f67228152f2544e79a864b9a9e12dbc79f69`, `conclusion` is `success`, and all 9 jobs are `success`.
- `gh run view 43561542242 --exit-status` exited 0; both plan `<automated>` pipelines exited 0.
- `git diff --name-only 48759e2c532d01d92a0deef08520a58c41115378..HEAD -- src/sif` printed exactly `src/sif/_version.py`.
- All five release artifacts were re-checked at the verified commit with the quoted outputs above.
- `release_head` is recorded as the frontmatter line and as the Task 3 evidence line; both are `c819f67228152f2544e79a864b9a9e12dbc79f69`, and `sed -n 's/.*release_head: \([0-9a-f]\{40\}\).*/\1/p' | head -1` yields that SHA.
- No tag exists for v1.1.2 yet; no publish workflow was dispatched; nothing was uploaded.

---
*Phase: 17-engineering-foundation-ci-matrix-hygiene-pypi*
*Completed: 2026-11-14*
