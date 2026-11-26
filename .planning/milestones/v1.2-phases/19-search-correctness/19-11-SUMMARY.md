---
phase: 19-search-correctness
plan: 11
subsystem: search
tags: [bm25, min-score, score-map, hybrid, bench, evidence, decision, gap-closure, uat, corr-03, g-19-2]

# Dependency graph
requires:
  - phase: 19-search-correctness
    provides: "19-10 (the plan this one depends on, so the plan base lies beyond its three commits); 19-05: the min_score predicate the evidence records (fourth truth of 19-05-PLAN.md) and the B0 comparison command the capture follows; the committed saved runs bench/b0.json and bench/b1.json (corpus fingerprint 8c006123784348d1)"
provides:
  - "bench/g19-2-min-score.json: the before half of the G-19-2 evidence (probe rows for Saltiv Protocol Notes, the outcomes of --min-score 0.12 and 0.23, the BM25 leg of the hybrid path at 0.3 and 0.5, the B0 and B1 comparison deltas) with head set to the plan base, and the recorded decision"
  - "A committed record that the unchanged tree at the plan base reproduces every value measured during planning at 6e28002"
  - "The operator's decision monotone-map, in the artifact's decision field and on this SUMMARY's Decision line, which plan 19-12 Task 1 requires before any source change"
  - "Plan base record left in place so the validator and the scope gate can be re-run"
affects: ["19 (plan 19-12 and UAT test 2)", "22 (the min_score item of the Phase 22 UI review, once plan 19-12 lands)"]

# Actuals (#2632): tokens are chars/4 over the unified diff of the one changed file, the artifact, from the plan base to the last task commit; this SUMMARY is not counted.
# commits is measured from the ledger (.git/gsd-plan-head-before-19-11); this SUMMARY is committed after them.
actuals:
  tokens: 518
  tasks: 3
  commits: 2
  plan_head_before: 4ac6262d506f8441bcbb69fb207f3cabcc57f4e9
  plan_head_after: dbb82b595f5701f77646ca55f1e1dfcb51b0d81f

tech-stack:
  added: []
  patterns:
    - "Before-evidence first: a behaviour that a decision may change is captured on the unchanged tree and committed before the decision is asked, with head set to the recorded plan base and every value pinned in a validator"
    - "A blocking-human decision is written into the evidence artifact's decision field and copied onto a whole Decision: line of the SUMMARY, so the plan that implements it gates on two records that a later verifier can read"

key-files:
  created:
    - .planning/milestones/v1.2-phases/19-search-correctness/bench/g19-2-min-score.json
  modified: []

key-decisions:
  - "monotone-map: the operator chose a monotone BM25 score with a matching threshold, so --min-score removes the weaker matches and keeps the best, and the BM25 leg of sif query --min-score keeps the matches whose own score is at least the threshold. Plan 19-12 implements it; this plan records the decision and changes no behaviour."

patterns-established:
  - "A one-way decision on a published output contract gets a plan of its own before the implementation: before-evidence on the unchanged tree, a blocking-human checkpoint without auto_select, and only then a plan led by its tracer"

