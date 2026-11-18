---
phase: quick-261111-wh9
plan: 01
subsystem: cli
status: complete
tags: [phase10, IN-05, cli, dead-option-removal, docs-regen, ledger-closure]
requires: []
provides:
  - "sif CLI without the no-op global config option (both spellings rejected exit-2, help unlisted)"
  - "Phase 10 IN-05 closed in 10-REVIEW-DISPOSITION.md (open 3->2, total 22)"
affects:
  - src/sif/cli/main.py
  - tests/unit/cli/test_main.py
  - docs/cli-reference.md
  - docs/installation.md
tech-stack:
  added: []
  patterns:
    - "Red-to-green rejection regression tests for removed CLI surface (CliRunner exit-2 + help-surface assertions)"
    - "Generator-owned docs updated only via make docs-generate; CI docs diff gate mirrored locally"
    - "Three-edit ledger closure with dynamic execution-time open-count decrement and byte-equality reconstruction"
key-files:
  created: []
  modified:
    - src/sif/cli/main.py
    - tests/unit/cli/test_main.py
    - docs/cli-reference.md
    - docs/installation.md
    - .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
key-decisions:
  - "USER DECISION (locked, honored verbatim): remove the no-op global config option; do NOT wire it into get_settings — configuration comes from SIF_ env vars via Pydantic Settings"
  - "DEFAULT_CONFIG_PATH in main.py was a module-level definition (not an import) with its only consumer inside the removed decorator; the same-named constant in config/constants.py is a different symbol and stayed untouched"
  - "Ledger open count decremented dynamically from execution-time git show HEAD (3->2; sibling wh7 had already closed WR-07); sibling-owned WR-08/IN-07 rows deliberately not state-asserted, preserved byte-identically"
metrics:
  duration: 8 min
  completed: 2026-11-11T15:58:21Z
  tasks: 3
actuals:
  tokens: 1893
  tasks: 3
  commits: 3
plan_head_before: ecb67e1d1b1d6aa7a65da4cf0a26c93025c354d2
plan_head_after: d1d73e807f65355e57fc745325428090dc666d03
---

# Quick 261111-wh9 Plan 01: Close Phase 10 IN-05 — Remove No-op Global Config Option Summary

**The sif CLI no longer accepts or documents the global config-path option: decorator, cli() parameter, ctx.obj config_path entry, and DEFAULT_CONFIG_PATH definition deleted (10 deletions / 1 insertion), three rejection regression tests proven red-to-green, CLI reference regenerated, and IN-05 closed in the Phase 10 ledger (open 3->2).**

## What Was Built

Closed Phase 10 finding **IN-05** ("`--config` global option is accepted, documented, and never consumed" — 10-REVIEW.md:183-187) per the locked USER DECISION: **removal, not wiring**. Planning-time sites in src/sif/cli/main.py at HEAD c8a234b: DEFAULT_CONFIG_PATH definition (line 28), decorator block (54-60), `config: str` parameter (64), ctx.obj assignment (79) — all re-verified by content at execution time before editing.

### Task 1 — Option removal with red-to-green rejection tests (commit 7fa8354)

