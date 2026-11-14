---
phase: 17-engineering-foundation-ci-matrix-hygiene-pypi
plan: 07
subsystem: release
tags: [pypi, testpypi, trusted-publishing, oidc, attestations, release, checkpoint, halted, final-retry, attempt-3]
status: halted

# Dependency graph
requires: ["17-06"]
provides:
  - "Annotated tag v1.1.2 unchanged on release_head c819f67228152f2544e79a864b9a9e12dbc79f69 — never moved or re-pushed across three attempts"
  - "Publish run 43562577065 attempts 1-3: Build distributions success (reused unchanged in attempts 2-3, no rebuild); Publish to TestPyPI failure (invalid-publisher all three attempts); Publish to PyPI skipped every attempt"
  - "Proof that no artifact reached either index after attempt 3: TestPyPI still 404 for docsif, PyPI still serves only 1.0.1 with no 1.1.2 release"
  - "The publisher registration was deleted and re-created with the exact expected fields between attempts 2 and 3, and the failure did not change — the mismatch is not the previously suspected repository-name case"
affects: []

# Actuals (#2632) — partial: plan halted at Task 1's external publisher-config blocker after the final policy-allowed retry; commits measured from the plan ledger before the final ledger commit
actuals:
  tokens: 10340
  tasks: 0
  commits: 4
  plan_head_before: b0b4258535d50f552c5957ee5a28bb7999059f97
  plan_head_after: ad22d11ab5bcfb7d6cb93776b29f19cffff17b44

tech-stack:
  added: []
  patterns:
    - "A tag push is release intent but not consumption: a trusted-publisher claim mismatch fails at token exchange, before any upload, so the immutable version stays available"
    - "Diagnose invalid-publisher from the OIDC claim dump in the action log; warehouse matches repository_name, repository_owner, repository_owner_id, and workflow_filename exactly, while environment names are lowercased"
    - "Rerunning `gh run rerun --failed` reuses a successful dependency job: the Build job kept its original attempt-1 timestamps and databaseId through attempts 2 and 3, so the artifact was never rebuilt"
    - "A re-created pending publisher with byte-identical field values producing an identical failure rules out value drift in the form; the remaining causes are the wrong index/account/project record or a warehouse-side fault"

key-files:
  created:
    - .planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-07-SUMMARY.md
  modified:
    - .planning/STATE.md
    - .planning/ROADMAP.md
    - .planning/WINDOWS.md

key-decisions:
  - "Tagged exactly release_head c819f67228152f2544e79a864b9a9e12dbc79f69 (never the later metadata commit) and verified tag^{commit} equals it; the tag was not touched on any retry"
  - "After the maintainer deleted and re-created the TestPyPI pending publisher and re-saved the PyPI trusted publisher with the exact expected fields, executed the one final policy-allowed rerun; attempt 3 failed identically at token exchange"
  - "Stopped after attempt 3 without looping: this was the last blind retry. The claim set is unchanged and already matches every documented field, so the residual mismatch is outside anything a local command can read or change"
  - "Did not create a new patch version: no upload occurred on either index on any attempt, so version 1.1.2 is NOT consumed and tag v1.1.2 remains valid"
  - "Did not fall back to an API-token/manual upload: the plan prohibits mutating the publish path, and a token-based publish would deviate from trusted publishing and requires an explicit user decision and plan amendment"
---

# Phase 17 Plan 07: Tag + Publish Checkpoint Summary — HALTED (attempt 3, final retry) at TestPyPI trusted-publisher mismatch

**The final policy-allowed rerun of Publish run `43562577065` failed identically: TestPyPI rejected the OIDC token exchange with `invalid-publisher`, even though the maintainer deleted and re-created the pending publisher with the exact expected fields (`project docsif`, `owner zhangtaolab`, `repository SIF`, `workflow_filename publish.yml`, `environment testpypi`) after attempt 2. The claims (`repository: zhangtaolab/SIF`, `environment: testpypi`, `workflow_ref: .../publish.yml@refs/tags/v1.1.2`, `repository_owner_id: 21210477`) still match no registered publisher. No upload occurred on either index, so version 1.1.2 remains unconsumed and tag `v1.1.2` stays on `c819f67`. No further rerun was attempted.**

