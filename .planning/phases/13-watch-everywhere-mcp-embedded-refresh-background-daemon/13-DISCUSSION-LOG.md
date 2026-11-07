# Phase 13: Watch Everywhere (MCP-Embedded Refresh + Background Daemon) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-07
**Phase:** 13-Watch Everywhere (MCP-Embedded Refresh + Background Daemon)
**Areas discussed:** MCP watch shape, Daemon lifecycle, Service install UX, Long-lived extras

---

## MCP watch shape

### Q1: Which MCP transports host the embedded watcher when SIF_MCP_WATCH=1 is set?

| Option | Description | Selected |
|--------|-------------|----------|
| Both stdio + HTTP (Recommended) | Works however the server is launched (Claude Desktop stdio spawn or `sif mcp http`); one FileWatcher core, two lifecycle hooks; SC1 holds for any client | ✓ |
| stdio only | Common AI-assistant integration; smaller test surface; SC1 becomes transport-conditional | |
| HTTP only | Natural long-lived host, but misses the main AI-assistant spawn path | |

**User's choice:** Both stdio + HTTP
**Notes:** —

### Q2: What update depth does the MCP-embedded watcher run at?

| Option | Description | Selected |
|--------|-------------|----------|
| BM25-only, always (Recommended) | Background host ⇒ embedding never runs as background default (LIVE-05); guards remote-API billing surprise; vectors catch up via `sif embed` / foreground `--embed` | ✓ |
| Honor watch_update_depth | Same rule as `sif watch`; the setting is itself an opt-in, but one step removed from starting a background server | |

**User's choice:** BM25-only, always
**Notes:** —

### Q3: Detached daemon AND MCP watch running simultaneously — what happens?

| Option | Description | Selected |
|--------|-------------|----------|
| Coexist via flock (Recommended) | Per-burst flock + wait-then-run serialize bursts; no discovery protocol; loser's pass no-ops on fresh checksums | ✓ |
| Stand down if daemon runs | Avoids duplicate work but couples LIVE-08 to LIVE-09 and reintroduces stale-detection swamp flock exists to avoid | |

**User's choice:** Coexist via flock
**Notes:** —

### Q4: How is the embedded watcher enabled?

| Option | Description | Selected |
|--------|-------------|----------|
| Env var only (Recommended) | `SIF_MCP_WATCH` → `mcp_watch` bool setting (standard SIF_ convention, auto-documented); one spelling for every launch path | ✓ |
| Env var + --watch flag | Inline override on mcp commands; more surface, doesn't help external stdio spawns | |

**User's choice:** Env var only
**Notes:** —

## Daemon lifecycle

### Q1: How do `sif watch --stop` and status reporting find the running daemon?

| Option | Description | Selected |
|--------|-------------|----------|
| PID file (Recommended) | Management metadata next to the DB; SIGTERM → bounded wait → SIGKILL; flock lock file can't host the PID (per-burst, not held idle); REQUIREments rejects PID-as-lock only | ✓ |
| Process-table scan | No state file, but fragile matching across platforms/invocation styles | |

**User's choice:** PID file
**Notes:** —

### Q2: Where does the detached daemon write its logs by default?

| Option | Description | Selected |
|--------|-------------|----------|
| Platform log dir (Recommended) | platformdirs (`~/Library/Logs/sif/` macOS / XDG state dir Linux); matches launchd recipe; `--log-file` overrides | ✓ |
| Next to the DB | One location, but DB dirs get sync'd/backed-up | |
| Silent by default | `/dev/null` unless `--log-file`; undebuggable daemon | |

**User's choice:** Platform log dir
**Notes:** —

### Q3: Where does the user ask "is watch running?" (SC2)

| Option | Description | Selected |
|--------|-------------|----------|
| Extend `sif status` (Recommended) | Existing top-level Rich table (+ `sif index status` alias) gains a Watch section (running, PID, mode, depth); qmd precedent | ✓ |
| `sif watch --status` flag | Self-contained but splits index state across commands | |
| Both | Most discoverable, two code paths for one question | |

**User's choice:** Extend `sif status`
**Notes:** —

### Q4: What update depth can the detached daemon run at?

| Option | Description | Selected |
|--------|-------------|----------|
| Same flags as foreground (Recommended) | Daemon = `sif watch` backgrounded; `--embed` stays explicit per-invocation opt-in; research anticipates lazy-load + cached model | ✓ |
| BM25-only daemon | Simplest billing story, but blocks always-fresh vectors without a terminal — the case "watch everywhere" names | |

**User's choice:** Same flags as foreground
**Notes:** —

## Service install UX

### Q1: How is service install spelled on the CLI?

