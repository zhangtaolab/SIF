# Architecture Research: SIF v1.2 Search Precision + Agent Experience Integration

**Domain:** Local hybrid search engine (existing layered Python 3.10+ app, CLI + MCP over SQLite/FTS5/sqlite-vec)
**Researched:** 2026-11-13
**Verified at:** HEAD `1aff2c9` (src/ byte-identical to `95c136c` where prior findings were recorded — `git diff --stat 95c136c..HEAD -- src/` empty)
**Confidence:** HIGH for all integration mapping (read directly from `src/sif/` this session); external MCP SDK v2 / sqlite-vec facts are official-primary-source but seam-tiered LOW (provider `webfetch`) — qualified inline and flagged for local verification before planning commitments.

**Scope:** Subsequent milestone — only how the v1.2 features integrate with the existing architecture. Not a greenfield survey. Locked decisions respected: PDF/HTML/EPUB OUT; Windows smoke only; Harrier switch gated on EN+ZH held-out; spellfix1/semantic-chunking/late-chunking/ANN SKIP; local-first MIT single-user.

---

## Prior-Findings Verification Ledger

Every claim in `<prior_findings_to_verify>` was re-checked against current HEAD. Result: **all confirmed**, with line-number corrections and several material additions the prior pass missed.

### Confirmed (corrected line numbers where drifted)

| Claim | Verified location |
|-------|-------------------|
| `create_parser` has ZERO production callers (tests only) | `indexing/parser.py:185-203`; grep: only `tests/unit/indexing/test_parser.py` imports it |
| IncrementalIndexer hardcodes MarkdownParser | `indexing/incremental.py:77` (`self._parser = MarkdownParser()`), used at `:287` |
| Checksum is body-only for Markdown | `indexing/parser.py:66-71` (comment + `sha256(body)`); TextParser/CodeParser hash whole content (`:106`, `:173`) |
| MCP SearchPipeline built WITHOUT expander/reranker/snippet | `mcp/backend.py:163-168` |
| CLI query_cmd wires all three | `cli/commands/search.py:947` (expander), `:949-966` (reranker gate), `:968` (snippet), `:977-985` (pipeline) |
| Eager embedder load in SearchBackend.__init__ | `mcp/backend.py:93-109` (factory.create_model in try/except) |
| Staleness scans ALL document_embeddings per search | `search/staleness.py:34-49` (`embedded_document_ids`), called from `bm25.py:147-149`, `vector.py:133-135`, `hybrid.py:121-123` |
| Context attachment scans whole contexts table | `search/context_attach.py:53-56` (constant SQL, `context_type='path'`, Python-side normalization) |
| Production SearchOptions = limit/offset/collection_ids/min_score + fusion knobs | `core/models.py:272-294` (also include_content/highlights/explain/candidate_limit/intent/snippet_max_length) |
| Dead parallel search layer | `models/search.py:54` (`filters` dict on **SearchQuery**, not SearchOptions), `search/strategy.py:23` (`SearchContext.filters`); importers are only `tests/conftest.py`, `tests/factories.py`, `tests/unit/test_search.py` + the `models/__init__.py` re-export |
| documents.mtime REAL + metadata TEXT JSON stored | `database/schema.py:70` (`mtime REAL NOT NULL`), `:73` (`metadata TEXT DEFAULT '{}'`) |
| idx_documents_path exists; NO mtime index | `schema.py:394-397`; `_create_indexes` (`:387-419`) has collection/path/checksum/chunks/contexts/llm_cache only |
| documents_fts indexes content only, porter | `schema.py:244-251` |
| VectorSearcher appends every KNN chunk row, no per-doc dedup | `search/vector.py:104-123` (loop), `:127` (trim to limit) |
| Hybrid dedups AFTER RRF truncation | `search/hybrid.py:77-82` (fuse at `options.limit`), `:97` (`_deduplicate_results`), `:101-119` |
| offset only sizes over-fetch, never slices (hybrid) | `hybrid.py:238` (`max(options.limit + options.offset, options.candidate_limit)`); no slice anywhere in hybrid/vector |
| DYM seam = difflib over first-letter±1 bucket, cutoff 0.75 | `search/suggest.py:250-269` (`_close_matches`), `:272-274` (`_ratio`); measured ~11ms/word bucketed vs ~46ms full-vocab (docstring) |
| Extension loading exists | `database/factory.py:119-133` (`_load_sqlite_vec`; `enable_load_extension` at `:127`) — prior cite `:120` corrected |
| LexSearch*/VecSearch* models defined but unwired | `mcp/protocol.py:265-290`; `mcp/handlers.py:215-222` registers only query/get/multi_get/status |
| Protocol version hardcoded 2024-11-05 | `mcp/server.py:71`, `mcp/protocol.py:99` and `:113` |
| Capabilities tools-only | `mcp/protocol.py:104-107` |
| resources/read serves docs://, no resources/list | `mcp/server.py:94-95`, `:138-177`; no `resources/list` branch in `handle_request` |
| HTTP Origin middleware, 403 non-allowlist; no Host check | `mcp/transports/http.py:181-191` |
| POST always plain JSON; GET SSE pings only; no DELETE; sessions auto-minted | `http.py:118-121` (JSONResponse), `:124-146` (ping generator), no DELETE route, `:57-70` (`_get_session_id` mints without initialize) |
| `sif mcp daemon` stub | `cli/commands/mcp.py:109-129` — raise at `:129` (prior cite 120-133 corrected) |
| No VACUUM/ANALYZE/FTS optimize anywhere in src | grep `vacuum\|analyze\|optimize` over `src/sif/` → zero hits |
| `sif cleanup` only deletes orphans | `cli/main.py:227-267` (orphan chunks + embeddings + expired LLM cache) |
| index embed accumulates ALL chunks before one embed call | `cli/commands/index.py:317` (`all_chunks = []`), `:340-343` (append), `:346-348` (single `manager.embed`), all inside one per-collection txn (`:324`) |
| SentenceTransformerEmbedder.encode passes no prompt_name | `embedding/embedder.py:92-97` (`_encode_kwargs` = normalize + batch_size only); ModelScope twin at `:380-385` |
| ModelDownloader.DEFAULT_MODELS names 7B gte_Qwen2 | `models/download.py:18-33` (embedding AND reranker = `iic/gte_Qwen2-7B-instruct`); ModelScopeEmbedder default also 7B (`embedder.py:313`) |
| md5-named cache-hit check never fires | `models/download.py:69-75`: checks `cache_dir/<md5[:8]>` but `snapshot_download(cache_dir=...)` writes `cache_dir/<model_id>/...` (`:80-95`) — the md5 dir is never created |
| ModelScopeEmbedder picks glob("*")[0] nondeterministically | `embedding/embedder.py:335-340` |
| sif pull is GGUF-only | `cli/commands/pull.py:63-84` (spec `owner/repo/filename.gguf` or URL), docstring `:100` |
| Makefile references bandit/pre-commit/build/twine absent from dev extras | Makefile `security`/`pre-commit`/`build` targets; `pyproject.toml:43-50` dev = pytest/pytest-cov/pytest-asyncio/black/ruff/ty only |
| .pre-commit-config.yaml missing | `ls` → No such file |
| example_config.yaml advertises YAML no code loads | file exists; `config/settings.py:26-31` reads `SIF_` env + `.env` only; no YAML loader in `src/sif/config/` |
| Tracked junk | `git ls-files`: `MagicMock/mock/*` (4 files), `quick_test.py`, `simple_test.py`, `verify_imports.py` |
| CI: only docs.yml | `.github/workflows/` contains `docs.yml` alone |
| Version dynamic via hatch; PyPI stale | `pyproject.toml:81-82` → `src/sif/_version.py` = `1.1.1`; PyPI `docsif` latest = **1.0.1** (uploaded 2026-11-07; releases 0.1.0/0.1.1/0.2.0/1.0.0/1.0.1) — verified via pypi.org/pypi/docsif/json |

### NEW findings the prior pass missed (material to v1.2)

1. **Frontmatter-only edits are invisible to the index — blocks tag/frontmatter filtering.**
   `incremental.py:300-318`: on checksum match the skip path converges **mtime only** and deliberately does NOT touch title/metadata (comment `:308-310`: "a whole-row update could smuggle a new frontmatter title/metadata through this skip"). Since the Markdown checksum covers the **body alone** (`parser.py:71`), editing only YAML frontmatter (tags!) leaves `documents.metadata` stale **forever**. Metadata filtering on tags is untrustworthy until this is fixed. This is a hard dependency of feature 1 on feature 2's parser work.

2. **RRF score inflation from duplicate vector chunks (not just slot consumption).**
   `rrf.py:56-79` accumulates `weight/(k+rank)` **per occurrence** keyed by document_id. A document appearing 3× in the vector list gets 3 rank contributions — its fused score is inflated, skewing ranking vs BM25-only docs. Per-doc dedup must therefore happen **inside VectorSearcher before fusion**, not only after RRF truncation. The post-truncation dedup (`hybrid.py:97`) fixes slots but cannot undo inflation.

