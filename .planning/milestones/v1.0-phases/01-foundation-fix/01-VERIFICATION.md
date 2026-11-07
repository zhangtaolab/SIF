---
phase: 01-foundation-fix
verified: 2026-04-15T12:00:00Z
status: passed
score: 12/12 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: null
  previous_score: null
  gaps_closed: []
  gaps_remaining: []
  regressions: []
gaps: []
deferred: []
human_verification: []
---

# Phase 01: Foundation Fix Verification Report

**Phase Goal:** Fix foundational bugs and clean up architecture debt in the indexing, search, embedding, and database layers so later phases build on solid ground.

**Verified:** 2026-04-15T12:00:00Z

**Status:** passed

**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #   | Truth   | Status     | Evidence       |
| --- | ------- | ---------- | -------------- |
| 1   | Project installs cleanly with all runtime dependencies declared | VERIFIED | `pyproject.toml` contains complete dependencies including `sqlite-vec>=0.1.9`, `watchdog>=3.0.0`, `numpy>=1.24.0`. `docsift --help` runs without ModuleNotFoundError. |
| 2   | FTS5 tables stay synchronized with documents and document_chunks automatically | VERIFIED | `schema.py` creates external content FTS5 tables with `content='documents'` and `content='document_chunks'`. All 6 AFTER INSERT/UPDATE/DELETE triggers exist. Live SQLite test confirms inserts, updates, and deletes propagate to both `documents_fts` and `chunks_fts`. |
| 3   | Stale sqlite_repository.py is removed | VERIFIED | File `src/docsift/database/sqlite_repository.py` does not exist. `database/__init__.py` exports concrete repositories from `repositories.py` (plural). |
| 4   | BM25Searcher joins on rowid, not TEXT id | VERIFIED | `src/docsift/search/bm25.py` lines 47 and 106 contain `JOIN documents d ON fts.rowid = d.rowid` and `JOIN document_chunks dc ON fts.rowid = dc.rowid`. Live BM25 search test returns correct results. |
| 5   | Index update skips unchanged documents and updates changed ones | VERIFIED | `src/docsift/cli/commands/index.py` line 108 contains `if existing.checksum == parsed.checksum and not force:`. |
| 6   | embed_cmd uses Settings.model_name instead of hardcoded path | VERIFIED | `src/docsift/cli/commands/index.py` line 187 contains `model_name = model or settings.model_name` with local import of `get_settings()`. |
| 7   | embed_cmd accepts --model CLI override | VERIFIED | `src/docsift/cli/commands/index.py` line 157 contains `@click.option("--model", "-m", help="Embedding model name")`. No hardcoded `BAAI/bge-small-zh-v1.5` remains in `src/`. |
| 8   | Embedding factory uses real SentenceTransformerEmbedder and LlamaCppEmbedder | VERIFIED | `src/docsift/embedding/factory.py` imports and instantiates `SentenceTransformerEmbedder` and `LlamaCppEmbedder` from `docsift.embedding.embedder`. No `random.random()` placeholders remain. Factory smoke test confirms `ValueError` for missing GGUF `model_path`. |
| 9   | ModelType is unified across modules | VERIFIED | `src/docsift/embedding/model.py` imports `ModelType` from `docsift.models.embedding`. The canonical `ModelType` enum in `models/embedding.py` defines `GGUF`, `SENTENCE_TRANSFORMERS`, `OPENAI`, `HUGGINGFACE`. |
| 10  | VectorSearcher raises RuntimeError without sqlite-vec and has no fallback | VERIFIED | `src/docsift/search/vector.py` line 19 raises `RuntimeError` when `sqlite-vec` is unavailable. Fallback methods `_search_fallback`, `_cosine_similarity`, `_add_embedding_fallback`, `_blob_to_embedding` are all removed. `search()` directly returns `self._search_with_vec()`. Spot-check confirms RuntimeError is raised in `:memory:` SQLite. |
| 11  | HybridSearcher doesn't suppress vector errors | VERIFIED | `src/docsift/search/hybrid.py` line 52 contains direct `query_embedding = self.embedder.embed(query)` and `vector_results = self.vector.search(...)` with no `try/except` around vector search. The string "Warning: Vector search failed" is not present. (Remaining `except Exception` blocks are for reranking and query expansion, not vector search.) |
| 12  | vsearch_cmd fails fast with click.ClickException | VERIFIED | `src/docsift/cli/commands/search.py` lines 200 and 202 raise `click.ClickException` for embedder loading failures. No "Falling back to BM25 search" text remains. `vsearch_cmd` performs real vector search with `VectorSearcher`. |
| 13  | MCP server uses connection-per-request | VERIFIED | `src/docsift/mcp/server.py` imports `DatabaseConnection` and contains 5 occurrences of `DatabaseConnection(self.index_path).transaction()`. No `self.db`, no `initialize()` method, no `server.initialize()` calls in `server.py` or `server_http.py`. Live import tests pass for both modules. |

