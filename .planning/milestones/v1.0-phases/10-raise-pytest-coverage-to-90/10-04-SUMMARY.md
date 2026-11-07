---
phase: 10-raise-pytest-coverage-to-90
plan: 04
subsystem: testing
tags: [pytest, coverage, sqlite, database, repositories]

requires:
  - phase: 10-raise-pytest-coverage-to-90
    plan: 01
    provides: Post-deletion coverage baseline and production-DDL Pattern 2 test foundation.
provides:
  - Real-SQLite repository, connection, migration, schema, and embedding-cache behavioral coverage.
  - Repositories, schema, database, and cache at 100%; migrations at 92% in the canonical full suite.
  - Regression protection for FTS deletion, lazy stats schema creation, and multi-statement migrations.
affects:
  - Phase 10 plan 10-07 coverage tollgate.
  - SQLite FTS consistency, database reset/stats behavior, and migration reliability.

actuals:
  tokens: 37562
  tasks: 3
  commits: 3
plan_head_before: e8c40f0f162cd86c4b799768ec0f28aebcd1a136
plan_head_after: 4b74482b1aa544e7afa545810fcc8b6b4bdfe707

tech-stack:
  added: []
  patterns: [real in-memory SQLite + production DDL (Pattern 2)]

key-files:
  created:
    - tests/unit/database/__init__.py
    - tests/unit/database/test_database.py
    - tests/unit/database/test_migrations.py
    - tests/unit/embedding/test_cache.py
  modified:
    - tests/unit/database/test_repositories.py
    - tests/unit/database/test_schema.py
    - src/sif/database/schema.py
    - src/sif/database/database.py
    - src/sif/database/migrations.py
    - src/sif/embedding/cache.py

key-decisions:
  - "Use production SchemaManager DDL and real SQLite for normal repository, migration, schema, and cache behavior; reserve patches for extension and external-failure boundaries."
  - "Repair real defects exposed by tests: use FTS5 delete commands, initialize missing tables before stats, execute migration scripts with executescript, and close cache connections safely."

patterns-established:
  - "A real-SQL round trip can validate repository and trigger behavior while exposing stale-index defects that mocked connections cannot detect."
  - "Small real-SQL adapters support MigrationManager without MagicMock; executescript is the explicit multi-statement capability boundary."

requirements-completed: [T-10-1]

coverage:
  - id: D1
    description: Repository CRUD, missing-row, batch, context, and LLM-cache behavior plus production schema/index/FTS paths execute against real SQLite.
    requirement: T-10-1
    verification:
      - kind: integration
        ref: "tests/unit/database/test_repositories.py and test_schema.py: 35 passed; TestRepositoryCoverage round trip and delete-trigger regressions"
        status: pass
      - kind: other
        ref: ".planning/tmp/10-04-repositories.xml database/repositories.py line-rate=1; threshold >= 0.88"
        status: pass
    human_judgment: false
  - id: D2
    description: Database connection/commit/rollback/stats/reset/extension fallback and MigrationManager fresh/current/failure/reset behavior use real SQLite.
    requirement: T-10-1
    verification:
      - kind: integration
        ref: "tests/unit/database/test_database.py and test_migrations.py: 12 passed; rollback leaves no partial row and fresh migration creates actual tables"
        status: pass
      - kind: other
        ref: ".planning/tmp/10-04-database.xml database/database.py line-rate=1; .planning/tmp/10-04-migrations.xml database/migrations.py line-rate=0.92; thresholds >= 0.85"
        status: pass
    human_judgment: false
  - id: D3
    description: EmbeddingCache miss/hit, batches, strict mismatch, segmentation, clear/stats, Unicode/empty keys, legacy rebuild, and failure fallbacks persist only beneath tmp_path.
    requirement: T-10-1
    verification:
      - kind: integration
        ref: "tests/unit/embedding/test_cache.py: 10 passed; cache DB path is tmp_path/cache/embeddings_cache.db"
        status: pass
      - kind: other
        ref: ".planning/tmp/10-04-cache.xml embedding/cache.py line-rate=1; threshold >= 0.85"
        status: pass
    human_judgment: false
  - id: D4
    description: The complete quality suite remains green and overall Phase 10 coverage reaches the phase target without coverage configuration changes.
    requirement: T-10-1
    verification:
      - kind: other
        ref: "ruff check src tests; ruff format --check src tests: PASS (136 files)"
        status: pass
      - kind: integration
        ref: "env -u FORCE_COLOR NO_COLOR=1 pytest --cov=src/sif: 797 passed, 0 failed; .planning/tmp/10-04-full.xml TOTAL line-rate=0.9089"
        status: pass
    human_judgment: false

