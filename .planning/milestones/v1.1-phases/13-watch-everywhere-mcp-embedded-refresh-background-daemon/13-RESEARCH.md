# Phase 13: Watch Everywhere (MCP-Embedded Refresh + Background Daemon) - Research

**Researched:** 2026-11-07
**Domain:** Hosting the proven Phase 12 watch core in long-lived processes — asyncio MCP server (both transports), a double-fork detached daemon with lifecycle controls, launchd/systemd service installation, and long-lived-host behaviors (live rescope, periodic WAL checkpoint, graceful schedule-failure warnings)
**Confidence:** HIGH (codebase claims verified by direct file reads this session; platform claims verified on this macOS machine; external recipes cross-verified against official docs)

## Summary

Phase 13 adds no new indexing logic. Everything indexes through the Phase 12 `FileWatcher` (`src/sif/indexing/watcher.py:307`) — a fully self-threaded pipeline (observer thread → per-collection `EventDebouncer` → `queue.Queue` → single worker thread → per-burst `index_lock` → `IncrementalIndexer.update_paths`). The single most important verified finding: **the milestone research's `queue.Queue`-to-asyncio bridge recipe (STACK.md #7) is obsolete.** Phase 12 landed `FileWatcher` as a complete thread-based machine with host callbacks; the MCP host needs zero asyncio coordination — it constructs the watcher, starts it, serves, and stops it in a `finally`. The only thread-safety contract is that `on_event`/`on_batch` callbacks fire on the worker thread and must not touch asyncio or stdout — for the stdio transport, host output must go through `get_logger` (stderr, `src/sif/utils/logging.py:120`) because **stdout is the JSON-RPC protocol channel**.

The daemon side is stdlib-only packaging: double-fork detach (~30 lines, Stevens recipe), a PID file as management metadata (never arbitration — REQUIREMENTS Out of Scope locks flock as the only lock), `--stop` with SIGTERM → bounded wait → SIGKILL escalation, a Watch section in `sif status`, and plist/unit generation + `launchctl`/`systemctl` invocation with explicit argv. Platform facts verified locally: `launchctl` present (`/bin/launchctl`, Darwin Bootstrapper 7.0.0), `~/Library/LaunchAgents/` exists, `systemctl` absent on this Mac (systemd side must be template-tested + mocked-subprocess per D-13), `platformdirs.user_log_dir("sif")` → `/Users/forrest/Library/Logs/sif` (the exact D-07 default). SC4 (SIGKILL leaves no stale lock) needs a proof test, not new code — per-burst flock is released by the kernel on process death by construction (`src/sif/database/locking.py` module docstring states this contract).

**Primary recommendation:** Build a shared watch-host module for MCP (one `FileWatcher`, transport-specific lifecycle: stdio threads-around-loop + HTTP FastAPI lifespan), a utils-level daemon helper (double-fork + PID file + stop), and a service-template module (plistlib + systemd unit text). Split work so `FileWatcher`'s new rescope/tick APIs land before the hosts that consume them, and prove SC1/SC2/SC4 with real subprocesses using the Phase 12 e2e culture (deadline-bounded polling, outcome assertions, never naked sleep loops).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**MCP-embedded watch (LIVE-08)**
- **D-01:** **Both transports** — stdio AND HTTP host the embedded watcher under `SIF_MCP_WATCH=1`; one `FileWatcher` core, transport-specific lifecycle wiring (stdio: threads around the serve loop; HTTP: FastAPI lifespan). SC1 then holds regardless of how a client launches the server. — **Reversibility:** reversible.
- **D-02:** **BM25-only depth, always** — the MCP-embedded watcher never embeds, regardless of `watch_update_depth`. Guards the billing-surprise vector: a remote-embedding config meeting a background host the user didn't launch with an explicit flag. Vector catch-up = `sif embed` or foreground `sif watch --embed`. Strict LIVE-05 reading for background hosts.
- **D-03:** **Coexistence via flock** — MCP watch + detached daemon + foreground watch may all run simultaneously; per-burst flock + wait-then-run (12-D04, 11-D02) serialize bursts. No stand-down/discovery protocol couples LIVE-08 to LIVE-09; stat-decides makes the loser's pass a cheap no-op.
- **D-04:** **Opt-in = env var only** — `SIF_MCP_WATCH` maps to a `mcp_watch` bool in Settings (standard `SIF_` convention; flows into docs/configuration.md via regeneration). No `--watch` flags on mcp commands — external clients spawn stdio directly, where the env var is the only lever.

