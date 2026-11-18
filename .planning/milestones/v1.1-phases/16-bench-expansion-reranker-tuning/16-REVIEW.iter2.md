---
phase: 16-bench-expansion-reranker-tuning
reviewed: 2026-11-08T15:59:23Z
depth: standard
files_reviewed: 30
files_reviewed_list:
  - src/sif/search/benchmark.py
  - src/sif/cli/commands/bench.py
  - src/sif/config/settings.py
  - src/sif/cli/commands/search.py
  - src/sif/search/rerank.py
  - src/sif/search/hybrid.py
  - scripts/generate_config_ref.py
  - scripts/generate_bench_fixture.py
  - tests/support/__init__.py
  - tests/support/bench.py
  - tests/fixtures/bench/queries.json
  - tests/fixtures/bench/heldout_defaults.json
  - tests/fixtures/bench/README.md
  - tests/unit/search/test_benchmark_metrics.py
  - tests/unit/search/test_bench_fixture.py
  - tests/unit/search/test_sweep.py
  - tests/unit/search/test_bench_snapshot.py
  - tests/unit/search/test_rerank.py
  - tests/unit/search/test_hybrid.py
  - tests/unit/inference/test_reranker.py
  - tests/unit/cli/test_bench.py
  - tests/unit/cli/test_search.py
  - tests/unit/cli/test_database_lifecycle.py
  - tests/unit/config/test_settings.py
  - tests/test_docs.py
  - docs/benchmarking.md
  - docs/search-algorithms.md
  - docs/api-reference.md
  - docs/configuration.md
  - docs/cli-reference.md
findings:
  critical: 1
  warning: 3
  info: 4
  total: 8
  necessity: 0
status: issues_found
---

# Phase 16: Code Review Report

**Reviewed:** 2026-11-08T15:59:23Z
**Depth:** standard
**Files Reviewed:** 30
**Status:** issues_found

## Summary

Phase 16 (bench expansion + reranker tuning) was reviewed at standard depth: all 30 listed source/test/doc files read, the git diff against `eea2bf0a` used to scope phase-introduced changes, and the phase gates re-executed (fixture drift gate `OK: 151 files`, generated `docs/configuration.md` byte-equal to generator output, targeted suites green: 75 + 13 + 117 + 182 tests passed under `env -u FORCE_COLOR NO_COLOR=1`).

All ten phase-critical properties in the review focus were verified to hold in the actual code:

1. `resolve_candidate_limit` (`src/sif/config/settings.py:399-415`) clamps on both the flag path (`-C 200` → 50, exercised end-to-end in `tests/unit/cli/test_search.py` and `tests/unit/cli/test_bench.py`) and the settings path; a non-int attr resolves to 20.
2. The rerank-off path constructs no reranker: `query_cmd` checks `rerank_requested = rerank or settings.rerank_enabled` before `create_reranker` (`src/sif/cli/commands/search.py:913-916`); bench's `_load_reranker` returns `None` before the factory call (`src/sif/cli/commands/bench.py:184-186`); pinned by `TestRerankOptIn` and `test_bench_off_only_json_states_additive_no_reranker`.
3. Over-fetch reaches both `self.hybrid.search(q, fetch_options)` (`src/sif/search/hybrid.py:244`) and the cross-query `rrf.fuse(all_results, fetch_options.limit, ...)` (line 255); `results[: options.candidate_limit]` slices the over-fetched set (line 259).
4. The relative-threshold filter is `pair[1] >= cutoff`, applied after the descending sort and before `[:top_k]`, in the single `_sort_and_build_results` shared by all three backends (`src/sif/search/rerank.py:43-48`).
5. `rank_sweep` uses `round(best - result.ndcg_at_10, 6) < epsilon` (`src/sif/search/benchmark.py:385`) on the tuning split only (held-out filtered in `_tuning_evaluator` before any search call); `winner_declared = len(tie_group) == 1`.
6. Off-only `bench --json` keeps every flat top-level key with `states` added alongside (`_render_report`, `src/sif/cli/commands/bench.py:408-413`).
7. The snapshot lock derives from `Settings(_env_file=None)` and asserts defaults equality and metric equality in one test (`tests/unit/search/test_bench_snapshot.py:190-214`); editing only the snapshot defaults fails.
8. `percentile` handles empty (0.0) and single-element inputs (`src/sif/search/benchmark.py:104-112`); both pinned.
9. Path-keyed relevance cannot escape `corpus_root`: `result_key` resolves and `relative_to`s, falling back to a non-matching full path on `ValueError`; relevance keys are never opened as files (verified `src/sif/search/benchmark.py:186-199`, plus `TestFixtureContractPaths`).
10. No new runtime dependencies: `pyproject.toml` untouched in the diff; new code uses stdlib + click/pydantic/rich only (numpy import in rerank.py is lazy and pre-declared).

