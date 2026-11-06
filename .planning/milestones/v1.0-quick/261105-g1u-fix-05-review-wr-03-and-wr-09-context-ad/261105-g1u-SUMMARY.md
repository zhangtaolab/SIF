---
phase: 261105-g1u-fix-05-review-wr-03-and-wr-09-context-ad
plan: 01
subsystem: cli
tags: [cli, context, config, validation, review-fix]
requires:
  - "05-REVIEW.md findings WR-03 / WR-09 open dispositions"
provides:
  - "context add/remove/list/prune share one identical missing-index contract"
  - "reranker_model_type validated to {gguf, sentence_transformers} at settings time"
  - "clean ClickException surfacing for invalid SIF_RERANKER_MODEL_TYPE on both query invocation paths"
affects: []
tech-stack:
  added: []
  patterns:
    - "sibling-guard replication (print-and-return missing-index contract)"
    - "fail-early field_validator + CLI-boundary ClickException conversion (defense in depth)"
key-files:
  created:
    - tests/unit/cli/test_main.py
  modified:
    - src/sif/cli/commands/context.py
    - src/sif/config/settings.py
    - src/sif/cli/main.py
    - src/sif/cli/commands/search.py
    - tests/unit/cli/test_context.py
    - tests/unit/config/test_settings.py
    - tests/unit/cli/test_search.py
decisions:
  - "Guard replicates sibling list/prune semantics exactly (console.print + bare return, exit 0), not ClickException"
  - "Fail-early field_validator + two query-path guards: _get_default_db_path (no --index) and query_cmd's own get_settings() (--index passed)"
  - "create_reranker ValueError converted to ClickException in query_cmd as defense in depth (ValidationError subclasses ValueError)"
metrics:
  duration: 6min
  completed: "2026-11-05"
  tests-before: 676
  tests-after: 684
actuals:
  tokens: 3664  # chars/4 over the realized src+tests diff (14,656 chars)
  tasks: 2
  commits: 2  # measured: git rev-list --count 91ca7ce..HEAD
plan_head_before: 91ca7ce
plan_head_after: b8a81e1
status: complete
---

# Quick Task 261105-g1u: Close Phase-05 Review Findings WR-03 and WR-09 Summary

**One-liner:** context add/remove now refuse to materialize a missing index (sibling-matching guard), and an invalid `reranker_model_type` fails at settings-validation time with a clean one-line ClickException on both query invocation paths.

## What Was Done

### Task 1 — WR-03: missing-index guard for `context add` / `context remove` (commit 25481d8)

- TDD: added `TestContextNoIndexGuard` to `tests/unit/cli/test_context.py` — two unpatched `tmp_path` tests (no Database/ContextRepository mocks) asserting exit 0, the sibling "No index found" warning, no false success line, and `not missing.db.exists()`. Both confirmed RED pre-fix (Database + init_schema created the file; remove even raised "No context found").
- Inserted the identical sibling guard (existence check → `console.print("[yellow]No index found.[/yellow]")` → bare `return`, matching `context list`/`context prune` exit semantics) in both `context_add` and `context_remove`, before `Database(index_path)`. The `rm` alias reuses `context_remove` and is covered.
- GREEN post-fix: all 25 tests in the file pass; `grep -c 'No index found' src/sif/cli/commands/context.py` = 4 (baseline 2).

### Task 2 — WR-09: `reranker_model_type` validator + clean ClickException surfacing (commit b8a81e1)

