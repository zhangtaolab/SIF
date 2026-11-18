---
phase: 19-search-correctness
plan: 01
subsystem: indexing
tags: [parser-dispatch, checksum, frontmatter, canonical-json, incremental-indexer, sqlite, corr-01]

# Dependency graph
requires: []
provides:
  - "canonical_metadata_json() and compute_checksum() — one serialization/checksum contract shared by all parsers and the repository"
  - "Per-file create_parser dispatch inside IncrementalIndexer with TextParser fallback for unknown suffixes"
  - "Create-path documents.checksum stores the parser checksum (body + canonical frontmatter), not a body-only fallback"
  - "DocumentRepository.create/update persist canonical metadata JSON (YAML dates no longer raise TypeError)"
  - "Three leading-`---` .yaml forms parse as whole files through CodeParser"
affects: [19-02 (metadata fast path and migration consume parsed.checksum and reindexed bodies), 20-metadata-filtering (full-frontmatter hash and canonical metadata JSON are its data contract)]

# Actuals (#2632) — same estimateTokens scale as the plan estimate (chars/4 over realized diff)
actuals:
  tokens: 8983
  tasks: 3
  commits: 4

commits: 4
plan_head_before: 999ab9a6144f85b0b251fd19b6e0b21007df9c7a
plan_head_after: 570a3a7093eb6b8c05d970bf1f5f06a5b6a0b27d

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "One canonical serializer is both the persisted metadata form and the checksum input (single source of truth for D-08)"
    - "Recursive mapping-key string coercion makes json.dumps(sort_keys=True, default=str) total over arbitrary frontmatter"
    - "Per-file parser selection happens at the one incremental loop, so every host (CLI/watch/MCP) converges identically"

key-files:
  created: []
  modified:
    - src/sif/core/models.py
    - src/sif/indexing/parser.py
    - src/sif/indexing/incremental.py
    - src/sif/database/repositories.py
    - tests/unit/indexing/test_parser.py
    - tests/unit/indexing/test_parser_checksum.py
    - tests/unit/indexing/test_incremental.py
    - tests/unit/database/test_repositories.py
    - tests/integration/test_embed_idempotency.py

key-decisions:
  - "D-08 implemented as body bytes + NUL + canonical JSON of the full frontmatter (sort_keys, default=str, ensure_ascii=False, compact separators); recursive key coercion was required because default=str applies to values only."
  - "create_parser keeps returning None for unmapped suffixes; the indexer call site applies the TextParser fallback so the factory's tested contract is unchanged."
  - "The create path passes checksum=parsed.checksum; Document.__post_init__'s body-only fallback remains only for constructors that omit it (fixtures)."
  - "An out-of-plan integration assertion was updated to the D-08 convention because it encoded the intentionally retired body-only checksum."

patterns-established:
  - "Canonical-form sharing: persist exactly the string that was hashed, so JSON round trips cannot diverge."
  - "Extension dispatch is tested at both layers: create_parser in isolation and the incremental call site with the TextParser fallback."

requirements-completed: [CORR-01]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "Per-file parser dispatch in IncrementalIndexer: .md -> MarkdownParser, .yaml/.yml -> CodeParser, .txt and unknown suffixes -> TextParser fallback"
    requirement: CORR-01
    verification:
      - kind: unit
        ref: "tests/unit/indexing/test_incremental.py#test_per_file_parser_dispatch_with_text_fallback"
        status: pass
      - kind: unit
        ref: "tests/unit/indexing/test_parser.py#test_factory_selects_parser_by_extension"
        status: pass
    human_judgment: false
  - id: D2
    description: "Metadata-aware checksum (body + canonical full frontmatter) computed by all three parsers and stored on document create"
    requirement: CORR-01
    verification:
      - kind: unit
        ref: "tests/unit/indexing/test_parser_checksum.py (8 tests: typed values, nested mixed keys, Unicode, key order, repeat parses, edits)"
        status: pass
      - kind: unit
        ref: "tests/unit/indexing/test_incremental.py#test_new_file_added_and_document_row_exists"
        status: pass
    human_judgment: false
  - id: D3
    description: "Canonical metadata persistence on create/update; YAML dates store as ISO text with no TypeError, body stays frontmatter-stripped byte-for-byte"
    requirement: CORR-01
    verification:
      - kind: unit
        ref: "tests/unit/database/test_repositories.py#TestDocumentMetadataCanonicalStorage"
        status: pass
      - kind: unit
        ref: "tests/unit/indexing/test_incremental.py#test_yaml_date_frontmatter_indexes_without_type_error"
        status: pass
    human_judgment: false
  - id: D4
    description: "A .yaml/.yml file whose first line is `---` parses as the whole file (closing delimiter, two blocks, no closing delimiter)"
    requirement: CORR-01
    verification:
      - kind: unit
        ref: "tests/unit/indexing/test_parser.py#test_yaml_leading_separator_is_parsed_as_whole_file"
        status: pass
    human_judgment: false

duration: 9min
completed: 2026-11-15
status: complete
---

# Phase 19 Plan 01: Parser Dispatch, Metadata-Aware Checksum, and Canonical Metadata Storage Summary

**Per-file parser dispatch, body+canonical-frontmatter checksums, and YAML-date-safe canonical metadata storage wired through the single incremental loop**

## Performance

