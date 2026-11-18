---
phase: 22-mcp-sdk-v2-modernization-agent-packaging
plan: 03
subsystem: mcp
tags: [mcp, transport-security, host-guard, allowed-hosts, daemon, pid-file, corroboration, watch-coexistence, docs-generate]

# Dependency graph
requires:
  - phase: 22-mcp-sdk-v2-modernization-agent-packaging
    provides: "22-01 SDK composition root (build_transport_security, create_http_app, run_http) and the mounted /mcp transport security"
  - phase: 22-mcp-sdk-v2-modernization-agent-packaging
    provides: "22-02 seven-tool surface and the deleted hand-rolled shell (single SDK-owned /mcp security path)"
  - phase: 13-live-index
    provides: "utils/daemon.py double-fork/arming/corroborated-stop machinery and the watch daemon precedent"
provides:
  - "Loopback-union transport allowlists: explicit --allowed-hosts extends, never replaces, the defaults; a literal * is dropped"
  - "Narrow parent-level /health Host guard sharing the SDK allowlist (bad Host 421, allowed loopback 200)"
  - "Repeatable --allowed-hosts on mcp http and mcp daemon; --cors-origins on mcp daemon"
  - "Real detached mcp daemon: model-free arm, <db>.mcp.pid (mode mcp, depth bm25), HTTP bind after arming, PID cleanup in finally"
  - "Marker-aware corroborate_pid/stop_daemon (keyword-only marker, default watch) plus pid_path_for_mcp"
  - "POSIX real-process proofs: initialize over /mcp, --stop, bind-failure cleanup, watch coexistence, Windows refusal"
  - "Generated docs/cli-reference.md with both --allowed-hosts entries and the real daemon lifecycle help"
affects: [22-04, 22-05, 22-06, 22-07]

# Actuals (#2632) - pairs with the plan's `estimate` (92000 tokens, 3 tasks).
actuals:
  tokens: 14362
  tasks: 3
  commits: 3
plan_head_before: 7e5091a6b696ac24cea54db633471018bd0eaf20
plan_head_after: 6a1f06c4636aaa3880995ae08b8ab42dd7e7a1b1

tech-stack:
  added: []
  patterns:
    - "Allowlist assembly as defaults UNION explicit values, with '*' dropped rather than honored"
    - "FastAPI Header dependency for a narrow parent-level Host guard (HTTPException 421)"
    - "Keyword-only daemon marker defaulting to watch; each lifecycle owns a distinct <db>.<mode>.pid artifact"
    - "Arm-on-readiness daemon: quiet -> schema -> model-free backend -> PID, then bind; PID removed in finally"
    - "Real-CLI-subprocess e2e (not in-process fork) so ps corroboration sees the sif.cli.main argv"

key-files:
  created:
    - tests/unit/mcp/test_daemon.py
  modified:
    - src/sif/mcp/app.py
    - src/sif/mcp/cli.py
    - src/sif/cli/commands/mcp.py
    - src/sif/utils/daemon.py
    - tests/unit/mcp/test_transport_security.py
    - tests/unit/mcp/test_app.py
    - tests/unit/cli/test_mcp.py
    - tests/unit/utils/test_daemon.py
    - docs/cli-reference.md

key-decisions:
  - "Explicit --allowed-hosts values UNION the loopback defaults: a caller can add a bind name but can never remove loopback or disable the check, and a literal '*' is dropped instead of widening (D-13)."
  - "The /health Host guard is a FastAPI Header dependency over the same resolved allowlist and answers a bad Host with 421, matching the SDK's /mcp status (C2)."
  - "corroborate_pid/stop_daemon take a keyword-only marker with the literal default 'watch'; pid_path_for_mcp owns <db>.mcp.pid with mode='mcp'/depth='bm25', so watch and MCP daemons coexist and each --stop signals only its own process (D-20/C5)."
  - "The daemon arm callback calls set_quiet(True), opens/closes the schema database, constructs the model-free SearchBackend, then writes the PID; the HTTP host runs after detach and the PID is removed in finally on every exit path (D-21/T-22-19)."
  - "run_http_host is the named daemon host seam in src/sif/mcp/cli.py; run_http_server delegates to it, so the bind-failure path is testable without forking uvicorn."
  - "The e2e proofs launder the daemon through real `python -m sif.cli.main` subprocesses because a fork inside pytest would carry pytest's argv and fail ps corroboration, testing the wrong thing."

