---
phase: 15-search-quality-configuration-hybrid-weights-query-suggestions
verified: 2026-11-08T11:14:54Z
status: human_needed
score: 30/30 must-haves verified
covered_files:
  - ".claude/skills/sif-search/SKILL.md"
  - ".planning/phases/15-search-quality-configuration-hybrid-weights-query-suggestions/15-01-PLAN.md"
  - ".planning/phases/15-search-quality-configuration-hybrid-weights-query-suggestions/15-01-SUMMARY.md"
  - ".planning/phases/15-search-quality-configuration-hybrid-weights-query-suggestions/15-02-PLAN.md"
  - ".planning/phases/15-search-quality-configuration-hybrid-weights-query-suggestions/15-02-SUMMARY.md"
  - ".planning/phases/15-search-quality-configuration-hybrid-weights-query-suggestions/15-03-PLAN.md"
  - ".planning/phases/15-search-quality-configuration-hybrid-weights-query-suggestions/15-03-SUMMARY.md"
  - "docs/api-reference.md"
  - "docs/cli-reference.md"
  - "docs/configuration.md"
  - "docs/mcp-server.md"
  - "docs/search-algorithms.md"
  - "scripts/generate_config_ref.py"
  - "src/sif/cli/commands/search.py"
  - "src/sif/cli/commands/suggest.py"
  - "src/sif/cli/main.py"
  - "src/sif/config/settings.py"
  - "src/sif/core/models.py"
  - "src/sif/database/repositories.py"
  - "src/sif/database/schema.py"
  - "src/sif/mcp/backend.py"
  - "src/sif/mcp/handlers.py"
  - "src/sif/mcp/protocol.py"
  - "src/sif/search/hybrid.py"
  - "src/sif/search/rrf.py"
  - "src/sif/search/suggest.py"
  - "tests/test_docs.py"
  - "tests/unit/cli/test_search.py"
  - "tests/unit/cli/test_suggest.py"
  - "tests/unit/config/test_settings.py"
  - "tests/unit/database/test_query_log_repo.py"
  - "tests/unit/database/test_schema.py"
  - "tests/unit/mcp/test_backend.py"
  - "tests/unit/search/test_hybrid.py"
  - "tests/unit/search/test_rrf.py"
  - "tests/unit/search/test_suggest.py"
covered_digest: "v4:sha256:9e3a6d35e176a3cf57222504d9213e1a04b7736a3aef84c3e93462cf0d3c6584"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Run `sif suggest <query>` and several zero-result searches against your real personal index; verify the did-you-mean rewrites are useful and accept the porter-stem display ('quantum machin')."
    expected: "Suggestions name the corrected query on stdout after 'No results found.'; the stem form is readable and helpful; nothing is re-executed automatically."
    why_human: "Suggestion relevance and stem-display UX are subjective and corpus-dependent (RESEARCH A1 / Open Question 1 resolved as stem display). Automated tests prove behaviour, not usefulness."
  - test: "Confirm acceptance of the locked zero-result-only trigger (CONTEXT D-05): a low-result (non-empty but weak) search does NOT show 'Did you mean'."
    expected: "The user accepts that only zero-result searches trigger suggestions; ROADMAP SC2's 'zero- or low-result' wording is intentionally narrowed by D-05. If not accepted, re-open the phase."
    why_human: "This is a product-scope decision recorded during discuss-phase, not a code defect; only the user can accept or reject the narrowing."
  - test: "Time `sif suggest <query> --json` against your real index, subtracting a `sif --help` startup baseline."
    expected: "Core work stays inside the D-14 100 ms product budget (this verification measured a 20,003-term synthetic index at 0.69-0.70 s end-to-end vs 0.69-0.70 s --help, i.e. ~0-10 ms of actual work)."
    why_human: "Latency feel and the size/shape of the user's actual vocabulary are environment-specific; the manual D-14 check is explicitly not a wall-clock test."
  - test: "Run `/gsd-secure-phase 15` and confirm the STRIDE mitigations (T-15-01..T-15-08) hold."
    expected: "Threat mitigations verified; a SECURITY.md exists for the phase."
    why_human: "No SECURITY.md was produced for this phase (security enforcement is on); per the verification context this is a follow-up, not a phase-15 failure, but it still requires the security workflow run."
  - test: "View `sif suggest <query>` (table mode) in your normal terminal width and confirm the three labeled sections and their tables render cleanly."
    expected: "Prefix completions / Did you mean / History headings appear in that fixed order with readable tables; no wrapped or broken headings."
    why_human: "Visual terminal rendering (Rich layout) is not assertable beyond CliRunner's 80-column capture."
