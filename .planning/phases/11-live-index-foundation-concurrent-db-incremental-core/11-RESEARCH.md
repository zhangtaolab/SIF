# Phase 11: Live-Index Foundation (Concurrent DB + Incremental Core) - Research

**Researched:** 2026-11-07
**Domain:** SQLite multi-process concurrency (WAL/busy_timeout/BEGIN IMMEDIATE), kernel flock single-writer arbitration, incremental-indexing loop extraction in Python 3.10+ stdlib
**Confidence:** HIGH (concurrency mechanics verified by local probes on Python 3.11/3.12/3.13 + official docs; codebase touchpoints read directly; zero new dependencies)

## Summary

Phase 11 is a configuration-and-refactor phase, not a library phase: every mechanism it needs is Python stdlib (`sqlite3`, `fcntl`) plus the existing `sqlite-vec` dependency. The two decisions that determine whether the phase lands cleanly are both about *where* the concurrency knobs live: (1) `BEGIN IMMEDIATE` should be implemented as `sqlite3.connect(..., isolation_level="IMMEDIATE")` inside the one shared connection factory — this preserves every existing `with conn:` block and `Database.transaction()` context manager verbatim (verified by probe: commit/rollback semantics survive unchanged), and it makes read-only paths (MCP searches) never acquire the write lock because implicit transactions open only before DML statements. The alternative — `isolation_level=None` + explicit `BEGIN IMMEDIATE` strings — would silently defuse every existing `with conn:` block (the context manager "does nothing" when no transaction is open) and force a rewrite of all 26+ write sites. (2) The deferred-transaction read→write upgrade failure is real and verified: a deferred transaction that reads, then tries to write after another writer committed, fails with `database is locked` in 0.00s **despite busy_timeout=5000** — this is the concrete, reproducible justification for IMMEDIATE, and `BEGIN IMMEDIATE` demonstrably waits out busy_timeout instead (verified: waited 3.27s, then raised only when the lock was still held).

The flock arbitration mechanics are verified end-to-end locally: `fcntl.flock(fd, LOCK_EX | LOCK_NB)` raises `BlockingIOError` (errno `EAGAIN`/`EACCES`) when held, a try-loop with deadline acquires ~0.5s after the holder releases, and the kernel releases the lock immediately when the holder is SIGKILLed (probe output: child `ACQUIRED` right after holder kill). `fcntl` is Unix-only (`Availability: Unix` in the Python docs); SIF has zero Windows support signals (no OS classifiers, no CI test matrix, no platform guards in `src/` — verified by grep), so the recommended Windows posture is graceful degradation (skip arbitration, warn in debug log; WAL + busy_timeout still protects integrity), not a new dependency. One verified wrinkle the milestone research only sketched: `PRAGMA journal_mode=WAL` executed while another connection holds a write transaction raises `OperationalError("database is locked")` **immediately** — busy_timeout is NOT honored for the WAL switch (verified: raised at 0.00s with busy_timeout=1000 set; retry after release succeeds) — which is precisely why the factory's pragma block needs the bounded first-open retry.

The extraction surface is now precisely mapped: `update_cmd` currently runs **one giant implicit transaction around all collections and all files** (`with db.connection:` at `src/sif/cli/commands/index.py:55` wraps everything), so moving to per-file BEGIN IMMEDIATE transactions changes failure semantics from all-or-nothing to resumable-per-file — exactly what D-04 locks in — while final index state stays identical (SC3). The dead code to retire is larger than one class: `tests/unit/indexing/test_indexer.py` (~660 lines) tests the dead `DocumentIndexer` and is deleted with it; `TestConnectionPool` in `tests/unit/db/test_database.py` is deleted with `ConnectionPool`.

**Primary recommendation:** Build one `create_connection()` factory (pragma block + sqlite-vec load + bounded WAL-switch retry + `isolation_level="IMMEDIATE"`) used by both `Database` and `DatabaseConnection`; extract `IncrementalIndexer` whose per-file body runs in `with conn:` transactions; implement flock as a small context manager (`LOCK_EX|LOCK_NB` try-loop with configurable deadline, `{db_path}.lock` created 0600, POSIX-only with degrade-and-warn elsewhere); prove SC1/SC2 with in-suite multi-connection tests against `tmp_path` file DBs plus 2-3 deterministic subprocess tests that never race — the parent holds/releases the lock and asserts the child's outcome.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
Copied verbatim from `.planning/phases/11-live-index-foundation-concurrent-db-incremental-core/11-CONTEXT.md` `<decisions>`:

**Arbitration semantics (flock)**
- **D-01:** Lock coverage = all long-running write jobs: `IncrementalIndexer` invocations (`update_cmd` + MCP index tool) and `embed_cmd`. Short CRUD writers (collection add/remove, context writes) stay OUTSIDE the lock — `busy_timeout` + `BEGIN IMMEDIATE` handles them. Rationale: `embed_cmd` holds the DB write lock for an entire collection (locked Phase 03 decision); without arbitration a concurrent update BUSY-fails after 5s. Matches LIVE-07's "no duplicate embed" spirit.
- **D-02:** Loser behavior = **wait then run**. A writer that finds the lock held waits up to a configurable timeout (suggested default ~30s) for the winner to finish, then runs its own pass. Never silently drops distinct work (`update -c B` while A runs must eventually index B). — **Reversibility:** costly — Phases 12–14 watch hosts (daemon, MCP-embedded, pre-command) all build on this collision contract; changing it later reworks all three hosts.
- **D-03:** Lock granularity = **one global lock per database** (lock file next to the DB, e.g. `sif.db.lock`, created `0600`). NOT per-collection locks — the Phase 12–14 daemon story needs one "is a watcher running?" answer; different-collection updates simply queue behind the wait-then-run semantics.

**Write granularity (IncrementalIndexer transactions)**
- **D-04:** `IncrementalIndexer` commits **per file** — each file's document + chunks + FTS writes are one short `BEGIN IMMEDIATE` transaction. Successful runs produce an identical index to today (SC3); only failure semantics change: a mid-run crash keeps completed files (resumable) instead of rolling back the whole run. Short lock holds are the point — searches and other writers interleave.
- **D-05:** `embed_cmd`'s per-collection transaction structure is **left untouched** in this phase. The flock decision (D-01) already absorbs its concurrency pain; Phase 03's CR-02 per-collection atomicity stays locked. Phase 12's watch `--embed` depth gets per-file behavior naturally through `IncrementalIndexer` when it lands.

**Connection consolidation**
- **D-06:** **Unify to one shared connection factory** — pragma block + sqlite-vec load + bounded first-open retry (research recipe: read→write lock upgrades return `SQLITE_BUSY` immediately, so the WAL switch itself needs the retry) live in exactly one place. `Database` (CLI path) and `DatabaseConnection` (MCP path, `src/sif/mcp/backend.py:68`) both route through it. No connection site can forget the pragmas.
- **D-07:** **Retire dead connection code**: `ConnectionPool` (`src/sif/database/connection.py:105`, zero real callers, loads neither sqlite-vec nor pragmas) and the duplicate legacy `DatabaseConnection` (`src/sif/database/database.py:108`) are deleted, alongside dead `DocumentIndexer`. — **Reversibility:** costly — both are re-exported from `src/sif/database/__init__.py`, i.e. published package API; reversal is a git revert but any external importer of `sif.database.ConnectionPool` breaks in between.

