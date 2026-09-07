---
phase: 05-agent-context-experience
reviewed: 2026-09-07T04:31:07Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - src/sif/cli/commands/context.py
  - src/sif/database/repositories.py
  - src/sif/search/bm25.py
  - src/sif/search/context_attach.py
  - src/sif/search/hybrid.py
  - src/sif/search/vector.py
  - src/sif/utils/paths.py
  - tests/unit/cli/test_context.py
  - tests/unit/database/test_repositories.py
  - tests/unit/database/test_schema.py
  - tests/unit/search/test_bm25.py
  - tests/unit/search/test_context_attach.py
  - tests/unit/search/test_hybrid.py
  - tests/unit/search/test_vector.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 05: Code Review Report (Incremental — gap-closure changes)

**Reviewed:** 2026-09-07T04:31:07Z
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Scope Note

Incremental review of the Phase 05 gap-closure work (plans 05-08 / 05-09): shared
`normalize_path()` + `attach_path_contexts()` helper replacing the SQL `IN` pre-filter in
all three searchers, canonical path targets at `context add` with dual-form upsert
self-heal, `delete_orphaned_paths()` rewritten to normalized comparison, real-SQL
regression tests replacing mock-bypassed ones, and the `vec_db` fixture fix.

Note: the `diff_base` full hash supplied by the workflow (`ff10314cc39efea...`) is not a
valid object name; it was resolved to the intended commit `ff10314cc3c4d82`
(`docs(05): add code review report`, the prior review commit). The diff over that base
matches the described scope exactly (14 files, +741/-166).

## Verification of Prior-Review Claims (2026-09-06 report, same path — now overwritten)

- **CR-02 (prune deletes valid mismatched contexts): FIXED — fix is real.**
  `ContextRepository.delete_orphaned_paths()` (`src/sif/database/repositories.py:463-485`)
  now normalizes both sides in Python via the shared `normalize_path`, and the regression
  test `test_prune_preserves_symlink_mismatched_context`
  (`tests/unit/database/test_repositories.py:86-104`) runs against real SQLite with a
  genuine symlink alias whose string forms verifiably differ (macOS `/private/var/folders/...`
  vs `/tmp`-style alias). The test passed in this review's run. The document-side invariant
  also holds: `src/sif/indexing/parser.py` stores `str(file_path.resolve())`, which equals
  `normalize_path`'s output for already-absolute spellings.
- **IN-03 (hybrid MagicMock tuple-row fallback): REMOVED cleanly.** The 24-line
  duck-typed fallback in `hybrid.py` is gone; `_attach_contexts` now delegates to the
  shared helper. No production caller relied on the fallback: both `Database.connection`
  (`src/sif/database/database.py:34`) and `DatabaseConnection` (line 120) set
  `row_factory = sqlite3.Row`, and the legacy MCP backend routes through
  `SearchPipeline` (`src/sif/mcp/backend.py:17,94`), so it inherits the helper. Full
  suite: 657 passed.
- **CR-01 (FTS5 external-content DELETE triggers): STILL OPEN — carried forward.**
  `src/sif/database/schema.py:235-241,260-266` still use `DELETE FROM documents_fts WHERE
  rowid = old.rowid`, and the new `TestFtsUpdateTrigger` class covers only UPDATE
  triggers, not DELETEs. Out of this diff's file scope (schema.py not in the changed
  set); must stay on the books.

Quality gates on the changed files: `ruff check` clean, `ruff format --check` clean,
targeted tests (52) and the full suite (657) pass with `env -u FORCE_COLOR NO_COLOR=1`.
The `vec_db` fixture fix (`sqlite_vec.load(db)`) is real: schema migration tests now
execute instead of silently skipping (0 skips in the run).

## Summary

The architecture of the fix is sound: one shared helper with a constant-SQL batch query
and Python-side normalization is the correct shape (realpath is not invertible, so any
exact-match SQL pre-filter on resolved strings can never match verbatim legacy rows),
and the replacement of mock-bypassed tests with real-SQL suites is a genuine
improvement — the symlink fixtures create real mismatches rather than asserting on
mocked cursors. No SQL injection, secret handling, or traversal issues: all new SQL is
parameterized or constant.

However, the adversarial pass found that the change widened the blast radius of
malformed path data. Pre-change, the SQL `IN` pre-filter meant only rows matching
result paths were ever `realpath`-ed, and prune was pure SQL. Post-change, **every**
stored path-context row is normalized on **every** search and on prune. A single
context row whose `target_id` holds an unresolvable `~user` form (an account removed, a
DB synced/copied to another machine — plausible for a portable personal-KB tool, and
exactly the class of pre-normalization verbatim rows the self-heal path acknowledges
exist) raises `RuntimeError` out of `Path.expanduser()` and crashes `sif search` (all
three searchers), `sif context prune`, and `sif context add` with raw tracebacks.
Reproduced live against real SQLite (WR-01). Second, the write-side self-heal only
merges when the user re-types the *exact* historical spelling; re-adding the same file
via its canonical form leaves the legacy row in place forever, and prune can never
clean the duplicate because both rows normalize to a live document path (WR-02).

## Critical Issues

None in this diff's file scope. (CR-01 from the prior review remains open in
`src/sif/database/schema.py` — carried forward above.)

## Warnings

### WR-01: One malformed `target_id` crashes all search commands, prune, and add

**File:** `src/sif/search/context_attach.py:56`, `src/sif/database/repositories.py:481`, `src/sif/cli/commands/context.py:63` (root: `src/sif/utils/paths.py:52`)
**Issue:** `normalize_path()` calls `Path(path).expanduser()`, which raises
`RuntimeError` ("Could not determine home directory") for `~username` forms whose user
does not resolve. `attach_path_contexts()` now runs `normalize_path(row["target_id"])`
over **every** path-type context row on **every** BM25/vector/hybrid search (the old
SQL `IN` pre-filter only ever normalized rows matching result paths), and
`delete_orphaned_paths()` normalizes every path-context row. Reproduced against real
SQLite in this review:

```
attach CRASHED: RuntimeError - Could not determine home directory.   # attach_path_contexts with one '~deleteduser/...' row
prune CRASHED: RuntimeError - Could not determine home directory.    # delete_orphaned_paths, documents table present
```

The same exception escapes `context_add` (line 63) as a raw traceback instead of a
`click.ClickException`, violating the project's stated error-handling convention
(CLAUDE.md). Trigger plausibility: a pre-fix verbatim row (the dual-form self-heal in
the same diff acknowledges such rows exist), or a DB whose `~user` targets stop
resolving after the account is removed or the DB file is copied to another machine.
Until the row is removed (only discoverable via `sif context list` + manual
`context remove`), every search command is bricked. This exposure did not exist
pre-change.

**Fix:** Make normalization total — never let a stored row raise:

```python
# src/sif/utils/paths.py
def normalize_path(path: str | Path) -> str:
    """..."""
    try:
        return str(expand_path(path))
    except (RuntimeError, OSError, ValueError):
        # e.g. "~removeduser/..." after an account no longer resolves. A stored
        # context row must never crash search/prune — degrade to the raw form
        # (it simply matches nothing, same effective outcome as today minus the crash).
        return str(path)
```

Additionally, wrap the `context add` path resolution in a `click.ClickException` so a
bad `~user` typo at the CLI produces a user-facing error, not a traceback, and add a
regression test inserting a `~unknownuser/...` row before calling
`attach_path_contexts` / `delete_orphaned_paths`.

### WR-02: Self-heal merge only fires on exact historical re-typing — duplicate rows accumulate and prune cannot clean them

**File:** `src/sif/cli/commands/context.py:66-74`
**Issue:** The dual-form upsert looks up only two spellings: the canonical form and the
exact verbatim string typed now. If a legacy row exists under spelling *A* (e.g.
`/tmp/vault/doc.md`) and the user re-adds the same file under spelling *B* (most
commonly the canonical `/private/tmp/vault/doc.md`, or any other alias), neither lookup
finds the legacy row, so a second row is created and the legacy row survives forever.
`delete_orphaned_paths()` cannot clean it: both rows normalize to a live document path,
so neither is an orphan. Result: permanent duplicate rows visible in `sif context list`,
with no automated cleanup path. Read behavior stays correct (newest `updated_at` wins
deterministically in `attach_path_contexts`), so this is data hygiene / user-facing
duplication rather than wrong results — but the merge the feature promises ("instead of
creating a duplicate row") silently fails on the most likely re-add path.

**Fix:** On the explicit re-add miss, resolve by normalized key over all path rows
instead of by exact string:

```python
if not existing and type == "path":
    # Merge ANY historical spelling of the same file, not just the exact
    # verbatim re-type. Explicit re-add only — never a bulk migration.
    candidates = [
        c for c in repo.list_by_type("path")
        if c.id != existing_id_marker and normalize_path(c.path) == actual_target
    ]
    if candidates:
        candidates.sort(key=lambda c: c.updated_at, reverse=True)
        winner = candidates[0]
        if repo.update_target(winner.id, actual_target):
            existing = winner
        for loser in candidates[1:]:
            repo.delete(loser.id)   # collapse duplicates left by old spellings
```

Guard the `normalize_path` comparison with the WR-01 total-form fallback so a poison
row cannot crash the merge either.

## Info

### IN-01: Duplicate-key winner chosen by TEXT ordering of mixed ISO-8601 formats

**File:** `src/sif/search/context_attach.py:53-56`
**Issue:** `ORDER BY updated_at` relies on SQLite TEXT comparison. Rows written today
carry `+00:00` and microseconds (`datetime.now(timezone.utc).isoformat()`), but rows
migrated from the legacy `path_contexts` table can carry offset-less or local-time
forms (the migration copies timestamps verbatim — see `schema.py:118-122` and the
`'2024-01-01T00:00:00'` fixtures). Across mixed formats/timezones the text sort can
rank a legacy row as "newest" when its instant is older, so duplicate normalized keys
can resolve to stale content.
**Fix:** Resolve duplicates in Python with parsed datetimes (or normalize timestamp
format during the `path_contexts` migration), e.g. keep the ORDER BY for determinism
but build the map via `datetime.fromisoformat` comparison on collision.

### IN-02: Tests call `SchemaManager` private methods to build fixtures

**File:** `tests/unit/database/test_repositories.py:31-32`, `tests/unit/search/test_context_attach.py:52`
**Issue:** `manager._create_documents_table()` / `manager._create_contexts_table()`
couple the new suites to private schema internals; a refactor of those methods breaks
tests for repositories and context attachment.
**Fix:** Use `SchemaManager(conn).create_all()` on a plain connection (vector tables
are skipped gracefully without sqlite-vec) or add a small public fixture-builder.

### IN-03: `update_target` return value ignored at the self-heal call site

**File:** `src/sif/cli/commands/context.py:74`
**Issue:** If `update_target` returns `False` (row vanished mid-transaction, or a
future subclass override), the code proceeds to `repo.update(existing)` and reports
"Context updated" while the row still holds the verbatim target. Harmless today in the
single-process CLI, but it is an unchecked error return on a data-mutating path.
**Fix:** `if not repo.update_target(existing.id, actual_target): raise
click.ClickException(...)` (or log a warning and continue).

---

_Reviewed: 2026-09-07T04:31:07Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
