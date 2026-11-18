---
phase: 21-scale-maintenance-embedder-identity
plan: 02
subsystem: database
tags: [sqlite, sqlite-vec, shadow-table, staleness, backfill, index-meta, anti-join, schema-migration]

# Dependency graph
requires:
  - phase: 21-scale-maintenance-embedder-identity
    provides: "21-01 embedder identity/prompt/role surface (independent of this plan's shadow read contract)"
  - phase: 20-metadata-filtering-discovery
    provides: "index_meta marker-gated backfill template (metadata_values_version)"
  - phase: 19-search-correctness
    provides: "single enrich_results attach contract and derived staleness marker"
provides:
  - "embedded_documents shadow table (vec0-conditional) maintained transactionally by VectorSearcher writes/deletes"
  - "embedded_documents_version marker + marker-gated one-time backfill with table-absent force rule"
  - "reconcile_embedded_documents(conn) -> (deleted, inserted) for cleanup/vacuum"
  - "Shadow-based embedded_document_ids / mark_vector_staleness (one display-gate probe + indexed PK lookups)"
  - "Bounded sif status vector-lag anti-join with byte-identical strings"
affects: [21-05, 21-06, 22, 23, 24]

# Actuals (#2632) - pairs with the plan's `estimate` (78000 tokens, 3 tasks).
actuals:
  tokens: 16785
  tasks: 3
  commits: 3
plan_head_before: 9b78aac46eaaad640cbda0e1d1b5cb29470c7563
plan_head_after: c3b16fd46f8b9f6ee5e07fba6953767b0affbdc2

tech-stack:
  added: []
  patterns:
    - "Derived shadow as a transactionally maintained, rebuildable read contract (never independently authoritative)"
    - "vec0-conditional DDL with an explicit None 'do not touch' signal so create_all stays total"
    - "Marker-gated backfill with a table-absent force rule (marker alone is not proof of a populated table)"
    - "Join-to-documents insert is the orphan rule: a deleted document can never be resurrected in the shadow"

key-files:
  created:
    - src/sif/database/maintenance.py
    - tests/unit/database/test_embedded_documents.py
  modified:
    - src/sif/database/schema.py
    - src/sif/search/vector.py
    - src/sif/search/staleness.py
    - src/sif/cli/main.py
    - tests/unit/search/test_staleness.py
    - tests/unit/search/test_hybrid.py
    - tests/unit/search/test_vector.py
    - tests/unit/search/test_bm25.py
    - tests/unit/cli/test_eval.py
    - tests/unit/cli/test_main.py
    - tests/unit/cli/test_status.py
    - tests/unit/cli/test_search.py
    - tests/unit/database/test_schema.py

key-decisions:
  - "The shadow is created only when SELECT vec_version() succeeds; _create_embedded_documents_table returns None on a vec0-free database so the backfill issues no shadow SQL, writes no marker, and create_all never raises."
  - "Backfill force rule: a table that did not pre-exist always triggers the DELETE+INSERT pass even when the marker matches, so a dropped/recreated table cannot stay silently empty behind a stale marker."
  - "Backfill derives through JOIN documents, so persisted orphan vec0 rows never enter the shadow; the marker is written only after the pass, in its own short transaction, and exceptions propagate out of create_all."
  - "mark_vector_staleness keeps the display gate and None degradation byte-identical: one SELECT 1 ... LIMIT 1 probe, then indexed PK lookups; the old vec0 batching rule now applies only to get_all_embedded_chunk_ids."
  - "reconcile_embedded_documents does not commit; the caller owns the transaction. Both statements scan by design (maintenance only)."
  - "Status keeps embedded_document_ids as the presence/degradation gate and computes the lagging count with one NOT EXISTS anti-join; all four strings remain byte-identical."

patterns-established:
  - "Shadow writer rule: every insert joins documents; delete by document id in the caller's transaction"
  - "Migration total-ness: an explicit None signal lets a conditional schema surface be a no-op rather than an error"
  - "Reader rule: display-gate probe + primary-key lookups on the search path; scans only in maintenance/backfill"

requirements-completed: [CORR-06]

