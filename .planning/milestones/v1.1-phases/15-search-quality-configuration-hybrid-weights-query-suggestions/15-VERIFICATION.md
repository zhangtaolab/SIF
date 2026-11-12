---
phase: 15-search-quality-configuration-hybrid-weights-query-suggestions
verified: 2026-11-12T07:47:46Z
status: passed
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
  - "src/sif/cli/error_handling.py"
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
covered_digest: "v4:sha256:981a287a257ba4f972677e8a6bd6a83b35129ec3147a57ba43ec20f78c63e984"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 30/30
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 15: Search Quality Configuration (Hybrid Weights + Query Suggestions) Verification Report

**Phase Goal:** Users can tune hybrid ranking to their corpus and recover from zero-result queries with suggestions — never silent rewrites.
**Verified:** 2026-11-12T07:47:46Z at HEAD `b47f55f6c551aa61ddd124913f6fe9a2663da06a`
**Status:** passed
**Re-verification:** Yes — stale-input refresh after Phases 16/16.1 and the Phase 11 WR-01 cache-expiry fix

## Goal Achievement

All 30 observable truths from the three PLAN frontmatters and the ROADMAP success criteria remain verified at HEAD. Independent focused regression: **378 passed, 0 skipped** across the RRF, hybrid, suggestion engine, CLI, MCP, query-log, schema, and settings batteries. Direct checks confirmed repr-exact default fusion, weighted reordering, and 66k-term suggestion-core latency of **26.806 / 29.054 / 31.878 ms**. The prior human UAT is complete (5/5 passed), and `15-SECURITY.md` is verified with zero open threats, so no human-verification items remain.

### Observable Truths — Plan 15-01 (QUAL-01)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Unconfigured search produces byte-identical fused scores and rankings (`repr` equality) to pre-phase output | ✓ VERIFIED | `src/sif/search/rrf.py:42-60` keeps multiply form, weight 1.0, and k=60. Direct check produced identical `(doc_id, rank, repr(rrf_score))` tuples for plain and explicit-default fusion. `test_rrf.py::TestRRFSC1Golden` and the literal pre-change pipeline snapshot in `test_hybrid.py::TestHybridSC1PipelineGolden` passed. |
| 2 | `sif query --bm25-weight 5.0 --vector-weight 0.2 --rrf-k 10` visibly reorders results vs defaults | ✓ VERIFIED | Query flags are declared at `src/sif/cli/commands/search.py:765-782`, resolved at `:858-869`, and consumed at `src/sif/search/hybrid.py:77-82`. Direct fusion changed order from `[a,c,d,b]` to `[a,b,c,d]`; pipeline test `test_pipeline_weights_visibly_reorder_fused_ranking` changes `[d3,d2]` to `[d3,d1]`. |
| 3 | Precedence per knob: CLI flag > `SIF_` setting > default | ✓ VERIFIED | Flag defaults are `None`; the single options-build site uses `x if x is not None else settings.x` (`search.py:858-869`). `TestQueryFusionWeightFlags` verifies explicit values, settings fallback, real-env resolution, and flag-over-env behavior. |
| 4 | `SIF_RRF_K=10` with no flags changes `sif query` ranking | ✓ VERIFIED | `Settings.rrf_k` at `src/sif/config/settings.py:228-233` reaches `SearchOptions` at `search.py:866`, then both fusion sites at `hybrid.py:81` and `:255`. Real-settings CLI test and `test_pipeline_k_changes_fused_scores_per_formula` passed. |
| 5 | MCP request fields override server settings; absent fields fall back to process settings | ✓ VERIFIED | Optional validated fields at `src/sif/mcp/protocol.py:248-250`; fallback into options at `src/sif/mcp/backend.py:145-155`; handler pass-through at `src/sif/mcp/handlers.py:77-86`. `TestHybridSearchWeightOverrides` passed all three override/fallback tests. |
| 6 | Invalid values are rejected at CLI/settings/MCP boundaries and name the field | ✓ VERIFIED | Click `IntRange(1, None)` / `FloatRange(0, min_open=True)` at `search.py:765-782`; Pydantic `ge=1` / `gt=0` at `settings.py:228-245` and `protocol.py:248-250`. CLI, settings, and `TestQueryInputWeightValidation` tests passed. |
| 7 | No upper bound: `SIF_VECTOR_WEIGHT=1000` is accepted | ✓ VERIFIED | No upper constraint exists on the three Settings fields. `test_vector_weight_has_no_upper_bound` and MCP `test_large_vector_weight_accepted` passed. |
| 8 | Generated configuration docs contain all three fusion environment variables | ✓ VERIFIED | `docs/configuration.md:106-108` documents `SIF_RRF_K`, `SIF_BM25_WEIGHT`, and `SIF_VECTOR_WEIGHT`; generator registration remains in `scripts/generate_config_ref.py`. The HEAD quality gate includes the docs tests. |
| 9 | Existing JSON/CSV consumers see identical output shape and default-order results (backstop) | ✓ VERIFIED | Explicit behavioral evidence: default golden snapshots pass, `_json_with_suggestions` delegates to unchanged `format_results_json` unless a zero-result suggestion exists (`search.py:308-321`), CSV formatting remains at `:324-346`, and the complete CLI format battery passed. |

