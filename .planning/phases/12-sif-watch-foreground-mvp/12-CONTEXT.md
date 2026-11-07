# Phase 12: `sif watch` Foreground MVP - Context

**Gathered:** 2026-11-07
**Status:** Ready for planning

<domain>
## Phase Boundary

The first complete host of the live-index loop: running `sif watch` in a terminal keeps the index current as files change, proving events → incremental reindex end-to-end on the Phase 11 engine.

1. **Watch command + event pipeline (LIVE-01/LIVE-02)** — new `sif watch` foreground CLI command; wire the log-only stubs in `src/sif/indexing/watcher.py` through debounce into incremental reindexing. Editor save storms (2–5 events) coalesce into one index operation.
2. **Save-reality reconciliation (LIVE-03)** — macOS atomic-save rename chains and moves/renames reconcile to the right document: no missed saves, no spurious delete + re-add churn.
3. **Exclusion parity (LIVE-04)** — temp/editor noise (`.swp`, `.sb-*`, `4913`, `.DS_Store`, etc.) never enters the index; watch exclusions behave identically to scanner `ignore_patterns` (one source of truth).
4. **Tiered depth (LIVE-05)** — default depth is BM25/FTS only; `--embed` explicitly opts into vector updates; embedding never runs as a background default.
5. **Missing-root protection (LIVE-11)** — a collection root that disappears (unmounted/renamed) is never treated as mass deletion; the index survives and recovers when the root returns.

NOT in scope: MCP-embedded refresh and `--detach`/daemon/service install (Phase 13), pre-command staleness detection and staleness markers on results (Phase 14 — QUAL-06 slotted there), search-quality work (Phases 15–16), live rescope for collections added/removed mid-run (Phase 13 daemon concern).

</domain>

<decisions>
## Implementation Decisions

### Watch scope & collection lifecycle
- **D-01:** Watch **all registered collections by default**; a repeatable `-c/--collection` flag filters to a subset. Watch exactly the registered collection paths — never anything broader (research FEATURES: recoll's monitordirs lesson). New dirs under a watched root come free via recursive watch.
- **D-02:** Collection-set changes (`sif collection add/remove` while watch runs) require a **watch restart in MVP**. The startup pass reconciles whatever is registered when watch starts. Missing-root *return* recovery (D-11/D-12) is in scope because SC5 demands it; general live rescope is deferred to Phase 13's long-lived hosts.
- **D-03:** On startup, watch runs **one full `update_collection` reconcile pass** per watched collection before/alongside going live. This anchors correctness (anything drifted before watch started becomes fresh immediately) and exercises the proven Phase 11 loop. — **Reversibility:** reversible.

### flock discipline for the resident writer
- **D-04:** Watch **acquires the Phase 11 per-DB flock per debounced work-burst and releases it when idle** — never holds the lock for its process lifetime. Watch is just another `IncrementalIndexer` invoker under the D-01/D-02 (Phase 11) collision contract. Holding for life would push every `sif index update` / `sif embed` past its wait deadline into "proceed unlocked" — reintroducing the duplicate-embed racing LIVE-07 exists to prevent. — **Reversibility:** costly — Phase 13 hosts (MCP-embedded watch, daemon) inherit this discipline; changing it later reworks their lifecycle logic.

### Event→work pipeline
- **D-05:** Debounce = watchdog's built-in **`EventDebouncer(interval, callback)`, called positionally** (research STACK: first kwarg renamed in 7.0, positional works 3.x–7.x; we are capped `<7`). No hand-rolled timer thread. Default interval from the `watch_debounce_interval` setting (research suggests 0.5–1.0 s; exact default = Claude's discretion).
- **D-06:** After a burst settles, work is **per-path targeted processing, not a full collection scan**. The path — not the event — is the unit of work: for each settled path, stat it; exists + checksum changed → re-index, gone → remove. Rationale: a full `update_collection` pass parses *every* file in the collection (checksums live in parser output), so per-burst full passes re-read the whole KB on every save — Pitfall 3's CPU burn. Cost must be proportional to burst size. — **Reversibility:** costly — the per-path API on `IncrementalIndexer` is consumed by Phase 13 hosts and is exactly what Phase 14's drift refresh (LIVE-10) wants; design its shape with those consumers in mind.
- **D-07:** Event filtering uses **the scanner's exact predicate** — collection `pattern` glob + `DEFAULT_IGNORE_PATTERNS` + per-collection `ignore_patterns` — so live events can never index what a scan would skip (Pitfall 4: today a `private/**`-excluded file gets indexed the moment it's saved). `on_moved` filters on **`dest_path`** (rename *into* the tree is create-equivalent); src-side handling marks the old path for removal.
- **D-08:** The editor-noise patterns (`.swp`, `.sb-*`, `4913`, `.DS_Store`, `~`-suffixed, `.#`-prefixed, `.tmp`) are added to **`FileScanner.DEFAULT_IGNORE_PATTERNS`** so scan and watch share one list (LIVE-04 "identical" by construction, not by duplication). Note the glob `**/*.md` already excludes most of these from scans; the list matters for watch-side events and the few `.md`-suffixed temp names.

