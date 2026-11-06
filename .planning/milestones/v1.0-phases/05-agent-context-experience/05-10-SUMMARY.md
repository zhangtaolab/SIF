---
phase: 05-agent-context-experience
plan: "10"
subsystem: cli
tags: [cli, context, sqlite, rich, path-normalization, tdd, gap-closure]

# Dependency graph
requires:
  - phase: 05-agent-context-experience
    provides: write-side canonical context add with dual-form upsert self-heal (05-09 _self_heal_path_row + update_target)
provides:
  - "_collapse_duplicate_path_rows(repo, canonical_target, keep_id) — the single duplicate-collapse loop shared by every context-add re-add path (truth 21)"
  - "Markup-safe context list rendering — rich.markup.escape on all three table cells (CR-02 closed)"
  - "Two real-SQL/CLI regression tests encoding the verifier's multi-alias legacy-state reproductions"
affects: [05-agent-context-experience verification, 05-11 search markup escaping, context CLI consumers]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
actuals:
  tokens: 3675     # chars/4 over the realized src+tests diff (14702 chars)
  tasks: 3
  commits: 4       # MEASURED: git rev-list --count 6942617..HEAD

# Tech tracking
tech-stack:
  added: []        # stdlib + existing rich/click only — no new packages (T-05-SC)
  patterns:
    - "Single shared duplicate-collapse helper (_collapse_duplicate_path_rows) funneled from every re-add path — exact-match branch, normalized-key branch, and upsert-hit path all call it"
    - "escape()-AFTER-truncation for markup-safe Rich table cells — display cap applies to raw text, stored bytes untouched (mirrors the 04-06 snippet-column precedent)"

key-files:
  created: []
  modified:
    - src/sif/cli/commands/context.py
    - tests/unit/cli/test_context.py

key-decisions:
  - "Exact-match self-heal branch now mirrors the normalized branch's landed-guard: collapse runs only after update_target returns True (T-05-16 data-safety posture)"
  - "Upsert-hit path captures an upsert_hit flag so collapse fires only when the pre-check found the canonical row — the self-heal branches already collapsed, avoiding a redundant scan"
  - "escape() applied after truncation so the 50-char display cap keeps applying to raw text"

patterns-established:
  - "Truth-21 invariant: re-adding a path via ANY spelling combination ends with exactly one canonical row — enforced by one shared helper, never per-branch inline loops"
  - "Every user-authored string that crosses into Rich table cells is escaped at the add_row site (search snippets 04-06, context list 05-10, search tables 05-11)"

requirements-completed: [CTX-01, CTX-02]

# Coverage metadata (#1602) — one entry per shipped deliverable.
coverage:
  - id: D1
    description: "Re-adding a path via any spelling (alias+canonical legacy rows, two-alias legacy rows) ends with exactly one canonical contexts row carrying the re-added text"
    requirement: CTX-01
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_context.py#TestContextAddMultiAliasSelfHeal::test_readd_via_alias_with_alias_and_canonical_legacy_rows_ends_with_one_row"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_context.py#TestContextAddMultiAliasSelfHeal::test_readd_via_alias_with_two_alias_legacy_rows_ends_with_one_row"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_context.py#TestContextAdd::test_readd_canonical_row_collapses_alias_duplicates"
        status: pass
    human_judgment: false
  - id: D2
    description: "context list renders markup-bearing stored content and target paths literally (no MarkupError, no swallowed bracket text)"
    requirement: CTX-02
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_context.py#TestContextList::test_list_renders_markup_bearing_cells_literally"
        status: pass
      - kind: other
        ref: "manual repro: sif --index <tmp> context list with content 'see section [/3] for caveats' — exit 0, literal text visible"
        status: pass
    human_judgment: false
  - id: D3
    description: "No regressions across the previously-verified truths — full project quality suite green under the permanent fail_under=90 coverage gate"
    verification:
      - kind: other
        ref: "COVERAGE_FILE=.coverage.05-10 env -u FORCE_COLOR NO_COLOR=1 pytest -q — 1003 passed, TOTAL 96.22% (>=90 gate)"
        status: pass
      - kind: other
        ref: "ruff check src tests && ruff format --check src tests — clean"
        status: pass
    human_judgment: false

