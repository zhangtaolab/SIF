---
phase: 04-advanced-search-pipeline
reviewed: 2026-09-05T01:16:21Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - src/sif/search/hybrid.py
  - src/sif/cli/commands/search.py
  - src/sif/search/expansion.py
  - src/sif/search/snippets.py
  - tests/unit/search/test_hybrid.py
  - tests/unit/cli/test_search.py
  - tests/unit/search/test_snippets.py
  - tests/unit/inference/test_query_expander.py
  - tests/integration/test_search_pipeline.py
findings:
  critical: 2
  warning: 12
  info: 6
  total: 20
status: issues_found
---

# Phase 04: Code Review Report (Re-review after plan 04-06)

**Reviewed:** 2026-09-05T01:16:21Z
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Re-review of Phase 04 (Advanced Search Pipeline) after gap-closure plan 04-06 (commits 2b26138..5a0954d), which added the transient snippet content feed (`SearchPipeline._apply_snippets`), snippet application on the `lex:`/`vec:`/`hyde:` early-return routes, the `_display_snippet` helper, and the Snippet column in the `query_cmd`/`search_cmd` rich tables.

**The 04-06 gap closure itself is sound.** The transient-fetch contract holds: `_apply_snippets` (hybrid.py:275-297) feeds fetched document text to the extractor and never writes `SearchResult.content` — verified in code and pinned by tests (`test_lex/vec/hyde_route_applies_snippets` assert `content is None`; integration tests cover both `include_content` polarities). Prefix routes now receive snippets, the fallback to `highlights[0]` works, and `rich.markup.escape` is applied to the new column. No defect found in the core gap-closure mechanism.

