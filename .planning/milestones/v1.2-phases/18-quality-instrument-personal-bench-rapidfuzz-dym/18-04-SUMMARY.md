---
phase: 18-quality-instrument-personal-bench-rapidfuzz-dym
plan: 04
subsystem: search/quality
tags:
  - did-you-mean
  - rapidfuzz
  - indel
  - full-vocabulary
  - dependency-lock
  - architecture-docs

requires:
  - phase: 15-search-quality-configuration-hybrid-weights-query-suggestions
    provides: "SuggestionEngine vocabulary/DYM/probe contracts and the sif suggest CLI surface"
  - phase: 18-quality-instrument-personal-bench-rapidfuzz-dym
    provides: "18-01/18-02 personal-bench modules that the architecture narrative now indexes"
provides:
  - "rapidfuzz>=3.14.5,<4 as a hard runtime dependency with a py3.10/py3.11+ split lock"
  - "full-vocabulary rapidfuzz fuzz.ratio did-you-mean scan at the internal 75.0 cutoff"
  - "deterministic score desc -> term asc -> df desc ordering with limit=None candidate exhaustion"
  - "measured p50 and cutoff 70/75/80 recall evidence recorded for QUAL-01"
affects: []

tech-stack:
  added:
    - "rapidfuzz 3.14.5 (py3.10) / 3.14.6 (py3.11+)"
  patterns:
    - "Full-vocabulary similarity scan with an internal cutoff constant; no setting or CLI knob"
    - "limit=None for ranking tie-break visibility, then explicit sort and slice to n"
    - "Lock regeneration for a requires-python-split dependency fleet (3.14.5 vs 3.14.6)"

key-files:
  created: []
  modified:
    - pyproject.toml
    - uv.lock
    - src/sif/search/suggest.py
    - tests/unit/search/test_suggest.py
    - docs/architecture.md

key-decisions:
  - "rapidfuzz>=3.14.5,<4 is a hard runtime dependency (D-13): a missing import is a broken install, never a difflib fallback."
  - "Did-you-mean scans the full sorted vocabulary with process.extract(scorer=fuzz.ratio, limit=None, score_cutoff=75.0); the first-letter bucket, difflib, and _ratio are deleted (D-14/D-16)."
  - "Ordering is score desc -> term lexicographic asc -> document frequency desc; limit=None makes every above-cutoff candidate visible before the sort and the n-slice (D-15)."
  - "The 75.0 cutoff is inclusive (>=) with no epsilon; resturant -> restaur at exactly 75.0 is pinned by a test."
  - "The probe/hit contracts, prefix completions, and history ranking are byte-identical; every emitted suggestion still returns >= 1 hit (D-17)."
  - "The lock diff is additive only (212 insertions, 0 deletions); no unrelated version moved."

requirements-completed: [QUAL-01]

coverage:
  - id: D1
    description: "rapidfuzz>=3.14.5,<4 is declared in pyproject, uv.lock is regenerated with a py3.10 3.14.5 and py3.11+ 3.14.6 resolution, and the frozen sync resolves on every CI Python."
    requirement: QUAL-01
    verification:
      - kind: integration
        ref: "uv lock --check && uv sync --frozen --extra dev --extra embed --dry-run"
        status: pass
      - kind: other
        ref: "python -c \"import rapidfuzz; print(rapidfuzz.__version__)\" -> 3.14.6 on py3.13"
        status: pass
    human_judgment: false
  - id: D2
    description: "Did-you-mean scans the entire sorted vocabulary with rapidfuzz fuzz.ratio; the first-letter bucket and difflib are gone."
    requirement: QUAL-01
    verification:
      - kind: unit
        ref: "tests/unit/search/test_suggest.py#TestCoreBudget::test_full_vocab_dym_under_budget_on_60k_vocab"
        status: pass
      - kind: other
        ref: "rg -n 'difflib|_ratio' src/sif/search/suggest.py (no matches)"
        status: pass
    human_judgment: false
  - id: D3
    description: "First-letter typo recall, the exact-75.0 boundary, sub-cutoff exclusion, deterministic tie order, empty edges, and the SC2 at-least-one-hit contract are pinned by tests."
    requirement: QUAL-01
    verification:
      - kind: unit
        ref: "tests/unit/search/test_suggest.py#TestDidYouMean::test_first_letter_typo_is_recalled"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_suggest.py#TestDidYouMean::test_cutoff_boundary_includes_exactly_75"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_suggest.py#TestDidYouMean::test_cutoff_boundary_excludes_below_75"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_suggest.py#TestDidYouMean::test_equal_scores_order_by_term_and_are_stable"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_suggest.py#TestDidYouMean::test_empty_token_and_empty_vocab_return_no_matches"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_suggest.py#TestDidYouMean::test_every_suggestion_hits_as_query"
        status: pass
    human_judgment: false
  - id: D4
    description: "docs/architecture.md describes rapidfuzz full-vocabulary Indel scoring (fuzz.ratio, 0-100, cutoff 75.0), bounds CJK did-you-mean claims by the tokenizer, and indexes PersonalBench in Key Abstractions with a narrative sentence."
    requirement: QUAL-01
    verification:
      - kind: other
        ref: "docs/architecture.md sections 'Search Flow', 'Suggestions and Query History', 'Key Abstractions'"
        status: pass
    human_judgment: true
    rationale: "Architecture prose has no content assertion test; a reviewer must confirm the narrative matches the implementation and does not overclaim CJK recall."