requirements-completed: [CORR-03]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "bench/g19-2-min-score.json records, on the unchanged tree at the plan base, the probe scores (rank 1 Saltiv Protocol Notes 0.10570305094775757, rank 2 Qelron Protocol Notes 0.1527108535938998), that --min-score 0.12 keeps only the weaker match and 0.23 keeps nothing, that the BM25 leg of the hybrid path returns no row at 0.3 or at 0.5, and that the B0 and B1 comparisons both report n 100 and mean 0.0"
    requirement: CORR-03
    verification:
      - kind: other
        ref: "Task 1 validator (19-11-PLAN.md Task 1, first automated block), re-run at dbb82b5: before-evidence OK, exit 0"
        status: pass
    human_judgment: false
  - id: D2
    description: "No file outside .planning/ changed since the plan base: src/sif/search/bm25.py, src/sif/cli/commands/search.py, every test and every doc are byte-identical to it, the committed B0, B1 and D-12 bench artifacts are not rewritten, and the full quality suite passes"
    requirement: CORR-03
    verification:
      - kind: other
        ref: "scope gate (19-11-PLAN.md Task 1, second automated block): exit 0 with an empty changed set at dbb82b5; git diff --quiet of src, tests and docs against the plan base exits 0"
        status: pass
      - kind: other
        ref: "ruff check src tests and ruff format --check src tests at dbb82b5: All checks passed!, 237 files already formatted"
        status: pass
      - kind: other
        ref: "full pytest suite at dbb82b5 with SIF_DB_PATH and SIF_CACHE_DIR in a scratch directory: 3286 passed, 1 skipped, 27 warnings in 206.11s, coverage 95.09%, fail_under=90 reached"
        status: pass
    human_judgment: false
  - id: D3
    description: "The operator decided among monotone-map, describe-current and deprecate-flag with the evidence and the full scope in front of them, including the BM25 leg of sif query --min-score, and nothing was selected automatically"
    requirement: CORR-03
    verification:
      - kind: manual_procedural
        ref: "checkpoint:decision of Task 2 (gate blocking-human, no auto_select): the first executor stopped at it and the answer that resumed the plan was monotone-map"
        status: pass
    human_judgment: true
    rationale: "Which behaviour --min-score should have is the operator's call, because it changes a published output contract, and no test can make it. The executor did not see the answer directly: the first executor returned the checkpoint and stopped, and this continuation received monotone-map in its dispatch prompt, which states that the operator gave it directly to the orchestrator and that nothing was selected automatically. The executor recorded that answer and checked the record (D4); it did not choose. If the operator wants to confirm or amend the choice, UAT test 2 of this phase is the place, and the plan is explicit that another option leaves 19-12 unexecuted and goes back to the orchestrator for re-planning."
  - id: D4
    description: "The chosen option is recorded in the evidence artifact and nothing else in the artifact changed; this SUMMARY copies the id onto a whole Decision: line and quotes the committed artifact byte for byte"
    verification:
      - kind: other
        ref: "Task 3 gate (19-11-PLAN.md Task 3): decision recorded: monotone-map and artifact otherwise as committed, exit 0 before the commit and again after it at dbb82b5"
        status: pass
      - kind: other
        ref: "Plan 19-12 Task 1 gate, first half, run on this file after it was written and before it was committed: grep -qxF 'Decision: monotone-map' exits 0, and the fenced block under Before evidence equals git show HEAD:bench/g19-2-min-score.json byte for byte. The command that makes this commit runs both and is refused if either fails"
        status: pass
    human_judgment: false

duration: 11min
completed: 2026-11-26
status: complete
---

# Phase 19 Plan 11: G-19-2 Before-Evidence and the BM25 Min-Score Decision Summary

**On the unchanged tree at plan base `4ac6262`, `sif search search --min-score` is on record removing the best BM25 match first (0.12 drops the rank-1 match at 0.1057 and keeps the rank-2 match at 0.1527; 0.23 keeps nothing) and the BM25 leg behind `sif search query --min-score` returns no row at 0.3 or 0.5; the operator chose `monotone-map` at a blocking-human checkpoint, and no behaviour changed in this plan.**

## Performance

- **Duration:** 11 min (this continuation, from the start of Task 3 to this SUMMARY)
- **Started:** 2026-11-26T02:14:19Z (this continuation). Task 1's plan base record dates from about 01:28Z and its commit `043db46` from 01:31:24Z. The first executor's start time is not known to this executor.
- **Completed:** 2026-11-26T02:26Z (the time of writing; the commit timestamp is authoritative)
- **Tasks:** 3/3
- **Files modified:** 1 (the evidence artifact: Task 1 created it and Task 3 changed one field), plus this SUMMARY

