# Phase 13: Watch Everywhere (MCP-Embedded Refresh + Background Daemon) - Context

**Gathered:** 2026-11-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Host the proven Phase 12 watch loop in two new long-lived forms — the index stays fresh with no terminal window open:

1. **MCP-embedded refresh (LIVE-08)** — `SIF_MCP_WATCH=1` runs the watcher inside the MCP server (both stdio and HTTP transports) so AI-assistant queries always hit a fresh index; event handling never starves query handling.
2. **Detached daemon + lifecycle (LIVE-09)** — `sif watch --detach` backgrounds the watcher (stdlib double-fork); PID reported at detach, `--stop` terminates cleanly, `sif status` reports running state.
3. **Service install (LIVE-09)** — `sif watch --install-service` generates AND installs a launchd LaunchAgent (macOS) / systemd user unit (Linux); the service runs foreground under the supervisor (no forking) and survives login sessions.
4. **SIGKILL safety proof (SC4)** — a SIGKILLed daemon leaves no stale lock; restart succeeds immediately (Phase 11 flock semantics — needs proof, not new design).
5. **Long-lived host behaviors** — live rescope (collection add/remove without host restart), idle-time periodic WAL checkpointing, graceful schedule-failure warnings (inotify limits).

NOT in scope: pre-command staleness detection and staleness markers (Phase 14), search-quality work (Phases 15–16), wiring the `sif mcp daemon` stub (deferred — helper shaped for reuse only), auto-PollingObserver fallback UX (deferred), self-restart loops for the raw daemon (the supervisor's job).

</domain>

<decisions>
## Implementation Decisions

### MCP-embedded watch (LIVE-08)
- **D-01:** **Both transports** — stdio AND HTTP host the embedded watcher under `SIF_MCP_WATCH=1`; one `FileWatcher` core, transport-specific lifecycle wiring (stdio: threads around the serve loop; HTTP: FastAPI lifespan). SC1 then holds regardless of how a client launches the server. — **Reversibility:** reversible.
- **D-02:** **BM25-only depth, always** — the MCP-embedded watcher never embeds, regardless of `watch_update_depth`. Guards the billing-surprise vector: a remote-embedding config meeting a background host the user didn't launch with an explicit flag. Vector catch-up = `sif embed` or foreground `sif watch --embed`. Strict LIVE-05 reading for background hosts.
- **D-03:** **Coexistence via flock** — MCP watch + detached daemon + foreground watch may all run simultaneously; per-burst flock + wait-then-run (12-D04, 11-D02) serialize bursts. No stand-down/discovery protocol couples LIVE-08 to LIVE-09; stat-decides makes the loser's pass a cheap no-op.
- **D-04:** **Opt-in = env var only** — `SIF_MCP_WATCH` maps to a `mcp_watch` bool in Settings (standard `SIF_` convention; flows into docs/configuration.md via regeneration). No `--watch` flags on mcp commands — external clients spawn stdio directly, where the env var is the only lever.

### Detach & daemon lifecycle (LIVE-09 SC2)
- **D-05:** **PID file as management metadata** — `--detach` writes a small PID file next to the DB; `--stop` = read PID → SIGTERM → bounded wait → SIGKILL fallback; stale PID (process gone) reports "not running" and cleans the file up. Arbitration stays flock — REQUIREMENTS rejects PID-as-lock, not PID-as-pointer. Note the flock lock file cannot host this PID (per-burst locking means it is not held while idle).
- **D-06:** **Detach mechanics = stdlib double-fork** (fork → setsid → fork, stdio redirected to the log file/`/dev/null`; research recipe, ~30 lines). Under a supervisor the process NEVER forks (SC3) — `--detach` and service install are deliberately distinct paths.
- **D-07:** **Daemon logs default to the platform log dir** via platformdirs (`~/Library/Logs/sif/` on macOS, XDG state dir on Linux — matches the launchd recipe); `--log-file` overrides.
- **D-08:** **Running state extends `sif status`** — the existing top-level Rich table (and its `sif index status` alias) gains a Watch section: running yes/no, PID, host mode, depth. qmd precedent ("MCP: running (PID…)"). No separate `sif watch --status` surface.
- **D-09:** **`--detach` accepts the same flags as foreground** (`-c`, `--embed`) — the daemon IS `sif watch` backgrounded; `--embed` remains an explicit per-invocation opt-in (LIVE-05 holds). Embedding model lazy-loads and caches (research: "the daemon becomes the only process that should embed").
- **D-10:** **Raw-daemon crash policy = stay down** — no self-restart loop (duplicates KeepAlive/RestartSec badly and fights SC3's no-fork stance). Resilience belongs to the installed service (KeepAlive / Restart=on-failure baked in); `sif status` makes the down-state visible. SC4 is about clean flock state, which Phase 11 already provides.

### Service install (LIVE-09 SC3)
- **D-11:** **Flags on `sif watch`** — `--install-service` / `--uninstall-service`, same flag family as `--detach`/`--stop`. Depth/collection flags given at install time are baked into the generated ProgramArguments / ExecStart.
- **D-12:** **Install = write + enable + start** — generate the plist/unit, then `launchctl bootstrap gui/$(id -u)` (macOS) / `systemctl --user daemon-reload && systemctl --user enable --now` (Linux), verify it came up, print the log location. Explicit argv lists, never `shell=True`; friendly errors when launchctl/systemctl is missing (research recipe).
- **D-13:** **Both platforms, full** — plist (plistlib) and unit (template) generation implemented and tested cross-platform (generation is pure text; tests assert BOTH artifacts on ANY platform); live launchctl/systemctl invocation is exercised only where available (macOS dev box for launchd; systemd via mocked-subprocess tests). launchd keys per research: `RunAtLoad`, `KeepAlive`, `ThrottleInterval=10`, logs to `~/Library/Logs/sif/`; systemd: `Type=simple`, `Restart=on-failure`, `RestartSec=5`, `WantedBy=default.target`; `loginctl enable-linger` documented for survive-logout.
- **D-14:** **`sif mcp daemon` stub stays unwired** — the shared detach/daemon helper is shaped for reuse by it, but wiring is a backlog/roadmap item (no Phase 13 SC covers an MCP HTTP daemon).

### Long-lived host behaviors
- **D-15:** **Live rescope is IN scope for the long-lived hosts** (daemon + MCP watch): a light collections-table poll riding the existing periodic tick (recovery-tick precedent, 12-D12); added roots get scheduled + one reconcile pass; removed roots get unscheduled. Foreground watch keeps its restart-on-change MVP behavior. Rationale: a service-managed daemon that silently ignores a newly-added collection is a footgun — 12-CONTEXT named Phase 13 as this feature's home. — **Reversibility:** costly — grows the FileWatcher scheduling lifecycle API that Phase 14+ hosts also consume.
- **D-16:** **Idle-time periodic WAL checkpoint** — the daemon piggybacks `PRAGMA wal_checkpoint(TRUNCATE)` on the existing periodic ticks (minutes-scale; skip when a burst ran recently or the lock is contended). D-14's shutdown checkpoint stays the final word. Exact interval/conditions = Claude's discretion.
- **D-17:** **Schedule-failure handling = graceful warn** — a root that fails to schedule (inotify exhaustion / ENOSPC) logs cause + remedy (raise `fs.inotify.max_user_watches`); other roots keep watching; the recovery/reconcile machinery remains the backstop. Auto-PollingObserver fallback UX stays deferred.

### Carried forward (pre-decided in research/prior phases — do not re-litigate)
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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone research (authoritative recipes)
- `.planning/research/STACK.md` §"Key Integration Points" #6 — detach double-fork + the full launchd recipe (`~/Library/LaunchAgents/com.docsif.watch.plist`; `RunAtLoad`/`KeepAlive`/`ThrottleInterval=10`; `bootstrap`/`bootout`/`kickstart`) + systemd recipe (`~/.config/systemd/user/sif-watch.service`; `Type=simple`, `Restart=on-failure`, `RestartSec=5`, `WantedBy=default.target`; `enable --now`; linger) + safety rules (explicit argv, never `shell=True`, friendly missing-manager errors)
- `.planning/research/STACK.md` §"Key Integration Points" #7 — MCP embedded refresh: watchdog threads × asyncio bridged by `queue.Queue`; no janus; reuse the same incremental path as `sif watch`
- `.planning/research/STACK.md` §"Stack Patterns by Variant" (embed-in-daemon: lazy load, cached model, `--embed` off by default) + §"What NOT to Use" (python-daemon rejected — forking defeats supervisor exit tracking) + §"Alternatives Considered" (stdlib double-fork)
- `.planning/research/ARCHITECTURE.md` §"New/Changed Modules" (utils-level daemon helper shared by `sif watch --detach` and the `sif mcp daemon` slot) + §rejected alternatives (shared IPC watch daemon; unconditional MCP watch — opt-in required)
- `.planning/research/FEATURES.md` §"Table Stakes" row "MCP-embedded watch" (MEDIUM-HIGH; thread inside MCPServer; both transports; debounce so a sync storm never starves queries) + row "Status visibility" (qmd precedent: watcher running?, PID, last sync)

### Planning documents
- `.planning/REQUIREMENTS.md` — LIVE-08, LIVE-09 definitions; Out of Scope table (PID-file *arbitration* rejected; auto-embed as background default rejected — both shape D-05 and D-02)
- `.planning/ROADMAP.md` §"Phase 13" — goal and success criteria 1–4 (the acceptance contract)
- `.planning/phases/12-sif-watch-foreground-mvp/12-CONTEXT.md` — D-04 per-burst flock, D-06 `update_paths` seam, D-13 event rendering, D-14 shutdown precedent, and the deferred-to-13 items this phase picks up (rescope, checkpoint periodicity, inotify UX)
- `.planning/phases/11-live-index-foundation-concurrent-db-incremental-core/11-CONTEXT.md` — flock contract (D-01..D-03), connection factory, subprocess-test culture
- `.planning/PROJECT.md` §"Key Decisions" — WAL-before-any-second-writer ordering; Phase 12 watch pipeline decisions

### Project conventions
- `CLAUDE.md` — quality gates (pytest fail_under=90, ruff, ty), CLI error conventions, two-blank-lines style

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `FileWatcher` (`src/sif/indexing/watcher.py:307`) — the host-agnostic watch core both new hosts embed: `start()`/`stop(flush=)`/`recovery_tick()`, worker thread off the observer thread, `_run_burst`/`_run_reconcile`, `_EmbedSession` (lazy embed). Gains the rescope API (D-15).
- `watch_cmd` (`src/sif/cli/commands/watch.py:192`) — the foreground host: `SignalState`/`install_signal_handlers`/`shutdown_watcher` (D-14 flush + checkpoint), `_select_collections`, `_effective_depth`, banner/event rendering. `--detach` wraps this exact command; the service runs it foreground.
- `IncrementalIndexer` — `update_paths` (per-burst) + `update_collection` (startup reconcile); SC4's restart-proofness comes from per-burst flock by construction.
- `index_lock()` (`src/sif/database/locking.py:43`) — per-DB flock with wait-then-run deadline; every host's bursts go through it.
- `MCPServer` (`src/sif/mcp/server.py:40`) + transports (`src/sif/mcp/transports/stdio.py`, `http.py`) — where the embedded watcher hooks per transport (D-01); backend per-request connections are already WAL-safe via the factory.
- `Settings` watch fields (`src/sif/config/settings.py:44-65`) — `watch_debounce_interval`, `watch_ignore_patterns`, `watch_update_depth`, `watch_restat_interval`; `mcp_watch` bool joins here (D-04).
- `status_cmd` (`src/sif/cli/main.py:111`) — Rich table to extend with a Watch section (D-08); `sif index status` delegates to it.
- `mcp_daemon_cmd` stub (`src/sif/cli/commands/mcp.py:74`) — stays unwired (D-14); the shared helper is shaped for it.

### Established Patterns
- CLI lifecycle `with Database(...) as db:`; every connection through the Phase 11 factory (pragmas + sqlite-vec)
- Progress-event protocol (`"code payload"`) — new hosts render the same events (12-D13)
- Deterministic tests: synthetic watchdog events driven directly; subprocess tests where the parent holds/releases the lock and asserts the child's outcome; generous timeouts, never sleep-polling without a deadline (11-D08/D-09, 12-D15)
- Settings → `docs/configuration.md` via the generator's SECTIONS allowlist; `docs/cli-reference.md` regenerated by `make docs-generate` — both generator-owned, never hand-edited (12-03 precedent)

### Integration Points
- `src/sif/cli/commands/watch.py` — gains `--detach`, `--stop`, `--install-service`, `--uninstall-service`, `--log-file`
- `src/sif/mcp/transports/stdio.py` + `http.py` — watcher lifecycle hooks behind `mcp_watch`
- `src/sif/config/settings.py` — `mcp_watch` bool (+ tick/checkpoint interval fields at Claude's discretion)
- `src/sif/cli/main.py` `status_cmd` — Watch section (reads PID file + probe)
- New utils-level daemon helper (double-fork, PID file, stop) + new service-template module (plistlib + systemd unit generation, launchctl/systemctl invocation) — placement at Claude's discretion per research ARCHITECTURE
- `pyproject.toml` — no dependency changes (zero new deps)

</code_context>

<specifics>
## Specific Ideas

No specific external references — decisions above are self-contained. Construction notes worth preserving for the planner:

- Under a supervisor = foreground, never fork: `--detach` (double-fork) and `--install-service` (foreground) are deliberately distinct paths — this is the SC3 contract, not an implementation detail.
- SC4 proof shape: SIGKILL the daemon → immediately relaunch `sif watch --detach` → succeeds with no lock error and no cleanup. flock is released by the kernel on process death; the test proves it, no new code should be needed.
- D-02's rationale from discussion: a remote-embedding config plus a background host the user didn't explicitly launch with `--embed` is the billing-surprise vector; BM25-only is the strict LIVE-05 reading for such hosts. The detached daemon differs only because the user typed `--embed` themselves (D-09).

</specifics>

<deferred>
## Deferred Ideas

- **Wiring `sif mcp daemon`** (HTTP MCP server as a background daemon) — the shared helper supports it; not covered by any Phase 13 SC — backlog/roadmap item.
- **Auto-PollingObserver fallback on inotify exhaustion** — warning lands (D-17); the automatic fallback + detection UX is a Linux-hardening item for a later pass.
- **Embed compute split outside the flock window** — deferred from 12-D10; not raised in this discussion, stays deferred unless lock-hold bites.
- **Phase 14 ownership unchanged** — pre-command drift refresh + staleness markers stay in Phase 14.

</deferred>

---

*Phase: 13-Watch Everywhere (MCP-Embedded Refresh + Background Daemon)*
*Context gathered: 2026-11-07*
