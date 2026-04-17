# Phase 04: Advanced Search Pipeline - Research

**Researched:** 2026-04-17
**Domain:** Information retrieval, hybrid search, cross-encoder reranking, query expansion, benchmark evaluation
**Confidence:** HIGH

## Summary

This phase implements an advanced search pipeline for DocSift, adding LLM reranking, query expansion, query prefix syntax, explainability, search quality controls, smart snippet extraction, and benchmark evaluation. The codebase already has skeleton implementations (`HybridSearcher`, `SearchPipeline`, `Reranker`, `QueryExpansion`) and well-defined protocols, but they are currently placeholders.

**Key architectural insight:** DocSift has **dual model systems** — `docsift.core.models` (dataclasses) used by the search engine internals, and `docsift.models.search` (Pydantic) used by tests and some newer modules. The `Reranker` class in `src/docsift/search/rerank.py` imports from `docsift.models.search` (Pydantic), while `BM25Searcher`/`VectorSearcher`/`HybridSearcher` import from `docsift.core.models` (dataclasses). This inconsistency must be resolved during implementation.

**Primary recommendation:** Unify on `docsift.core.models` dataclasses for the search pipeline (adding missing fields like `scores` dict), keep Pydantic models for API/MCP boundaries. Implement the reranker with optional backends (sentence-transformers CrossEncoder primary, llama-cpp-python fallback), implement embedding-based pseudo-relevance feedback for query expansion, and wire everything through `SearchPipeline` with prefix-based query routing.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Query prefix parsing (`lex:`, `vec:`, etc.) | CLI / API | — | User input transformation happens at entry point before search execution |
| BM25 search | Database (SQLite FTS5) | — | FTS5 virtual tables with triggers handle all keyword search |
| Vector search | Database (sqlite-vec) | — | sqlite-vec extension handles kNN similarity inside SQLite |
| RRF fusion | Application (Python) | — | Score aggregation is business logic, not storage |
| Cross-encoder reranking | Application (Python) | — | Model inference happens in Python, not DB |
| Query expansion | Application (Python) | — | Embedding-based PRF or LLM generation |
| Score explainability | Application (Python) | — | Score tracking across pipeline stages |
| Snippet extraction | Application (Python) | — | Text processing on retrieved chunks |
| Benchmark metrics | CLI / Application | — | Pure computation over search results |
| Result formatting | CLI (Rich/console) | — | Presentation layer concern |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sentence-transformers | 5.4.1 | Cross-encoder reranking (`CrossEncoder`) | [VERIFIED: pip index] Gold standard for reranking; `rank()` and `predict()` APIs stable since v2.x |
| sqlite-vec | 0.1.9 | Vector search via SQLite extension | [VERIFIED: pyproject.toml] Already project dependency; kNN with cosine distance |
| numpy | 1.24.0+ | Vector math, score normalization | [VERIFIED: pyproject.toml] Required by both ST and sqlite-vec |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| llama-cpp-python | latest (optional extra) | GGUF cross-encoder reranker | [CITED: GitHub llama.cpp #8555] When user wants local-first without downloading HF models; requires `pooling_type=LLAMA_POOLING_TYPE_RANK` |
| rich | 13.0.0+ | CLI table output with explain columns | [VERIFIED: pyproject.toml] Already used for all CLI formatting |
| click | 8.0.0+ | CLI option parsing | [VERIFIED: pyproject.toml] Already project dependency |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| sentence-transformers CrossEncoder | llama-cpp-python `LlamaEmbedding` with `pooling_type=RANK` | GGUF models are smaller and faster but quality varies; ST has better ecosystem |
| embedding-based PRF | LLM-based expansion (OpenAI API) | PRF is local and fast; LLM expansion requires API key and adds latency. Decision: PRF as default, LLM as optional. [from CONTEXT.md] |
| custom RRF | sqlite-vec hybrid SQL | Custom RRF gives more control over score tracking and explainability |

**Installation:**
```bash
# Core (already in pyproject.toml dependencies)
# sentence-transformers is in [project.optional-dependencies] "embed" and "all"

# For reranking support:
pip install -e ".[embed]"  # pulls sentence-transformers

# For GGUF reranker support (optional):
pip install llama-cpp-python
```

**Version verification:**
- `sentence-transformers`: 5.4.1 verified via `pip index versions` [VERIFIED]
- `sqlite-vec`: 0.1.9 verified via `python -c "import sqlite_vec; print(sqlite_vec.__version__)")` [VERIFIED]

## Architecture Patterns

### System Architecture Diagram

```
User Query
    |
    v
[Query Parser] --(prefix: lex:/vec:/hyde:/expand:)--> [Search Mode Router]
    |                                                    |
    | no prefix                                          |
    v                                                    v
[SearchPipeline.search()]                          [BM25Searcher] (lex:)
    |                                                    |
    v                                              [VectorSearcher] (vec:)
[QueryExpansion.expand()] (if expand: or default)      |
    |                                              [HydeGenerator] (hyde:)
    v                                                    |
[HybridSearcher.search()] <----------------------------+
    |
    +---> [BM25Searcher.search()] ----+
    |                                  |
    +---> [VectorSearcher.search()] ---+---> [RRFFusion.fuse()] ---> fused results
    |                                                              |
    v                                                              v
[ScoreTracker] (if --explain)                              [Reranker.rerank()] (if configured)
    |                                                              |
    | scores: {bm25_score, vector_score,                          | reranker_score
    |          rrf_score, reranker_score}                          |
    v                                                              v
[ResultFormatter] <----------------------------------------------+
    |
    +---> Rich table (with explain column/footer)
    +---> JSON (with scores dict)
    +---> CSV / MD / XML
```

### Recommended Project Structure

```
src/docsift/
├── search/
│   ├── __init__.py          # Exports: BM25Searcher, VectorSearcher, HybridSearcher, SearchPipeline, RRFFusion
│   ├── bm25.py              # BM25Searcher (existing, needs min_score fix)
│   ├── vector.py            # VectorSearcher (existing, distance->score conversion)
│   ├── hybrid.py            # HybridSearcher + SearchPipeline (needs wiring)
│   ├── rrf.py               # RRFFusion (existing, needs score preservation)
│   ├── rerank.py            # Reranker class (placeholder -> real implementation)
│   ├── expansion.py         # QueryExpansion (placeholder -> real implementation)
│   ├── snippets.py          # NEW: SmartSnippetExtractor
│   └── benchmark.py         # NEW: SearchEvaluator with precision@k, recall, MRR
├── cli/commands/
│   ├── search.py            # query_cmd with new flags (--explain, --candidate-limit, --intent)
│   └── bench.py             # NEW: bench command
├── core/models.py           # SearchResult + SearchOptions (add scores dict, snippet field)
└── config/settings.py       # Add reranker_* settings fields
```

### Pattern 1: Optional Heavy ML Import with Graceful Degradation
**What:** Import sentence-transformers/llama-cpp-python at runtime with clear error messages.
**When to use:** All optional ML backends (embedders, rerankers).
**Example:**
```python
# Source: CLAUDE.md + existing codebase pattern
try:
    from sentence_transformers import CrossEncoder
except ImportError:
    logger.error("sentence-transformers not installed. Install with: pip install -e '.[embed]'")
    raise
```

### Pattern 2: Score Tracking Across Pipeline Stages
**What:** Attach a `scores` dictionary to each `SearchResult` that records intermediate scores from each stage.
**When to use:** When `--explain` is enabled.
**Example:**
```python
# Source: 04-CONTEXT.md decision
@dataclass
class SearchResult:
    document_id: str
    title: str
    path: str
    collection_name: str
    score: float
    content: Optional[str] = None
    highlights: List[str] = field(default_factory=list)
    rank: int = 0
    scores: Dict[str, Optional[float]] = field(default_factory=dict)  # NEW
    snippet: Optional[str] = None  # NEW for SRCH-07
```

### Pattern 3: Query Prefix Router
**What:** Parse query string prefix to determine search mode, strip prefix before executing.
**When to use:** CLI `query_cmd` entry point.
**Example:**
```python
# Source: 04-CONTEXT.md decision
PREFIX_MAP = {
    "lex:": SearchType.BM25,
    "vec:": SearchType.VECTOR,
    "hyde:": SearchType.HYDE,
    "expand:": SearchType.EXPAND,
}

def parse_query_prefix(query: str) -> tuple[str, SearchType]:
    for prefix, search_type in PREFIX_MAP.items():
        if query.startswith(prefix):
            return query[len(prefix):].strip(), search_type
    return query, SearchType.HYBRID
```

### Pattern 4: Settings Override Pattern
**What:** Use `settings.model_copy(update={...})` for CLI overrides to avoid Pydantic v2 duplicate-keyword errors.
**When to use:** Any CLI option that overrides a Settings field.
**Example:**
```python
# Source: 04-CONTEXT.md established pattern
settings = get_settings()
if model_type:
    settings = settings.model_copy(update={"model_type": model_type})
```

### Anti-Patterns to Avoid
- **Mixing dataclass and Pydantic SearchResult in the same pipeline:** The current `Reranker` uses Pydantic `SearchResult` while `HybridSearcher` uses dataclass `SearchResult`. This causes type mismatches and silent failures. Unify on one type.
- **Silent fallback on reranker failure:** Current `search_with_reranking()` catches all exceptions and prints a warning. Per project conventions, optional components should fail fast with `click.ClickException` at the CLI layer, not silently degrade.
- **Storing raw sqlite-vec distances as scores:** Current `VectorSearcher` converts distance to score with `1.0 - (distance / 2.0)`. This assumes cosine distance but sqlite-vec may use other metrics. Verify the actual metric or use `vec_distance_cosine()` explicitly.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cross-encoder reranking | Custom neural network inference | `sentence_transformers.CrossEncoder` | Handles tokenization, batching, padding, model caching, ONNX backend. [CITED: sbert.net docs] |
| RRF fusion | Custom score aggregation | `RRFFusion` (existing) | Already implemented, well-tested formula. Just needs score preservation. |
| IR evaluation metrics | Custom precision/recall/MRR | Pure Python implementation (20-30 lines each) | Metrics are simple enough to hand-roll correctly, but `ir_evaluation` package exists if we want zero-dependency. [CITED: plurch/ir_evaluation] |
| Query expansion with embeddings | Custom nearest-neighbor over vocabulary | Embedding-based PRF using existing `EmbeddingManager` | Reuses existing infrastructure; no new dependencies. |
| BM25 highlighting | Custom text search | Existing `_get_highlights()` in `BM25Searcher` | Already implemented; just needs snippet scoring integration. |

**Key insight:** The reranker is the only component where a library is clearly superior to hand-rolling. Cross-encoders require careful tokenization, batching, and model management that `sentence-transformers` handles expertly.

## Runtime State Inventory

This phase is a greenfield feature addition (filling placeholders), not a rename/refactor. No runtime state inventory needed.

## Common Pitfalls

### Pitfall 1: Dual SearchResult Model Confusion
**What goes wrong:** `docsift.core.models.SearchResult` (dataclass, 8 fields) and `docsift.models.search.SearchResult` (Pydantic, 11 fields) are different types. The `Reranker` class imports Pydantic but `HybridSearcher` produces dataclass instances. Passing dataclass results to `Reranker.rerank()` will fail on attribute access (`document_path` vs `path`).
**Why it happens:** Two model systems evolved independently. Tests use Pydantic fixtures; search engine uses dataclasses.
**How to avoid:** Unify `SearchResult` to a single type. Recommended: extend the dataclass in `core/models.py` with `scores` dict and `snippet` fields, then update `Reranker` to use it. Update test fixtures accordingly.
**Warning signs:** `AttributeError: 'SearchResult' object has no attribute 'document_path'` during reranking.

### Pitfall 2: sqlite-vec Distance Metric Assumption
**What goes wrong:** `VectorSearcher._search_with_vec()` assumes cosine distance with `score = 1.0 - (row["score"] / 2.0)`. If sqlite-vec is configured with L2 distance, this normalization is wrong.
**Why it happens:** sqlite-vec supports multiple distance metrics; the default depends on table creation.
**How to avoid:** Verify the distance metric used in `document_embeddings` vec0 table, or use `vec_distance_cosine()` explicitly in SQL. The schema in `schema.py` creates `FLOAT[{dim}]` which defaults to L2 in some sqlite-vec versions.
**Warning signs:** Vector scores outside [0, 1] range, or scores that don't correlate with semantic similarity.

### Pitfall 3: Cross-Encoder Score Range Mismatch
**What goes wrong:** `CrossEncoder.predict()` returns raw logits (can be negative, unbounded). If stored directly in `SearchResult.score` (which has `ge=0, le=1` validation in Pydantic model), validation fails.
**Why it happens:** Cross-encoders output logits, not probabilities. The current `Reranker` placeholder uses original scores which are already normalized.
**How to avoid:** Apply sigmoid or min-max normalization to cross-encoder scores before storing, or remove the score bounds from `SearchResult`.
**Warning signs:** `pydantic.ValidationError: Input should be greater than or equal to 0` when reranker is enabled.

### Pitfall 4: Query Expansion Infinite Loop
**What goes wrong:** If `QueryExpansion.expand()` is called on an already-expanded query, or if expansion terms include the original query terms, the pipeline could loop or produce redundant searches.
**Why it happens:** `SearchPipeline.search()` runs hybrid search for each expanded query variant, then fuses all results. Duplicate queries waste compute.
**How to avoid:** Deduplicate expanded queries before searching. Track original vs expanded queries separately.
**Warning signs:** Search latency increases linearly with expansion factor; duplicate documents in fused results.

### Pitfall 5: Reranker Candidate Pool Too Large
**What goes wrong:** Passing hundreds of candidates to a cross-encoder causes excessive latency (seconds per query).
**Why it happens:** Cross-encoders are O(n) in candidate count and much slower than bi-encoders.
**How to avoid:** Use `--candidate-limit` / `-C` to cap candidates entering the reranker. Default to 20-50. Document this clearly.
**Warning signs:** Query latency > 5 seconds on CPU.

## Code Examples

### Verified patterns from official sources:

### Cross-Encoder Reranker Implementation
```python
# Source: [CITED: sentence-transformers docs / WebSearch verified]
from typing import List, Optional
from docsift.core.models import SearchResult
from docsift.utils.logging import get_logger

logger = get_logger(__name__)

class CrossEncoderReranker:
    """Reranker using sentence-transformers CrossEncoder."""
    
    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        model_path: Optional[str] = None,
        device: Optional[str] = None,
        batch_size: int = 32,
    ) -> None:
        try:
            from sentence_transformers import CrossEncoder
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install -e '.[embed]'"
            )
        
        self.batch_size = batch_size
        self.model = CrossEncoder(
            model_path or model_name,
            device=device,
            max_length=512,
        )
    
    def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_k: int = 10,
    ) -> List[SearchResult]:
        if not results:
            return []
        
        # Build query-document pairs using content or snippet
        pairs = [
            (query, result.content or result.highlights[0] if result.highlights else "")
            for result in results
        ]
        
        # Score all pairs
        scores = self.model.predict(pairs, batch_size=self.batch_size)
        
        # Normalize scores to [0, 1] using sigmoid
        import math
        normalized = [1.0 / (1.0 + math.exp(-s)) for s in scores]
        
        # Sort by score descending
        scored = list(zip(results, normalized))
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # Rebuild results with new scores and ranks
        reranked = []
        for rank, (result, score) in enumerate(scored[:top_k], 1):
            result.score = score
            result.rank = rank
            reranked.append(result)
        
        return reranked
```

### Query Expansion with Embedding-Based PRF
```python
# Source: [ASSUMED: standard IR technique, verified against codebase capabilities]
from typing import List, Optional
from docsift.embedding.manager import EmbeddingManager
from docsift.utils.logging import get_logger

logger = get_logger(__name__)

class EmbeddingQueryExpansion:
    """Expand query using embedding-based pseudo-relevance feedback."""
    
    def __init__(
        self,
        embedding_manager: EmbeddingManager,
        expansion_factor: int = 3,
    ) -> None:
        self._embedding_manager = embedding_manager
        self._expansion_factor = expansion_factor
    
    def expand(self, query: str) -> List[str]:
        """Return list of expanded query variants."""
        # Embed the query
        query_embedding = self._embedding_manager.embed_single(query)
        
        # Find similar terms from vocabulary (simplified)
        # In practice: retrieve top-k chunks, extract keywords, embed, find nearest
        expansion_terms = self._find_similar_terms(query, query_embedding)
        
        # Return expanded variants
        variants = [query]
        for term in expansion_terms[:self._expansion_factor]:
            variants.append(f"{query} {term}")
        
        return variants
    
    def _find_similar_terms(
        self,
        query: str,
        query_embedding: List[float],
    ) -> List[str]:
        # Placeholder: would query indexed chunks for nearest neighbors
        # and extract distinctive terms
        return []
```

### Benchmark Metrics Implementation
```python
# Source: [CITED: plurch/ir_evaluation + WebSearch verified]
from typing import List, Dict, Sequence

def precision_at_k(relevance: Sequence[int], k: int) -> float:
    """Precision@K: relevant items in top-K / K."""
    if k == 0:
        return 0.0
    return sum(relevance[:k]) / k

def recall_at_k(relevance: Sequence[int], total_relevant: int, k: int) -> float:
    """Recall@K: relevant items retrieved / total relevant."""
    if total_relevant == 0:
        return 0.0
    return sum(relevance[:k]) / total_relevant

def reciprocal_rank(relevance: Sequence[int]) -> float:
    """Reciprocal rank: 1 / rank of first relevant item."""
    for i, rel in enumerate(relevance, start=1):
        if rel:
            return 1.0 / i
    return 0.0

def mean_reciprocal_rank(all_relevance: List[Sequence[int]]) -> float:
    """Mean Reciprocal Rank across queries."""
    rr_scores = [reciprocal_rank(r) for r in all_relevance]
    return sum(rr_scores) / len(rr_scores) if rr_scores else 0.0

class SearchEvaluator:
    """Evaluate search quality against a benchmark fixture."""
    
    def __init__(self, fixture_path: str):
        self.fixture = self._load_fixture(fixture_path)
    
    def evaluate(
        self,
        search_fn,
        k_values: List[int] = None,
    ) -> Dict[str, float]:
        k_values = k_values or [1, 5, 10]
        metrics = {}
        
        all_relevance = []
        for query_item in self.fixture["queries"]:
            query = query_item["query"]
            relevant_ids = set(query_item["relevant_docids"])
            
            results = search_fn(query)
            result_ids = [r.document_id for r in results]
            relevance = [1 if rid in relevant_ids else 0 for rid in result_ids]
            all_relevance.append(relevance)
            
            for k in k_values:
                metrics.setdefault(f"precision@{k}", []).append(
                    precision_at_k(relevance, k)
                )
                metrics.setdefault(f"recall@{k}", []).append(
                    recall_at_k(relevance, len(relevant_ids), k)
                )
        
        # Average across queries
        averaged = {k: sum(v) / len(v) for k, v in metrics.items()}
        averaged["mrr"] = mean_reciprocal_rank(all_relevance)
        
        return averaged
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Bi-encoder only (embedding similarity) | Bi-encoder retrieve + cross-encoder rerank | 2020+ (ST v2+) | 15-30% relevance improvement at cost of latency |
| Query expansion via synonym dictionaries | Embedding-based pseudo-relevance feedback | 2023+ | Better domain adaptation, no dictionary maintenance |
| Score normalization by fixed formula | Metric-aware normalization (cosine vs L2) | 2024+ | More accurate score comparisons across metrics |
| Single search type (BM25 or vector) | Hybrid with RRF fusion | 2022+ (Cohere, Pinecone) | Best of both lexical and semantic matching |

**Deprecated/outdated:**
- `BM25SearchStrategy` / `VectorSearchStrategy` / `HybridSearchStrategy`: These classes exist in tests but not in source. The actual implementations are `BM25Searcher`, `VectorSearcher`, `HybridSearcher`. Tests need updating.
- `SearchContext` from `strategy.py`: Used in broken tests but not in actual search pipeline. The real pipeline uses `SearchOptions` + raw query string.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Reranker backend** — Support GGUF cross-encoder via llama-cpp-python as primary local-first backend, with optional sentence-transformers HF cross-encoder fallback. Reranker settings independent from embedder settings (`reranker_model_name`, `reranker_model_path`, `reranker_model_type`).
- **Query expansion mechanism** — Embedding-based pseudo-relevance feedback as default local mechanism (reuses existing `EmbeddingManager`), with optional LLM-based expansion when a local GGUF LLM or OpenAI-compatible API is configured.
- **Query prefix semantics** — Prefixes act as mutually exclusive mode switches on the entire query string. `lex:` forces BM25-only, `vec:` forces vector-only, `hyde:` generates a hypothetical document and searches by vector, `expand:` runs the default hybrid search with query expansion enabled.
- **Explain output format** — Structured `scores` dictionary attached to each result (visible in JSON) containing `bm25_score`, `vector_score`, `rrf_score`, and `reranker_score`. In rich table output, append concise "Explain" column or footer line. When stages are skipped, their scores are `null` rather than omitted.

### Claude's Discretion
- Reranker backend selection (GGUF primary, ST fallback) — already decided above.
- Query expansion mechanism — already decided above.
- Query prefix semantics — already decided above.
- Explain output format — already decided above.

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SRCH-01 | Configurable LLM reranker with cross-encoder support | `CrossEncoder` API from sentence-transformers 5.4.1; `LlamaEmbedding` with `pooling_type=RANK` for GGUF. Score normalization via sigmoid required. |
| SRCH-02 | LLM query expansion | Embedding-based PRF reuses `EmbeddingManager.embed_single()`. Optional LLM path via existing `llm_cache` table. |
| SRCH-03 | Query document syntax (`lex:`, `vec:`, `hyde:`, `expand:`) | Prefix router pattern in CLI entry point. `hyde:` requires hypothetical doc generation (prompt template + embed + vector search). |
| SRCH-04 | `--explain` score breakdowns | Extend `SearchResult` with `scores: dict[str, Optional[float]]`. Track scores at each pipeline stage. |
| SRCH-05 | `--candidate-limit` / `-C` for reranker pool | Cap results passed to `Reranker.rerank()` before invocation. Default 20-50. |
| SRCH-06 | `--intent` parameter passed through pipeline | Add `intent: Optional[str]` to `SearchOptions`, propagate to expansion and reranker (e.g., as prompt prefix). |
| SRCH-07 | Smart snippet extraction from chunks | Reuse BM25 highlight terms to score sentences within chunk, return highest-scoring window. Add `snippet` field to `SearchResult`. |
| SRCH-08 | `bench` command with fixture-driven metrics | Pure Python metrics (precision@k, recall, MRR). JSON fixture format: `{queries: [{query, relevant_docids, collections?}]}` |
| CLI-06 | `--min-score` parameter | Already in `SearchOptions` (field exists). Ensure all searchers respect it. Currently `BM25Searcher` and `VectorSearcher` do; verify `HybridSearcher` and `SearchPipeline`. |
| CLI-07 | `--full` parameter | Already in `SearchOptions.include_content`. Ensure all formatters respect it. |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | sqlite-vec `document_embeddings` table uses cosine distance (enabling `score = 1.0 - distance/2.0`) | Common Pitfalls #2 | Score normalization will be incorrect; need to verify actual metric or use explicit `vec_distance_cosine()` |
| A2 | `llama-cpp-python` supports `LlamaEmbedding` with `pooling_type=LLAMA_POOLING_TYPE_RANK` in the version users will install | Standard Stack | If not merged upstream, GGUF reranker path will fail; fallback to sentence-transformers works |
| A3 | Hypothetical document generation for `hyde:` can use the same embedding model with a simple prompt template (no separate LLM required) | Phase Requirements SRCH-03 | If embedding model cannot generate text, `hyde:` requires a separate text-generation model; need to document this dependency |
| A4 | Benchmark fixtures will be user-provided JSON files, not built into the codebase | Phase Requirements SRCH-08 | If built-in fixtures are expected, need to create sample benchmark data |

## Open Questions

1. **sqlite-vec distance metric verification**
   - What we know: `VectorSearcher` assumes cosine distance with `score = 1.0 - (distance / 2.0)`
   - What's unclear: Whether `document_embeddings` vec0 table was created with default metric or explicit cosine
   - Recommendation: Check `schema.py` for vec0 creation SQL; if no metric specified, verify with `sqlite-vec` docs or test query

2. **Unified SearchResult model**
   - What we know: Two incompatible `SearchResult` types exist (dataclass vs Pydantic)
   - What's unclear: Whether Pydantic models are used by MCP/API layer and must be preserved
   - Recommendation: Extend dataclass `SearchResult` with new fields; create converter function for API boundaries if needed

3. **Test file compatibility**
   - What we know: Multiple test files import non-existent classes (`BM25SearchStrategy`, `ParseResult`) and fail collection
   - What's unclear: Whether these tests represent desired future API or stale code
   - Recommendation: Update tests to match actual class names, or rename source classes to match tests

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | Yes | 3.13.9 | — |
| pytest | Testing | Yes | 9.0.2 | — |
| ruff | Linting | Yes | 0.1.x | — |
| mypy | Type checking | Yes | 1.20.1 | — |
| sqlite-vec | Vector search | Yes | 0.1.9 | RuntimeError (fail fast) |
| sentence-transformers | Reranker (SRCH-01) | No (optional extra) | 5.4.1 (verified) | `pip install -e ".[embed]"` |
| llama-cpp-python | GGUF reranker (SRCH-01) | No (optional extra) | latest | Skip GGUF path, use ST only |
| numpy | Math | Yes | 1.24.0+ | — |

**Missing dependencies with no fallback:**
- None — all core dependencies are available.

**Missing dependencies with fallback:**
- `sentence-transformers`: Not installed in current venv, but is declared as optional extra. Install with `pip install -e ".[embed]"`.
- `llama-cpp-python`: Not installed. Fallback to sentence-transformers CrossEncoder for reranking.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` (tool.pytest.ini_options) |
| Quick run command | `pytest tests/unit/search/test_vector.py tests/unit/inference/test_reranker.py -x` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SRCH-01 | Cross-encoder reranking produces reordered results | unit | `pytest tests/unit/inference/test_reranker.py -x` | Yes (needs update for real impl) |
| SRCH-02 | Query expansion returns expanded variants | unit | `pytest tests/unit/inference/test_query_expander.py -x` | Yes (needs update for real impl) |
| SRCH-03 | `lex:` prefix routes to BM25 only | integration | `pytest tests/integration/test_search_pipeline.py -x` | Yes (broken imports — fix first) |
| SRCH-04 | `--explain` includes scores dict in JSON output | unit | New test needed | No — Wave 0 |
| SRCH-05 | `--candidate-limit` caps reranker input | unit | New test needed | No — Wave 0 |
| SRCH-06 | `--intent` propagates to search pipeline | unit | New test needed | No — Wave 0 |
| SRCH-07 | Smart snippet extraction scores sentences | unit | New test needed | No — Wave 0 |
| SRCH-08 | `bench` command computes precision@k, recall, MRR | integration | New test needed | No — Wave 0 |
| CLI-06 | `--min-score` filters results | unit | `pytest tests/unit/search/test_vector.py::TestVectorSearcher::test_search_applies_min_score -x` | Yes |
| CLI-07 | `--full` includes document content | unit | New test needed | No — Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/unit/search/ -x --ignore=tests/unit/search/test_bm25.py --ignore=tests/unit/search/test_hybrid.py`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/search/test_reranker.py` — update for real `CrossEncoder` implementation (currently tests placeholder)
- [ ] `tests/unit/search/test_expansion.py` — update for real embedding-based expansion
- [ ] `tests/unit/search/test_snippets.py` — NEW: smart snippet extraction
- [ ] `tests/unit/search/test_benchmark.py` — NEW: benchmark metrics
- [ ] `tests/unit/cli/test_bench.py` — NEW: bench CLI command
- [ ] `tests/integration/test_search_pipeline.py` — fix imports (`BM25SearchStrategy` -> `BM25Searcher`)
- [ ] `tests/unit/search/test_bm25.py` — fix imports (`BM25SearchStrategy` -> `BM25Searcher`)
- [ ] `tests/unit/search/test_hybrid.py` — fix imports (`BM25SearchStrategy` -> `BM25Searcher`)
- [ ] `tests/unit/search/test_rrf.py` — fix `RRFFusion(default_k=60)` -> `RRFFusion(k=60)`
- [ ] Framework install: `pip install -e ".[embed]"` — if sentence-transformers not available

## Security Domain

> Required when `security_enforcement` is enabled (absent = enabled). Omit only if explicitly `false` in config.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Not in scope for this phase |
| V3 Session Management | No | Not in scope for this phase |
| V4 Access Control | No | Not in scope for this phase |
| V5 Input Validation | Yes | Query strings must be sanitized before FTS5 `MATCH` and SQL `LIKE`; use parameterized queries exclusively |
| V6 Cryptography | No | Not in scope for this phase |
| V7 Error Handling | Yes | CLI raises `click.ClickException` for user-facing errors; no stack traces in production |

### Known Threat Patterns for Search Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via query string | Tampering | Parameterized queries (already used in BM25Searcher, VectorSearcher) |
| FTS5 query injection | Tampering | Validate/sanitize query terms before `_build_fts_query()`; reject control characters |
| Prompt injection in `hyde:` / expansion | Tampering | Treat user query as untrusted input; use structured prompts with clear delimiters |
| Information disclosure via `--explain` | Information Disclosure | Scores reveal internal model behavior; acceptable for local-first tool |
| DoS via large `--candidate-limit` | Denial of Service | Cap `--candidate-limit` to reasonable max (e.g., 200) in CLI option validation |

## Sources

### Primary (HIGH confidence)
- `src/docsift/search/rerank.py` — Current `Reranker` placeholder API surface
- `src/docsift/search/expansion.py` — Current `QueryExpansion` placeholder
- `src/docsift/search/hybrid.py` — `HybridSearcher` and `SearchPipeline` skeleton
- `src/docsift/search/bm25.py` — `BM25Searcher` implementation
- `src/docsift/search/vector.py` — `VectorSearcher` with sqlite-vec integration
- `src/docsift/search/rrf.py` — `RRFFusion` implementation
- `src/docsift/core/models.py` — `SearchResult`, `SearchOptions`, `Reranker` protocol, `QueryExpander` protocol
- `src/docsift/config/settings.py` — Pydantic Settings structure
- `src/docsift/embedding/manager.py` — `EmbeddingManager` for batch inference
- `src/docsift/cli/commands/search.py` — CLI command patterns
- `pyproject.toml` — Dependency versions and test configuration

### Secondary (MEDIUM confidence)
- [Sentence Transformers CrossEncoder docs](https://www.sbert.net/docs/cross_encoder/training_overview.html) — CrossEncoder API patterns [WebSearch verified]
- [llama.cpp reranker support #8555](https://github.com/ggml-org/llama.cpp/issues/8555) — GGUF cross-encoder capability [WebSearch verified]
- [sqlite-vec API reference](https://alexgarcia.xyz/sqlite-vec/api-reference.html) — Distance metrics and kNN search [WebSearch verified]
- [plurch/ir_evaluation](https://github.com/plurch/ir_evaluation) — Pure Python IR metrics [WebSearch verified]

### Tertiary (LOW confidence)
- JamePeng fork `LlamaEmbedding` with `LLAMA_POOLING_TYPE_RANK` — may not be in mainline `llama-cpp-python` yet [WebSearch only, needs validation]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified package versions, official docs consulted
- Architecture: HIGH — codebase thoroughly inspected, patterns established
- Pitfalls: HIGH — actual test failures observed and root-caused (dual model issue, score validation, distance metric assumption)

**Research date:** 2026-04-17
**Valid until:** 2026-05-17 (stable stack, low churn expected)
