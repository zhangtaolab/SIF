# Domain Pitfalls

**Domain:** Python local LLM / document search (embeddings, vector search, MCP servers, SQLite-based storage)
**Researched:** 2026-04-14
**Confidence:** MEDIUM-HIGH (based on verified codebase issues + domain research)

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: Placeholder Embedding Implementations in Production Code
**What goes wrong:** Factory methods raise `NotImplementedError` for some model types, while other paths return `numpy.random.rand()` embeddings. A hard-coded model path in the CLI embed command bypasses configuration entirely. Users get silently wrong vector search results or crashes.
**Why it happens:** Embedding models are heavy dependencies, so developers stub them out during early development and forget to remove the stubs before shipping.
**Consequences:** Vector search returns garbage (random vectors), semantic similarity is meaningless, and reranking pipelines fail.
**Prevention:**
- Never commit random/placeholder embeddings to `main`.
- Gate incomplete model backends behind feature flags or optional extras, and fail fast with a clear error if a user selects an unimplemented backend.
- Load model names from `Settings`, not hard-coded strings in CLI commands.
**Detection:** Run a smoke test that embeds two semantically similar sentences and asserts cosine similarity > 0.5.
**Phase to address:** Phase 1 (Bugfix / Stub Removal)

### Pitfall 2: Brute-Force Vector Search Fallback That Loads All Embeddings into Memory
**What goes wrong:** A fallback vector search implementation selects every row from the embeddings table, deserializes all vectors, and computes cosine similarity in pure Python. This works for demos but collapses linearly as the corpus grows.
**Why it happens:** Developers want the system to work even when `sqlite-vec` is not installed, so they write a naive fallback. They underestimate how quickly personal note collections grow.
**Consequences:** O(N) memory and CPU scaling. A few thousand chunks may be fine, but tens of thousands cause multi-second latency and RAM spikes. Users experience "my search got slower for no reason."
**Prevention:**
- Make `sqlite-vec` a required dependency for vector search; do not offer a naive Python fallback in production.
- If a fallback is absolutely necessary, cap the maximum index size (e.g., refuse to run fallback on >5,000 chunks) and emit a loud warning.
- Use `sqlite-vec` for exact KNN; accept its brute-force nature inside SQLite (which is still faster than Python loops) and monitor query latency.
**Detection:** Profile `vsearch` with 10K+ chunks. If RSS memory grows proportionally to chunk count, the fallback is being hit.
**Phase to address:** Phase 1 (Bugfix / Stub Removal)

### Pitfall 3: MCP Server Writing to `stdout` (Breaking STDIO Transport)
**What goes wrong:** Any `print()`, default logging to `stdout`, or debug output sent to `stdout` corrupts the JSON-RPC stream between MCP host and server. The host sees malformed JSON and disconnects.
**Why it happens:** Python developers habitually use `print()` for debugging. MCP STDIO transport reuses `stdout` for protocol messages, so even innocent log statements become fatal.
**Consequences:** MCP server appears "unreachable" or "crashes on startup." The root cause is hidden because the error manifests in the host, not the server.
**Prevention:**
- Configure all logging to `sys.stderr` at server startup.
- Add a lint rule or code review checklist: "No `print()` in MCP server code."
- Use the official MCP Python SDK transport classes, which already isolate protocol I/O.
**Detection:** Run the server under Claude Desktop or Claude Code; if initialization fails with JSON parse errors, check for stdout pollution.
**Phase to address:** Phase 3 (MCP Server Unification)

### Pitfall 4: SQLite Connection Singleton with `check_same_thread=False`
**What goes wrong:** A cached `sqlite3.Connection` is shared across the lifetime of a `Database` object with `check_same_thread=False`. In async contexts (FastAPI/MCP HTTP), multiple requests hit the same connection simultaneously.
**Why it happens:** SQLite connections are expensive to create, so developers cache them. `check_same_thread=False` is used as a band-aid to bypass Python's thread-ownership check.
**Consequences:** Race conditions, `sqlite3.ProgrammingError`, data corruption, and event-loop blocking. The error is intermittent and hard to reproduce.
**Prevention:**
- Use connection-per-request for the MCP HTTP server, or offload sync SQLite calls to a thread pool with `run_in_threadpool`.
- For CLI, keep the context-manager pattern (`with DatabaseConnection.connect():`).
- If persistent connections are needed, use `threading.local()` so each thread gets its own connection.
**Detection:** Stress-test the MCP HTTP transport with concurrent requests; watch for `SQLite objects created in a thread can only be used in that same thread`.
**Phase to address:** Phase 3 (MCP Server Unification)

