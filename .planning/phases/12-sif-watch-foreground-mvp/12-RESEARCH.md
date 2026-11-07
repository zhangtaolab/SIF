# Phase 12: `sif watch` Foreground MVP - Research

**Researched:** 2026-11-07
**Domain:** Filesystem-event-driven incremental indexing (watchdog + IncrementalIndexer + flock/WAL SQLite), foreground CLI host, signal-driven shutdown
**Confidence:** HIGH (codebase claims verified by reading Phase 11 source this session; watchdog behavior verified against the installed 6.0.0 package source AND a real-FSEvents probe on this machine; Click signal behavior verified empirically; milestone research same-day and primary-sourced)

## Summary

Phase 12 is a **wiring phase, not a foundation phase**. Phase 11 landed every hard prerequisite: `create_connection()` (busy_timeout → WAL → synchronous=NORMAL, implicit BEGIN IMMEDIATE), `IncrementalIndexer.update_collection()` with per-file transactions and a presentation-free progress protocol, `index_lock()` per-DB flock with wait-then-run loser semantics, and `DocumentRepository.get_by_path()`. What Phase 12 actually builds is: (1) the per-path targeted update API on `IncrementalIndexer` (D-06 — today only the full-collection scan exists), (2) the event→debounce→reconcile pipeline replacing the log-only stubs in `src/sif/indexing/watcher.py`, (3) a shared scan/watch exclusion predicate (D-07/D-08), (4) the missing-root guard (D-11 — a **verified latent mass-delete bug** in `update_collection` today), (5) the `sif watch` CLI host with tiered depth and signal-driven shutdown, and (6) the watchdog version cap `>=4.0.0,<7.0.0` (pyproject currently pins `>=3.0.0`; installed 6.0.0 already satisfies the new range).

This research's decisive contribution is a **real-machine event-shape probe** (watchdog 6.0.0 / FSEventsObserver on this macOS host) that converts the milestone's Pitfall-2 narrative into concrete, fixture-ready event sequences — including three facts the milestone research did not carry: (a) the observer emits a startup burst of `created` events for **pre-existing** files (absorbed by D-03's startup reconcile + checksum skip, but the handler must tolerate it); (b) FSEvents delivers **realpaths** (`/private/var/...` when the watched path was `/var/...`) — event→collection path matching must `resolve()` both sides or events never match under symlinked prefixes; (c) the atomic-save chain ends with a **trailing `deleted` event on the final path after the `moved` event** — proof that D-06's stat-based reconciliation (disk is truth, events are hints) is not optional polish but the correctness mechanism. Shutdown behavior (D-14) was verified empirically: a `signal.signal` handler inside a Click command intercepts before Click's `KeyboardInterrupt` → `Abort` path; graceful exit 0, double-SIGINT exit 130, SIGTERM exit 0 all reproduce on this machine with click 8.3.2.

**Primary recommendation:** Build in this order — (1) `IncrementalIndexer` gains `update_paths(collection, paths, *, force, progress)` + the missing-root guard inside `update_collection` (pure unit-testable increments, no watchdog involved); (2) the shared exclusion predicate + `DEFAULT_IGNORE_PATTERNS` additions; (3) the rewritten watcher module (debounce → per-path fold → single worker thread → per-burst flock); (4) the CLI host (startup reconcile → banner → signal loop → checkpoint on exit); (5) `--embed` inline depth last (it composes the per-path API with the embed_cmd primitives, all of which exist). Test with synthetic watchdog events driven directly into the handler (D-15), plus 1–2 real-FS integration tests in `tests/integration/` using the probe's verified sequences.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Watch scope & collection lifecycle**
- **D-01:** Watch **all registered collections by default**; a repeatable `-c/--collection` flag filters to a subset. Watch exactly the registered collection paths — never anything broader (research FEATURES: recoll's monitordirs lesson). New dirs under a watched root come free via recursive watch.
- **D-02:** Collection-set changes (`sif collection add/remove` while watch runs) require a **watch restart in MVP**. The startup pass reconciles whatever is registered when watch starts. Missing-root *return* recovery (D-11/D-12) is in scope because SC5 demands it; general live rescope is deferred to Phase 13's long-lived hosts.
- **D-03:** On startup, watch runs **one full `update_collection` reconcile pass** per watched collection before/alongside going live. This anchors correctness (anything drifted before watch started becomes fresh immediately) and exercises the proven Phase 11 loop. — **Reversibility:** reversible.

**flock discipline for the resident writer**
- **D-04:** Watch **acquires the Phase 11 per-DB flock per debounced work-burst and releases it when idle** — never holds the lock for its process lifetime. Watch is just another `IncrementalIndexer` invoker under the D-01/D-02 (Phase 11) collision contract. Holding for life would push every `sif index update` / `sif embed` past its wait deadline into "proceed unlocked" — reintroducing the duplicate-embed racing LIVE-07 exists to prevent. — **Reversibility:** costly — Phase 13 hosts (MCP-embedded watch, daemon) inherit this discipline; changing it later reworks their lifecycle logic.

**Event→work pipeline**
- **D-05:** Debounce = watchdog's built-in **`EventDebouncer(interval, callback)`, called positionally** (research STACK: first kwarg renamed in 7.0, positional works 3.x–7.x; we are capped `<7`). No hand-rolled timer thread. Default interval from the `watch_debounce_interval` setting (research suggests 0.5–1.0 s; exact default = Claude's discretion).
- **D-06:** After a burst settles, work is **per-path targeted processing, not a full collection scan**. The path — not the event — is the unit of work: for each settled path, stat it; exists + checksum changed → re-index, gone → remove. Rationale: a full `update_collection` pass parses *every* file in the collection (checksums live in parser output), so per-burst full passes re-read the whole KB on every save — Pitfall 3's CPU burn. Cost must be proportional to burst size. — **Reversibility:** costly — the per-path API on `IncrementalIndexer` is consumed by Phase 13 hosts and is exactly what Phase 14's drift refresh (LIVE-10) wants; design its shape with those consumers in mind.
- **D-07:** Event filtering uses **the scanner's exact predicate** — collection `pattern` glob + `DEFAULT_IGNORE_PATTERNS` + per-collection `ignore_patterns` — so live events can never index what a scan would skip (Pitfall 4: today a `private/**`-excluded file gets indexed the moment it's saved). `on_moved` filters on **`dest_path`** (rename *into* the tree is create-equivalent); src-side handling marks the old path for removal.
- **D-08:** The editor-noise patterns (`.swp`, `.sb-*`, `4913`, `.DS_Store`, `~`-suffixed, `.#`-prefixed, `.tmp`) are added to **`FileScanner.DEFAULT_IGNORE_PATTERNS`** so scan and watch share one list (LIVE-04 "identical" by construction, not by duplication). Note the glob `**/*.md` already excludes most of these from scans; the list matters for watch-side events and the few `.md`-suffixed temp names.

**`--embed` depth mechanics (LIVE-05)**
- **D-09:** `--embed` runs **per-file inline inside the same per-burst flock window**, per Phase 11 D-05's locked direction. Sequence per changed file: parse/checksum → BM25/FTS per-file commit (existing D-04 Phase 11 txn) → embed chunks computed **outside any write transaction** (Pitfall 1: never hold a write txn across an embed call) → short vector-write txn. The embedding model lazy-loads on first `--embed` work and stays cached (`EmbeddingManager._model`); watch startup stays BM25-cheap.
- **D-10:** Without `--embed`: changed docs get stale chunks/vectors purged (existing `_process_file` behavior) and BM25/FTS stays fresh. Staleness *visibility* (markers on results) is Phase 14's QUAL-06 — not built here. Accepted trade-off: a large embed burst holds the lock longer, so a concurrent `update_cmd` may wait past its deadline; acceptable because bursts are small after debounce — if it bites, Phase 13 can split embed compute outside the lock.