**Detach & daemon lifecycle (LIVE-09 SC2)**
- **D-05:** **PID file as management metadata** — `--detach` writes a small PID file next to the DB; `--stop` = read PID → SIGTERM → bounded wait → SIGKILL fallback; stale PID (process gone) reports "not running" and cleans the file up. Arbitration stays flock — REQUIREMENTS rejects PID-as-lock, not PID-as-pointer. Note the flock lock file cannot host this PID (per-burst locking means it is not held while idle).
- **D-06:** **Detach mechanics = stdlib double-fork** (fork → setsid → fork, stdio redirected to the log file/`/dev/null`; research recipe, ~30 lines). Under a supervisor the process NEVER forks (SC3) — `--detach` and service install are deliberately distinct paths.
- **D-07:** **Daemon logs default to the platform log dir** via platformdirs (`~/Library/Logs/sif/` on macOS, XDG state dir on Linux — matches the launchd recipe); `--log-file` overrides.
- **D-08:** **Running state extends `sif status`** — the existing top-level Rich table (and its `sif index status` alias) gains a Watch section: running yes/no, PID, host mode, depth. qmd precedent ("MCP: running (PID…)"). No separate `sif watch --status` surface.
- **D-09:** **`--detach` accepts the same flags as foreground** (`-c`, `--embed`) — the daemon IS `sif watch` backgrounded; `--embed` remains an explicit per-invocation opt-in (LIVE-05 holds). Embedding model lazy-loads and caches (research: "the daemon becomes the only process that should embed").
- **D-10:** **Raw-daemon crash policy = stay down** — no self-restart loop (duplicates KeepAlive/RestartSec badly and fights SC3's no-fork stance). Resilience belongs to the installed service (KeepAlive / Restart=on-failure baked in); `sif status` makes the down-state visible. SC4 is about clean flock state, which Phase 11 already provides.

**Service install (LIVE-09 SC3)**
- **D-11:** **Flags on `sif watch`** — `--install-service` / `--uninstall-service`, same flag family as `--detach`/`--stop`. Depth/collection flags given at install time are baked into the generated ProgramArguments / ExecStart.
- **D-12:** **Install = write + enable + start** — generate the plist/unit, then `launchctl bootstrap gui/$(id -u)` (macOS) / `systemctl --user daemon-reload && systemctl --user enable --now` (Linux), verify it came up, print the log location. Explicit argv lists, never `shell=True`; friendly errors when launchctl/systemctl is missing (research recipe).
- **D-13:** **Both platforms, full** — plist (plistlib) and unit (template) generation implemented and tested cross-platform (generation is pure text; tests assert BOTH artifacts on ANY platform); live launchctl/systemctl invocation is exercised only where available (macOS dev box for launchd; systemd via mocked-subprocess tests). launchd keys per research: `RunAtLoad`, `KeepAlive`, `ThrottleInterval=10`, logs to `~/Library/Logs/sif/`; systemd: `Type=simple`, `Restart=on-failure`, `RestartSec=5`, `WantedBy=default.target`; `loginctl enable-linger` documented for survive-logout.
- **D-14:** **`sif mcp daemon` stub stays unwired** — the shared detach/daemon helper is shaped for reuse by it, but wiring is a backlog/roadmap item (no Phase 13 SC covers an MCP HTTP daemon).

**Long-lived host behaviors**
- **D-15:** **Live rescope is IN scope for the long-lived hosts** (daemon + MCP watch): a light collections-table poll riding the existing periodic tick (recovery-tick precedent, 12-D12); added roots get scheduled + one reconcile pass; removed roots get unscheduled. Foreground watch keeps its restart-on-change MVP behavior. Rationale: a service-managed daemon that silently ignores a newly-added collection is a footgun — 12-CONTEXT named Phase 13 as this feature's home. — **Reversibility:** costly — grows the FileWatcher scheduling lifecycle API that Phase 14+ hosts also consume.
- **D-16:** **Idle-time periodic WAL checkpoint** — the daemon piggybacks `PRAGMA wal_checkpoint(TRUNCATE)` on the existing periodic ticks (minutes-scale; skip when a burst ran recently or the lock is contended). D-14's shutdown checkpoint stays the final word. Exact interval/conditions = Claude's discretion.
- **D-17:** **Schedule-failure handling = graceful warn** — a root that fails to schedule (inotify exhaustion / ENOSPC) logs cause + remedy (raise `fs.inotify.max_user_watches`); other roots keep watching; the recovery/reconcile machinery remains the backstop. Auto-PollingObserver fallback UX stays deferred.

### Carried forward (pre-decided — do not re-litigate)
- Per-burst flock released when idle (12-D04); wait-then-run loser semantics (11-D02); `update_paths` per-path seam (12-D06) — the API every host reuses.
- Signal shutdown = bounded flush + `wal_checkpoint(TRUNCATE)` + exit 0; second signal exits 130 (12-D14) — the daemon shutdown precedent.
- Single exclusion predicate `FileScanner.matches`; missing-root guard + recovery (12-D07/D08/D11/D12) — shared core behavior, free for new hosts.
- Startup reconcile pass per watched collection at host start (12-D03 reuse).
- Zero new runtime dependencies; `queue.Queue` thread→asyncio bridge if async coordination is needed — no janus (research #7); MCP watch opt-in only, never unconditional.
- Foreground under supervisor, never fork; explicit argv, no `shell=True`.

### Claude's Discretion
- PID file exact name/path derivation; `--stop` wait bounds and SIGKILL escalation timing
- Double-fork implementation details; parent/child handshake before printing the PID
- Rescope poll interval and diffing mechanics (as long as it rides the existing tick)
- Checkpoint interval/skip conditions (D-16)
- Service label naming (e.g. `com.docsif.watch`), plist/unit authorship details, uninstall semantics (stop-then-remove)
- Transport lifecycle wiring specifics — where FileWatcher start/stop hooks live per transport; whether `FileWatcher` needs light restructuring to host cleanly (keep a clean start/stop contract)
- Watch-section rendering in `sif status` (Rich layout/wording; "last sync time" optional per research FEATURES #27)
- Test scaffolding for detach/service paths (deterministic subprocess tests per 11-D08/D-09 + 12-D15 culture)
- New `SIF_` settings field names beyond `mcp_watch` (tick/checkpoint intervals); docs regeneration via `make docs-generate` (cli-reference.md and configuration.md are generator-owned — never hand-edit)

### Deferred Ideas (OUT OF SCOPE)
- **Wiring `sif mcp daemon`** (HTTP MCP server as a background daemon) — the shared helper supports it; not covered by any Phase 13 SC — backlog/roadmap item.
- **Auto-PollingObserver fallback on inotify exhaustion** — warning lands (D-17); the automatic fallback + detection UX is a Linux-hardening item for a later pass.
- **Embed compute split outside the flock window** — deferred from 12-D10; not raised in this discussion, stays deferred unless lock-hold bites.
- **Phase 14 ownership unchanged** — pre-command drift refresh + staleness markers stay in Phase 14.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LIVE-08 | `SIF_MCP_WATCH=1` 启用 MCP server 内嵌刷新，查询不被事件风暴阻塞 | `FileWatcher` is a self-threaded core needing only start/stop (verified API, §Architecture Pattern 1); both transport construction sites read (`run_stdio_server`, `run_http_server`/`create_app` — no lifespan today); FastAPI lifespan pattern verified from official docs; backend already WAL-safe per-request (fresh `DatabaseConnection` per query via `asyncio.to_thread`) so reads never block on watcher writes |
| LIVE-09 | `sif watch --detach`（PID/stop/status）+ launchd/systemd 服务安装 | Double-fork recipe cross-verified (§Code Examples); PID-file-as-metadata vs flock-arbitration contract verified from `locking.py`; launchd keys verified from local `man launchd.plist`; `launchctl bootstrap` syntax verified from local `launchctl help`; systemd recipe cross-verified (systemctl absent on this Mac — mocked tests per D-13); `status_cmd` extension point verified; `platformdirs.user_log_dir` default verified locally |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Python 3.10+; `list[str] | None` union syntax; line length 100 (ruff); max complexity 10; `combine-as-imports = true`; stdlib → third-party → `sif` import order; two blank lines after imports.
- Full annotations; `ty check src/sif` must stay clean; CLI modules keep Click decorators as-is.
- Quality suite after every plan: `ruff check src tests`, `ruff format --check src tests`, `pytest` (fail_under=90 coverage gate; current suite 1015 passed @ 96.20%).
- CLI errors raise `click.ClickException(str(e))`; transactions via `Database.transaction()` with rollback; `HybridSearcher` fail-fast conventions.
- Logging: module-level `logger = get_logger(__name__)`, names prefixed `sif`, **output to stderr**.
- GSD workflow: use `/gsd-execute-phase` for planned work; run the full quality suite before marking a plan done.
- Additional project conventions (from auto-memory, treat as binding): docs/cli-reference.md and docs/configuration.md are generator-owned (`make docs-generate`) — never hand-edit; unset `FORCE_COLOR` and set `NO_COLOR=1` when running pytest in agent shells.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| File-event → incremental index (watch core) | Application (`sif.indexing.watcher.FileWatcher`) | — | Host-agnostic core exists; all three new hosts embed it unchanged (except the rescope/tick API growth, D-15/D-16) |
| Single-writer arbitration | Infrastructure (`sif.database.locking.index_lock`) | — | Per-burst flock; kernel releases on death (SC4 by construction); hosts never add protocol on top (D-03) |
| MCP query serving | Application (`sif.mcp.server` + `SearchBackend`) | — | Already WAL-safe: fresh `DatabaseConnection` per request in `asyncio.to_thread` [VERIFIED: src/sif/mcp/backend.py:64-71] — no change needed for concurrent watcher writes |
| MCP watcher lifecycle | Application (new MCP watch-host helper) | Presentation (transports) | D-01: one FileWatcher core, transport-specific wiring — stdio wraps the serve loop, HTTP uses FastAPI lifespan; a shared helper keeps transports thin |
| Daemon detach + PID lifecycle | Utilities (new daemon helper) | CLI (`watch.py` flags) | Shared by `sif watch --detach` and the future `sif mcp daemon` slot (D-14 shape-for-reuse); fork mechanics are process-level, not CLI-level |
| Service install (launchd/systemd) | Utilities (new service-template module) | CLI (`watch.py --install-service`) | Generation is pure text (cross-platform testable); invocation is platform-gated subprocess with explicit argv |
| Running-state visibility | CLI presentation (`status_cmd`) | Daemon helper (PID file format) | D-08 extends the existing Rich table; PID file content must carry what status needs (pid + mode + depth) |
| Rescope / checkpoint cadence | Application (`FileWatcher` tick growth) | — | D-15/D-16 both ride the existing worker idle-timeout tick (recovery-tick precedent) |
| Log placement (detached hosts) | Utilities (platformdirs `user_log_dir`) | — | D-07 default matches the launchd StandardOutPath recipe so raw + service daemons log to one tree |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| (none new — zero-dependency phase) | — | — | CONTEXT "Carried forward": "Zero new runtime dependencies" [VERIFIED: 13-CONTEXT.md] |

All work uses existing verified dependencies:

| Library | Installed | Purpose in this phase | Verification |
|---------|-----------|----------------------|--------------|
| watchdog | 6.0.0 (pyproject `>=4.0.0,<7.0.0`) | `Observer`/`EventDebouncer` — already fully wired inside `FileWatcher`; new hosts only construct/start/stop it | [VERIFIED: local `importlib.metadata` + pyproject.toml dependencies block] |
| platformdirs | 4.5.0 (pyproject `>=3.0.0`) | `user_log_dir("sif")` for D-07 daemon log default — resolves to `/Users/forrest/Library/Logs/sif` on this machine | [VERIFIED: local run of `platformdirs.user_log_dir('sif')`] |
| Python stdlib (`os`, `signal`, `subprocess`, `plistlib`) | 3.10+ | double-fork detach, PID file, stop escalation, plist generation, launchctl/systemctl invocation | [CITED: Stevens/APUE double-fork recipe via cross-verified ports; plistlib in stdlib docs] |
| FastAPI / uvicorn | already deps | HTTP transport lifespan hook (D-01) | [CITED: fastapi.tiangolo.com/advanced/events/] |
| SQLite (stdlib sqlite3) | system | `PRAGMA wal_checkpoint(TRUNCATE)` idle checkpointing (D-16) | [VERIFIED: `src/sif/cli/commands/watch.py:43` — `_WAL_CHECKPOINT_TRUNCATE = "PRAGMA wal_checkpoint(TRUNCATE)"`] |

**Installation:** none — `pyproject.toml` dependency list is untouched this phase.

## Package Legitimacy Audit

This phase installs **zero external packages** (locked decision). No registry checks required. Existing dependencies were verified present and importable locally this session (watchdog 6.0.0, platformdirs 4.5.0, Python 3.13.9). Any plan step that proposes `pip install <new-package>` (e.g. `python-daemon`, `janus`, `psutil`) contradicts a locked decision and the milestone research "What NOT to Use" table — reject it.

## Architecture Patterns

### System Architecture Diagram

```
                       ┌──────────────── long-lived hosts (new) ────────────────┐
                       │                                                        │
  AI assistant ──────▶ │  MCP server process (SIF_MCP_WATCH=1)                  │
  (stdio / HTTP)       │   run_stdio_server / run_http_server                   │
                       │     ├─ SearchBackend (per-request DatabaseConnection,  │
                       │     │  WAL reads — never blocked by writer)             │
                       │     └─ MCP watch host ── construct + start ─┐           │
                       │        (stdio: around serve loop / finally; │           │
                       │         HTTP: FastAPI lifespan)             ▼           │
                       │                                                    ──┤
  user terminal ─────▶ │  sif watch --detach                                │ │
  (once, then exits)   │   double-fork ──▶ daemon child ──┐                  │ │
                       │   pipe handshake: PID ──▶ parent prints + exits │   │ │
                       │                                     │           │ │
  login session ─────▶ │  launchd/systemd ──▶ sif watch (FOREGROUND)   │ │ │
  (supervisor)         │   RunAtLoad/KeepAlive / Restart=on-failure    │ │ │
                       └───────────────┬──────────────────────┬─────────┬─┬─┘
                                       │ all three embed the SAME core  │ │
                                       ▼                                ▼ ▼
                            ┌──────────────────────────┐   ┌──────────────────────┐
                            │ FileWatcher (Phase 12)   │   │ collections-table    │
                            │ observer→debouncer→queue │   │ poll + WAL checkpoint│
                            │ →worker thread           │──▶│ riding the tick      │
                            │ (D-15 rescope API grows  │   │ (D-15/D-16, new)     │
                            │  this; D-17 warn on      │   └──────────────────────┘
                            │  schedule failure)       │
                            └────────────┬─────────────┘
                                         │ per-burst index_lock (flock; kernel-released)
                                         ▼
                            ┌──────────────────────────┐
                            │ IncrementalIndexer       │
                            │  update_paths /          │
                            │  update_collection       │
                            └────────────┬─────────────┘
                                         ▼
                                   SQLite (WAL) ◀── concurrent CLI/MCP readers
```

Trace: an editor save under any host → observer → debouncer → worker → flock → `update_paths` → WAL commit → a concurrent MCP `tools/call` query on a fresh connection reads fresh rows without ever waiting on the writer (SC1).

### Recommended Project Structure (deltas only)

```
src/sif/
├── indexing/
│   └── watcher.py          # MODIFY: rescope API (D-15), tick-driven checkpoint hook
│                           #  (D-16), schedule-failure warn (D-17)
├── mcp/
│   ├── watch_host.py       # NEW (name at planner's discretion): shared MCP watch
│                           #  lifecycle — build Database+FileWatcher behind
│                           #  settings.mcp_watch, BM25-only depth (D-02),
│                           #  logger-only callbacks (stdout is protocol!)
│                           #  + FastAPI lifespan factory for HTTP
│   └── transports/
│       ├── stdio.py        # MODIFY: run_stdio_server starts/stops watcher around loop
│       └── http.py         # MODIFY: lifespan threading through HTTPTransport/create_app
├── cli/
│   ├── commands/
│   │   └── watch.py        # MODIFY: --detach/--stop/--install-service/
│   │                       #  --uninstall-service/--log-file flags
│   └── main.py             # MODIFY: status_cmd Watch section (D-08)
├── utils/
│   ├── daemon.py           # NEW (placement per research ARCHITECTURE): double-fork,
│   │                       #  PID file read/write, stop escalation — shaped for the
│   │                       #  sif mcp daemon slot too (D-14)
│   └── service.py          # NEW (name at planner's discretion): plist (plistlib) +
│                           #  systemd unit generation, launchctl/systemctl invocation
└── config/
    └── settings.py         # MODIFY: mcp_watch bool + tick/checkpoint interval fields
```

Tests mirror existing layout: `tests/unit/utils/`, `tests/unit/mcp/`, `tests/unit/cli/`, `tests/unit/indexing/test_watcher.py` (extend), `tests/integration/` for subprocess e2e.

### Pattern 1: MCP-embedded watch — one core, two lifecycle wirings (D-01/D-02/D-03/D-04)

**What:** A shared helper constructs the watcher when `settings.mcp_watch` is true — open `Database`, `init_schema()`, select ALL collections (no `-c` filter exists in MCP context), run the 12-D03 startup reconcile, construct `FileWatcher` with **depth forced to `"bm25"`** (D-02) and callbacks routed to `logger` (never `console.print`), `start()`. Stdio: start before `transport.run()`, stop in `finally`. HTTP: the helper returns an `@asynccontextmanager` lifespan; `run_http_server` threads it into `HTTPTransport` → `create_app`.

**When to use:** both transports, unconditionally behind the env flag.

**Verified anchor points** (read this session):
- `run_stdio_server(db_path: str)` is the stdio construction site — body is exactly: `backend = SearchBackend(db_path)` / `server = MCPServer(backend)` / `server.register_tools(create_default_tools())` / `transport = StdioTransport(server)` / `await transport.run()` [VERIFIED: src/sif/mcp/transports/stdio.py:127-133]
- `create_app(server, cors_origins=None, sse_ping_interval=30, sse_max_events=None)` builds the FastAPI app with **no lifespan today** [VERIFIED: src/sif/mcp/transports/http.py:145-157 — signature and body read; new params must default to keep `create_app(server)`-style test call sites working]
- `HTTPTransport.run()` calls `create_app(self.server, self.cors_origins)` then `uvicorn.run(app, ...)` [VERIFIED: src/sif/mcp/transports/http.py:215-220]
- FastAPI lifespan (official docs): code before `yield` runs before the app accepts requests; after `yield` runs after it finishes; `FastAPI(lifespan=lifespan)`; it fully replaces deprecated `on_event` handlers — "It's all lifespan or all events, not both" [CITED: https://fastapi.tiangolo.com/advanced/events/]
- The CLI reaches transports via `sif/mcp/cli.py`, which re-exports `run_stdio_server_sync as run_stdio_server` [VERIFIED: src/sif/mcp/cli.py]

**Critical constraint — stdout is the protocol:** stdio transport writes JSON-RPC to stdout (`self.stdout.write`). Any Rich `console.print` from watch callbacks corrupts the stream. `get_logger` handlers are constructed as `logging.StreamHandler(sys.stderr)` [VERIFIED: src/sif/utils/logging.py:120] — logger-only output is safe on both transports.

**Why queries never starve (SC1):** watcher writes run on `FileWatcher`'s own worker thread; queries run through `SearchBackend._run_in_db` → `asyncio.to_thread` with a fresh `DatabaseConnection(self.db_path)` per request [VERIFIED: src/sif/mcp/backend.py:64-71]. WAL readers never block on the writer; the event loop never awaits watcher work. The only shared resource is the GIL (burst parse work is ms-scale per file; sqlite3 releases the GIL during I/O) — assert responsiveness with a deadline-bounded e2e rather than reasoning alone.

**Design note — startup reconcile must not block serving:** the foreground CLI reconciles before arming [VERIFIED pattern at src/sif/cli/commands/watch.py:241-260]. An MCP client's `initialize` handshake will time out if first-line serving waits minutes on a large reconcile. Recommended: start serving immediately; run the reconcile as the watcher's first queued job (worker thread) — the FSEvents startup burst is absorbed by checksum skipping either way (12-D03's rationale), and `update_paths`/`update_collection` are stat/checksum-decided. Planner decides; this is the main D-01 lifecycle-wiring subtlety.

### Pattern 2: Detach — stdlib double-fork with a pipe handshake (D-05/D-06/D-07/D-09)

**What:** `sif watch --detach [flags]` forks BEFORE any thread/observer exists (pre-fork constraint: `os.fork()` in a threaded process risks lock/malloc deadlocks), the child detaches and becomes the daemon; the parent stays alive only long enough to learn the daemon armed successfully, then prints the PID and exits 0.

Sequence (cross-verified against the Stevens-lineage recipe — see Code Examples):
1. Open a pipe (`os.pipe()`); `pid = os.fork()`.
2. Parent: close write end, `os.read` with a bounded timeout; on success message → print PID (SC2), `os._exit(0)`; on EOF/error → report failure, exit non-zero.
3. Child: `os.setsid()`; second `os.fork()` (grandchild can never re-acquire a controlling terminal); close pipe read end; `os.chdir` not required (all paths absolute/derived) — do NOT chdir("/") blindly if relative `--index` was given; flush `sys.stdout/stderr`; `dup2` `/dev/null` → stdin and the log file → stdout/stderr (D-07 default `user_log_dir("sif")` [VERIFIED local resolution], `--log-file` override).
4. Grandchild: write the PID file next to the DB (D-05; exact name planner's discretion, e.g. `{db_path}.watch.pid`), write "armed <pid>" to the pipe, then run the exact foreground watch body (D-09 — the daemon IS `sif watch`), reusing `SignalState`/`install_signal_handlers`/`shutdown_watcher` verbatim [VERIFIED: src/sif/cli/commands/watch.py:46-90 — module-level, directly reusable].

**Handshake rationale:** "PID reported at detach" (SC2) requires the parent to know the daemon actually started (schema opened, collections selected) — a pipe message after arming is deterministic; polling for the PID file's existence is racy by comparison. `os._exit` in the parent avoids running Click/atexit teardown twice. [ASSUMED — standard UNIX practice recommendation, planner may substitute]

**Stop path (D-05):** `sif watch --stop` reads the PID file → gone/stale (`os.kill(pid, 0)` raising `ProcessLookupError`) → print "not running", delete file → alive → SIGTERM → bounded wait for exit → SIGKILL fallback → remove file. Wait bounds are Claude's discretion. See Pitfall 3 for the PID-reuse race.

**SC4 proof shape (CONTEXT `<specifics>`):** SIGKILL the daemon → immediately relaunch `sif watch --detach` → succeeds with no lock error and no cleanup; flock is released by the kernel on process death (the `index_lock` docstring states the contract: "the lock is released when the holder's process exits, even on SIGKILL" [VERIFIED: src/sif/database/locking.py:11-13]). Test proves it; no new code.

### Pattern 3: Service install — generate, enable, start, verify (D-11/D-12/D-13)

**What:** `--install-service` renders the artifact for the current platform, writes it, invokes the manager with an explicit argv list, verifies the service came up, prints the log location. The service runs the plain foreground `sif watch` with the install-time flags baked into argv (SC3: no forking under the supervisor).

**launchd (macOS)** — keys verified from the local man page (`man launchd.plist`, primary source on this machine):
- `KeepAlive` — "boolean or dictionary of stuff … default is false … may be set to true to unconditionally keep the job alive" [VERIFIED: local man page]
- `RunAtLoad` — "boolean … default is false … launched once at the time the job is loaded" [VERIFIED: local man page]
- `ThrottleInterval` — "integer … value is in seconds, and by default, jobs will not be spawned more than once every 10 seconds" — so `ThrottleInterval=10` matches the launchd default; stating it explicitly is documentation, not a behavior change [VERIFIED: local man page]
- Invocation: `launchctl bootstrap <domain-target> [service-path, ...]` [VERIFIED: local `launchctl help bootstrap`] — `gui/$(id -u)` domain target per milestone recipe; undo = `launchctl bootout gui/$(id -u)/<plist>`; verify = `launchctl print gui/$(id -u)/<label>`.
- `ProgramArguments` must carry an absolute interpreter: `[sys.executable, "-m", "sif.cli.main", "watch", ...]` (launchd has no user PATH; `python -m sif.cli.main` is the documented local run form [VERIFIED: CLAUDE.md "Run the CLI locally"]). [CITED: milestone STACK.md #6 for the pattern]
- `StandardOutPath`/`StandardErrorPath` → `~/Library/Logs/sif/` files so the supervisor captures the foreground output [CITED: milestone recipe; individual key semantics not man-page-verified this session]
- Destination `~/Library/LaunchAgents/` (exists on this machine [VERIFIED local]). Label at planner's discretion (CONTEXT suggests `com.docsif.watch`).

**systemd (Linux)** — cross-verified across multiple independent implementations:
- Unit at `~/.config/systemd/user/sif-watch.service`: `[Service] Type=simple` (foreground; never fork or append `&` — an immediately-exiting ExecStart reads as failure and restart-loops), `Restart=on-failure`, `RestartSec=5`, optionally `StartLimitIntervalSec`/`StartLimitBurst`; `[Install] WantedBy=default.target`
- Install: `systemctl --user daemon-reload && systemctl --user enable --now sif-watch`
- Survive-logout: `loginctl enable-linger $USER` (since systemd v230 the user manager ends with the last session without linger) — document in install output
- Verify: `systemctl --user status sif-watch`; logs: `journalctl --user -u sif-watch -f`
[CITED: freedesktop systemd v230 announcement, NixOS wiki Systemd/User Services, Baeldung — cross-verified; systemctl absent on this Mac so nothing live-tested]

**Cross-platform testing (D-13):** generation is pure text — assert BOTH artifacts' contents on ANY platform (plist parsed back via `plistlib`; unit text asserted directly). Live invocation: launchd exercised for real on the macOS dev box (scratch label + tmp DB, then bootout — do NOT touch the user's real agents); systemd via mocked `subprocess.run` asserting exact argv. Friendly `ClickException` when the manager binary is missing (`shutil.which` gate).

### Pattern 4: Long-lived host behaviors riding the existing tick (D-15/D-16/D-17)

**What:** the worker's idle wait is already the periodic tick — `job = self._queue.get(timeout=selfconfig.restat_interval)` and on `queue.Empty` → `self.recovery_tick()` [VERIFIED: src/sif/indexing/watcher.py:483-487]. Three behaviors join it:

- **Rescope (D-15):** a collections-table poll diffing registered vs watched sets. The arming/teardown primitives already exist and are thread-safe: `_schedule_watch(state, observer)` arms debouncer + recursive watch [VERIFIED: watcher.py:370-384], `observer.unschedule(handle)` under watchdog's internal lock (`BaseObserver.unschedule` body begins `with self._lock:` [VERIFIED: local inspection of installed watchdog 6.0.0 source]) — Phase 12's `recovery_tick` already calls both from the worker thread [VERIFIED: watcher.py:422-454], so the rescope diff follows the same proven pattern. Added collection → `_schedule_watch` + enqueue `(collection, FoldResult(needs_reconcile=True))` (the exact recovery-return job shape [VERIFIED: watcher.py:454]); removed collection → unschedule + drop `_WatchState` (documents stay — stopping watching never deletes). New API shape (e.g. `rescope(collections: list[Collection])` callable from the tick, or a repo-backed poll inside `FileWatcher`) is planner's discretion; D-15 warns it "grows the FileWatcher scheduling lifecycle API that Phase 14+ hosts also consume."
- **Subtlety — `-c` filtered hosts:** `_select_collections` [VERIFIED: watch.py:93-111] means a host may watch a subset. The poll must not pull in collections the host deliberately excluded: watch-all hosts diff the full table; `-c`-filtered hosts should skip rescope or diff within the filter. Decide explicitly in the plan.
- **Idle checkpoint (D-16):** on the tick (minutes-scale — the 5s `restat_interval` default is too hot; a counter or deadline is needed, exact mechanics planner's discretion), run `conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")` on the worker's connection, skipping when a burst ran recently or contention is present (`wal_checkpoint` returns a `(busy, log, checkpointed)` row — inspecting `busy` gives a cheap skip signal). The D-14 shutdown checkpoint stays the final word.
- **Schedule-failure warn (D-17):** `observer.schedule` raising `OSError`/ENOSPC on a root → log cause + remedy (`raise fs.inotify.max_user_watches`), keep other roots watching, let the recovery/reconcile machinery backstop. This wraps `_schedule_watch` callers (startup, recovery-return, rescope-added).

### Pattern 5: Status visibility (D-08)

**What:** `status_cmd` [VERIFIED: src/sif/cli/main.py:109-146] gains a Watch section (running yes/no, PID, host mode, depth). `sif index status` already delegates via `ctx.invoke(status_cmd)` [VERIFIED: src/sif/cli/commands/index.py:387-392] — one extension covers both surfaces.

**Data source:** the daemon PID file (Pattern 2). Recommended content: a tiny structured payload (pid + mode + depth + started timestamp) so the section can render "daemon · PID 1234 · embed" without guessing; stale file → "not running" + clean-up question. Foreground watch and MCP hosts are deliberately NOT tracked by the PID file (foreground owns its terminal; MCP servers are client-spawned and plural) — status honestly reports what it knows. Optional "last sync time" per FEATURES #27. Exact Rich wording is Claude's discretion.

### Anti-Patterns to Avoid

- **`python-daemon` / any daemonization library:** rejected — new runtime dep for ~30 stdlib lines, and its forking actively breaks supervisor exit tracking (launchd `KeepAlive` / systemd `Type=simple` expect foreground). [CITED: milestone STACK.md "What NOT to Use"]
- **PID file as lock / single-instance gate:** REQUIREMENTS Out of Scope locks flock as the only arbitration ("自定义 lockfile 方案 | flock 语义上不可能 stale，优先于 PID 文件方案"). The PID file is metadata for `--stop`/`status` only. Two daemons may run; per-burst flock + stat-decides make the overlap a cheap no-op (D-03, D-05).
- **Self-restart loop in the raw daemon (D-10):** duplicates KeepAlive/RestartSec badly; resilience belongs to the installed service.
- **`--detach` under the supervisor / forking in the service path:** SC3's contract — `--detach` and `--install-service` are deliberately distinct paths.
- **`shell=True` or string command lines for launchctl/systemctl:** explicit argv lists only (D-12; injection surface — see Security Domain).
- **Rich/console output from the MCP-embedded watcher:** stdout is the JSON-RPC channel on stdio transport — corrupts the protocol. Logger (stderr) only.
- **Blocking the MCP `initialize` handshake on the startup reconcile:** serve first, reconcile on the worker (Pattern 1 design note).
- **A stand-down/discovery protocol between hosts (D-03):** no cross-host coupling — flock + stat-decides is the entire coexistence story.
- **Embedding in the MCP watcher (D-02):** never, regardless of `watch_update_depth` — the billing-surprise vector. Depth is forced `"bm25"` at construction.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Asyncio↔thread event bridging | Custom condition-var/`janus` bridge into the event loop | Nothing — `FileWatcher` is self-threaded; start/stop only | Phase 12 already encapsulated all threading; the milestone's bridge recipe (STACK #7) predates the landed code [VERIFIED: watcher.py module architecture] |
| Daemonization | fork/setsid edge-case handling beyond the recipe; `python-daemon` | The ~30-line verified double-fork recipe (Pattern 2) | Second fork + setsid + dup2 is the complete correct recipe; libraries add dependency + supervisor-hostile forking [CITED: cross-verified Stevens-lineage ports] |
| plist XML authorship | String-interpolated XML | `plistlib.dump` | stdlib, correct escaping/types, round-trip parseable for tests |
| Single-writer arbitration | PID-based "is the daemon running" gates around indexing | `index_lock` per burst, untouched | Kernel flock cannot go stale (SC4); PID gates reintroduce the stale-lock tar pit REQUIREMENTS rejects [VERIFIED: locking.py contract] |
| Freshness under concurrent access | Cross-process invalidation/signals | WAL + per-request connections (already in `SearchBackend`) | Readers never block; verified pattern at backend.py:64-71 |
| systemd behavior testing | Linux CI or VM for this phase | Template asserts + mocked `subprocess.run` argv asserts | D-13 locks this; generation is pure text |

**Key insight:** Phase 12's core was built host-agnostic precisely so this phase is packaging + lifecycle, not indexing logic. Every hour spent re-plumbing events is a defect vector; every host should reduce to construct → start → (serve | park) → stop.

## Common Pitfalls

### Pitfall 1: Corrupting the stdio JSON-RPC stream
**What goes wrong:** watch callbacks print (Rich banner, batch summaries) to stdout in the MCP server process → the AI client receives garbage frames and the session dies — and SC1 fails mysteriously.
**Why:** the foreground host renders via `Console()`; reusing that code verbatim in MCP writes to stdout, which `StdioTransport._write_message` owns [VERIFIED: stdio.py:68-74].
**How to avoid:** the MCP watch host routes `on_event`/`on_batch` to `logger` only; `get_logger` handlers target stderr [VERIFIED: logging.py:120]. Optionally guard with a test asserting the subprocess's stdout contains ONLY JSON lines while a burst runs.
**Warning signs:** client "parse error" logs; e2e JSON decode failures during bursts.

### Pitfall 2: Forking after threads exist
**What goes wrong:** `--detach` forks after the CLI group callback or an earlier step started threads (or after `asyncio.run` in an MCP context) → child deadlocks on a lock held mid-fork (malloc/gil/embedding-loader locks).
**Why:** POSIX fork duplicates only the calling thread; other threads' held locks never release in the child.
**How to avoid:** detach BEFORE constructing `Database`/observer/anything threaded — the double-fork helper should be the first thing `--detach` does; the daemon child then builds everything fresh.
**Warning signs:** hangs between detach and PID-file appearance; flaky macOS-only deadlocks. [CITED: general fork+threads hazard, cross-verified in daemonization literature]

### Pitfall 3: PID reuse makes `--stop` kill an innocent process
**What goes wrong:** daemon dies uncleanly (SIGKILL), PID file lingers; the OS reuses the PID; `sif watch --stop` SIGTERMs an unrelated process.
**Why:** PID files are hints, not leases — exactly why REQUIREMENTS bans PID-as-lock.
**How to avoid:** before signaling, corroborate identity (e.g. process start-time/`ps -p <pid> -o lstart=` vs a timestamp stored in the PID file, or a cmdline check); refuse with "PID file is stale" when the match fails. Bounded-wait then SIGKILL only after identity is confirmed. Exact scheme = planner's discretion (CONTEXT lists `--stop` bounds as discretion).
**Warning signs:** `--stop` succeeding while the daemon demonstrably still holds the lock; status flip-flop.

### Pitfall 4: Startup reconcile stalls the MCP handshake
**What goes wrong:** MCP host copies the foreground order (reconcile fully, then serve) → a multi-minute first reconcile on a large KB → the client's `initialize` times out and kills the server; SIF_MCP_WATCH looks broken.
**Why:** foreground could afford blocking (user watches the spinner); a protocol server cannot.
**How to avoid:** serve first; enqueue the reconcile as the watcher's first job (Pattern 1 design note).
**Warning signs:** e2e initialize timeouts proportional to collection size.

### Pitfall 5: launchd bootstrap errors on re-install / partial states
**What goes wrong:** `--install-service` over an already-bootstrapped label → `bootstrap` fails ("already booted" class errors); a previously-written plist with a stale interpreter path silently keeps the OLD config after "successful" reinstall.
**Why:** bootstrap loads a domain's services; an existing load conflicts.
**How to avoid:** treat install as idempotent-ish: on conflict, bootout-then-bootstrap (or `kickstart -k` after plist rewrite); always print the plist path + log path + verify command in the output.
**Warning signs:** install succeeds but behavior matches the old flags. [ASSUMED — mitigation pattern from the recipe family; verify against `launchctl` output during implementation]

### Pitfall 6: Rescope fights the `-c` filter or races the observer
**What goes wrong:** the collections poll pulls in a collection the user explicitly excluded with `-c` (surprise watching), or mutates `_watch_states`/`_debouncers` while `recovery_tick` iterates them.
**Why:** `_watch_states` is keyed by name and iterated by the tick [VERIFIED: watcher.py:338, 434]; two writers on it must be the same thread.
**How to avoid:** run the rescope diff ON the worker thread inside the same tick (never from arbitrary threads); scope the diff to the host's eligible set (all vs `-c` names).
**Warning signs:** a filtered daemon suddenly watching everything; rare KeyError in recovery_tick.

### Pitfall 7: WAL checkpoint on a contended DB stalls the tick
**What goes wrong:** `wal_checkpoint(TRUNCATE)` issued while another process holds a read/write lock blocks or returns busy every tick, adding latency or log noise.
**Why:** TRUNCATE needs all readers drained past the log.
**How to avoid:** treat the checkpoint result row as the skip signal (busy → skip silently this tick); skip when a burst ran recently (D-16's own conditions); minutes-scale cadence, never per-tick-at-5s.
**Warning signs:** tick latency spikes correlated with concurrent searches.

### Pitfall 8: Service-tested-only-on-macOS regressions on Linux (and vice versa)
**What goes wrong:** plist path asserts pass on macOS but the unit-file text has platform drift (paths, `WantedBy`), or `--install-service` on Linux shells out with a stale argv.
**Why:** one dev machine can run only one manager live.
**How to avoid:** D-13's discipline — BOTH artifacts asserted on ANY platform (pure-text generation tests); live invocation behind `shutil.which` gates with friendly errors; systemd argv asserted via mocked subprocess everywhere, exercised live only where available.
**Warning signs:** generation tests skipped on one platform.

## Code Examples

### Detach: double-fork skeleton (verified recipe shape)

```python
# Source: cross-verified Stevens-lineage recipe (Sander Marechal port citing
# APUE §13.3; V8 testrunner daemon.py; pywikibot daemonize) — adapted to D-06/D-07.
import os
import sys

def detach(log_path: str) -> int:
    """Double-fork; return the daemon PID to the original parent via pipe."""
    read_fd, write_fd = os.pipe()
    pid = os.fork()
    if pid > 0:
        # Original parent: learn the armed PID, then exit without teardown.
        os.close(write_fd)
        with os.fdopen(read_fd, "rb") as r:
            msg = r.read()  # daemon writes b"armed <pid>" (or an error) and closes
        # parse msg; caller prints the PID (SC2) and os._exit(0)
        return -1  # (illustrative — real helper returns parsed pid/status)
    # First child: new session, then fork again so the daemon is NOT a
    # session leader and can never re-acquire a controlling terminal.
    os.setsid()
    if os.fork() > 0:
        os._exit(0)
    os.close(read_fd)
    # Redirect stdio: /dev/null in, log file out/err (D-07).
    sys.stdout.flush()
    sys.stderr.flush()
    devnull = os.open(os.devnull, os.O_RDONLY)
    log = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    os.dup2(devnull, 0)
    os.dup2(log, 1)
    os.dup2(log, 2)
    # ... write PID file, write b"armed <pid>" to write_fd, close it,
    # then run the exact foreground watch body (D-09).
```

[ASSUMED for the pipe-handshake specifics; the fork/setsid/fork/dup2 sequence is cross-verified. `os._exit` in parents avoids double atexit/buffer teardown — pywikibot's documented choice.]

### FastAPI lifespan hosting the watcher (HTTP transport, D-01)

```python
# Source: https://fastapi.tiangolo.com/advanced/events/ (pattern, verified)
from contextlib import asynccontextmanager

@asynccontextmanager
async def mcp_watch_lifespan(app):     # built by the shared watch host
    watcher = start_embedded_watch(db_path)   # Database + FileWatcher, BM25-only
    yield
    if watcher is not None:
        stop_embedded_watch(watcher)          # stop(flush=True) + checkpoint

app = FastAPI(lifespan=mcp_watch_lifespan)    # before yield = pre-request;
                                             # after yield = post-serving
```

[CITED: fastapi.tiangolo.com/advanced/events/ — "It's all lifespan or all events, not both"; `create_app` must thread this through with a default of None to keep existing test call sites working [VERIFIED: http.py:145-157]]

### systemd user unit (D-13)

```ini
# Source: cross-verified pattern (NixOS wiki, Baeldung, freedesktop v230 notes)
[Unit]
Description=DocSIF watch daemon

[Service]
Type=simple
ExecStart=/abs/python -m sif.cli.main watch --index /abs/sif.db
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

Install: `systemctl --user daemon-reload && systemctl --user enable --now sif-watch`; survive-logout: `loginctl enable-linger $USER`. [CITED: cross-verified]

### Reused Phase 12 anchors (verified verbatim this session)

- Watcher lifecycle contract: `def start(self) -> None:` arms observer/debouncers/worker [VERIFIED: src/sif/indexing/watcher.py:345]; `def stop(self, *, flush: bool = True) -> None:` [VERIFIED: watcher.py:386]; `def recovery_tick(self) -> None:` [VERIFIED: watcher.py:422].
- `WatchConfig` fields, verbatim [VERIFIED: src/sif/indexing/watcher.py:82-87]:
  ```python
  debounce_interval: float = 0.5
  lock_timeout: float = 30.0
  depth: str = "bm25"
  restat_interval: float = 5.0
  on_event: Callable[[str], None] | None = None
  on_batch: Callable[[Collection, IncrementalResult], None] | None = None
  ```
- Per-path seam [VERIFIED: src/sif/indexing/incremental.py:164-171]: `def update_paths(self, collection: Collection, paths: Iterable[Path], *, force: bool = False, progress: Callable[[str], None] | None = None) -> IncrementalResult:`
- Tick (where D-15/D-16 ride) [VERIFIED: src/sif/indexing/watcher.py:483-487]:
  ```python
  job = self._queue.get(timeout=self._config.restat_interval)
  except queue.Empty:
      self.recovery_tick()
  ```
- Settings fields this phase extends [VERIFIED: src/sif/config/settings.py:43-66 — `watch_debounce_interval`, `watch_ignore_patterns`, `watch_update_depth`, `watch_restat_interval`] and [VERIFIED: settings.py:155-169 — `mcp_host`, `mcp_port`, `mcp_transport`].
- Shutdown precedent, verbatim [VERIFIED: src/sif/cli/commands/watch.py:43]: `_WAL_CHECKPOINT_TRUNCATE = "PRAGMA wal_checkpoint(TRUNCATE)"` and `shutdown_watcher(watcher, conn)` at watch.py:79-90 (stop with flush, then checkpoint in `finally`) — module-level and directly reusable by the daemon host.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| STACK.md #7: watchdog threads × asyncio bridged by `queue.Queue` drained by a periodic asyncio task | `FileWatcher` is fully self-threaded; hosts only start/stop it; no asyncio coordination | Phase 12 landing (2026-11-07) | Do NOT plan a bridge; the only cross-thread rule is "callbacks run on the worker thread — log, don't print" |
| `on_event("startup"/"shutdown")` FastAPI handlers | `lifespan` async context manager (on_event deprecated; mutually exclusive with lifespan) | FastAPI current docs | New HTTP wiring uses lifespan only |
| research ARCHITECTURE's `LiveIndexService` / `indexing/live.py` naming | `FileWatcher` in `indexing/watcher.py` is the landed core | Phase 12 | All milestone-research module names for the watch core are superseded by the landed names in this document |
| research's "MCP backend.py thread owned by backend" | Transports own construction (`run_stdio_server`/`run_http_server`); a new shared watch-host helper keeps both thin | Phase 12/13 code shape | Hook at the transport entry points, not inside `SearchBackend` (backend stays query-only) |

**Deprecated/outdated in the milestone research (superseded by landed code):** module names `indexing/live.py`, `LiveIndexService`, `mcp/backend.py`-hosted watcher thread, pidfile-in-daemon-helper-as-lock framing. The recipes' *semantics* (double-fork, plist/unit, no-janus) remain authoritative.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Pipe handshake for `--detach` PID reporting (child writes "armed <pid>" after init; parent prints and `os._exit(0)`) is the right deterministic handshake | Pattern 2, Code Examples | Low — any deterministic parent-learns-success scheme satisfies SC2; polling the PID file also works |
| A2 | `StandardOutPath`/`StandardErrorPath` plist keys capture the service's foreground output to `~/Library/Logs/sif/` | Pattern 3 | Low-Med — if wrong, service logs go nowhere; verify during implementation against `launchctl print` output |
| A3 | launchd re-install conflict handling = bootout-then-bootstrap (or kickstart after rewrite) | Pitfall 5 | Low — surfaced as friendly error otherwise; UX polish |
| A4 | GIL contention between watcher bursts and query threads is negligible at personal-KB scale (SC1 holds) | Pattern 1 | Med — if wrong, SC1 e2e shows latency; mitigation would be chunked/yielding bursts (defer; measure first) |
| A5 | systemd unit details (`Restart=on-failure`, `RestartSec=5`, `WantedBy=default.target`, linger requirement) as cross-verified — no Linux box available this session | Pattern 3 | Low — multiple independent sources agree; live verification impossible on this Mac (D-13 anticipates mocked tests) |
| A6 | `wal_checkpoint(TRUNCATE)` result row `(busy, log, checkpointed)` is the skip signal for D-16 | Pattern 4 | Low — fire-and-forget execution is also acceptable per D-16 discretion |
| A7 | Status "host mode/depth" are carried inside the PID file payload (small structured content) | Pattern 5 | Low — alternative is filename/dir conventions; both satisfy D-08 |

## Open Questions (RESOLVED)

All four resolved during phase planning (revision 1); each resolution below names the plan task that adopts it.

1. **Rescope scope for `-c`-filtered hosts** — should a filtered daemon/MCP host rescope within its filter (recommended) or skip rescope entirely (simplest)?
   - What we know: `_select_collections` supports subsets; D-15's rationale (new collections must not be silently ignored) is about watch-all hosts.
   - What's unclear: whether a `-c` user adding a collection expects it picked up.
   - Recommendation: rescope within the filter (added-and-selected → watch; deselected-or-removed → unwatch); document in the plan.
   - **Resolution:** rescope within the filter — the rescope provider returns only the host's eligible set (adopted: 13-01 must_haves truth 4; the daemon's filter-respecting provider in 13-02 truth 8).
2. **MCP startup reconcile placement** — serve-then-reconcile-on-worker (recommended, Pitfall 4) vs reconcile-then-serve.
   - Recommendation: serve first; enqueue reconcile as first job; checksum skipping absorbs the startup burst either way.
   - **Resolution:** serve-then-reconcile-on-worker — the watcher starts before serving and the per-collection reconcile runs as the first queued worker jobs (adopted: 13-03 must_haves truth 6 / Task 1 step 1; e2e Test 4 pins the unblocked handshake).
3. **Does the MCP-embedded watcher also get rescope (D-15)?** — CONTEXT says "daemon + MCP watch" are the long-lived hosts; confirm both get the API (recommended: yes — same `FileWatcher` core, same tick).
   - **Resolution:** yes — the MCP host wires rescope_provider returning all registered collections on the 13-01 tick seam (adopted: 13-03 must_haves truth 8 / Task 1 step 1).
4. **`--stop` identity corroboration scheme** (Pitfall 3) — start-timestamp in PID file vs cmdline probe vs both.
   - Recommendation: timestamp-in-file + `ps` start-time comparison on macOS, `/proc/<pid>/stat` field 22 on Linux; planner picks the lightest portable form.
   - **Resolution:** cmdline probe, the lightest portable form the recommendation grants — `ps -p PID -o command=` output must contain the sif CLI and watch argv markers, fail-closed on mismatch or missing ps (adopted: 13-02 Task 1 step 3 corroborate_pid; unit-pinned in 13-02 Task 2 Test 3).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | everything | ✓ | 3.13.9 (local) | project floor 3.10 — code must stay 3.10-compatible (union syntax only, no 3.11+ APIs) |
| watchdog | FileWatcher | ✓ | 6.0.0 installed; pyproject `>=4.0.0,<7.0.0` | — |
| platformdirs | D-07 log dir | ✓ | 4.5.0; `user_log_dir('sif')` → `/Users/forrest/Library/Logs/sif` | — |
| launchctl (macOS) | service install/live test | ✓ | `/bin/launchctl` (Darwin Bootstrapper 7.0.0) | — |
| `~/Library/LaunchAgents/` | plist destination | ✓ | exists | create on install |
| systemctl (Linux) | service install/live | ✗ | absent on this Mac | D-13: template asserts + mocked-subprocess tests; live systemd untestable here |
| FastAPI/uvicorn | HTTP lifespan | ✓ | in dependencies | ImportError path already handled by `mcp http` command |
| `man launchd.plist` | key verification | ✓ | verified this session (KeepAlive/RunAtLoad/ThrottleInterval) | — |

**Missing dependencies with no fallback:** none for macOS development. Linux live-install verification is structurally unavailable in this environment — D-13's mocked-test strategy is the designed mitigation, not a workaround.

**Missing dependencies with fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (1015 passed @ 96.20% coverage; fail_under=90 enforced) + ruff + ruff-format + ty |
| Config file | `pyproject.toml` ([tool.pytest.ini_options] / [tool.ruff]) |
| Quick run command | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/test_watcher.py tests/unit/cli/test_watch_cmd.py -x -q` |
| Full suite command | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` (then `ruff check src tests`, `ruff format --check src tests`, `ty check src/sif`) |

Note: unset `FORCE_COLOR` (`env -u`, setting "0" does not work) and set `NO_COLOR=1` — known spurious-failure vector in agent shells.

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LIVE-08 | `SIF_MCP_WATCH=1` stdio server refreshes index while serving; queries responsive during burst (SC1) | integration (real subprocess) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/integration/test_mcp_watch_e2e.py -x -q` | ❌ Wave 0 |
| LIVE-08 | HTTP transport lifespan starts/stops watcher behind flag | unit | `python -m pytest tests/unit/mcp/test_mcp_watch_host.py -x -q` | ❌ Wave 0 |
| LIVE-08 | MCP depth forced BM25 regardless of `watch_update_depth` (D-02) | unit | same host test file | ❌ Wave 0 |
| LIVE-09 | `--detach` backgrounds, PID reported, daemon updates index; `--stop` clean | integration (subprocess) | `python -m pytest tests/integration/test_watch_daemon_e2e.py -x -q` | ❌ Wave 0 |
| LIVE-09 | SC4: SIGKILL then immediate re-detach succeeds, no lock error | integration (subprocess) | `python -m pytest tests/integration/test_watch_daemon_e2e.py -k sigkill -x -q` | ❌ Wave 0 |
| LIVE-09 | stale PID file → "not running" + cleanup; stop escalation | unit (daemon helper) | `python -m pytest tests/unit/utils/test_daemon.py -x -q` | ❌ Wave 0 |
| LIVE-09 | plist + unit generation cross-platform asserts; install argv via mocked subprocess | unit | `python -m pytest tests/unit/utils/test_service.py -x -q` | ❌ Wave 0 |
| LIVE-09 | `status_cmd` Watch section (running/PID/mode/depth) | unit | `python -m pytest tests/unit/cli/test_status_watch.py -x -q` | ❌ Wave 0 |
| D-15 | rescope: added root scheduled + reconciled; removed root unscheduled; docs untouched | unit (extend existing) | `python -m pytest tests/unit/indexing/test_watcher.py -k rescope -x -q` | ✅ (file exists; tests added) |
| D-16 | idle tick runs TRUNCATE checkpoint; skips when contended/recent burst | unit (extend existing) | `python -m pytest tests/unit/indexing/test_watcher.py -k checkpoint -x -q` | ✅ (file exists; tests added) |
| D-17 | schedule failure warns with remedy; other roots keep watching | unit (extend existing) | `python -m pytest tests/unit/indexing/test_watcher.py -k "schedule_failure or inotify" -x -q` | ✅ (file exists; tests added) |
| docs | new flags/settings flow into generator-owned docs | unit (existing gate) | `python -m pytest tests/test_docs.py -x -q` after `make docs-generate` | ✅ (existing gate; regenerate in final plan) |

### Sampling Rate
- **Per task commit:** quick unit run for the touched area + full-suite-fast if cheap (`pytest -x -q tests/unit`)
- **Per wave merge:** `env -u FORCE_COLOR NO_COLOR=1 python -m pytest`
- **Phase gate:** full suite + `ruff check src tests` + `ruff format --check src tests` + `ty check src/sif` green before `/gsd-verify-work`; docs regen (`make docs-generate`) lands with the flags/settings plan (12-03 precedent — docs gate stays red only until that plan, then must be green at phase end)

### Wave 0 Gaps
- [ ] `tests/integration/test_mcp_watch_e2e.py` — SC1 (subprocess `sif mcp stdio` with `SIF_MCP_WATCH=1`, seeded tmp collection, deadline-bounded responsiveness assertions) — LIVE-08
- [ ] `tests/unit/mcp/test_mcp_watch_host.py` — host helper: flag on/off, BM25-forced depth, logger-only callbacks, lifespan factory
- [ ] `tests/integration/test_watch_daemon_e2e.py` — detach lifecycle + SC4 SIGKILL/restart
- [ ] `tests/unit/utils/test_daemon.py` — PID file write/read/stale, stop escalation with fake PIDs (no real kills in unit tests)
- [ ] `tests/unit/utils/test_service.py` — plist (parse-back via plistlib) + unit text on BOTH platforms; launchctl/systemctl argv via mocked `subprocess.run`
- [ ] `tests/unit/cli/test_status_watch.py` — Watch section rendering incl. stale-PID path
- [ ] Extend `tests/unit/indexing/test_watcher.py` — rescope / checkpoint tick / schedule-failure warn (synthetic, zero-timing per 12-D15)

Existing infrastructure otherwise covers the phase (conftest fixtures, e2e helpers in `tests/integration/test_watch_e2e.py` — seeded-DB + deadline-poll patterns to copy).

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Local single-user tool; no auth surface added |
| V3 Session Management | no | No sessions introduced |
| V4 Access Control | yes | File permissions on new artifacts: PID file and log file created with restrictive modes (follow the lock file precedent — `os.open(..., 0o600)` [VERIFIED: locking.py:70]); plist written 0644 (launchd must read it) into a user-owned dir |
| V5 Input Validation | yes | All manager invocation via explicit argv lists — never `shell=True`, never user text concatenated into a shell (D-12); service-label/path derived from validated constants; PID file content parsed defensively (a tampered file must not crash or kill arbitrary PIDs — corroborate identity, Pitfall 3) |
| V6 Cryptography | no | Nothing cryptographic |
| V14 Config | yes | Generated plist/unit contents are fully derived from flags + resolved paths; `--index` paths embedded verbatim into ProgramArguments — escape-free by argv-list construction; never interpolate into XML outside plistlib |

### Known Threat Patterns for daemon/service install (local CLI, Python/SQLite)

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Shell injection via install flags / paths | Tampering / Elevation | `subprocess.run` with argv lists only (D-12); no `shell=True` anywhere in the new modules |
| Symlink/pre-planted file at PID-file or plist path | Tampering | Create with explicit modes; refuse or replace atomically (write-temp-then-rename); plist destination is user-owned `~/Library/LaunchAgents` — overwrite only our own label's file |
| PID reuse → SIGTERM/SIGKILL on innocent process (DoS on user processes) | Denial of Service | Identity corroboration before signaling (Pitfall 3); refuse on mismatch |
| Corrupt/hand-edited PID file parsed into a kill | Tampering | Defensive parse (int-or-structured payload only); stale/garbage → "not running" + cleanup, never a blind kill |
| Service capture via writable unit/plist by another local user | Elevation | Destinations are user-scoped (`~/Library/LaunchAgents`, `~/.config/systemd/user`) with default umask; no world-writable creates |
| Protocol stream corruption from stray stdout writes (stdio MCP) | Tampering | Logger-to-stderr-only rule for the embedded watcher (Pitfall 1); e2e asserts protocol-clean stdout during bursts |

## Sources

### Primary (HIGH confidence)
- Codebase reads this session (verbatim quotes in-document): `src/sif/indexing/watcher.py` (full), `src/sif/cli/commands/watch.py` (full), `src/sif/database/locking.py` (full), `src/sif/config/settings.py` (full), `src/sif/mcp/server.py` (full), `src/sif/mcp/transports/stdio.py` (full), `src/sif/mcp/transports/http.py` (full), `src/sif/cli/commands/mcp.py` (full), `src/sif/mcp/cli.py`, `src/sif/cli/main.py:109-146` (status_cmd), `src/sif/cli/commands/index.py:387-392`, `src/sif/mcp/backend.py:1-100`, `src/sif/utils/logging.py:120`, `src/sif/indexing/incremental.py:164-178`, `scripts/generate_config_ref.py:137-175`, `pyproject.toml` deps
- Local machine verification (2026-11-07, macOS / Darwin 25.6.0): Python 3.13.9; watchdog 6.0.0; platformdirs 4.5.0 (`user_log_dir('sif')` → `/Users/forrest/Library/Logs/sif`); `/bin/launchctl` present; `~/Library/LaunchAgents/` exists; `systemctl` absent; `man launchd.plist` (KeepAlive/RunAtLoad/ThrottleInterval semantics); `launchctl help bootstrap` usage; `watchdog.observers.api.BaseObserver.unschedule` source (thread-safe under `self._lock`)
- Phase 12/13 CONTEXT + REQUIREMENTS + ROADMAP (planning docs — locked decisions, not external claims)

### Secondary (MEDIUM confidence)
- FastAPI lifespan — https://fastapi.tiangolo.com/advanced/events/ (official docs, fetched this session)
- systemd user units + linger — freedesktop systemd v230 announcement, NixOS wiki Systemd/User Services, Baeldung (cross-verified, no live Linux box)
- Double-fork daemonization — Stevens APUE §13.3 lineage: Sander Marechal recipe, V8 testrunner daemon.py, pywikibot daemonize (cross-verified)
- Milestone research (in-repo, 2026-11-07): `.planning/research/STACK.md` (#6/#7, patterns), `ARCHITECTURE.md`, `FEATURES.md` — authoritative for recipes, superseded for module names by landed Phase 12 code

### Tertiary (LOW confidence)
- None used load-bearing. [ASSUMED] items are quarantined in the Assumptions Log.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new deps; every existing anchor read or executed locally this session
- Architecture (MCP hosts): HIGH — transport construction sites and FileWatcher contract read verbatim; lifespan pattern from official docs; one design question flagged (reconcile placement)
- Architecture (daemon/service): HIGH for macOS (local man page + launchctl verification), MEDIUM for systemd (cross-verified secondary sources only — structurally unverifiable on this machine)
- Pitfalls: HIGH — each anchored to a verified code fact or a cross-verified external recipe; PID-reuse and launchd-reinstall mitigations are recommendations, not verified cures

**Research date:** 2026-11-07
**Valid until:** 2027-01-07 (stable domain — stdlib/launchd/systemd semantics move slowly; watchdog capped) — recheck FastAPI lifespan API only if FastAPI major-bumps before implementation
