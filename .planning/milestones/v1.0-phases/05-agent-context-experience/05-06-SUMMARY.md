---
phase: 05-agent-context-experience
plan: 05-06
status: complete
completed: "2026-04-18"
---

# Summary: Fix Path Normalization in Search Context Attachment

## What Was Built

Fixed path normalization mismatch in `_attach_contexts()` across all three search strategies (BM25, Vector, Hybrid). On macOS, `/tmp` resolves to `/private/tmp` for documents but user-provided `/tmp/...` is stored in context `target_id`. The literal string match was failing, so context descriptions were not being attached to search results.

## Changes

### src/docsift/search/bm25.py
- Added `import os`
- `_attach_contexts()` now normalizes both DB keys and result paths with `os.path.realpath()` before matching

### src/docsift/search/vector.py
- Added `import os`
- `_attach_contexts()` now normalizes both DB keys and result paths with `os.path.realpath()` before matching

### src/docsift/search/hybrid.py
- Added `import os`
- `_attach_contexts()` normalizes paths in both the dict-like row path and tuple fallback path, and when looking up results
- MagicMock-safe row handling preserved

### tests/unit/search/test_bm25.py
- Added `test_search_attaches_context_with_normalized_path` — verifies context attaches when document path is `/private/tmp/doc.md` but context target_id is `/tmp/doc.md`

### tests/unit/search/test_vector.py
- Added `test_search_attaches_context_with_normalized_path` — same normalization test for vector search

### tests/unit/search/test_hybrid.py
- Added `test_hybrid_search_attaches_context_with_normalized_path` — verifies hybrid search context attachment with tuple-row mock data representing normalized path mismatch

## Verification

- `pytest tests/unit/search/test_bm25.py tests/unit/search/test_vector.py tests/unit/search/test_hybrid.py -x` — 48 passed
- Import verification: all searchers import correctly

## Deviations

None.
