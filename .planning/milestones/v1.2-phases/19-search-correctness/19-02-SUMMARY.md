---
phase: 19-search-correctness
plan: 02
subsystem: indexing
tags: [incremental-indexer, metadata-fast-path, convention-migration, index-meta, watcher, embeddings, corr-01]

# Dependency graph
requires:
  - phase: 19-search-correctness
    provides: "19-01 body+canonical-frontmatter checksums, per-file parser dispatch, canonical metadata storage"
provides:
  - "index_meta(key, value) table and IndexMetaRepository.get/set for namespaced index state"
  - "CONVENTION_VERSION = 2 marker with exactly one forced re-parse pass per collection"
  - "D-07 metadata fast path: frontmatter-only edits update the row and keep chunks/embeddings"
  - "IncrementalResult.reindexed_paths/metadata_only; the watch embed leg is driven by reindexed_paths"
  - "migrate <n> progress event rendered as one CLI line"
affects: [19-04 (title-FTS rebuild shares the migration/seeding discipline), 20-metadata-filtering (metadata freshness), 21 (embedder identity reuses index_meta), 22 (MCP parity consumes the same event protocol)]

# Actuals (#2632) — chars/4 over the realized diff (same scale as the plan estimate)
actuals:
  tokens: 15061
  tasks: 3
  commits: 4

commits: 4
plan_head_before: cbbc4ba3300a2f86ed14781e0e16c3446a61be79
plan_head_after: 26aa5ceeab6123322db619ac32d1814a6580ff07

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-collection namespaced marker keys (`convention:<collection_id>`) written only after a zero-failure pass"
    - "One explicit reindex signal (reindexed_paths) replaces checksum-diff change detection for append-only writers"
    - "force and migrating are distinct bypasses of the checksum shortcut; both preserve chunks for unchanged bodies"

key-files:
  created: []
  modified:
    - src/sif/database/schema.py
    - src/sif/database/repositories.py
    - src/sif/indexing/parser.py
    - src/sif/indexing/incremental.py
    - src/sif/indexing/watcher.py
    - src/sif/cli/commands/index.py
    - tests/unit/indexing/test_incremental.py
    - tests/unit/indexing/test_watcher.py
    - tests/unit/database/test_schema.py
    - tests/unit/cli/test_index.py
    - tests/integration/test_incremental_equivalence.py

key-decisions:
  - "reindexed_paths/metadata_only are compare=False so every existing IncrementalResult equality assertion stays valid; metadata counts as `updated` in both update_collection and update_paths."
  - "The marker lives at `convention:<collection_id>` (per collection) and is written after the per-file loop and removal sweep in a short transaction only when failed == 0; an empty collection is marked silently with no migrate event."
  - "--force and migrating stay distinct: both bypass the checksum skip, but both take the metadata fast path when the stored body is byte-identical (RESEARCH Pitfall 15)."
  - "The watch embed leg always calls embed_documents at embed depth (even with an empty reindex signal) so the _pending_retry union still heals failed paths."
  - "The four checksum-snapshot helpers and the unused FileWatcher._doc_repo attribute were removed once result.reindexed_paths became the sole embed-candidate source."
  - "The pre-existing full body-change path now refreshes documents.file_size, matching the fast path (Rule 1 deviation)."

patterns-established:
  - "Migration markers are detection-gated per collection and cleared only on a clean pass, so a partial run is resumable and never masks old-convention data."
  - "Append-only writers (the embed leg) consume an explicit purge signal from the BM25 writer instead of re-deriving change from stored state."

