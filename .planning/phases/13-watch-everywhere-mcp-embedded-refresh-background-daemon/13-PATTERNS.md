# Phase 13: Watch Everywhere (MCP-Embedded Refresh + Background Daemon) - Pattern Map

**Mapped:** 2026-11-07
**Files analyzed:** 15 (5 new source modules, 5 modified source files, 1 modified script allowlist, 7 new/extended test files — counts overlap per wave)
**Analogs found:** 15 / 15 (all named analogs are git-TRACKED source, verified via `git ls-files`)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/sif/cli/commands/watch.py` (MODIFY) | controller (CLI command) | event-driven → long-lived host | itself + `src/sif/cli/commands/mcp.py` lifecycle-flag family | exact |
| `src/sif/utils/daemon.py` (NEW) | utility (process lifecycle) | file-I/O + signals | `src/sif/database/locking.py` (file artifact + 0600 + docstring contract) | role-match |
| `src/sif/utils/service.py` (NEW, name at planner discretion) | utility (template gen + subprocess) | file-I/O + request-response (mgr invocation) | `scripts/generate_config_ref.py` (generator style) + explicit-argv discipline | partial (no service module exists) |
| `src/sif/mcp/watch_host.py` (NEW, name at planner discretion) | service (host lifecycle factory) | event-driven (owns FileWatcher) | `watch_cmd` construction sequence in `src/sif/cli/commands/watch.py:227-281` | exact (construction shape) |
| `src/sif/mcp/transports/stdio.py` (MODIFY) | transport | request-response | itself — `run_stdio_server` at lines 127-133 | exact |
| `src/sif/mcp/transports/http.py` (MODIFY) | transport | request-response | itself — `create_app` at lines 145-157, `HTTPTransport.run` at 215-220 | exact |
| `src/sif/config/settings.py` (MODIFY) | config | CRUD (pydantic fields) | existing `watch_*` fields, lines 43-66 | exact |
| `src/sif/cli/main.py` `status_cmd` (MODIFY) | controller (presentation) | request-response | itself — Rich table at lines 109-146 | exact |
| `src/sif/indexing/watcher.py` (MODIFY) | service (watch core) | event-driven | itself — `recovery_tick` 422-454, `_schedule_watch` 370-384, `_worker_loop` 477-499 | exact |
| `scripts/generate_config_ref.py` (MODIFY) | config/docs generator | transform | itself — `SECTIONS` allowlist lines 137-175 | exact |
| `tests/unit/indexing/test_watcher.py` (EXTEND) | test | synthetic event-driven | itself — header + fixtures | exact |
| `tests/integration/test_watch_e2e.py` (analog only) | test | subprocess e2e | itself — `_watch_process`/`_poll_until` helpers | exact |
| `tests/unit/cli/test_watch_cmd.py` (analog + extend for flags) | test | CliRunner | itself | exact |
| `tests/unit/utils/test_daemon.py`, `test_service.py` (NEW) | test | unit | `tests/unit/utils/test_logging.py` (module layout) | role-match |
| `tests/unit/mcp/test_mcp_watch_host.py` (NEW) | test | unit | `tests/unit/mcp/test_transports_stdio.py` / `test_transports_http.py` | role-match |

## Pattern Assignments

### `src/sif/cli/commands/watch.py` (controller, event-driven host — MODIFY)

**Analog:** itself; new flags follow the `mcp_daemon_cmd` lifecycle-flag family in `src/sif/cli/commands/mcp.py:74-90` (`--pid-file`, `--log-file`, `--stop` as `is_flag=True` options).

**Existing option declaration pattern** (lines 167-191) — new `--detach`/`--stop`/`--install-service`/`--uninstall-service`/`--log-file` copy this shape:

```python
@click.command("watch")
@click.option(
    "--collection",
    "-c",
    "collections",
    multiple=True,
    help="Watch only the named collection(s); repeatable. ...",
)
@click.option(
    "--embed",
    is_flag=True,
    help="Also write vector embeddings for changed documents (opt-in; default is BM25-only)",
)
```

**Reusable module-level lifecycle machinery — do NOT duplicate** (lines 46-90). The daemon child runs the exact foreground body (D-09), so `SignalState`, `make_signal_handler`, `install_signal_handlers`, `shutdown_watcher`, `_WAL_CHECKPOINT_TRUNCATE` are reused verbatim:

```python
@dataclass
class SignalState:
    stop: bool = False
    signal_count: int = 0

