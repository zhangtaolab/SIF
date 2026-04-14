# Phase 01: Foundation Fix - Research

**Researched:** 2026-04-14
**Domain:** Python CLI/SQLite local search engine - dependency management, FTS5 synchronization, embedding factories, SQLite threading
**Confidence:** HIGH

## Summary

Phase 01 addresses critical bugs, missing runtime dependencies, stub implementations, and SQLite safety issues in DocSift's foundation. The codebase has two parallel schema definition systems (SchemaManager vs MigrationManager), an inverted checksum condition that skips changed documents, placeholder embedding factories that return random vectors, hardcoded model paths bypassing Settings, and unsafe SQLite connection sharing in the MCP server. All eight requirements (FND-01 through FND-08) are well-understood and have clear implementation paths.

**Primary recommendation:** Fix `pyproject.toml` dependencies first (unblocks tests), then consolidate schema/triggers in `SchemaManager`, replace factory stubs with real `sentence-transformers`/`llama-cpp-python` loaders wired to `Settings`, remove the Python vector-search fallback, and switch the MCP server to connection-per-request.

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

- None — discussion stayed within phase scope.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FND-01 | Fix missing runtime deps in `pyproject.toml` | Verified missing packages by AST import audit; structlog is **not** actually imported and should be excluded |
| FND-02 | Fix checksum comparison bug (skip unchanged, update changed) | Bug found in `cli/commands/index.py` line ~108 (`!=` instead of `==`); `indexer.py` appears correct |
| FND-03 | Replace stub/random embeddings with real `sentence-transformers` and `llama-cpp-python` loaders | Real implementations exist in `embedding/embedder.py`; factory should delegate to them after unifying `ModelType` |
| FND-04 | Remove hardcoded model path `BAAI/bge-small-zh-v1.5`, read from Settings, allow CLI override | Hardcoded in `cli/commands/index.py` and `embedding/embedder.py`; Settings already has `model_name` |
| FND-05 | Consolidate duplicate repository implementations (`repositories.py` vs `sqlite_repository.py`) | `sqlite_repository.py` is completely unused; `repositories.py` is the canonical concrete layer |
| FND-06 | Fix FTS5 external content synchronization | Verified FTS5 triggers work with integer `rowid`; `BM25Searcher` join is wrong (`d.id` -> `d.rowid`); `chunks_fts` also needs triggers |
| FND-07 | Fix vector search CLI fallback: `vsearch` must not silently fall back to BM25 | `VectorSearcher` has `_search_fallback` to remove; `vsearch_cmd` unconditionally falls back; `HybridSearcher` catches and ignores vector errors |
| FND-08 | Improve SQLite connection safety across async/multi-threaded ops | Verified `check_same_thread=False` still races; `DatabaseConnection.connect()` per-request is safe; MCP server reuses cached `Database` |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12 (dev env) / 3.9+ (target) | Runtime | Project already targets 3.9+ syntax |
| `click` | >=8.0.0 | CLI framework | Already integrated; stable |
| `rich` | >=13.0.0 | Terminal output | Already integrated |
| `pydantic` | >=2.0.0 | Config validation | `Settings` already uses Pydantic v2 |
| `pydantic-settings` | >=2.0.0 | Env-var loading | Already used in `config/settings.py` |
| `sqlite-vec` | >=0.1.9 | Vector search in SQLite | Verified installable; requires `conn.enable_load_extension(True)` before `sqlite_vec.load(conn)` |
| `numpy` | >=1.24.0 | Vector math | Required by embedding code directly and transitively |
| `platformdirs` | >=3.0.0 | Cross-platform paths | Already used for default DB/cache dirs |
| `fastapi` | >=0.100.0 | MCP HTTP transport | Already used in `mcp/server_http.py` |
| `uvicorn` | >=0.20.0 | ASGI server | Already used in `mcp/server_http.py` |
| `watchdog` | >=3.0.0 | File watching | Imported in `indexing/watcher.py` |
| `python-frontmatter` | >=1.0.0 | Markdown YAML parsing | Already declared; provides `frontmatter` module |

### Optional / Heavy

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `sentence-transformers` | >=2.2.0 | Default embedding backend | User installs `[embed]` extra |
| `llama-cpp-python` | >=0.3.20 | GGUF local embeddings | User installs `[llm]` extra |
| `modelscope` | >=1.0.0 | China HF mirror downloads | User installs `[modelscope]` extra |

**Installation:**
```bash
pip install -e ".[dev]"
```

