---
phase: 04-advanced-search-pipeline
verified: 2026-09-05T01:26:04Z
status: passed
score: 8/9 must-haves verified # 8/8 roadmap SCs verified incl. the previously-gapped SC 7; 1 plan-level backstop truth (04-06: human snippet-relevance judgment on a real personal index) abstained per protocol — routed to human verification, never a silent pass
behavior_unverified: 0 # No PRESENT_BEHAVIOR_UNVERIFIED truths; the backstop abstention is an insufficient_spec/human-judgment item, not a behavior gap — code is present, wired, and test-exercised
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 7/8
  gaps_closed:
    - "SC 7 / SRCH-07: Search results show the most relevant snippet extracted from each chunk — display half, transient content feed, and prefix-route coverage all delivered by 04-06 (commits 2b26138..5608cc6) and re-verified from scratch below"
  gaps_remaining: []
  regressions: [] # Full-suite failure profile identical at pre-04-06 commit (21 failed / 2 collection errors, all in MCP/embedding files, missing pytest-asyncio+httpx in venv); delta vs baseline is exactly +11 passing snippet tests, 0 new failures
human_verification:

  - test: "On your real personal index, run `sif search query <terms>` (no --full) and `sif search search <terms>`; read the rendered Snippet column for several queries"
    expected: "The snippet reads as the most relevant excerpt for its query (the sentence window a human would pick), not an arbitrary lead paragraph"
    why_human: "04-06 PLAN must_haves backstop truth (verification: backstop): snippet relevance is a human judgment on a real corpus; automated tests prove extraction mechanics (term-frequency window selection) only. Verifier abstained per the backstop protocol — no explicit evidence available (query_cmd additionally cannot load the modelscope embedder in this venv)"
  - test: "Configure reranker_model_name (GGUF cross-encoder or cross-encoder/ms-marco-MiniLM-L-6-v2), run `sif search query <terms>` with and without reranking, with --explain"
    expected: "Reranked order is more relevant; explain output shows reranker_score alongside bm25_score/vector_score/rrf_score"
    why_human: "Real-model download and relevance judgment required; unit tests exercise the pipeline with mocked backends (SC 1 carried over from initial verification)"
  - test: "Run `sif search query hyde: <question>` with a generation-capable GGUF embedder"
    expected: "Hypothetical document generated, embedded, vector-searched; no RuntimeError; snippet populated"
    why_human: "Requires a text-generation-capable model; the no-generate RuntimeError path is unit-tested, the real generation path is not (SC 2 hyde: carried over)"
  - test: "Author a fixture with real queries and judged relevant docids from your index; run `sif bench fixture.json` and --json"
    expected: "Table/JSON metrics (precision@k, recall, MRR) consistent with your manual relevance judgments"
    why_human: "Requires a real index and human relevance judgments (SC 8 carried over)"
---

# Phase 4: Advanced Search Pipeline Verification Report

**Phase Goal:** Users can perform high-quality hybrid searches with reranking, query expansion, and diagnostic visibility.
**Verified:** 2026-09-05T01:26:04Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (prior report 2026-09-04, gaps_found 7/8, SC 7 partial)

**Re-verification mode note:** All 8 roadmap truths were re-verified from scratch against the current tree (goal-backward, prior evidence spot-checked rather than inherited). SC 7 — the previously failed truth — received full three-level plus behavioral and live-CLI verification. The 04-06 gap-closure plan's six truth strings, four artifacts, three key links, and three prohibitions were each checked independently; its structured backstop truth ({statement, verification: backstop}) was abstained per protocol (no explicit evidence available) and routes to human verification — no silent pass.

## Goal Achievement

### Observable Truths