3. **Double context/staleness attachment on the hybrid pipeline path (N+1 full scans).**
   `HybridSearcher.search` already returns `self._attach_contexts(...)` (`hybrid.py:70/72/99`); `SearchPipeline.search` then calls `self.hybrid._attach_contexts(results)` **again** at `hybrid.py:271`. With query expansion (N variants) that is N+1 full `document_embeddings` scans + N+1 full `contexts` scans per query. Idempotent (staleness docstring guarantees re-mark safety) but a real per-query full-scan multiplier. The lex/vec pipeline paths attach exactly once (inside the searchers, `bm25.py:145`/`vector.py:131`). "Eliminate per-query full scans" must fix this too.

4. **The embedding cache ALREADY has embedder identity — reuse its key format.**
   `embedding/manager.py:153-163` (`_cache_model_id` = `"{model_type}:{model_name}[@{api_base}]"`) and `embedding/cache.py:69-77` (`PRIMARY KEY (content_hash, model_id)`, with a legacy-table rebuild migration at `:56-67`). The main index DB has no identity, but the exact identity string and the per-model segmentation precedent exist. `EmbeddingManager.embed` already returns `model_id` + `dimensions` in `EmbeddingResponse` (`manager.py:145-151`).

5. **`MigrationManager` is a DEAD parallel schema system — do not wire v1.2 migrations through it.**
   `database/migrations.py:134-233` is instantiated only by `tests/unit/database/test_migrations.py`. Its `SCHEMA_SQL` diverges from production (`chunks` vs `document_chunks`, `chunk_embeddings` vs `document_embeddings`, `schema_version` table, and the **broken legacy direct-UPDATE/DELETE FTS triggers** at `:100-110` that Phase 10.1 hunted). `SchemaManager` (`database/schema.py`) is the real, production migration machinery. Same trap class as the dead `models/search.py` layer.

6. **BM25 applies min_score AFTER SQL LIMIT/OFFSET** (`bm25.py:112-122`) — filtered pages under-return. Vector does it in the correct order (min_score before trim, `vector.py:109-127`). Pagination fixes must reconcile this.

7. **offset is entirely dead plumbing today.** No `--offset` flag on any of the search trio (verified flag lists at `search.py:429-452`, `:602-625`, `:767-832`); no `offset` field in MCP `QueryInput` (`protocol.py:240-252`). Only `SearchOptions.offset` default 0 and the BM25 SQL `OFFSET ?` exist. "Pagination fixes" = build the user surface AND fix hybrid/vector slicing, not just slice.

8. **Three separate vec0 dimension-guard sites** — `schema.py:361-376` (RuntimeError), `cli/commands/index.py:242-253` (ClickException), `indexing/watcher.py:234-238` (embed-leg RuntimeError). Embedder identity should consolidate the guard logic, not add a fourth copy.

9. **MCP builds a fresh SearchPipeline per request** (`backend.py:163` inside `_search`), including a VectorSearcher extension-check query each time. CLI/bench hoist the pipeline (bench `_measure_state` comment: "never per query"). Relevant to lazy-embedder + parity design.

10. **fastapi + uvicorn are CORE dependencies** (`pyproject.toml:36-37`); the `[mcp]`/`[http]` extras only re-add uvicorn (redundant). `mcp` 1.27.0 is already installed in the dev environment (transitive). The SDK-v2 dependency placement is a real decision, not a no-op.

11. **Daemon + service infrastructure already exists** — `utils/daemon.py` (`detach` :216, `stop_daemon` :289, pid helpers :84-151) and `utils/service.py` (launchd/systemd generators), built for `sif watch --detach`. `sif mcp daemon` resolution should reuse these, not build new.

12. **Docs generation gate constrains every new command/setting.** `scripts/generate_cli_ref.py` + `generate_config_ref.py` wholesale-rewrite `docs/cli-reference.md` + `docs/configuration.md`; `tests/test_docs.py` enforces (`test_cli_reference_has_all_commands`, `test_configuration_no_phantom_fields`, `test_shell_commands_exist`, `test_model_names_are_current`). New CLI commands (models/eval/vacuum/metadata/filter flags) and Settings fields MUST run `make docs-generate`. `test_model_names_are_current` interacts with the DEFAULT_MODELS fix.

13. **Model cache location inconsistency:** `pull.py:101-103` defaults to `~/.sif/models`; `cli/main.py:272-278` migrates legacy `~/.local/share/docsift/models` → `~/.local/share/sif/models` (platformdirs). Models UX work must pick one canonical location.

14. **PyPI classifiers stop at 3.12** (`pyproject.toml:16-26`) — the 3.13 CI matrix leg needs a classifier addition.

15. **`BM25Searcher.search_chunks` is dead** (`bm25.py:151-185`, no src callers) — chunk-level FTS exists but is unwired; relevant if chunk-sweep experiments want chunk-level retrieval.

16. **SQLite JSON1 is available** (verified `json_extract` on local python3 sqlite) but **unused in src** (zero `json_each`/`json_extract` hits) — metadata discovery will be the first JSON1 consumer; verify on all CI platforms.

---

## Standard Architecture (Target State for v1.2)

### System Overview