**Version verification performed:**
- `sqlite-vec` 0.1.9 installed and verified KNN search works [VERIFIED: local install]
- `sentence-transformers` 5.2.3 available in environment [VERIFIED: local import]
- `pydantic` 2.12.5 available [VERIFIED: local import]
- `fastapi` 0.131.0, `uvicorn` 0.41.0 available [VERIFIED: local import]
- `numpy` 2.4.4 available [VERIFIED: local import]

## Architecture Patterns

### System Architecture Diagram

```
User CLI / MCP HTTP Request
        |
        v
+-------------------+     +-------------------+
|  CLI Commands     |     |  MCP Server       |
|  (index, search)  |     |  (per-request conn)|
+---------+---------+     +---------+---------+
          |                         |
          v                         v
+---------+-------------------------+---------+
|           Database Layer                    |
|  Database (CLI, cached conn)                |
|  DatabaseConnection (async/thread-safe)     |
+---------+-----------------------------------+
          |
          v
+---------+-------------------------+---------+
|           SchemaManager                     |
|  - tables, indexes, FTS5 triggers           |
|  - vec0 virtual tables (configurable dim)   |
+---------+-----------------------------------+
          |
          +----------------+----------------+
          |                                 |
          v                                 v
+-------------------+             +-------------------+
|  BM25Searcher     |             |  VectorSearcher   |
|  (FTS5 + triggers)|             |  (sqlite-vec KNN) |
+---------+---------+             +---------+---------+
          |                                 |
          +----------------+----------------+
                             |
                             v
                    +-------------------+
                    |  HybridSearcher   |
                    |  (BM25 + Vector   |
                    |   + RRF fusion)   |
                    +-------------------+
```

### Recommended Project Structure

No reorganization needed. The existing structure is sound:

```
src/docsift/
├── cli/commands/       # Click command implementations
├── database/           # SchemaManager, repositories, connection managers
├── embedding/          # Factory, embedder implementations, manager
├── indexing/           # Parser, chunker, indexer
├── search/             # BM25, vector, hybrid, RRF
└── config/             # Pydantic Settings
```

### Pattern 1: Connection-Per-Request for Async Contexts

**What:** Each async request or thread gets its own `sqlite3.Connection` via `DatabaseConnection.connect()`.
**When to use:** MCP HTTP server, any threaded background workers.
**Example:**
```python
# Source: docsift/database/connection.py (verified behavior)
from docsift.database.connection import DatabaseConnection

def handle_request(db_path: str) -> None:
    conn = DatabaseConnection(db_path)
    with conn.connect() as db:
        db.execute("SELECT ...")
```

### Pattern 2: Factory Delegation to Real Implementations

**What:** `EmbeddingModelFactory` should instantiate the real embedder classes in `embedding/embedder.py` instead of inline stub classes.
**When to use:** FND-03 implementation.
**Example:**
```python
# Source: verified from codebase
from docsift.embedding.embedder import SentenceTransformerEmbedder, LlamaCppEmbedder

if model_type == ModelType.SENTENCE_TRANSFORMERS:
    return SentenceTransformerEmbedder(model_name=model_name, ...)
elif model_type == ModelType.GGUF:
    return LlamaCppEmbedder(model_path=model_path, ...)
```

### Anti-Patterns to Avoid

- **Caching `sqlite3.Connection` across async tasks:** `Database.connection` property caches one connection with `check_same_thread=False`. Verified under threaded load it produces `bad parameter or other API misuse` errors.
- **FTS5 `rowid` = TEXT column:** `documents_fts` and `chunks_fts` must use the auto-generated integer `rowid`, not `id`.
- **Random embeddings in production:** The current factory returns `random.random()` vectors. This must be removed entirely.
- **Two schema systems:** `SchemaManager` and `MigrationManager` define different schemas. Consolidate on `SchemaManager` per D-03.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Vector similarity search | Brute-force Python cosine loop over all rows | `sqlite-vec` KNN inside SQLite | O(N) memory/CPU scaling; sqlite-vec is tested and supports `MATCH` + `ORDER BY distance` |
| FTS5 synchronization | Application-level manual INSERT/UPDATE/DELETE mirroring | SQLite `AFTER INSERT/UPDATE/DELETE` triggers | Triggers are atomic with the parent transaction and cannot be forgotten |
| Embedding model loading | Custom download/cache logic for HF models | `sentence_transformers.SentenceTransformer` | Handles caching, device selection, batching, normalization automatically |
| GGUF embedding | Raw `llama.cpp` C bindings | `llama-cpp-python` | Canonical Python binding; provides `Llama.embed()` with numpy output |
| SQLite connection pooling for reads | Complex custom pool | `DatabaseConnection.connect()` context manager + one write connection | SQLite write serialization makes fancy pools unnecessary; simple per-request connections are sufficient |

