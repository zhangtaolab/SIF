---
phase: 21-scale-maintenance-embedder-identity
plan: 03
subsystem: search
tags: [sqlite, context-cache, data-version, invalidation, sentinel, atexit, enrich-results, corr-06]

# Dependency graph
requires:
  - phase: 19-search-correctness
    provides: "single enrich_results attach contract (CORR-05) and two-sided normalize_path matching"
  - phase: 21-scale-maintenance-embedder-identity
    provides: "shared tests/conftest.py fixture culture (21-01 identity reset) and the 21-02 bounded staleness read"
provides:
  - "Per-process normalized context-map cache keyed by resolved main DB path (D-12): one contexts SELECT across attaches"
  - "Repository write generation (bump_context_write_generation/context_write_generation) bumped by every ContextRepository write"
  - "Sentinel PRAGMA data_version + inode-change invalidation with atexit close and reset_context_cache test hook"
  - "Autouse reset_context_cache conftest fixture"
  - "enrich_results(..., vectors_untrusted: bool = False) seam for the 21-04 identity-warning paths"
affects: [21-04, 21-05, 21-06]

# Actuals (#2632) - pairs with the plan's `estimate` (58000 tokens, 2 tasks).
actuals:
  tokens: 8662
  tasks: 2
  commits: 2
plan_head_before: 590e0f6def7ecb6fffa7422bf5957b1350bf8c04
plan_head_after: b03574521b68766553615c9a46eec032cb31579e

tech-stack:
  added: []
  patterns:
    - "Cache keyed by resolved DB path, never a connection object (sqlite3.Connection is neither attribute-able nor weak-referenceable)"
    - "Sample every invalidation trigger before the build so a concurrent write/commit is never recorded as already-seen"
    - "Bypass the cache for :memory: and open transactions; every sentinel failure degrades to the verbatim scan"
    - "Mutable container for process-level state instead of module globals (ruff PLW0603), mirroring _IdentityState"

key-files:
  created: []
  modified:
    - src/sif/search/context_attach.py
    - src/sif/database/repositories.py
    - tests/conftest.py
    - tests/unit/search/test_context_attach.py

key-decisions:
  - "The cache is keyed by the resolved main DB path from PRAGMA database_list, never by a connection object; a :memory: database returns the empty file and bypasses entirely."
  - "The sentinel is a plain sqlite3 connection (timeout 5s, busy_timeout 5000, check_same_thread=False) opened lazily per path, never for :memory:, closed by atexit/reset."
  - "A sentinel that cannot be sampled is closed and dropped and the call bypasses without caching; the next attach opens a fresh sentinel."
  - "Connections with an open transaction bypass the cache (Rule 2 hardening): a map built from a transaction snapshot could freeze stale rows behind an unchanged data_version and could cache uncommitted rows that later roll back."
  - "enrich_results keeps the normal mark_vector_staleness(attach_path_contexts(...)) composition and only overrides vectors_stale when vectors_untrusted is true; no call site changed."

patterns-established:
  - "Invalidation sample-before-build: generation, data_version, and inode are all captured before the contexts scan and stored on the entry"
  - "Conservative invalidation: any commit (query log, chunks, embeddings), not only a contexts write, invalidates the map"
  - "Degrade-never-fail cache: missing/broken sentinel, unreadable database_list, unstattable file, or an open transaction all fall back to the verbatim query"

requirements-completed: [CORR-06]

coverage:
  - id: D1
    description: "Two attachments on one file database issue exactly one contexts SELECT and both attach the same map; repository writes, same-process and cross-process commits, and unrelated commits invalidate it; :memory: re-queries each attach; newest-updated_at and verbatim alias matching are unchanged"
    requirement: CORR-06
    verification:
      - kind: unit
        ref: "tests/unit/search/test_context_attach.py#TestContextMapCache"
        status: pass
    human_judgment: false
  - id: D2
    description: "reset_context_cache closes sentinels and forces a rebuild, inode changes reopen the sentinel, a broken sentinel bypasses without caching, and enrich_results(vectors_untrusted=True) marks every result stale after the normal pass while the two-argument form is unchanged"
    requirement: CORR-06
    verification:
      - kind: unit
        ref: "tests/unit/search/test_context_attach.py#TestContextCacheLifecycle,TestVectorsUntrustedSeam"
        status: pass
    human_judgment: false
  - id: D3
    description: "Full regression suite and quality gates stay green with the configured coverage floor; the contexts schema and the constant query are untouched"
    requirement: CORR-06
    verification:
      - kind: other
        ref: "env -u FORCE_COLOR NO_COLOR=1 pytest (2622 passed, 1 skipped, 95.23%); ruff check; ruff format --check; ty check src/sif"
        status: pass
    human_judgment: false

