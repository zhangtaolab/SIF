# Phase 1: Foundation Fix - Research

**Researched:** 2026-04-14
**Domain:** Python CLI/SQLite local search - bugfix, stub removal, dependency cleanup
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Use SQLite triggers to automatically synchronize FTS5 external content tables with the main `documents` and `document_chunks` tables. Triggers are created in `SchemaManager` alongside the tables they protect.
- **D-02:** Consolidate all database access into `src/docsift/database/repositories.py`. Migrate any unique functionality from `src/docsift/database/sqlite_repository.py`, then delete the duplicate file.
- **D-03:** `SchemaManager` (in `schema.py`) remains the single source of truth for table and trigger definitions.
- **D-04:** CLI commands continue using `Database.transaction()` context manager with a single connection.
- **D-05:** Async/multi-threaded contexts (e.g., MCP HTTP server) create a new `sqlite3.Connection` per request. No shared cached connections across threads or async tasks.
- **D-06:** Make `sqlite-vec` a hard runtime requirement for vector search. Remove the brute-force Python fallback in `VectorSearcher`.
- **D-07:** If `sqlite-vec` is unavailable, `VectorSearcher` must raise a clear runtime error rather than silently falling back to BM25 or loading all embeddings into memory.
- **D-08:** Add all missing runtime dependencies to `pyproject.toml` under `dependencies` (not just dev/test). This includes `sqlite-vec`, `structlog`, `platformdirs`, `pydantic`, `pydantic-settings`, `python-frontmatter`, `watchdog`, `fastapi`, and `uvicorn`.
- **D-09:** Keep `llama-cpp-python` and `sentence-transformers` as optional extras (`[embed]` or `[llm]`) because they pull in heavy native libraries.

### Claude's Discretion
- Exact trigger SQL syntax and naming convention
- Migration path for users with existing databases that lack triggers
- Specific error message wording for sqlite-vec failures

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FND-01 | Fix missing runtime dependencies in `pyproject.toml` (sqlite-vec, structlog, platformdirs, pydantic, fastapi/uvicorn, watchdog, python-frontmatter, etc.) | Verified current versions via `pip index versions`; core deps should be in `[project] dependencies`, heavy ML deps in `[project.optional-dependencies]` |
| FND-02 | Fix checksum comparison bug in indexing update logic (should skip unchanged docs, not skip changed docs) | Code audit shows inverted condition at `src/docsift/cli/commands/index.py:108` and `src/docsift/indexing/indexer.py:163` |
| FND-03 | Replace random/placeholder embedding implementations with real sentence-transformers and llama-cpp-python loading paths | `factory.py` contains `random.random()` stubs and `NotImplementedError` for OpenAI/HF; real backends verified via PyPI |
| FND-04 | Remove hardcoded model path `BAAI/bge-small-zh-v1.5`, read from Settings and allow CLI override | Hardcoded path found in `src/docsift/cli/commands/index.py:185`; Settings already has `model_name` and `model_path` fields |
| FND-05 | Unify or clean up duplicate database repository implementations (`repositories.py` vs `sqlite_repository.py`) | `sqlite_repository.py` uses old schema (`paths` instead of `path`, `contexts` table, etc.) and should be merged/deleted per D-02 |
| FND-06 | Fix FTS5 external content table synchronization so BM25 results stay consistent with main tables | Current schema creates FTS5 tables without `content=` / `content_rowid=` and no triggers; triggers are the standard SQLite solution |
| FND-07 | Fix vector search CLI fallback: `vsearch` should not unconditionally fall back to BM25 when embedder is unavailable | `vsearch_cmd` in `search.py:190-200` always prints warning and falls back; per D-06/D-07 it must fail fast or use real embeddings |
| FND-08 | Improve SQLite connection management to avoid race conditions in async/multi-threaded contexts | `Database` caches a single connection with `check_same_thread=False`; per D-05 HTTP contexts need connection-per-request |
</phase_requirements>

