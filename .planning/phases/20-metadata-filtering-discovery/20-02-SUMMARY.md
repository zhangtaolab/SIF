---
phase: 20-metadata-filtering-discovery
plan: "02"
subsystem: database
tags: [sqlite, typed-kv, metadata-backfill, migration, qmd-namespace, bench-fixture]

# Dependency graph
requires:
  - phase: 20-metadata-filtering-discovery
    plan: "01"
    provides: "document_metadata_values/document_metadata_skips tables, typed_rows derivation, per-write kv sync, canonical_metadata_json"
provides:
  - "filterable_metadata qmd.metadata namespace merge (namespace wins on collision) with reserved path/mtime shadowing"
  - "typed_rows full D-07 contract: five caps, eight skip reasons, 64-row bounded skip accounting"
  - "SchemaManager._backfill_metadata_values: resumable index_meta-gated typed-metadata backfill"
  - "_METADATA_VALUES_VERSION='1' / _METADATA_VALUES_VERSION_KEY='metadata_values_version'"
  - "Filterable bench fixture: synthetic bench_category (string) / bench_doc (number) keys"
affects: [20-03, 20-04, 20-05, 22]

# Actuals (#2632) — chars/4 over the realized diff, same scale as the plan estimate.
actuals:
  tokens: 11874
  tasks: 3
  commits: 3

# Measured commit ledger (#3968) — base recorded before the first task commit.
plan_head_before: d61b1f5a7a6fb6aa927091e84e9a166d1af29c74
plan_head_after: 60146bc235a2c27d36906ec8eb6977ae38bff9c1

tech-stack:
  added: []
  patterns:
    - "Derived-view resolution: namespace merge and reserved shadowing never touch parser.py or the checksum"
    - "Bounded skip accounting: one 64-key budget shared by values and skip rows"
    - "Global index_meta marker written only after a complete per-document-transaction pass"
    - "Lazy repository imports inside SchemaManager migrations (PLC0415) to avoid cycles"

key-files:
  created:
    - tests/unit/database/test_metadata_values.py
  modified:
    - src/sif/database/metadata_repository.py
    - src/sif/database/schema.py
    - tests/unit/database/test_schema.py
    - tests/unit/indexing/test_incremental.py
    - tests/support/bench.py

key-decisions:
  - "qmd.metadata resolution drops the qmd key only when qmd.metadata is a mapping; any other qmd shape stays a native key (nested-skipped), per D-19."
  - "Keys are classified in sorted resolved-key order so caps and skip rows are deterministic regardless of namespace merge order."
  - "A list of lists is mixed_array (D-07's explicit parenthetical); an array containing an object is nested. Empty arrays emit neither rows nor skips."
  - "The 64-key document budget is also the 64-row skip budget, capping hostile sidecar amplification."
  - "Backfill reads SELECT id, metadata FROM documents, one short transaction per document; the marker is written last and only after a complete pass."
  - "Pass failures propagate out of create_all (never swallowed) so no host serves filtering from a half-populated store; fresh DBs write the marker immediately."
  - "Bench fixture keys are synthetic and derived through canonical_metadata_json; corpus files, ids, paths, content, checksums, chunks, and vectors are untouched."

patterns-established:
  - "Derivation helper split: _classify_value/_classify_array keep typed_rows under the mccabe-10 complexity limit"
  - "Backfill tests compare an interrupted-then-resumed DB snapshot against a clean-run snapshot"

requirements-completed: [FILT-04]

