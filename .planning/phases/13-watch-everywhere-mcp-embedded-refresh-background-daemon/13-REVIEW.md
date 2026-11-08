---
phase: 13-watch-everywhere-mcp-embedded-refresh-background-daemon
reviewed: 2026-11-08T08:19:56Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - docs/cli-reference.md
  - docs/configuration.md
  - scripts/generate_config_ref.py
  - src/sif/cli/commands/watch.py
  - src/sif/cli/main.py
  - src/sif/config/settings.py
  - src/sif/indexing/watcher.py
  - src/sif/mcp/transports/http.py
  - src/sif/mcp/watch_host.py
  - src/sif/utils/daemon.py
  - tests/integration/test_watch_daemon_e2e.py
  - tests/unit/cli/test_status.py
  - tests/unit/cli/test_watch_cmd.py
  - tests/unit/indexing/test_watcher.py
  - tests/unit/mcp/test_mcp_watch_host.py
  - tests/unit/mcp/test_transports_http.py
  - tests/unit/utils/test_daemon.py
findings:
  critical: 0
  warning: 1
  info: 1
  total: 2
  necessity: 0
status: issues_found
---

# Phase 13: Code Review Report (Incremental Re-review, Round 3)

**Reviewed:** 2026-11-08T08:19:56Z
**Depth:** standard
**Files Reviewed:** 17
**Status:** issues_found

## Summary

Incremental re-review of phase 13 over the files changed since the prior
review commit `03d8b54` (17 files: the phase-13 post-review fix commits
`9acfd69..f418ff9` plus the later phase-14 shared-surface commits
`bde4b8c..337a68e` that touch this phase's files — `main.py` status Vector
lag row, `settings.py` `search_refresh_*` fields, `test_status.py`
`TestVectorLag`, and regenerated docs).

**Re-verification of all 9 prior findings — every fix is present and
correct in the current tree:**