Environment: Python 3.13.9, pytest 9.1.1, ruff 0.15.11, branch `gsd/phase-24-reverify`, main checkout, no worktree.

## Plan Base and Precondition

- Plan base: `4ac6262d506f8441bcbb69fb207f3cabcc57f4e9`, the parent of the first commit with the `(19-11)` scope. Task 1 Step 0 recorded it at `.git/gsd-plan-19-11-base`, it equals `probe.before.head`, and it is left in place so the validator and the scope gate can be re-run.
- Precondition of Task 3, checked read-only before the edit: the continuation prompt names `monotone-map`, one of the three option ids, and the artifact existed with a `probe.before` half, no after half and the pending marker as its `decision`.
- Execution split: the first executor ran Task 1 and returned the Task 2 checkpoint. This continuation ran Task 3 and wrote this SUMMARY.

## Accomplishments

- `bench/g19-2-min-score.json` is committed with the before half of the G-19-2 evidence, captured by Task 1 on the unchanged tree: the probe rows, both threshold outcomes, the rows of the hybrid path's BM25 leg at two thresholds, and the B0 and B1 comparison deltas. The Task 1 validator confirms every recorded value against the values measured during planning at commit `6e28002`.
- The Task 2 checkpoint reached the operator and stopped there, although this project's auto mode is on (`workflow.auto_advance: true`). The answer was `monotone-map`.
- Task 3 replaced the pending marker with that id. Its gate reads the artifact and its committed copy alone and confirms that the id is one of the three and that nothing else in the artifact changed.
- No file outside `.planning/` differs from the plan base, and the full quality suite passes.

## Before evidence

The committed artifact at `dbb82b5`, byte for byte. SHA-256 of the file: `5f74a35ff86a1297a76b96136d9b2bc5492cafab5fce6e00fa5f8195d859b00f`.

```json
{
  "gap": "G-19-2",
  "plans": [
    "19-11",
    "19-12"
  ],
  "decision": "monotone-map",
  "score_map": {
    "before": "1/(1+|bm25|)",
    "after": "|bm25|/(1+|bm25|)"
  },
  "probe": {
    "query": "Saltiv Protocol Notes",
    "index": "tests/fixtures/bench/corpus as collection bench-fixture (150 documents, BM25 only)",
    "before": {
      "head": "4ac6262d506f8441bcbb69fb207f3cabcc57f4e9",
      "rows": [
        [
          1,
          "Saltiv Protocol Notes",
          0.10570305094775757
        ],
        [
          2,
          "Qelron Protocol Notes",
          0.1527108535938998
        ]
      ],
      "min_score_0_12": [
        [
          1,
          "Qelron Protocol Notes",
          0.1527108535938998
        ]
      ],
      "min_score_0_23": []
    }
  },
  "hybrid_bm25_leg": {
    "command": "sif search query --min-score: the BM25 leg of the hybrid path, read through HybridSearcher.search without a vector leg (limit 10)",
    "before": {
      "rows": [
        [
          1,
          "Saltiv Protocol Notes",
          0.10570305094775757
        ],
        [
          2,
          "Qelron Protocol Notes",
          0.1527108535938998
        ]
      ],
      "min_score_0_3": [],
      "min_score_0_5": []
    }
  },
  "bench_compare": {
    "b0": {
      "before": {
        "mean": 0.0,
        "helped": 0,
        "hurt": 0,
        "unchanged": 100,
        "n": 100,
        "noise_floor": 0.01
      }
    },
    "b1": {
      "before": {
        "mean": 0.0,
        "helped": 0,
        "hurt": 0,
        "unchanged": 100,
        "n": 100,
        "noise_floor": 0.01
      }
    }
  }
}
```

