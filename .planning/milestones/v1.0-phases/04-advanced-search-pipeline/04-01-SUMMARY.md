# Plan 04-01 Summary

**Status:** Complete
**Completed:** 2026-04-17

## What Was Built

### Task 1: Extended SearchResult and SearchOptions
- Added `scores: dict[str, float | None]` to `SearchResult` for pipeline stage score tracking
- Added `snippet: str | None` to `SearchResult` for smart snippet extraction
- Added `explain`, `candidate_limit`, `intent`, `snippet_max_length` to `SearchOptions`
- Added `HYDE` and `EXPAND` to `SearchType` enum

### Task 2: Reranker Settings + RRF Score Preservation
- Added `reranker_model_name`, `reranker_model_path`, `reranker_model_type` (default='gguf'), `reranker_batch_size` to Settings
- Updated `RRFFusion.fuse()` to preserve `bm25_score`, `vector_score`, and `rrf_score` in `SearchResult.scores` dict
- Same updates applied to `fuse_with_weights()`

### Task 3: Cross-Encoder Reranker Implementation
- Implemented `LlamaCppReranker` (primary, per locked decision D-04) with lazy loading via `llama_cpp.Llama`
- Implemented `CrossEncoderReranker` (fallback) with lazy loading via `sentence_transformers.CrossEncoder`
- Added `create_reranker(settings)` factory function
- Added `Reranker = LlamaCppReranker` backwards-compatible alias
- Sigmoid normalization for scores to [0, 1]
- Updated `test_reranker.py` for dataclass `SearchResult`

## Commits
- `32bdfc1`: feat(04-01): extend SearchResult and SearchOptions dataclasses
- `e474c53`: feat(04-01): add reranker settings and fix RRF score preservation
- `6a782d8`: feat(04-01): implement LlamaCppReranker and CrossEncoderReranker with factory

## Deviations
- `test_rrf.py` fixes planned for Task 2 were not included in commit; will be addressed in Plan 04-05