```
┌────────────────────────────────────────────────────────────────────────────┐
│                             Interface Layer                                 │
│  ┌──────────────────────────┐      ┌──────────────────────────────────────┐ │
│  │ CLI (Click)              │      │ MCP — official SDK v2 MCPServer      │ │
│  │  search/vsearch/query    │      │  [REPLACES hand-rolled server.py +   │ │
│  │   + filter flags [NEW]   │      │   protocol.py JSON-RPC + transports/]│ │
│  │   + --offset [NEW]       │      │  @mcp.tool fns wrap SearchBackend    │ │
│  │  metadata [NEW]          │      │   [PRESERVED] + annotations +        │ │
│  │  eval --personal [NEW]   │      │   structuredContent/outputSchema     │ │
│  │  models pull/status[NEW] │      │  lex_search/vec_search [WIRED]       │ │
│  │  index vacuum/backup[NEW]│      │  metadata tool [NEW]                 │ │
│  │  mcp daemon [UN-STUBBED] │      │  stdio + streamable_http_app()       │ │
│  └────────────┬─────────────┘      │  dual-era ≤2025-11-25 / 2026-07-28   │ │
│               │                    │  watch_host lifespan [REWIRed]       │ │
│               │                    └──────────────────┬───────────────────┘ │
│               └───────────────────┬───────────────────┘                     │
├───────────────────────────────────┼─────────────────────────────────────────┤
│                            Application Layer                                │
│  ┌────────────────────────────────┼──────────────────────────────────────┐  │
│  │ FilterAst [NEW core/filters.py]│  SearchPipeline / HybridSearcher      │  │
│  │  → SQL compiler [NEW           │   [MODIFIED: pre-RRF per-doc dedup,   │  │
│  │    search/filters.py]          │    offset slice, single attach]       │  │
│  │  → BM25 WHERE + Vector JOIN    │  BM25Searcher [MODIFIED: filter WHERE,│  │
│  │    (pre-RRF by construction)   │    title column weights, min_score    │  │
│  │ MetadataDiscovery [NEW]        │    order]  VectorSearcher [MODIFIED:  │  │
│  │ PersonalBench [NEW             │    filter JOIN, adaptive fetch_k,     │  │
│  │  search/personal.py]           │    per-doc dedup]                     │  │
│  │  → SearchEvaluator [REUSED]    │  SuggestionEngine [MODIFIED: rapidfuzz│  │
│  │  → QueryLogRepository [REUSED] │    _close_matches]                    │  │
│  │ IncrementalIndexer [MODIFIED:  │  Staleness/ContextAttach [MODIFIED:   │  │
│  │  create_parser dispatch +      │    indexed/bounded reads, no full     │  │
│  │  frontmatter-aware checksum]   │    scans per query]                   │  │
│  └────────────┬───────────────────┴──────────────────┬────────────────────┘  │
├───────────────┼──────────────────────────────────────┼───────────────────────┤
│                          Infrastructure Layer                                │
│  ┌────────────┴──────────────────────────────────────┴────────────────────┐  │
│  │ SchemaManager [MODIFIED: title-FTS detect+rebuild, idx_documents_mtime,│  │
│  │   index_meta table]   EmbedderIdentity [NEW: index_meta guard,         │  │
│  │   consolidates 3 dim-guard sites]                                      │  │
│  │ SQLite: documents(+mtime idx) + documents_fts(title,content) + vec0    │  │
│  │   + index_meta(key,value) [NEW] + contexts + query_log + llm_cache     │  │
│  │ EmbeddingCache [UNCHANGED — already per-model segmented]               │  │
│  │ Maintenance [NEW: VACUUM/ANALYZE/FTS optimize + backup]                │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities — NEW vs MODIFIED vs PRESERVED vs DELETED

| Component | Status | Responsibility | Evidence / notes |
|-----------|--------|----------------|------------------|
| `core/filters.py` (FilterAst dataclasses) | **NEW** | Pure domain value objects: Path/Mtime/Tag/Frontmatter predicates + And/Or/Not; no SQL | Imported by `core/models.py` SearchOptions; keeps core→search layering clean |
| `search/filters.py` (SQL compiler) | **NEW** | `compile_filter(node, alias="d") -> (where_sql, params)` over `documents`; shared by BM25 + Vector | One compiler, two injection points; Python `matches()` evaluator for tests/discovery |
| `core/models.py::SearchOptions` | **MODIFIED** | Add `filters: FilterNode \| None = None`; offset becomes live | `:272-294`; rides `dataclasses.replace` in pipeline over-fetch (`hybrid.py:236-239`) automatically |
| `search/bm25.py` | **MODIFIED** | Append compiled WHERE to BOTH SQL paths; title column weights via `bm25()` aux; min_score/limit/offset ordering | Scoped CTE `:76-93` (filter in OUTER where, never inside the materialized MATCH), unscoped `:98-111` |
| `search/vector.py` | **MODIFIED** | Append compiled WHERE to post-KNN JOIN; adaptive `fetch_k` when filters present; per-doc dedup BEFORE trim | `:87-99` SQL, `:77` fetch_k, `:104-127` loop/trim |
| `search/hybrid.py` | **MODIFIED** | Per-doc dedup pre-fusion (vector side); fuse over `limit+offset`; slice `[offset:offset+limit]` AFTER dedup; remove double `_attach_contexts` | `:77-99`, `:271`; RRF math itself unchanged |
| `search/rrf.py` | **PRESERVED** | Fusion math correct once inputs are per-doc deduped | Do NOT add dedup here — inflation fix belongs upstream |
| `search/staleness.py` / `context_attach.py` | **MODIFIED** | Replace per-query full scans with bounded/indexed reads; single attach per pipeline exit | `staleness.py:34-49`, `context_attach.py:53-56`; see Pattern 6 |
| `search/suggest.py` | **MODIFIED** | rapidfuzz `process.extract` over full vocab replaces difflib+bucket in `_close_matches`/`_ratio` | `:250-274`; bucket removal is the recall fix (first-letter typos) |
| `search/personal.py` + `cli/commands/eval.py` | **NEW** | Known-item fixture synthesis from user corpus + real-query replay from query_log; `sif eval --personal` | Reuses `SearchEvaluator.report` (`benchmark.py:575`) + `BenchHarness` pattern (`bench.py:214-235`) |
| `search/benchmark.py` | **PRESERVED** | Metrics, sweep, held-out gate already complete | `warrants_default_change:394-407` is the Harrier gate |
| `indexing/parser.py` | **MODIFIED** | `create_parser` becomes the production dispatch; frontmatter-aware checksum decision | `:185-203` exists, zero prod callers today |
| `indexing/incremental.py` | **MODIFIED** | Use `create_parser(file_path)` per file; fix frontmatter-only-edit invisibility | `:77`, `:287`, `:300-318` |
| `indexing/watcher.py` | **MODIFIED (minor)** | Embed leg inherits dispatch + identity guard; streaming batches already partly here | lazy `_EmbedState:191-238`, embed outside write txn (`:6-7`) |
| `database/schema.py` | **MODIFIED** | title-FTS detect+rebuild; `idx_documents_mtime`; `index_meta` table | Machinery already exists — see Schema Migration List |
| `database/migrations.py` | **DELETED or quarantined** | Dead parallel schema with broken legacy triggers; tests-only | Never wire v1.2 through it |
| `models/search.py` + `search/strategy.py` | **DELETED or quarantined** | Dead parallel search layer; tests-only | Remove before filter work so nobody wires filters into the dead `filters` dict |
| `embedding/embedder.py` | **MODIFIED** | `prompt_name` support in `_encode_kwargs` (query side); deterministic ModelScope dir resolution | `:92-97`, `:335-340`, `:380-385` |
| `embedding/manager.py` | **PRESERVED (reuse)** | `_cache_model_id` identity string is the index-identity key format | `:153-163` |
| `embedding/identity.py` (or in manager) | **NEW** | Read/write `index_meta` embedder identity; consolidate 3 dim guards; mismatch → fail-fast re-embed remedy | Precedent: `schema.py:361-376` error wording |
| `models/download.py` | **MODIFIED** | DEFAULT_MODELS → Qwen3-0.6B family; fix md5 cache check (use snapshot_download's real layout); deterministic path | `:18-33`, `:69-75` |
| `cli/commands/models.py` | **NEW** | `sif models pull/status` group wrapping fixed downloader + pull; canonical cache dir | Unifies `pull.py` + `download.py`; docs-gate applies |
| `cli/commands/index.py` | **MODIFIED** | Streaming embed batches (bounded memory); `index vacuum` + `index backup` subcommands | `:317-359` accumulator; vacuum/backup are NEW maintenance ops |
| `cli/commands/mcp.py` | **MODIFIED** | `daemon` un-stubbed via `utils/daemon.py` reuse | `:109-129` |
| `mcp/server.py` | **DELETED (replaced)** | Hand-rolled state machine → SDK MCPServer owns initialize/negotiation/state | Name collision with SDK `MCPServer` — delete, don't rename |
| `mcp/protocol.py` | **SPLIT** | JSON-RPC + Initialize/ToolsList/ToolsCall models → SDK types (DELETE); SIF I/O models (QueryInput/QueryOutput/GetInput/... Lex/Vec) → PRESERVED as tool I/O | `:29-194` deleted; `:201-331` preserved |
| `mcp/handlers.py` | **REWRITTEN (thin)** | ToolHandler ABC → `@mcp.tool` functions wrapping SearchBackend; business mapping preserved | `:28-42` ABC dies; QueryInput validation + output shaping survive |
| `mcp/backend.py` | **PRESERVED + MODIFIED** | All business logic survives; add lazy embedder, pipeline parity (expander/reranker/snippet), filters param, hoisted pipeline | `:87-109` lazy; `:163-168` parity; `_run_in_db:111-118` unchanged |
| `mcp/transports/stdio.py` + `http.py` | **DELETED (replaced)** | SDK stdio + `streamable_http_app()`; Origin middleware/session dict/ping SSE replaced by SDK transport + transport_security | `http.py:181-191` Origin check → verify SDK covers Host+Origin |
| `mcp/watch_host.py` | **PRESERVED + REWIRED** | start/stop_embedded_watch unchanged; lifespan composes SDK `session_manager.run()` + watch | `:103-213`; D-14 teardown order preserved |
| `mcp/app.py` | **NEW** | Builds SDK MCPServer, registers tools from backend, wires lifespan + transports | The single new MCP composition root |
| `config/settings.py` | **MODIFIED** | New fields: title_weight, query_prompt_name, filter/eval knobs; env-only contract unchanged | Docs-gate applies to every field |
| `.github/workflows/test.yml` | **NEW** | py3.10–3.13 × ubuntu/macos matrix + Windows smoke (hc remote yoga) | Currently only docs.yml exists |
| `pyproject.toml` | **MODIFIED** | `mcp>=2.3,<3` dependency; 3.13 classifier; extras cleanup; trusted publishing | fastapi/uvicorn already core (`:36-37`) |

## Recommended Project Structure (deltas only)

```
src/sif/
├── core/
│   ├── models.py          # MODIFIED: SearchOptions.filters + live offset
│   └── filters.py         # NEW: FilterAst domain dataclasses (no SQL)
├── search/
│   ├── filters.py         # NEW: SQL compiler + Python evaluator
│   ├── bm25.py            # MODIFIED: filter WHERE, title weights, score order
│   ├── vector.py          # MODIFIED: filter JOIN, adaptive fetch_k, dedup
│   ├── hybrid.py          # MODIFIED: dedup pre-fusion, offset slice, single attach
│   ├── staleness.py       # MODIFIED: bounded read
│   ├── context_attach.py  # MODIFIED: bounded read
│   ├── suggest.py         # MODIFIED: rapidfuzz
│   ├── personal.py        # NEW: known-item fixture synthesis
│   └── benchmark.py       # PRESERVED
├── indexing/
│   ├── parser.py          # MODIFIED: dispatch wired, checksum decision
│   └── incremental.py     # MODIFIED: create_parser + frontmatter freshness
├── database/
│   ├── schema.py          # MODIFIED: title FTS, mtime idx, index_meta
│   ├── migrations.py      # DELETED/quarantined (dead)
│   └── maintenance.py     # NEW: vacuum/analyze/optimize/backup ops
├── embedding/
│   ├── embedder.py        # MODIFIED: prompt_name, deterministic ModelScope path
│   └── identity.py        # NEW: index_meta embedder identity guard
├── models/
│   ├── search.py          # DELETED/quarantined (dead)
│   └── download.py        # MODIFIED: defaults + cache fix
├── mcp/
│   ├── app.py             # NEW: SDK composition root
│   ├── backend.py         # PRESERVED+MODIFIED: lazy/parity/filters
│   ├── watch_host.py      # PRESERVED+REWIRed lifespan
│   ├── server.py          # DELETED (SDK replaces)
│   ├── protocol.py        # SPLIT: wire types deleted, I/O models preserved
│   ├── handlers.py        # REWRITTEN thin (@mcp.tool wrappers)
│   └── transports/        # DELETED (SDK replaces)
├── cli/commands/
│   ├── eval.py            # NEW: sif eval --personal
│   ├── models.py          # NEW: sif models pull/status
│   ├── metadata.py        # NEW: sif metadata discovery
│   ├── search.py          # MODIFIED: filter flags + --offset (shared decorator)
│   ├── index.py           # MODIFIED: streaming embed, vacuum, backup
│   └── mcp.py             # MODIFIED: daemon un-stub
└── config/settings.py     # MODIFIED: new fields
```

**Rationale:** FilterAst in `core/` (domain, shared by CLI/MCP/searchers, no SQL dependency); compiler in `search/` (mirrors how `core/models.py` holds protocols while `search/` holds implementations). `maintenance.py` in `database/` (SQL ops, presentation-free; CLI renders). MCP `app.py` is the only new composition root — backend/watch_host survive because they are already transport-agnostic.

---

## Architectural Patterns

### Pattern 1: One Filter AST, Two SQL Injection Points — Pre-RRF by Construction

**What:** A single domain AST (`core/filters.py`) compiled to one SQL WHERE fragment over the `documents` table (`search/filters.py`). BM25 injects it into its existing WHERE; Vector injects it into its existing post-KNN JOIN WHERE. Hybrid applies it **automatically pre-RRF** because both source searchers receive the same `SearchOptions.filters` — no hybrid-specific filter code exists.

**When to use:** Always — this is the answer to "where does the filter AST live."

**Injection points (verified):**
- BM25 scoped path: `bm25.py:76-93` — the `AS MATERIALIZED` CTE computes MATCH once; the filter goes in the **outer** `WHERE d.collection_id IN (...)` clause (`:90`), NEVER inside the CTE (would re-run MATCH per candidate — the plan optimization comment `:68-75` documents why).
- BM25 unscoped path: `bm25.py:98-111` — the empty `collection_filter` slot (`:108`) is the natural injection point.
- Vector: `vector.py:87-99` — append to `{collection_filter}` (`:97`) after the KNN MATCH; the JOIN to `documents d` already exists.

**Trade-offs / why NOT vec0 metadata columns:** Official sqlite-vec docs (alexgarcia.xyz/sqlite-vec/features/vec0.html, seam tier LOW — cross-checked with the codebase's own audit note `vector.py:80-86`) confirm vec0 metadata WHERE only supports `=,!=,>,>=,<,<=` — **no LIKE/GLOB/IS NULL/JSON functions**. Path-prefix (LIKE) and frontmatter-key (JSON) predicates cannot be expressed; adding metadata columns requires a full vec0 table rebuild (vec0 has no ALTER); and KNN is brute-force regardless, so metadata columns save nothing at personal-KB scale (only partition keys shard, and a single-user KB is one partition). The post-KNN JOIN-WHERE over-fetch pattern is already proven in production for collection filters (WR-04). **Keep it; scale the over-fetch.**

**Adaptive over-fetch:** `fetch_k = max(limit*4, 50)` (`vector.py:77`) under-returns selective filters (the WR-04 comment documents the exact trap). When `options.filters` is present, raise the multiplier (e.g. estimate selectivity via a cheap `SELECT COUNT(*)` with the compiled WHERE, or iteratively double fetch_k up to a cap until `limit+offset` survivors). Bound it — a 1-in-10000 filter must not scan the whole vec0 table silently; surface "filter too selective, raise limit" honestly.

**Example:**
```python
# core/filters.py (sketch)
@dataclass(frozen=True)
class PathPrefix:
    prefix: str