- **Probe.** For `Saltiv Protocol Notes` on the bench-fixture index, rank 1 is `Saltiv Protocol Notes` with score 0.10570305094775757 and rank 2 is `Qelron Protocol Notes` with 0.1527108535938998: the better match shows the lower score.
- **Thresholds.** `--min-score 0.12` keeps only `Qelron Protocol Notes`, re-numbered to rank 1. `--min-score 0.23` keeps nothing.
- **BM25 leg of the hybrid path.** With no threshold it returns the same two rows; at 0.3 and at 0.5 it returns no row, so `sif search query --min-score` silently loses that leg at ordinary thresholds.
- **Bench comparisons.** Against the committed B0 and B1 runs, both comparisons report n 100, mean 0.0, helped 0, hurt 0 and unchanged 100 at a noise floor of 0.01: the unchanged tree reproduces the recorded ranking.
- **Not measured here.** `score_map.after` names the map that `monotone-map` will bring; Task 1 wrote it as part of the artifact's design. The artifact has no after half. Plan 19-12 measures it.

## Task Commits

Each task that edits was committed atomically, by explicit path, on `gsd/phase-24-reverify`:

1. **Task 1: Record the G-19-2 before-evidence on the unchanged tree** - `043db46` (docs; first executor)
2. **Task 2: Decide how BM25 `--min-score` should behave** - no commit: a `checkpoint:decision` with gate `blocking-human` makes no edit; answered `monotone-map`
3. **Task 3: Record the chosen option in the evidence artifact** - `dbb82b5` (docs; this continuation, one line changed)

**Plan metadata:** this SUMMARY is committed separately, immediately after it is written (docs: complete 19-11 plan).

## Gate Evidence

All commands ran in the main checkout with the checkout root as working directory.

| Gate | Outcome |
|------|---------|
| **Task 3, before the commit (HEAD `043db46`)** | |
| Precondition, read-only | met: `monotone-map` is one of the three ids; `probe.before` present; no after half; decision was the pending marker |
| The plan's write command, with `CHOSEN_ID` replaced by `monotone-map` | exit 0; `git diff --numstat` reports `1 1` |
| Task 3 gate, verbatim | `decision recorded: monotone-map`, `artifact otherwise as committed`, exit 0 |
| **Task 3, after the commit (HEAD `dbb82b5`)** | |
| Task 3 gate, verbatim | `decision recorded: monotone-map`, `artifact otherwise as committed`, exit 0 |
| Commit checks | staged set was exactly the artifact; no file deleted |
| **Plan-level verification** | |
| The artifact parses (`python -c "import json; json.load(open(...))"`) | exit 0 |
| Task 1 validator, verbatim | `before-evidence OK`, exit 0 |
| Task 3 gate, verbatim | `decision recorded: monotone-map`, `artifact otherwise as committed`, exit 0 |
| Scope gate (Task 1, second automated block), verbatim | exit 0; changed set empty against plan base `4ac6262` |
| `git diff --quiet` of `src/sif/search/bm25.py` and `src/sif/cli/commands/search.py`, base against HEAD | exit 0 |
| `git diff --quiet` of `src`, `tests` and `docs`, base against HEAD and HEAD against the working tree | exit 0 and exit 0 |
| `git diff --quiet` of `bench/b0.json`, `bench/b1.json` and `bench/d12-verdict.json`, base against HEAD | exit 0 |
| `git diff --quiet 6e28002 HEAD -- src/sif/search/bm25.py` | exit 0 |
| Paths that differ from the plan base | one: `bench/g19-2-min-score.json` (added) |
| `gsd-tools check evaluation-scope --plan 19-11 --commits-only --raw` | `status: resolved`; commits `043db46` and `dbb82b5`; `changedFiles` is empty because the only changed file is a planning artifact |
| **Quality suite (`CLAUDE.md`), at `dbb82b5`** | |
| `ruff check --no-cache src tests` | All checks passed! |
| `ruff format --check --no-cache src tests` | 237 files already formatted |
| `pytest`, full suite | exit 0: 3286 passed, 1 skipped, 27 warnings in 206.11s; coverage 95.09%; `Required test coverage of 90.0% reached` |
| Real model cache, `~/Library/Caches/sif` | 129 entries before and after; path, type, size and modification time of every entry identical |
| Default database directory, `~/Library/Application Support/sif` | 4 entries before and after; identical |