def shutdown_watcher(watcher: FileWatcher, conn: sqlite3.Connection) -> None:
    try:
        watcher.stop(flush=True)
    finally:
        conn.execute(_WAL_CHECKPOINT_TRUNCATE)
```

**Host construction sequence to embed in the daemon/MCP hosts** (lines 227-281): `with Database(index_path) as db:` → `db.init_schema()` → `_select_collections(...)` → per-collection reconcile under `index_lock` → `FileWatcher(selected, db.connection, Path(index_path), WatchConfig(...))` → `watcher.start()`. The MCP host differs per D-02 (depth forced `"bm25"`) and Pitfall 4 (reconcile enqueued on the worker, not blocking).

**Error convention** (lines 208-217): `Settings` failures raise `click.ClickException(str(e))`; unknown collection names raise `click.ClickException(f"Collection '{name}' not found")` (line 109). All new user-facing failures (`--stop` when not running, missing launchctl/systemctl) use `click.ClickException`.

---

### `src/sif/utils/daemon.py` (utility, file-I/O + signals — NEW)

**Analog:** `src/sif/database/locking.py` — the project's precedent for a small utils-style module owning a file artifact next to the DB with a documented contract. Copy its discipline:

**Module docstring contract pattern** (locking.py:1-16) — state the kernel-level guarantee up front (flock released on SIGKILL) and the deliberate non-goals (no PID-as-lock); daemon.py should mirror this for the PID file (metadata, never arbitration).

**File-artifact creation pattern** (locking.py:67-70) — canonicalize the path exactly like `Database` does, derive the sibling artifact, create with restrictive mode:

```python
lock_path = Path(db_path).expanduser().resolve()
lock_path = lock_path.with_name(lock_path.name + ".lock")

fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
```

Apply verbatim to the PID file: `Path(db_path).resolve()` → `.with_name(...)` (e.g. `{name}.watch.pid`), `os.open(..., 0o600)` per the ASVS V4 note.

**Deadline-bounded poll loop pattern** (locking.py:71-93) — `deadline = time.monotonic() + timeout_s`, poll at a small `_POLL_INTERVAL_SECONDS = 0.05`, act on expiry; reuse this shape for `--stop`'s bounded wait before SIGKILL escalation.

**Signal-shutdown precedent:** `watch.py:63-67` (`sys.exit(130)` on second signal) is what `--stop`'s SIGTERM triggers inside the daemon.

**No analog for:** double-fork mechanics — use the verified recipe in 13-RESEARCH.md Code Examples (fork BEFORE any thread exists — Pitfall 2).

---

### `src/sif/utils/service.py` (utility, generation + subprocess — NEW)

**Analog (generation):** `scripts/generate_config_ref.py` — pure-text generation from structured inputs, round-trip assertable. `SECTIONS` allowlist (lines 137-175) is the registration point for new `mcp_watch`/tick settings (see Shared Patterns).

**Analog (invocation):** no existing launchctl/systemctl subprocess site exists. Follow the repo-wide explicit-argv discipline seen in tests (`tests/integration/test_watch_e2e.py:88`: `argv = [sys.executable, "-u", "-m", "sif.cli.main", "--index", str(db_path), "watch"]`) — build `subprocess.run` argv lists only, gate on `shutil.which("launchctl")`/`"systemctl"` with a friendly `click.ClickException`. Plist content via `plistlib.dump` (never string-interpolated XML); systemd unit as a text template.

---

### `src/sif/mcp/watch_host.py` (service, event-driven — NEW)

**Analog:** the `watch_cmd` construction sequence (`src/sif/cli/commands/watch.py:227-281`), minus terminal presentation. Key deviations locked by decisions:

- Depth forced `"bm25"` regardless of `watch_update_depth` (D-02) — do NOT call `_effective_depth`.
- All collections (`_select_collections` with no names — `watch.py:101-102`).
- Callbacks route to `logger` ONLY (stdout is JSON-RPC on stdio — Pitfall 1); `_render_watch_event`/`_render_batch` (console/Rich) must NOT be reused.

**Logger pattern** (`src/sif/utils/logging.py:120`, handlers are `StreamHandler(sys.stderr)`; module convention as in every file):

```python
from sif.utils.logging import get_logger
logger = get_logger(__name__)
```

**HTTP lifespan factory:** `@asynccontextmanager` per 13-RESEARCH.md Code Examples; `create_app` gains a `lifespan=None` parameter (see below).

---

### `src/sif/mcp/transports/stdio.py` (transport, request-response — MODIFY)

**Analog:** itself. Construction site (lines 127-133):

```python
async def run_stdio_server(db_path: str) -> None:
    """Run MCP server in stdio mode."""
    backend = SearchBackend(db_path)
    server = MCPServer(backend)
    server.register_tools(create_default_tools())
    transport = StdioTransport(server)
    await transport.run()