## Summary

Phase 1 is a foundational bugfix and stub-removal phase. The codebase has eight well-defined issues that all stem from early scaffolding: missing dependency declarations, inverted checksum logic, placeholder embedding implementations, hardcoded model paths, duplicate repository files, unsynchronized FTS5 tables, an unconditional BM25 fallback in vector search CLI, and unsafe SQLite connection sharing.

All eight requirements have clear, bounded fixes. The primary technical decisions (triggers for FTS5, repository consolidation, sqlite-vec as a hard requirement, connection-per-request for async) are already locked from the discuss phase. Research confirms these decisions align with SQLite best practices and the existing architecture.

**Primary recommendation:** Implement the locked decisions in dependency order: (1) fix `pyproject.toml` so the package installs cleanly, (2) consolidate repositories and schema, (3) fix indexing/search logic, (4) replace embedding stubs, (5) fix CLI commands to use Settings and fail fast, and (6) add connection safety for async contexts.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `click` | >=8.0.0 | CLI framework | Already integrated; stable, well-documented [VERIFIED: codebase] |
| `pydantic` | >=2.0 | Config models | Used by `Settings` class [VERIFIED: codebase] |
| `pydantic-settings` | >=2.0 | Env-var / `.env` loading | Required by `config/settings.py` [VERIFIED: codebase] |
| `rich` | >=13.0.0 | Terminal formatting | Powers tables and progress bars [VERIFIED: codebase] |
| `python-frontmatter` | >=1.0.0 | Markdown YAML frontmatter parsing | Used in parser [VERIFIED: codebase] |
| `platformdirs` | >=4.0.0 | Cross-platform data/cache directories | Used for DB/cache paths [VERIFIED: codebase] |
| `sqlite-vec` | >=0.1.9 | Vector similarity in SQLite | Verified latest on PyPI; required for vector search [VERIFIED: pip index versions] |
| `structlog` | >=25.0.0 | Structured logging | Referenced in `utils/logging.py` patterns [VERIFIED: pip index versions] |
| `watchdog` | >=6.0.0 | File system events | Referenced in project scope [VERIFIED: pip index versions] |
| `fastapi` | >=0.131.0 | MCP HTTP transport | Runtime import in `mcp_server/transport.py` [VERIFIED: pip index versions] |
| `uvicorn` | >=0.41.0 | ASGI server | Runtime import for HTTP mode [VERIFIED: pip index versions] |
| `numpy` | >=1.24.0 | Vector math | Required by sentence-transformers and sqlite-vec [VERIFIED: codebase] |

### Optional / Heavy
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `sentence-transformers` | >=2.2.0 (recommend >=5.4.0) | Default embedding backend | Optional extra `[embed]` [VERIFIED: pip index versions] |
| `llama-cpp-python` | >=0.3.20 | GGUF local embedding + reranking | Optional extra `[llm]` [VERIFIED: pip index versions] |

### Installation
```bash
# Core runtime
pip install -e .

# With optional embedding backends
pip install -e ".[embed,llm]"
```

## Architecture Patterns

### Recommended Change Sequence
```
1. pyproject.toml dependencies
2. database/schema.py (triggers + FTS5 external content)
3. database/repositories.py (consolidation)
4. delete sqlite_repository.py
5. embedding/factory.py (real implementations)
6. cli/commands/index.py (checksum fix + Settings-driven model)
7. cli/commands/search.py (vsearch fail-fast)
8. database/database.py (async connection safety)
```