**Concurrency test depth**
- **D-08:** SC1/SC2 proof uses **both layers**: (a) in-suite tests with multiple real sqlite3 connections/threads against a real file DB in `tmp_path` — WAL interplay, pragma order, `BEGIN IMMEDIATE`, flock wait-then-run — broad, fast, coverage-counting; (b) 2–3 subprocess-level tests for the literal SC2 proof (two real `sif index update` processes racing; exactly one defers). Deterministic by construction: the parent holds/releases the lock and asserts the child's outcome.
- **D-09:** Subprocess concurrency tests run **in the default pytest invocation** (keeping `fail_under=90` honest about them), serialized (no xdist overlap), with generous timeouts (30s+ vs expected <5s), never sleep-polling without a deadline.

**Carried forward (pre-decided in research/roadmap — do not re-litigate)**
- Pragma order and values: `busy_timeout=5000` FIRST, then `journal_mode=WAL` (persistent, set once per DB), then `synchronous=NORMAL`; `wal_checkpoint(TRUNCATE)` at daemon shutdown; network-FS WAL-fallback detection (pragma returns old mode → degrade + warn). Source: `.planning/research/STACK.md` "Key Integration Points" #1 and "Stack Patterns by Variant".
- `BEGIN IMMEDIATE` for write transactions (LIVE-06); vec0/embedding writes always inside explicit transactions.
- flock (kernel) — not PID-file-only, not a custom lockfile scheme (REQUIREMENTS.md Out of Scope).
- Zero new runtime dependencies.

### Claude's Discretion
- Lock file exact name/path derivation (next to DB, `0600`, per research security note)
- Wait-timeout default value and its `SIF_` settings field name (~30s suggested)
- Connection factory module placement and internal API shape
- `IncrementalIndexer` class/API shape (constructor deps, return type carrying added/updated/removed counts so CLI output stays identical)
- Subprocess test implementation details (env, invocation) as long as deterministic + serialized
- Bounded first-open/DDL retry bounds (research: "a handful of attempts, small backoff")
- CLI notice wording while waiting for the lock; winner/loser exit codes (both 0 on success)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.

Also out of scope per the phase boundary: watch event handling/debounce (Phase 12), MCP-embedded refresh and daemon incl. `wal_checkpoint(TRUNCATE)` at shutdown (Phase 13), pre-command staleness detection (Phase 14), any embed_cmd transaction restructuring (D-05), search-quality work (15–16).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LIVE-06 | watch 写入与 CLI/MCP 并发读共存，零 "database is locked"（WAL + busy_timeout + BEGIN IMMEDIATE） | Shared-factory recipe with verified pragma ordering; `isolation_level="IMMEDIATE"` mechanism verified (preserves `with conn:` blocks; read-only paths never lock); WAL-switch BUSY-not-honoring-timeout verified → bounded retry design; WAL reader-during-writer verified OK; per-file transaction boundaries confirmed safe against FTS external-content triggers and vec0 deletes |
| LIVE-07 | flock 单写者仲裁，多 watch 形态并存不重复 embed | fcntl.flock try-lock/wait/death-release semantics verified by probe; lock-file design (0600, per-DB) from locked D-03; wait-then-run loop verified (~0.5s acquire after release); Windows degradation posture researched; loser-pass dedup via existing checksum-skip idempotency confirmed in `update_cmd` |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Connection creation + pragmas (busy_timeout/WAL/synchronous) | Infra layer — `sif/database/` shared factory | — | Every connection CLI/MCP opens needs identical setup; one factory is the only way no site forgets it (D-06) |
| Write serialization (BEGIN IMMEDIATE) | Infra layer — factory `isolation_level` + existing `with conn:` blocks | — | Lock acquisition belongs to the connection/transaction machinery, not to callers |
| Single-writer arbitration (flock) | Application layer — lock utility used by `update_cmd`/`embed_cmd` entry points | Infra (`sif/utils/` or `sif/database/`) for the mechanism | The mechanism is generic; the *policy* (which commands lock) lives in CLI commands (D-01) |
| Per-file incremental indexing | Application layer — `IncrementalIndexer` (`sif/indexing/`) | Repositories for persistence | Orchestration (scan → checksum diff → parse → write) is application logic; persistence stays in repositories |
| CLI presentation (progress, counts, lock-wait notice) | Presentation — `cli/commands/index.py` | — | `update_cmd` delegates and renders; core returns counts (SC3 CLI output identical) |
| MCP DB access | Application — `SearchBackend._run_in_db` via `DatabaseConnection` | Factory underneath | Backend opens fresh connection per tool transaction; inherits pragmas via factory (D-06) |
| SC1/SC2 proof | Test layer — in-suite + subprocess tests | — | Verification only; no production code |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `sqlite3` (stdlib) | Python 3.10+ bundled (SQLite ≥3.31 typical; any ≥3.7 has WAL) | WAL mode, busy_timeout, `isolation_level="IMMEDIATE"` | The entire LIVE-06 hardening is stdlib configuration; no dependency change [VERIFIED: local probes on SQLite 3.50.4/3.51.0/3.53.1] |
| `fcntl` (stdlib) | Python 3.10+ | `flock` single-writer arbitration | Kernel lock: no stale locks possible (released on process death — verified by SIGKILL probe); Unix-only, matches SIF's supported surface [VERIFIED: local probe; CITED: docs.python.org/3/library/fcntl.html] |
| `sqlite-vec` (existing dep) | 0.1.9 (pyproject floor, installed in .venv) | vec0 virtual tables; loaded inside the factory | Already a runtime dependency; WAL compatibility pre-verified by milestone research [VERIFIED: .venv `pip show sqlite-vec 0.1.9`] |
| `pytest` + `pytest-cov` (existing dev deps) | pytest 9.0.3, pytest-cov 7.1.0, coverage 7.13.5 in .venv | Concurrency tests in the default run, `fail_under=90` gate | Existing suite; no additions [VERIFIED: .venv `pip show`] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `subprocess` (stdlib) | — | SC2 two-writer subprocess tests | `[sys.executable, "-m", "sif.cli.main", ...]` — `main.py:215` has the `if __name__ == "__main__":` guard [VERIFIED: src/sif/cli/main.py:202-216] |
| `threading` (stdlib) | — | In-suite multi-connection concurrency tests | Threads each holding their own connection against a `tmp_path` file DB |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `isolation_level="IMMEDIATE"` (implicit BEGIN IMMEDIATE) | `isolation_level=None` + explicit `conn.execute("BEGIN IMMEDIATE")` | Explicit mode is the "modern autocommit" direction (3.12 `autocommit` API) but silently defuses every existing `with conn:` block ("the context manager does nothing" without an open transaction — docs quote below) and requires rewriting every write site now. Implicit IMMEDIATE achieves the same lock behavior with zero call-site changes. Revisit if the codebase ever migrates to `autocommit` |
| `fcntl.flock` | `msvcrt.locking` (Windows) / `portalocker` | `msvcrt` byte-range locks are per-fd with different death semantics and are untestable here (no Windows); `portalocker` violates zero-new-deps. Degrade-and-warn on non-POSIX instead |
| Wait-loop try-lock with deadline | Blocking `flock(fd, LOCK_EX)` in a thread | Blocking flock has no timeout — an embedded writer would hang forever; the try-loop honors D-02's configurable deadline and lets the CLI print a waiting notice |

