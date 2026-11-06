---
phase: 07-cli-claude-skill
plan: 02
status: completed
completed_at: "2026-04-20"
---

# Plan 02 Summary: Create sif-get Claude Skill

## What Was Done

Created the `sif-get` Claude Skill that wraps SIF's document retrieval CLI commands.

### Deliverables

- **Skill file**: `.claude/skills/sif-get/SKILL.md`
- **Symlink**: `~/.claude/skills/sif-get -> /Users/forrest/GitHub/SIF/.claude/skills/sif-get`

### Skill Capabilities

The `sif-get` skill provides:

1. **Single document retrieval** by path: `sif get get {path}`
2. **Single document retrieval** by document ID: `sif get get {doc_id}`
3. **Batch retrieval** via glob pattern: `sif get multi-get "*.md"`
4. **Batch retrieval** via comma-separated paths: `sif get multi-get "a.md,b.md"`
5. **Line limiting**: `--lines N` and `--from-line M`

### Smart Defaults

- `-q` (quiet mode, suppresses non-error output)
- `--line-numbers` (show line numbers)

### Error Handling

- Returns stderr to LLM on non-zero exit codes
- Lets LLM explain "document not found" errors
- Suggests `sif update` if index is missing

### Note on Naming

The original plan specified `docsift-get` (pre-rename). The skill was created as `sif-get` during the Phase 8 project rename from DocSift to SIF. The skill content was updated to use the `sif` CLI command.