### Pattern 1: FTS5 External Content Tables with Triggers
**What:** Create FTS5 virtual tables using `content='documents', content_rowid='id'`, then maintain them with `AFTER INSERT/UPDATE/DELETE` triggers on the source tables.
**When to use:** Any time FTS5 must stay synchronized with a main table without application-level bookkeeping.
**Example:**
```sql
-- Source: SQLite FTS5 documentation best practice
CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
    content,
    tokenize='porter',
    content='documents',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS documents_fts_insert
AFTER INSERT ON documents
BEGIN
    INSERT INTO documents_fts(rowid, content)
    VALUES (NEW.id, NEW.content);
END;

CREATE TRIGGER IF NOT EXISTS documents_fts_update
AFTER UPDATE ON documents
BEGIN
    INSERT INTO documents_fts(documents_fts, rowid, content)
    VALUES ('delete', OLD.id, OLD.content);
    INSERT INTO documents_fts(rowid, content)
    VALUES (NEW.id, NEW.content);
END;

CREATE TRIGGER IF NOT EXISTS documents_fts_delete
AFTER DELETE ON documents
BEGIN
    INSERT INTO documents_fts(documents_fts, rowid, content)
    VALUES ('delete', OLD.id, OLD.content);
END;
```
**Important:** When using `content=` and `content_rowid=`, the `rowid` in the FTS table corresponds to the source table's `id` column. You must explicitly include `rowid` in `INSERT` statements to avoid mismatches [CITED: .planning/research/PITFALLS.md Pitfall 5].

### Pattern 2: Repository Consolidation
**What:** Migrate any unique behavior from `sqlite_repository.py` into `repositories.py`, update all imports, then delete the legacy file.
**When to use:** When two files implement overlapping responsibilities and one is canonical.
**Key insight:** `sqlite_repository.py` uses an older schema (`paths` JSON list instead of `path` + `pattern`, `contexts` table instead of `path_contexts`). The canonical schema lives in `SchemaManager`, so `repositories.py` is the correct target. No meaningful logic needs to be preserved from `sqlite_repository.py`.

### Pattern 3: Connection-Per-Request for Async/Multi-Threaded SQLite
**What:** Instead of caching a single `sqlite3.Connection`, create a fresh connection for each request in async contexts.
**When to use:** FastAPI/uvicorn HTTP handlers, thread pools, or any concurrent environment.
**Example:**
```python
# In async HTTP handler
with DatabaseConnection(db_path).connect() as conn:
    repo = DocumentRepository(conn)
    ...
```
**For CLI:** Continue using `Database.transaction()` — single-threaded, context-manager is safe.

### Anti-Patterns to Avoid
- **FTS5 without `content=`:** Creates a second copy of all text and no automatic synchronization.
- **`check_same_thread=False` as a concurrency fix:** It bypasses Python's guard but does not make SQLite connections thread-safe.
- **Brute-force Python vector search:** Loading every embedding into memory scales linearly and will collapse on personal knowledge bases with tens of thousands of chunks.
- **Random embeddings in production:** Makes vector search meaningless and hides the problem until users notice bad results.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| FTS5 synchronization | Application-level bookkeeping | SQLite triggers + `content=` / `content_rowid=` | Triggers are atomic, zero maintenance, and officially supported |
| Vector similarity search | Brute-force Python cosine loops | `sqlite-vec` extension | SQLite-native, same DB file, handles serialization and memory |
| Dependency management | Manual `requirements.txt` only | `pyproject.toml` `[project] dependencies` + `[project.optional-dependencies]` | Standard Python packaging, installable via `pip install -e .` |
| Settings loading | Custom `os.environ` parsing | `pydantic-settings` | Already used, validates types, loads `.env` automatically |

**Key insight:** The current codebase already has stubs and fallbacks that were reasonable during scaffolding but are now technical debt. The fixes are all "use the real thing that was already planned."

## Common Pitfalls

### Pitfall 1: Inverted Checksum Condition
**What goes wrong:** `if existing.checksum != parsed.checksum and not force: skip` skips changed documents unless `--force` is passed.
**Why it happens:** A logic inversion during initial implementation.
**How to avoid:** Change to `if existing.checksum == parsed.checksum and not force: skip`.
**Warning signs:** Running `docsift index update` without `--force` never updates existing documents.
**Locations found:** `src/docsift/cli/commands/index.py:108` and `src/docsift/indexing/indexer.py:163` [VERIFIED: codebase audit].

