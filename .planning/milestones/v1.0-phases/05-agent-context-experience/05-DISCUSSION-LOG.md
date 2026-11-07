# Phase 5: Agent Context Experience - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-18
**Phase:** 05-agent-context-experience
**Areas discussed:** CLI Interface Design, Search Integration Strategy, Database Schema & Constraints

---

## CLI Interface Design

| Option | Description | Selected |
|--------|-------------|----------|
| `context add <type> <target> <content>` (3 positional args) | Type-first, matches SPEC wording directly | ✓ |
| `context add <target> --type <type> <content>` (option-style) | Target-first, closer to existing CLI pattern | |

**User's choice:** `context add <type> <target> <content>` (3 positional args)
**Notes:** User preferred type-first as it matches the SPEC requirement "`context add <type> <target> <content>` accepts type" most directly.

---

## Collection Target Resolution

| Option | Description | Selected |
|--------|-------------|----------|
| Collection name only | Consistent with other collection CLI commands | |
| Collection ID only | Precise but not user-friendly | |
| Name-first with ID fallback | Most flexible, name is primary UX | ✓ |

**User's choice:** Name-first with ID fallback
**Notes:** Try `get_by_name(target)` first, if no match and target looks like a UUID, try `get_by_id(target)`.

---

## Search Integration Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| SQL JOIN (single query) | LEFT JOIN contexts in search SQL. No N+1 but changes all search SQL | |
| Python-layer batch query (IN query) | Collect paths, single `IN` query, map back. Clean separation, no N+1 | ✓ |
| Per-result individual query | Simplest code but N+1 problem | |

**User's choice:** Python-layer batch query (IN query)
**Notes:** Avoids N+1, doesn't modify existing search SQL, and keeps search strategies focused on their primary job.

---

## context_type Constraint Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Application-layer only | Click Choice + Pydantic. Matches existing schema patterns (no CHECK constraints) | |
| Database CHECK + application dual | SQLite CHECK constraint plus Click/Pydantic validation. Safest | ✓ |
| Separate enum table + FK | Over-engineered for 3 fixed values | |

**User's choice:** Database CHECK + application dual validation
**Notes:** Provides defense in depth. CHECK constraint prevents bad data at the database level, application validation ensures good UX.

---

## Claude's Discretion

- Exact error message wording for migration failure
- `context list` output formatting (table columns, truncation length)
- Whether to add `--json` or `--format` options to `context list`
- Migration timestamp tracking

## Deferred Ideas

- MCP server returning context descriptions — Phase 6+
- Collection/global context injection into `SearchContext.context_string` — Phase 6+
- `--format` flag for `context list` — nice-to-have
- Context description semantic relevance filtering — future enhancement