### `--embed` depth mechanics (LIVE-05)
- **D-09:** `--embed` runs **per-file inline inside the same per-burst flock window**, per Phase 11 D-05's locked direction. Sequence per changed file: parse/checksum → BM25/FTS per-file commit (existing D-04 Phase 11 txn) → embed chunks computed **outside any write transaction** (Pitfall 1: never hold a write txn across an embed call) → short vector-write txn. The embedding model lazy-loads on first `--embed` work and stays cached (`EmbeddingManager._model`); watch startup stays BM25-cheap.
- **D-10:** Without `--embed`: changed docs get stale chunks/vectors purged (existing `_process_file` behavior) and BM25/FTS stays fresh. Staleness *visibility* (markers on results) is Phase 14's QUAL-06 — not built here. Accepted trade-off: a large embed burst holds the lock longer, so a concurrent `update_cmd` may wait past its deadline; acceptable because bursts are small after debounce — if it bites, Phase 13 can split embed compute outside the lock.

### Missing-root protection (LIVE-11)
- **D-11:** **Guard in the shared core:** `IncrementalIndexer` (both `update_collection` and the new per-path path) **skips with a warning — never sweeps — any collection whose root does not exist**. This also fixes a live latent bug: today `update_cmd` on a missing/unmounted root scans empty and mass-deletes that collection's index.
- **D-12:** **Watcher-level recovery:** when a watched root disappears, mark the collection missing, keep a light periodic re-stat (interval = Claude's discretion, seconds-scale), and on return reschedule the watch + run a full reconcile pass for that collection. Warn once per transition, not per poll.

### Foreground UX & shutdown
- **D-13:** Output reuses the **Phase 11 progress-event protocol** (`"code payload"` events): concise per-batch summary lines (e.g. `indexed N · removed M · unchanged K`) plus a startup banner listing watched roots, depth mode (BM25-only / `--embed`), and debounce interval. `--verbose` yields per-file lines. Exact Rich rendering = Claude's discretion; document content is never Rich-markup-rendered (locked project decision).
- **D-14:** SIGINT/SIGTERM shutdown: stop accepting events, **flush the in-flight debounced batch (bounded)**, release the lock, run `PRAGMA wal_checkpoint(TRUNCATE)` (research recipe; establishes the Phase 13 shutdown precedent), exit 0. A second SIGINT exits immediately without flush.

### Test determinism
- **D-15:** Event-pipeline tests are **synthetic-event, zero-timing**: construct watchdog event objects (`FileCreatedEvent`/`FileMovedEvent`/…) directly against the handler — atomic-save rename chains, delete+create pairs, temp-file noise — with debounce flushed by invoking the settled callback directly (or an injected clock). 1–2 real-FS end-to-end tests in `tmp_path` (real observer, real `os.replace` atomic save) with generous timeouts, serialized, never sleep-polling without a deadline (Phase 11 D-08/D-09 culture).

### Carried forward (pre-decided in research/roadmap — do not re-litigate)
- WAL + busy_timeout + BEGIN IMMEDIATE via the one shared connection factory; per-file transactions (Phase 11 D-04/D-06).
- flock per-DB global lock, wait-then-run loser semantics (Phase 11 D-02/D-03); kernel flock, not PID-file (REQUIREMENTS Out of Scope).
- watchdog cap `>=4.0.0,<7.0.0` (7.0 dropped Python 3.10); `EventDebouncer` over hand-rolled debounce.
- Zero new runtime dependencies.
- FSEvents/inotify auto-selection via default `Observer()`; `PollingObserver` only as network-FS/inotify-exhaustion fallback.
- Settings: `SIF_`-prefixed fields for `watch_debounce_interval`, `watch_ignore_patterns`, update-depth default (research STACK #3).

### Claude's Discretion
- Exact CLI surface details beyond D-01 (`--verbose` naming, banner wording, Rich layout)
- Per-path update API shape on `IncrementalIndexer` (method names, return type extending `IncrementalResult`)
- Debounce interval default value and settings field names
- Missing-root re-stat interval and warning cadence
- Watcher module restructuring (the `FileWatcher`/`IndexingEventHandler` skeletons have known lifecycle gaps — `stop()` never unschedules, `start()` overwrites a live observer — rewrite freely as long as hosts keep a clean start/stop contract)
- Burst batching internals (queue, single worker thread — writes off the observer thread per research)
- Where the per-path/temp-pattern logic lives (scanner vs. shared helper) as long as scan and watch share one predicate

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone research (authoritative recipes)
- `.planning/research/STACK.md` §"Key Integration Points" #2, #3, #6 — watcher wiring recipe (EventDebouncer positional, dest_path filtering, PatternMatchingEventHandler), watch settings fields, `sif watch` foreground loop shape
- `.planning/research/STACK.md` §"Stack Patterns by Variant" + §"Version Compatibility" — watchdog version matrix (cap `<7`, EventDebouncer signature), FSEvents coalescing notes
- `.planning/research/PITFALLS.md` §"Pitfall 2" — macOS atomic-save rename chains (the event sequences to reconcile)
- `.planning/research/PITFALLS.md` §"Pitfall 3" — debounce design (per-path settle, settle only event-emitting paths, serial worker)
- `.planning/research/PITFALLS.md` §"Pitfall 4" — watch-scope shaping vs event filtering; live events must not bypass collection ignore rules; overflow recovery
- `.planning/research/PITFALLS.md` §"Pitfall 5" — single-instance/double-writer context (flock designed in 11, consumed here per-burst)
- `.planning/research/PITFALLS.md` §"Pitfall 6" — events fire at write *start*; settle-check before reading
- `.planning/research/FEATURES.md` §table-stakes rows 1–4 + §"Watch shapes are a progression" — the watch-core-is-the-risk-item ordering, tiered-depth staleness semantics

### Planning documents
- `.planning/REQUIREMENTS.md` — LIVE-01..LIVE-05, LIVE-11 definitions; Out of Scope table
- `.planning/ROADMAP.md` §"Phase 12" — goal and success criteria 1–5 (the acceptance contract)
- `.planning/phases/11-live-index-foundation-concurrent-db-incremental-core/11-CONTEXT.md` — the lock contract (D-01..D-05), write granularity, and test-depth culture this phase builds on
- `.planning/PROJECT.md` §"Key Decisions" — embed_cmd per-collection transaction (Phase 03), WAL-before-any-second-writer ordering

### Project conventions
- `CLAUDE.md` — quality gates (pytest fail_under=90, ruff, ty), error-handling and CLI conventions, two-blank-lines style

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `IncrementalIndexer` (`src/sif/indexing/incremental.py:65`) — the shared incremental core; `update_collection()` is the proven full pass (startup reconcile, D-03); gains the per-path API (D-06). Presentation-free via `progress` callback events.
- `index_lock()` (`src/sif/database/locking.py:43`) — Phase 11 flock context manager with wait-then-run deadline; acquired per work-burst (D-04).
- `FileScanner` (`src/sif/indexing/scanner.py`) + `DEFAULT_IGNORE_PATTERNS` — the single exclusion predicate both scan and watch reuse (D-07/D-08).
- `src/sif/indexing/watcher.py` — `IndexingEventHandler`/`FileWatcher` skeletons: event dispatch shape and extension filtering exist, but handlers are log-only, `on_moved` checks src only, and lifecycle methods have gaps (stop never unschedules; start overwrites a live observer). Rewrite target, not preservation target.
- Connection factory (Phase 11) — every connection the watch process opens goes through it; no new connection sites.

### Established Patterns
- Repository pattern + per-file `with conn:` BEGIN IMMEDIATE transactions — extend, never long-running txns
- CLI lifecycle: `with Database(index_path) as db:` held for the command body (WR-01); watch is the first long-lived CLI process — signal handling is new territory
- Progress-event protocol (`"scan <n>"`, `"unchanged <name>"`, `"error <msg>"`, `"indexed <name>"`) — watch is a new host rendering the same events (D-13)
- Quality gates: pytest fail_under=90 zero exemptions; ruff line-length 100, mccabe ≤ 10; `ty check src/sif` clean

### Integration Points
- `src/sif/cli/commands/` — new `watch.py` command module (no `watch` command exists today; `mcp.py`/`index.py` are the structural analogs)
- `src/sif/config/settings.py` — new `watch_*` fields (debounce interval, ignore patterns, depth default)
- `pyproject.toml` — watchdog cap bump `>=3.0.0` → `>=4.0.0,<7.0.0`
- `update_cmd` (`src/sif/cli/commands/index.py`) — gains the missing-root guard for free through `IncrementalIndexer` (D-11)
- FTS5 external-content triggers (`src/sif/database/schema.py`) — per-file commits already interact correctly; per-path updates must keep trigger behavior identical

</code_context>

<specifics>
## Specific Ideas

No specific external references — decisions above are self-contained. Two construction details worth preserving for the planner:

- The deterministic event-test pattern is "construct watchdog event objects and drive the handler directly; flush debounce by invoking the settled callback" — never timing-race assertions (extends Phase 11's parent-holds-lock pattern culture to the event domain).
- macOS atomic-save arrives as `moved(file.md → file.md.sb-XXXX)` + `deleted(.sb-XXXX)` + `created(file.md)` + `modified(file.md)` — the temp leg is dropped by patterns, and the created/modified legs on the final path collapse under debounce into one per-path reindex. Vim is the opposite shape: in-place modifies plus `.swp`/`4913` noise.

</specifics>

<deferred>
## Deferred Ideas

- **Live rescope on collection add/remove while watch runs** — Phase 13 daemon/MCP hosts are the long-lived processes where restart-free rescope matters; MVP restarts (D-02).
- **Embed compute split outside the flock window** — only if D-10's lock-hold trade-off bites in practice; revisit with Phase 13's hosts.
- **`wal_checkpoint(TRUNCATE)` periodicity during long runs** — D-14 checkpoints at shutdown; periodic checkpointing is a daemon-era (Phase 13) tuning question.
- **inotify watch-limit detection + `PollingObserver` fallback UX** — research prescribes the fallback exists; polished detection/warning UX can land with Phase 13's Linux daemon testing.

</deferred>

---

*Phase: 12-`sif watch` Foreground MVP*
*Context gathered: 2026-11-07*
