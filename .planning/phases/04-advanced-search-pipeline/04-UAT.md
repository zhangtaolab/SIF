---
status: complete
phase: 04-advanced-search-pipeline
source: [04-VERIFICATION.md]
started: 2026-09-05T01:28:09Z
updated: 2026-09-06T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Snippet relevance on your real index (04-06 backstop truth)
expected: On your real personal index, run `sif search query <terms>` (no --full) and `sif search search <terms>`; read the rendered Snippet column across several queries. The snippet reads as the most relevant excerpt for its query.
result: pass
reported: "修复不达标的问题"
user_verdict: "pass (final post-fix confirmation after quick task 260905-hc3)"
severity: major
evidence: "Scratch index (23 repo docs, 1003 chunks, Qwen3-Embedding-0.6B, reranker off). Hybrid 'RRF fusion ranking' top-1 snippet correct. But 'chunk overlap tokens' and 'sqlite-vec virtual table' snippets landed on markdown section starts (## Configuration Options, CREATE TABLE collections) instead of matched rows; BM25 ~1/3 rows rendered empty Snippet cells (FTS5 stems vs literal find); substring false positive (query 'table' matched 'notable' -> changelog lead shown)."

### 2. Real-model reranking quality (SC 1)
expected: Configure `reranker_model_name` (GGUF cross-encoder or `cross-encoder/ms-marco-MiniLM-L-6-v2`), run `sif search query <terms>` with and without reranking, with `--explain`. Reranked order is more relevant; explain output shows `reranker_score` alongside `bm25_score`/`vector_score`/`rrf_score`.
result: pass
reported: "(executor-observed during user-directed download retry: model downloads OK, then `sif search query` crashes with RuntimeError before any results render)"
severity: blocker
evidence: "After successful 1.11GB download of default reranker Qwen/Qwen3-Reranker-0.6B, `sif search query 'RRF fusion ranking' --explain` raises RuntimeError: Reranking failed: stat: path should be string... not NoneType. Root cause verified: rerank.py load() sets local_path=subdirs[0] of the ModelScope download dir; that repo ships an aux subdir 1_LogitScore/ (57-byte config with true/false token ids) alongside root-level model files, so subdirs[0]=1_LogitScore and AutoTokenizer falls back to BertTokenizer with vocab_file=None. Loading from the download ROOT works (Qwen2TokenizerFast, verified). Secondary: the failure surfaces as a raw 60-line traceback, not click.ClickException, violating the CLI error convention."
resolution: "Fixed during test via quick task 260905-kmv (gap G-04-2, commits ed542f4..0831f41). Re-verified: exit 0, model loads from download root, order reranked with well-separated scores, explain shows reranker_score alongside bm25/vector/rrf for all 5 results. User confirmed: pass."

### 3. HyDE end-to-end with a generation-capable model (SC 2)
expected: Run `sif search query hyde: <question>` with a generation-capable GGUF embedder. A hypothetical document is generated, embedded, vector-searched; no RuntimeError; snippet populated.
result: pass
reported: "你能修复问题吗？"
severity: blocker
user_verdict: "pass"
resolution: "Two stacked fixes: G-04-3 via quick task 260905-sxc (create_completion, commits 9f079b6/67c9ecf) and G-04-4 via quick task 260905-tax (embed shape unwrap, commits 4560127/958262b/04f7504). E2E re-verified on GGUF scratch index (896-dim, Qwen2.5-0.5B-Instruct q4_k_m): hyde: query exit 0, no RuntimeError, hypothetical doc generated (direct reproduction shows coherent answer text), embedded + vector-searched (scores 0.78-0.81), snippets populated on all rows."
evidence: "Pre-check found HyDE unreachable for EVERY shipped embedder: SearchPipeline._generate_hypothetical_document requires the embedder to expose .generate() or .create_completion(), but runtime verification shows none of the 5 embedder classes (SentenceTransformerEmbedder, LlamaCppEmbedder, ModelScopeEmbedder, OpenAIEmbedder, SimpleEmbedder) define either method — LlamaCppEmbedder only has embed/embed_batch/dimension. Any `hyde:` query raises RuntimeError('HyDE search requires a text-generation-capable model (e.g., GGUF)...') before generating anything. SC 2's generation capability was never wired into LlamaCppEmbedder."

### 4. bench on a real corpus (SC 8)
expected: Author a fixture with real queries and judged relevant docids from your index; run `sif bench fixture.json` and `--json`. Table/JSON metrics (precision@k, recall, MRR) are consistent with your manual relevance judgments.
result: pass
evidence: "Fixture: 5 real queries + 16 manually judged relevant docids (from corpus knowledge verified doc-by-doc this session) on the 1024-dim scratch index (23 docs / 1003 chunks, default embedder + reranker). sif bench table and --json agree exactly: MRR 0.7667, precision@1 0.60, precision@5 0.52, precision@10 0.26, recall@5=recall@10 0.8333. Consistent with judgments: first relevant at ranks {1,1,1,2,3} (3/5 queries rank-1), 83% of judged docs in top-5, misses are borderline calls (api-reference for RRF query), values plausible rather than suspiciously perfect."

