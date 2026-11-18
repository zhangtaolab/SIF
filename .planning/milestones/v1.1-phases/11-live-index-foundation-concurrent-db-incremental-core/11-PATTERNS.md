# Phase 11: Live-Index Foundation (Concurrent DB + Incremental Core) - Pattern Map

**Mapped:** 2026-11-07
**Files analyzed:** 15 (7 new source, 6 modified source, 6 new test + 2 test deletions)
**Analogs found:** 13 / 15 (2 have no in-codebase analog — flock module, subprocess tests — use RESEARCH.md probe-verified patterns)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/sif/database/factory.py` (NEW) | utility (connection factory) | request-response (per-connection setup) | `src/sif/database/database.py:29-52` (`Database.connection` + `_enable_extensions`) | exact role; extend with pragma block/WAL retry from RESEARCH.md |
| `src/sif/database/locking.py` (NEW) | utility (flock context manager) | event-driven (try-lock/wait) | none in codebase — use RESEARCH.md Pattern 3 probe code | no analog |
| `src/sif/indexing/incremental.py` (NEW) | service (IncrementalIndexer) | batch (per-file transform) | `src/sif/cli/commands/index.py:48-213` (`update_cmd` loop body) | exact — this IS the extraction source |
| `src/sif/database/database.py` (MOD) | model/infra wrapper | CRUD | itself (lines 29-52 route through factory; delete lines 108-143) | exact |
| `src/sif/database/connection.py` (MOD) | model/infra wrapper | CRUD | itself (lines 24-37 delegate to factory; delete lines 105-143) | exact |
| `src/sif/database/__init__.py` (MOD) | config (exports) | — | itself | exact |
| `src/sif/cli/commands/index.py` (MOD) | controller (CLI) | request-response | itself (`update_cmd`/`embed_cmd`) | exact |
| `src/sif/indexing/indexer.py` (MOD, deletions) | — | — | — | deletion only |
| `src/sif/indexing/watcher.py` (MOD) | hook (stub) | event-driven | itself (lines 14-15, 31, 106) | exact |
| `src/sif/mcp/backend.py` (MOD, inherits via connection.py) | service | request-response | itself (line 68) | exact |
| `src/sif/config/settings.py` (MOD, additive field) | config | — | itself (lines 19-24, 31-35) | exact |
| `tests/unit/database/test_factory.py` (NEW) | test | — | `tests/unit/db/test_database.py` | role-match |
| `tests/unit/database/test_locking.py` (NEW) | test | — | `tests/unit/db/test_database.py` (class-based structure) | role-match |
| `tests/unit/indexing/test_incremental.py` (NEW) | test | — | `tests/integration/test_embed_idempotency.py` (real-DB + patch helpers) | role-match |
| `tests/integration/test_concurrency.py` (NEW) | test | — | `tests/integration/test_embed_idempotency.py` (`_store_state` raw-sqlite3 inspection, lines 82-97) | role-match |
| `tests/integration/test_two_writer_subprocess.py` (NEW) | test | — | none — RESEARCH.md subprocess skeleton | no analog |
| `tests/integration/test_incremental_equivalence.py` (NEW) | test | — | `tests/integration/test_embed_idempotency.py` (CliRunner + real DB) | exact for the pattern |
| Deletions: `tests/unit/indexing/test_indexer.py`, `TestConnectionPool` in `tests/unit/db/test_database.py:219-300` | — | — | — | — |

## Pattern Assignments

### `src/sif/database/factory.py` (NEW — connection factory)

**Analog:** `src/sif/database/database.py` lines 25-52 (cached-connection property + `_enable_extensions`)

Current connection-creation block being unified (lines 28-52):
```python
if self._connection is None:
    self._connection = sqlite3.connect(
        str(self.db_path),
        detect_types=sqlite3.PARSE_DECLTYPES,
        check_same_thread=False,
    )
    self._connection.row_factory = sqlite3.Row
    self._enable_extensions()
...
def _enable_extensions(self) -> None:
    conn = self._connection
    assert conn is not None
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
    except Exception:
        pass  # sqlite-vec is optional
