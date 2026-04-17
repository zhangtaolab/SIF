# Phase 5: Agent Context Experience - Research

**Researched:** 2026-04-18
**Domain:** SQLite schema migration, Click CLI patterns, search result enrichment
**Confidence:** HIGH

## Summary

This phase migrates the existing `path_contexts` table to a unified `contexts` table supporting path, collection, and global scopes; extends the CLI to manage all context types; and attaches path context descriptions to search results across BM25, vector, and hybrid search strategies.

All critical technical decisions have been verified through direct testing:
- SQLite SAVEPOINTs enable atomic DDL migration with rollback on failure [VERIFIED: direct testing]
- Click 8.3.2 does not support command aliases natively; the `add_command` twice pattern works [VERIFIED: direct testing]
- Adding `context_description` to `SearchResult` with `default=None` preserves backward compatibility [VERIFIED: direct testing]
- The batch-query-then-map pattern for context enrichment avoids N+1 queries without modifying search SQL [VERIFIED: direct testing]

**Primary recommendation:** Implement migration via SchemaManager using SAVEPOINT for atomicity; use `cli.add_command(remove_cmd, name="rm")` for the alias; add `_attach_contexts()` helper to each search strategy class, called at the final return point.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Schema migration | Database (SchemaManager) | — | SQLite DDL and data migration belong in the schema layer |
| Context CRUD | Database (ContextRepository) | — | Repository pattern owns all DB access per CLAUDE.md |
| CLI command handling | CLI (context.py) | — | Click commands parse input, delegate to repositories |
| Collection name resolution | CLI (context.py) | — | Name-first resolution is a CLI concern, not repository |
| Search result enrichment | Search (BM25/Vector/Hybrid/Pipeline) | — | Each searcher enriches its own final results |
| Orphaned context cleanup | CLI (prune command) | Database | CLI triggers, repository executes DELETE |

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** `context add` uses three positional arguments: `context add <type> <target> <content>`
  - `type`: One of `path`, `collection`, `global`
  - `target`: For `path` type → file path string; for `collection` type → collection name (resolved first by name, fallback to ID); for `global` type → ignored (any value accepted, stored as `"global"`)
  - `content`: The contextual description text
- **D-02:** Collection target resolution is name-first: CLI attempts `CollectionRepository.get_by_name(target)`, and if no match, falls back to treating `target` as a collection ID directly
- **D-03:** `rm` is registered as an alias for the `remove` subcommand via `cli.add_command(remove_cmd, name="rm")` or equivalent Click mechanism
- **D-04:** `context list` supports optional `--type` filter; without it, lists all contexts sorted by `context_type` then `target_id`
- **D-05:** `context remove` (and `rm`) accepts a context ID (UUID), not a target name/path
- **D-06:** Context descriptions are attached to search results via **Python-layer batch query** (not SQL JOIN)
  - Step 1: Search strategy returns `list[SearchResult]` as usual
  - Step 2: Collect all unique `result.path` values from results
  - Step 3: Execute single query: `SELECT target_id, content FROM contexts WHERE context_type = 'path' AND target_id IN (?)`
  - Step 4: Map results back to `SearchResult.context_description` field
- **D-07:** Only **path** contexts are attached to search results in this phase
- **D-08:** `SearchResult.context_description` is `str | None`; full text included without truncation at search layer
- **D-09:** Database CHECK + application-layer dual validation for `context_type`
- **D-10:** Migration is **atomic**: `SchemaManager` wraps table creation, data migration, and old-table drop in a single SQLite transaction (via SAVEPOINT). On failure, rolls back and prints error to stderr
- **D-11:** The old `path_contexts` table is **dropped** after successful migration
- **D-12:** `context prune` scans `contexts` where `context_type='path'`, checks `target_id` against `documents` table, deletes records for missing paths. Prints count of deleted records
- **D-13:** Document deletion/renaming does **not** auto-delete associated path contexts

### Claude's Discretion
- Exact error message wording for migration failure
- `context list` output formatting (table columns, truncation length)
- Whether to add `--json` or `--format` options to `context list`
- Migration timestamp tracking (whether to record when migration happened)

