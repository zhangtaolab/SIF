---
phase: 04-advanced-search-pipeline
reviewed: 2026-09-05T00:00:00Z
depth: standard
files_reviewed: 21
files_reviewed_list:
  - src/sif/core/models.py
  - src/sif/config/settings.py
  - src/sif/search/rrf.py
  - src/sif/search/rerank.py
  - src/sif/search/expansion.py
  - src/sif/search/snippets.py
  - src/sif/search/hybrid.py
  - src/sif/search/benchmark.py
  - src/sif/cli/commands/search.py
  - src/sif/cli/commands/bench.py
  - src/sif/cli/main.py
  - tests/unit/search/test_rrf.py
  - tests/unit/inference/test_reranker.py
  - tests/unit/inference/test_query_expander.py
  - tests/unit/search/test_snippets.py
  - tests/unit/search/test_hybrid.py
  - tests/integration/test_search_pipeline.py
  - tests/unit/cli/test_search.py
  - tests/unit/search/test_benchmark.py
  - tests/unit/cli/test_bench.py
  - tests/unit/search/test_bm25.py
findings:
  critical: 3
  warning: 12
  info: 9
  total: 24
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-09-05
**Depth:** standard
**Files Reviewed:** 21
**Status:** issues_found

## Summary

Reviewed the advanced search pipeline (RRF fusion, rerankers, query expansion, smart snippets, hybrid/pipeline routing, benchmark evaluator, CLI `search`/`query`/`vsearch`/`bench` commands) plus supporting cross-referenced modules (`bm25.py`, `vector.py`, `embedding/manager.py`, `cli/formatters.py`, `utils/logging.py`).

Three confirmed critical defects: (1) `--line-numbers` combined with `--csv`/`--md`/`--xml` crashes with `AttributeError` (reproduced); (2) `cli/main.py` references `sqlite3` in an exception handler without importing it — the handler itself raises `NameError` when triggered; (3) vector-only search routes return chunk-level duplicate documents because dedup only runs on the fused hybrid path. Beyond those, the pipeline has several correctness/robustness gaps: dedup-after-limit under-fills results, chunk duplicates double-count in RRF, `--intent` pollutes the literal search query, unescaped CSV/XML output, and misleading benchmark surface (`--candidate-limit` is a dead flag; per-query fixture `collections` silently ignored). Findings were verified against current code (post phases 05/08); no historical attribution is implied.

## Critical Issues

### CR-01: `--line-numbers` with `--csv`/`--md`/`--xml` crashes with AttributeError

**File:** `src/sif/cli/commands/search.py:176-199` and `src/sif/cli/commands/search.py:522-545`
**Issue:** When `--line-numbers` is passed, the code converts results to plain dicts via `add_line_numbers_to_results([r.to_dict() for r in results])`, then feeds them to `format_results_csv` / `format_results_md` / `format_results_xml`. All three formatters access attributes (`r.rank`, `r.score`, `r.title`, `r.path`, `r.collection_name`), which raises `AttributeError: 'dict' object has no attribute 'rank'`. Reproduced:

```
$ python -c "from sif.cli.commands.search import format_results_csv; ..."
csv CRASH: AttributeError 'dict' object has no attribute 'rank'
md  CRASH: AttributeError 'dict' object has no attribute 'rank'
xml CRASH: AttributeError 'dict' object has no attribute 'rank'
```

Affected invocations: `sif search search Q --csv --line-numbers` (also `--md`, `--xml`) and `sif search query Q --csv|--md|--xml --line-numbers`. Only `--json` and the rich-table paths work with `--line-numbers`; there is no test covering the `--csv|--md|--xml` + `--line-numbers` combination (tests/unit/cli/test_search.py covers table and JSON only).
**Fix:** Either make the formatters accept both shapes, or stop pre-converting to dicts and let each formatter handle line numbers:

```python
def format_results_csv(results: list) -> str:
    import csv, io
    out = io.StringIO()
    writer = csv.writer(out, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(["rank", "score", "title", "path", "collection", "line_numbers"])
    for r in results:
        if isinstance(r, dict):
            writer.writerow([r.get("rank"), r.get("score"), r.get("title"),
                             r.get("path"), r.get("collection_name"), r.get("line_numbers", "")])
        else:
            writer.writerow([r.rank, f"{r.score:.4f}", r.title, r.path, r.collection_name, ""])
    return out.getvalue()
```

