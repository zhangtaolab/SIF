# Project Research Summary

**Project:** DocSift
**Domain:** Local-first Python document search engine (personal knowledge base)
**Researched:** 2026-04-14
**Confidence:** HIGH

## Executive Summary

DocSift is a local-first, CLI-driven document search engine targeting personal knowledge bases. The research confirms it should follow a layered Python architecture with dual interfaces (CLI via Click and MCP server for AI assistants), SQLite as the single storage engine (FTS5 for BM25 + `sqlite-vec` for vector search), and local embedding models via `sentence-transformers` and `llama-cpp-python`. The codebase already has solid structural bones but is currently blocked by stubbed implementations, missing dependencies, duplicate code paths, and placeholder logic that would silently produce garbage results if shipped.

The recommended approach is to fix the foundation first: remove embedding stubs, consolidate duplicate repositories, declare missing dependencies, and synchronize FTS5 tables. Only after the core indexing and search pipelines are trustworthy should the project add configurability (embedding model selection), advanced search features (reranking, query expansion), and finally unify the dual MCP implementations into a single server using `fastmcp`.

Key risks are all addressable: (1) placeholder embeddings and mock MCP handlers will break user trust if not caught—smoke tests are essential; (2) `llama-cpp-python` has a known batch-embedding regression after v0.3.14, so GGUF paths should process one text at a time until verified; (3) SQLite connection sharing across async MCP requests will cause race conditions—connection-per-request or threadpool offloading is required; (4) missing runtime dependencies in `pyproject.toml` will break first installs and must be audited in CI.

## Key Findings

### Recommended Stack

DocSift should stay Python-based and double down on SQLite as the single storage engine. Vector search should use `sqlite-vec` (not ChromaDB, FAISS, or LanceDB) because it keeps vectors in the same file as metadata and requires no external server. For embeddings, `sentence-transformers` is the default backend, while `llama-cpp-python` provides GGUF embedding and reranking support. The MCP server should be rebuilt on `fastmcp` >=3.2.4, which is now the dominant Python MCP framework and replaces the current low-level scaffolding. Python minimum should be bumped to 3.10 because `llama-cpp-python` 0.3.20 does not ship pre-built wheels for 3.9.

**Core technologies:**
- **Python 3.10+**: Runtime. Required because `llama-cpp-python` 0.3.20 lacks pre-built wheels for 3.9.
- **SQLite + FTS5 + `sqlite-vec`**: Relational, full-text, and vector search in a single file. Zero external server dependencies.
- **`sentence-transformers` >=5.4.0**: Default embedding backend. GPU-accelerated, batched, and supports the best open-source embedding models.
- **`llama-cpp-python` >=0.3.20**: GGUF embeddings and local reranking. v0.3.20 adds native reranking via `LLAMA_POOLING_TYPE_RANK`.
- **`fastmcp` >=3.2.4**: High-level MCP server framework. Decorator-based, async-friendly, and replaces legacy MCP scaffolding.
- **`click` + `rich` + `pydantic` v2**: CLI framework, terminal formatting, and config validation. Already integrated and stable.

### Expected Features

Users expect BM25 search, collection management, document indexing with checksum deduplication, vector semantic search, hybrid search, and MCP integration. DocSift already has many of these partially implemented, but several table-stakes features are missing (`multi-get`, `ls`, working vector search). The biggest competitive differentiators from qmd are LLM reranking, query expansion, query document syntax (`lex:`, `vec:`, `hyde:`), and score explainability.

**Must have (table stakes):**
- BM25 full-text search — already implemented via FTS5.
- Collection management (add/list/remove/rename/show) — partially done; missing `update-cmd` and include/exclude filters.
- Document indexing with checksum dedup — already implemented.
- File retrieval (`get`, `multi-get`, `ls`) — `get` exists; `multi-get` and `ls` are missing.
- Vector semantic search — partially implemented; stubbed embedder fallback must be replaced.
- Hybrid search (BM25 + vector fusion) — already implemented with RRF.
- MCP server integration — skeleton exists; needs unification and real tool handlers.
- Local-first execution — core design constraint.