### Deferred Ideas (OUT OF SCOPE)
- MCP server returning context descriptions in tool responses
- Automatic injection of collection/global contexts into `SearchContext.context_string` for query expansion
- Interactive or bulk import of contexts from files
- Semantic relevance filtering for context descriptions
- Automatic cascade deletion on document removal
- `DOCUMENT` context type

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CTX-01 | `context add`: attach descriptions to paths/collections/global | Click Choice validation, collection name resolution pattern, ContextRepository CRUD |
| CTX-02 | `context list` and `context rm`: view and delete contexts | Click alias pattern (`add_command` twice), repository list_by_type, delete by ID |
| CTX-03 | Context descriptions carried in search results | Batch query pattern, SearchResult field extension, enrichment at final return point |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Click | 8.3.2 | CLI framework | Already used throughout project; `Choice` type for context_type validation [VERIFIED: `python -c "import click; print(click.__version__)"`] |
| sqlite3 | 3.51.0 | Database | Built-in; SAVEPOINT supports DDL rollback [VERIFIED: direct testing] |
| Pydantic | 2.x | Settings/models | Already used in `models/context.py` for `ContextType` str enum |
| rich | latest | Table output | Already used in CLI for formatted output |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| uuid | stdlib | Context ID generation | Already used in all repository create methods |
| datetime | stdlib | Timestamp fields | Already used in repository layer |

## Architecture Patterns

### System Architecture Diagram

```
User Input (CLI)
    |
    v
+----------------------------------+
| Click CLI (context.py)           |
| - context add <type> <target> <content>  |
| - context list [--type]          |
| - context remove <id>  + rm alias|
| - context prune                  |
+----------------------------------+
    |
    v
+----------------------------------+
| Collection Name Resolution       |
| (name-first: get_by_name ->      |
|  fallback to get_by_id)          |
+----------------------------------+
    |
    v
+----------------------------------+
| ContextRepository (repositories) |
| - create / get_by_id / get_by_target |
| - list_all / list_by_type        |
| - update / delete / delete_by_target |
+----------------------------------+
    |
    v
+----------------------------------+
| SQLite Database                  |
| - contexts table (unified)       |
| - SchemaManager migration logic  |
+----------------------------------+

Search Path (separate flow):
+----------------------------------+
| SearchPipeline / HybridSearcher  |
| / BM25Searcher / VectorSearcher  |
+----------------------------------+
    |
    v
+----------------------------------+
| _attach_contexts() helper        |
| Batch query: SELECT target_id,   |
| content FROM contexts WHERE      |
| context_type='path' AND target_id|
| IN (paths from results)          |
+----------------------------------+
    |
    v
+----------------------------------+
| SearchResult.context_description |
| populated for matching paths     |
+----------------------------------+
```

### Recommended Project Structure

```
src/docsift/
├── cli/commands/context.py       # Extended: add/list/remove/prune for all types
├── core/models.py                # SearchResult + context_description field
├── core/context.py               # ContextManager (already exists, wire to repo)
├── database/schema.py            # SchemaManager: migration + contexts table
├── database/repositories.py      # PathContextRepository -> ContextRepository
└── search/{bm25,vector,hybrid}.py # Add _attach_contexts() helper
```

### Pattern 1: Atomic Schema Migration with SAVEPOINT
**What:** Wrap table creation, data migration, and old-table drop in a SQLite SAVEPOINT for atomic rollback on failure.
**When to use:** Any DDL migration that must be atomic, especially when SQLite is in default mode (DDL auto-commits).
**Why SAVEPOINT instead of transaction:** SQLite's default mode auto-commits DDL statements. `BEGIN` + `ROLLBACK` does NOT rollback `CREATE TABLE` in default mode. SAVEPOINT does. [VERIFIED: direct testing]