coverage:
  - id: D1
    description: "Vector writes/deletes maintain exactly one embedded_documents row per existing document in the caller's transaction; orphan vec0 rows never create shadow rows; staleness marking is one display-gate probe plus indexed PK lookups with no document_embeddings scan"
    requirement: CORR-06
    verification:
      - kind: unit
        ref: "tests/unit/search/test_staleness.py#TestShadowWritePath,TestMarkVectorStaleness.test_marking_is_bounded_by_the_shadow_not_a_vec0_scan"
        status: pass
    human_judgment: false
  - id: D2
    description: "Fresh vec0 databases create the shadow and write the marker at zero cost; legacy indexes backfill exactly the distinct existing documents once with one warning; a dropped table forces a rebuild; a vec0-free database completes create_all with no shadow DDL, no marker, and no error"
    requirement: CORR-06
    verification:
      - kind: unit
        ref: "tests/unit/database/test_embedded_documents.py#TestFreshDatabase,TestLegacyBackfill,TestVec0FreeDatabase"
        status: pass
    human_judgment: false
  - id: D3
    description: "reconcile_embedded_documents deletes shadow rows whose document or embeddings are gone, inserts missing rows only for documents that still exist, returns (deleted, inserted), and leaves the commit to the caller"
    requirement: CORR-06
    verification:
      - kind: unit
        ref: "tests/unit/database/test_embedded_documents.py#TestReconcileEmbeddedDocuments"
        status: pass
    human_judgment: false
  - id: D4
    description: "sif status vector-lag renders n/a, none (no vectors indexed), 1 document, and N documents byte-identically from one indexed anti-join, and the status wrapper still degrades probe failures to n/a"
    requirement: CORR-06
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_main.py#TestVectorLagText; tests/unit/cli/test_status.py#TestVectorLag"
        status: pass
    human_judgment: false
  - id: D5
    description: "Full regression suite and quality gates stay green with the configured coverage floor"
    requirement: CORR-06
    verification:
      - kind: other
        ref: "env -u FORCE_COLOR NO_COLOR=1 pytest (2603 passed, 1 skipped, 95.32%); ruff check; ruff format --check; ty check src/sif"
        status: pass
    human_judgment: false

duration: 18min
completed: 2026-11-16
status: complete
---

# Phase 21 Plan 02: Transactional `embedded_documents` Shadow and Bounded Staleness Reads

**A transactionally maintained, rebuildable `embedded_documents` shadow replaces both per-query `document_embeddings` scans: the vector writer keeps it exact, schema init backfills it once, and staleness marking plus `sif status` read it through indexed primary-key probes and one anti-join with byte-identical output.**

## Performance

- **Duration:** 18 min
- **Started:** 2026-11-15T16:20:21Z
- **Completed:** 2026-11-15T16:38:04Z (2026-11-16 local)
- **Tasks:** 3
- **Files modified:** 15 (13 modified, 2 created)
- **Commits:** 3 task commits

## Accomplishments

- `VectorSearcher` detects the shadow once in `__init__` (`_shadow_available`, a plain bool) and maintains it inside every write path: single insert, batch insert (one row per distinct existing document via one `executemany`), and document delete. Every insert joins `documents`, so an orphan vec0 row can never resurrect a deleted document in the shadow; no method adds a commit — callers own the transaction.
- `mark_vector_staleness` now runs one display-gate probe (`SELECT 1 FROM embedded_documents LIMIT 1`) plus indexed primary-key lookups per result; `embedded_document_ids` reads the shadow. The display gate (empty shadow ⇒ unmarked), `None` degradation (shadow/vec0 absent ⇒ unmarked), and the single `enrich_results` attach contract are unchanged. The old vec0 batching rule now applies only to `get_all_embedded_chunk_ids`.
- `SchemaManager._create_embedded_documents_table` creates the shadow only when sqlite-vec is present and returns `None` otherwise, making `create_all` total on a vec0-free database: no shadow DDL, no marker, no raise, and no statement against the absent table.
- `SchemaManager._backfill_embedded_documents` is the Phase-20-template migration: clear the derived table, derive every distinct existing document through `JOIN documents`, warn once with the document count, then write `index_meta['embedded_documents_version'] = '1'` only after a complete pass. A table that did not pre-exist forces the pass even when the marker survives.
- `drop_all` drops `embedded_documents` before `documents`; a populated database with `PRAGMA foreign_keys = ON` drops cleanly.
- New `src/sif/database/maintenance.py` provides `reconcile_embedded_documents(conn) -> (deleted, inserted)` for cleanup/vacuum: delete rows whose document or embeddings are gone, insert missing rows only for documents that still exist. No commit; scans are maintenance-only.
- `_vector_lag_text` keeps `embedded_document_ids` as the presence/degradation gate and computes the lagging count with one `SELECT COUNT(*) ... WHERE NOT EXISTS` anti-join; the `n/a`, `none (no vectors indexed)`, `1 document`, and `N documents` strings are byte-identical to the pre-change output.

## Task Commits

Each task was committed atomically:

1. **Task 1: Shadow write/read path — VectorSearcher maintenance and shadow-based staleness** — `26c2407` (feat)
2. **Task 2: Shadow DDL, marker-gated backfill, `drop_all` ordering, reconcile helper** — `cf9f709` (feat)
3. **Task 3: Bounded status vector-lag via shadow anti-join** — `c3b16fd` (feat)

