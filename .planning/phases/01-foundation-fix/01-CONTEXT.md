# Phase 1: Foundation Fix - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Core indexing and search infrastructure is trustworthy and free of critical bugs, stubs, and missing dependencies.
</domain>

<decisions>
## Implementation Decisions

### FTS5 Synchronization
- **D-01:** Use SQLite triggers to automatically synchronize FTS5 external content tables with the main `documents` and `document_chunks` tables. Triggers are created in `SchemaManager` alongside the tables they protect.

### Repository Consolidation
- **D-02:** Consolidate all database access into `src/docsift/database/repositories.py`. Migrate any unique functionality from `src/docsift/database/sqlite_repository.py`, then delete the duplicate file.
- **D-03:** `SchemaManager` (in `schema.py`) remains the single source of truth for table and trigger definitions.

### SQLite Connection Safety
- **D-04:** CLI commands continue using `Database.transaction()` context manager with a single connection.
- **D-05:** Async/multi-threaded contexts (e.g., MCP HTTP server) create a new `sqlite3.Connection` per request. No shared cached connections across threads or async tasks.

### Vector Search Fallback
- **D-06:** Make `sqlite-vec` a hard runtime requirement for vector search. Remove the brute-force Python fallback in `VectorSearcher`.
- **D-07:** If `sqlite-vec` is unavailable, `VectorSearcher` must raise a clear runtime error rather than silently falling back to BM25 or loading all embeddings into memory.

### Dependency Strategy
- **D-08:** Add all missing runtime dependencies to `pyproject.toml` under `dependencies` (not just dev/test). This includes `sqlite-vec`, `platformdirs`, `pydantic`, `pydantic-settings`, `python-frontmatter`, `watchdog`, `fastapi`, and `uvicorn`. Exclude `structlog` because it is not imported anywhere in the codebase.
- **D-09:** Keep `llama-cpp-python` and `sentence-transformers` as optional extras (`[embed]` or `[llm]`) because they pull in heavy native libraries.

### Claude's Discretion
- Exact trigger SQL syntax and naming convention
- Migration path for users with existing databases that lack triggers
- Specific error message wording for sqlite-vec failures

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` § Foundation (Bugfix & Stub Removal) — FND-01 through FND-08
- `.planning/ROADMAP.md` § Phase 1: Foundation Fix — goal, success criteria, and requirements mapping

### Codebase
- `src/docsift/database/schema.py` — current schema and FTS5 table definitions
- `src/docsift/database/repositories.py` — target unified repository layer
- `src/docsift/database/sqlite_repository.py` — duplicate repository layer to be merged and deleted
- `src/docsift/database/database.py` — connection manager and `Database` class
- `src/docsift/search/vector.py` — `VectorSearcher` with fallback logic to be removed
- `src/docsift/embedding/factory.py` — embedding factory with stub/random implementations
- `pyproject.toml` — dependency declarations

### Research
- `.planning/research/PITFALLS.md` — known pitfalls for FTS5, SQLite threading, and placeholder embeddings
- `.planning/research/STACK.md` — recommended library versions including `sqlite-vec>=0.1.9`
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SchemaManager` already creates FTS5 virtual tables; it is the right place to add trigger definitions.
- `repositories.py` already has `CollectionRepository`, `DocumentRepository`, `DocumentChunkRepository`, and `PathContextRepository` — these are the canonical interfaces.

### Established Patterns
- Repository pattern: one repository per aggregate root.
- Database transactions use context manager with automatic rollback on exception.
- Graceful degradation with console warnings (but for this phase, vector search must fail fast instead).

### Integration Points
- Triggers must be created/migrated alongside the existing schema initialization flow.
- `repositories.py` is consumed by CLI (`src/docsift/cli/`) and MCP server (`src/docsift/mcp/`).
- `VectorSearcher` is consumed by `HybridSearcher` and the CLI search commands.
</code_context>

<specifics>
## Specific Ideas

- No specific requirements beyond the decisions above — open to standard approaches.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.
</deferred>

---

*Phase: 01-foundation-fix*
*Context gathered: 2026-04-14*