(Or simpler: pass `results` unchanged to the formatters and compute line numbers inside them from `r.content`.) Add CLI tests for every format-flag combination.

### CR-02: `except sqlite3.OperationalError` references an unimported name — handler raises NameError

**File:** `src/sif/cli/main.py:166`
**Issue:** The `cleanup` command's fallback handler is:

```python
except sqlite3.OperationalError:  # noqa: F821
    embeddings_removed = 0
```

`sqlite3` is never imported in `src/sif/cli/main.py` (the `# noqa: F821` suppresses the linter rather than fixing the bug). When the `DELETE FROM document_embeddings` statement raises `OperationalError` (the exact scenario this handler exists for — e.g., a sqlite-vec build that rejects DELETE with a non-key WHERE clause), evaluating `sqlite3.OperationalError` itself raises `NameError`. The outer `except Exception` then converts it into a misleading `ClickException: name 'sqlite3' is not defined` and rolls back the entire cleanup transaction, so orphaned-chunk removal is lost too. The graceful-degradation path can never execute.
**Fix:**

```python
import sqlite3  # at module top of src/sif/cli/main.py
...
except sqlite3.OperationalError:
    embeddings_removed = 0
```

(And remove the `# noqa: F821`.)

### CR-03: Vector-only search routes return chunk-level duplicate documents

**File:** `src/sif/search/hybrid.py:69-70` and `src/sif/search/hybrid.py:211-221`
**Issue:** `document_embeddings` stores one row per chunk (`chunk_id` column), and `VectorSearcher._search_with_vec` emits one `SearchResult` per matching embedding row with no document-level dedup. The class's own `_deduplicate_results` docstring (hybrid.py:95-98) acknowledges this: "Vector search operates at chunk level, so the same document may appear multiple times." However, dedup is only applied on the BM25+vector fused path:

- `HybridSearcher.search`: `if not bm25_results: return self._attach_contexts(vector_results)` — vector-only fallback returns the same document N times (once per chunk), each with its own rank.
- `SearchPipeline.search` `vec:` route (lines 211-215) and `hyde:` route (lines 216-221) return raw `vector.search(...)` output — same duplication.

A document with 5 embedded chunks can occupy 5 of the 10 requested slots, and `results[0]`/`results[1]` may be the same document with different chunk scores. The CLI's `vsearch` command (search.py:322-323) is equally affected since it calls `VectorSearcher.search` directly.
**Fix:** Deduplicate at the vector search boundary so every consumer gets document-level results:

```python
# VectorSearcher._search_with_vec, after the fetch loop (before trimming):
seen: set[str] = set()
unique: list[SearchResult] = []
for result in results:          # results are ordered by distance (best first)
    if result.document_id not in seen:
        seen.add(result.document_id)
        unique.append(result)
results = unique[: max(1, options.limit)]
```

(Over-fetch via `fetch_k` already provides headroom for the collapse.)

## Warnings

### WR-01: Hybrid dedup runs after limit truncation — returns fewer results than requested