- TDD: 5 behavior tests written first, all confirmed RED pre-fix (`DID NOT RAISE ValueError` / `DID NOT RAISE ClickException` / missing "Error:" output).
- `src/sif/config/settings.py`: new `field_validator("reranker_model_type")` directly after `validate_model_type`, valid set exactly `{"gguf", "sentence_transformers"}` (the two `create_reranker` dispatch branches; the Qwen3 auto-detect never reads model_type), raising `Invalid reranker_model_type: {v}. Must be one of ['gguf', 'sentence_transformers']`.
- `src/sif/cli/main.py`: `_get_default_db_path` (the callable `--index` default Click evaluates on every no-`--index` invocation) now wraps `get_settings()` in `try/except ValidationError` → `click.ClickException(str(e))`; pydantic `ValidationError` imported.
- `src/sif/cli/commands/search.py` `query_cmd`: (a) wraps its own `settings = get_settings()` load (first settings touchpoint when `--index` IS passed) with the same ValidationError → ClickException conversion; (b) adds `except ValueError as e: raise click.ClickException(str(e)) from e` alongside the existing `except ImportError` in the create_reranker block (defense in depth). Comment literals kept clear of the `except ValueError` grep-gated string.
- New tests: validator accept/reject pair in `tests/unit/config/test_settings.py`; brand-new `tests/unit/cli/test_main.py` (direct `_get_default_db_path` unit test + end-to-end `runner.invoke(cli, ["status"])` group test, both with env set → `cache_clear()` → invoke → `cache_clear()` in finally); `TestQueryRerankerConfigError` in `tests/unit/cli/test_search.py` (env path with real unpatched `get_settings`, and mocked `create_reranker` ValueError path patching the module attribute since query_cmd imports it function-locally).

### Verification

- Task 1 gate: `pytest tests/unit/cli/test_context.py` green + grep count = 4 — pass.
- Task 2 gates: 67 tests green across `test_settings.py` / `test_main.py` / `test_search.py` / `test_reranker.py`; validator grep present; `ValidationError` counts main.py=2, search.py=2 (>=1); `except ValueError` in search.py = 1 (exact) — all pass.
- Full CLAUDE.md quality suite: `ruff check src tests` clean, `ruff format --check` 133 files formatted, full pytest **684 passed** (baseline 676 + 8 new: 2 context + 2 settings + 2 main + 2 search).
- Manual spot-checks: `SIF_RERANKER_MODEL_TYPE=cross-encoder python -m sif.cli.main status` → one-line `Error: 1 validation error for Settings ... Invalid reranker_model_type ...`, exit 1, zero "Traceback" lines; missing-index `context add` → "No index found.", no DB file.

## Deviations from Plan

- **Plan arithmetic error (no code impact):** the plan's must-have stated "35 tests = 33 baseline + 2 new" for `tests/unit/cli/test_context.py`; the actual baseline at HEAD was 23, so the file now has 25 passing tests. All behavioral gates (2 new RED→GREEN tests, grep count 4) hold as specified.
- **Optional spot-check expectation partially unmet (out-of-scope, pre-existing):** the plan's optional manual spot-check expected `/tmp/definitely-missing/` "NOT created" after a guarded `context add`. The WR-03 fix correctly creates no DB *file*, but the pre-existing `cli` group callback (`src/sif/cli/main.py:71`) unconditionally mkdirs the index parent directory for **every** command — including the long-guarded `context list`. This predates the task, affects all commands uniformly, and gating it is an architectural decision; logged to `deferred-items.md` as a follow-up candidate rather than auto-fixed (scope boundary).

### Auto-fixed Issues

None — both tasks executed exactly as planned.

## Known Stubs

None — no placeholders or unwired data paths were introduced.

## Threat Mitigations Applied

- **T-g1u-01 (Tampering, mitigate):** context add/remove on a missing index no longer materialize a fresh empty index DB that later commands would treat as real user state.
- **T-g1u-02 (Information Disclosure, mitigate):** invalid reranker config renders as a one-line ClickException instead of a stack trace (no absolute paths / library versions disclosed); the validator bounds accepted values to the dispatch set.

## Follow-up Candidates (not in scope)

- Group-level `mkdir` of the index parent directory (`main.py:71`) runs for every command — consider gating to index-creating commands (see `deferred-items.md`).
- `vsearch_cmd` settings load (`search.py:306`), `index.py:269`, and `bench.py:75` do not convert ValidationError to ClickException — per plan, invalid env config there surfaces pydantic's multi-line ValidationError exactly as the pre-existing `SIF_MODEL_TYPE` validator already does at those sites.

## Self-Check: PASSED

All 8 plan files + SUMMARY.md exist on disk; both task commits (25481d8, b8a81e1) verified as ancestors of HEAD; no non-planning untracked files left behind.