### Pitfall 2: FTS5 `rowid` Mismatch
**What goes wrong:** Inserting into an external-content FTS5 table without specifying `rowid` causes SQLite to auto-generate a rowid that does not match the source table's primary key.
**Why it happens:** Developers treat FTS5 inserts like regular table inserts.
**How to avoid:** Always include `rowid` explicitly: `INSERT INTO documents_fts(rowid, content) VALUES (NEW.id, NEW.content)`.
**Warning signs:** BM25 queries return empty results even though documents exist.

### Pitfall 3: sqlite-vec Extension Loading Failures
**What goes wrong:** `load_extension("vec0")` fails on some systems because the library path differs or the extension is not installed.
**Why it happens:** `sqlite-vec` is a C extension; the Python package installs the shared library but SQLite's load path may not find it.
**How to avoid:** Use `sqlite_vec.load(conn)` (provided by the `sqlite-vec` Python package) instead of manual `enable_load_extension` + `load_extension` paths. This handles platform-specific paths automatically [ASSUMED: based on sqlite-vec Python package conventions].
**Warning signs:** `sqlite3.OperationalError: no such module: vec0` even after `pip install sqlite-vec`.

### Pitfall 4: Placeholder Embeddings Silently Returning Garbage
**What goes wrong:** `factory.py` returns `random.random()` embeddings for sentence-transformers and GGUF paths.
**Why it happens:** Heavy dependencies were stubbed during early development.
**How to avoid:** Implement real `SentenceTransformer(model_id).encode(...)` and `llama_cpp.Llama(...)` embedding calls. Gate unimplemented backends behind a clear `NotImplementedError` or `ValueError`.
**Warning signs:** Vector search returns results but semantic similarity is nonsensical.

### Pitfall 5: `vsearch` CLI Always Falling Back to BM25
**What goes wrong:** `vsearch_cmd` unconditionally prints a warning and calls `search_cmd` (BM25), even if embeddings exist.
**Why it happens:** The command was scaffolded before the embedder integration was complete.
**How to avoid:** Load the embedder via `EmbeddingManager`, generate a query embedding, and call `VectorSearcher.search()`. If `sqlite-vec` is unavailable, raise `click.ClickException` with a clear message instead of falling back.

### Pitfall 6: Duplicate Repository Files Causing Schema Drift
**What goes wrong:** `sqlite_repository.py` and `repositories.py` use different schemas and different model imports. Fixes in one do not apply to the other.
**Why it happens:** A refactoring started a new repository layer but the old one was never deleted.
**How to avoid:** Delete `sqlite_repository.py` as soon as `repositories.py` covers all needed operations. Update any remaining imports.

## Code Examples

### FTS5 Trigger Setup in SchemaManager
```python
# Source: SQLite FTS5 documentation + codebase patterns
class SchemaManager:
    ...
    def _create_fts_tables(self) -> None:
        self.db.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                content,
                tokenize='porter',
                content='documents',
                content_rowid='id'
            )
        """)
        self.db.execute("""
            CREATE TRIGGER IF NOT EXISTS documents_fts_insert
            AFTER INSERT ON documents
            BEGIN
                INSERT INTO documents_fts(rowid, content)
                VALUES (NEW.id, NEW.content);
            END
        """)
        self.db.execute("""
            CREATE TRIGGER IF NOT EXISTS documents_fts_update
            AFTER UPDATE ON documents
            BEGIN
                INSERT INTO documents_fts(documents_fts, rowid, content)
                VALUES ('delete', OLD.id, OLD.content);
                INSERT INTO documents_fts(rowid, content)
                VALUES (NEW.id, NEW.content);
            END
        """)
        self.db.execute("""
            CREATE TRIGGER IF NOT EXISTS documents_fts_delete
            AFTER DELETE ON documents
            BEGIN
                INSERT INTO documents_fts(documents_fts, rowid, content)
                VALUES ('delete', OLD.id, OLD.content);
            END
        """)
        # Same pattern for chunks_fts -> document_chunks
```

