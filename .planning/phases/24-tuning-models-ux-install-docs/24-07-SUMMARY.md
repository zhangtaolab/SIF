---
phase: 24-tuning-models-ux-install-docs
plan: 07
subsystem: indexing-search-tuning
tags: [breadcrumb, duplicate-metrics, held-out-gate, runbook, quality]
requires:
  - "Plan 24-01 tuning_verdict chunk policy and chunk_sweep runbook helpers (scope state, scratch guards, identity gate, artifact guard)"
  - "Plan 24-02 breadcrumb_embed_texts builder and Settings.embed_breadcrumb switch"
  - "Phase 18 personal-bench GateResult and per-leg comparison payloads"
provides:
  - "src/sif/indexing/breadcrumb.py duplicate_metrics (title/in-content/sub-chunk/title-equals-heading shares)"
  - "src/sif/search/tuning_verdict.py BreadcrumbDecision and decide_breadcrumb_default (body-leg duplicate veto)"
  - "scripts/breadcrumb_eval.py one-arm modelscope Qwen3 breadcrumb runbook with identity gate and guarded artifact"
affects:
  - "Plan 24-06 (real breadcrumb evidence run and committed breadcrumb-verdict.json)"
  - "Any future breadcrumb default change (D-04/D-05): adopt requires an overall held-out win plus a winning body leg"
tech-stack:
  added: []
  patterns:
    - "Pure policy over Phase 18 gate values with a mandatory per-leg duplicate veto"
    - "Scope-keyed resumable stage machine with argv-only subprocesses and a per-arm identity probe"
    - "Aggregate-only committed artifact with a decision/fingerprint overwrite guard"
key-files:
  created:
    - scripts/breadcrumb_eval.py
    - tests/unit/scripts/test_breadcrumb_eval.py
  modified:
    - src/sif/indexing/breadcrumb.py
    - src/sif/search/tuning_verdict.py
    - tests/unit/indexing/test_breadcrumb.py
    - tests/unit/search/test_tuning_verdict.py
decisions:
  - "The breadcrumb arm is one isolated DB at 512/128 with SIF_EMBED_BREADCRUMB=1, pinned to modelscope Qwen/Qwen3-Embedding-0.6B, dim 1024, max_tokens 512, no prompts."
  - "The arm's persisted identity is asserted in an arm:identity stage after embed and before eval; a mismatched cache id, dimension, source, or prompt fails the run before any comparison."
  - "An unusable baseline saved run (missing/invalid/fingerprint/backend/model mismatch) is rejected with a path-free reason and a fresh 512/128 Qwen3 baseline is generated with the breadcrumb off, so no delta conflates a backend swap with the breadcrumb."
  - "Duplicate metrics are computed per document and aggregated weighted by chunk count; the decision prefers the held-out per-leg gate (leg_splits.heldout) and falls back to the all-split legs."
  - "Adoption requires the overall held-out winner, a winning and sufficient body leg, and a recorded duplicate summary; title-leg-only, flat, and regressing body legs are keep-breadcrumb-off with named reasons, and an absent body leg is insufficient evidence."
  - "The artifact records identity and model_type, refuses a differing decision or corpus fingerprint without --force, and exits 3 with a countable artifact on insufficient evidence."
metrics:
  duration: "~20 min"
  completed: "2026-11-17"
  tasks: 3
  files: 6
status: complete
actuals:
  tokens: 22729
  tasks: 3
  commits: 3
commits: 3
plan_head_before: 88c8f4808ab5db545ecca98c23c94e59fe670f76
plan_head_after: 409d7465fec31f32ee78f9185de5386f7ff86635
---

# Phase 24 Plan 07: Breadcrumb Duplicate Metrics + Body-Leg Veto + One-Arm Runbook Summary

A single identity-gated breadcrumb arm on the Phase 23 modelscope Qwen3 vector
space, a pure duplicate-signal veto that refuses a title-leg-only gain, and an
aggregate-only guarded artifact — no default changes in this plan.

## What Was Built

- **`duplicate_metrics(title, chunks)`** in `src/sif/indexing/breadcrumb.py` —
  reports `chunks`, `documents`, `title_share`, `in_content_share`
  (the current section heading text already occurs in the chunk),
  `subchunk_share` (first non-empty line is not a heading), and
  `title_equals_heading_share`. Shares round to six decimals; an empty chunk
  list is all zeros with `documents=0`; a single chunk is a valid denominator.
  Heading extraction reuses the builder's exact logic, including inherited
  headings for headingless continuations and CJK labels.
- **`decide_breadcrumb_default(confirmation, leg_gates, duplicates)`** in
  `src/sif/search/tuning_verdict.py` — `BreadcrumbDecision` plus
  `DECISION_ADOPT_BREADCRUMB` / `DECISION_KEEP_BREADCRUMB`. The body-leg veto
  is mandatory: a title-leg-only gain, a flat body leg, a regressing body leg,
  a sub-sufficiency body gate, or a missing duplicate summary all return
  `keep-breadcrumb-off` with named reasons; an absent body leg is
  `insufficient-evidence`. The duplicate summary is carried on every outcome,
  and bootstrap/1/N arithmetic is never recomputed.
