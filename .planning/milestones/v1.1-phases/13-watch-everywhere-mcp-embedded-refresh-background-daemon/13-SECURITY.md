---
phase: "13"
slug: "watch-everywhere-mcp-embedded-refresh-background-daemon"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-08"
---

# Phase 13 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| collections table → rescope diff → observer scheduling (13-01) | A collection row added/removed by any process becomes live watch scope without host restart | collection rows (paths, names) |
| worker connection → `PRAGMA wal_checkpoint(TRUNCATE)` (13-01) | The tick issues a checkpoint that can interact with concurrent readers/writers | WAL state |
| PID file on disk (any local process can write it) → `--stop` signal decision (13-02) | The file is untrusted input: parse defensively, corroborate before any signal | PID + argv metadata |
| daemon log file (user-writable dir) (13-02) | sif-generated content only; 0644 in a user-owned dir matching the launchd StandardOutPath contract | event text: document paths/names |
| signals (SIGTERM from `--stop`, SIGKILL from SC4) → daemon shutdown path (13-02) | Bounded graceful path; kernel-released flock keeps arbitration correct on SIGKILL | OS signals |
| `SIF_MCP_WATCH` env → background writer inside a server the user did not flag-launch (13-03) | Opt-in must gate the watcher AND its depth (no background embedding) | env flag |
| watcher thread → stdout (the JSON-RPC channel) (13-03) | Any stray print corrupts the protocol stream the AI client parses | log/event output |
| filesystem events → index writes concurrent with query reads (13-03) | WAL + per-request connections keep readers correct; per-burst flock serializes writers | index mutations |
| install flags + resolved paths → generated plist/unit → OS service manager (13-04) | Everything embedded in ProgramArguments/ExecStart derives from flags and resolved absolute paths — no user free-text reaches a shell | argv, paths |
| artifact destinations (`~/Library/LaunchAgents`, `~/.config/systemd/user`) (13-04) | User-owned dirs; only our own label's file is written or removed | plist/unit files |
| manager binaries invoked via subprocess (13-04) | Explicit argv only; missing-binary and failure paths must degrade to friendly errors | process invocation |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-13-01 | Tampering | `_watch_states`/dict mutation from a non-worker thread (rescope called off-thread) → KeyError/racing observer mutations | medium | mitigate | Worker-thread-only contract documented in `rescope` docstring (`src/sif/indexing/watcher.py:540`); the only production caller is the tick; tests invoke directly with the worker quiesced | closed |
| T-13-02 | DoS | tick stalls on `wal_checkpoint(TRUNCATE)` against a contended DB (Pitfall 7) | medium | mitigate | Disabled unless `checkpoint_interval > 0`; busy result row → silent skip; deadline resets whether or not the checkpoint ran; recent-burst window skip (`src/sif/indexing/watcher.py:645-684`) | closed |
| T-13-03 | DoS | `--stop` killing an innocent process after PID reuse (Pitfall 3) | high | mitigate | Fail-closed `corroborate_pid`: ps command line must contain sif watch argv markers as its own token; ProcessLookup/ps-missing/mismatch → stale handling, never a signal (`src/sif/utils/daemon.py:150-176`, gated at `:283`) | closed |
| T-13-04 | Tampering | pre-planted/symlinked or hand-edited PID file driving a kill or a crash | medium | mitigate | 0600 create via `os.open` (`src/sif/utils/daemon.py:106`); defensive JSON parse — ANY defect reads back as None → not-running + cleanup (`:117-128`); no world-writable creates; file is metadata only (D-05) | closed |
| T-13-05 | DoS | daemon child forked after threads/resources exist → malloc/GIL deadlock in the child (Pitfall 2) | medium | mitigate | `--detach` double-forks FIRST — before Database, observer, or any thread (`src/sif/utils/daemon.py:187-233`); e2e detach test would hang/fail on violation | closed |
| T-13-06 | Information Disclosure | daemon log carries document paths/names | low | accept | Event protocol carries paths/names only (Phase 12 contract); log dir is user-owned single-user machine; matches the launchd log-tree convention D-07 deliberately joins — see Accepted Risks Log | closed |
| T-13-07 | Tampering | watch callbacks writing to stdout corrupting the stdio JSON-RPC stream (Pitfall 1) | high | mitigate | Logger-only renderers — `get_logger` stderr handlers (`src/sif/mcp/watch_host.py:13-15,68`); e2e asserts every stdout line parses as JSON during a live burst; unit test pins stdout-empty callbacks | closed |
| T-13-08 | DoS | embedded watcher embedding (remote-API billing surprise) despite no explicit user flag | high | mitigate | Depth forced to the module literal `_MCP_WATCH_DEPTH = "bm25"` in construction — never read from settings; unit-pinned even under `SIF_WATCH_UPDATE_DEPTH=embed` (D-02) (`src/sif/mcp/watch_host.py:49`) | closed |
| T-13-09 | DoS | startup reconcile blocking the initialize handshake → client timeout kills the server (Pitfall 4) | medium | mitigate | Serve-first: watcher starts immediately, reconcile enqueued as first worker jobs via `_enqueue_startup_reconcile` (`src/sif/mcp/watch_host.py:93-101,156-158`); e2e pins handshake latency under drift | closed |
| T-13-10 | Elevation | shell injection through install flags/paths into launchctl/systemctl | high | mitigate | Explicit argv lists exclusively — zero `shell=True` in `src/sif/utils/service.py`; plist values via plistlib (typed, escaped); unit ExecStart from validated absolute paths (D-12) | closed |
| T-13-11 | Tampering | pre-planted file/symlink at the plist/unit destination swapped into service position | medium | mitigate | Atomic write-temp-then-rename with 0644 via `os.replace` into user-owned dirs (`src/sif/utils/service.py:181-193`); only our own label's filename is ever written or removed; no world-writable creates | closed |
| T-13-12 | Elevation | another local user planting/capturing the service definition | low | mitigate | Destinations are user-scoped (`~/Library/LaunchAgents`, `~/.config/systemd/user`) with explicit modes (`src/sif/utils/service.py:171-176`); single-user local tool per REQUIREMENTS positioning | closed |
| T-13-13 | DoS | re-install over an already-bootstrapped label leaves partial/stale service state (Pitfall 5) | low | mitigate | Bootout-then-bootstrap on conflict, post-install verify via `launchctl print` / `is-active`, output names the artifact path (`src/sif/utils/service.py:292-306`) | closed |
| T-13-SC | Tampering | package installs introducing malicious/typo-squatted dependencies (locked across all four plans) | high | mitigate | Zero-new-runtime-deps lock held: no `pyproject.toml` dependency commits during phase 13 (last dependency change 10d652a, phase 12); no pip-install steps in any plan execution | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-13-01 | T-13-06 | Daemon log carries document paths/names. The event protocol carries paths/names only (no content); the log dir is user-owned on a single-user machine; this matches the launchd log-tree convention (D-07) the phase deliberately joins. | Plan 13-02 (threat model, disposition: accept) | 2026-11-07 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-08 | 14 | 14 | 0 | gsd-secure-phase (ASVS L1, plan-time register, short-circuit: no open threats) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-08
