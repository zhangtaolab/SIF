---
phase: 20-metadata-filtering-discovery
plan: "04"
subsystem: cli-mcp-surfaces
tags: [click, mcp, pydantic, metadata-filter, error-taxonomy, generated-docs]

# Dependency graph
requires:
  - phase: 20-metadata-filtering-discovery
    plan: "01"
    provides: "FilterNode/parse_filter/FilterValidationError, SearchOptions.filter, sif search --filter and _parse_filter_option"
  - phase: 20-metadata-filtering-discovery
    plan: "03"
    provides: "corrected filtered vector escalation and pre-RRF filter semantics on both legs"
provides:
  - "--filter on sif search vsearch and sif search query, validated before open_initialized_database"
  - "filter on QueryInput/LexSearchInput/VecSearchInput plus the QueryToolHandler input_schema property"
  - "SearchBackend.hybrid_search(filter_node=...) threaded into SearchOptions.filter"
  - "controlled ToolsCallResult(isError=True) filter-validation path (never JSON-RPC INVALID_PARAMS)"
  - "regenerated docs/cli-reference.md documenting --filter on all three result commands"
affects: [20-05, 22]

# Actuals (#2632) — chars/4 over the realized diff, same scale as the plan estimate.
actuals:
  tokens: 7964
  tasks: 3
  commits: 3

# Measured commit ledger (#3968) — base recorded before the first task commit.
plan_head_before: 0443e19c089f5dacd5c48cc6ab998080d7daa25f
plan_head_after: aad3e9be555c044030b7083bf28f69a286175770

tech-stack:
  added: []
  patterns:
    - "One CLI filter-option parser (json -> parse_filter -> ClickException) reused by all three result commands"
    - "MCP filter typed as a raw dict; validation lives in the handler so failures are tool execution errors"
    - "Backend filter parameter named filter_node (ruff A002: no function-argument builtin shadowing)"
    - "Session budget pre-walk runs before pydantic on every surface via the shared parse_filter"

key-files:
  created: []
  modified:
    - src/sif/cli/commands/search.py
    - src/sif/mcp/protocol.py
    - src/sif/mcp/handlers.py
    - src/sif/mcp/backend.py
    - tests/unit/cli/test_search_filter.py
    - tests/unit/cli/test_search.py
    - tests/unit/mcp/test_backend.py
    - docs/cli-reference.md

key-decisions:
  - "vsearch/query parse --filter immediately after limit resolution and before open_initialized_database, mirroring 20-01's search_cmd placement (D-17): an invalid filter never opens the index or pays _pre_search_refresh."
  - "The AST-validation message renders filter.<operator-path> (e.g. `filter.gt: \"gt\" requires a numeric value; field 'tags' got str`), 20-01's shipped convention — the message names operator, field, and path even though the plan's example spelling was filter.tags.gt; changing the shipped validator was out of scope."
  - "MCP filter stays a raw dict[str, Any] in the pydantic models; the handler runs parse_filter after model construction, so a grammar violation is an explicit isError (no logged stack trace) and a non-object payload still lands in the server's generic isError catch."
  - "Backend parameter is filter_node, not filter (ruff A002); the pydantic/dataclass field names stay `filter` and carry no noqa (A003 does not fire on annotated fields, RUF100 would flag an unused directive)."
  - "Unfiltered defaults are pinned by tests on all six surfaces: SearchOptions.filter stays None and no pre-count/notice is emitted."

patterns-established:
  - "Schema-sync tests assert every advertised input_schema property against the pydantic model (filter joins offset/per_chunk/weights)"
  - "Surface-parity tests parametrize one CLI behavior across search/vsearch/query with pytest ids"
  - "Protocol-error vs tool-error is asserted through the real MCPServer dispatch, not only the handler"

requirements-completed: [FILT-01, FILT-02]

coverage:
  - id: D1
    description: "All three CLI result commands accept --filter with identical grammar, validate before any DB open or drift walk, and compose it by AND with collection/offset/min-score."
    requirement: FILT-01
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_search_filter.py#TestFilterOptionMatrix"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search_filter.py#TestFilterComposition"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestNoFilterRegression"
        status: pass
    human_judgment: false
  - id: D2
    description: "All three MCP search inputs declare filter, the hand-written query schema advertises it, and the parsed AST reaches SearchOptions.filter through SearchBackend (BM25 fallback included)."
    requirement: FILT-01
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_backend.py#TestFilterInputs"
        status: pass
      - kind: unit
        ref: "tests/unit/mcp/test_backend.py#TestQueryToolHandlerFilter"
        status: pass
      - kind: unit
        ref: "tests/unit/mcp/test_backend.py#TestFilterThroughBackend"
        status: pass
    human_judgment: false
  - id: D3
    description: "An invalid MCP filter is a ToolsCallResult(isError=True) inside a successful JSON-RPC envelope, never an INVALID_PARAMS protocol error."
    requirement: FILT-01
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_backend.py#TestInvalidFilterIsNotAProtocolError::test_invalid_filter_yields_success_envelope_with_iserror"
        status: pass
    human_judgment: false
  - id: D4
    description: "Generator-owned docs/cli-reference.md is regenerated by make docs-generate and documents --filter in all three search sections; configuration.md is unchanged."
    requirement: FILT-02
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_search_filter.py#TestDocsSurface::test_cli_reference_documents_filter_flag"
        status: pass
      - kind: unit
        ref: "make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-11-15