---

# Phase 15: Search Quality Configuration (Hybrid Weights + Query Suggestions) Verification Report

**Phase Goal:** Users can tune hybrid ranking to their corpus and recover from zero-result queries with suggestions — never silent rewrites.
**Verified:** 2026-11-08T11:14:54Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

All 30 observable truths derived from the three PLAN frontmatters and the ROADMAP success criteria are verified against the codebase and independently exercised where runnable. All 12 prohibitions hold by inspection and test. Human verification remains for suggestion UX, the locked zero-result scope narrowing, real-index latency feel, terminal rendering, and the pending security-phase run.

### Observable Truths — Plan 15-01 (QUAL-01)

| #   | Truth   | Status     | Evidence       |
| --- | ------- | ---------- | -------------- |
| 1 | Unconfigured search produces byte-identical fused scores and rankings (repr equality) to pre-phase output | ✓ VERIFIED | `src/sif/search/rrf.py:55-60` uses multiply form with weight 1.0 / k=60; direct check: plain vs `weights=[1.0,1.0], k=60` produced identical `(doc_id, rank, repr(rrf_score))` tuples. Tests: `test_rrf.py::TestRRFSC1Golden`, `test_hybrid.py::TestHybridSC1PipelineGolden::test_default_options_match_prechange_snapshot` (literal pre-change snapshot). |
| 2 | `sif query --bm25-weight 5.0 --vector-weight 0.2 --rrf-k 10` visibly reorders results vs defaults on a fixture corpus | ✓ VERIFIED | Flags at `src/sif/cli/commands/search.py:753-770`; fill at `:850-852`; fusion at `hybrid.py:79-80`. Pipeline test `test_pipeline_weights_visibly_reorder_fused_ranking`: default `[d3,d2]` → bm25-heavy `[d3,d1]`; direct fuse check reordered `[b,c,a,d]` → `[a,b,c,d]`. |
| 3 | Precedence per knob: CLI flag > `SIF_` setting > default | ✓ VERIFIED | Single fill site `search.py:850-852` (`x if x is not None else settings.x`), flag defaults `None` (`:754-770`), settings load moved above the options build (`:826-853`). Tests `TestQueryFusionWeightFlags::test_flag_beats_env_setting`, `test_env_setting_reaches_options_with_real_settings`. |
| 4 | `SIF_RRF_K=10` with no flags changes `sif query` ranking (settings path reaches fusion) | ✓ VERIFIED | `settings.py:193-198` → `SearchOptions.rrf_k` (`models.py:292`) → `hybrid.py:80` (source fusion) and `:237` (variant fusion). `SIF_RRF_K=7` live-resolved to `settings.rrf_k == 7`; `test_override_k_in_fuse` and `test_pipeline_k_changes_fused_scores_per_formula` prove ranking/score change. |
| 5 | MCP request fields override server settings; absent fields fall back to the server process's `SIF_` settings | ✓ VERIFIED | `protocol.py:248-250` (`rrf_k`/`bm25_weight`/`vector_weight`, ge/gt), `backend.py:126-146` (None → `self.settings.*` into `SearchOptions`), `handlers.py:64-66` (schema) and `:83-85` (pass-through). Tests `TestHybridSearchWeightOverrides::test_request_weights_flow_into_options`, `test_absent_fields_fall_back_to_server_settings`, `test_request_field_overrides_settings`. |
| 6 | Invalid values rejected at the boundary: CLI `--rrf-k 0` / `--bm25-weight 0` fail as usage errors; `SIF_RRF_K=0` / `SIF_BM25_WEIGHT=-1` fail Pydantic naming the field | ✓ VERIFIED | `click.IntRange(1, None)` / `click.FloatRange(0, min_open=True)` (`search.py:753-770`); Pydantic `ge=1`/`gt=0` (`settings.py:193-211`, `protocol.py:248-250`). Tests `test_invalid_flag_values_rejected`, `test_rrf_k_rejects_zero_naming_the_field`, `test_negative_bm25_weight_rejected`. Live: `SIF_RRF_K=0` raised `ValidationError` containing `rrf_k`. |
| 7 | No upper bound: `SIF_VECTOR_WEIGHT=1000` accepted | ✓ VERIFIED | No `le` on the three fields (`settings.py:193-211`); live `SIF_VECTOR_WEIGHT=1000` → `vector_weight == 1000.0`; tests `test_vector_weight_has_no_upper_bound`, MCP `test_large_vector_weight_accepted`. |
| 8 | `docs/configuration.md` documents `SIF_RRF_K`, `SIF_BM25_WEIGHT`, `SIF_VECTOR_WEIGHT` after `make docs-generate` | ✓ VERIFIED | `docs/configuration.md:103-105`; registered in `scripts/generate_config_ref.py:177-188`; `make docs-generate` produced no diff (`DOCS_CLEAN`); docs gate 13 passed. |
| 9 | Existing JSON/CSV consumers see identical output shape and default-order results (backstop) | ✓ VERIFIED | Explicit evidence: golden pipeline snapshot pins default order; `_json_with_suggestions` delegates to the unchanged `format_results_json` whenever there is no zero-result suggestion (`search.py:314-320`, `:71-77`); CSV formatter unchanged; full CLI format battery passes. |

