# Search Algorithms

Deep dive into DocSift's search algorithms and ranking mechanisms.

## Overview

DocSift implements three search strategies:

1. **BM25** - Full-text search using SQLite FTS5
2. **Vector Search** - Semantic similarity using embeddings
3. **Hybrid Search** - Combined approach with RRF fusion

```
┌─────────────────────────────────────────────────────────────┐
│                      Search Pipeline                         │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │    Query     │───►│   Strategy   │───►│   Results    │  │
│  │   Parsing    │    │  Selection   │    │   Ranking    │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                              │                               │
│              ┌───────────────┼───────────────┐               │
│              ▼               ▼               ▼               │
│         ┌────────┐    ┌──────────┐    ┌──────────┐          │
│         │  BM25  │    │  Vector  │    │  Hybrid  │          │
│         └────────┘    └──────────┘    └──────────┘          │
└─────────────────────────────────────────────────────────────┘
```

## BM25 (Best Match 25)

BM25 is a probabilistic ranking function used for full-text search.

### Formula

```
score(D, Q) = Σ IDF(q_i) * (f(q_i, D) * (k1 + 1)) /
              (f(q_i, D) + k1 * (1 - b + b * |D| / avgdl))

Where:
- D: Document
- Q: Query (terms q_1 to q_n)
- f(q_i, D): Term frequency of q_i in D
- |D|: Document length (in tokens)
- avgdl: Average document length
- k1: Term frequency saturation parameter
- b: Length normalization parameter
```

### IDF Calculation

```
IDF(q_i) = log((N - n(q_i) + 0.5) / (n(q_i) + 0.5))

Where:
- N: Total number of documents
- n(q_i): Number of documents containing q_i
```

### Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `k1` | 1.5 | 0.1 - 3.0 | Controls term frequency saturation |
| `b` | 0.75 | 0.1 - 1.0 | Controls length normalization |

### Tuning Guidelines

**High k1 (2.0-3.0):**
- Documents with many occurrences rank higher
- Good for: Technical documentation, long articles

**Low k1 (0.5-1.0):**
- Term frequency has less impact
- Good for: Short documents, titles

**High b (0.8-1.0):**
- Strong length normalization
- Good for: Mixed-length documents

**Low b (0.1-0.3):**
- Weak length normalization
- Good for: Uniform-length documents

### Implementation

```python
from docsift.search.bm25 import BM25Searcher
from docsift.core.models import SearchOptions

searcher = BM25Searcher(db_connection)
options = SearchOptions(limit=10)
results = searcher.search("python decorators", options)
```

### SQLite FTS5 Integration

DocSift uses SQLite FTS5 for BM25 implementation:

```sql
-- Create FTS5 virtual table
CREATE VIRTUAL TABLE documents_fts USING fts5(
    content,
    content='documents',
    content_rowid='rowid',
    tokenize='porter'
);

-- Search with BM25 ranking
SELECT rowid, bm25(documents_fts) as score
FROM documents_fts
WHERE documents_fts MATCH 'python decorators'
ORDER BY score;
```

## Vector Search

Vector search uses embeddings to find semantically similar documents.

### Cosine Similarity

```
similarity(A, B) = (A · B) / (||A|| * ||B||)

Where:
- A, B: Embedding vectors
- A · B: Dot product
- ||A||: Euclidean norm of A
```

### Implementation

```python
from docsift.search.vector import VectorSearcher

searcher = VectorSearcher(db_connection, embedding_dim=1024)
results = searcher.search(query_embedding, options)
```

### Embedding Models

**Supported Models:**

| Model | Dimensions | Best For |
|-------|------------|----------|
| Qwen/Qwen3-Embedding-0.6B | 1024 | Default, high quality |
| sentence-transformers/all-MiniLM-L6-v2 | 384 | Fast, general purpose |
| sentence-transformers/all-mpnet-base-v2 | 768 | Higher quality |

**Model Sources:**
- HuggingFace Hub
- ModelScope (alternative for China region)
- Local GGUF files
- OpenAI-compatible API endpoints

**Model Selection:**
- Use `Qwen/Qwen3-Embedding-0.6B` for best quality (default)
- Use `all-MiniLM-L6-v2` for faster inference
- Consider domain-specific models for specialized content

### Vector Index

DocSift uses sqlite-vec for vector storage:

```sql
-- Create vector table
CREATE VIRTUAL TABLE document_embeddings USING vec0(
    embedding_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    chunk_id TEXT,
    embedding FLOAT[{dim}]  -- dimension from model (default: 1024)
);

-- Search similar vectors
SELECT document_id, distance
FROM document_embeddings
WHERE embedding MATCH ?
ORDER BY distance
LIMIT 10;
```

## Hybrid Search

Hybrid search combines BM25 and vector search using Reciprocal Rank Fusion (RRF).

### Reciprocal Rank Fusion (RRF)

```
RRF_score(d) = Σ 1 / (k + rank_i(d))

Where:
- d: Document
- k: Constant (typically 60)
- rank_i(d): Rank of document d in result set i
```