**Installation:** None. Zero new runtime dependencies (locked decision). Stdlib only.

**Version verification:** No new packages to verify. Existing environment confirmed: `.venv` Python 3.13.9, sqlite-vec 0.1.9, pytest 9.0.3, pytest-cov 7.1.0, coverage 7.13.5, `sif` console script 1.0.1 working.

## Package Legitimacy Audit

**No external packages are installed by this phase.** All mechanisms are Python stdlib (`sqlite3`, `fcntl`, `subprocess`, `threading`) plus the already-declared `sqlite-vec` runtime dependency. The legitimacy gate has nothing to assess; no `[SUS]`/`[SLOP]` candidates exist. Per the locked decision "Zero new runtime dependencies", any plan task that proposes a new package violates the phase contract.

## Architecture Patterns

### System Architecture Diagram

```
                     ┌────────────────────────────────────────────────┐
                     │            create_connection(db_path)          │
                     │        (ONE shared factory, D-06)              │
                     │  1. sqlite3.connect(timeout=5.0,               │
                     │       isolation_level="IMMEDIATE", ...)        │
                     │  2. PRAGMA foreign_keys=ON                     │
                     │  3. PRAGMA busy_timeout=5000   ← FIRST         │
                     │  4. PRAGMA journal_mode=WAL     ← bounded retry│
                     │     (raises immediately under contention —     │
                     │      verified; check row == 'wal' else degrade)│
                     │  5. PRAGMA synchronous=NORMAL                  │
                     │  6. sqlite_vec.load(conn)                      │
                     └──────────┬─────────────────────┬───────────────┘
                                │                     │
              ┌─────────────────▼──────┐   ┌──────────▼──────────────┐
              │  Database (CLI path)   │   │ DatabaseConnection      │
              │  cached conn property  │   │ (MCP path; per-op conn  │
              │  transaction() ctx mgr │   │ via backend.py:68)      │
              └───────────┬────────────┘   └──────────┬──────────────┘
                          │ 26 `with Database(...)` CLI sites        │
                          │                           │
        ┌─────────────────▼──────────────┐            │ MCP searches (read-only:
        │  flock: {db_path}.lock (0600)  │            │  no implicit txn → no
        │  LOCK_EX|LOCK_NB try-loop,     │            │  write lock taken)
        │  deadline = SIF_ setting (~30s)│            │
        └───────┬──────────────┬─────────┘            │
                │ winner       │ loser: wait ≤ deadline, then own pass
                ▼              ▼                      ▼
      ┌─────────────────────────────┐        ┌────────────────┐
      │ IncrementalIndexer (NEW)    │        │ embed_cmd      │
      │ per file: `with conn:` =    │        │ (structure     │
      │  BEGIN IMMEDIATE → doc +    │        │  untouched,    │
      │  chunks + FTS triggers →    │        │  gains flock   │
      │  COMMIT                     │        │  acquisition)  │
      │ update_cmd delegates to it  │        └────────────────┘
      └─────────────────────────────┘
                │
                ▼  interleaves safely (WAL: readers never block writer)
      ┌────────────────┐   ┌─────────────┐
      │ CLI searches   │   │ MCP queries │
      └────────────────┘   └─────────────┘
```

Trace the SC1 path: background IncrementalIndexer holds short BEGIN IMMEDIATE write transactions per file → concurrent CLI/MCP readers on WAL connections read without blocking and never raise "database is locked" (busy_timeout absorbs any brief writer-writer collision). Trace the SC2 path: two `sif index update` processes → both open `{db_path}.lock` → exactly one `flock` succeeds → loser enters the wait loop → on winner completion (or deadline) loser runs its own pass, which checksum-skips to a no-op for identical work.

### Recommended Project Structure
```
src/sif/database/
├── factory.py        # NEW: create_connection() — pragma block + vec load + bounded
│                     #      WAL-switch retry + isolation_level="IMMEDIATE"
├── database.py       # Database.connection routes through factory; legacy duplicate
│                     #   DatabaseConnection (line ~108) DELETED
├── connection.py     # DatabaseConnection._create_connection delegates to factory;
│                     #   ConnectionPool DELETED
├── locking.py        # NEW (or utils/): index_lock() context manager — flock try-loop
└── __init__.py       # exports updated: ConnectionPool removed, duplicate
                      #   DatabaseConnection import removed
src/sif/indexing/
├── incremental.py    # NEW: IncrementalIndexer — per-file loop extracted from update_cmd
├── indexer.py        # DocumentIndexer DELETED (with IndexStatus/IndexResult if unused elsewhere)
└── watcher.py        # TYPE_CHECKING refs repointed: DocumentIndexer → IncrementalIndexer
```

### Pattern 1: BEGIN IMMEDIATE via isolation_level on the connection
**What:** Set `isolation_level="IMMEDIATE"` at connect time so every implicit write transaction starts with `BEGIN IMMEDIATE`.
**When to use:** In the one shared factory — nowhere else.
**Why this shape:** All existing call sites keep working verbatim. Verified on Python 3.11/3.12/3.13: `with conn:` commits on success and rolls back on exception under `isolation_level="IMMEDIATE"` exactly as under the default `""`/DEFERRED; a second writer against an open IMMEDIATE transaction waits out busy_timeout then raises (`database is locked` after 0.26s with busy_timeout=0.2s). Docs: implicit transactions open only "if *sql* is an `INSERT`, `UPDATE`, `DELETE`, or `REPLACE` statement" — so read-only paths (every MCP `_run_in_db` search) never open a transaction and never take the write lock. [VERIFIED: local probe + CITED: docs.python.org/3/library/sqlite3.html]

```python
# Source: probe-verified pattern (Python 3.11/3.12/3.13, SQLite 3.50-3.53)
conn = sqlite3.connect(
    str(db_path),
    timeout=5.0,                        # busy handler while connecting (docs: default 5.0)
    isolation_level="IMMEDIATE",        # implicit BEGIN becomes BEGIN IMMEDIATE
    detect_types=sqlite3.PARSE_DECLTYPES,
    check_same_thread=False,
)
conn.execute("PRAGMA foreign_keys = ON")
conn.execute("PRAGMA busy_timeout = 5000")   # authoritative; overrides timeout= (last set wins)
mode = _switch_wal_with_retry(conn)          # bounded retry; returns resulting mode row
conn.execute("PRAGMA synchronous = NORMAL")
conn.row_factory = sqlite3.Row
```