- The suite ran with `SIF_DB_PATH` and `SIF_CACHE_DIR` pointing into a `mktemp -d` directory, with `NO_COLOR=1` and `PYTHONPATH=src`. That applies to the test run the isolation the dispatch rules set for `sif` commands, so that no test could write into the default database or the real model cache. The reranker tests, which plan 19-10 records as T-19-36, construct `CrossEncoderReranker()` without a cache directory; that default resolves through `get_settings().get_cache_dir()`, so their lock file landed at `models/.lock/cross-encoder___ms-marco-MiniLM-L-6-v2` inside the scratch directory. No `sif` command ran in this continuation.
- The pass and skip counts equal the ones recorded at the end of plan 19-10 (3286 passed, 1 skipped, 27 warnings). Coverage read 95.16% there and 95.09% here. The environment variables are the one known difference between the two setups; the difference was not analysed further. The 27 warnings are `ResourceWarning: unclosed database`, as before.
- `ty check` did not run: it is not part of the suite `CLAUDE.md` names, and no source file differs from the plan base.

## Files Created/Modified

- `.planning/milestones/v1.2-phases/19-search-correctness/bench/g19-2-min-score.json` - the G-19-2 evidence artifact. Task 1 created it with the before half (`probe.before`, `hybrid_bm25_leg.before`, `bench_compare.*.before`) and the pending marker. Task 3 replaced that marker with `monotone-map`; no other value changed.
- `.planning/milestones/v1.2-phases/19-search-correctness/19-11-SUMMARY.md` - this file.

Nothing under `src/`, `tests/` or `docs/` was created, modified or deleted. No committed bench run was rewritten.

## Decisions Made

Decision: monotone-map

- **What was decided.** BM25 gets a monotone score with a matching threshold. The displayed score rises with relevance, and `--min-score` keeps the rows at or above the threshold, so the weaker matches are removed and the best survives. As a consequence the BM25 leg of `sif search query --min-score` keeps the stronger matches instead of returning nothing at ordinary thresholds. Ranking does not change where no threshold is set.
- **What the choice carries**, as the checkpoint's option statement sets it out: every BM25 score a user or client sees changes value (an old value `v` reads `1 - v`); truth 4 of `19-05-PLAN.md` is amended and seven tests re-pinned; two golden values are regenerated; a caller of `sif search query --min-score` that relied on the BM25 leg being emptied now receives the fused page; a threshold of 1 or more returns nothing from `sif search search`.
- **Where it is recorded.** In the `decision` field of `bench/g19-2-min-score.json` (commit `dbb82b5`) and on the line above. Plan 19-12 Task 1 requires both to read `monotone-map` before any source changes.
- **Who decided, and how the executor knows.** The operator. The first executor returned the Task 2 checkpoint, which declares no `auto_select` and carries `gate="blocking-human"`, and stopped there. This continuation received the answer `monotone-map` in its dispatch prompt, which states that the operator gave it directly to the orchestrator and that nothing was selected automatically. The executor recorded that answer and checked the record; it did not choose.
- **Not decided here.** The implementation. It belongs to plan 19-12, which starts from this record.

## Deviations from Plan

The plan ran as written: no gate was weakened, skipped or re-run with different settings, and no product default changed. One addition, required by `CLAUDE.md` rather than by the plan:

1. **[Addition, `CLAUDE.md`] The full quality suite ran after the last task.** `CLAUDE.md` requires `ruff check src tests`, `ruff format --check src tests` and `pytest` after every plan. The plan does not list them, because it changes no behaviour. All three ran at `dbb82b5` and passed, with the database and cache paths in a scratch directory (see Gate Evidence). The two ruff commands ran with `--no-cache`, which changes nothing they check.