### Why RRF?

1. **No score normalization needed**: Works with different score ranges
2. **Rank-based**: Focuses on relative ordering
3. **Simple and effective**: Proven performance

### Implementation

```python
from docsift.search.hybrid import HybridSearcher
from docsift.search.bm25 import BM25Searcher
from docsift.search.vector import VectorSearcher

# Create component searchers
bm25 = BM25Searcher(db_connection)
vector = VectorSearcher(db_connection, embedding_dim=1024)

# Create hybrid searcher
hybrid = HybridSearcher(
    db_connection,
    embedder=embedder,
    embedding_dim=1024
)

# Search
results = hybrid.search("python decorators", options)
```

### RRF Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `rrf_k` | 60 | Fusion constant |

**Tuning k:**
- Lower k (20-40): Emphasizes top ranks
- Higher k (80-100): More democratic fusion

### Weighted Combination

For fine-grained control, use weighted scores:

```
final_score = bm25_weight * bm25_score + vector_weight * vector_score

Where:
- bm25_weight + vector_weight = 1.0
```

## Query Expansion

Query expansion improves recall by adding related terms.

### Methods

1. **Synonym Expansion**: Add synonyms
2. **Word Embeddings**: Use similar words from embeddings
3. **Pseudo-relevance Feedback**: Expand using top results

### Implementation

```python
from docsift.search.expansion import QueryExpansion

expander = QueryExpansion(embedding_manager=manager)

expanded = expander.expand("python decorators")
# Result: ["python decorators", "python decorators wrapper function"]
```

## Result Reranking

Reranking improves result quality using a more sophisticated model.

### Cross-Encoder Reranking

```
score = cross_encoder(query, document)
```

Cross-encoders:
- Jointly encode query and document
- More accurate than bi-encoders
- Slower (compute at query time)

### Implementation

```python
from docsift.search.rerank import create_reranker
from docsift.config.settings import get_settings

settings = get_settings()
reranker = create_reranker(settings)

# Rerank top-k results
reranked = reranker.rerank(
    query="python decorators",
    documents=[r.content for r in initial_results],
)
```

## Search Pipeline

Complete search flow with expansion, reranking, and snippet extraction:

```python
from docsift.search.hybrid import SearchPipeline
from docsift.search.expansion import QueryExpansion
from docsift.search.rerank import create_reranker
from docsift.search.snippets import SmartSnippetExtractor

pipeline = SearchPipeline(
    db_connection,
    embedder=manager._model,
    query_expander=QueryExpansion(embedding_manager=manager),
    reranker=create_reranker(settings),
    snippet_extractor=SmartSnippetExtractor(),
    embedding_dim=1024,
)

results = pipeline.search("python decorators", options)
```

The pipeline supports query prefix routing:
- `lex:` prefix for BM25-only search
- `vec:` prefix for vector-only search
- `hyde:` prefix for HyDE (hypothetical document embedding) search
- `expand:` prefix for expanded query search
- No prefix for hybrid search (default)

```
1. Parse Query (including prefix)
   │
   ▼
2. Expand Query (optional)
   │
   ▼
3. Generate Embedding (for vector/hybrid)
   │
   ▼
4. Execute Search Strategy
   │
   ├── BM25: Query FTS5 index
   │
   ├── Vector: Query vector index
   │
   └── Hybrid: Combine with RRF
   │
   ▼
5. Rerank Results (optional)
   │
   ▼
6. Extract Smart Snippets (optional)
   │
   ▼
7. Return Results
```

## Performance Optimization

### Indexing

- **Batch inserts**: Group document insertions
- **Parallel embedding**: Use multiple workers
- **Incremental updates**: Only index changed documents

### Querying

- **Caching**: Cache embeddings and results
- **Early termination**: Stop when score threshold reached
- **Prefetching**: Preload popular documents

### Configuration

```python
# Fast search
fast_options = SearchOptions(
    limit=10,
    include_highlights=False,
)

# Accurate search
accurate_options = SearchOptions(
    limit=20,
    include_highlights=True,
    candidate_limit=50,
)
```

## Benchmarks

Performance varies by hardware and collection size. Run your own benchmarks with:

```bash
docsift bench fixture.json
```

## Comparison

| Feature | BM25 | Vector | Hybrid |
|---------|------|--------|--------|
| Keyword matching | Excellent | Poor | Good |
| Semantic matching | Poor | Excellent | Good |
| Speed | Fast | Medium | Medium |
| Memory | Low | High | High |
| Setup | Simple | Complex | Complex |

## Best Practices

1. **Use BM25 for**: Exact keyword matching, titles, short queries
2. **Use Vector for**: Conceptual search, long queries, semantic similarity
3. **Use Hybrid for**: General-purpose search, best overall quality
4. **Enable expansion for**: Short queries, low recall issues
5. **Enable reranking for**: High-precision requirements

## Related Documentation

- [API Reference](api-reference.md) - Search API usage
- [Models](models.md) - Search model definitions
- [Architecture](architecture.md) - Search architecture
