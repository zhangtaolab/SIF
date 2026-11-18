# Architecture Research: v1.1 Live Index + Search Quality Integration

**Domain:** Local hybrid search engine (existing layered Python 3.10+ app, CLI + MCP over SQLite/FTS5/sqlite-vec)
**Researched:** 2026-11-07
**Confidence:** HIGH for integration mapping (read directly from `src/sif/` source); MEDIUM for external best practices (cross-verified against sqlite.org primary docs, watchdog official docs, and qmd's own release notes)

**Scope:** Subsequent milestone — only how NEW features integrate with the existing architecture. Not a greenfield stack survey.

---

## Standard Architecture (Target State for v1.1)

### System Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          Interface Layer                                  │
│                                                                           │
│  ┌────────────────────┐              ┌─────────────────────────────────┐  │
│  │ CLI (Click)        │              │ MCP Server (stdio / HTTP)       │  │
│  │  sif watch  [NEW]  │              │  embedded LiveIndexService      │  │
│  │  sif search        │              │    thread [MODIFIED backend]    │  │
│  │   + pre-search     │              │  suggest tool [NEW handler]     │  │
│  │     detect [NEW]   │              │                                 │  │
│  │  sif suggest [NEW] │              │                                 │  │
│  └────────┬───────────┘              └───────────────┬─────────────────┘  │
│           │                                          │                    │
│           └────────────────────┬─────────────────────┘                    │
├────────────────────────────────┼──────────────────────────────────────────┤
│                        Application Layer                                  │
│  ┌─────────────────────────────┼───────────────────────────────────────┐  │
│  │ LiveIndexService [NEW]      │   SearchPipeline / HybridSearcher     │  │
│  │  EventDebouncer (watchdog)  │   [MODIFIED: rrf_k + weights ctor]    │  │
│  │  → IncrementalIndexer       │   Suggester [NEW: fts5vocab+history]  │  │
│  │    [EXTRACTED from          │   Reranker [MODIFIED: threshold]      │  │
│  │     update_cmd]             │                                       │  │
│  │  → optional embed step      │                                       │  │
│  └──────────────┬──────────────┴───────────────────┬───────────────────┘  │
├─────────────────┼──────────────────────────────────┼──────────────────────┤
│                       Infrastructure Layer                                │
│  ┌──────────────┴──────────────────────────────────┴───────────────────┐  │
│  │ Database / DatabaseConnection  [MODIFIED: WAL + busy_timeout +      │  │
│  │                                 BEGIN IMMEDIATE write txns]         │  │
│  │ SchemaManager [MODIFIED: DDL race guard, fts5vocab, query_log]      │  │
│  │ SQLite single file: documents + document_chunks + FTS5 (triggers)   │  │
│  │                     + vec0 embeddings + contexts + llm_cache        │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

One `LiveIndexService`, three thin hosts (CLI watch process, MCP server thread, one-shot pre-search check). One database file, WAL mode, single-writer discipline.

### Component Responsibilities

| Component | Status | Responsibility | Notes |
|-----------|--------|----------------|-------|
| `indexing/live.py` → `LiveIndexService` | **NEW** | Owns the watch loop logic: debounce → coalesce paths → checksum diff → incremental FTS write → optional embed | Host-agnostic; does not know whether it runs in CLI, MCP, or one-shot |
| `indexing/watcher.py` (`FileWatcher`, `IndexingEventHandler`) | **MODIFIED** | Wire stub handlers to `LiveIndexService`; add watchdog `EventDebouncer`; settle-check (mtime+size) before reading | Handlers currently log-only ("# Trigger incremental index" comments); `watchdog>=3.0.0` already a dependency |
| `indexing/incremental.py` (or extend `indexer.py`) → `IncrementalIndexer` | **EXTRACTED** | Per-file/per-path checksum-diff update (parse → update doc row → delete stale chunks → optional purge vectors); per-collection delete of vanished files | Extract the proven inline loop from `cli/commands/index.py::update_cmd` (lines 110–208). `DocumentIndexer` in `indexing/indexer.py` is currently dead code — referenced nowhere; either delegate to the new service or retire it |
| `database/connection.py` + `database/database.py` | **MODIFIED** | Every connection: `PRAGMA busy_timeout` first, then `journal_mode=WAL`, then `synchronous=NORMAL`; write txns via `BEGIN IMMEDIATE` | Both classes currently open per-operation connections with zero WAL/busy_timeout config — the primary concurrency gap |
| `database/schema.py` (`SchemaManager`) | **MODIFIED** | Concurrency-safe DDL (BEGIN IMMEDIATE + double-check, treat "already exists" as success); create `fts5vocab` virtual table + `query_log` table | qmd hit the exact "table documents_fts already exists" race on concurrent cold open under WAL and fixed it this way (qmd release notes) |
| `search/hybrid.py` (`HybridSearcher`, `SearchPipeline`) | **MODIFIED** | Accept `rrf_k` and `bm25_weight`/`vector_weight` in constructor; call `rrf.fuse_with_weights` for the BM25-vs-vector fusion | `RRFFusion.fuse_with_weights` ALREADY EXISTS (rrf.py) — this is plumbing, not new math. Weighted fusion applies only at the BM25↔vector point; multi-query-variant fusion in `SearchPipeline` stays 1:1 unweighted |
| `search/suggest.py` → `Suggester` | **NEW** | Prefix completion from `fts5vocab(documents_fts,'row')` + did-you-mean (edit distance over vocab candidates) + history suggestions from `query_log` | Read-only; NOT in the hot search path |
| `mcp/backend.py` (`SearchBackend`) | **MODIFIED** | Optionally start/stop an embedded `LiveIndexService` background thread at server construction/shutdown | Fresh-connection-per-request pattern (`_run_in_db`) is already concurrency-correct once WAL lands — no change needed there |
| `cli/commands/watch.py` → `sif watch` | **NEW** | Foreground watch loop; `--detach` spawns daemon; `--embed` sets update depth; pidfile/lockfile | Precedent: `sif mcp daemon` command slot exists (currently a stub raising "not yet implemented") — build one shared daemon helper for both |
| `utils/daemon.py` (or `cli/daemon.py`) | **NEW** | Detach (double-fork / `Popen`+setsid), pidfile, single-instance lock, launchd plist / systemd unit generation | Also un-stubs `sif mcp daemon` |
| `config/settings.py` | **MODIFIED** | New fields: `rrf_k`, `bm25_weight`, `vector_weight`, `watch_debounce_seconds`, `watch_embed` (depth), `watch_exclude_globs`, reranker threshold/latency knobs | Flows via existing `SIF_` env prefix + `get_settings()` lru_cache |

## Recommended Project Structure (deltas only)

```
src/sif/
├── indexing/
│   ├── watcher.py        # MODIFIED: EventDebouncer + LiveIndexService callbacks
│   ├── live.py           # NEW: LiveIndexService (the watch loop core)
│   ├── incremental.py    # NEW: IncrementalIndexer extracted from update_cmd
│   └── indexer.py        # MODIFIED: delegate or retire (currently dead code)
├── search/
│   ├── hybrid.py         # MODIFIED: rrf_k/weights ctor params, fuse_with_weights
│   ├── suggest.py        # NEW: Suggester (vocab prefix + did-you-mean + history)
│   └── rerank.py         # MODIFIED: score threshold filter in _sort_and_build_results
├── database/
│   ├── connection.py     # MODIFIED: WAL pragma stack on every connection
│   ├── database.py       # MODIFIED: same
│   └── schema.py         # MODIFIED: DDL race guard, fts5vocab, query_log
├── cli/
│   ├── commands/
│   │   ├── watch.py      # NEW: sif watch [--detach] [--embed]
│   │   └── search.py     # MODIFIED: pre-search detect hook, suggestions on empty
│   └── main.py           # MODIFIED: register watch_group
├── mcp/
│   ├── backend.py        # MODIFIED: embedded watcher lifecycle
│   └── handlers.py       # MODIFIED/NEW: suggest tool schema
├── utils/
│   └── daemon.py         # NEW: detach/pidfile/lock/launchd/systemd helper
└── config/
    └── settings.py       # MODIFIED: new fields above
```

**Rationale:** `live.py` sits in `indexing/` (application service over scanner/parser/repos, mirrors `DocumentIndexer` altitude). `suggest.py` sits in `search/` (pure read path over the DB). The daemon helper is `utils/`-level because both `sif watch --detach` and `sif mcp daemon` need it.

## Architectural Patterns

### Pattern 1: One Watch-Loop Service, Three Thin Hosts

**What:** The watcher loop lives in a single reusable class (`LiveIndexService`), hosted by three drivers:
1. **CLI process** — `sif watch` (foreground) / `sif watch --detach` (daemon)
2. **MCP server process** — background thread started at server construction, joined at shutdown
3. **One-shot pre-search check** — no loop at all; runs the same `LiveIndexService.refresh_once()` (scan + checksum diff + write diffs) before a search command

**When to use:** Always, for this milestone — this is the recommended answer to "where does the watcher loop live."

**Trade-offs / why NOT the alternatives:**
- *A single shared watch daemon that CLI/MCP clients talk to* — rejected: requires IPC protocol (socket/queue) that doesn't exist, and MCP stdio servers are spawned/killed at will by clients (Claude Desktop etc.), so a stdio server is an unreliable home for the only watcher. The DB file is the only shared state — keep it that way.
- *Watcher inside every MCP server unconditionally* — rejected: remote-embedding configs would bill on file changes without user intent; make it opt-in (`SIF_MCP_WATCH=1` or `mcp serve --watch`).
- Precedent from the qmd ecosystem: neither obsidian-qmd nor openclaw embeds a watcher in qmd itself — they debounce externally and shell out to periodic `qmd update` (openclaw defaults: update every 5m, embed every 60m). SIF's pre-search-detect tier is exactly this pattern, in-process.

**Example:**
```python
# indexing/live.py (sketch)
class LiveIndexService:
    def __init__(self, db_path, settings, indexer: IncrementalIndexer,
                 debounce_seconds: float = 1.0, embed: bool = False): ...

    def start(self, collections: list[Collection]) -> None:
        # watchdog Observer + EventDebouncer(debounce_interval=..., events_callback=self._on_events)
        ...

    def _on_events(self, events: list[FileSystemEvent]) -> None:
        paths = {fsdecode(e.src_path) for e in events if not e.is_directory}
        self.apply_paths(paths)          # checksum diff → short BEGIN IMMEDIATE txn per file

    def refresh_once(self, collections) -> IndexResult:
        # full scan + checksum diff — the pre-search fallback path
        ...

    def stop(self) -> None: ...          # observer.stop/join + debouncer.stop/join (flushes accrued)
```

### Pattern 2: Single-Writer Discipline — WAL + busy_timeout + BEGIN IMMEDIATE

**What:** Watcher writes vs CLI/MCP readers across processes are handled by SQLite itself:
- `PRAGMA busy_timeout=5000` **first**, then `PRAGMA journal_mode=WAL` (persistent per-file), then `PRAGMA synchronous=NORMAL` on **every** connection (both `DatabaseConnection._create_connection` and `Database.connection`). Order matters: the WAL switch itself takes a write lock, so two processes doing first-open race on it — busy_timeout must already be set.
- All write transactions use `BEGIN IMMEDIATE` (Python: `conn.execute("BEGIN IMMEDIATE")` inside the existing `transaction()` context managers). A deferred transaction that starts with a SELECT and then writes returns `SQLITE_BUSY` **immediately, regardless of timeout** (the upgrade trap) — this matters because `update_cmd` reads `existing_docs` then writes inside one connection scope.
- Keep write transactions milliseconds-short: parse/checksum/embed OUTSIDE the txn; only the repository writes inside.
- WAL + sqlite-vec vec0 tables is a proven production combination (llama-stack, tencent MemoryCore both run exactly this stack with these pragmas). No cross-process serialization needed beyond SQLite's own locks.

**When to use:** Land this BEFORE any watcher exists — it is the foundation every later phase stands on, and retrofitting concurrency after hosts multiply is the risky direction.

**Trade-offs:** WAL adds `-wal`/`-shm` sidecar files (fine on one machine; WAL never works on network filesystems — acceptable for a local-first tool). Long-running MCP read sessions can block checkpoints; `wal_autocheckpoint` default (1000 pages) bounds growth adequately at personal-KB scale.

**Verified against:** sqlite.org/wal.html (primary), Simon Willison / Bert Hubert on BEGIN IMMEDIATE, engam-lite and llama-stack connection code (MEDIUM — cross-verified web sources).

### Pattern 3: Update-Depth Split — BM25 Fast Path, Embed Opt-In

**What:** The watcher's default depth mirrors the existing CLI split between `index update` (documents + chunks + FTS triggers, no embeddings) and `index embed` (vectors, separate command). Watch events trigger only the FTS-affecting write; `--embed`/`SIF_WATCH_EMBED=1` additionally chains embed for changed documents only (lazy model load — `EmbeddingManager` already caches in `_model`).

**When to use:** Always as the default. Rationale: embed is 100–1000x slower than the FTS write, may load a 0.6B-param model, and for remote backends costs money per token — it must never be the silent default of an automatic background process. qmd's own ecosystem decouples the cadences (update 5m / embed 60m in openclaw).

**Trade-offs:** Vector results lag BM25 results between embed runs — acceptable and already true today (users run `update` and `embed` separately); the `--embed` tier closes it.

### Pattern 4: Configurable Hybrid Weights — Settings → HybridSearcher → RRFFusion

**What:** New Settings fields (`rrf_k: int = 60`, `bm25_weight: float = 0.5`, `vector_weight: float = 0.5`, with validators) flow: CLI/MCP construction sites read `get_settings()` → pass into `HybridSearcher(db, embedder, embedding_dim, rrf_k=..., weights=(bm25_w, vec_w))` → `HybridSearcher.__init__` builds `RRFFusion(k=rrf_k)` (currently hardcoded `k=60`) and `search()` calls `self.rrf.fuse_with_weights([bm25_results, vector_results], [w_bm25, w_vec], limit)` when weights are non-uniform, `fuse()` otherwise.

**Trap to avoid:** there are TWO `SearchOptions`/`SearchResult` model sets. `sif/models/search.py` (Pydantic) already has `bm25_weight`/`vector_weight`/`rrf_k` fields — but they are **dead**: the live search path uses `sif/core/models.py` dataclasses (`SearchOptions` there has NO weight fields). Wire the new settings through constructors, not through the dead Pydantic model; extend `core.models.SearchOptions` only if per-request override (`--bm25-weight` flag) is wanted.

**Trade-offs:** constructor injection keeps `HybridSearcher` testable and avoids a global; per-request overrides via `SearchOptions` are additive later. Weights apply only to the BM25↔vector fusion — NOT the multi-query-variant fusion in `SearchPipeline` (variants of one query are equals; weighting them is a different feature).

### Pattern 5: Query Suggestions as a Separate Read Path

**What:** `Suggester` in `search/suggest.py` is a standalone read-only service:
- **Prefix completion:** `CREATE VIRTUAL TABLE documents_fts_vocab USING fts5vocab(documents_fts, 'row')` (schema addition) → `SELECT term, cnt FROM documents_fts_vocab WHERE term LIKE 'q%' ORDER BY cnt DESC LIMIT n`. Endorsed pattern from the sqlite.org forum.
- **Did-you-mean:** pure-Python edit distance (stdlib `difflib.get_close_matches` suffices; no new dependency) over vocab candidates narrowed by first-letter/prefix — avoids shipping the `spellfix1` compiled extension, which is not in standard SQLite builds.
- **History:** new `query_log` table (query, timestamp, result_count); "did you mean" from your own past queries. No history table exists today (schema has collections/documents/document_chunks/contexts/llm_cache only).

**Where it hooks in:** the presentation/orchestration layer — CLI `query_cmd`/`search_group` and an MCP tool call it when results are empty or below threshold, plus an explicit `sif suggest "prefix"` command. It does NOT go inside `SearchPipeline.search()` — that keeps the hot path free of extra queries and keeps the pipeline's rerank/expand semantics untouched.

**Honest limitation (design-relevant):** SIF's FTS uses `tokenize='porter'` over unicode61, which does not segment CJK — continuous Chinese text becomes single long tokens. Vocab-based suggestions therefore skew ASCII; for a Chinese-language user, history-based suggestions and pinyin/substring matching matter more. Plan the fixture tests accordingly.

## Data Flow

### Watch Event Flow (Live Index)

```
FS change (editor save: created + 2-3 modified events)
    ↓
watchdog Observer (platform: FSEvents / inotify)      [EXISTING dep]
    ↓
EventDebouncer(debounce_interval≈1s)  ← timer resets per event; fires when quiet
    ↓  coalesced list[FileSystemEvent]
LiveIndexService._on_events
    ↓ filter by collection pattern/ignore/extension; settle-check (mtime+size stable)
IncrementalIndexer.apply_paths(changed, deleted, moved)
    ↓ checksum (sha256) vs documents.checksum           [read, outside txn]
    ↓ per file: parse → chunk → BEGIN IMMEDIATE txn → doc upsert + chunk delete/insert
    ↓            (FTS5 external-content triggers fire automatically) → COMMIT
    ↓ [only if --embed] EmbeddingManager.embed(changed chunks) → vec0 insert (own txn)
    ↓ collection stats update (document_count, last_indexed_at)
SQLite (WAL)  ←─ concurrently readable by CLI search / MCP queries ──
```

### Pre-Search Auto-Detect Flow (fallback tier)

```
sif search / query_cmd
    ↓
staleness check (cheap, no writes): scanner.stat_walk(collection.path)
    compare mtimes vs documents table — skip everything if no mtime drift
    ↓ drift detected
LiveIndexService.refresh_once(collections)   # same IncrementalIndexer, full-scan diff
    ↓
normal SearchPipeline.search(...)
```

Guard with a "cheap first" design: a stat-only walk detects drift in milliseconds at personal-KB scale (thousands of files); only then pay the checksum/parse cost. Cap the fallback (e.g. skip if >N files changed — tell the user to run `index update` instead) so a git branch switch doesn't turn a search into a full reindex.

### Hybrid Weights Flow

```
Settings (SIF_RRF_K / SIF_BM25_WEIGHT / SIF_VECTOR_WEIGHT, validated)
    ↓ get_settings() at construction
CLI query_cmd / MCP SearchBackend.hybrid_search
    ↓ HybridSearcher(db, embedder, dim, rrf_k, weights)
    ↓ BM25Searcher.search ─┐
    ↓ VectorSearcher.search ┴→ RRFFusion(k).fuse_with_weights([bm25, vec], [w_b, w_v])
    ↓ rerank (existing) → snippets (existing) → context attach (existing)
```

## Scaling Considerations

| Concern | ~1k docs | ~10k docs | ~100k docs |
|---------|----------|-----------|------------|
| Debounce burst (git checkout: thousands of events) | non-issue | coalesce via EventDebouncer; batch paths into ONE refresh pass, not per-file txns | same + consider full-scan refresh instead of event replay (events lie after mass renames); FTS optimize/cleanup |
| Pre-search detect cost | stat walk < 50ms | stat walk fine; mtime-drift gate prevents needless checksums | sample-based drift check or skip tier |
| Embed depth | seconds/file | background embed queue, lazy model load | decouple embed cadence from update (openclaw precedent: 5m/60m) |
| WAL growth | auto-checkpoint handles it | fine; watch `-wal` size if an MCP HTTP server holds long read sessions | periodic `wal_checkpoint(TRUNCATE)` in cleanup |
| Write contention | none at human typing speed | busy_timeout absorbs the rare overlap (watcher write vs manual `index update`) | single-writer is still the invariant; funneled writes, short txns |

### Scaling Priorities

1. **First bottleneck: embed throughput, not SQLite.** A 0.6B model on CPU dwarfs any DB write. Keep embed off the default path, lazy-load, batch changed docs.
2. **Second: mass-change events.** Debounce + batch-apply + full-scan fallback keeps the watcher from thrashing on branch switches/builds; `ignore_patterns` per collection already exists — reuse it for watch excludes.

## Anti-Patterns

### Anti-Pattern 1: A Third Copy of the Indexing Loop

**What people do:** write new watcher-specific indexing code.
**Why it's wrong:** there are ALREADY two implementations — `DocumentIndexer.index_collection` (dead code, referenced nowhere) and the inline loop in `update_cmd` (the production one, with hard-won fixes: checksum persistence, chunk purge before re-chunk, vector purge before doc delete, pre_update_cmd timeout). A watcher adding a third copy diverges from day one.
**Do this instead:** extract `IncrementalIndexer` from `update_cmd`'s loop, make `update_cmd` and `LiveIndexService` both call it, retire or delegate `DocumentIndexer`.

### Anti-Pattern 2: Indexing per Event Without Debounce

**What people do:** call the indexer in `on_modified`.
**Why it's wrong:** one editor save fires created+modified×N; atomic saves are rename bursts (temp file + move); you reindex half-written files and thrash FTS.
**Do this instead:** watchdog's built-in `EventDebouncer` (official documented pattern: `debounce_interval`, callback receives the coalesced list, flushes on stop) + an mtime/size settle check before reading.

### Anti-Pattern 3: Trusting busy_timeout Alone

**What people do:** set `busy_timeout`, skip `BEGIN IMMEDIATE`.
**Why it's wrong:** a read-then-write (deferred) transaction that needs a lock upgrade fails with SQLITE_BUSY immediately — the timeout does not apply to upgrades. `update_cmd`'s read-existing-then-write shape is exactly this. qmd additionally hit the DDL variant ("table documents_fts already exists" on concurrent cold open) because FTS5 `CREATE VIRTUAL TABLE IF NOT EXISTS` is not atomic across WAL connections.
**Do this instead:** BEGIN IMMEDIATE for write txns; schema DDL under BEGIN IMMEDIATE + double-check + treat "already exists" as success; small retry-on-BUSY wrapper for CLI first-open.

### Anti-Pattern 4: Embedding Inside the Watcher's Default Path

**What people do:** "keep everything fresh" — watcher embeds on every change.
**Why it's wrong:** model load latency in a background process; repeated re-embedding of a file being actively edited (each debounce flush = new chunks = new vectors); real money burned on remote-API embedding configs without user consent.
**Do this instead:** FTS-only default; `--embed` opt-in; embed only documents whose checksums actually changed; respect the existing `--force`/chunk-id-set skip logic.

### Anti-Pattern 5: Wiring Weights Through the Dead Model

**What people do:** add knobs to `sif/models/search.py::SearchOptions` (it already HAS `bm25_weight`/`rrf_k` fields — tempting).
**Why it's wrong:** that Pydantic model is unused by the live search path (`HybridSearcher`/`SearchPipeline` consume `core/models.py` dataclasses). Wires would be connected to nothing.
**Do this instead:** Settings → constructor injection per Pattern 4; extend `core.models.SearchOptions` for per-request overrides.

### Anti-Pattern 6: Suggestions Inside the Search Pipeline

**What people do:** compute suggestions on every search "since we're there."
**Why it's wrong:** adds queries to the hot path; muddies pipeline semantics (rerank vs suggest ordering); vocab queries are only valuable on empty/weak results.
**Do this instead:** separate `Suggester`, invoked by CLI/MCP presentation layer on empty-or-thin results, or explicitly.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| watchdog `Observer` | already a dependency; add `EventDebouncer` from `watchdog.utils.event_debouncer` | Platform backends (FSEvents/inotify) handled by watchdog |
| launchd / systemd | generate plist / unit files from the shared daemon helper; `sif watch --detach` for the portable path | KeepKeepAlive=false, WatchPaths alternative is NOT enough (needs debounce + depth logic) |
| Remote embedding APIs (optional) | unchanged; `--embed` depth is user opt-in so file events never silently bill | Probe-free dimension logic already cached per `base_url::model_name` |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `LiveIndexService` ↔ repositories | direct calls, existing Repository pattern | New per-file methods thin: `get_by_path` already exists; add `delete_by_path` if missing |
| Watcher ↔ `EmbeddingManager` | lazy, only when depth=embed | Model cached in `_model`; never load at watcher startup |
| MCP `SearchBackend` ↔ `LiveIndexService` | thread owned by backend; start in `__init__`/server start, join on shutdown | `_run_in_db` fresh-connection-per-request needs NO change under WAL |
| CLI search commands ↔ staleness check | function call before pipeline construction | Must stay optional + cheap (stat-only gate) |
| `Suggester` ↔ schema | fts5vocab virtual table + `query_log` writes at query time | query_log write is fire-and-forget, tiny txn, WAL-absorbed |
| `HybridSearcher` ↔ Settings | constructor injection at the 3 existing construction sites (query_cmd, MCP backend, tests) | Keep default k=60/0.5/0.5 so current behavior is byte-identical |

## Suggested Build Order

Dependency-driven; each tier unlocks the next. Matches the milestone's "四种形态，依赖递进" structure.

| # | Build | Why this position | Depends on |
|---|-------|-------------------|------------|
| 1 | **DB concurrency hardening + `IncrementalIndexer` extraction** (WAL/busy_timeout/BEGIN IMMEDIATE everywhere; schema DDL race guard; extract loop from `update_cmd`; per-file public API) | Foundation every watcher host stands on; WAL retrofit AFTER hosts multiply is the risky direction; extraction removes the dead-code hazard before a third copy appears | — |
| 2 | **`sif watch` foreground** (EventDebouncer wiring, BM25-only depth, `--embed` flag) | First and simplest host; proves the loop end-to-end; daemon and MCP embed reuse it verbatim | 1 |
| 3 | **MCP server embedded refresh** (backend thread lifecycle, opt-in flag) | Second host; stdio servers are client-lifecycle-owned — embed only where startup is explicit | 2 |
| 4 | **Daemon/detach** (`--detach`, pidfile, single-instance lock, launchd/systemd units; un-stub `mcp daemon`) | Packaging of the proven loop; lock prevents double-writer with tier 2/3 | 2 (independent of 3) |
| 5 | **Pre-search auto-detect** (stat-only drift gate + `refresh_once`) | Fallback tier for users who run nothing; needs `IncrementalIndexer` but not the loop; capped so it never becomes a hidden full reindex | 1 |
| 6 | **Hybrid weights configurable** (Settings → HybridSearcher → `fuse_with_weights`) | Fully independent of the watch tiers; pure plumbing over existing math; can slot anywhere after 1 — placing here keeps live-index phases contiguous | 1 (trivially) |
| 7 | **Query suggestions** (fts5vocab + query_log schema, Suggester, CLI/MCP surface) | Needs schema changes (fits with 1's schema work if desired) but not the watcher; CJK-limitation noted | schema touch |
| 8 | **Reranker tuning + bench expansion** (threshold/latency knobs; fixtures for weights+suggestions) | Consumes 6+7 as measurement subjects; quantified tuning last closes the loop | 6, 7 |

Watch core (2) before MCP embed (3) before daemon (4) before pre-command detect (5) — exactly the milestone's stated dependency progression.

## Sources

- Codebase (HIGH — read directly, 2026-11-07): `src/sif/indexing/watcher.py` (stub handlers confirmed), `indexing/indexer.py` (DocumentIndexer dead code confirmed via grep), `cli/commands/index.py` (production inline loop, update/embed split, pre_update_cmd timeout), `database/connection.py` + `database/database.py` (no WAL/busy_timeout confirmed), `database/schema.py` (porter FTS5 external-content triggers, vec0, no vocab/history tables), `search/hybrid.py` (hardcoded `RRFFusion(k=60)`, unweighted `fuse`), `search/rrf.py` (`fuse_with_weights` exists), `models/search.py` vs `core/models.py` (dead duplicate confirmed), `mcp/backend.py` (`_run_in_db` per-request connections), `mcp/transports/stdio.py`+`http.py` (server construction sites), `cli/commands/mcp.py` (`mcp daemon` stub), `config/settings.py` (no watch/weight fields), `pyproject.toml` (`watchdog>=3.0.0` present)
- sqlite.org WAL docs — sqlite.org/wal.html (MEDIUM via exa, cross-verified with practitioner sources)
- BEGIN IMMEDIATE upgrade trap — Simon Willison (2025-02-17) / Bert Hubert; sqlite.org locking model write-ups (MEDIUM, cross-verified)
- WAL + sqlite-vec in production — llama-stack PR #5428, tencent MemoryCore, engam-lite connection code (MEDIUM, multiple independent implementations)
- watchdog EventDebouncer — python-watchdog official examples + source (MEDIUM, primary docs)
- fts5vocab suggestions — sqlite.org FTS5 docs + sqlite.org forum a08215b6d3; spellfix1 docs (MEDIUM)
- qmd concurrency precedents — github.com/tobi/qmd releases (concurrent cold-open FTS5 DDL fix with BEGIN IMMEDIATE + double-check; embed context serialization), deepwiki tobi/qmd, obsidian-qmd CLAUDE.md (external debounced `update`+`embed`), openclaw memory-qmd docs (5m/60m cadence split) (MEDIUM)

---
*Architecture research for: SIF v1.1 Live Index + Search Quality (integration focus)*
*Researched: 2026-11-07*