## Task Status

| Task | Name | Status | Evidence / Blocker |
|------|------|--------|--------------------|
| 1 | Push tag v1.1.2 and drive build -> TestPyPI -> PyPI to success (D-13, D-14, D-15) | Blocked (attempt 3, final retry) | Tag unchanged on `c819f67`; run `43562577065` attempts 1-3: build `success` (reused, never rebuilt), publish-testpypi `failure` (`invalid-publisher`), publish-pypi `skipped` |
| 2 | Post-publish provenance and install proofs | Not started | Precondition unmet: Task 1 did not publish |

## Attempt History

| Attempt | Trigger | Build distributions | Publish to TestPyPI | Publish to PyPI | Run |
|---------|---------|---------------------|---------------------|-----------------|-----|
| 1 | tag push `v1.1.2` | success 05:39:24Z -> 05:39:38Z | **failure** 05:39:41Z -> 05:39:53Z (`invalid-publisher`) | skipped | failure |
| 2 | `gh run rerun 43562577065 --failed` (after correcting repository case to `SIF`) | success — **not re-executed** (same timestamps 05:39:24Z -> 05:39:38Z) | **failure** 05:46:23Z -> 05:46:39Z (`invalid-publisher`) | skipped 05:46:39Z | failure |
| 3 | `gh run rerun 43562577065 --failed` (after delete + re-create of the pending publisher) | success — **not re-executed** (same timestamps 05:39:24Z -> 05:39:38Z) | **failure** 06:00:49Z -> 06:00:58Z (`invalid-publisher`) | skipped 06:00:58Z | failure |

Run URL: https://github.com/zhangtaolab/SIF/actions/runs/43562577065 (event `push`, `headSha` `c819f67228152f2544e79a864b9a9e12dbc79f69`, `headBranch` `v1.1.2`, `attempt: 3`, `status: completed`, `conclusion: failure`, createdAt 05:39:22Z, updatedAt 06:00:59Z).

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

The tag target equals `release_head` from `17-06-SUMMARY.md`. No continuation deleted, moved, or re-pushed the tag.

### Final retry (attempt 3)

```text
$ gh run rerun 43562577065 --failed
(no output — rerun accepted)
$ gh run view 43562577065 --json status,conclusion,attempt
{"attempt":3,"conclusion":"failure","status":"completed"}
```

Attempt 3 started at 06:00:49Z and the TestPyPI publish step failed at 06:00:57Z.

### Attempt 3 job conclusions

```text
$ gh run view 43562577065 --json jobs --jq '.jobs[] | {name, status, conclusion, startedAt, completedAt}'
{"name":"Publish to TestPyPI","status":"completed","conclusion":"failure","startedAt":"2026-11-14T06:00:49Z","completedAt":"2026-11-14T06:00:58Z"}
{"name":"Build distributions","status":"completed","conclusion":"success","startedAt":"2026-11-14T05:39:24Z","completedAt":"2026-11-14T05:39:38Z"}
{"name":"Publish to PyPI","status":"completed","conclusion":"skipped","startedAt":"2026-11-14T06:00:59Z","completedAt":"2026-11-14T06:00:58Z"}
```

`Build distributions` again kept its attempt-1 start/complete timestamps, so the successful dependency job was reused: the distributions were **not** rebuilt. `Publish to TestPyPI` job databaseId `132354423329`; step `Publish to TestPyPI` (step 3) is the only failed step. `gh run view 43562577065 --exit-status` exits **1**.

### Exact failure (attempt 3)

