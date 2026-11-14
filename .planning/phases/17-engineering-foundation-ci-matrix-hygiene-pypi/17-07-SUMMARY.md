---
phase: 17-engineering-foundation-ci-matrix-hygiene-pypi
plan: 07
subsystem: release
tags: [pypi, testpypi, trusted-publishing, oidc, attestations, pep740, release, install-proof, completed]
status: complete

# Dependency graph
requires: ["17-06"]
provides:
  - "docsif 1.1.2 published to TestPyPI and PyPI from annotated tag v1.1.2 on release_head c819f67228152f2544e79a864b9a9e12dbc79f69 — the tag was never moved or re-pushed across four attempts"
  - "Publish run 43562577065 attempt 4: Build distributions success (artifact 14100657070 reused from attempt 1 — never rebuilt), Publish to TestPyPI success, Publish to PyPI success; `gh run view 43562577065 --exit-status` exits 0"
  - "PyPI JSON proof: info.version == 1.1.2 and info.description contains the exact marker <!-- mcp-name: io.github.zhangtaolab/sif -->; wheel 220225 bytes + sdist 3108000 bytes uploaded 09:20:00Z/09:20:02Z"
  - "PEP 740 attestation verification succeeds: pypi-attestations reports `OK: docsif-1.1.2-py3-none-any.whl` (exit 0) for the published wheel when the repository URL uses the canonical `zhangtaolab/SIF` case"
  - "Install proofs: fresh /tmp venvs report `sif, version 1.1.2` from PyPI and from TestPyPI (PyPI extra index for dependencies)"
affects: ["22"]

# Actuals (#2632) — measured from the plan ledger; tokens = chars/4 over the realized planning diff
actuals:
  tokens: 9560
  tasks: 2
  commits: 5
  plan_head_before: b0b4258535d50f552c5957ee5a28bb7999059f97
  plan_head_after: bd8f514516370fee9b60c2207bcd4b3879d3bbf5

tech-stack:
  added: []
  patterns:
    - "A trusted-publisher claim mismatch fails at OIDC token exchange, before any upload — that is why release attempts 1-3 did not consume the immutable version, and why attempt 4 could reuse the exact same tag and bytes"
    - "`gh run rerun --failed` reuses the successful dependency job: the Build job kept its attempt-1 databaseId and timestamps (artifact 14100657070 created 05:39:35Z) through all four attempts, so the published bytes were built exactly once"
    - "PyPI/TestPyPI pending-publisher registration is browser-only and unverifiable from CI; the first successful OIDC mint is the only proof. A 404 on the index and no upload in the job log together prove the version is still unconsumed after a failure"
    - "pypi-attestations 0.0.31 compares the provenance repository to the `--repository` URL path with an exact, case-sensitive `!=`; GitHub records the canonical repo name, so the URL must use `zhangtaolab/SIF` (uppercase), not the lowercase form in the PyPI docs example"

key-files:
  created: []
  modified:
    - .planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-07-SUMMARY.md
    - .planning/STATE.md
    - .planning/ROADMAP.md
    - .planning/WINDOWS.md

key-decisions:
  - "Reran the failed jobs only (`gh run rerun 43562577065 --failed`) after the maintainer created and verified the TestPyPI pending publisher; no rebuild, no retag, no version mutation, no manual upload"
  - "Did NOT create a new patch version: attempts 1-3 uploaded nothing and attempt 4 published 1.1.2 cleanly, so version 1.1.2 is now legitimately consumed by a successful release"
  - "Ran the attestation verification with the canonical repository case `https://github.com/zhangtaolab/SIF` (deviation Rule 1): the plan's lowercase URL is the same GitHub repository, but pypi-attestations does an exact case-sensitive compare and reported a false identity mismatch"
  - "Recorded both attestation outputs (the lowercase failure and the canonical success) instead of hiding the first attempt, so the deviation is auditable"