**Prohibitions (15-01):** no normalization in default fusion (`rrf.py:55-60`) — VERIFIED; no upper clamp — VERIFIED; no weight flags on `search_cmd`/`vsearch_cmd`, including negative CLI tests — VERIFIED; zero Phase 15 runtime dependencies (`git diff a1c801c^..b90c568 -- pyproject.toml` empty) — VERIFIED.

### Observable Truths — Plan 15-02 (QUAL-02/03/04 core)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 10 | `documents_fts_v` exists on fresh and lazily opened old DBs and enumerates real porter stems | ✓ VERIFIED | DDL at `src/sif/database/schema.py:256-262`, lazy ensure/load at `src/sif/search/suggest.py:58-84`; `TestVocabShadowTable` and the real-production-DDL engine fixtures passed. |
| 11 | Prefix completions return vocab terms only, and every completion returns at least one BM25 hit | ✓ VERIFIED | Bisect vocabulary scan at `suggest.py:86-106`; `test_completions_are_real_queryable_stems` re-runs every completion through `BM25Searcher` and asserts a non-empty result. |
| 12 | DYM rewrites the full query per out-of-vocab word, keeps retrievable words, and returns `[]` when all retrieve | ✓ VERIFIED | Slot planning and full-variant expansion at `suggest.py:108-122,168-207`; `test_rewrites_full_query_per_out_of_vocab_word`, `test_no_dym_when_every_word_retrieves`, and uncorrectable-token tests passed. |
| 13 | Every DYM suggestion run as a real BM25 query returns at least one hit, including conjunction co-occurrence | ✓ VERIFIED | `_hits` probes using the searcher's own `_build_fts_query` (`suggest.py:140-152`); `test_every_suggestion_hits_as_query`, cross-document rejection, and co-occurrence acceptance tests passed. |
| 14 | Empty/missing vocab, unusable tokens, and `OperationalError` degrade to empty suggestions | ✓ VERIFIED | Guards and fail-soft handling at `suggest.py:70-84,124-138,168-188`; `TestVocabDegradation` and `test_empty_and_metachar_only_queries_return_empty` passed. |
| 15 | DYM is deterministic for a fixed vocabulary, including equal-ratio ties | ✓ VERIFIED | Matches are explicitly re-sorted by ratio descending then term ascending (`suggest.py:250-269`); repeated-call and variant-order tests passed. |
| 16 | `query_log` uses aware-UTC timestamps and trim-in-write keeps exactly N rows | ✓ VERIFIED | Schema at `schema.py:149-170`; `QueryLogEntry` at `src/sif/core/models.py:207-230`; INSERT + parameterized trim DELETE at `src/sif/database/repositories.py:659-680`. Real-SQL persistence and exact-trim tests passed. |
| 17 | History ranking is count × exp(−ln2 × age_days / 14) from one GROUP BY; cold start is empty | ✓ VERIFIED | Aggregate at `repositories.py:682-693`; decay and stable tie-breaks at `suggest.py:277-303`. Frequency/recency, tie, and cold-start tests passed. |
| 18 | History opt-out returns `[]`; limit defaults to 500 and is adjustable with ge=1 | ✓ VERIFIED | Settings at `settings.py:246-261`; read gate at `suggest.py:209-235`. Disabled-read, settings-failure, defaults, and validation tests passed. |
| 19 | Core suggestion pipeline on a ≥60k-term fixture meets the performance budget with bounded candidate buckets | ✓ VERIFIED | `test_bucketed_dym_under_budget_on_60k_vocab` passed with its <10% bucket assertion. Independent direct runs over 66,000 terms completed prefix + DYM in **26.806, 29.054, and 31.878 ms**, inside 100 ms. |
| 20 | Generated docs contain `SIF_QUERY_HISTORY_ENABLED` and `SIF_QUERY_HISTORY_LIMIT` | ✓ VERIFIED | Present at `docs/configuration.md:109-110`; settings and generator registrations remain present, with docs tests included in the HEAD gate. |

