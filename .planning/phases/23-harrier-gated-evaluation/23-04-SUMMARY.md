---
phase: 23-harrier-gated-evaluation
plan: 04
subsystem: search-eval
tags: [harrier, qwen3, verdict-artifact, benchmarking-docs, keep-qwen3, validation-record]

# Dependency graph
requires:
  - phase: 23-harrier-gated-evaluation
    plan: "01"
    provides: "Per-language and leg-language held-out gates"
  - phase: 23-harrier-gated-evaluation
    plan: "02"
    provides: "Two-sided verdict rule and MIN_HELDOUT_FOR_EPSILON_WIN"
  - phase: 23-harrier-gated-evaluation
    plan: "03"
    provides: "Two-arm runbook, identity gate, adequacy preflight, artifact writer"
provides:
  - "Committed keep-qwen3 aggregate verdict artifact from the real EN+ZH two-arm run"
  - "docs/benchmarking.md Phase 23 Harrier evidence section"
  - "Recorded manual verification outcome; conditional flip and zero-delta proof remain pending"
affects: [23-05, 23-06, 24]

actuals:
  tokens: 8872
  tasks: 3
  commits: 1
  plan_head_before: b7ddc024141a36676f05f0fb3cdb471241cc1ecb
  plan_head_after: 0b9c143e414892e6537d1896b0cecc412c8a0349

tech-stack:
  added: []
  patterns:
    - "Aggregate-only evidence commit: the verdict artifact and a hand-written benchmarking section are the deliverables; arm DBs and saved runs stay in ignored scratch storage"

key-files:
  created:
    - .planning/phases/23-harrier-gated-evaluation/bench/harrier-verdict.json
  modified:
    - docs/benchmarking.md
    - .planning/phases/23-harrier-gated-evaluation/23-VALIDATION.md

key-decisions:
  - "The real two-arm run recorded keep-qwen3: overall held-out mean delta +0.009430 at N=56 includes zero, is below the 0.01 epsilon, and is below the 0.017857 1/N noise floor, so the Qwen3-Embedding-0.6B default did not move"
  - "Corpus adequacy was recorded before the embed: adequate=true with held-out en=42, zh=11, mixed=3; both required languages cleared the N>=10 floor"
  - "Both arm identities are source: verified at 1024 dimensions with distinct fingerprints, so the comparison could not share an embedding cache bucket"
  - "The docs section records the held-out, per-language, per-leg, and per-leg-language gates, names the suppressed groups, and summarizes per-arm costs; the committed artifact remains aggregate-only"
  - "The conditional default flip and explicit-Qwen3 zero-delta proof were not exercised by keep-qwen3 and remain pending for plans 23-05/23-06"

requirements-completed: [MODEL-01, MODEL-02]

coverage:
  - id: D1
    description: "Corpus scope and EN+ZH adequacy were recorded before any embedding; both required languages reached N >= 10"
    requirement: MODEL-01
    verification:
      - kind: manual_procedural
        ref: "23-VALIDATION.md#Recorded Run (2026-11-16)"
        status: pass
    human_judgment: true
  - id: D2
    description: "The real two-arm EN+ZH run produced a three-way verdict artifact with both verified identities, distinct fingerprints, the full gate set, and per-arm costs"
    requirement: MODEL-01
    verification:
      - kind: manual_procedural
        ref: ".planning/phases/23-harrier-gated-evaluation/bench/harrier-verdict.json"
        status: pass
    human_judgment: true
  - id: D3
    description: "docs/benchmarking.md records the Phase 23 evidence in the held-out/rejection style with no query text or absolute personal paths"
    requirement: MODEL-02
    verification:
      - kind: automated
        ref: "Task 3 artifact assertion plus docs grep gates and git status scratch check"
        status: pass
    human_judgment: false

duration: 5min
completed: 2026-11-16
status: complete
---

# Phase 23 Plan 04: Real EN+ZH Evidence Run Summary

**A real two-arm EN+ZH evaluation on 498 personal documents produced `keep-qwen3`: the overall held-out mean delta +0.009430 at N=56 includes zero and sits below both the 0.01 epsilon and the 1/N noise floor, so the Qwen3 default stayed; the aggregate verdict artifact and Phase 23 benchmarking section are committed.**

## Performance

- **Duration:** 5 min (Task 3 executor; Tasks 1-2 were the blocking-human preflight and real run completed before this executor)
- **Started:** 2026-11-16T14:14:45Z
- **Completed:** 2026-11-16T14:19:47Z
- **Tasks:** 3
- **Files modified:** 3 (1 created, 2 modified)
- **Real-run embed wall:** 2,697.202 s across both arms (Qwen3 1328.186 s, Harrier 1369.016 s)

## Accomplishments

- Task 1 approved a curated seven-root bilingual scope (basenames: 项目申请, 实验室项目, 课程教学, 评审, 学生论文, PPT, Book) and ran the adequacy preflight before any embedding: `adequate: true`, sampled 50, held-out `en = 42`, `zh = 11`, `mixed = 3`, corpus fingerprint `b5d50ce0c696ab3d`. Both required languages cleared N >= 10, so the embed budget was authorized.
- Task 2 produced the real two-arm run: each arm indexed the same 498 documents / 21,798 chunks and embedded all 498 documents (Qwen3 1328.186 s, Harrier 1369.016 s). Both stored identities are `source: verified`, 1024-dimensional, and have distinct fingerprints (`d72e733a...` vs `dbfc87b7...`); Harrier records `query_prompt: web_search_query` and no document prompt, Qwen3 remains prompt-free. The query-set fingerprint is `b71a4be84d2a8724`.
- The overall held-out gate was `sufficient: true` but `winner: false`: n=56, mean delta +0.009430, 95% CI [-0.029587, +0.048389], 1/N floor 0.017857. Per-language held-out deltas were `en` +0.013848 (n=42) and `zh` -0.004865 (n=11); both clear the inclusive -0.01 language floor, but neither funds a switch, so the artifact records `keep-qwen3`.
- Task 3 added the Phase 23 `docs/benchmarking.md` evidence section with the decision, artifact path, corpus fingerprint, adequacy counts, the 101-query implication, arm identities, query-set fingerprint, held-out/per-language/per-leg/per-leg-language gates (N, deltas, CIs, noise floors, winner), suppressed group names, per-arm costs, environment, and the replay-unavailable note.
- Privacy validation passed: the artifact contains no query text, saved-run records, or absolute personal paths; corpus scope labels are basenames only. `git status --porcelain .planning/tmp` is empty because the scratch root is git-ignored.
- `23-VALIDATION.md` now marks the adequacy preflight and real two-arm run as recorded with the run date, environment label, artifact path, and decision; the conditional flip and zero-delta proof remain pending for plans 23-05/23-06.