coverage:
  - id: D1
    description: "The complete typed-metadata derivation contract: qmd.metadata namespace precedence, reserved path/mtime shadowing, five caps, eight per-key skip reasons, and bounded skip accounting."
    requirement: FILT-04
    verification:
      - kind: unit
        ref: "tests/unit/database/test_metadata_values.py#TestDerivation"
        status: pass
    human_judgment: false
  - id: D2
    description: "A resumable, idempotent, announced-once backfill that turns every existing index filterable, gated by the index_meta metadata_values_version marker and safe against half-populated stores."
    requirement: FILT-04
    verification:
      - kind: unit
        ref: "tests/unit/database/test_schema.py#TestMetadataBackfill"
        status: pass
      - kind: unit
        ref: "tests/unit/database/test_schema.py#TestIndexMetaTable"
        status: pass
    human_judgment: false
  - id: D3
    description: "Write-path freshness: a frontmatter-only edit refreshes typed rows in the same command and a body edit leaves no stale row for a dropped key."
    requirement: FILT-04
    verification:
      - kind: unit
        ref: "tests/unit/indexing/test_incremental.py#TestMetadataFastPath::test_frontmatter_only_edit_refreshes_typed_rows"
        status: pass
      - kind: unit
        ref: "tests/unit/indexing/test_incremental.py#TestMetadataFastPath::test_body_edit_removes_typed_rows_for_dropped_keys"
        status: pass
    human_judgment: false
  - id: D4
    description: "The frozen 150-document bench corpus is filterable through synthetic bench_category/bench_doc keys without moving a ranking golden."
    requirement: FILT-04
    verification:
      - kind: unit
        ref: "tests/unit/database/test_metadata_values.py#TestBenchFixtureFilterable"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_bm25.py + tests/unit/search/test_hybrid.py + tests/unit/search/test_bench_fixture.py + tests/unit/cli/test_bench.py"
        status: pass
    human_judgment: false

duration: 9min
completed: 2026-11-15
status: complete
---

# Phase 20 Plan 02: Upgrade-safe typed metadata storage

**Every existing index becomes filterable through a resumable `index_meta`-gated backfill, while the derived view gains qmd.metadata namespace precedence, reserved-name shadowing, all five D-07 caps, and bounded per-key skip accounting — with the 150-document bench corpus filterable without moving a single ranking golden.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-11-15T12:20:04Z
- **Completed:** 2026-11-15T12:28:50Z
- **Tasks:** 3
- **Files modified:** 6 (1 created)

## Accomplishments
- `filterable_metadata` now resolves `qmd.metadata` over native keys (namespace wins on collision), drops the `qmd` block, and shadows reserved `path`/`mtime` names without recording a skip — all in the derived view, never in `parser.py` or the checksum path.
- `typed_rows` implements the full D-07 contract: 64-KB frontmatter cap, 64-key cap, 128-byte key cap, 1024-char string cap, 128-element array cap, and the `nested` / `null` / `mixed_array` / `cap_*` reasons, with skip rows bounded at 64 per document.
- `SchemaManager._backfill_metadata_values` derives typed rows from stored canonical `documents.metadata` in one short transaction per document, announces the one-time pass exactly once via the module logger (stderr), and writes the global `metadata_values_version` marker only after a complete pass. A fresh DB writes it immediately at zero cost; a failed pass propagates out of `create_all`.
- The write path is proven fresh: a frontmatter-only edit updates typed rows in the same command (old value stops matching) and a body edit rebuilds the view with no stale row for a dropped key.
- `build_bench_db` now writes synthetic `bench_category` (4 categories) and `bench_doc` (150 rows) keys through the same canonical-JSON derivation; every existing BM25/hybrid/bench golden still passes.
- Quality gates green: `ruff check src tests`, `ruff format --check src tests`, `ty check src/sif` (0 diagnostics), full `pytest` 2283 passed / 1 skipped at 95.09% coverage (gate 90).

## Task Commits

Each task was committed atomically:

1. **Task 1: Derivation contract (namespace, shadowing, caps, skip accounting)** - `8e9e39c` (feat)
2. **Task 2: Resumable backfill + `index_meta` marker** - `cf03ae6` (feat)
3. **Task 3: Write-path freshness + filterable bench fixture** - `60146bc` (test)

**Plan metadata:** the closing docs commit created after this SUMMARY.

## Files Created/Modified
- `src/sif/database/metadata_repository.py` — namespace merge, reserved shadowing, `_classify_value`/`_classify_array`, cap constants, bounded skips.
- `src/sif/database/schema.py` — module logger, marker constants, `_backfill_metadata_values`, `create_all` call site.
- `tests/unit/database/test_metadata_values.py` (new) — `TestDerivation` (20 tests) and `TestBenchFixtureFilterable`.
- `tests/unit/database/test_schema.py` — reconciled `TestIndexMetaTable`; added `TestMetadataBackfill` (fresh/populated/reopen/interrupted/drop_all).
- `tests/unit/indexing/test_incremental.py` — `_metadata_values` helper plus the two freshness regressions.
- `tests/support/bench.py` — synthetic bench metadata through `canonical_metadata_json` + `MetadataValueRepository`.