requirements-completed: [ENG-03]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "Publish workflow run 43562577065 completed green: build, publish-testpypi, publish-pypi all success, and the run's exit-status is 0"
    requirement: ENG-03
    verification:
      - kind: other
        ref: "gh run view 43562577065 --exit-status && gh run view 43562577065 --json jobs --jq '([.jobs[] | select(.conclusion == \"success\")] | length) == 3'"
        status: pass
    human_judgment: false
  - id: D2
    description: "PyPI serves docsif 1.1.2 and info.description contains the exact mcp-name marker"
    requirement: ENG-03
    verification:
      - kind: other
        ref: "curl -fsS https://pypi.org/pypi/docsif/1.1.2/json | python -c \"... assert version=='1.1.2'; assert marker in description\""
        status: pass
    human_judgment: false
  - id: D3
    description: "PEP 740 provenance verifies for the published wheel against repository zhangtaolab/SIF"
    requirement: ENG-03
    verification:
      - kind: other
        ref: "uvx pypi-attestations verify pypi --repository https://github.com/zhangtaolab/SIF pypi:docsif-1.1.2-py3-none-any.whl"
        status: pass
    human_judgment: false
  - id: D4
    description: "A fresh venv installs docsif==1.1.2 from PyPI and `sif --version` prints `sif, version 1.1.2`"
    requirement: ENG-03
    verification:
      - kind: other
        ref: "uv venv /tmp/sif-release-pypi-venv --python 3.12 && uv pip install --python /tmp/sif-release-pypi-venv/bin/python docsif==1.1.2 && /tmp/sif-release-pypi-venv/bin/sif --version"
        status: pass
    human_judgment: false
  - id: D5
    description: "A fresh venv installs docsif==1.1.2 from TestPyPI (with the PyPI extra index for dependencies) and prints the same version"
    requirement: ENG-03
    verification:
      - kind: other
        ref: "uv venv /tmp/sif-release-testpypi-venv --python 3.12 && uv pip install --python /tmp/sif-release-testpypi-venv/bin/python --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple docsif==1.1.2 && /tmp/sif-release-testpypi-venv/bin/sif --version"
        status: pass
    human_judgment: false

duration: 3h41m
completed: 2026-11-14
---

# Phase 17 Plan 07: Tag + Publish — docsif 1.1.2 shipped to TestPyPI and PyPI

**Annotated tag `v1.1.2` on release_head `c819f67228152f2544e79a864b9a9e12dbc79f69` drove Publish run `43562577065` to full success on attempt 4: build (artifact reused, never rebuilt), TestPyPI, and PyPI all green. PyPI serves `docsif 1.1.2` with the `<!-- mcp-name: io.github.zhangtaolab/sif -->` marker in `info.description`, PEP 740 provenance verifies against `zhangtaolab/SIF`, and fresh venvs install 1.1.2 from both indexes.**

## Performance

- **Duration:** 3h41m wall clock (tag push 05:39Z -> final publish 09:20Z), spanning the three halted attempts, the maintainer's publisher re-registration, and this completing continuation
- **Tasks:** 2 of 2
- **Files modified:** 4 (planning metadata only — no product or test file changed)

## Accomplishments

- Tag `v1.1.2` (annotated, object `fcca22f8d28addd5e941e1fc77bae5334507c151`) points at release_head `c819f67228152f2544e79a864b9a9e12dbc79f69` locally and on origin; it was never deleted, moved, or re-pushed.
- Publish run `43562577065` attempt 4 concluded **success** with every step of every job green. The Build job kept its attempt-1 `databaseId` `132402290792` and timestamps (05:39:24Z -> 05:39:38Z) and artifact `dist` id `14100657070` (created 05:39:35Z), proving the published bytes were built exactly once.
- TestPyPI accepted the trusted-publisher OIDC mint and published both files (wheel 220225 bytes at 09:19:10Z, sdist 3108000 bytes at 09:19:12Z); PyPI then published the identical sizes at 09:20:00Z / 09:20:02Z — same bytes to both indexes.
- PyPI serves `info.version == "1.1.2"` with the exact mcp-name marker in `info.description`, unblocking Phase 22's MCP Registry listing.
- PEP 740 provenance verified: `OK: docsif-1.1.2-py3-none-any.whl`.
- Two throwaway venvs install `docsif==1.1.2` from PyPI and from TestPyPI and both report `sif, version 1.1.2`.
- Project quality suite re-run green after the release: `ruff check` pass, `ruff format --check` pass, `pytest` 1669 passed / 1 skipped, coverage 95.07%.

## Task Status

