---
phase: 13-watch-everywhere-mcp-embedded-refresh-background-daemon
plan: 02
subsystem: infra
tags: [daemon, double-fork, pidfile, launchd-prep, flock, watch-lifecycle, status]

requires:
  - phase: 13-01
    provides: [rescope seam, tick checkpoint, watch settings]
provides:
  - src/sif/utils/daemon.py — stdlib double-fork detach with pipe handshake, 0600 PID-file artifact (metadata, never arbitration), fail-closed ps corroboration, SIGTERM→SIGKILL stop escalation; shaped for the future sif mcp daemon slot (D-14)
  - watch_cmd --detach/--stop/--log-file lifecycle flags with guards; module-level run_watch_host(WatchHostParams) shared verbatim by foreground and daemon child (D-09)
  - Daemon wiring of the 13-01 seam — rescope-within-filter provider + rescope/checkpoint intervals from settings (D-15/D-16)
  - status_cmd Watch section (running/PID/mode/depth, stale cleanup) on both sif status and the sif index status alias (D-08)
  - SC4 proof: SIGKILL leaves no stale lock; immediate re-detach succeeds with no cleanup
affects: [13-04 service install + docs regeneration, sif status UX]

actuals:
  tokens: 17290   # chars/4 over the realized diff (69159 chars across 7 files, 1551 insertions / 90 deletions)
  tasks: 2
  commits: 5      # measured: git rev-list --count 6a45a53..HEAD (2x RED + 2x GREEN + 1 dangling-lint-fix commit)
plan_head_before: 6a45a534655f4196b2438d1272c1752fe8abe238
plan_head_after: 9bbd37d5c1cf7452b25357b7e18960a2efbf069e

tech-stack:
  added: []       # zero new deps — stdlib os/signal/subprocess/select + existing platformdirs (D-13/SC lock held)
  patterns:
    - "Pipe-handshake double-fork: armed means schema+collections+PID-file written; the printed PID always refers to a ready daemon"
    - "PID file as management metadata mirroring locking.py's docstring discipline — 0600 sibling artifact, defensive parse, never a gate"
    - "Fail-closed corroboration: ps argv must carry sif.cli.main AND a standalone 'watch' token; a 'watch.db' path fragment never corroborates"
    - "Shared host body via WatchHostParams struct (WatchConfig bundling precedent); daemon derives its copy with dataclasses.replace wiring the long-lived opt-ins"
    - "Graceful daemon exit removes its own PID file so --stop/status stay honest without a cleanup pass"

key-files:
  created:
    - src/sif/utils/daemon.py
    - tests/unit/utils/test_daemon.py
    - tests/integration/test_watch_daemon_e2e.py
  modified:
    - src/sif/cli/commands/watch.py - run_watch_host + WatchHostParams extraction, --detach/--stop/--log-file + guards, _run_detach (fork-first), _daemon_log_path (D-07), _daemon_rescope_provider (D-15), _run_stop
    - src/sif/cli/main.py - _watch_status_text + Watch row inside status_cmd (single path for both surfaces)
    - tests/unit/cli/test_watch_cmd.py - flag guards, help surface, D-07 log-path units
    - tests/unit/cli/test_status.py - TestWatchSection battery (running/stale×2/missing/alias)

key-decisions:
  - "The detach handshake is a single pipe message (armed <pid> / error <msg>) with a 30s bounded select read; parent timeout or EOF is a reported failure, exit non-zero — never a silent maybe-detach"
  - "'watch' corroboration marker is token-based (command.split()), not substring: a reused PID whose argv merely contains 'watch.db' (e.g. an MCP stdio process) must never corroborate"
  - "run_watch_host takes an OPEN Database whose lifecycle the caller owns; arm() opens it in the grandchild, the daemon wraps it in `with db:` and unlinks its PID file in the finally"
  - "Daemon rescope provider reads the collections table through the shared worker connection (provider runs on the worker thread via the 13-01 tick) and withholds non-`-c` names — rescope-within-the-filter"
  - "stop_daemon exposes term/kill/poll/now parameters so the escalation unit battery runs in milliseconds — the CLI calls with the 10s/5s defaults"
  - "Foreground watch is unchanged in behavior: it passes no rescope/checkpoint opt-ins, so restart-on-change (12 MVP) is preserved"

