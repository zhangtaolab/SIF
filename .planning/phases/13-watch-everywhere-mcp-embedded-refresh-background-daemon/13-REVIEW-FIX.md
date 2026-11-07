---
phase: 13-watch-everywhere-mcp-embedded-refresh-background-daemon
fixed_at: 2026-11-07T17:30:29Z
review_path: .planning/phases/13-watch-everywhere-mcp-embedded-refresh-background-daemon/13-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 13: Code Review Fix Report

**Fixed at:** 2026-11-07T17:30:29Z
**Source review:** `.planning/phases/13-watch-everywhere-mcp-embedded-refresh-background-daemon/13-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (fix_scope=critical_warning: CR-01, WR-01..WR-04)
- Fixed: 5
- Skipped: 0
- Out of scope (Info, untouched): IN-01, IN-02, IN-03, IN-04 — remain open in REVIEW.md

**Mode note:** `workflow.use_worktrees=false`, so all edits and commits were made
directly in the main checkout on branch `dev`.

## Fixed Issues

### CR-01: MCP HTTP transport crashes at startup — lifespan passed as invoked context manager, not a factory

**Files modified:** `src/sif/mcp/watch_host.py`, `tests/unit/mcp/test_mcp_watch_host.py`, `tests/unit/mcp/test_transports_http.py`
**Commit:** 9acfd69
**Applied fix:** `mcp_watch_lifespan` is now a lifespan FACTORY — a plain function
taking `db_path` that returns a `Callable[[Any], ...]` wrapping an
`@asynccontextmanager` inner function accepting the app. The `run_http_server`
call site (`lifespan = mcp_watch_lifespan(db_path)`) is unchanged and now hands
FastAPI/Starlette the correct shape. Reproduced the crash first (TestClient
startup: `TypeError 'function' object does not support the asynchronous context
manager protocol`) and verified startup returns 200 after the fix. The three
direct-use lifespan tests in `test_mcp_watch_host.py` now invoke the factory
with the app argument, and the mock-pinning test
(`test_run_http_server_hands_mcp_watch_lifespan_to_transport`) is replaced by
`test_mcp_watch_lifespan_boots_a_real_app`, which runs the REAL lifespan
(only `start_embedded_watch`/`stop_embedded_watch` collaborators patched)
through `create_app` + `TestClient`, so the regression can no longer hide
behind a mock. `test_run_http_server_composes_backend_tools_and_transport`
still covers the wiring/threading path.

### WR-01: Shutdown WAL checkpoint bypasses the worker-liveness gate

**Files modified:** `src/sif/indexing/watcher.py`, `src/sif/cli/commands/watch.py`, `src/sif/mcp/watch_host.py`, `tests/unit/cli/test_watch_cmd.py`, `tests/unit/mcp/test_mcp_watch_host.py`, `tests/unit/indexing/test_watcher.py`
**Commit:** e3156da
**Applied fix:** `FileWatcher` gains `worker_joined()` — a live
`is_alive()`-derived truth source (True when no worker was started or the
thread exited, False while it runs, so a late-exiting worker still reports
True). `shutdown_watcher` (CLI host) and `stop_embedded_watch` (MCP host) now
execute `PRAGMA wal_checkpoint(TRUNCATE)` only when `worker_joined()` holds;
otherwise they log a warning and skip. A failed flush no longer force-runs the
checkpoint either (worker state unknown — same hazard). Added skip-branch tests
for both hosts and a `worker_joined` liveness-matrix test mirroring the
TestStopFlushGate BusyWorker/DoneWorker pattern. **Logic change on a shutdown
path: requires human verification** that gating (rather than attempting) the
checkpoint is the desired D-14 behavior when the worker outlives the join.

### WR-02: Debouncer thread leaked on every missing-root disappear/return cycle

**Files modified:** `src/sif/indexing/watcher.py`, `tests/unit/indexing/test_watcher.py`
**Commit:** 8039a3e
**Applied fix:** `recovery_tick`'s disappear branch now stops and joins
`state.debouncer` (with `_JOIN_TIMEOUT_SECONDS`, exact `_unschedule_removed`
parity) and clears the slot before setting `state.missing` — the watch handle
is already unscheduled, so no events can arrive, and the return branch's fresh
`EventDebouncer` no longer orphans a live `BaseThread` per cycle. The
disappear test now asserts the debouncer is cleared and dead, and a new
regression test drives three full disappear/return cycles asserting every
superseded debouncer thread is dead and the observer scheduled exactly once
per (re)arm.

### WR-03: `--install-service` drops `--no-embed` — an installed BM25 service can silently start embedding

**Files modified:** `src/sif/cli/commands/watch.py`, `tests/unit/cli/test_watch_cmd.py`, `docs/cli-reference.md`
**Commit:** 191aa05
**Applied fix:** `_service_argv_tail` takes `settings` and `no_embed` and bakes
`--no-embed` whenever the installer's effective depth is bm25 and the ambient
setting is embed (or the explicit flag forced BM25) — pinning the installer's
intent against a service environment that inherits `SIF_WATCH_UPDATE_DEPTH`.
`_run_install_service` and the `watch_cmd` call site plumb both through.
Depth matrix unit tests cover embed/baked-no-embed/plain-bm25, plus a
CliRunner plumbing test installing `--no-embed` under an embed setting. The
`--install-service` help text was updated and the generator-owned
`docs/cli-reference.md` regenerated via `make docs-generate` (never
hand-edited; diff is exactly the one help-string line).

### WR-04: Detach handshake timeout produces the "silent maybe-detach" SC2 explicitly forbids

**Files modified:** `src/sif/utils/daemon.py`, `tests/unit/utils/test_daemon.py`, `tests/integration/test_watch_daemon_e2e.py`
**Commit:** cd33b21
**Applied fix:** On a `None` handshake message (timeout/read error), the
detach parent now calls the new `_kill_detached_group(pid)` — SIGKILL via
`os.killpg` on the detached session's process group (the intermediate child's
`setsid()` made its pid the pgid, so one killpg reaches the late-arming
grandchild and anything it spawned), best-effort with OSError suppressed —
before reporting. `_parent_outcome`'s timeout error now reads "daemon did not
report readiness within Ns; terminated the daemon process group — if a daemon
still survives, stop it with 'sif watch --stop'". Hermetic unit tests pin the
message, the helper's SIGKILL/gone-group behavior, and the fork-branch wiring
(fork/read/killpg/waitpid faked), and a real-double-fork integration test
proves a slow-arming grandchild is killed mid-arm (survival marker file stays
absent) while the parent reports the terminated-timeout error. **Process-kill
logic: requires human verification** that killpg-on-intermediate-pid is
acceptable in the rare PID-recycling window.

### Lint cleanup (post-gate)

**Files modified:** `tests/unit/cli/test_watch_cmd.py`, `tests/unit/mcp/test_transports_http.py`, `tests/unit/utils/test_daemon.py`, `src/sif/mcp/watch_host.py`
**Commit:** 9756321
**Applied fix:** ruff findings in the new test helpers (unused args, explicit
`return None`) and one `ruff format` collapse in `watch_host.py`, surfaced by
the full-suite gate after the per-finding commits.

## Verification

Per-fix: Tier 1 (re-read of every modified section) + Tier 2 (`ast.parse`
syntax checks on each edited Python file; targeted pytest runs per finding —
37, 85, 43, 35, 29+1 tests respectively, all green before each commit).

**Full quality gate (after all fixes, run in the MAIN CHECKOUT — no worktree
was created, `workflow.use_worktrees=false`; numbers are reproducible from
this tree):**

- `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` — **1161 passed, 1 skipped**
  (skip is the pre-existing opt-in `SIF_TEST_LIVE_LAUNCHD` live launchd proof),
  coverage 94.59% (fail_under=90 met)
- `ruff check src tests` — All checks passed
- `ruff format --check src tests` — 172 files already formatted
- `ty check src/sif` — All checks passed

## Skipped Issues

None — all 5 in-scope findings were fixed.

---

_Fixed: 2026-11-07T17:30:29Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
