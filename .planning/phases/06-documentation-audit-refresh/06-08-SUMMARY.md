---
phase: 06-documentation-audit-refresh
plan: "08"
subsystem: docs-generation
tags: [documentation, generators, ci, gap-closure]
requires:
  - "WR-06 Choice-typed --chunk-strategy (bda12a2)"
  - "WR-07 valid_types set without huggingface (60a2c08)"
  - "--quiet on search trio (2f7cbb4), --cors-origins on mcp http (phase 09)"
provides:
  - "Validator-passing docs generation pipeline (make docs-generate → 13 green tests)"
  - "Machine-independent generator output (tilde-rewritten home paths)"
  - "Blocking CI drift gate on committed reference docs"
  - "Live-source-derived validation table + model_type truthfulness regression lock"
affects:
  - docs/cli-reference.md
  - docs/configuration.md
  - .github/workflows/docs.yml
tech-stack:
  added: []
  patterns:
    - "Regex extraction of valid_types from inspect.getsource(Settings) with loud failure on miss"
    - "Home-prefix rewrite to ~ in default formatting for machine-independent docs"
    - "Section-builder extraction in generators (lint-compliant function sizes)"
key-files:
  created: []
  modified:
    - scripts/generate_cli_ref.py
    - scripts/generate_config_ref.py
    - docs/cli-reference.md
    - docs/configuration.md
    - tests/test_docs.py
    - .github/workflows/docs.yml
decisions:
  - "Generator emits plain `sif status` in the viewing section (no --verbose variant): --verbose is a group-level option, so `sif status --verbose` is not a valid placement"
  - "Validation Rules row and error example render from the live valid_types set (sorted), matching settings.py:163's message format exactly"
  - "Kept computed db_path/cache_dir defaults hardcoded in get_computed_default (phase 06-02 decision: real getters create directories as a side effect)"
metrics:
  duration: 12min
  completed: 2026-09-15
status: complete
gap_ids: [G-06-1, G-06-2, G-06-8]
requirements: [DOC-01, DOC-02, DOC-06, DOC-07]
actuals:
  tokens: 8460    # chars/4 over the realized diff (33840 chars, 6 files)
  tasks: 3
  commits: 3      # MEASURED: git rev-list --count e9eb749..HEAD
plan_head_before: e9eb74948c8019a7104576edbdcb34670b49ab51
---

# Phase 06 Plan 08: Docs Generation Pipeline Gap Closure Summary

Repaired both docs generator scripts (portable defaults, Choice types, live-derived validation rows, real commands in examples), regenerated both reference docs from live code, locked the WR-07 drift in the docs validator, and made the CI drift check blocking.

## What Was Done

### Task 1: generate_cli_ref.py — portable defaults, Choice types, valid examples (dbd3163)

- `_format_default` rewrites any default string prefixed with the current user's home directory to a `~` prefix, so the global `--config` default renders as `~/.config/sif` (matching `DEFAULT_CONFIG_PATH` in constants.py) instead of a machine-absolute `/Users/<name>/...` path. This is the prerequisite for the blocking CI drift gate (generator output is now machine-independent).
- `_format_type` renders `click.Choice` params as `choice [a|b|c]` from `param.type.choices`: `--chunk-strategy` now shows `choice [auto|fixed|markdown|code]`, and every `--model-type` row shows its four backends.
- Common Workflows examples fixed: `sif index update --collection my-notes` (flag, not positional) and `sif search query "python tips"` (leaf subcommand, not the bare group) — these were the two validator failures from G-06-8.
- Regenerated output automatically picked up `-q, --quiet` on the search trio (4 `--quiet` rows incl. global) and `--cors-origins` on `mcp http` from live param introspection; zero `/Users/` paths remain.

### Task 2: generate_config_ref.py — live-derived validation row, real defaults (3c14e7e)