## Task Commits

Tasks 1-2 were blocking-human checkpoints with no code commit; their output is the artifact committed with Task 3.

1. **Task 1: Corpus scope and EN+ZH adequacy approval** - no commit (manual preflight, recorded in validation)
2. **Task 2: Produce the real two-arm evidence run** - no commit (artifact committed with Task 3)
3. **Task 3: Write the Phase 23 evidence section and finalize the artifact record** - `0b9c143` (docs)

**Plan metadata:** pending final docs commit.

## Files Created/Modified

- `.planning/phases/23-harrier-gated-evaluation/bench/harrier-verdict.json` - Committed aggregate verdict artifact: three-way decision, rule booleans/reasons, both arm identities and costs, corpus adequacy/fingerprint, query-set fingerprint, full gate set, suppressed groups, environment, and replay note.
- `docs/benchmarking.md` - New `## Embedder Substitution Evidence` section with the `### Harrier gated evaluation (Phase 23)` evidence subsection and tables.
- `.planning/phases/23-harrier-gated-evaluation/23-VALIDATION.md` - Real-run record: task statuses, manual-verification outcomes, run date, environment, artifact path, decision, and pending conditional proof.

## Decisions Made

- The run's `keep-qwen3` decision is recorded as final; no default embedder setting changed and no setting was touched in this plan.
- The docs section reproduces the artifact's rounded aggregate numbers and full identity fingerprints; it names the nine suppressed leg × language × length groups rather than rendering zero rows.
- The Qwen3 pre-flip saved run and arm DBs are retained locally in the ignored scratch cache for plan 23-06's conditional zero-delta proof; no saved-run path or record was committed.
- The commit contains only the three authorized paths; unrelated pre-existing untracked planning files were left alone.

## Deviations from Plan

### Auto-fixed Issues

**1. [Plan wording] Saved-run fingerprint is not an artifact field**
- **Found during:** Task 3
- **Issue:** The Task 3 action asks the docs section to include "the query-set fingerprint and saved-run fingerprint", but the 23-03 artifact schema exposes `query_set_fingerprint` and no saved-run fingerprint, and the runbook is the artifact writer.
- **Resolution:** The section records the committed query-set fingerprint `b71a4be84d2a8724` and states the Qwen3 pre-flip saved run is retained locally (uncommitted) for plan 23-06. No fingerprint was fabricated and the runbook schema was not changed in this docs-only task.
- **Files modified:** `docs/benchmarking.md`
- **Commit:** `0b9c143`

**Structural note:** The required `### Harrier gated evaluation (Phase 23)` heading is nested under a new `## Embedder Substitution Evidence` H2 so the page's heading hierarchy stays valid; no existing section moved.

---

**Total deviations:** 1 plan-wording resolution (no code change).
**Impact on plan:** Documentation completeness only; the artifact schema and the verdict are unchanged.

## Issues Encountered

None. The full suite auto-backgrounded after the 180 s foreground window and completed green.

## Auth Gates

None - the run was local-only; both arms removed API base/key from their environment.

## User Setup Required

None - the corpus scope and embed budget were approved in Task 1, and the run was completed in Task 2.

## Next Phase Readiness

- Plan 23-05's conditional default flip is **not applicable** to this run: the decision is `keep-qwen3`, so Settings/EmbeddingConfig defaults stay on Qwen3-Embedding-0.6B and the plan should record not-applicable rather than flipping.
- Plan 23-06's explicit-Qwen3 zero-delta proof remains pending/conditional; the retained Qwen3 arm DB and pre-flip saved run stay in the local scratch cache (git-ignored and uncommitted).
- No CLI or Settings surface changed, so `docs/cli-reference.md` and `docs/configuration.md` were not regenerated or hand-edited.
- Full suite green at 2981 passed / 1 skipped / 95.13% coverage; `ruff check`, `ruff format --check`, and `ty check src/sif` all pass.

## Verification Results

- Task 3 artifact assertion: PASS (`decision` valid, `min_heldout_for_epsilon_win == 101`, corpus fingerprint and adequacy counts present, both arms + `language_splits` + query-set fingerprint present).
- `grep -c "harrier-verdict.json" docs/benchmarking.md`: 1; `min_heldout_for_epsilon_win`: 1; `Harrier gated evaluation`: 1.
- `git status --porcelain .planning/tmp`: empty.
- `env -u FORCE_COLOR NO_COLOR=1 pytest`: 2981 passed, 1 skipped, 95.13% coverage.
- `ruff check src tests`, `ruff format --check src tests`, `ty check src/sif`: pass.

---
*Phase: 23-harrier-gated-evaluation*
*Completed: 2026-11-16*

## Self-Check: PASSED

All three committed files exist at HEAD and the task commit is an ancestor of HEAD.
