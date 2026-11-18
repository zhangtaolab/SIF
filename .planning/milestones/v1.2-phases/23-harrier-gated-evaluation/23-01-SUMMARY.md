---
phase: 23-harrier-gated-evaluation
plan: 01
subsystem: search-eval
tags: [personal-bench, held-out-gates, paired-bootstrap, bilingual, click]

# Dependency graph
requires:
  - phase: 18-quality-instrument-personal-bench-rapidfuzz-dym
    provides: personal-bench legs, hash sampling, 50/50 splits, paired bootstrap gates
provides:
  - Per-language and per-leg x per-language held-out gates in `--compare --json`
  - Language-aware held-out widening in `ensure_heldout(required_languages=...)`
  - HeldoutFloorError with per-language held-out counts
  - Repeatable `sif eval --require-language` validated against LANGUAGES
  - Deterministic bilingual test fixture helper
affects: [23-02, 23-03, 23-04, 23-05]

actuals:
  tokens: 9613
  tasks: 2
  commits: 2
  plan_head_before: 7f7ac8cc74c9ede6482d737851b33efe267235cc
  plan_head_after: 2c948aecff64c0386aa54d88b86561d24cb32384

tech-stack:
  added: []
  patterns:
    - "Defaulted frozen-dataclass report fields keep the single constructor site and existing callers valid"
    - "Axis gates iterate declared LANGUAGES order; absent keys are omitted, empty splits stay visible"

key-files:
  created: []
  modified:
    - src/sif/search/personal_bench.py
    - src/sif/cli/commands/eval.py
    - tests/support/eval.py
    - tests/unit/search/test_personal_bench.py
    - tests/unit/cli/test_eval.py
    - docs/cli-reference.md

key-decisions:
  - "ComparisonReport language fields are defaulted and appended last, so existing construction and Phase 18 output remain valid"
  - "Absent languages produce no gate key; a present language with an empty split carries an n=0, sufficient=False diagnostic"
  - "ensure_heldout(required_languages=()) reproduces the pre-Phase-23 path byte-for-byte; the language floor is added to both the widening loop and the cap guard"
  - "HeldoutFloorError subclasses ValueError so the CLI translation boundary and existing pytest.raises(ValueError) callers stay valid"
  - "--require-language uses click.Choice(LANGUAGES); compare mode warns once on stderr and never resamples the saved query set"
  - "Per-language gate counts come from the same baseline_ndcg/current_ndcg series; no baseline grades are re-derived"

patterns-established:
  - "Axis gate helper: group by record axis in declared order, then pass empty series for empty splits"
  - "Ocean of counts in domain error: carry structured attributes for the runbook and append per-language counts to the message"

requirements-completed: [MODEL-01]

coverage:
  - id: D1
    description: "`--compare --json` carries per-language and per-leg x per-language tuning/held-out gates with absent languages omitted and empty splits visible"
    requirement: MODEL-01
    verification:
      - kind: unit
        ref: "tests/unit/search/test_personal_bench.py#TestPerLanguageNoiseGates"
        status: pass
    human_judgment: false
  - id: D2
    description: "Language-aware widening raises HeldoutFloorError with per-language counts, and `sif eval --require-language` parses, validates, forwards, and warns in compare mode"
    requirement: MODEL-01
    verification:
      - kind: unit
        ref: "tests/unit/search/test_personal_bench.py#TestEnsureHeldout"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_eval.py#TestRequireLanguageCli"
        status: pass
      - kind: other
        ref: "make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md"
        status: pass
    human_judgment: false

duration: 8min
completed: 2026-11-16
status: complete
---

# Phase 23 Plan 01: Harrier Gated Evaluation Summary

