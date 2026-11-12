# Phase 12: `sif watch` Foreground MVP - Pattern Map

**Mapped:** 2026-11-07
**Files analyzed:** 11 (5 source extend/new, 1 pyproject, 1 CLI registration, 5 test files)
**Analogs found:** 9 / 10 (one greenfield: signal handling — no analog anywhere in `src/sif`)

All analog paths verified git-tracked via `git ls-files`.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/sif/indexing/incremental.py` (extend: `update_paths()` + missing-root guard) | service (domain core) | CRUD / file-I/O | itself (`update_collection`, `_process_file`, `_sweep_removed`) | exact |
| `src/sif/indexing/watcher.py` (rewrite) | service (event pipeline) | event-driven | itself (skeleton: dispatch shape, `_event_path`, `is_directory` skips) + `indexing/scanner.py` predicate | partial (stubs are log-only; rewrite target) |
| `src/sif/indexing/scanner.py` (extend: `DEFAULT_IGNORE_PATTERNS` + shared predicate helper) | utility | file-I/O / transform | itself (`_should_ignore`, `scan`) | exact |
| `src/sif/cli/commands/watch.py` (NEW) | controller (CLI) | request-response / long-lived foreground | `src/sif/cli/commands/index.py` `update_cmd` | role-match |
| `src/sif/cli/main.py` (extend: register `watch_cmd`) | route | request-response | existing `cli.add_command` block | exact |
| `src/sif/config/settings.py` (extend: `watch_*` fields) | config | — | `lock_wait_timeout` field | exact |
| `pyproject.toml` (watchdog cap `>=4.0.0,<7.0.0`) | config | — | line 38 current `"watchdog>=3.0.0"` | exact |
| `tests/unit/indexing/test_incremental.py` (extend) | test | — | itself (fixture helpers) | exact |
| `tests/unit/indexing/test_watcher.py` (rewrite) | test | — | itself (delete) + `test_incremental.py` real-DB culture | role-match |
| `tests/unit/indexing/test_scanner.py` (extend) | test | — | itself | exact |
| `tests/integration/test_watch_e2e.py` (NEW) + `tests/unit/cli/test_watch_cmd.py` (NEW) | test | — | `tests/integration/test_two_writer_subprocess.py` / `test_incremental_equivalence.py` | role-match |

## Pattern Assignments

### `src/sif/indexing/incremental.py` — extend with `update_paths()` + missing-root guard

**Analog:** the file itself. New method mirrors `update_collection`'s contract exactly (D-06).

**Missing-root guard placement** — insert at top of `update_collection` (line 87, after signature) and inside `update_paths`. Current vulnerable scan (lines 110-116):

```python
scanner = FileScanner()
scan_result = scanner.scan(
    Path(collection.path),
    pattern=collection.pattern,
    ignore_patterns=collection.ignore_patterns,
)
```
`rglob` on a missing root returns `[]` → `_sweep_removed` (line 142) mass-deletes. Guard shape: `if not Path(collection.path).exists(): logger.warning(...); self._notify(progress, f"missing {collection.name}"); return IncrementalResult()`.

**Per-file processing to reuse verbatim** — `_process_file` (lines 158-219) already takes `existing: Document | None` explicitly, so `update_paths` looks up via `self._doc_repo.get_by_path(str(path), collection.id)` and delegates. Its internal checksum-skip (lines 176-179) makes unchanged paths free `skipped` outcomes.

**Single-doc removal to extract** — `_sweep_removed` inner body (lines 228-238): vector purge BEFORE doc delete (vec0 rows don't FK-cascade), both inside one `with self._conn:` block. Extract into `_remove_document(doc)` shared by both paths.

**Stats-refresh tail to mirror** (lines 145-148):
```python
with self._conn:
    collection.document_count = len(self._doc_repo.list_by_collection(collection.id))
    collection.last_indexed_at = datetime.now(timezone.utc)
    self._coll_repo.update(collection)
```

**Progress protocol** (docstring lines 99-105): `"scan <n>"`, `"unchanged <name>"`, `"error <message>"`, `"indexed <name>"`. New additive code `"missing <name>"` is safe — the CLI renderer matches only known codes (index.py:159-169).

**Constructor/imports** (lines 15-39, 72-85): module-level `logger = get_logger(__name__)`, `TYPE_CHECKING` for `VectorSearcher`, repos built from the single `conn` — follow unchanged.

---

### `src/sif/indexing/watcher.py` — rewrite (host-agnostic event pipeline)

**Analog:** the file itself (skeleton only — dispatch shape, not logic). Preserve: `_event_path` helper (lines 20-22, `os.fsdecode` — the security-note normalization), `event.is_directory` early-returns, `FileSystemEventHandler` base. Delete: `_should_handle` extension-set filter (lines 85-94 — bypasses collection ignore rules, Pitfall 6) and the broken `FileWatcher.start/stop` lifecycle (start overwrites a live observer at line 129; stop never unschedules).

**New intake shape** — handler `on_*` methods call `debouncer.handle_event(event)` only; all `on_moved` filtering uses `dest_path` (D-07). Wiring per research Pattern 3:

```python
from watchdog.observers import Observer
from watchdog.utils.event_debouncer import EventDebouncer

