---
phase: 16-bench-expansion-reranker-tuning
fixed_at: 2026-11-08T16:24:19Z
review_path: .planning/phases/16-bench-expansion-reranker-tuning/16-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 16: Code Review Fix Report

**Fixed at:** 2026-11-08T16:24:19Z
**Source review:** `.planning/phases/16-bench-expansion-reranker-tuning/16-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (fix_scope `critical_warning`: CR-01, WR-01, WR-02, WR-03)
- Fixed: 4
- Skipped: 0

The four Info findings (IN-01..IN-04) are out of scope for this iteration and remain
in REVIEW.md for disposition by the human.

## Fixed Issues

### CR-01: Bench soft-fail warnings print to stdout and corrupt `--json` output

**Files modified:** `src/sif/cli/commands/bench.py`, `tests/unit/cli/test_bench.py`
**Commit:** `7d5d788` (+ format follow-up `77e6511`)
**Applied fix:** Mirrored `search.py`'s D-07 stderr contract in `bench.py`: added a
module-level `console_err = Console(stderr=True)` and routed all four soft-fail
warning sites to it (`_load_embedder`'s ImportError/generic handlers and
`_load_reranker`'s ImportError/generic handlers). `console` remains for human-mode
table rendering. Added two pinning tests: `test_bench_rerank_missing_backend_warning_stays_off_json_stdout`
(runs `bench --rerank --json` with `create_reranker` raising ImportError; asserts
`json.loads(result.stdout)` succeeds, the warning is absent from stdout and present
on stderr) and `test_bench_embedder_soft_fail_warning_stays_off_json_stdout`
(same contract for the embedder ImportError path). Click 8.3.2 captures
`result.stdout`/`result.stderr` separately by default, so no `mix_stderr` was needed;
existing degradation tests keep passing because `result.output` remains the merged
stream.

### WR-01: Deleted `class TestMachineOutputNoWrap:` header silently merges two test classes

**Files modified:** `tests/unit/cli/test_search.py`
**Commit:** `3562dac`
**Applied fix:** Re-inserted `class TestMachineOutputNoWrap:` immediately above the
orphaned docstring (old line 1323), restoring the class boundary: the docstring,
`LONG_TEXT`/`LONG_PATH`, `_make_result`, `_invoke_query`, and the four machine-format
tests again belong to their own class. Verified via `pytest --collect-only`:
`TestCandidateLimitResolution` collects exactly its 4 candidate-limit tests and
`TestMachineOutputNoWrap` exactly its 4 machine-format tests (8 tests run, all pass).

### WR-02: Snapshot-lock fixture reads real environment variables — non-hermetic

**Files modified:** `tests/unit/search/test_bench_snapshot.py`
**Commit:** `62aeacb`
**Applied fix:** Made the module-scoped `live_settings` fixture hermetic: it now runs
inside `pytest.MonkeyPatch.context()` and `delenv`s `SIF_RRF_K`, `SIF_BM25_WEIGHT`,
`SIF_VECTOR_WEIGHT` (the same three vars and convention as
`tests/unit/config/test_settings.py::test_fusion_defaults_match_prechange_behavior`)
before constructing `Settings(_env_file=None)`, yielding the settings and undoing the
deletions at module teardown. Verified by running the module with all three vars
hostile-exported (`SIF_RRF_K=100 SIF_BM25_WEIGHT=2.0 SIF_VECTOR_WEIGHT=0.5`):
all 13 tests pass, where the defaults lock previously would have failed with a
misleading regenerate message.

### WR-03: `--check` drift gate does not detect unexpected files outside `corpus/**/*.md`

**Files modified:** `scripts/generate_bench_fixture.py`, `tests/unit/search/test_bench_fixture.py`
**Commit:** `f3a9700`
**Applied fix:** Took the preferred evidence-integrity direction (gate strengthened;
`docs/benchmarking.md:50` claim left unchanged and now true). `check_pack()` now
scans every file under the pack root recursively and flags anything not generator-
expected and not in the new `ALLOWED_EXTRA_FILES` allowlist (`heldout_defaults.json`,
`README.md` — the intentionally committed pack-root files). This subsumes the old
`corpus/**/*.md`-only scan and adds root-stray and non-.md-under-corpus detection.
Note: the review's suggested snippet iterated `out.iterdir()` and would have flagged
the `corpus` directory itself; the applied version walks files only (`path.is_file()`).
Added `TestCheckPackDriftGate` (5 tests): clean pack with allowlisted root files,
stray root file, stray non-`.md` under corpus, stray `.md` under corpus (the metric-
invalidating case), and the real committed pack passing the strengthened gate.
Verified end-to-end: `python scripts/generate_bench_fixture.py --check` → `OK: 151
files` (exit 0) on the committed pack, and a temp pack copy with `notes.md` +
`corpus/keyword/extra.txt` injected → both reported `unexpected:` and exit 1.

## Verification

All verification ran in the **main checkout** (`workflow.use_worktrees=false` in
`.planning/config.json` — no isolated worktree was created, so the numbers are
reproducible directly from this tree).

Per-fix: `ast.parse` syntax checks plus targeted suites (`tests/unit/cli/test_bench.py`
34 passed; `TestCandidateLimitResolution` + `TestMachineOutputNoWrap` 8 passed;
`tests/unit/search/test_bench_snapshot.py` 13 passed hostile-env and clean-env;
`tests/unit/search/test_bench_fixture.py` 29 passed).

Full quality suite after all fixes (main checkout):

- `ruff check src tests` — All checks passed
- `ruff format --check src tests` — 187 files already formatted
- `ty check src/sif` — All checks passed
- `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` — 1501 passed, 1 skipped,
  coverage 94.95% (90% required)
- `python scripts/generate_bench_fixture.py --check` — `OK: 151 files`, exit 0
- Generator-owned docs untouched (`docs/cli-reference.md`, `docs/configuration.md`);
  `docs/benchmarking.md` (hand-authored) needed no edit since the strengthened gate
  now matches its existing claim.

---

_Fixed: 2026-11-08T16:24:19Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
