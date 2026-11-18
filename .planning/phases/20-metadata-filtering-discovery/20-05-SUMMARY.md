---
phase: 20-metadata-filtering-discovery
plan: "05"
subsystem: discovery
tags: [sqlite, metadata-discovery, typed-kv, click, rich, mcp, pydantic, generated-docs]

# Dependency graph
requires:
  - phase: 20-metadata-filtering-discovery
    plan: "01"
    provides: "FilterNode/parse_filter/parse_match, compile_filter/compile_match, typed kv store, count_matching_documents"
  - phase: 20-metadata-filtering-discovery
    plan: "02"
    provides: "fully backfilled typed store with qmd.metadata resolution, reserved shadowing, and skip accounting"
  - phase: 20-metadata-filtering-discovery
    plan: "03"
    provides: "sqlite-vec-free integration battery scaffold and the pre-RRF filter contract"
  - phase: 20-metadata-filtering-discovery
    plan: "04"
    provides: "the shared CLI/MCP filter error mapping and the four-tool MCP registry"
provides:
  - "MetadataValueRepository.discover: filter-aware keys/types/values, exact remainders, skippedKeys, and the D-20 path/mtime builtIns section"
  - "src/sif/cli/filter_options.py shared CLI adapters (parse_filter_option/parse_match_option)"
  - "sif collection metadata [NAME] with --filter/--match/--min-count/--sort/--limit/--value-limit/--json"
  - "MCP MetadataInput/MetadataOutput + summary models, the frozen Phase 22 contract including builtIns"
  - "MetadataToolHandler registered in create_default_tools; SearchBackend.metadata"
  - "TestDiscoveryParity proving both directions of the D-16 invariant without sqlite-vec"
affects: [22]

# Actuals (#2632) — chars/4 over the realized diff, same scale as the plan estimate.
actuals:
  tokens: 21029
  tasks: 3
  commits: 3

# Measured commit ledger (#3968) — base recorded before the first task commit.
plan_head_before: 4054b06917b38f36ba95aa262f4835b65490f4c7
plan_head_after: 6cb63befb78e1f757c04d103baae75280a1f3161

tech-stack:
  added: []
  patterns:
    - "One region CTE per discovery query: collection scope + caller-compiled filter; match narrows entries only"
    - "Median via ROW_NUMBER()/COUNT(*) OVER with integer-division positions; midpoint averaged in Python"
    - "Batched page-key aggregates: one type-split query, one values GROUP BY ... HAVING min_count, one median query"
    - "Built-ins computed from the documents columns over the same region, never from the typed store"
    - "Shared CLI JSON-option adapter used by search/vsearch/query and collection metadata"
    - "MCP frozen envelope serialized with model_dump(exclude_none=True)"

key-files:
  created:
    - src/sif/cli/filter_options.py
  modified:
    - src/sif/database/metadata_repository.py
    - src/sif/cli/commands/search.py
    - src/sif/cli/commands/collection.py
    - src/sif/mcp/protocol.py
    - src/sif/mcp/handlers.py
    - src/sif/mcp/backend.py
    - tests/unit/database/test_metadata_values.py
    - tests/integration/test_metadata_filtering.py
    - tests/unit/cli/test_collection.py
    - tests/unit/mcp/test_integration.py
    - tests/unit/mcp/test_backend.py
    - docs/cli-reference.md

key-decisions:
  - "discover takes already-compiled fragments; absent filter/match is passed as None, never compile_*('', [])'s empty fragment, so filteredDocuments appears exactly when a filter was supplied."
  - "documents is the collection-scope denominator; filteredDocuments (filter-aware) is the coverage denominator. The filter narrows every count including the built-in document counts, never documents."
  - "builtIns is a fixed path-then-mtime list computed from documents.path/mtime over the same region: no inline values, remainingValues == distinctValues, invariant under match, excluded from keys/totalKeys/remainingKeys (D-03/D-20)."
  - "Type entries order string, number, boolean; value entries order documents DESC then str(value) ASC; key window orders documents DESC, key ASC by default (key ASC for --sort value)."
  - "Median uses integer-division positions ((total+1)/2, (total+2)/2); min/max come from the type-split aggregate over all numeric rows, so min_count does not narrow a range."
  - "CLI --json prints the raw discover dict, so no-filter output omits filteredDocuments exactly like MCP's exclude_none dump; the table marks built-ins with Source=built-in and renders built-in value windows as '0 of N'."
  - "MCP envelope fields keep camelCase with trailing # noqa: N815; annotated pydantic fields needed no A003 suppression (ruff reports none)."
  - "SearchBackend.metadata names its argument filter_node (ruff A002) and returns the raw dict; the handler converts it to MetadataOutput so validation lives at one boundary."
  - "parse_match semantic errors still render with the shared validator's 'filter.<path>' prefix (20-01's shipped convention); only the CLI's invalid-JSON message names 'match'."
  - "The metadata handler parses filter/match explicitly to return a controlled isError; invalid input never reaches the JSON-RPC INVALID_PARAMS path."

