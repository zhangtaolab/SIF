# DocSift Roadmap

**Granularity:** Standard
**Phases:** 8
**Coverage:** 31/31 v1 requirements mapped

## Phases

- [x] **Phase 1: Foundation Fix** - Fix bugs, remove stubs, and make the core infrastructure trustworthy
- [x] **Phase 2: CLI Core Completion** - Complete missing CLI commands for document retrieval and collection management
- [x] **Phase 3: Embedding & Vector Search** - Enable configurable embedding backends and working semantic search
- [x] **Phase 4: Advanced Search Pipeline** - Add reranking, query expansion, explainability, and search quality controls
- [x] **Phase 5: Agent Context Experience** - Allow users to augment collections with contextual descriptions for better retrieval
- [x] **Phase 6: Documentation Audit & Refresh** - Ensure all docs accurately reflect CLI, API, and config; establish docs testing infrastructure
- [x] **Phase 7: CLI Claude Skill** - Generate Claude skills for all CLI commands

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
**Plans:** 6 plans


Plans:
- [x] 01-01-PLAN.md — Fix missing runtime dependencies in pyproject.toml
- [x] 01-02-PLAN.md — Fix FTS5 synchronization and consolidate repository files
- [x] 01-03-PLAN.md — Fix inverted checksum comparison and remove hardcoded model path
- [x] 01-04-PLAN.md — Replace placeholder embeddings with real ST and GGUF implementations
- [x] 01-05-PLAN.md — Remove vector search fallback and make vsearch fail fast
- [x] 01-06-PLAN.md — Improve SQLite connection safety for async/multi-threaded contexts

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
**Plans:** 6/6 plans executed

Plans:
- [x] 02-01-PLAN.md — Implement multi-get batch document retrieval (CLI-01)
- [x] 02-02-PLAN.md — Implement ls virtual file tree for indexed documents (CLI-02)
- [x] 02-03-PLAN.md — Add collection update-cmd, include/exclude, and wire --all in search (CLI-03, CLI-04)
- [x] 02-04-PLAN.md — Implement pull for downloading GGUF model files (CLI-05)
- [x] 02-05-PLAN.md — Add --line-numbers to get, multi-get, search, query, and vsearch (CLI-08)
- [x] 02-06-PLAN.md — Add collection enable/disable commands

### Phase 3: Embedding & Vector Search
**Goal**: Users can perform semantic vector search with configurable embedding backends.
**Depends on**: Phase 1
**Requirements**: VEC-01, VEC-02, VEC-03, VEC-04
**Success Criteria** (what must be TRUE):
  1. User can configure different embedding backends (sentence-transformers, llama-cpp-python, OpenAI-compatible API) via Settings and CLI
  2. Vector search uses `sqlite-vec` and refuses brute-force Python fallback on large indexes
  3. Document indexing benefits from batch embedding insertion for better performance
  4. User can download embedding models from ModelScope as an alternative to HuggingFace
**Plans:** 6/6 plans executed

Plans:
- [x] 03-01-PLAN.md — Add Settings fields for embedding backends and create unit tests (VEC-01)
- [x] 03-02-PLAN.md — Implement OpenAIEmbedder, wire ModelScope, refactor factory to Embedder protocol (VEC-01, VEC-04)
- [x] 03-03-PLAN.md — Make SchemaManager dimension-aware with fail-fast mismatch detection (VEC-02)
- [x] 03-04-PLAN.md — Add batch embedding insertion to VectorSearcher and create tests (VEC-02, VEC-03)
- [x] 03-05-PLAN.md — Refactor EmbeddingManager to use Embedder protocol and create tests (VEC-01, VEC-03)
- [x] 03-06-PLAN.md — Integrate EmbeddingManager into CLI search/index commands and fix indexer (VEC-01, VEC-02, VEC-03)

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
**Plans:** 5 plans

Plans:
- [x] 04-01-PLAN.md — Extend core models, add reranker settings, implement CrossEncoderReranker, fix RRF score preservation (SRCH-01, SRCH-04, SRCH-05)
- [x] 04-02-PLAN.md — Implement QueryExpansion with embedding-based PRF and SmartSnippetExtractor (SRCH-02, SRCH-07)
- [x] 04-03-PLAN.md — Wire SearchPipeline with prefix routing, explainability, candidate capping; update CLI commands (SRCH-03, SRCH-04, SRCH-05, SRCH-06, CLI-06, CLI-07)
- [x] 04-04-PLAN.md — Implement bench command with SearchEvaluator and benchmark metrics (SRCH-08)
- [x] 04-05-PLAN.md — Fix broken tests and run full quality suite

### Phase 5: Agent Context Experience
**Goal**: Users can augment document collections with contextual descriptions to improve retrieval quality for agent workflows.
**Depends on**: Phase 4
**Requirements**: CTX-01, CTX-02, CTX-03
**Success Criteria** (what must be TRUE):
  1. User can add contextual descriptions to paths or collections via `context add`
  2. User can list and remove contextual descriptions via `context list` and `context rm`
  3. Search results include relevant contextual descriptions alongside document content
**Plans:** 7 plans (4 original + 3 gap closure)