status: complete
---

# Phase 20 Plan 04: CLI and MCP filter surfaces

**The same `--filter` JSON AST now reaches every CLI result command and all three MCP search inputs through one validator: invalid filters fail as user input before any index work on the CLI and as recoverable tool execution errors inside a successful JSON-RPC envelope on MCP, with unfiltered output unchanged and the generated CLI reference proving the flag on all three commands.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-11-15T12:46:19Z
- **Completed:** 2026-11-15T12:58:08Z
- **Tasks:** 3
- **Files modified:** 8 (1 generated)

## Accomplishments
- `sif search vsearch` and `sif search query` accept the same `--filter <json>` flag as `sif search search`; `--filter` is parsed and validated before `open_initialized_database`, so a bad filter never opens the index and never calls `_pre_search_refresh` (asserted with patched spies on all three commands).
- The CLI error taxonomy is distinct and actionable: invalid JSON reports `filter: invalid JSON: ...`, a semantic violation reports `filter.gt: "gt" requires a numeric value; field 'tags' got str`, and the filter op is not on `get`/`multi-get`/`ls`.
- Filtering composes by AND with `-c`, `--offset`, and `--min-score`: the `SearchOptions` handed to the BM25 searcher, VectorSearcher, and SearchPipeline carries all four values.
- `QueryInput`, `LexSearchInput`, and `VecSearchInput` each declare `filter: dict[str, Any] | None`, and `QueryToolHandler.input_schema` advertises `"filter": {"type": "object"}` so Phase 22 tool discovery sees the property.
- `QueryToolHandler.handle` validates through the shared `parse_filter` and returns `ToolsCallResult(isError=True)` on `FilterValidationError`; asserted through the real `MCPServer` dispatch that the JSON-RPC envelope is a success (`error is None`, `result.isError is True`).
- `SearchBackend.hybrid_search(filter_node=...)` sets `SearchOptions.filter` by object identity, and the BM25-only degrade path receives the same options object — so the filter applies on both paths.
- `make docs-generate` regenerated `docs/cli-reference.md` with `--filter` under `search query`, `search search`, and `search vsearch`; `docs/configuration.md` is unchanged (no new setting).
- Unfiltered defaults pinned: `SearchOptions.filter is None` for all three CLI commands and for unfiltered MCP calls; no pre-count, warning, or extra output appears (`--json` stdout parses cleanly).

## Task Commits

Each task was committed atomically:

1. **Task 1: CLI `--filter` on vsearch and query** - `d5a6de8` (feat)
2. **Task 2: MCP `filter` on all three inputs + backend threading** - `4bc1697` (feat)
3. **Task 3: Regenerate generator-owned CLI docs + docs-surface test** - `aad3e9b` (docs)

**Plan metadata:** the closing docs commit created after this SUMMARY.

## Files Created/Modified
- `src/sif/cli/commands/search.py` — `--filter` option, `filter_json` parameter, `_parse_filter_option` call before DB open, and `filter=filter_node` in the `vsearch_cmd`/`query_cmd` `SearchOptions`.
- `src/sif/mcp/protocol.py` — `filter: dict[str, Any] | None = None` on all three search inputs with D-02 comments.
- `src/sif/mcp/handlers.py` — `filter` property in `QueryToolHandler.input_schema`; controlled `parse_filter` try/except returning `ToolsCallResult(isError=True)`; `filter_node=` forwarded to the backend.
- `src/sif/mcp/backend.py` — `filter_node` parameter, `FilterNode` import, and `filter=filter_node` in the `SearchOptions` construction.
- `tests/unit/cli/test_search_filter.py` — `TestFilterOptionMatrix` (flag presence, JSON/AST errors before any index work, clean JSON stdout across the three commands), `TestFilterComposition` (AND with collection/offset/min-score on each command), `TestDocsSurface`.
- `tests/unit/cli/test_search.py` — `TestNoFilterRegression`: one test per command asserting `SearchOptions.filter is None`.
- `tests/unit/mcp/test_backend.py` — `TestFilterInputs`, `TestQueryToolHandlerFilter`, `TestInvalidFilterIsNotAProtocolError`, `TestFilterThroughBackend` (11 tests).
- `docs/cli-reference.md` — regenerated (`--filter` rows for query/vsearch), never hand-edited.