- New `get_valid_model_types()` regex-extracts the `valid_types = {...}` set literal from `inspect.getsource(Settings)`'s `validate_model_type` body and raises loudly if the set is missing or empty, so future refactors cannot silently emit a stale/empty list.
- Validation Rules row and the bash error example now render from that set: `Must be one of: gguf, modelscope, openai, sentence_transformers` with the error message matching settings.py:163's format verbatim (`Invalid model_type: invalid. Must be one of ['gguf', 'modelscope', 'openai', 'sentence_transformers']`). `huggingface` (removed by WR-07) is gone everywhere.
- `.env` example derives `SIF_MODEL_TYPE=modelscope` and `SIF_RERANKER_MODEL_TYPE=sentence_transformers` from `Settings.model_fields[...].default`.
- Viewing section emits the real `sif status` command (the generator previously emitted nonexistent `sif config show [--with-defaults]`); no `--verbose` variant because that flag belongs to the group, not the subcommand.
- Troubleshooting drops the phantom `SIF_ENV_FILE` export and the `~/.env` lookup; Configuration Methods/Precedence now documents the truthful chain: environment variables → working-directory `.env` → defaults.
- Computed `db_path`/`cache_dir` defaults stay hardcoded per the phase 06-02 decision (real getters create directories as a side effect).

### Task 3: regenerate, lock regressions, blocking CI gate (79bf868)

- Both reference docs regenerated via `make docs-generate` and committed as generator output.
- `tests/test_docs.py`: phantom list extended with `SIF_ENV_FILE`; new `test_configuration_model_type_validation_is_truthful` asserts both directions of the WR-07 drift — `Settings.model_validate({"model_type": "huggingface"})` raises `ValidationError`, and the regenerated configuration.md never lists that backend.
- `.github/workflows/docs.yml`: dropped the `|| true` suffix from the `git diff --exit-code` drift step; divergence between committed and regenerated docs now fails the Docs Validation job. Triggers, setup, and step order unchanged; no new permissions.

## Verification Results

| Check | Result |
|-------|--------|
| `make docs-generate` → docs validator (`env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/test_docs.py -v`) | 13 passed (G-06-8 truth) |
| Generate-twice determinism (`git status --porcelain` after each of two runs) | empty both times |
| Full suite `env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q` | 676 passed / 0 failed (675 baseline + 1 new lock; known caplog order-dependents did not surface) |
| `ruff check` + `ruff format --check` on src tests + both generators | clean |
| docs.yml parses (`yaml.safe_load`), `grep -c '\|\| true'` | valid / 0 |
| Grep gates: `--quiet` rows, cors-origins, choice row, `~/.config/sif`, zero `/Users/`, modelscope/sentence_transformers defaults, zero huggingface/SIF_ENV_FILE/`sif config show`/`home directory` | all pass |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pre-existing lint failures on generate_cli_ref.py blocked the plan's own ruff gate**
- **Found during:** Task 1
- **Issue:** The plan requires `ruff check scripts/generate_cli_ref.py` clean, but the function failed PLR0915 (114 > 50 statements) and C901 (complexity 11 > 10) on `generate_cli_reference()` at HEAD — pre-existing, not caused by this plan's edits.
- **Fix:** Mechanical extraction of `generate_cli_reference()` sections into `_append_global_options` / `_append_command_overview` / `_append_command_sections` / `_append_output_formats` / `_append_exit_codes` / `_append_common_workflows` helpers (plus a module-level `GROUP_ORDER` constant). Output is byte-identical; both files now pass `ruff check` and `ruff format --check`.
- **Files modified:** scripts/generate_cli_ref.py
- **Commit:** dbd3163

Otherwise the plan executed exactly as written.

## Gap Closure Assessment

- **G-06-8 (root cause):** `make docs-generate` now emits docs that pass the project's own validator (13/13), and the CI drift check is blocking — the regeneration loop is trustworthy again.
- **G-06-1:** cli-reference.md option tables match live Click params: `--quiet` on the search trio, `--cors-origins` on mcp http, Choice-typed `--chunk-strategy` with choices listed, tilde-relative `--config` default, zero machine-absolute paths.
- **G-06-2:** configuration.md shows live defaults (model_type=modelscope, reranker_model_type=sentence_transformers) in tables and the .env example, a validation row + error example derived from the live validator's set, `sif status` in the viewing section, and no phantom env-file variable or home-directory .env precedence claim.

## Known Stubs

None — generators emit real content derived from live introspection; no placeholder values remain.

## Self-Check: PASSED

- Files exist: scripts/generate_cli_ref.py, scripts/generate_config_ref.py, docs/cli-reference.md, docs/configuration.md, tests/test_docs.py, .github/workflows/docs.yml — all FOUND
- Commits exist: dbd3163, 3c14e7e, 79bf868 — all FOUND on main
- No file deletions in any plan commit