patterns-established:
  - "Discovery region CTE shared by every aggregate; match appended only to frontmatter-entry queries"
  - "Exact window accounting: window + remainder == total for keys and per-type values, asserted at and beyond the boundary"
  - "Built-in rows always precede frontmatter rows in the table; JSON and MCP carry the same builtIns list"

requirements-completed: [FILT-05]

coverage:
  - id: D1
    description: "One repository aggregate reports filter-aware keys, per-type splits, value windows, exact remainders, skip counts, and the two reserved built-in fields from the same typed store the filters read."
    requirement: FILT-05
    verification:
      - kind: unit
        ref: "tests/unit/database/test_metadata_values.py#TestDiscovery"
        status: pass
    human_judgment: false
  - id: D2
    description: "The discovery invariant is proven in both directions, including the non-indexable-key case and the built-ins' own filterability, on a host without sqlite-vec."
    requirement: FILT-05
    verification:
      - kind: integration
        ref: "tests/integration/test_metadata_filtering.py#TestDiscoveryParity"
        status: pass
    human_judgment: false
  - id: D3
    description: "`sif collection metadata [NAME]` ships all seven options, renders built-ins first with a Source column, emits the envelope under --json, and validates filter/match before the database opens."
    requirement: FILT-05
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_collection.py#TestCollectionMetadata"
        status: pass
      - kind: unit
        ref: "make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md"
        status: pass
    human_judgment: false
  - id: D4
    description: "The MCP `metadata` tool is registered, its input/output schema is the frozen Phase 22 envelope including builtIns, and invalid filter/match are tool execution errors rather than protocol errors."
    requirement: FILT-05
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_backend.py#TestMetadataToolHandler + TestMetadataInputValidation + TestMetadataToolHandlerSchema + TestSearchBackendMetadata"
        status: pass
      - kind: unit
        ref: "tests/unit/mcp/test_integration.py#TestStdioIntegration::test_stdio_full_lifecycle"
        status: pass
      - kind: unit
        ref: "tests/unit/mcp/test_integration.py#TestHTTPIntegration::test_http_full_lifecycle"
        status: pass
    human_judgment: false
  - id: D5
    description: "Unfiltered behavior is unchanged: existing search filters, the four pre-existing tools, and generated configuration docs are untouched."
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_search_filter.py + tests/unit/cli/test_search.py"
        status: pass
      - kind: unit
        ref: "env -u FORCE_COLOR NO_COLOR=1 python -m pytest (full suite)"
        status: pass
    human_judgment: false

duration: 14min
completed: 2026-11-15
status: complete
---

# Phase 20 Plan 05: Metadata discovery across repository, CLI, and MCP

**Agents no longer guess metadata keys: one repository aggregate over the same typed store the filters read reports filter-aware keys, per-type splits, exact window remainders, and numeric min/median/max, with `path`/`mtime` as a fixed built-in section — surfaced as `sif collection metadata` and the MCP `metadata` tool whose envelope is now frozen for Phase 22.**

## Performance

- **Duration:** 14 min
- **Started:** 2026-11-15T13:12:27Z
- **Completed:** 2026-11-15T13:26:13Z
- **Tasks:** 3
- **Files modified:** 13 (1 created, 1 generated)