Plans:
- [x] 05-01-PLAN.md — Migrate path_contexts to unified contexts table, rename repository, add SearchResult field (CTX-01)
- [x] 05-02-PLAN.md — Implement context CLI: add (all types), list --type, remove/rm alias, prune (CTX-01, CTX-02)
- [x] 05-03-PLAN.md — Attach path context descriptions to BM25, vector, and hybrid search results (CTX-03)
- [x] 05-04-PLAN.md — Write unit tests for migration, repository, CLI, and search integration
- [ ] 05-05-PLAN.md — Fix context_type storage and display (Gaps 1, 2, 3, 6)
- [ ] 05-06-PLAN.md — Fix path normalization in search context attachment (Gap 4)
- [ ] 05-07-PLAN.md — Fix status command DB path to respect DOCSIFT_DB_PATH (Gap 5)

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation Fix | 6/6 | Complete | 2026-04-14 |
| 2. CLI Core Completion | 6/6 | Complete | 2026-04-15 |
| 3. Embedding & Vector Search | 6/6 | Complete | 2026-04-16 |
| 4. Advanced Search Pipeline | 5/5 | Complete | 2026-04-17 |
| 5. Agent Context Experience | 7/7 | Complete | 2026-04-18 |
| 6. Documentation Audit & Refresh | 7/7 | Complete | 2026-04-18 |
| 7. CLI Claude Skill | 2/2 | Complete | 2026-04-20 |
| 8. Project rename from DocSift to SIF | 2/8 | In Progress | — |

### Phase 6: Documentation Audit & Refresh

**Goal**: All project documentation accurately reflects the current CLI commands, API, and configuration. Every code example in docs is syntax-checked or executed and verified to work.
**Depends on**: Phase 5
**Requirements**: DOC-01, DOC-02, DOC-03, DOC-04, DOC-05, DOC-06, DOC-07
**Success Criteria** (what must be TRUE):
  1. `docs/cli-reference.md` accurately describes every current Click command, subcommand, argument, and option
  2. `docs/configuration.md` documents every `Settings` field with correct default value
  3. Every shell command example in `docs/quickstart.md` executes successfully
  4. `README.md` reflects current features, default models, and realistic roadmap
  5. Technical docs (`mcp-server.md`, `search-algorithms.md`, `architecture.md`, `models.md`) are up-to-date
  6. All code examples in docs are executed or syntax-checked
  7. Docs test infrastructure exists (`tests/test_docs.py`, `make docs-test`, GitHub Actions CI)
**Plans:** 7 plans

Plans:
- [x] 06-01-PLAN.md — Auto-generate CLI reference from Click --help
- [x] 06-02-PLAN.md — Introspect Settings class and validate configuration.md
- [x] 06-03-PLAN.md — Execute and validate quickstart.md code examples
- [x] 06-04-PLAN.md — Review and fix README.md accuracy
- [x] 06-05-PLAN.md — Review technical docs for discrepancies
- [x] 06-06-PLAN.md — Create docs code block validator with pytest
- [x] 06-07-PLAN.md — Add Makefile target and GitHub Actions CI workflow

### Phase 7: CLI Claude Skill

**Goal**: Claude skills for all CLI commands are created and functional.
**Depends on**: Phase 6
**Requirements**: TBD
**Success Criteria** (what must be TRUE):
  1. `docsift-search` skill allows Claude to search the user's document index
  2. `docsift-get` skill allows Claude to retrieve document content by path or pattern
**Plans:** 2 plans

Plans:
- [x] 07-01-PLAN.md — Create docsift-search skill for search commands
- [x] 07-02-PLAN.md — Create docsift-get skill for document retrieval

### Phase 8: Project rename from DocSift to SIF

**Goal**: The entire Python project is renamed from `DocSift`/`docsift` to `SIF`/`sif`, including package name, CLI command, environment variables, config paths, documentation, tests, and Claude Skills. The rename is a complete break with no backward compatibility.
**Depends on**: Phase 7
**Requirements**: TBD
**Success Criteria** (what must be TRUE):
  1. Python package directory is `src/sif/` (not `src/docsift/`)
  2. CLI command is `sif` (not `docsift`)
  3. Environment variable prefix is `SIF_` (not `DOCSIFT_`)
  4. Data paths use `~/.local/share/sif/` (not `~/.local/share/docsift/`)
  5. All documentation uses SIF branding and sif CLI examples
  6. All tests import from `sif` and patch `sif.` module paths
  7. Claude Skills are renamed to `sif-search` and `sif-get`
  8. pyproject.toml uses `sif` for package name, scripts, and tool configs
  9. Model cache auto-migrates from old docsift path on first CLI run
  10. Full test suite passes after rename
**Plans:** 8 plans

Plans:
- [x] 08-01-PLAN.md — Rename src/docsift/ to src/sif/ and update pyproject.toml
- [x] 08-02-PLAN.md — Update constants.py, metadata files, and add model cache migration to CLI
- [ ] 08-03-PLAN.md — Update all Python imports in src/sif/ from docsift to sif
- [ ] 08-04-PLAN.md — Update settings.py env_prefix to SIF_ and verify paths
- [ ] 08-05-PLAN.md — Update all test imports, patch targets, and rename test_docsift_complete.py
- [ ] 08-06-PLAN.md — Update README.md, CLAUDE.md, docs/, and mkdocs.yml
- [ ] 08-07-PLAN.md — Rename Claude Skills and update skill files
- [ ] 08-08-PLAN.md — Run full quality suite: pytest, ruff, mypy, CLI verification, grep audit
