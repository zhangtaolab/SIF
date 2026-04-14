# Architecture Research: DocSift Python Document Search System

**Domain:** Local-first Python document search engine (personal knowledge base)
**Researched:** 2026-04-14
**Confidence:** HIGH

## Standard Architecture

### System Overview

DocSift follows a **layered modular architecture** with dual interfaces (CLI + MCP), a pipeline-based indexing flow, and a strategy-based search flow. The architecture prioritizes local execution, zero external dependencies by default, and clean separation between domain logic and infrastructure.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Interface Layer                               │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐              ┌─────────────────────────────────┐  │
│  │  CLI (Click) │              │  MCP Server (stdio / HTTP)      │  │
│  │  - search    │              │  - query                        │  │
│  │  - index     │              │  - lex_search                   │  │
│  │  - collection│              │  - vec_search                   │  │
│  │  - status    │              │  - get / multi_get              │  │
│  └──────┬───────┘              └───────────────┬─────────────────┘  │
│         │                                      │                      │
│         └──────────────────┬───────────────────┘                      │
├────────────────────────────┼────────────────────────────────────────┤
│                        Application Layer                             │
│  ┌─────────────────────────┼─────────────────────────────────────┐  │
│  │     Search Pipeline     │     Indexing Pipeline               │  │
│  │  ┌─────────────────┐    │    ┌───────────────────────────┐    │  │
│  │  │ QueryExpander   │    │    │ FileScanner               │    │  │
│  │  │ HybridSearcher  │──┐ │    │ Parser (MD/Code/Text)     │    │  │
│  │  │ Reranker        │  │ │    │ Chunker                   │    │  │
│  │  └─────────────────┘  │ │    │ DocumentIndexer           │    │  │
│  │                       │ │    └───────────────────────────┘    │  │
│  │  ┌─────────────────┐  │ │                                       │  │
│  │  │ BM25Searcher    │◄─┘ │    ┌───────────────────────────┐      │  │
│  │  │ VectorSearcher  │    │    │ EmbeddingManager          │      │  │
│  │  │ RRFFusion       │    │    │ - Model lifecycle         │      │  │
│  │  └─────────────────┘    │    │ - Cache                   │      │  │
│  │                         │    │ - Batch embed             │      │  │
│  └─────────────────────────┘    └───────────────────────────┘      │  │
├─────────────────────────────────────────────────────────────────────┤
│                        Domain Layer                                  │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Core Models: Collection, Document, DocumentChunk,            │  │
│  │  SearchResult, SearchOptions, Embedder (Protocol),            │  │
│  │  Reranker (Protocol), QueryExpander (Protocol)                │  │
│  └───────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│                        Infrastructure Layer                          │
│  ┌────────────────────┐  ┌────────────────────┐  ┌─────────────┐  │
│  │  Database (SQLite) │  │  Embedding Models  │  │  Config     │  │
│  │  - FTS5 (BM25)     │  │  - GGUF (llama-cpp)│  │  (Pydantic) │  │
│  │  - sqlite-vec      │  │  - Sentence-Trans. │  │             │  │
│  │  - Repository      │  │  - OpenAI compat.  │  │             │  │
│  └────────────────────┘  └────────────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Implementation in DocSift |
|-----------|----------------|---------------------------|
| CLI Layer | Parse user input, dispatch commands, format output | `src/docsift/cli/` using Click groups |
| MCP Layer | Expose tools via Model Context Protocol for AI assistants | `src/docsift/mcp/` (legacy) + `src/docsift/mcp_server/` (refactored) |
| Search Layer | Execute retrieval strategies and rank results | `src/docsift/search/` — BM25, vector, hybrid, RRF, reranking |
| Indexing Layer | Ingest files, parse content, chunk, embed, persist | `src/docsift/indexing/` — scanner, parser, chunker, indexer |
| Embedding Layer | Load models, generate vectors, cache results | `src/docsift/embedding/` — manager, factory, model ABC, cache |
| Database Layer | Schema management, persistence, repository pattern | `src/docsift/database/` — SQLite + repositories |
| Core Domain | Shared models, enums, protocols | `src/docsift/core/` — dataclasses and `typing.Protocol` |