**Should have (competitive):**
- LLM reranking — the "secret sauce" of qmd's `query` command.
- LLM query expansion — improves recall for vague queries.
- Query document format (`lex:`, `vec:`, `hyde:`, `expand:`) — power-user feature unique to qmd.
- Score explainability (`--explain`) — useful for debugging and tuning.
- Min-score threshold (`--min-score`) — critical for agent integrations.
- Context descriptions (`context add`) — improves retrieval quality for agents.

**Defer (v2+):**
- Search benchmarking (`bench`) — nice for tuning, not essential.
- Per-collection model configuration — advanced optimization.
- Intent parameter — requires the full pipeline to be mature first.
- Smart snippet extraction with intent weighting — polishing feature.

### Architecture Approach

DocSift follows a layered modular architecture: Interface (CLI + MCP), Application (search pipeline + indexing pipeline), Domain (models and protocols), and Infrastructure (SQLite, embedding models, config). The codebase already aligns well with this structure. The remaining work is to consolidate the dual MCP packages (`mcp/` and `mcp_server/`), fill in missing search pipeline components (reranker, query expander), and extract a service layer so that CLI and MCP share the same business logic instead of duplicating it.

**Major components:**
1. **CLI Layer (`cli/`)** — Click commands and output formatters. Should remain thin and delegate to services.
2. **MCP Layer (`mcp/`)** — Unified MCP server exposing search and retrieval tools. Must be rebuilt on `fastmcp`.
3. **Search Layer (`search/`)** — Strategy-based retrieval (BM25, vector, hybrid, RRF, reranking). Each algorithm is a standalone class.
4. **Indexing Layer (`indexing/`)** — Pipeline: scan → parse → chunk → embed → persist. `DocumentIndexer` orchestrates.
5. **Embedding Layer (`embedding/`)** — Model lifecycle, caching, and batching. Isolated because model loading is expensive.
6. **Database Layer (`database/`)** — SQLite schema, connection management, and repository pattern for all CRUD.
7. **Core Domain (`core/`)** — Shared models, enums, and `typing.Protocol` definitions for embedders and rerankers.

### Critical Pitfalls

The codebase audit revealed ten critical pitfalls, most of which cluster around stubbed implementations, missing dependencies, and SQLite/MCP concurrency issues. The top risks are:

1. **Placeholder embedding implementations in production code** — Factory methods raise `NotImplementedError` or return random vectors. Prevention: gate incomplete backends behind feature flags, load model names from `Settings`, and run a cosine-similarity smoke test.
2. **Brute-force vector search fallback loading all embeddings into memory** — `VectorSearcher._search_fallback()` is O(N) in Python and will break at scale. Prevention: make `sqlite-vec` required, cap or remove the fallback.
3. **MCP server writing to `stdout` (breaking STDIO transport)** — Any `print()` or logging to `stdout` corrupts JSON-RPC. Prevention: configure all logging to `sys.stderr`, ban `print()` in MCP code, and test with a real MCP client.
4. **SQLite connection singleton with `check_same_thread=False`** — Shared connections across async MCP requests cause race conditions and `ProgrammingError`. Prevention: connection-per-request or threadpool offloading for the HTTP transport.
5. **FTS5 external content tables without synchronization** — Missing triggers or explicit mirroring causes BM25 to return empty/stale results. Prevention: use `content=` / `content_rowid=` and maintain synchronization via triggers or repository logic.
6. **Missing runtime dependencies in `pyproject.toml`** — Imports exist for packages not declared as dependencies. Prevention: install in a clean venv and run the CLI as a CI step.
7. **Duplicate repository implementations with schema drift** — `repositories.py` and `sqlite_repository.py` coexist with different schemas. Prevention: delete the legacy file immediately after wiring up the new one.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Foundation Fix (Bugfix / Stub Removal)
**Rationale:** The foundation is currently unsafe to build on. Stubbed embeddings, missing dependencies, duplicate repositories, and broken checksum logic will corrupt every feature built above them. This phase must come first.
**Delivers:** A trustworthy embedding layer, a single repository implementation, synchronized FTS5 tables, and a clean `pyproject.toml`.
**Addresses:** Fix stubbed embedder (FEATURES.md P1), `get` / `multi-get` / `ls` commands (FEATURES.md P1), missing runtime dependencies.
**Avoids:** Placeholder embeddings (PITFALLS.md #1), brute-force fallback (PITFALLS.md #2), FTS5 desync (PITFALLS.md #5), missing deps (PITFALLS.md #6), duplicate repositories (PITFALLS.md #7), inverted checksum logic (PITFALLS.md moderate #5), SQL injection via f-strings (PITFALLS.md moderate #2), N+1 deletes (PITFALLS.md moderate #3), collection stats re-counting (PITFALLS.md moderate #4), vector search CLI fallback to BM25 (PITFULLS.md minor #1).

### Phase 2: Embedding Model Configurability
**Rationale:** Working vector search and configurable models unlock hybrid search and everything that depends on it (reranking, query expansion). This is a natural next step once the foundation is solid.
**Delivers:** Configurable embedding backends (`sentence-transformers` default, `llama-cpp-python` GGUF optional), working `vsearch` and `query` CLI commands, and embedding cache/manager hardening.
**Uses:** `sentence-transformers` >=5.4.0, `llama-cpp-python` >=0.3.20, `sqlite-vec` >=0.1.9 (STACK.md).
**Avoids:** `llama-cpp-python` batch regression (PITFALLS.md #8 — process one text at a time), sentence-transformers memory spikes (PITFALLS.md #10 — expose `batch_size` setting with conservative default).

### Phase 3: MCP Server Unification
**Rationale:** MCP depends on stable search and retrieval APIs. Unifying the server last avoids refactoring it twice as the underlying services change.
**Delivers:** A single `mcp/` package built on `fastmcp`, with real tool handlers wired to `SearchService` and `IndexService`, supporting both stdio and HTTP transports.
**Addresses:** MCP server unification (FEATURES.md P1).
**Avoids:** Mock tool handlers (PITFALLS.md #9), stdout pollution (PITFALLS.md #3), SQLite singleton races (PITFALLS.md #4), CORS wildcard (PITFALLS.md moderate #1), tight import coupling (PITFALLS.md minor #3), `vec_search` delegating to `lex_search` (PITFALLS.md minor #2).

### Phase 4: Advanced Search Pipeline (Rerank + Query Expansion)
**Rationale:** These are the main quality differentiators, but they depend on a fully working embedding layer and stable search pipeline from Phase 2.
**Delivers:** LLM reranking, LLM query expansion, query document syntax (`lex:`, `vec:`, `hyde:`), and score explainability (`--explain`).
**Addresses:** LLM reranking (FEATURES.md P2), LLM query expansion (FEATURES.md P2), query document format (FEATURES.md P2), `--explain` (FEATURES.md P2).
**Avoids:** LLM reranking latency spikes (PITFALLS.md phase warnings) — add timeout and truncation guards.

### Phase 5: Agent Experience & Polish
**Rationale:** Lower-priority features that improve the tool for agent workflows and power users once the core pipeline is mature.
**Delivers:** `--min-score`, full-content / line-number output, context descriptions, `update-cmd`, `--candidate-limit`.
**Addresses:** `--min-score` (FEATURES.md P2), context descriptions (FEATURES.md P2), `update-cmd` (FEATURES.md P2), full-content/line-number output (FEATURES.md P2).

### Phase Ordering Rationale

- **Dependencies dictate order:** Vector search requires a working embedder; MCP requires stable search and retrieval APIs; reranking requires hybrid search.
- **Risk reduction:** Fixing stubs and dependencies first prevents building features on broken assumptions.
- **Architecture alignment:** The suggested order mirrors the "Suggested Build Order for Missing Pieces" in ARCHITECTURE.md (fix stubs → complete CLI → query expansion/reranking → unify MCP).

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4 (Advanced Search Pipeline):** The `llama-cpp-python` batch embedding regression and GGUF reranker integration may need API-level research to confirm exact call patterns for `LLAMA_POOLING_TYPE_RANK`. Query expansion model selection also lacks a single consensus choice in the Python ecosystem.
- **Phase 5 (Agent Experience & Polish):** Snippet extraction and intent-aware scoring are not yet well-defined in the codebase; if these are pulled forward, they will need design research.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Foundation Fix):** Well-understood bugs with clear fixes. No additional research needed.
- **Phase 2 (Embedding Model Configurability):** Standard `sentence-transformers` and `sqlite-vec` patterns are well documented.
- **Phase 3 (MCP Server Unification):** `fastmcp` 3.x patterns are established and documented at gofastmcp.com.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified via PyPI dry-run installs, official docs, and ecosystem consensus. `sqlite-vec`, `fastmcp`, `sentence-transformers`, and `llama-cpp-python` versions are all confirmed. |
| Features | MEDIUM | qmd feature set is well documented, but some docsift-specific trade-offs (e.g., which qmd features to port vs. defer) are judgment calls based on priority matrix. |
| Architecture | HIGH | Codebase audit provides direct evidence of current structure and gaps. Patterns (repository, strategy, pipeline) are standard and well documented. |
| Pitfalls | MEDIUM-HIGH | Based on verified codebase issues (`CONCERNS.md`) plus domain research. Most pitfalls are directly observable in the current code. |

**Overall confidence:** HIGH

### Gaps to Address

- **GGUF reranker call patterns:** The exact Python API for `llama-cpp-python` 0.3.20 reranking (`LLAMA_POOLING_TYPE_RANK`) is documented but should be validated with a small integration test before Phase 4 planning.
- **Query expansion model choice:** No single lightweight local model dominates for query expansion in Python. During Phase 4 planning, evaluate rule-based expansion vs. small GGUF/Sentence-Transformer options.
- **MCP client testing strategy:** We need a reproducible MCP client test harness (e.g., Claude Code or a scripted JSON-RPC client) to verify stdio and HTTP transports end-to-end before Phase 3 execution.
- **Windows compatibility of `sqlite-vec`:** macOS ARM64 and Linux x86_64 wheels exist; Windows may need MSVC redistributables. If Windows is a supported target, this needs validation.

## Sources

### Primary (HIGH confidence)
- DocSift codebase analysis (`src/docsift/`, `.planning/codebase/CONCERNS.md`) — current structure, stubs, and bugs.
- [llama-cpp-python PyPI](https://pypi.org/project/llama-cpp-python/) — version 0.3.20, batch embedding regression notes.
- [sqlite-vec PyPI](https://pypi.org/project/sqlite-vec/) — version 0.1.9, installation and API verification.
- [fastmcp PyPI](https://pypi.org/project/fastmcp/) — version 3.2.4, decorator-based API.
- [sentence-transformers PyPI](https://pypi.org/project/sentence-transformers/) — version 5.4.0, `encode()` API stability.
- [sqlite-vec Official Docs](https://alexgarcia.xyz/sqlite-vec/) — hybrid FTS5 + vector query patterns.
- [FastMCP Documentation](https://gofastmcp.com/) — transport and tool handler patterns.

### Secondary (MEDIUM confidence)
- [tobi/qmd on GitHub](https://github.com/tobi/qmd) — feature parity target.
- [QMD Changelog](https://github.com/tobi/qmd/blob/main/CHANGELOG.md) — versioned feature additions (`--explain`, `--intent`, etc.).
- [QMD Query Syntax Documentation](https://mintlify.com/tobi/qmd/concepts/query-syntax) — `lex:`, `vec:`, `hyde:` semantics.
- OWASP LLM08:2025 — Vector and Embedding Weaknesses.
- "Real Faults in Model Context Protocol (MCP) Software" (arXiv:2603.05637v1) — stdout pollution and transport issues.

### Tertiary (LOW confidence)
- `llama-cpp-python` community fork reports (mid-2025) — maintenance hiatus and version confusion. Needs re-verification at implementation time.
- `sqlite-vec` ANN limitations (GitHub issue #25, 2024-2025) — brute-force KNN is acceptable for personal scale, but HNSW is not yet available.

---
*Research completed: 2026-04-14*
*Ready for roadmap: yes*