observer = Observer()                        # FSEvents/inotify auto-select
debouncer = EventDebouncer(interval_s, on_burst)   # POSITIONAL args (D-05)
```

**Fold rule (in the settled callback — must be cheap, runs under the debouncer's condition lock):** `moved(src→dest)`: dest joins index-candidates (predicate-checked), src joins remove-candidates; `created`/`modified` → index-candidates; `deleted` → remove-candidates. A path in both sets is fine — `update_paths` stats it once. Then push batch onto `queue.Queue` and return; a single worker thread pops, wraps in `index_lock(...)`, and calls `update_paths`.

**Path handling** — schedule `str(Path(coll.path).resolve())` (FSEvents delivers realpaths, `/private/var/...`); `FileScanner.scan()` already resolves (scanner.py:69) so stored paths are resolved — resolve event paths before predicate/`get_by_path`.

---

### `src/sif/indexing/scanner.py` — extend (one shared predicate, D-07/D-08)

**Analog:** the file itself.

**`DEFAULT_IGNORE_PATTERNS`** (lines 26-48, tuple): add `"*.sb-*"`, `"4913"`, `".#*"`, `"*.tmp"` (`.DS_Store`/`*.swp`/`*~` already present).

**The subtlety:** `scan()` applies the collection `pattern` via `root_path.rglob(pattern)` (line 80) — OUTSIDE `_should_ignore`. A shared predicate (e.g. `FileScanner.matches(root_path, file_path, pattern, ignore_patterns) -> bool`) must check BOTH pattern-match and `_should_ignore`; `scan()` and the watch handler both call it. `_should_ignore`'s fnmatch semantics (lines 109-124: per-part, full rel-path, and filename checks) are the parity baseline — mirror-test `scan()` membership == `matches()` True.

---

### `src/sif/cli/commands/watch.py` — NEW command module

**Analog:** `src/sif/cli/commands/index.py` (`update_cmd`, lines 40-111).

**Command skeleton to copy** (index.py lines 40-60):
```python
@click.group("index")  # watch is a TOP-LEVEL command like ls_cmd/pull_cmd, not a group
...
@index_group.command("update")
@click.option("--collection", "-c", help="Update specific collection only")
@click.option("--force", "-f", is_flag=True, help="Force re-index all documents")
@click.pass_context
def update_cmd(ctx: click.Context, collection: str | None, force: bool) -> None:
    index_path = ctx.obj["index_path"]
    with Database(index_path) as db:
        db.init_schema()
```
Watch adapts: top-level `@click.command("watch")`, repeatable `-c` (`multiple=True`), `--embed` flag, `--verbose`. Registration in `src/sif/cli/main.py` lines 84-104 (import after the `cli` group, then `cli.add_command(watch_cmd)`).

**flock usage to copy** (index.py lines 53-60) — but per-burst inside the worker (D-04), not around the command body:
```python
lock_timeout = get_settings().lock_wait_timeout
with index_lock(
    Path(index_path),
    lock_timeout,
    on_wait=lambda: console.print(
        f"[dim]Another index writer is running; waiting up to {lock_timeout:.0f}s...[/dim]"
    ),
):
```

**Collections listing** (index.py lines 61-76): use `coll_repo.list_all()` — NOT `list_enabled()` (filters `include_by_default = 1`; a search-excluded collection still needs watching). Zero-collections notice (lines 72-76) reused verbatim.

**Progress-event rendering** (index.py lines 147-170, `_render_index_event`): the `"code payload"` `partition(" ")` pattern with unknown-code tolerance. Watch adds per-batch summary lines; document content never Rich-markup-rendered.

**DO NOT copy `embed_cmd`'s transaction shape** (manager.embed at index.py:347 sits INSIDE `with db.connection:` at line 323). Watch `--embed` must: `_process_file` BM25 commit → chunk+embed with NO txn open → short vector-write txn (`chunk_repo.create` loop + `add_embeddings_batch`). DO copy embed_cmd's dimension check (index.py lines 236-256, `get_model_info()["embedding_dim"]` + `FLOAT[n]` regex) at first `--embed` use, and its lazy-import style (`from sif.config.settings import get_settings  # noqa: PLC0415`, line 51).