The defects found are one machine-output contract violation on a supported degradation path (Critical), a botched test-file edit that deleted a class header (Warning), an environment-sensitive snapshot fixture (Warning), and a drift-gate/doc overstatement (Warning), plus four Info items.

## Critical Issues

### CR-01: Bench soft-fail warnings print to stdout and corrupt `--json` output

**File:** `src/sif/cli/commands/bench.py:41,108-110,189-197`
**Issue:** The module-level `console = Console()` writes to stdout. On the explicitly supported soft-fail paths — embedding backend not installed / model load failure (`_load_embedder`, lines 108/110) and reranker backend missing / model load failure (`_load_reranker`, lines 189-197, added this phase) — a Rich `[yellow]` warning is printed to **stdout** and then execution continues (exit 0) to emit the JSON payload via `click.echo`. Any `sif bench fixture.json --json | jq .` (the exact recipe in `docs/benchmarking.md` "Commands and Reproduction") fails to parse on these paths. The phase's own `_render_report` docstring claims "JSON goes through click.echo (never Rich) so it strict-parses" and the narrow-width tests pin strict parsing — but only against Rich *wrapping*, not stream separation. `src/sif/cli/commands/search.py:31-33` already established the correct contract for this exact problem ("D-07 stderr contract: refresh notices/warnings must never pollute stdout, which stays clean for --json/--csv piping") via `console_err = Console(stderr=True)`; bench was not given the same treatment, and the new `_load_reranker` warnings (used with the new `--rerank --json` mode) extend the violation. The `_load_embedder` half pre-exists at the diff base, but this phase both added new warning sites and made the strict-parse JSON contract central to the command. The existing tests cannot catch this: `test_bench_rerank_missing_backend_degrades_to_off_only` uses table mode, and CliRunner's `result.output` merges stdout and stderr anyway.
**Fix:**
```python
# src/sif/cli/commands/bench.py — mirror search.py's D-07 stderr contract
from rich.console import Console

console = Console()                    # table rendering (human mode only)
console_err = Console(stderr=True)     # warnings — never pollute --json stdout

# in _load_embedder / _load_reranker:
console_err.print(f"[yellow]Embedding backend not installed: {e}[/yellow]")
console_err.print(
    f"[yellow]Reranker backend not available, measuring the off state only: {e}[/yellow]"
)
```
Then add a test that runs `bench --json` with `create_reranker` raising `ImportError` and asserts `json.loads(result.stdout)` succeeds (CliRunner supports `mix_stderr=False`).

## Warnings

### WR-01: Deleted `class TestMachineOutputNoWrap:` header silently merges two test classes

**File:** `tests/unit/cli/test_search.py:1310-1349`
**Issue:** This phase's insertion of `TestRerankOptIn`/`TestCandidateLimitResolution` replaced the `class TestMachineOutputNoWrap:` line (see the diff hunk at old line ~1117): the deleted class's docstring now sits as an orphaned no-op string at line 1323 inside `TestCandidateLimitResolution`, and the entire former class body (`LONG_TEXT`, `LONG_PATH`, `_make_result`, `_invoke_query`, and its four machine-format tests) was silently absorbed into `TestCandidateLimitResolution`. Verified by collection: `pytest --collect-only` reports `TestCandidateLimitResolution::test_search_json_parses_at_narrow_width`, `::test_query_json_parses_at_narrow_width`, `::test_search_files_long_path_single_line`, `::test_search_csv_rows_single_line` — 8 tests under a class whose name promises only candidate-limit resolution. `grep -rn TestMachineOutputNoWrap` finds the class nowhere in the repo. Tests still run today, but the file structure is corrupted: the class boundary is gone, the docstring is dead code, and future edits (e.g. moving a helper, adding a class attribute, or `-m`/`-k` selection by class) will misfire. This is the same edit-accident family as the stray docstring at `tests/unit/inference/test_reranker.py:305` (pre-existing, see IN-02).
**Fix:** Re-insert the class header immediately before the orphaned docstring:
```python
        assert isinstance(options.candidate_limit, int)


class TestMachineOutputNoWrap:
    """Machine-format output must be byte-faithful regardless of width (CLI-JSON-WRAP).
    ...
    """
```
(i.e. restore line `class TestMachineOutputNoWrap:` above current line 1323 so the docstring and the absorbed members belong to their own class again).