**Prohibitions (15-01):** no normalization in the default fusion path (`rrf.py:59-60` multiply form only) — VERIFIED; no upper clamp on weights — VERIFIED; no weight flags on `search_cmd`/`vsearch_cmd` (grep of both decorator blocks is clean) — VERIFIED; zero new runtime dependencies (`git diff pyproject.toml` empty) — VERIFIED.

### Observable Truths — Plan 15-02 (QUAL-02/03/04 core)

| #   | Truth   | Status     | Evidence       |
| --- | ------- | ---------- | -------------- |
| 10 | `documents_fts_v` exists after `init_schema` on a fresh DB and after the engine's lazy ensure on an old DB, enumerating real porter-stem terms | ✓ VERIFIED | DDL `schema.py:260-262`, `drop_all` `:424`; engine re-ensure `suggest.py:34-37,58-84`. Tests `test_schema.py::TestVocabShadowTable`; direct observation: a DB with `documents_fts` but no vocab gained `documents_fts_v` after `_ensure_loaded()`. |
| 11 | Prefix completions return vocab terms only, and every completion run as a BM25 query returns ≥ 1 result | ✓ VERIFIED | `suggest.py:86-106` (bisect over sorted stems, min length 2); test `test_completions_are_real_queryable_stems` asserts prefix + `BM25Searcher.search(term)` non-empty. |
| 12 | `did_you_mean` rewrites the full query per out-of-vocab word, keeps in-vocab words, and returns `[]` when every word already retrieves | ✓ VERIFIED | `suggest.py:108-207` (`_dym_slots` returns None for all-retrievable); tests `test_rewrites_full_query_per_out_of_vocab_word`, `test_no_dym_when_every_word_retrieves`, `test_uncorrectable_token_yields_no_suggestion`. Live: `quantm machin` → `quantum machin`. |
| 13 | SC2 pin: every DYM suggestion run as a real BM25 query returns ≥ 1 result (including conjunction co-occurrence) | ✓ VERIFIED | `_hits` probes with the searcher's own `_build_fts_query` (`suggest.py:140-152`); tests `test_every_suggestion_hits_as_query`, `test_cross_document_terms_drop_zero_hit_suggestions` (CR-01 regression), `test_co_occurring_rewrite_is_still_emitted`. |
| 14 | Empty/missing vocab or a query with no usable tokens yields empty suggestions; `OperationalError` degrades without crashing | ✓ VERIFIED | `suggest.py:70-84`, `124-138`, `237-248`; tests `TestVocabDegradation` (empty, missing table, read-only), `test_empty_and_metachar_only_queries_return_empty`. |
| 15 | DYM output is deterministic for a fixed vocab (sorted-term tie order) | ✓ VERIFIED | `_close_matches` re-sorts by `(ratio desc, term asc)` (`suggest.py:250-269`); tests `test_repeated_calls_are_deterministic`, `test_variant_depth_follows_close_match_order`. |
| 16 | `query_log` rows carry aware-UTC `created_at`; inserting beyond the limit trims the oldest in the same write so the table never exceeds N | ✓ VERIFIED | Schema `schema.py:149-170`; `QueryLogEntry` aware-UTC (`models.py:208-230`); `QueryLogRepository.add` INSERT + trim DELETE (`repositories.py:593-614`). Tests `test_query_log_repo.py::TestAddPersistence`, `TestTrimInWrite` (exactly keep), `TestClear`. |
| 17 | History ranking = count × exp(−ln2 × age_days / 14) from one GROUP BY aggregate; cold start leaves the section empty | ✓ VERIFIED | `QueryLogRepository.history` one GROUP BY (`repositories.py:616-627`); decay + multi-pass stable sort (`suggest.py:277-303`). Tests `test_history_ranks_frequency_times_recency`, `test_history_tie_breaks_last_used_then_lexical`, `test_history_cold_start_is_empty`. |
| 18 | `SIF_QUERY_HISTORY_ENABLED=0` makes the history read return `[]`; `SIF_QUERY_HISTORY_LIMIT` defaults 500 and is ge=1 | ✓ VERIFIED | `settings.py:215-226`; read gate `suggest.py:218-226`; tests `test_history_read_gate_disabled_returns_empty`, `test_history_settings_failure_returns_empty`, `test_query_history_defaults`, `test_query_history_limit_rejects_zero_naming_the_field`. |
| 19 | Core suggest pipeline on a ≥60k-term fixture completes inside the bound, with a deterministic bucket-usage assertion | ✓ VERIFIED | `test_bucketed_dym_under_budget_on_60k_vocab` passed (spied difflib bucket < 10% of vocab; full core under the generous wall bound). |
| 20 | `docs/configuration.md` documents `SIF_QUERY_HISTORY_ENABLED` and `SIF_QUERY_HISTORY_LIMIT` after regen | ✓ VERIFIED | `docs/configuration.md:106-107`; generator registration `scripts/generate_config_ref.py:184-185`; regen diff clean; docs gate 13 passed. |