### Pattern 2: The WAL switch needs its own bounded retry
**What:** Wrap only the `journal_mode=WAL` pragma in a small retry loop (e.g. 3-4 attempts, 100-250ms backoff), and verify the returned row.
**Why (verified):** With another connection holding a write transaction, `PRAGMA journal_mode=WAL` raised `OperationalError: database is locked` **immediately (0.00s) despite busy_timeout=1000** — the busy handler is not honored for this lock upgrade; the retry after release returned `('wal',)`. On success the pragma returns `('wal',)` and the mode persists in the DB header — a fresh connection on the same file reads `wal` without re-setting it, so the retry cost is paid at most on the true first open (or after an external mode reset). [VERIFIED: local probes 5a/5b/2a-2c]
**Also check the returned mode:** on filesystems that cannot support WAL (network FS), the pragma can return the *old* mode instead of raising — if the row is not `'wal'`, degrade + warn (locked network-FS fallback decision). [CITED: .planning/research/STACK.md §Stack Patterns by Variant]
**synchronous:** WAL's default remains `2` (FULL) — probe 2d read `(2,)` after switching — so `PRAGMA synchronous=NORMAL` must be set explicitly on every connection (it is per-connection, unlike journal_mode). [VERIFIED: local probe 2d]

### Pattern 3: flock single-writer as a context manager
**What:** One lock file per DB (`{db_path}.lock`), created `0600`; `LOCK_EX | LOCK_NB` try-loop with deadline; held for the whole write job.
**Verified semantics:** held lock → `BlockingIOError` errno `EAGAIN`(35)/`EACCES`; holder release → waiter acquires (~0.5s with a 50ms poll loop); holder SIGKILL → lock released by kernel, next try-lock `ACQUIRED` immediately; the deadline is honored (TIMEOUT observed at exactly 5.02s). Docs: "Availability: Unix, not WASI"; on `LOCK_NB` failure "an `OSError` will be raised and the exception will have an *errno* attribute set to `EACCES` or `EAGAIN`". flock locks are per-open-file-description — keep the fd open for the lock's lifetime; close (or `LOCK_UN`) releases. [VERIFIED: local probes; CITED: docs.python.org/3/library/fcntl.html]

```python
# Source: probe-verified pattern (fcntl, Python 3.11-3.13 on macOS)
import fcntl, os, time

def acquire_index_lock(lock_path: Path, timeout_s: float) -> int | None:
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    deadline = time.monotonic() + timeout_s
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd                      # winner
        except BlockingIOError:
            if time.monotonic() >= deadline:
                os.close(fd)
                return None                # timed out (caller decides: run anyway per D-02)
            time.sleep(0.05)
```
D-02 nuance: timeout expiry is NOT an error — the loser *then runs its own pass* (never drops distinct work). For identical work the checksum-skip makes the loser's pass a no-op, which is what makes "no duplicated indexing or embedding" (SC2) true even though both processes complete. The wait deadline only bounds how long the CLI will *pause with a notice* before proceeding.

### Pattern 4: IncrementalIndexer per-file transactions
**What:** Move the loop body of `update_cmd` (parse → checksum diff → chunk purge → doc create/update) into `IncrementalIndexer`; each file's writes run inside one short `with conn:` block (= BEGIN IMMEDIATE → COMMIT under the factory). The removed-file sweep and the per-collection stats update become their own short transactions.
**Why the boundaries are safe (verified against source):**
- FTS sync is trigger-based on the *content tables*: `AFTER INSERT/UPDATE/DELETE ON documents` / `ON document_chunks` triggers using the documented external-content `'delete'` command form — the per-file transaction writes `documents`/`document_chunks` rows; the triggers fire inside the same transaction, so FTS state advances atomically with each file commit. [VERIFIED: src/sif/database/schema.py:239-289 — e.g. the update trigger reads `INSERT INTO documents_fts(documents_fts, rowid, content) VALUES('delete', old.rowid, old.content); INSERT INTO documents_fts(rowid, content) VALUES(new.rowid, new.content);`]
- vec0 interaction on the update path is delete-only: `update_cmd` purges stale embeddings via `VectorSearcher.delete_embeddings_by_document` (a parameterized `DELETE FROM document_embeddings WHERE document_id = ?`) before rewriting the doc — a DML statement inside the same per-file transaction, consistent with the locked "vec0 writes always inside explicit transactions" rule. `update_cmd` never inserts embeddings (BM25-only). [VERIFIED: src/sif/cli/commands/index.py:161-163,198-200; src/sif/search/vector.py:195-204]
- Semantics change (blessed by D-04): today everything runs in ONE implicit deferred transaction — the `with db.connection:` at index.py:55 wraps *all collections and all files* — so a mid-run crash currently rolls back everything; per-file commits make completed files durable/resumable. Final state is identical (SC3).
- `existing_docs` snapshot is read once per collection before the loop; with per-file commits a concurrent short CRUD writer could in principle make it stale mid-collection — but flock arbitration means only one *index writer* at a time, so this exposure is no worse than today. Accepted; document it in the plan.

### Pattern 5: SC3-safe delegation (CLI output identical)
**What:** `IncrementalIndexer` returns a counts result (added/updated/removed); `update_cmd` prints the same `Added:/Updated:/Removed:` lines it prints today (index.py:210-213). Keep Rich `Progress` *out* of the core — pass a progress callback from the CLI so MCP/watch hosts (Phases 12-13) reuse the core without Rich. The `noqa: C901, PLR0912, PLR0915` on `update_cmd` (index.py:48) should become unnecessary after extraction.

### Anti-Patterns to Avoid
- **`isolation_level=None` + manual BEGIN/COMMIT strings now:** defuses every existing `with conn:` block (docs: "If there is no open transaction upon leaving the body of the `with` statement ... the context manager does nothing") — writes would silently autocommit piecemeal. [CITED: docs.python.org/3/library/sqlite3.html]
- **Setting `journal_mode=WAL` before `busy_timeout`:** the WAL switch does not honor a busy handler for its lock upgrade (verified: immediate raise) — busy_timeout first is still right for everything else, but the retry loop is the actual fix for the switch itself.
- **Blocking `flock()` without LOCK_NB:** no timeout mechanism — a stuck winner hangs every loser forever; D-02 requires a configurable deadline.
- **Asserting exact `-wal`/`-shm` file presence in tests while connections are open:** verified file sets are `['x.db','x.db-shm','x.db-wal']` while open and `['x.db']` only after the last connection closes (auto-checkpoint removes them; data survives; mode persists). Copying only `sif.db` mid-session loses WAL-resident commits. [VERIFIED: local probe]
- **Sleep-poll racing in subprocess tests:** violates D-09; use the parent-holds-lock pattern (below).
- **Holding a write transaction across embedding/model work:** the per-file loop must stay BM25-only (it is today); embed work stays in `embed_cmd`'s per-collection structure (D-05).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Transaction retry/backoff frameworks | Custom busy-retry decorators over every repository call | `busy_timeout` pragma + `BEGIN IMMEDIATE` + flock arbitration | busy_timeout already retries waits inside SQLite (verified: 0.26s/3.27s waits); IMMEDIATE removes the upgrade-BUSY case; flock removes the long-writer case. A retry framework would just re-implement the busy handler |
| Cross-platform file-lock abstraction | Lock library, portalocker wrapper | `fcntl.flock` + degrade-and-warn on non-POSIX | Zero-new-deps is locked; SIF ships no Windows support today (no OS classifiers in pyproject, no CI matrix, no platform guards — verified by grep). msvcrt semantics differ and are untestable here |
| Lock liveness checking (PID files, `os.kill(pid,0)`) | Stale-lock detection/cleanup code | flock kernel semantics | Kernel releases on process death — verified: child acquired immediately after holder SIGKILL. Stale locks are impossible by construction; PID files are explicitly rejected in REQUIREMENTS Out of Scope |
| Subprocess orchestration for races | Timing-based "start two, hope they collide" tests | Parent holds/releases the lock, asserts child outcome | Deterministic by construction (CONTEXT construction detail); timing races are flake generators (D-08/D-09) |