patterns-established:
  - "Lifecycle-flag family on watch_cmd follows mcp_daemon_cmd (--detach/--stop/--log-file as is_flag/path options with guard ClickExceptions)"
  - "E2E daemon safety net: context manager runs the real detach parent, asserts exit 0 + PID line, and guarantees --stop→SIGKILL cleanup in finally — a detached daemon never leaks past a failing test"
  - "Metadata display hardening: the status Watch probe is wrapped so no PID-file artifact issue can take the status command down (renders not-running + logger.debug instead)"

requirements-completed: [LIVE-09]   # declared by this plan; shared-ID gate holds it open (13-04 also declares LIVE-09 and is pending)

coverage:
  - id: D1
    description: "SC2 detach lifecycle end-to-end: --detach prints the daemon PID before parent exit 0; PID file payload matches the printed PID (mode=daemon, depth); a live file change is indexed with no terminal attached; --stop exits 0, daemon gone, PID file removed"
    requirement: LIVE-09
    verification:
      - kind: integration
        ref: "tests/integration/test_watch_daemon_e2e.py#test_detach_backgrounds_watcher_and_indexes_live_changes (pass, twice in a row per acceptance criterion)"
        status: pass
    human_judgment: false
  - id: D2
    description: "--stop drives the D-14 graceful path: no traceback in the daemon log, -wal truncated to 0 bytes after exit (holder-connection proof), stop subprocess exit 0"
    requirement: LIVE-09
    verification:
      - kind: integration
        ref: "tests/integration/test_watch_daemon_e2e.py#test_stop_terminates_gracefully_with_wal_truncate (pass)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Stop idempotence and flag surface: no PID file -> not-running notice exit 0; --detach+--stop and --log-file-without---detach rejected; --help lists the three flags; D-07 default platform log dir with --log-file override"
    requirement: LIVE-09
    verification:
      - kind: integration
        ref: "tests/integration/test_watch_daemon_e2e.py#test_stop_without_daemon_prints_not_running (pass)"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_watch_cmd.py#TestDaemonFlagGuards + TestDaemonLogPath (5 tests, pass)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Hermetic daemon unit battery (zero real forks/kills): pid_path_for sibling derivation; 0600 write/read round-trip; parametrized defective payloads -> None; fail-closed corroboration (markers/unrelated/gone/ps-missing/ps-fail/watch-in-path-fragment); stop escalation order (TERM before KILL, KILL only after bounded wait, gone-before-signal, stale-only-unlinks); CLI stop messages"
    requirement: LIVE-09
    verification:
      - kind: unit
        ref: "tests/unit/utils/test_daemon.py (20 tests across TestPidPath/TestPidPayload/TestCorroboratePid/TestStopEscalation/TestStopCliPath, pass)"
        status: pass
    human_judgment: false
  - id: D5
    description: "D-08 status Watch section: running row renders PID/mode/depth from the corroborated payload; corroborate-False, garbage, and missing-file paths render not-running wording with stale cleanup where applicable; the same code path renders for sif status and the sif index status alias"
    requirement: LIVE-09
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_status.py#TestWatchSection (5 tests incl. index-status alias, pass)"
        status: pass
    human_judgment: false
  - id: D6
    description: "SC4 SIGKILL/restart proof: daemon A SIGKILLed at steady state; immediate re-detach parent exits 0 with a new PID, PID file overwritten (metadata, never a gate); replacement daemon indexes a subsequent change and stops cleanly; no lock-error markers or tracebacks in either log — per-burst flock is kernel-released on death, no new production code"
    requirement: LIVE-09
    verification:
      - kind: integration
        ref: "tests/integration/test_watch_daemon_e2e.py#test_sigkill_then_immediate_redetach_succeeds (pass)"
        status: pass
    human_judgment: false

duration: 28min
completed: 2026-11-07
status: complete
---

# Phase 13 Plan 02: Detached Daemon Lifecycle (Detach / Stop / Status) Summary

**`sif watch --detach` backgrounds the proven Phase 12 host through a stdlib double-fork with a deterministic pipe handshake (PID reported only once armed), `--stop` corroborates identity via ps argv markers before SIGTERM→bounded-wait→SIGKILL escalation, and `sif status` gains a Watch row — with the SC4 SIGKILL/re-detach proof that kernel-released flock leaves no stale lock.**

## Performance
- **Duration:** 28min | **Started:** 2026-11-07T15:18:39Z | **Completed:** 2026-11-07T15:47:00Z | **Tasks:** 2 | **Files:** 7 (3 created, 4 modified)
- **Suite:** 1110 passed @ 94.40% coverage (fail_under=90); ruff check/format green; ty check src/sif 0 diagnostics
- **Estimate vs actual:** 40000 tokens estimated (confidence: low), 17290 actual (chars/4 over the realized diff) — the 13-01 seam and the Phase 12 e2e culture carried more of the work than the estimate assumed

