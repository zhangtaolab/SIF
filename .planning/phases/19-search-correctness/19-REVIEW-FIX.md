---
phase: 19-search-correctness
fixed_at: 2026-11-15T05:16:12Z
review_path: .planning/phases/19-search-correctness/19-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 19: Code Review Fix Report

**Fixed at:** 2026-11-15T05:16:12Z
**Source review:** `.planning/phases/19-search-correctness/19-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (CR-01, CR-02, WR-01, WR-02, IN-04)
- Fixed: 5
- Skipped: 0
- Deferred: 5 (IN-01, IN-02, IN-03, IN-05, IN-06 — out of scope per the dispatch)

All work was done directly in the main checkout: `.planning/config.json` sets
`workflow.use_worktrees: false`, so no isolated worktree was created and the
quality gates below ran against the main working tree (reproducible from it).

## Fixed Issues

### CR-01: FTS title migration is not durable — the rebuild is rolled back while its DDL is committed

**Files modified:** `src/sif/database/schema.py`, `src/sif/mcp/backend.py`,
`tests/unit/database/test_schema_title_fts.py`, `tests/unit/mcp/test_backend.py`
**Commit:** `4546047`
**Applied fix:**
- `SchemaManager._create_fts_tables` now runs the legacy-trigger repair and the
  whole drop/recreate/rebuild sequence under `SAVEPOINT sp_fts_tables` /
  `RELEASE SAVEPOINT`, with `ROLLBACK TO SAVEPOINT` on any exception. Because
  the savepoint starts a real transaction, pysqlite's DDL auto-commit no longer
  separates the two-column `CREATE` from the `('rebuild')`/chunk-seed DML: a
  crash/failure leaves the legacy one-column shape intact (so the detection
  gate re-triggers on the next open), and a success commits the populated
  index before the rest of `create_all` runs. The rollback itself is guarded
  with `contextlib.suppress(sqlite3.Error)` so it can never mask the original
  error.
- `SchemaManager.create_all` commits its writes at the end (the read-only
  command path: `sif status` / `sif index status` open + init + close with no
  command transaction).
- `SearchBackend.__init__` dropped its now-redundant explicit
  `db.connection.commit()` and documents that `init_schema` owns durability,
  so the embedding-dimension `RuntimeError` raised later by
  `_create_vector_tables` cannot roll the rebuild back.
- Regression tests reopen the database on a new connection (`:memory:` cannot
  catch the rollback): close without an explicit commit, the read-only CLI
  boundary path, idempotent re-init with a statement trace, and an injected
  failure between the DDL and the population proving the legacy shape is
  restored so the next open retries. The chunks seed/rebuild (same DML shape)
  is asserted across a reopen too. See IN-04 below for the backend
  dimension-mismatch reopen test added in this same commit.
- Verification: targeted suites green; manual end-to-end probes confirmed a
  `sif status`-shaped open/close and a forced dimension mismatch both leave a
  populated two-column index readable from a fresh connection.

### CR-02: A non-string frontmatter `title` aborts the entire index update with a raw traceback

**Files modified:** `src/sif/indexing/parser.py`, `src/sif/indexing/incremental.py`,
`tests/unit/indexing/test_parser.py`, `tests/unit/indexing/test_incremental.py`
**Commit:** `a43296e`
**Applied fix:**
- `MarkdownParser.parse` coerces only a `str` frontmatter title (stripped);
  lists, mappings, numbers and `None` fall through to the H1/stem extraction.
  The raw metadata value is left untouched so the D-08 checksum/storage
  contract is unchanged. The unchecked `cast("str", ...)` is gone.
- `IncrementalIndexer._process_file` now keeps the document-row writes inside
  a per-file `except (sqlite3.Error, TypeError)` boundary: a write failure is
  logged, emitted as `error Error indexing ...`, counted as `failed`, and the
  pass continues (D-04 isolation). Each write block still owns its short
  transaction, so a failed file leaves nothing half-written.
- Tests: parser fixtures for `title: [not, a, string]`, `title: {a: b}`, and
  `title: 42` (H1 fallback and stem fallback), an incremental pass with both
  bad-title files sorting before a healthy trailing file (proving continued
  processing), and a repo-write `TypeError` fixture proving the write
  boundary counts the failure and later files still index.

### WR-01: The convention migration never completes when any in-scope file permanently fails to parse

**Files modified:** `src/sif/indexing/incremental.py`, `tests/unit/indexing/test_incremental.py`
**Commit:** `dd0bfa5`
**Applied fix:**
- `update_collection` now tracks `failed_stored` — failures whose scan path
  already has a stored document — and writes the `convention:<collection_id>`
  marker when `failed_stored == 0` instead of `failed == 0`. A permanently
  unparseable file that was never stored (binary/non-UTF-8, permission loss)
  stays reported in `result.failed` but cannot strand the migration, so
  subsequent updates take the checksum-skip path again instead of re-parsing
  and rewriting every healthy document forever.
- A failure on stored data still blocks the marker (D-09 preserved), keeping
  old-convention rows retryable.
- Tests: a permanent binary file plus a healthy `.md` shows the marker written
  on the first pass and a second pass that leaves the healthy row untouched
  (`updated == 0`, `metadata_only == 0`, no `migrate` event); a stored file
  that becomes unreadable keeps the marker absent until the file is fixed and
  the next pass completes the migration.

### WR-02: `-n/--limit` accepts zero/negative values with three different behaviors

**Files modified:** `src/sif/cli/commands/search.py`, `tests/unit/cli/test_search_pagination.py`
**Commit:** `340546e`
**Applied fix:**
- The `-n/--limit` option on `search`, `vsearch`, and `query` is now
  `click.IntRange(min=1)` (default `None` still resolves through
  `_resolve_limit`), so 0 and negative values exit 2 at parse time instead of
  reaching `LIMIT -1` (SQLite's unbounded semantics) on BM25 while the other
  two commands clamped to one row.
- Tests: `0` and `-1` are asserted to exit 2 with the Click range error on all
  three commands (six parametrized cases).

### IN-04: Migration tests never reopen the database, so rebuild rollbacks are invisible

**Files modified:** `tests/unit/database/test_schema_title_fts.py`, `tests/unit/mcp/test_backend.py`
**Commit:** `4546047` (same commit as CR-01 — the reopen assertions are the
CR-01 regression tests)
**Applied fix:**
- Added `TestMigrationDurability` (four reopen-on-a-new-connection tests:
  close-without-commit, read-only CLI boundary, idempotent re-init with a
  statement trace, injected DDL/population failure) and
  `test_dimension_mismatch_leaves_the_migrated_index_populated`, which runs
  the real `SearchBackend` dimension-mismatch construction, reopens the file,
  and asserts the pre-existing document is still title-MATCHable with FTS row
  count equal to the document count — both before and after a later
  correct-width construction.

## Deferred

Per the dispatch scope, these Info findings were deliberately left open and
are **not** addressed by this iteration:

- **IN-01** — vector scores are L2-derived but documented/converted as cosine
  distance (`src/sif/search/vector.py`). Pre-existing; needs a metric/scale
  decision (schema migration or doc correction) before Phase 20/21 score
  filters.
- **IN-02** — rerank rebuild drops `vectors_stale` (`src/sif/search/rerank.py`).
  Latent today; candidate for a `dataclasses.replace` cleanup.
- **IN-03** — docs claim an MCP `vec_search` per-chunk surface that is not
  registered (`docs/benchmarking.md`). `docs/benchmarking.md` is not
  generator-owned, but this is a wording fix outside the dispatched scope.
- **IN-05** — `BM25Searcher.search_chunks` violates the pre-pagination
  `min_score`/global-rank contract; no production caller today.
- **IN-06** — MCP backend silently creates an empty index at a nonexistent
  path; a diagnosability warning, not data loss.

## Quality Gates

Run after all four fixes, in the main checkout (`workflow.use_worktrees:
false`; PATH `pytest`, not `.venv`):

| Gate | Result |
|------|--------|
| `ruff check src tests` | All checks passed |
| `ruff format --check src tests` | 198 files already formatted |
| `ty check src/sif` | All checks passed |
| `env -u FORCE_COLOR NO_COLOR=1 pytest` | 2054 passed, 1 skipped; coverage 95.27% (fail_under=90) |

No `pyproject.toml`/`uv.lock` changes; no new dependencies; no new source files
(tests were added to existing test modules). Locked CONTEXT decisions, the
public FTS column contract, the bench method, and the pinned
`_TITLE_WEIGHT = 1.0` verdict are untouched.

---

_Fixed: 2026-11-15T05:16:12Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