### Real Sentence-Transformers Factory Implementation
```python
# Source: sentence-transformers docs + codebase model.py protocol
class STModel(EmbeddingModel):
    def __init__(self, name: str, **kwargs):
        super().__init__(
            model_id=name,
            embedding_dim=kwargs.get("embedding_dim", 384),
            max_tokens=kwargs.get("max_tokens", 512),
        )
        self._model: Any | None = None
        self._batch_size = kwargs.get("batch_size", 32)

    def load(self) -> None:
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(self._model_id)
        self._loaded = True

    def embed(self, texts: list[str], normalize: bool = True) -> list[list[float]]:
        if self._model is None:
            raise RuntimeError("Model not loaded")
        embeddings = self._model.encode(
            texts,
            normalize_embeddings=normalize,
            batch_size=self._batch_size,
            show_progress_bar=False,
        )
        return [e.tolist() for e in embeddings]
```

### Connection-Per-Request for Async Contexts
```python
# Source: Python sqlite3 best practices + project decisions
from docsift.database.database import DatabaseConnection

def handle_request(db_path: Path):
    with DatabaseConnection(db_path).connect() as conn:
        repo = DocumentRepository(conn)
        ...
```

### Correct Checksum Logic
```python
# Source: codebase audit + PITFALLS.md
if existing.checksum == checksum and not force:
    logger.debug(f"File unchanged, skipping: {file_path}")
    return IndexStatus.SKIPPED
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Brute-force Python vector fallback | `sqlite-vec` hard requirement | Phase 1 (now) | Eliminates O(N) memory scaling; requires extension install |
| Random embedding stubs | Real `sentence-transformers` / `llama-cpp-python` | Phase 1 (now) | Vector search becomes semantically meaningful |
| FTS5 without triggers | External content tables + triggers | Phase 1 (now) | BM25 stays synchronized automatically |
| `sqlite_repository.py` | Unified `repositories.py` | Phase 1 (now) | Single source of truth for DB access |

**Deprecated/outdated:**
- `sqlite_repository.py`: Old schema, redundant with `repositories.py` — delete it.
- `VectorSearcher._search_fallback()`: Brute-force Python loop — remove it.
- Hardcoded `BAAI/bge-small-zh-v1.5` in `embed_cmd`: Use `Settings.model_name` instead.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `sqlite_vec.load(conn)` is the recommended cross-platform way to load the extension | Standard Stack / Pitfalls | If wrong, manual path probing in `database.py` can be kept, but it is brittle |
| A2 | No production code outside the repo imports `sqlite_repository.py` | Architecture Patterns | If wrong, deleting it will break external consumers; a grep should be run before deletion |

## Open Questions

1. **Migration path for existing databases without triggers**
   - What we know: D-01 says triggers must be created in `SchemaManager`. Existing user databases will lack them.
   - What's unclear: Should `init_schema()` detect missing triggers and add them, or should there be an explicit migration command?
   - Recommendation: Add trigger creation defensively in `SchemaManager.create_all()` using `CREATE TRIGGER IF NOT EXISTS`. Existing databases will get triggers on the next schema init or explicit `docsift cleanup` / re-index.

2. **Exact `sqlite-vec` error message wording**
   - What we know: D-07 leaves wording to discretion.
   - What's unclear: None — implement a concise, actionable message.
   - Recommendation: `click.ClickException("sqlite-vec is required for vector search but could not be loaded. Install it with: pip install sqlite-vec")`

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | ✓ | 3.12.8 | — |
| SQLite | Database + FTS5 | ✓ | 3.47.2 | — |
| pytest | Testing | ✓ | 9.0.2 | — |
| ruff | Linting/formatting | ✓ | 0.15.9 | — |
| mypy | Type checking | ✓ | 1.20.0 | — |
| sqlite-vec | Vector search | ✓ | 0.1.9 | None (hard requirement) |
| sentence-transformers | Embeddings | ✓ | 5.2.3 installed, 5.4.0 latest | Optional extra |

**Missing dependencies with no fallback:**
- None — all core tools are present.

**Missing dependencies with fallback:**
- None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/unit -x` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FND-01 | Package installs without `ModuleNotFoundError` | smoke | `python -m docsift --help` in fresh venv | ❌ Wave 0 |
| FND-02 | Changed documents are updated, unchanged are skipped | unit | `pytest tests/unit/cli/test_index_commands.py -x` | ✅ |
| FND-03 | Factory loads real models and returns non-random embeddings | unit | `pytest tests/unit/inference/test_embedder.py -x` | ✅ |
| FND-04 | CLI `embed` uses Settings model name, not hardcoded path | unit/integration | `pytest tests/unit/cli/test_index_commands.py -x` | ✅ |
| FND-05 | Only one repository file exists; `sqlite_repository.py` deleted | smoke | `test -f src/docsift/database/sqlite_repository.py` (should fail) | ❌ Wave 0 |
| FND-06 | Inserting a document makes it findable via BM25 | integration | `pytest tests/integration/test_index_and_search.py -x` | ✅ |
| FND-07 | `vsearch` without sqlite-vec raises error instead of falling back | unit/e2e | `pytest tests/unit/cli/test_search_commands.py -x` | ✅ |
| FND-08 | Concurrent HTTP requests do not trigger SQLite thread errors | integration | New async stress test | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/unit -x`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] Fresh-venv smoke test for `FND-01` — can be a simple shell assertion in CI or a temporary venv test
- [ ] File-deletion smoke test for `FND-05`
- [ ] Async SQLite stress test for `FND-08`
- [ ] Update `tests/unit/db/test_repositories.py` if schema changes affect fixtures

*(If no gaps: "None — existing test infrastructure covers all phase requirements")*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Not in scope for this phase |
| V3 Session Management | No | Not in scope for this phase |
| V4 Access Control | No | Local single-user tool |
| V5 Input Validation | Yes | Parameterized queries already used; verify no f-string interpolation for user values |
| V6 Cryptography | No | Checksum uses SHA-256 (standard) |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via f-string query building | Tampering | Use `?` placeholders for all values; sanitize FTS5 `MATCH` terms [CITED: PITFALLS.md] |
| SQLite connection sharing across threads | Denial of Service | Connection-per-request in async contexts [CITED: PITFALLS.md] |

## Sources

### Primary (HIGH confidence)
- Codebase audit of `src/docsift/cli/commands/index.py`, `search.py`, `embedding/factory.py`, `database/schema.py`, `database/repositories.py`, `database/sqlite_repository.py`, `database/database.py`, `indexing/indexer.py` [VERIFIED: direct file reads]
- `.planning/research/PITFALLS.md` — known pitfalls for FTS5, SQLite threading, placeholder embeddings [CITED: project research doc]
- `.planning/research/STACK.md` — recommended library versions [CITED: project research doc]
- `pip index versions` output for `sqlite-vec`, `sentence-transformers`, `llama-cpp-python`, `pydantic-settings`, `structlog`, `platformdirs`, `fastapi`, `uvicorn`, `watchdog` [VERIFIED: tool execution]

### Secondary (MEDIUM confidence)
- SQLite FTS5 external content table documentation patterns [ASSUMED: standard SQLite behavior, consistent with PITFALLS.md]
- `sqlite-vec` Python package providing `sqlite_vec.load()` helper [ASSUMED: common pattern for loadable SQLite extensions in Python]

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — versions verified via PyPI index
- Architecture: **HIGH** — codebase audited directly; decisions locked in CONTEXT.md
- Pitfalls: **HIGH** — issues are explicitly documented in PITFALLS.md and confirmed by code review

**Research date:** 2026-04-14
**Valid until:** 2026-05-14 (stable stack, low churn expected)
