---
phase: 23-harrier-gated-evaluation
plan: 02
subsystem: search-eval
tags: [embedder-verdict, held-out-gate, two-sided-rule, pure-policy, phase-18-gates]

# Dependency graph
requires:
  - phase: 23-harrier-gated-evaluation
    plan: "01"
    provides: "language_splits/leg_language_splits held-out gates and the SUPPRESS_BELOW adequacy contract"
  - phase: 18-quality-instrument-personal-bench-rapidfuzz-dym
    provides: "noise_gate/GateResult winner semantics (CI, 0.01 tie rule, strict 1/N floor), EPSILON"
provides:
  - "DECISION_ADOPT / DECISION_KEEP / DECISION_INSUFFICIENT decision vocabulary"
  - "VerdictDecision with literal rule booleans, per-language counts/deltas, and named reasons"
  - "decide_from_gates / decide / decide_from_payload pure entry points"
  - "MIN_HELDOUT_FOR_EPSILON_WIN = 101 pinning the strict 1/N floor boundary"
affects: [23-03, 23-04, 23-05]

actuals:
  tokens: 5590
  tasks: 2
  commits: 2
  plan_head_before: e4540b0742f10a85385714cea6517b98c7bcbd16
  plan_head_after: 2c66e00fff8bc822e417cd1fb744689451cf6094

tech-stack:
  added: []
  patterns:
    - "Pure policy module: consume GateResult fields verbatim, never re-derive bootstrap/CI/tie-rule/floor arithmetic"
    - "Fixed-order to_dict with copied nested maps, so the runbook records evidence it cannot mutate"

key-files:
  created:
    - src/sif/search/embedder_verdict.py
    - tests/unit/search/test_embedder_verdict.py
  modified: []

key-decisions:
  - "A missing overall held-out gate is insufficient-evidence with zeroed overall fields; language evidence is still recorded for audit"
  - "A non-mapping top-level language_splits in the CLI payload raises a named ValueError; a missing or malformed per-language entry is absent evidence (never a pass)"
  - "Reasons name every failed condition; adopt-harrier carries an empty reasons tuple"
  - "VerdictDecision.to_dict emits a fixed 16-key order and copies nested dicts so callers cannot mutate recorded evidence"

patterns-established:
  - "Three-way verdict precedence: adequacy -> winner+language floor -> keep/insufficient"
  - "Boundary battery builds real noise_gate gates; only malformed-payload cases use hand-built dicts"

requirements-completed: [MODEL-02]

coverage:
  - id: D1
    description: "Pure two-sided rule returns adopt-harrier only on an overall held-out winner plus every required language floor, recording literal booleans"
    requirement: MODEL-02
    verification:
      - kind: unit
        ref: "tests/unit/search/test_embedder_verdict.py#TestAdoptEndToEnd"
        status: pass
    human_judgment: false
  - id: D2
    description: "Boundary battery pins the 1/N floor, the inclusive -0.01 language floor, the 10-query adequacy floor, and malformed-payload rejection"
    requirement: MODEL-02
    verification:
      - kind: unit
        ref: "tests/unit/search/test_embedder_verdict.py#TestBoundaryRules"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_embedder_verdict.py#TestAdequacy"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_embedder_verdict.py#TestMalformedPayloads"
        status: pass
    human_judgment: false

duration: 6min
completed: 2026-11-16
status: complete
---

# Phase 23 Plan 02: Two-Sided Embedder Verdict Rule Summary

**A pure three-way verdict rule consumes Phase 18 gates verbatim, returning `adopt-harrier` only on an overall held-out winner plus EN+ZH floors, with every literal boolean and rejection reason recorded.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-11-16T12:05:45Z
- **Completed:** 2026-11-16T12:11:27Z
- **Tasks:** 2
- **Files created:** 2

## Accomplishments