## Decisions Made
- **CLI placement and signature shape.** `_parse_filter_option` runs right after `limit` resolution on both commands; the new `filter_json` parameter sits in the defaulted tail of the long signatures (Click binds by option name), keeping the existing positional contract untouched.
- **Error spelling follows 20-01, not the plan's example.** The shipped validator renders the operator path (`filter.gt`) and names the field in the message; the plan's example (`filter.tags.gt`) does not match the shipped convention, so the test asserts operator + field + path without rewriting 20-01's validator (see deviations).
- **MCP validation boundary.** `parse_filter` runs in the handler after `QueryInput(**params)`: grammar/budget violations return an explicit `isError` (no stack trace), while model-shape failures (e.g. a non-object `filter`) keep the server's generic `isError` catch — still never `INVALID_PARAMS`.
- **A002 vs A003.** Only the backend function parameter is renamed to `filter_node`; the annotated pydantic fields keep `filter` with no `noqa`, since A003 does not fire on annotated fields and RUF100 would flag an unused directive.
- **Byte-identical defaults.** All filtered-only behavior stays gated on `filter_node is not None`; the tests pin `None` on every unfiltered path.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] AST error-path assertion did not match the shipped 20-01 convention**
- **Found during:** Task 1 (`TestFilterOptionMatrix` first run)
- **Issue:** The plan's action/acceptance text gave `filter.tags.gt` as the expected path spelling, but 20-01's shipped `FilterValidationError` renders the operator path (`filter.gt: "gt" requires a numeric value; field 'tags' got str`) and its own tests pin that form. Rewriting the validator would have been a 20-01 behavior change outside this plan's files and a breaking change to shipped messages.
- **Fix:** The test asserts the shipped message names the operator (`"gt" requires a numeric value`), the offending field (`tags`), and its dotted path (`filter.gt`), satisfying D-17's "names the operator, field, and path" criterion.
- **Files modified:** `tests/unit/cli/test_search_filter.py`
- **Verification:** `TestFilterOptionMatrix` 12 cases pass; `tests/unit/core/test_filters.py` remains green in the full suite.
- **Committed in:** `d5a6de8` (amended into Task 1)

---

**Total deviations:** 1 auto-fixed (1 blocking test-expectation adjustment).
**Impact on plan:** No production behavior changed; the adjustment only reconciled the plan's example spelling with the already-shipped 20-01 error convention.

## Issues Encountered
- None beyond the deviation above.

## Threat Model Compliance
- **T-20-13 (tampering):** both surfaces call the one `parse_filter`; the compiler remains parameterized and the 20-01/20-03 injection tests stay green. The MCP schema declares the property but never passes the raw dict to SQL.
- **T-20-14 (DoS):** the shared budget pre-walk (depth/nodes/string/array) runs before pydantic on both new surfaces; an over-budget payload raises `FilterValidationError` with a named budget message.
- **T-20-15 (integrity):** no filter path writes to stdout; `TestFilterOptionMatrix::test_filtered_json_output_is_clean_json` parses `--json` stdout and asserts no notice text.
- **T-20-16 (information disclosure):** the parsed AST is passed explicitly and identity-asserted through the backend; every unfiltered CLI/MCP path is asserted to leave `SearchOptions.filter is None`.
- **T-20-SC:** no dependency was added or installed.

## Known Stubs
None.

## Threat Flags
None — the shipped surface is covered by the plan's threat register (T-20-13..16).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- **Ready for 20-05:** the discovery tool can reuse the same CLI/MCP error mapping (`_parse_filter_option` on the CLI, handler-local `parse_filter` + `isError` on MCP); `filter` is already declared on the input models and the query schema, so Phase 22's registration parity has no filter gap.
- **Carry-forward:** qmd's AST is still `[Unreleased]`; re-verify the field name/operator list before Phase 22 freezes the MCP schema.
- Quality gates green: `ruff check src tests`, `ruff format --check src tests`, `ty check src/sif` (0 diagnostics), full `pytest` 2346 passed / 1 skipped at 95.19% coverage (gate 90).

---
*Phase: 20-metadata-filtering-discovery*
*Completed: 2026-11-15*

## Self-Check: PASSED

- All 8 files and this SUMMARY exist on disk.
- All three task commits (`d5a6de8`, `4bc1697`, `aad3e9b`) are ancestors of HEAD.
- `make docs-generate` leaves a clean diff on both generated files.