```

Pattern: watcher start goes before `transport.run()`, stop in a `finally` — mirroring `watch.py:297-301`'s `finally: watcher.stop(flush=False)` exception-path discipline. Note `run_stdio_server_sync` (line 136-138) wraps with `asyncio.run`; do not fork after it (Pitfall 2).

### `src/sif/mcp/transports/http.py` (transport, request-response — MODIFY)

**Analog:** itself. `create_app` (lines 145-157) builds `app = FastAPI()` with NO lifespan today; new params must default (e.g. `lifespan: ... | None = None`) so existing `create_app(server)` test call sites keep working. `HTTPTransport.run` (lines 215-220) calls `create_app(self.server, self.cors_origins)` then `uvicorn.run(app, ...)` — thread the lifespan through `HTTPTransport.__init__` → `create_app` → `FastAPI(lifespan=...)`. The lazy-import precedent at line 217 (`import uvicorn  # noqa: PLC0415`) and the try/except ImportError block (lines 13-23) are the established optional-dependency pattern.

---

### `src/sif/config/settings.py` (config — MODIFY)

**Analog:** existing Watch fields (lines 43-66). New fields (`mcp_watch: bool`, tick/checkpoint intervals) copy this exact `Field(default=..., description=...)` style with the `SIF_` env prefix for free:

```python
watch_restat_interval: float = Field(
    default=5.0,
    ge=0.1,
    description="Seconds between re-stat checks for watched collection roots "
    "that went missing while `sif watch` runs",
)
```

Constraints: `gt`/`ge` bounds on intervals; descriptions flow into generator-owned docs — register in `SECTIONS` (below) and run `make docs-generate`; never hand-edit `docs/configuration.md`.

---

### `src/sif/cli/main.py` `status_cmd` (controller, presentation — MODIFY)

**Analog:** itself (lines 109-146). Rich table pattern to extend with a Watch section (add rows or a second `Table`):

```python
table = Table(title="Index Status")
table.add_column("Metric", style="cyan")
table.add_column("Value", style="green")
table.add_row("Index Path", str(index_path))
```

Note `sif index status` delegates via `ctx.invoke(status_cmd)` (`src/sif/cli/commands/index.py:387-392`) — one extension covers both surfaces. Error handling convention: `console.print(f"[red]Error reading index: {e}[/red]")` + `raise click.ClickException(str(e))` (lines 144-146). Escape user data with `rich.markup.escape` (watch.py:135-138 IN-01 precedent) if collection names appear.

---

### `src/sif/indexing/watcher.py` (service, event-driven core — MODIFY)

**Analog:** itself. Three growth points, each anchored to existing internal patterns:

**D-15 rescope** — copy the `recovery_tick` mutation pattern (lines 422-454): run ON the worker thread inside the tick, use `_schedule_watch(state, observer)` to arm (lines 370-384) and `observer.unschedule(state.handle)` to tear down (line 443), enqueue `FoldResult(needs_reconcile=True)` for newly added roots (line 454):

```python
elif exists and state.missing:
    self._schedule_watch(state, observer)
    state.missing = False
    self._queue.put((state.collection, FoldResult(needs_reconcile=True)))
```

**D-16 checkpoint** — ride the tick site (lines 483-487):