requirements-completed: [CORR-01]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "D-07 metadata fast path: a frontmatter-only edit updates title/metadata/checksum/file_size/mtime and keeps the document's chunk and embedding rows; a body edit still purges them; --force with an unchanged body takes the fast path"
    requirement: CORR-01
    verification:
      - kind: unit
        ref: "tests/unit/indexing/test_incremental.py#TestMetadataFastPath (5 tests: frontmatter edit, body edit, force, mtime-only, reindexed_paths)"
        status: pass
      - kind: unit
        ref: "tests/unit/indexing/test_incremental.py#test_update_paths_purges_embeddings_of_modified_doc (extended with the update_paths metadata case)"
        status: pass
      - kind: integration
        ref: "tests/integration/test_incremental_equivalence.py#test_frontmatter_only_cycle_preserves_chunks_and_moves_title"
        status: pass
    human_judgment: false
  - id: D2
    description: "One forced re-parse migration per collection: index_meta exists and drops cleanly, the marker is written only after a clean pass, exactly one migrate <n> event fires, empty collections are marked silently, failures keep the marker absent, and update_paths never touches it"
    requirement: CORR-01
    verification:
      - kind: unit
        ref: "tests/unit/indexing/test_incremental.py#TestConventionMigration (5 tests: fresh/skip, legacy+preserve, failure-retry, empty, update_paths)"
        status: pass
      - kind: unit
        ref: "tests/unit/database/test_schema.py#TestIndexMetaTable (create_all + drop_all/recreate)"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_index.py#TestRenderIndexEvent#test_migrate_event_renders_one_line_with_count"
        status: pass
      - kind: manual_procedural
        ref: "CLI smoke: temp DB, simulated legacy marker -> `sif index update` printed 'Upgrading index format: reindexing 1 documents once' exactly once (Updated: 1); next run Unchanged: 1 with no notice"
        status: pass
    human_judgment: false
  - id: D3
    description: "The watch embed leg consumes IncrementalResult.reindexed_paths in burst and reconcile paths, so a metadata-only edit produces no duplicate chunk/vector rows and a migrating pass over unchanged bodies leaves counts unchanged"
    requirement: CORR-01
    verification:
      - kind: unit
        ref: "tests/unit/indexing/test_watcher.py#TestEmbedDepth (metadata-only counts, body-edit contiguous/disjoint set, migrating-reconcile no duplication)"
        status: pass
      - kind: unit
        ref: "tests/unit/indexing/test_watcher.py#test_embed_failure_emits_error_continues_and_retries_next_burst (pending-retry contract preserved)"
        status: pass
      - kind: integration
        ref: "tests/integration/test_incremental_equivalence.py#test_frontmatter_only_cycle_preserves_chunks_and_moves_title"
        status: pass
    human_judgment: false

duration: 8min
completed: 2026-11-15
status: complete
---

# Phase 19 Plan 02: Metadata Fast Path, Convention Migration, and Watch Embed Signal Summary

**Frontmatter-only edits now rewrite document rows without touching chunks or vectors, one per-collection `convention:<id>` marker forces exactly one re-parse pass, and the watch embed leg consumes the indexer's explicit reindex signal instead of a checksum diff**

## Performance

- **Duration:** 8 min
- **Started:** 2026-11-15T02:58:44Z
- **Completed:** 2026-11-15T03:07:19Z
- **Tasks:** 3/3
- **Files modified:** 11 (6 source, 5 test)
- **Commits:** 4 (3 tasks + 1 deviation-test)

## Accomplishments

- `index_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)` is created before FTS, dropped by `drop_all`, and exposed through `IndexMetaRepository.get/set` with parameterized SQL — the namespaced home Phase 21 will reuse for embedder identity.
- `_process_file` now discriminates three outcomes beyond the checksum skip: the D-07 metadata fast path (`"metadata"`: title/metadata/checksum/file_size/mtime rewritten, chunks and embeddings preserved), the existing full body-change path (`"updated"`: purge then rewrite), and create (`"added"`).
- `IncrementalResult` carries `reindexed_paths` (added + body-changed only) and `metadata_only`, both `compare=False`; both `update_collection` and `update_paths` count metadata-only work as `updated`.
- D-09 migration: `update_collection` reads `convention:<collection_id>`, emits exactly one `migrate <n>` event when stored documents exist, bypasses the checksum skip for that pass, and writes `CONVENTION_VERSION = 2` only after a zero-failure pass. Empty collections are marked silently; a parse failure leaves the marker absent so the next pass retries.
- `update_paths` (watch bursts, pre-search drift refresh) never reads or writes the marker — proven by a test that patches `IndexMetaRepository.get` to raise.
- The watcher's `_run_burst` and `_run_reconcile` feed `result.reindexed_paths` into the embed leg; the four checksum-snapshot helpers (`_checksums`, `_collection_checksums`, `_changed_since`, `_path_changed`) and the unused `_doc_repo` attribute are gone.
- Regression coverage pins the duplicate-chunk hazard at all three layers: unit slice, watch pipeline at embed depth, and the real CLI integration cycle.
- CLI smoke on a temp DB confirmed the upgrade notice is printed once on a simulated legacy marker and absent on the following pass.

## Task Commits

Each task was committed atomically:

1. **Task 1: Metadata-only fast path end-to-end through IncrementalIndexer (tracer)** - `16865c5` (feat)
2. **Task 2: Per-collection convention marker, forced migration pass, and migrate event** - `2c5a71c` (feat)
3. **Task 3: Watch embed candidates from reindexed_paths + no-duplicate-chunk regression** - `e833d26` (feat)

**Deviation test:** `26aa5ce` (test: assert file_size refresh on the full body-change path)

**Plan metadata:** committed after this SUMMARY (docs: complete plan)

_Note: Task 1 ran as a tracer; the feedback gate re-ran its `<verify>` end-to-end green before expansion._

## Files Created/Modified