**Prohibitions (15-02):** DYM imports only stdlib/local modules, with no LLM/network path — VERIFIED; terms re-enter MATCH only through `BM25Searcher._build_fts_query` (`suggest.py:152,166`) — VERIFIED; `query_log` contains only metadata columns — VERIFIED; zero new runtime dependencies — VERIFIED.

### Observable Truths — Plan 15-03 (QUAL-02/03/04 hosts)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 21 | `sif suggest QUERY` prints prefix completions, did you mean, and history in fixed order, independently top-N | ✓ VERIFIED | Titles at `src/sif/cli/commands/suggest.py:41`; collection at `:103-109`; rendering at `:181-183`. Fixed-order, independent-limit, and real-DB CLI tests passed. |
| 22 | `sif suggest --json` has exactly three arrays and no CSV/MD/XML modes | ✓ VERIFIED | JSON object at `suggest.py:165-175`; only limit/JSON/quiet/clear options at `:117-129`. Exact-key and DYM-payload tests passed. |
| 23 | `--clear-history` deletes all rows, confirms after commit, and is mutually exclusive with QUERY | ✓ VERIFIED | `_clear_history` at `suggest.py:72-81`, validation at `:84-89`, dispatch at `:156-158`; `TestClearHistory` passed against real rows. |
| 24 | Zero-result table output shows DYM after no-results; machine modes keep suggestions off stdout | ✓ VERIFIED | Shared helpers at `search.py:239-321`; call sites at `:486-543`, `:674-707`, and `:935-1010`. All-three-command, CSV/MD/XML/files purity, and quiet tests passed. |
| 25 | Zero-result JSON conditionally wraps suggestions and otherwise remains plain `[]` | ✓ VERIFIED | `_json_with_suggestions` at `search.py:308-321`; `test_zero_result_json_wraps_suggestions_or_keeps_plain_array` passed both shapes. |
| 26 | Every executed CLI search logs one row; opt-out writes none; suggest and MCP never write | ✓ VERIFIED | Fail-soft writer at `search.py:256-287`, called at `:492`, `:687`, and `:959`; CLI all-command/disabled/quiet tests and MCP no-write test passed. Suggest count-preservation test passed. |
| 27 | Query-log or suggestion failure never fails a search | ✓ VERIFIED | Exception boundaries at `search.py:249-253` and `:271-287`; raising-repository and raising-engine tests exit 0. MCP engine-failure degradation also passed. |
| 28 | MCP zero-result responses carry suggestions and never write `query_log` | ✓ VERIFIED | `QueryOutput.suggestions` at `protocol.py:253-260`; engine attach at `backend.py:53-71,202-204`; explicit handler remap at `handlers.py:87-94`. Backend and serialized-output tests passed. |
| 29 | Cold-start history is empty; no-index suggest modes exit cleanly | ✓ VERIFIED | Missing-index guard at `suggest.py:146-154`; empty-history and table/JSON/quiet guard tests passed without materializing a DB. |
| 30 | `sif suggest` stays within the 100 ms core-work budget | ✓ VERIFIED | Independent 66k-term core runs measured 26.806–31.878 ms. Existing UAT measured suggest-vs-startup at −5.3 ms median delta on a 1,206-document corpus; the deterministic 60k-term budget test passed at HEAD. |

**Prohibitions (15-03):** suggestions are display-only and no host re-executes them — VERIFIED; MCP never writes query history — VERIFIED; suggest supports table + JSON only — VERIFIED; no document content enters `query_log` — VERIFIED.

**Score:** 30/30 truths verified (0 present, behavior-unverified)

### Deferred Items

None — no gap was identified, and no item required deferral to a later phase.