## Recommended Project Structure

DocSift already has a well-structured layout. The remaining work is to consolidate the dual MCP implementations and fill in missing search pipeline components.

```
src/docsift/
├── cli/                    # Click commands and formatters
│   ├── commands/
│   │   ├── search.py       # search, vsearch, query commands
│   │   ├── index.py        # update, reindex commands
│   │   ├── collection.py   # CRUD for collections
│   │   ├── get.py          # get, multi_get
│   │   └── mcp.py          # mcp serve entry points
│   └── main.py             # CLI root + global options
├── core/                   # Domain models and protocols
│   ├── models.py           # Collection, Document, SearchResult, etc.
│   ├── protocols.py        # Embedder, Reranker, QueryExpander (optional split)
│   └── constants.py        # App-level constants
├── database/               # Persistence layer
│   ├── database.py         # Connection manager
│   ├── schema.py           # SchemaManager (DDL)
│   └── repositories.py     # CollectionRepository, DocumentRepository, etc.
├── indexing/               # Ingestion pipeline
│   ├── indexer.py          # DocumentIndexer orchestrator
│   ├── scanner.py          # File discovery
│   ├── parser.py           # Markdown, text, code parsers
│   └── chunker.py          # Chunker ABC + implementations
├── search/                 # Retrieval and ranking
│   ├── bm25.py             # FTS5 BM25 searcher
│   ├── vector.py           # sqlite-vec / fallback vector searcher
│   ├── hybrid.py           # HybridSearcher + SearchPipeline
│   ├── rrf.py              # Reciprocal Rank Fusion
│   ├── reranker.py         # LLM reranking implementation
│   └── expander.py         # Query expansion implementation
├── embedding/              # Model lifecycle
│   ├── manager.py          # EmbeddingManager
│   ├── model.py            # EmbeddingModel ABC
│   ├── factory.py          # EmbeddingModelFactory
│   └── cache.py            # EmbeddingCache (disk-based)
├── mcp/                    # Unified MCP server
│   ├── server.py           # MCP server core (merge legacy + refactored)
│   ├── transport.py        # Transport ABC + stdio + HTTP
│   ├── handlers.py         # ToolHandler / ResourceHandler ABCs
│   └── tools.py            # Concrete tool implementations
└── utils/                  # Cross-cutting helpers
    ├── logging.py
    ├── progress.py
    └── helpers.py
```

### Structure Rationale

- **`cli/`**: Separated by command domain. Output formatters live alongside commands because formatting is a presentation concern, not a domain concern.
- **`search/`**: Each strategy (BM25, vector, hybrid) is its own module. The pipeline (`hybrid.py`) composes them. Reranking and query expansion are search concerns, so they belong here.
- **`indexing/`**: The pipeline is unidirectional: scan → parse → chunk → embed → persist. The `DocumentIndexer` orchestrates without knowing database details (uses repositories).
- **`embedding/`**: Isolated because model loading is expensive and error-prone. Keeping it separate allows graceful degradation (e.g., fallback to BM25-only search if embedding fails).
- **`mcp/`**: The legacy `mcp/` and refactored `mcp_server/` should be unified into a single `mcp/` package. The refactored OOP abstractions (transport, handlers) are superior; the legacy tool implementations should be ported over.
- **`database/`**: Repository pattern keeps SQL out of business logic. One repository per aggregate root.

## Architectural Patterns

### Pattern 1: Protocol-Based Abstraction for Embeddings

**What:** Define embedding providers via `typing.Protocol` rather than inheritance.
**When to use:** When multiple implementations (local GGUF, sentence-transformers, OpenAI API) must be interchangeable without forcing a class hierarchy.
**Trade-offs:**
- Pro: No inheritance coupling; any object with `embed()`, `embed_batch()`, and `dimension` works.
- Con: Less discoverability than ABCs; mypy is required for static checking.