**Total deviations:** 1 addition, no auto-fix. **Impact on plan:** none on scope, gates or behaviour; the scope gate reports an empty changed set.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None. No test is skipped by this plan and every automated `<verify>` command ran. The one skipped test and the 27 warnings in the suite are the same as at the end of plan 19-10.

## Next Phase Readiness

- Plan 19-12 can start as written: both records of the decision read `monotone-map`, the artifact has its before half and no after half, and its `probe.before.head` is this plan's base. Its first gate re-runs both checks before any edit.
- Plan 19-12 adds the after half of the artifact.
- Nothing in this plan changes behaviour, so no verification of another phase goes stale from it.
- Not done by this executor, by instruction: `STATE.md` and `ROADMAP.md` are untouched. `REQUIREMENTS.md` does not exist in this repository (commit `4920fb1e` removed it for the v1.2 milestone), so the CORR-03 checkbox was not touched either. The orchestrator owns those writes.

## Threat Model Disposition

- T-19-28 (repudiation, integrity of the before-evidence): mitigated. `probe.before.head` equals the recorded plan base, the validator re-ran green at `dbb82b5` with every pin intact, and the scope gate shows `src/sif/search/bm25.py` byte-identical to the base and to `6e28002`.
- T-19-29 (tampering, decision integrity): mitigated. The checkpoint declares no `auto_select` and carries `gate="blocking-human"`, and the first executor stopped at it under auto mode. The Task 3 command wrote only an id that is one of the three and that was still pending, and the gate read the artifact and its committed copy alone. Both records now read `monotone-map`; plan 19-12 Task 1 checks that they agree.
- T-19-30 (denial of service, default database and caches): mitigated for this continuation. No `sif` command ran, and Task 3 used one command that imports only the standard library. The quality suite ran with both paths in a scratch directory, and the metadata snapshots of the real cache and the default database directory are identical before and after. The scratch directory is removed.
- T-19-SC (package installs): no package was installed, added or removed; `pyproject.toml` and `uv.lock` are untouched.

No threat flags: no file adds an endpoint, auth path, file-access pattern or schema change, and no file outside `.planning/` changed.

## Self-Check: PASSED

Run at `dbb82b5`, immediately before this SUMMARY was written:

- Files: `bench/g19-2-min-score.json` is present on disk, and its SHA-256 equals that of the committed blob. Every JSON field the plan's artifacts table names is present (`probe.before.rows`, `min_score_0_12`, `min_score_0_23` and `head`; `hybrid_bm25_leg.before.rows`, `min_score_0_3` and `min_score_0_5`; `bench_compare.b0.before` and `b1.before`; `decision`), and the artifact has no after half.
- Commits: `043db46` and `dbb82b5` are ancestors of HEAD, and `git rev-list --count 4ac6262..HEAD` is 2.
- `gsd-tools check evaluation-scope --plan 19-11 --commits-only` resolved the same two commits.
- Plan base record present and equal to `4ac6262d506f8441bcbb69fb207f3cabcc57f4e9`.
- Both acceptance criteria of Task 3 and every command of the plan-level verification passed (see Gate Evidence).
- Working tree clean of tracked changes; the only untracked paths are the ones that predate this plan.

Not covered by that run, because this file did not exist yet: the `Decision:` line and the quoted artifact above. Two checks run on this file after it is written and before it is committed, by the command that makes the commit, which is refused if either fails: `grep -qxF 'Decision: monotone-map'`, the first half of the 19-12 Task 1 gate; and a byte comparison of the fenced block under Before evidence with `git show HEAD:bench/g19-2-min-score.json`. Their outcome is in the executor's return message, not in this file.

---
*Phase: 19-search-correctness*
*Completed: 2026-11-26*