duration: 30min
completed: 2026-11-05
status: complete
---

# Phase 10 Plan 04: Real-SQLite Database Layer Coverage Summary

**Raised full-suite coverage from 88.57% to 90.89% with real-SQLite database/cache tests; repositories, database, schema, and cache reached 100%, migrations reached 92%, and real SQL exposed and proved fixes for stale FTS rows, lazy stats initialization, and broken migration scripts.**

## Performance

- **Duration:** 30 minutes (1,813 seconds)
- **Started:** 2026-11-05T18:54:45Z
- **Completed:** 2026-11-05T19:24:58Z
- **Tasks:** 3/3
- **Files modified:** 6 test modules plus 4 production modules (10 code/test files), plus planning state.
- **Realized code/test diff:** 150,248 characters across before/after file content (37,562 chars/4 actual tokens); 1,164 insertions and 56 deletions.
- **Full suite:** 797 passed, 0 failed in 10.89 seconds.

## Accomplishments

- Added the `tests/unit/database` package marker and `TestRepositoryCoverage`, proving collection/document/chunk/context CRUD, empty and missing-row behavior, collection deletion, batch ordering, and LLM-cache expiry against production DDL.
- Extended schema tests through index creation, FTS insert/update/delete synchronization, legacy FTS rebuild/reseed, migration savepoint rollback, stats, and reset behavior.
- Added `TestDatabaseRealSQLite` for connection reuse/closure, both connection styles, commit/rollback, lazy stats, reset, and optional sqlite-vec failures using only `tmp_path` databases.
- Added `TestMigrationManager` with a small real-SQL adapter, proving version 0/current/fresh/error/reset behavior and actual migrated table creation at a custom embedding dimension.
- Added `TestEmbeddingCache` for persistence, batches, strict mismatch, model segmentation, replacement, clear/stats, Unicode/empty hashes, legacy rebuild, corrupt JSON/schema, and acquisition failure fallbacks.
- Passed the automatic tracer feedback gate by rerunning repository/schema behavior and the 88% repository coverage gate before expansion.
- Reached **90.89% overall line coverage**, satisfying the Phase 10 target before the final permanent gate plan, without editing `pyproject.toml` or adding pragmas/exclusions.

## Measured Coverage Movement

| File | 10-03 full suite | 10-04 full suite | Missed change |
|---|---:|---:|---:|
| `src/sif/database/repositories.py` | 73% (47 missed / 173) | **100%** (0 missed / 173) | -47 |
| `src/sif/database/database.py` | 62% (32 missed / 85) | **100%** (0 missed / 86) | -32 |
| `src/sif/database/migrations.py` | 35% (24 missed / 37) | **92%** (4 missed / 50) | -20 |
| `src/sif/embedding/cache.py` | 60% (31 missed / 77) | **100%** (0 missed / 79) | -31 |
| `src/sif/database/schema.py` | 91% (12 missed / 128) | **100%** (0 missed / 128) | -12 |
| **TOTAL** | **88.57%** (608 missed / 5321) | **90.89%** (486 missed / 5337) | **-122** |