**Key insight:** everything in this phase is already-solved mechanism (SQLite busy handler, kernel flock, sqlite3 implicit transactions). The engineering work is *placement* (one factory) and *boundaries* (per-file transactions), not invention.

## Runtime State Inventory

This phase is a refactor + infrastructure change; the runtime state that changes shape is the database file itself and the published package API.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Existing user DBs are journal-mode DELETE (no WAL pragmas anywhere today — verified: `connection.py:24-37` sets only `foreign_keys`; `database.py:29-52` sets none). First open with the new factory flips the header to WAL — a one-time, persistent, self-upgrading change; no data migration. `-wal`/`-shm` files begin appearing next to user DBs (removed on last close — verified) | None (code change only); document in release notes that DBs auto-convert on first open |
| Live service config | None — no external services store SIF config outside git (SQLite/CLI/MCP app; no n8n/Datadog-class state) | None — verified by architecture (all state in SQLite + Settings) |
| OS-registered state | None today. NEW: `{db_path}.lock` files will appear next to DBs — inert data-less files, kernel-lock-only, safe to delete when no process runs | None (creation is part of the feature); ensure `0600` per security note |
| Secrets/env vars | New `SIF_`-prefixed settings fields (lock wait timeout) are additive; no existing key renames | None — additive Settings fields (env_prefix `SIF_` verified at src/sif/config/settings.py:19-24) |
| Build artifacts / installed packages | `sif.database.ConnectionPool` + duplicate `DatabaseConnection` are published API (re-exported in `src/sif/database/__init__.py:3,16-17` — verbatim: `"ConnectionPool"`, `"DatabaseConnection"` in `__all__`); external importers break on removal (D-07 acknowledges) | Code edit + semver note; no artifact rebuilds |

**Nothing found in category:** "Live service config" and "OS-registered state" — verified by architecture review (local single-user tool; grep found no fcntl/platform/OS registrations anywhere in src/).

## Common Pitfalls

