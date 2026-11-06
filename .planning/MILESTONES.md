# Milestones

## v1.0 MVP — qmd 功能对等的本地混合搜索引擎 (Shipped: 2026-11-07)

**Phases completed:** 11 phases, 68 plans, 112 tasks

**Key accomplishments:**
- Added all missing runtime dependencies to pyproject.toml so `pip install -e .` succeeds and the CLI launches without ModuleNotFoundError.
- Converted FTS5 virtual tables to external content tables with SQLite triggers, removed stale sqlite_repository.py, and fixed BM5 rowid joins.
- Fixed inverted checksum logic in index update and removed hardcoded embedding model paths, aligning CLI and embedder defaults with Settings
- Replaced random/placeholder embedding implementations in the factory with real `sentence-transformers` and `llama-cpp-python` loaders, and unified the `ModelType` enum across modules.
- Made sqlite-vec a hard requirement for vector search, removed all Python brute-force fallbacks, and rewrote the vsearch CLI to fail fast with clear errors.
- Implemented `multi-get` command with auto-detection for comma-separated IDs, glob patterns, and single docid/path fallback, plus full unit test coverage.
- Top-level `docsift ls` command displaying indexed documents as a virtual file tree, with optional collection and subpath filtering
- Collection update-cmd, include/exclude subcommands, and pre-index shell hook with fail-fast subprocess execution
- Wired `--all` flag into `search`, `query`, and `vsearch` CLI commands so default searches respect `include_by_default` collection setting.
- Implemented OpenAIEmbedder with dimension auto-detection, added MODELSCOPE to ModelType, refactored the factory to return Embedder protocol instances, and created unit tests for all backends.
- Refactored EmbeddingManager to work with the Embedder protocol and added comprehensive unit tests.
- OpenAIEmbedder(Embedder) with generic OpenAI-compatible endpoint support (api_base → {api_base}/embeddings), per-model dimension auto-detection cached to openai_dim_cache.json with a 7-day TTL and fail-fast SIF_EMBEDDING_DIM mismatch validation, wired through EmbeddingModelFactory — closing the single 03-VERIFICATION VEC-01 gap and delivering both missing Wave-0 test files.
- Idempotent `sif index embed`: delete-before-insert replaces a re-chunked document's vec0 rows, and a per-document exact-set check skips complete documents unless `--force` — closing UAT gap G-03-3 where 7 runs on a 3-chunk collection left 21 searchable embedding rows returning the document 7 times.
- Complete
- QueryExpansion with embedding-based pseudo-relevance feedback returning list[str], and SmartSnippetExtractor scoring sentences by weighted query term frequency.
- Snippet column in query/search CLI tables fed by transient content fetch and prefix-route snippet coverage.
- Unified contexts table with SAVEPOINT atomic migration, ContextRepository with context_type filtering, and SearchResult.context_description field preserved through RRF fusion and cross-encoder reranking
- Attach path context descriptions to all search results via batch query across BM25, vector, hybrid, and pipeline searchers.
- Shared `_collapse_duplicate_path_rows` helper collapses every same-file spelling into one canonical row on ALL re-add paths (truth 21), and `context list` escapes all Rich table cells so markup-bearing content renders literally (CR-02).
- escape() on every user-derived string crossing Rich in the search/vsearch/query tables and both explain prints — markup-bearing queries, titles, collection names, and content render literally instead of crashing with rich.errors.MarkupError
- Bracket-named context targets are now addable — rich.markup.escape at the three confirmation prints (add create, add update, remove) stops the MarkupError that rolled back writes inside the transaction, locked by three machine-validated RED-first regression tests.
- Auto-generated CLI reference via Click introspection, replacing stale manual documentation with accurate command/argument/option tables for all 32 commands.
- Auto-generated configuration reference from Pydantic Settings introspection, eliminating 6 phantom fields and documenting 25 real settings with Qwen3 defaults.
- Complete rewrite of docs/quickstart.md to match current CLI signatures, replacing all broken examples (collection create, add-path, update, search similar, mcp start) with working commands verified against installed package
- Updated README.md and docs/index.md to reflect current v1.0 features, Qwen3 default models, and correct CLI examples while removing "planned" labels from already-implemented features.
- Updated four technical docs and created an architecture diagram generator to reflect current implementation after Phases 1-5
- Renamed Python package directory from `src/docsift/` to `src/sif/` and updated all `pyproject.toml` metadata, scripts, URLs, and tool configs.
- SIF branding applied to all core constants, package metadata, and CLI entry point with automatic model cache migration from old docsift paths
- Bulk mechanical rename of all internal imports and string references from `docsift` to `sif` across 54 source files, with zero remaining `from docsift` imports and full compile/import verification.
- Updated Pydantic Settings env_prefix from "DOCSIFT_" to "SIF_", changed default DB path to "sif.db", and verified all filesystem paths resolve under sif/ directories.
- All 31 test files migrated from `docsift` to `sif` imports, patch targets, and command references with pytest collecting 388 tests successfully
- Full quality suite verification of DocSift-to-SIF rename with 377 tests passing, zero rename-related errors, and consistent SIF branding.
- Deleted the D-01 dead-code cluster and re-baselined coverage from 78% to 81.48% (5320 statements, 985 missed), with 690 tests passing and live CLI imports intact.
- Raised full-suite line coverage from 81.48% to 85.34% with real-SQLite CLI tests: collection 99.15%, main 86.99%, get 100%, and all D-06 order probes green.
- Raised full-suite line coverage from 85.34% to 88.57% with deterministic reranker tests and 64 search CLI tests; rerank.py reached 98.60%, search.py 99.44%, and XML now safely escapes machine output.
- Raised full-suite coverage from 88.57% to 90.89% with real-SQLite database/cache tests; repositories, database, schema, and cache reached 100%, migrations reached 92%, and real SQL exposed and proved fixes for stale FTS rows, lazy stats initialization, and broken migration scripts.
- Raised full-suite coverage from 90.89% to 93.48% with 78 new behavior tests; all seven target files reached 100%, ModelScope/network/home boundaries remained isolated, and the tests exposed and proved fixes for custom logging formatter and indeterminate Rich progress defects.
- Raised full-suite coverage from 93.48% to 96.16% with 83 new behavior tests, reached 100% parser/scanner/server/stdio coverage, and fixed chunker non-termination plus MCP session-limit defects exposed by the new edge cases.
- Rehearsed the 90% gate at TOTAL 96.16% with zero long-tail additions and landed `[tool.coverage.report] fail_under = 90` as the single pyproject coverage config change — the canonical suite now exits 0 only when src/sif line coverage stays at or above 90%.
- Symlink-alias paths now resolve to indexed documents across sif get/multi-get and MCP get_document via normalize_path-wrapped lookups, get.py owns its Database lifecycle, and the index-vs-disk fallback boundary is documented in the generated CLI reference.
- Generalized legacy-FTS-trigger detector migrating direct-DELETE triggers to 'delete'-command form with a detection-gated 'rebuild' that purges stale MATCHable entries on the same open
- W3C XML 1.0 Char-production sanitizer stripping forbidden code points from every `--xml`-bound string, plus context-manager Database ownership for search/query/vsearch with closure regression locks
- Context-manager Database ownership at all 21 remaining CLI construction sites (6 modules) plus a TrackingDatabase closure harness asserting success- and exception-path closure

---
