# Phase 11: Live-Index Foundation (Concurrent DB + Incremental Core) - Context

**Gathered:** 2026-11-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the SQLite layer safe for a resident background writer and extract the single shared incremental-indexing core that all future watch hosts (Phases 12–14) reuse:

1. **Concurrent DB hardening (LIVE-06)** — every connection the codebase opens gets the locked pragma recipe (`busy_timeout=5000` → `journal_mode=WAL` → `synchronous=NORMAL`, in that order); write transactions use `BEGIN IMMEDIATE`; delivered via ONE shared connection factory.
2. **IncrementalIndexer extraction (roadmap SC3)** — the per-file incremental loop inside `update_cmd` (`src/sif/cli/commands/index.py:48`) is extracted into a shared `IncrementalIndexer`; `update_cmd` delegates to it; the dead `DocumentIndexer` (`src/sif/indexing/indexer.py:44`) is retired; no third copy of the loop exists.
3. **flock single-writer arbitration (LIVE-07)** — kernel flock on one global per-DB lock file; covers both long-running writers (IncrementalIndexer invocations AND `embed_cmd`); losers wait then run.

NOT in scope: watch event handling/debounce (Phase 12), MCP-embedded refresh and daemon (Phase 13), pre-command staleness detection (Phase 14), any embed_cmd transaction restructuring, search-quality work (15–16).

</domain>

<decisions>
## Implementation Decisions

### Arbitration semantics (flock)
- **D-01:** Lock coverage = all long-running write jobs: `IncrementalIndexer` invocations (`update_cmd` + MCP index tool) and `embed_cmd`. Short CRUD writers (collection add/remove, context writes) stay OUTSIDE the lock — `busy_timeout` + `BEGIN IMMEDIATE` handles them. Rationale: `embed_cmd` holds the DB write lock for an entire collection (locked Phase 03 decision); without arbitration a concurrent update BUSY-fails after 5s. Matches LIVE-07's "no duplicate embed" spirit.
- **D-02:** Loser behavior = **wait then run**. A writer that finds the lock held waits up to a configurable timeout (suggested default ~30s) for the winner to finish, then runs its own pass. Never silently drops distinct work (`update -c B` while A runs must eventually index B). — **Reversibility:** costly — Phases 12–14 watch hosts (daemon, MCP-embedded, pre-command) all build on this collision contract; changing it later reworks all three hosts.
- **D-03:** Lock granularity = **one global lock per database** (lock file next to the DB, e.g. `sif.db.lock`, created `0600`). NOT per-collection locks — the Phase 12–14 daemon story needs one "is a watcher running?" answer; different-collection updates simply queue behind the wait-then-run semantics.

### Write granularity (IncrementalIndexer transactions)
- **D-04:** `IncrementalIndexer` commits **per file** — each file's document + chunks + FTS writes are one short `BEGIN IMMEDIATE` transaction. Successful runs produce an identical index to today (SC3); only failure semantics change: a mid-run crash keeps completed files (resumable) instead of rolling back the whole run. Short lock holds are the point — searches and other writers interleave.
- **D-05:** `embed_cmd`'s per-collection transaction structure is **left untouched** in this phase. The flock decision (D-01) already absorbs its concurrency pain; Phase 03's CR-02 per-collection atomicity stays locked. Phase 12's watch `--embed` depth gets per-file behavior naturally through `IncrementalIndexer` when it lands.

### Connection consolidation
- **D-06:** **Unify to one shared connection factory** — pragma block + sqlite-vec load + bounded first-open retry (research recipe: read→write lock upgrades return `SQLITE_BUSY` immediately, so the WAL switch itself needs the retry) live in exactly one place. `Database` (CLI path) and `DatabaseConnection` (MCP path, `src/sif/mcp/backend.py:68`) both route through it. No connection site can forget the pragmas.
- **D-07:** **Retire dead connection code**: `ConnectionPool` (`src/sif/database/connection.py:105`, zero real callers, loads neither sqlite-vec nor pragmas) and the duplicate legacy `DatabaseConnection` (`src/sif/database/database.py:108`) are deleted, alongside dead `DocumentIndexer`. — **Reversibility:** costly — both are re-exported from `src/sif/database/__init__.py`, i.e. published package API; reversal is a git revert but any external importer of `sif.database.ConnectionPool` breaks in between.

### Concurrency test depth
- **D-08:** SC1/SC2 proof uses **both layers**: (a) in-suite tests with multiple real sqlite3 connections/threads against a real file DB in `tmp_path` — WAL interplay, pragma order, `BEGIN IMMEDIATE`, flock wait-then-run — broad, fast, coverage-counting; (b) 2–3 subprocess-level tests for the literal SC2 proof (two real `sif index update` processes racing; exactly one defers). Deterministic by construction: the parent holds/releases the lock and asserts the child's outcome.
- **D-09:** Subprocess concurrency tests run **in the default pytest invocation** (keeping `fail_under=90` honest about them), serialized (no xdist overlap), with generous timeouts (30s+ vs expected <5s), never sleep-polling without a deadline.