- Added `src/sif/search/embedder_verdict.py`, a pure policy module with no Click, Rich, embedding, or database imports. It reads `GateResult.n/mean_delta/ci_low/ci_high/noise_floor/winner` and never reimplements bootstrap, CI, tie-rule, or noise-floor arithmetic (T-23-04).
- `decide_from_gates` enforces the locked two-sided gate: adequacy requires every required language held-out gate with `n >= SUPPRESS_BELOW` (10); `adopt-harrier` additionally requires `GateResult.winner` and every language mean delta at or above the inclusive `-0.01` floor; otherwise `keep-qwen3`, and a missing/thin language is `insufficient-evidence` (D-07, D-08).
- `VerdictDecision` records the literal booleans (`overall_winner`, `ci_excludes_zero`, `mean_delta_at_least_epsilon`, `above_noise_floor`, `per_language_floor_ok`, `adequate`), per-language `n`/mean deltas, named reasons, and `MIN_HELDOUT_FOR_EPSILON_WIN = 101`; `to_dict()` emits a fixed key order with copied nested maps.
- Added `decide`, `decide_from_payload`, and `_gate_value` so the runbook can consume a `ComparisonReport`-shaped object or the CLI comparison JSON without re-deriving metrics. Malformed payloads raise named `ValueError`s; a missing `language_splits` block is insufficient evidence, not an exception (T-23-05).
- Added a 20-test battery built on real `noise_gate` gates: adopt end-to-end through all three entry points, N=100 floor equality vs N=101 clearance, CI-containing-zero rejection, the `-0.02` language veto, the inclusive `-0.01` floor, absent-language and n=9/n=10 adequacy boundaries, malformed payloads, and reason auditability.

## Task Commits

Each task was committed atomically:

1. **Task 1: Tracer — one `adopt-harrier` decision end-to-end through the pure rule** - `8710915` (feat)
2. **Task 2: Boundary and rejection battery for the two-sided gate** - `2c66e00` (test)

**Plan metadata:** pending final docs commit.

## Files Created/Modified

- `src/sif/search/embedder_verdict.py` - decision constants, `LANGUAGE_FLOOR`, `MIN_HELDOUT_FOR_EPSILON_WIN`, `VerdictDecision`, `_gate_value`, `_language_evidence`, `_split_gate`, `decide_from_gates`, `decide`, `decide_from_payload`.
- `tests/unit/search/test_embedder_verdict.py` - `TestAdoptEndToEnd`, `TestBoundaryRules`, `TestAdequacy`, `TestMalformedPayloads`, `TestReasonAuditability` (20 tests).

## Decisions Made

- A missing overall held-out gate returns `insufficient-evidence` immediately, with zeroed overall fields but the actual language evidence still recorded; this keeps a broken payload auditable rather than anonymous.
- The payload contract is split: a non-mapping top-level `language_splits` is malformed and raises a named `ValueError`, while a missing or non-mapping per-language entry is treated as absent evidence (`insufficient-evidence`). Neither path can ever produce `adopt-harrier`.
- The language floor uses the house rounded arithmetic (`round(mean_delta, 6) >= -EPSILON`), so exactly `-0.01` is accepted and `-0.02` is a veto.
- `required_languages` is a tuple defaulted to `("en", "zh")`; recorded language dictionaries iterate in that required order, and an absent language is recorded as `n=0`/`delta=0.0` without affecting adequacy.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. Ruff required removing Task-2-only imports from the Task-1 commit and rewriting one test assertion to avoid the SIM300 Yoda-condition rule; both were formatting details inside the specified implementation.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 23-03's runbook can call `decide_from_payload(payload)` on the CLI comparison object directly and write `decision.to_dict()` into the verdict artifact.
- Plan 23-05's conditional default flip can treat `DECISION_ADOPT` as the sole authorization; the module never flips a default itself.
- Full suite green at 2924 passed / 1 skipped / 95.12% coverage; `ruff check`, `ruff format --check`, and `ty check src/sif` all pass.

---
*Phase: 23-harrier-gated-evaluation*
*Completed: 2026-11-16*

## Self-Check: PASSED

Both created files exist; both task commits (`8710915`, `2c66e00`) are ancestors of HEAD.
