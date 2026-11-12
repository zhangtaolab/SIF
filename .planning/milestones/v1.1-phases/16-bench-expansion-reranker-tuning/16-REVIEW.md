---
phase: 16-bench-expansion-reranker-tuning
reviewed: 2026-11-08T16:33:03Z
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
  critical: 0
  warning: 0
  info: 6
  total: 6
  necessity: 0
status: issues_found
---

# Phase 16: Code Review Report (Re-review, Fix Iteration 2)

**Reviewed:** 2026-11-08T16:33:03Z
**Depth:** standard
**Files Reviewed:** 30
**Status:** issues_found (Critical/Warning tiers clear; 6 Info items, 4 carried forward)

## Summary

This is iteration 2 of the fix loop: a fresh standard-depth review of the current state of all 30 scoped files, with the five fix commits (7d5d788, 77e6511, 3562dac, 62aeacb, f3a9700) re-verified against the cited code rather than the fix report.

**All four blocking findings from the previous review (16-REVIEW.iter2.md) are genuinely resolved.** Each fix was independently reproduced, not just read:

1. **CR-01 (resolved):** `console_err = Console(stderr=True)` now exists at `src/sif/cli/commands/bench.py:44`, and all four soft-fail warning sites route through it — embedder `ImportError` (line 111), embedder generic `Exception` (line 113), reranker `ImportError` (line 192), reranker generic `Exception` (line 198). Two new tests pin stream separation on both degradation paths (`test_bench_embedder_soft_fail_warning_stays_off_json_stdout`, `test_bench_rerank_missing_backend_warning_stays_off_json_stdout`) using `result.stdout`/`result.stderr` — which under installed Click 8.3.2 are genuinely separate streams (verified: Click ≥8.2's `Result.output` mixes, `Result.stdout`/`Result.stderr` do not). `json.loads(result.stdout)` succeeds and the warning text is asserted absent from stdout and present in stderr.
2. **WR-01 (resolved):** `class TestMachineOutputNoWrap:` is restored at `tests/unit/cli/test_search.py:1324`. Verified two ways: `pytest --collect-only` shows exactly 4 tests under `TestMachineOutputNoWrap` and exactly 4 under `TestCandidateLimitResolution`, and an AST scan for orphaned docstrings (the WR-01/IN-02 accident family) across all 12 changed test/support files reports zero orphans in this file.
3. **WR-02 (resolved):** `live_settings` (`tests/unit/search/test_bench_snapshot.py:127-141`) is now a module-scoped generator using `pytest.MonkeyPatch.context()` to `delenv` `SIF_RRF_K`/`SIF_BM25_WEIGHT`/`SIF_VECTOR_WEIGHT` before constructing `Settings(_env_file=None)` inside the context (`Iterator` is imported at line 21). Reproduced live: the full snapshot module passes with `SIF_RRF_K=99` exported into the test environment — the exact spurious-failure scenario the finding described.
4. **WR-03 (resolved):** `check_pack` (`scripts/generate_bench_fixture.py:477-500`) now walks every file under the pack root via `out.rglob("*")` and flags anything not in `set(files) | ALLOWED_EXTRA_FILES` (`{"heldout_defaults.json", "README.md"}`), so stray root files and non-`.md` strays under `corpus/` are both caught. Five new tests cover clean-pack, stray root file, stray non-`.md` under corpus, stray `.md` under corpus, and the real committed pack; the doc claim at `docs/benchmarking.md:50` ("unexpected files included") is now true.

No new defects were introduced by the fixes: the CR-01 stream change touches only the warning sites, the WR-01 header insertion is placement-only, the WR-02 fixture is correctly scoped, and the WR-03 scan has no false positives against the real pack.

Phase gates re-executed during this review, all green: `python scripts/generate_bench_fixture.py --check` → `OK: 151 files`; `docs/configuration.md` byte-equal to `scripts/generate_config_ref.py` output; `ruff check` / `ruff format --check` / `ty check src/sif` all clean; full suite `env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q` → 1501 passed, 1 skipped, coverage 94.95%.

Remaining: the four Info findings from iteration 1 (out of fix scope) are still present and carried forward below at unchanged severity, plus two new Info-level stream-consistency notes found in this fresh pass (IN-05, IN-06). Nothing at Critical or Warning severity remains.

## Fix Verification Detail

| Prior ID | Status | Evidence |
|---|---|---|
| CR-01 | Fixed | `bench.py:44,111,113,192,198`; both new stderr-purity tests pass; Click 8.3.2 stream semantics confirmed |
| WR-01 | Fixed | `test_search.py:1324`; collection shows 4+4 tests in the correct classes; AST orphan scan clean |
| WR-02 | Fixed | `test_bench_snapshot.py:127-141`; module passes with `SIF_RRF_K=99` exported |
| WR-03 | Fixed | `generate_bench_fixture.py:471-500` + `TestCheckPackDriftGate` (5 tests); drift gate green on the committed pack |

## Info

### IN-01: `_sort_and_build_results` drops `vectors_stale` when rebuilding SearchResult (carried forward)

**File:** `src/sif/search/rerank.py:52-66`
**Issue:** The rebuild passes `document_id ... context_description` but not `vectors_stale`, so any rerank resets the flag to its `False` default. Not a live bug on the pipeline path — `SearchPipeline.search` re-attaches staleness after reranking (`hybrid.py:269` → `mark_vector_staleness`, which sets unconditionally) — but `reranker.rerank()` is a public API documented with usage examples in `docs/api-reference.md` and `docs/search-algorithms.md:319-332`; any such caller reranking already-attached results silently loses stale-vector markers.
**Fix:** Add `vectors_stale=result.vectors_stale` to the `SearchResult(...)` construction in the rebuild loop.

### IN-02: Stray class docstring inside `TestCrossEncoderRerankerLoad` (carried forward, pre-existing)

**File:** `tests/unit/inference/test_reranker.py:305`
**Issue:** A bare `"""Tests for CrossEncoderReranker reranking."""` sits mid-class after `test_download_failure_falls_back_to_model_id` — the `TestCrossEncoderRerankerRerank` class header it once introduced is missing, so the `test_rerank_*` methods below it live under the "Load" class and the string is a dead no-op expression. Confirmed still present by AST scan in this review (the only remaining orphan in the changed files). Same accident family as the (now-fixed) WR-01.
**Fix:** Replace the bare string at line 305 with `class TestCrossEncoderRerankerRerank:` followed by the docstring.

### IN-03: `Qwen3Reranker.load` duplicates the whole model-loading body across quiet/non-quiet branches (carried forward, pre-existing)

**File:** `src/sif/search/rerank.py:327-357`
**Issue:** The quiet and non-quiet branches repeat tokenization, model construction, device movement, and token-id setup verbatim; the only difference is the `suppress_output()` wrapper. A future edit to one branch (dtype or device policy) can silently miss the other.
**Fix:** Extract a `_load_model(...) -> None` helper and call it once, wrapping only the load statements in `suppress_output()` when `is_quiet()`.

### IN-04: Benchmarking doc gaps: grade-1 legend missing; `SIF_RERANK_ENABLED=1` implied to enable bench rerank state (carried forward)

**File:** `docs/benchmarking.md:56,147`
**Issue:** (a) Line 56 says grades are "3 = authoritative answer, 2 = supporting, 0 = a rival" but omits `1 = partial`, which the fixture README (`tests/fixtures/bench/README.md:44`) and `SearchEvaluator` both accept — the generator currently emits no grade-1 keys, so the gap is latent rather than wrong. (b) Line 147 opens the bench-facing "Rerank States" section with "pass `--rerank` **or set `SIF_RERANK_ENABLED=1`**", but `sif bench` honors only the `--rerank` flag (`_load_reranker` returns `None` whenever the flag is absent, ignoring `settings.rerank_enabled`, `src/sif/cli/commands/bench.py:187-188`); a user who exports the variable and runs `sif bench --json` gets the off-only report with no warning. The sentence is accurate for `sif search query` (and is correctly scoped there in `docs/search-algorithms.md:286-287`) but reads as bench guidance in this section.
**Fix:** (a) Add `1 = partial` to the legend. (b) Reword line 147 to scope the env-var alternative to `sif search query` and state that `sif bench` measures the on state only via `--rerank` (deliberate per D-12: bench is diagnostic and explicit).

### IN-05: `bench` no-index warning prints to stdout and exits 0 — `--json` consumers get non-JSON stdout with a success exit code (new this review, pre-existing line)

**File:** `src/sif/cli/commands/bench.py:617-619`
**Issue:** `if not index_path.exists(): console.print("[yellow]No index found...")` writes to **stdout** via the module-level `console` and returns with **exit code 0**, emitting no JSON. A `sif bench fixture.json --json | jq .` on such a machine feeds jq the Rich-formatted warning line; the pipeline exit status comes from jq's parse failure, not from sif. This is the same D-07 stream-contract family CR-01 addressed, on the one remaining stdout warning site in the command — but the line predates the phase diff base (present verbatim at base `eea2bf0a`), is the established pattern across every CLI command (`search.py:830-833` does the same for all trio commands), and is pinned as intended behavior by `test_bench_no_index` (`tests/unit/cli/test_bench.py:354-370`, asserts exit 0 + message in output). Info rather than Warning for those reasons; under Click ≥8.2 the existing test keeps passing even if the message moves to `console_err` (`result.output` mixes streams).
**Fix:** Route the notice through `console_err` and consider a non-zero exit (e.g. `raise click.ClickException(...)` or `ctx.exit(1)`) so machine consumers can detect the missing index without parsing stdout — as a codebase-wide follow-up, not a Phase 16 fix.

### IN-06: `query_cmd` reranker-unavailable degradation warning still targets stdout `console` (new this review, pre-existing line; currently unreachable in production)

**File:** `src/sif/cli/commands/search.py:917-922`
**Issue:** The `except ImportError` handler around `create_reranker` prints "Reranker not available. Install with..." via `console` (**stdout**), violating the module's own D-07 stderr contract (its `console_err` docstring at lines 31-33) if ever reached in a `--rerank --json` invocation. Today the branch is production-unreachable: `create_reranker` (`src/sif/search/rerank.py:424-463`) performs no eager optional-backend imports (all `sentence_transformers`/`llama_cpp`/`transformers` imports are lazy inside `load()`), so an ImportError can only be injected by the test seams at `tests/unit/cli/test_search.py:3070,3168,3299,3342`. It is a latent trap: the moment `create_reranker` gains an eager import, `sif search query --rerank --json` on a machine without the backend gets stdout pollution identical to CR-01.
**Fix:** Switch the `console.print(...)` at lines 919-922 to `console_err.print(...)` — a one-word change that aligns the defensive branch with the module's established contract before it can become live.

## Necessity Review

`$HOME/.claude/gsd-core/references/necessity-review.md` was read and applied. Zero necessity findings. Re-examined this iteration: the MagicMock-tolerance guards (`resolve_candidate_limit`'s non-int fallback, `create_reranker`'s non-numeric threshold fallback, `_state_metrics`' numeric check) each defend states that committed tests instantiate through the production path (the project's documented "Pitfall 10" test-seam convention — excluded from necessity by the rubric's test-seam carve-out), and no impossible-state, already-defended, cargo-culted, phantom, or single-instantiation generality was provable from the repository.

---

Phase gates re-verified during this review: drift gate `OK: 151 files`; `docs/configuration.md` byte-equal to generator output; `ruff check` + `ruff format --check` + `ty check src/sif` clean; full suite 1501 passed / 1 skipped, coverage 94.95% (`env -u FORCE_COLOR NO_COLOR=1`).

_Reviewed: 2026-11-08T16:33:03Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
_Iteration: 2 (re-review after CR-01/WR-01/WR-02/WR-03 fixes; all four confirmed resolved)_