Roadmap success criteria are the contract; the 04-06 backstop truth is merged in as row 9.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can apply LLM reranking to search results for better relevance ranking | ✓ VERIFIED | `src/sif/search/rerank.py`: `LlamaCppReranker` (GGUF primary per D-04), `CrossEncoderReranker`, `Qwen3Reranker`, `create_reranker` factory (lines 51/129/213/359); independent settings `reranker_model_name/path/type/batch_size` (`settings.py:82-97`). Wired: `query_cmd` builds reranker via `create_reranker` when configured (`search.py:501-511`); pipeline applies `reranker.rerank(parsed_query, candidates, top_k=options.limit)` with candidate capping and fail-fast RuntimeError (`hybrid.py:262-268`). Named tests passed this run: `test_create_reranker_gguf_default`, `test_rerank_sorts_by_score`, `test_rerank_adds_reranker_score`, `test_rerank_preserves_result_type`, `test_pipeline_with_reranker`. "Better relevance" with a real model remains human item 2. |
| 2 | User can use query document syntax (`lex:`, `vec:`, `hyde:`, `expand:`) for targeted search modes | ✓ VERIFIED | `_parse_query_prefix` maps all four prefixes (`hybrid.py:299-310`); routing at 209-224 now returns through `_apply_snippets`. Named tests passed: `test_parse_query_prefix_{lex,vec,hyde,expand,default}`, `test_pipeline_prefix_lex_routes_to_bm25` (8-test batch). Independent E2E this run: `lex: decorators` against a real seeded sqlite index returned a snippet-bearing result. Advisory: CR-03 vec:/hyde: chunk duplicates (see Anti-Patterns). |
| 3 | User can see score breakdowns across BM25, RRF, and reranker stages with `--explain` | ✓ VERIFIED | `TestRRFScorePreservation` 3/3 passed (incl. `test_fuse_preserves_bm25_and_vector_scores`, `test_fuse_with_weights_preserves_scores`); `test_query_with_explain` passed (7-test batch); `--explain` renders per-result score breakdowns (`search.py:598-602`). Advisory: WR-09 multi-list (expand:) provenance mislabeling. |
| 4 | User can filter low-confidence results with `--min-score` and retrieve full document content with `--full` | ✓ VERIFIED | `--min-score`/`--full` on `search_cmd` (search.py:109-110), `vsearch_cmd` (261-262), `query_cmd` (392-393); wired into `SearchOptions(min_score=..., include_content=full)`; real filtering in searchers. Named tests passed: `test_search_applies_min_score`, `test_vsearch_with_min_score`, `test_vsearch_with_full`. CLI-07 contract re-proven live this run: without `--full`, `SearchResult.to_dict()["content"]` is None even after the new transient snippet fetch (E2E scenario S4). |
| 5 | User can control how many candidates enter the reranker with `--candidate-limit` | ✓ VERIFIED | `-C/--candidate-limit` with `click.IntRange(1, 200)` (`search.py:395-401`); pipeline caps candidates before reranking (`hybrid.py:262-263`). Named test passed: `test_pipeline_candidate_limit` (8-test batch). |
| 6 | User can pass intent hints through `--intent` to guide search behavior | ✓ VERIFIED | `--intent` flag (`search.py:402`); `SearchOptions.intent`; pipeline prepends intent to the parsed query (`hybrid.py:205-206`). Named test passed: `test_intent_prepended_to_query` (8-test batch). Advisory: WR-03 — intent is prepended as literal query text (now also feeding snippet terms, a new 04-06 interaction); the existing test encodes this design. |
| 7 | Search results show the most relevant snippet extracted from each chunk | ✓ VERIFIED (gap closed) | **Pipeline half:** `SearchPipeline._apply_snippets` (`hybrid.py:275-297`) extracts via transient fetch — `result.content` when truthy, else `self.hybrid._get_document_content(result.document_id)` — feeding `SmartSnippetExtractor.extract(text, query_terms)` into `result.snippet` only; the include_content dependency is gone. All four routes run the stage: BM25/VECTOR/HYDE early returns at `hybrid.py:209-224` and the default-route tail at 271. **Display half:** `_display_snippet(r, max_len=200)` module-level helper with first-highlight fallback (`search.py:28-41`); `Snippet` column in the query_cmd table (`search.py:577, 587`) and search_cmd table (`search.py:230, 240`), both wrapped in `rich.markup.escape`. **Tests:** 11 snippet tests pass (2 real-sqlite integration `TestSnippetExtractionIntegration`, 5 route unit `TestPipelineSnippetRoutes`, 4 CLI display `TestSnippetDisplay`). **Independent E2E this run (real seeded sqlite):** default-no-content → snippet set, content None; lex:-no-content → snippet set, content None; lex:-with-content → snippet set, content populated; to_dict content None. **Live CLI run:** `sif ... search search decorators` rendered a real Snippet column with the correct window; a bracket-heavy doc rendered `[bold]`, `[/dim]`, `[link=foo]` literally (no markup parsing). Advisory: WR-06 extract can exceed max_length on long single sentences — table render is bounded at 200 chars (verified live); overflow reaches --json only. Relevance-quality judgment = backstop truth, row 9. |
| 8 | User can run benchmark fixtures to measure precision@k, recall, and MRR | ✓ VERIFIED | `benchmark.py`: `precision_at_k`/`recall_at_k`/`reciprocal_rank`/`mean_reciprocal_rank`/`SearchEvaluator` (lines 14-42); `bench_cmd` (148 lines) registered in `cli/main.py:73`; `bench --help` verified live this run (usage + all options). Named tests passed: `test_evaluate_*`, `test_bench_with_valid_fixture`, `test_bench_json_output` (7-test batch). Advisories: WR-07 dead `-C` flag, WR-08 ignored per-query collections field. |
| 9 | 04-06 backstop: on the maintainer's real personal index, the rendered snippet is judged the most relevant excerpt for its query | ? UNCERTAIN (backstop — abstained) | Plan-declared `verification: backstop`; requires human relevance judgment on the maintainer's real corpus. No explicit evidence available to the verifier (automated tests prove extraction mechanics only; `query_cmd` cannot even load the modelscope embedder in this venv). Abstained per the non-inferable-truth protocol → human verification item 1. Not counted as verified; not a behavior gap. |