### WR-02: Snapshot-lock fixture reads real environment variables — non-hermetic against `SIF_RRF_K`/`SIF_BM25_WEIGHT`/`SIF_VECTOR_WEIGHT`

**File:** `tests/unit/search/test_bench_snapshot.py:127-130,91-108`
**Issue:** `live_settings` builds `Settings(_env_file=None)` and the comment concedes "(mod env)". Unlike every hermetic sibling in `tests/unit/config/test_settings.py` (e.g. `test_fusion_defaults_match_prechange_behavior`, which `monkeypatch.delenv`s exactly these three vars), this module does not clear them. With any of `SIF_RRF_K`, `SIF_BM25_WEIGHT`, or `SIF_VECTOR_WEIGHT` exported in the developer/CI shell, `_assert_defaults_lock` fails with a message instructing the user to *regenerate* `tests/fixtures/bench/heldout_defaults.json` — actively misleading, since the correct remedy is to unset the env var — and `test_settings_default_change_without_metric_regeneration_fails` / `test_candidate_is_ranked_winner...` inherit the same sensitivity. This project has a documented history of environment-sensitive spurious test failures (FORCE_COLOR memory note), so this is a realistic flake source for the exact tests that gate shipped defaults.
**Fix:** Make the fixture hermetic with a module-scoped monkeypatch (or clear the vars in the fixture):
```python
@pytest.fixture(scope="module")
def live_settings(monkeypatch_session) -> Settings:
    for var in ("SIF_RRF_K", "SIF_BM25_WEIGHT", "SIF_VECTOR_WEIGHT", "SIF_RERANK_ENABLED"):
        monkeypatch_session.delenv(var, raising=False)
    return Settings(_env_file=None)
```
(`pytest.MonkeyPatch()` can be instantiated directly for a module-scoped hand-rolled fixture; alternatively pin the three knobs by constructing `Settings(_env_file=None, rrf_k=60, bm25_weight=1.0, vector_weight=1.0)` and asserting the *class defaults* equal those literals, which keeps the lock testing the shipped defaults rather than the shell.)

### WR-03: `--check` drift gate does not detect unexpected files outside `corpus/**/*.md`, but `docs/benchmarking.md` claims it does

**File:** `scripts/generate_bench_fixture.py:471-487` (claim: `docs/benchmarking.md:50`)
**Issue:** `check_pack()` flags missing/drifted expected files, but the unexpected-file scan only walks `out/corpus` with `rglob("*.md")`. A stray file at the pack root (e.g. `tests/fixtures/bench/notes.md`, or a leftover `corpus/keyword/extra.txt`) is silently accepted. `docs/benchmarking.md:50` states "The `--check` gate exits non-zero on any drift (**unexpected files included**)" — a verification guarantee the code does not provide. Since the drift gate's whole purpose is "snapshot drift can only come from code, never the pack", an undetected stray corpus file (which `build_bench_db` indexes via `rglob("*.md")` — actually no: build_bench_db walks `corpus_root`, so a root-level stray is inert, but a stray `.md` under `corpus/` silently changes every measured metric while `--check` stays green) can invalidate the committed evidence without any gate firing. Note `heldout_defaults.json` and `README.md` at the pack root are intentionally committed, so the scan cannot simply flag everything unexpected — it needs an allowlist.
**Fix:** Either strengthen the gate:
```python
ALLOWED_ROOT = {"queries.json", "heldout_defaults.json", "README.md"}
for path in sorted(out.iterdir()):
    rel = path.relative_to(out).as_posix()
    if rel not in expected and rel not in ALLOWED_ROOT:
        drift.append(f"unexpected: {rel}")
for path in sorted(corpus_dir.rglob("*")) if corpus_dir.is_dir() else []:
    if path.is_file() and path.suffix != ".md":
        drift.append(f"unexpected: {path.relative_to(out).as_posix()}")
```
— or soften the doc sentence to "unexpected `corpus/**/*.md` files included". Prefer the former; the corpus-stray case is a real evidence-integrity hole.

## Info

### IN-01: `_sort_and_build_results` drops `vectors_stale` when rebuilding SearchResult