**Plan metadata:** the final docs commit captures this SUMMARY plus STATE/ROADMAP/REQUIREMENTS updates.

## Files Created/Modified

- `src/sif/search/vector.py` — `_shadow_available` detection, `_SHADOW_INSERT_SQL`/`_SHADOW_DELETE_SQL`, shadow maintenance in `_add_embedding_vec`, `add_embeddings_batch`, `delete_embeddings_by_document`.
- `src/sif/search/staleness.py` — shadow-based `embedded_document_ids`; display-gate + PK-probe `mark_vector_staleness`; docstring distinguishing the vec0 batching rule from the shadow PK.
- `src/sif/database/schema.py` — `_EMBEDDED_DOCUMENTS_VERSION` constants, `_create_embedded_documents_table` (`bool | None`), `_backfill_embedded_documents`, `create_all` ordering, `drop_all` entry.
- `src/sif/database/maintenance.py` (new) — `reconcile_embedded_documents` with constant SQL strings and the caller-owns-the-transaction contract.
- `src/sif/cli/main.py` — `_vector_lag_text` anti-join rewrite.
- `tests/unit/database/test_embedded_documents.py` (new) — 11-test fresh/legacy/vec0-free/reconcile battery.
- `tests/unit/search/test_staleness.py` — shadow fixture, writer battery, bounded-read recording test, orphan rule, missing-shadow degradation, migrated E2E.
- `tests/unit/database/test_schema.py` — widened fresh-`index_meta` assertion (allows `embedded_documents_version`, forbids an identity row).
- `tests/unit/cli/test_main.py` — direct four-state `_vector_lag_text` battery against a real in-memory schema.
- `tests/unit/cli/test_status.py` — `TestVectorLag` migrated to the anti-join count and extended with the singular state and no-count assertions.
- `tests/unit/search/test_hybrid.py` — staleness fixture deletes through `VectorSearcher` so the shadow stays truthful.
- `tests/unit/cli/test_eval.py` — `_delete_embeddings` routed through `VectorSearcher.delete_embeddings_by_document`.
- `tests/unit/search/test_vector.py`, `tests/unit/search/test_bm25.py`, `tests/unit/cli/test_search.py` — call-count/enrichment fixtures adapted to the new constructor probe and display-gate probe.

## Decisions Made

- **`None` as the vec0-free signal.** `_create_embedded_documents_table` returns `None` when `SELECT vec_version()` raises, so the backfill can distinguish "no shadow by design" from "shadow absent but should exist"; this is what makes `create_all` total rather than exception-driven.
- **Marker + pre-existence, not marker alone.** A matching marker is honoured only when the table pre-existed; otherwise the pass always runs. This closes the dropped-table-behind-a-stale-marker hole without a new invariant.
- **Derived-table rebuild is DELETE+INSERT.** It is idempotent, excludes orphans by construction, and keeps the warning's count honest (total rows of a freshly cleared table).
- **Per-result PK probes are correct because the shadow PK is an ordinary index.** The historical one-scan batching rule was a vec0-metadata limitation, not a general SQLite rule; the docstring now states exactly where each rule applies.
- **Reconcile returns counts and never commits.** cleanup/vacuum can compose it inside their existing transaction and report repair totals; it is a helper here, wiring belongs to the maintenance-command plan (21-06).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Collateral test updates for the constructor shadow probe**
- **Found during:** Task 1 (shadow write/read path)
- **Issue:** `VectorSearcher.__init__` now issues a `sqlite_master` probe. Exact-call-count and `side_effect`-list tests in `tests/unit/search/test_vector.py` assumed only the `vec_version()` probe; enrichment fixtures in `tests/unit/search/test_bm25.py` and `tests/unit/cli/test_search.py` modelled the old two-statement staleness read and overwrote crafted `vectors_stale` flags once the display-gate probe returned a truthy `MagicMock`.
- **Fix:** Updated the constructor-call indices/counts, isolated vec-insert assertions from the shadow write, and configured the mock connections as an empty shadow (the display gate) where the test's subject is enrichment/formatting.
- **Files modified:** `tests/unit/search/test_vector.py`, `tests/unit/search/test_bm25.py`, `tests/unit/cli/test_search.py`
- **Verification:** Targeted suites and the full 2603-test suite pass.
- **Committed in:** `26c2407` (Task 1 commit)

