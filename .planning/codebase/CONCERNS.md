# Codebase Concerns

**Analysis Date:** 2026-04-14

## Tech Debt

### Missing Dependency Declarations
- Issue: `pyproject.toml` omits several runtime dependencies that are imported throughout the codebase.
- Files: `pyproject.toml`
- Missing packages:
  - `sqlite-vec` — used in `src/docsift/database/database.py` and `src/docsift/database/schema.py`
  - `structlog` — used in `src/docsift/utils/logging.py` and search modules
  - `platformdirs` — used in `src/docsift/config/settings.py`
  - `pydantic` and `pydantic-settings` — used in `src/docsift/config/settings.py` and `src/docsift/mcp/protocol.py`
  - `fastapi` and `uvicorn` — used in `src/docsift/mcp/transport_http.py`
  - `watchdog` and `python-frontmatter` — installed during testing but not declared
- Impact: Package fails to run after a clean `pip install`. Users must manually discover and install missing packages.
- Fix approach: Add all runtime dependencies to `pyproject.toml` under `dependencies` or appropriate extras groups.

### Incomplete Embedding Model Implementations
- Issue: `EmbeddingModelFactory` raises `NotImplementedError` for OpenAI and HuggingFace model types, and the GGUF and SentenceTransformers implementations return random embeddings as placeholders.
- Files: `src/docsift/embedding/factory.py`
- Impact: Vector search and embedding generation do not work with real models except the hard-coded `BAAI/bge-small-zh-v1.5` path in `src/docsift/cli/commands/index.py`.
- Fix approach: Implement actual model loading using `llama-cpp-python` for GGUF and `sentence-transformers` for ST models; remove or defer unsupported types.

### Placeholder / Stub Implementations in MCP Tools
- Issue: `mcp_server/tools.py` contains placeholder tool handlers (`SearchTool`, `IndexTool`, `CollectionTool`) that return mock strings instead of calling real services.
- Files: `src/docsift/mcp_server/tools.py`
- Impact: The alternative MCP server (`mcp_server/`) is non-functional for real workloads.
- Fix approach: Wire these tools to the actual `SearchService`, `DocumentIndexer`, and collection managers, or remove the unused `mcp_server/` package to avoid confusion.

### FTS5 External Content Table Not Fully Wired
- Issue: `SchemaManager._create_fts_tables()` creates standalone FTS5 virtual tables (`documents_fts`, `chunks_fts`) without `content=` or `content_rowid=` linking them to the main tables. Synchronizing inserts/updates/deletes between `documents`/`document_chunks` and the FTS tables is missing.
- Files: `src/docsift/database/schema.py`, `src/docsift/database/repositories.py`
- Impact: BM25 search in `src/docsift/search/bm25.py` joins on `fts.rowid = d.id`, but if the FTS table is not populated or gets out of sync, search returns stale or empty results.
- Fix approach: Use FTS5 external content tables with triggers, or explicitly insert/delete FTS rows in repository methods alongside main table operations.

### SQLite Repository Duplication and Divergence
- Issue: There are two parallel repository implementations: `src/docsift/database/repositories.py` (used by CLI/MCP) and `src/docsift/database/sqlite_repository.py` (used by some tests/integration). They have different schemas, different model imports (`docsift.core.models` vs `docsift.core.collection/document/context`), and different behavior.
- Files: `src/docsift/database/repositories.py`, `src/docsift/database/sqlite_repository.py`
- Impact: Maintenance burden, risk of schema drift, and confusion about which repository to use.
- Fix approach: Consolidate into a single repository layer backed by `SchemaManager`; delete the duplicate.

## Known Bugs

### Vector Search CLI Falls Back to BM25 Without Embeddings
- Issue: `vsearch_cmd` in `src/docsift/cli/commands/search.py` always prints a warning and falls back to BM25, even if embeddings exist.
- Files: `src/docsift/cli/commands/search.py` (lines 183–200)
- Trigger: Running `docsift vsearch <query>`.
- Workaround: Use `docsift query` (hybrid) after running `docsift embed`.
- Fix approach: Implement real vector query embedding in the CLI command (reuse the embedder logic from `embed_cmd`).

### MCP Server `vec_search` Tool Falls Back to `lex_search`
- Issue: `MCPServer._tool_vec_search()` delegates directly to `_tool_lex_search()`.
- Files: `src/docsift/mcp/server.py` (line 257)
- Impact: Clients requesting vector search receive BM25 results silently.
- Fix approach: Integrate an embedder and `VectorSearcher` into the MCP server.

### Index Update Logic Skips Changed Documents
- Issue: In `src/docsift/cli/commands/index.py` line 108, the update logic checks `if existing.checksum != parsed.checksum and not force:` then skips the file. The condition should be `if existing.checksum == parsed.checksum and not force:` to skip unchanged files.
- Files: `src/docsift/cli/commands/index.py`
- Impact: Changed documents are skipped unless `--force` is passed; unchanged documents may be re-processed depending on intent.
- Fix approach: Invert the checksum equality logic.

## Security Considerations

### SQL Injection via F-String Query Building
- Issue: `BM25Searcher.search()` and `VectorSearcher._search_with_vec()` build SQL using f-strings for `collection_filter` with `?` placeholders, which is mostly safe, but `BM25Searcher.search_chunks()` and the FTS table creation do not validate `query` input before passing to FTS `MATCH`. More critically, `SchemaManager.drop_all()` uses f-strings for table names, and several repository methods construct dynamic SQL.
- Files: `src/docsift/search/bm25.py`, `src/docsift/search/vector.py`, `src/docsift/database/schema.py`
- Risk: FTS5 `MATCH` with unescaped user input can trigger syntax errors or potentially be manipulated. Dynamic table names in `drop_all()` are low risk but bad practice.
- Current mitigation: Collection IDs use parameterized queries.
- Recommendations: Sanitize or escape FTS query terms before `MATCH`; avoid f-string table names in schema management.