- **Duration:** 9 min
- **Started:** 2026-11-15T02:40:50Z
- **Completed:** 2026-11-15T02:49:55Z
- **Tasks:** 3/3
- **Files modified:** 9 (4 source, 5 test)
- **Commits:** 4 (3 tasks + 1 auto-fix)

## Accomplishments

- Added `canonical_metadata_json()` and `compute_checksum()` to `sif.core.models` — one serializer is now both the persisted metadata form and the checksum input, with recursive mapping-key coercion making it total over arbitrary frontmatter (nested mixed keys included).
- All three parsers now compute `ParsedDocument.checksum` over the body plus the canonical full frontmatter; a frontmatter-only edit is visible to change detection while the Markdown body bytes stay identical.
- `IncrementalIndexer` selects `create_parser(file_path) or TextParser()` per file instead of a hardcoded `MarkdownParser`, and the create path now stores `checksum=parsed.checksum`.
- `DocumentRepository.create/update` persist `canonical_metadata_json(metadata)`, fixing the latent YAML-date `TypeError` while keeping `_row_to_document`'s `json.loads` round trip exact.
- `.yaml/.yml` files whose first line is `---` are stored whole (all three verified forms), closing the frontmatter-truncation bug.
- Test contract rewritten and expanded: D-08 checksum matrix, dispatch fixtures across all parser families, and the YAML-date end-to-end fixture.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end parser dispatch + metadata-aware checksum** - `5b964e1` (feat, tracer)
2. **Task 2: Canonical metadata storage on create and update (YAML-date fix)** - `b0ec8cf` (fix)
3. **Task 3: Checksum-contract regression matrix and dispatch fixtures** - `36ec7c9` (test)

**Deviation auto-fix:** `570a3a7` (fix: D-08 convention in update-idempotency integration test)

**Plan metadata:** committed after this SUMMARY (docs: complete plan)

## Files Created/Modified

- `src/sif/core/models.py` - `_canonicalize_metadata`, `canonical_metadata_json`, `compute_checksum`
- `src/sif/indexing/parser.py` - all three parsers use `compute_checksum`; `create_parser` map unchanged
- `src/sif/indexing/incremental.py` - per-file dispatch with `TextParser` fallback; create path passes `parsed.checksum`
- `src/sif/database/repositories.py` - canonical metadata JSON on document create/update
- `tests/unit/indexing/test_parser.py` - D-08 checksum assertions, `.yaml/.yml` factory matrix, three leading-`---` fixtures, `.py`/`.txt`/`.md` dispatch fixtures
- `tests/unit/indexing/test_parser_checksum.py` - rewritten 8-test D-08 matrix (typed values, nested mixed keys, Unicode, key order, determinism, edits)
- `tests/unit/indexing/test_incremental.py` - dispatch-through-indexer test, YAML-date fixture, canonical checksum assertions
- `tests/unit/database/test_repositories.py` - date metadata create/update round trips and byte-equal stored canonical JSON
- `tests/integration/test_embed_idempotency.py` - idempotency assertion updated to the D-08 convention (deviation fix)

## Decisions Made

- One canonical serializer serves both storage and hashing; the persisted string is byte-equal to the hashed string by construction.
- Key coercion recurses through mappings and sequences because `json.dumps(default=str)` cannot handle keys — the serializer must be total, not merely usually sufficient.
- The `TextParser` fallback lives at the indexer call site, leaving `create_parser`'s `None` contract intact (still asserted for `.pdf`).
- The plan's `must_haves.truths` edge behaviors stand as the acceptance contract: CORR-01 was returned `unclassified` by the spec-less edge probe (UNCLASSIFIED-FLAGGED), so these are planner-authored criteria, verified explicitly by the tests above.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Update-idempotency integration test asserted the retired body-only checksum**
- **Found during:** Plan-level full-suite verification (after Task 3)
- **Issue:** `tests/integration/test_embed_idempotency.py::TestUpdateChecksumIdempotency::test_zero_change_rerun_reports_zero_updated` asserted `stored_cs == sha256(stored_content)`, which is exactly the body-only convention D-08 intentionally retired; the full suite failed with one assertion.
- **Fix:** Read the stored metadata and compare against `compute_checksum(stored_content, json.loads(stored_metadata))`; class docstring records that the idempotency contract is unchanged under D-08.
- **Files modified:** `tests/integration/test_embed_idempotency.py`
- **Verification:** `pytest tests/integration/test_embed_idempotency.py -x --no-cov` → 9 passed; full suite green afterwards.
- **Committed in:** `570a3a7`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Required for the full-suite gate; no behavioral change beyond the intended convention migration. No scope creep.

## Issues Encountered

None beyond the deviation above. The plan executed in the intended order; the tracer feedback gate re-ran the Task 1 verify end-to-end green before expansion.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CORR-01's first half is complete: frontmatter-only edits now change the checksum, so Plan 19-02 can implement the metadata fast path and the forced-reindex migration against a stable convention.
- The checksum-convention change means pre-CORR-01 personal-eval saved runs are refused by the Phase 18 corpus fingerprint; the measurement baseline must be recorded after this plan (research constraint recorded for 19-06/19-07/19-09 goldens work).
- No dependency, schema, or public-interface changes; `pyproject.toml`/`uv.lock` untouched.

---
*Phase: 19-search-correctness*
*Completed: 2026-11-15*

## Self-Check: PASSED