### Pitfall 1: The WAL switch raises immediately under contention — no retry = flaky first open
**What goes wrong:** Two processes hit a fresh/first open simultaneously (or one opens while another's write transaction runs): `PRAGMA journal_mode=WAL` raises `OperationalError: database is locked` at 0.00s even with busy_timeout set — the pragma's lock upgrade does not invoke the busy handler.
**Why it happens:** Verified locally (probe 5a: busy_timeout=1000, raise at 0.00s; 5b: immediate success on retry after release). The mode-switch takes a lock the busy handler cannot wait on.
**How to avoid:** Bounded retry (3-4 attempts, 100-250ms backoff) around the WAL pragma only; then assert the returned row is `('wal',)` and degrade+warn otherwise (network FS). After the first successful switch the mode persists in the DB header (verified: fresh connections read `wal` with no pragma), so the retry cost exists only on true first open.
**Warning signs:** intermittent `database is locked` at *startup* on multi-process tests; tests that create the DB in one process and immediately open it in another.

### Pitfall 2: Choosing explicit-BEGIN mode and silently breaking every `with conn:`
**What goes wrong:** `isolation_level=None` makes `with conn:` a no-op for transactionality; each DML autocommits. Existing multi-statement blocks (e.g. `embed_cmd`'s per-collection block, `Database.transaction()`) lose atomicity *silently* — tests still pass in the happy path.
**Why it happens:** The docs frame None/autocommit as the recommended modern mode, so it looks like the "right" refactor; but the codebase has ~dozens of `with conn:` blocks written for legacy semantics.
**How to avoid:** `isolation_level="IMMEDIATE"` in the factory only. If a future migration to `autocommit` happens, it must rewrite every transactional block in the same change.
**Warning signs:** a plan task that says "switch to autocommit mode"; coverage dropping on rollback-path tests.

### Pitfall 3: deferred read→write upgrade fails instantly despite busy_timeout (the trap IMMEDIATE exists for)
**What goes wrong:** A connection that reads inside a deferred transaction, then writes after another writer committed in between, gets `database is locked` after 0.00s — busy_timeout never engages (verified: probe 4a with busy_timeout=5000).
**Why it happens:** SQLite returns BUSY_SNAPSHOT-class errors immediately on lock upgrade; the busy handler only covers acquiring locks a transaction doesn't already partially hold.
**How to avoid:** All write transactions begin IMMEDIATE (the factory setting does this for every implicit transaction — verified waits: BEGIN IMMEDIATE waited 3.27s under busy_timeout=3000 rather than raising instantly, and absorbs short holders).
**Warning signs:** any code path that opens a transaction, SELECTs, then INSERTs — after this phase that pattern should not exist outside explicit IMMEDIATE.

### Pitfall 4: Subprocess tests that count coverage or race on timing
**What goes wrong:** (a) Expecting subprocess lines to count toward `fail_under=90`: pytest-cov **7.0 removed built-in subprocess support** — without `[tool.coverage.run] patch = ["subprocess"]` (which auto-enables `parallel = true`), subprocess code is unmeasured. Installed dev env is pytest-cov 7.1.0 (verified). (b) Tests that spawn two children and "hope" they overlap → flakes.
**Why it happens:** pytest-cov's old COV_CORE/.pth mechanism is gone (docs: "Subprocess support was removed in pytest-cov 7.0"); race windows are inherently nondeterministic.
**How to avoid:** In-suite tests carry coverage of all shared code paths; subprocess tests assert outcomes only (exit codes, DB row state, lock behavior). Deterministic parent-holds-lock pattern per D-08. If subprocess coverage is ever wanted, it's a config addition (`patch = ["subprocess"]`) with `parallel = true` implications — flag, don't improvise.
**Warning signs:** subprocess tests with `time.sleep` waits for other processes; CI coverage dips when subprocess tests are added.

### Pitfall 5: WAL file lifecycle surprises in tests
**What goes wrong:** Tests that copy/inspect only `sif.db` while a connection is open miss WAL-resident commits; tests that assert the directory contains exactly one file fail while connections are open (`-wal`/`-shm` present); after the last close the files vanish (verified).
**Why it happens:** WAL keeps recent commits in `-wal` until checkpoint; auto-checkpoint on last close removes the files.
**How to avoid:** In tests, close connections (or end subprocesses) before asserting DB contents; assert on query results, not file listings. Note `pytest`'s `tmp_path` cleanup handles the extra files fine.
**Warning signs:** "works when I run it alone, missing rows in the concurrent test".

### Pitfall 6: Retirement blast radius larger than the class
**What goes wrong:** Deleting `DocumentIndexer`/`ConnectionPool` compiles fine but leaves ~660 lines of dead-code tests (`tests/unit/indexing/test_indexer.py` imports `DocumentIndexer, IndexResult, IndexStatus` — verified), `TestConnectionPool` in `tests/unit/db/test_database.py:219-300`, watcher.py string annotations (`"DocumentIndexer"` at watcher.py:31,106 under `TYPE_CHECKING` import at watcher.py:14-15), and `sif.database.__init__` exports.
**Why it happens:** Dead code accretes its own test suites and re-exports.
**How to avoid:** Plan the retirement as one task list: class + its test file + TYPE_CHECKING repoint + `__init__.py` exports + pool tests. Run `ruff` + full suite after.
**Warning signs:** `F401`/`F821` ruff failures; ty errors on the string annotations.

### Pitfall 7: embed_cmd's implicit transaction change
**What goes wrong:** Nothing visible — but the plan should *know* that `embed_cmd`'s `with db.connection:` per-collection blocks (index.py:338, 365) now implicitly BEGIN IMMEDIATE instead of DEFERRED. Commit points are unchanged (same `with` exits), so CR-02 semantics are preserved — this is the factory change flowing through, not a restructure (D-05 respected).
**Why it happens:** isolation_level is a connection-wide property.
**How to avoid:** Accept it (it is strictly better: the collection-embed transaction now takes the write lock upfront and waits via busy_timeout instead of risking the upgrade-BUSY); add one regression test that a failing collection rolls back only its own work (the existing CR-02 tests in tests/integration/test_embed_idempotency.py and unit tests already encode this).
**Warning signs:** embed tests failing on lock behavior would indicate the factory wasn't applied uniformly.

## Code Examples

### Factory (pragma block with WAL retry) — probe-verified mechanics
```python
# Source: local probes (Python 3.11/3.12/3.13) + docs.python.org/3/library/sqlite3.html
def create_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(
        str(db_path),
        timeout=5.0,
        isolation_level="IMMEDIATE",     # implicit BEGIN IMMEDIATE before every DML
        detect_types=sqlite3.PARSE_DECLTYPES,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")   # authoritative over timeout= (verified)
    _set_wal_with_retry(conn, attempts=4, backoff_s=0.15)
    conn.execute("PRAGMA synchronous = NORMAL")  # WAL default is FULL (verified (2,))
    _load_sqlite_vec(conn)                       # best-effort, as today
    return conn

def _set_wal_with_retry(conn, attempts: int, backoff_s: float) -> None:
    for attempt in range(attempts):
        try:
            row = conn.execute("PRAGMA journal_mode=WAL").fetchone()
        except sqlite3.OperationalError:          # verified: raises immediately under contention
            if attempt == attempts - 1:
                raise
            time.sleep(backoff_s)
            continue
        if row and row[0] == "wal":               # success row is ('wal',) — verified
            return
    # row != 'wal' without raising → WAL unsupported (network FS): degrade + warn (locked fallback)
    logger.warning("WAL mode unavailable (journal_mode=%s); using rollback journal", row[0] if row else "?")
```

### In-suite concurrency proof skeleton (SC1)
```python
# Source: probe-verified behaviors; uses tmp_path file DB per D-08
def test_reader_never_blocks_during_writer(tmp_path):
    db = tmp_path / "c.db"
    w = create_connection(db)          # writer
    r = create_connection(db)          # concurrent reader
    w.execute("CREATE TABLE t (x INTEGER)"); w.commit()
    w.execute("INSERT INTO t VALUES (1)")            # open write txn (BEGIN IMMEDIATE implicit)
    rows = r.execute("SELECT COUNT(*) FROM t").fetchone()   # WAL: reads OK during write — verified
    w.rollback()

def test_second_writer_waits_busy_timeout_then_raises_or_succeeds(tmp_path):
    # verified numbers: contention with busy_timeout=200 raised after ~0.26s;
    # BEGIN IMMEDIATE under busy_timeout=3000 waited 3.27s while the lock was held
    ...
```

### Deterministic subprocess two-writer test (SC2) — parent controls the lock
```python
# Source: CONTEXT "Specifics" construction detail + verified flock semantics
def test_second_writer_waits_then_runs(tmp_path, ...):
    lock_path = db_path.with_suffix(".db.lock")     # same derivation as production code
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)  # parent = incumbent writer
    child = subprocess.Popen(
        [sys.executable, "-m", "sif.cli.main", "-q", "index", "update"],
        env={**os.environ, "SIF_DB_PATH": str(db_path), "NO_COLOR": "1"},
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    time.sleep(0.5)                                  # child is now waiting (deterministic: lock held)
    fcntl.flock(fd, fcntl.LOCK_UN); os.close(fd)     # release -> child proceeds
    out, err = child.communicate(timeout=30)         # generous timeout vs <5s expected (D-09)
    assert child.returncode == 0
```
Both-exit-0 is the D-02 contract; "no duplicated work" is asserted from DB state (row counts, single row per path) plus the checksum-skip no-op property, not from timing. `env -u FORCE_COLOR`/`NO_COLOR=1` applies when *running* the suite from agent shells (project memory note).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Rollback journal (DELETE) + busy_timeout=0 (SIF today) | WAL + busy_timeout + synchronous=NORMAL | SQLite WAL since 3.7 (2010); production-standard for local multi-process | Readers stop blocking on the writer; one writer at a time remains |
| Implicit DEFERRED transactions for read-modify-write | BEGIN IMMEDIATE for write transactions | Long-standing SQLite guidance | Eliminates instant-BUSY on lock upgrade (verified 0.00s failure mode) |
| PID-file single-instance checks | Kernel flock | — | Stale locks structurally impossible (verified: released on SIGKILL) |
| pytest-cov built-in subprocess coverage (COV_CORE/.pth) | Removed in pytest-cov 7.0; coverage.py `patch = ["subprocess"]` | pytest-cov 7.0 | Subprocess lines unmeasured by default — plan accordingly |

**Deprecated/outdated:** `isolation_level=None`-style manual transaction management is *not* deprecated, but Python 3.12+ recommends the new `autocommit` attribute; SIF stays on legacy control for 3.10 compatibility — a deliberate, documented choice, not an oversight.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `isolation_level="IMMEDIATE"` semantics identical on Python 3.10 (probes ran 3.11.15/3.12.12/3.13.9; no 3.10 interpreter on this machine; docs describe the behavior as the pre-3.12 legacy mode, and 3.10 predates the 3.12 autocommit addition) | Pattern 1 | Low — mechanism unchanged since 3.6 era; a 3.10 CI run would confirm |
| A2 | Windows posture = degrade-and-warn (skip flock) is acceptable; no Windows users to protect (no OS classifiers, no Windows CI, no platform guards — verified absent) | Pattern 3 | Low-Medium — if Windows is silently used, arbitration is absent there (WAL still protects integrity; only duplicate-work protection is lost) — flag for user confirmation |
| A3 | `embed_cmd` per-collection `with db.connection:` blocks remain correct when the factory makes them BEGIN IMMEDIATE (commit points identical; only lock acquisition timing changes) | Pitfall 7 | Low — CR-02 regression tests exist and will catch violations |
| A4 | Schema DDL first-open races are absorbed by the WAL-switch retry + busy_timeout (the verified hazard is the WAL pragma itself; DDL statements autocommit individually under legacy isolation and are guarded by `IF NOT EXISTS` forms) | Pattern 2 | Low — the SUMMARY-research "DDL race guard" is covered by the same bounded retry if wrapped around the factory's first-open; planner may wrap `init_schema` calls in the same retry for belt-and-braces |
| A5 | Recommended lock-file name `{db_path}.lock` and settings field name (e.g. `SIF_LOCK_WAIT_TIMEOUT`, default ~30s) — Claude's-discretion choices research is recommending, not user-locked | Pattern 3 | None — explicitly discretionary |

## Open Questions

1. **Subprocess coverage measurement** — enable `[tool.coverage.run] patch = ["subprocess"]` (auto-enables `parallel = true`, changes `.coverage*` file handling) or rely on in-suite coverage with subprocess tests as outcome-only proofs?
   - What we know: pytest-cov 7.1.0 installed; subprocess support removed upstream; in-suite tests can cover all shared code paths.
   - What's unclear: whether the team wants subprocess lines counted for the 90% gate.
   - Recommendation: rely on in-suite coverage (config untouched, zero risk); revisit only if the gate gets tight.
2. **Windows arbitration** — degrade-and-warn (recommended) vs implementing `msvcrt.locking`.
   - What we know: no Windows support signals anywhere in the project; zero-new-deps locked.
   - Recommendation: degrade-and-warn behind a `try: import fcntl` guard; revisit if Windows support is ever declared.
3. **Factory behavior when sqlite-vec fails to load** — the two current paths disagree: `Database._enable_extensions` swallows (`except Exception: pass  # sqlite-vec is optional`) while `connection.py:_create_connection` lets it raise; `SchemaManager._create_vector_tables` and `VectorSearcher.__init__` both detect availability lazily.
   - Recommendation: unify on swallow+lazy-detect (matches schema/searcher behavior and keeps BM25-only installs working); planner should encode whichever choice keeps the existing suite green.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python (stdlib sqlite3) | all of Phase 11 | ✓ | .venv 3.13.9; probes also on 3.11.15/3.12.12 | — |
| SQLite library (WAL, busy_timeout) | LIVE-06 | ✓ | 3.50.4 / 3.51.0 / 3.53.1 (probed); WAL needs ≥3.7 | — |
| `fcntl` (POSIX flock) | LIVE-07 | ✓ (macOS) | stdlib | non-POSIX: degrade-and-warn (see A2) |
| sqlite-vec | factory vec load | ✓ | 0.1.9 in .venv | load failure tolerated (existing behavior) |
| `sif` console script / `python -m sif.cli.main` | subprocess tests | ✓ | 1.0.1; `__main__` guard at main.py:215 | `[sys.executable, "-m", "sif.cli.main"]` preferred (venv-independent) |
| pytest / pytest-cov | validation | ✓ | 9.0.3 / 7.1.0 | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none (Windows `fcntl` absence handled by design, not environment).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 (+ pytest-asyncio 1.4.0 for MCP async tests) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — `testpaths = ["tests"]`, `addopts = "--cov=src/sif --cov-report=term-missing --cov-report=html --cov-report=xml"` [VERIFIED: pyproject.toml:203-208] |
| Coverage gate | `[tool.coverage.report] fail_under = 90` (current suite 1015 passed @ 96.20%) [VERIFIED: pyproject.toml:210-211; STATE.md] |
| Quick run command | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/db -x` (subset; FORCE_COLOR quirk per project memory) |
| Full suite command | `env -u FORCE_COLOR NO_COLOR=1 pytest` (no xdist configured → subprocess tests serialize naturally, satisfying D-09's serialization requirement) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LIVE-06 | Every factory-created connection has busy_timeout=5000, journal_mode=wal, synchronous=NORMAL, foreign_keys=on (pragma audit — milestone verification bar) | unit | `pytest tests/unit/database/test_factory.py -x` | ❌ Wave 0 |
| LIVE-06 | Reader (CLI-style and MCP-style `DatabaseConnection`) queries succeed during an open BEGIN IMMEDIATE write transaction, zero "database is locked" | integration (in-suite, real file DB in tmp_path, multi-connection/threads) | `pytest tests/integration/test_concurrency.py -x` | ❌ Wave 0 |
| LIVE-06 | Second writer under contention waits busy_timeout then proceeds (short holder) / raises (long holder) — verified baselines: ~0.26s wait at 200ms timeout | unit/integration | `pytest tests/integration/test_concurrency.py -k busy -x` | ❌ Wave 0 |
| LIVE-06 | WAL switch retries under contention and succeeds; returned-mode check degrades on non-wal result | unit (mock contention via second connection holding write txn) | `pytest tests/unit/database/test_factory.py -k wal -x` | ❌ Wave 0 |
| LIVE-07 | flock: try-lock blocks while held; acquires after release within deadline; times out cleanly at deadline; released on holder death (kill child process) | unit | `pytest tests/unit/database/test_locking.py -x` | ❌ Wave 0 |
| LIVE-07 | `update_cmd` and `embed_cmd` acquire the lock; loser waits then runs its own pass (parent holds/releases; child exit 0) — deterministic subprocess proof | integration (subprocess, default run, 30s timeouts) | `pytest tests/integration/test_two_writer_subprocess.py -x` | ❌ Wave 0 |
| LIVE-07/SC2 | Two `sif index update` on same collection: each file indexed exactly once, no duplicate embedding rows, both exit 0 (assert DB state, not timing) | integration (subprocess) | `pytest tests/integration/test_two_writer_subprocess.py -k duplicate -x` | ❌ Wave 0 |
| SC3 | Index state identical before/after extraction: documents/document_chunks/FTS rows + CLI Added/Updated/Removed output on a fixture tree | integration (golden comparison; extend the existing CliRunner+real-DB pattern in tests/integration/test_embed_idempotency.py) | `pytest tests/integration/test_incremental_equivalence.py -x` | ❌ Wave 0 |
| SC3/D-04 | Per-file commit: mid-run failure keeps completed files, failed file not half-written | unit (fail via mocked repo error on Nth file) | `pytest tests/unit/indexing/test_incremental.py -x` | ❌ Wave 0 |
| SC4 | Full quality suite green | suite | `env -u FORCE_COLOR NO_COLOR=1 pytest && ruff check src tests && ruff format --check src tests && ty check src/sif` | ✅ (existing suite) |
| D-07 | Retirement: `ConnectionPool`/duplicate `DatabaseConnection`/`DocumentIndexer` gone, exports updated, watcher TYPE_CHECKING repointed, dead tests removed | suite-level (ruff F401/F821 + import assertions) | `pytest tests/unit/database/test_exports.py -x` (or fold into factory tests) | ❌ Wave 0 |

Existing tests to keep green/extend: `tests/integration/test_embed_idempotency.py` (CR-02/G-03-3 semantics under the new factory), `tests/unit/cli/test_collection.py` (pre-update-hook tests at lines 427-528 mock `subprocess.run` and `Database` — unaffected by factory), `tests/unit/cli/test_database_lifecycle.py` (WR-01 closure pattern must survive the `Database` refactor), `tests/unit/mcp/test_backend.py` (MCP path through factory).

### Sampling Rate
- **Per task commit:** `env -u FORCE_COLOR NO_COLOR=1 pytest <touched-area> -x` + `ruff check src tests` + `ruff format --check src tests`
- **Per wave merge:** `env -u FORCE_COLOR NO_COLOR=1 pytest` (full, includes subprocess tests) + `ty check src/sif`
- **Phase gate:** full suite green (fail_under=90 honored with the new tests inside the default run, per D-09) before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/database/test_factory.py` — pragma audit + WAL retry (LIVE-06)
- [ ] `tests/unit/database/test_locking.py` — flock semantics incl. holder-death (LIVE-07)
- [ ] `tests/unit/indexing/test_incremental.py` — IncrementalIndexer unit tests incl. per-file failure (SC3/D-04)
- [ ] `tests/integration/test_concurrency.py` — in-suite multi-connection WAL/BUSY proofs (SC1)
- [ ] `tests/integration/test_two_writer_subprocess.py` — deterministic parent-holds-lock subprocess proofs (SC2, D-08/D-09)
- [ ] `tests/integration/test_incremental_equivalence.py` — before/after golden index state (SC3)
- [ ] Deletions: `tests/unit/indexing/test_indexer.py` (dead `DocumentIndexer` suite, ~660 lines), `TestConnectionPool` in `tests/unit/db/test_database.py:219-300`

## Security Domain

`security_enforcement` is absent from `.planning/config.json` workflow — treated as enabled; this phase adds no network surface, no user input parsing, and no cryptography.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Local single-user tool; no auth surface added |
| V3 Session Management | no | No sessions |
| V4 Access Control | no | No privilege boundaries changed |
| V5 Input Validation | no (indirect) | Lock/DB paths derive from Settings paths already normalized by existing validators (settings.py `field_validator("db_path", ...)`); no new user-supplied input paths |
| V6 Cryptography | no | None used |
| V14 Unauthenticated Access (config) | marginal | Lock file created `0600` in the user data dir per milestone security note (prevents another local user spoofing/poisoning the lock file); DB dir already user-scoped |

### Known Threat Patterns for SQLite local multi-process
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Lock-file poisoning (local attacker pre-creates world-writable lock file / symlink) | Tampering/Elevation | Create with `0o600` via `os.open(..., O_CREAT, 0o600)` next to the DB in the user data dir (locked D-03 + milestone Security Mistakes table) |
| DoS via holding flock (local process grabs the lock forever) | Denial | Wait deadline (D-02) bounds the pause; loser proceeds after timeout — availability over strict exclusion; lock holds no data, deleting it is safe when idle |
| WAL sidecar files readable by other local users | Information disclosure | Data dir permissions are the existing boundary (platformdirs user_data_dir); no change — flag only |

## Sources

### Primary (HIGH confidence)
- Local probes (this machine, macOS Darwin 25.6.2): Python 3.11.15/SQLite 3.53.1, 3.12.12/3.50.4, 3.13.9/3.51.0 — isolation_level="IMMEDIATE" + `with conn:` commit/rollback; second-writer busy_timeout waits (0.26s/3.27s); deferred-upgrade instant BUSY (0.00s at busy_timeout=5000); WAL pragma return values/persistence; WAL-switch contention raise at 0.00s + retry success; synchronous default FULL under WAL; connect(timeout=) vs PRAGMA busy_timeout override; -wal/-shm lifecycle incl. last-close cleanup; flock try/wait/deadline/SIGKILL-release
- SIF codebase reads (this session): `src/sif/database/database.py`, `connection.py`, `__init__.py`, `schema.py`, `repositories.py`, `migrations.py`; `src/sif/cli/commands/index.py`; `src/sif/cli/main.py`; `src/sif/indexing/indexer.py`, `watcher.py`; `src/sif/mcp/backend.py`; `src/sif/search/vector.py`; `src/sif/config/settings.py`; `pyproject.toml`; `tests/conftest.py`; tests layout greps
- `.planning/research/STACK.md`, `.planning/research/PITFALLS.md`, `.planning/research/SUMMARY.md` (authoritative milestone research, read not duplicated)

### Secondary (MEDIUM confidence)
- docs.python.org/3/library/sqlite3.html — isolation_level values, implicit-transaction-before-DML rule, `with conn:` semantics, `timeout` param ("How many seconds the connection should wait before raising an OperationalError when a table is locked... Default five seconds.")
- docs.python.org/3/library/fcntl.html — flock LOCK_* semantics, EACCES/EAGAIN, "Availability: Unix, not WASI"
- pytest-cov.readthedocs.io/en/latest/subprocess-support.html — "Subprocess support was removed in pytest-cov 7.0"; `patch = subprocess` migration path

### Tertiary (LOW confidence)
- Network-FS "pragma returns old mode without raising" failure shape — carried from milestone STACK.md (sqlite.org-derived) but not re-verified this session; the factory handles *both* shapes (raise + wrong-mode row), so plan correctness does not depend on which occurs

## Project Constraints (from CLAUDE.md)

Directives the plan and executor must honor (extracted from ./CLAUDE.md):
- Quality gates: `ruff check src tests`, `ruff format --check src tests`, `pytest` (fail_under=90), `ty check src/sif` — run the full suite after every plan completes in the phase.
- Python 3.10+, `list[str] | None` union syntax, line length 100, max complexity 10 (mccabe), ruff isort with `combine-as-imports = true`, two blank lines after imports.
- New code fully type-annotated; CLI modules keep Click decorators as-is.
- CLI commands raise `click.ClickException(str(e))` for user-facing errors; transactions use context managers with rollback on exception.
- Module-level loggers via `get_logger(__name__)` (names prefixed `sif`, output to stderr).
- GSD workflow: planned phase work via `/gsd-execute-phase`; no direct file changes outside it.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib-only, zero deps, versions confirmed in .venv
- Concurrency mechanics (WAL/BUSY/IMMEDIATE/flock): HIGH — locally probed on three Python versions with consistent results, cross-checked against docs.python.org
- Architecture (factory/extraction surface): HIGH — every touchpoint read directly this session with line-verified quotes
- Windows posture: MEDIUM — absence of support signals verified, but the degrade-vs-implement choice is a judgment call flagged as assumption A2

**Research date:** 2026-11-07
**Valid until:** 2027-01-07 (stable stdlib semantics; re-check only if Python floor moves past 3.10 or sqlite-vec major-bumps)