**Key insight:** The existing codebase already contains correct implementations for `SentenceTransformerEmbedder` and `LlamaCppEmbedder` in `embedding/embedder.py`. The factory's job is to route to them, not reimplement them.

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | Existing SQLite DBs may lack FTS5 triggers and have `documents_fts` without `content=` / `content_rowid=` | Schema migration: drop/recreate FTS5 virtual tables, add triggers, rebuild index |
| Live service config | None — MCP server is not running | None |
| OS-registered state | None | None |
| Secrets/env vars | None affected | None |
| Build artifacts | `sqlite_repository.py` stale module; `__pycache__` will regenerate | Delete `sqlite_repository.py` |

**Nothing found in category:** Live service config, OS-registered state, Secrets/env vars.

## Common Pitfalls

### Pitfall 1: Inverted Checksum Condition Skips Changed Documents
**What goes wrong:** `cli/commands/index.py` uses `if existing.checksum != parsed.checksum and not force: skip`. This skips files that changed unless `--force` is passed.
**Why it happens:** The boolean logic was inverted during development.
**How to avoid:** Change to `if existing.checksum == parsed.checksum and not force: skip`.
**Warning signs:** `update` command reports "Unchanged" for files that were just edited.

### Pitfall 2: TEXT `id` Used as FTS5 `rowid`
**What goes wrong:** `chunks_fts` inserts use `chunk.id` (TEXT) as `rowid`, causing `sqlite3.IntegrityError: datatype mismatch`. `BM25Searcher` joins `fts.rowid = d.id` instead of `fts.rowid = d.rowid`.
**Why it happens:** SQLite auto-generates an integer `rowid` even when the primary key is TEXT, but the code assumed `rowid == id`.
**How to avoid:** Always use `rowid` for FTS5 external content tables and triggers. Join on `fts.rowid = documents.rowid`.
**Warning signs:** FTS5 searches return empty results or raise `datatype mismatch`.

### Pitfall 3: `sqlite-vec` Import at Top Level Breaks All Imports
**What goes wrong:** `database/connection.py` imports `sqlite_vec` unconditionally. `database/__init__.py` re-exports `DatabaseConnection`, so any import from `docsift.database` fails when `sqlite-vec` is not installed.
**Why it happens:** Heavy dependency was treated as optional but wired into the package init path.
**How to avoid:** Add `sqlite-vec` to `[project.dependencies]` so it is always present, or make the import lazy inside `_create_connection()`.
**Warning signs:** `pip install -e .` followed by `python -m docsift --help` raises `ModuleNotFoundError`.

### Pitfall 4: Vector Search Python Fallback Collapses at Scale
**What goes wrong:** `VectorSearcher._search_fallback()` `SELECT`s every embedding, deserializes all vectors into Python lists, and computes cosine similarity in a loop.
**Why it happens:** Developer wanted the system to work without `sqlite-vec`.
**How to avoid:** Remove the fallback entirely. If `sqlite-vec` is unavailable, raise `RuntimeError` with a clear message.
**Warning signs:** `vsearch` latency grows linearly with document count; RSS spikes proportionally.

### Pitfall 5: MCP Server Shares Cached SQLite Connection Across Async Requests
**What goes wrong:** `mcp/server.py` creates one `Database(index_path)` at startup and holds it. `mcp/server_http.py` creates one `MCPServer` and reuses it for all FastAPI requests.
**Why it happens:** `Database` was designed for single-threaded CLI usage.
**How to avoid:** Refactor MCP tool handlers to create a new `DatabaseConnection.connect()` inside each handler, or pass a connection factory.
**Warning signs:** Intermittent `sqlite3.ProgrammingError` under concurrent HTTP load.

## Code Examples

### FTS5 External Content Table with Triggers

```sql
-- Source: verified with SQLite 3.47.2 local test
CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
    content,
    content='documents',
    content_rowid='rowid',
    tokenize='porter'
);

CREATE TRIGGER IF NOT EXISTS documents_fts_insert
AFTER INSERT ON documents
BEGIN
    INSERT INTO documents_fts(rowid, content) VALUES (new.rowid, new.content);
END;

CREATE TRIGGER IF NOT EXISTS documents_fts_update
AFTER UPDATE ON documents
BEGIN
    UPDATE documents_fts SET content = new.content WHERE rowid = old.rowid;
END;

CREATE TRIGGER IF NOT EXISTS documents_fts_delete
AFTER DELETE ON documents
BEGIN
    DELETE FROM documents_fts WHERE rowid = old.rowid;
END;
```