## Accomplishments
- **SC2 detach (D-06/D-07/D-09):** `daemon.detach` implements the verified double-fork (fork→setsid→fork, /dev/null stdin, log-file stdout/stderr, no chdir) with a one-message pipe handshake. The grandchild runs `arm()` — Database open, `init_schema`, `_select_collections`, PID-file write — and only then reports `armed <pid>`; any arm failure reaches the parent as `error <msg>` and surfaces as a `ClickException` (non-zero exit). The daemon child then runs the extracted `run_watch_host` — the exact foreground body — with the 13-01 seam wired: rescope-within-`-c`-filter provider, `watch_rescope_interval`, `watch_checkpoint_interval` (D-15/D-16). Logs default to `platformdirs.user_log_dir("sif")/watch.log` with `--log-file` override (D-07).
- **D-05 stop + Pitfall 3:** `--stop` reads the PID file defensively (garbage → stale+cleanup), corroborates identity fail-closed (`ps -p PID -o command=` must carry `sif.cli.main` AND a standalone `watch` token; ps missing/failing/mismatching → stale, never signalled), then SIGTERM → bounded poll (10s) → SIGKILL → bounded poll (5s) → unlink. A process that vanishes between corroboration and signal is handled without crashing.
- **D-08 status:** `status_cmd` renders a Watch row — `running — daemon · PID 4242 · bm25` from the corroborated payload, `not running`, or `not running (stale PID file removed)` with cleanup — through the single code path that `sif index status` delegates to.
- **SC4:** proven by test, not code — SIGKILL at steady state, immediate re-detach exits 0 with a new PID, no lock-error markers in either log, replacement indexes a change and stops cleanly.

## Task Commits
Each task followed RED → GREEN with machine-validated RED evidence (`gsd_run check tdd-red-evidence` → RED_EVIDENCE_OK, junit format):

1. **Task 1: End-to-end detach tracer (SC2)** — `0221013` (test: detach/stop e2e battery + flag guards, target `test_detach_backgrounds_watcher_and_indexes_live_changes` failing on the missing PID line) → `f7a889c` (feat: daemon.py + watch.py lifecycle)
   - Tracer feedback gate: all three `<verify>` commands re-run end-to-end after the tracer commit — e2e 3 passed TWICE in a row (flakiness criterion), units 23 passed, ruff clean. `⚡ Tracer verified end-to-end — expanding.`
2. **Task 2: Unit battery + status Watch section + SC4** — `637c823` (test: status battery failing on the missing Watch row + daemon pins + SC4, target `test_running_daemon_renders_pid_mode_depth`) → `335066e` (feat: status_cmd Watch section + lint-clean hermetic battery)
3. **`9bbd37d`** (style): a one-line ARG005 lint fix in test_watch_cmd.py that missed its GREEN staging — no logic change; the full suite had already run with it in place

**Plan metadata:** `see final docs commit below` (docs(13-02): complete detached daemon plan)

## Files Created/Modified
- `src/sif/utils/daemon.py` — NEW: pid_path_for/write_pid_file/read_pid_file/remove_pid_file, corroborate_pid, detach (double-fork + pipe), stop_daemon (+_terminate_corroborated/_signal_or_confirm_gone/_wait_gone/_read_pipe_message); module docstring states the metadata-never-arbitration contract (locking.py discipline)
- `src/sif/cli/commands/watch.py` — WatchHostParams dataclass; run_watch_host (extracted shared body); _daemon_log_path, _daemon_rescope_provider, _run_detach (fork-first, arm, replace()-derived daemon params, self-cleanup PID file), _run_stop; --detach/--stop/--log-file options + guards
- `src/sif/cli/main.py` — _watch_status_text + Watch row (probe wrapped: metadata can never take status down)
- `tests/integration/test_watch_daemon_e2e.py` — NEW: 4 tests (detach e2e, graceful stop WAL proof, stop idempotence, SC4 sigkill/re-detach) + safety-net `_detached_daemon` CM
- `tests/unit/utils/test_daemon.py` — NEW: 20 hermetic tests (fakes only)
- `tests/unit/cli/test_watch_cmd.py` — +5 tests (guards ×2, help, log-path ×2)
- `tests/unit/cli/test_status.py` — +5 Watch-section tests (running, stale ×2, missing, alias)