**2. [Rule 3 - Blocking] Status assertions live in `test_status.py`, not `test_main.py`**
- **Found during:** Task 3 (bounded status vector-lag)
- **Issue:** The plan named `tests/unit/cli/test_main.py` as the home of the existing status assertions; the actual `TestVectorLag` battery (and the mocked status harness) lives in `tests/unit/cli/test_status.py`. Migrating only `test_main.py` would have left four tests failing against the removed `SELECT id FROM documents` iteration.
- **Fix:** Migrated and extended `TestVectorLag` in `test_status.py` (singular/plural/no-vectors/n-a + anti-join SQL assertions), and added the plan's four-state direct helper battery to `test_main.py` (`TestVectorLagText`) so both the presentation contract and the helper are pinned.
- **Files modified:** `tests/unit/cli/test_status.py`, `tests/unit/cli/test_main.py`
- **Verification:** `pytest tests/unit/cli/test_main.py tests/unit/cli/test_status.py` — 38 passed; full suite green.
- **Committed in:** `c3b16fd` (Task 3 commit)

**3. [Rule 3 - Blocking] Temporary test-only shadow DDL removed when production DDL landed**
- **Found during:** Task 2 (schema DDL)
- **Issue:** Task 1's tests needed the shadow table before `SchemaManager` owned it; the fixture built it with raw `CREATE TABLE IF NOT EXISTS`.
- **Fix:** Removed the temporary DDL from `tests/unit/search/test_staleness.py` and `tests/unit/search/test_hybrid.py` once `create_all` created the table, so the fixtures exercise the production schema shape.
- **Files modified:** `tests/unit/search/test_staleness.py`, `tests/unit/search/test_hybrid.py`
- **Verification:** Full suite green after Task 2.
- **Committed in:** `cf9f709` (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (3 blocking)
**Impact on plan:** All updates are test-only collateral forced by the new schema surface; no production scope was added. The plan's declared file list under-counted the test files that exercise `VectorSearcher` construction and the status command.

## Issues Encountered

- The PLR0915 statement limit in the existing end-to-end staleness test was briefly tripped by the temporary fixture DDL; removing that DDL when production DDL landed resolved it without a suppression.

## User Setup Required

None - no external service configuration required. No dependency was added (`pyproject.toml`/`uv.lock` untouched); no new Settings or CLI commands, so the `make docs-generate` gate has nothing to regenerate.

## Verification

- `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/database/test_embedded_documents.py tests/unit/database/test_schema.py tests/unit/search/test_staleness.py tests/unit/cli/test_main.py -x --no-cov` — 92 passed.
- Per-task gates: staleness 20 passed; hybrid + eval 118 passed; new shadow schema battery 11 passed; schema battery 38 passed; status/main 38 passed.
- `ruff check src tests` — clean; `ruff format --check src tests` — 214 files already formatted; `ty check src/sif` — clean.
- Full suite: `env -u FORCE_COLOR NO_COLOR=1 pytest` — **2603 passed, 1 skipped**, total coverage **95.32%** (fail_under=90).
- Prohibitions:
  - Staleness remains derived: no persisted per-result stale flag or schema change; the shadow stores document ids only and is rebuildable.
  - No search-path scan: `grep -n "SELECT document_id FROM document_embeddings" src/sif/search/staleness.py` finds nothing; the recording-connection test asserts only the display gate + PK lookups during marking. The remaining full vec0 scan is `get_all_embedded_chunk_ids` (resume).
  - Orphans cannot resurrect documents: Task 1's writer battery and Task 2's backfill/reconcile tests all assert orphan exclusion.
  - The shadow is not independently authoritative: both backfill and reconcile derive every row from `documents` + `document_embeddings`.
  - Vec0-free no-op: `TestVec0FreeDatabase` proves `create_all` completes with no shadow DDL/marker and no statement against the absent table.

## Known Stubs

None.

## Threat Flags

None - no new network endpoint, auth path, file-access pattern, or trust-boundary surface was introduced. The threat mitigations T-21-05 (shadow tampering) and T-21-06 (search-path DoS) are the transaction/join and bounded-read contracts proven above.

## Next Phase Readiness

- The shadow is now the read contract for the streaming writer (21-05): its per-document transaction must keep calling these `VectorSearcher` methods, which maintain the shadow automatically.
- `reconcile_embedded_documents` is ready to be wired into `sif cleanup` and `sif index vacuum` by the maintenance-command plan (21-06), which owns those commands.
- Residual accepted limitation: raw-SQL test fixtures or third-party scripts that write vec0 rows directly bypass the shadow until a reconcile runs; production writers are funneled through `VectorSearcher`.
- No blockers.

## Self-Check: PASSED

- FOUND: src/sif/database/maintenance.py
- FOUND: tests/unit/database/test_embedded_documents.py
- FOUND: 26c2407
- FOUND: cf9f709
- FOUND: c3b16fd

