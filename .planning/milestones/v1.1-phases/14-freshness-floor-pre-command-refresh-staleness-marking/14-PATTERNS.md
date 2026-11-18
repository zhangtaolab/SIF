# Phase 14: Freshness Floor (Pre-Command Refresh + Staleness Marking) - Pattern Map

**Mapped:** 2026-11-08
**Files analyzed:** 16 (4 new, 12 modified; docs regeneration via `make docs-generate` is a process step, not a hand-edit)
**Analogs found:** 16 / 16 (every file has an in-repo analog — this phase is pure integration; RESEARCH.md confirms zero new dependencies)

All analog paths below verified git-tracked via `git ls-files`.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/sif/indexing/drift.py` (NEW) | service (indexing) | file-I/O (stat walk) + bounded CRUD refresh | `src/sif/indexing/incremental.py` + `src/sif/indexing/watcher.py` burst | exact |
| `src/sif/search/staleness.py` (NEW) | service (search enrichment) | batch transform | `src/sif/search/context_attach.py` | exact |
| `src/sif/core/models.py` (MOD: `SearchResult`) | model | transform | itself — `context_description` field precedent (models.py:221, 236) | exact |
| `src/sif/database/repositories.py` (MOD: `DocumentRepository`) | repository | CRUD (read) | itself — `list_by_collection` (repositories.py:192-198) | exact |
| `src/sif/cli/commands/search.py` (MOD: trio + format battery) | controller (CLI) | request-response | itself — trio bodies + `_field` format battery | exact |
| `src/sif/cli/main.py` (MOD: `status_cmd`) | controller (CLI) | request-response | itself — Phase 13 Watch row (main.py:110-129, 165-173) | exact |
| `src/sif/mcp/backend.py` (MOD: `hybrid_search`) | service (MCP mapping) | transform | itself — explicit field re-mapping (backend.py:100-112) | exact |
| `src/sif/config/settings.py` (MOD: 2 new `SIF_` fields) | config | — | itself — `watch_*` field block (settings.py:43-85) | exact |
| `scripts/generate_config_ref.py` (MOD: SECTIONS) | config tooling | transform | itself — `SECTIONS` allowlist (generate_config_ref.py:150-190) | exact |
| `tests/unit/indexing/test_drift.py` (NEW) | test | — | `tests/unit/indexing/test_incremental.py` | exact |
| `tests/unit/search/test_staleness.py` (NEW) | test | — | `tests/unit/search/test_context_attach.py` | exact |
| `tests/unit/cli/test_search.py` (MOD) | test | — | itself — mock scaffolds (test_search.py:246-306, 831-874) | exact |
| `tests/unit/cli/test_status.py` (MOD) | test | — | itself — `TestWatchSection` (test_status.py:95-194) | exact |
| `tests/unit/cli/test_index_locking.py` (MOD) | test | — | itself — `_recording_lock` + `TestHeldLockProceeds` (107-127, 174-211) | exact |
| `tests/unit/indexing/test_incremental.py` (MOD: D-08 invariant regression) | test | — | itself — purge test (137+) | exact |
| `tests/unit/mcp/test_backend.py` (MOD) | test | — | itself — `test_hybrid_search_mocks` (63-83) | exact |

## Pattern Assignments

### `src/sif/indexing/drift.py` (NEW — service, file-I/O + bounded refresh)

**Primary analog:** `src/sif/indexing/incremental.py` (same package, same dataflow: walk → compare vs `documents` → targeted writes). **Secondary:** `src/sif/indexing/watcher.py:728-789` (flock-wrapped burst) and `src/sif/cli/commands/index.py:48-60` (CLI-side lock invocation).

**Imports pattern** (incremental.py:15-32) — stdlib → first-party `sif`, `get_logger(__name__)`, dataclass result type:
```python
from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from sif.core.models import Collection, Document
from sif.database.repositories import (
    CollectionRepository,
    DocumentRepository,
)
from sif.indexing.parser import MarkdownParser
from sif.indexing.scanner import FileScanner
from sif.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class IncrementalResult:
    """Counts reported by one incremental update pass over a collection."""

    added: int = 0
    updated: int = 0
    removed: int = 0
    unchanged: int = 0
