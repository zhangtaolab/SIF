---
phase: 06-documentation-audit-refresh
plan: 01
subsystem: documentation
completed_date: "2026-04-18"
duration_minutes: 35
tasks_completed: 2
commits: 1
key_files:
  created:
    - scripts/generate_cli_ref.py
  modified:
    - docs/cli-reference.md
deviations: "None - plan executed exactly as written."
---

# Phase 06 Plan 01: CLI Reference Audit and Refresh Summary

**One-liner:** Auto-generated CLI reference via Click introspection, replacing stale manual documentation with accurate command/argument/option tables for all 32 commands.

## What Was Built

### scripts/generate_cli_ref.py
A Python script that imports the live Click CLI tree and generates complete markdown documentation:
- Recursively traverses groups and leaf commands
- Extracts arguments (name, type, required, help)
- Extracts options (short/long flags, type, default, multiple, is_flag, help)
- Handles Click sentinel defaults and callable defaults gracefully
- Generates global options table, ASCII command tree, per-command sections
- Includes output formats reference, exit codes, and common workflow examples

### docs/cli-reference.md
Fully regenerated from the live CLI code. Key improvements over the stale version:
- **32 commands documented** (was ~20 with many errors)
- **Removed stale commands:** top-level `query`, `embed`, `vsearch`, `mcp start`, `mcp config`
- **Added missing commands:** `collection enable/disable/update-cmd/include/exclude/ls`, `context prune/rm`, `mcp stdio/http/daemon`, `bench`, `pull`, `status`, `cleanup`
- **Corrected command paths:** `docsift get get`, `docsift search search`, `docsift search vsearch`, `docsift search query`, `docsift index update`, `docsift index embed`
- **Corrected signatures:** `collection add PATH --name/-n` (not `collection create NAME`), `context add TYPE TARGET CONTENT` positional args (not `--collection/--global` flags)
- **Accurate options tables:** all defaults, types, and help text from live Click params

## Verification Results

- All 32 leaf commands from `docsift.cli.main:cli` present in generated doc
- Zero removed commands appear in reference
- Workflow examples section present with working command patterns
- Output formats: table, json, csv, md, xml, files
- Exit codes: 0=Success, 1=General error, 2=Invalid arguments
- ruff check passes on generator script (with PLR0915/C901 complexity ignores for a doc-generation script)

## Commits

| Hash | Message |
|------|---------|
| 469abaf | feat(06-01): create CLI reference generator and regenerate docs/cli-reference.md |

## Self-Check: PASSED

- [x] scripts/generate_cli_ref.py exists
- [x] docs/cli-reference.md exists (715 lines)
- [x] Commit 469abaf exists
- [x] All 32 commands documented
- [x] No removed commands present
- [x] Workflow examples included