duration: 7min
completed: 2026-11-16
status: complete
---

# Phase 21 Plan 03: Cached Normalized Context Map and the Untrusted-Vector Enrichment Seam

**A per-process normalized context-map cache keyed by the resolved database path removes the per-query `contexts` scan, invalidated by repository write generations, a sentinel connection's `PRAGMA data_version`, and inode changes while preserving verbatim two-sided matching — plus the `vectors_untrusted` keyword that keeps `enrich_results` the single enrichment owner.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-11-15T16:41:26Z
- **Completed:** 2026-11-15T16:48:20Z (2026-11-16 local)
- **Tasks:** 2
- **Files modified:** 4 (2 source, 2 test)

## Accomplishments

- `src/sif/search/context_attach.py` now caches `{normalize_path(target_id): content}` per process per resolved main database path. Two attachments on the same file database execute exactly one `SELECT target_id, content FROM contexts ...`; the query string, `ORDER BY updated_at`, and two-sided normalization are verbatim.
- Invalidation is proven for all three triggers: a `ContextRepository` write generation (repository `create`/`update`/`update_target`/`delete`, with `delete_orphaned_paths` covered through `self.delete`), a same-process or cross-process commit observed by a dedicated sentinel connection's `PRAGMA data_version`, and an inode change that closes and reopens the sentinel.
- `:memory:` databases bypass the cache (a second connection cannot see their writes), and any sentinel failure — open, setup, or `data_version` sampling — degrades to a fresh verbatim scan without caching the failure. No search can fail because of the cache.
- Every entry samples the generation, `data_version`, and inode **before** building the map, so a write or commit landing mid-build is detected by the next attachment (must-have prohibition preserved).
- `enrich_results(db, results, *, vectors_untrusted=False)` force-marks every result stale after the normal `mark_vector_staleness(attach_path_contexts(...))` composition; existing two-argument call sites and monkeypatched two-argument test doubles are untouched.
- The autouse `reset_context_cache` fixture in `tests/conftest.py` uses the lazy module-lookup pattern and resets both before and after each test, so no test inherits a sentinel or map.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end cached context map with write and commit invalidation** — `75b0def` (feat)
2. **Task 2: Cache lifecycle hardening, test reset hook, and the vectors_untrusted seam** — `b035745` (feat)

**Plan metadata:** the final docs commit captures this SUMMARY plus STATE/ROADMAP/REQUIREMENTS updates.

## Files Created/Modified

- `src/sif/search/context_attach.py` — `_ContextCacheEntry`, `_context_cache`, `_cache_lock`, `_resolved_main_path`, `_build_context_map`, `_open_sentinel`, `_sample_data_version`, `_close_sentinel`, `_drop_entry`, `_lookup_cached`, `_store_entry`, `get_context_map`, `_close_sentinels`, `reset_context_cache`, `enrich_results(vectors_untrusted)`; `attach_path_contexts` now consumes `get_context_map`.
- `src/sif/database/repositories.py` — `_ContextWriteGeneration` container (lock + int), `bump_context_write_generation()`, `context_write_generation()`, bumps in `ContextRepository.create`/`.update`/`.update_target`/`.delete`.
- `tests/conftest.py` — autouse `reset_context_cache` fixture (lazy `sys.modules` lookup, setup + teardown).
- `tests/unit/search/test_context_attach.py` — `TestContextMapCache` (one-SELECT trace pin, generation-only trigger, same/cross-connection commit invalidation, `:memory:` bypass, alias/newest-wins through the cache, sentinel-open fallback, real open failure, unstattable inode), `TestContextCacheLifecycle` (empty-map caching, reset, inode reopen, broken-sentinel bypass), `TestVectorsUntrustedSeam` (flag after the normal pass, two-argument compatibility).

## Decisions Made

