---
phase: 17-engineering-foundation-ci-matrix-hygiene-pypi
plan: 07
subsystem: release
tags: [pypi, testpypi, trusted-publishing, oidc, attestations, release, checkpoint, halted, retry]
status: halted

# Dependency graph
requires: ["17-06"]
provides:
  - "Annotated tag v1.1.2 unchanged on release_head c819f67228152f2544e79a864b9a9e12dbc79f69 — never moved or re-pushed"
  - "Publish run 43562577065 attempts 1-2: Build distributions success (reused in attempt 2 with unchanged timestamps, no rebuild); Publish to TestPyPI failure (invalid-publisher both attempts); Publish to PyPI skipped"
  - "Proof that no artifact reached either index: TestPyPI still 404 for docsif, PyPI still serves only 1.0.1 with no 1.1.2 release"
affects: []

# Actuals (#2632) — partial: plan halted at Task 1's external publisher-config blocker after one retry; commits measured from the plan ledger before the final ledger commit
actuals:
  tokens: 6642
  tasks: 0
  commits: 3
  plan_head_before: b0b4258535d50f552c5957ee5a28bb7999059f97
  plan_head_after: 118526ab34081707102d3a3122017922db467dc6

tech-stack:
  added: []
  patterns:
    - "A tag push is release intent but not consumption: a trusted-publisher claim mismatch fails at token exchange, before any upload, so the immutable version stays available"
    - "Diagnose invalid-publisher from the OIDC claim dump in the action log; warehouse matches repository_name, repository_owner, repository_owner_id, and workflow_filename exactly, while environment names are lowercased"
    - "Rerunning `gh run rerun --failed` reuses a successful dependency job: the Build job kept its original attempt-1 timestamps and databaseId, so the artifact was not rebuilt"

key-files:
  created:
    - .planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-07-SUMMARY.md
  modified:
    - .planning/STATE.md
    - .planning/ROADMAP.md

key-decisions:
  - "Tagged exactly release_head c819f67228152f2544e79a864b9a9e12dbc79f69 (never the later metadata commit) and verified tag^{commit} equals it; the tag was left untouched on retry"
  - "Executed the single policy-allowed retry of the failed jobs after the maintainer confirmed both registrations were corrected to repository SIF; attempt 2 failed identically at token exchange"
  - "Stopped after that one retry instead of looping: the claim already carries repository zhangtaolab/SIF, so the remaining registration mismatch is in another exact-match field (or the pending publisher was not saved), and no local command can read or change these records"
  - "Did not create a new patch version: no upload occurred on either index, so version 1.1.2 is NOT consumed"
---

# Phase 17 Plan 07: Tag + Publish Checkpoint Summary — HALTED (attempt 2) at TestPyPI trusted-publisher mismatch

**After the maintainer corrected both publisher registrations to repository `SIF`, the single policy-allowed retry of Publish run `43562577065` failed again at the TestPyPI OIDC token exchange with `invalid-publisher`: the claims (`repository: zhangtaolab/SIF`, `environment: testpypi`, `workflow_ref: zhangtaolab/SIF/.github/workflows/publish.yml@refs/tags/v1.1.2`) still match no registered publisher. No upload occurred on either index, so version 1.1.2 remains unconsumed and tag `v1.1.2` stays on `c819f67`.**

## Task Status

| Task | Name | Status | Evidence / Blocker |
|------|------|--------|--------------------|
| 1 | Push tag v1.1.2 and drive build -> TestPyPI -> PyPI to success (D-13, D-14, D-15) | Blocked (attempt 2) | Tag unchanged on `c819f67`; run `43562577065` attempts 1-2: build `success` (reused), publish-testpypi `failure` (`invalid-publisher`), publish-pypi `skipped` |
| 2 | Post-publish provenance and install proofs | Not started | Precondition unmet: Task 1 did not publish |

## Attempt History

| Attempt | Trigger | Build distributions | Publish to TestPyPI | Publish to PyPI | Run |
|---------|---------|---------------------|---------------------|-----------------|-----|
| 1 | tag push `v1.1.2` | success 05:39:24Z -> 05:39:38Z | **failure** 05:39:41Z -> 05:39:53Z (`invalid-publisher`) | skipped | failure |
| 2 | `gh run rerun 43562577065 --failed` | success — **not re-executed** (same timestamps 05:39:24Z -> 05:39:38Z) | **failure** 05:46:23Z -> 05:46:39Z (`invalid-publisher`) | skipped 05:46:39Z | failure |