patterns-established:
  - "Host matching helper: exact entry or ':*' suffix, shared by the SDK settings and the /health guard"
  - "Four-class MCP daemon stop messaging (stopped / not running / permission denied / stale removed), parallel to watch"
  - "POSIX-only real-process daemon battery with deadline-bounded polls and a safety net that never leaks a detached process"

requirements-completed: [MCP-04, MCP-07]

coverage:
  - id: D1
    description: "The mounted /mcp app enforces the SDK Host/Origin/Content-Type matrix (bad Host 421, bad Origin 403, allowed 200, absent Origin 200, non-JSON 400)"
    requirement: MCP-04
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_transport_security.py#test_spoofed_host_is_rejected_with_421"
        status: pass
      - kind: unit
        ref: "tests/unit/mcp/test_transport_security.py#test_spoofed_origin_is_rejected_with_403"
        status: pass
      - kind: unit
        ref: "tests/unit/mcp/test_transport_security.py#test_non_json_content_type_is_rejected_with_400"
        status: pass
    human_judgment: false
  - id: D2
    description: "/health carries a narrow Host guard over the same allowlist (421 bad, 200 allowed loopback), and explicit allowed hosts extend rather than replace the loopback defaults with no '*'"
    requirement: MCP-04
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_transport_security.py#test_health_rejects_a_spoofed_host_with_421"
        status: pass
      - kind: unit
        ref: "tests/unit/mcp/test_transport_security.py#test_health_allows_an_allowed_loopback_host"
        status: pass
      - kind: unit
        ref: "tests/unit/mcp/test_app.py#test_build_transport_security_never_honors_a_wildcard_host"
        status: pass
      - kind: unit
        ref: "tests/unit/mcp/test_transport_security.py#test_non_loopback_bind_warns_and_keeps_loopback_only_defaults"
        status: pass
    human_judgment: false
  - id: D3
    description: "--allowed-hosts is repeatable and forwarded on mcp http; mcp daemon exposes --allowed-hosts/--cors-origins/--pid-file/--log-file/--stop"
    requirement: MCP-04
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_mcp.py#test_http_allowed_hosts_are_repeatable_and_forwarded"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_mcp.py#test_daemon_help_lists_lifecycle_and_security_flags"
        status: pass
    human_judgment: false
  - id: D4
    description: "The MCP daemon owns <db>.mcp.pid (mode mcp, depth bm25); marker-aware corroboration defaults to watch, and mcp --stop only signals a corroborated MCP process"
    requirement: MCP-07
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_daemon.py#TestMcpPidArtifact"
        status: pass
      - kind: unit
        ref: "tests/unit/mcp/test_daemon.py#TestMcpCorroboration"
        status: pass
      - kind: unit
        ref: "tests/unit/utils/test_daemon.py#TestStopEscalation::test_marker_is_forwarded_and_defaults_to_watch"
        status: pass
    human_judgment: false
  - id: D5
    description: "A real POSIX daemon arms, serves a spec-valid 2024-11-05 initialize on /mcp, stops via --stop, and removes its PID; a bind failure cleans the PID and propagates; watch coexistence leaves .watch.pid and the watch process alive; Windows refuses with cause/remedy"
    requirement: MCP-07
    verification:
      - kind: e2e
        ref: "tests/unit/mcp/test_daemon.py#TestMcpDaemonEndToEnd::test_daemon_e2e_serves_initialize_and_stops"
        status: pass
      - kind: unit
        ref: "tests/unit/mcp/test_daemon.py#TestMcpDaemonEndToEnd::test_daemon_bind_failure_removes_pid_and_propagates"
        status: pass
      - kind: e2e
        ref: "tests/unit/mcp/test_daemon.py#TestMcpDaemonEndToEnd::test_daemon_coexists_with_a_watch_daemon"
        status: pass
      - kind: unit
        ref: "tests/unit/mcp/test_daemon.py#TestMcpDaemonEndToEnd::test_windows_daemon_refusal_names_posix_cause_and_foreground_remedy"
        status: pass
    human_judgment: false
  - id: D6
    description: "make docs-generate publishes both --allowed-hosts entries and the real daemon help, leaves a byte-clean second run, and contains zero 'not implemented' claims"
    requirement: MCP-04
    verification:
      - kind: other
        ref: "make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md"
        status: pass
      - kind: other
        ref: "grep -c -- '--allowed-hosts' docs/cli-reference.md == 2; grep -c 'not implemented' docs/cli-reference.md == 0"
        status: pass
    human_judgment: false

