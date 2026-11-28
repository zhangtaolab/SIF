---
phase: 25-contract-freeze-feasibility-spike
plan: 02
subsystem: research-spike
tags: [contract-freeze, sha256-manifest, wire-goldens, mcp-tools, query-input, runtime-dependencies, directional-signal, evidence]

# Dependency graph
requires:
  - phase: 25-01
    provides: "raw compat_result.json, delta_result.json, start manifest/tests/git, and the committed query-only anchor table"
provides:
  - "Authoritative Phase 25 verdict JSON, 36-row paired delta CSV, contract-freeze report, and coverage declaration, all from one in-memory dictionary"
  - "Byte-identical START/END 11-file SHA-256 manifest matching the 25-CONTEXT expected table, with 13 passed shipped MCP tests at both ends"
  - "Directional-signal stop/go record through gsd_run state record-session; Phase 26/27 unlocked"
affects: [phase-26, phase-27]

# Actuals (#2632) — same chars/4 scale as the plan estimate.
actuals:
  tokens: 20863
  tasks: 3
  commits: 2
  plan_head_before: 5fb2712d7a9840de22877b13631c93f16e3665ba
  plan_head_after: d86eaa264e87560a8760a11ba93e640000c7c4f3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "One in-memory verdict dictionary is the only source for JSON, CSV, and Markdown (D-14); renderers never recompute a metric"
    - "START/END SHA-256 manifest over 11 frozen paths plus the two shipped MCP test files run with --no-cov"
    - "Stop/go verdict crosses into project state only through gsd_run state record-session"

key-files:
  created:
    - .planning/phases/25-contract-freeze-feasibility-spike/bench/spike-verdict.json
    - .planning/phases/25-contract-freeze-feasibility-spike/bench/spike-delta.csv
    - .planning/phases/25-contract-freeze-feasibility-spike/25-CONTRACT-FREEZE.md
    - .planning/phases/25-contract-freeze-feasibility-spike/COVERAGE.md
  modified:
    - .planning/STATE.md

key-decisions:
  - "The verdict JSON is authoritative; the CSV and Markdown are rendered from the same in-memory dictionary, so they cannot drift."
  - "The measured commit count is recorded at two points: 20 at the Task 1 freeze-check HEAD (5fb2712) and 21 at the final render HEAD (fb5ac0f); CONTEXT's 4 and research's 7 are stale."
  - "The directional-signal branch was taken as the literal D-08 rule dictates (mean +0.130203 > 0 AND helped 6 > hurt 0); no 25-SPIKE-VERDICT.md was created."
  - "The frozen uv.lock was restored to its committed HEAD content after an out-of-band Aliyun-mirror uv rewrite changed it after Wave 1."

requirements-completed: [SPK-03, CTR-01, CTR-02]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "START and END 11-file SHA-256 manifests are byte-identical and match all 11 expected hashes; both frozen ends report 13 passed with --no-cov"
    verification:
      - kind: other
        ref: "diff -u .planning/tmp/phase-25/start-manifest.sha256 .planning/tmp/phase-25/end-manifest.sha256; .venv/bin/python -m pytest tests/unit/mcp/test_wire_transcripts.py tests/unit/mcp/test_packaging.py -q --no-cov"
        status: pass
    human_judgment: false
  - id: D2
    description: "bench/spike-verdict.json is authoritative; bench/spike-delta.csv has 36 rows in fixture order matching the JSON; 25-CONTRACT-FREEZE.md renders the same values"
    verification:
      - kind: other
        ref: "python assertions over verdict JSON, CSV rows, and report literals"
        status: pass
    human_judgment: false
  - id: D3
    description: "COVERAGE.md carries the exact no-external-API declaration and passes the api-coverage gate"
    verification:
      - kind: other
        ref: "gsd_run check api-coverage-verify-pre 25-contract-freeze-feasibility-spike"
        status: pass
    human_judgment: false
  - id: D4
    description: "Directional-signal verdict recorded through gsd_run state record-session; no 25-SPIKE-VERDICT.md remains"
    verification:
      - kind: other
        ref: "python assert STATE.md contains 'directional signal recorded'; test ! -e 25-SPIKE-VERDICT.md"
        status: pass
    human_judgment: false
  - id: D5
    description: "Working-tree proof: src/, tests/, pyproject.toml, uv.lock zero diff; the three whitelisted untracked planning docs explained"
    verification:
      - kind: other
        ref: "test -z \"$(git status --porcelain -- src tests pyproject.toml uv.lock)\"; grep the three docs in 25-CONTRACT-FREEZE.md"
        status: pass
    human_judgment: false
  - id: D6
    description: "uv.lock restored to the committed HEAD content after an out-of-band Aliyun-mirror uv rewrite changed it after Wave 1"
    verification:
      - kind: other
        ref: "shasum -a 256 uv.lock == b0175d451e4f8c127da90ffeef94d049a5f181d36743076eaae42b102ea5a308; git diff v1.2.5..HEAD -- uv.lock empty"
        status: pass
    human_judgment: true
    rationale: "An environmental rewrite of the frozen lockfile was discarded by restoring HEAD; a human should confirm the restore was intended and that no mirror-pinned lock is wanted."

