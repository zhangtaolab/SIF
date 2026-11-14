---
phase: 18-quality-instrument-personal-bench-rapidfuzz-dym
verified: 2026-11-14T16:28:04Z
status: human_needed
score: 44/44 must-haves verified
covered_files: [".planning/phases/18-quality-instrument-personal-bench-rapidfuzz-dym/18-01-PLAN.md", ".planning/phases/18-quality-instrument-personal-bench-rapidfuzz-dym/18-01-SUMMARY.md", ".planning/phases/18-quality-instrument-personal-bench-rapidfuzz-dym/18-02-PLAN.md", ".planning/phases/18-quality-instrument-personal-bench-rapidfuzz-dym/18-02-SUMMARY.md", ".planning/phases/18-quality-instrument-personal-bench-rapidfuzz-dym/18-03-PLAN.md", ".planning/phases/18-quality-instrument-personal-bench-rapidfuzz-dym/18-03-SUMMARY.md", ".planning/phases/18-quality-instrument-personal-bench-rapidfuzz-dym/18-04-PLAN.md", ".planning/phases/18-quality-instrument-personal-bench-rapidfuzz-dym/18-04-SUMMARY.md", "docs/architecture.md", "docs/benchmarking.md", "docs/cli-reference.md", "pyproject.toml", "scripts/generate_cli_ref.py", "src/sif/cli/commands/eval.py", "src/sif/cli/main.py", "src/sif/search/benchmark.py", "src/sif/search/hybrid.py", "src/sif/search/personal_bench.py", "src/sif/search/suggest.py", "tests/support/eval.py", "tests/test_docs.py", "tests/unit/cli/test_eval.py", "tests/unit/search/test_benchmark.py", "tests/unit/search/test_personal_bench.py", "tests/unit/search/test_suggest.py", "uv.lock"]
covered_digest: "v4:sha256:c2bbf814e54238c3f208e8b3f9ed63ef33939358117030dc26123f9d91063598"
behavior_unverified: 0
overrides_applied: 0
prohibitions_flagged: 13
human_verification:
  - test: "P1: Confirm the body-leg query excerpt is acceptable under the no-document-body-content prohibition"
    expected: "You agree titles/paths/ids/metrics plus the <=10-token synthesized excerpt (WR-05 disclosure) are the intended output"
    why_human: "Judgment-tier privacy prohibition; LLM audit is non-authoritative"
  - test: "P2: Confirm the remote-provider disclosure plus --bm25-only satisfies the no-personal-data-upload prohibition"
    expected: "No eval-owned upload; disclosure is accurate and visible on stderr and in report notes"
    why_human: "Judgment-tier privacy prohibition"
  - test: "P3: Confirm per-leg and total rejected-query counts are sufficient transparency"
    expected: "No silent query-set shrinkage"
    why_human: "Judgment-tier transparency prohibition"
  - test: "P4: Confirm suppressed group names are listed and replay is labelled stability, never quality"
    expected: "No zero-valued rendering for a suppressed group"
    why_human: "Judgment-tier transparency prohibition"
  - test: "P5: Confirm per-leg rejection counts and the applied budget are always reported"
    expected: "No hidden rejections"
    why_human: "Judgment-tier transparency prohibition"
  - test: "P6: Audit report fields for document content/snippets beyond query strings"
    expected: "Query strings, paths, ids, metrics only"
    why_human: "Judgment-tier privacy prohibition"
  - test: "P7: Review the winner rule and held-out gating"
    expected: "No winner inside noise and no defaults change from tuning results"
    why_human: "Judgment-tier integrity prohibition"
  - test: "P8: Run --compare against a changed corpus"
    expected: "Clear refusal naming both fingerprints; no manufactured delta"
    why_human: "Judgment-tier integrity prohibition"
  - test: "P9: Inspect a saved run file from a real corpus"
    expected: "Only query text/paths/ids/metrics; local cache only; short body excerpt acknowledged"
    why_human: "Judgment-tier privacy prohibition"
  - test: "P10: Feed a malformed saved run to --compare"
    expected: "Clear ClickException naming the field; no traceback and no path opened"
    why_human: "Judgment-tier safety prohibition"
  - test: "P11: Confirm scorer=fuzz.ratio and cutoff 75.0 on the 0-100 Indel scale, with no WRatio path"
    expected: "Deliberate, documented scorer semantics"
    why_human: "Judgment-tier transparency prohibition"
  - test: "P12: Confirm every displayed suggestion re-queries to at least one hit"
    expected: "No fabricated suggestion"
    why_human: "Judgment-tier integrity prohibition"
  - test: "P13: Confirm the search path never auto-rewrites a user query"
    expected: "Suggestions remain display-only"
    why_human: "Judgment-tier product prohibition"
  - test: "Run sif eval --personal --bm25-only (or hybrid) on a real indexed corpus with >=50 documents, then --compare the saved run after re-indexing"
    expected: "Readable per-leg/group table, saved-run path on stderr, and a comparison with CI/winner columns; numbers plausible for the corpus"
    why_human: "Tests use synthetic fixtures; the phase outcome is user-facing measurement on a real corpus"
  - test: "Run sif suggest <first-letter-typo> on a large indexed corpus"
    expected: "Suggestions appear promptly (measured p50 1.376 ms at 73k terms) and include first-letter-typo corrections"
    why_human: "Performance feel and lexical usefulness are user judgments"