**Example:**
```python
class Embedder(Protocol):
    def embed(self, text: str) -> list[float]: ...
    def embed_batch(self, texts: list[str]) -> list[list[float]]: ...
    @property
    def dimension(self) -> int: ...

# Any of these works:
# - SentenceTransformersEmbedder
# - LlamaCppEmbedder
# - OpenAIEmbedder
```

### Pattern 2: Repository Pattern for Database Access

**What:** Encapsulate all SQLite CRUD and row mapping in repository classes.
**When to use:** When business logic (indexer, searchers, CLI) should not contain SQL.
**Trade-offs:**
- Pro: Easy to test with mocked repositories; schema changes are localized.
- Con: Slight boilerplate for simple queries; overkill if the app never grows beyond a few tables.

**Example:**
```python
class DocumentRepository:
    def __init__(self, db: sqlite3.Connection) -> None: ...
    def get_by_path(self, path: str, collection_id: str) -> Optional[Document]: ...
    def create(self, document: Document) -> Document: ...
```

### Pattern 3: Strategy Pattern for Search

**What:** Each search algorithm (BM25, vector, hybrid) is a standalone class with the same interface.
**When to use:** When you want to compose search strategies or swap them at runtime.
**Trade-offs:**
- Pro: `HybridSearcher` can delegate to `BM25Searcher` and `VectorSearcher` without knowing their internals.
- Con: Multiple classes with similar method signatures; shared helper methods may need duplication or a base class.

**Example:**
```python
class HybridSearcher:
    def __init__(self, db, embedder=None):
        self.bm25 = BM25Searcher(db)
        self.vector = VectorSearcher(db)
        self.rrf = RRFFusion(k=60)
```

### Pattern 4: Pipeline Pattern for Search Orchestration

**What:** `SearchPipeline` composes optional stages (query expansion → hybrid search → reranking) into a single `search()` call.
**When to use:** When search involves multiple optional, ordered transformations.
**Trade-offs:**
- Pro: Clean separation of concerns; easy to disable stages (pass `None` for expander/reranker).
- Con: Debugging requires stepping through multiple objects; error handling must be uniform.

**Example:**
```python
class SearchPipeline:
    def search(self, query: str, options: SearchOptions) -> list[SearchResult]:
        queries = [query]
        if self.query_expander:
            queries.extend(self.query_expander.expand(query))
        all_results = [self.hybrid.search(q, options) for q in queries]
        results = self.hybrid.rrf.fuse(all_results, options.limit) if len(all_results) > 1 else all_results[0]
        if self.reranker:
            results = self._rerank(query, results)
        return results
```

### Pattern 5: Graceful Degradation

**What:** Every optional subsystem (vector search, reranking, query expansion) fails safely back to the baseline.
**When to use:** Essential for local-first tools where optional models may be missing or misconfigured.
**Trade-offs:**
- Pro: User always gets *some* results; no hard dependency on large model downloads.
- Con: Silent failures can mask configuration issues; logging is critical.

**Current implementation:**
- `HybridSearcher.search()` catches vector search exceptions and returns BM25 results.
- `SearchPipeline.search()` catches expansion/reranking exceptions and returns intermediate results.
- CLI `vsearch` falls back to BM25 if embeddings are unavailable.

## Data Flow

### Indexing Flow

```
CLI: docsift index update <collection>
    ↓
DocumentIndexer.index_collection(collection)
    ↓
FileScanner.scan_multiple(paths) → list[Path]
    ↓
Parser.parse(path) → ParseResult (content, metadata, title)
    ↓
Checksum check → skip if unchanged
    ↓
Chunker.chunk(content) → list[DocumentChunk]
    ↓
EmbeddingManager.embed(chunk_texts) → list[embeddings]
    ↓
DocumentRepository.create/update(document_with_chunks)
    ↓
FTS5 tables + document_embeddings updated
```

### Search Flow (Full Pipeline)