### Pitfall 5: FTS5 External Content Tables Without Synchronization
**What goes wrong:** FTS5 virtual tables are created without `content=` / `content_rowid=` linking to main tables, and no triggers or application-level logic keeps them synchronized. BM25 search joins on `fts.rowid = documents.id`, but the FTS table may be empty or stale.
**Why it happens:** FTS5 syntax looks like a regular `CREATE TABLE`, so developers assume it auto-syncs. It does not.
**Consequences:** BM25 returns empty or stale results. Users think keyword search is broken.
**Prevention:**
- Use FTS5 external content tables with explicit `content='documents', content_rowid='id'`.
- Create `AFTER INSERT/UPDATE/DELETE` triggers to mirror changes into the FTS table, or handle it explicitly in repository methods.
- Always include `rowid` in FTS5 `INSERT` statements; omitting it causes `rowid` mismatches that corrupt the index.
**Detection:** Insert a document, then query BM25 for a unique word from that document. If no results, synchronization is missing.
**Phase to address:** Phase 1 (Bugfix / Stub Removal)

### Pitfall 6: Missing Runtime Dependencies in `pyproject.toml`
**What goes wrong:** The package imports `sqlite-vec`, `structlog`, `platformdirs`, `pydantic-settings`, `fastapi`, `uvicorn`, and others, but none are declared in `[project] dependencies`.
**Why it happens:** Development environments often have these installed globally or via `requirements.txt`, so the omission is not noticed until a clean `pip install` fails.
**Consequences:** Users install the package and immediately hit `ModuleNotFoundError`. First-run experience is broken.
**Prevention:**
- Run `pip install` in a fresh venv and execute the CLI entry point as a CI step.
- Use `pipdeptree` or `pyproject-fmt` to audit declared vs imported packages.
- Declare heavy/optional deps (e.g., `llama-cpp-python`, `sentence-transformers`) under `[project.optional-dependencies]` so the core package is lightweight.
**Detection:** `python -m docsift --help` in a clean venv should not raise import errors.
**Phase to address:** Phase 1 (Bugfix / Stub Removal)

### Pitfall 7: Duplicate Repository Implementations with Schema Drift
**What goes wrong:** Two parallel repository files (`repositories.py` and `sqlite_repository.py`) use different schemas, different model imports, and different behavior. Tests use one; CLI/MCP use the other.
**Why it happens:** Refactoring started a new repository layer but the old one was never deleted.
**Consequences:** Fixes in one file do not apply to the other. Schema migrations become ambiguous. Tests pass against code that production does not use.
**Prevention:**
- Delete the legacy file as soon as the new one is wired up.
- If a transition period is needed, rename the old file with a `_legacy` suffix and add a `DeprecationWarning`.
**Detection:** Search for multiple classes implementing the same repository interface. If more than one exists, consolidation is needed.
**Phase to address:** Phase 1 (Bugfix / Stub Removal)

### Pitfall 8: `llama-cpp-python` Embedding Regressions and Fork Confusion
**What goes wrong:** `llama-cpp-python` has a documented regression (post-v0.3.14) where batch embedding calls fail with `RuntimeError: llama_decode returned -1`. Additionally, a community fork emerged in mid-2025 due to an upstream maintenance hiatus, creating version confusion.
**Why it happens:** The underlying `llama.cpp` C++ library moves fast; the Python bindings occasionally lag or break.
**Consequences:** Local GGUF embedding models crash on multi-text batching. Users may install the wrong package variant and get incompatible binaries.
**Prevention:**
- Process embeddings one text at a time with `llama-cpp-python` until the batch regression is resolved.
- Pin `llama-cpp-python` to a known-good version in `pyproject.toml` and document the constraint.
- Verify GGUF model architecture compatibility before adding a model to the supported list.
**Detection:** Run the embedding factory's GGUF path against a small test corpus. If it crashes on the second text, the regression is present.
**Phase to address:** Phase 2 (Embedding Model Configurability)

### Pitfall 9: MCP Tool Handlers Returning Mock Data Instead of Calling Real Services
**What goes wrong:** `mcp_server/tools.py` contains placeholder tool handlers that return hard-coded strings like `"Mock search result"` rather than invoking `SearchService` or `DocumentIndexer`.
**Why it happens:** MCP server skeleton was scaffolded before the business logic was ready.
**Consequences:** The alternative MCP server package (`mcp_server/`) is completely non-functional. Users configuring their client to use it get meaningless results.
**Prevention:**
- Do not ship mock handlers in production modules. Keep mocks in `tests/` or a dedicated `mocks/` package.
- Wire tool handlers to real services as soon as the service interface stabilizes.
- If a tool is not yet ready, return a clear error message explaining the missing capability.
**Detection:** Call each MCP tool and verify the response contains data from the actual database, not a mock string.
**Phase to address:** Phase 3 (MCP Server Unification)

### Pitfall 10: Sentence-Transformers Memory Spikes from Ignored Batch Size
**What goes wrong:** Code calls `model.encode(chunks)` without passing `batch_size`. `sentence-transformers` falls back to its default (32), which can OOM when chunks are long or the model has a large context window.
**Why it happens:** The `batch_size` parameter is easy to overlook, and defaults seem safe until they are not.
**Consequences:** RAM/VRAM spikes during indexing, process killed by the OS, or degraded system performance.
**Prevention:**
- Always pass an explicit `batch_size` to `encode()`.
- Expose batch size as a configurable setting (e.g., `embedding_batch_size`) with a conservative default (e.g., 16).
- Monitor memory during indexing and auto-reduce batch size on `MemoryError`.
**Detection:** Index a collection with 1,000 long chunks and watch RSS. If it spikes by multiple gigabytes, batch size is too large.
**Phase to address:** Phase 2 (Embedding Model Configurability)