**Prohibitions (15-02):** no LLM/network call in DYM (imports are `bisect/difflib/math/sqlite3/datetime` only) — VERIFIED; vocab terms never hand-interpolated into MATCH (both probe paths call `BM25Searcher._build_fts_query`, `suggest.py:152,166`) — VERIFIED; `query_log` stores query/result_count/collections/created_at only (`schema.py:159-165`) — VERIFIED; zero new runtime dependencies — VERIFIED.

### Observable Truths — Plan 15-03 (QUAL-02/03/04 hosts)

| #   | Truth   | Status     | Evidence       |
| --- | ------- | ---------- | -------------- |
| 21 | `sif suggest QUERY` prints three labeled sections — prefix completions, did you mean, history — in that fixed order, each independently top-N | ✓ VERIFIED | `suggest.py:40` titles + `:180-182` render order; test `test_table_shows_three_labeled_sections_in_fixed_order`; live run printed all three headings in order. |
| 22 | `sif suggest QUERY --json` emits exactly three keys — completions, did_you_mean, history — each an array; no CSV/MD/XML formats exist | ✓ VERIFIED | `suggest.py:164-175`; no `--csv/--md/--xml` options; tests `test_json_has_exactly_three_arrays`, `test_json_did_you_mean_carries_the_rewritten_query`; live output keys exactly the three arrays. |
| 23 | `sif suggest --clear-history` deletes all rows, prints confirmation after commit, and is mutually exclusive with QUERY | ✓ VERIFIED | `suggest.py:71-87` (clear in transaction, print after), `:82-87` (UsageError), `:155-160`; tests `TestClearHistory`; live: "Cleared 3 query history row(s)." then 0 rows; `--clear-history "q"` raises UsageError (test). |
| 24 | Zero-result table mode on search/vsearch/query shows a "Did you mean" line after "No results found." (respecting `-q`); CSV/MD/XML/files modes put suggestions on stderr only | ✓ VERIFIED | Helpers `search.py:289-305`; wired at `:491-546`, `:683-706`, `:925-979`. Tests `TestZeroResultSuggestions` incl. machine-mode purity and quiet gating. Live: table printed "Did you mean: quantum machin?" after "No results found."; `--csv` stdout contained only the CSV header/rows with the line on stderr. |
| 25 | Zero-result `--json` emits `{"query","results": [],"suggestions"}` when suggestions exist, and plain `[]` when none | ✓ VERIFIED | `_json_with_suggestions` (`search.py:307-320`). Test `test_zero_result_json_wraps_suggestions_or_keeps_plain_array` (both shapes); live object output matched exactly. |
| 26 | Every executed CLI search writes one `query_log` row (query, result count, collections); `SIF_QUERY_HISTORY_ENABLED=0` writes nothing; suggest and MCP query never write | ✓ VERIFIED | `_record_query_history` (`search.py:255-286`) called inside the connection block at `:493`, `:685`, `:927`. Tests `TestQueryHistoryWrite` (all three commands; disabled; quiet still logs), `test_mcp_query_never_writes_query_log`, suggest test asserting count unchanged; live: one row after a search, no row after `SIF_QUERY_HISTORY_ENABLED=0`. |
| 27 | A `query_log` or suggestion-engine failure never fails a search command (fail-soft + logger.warning, exit 0) | ✓ VERIFIED | Both hooks wrap in `try/except Exception` (`search.py:248-252`, `:270-286`); tests `test_history_write_failure_never_fails_search`, `test_suggestion_failure_never_fails_zero_result_search`, MCP `test_engine_failure_degrades_to_empty_suggestions`. |
| 28 | MCP query responses carry a suggestions list on zero results; MCP never writes `query_log` | ✓ VERIFIED | `QueryOutput.suggestions` (`protocol.py:253-260`); `HybridSearchResults` + `_with_suggestions` (`backend.py:29-70`, zero-result paths `:153`, `:184`); handler remap (`handlers.py:87-95`). Tests `TestZeroResultSuggestions` (carry, empty when results exist, explicit remap) and `test_mcp_query_never_writes_query_log`. |
| 29 | Cold start history section is empty; no-index guard prints a "No index found." style notice and exits cleanly for all suggest modes | ✓ VERIFIED | Guard `suggest.py:145-153` (JSON: parseable empty three-array doc; table: notice; `-q` suppresses); tests `test_cold_start_history_section_is_empty_not_an_error`, `TestGuardsAndQuiet`; live: notice printed, no DB materialized for table mode, empty JSON document for `--json`. |
| 30 | 100 ms product budget sanity (manual, D-14) stays near the engine's measured cost minus a `--help` startup baseline | ✓ VERIFIED | Independent measurement on a 20,003-term synthetic index: `sif suggest ... --json` 0.69-0.70 s vs `sif --help` 0.69-0.70 s (delta ≤ ~10 ms), consistent with the SUMMARY's 11.4 ms; `test_bucketed_dym_under_budget_on_60k_vocab` bounds the core deterministically. |