---

# Phase 18: Quality Instrument (Personal Bench + rapidfuzz DYM) Verification Report

**Phase Goal:** Users can measure search quality on their own corpus with trustworthy bias controls BEFORE any ranking behavior changes — the instrument that arbitrates the correctness fixes (19), the Harrier gate (23), and the tuning sweeps (24).
**Verified:** 2026-11-14T16:28:04Z
**Status:** human_needed (all automated must-haves verified; 13 judgment-tier prohibitions and 2 real-corpus UAT checks need human resolution)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `sif eval --personal` runs on a real on-disk index (>=50 docs) and emits a nDCG@10/Hit@10 table plus strict `--json` | ✓ VERIFIED | `_run_fresh`/`_render_personal` in `src/sif/cli/commands/eval.py`; `test_personal_run_renders_table`, `test_personal_json_is_strict_and_shaped` pass |
| 2 | Title/H1 leg synthesizes one known-item query per sampled document, labelling only the target grade 1 through the legacy `{"queries":[{"query","relevant_docids"}]}` schema | ✓ VERIFIED | `synthesize_title_queries` + `build_legacy_fixture` (`src/sif/search/personal_bench.py:1081-1093`); `SearchEvaluator` legacy path |
| 3 | Deterministic sampling by `(sha256(path + NUL + checksum), path, id)`; two runs produce identical sampled set and query order | ✓ VERIFIED | `_sample_key` (`personal_bench.py:736`); `test_two_runs_emit_the_identical_query_order` passes |
| 4 | Whole-corpus scan is metadata-only (`id,path,title,checksum,file_size`); bodies load only for the bounded sample; report names retrieval mode and provider | ✓ VERIFIED | `load_document_metadata` SELECT omits `content`; `load_sampled_content` bounded/chunked; `PersonalReport.retrieval`/`.model` |
| 5 | Remote-capable embedder (`openai`/`modelscope`) disclosed on stderr with the `--bm25-only` local alternative; eval code never uploads, serializes, or prints body content | ✓ VERIFIED | `_REMOTE_MODEL_TYPES` disclosure in `eval.py:220-227` and report notes; no upload path in `personal_bench.py`; `_SAVED_FORBIDDEN_KEYS = {"content","snippet"}` |
| 6 | `SearchEvaluator.evaluate_per_query()` is additive; `report()`/`BenchReport.to_dict()` stay byte-identical | ✓ VERIFIED | Commit 715b270 changes `benchmark.py` `+52/-0` (additions only); `test_report_to_dict_keeps_exactly_its_pre_change_keys` and 20 benchmark tests pass |
| 7 | Empty edge: <50 docs exits 1 with a ClickException naming the count and `sif index update`; empty title rejected and counted | ✓ VERIFIED | `MIN_DOCUMENTS` guard in `_run_fresh`; `test_fewer_than_min_documents_exits_one_with_count_and_remedy`, `test_empty_title_is_rejected_and_never_emitted` pass |
| 8 | Adjacency edge: duplicate normalized query text collides; first in deterministic sample order kept, later counted duplicate | ✓ VERIFIED | `dedupe_queries` sorts by declared leg then input order; `test_duplicate_normalized_title_keeps_the_first_and_counts_it` passes |
| 9 | Ordering edge: emission order is sampled-document order; JSON `queries` counts use fixed keys; no set iteration order reaches output | ✓ VERIFIED | `build_personal_report` fixed keys; `_per_leg_queries` declared title/body order; replay normalized+sorted |
| 10 | Generated CLI docs render an `eval` section after the leaf-group fix; `make docs-generate` produces no diff | ✓ VERIFIED | `make docs-generate` exit 0; `git diff --exit-code -- docs/` exit 0; `test_cli_reference_has_all_commands` passes; `docs/cli-reference.md:622` |
| 11 | Default run delivers all three legs (title, body, replay), each with its own counts and applied budget | ✓ VERIFIED | `synthesize_known_item_queries` + `replay_leg`; `_per_leg_queries`/`_legs_table`; `TestTwoLegDefault` passes |
| 12 | Body leg rejects token Jaccard > 0.60 against title + first 200 chars and reports the count; title is exact-term/unbudgeted; replay synthesizes nothing | ✓ VERIFIED | `apply_overlap_budget` (`> OVERLAP_BUDGET` rejects, 0.60 accepted); `LEG_BUDGETS`; `test_over_budget_is_rejected_and_counted`, `test_exactly_sixty_percent_is_accepted`, `test_title_leg_is_exact_term_and_never_budgeted` pass |
| 13 | Hash split 50/50 by sha256; start from 50 docs, widen by doubling toward `min(eligible, 250)` while accepted<50 or held-out<25; `run_personal` invokes it before evaluation; only a floor unmet at the cap raises a counted ValueError | ✓ VERIFIED | `assign_split` (`digest[0] < 128`), `ensure_heldout`, `_run_fresh`; `test_widens_to_the_cap...`, `test_no_widening_when_the_floors_are_met` pass |
| 14 | Both known-item legs flow through one `synthesize_known_item_queries` orchestrator invoked by the personal run; per-leg counts appear in table and JSON | ✓ VERIFIED | `ensure_heldout` → `_synthesize_and_split` → orchestrator; `_run_fresh`; per-leg `budget/accepted/rejected_*` rendered |
| 15 | `PersonalReport` carries `mode`, `retrieval`, `top_k`, `corpus(documents,sampled,fingerprint,widened)`, `model`; records carry rank-aligned `retrieved_doc_ids`; `to_dict()` adds `top_k`, `splits`, `groups`, `suppressed`, `replay` | ✓ VERIFIED | `PersonalReport`/`PersonalQueryRecord` dataclasses; `test_to_dict_keeps_plan_01_keys_and_adds_the_new_sections` passes |
| 16 | Per-leg × per-language × per-length report; groups below 10 suppressed and named so an empty cell is never read as zero | ✓ VERIFIED | `group_metrics` / `SUPPRESS_BELOW = 10`; `test_nine_query_group_is_suppressed_and_named`; `_groups_table` |
| 17 | Adjacency edge: Jaccard exactly 0.60 accepted; cross-leg duplicates resolved in declared leg order (title before body), first kept, later counted per leg | ✓ VERIFIED | `apply_overlap_budget`, `_leg_rank`, `dedupe_queries`; tests pass |
| 18 | Empty edge: body candidate <4 tokens rejected/counted; zero body candidates still yields visible `body` count 0; empty query_log makes replay `available: false` and never fails the run | ✓ VERIFIED | `_BODY_MIN_TOKENS` in `synthesize_body_queries`; `_per_leg_queries` always includes body; `test_empty_query_log_yields_an_unavailable_leg` passes |
| 19 | Ordering edge: split is `sha256(normalized_query)[0] < 128 -> tuning`; groups emitted in LEGS × LANGUAGES × LENGTH_BUCKETS order; replay sorted lexicographically | ✓ VERIFIED | `assign_split`, `group_metrics`, `load_replay_queries`; tests pass |
| 20 | Replay reports `available`, replayed count, and the CLI-only bias note; never folded into known-item nDCG/Hit; never assigned a split | ✓ VERIFIED | `ReplayResult`/`REPLAY_BIAS_NOTE`; `build_personal_report` means over records only; `test_replay_never_changes_known_item_metrics_splits_or_groups`, `test_group_metrics_never_include_replay_records` pass |
| 21 | Every personal run auto-saves a versioned JSON query set under `<cache_dir>/eval/`; `--no-save` opts out; records carry query/path/split/leg/language/length/grade plus rank-aligned retrieved paths/ids; envelope records `top_k`; no content | ✓ VERIFIED | `_save_run` uses `settings.get_cache_dir()/ "eval"`; `run_to_saved`/`saved_run_to_dict`; `test_personal_run_writes_exactly_one_versioned_run`, `test_no_save_writes_no_run_and_reports_none` pass |
| 22 | `--compare` refuses a fingerprint mismatch with a clear ClickException; on match evaluates exactly the saved query set (no re-synthesis, no overlap re-application) | ✓ VERIFIED | `require_matching_corpus`; `compare_saved_run` builds queries directly; `test_compare_evaluates_exactly_the_saved_queries_in_saved_order`, `test_compare_fingerprint_mismatch_exits_one_with_both_values` pass |
| 23 | Comparison reports paired nDCG@10 deltas with a seeded 95% percentile bootstrap CI, the 1/N noise floor, helped/hurt/unchanged overall, per split, and per group (suppressed <10 named); winner only when CI excludes zero and rounded mean reaches 0.01 | ✓ VERIFIED | `paired_bootstrap` (`random.Random(0)`, 10,000), `noise_gate`, `group_noise_gates`; boundary tests pass |
| 24 | Both arms grade through document id (saved `retrieved_doc_ids` vs resolved current id); repeated ids deduped by first occurrence so baseline nDCG@10 cannot exceed 1.0 | ✓ VERIFIED | `_baseline_query_metrics` + `_dedupe_first`; `test_repeated_target_id_counts_once_and_never_exceeds_one` passes |
| 25 | Every auto-saved run comes from one `run_to_saved` contract; `--compare` passes `ComparisonReport.current_report`; `created_at` stamped inside `run_to_saved` | ✓ VERIFIED | `run_to_saved` (`created_at` line 1317); `_save_and_render`; `test_saved_run_is_built_from_the_report_contract` passes |
| 26 | Saved run records `top_k`; `--compare` evaluates both arms at saved depth; retrieval-mode difference surfaced on stderr and in comparison JSON | ✓ VERIFIED | `_run_compare` builds options at `saved.top_k`, warns; `ComparisonReport.retrieval`; `test_compare_uses_saved_depth_and_warns_when_limit_differs`, `test_compare_retrieval_mode_difference_warns_and_still_reports` pass |
| 27 | Only the held-out split can warrant a default change | ✓ VERIFIED | `warrants_default_change=splits["heldout"].winner` (`personal_bench.py:2143`); `test_only_the_held_out_gate_warrants_a_defaults_change` passes |
| 28 | Replay comparison reports Jaccard@10 and top-1 stability; `available: false` instead of inventing a number when either side is missing | ✓ VERIFIED | `replay_stability`; `test_compare_table_reports_replay_unavailable_on_stderr` passes |
| 29 | Adjacency edge: rounded 0.01 with CI excluding zero wins; 0.009999 does not; a CI including zero never declares one | ✓ VERIFIED | `noise_gate`; `test_exactly_one_hundredth_above_the_noise_floor_declares_a_winner`, `test_below_the_tie_rule_never_declares_a_winner`, `test_ci_containing_zero_never_declares_a_winner` pass |
| 30 | Empty edge: malformed envelope (types/version/top_k/replay/record fields), zero records, >10,000 records, non-finite floats, non-list ids, unknown leg/split/language/length rejected naming the field; empty deltas report `sufficient: false` and no winner | ✓ VERIFIED | `validate_saved_run` + `_saved_*` validators; parametrized envelope/record defect tests, `test_compare_deeply_nested_saved_run_is_a_click_exception`, `test_empty_list_is_insufficient` pass |
| 31 | Ordering edge: positional pairing over saved order; `random.Random(0)` exactly 10,000 resamples; arrays preserve saved order; target resolves by id first, unique-path fallback only | ✓ VERIFIED | `compare_saved_run`/`paired_bootstrap`/`resolve_saved_targets`; `test_target_resolves_by_document_id_before_path`, `test_stale_id_with_an_ambiguous_path_is_a_loud_error` pass |
| 32 | `rapidfuzz>=3.14.5,<4` is a hard runtime dependency; `uv.lock` regenerated resolving 3.14.5 on py3.10 and 3.14.6 on py3.11+ | ✓ VERIFIED | `pyproject.toml:41`; `uv.lock:494-495` markers; `uv lock --check` passes (independent run) |
| 33 | `_close_matches` scans the FULL sorted vocabulary with `process.extract(token, self._terms, scorer=fuzz.ratio, limit=None, score_cutoff=75.0)`; first-letter bucket and difflib gone | ✓ VERIFIED | `src/sif/search/suggest.py:276-284`; grep finds no `difflib`, no bucket |
| 34 | First-letter typo `xuantum -> quantum` recalled; a full-vocabulary spy proves the choice list is the entire vocabulary | ✓ VERIFIED | `test_first_letter_typo_is_recalled`; `test_full_vocab_dym_under_budget_on_60k_vocab` asserts `max(calls) == vocab_size` — both pass |
| 35 | Cutoff is an internal constant 75.0 (no setting/CLI knob); exactly 75.0 included, below excluded | ✓ VERIFIED | `_DYM_CUTOFF = 75.0`; no settings key; `test_cutoff_boundary_includes_exactly_75`, `test_cutoff_boundary_excludes_below_75` pass |
| 36 | Tie-break score desc → term lexicographic asc → df desc; `limit=None` returns every above-cutoff candidate, then sorted and sliced | ✓ VERIFIED | Sort key `(-match[1], match[0], -self._df.get(...))`; `limit=None` |
| 37 | Adjacency edge: score exactly 75.0 included (`>=`, no epsilon); equal scores ordered term asc then df desc | ✓ VERIFIED | rapidfuzz inclusive `score_cutoff`; `test_cutoff_boundary_includes_exactly_75`, `test_equal_scores_order_by_term_and_are_stable` pass |
| 38 | Empty edge: empty token or vocabulary returns `[]`; no above-cutoff match yields no suggestion; `_dym_slots` returns None when an out-of-vocab token is uncorrectable | ✓ VERIFIED | Guards in `_close_matches`/`_dym_slots`; `test_empty_token_and_empty_vocab_return_no_matches`, `test_uncorrectable_token_yields_no_suggestion` pass |
| 39 | Output order is deterministic for a fixed vocabulary and query | ✓ VERIFIED | Sorted term list + explicit sort; `test_repeated_calls_are_deterministic` passes |
| 40 | QUAL-01 cutoff boundary: the only cutoff rule is the pinned 75.0 constant with `>=` inclusion — no epsilon, no WRatio, no runtime knob | ✓ VERIFIED | `scorer=fuzz.ratio` explicit; no WRatio/knob in `suggest.py` |
| 41 | Probe/hit contracts untouched: every emitted suggestion returns >=1 hit, `_probe` stays fail-soft, prefix completions/history unchanged | ✓ VERIFIED | `did_you_mean` filters through `_hits`; `_probe` catches `sqlite3.OperationalError`; whole `test_suggest.py` (38 tests) passes |
| 42 | ROADMAP SC1: personal eval runs with no manual labeling — known-item synthesis + legacy fixture schema + `SearchEvaluator` reuse + query_log replay, with CLI-only bias documented | ✓ VERIFIED | Truths 1, 2, 11, 20; `REPLAY_BIAS_NOTE`; `docs/benchmarking.md:155` |
| 43 | ROADMAP SC2: trustworthy numbers — overlap budget enforced, per-leg × language × length(category) reports, hash-split tuning/held-out, paired deltas with noise gate (N≈71 floor ~0.014 vs 0.01 tie rule) | ✓ VERIFIED | Truths 12, 13, 16, 23, 29; `docs/benchmarking.md:192` documents the N≈71 ~0.014 floor |
| 44 | ROADMAP SC3: faster, higher-recall DYM — swap drops first-letter bucketing, within ≤10 ms, cutoff re-measured on 0–100 Indel, tie-break/probe contracts preserved | ✓ VERIFIED | Truths 32–41; measured full-vocab p50 1.376 ms / max 2.994 ms at 73,040 terms (below the 10 ms budget) |