### Advisory (New Scope, Unevidenced)

None. The re-verification anti-pattern scan found no new blocker, warning, or unevidenced concern. The `placeholders` match in `LLMCacheRepository.clear_expired` is a local SQL-bind variable in the WR-01 fix, not a stub or placeholder implementation.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/sif/core/models.py` | Fusion defaults 60/1.0/1.0; aware-UTC query-log model | ✓ VERIFIED | Fields at `:207-230,271-294`; imported and exercised by CLI, MCP, engine, and repositories. |
| `src/sif/search/rrf.py` | Multiply-form weighted `fuse(weights, k)` | ✓ VERIFIED | `:20-109`; no `fuse_with_weights` remains in source/tests/docs. |
| `src/sif/search/hybrid.py` | Weights at source fusion, k at both fusion sites | ✓ VERIFIED | `:77-82,252-255`; golden and reorder behavior passed. |
| `src/sif/config/settings.py` | Validated fusion and history settings | ✓ VERIFIED | `:223-261`; real-env and validation tests passed. |
| `src/sif/cli/commands/search.py` | Query-only weight flags; zero-result DYM and history hooks | ✓ VERIFIED | Flags `:765-782`; options `:858-869`; hooks `:239-321,486-492,674-687,935-959`. |
| `src/sif/mcp/protocol.py` | Optional request weights and response suggestions | ✓ VERIFIED | `:238-260`; handler/backend tests passed. |
| `src/sif/mcp/backend.py` | Settings fallback and zero-result suggestions | ✓ VERIFIED | `:53-71,120-206`; real DB and handler serialization covered. |
| `src/sif/mcp/handlers.py` | Discoverable weight properties; explicit suggestions remap | ✓ VERIFIED | `:53-69,71-102`. |
| `src/sif/search/suggest.py` | Lazy vocab, prefix, DYM, history | ✓ VERIFIED | `:48-303`; real FTS probes and real SQL; direct 66k-term run. |
| `src/sif/database/schema.py` | `documents_fts_v`, `query_log`, index, drop entries | ✓ VERIFIED | `:149-170,256-262,422-438`; schema tests passed. |
| `src/sif/database/repositories.py` | `QueryLogRepository.add/history/clear` | ✓ VERIFIED | `:645-698`; every line blames to Phase 15 commit `04d0d93a`; no later QueryLog change. |
| `src/sif/cli/commands/suggest.py` | Three sections, JSON, clear, missing-index guard | ✓ VERIFIED | `:41-183`; 15 CLI tests passed, including new error-boundary preservation tests. |
| `src/sif/cli/error_handling.py` | Phase 16.1 opener adoption without behavior drift | ✓ VERIFIED | `:31-66` performs the same construction + `init_schema()` pair and context-managed lifetime; only foreseeable open/schema errors become ClickException. |
| `src/sif/cli/main.py` | `suggest_cmd` registration | ✓ VERIFIED | Import and `cli.add_command(suggest_cmd)` at `:105`. |
| `scripts/generate_config_ref.py` + generated docs | Current fusion/history settings and suggest CLI docs | ✓ VERIFIED | `docs/configuration.md:106-110`; `docs/cli-reference.md:440-442,670`; HEAD docs gate green. |
| `.claude/skills/sif-search/SKILL.md` | Both zero-result JSON shapes, no silent rerun | ✓ VERIFIED | `:69-76`. |
| Requirement-linked test batteries | RRF, hybrid, engine, repo, schema, settings, CLI, MCP | ✓ VERIFIED | **378 passed, 0 skipped** in the independent focused run. |

Automated artifact query result: **23/23 declared artifact entries passed** across all three plans (duplicate paths counted per declaration).

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `search.py query_cmd` | `SearchOptions` | flag > settings > default fill | ✓ WIRED | `search.py:858-869`; CLI tests inspect the options actually passed to the pipeline. |
| `hybrid.py` | `rrf.py` | weights/k into `fuse` | ✓ WIRED | `hybrid.py:77-82`; direct parity and weighted reorder checks. |
| `mcp/backend.py` | `SearchOptions` | None → `self.settings.*` | ✓ WIRED | `backend.py:145-155`; MCP override/fallback tests. |
| `schema.py` FTS setup | `suggest.py` loader | `fts5vocab(documents_fts,'row')` + `SELECT term, doc` | ✓ WIRED | `schema.py:256-262`, `suggest.py:58-76`; fresh and lazy paths tested. |
| `suggest.py` DYM | `bm25.py` matching semantics | sanitizer-built MATCH probes | ✓ WIRED | `suggest.py:140-166`; SC2 and co-occurrence tests. |
| `QueryLogRepository.add` | `query_log` | parameterized INSERT + trim DELETE | ✓ WIRED | `repositories.py:659-680`; real-SQL exact-cap test. |
| Search zero-result paths | `SuggestionEngine.did_you_mean` | already-open connection before early return | ✓ WIRED | `search.py:490,685,957`; all-three-command tests. |
| Search post-results paths | `QueryLogRepository.add` | fail-soft gated write | ✓ WIRED | `search.py:492,687,959`; row-count and opt-out tests. |
| `cli/commands/suggest.py` | `SuggestionEngine` | three section reads | ✓ WIRED | `suggest.py:103-109,163-183`; real-DB CLI tests. |

The key-link query reported path-parse false negatives where PLAN `from:` values include component annotations (for example `search.py (query_cmd)`). Each was resolved manually above; there are **9/9 actual connections wired**, not missing links.

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `sif suggest` sections | `completions`, `did_you_mean`, `history` | `documents_fts_v` and `query_log` through `QueryLogRepository.history` | Yes — production-DDL real-DB CLI tests returned vocab terms and logged queries | ✓ FLOWING |
| Zero-result DYM (CLI) | `suggestions` | `SuggestionEngine.did_you_mean` over live FTS, validated by real MATCH probe | Yes — tests assert `quantm machin` → `quantum machin` | ✓ FLOWING |
| History ranking | `(query, count, last_used)` | `query_log` rows written by executed searches | Yes — real row counts, values, ranking, opt-out, and clear asserted | ✓ FLOWING |
| Weighted fusion | `options.*`, `rrf_score` | CLI flags/settings or MCP request fields into `SearchOptions` | Yes — direct scores/order plus real pipeline golden/reorder tests | ✓ FLOWING |
| MCP suggestions | `QueryOutput.suggestions` | `HybridSearchResults.suggestions` from the engine | Yes — backend and final serialized handler payload asserted | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase 15 regression battery | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/search/test_rrf.py tests/unit/search/test_suggest.py tests/unit/search/test_hybrid.py tests/unit/cli/test_suggest.py tests/unit/cli/test_search.py tests/unit/mcp/test_backend.py tests/unit/database/test_query_log_repo.py tests/unit/database/test_schema.py tests/unit/config/test_settings.py --no-cov` | 378 passed in 2.24s | ✓ PASS |
| Byte-identical default fusion | Direct Python: plain `fuse` vs explicit `[1.0,1.0], k=60` | Identical document order, ranks, and `repr(rrf_score)` | ✓ PASS |
| Weighted fusion reorders | Direct Python: `[5.0,0.2], k=10` | `[a,c,d,b]` → `[a,b,c,d]` | ✓ PASS |
| 66k-term suggest core | Direct Python, fresh engine for each of 3 runs | 26.806 / 29.054 / 31.878 ms | ✓ PASS |
| Full HEAD quality gate | Supplied HEAD gate result for `b47f55f` | 1591 passed, 1 skipped, 95.18% coverage; ruff/format/ty clean | ✓ PASS |

