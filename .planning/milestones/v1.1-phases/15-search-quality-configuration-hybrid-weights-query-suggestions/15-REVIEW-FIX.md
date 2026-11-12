---
phase: 15-search-quality-configuration-hybrid-weights-query-suggestions
fixed_at: 2026-11-08T11:08:36Z
review_path: .planning/phases/15-search-quality-configuration-hybrid-weights-query-suggestions/15-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 15: Code Review Fix Report

**Fixed at:** 2026-11-08T11:08:36Z
**Source review:** `.planning/phases/15-search-quality-configuration-hybrid-weights-query-suggestions/15-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 6 (CR-01, WR-01..WR-05)
- Fixed: 6
- Skipped: 0
- Out of scope (left open in the review): the seven INFO findings (IN-01..IN-07)

## Fixed Issues

### CR-01: DYM suggestions are never validated as a conjunction — emitted suggestions can return zero hits (SC2 violated)

**Files modified:** `src/sif/search/suggest.py`, `tests/unit/search/test_suggest.py`
**Commit:** 360a619
**Applied fix:** Added `SuggestionEngine._hits()`, which probes `documents_fts` with the searcher's own `_build_fts_query()` (the exact AND-of-quoted-prefix-phrases a real search runs). `did_you_mean()` now filters generated variants through that probe and drops zero-hit ones, so every emitted suggestion returns >= 1 hit (QUAL-02/SC2). Strengthened the SC2 pin with a cross-document fixture (`d1="alpha"`, `d2="beta"`; `"alphx beta"` -> `[]` because `"alpha beta"` hits nothing) plus a positive co-occurring test proving genuine corrections still emit (`d1="alpha beta"` -> `["alpha beta"]`). This is the SC2 pin change the task required.
**Note:** requires human verification of the logic (semantic fix; the test battery pins both directions).

### WR-01: `_retrievable` prefix-substring test is unsound — suppresses real corrections and invents spurious ones

**Files modified:** `src/sif/search/suggest.py`, `tests/unit/search/test_suggest.py`
**Commit:** 9988a45
**Applied fix:** Replaced the prefix-substring predicate with an index probe using the same `_probe()`/`_build_fts_query()` mechanism as CR-01 (the chosen mechanism: a token is retrievable only when the FTS MATCH for it returns >= 1 row; documented in the docstring). Porter stemming and prefix semantics now match the real search exactly. Removed the now-unused `_term_set`. Regression tests cover both demonstrated directions: (a) `resturant` with `rest` in the vocab now yields `["restaur"]` instead of `[]`, (b) `happy dog` with `happi` in the vocab yields `[]` instead of rewriting the valid word.
**Note:** requires human verification of the logic (semantic fix).

### WR-02: `sif suggest --limit` does not cap the "Did you mean" section

**Files modified:** `src/sif/search/suggest.py`, `src/sif/cli/commands/suggest.py`, `tests/unit/cli/test_suggest.py`
**Commit:** d6ffcda
**Applied fix:** Threaded `limit` through the DYM path: the CLI passes `engine.did_you_mean(query, limit)`; `_dym_slots()` forwards `n` to `_close_matches()`, which now uses `difflib.get_close_matches(..., n=n, cutoff=0.75)` instead of the hardcoded `n=3`. The `n=3` defaults remain for API compatibility. Test pins `--limit 1` -> one DYM entry and `--limit 10` -> all three available matches.

### WR-03: Docs still advertise the deleted `RRFFusion.fuse_with_weights` and deny the new knobs

**Files modified:** `docs/api-reference.md`, `docs/search-algorithms.md`
**Commit:** 2665db2
**Applied fix:** `docs/api-reference.md` now documents the current signature `fuse(results_lists, limit=10, weights=None, k=None)` (multiply form, never normalized, per-call `k`) and no longer lists `fuse_with_weights`; the usage example shows both the bit-identical default and a weighted call. `docs/search-algorithms.md` replaces the "no CLI or environment knob selects weights" claim with the delivered reality: `--bm25-weight`/`--vector-weight`/`--rrf-k`, `SIF_BM25_WEIGHT`/`SIF_VECTOR_WEIGHT`/`SIF_RRF_K`, the Python and MCP channels, and the precedence rule (flag/request > setting > default; only `query` exposes weights).

### WR-04: `docs/mcp-server.md` query tool contract not updated for the new params/response field

**Files modified:** `docs/mcp-server.md`
**Commit:** 8c38be0
**Applied fix:** Added `rrf_k` (integer >= 1), `bm25_weight` (number > 0), and `vector_weight` (number > 0) to the `query` parameter table with omitted-means-server-setting semantics, and added `"suggestions": []` to the response example with a note that it is populated only on zero-result responses (and every suggestion returns >= 1 hit when re-run).

### WR-05: `sif suggest --json` writes human text to stdout when the index is missing (and `-q` does not suppress it)

**Files modified:** `src/sif/cli/commands/suggest.py`, `tests/unit/cli/test_suggest.py`
**Commit:** b60251c
**Applied fix:** On the missing-index path the command now emits the documented empty three-array JSON document (`{"completions": [], "did_you_mean": [], "history": []}`) when `--json` is set, and only prints the human "No index found." notice when not quiet. A JSON consumer can always parse stdout. Tests pin the parseable-empty-document contract, absence of the human notice under `--json`, and `-q` suppression of the notice.

## Skipped Issues

None.

## Verification

**Where the gates ran:** the main checkout (`workflow.use_worktrees` is `false`, so per #2825 no isolated worktree was created — the fixes were edited and committed in the primary working tree).

- Full suite: `env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q` -> **1340 passed, 1 skipped**; coverage 94.82% (fail_under=90).
- Lint: `ruff check src tests` -> clean.
- Format: `ruff format --check src tests` -> 181 files already formatted.
- Types: `ty check src/sif` -> clean.
- Docs: `tests/test_docs.py` included in the full run (13 passed); generator-owned docs (`docs/cli-reference.md`, `docs/configuration.md`) were not touched (no `make docs-generate` needed).

---

_Fixed: 2026-11-08T11:08:36Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