| Task | Name | Status | Evidence |
|------|------|--------|----------|
| 1 | Push tag v1.1.2 and drive build -> TestPyPI -> PyPI to success (D-13, D-14, D-15) | Complete | Tag `v1.1.2^{commit}` = `c819f67` = `release_head`; run `43562577065` attempt 4 all three jobs success; `--exit-status` 0; PyPI JSON version + marker asserted |
| 2 | Post-publish provenance and install proofs | Complete | pypi-attestations `OK`; PyPI venv `sif, version 1.1.2`; TestPyPI venv `sif, version 1.1.2` |

## Task 1 Evidence

### Tag (unchanged since attempt 1)

```text
$ git rev-parse 'v1.1.2^{commit}'
c819f67228152f2544e79a864b9a9e12dbc79f69
$ git rev-parse 'v1.1.2'
fcca22f8d28addd5e941e1fc77bae5334507c151
$ git ls-remote --tags origin 'v1.1.2' 'v1.1.2^{}'
fcca22f8d28addd5e941e1fc77bae5334507c151	refs/tags/v1.1.2
c819f67228152f2544e79a864b9a9e12dbc79f69	refs/tags/v1.1.2^{}
```

The tag target equals `release_head` from `17-06-SUMMARY.md` (`c819f67228152f2544e79a864b9a9e12dbc79f69`), never a later metadata commit.

### Attempt 4 rerun

```text
$ gh run rerun 43562577065 --failed
(no output — rerun accepted, exit 0)
$ gh run view 43562577065 --json status,conclusion,attempt
{"attempt":4,"conclusion":"success","status":"completed","updatedAt":"2026-11-14T09:20:07Z"}
```

The trigger was the maintainer's newly created and verified TestPyPI pending publisher: project `docsif`, publisher GitHub, repository `zhangtaolab/SIF`, workflow `publish.yml`, environment `testpypi`. The PyPI trusted publisher for project `docsif` was registered through `https://pypi.org/manage/project/docsif/settings/publishing/` with repository `SIF`, workflow `publish.yml`, environment `pypi` (note: the older `/manage/project/docsif/publishing/` route is a stale 404).

### Attempt 4 job conclusions

```text
$ gh run view 43562577065 --json jobs --jq '.jobs[] | {name, conclusion, startedAt, completedAt, databaseId}'
{"name":"Publish to TestPyPI","conclusion":"success","startedAt":"2026-11-14T09:18:39Z","completedAt":"2026-11-14T09:19:17Z","databaseId":132402290076}
{"name":"Build distributions","conclusion":"success","startedAt":"2026-11-14T05:39:24Z","completedAt":"2026-11-14T05:39:38Z","databaseId":132402290792}
{"name":"Publish to PyPI","conclusion":"success","startedAt":"2026-11-14T09:19:20Z","completedAt":"2026-11-14T09:20:07Z","databaseId":132402458094}
$ gh run view 43562577065 --exit-status
(no output, exit 0)
```

Every step in every job concluded `success`, including the tag/version verification step, `Build`, `Check metadata`, `Publish to TestPyPI`, and `Publish to PyPI`. The TestPyPI and PyPI jobs each emitted an "Generating and uploading digital attestations" annotation.

The Build job's timestamps and `databaseId` are unchanged from attempt 1 and artifact `dist` id `14100657070` was created at `2026-11-14T05:39:35Z`, so the dependency job was reused: **no rebuild**.

### PyPI JSON proof

```text
$ curl -fsS https://pypi.org/pypi/docsif/1.1.2/json | python -c "..."
version: 1.1.2
files: docsif-1.1.2-py3-none-any.whl 220225 uploaded 2026-11-14T09:20:00.473646Z
       docsif-1.1.2.tar.gz          3108000 uploaded 2026-11-14T09:20:02.722664Z
marker present: True
```

Task 1's automated verify (tag == release_head, run exists, `--exit-status` 0, exactly 3 successful jobs, version/marker assertions) exits 0.

TestPyPI proof: `https://test.pypi.org/pypi/docsif/1.1.2/json` serves version `1.1.2` with the same two filenames and identical byte sizes (220225 / 3108000) and the marker present — the same build reached both indexes.

## Task 2 Evidence

### PEP 740 attestation verification