```

**Extraction directive:** Move exactly this shape (connect kwargs, `sqlite3.Row` factory, foreign_keys pragma, swallow-on-failure sqlite-vec load) into `create_connection(db_path)`, then add from RESEARCH.md Pattern 1/2: `timeout=5.0`, `isolation_level="IMMEDIATE"`, `PRAGMA busy_timeout=5000` before WAL, bounded-retry `PRAGMA journal_mode=WAL` with `('wal',)` row check (degrade+warn otherwise), `PRAGMA synchronous=NORMAL`. See 11-RESEARCH.md "Code Examples" for the full probe-verified factory body.

**Conflict to resolve (RESEARCH.md Open Question 3):** `database.py:47-52` swallows sqlite-vec load failure; `connection.py:33-35` lets it raise. Unify on the swallow form (matches `VectorSearcher`/`SchemaManager` lazy-detect and keeps BM25-only installs working).

**Module skeleton conventions** (from `src/sif/database/connection.py:1-11`):
```python
"""Database connection management."""
import sqlite3
from pathlib import Path
import sqlite_vec
```
Plus module logger: `logger = get_logger(__name__)` (from `src/sif/utils/logging.py`, pattern at `src/sif/mcp/backend.py:22`). Full type annotations, `from __future__ import annotations` (see `database.py:3`).

### `src/sif/database/database.py` (MOD)

**Analog:** itself.

- `Database.connection` (lines 25-36): replace the inline `sqlite3.connect(...)` + `_enable_extensions()` with `self._connection = create_connection(self.db_path)`; keep the None-caching property shape and `check_same_thread` behavior verbatim so `tests/unit/cli/test_database_lifecycle.py` (which subclasses `Database` and asserts `_connection is None` after close) stays green.
- `transaction()` context manager (lines 62-71) — **do not change**; `isolation_level="IMMEDIATE"` at connect time makes every `with conn:` a BEGIN IMMEDIATE with identical commit/rollback semantics (RESEARCH.md Pattern 1, probe-verified):
```python
@contextmanager
def transaction(self) -> Generator[sqlite3.Connection, None, None]:
    conn = self.connection
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
```
- Delete legacy duplicate `DatabaseConnection` (lines 108-143). Blast radius per RESEARCH.md Pitfall 6: `src/sif/database/__init__.py` re-exports and any string-annotation importers.

### `src/sif/database/connection.py` (MOD)

**Analog:** itself.

- `_create_connection` (lines 24-37): replace body with `return create_connection(self._db_path)` — keep the method and the class's `connect()`/`transaction()`/`execute`/`fetchone`/`fetchall` context-manager shapes (lines 39-102) verbatim; `src/sif/mcp/backend.py:68` and `tests/conftest.py:105-113` depend on them.
- Delete `ConnectionPool` (lines 105-143) and its `__init__.py` export.

### `src/sif/database/__init__.py` (MOD)

**Analog:** itself (lines 1-23). Remove `"ConnectionPool"` from the import (line 3) and `__all__` (line 16); add `create_connection` (and lock helper if placed in `sif.database`) to exports. Keep alphabetical `__all__` ordering.

### `src/sif/database/locking.py` (NEW — flock single-writer)

**No in-codebase analog** (no fcntl usage anywhere in src/ — verified by research grep). Use RESEARCH.md Pattern 3 probe-verified code:

```python
fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
deadline = time.monotonic() + timeout_s
while True:
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd                      # winner
    except BlockingIOError:
        if time.monotonic() >= deadline:
            os.close(fd)
            return None                # timed out → caller runs anyway (D-02)
        time.sleep(0.05)
```

Shape it as a `@contextmanager` (follow `Database.transaction` at `database.py:62-71` for context-manager conventions). Key constraints: lock file `{db_path}.lock` derived next to DB, `0600`; fd held for lock lifetime; non-POSIX degrade-and-warn behind `try: import fcntl` guard. D-02 nuance: timeout expiry is NOT an error — loser proceeds after the deadline.

### `src/sif/indexing/incremental.py` (NEW — IncrementalIndexer)

**Analog:** `src/sif/cli/commands/index.py` lines 48-213 — this is a literal extraction, not an analog.

**The loop body to move (lines 110-208), condensed to its pattern:**
```python
scanner = FileScanner()
scan_result = scanner.scan(Path(coll.path), pattern=coll.pattern, ignore_patterns=coll.ignore_patterns)
existing_docs = {d.path: d for d in doc_repo.list_by_collection(coll.id)}
scanned_paths = set()
parser = MarkdownParser()
for file_path in scan_result.files:
    scanned_paths.add(str(file_path))
    parsed = parser.parse(file_path)                      # per-file error → skip + continue
    existing = existing_docs.get(str(file_path))
    if existing:
        if existing.checksum == parsed.checksum and not force:
            continue                                       # checksum-skip (SC2 no-dup property)
        chunk_repo.delete_by_document(existing.id)          # CR-01 stale purge
        if vector_purger is not None:
            vector_purger.delete_embeddings_by_document(existing.id)
        existing.content/title/metadata/mtime/checksum = parsed...  # checksum must persist
        doc_repo.update(existing)
    else:
        doc_repo.create(Document(path=..., collection_id=coll.id, ...))