Run URL: https://github.com/zhangtaolab/SIF/actions/runs/43562577065 (event `push`, `headSha` `c819f67228152f2544e79a864b9a9e12dbc79f69`, `attempt: 2`).

## Task 1 Evidence

### Tag (unchanged, not retagged)

```text
$ git rev-parse 'v1.1.2^{commit}'
c819f67228152f2544e79a864b9a9e12dbc79f69
$ git rev-parse 'v1.1.2'
fcca22f8d28addd5e941e1fc77bae5334507c151
$ git ls-remote --tags origin 'v1.1.2^{}'
c819f67228152f2544e79a864b9a9e12dbc79f69	refs/tags/v1.1.2^{}
```

The tag target equals `release_head` from `17-06-SUMMARY.md`. This continuation did not delete, move, or re-push the tag.

### Retry

```text
$ gh run rerun 43562577065 --failed
(no output — rerun accepted)
$ gh run view 43562577065 --json status,conclusion,attempt
{"attempt":2,"conclusion":"failure","status":"completed"}
```

### Attempt 2 job conclusions

```text
$ gh run view 43562577065 --json jobs --jq '.jobs[] | {name, databaseId, status, conclusion, startedAt, completedAt}'
{"name":"Publish to TestPyPI","databaseId":132350992858,"status":"completed","conclusion":"failure","startedAt":"2026-11-14T05:46:23Z","completedAt":"2026-11-14T05:46:39Z"}
{"name":"Build distributions","databaseId":132350993506,"status":"completed","conclusion":"success","startedAt":"2026-11-14T05:39:24Z","completedAt":"2026-11-14T05:39:38Z"}
{"name":"Publish to PyPI","databaseId":132351072495,"status":"completed","conclusion":"skipped","startedAt":"2026-11-14T05:46:39Z","completedAt":"2026-11-14T05:46:39Z"}
```

`Build distributions` kept its attempt-1 start/complete timestamps, so the successful dependency job was reused: the distributions were **not** rebuilt. `gh run view 43562577065 --exit-status` exited 1.

### Failure excerpt (attempt 2)

```text
Publish to TestPyPI  ##[error]Trusted publishing exchange failure:
Publish to TestPyPI  Token request failed: the server refused the request for the following reasons:
Publish to TestPyPI  * `invalid-publisher`: valid token, but no corresponding publisher (Publisher with matching claims was not found)
Publish to TestPyPI  This generally indicates a trusted publisher configuration error, but could
Publish to TestPyPI  also indicate an internal error on GitHub or PyPI's part.
Publish to TestPyPI  * `sub`: `repo:zhangtaolab/SIF:environment:testpypi`
Publish to TestPyPI  * `repository`: `zhangtaolab/SIF`
Publish to TestPyPI  * `repository_owner`: `zhangtaolab`
Publish to TestPyPI  * `repository_owner_id`: `21210477`
Publish to TestPyPI  * `workflow_ref`: `zhangtaolab/SIF/.github/workflows/publish.yml@refs/tags/v1.1.2`
Publish to TestPyPI  * `job_workflow_ref`: `zhangtaolab/SIF/.github/workflows/publish.yml@refs/tags/v1.1.2`
Publish to TestPyPI  * `ref`: `refs/tags/v1.1.2`
Publish to TestPyPI  * `environment`: `testpypi`
```

The failure occurred during OIDC token exchange in `pypa/gh-action-pypi-publish@release/v1`, before any upload request.

## Diagnosis

Attempt 1 was diagnosed as a case mismatch: the recorded TestPyPI pending publisher used repository `sif` while GitHub's canonical OIDC claim is `zhangtaolab/SIF`, and warehouse compares `repository_name` exactly. The maintainer then confirmed both registrations were corrected to repository **`SIF` (uppercase)** — TestPyPI pending publisher (project `docsif`, environment `testpypi`) and PyPI trusted publisher (project `docsif`, environment `pypi`).

Attempt 2 still returns `invalid-publisher` even though the claim already carries `repository: zhangtaolab/SIF`. The remaining cause is therefore one of the other exact-match fields, or the TestPyPI pending publisher record is not the one being consulted:

