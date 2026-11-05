---
phase: 10-raise-pytest-coverage-to-90
reviewed: 2026-11-05T20:38:48Z
depth: standard
files_reviewed: 42
files_reviewed_list:
  - pyproject.toml
  - src/sif/cli/commands/search.py
  - src/sif/cli/formatters.py
  - src/sif/database/database.py
  - src/sif/database/migrations.py
  - src/sif/database/schema.py
  - src/sif/embedding/cache.py
  - src/sif/indexing/chunker.py
  - src/sif/mcp/transports/http.py
  - src/sif/utils/__init__.py
  - src/sif/utils/logging.py
  - src/sif/utils/progress.py
  - src/sif/utils/text.py
  - tests/unit/cli/test_collection.py
  - tests/unit/cli/test_get.py
  - tests/unit/cli/test_main.py
  - tests/unit/cli/test_search.py
  - tests/unit/core/__init__.py
  - tests/unit/core/test_collection_entity.py
  - tests/unit/core/test_context.py
  - tests/unit/database/__init__.py
  - tests/unit/database/test_database.py
  - tests/unit/database/test_migrations.py
  - tests/unit/database/test_repositories.py
  - tests/unit/database/test_schema.py
  - tests/unit/embedding/test_cache.py
  - tests/unit/indexing/test_chunker.py
  - tests/unit/indexing/test_parser.py
  - tests/unit/indexing/test_scanner.py
  - tests/unit/inference/test_reranker.py
  - tests/unit/mcp/test_integration.py
  - tests/unit/mcp/test_server.py
  - tests/unit/mcp/test_transports_http.py
  - tests/unit/mcp/test_transports_stdio.py
  - tests/unit/models/__init__.py
  - tests/unit/models/test_download.py
  - tests/unit/search/test_rerank.py
  - tests/unit/utils/__init__.py
  - tests/unit/utils/test_logging.py
  - tests/unit/utils/test_paths.py
  - tests/unit/utils/test_progress.py
  - tests/unit/utils/test_text.py
findings:
  critical: 2
  warning: 1
  info: 0
  total: 3
  necessity: 0
status: issues_found
---

# Phase 10: Code Review Report

**Reviewed:** 2026-11-05T20:38:48Z
**Depth:** standard
**Files Reviewed:** 42
**Status:** issues_found

## Summary

Reviewed all 42 scoped files, including the production fixes and the new real-SQLite/CLI/mocked-ML tests. Cross-checked migration behavior against `DatabaseConnection` in `src/sif/database/connection.py` and repository delete paths in `src/sif/database/repositories.py`. Necessity review was performed; no provable necessity findings were identified.

The full suite passes: 958 tests, 96.16% coverage, with the 90% gate satisfied. Ruff lint and format checks also pass. Those results do not cover the two failure cases below: a direct real-SQLite probe proved that legacy delete triggers survive schema initialization and continue returning deleted content, and XML output containing a legal document control character cannot be parsed. The tests also expose many unclosed SQLite `ResourceWarning`s because production CLI commands do not close their `Database` instances.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: Legacy direct-DELETE FTS triggers are never migrated

**File:** `src/sif/database/schema.py:148-163,188-191,236-242,261-267`
**Issue:** `_create_fts_tables()` detects and replaces only legacy direct-UPDATE triggers. Existing `documents_fts_delete` and `chunks_fts_delete` triggers using `DELETE FROM ...` are left in place by `CREATE TRIGGER IF NOT EXISTS`. On an external-content FTS5 table, that direct delete does not remove the index entry. A real-SQLite probe created an otherwise-correct external-content `documents_fts`, installed the old delete trigger, ran `_create_fts_tables()`, then deleted its source document: `MATCH 'legacydelete'` still returned 1 row and the trigger SQL remained unchanged. Existing upgraded databases can therefore return deleted documents and chunks indefinitely, despite the new fresh-schema delete triggers being correct.
**Fix:** Detect legacy delete triggers as well as update triggers and drop/recreate both during `create_all()`. Generalize the legacy-trigger helper to identify `DELETE FROM {fts_table}` as well as `UPDATE {fts_table} SET`, invoke it for `documents_fts_delete` and `chunks_fts_delete`, and add a regression test that begins with the legacy delete trigger on an already-external-content FTS table, calls `create_all()`, deletes the row, and asserts a zero-result `MATCH` query. Merely testing fresh-schema triggers will not cover this migration path.

### CR-02: XML escaping still emits XML-forbidden control characters

**File:** `src/sif/cli/commands/search.py:104-121`
**Issue:** `xml.sax.saxutils.escape()` and `quoteattr()` escape markup delimiters but do not remove or encode characters forbidden by XML 1.0, such as `\x00`-`\x08`, `\x0b`, `\x0c`, and `\x0e`-`\x1f`. These characters can legitimately occur in indexed document metadata/content. A direct call with a title containing `\x0b` produced output that `xml.etree.ElementTree.fromstring()` rejected as `not well-formed (invalid token)`. Thus `--xml` can still produce unusable machine output after the escaping fix.
**Fix:** Sanitize every XML-bound string (query attributes, result fields, and line numbers) through one XML 1.0 character validator before applying `escape()`/`quoteattr()`. Remove or explicitly replace forbidden code points, preserving tab, LF, and CR; alternatively use an XML serializer configured for the project's desired invalid-character policy. Add round-trip parsing tests containing control characters in both the query and result fields.

## Warnings

### WR-01: CLI-invoked database connections are left open

**File:** `src/sif/cli/commands/search.py:174-175,201-203,351-352,375-377,485-486,562-574`
**Issue:** Each command creates a persistent `Database` but never calls `close()` or uses its context manager. The `with db.connection` blocks only manage SQLite transaction state; they do not close the connection. The full suite reports numerous `ResourceWarning: unclosed database` messages, including from the reviewed CLI tests. The same lifecycle defect can accumulate open handles during repeated in-process invocation and prevents deterministic cleanup on normal and exceptional exits.
**Fix:** Own each command's database with `with Database(index_path) as db:` (covering schema initialization, queries, and output generation as needed), or use `try/finally: db.close()` around the entire command body. Apply the same pattern consistently to the other reviewed real-CLI command modules that instantiate `Database`, and add a test asserting closure after both success and an exception.

---

_Reviewed: 2026-11-05T20:38:48Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