```text
Publish to TestPyPI  ##[error]Trusted publishing exchange failure:
Publish to TestPyPI  Token request failed: the server refused the request for the following reasons:
Publish to TestPyPI  * `invalid-publisher`: valid token, but no corresponding publisher (Publisher with matching claims was not found)
Publish to TestPyPI  This generally indicates a trusted publisher configuration error, but could
Publish to TestPyPI  also indicate an internal error on GitHub or PyPI's part.
Publish to TestPyPI  The claims rendered below are **for debugging purposes only**. You should **not**
Publish to TestPyPI  If a claim is not present in the claim set, then it is rendered as `MISSING`.
Publish to TestPyPI  * `sub`: `repo:zhangtaolab/SIF:environment:testpypi`
Publish to TestPyPI  * `repository`: `zhangtaolab/SIF`
Publish to TestPyPI  * `repository_owner`: `zhangtaolab`
Publish to TestPyPI  * `repository_owner_id`: `21210477`
Publish to TestPyPI  * `workflow_ref`: `zhangtaolab/SIF/.github/workflows/publish.yml@refs/tags/v1.1.2`
Publish to TestPyPI  * `job_workflow_ref`: `zhangtaolab/SIF/.github/workflows/publish.yml@refs/tags/v1.1.2`
Publish to TestPyPI  * `ref`: `refs/tags/v1.1.2`
Publish to TestPyPI  * `environment`: `testpypi`
```

The failure again occurred during OIDC token exchange in `pypa/gh-action-pypi-publish@release/v1`, before any upload request. The claim set is byte-identical to attempt 2; the claim values that warehouse matches did not change.

## Diagnosis

| Attempt | Publisher state at trigger | Outcome |
|---------|---------------------------|---------|
| 1 | Recorded TestPyPI pending publisher used lowercase repository `sif` | `invalid-publisher` |
| 2 | Maintainer corrected repository to `SIF` in both registrations | `invalid-publisher` (identical claims) |
| 3 | Maintainer **deleted and re-created** the TestPyPI pending publisher with `project docsif`, `owner zhangtaolab`, `repository SIF`, `workflow_filename publish.yml`, `environment testpypi`, and re-saved the PyPI trusted publisher (`project docsif`, `environment pypi`) | `invalid-publisher` (identical claims) |

Deleting and re-creating the pending publisher with the exact expected values did not change the outcome. That rules out form-value drift on the maintainer's side as the cause of the remaining mismatch. The claim set GitHub sends matches every value the pending publisher is documented to require. The residual possibilities, none of which can be read or changed from this environment, are:

1. **Wrong index or wrong record.** The pending publisher may have been saved on `pypi.org` instead of `test.pypi.org` (the two sites share a login database but have separate publisher lists), or the re-created entry may not be the one warehouse consults.
2. **Project-name mismatch invisible in the form.** The stored project name may not be exactly `docsif` (case/whitespace/unicode lookalike). Warehouse compares the project name exactly when resolving a pending publisher.
3. **Workflow filename mismatch.** Must be exactly `publish.yml`. The OIDC `workflow_ref` ends in `/.github/workflows/publish.yml`; a stored value such as `.github/workflows/publish.yml`, `Publish`, or `publish.yaml` would not match.
4. **Warehouse-side fault.** The action's own message allows a PyPI/TestPyPI internal error. Three deterministic failures make a configuration or record problem the leading hypothesis, but a service-side fault cannot be excluded from here.
5. **Account/ownership anomaly.** The pending publisher is bound to the account that created it; if the maintainer's browser session was authenticated as a different account than the one holding publisher rights for `docsif`, the record may live somewhere the OIDC claims do not reach.

No local command can read or change these browser-only registrations; only a subsequent OIDC attempt proves a fix, and the failure policy for this continuation forbids further blind retries.

## One-Way-Door Safety State (measured after attempt 3)