**File:** `src/sif/search/hybrid.py:73` and `src/sif/search/hybrid.py:87-90`
**Issue:** `self.rrf.fuse([bm25_results, vector_results], options.limit)` truncates to `limit` first; `_deduplicate_results` then drops chunk-level duplicates from the already-truncated list. A `limit=10` request where the top-10 fused entries contain 4 chunk duplicates returns only 6 documents, even though more matching documents exist in the un-fused pool.
**Fix:** Deduplicate before applying the limit — either pass a larger limit to `fuse` and dedup+trim after, or run `_deduplicate_results` on the full fused list and slice to `options.limit` afterwards. (Combined with CR-03's fix at the VectorSearcher boundary, this becomes moot; keep one dedup point.)

### WR-02: Chunk-level duplicates double-count RRF contributions

**File:** `src/sif/search/rrf.py:37-63`
**Issue:** `fuse` keys contributions by `document_id`, so if the *same list* contains the same document twice (which the vector list does — see CR-03), each occurrence adds `1/(k+rank)` to that document's fused score. Documents with many embedded chunks get systematically inflated RRF scores and outrank documents that match equally well but have fewer chunks. `fuse_with_weights` (lines 119-147) has the identical flaw.
**Fix:** Collapse each input list to unique documents before scoring (keep the best-ranked occurrence):

```python
for list_idx, results in enumerate(results_lists):
    seen: set[str] = set()
    for rank, result in enumerate(results, 1):
        if result.document_id in seen:
            continue
        seen.add(result.document_id)
        ...
```

### WR-03: `--intent` is prepended as literal query text and becomes a hard search term

**File:** `src/sif/search/hybrid.py:204-206`
**Issue:** `parsed_query = f"{options.intent}: {parsed_query}"` rewrites the actual search string. Downstream: (a) on the `lex:` route, `BM25Searcher._build_fts_query("code: test")` produces `"code"* AND "test"*` — the intent word becomes a mandatory AND term, silently excluding documents that don't contain the literal word "code"; (b) on `vec:`/hybrid routes the string `"code: test"` is embedded, skewing the query vector; (c) `QueryExpansion.expand(parsed_query)` receives the polluted string even though it has a dedicated `intent` parameter that is never used by the pipeline. The CLI documents the flag as "Search intent hint for query expansion" — the implementation makes it a filter instead. `tests/unit/search/test_hybrid.py:413-427` asserts the current (polluting) behavior, so the test encodes the bug.
**Fix:** Do not mutate the query string. Pass intent through to the expander and keep the searched query clean:

```python
expanded = self.query_expander.expand(parsed_query, intent=options.intent)
```

and update `test_intent_prepended_to_query` to assert the searcher receives the unpolluted query while variants carry the intent prefix.

### WR-04: CSV and XML output are not escaped

**File:** `src/sif/cli/commands/search.py:36-42` and `src/sif/cli/commands/search.py:64-78`
**Issue:** `format_results_csv` wraps fields in double quotes but never escapes embedded quotes (reproduced: a title `He said "hello"` yields the malformed field `"He said "hello""`). `format_results_xml` interpolates `r.title`, `r.path`, `r.collection_name` and the `query` attribute with no XML escaping, so titles containing `&`, `<`, or `"` produce malformed/unparseable XML. Titles come from indexed filenames/frontmatter, so this is ordinary input, not an edge case. Note `src/sif/cli/formatters.py` already has a correct `format_csv` (csv module) and `format_xml` that these local copies bypass.
**Fix:**

```python
import csv, io
from xml.sax.saxutils import escape, quoteattr

def format_results_csv(results: list) -> str:
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["rank", "score", "title", "path", "collection"])
    w.writerows([r.rank, f"{r.score:.4f}", r.title, r.path, r.collection_name] for r in results)
    return out.getvalue()

# XML: escape(r.title), escape(r.path), quoteattr(query), etc.
```

### WR-05: Pipeline/vector RuntimeErrors surface as raw tracebacks from the CLI

**File:** `src/sif/cli/commands/search.py:496-505` (and `src/sif/cli/commands/search.py:321-323`, `484-491`)
**Issue:** `SearchPipeline.search` intentionally fails fast — it raises `RuntimeError` for missing embedder (hybrid.py:213, 219), reranker failure (hybrid.py:265), and HyDE without generation support (hybrid.py:298-329); `VectorSearcher.__init__` raises `RuntimeError` when sqlite-vec is missing (vector.py:21-23). None of these are caught in `query_cmd`/`vsearch_cmd`/`bench_cmd`, so users get a full Python traceback. Likewise `create_reranker` raises `ValueError` for an unknown `reranker_model_type`, but `query_cmd` only catches `ImportError` (search.py:484-491). This violates the project convention "CLI commands raise `click.ClickException(str(e))` for user-facing errors."
**Fix:** Wrap the search execution:

```python
try:
    results = pipeline.search(query, options)
except RuntimeError as e:
    raise click.ClickException(str(e)) from e
```

and add `except ValueError` alongside the existing `except ImportError` around `create_reranker`.

### WR-06: SmartSnippetExtractor violates max_length when the best sentence alone exceeds it

**File:** `src/sif/search/snippets.py:79-120`
**Issue:** `_build_window` starts with `window = [sentences[center_idx]]` and never truncates the center sentence. If the highest-scoring sentence is longer than `max_length`, the returned snippet is that entire sentence (reproduced: `max_length=50` returned a 307-char snippet). Real markdown chunks frequently contain very long "sentences" (code blocks, lists without terminal punctuation), so the CLI's `snippet_max_length=300` (SearchOptions default) is routinely exceeded.
**Fix:** Truncate as a final step in `extract`:

```python
snippet = self._build_window(sentences, best_idx, query_terms)
return self._truncate(snippet)  # also handles the center-sentence overflow
```

(`_truncate` currently returns `text` unchanged when `len(text) <= max_length`, so this is safe for short windows.)

### WR-07: `bench --candidate-limit` is a dead flag

**File:** `src/sif/cli/commands/bench.py:28` and `src/sif/cli/commands/bench.py:116-122`
**Issue:** `bench_cmd` advertises `-C/--candidate-limit` ("Reranker candidate pool size") and threads it into `SearchOptions`, but the `SearchPipeline` it builds is constructed without a `reranker`, so `candidate_limit` is never read anywhere in the benchmark path. Users tuning it see zero effect on metrics, which silently invalidates A/B comparisons made with different `-C` values.
**Fix:** Either construct the pipeline with a reranker (mirroring `query_cmd`'s load-or-warn logic) or remove the flag from `bench_cmd` until reranking is benchmarked.

### WR-08: Per-query `collections` field in bench fixtures is silently ignored

**File:** `src/sif/cli/commands/bench.py:50-58` and `src/sif/search/benchmark.py:50-51, 83-100`
**Issue:** The `bench` help text and `SearchEvaluator` docstring document a per-query `"collections": [...]` fixture field, but `evaluate()` never reads it — queries run against the CLI-level collection selection only. A fixture author who scopes relevance judgments per collection gets metrics computed over a different (larger) result set, with no warning. `SearchOptions` supports `collection_ids`, so the plumbing exists.
**Fix:** In `SearchEvaluator.evaluate`, honor the field:

```python
colls = query_item.get("collections")
if colls:
    options.collection_ids = resolved_ids  # requires passing a resolver or raw names
```

or, minimally, raise/warn in `_validate_fixture` when an unsupported `collections` key is present, and delete it from the documented format.

### WR-09: RRF `fuse` mislabels and drops scores when fusing more than two lists

**File:** `src/sif/search/rrf.py:50-52` and `src/sif/search/rrf.py:134-136`
**Issue:** `score_key = "bm25_score" if list_idx == 0 else "vector_score"` hard-codes two-list semantics. `SearchPipeline.search` calls `self.hybrid.rrf.fuse(all_results, options.limit)` with one list per *query variant* (hybrid.py:245-256) — for lists 1..N, every result's score is recorded under `"vector_score"` regardless of provenance (list 0's gets recorded as `"bm25_score"` even though it is an inner RRF score), and because of the `if score_key not in doc_scores` guard, later lists' contributions are dropped from `scores` entirely. The `--explain` output (`query_cmd`, search.py:577-581) then displays wrong provenance for any expanded query.
**Fix:** Make the key derivation data-driven, e.g. accept an optional `list_names: list[str]` parameter (default `["bm25_score", "vector_score"]`) and use `list_names[list_idx] if list_idx < len(list_names) else f"list_{list_idx}_score"`, or have the pipeline fuse on a dedicated key (`query_variant_score`) instead of reusing the two-list fusion.

### WR-10: `fuse_with_weights` divides by zero when weights sum to 0; docstring contradicts code

**File:** `src/sif/search/rrf.py:103-114`
**Issue:** `total_weight = sum(weights); normalized_weights = [w / total_weight for w in weights]` raises an uncaught `ZeroDivisionError` for `weights=[0.0, 0.0]`. The docstring says weights "must sum to 1.0" but the code normalizes anyway (contradictory contract), and negative weights are accepted, which would invert rankings. The existing tests only cover a partial zero (`[1.0, 0.0]`, test_rrf.py:395-428).
**Fix:**

```python
total_weight = sum(weights)
if total_weight <= 0:
    raise ValueError("weights must sum to a positive value")
if any(w < 0 for w in weights):
    raise ValueError("weights must be non-negative")
```

### WR-11: CrossEncoderReranker.load swallows all download errors and guesses a subdirectory

**File:** `src/sif/search/rerank.py:158-172`
**Issue:** The ModelScope download block is wrapped in `except Exception:` with only an info-level log, then execution proceeds with `local_path = model_id` — so a network failure, disk error, or downloader bug silently degrades into a HuggingFace load attempt (which will fail confusingly later, or load a different artifact). Additionally `subdirs[0]` selects an arbitrary subdirectory of the snapshot with no validation that it contains a model. Compare `Qwen3Reranker.load` (lines 254-260), which lets download failures propagate.
**Fix:** Narrow the exception to what is actually recoverable (e.g., `except ImportError:` for a missing modelscope dependency) and let genuine download errors propagate; log at `warning`/`error` level. Validate the chosen subdir (contains `config.json`) before using it.

### WR-12: Test-mock accommodation baked into production `_attach_contexts`

**File:** `src/sif/search/hybrid.py:124-141`
**Issue:** The row-parsing loop contains a comment "Fallback: assume tuple-like access (skip MagicMock rows in tests)" and three exception-swallowing branches (`except (KeyError, TypeError): pass`, `except (KeyError, IndexError, TypeError): continue`). Production row handling now silently skips any row that does not parse, and the shape of the function is dictated by test doubles rather than the real `sqlite3.Row` contract used by the sibling implementations in `bm25.py:108-125` and `vector.py:116-133`. If the row factory ever changes, rows are dropped with no signal.
**Fix:** Delete the defensive branches and use the same dict-row access as bm25/vector; fix the tests that feed non-`sqlite3.Row`-like mocks (e.g., via `sqlite3.Row` fixture rows or by mocking at the searcher boundary).

## Info

### IN-01: Substantial copy-paste duplication across the phase's modules

**File:** `src/sif/search/rrf.py:20-175`; `src/sif/search/rerank.py:264-295`; `src/sif/search/hybrid.py`/`bm25.py`/`vector.py` (`_attach_contexts` x3); `src/sif/cli/commands/search.py` (three near-identical output blocks); `src/sif/cli/commands/bench.py:102-114` vs `search.py:446-458`
**Issue:** (a) `fuse` and `fuse_with_weights` share ~65 identical lines (WR-02's fix would otherwise need to be applied twice); (b) `Qwen3Reranker.load` duplicates the entire ~15-line model-loading body in quiet/non-quiet branches; (c) `_attach_contexts` exists in three copies; (d) `search_cmd`/`vsearch_cmd`/`query_cmd` each repeat the collection-resolution and table/format output blocks; (e) bench re-implements the collection filter from query_cmd.
**Fix:** Extract a shared `_fuse(results_lists, limit, weight_fn)` core, a `_load_model()` helper for Qwen3, a shared context-attachment utility (e.g., in `sif/utils` or a searcher base class), and shared CLI helpers for collection resolution and result rendering.

### IN-02: Dead code across the reviewed files

**File:** `src/sif/search/rrf.py:178-188`; `src/sif/cli/main.py:22`; `src/sif/search/expansion.py:62-63`; `src/sif/search/hybrid.py:259`; `src/sif/cli/commands/search.py:163, 508`
**Issue:** `compute_rrf_score` is defined but never called anywhere in `src/` or `tests/`; `DEFAULT_INDEX_PATH` in main.py is defined but unused (the `--index` default comes from `get_settings().get_db_path()` — and the two disagree on location, `~/.local/share/sif/sif.db` vs `user_data_dir`); `if not variants: return [query]` in `expand()` is unreachable because `variants` always contains the original query; `len(results) > 0` is redundant when `results` is truthy-checked by usage; `quiet = quiet or ctx.obj.get("quiet", False)` is computed twice in both `search_cmd` and `query_cmd` with no intervening mutation.
**Fix:** Delete the dead function/constant/branches, or wire `DEFAULT_INDEX_PATH` to the settings-derived path.

### IN-03: Private attribute access `manager._model` at CLI boundary

**File:** `src/sif/cli/commands/search.py:499`; `src/sif/cli/commands/bench.py:119`
**Issue:** Both commands pass `embedder=manager._model` (with `# noqa: SLF001`) because `EmbeddingManager` exposes no public accessor for the loaded model. If the manager is unloaded or the model load is skipped, this silently passes `None` downstream.
**Fix:** Add a public property (`@property def model(self) -> Embedder | None`) or a `get_embedder()` method on `EmbeddingManager` and use it from the CLIs.

### IN-04: `LlamaCppReranker._batch_size` is accepted and stored but never used

**File:** `src/sif/search/rerank.py:67` and `src/sif/search/rerank.py:89-126`
**Issue:** `rerank()` embeds documents one at a time in a Python loop; the `batch_size` parameter (also passed from settings via `create_reranker`) has no effect. Compare `Qwen3Reranker`, which batches.
**Fix:** Either batch the calls (if the backend supports it) or remove the parameter to stop implying behavior that doesn't exist.

### IN-05: `Qwen3Reranker` token ids can be `None` and are indexed unchecked

**File:** `src/sif/search/rerank.py:239-240` and `src/sif/search/rerank.py:349-350`
**Issue:** `_token_true_id`/`_token_false_id` are typed `int | None` (a tokenizer that cannot map "yes"/"no" returns `None`), but `logits[:, self._token_true_id]` uses them directly. With `None`, torch treats the index as `newaxis` and silently returns a differently-shaped tensor, producing garbage scores instead of an error.
**Fix:** After `convert_tokens_to_ids`, assert/raise if either id is `None` ("tokenizer does not contain the required 'yes'/'no' tokens").

### IN-06: `reranker_model_type` lacks the validation applied to `model_type`

**File:** `src/sif/config/settings.py:90-93` vs `src/sif/config/settings.py:150-164`
**Issue:** `model_type` has a field validator restricting it to supported backends (with a documented rationale), but `reranker_model_type` — consumed by `create_reranker`, which raises `ValueError` for anything except `gguf`/`sentence_transformers` — has no validator, so typos fail at query time instead of configuration load time.
**Fix:** Add an analogous `@field_validator("reranker_model_type")` allowing `{"gguf", "sentence_transformers"}`.

### IN-07: Hardcoded `embedding_dim = 384` fallback in bench

**File:** `src/sif/cli/commands/bench.py:81`
**Issue:** When embedding load fails, `embedding_dim` stays at the magic default 384, which matches neither `Settings.embedding_dim` (default 1024) nor any model actually configured. It is only used to construct `VectorSearcher` when `manager` is `None`, so today it is harmless, but it will mislead anyone who later makes dimension matter on that path.
**Fix:** Use `settings.embedding_dim` as the fallback, or drop the variable and pass `0`/omit when no embedder is available.

### IN-08: Unprotected sigmoid can overflow

**File:** `src/sif/search/rerank.py:124` and `src/sif/search/rerank.py:208`
**Issue:** `1.0 / (1.0 + math.exp(-s))` raises `OverflowError` once `s < ~-709`. Cosine-similarity inputs (LlamaCpp path) are bounded in `[-1, 1]`, but `CrossEncoder.predict` returns raw logits that are only conventionally bounded; a pathological pair would crash reranking (which the pipeline then converts to `RuntimeError`).
**Fix:** Clamp the exponent: `math.exp(-max(-60.0, min(60.0, s)))`, or use a numerically stable formulation.

### IN-09: Fixture file opened without explicit encoding

**File:** `src/sif/cli/commands/bench.py:68`
**Issue:** `with open(fixture) as f: json.load(f)` relies on the locale default encoding (UTF-8 on macOS/Linux, but cp1252 on many Windows setups). Benchmarks fixtures with non-ASCII content in `query`/`relevant_docids` would fail to load on those platforms.
**Fix:** `with open(fixture, encoding="utf-8") as f:`

---

_Reviewed: 2026-09-05_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
