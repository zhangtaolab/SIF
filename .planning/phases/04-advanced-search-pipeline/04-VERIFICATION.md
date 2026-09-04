---
phase: 04-advanced-search-pipeline
verified: 2026-09-04T16:12:43Z
status: gaps_found
score: 7/8 must-haves verified
behavior_unverified: 0 # Count of PRESENT_BEHAVIOR_UNVERIFIED truths; real-model reranker/HyDE quality items are routed to human verification in the report body
overrides_applied: 0
gaps:
  - truth: "Search results show the most relevant snippet extracted from each chunk"
    status: partial
    reason: >-
      The SmartSnippetExtractor engine is implemented, unit-tested (10 tests), and wired
      into SearchPipeline's default hybrid path, but the last mile is missing: the CLI
      never renders r.snippet in any human-facing output (grep of src/sif/cli/ shows the
      field is only serialized by SearchResult.to_dict() into --json); snippet extraction
      in the pipeline requires result.content to be populated, which only happens with
      --full (include_content), so default searches never extract a snippet; and the
      lex:/vec:/hyde: prefix routes return early before the snippet stage. Empirically
      verified: hybrid+content yields a correct snippet; hybrid-without-content and
      lex:-with-content both yield snippet=None. No pipeline, CLI, or integration test
      asserts snippet extraction or display. 04-UI-REVIEW independently flags the same
      defect ("snippets are never shown", "SRCH-07 is invisible to table users").
    artifacts:
      - path: src/sif/cli/commands/search.py
        issue: >-
          query_cmd's rich table (lines 553-575) has no Snippet/Content column except
          behind --line-numbers; r.snippet is never rendered anywhere in the CLI, only
          serialized via to_dict() in --json output
      - path: src/sif/search/hybrid.py
        issue: >-
          SearchPipeline.search returns early on the BM25/VECTOR/HYDE routes (lines
          209-221), skipping the snippet stage; the snippet loop (lines 268-272) requires
          result.content, which is only fetched when include_content/--full is set
    missing:
      - Render a truncated snippet (falling back to highlights) as a default column in the query/search rich tables
      - Fetch content (or best-chunk content) for snippet extraction when include_content is False so default searches carry snippets
      - Apply snippet extraction on the lex:/vec:/hyde: routes before returning
      - Add pipeline/CLI tests asserting snippet extraction and display end to end
---

# Phase 4: Advanced Search Pipeline Verification Report

**Phase Goal:** Users can perform high-quality hybrid searches with reranking, query expansion, and diagnostic visibility.
**Verified:** 2026-09-04T16:12:43Z
**Status:** gaps_found
**Re-verification:** No — initial verification

**Verification mode note:** Retroactive verification (phase-gate bookkeeping). Phase 04 was executed 2026-04-17 under the package name `docsift`; the project was renamed to `sif` in phase 08. Plan frontmatter paths (`src/docsift/...`) were verified against the current tree (`src/sif/...`), per instruction.

## Goal Achievement

### Observable Truths