- **`scripts/breadcrumb_eval.py`** — stdlib-only-at-import one-arm runbook:
  - `build_arm_env` removes the inherited API/base/prompt/model-path keys and
    pins modelscope Qwen3/1024/512 with `SIF_EMBED_BREADCRUMB=1` (the baseline
    twin pins it to `0`);
  - the ordered plan is `arm:index` (one collection add per root plus
    `index update`) → `arm:embed --force --chunk-strategy auto` →
    `arm:identity` → `arm:eval --compare <saved run> --json`;
  - the `arm:identity` stage runs this script's `--probe-identity` under the
    arm env, reads the arm DB's persisted identity, and requires
    `modelscope:Qwen/Qwen3-Embedding-0.6B`, dim 1024, `verified`, and null
    prompts before eval;
  - an unusable baseline saved run is rejected with a path-free reason and a
    fresh baseline twin is generated and copied to `saved-runs/baseline.json`;
  - duplicate metrics are read from the arm DB read-only, computed per
    document, and aggregated weighted by chunk count;
  - the artifact carries `model_type`, `identity`, `confirmation`, `legs`,
    `duplicates`, `corpus_label`, `corpus_fingerprint`, `baseline_source`,
    `selection_rule`, `min_heldout_for_epsilon_win=101`, and the N=56
    limitation; it is aggregate-only and refuses a differing decision or
    corpus fingerprint without `--force`; insufficient evidence exits 3 after
    writing the artifact.
- **Tests** — 40 runbook cases, 9 new duplicate-metric cases, and 16 new
  policy cases: dry-run arm/env/stage contract, no-subprocess dry run,
  scope-key resume invalidation, parent/child corpus and home-scratch
  refusals, identity mismatches (cache id, query prompt, document prompt), the
  baseline rejection categories, weighted duplicate aggregation on a synthetic
  SQLite arm DB, artifact schema/privacy, the overwrite guard, and the
  insufficient exit-3 path.

## Verification

- `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/scripts/test_breadcrumb_eval.py tests/unit/indexing/test_breadcrumb.py tests/unit/search/test_tuning_verdict.py -x --no-cov` — 96 passed.
- `python scripts/breadcrumb_eval.py --dry-run --json` — one breadcrumb arm,
  modelscope Qwen3/1024/512, `SIF_EMBED_BREADCRUMB=1`, ordered
  `arm:index`/`arm:embed`/`arm:identity`/`arm:eval`, expected cache id
  `modelscope:Qwen/Qwen3-Embedding-0.6B`; no subprocess.
- `ruff check src tests scripts` and `ruff format --check src tests scripts` — green.
- `ty check src/sif/indexing/breadcrumb.py src/sif/search/tuning_verdict.py` — green.
- Full `env -u FORCE_COLOR NO_COLOR=1 pytest` — 3184 passed, 1 skipped,
  coverage 95.05% (gate 90%).

## Deviations from Plan

None - plan executed as written.

## Notes

- `decide_breadcrumb_default` additionally refuses a sub-sufficiency body gate
  and a missing duplicate summary. Both follow the plan's "adopt only when the
  body leg wins and the duplicate summary is recorded" and `GateResult`'s
  documented rule that a small gate "can never warrant a defaults change";
  neither adds an adoption path.
- The decision reads the held-out per-leg gate (`comparison.leg_splits.heldout`)
  first and falls back to the all-split `comparison.legs`. D-04's veto is a
  held-out claim, and the artifact records the gates actually used.
- Baseline regeneration emits `baseline:*` stages at runtime; the dry-run's
  `stages` list stays exactly the four arm stages (the plan's verify asserts
  that list), with the conditional baseline plan recorded under `baseline`.
- Real breadcrumb evidence (≈22 min) remains a recorded manual run per
  `24-VALIDATION.md`; this plan commits machinery only and changes no default.

## Threat Flags

None. The implementation mitigates the registered threats: T-24-13 identity
substitution (pinned backend, baseline model_type/model_name check, persisted
cache-id/dimension/prompt gate before eval, identity recorded), T-24-06
artifact disclosure (aggregate-only schema with a privacy test), and T-24-SC
(no package installed, no model downloaded).

## Known Stubs

None.

## Self-Check: PASSED

- `src/sif/indexing/breadcrumb.py` contains `duplicate_metrics`.
- `src/sif/search/tuning_verdict.py` contains `decide_breadcrumb_default`.
- `scripts/breadcrumb_eval.py` exists and contains `SIF_EMBED_BREADCRUMB`.
- `tests/unit/scripts/test_breadcrumb_eval.py` exists and contains `modelscope`.
- Commits b2edcb9, 2b882b9, and 409d746 are ancestors of HEAD.