**Signal handling (D-14) — NO analog exists** (grep-verified: no `signal` import anywhere in `src/sif`). Use the research-verified skeleton:
```python
state = {"stop": False, "sigs": 0}
def _handle(signum, frame):
    state["sigs"] += 1
    if state["sigs"] >= 2:
        sys.exit(130)          # second signal: immediate, no flush
    state["stop"] = True
signal.signal(signal.SIGINT, _handle)
signal.signal(signal.SIGTERM, _handle)
```
Shutdown sequence: stop flag → `observer.stop()` → `debouncer.stop()` → drain queue once bounded → join threads → `conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")` in `try/finally` → `sys.exit(0)`.

---

### `src/sif/config/settings.py` — extend

**Analog:** `lock_wait_timeout` (lines 36-41):
```python
lock_wait_timeout: float = Field(
    default=30.0,
    ge=0,
    description="Seconds an index writer waits for a competing writer's "
    "lock before proceeding with its own pass anyway",
)
```
Add `watch_debounce_interval: float` (default ~0.5), `watch_ignore_patterns: list[str]` (semantics: global extension of the shared predicate, NOT watch-only — preserves LIVE-04 parity), `watch_update_depth: str` (`"bm25"` default | `"embed"`). `env_prefix="SIF_"` (line 20) gives the env vars for free.

## Shared Patterns

### Per-file BEGIN IMMEDIATE transactions
**Source:** `src/sif/indexing/incremental.py` lines 181-216 — every `with self._conn:` block is one short txn (factory sets `isolation_level="IMMEDIATE"`). Apply to: `update_paths` add/update/remove paths and the vector-write txn. Never hold a txn across an embed call (Pitfall 1/5).

### flock per work unit
**Source:** `src/sif/database/locking.py` lines 42-98 — `index_lock(db_path, timeout_s, on_wait=...)` context manager; wait-then-run loser semantics; lock file 0600 resolved next to DB. Watch acquires it per settled burst (D-04), never for process lifetime.

### Progress-event protocol
**Source:** `incremental.py` lines 99-105 + renderer `index.py` lines 147-170. Core stays Rich-free; hosts render. Watch adds `"missing <name>"` additively.

### Logging
**Source:** every module: `logger = get_logger(__name__)`, stderr, `sif.`-prefixed. Log paths at debug, never document content.

### Error handling (CLI)
**Source:** `index.py` — `raise click.ClickException(str(e))` for user-facing failures; per-collection `try/except` + `failed_collections` accumulate-then-raise-outside-txn (lines 369-382) is the model for per-batch error tolerance in watch.

### Test culture
**Source:** `tests/unit/indexing/test_incremental.py` lines 30-80 — module-level body constants (`BODY_ALPHA`/`BODY_BETA`), helper functions `_seed_collection` / `_open_indexer` / `_doc_paths` (query through a FRESH connection, not ORM cache), `patch("sif.config.settings.get_settings", return_value=_test_settings())` for hermetic schema init. Synthetic-event tests construct watchdog event objects directly (`FileCreatedEvent('/x/a.md')`, `FileMovedEvent(src, dest)` — both positional) and drive the fold/settled callback with zero timing (D-15). Integration analogs: `tests/integration/test_two_writer_subprocess.py`, `test_incremental_equivalence.py` (real DB, real FS, deadline-bounded).

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| Signal handling in `watch.py` (D-14) | controller | event-driven | No `signal` usage anywhere in `src/sif` — use research's machine-verified skeleton (exit 0 graceful / 130 second SIGINT / 0 SIGTERM) |
| `PRAGMA wal_checkpoint(TRUNCATE)` | — | — | Appears nowhere in `src/sif` or `tests/` today — new code per D-14, run on the worker's connection after quiesce |
| Real-FS watch e2e | test | event-driven | No observer-based test exists; follow D-15 (deadline-bounded outcome polling, serialized, `os.replace` atomic save in `tmp_path`) |

## Metadata

**Analog search scope:** `src/sif/indexing/`, `src/sif/cli/`, `src/sif/database/`, `src/sif/config/`, `tests/unit/indexing/`, `tests/integration/`
**Files scanned:** 12 primary + directory listings
**Pattern extraction date:** 2026-11-07
**Note:** docs are generator-owned — `docs/cli-reference.md`/`docs/configuration.md` update via `make docs-generate` only, never hand-edited (add a docs-regen step to the final plan).
