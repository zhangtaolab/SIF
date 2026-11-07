---
phase: 06-documentation-audit-refresh
plan: 09
subsystem: docs
tags: [documentation, gap-closure, mcp, cli-reference, truthfulness]
requires:
  - "06-08 regenerated docs (cli-reference.md, configuration.md) — not modified here"
provides:
  - "G-06-3 closed: quickstart jq example matches live --json output shape"
  - "G-06-4 closed: README remove example uses live --yes flag"
  - "G-06-6 closed: models.md EmbeddingConfig model_type default synced to ModelType.MODELSCOPE"
  - "G-06-7 closed: mcp-server.md documents all three mcp subcommands honestly and the real computed default db path"
affects: []
tech-stack:
  added: []
  patterns:
    - "hand-maintained docs corrected against live code (help output, source defaults, emitted JSON shape)"
key-files:
  created: []
  modified:
    - docs/quickstart.md
    - README.md
    - docs/models.md
    - docs/mcp-server.md
decisions:
  - "daemon documented with its exact live failure mode (ClickException 'not yet implemented, use mcp http') rather than aspirational behavior (T-06-05)"
  - "absolute-form stale paths (Claude Desktop JSON, SearchBackend example) also corrected to the platformdirs macOS location — same defect, found via the plan-mandated repo grep"
metrics:
  duration: 6min
  completed: "2026-09-15"
status: complete
gap_closure: true
gap_ids: [G-06-3, G-06-4, G-06-6, G-06-7]
estimate_tokens: 18000
actuals:
  tokens: 899
  tasks: 2
  commits: 2
commits: 2
plan_head_before: 79bf868e6be1d8b740fde463c547c4a9da901ddc
commits_list:
  - e9fd3db
  - 259b6e8
---

# Phase 06 Plan 09: Hand-Sync Four Generator-Unreachable Docs (Gap Closure) Summary

Hand-corrected the four documentation spots `make docs-generate` cannot reach — jq filter against the real `--json` array shape, live `--yes` confirmation flag, live `ModelType.MODELSCOPE` default, and an honest daemon subsection plus the platformdirs-computed default db path — closing gaps G-06-3, G-06-4, G-06-6, G-06-7.

## What Was Done

### Task 1: quickstart jq filter, README remove flag, models.md default (e9fd3db)

- **docs/quickstart.md:359** — jq example changed from `jq '.results[].document_path'` (wrapper-object shape the CLI never emits; silently returned nothing) to `jq '.[].path'`, verified against `format_results_json` (src/sif/cli/commands/search.py:44-50 emits a top-level array of `to_dict()` results) and `SearchResult.to_dict` (src/sif/core/models.py emits the `path` key). (G-06-3)
- **README.md:89** — collection remove example changed from nonexistent `--force` to the live `--yes` flag, confirmed via `sif collection remove --help` ("--yes  Confirm the action without prompting."). No other README content touched. (G-06-4)
- **docs/models.md:283** — EmbeddingConfig `model_type` default changed from `ModelType.SENTENCE_TRANSFORMERS` to the live `ModelType.MODELSCOPE` (src/sif/models/embedding.py:21). All other field listings untouched. (G-06-6)

### Task 2: mcp-server.md daemon + default db path (259b6e8)

- **Transport Types** — added a third subsection "daemon Transport (Not Yet Implemented)" after the HTTP endpoints table, documenting the subcommand's exact live behavior: it exists (`sif mcp daemon`, src/sif/cli/commands/mcp.py:75-91) but exits immediately with `Daemon mode is not yet implemented. Use 'mcp http' instead.`, with guidance to use `sif mcp http` today. No capabilities advertised beyond that (T-06-05 mitigated). The example bash block is existence-verified but never executed by the validator (`daemon` is in `_SUBCOMMANDS`; `"mcp daemon"` is in `SKIP_COMMAND_PATTERNS`).
- **Default db path** — all four stale occurrences replaced (plan named lines 185 and 197; the plan-mandated repo grep found two more absolute-form occurrences at lines 216 and 302):
  - env-var table: `~/.sif/index.sqlite` → `~/.local/share/sif/sif.db`
  - `.env` example: same replacement
  - Claude Desktop JSON example: `/Users/forrest/.sif/index.sqlite` → `/Users/forrest/Library/Application Support/sif/sif.db`
  - Custom Tool Handler example: same absolute-path replacement
  - Added a prose note under the env-var table: unset `SIF_DB_PATH` computes the path in the platform data directory (platformdirs), created on first run — Linux `~/.local/share/sif/sif.db`, macOS `~/Library/Application Support/sif/sif.db` (T-06-06 mitigated). Verified against `DEFAULT_DB_PATH` (src/sif/config/constants.py:11) and `Settings.get_db_path` (src/sif/config/settings.py:195-204); live computation confirmed as `/Users/forrest/Library/Application Support/sif/sif.db`.

## Verification Results

| Check | Result |
|-------|--------|
| `grep -cF "jq '.[].path'" docs/quickstart.md` | 1 |
| `.results[].document_path` in quickstart.md | 0 |
| `collection remove old-collection --yes` in README.md | 1 |
| `old-collection --force` in README.md | 0 |
| `Field(ModelType.MODELSCOPE` in models.md | 1 |
| `Field(ModelType.SENTENCE_TRANSFORMERS` in models.md | 0 |
| `sif mcp daemon` in mcp-server.md | 1 |
| `~/.local/share/sif/sif.db` in mcp-server.md | 3 |
| `~/.sif/index.sqlite` in mcp-server.md | 0 |
| Residual `sif/index.sqlite` sweep over docs/ + README.md | 0 occurrences |
| `pytest tests/test_docs.py -v` | 13 passed |
| Full suite `env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q` | 676 passed, 0 failed |
| `ruff check src tests` | All checks passed |
| `ruff format --check src tests` | 132 files already formatted |

All four gap truths from 06-UAT.md are demonstrably true via the greps and validator above.

## Deviations from Plan

None — plan executed exactly as written. Two clarifying notes:

- **Baseline count drift:** the Task 1 precondition cited "675 passed / 0 failed" but the live baseline is 676 (plan 06-08 added tests after this plan was written). Baseline run before any edit: 676 passed / 0 failed — precondition met; docs-only change kept it at 676.
- **Extra stale-path occurrences:** the plan explicitly instructed "check for additional occurrences with a repo grep"; that grep found two absolute-form occurrences (lines 216, 302) beyond the two named lines, and they were corrected as part of the same defect.

## Execution Notes

- Commits landed directly on `main`: project GSD config sets `branching_strategy: "none"` and `use_worktrees: false`, and the repo's entire phase/quick-task history is trunk-based on main; the generic protected-branch guard does not apply to this project's deliberate setup.
- Per orchestrator constraints, SUMMARY.md was not committed and STATE.md/ROADMAP.md were not edited — the orchestrator handles those after this return.
- Untracked runtime dirs (.gsd/, .planning/state.json, .planning/tmp/, .planning/ui-reviews/) and the uncommitted 06-08-SUMMARY.md were left untouched, as instructed.
- The 2 order-dependent caplog failures in tests/unit/embedding/test_openai_embedder.py did not appear in either full-suite run (known pre-existing item, WINDOWS.md #3/#4).

## Self-Check: PASSED

All 5 files FOUND (4 modified docs + this SUMMARY); both commit hashes FOUND (e9fd3db, 259b6e8); working tree clean for all four target files after commits.
