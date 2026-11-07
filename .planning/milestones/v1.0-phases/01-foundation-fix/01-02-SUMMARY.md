---
phase: 01-foundation-fix
plan: 02
subsystem: database + search
key-files:
  created: []
  modified:
    - src/docsift/database/schema.py
    - src/docsift/database/repositories.py
    - src/docsift/search/bm25.py
    - src/docsift/database/__init__.py
  deleted:
    - src/docsift/database/sqlite_repository.py
decisions:
  - "Use FTS5 external content tables with content_rowid='rowid' instead of standalone virtual tables"
  - "Synchronize FTS5 via SQLite AFTER INSERT/UPDATE/DELETE triggers rather than manual repository inserts/deletes"
  - "Join FTS5 virtual tables on integer rowid, not TEXT id"
  - "Remove stale sqlite_repository.py and consolidate exports through repositories.py"
tech-stack:
  added: []
  patterns:
    - "FTS5 external content tables"
    - "SQLite triggers for automatic index synchronization"
metrics:
  duration_minutes: ~10
  tasks_completed: 4
  files_changed: 4
  files_deleted: 1
---

# Phase 01 Plan 02: FTS5 Synchronization Fix Summary

**One-liner:** Converted FTS5 virtual tables to external content tables with SQLite triggers, removed stale sqlite_repository.py, and fixed BM5 rowid joins.

## What Changed

- **`src/docsift/database/schema.py`**: Rewrote `_create_fts_tables` to create `documents_fts` and `chunks_fts` as external content tables (`content='documents'`, `content='document_chunks'`, `content_rowid='rowid'`). Added `INSERT`/`UPDATE`/`DELETE` triggers for both tables. Added `_fts_is_misconfigured` helper to avoid unnecessary drops, with conditional seeding of existing data.
- **`src/docsift/database/repositories.py`**: Removed manual `INSERT INTO chunks_fts` from `DocumentChunkRepository.create` and manual `DELETE FROM chunks_fts` loop from `delete_by_document`. Triggers now handle synchronization.
- **`src/docsift/search/bm25.py`**: Fixed JOIN conditions so `documents_fts` joins on `d.rowid` and `chunks_fts` joins on `dc.rowid` instead of the TEXT `id` columns.
- **`src/docsift/database/sqlite_repository.py`**: Deleted stale legacy repository file.
- **`src/docsift/database/__init__.py`**: Rewrote exports to expose concrete repository classes from `repositories.py` and connection classes from `connection.py`, keeping `MigrationManager` for backward compatibility.

## Deviations from Plan

None — plan executed exactly as written.

## Deferred Issues

- `tests/integration/test_index_and_search.py` fails to collect due to a pre-existing import error (`cannot import name 'ChunkingStrategy' from 'docsift.indexing.chunker'`). This is unrelated to the current plan and was not fixed.

## Threat Flags

None — no new security-relevant surface introduced.

## Self-Check: PASSED

- [x] `src/docsift/database/schema.py` contains `content='documents'` and triggers
- [x] `src/docsift/database/repositories.py` no longer contains manual FTS INSERT/DELETE
- [x] `src/docsift/search/bm25.py` joins on `rowid`
- [x] `src/docsift/database/sqlite_repository.py` does not exist
- [x] `src/docsift/database/__init__.py` exports concrete repositories from `repositories.py`
- [x] All four tasks committed

## Commits

| Hash | Message |
|------|---------|
| 1289936 | feat(01-02): update SchemaManager with external content FTS5 tables and triggers |
| 7d725ea | fix(01-02): remove manual FTS sync from DocumentChunkRepository |
| e3c8271 | fix(01-02): fix BM25Searcher FTS5 joins to use rowid |
| ce76690 | chore(01-02): delete sqlite_repository.py and fix database __init__ exports |