# Metrics
commits: 4
plan_head_before: 6942617da9589139b3189cbf8fde8477606a8c61
plan_head_after: ba7e0e4a514491385f5145a05cb2c342a72921f3
duration: 8min
completed: 2026-11-06
status: complete
---

# Phase 05 Plan 10: Multi-Alias Re-Add Collapse + CR-02 List Escaping Summary

**Shared `_collapse_duplicate_path_rows` helper collapses every same-file spelling into one canonical row on ALL re-add paths (truth 21), and `context list` escapes all Rich table cells so markup-bearing content renders literally (CR-02).**

## Performance

- **Duration:** 8 min
- **Started:** 2026-11-06T08:06:00Z
- **Completed:** 2026-11-06T08:14:00Z
- **Tasks:** 3 (TDD: 2 RED commits, 2 GREEN commits)
- **Files modified:** 2

## TDD Gate Compliance

RED → GREEN cycles executed per task, all in ancestry order (`test` before its `feat`):

### Task 1 — RED (real-SQL regression tests)

- **Tests written:** `TestContextAddMultiAliasSelfHeal.test_readd_via_alias_with_alias_and_canonical_legacy_rows_ends_with_one_row` (repro a) and `..._with_two_alias_legacy_rows_ends_with_one_row` (repro b) — real symlink dirs + real `Database(tmp_path/"index.db")` + real `ContextRepository` seeding, `CliRunner` against the real file, zero patch calls, direct SQL end-state assertions.
- **RED run:** `env -u FORCE_COLOR NO_COLOR=1 pytest --no-cov tests/unit/cli/test_context.py -k "ends_with_one_row"` → **2 failed, 25 deselected** (exit 1), both on `assert len(rows) == 1` — the planned exactly-one-row assertion.
- **Semantic assessment:** both target tests executed and failed for the verifier's exact reason — repro (a) leaves the alias row beside the canonical row (upsert short-circuit), repro (b) leaves the second alias row (exact-match branch never collapses). No import/fixture/syntax faults; the `exit_code == 0` and "Context updated" assertions passed, isolating the failure to the duplicate-collapse gap. Evidence: `.planning/tmp/05-10-red-evidence-task1.json`.
- **Commit:** `06bb5e5`

### Task 2 — GREEN (collapse on every re-add path)

- **Implementation:** module-level `_collapse_duplicate_path_rows(repo, canonical_target, keep_id)` (normalize_path equality only, path-type rows only, keep_id excluded — T-05-17); exact-match branch guarded on `update_target` returning True before collapsing (T-05-16); normalized branch's inline losers loop replaced by the helper; `context_add` upsert-hit path collapses shadowed alias rows before refreshing the canonical row's content via `repo.update`.
- **GREEN run:** `pytest --no-cov tests/unit/cli/test_context.py -x` → **27 passed** (both new real-SQL tests green; `test_readd_via_canonical_merges_legacy_alias_rows` anchor unchanged and green). Repository contract regression: `pytest tests/unit/database/test_repositories.py -k "update_target or prune or orphan"` → 8 passed.
- **Commit:** `608c5f8`

### Task 3 — RED then GREEN (CR-02 escaping)

- **RED:** `TestContextList.test_list_renders_markup_bearing_cells_literally` failed with the verifier's exact error — `MarkupError("closing tag '[/3]' at position 12 doesn't match any open tag")`, exit 1 (1 failed, 27 deselected). Evidence: `.planning/tmp/05-10-red-evidence-task3.json`. Commit: `ce73b87`.
- **GREEN:** `from rich.markup import escape`; all three `table.add_row` cells wrapped, escape AFTER truncation. `pytest -k markup` → 1 passed; full suite green. Commit: `ba7e0e4`.

### REFACTOR

Not needed — GREEN implementations landed in the shape the plan specified (one helper, three call sites); no cleanup warranted and none committed.