## Decisions Made
- **Namespace shape gate:** the `qmd` key is dropped only when `qmd.metadata` is a mapping; any other `qmd` shape remains a native key and is nested-skipped.
- **Deterministic caps:** classification iterates sorted resolved keys so cap boundaries cannot depend on merge order.
- **List-of-lists:** classified `mixed_array` (the D-07 parenthetical) while arrays containing objects are `nested`; empty arrays produce neither rows nor skips.
- **Skip budget = key budget:** the same 64 bound covers both, so a hostile document cannot amplify the skip sidecar.
- **Marker placement:** global `metadata_values_version` in the existing `index_meta` table (never `schema_meta`, never a second kv table).
- **Backfill failure semantics:** exceptions propagate out of `create_all`; there is deliberately no partial-success swallow.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `ty` could not narrow a set-pop element type in `_classify_array`**
- **Found during:** Task 3 (plan-level `ty check src/sif`)
- **Issue:** `element_types.pop()` is typed `str | None` even after the `None`/length guards, so `_typed_row(..., value_type)` failed `ty check` (1 diagnostic).
- **Fix:** Classified the first element and compared every element against it, which narrows `value_type` to `str` with identical semantics.
- **Files modified:** `src/sif/database/metadata_repository.py`
- **Verification:** `ty check src/sif` 0 diagnostics; `TestDerivation` 20 passed; full suite green.
- **Committed in:** `60146bc`

---

**Total deviations:** 1 auto-fixed (blocking).
**Impact on plan:** Type-check-only refactor with identical behavior; no scope change.

## Issues Encountered
- The Task 3 instruction "assert through `MetadataValueRepository` reads on the same connection" has no read API in this plan (`discover` lands in 20-05). The tests read the repository-maintained tables through fresh connections, which proves the same storage contract without adding API surface that 20-05 owns.
- The plan's Task 1 rule ordering lists "a list containing a non-scalar → nested" and "a list of lists → mixed_array"; the two overlap. Implemented the explicit D-07 parenthetical (list-of-lists → `mixed_array`, arrays containing objects → `nested`) and documented it in the docstring.

## Threat Model Compliance
- **T-20-05 (tampering):** all binds are `?` parameters; table/column text is fixed in the module; the backfill only reads stored canonical JSON and binds through the repository.
- **T-20-06 (DoS):** nested/null/mixed/over-cap values are skipped per key; only scalars and flat homogeneous scalar arrays are bound; skips are capped at 64 rows per document; the >64 KB blob path records at most 64 skip rows and no values.
- **T-20-07 (integrity):** the migration announcement goes through `logger.warning` (stderr); tests assert stdout stays empty.
- **T-20-08 (integrity):** per-document short transactions; the marker is written only after a complete pass; a pass failure propagates out of `create_all`.

## Known Stubs
None.

## Threat Flags
None — the shipped surface is covered by the plan's threat register.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- **Ready for 20-03:** typed rows are complete and upgrade-safe; the vector pre-count can trust a store that is either fully backfilled (marker present) or has just completed a pass in this opening.
- **Ready for 20-04:** `compile_match` and the typed store are aligned with the same derivation, so discovery/filter parity has one source of truth.
- **Ready for 20-05:** `MetadataValueRepository.discover` can aggregate over the tables this plan finalized; `TestBenchFixtureFilterable` already provides a 150-document filterable corpus for discovery parity tests.
- **Carry-forward:** qmd's AST is still `[Unreleased]`; re-verify before Phase 22 freezes the MCP schema.

---
*Phase: 20-metadata-filtering-discovery*
*Completed: 2026-11-15*

## Self-Check: PASSED

- All key files exist on disk (source, tests, and this SUMMARY).
- All three task commits (`8e9e39c`, `cf03ae6`, `60146bc`) are ancestors of HEAD.