duration: ~7 min
completed: 2026-11-28
status: complete
---

# Phase 25 Plan 02: Contract Freeze & Feasibility Spike — Evidence Assembly and Verdict

**Phase 25 freezes the MCP/packaging contract at v1.2.5 with a byte-identical 11-file SHA-256 manifest and 13 passing shipped tests, and records a directional-signal verdict (mean paired nDCG@10 +0.130203, helped 6 / hurt 0 / unchanged 30, N=36) through the GSD state seam.**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-11-28T00:47:04Z
- **Completed:** 2026-11-28T00:54Z
- **Tasks:** 3
- **Files modified:** 4 committed evidence artifacts created; STATE.md modified via `gsd_run state record-session`; 5 gitignored scratch inputs/outputs under `.planning/tmp/phase-25/`

## Accomplishments

- **The contract is proven byte-identical at both ends.** The END `shasum -a 256` manifest is byte-identical to the START manifest (`diff -u` empty), both contain exactly 11 lines, and all 11 hashes equal the expected table in `25-CONTEXT.md`. The two shipped MCP test files report `13 passed` at both ends with `--no-cov`; `git diff v1.2.5..HEAD` under the frozen paths is empty and the working tree has no change there.
- **The contract facts are machine-readable.** `contract-facts.json` records exactly seven tools in pinned `register_tools()` order (`query`, `get`, `multi_get`, `status`, `metadata`, `lex_search`, `vec_search`), the `QueryInput` field list with `has_anchor_field: false`, five goldens, all 13 runtime dependencies, `llama-cpp-python>=0.3.35` in the `all` extra, and the `0.3.35` lock resolution.
- **The evidence trio is same-source.** `bench/spike-verdict.json` (authoritative, 1,218 lines) embeds the full decision, rule, arms, queries, delta, reproducibility, compatibility, contract-freeze, working-tree, environment, evidence, notes, and the 36 raw rows. `bench/spike-delta.csv` has the exact 14-column header and 36 data rows in fixture order; `25-CONTRACT-FREEZE.md` (575 lines) renders the same literals. No renderer recomputes a metric.
- **The compatibility evidence is reviewable.** The locked 0.3.35 load failure is recorded as `ValueError` with the native `unknown model architecture: 'lfm3'` reason; the isolated 0.3.37 attempt records the non-empty greedy generation verbatim, the ChatML-style chat template, and the measured embed/rerank impact (both versions accept `embedding=True`, 1024 dimensions). No absolute user path or raw log was committed.
- **The directional-signal verdict is recorded through the state seam.** `gsd_run state record-session` wrote `Phase 25 complete — directional signal recorded; Phases 26/27 unlocked` with `--resume-file` pointing at `bench/spike-verdict.json`. `25-SPIKE-VERDICT.md` is absent, and the ROADMAP Phase 25 checkbox was not edited.
- **The no-half-finished-code proof is complete.** The final `git status --porcelain` is pasted into the report and every entry is explained; `src/`, `tests/`, `pyproject.toml`, and `uv.lock` have zero changes. `COVERAGE.md` passes the api-coverage gate with the exact reasoned no-external-API declaration.

## Task Commits

Each task was committed atomically:

1. **Task 1: Tracer — byte-identical contract proof** — no commit (all four outputs are gitignored scratch under `.planning/tmp/phase-25/`, D-13)
2. **Task 2: Assemble the authoritative verdict JSON, delta CSV, contract-freeze report, and coverage declaration** — `fb5ac0f` (feat)
3. **Task 3: Apply the directional-signal rule, record stop/go state, prove the tree is clean** — `d86eaa2` (docs)

**Plan metadata:** committed separately after this file (docs commit for this SUMMARY).

## Files Created/Modified

- `.planning/phases/25-contract-freeze-feasibility-spike/bench/spike-verdict.json` — authoritative Phase 25 verdict and evidence.
- `.planning/phases/25-contract-freeze-feasibility-spike/bench/spike-delta.csv` — 14-column, 36-row paired delta table in fixture order.
- `.planning/phases/25-contract-freeze-feasibility-spike/25-CONTRACT-FREEZE.md` — freeze anchor, START/END manifests, test proof, contract facts, SPK-01/SPK-02 evidence, working-tree statement, runbook, limitations.
- `.planning/phases/25-contract-freeze-feasibility-spike/COVERAGE.md` — reasoned no-external-API declaration.
- `.planning/STATE.md` — session record written only by `gsd_run state record-session`.
- `.planning/tmp/phase-25/assemble_evidence.py` — throwaway single-source generator with `--stage initial|final` (gitignored).
- `.planning/tmp/phase-25/end-manifest.sha256`, `end-tests.txt`, `end-git.txt`, `contract-facts.json` — phase-end freeze inputs (gitignored).