```
Copy this shape: module docstring citing the decision IDs, `@dataclass` report type (`DriftReport`) instead of ad-hoc tuples.

**Missing-root guard** (incremental.py:111-120 and 193-199 — the guard runs twice, once per entry point; drift.py MUST have it in the WALK too, per RESEARCH Pitfall 4):
```python
# D-11: a missing collection root must never be read as mass
# deletion — rglob on a missing root yields no files, which the
# sweep below would otherwise treat as "every file vanished".
if not Path(collection.path).exists():
    logger.warning(
        "Collection root %s does not exist; skipping update (all documents preserved)",
        collection.path,
    )
    self._notify(progress, f"missing {collection.name}")
    return IncrementalResult()
```

**Walk shape** (incremental.py:122-134) — `FileScanner` is the only membership predicate; snapshot stored docs once per collection:
```python
scanner = FileScanner()
scan_result = scanner.scan(
    Path(collection.path),
    pattern=collection.pattern,
    ignore_patterns=collection.ignore_patterns,
)
...
existing_docs = {d.path: d for d in self._doc_repo.list_by_collection(collection.id)}
```
Drift.py replaces the `list_by_collection` (SELECT *, loads content — RESEARCH Pitfall 7) with the new lightweight `list_stat_by_collection` and compares `st_mtime` (mtime-ONLY — `documents.file_size` is body-byte-length, never refreshed; RESEARCH Pitfall 1). Resolve walk paths before comparing (`str(f.resolve())` — stored paths are resolved, incremental.py:203; RESEARCH Pitfall 10).

**The refresh seam being consumed** (incremental.py:164-171) — `update_paths` signature; drift.py calls this, never re-implements it:
```python
def update_paths(
    self,
    collection: Collection,
    paths: Iterable[Path],
    *,
    force: bool = False,
    progress: Callable[[str], None] | None = None,
) -> IncrementalResult:
```

**Flock-wrapped burst** (watcher.py:736-745, 776-782) — acquire the lock ONLY after drift was found (clean search must never create the lock file, RESEARCH Pitfall 6):
```python
# watcher._run_job -> BM25-only depth:
with index_lock(self._db_path, self._config.lock_timeout):
    result = self._run_burst(collection, folded)
# _run_burst, bm25 depth:
indexer = IncrementalIndexer(self._conn)
if self._config.depth != "embed":
    return indexer.update_paths(collection, paths, progress=progress)
```
CLI-side lock invocation precedent (`index.py:48-60`) — settings-driven timeout:
```python
from sif.config.settings import get_settings  # noqa: PLC0415

lock_timeout = get_settings().lock_wait_timeout
with index_lock(
    Path(index_path),
    lock_timeout,
    on_wait=lambda: console.print(
        f"[dim]Another index writer is running; waiting up to {lock_timeout:.0f}s...[/dim]"
    ),
):
```

---

### `src/sif/search/staleness.py` (NEW — service, batch transform)

**Analog:** `src/sif/search/context_attach.py` — the exact sibling RESEARCH Pattern 3 prescribes.

**Full core pattern** (context_attach.py:24-62) — copy this function shape verbatim: early-return on empty, ONE constant SQL (no interpolated values), decorate results in Python, mutate-and-return:
```python
def attach_path_contexts(
    db: sqlite3.Connection,
    results: list[SearchResult],
) -> list[SearchResult]:
    if not results:
        return results

    cursor = db.execute(
        "SELECT target_id, content FROM contexts WHERE context_type = 'path' ORDER BY updated_at"
    )
    context_map = {normalize_path(row["target_id"]): row["content"] for row in cursor.fetchall()}

    for result in results:
        key = normalize_path(result.path)
        if key in context_map:
            result.context_description = context_map[key]
    return results