# removed-file sweep: vector_purger.delete_embeddings_by_document(doc.id) BEFORE doc_repo.delete (WR-01)
# stats: coll.document_count / coll.last_indexed_at = datetime.now(timezone.utc); coll_repo.update(coll)
```

**Extraction directives (RESEARCH.md Patterns 4-5):**
- Each file's writes become one short `with conn:` block (= BEGIN IMMEDIATE under the factory); the removed-file sweep and per-collection stats update are their own short transactions. Today's single `with db.connection:` at `index.py:55` wrapping everything goes away.
- Keep the exact ordering and comments: embeddings purged BEFORE the document row delete (WR-01 comment, lines 194-197); fresh checksum persisted or every run rewrites (comment, lines 170-173); delete-before-insert rationale (CR-01 comment, lines 157-160).
- Preserve the pre-update subprocess hook semantics (lines 85-108, `_PRE_UPDATE_TIMEOUT_SECONDS` at line 35) — decide whether the hook stays in `update_cmd` (presentation/policy) or moves into the indexer; RESEARCH.md assigns progress/notice to CLI, core returns counts.
- Return type carries added/updated/removed counts so `update_cmd` prints the identical `Added:/Updated:/Removed:` block (lines 210-213) — SC3 CLI output identical.
- Pass a progress callback from the CLI instead of Rich `Progress` (keep Rich out of the core; today's Rich usage at lines 127-134 stays in `update_cmd`).
- Per-file parse errors: keep skip-and-continue (lines 140-145).
- Constructor deps follow the repository-injection style of `update_cmd` (repos constructed from `db.connection`, lines 56-59); `_embedding_purger` helper (lines 216-227) moves with the core (it returns `None` without sqlite-vec).
- The `noqa: C901, PLR0912, PLR0915` on `update_cmd` (line 48) should become unnecessary after extraction.

### `src/sif/cli/commands/index.py` (MOD)

**Analog:** itself.

- `update_cmd` (lines 44-213): keep Click decorator shape, `ctx.obj["index_path"]`, `with Database(index_path) as db:` + `db.init_schema()` lifecycle (lines 50-53) — this is the Phase 10.1 WR-01 pattern asserted by `tests/unit/cli/test_database_lifecycle.py`; delegation replaces the loop; error convention `raise click.ClickException(...)` (lines 65, 98-108).
- `embed_cmd` (lines 240-420): structure untouched (D-05) except acquiring the flock (D-01) around the collection loop; its per-collection `with db.connection:` blocks (lines 338, 365) implicitly become BEGIN IMMEDIATE via the factory — accepted (Pitfall 7).
- Lock acquisition: wrap the long-running write work in the new lock context manager, with a CLI "waiting for lock" notice; both winner and loser exit 0 on success.

### `src/sif/indexing/watcher.py` (MOD)

**Analog:** itself. Repoint `TYPE_CHECKING` import (lines 14-15) and string annotations `"DocumentIndexer"` (lines 31, 106) to `IncrementalIndexer` from `sif.indexing.incremental`. Watch for ruff F401/ty F821 on the string annotations (Pitfall 6).

### `src/sif/mcp/backend.py` (MOD — no direct edit expected)

**Analog:** itself, line 64-71:
```python
async def _run_in_db(self, callback: Callable[[Any], T]) -> T:
    def _run() -> T:
        with DatabaseConnection(self.db_path).transaction() as conn:
            return callback(conn)
    return await asyncio.to_thread(_run)