@dataclass(frozen=True)
class MtimeRange:
    after: float | None = None
    before: float | None = None
@dataclass(frozen=True)
class Tags:
    values: list[str]
    mode: str = "any"          # any | all
@dataclass(frozen=True)
class Frontmatter:
    key: str
    op: str                    # eq | ne | gt | lt | contains
    value: str | float | bool
@dataclass(frozen=True)
class And:
    nodes: list["FilterNode"]
# Or / Not similarly; FilterNode = union of the above

# search/filters.py (sketch)
def compile_filter(node: FilterNode | None, alias: str = "d") -> tuple[str, list[Any]]:
    """Return ('AND d.path LIKE ? ...', params) or ('', []) for None.
    Tags/Frontmatter compile to json_each / json_extract over {alias}.metadata.
    Parameterized only — no string interpolation of user values."""
```

**Sentinel contract:** `SearchOptions.collection_ids` uses None=unfiltered / []=exclude-all (`core/models.py:277-279`, guards `bm25.py:55-56`, `vector.py:48-49`). Filters must follow the same discipline: `filters=None` means no filter; an impossible filter returns zero results, never leaks.

### Pattern 2: Dedup and Pagination Order — Over-fetch → Filter → Per-doc Dedup → Fuse → Slice

**What:** The correct hybrid result pipeline order, fixing three verified bugs at once:
1. VectorSearcher dedups by document_id (keep best distance) **before** trim and **before** returning to fusion — kills RRF rank-sum inflation (`rrf.py:56-79`).
2. HybridSearcher fuses over `limit + offset` candidates, dedups (now mostly a no-op safety net), then slices `[offset : offset+limit]` — kills the post-truncation dedup slot loss (`hybrid.py:77-99`) and the dead offset (`hybrid.py:238`).
3. BM25 min_score moves into SQL (or is applied before LIMIT) so pages don't under-return (`bm25.py:112-122`).

**When to use:** Always; this is the correctness core of feature 2.

**Trade-offs:** Per-doc dedup in vector changes scores for multi-chunk documents (deflates the inflated ones) — this is a **ranking behavior change**, so the personal bench (Pattern 5) should measure it. Keep the change behind the bench instrument, not before it. BM25 SQL already applies OFFSET (`:112`); vector must account offset in fetch_k and trim; hybrid must NOT double-apply offset (BM25 already skipped offset rows — decide one owner: recommended **searchers return from rank 0, hybrid owns the offset slice**, which means removing OFFSET from the BM25 SQL when called via hybrid, or keeping BM25 offset for standalone use and having hybrid pass offset=0 downward then slice itself; the latter preserves standalone BM25 pagination — pick it).

**Example:**
```python
# hybrid.py search() (sketch of the corrected tail)
fetch = replace(options, limit=options.limit + options.offset, offset=0)
bm25_results = self.bm25.search(query, fetch)
vector_results = self.vector.search(embedding, fetch)   # already per-doc deduped
fused = self.rrf.fuse([bm25_results, vector_results],
                      fetch.limit, weights=[...], k=options.rrf_k)
