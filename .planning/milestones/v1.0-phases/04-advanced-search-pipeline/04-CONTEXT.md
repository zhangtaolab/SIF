# Phase 4: Advanced Search Pipeline - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Add reranking, query expansion, explainability, and search quality controls.

This phase delivers:
- Configurable LLM reranker with cross-encoder support (SRCH-01)
- LLM query expansion for improved recall (SRCH-02)
- Query document syntax (`lex:`, `vec:`, `hyde:`, `expand:`) for targeted search modes (SRCH-03)
- `--explain` score breakdowns across BM25, RRF, and reranker stages (SRCH-04)
- `--min-score` and `--full` CLI controls (CLI-06, CLI-07)
- `--candidate-limit` / `-C` for reranker candidate pool size (SRCH-05)
- `--intent` parameter passed through search pipeline (SRCH-06)
- Smart snippet extraction from chunks (SRCH-07)
- `bench` command with fixture-driven metrics: precision@k, recall, MRR (SRCH-08)

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
- **Reranker backend** — User deferred to Claude. Decision: support GGUF cross-encoder via llama-cpp-python as the primary local-first backend, with optional sentence-transformers HF cross-encoder fallback for compatibility. Reranker settings should be independent from embedder settings (`reranker_model_name`, `reranker_model_path`, `reranker_model_type`).
- **Query expansion mechanism** — User deferred to Claude. Decision: implement embedding-based pseudo-relevance feedback as the default local mechanism (reuses existing `EmbeddingManager`), with optional LLM-based expansion when a local GGUF LLM or OpenAI-compatible API is configured.
- **Query prefix semantics** — User deferred to Claude. Decision: prefixes act as mutually exclusive mode switches on the entire query string. `lex:` forces BM25-only, `vec:` forces vector-only, `hyde:` generates a hypothetical document and searches by vector, `expand:` runs the default hybrid search with query expansion enabled.
- **Explain output format** — User deferred to Claude. Decision: attach a structured `scores` dictionary to each result (visible in JSON output) containing `bm25_score`, `vector_score`, `rrf_score`, and `reranker_score`. In rich table output, append a concise "Explain" column or footer line when space permits. When stages are skipped, their scores are `null` rather than omitted.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` § Advanced Search Pipeline — SRCH-01 through SRCH-08, CLI-06, CLI-07
- `.planning/ROADMAP.md` § Phase 4: Advanced Search Pipeline — goal and success criteria

### Prior Phase Context
- `.planning/phases/03-embedding-vector-search/03-CONTEXT.md` — Embedding backend configuration patterns, `model_type` and `Settings.model_copy(update=...)` override pattern
- `.planning/phases/01-foundation-fix/01-CONTEXT.md` — Vector search must fail fast; heavy ML libraries remain optional extras
- `.planning/phases/02-cli-core-completion/02-CONTEXT.md` — `pull` HF primary / ModelScope fallback decision

### Existing Code (Patterns to Follow)
- `src/docsift/search/hybrid.py` — `HybridSearcher`, `SearchPipeline`, `search_with_reranking()` hooks
- `src/docsift/search/rerank.py` — `Reranker` class with placeholder `rerank()` implementation
- `src/docsift/search/expansion.py` — `QueryExpansion` placeholder
- `src/docsift/search/vector.py` — `VectorSearcher` with sqlite-vec integration
- `src/docsift/search/bm25.py` — `BM25Searcher` and highlight logic
- `src/docsift/search/rrf.py` — `RRFFusion` for result fusion
- `src/docsift/cli/commands/search.py` — `search_cmd`, `vsearch_cmd`, `query_cmd` with existing option patterns
- `src/docsift/core/models.py` — `SearchResult`, `SearchOptions`, `Reranker` protocol, `QueryExpander` protocol
- `src/docsift/config/settings.py` — Pydantic Settings with `DOCSIFT_` env prefix
- `src/docsift/embedding/manager.py` — `EmbeddingManager` for batch inference and model loading

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `HybridSearcher` already combines BM25 + Vector + RRF; `search_with_reranking()` accepts an optional `reranker` argument.
- `SearchPipeline` already has skeleton logic for query expansion and final reranking.
- `Reranker` class in `rerank.py` has the right API surface (`rerank(query, results, top_k)`) but is currently a placeholder.
- `QueryExpansion` in `expansion.py` has the right interface (`expand(query) -> str`) but is currently a placeholder returning empty terms.
- `SearchResult` and `SearchOptions` dataclasses in `core/models.py` can be extended with new fields (e.g., `scores` dict, `snippets`) without breaking existing tests.

### Established Patterns
- CLI commands get `index_path` from `ctx.obj`, instantiate `Database`, and operate within `db.connection` blocks.
- Optional heavy ML libraries are imported at runtime with clear `ImportError` messages (`llama-cpp-python`, `sentence-transformers`).
- Settings overrides use `settings.model_copy(update={...})` to avoid Pydantic v2 duplicate-keyword errors (from Phase 03).
- Search formatters (`format_results_json`, `format_results_csv`, etc.) live in `src/docsift/cli/commands/search.py` and accept both dataclass objects and plain dicts.

### Integration Points
- `query_cmd` in `src/docsift/cli/commands/search.py` is the primary entry point for hybrid search; new flags (`--explain`, `--candidate-limit`, `--intent`) should be added there.
- `search_cmd` (BM25-only) and `vsearch_cmd` (vector-only) should also respect `--min-score` and `--full` for consistency.
- `SearchPipeline.search()` is the natural place to wire query expansion, reranking, and explainability.
- The `bench` command should be a new CLI module under `src/docsift/cli/commands/`, registered in `main.py`.

</code_context>

<specifics>
## Specific Ideas

- `hyde:` prefix workflow: generate a hypothetical ideal answer document from the query (using a lightweight local prompt or the configured LLM API), embed it, and run vector search against chunk embeddings.
- `--explain` should store intermediate scores inside `SearchResult.metadata` or a new `SearchResult.scores` field so formatters can display or hide them without re-running search.
- Smart snippet extraction (SRCH-07) can reuse BM25 highlight terms to score sentences within a chunk and return the highest-scoring contiguous window.
- `bench` should accept a JSON fixture path with fields: `queries`, `relevant_docids_per_query`, and optional `collections`. Built-in fixtures are nice-to-have but not required for this phase.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-advanced-search-pipeline*
*Context gathered: 2026-04-16*