# Metrics
duration: 11min
completed: 2026-11-16
status: complete
---

# Phase 22 Plan 03: Transport Security, `/health` Guard, and the Real MCP Daemon Summary

**SDK-backed Host/Origin defense with a narrow `/health` Host guard and repeatable `--allowed-hosts`, plus a real detached `mcp daemon` owning `<db>.mcp.pid` and a distinct corroboration marker so it coexists with the watch daemon**

## Performance

- **Duration:** ~11 min
- **Started:** 2026-11-16T07:40:15Z
- **Completed:** 2026-11-16T07:51:06Z
- **Tasks:** 3
- **Files modified:** 10 (4 source, 5 test, 1 generated doc)

## Accomplishments

- `build_transport_security` now assembles the allowlist as loopback defaults UNION explicit `--allowed-hosts` values. A caller can add a bind name but can never remove loopback or disable the check; a literal `*` is dropped rather than honored. Origins keep `--cors-origins`/`DEFAULT_CORS_ORIGINS`, with a literal `*` likewise dropped.
- `/health` gained a narrow FastAPI `Header` dependency over the same resolved allowlist: a spoofed `Host` returns 421 (matching the SDK's `/mcp` status), an allowed loopback Host returns 200, and a missing Host fails closed. `CORSMiddleware` remains for preflight/response headers.
- `--allowed-hosts` is repeatable on both `mcp http` and `mcp daemon`; `--cors-origins` moved onto `mcp daemon` as well. A non-loopback bind without explicit hosts logs a warning naming the cause and the flag and keeps the loopback-only allowlist — no silent widening.
- `mcp daemon` is now a real detached HTTP daemon: it arms quietly (`set_quiet`), opens and closes the schema database, constructs the model-free `SearchBackend`, writes `<db>.mcp.pid` with `mode: "mcp"` and `depth: "bm25"`, then binds after `detach`. Any exit path removes the PID in `finally`, including a bind failure that propagates non-zero.
- `corroborate_pid`/`stop_daemon` accept a keyword-only `marker` (literal default `"watch"`, preserving every watch behavior); `pid_path_for_mcp` yields `<db>.mcp.pid`. `mcp daemon --stop` resolves the MCP path with `--pid-file` override and signals only a corroborated MCP process; a live watch daemon is never reclassified as stale.
- Windows refuses before any log/PID work with the POSIX-fork cause and the foreground `sif mcp http` remedy; the daemon serves HTTP only and its help says stdio is not a daemon mode.
- The POSIX e2e proves the whole lifecycle with real `python -m sif.cli.main` subprocesses: a spec-valid 2024-11-05 `initialize` on a pre-reserved ephemeral port, `--stop` exiting 0, PID removal, a second `--stop` reporting not running, and a watch daemon on the same index surviving untouched (`.watch.pid` present and process alive).
- `make docs-generate` published both `--allowed-hosts` entries and the real daemon help; a second run is byte-clean and `not implemented` is absent (was 2 at HEAD).

## Task Commits

Each task was committed atomically:

1. **Task 1: Host/Origin allowlists, `/health` guard, and repeatable `--allowed-hosts`** - `4aa3022` (feat)
2. **Task 2: Real `mcp daemon` with an MCP PID artifact and mode-aware corroboration** - `446b424` (feat)
3. **Task 3: Daemon end-to-end proof, bind-failure cleanup, watch coexistence, and generated docs** - `6a1f06c` (feat)

**Plan metadata:** docs commit created after this SUMMARY (not counted in `actuals.commits`).

## Files Created/Modified

- `src/sif/mcp/app.py` - allowlist union/`*` drop, `_host_is_allowed`, `_make_health_host_guard`, `/health` dependencies
- `src/sif/mcp/cli.py` - `run_http_host` daemon host seam; `run_http_server` delegates
- `src/sif/cli/commands/mcp.py` - `--allowed-hosts` on http; full daemon command (arm/host/stop, log default, Windows refusal)
- `src/sif/utils/daemon.py` - `_PID_SUFFIX_MCP`, `pid_path_for_mcp`, marker-aware `corroborate_pid`/`stop_daemon`
- `tests/unit/mcp/test_transport_security.py` - health 421/200, explicit-host acceptance, non-loopback warning
- `tests/unit/mcp/test_app.py` - allowlist union and wildcard-drop assertions
- `tests/unit/cli/test_mcp.py` - option plumbing, daemon stop classes, Windows refusal
- `tests/unit/utils/test_daemon.py` - five marker-accepting fakes + marker forwarding
- `tests/unit/mcp/test_daemon.py` - PID artifact/corroboration/stop battery plus the POSIX e2e proofs
- `docs/cli-reference.md` - generated daemon and `--allowed-hosts` sections

## Decisions Made

- See frontmatter `key-decisions`. The most load-bearing: explicit hosts union the loopback defaults (never replace/disable), the `/health` guard shares the resolved SDK allowlist, and the daemon marker is a keyword-only parameter defaulting to the literal `watch` so existing watch behavior is byte-preserved.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] The plan's absence grep forbade an explanatory `load_model` mention**
- **Found during:** Task 2 (source guard)
- **Issue:** The verify step runs `grep -rn "load_model" src/sif/cli/commands/mcp.py; test $? -eq 1`; a comment explaining the arm is model-free contained the literal token and failed the guard.
- **Fix:** Reworded the comment to "no eager model load" — no code or behavior change.
- **Files modified:** `src/sif/cli/commands/mcp.py`
- **Committed in:** `446b424`