duration: 8min
completed: 2026-11-14
status: complete
plan_head_before: 08a28f575330b37e7230fdc84c47e48eabc02f24
plan_head_after: 27c3d2f869ef9034da8761831f98017eaf8fe448
actuals:
  tokens: 2902
  tasks: 3
  commits: 3
---

# Phase 18 Plan 04: rapidfuzz Full-Vocabulary Did-You-Me (QUAL-01) Summary

**Did-you-mean now scores every out-of-vocab token against the full 73k-term FTS vocabulary with rapidfuzz's Indel ratio at an internal 75.0 cutoff (p50 1.51 ms), recalling first-letter typos the old difflib bucket never saw, with rapidfuzz locked as the v1.2 runtime dependency.**

## Performance

- **Duration:** 8 min (8m23s measured to the final code commit; metadata commit follows)
- **Started:** 2026-11-14T15:06:39Z
- **Completed:** 2026-11-14T15:15:02Z
- **Tasks:** 3 completed (Task 1's blocking-human package-legitimacy gate was approved before this continuation; Tasks 2 and 3 executed here)
- **Files modified:** 5 (0 created, 5 modified)
- **Estimate vs actual:** plan estimated 45,000 tokens; realized diff measured at 2,902 tokens (chars/4 over the `-U0` diff of pyproject/src/tests/docs, excluding the 212-line generated `uv.lock`), 3 commits.

## Accomplishments

- `rapidfuzz>=3.14.5,<4` is declared in `[project] dependencies` and `uv.lock` was regenerated by `uv lock` (never hand-edited): the diff is additive only (212 insertions, 0 deletions) and splits the resolution into rapidfuzz 3.14.5 for `python_full_version < '3.11'` and 3.14.6 for 3.11+, exactly the Phase 17 requires-python fleet pattern. `uv lock --check` and `uv sync --frozen --extra dev --extra embed --dry-run` both exit 0.
- `_close_matches` now calls `process.extract(token, self._terms, scorer=fuzz.ratio, limit=None, score_cutoff=_DYM_CUTOFF)` over the entire sorted vocabulary, sorts by `(-score, term, -df)`, and slices to `n`. The `±1` first-letter bucket, the `difflib` import, and the `_ratio` helper are deleted; `_probe`, `_hits`, `_retrievable`, `_dym_slots`, `_expand_variants`, prefix completions, and `_rank_history` are byte-identical (diff review).
- The first-letter recall hole is closed and pinned: `xuantum -> quantum` (Indel 85.7, first letters 7 codepoints apart) now returns a suggestion that hits; a spy on `rapidfuzz.process.extract` proves the choice list is the **whole** 66k-term synthetic vocabulary (`max(calls) == vocab_size`), not a bucket.
- Cutoff and determinism contracts are pinned: `resturant -> restaur` is included at exactly 75.0 (`>=`, no epsilon), a 60.0 pair is excluded, equal-score matches order term-ascending and repeat identically, and empty token/vocabulary return `[]` instead of raising `IndexError`.
- The SC2 contract holds: every emitted DYM variant still flows through `_hits`/`_probe` and returns at least one real BM25 hit; the existing cross-document zero-hit test still passes.
- `docs/architecture.md` now describes rapidfuzz full-vocabulary Indel scoring (`fuzz.ratio`, 0-100, cutoff 75.0) instead of first-letter bucketing, explicitly bounds CJK did-you-mean recall by the FTS tokenizer (no ZH improvement claimed), and adds a `PersonalBench` Key Abstractions row plus a search-quality narrative sentence naming `sif/search/personal_bench.py`.

## Measured Evidence (QUAL-01)

**p50 of the core DYM call** — `SuggestionEngine._close_matches`, one full-vocabulary `process.extract` per out-of-vocab token, 200 first-letter typos, after 20 warm-up calls:

| Environment | Vocabulary | p50 | p95 | Mean |
|---|---|---|---|---|
| rapidfuzz 3.14.6, Python 3.13.9, macOS arm64 | 73,040 synthetic terms | **1.513 ms** | 1.629 ms | 1.514 ms |
| same | committed bench vocabulary (422 porter stems) | 0.007 ms | — | — |

This is within the RESEARCH 3.14.5 measurement (~1.70 ms at 72,999 terms) and comfortably inside the plan's <=10 ms core budget; the automated guard asserts elapsed < 1.0 s and the full-vocabulary choice count.

**Cutoff 70/75/80 first-letter recall@3 from 18-RESEARCH.md (the pinned decision table):**

| Vocabulary | Cutoff 70 | Cutoff 75 | Cutoff 80 | Old `±1` bucket |
|---|---|---|---|---|
| Committed bench corpus (422 porter stems) | 0.965 (1.27 sugg/q) | **0.965 (1.10)** | 0.789 (0.84) | 0.965 (same-first-letter only) |
| Synthetic 73k terms | 1.000 (1.47) | **1.000 (1.00)** | 1.000 (1.00) | 1.000 (same-first-letter only) |
| Committed bench corpus, **first-letter typos** | 1.000 | **1.000** | 0.813 | **0.070** |

**Local confirmation on rapidfuzz 3.14.6** (committed bench vocabulary, 363 collision-free first-letter substitutions): cutoff 70 = 0.956 (1.22 sugg/q), cutoff 75 = 0.956 (1.07), cutoff 80 = 0.799 (0.84), old `±1` bucket = 0.000. The exact rates shift with the typo generator, but the decision direction is identical: 70 adds candidates without recall, 80 loses recall, 75 is the high-recall point with the fewest candidates. One synthetic-generator caveat: a 73k all-numeric vocabulary has many equal-score near-neighbors, which caps top-3 recall regardless of cutoff (a tie artifact, not a cutoff effect), so the cutoff decision rests on the committed-bench and RESEARCH typo batteries.

## TDD Cycle

- **RED** (`965f6cc`, `test(18-04)`): added the full-vocabulary spy, `xuantum -> quantum`, exact-75.0 and sub-cutoff boundaries, tie stability, empty-token/vocabulary, and SC2 tests against the old difflib implementation. The target tests failed on the planned behaviors: `did_you_mean("xuantum")` returned `[]` instead of `["quantum"]`, `_close_matches("")` raised `IndexError: string index out of range`, and the spy recorded no `process.extract` calls (`assert []`). 3 failed, 29 passed.
- **GREEN** (`27c3d2f`, `feat(18-04)`): implemented the full-vocabulary rapidfuzz scan and updated the architecture narrative. Targeted suite: 47 passed (`tests/unit/search/test_suggest.py` + `tests/unit/cli/test_suggest.py`).
- **REFACTOR:** none needed — the diff is 30 insertions / 21 deletions, exactly the imports, constant, `_close_matches`, and `_ratio` removal; no cleanup commit.

## Task Commits

Each task was committed atomically with normal hooks (no `--no-verify`):

1. **Task 2: rapidfuzz dependency and regenerated lock** - `70a5278` (feat)
2. **Task 3 RED: failing full-vocab did-you-mean tests** - `965f6cc` (test)
3. **Task 3 GREEN: full-vocabulary rapidfuzz `_close_matches` + docs** - `27c3d2f` (feat)

Task 1 was a `checkpoint:human-verify` package-legitimacy gate (no code change, no commit); the user approved `rapidfuzz>=3.14.5,<4` before this continuation.

**Plan metadata:** `docs(18-04): complete rapidfuzz did-you-mean plan` (the commit following this SUMMARY)

## Files Created/Modified

- `pyproject.toml` - `[project] dependencies` gains `"rapidfuzz>=3.14.5,<4"`; no other entry reordered or pinned.
- `uv.lock` - regenerated by `uv lock`; add-only diff with 3.14.5 (<3.11) and 3.14.6 (>=3.11) resolution markers.
- `src/sif/search/suggest.py` - `_DYM_CUTOFF = 75.0`, rapidfuzz imports, rewritten `_close_matches`; `difflib`, `_ratio`, and the first-letter bucket removed.
- `tests/unit/search/test_suggest.py` - full-vocabulary spy, first-letter recall, cutoff boundaries, tie stability, empty edges; difflib spy removed.
- `docs/architecture.md` - SuggestionEngine narrative + Key Abstractions row describe rapidfuzz Indel scoring; CJK bound documented; `PersonalBench` row and search-quality narrative sentence added.

## Decisions Made

- Kept `limit=None` because the installed rapidfuzz accepts it; this returns every above-cutoff candidate, making the documented df tie-break real and the sort/slice explicit. No `limit=len(terms)` fallback was needed.
- The `_DYM_CUTOFF` comment records the measured range (0.799-0.813 at 80 vs 0.956-1.000 at 75, with 70 adding candidates and no recall) rather than an absolute 100%, so the recorded evidence cannot overclaim a generator-specific rate.
- Tests assert membership/order and the exact-75.0 Indel arithmetic via `pytest.approx`; no rapidfuzz version is asserted (3.14.5 on py3.10 and 3.14.6 on 3.11+ must both pass).

## Deviations from Plan

None - plan executed exactly as written. No auto-fixed issues, no Rule 4 decisions, no blocked work.

## Issues Encountered

- The PATH Python (miniconda 3.13.9) did not have rapidfuzz; the plan's documented local dev install (`python -m pip install -e ".[dev]"`) added rapidfuzz 3.14.6 and re-installed the editable package, after which the import check and tests ran. The lock remains the CI source of truth.
- `uv sync --frozen --extra dev --extra embed --dry-run` reports incidental install/uninstall plans for the existing `.venv` (stale dev extras such as black/mypy), but exits 0 and resolves rapidfuzz 3.14.6; this is the plan's required verification, not a lock drift.
- The synthetic all-numeric 73k vocabulary produces equal-score near-neighbors that cap top-3 recall at ~0.875-0.900 independent of cutoff. That is a synthetic-tie artifact (rapidfuzz breaks ties by choice index); the cutoff decision evidence therefore uses the committed-bench typo battery, matching 18-RESEARCH.md.

## User Setup Required

None - no external service configuration required. The package-legitimacy checkpoint was approved by the user on 2026-11-14 (PyPI 3.14.5 MIT, `requires_python >=3.10`; repository `github.com/rapidfuzz/RapidFuzz`).

## Threat Surface Scan

No new security-relevant surface beyond the plan's threat model. Mitigations verified: T-18-11 (blocking human package-legitimacy gate, locked range, `uv lock --check`, frozen sync), T-18-12 (`score_cutoff=75.0` bounds candidates; measured p50 1.51 ms at 73k terms; automated generous wall bound), T-18-13 (every emitted variant still flows through `_hits`/`_probe`; SC2 test retained), T-18-14 (no new output surface; the CLI's truncate-then-escape convention is untouched). No content, paths, or query text is newly persisted or transmitted.

## Next Phase Readiness

- QUAL-01's implementation, packaging, and evidence are complete; Phase 18 now has all four plans (18-01/18-02/18-03 EVAL-01/EVAL-02, 18-04 QUAL-01).
- The next step is phase-level verification (`/gsd-verify-work 18`) and then the Phase 19 entry. No blockers.
- Final gates: full pytest 1,751 passed / 1 skipped at 95.09% coverage (fail_under 90), `ruff check src tests` and `ruff format --check src tests` clean, `ty check src/sif` clean, `uv lock --check` and the frozen dry-run green.

## Self-Check: PASSED

- FOUND: pyproject.toml
- FOUND: uv.lock
- FOUND: src/sif/search/suggest.py
- FOUND: tests/unit/search/test_suggest.py
- FOUND: docs/architecture.md
- FOUND: 70a5278 (Task 2)
- FOUND: 965f6cc (Task 3 RED)
- FOUND: 27c3d2f (Task 3 GREEN)

---
*Phase: 18-quality-instrument-personal-bench-rapidfuzz-dym*
*Completed: 2026-11-14*