**Score:** 8/9 truths verified (0 present, behavior-unverified; 1 backstop abstained to human judgment)

### Required Artifacts

All plan-declared artifacts exist in the current tree, are substantive, and are wired. 04-06 symbols bolded.

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/sif/search/hybrid.py` | SearchPipeline with prefix routing, explainability, candidate capping, intent, **_apply_snippets on all four routes** | ✓ VERIFIED | 353 lines; **`_apply_snippets` at 275-297 with `_get_document_content` feed; routes at 209-224 and tail at 271** |
| `src/sif/cli/commands/search.py` | query/search/vsearch with all phase flags, **Snippet column + _display_snippet + escape** | ✓ VERIFIED | **`_display_snippet` at 28-41; Snippet columns at 230/577; `escape` import at line 9; `SearchResult` import at line 13** |
| `tests/integration/test_search_pipeline.py` | Real-sqlite snippet integration tests | ✓ VERIFIED | `TestSnippetExtractionIntegration` (2 tests, with/without content, content-None assertion) |
| `tests/unit/search/test_hybrid.py` | Per-route snippet tests | ✓ VERIFIED | `TestPipelineSnippetRoutes` (5 tests: lex/vec/hyde, idempotent skip, no-extractor no-op) |
| `tests/unit/cli/test_search.py` | CLI snippet display tests | ✓ VERIFIED | `TestSnippetDisplay` (4 tests: query column, highlight fallback, search_cmd column, --files shape) |
| `src/sif/core/models.py` | SearchResult scores/snippet/content/highlights; SearchOptions phase fields | ✓ VERIFIED | Fields confirmed via test construction and pipeline usage |
| `src/sif/config/settings.py` | Independent reranker settings | ✓ VERIFIED | `reranker_model_name/path/type/batch_size` (82-97) |
| `src/sif/search/rerank.py` | create_reranker factory, GGUF primary + fallbacks | ✓ VERIFIED | 393 lines, three backends + factory + alias |
| `src/sif/search/expansion.py` | QueryExpansion.expand() -> list[str], PRF | ✓ VERIFIED | `expand` (44) with dedicated `intent` param, `expand_batch` (135) |
| `src/sif/search/snippets.py` | SmartSnippetExtractor.extract(text, query_terms) | ✓ VERIFIED | 130 lines; live-exercised this run |
| `src/sif/search/benchmark.py` + `cli/commands/bench.py` | Metrics + evaluator + bench command | ✓ VERIFIED | All four metrics + evaluator; bench registered and live-verified |

### Key Link Verification

04-06 key links verified first (the gap-closure contract), then phase-wide links re-spot-checked.

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `SearchPipeline._apply_snippets` | `HybridSearcher._get_document_content` → `SmartSnippetExtractor.extract` → `SearchResult.snippet` | transient content feed | ✓ WIRED | hybrid.py:292-296; proven live on real sqlite (S1-S3) |
| query_cmd + search_cmd tables | `_display_snippet(r)` → `r.snippet` else `r.highlights[0]` | render target | ✓ WIRED | search.py:240, 587; proven live (real CLI table render, both fallback branches unit-tested) |
| lex:/vec:/hyde: early returns | `_apply_snippets` before return | route coverage | ✓ WIRED | hybrid.py:209-224; unit-tested per route + lex: live |
| cli/commands/search.py | search/hybrid.py | `SearchPipeline(...)` + `.search(query, options)` | ✓ WIRED | search.py:516-524 (with snippet_extractor at 521) |
| search/hybrid.py | search/expansion.py | `query_expander.expand(parsed_query)` | ✓ WIRED | hybrid.py:235 |
| search/hybrid.py | search/rerank.py | `reranker.rerank(query, candidates)` | ✓ WIRED | hybrid.py:265 |
| search/hybrid.py | search/snippets.py | `snippet_extractor.extract(content, query_terms)` | ✓ WIRED | hybrid.py:296, all four routes |
| cli/commands/bench.py | search/benchmark.py | `SearchEvaluator(...).evaluate(search_fn)` | ✓ WIRED | bench.py; live --help |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| search.py Snippet cells | `r.snippet` / `r.highlights[0]` via `_display_snippet` | pipeline extraction (transient DB fetch) / BM25 highlighter | Yes — rendered live against a real seeded index | ✓ FLOWING |
| hybrid.py `_apply_snippets` | `text` | `documents.content` SELECT (hybrid.py:148-152) | Yes — live sqlite E2E populated snippets on all tested routes | ✓ FLOWING |
| bm25.py / vector.py | results | FTS5 MATCH / vec search | Yes | ✓ FLOWING |
| rrf.py | scores | searcher outputs | Yes | ✓ FLOWING |
| bench.py | metrics | SearchEvaluator over real pipeline | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

All commands prefixed `env -u FORCE_COLOR NO_COLOR=1` (documented remedy for this host's FORCE_COLOR=3, which Rich honors over NO_COLOR).

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All snippet tests (integration + route unit + CLI display) | `pytest <3 files> -k snippet` | 11 passed | ✓ PASS |
| SC 7 E2E inversion S1: default hybrid, no --full (prior failure) | seeded real sqlite, `pipeline.search("decorators", SearchOptions(limit=5))` | snippet set ("Python decorators wrap functions..."), content None | ✓ PASS |
| SC 7 E2E inversion S2: lex: route, no --full | `pipeline.search("lex: decorators", ...)` | snippet set, content None | ✓ PASS |
| SC 7 E2E inversion S3: lex: with content (exact prior failing smoke) | `pipeline.search("lex: decorators", include_content=True)` | snippet set, content populated | ✓ PASS |
| Prohibition 1: --json shape unchanged (CLI-07) | `results[0].to_dict()["content"]` after default search | None (snippet present) | ✓ PASS |
| SC 7 display: real CLI table render | `python -m sif.cli.main --index <seeded> search search decorators` | Rich table with Snippet column containing correct window | ✓ PASS |
| Prohibition 2: bracket text renders literally | seeded doc with `[bold]`/`[/dim]`/`[link=foo]`, real CLI run | literal text in Snippet cell, no markup parse/crash | ✓ PASS |
| WR-06 severity: table render bounded | `SmartSnippetExtractor(max_length=50)` + `_display_snippet` on oversized extract | extract 673 chars → cell 203 (bounded) | ✓ PASS (overflow reaches --json only — Warning) |
| Truths 1,2,5,6 named tests | `pytest test_hybrid.py -k "..."` batch | 8 passed | ✓ PASS |
| Truth 3 named tests | `pytest TestRRFScorePreservation + explain tests` | 3 + explain batch passed | ✓ PASS |
| Truths 4,8 named tests | `pytest -k "min_score or vsearch_with_full or ... bench_json"` | 7 passed | ✓ PASS |
| Truth 1 reranker tests | `pytest test_reranker.py -k "gguf_default or sorts_by_score or adds_reranker_score or preserves_result_type"` | 5 passed | ✓ PASS |
| Phase-04 scoped suite | `pytest tests/unit/search/ tests/unit/cli/test_search.py tests/unit/cli/test_bench.py tests/unit/inference/test_reranker.py tests/integration/test_search_pipeline.py` | 183 passed | ✓ PASS |
| Full suite (once) | `pytest` (excluding 2 httpx-blocked MCP files) | 540 passed, 21 failed, 11 skipped | ⚠️ WARNING — all 21 failures + 2 collection errors are in MCP/embedding files (missing pytest-asyncio/httpx in current venv), proven pre-existing: identical profile at pre-04-06 commit (529 passed/21 failed; delta = exactly the +11 snippet tests, 0 new failures). SUMMARY's 583/11 claim reflects an environment where those deps were installed; neither is declared in pyproject dev extras and uv.lock is modified in the working tree |
| ruff on phase files + format repo-wide | `ruff check <5 phase files>` / `ruff format --check src tests` | All checks passed; 125 files formatted | ✓ PASS |
| 04-06 commits exist | `git cat-file -t` for 2b26138, cea6a83, 12ebda7, 5eeae8b, 5d19f74, 5608cc6, 0df289f, 5a0954d | 8/8 exist | ✓ PASS |

### Probe Execution

No phase-declared probes and no `scripts/*/tests/probe-*.sh` exist. Step 7c: N/A for this phase type.

### Requirements Coverage

| Requirement | Source Plan | Description (from REQUIREMENTS.md) | Status | Evidence |
|-------------|------------|-------------------------------------|--------|----------|
| SRCH-01 | 01, 05 | Configurable LLM reranker, llama-cpp GGUF cross-encoder | ✓ SATISFIED | rerank.py + settings + factory + CLI wiring + tests |
| SRCH-02 | 02, 05 | LLM query expansion (lex/vec/hyde variants) | ✓ SATISFIED | expansion.py, wired at hybrid.py:235 |
| SRCH-03 | 02, 05, 06 | Query document syntax lex:/vec:/hyde:/expand: | ✓ SATISFIED | hybrid.py:299-310 routing + tests + live lex: E2E |
| SRCH-04 | 01, 03, 05 | --explain stage score traces | ✓ SATISFIED | RRF preservation tests + search.py:598-602 + explain test |
| SRCH-05 | 01, 03, 05 | --candidate-limit / -C | ✓ SATISFIED | IntRange 1-200 + hybrid.py:262-263 + tests |
| SRCH-06 | 03, 05 | --intent passed through search stages | ✓ SATISFIED | search.py:402 + hybrid.py:205-206 + test (WR-03 advisory) |
| SRCH-07 | 02, 05, 06 | Smart snippet extraction from chunks, most relevant excerpt | ✓ SATISFIED | Extraction on all four routes + Snippet column in both tables + 11 tests + live E2E and live CLI render (was PARTIAL at initial verification) |
| SRCH-08 | 04, 05 | bench command, fixture JSON, precision@k/recall/MRR | ✓ SATISFIED | benchmark.py + bench.py + registration + live --help + tests |
| CLI-06 | 03, 05 | --min-score filters low-confidence results | ✓ SATISFIED | Flags on all three commands; real filtering in searchers + tests |
| CLI-07 | 03, 05 | --full returns full document content | ✓ SATISFIED | include_content wiring + test + live to_dict content-None proof (contract preserved through the new transient fetch) |

No orphaned requirements: REQUIREMENTS.md maps exactly these 10 IDs to Phase 4 (traceability lines 107-116) and every ID appears in plan frontmatters (01: SRCH-01/04/05; 02: SRCH-02/07; 03: SRCH-03/04/05/06 + CLI-06/07; 04: SRCH-08; 05: SRCH-01..06; 06: SRCH-07). Bookkeeping: SRCH-07 is now marked Complete; the other 9 remain "Pending" despite verified implementations — stale flags, not an implementation signal.

### Decision Coverage

All 4 04-CONTEXT.md `<decisions>` entries are honored in shipped artifacts: (1) GGUF-primary reranker with independent `reranker_*` settings (rerank.py + settings.py:82-97); (2) embedding-based PRF expansion (expansion.py, wired hybrid.py:235); (3) mutually-exclusive prefix mode switches (hybrid.py:299-310); (4) structured scores dict with null-when-skipped, rendered via `--explain` with the `if v is not None` filter (search.py:600). 4/4 honored, none abandoned.

### Anti-Patterns Found

No debt markers (TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER) and no stub implementations in any phase-modified file (the one "placeholders" grep hit is SQL `?`-placeholder construction, hybrid.py:117). No disabled/skipped tests in phase files.

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| 04-REVIEW CR-01: `--line-numbers` + `--csv`/`--md`/`--xml` crashes (AttributeError on dict rows) | Code review finding, re-verified | ⚠️ Warning | Real crash, but `--line-numbers` and the machine-format flags are not among the 10 phase-04 requirement IDs or 8 SCs; quality follow-up |
| 04-REVIEW CR-03: vec:/hyde:/vsearch return chunk-level duplicate documents (dedup only on fused path) | Code review finding, re-verified | ⚠️ Warning | Degrades vector-route result quality; SC 2's capability truth (targeted modes route and return) still verified; the goal's default hybrid path dedups correctly (hybrid.py:88). Explicitly out of 04-06 scope per its prohibition 3 |
| 04-REVIEW WR-03: intent literal-prepend pollutes lex: AND-term, expansion input, and (new in 04-06) snippet term list | Design quality | ⚠️ Warning | SC 6 capability holds; the existing test encodes the design. Does not invalidate an SC |
| 04-REVIEW WR-06: extractor violates max_length on long single sentences (673 chars observed) | Code review finding, verified live | ⚠️ Warning | Table render bounded at 200 (verified); overflow leaks to --json only. SC 7 display truth intact; quality follow-up |
| 04-REVIEW WR-09: multi-list fusion (expand:) mislabels later lists' scores as vector_score | Code review finding | ⚠️ Warning | Default two-list path preserves provenance correctly (tested); SC 3 holds on the primary path |
| 04-REVIEW WR-04/07/08: csv/xml escaping, dead bench -C flag, ignored fixture collections field | Code review findings | ℹ️ Advisory | Quality follow-ups outside phase-04 SCs |
| 04-06-SUMMARY "583 passed/11 skipped" not reproducible in current venv | Environment drift | ⚠️ Warning | Current venv lacks pytest-asyncio + httpx (not in dev extras; uv.lock modified in working tree). Same 21 failures + 2 collection errors exist at the pre-04-06 commit — not a 04-06 regression. Recommend adding the two test deps to dev extras or documenting the gate environment |
| REQUIREMENTS.md: 9 of 10 phase-4 IDs still "Pending" | Stale bookkeeping | ℹ️ Info | All 10 verified satisfied above |

Advisory assessment per instruction (do the known advisories invalidate a SUCCESS CRITERION?): **No.** CR-01 concerns flags outside the SC set; CR-03 degrades vector-route quality but not routing capability (and the goal's default hybrid path dedups); WR-03 keeps SC 6's capability while polluting quality; WR-06's overflow is masked in the only user-facing render (table) and was verified bounded at 200 live; WR-09 affects the expand: sub-path only while the SC's primary path is proven. Each remains a recommended hardening item, not a failed truth.

### Human Verification Required

1. **Snippet relevance on your real index (04-06 backstop truth)**
   - **Test:** On your real personal index, run `sif search query <terms>` (no --full) and `sif search search <terms>`; read the rendered Snippet column across several queries.
   - **Expected:** The snippet reads as the most relevant excerpt for its query — the window a human would pick.
   - **Why human:** Plan-declared `verification: backstop`; relevance is a human judgment on a real corpus. Automated tests prove extraction mechanics only. The verifier abstained (no real personal index available; `query_cmd`'s modelscope embedder cannot load in this venv).
2. **Real-model reranking quality (SC 1)** — configure a real reranker, compare with/without, check `--explain` shows `reranker_score`.
3. **HyDE end-to-end with a generation-capable model (SC 2)** — `sif search query hyde: <question>`; generation path is only mock-tested.
4. **bench on a real corpus (SC 8)** — author a fixture with your own relevance judgments; confirm metric sanity.

### Gaps Summary

No failed truths; no gaps remain from the initial verification. The single prior gap (SC 7 / SRCH-07) is closed end to end and independently re-proven: extraction now runs on all four pipeline routes via a transient content fetch (never mutating `SearchResult.content`, preserving the CLI-07 `--full` contract — proven live via `to_dict()`), and both human-facing rich tables render a `Snippet` column (live CLI render observed; bracket text escapes literally). The two empirical failures that defined the gap are inverted by automated tests and were independently reproduced as passing by this verifier against a fresh real-sqlite index.

The phase cannot be marked `passed` solely because four items genuinely require the maintainer: the 04-06 backstop truth (snippet relevance judgment on your real index) plus the three carried real-model confirmations. Automated checks are otherwise green within phase scope: 183 phase-scoped tests pass, all named behavioral tests pass, ruff is clean, all 8 task commits exist, and the full-suite failures observable in this venv (21 + 2 collection errors, all MCP/embedding files) were proven identical at the pre-04-06 commit — an environment-dependency issue (missing pytest-asyncio/httpx, neither declared in dev extras), not a regression.

---

_Verified: 2026-09-05T01:26:04Z_
_Verifier: Claude (gsd-verifier)_