```python
job = self._queue.get(timeout=self._config.restat_interval)
except queue.Empty:
    self.recovery_tick()
```

Reuse `_WAL_CHECKPOINT_TRUNCATE = "PRAGMA wal_checkpoint(TRUNCATE)"` (spelling at `watch.py:43`); minutes-scale cadence (the 5s restat default is too hot — counter/deadline, planner discretion); inspect the `(busy, log, checkpointed)` row as the skip signal.

**D-17 schedule-failure warn** — wrap `_schedule_watch` callers; copy the warning-logger style at lines 352-356 (`logger.warning("Collection root %s missing; not scheduling a watch (D-11)", root)`) with cause + remedy (`raise fs.inotify.max_user_watches`); other roots continue.

## Shared Patterns

### Process/file artifact discipline
**Source:** `src/sif/database/locking.py:67-70`
**Apply to:** `utils/daemon.py` PID file, `utils/service.py` plist/unit writes.
`Path(...).expanduser().resolve()` → sibling-name derivation → `os.open(..., 0o600)` (plist 0644 instead — launchd must read it).

### CLI error convention
**Source:** `src/sif/cli/commands/watch.py:208-217`, `src/sif/cli/main.py:144-146`
**Apply to:** every new flag path (`--stop` not-running, missing manager binary, stale PID file). `raise click.ClickException(str(e))` for user-facing failures; yellow `[yellow]...[/yellow]` console prints for soft notices.

### Logging (never print in hosts)
**Source:** `src/sif/utils/logging.py:120` + `watcher.py:44`
**Apply to:** `mcp/watch_host.py`, daemon callbacks, schedule-failure warnings. `logger = get_logger(__name__)`, stderr handlers — stdout is the stdio JSON-RPC channel.

### Settings → generator-owned docs
**Source:** `scripts/generate_config_ref.py:137-175` (`SECTIONS` allowlist, "Watch Settings" entry)
**Apply to:** `mcp_watch` + interval fields. Register field names in a section, then `make docs-generate`; `tests/test_docs.py` gates it. Never hand-edit `docs/configuration.md` or `docs/cli-reference.md`.

### Deterministic test culture
**Source:** `tests/unit/indexing/test_watcher.py` (synthetic events, zero timing, `_seed_collection`/`_open_indexer` fixtures) and `tests/integration/test_watch_e2e.py` (`_child_env`, `_watch_process` context manager with safety-net termination, `_poll_until` deadline helper at line 133, `_fetch_one` fresh-connection reads).
**Apply to:** ALL new test files. Subprocess tests copy `_watch_process`'s finally-terminate structure; new daemon e2e adds SIGKILL/re-detach (SC4); service tests assert BOTH plist (parse-back via plistlib) and unit text on ANY platform with mocked `subprocess.run` argv asserts. Run pytest with `env -u FORCE_COLOR NO_COLOR=1`.

### Per-burst flock (untouched)
**Source:** `src/sif/database/locking.py:42-98` via `index_lock(...)`
**Apply to:** nothing new — hosts add NO protocol on top (D-03). SC4 is proven by test, not code.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/sif/utils/daemon.py` double-fork body | utility | process lifecycle | No fork/daemon code exists in the repo — use the verified recipe in 13-RESEARCH.md Pattern 2 / Code Examples |
| `src/sif/utils/service.py` launchctl/systemctl invocation | utility | subprocess | No service-manager subprocess site exists — explicit-argv + `shutil.which` gate per D-12; recipes in 13-RESEARCH.md Pattern 3 |
| FastAPI lifespan wiring | transport | request-response | No lifespan exists in `create_app` today — official-docs pattern quoted in 13-RESEARCH.md Code Examples |

## Metadata

**Analog search scope:** `src/sif/{cli,indexing,mcp,database,config,utils}`, `tests/unit/{indexing,cli,mcp,utils}`, `tests/integration`, `scripts/`
**Tracked-source gate:** all named analogs verified via `git ls-files` (gitignored-mirror check: none of the analogs live under `.gsd/` capability trees)
**Files scanned:** ~12 read in full/targeted sections
**Pattern extraction date:** 2026-11-07
