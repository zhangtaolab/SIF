---
phase: 260905-kmv-fix-g-04-2-reranker-load-crash
plan: 01
type: execute
subsystem: search
tags: [reranker, modelscope, cli, error-handling, uat-gap]
requires:
  - "Qwen/Qwen3-Reranker-0.6B downloaded from ModelScope (already on disk from UAT test 2 attempt)"
provides:
  - "_resolve_model_dir(downloaded) config-aware model-dir resolver shared by Qwen3Reranker and CrossEncoderReranker"
  - "query_cmd converts pipeline.search RuntimeError into one-line ClickException (exit 1)"
affects:
  - "UAT 04 test 2 (real-model reranking quality, SC 1) — unblocked; rerun via /gsd-verify-work 04 resume"
tech-stack:
  added: []
  patterns:
    - "Config-qualification pass (config.json model_type key) + weights-file fallback + root final fallback for download-dir resolution"
key-files:
  created:
    - tests/unit/search/test_rerank.py
  modified:
    - src/sif/search/rerank.py
    - src/sif/cli/commands/search.py
    - tests/unit/cli/test_search.py
decisions:
  - "Model-dir resolution is a two-pass module-level helper: config-based qualification (root first, then sorted subdirs), weights-file fallback, root final fallback — never returns None"
  - "json.load guarded against OSError/JSONDecodeError and non-dict parse results so aux/corrupt configs (1_LogitScore) simply do not qualify"
  - "query_cmd except clause stays narrow to RuntimeError; all other exceptions still propagate uncaught"
metrics:
  duration: 3min
  completed: "2026-09-05"
  tests_added: 9
  tests_total: "617 passed, 11 skipped, 0 failed"
status: complete
actuals:
  tokens: 20500
  tasks: 3
  commits: 4
---

# Quick Task 260905-kmv: Fix G-04-2 reranker load crash (ModelScope model dir) Summary

One-liner: Config-aware `_resolve_model_dir` resolver (root before aux subdirs, weights fallback, never None) fixes the Qwen3-Reranker ModelScope load crash, and `query_cmd` now surfaces pipeline RuntimeErrors as one-line ClickExceptions.

## What Changed

### Task 1: Model-dir resolver in rerank.py + regression tests

- `src/sif/search/rerank.py` — added `import json` and module-level `_resolve_model_dir(downloaded: Path) -> Path` next to `_sort_and_build_results`. Candidates in deterministic order (download root first, then immediate subdirs sorted by name). Pass 1 returns the first candidate whose `config.json` parses into a dict containing `model_type` (guarded against `OSError`, `json.JSONDecodeError`, and non-dict results — this is what disqualifies `1_LogitScore/` whose 57-byte config holds only token ids). Pass 2 returns the first candidate containing a `*.safetensors` or `*.bin` file. Final fallback returns the download root unchanged.
- Both `Qwen3Reranker.load()` and `CrossEncoderReranker.load()` now assign `local_path = str(_resolve_model_dir(downloaded))`; the `subdirs[0]` heuristic is gone from the file (grep-verified).
- `tests/unit/search/test_rerank.py` — new file, 7 tests against `tmp_path` mocks of the ModelScope layout: root-with-aux resolves to root, qualifying subdir (`2_Weights`) beats sorted order, root weights fallback, subdir weights fallback, empty dir returns root (never None), invalid-JSON root config skipped without raising, non-dict JSON config does not qualify.

### Task 2: query_cmd wraps pipeline RuntimeError as ClickException + CLI test

- `src/sif/cli/commands/search.py` — wrapped only the `results = pipeline.search(query, options)` statement in `query_cmd` in `try/except RuntimeError` raising `click.ClickException(str(e)) from e`, mirroring the embedder-load pattern above it. The call stays inside the `with db.connection:` block; the except clause is not widened; output-rendering branches untouched.
- `tests/unit/cli/test_search.py` — new `TestQueryPipelineErrorHandling` class following the `TestSnippetDisplay` scaffold: RuntimeError("Reranking failed: boom") yields exit code 1 with "Error:" and "Reranking failed" in output and no RuntimeError in `result.exception`; ValueError still propagates uncaught.

### Task 3: Full quality suite gate

- `ruff check src tests` — clean.
- `ruff format --check src tests` — 128 files already formatted.
- `env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q` — **617 passed, 11 skipped, 0 failed**.
- No fallout required fixing; no unrelated files touched.
- Structure check (plan verification item 3): `create_reranker`, `Qwen3Reranker.load`, `CrossEncoderReranker.load`, `LlamaCppReranker.load` signatures unchanged; cumulative src diff is exactly the json import, the new helper, the two `local_path` assignments, and the one try/except in `query_cmd`.

## TDD Gate Compliance

Both implementation tasks followed RED -> GREEN with separate commits:

1. `ed542f4` — test(260905-kmv): resolver tests fail on import (RED, verified: ImportError)
2. `bdb4cce` — feat(260905-kmv): resolver implementation, 7/7 tests pass (GREEN)
3. `3e7b9b9` — test(260905-kmv): CLI wrapping test fails pre-fix (RED, verified: Test 1 failed, Test 2 narrowness guard passed by design)
4. `0831f41` — feat(260905-kmv): ClickException wrap, 20/20 file tests pass (GREEN)

## Commits

| Hash | Type | Subject |
|------|------|---------|
| ed542f4 | test | add failing tests for reranker model-dir resolver |
| bdb4cce | feat | resolve reranker model dir via config-aware resolver |
| 3e7b9b9 | test | add failing test for query_cmd pipeline error wrapping |
| 0831f41 | feat | wrap pipeline.search RuntimeError as ClickException |

All commits are pathspec-scoped (`git commit -- <files>`); the user's staged `mypy.ini` deletion remains staged and untouched in the index.

## Test Results

| Suite | Result |
|-------|--------|
| tests/unit/search/test_rerank.py | 7 passed |
| tests/unit/cli/test_search.py | 20 passed (18 pre-existing + 2 new) |
| Full suite (`env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q`) | 617 passed, 11 skipped, 0 failed |

## Deviations from Plan

- **Test-count estimate:** the plan's Task 1 behavior listed 5 resolver tests; the implementation ships 7 (weights fallback and defensive parsing each got a second strengthening variant: subdir-weights resolution and non-dict JSON config). With the 2 CLI tests this makes 9 new tests total, so the full suite reads 617 passed rather than the plan's estimated 615. Coverage strengthening only — no behavior drift.
- **Task 3 fixes:** none needed; the suite was green on first run.

Otherwise the plan executed exactly as written.

## Known Stubs

None.

## Threat Surface

No new security-relevant surface beyond the plan's threat model. T-260905k-01 mitigated as specified (json.load guards, deterministic candidate order); T-260905k-02 accepted as specified (str(e) follows the existing CLI convention).

## Next Step (out of scope, per plan)

Re-verify UAT 04 test 2 via `/gsd-verify-work 04` resume: `sif search query <terms> --explain` with the already-downloaded Qwen/Qwen3-Reranker-0.6B should render results with reranker_score; then flip G-04-2 to resolved in 04-UAT.md.

## Self-Check: PASSED

- Files: tests/unit/search/test_rerank.py, src/sif/search/rerank.py, src/sif/cli/commands/search.py, tests/unit/cli/test_search.py — all FOUND.
- Commits: ed542f4, bdb4cce, 3e7b9b9, 0831f41 — all FOUND in git log.
