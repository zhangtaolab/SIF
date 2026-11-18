---
phase: 21-scale-maintenance-embedder-identity
fixed_at: 2026-11-15T18:25:45Z
review_path: .planning/phases/21-scale-maintenance-embedder-identity/21-REVIEW.md
iteration: 1
findings_in_scope: 9
fixed: 9
skipped: 0
status: all_fixed
---

# Phase 21: Code Review Fix Report

**Fixed at:** 2026-11-15T18:25:45Z
**Source review:** `.planning/phases/21-scale-maintenance-embedder-identity/21-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 9 (CR-01..CR-03, WR-01..WR-06)
- Fixed: 9
- Skipped: 0
- Info findings (IN-01..IN-07) are out of scope for `critical_warning` and were
  left untouched.

## Fixed Issues

### CR-01: Bench embedder soft-fail is converted into an uncaught crash

**Files modified:** `src/sif/cli/commands/bench.py`, `tests/unit/cli/test_bench.py`
**Commit:** d8b7f0d
**Status:** fixed
**Applied fix:** `_load_embedder` now clears `manager` on both the `ImportError`
and generic `Exception` paths, so a failure inside `load_model()` cannot leave
a constructed-but-unloaded manager for `_search_identity_check` to re-enter and
crash on. Regression tests patch the real failure seam (`load_model`) rather
than `from_settings`, for both error classes, and assert
`_search_identity_check(None, db)` returns `None`.

### CR-02: Identity decision is taken outside the index flock

**Files modified:** `src/sif/cli/commands/index.py`, `src/sif/indexing/embed_writer.py`,
`src/sif/embedding/identity.py`, `tests/unit/indexing/test_embed_writer.py`,
`tests/unit/cli/test_index.py`
**Commit:** 6dd935c
**Status:** fixed: requires human verification (concurrency logic)
**Applied fix:**
- `StreamingEmbedWriter.embed_document` now re-validates stored provenance in
  the document's own transaction: an explicit `BEGIN IMMEDIATE` holds SQLite's
  write lock across the vector/identity read and the identity write.
- D-02 is preserved exactly: when no vectors exist, a stale identity row never
  blocks the first vector write (which overwrites it as `verified`); when
  vectors now exist, the writer adopts a matching stored identity or raises
  `SystemicEmbedError` on a mismatch / missing identity. This deliberately
  differs from the review's literal snippet, which would have rejected the
  stale-row-on-empty-index case that D-02 and the existing
  `test_stale_identity_on_empty_index_is_overwritten_by_first_commit` require.
- `embed_cmd` now computes `current`, the check, and `write_identity_on_first`
  under `index_lock`, and runs `--force` certification inside the same lock
  window (only for a complete, unfiltered, zero-failure run).
- The vector probe is exposed as `has_stored_vectors` (public, documented).
- Regression tests: stale claim refused without persisting rows, matching
  concurrent identity adopted, and the lock-ordering spy proving identity
  resolution occurs between lock enter/exit.

### CR-03: backup / vacuum silently create an empty index

**Files modified:** `src/sif/cli/commands/index.py`, `tests/unit/cli/test_index.py`
**Commit:** ef200f7
**Status:** fixed
**Applied fix:** Both `vacuum_cmd` and `backup_cmd` refuse a nonexistent
`--index` path with `No index found at ... Run 'sif index update' first.`
before `open_initialized_database` can create the file/schema. Helper-level
`MaintenanceTargetError` contracts are unchanged for API callers. Existing
command tests now create the index file first; new tests assert a typo'd path
exits non-zero, creates neither the index nor a backup output, and never calls
the maintenance helper.

### WR-01: Reconcile assumes `document_embeddings` exists whenever the shadow does

**Files modified:** `src/sif/database/maintenance.py`, `tests/unit/database/test_maintenance.py`
**Commit:** fdb7e24
**Status:** fixed
**Applied fix:** `reconcile_embedded_documents` requires both
`embedded_documents` and `document_embeddings` to be present before touching
anything; a stripped environment is a `(0, 0)` no-op instead of a
`no such table` failure. Regression test builds a shadow-only database and
runs both `reconcile_embedded_documents` and a full `vacuum_index`.

### WR-02: Systemic model-output failures classified as document-local

**Files modified:** `src/sif/models/embedding.py`, `src/sif/embedding/manager.py`,
`src/sif/indexing/embed_writer.py`, `tests/unit/embedding/test_manager.py`,
`tests/unit/indexing/test_embed_writer.py`, `tests/unit/indexing/test_watcher.py`
**Commit:** 4687b0b
**Status:** fixed
**Applied fix:** Added `EmbeddingOutputError(RuntimeError)` for output count,
width, and finiteness violations; the manager's count/width/finiteness guards
raise it. `StreamingEmbedWriter.embed_document` translates it to
`SystemicEmbedError` (with document and batch context), so `embed_cmd` aborts
after prior commits and the watcher disables the session instead of re-queueing
the path forever. Genuine document-local parse/chunk/storage errors keep the
per-document path (existing `RuntimeError` tests still pass by subclassing).
Tests cover the manager type, the writer translation, and a watcher burst that
disables without retrying.

### WR-03: Backup copy is group/other-readable during copy and verification

**Files modified:** `src/sif/database/maintenance.py`, `tests/unit/database/test_maintenance.py`
**Commit:** a6ad0c3
**Status:** fixed
**Applied fix:** `_create_backup_target` creates the copy with
`os.open(O_CREAT|O_EXCL|O_WRONLY|O_NOFOLLOW, 0o600)` before the SQLite backup
connection opens it, so the restrictive mode applies from the first byte and
the whole copy/integrity-check window. The post-copy chmod remains as
defense-in-depth. Regression test records the file mode from inside
`Connection.backup` under umask 022 and requires `0o600`.

### WR-04: Backup target validation is check-then-use (symlink TOCTOU)

**Files modified:** `src/sif/database/maintenance.py`, `tests/unit/database/test_maintenance.py`
**Commit:** a6ad0c3
**Status:** fixed
**Applied fix:** The same exclusive `O_CREAT|O_EXCL|O_NOFOLLOW` creation is now
the enforcement point: a file or symlink planted after `_validate_backup_target`
makes creation fail rather than being opened and overwritten. `fstat` confirms a
regular file. The path-based pre-checks remain for their specific messages and
are documented as non-authoritative. Regression test covers repeated creation
(refused) and a planted symlink (refused, link target never created).

### WR-05: `vsearch` embeds the query before its identity check

**Files modified:** `src/sif/cli/commands/search.py`, `tests/unit/cli/test_search.py`
**Commit:** dbf1efa
**Status:** fixed
**Applied fix:** `vsearch_cmd` now opens the DB and resolves collections first,
runs the search-mode identity check, and only then calls `manager.embed_query`.
The old duplicated error translation moved into `_embedder_error`, preserving
the exact `Embedding backend not installed` / `Failed to load embedding model`
messages. The dimension-refusal test now also asserts `embed_query` was never
called (fails before the fix, passes after).

### WR-06: Writer clears the identity-write flag before the transaction commits

**Files modified:** `src/sif/indexing/embed_writer.py`, `tests/unit/indexing/test_embed_writer.py`
**Commit:** 6dd935c (grouped with CR-02; both live in the same transaction hunk)
**Status:** fixed: requires human verification (transaction-state logic)
**Applied fix:** `embed_document` records that it claimed the identity inside
the `with conn:` block and clears `self._write_identity` only after the block
exits successfully. A failed commit leaves the claim pending, so the next
document/retry writes the identity instead of committing vectors without
provenance. Regression test uses a connection proxy whose first commit fails,
asserts the claim stays pending and nothing is visible, then retries and
asserts the identity commits with the vectors.

## Skipped Issues

None.

## Verification

All quality gates ran in the **main checkout** (`workflow.use_worktrees` is
`false` in `.planning/config.json`, so no isolated worktree was created). The
results below are reproducible from the tree at commit `dbf1efa`.

- `ruff check src tests` — passed.
- `ruff format --check src tests` — passed (218 files).
- `ty check src/sif` — passed.
- `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit -q --no-cov` — 2586 passed.
- `env -u FORCE_COLOR NO_COLOR=1 pytest tests/integration -q --no-cov` — 88 passed, 1 skipped.

Per-fix targeted runs (also green): `tests/unit/cli/test_bench.py`,
`tests/unit/indexing/test_embed_writer.py`, `tests/unit/cli/test_index.py`,
`tests/unit/indexing/test_watcher.py`, `tests/unit/database/test_maintenance.py`,
`tests/unit/embedding/test_manager.py`, `tests/unit/cli/test_search.py`.

REVIEW-FIX.md is intentionally left uncommitted; the orchestrator commits it.

---

_Fixed: 2026-11-15T18:25:45Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