**Example:**
```python
# Source: verified via direct SQLite testing
def _migrate_path_contexts(self) -> None:
    """Migrate path_contexts -> contexts atomically."""
    cursor = self.db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='path_contexts'"
    )
    if not cursor.fetchone():
        return  # Nothing to migrate

    self.db.execute("SAVEPOINT sp_migration")
    try:
        # Create new table if not exists
        self._create_contexts_table()
        # Migrate data
        self.db.execute("""
            INSERT INTO contexts (id, target_id, context_type, content, created_at, updated_at)
            SELECT id, path, 'path', context, created_at, updated_at
            FROM path_contexts
        """)
        # Drop old table
        self.db.execute("DROP TABLE path_contexts")
        # Create index
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_contexts_target
            ON contexts(target_id, context_type)
        """)
        self.db.execute("RELEASE SAVEPOINT sp_migration")
    except Exception as e:
        self.db.execute("ROLLBACK TO SAVEPOINT sp_migration")
        print(f"Migration failed: {e}", file=sys.stderr)
        raise
```

### Pattern 2: Click Command Alias
**What:** Register the same command function under two names using `add_command(cmd, name="alias")`.
**When to use:** When Click version does not support native aliases (Click < 9.x).
**Example:**
```python
# Source: verified via direct Click testing
@context_group.command("remove")
@click.argument("context_id")
def context_remove(context_id: str) -> None:
    """Remove a context by ID."""
    ...

# Register alias
context_group.add_command(context_remove, name="rm")
```

### Pattern 3: Batch Context Enrichment
**What:** After search returns results, collect unique paths, execute a single batch query for contexts, then map back to results.
**When to use:** When you need to attach related data to search results without modifying the search SQL.
**Example:**
```python
# Source: verified via direct SQLite testing
def _attach_contexts(self, results: list[SearchResult]) -> list[SearchResult]:
    if not results:
        return results
    paths = list({r.path for r in results})
    placeholders = ", ".join(["?"] * len(paths))
    sql = f"""
        SELECT target_id, content FROM contexts
        WHERE context_type = 'path' AND target_id IN ({placeholders})
    """
    cursor = self.db.execute(sql, paths)
    context_map = {row["target_id"]: row["content"] for row in cursor.fetchall()}
    for result in results:
        result.context_description = context_map.get(result.path)
    return results
```

### Anti-Patterns to Avoid
- **Modifying search SQL to JOIN contexts:** This would require changes to every search query and complicates the already-complex vector search SQL. The batch query pattern (D-06) is cleaner.
- **Enriching before RRF fusion:** RRF creates new `SearchResult` objects and does not copy `context_description`. Enrichment must happen at the final return point of each searcher.
- **Using SQLite transactions (BEGIN/COMMIT) for DDL migration:** In SQLite's default mode, DDL auto-commits and cannot be rolled back with `ROLLBACK`. Use SAVEPOINT instead.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Command aliases | Custom Click subclass or decorator hacking | `group.add_command(cmd, name="alias")` | Click 8.3.2 does not support `aliases` parameter; the `add_command` pattern is the standard workaround [VERIFIED: direct testing] |
| Context type validation | Manual string checking | `click.Choice(["path", "collection", "global"])` | Provides automatic validation, error messages, and help text |
| Collection name resolution | Custom resolution logic | `get_by_name()` then `get_by_id()` | Already established pattern in `collection.py` CLI commands |
| UUID detection | Regex matching | `uuid.UUID(s)` with try/except | Python stdlib handles all UUID formats correctly |

## Runtime State Inventory

This phase involves a table rename (`path_contexts` -> `contexts`) with data migration. After all file changes are complete, the following runtime state must be verified:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | SQLite databases with `path_contexts` table | Migration runs on next `Database.init_schema()` call (automatic) |
| Live service config | None — no external services | — |
| OS-registered state | None — no OS registrations | — |
| Secrets/env vars | None — no secrets affected | — |
| Build artifacts | `docsift` package installed in `.venv` | May need `pip install -e .` after model changes if imports break |

**Nothing found in category:** Live service config, OS-registered state, Secrets/env vars — verified by codebase inspection.

## Common Pitfalls