## Accomplishments
- `MetadataValueRepository.discover` returns the frozen D-15/D-20 envelope: `documents` (collection scope only), `filteredDocuments` (only when a filter is supplied), `totalKeys`/`remainingKeys`, `skippedKeys`, a two-entry `builtIns` list (`path` then `mtime`, computed from the `documents` columns over the same filter-aware region), and per-key `types[]` with document counts, per-type distinct values, windowed values with exact remainders, and numeric `range` objects.
- Window arithmetic is exact in both directions: the key window plus `remainingKeys` equals `totalKeys`, and each type's value window plus `remainingValues` equals its post-`min_count` distinct count, asserted at and beyond the boundary.
- Median is computed with `ROW_NUMBER()`/`COUNT(*) OVER` and integer-division positions; a three-row cohort yields the middle value, a four-row cohort the midpoint of positions two and three, and array elements each count as a numeric row.
- Mixed-type keys split into one entry per type with a `range` only on the number entry; reserved frontmatter names are shadowed (no key, no skip row) while the built-ins still appear.
- `sif collection metadata [NAME]` ships on the existing `collection` group with all seven options, a `Source` column that renders the two built-in rows first, `... N more keys` footer, and `--json` printing only the envelope. Invalid `--filter`/`--match` fail before `open_initialized_database`.
- The shared CLI adapters (`src/sif/cli/filter_options.py`) now serve both the search commands and discovery, so there is exactly one JSON/AST error mapping.
- The `metadata` MCP tool is registered as the fifth tool with a hand-written `input_schema` synced to `MetadataInput`; invalid filter/match return `ToolsCallResult(isError=True)` inside a successful JSON-RPC envelope, and no-filter calls omit `filteredDocuments` (proving `None`, never the compiler's empty fragment).
- `TestDiscoveryParity` proves reported ⇒ filterable and filterable ⇒ reported on a repository-built corpus that needs no sqlite-vec, including the nested-key document (one `skippedKeys` row, no key entry, still filterable by its other keys) and the built-ins' own `path` prefix / `mtime` range filterability.
- Quality gates green: `ruff check src tests`, `ruff format --check src tests`, `ty check src/sif` (0 diagnostics), full `pytest` 2388 passed / 1 skipped at 95.26% coverage (gate 90); `make docs-generate` leaves a clean diff.

## Task Commits

Each task was committed atomically:

1. **Task 1: Discovery aggregate over the typed store** - `6159a90` (feat)
2. **Task 2: `sif collection metadata` CLI command** - `5329a1f` (feat)
3. **Task 3: MCP `metadata` tool + frozen Phase 22 envelope + docs** - `6cb63be` (feat)

**Plan metadata:** the closing docs commit created after this SUMMARY.

## Files Created/Modified
- `src/sif/database/metadata_repository.py` — `_DiscoveryQuery`, `_collection_clause`, `_key_entries`, and `MetadataValueRepository.discover` plus `_count`/`_key_aggregates`/`_medians`/`_built_in_entries`/`_mtime_median`.
- `src/sif/cli/filter_options.py` (new) — `parse_filter_option`/`parse_match_option`, the one CLI JSON/AST adapter.
- `src/sif/cli/commands/search.py` — `_parse_filter_option` delegates to the shared adapter (behavior unchanged).
- `src/sif/cli/commands/collection.py` — `collection_metadata` command plus table/range/value-window renderers.
- `src/sif/mcp/protocol.py` — `MetadataRange`, `MetadataValueSummary`, `MetadataTypeSummary`, `MetadataKeySummary`, `MetadataInput`, `MetadataOutput` (camelCase contract, `builtIns` included).
- `src/sif/mcp/handlers.py` — `MetadataToolHandler`, registry entry, `parse_match` import.
- `src/sif/mcp/backend.py` — `SearchBackend.metadata` compiling only supplied predicates and resolving collection names.
- `tests/unit/database/test_metadata_values.py` — `_seed_document` mtime support and `TestDiscovery` (14 tests).
- `tests/integration/test_metadata_filtering.py` — sqlite-vec-free `discovery_db` corpus and `TestDiscoveryParity` (4 tests).
- `tests/unit/cli/test_collection.py` — `TestCollectionMetadata` (7 tests: table, JSON, filter, match, windows, unknown NAME, pre-open validation).
- `tests/unit/mcp/test_integration.py` — five-tool assertions in stdio and HTTP plus a metadata `tools/call` envelope check.
- `tests/unit/mcp/test_backend.py` — 17 tests across input validation, schema sync, handler behavior, protocol-error taxonomy, and backend scoping.
- `docs/cli-reference.md` — regenerated (`collection metadata` section), never hand-edited.

## Decisions Made
- **Denominator split.** `documents` stays the collection-scope denominator; a supplied filter adds `filteredDocuments` and narrows every other count (including the built-in document counts) without moving `documents` — asserted in both the unit and CLI batteries.
- **Built-in construction.** `builtIns` is a fixed `path`-then-`mtime` list derived from `documents.path`/`documents.mtime` over the same region CTE; it reports `values: []` with `remainingValues == distinctValues`, is invariant under `match`, and is never in `keys`/`totalKeys`.
- **Window ordering and type order.** Values sort by `documents DESC, str(value) ASC`; type entries use the fixed string → number → boolean order; keys default to `documents DESC, key ASC` and switch to `key ASC` for `--sort value`.
- **Range vs `min_count`.** `min_count` narrows values and `distinctValues`, not the numeric `range`, which is computed over all numeric rows of the type.
- **Shared adapter boundary.** `search.py::_parse_filter_option` now delegates to `src/sif/cli/filter_options.py`, so search and discovery cannot drift in JSON/AST error handling.
- **MCP schema casing.** The envelope keeps qmd's camelCase verbatim with `# noqa: N815`; annotated pydantic fields triggered no A003 diagnostic, so no unused suppressions were added.
- **`filter_node` naming.** The backend argument is `filter_node` (ruff A002); the pydantic field stays `filter`, matching the 20-04 precedent.
- **Match error spelling.** `parse_match` violations render with the shared validator's `filter.<path>` prefix (20-01's shipped convention); only invalid JSON names `match`.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- The shared `FilterValidationError` renders `filter.<path>` for both `parse_filter` and `parse_match`, so a semantic `--match` error is `filter.`-prefixed while an invalid-JSON `--match` error is `match:`-prefixed. Tests pin the actual shipped convention rather than introducing a second error formatter.
- SQLite's `COUNT(DISTINCT ...)` on `mtime` and the median window both run over the region CTE; the two fixed built-in queries (one count/aggregate query plus one median query) satisfy the plan's query budget without depending on the key window.

