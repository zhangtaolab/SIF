---
phase: 09-mcp-server-implementation
plan: 02
status: complete
executed: 2026-05-12
---

# Plan 09-02: SearchBackend Implementation

## Objective

Implement the real `SearchBackend` class connecting to `DatabaseConnection`, instantiating actual searchers, and returning genuine search results with async wrapper over sync sqlite3.

## What Was Built

### Files Updated
- `src/sif/mcp/backend.py` — Full SearchBackend implementation
  - `__init__`: Stores db_path and settings (default from `get_settings()`)
  - `_run_in_db`: Wraps sync DB callbacks in `asyncio.to_thread()` with fresh `DatabaseConnection`
  - `hybrid_search`: Builds `SearchOptions`, resolves collection names to IDs, creates `SearchPipeline`, maps results to `protocol.SearchResult`
  - `get_document`: Looks up by ID then by path across collections, supports line slicing with `from_line`/`max_lines`
  - `get_documents_by_pattern`: Uses `fnmatch` to filter documents across collections, enforces max_bytes limit
  - `get_status`: Returns collection counts and total document count
  - `_truncate_content`: Module-level helper limiting output to 100KB

### Tests Created
- `tests/unit/mcp/test_backend.py` — Tests for SearchBackend with mocked dependencies

## Key Decisions

- `SearchPipeline` is instantiated per call (not cached) to keep code simple
- `embedder=None` passed to SearchPipeline — pipeline handles its own embedder resolution
- `_truncate_content` limits to 100KB per SPEC.md constraint
- No `asyncio.Lock` on embedder — `EmbeddingManager._model` caches at class level, load_model is idempotent

## Self-Check

- [x] `python -c "from sif.mcp.backend import SearchBackend; import inspect; assert inspect.iscoroutinefunction(SearchBackend.hybrid_search)"` passes
- [x] All 4 methods are async
- [x] `ruff check src/sif/mcp/backend.py` passes
- [x] `pytest tests/unit/mcp/test_backend.py` passes

## Deviations

- EmbeddingManager is not stored as instance attribute; settings are stored and `SearchPipeline` handles embedder internally. This simplifies the backend and avoids locking complexity.
- `_run_in_db` takes a callback rather than using context manager directly, making the sync/async boundary cleaner.
