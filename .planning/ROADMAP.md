# DocSift Roadmap

**Granularity:** Standard
**Phases:** 5
**Coverage:** 31/31 v1 requirements mapped

## Phases

- [ ] **Phase 1: Foundation Fix** - Fix bugs, remove stubs, and make the core infrastructure trustworthy
- [ ] **Phase 2: CLI Core Completion** - Complete missing CLI commands for document retrieval and collection management
- [ ] **Phase 3: Embedding & Vector Search** - Enable configurable embedding backends and working semantic search
- [ ] **Phase 4: Advanced Search Pipeline** - Add reranking, query expansion, explainability, and search quality controls
- [ ] **Phase 5: Agent Context Experience** - Allow users to augment collections with contextual descriptions for better retrieval

## Phase Details

### Phase 1: Foundation Fix
**Goal**: Core indexing and search infrastructure is trustworthy and free of critical bugs, stubs, and missing dependencies.
**Depends on**: Nothing (first phase)
**Requirements**: FND-01, FND-02, FND-03, FND-04, FND-05, FND-06, FND-07, FND-08
**Success Criteria** (what must be TRUE):
  1. Project installs cleanly with all runtime dependencies declared in `pyproject.toml`
  2. Document indexing correctly skips unchanged files and updates changed ones based on checksum
  3. Embedding factory loads real `sentence-transformers` and `llama-cpp-python` models instead of stubs or random vectors
  4. Model paths are read from Settings and can be overridden via CLI instead of being hardcoded
  5. FTS5 search results stay synchronized with the main document table
  6. Vector search CLI does not silently fall back to BM25 when the embedder is unavailable
  7. SQLite connections are safe across async and multi-threaded operations
**Plans**: TBD

### Phase 2: CLI Core Completion
**Goal**: Users can manage collections and retrieve documents through a complete, functional CLI.
**Depends on**: Phase 1
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04, CLI-05, CLI-08
**Success Criteria** (what must be TRUE):
  1. User can batch-retrieve documents by glob pattern, comma-separated list, or docid with `multi-get`
  2. User can list indexed documents as a virtual file tree via `ls`
  3. User can set or clear a pre-index shell command per collection with `collection update-cmd`
  4. User can include or exclude collections from default queries with `collection include/exclude`
  5. User can download and verify local GGUF model files with `pull`
  6. Search and retrieval output can display line numbers via `--line-numbers`
**Plans**: TBD

### Phase 3: Embedding & Vector Search
**Goal**: Users can perform semantic vector search with configurable embedding backends.
**Depends on**: Phase 1
**Requirements**: VEC-01, VEC-02, VEC-03, VEC-04
**Success Criteria** (what must be TRUE):
  1. User can configure different embedding backends (sentence-transformers, llama-cpp-python, OpenAI-compatible API) via Settings and CLI
  2. Vector search uses `sqlite-vec` and refuses brute-force Python fallback on large indexes
  3. Document indexing benefits from batch embedding insertion for better performance
  4. User can download embedding models from ModelScope as an alternative to HuggingFace
**Plans**: TBD

### Phase 4: Advanced Search Pipeline
**Goal**: Users can perform high-quality hybrid searches with reranking, query expansion, and diagnostic visibility.
**Depends on**: Phase 2, Phase 3
**Requirements**: SRCH-01, SRCH-02, SRCH-03, SRCH-04, SRCH-05, SRCH-06, SRCH-07, SRCH-08, CLI-06, CLI-07
**Success Criteria** (what must be TRUE):
  1. User can apply LLM reranking to search results for better relevance ranking
  2. User can use query document syntax (`lex:`, `vec:`, `hyde:`, `expand:`) for targeted search modes
  3. User can see score breakdowns across BM25, RRF, and reranker stages with `--explain`
  4. User can filter low-confidence results with `--min-score` and retrieve full document content with `--full`
  5. User can control how many candidates enter the reranker with `--candidate-limit`
  6. User can pass intent hints through `--intent` to guide search behavior
  7. Search results show the most relevant snippet extracted from each chunk
  8. User can run benchmark fixtures to measure precision@k, recall, and MRR
**Plans**: TBD

### Phase 5: Agent Context Experience
**Goal**: Users can augment document collections with contextual descriptions to improve retrieval quality for agent workflows.
**Depends on**: Phase 4
**Requirements**: CTX-01, CTX-02, CTX-03
**Success Criteria** (what must be TRUE):
  1. User can add contextual descriptions to paths or collections via `context add`
  2. User can list and remove contextual descriptions via `context list` and `context rm`
  3. Search results include relevant contextual descriptions alongside document content
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation Fix | 0/TBD | Not started | - |
| 2. CLI Core Completion | 0/TBD | Not started | - |
| 3. Embedding & Vector Search | 0/TBD | Not started | - |
| 4. Advanced Search Pipeline | 0/TBD | Not started | - |
| 5. Agent Context Experience | 0/TBD | Not started | - |