deduped = self._deduplicate_results(fused)               # safety net
page = deduped[options.offset : options.offset + options.limit]
return self._attach_contexts(page)                       # ONE attach
```

### Pattern 3: MCP SDK v2 Migration — Preserve the Backend, Replace the Protocol Shell

**What:** The hand-rolled MCP stack is a protocol shell around a clean async backend. SDK v2 replaces the shell; the backend survives nearly intact.

**External facts (official primary sources; seam tier LOW for `webfetch` — verify by install/import smoke at phase start before committing plans):**
- PyPI `mcp` latest **2.3.0**; v2 exists. `requires_python >=3.10` (PyPI metadata, classifiers 3.10–3.14) **but README says "Python 3.11+"** — unresolved contradiction, critical for SIF's 3.10 floor (see Research Flags).
- `FastMCP` is now `MCPServer` (`from mcp.server.mcpserver import MCPServer, Context`; README also shows `from mcp.server import MCPServer`). Old import path raises ModuleNotFoundError. Decorator API `@mcp.tool()`/`@mcp.resource()` keeps v1 signatures.
- **Dual-era is automatic:** one `streamable_http_app()` serves the 2026-07-28 revision AND handshake-era clients ≤2025-11-25, routed per-request by `MCP-Protocol-Version` header before user code. No `legacy=` option, no version allowlist — both eras always on. 2026-era HTTP has no `Mcp-Session-Id`; the 2025-era leg keeps in-process sessions (`max_sessions` default 10000, `session_idle_timeout` 1800s). `stateless_http=True` affects the legacy leg only. This is exactly the milestone's "双时代（2025/2026）" requirement — the SDK does it for free.
- **Annotations:** `@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False))` from `mcp.types` (snake_case). Hints are not security. `idempotent_hint`/`destructive_hint` are defined only for non-read-only tools — SIF's tools are all read-only, so `read_only_hint=True, open_world_hint=False` is the correct annotation set; idempotent is meaningless on them.
- **Structured output:** the return type annotation drives `outputSchema` + `structured_content` automatically; Pydantic return models supported; dict/list/scalar returns wrapped into both `content` (JSON text) and `structured_content`. Returning the existing `QueryOutput`/`GetOutput` Pydantic models from tool functions gives legacy clients the JSON text they parse today AND modern clients structuredContent — zero client breakage.
- **Transport security:** DNS-rebinding protection auto-enables for loopback hosts unless `transport_security` is set — this is the Host-header validation the milestone asks for; verify it covers Host+Origin and delete the hand-rolled Origin middleware (`http.py:181-191`) only after confirming.
- Low-level `Server` rebuilt (constructor handlers) — SIF does NOT need it; the decorator API is the path. `mcp-types` is a separate distribution; fields snake_case, wire JSON camelCase via `model_dump(by_alias=True)`. `ToolError` for model-visible errors; other exceptions sanitized to `-32603`.
- `mcp.run(transport="stdio"|"streamable-http", host=..., port=...)` for standalone; `streamable_http_app()` ASGI factory for mounting; mounted apps need a lifespan driving `mcp.session_manager.run()`.

**Migration mapping (SIF files):**

| SIF file | Disposition | Why |
|----------|-------------|-----|
| `mcp/server.py` (state machine, initialize, tools/list, tools/call, resources/read) | **DELETE** | SDK owns all of it; name collision with SDK MCPServer |
| `mcp/protocol.py:29-194` (JsonRpc*, Initialize*, ToolsList*, ToolsCall*, MCPTool, capabilities) | **DELETE** | SDK wire types replace; protocol version negotiation automatic |
| `mcp/protocol.py:201-331` (SearchResult, Document, CollectionInfo, QueryInput/Output, GetInput/Output, MultiGet, Status, Lex/Vec) | **PRESERVE** | These are SIF's tool I/O contract (qmd compat); become @mcp.tool input params + return models |
| `mcp/handlers.py` (ToolHandler ABC + 4 handlers) | **REWRITE thin** | ABC dies; each handler becomes an `@mcp.tool` async function calling the same backend methods; QueryInput validation preserved |
| `mcp/backend.py` (SearchBackend) | **PRESERVE + MODIFY** | `_run_in_db` threading, WR-08 degradation, suggestions wrapper, boundary remap all survive; add lazy embedder + parity + filters |
| `mcp/transports/stdio.py`, `http.py` | **DELETE** | SDK stdio + streamable_http_app replace; session dict/ping SSE/Origin middleware gone |
| `mcp/watch_host.py` | **PRESERVE + REWIRE** | start/stop_embedded_watch unchanged; `mcp_watch_lifespan` composes `async with mcp.session_manager.run(): watch=start(); yield; stop()` |
| `mcp/app.py` | **NEW** | Composition root: build MCPServer, register tools, wire lifespan, run transport |
| `cli/commands/mcp.py` | **MODIFY** | stdio/http call app.py; daemon un-stub via utils/daemon.py |

**What can be preserved (the important answer):** ~all business logic. `SearchBackend` (321 lines) is already async + transport-agnostic + fresh-connection-per-request — it was built for this. The watch host's D-14 teardown ordering and the WR-08 BM25-degradation carve-out survive verbatim. The SIF I/O Pydantic models survive as the tool contract. Only the ~600 lines of hand-rolled JSON-RPC/state/transport shell are deleted.

**Pipeline parity + lazy embedder (backend modifications):**
- Parity: build `SearchPipeline` with `query_expander`/`reranker`/`snippet_extractor` exactly as CLI `query_cmd` does (`search.py:947-985`), gated by the same settings (`rerank_enabled` opt-in). Hoist the pipeline per connection-context instead of per request (`backend.py:163`).
- Lazy embedder: replace eager `factory.create_model` in `__init__` (`backend.py:93-109`) with a lazy property that loads on first vector/hybrid need — `EmbeddingManager.load_model()` is already idempotent (`manager.py:80-101`); the watcher's `_EmbedState` (`watcher.py:191-238`) is the in-repo lazy precedent. BM25-only MCP sessions never load a model.
- lex/vec tools: wire the existing `LexSearchInput/Output`, `VecSearchInput/Output` (`protocol.py:265-290`) to `pipeline.search("lex: ...")` / `"vec: ..."` — the prefix routing already exists (`hybrid.py:297-317`).

**Trade-offs:** Big-bang shell replacement is risky but the blast radius is bounded: 6 MCP test modules (`tests/unit/mcp/`: test_server, test_transports_http, test_transports_stdio rewrite; test_backend, test_mcp_watch_host, test_integration mostly survive). The 90% coverage gate must hold through the rewrite. Doing MCP migration AFTER the search-layer fixes (filters/dedup/parity semantics) avoids re-working tool schemas twice.

### Pattern 4: Embedder Identity in a Regular `index_meta` Table — Not vec0 Markers

**What:** A new regular SQLite table `index_meta(key TEXT PRIMARY KEY, value TEXT)` stores the embedder identity JSON written at embed time and checked at embed/search construction:

```json
{"embedder": {"model_type": "modelscope", "model_name": "Qwen/Qwen3-Embedding-0.6B",
              "api_base": null, "dimension": 1024, "query_prompt_name": null,
              "identity_version": 1}}