- TestPyPI: `curl -sS -o /dev/null -w '%{http_code}' https://test.pypi.org/pypi/docsif/json` -> **HTTP 404** (no project, no upload).
- PyPI: `info.version` is `1.0.1`; releases are `['0.1.0', '0.1.1', '0.2.0', '1.0.0', '1.0.1']`; `https://pypi.org/pypi/docsif/1.1.2/json` -> **HTTP 404**.
- Version 1.1.2 is therefore **NOT consumed**; no new patch version is needed.
- Tag `v1.1.2` remains on `c819f67228152f2544e79a864b9a9e12dbc79f69` locally and on origin.
- This safety only holds while TestPyPI fails before upload. Once TestPyPI succeeds, the PyPI job runs; a PyPI failure **after** any upload consumes 1.1.2 and requires a new patch version (one-way decision, D-13).

## Required Human Action (blocking, browser-only)

The remaining work is a publisher-registration diagnosis plus an explicit decision. Do not rerun the workflow until the registration question is resolved, because a rerun reproduces the same deterministic failure.

1. **TestPyPI** — open `https://test.pypi.org/manage/account/publishing/` (note: **test** index) and confirm a saved entry exists with exactly:
   - Project name: `docsif`
   - Owner: `zhangtaolab`
   - Repository name: `SIF`
   - Workflow filename: `publish.yml`
   - Environment name: `testpypi`
2. **PyPI** — open `https://pypi.org/manage/project/docsif/publishing/` and confirm the trusted publisher has the same values except environment `pypi`.
3. Confirm the browser session is authenticated as the PyPI/TestPyPI account that owns the `docsif` project rights for owner `zhangtaolab`.
4. If every field is exactly right and a rerun still returns `invalid-publisher`, escalate to PyPI support (`admin@pypi.org`) with the run URL `https://github.com/zhangtaolab/SIF/actions/runs/43562577065` and the exact claim dump above.
5. **Decision required (one-way):** if trusted publishing cannot be made to match, the alternative is an API-token publish (`uv publish`/`twine` with a scoped TestPyPI and PyPI token) of the existing built artifacts. That deviates from the plan's trusted-publishing prohibition and requires a plan amendment and an explicit user decision; it must publish the same bytes (no rebuild, no version mutation).
6. After any registration fix, resume 17-07 with one more `gh run rerun 43562577065 --failed`, then complete Task 1 verify (PyPI JSON version + marker) and Task 2 (pypi-attestations verification, PyPI and TestPyPI fresh-venv install proofs).

## Files Created/Modified

- `.planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-07-SUMMARY.md` — this attempt-3 (final retry) checkpoint record (updated from the attempt-2 halt).
- `.planning/STATE.md` — halt position, blocker, decisions updated to attempt 3.
- `.planning/ROADMAP.md` — 17-07 annotated blocked after the final retry; plan count stays 8/9.
- `.planning/WINDOWS.md` — the two open blocker entries (ids 11 `unmet-truth`, 12 `unrun-verify`) remain open and now cite attempts 1-3.
- No product or test file changed; no package installed; the tag was not modified.

## Deviations from Plan

None. The plan's documented failure policy was executed exactly: run the failed jobs after the publisher correction, then stop with evidence when `invalid-publisher` repeated. This continuation's single rerun allowance was consumed by attempt 3; no further attempt was made.

## Self-Check: PASSED

- `git rev-parse 'v1.1.2^{commit}'` equals `release_head` `c819f67228152f2544e79a864b9a9e12dbc79f69`; `git ls-remote --tags origin 'v1.1.2^{}'` peels to the same commit.
- Run `43562577065` is at `attempt: 3`, `status: completed`, `conclusion: failure`; build `success` (reused, original timestamps), publish-testpypi `failure` (`invalid-publisher` at 06:00:57Z), publish-pypi `skipped`; `--exit-status` exits 1.
- Both indexes were re-checked after attempt 3: TestPyPI `/pypi/docsif/json` -> 404; PyPI latest is 1.0.1 and `/pypi/docsif/1.1.2/json` -> 404, proving nothing was consumed.
- No task-level product commit was made; only this checkpoint's metadata is committed.
- No retry beyond the final policy-allowed one was attempted.

---
*Phase: 17-engineering-foundation-ci-matrix-hygiene-pypi*
*Checkpoint: 2026-11-14 (attempt 3, final retry)*