## Decisions Made

- The verdict JSON is the authoritative artifact; CSV and Markdown are rendered from the same in-memory dictionary at generation time, per D-14.
- The final report records both the Task 1 freeze-check measurement (HEAD `5fb2712`, 20 commits since v1.2.5) and the final render measurement (HEAD `fb5ac0f`, 21 commits), so the advance caused by the evidence commit is explicit rather than hidden.
- The directional-signal branch was followed literally; no stop-loss document was created and the ROADMAP checkbox was left untouched for the orchestrator.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Restored the frozen `uv.lock` after an out-of-band mirror rewrite**
- **Found during:** Task 1 precondition (before the END manifest could be computed)
- **Issue:** The working-tree `uv.lock` hashed to `5978a407…`, not the expected `b0175d45…`. It had been regenerated at 08:40 (after Wave 1) against the user's global Aliyun mirror (`~/.config/uv/uv.toml`), rewriting registry URLs and downgrading `revision` 5 → 3. The committed HEAD blob still hashed to the expected value, and this is one of the 11 frozen files the plan requires to be byte-identical.
- **Fix:** Ran the sanctioned specific-file `git checkout -- uv.lock` (never a blanket reset) to restore the committed content. The plan's hard-failure rule forbids rebaselining the expected hashes or editing a manifest; restoring the committed frozen file makes the comparison genuinely pass.
- **Files modified:** `uv.lock` (restored to HEAD; no dependency or version change)
- **Verification:** `shasum -a 256 uv.lock` == `b0175d451e4f8c127da90ffeef94d049a5f181d36743076eaae42b102ea5a308`; `git diff --exit-code v1.2.5..HEAD -- uv.lock` empty; `git status --porcelain -- pyproject.toml uv.lock src/sif/mcp tests/unit/mcp` empty.
- **Committed in:** No new commit — the restore returns the file to its committed state.

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Without the restore, Task 1's END manifest could not match the START manifest or the expected table. The restore changes no dependency, version, or product code; the committed contract is exactly the v1.2.5 baseline. Flagged for human confirmation in coverage D6.

## Issues Encountered

- **Stale commit-count assumptions.** The plan's assumption text said 10 commits at planning time, CONTEXT said 4, research said 7; the execution-time measurement is 20 at the Task 1 freeze check and 21 at the final render. Both measured values are recorded, per Pitfall 8.
- **The `Shasum` first-line fidelity bug.** The generator's initial `git status --porcelain` capture stripped the leading status column of the first line; fixed to preserve the exact porcelain bytes before the committed artifacts were written.
- **Full suite intentionally not run.** This phase changes no file under `src/`, `tests/`, `pyproject.toml`, or `uv.lock`, and a full `pytest` run touches the real model cache (25-RESEARCH.md Pitfall 7). The plan records the reasoned CLAUDE.md waiver; `/gsd-execute-phase` runs the full quality suite at plan completion.

## User Setup Required

None — the human-supplied GGUF path was obtained during Wave 1; this plan required no external service configuration.

## Next Phase Readiness

- Phase 26/27 are unlocked by a recorded directional signal: mean paired nDCG@10 delta +0.130203, helped 6 / hurt 0 / unchanged 30, N=36, noise floor 0.027778.
- The authoritative evidence is `bench/spike-verdict.json`; the freeze proof is in `25-CONTRACT-FREEZE.md`; the coverage gate is green.
- Remaining orchestrator bookkeeping: mark SPK-03/CTR-01/CTR-02 complete, advance the plan counter, and tick the ROADMAP Phase 25 checkbox (not done by this plan per the dispatch constraints).

## Known Stubs

None — no hardcoded placeholders, TODO/FIXME markers, or unwired data sources were introduced.

## Threat Flags

None — no new network endpoint, auth path, schema change, or trust boundary was introduced beyond the plan's threat model (T-25-06..T-25-SC). The committed evidence contains no absolute user path (asserted at generation time).

## Self-Check: PASSED

- `bench/spike-verdict.json`, `bench/spike-delta.csv`, `25-CONTRACT-FREEZE.md`, and `COVERAGE.md` exist and are committed at `fb5ac0f` (final render at `d86eaa2`).
- Task commits `fb5ac0f` and `d86eaa2` are ancestors of HEAD.
- START and END manifests are byte-identical, 11 lines each, and match all 11 expected hashes.
- Both shipped MCP test files report 13 passed with `--no-cov` at both ends.
- `src/`, `tests/`, `pyproject.toml`, and `uv.lock` have zero working-tree changes.
- STATE.md and ROADMAP.md were never hand-edited; the session record went through `gsd_run state record-session`.

---
*Phase: 25-contract-freeze-feasibility-spike*
*Completed: 2026-11-28*
