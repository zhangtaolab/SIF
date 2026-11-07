---
phase: 04-advanced-search-pipeline
plan: 02
subsystem: search
phase_number: 4
plan_number: 2
tags: [query-expansion, snippets, embedding, PRF]
dependencies:
  requires: []
  provides: [SRCH-02, SRCH-07]
  affects: [src/docsift/search/expansion.py, src/docsift/search/snippets.py]
tech-stack:
  added: []
  patterns: [Protocol-based extensibility, embedding-based PRF, sentence scoring]
key-files:
  created:
    - src/docsift/search/snippets.py
    - tests/unit/search/test_snippets.py
  modified:
    - src/docsift/search/expansion.py
    - tests/unit/inference/test_query_expander.py
decisions:
  - "QueryExpansion.expand() returns list[str] per QueryExpander protocol, with [query] as fallback"
  - "Embedding-based PRF uses synonym map + cosine similarity over candidate terms"
  - "SmartSnippetExtractor scores sentences by weighted term frequency (count * term_length)"
  - "expand_batch() deduplicates while preserving order"
metrics:
  duration_seconds: 409
  completed_date: "2026-04-17T12:57:00Z"
  tasks_completed: 2
  tests_added: 25
  tests_passing: 25
---

# Phase 04 Plan 02: Query Expansion and Smart Snippets Summary

**One-liner:** QueryExpansion with embedding-based pseudo-relevance feedback returning list[str], and SmartSnippetExtractor scoring sentences by weighted query term frequency.

## What Was Built

### Task 1: QueryExpansion with Embedding-Based PRF

Updated `src/docsift/search/expansion.py` to implement real query expansion:

- **Protocol compliance:** `expand()` now returns `list[str]` matching the `QueryExpander` protocol in `core/models.py`
- **Intent support:** Optional `intent` parameter prepends an intent hint to each variant
- **Embedding-based PRF:** `_get_expansion_terms()` embeds the query, generates candidate terms from query words + synonym map, and ranks them by cosine similarity
- **expand_batch():** Expands multiple queries and returns a flat deduplicated list preserving order
- **Graceful fallback:** Returns `[query]` when no embedding manager or no expansion terms found

### Task 2: SmartSnippetExtractor

Created `src/docsift/search/snippets.py` with sentence-level snippet extraction:

- **Sentence scoring:** `_score_sentence()` weights term frequency by term length for smarter matching
- **Window building:** `_build_window()` expands outward from the best-scoring sentence up to `max_length`
- **Ellipsis handling:** Adds "..." when window is truncated at either end
- **Fallback:** Returns beginning of text when no query terms match

## Test Results

| Test File | Tests | Status |
|-----------|-------|--------|
| tests/unit/inference/test_query_expander.py | 15 | PASS |
| tests/unit/search/test_snippets.py | 10 | PASS |
| **Total** | **25** | **PASS** |

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 4acf4d3 | feat(04-02): implement QueryExpansion with embedding-based PRF returning list[str] |
| 2 | 6473394 | feat(04-02): implement SmartSnippetExtractor with sentence scoring and window extraction |

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None. Both components are fully functional with real implementations.

## Threat Flags

None. Query expansion operates locally with no external API calls. Snippet extraction processes only indexed content.

## Self-Check: PASSED

- [x] `src/docsift/search/expansion.py` exists and lints clean
- [x] `src/docsift/search/snippets.py` exists and lints clean
- [x] `tests/unit/inference/test_query_expander.py` exists and passes (15/15)
- [x] `tests/unit/search/test_snippets.py` exists and passes (10/10)
- [x] Commit 4acf4d3 exists
- [x] Commit 6473394 exists