```
CLI: docsift query "..."  or  MCP: tools/call query
    ↓
SearchPipeline.search(query, options)
    ↓
QueryExpander.expand(query) → [query, variant1, variant2]
    ↓ (for each variant)
HybridSearcher.search(variant, options)
    ├── BM25Searcher.search(variant) → list[SearchResult]
    └── VectorSearcher.search(embed(variant)) → list[SearchResult]
            ↓
        RRFFusion.fuse([bm25_results, vector_results]) → fused_results
            ↓
RRFFusion.fuse([results_for_all_variants]) → combined_results
    ↓
Reranker.rerank(original_query, document_contents) → reordered_results
    ↓
Output formatter (rich / JSON / CSV / Markdown / XML)
```

### MCP Request Flow

```
MCP Client (Claude Desktop)
    ↓
Transport (stdio or HTTP)
    ↓
MCPServer.handle_request(jsonrpc_request)
    ↓
Method router (initialize, tools/list, tools/call)
    ↓
ToolHandler.handle(params)
    ↓
Business logic (search, index, collection CRUD)
    ↓
JSON-RPC response → Transport.send()
```

### State Management

- **No global application state.** All persistent state is in SQLite (`~/.docsift/index.sqlite`).
- **CLI context** (`click.Context.obj`) holds only ephemeral config: `index_path`, `config_path`, `verbose`.
- **Embedding model cache** lives in `EmbeddingManager._model` (loaded on demand, unloaded explicitly).
- **Database connection** is lazily initialized and reused per `Database` instance.

## Scaling Considerations

DocSift is a **local single-user tool**, so "scaling" means handling larger personal document collections, not more concurrent users.

| Collection Size | Architecture Adjustments |
|-----------------|--------------------------|
| 0-10k docs | Current architecture is fine. SQLite with FTS5 handles this easily. |
| 10k-100k docs | Add batching to indexing; consider WAL mode for SQLite; embedding cache becomes critical. |
| 100k+ docs | SQLite may become the bottleneck for vector search; consider HNSW index (via `sqlite-vec` or migrate to `faiss` for vector search while keeping SQLite for metadata). |

### Scaling Priorities

1. **First bottleneck: embedding generation.** Indexing 10k+ documents with a local model is slow. Mitigate with:
   - Larger batch sizes in `EmbeddingManager.embed()`
   - GPU offloading (`n_gpu_layers` for llama-cpp)
   - Skip unchanged files via checksums (already implemented)

2. **Second bottleneck: fallback vector search.** The fallback in `VectorSearcher._search_fallback()` loads *all* embeddings into Python for cosine similarity. This is O(N) per query and will break at ~50k documents. Mitigate by:
   - Ensuring `sqlite-vec` extension is available (uses native vector indexing)
   - Or adding an optional `faiss` index for large collections

## Anti-Patterns

### Anti-Pattern 1: Leaking SQL into Business Logic

**What people do:** Write raw SQL in CLI commands or searchers.
**Why it's wrong:** Schema changes ripple through the entire codebase; testing requires a real database.
**Do this instead:** Route all SQL through repository classes. Searchers should only use repositories or dedicated query objects.

### Anti-Pattern 2: Tight Coupling Between MCP and CLI

**What people do:** Implement tool logic inside the MCP server and duplicate it in CLI commands.
**Why it's wrong:** Every feature must be implemented twice; drift between CLI and MCP behavior.
**Do this instead:** Extract a service layer (e.g., `SearchService`, `IndexService`) that both CLI and MCP call. The MCP server should be a thin adapter.

### Anti-Pattern 3: Loading the Embedding Model on Every Request

**What people do:** Instantiate `EmbeddingManager` and call `load_model()` inside every search command.
**Why it's wrong:** Local models (especially GGUF) take seconds to load. This makes search unbearably slow.
**Do this instead:** Keep `EmbeddingManager` alive for the duration of the CLI command or MCP session. Cache the loaded model in memory. Unload only when memory pressure requires it.

### Anti-Pattern 4: Dual MCP Codebases

**What people do:** Maintain `mcp/` (legacy functional) and `mcp_server/` (refactored OOP) in parallel.
**Why it's wrong:** Bug fixes and new tools must be added twice. The legacy server lacks abstractions; the refactored server lacks working tools.
**Do this instead:** Migrate all working tool logic from `mcp/` into `mcp_server/` (or a unified `mcp/` package), then delete the legacy code. The refactored transport and handler abstractions are the right foundation.