## Threat Model Compliance
- **T-20-17 (tampering):** every operand and window size is a bound parameter; key lists are `?, ` placeholder runs; only `compile_filter`/`compile_match` produce predicates.
- **T-20-18 (DoS):** the key window defaults to 50 and each type's value window to 10, with exact remainders; aggregates are batched to the page's keys; no unbounded mode exists.
- **T-20-19 (integrity):** `--json` prints only the envelope and table mode prints only the table plus the remainder footer; no notice text enters either stream.
- **T-20-20 (information disclosure):** `documents` is the scope denominator, `filteredDocuments` appears only with a filter, skipped keys are counted but never listed as filterable, and `keys`/`builtIns` are disjoint.
- **T-20-SC:** no dependency was added or installed.

## Known Stubs
None.

## Threat Flags
None — the shipped surface is covered by the plan's threat register (T-20-17..20).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- **Frozen for Phase 22:** `MetadataInput`/`MetadataOutput` (including the additive `builtIns` list) are the cross-phase contract; Phase 22 surfaces them unchanged. The tool is already registered as the fifth tool, so Phase 22's registration parity has no discovery gap.
- **Discovery invariant is executable:** `TestDiscoveryParity` runs without sqlite-vec and can be extended by later phases; it proves both directions, the non-indexable case, and the built-ins' filterability.
- **Carry-forward:** qmd's filter AST is still `[Unreleased]` (verified 2026-11-15); re-verify the field name/operator list before Phase 22 finalizes agent-facing docs. Phase 20 now has all five plans summarized; verification is the next step.

---
*Phase: 20-metadata-filtering-discovery*
*Completed: 2026-11-15*

## Self-Check: PASSED

- All 13 key files and this SUMMARY exist on disk.
- All three task commits (`6159a90`, `5329a1f`, `6cb63be`) are ancestors of HEAD; the measured ledger records 3 commits between base and HEAD.
- `make docs-generate` leaves a clean diff on both generated files.