The plan's literal command uses the lowercase repository URL from the PyPI docs example. `pypi-attestations 0.0.31` compares the signed repository string to the URL path with an exact, case-sensitive `!=` (`pypi_attestations/_cli.py:438-444`), and GitHub signs the canonical repository name, so the lowercase form fails:

```text
$ uvx pypi-attestations verify pypi --repository https://github.com/zhangtaolab/sif pypi:docsif-1.1.2-py3-none-any.whl
Verification failed: provenance was signed by repository "zhangtaolab/SIF", expected "zhangtaolab/sif"
(exit 1)
```

Re-running with the canonical repository case (`zhangtaolab/SIF` is the same GitHub repository; GitHub URLs are case-insensitive) verifies the cryptographic provenance and Trusted Publisher identity:

```text
$ uvx pypi-attestations verify pypi --repository https://github.com/zhangtaolab/SIF pypi:docsif-1.1.2-py3-none-any.whl
OK: docsif-1.1.2-py3-none-any.whl
(exit 0)
```

### PyPI install proof

```text
$ rm -rf /tmp/sif-release-pypi-venv && uv venv /tmp/sif-release-pypi-venv --python 3.12
Using CPython 3.12.12
$ uv pip install --python /tmp/sif-release-pypi-venv/bin/python docsif==1.1.2
Resolved 27 packages in 4.93s
Installed 27 packages in 36ms
 + docsif==1.1.2
$ /tmp/sif-release-pypi-venv/bin/sif --version
sif, version 1.1.2
(exit 0)
```

### TestPyPI install proof

```text
$ rm -rf /tmp/sif-release-testpypi-venv && uv venv /tmp/sif-release-testpypi-venv --python 3.12
Using CPython 3.12.12
$ uv pip install --python /tmp/sif-release-testpypi-venv/bin/python \
    --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple docsif==1.1.2
Resolved 27 packages in 2ms
Installed 27 packages in 47ms
 + docsif==1.1.2
$ /tmp/sif-release-testpypi-venv/bin/sif --version
sif, version 1.1.2
(exit 0)
```

Both installs used throwaway `/tmp` venvs; nothing was installed into the project environment.

## Attempt History

| Attempt | Trigger | Build distributions | Publish to TestPyPI | Publish to PyPI | Run |
|---------|---------|---------------------|---------------------|-----------------|-----|
| 1 | tag push `v1.1.2` | success 05:39:24Z -> 05:39:38Z | **failure** 05:39:41Z -> 05:39:53Z (`invalid-publisher`) | skipped | failure |
| 2 | `gh run rerun --failed` (repository case corrected to `SIF`) | success — not re-executed | **failure** 05:46:23Z -> 05:46:39Z (`invalid-publisher`) | skipped | failure |
| 3 | `gh run rerun --failed` (pending publisher delete + re-create) | success — not re-executed | **failure** 06:00:49Z -> 06:00:58Z (`invalid-publisher`) | skipped | failure |
| 4 | `gh run rerun --failed` (after maintainer created and verified the TestPyPI pending publisher: `docsif` / GitHub / `zhangtaolab/SIF` / `publish.yml` / `testpypi`) | success — not re-executed (same `databaseId`, artifact `14100657070`) | **success** 09:18:39Z -> 09:19:17Z | **success** 09:19:20Z -> 09:20:07Z | **success** |

Run URL: https://github.com/zhangtaolab/SIF/actions/runs/43562577065 (event `push`, `headSha` `c819f67228152f2544e79a864b9a9e12dbc79f69`, `headBranch` `v1.1.2`).

## Files Created/Modified

- `.planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-07-SUMMARY.md` — completion record (flipped from the attempt-3 halt).
- `.planning/STATE.md` — 17-07 complete, Phase 17 9/9, progress 12.5%, release decisions and blocker resolution.
- `.planning/ROADMAP.md` — Phase 17 plan count 9/9 and 17-07 completion note.
- `.planning/WINDOWS.md` — entries 11 (`unmet-truth`) and 12 (`unrun-verify`) marked fixed with evidence.
- No product or test file changed; no package installed into the project environment; the tag was not modified; nothing was manually uploaded.

## Decisions Made