### Anti-Pattern 5: Chunking Without Context Overlap

**What people do:** Split documents into fixed-size chunks with hard boundaries.
**Why it's wrong:** Sentences or concepts spanning chunk boundaries get lost; vector search retrieves incomplete context.
**Do this instead:** Use overlapping windows (e.g., 20% overlap) or semantic chunking (split on headers/paragraphs). The `Chunker` ABC should support an `overlap` parameter.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Local GGUF models | llama-cpp-python via `EmbeddingModel` subclass | Requires model download; supports GPU offloading |
| sentence-transformers | Python package via `EmbeddingModel` subclass | Easiest local embedding path; no C++ compile needed |
| OpenAI-compatible API | HTTP client via `EmbeddingModel` subclass | Optional; requires API key; adds latency |
| MCP clients | JSON-RPC 2.0 over stdio or HTTP | Must conform to MCP spec; stdio is primary for Claude Desktop |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| CLI ↔ Search | Direct instantiation of `SearchPipeline` | Could be improved with a `SearchService` facade |
| MCP ↔ Search | Direct instantiation inside tool handlers | Same issue; needs service extraction |
| Search ↔ Database | `sqlite3.Connection` passed to searchers | Acceptable for performance, but repositories preferred for writes |
| Indexing ↔ Embedding | `EmbeddingManager.embed()` call | Clean boundary; manager handles batching and caching |
| Indexing ↔ Database | `DocumentRepository` | Good boundary; no SQL in indexer |

## Suggested Build Order for Missing Pieces

Based on dependency analysis, build the remaining features in this order:

### 1. Fix Existing Stubs and Bugs
**Rationale:** The foundation must be solid before adding features.
- Fix hardcoded model paths in `EmbeddingConfig` / `Settings`
- Replace random embedding fallbacks in `factory.py` with real `sentence-transformers` and `llama-cpp-python` implementations
- Fix `Document` model checksum double-computation (`indexer.py` computes SHA256 from bytes, then `Document.__post_init__` recomputes from content string)

### 2. Complete CLI Commands
**Rationale:** CLI is the primary user interface; missing commands block feature parity with qmd.
- `multi-get`, `ls`, `update-cmd`, `pull`, `bench`
- These are mostly database queries + formatting; low architectural risk

### 3. Implement Query Expansion and Reranking
**Rationale:** These depend on a working embedding/LLM layer (step 1) and integrate into `SearchPipeline`.
- `QueryExpander` protocol implementation (can use lightweight local model or rule-based expansion)
- `Reranker` protocol implementation (cross-encoder or LLM-based reranking)
- Wire both into `SearchPipeline`
- Update `query` command to use `SearchPipeline` instead of bare `HybridSearcher`

### 4. Unify MCP Server
**Rationale:** MCP depends on all other features being stable. Unifying last avoids refactoring twice.
- Port all working legacy tool handlers (`query`, `lex_search`, `vec_search`, `get`, `multi_get`, `status`) into the refactored `mcp_server/` handler framework
- Wire `ToolHandler` instances into `MCPServer`
- Update CLI `mcp` commands to use the refactored server
- Delete legacy `mcp/` code

### Dependency Graph

```
Config/Settings ─┬─► Embedding Layer (fix stubs) ─┬─► Query Expansion
                 │                                 ├─► Reranker
                 │                                 └─► SearchPipeline
                 │
                 ├─► Database/Repository (stable) ─┬─► CLI commands
                 │                                 └─► MCP tools
                 │
                 └─► Indexing Pipeline (stable) ───► Search Layer
```

## Sources

- DocSift codebase analysis (`src/docsift/`), 2026-04-14
- Original qmd project context (TypeScript/Bun local search engine)
- SQLite FTS5 and sqlite-vec documentation patterns
- Model Context Protocol specification (JSON-RPC 2.0, stdio/HTTP transports)

---
*Architecture research for: DocSift local document search system*
*Researched: 2026-04-14*