### Probe Execution

N/A — no probe is declared by the phase and no `scripts/*/tests/probe-*.sh` files exist; this is not a migration/tooling phase.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| QUAL-01 | 15-01 | Fusion weights/k via settings and per-query parameters; byte-identical defaults | ✓ SATISFIED | Truths 1-9; direct parity/reorder plus CLI, MCP, pipeline, and settings tests. |
| QUAL-02 | 15-02, 15-03 | Zero-result DYM from indexed terms, at least one hit, never silent rewrites | ✓ SATISFIED | Truths 10-15, 24-28; SC2 real-query pin and host serialization tests. D-05's user-selected zero-result-only narrowing was accepted in UAT. |
| QUAL-03 | 15-02, 15-03 | Local query-history suggestions with opt-out and clear | ✓ SATISFIED | Truths 16-18, 23, 26; storage, cap, ranking, gating, clear, and no-MCP-write tests. |
| QUAL-04 | 15-02, 15-03 | `sif suggest` prefix + DYM + history within 100 ms | ✓ SATISFIED | Truths 19-23, 29-30; three-section table/JSON and direct 26.8-31.9 ms measurements. |

No orphaned requirements: `REQUIREMENTS.md` maps exactly QUAL-01 through QUAL-04 to Phase 15, and all appear in plan frontmatter.