| Option | Description | Selected |
|--------|-------------|----------|
| Flags on `sif watch` (Recommended) | `--install-service` / `--uninstall-service`, same family as `--detach`/`--stop` (SC2 precedent); install-time depth flags baked into ProgramArguments/ExecStart | ✓ |
| Subcommand group | Cleaner grammar but reshapes the Phase 12 command tree | |

**User's choice:** Flags on `sif watch`
**Notes:** —

### Q2: What does `sif watch --install-service` actually do?

| Option | Description | Selected |
|--------|-------------|----------|
| Write + enable + start (Recommended) | Generate, `launchctl bootstrap` / `systemctl --user daemon-reload && enable --now`, verify, print log location; explicit argv, friendly missing-manager errors | ✓ |
| Write only | Safest, but SC3's "installed" becomes a manual documented step | |

**User's choice:** Write + enable + start
**Notes:** —

### Q3: Platform coverage for service install?

| Option | Description | Selected |
|--------|-------------|----------|
| Both, full (Recommended) | plist + unit generation implemented and content-tested cross-platform (pure text); live launchctl/systemctl native-platform only (macOS dev box / mocked) | ✓ |
| macOS first-class only | Faster, but Linux gets a half-feature | |

**User's choice:** Both, full
**Notes:** —

### Q4: Is wiring the existing `sif mcp daemon` stub part of this phase?

| Option | Description | Selected |
|--------|-------------|----------|
| Defer, share helper (Recommended) | Not in any Phase 13 SC; helper shaped for reuse; wiring is backlog | ✓ |
| Wire it in Phase 13 | Proves the helper but grows the phase beyond its four SCs with a fresh surface | |

**User's choice:** Defer, share helper
**Notes:** —

## Long-lived extras

### Q1: Live rescope — in scope for Phase 13?

| Option | Description | Selected |
|--------|-------------|----------|
| In scope for long-lived hosts (Recommended) | Collections-table poll riding the existing tick; added roots scheduled + reconciled, removed unscheduled; foreground keeps restart-on-change; 12-CONTEXT named Phase 13 as its home | ✓ |
| Defer again | Smaller phase, but a service-managed daemon silently ignoring new collections is a footgun | |

**User's choice:** In scope for long-lived hosts
**Notes:** —

### Q2: Periodic WAL checkpointing for the long-running daemon?

| Option | Description | Selected |
|--------|-------------|----------|
| Idle-time periodic (Recommended) | `wal_checkpoint(TRUNCATE)` piggybacked on existing ticks, minutes-scale, skip-if-recent-burst/contended; shutdown checkpoint stays final | ✓ |
| Shutdown-only (status quo) | Zero new machinery, but `-wal` sits large for weeks-long daemons | |

**User's choice:** Idle-time periodic
**Notes:** —

### Q3: When the raw (non-service) detached daemon crashes or is SIGKILLed, what happens?

| Option | Description | Selected |
|--------|-------------|----------|
| Stay down; supervisor revives (Recommended) | Resilience = installed service (KeepAlive / Restart=on-failure); `sif status` shows down; no crash-looping without supervisor backoff | ✓ |
| Self-restart loop | Watch-everywhere without a service, but duplicates supervisors badly and fights SC3 no-fork | |

**User's choice:** Stay down; supervisor revives
**Notes:** —

### Q4: inotify watch-limit exhaustion on Linux daemons — how far does Phase 13 go?

| Option | Description | Selected |
|--------|-------------|----------|
| Graceful warn, defer fallback UX (Recommended) | Warning names cause + remedy; other roots keep watching; reconcile machinery is the backstop | ✓ |
| Full auto-fallback now | Complete research prescription, but untestable on macOS except by simulation and not in any SC | |

**User's choice:** Graceful warn, defer fallback UX
**Notes:** —

## Claude's Discretion

- PID file name/path derivation; `--stop` wait bounds and SIGKILL escalation timing
- Double-fork implementation details; parent/child handshake before printing PID
- Rescope poll interval and diffing mechanics (must ride the existing tick)
- Checkpoint interval / skip conditions
- Service label naming; plist/unit authorship details; uninstall semantics (stop-then-remove)
- Transport lifecycle wiring specifics; FileWatcher restructuring freedom (clean start/stop contract)
- `sif status` Watch-section rendering; "last sync time" optional
- Test scaffolding for detach/service paths (deterministic subprocess tests per 11/12 culture)
- Settings field names beyond `mcp_watch`; docs regeneration via `make docs-generate`

## Deferred Ideas

- Wiring `sif mcp daemon` (HTTP server as daemon) — helper supports it; backlog item
- Auto-PollingObserver fallback on inotify exhaustion — Linux-hardening pass
- Embed compute split outside the flock window — stays deferred from 12 unless lock-hold bites