**Score:** 13/13 truths verified

### Required Artifacts

| Artifact | Expected    | Status | Details |
| -------- | ----------- | ------ | ------- |
| `pyproject.toml` | Complete dependency declarations | VERIFIED | Contains all runtime deps; no structlog. gsd-tools artifact check passed. |
| `src/docsift/database/schema.py` | FTS5 external content tables with triggers | VERIFIED | gsd-tools artifact check passed. Contains `content='documents'`, `content='document_chunks'`, all 6 triggers, and `_fts_is_misconfigured` helper. |
| `src/docsift/database/repositories.py` | Clean repository without manual FTS sync | VERIFIED | gsd-tools artifact check passed. No `INSERT INTO chunks_fts` or `DELETE FROM chunks_fts` remains. |
| `src/docsift/search/bm25.py` | Correct FTS5 rowid joins | VERIFIED | gsd-tools artifact check passed. Joins on `fts.rowid = d.rowid` and `fts.rowid = dc.rowid`. |
| `src/docsift/database/__init__.py` | Exports concrete repositories | VERIFIED | gsd-tools artifact check passed. Imports from `docsift.database.repositories`. |
| `src/docsift/cli/commands/index.py` | Correct checksum logic and configurable model | VERIFIED | gsd-tools artifact check passed. Checksum fix and `--model` override present. |
| `src/docsift/embedding/embedder.py` | Default model aligned with Settings | VERIFIED | gsd-tools artifact check passed. Default is `all-MiniLM-L6-v2`. |
| `src/docsift/embedding/factory.py` | Real embedder instantiation | VERIFIED | gsd-tools artifact check passed. Delegates to real embedders, no placeholders. |
| `src/docsift/embedding/model.py` | Unified ModelType import | VERIFIED | gsd-tools artifact check passed. Imports `ModelType` from canonical location. |
| `src/docsift/search/vector.py` | Hard sqlite-vec requirement | VERIFIED | gsd-tools artifact check passed. Raises `RuntimeError`, fallbacks removed. |
| `src/docsift/search/hybrid.py` | No vector error suppression | VERIFIED | gsd-tools artifact check passed. Vector search block has no `try/except`. |
| `src/docsift/cli/commands/search.py` | Fail-fast vsearch command | VERIFIED | gsd-tools artifact check passed. Uses `click.ClickException`, no BM25 fallback. |
| `src/docsift/mcp/server.py` | Connection-per-request MCP handlers | VERIFIED | gsd-tools artifact check passed. Uses `DatabaseConnection`, no `self.db`. |
| `src/docsift/mcp/server_http.py` | Stateless HTTP server | VERIFIED | gsd-tools artifact check passed. No `server.initialize()` call. |

### Key Link Verification