## Moderate Pitfalls

### Pitfall 1: CORS Origins Set to Wildcard in MCP HTTP Transport
**What goes wrong:** `HTTPTransport` defaults `cors_origins` to `["*"]`, allowing any website to make requests to the local MCP server.
**Prevention:** Default to `[]` or `["http://localhost"]`, and require explicit configuration for `*`.
**Phase to address:** Phase 3 (MCP Server Unification)

### Pitfall 2: SQL Injection via F-String Query Building
**What goes wrong:** Dynamic SQL in `BM25Searcher`, `VectorSearcher`, and `SchemaManager` uses f-strings for table names and FTS `MATCH` queries. User input is not always sanitized.
**Prevention:**
- Use parameterized queries (`?` placeholders) for all values.
- Sanitize or escape FTS5 `MATCH` terms before passing them to SQLite.
- Validate table/collection identifiers against a whitelist rather than interpolating them.
**Phase to address:** Phase 1 (Bugfix / Stub Removal)

### Pitfall 3: N+1 Deletes in Chunk Repository
**What goes wrong:** `DocumentChunkRepository.delete_by_document()` loops over chunk IDs and issues individual `DELETE` statements against `chunks_fts`.
**Prevention:** Use `DELETE FROM chunks_fts WHERE rowid IN (...)` with a single query.
**Phase to address:** Phase 1 (Bugfix / Stub Removal)

### Pitfall 4: Collection Stats Re-count Documents on Every Index Operation
**What goes wrong:** `index_collection()` calls `len(list(repository.list_by_collection(...)))` to update stats, loading every document row just to count them.
**Prevention:** Use `COUNT(*)` SQL or maintain increment/decrement counters.
**Phase to address:** Phase 1 (Bugfix / Stub Removal)

### Pitfall 5: Index Update Logic with Inverted Checksum Condition
**What goes wrong:** The update logic uses `if existing.checksum != parsed.checksum and not force: skip`. This skips changed documents unless `--force` is passed.
**Prevention:** Invert to `if existing.checksum == parsed.checksum and not force: skip`.
**Phase to address:** Phase 1 (Bugfix / Stub Removal)

## Minor Pitfalls

### Pitfall 1: Vector Search CLI Falls Back to BM25 Without Embeddings
**What goes wrong:** `vsearch_cmd` always prints a warning and falls back to BM25, even if embeddings exist.
**Prevention:** Reuse the embedder logic from `embed_cmd` to generate query embeddings before calling `VectorSearcher`.
**Phase to address:** Phase 1 (Bugfix / Stub Removal)

### Pitfall 2: MCP Server `vec_search` Tool Delegates to `lex_search`
**What goes wrong:** `MCPServer._tool_vec_search()` calls `_tool_lex_search()` directly, silently returning keyword results for vector search requests.
**Prevention:** Integrate an embedder and `VectorSearcher` into the MCP server.
**Phase to address:** Phase 3 (MCP Server Unification)

### Pitfall 3: Tight Import Coupling Between MCP Transports and Search/Database Modules
**What goes wrong:** `transport_http.py` and `transport_stdio.py` import `MCPServer`, which imports database and search modules. A change in search logic can break MCP server startup.
**Prevention:** Use dependency injection or lazy imports in the transport layer. Add transport-level smoke tests.
**Phase to address:** Phase 3 (MCP Server Unification)

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Bugfix / Stub Removal | Placeholder embeddings, missing deps, FTS5 desync, inverted checksum | Smoke tests for every CLI command; verify BM25 and vector search against real data |
| Embedding Model Configurability | `llama-cpp-python` batch crash, sentence-transformers OOM, hard-coded model path | Pin versions, expose batch_size, test each backend with a small corpus |
| MCP Server Unification | Mock tool handlers, stdout pollution, singleton SQLite connection, CORS wildcard | End-to-end MCP test with real client; run concurrency tests on HTTP transport |
| Rerank / Query Expansion | LLM reranking latency spikes, context window overflow | Add timeout and truncation guards; benchmark against qmd baseline |

## Sources

- Codebase audit: `.planning/codebase/CONCERNS.md` (2026-04-14)
- OWASP LLM08:2025 — Vector and Embedding Weaknesses
- "Real Faults in Model Context Protocol (MCP) Software" (arXiv:2603.05637v1)
- SQLite FTS5 documentation and external content table best practices (2025)
- `llama-cpp-python` issue analyses and community reports (2025)
- `sqlite-vec` scaling and ANN limitations (GitHub issue #25, 2024-2025)
- Sentence-transformers batch size and memory optimization guides (2025)
- Python sqlite3 thread safety discussions (Python 3.11+, 2025)