However, the two prior Critical findings are **still present and re-verified by reproduction**, and the re-review surfaced four new Warnings: (1) the new `escape()` call is applied only to the Snippet cell while title/collection/content cells and table titles remain unescaped — a note containing a stray `[/tag]` sequence crashes the whole table render with `MarkupError` (reproduced); (2) four tests in `tests/unit/cli/test_search.py` fail whenever `FORCE_COLOR` is set in the ambient environment (reproduced: 4 failed with `FORCE_COLOR=3`, 18/18 pass without); (3) the shared `mock_embedding_manager` conftest fixture returns a plain list from `embed()` instead of an `EmbeddingResponse`, so the embedding-similarity path in `_get_expansion_terms` is silently swallowed by the broad `except Exception` and never actually tested (reproduced); (4) the prior WR-01/WR-01-mechanism is corrected: `rrf.fuse` output is already unique per `document_id` (verified), so `_deduplicate_results` on the fused path is dead code and the within-list duplicate handling in `fuse` overwrites score provenance (verified: the lower-scoring duplicate chunk's raw score wins).

Prior findings CR-01, CR-03, WR-03, WR-04, WR-05, WR-06, WR-07, WR-08, WR-09, WR-12 re-verified against current state and re-reported below with original IDs.

## Critical Issues

### CR-01 [BLOCKER]: `--line-numbers` with `--csv`/`--md`/`--xml` crashes with AttributeError (re-verified)

**File:** `src/sif/cli/commands/search.py:192-217` (search_cmd), `src/sif/cli/commands/search.py:539-563` (query_cmd), formatters at `src/sif/cli/commands/search.py:53-59, 62-78, 81-95`
**Issue:** When `--line-numbers` is passed, results are converted to plain dicts via `add_line_numbers_to_results([r.to_dict() for r in results])` and fed to `format_results_csv` / `format_results_md` / `format_results_xml`, all of which access attributes (`r.rank`, `r.score`, `r.title`, ...). Reproduced in this re-review:

```
csv CRASH: AttributeError 'dict' object has no attribute 'rank'
md  CRASH: AttributeError 'dict' object has no attribute 'rank'
xml CRASH: AttributeError 'dict' object has no attribute 'rank'
```

Affected invocations: `sif search search Q --csv --line-numbers` (also `--md`, `--xml`) and `sif search query Q --csv|--md|--xml --line-numbers`. Only `--json` and the rich-table paths work with `--line-numbers`; no test covers the broken combinations (`tests/unit/cli/test_search.py` covers table and JSON only).
**Fix:** Pass `results` (objects) to the formatters unchanged and compute line numbers inside each formatter from `r.content`, or make each formatter accept both shapes:

```python
def _row(r) -> tuple:
    if isinstance(r, dict):
        return (r.get("rank"), f'{float(r.get("score", 0)):.4f}', r.get("title"),
                r.get("path"), r.get("collection_name"), r.get("line_numbers", ""))
    return (r.rank, f"{r.score:.4f}", r.title, r.path, r.collection_name, "")
```

Add CLI tests for every `--line-numbers` x format-flag combination.

### CR-03 [BLOCKER]: Vector-only search routes return chunk-level duplicate documents (re-verified)

**File:** `src/sif/search/hybrid.py:67-70`, `src/sif/search/hybrid.py:212-224` (vec:/hyde: routes), `src/sif/cli/commands/search.py:340-342` (vsearch_cmd)
**Issue:** `document_embeddings` stores one row per chunk; `VectorSearcher._search_with_vec` emits one `SearchResult` per matching row with no document-level dedup. The routes that bypass RRF fusion return the raw duplicates:

- `HybridSearcher.search`: `if not bm25_results: return self._attach_contexts(vector_results)` — vector-only fallback returns the same document N times.
- `SearchPipeline.search` `vec:` (lines 212-217) and `hyde:` (lines 218-224) routes return `self.hybrid.vector.search(...)` output directly.
- `vsearch_cmd` calls `VectorSearcher.search` directly.

A document with 5 embedded chunks can occupy 5 of the 10 requested slots; `results[0]` and `results[1]` may be the same document.

**New evidence from this re-review:** `_deduplicate_results` (hybrid.py:92-110) — the class's own dedup whose docstring claims to handle exactly this — is only called at hybrid.py:88 on the output of `self.rrf.fuse(...)`, and `fuse` keys its accumulator by `document_id`, so its output is already unique per document (verified: a list with `d1, d1, d2` fuses to `[d1, d2]`). The dedup is a no-op on its only call site; the paths that actually observe chunk duplicates never call it. See also WR-01 for the in-list score inflation this causes on the fused path.
**Fix:** Deduplicate at the vector search boundary so every consumer gets document-level results:

```python
# VectorSearcher._search_with_vec, after the fetch loop (before trimming):
seen: set[str] = set()
unique: list[SearchResult] = []
for result in results:          # ordered by distance (best first)
    if result.document_id not in seen:
        seen.add(result.document_id)
        unique.append(result)
results = unique[: max(1, options.limit)]
```

(The `fetch_k` over-fetch already provides headroom for the collapse.)

## Warnings

### WR-01: Dead `_deduplicate_results` + RRF duplicate merge overwrites score provenance (corrects prior WR-01/WR-02)

**File:** `src/sif/search/hybrid.py:87-110`, `src/sif/search/rrf.py:37-63`
**Issue:** The prior review's WR-01 claimed dedup-after-limit under-fills hybrid results; that mechanism is wrong — `rrf.fuse` collapses duplicate `document_id`s within its accumulator, so the fused list is unique and `_deduplicate_results(fused_results)` is dead code (verified). The real duplicate-related defects on this path are:

1. **Score inflation (prior WR-02):** when the *same list* contains the same document twice (the vector list does — see CR-03), each occurrence adds `1/(k+rank)`, so multi-chunk documents get systematically inflated fused scores (verified: `d1` at ranks 1 and 2 in one list fuses to `1/61 + 1/62`).
2. **Provenance overwrite (new):** on merge, `merged_scores.update(doc_scores)` lets the later duplicate's raw score overwrite the first occurrence's — verified: two `d1` entries with scores 0.9 then 0.8 produce `scores['bm25_score'] == 0.8`. `--explain` then shows the wrong underlying score.

`fuse_with_weights` (rrf.py:119-147) has the identical merge logic.
**Fix:** With CR-03's boundary dedup in place, in-list duplicates disappear and both effects become moot; alternatively collapse each input list to unique documents (best-ranked occurrence) at the top of `fuse`/`fuse_with_weights`, and delete or repurpose the dead `_deduplicate_results`.

### WR-03: `--intent` is prepended as literal query text and pollutes search, expansion, and now snippet terms (re-report)

**File:** `src/sif/search/hybrid.py:204-206`; new interaction at `src/sif/search/hybrid.py:288`
**Issue:** `parsed_query = f"{options.intent}: {parsed_query}"` rewrites the actual search string. Downstream: (a) on the `lex:` route, `BM25Searcher._build_fts_query("code: test")` turns the intent word into a mandatory AND term, silently excluding documents that don't contain the literal word; (b) on `vec:`/hyde: routes the polluted string is embedded; (c) `QueryExpansion.expand(parsed_query)` receives the polluted string even though it has a dedicated `intent` parameter the pipeline never passes; and — **new in 04-06** — (d) `_apply_snippets` derives its scoring terms from the same polluted string (`parsed_query.lower().split()` yields `"code:"` as a term), so the intent token now also participates in snippet selection. `tests/unit/search/test_hybrid.py:414-428` asserts the polluting behavior.
**Fix:** Do not mutate the query string. Keep the searched query clean and pass intent through:

```python
expanded = self.query_expander.expand(parsed_query, intent=options.intent)
```

and update `test_intent_prepended_to_query` to assert the searcher receives the unpolluted query while expansion variants carry the intent prefix.

### WR-04: CSV and XML output are not escaped (re-report)

**File:** `src/sif/cli/commands/search.py:53-59` (CSV), `src/sif/cli/commands/search.py:81-95` (XML)
**Issue:** `format_results_csv` wraps fields in double quotes but never escapes embedded quotes (a title `He said "hello"` yields the malformed field `"He said "hello""`). `format_results_xml` interpolates `r.title`, `r.path`, `r.collection_name`, and the `query` attribute with no XML escaping, so titles containing `&`, `<`, or `"` produce malformed, unparseable XML. Titles come from indexed filenames/frontmatter — ordinary input, not an edge case. `src/sif/cli/formatters.py` already contains a correct `format_csv` (csv module) and `format_xml` that these local copies bypass.
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
# XML: escape(r.title), escape(r.path), quoteattr(query), ...
```

### WR-05: Pipeline/RuntimeErrors surface as raw tracebacks from the CLI (re-report)

**File:** `src/sif/cli/commands/search.py:514-524` (unwrapped `pipeline.search`), `src/sif/cli/commands/search.py:501-510` (`create_reranker` catches only `ImportError`), `src/sif/cli/commands/search.py:340-342` (vsearch `VectorSearcher(...)` unwrapped)
**Issue:** `SearchPipeline.search` intentionally fails fast — `RuntimeError` for reranker failure (hybrid.py:267-268) and HyDE without text generation (hybrid.py:348-352) — and `VectorSearcher.__init__` raises `RuntimeError` when sqlite-vec is missing. None are caught in `query_cmd`/`vsearch_cmd`, so e.g. `sif search query "hyde: foo"` with the default `modelscope` embedder (no `.generate()`/`.create_completion()`) ends in a full Python traceback. `create_reranker` raises `ValueError` for an unknown `reranker_model_type`, but only `ImportError` is handled. Note also that `settings.reranker_model_name` defaults to `"Qwen/Qwen3-Reranker-0.6B"`, so the `if settings.reranker_model_name or ...` guard at search.py:502 is always true by default — a reranker is constructed (and lazily loaded on first rerank) for every `query` invocation, making the unhandled load-failure path realistic, not hypothetical. This violates the project convention "CLI commands raise `click.ClickException(str(e))` for user-facing errors."
**Fix:** Wrap the search execution and reranker creation:

```python
try:
    reranker = create_reranker(settings)
except ImportError:
    ...
except ValueError as e:
    raise click.ClickException(str(e)) from e
...
try:
    results = pipeline.search(query, options)
except RuntimeError as e:
    raise click.ClickException(str(e)) from e
```

### WR-06: SmartSnippetExtractor violates max_length when the best sentence alone exceeds it (re-report, re-verified)

**File:** `src/sif/search/snippets.py:79-120`
**Issue:** `_build_window` starts with `window = [sentences[center_idx]]` and never truncates the center sentence; `extract` returns its output directly (snippets.py:61) with no final truncation. Re-verified in this review: with `max_length=50` and a long best sentence, `extract` returned a 514-character snippet. Real markdown chunks routinely contain long "sentences" (code blocks, lists without terminal punctuation), so the 300-char default (`SearchOptions.snippet_max_length`) is regularly exceeded — and the excess now leaks into `--json` output via `SearchResult.to_dict()` (the table column truncates at 200 for display, masking it).
**Fix:**

```python
# in extract(), replace the final return:
return self._truncate(self._build_window(sentences, best_idx, query_terms))
```

(`_truncate` is a no-op when the window already fits.)

### WR-07: `bench --candidate-limit` is a dead flag (re-report; file outside current 9-file scope)

**File:** `src/sif/cli/commands/bench.py:28`
**Issue:** Re-verified via grep: `bench_cmd` still advertises `-C/--candidate-limit` and threads it into `SearchOptions`, but the `SearchPipeline` it builds has no reranker, so `candidate_limit` is never read on the benchmark path. A/B comparisons made with different `-C` values are silently identical. (bench.py is not in this review's file list; reported per re-review instructions.)
**Fix:** Construct the bench pipeline with a reranker (mirroring `query_cmd`'s load-or-warn logic) or remove the flag.

### WR-08: Per-query `collections` field in bench fixtures is silently ignored (re-report; file outside current 9-file scope)

**File:** `src/sif/cli/commands/bench.py:56` (documented fixture format), consumer `src/sif/search/benchmark.py`
**Issue:** Re-verified via grep: the fixture format still documents `"collections": ["optional-collection-filter"]` per query, but `SearchEvaluator.evaluate` never reads it — queries run against the CLI-level collection selection only. Relevance judgments scoped per collection are computed over a different result set, with no warning.
**Fix:** Honor the field in `evaluate()` via `SearchOptions.collection_ids`, or warn/reject in fixture validation and delete it from the documented format.

### WR-09: RRF `fuse` mislabels and drops score provenance when fusing more than two lists (re-report, aggravated)

**File:** `src/sif/search/hybrid.py:247-259` (fuse call with one list per expansion variant), `src/sif/cli/commands/search.py:598-602` (`--explain` rendering); root cause `src/sif/search/rrf.py:50-52, 134-136`
**Issue:** `score_key = "bm25_score" if list_idx == 0 else "vector_score"` hard-codes two-list semantics. `SearchPipeline.search` fuses one list per *query variant*, so lists 1..N are all recorded as `"vector_score"` regardless of provenance, and the `if score_key not in doc_scores` guard drops later lists' contributions from `scores` entirely. `--explain` then displays wrong provenance for any expanded query. **Aggravation observed in this re-review:** on the `lex:`/`vec:`/`hyde:` early-return routes, `SearchResult.scores` is `{}` (BM25Searcher/VectorSearcher never populate it), so `sif search query "lex: foo" --explain` prints nothing at all — the flag silently does nothing for prefix routes.
**Fix:** Make key derivation data-driven (optional `list_names` parameter defaulting to `["bm25_score", "vector_score"]`, with `f"list_{i}_score"` fallback), and have the searchers populate at least a base score key so `--explain` works on every route.

### WR-12: Test-mock accommodation baked into production `_attach_contexts` (re-report)

**File:** `src/sif/search/hybrid.py:124-141`
**Issue:** The row-parsing loop still contains the "skip MagicMock rows in tests" fallback with three exception-swallowing branches. Production row handling silently skips any row that does not parse, and the function's shape is dictated by test doubles rather than the real `sqlite3.Row` contract used by the sibling implementations in bm25.py:108-125 and vector.py:116-133.
**Fix:** Delete the defensive branches and use dict-row access identical to bm25/vector; fix the tests that feed non-`sqlite3.Row`-like mocks.

### WR-13: Rich markup applied inconsistently — unescaped title/collection/content cells and table titles can silently drop text or crash rendering (new)

**File:** `src/sif/cli/commands/search.py:240, 587` (only the Snippet cell is escaped); unescaped: `225, 572` (table titles embed the raw query), `238, 585` (title cells), `239, 586` (collection cells), `242-246, 589-593` (raw content with line numbers), `602` (`--explain` `[dim]{r.title}...[/dim]`); `vsearch_cmd` table at `362-383` is fully unescaped
**Issue:** 04-06 added `escape(_display_snippet(r))` for the new Snippet column but left every other interpolation of user-controlled text (document titles, collection names, and — with `--line-numbers` — full note content) unescaped, plus the table titles `f'Search Results: "{query}"'` that embed the raw query. Verified behavior with rich:

- `table.add_row('Note [draft] version', ...)` renders as `Note version` — the bracketed text is **silently dropped** (markup-tag interpretation).
- content containing a stray closing tag (e.g. a note documenting `[/red]` syntax) raises `MarkupError: closing tag '[/red]' ... doesn't match any open tag` — the **entire table render crashes**.

Since indexed notes are arbitrary user files, both outcomes are reachable from ordinary content, and the new code's selective escaping makes the omission look deliberate rather than overlooked.
**Fix:** Escape every user-controlled interpolation at the render boundary:

```python
table = Table(title=f'Hybrid Search Results: "{escape(query)}"')
...
r_title = r.title[:_TITLE_MAX_LEN] + "..." if len(r.title) > _TITLE_MAX_LEN else r.title
row = [str(r.rank), f"{r.score:.4f}", escape(r_title), escape(r.collection_name),
       escape(_display_snippet(r))]
...
row.append(escape(prepend_line_numbers(r.content)))
...
console.print(f"[dim]{escape(r.title)}: {scores_str}[/dim]")
```

### WR-14: CLI tests fail when `FORCE_COLOR` is set in the environment (new, test reliability)

**File:** `src/sif/cli/commands/search.py:21` (`console = Console()`); failing assertions in `tests/unit/cli/test_search.py:256-286` (`test_search_line_numbers_json`), `:338-383` (`test_vsearch_line_numbers_flag`), `:408-452` (`test_query_with_explain`), `:794-805` (`test_query_files_output_has_no_table_headers`)
**Issue:** Reproduced in this review: running `pytest tests/unit/cli/test_search.py` with the ambient `FORCE_COLOR=3` set (as it is in this machine's shell) fails 4 tests — the module-level `Console()` honors `FORCE_COLOR`, so `result.output` contains ANSI escapes and line-wrapped highlighted paths, breaking substring assertions like `'"line_numbers": "1\\n2"' in result.output` and `'/notes/decorators.md' in result.output`. The same run passes 18/18 with `FORCE_COLOR` unset. The tests are therefore environment-dependent and will fail for any developer/CI that sets `FORCE_COLOR` (or, per rich's detection rules, other terminal-detection env vars).
**Fix:** Isolate rendering from ambient env in the commands under test (and/or strip ANSI in assertions):

```python
# tests/unit/cli/test_search.py
import re
_ANSI = re.compile(r"\x1b\[[0-9;]*m")

def _plain(output: str) -> str:
    return _ANSI.sub("", output)

assert '"line_numbers": "1\\n2"' in _plain(result.output)
```

or construct the CLI console with explicit `no_color`/`force_terminal=False` under test.

### WR-15: `mock_embedding_manager` violates the `EmbeddingManager.embed()` contract — expansion similarity path silently untested (new, test reliability + error masking)

**File:** `tests/conftest.py:481-495` (fixture); masked by `src/sif/search/expansion.py:131-133` (broad `except Exception`); vacuous assertions at `tests/unit/inference/test_query_expander.py:135-144, 213-222`
**Issue:** The fixture's `mock.embed.side_effect` returns a plain `list[list[float]]`, but real `EmbeddingManager.embed()` returns an `EmbeddingResponse` whose vectors live in `.embeddings`. `QueryExpansion._get_expansion_terms` does `candidate_embeddings = self._embedding_manager.embed(candidate_list)` then iterates `candidate_embeddings.embeddings` — with the fixture this raises `AttributeError: 'list' object has no attribute 'embeddings'`, which the method's broad `except Exception: logger.warning(...); return []` swallows. Verified: `_get_expansion_terms('python search')` with the fixture-shaped mock returns `[]` via the exception path. Consequently the entire similarity-scoring block (expansion.py:110-130 — candidate generation, cosine scoring, top-k selection) is never executed by any test, and `test_get_expansion_terms_with_embedding_manager` / `test_expand_with_embedding_manager` pass vacuously on `isinstance(terms, list)`. The same broad except in production would equally mask a real contract drift in any future embedder backend.
**Fix:** Make the fixture conform (return an object with `.embeddings`):

```python
class _FakeResponse:
    def __init__(self, vectors): self.embeddings = vectors

mock.embed.side_effect = lambda texts: _FakeResponse([[0.1] * 384 for _ in texts])
```

and narrow the production `except Exception` to expected failure types (or at least log at `warning` with the traceback) so contract mismatches surface.

## Info

### IN-02: Dead code and redundant branches in the scoped files (re-report, updated)

**File:** `src/sif/search/hybrid.py:262` (`len(results) > 0` redundant — `results` is truthy-checked by the same `if`); `src/sif/search/hybrid.py:220-221` (embedder-None check unreachable: `_generate_hypothetical_document` at line 219 already raises the same-messaged `RuntimeError`); `src/sif/search/expansion.py:62-63` (`if not variants: return [query]` unreachable — `variants` always contains the original); `src/sif/cli/commands/search.py:139+180` and `441+527` (`quiet = quiet or ctx.obj.get("quiet", False)` computed twice per command with no intervening mutation)
**Issue:** Dead/redundant branches accumulate and obscure the live logic.
**Fix:** Delete the redundant conditions; hoist the duplicate `quiet` computation to a single statement.

### IN-03: Private attribute access `manager._model` at the CLI boundary (re-report)

**File:** `src/sif/cli/commands/search.py:518`
**Issue:** `query_cmd` passes `embedder=manager._model` (with `# noqa: SLF001`) because `EmbeddingManager` exposes no public accessor for the loaded model.
**Fix:** Add a public property (`@property def model(self) -> Embedder | None`) or `get_embedder()` on `EmbeddingManager` and use it from the CLI.

### IN-10: `-C/--candidate-limit` has no effect on `lex:`/`vec:`/`hyde:` prefix routes (new)

**File:** `src/sif/cli/commands/search.py:395-401` (flag help), `src/sif/search/hybrid.py:209-224` (early returns skip the reranker)
**Issue:** The reranker (and therefore `candidate_limit`) only runs on the default hybrid route; the prefix early-returns at hybrid.py:211/217/224 bypass it entirely. The help text ("Reranker candidate pool size") does not mention this.
**Fix:** Either route prefix queries through the rerank stage too, or document in the flag help that it applies only to hybrid/expand queries.

### IN-11: Unused parameters retained in SmartSnippetExtractor (new)

**File:** `src/sif/search/snippets.py:16-24` (`context_radius` accepted and stored, never used — docstring says "kept for API compat"), `src/sif/search/snippets.py:79` (`_build_window`'s `_query_terms` parameter unused)
**Issue:** Signature implies behavior that does not exist; invites misuse.
**Fix:** Remove `context_radius` (or implement radius-based context), drop the unused parameter.

### IN-12: `--full` has no visible effect on default table output (new)

**File:** `src/sif/cli/commands/search.py:231-232, 578-579` (Content column added only `if line_numbers and any(...)`); `src/sif/cli/commands/search.py:152-157, 454-462` (`include_content=full`)
**Issue:** The Content column requires both `--full` and `--line-numbers`, so `sif search query Q --full` (without `--line-numbers`) fetches full document content per result (extra per-result DB reads, plus snippet extraction over full text) but renders only the 200-char Snippet cell — the fetched content is invisible unless JSON/table+line-numbers output is chosen. Users reasonably expect `--full` to show more.
**Fix:** Add the Content column when `full or line_numbers`, or document the interaction in the flag help.

### IN-13: QueryExpansion docstring/contract inconsistencies (new)

**File:** `src/sif/search/expansion.py:34-39` vs `:57, :130` (`expansion_factor` documented as "expansion terms to add per query term" but actually caps the total top-k variants); `src/sif/search/expansion.py:149-155` (`expand_batch` deduplicates case-sensitively while `SearchPipeline.search` dedups variants case-insensitively — hybrid.py:239-243 — so batch and pipeline paths can diverge on near-duplicate variants)
**Issue:** Two dedup notions and a docstring/behavior mismatch make the expansion contract hard to reason about.
**Fix:** Align `expand_batch` with the pipeline's case-insensitive dedup and correct the `expansion_factor` docstring to "maximum number of expansion variants".

---

_Reviewed: 2026-09-05T01:16:21Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