## Accomplishments

- Truth 21's two reachable failure states are fixed: re-adding a path under ANY legacy spelling combination (alias+canonical, two aliases, single legacy row) always ends with exactly one canonical row carrying the re-added text — proven by real-SQL CLI tests, not mocks.
- CR-02 closed: `context list` renders markup-bearing content and bracket text literally with exit 0 (previously `rich.errors.MarkupError`, exit 1); everyday bracket text like `[WIP]` is no longer swallowed.
- Manual repro closure via the real installed `sif` CLI on a temp DB: 2 seeded legacy rows (alias + canonical) → re-add via alias → "Context updated", `SELECT COUNT(*)` = 1 at canonical with "new text"; markup content lists with exit 0.
- Full quality suite green: 1003 passed (1000 at HEAD + this plan's 3 new tests), TOTAL coverage 96.22% under the permanent fail_under=90 gate; ruff check + format clean.

## Task Commits

Each task was committed atomically (TDD ordering preserved):

1. **Task 1: RED — real-SQL regression tests for the two multi-alias legacy states** - `06bb5e5` (test)
2. **Task 2: GREEN — collapse all same-file rows on every re-add path** - `608c5f8` (feat)
3. **Task 3: RED — markup-rendering regression test** - `ce73b87` (test)
4. **Task 3: GREEN — escape context list cells (CR-02)** - `ba7e0e4` (feat)

## Files Created/Modified

- `src/sif/cli/commands/context.py` — added `_collapse_duplicate_path_rows`; landed-guard + collapse in the exact-match branch; helper call in the normalized branch; upsert-hit collapse in `context_add`; `rich.markup.escape` on all three `context list` table cells.
- `tests/unit/cli/test_context.py` — new `TestContextAddMultiAliasSelfHeal` (2 real-SQL tests); new `TestContextList.test_list_renders_markup_bearing_cells_literally`; widened `test_readd_legacy_verbatim_row_self_heals` (delete-not-called assertion); renamed/strengthened `test_readd_canonical_row_updates_without_repoint` → `test_readd_canonical_row_collapses_alias_duplicates`.

## Decisions Made

- Exact-match branch mirrors the normalized branch's landed-guard (`update_target` True before any deletion) so the destructive collapse can never orphan the user's re-added content (threat T-05-16 mitigation).
- `context_add` captures `upsert_hit` at the pre-check so the collapse runs exactly once per re-add — self-heal branches already collapsed their duplicates; the flag avoids a redundant full `list_by_type` scan.
- Escape applied after truncation so the 50-char display cap keeps applying to raw text; display-only change, stored bytes untouched.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. (A first attempt at the optional manual repro used the bare system `python3`, which lacks the editable install — rerun with the miniconda interpreter that `pytest`/`sif` resolve to; no code impact.)

## User Setup Required

None - no external service configuration required.

## Known Stubs

None.

## Next Phase Readiness

- 05-VERIFICATION gap 1 (truth 21, partial) and 05-REVIEW CR-02 are closed for the context CLI; plan 05-11 (CR-01 search-table escaping) remains open in this gap-closure wave.
- All 23 previously-verified truths stay verified: full suite 1003 passed, 0 failed; repository contracts (update_target/prune/orphan) untouched and green.

## Self-Check: PASSED

- Files verified on disk: `src/sif/cli/commands/context.py`, `tests/unit/cli/test_context.py`, `05-10-SUMMARY.md` — all FOUND.
- Commits verified as ancestors of HEAD: `06bb5e5`, `608c5f8`, `ce73b87`, `ba7e0e4` — all FOUND.
- `gsd_run check evaluation-scope --plan 05-10 --commits-only` resolved with all 4 plan commits on this branch.
- Re-ran plan-level verification: context CLI suite 28 passed; repository contract (`update_target or prune or orphan`) 8 passed; full suite 1003 passed at 96.22% TOTAL under the fail_under=90 gate; ruff check + format clean.

---
*Phase: 05-agent-context-experience*
*Completed: 2026-11-06*
