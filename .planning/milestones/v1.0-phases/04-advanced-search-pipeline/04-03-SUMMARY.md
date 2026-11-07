---
phase: 04-advanced-search-pipeline
plan: 03
date: "2026-04-17"
status: complete
---

# Plan 04-03 Summary: Wire SearchPipeline with Prefix Routing and CLI Integration

## What Was Built

### Task 1: Rewrite SearchPipeline with prefix routing, explainability, candidate capping, and intent propagation

**src/docsift/search/hybrid.py**
- Removed obsolete `search_with_reranking()` from `HybridSearcher` (superseded by `SearchPipeline`)
- Rewrote `SearchPipeline` with:
  - Query prefix routing: `lex:` → BM25, `vec:` → vector, `hyde:` → HyDE, `expand:` → expansion, default → hybrid
  - Intent propagation: prepends `options.intent` to parsed query before search
  - Candidate capping: applies `options.candidate_limit` before reranking (default 20)
  - Explainability: RRF preserves `bm25_score`, `vector_score`, `rrf_score` in `result.scores`
  - Smart snippet extraction: uses `SmartSnippetExtractor` when `result.snippet` is missing
  - HyDE support with text-generation capability check: raises `RuntimeError` if embedder lacks `.generate()` or `.create_completion()`
  - Query expansion with deduplication: expands via `QueryExpansion`, deduplicates case-insensitively
  - Fail-fast reranking: raises `RuntimeError` on reranker failure (per project convention)

### Task 2: Update CLI search commands with new flags and wire SearchPipeline

**src/docsift/cli/commands/search.py**
- `query_cmd`: added `--explain`, `-C/--candidate-limit` (validated 1-200 via `click.IntRange`), `--intent`
- `query_cmd`: builds `SearchOptions` with `explain`, `candidate_limit`, `intent`
- `query_cmd`: wires `SearchPipeline` with `QueryExpansion`, `create_reranker()` factory, `SmartSnippetExtractor`
- `query_cmd`: shows score breakdowns when `--explain` is used
- `vsearch_cmd`: added `--min-score` and `--full` options
- `search_cmd`: already had `--min-score` and `--full`; verified they work

### Task 3: Fix test_hybrid.py, test_search_pipeline.py, and add pipeline tests

**tests/unit/search/test_hybrid.py**
- Complete rewrite with correct imports (`docsift.core.models`, `docsift.search.hybrid`)
- Tests for `SearchPipeline` prefix routing (lex, vec, hyde, expand, default)
- Tests for query expansion with deduplication
- Tests for reranking with candidate limit enforcement
- Tests for explain score preservation (bm25_score, vector_score, rrf_score)
- Tests for intent propagation

**tests/integration/test_search_pipeline.py**
- Complete rewrite with real `HybridSearcher`/`SearchPipeline` APIs
- Integration tests for BM25, vector, hybrid pipelines
- Tests for query expansion and reranking integration
- Tests for RRF fusion correctness

**tests/unit/cli/test_search.py**
- Fixed existing tests to patch `SearchPipeline` instead of `HybridSearcher`
- Added `reranker_model_name=None` to settings mocks
- Added tests for `--explain`, `--candidate-limit`, `--intent`
- Added tests for `--min-score`, `--full` in vsearch
- Added candidate-limit range validation test

## Commits

1. `56cb05b` — feat(04-03): rewrite SearchPipeline with prefix routing and explainability
2. `9d4874d` — feat(04-03): update CLI search commands with new flags and wire SearchPipeline
3. `ca6df8d` — test(04-03): fix test imports and add SearchPipeline tests
4. `aaa29ae` — test(04-03): add CLI search flag tests and fix existing test mocks

## Verification

- `pytest tests/unit/search/test_hybrid.py` — 17 passed
- `pytest tests/integration/test_search_pipeline.py` — 8 passed
- `pytest tests/unit/cli/test_search.py` — 14 passed
- `python -c "from docsift.search.hybrid import HybridSearcher, SearchPipeline; print('OK')"` — OK
- `python -c "from docsift.cli.commands.search import query_cmd, vsearch_cmd; print('OK')"` — OK

## Notable Deviations

- None. All acceptance criteria met.

## Self-Check

- [x] All tasks executed
- [x] Each task committed individually
- [x] Tests pass
- [x] Imports clean
