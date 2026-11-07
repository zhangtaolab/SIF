# Phase 2: CLI Core Completion - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-15
**Phase:** 02-cli-core-completion
**Areas discussed:** multi-get interface, ls command design, update-cmd behavior, include/exclude semantics

---

## multi-get Interface

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-detect single argument | One positional argument: detect commas (split to IDs), glob chars (*?) → pattern match, otherwise treat as docid/path. Keeps the command simple. | ✓ |
| Explicit flags | Positional args = docids only. Add `--glob PATTERN` and `--comma LIST`. Unambiguous but more verbose. | |
| You decide | Claude chooses the approach based on codebase patterns and qmd compatibility. | |

**User's choice:** Auto-detect single argument
**Notes:** User wants a simple interface where one argument handles docids, comma-separated lists, and glob patterns automatically.

---

## ls Command Design

| Option | Description | Selected |
|--------|-------------|----------|
| Top-level `ls` for indexed docs | Create a new top-level `docsift ls` command that queries the database and shows indexed documents as a virtual tree. Keep `collection ls` as-is for filesystem preview. | ✓ (Claude's discretion) |
| Replace `collection ls` behavior | Change `collection ls` to show indexed documents from the database instead of filesystem scan. Remove or repurpose the filesystem preview behavior. | |
| You decide | Claude decides based on qmd compatibility and existing patterns. | |

**User's choice:** You decide → Claude selected "Top-level `ls` for indexed docs"
**Notes:** Aligns with qmd's top-level `ls` command and preserves the existing useful `collection ls` filesystem preview behavior.

---

## update-cmd Behavior

### When to run

| Option | Description | Selected |
|--------|-------------|----------|
| Run automatically before every index update | The command executes silently before each `docsift index update <collection>`. If it fails, the update stops. This is the expected 'hook' behavior. | ✓ |
| Run only on explicit request | The command only runs when the user runs something like `docsift index update --run-cmd <collection>`. More manual but safer for destructive commands. | |
| You decide | Claude chooses based on typical developer workflow expectations. | |

**User's choice:** Run automatically before every index update

### Failure behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Fail fast and skip indexing | A failing command aborts the update. This prevents indexing stale or broken state. | ✓ (Claude's discretion) |
| Warn and continue indexing | Print the error but proceed with indexing anyway. Useful when the command is advisory (e.g., a best-effort sync). | |
| You decide | Claude chooses based on the primary use case. | |

**User's choice:** You decide → Claude selected "Fail fast and skip indexing"
**Notes:** Pre-index commands are typically structural (like `git pull`) and inconsistent source state should not be indexed.

---

## include/exclude Semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Simple aliases | `include` = `enable`, `exclude` = `disable`. Both just flip `include_by_default`. Keeps the API small. | ✓ (Claude's discretion) |
| Distinct semantics | `enable`/`disable` controls whether the collection exists/is indexed at all. `include`/`exclude` only controls default search scope. This gives finer-grained control but requires a new database field. | |
| You decide | Claude chooses based on qmd compatibility and data model simplicity. | |

**User's choice:** You decide → Claude selected "Simple aliases"
**Notes:** The `Collection` model already has `include_by_default`. Adding a separate field would be unnecessary complexity for this phase.

---

## Claude's Discretion

- pull model sources and verification strategy
- line-numbers formatting details in structured output
- Specific error message wording for update-cmd failures
- Exact virtual tree rendering style for `ls`
- Pull command progress reporting format

## Deferred Ideas

None — discussion stayed within phase scope.