### sqlite-vec Insert and KNN Query

```python
# Source: verified local test with sqlite-vec 0.1.9
import sqlite3
import sqlite_vec

conn = sqlite3.connect(path)
conn.enable_load_extension(True)
sqlite_vec.load(conn)
conn.enable_load_extension(False)

conn.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS embeddings USING vec0(
        embedding_id TEXT PRIMARY KEY,
        document_id TEXT NOT NULL,
        chunk_id TEXT,
        embedding FLOAT[384]
    )
""")

conn.execute(
    "INSERT INTO embeddings(embedding_id, document_id, chunk_id, embedding) VALUES (?, ?, ?, vec_f32(?))",
    ("e1", "d1", "c1", "[0.1, 0.2, 0.3, 0.4]")
)

rows = conn.execute(
    "SELECT embedding_id, distance FROM embeddings WHERE embedding MATCH ? ORDER BY distance LIMIT ?",
    ("[0.1, 0.2, 0.3, 0.4]", 5)
).fetchall()
```

### Sentence-Transformers Encode with Explicit Batch Size

```python
# Source: sentence-transformers source inspection (5.2.3)
from sentence_transformers import SentenceTransformer

model = SentenceTransformer(model_name)
embeddings = model.encode(
    texts,
    batch_size=16,
    normalize_embeddings=True,
    show_progress_bar=False,
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Brute-force Python vector search | `sqlite-vec` hard requirement | Phase 1 (now) | Eliminates O(N) memory scaling; requires extension install |
| Random embedding stubs | Real `sentence-transformers` / `llama-cpp-python` | Phase 1 (now) | Vector search becomes semantically meaningful |
| FTS5 standalone tables | External content tables + triggers | Phase 1 (now) | BM25 stays synchronized automatically |
| `sqlite_repository.py` | Unified `repositories.py` | Phase 1 (now) | Single source of truth for DB access |

**Deprecated/outdated:**
- `sqlite_repository.py`: Completely unused; schema is stale and incompatible with current `SchemaManager`. Delete per D-02.
- `VectorSearcher._search_fallback()`: Loads all embeddings into memory. Remove per D-06/D-07.
- Hardcoded `BAAI/bge-small-zh-v1.5` in `embed_cmd`: Use `Settings.model_name` instead.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `structlog` is not imported anywhere in `src/docsift/` and should not be added to `pyproject.toml` | Standard Stack / FND-01 | If the user intended structlog to be added, it would be an unused dependency; low risk |
| A2 | `llama-cpp-python` batch embedding regression (post-v0.3.14) means we should process one text at a time for GGUF | Don't Hand-Roll | If fixed in newer versions, single-text loop is slightly slower but still correct; low risk |
| A3 | Existing databases with `documents_fts` created without `content=` can be safely dropped and recreated because no other tables reference the FTS5 virtual table | Runtime State Inventory | FTS5 data will be lost but can be rebuilt from triggers + reindex; acceptable for local-first tool |

## Open Questions

1. **Migration path for existing DBs with wrong `documents_fts` configuration**
   - What we know: `DROP TABLE documents_fts` is safe; triggers will repopulate on subsequent document operations, but existing documents won't be indexed until reindexed.
   - What's unclear: Should the plan include an explicit `REINDEX` or full reindex command?
   - Recommendation: Add a one-time migration step in `SchemaManager` that drops/recreates FTS5 tables and runs `INSERT INTO documents_fts(rowid, content) SELECT rowid, content FROM documents` for seeding.

2. **`ModelType` unification strategy**
   - What we know: `embedding/model.py` uses `Enum(auto())`; `models/embedding.py` uses `str, Enum`.
   - What's unclear: Which one should be the canonical type?
   - Recommendation: Use the `str, Enum` from `models/embedding.py` because it serializes cleanly to JSON/Pydantic, and update `embedding/model.py` and `embedding/factory.py` to match.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | ✓ | 3.12.8 | — |
| SQLite | FTS5 + sqlite-vec | ✓ | 3.47.2 | — |
| pytest | Tests | ✓ | 9.0.2 | — |
| ruff | Lint/format | ✓ | 0.15.9 | — |
| mypy | Type check | ✓ | 1.20.0 | — |
| sentence-transformers | FND-03 real embeddings | ✓ | 5.2.3 | — |
| sqlite-vec | FND-06/FND-07 vector search | ✗ (not in venv deps) | — | Must add to `pyproject.toml` and install |
| llama-cpp-python | FND-03 GGUF path | ✗ | — | Optional extra; plan can skip runtime verification |
| pydantic | Settings | ✓ | 2.12.5 | — |
| pydantic-settings | Settings | ✓ | (bundled) | — |
| fastapi | MCP HTTP | ✓ | 0.131.0 | — |
| uvicorn | MCP HTTP | ✓ | 0.41.0 | — |
| platformdirs | Default paths | ✓ | 4.9.4 | — |
| watchdog | File watcher | ✗ | — | Must add to `pyproject.toml` and install |
| python-frontmatter | Parser | ✗ | — | Already declared; install issue is local env only |

**Missing dependencies with no fallback:**
- `sqlite-vec` — blocks all imports from `docsift.database` because `connection.py` imports it at top level
- `watchdog` — imported by `indexing/watcher.py`

**Missing dependencies with fallback:**
- `llama-cpp-python` — optional extra per D-09; GGUF path can raise clear error if not installed

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/unit/test_X.py -x` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FND-01 | `pip install -e .` succeeds and `docsift --help` runs | smoke | `python -m docsift --help` | ❌ Wave 0 |
| FND-02 | Changed documents are updated, unchanged are skipped | unit | `pytest tests/unit/cli/test_index_commands.py -x` | ⚠️ exists but tests old API |
| FND-03 | Factory returns real embeddings (not random) | unit | `pytest tests/unit/inference/test_embedder.py -x` | ⚠️ tests abstract interface only |
| FND-04 | CLI `--model` overrides Settings model name | unit | `pytest tests/unit/cli/test_index_commands.py -x` | ❌ no such test exists |
| FND-05 | `sqlite_repository.py` deleted, imports still work | smoke | `python -c "import docsift.database.repositories"` | ❌ Wave 0 |
| FND-06 | BM25 returns results for newly inserted documents | integration | `pytest tests/integration/test_index_and_search.py -x` | ✅ exists |
| FND-07 | `vsearch` raises error when embedder unavailable | unit | `pytest tests/unit/cli/test_search_commands.py -x` | ❌ no such test exists |
| FND-08 | Concurrent MCP requests do not crash | integration | custom threaded test | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/unit/test_relevant.py -x`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/unit/cli/test_index_commands.py` — needs update for current `DocumentIndexer` API
- [ ] `tests/unit/cli/test_search_commands.py` — needs tests for `vsearch` fail-fast behavior
- [ ] `tests/unit/search/test_vector.py` — imports `VectorSearchStrategy` (does not exist; should be `VectorSearcher`)
- [ ] `tests/conftest.py` — blocked by `sqlite_vec` import until FND-01 fixes dependencies
- [ ] `tests/unit/db/test_database.py` — verify if it covers `DatabaseConnection` per-request safety

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | Sanitize FTS5 `MATCH` terms; use parameterized queries (`?` placeholders) for all SQL values |
| V6 Cryptography | no | — |