- Reran only the failed jobs; the successful build artifact was reused in all four attempts, preserving the build-once guarantee.
- Did not create a new patch version: 1.1.2 was never partially uploaded, and attempt 4 published it cleanly, so the immutable version is legitimately consumed by a complete release.
- Used the canonical repository case for attestation verification (see Deviations) rather than weakening or skipping the check.
- Recorded both attestation outputs so the case mismatch is auditable rather than silently corrected.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Attestation verify invoked with a case-mismatched repository URL**
- **Found during:** Task 2 (provenance verification)
- **Issue:** The plan's command (`uvx pypi-attestations verify pypi`) with the lowercase repository URL exited 1 with `Verification failed: provenance was signed by repository "zhangtaolab/SIF", expected "zhangtaolab/sif"`. `pypi-attestations 0.0.31` (`_check_repository_identity`) compares the signed repository string against the URL path with an exact case-sensitive comparison, while GitHub records the canonical repository name `zhangtaolab/SIF`. The attestation itself is valid; only the expected-string casing was wrong.
- **Fix:** Re-ran the same verification with the canonical repository case, `--repository https://github.com/zhangtaolab/SIF` (same GitHub repository, since GitHub URLs are case-insensitive). Result: `OK: docsif-1.1.2-py3-none-any.whl`, exit 0.
- **Files modified:** None (verification invocation only).
- **Verification:** The canonical-case command exits 0 and the lowercase output is recorded above so the difference is auditable.
- **Committed in:** Metadata commit for this plan (no product change).

---

**Total deviations:** 1 auto-fixed (Rule 1)
**Impact on plan:** No scope change. The published bytes, tag, and workflow were untouched; the fix only corrects the verifier's expected repository string.

## Issues Encountered

- Attempts 1-3 failed at OIDC token exchange with `invalid-publisher` because the TestPyPI pending publisher was missing/mismatched. This was fully diagnosed in the halted SUMMARY; the maintainer created and verified the publisher before attempt 4, which then succeeded on the first try.
- During the rerun, an early `curl` of `https://pypi.org/pypi/docsif/1.1.2/json` returned 404 while the top-level JSON already reported 1.1.2 — a CDN propagation race. A `Cache-Control: no-cache` re-query returned 200 with the marker, and all later assertions passed.

## Known Stubs

None — this plan changed no product code, and every published-install path is proven end-to-end.

## Threat Flags

None — no new surface was introduced. The release used the existing trusted-publishing path (no secrets, no manual upload).

## Next Phase Readiness

- Phase 17 is complete (9/9 plans): the CI matrix, hygiene gate, Windows degradation smoke, and the PyPI release prerequisite all hold.
- Phase 22's MCP Registry listing prerequisite is satisfied: `docsif 1.1.2` is installable from PyPI and its published `info.description` carries the exact `<!-- mcp-name: io.github.zhangtaolab/sif -->` marker.
- Attestations verify against `https://github.com/zhangtaolab/SIF`, so downstream consumers can bind the artifact to this repository.
- No blockers remain. Next action: Phase 17 verification (`/gsd-verify-work 17`), then Phase 18.

## Self-Check: PASSED

- `git rev-parse 'v1.1.2^{commit}'` equals `release_head` `c819f67228152f2544e79a864b9a9e12dbc79f69`; `git ls-remote --tags origin 'v1.1.2^{}'` peels the same commit.
- Run `43562577065` is at `attempt: 4`, `status: completed`, `conclusion: success`; Build distributions, Publish to TestPyPI, and Publish to PyPI all `success`; `gh run view 43562577065 --exit-status` exits 0.
- `https://pypi.org/pypi/docsif/1.1.2/json` returns 200 with `info.version == "1.1.2"` and the exact marker in `info.description`.
- `https://test.pypi.org/pypi/docsif/1.1.2/json` returns 200 with the same two filenames and identical sizes.
- `pypi-attestations verify` reports `OK: docsif-1.1.2-py3-none-any.whl` (canonical repository case).
- Both `/tmp` venvs report `sif, version 1.1.2`.
- No product/test file changed; the tag was not moved; no rebuild and no manual upload occurred.

---
*Phase: 17-engineering-foundation-ci-matrix-hygiene-pypi*
*Completed: 2026-11-14*