### Pitfall 1: SQLite DDL Not Rolling Back in Default Mode
**What goes wrong:** Wrapping migration in `Database.transaction()` (which uses `BEGIN`/`ROLLBACK`) does NOT rollback `CREATE TABLE` or `DROP TABLE` on error. The old table may be dropped while the new table was not properly populated.
**Why it happens:** SQLite auto-commits DDL statements in default mode. `ROLLBACK` only undoes DML (INSERT/UPDATE/DELETE) since the last implicit commit.
**How to avoid:** Use `SAVEPOINT` + `ROLLBACK TO SAVEPOINT` for atomic DDL operations. [VERIFIED: direct testing]
**Warning signs:** After a failed migration, `path_contexts` is missing but `contexts` is empty or has partial data.

### Pitfall 2: Rerankers Losing context_description
**What goes wrong:** `SearchResult.context_description` is populated by `HybridSearcher.search()`, but then `SearchPipeline` calls the reranker which constructs brand-new `SearchResult` objects without copying `context_description`. The field becomes `None` in final results.
**Why it happens:** `LlamaCppReranker.rerank()` and `CrossEncoderReranker.rerank()` both create new `SearchResult(...)` objects from scratch. `RRFFusion.fuse()` also creates new objects.
**How to avoid:** Each searcher must call `_attach_contexts()` at its **final** return point, AFTER any fusion or reranking. `SearchPipeline.search()` must enrich at the very end.
**Warning signs:** BM25 search returns `context_description` but hybrid search does not.

### Pitfall 3: Positional Arg Breakage from SearchResult Field Addition
**What goes wrong:** Adding `context_description` to `SearchResult` dataclass could break tests that use positional arguments.
**Why it happens:** `tests/test_docsift_complete.py` uses positional args: `SearchResult("doc1", "Doc 1", "/path/1", "coll", 0.9, rank=1)`.
**How to avoid:** Add the new field at the **end** of the dataclass with `default=None`. The first 5 positional args map to the first 5 required fields; remaining fields are keyword-only in practice. [VERIFIED: direct testing]
**Warning signs:** `TypeError: SearchResult.__init__() takes X positional args but Y were given` in tests.

### Pitfall 4: Collection Target Resolution Ambiguity
**What goes wrong:** A collection name that looks like a UUID (e.g., "550e8400-e29b-41d4-a716-446655440000") could be resolved as a name when the user intended it as an ID, or vice versa.
**Why it happens:** Per D-02, resolution is name-first. If a collection happens to have a UUID-like name, `get_by_name()` will find it first.
**How to avoid:** This is the intended behavior per D-02. Document it clearly. Users can rename collections to avoid UUID-like names.
**Warning signs:** `context add collection <uuid-looking-string>` attaches to the wrong collection.

### Pitfall 5: Broken ContextFactory in Tests
**What goes wrong:** `tests/factories.py` `ContextFactory.create()` passes `metadata` to `Context` dataclass, but `Context` does not have a `metadata` field. This causes `TypeError` if the factory is ever used.
**Why it happens:** Pre-existing bug — `Context` dataclass in `core/context.py` lacks `metadata` but the factory assumes it exists.
**How to avoid:** Fix `ContextFactory` to not pass `metadata` (or add `metadata` to `Context` if needed). Since the factory is unused in current tests, this is low risk.
**Warning signs:** `TypeError: Context.__init__() got an unexpected keyword argument 'metadata'` when writing new tests.

## Code Examples

### SQLite SAVEPOINT Migration (Verified Pattern)
```python
# Source: verified via direct SQLite testing on 3.51.0
conn.execute("SAVEPOINT sp_migration")
try:
    conn.execute("CREATE TABLE contexts (...)")
    conn.execute("INSERT INTO contexts SELECT ... FROM path_contexts")
    conn.execute("DROP TABLE path_contexts")
    conn.execute("RELEASE SAVEPOINT sp_migration")
except Exception:
    conn.execute("ROLLBACK TO SAVEPOINT sp_migration")
    raise
```

### Click Alias Registration (Verified Pattern)
```python
# Source: verified via direct Click 8.3.2 testing
@context_group.command("remove")
@click.argument("context_id")
def context_remove(context_id: str) -> None:
    """Remove a context by ID."""
    ...

context_group.add_command(context_remove, name="rm")
```