The statement denominator increased by 16 because the sanctioned migration repair and safe cache connection handling added production statements. The canonical XML records 5,337 valid lines, 4,851 covered lines, and `line-rate=0.9089`; terminal output displays TOTAL as 91%.

## Task Commits

1. **Task 1: Prove repository round trip and expand production-DDL coverage** — `0a4adc4` (test)
2. **Task 2: Exercise Database and MigrationManager on real SQLite** — `777df7e` (test)
3. **Task 3: Cover EmbeddingCache persistence and defensive paths** — `4b74482` (test)

## Files Created/Modified

- `tests/unit/database/__init__.py` — package marker preventing same-basename collection collisions with legacy `tests/unit/db/`.
- `tests/unit/database/test_repositories.py` — expanded the real-SQL fixture to production tables/FTS/indexes and added comprehensive repository behavior.
- `tests/unit/database/test_schema.py` — added production index, FTS delete/rebuild, migration rollback, reset, and stats coverage.
- `tests/unit/database/test_database.py` — new real-temp-file connection and transaction suite with Settings cache isolation.
- `tests/unit/database/test_migrations.py` — new real-SQL migration adapter and fresh/current/failure/reset suite.
- `tests/unit/embedding/test_cache.py` — new real-temp-file cache behavior and corruption/failure suite.
- `src/sif/database/schema.py` — fixed external-content FTS5 delete triggers to issue the required `delete` command.
- `src/sif/database/database.py` — fixed lazy `get_stats()` to create missing schema before querying.
- `src/sif/database/migrations.py` — added a typed `_execute_script` path using `executescript` for the two SQL script constants.
- `src/sif/embedding/cache.py` — centralized real SQLite connection closure while preserving normal cache semantics.

## Decisions Made

- Used real SQLite for every normal SQL path; no MagicMock connection was introduced. Narrow patches covered sqlite-vec loading, migration failure injection, and cache connection acquisition failures.
- Retained and strengthened assertions that exposed production defects rather than weakening tests to fit existing behavior.
- Used `executescript` only for `SCHEMA_SQL` and `FTS_SQL`, exactly as the plan's conditional production artifact allowed; vector DDL remains single-statement `execute`.
- Preserved D-07 isolation with an autouse `get_settings.cache_clear()` fixture and scoped patches; all persistent paths are in memory or under `tmp_path`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed stale rows from external-content FTS indexes on deletion**
- **Found during:** Task 1.
- **Issue:** The new real-SQL delete-trigger regression failed because direct `DELETE FROM documents_fts/chunks_fts` left deleted content searchable.
- **Fix:** Changed both production delete triggers to issue FTS5's external-content `INSERT ... VALUES('delete', old.rowid, old.content)` command.
- **Files modified:** `src/sif/database/schema.py`, `tests/unit/database/test_schema.py`.
- **Verification:** Insert/update/delete queries return expected counts; all 35 focused tests and the full suite pass.
- **Commit:** `0a4adc4`.

**2. [Rule 1 - Bug] Initialized tables before lazy database stats**
- **Found during:** Task 2.
- **Issue:** `Database.get_stats()` created a `SchemaManager` but did not create tables, so a fresh real DB raised `sqlite3.OperationalError` despite the lazy-initialization contract.
- **Fix:** Called `create_all()` when lazily constructing the stats schema manager.
- **Files modified:** `src/sif/database/database.py`, `tests/unit/database/test_database.py`.
- **Verification:** Fresh stats returns zero counts, reset recreates usable tables, database focused coverage is 100%.
- **Commit:** `777df7e`.

**3. [Rule 1 - Bug] Executed migration DDL as scripts**
- **Found during:** Task 2.
- **Issue:** Fresh migration passed multi-statement `SCHEMA_SQL` to sqlite3 `execute`, producing `ProgrammingError: You can only execute one statement at a time`.
- **Fix:** Added typed `_execute_script`, using the real connection context's `executescript` or an adapter's equivalent capability; added actual-table and failure regression tests.
- **Files modified:** `src/sif/database/migrations.py`, `tests/unit/database/test_migrations.py`.
- **Verification:** Fresh migration creates all expected tables and version row; migration focused coverage is 92%.
- **Commit:** `777df7e`.