**2. [Rule 1 - Bug] Bind-failure test seeded an ambient-dimension schema before patching 8-dim settings**
- **Found during:** Task 3 (bind-failure test)
- **Issue:** `_seed_db` ran before the test settings patch, creating a FLOAT[1024] schema; the arm then constructed the backend with `embedding_dim=8`, raising `IdentityDimensionError` before the injected `OSError`.
- **Fix:** Patch `sif.config.settings.get_settings` and `sif.mcp.backend.get_settings` before seeding so the schema and the arm agree on the dimension.
- **Files modified:** `tests/unit/mcp/test_daemon.py`
- **Verification:** The bind-failure test now asserts the propagated `OSError` and PID removal.
- **Committed in:** `6a1f06c`

### Plan Notes (not deviations)

- `tests/unit/mcp/test_app.py`'s `/health` 200 assertion already constructed `TestClient(app, base_url="http://localhost")`; no adaptation was needed, and the existing test now exercises the new guard.
- "Refuses stdio daemon mode" is expressed structurally: `mcp daemon` has no transport option and serves Streamable HTTP only, with the help stating `sif mcp stdio` is not a daemon mode.
- Task 1 did not need an `src/sif/mcp/cli.py` change (the wrapper already forwarded `allowed_hosts`); Task 2 added `run_http_host` there.

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both fixes were test/comment-level; no public contract or runtime behavior changed.

## Issues Encountered

- The in-process fork path cannot be used for the daemon e2e: the grandchild in a pytest process carries pytest's argv, so ps corroboration correctly refuses it. The proofs use real `python -m sif.cli.main` subprocesses, which is also the production argv shape. The safety net stops/kills any leaked daemon even on assertion failure.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 22-04 can wire query parity/lazy degradation on top of the now-complete HTTP security surface; `run_http` still owns the non-loopback warning and `set_quiet`.
- The generated `docs/cli-reference.md` now carries the real daemon help; any later flag change must re-run `make docs-generate` (never hand-edit).
- The daemon lifecycle is proven on POSIX only by design; Windows remains the foreground `mcp http` path (D-19).
- No blockers introduced.

## Self-Check: PASSED

`tests/unit/mcp/test_daemon.py` and `docs/cli-reference.md` exist on disk; all three task commits (`4aa3022`, `446b424`, `6a1f06c`) are ancestors of HEAD; the full suite is green at 2769 passed / 1 skipped / 95.09% coverage.
