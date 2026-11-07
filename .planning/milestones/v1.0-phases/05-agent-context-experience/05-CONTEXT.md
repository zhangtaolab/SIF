# Phase 5: Agent Context Experience - Context

**Gathered:** 2026-04-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Allow users to augment document collections with contextual descriptions to improve retrieval quality for agent workflows.

This phase delivers:
- Unified `contexts` table supporting path, collection, and global scopes
- `context add/list/remove` CLI commands for all context types
- `context prune` command for manual orphaned-context cleanup
- Context descriptions automatically included in search results for matching documents
</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**4 requirements are locked.** See `05-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `05-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):**
- Database schema migration: `path_contexts` → unified `contexts` table with `context_type` enum
- `SchemaManager` migration logic (transactional, with rollback on failure)
- CLI command updates: `context add/list/remove` supporting path/collection/global
- `rm` as a CLI alias for `remove`
- `SearchResult` field addition (`context_description`)
- Search strategy updates (BM25, Vector, Hybrid) to query and attach path contexts
- `context prune` command for manual orphaned-context cleanup

**Out of scope (from SPEC.md):**
- MCP server returning context descriptions in tool responses
- Automatic injection of collection/global contexts into `SearchContext.context_string` for query expansion
- Interactive or bulk import of contexts from files
- Semantic relevance filtering for context descriptions
- Automatic cascade deletion on document removal
- `DOCUMENT` context type
</spec_lock>

<decisions>
## Implementation Decisions

### CLI Interface Design
- **D-01:** `context add` uses three positional arguments: `context add <type> <target> <content>`
  - `type`: One of `path`, `collection`, `global`
  - `target`: For `path` type → file path string; for `collection` type → collection name (resolved first by name, fallback to ID); for `global` type → ignored (any value accepted, stored as `"global"`)
  - `content`: The contextual description text
- **D-02:** Collection target resolution is name-first: CLI attempts `CollectionRepository.get_by_name(target)`, and if no match, falls back to treating `target` as a collection ID directly
- **D-03:** `rm` is registered as an alias for the `remove` subcommand via `@click.command("remove", aliases=["rm"])` or equivalent Click mechanism
- **D-04:** `context list` supports optional `--type` filter; without it, lists all contexts sorted by `context_type` then `target_id`
- **D-05:** `context remove` (and `rm`) accepts a context ID (UUID), not a target name/path — this is unambiguous and consistent with database-level deletion

### Search Integration Strategy
- **D-06:** Context descriptions are attached to search results via **Python-layer batch query** (not SQL JOIN)
  - Step 1: Search strategy returns `list[SearchResult]` as usual
  - Step 2: Collect all unique `result.path` values from results
  - Step 3: Execute single query: `SELECT target_id, content FROM contexts WHERE context_type = 'path' AND target_id IN (?)`
  - Step 4: Map results back to `SearchResult.context_description` field
  - This avoids N+1 queries and does not require modifying existing search SQL
- **D-07:** Only **path** contexts are attached to search results in this phase. Collection and global contexts are stored but not injected into search results (per SPEC.md scope)
- **D-08:** `SearchResult.context_description` is `str | None`; the full text is included without truncation at the search layer. CLI formatters may truncate for display

### Database Schema & Constraints
- **D-09:** The `contexts` table uses **database CHECK + application-layer dual validation**
  - SQLite: `context_type TEXT NOT NULL CHECK(context_type IN ('path', 'collection', 'global'))`
  - Click CLI: `@click.argument("type", type=click.Choice(["path", "collection", "global"]))`
  - Pydantic (if applicable): `Literal["path", "collection", "global"]` or enum validation
- **D-10:** Migration is **atomic**: `SchemaManager` wraps table creation, data migration, and old-table drop in a single SQLite transaction. On failure, rolls back and prints error to stderr
- **D-11:** The old `path_contexts` table is **dropped** after successful migration, not kept as a view or backup

### Orphaned Context Handling
- **D-12:** `context prune` scans `contexts` where `context_type='path'`, checks `target_id` against `documents` table, and deletes records for missing paths. Prints count of deleted records
- **D-13:** Document deletion/renaming does **not** auto-delete associated path contexts. Cleanup is always explicit via `prune`

### Claude's Discretion
- Exact error message wording for migration failure
- `context list` output formatting (table columns, truncation length)
- Whether to add `--json` or `--format` options to `context list`
- Migration timestamp tracking (whether to record when migration happened)
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap
- `.planning/phases/05-agent-context-experience/05-SPEC.md` — Locked requirements, boundaries, acceptance criteria
- `.planning/REQUIREMENTS.md` § Context & Agent Experience — CTX-01, CTX-02, CTX-03
- `.planning/ROADMAP.md` § Phase 5: Agent Context Experience — goal and success criteria

