---
phase: 18-quality-instrument-personal-bench-rapidfuzz-dym
fixed_at: 2026-11-15T00:00:00Z
review_path: .planning/phases/18-quality-instrument-personal-bench-rapidfuzz-dym/18-REVIEW.md
iteration: 1
findings_in_scope: 11
fixed: 11
skipped: 0
status: all_fixed
---

# Phase 18: Code Review Fix Report

**Fixed at:** 2026-11-15
**Source review:** `.planning/phases/18-quality-instrument-personal-bench-rapidfuzz-dym/18-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 11 (CR-01, WR-01 through WR-10)
- Fixed: 11
- Skipped: 0
- Info findings IN-01 through IN-11: intentionally **not** fixed (explicit user decision); they remain open in `18-REVIEW.md` / `18-REVIEW-DISPOSITION.md`.

All fixes were applied on the main working tree (`dev`) as instructed, one atomic commit per
finding, with the repository hooks enabled (no `--no-verify`).

## Fixed Issues

### CR-01: Reserved-prefix titles/body/replay queries abort the entire eval

**Files modified:** `src/sif/search/hybrid.py`, `src/sif/cli/commands/eval.py`, `tests/unit/cli/test_eval.py`
**Commit:** `0033acd`

**Applied fix:** Added a literal mode to `SearchPipeline` (`parse_prefix=False`) that skips
`_parse_query_prefix` and routes the query through the configured default search type. The eval
`_search_fn` now constructs one literal-mode pipeline per run with
`default_search_type` set from the measured arm (`hybrid` when an embedder is loaded, `bm25`
otherwise), so known-item and replay text can never be reinterpreted as `vec:`/`hyde:`/`lex:`/
`expand:` operators.

**Test evidence:** `TestLiteralPrefixedQueries::test_vec_and_hyde_titles_and_history_run_as_literal_text`
uses the real pipeline in `--bm25-only` mode against a 60-document fixture whose titles alternate
between `vec:` and `hyde:` prefixes and whose `query_log` is seeded with `vec:`/`hyde:` history.
The run exits 0, the reserved-prefix titles and history queries reach the searcher as literal
text, and no vector/HyDE error aborts the run.

### WR-01: `-n/--limit` accepts zero and negative values

**Files modified:** `src/sif/search/personal_bench.py`, `src/sif/cli/commands/eval.py`, `tests/unit/cli/test_eval.py`, `docs/cli-reference.md`
**Commit:** `9feb106`

**Applied fix:** Added `MAX_TOP_K = 200` and declared the option as
`click.IntRange(1, MAX_TOP_K)`. The generated CLI reference was regenerated with
`make docs-generate` and committed (option type now `integer range`, help `(1-200)`).

**Test evidence:** `test_limit_outside_the_supported_range_is_a_usage_error` parametrizes
`0`, `-1`, and `201`; all exit 2 with a Click "Invalid value" message and no auto-saved file.

### WR-02: The saved-run writer can produce runs its own loader rejects

**Files modified:** `src/sif/search/personal_bench.py`, `src/sif/cli/commands/eval.py`, `tests/unit/search/test_personal_bench.py`, `tests/unit/cli/test_eval.py`
**Commit:** `7b10c26`

**Applied fix:** `_save_run` now runs `validate_saved_run(saved_run_to_dict(run))` before
resolving the cache directory or creating any file, translating a defect into a
`ClickException`. `run_to_saved` caps each `retrieved`/`retrieved_doc_ids` array at the report's
`top_k`; `validate_saved_run` enforces `1 <= top_k <= MAX_TOP_K`; and `write_saved_run`
serializes the payload first and refuses anything over `MAX_SAVED_FILE_BYTES` before writing.

**Test evidence:** `test_run_to_saved_caps_retrieval_arrays_at_top_k` (arrays truncated to
`top_k`), `test_write_saved_run_refuses_a_payload_over_the_size_cap` (ValueError, no file
created), envelope defect `top-k-too-large`,
`test_non_default_depth_round_trips_through_the_loader` (`-n 3` run loads back with
`top_k == 3`), and `test_unserializable_query_fails_before_any_file_is_written` (a >10,000-char
title exits 1 with "Could not save the personal eval run" and zero saved files).

### WR-03: `RecursionError` from a deeply nested saved-run file escapes as a traceback

**Files modified:** `src/sif/search/personal_bench.py`, `tests/unit/search/test_personal_bench.py`, `tests/unit/cli/test_eval.py`
**Commit:** `e073284`

**Applied fix:** `load_saved_run` catches `RecursionError` around `json.loads` and re-raises the
documented `ValueError` with "JSON is nested too deeply". The CLI's existing `ValueError` boundary
then turns it into a `ClickException`.

**Test evidence:** `test_load_translates_deeply_nested_json_to_value_error` (a ~200 KB,
100,000-deep file) and
`TestCompareCli::test_compare_deeply_nested_saved_run_is_a_click_exception` (exit 1, message,
no traceback).

### WR-04: Replay bypasses `SIF_QUERY_HISTORY_ENABLED=0`

**Files modified:** `src/sif/cli/commands/eval.py`, `tests/unit/cli/test_eval.py`
**Commit:** `d0b2d7b`

**Applied fix:** `_run_fresh` reads `settings.query_history_enabled`; when false it never calls
`load_replay_queries`, returns the unavailable replay result, and adds
"Replay skipped: SIF_QUERY_HISTORY_ENABLED=0 disables query-history reads." to the report notes.
Compare mode still uses the snapshot inside the user-supplied saved file.

**Test evidence:** `TestReplayCli::test_disabled_query_history_never_reads_the_log` seeds a
`query_log`, runs with the setting off, asserts `replay.available is False`, that the seeded text
never reaches the pipeline, and that the skip note is present.

### WR-05: Saved runs contain literal document-body text contrary to the privacy claim

**Files modified:** `docs/benchmarking.md`, `src/sif/search/personal_bench.py`, `tests/unit/search/test_personal_bench.py`, `tests/unit/cli/test_eval.py`
**Commit:** `42fc5fc` (code/tests/docs), `3678b92` (title-leg provenance wording)

**Applied fix:** Qualified the public privacy claim instead of hiding the data: saved runs store
the body-leg query string, described honestly as a short normalized excerpt of the sampled
document's later prose (at most 10 tokens, markup/punctuation stripped), while never storing full
bodies, snippets, or embeddings. Module/dataclass docstrings now say the same. Tests now assert
the real property: the casefolded excerpt **is** present in the saved file and the full body
(opening context and tail) is absent.

**Test evidence:** `test_saved_file_stores_only_the_body_excerpt_never_the_full_body` and the
updated CLI saved-run test (`document body` present; `Introductory context` and
`evaluation on a personal corpus` absent; no `content`/`body`/`snippet` keys).

**Note:** `18-SECURITY.md` (T-18-04/T-18-15 wording) was not edited because the task's hard
constraints forbid changing `.planning/` artifacts other than this report. The public docs and
code now state the actual behavior; the security register wording should be reconciled in a
planning-artifact update outside this fix run.

### WR-06: The noise gate can warrant a defaults change from one query, below its own noise floor

**Files modified:** `src/sif/search/personal_bench.py`, `tests/unit/search/test_personal_bench.py`, `docs/benchmarking.md`
**Commit:** `e932fce`

**Applied fix:** `noise_gate` now requires all of: `N >= SUPPRESS_BELOW` for a non-empty
`sufficient` gate, a CI excluding zero, the rounded 0.01 tie rule, and an **absolute mean delta
strictly above the displayed `1/N` noise floor**. `sufficient` is false below 10 paired queries;
such gates remain visible as diagnostics but can never set `winner`/`regression` or
`warrants_default_change`. The docs' gate description was updated to match.

**Test evidence:** one-record held-out comparison now expects no winner/warrant;
`test_nine_paired_queries_cannot_win_but_ten_can`;
`test_mean_delta_at_the_noise_floor_never_wins` (N=100, equality is not strictly above);
`test_mean_delta_below_the_noise_floor_never_wins` (the review's N=25 example); and the
exactly-0.01 adjacency test now uses N=200 (floor 0.005), where a 0.01 delta legitimately clears
both the tie rule and the floor.

**Contract note:** the 18-03 plan's "exactly 0.01 with CI excluding zero declares a winner"
adjacency is preserved where the mean delta is above the noise floor; at small N the displayed
floor now genuinely vetoes the win, which is the WR-06 fix the review requested.

### WR-07: `retrieval: "hybrid"` reported without verifying the index has vectors

**Files modified:** `src/sif/cli/commands/eval.py`, `tests/unit/cli/test_eval.py`, `docs/benchmarking.md`
**Commit:** `086f530`

**Applied fix:** Added `_has_scoped_embeddings` (a cheap `LIMIT 1` probe, collection-scoped when a
scope is given) and `_require_scoped_embeddings`. Both fresh and compare hybrid paths fail with a
`sif index embed` / `--bm25-only` remedy before loading the embedder or running any search when the
scoped index has no vectors; the run can no longer label BM25 results as hybrid.

**Test evidence:** `test_hybrid_run_on_a_non_embedded_index_fails_with_the_embed_remedy` (vectors
deleted from the real fixture; exit 1 with the remedy, no search executed) and
`test_bm25_only_runs_on_a_non_embedded_index` (explicit BM25 path still succeeds and reports
`bm25`).

### WR-08: The overlap budget is blind to CJK title echoes

**Files modified:** `src/sif/search/personal_bench.py`, `tests/unit/search/test_personal_bench.py`
**Commit:** `845962e`

**Applied fix:** Added `_budget_units`, which compares CJK runs as character bigrams (single
characters for one-character runs) plus ASCII tokens; `apply_overlap_budget` now uses it. Whole-run
`token_set` tokenization is unchanged for FTS matching.

**Test evidence:** `test_cjk_title_prefix_body_candidate_is_rejected` (title
`如何配置混合搜索引擎的权重`, candidate `如何配置混合搜索引擎` → reject) and
`test_paraphrased_cjk_body_candidate_is_kept`
(`如何调整混合检索系统的参数` → kept), plus a pin that `token_set` still keeps whole CJK runs.

### WR-09: Several failure paths escape the CLI's `ClickException` contract

**Files modified:** `src/sif/cli/commands/eval.py`, `tests/unit/cli/test_eval.py`
**Commit:** `9316758`

**Applied fix:** `run_personal` wraps collection resolution + metadata loading in
`except (sqlite3.Error, OSError)`; `_run_fresh` translates `ensure_heldout` sqlite/OS errors;
`_load_embedder` wraps the model-info/probe identity resolution in its own translation boundary;
and the cache-directory resolution/mkdir already moved inside `_save_run`'s `try` under WR-02.

**Test evidence:** `test_metadata_load_sqlite_error_is_a_click_exception`,
`test_heldout_sqlite_error_is_a_click_exception`,
`test_cache_dir_oserror_is_a_click_exception`, and
`test_embedder_probe_failure_is_a_click_exception`; each asserts exit 1, the cause text, and no
traceback.

### WR-10: The remote-provider disclosure omits replay history and provenance

**Files modified:** `src/sif/cli/commands/eval.py`, `tests/unit/cli/test_eval.py`, `docs/benchmarking.md`
**Commit:** `aea961c`

**Applied fix:** Both the stderr notice and the report note now name the actual data crossing the
boundary: document titles, body-sentence excerpts, and replay query history (when query history is
enabled), with `--bm25-only` as the local alternative. The benchmarking privacy narrative says the
same.

**Test evidence:** `test_remote_model_type_discloses_on_stderr_only` now asserts `document titles`,
`body-sentence excerpts`, and `replay query history` in both stderr and the JSON note, while
`test_bm25_only_prints_no_remote_disclosure` still pins the local path's silence.

## Skipped Issues

None for the in-scope findings.

IN-01 through IN-11 were deliberately left unfixed by explicit user instruction and remain open
in `18-REVIEW.md` and `18-REVIEW-DISPOSITION.md`; this report does not mark them fixed.

## Verification

All gates ran in the **main checkout** (`/Users/forrest/GitHub/SIF`, branch `dev`), not an isolated
worktree, per the task instruction. Results:

- Targeted tests after each fix (per-finding evidence above), then
  `env -u FORCE_COLOR NO_COLOR=1 python -m pytest`:
  **1882 passed, 1 skipped**, total coverage **95.17%** (required 90%).
- `ruff check src tests` — passed.
- `ruff format --check src tests` — 195 files already formatted.
- `ty check src/sif` — passed.
- `make docs-generate` followed by `git diff --exit-code -- docs/cli-reference.md docs/configuration.md`
  — clean (the WR-01 option-range change is already committed in the regenerated reference).
- `python scripts/generate_bench_fixture.py --check` — OK (151 fixture files match).
- All fixes committed with hooks enabled; no `--no-verify` and no uncommitted source changes.

---

_Fixed: 2026-11-15_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