```
Staleness version: `SELECT document_id FROM document_embeddings` → Python set → `r.vectors_stale = r.document_id not in embedded`. Guard the execute with `except sqlite3.OperationalError: return results` (vec0 table is conditionally created, schema.py:315-323 — degrade = no markers, never a crash).

**Why one scan, not per-result queries** (vector.py:219-228, in-repo docstring, verbatim rule):
```python
"""...The vec0 virtual table has no index on its metadata columns, so each
per-document filtered lookup costs a full table scan; callers judging
every document must batch. Rows are iterated one at a time (never
fetchall) so peak memory is the resulting map, not a row buffer."""
```

**Call-site wiring** — identical `_attach_contexts` method at three sites; the staleness sibling is called right beside each (D-09's one-code-path contract):
```python
# bm25.py:119-121 (call at :117); same shape at vector.py:132-134 (call at :130),
# hybrid.py:112-114 (call at :90)
def _attach_contexts(self, results: list[SearchResult]) -> list[SearchResult]:
    """Attach path context descriptions to search results via batch query."""
    return attach_path_contexts(self.db, results)
```

---

### `src/sif/core/models.py` (MOD — model, transform)

**Analog:** itself — `context_description` is the exact precedent for a late-added defaulted enrichment field flowing to every format.

**Field landing site** (models.py:207-237) — add `vectors_stale: bool = False` after `context_description` (:221) and a `"vectors_stale": self.vectors_stale` entry in `to_dict()`:
```python
@dataclass
class SearchResult:
    """A search result."""

    document_id: str
    title: str
    path: str
    collection_name: str
    score: float
    content: str | None = None
    highlights: list[str] = field(default_factory=list)
    rank: int = 0
    scores: dict[str, float | None] = field(default_factory=dict)
    snippet: str | None = None
    context_description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "document_id": self.document_id,
            ...
            "context_description": self.context_description,
        }
```
The `--line-numbers` path preserves new keys automatically (`add_line_numbers_to_results` copies dicts, only adds `line_numbers` — `src/sif/cli/formatters.py:11-25`, per RESEARCH verification).

---

### `src/sif/database/repositories.py` (MOD — repository, CRUD read)

**Analog:** itself — `DocumentRepository.list_by_collection` (repositories.py:192-198) is the shape; the new `list_stat_by_collection` is its lightweight sibling:
```python
def list_by_collection(self, collection_id: str) -> list[Document]:
    """List documents in a collection."""
    cursor = self.db.execute(
        "SELECT * FROM documents WHERE collection_id = ? ORDER BY filename",
        (collection_id,),
    )
    return [self._row_to_document(row) for row in cursor.fetchall()]
```
New method: `SELECT path, mtime FROM documents WHERE collection_id = ?` — must NOT load content (RESEARCH Pitfall 7); the `idx_documents_collection` index already exists (schema.py:353-356). Constructor/parameterized style from the class (:137-139). Return a `dict[str, float]` or list of tuples — keep it raw, no `_row_to_document` (that materializes content).

---

### `src/sif/cli/commands/search.py` (MOD — controller, request-response)

**Analog:** itself — the three command bodies; this file IS the D-01 placement.

**Where the check slots in** (search_cmd, search.py:198-227 — vsearch :379-405 and query :517-546 have the same shape) — after collection resolution (needs `Collection` objects), before searcher/pipeline construction:
```python
with Database(index_path) as db:
    db.init_schema()

    # Build options
    options = SearchOptions(...)

    # Get collection IDs if specified
    if collection:
        with db.connection:
            repo = CollectionRepository(db.connection)
            options.collection_ids = []
            for name in collection:
                coll = repo.get_by_name(name)
                if coll:
                    options.collection_ids.append(coll.id)
    elif not search_all:
        with db.connection:
            repo = CollectionRepository(db.connection)
            enabled = repo.list_enabled()
            options.collection_ids = [c.id for c in enabled]

    # [NEW] drift check goes HERE; --all leaves collection_ids=None —
    # the walk must then use repo.list_all()

    # Search
    with db.connection:
        searcher = BM25Searcher(db.connection)
        results = searcher.search(query, options)