### Carried forward (pre-decided in research/roadmap — do not re-litigate)
- Pragma order and values: `busy_timeout=5000` FIRST, then `journal_mode=WAL` (persistent, set once per DB), then `synchronous=NORMAL`; `wal_checkpoint(TRUNCATE)` at daemon shutdown; network-FS WAL-fallback detection (pragma returns old mode → degrade + warn). Source: `.planning/research/STACK.md` "Key Integration Points" #1 and "Stack Patterns by Variant".
- `BEGIN IMMEDIATE` for write transactions (LIVE-06); vec0/embedding writes always inside explicit transactions.
- flock (kernel) — not PID-file-only, not a custom lockfile scheme (REQUIREMENTS.md Out of Scope).
- Zero new runtime dependencies.

### Claude's Discretion
- Lock file exact name/path derivation (next to DB, `0600`, per research security note)
- Wait-timeout default value and its `SIF_` settings field name (~30s suggested)
- Connection factory module placement and internal API shape
- `IncrementalIndexer` class/API shape (constructor deps, return type carrying added/updated/removed counts so CLI output stays identical)
- Subprocess test implementation details (env, invocation) as long as deterministic + serialized
- Bounded first-open/DDL retry bounds (research: "a handful of attempts, small backoff")
- CLI notice wording while waiting for the lock; winner/loser exit codes (both 0 on success)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone research (authoritative recipes)
- `.planning/research/STACK.md` §"Key Integration Points" #1 — the exact pragma block, order, first-open retry, checkpoint, and the connection-site inventory
- `.planning/research/STACK.md` §"What NOT to Use" + §"Version Compatibility" — WAL/sqlite-vec/busy_timeout compatibility matrix (WAL verified compatible with sqlite-vec 0.1.9)
- `.planning/research/PITFALLS.md` §"Pitfall 1" — current no-WAL/no-busy_timeout state with file:line evidence; the embed per-collection-transaction landmine
- `.planning/research/PITFALLS.md` §"Pitfall 5" + §"Security Mistakes" — flock vs PID-file design, 0600 lock file, double-writer arbitration model
- `.planning/research/PITFALLS.md` §"Looks Done But Isn't" — the concurrency-proof bar SC1/SC2 tests must meet
- `.planning/research/SUMMARY.md` §"Implications for Roadmap" — research phase 1 → roadmap Phase 11 mapping

### Planning documents
- `.planning/REQUIREMENTS.md` — LIVE-06, LIVE-07 definitions; Out of Scope table (lockfile/PID-file rejections)
- `.planning/ROADMAP.md` §"Phase 11" — goal and success criteria 1–4 (the acceptance contract)
- `.planning/PROJECT.md` §"Key Decisions" — embed_cmd per-collection transaction (Phase 03), WAL-before-any-second-writer ordering

### Project conventions
- `CLAUDE.md` — quality gates (pytest fail_under=90, ruff, ty), error-handling and CLI conventions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Database` (`src/sif/database/database.py:15`): CLI's connection wrapper — cached-connection property, `transaction()` context manager, `init_schema()`. Primary refactor target for factory routing (D-06).
- `DatabaseConnection` (`src/sif/database/connection.py:12`): MCP path; `backend.py:68` opens a fresh connection per tool transaction. Second route-through target.
- `update_cmd` (`src/sif/cli/commands/index.py:48`): the incremental loop to extract — pre-update subprocess hook, `FileScanner.scan`, checksum diff vs `existing_docs`, `MarkdownParser`, stale chunk/embedding cleanup, removed-file sweep. Carries `noqa: C901, PLR0912, PLR0915` — the extraction should shed those.
- `FileScanner` (`src/sif/indexing/scanner.py`) + checksum logic: reused as-is by `IncrementalIndexer`.
- Repositories (`src/sif/database/repositories.py`): `CollectionRepository` / `DocumentRepository` / `DocumentChunkRepository` — the per-file transaction body stays repository calls.

### Established Patterns
- Repository pattern; `Database.transaction()` commit/rollback context manager — extend with `BEGIN IMMEDIATE` rather than replacing
- CLI lifecycle: `with Database(index_path) as db:` held for the whole command body (Phase 10.1 WR-01, 26 construction sites) — keep this shape
- Quality gates: `pytest` fail_under=90 with zero exemption lines; ruff line-length 100; `ty check src/sif` clean

### Integration Points
- MCP: `src/sif/mcp/backend.py:68` — every tool transaction goes through `DatabaseConnection(...).transaction()`; must inherit pragmas via the factory
- `src/sif/indexing/watcher.py` — unwired watchdog stubs; its `TYPE_CHECKING` references to `DocumentIndexer` must be repointed to `IncrementalIndexer` when the dead class is deleted (Phase 12 wires the rest)
- `src/sif/database/__init__.py` — exports `ConnectionPool` + `DatabaseConnection`; update when retiring dead code (D-07)
- FTS5 external-content triggers (`src/sif/database/schema.py`) — per-file commits interact with the insert/update/delete triggers per file; behavior must remain identical (SC3)
- `embed_cmd` (`src/sif/cli/commands/index.py`) — gains flock acquisition (D-01), otherwise untouched (D-05)

</code_context>

<specifics>
## Specific Ideas

No specific external references — decisions above are self-contained. One construction detail worth preserving for the planner: the deterministic subprocess test pattern is "parent holds/releases the lock and asserts the child's outcome" (hold lock → child waits → release → child completes → assert both), never timing-race assertions.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 11-Live-Index Foundation (Concurrent DB + Incremental Core)*
*Context gathered: 2026-11-07*