**File:** `src/sif/search/rerank.py:52-66`
**Issue:** The rebuild passes `document_id ... context_description` but not `vectors_stale`, so any rerank resets the flag to its `False` default. Not a live bug on the pipeline path — `SearchPipeline.search` re-attaches staleness *after* reranking (`hybrid.py:269` → `mark_vector_staleness`, which sets unconditionally), and `vectors_stale` is `False` at rerank time anyway. But `reranker.rerank()` is a public API (documented in `docs/api-reference.md` / `docs/search-algorithms.md` "Implementation" examples that rerank already-attached results); any such caller silently loses stale-vector markers.
**Fix:** Add `vectors_stale=result.vectors_stale` to the `SearchResult(...)` construction in the rebuild loop.

### IN-02: Stray class docstring inside `TestCrossEncoderRerankerLoad` (pre-existing)

**File:** `tests/unit/inference/test_reranker.py:305`
**Issue:** A bare `"""Tests for CrossEncoderReranker reranking."""` sits mid-class after `test_download_failure_falls_back_to_model_id` — the `TestCrossEncoderRerankerRerank` class header it once introduced is missing, so the `test_rerank_*` methods below it live under the "Load" test class and the string is a dead no-op expression. Pre-existing at the diff base (not introduced by this phase), but it is the same accident family WR-01 proves is recurring in this repo; worth fixing while in the area.
**Fix:** Replace the bare string at line 305 with `class TestCrossEncoderRerankerRerank:` followed by the docstring.

### IN-03: `Qwen3Reranker.load` duplicates the whole model-loading body across quiet/non-quiet branches (pre-existing)

**File:** `src/sif/search/rerank.py:327-357`
**Issue:** The quiet and non-quiet branches repeat tokenization, model construction, device movement, and token-id setup verbatim; the only difference is the `suppress_output()` wrapper. Duplication in a file this phase modified (threshold plumbing) — a future edit to one branch (e.g. dtype or device policy) can silently miss the other. Pre-existing shape, retained through this phase's edits.
**Fix:** Extract a `_load_model(...) -> None` helper and call it once inside `if is_quiet(): with suppress_output(): ... else: ...`, or wrap only the load statements in a context manager selected by `is_quiet()`.

### IN-04: Benchmarking doc gaps: grade-1 legend missing; `SIF_RERANK_ENABLED=1` implied to enable bench rerank state

**File:** `docs/benchmarking.md:56,147-155`
**Issue:** (a) The grade legend says "3 = authoritative answer, 2 = supporting, 0 = a rival" but omits `1 = partial`, which the fixture README and `SearchEvaluator` accept — a hand-authored doc gap in an otherwise precise metric contract. (b) The "Rerank States" section opens with "Reranking is explicit opt-in and defaults off: pass `--rerank` **or set `SIF_RERANK_ENABLED=1`**", but `sif bench` honors only the `--rerank` flag (`_load_reranker(rerank, settings)` returns `None` whenever the flag is absent, ignoring `settings.rerank_enabled`, `src/sif/cli/commands/bench.py:184-186`); a user who exports `SIF_RERANK_ENABLED=1` and runs `sif bench --json` gets the off-only report with no warning. The sentence is accurate for `sif search query` but reads as bench guidance in this section.
**Fix:** (a) Add `1 = partial` to the legend. (b) Reword to scope the env-var sentence to `sif search query` and state that `sif bench` measures the on state only via `--rerank` (deliberate per D-12: bench is diagnostic and explicit).

---

Necessity review (`$HOME/.claude/gsd-core/references/necessity-review.md`) was read and applied. Zero necessity findings: the MagicMock-tolerance guards (`resolve_candidate_limit`'s non-int fallback, `create_reranker`'s non-numeric threshold fallback, `_state_metrics`' numeric check) were considered and **not** flagged — each guarded state is instantiated by committed tests exercising the production path (the project's documented "Pitfall 10" convention), so they defend against states that occur in this stack, and none qualifies as an impossible-state/already-defended finding.

Phase gates re-verified during review: `python scripts/generate_bench_fixture.py --check` → `OK: 151 files`; `docs/configuration.md` byte-equal to `scripts/generate_config_ref.py` output; targeted suites green (test_sweep + test_benchmark_metrics + test_bench_fixture: 75 passed; test_bench_snapshot: 13 passed; test_bench + test_settings + test_rerank + test_hybrid: 117 passed; test_search + test_database_lifecycle + test_docs: 182 passed).

_Reviewed: 2026-11-08T15:59:23Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