**Per-language held-out gates, language-aware widening, and the additive `--require-language` flag now give Phase 23 the evidence surface its two-sided EN+ZH verdict needs, with the Phase 18 default path unchanged.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-11-16T11:54:46Z
- **Completed:** 2026-11-16T12:02:31Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- `ComparisonReport` now carries `language_splits` and `leg_language_splits`, populated from the same paired series as the existing gates, so D-08 rule (b) and D-07 adequacy are readable from `--compare --json` without re-deriving baseline grades.
- `ensure_heldout(required_languages=...)` widens past the total/held-out floors until every required language has 10 held-out queries; at the cap it raises `HeldoutFloorError` with `accepted`/`tuning`/`heldout`/`sampled`/`language_counts` attributes and per-language counts in the message.
- `sif eval --personal --require-language en --require-language zh` parses, validates against `LANGUAGES`, forwards to `ensure_heldout`, and compare mode warns once on stderr while keeping stdout JSON clean.
- Added a deterministic bilingual fixture helper (`bilingual_titles_and_bodies`) with unique Chinese body candidates, and regenerated `docs/cli-reference.md` through `make docs-generate`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Tracer — per-language and per-leg-language held-out gates reach `--compare --json`** - `cf6e0be` (feat)
2. **Task 2: Language-aware widening, `--require-language`, and regenerated CLI docs** - `2c948ae` (feat)

**Plan metadata:** pending final docs commit.

## Files Created/Modified

- `src/sif/search/personal_bench.py` - `field` import, `HeldoutFloorError`, `language_noise_gates`, `leg_language_noise_gates`, `heldout_language_counts`, `_language_floor_unmet`, `ensure_heldout(required_languages=...)`, defaulted `ComparisonReport` language fields and `to_dict` keys, `compare_saved_run` wiring.
- `src/sif/cli/commands/eval.py` - `LANGUAGES` import, repeatable `--require-language` option, `require_language` threading through `run_personal`/`_run_fresh`, compare-mode stderr warning.
- `tests/support/eval.py` - `bilingual_titles_and_bodies` plus deterministic Chinese title/body helpers; `build_personal_db` defaults untouched.
- `tests/unit/search/test_personal_bench.py` - `TestPerLanguageNoiseGates`, `TestHeldoutLanguageCounts`, and language-aware widening/cap-guard cases in `TestEnsureHeldout`.
- `tests/unit/cli/test_eval.py` - `TestRequireLanguageCli` and `TestBilingualFixture`.
- `docs/cli-reference.md` - regenerated `sif eval` section documenting `--require-language`.

## Decisions Made

- Defaulted the two new `ComparisonReport` fields (appended last) rather than making them required, so the single constructor site and all Phase 18 callers remain valid.
- Language gates ignore absent languages entirely and emit `n=0, sufficient=False` for an empty split, matching the existing per-leg gate semantics and T-23-02's anti-fabrication rule.
- Added the language floor to both the widening loop condition and the post-loop cap guard; the cap guard is what makes a total-floor-satisfying but language-short corpus fail loudly.
- `HeldoutFloorError` subclasses `ValueError` and carries structured attributes, preserving the CLI's existing `except ValueError` translation and the existing test match on "held-out".
- `--require-language` only affects fresh sampling; compare mode prints exactly one stderr warning and never resamples the saved query set (D-05).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. Ruff formatting and lint rules required a docstring/noqa on `HeldoutFloorError.__init__`, `dict.fromkeys` for the counts helper, and an unambiguous CJK comma in the fixture intro; all were part of implementing the specified code.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 23-02 can compute the two-sided verdict from `ComparisonReport.language_splits["en"|"zh"]["heldout"]` and `.splits["heldout"]`.
- Plan 23-03/23-04 runbook can pass `--require-language en --require-language zh` on the fresh Qwen3 arm.
- Default path unchanged: `required_languages=()` is byte-identical and the full suite is green at 2904 passed / 1 skipped / 95.12% coverage.

---
*Phase: 23-harrier-gated-evaluation*
*Completed: 2026-11-16*

## Self-Check: PASSED

All 6 modified files and the SUMMARY exist; both task commits are ancestors of HEAD.