**Prohibitions (15-03):** queries never silently rewritten (`did_you_mean` appears only in display paths: `search.py:249`, `mcp/backend.py:66`) — VERIFIED; MCP never writes `query_log` — VERIFIED; suggest output is table + `--json` only — VERIFIED; `query_log` stores no document content — VERIFIED.

**Score:** 30/30 truths verified (0 present, behavior-unverified)

### Deferred Items

None — no gap was identified.

### Advisory (New Scope, Unevidenced)

None — initial verification (the Step 7 advisory gate applies only to re-verification).

### Required Artifacts

| Artifact | Expected    | Status | Details |
| -------- | ----------- | ------ | ------- |
| `src/sif/core/models.py` | `SearchOptions.rrf_k/bm25_weight/vector_weight` defaults 60/1.0/1.0; `QueryLogEntry` aware-UTC | ✓ VERIFIED | Fields at `:292-294`; entry at `:208-230`. |
| `src/sif/search/rrf.py` | `fuse(..., weights, k)` multiply form; `fuse_with_weights` removed | ✓ VERIFIED | `:20-109`; no `fuse_with_weights` anywhere in src/tests/docs. |
| `src/sif/search/hybrid.py` | weights at source fusion, k at both fuse sites | ✓ VERIFIED | `:79-80`, `:237`. |
| `src/sif/config/settings.py` | `rrf_k(ge=1)`, `bm25_weight(gt=0)`, `vector_weight(gt=0)`; history settings | ✓ VERIFIED | `:193-226`, no upper bound. |
| `src/sif/cli/commands/search.py` | query-only weight flags; zero-result DYM hooks; history writes | ✓ VERIFIED | Flags `:753-770`; hooks `:238-320`, call sites `:491-546`, `:683-706`, `:925-979`. |
| `src/sif/mcp/protocol.py` | `QueryInput` weight fields; `QueryOutput.suggestions` | ✓ VERIFIED | `:238-260`. |
| `src/sif/mcp/backend.py` | settings fallback; suggestions boundary remap | ✓ VERIFIED | `:29-70`, `:118-184`. |
| `src/sif/mcp/handlers.py` | schema weight properties; explicit suggestions remap | ✓ VERIFIED | `:56-66`, `:83-95`. |
| `src/sif/search/suggest.py` | `SuggestionEngine`: lazy vocab, prefix, DYM, history | ✓ VERIFIED | `:48-303`; real index probes for retrievability and SC2. |
| `src/sif/database/schema.py` | `documents_fts_v`, `query_log` + index, drop_all entries | ✓ VERIFIED | `:149-170`, `:260-262`, `:419-436`. |
| `src/sif/database/repositories.py` | `QueryLogRepository.add/history/clear` | ✓ VERIFIED | `:579-632`, parameterized, trim-in-write. |
| `src/sif/cli/commands/suggest.py` | `suggest_cmd` three sections, JSON, clear, guard | ✓ VERIFIED | `:116-183`. |
| `src/sif/cli/main.py` | `add_command(suggest_cmd)` | ✓ VERIFIED | `:94`, `:112`. |
| `scripts/generate_config_ref.py` | Search Settings registration | ✓ VERIFIED | `:177-188`. |
| `docs/configuration.md`, `docs/cli-reference.md` | generated docs current | ✓ VERIFIED | Env spellings at `configuration.md:103-107`; `sif suggest` at `cli-reference.md:660`; regen diff clean. |
| `.claude/skills/sif-search/SKILL.md` | both zero-result JSON shapes | ✓ VERIFIED | `:73-77`. |
| Test batteries | requirement-linked tests | ✓ VERIFIED | `test_rrf.py`, `test_hybrid.py`, `test_suggest.py`, `test_query_log_repo.py`, `test_schema.py`, `test_settings.py`, `test_search.py`, `test_suggest.py` (CLI), `test_backend.py`, `test_docs.py`. |

