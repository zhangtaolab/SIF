# Milestones

## v1.1 Live Index and Search Quality (Shipped: 2026-11-12)

**Phases completed:** 7 phases, 27 plans, 67 tasks

**Key accomplishments:**
- One shared SQLite connection factory (busy_timeout→WAL→synchronous + implicit BEGIN IMMEDIATE) for both CLI and MCP paths, plus kernel-flock per-DB single-writer arbitration proven end-to-end with deterministic two-writer subprocess tests
- Per-file incremental indexing core (IncrementalIndexer) extracted from update_cmd into one shared presentation-free loop with per-file BEGIN IMMEDIATE transactions (D-04), proven golden-equivalent on index state and CLI output (SC3)
- Dead third copy of the indexing loop retired (DocumentIndexer module + ConnectionPool + duplicate DatabaseConnection, D-07) and embed_cmd brought under the same per-DB flock as update_cmd (D-01), closing the phase with the full quality gate green (SC4)
- End-to-end `sif watch` slice: observer -> EventDebouncer -> fold -> worker -> per-burst flock -> update_paths, proven by a real-subprocess e2e test plus the shared-predicate, missing-root-guard, and watchdog-cap landings
- Complete foreground host around the 12-01 pipeline: tiered --embed depth with embedding computed outside any write transaction, signal-driven shutdown with WAL truncate checkpoint, repeatable -c filtering, and missing-root recovery — all unit-proven with machine-verified TDD gates
- Real-FS e2e battery proving every Phase 12 SC against the real CLI subprocess (edit/delete, os.replace atomic save, temp-noise exclusion, missing-root recovery, SIGINT/SIGTERM exit 0 with a demonstrated 0-byte WAL), plus generator-only docs regeneration that turns the full quality gate green with nothing deselected
- FileWatcher grown into the long-lived-host substrate: live rescope of the watched collection set (exact-set diff, reconcile-on-add, documents preserved on removal), idle PRAGMA wal_checkpoint(TRUNCATE) riding the tick with busy/recent-burst skips, and ENOSPC schedule failures that warn once with the inotify remedy — plus the mcp_watch/rescope/checkpoint settings fields.
- `sif watch --detach` backgrounds the proven Phase 12 host through a stdlib double-fork with a deterministic pipe handshake (PID reported only once armed), `--stop` corroborates identity via ps argv markers before SIGTERM→bounded-wait→SIGKILL escalation, and `sif status` gains a Watch row — with the SC4 SIGKILL/re-detach proof that kernel-released flock leaves no stale lock.
- The proven FileWatcher now lives inside the MCP server under SIF_MCP_WATCH=1 — one shared watch host (BM25-only depth, logger-only output, serve-first queued reconcile, rescope) wired around the stdio serve loop and into the HTTP transport via a FastAPI lifespan, proven by a real stdio subprocess e2e that answers queries while indexing a live burst with a 100% JSON-clean stdout.
- `sif watch --install-service/--uninstall-service` generates a launchd LaunchAgent or systemd user unit that runs the FOREGROUND watcher under the OS supervisor with the install-time `-c/--embed` flags baked into an absolute-interpreter argv (SC3, never forks), installs it with explicit-argv manager calls (bootstrap/bootout-retry or daemon-reload/enable --now, verified, friendly missing-binary errors), and the generator-owned docs are regenerated to tell the whole LIVE-09 story — with a real launchd round-trip proven live twice on this machine.
- Stat-walk drift detection (mtime vs documents) + capped BM25-only refresh in the search trio's command layer — `sif search` now finds post-index edits with no watch running, and a clean index pays zero writes, zero locks, zero notices.
- Derived vector-staleness marking on every search surface: a corrected "no embeddings" D-08 signal computed in the shared searcher enrichment path, forwarded through MCP metadata, plus a `sif status` Vector lag row — zero schema change, zero new dependencies.
- The staleness marker renders on all five CLI output surfaces — dim `(stale vectors)` table annotation (no new column), CSV `vectors_stale` column, Markdown annotation, XML boolean attribute, JSON via `to_dict()` — plus the one-line stderr `sif index embed` remedy hint, so no format silently drops the signal (D-12/D-13, SC3).
- Weighted RRF fusion (weights/k in multiply form, byte-identical at defaults) plumbed end-to-end: `sif query` flags, SIF_ settings, and MCP query params all resolve into SearchOptions and reach RRFFusion.fuse — with golden tests pinning repr-exact default output on a real-DB fixture.
- FTS5 vocab shadow + SuggestionEngine (prefix completions, per-word DYM rewrites with an SC2 pin, frequency×recency history) + capped aware-UTC query_log storage — the one engine three hosts wire in 15-03.
- `sif suggest`'s three-section table/JSON surface, zero-result did-you-mean across all three CLI searches and the MCP query tool (stdout-pure, conditional JSON object), and fail-soft query-history writes with opt-out and a single clear path — phase gate green at 94.85% coverage.
- nDCG@10/Hit@10 with per-category breakdown, warmed p50/p95 latency, and a settings-resolved baseline layered onto `SearchEvaluator`/`sif bench` — legacy flat metrics byte-compatible
- SIF_RERANK_ENABLED (default false) + --rerank make rerank explicit; SIF_RERANK_CANDIDATE_LIMIT (5-50) and SIF_RERANK_RELATIVE_THRESHOLD ((0,1]) are Pydantic-validated; the shipped -C flag resolves through the shared `resolve_candidate_limit` clamp
- Deterministic ConceptEmbedder + direct-DB builder, and a committed 150-doc synthetic corpus with 56 graded queries (36 tuning / 20 held-out) regenerated byte-identically by a seeded drift-gated generator — proven retrievable and CLI-joined with non-zero nDCG@10
- 45-config declared-grid sweep with the rounded-delta 0.01 tie rule (tuning-only, embedding-once, settings baseline with exact-zero deltas) plus bench rerank off/on states strictly additive to the pinned flat --json contract
- Shipped defaults locked to a committed held-out snapshot (nDCG@10 0.8120 reproducing exactly, sweep winner's +0.0066 delta honestly below the 0.01 bar -> verdict "unchanged") with the full measurement system documented in docs-validated docs/benchmarking.md
- Class-injected `open_initialized_database` boundary converts foreseeable DB failures to remedy-bearing Click errors end-to-end on index update/embed, plus constructor-only sqlite-vec guards on vsearch/query and suggest opener adoption — 7 of 30 convention sites, tracer-proven before Plan 02's sweep.
- All 30 CLI DB open/schema sites now route through the Plan 01 shared boundary — 23 converted here (collection/context/get/ls/bench/watch/main), the daemon arm() site via the unmanaged variant, status/cleanup handlers narrowed to D-04 known classes with pure stdout, and an AST inventory gate that structurally forbids future direct init_schema in CLI code.
- LLM cache get() now compares parsed aware-UTC instants through one shared expiry parser (legacy naive-local rows read correctly east AND west of UTC), and every embedding-cache connection comes from the Phase 11 factory — 14-WR-03 read side and W-1 closed with zero migration and byte-identical fail-soft fallbacks.
- FileWatcher.enqueue_reconcile(collections: Iterable[Collection]) — narrow public reconcile-intent API replacing the MCP host's private-queue reach-in, with all three reconcile producers routed and serve-first ordering pinned at unit and protocol level
- Closed 11-WR-03 and 14-WR-02/03/04 with plan-and-test Source evidence, preserved 15-IN-06 as an explicit partial closure, and re-proved the entire phase with 1586 passing tests, 95.17% coverage, clean static gates, and byte-identical generated docs.

---

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