- **Truly-unused proof re-verified at execution time:** `grep -rn config_path src/ tests/ scripts/` matched only the main.py:79 assignment itself; `DEFAULT_CONFIG_PATH` had exactly one consumer (the removed decorator's `default=`). The config/constants.py constant is a different symbol — untouched.
- **RED evidence (against unmodified main.py, before any src edit):** all three new `TestConfigOptionRemoved` tests failed non-vacuously —
  - `test_long_form_config_option_rejected`: `AssertionError: ... assert 0 == 2` (option accepted, status ran, "No index found" guidance printed)
  - `test_short_form_config_option_rejected`: `AssertionError: ... assert 0 == 2` (same acceptance via `-c`)
  - `test_help_does_not_list_config_option`: `'--config' is contained here: -c, --config PATH  Path to the configuration file`
- **GREEN:** deleted exactly the seven-line decorator block, the signature parameter (def line rewritten, 76 chars, one line), the ctx.obj config_path assignment, and the DEFAULT_CONFIG_PATH definition. `# Default paths` / `# Store options in context` comments and DEFAULT_INDEX_PATH kept. Diff shape asserted: `git diff --numstat` = **1 insertion / 10 deletions** — exactly the planned shape.
- Tests follow file conventions: CliRunner against the imported cli group, explicit tmp_path `--index` (callable Settings default never evaluated), class-local autouse `get_settings.cache_clear()` fixture mirroring RealDatabaseTestCase.isolated_settings.
- All 7 pre-existing test_main.py tests stayed green with zero assertion edits; every subcommand-level `-c` option (watch/search/query/vsearch/bench --collection, index --collection, collection update-cmd --cmd) untouched.

### Task 2 — Docs regeneration + hand-owned snippet fix (commit 7bd17be)

- `make docs-generate` run from checkout root; **cli-reference.md lost exactly the one Global Options `--config` row** (numstat `0 1`), nothing else.
- **configuration.md byte-identical** after regeneration (`git diff --exit-code` passed; the option never appeared in Settings) — not committed, never hand-edited.
- docs/installation.md (hand-written): deleted exactly the one stale `--config PATH` line from the `sif --help` expected-output snippet (numstat `0 1`); rest of snippet untouched.
- All 13 docs-gate tests (tests/test_docs.py) pass; regeneration idempotent.

### Task 3 — Ledger closure, IN-05 only (commit d1d73e8)

Exactly three scoped edits in 10-REVIEW-DISPOSITION.md (numstat 3/3):
1. IN-05 YAML block `disposition: open` -> `fixed` (id, severity info, title preserved).
2. Aggregate `open:` decremented **dynamically from execution-time `git show HEAD:<ledger>`: 3 -> 2** (sibling 261111-wh7 had already closed WR-07, moving the planning-time 4 to 3). `total: 22` and `recorded` timestamp unchanged.
3. IN-05 markdown row replaced with Source cell naming quick 261111-wh9 and the user decision (no pipe characters in the cell).

The plan's byte-equality reconstruction gate passed verbatim: `IN-05-fixed; open-count-decremented-from-execution-time-HEAD; all-other-ledger-content-unchanged`. Sibling-owned WR-08/IN-07 rows remain open and byte-identical (deliberately not state-asserted). No `**Status:**` line introduced.

## Verification Results (all gates green)

| Gate | Result |
|------|--------|
| Targeted: test_main.py + test_docs.py (--no-cov) | 23 passed (20 baseline + 3 new) |
| Negative greps (comment-filtered main.py x3, cli-reference.md, installation.md) | all 5 pass (baselines at HEAD: 1/1/2/1/1 — all removed) |
| ruff check src tests | All checks passed |
| ruff format --check src tests | 188 files already formatted |
| Full suite: python -m pytest (PATH miniconda, coverage on) | **1537 passed, 1 skipped, 95.06% coverage** (fail_under=90 met) |
| ty check src/sif | All checks passed |
| CI docs-gate mirror: make docs-generate && git diff --exit-code -- docs/cli-reference.md docs/configuration.md | zero diff — committed docs equal generator output |
| Scoped diff review | main.py 1/10 + tests 59/0; docs 0/1 + 0/1; ledger 3/3; no file deletions; pre-existing .planning churn never staged |

Full-suite count note: planning-time baseline was 1531; execution-time HEAD already included sibling wh7's 3 regression tests, so 1531 + 3 (wh7) + 3 (this plan) = 1537. The plan's gate is zero failures, not an exact count — met.

## Deviations from Plan

None — plan executed exactly as written. The user's locked removal decision was honored verbatim (no wiring attempted); the dynamic ledger decrement, generator-only docs updates, and task-scoped commits all followed the plan's gates.

## Known Stubs

None — no placeholder values, no skipped tests, no unrun verification. (WINDOWS ledger: nothing to append.)

## Threat Flags

None — the change removes an unused CLI parsing surface; no new endpoints, auth paths, file access, or schema changes.

## Commits

| Task | Commit | Files |
|------|--------|-------|
| 1 — option removal + rejection tests | 7fa8354 | src/sif/cli/main.py, tests/unit/cli/test_main.py |
| 2 — docs regen + snippet line | 7bd17be | docs/cli-reference.md, docs/installation.md |
| 3 — IN-05 ledger closure | d1d73e8 | .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md |

Planning artifacts (this SUMMARY, STATE.md) are intentionally uncommitted — the orchestrator owns the docs/state commit per batch constraints.

## Self-Check: PASSED

- All 5 modified artifacts + this SUMMARY exist on disk.
- All 3 task commits (7fa8354, 7bd17be, d1d73e8) verified as ancestors of HEAD (d1d73e8).
- Frontmatter `status: complete` present; commits count measured from plan-head ledger (ecb67e1..d1d73e8 = 3).