### Known Threat Patterns for Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via f-string query building | Tampering | Use `?` placeholders for values; validate identifiers against whitelist if dynamically interpolated |
| FTS5 `MATCH` term injection | Tampering | Escape/sanitize user query terms before passing to SQLite FTS5; reject unmatched quotes |

## Sources

### Primary (HIGH confidence)
- Codebase audit of `src/docsift/` — direct file reads of schema, search, embedding, CLI, and database modules
- Local verification — SQLite 3.47.2 FTS5 trigger behavior, `sqlite-vec` 0.1.9 KNN queries, threaded SQLite connection safety
- `sentence-transformers` 5.2.3 source inspection — `encode()` signature and batch size parameter

### Secondary (MEDIUM confidence)
- `.planning/research/PITFALLS.md` — documented pitfalls for placeholder embeddings, FTS5 desync, and SQLite threading
- `.planning/research/STACK.md` — recommended library versions including `sqlite-vec>=0.1.9`

### Tertiary (LOW confidence)
- `llama-cpp-python` batch embedding regression notes from PITFALLS.md — not verified locally because package is not installed

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified via local imports and installs
- Architecture: HIGH — direct codebase audit and SQLite behavior tests
- Pitfalls: HIGH — reproduced threading errors and FTS5 datatype mismatch locally

**Research date:** 2026-04-14
**Valid until:** 2026-05-14 (stable stack)