## Decisions Made
- Token-boundary corroboration: the plan's "contains the watch marker" is implemented as `"watch" in command.split()` — a reused PID running another sif command whose argv merely embeds `watch.db` must never corroborate (pinned by test).
- The daemon unlinks its own PID file on graceful exit (finally around run_watch_host) — `sif status` stays honest after a plain SIGTERM without a cleanup pass; D-05's metadata lifecycle.
- run_watch_host takes an OPEN Database (caller owns lifecycle); `arm()` opens it in the grandchild so "armed" genuinely means schema+collections+PID ready.
- WatchHostParams bundling (PLR0913, WatchConfig precedent); the daemon derives its copy via `dataclasses.replace` wiring only the three long-lived opt-ins — foreground behavior is byte-for-byte the Phase 12 flow.
- stop_daemon's term/kill/poll/now are injectable parameters (defaults 10s/5s/50ms/monotonic) so the escalation battery is hermetic and fast.

## Deviations from Plan
**[Rule 2 - Missing critical functionality] Status Watch-probe guard** — Found during: Task 2 GREEN | Issue: an unexpected exception while deriving/reading the PID artifact (e.g. a pathological index path) would escape into status_cmd's `Error reading index` handler and fail the whole command over display metadata; it also broke the existing mock-path status tests | Fix: the Watch probe is wrapped (exception → `not running` + logger.debug) — metadata display can never take the status command down | Files: src/sif/cli/main.py | Verification: full suite 1110 passed incl. both pre-existing status tests; the five Watch-section tests pass | Commit: 335066e

**Total deviations:** 1 auto-fixed (Rule 2). **Impact:** none on planned behavior; hardens the D-08 surface exactly as the threat model's defensive-parse posture requires.

## TDD Gate Compliance

| Task | RED commit | RED evidence | GREEN commit | REFACTOR |
|------|-----------|--------------|--------------|----------|
| 1 (tracer) | `0221013` | RED_EVIDENCE_OK (junit; target: test_detach_backgrounds_watcher_and_indexes_live_changes — "detach parent printed no daemon PID line", CLI exits 2 "No such option: --detach") | `f7a889c` | none needed (lint restructuring absorbed into GREEN) |
| 2 | `637c823` | RED_EVIDENCE_OK (junit; target: test_running_daemon_renders_pid_mode_depth — assert 'Watch' in output failed, no Watch row rendered) | `335066e` | none needed |

Both GREEN commits are preceded by their RED commits; every RED was machine-validated before production edits. No violations. (The Task 2 daemon unit pins passed on arrival by design — they pin Task 1's e2e-proven API; the RED target was the new status behavior, matching the plan's test-first split.)

## Issues Encountered
- pytest's whole-suite `fail_under=90` gate trips on any single-file run, so partial-run exit codes are red despite green summaries; all verify commands were additionally run with `--no-cov` for clean exit codes, and the full suite proves the gate proper (94.40%).
- Lint iterations inside GREEN (PLR0913 ×3 → WatchHostParams bundling + mcp_daemon_cmd-precedent noqa on the Click command; PLR0911 → _terminate_corroborated extraction; ARG005/E501/PT018/RUF012 test cleanups) — resolved within theGREEN loops, all gates green.
- Pre-existing (out of scope, logged to deferred-items.md): ResourceWarning from an unclosed sqlite connection in 13-01's TestIdleCheckpoint.

## User Setup Required
None - no external service configuration required. (`sif watch --detach` works against any existing index; the default daemon log dir is created on first detach.)

## Known Stubs
None. The `sif mcp daemon` slot remains unwired by design (D-14 — backlog, not this plan); `daemon.py` is deliberately shaped for its reuse.

## Next Phase Readiness
Ready for 13-04 (Wave 3): the lifecycle-flag family and Watch-section surface it documents are landed; 13-04 must regenerate the generator-owned docs (`make docs-generate`) so `--detach/--stop/--log-file`, the Watch section, and the 13-01 settings fields appear in cli-reference.md/configuration.md, then land service install (`--install-service`/`--uninstall-service`) on the same flag family. LIVE-09 stays open at the requirements gate until 13-04 completes (shared-ID).

## Self-Check: PASSED
- Created files FOUND: src/sif/utils/daemon.py, tests/unit/utils/test_daemon.py, tests/integration/test_watch_daemon_e2e.py
- Commits FOUND (ancestors of HEAD): 0221013, f7a889c, 637c823, 335066e
- Full suite: 1110 passed @ 94.40%; ruff/format/ty green

---
*Phase: 13-watch-everywhere-mcp-embedded-refresh-background-daemon*
*Completed: 2026-11-07*