```
Inherits factory pragmas automatically once `connection.py._create_connection` delegates. Read-only searches never open a transaction under `isolation_level="IMMEDIATE"` (implicit transactions only before DML) — verify via `tests/unit/mcp/test_backend.py`.

### `src/sif/config/settings.py` (MOD — additive)

**Analog:** itself. New lock-wait-timeout field follows the existing Field style (lines 31-35):
```python
db_path: Path | None = Field(default=None, description="Path to SQLite database file"),
```
`env_prefix="SIF_"` (line 20) gives the env var for free (suggested `SIF_LOCK_WAIT_TIMEOUT`, default ~30s — discretionary per CONTEXT.md).

### `tests/unit/database/test_factory.py`, `test_locking.py` (NEW)

**Analog:** `tests/unit/db/test_database.py` — class-based test structure (`TestConnectionPool` at lines 219-300 is the structural template even though it is being deleted; also `tests/unit/cli/test_database_lifecycle.py:40-84` for fixture/patch-target discipline: subclass doubles, `monkeypatch.setattr(module, "Database", tracking)`, autouse `get_settings.cache_clear()`).

**Isolation pattern to copy** (`tests/unit/cli/test_database_lifecycle.py:51-72`):
```python
@pytest.fixture(autouse=True)
def isolated_settings() -> Generator[None, None, None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()

@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "sif.db"
    with Database(db_path) as db:
        db.init_schema()
    return db_path
```

### `tests/unit/indexing/test_incremental.py`, `tests/integration/test_concurrency.py`, `tests/integration/test_incremental_equivalence.py` (NEW)

**Analog:** `tests/integration/test_embed_idempotency.py` — the canonical real-DB integration pattern:

Helper patterns to copy (lines 52-117):
```python
def _seed_collection(db_path: Path, settings: Settings) -> str:
    db = Database(db_path)
    with patch("sif.config.settings.get_settings", return_value=settings):
        db.init_schema()
        with db.connection:
            ...coll_repo.create(coll); doc_repo.create(doc)
    db.close()

def _store_state(db_path: Path) -> tuple[int, int, set[str], set[str]]:
    conn = sqlite3.connect(str(db_path))
    try:
        conn.enable_load_extension(True); sqlite_vec.load(conn); ...
        emb_count = conn.execute("SELECT COUNT(*) FROM document_embeddings").fetchone()[0]
    finally:
        conn.close()

def _invoke_embed(db_path, manager, settings, args):
    runner = CliRunner()
    with (patch(...get_settings...), patch(...EmbeddingManager.from_settings...)):
        return runner.invoke(embed_cmd, args, obj={"index_path": db_path})
```
Also `_delenv_settings_vars(monkeypatch)` (line 120+) for env hermeticity.

**DB-state assertions, never file listings** (Pitfall 5): assert row counts/ids via a separate connection after closing; do not assert `-wal`/`-shm` presence while connections are open.

### `tests/integration/test_two_writer_subprocess.py` (NEW)

**No in-codebase analog** — no existing subprocess-racing test. Use RESEARCH.md "Deterministic subprocess two-writer test" skeleton: parent opens the same `{db_path}.lock`, `fcntl.flock(fd, LOCK_EX | LOCK_NB)`, spawns `[sys.executable, "-m", "sif.cli.main", ...]` with `SIF_DB_PATH` env, short sleep, release, `communicate(timeout=30)`, assert `returncode == 0` and DB state (not timing). Run with `env -u FORCE_COLOR NO_COLOR=1` when invoking pytest from agent shells.

### `tests/conftest.py` (MOD, likely)

**Analog:** itself. `db_connection`/`temp_db` fixtures (lines 104-181) construct `DatabaseConnection` directly — they inherit factory pragmas automatically. `docs_runner` (lines 608-613) shows the CliRunner env-pinning pattern for subprocess-equivalent invocations.

## Shared Patterns

### Transaction / error handling
**Source:** `src/sif/database/database.py:62-71` — apply everywhere unchanged; the factory's `isolation_level="IMMEDIATE"` is the only mechanism change. Never adopt `isolation_level=None` (RESEARCH.md Pitfall 2).

### CLI lifecycle
**Source:** `src/sif/cli/commands/index.py:50-53` — `with Database(index_path) as db: db.init_schema()` held for the whole command body (26 sites, WR-01). Keep in `update_cmd`/`embed_cmd`. Errors: `raise click.ClickException(str(e))`.

### Logging
**Source:** `src/sif/mcp/backend.py:22` — `logger = get_logger(__name__)`, module-level, stderr. Apply to factory.py, locking.py, incremental.py.

### sqlite-vec load (swallow + lazy detect)
**Source:** `src/sif/database/database.py:47-52` — `except Exception: pass  # sqlite-vec is optional`. Unify both connection paths on this (resolves the connection.py:33-35 disagreement).

### Code style gates
Line length 100, mccabe ≤ 10, `list[str] | None` unions, full annotations, ruff isort combine-as-imports, two blank lines after imports, `ty check src/sif` clean. Coverage `fail_under=90` — in-suite tests must carry coverage (subprocess tests are outcome-only).

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/sif/database/locking.py` | utility | event-driven | No fcntl/file-lock code exists in src/ — use RESEARCH.md Pattern 3 (probe-verified) |
| `tests/integration/test_two_writer_subprocess.py` | test | event-driven | No existing subprocess-race tests — use RESEARCH.md deterministic parent-holds-lock skeleton |

## Metadata

**Analog search scope:** `src/sif/database/`, `src/sif/indexing/`, `src/sif/cli/commands/`, `src/sif/mcp/`, `src/sif/config/`, `tests/unit/db/`, `tests/unit/cli/`, `tests/unit/database/` (absent), `tests/unit/indexing/`, `tests/integration/`
**Files scanned:** 13 analog candidates read; all verified git-tracked via `git ls-files`
**Pattern extraction date:** 2026-11-07