**4. [Rule 2 - Resource safety] Made cache connection cleanup reliable**
- **Found during:** Task 3.
- **Issue:** Failure-path probes showed connection acquisition/cleanup needed to be exception-safe; SQLite's transaction context alone does not close connections.
- **Fix:** Added a small `_connection` context manager that opens a real connection and closes it in `finally`; kept cache exception fallbacks intact.
- **Files modified:** `src/sif/embedding/cache.py`, `tests/unit/embedding/test_cache.py`.
- **Verification:** Normal real-SQL behavior, corruption recovery, connection acquisition failure fallbacks, and 100% cache coverage pass.
- **Commit:** `4b74482`.

**5. [Rule 3 - New test scaffolding] Corrected FTS fixtures and real adapter shapes**
- **Found during:** Tasks 1-3.
- **Issue:** Initial new tests used hyphenated unquoted FTS5 MATCH terms, compared regenerated context timestamps, and assumed sqlite3 methods were monkeypatchable; formatter/linter required focused structural cleanup.
- **Fix:** Used valid token fixtures, asserted persisted fields/IDs, used real adapters/direct real connections, and formatted split helpers without suppressions.
- **Files modified:** the new/modified Task 1-3 test modules.
- **Verification:** All focused acceptance commands, Ruff checks, and full suite pass.
- **Commits:** `0a4adc4`, `777df7e`, `4b74482`.

**Total deviations:** 5 auto-fixed (three production behavior defects, one resource-safety hardening, and new-test scaffolding corrections).
**Impact on plan:** Real SQL fulfilled its purpose by exposing previously unproven defects. No API redesign, coverage suppression, dependency, package install, or architectural change was introduced.

## Issues Encountered

- The canonical full suite emitted 61 warnings, predominantly existing SQLite `ResourceWarning` messages outside this plan's new tests. The suite passed; unrelated legacy warnings were not modified under the scope boundary.
- No authentication gates, package installs, blockers, stubs, skipped tests, unrun verification commands, generator-owned doc edits, or user setup occurred.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The next measured starting point is **90.89% (486 missed / 5337 statements)** with **797 passing tests**. All plan-specific focused thresholds passed: repositories 100% >= 88%, database 100% >= 85%, migrations 92% >= 85%, and cache 100% >= 85%. `requirements.ready-ids` returned `ready: []`; `T-10-1` remains unmarked because the seven-plan shared-ID gate has not released it. `pyproject.toml` remains untouched and the permanent `fail_under=90` gate remains reserved for plan 10-07.

## Self-Check: PASSED

- Required files/classes exist: `tests/unit/database/__init__.py`, `TestRepositoryCoverage`, `TestDatabaseRealSQLite`, `TestMigrationManager`, and `TestEmbeddingCache`.
- Task commits `0a4adc4`, `777df7e`, and `4b74482` are ancestors of HEAD; the measured ledger records exactly 3 commits from `e8c40f0` through `4b74482`.
- Tracer behavior and focused repository coverage reruns passed before expansion; focused repository/database/migration/cache gates passed at 100%, 100%, 92%, and 100%.
- `ruff check src tests`: PASS. `ruff format --check src tests`: PASS (136 files).
- Canonical `env -u FORCE_COLOR NO_COLOR=1 pytest --cov=src/sif`: PASS (797 passed, 0 failed; TOTAL 90.89%).
- `pyproject.toml` unchanged; no business-logic pragmas, coverage exclusions, generator-owned doc edits, new dependencies, or persistent paths outside memory/`tmp_path`.
- Requirement readiness returned `ready: []`; `T-10-1` was not prematurely marked complete.

---
*Phase: 10-raise-pytest-coverage-to-90*
*Completed: 2026-11-05*
