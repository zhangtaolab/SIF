---
phase: 22-mcp-sdk-v2-modernization-agent-packaging
plan: 05
subsystem: mcp
tags: [mcp, citations, snippets, line-ranges, content-hash, goldens, frozen-envelope]

# Dependency graph
requires:
  - phase: 22-mcp-sdk-v2-modernization-agent-packaging
    provides: "22-02 seven-tool surface, outputSchema/structuredContent, goldens writer"
  - phase: 22-mcp-sdk-v2-modernization-agent-packaging
    provides: "22-04 query pipeline parity with the hoisted snippet extractor"
  - phase: 20-metadata-filtering-discovery
    provides: "frozen metadata envelope and typed metadata discovery"
provides:
  - "SmartSnippetExtractor.extract_with_range returning (snippet, line_start, line_end) with byte-identical extract()"
  - "Core SearchResult line_start/line_end dataclass fields excluded from to_dict()"
  - "MCP SearchResult snippet/content_hash/line_start/line_end and Document content_hash (additive)"
  - "DocumentRepository.get_checksums chunked page lookup (one bounded IN query per chunk)"
  - "Full 1..N and requested inclusive ranges on get; full ranges plus hashes on multi_get"
  - "Independent Phase 20 envelope oracle and citation edge battery"
  - "Five era goldens regenerated for the citation output schemas (tools/list only)"
affects: [22-06, 22-07]

# Actuals (#2632) — pairs with the plan's `estimate` (88000 tokens, 3 tasks).
actuals:
  tokens: 30468
  tasks: 3
  commits: 3
plan_head_before: 1cb954e730ab25ce29b51e13c200a42e6a481a29
plan_head_after: 8476392d0b88c3ac82ac03d35cd6eb3dd3c03458

tech-stack:
  added: []
  patterns:
    - "One extractor pass returns snippet bytes plus the rendered inclusive line window; extract() delegates to element 0"
    - "Citation fields ride the existing explicit MCP boundary map; the stored checksum is fetched once per page, never recomputed"
    - "Full-document ranges count newline splits with trailing-newline accounting; ranged requests report the requested inclusive range"
    - "The direct lex/BM25 route keeps the documented 22-04 snippet deviation while still attaching content_hash"
    - "Metadata envelope is proven by an independent oracle deep-equaled against both channels"

key-files:
  created:
    - tests/unit/mcp/test_citations.py
  modified:
    - src/sif/search/snippets.py
    - src/sif/search/hybrid.py
    - src/sif/core/models.py
    - src/sif/mcp/protocol.py
    - src/sif/mcp/backend.py
    - src/sif/database/repositories.py
    - tests/unit/search/test_snippets.py
    - tests/unit/search/test_hybrid.py
    - tests/unit/mcp/test_backend.py
    - tests/unit/mcp/test_tools.py
    - tests/unit/mcp/test_lazy_embedder.py
    - tests/unit/mcp/goldens/2024-11-05.json
    - tests/unit/mcp/goldens/2025-03-26.json
    - tests/unit/mcp/goldens/2025-06-18.json
    - tests/unit/mcp/goldens/2025-11-25.json
    - tests/unit/mcp/goldens/2026-07-28.json

key-decisions:
  - "extract_with_range reports inclusive 1-based ranges for every path: a normal window (start+1..end+1), a long-line cut as that single line, a fallback as the rendered line span, and empty text as the (1, 1) sentinel with no line fields assigned."
  - "extract() is a thin wrapper over extract_with_range()[0], so existing CLI snippet bytes are byte-identical; _apply_snippets still assigns an empty snippet (preserving to_dict bytes) while leaving line fields unset."
  - "line_start/line_end live only on the core dataclass and are deliberately absent from to_dict(); the MCP boundary maps them explicitly (D-11)."
  - "content_hash is documents.checksum fetched by one DocumentRepository.get_checksums call per result page (chunked at 900 placeholders), never recomputed from snippet or content."
  - "The direct lex:/BM25 and stripped-degrade routes keep 22-04's documented no-snippet deviation (snippet/line fields stay None) but still attach content_hash; citation for those routes is served by get."
  - "A full get is 1..N counting newline splits with trailing-newline accounting; a ranged get is the requested inclusive range, and adjacent requests stay contiguous (2..4 then 5..5)."
  - "multi_get builds its documents after the byte-budget loop so all hashes come from one batched call and every document carries its full 1..N range."
  - "The five goldens were regenerated with SIF_UPDATE_WIRE_GOLDENS=1; a structural diff confirmed only tools/list exchanges changed in every era."

patterns-established:
  - "Citation battery: real production schema + repository-created docs; mocked pipeline rows prove the explicit boundary map and batched checksum call"
  - "Frozen-envelope oracle duplicated as an independent contract test rather than imported from test_tools"
  - "Golden review gate: compare per-exchange methods between HEAD and the working tree and require exactly ['tools/list']"

requirements-completed: [MCP-03]