### CORS Origins Set to Wildcard in MCP HTTP Transport
- Issue: `HTTPTransport` defaults `cors_origins` to `["*"]`.
- Files: `src/docsift/mcp/transport_http.py`
- Risk: Any website can make requests to the local MCP HTTP server.
- Recommendations: Default to `[]` or `["http://localhost"]`, and require explicit configuration for `*`.

## Performance Bottlenecks

### Fallback Vector Search Loads All Embeddings into Memory
- Issue: `VectorSearcher._search_fallback()` selects every row from `document_embeddings`, deserializes all embeddings, and computes cosine similarity in Python.
- Files: `src/docsift/search/vector.py` (lines 103–157)
- Cause: O(N) memory and CPU scaling with number of chunks.
- Improvement path: Require `sqlite-vec` for production use; the fallback should emit a warning and refuse to run on large indexes, or paginate queries.

### Chunk Repository Deletes FTS Rows One-by-One
- Issue: `DocumentChunkRepository.delete_by_document()` loops over chunk IDs and issues individual `DELETE` statements against `chunks_fts`.
- Files: `src/docsift/database/repositories.py` (lines 339–358)
- Cause: N+1 deletes when removing a document.
- Improvement path: Use `DELETE FROM chunks_fts WHERE rowid IN (...)` with a single query.

### Collection Stats Re-count Documents on Every Index Operation
- Issue: `index_collection()` in `src/docsift/indexing/indexer.py` calls `self._repository.list_by_collection(collection.id).__len__()` to update stats.
- Files: `src/docsift/indexing/indexer.py`
- Cause: Loads all documents just to count them.
- Improvement path: Use `COUNT(*)` SQL or maintain counters incrementally.

## Fragile Areas

### MCP Protocol Import Coupling
- Files: `src/docsift/mcp/transport_http.py`, `src/docsift/mcp/transport_stdio.py`
- Why fragile: Both transports import `MCPServer`, `ServerConfig`, `ServerState` from `.server`, but `.server` also imports from `docsift.database.database` and `docsift.search.hybrid`. This creates a tight import web where changes to search or database code can break the MCP server startup.
- Safe modification: Always test `python -m docsift.mcp.transport_stdio` and `python -m docsift.mcp.transport_http` after modifying database or search modules.
- Test coverage: No dedicated transport-level unit tests were found.

### Database Connection Singleton Pattern
- Issue: `Database.connection` is a cached property that returns the same `sqlite3.Connection` across the lifetime of the `Database` object, with `check_same_thread=False`.
- Files: `src/docsift/database/database.py`
- Why fragile: SQLite connections are not truly thread-safe for concurrent writes. The MCP HTTP server (FastAPI/async) and CLI may share connection patterns incorrectly.
- Safe modification: Use connection-per-request or a connection pool for async contexts; keep `DatabaseConnection.connect()` context manager for CLI.

### Hard-Coded Model Path in CLI Embed Command
- Issue: `embed_cmd` hard-codes `SentenceTransformer("BAAI/bge-small-zh-v1.5")`.
- Files: `src/docsift/cli/commands/index.py` (line 185)
- Why fragile: Users cannot configure the model via settings or CLI flags. The model download may fail silently or use an unexpected model.
- Fix approach: Read `model_name` from `Settings` and allow CLI override.

## Missing Critical Features

### No Real LLM Reranking or Query Expansion
- Problem: `SearchPipeline` and `HybridSearcher` accept `reranker` and `query_expander` objects, but no concrete implementations are wired in the CLI or MCP server.
- Files: `src/docsift/search/hybrid.py`, `src/docsift/cli/commands/search.py`
- Blocks: Advanced hybrid search quality improvements.

### No Batch / Bulk Operations for Embeddings
- Problem: `VectorSearcher.add_embedding()` inserts one embedding at a time. The `embed_cmd` loops over chunks individually.
- Files: `src/docsift/search/vector.py`, `src/docsift/cli/commands/index.py`
- Blocks: Efficient indexing of large collections.

## Test Coverage Gaps

### Transport and Server Tests Are Minimal
- What's not tested: `mcp/transport_http.py`, `mcp/transport_stdio.py`, and the full JSON-RPC request/response cycle of `MCPServer`.
- Files: `src/docsift/mcp/transport_http.py`, `src/docsift/mcp/transport_stdio.py`, `src/docsift/mcp/server.py`
- Risk: MCP protocol regressions go unnoticed.
- Priority: Medium

### Embedding Factory Not Tested with Real Models
- What's not tested: Actual GGUF or SentenceTransformers loading paths in `embedding/factory.py`.
- Files: `src/docsift/embedding/factory.py`
- Risk: Model loading regressions and environment-specific failures.
- Priority: Medium

### End-to-End Search Quality Not Validated
- What's not tested: Whether BM25 + Vector + RRF actually returns better results than BM25 alone on real documents.
- Files: `src/docsift/search/hybrid.py`, `src/docsift/search/rrf.py`
- Risk: Fusion algorithm bugs or scoring inversions go unnoticed.
- Priority: Low

## Dependencies at Risk

### `llama-cpp-python` and `sentence-transformers` Are Heavy Optional Dependencies
- Risk: These packages pull in large native libraries (CUDA, Metal, compiled extensions) that frequently fail to install in clean environments.
- Impact: Users cannot install `docsift[all]` or `docsift[embed]` on systems without the correct toolchain.
- Migration plan: Keep embeddings as an optional extra; ensure the core package works without them (it mostly does, but vector search CLI commands degrade gracefully to BM25).

---

*Concerns audit: 2026-04-14*