Roadmap success criteria are the contract; plan-level must_haves were merged in and folded into the evidence column.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can apply LLM reranking to search results for better relevance ranking | ✓ VERIFIED | `src/sif/search/rerank.py`: `LlamaCppReranker` (GGUF via llama-cpp-python, primary per D-04), `CrossEncoderReranker` (sentence-transformers fallback), `Qwen3Reranker` (later addition), `create_reranker(settings)` factory honoring `reranker_model_type` (default `gguf`). Independent settings (`reranker_model_name/path/type/batch_size` in `src/sif/config/settings.py:82-97`). Wired: `query_cmd` builds reranker via `create_reranker` when configured (`src/sif/cli/commands/search.py:464,483-491`); `SearchPipeline.search` applies `reranker.rerank(parsed_query, candidates, top_k=options.limit)` with fail-fast (`src/sif/search/hybrid.py:259-265`). Tests pass: `test_pipeline_with_reranker`, `test_rerank_adds_reranker_score`, `test_create_reranker_gguf_default`, `test_rerank_sorts_by_score`. "Better relevance" with a real model needs human confirmation (see Human Verification). |
| 2 | User can use query document syntax (`lex:`, `vec:`, `hyde:`, `expand:`) for targeted search modes | ✓ VERIFIED | `_parse_query_prefix` maps all four prefixes (`src/sif/search/hybrid.py:276-287`); routing at lines 209-231. Tests pass: `test_parse_query_prefix_{lex,vec,hyde,expand,default}`, `test_pipeline_prefix_lex_routes_to_bm25`, `test_pipeline_prefix_vec_raises_without_embedder`, `test_pipeline_prefix_hyde_raises_without_generate`. E2E smoke test against a real SQLite FTS5 index confirmed `lex: decorators` routes to BM25 and returns the expected document. Advisory: 04-REVIEW CR-03 — vec:/hyde: and no-BM25 hybrid paths return chunk-level duplicate documents (dedup only runs on the fused path); the modes work, result quality is affected. |
| 3 | User can see score breakdowns across BM25, RRF, and reranker stages with `--explain` | ✓ VERIFIED | `RRFFusion.fuse`/`fuse_with_weights` preserve `bm25_score`, `vector_score`, `rrf_score` in `SearchResult.scores` (`src/sif/search/rrf.py:45-52,88`); reranker adds `reranker_score` (`rerank.py:29-31`); `query_cmd --explain` prints per-result score breakdowns (`search.py:577-581`). Tests pass: `test_fuse_preserves_bm25_and_vector_scores`, `test_fuse_with_weights_preserves_scores`, `test_explain_preserves_scores`, `test_query_with_explain` (asserts `bm25_score=` in CLI output; passes with `FORCE_COLOR` unset — see Environment note). Advisory: 04-REVIEW WR-09 — multi-list fusion (expanded queries) mislabels later lists' scores as `vector_score`. |
| 4 | User can filter low-confidence results with `--min-score` and retrieve full document content with `--full` | ✓ VERIFIED | `--min-score` and `--full` present on `search_cmd` (`search.py:92-93`), `vsearch_cmd` (`242-243`), `query_cmd` (`373-374`); wired into `SearchOptions(min_score=..., include_content=full)`. Filtering is real data flow, not cosmetic: `bm25.py:82,158` and `vector.py:92` skip rows below threshold. Tests pass: `test_search_applies_min_score`, `test_vsearch_with_min_score`, `test_vsearch_with_full`. E2E smoke test: `min_score=0.9999` returned 0 results against a real index. |
| 5 | User can control how many candidates enter the reranker with `--candidate-limit` | ✓ VERIFIED | `query_cmd` `-C/--candidate-limit` with `click.IntRange(1, 200)` (`search.py:376-382`); pipeline caps before reranking: `candidates = results[: options.candidate_limit]` (`hybrid.py:258-262`). Tests pass: `test_pipeline_candidate_limit`, `test_query_with_candidate_limit`, `test_query_candidate_limit_out_of_range`. |
| 6 | User can pass intent hints through `--intent` to guide search behavior | ✓ VERIFIED | `query_cmd --intent` (`search.py:383`); `SearchOptions.intent` (`models.py:253`); pipeline prepends intent to the parsed query before search (`hybrid.py:204-206`). Test passes: `test_intent_prepended_to_query`, `test_query_with_intent`. Advisory: 04-REVIEW WR-03 — intent is prepended as literal query text (a hard AND term on the lex: route) rather than passed to the expander's dedicated `intent` parameter; the existing test encodes this design. |
| 7 | Search results show the most relevant snippet extracted from each chunk | ✗ FAILED | Extraction half delivered: `SmartSnippetExtractor` (`src/sif/search/snippets.py`) scores sentences by weighted term frequency and builds a window — 10 unit tests pass (`test_snippets.py`), and an E2E smoke test against a real index produced a correct snippet on the hybrid+content path. Display half missing: the CLI never renders `r.snippet` (only `to_dict()` → `--json`); default searches (no `--full`) never fetch content so never extract; `lex:`/`vec:`/`hyde:` routes return before the snippet stage (empirically: `lex:` with content → `snippet=None`). No pipeline/CLI/integration test asserts snippet flow. 04-UI-REVIEW finding 3 corroborates. See Gaps Summary. |
| 8 | User can run benchmark fixtures to measure precision@k, recall, and MRR | ✓ VERIFIED | `src/sif/search/benchmark.py`: `precision_at_k`, `recall_at_k`, `reciprocal_rank`, `mean_reciprocal_rank`, `SearchEvaluator.evaluate()` averaging across fixture queries; `bench_cmd` loads JSON fixtures, runs the real `SearchPipeline` per query, outputs rich table or `--json` (`src/sif/cli/commands/bench.py`); registered in `cli/main.py:74,93`. Tests pass (20 total): `test_evaluate_single_query`, `test_evaluate_multiple_queries`, `test_bench_with_valid_fixture`, `test_bench_json_output`. `python -m sif.cli.main bench --help` verified live. Advisory: 04-REVIEW WR-07 (`bench -C` is a dead flag — bench's pipeline has no reranker) and WR-08 (per-query `collections` fixture field silently ignored). |

**Score:** 7/8 truths verified (0 present, behavior-unverified)

### Required Artifacts

All plan-declared artifacts exist in the current (renamed) tree, are substantive, and are wired. Key ones:

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/sif/core/models.py` | SearchResult with scores dict + snippet; SearchOptions with explain/candidate_limit/intent; HYDE/EXPAND SearchTypes | ✓ VERIFIED | `scores: dict[str, float \| None]` (line 219), `snippet` (220), `explain/candidate_limit/intent/snippet_max_length` (251-254), enum values (29-30) |
| `src/sif/config/settings.py` | Independent reranker settings | ✓ VERIFIED | `reranker_model_name/path/type/batch_size` (lines 82-97) |
| `src/sif/search/rrf.py` | fuse() preserves bm25/vector/rrf scores | ✓ VERIFIED | Both `fuse` and `fuse_with_weights` |
| `src/sif/search/rerank.py` | create_reranker factory, LlamaCpp (default) + CrossEncoder fallback | ✓ VERIFIED | 394 lines, three backends + factory + alias |
| `src/sif/search/expansion.py` | QueryExpansion.expand() -> list[str] with embedding-based PRF | ✓ VERIFIED | Protocol-compliant return; synonym map + cosine-similarity PRF; `expand_batch` dedup |
| `src/sif/search/snippets.py` | SmartSnippetExtractor.extract(text, query_terms) -> str | ✓ VERIFIED | Sentence scoring, window building, ellipsis, fallback |
| `src/sif/search/hybrid.py` | SearchPipeline with prefix routing, explainability, candidate capping, intent | ✓ VERIFIED | 330 lines; full pipeline verified above |
| `src/sif/cli/commands/search.py` | query/search/vsearch with all phase flags | ✓ VERIFIED | All flags present and wired |
| `src/sif/search/benchmark.py` | Metrics + SearchEvaluator | ✓ VERIFIED | All four metrics + evaluator |
| `src/sif/cli/commands/bench.py` + `main.py` registration | bench_cmd | ✓ VERIFIED | Registered (main.py:74,93), help verified live |
| Test files (8 phase-scoped) | Per plan 04-05 | ✓ VERIFIED | All exist; 159 phase-scoped tests pass (see Spot-Checks) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| cli/commands/search.py | search/hybrid.py | `SearchPipeline(...)` + `.search(query, options)` | ✓ WIRED | search.py:497-505 |
| cli/commands/bench.py | search/hybrid.py | `SearchPipeline(...)` + `.search()` | ✓ WIRED | bench.py:117-122 |
| search/hybrid.py | search/expansion.py | `query_expander.expand(parsed_query)` | ✓ WIRED | hybrid.py:232 |
| search/hybrid.py | search/rerank.py | `reranker.rerank(query, candidates)` | ✓ WIRED | hybrid.py:262; CLI factory at search.py:485 |
| search/hybrid.py | search/snippets.py | `snippet_extractor.extract(content, query_terms)` | ✓ WIRED | hybrid.py:272 (default route only — contributes to Truth 7 gap) |
| cli/commands/bench.py | search/benchmark.py | `SearchEvaluator(fixture_data).evaluate(search_fn)` | ✓ WIRED | bench.py:125-127 |
| search/rrf.py | core/models.py | `SearchResult.scores` dict | ✓ WIRED | bm25_score/vector_score/rrf_score keys |
| search/snippets.py | search/bm25.py | "reuses BM25 highlight logic" (plan 04-02 key link) | ⚠️ DEVIATED | snippets.py does not import bm25.py; it implements its own weighted term-frequency scoring, and the caller computes `query_terms = parsed_query.lower().split()` (hybrid.py:271) — equivalent intent achieved by alternative means. Info-level; roadmap SC does not require the import. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| bm25.py | results | `documents_fts` FTS5 MATCH query | Yes | ✓ FLOWING |
| vector.py | results | `document_embeddings` vec search | Yes | ✓ FLOWING |
| rrf.py | scores | computed from searcher outputs | Yes | ✓ FLOWING |
| bench.py | metrics | SearchEvaluator over real pipeline per fixture query | Yes | ✓ FLOWING |
| search.py CLI explain block | `r.scores` | pipeline fusion/reranker stages | Yes | ✓ FLOWING |
| search.py CLI snippet display | `r.snippet` | pipeline extraction (requires content) | No render target exists | ✗ HOLLOW (Truth 7 gap) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase-scoped test suite | `pytest` (10 phase-04 test files, FORCE_COLOR unset) | 159 passed in 0.11s | ✓ PASS |
| 10 named behavioral tests (routing, candidate limit, explain, RRF preservation, benchmark, min-score, CLI flags, bench) | `pytest <named tests>` | 10 passed with FORCE_COLOR unset | ✓ PASS |
| lex: prefix routes to BM25 on a real index | E2E smoke (real SQLite + FTS5) | returned expected document | ✓ PASS |
| min-score filters on a real index | E2E smoke, `min_score=0.9999` | 0 results | ✓ PASS |
| Snippet extraction (hybrid + content) | E2E smoke | `'Python decorators wrap functions. Decorators use the @ syntax....'` | ✓ PASS |
| Snippet on lex: route (with content) | E2E smoke | `snippet=None` (early return skips stage) | ✗ FAIL (gap evidence) |
| Snippet on default hybrid (no --full) | E2E smoke | `snippet=None` (no content fetched) | ✗ FAIL (gap evidence) |
| bench CLI entry point | `python -m sif.cli.main bench --help` | usage + all options | ✓ PASS |
| ruff on all phase files | `ruff check <15 paths>` | All checks passed | ✓ PASS |
| Documented commits exist | `git cat-file -t <hash>` ×9 | 7/9 exist; `4acf4d3`, `6473394` (04-02) missing | ⚠️ WARNING |

**Environment note (test reliability):** this sandbox exports `FORCE_COLOR=3`, which Rich honors *over* `NO_COLOR=1`, injecting ANSI escapes into CliRunner output and failing plain-text assertions (`test_query_with_explain`, `test_bench_json_output`, line-number tests). `env -u FORCE_COLOR NO_COLOR=1 pytest ...` passes cleanly (159/159). The 04-VALIDATION.md guidance ("run with NO_COLOR=1") is insufficient on hosts that set FORCE_COLOR; recommend `env -u FORCE_COLOR` in gate scripts. Not a code regression.

### Probe Execution

No phase-declared probes and no `scripts/*/tests/probe-*.sh` exist (the single "probe" grep hit in 04-04-PLAN.md is the `embed_single("probe")` warm-up string in bench.py). Step 7c: N/A for this phase type.

### Requirements Coverage

| Requirement | Source Plan | Description (from REQUIREMENTS.md) | Status | Evidence |
|-------------|------------|-------------------------------------|--------|----------|
| SRCH-01 | 01, 05 | Configurable LLM reranker, llama-cpp GGUF cross-encoder | ✓ SATISFIED | rerank.py + settings + factory + CLI wiring |
| SRCH-02 | 02, 05 | LLM query expansion (lex/vec/hyde variants) | ✓ SATISFIED | expansion.py, wired at hybrid.py:232 |
| SRCH-03 | 03, 05 | Query document syntax lex:/vec:/hyde:/expand: | ✓ SATISFIED | hybrid.py:276-287 + tests + E2E |
| SRCH-04 | 01, 03, 05 | `--explain` stage score traces | ✓ SATISFIED | rrf.py score preservation + search.py:577-581 + tests |
| SRCH-05 | 01, 03, 05 | `--candidate-limit` / `-C` | ✓ SATISFIED | IntRange 1-200 + hybrid.py:258-262 + tests |
| SRCH-06 | 03, 05 | `--intent` passed through search stages | ✓ SATISFIED | search.py:383 + hybrid.py:204-206 + test (advisory: literal-prepend design, WR-03) |
| SRCH-07 | 02, 05 | Smart snippet extraction from chunks by weighted term frequency | ✗ PARTIAL | Extractor implemented/tested; never rendered to users; skipped on prefix routes and without --full |
| SRCH-08 | 04, 05 | `bench` command with fixture JSON, precision@k/recall/MRR | ✓ SATISFIED | benchmark.py + bench.py + main.py registration + 20 tests |
| CLI-06 | 03, 05 | `--min-score` filters low-confidence results | ✓ SATISFIED | Flags on all three commands; real filtering in searchers |
| CLI-07 | 03, 05 | `--full` returns full document content | ✓ SATISFIED | include_content wiring + test_vsearch_with_full |

No orphaned requirements: REQUIREMENTS.md maps exactly these 10 IDs to Phase 4 (traceability lines 107-116), and all 10 appear in plan frontmatters. Note: REQUIREMENTS.md still lists all 10 as "Pending" — stale bookkeeping, not an implementation signal.

### Anti-Patterns Found

No debt markers (`TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`) and no stub implementations in any phase file.

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| 04-REVIEW.md CR-01/CR-02 (cli/search.py --line-numbers formatters; cli/main.py sqlite3 NameError) | Code review findings | ℹ️ Advisory | Both outside phase-04 SCs (`--line-numbers` and `cleanup` are later-phase artifacts); recorded for follow-up, not phase blockers |
| 04-REVIEW.md CR-03 (vector-only chunk duplicates) | Code review finding | ⚠️ Warning | Degrades vec:/hyde:/vsearch result quality; SC 2 (routing works) still verified |
| 04-REVIEW.md WR-03/WR-07/WR-08/WR-09 (intent pollution, dead bench flag, ignored fixture field, explain provenance) | Code review findings | ℹ️ Advisory | Truths verified; quality follow-ups recommended |
| 04-02-SUMMARY commits `4acf4d3`, `6473394` | Commit hashes not in repo history | ⚠️ Warning | History was rewritten (phase-08 era); work demonstrably survives in the tree — expansion.py reimplemented in `ade4bc9` (04-05), snippets.py first appears in current history at `ba8a440`. Bookkeeping discrepancy only |
| hybrid.py:259 `len(results) > 0` | Redundant truthiness (IN-02) | ℹ️ Info | Cosmetic |

### Human Verification Required

These require a real model download and/or a real personal index; they cannot be verified by grep or mock-based tests.

1. **Real-model reranking quality (SC 1)**
   - **Test:** Configure `reranker_model_name` (GGUF cross-encoder or `cross-encoder/ms-marco-MiniLM-L-6-v2`), run `sif search query <terms>` on a real index with and without reranking, and with `--explain`.
   - **Expected:** Reranked order is more relevant; explain output shows `reranker_score` alongside `bm25_score`/`vector_score`/`rrf_score`.
   - **Why human:** Unit tests exercise the pipeline with mocked backends only; "better relevance" is a real-model judgment.
2. **HyDE end-to-end (SC 2, hyde: route)**
   - **Test:** `sif search query hyde: <question>` with a generation-capable GGUF embedder.
   - **Expected:** A hypothetical document is generated, embedded, and vector-searched; no RuntimeError.
   - **Why human:** Requires a text-generation-capable model; the no-generate RuntimeError path is unit-tested but the real generation path is not.
3. **bench on a real corpus (SC 8)**
   - **Test:** Author a fixture with real queries and judged relevant docids from your own index; run `sif bench fixture.json` and `--json`.
   - **Expected:** Table/JSON metrics consistent with manual relevance judgments.
   - **Why human:** Requires a real index and human relevance judgments.

### Gaps Summary

One must-have truth failed (partially): **SC 7 — "Search results show the most relevant snippet extracted from each chunk."** The extraction engine (`SmartSnippetExtractor`) is fully implemented, tested, and wired into the pipeline's default hybrid path, but the user-visible half is missing: the CLI renders `r.snippet` nowhere (only `to_dict()` into `--json`), extraction depends on `--full` for content so default searches carry no snippet, and the `lex:`/`vec:`/`hyde:` routes return before the snippet stage. The gap is corroborated independently by 04-UI-REVIEW finding 3 and by empirical E2E runs (hybrid+content → correct snippet; lex:+content and hybrid-without-content → `None`). Fixing it is a small, focused CLI change (render + content-fetch + route coverage + one test), structured in the frontmatter for `/gsd-plan-phase --gaps`.

Everything else the phase promised is present and demonstrably working in the current tree: all four prefix routes, reranker stack with GGUF-primary per D-04, score preservation across RRF and reranker stages with `--explain` display, `--min-score`/`--full`/`--candidate-limit`/`--intent` flags wired to real behavior, and the bench/evaluator toolchain — 159 phase-scoped tests pass, ruff is clean, no debt markers.

The 04-REVIEW Critical/Warning findings (CR-01..03, WR-01..12) are real defects in the current tree but map to quality/robustness follow-ups rather than failed phase-04 success criteria; they are catalogued above as advisory and should feed the next hardening pass. If the maintainer judges JSON-only snippet surfacing acceptable for this phase, SC 7 can be closed via an `overrides:` entry in this file's frontmatter instead of a gap plan.

---

_Verified: 2026-09-04T16:12:43Z_
_Verifier: Claude (gsd-verifier)_