- **CR-01** — `mcp_watch_lifespan` (`src/sif/mcp/watch_host.py:190`) is now
  a factory returning an `@asynccontextmanager`-decorated callable; the
  shape Starlette's `Router.lifespan` executes (`async with
  self.lifespan_context(app)`). `http.py:255` wires the factory product
  into `HTTPTransport`, and `create_app(lifespan=...)` hands it to FastAPI
  verbatim. The regression test boots a REAL app through the factory
  (`tests/unit/mcp/test_transports_http.py:433`).
- **WR-01** — `FileWatcher.worker_joined()` (`watcher.py:478-489`) gates the
  shutdown WAL checkpoint in both hosts (`watch.py:112`,
  `watch_host.py:181`). The live-liveness (rather than recorded-at-stop)
  check is race-safe: the worker thread is never restarted, so a `True`
  observation cannot be invalidated. The flush-skip gate in `stop()`
  (`watcher.py:461-469`) and the checkpoint gate are consistent.
- **WR-02** — the disappear branch of `recovery_tick` stops, joins (5s
  bound), and clears the state's debouncer (`watcher.py:517-524`), matching
  `_unschedule_removed` parity. The failed-reschedule path correctly does
  NOT start the replacement debouncer (`_schedule_watch` starts it only
  after a successful `observer.schedule`), so no leak on that branch either.
- **WR-03** — `_service_argv_tail` (`watch.py:424-452`) bakes `--no-embed`
  when the install is BM25 under an embed-wanting ambient setting. Depth
  matrix verified: `depth=="bm25" ∧ ¬no_embed ⟹ settings==bm25` follows
  from `_effective_depth`, so the `elif` conditions are exactly the
  pin-worthy cases (one residual gap noted as IN-01 below).
- **WR-04** — `_kill_detached_group` (`daemon.py:335-346`) SIGKILLs the
  detached session on handshake timeout BEFORE `waitpid` reaps the
  intermediate child. PID-reuse hazard ruled out: the unreaped zombie
  intermediate child holds the pgid, so `killpg` cannot strike an unrelated
  group; `ProcessLookupError`/`PermissionError` are suppressed by design.
  The error message honestly states the termination and the `--stop`
  remedy.
- **IN-01** — the generator's `get_validators` now registers every field a
  `@field_validator` decorator names (comma-split, kwargs skipped), and
  `lock_wait_timeout` is in the Database Settings `SECTIONS` allowlist. I
  re-ran BOTH generators (`generate_config_ref.py`, `generate_cli_ref.py`):
  output is byte-identical to the committed `docs/configuration.md` and
  `docs/cli-reference.md` — no drift.
- **IN-02** — (fix lives in `service.py`/`test_service.py`, outside this
  round's file list) interface spot-checked against the in-scope callers:
  `_RUN_TIMEOUT_SECONDS = 30.0`, `ServiceManagerMissing`/
  `ServiceCommandError`, and `install_watch_service(db_path, argv_tail, *,
  manager=...)` all match `watch.py`'s call sites and except-clauses.
- **IN-03** — `write_pid_file` writes `.<name>.tmp` (mode 0600) then
  `os.replace`s it onto the PID path; symlink no longer followed; temp
  unlinked on failure (`daemon.py:105-113`). One residual race found in
  this implementation — see WR-01 below.
- **IN-04** — `SESSION_MAX_AGE` removed; repo-wide grep finds zero
  remaining references. The `created`/`last_accessed` bookkeeping retained
  by the fixer's documented decision (observable metadata, asserted by
  tests) — not re-flagged.

**Phase-14 shared surface vs phase-13 contract:** the `search_refresh_*`
settings fields are purely additive (validated `ge=1`, no interaction with
watch paths); the `Vector lag` status row reuses
`staleness.embedded_document_ids` (returns `None` on missing vec0 —
verified) under the same degrade-never-fail `try/except` contract as the
phase-13 Watch row; the regenerated docs match their generators exactly.
Nothing in the phase-14 changes breaks phase 13's own contract.

**Verification run this round:** all scoped unit suites (170 passed) and
the real-subprocess daemon e2e battery (5 passed) under `env -u FORCE_COLOR
NO_COLOR=1`; `ruff check` and `ty check` clean on every scoped file; both
doc generators re-run with zero diff. (Coverage-per-subset-run fails only
because these were scoped runs, not the full suite.)

**Necessity (#4100):** assessed per the rubric; 0 findings. The
belt-and-braces asserts in `stop_daemon` and `_run_detach` guard
trust-boundary data (a tamperable PID file) or serve type narrowing — both
in the rubric's negative space; no provable phantom requirements or
impossible-state guards were found in the scoped files.

Two new findings follow — one WARNING on the IN-03 implementation, one
INFO on the WR-03 pin's completeness.

## Warnings

### WR-01: `write_pid_file` uses a process-shared temp name — concurrent detaches race on the same inode

**File:** `src/sif/utils/daemon.py:105-113`
**Issue:** The IN-03 temp-then-rename hardening derives the temp path as a
fixed function of the final path: `tmp = path.with_name(f".{path.name}.tmp")`.
Two `sif watch --detach` invocations on the same index therefore share one
temp inode — and the module's own contract explicitly accommodates that
concurrency ("two daemons may run simultaneously"; flock per burst is the
only arbitration, `daemon.py:4-8`). Interleavings: (a) process B's
`os.open(O_TRUNC)` lands between A's write and A's `os.replace` — A's
replace consumes the inode, and B's subsequent `os.replace` raises
`FileNotFoundError`, so B's `arm()` fails and the CLI reports "Watch daemon
failed to start" for a daemon that was otherwise healthy; (b) both write
through separate fds to the same truncated inode with differing payload
lengths, leaving a concatenated/garbage PID file (fail-closed at read —
`None` → stale — so no wrong signal, but the artifact is corrupt). The
pre-IN-03 code never made a healthy daemon's start fail this way. Severity
is WARNING, not BLOCKER: outcomes stay fail-closed and the window is
microseconds, but the hardening fix undermined its own integrity goal for
the multi-daemon case the module documents.
**Fix:**
```python
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
```
A per-process (or `uuid`/`tempfile`-style) temp name makes each writer's
create/write/rename sequence independent; `os.replace` still lands
atomically and the symlink hardening is unaffected.

## Info

### IN-01: `_service_argv_tail` half-pins the depth — an unpinned BM25 install can still go embed in a divergent service environment

**File:** `src/sif/cli/commands/watch.py:450-451`
**Issue:** WR-03 bakes `--no-embed` only when the INSTALLER observed an
embed-wanting ambient config (`no_embed or settings.watch_update_depth ==
"embed"`); a plain BM25 install (no flags, ambient `bm25`) bakes nothing,
pinned by `test_argv_tail_bakes_embed_and_plain_bm25_bakes_no_depth_flag`.
But the fix's own rationale — "launchd/systemd environments are not the
installing shell's" — cuts both ways: if the service's runtime environment
later carries `SIF_WATCH_UPDATE_DEPTH=embed` (e.g. `launchctl setenv`,
which persists for every LaunchAgent), the unpinned service re-derives
embed and starts computing vectors, against the docstring's stated
invariant "an installed-BM25 service must never start computing vectors"
and against its closing principle "the service replays exactly what was
installed". The embed and no-embed installs are fully pinned (flags beat
settings at runtime); only the bm25 install relies on ambient agreement.
Judgment call whether honoring a deliberately-set service-env var is user
intent — hence Info, not Warning.
**Fix:** Bake `--no-embed` unconditionally when `params.depth == "bm25"`
(the pin is a no-op at the bm25 runtime default and only bites when the
service environment diverges from what was installed), updating the
`plain_tail == ["-c", "notes"]` expectation accordingly.

---

_Reviewed: 2026-11-08T08:19:56Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