### Key Link Verification

| From | To  | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `search.py` `query_cmd` | `SearchOptions` | flag > settings > default fill | ✓ WIRED | `:850-852`; flags default `None` at `:754-770`. |
| `hybrid.py` | `rrf.py` | weights/k into `fuse` | ✓ WIRED | `:79-80` (`weights=[options.bm25_weight, options.vector_weight]`, `k=options.rrf_k`). |
| `mcp/backend.py` | `SearchOptions` | None → `self.settings.*` | ✓ WIRED | `:143-146`. |
| `schema.py` `_create_fts_tables` | `suggest.py` `_load` | `fts5vocab(documents_fts,'row')` + `SELECT term, doc` | ✓ WIRED | `schema.py:260-262`, `suggest.py:62-68`; lazy re-ensure `suggest.py:58-60`. |
| `suggest.py` `did_you_mean` | `bm25.py` matching semantics | tokenization + `_build_fts_query` probe | ✓ WIRED | `_FTS_METACHARS` import `:25`, probe `:152,166`. |
| `repositories.py` `add` | `query_log` | INSERT + trim DELETE | ✓ WIRED | `:593-614`. |
| `search.py` zero-result sites | `SuggestionEngine.did_you_mean` | engine on open connection before early return | ✓ WIRED | `:491`, `:683`, `:925`. |
| `search.py` post-results | `QueryLogRepository.add` | fail-soft gated write | ✓ WIRED | `:493`, `:685`, `:927`. |
| `cli/commands/suggest.py` | `SuggestionEngine` | three section reads | ✓ WIRED | `:101-113`, `:162-182`. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `sif suggest` sections | `completions`, `did_you_mean`, `history` | `documents_fts_v` + `query_log` via `QueryLogRepository.history` | Yes — live run returned real stems and a real logged query | ✓ FLOWING |
| Zero-result DYM (CLI) | `suggestions` | `SuggestionEngine.did_you_mean` over the live FTS index (real MATCH probe) | Yes — live `quantm machin` → `quantum machin` | ✓ FLOWING |
| History ranking | aggregated `(query, count, last_used)` | `query_log` written by executed searches | Yes — live logged query appeared in the history section | ✓ FLOWING |
| Weighted fusion | `status`, `options.*`, `rrf_score` | `SearchOptions` from flags/settings/request | Yes — direct fuse and pipeline checks reordered scores | ✓ FLOWING |
| MCP suggestions | `QueryOutput.suggestions` | `HybridSearchResults.suggestions` from engine | Yes — tests assert `["quantum machin"]` from the real vocab fixture | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Byte-identical default fusion | direct Python: `fuse(...)` vs `fuse(..., weights=[1.0,1.0], k=60)` | identical `(doc_id, rank, repr(rrf_score))` tuples | ✓ PASS |
| Weighted fusion reorders | direct Python: `weights=[5.0,0.2]` | order changed `[b,c,a,d]` → `[a,b,c,d]`; k=1 top score 0.8333… | ✓ PASS |
| `sif suggest --json` shape | `python -m sif.cli.main -i <tmp>.db suggest quant --json` | `{"completions":["quantum","quantifi"],"did_you_mean":[],"history":[]}` | ✓ PASS |
| Table mode three sections | `... suggest "quantum"` | Prefix completions / Did you mean / History in order | ✓ PASS |
| Zero-result table DYM | `... search search "quantm machin"` | `No results found.` then `Did you mean: quantum machin?` | ✓ PASS |
| Zero-result conditional JSON | `... search search "quantm machin" --json` | `{"query":..., "results": [], "suggestions": ["quantum machin"]}` | ✓ PASS |
| CSV stdout purity | `... search search "quantm machin" --csv` | stdout only CSV header/rows; DYM line on stderr | ✓ PASS |
| History write + opt-out | search, then `SIF_QUERY_HISTORY_ENABLED=0` search, count rows | one row per enabled search; unchanged under opt-out (3 rows) | ✓ PASS |
| History suggestions | `... suggest "" --json` after logged searches | `history: ["quantm machin"]` | ✓ PASS |
| Clear history | `... suggest --clear-history` | `Cleared 3 query history row(s).`; rows 0 | ✓ PASS |
| Missing index | `... suggest quant` / `... suggest quant --json` | `No index found.` with no DB created / parseable empty three-array doc | ✓ PASS |
| Latency budget | 20,003-term index: suggest vs `--help`, 3 runs each | 0.69-0.70 s vs 0.69-0.70 s (delta ≤ ~10 ms) | ✓ PASS |
| Lazy vocab ensure | Python: old-schema conn + `_ensure_loaded()` | `documents_fts_v` created | ✓ PASS |