### Batch Context Query (Verified Pattern)
```python
# Source: verified via direct SQLite testing
paths = ["/path/a", "/path/b", "/path/c"]
placeholders = ", ".join(["?"] * len(paths))
sql = f"""
    SELECT target_id, content FROM contexts
    WHERE context_type = 'path' AND target_id IN ({placeholders})
"""
cursor = db.execute(sql, paths)
context_map = {row["target_id"]: row["content"] for row in cursor.fetchall()}
```

### SearchResult with New Field (Backward Compatible)
```python
# Source: verified via direct Python testing
@dataclass
class SearchResult:
    document_id: str
    title: str
    path: str
    collection_name: str
    score: float
    content: str | None = None
    highlights: list[str] = field(default_factory=list)
    rank: int = 0
    scores: dict = field(default_factory=dict)
    snippet: str | None = None
    context_description: str | None = None  # NEW - added at end with default

# All these work:
r1 = SearchResult("id", "title", "/path", "col", 0.5)  # positional (tests)
r2 = SearchResult(document_id="id", title="title", path="/path", collection_name="col", score=0.5)  # keyword (src)
r3 = SearchResult("id", "title", "/path", "col", 0.5, context_description="desc")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `path_contexts` table (path-only) | `contexts` table (unified) | Phase 5 | Supports collection and global scopes |
| `PathContextRepository` | `ContextRepository` | Phase 5 | Unified CRUD for all context types |
| `context add <path> <text>` | `context add <type> <target> <content>` | Phase 5 | Supports all context types via single interface |

**Deprecated/outdated:**
- `PathContext` dataclass: Still exists in `core/models.py` but should be replaced by `Context` from `core/context.py` for new code. Keep for backward compatibility during migration.
- `path_contexts` table: Dropped after migration. No code should reference it post-migration.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `Context` dataclass from `core/context.py` (not `models/context.py` ContextResponse) is the correct domain model for repository operations | Standard Stack | Repository would use wrong model, causing serialization issues |
| A2 | `SearchResult` field order is stable; adding at end with `default=None` won't break existing code | Code Examples | Tests using positional args would fail |
| A3 | SAVEPOINT rollback works correctly for DDL in SQLite 3.51.0 with the project's Database connection settings | Common Pitfalls | Migration could leave database in inconsistent state |
| A4 | All search strategies construct `SearchResult` objects with keyword arguments only | Architecture Patterns | Adding a field in the middle would break positional construction in src/ |
| A5 | The `database/repository.py` (singular) abstract `ContextRepository` does not need updating for this phase — only the concrete `repositories.py` (plural) implementation changes | Standard Stack | Abstract interface mismatch if repository.py is also used |

## Open Questions

1. **Should `context list` display the full context content or truncate it?**
   - What we know: D-08 says CLI formatters may truncate for display; current `context list` truncates to 50 chars
   - What's unclear: Whether to keep 50-char truncation or adjust for the new table format (which includes type and target columns)
   - Recommendation: Keep truncation at ~50 chars but add type/target columns to the rich table

2. **Should the migration record a timestamp or version number?**
   - What we know: D-10 mentions atomic migration with rollback; deferred ideas mention "migration timestamp tracking"
   - What's unclear: Whether to add a `schema_migrations` table or similar
   - Recommendation: Skip for this phase. The absence of `path_contexts` table is sufficient evidence of successful migration.

3. **How should `context add` handle updating an existing context for the same target?**
   - What we know: The existing `context_add` in `context.py` updates if path already exists. `ContextManager.add_context()` in `core/context.py` also does upsert.
   - What's unclear: Whether collection and global contexts should also upsert
   - Recommendation: Yes, upsert for all types. A target should have at most one context of each type. This matches the existing behavior and the `UNIQUE(context_type, target_id)` constraint in `migrations.py`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All | Yes | 3.13 | — |
| Click | CLI | Yes | 8.3.2 | — |
| SQLite | Database | Yes | 3.51.0 | — |
| rich | CLI output | Yes | latest | — |
| pytest | Testing | Yes | latest | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` (implicit) |
| Quick run command | `pytest tests/unit/search/test_bm25.py -x` |
| Full suite command | `pytest` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CTX-01 | `context add path /notes/a.md "desc"` creates path context | unit | `pytest tests/unit/cli/test_context.py -x` | No — Wave 0 |
| CTX-01 | `context add collection my-coll "desc"` resolves name and creates collection context | unit | `pytest tests/unit/cli/test_context.py -x` | No — Wave 0 |
| CTX-01 | `context add global global "desc"` creates global context | unit | `pytest tests/unit/cli/test_context.py -x` | No — Wave 0 |
| CTX-02 | `context list --type collection` filters by type | unit | `pytest tests/unit/cli/test_context.py -x` | No — Wave 0 |
| CTX-02 | `context rm <id>` deletes context (alias verified) | unit | `pytest tests/unit/cli/test_context.py -x` | No — Wave 0 |
| CTX-03 | BM25 search returns `context_description` for document with path context | unit | `pytest tests/unit/search/test_bm25.py -x` | Yes |
| CTX-03 | Vector search returns `context_description` for document with path context | unit | `pytest tests/unit/search/test_vector.py -x` | Yes |
| CTX-03 | Hybrid search returns `context_description` for document with path context | unit | `pytest tests/unit/search/test_hybrid.py -x` | Yes |
| Migration | `path_contexts` data migrated to `contexts` with `context_type='path'` | unit | `pytest tests/unit/database/test_schema.py -x` | Yes (extend) |
| Migration | Old table dropped after successful migration | unit | `pytest tests/unit/database/test_schema.py -x` | Yes (extend) |
| Prune | `context prune` deletes orphaned path contexts | unit | `pytest tests/unit/cli/test_context.py -x` | No — Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/unit/cli/test_context.py tests/unit/search/test_bm25.py tests/unit/search/test_hybrid.py -x`
- **Per wave merge:** `pytest tests/unit/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/cli/test_context.py` — covers CTX-01, CTX-02 CLI acceptance criteria
- [ ] `tests/unit/database/test_schema.py` additions — covers migration acceptance criteria
- [ ] `tests/unit/db/test_repositories.py` real repository tests — covers ContextRepository CRUD (currently only mock tests exist)

## Security Domain

This phase does not introduce new security-sensitive functionality. Context descriptions are user-provided text stored locally in SQLite. No network access, authentication, or authorization changes.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | — |
| V3 Session Management | No | — |
| V4 Access Control | No | — |
| V5 Input Validation | Yes | `click.Choice` for context_type; Pydantic `min_length=1` for content |
| V6 Cryptography | No | — |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection in batch query | Tampering | Parameterized query with `?` placeholders (already used) |
| Context type bypass | Tampering | Database CHECK constraint + Click Choice dual validation |

## Sources

### Primary (HIGH confidence)
- Direct SQLite 3.51.0 testing — SAVEPOINT DDL rollback, batch query pattern, CHECK constraints
- Direct Click 8.3.2 testing — alias registration via `add_command`, `Choice` validation
- Direct Python dataclass testing — `SearchResult` backward compatibility with new field
- Codebase inspection — `src/docsift/search/rrf.py`, `src/docsift/search/rerank.py` — verified new `SearchResult` creation

### Secondary (MEDIUM confidence)
- `src/docsift/database/schema.py` — existing `SchemaManager` patterns
- `src/docsift/cli/commands/collection.py` — collection name resolution pattern
- `src/docsift/database/repositories.py` — `PathContextRepository` implementation
- `src/docsift/core/context.py` — `ContextManager` and `ContextRepository` protocol

### Tertiary (LOW confidence)
- None — all claims verified through direct testing or codebase inspection

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified via direct testing
- Architecture: HIGH — all patterns verified via direct testing
- Pitfalls: HIGH — DDL rollback and reranker recreation verified via direct testing

**Research date:** 2026-04-18
**Valid until:** 2026-05-18 (stable stack — SQLite, Click, Pydantic are slow-moving)