## Summary

total: 4
passed: 4
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

- gap_id: G-04-1
  truth: "The snippet reads as the most relevant excerpt for its query (the sentence window a human would pick), not an arbitrary lead paragraph."
  status: resolved
  reason: 'User reported: "修复不达标的问题" (accepting evidence: hybrid snippets land on markdown section starts instead of matched lines; BM25 ~1/3 rows empty Snippet cells; substring false positive notable/table)'
  severity: major
  test: 1
  root_cause: "Two independent causes. (1) SmartSnippetExtractor splits sentences only on .!? — markdown headings/lists/tables/code blocks become giant pseudo-sentences; term-count scoring selects the block and _build_window renders from its start (section header) instead of the matched line. (2) BM25Searcher._get_highlights gates chunks with literal `term in chunk_lower` and _extract_snippet uses str.find, while FTS5 matches stemmed tokens (ranking<->rank), so stem-mismatched docs get zero highlights -> empty Snippet cells; literal substring matching also false-positives inside words (table inside notable)."
  artifacts:
    - path: "src/sif/search/snippets.py"
      issue: "sentence splitting blind to markdown structure; window renders block start"
    - path: "src/sif/search/bm25.py"
      issue: "literal substring term matching in _get_highlights/_extract_snippet"
  missing:
    - "Markdown line-aware snippet extraction with matched-line centering in SmartSnippetExtractor"
    - "Stem-tolerant, word-boundary term matching shared by BM25 highlights (CJK via substring)"
  debug_session: ""
  resolved_by: "quick task 260905-hc3 (commits a4887de, 2d99c86, f85747a, 89a8a5e — src/sif/search/term_match.py new; snippets.py line-aware rewrite; bm25.py routed through shared matcher)"
  resolved_at: 2026-09-05
  verification: "Rerun on same scratch index: hybrid 'chunk overlap tokens' -> SIF_CHUNK_OVERLAP/DOCSIFT_CHUNK_OVERLAP rows; 'sqlite-vec virtual table' -> CREATE VIRTUAL TABLE ... vec0 sections; BM25 'RRF fusion ranking' 9/9 rows populated (was 6/9); changelog lead-paragraph notable/table false positive gone; CJK 向量搜索 3/3 rows populated (was 0/4). Suite: ruff clean, format clean, pytest 608 passed / 11 skipped / 0 failed."

- gap_id: G-04-2
  truth: "Reranked order is more relevant; explain output shows reranker_score alongside bm25_score/vector_score/rrf_score."
  status: resolved
  reason: 'Executor-observed during user-directed download retry: default reranker Qwen/Qwen3-Reranker-0.6B downloads successfully, then `sif search query --explain` crashes with RuntimeError before rendering results (raw traceback, not ClickException).'
  severity: blocker
  test: 2
  root_cause: "rerank.py Qwen3Reranker.load() resolves local_path = subdirs[0] of the ModelScope download directory. Qwen/Qwen3-Reranker-0.6B ships its real model files at the download ROOT plus an aux subdir 1_LogitScore/ (57-byte config holding true/false token ids); subdirs[0] picks 1_LogitScore, so AutoTokenizer sees a config without model_type, falls back to BertTokenizer with vocab_file=None and raises TypeError, which SearchPipeline wraps as RuntimeError and the CLI surfaces as a raw traceback."
  artifacts:
    - path: "src/sif/search/rerank.py"
      issue: "local_path = subdirs[0] picks aux 1_LogitScore dir instead of model root"
    - path: "src/sif/cli/commands/search.py"
      issue: "pipeline RuntimeError propagates as traceback instead of click.ClickException"
  missing:
    - "Model-dir resolution preferring a directory containing a real model config (config.json with model_type) — download root before aux subdirs"
    - "Regression test with a mock download dir containing an aux subdir"
    - "query_cmd wraps pipeline.search RuntimeError into click.ClickException per CLI error convention"
  debug_session: ""
  resolved_by: "quick task 260905-kmv (commits ed542f4, bdb4cce, 3e7b9b9, 0831f41 — _resolve_model_dir resolver wired into Qwen3Reranker.load and CrossEncoderReranker.load; query_cmd ClickException wrap; 9 new tests)"
  resolved_at: 2026-09-05
  verification: "Rerun `sif search query 'RRF fusion ranking' -n 5 --explain` with default reranker on scratch index: exit 0, 'Qwen3 reranker model loaded successfully' (loads from download root), results render, order reranked (Changelog 0.3573 > 测试报告 0.0895 > Search Algorithms 0.0802 vs no-reranker order Search Algorithms > API Reference > Changelog), explain prints reranker_score alongside bm25_score/vector_score/rrf_score for all 5 results. Suite: ruff clean, format clean, pytest 617 passed / 11 skipped / 0 failed."