```

**Why a regular table, not vec0 metadata/markers:**
1. Identity is **per-index**, not per-row — a vec0 column would repeat it 100k× and still require a full vec0 rebuild to add (no ALTER on vec0).
2. The existing dim guard already reads `sqlite_master` for `FLOAT[dim]` (`schema.py:361-376`); a regular table is readable without sqlite-vec loaded (BM25-only installs can still report identity).
3. **The cache already does exactly this** — `_cache_model_id` (`manager.py:153-163`) = `"{model_type}:{model_name}[@{api_base}]"`, cache PK `(content_hash, model_id)` (`cache.py:69-77`). Reuse the same identity string as the `index_meta` key value so cache and index agree on "which model."
4. **The same-dimension trap is real:** Harrier-OSS-v1-0.6b and Qwen3-0.6B are both 1024-dim (PROJECT.md Key Decisions). The three existing dim guards (`schema.py:366`, `index.py:247`, `watcher.py:234`) all pass silently on a same-dim swap. Identity (model_name + prompt_name) is the only guard that catches it.

**Behavior:**
- Write identity on every successful embed commit (embed_cmd + watch embed leg).
- On mismatch at embed time: fail-fast with the existing remedy wording ("re-embed or restore model") — extend, don't duplicate, the three guard sites (consolidate into `embedding/identity.py`).
- On mismatch at search time: warn + mark results (reuse the `vectors_stale` machinery) rather than hard-fail reads — reads must degrade, never crash (staleness module posture).
- **Legacy DBs (vectors exist, no identity):** treat missing identity as "legacy unknown" — warn once, offer `sif index embed --force`, do NOT hard-fail existing searches. Backfill identity on the next embed.
- `query_prompt_name` is part of identity: prompted vs unprompted query vectors are incompatible even for the same model (Qwen3/Harrier instruct pattern). Document-side embeds use no prompt; query-side uses `prompt_name` (new Settings field + `_encode_kwargs` support).

**Trade-offs:** A regular table is one more schema object, but it is idempotent DDL (`CREATE TABLE IF NOT EXISTS`) — zero migration risk, and it can later hold other index facts (schema fingerprint, last vacuum) without new tables.

### Pattern 5: Personal Bench = Known-Item Synthesis + SearchEvaluator Reuse + query_log Replay

**What:** `sif eval --personal` needs no manual annotation. Two complementary instruments, both riding existing machinery:

1. **Known-item synthesis (labeled, nDCG/Hit/MRR):** generate queries from the user's own corpus — title/H1/frontmatter `title` → query string; the source document's corpus-relative path → grade-1 relevance. Use the **legacy fixture schema** (`relevant_docids`/path-keyed, `relevance_key="path"`) so `SearchEvaluator._validate_fixture` (`benchmark.py:453-484`) accepts it WITHOUT category/split labels — the fixed `CATEGORIES` tuple (`benchmark.py:21`) stays byte-identical for the standard bench. New module `search/personal.py` synthesizes the fixture dict; `SearchEvaluator.report(search_fn, clock)` (`benchmark.py:575-657`) runs it unchanged.
2. **Real-query replay (unlabeled, retrieval stats):** `QueryLogRepository.history()` (`repositories.py:682`, returns `(query, count, last_used)` aggregates) supplies the user's actual queries. Replay reports zero-result rate, latency percentiles, suggestion hit rate — NOT nDCG (no labels). This is the "免人工标注" real-world signal.

**Hook points (verified):**
- `SearchEvaluator` (`benchmark.py:410`) + `BenchHarness`/`_measure_state` pattern (`cli/commands/bench.py:214-235`: hoist pipeline once per state, `evaluator.report(lambda q: pipeline.search(q, options), clock=time.perf_counter)`).
- `QueryLogRepository` (`repositories.py:645-698`) — already written by CLI search (`search.py:271 _record_query_history`); MCP deliberately does NOT write query_log (`backend.py:204` comment, D-08) — personal replay reflects CLI usage only; document that.
- Held-out gate for Harrier: `warrants_default_change(baseline, candidate, delta)` (`benchmark.py:394-407`) + `rank_sweep` tie honesty (`:361-391`). The personal corpus needs its own tuning/held-out split (e.g. hash-of-path bucketing) so Harrier's EN+ZH held-out win is measured on documents never used for tuning.

**When to use:** Build this BEFORE the correctness fixes and BEFORE Harrier — it is the measurement substrate for dedup/title-FTS/chunk-swap decisions. The milestone explicitly gates Harrier on held-out evidence; the instrument must exist first.

**Trade-offs:** Known-item queries are easier than real information needs (title-match bias) — honest limitation; pair with real-query replay and the existing 56-query graded bench. Do NOT extend `CATEGORIES` (breaks byte-identical category reporting the Phase 16 work locked); personal fixtures use the legacy schema or a separate report path.

### Pattern 6: Eliminate Per-Query Full Scans — Bounded Reads + Single Attach

**What:** Three verified full-scan sources, three fixes:
1. **Staleness** (`staleness.py:34-49`): full `document_embeddings` scan per search. Fix: the result set is ≤ limit+offset documents — judge staleness with a **bounded** read. vec0 has no metadata index (per-document filtered lookup is itself a full scan — the module docstring says so), so the options are: (a) maintain a regular SQLite shadow table `embedded_documents(document_id PRIMARY KEY)` written in the same txn as vector insert/delete (cheap, indexed, `SELECT document_id FROM embedded_documents WHERE document_id IN (...)`), or (b) cache the embedded-id set per connection with a write-generation invalidator. **Recommend (a)** — a regular shadow table is the same pattern as `index_meta`, survives process boundaries (MCP fresh-connection-per-request can't cache), and the write paths are already centralized (`VectorSearcher.add_embeddings_batch`/`delete_embeddings_by_document`, `vector.py:176-206`). The display gate (no embeddings → no markers) and degrade-never-crash (vec0 missing → None) contracts must be preserved.
2. **Contexts** (`context_attach.py:53-56`): full `contexts WHERE context_type='path'` scan per search. The module docstring explains WHY no SQL pre-filter: verbatim legacy `target_id` rows can't match resolved paths in SQL (realpath not invertible). Fix without breaking that contract: keep the Python normalization but **bound the read** — load only path-type contexts (already filtered) and cache the normalized map per connection with an invalidator on context writes; OR add a normalized-path column written at context-write time (the write-side normalization decision already exists per PROJECT.md) and SQL-match on it with verbatim fallback. Recommend the write-side normalized column + `idx_contexts_target` (already exists, `schema.py:410-413`) — but this touches the context normalization Key Decision, so flag for phase discussion; the per-connection cache is the lower-risk first step.
3. **Double attach** (`hybrid.py:99` + `:271`): remove the pipeline-exit re-attach for the hybrid path (searchers already attach); attach exactly once at the pipeline exit for ALL paths, removing the searcher-internal attach OR the pipeline one — pick one owner. Recommend: searchers stop attaching; `SearchPipeline` attaches once at every exit (lex/vec/hyde/hybrid). This also fixes the lex/vec paths getting attach via searcher while hybrid gets it twice — one owner, one scan.

**When to use:** Feature 2 scale work; after the correctness fixes (the attach-owner change interacts with dedup/offset).

**Trade-offs:** The shadow table is a maintained flag — the staleness docstring explicitly warns that maintained flags are "the silent-lie bug class Phase 10.1 hunted." Mitigation: write it in the SAME transaction as every vector insert/delete (the paths are centralized in VectorSearcher + the purger), and add a reconcile check to `sif cleanup`/`index vacuum`. If the planner judges the lie-risk too high, the per-connection cached-set option (b) is derived-only (no persisted flag) but doesn't help MCP's fresh connections — hence (a) with transactional coupling is the recommendation.

### Pattern 7: Schema Migrations via SchemaManager's Idempotent + Detection-Gated Machinery

**What:** `SchemaManager.create_all` (`schema.py:18-29`) runs on every `init_schema` and is the production migration engine. Its proven mechanisms:
- **Idempotent DDL:** `CREATE TABLE/INDEX IF NOT EXISTS` everywhere.
- **Column add:** `_add_column_if_missing` (`:31-36`, PRAGMA table_info + ALTER).
- **Table migration:** SAVEPOINT-wrapped (`_migrate_path_contexts:108-132`).
- **FTS detect-and-rebuild:** `_fts_is_misconfigured` (`:221-231`) reads `sqlite_master.sql`, drops+recreates+reseeds when the shape is wrong (`:233-241`, `:326-336`); legacy-trigger detection gates a `'rebuild'` (`:345-348`) so migrated DBs pay nothing (CR-01 decision).

**v1.2 migrations follow these exact patterns — NOT MigrationManager (dead, divergent, broken triggers).** See the Schema Migration List below.

---

## Schema Migration List

| # | Migration | Mechanism | Cost / risk | Gate |
|---|-----------|-----------|-------------|------|
| 1 | `idx_documents_mtime ON documents(mtime)` | `_create_indexes` idempotent CREATE INDEX (`schema.py:387-419`) | One-time index build, trivial | None — fresh+migrated identical |
| 2 | `documents_fts` gains `title` column: `fts5(title, content, content='documents', ...)` | Extend the detect-and-rebuild machinery: add a `_fts_lacks_title` predicate reading `sqlite_master.sql` (mirror `_fts_is_misconfigured:221-231`); DROP+recreate when absent; **update all 3 documents triggers** (`:275-298`) to carry `new.title`/`old.title`; reseed (`:327-331` pattern) | One-time full FTS rebuild on upgrade (proportional to corpus); zero cost after | Detection-gated like CR-01; verify `documents_fts_v` vocab shadow (`:259-262`) survives the drop/recreate (it resolves by name at query time — flag for phase test) |
| 3 | `index_meta(key TEXT PRIMARY KEY, value TEXT)` | New `_create_index_meta_table` in `create_all`, CREATE TABLE IF NOT EXISTS | Trivial | None; identity backfilled on next embed (Pattern 4 legacy handling) |
| 4 | `embedded_documents(document_id TEXT PRIMARY KEY)` shadow (Pattern 6 option a) | CREATE TABLE IF NOT EXISTS + backfill `INSERT ... SELECT DISTINCT document_id FROM document_embeddings` gated on table-empty | One-time backfill scan; ongoing transactional writes | Reconcile in cleanup/vacuum; preserve display-gate + degrade contracts |
| 5 | Title column weights | **No schema change** — `ORDER BY bm25(documents_fts, w_title, w_content)` aux function at query time replaces `rank` in both BM25 SQL paths; weights from Settings (`title_weight`) | Query-plan change only | Bench-measured (Pattern 5); default weights reproduce current behavior if w_title=w_content |
| 6 | (Optional, deferred) normalized context path column | Only if Pattern 6 contexts fix chooses write-side normalization | Touches context Key Decision | Phase discussion; per-connection cache is the lower-risk default |

**NOT migrations:** vec0 table is UNCHANGED (no metadata columns, no rebuild — Pattern 1/4 rationale). `documents.metadata` stays TEXT JSON (json_each at query time; JSON1 verified available locally, unused in src today — verify on CI platforms). No `schema_version` table (that belongs to the dead MigrationManager).

---

## Data Flow Changes

### Filtered Hybrid Search (v1.2)

```
CLI --path/--tag/--mtime/--meta  OR  MCP QueryInput.filters
    ↓ parse + validate (Pydantic on MCP side)
FilterAst (core/filters.py) → SearchOptions.filters
    ↓ compile_filter() → (WHERE fragment, params) over documents d
    ├─ BM25Searcher: outer WHERE of scoped CTE / unscoped SQL  [pre-RRF]
    │    ORDER BY bm25(fts, w_title, w_content), min_score in SQL, LIMIT/OFFSET
    └─ VectorSearcher: post-KNN JOIN WHERE + adaptive fetch_k   [pre-RRF]
         per-doc dedup (best distance) BEFORE trim
    ↓ both return per-doc results from rank 0
RRFFusion.fuse([bm25, vec], limit+offset, weights, k)   [math unchanged]
    ↓ dedup safety net → slice [offset:offset+limit]
ONE attach_path_contexts + mark_vector_staleness (bounded reads)
    ↓
SearchResult page → CLI formatters / MCP structuredContent
```

### MCP v2 Request Flow

```
client (2025-era initialize  OR  2026-era MCP-Protocol-Version header)
    ↓ SDK streamable_http_app() routes by era BEFORE user code
    ↓ transport_security: Host/Origin validation (loopback auto)
@mcp.tool async fn (annotations: read_only_hint=True, open_world_hint=False)
    ↓ QueryInput validation (PRESERVED Pydantic model)
SearchBackend.hybrid_search(filters=..., ...)   [PRESERVED]
    ↓ _run_in_db: fresh connection in asyncio.to_thread  [UNCHANGED]
    ↓ lazy embedder (first vector need) + hoisted SearchPipeline w/ parity
SearchPipeline.search → (filtered hybrid flow above)
    ↓ return QueryOutput (Pydantic)
SDK auto-wraps → content (JSON text, legacy clients) + structuredContent + outputSchema
```

### Embedder Identity Flow

```
sif index embed / watch --embed
    ↓ EmbeddingManager.embed → EmbeddingResponse(model_id, dimensions)
    ↓ identity string = _cache_model_id() format (model_type:model_name[@api_base])
    ↓ + query_prompt_name + dimension → index_meta JSON
    ↓ write in SAME txn as vector batch commit
next embed/search construction:
    ↓ read index_meta → compare to configured embedder identity
    ├─ match → proceed
    ├─ mismatch (incl. same-dim Harrier swap) → embed: fail-fast re-embed remedy
    │                                          search: warn + vectors_stale markers
    └─ missing (legacy DB) → warn once, backfill on next embed, never hard-fail reads
```

### Personal Bench Flow

```
sif eval --personal
    ├─ search/personal.py: scan corpus titles/H1/frontmatter → known-item fixture
    │    (legacy schema, relevance_key="path", hash-split tuning/held-out)
    ├─ QueryLogRepository.history() → real-query replay set (unlabeled)
    ↓ BenchHarness hoists SearchPipeline (bench.py:214-235 pattern)
    ↓ SearchEvaluator.report(search_fn, clock)  [REUSED unchanged]
    ↓ known-item: nDCG@10/Hit@10/MRR + p50/p95; replay: zero-result rate/latency
    ↓ warrants_default_change(baseline, candidate) gates Harrier switch