### Decision Coverage

All trackable CONTEXT.md decisions are honored by shipped artifacts — **14/14 honored**, none missing (`check.decision-coverage-verify`).

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|------------|--------|---------|----------|-----------------|---------|
| `tests/unit/search/test_rrf.py` | QUAL-01 | Yes | 0 | No | Value/behavioral | PASS |
| `tests/unit/search/test_hybrid.py` | QUAL-01 | Yes | 0 in focused run | No | Behavioral; literal pre-change snapshot | PASS |
| `tests/unit/search/test_suggest.py` | QUAL-02/03/04 | Yes | 0 | No | Behavioral with real BM25 re-query | PASS |
| `tests/unit/database/test_query_log_repo.py` | QUAL-03 | Yes | 0 | No | Value/behavioral with real SQL | PASS |
| `tests/unit/database/test_schema.py` | QUAL-02 | Yes | 0 in focused run | No | Value/behavioral | PASS |
| `tests/unit/config/test_settings.py` | QUAL-01/03 | Yes | 0 | No | Value | PASS |
| `tests/unit/cli/test_suggest.py` | QUAL-04 | Yes | 0 | No | Behavioral on real DB | PASS |
| `tests/unit/cli/test_search.py` | QUAL-01/02/03 | Yes | 0 | No | Behavioral, output shape, persistence | PASS |
| `tests/unit/mcp/test_backend.py` | QUAL-01/02 | Yes | 0 | No | Behavioral through serialized boundary | PASS |

**Disabled tests on requirements:** 0 disabled tests. Environment guards using `pytest.skip` did not trigger in the focused run; the result was 378 passed, 0 skipped.
**Circular patterns detected:** 0. The compatibility snapshot is a literal captured from pre-change code, not generated by the current system during the test.
**Insufficient assertions:** 0. Assertions check values, ordering, persistence, output shapes, and end-to-end behavior rather than mere existence.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | `TBD`/`FIXME`/`XXX` debt markers | — | None found. |
| — | — | TODO/HACK/placeholder/not-implemented stubs | — | None found; the `placeholders` SQL-bind local in `repositories.py:636-638` is functional WR-01 batching code. |
| — | — | Empty/debug-only implementations | — | None found; empty suggestion returns are tested degradation paths, not stubs. |

### Human Verification Required

None. The earlier five human checks are complete in `15-UAT.md` (5/5 passed): real-corpus suggestion quality, zero-result-only product scope, real-index latency, security verification, and terminal rendering. This re-verification found no new behavior-unverified or non-inferable item requiring another human decision.

### Phase 16.1 / WR-01 Regression Assessment

- `08e261b` replaced the three `Database(...); init_schema()` pairs in `search.py` with `open_initialized_database`; the weight resolution, pipeline call, zero-result suggestion hook, and history write remain in their original order. Constructor-only RuntimeError guards do not wrap suggestion or history behavior.
- `381e07c` made the same opener-only substitution in `suggest.py`; three-section collection/rendering and clear-after-commit behavior are unchanged. Fifteen current suggest CLI tests, including error-presentation and preservation pins, passed.
- `aa520be` changed only `LLMCacheRepository.clear_expired` batching. `QueryLogRepository` at `repositories.py:645-698` still blames entirely to Phase 15 commit `04d0d93a`, and its real-SQL tests pass.
- No regression was found in weighted fusion, per-query plumbing, suggestion generation, query history, or output contracts.

### Gaps Summary

No gaps. Phase 15's goal remains achieved at HEAD `b47f55f`: defaults are repr-exact, weighted RRF and per-query controls work, suggestions are real index-derived display-only queries with hit validation, local history supports opt-out/clear, and `sif suggest` meets the measured 100 ms core budget. All prior UAT and security follow-ups are closed. The fresh covered-input fingerprint supersedes the stale report.

---

_Verified: 2026-11-12T07:47:46Z_
_Verifier: Claude (gsd-verifier)_