- gap_id: G-04-3
  truth: "HyDE: a hypothetical document is generated, embedded, vector-searched; no RuntimeError; snippet populated."
  status: resolved
  reason: 'User reported: "你能修复问题吗？" (accepting pre-check finding: hyde: queries always raise RuntimeError because no embedder class implements the required generation API)'
  severity: blocker
  test: 3
  root_cause: "SearchPipeline._generate_hypothetical_document (hybrid.py ~line 315-350) gates on hasattr(embedder, 'generate') / hasattr(embedder, 'create_completion'), but LlamaCppEmbedder (the only GGUF embedder, the one the feature targets) implements only embed/embed_batch/dimension — the generation methods were specified in the HyDE design but never wired into the embedder. Every shipped embedder class fails the capability check, so `hyde:` queries raise RuntimeError before any generation."
  artifacts:
    - path: "src/sif/embedding/embedder.py"
      issue: "LlamaCppEmbedder lacks create_completion/generate; HyDE contract unimplementable"
  missing:
    - "LlamaCppEmbedder.create_completion(prompt, max_tokens, temperature, stop) wrapping llama_cpp Llama.create_completion with openai-style {'choices': [{'text': ...}]} return shape matching the HyDE call site"
    - "Unit test with a stubbed llama_cpp Llama verifying the wrapper contract (prompt passthrough, stop/max_tokens, return shape)"
  debug_session: ""
  resolved_by: "quick task 260905-sxc (commits 9f079b6, 67c9ecf — LlamaCppEmbedder.create_completion delegation wrapper + 4 contract tests; CreateCompletionResponse subclasses dict so the HyDE subscript contract holds)"
  resolved_at: 2026-09-05
  verification: "hasattr(LlamaCppEmbedder, 'create_completion') now True (HyDE gate passes); unit tests verify kwarg forwarding, defaults, openai-dict propagation. Suite 621 passed / 0 failed. End-to-end hyde: run pending G-04-4 fix (GGUF embed shape bug blocks indexing, separate gap)."

- gap_id: G-04-4
  truth: "HyDE: a hypothetical document is generated, embedded, vector-searched; no RuntimeError; snippet populated."
  status: resolved
  reason: 'Discovered during test 3 re-verification after G-04-3 fix: `sif index embed` with GGUF embedder reports "Embedding complete: 0 chunks embedded" + pydantic float_type validation errors on EmbeddingResponse.embeddings — GGUF embeddings have never been persistable.'
  severity: blocker
  test: 3
  root_cause: "llama_cpp.Llama.embed() returns a LIST of embeddings ("A list of embeddings" per its docstring) — List[List[float]] for pooled models, and List[List[List[float]]] token-level when pooling_type is NONE (true for decoder-only GGUFs like Qwen2.5-0.5B-Instruct with no pooling layer). LlamaCppEmbedder.embed treats the return as a flat vector: np normalization preserves the nesting and .tolist() returns [[...]] per text, so EmbeddingResponse (embeddings: list[list[float]]) receives a triple-nested payload and pydantic rejects every entry; the embed CLI swallows the exception per collection ("Embedding failed for 1 collection(s)") leaving 0 chunks embedded."
  artifacts:
    - path: "src/sif/embedding/embedder.py"
      issue: "LlamaCppEmbedder.embed does not unwrap llama_cpp's list-of-embeddings return shape nor mean-pool token-level embeddings"
  missing:
    - "Shape-aware embed(): unwrap single-sequence List[List[float]]; mean-pool token-level List[List[List[float]]] over axis 0 before normalization"
    - "Unit tests with stubbed llama_cpp returns covering both shapes (pooled and token-level)"
  debug_session: ""
  resolved_by: "quick task 260905-tax (commits 4560127, 958262b, 04f7504 — _unwrap_embedding shape-aware embed: 1-D passthrough, 2-D mean-pool axis 0, 3-D unwrap+mean-pool; 8 new tests)"
  resolved_at: 2026-09-05
  verification: "sif index embed with Qwen2.5-0.5B-Instruct q4_k_m: 1003 chunks embedded (was 0). NOTE: pre-fix runs had cached malformed nested vectors under cache bucket gguf:<model_name>; purged gguf:* rows from /Users/forrest/Library/Caches/sif/embeddings_cache.db before re-embed (cache bucket key omits model_path — recorded as deferred follow-up)."

## Deferred Follow-Ups

- test: 3
  idea: "Embedding cache bucket key (f"{model_type}:{model_name}") omits model_path — switching GGUF files under the same model_name reuses another file's cached vectors; also lets malformed pre-fix vectors resurrect post-fix (bit us during G-04-4 verification, resolved by purging gguf:* rows). Include model_path (or content hash of it) in _cache_model_id."
  deferred_at: 2026-09-05
- test: 3
  idea: "2 pre-existing caplog test failures (setup_logging sets sif logger propagate=False, poisoning caplog after test_docs.py CLI runs) — proven unrelated via minimal repro; suggested conftest logger-state snapshot fixture. Details: .planning/quick/260905-tax-fix-g-04-4-gguf-embed-shape-unwrap-llama/deferred-items.md"
  deferred_at: 2026-09-05