### Probe Execution

N/A — the phase declares no probe scripts and none exist under `scripts/*/tests/probe-*.sh` (not a migration/tooling phase).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| QUAL-01 | 15-01 | `rrf_k`/`bm25_weight`/`vector_weight` configurable via `SIF_` settings + per-query params; default behavior byte-identical (k=60 equal weights) | ✓ SATISFIED | Truths 1-9; golden tests, CLI/MCP tests, live settings checks. |
| QUAL-02 | 15-02, 15-03 | Zero-result "Did you mean" suggestions (vocab + history, suggestions only, never silent rewrites) | ✓ SATISFIED | Truths 10-13, 21-25, 27-28; SC2 pin incl. conjunction probe; live CLI/MCP paths. History participates via `sif suggest` (QUAL-03). |
| QUAL-03 | 15-02, 15-03 | Suggestions based on query history (local `query_log` storage) | ✓ SATISFIED | Truths 16-18, 26; storage/trim/opt-out/clear and frequency×recency ranking verified; live history read. |
| QUAL-04 | 15-02, 15-03 | `sif suggest` command (prefix completions + DYM + history) | ✓ SATISFIED | Truths 21-23, 29-30; three-section table/JSON, clear, guard, latency. |

No orphaned requirements: the REQUIREMENTS.md Phase 15 mapping contains only QUAL-01..04, and every plan-declared ID is covered.

### Decision Coverage

All trackable CONTEXT.md decisions are honored by shipped artifacts — 14/14 honored, none missing (`gsd_run query check.decision-coverage-verify`).

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| `tests/unit/search/test_rrf.py` | QUAL-01 | Yes | 0 | No (literal golden; pre-change capture documented) | Value/behavioral | PASS |
| `tests/unit/search/test_hybrid.py` | QUAL-01 | Yes | 1 env-conditional (`sqlite-vec not available`) | No | Behavioral (pipeline snapshot + reorder) | PASS |
| `tests/unit/search/test_suggest.py` | QUAL-02/03/04 | Yes | 0 | No | Behavioral (real searcher re-query) | PASS |
| `tests/unit/database/test_query_log_repo.py` | QUAL-03 | Yes | 0 | No | Value (real SQL) | PASS |
| `tests/unit/database/test_schema.py` | QUAL-02 | Yes | 0 | No | Value/behavioral | PASS |
| `tests/unit/config/test_settings.py` | QUAL-01/03 | Yes | 0 | No | Value | PASS |
| `tests/unit/cli/test_suggest.py` | QUAL-04 | Yes | 0 | No | Behavioral (CliRunner on real DB) | PASS |
| `tests/unit/cli/test_search.py` | QUAL-01/02/03 | Yes | 0 | No | Behavioral | PASS |
| `tests/unit/mcp/test_backend.py` | QUAL-01/02 | Yes | 0 | No | Behavioral | PASS |