### Prior Phase Context
- `.planning/phases/04-advanced-search-pipeline/04-CONTEXT.md` — Search strategy patterns, `SearchResult` dataclass extension approach, `SearchPipeline.search()` integration points
- `.planning/phases/02-cli-core-completion/02-CONTEXT.md` — CLI command patterns, `ctx.obj["index_path"]`, `Database` + repository usage, `click.ClickException` for errors, collection name resolution patterns
- `.planning/phases/01-foundation-fix/01-CONTEXT.md` — `SchemaManager` table creation patterns, SQLite transaction safety

### Existing Code (Patterns to Follow)
- `src/docsift/cli/commands/context.py` — Existing path-only context CLI (add/remove/list)
- `src/docsift/core/context.py` — `ContextManager` with abstract `ContextType` enum and `ContextRepository` protocol
- `src/docsift/models/context.py` — Pydantic models for Context operations (`ContextType`, `ContextCreate`, `ContextResponse`)
- `src/docsift/database/schema.py` — `SchemaManager._create_path_contexts_table()` and `_create_indexes()`
- `src/docsift/database/repositories.py` — `PathContextRepository` (to be migrated/renamed)
- `src/docsift/core/models.py` — `PathContext` dataclass and `SearchResult` dataclass
- `src/docsift/search/strategy.py` — `SearchContext` dataclass and `SearchStrategy` ABC
- `src/docsift/search/bm25.py` — `BM25Searcher.search()` result construction
- `src/docsift/search/vector.py` — `VectorSearcher.search()` result construction
- `src/docsift/search/hybrid.py` — `HybridSearcher.search()` and `SearchPipeline`
- `src/docsift/cli/commands/collection.py` — Collection name resolution patterns (`get_by_name`)
- `src/docsift/cli/main.py` — CLI group registration
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `PathContextRepository` in `repositories.py` — rename to `ContextRepository` and extend with `context_type` support. Existing CRUD methods map naturally.
- `ContextManager` in `core/context.py` — already has `ContextType` enum and `build_search_context()` method. `add_context()` already handles upsert (update if exists for target).
- `Context` Pydantic models in `models/context.py` — `ContextType` enum values map to database strings.
- `SearchResult` dataclass in `core/models.py` — can be extended with `context_description: Optional[str] = None` without breaking existing code.

### Established Patterns
- CLI commands get `index_path` from `ctx.obj`, create `Database`, and operate within `db.connection` or `db.transaction()` blocks.
- User-facing errors raise `click.ClickException(str(e))`.
- SchemaManager creates tables in `_create_tables()` and indexes in `_create_indexes()`.
- Repository pattern: one repository class per domain entity, operating on a `sqlite3.Connection`.
- Collection name resolution: `CollectionRepository.get_by_name(name)` returns `Collection | None`.

### Integration Points
- `src/docsift/cli/commands/context.py` — expand existing commands to support all context types.
- `src/docsift/database/schema.py` — replace `_create_path_contexts_table()` with `_create_contexts_table()`, add migration logic.
- `src/docsift/database/repositories.py` — migrate `PathContextRepository` → `ContextRepository` with `context_type` filter params.
- `src/docsift/search/bm25.py`, `vector.py`, `hybrid.py` — after building `list[SearchResult]`, query contexts and populate `context_description`.
- `src/docsift/core/models.py` — add `context_description` field to `SearchResult`.
- `src/docsift/cli/main.py` — register `context prune` subcommand.
</code_context>

<specifics>
## Specific Ideas

- `context add global global "This is a global context"` — the second `global` is a dummy target (ignored), required by the 3-positional-arg signature.
- For collection name resolution: try `CollectionRepository.get_by_name(target)` first, then if `target` looks like a UUID (36 chars with dashes), try `get_by_id(target)`.
- `context prune` should confirm before deleting if the count is high (>10), with a `--yes` flag to skip confirmation. But per SPEC minimal CLI, maybe skip confirmation entirely and just print the count.
- Context descriptions in search results: for JSON/CSV output, include as `context_description` field; for rich table, show as a separate column or tooltip (up to formatter discretion).
</specifics>

<deferred>
## Deferred Ideas

- MCP server returning context descriptions in tool responses — Phase 6+ consideration
- Automatic injection of collection/global contexts into `SearchContext.context_string` for query expansion — could enhance search quality but is out of scope for this phase
- `--format` flag for `context list` (json, csv, etc.) — nice-to-have, not required
- Context description search/relevance filtering — semantic matching between query and context descriptions

### Reviewed Todos (not folded)
- None — no relevant pending todos found.
</deferred>

---

*Phase: 05-agent-context-experience*
*Context gathered: 2026-04-18*