**Missing-root protection (LIVE-11)**
- **D-11:** **Guard in the shared core:** `IncrementalIndexer` (both `update_collection` and the new per-path path) **skips with a warning — never sweeps — any collection whose root does not exist**. This also fixes a live latent bug: today `update_cmd` on a missing/unmounted root scans empty and mass-deletes that collection's index.
- **D-12:** **Watcher-level recovery:** when a watched root disappears, mark the collection missing, keep a light periodic re-stat (interval = Claude's discretion, seconds-scale), and on return reschedule the watch + run a full reconcile pass for that collection. Warn once per transition, not per poll.

**Foreground UX & shutdown**
- **D-13:** Output reuses the **Phase 11 progress-event protocol** (`"code payload"` events): concise per-batch summary lines (e.g. `indexed N · removed M · unchanged K`) plus a startup banner listing watched roots, depth mode (BM25-only / `--embed`), and debounce interval. `--verbose` yields per-file lines. Exact Rich rendering = Claude's discretion; document content is never Rich-markup-rendered (locked project decision).
- **D-14:** SIGINT/SIGTERM shutdown: stop accepting events, **flush the in-flight debounced batch (bounded)**, release the lock, run `PRAGMA wal_checkpoint(TRUNCATE)` (research recipe; establishes the Phase 13 shutdown precedent), exit 0. A second SIGINT exits immediately without flush.

**Test determinism**
- **D-15:** Event-pipeline tests are **synthetic-event, zero-timing**: construct watchdog event objects (`FileCreatedEvent`/`FileMovedEvent`/…) directly against the handler — atomic-save rename chains, delete+create pairs, temp-file noise — with debounce flushed by invoking the settled callback directly (or an injected clock). 1–2 real-FS end-to-end tests in `tmp_path` (real observer, real `os.replace` atomic save) with generous timeouts, serialized, never sleep-polling without a deadline (Phase 11 D-08/D-09 culture).

**Carried forward (pre-decided in research/roadmap — do not re-litigate)**
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

### Deferred Ideas (OUT OF SCOPE)
- **Live rescope on collection add/remove while watch runs** — Phase 13 daemon/MCP hosts are the long-lived processes where restart-free rescope matters; MVP restarts (D-02).
- **Embed compute split outside the flock window** — only if D-10's lock-hold trade-off bites in practice; revisit with Phase 13's hosts.
- **`wal_checkpoint(TRUNCATE)` periodicity during long runs** — D-14 checkpoints at shutdown; periodic checkpointing is a daemon-era (Phase 13) tuning question.
- **inotify watch-limit detection + `PollingObserver` fallback UX** — research prescribes the fallback exists; polished detection/warning UX can land with Phase 13's Linux daemon testing.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LIVE-01 | 运行 `sif watch` 后，collection 内文件增/改/删自动增量重索引，无需手动 `sif index update` | New `update_paths()` per-path API on `IncrementalIndexer` (§ Pattern 2); rewritten watcher pipeline (§ Pattern 3); CLI host (§ Pattern 6); verified FSEvents event shapes (§ Machine-Verified Evidence) |
| LIVE-02 | 编辑器保存风暴（单次保存 2-5 事件）防抖合并为一次索引操作 | `EventDebouncer` verified in installed 6.0.0 (§ Pattern 3); probe shows bursts arrive at identical timestamps; per-path fold + single worker; LIVE-02 test = synthetic burst driven into handler (§ Validation) |
| LIVE-03 | macOS 原子保存（rename 链）与文件移动/重命名正确处理，不误删不重建 | Probe-captured atomic-save sequence incl. trailing `deleted` after `moved` (§ Machine-Verified Evidence); stat-based reconciliation rule; `dest_path` filtering (D-07); `get_by_path` + path-keyed documents make rename = remove-old + add-new |
| LIVE-04 | 临时文件（`.swp`/`.sb-*`/`4913`/`.DS_Store` 等）与 scanner `ignore_patterns` 一致排除 | `DEFAULT_IGNORE_PATTERNS` verbatim audit (already contains `.DS_Store`, `*.swp`, `*.swo`, `*~`; missing `.sb-*`, `4913`, `.#*`, `*.tmp`); shared-predicate pattern (§ Pattern 4) |
| LIVE-05 | 默认仅更新 BM25/FTS；`--embed` 显式开启向量更新 | `_process_file` purges stale chunks/vectors today (BM25-only default is already the core's behavior); `--embed` composes chunker + `EmbeddingManager` + `VectorSearcher` primitives verified in embed_cmd (§ Pattern 5); embed-outside-txn contrast documented |
| LIVE-11 | collection 根目录消失不解读为全量删除（missing-root 防护） | **Latent bug verified**: `Path.rglob` on missing root returns `[]` (no exception) → `_sweep_removed` deletes every document. Guard in `update_collection` + per-path path (D-11); watcher re-stat recovery (D-12) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

Directives the plan and tasks MUST honor (extracted from `/Users/forrest/GitHub/SIF/CLAUDE.md`):

- **Quality gates:** `ruff check src tests`; `ruff format --check src tests`; `pytest` (fail_under=90, zero exemptions); `ty check src/sif` clean. Full suite after every plan completes within the phase.
- **Style:** Python 3.10+ with `list[str] | None` union syntax; line length 100; max mccabe complexity 10 (no noqa exemptions — Phase 11 split loop bodies into `_process_file`/`_sweep_removed` specifically to stay ≤10); ruff isort `combine-as-imports = true`; stdlib → third-party → first-party (`sif`) order; two blank lines after imports; fully type-annotated functions.
- **CLI conventions:** user-facing errors via `click.ClickException(str(e))`; Click decorators kept as-is (ty needs no decorator relaxations).
- **Transactions:** `Database.transaction()` context manager with automatic rollback; per-file `with conn:` blocks are the established BEGIN IMMEDIATE unit (factory `isolation_level="IMMEDIATE"` makes them so).
- **Logging:** `logger = get_logger(__name__)` module-level; output to stderr; names prefixed `sif`.
- **GSD workflow:** planned phase work via `/gsd-execute-phase`; run the full quality suite before marking each plan done.
- **Generator-owned docs (project memory):** `docs/cli-reference.md` + `docs/configuration.md` are wholesale rewritten by `make docs-generate` under a CI diff gate — the new `sif watch` command and `watch_*` settings appear there via regeneration, **never hand-edited**. A docs-regen step belongs in the final plan's task list.
- **Agent-shell pytest (project memory):** run pytest with `env -u FORCE_COLOR NO_COLOR=1 ...` — unsetting, not `FORCE_COLOR=0`, avoids spurious failures.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Filesystem event capture (FSEvents/inotify) | OS → watchdog `Observer` (process-local) | — | Kernel events; `Observer()` auto-selects `FSEventsObserver` on macOS (verified importable + selected on this machine) |
| Event debouncing | watchdog `EventDebouncer` thread | — | D-05 locked; verified in installed 6.0.0: global quiet-window, delivers ordered event list |
| Event→path folding + exclusion filtering | Watch host (watcher module, debouncer callback) | — | Must run cheaply (callback executes under the debouncer's condition lock — verified); predicate delegates to shared scanner logic (D-07) |
| Per-path reconcile (stat → index/remove) | `IncrementalIndexer` (domain/indexing layer) | — | D-06: same core as `update_cmd`/MCP/Phase 13-14 hosts; presentation-free via progress callback |
| Single-writer arbitration | `index_lock` flock (per-burst in watch) | — | D-04: acquired per settled burst, released when idle |
| BM25/FTS writes | Repositories + FTS5 external-content triggers | — | Per-file `with conn:` blocks; triggers keep `documents_fts` in sync automatically — per-path updates inherit this unchanged |
| Embedding compute + vector writes (opt-in `--embed`) | Watch worker thread (embed outside txn) | `EmbeddingManager` (lazy model cache) | D-09; model never loads at startup; vectors written in short txns via `VectorSearcher` |
| Presentation (banner, per-batch lines, `--verbose`) | CLI `watch.py` command | — | D-13; renders progress-event protocol; core stays Rich-free |
| Signal handling + checkpoint + exit codes | CLI `watch.py` command | — | D-14; empirically verified pattern (§ Pattern 7); no signal handling exists anywhere in `src/sif` today |
| Missing-root guard | `IncrementalIndexer` (shared core) | Watch host (re-stat loop) | D-11 core guard fixes `update_cmd` too; D-12 watcher recovery on return |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| watchdog (existing dep, range tightened) | `>=4.0.0,<7.0.0` (from `>=3.0.0`) | Event source (`Observer`, `EventDebouncer`, event classes) | Already vendored; installed 6.0.0 satisfies the new range. Cap re-verified today: PyPI latest is 7.1.0 (2026-11-04) with `requires-python ">=3.11"` — 7.x cannot install on SIF's 3.10 floor; 6.0.0 remains the newest 3.10-compatible release [VERIFIED: pypi.org/pypi/watchdog/json fetched 2026-11-07] |
| sqlite3 (stdlib) | Python 3.10+ | All DB access via `create_connection()` factory | Phase 11 landed; no new connection sites this phase (D-06 Phase 11) |
| Click (existing) | 8.x (8.3.2 installed) | `sif watch` command | Project CLI standard; signal behavior verified (§ Pattern 7) |
| Rich (existing) | >=13 | Banner + per-batch rendering | Existing `_render_index_event` analog; document content never markup-rendered (locked) |
| signal / queue / threading / os (stdlib) | 3.10+ | SIGINT/SIGTERM handling, burst queue, worker thread, re-stat loop | D-14/D-discretion; zero new deps |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `PollingObserver` (watchdog, existing) | same | Network-FS / inotify-exhaustion fallback | Import path verified (`from watchdog.observers.polling import PollingObserver`); polished detection UX deferred (Phase 13) — MVP keeps default `Observer()` only |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `EventDebouncer` | Hand-rolled `threading.Timer` coalescer | Rejected by D-05 (locked). Also: 6.0.0's EventDebouncer callback runs **under its condition lock** — a hand-rolled version would not change the requirement that the callback stay cheap |
| `PatternMatchingEventHandler` (watchdog) | — | **Rejected by D-07**: its pattern semantics differ from the scanner's part-wise `fnmatch` predicate (and changed to `full_match` in 7.0). Use plain `FileSystemEventHandler` + the shared scanner predicate so parity holds by construction |
| Per-burst flock (D-04) | Hold lock for process lifetime | Rejected (locked D-04) — would push every `sif index update`/`sif embed` past its 30s wait deadline into proceed-unlocked |

**Installation:**
```bash
# No installs. One pyproject.toml edit (line 38):
#   "watchdog>=3.0.0"  ->  "watchdog>=4.0.0,<7.0.0"
# then refresh the lock (uv.lock exists; current entry: specifier ">=3.0.0"):
uv lock
```
[VERIFIED: pyproject.toml line 38 reads `"watchdog>=3.0.0"`; uv.lock entry `{ name = "watchdog", specifier = ">=3.0.0" }` — both read this session]

## Package Legitimacy Audit

> Gate run via `gsd-tools query package-legitimacy check --ecosystem pypi watchdog`. **This phase installs zero new packages** — the only dependency change is a range tightening on an existing, locked dependency.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| watchdog | PyPI | ~15 yrs (active; 7.1.0 released 2026-11-04) | n/a (PyPI JSON API exposes none) | github.com/gorakhargosh/watchdog | SUS (heuristic) | Approved — false positive |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** watchdog — the seam's `too-new`/`unknown-downloads` signals are artifacts: `publishedAt` reflects 7.1.0's recent upload (active maintenance, not slop) and PyPI's JSON API never reports weekly downloads. watchdog has been SIF's dependency since v1.0 (uv.lock), its changelog was raw-fetched from the official repo by the milestone research, and the installed 6.0.0 was inspected source-level this session. No `checkpoint:human-verify` needed.

## Architecture Patterns

### System Architecture Diagram

```
 terminal (Ctrl-C / SIGTERM)
        │ signal
        ▼
┌─────────────────────────── sif watch (CLI host, src/sif/cli/commands/watch.py) ───────────────────────────┐
│                                                                                                            │
│  startup: Database(index_path) → init_schema → CollectionRepository.list_all() (-c filters)              │
│      │                                                                                                    │
│      ├─ missing root? ──no──► D-03: IncrementalIndexer.update_collection(coll)  ◄── full reconcile pass   │
│      │        │                                                                                          │
│      │       yes ► D-11: warn + skip (NEVER sweep); D-12: mark missing, periodic re-stat ──► on return:   │
│      │              reschedule watch + full reconcile                                                    │
│      ▼                                                                                                    │
│  banner (roots, depth, debounce) ──► observer.schedule(handler, root, recursive=True) per collection      │
│                                                                                                            │
│  ┌── watchdog Observer thread (FSEvents/inotify) ──────────────────────────────────────────────┐          │
│  │  raw events ──► handler dispatch ──► EventDebouncer.handle_event()                          │          │
│  └──────────────────────────────────────────────┬──────────────────────────────────────────────┘          │
│                                                 │ after quiet interval (global window)                      │
│                                                 ▼                                                             │
│  ┌── EventDebouncer thread ─────────── callback(events: list) — MUST be cheap (runs under cond lock) ──┐  │
│  │  fold events → candidate paths (moved: dest_path=index-hint, src=remove-hint)                        │  │
│  │  filter via SHARED PREDICATE (pattern + DEFAULT_IGNORE + per-collection + watch extras)              │  │
│  │  push batch onto queue.Queue ──► return                                                              │  │
│  └──────────────────────────────────────────────┬────────────────────────────────────────────────────┘  │
│                                                 ▼                                                           │
│  ┌── single worker thread ──────────────────────────────────────────────────────────────────────────┐    │
│  │  pop batch → index_lock(db_path, timeout) ◄── D-04: per-burst flock                              │    │
│  │      for each settled path:  update_paths(coll, paths)   ◄── D-06: stat = truth                   │    │
│  │          exists + checksum changed → _process_file (per-file BEGIN IMMEDIATE txn)                │    │
│  │          exists + unchanged      → skip                                                           │    │
│  │          gone                    → purge vectors + delete doc (short txn)                         │    │
│  │      [--embed only, D-09]: chunk + embed OUTSIDE txn → short vector-write txn                     │    │
│  │  release lock → progress events → CLI renders "indexed N · removed M · unchanged K"              │    │
│  │  idle: doubles as missing-root re-stat loop (queue.get(timeout=restat_interval))                  │    │
│  └──────────────────────────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                                            │
│  shutdown (D-14): stop accepting events → flush in-flight batch (bounded) → release lock                   │
│      → PRAGMA wal_checkpoint(TRUNCATE) → exit 0   (2nd SIGINT: immediate exit, no flush)                   │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
        │ writes (WAL, busy_timeout=5000, BEGIN IMMEDIATE per file)
        ▼
   sif.db  ◄── concurrent readers: sif search / MCP queries (never blocked > busy_timeout)
   concurrent writers: sif index update / sif embed ──► serialize on the same flock (wait-then-run)
```

Trace LIVE-01 end-to-end: editor save → Observer event → debouncer quiet window → fold+filter → worker → flock → `update_paths` stats the path, checksum-differs, per-file txn commits doc (FTS triggers fire) → lock released → next `sif search` sees the new content. No `sif index update` involved.

### Recommended Project Structure
```
src/sif/
├── cli/commands/watch.py          # NEW — `sif watch` host: banner, signal loop, render, checkpoint
├── indexing/
│   ├── watcher.py                 # REWRITE — handler + debounce wiring + fold + worker (host-agnostic core)
│   ├── incremental.py             # EXTEND — update_paths() + missing-root guard in update_collection
│   └── scanner.py                 # EXTEND — DEFAULT_IGNORE_PATTERNS additions + shared predicate helper
├── config/settings.py             # EXTEND — watch_debounce_interval, watch_ignore_patterns, watch_update_depth
└── (database/, search/, embedding/ unchanged — consume as-is)
tests/unit/indexing/test_watcher.py        # REWRITE (stub tests are mock-based on the old surface)
tests/unit/indexing/test_incremental.py    # EXTEND — update_paths + missing-root guard tests
tests/integration/test_watch_e2e.py        # NEW — 1–2 real-FS observer tests (serialized, generous timeouts)
```

### Pattern 1: Missing-root guard in the shared core (D-11) — fixes a verified latent bug

**What:** At the top of `update_collection()` (and inside the per-path path), if `not Path(collection.path).exists()`: warn, return zero counts, never scan.

**Verified bug (this machine, this session):**
```python
>>> list(Path("/nonexistent-root").rglob("**/*.md"))
[]   # no exception — FileScanner.scan() returns 0 files
```
`update_collection` then computes `scanned_paths = set()` and `_sweep_removed(existing_docs, set())` deletes **every** document of that collection [VERIFIED: src/sif/indexing/incremental.py:122-150 — `update_collection` scans, then `removed = self._sweep_removed(existing_docs, scanned_paths)`; there is no root-existence check anywhere in the method]. An unmounted drive today = silent mass delete via `sif index update`.

**Recommended shape (discretion per CONTEXT):** return `IncrementalResult(0, 0, 0)` after `logger.warning(...)`, and emit an additive progress event `"missing <name>"` so hosts can render it. The existing CLI renderer is safe against unknown codes by construction — `_render_index_event` partitions on space, matches only `"scan"`/`"unchanged"`/`"error"` and otherwise just advances [VERIFIED: src/sif/cli/commands/index.py:159-169].

### Pattern 2: The per-path update API (D-06) — exact integration points

**What:** A second public method on `IncrementalIndexer`, mirroring `update_collection`'s contract but taking explicit paths.

**Verified current API surface (read this session):**
- `IncrementalIndexer.__init__(self, conn: sqlite3.Connection)` — repos, `MarkdownParser`, `_vector_purger` all instance state [VERIFIED: src/sif/indexing/incremental.py:72-85]
- Progress protocol, verbatim from the docstring: ``"scan <n>"`` (scan finished with n files), ``"unchanged <name>"`` (checksum-skip fired), ``"error <message>"`` (per-file parse failure, file skipped), ``"indexed <name>"`` (file added or updated) [VERIFIED: src/sif/indexing/incremental.py:99-105]
- `IncrementalResult` fields, verbatim: `added: int = 0`, `updated: int = 0`, `removed: int = 0` [VERIFIED: src/sif/indexing/incremental.py:42-48]
- `_process_file(file_path, *, collection, existing, force, progress) -> str` returns `"added"`, `"updated"`, or `"skipped"` — already takes the existing doc explicitly, so the per-path method can look up via `DocumentRepository.get_by_path(path, collection_id)` [VERIFIED: src/sif/indexing/incremental.py:158-219; repositories.py:174 `def get_by_path(self, path: str, collection_id: str) -> Document | None`]
- Single-doc removal body exists inside `_sweep_removed`: vector purge **before** doc delete (vec0 rows don't FK-cascade), then `doc_repo.delete(doc.id)` [VERIFIED: src/sif/indexing/incremental.py:221-239]

**Recommended signature (named for Phase 13/14 consumers):**
```python
def update_paths(
    self,
    collection: Collection,
    paths: Iterable[Path],
    *,
    force: bool = False,
    progress: Callable[[str], None] | None = None,
) -> IncrementalResult:
    """Targeted update: for each path, stat it — exists+changed → re-index, gone → remove.

    Cost is proportional to len(paths); never scans the collection tree.
    Collection stats (document_count) refreshed in one short closing transaction,
    mirroring update_collection's tail.
    """
```
Semantics (disk is truth — events are only hints):
- `path.exists()` (after `resolve()`) and predicate-matching → `existing = doc_repo.get_by_path(str(path), collection.id)`; delegate to `self._process_file(...)` (its internal checksum-skip makes unchanged paths free `skipped` outcomes → count as "unchanged" in rendering).
- Not on disk → single-path remove in one short `with self._conn:` block: vector purge then doc delete (extract the `_sweep_removed` inner body into a `_remove_document(doc)` helper both paths share).
- Path exists but fails the shared predicate → ignore (never indexed; handles `.sb-` legs landing on `.md`-named temps).
- Parse failure → `"error <message>"` event, skip (identical to update_collection).

**Why resolve() matters (machine-verified):** see Machine-Verified Evidence — FSEvents delivers realpaths (`/private/var/...`); stored document paths come from `FileScanner.scan()` which does `Path(root_path).resolve()` [VERIFIED: src/sif/indexing/scanner.py:69]. Resolve event paths before `get_by_path` or lookups silently miss.

### Pattern 3: The event pipeline (D-05/D-06) — EventDebouncer verified in installed 6.0.0

Verified from the installed package source (`/Users/forrest/miniconda3/lib/python3.13/site-packages/watchdog/utils/event_debouncer.py`, watchdog 6.0.0):

```python
def __init__(
    self,
    debounce_interval_seconds: 'int',
    events_callback: 'Callable[[list[FileSystemEvent]], None]',
) -> 'None':
```
[VERIFIED: local package source read — signature quoted verbatim]

Three load-bearing semantics:
1. **Global quiet-window, not per-path**: any event resets one timer for ALL pending events; on quiet, the callback receives the whole ordered batch (`"the callback will be called with a list of events in the order in which they were received"` — class docstring). Per-path coalescing therefore happens in YOUR fold, not the debouncer. This is exactly D-06's shape: fold the batch into a set of paths.
2. **The callback runs while holding the debouncer's condition lock** — `run()` executes `self.events_callback(events)` inside `with self._cond:` [VERIFIED: verbatim from the run() source]. Consequence: the callback must only fold + enqueue (microseconds) and return; a slow callback blocks `handle_event()` (event intake) AND `stop()`. Indexing work happens on a separate worker thread (D-discretion "single worker thread").
3. **Interval is runtime-float-compatible**: the annotation says `int` but the value flows only into `threading.Condition.wait(timeout=...)`, which accepts floats — `EventDebouncer(0.5, cb)` works; a falsy interval (0) skips the wait entirely. Pass positionally (D-05).

**Intake:** the handler's `dispatch`/`on_*` methods call `debouncer.handle_event(event)`. Synthetic tests bypass the thread entirely: build event objects, call `handle_event` or invoke the settled callback with a constructed list (D-15). All four event classes construct positionally [VERIFIED: `FileCreatedEvent('/x/a.md')`, `FileModifiedEvent(...)`, `FileDeletedEvent(...)`, `FileMovedEvent(src, dest)` with `.dest_path` and `.is_directory` attributes — constructed on this machine].

**Fold rule (stat-reconciles-noise):** per batch —
- `moved(src → dest)`: dest (predicate-checked) joins the index-candidate set; src joins the remove-candidate set (only if it previously could have been indexed — its predicate check for removal uses the same predicate; never-indexed temps are harmless no-op removes).
- `created`/`modified`: src joins index-candidates.
- `deleted`: src joins remove-candidates.
- A path in BOTH sets (the atomic-save trailing `deleted` after `moved→path`, or the in-place `created`+`modified` pair) is fine: `update_paths` stats the path once and lets disk state decide. **Never** process events sequentially with per-event semantics.

### Pattern 4: One shared exclusion predicate (D-07/D-08)

**Verified current state of `DEFAULT_IGNORE_PATTERNS`** (tuple, verbatim) [VERIFIED: src/sif/indexing/scanner.py:26-48]:
```python
DEFAULT_IGNORE_PATTERNS = (
    "node_modules", ".git", ".svn", ".hg", "__pycache__", ".pytest_cache",
    ".tox", ".venv", "venv", "env", ".env", "dist", "build", "*.egg-info",
    ".DS_Store", "Thumbs.db", "*.swp", "*.swo", "*~", ".idea", ".vscode",
)
```
Already covered from D-08's list: `.DS_Store` (`".DS_Store"`), `.swp` (`"*.swp"`), `~`-suffixed (`"*~"`). **Missing — add:** `"*.sb-*"` (hmm — see note), `"4913"`, `".#*"`, `"*.tmp"`. Note on `.sb-*`: fnmatch patterns match path *parts*, the full rel path, and the filename [VERIFIED: `_should_ignore` at scanner.py:93-124 checks `fnmatch.fnmatch(part, pattern)`, `fnmatch.fnmatch(str(rel_path), pattern)`, and `fnmatch.fnmatch(file_path.name, pattern)`]. `"*.sb-*"` matches the filename `note.md.sb-ABCD1234`. Quote the exact added patterns in the plan: `(".sb-*", "4913", ".#*", "*.tmp")` — `".sb-*"` (leading dot form) also works since fnmatch `*` matches the `note.md` prefix only in the `"*.sb-*"` form; pick `"*.sb-*"` to match both `x.sb-123` and `.sb-123` shapes.

**Critical subtlety — the pattern half of the predicate lives OUTSIDE `_should_ignore`:** `FileScanner.scan()` applies the collection `pattern` (default `"**/*.md"`) via `root_path.rglob(pattern)` [VERIFIED: scanner.py:80]; `_should_ignore` only checks ignore patterns. A shared predicate reusable by the handler must therefore check BOTH: (a) pattern match (e.g. via `PurePath.full_match`-equivalent for `**` globs or a suffix/`fnmatch` translation), and (b) `_should_ignore` with the collection root. Recommended placement (discretion): a `FileScanner.matches(root_path, file_path, pattern, ignore_patterns) -> bool` (or module-level helper) that `scan()` and the watch handler both call — "one predicate" by construction. Mirror-update test: for a parametrized path list, `scan()` output membership == `matches()` True (LIVE-04's parity proof).

**Do NOT use `PatternMatchingEventHandler`** (supersedes STACK.md's earlier suggestion): its pattern semantics differ from this predicate and changed again in 7.0; D-07 locks the scanner predicate.

**Watch-scope shaping honesty (Pitfall 4):** watchdog's `schedule()` has no subtree-exclusion API — a recursive watch burns one inotify descriptor per directory on Linux, including ignored ones, and handler-side filtering cannot prevent that. MVP accepts this (personal-KB scale); `PollingObserver` fallback UX is deferred (CONTEXT deferred list). The predicate still pays off on the event side (no ignored file ever reaches the fold) and would be where any future scope-shaping hooks in.

**`watch_ignore_patterns` settings-field semantics (carried-forward field, exact meaning = discretion):** to preserve D-07/D-8 "identical by construction", patterns from `SIF_WATCH_IGNORE_PATTERNS` must extend the **shared** predicate (affecting scan AND watch), functioning as a user-global addition to `DEFAULT_IGNORE_PATTERNS` — NOT as a watch-only filter, which would create scan/watch divergence. Alternatively the plan may drop the field for MVP and rely on per-collection `ignore_patterns`; either satisfies the locked "one predicate" rule, but the carried-forward list names the field, so recommend: field exists, semantics = global ignore extension applied inside the shared predicate.

### Pattern 5: `--embed` inline depth (D-09) — compose existing primitives, but NOT embed_cmd's transaction shape

**Verified primitives** (all read this session):
- Chunker: `create_chunker(strategy)` — strategies `"fixed"`, `"markdown"`, `"code"`, `"auto"` [VERIFIED: src/sif/indexing/chunker.py:210-228]; usage: `chunks = chunker.chunk(doc.content)`, then `chunk.document_id = doc.id; chunk.sequence = i` [VERIFIED: index.py:337-342]
- Embedder: `EmbeddingManager.from_settings(settings)`; `load_model()` is **idempotent** (`if self._model is not None: return`), model cached in `self._model` [VERIFIED: src/sif/embedding/manager.py:43,75-77]; `embed(texts)` itself calls `load_model()` (line 120); `get_model_info()` returns `"embedding_dim"` [VERIFIED: manager.py:231-246]
- Vectors: `VectorSearcher(db, embedding_dim=768)` raises RuntimeError without sqlite-vec [VERIFIED: src/sif/search/vector.py:15-22]; `add_embeddings_batch(items: list[tuple[str, str, str | None, list[float]]])` where each item is `(embedding_id, document_id, chunk_id, embedding_vector)` [VERIFIED: vector.py:175-181]; `delete_embeddings_by_document(document_id) -> int` [VERIFIED: vector.py:195]
- Chunks: `DocumentChunkRepository.create(chunk)`, `delete_by_document(document_id)`, `get_by_document(document_id)` [VERIFIED: repositories.py:303,345,333]

**The contrast that matters (planner beware):** `embed_cmd` runs `manager.embed(chunk_texts)` **inside** its per-collection `with db.connection:` block [VERIFIED: index.py:323 block opens; the `manager.embed` call sits at index.py:347 inside it] — Phase 03's locked structure, safe only because of flock arbitration. The watch `--embed` path must NOT copy that shape: D-09 mandates parse/checksum → BM25 per-file commit (existing `_process_file` txn) → **chunk+embed with no write transaction open** → short vector-write txn (`chunk_repo.create` loop + `add_embeddings_batch` inside one `with conn:`). This also means the embed path lives OUTSIDE `IncrementalIndexer`'s BM25-only core (whose module docstring says "The loop is BM25-only; embedding work stays in `embed_cmd`" [VERIFIED: incremental.py:12]) — recommended: an embed step in the watch worker (or a small `--embed` helper module the worker calls), keeping the core's Phase 11 contract intact. Dimension checking: reuse embed_cmd's probe-free pattern (`get_model_info()["embedding_dim"]` + vec0 `FLOAT[n]` regex check) at first `--embed` use, not at startup.

### Pattern 6: The CLI host (D-01/D-03/D-13)

Structural analogs verified: command modules live in `src/sif/cli/commands/`, registered in `main.py` via `cli.add_command(...)` with `ctx.obj["index_path"]` a `Path` [VERIFIED: main.py:75,96-104]. `sif watch` is a top-level command (like `ls_cmd`/`pull_cmd`), not a subcommand.

- Collections: `CollectionRepository.list_all()` — mirror `update_cmd` exactly (it uses `list_all()`, NOT `list_enabled()`: `list_enabled` filters `include_by_default = 1` [VERIFIED: index.py:70; repositories.py:106-111], and a collection excluded from default search still needs watching — D-01 "all registered").
- Zero collections: recommend printing the same "No collections found" notice as `update_cmd` and exiting 0 (watching nothing is useless; D-02 requires restart after `collection add` anyway). Discretion.
- Pre-update hooks: watch does NOT run `_run_pre_update_hook` — its docstring explicitly reserves that as CLI-update policy: "watch hosts (Phases 12-13) decide their own pre-behavior" [VERIFIED: index.py:114-119].
- `Collection` fields available for banner/predicate: `name`, `path`, `pattern` (default `"**/*.md"`), `ignore_patterns` (list), `include_by_default`, `pre_update_cmd`, `document_count`, `chunk_count`, `last_indexed_at` [VERIFIED: src/sif/core/models.py:34-49].

### Pattern 7: Signal-driven shutdown (D-14) — empirically verified

Machine-tested this session (macOS, click 8.3.2, real `kill -INT`/`kill -TERM` against a Click command with a handler):
- `signal.signal(SIGINT/SIGTERM, handler)` inside the command body intercepts **before** Click's standalone-mode path — click 8.3.2 wraps invocation in `except (EOFError, KeyboardInterrupt) → raise Abort()` [VERIFIED: click/core.py source read], but a custom handler prevents the KeyboardInterrupt from ever propagating.
- Graceful handler (set flag → loop exits → flush → `sys.exit(0)`): **exit code 0**.
- Second-signal branch (`sys.exit(130)`): **exit 130**.
- SIGTERM symmetric: **exit 0**.
- Without a handler, SIGINT would surface as Click's `Aborted!` with nonzero exit — the reason the handler is required.

Sequence inside the handler/teardown: set stop flag → `observer.stop()` → `debouncer.stop()` → drain the queue **once, bounded** (e.g. one final batch with a short timeout — the in-flight batch only; never wait for new events) → `observer.join(timeout)` / worker join → `PRAGMA wal_checkpoint(TRUNCATE)` on the connection → close. `wal_checkpoint` appears nowhere in `src/sif` or `tests/` today (grep-verified) — D-14 introduces it; put it on the same connection the worker used, after the worker has quiesced, inside `try/finally` so Ctrl-C-during-flush still checkpoints best-effort.

### Anti-Patterns to Avoid
- **Per-event sequential processing** (act inside `on_modified` directly): the probe's trailing `deleted` after `moved→path` and the `created`+`modified` pair on plain appends make per-event semantics wrong, not just wasteful. Fold by path; stat decides.
- **Event paths used unresolved**: FSEvents realpaths (`/private/var/...`) never prefix-match a stored `/var/...` path. Resolve both sides.
- **Slow work in the EventDebouncer callback**: it runs under the debouncer's condition lock (verified) — blocks intake and stop. Callback folds and enqueues only.
- **Indexing on the observer/emitter thread**: sqlite3 connections are thread-bound; `check_same_thread=False` is set by the factory but a connection must not be shared mid-transaction across threads. One worker thread owns the DB work (writes off the observer thread — carried-forward decision).
- **Full `update_collection` per burst**: re-parses the entire collection (checksums live in parser output — D-06 rationale). Only the startup pass (D-03) and missing-root recovery (D-12) use the full pass.
- **Holding the flock for the process lifetime**: pushes every concurrent `sif index update`/`sif embed` past the 30 s `lock_wait_timeout` into proceed-unlocked (verified: settings.py:36-41 default `30.0`; locking.py deadline-expiry breaks to the yield).
- **Hand-editing `docs/cli-reference.md`/`docs/configuration.md`**: generator-owned (`make docs-generate`), CI diff-gated.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Event coalescing/debounce | `threading.Timer` dict-per-path machinery | `watchdog.utils.event_debouncer.EventDebouncer` | D-05 locked; built-in thread, battle-tested; verified present with positional signature in 4.x–6.x |
| OS event backend selection | Per-OS observer picking | `Observer()` default | Auto-selects FSEvents/inotify/ReadDirectoryChangesW (FSEventsObserver confirmed selected on this machine) |
| File-change detection | mtime trackers / content watchers | Existing checksum skip inside `_process_file` | Unchanged paths are free no-ops; idempotent re-index |
| Incremental write loop | New per-event indexing code | `IncrementalIndexer` + new `update_paths` | One loop for all hosts (SC3's whole point); triggers keep FTS in sync automatically |
| Writer arbitration | PID files / polling locks | `index_lock flock | Locked decision (REQUIREMENTS Out of Scope rejects custom lockfiles); kernel releases on death |
| Graceful shutdown | Daemonization frameworks | stdlib `signal` + Click | Verified exit-code behavior; `--detach` is Phase 13 |
| CLI docs for the new command | Manual doc edits | `make docs-generate` | CI diff gate fails hand-edits |

**Key insight:** every hard problem in this phase (debounce, atomic-save reconciliation, single-writer, WAL concurrency, graceful drain) already has a landed mechanism from Phase 11 or the milestone research; the phase's risk is concentrated in the fold/reconcile semantics and lifecycle glue, which is exactly where the tests must aim.

## Machine-Verified Evidence (FSEvents probe, this host, watchdog 6.0.0)

Real `Observer` + `FSEventsObserver`, real filesystem ops in a temp dir under `/var/folders/...` (macOS). Paths shortened (`root` → `.`). [VERIFIED: probe run 2026-11-07, /tmp/watch-probe/probe_events.py]

| Operation | Delivered events (in order) |
|-----------|------------------------------|
| **Startup** (observer armed over existing `note.md`) | `created .` , `modified .`, `created ./note.md`, `modified .` — **pre-existing files arrive as `created`** |
| **Atomic save** (`write note.md.sb-ABCD1234` + `os.replace` over `note.md`) | `created ./note.md.sb-ABCD1234` → `modified ./note.md.sb-ABCD1234` → `moved ./note.md.sb-ABCD1234 -> ./note.md` → `modified ./note.md` → **`deleted ./note.md`** (trailing delete of the final path AFTER the moved event) |
| **In-place append** (`open(a)`) | `modified ./note.md` → `created ./note.md` (created AND modified for a plain append) |
| **Rename** (`os.rename note.md → renamed.md`) | `modified ./note.md` → `moved ./note.md -> ./renamed.md` |
| **Delete** (`unlink`) | `deleted ./renamed.md` → `modified .` |
| **New subdir + file** | `created ./subdir` (dir) → `modified ./subdir` (dir) → `created ./subdir/new.md` → `modified ./subdir` → `modified ./subdir/new.md` — recursive watch covers new subtrees (D-01 confirmed) |
| **Path spelling** | Watched root given as `/var/folders/...`; events arrive as `/private/var/folders/...` — **FSEvents canonicalizes to realpath** |

Direct consequences: (1) the trailing `deleted ./note.md` in the atomic-save chain is why per-event semantics cannot work and D-06's stat reconciliation can (path exists → re-index; the delete is noise); (2) the `.sb-` legs are dropped by predicate, leaving `note.md` as the only surviving candidate — exactly one re-index; (3) startup `created` bursts make D-03's startup reconcile semantically necessary (it also absorbs them via checksum); (4) directory `modified` events fire on every child change — `event.is_directory` must be skipped (current stubs already do).

**Caveat:** probe is macOS/FSEvents only. Linux/CI (inotify) event shapes differ in detail (e.g. `FileClosedEvent` exists only on inotify; moved events pair differently) — synthetic tests should assert on FOLD outcomes (stat-decided), not raw sequences, so they stay backend-agnostic. [ASSUMED] for inotify specifics.

## Common Pitfalls

### Pitfall 1: Startup `created` burst re-indexes everything (or confuses the handler)
**What goes wrong:** The observer emits `created` for pre-existing files at arming (probe-verified). A handler treating `created` as "new file → full parse + index" burns a full parse of the KB seconds after every `sif watch` start; worse, a handler that counted events would report phantom adds.
**Why it happens:** FSEvents snapshot/historic-window behavior; watchdog 6.0.0 does not fully suppress it (probe shows the burst).
**How to avoid:** Run D-03's startup reconcile FIRST, then arm the observer — by the time the startup burst lands, checksums match and `_process_file`'s skip path makes every event a free no-op. Per-path fold + checksum skip absorbs the rest.
**Warning signs:** `indexed N` counts at startup ≈ total docs; CPU spike on `sif watch` start.

### Pitfall 2: Event paths vs stored paths — the realpath mismatch
**What goes wrong:** Events arrive realpath-canonicalized (`/private/var/...`) while `collection.path` may be spelled through a symlink; `str.startswith` or `get_by_path` with the unresolved spelling silently matches nothing — watch "runs" but never indexes.
**Why it happens:** FSEvents canonicalizes (probe-verified); `FileScanner.scan()` resolves [VERIFIED: scanner.py:69] so stored doc paths are resolved.
**How to avoid:** `Path(collection.path).resolve()` at watch setup (schedule the resolved path); resolve event paths before predicate/fold; `get_by_path` with resolved strings. Test in `tmp_path` (which IS `/private/var/...` on macOS — the probe's exact condition).
**Warning signs:** integration test flakiness where the same code passes on Linux and misses on macOS.

### Pitfall 3: Slow EventDebouncer callback deadlocks stop()
**What goes wrong:** Indexing inside the debouncer callback blocks `handle_event` and `stop()` (callback runs under the condition lock — source-verified), so Ctrl-C hangs.
**How to avoid:** Callback = fold + filter + enqueue, nothing else. Worker thread does all DB work.
**Warning signs:** `sif watch` not exiting on Ctrl-C; events stopping during a long burst.

### Pitfall 4: Missing root = mass delete (the D-11 bug)
**What goes wrong:** `rglob` on a missing root returns `[]` (verified) → sweep removes every doc of that collection. An unmounted USB drive or renamed root silently destroys that collection's index via a routine `sif index update`.
**How to avoid:** Guard at the top of `update_collection` AND the per-path path (a per-path event on a missing root should also not be interpreted as thousands of deletes — if the root is missing, skip with the same warning).
**Warning signs:** `removed` counts equal to document totals after a mount glitch.

### Pitfall 5: `--embed` copied from embed_cmd's transaction shape
**What goes wrong:** embed_cmd computes embeddings inside its per-collection transaction (verified) — copying that into watch holds a write txn across model inference per file, blocking all writers for seconds per save.
**How to avoid:** D-09's sequence: BM25 commit first (existing `_process_file` txn), then chunk+embed with NO txn open, then one short vector-write txn.
**Warning signs:** concurrent `sif search` latency spikes during `--embed` watch bursts.

### Pitfall 6: Watch handler bypasses collection ignore rules
**What goes wrong:** Extension-only filtering (the current stub's `_should_handle`) lets a `private/**`-excluded file get indexed the moment it's saved (milestone Pitfall 4).
**How to avoid:** The shared predicate (Pattern 4) is the ONLY filter; delete `_should_handle`'s extension-set approach in the rewrite.
**Warning signs:** docs in the index that `sif index update` would skip.

### Pitfall 7: Directory events and directory renames
**What goes wrong:** Dir `modified` events fire constantly (probe); processing them spams the fold. Conversely a directory RENAME emits a dir `moved` event whose children get no individual events — children's old paths are now stale but nothing removes them until a full pass.
**How to avoid:** Skip `is_directory` events on intake. For dir moves, accept MVP drift: the next startup reconcile (or Phase 14's drift detection) heals it; optionally treat a dir `moved` as "schedule a full reconcile for that collection" — planner's call, document whichever.
**Warning signs:** ghost docs after folder renames (known MVP limitation if unreconciled).

### Pitfall 8: Second SIGINT during flush corrupts the drain contract
**What goes wrong:** Handler waits forever if the worker is stuck on the lock (a concurrent `sif embed` holding the flock past its own deadline); or double-Ctrl-C leaves the WAL uncheckpointed and exit code wrong.
**How to avoid:** Bounded flush (one queue drain with short timeout); second signal = immediate exit (verified 130 pattern); checkpoint in `finally`.
**Warning signs:** tests hanging on shutdown; exit code 1 on clean Ctrl-C.

## Code Examples

### The debouncer wiring (verified against installed watchdog 6.0.0)
```python
# Source: watchdog 6.0.0 installed source (signature quoted verbatim in Pattern 3) + STACK.md recipe
from watchdog.observers import Observer
from watchdog.utils.event_debouncer import EventDebouncer

observer = Observer()                        # FSEvents on macOS, inotify on Linux
debouncer = EventDebouncer(interval_s, on_burst)   # POSITIONAL (D-05); float OK (see Pattern 3.3)
handler = WatchHandler(predicate=..., enqueue=debouncer.handle_event)
for coll in collections:
    if root_exists(coll):
        observer.schedule(handler, str(Path(coll.path).resolve()), recursive=True)
observer.start()
debouncer.start()
# shutdown: observer.stop(); debouncer.stop(); join both; drain once (bounded); checkpoint
```

### The synthetic-event test pattern (D-15 — extend Phase 11's culture)
```python
# Source: verified event constructors (this machine) + CONTEXT <specifics> construction note
from watchdog.events import (
    FileCreatedEvent, FileDeletedEvent, FileModifiedEvent, FileMovedEvent,
)

def test_atomic_save_chain_reconciles_to_one_reindex(handler, indexer, tmp_path):
    note = tmp_path / "notes" / "file.md"
    # macOS atomic save, per the FSEvents probe (trailing delete included):
    burst = [
        FileCreatedEvent(str(tmp_path / "notes" / "file.md.sb-ABCD")),
        FileModifiedEvent(str(tmp_path / "notes" / "file.md.sb-ABCD")),
        FileMovedEvent(str(tmp_path / "notes" / "file.md.sb-ABCD"), str(note)),
        FileModifiedEvent(str(note)),
        FileDeletedEvent(str(note)),   # trailing noise — must NOT win
    ]
    handler.fold(burst)                       # drive the settled-callback path directly; zero timing
    result = indexer.update_paths(collection, handler.candidate_paths())
    assert result.added + result.updated == 1 # exactly one index operation
    assert result.removed == 0                # no spurious delete + rebuild
    # burst-count assertion for LIVE-02: count indexer invocations, not events
```

### The signal/shutdown skeleton (verified exit codes: 0 graceful / 130 second / 0 TERM)
```python
# Source: /tmp/watch-probe/test_sigint.py — run against real signals on this machine
import signal, sys, click

@stop_flag_machinery
def watch_cmd(...):
    state = {"stop": False, "sigs": 0}
    def _handle(signum, frame):
        state["sigs"] += 1
        if state["sigs"] >= 2:
            sys.exit(130)          # second signal: immediate, no flush
        state["stop"] = True       # first: graceful drain begins
    signal.signal(signal.SIGINT, _handle)
    signal.signal(signal.SIGTERM, _handle)
    ...run loop until state["stop"]...
    ...drain one bounded batch, release lock...
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")   # D-14 — new; exists nowhere today
    sys.exit(0)
```

### The embed-outside-txn shape (D-09; contrast with embed_cmd)
```python
# BM25 leg: existing per-file txn (incremental.py _process_file) — commit.
# Vector leg: NO write txn open during compute.
chunks = chunker.chunk(doc.content)             # outside txn
vectors = manager.embed([c.content for c in chunks])   # outside txn — model lazy-loaded once
with conn:                                       # short vector-write txn
    for i, chunk in enumerate(chunks):
        chunk.document_id = doc.id; chunk.sequence = i
        chunk_repo.create(chunk)
    vector_searcher.add_embeddings_batch([(c.id, doc.id, c.id, e) for c, e in zip(chunks, vectors)])
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| watchdog `>=3.0.0` unversioned (split-brain 6.x/7.x across interpreters) | `>=4.0.0,<7.0.0` cap | 7.0.0 released 2026-10-31 (dropped py3.10) | Lockfile resolves identically everywhere; 7.x `full_match` pattern semantics excluded while on 3.10 |
| STACK.md's `PatternMatchingEventHandler` suggestion | Scanner-predicate filtering (D-07) | Phase 12 context | Parity by construction; immune to 7.0 semantics change |
| Milestone-research event narratives | Probe-verified sequences (this research) | 2026-11-07 | Startup burst, realpath, trailing-delete facts now fixture-grade |

**Deprecated/outdated:** `.planning/codebase/*.md` maps (April-era) predate Phase 11 entirely — `incremental.py`, `locking.py`, `factory.py` do not exist in them; trust the source tree (this research cites file:line for every integration point).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Linux/inotify event details differ from the macOS probe (no inotify probe run) | Machine-Verified Evidence | Low — tests assert fold outcomes, not raw sequences; CI on Linux exercises the real-FS e2e |
| A2 | `sif watch` exits 0 with a notice when zero collections registered (discretion recommendation, not user-locked) | Pattern 6 | Trivial UX choice; revisit in UAT |
| A3 | Debounce default 0.5 s is the right default (discretion; STACK suggests 0.5–1.0, watchdog recipe uses 1 s) | Standard Stack | Tunable via `SIF_WATCH_DEBOUNCE_INTERVAL`; low |
| A4 | `watch_ignore_patterns` semantics = global ignore extension applied to BOTH scan and watch (carried-forward names the field; exact meaning was unresolved) | Pattern 4 | Medium — if the plan instead makes it watch-only, LIVE-04 "identical" breaks; the recommendation preserves parity |
| A5 | Recommended API name `update_paths` / event code `"missing"` (discretion areas) | Patterns 1-2 | Low — internal naming; Phase 13/14 consume it, so decide once here |
| A6 | Dir-move handling choice (skip vs schedule-reconcile) left to planner within the documented options | Pitfall 7 | Low for MVP; SC2 covers file moves, not dir moves |
| A7 | `queue.get(timeout=restat_interval)` worker-idle re-stat is the D-12 recovery loop shape (discretion) | Pattern 3/D-12 | Low — alternative is a dedicated timer thread |
| A8 | Checkpoint on the worker's connection after quiesce is sufficient (no second connection needed) | Pattern 7 | Low — SQLite checkpointing works from any connection; worst case the -wal file stays larger until next open |

## Open Questions

1. **Does CI run Linux inotify e2e for the real-FS watch tests?**
   - What we know: `tests/integration/` exists with Phase 11 subprocess tests; probe was macOS-only.
   - What's unclear: whether GitHub CI's Linux runner will exercise the real-FS watch test with inotify (and how its event shapes differ).
   - Recommendation: write the e2e test to await the *outcome* (doc indexed) with a deadline, not specific event types; it then passes on both backends. Keep it serialized with generous timeout (D-15).
2. **`watch_update_depth` setting vs `--embed` flag precedence:**
   - What we know: carried-forward names a settings field for update-depth default; D-09 names `--embed` as the opt-in flag.
   - What's unclear: whether `SIF_WATCH_UPDATE_DEPTH=embed` should make `--embed` the default (flag then becomes a no-op/override-off?).
   - Recommendation: setting sets the default depth (`"bm25"` | `"embed"`); `--embed` flag forces embed on; add `--no-embed` for forcing off — planner decides the exact matrix; keep LIVE-05's invariant (never embed unless explicitly opted in via flag OR setting).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| watchdog | event pipeline | ✓ | 6.0.0 installed (satisfies `>=4.0.0,<7.0.0`) | — |
| Python | all | ✓ | 3.13.9 dev (project floor 3.10) | — |
| pytest + pytest-cov | quality gate | ✓ | pytest 9.1.1 | — |
| ruff | lint/format gate | ✓ | 0.15.11 | — |
| ty | typecheck gate | ✓ | 0.0.97 | — |
| uv | lock refresh after pyproject bump | ✓ | uv.lock present | regenerate via `uv lock` |
| macOS FSEvents | dev-machine UAT + probe | ✓ | FSEventsObserver confirmed selected | inotify on Linux CI |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + pytest-cov (addopts: `--cov=src/sif --cov-report=term-missing --cov-report=html --cov-report=xml`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (testpaths `tests`, `fail_under=90` in `[tool.coverage.report]`) |
| Quick run command | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/test_watcher.py -x -q --no-cov` |
| Full suite command | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` |

(Env prefix per project memory: agent shells must UNSET `FORCE_COLOR` — `"0"` still fails — and set `NO_COLOR=1`.)

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LIVE-01 | created/modified/deleted → auto re-index (no manual update) | unit (synthetic events → `update_paths`) + integration (real FS) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/test_incremental.py -k update_paths -x` ; `... pytest tests/integration/test_watch_e2e.py -x` | ❌ Wave 0 (extend existing file / new e2e file) |
| LIVE-02 | 2–5-event save burst → exactly one index operation | unit (burst fold; count `update_paths` calls or summed counts) | `... pytest tests/unit/indexing/test_watcher.py -k burst -x` | ❌ Wave 0 (rewrite) |
| LIVE-03 | atomic-save rename chain + moves/renames reconcile; no spurious delete+rebuild | unit (probe-sequence fixture incl. trailing delete; moved dest_path filtering) | `... pytest tests/unit/indexing/test_watcher.py -k "atomic or moved or rename" -x` | ❌ Wave 0 |
| LIVE-04 | temp files never indexed; parity with scanner predicate | unit (parametrized `.swp/.sb-*/4913/.DS_Store/.#*/.tmp` + parity test scan-vs-predicate) | `... pytest tests/unit/indexing/test_scanner.py tests/unit/indexing/test_watcher.py -k "ignore or temp or parity" -x` | ❌ Wave 0 (extend scanner tests) |
| LIVE-05 | default BM25-only; `--embed` opt-in writes vectors; embed outside txn | unit (no chunks created default; with embed → chunks+vectors; txn-boundary assertion via mocked embedder) | `... pytest tests/unit/indexing/test_watcher.py -k embed -x` | ❌ Wave 0 |
| LIVE-11 | missing root: no sweep, docs survive; recovery on return | unit (`update_collection` missing-root guard) + unit (watcher re-stat transition, warn-once) | `... pytest tests/unit/indexing/test_incremental.py -k missing -x` | ❌ Wave 0 |
| SC1-5 (roadmap) | end-to-end real-FS proof | integration (real Observer + `os.replace` atomic save in `tmp_path`, serialized, deadline-bounded) | `... pytest tests/integration/test_watch_e2e.py -x` | ❌ Wave 0 |
| Shutdown (D-14) | SIGINT flush+exit 0; 2nd SIGINT immediate 130; checkpoint runs | unit/integration (drive the shutdown function with the stop-flag machinery; subprocess signal test optional) | `... pytest tests/unit/cli/test_watch_cmd.py -k shutdown -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/ tests/unit/cli/ -x -q --no-cov` (+ the touched files' targeted runs)
- **Per wave merge:** `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` + `ruff check src tests` + `ruff format --check src tests` + `ty check src/sif`
- **Phase gate:** full suite green before `/gsd-verify-work`; docs regenerated (`make docs-generate`) with diff reviewed

### Wave 0 Gaps
- [ ] `tests/unit/indexing/test_watcher.py` — REWRITE: current 396 lines are mock-based against the stub surface (`_extensions`, MagicMock events, Observer patching); the rewrite deletes/replaces them per Phase 11 11-03's same-commit RED culture (deleted tests must not import removed symbols)
- [ ] `tests/unit/indexing/test_incremental.py` — EXTEND: `update_paths` + missing-root guard + per-path remove cases
- [ ] `tests/unit/indexing/test_scanner.py` — EXTEND: new `DEFAULT_IGNORE_PATTERNS` entries + shared-predicate parity test
- [ ] `tests/integration/test_watch_e2e.py` — NEW: 1–2 real-FS tests (real Observer, `os.replace` chain, deadline-bounded polling for the indexed outcome, serialized)
- [ ] `tests/unit/cli/test_watch_cmd.py` — NEW: banner/flag surface + shutdown machinery (signal handler logic tested via direct invocation of the stop-flag path; the subprocess-signal variant is optional)
- [ ] No framework install needed — pytest/pytest-cov already configured

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Local single-user CLI; no auth surface added |
| V3 Session Management | no | No sessions |
| V4 Access Control | no | No multi-user surface; watch reads only registered collection roots (D-01 anti-scope-creep) |
| V5 Input Validation | yes | FS event paths are externally-shaped input: handled via `Path.resolve()` + fnmatch predicate (no shell interpolation, no eval); document content parsed by the existing MarkdownParser and never logged (per milestone security note: log paths at debug, never content); document content never Rich-markup-rendered (locked decision, D-13) |
| V6 Cryptography | no | None added |
| V12 File & Resources | yes | Watch scope strictly registered roots; temp/pattern exclusions prevent junk ingestion; bounded flush prevents unbounded memory from event storms |

### Known Threat Patterns for filesystem-watch indexing (local, single-user)

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Pathological filenames from events (huge names, non-UTF8 bytes) | Tampering/DoS | `os.fsdecode` normalization (existing `_event_path` helper), predicate fnmatch, length-tolerant logging; no string interpolation into SQL (repositories are parameterized) |
| Event-storm memory growth | DoS | Debounce coalesces; fold dedupes to a path SET; bounded shutdown flush; queue bounded naturally by burst size |
| Log content leakage (note text in logs) | Information disclosure | Log paths (debug), never parsed content — milestone Security Mistakes table |
| Symlinked watch paths escaping intended roots | Tampering | Watch the RESOLVED root only; recursive watch stays under it; never watch anything beyond registered collections (locked) |
| Lock file tampering (flock file) | Tampering | Already mitigated in Phase 11: created 0600, path resolved [VERIFIED: locking.py:42-70] |

## Sources

### Primary (HIGH confidence)
- SIF source tree, read this session with line citations: `src/sif/indexing/incremental.py`, `src/sif/database/locking.py`, `src/sif/database/factory.py`, `src/sif/database/database.py`, `src/sif/indexing/watcher.py`, `src/sif/indexing/scanner.py`, `src/sif/cli/commands/index.py`, `src/sif/cli/main.py`, `src/sif/config/settings.py`, `src/sif/core/models.py`, `src/sif/database/repositories.py`, `src/sif/search/vector.py`, `src/sif/embedding/manager.py`, `src/sif/indexing/chunker.py`, `pyproject.toml`, `uv.lock`, `tests/unit/indexing/*`, `tests/integration/`
- Installed watchdog 6.0.0 source: `watchdog/utils/event_debouncer.py` (signature + run() semantics quoted verbatim); event-class constructors constructed live; `Observer`/`PollingObserver` imports verified
- Local machine probes (macOS, 2026-11-07): FSEvents event-sequence probe (/tmp/watch-probe/probe_events.py); `rglob`-on-missing-root behavior; Click 8.3.2 SIGINT/SIGTERM exit-code test (/tmp/watch-probe/test_sigint.py)
- PyPI JSON API `pypi.org/pypi/watchdog/json` (fetched 2026-11-07): latest 7.1.0, `requires_python ">=3.11"`
- `gsd-tools query package-legitimacy check --ecosystem pypi watchdog`

### Secondary (MEDIUM confidence)
- `.planning/research/STACK.md`, `PITFALLS.md`, `FEATURES.md`, `SUMMARY.md` (same-day milestone research, primary-sourced) — watchdog version matrix, WAL recipes, pitfall narratives; cross-checked against the live tree this session (all integration points still accurate except where superseded: `connection.py` pragma guidance is now landed as `factory.py`; `PatternMatchingEventHandler` suggestion superseded by D-07)
- `.planning/phases/11-.../11-CONTEXT.md` — lock contract D-01..D-05, write granularity, test culture

### Tertiary (LOW confidence)
- None load-bearing; A1 (inotify shape differences) is the only [ASSUMED] external-behavior claim

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new deps; cap re-verified against PyPI today; installed package source-verified
- Architecture: HIGH — every integration point read from the post-Phase-11 tree with line numbers; API shapes quoted verbatim
- Pitfalls: HIGH — three of the four novel pitfalls (startup burst, realpath, trailing-delete) are machine-probe findings, not literature claims
- Validation: HIGH — test map maps 1:1 to requirement IDs; existing test files/patterns inspected

**Research date:** 2026-11-07
**Valid until:** 2026-12-07 (stable local domain; watchdog cap re-check only if a 6.x/7.x release lands)