- `src/sif/database/schema.py` - `_create_index_meta_table()` before FTS, `index_meta` added to `drop_all`
- `src/sif/database/repositories.py` - `IndexMetaRepository.get(key)` / `.set(key, value)`
- `src/sif/indexing/parser.py` - `CONVENTION_VERSION = 2`
- `src/sif/indexing/incremental.py` - metadata fast path, `migrating` flag, marker read/write, `reindexed_paths`/`metadata_only`, full-path `file_size` refresh
- `src/sif/indexing/watcher.py` - embed candidates from `result.reindexed_paths` in burst and reconcile; checksum-snapshot helpers removed
- `src/sif/cli/commands/index.py` - `migrate` branch in `_render_index_event` (one styled line)
- `tests/unit/indexing/test_incremental.py` - `TestMetadataFastPath` (5), `TestConventionMigration` (5), extended update_paths metadata case
- `tests/unit/indexing/test_watcher.py` - 3 embed-depth regressions (metadata-only counts, body-edit contiguous/disjoint, migrating reconcile)
- `tests/unit/database/test_schema.py` - `TestIndexMetaTable` (create + drop/recreate)
- `tests/unit/cli/test_index.py` - migrate event rendering
- `tests/integration/test_incremental_equivalence.py` - frontmatter-only CLI cycle

## Decisions Made

- `reindexed_paths` and `metadata_only` are `compare=False` so the existing `IncrementalResult(...)` equality assertions across the suite remain valid; `metadata` outcomes count as `updated` in both APIs.
- The marker key is per collection (`convention:<collection_id>`), written after the per-file loop and removal sweep in its own short transaction, only when `failed == 0`. A collection with no stored documents is marked silently (nothing to migrate, no notice).
- `--force` and `migrating` remain separate flags: both bypass the checksum skip, and both take the metadata fast path when the body is unchanged, so an upgrade never purges chunks (Pitfall 15).
- The watch embed leg is called at embed depth even when `reindexed_paths` is empty, preserving the `_pending_retry` healing contract for previously failed paths.
- The `migrate` event keeps the single-space `"code payload"` protocol; the CLI is the only renderer, so MCP/watch hosts style or ignore it without stdout corruption.
- The full body-change path now refreshes `documents.file_size`; the fast path already did, and a stale size would silently break any size-based consumer.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Full body-change path never refreshed documents.file_size**
- **Found during:** Task 1 (metadata fast path implementation)
- **Issue:** The pre-existing full update path rewrote title/content/checksum/mtime but left `file_size` at the pre-edit byte length, so a body edit left a stale size on the row while a create computed it correctly.
- **Fix:** Set `existing.file_size = len(parsed.content.encode("utf-8"))` in the same `with self._conn` block as the other full-path fields, mirroring the fast path.
- **Files modified:** `src/sif/indexing/incremental.py`
- **Verification:** `tests/unit/indexing/test_incremental.py#TestMetadataFastPath#test_body_edit_purges_chunks_and_embeddings` asserts the stored size equals the new parsed body's byte length.
- **Committed in:** `16865c5` (fix) and `26aa5ce` (test)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Required for row consistency between the two update paths; no behavior beyond the intended fast-path contract. No scope creep.

## Issues Encountered

None beyond the deviation above. The plan executed in the intended order; the tracer feedback gate re-ran Task 1's `<verify>` green before expansion.

## Verification Results

- `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/indexing tests/unit/database/test_schema.py tests/unit/cli/test_index.py tests/integration/test_incremental_equivalence.py -x --no-cov` → 200 passed
- `ruff check src tests` → All checks passed
- `ruff format --check src tests` → 195 files already formatted
- `ty check src/sif` → All checks passed
- Full suite (CLAUDE.md gate): `env -u FORCE_COLOR NO_COLOR=1 pytest` → 1916 passed, 1 skipped, coverage 95.22% (fail_under=90)
- CLI migration smoke on a temp DB: fresh pass silent; simulated legacy marker printed the upgrade line exactly once (Updated: 1); next pass `Unchanged: 1` with no notice
- Dependency guard: `git diff --name-only <plan_head_before>..HEAD -- pyproject.toml uv.lock` → 0 files (no dependency or lockfile change)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CORR-01's second half is complete: the checksum convention now has a one-time upgrade contract, and frontmatter edits no longer drop documents out of vector search.
- The watch embed leg's explicit-signal contract is in place before the title-FTS plan (19-04) touches triggers and before any metadata-filtering work that relies on fresh stored metadata.
- `index_meta` is the shared home for Phase 21's embedder identity marker; its namespaced-key convention and clean-pass write discipline are established here.
- No dependency, schema-breaking, or public-interface changes; `pyproject.toml`/`uv.lock` untouched.

---

*Phase: 19-search-correctness*
*Completed: 2026-11-15*

## Self-Check: PASSED

- Key files exist on disk: 11/11 modified files found.
- Commits are ancestors of HEAD: `16865c5`, `2c5a71c`, `e833d26`, `26aa5ce` all found.
- Acceptance criteria re-verified by the targeted suites (200 passed) and the full suite (1916 passed, 1 skipped).
- Evaluation scope resolved for plan `19-02` (commits-only scope).