**Score:** 44/44 truths verified (0 present, behavior-unverified)

### Deferred Items

None. All phase requirements are claimed by a plan; no gap was deferred to a later milestone phase.

### Advisory (New Scope, Unevidenced)

Not applicable — initial verification (no prior VERIFICATION.md, so the #3304 gate is a no-op).

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/sif/search/personal_bench.py` | metadata scan, deterministic sampling, 3-leg synthesis, overlap budget, split/widening, groups, saved-run schema/validation, paired bootstrap/noise gate, replay stability | ✓ VERIFIED | 2,145 lines; all domain surfaces present and exercised |
| `src/sif/search/benchmark.py` | additive `SearchEvaluator.evaluate_per_query` + `QueryEvaluation` | ✓ VERIFIED | +52/−0 in commit 715b270; `report()`/`to_dict()` untouched |
| `src/sif/cli/commands/eval.py` | `eval_group` with `--personal/--compare/--no-save/--bm25-only/-n/-c/--all/--json` and both runners | ✓ VERIFIED | 910 lines; rendered tables/JSON verified |
| `src/sif/cli/main.py` | eval group registration | ✓ VERIFIED | import line 94, `cli.add_command(eval_group)` line 114 |
| `scripts/generate_cli_ref.py` | leaf-group traversal fix + eval in GROUP_ORDER | ✓ VERIFIED | `make docs-generate` clean |
| `tests/support/eval.py` | on-disk ≥50-doc fixture + query_log seeding | ✓ VERIFIED | `build_personal_db(documents=60)`, `seed_query_log(keep=500)` |
| `docs/cli-reference.md` | regenerated `eval` section incl. `--compare`/`--no-save` | ✓ VERIFIED | eval section lines 622-648; generator no-diff |
| `tests/unit/search/test_personal_bench.py` | EVAL-01/EVAL-02 domain battery | ✓ VERIFIED | 144 tests; all pass |
| `docs/benchmarking.md` | personal bench narrative, comparison contract, noise-gate interpretation | ✓ VERIFIED | Lines 145-203 cover all clauses |
| `pyproject.toml` | `rapidfuzz>=3.14.5,<4` | ✓ VERIFIED | Line 41 |
| `uv.lock` | regenerated resolution | ✓ VERIFIED | 3.14.5 (<3.11) / 3.14.6 (>=3.11); `uv lock --check` passes |
| `src/sif/search/suggest.py` | `_DYM_CUTOFF`, rapidfuzz full-vocabulary `_close_matches`; difflib removed | ✓ VERIFIED | 313 lines; no difflib |
| `tests/unit/search/test_suggest.py` | full-vocab spy, first-letter recall, cutoff boundary, tie-break, budget | ✓ VERIFIED | 38 tests; all pass |
| `docs/architecture.md` | SuggestionEngine rapidfuzz narrative + PersonalBench row | ✓ VERIFIED | Lines 250, 674, 708-709 |
| `src/sif/search/hybrid.py` | literal-mode pipeline (`parse_prefix=False`) for CR-01 | ✓ VERIFIED | `eval.py:_search_fn` uses it; `TestLiteralPrefixedQueries` passes |

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/sif/cli/commands/eval.py` | `src/sif/search/personal_bench.py` | `run_personal()` calls the domain pipeline | ✓ WIRED | `from sif.search.personal_bench import (...)` line 35; calls `ensure_heldout`, `evaluate_known_items`, `replay_leg`, `build_personal_report`, `compare_saved_run`, `run_to_saved` |
| `src/sif/search/personal_bench.py` | `src/sif/search/benchmark.py` | `evaluate_per_query` is the only metric path | ✓ WIRED | `from sif.search.benchmark import (...)` line 39; `evaluate_known_items` calls it |
| `src/sif/cli/main.py` | `src/sif/cli/commands/eval.py` | `cli.add_command(eval_group)` | ✓ WIRED | Import + registration at lines 94/114 |
| `src/sif/search/personal_bench.py` | `src/sif/database/repositories.py` | `QueryLogRepository.history()` is the only replay source | ✓ WIRED | Import line 38; `load_replay_queries` calls `history()` |
| `src/sif/cli/commands/eval.py` | `src/sif/search/personal_bench.py` | CLI renders `to_dict()`, never recomputes groups/splits | ✓ WIRED | `_render_personal`/`_render_comparison` only read payload |
| `src/sif/search/personal_bench.py` | `src/sif/search/benchmark.py` | `percentile()` / `warrants_default_change()` reused | ✓ WIRED | Imports `EPSILON`, `percentile` (lines 41/46); held-out gate sets `warrants_default_change` |
| `src/sif/config/settings.py` | auto-save directory | `Settings.get_cache_dir()`; no new setting | ✓ WIRED (location note) | The plan named `personal_bench.py` as the source; the save directory is resolved in the CLI writer (`eval.py:505` `settings.get_cache_dir() / "eval"`). The contract ("no new setting", local cache path) holds, and `run_to_saved` intentionally does not write files. Not a functional gap. |
| `src/sif/search/suggest.py` | `pyproject.toml` | imports `rapidfuzz.fuzz`/`rapidfuzz.process`; declared and locked | ✓ WIRED | Import line 22; dependency line 41; lock entries |
| `src/sif/search/suggest.py` | `src/sif/search/bm25.py` | `_probe`/`_hits`/`_retrievable` call `BM25Searcher._build_fts_query` | ✓ WIRED | Import line 26; calls at lines 162/176 |

Automated `gsd_run query verify.key-links` reported all links `verified: false` with detail "Target not referenced in source". That is a heuristic limitation: with no `pattern:` in a link, the verb only searches for the literal slash-path string inside the source file, while these modules import each other by dotted module path (e.g. `from sif.search.personal_bench import ...`). Direct source inspection above verifies every link; the single recorded deviation is the `Settings.get_cache_dir()` source location, which still satisfies the link's intent.

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `personal_bench.py` | `DocumentRecord` / `SynthesizedQuery` / `PersonalQueryRecord` | `documents` table metadata + bounded `content` loads + `query_log` | Yes — real SQL reads; no static/mock return | ✓ FLOWING |
| `cli/commands/eval.py` | `evaluations` / `report.to_dict()` | `SearchPipeline.search` over the index; report assembled from records | Yes | ✓ FLOWING |
| `benchmark.py` | `QueryEvaluation` | `search_fn` results + fixture grades | Yes | ✓ FLOWING |
| `suggest.py` | `_terms` / `_df` / suggestions | `documents_fts_v` (fts5vocab) + index probes | Yes | ✓ FLOWING |
| docs (`benchmarking.md`, `cli-reference.md`, `architecture.md`) | static prose/generated text | generator + hand-written narrative | N/A (static artifact) | ✓ VERIFIED |

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All requirement-linked test files | `pytest tests/unit/search/test_personal_bench.py tests/unit/cli/test_eval.py tests/unit/search/test_suggest.py tests/unit/search/test_benchmark.py tests/unit/cli/test_bench.py tests/test_docs.py --no-cov` | 306 passed | ✓ PASS |
| Full-vocabulary DYM latency at 73,040 terms | inline `rapidfuzz.process.extract(..., scorer=fuzz.ratio, limit=None, score_cutoff=75.0)` ×7 | p50 1.376 ms, max 2.994 ms | ✓ PASS (≤10 ms) |
| Noise gate boundary (0.01 wins, 0.009999 does not, CI includes zero never) | `pytest -k "TestNoiseGate"` | all pass (boundary cases) | ✓ PASS |
| Hash split / overlap budget / bootstrap determinism | targeted pytest selection | 38 passed / 11 passed / 6 passed | ✓ PASS |
| CLI compare contract (saved order, fingerprint refusal, saved depth) | `pytest tests/unit/cli/test_eval.py::TestCompareCli` | 6 selected passed | ✓ PASS |
| Docs generator idempotence | `make docs-generate && git diff --exit-code -- docs/` | exit 0, no diff | ✓ PASS |
| Bench fixture integrity | `python scripts/generate_bench_fixture.py --check` | `OK: ... matches generator output (151 files)` | ✓ PASS |
| CLI surface | `python -m sif.cli.main eval --help` | all eight options listed | ✓ PASS |
| Full quality suite (independent evidence provided with the handoff) | `pytest` | 1882 passed, 1 skipped, 95.17% coverage | ✓ PASS (external evidence) |

## Probe Execution

N/A — this phase declares no probes and the repo has no `scripts/*/tests/probe-*.sh`; the phase is a library/CLI feature, not a migration/tooling probe phase.

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| EVAL-01 | 18-01, 18-02 | User can measure search quality on their own corpus via `sif eval --personal` (known-item synthesis through legacy fixture schema + `SearchEvaluator` reuse + query_log replay with documented CLI-only bias) | ✓ SATISFIED | Truths 1–5, 7–9, 20, 42; CLI tests + docs |
| EVAL-02 | 18-02, 18-03 | User can trust the bench's bias controls (overlap budget; per-leg × per-language × per-category reports; hash-split tuning/held-out; paired deltas + noise gate) | ✓ SATISFIED | Truths 11–19, 21–31, 43; domain + CLI tests + docs |
| QUAL-01 | 18-04 | Faster, higher-recall did-you-mean (rapidfuzz measured swap, first-letter bucketing dropped, ≤10 ms, 0–100 Indel cutoff, tie-break/probe preserved) | ✓ SATISFIED | Truths 32–41, 44; 38 suggest tests + measured latency + lock |

**Orphaned requirements:** none — all three Phase 18 IDs (EVAL-01, EVAL-02, QUAL-01) appear in plan frontmatter and are mapped to Phase 18 in `.planning/REQUIREMENTS.md:136-138`.

### Decision Coverage

All trackable CONTEXT.md decisions are honored by shipped artifacts (17/17; `gsd_run query check.decision-coverage-verify` exit 0, `not_honored: []`).

## Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| `tests/unit/search/test_personal_bench.py` | EVAL-01, EVAL-02 | 144 | 0 | No | Value + behavioral (exact metrics, counts, ordering) | ✓ PASS |
| `tests/unit/cli/test_eval.py` | EVAL-01, EVAL-02 | 107 | 0 | No | Behavioral (CLI table/JSON, exit codes, saved runs) | ✓ PASS |
| `tests/unit/search/test_suggest.py` | QUAL-01 | 38 | 0 | No | Value + behavioral (spy call count, exact-75 scores, order) | ✓ PASS |
| `tests/unit/search/test_benchmark.py` | EVAL-01 (additivity) | 20 | 0 | No | Value | ✓ PASS |
| `tests/unit/cli/test_bench.py` | EVAL-01 (bench unaffected) | 7 | 0 | No | Behavioral | ✓ PASS |
| `tests/test_docs.py` | EVAL-01/QUAL-01 (docs gates) | 13 | 0 (3 guard skips not triggered) | No | Existence + content | ✓ PASS |

**Disabled tests on requirements:** 0 → no blocker.
**Circular patterns detected:** 0. `tests/support/eval.py` builds fixture input (cur documents + query_log), never expected outputs from the system under test.
**Insufficient assertions:** 0 linked to a requirement. Expected values are independent (exact nDCG arithmetic, documented Indel scores, fixed sha256 rules), not captured engine output.

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers in any phase-modified file | — | None |
| — | — | No stub returns reaching user-visible output; empty-list returns are guarded degradation paths (empty vocab, unreadable saved run) | — | None |
| — | — | No `difflib` or first-letter bucket remains in `suggest.py` | — | None |

Code-review info findings IN-01..IN-11 (documentation/stream/dead-key observations) remain open by explicit user decision (`18-REVIEW-DISPOSITION.md`). None contradicts a plan must-have; the two closest (IN-01 model-mismatch JSON claim, IN-09 architecture layering claim) are documentation precision issues with no runtime effect on the phase goal. Recorded as ℹ️ Info, not blockers.

## Prohibition Verification (judgment tier)

All 13 plan prohibitions are `verification: judgment`. The LLM-judge audit below is **non-authoritative**; every item is flagged `unverified-prohibition — human review recommended` per ADR-550 D4.

| # | Plan | Prohibition | LLM-judge verdict | Evidence | Flag |
|---|------|-------------|-------------------|----------|------|
| P1 | 01 | MUST NOT store/print document body content in output/logs; only paths, ids, titles-as-query-text, aggregate metrics | No violation found under the query-string carve-out; body-leg queries are short (≤10-token) synthesized excerpts, disclosed by WR-05/docs | `to_dict`/`saved_run_to_dict` carry query text/paths/ids only; `_SAVED_FORBIDDEN_KEYS` | ⚠️ human review |
| P2 | 01 | MUST NOT upload/serialize personal data from eval code; remote-capable provider disclosed on stderr with `--bm25-only` | No violation found | No upload path; disclosure at `eval.py:220-227` + notes; runs stay local | ⚠️ human review |
| P3 | 01 | MUST NOT silently shrink the query set; every rejected title query counted and reported | No violation found | `rejected_empty`/`rejected_duplicate` and counts in every table/JSON | ⚠️ human review |
| P4 | 02 | MUST NOT present suppressed/empty group as zero; names listed; replay labelled stability, never quality | No violation found | `suppressed` list; `REPLAY_BIAS_NOTE`; "stability, not quality" rendering | ⚠️ human review |
| P5 | 02 | MUST NOT hide rejected synthesized queries; counts and applied budget always reported | No violation found | Per-leg table columns budget/accepted/empty/duplicate/overlap | ⚠️ human review |
| P6 | 02 | MUST NOT store body content or replay query text beyond query strings; no document content serialized | No violation found | No content/snippet fields; query strings only | ⚠️ human review |
| P7 | 03 | MUST NOT declare a winner inside noise; no tuning-gated decision | No violation found | `noise_gate` requires N floor + CI excludes zero + rounded ≥0.01 + floor clearance; `warrants_default_change` from held-out only | ⚠️ human review |
| P8 | 03 | MUST NOT compare a different corpus; fingerprint mismatch refuses | No violation found | `require_matching_corpus` raises; CLI ClickException | ⚠️ human review |
| P9 | 03 | MUST NOT store document content/snippets in saved runs; local only, never uploaded | No violation found under the query-string carve-out; short body excerpts are the stored query (documented) | `saved_run_to_dict`; forbidden keys; cache-dir path | ⚠️ human review |
| P10 | 03 | MUST NOT trust a saved-run file; validate version/types/ranges/caps/finite; never open saved paths | No violation found | `validate_saved_run` + helpers; `resolve_saved_targets` uses SQL only | ⚠️ human review |
| P11 | 04 | MUST NOT silently change scorer semantics; explicit `fuzz.ratio`, 0–100 Indel, no WRatio | No violation found | `scorer=fuzz.ratio`, `_DYM_CUTOFF=75.0` | ⚠️ human review |
| P12 | 04 | MUST NOT fabricate a DYM suggestion with zero hits; every variant flows through `_hits`/`_probe` | No violation found | `did_you_mean` filters via `_hits`; `test_every_suggestion_hits_as_query` | ⚠️ human review |
| P13 | 04 | MUST NOT auto-rewrite the user's query; suggestions remain display-only | No violation found | No search-path rewrite; `did_you_mean` returns strings | ⚠️ human review |

## Human Verification Required

### Judgment-tier prohibitions (13 items — flagged by ADR-550 D4)

1. **P1 — personal-eval privacy (body content)**
   **Test:** Confirm the body-leg excerpt admitted as a query string is acceptable under the "no document body content" prohibition.
   **Expected:** You agree the ≤10-token synthesized excerpt plus titles/paths/ids/metrics is the intended disclosure (WR-05 documentation).
   **Why human:** A judgment-tier prohibition cannot be authoritatively resolved by an LLM audit.

2. **P2 — no personal-data upload from eval code**
   **Test:** Confirm the remote-provider disclosure (stderr + notes) plus the `--bm25-only` alternative satisfies the prohibition.
   **Expected:** No eval-owned upload; disclosure is accurate and visible.
   **Why human:** Judgment-tier privacy semantics.

3. **P3 — rejected queries reported**
   **Test:** Confirm per-leg and total rejection counts are sufficient transparency.
   **Expected:** No silent shrinkage.
   **Why human:** Judgment-tier transparency.

4. **P4 — suppressed groups and replay labelling**
   **Test:** Confirm suppressed group names are listed and replay is labeled stability, never quality.
   **Expected:** No zero-valued cell for a suppressed group.
   **Why human:** Judgment-tier transparency.

5. **P5 — rejected-query counts and applied budget**
   **Test:** Confirm the per-leg budget column and rejection counts are always visible.
   **Expected:** No hidden rejections.
   **Why human:** Judgment-tier transparency.

6. **P6 — no body content in report fields beyond query strings**
   **Test:** Audit `to_dict()`/saved records for content/snippet fields.
   **Expected:** Query strings, paths, ids, metrics only.
   **Why human:** Judgment-tier privacy.

7. **P7 — no winner inside noise**
   **Test:** Review the winner rule (N floor, CI excludes zero, rounded ≥0.01, floor clearance) and held-out gating.
   **Expected:** No defaults change from tuning or a noise-level delta.
   **Why human:** Judgment-tier integrity.

8. **P8 — fingerprint refusal**
   **Test:** Run `--compare` against a changed corpus.
   **Expected:** Clear refusal naming both fingerprints; no manufactured delta.
   **Why human:** Judgment-tier integrity (the code path is tested; acceptance is a judgment).

9. **P9 — saved-run privacy**
   **Test:** Inspect a saved run file from a real corpus.
   **Expected:** Only query text/paths/ids/metrics; local cache only; short body excerpt acknowledged.
   **Why human:** Judgment-tier privacy.

10. **P10 — untrusted saved-run file**
    **Test:** Feed a malformed saved run.
    **Expected:** Clear ClickException naming the field; no traceback, no path opened.
    **Why human:** Judgment-tier safety (many cases are test-pinned; residual cases are judgment).

11. **P11 — scorer semantics unchanged**
    **Test:** Confirm `scorer=fuzz.ratio` and cutoff 75.0 on the 0–100 Indel scale, no WRatio path.
    **Expected:** Deliberate, documented semantics.
    **Why human:** Judgment-tier transparency.

12. **P12 — no zero-hit suggestions**
    **Test:** Confirm every displayed suggestion re-queries to ≥1 hit.
    **Expected:** No fabricated suggestion.
    **Why human:** Judgment-tier integrity.

13. **P13 — display-only suggestions**
    **Test:** Confirm the search path never auto-rewrites a user query.
    **Expected:** Suggestions require explicit user action.
    **Why human:** Judgment-tier product contract.

### Real-corpus UAT (2 items)

14. **Personal eval on your own corpus**
    **Test:** Run `sif eval --personal --bm25-only` (or hybrid) on a real indexed corpus with ≥50 documents, then save and re-run with `--compare <saved-run.json>` after re-indexing.
    **Expected:** A readable per-leg/group table, a saved-run path on stderr, and a comparison with CI/winner columns. Numbers are plausible for the corpus.
    **Why human:** Tests use synthetic fixtures; the phase outcome is a user-facing measurement on a real corpus.

15. **DYM latency and usefulness on your vocabulary**
    **Test:** Run `sif suggest <first-letter-typo>` on a large indexed corpus.
    **Expected:** Suggestions appear promptly (measured p50 1.376 ms at 73k terms) and include first-letter-typo corrections.
    **Why human:** Performance feel and lexical usefulness are user judgments.

## Gaps Summary

No gaps. All 44 merged must-have truths are verified against the codebase, all 14 unique artifacts are present/substantive/wired with real data flow, and all requirement-linked tests pass (306 selected tests; the full suite was independently reported at 1,882 passed, 1 skipped, 95.17% coverage). The docs generator is idempotent and the bench fixture check is clean.

Two items keep the status at `human_needed` rather than `passed`:
1. **13 judgment-tier prohibitions** are flagged for human review per ADR-550 D4 — the LLM-judge verdict is non-authoritative and must never be silently absorbed into a pass.
2. **2 real-corpus UAT checks** exercise the user-facing outcome on a corpus larger and more varied than the synthetic fixtures.

One recorded deviation is informational: the plan's `personal_bench.py -> settings.py` key link is fulfilled by `eval.py` calling `settings.get_cache_dir()` — the auto-save contract, local-only path, and "no new setting" rule all hold; only the calling module differs from the plan's written source.

---

_Verified: 2026-11-14T16:28:04Z_
_Verifier: Claude (gsd-verifier)_