- **Path key, not connection key.** `PRAGMA database_list` supplies the resolved main path; `:memory:` reports the empty file and bypasses. This is the only key that works because `sqlite3.Connection` is neither attribute-able nor weak-referenceable.
- **Sample before build.** The generation, sentinel `data_version`, and inode are all sampled before the `contexts` scan and stored on the entry, so a concurrent write or commit cannot be mistaken for already-seen state.
- **Broken sentinel = bypass, no cache.** `_lookup_cached` reports sentinel health alongside the map; a failed `data_version` sample closes and drops the entry and the call returns the fresh scan without caching. The next attach reopens a sentinel.
- **Mutable generation container.** `_ContextWriteGeneration` (lock + integer) satisfies ruff PLW0603 and mirrors 21-01's `_IdentityState`; concurrent bumps cannot lose an increment.
- **Return a copy.** `get_context_map` hands callers `dict(...)`, so no result path can mutate the cached map.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Connections with an open transaction bypass the cache**
- **Found during:** Task 1 (cached context map)
- **Issue:** A map built on a connection inside a transaction is a snapshot. Caching it would (a) freeze stale rows behind an unchanged `data_version` after the snapshot ends and (b) potentially cache uncommitted context rows that later roll back — both violate the T-21-08 freshness mitigation the plan exists to satisfy.
- **Fix:** `get_context_map` returns `_build_context_map(db)` immediately when `db.in_transaction` is true and caches nothing. A bare SELECT in autocommit mode leaves `in_transaction` false, so the normal search path still caches.
- **Files modified:** `src/sif/search/context_attach.py`
- **Verification:** The cache battery still proves one SELECT across attaches; full suite green. A side benefit: MagicMock connections (truthy `in_transaction`) keep the existing mock-based enrichment tests untouched.
- **Committed in:** `75b0def` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** The guard closes a freshness hole in the plan's stated design with no new surface and no behavioral change on the real search path. Every declared file's scope was respected; no collateral test files needed changes.

## Issues Encountered

- The module-level logger resolves to `sif.sif.search.context_attach` because `get_logger(__name__)` prefixes `sif.` — the pre-existing project-wide convention. Debug-log assertions therefore use a root-level `caplog.at_level(logging.DEBUG)` rather than a logger-scoped level.
- No package installs, no schema changes, no new dependencies (`pyproject.toml`/`uv.lock` untouched).

## User Setup Required

None - no external service configuration required.

## Verification

- `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search/test_context_attach.py -x --no-cov` — 29 passed.
- Related suites: `tests/unit/search` + `tests/unit/database` + `tests/unit/cli/test_context.py` — 900 passed.
- `ruff check src tests` — clean; `ruff format --check src tests` — 214 files already formatted; `ty check src/sif` — clean.
- Full suite: `env -u FORCE_COLOR NO_COLOR=1 pytest` — **2622 passed, 1 skipped**, total coverage **95.23%** (fail_under=90).
- Prohibitions:
  - No contexts schema change: `git diff 590e0f6..HEAD -- src/sif/database/schema.py` is empty; `grep -rn "normalized_target_id" src/sif` exits 1.
  - No SQL path pre-filter or JOIN: the constant query is `SELECT target_id, content FROM contexts WHERE context_type = 'path' ORDER BY updated_at`; matching normalizes both sides in Python and the trace test pins the exact statement.
  - Not keyed by connection identity: the key is the resolved main path; `grep -n "id(db)\|id(conn)\|weakref"` finds nothing.
  - Sample-before-build: `_store_entry` samples the generation and the sentinel `data_version` before `_build_context_map` and stores the pre-build inode.

## Known Stubs

None.

## Threat Flags

None - no new network endpoint, auth path, file-access pattern, or trust-boundary surface. The sentinel is a second read-only connection to an already-open local database; T-21-08 (freshness) and T-21-09 (sentinel lifecycle DoS) are the invalidation and close/bypass contracts proven above.

## Next Phase Readiness

- 21-04's identity-warning paths can pass `vectors_untrusted=True` at the existing `enrich_results` call sites; the two-argument form remains the default until then.
- 21-05/21-06 write paths keep using `ContextRepository`, so every context write continues to bump the generation; direct raw-SQL context writes outside the repository would only be caught by `data_version`/inode (documented conservative limitation).
- The cache is an in-process read optimization only; there is no persisted state and no migration.

## Self-Check: PASSED

- FOUND: src/sif/search/context_attach.py
- FOUND: src/sif/database/repositories.py
- FOUND: tests/conftest.py
- FOUND: tests/unit/search/test_context_attach.py
- FOUND: 75b0def
- FOUND: b035745