coverage:
  - id: D1
    description: "SmartSnippetExtractor reports inclusive 1-based line windows for window, long-line, fallback, and empty paths while extract() bytes stay unchanged"
    requirement: MCP-03
    verification:
      - kind: unit
        ref: "tests/unit/search/test_snippets.py#TestExtractWithRange"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_hybrid.py#TestPipelineSnippetRoutes::test_apply_snippets_fills_snippet_and_line_fields_together"
        status: pass
    human_judgment: false
  - id: D2
    description: "MCP SearchResult/Document carry additive citation fields; content_hash is the stored checksum fetched once per page; get is 1..N or the requested range; multi_get carries hashes and full ranges"
    requirement: MCP-03
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_citations.py#TestQueryCitationFields"
        status: pass
      - kind: unit
        ref: "tests/unit/mcp/test_citations.py#TestGetCitationRanges"
        status: pass
      - kind: unit
        ref: "tests/unit/mcp/test_backend.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "The Phase 20 metadata envelope is deep-equal in text and structuredContent, builtIns is path then mtime, filteredDocuments is absent without a filter, and metadata gains no citation fields"
    requirement: MCP-03
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_citations.py#TestFrozenMetadataEnvelope"
        status: pass
    human_judgment: false
  - id: D4
    description: "Zero-result pages conform, missing documents raise ToolError with no payload, ranges use newline splits, hashes are stored values, and to_dict omits line fields"
    requirement: MCP-03
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_citations.py#TestCitationEdgeCases"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search_pagination.py"
        status: pass
    human_judgment: false
  - id: D5
    description: "All five era goldens carry the citation output schemas; the structural diff changes only tools/list and every initialize/status exchange stays byte-identical"
    requirement: MCP-03
    verification:
      - kind: integration
        ref: "tests/unit/mcp/test_wire_transcripts.py"
        status: pass
      - kind: other
        ref: "structural golden diff: changed exchanges == ['tools/list'] for all five eras"
        status: pass
    human_judgment: false

# Metrics
duration: 17min
completed: 2026-11-16
status: complete
---

# Phase 22 Plan 05: Citation-Grade MCP Output Summary

**Snippet line windows, stored content hashes, and full/ranged get citation fields added additively to the MCP boundary while CLI JSON and the frozen metadata envelope stayed byte-identical**

## Performance

- **Duration:** ~17 min
- **Started:** 2026-11-16T16:13:00Z (approx.)
- **Completed:** 2026-11-16T16:30:14Z
- **Tasks:** 3
- **Files changed:** 17 (6 source, 6 test modules, 5 goldens)

## Accomplishments

- `SmartSnippetExtractor.extract_with_range` returns `(snippet, line_start, line_end)` with inclusive 1-based document lines for every path: a normal `_build_window` span, a long-line cut as that single line, a fallback as the first renderable line through the last rendered line (or the truncated line), and `(1, 1)` for empty text. `extract()` delegates to element 0, so CLI snippet bytes are unchanged.
- The core `SearchResult` gained `line_start`/`line_end` dataclass fields with a comment marking them MCP-only; `to_dict()` was not touched. `_apply_snippets` now assigns the snippet bytes and both line fields in the same pass that already fetched content, keeping the empty-snippet CLI byte contract while leaving line fields unset for it.
- The MCP `SearchResult` gained `snippet`, `content_hash`, `line_start`, `line_end`; `Document` gained `content_hash`. All are additive with `None` defaults, and every existing field name/default is preserved (D-12).
- `DocumentRepository.get_checksums` fetches a page's stored checksums with chunked `WHERE id IN (...)` queries (900 placeholders per chunk), never a per-document N+1 loop. `SearchBackend` performs exactly one call per result page and maps `content_hash` from it, while the snippet and window ride the core row through the explicit boundary map.
- `get` now always reports an inclusive range: full read = 1..N (newline splits, trailing newline does not add a line), ranged read = the requested inclusive range. `multi_get` reports full 1..N ranges and hashes for every returned document from one batched lookup. `content_hash` in both comes from the stored `documents.checksum`.
- The direct `lex:`/BM25 routes keep 22-04's documented snippet deviation (`snippet`/`line_start`/`line_end` stay `None`) but still attach `content_hash`; citation for those routes is served by `get`.
- The five era goldens were regenerated for the citation output schemas. A structural comparison against HEAD showed changed exchanges == `['tools/list']` for all five eras; every initialize and status exchange stayed byte-identical.
- `tests/unit/mcp/test_citations.py` now holds an independent Phase 20 envelope oracle (context: text and `structuredContent` deep-equal, `builtIns` path then mtime, no `filteredDocuments` without a filter, no wrapper key, no `range` on strings), citation edge cases, schema assertions, and the explicit `to_dict()` exclusion guard.
- CLI JSON regression tests (`test_search.py`, `test_search_pagination.py`) pass unmodified, proving `--json` output did not gain line fields.

## Task Commits

Each task was committed atomically:

1. **Task 1: Snippet line windows without changing CLI snippet bytes** - `8b0fb2b` (feat)
2. **Task 2: Citation fields, batched hashes, and full/ranged get ranges** - `9cd048e` (feat)
3. **Task 3: Frozen envelope, citation edges, and CLI regression battery** - `8476392` (test)

**Plan metadata:** docs commit created after this SUMMARY (not counted in `actuals.commits`).

## Files Created/Modified

- `src/sif/search/snippets.py` - `extract_with_range`, `_fallback_with_range`, thin `extract()`
- `src/sif/search/hybrid.py` - one-pass snippet/line assignment in `_apply_snippets`
- `src/sif/core/models.py` - MCP-only `line_start`/`line_end` dataclass fields (not in `to_dict`)
- `src/sif/mcp/protocol.py` - additive citation fields on `SearchResult` and `Document`
- `src/sif/mcp/backend.py` - citation boundary map, `_page_checksums`, `_full_line_range`, full/ranged `get`, batched `multi_get`
- `src/sif/database/repositories.py` - `get_checksums` chunked page lookup
- `tests/unit/mcp/test_citations.py` - citation, schema, serialization, envelope, and edge battery
- `tests/unit/mcp/test_backend.py` - full-read 1..N expectation, checksum-configured get/multi_get mocks, explicit citation values in `_weight_result`
- `tests/unit/mcp/test_tools.py` - citation serialization on both channels
- `tests/unit/search/test_snippets.py`, `tests/unit/search/test_hybrid.py` - range and byte-identity proofs
- `tests/unit/mcp/goldens/*.json` - regenerated `tools/list` citation output schemas

## Decisions Made

- See frontmatter `key-decisions`. The load-bearing ones: the extractor reports its existing window rather than rescanning; `content_hash` is always the stored checksum fetched once per page; line fields are dataclass-only and excluded from CLI JSON; and the direct lex/BM25 routes keep their documented no-snippet deviation while gaining hashes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] The lazy-embedder core-result double needed the additive citation fields**
- **Found during:** Task 3 (full-suite regression run)
- **Issue:** `tests/unit/mcp/test_lazy_embedder.py::_core_result` builds a `MagicMock` for the direct BM25 routes. The extended boundary map reads `snippet`/`line_start`/`line_end`, and MagicMock's auto-created attributes fail Pydantic's string/int validation.
- **Fix:** Gave the double explicit `None` citation values (matching the documented direct-route deviation) instead of letting MagicMock auto-create them. No production behavior changed.
- **Files modified:** `tests/unit/mcp/test_lazy_embedder.py`
- **Verification:** `pytest tests/unit/mcp/test_lazy_embedder.py` — 8 passed; full suite green afterward.
- **Committed in:** `8476392`

### Plan Notes (not deviations)

- `src/sif/mcp/tools.py` needed no edit: the tool return annotations already derive from the extended `protocol` models, so `outputSchema` changed without touching the registration code.
- `tests/unit/mcp/test_wire_transcripts.py` and the two CLI test modules were intentionally left unmodified (the plan lists them as regression surfaces, not edit targets).
- 22-04's `test_query_path_invokes_the_smart_snippet_extractor` was adapted in `test_backend.py` (a plan-listed file) to the new `extract_with_range` contract and now also asserts the mapped snippet/line fields.
- `tests/unit/mcp/test_backend.py::_weight_result` and the early hybrid mock carry explicit citation values so the boundary assertions are deterministic rather than MagicMock-derived.

## Issues Encountered

- Golden regeneration initially failed the byte comparison as expected; after `SIF_UPDATE_WIRE_GOLDENS=1 pytest tests/unit/mcp/test_wire_transcripts.py`, a per-exchange method comparison confirmed only `tools/list` payloads moved in all five eras.
- The full suite surfaced the lazy-embedder double issue above; it was fixed before the Task 3 commit.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None.

## Threat Flags

None - no new network, auth, filesystem, or schema surface. The T-22-12 mitigation is implemented as specified: `content_hash` is the stored checksum fetched once per page, never recomputed, and tests pin stored-value equality.

---

**Total deviations:** 1 auto-fixed (blocking test-double adaptation)
**Impact on plan:** Every behavior the plan specifies is implemented; the only extra change was making a pre-existing test double express the new additive fields explicitly.

## Next Phase Readiness

- 22-06's `sif-cite` skill can rely on `query` results carrying `snippet`/`content_hash`/`line_start`/`line_end` and on `get` returning a stored hash plus an inclusive range; the two-stage citation rule (get before citing) is now fully supported by the wire contract.
- Any further tool-surface change must re-run the golden writer and re-check that only `tools/list` exchanges changed.
- Full suite green at 2822 passed / 1 skipped / 95.11% coverage; `ruff check`, `ruff format --check`, and `ty check src/sif` all pass.

## Self-Check: PASSED

All created files exist on disk; all three task commits (`8b0fb2b`, `9cd048e`, `8476392`) are ancestors of HEAD.