| From | To  | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `pyproject.toml` | `pip install` | dependencies array | VERIFIED | `docsift --help` executes successfully; editable install works. |
| `documents` table | `documents_fts` | AFTER INSERT/UPDATE/DELETE triggers | VERIFIED | Live SQLite test confirms trigger synchronization. |
| `document_chunks` table | `chunks_fts` | AFTER INSERT/UPDATE/DELETE triggers | VERIFIED | Live SQLite test confirms trigger synchronization. |
| `update_cmd` | `Document.checksum` | `==` comparison for unchanged skip | VERIFIED | Line 108 in `index.py`. |
| `embed_cmd` | `Settings.model_name` | `get_settings().model_name` | VERIFIED | Line 187 in `index.py`. |
| `EmbeddingModelFactory.create_model` | `SentenceTransformerEmbedder` | `ModelType.SENTENCE_TRANSFORMERS` branch | VERIFIED | Factory instantiates real embedder class. |
| `EmbeddingModelFactory.create_model` | `LlamaCppEmbedder` | `ModelType.GGUF` branch | VERIFIED | Factory instantiates real embedder class with `model_path` validation. |
| `VectorSearcher.__init__` | sqlite-vec availability | `RuntimeError` on missing extension | VERIFIED | Spot-check raises RuntimeError in `:memory:` SQLite without extension. |
| `HybridSearcher.search` | `VectorSearcher.search` | direct call without `try/except` | VERIFIED | Lines 52-53 in `hybrid.py`. |
| `MCPServer._tool_query` | `sqlite3.Connection` | `DatabaseConnection.transaction()` context manager | VERIFIED | 5 handlers use `DatabaseConnection(self.index_path).transaction() as conn`. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `BM25Searcher.search` | `cursor.fetchall()` | `documents_fts` JOIN + MATCH query | Yes — live test returns document | FLOWING |
| `VectorSearcher.__init__` | `self._vec_available` | `SELECT vec_version()` | Yes — raises RuntimeError when absent | FLOWING |
| `embed_cmd` | `model_name` | CLI `--model` or `get_settings().model_name` | Yes — resolves to `all-MiniLM-L6-v2` | FLOWING |
| `vsearch_cmd` | `embedder` | `SentenceTransformerEmbedder(settings.model_name)` | Yes — instantiates real embedder | FLOWING |
| `MCP handlers` | `conn` | `DatabaseConnection(self.index_path).transaction()` | Yes — fresh SQLite connection per request | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| CLI launches without import errors | `docsift --help` | Usage banner printed, exit 0 | PASS |
| FTS5 triggers synchronize inserts | Live SQLite test | `documents_fts` contains row after insert | PASS |
| FTS5 triggers synchronize updates | Live SQLite test | `documents_fts` content updated after base table update | PASS |
| FTS5 triggers synchronize deletes | Live SQLite test | `documents_fts` row removed after base table delete | PASS |
| BM25 search returns results with rowid join | Live SQLite test | Returns correct document | PASS |
| VectorSearcher fails fast without sqlite-vec | `VectorSearcher(:memory:, 384)` | Raises `RuntimeError` as expected | PASS |
| Factory validates missing GGUF model_path | `f.create_model(ModelType.GGUF, None, 'test')` | Raises `ValueError` as expected | PASS |
| MCP modules import cleanly | `from docsift.mcp.server import MCPServer` | Import succeeds | PASS |
| Core test suite passes | `pytest tests/test_docsift_complete.py -x` | 9 passed | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| FND-01 | 01-01 | Fix missing runtime dependencies in pyproject.toml | SATISFIED | `pyproject.toml` contains all required runtime dependencies; `docsift --help` works. |
| FND-02 | 01-03 | Fix inverted checksum comparison in index update | SATISFIED | `index.py` uses `existing.checksum == parsed.checksum`. |
| FND-03 | 01-04 | Replace placeholder embedding factory with real loaders | SATISFIED | `factory.py` delegates to `SentenceTransformerEmbedder` and `LlamaCppEmbedder`. |
| FND-04 | 01-03 | Remove hardcoded model path, use Settings with CLI override | SATISFIED | `embed_cmd` uses `model or settings.model_name`; no `BAAI/bge-small-zh-v1.5` remains. |
| FND-05 | 01-02 | Unify/clean up repository implementations | SATISFIED | `sqlite_repository.py` deleted; `database/__init__.py` exports from `repositories.py`. |
| FND-06 | 01-02 | Fix FTS5 external content synchronization and BM25 rowid joins | SATISFIED | External content FTS5 tables with triggers created; BM25 joins on `rowid`. |
| FND-07 | 01-05 | Remove vector search fallback, fail fast in vsearch CLI | SATISFIED | `vector.py` raises `RuntimeError`; `hybrid.py` does not suppress vector errors; `vsearch_cmd` fails fast with `click.ClickException`. |
| FND-08 | 01-06 | Improve SQLite connection management for async/thread safety | SATISFIED | MCP server uses `DatabaseConnection(self.index_path).transaction()` per request; no cached `Database` instance. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| None | — | — | — | No TODO/FIXME/placeholder patterns found in phase-modified files. |

**Notes:**
- `src/docsift/search/hybrid.py` still contains `except Exception as e:` blocks at lines 119 and 180, but these are for **reranking** and **query expansion** failures, not vector search. The vector search suppression was correctly removed.
- `src/docsift/embedding/factory.py` intentionally raises `NotImplementedError` for `OPENAI` and `HUGGINGFACE` branches per plan specification. These are not stubs — they are explicit unimplemented boundaries.

### Human Verification Required

None. All behaviors are verifiable programmatically.

### Gaps Summary

No gaps found. All 13 observable truths are verified, all 14 required artifacts pass existence/substance/wiring checks, all 10 key links are confirmed, and all 8 requirement IDs (FND-01 through FND-08) are satisfied.

---

_Verified: 2026-04-15T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