```
Note the trio currently discards `Collection` objects (keeps only ids) — the shared `_resolve_collections()` helper RESEARCH recommends keeps both. The resolution block is copy-pasted 3x today; extracting it is optional cleanup, not a requirement.

**Stderr contract precedent** — the module's `console = Console()` (search.py:26) writes to STDOUT; do NOT copy neighboring `console.print` for the D-07/D-13 notices. Use the `mcp.py` precedent (`src/sif/cli/commands/mcp.py:12, 28-30`):
```python
console = Console()
console_err = Console(stderr=True)
...
console_err.print(
    "[yellow]Warning: No index found. Some features may not work.[/yellow]",
)
```
(or `click.echo(msg, err=True)`). Gate with `quiet` / `set_quiet` exactly as the commands already do (search.py:189-191).

**Format battery touchpoints for the marker (D-12)** — the dual-shape reader plus the three explicit formats:
```python
# search.py:72-74 — reads attrs on SearchResult rows AND keys on --line-numbers dicts:
def _field(r: Any, name: str) -> Any:
    """Read a result field from a dict (--line-numbers path) or object row."""
    return r.get(name, "") if isinstance(r, dict) else getattr(r, name, "")

# search.py:85 — CSV header (add one column):
buf.write("rank,score,title,path,collection\n")

# search.py:104 — MD per-result block start (inline annotation joins here):
lines.append(f"## {_field(r, 'rank')}. {_field(r, 'title')}")

# search.py:127 — XML per-result element (attribute; quoteattr discipline governs):
lines.append(f'  <result rank="{_field(r, "rank")}" score="{score}">')
```
JSON needs no formatter change (`format_results_json`, :63-69, serializes `to_dict()` — the new boolean rides along). Rich table marker: dim inline annotation next to the title cell (search.py:288-292), no new column. `escape()` discipline for any wording variant.

---

### `src/sif/cli/main.py` (MOD — controller, request-response)

**Analog:** itself — the Phase 13 Watch row is the exact pattern D-10 extends: probe helper + try/except + one `table.add_row`.

**Probe helper + degrade-never-fail row** (main.py:110-129, 165-173):
```python
def _watch_status_text(index_path: Path) -> str:
    """Watch-section value for the status table (D-08)."""
    pid_path = daemon.pid_path_for(index_path)
    payload = daemon.read_pid_file(pid_path)
    if payload is None:
        ...
    return f"running — {payload['mode']} · PID {payload['pid']} · {payload['depth']}"
...
            # Watch section (D-08): one row sourced from the daemon PID file.
            # Metadata display must never take the status command down, so
            # any unexpected failure renders as not-running instead.
            try:
                watch_text = _watch_status_text(Path(index_path))
            except Exception:
                logger.debug("Watch status probe failed", exc_info=True)
                watch_text = "not running"
            table.add_row("Watch", watch_text)
