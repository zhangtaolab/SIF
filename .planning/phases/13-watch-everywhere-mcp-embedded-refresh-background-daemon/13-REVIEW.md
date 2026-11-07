---
phase: 13-watch-everywhere-mcp-embedded-refresh-background-daemon
reviewed: 2026-11-08T00:00:00Z
depth: standard
files_reviewed: 20
files_reviewed_list:
  - scripts/generate_config_ref.py
  - src/sif/cli/commands/watch.py
  - src/sif/cli/main.py
  - src/sif/config/settings.py
  - src/sif/indexing/watcher.py
  - src/sif/mcp/transports/http.py
  - src/sif/mcp/transports/stdio.py
  - src/sif/mcp/watch_host.py
  - src/sif/utils/daemon.py
  - src/sif/utils/service.py
  - tests/integration/test_mcp_watch_e2e.py
  - tests/integration/test_service_live_launchd.py
  - tests/integration/test_watch_daemon_e2e.py
  - tests/unit/cli/test_status.py
  - tests/unit/cli/test_watch_cmd.py
  - tests/unit/indexing/test_watcher.py
  - tests/unit/mcp/test_mcp_watch_host.py
  - tests/unit/mcp/test_transports_http.py
  - tests/unit/utils/test_daemon.py
  - tests/unit/utils/test_service.py
findings:
  critical: 1
  warning: 4
  info: 4
  total: 9
  necessity: 0
status: issues_found
---

# Phase 13: Code Review Report

**Reviewed:** 2026-11-08
**Depth:** standard
**Files Reviewed:** 20
**Status:** issues_found

## Summary

Reviewed all 20 scoped files at standard depth, with cross-module verification against the installed dependencies (starlette 1.0.0, watchdog 6.0.0, sqlite factory/locking) and the phase diff (`b2f117a`). The three-host watch architecture is well built — the flock discipline, PID-file-as-metadata corroboration, fail-closed stop path, and the stdio protocol-cleanliness battery are all sound and verified. One shipping blocker exists in the HTTP lane, plus four robustness warnings.

**CR-01 is a hard startup crash of the entire HTTP MCP transport.** `run_http_server` passes an already-invoked `_AsyncGeneratorContextManager` into `FastAPI(lifespan=...)`. Starlette 1.0.0 (`Router.lifespan`) executes `self.lifespan_context(app)`; for an invoked context manager, `__call__` is contextlib's decorator protocol and returns an async *function*, which fails `async with` with `TypeError`. Reproduced against the project's own `create_app` + `mcp_watch_lifespan` wiring: `STARTUP FAILED: TypeError 'function' object does not support the asynchronous context manager protocol`. Every `sif mcp serve/http` invocation dies at lifespan startup — regardless of `SIF_MCP_WATCH`, because the wiring is unconditional. The unit test battery mocked `mcp_watch_lifespan` itself (test_transports_http.py:433-448) so it asserts and preserves the broken shape, and the e2e battery covers stdio only — which is exactly why this escaped.

The warnings: (1) both hosts' shutdown WAL checkpoint bypasses the CR-01 worker-liveness gate that the same phase added, allowing concurrent same-connection use; (2) a debouncer-thread leak on missing-root return cycles (a regression vs. the pre-phase flat-list implementation, in the exact D-12 scenario); (3) `--install-service` silently drops `--no-embed`, so an ambient `SIF_WATCH_UPDATE_DEPTH=embed` in the service environment can flip an installed-BM25 service into embedding; (4) the detach handshake timeout path violates the "never a silent maybe-detach" (SC2) guarantee — the parent reports failure while the grandchild arms and runs.