**Disabled tests on requirements:** 0 (the single `pytest.skip` is an environment-availability guard for the sqlite-vec fixture; the fuse-level golden still runs without it).
**Circular patterns detected:** 0. The pipeline golden snapshot is a literal captured from the pre-change code — the intended compatibility oracle for SC1, not a runtime-generated expectation.
**Insufficient assertions:** 0.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | `TBD`/`FIXME`/`XXX`/`TODO`/`HACK` in phase-modified source | — | None found (debt-marker gate clean). |
| — | — | Placeholder/coming-soon/not-implemented strings | — | None found; "Reranker not available" is a legitimate runtime error message. |
| `src/sif/search/suggest.py` / `search.py` / `mcp/backend.py` | — | Debug-only or empty implementations | — | None; empty returns are documented degradation paths, not stubs. |

Open INFO findings from the code review remain recorded in `15-REVIEW-DISPOSITION.md` (7 open: IN-01..IN-07). The three relevant to future work are: IN-02 (`sif bench` does not read the new global fusion settings — Phase 16 sweep relevance), IN-05 (multi-word queries make prefix completions effectively empty), and IN-06 (`sif suggest` lets DB/config failures escape as tracebacks; `--clear-history` prints under `-q`). None maps to a phase-15 must-have; all are Info-level and were dispositioned as open at review time.

### Human Verification Required

#### 1. Suggestion quality on a real personal KB

**Test:** Run `sif suggest <query>` and several intentionally-zero-result `sif search` queries against the real index; review the did-you-mean rewrites and the porter-stem display.
**Expected:** Suggestions name the corrected query after "No results found.", are useful, and the stem form ("quantum machin") is acceptable. Confirm the documented trade-offs: index-global suggestions under `--collection` filters, CJK run-level completions, deterministic tie order.
**Why human:** Relevance/UX and corpus-specific vocabulary are subjective; automated tests prove behavior, not usefulness (RESEARCH A1 / Open Question 1 resolved as stem display).

#### 2. Accept the locked zero-result-only trigger (CONTEXT D-05)

**Test:** Confirm that a low-result (non-empty but weak) search intentionally shows no "Did you mean" line.
**Expected:** The user accepts the narrowing of ROADMAP SC2's "zero- or low-result" wording to the zero-result case per D-05. If not accepted, re-open the phase.
**Why human:** A product-scope decision, not a code defect.

#### 3. Perceived latency on the real index

**Test:** Time `sif suggest <query> --json` against the real index, subtracting a `sif --help` baseline.
**Expected:** Core work stays inside the D-14 100 ms budget. (This verification measured 0.69-0.70 s vs 0.69-0.70 s on a 20,003-term synthetic index — ≤ ~10 ms of actual work.)
**Why human:** The user's corpus size/shape and machine latency are environment-specific; D-14 is explicitly a manual measure, not a wall-clock test.

#### 4. Security phase follow-up

**Test:** Run `/gsd-secure-phase 15`.
**Expected:** A SECURITY.md exists and the STRIDE mitigations (T-15-01..T-15-08) are verified.
**Why human:** No SECURITY.md was produced for this phase; per the verification context this is a follow-up, not a phase-15 failure.

#### 5. Terminal rendering

**Test:** View `sif suggest <query>` (table mode) at your normal terminal width.
**Expected:** The three labeled sections render in fixed order with readable tables and no wrapped/broken headings.
**Why human:** Rich visual layout cannot be fully asserted beyond the 80-column CliRunner capture.

### Gaps Summary

No gaps. Every must-have truth, artifact, key link, and prohibition resolves VERIFIED. The phase goal is achieved in the codebase: fusion weights/k resolve from flags/settings/MCP requests with byte-identical defaults, and zero-result recovery — vocabulary did-you-mean (with an index-conjunction SC2 probe), `sif suggest` prefix/DYM/history sections, fail-soft `query_log` history with opt-out and clear, stdout-pure CLI modes and MCP suggestions — works in live runs and in the full suite (1340 passed, 1 skipped, 94.82% coverage; ruff/format/ty/docs gates green). Remaining items are human acceptance and the pending security-phase run, so the status is `human_needed`.

---

_Verified: 2026-11-08T11:14:54Z_
_Verifier: Claude (gsd-verifier)_