```
Vector-lag row: `_vector_lag_text(db.connection) -> str` sibling using the same derived SQL; on vec0-missing (`sqlite3.OperationalError`) render `"n/a"`, never raise.

---

### `src/sif/mcp/backend.py` (MOD — service, transform)

**Analog:** itself — `hybrid_search` re-maps every field explicitly; unknown core-model fields are DROPPED here (RESEARCH Pitfall 8 — D-11's "automatic" claim is wrong at this boundary; one forwarding line is required).

**Mapping site** (backend.py:100-112) — `metadata` already carries extra core fields; add the flag there (zero protocol change):
```python
core_results = pipeline.search(query, options)
return [
    SearchResult(
        doc_id=r.document_id,
        path=r.path,
        title=r.title,
        content=r.content,
        score=r.score,
        highlights=r.highlights,
        metadata={"rank": r.rank, "collection_name": r.collection_name},
    )
    for r in core_results
]
```
Protocol target (`src/sif/mcp/protocol.py:199-208`): `metadata: dict[str, Any] = Field(default_factory=dict)` — serializes through `model_dump()` at the handlers.

---

### `src/sif/config/settings.py` (MOD — config)

**Analog:** itself — the `watch_*` block (Phase 12) is the field-group precedent; `lock_wait_timeout` is the numeric-constraint style.

**Field patterns** (settings.py:36-41, 43-49, 61-66):
```python
lock_wait_timeout: float = Field(
    default=30.0,
    ge=0,
    description="Seconds an index writer waits for a competing writer's "
    "lock before proceeding with its own pass anyway",
)
# Watch settings (Phase 12 live index)
watch_debounce_interval: float = Field(
    default=0.5,
    gt=0,
    description="Quiet window in seconds a filesystem event burst must "
    "settle for before `sif watch` runs one incremental update",
)
```
New fields: a bool enable toggle (default True) + an int max-files cap (`ge=1`, default per RESEARCH A2 ~100-200, planner picks). Multi-line description strings wrapping the WHY into docs. Env prefix `SIF_` is automatic (model_config, :19-24). A `field_validator` is only needed if a membership set exists (pattern at :200-214) — not needed for a bool/int.

### `scripts/generate_config_ref.py` (MOD — config tooling)

**Analog:** itself — SECTIONS allowlist; a field not registered here silently misses `docs/configuration.md` and fails `tests/test_docs.py` (RESEARCH Pitfall 9).

**Registration site** (generate_config_ref.py:150-190) — natural home: extend "Search Settings" (:176) or add a small new section:
```python
SECTIONS: list[tuple[str, list[str]]] = [
    ...
    ("Search Settings", ["default_search_type", "default_limit"]),
    (
        "Watch Settings",
        [
            "watch_debounce_interval",
            ...
        ],
    ),
    ...
]
```
Then regenerate via `make docs-generate` — docs are generator-owned (memory: never hand-edit `docs/cli-reference.md` / `docs/configuration.md`).

---

### `tests/unit/indexing/test_drift.py` (NEW — test)

**Analog:** `tests/unit/indexing/test_incremental.py` — the deterministic tmp_path seeding + fresh-connection assertion culture.

**Seeding helpers** (test_incremental.py:34-58, 70-104):
```python
def _delenv_settings_vars(monkeypatch) -> None:
    """Keep Settings construction hermetic against a developer shell."""
    for var in ("SIF_EMBEDDING_DIM", "SIF_MODEL_TYPE", "SIF_MODEL_NAME"):
        monkeypatch.delenv(var, raising=False)


def _seed_collection(db_path: Path, notes: Path) -> str:
    """Init schema and create one collection pointing at ``notes``; return its id."""
    db = Database(db_path)
    with patch("sif.config.settings.get_settings", return_value=_test_settings()):
        db.init_schema()
        with db.connection:
            coll_repo = CollectionRepository(db.connection)
            coll = Coll(name="notes", path=str(notes))
            coll_repo.create(coll)
            coll_id = coll.id
    db.close()
    return coll_id


def _doc_paths(db_path: Path) -> set[str]:
    """Read document paths through a fresh connection (Pitfall 5: query, not files)."""
    conn = sqlite3.connect(str(db_path))
    try:
        return {row[0] for row in conn.execute("SELECT path FROM documents")}
    finally:
        conn.close()