1. **Project name** — must be exactly `docsif` (a pending publisher for a different project name creates a different reservation).
2. **Repository name** — must be saved as exactly `SIF`; confirm by reopening the saved entry, not just the form. A stale/unsaved edit produces the same failure.
3. **Workflow filename** — must be exactly `publish.yml` (file name with extension, not the `Publish` display name and not `.github/workflows/publish.yml`).
4. **Environment name** — must be `testpypi` (warehouse lowercases environment names; a different non-blank name such as `pypi` would not match).
5. **Owner** — must be `zhangtaolab` with owner id `21210477`.
6. The pending publisher may have failed to persist, or may be listed under another account/project; deleting and re-creating the entry is the definitive remedy.
7. The action's message also allows a GitHub/PyPI internal error. Two identical deterministic failures make a configuration mismatch the leading hypothesis, but a transient service-side fault cannot be fully excluded from this environment.

No local command can read or change these browser-only registrations; the next OIDC attempt is the only proof. One retry was allowed by the plan's failure policy and was consumed — do not rerun blindly again.

## One-Way-Door Safety State (measured after attempt 2)

- TestPyPI: `curl https://test.pypi.org/pypi/docsif/json` -> **HTTP 404** (no project, no upload).
- PyPI: `info.version` is `1.0.1`; releases are `['0.1.0', '0.1.1', '0.2.0', '1.0.0', '1.0.1']`; `1.1.2` is **absent**.
- Version 1.1.2 is therefore **NOT consumed**; no new patch version is needed.
- Tag `v1.1.2` remains on `c819f67228152f2544e79a864b9a9e12dbc79f69` locally and on origin.
- This safety only holds while TestPyPI fails before upload. Once TestPyPI succeeds, the PyPI job runs; a PyPI failure **after** any upload consumes 1.1.2 and requires a new patch version (one-way decision, D-13).

## Required Human Action (blocking, browser-only)

1. **TestPyPI** — open `https://test.pypi.org/manage/account/publishing/` and verify the **saved** pending publisher entry (not just the edit form). Expected values:
   - Project name: `docsif`
   - Owner: `zhangtaolab`
   - Repository name: **`SIF`** (uppercase, exact)
   - Workflow filename: `publish.yml`
   - Environment name: `testpypi`
   If anything differs or the entry looks stale, delete it and re-create it with these values.
2. **PyPI** — verify `https://pypi.org/manage/project/docsif/publishing/` has the same values, except environment `pypi`. Correcting it now prevents the PyPI leg from failing after the version is consumed.
3. Report the corrected/recreated entries. Then resume 17-07 with one more
   `gh run rerun 43562577065 --failed`, and continue with the plan's verify blocks, attestation verification, and both install proofs.

## Files Created/Modified

- `.planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-07-SUMMARY.md` — this attempt-2 checkpoint record (updated from the attempt-1 halt).
- `.planning/STATE.md` — halt position, blocker, decisions updated to attempt 2.
- `.planning/ROADMAP.md` — 17-07 annotated blocked after retry; plan count stays 8/9.
- `.planning/WINDOWS.md` — two open blocker entries appended: `unmet-truth` (run 43562577065 not green) and `unrun-verify` (Task 2 attestation/install proofs pending).
- No product or test file changed; no package installed; the tag was not modified.

## Deviations from Plan

None. The plan's documented failure policy was executed exactly: one retry of the failed jobs after the publisher correction, then stop with evidence when `invalid-publisher` repeated.

## Self-Check: PASSED

- `git rev-parse 'v1.1.2^{commit}'` equals `release_head` `c819f67228152f2544e79a864b9a9e12dbc79f69`; `git ls-remote --tags origin 'v1.1.2^{}'` peels to the same commit.
- Run `43562577065` is at `attempt: 2`, `status: completed`, `conclusion: failure`; build `success` (reused, original timestamps), publish-testpypi `failure`, publish-pypi `skipped`; `--exit-status` exits 1.
- `--log-failed` was inspected; the attempt-2 failure is `invalid-publisher` at token exchange with the claims quoted above.
- Both indexes were re-checked after attempt 2 and still do not serve 1.1.2, proving nothing was consumed.
- No task-level product commit was made; only this checkpoint's metadata is committed.
- No retry beyond the policy-allowed one was attempted.

---
*Phase: 17-engineering-foundation-ci-matrix-hygiene-pypi*
*Checkpoint: 2026-11-14 (attempt 2)*
