---
phase: 05-agent-context-experience
fixed_at: 2026-09-07T04:47:02Z
review_path: .planning/phases/05-agent-context-experience/05-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 05: Code Review Fix Report

**Fixed at:** 2026-09-07T04:47:02Z
**Source review:** .planning/phases/05-agent-context-experience/05-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 2 (WR-01, WR-02; critical = 0, fix_scope = critical_warning)
- Fixed: 2
- Skipped: 0

**Environment note:** `workflow.use_worktrees = false` — fixes were applied and
committed directly in the main checkout (`main`). All verification below ran in
the main checkout with `env -u FORCE_COLOR NO_COLOR=1` (FORCE_COLOR breaks CLI
output assertions on this machine).

**History note:** during this fix run the `main` branch was rewritten by a
concurrent session (commits `d5c202f`/`4c10993`/`ff10314` replaced by
`e3aad7b` and the phase 05-08/05-09 implementation line). Both fix commits
landed on top of the new `e3aad7b` base; the baseline experiment for the
pre-existing test failures (see Verification) was re-run against `e3aad7b`
after the rewrite was discovered.

## Fixed Issues

### WR-01: One malformed `target_id` crashes all search commands, prune, and add

**Files modified:** `src/sif/utils/paths.py`, `src/sif/cli/commands/context.py`,
`tests/unit/search/test_context_attach.py`, `tests/unit/database/test_repositories.py`,
`tests/unit/cli/test_context.py`
**Commit:** 98dc8fc
**Applied fix:**
- `normalize_path()` is now a total function: `expand_path()` failures
  (`RuntimeError` / `OSError` / `ValueError`, e.g. `~removeduser/...` whose
  account no longer resolves) degrade to `str(path)` instead of raising, so a
  single malformed stored row can no longer crash `attach_path_contexts()`
  (all three searchers), `delete_orphaned_paths()` (prune), or the WR-02 merge
  scan. The degraded row simply matches nothing — the same effective outcome
  as before, minus the crash.
- `context add path` now probes expandability via `expand_path()` and raises a
  clean `click.ClickException("Cannot resolve path '...': ...")` for an
  un-expandable `~user` typo (project convention), instead of storing a
  never-matching target or leaking a raw traceback.
- Regression tests (all real SQL where applicable):
  - `test_normalize_path_unexpandable_tilde_degrades_to_raw_form`
  - `test_malformed_tilde_row_does_not_crash_attach` (malformed
    `~sif-no-such-user-7f3a/...` row inserted; healthy contexts still attach)
  - `test_prune_survives_malformed_tilde_row` (prune completes; the malformed
    row is correctly classified as an orphan and deleted, no crash)
  - `test_add_path_unexpandable_tilde_clean_error` (exit != 0, clean
    "Error: Cannot resolve path ..." output, nothing stored)

### WR-02: Self-heal merge only fires on exact historical re-typing — duplicate rows accumulate and prune cannot clean them

**Files modified:** `src/sif/cli/commands/context.py`, `tests/unit/cli/test_context.py`
**Commit:** 5aeea94
**Applied fix:**
- On the dual-form exact-lookup miss, `context add path` now resolves by
  normalized key over `repo.list_by_type("path")`: all historical spellings of
  the same file are merged into one canonical row (newest `updated_at` wins
  via `repo.update_target`, older duplicate spellings are deleted via
  `repo.delete`). Re-adding a legacy-aliased file via its canonical spelling
  now merges instead of creating a duplicate row that prune could never
  remove. Explicit re-add only — never a bulk migration.
- Adaptations to the reviewer's snippet (guidance, applied to actual code):
  - `context_add` sits exactly at the ruff C901 limit (10), so the merge lives
    in module-level helpers (`_self_heal_path_row`, `_merge_key`,
    `_resolve_path_target`) rather than inline; behavior matches the
    suggestion.
  - The `updated_at` sort uses a tz-safe epoch key: rows migrated from the
    legacy `path_contexts` table carry offset-less timestamps (the IN-01
    `'2024-01-01T00:00:00'` forms), and sorting a naive/aware mix would raise
    `TypeError` on exactly the legacy rows this merge targets.
  - Loser rows are deleted only when `update_target` actually returned `True`;
    a vanished-winner `False` falls through to create instead of risking
    content loss.
  - The comparison `normalize_path(c.path) == actual_target` is guarded by the
    WR-01 total-form fallback, so a poison row cannot crash the merge.
- Regression test: `test_readd_via_canonical_merges_legacy_alias_rows` — two
  legacy rows under two real symlink-alias spellings (one with a deliberately
  naive timestamp), re-add via the canonical spelling: newest row re-pointed,
  older duplicate deleted, no create. Three existing mock tests
  (`test_add_path_context`, `test_add_path_symlink_alias_stores_resolved_form`,
  `test_add_path_home_relative_expands`) updated to stub
  `list_by_type` since the new scan path is now reached on a total miss.

## Skipped Issues

None — both in-scope findings were fixed.

Out-of-scope info findings (IN-01, IN-02, IN-03) were not attempted, per
`fix_scope: critical_warning`. Note IN-03's call-site return check remains as
reviewed (the new WR-02 merge path does check its `update_target` return).

## Verification

- Tier 1 (per fix): modified sections re-read; fix text present, surrounding
  code intact.
- Tier 2 (per fix): `ast.parse` on every edited file; `ruff check src tests`
  and `ruff format --check src tests` clean (first WR-02 draft was rejected by
  C901/PLR0912 and refactored into helpers before commit).
- Targeted tests: `tests/unit/cli/test_context.py` +
  `tests/unit/database/test_repositories.py` +
  `tests/unit/search/test_context_attach.py` = 41 passed (36 baseline + 5 new).
- Full suite (main checkout, `env -u FORCE_COLOR NO_COLOR=1`):
  **660 passed, 2 failed** — the 2 failures
  (`tests/unit/embedding/test_openai_embedder.py::
  TestOpenAIEmbedderBehavior::test_import_error_logs_install_hint`,
  `...::TestOpenAIEmbedderDimensionCache::test_corrupt_cache_treated_as_miss`)
  are **pre-existing and unrelated**: both fail with `caplog.text == ''` (a
  logging-propagation/isolation interference from other suite tests) and were
  proven present at the pre-fix base `e3aad7b` (655 passed / 2 failed there,
  660 passed / same 2 failed with this fix's 5 new tests; they pass when the
  file runs alone). No new failures introduced; all 5 new tests pass.
- Commits are pathspec-limited; the unrelated pre-existing working-tree state
  (staged `mypy.ini` deletion; unstaged `.planning/WINDOWS.md`,
  `.planning/config.json`, `uv.lock`, `.planning/phases/03-.../.continue-here.md`)
  was left exactly as found.

---

_Fixed: 2026-09-07T04:47:02Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