```
Drift determinism: `os.utime(path, (1_700_000_000, 1_700_000_000))` for touch-drift, content writes for edit-drift, `.unlink()` for delete-drift — never `sleep()` (RESEARCH Pitfall 11). SC2 clean-path assertions are structural (lock file absent, DB bytes unchanged), not latency. Over-cap test: set the cap field via `Settings(...)` / runner env, assert NO refresh (doc rows unchanged) + warning names the count.

### `tests/unit/search/test_staleness.py` (NEW — test)

**Analog:** `tests/unit/search/test_context_attach.py` — real-SQL fixture + result factory + searcher-delegation proof.

**Fixture + factory** (test_context_attach.py:47-54, 72-83):
```python
@pytest.fixture
def db():
    """Real in-memory SQLite with the production contexts table DDL."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    SchemaManager(conn)._create_contexts_table()
    yield conn
    conn.close()


def _result(path: str, description: str | None = None) -> SearchResult:
    result = SearchResult(
        document_id="d1", title="T", path=path, collection_name="c",
        score=1.0, rank=1,
    )
    ...
```
Staleness version: fixture creates the vec0 `document_embeddings` table (needs sqlite-vec or raw `CREATE VIRTUAL TABLE` stub — vec0-missing case is a plain connection without it). Cover: embedded → unmarked; never-embedded / BM25-refreshed → marked; empty results → no query (mirror test_context_attach.py:236-240 `mock_db.execute.assert_not_called()`); delegation wiring per searcher (mirror :148-186).

### `tests/unit/cli/test_search.py` (MOD — test)

**Analog:** itself — two scaffolds to copy.

**Mock scaffold for search_cmd** (test_search.py:246-306) — patch at module boundary, assert on `result.output`:
```python
mock_repo = MagicMock()
mock_repo.list_enabled.return_value = []
mock_searcher = MagicMock()
mock_searcher.search.return_value = [self._make_search_result()]
mock_db = MagicMock()
with (
    patch("sif.cli.commands.search.Database", return_value=mock_db),
    patch("sif.cli.commands.search.CollectionRepository", return_value=mock_repo),
    patch("sif.cli.commands.search.BM25Searcher", return_value=mock_searcher),
):
    result = runner.invoke(
        search_cmd,
        ["query", "--line-numbers", "--json"],
        obj={"index_path": MagicMock(exists=lambda: True)},
    )
assert result.exit_code == 0
assert '"line_numbers": "1\\n2"' in result.output
```
**Pipeline scaffold for query_cmd** (test_search.py:831-874) — `TestSnippetDisplay._invoke_query` patches Database + CollectionRepository + SearchPipeline + EmbeddingManager.from_settings + get_settings in one helper; reuse it for the staleness format battery (JSON key assert, CSV column, MD/XML annotation).

### `tests/unit/cli/test_status.py` (MOD — test)

**Analog:** itself — `TestWatchSection._invoke` (test_status.py:111-123) mocks Database + the probe source, then asserts row text in `result.output` (`assert "Watch" in output; assert "PID 4242" in output`). Vector-lag tests: same scaffold, patch the lag-probe source or seed real stats; degraded case asserts `"n/a"` renders.

### `tests/unit/cli/test_index_locking.py` (MOD — test)

**Analog:** itself — the two coexistence proofs the refresh burst joins.

**Lock spy** (test_index_locking.py:107-127) — recording wrapper proving exactly-one entry; drift tests assert ZERO entries when clean (SC2) and one when refreshing:
```python
def _recording_lock(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    import sif.cli.commands.index as index_mod
    real_lock = index_mod.index_lock
    events: list[str] = []

    @contextmanager
    def recording_lock(db_path, timeout_s, on_wait=None):
        events.append("acquire")
        with real_lock(db_path, timeout_s, on_wait=on_wait):
            events.append("enter")
            yield
        events.append("release")

    monkeypatch.setattr(index_mod, "index_lock", recording_lock)
    return events
```
**Parent-holds-lock** (test_index_locking.py:174-211) — the test process opens the derived `{db}.lock` path itself (`resolved.with_name(resolved.name + ".lock")`, `fcntl.flock(fd, LOCK_EX | LOCK_NB)`), sets `lock_wait_timeout=0.2`, asserts the loser waits then completes (D-02). Also note the `isolated_settings` autouse fixture clearing `get_settings.cache_clear()` (:38-43) — required for any test that varies the new settings.

### `tests/unit/indexing/test_incremental.py` (MOD — test)

**Analog:** itself — `test_modified_file_purges_stale_chunks_and_persists_fresh_checksum` (:137+) is the exact template for the D-08 invariant regression (BM25-only update leaves the doc embeddings-free — the property the derived signal rests on). Fresh-connection readers `_doc_row`/`_chunk_contents` (:79-104) show how to assert DB state post-close.

### `tests/unit/mcp/test_backend.py` (MOD — test)

**Analog:** itself — `test_hybrid_search_mocks` (:63-83) patches `sif.mcp.backend.SearchPipeline`, invokes `backend.hybrid_search`, asserts the mapping; extend to assert `metadata["vectors_stale"]` (or the chosen forwarding key) is carried.

## Shared Patterns

### Flock-wrapped write bursts — lock ONLY when there is work
**Source:** `src/sif/database/locking.py:42-98` (`index_lock`, wait-then-run loser semantics); consumed at `watcher.py:741,763` and `index.py:53-60`.
**Apply to:** drift refresh burst. Order is the contract: read-only walk → count → only if `0 < count <= cap` acquire the lock (clean search never creates `{db}.lock` — `os.open(..., O_CREAT)` runs on entry, locking.py:70). Deadline expiry is not an error (D-02 loser runs anyway).

### Presentation-free core + host renders
**Source:** `incremental.py:10-12, 249-253` (`progress` callback protocol: `"scan <n>"`, `"unchanged <name>"`, `"missing <name>"`...).
**Apply to:** `drift.py` and `staleness.py` — no Console/click imports in `src/sif/indexing/` or `src/sif/search/`; all D-07/D-13 stderr notices live in `cli/commands/search.py`.

### Batched enrichment, never N+1
**Source:** `context_attach.py:53-56` (one constant SQL, Python-side match); `vector.py:221-228` (vec0 has NO metadata index — per-doc filtered lookups are full scans).
**Apply to:** staleness SQL (one `SELECT document_id FROM document_embeddings` scan → set membership) and any status vector-lag count.

### Degrade-never-crash on optional metadata
**Source:** `main.py:165-173` (Watch probe try/except → "not running"); `schema.py:315-323` (vec0 table conditional); `vector.py` OperationalError handling.
**Apply to:** staleness marker when vec0 missing (no markers, not an error); status Vector-lag row ("n/a").

### Stderr contract for pipes
**Source:** `src/sif/cli/commands/mcp.py:12` (`console_err = Console(stderr=True)`); module-level `console = Console()` writes to stdout (search.py:26 — the trap).
**Apply to:** under-cap refresh notice, over-cap warning, stale-results remedy hint. `-q`/`set_quiet` gates them; stdout stays clean for `--json`/`--csv` (the `sif-search`/`sif-get` skills consume `sif -q search ... --json`).

### Error handling conventions
**Source:** CLAUDE.md + `search.py:604-606` (`raise click.ClickException(str(e)) from e`); `incremental.py:281` (`with self._conn:` per-file short transactions).
**Apply to:** drift refresh failures must never make search an error (D-05 spirit: drift is surfaced, search proceeds).

### Settings → generated docs pairing
**Source:** `settings.py:43-85` (watch_* fields) + `generate_config_ref.py:150-190` (SECTIONS allowlist) + `tests/test_docs.py` drift gate.
**Apply to:** both new `SIF_` fields registered in the same change; `make docs-generate` only, never hand-edit docs.

### Deterministic test culture (11-D08/D-09, 12-D15)
**Source:** `test_incremental.py:70-104` (fresh-connection assertions), `test_index_locking.py:174-211` (parent holds lock, deadline lower-bound only), `os.utime` for exact mtimes (float round-trip is bit-exact — RESEARCH Pitfall 2).
**Apply to:** all five test files. No naked sleep-polling, no latency asserts for SC2 (assert zero writes: lock file absent, DB unchanged).

## No Analog Found

None — every file in this phase has a direct in-repo analog (this is an integration phase over Phase 11-13 machinery). The genuinely new logic (mtime compare loop, cap decision) follows the sketched shapes in `14-RESEARCH.md` Patterns 1-2, which themselves are composites of the analogs above.

## Metadata

**Analog search scope:** `src/sif/{indexing,search,core,database,cli,mcp,config}/`, `scripts/`, `tests/unit/{indexing,search,cli,mcp}/`; project skills `.claude/skills/sif-{get,search}/SKILL.md` (read for the stdout-cleanliness consumer contract)
**Files scanned:** 20 source/test files read (all analog excerpts above verified by direct read this session; every named path confirmed via `git ls-files`)
**Pattern extraction date:** 2026-11-08