**Necessity (#4100):** assessed per the standard-depth rubric; no provable phantom guards found in the changed code (the `assert isinstance(pid, int)` narrowing in `stop_daemon` serves the `ty` type checker over a just-validated value and the PID file is a trust boundary, so it is excluded under the rubric's negative space). `necessity: 0`.

Phase-context design decisions were treated as intentional and NOT flagged: flock-only arbitration with coexisting hosts, PID file as metadata only, MCP watch BM25-only/D-02 and opt-in/D-04, serve-then-reconcile, launchd bootout-then-bootstrap retry, worker-thread failure guards, logger-to-stderr-only in the stdio host. Verified along the way: `FileScanner.matches` does honor `watch_ignore_patterns` via `_combined_ignore_patterns` (no predicate inconsistency); `pid_path_for` canonicalization matches `index_lock`'s `.resolve()`; all `IncrementalIndexer`/`_render_index_event`/`Database` call signatures line up.

## Critical Issues

### CR-01: MCP HTTP transport crashes at startup — lifespan passed as invoked context manager, not a factory

**File:** `src/sif/mcp/transports/http.py:256` (with `src/sif/mcp/watch_host.py:186-202`)
**Issue:** `run_http_server` builds `lifespan = mcp_watch_lifespan(db_path)` — it *invokes* the `@asynccontextmanager` function, producing a `_AsyncGeneratorContextManager` object — and threads that object into `HTTPTransport` → `create_app` → `FastAPI(lifespan=...)`. Starlette 1.0.0's `Router.lifespan()` (verified in the installed package) executes `async with self.lifespan_context(app)`: the lifespan must be a **callable accepting the app** that returns an async context manager. An invoked `_AsyncGeneratorContextManager` is "callable" only through contextlib's `__call__` *decorator* protocol, which returns an async wrapper function — and `async with` on that function raises `TypeError`. Reproduced with the project's real wiring and `fastapi.testclient.TestClient`:

```
STARTUP FAILED: TypeError 'function' object does not support the asynchronous context manager protocol
```

Under uvicorn this surfaces as `lifespan.startup.failed` → "Application startup failed. Exiting." — `sif mcp serve` (HTTP mode, `src/sif/cli/commands/mcp.py:68`) cannot start at all, with or without `SIF_MCP_WATCH`. The passing unit tests never exercise the real shape: `test_run_http_server_hands_mcp_watch_lifespan_to_transport` patches `mcp_watch_lifespan` with a `MagicMock` (so any invocation shape "works"), and `test_transport_run_forwards_lifespan_into_create_app` uses a sentinel mock. That test currently *pins the broken contract* and must be updated with the fix. The stdio lane is unaffected.
**Fix:** Make `mcp_watch_lifespan` return a lifespan *factory* (callable with the app) instead of being the context manager itself; the `run_http_server` call site then stays unchanged:

```python
# src/sif/mcp/watch_host.py
from collections.abc import Callable
from contextlib import asynccontextmanager

def mcp_watch_lifespan(db_path: str) -> Callable[[Any], AsyncGenerator[None, None]]:
    """FastAPI lifespan factory hosting the embedded watcher (D-01)."""

    @asynccontextmanager
    async def _lifespan(_app: Any) -> AsyncGenerator[None, None]:
        watch = start_embedded_watch(db_path)
        try:
            yield
        finally:
            stop_embedded_watch(watch)

    return _lifespan
```

Then add one real-app test (no mocks around the lifespan) proving startup succeeds, e.g. `with TestClient(create_app(server, lifespan=mcp_watch_lifespan(tmp_db))): ...` — which fails on the current code and passes with the fix.

## Warnings

### WR-01: Shutdown WAL checkpoint bypasses the worker-liveness gate — can execute on the same sqlite connection as a still-live worker

**File:** `src/sif/cli/commands/watch.py:104-107` (same shape in `src/sif/mcp/watch_host.py:176-182`)
**Issue:** `FileWatcher.stop()` (watcher.py:461-469) deliberately skips the bounded flush when `worker.join(10s)` times out, with the explicit CR-01 rationale that a legitimately-still-running job (flock wait up to `lock_timeout`, default 30s, or first-use embed model load) must not race the calling thread on the same connection. But `shutdown_watcher` and `stop_embedded_watch` then unconditionally run `conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")` in a `finally` — on the *same* connection the possibly-still-live worker is using mid-transaction. The factory sets `check_same_thread=False` (`src/sif/database/factory.py`), which permits cross-thread use but makes concurrent use of one connection undefined: the checkpoint can interleave with the worker's open `with conn:` transaction, producing an `OperationalError`/`ProgrammingError` at teardown (daemon exits with a traceback instead of the D-14 exit-0 contract) or a silently ineffective checkpoint. The gate that exists for the flush is simply not applied to the checkpoint that follows it.
**Fix:** Have `stop()` report whether the worker actually exited (e.g. return a bool, or expose `watcher.worker_joined()`), and only checkpoint when it did; otherwise log and skip, mirroring the flush gate:

```python
def shutdown_watcher(watcher: FileWatcher, conn: sqlite3.Connection) -> None:
    try:
        watcher.stop(flush=True)
        if watcher.worker_joined():          # False when the join timed out
            conn.execute(_WAL_CHECKPOINT_TRUNCATE)
        else:
            logger.warning("skipping shutdown checkpoint; worker still busy")
    finally:
        pass  # failed flush no longer force-runs the checkpoint either
```

### WR-02: Debouncer thread leaked on every missing-root disappear/return cycle (regression vs. the flat-list implementation)

**File:** `src/sif/indexing/watcher.py:490-501` and `watcher.py:436`
**Issue:** When a root disappears, `recovery_tick` unschedules the observer handle but never stops `state.debouncer`. When the root returns, `_schedule_watch` (line 436) assigns a brand-new `EventDebouncer` over `state.debouncer`, orphaning the old one. `EventDebouncer` extends watchdog's `BaseThread` (verified: a real daemon thread parked on `self._cond.wait()`), so each disappear/return cycle permanently leaks one live thread in a process designed to run for months — precisely the flaky-mount scenario the D-12 recovery loop exists for. `stop()` and `_unschedule_removed` only see the current `state.debouncer`, so the orphan is never stopped or joined anywhere. The pre-phase implementation kept all debouncers in `self._debouncers` and stopped them all at shutdown; this phase's per-state refactor introduced the leak. A secondary effect: an orphaned debouncer holding pending events can still fire its callback after the root vanished (benign — the D-11 guard absorbs it — but the burst is unattributable to any live watch).
**Fix:** In the disappear branch, stop and join the debouncer exactly as `_unschedule_removed` does (the watch handle is already gone, so no events can arrive):

```python
if not exists and not state.missing:
    logger.warning(...)
    if state.handle is not None:
        observer.unschedule(state.handle)
        state.handle = None
    if state.debouncer is not None:
        state.debouncer.stop()
        state.debouncer.join(timeout=_JOIN_TIMEOUT_SECONDS)
        state.debouncer = None
    state.missing = True
```

### WR-03: `--install-service` drops `--no-embed` — an installed BM25 service can silently start embedding

**File:** `src/sif/cli/commands/watch.py:413-425`
**Issue:** `_service_argv_tail` bakes only `-c` names and `--embed` (when the install-time effective depth is embed). If the user installs with `--no-embed` while `SIF_WATCH_UPDATE_DEPTH=embed` is present in the *service's* runtime environment (launchd agents inherit the GUI-session environment incl. `launchctl setenv` values; systemd user units inherit manager `DefaultEnvironment`), nothing is baked and the supervised process re-derives depth=embed at runtime. The service then computes and writes vectors — the exact billing-surprise class D-02 guards against — contradicting the module's own contract that "the service replays exactly what was installed" (docstring, D-11). The `--detach` path does not have this hole because the daemon inherits the invoking shell's environment and flags.
**Fix:** Bake the forced-off flag too, so the replay is exact whenever the setting disagrees with the flags:

```python
def _service_argv_tail(params, collections, settings, no_embed: bool) -> list[str]:
    tail: list[str] = []
    for name in dict.fromkeys(collections):
        tail.extend(["-c", name])
    if params.depth == "embed":
        tail.append("--embed")
    elif no_embed or settings.watch_update_depth == "embed":
        tail.append("--no-embed")   # pin the installer's BM25 intent
    return tail
```

### WR-04: Detach handshake timeout produces the "silent maybe-detach" SC2 explicitly forbids

**File:** `src/sif/utils/daemon.py:200-207` (timeout path in `detach`) and `daemon.py:315-318`
**Issue:** If `arm()` exceeds `_ARM_TIMEOUT_SECONDS` (30s) — plausible when `init_schema` contends with a concurrent reindex (busy_timeout is 5s *per statement* across many DDL statements) or on slow storage — the parent's `_read_pipe_message` returns None, the parent reports "daemon did not report readiness within 30s" and exits non-zero, and `_parent_outcome` translates it to a CLI failure. But the grandchild is still running: it finishes arming, writes the PID file, and enters the watch host indefinitely. The user is told the daemon failed while an armed daemon runs — exactly the outcome the handshake was built to prevent ("never a silent maybe-detach (SC2)", module docstring). The e2e battery only covers the fast path, so this branch is unproven.
**Fix:** On timeout, don't just report failure — attempt cleanup of the maybe-daemon: send SIGKILL to the grandchild PID (`os.killpg` on the new session, or track the grandchild PID via a second short pipe message from the intermediate child), then remove a possibly-written PID file; or at minimum extend the failure message to tell the user a daemon may still have armed and to run `sif watch --stop`. A minimal honest variant:

```python
if message is None:
    # The grandchild may still arm late: kill the session we created and
    # clear any PID file it manages to write (SC2: no silent maybe-detach).
    _kill_grandchild_session(pid)   # SIGKILL via os.killpg after setsid group
    return DetachOutcome(error=f"daemon did not report readiness within {timeout_s:.0f}s; terminated")
```

## Info

### IN-01: `SIF_LOCK_WAIT_TIMEOUT` missing from the generated configuration reference; multi-field validators annotated on only their first field

**File:** `scripts/generate_config_ref.py:137-177` (and `:61-68`)
**Issue:** `Settings.lock_wait_timeout` exists (`src/sif/config/settings.py:36-41`) and is load-bearing for the watch hosts, but is absent from every entry in `SECTIONS`, so the generator-owned `docs/configuration.md` (CI drift-gated, never hand-edited) silently omits it — `_append_options_tables` skips any field not listed. Separately, `get_validators` records only the first field of `@field_validator("db_path", "cache_dir", ...)`, so the `cache_dir` row never shows its `(validated by expand_path)` annotation. The generator was modified this phase (new watch settings + `mcp_watch`); these gaps should close in the same place.
**Fix:** Add `"lock_wait_timeout"` to the Database (or Watch) section of `SECTIONS`; optionally extend `get_validators` to split the decorator's field list on commas and register every field name.

### IN-02: Service-manager invocations have no timeout — a wedged launchctl/systemctl hangs the CLI forever

**File:** `src/sif/utils/service.py:198-200`
**Issue:** `_run` calls `subprocess.run(argv, capture_output=True, text=True, check=False)` with no `timeout=`. The same codebase's `ps` probe in `daemon.py` (`_PS_TIMEOUT_SECONDS = 5.0`) sets the precedent that external binaries must be deadline-bounded. A stuck manager binary (or a `launchctl bootstrap` blocked on a wedged launchd) makes `sif watch --install-service`/`--uninstall-service` hang indefinitely with no diagnostics.
**Fix:** Add a bounded timeout and map it to `ServiceCommandError`, e.g. `runner(argv, capture_output=True, text=True, check=False, timeout=30)` with `except subprocess.TimeoutExpired: raise ServiceCommandError(argv, "timed out")`.

### IN-03: `write_pid_file` follows a pre-planted symlink (hardening parity with `service._write_artifact`)

**File:** `src/sif/utils/daemon.py:101`
**Issue:** `os.open(path, O_WRONLY | O_CREAT | O_TRUNC, 0o600)` follows symlinks, so a pre-planted `<db>.watch.pid` symlink redirects the daemon's PID-file write (and later removal) to an arbitrary path. The service module solves the same class explicitly (T-13-11: write-temp-then-rename). Local single-user threat model keeps this low severity, but the asymmetry within the same phase is worth closing.
**Fix:** Use `O_NOFOLLOW` where available (macOS/Linux both support it) or adopt the write-temp-rename pattern from `service._write_artifact`.

### IN-04: `SESSION_MAX_AGE` is dead — sessions never expire by age

**File:** `src/sif/mcp/transports/http.py:42`
**Issue:** `SESSION_MAX_AGE = 3600` is defined but never referenced; session eviction is count-only (`SESSION_MAX_COUNT` LRU in `_get_session_id`), so `last_accessed` is recorded but never acted upon. Pre-existing (not introduced this phase), but the file is in scope and the constant implies an expiry behavior that does not exist.
**Fix:** Either implement age-based expiry in `_get_session_id` (drop sessions older than the age while evicting) or delete the constant and the misleading `last_accessed` bookkeeping.

---

_Reviewed: 2026-11-08_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