```

---

## Scaling Considerations

| Concern | ~1k docs | ~10k docs | ~100k docs |
|---------|----------|-----------|------------|
| Per-query staleness/contexts scans (today) | tolerable | noticeable (N+1 with expansion) | dominant cost — Pattern 6 bounded reads required |
| Vector over-fetch with selective filter | fetch_k=50 fine | adaptive multiplier needed | cap + honest "too selective" message; brute-force KNN is 75-150ms (PROJECT.md ANN-skip rationale) |
| Title FTS rebuild on upgrade | seconds | seconds-minutes | minutes; one-time, detection-gated |
| Embed memory (today: all chunks accumulated) | fine | fine | OOM risk — streaming batches (feature 2); watcher already embeds outside txn |
| MCP per-request pipeline construction | minor | minor | hoist per connection-context |
| index_meta / shadow table writes | negligible | negligible | negligible (transactional, indexed) |

### Scaling Priorities

1. **First bottleneck: per-query full scans** (staleness + contexts + double attach) — fixed by Pattern 6, benefits every search at every scale.
2. **Second: embed memory** at 100k docs — streaming batches; the model compute still dominates wall-clock (unchanged).
3. **Not a bottleneck: SQLite itself** — WAL+flock+short txns (v1.1) already correct; VACUUM/ANALYZE/optimize are maintenance hygiene, not hot-path fixes.

---

## Anti-Patterns

### Anti-Pattern 1: Wiring Filters Into the Dead Layer
**What people do:** add filter fields to `models/search.py::SearchQuery.filters` (it already HAS a `filters` dict — tempting) or `search/strategy.py::SearchContext.filters`.
**Why it's wrong:** both are test-only dead code (verified importers); the live path is `core/models.py::SearchOptions` → BM25/Vector/Hybrid. Wires connect to nothing.
**Do this instead:** extend `core.models.SearchOptions`; delete/quarantine the dead layer first so the trap disappears.

### Anti-Pattern 2: Filtering Inside the BM25 Materialized CTE
**What people do:** put the filter predicate inside `WITH matched AS MATERIALIZED (SELECT ... WHERE documents_fts MATCH ? AND <filter>)`.
**Why it's wrong:** the CTE exists to evaluate MATCH exactly once (`bm25.py:68-75` comment); a filter inside re-runs MATCH per candidate document (the `SCAN fts VIRTUAL TABLE INDEX 32:=M1` plan the comment warns about).
**Do this instead:** filter in the OUTER WHERE after the JOIN to documents.

### Anti-Pattern 3: vec0 Metadata Columns for the Filter AST
**What people do:** add path/tag/mtime as vec0 metadata columns to "pre-filter KNN."
**Why it's wrong:** no LIKE/GLOB/JSON operators (official docs); full vec0 rebuild to add columns; brute-force KNN anyway; identity is per-index not per-row.
**Do this instead:** post-KNN JOIN-WHERE over `documents` with adaptive over-fetch (Pattern 1); identity in `index_meta` (Pattern 4).

### Anti-Pattern 4: Dedup After Fusion Only
**What people do:** keep `hybrid.py:97` post-truncation dedup as the only dedup.
**Why it's wrong:** RRF already summed duplicate ranks (`rrf.py:56-79`) — scores are inflated before dedup runs; slots were consumed before truncation.
**Do this instead:** per-doc dedup inside VectorSearcher before returning; hybrid dedup is a safety net; fuse over limit+offset then slice.

### Anti-Pattern 5: Migrating Through MigrationManager
**What people do:** add v1.2 DDL to `database/migrations.py` because it's named "migrations" and has a `schema_version` table.
**Why it's wrong:** dead (tests-only), divergent schema (`chunks`/`chunk_embeddings`), and it carries the broken legacy FTS triggers Phase 10.1 eradicated.
**Do this instead:** SchemaManager idempotent + detection-gated patterns (Pattern 7); delete/quarantine MigrationManager.

### Anti-Pattern 6: Trusting the Dimension Guard for Model Swaps
**What people do:** assume the `FLOAT[dim]` mismatch guard catches a bad embedder swap.
**Why it's wrong:** Harrier-0.6b and Qwen3-0.6B are both 1024-dim — the guard passes silently (PROJECT.md Key Decision).
**Do this instead:** identity = model_type+model_name+api_base+prompt_name in index_meta (Pattern 4); dim guard stays as a secondary check.

### Anti-Pattern 7: Shipping Tag Filters Before Fixing Frontmatter Freshness
**What people do:** build the filter AST and discovery on top of `documents.metadata` as-is.
**Why it's wrong:** frontmatter-only edits never update metadata (New finding 1, `incremental.py:300-318`) — tag filters silently return stale results.
**Do this instead:** parser/checksum freshness fix (feature 2) lands BEFORE or WITH the filter feature; add a regression test: edit only frontmatter tags → reindex → metadata updated.

### Anti-Pattern 8: Keeping the Hand-Rolled MCP Server Alongside the SDK
**What people do:** wrap the SDK around the existing `MCPServer` class or keep both "for compatibility."
**Why it's wrong:** name collision, two state machines, double negotiation logic; the SDK already serves both eras.
**Do this instead:** delete the shell (server.py/protocol wire types/transports), preserve backend + I/O models + watch_host (Pattern 3).

### Anti-Pattern 9: Maintained Staleness Flag Without Transactional Coupling
**What people do:** add an `embedded_documents` shadow table updated "best effort" after vector writes.
**Why it's wrong:** the staleness docstring names maintained flags as the silent-lie bug class; a shadow that drifts lies about vector lag.
**Do this instead:** write the shadow in the SAME transaction as every vector insert/delete (centralized in VectorSearcher); reconcile in cleanup/vacuum; preserve display-gate + degrade-never-crash.

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| MCP Python SDK v2 (`mcp>=2.3,<3`) | NEW core dependency (fastapi/uvicorn already core); `mcp.server.mcpserver.MCPServer` decorator API | **Verify Python 3.10 install first** (PyPI >=3.10 vs README 3.11+ contradiction); mcp 1.27.0 already in dev env |
| sqlite-vec 0.1.9 | UNCHANGED — no vec0 schema change | KNN brute-force; filters via JOIN; identity via regular table |
| rapidfuzz | NEW dependency (suggest only) | `process.extract` over full vocab replaces difflib+bucket; measure recall+latency vs the documented 11ms/46ms baselines |
| Harrier-OSS-v1-0.6b | Optional embedder via existing factory | Gated on EN+ZH held-out win; identity + query prompt_name required |
| PyPI trusted publishing | NEW CI workflow | docsif latest 1.0.1; publish v1.1.x then v1.2; hatch dynamic version already wired |
| GitHub Actions test matrix | NEW workflow (py3.10–3.13 × ubuntu/macos) | Add 3.13 classifier; Windows smoke via hc remote yoga (yoga needs uv/Python setup first — PROJECT.md) |
| MCP Registry + Claude Code skill | NEW packaging artifacts | Tool annotations + structuredContent make the server registry-ready; skill wraps the CLI/MCP surface |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| FilterAst ↔ SearchOptions | `filters` field on the dataclass | Rides `dataclasses.replace` over-fetch automatically (`hybrid.py:236-239`) |
| Filter compiler ↔ BM25/Vector | `(where_sql, params)` tuple | Parameterized only; alias `d`; respects collection sentinel contract |
| CLI ↔ MCP filter surface | shared FilterAst; CLI flags via one decorator, MCP via Pydantic input model | Parity by construction — same AST, same compiler |
| SearchBackend ↔ SDK tools | `@mcp.tool` async fns call backend methods | Backend stays transport-agnostic; `_run_in_db` unchanged |
| watch_host ↔ SDK lifespan | compose `session_manager.run()` + start/stop_embedded_watch | D-14 teardown order preserved; flag-off path byte-identical |
| Embedder identity ↔ 3 dim guards | consolidate into `embedding/identity.py` | schema.py:366 / index.py:247 / watcher.py:234 call one guard |
| Personal bench ↔ SearchEvaluator | fixture dict in, BenchReport out | Evaluator unchanged; legacy schema avoids CATEGORIES coupling |
| Personal bench ↔ QueryLogRepository | `.history()` read | CLI-written only (MCP doesn't log, D-08) — document the bias |
| Maintenance ↔ SchemaManager | vacuum/analyze/optimize/backup ops in database/maintenance.py | CLI renders; flock arbitration for vacuum (write op) |
| CLI commands/Settings ↔ docs gate | `make docs-generate` + tests/test_docs.py | Every new command/field regenerates cli-reference.md + configuration.md |

---

## Suggested Build Order

Dependency-driven tiers. Each tier unlocks the next; parallelization notes included. The ordering principle: **regression net → measurement → correctness → features → shell swap → gated evaluation → polish.**

| Tier | Build | Why this position | Depends on |
|------|-------|-------------------|------------|
| **0** | **Engineering foundation:** test CI matrix (py3.10–3.13 × ubuntu/macos) + Windows smoke (hc remote yoga, uv/Python setup first) + repo hygiene (delete tracked junk, dead MigrationManager/models.search/strategy quarantine, Makefile/extras/pre-commit cleanup, 3.13 classifier) + **PyPI v1.1.x trusted publishing** | CI BEFORE any risky migration — every later tier needs the regression net; hygiene removes the dead-layer traps before filter work; publishing v1.1.x is independent and de-risks the v1.2 release pipeline | — |
| **1** | **Quality instrument:** personal known-item bench (`sif eval --personal`, search/personal.py + eval.py) + rapidfuzz swap (measured) | Measurement BEFORE mutation — dedup/title-FTS/chunk changes need a baseline; rapidfuzz is independent and small; instrument reuses SearchEvaluator unchanged | 0 (CI net) |
| **2** | **Search correctness:** parser dispatch wiring + frontmatter-freshness fix; per-doc vector dedup + pre-truncation hybrid dedup; offset/pagination (CLI --offset + MCP offset + hybrid slice + BM25 min_score order); double-attach elimination; **title FTS + column weights** (schema migrations #1 mtime idx, #2 title FTS) | The bug fixes that change ranking semantics — measured by tier 1's instrument; parser/frontmatter fix MUST precede metadata filters (Anti-Pattern 7); title FTS is the riskiest schema migration, done early with CI net + bench | 1 |
| **3** | **Metadata filtering:** FilterAst + SQL compiler + CLI/MCP filter surface + metadata discovery tool/CLI + adaptive over-fetch | Depends on tier 2's metadata freshness + pagination; one AST shared CLI/MCP; discovery uses JSON1 (verify on CI) | 2 |
| **4** | **Scale & maintenance:** staleness/contexts bounded reads (shadow table + single attach owner); `index vacuum`/`backup`; streaming embed batches; **embedder identity** (index_meta, migration #3/#4, consolidate dim guards) | Identity BEFORE Harrier (tier 6); scan elimination after correctness (attach-owner interacts with dedup); streaming embed independent; vacuum/backup independent | 2 (identity also 0 for CI) |
| **5** | **MCP SDK v2 modernization:** shell replacement (app.py, delete server/protocol-wire/transports) + annotations + structuredContent/outputSchema + pipeline parity + lazy embedder + lex/vec wiring + Host validation (transport_security) + `mcp daemon` un-stub + Claude Code skill + MCP Registry | AFTER the search layer stabilizes (filters/dedup/parity semantics) so tool schemas aren't reworked twice; backend/watch_host preserved; **start with a Python-3.10 install/import smoke spike** (can run during tier 2-3); 6 MCP test modules rewrite, coverage gate holds | 3 (filter surface), 2 (pipeline semantics); SDK spike early |
| **6** | **Harrier gated evaluation:** EN+ZH held-out via personal instrument + standard bench; query prompt_name support; switch default ONLY on `warrants_default_change` win | Depends on tier 1 instrument + tier 4 identity (same-dim trap) + prompt_name; locked decision: held-out gate | 1, 4 |
| **7** | **Chunk sweep + breadcrumb experiment + models UX + install docs:** chunk size/overlap sweep + title-breadcrumb experiment (bench-measured); `sif models pull/status` + downloader fixes (DEFAULT_MODELS, md5 cache, deterministic ModelScope path, canonical cache dir); install docs rewrite (uv-first) | Chunk sweep needs instrument + streaming embed; models UX is independent (can float to tier 0/1 if capacity); install docs after models UX settles | 1, 4 (sweep); models UX independent |

**Phase ordering rationale:**
- CI (0) before migrations (2/4) — the milestone's riskiest changes (title FTS rebuild, shell swap) need a green matrix to land against; Windows smoke is a gate, not full support (locked).
- Instrument (1) before correctness (2) and Harrier (6) — "bench instrument before Harrier evaluation" is explicit; dedup/title changes are ranking-behavior changes that need evidence.
- Parser wiring (2) before metadata filters (3) — frontmatter freshness is a hard correctness dependency (New finding 1), and "parser wiring before format-adjacent work" is the stated downstream constraint.
- Identity (4) before Harrier (6) — the same-dimension trap makes identity a prerequisite, not a nice-to-have.
- MCP shell swap (5) after search-layer stability (2/3) — avoids double-rework of tool I/O schemas; the SDK 3.10-compat spike de-risks early without blocking.

**Research flags for phases:**
- **Tier 5 (MCP):** HIGH research need — Python 3.10 vs 3.11 SDK contradiction (install smoke FIRST); 2024-11-05-era client compat under v2 (milestone dual-era = 2025/2026; confirm dropping 2024-era is acceptable); exact `transport_security` Host/Origin semantics vs the existing middleware; `streamable_http_app()` lifespan composition with watch_host.
- **Tier 2 (title FTS):** MEDIUM — verify `documents_fts_v` vocab shadow survives drop/recreate; bm25() column-weight query plan; FTS rebuild cost at corpus scale.
- **Tier 3 (filters):** MEDIUM — LIKE-prefix index usability (collation) for path filters; JSON1 availability on ubuntu/macos/Windows CI; adaptive over-fetch selectivity estimation.
- **Tier 4 (staleness shadow):** MEDIUM — transactional coupling audit of ALL vector write paths; reconcile design; the maintained-flag lie-risk (Anti-Pattern 9).
- **Tier 0/1/7:** LOW — standard patterns (CI workflow, Click commands, downloader fixes); unlikely to need deep research.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Integration mapping (file:line) | HIGH | Read directly from src at HEAD 1aff2c9 this session; every prior claim re-verified |
| Filter AST design | HIGH | Grounded in verified BM25 CTE + Vector JOIN seams + official sqlite-vec operator limits |
| Schema migration plan | HIGH | SchemaManager machinery read directly; patterns mirror proven CR-01/Phase-10.1 work |
| Dedup/pagination/attach fixes | HIGH | Bugs verified in source (rrf.py accumulation, hybrid.py order, double attach) |
| MCP SDK v2 API facts | LOW (seam: webfetch) | Official primary sources (PyPI JSON, SDK repo, py.sdk.modelcontextprotocol.io) agree across 6 pages, but provider tier is LOW — **verify by install/import smoke before planning commitments**; Python 3.10 contradiction unresolved |
| Personal bench design | HIGH | Reuses verified SearchEvaluator/QueryLogRepository/BenchHarness; legacy-schema path avoids CATEGORIES coupling |
| Build order | HIGH (dependency logic) | Derived from verified code dependencies; tier 5 timing carries the SDK-compat uncertainty |

## Gaps to Address (phase-specific research later)

1. **MCP SDK Python 3.10 support** — PyPI `requires_python>=3.10` vs README "3.11+". Resolve by `pip install mcp==2.3.0` + import smoke on a 3.10 interpreter at MCP phase start. If v2 truly needs 3.11: either environment-marker pin `mcp<2` on 3.10 or drop 3.10 (a Constraints change requiring user decision).
2. **2024-11-05-era clients under SDK v2** — docs enumerate only ≤2025-11-25 handshake era + 2026-07-28. SIF today hardcodes 2024-11-05. Confirm whether old-era clients still negotiate; milestone "dual-era 2025/2026" suggests 2024-era drop is acceptable — document it.
3. **fts5vocab shadow survival** across documents_fts drop/recreate (title migration) — test on a populated DB.
4. **transport_security exact behavior** — does SDK loopback DNS-rebinding protection validate Host AND Origin sufficiently to delete the custom middleware? Test with spoofed Host/Origin.
5. **JSON1 on all CI platforms** — verified locally (macOS); confirm ubuntu + Windows smoke.
6. **LIKE-prefix index usability** for path filters under default collation — EXPLAIN QUERY PLAN check.
7. **Contexts normalization decision** — Pattern 6's write-side normalized column touches the context Key Decision (PROJECT.md); needs phase discussion vs the lower-risk per-connection cache.

## Sources

- **Codebase (HIGH — read directly at HEAD 1aff2c9, 2026-11-13):** all `src/sif/` files cited inline; `git diff 95c136c..HEAD -- src/` empty (prior line numbers valid, corrections noted); `pyproject.toml`, `Makefile`, `.github/workflows/docs.yml`, `tests/test_docs.py`, `scripts/generate_*_ref.py`, `git ls-files` (junk), `src/sif/_version.py`.
- **PyPI JSON API (seam tier LOW, direct authoritative read):** pypi.org/pypi/docsif/json (releases 0.1.0–1.0.1, latest 1.0.1 uploaded 2026-11-07); pypi.org/pypi/mcp/json (latest 2.3.0, requires_python >=3.10).
- **Official MCP Python SDK docs (seam tier LOW, cross-verified across pages):** github.com/modelcontextprotocol/python-sdk (README); py.sdk.modelcontextprotocol.io/whats-new/, /migration/, /servers/tools/, /run/legacy-clients/ (FastMCP→MCPServer, dual-era routing, ToolAnnotations, structured output, transport_security, session model).
- **Official sqlite-vec docs (seam tier LOW, cross-checked with codebase audit note):** alexgarcia.xyz/sqlite-vec/features/vec0.html (metadata/auxiliary/partition columns, operator limits); github.com/asg017/sqlite-vec (README); SIF `search/vector.py:80-86` (brute-force KNN audit, HIGH).
- **Historical (reference only):** `.planning/milestones/v1.1-research/ARCHITECTURE.md` (v1.1 patterns — WAL/flock, IncrementalIndexer extraction, dead-layer warning — all confirmed shipped).

---
*Architecture research for: SIF v1.2 Search Precision and Agent Experience (integration focus)*
*Researched: 2026-11-13 · Verified at HEAD 1aff2c9*
