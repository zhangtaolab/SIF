---
phase: 19-search-correctness
reviewed: 2026-11-27T10:21:11Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - docs/changelog.md
  - docs/cli-reference.md
  - docs/mcp-server.md
  - src/sif/cli/commands/search.py
  - src/sif/search/bm25.py
  - tests/test_docs.py
  - tests/unit/cli/test_search.py
  - tests/unit/cli/test_search_exact_threshold.py
  - tests/unit/search/test_bm25.py
  - tests/unit/search/test_filters_sql.py
findings:
  critical: 0
  warning: 1
  info: 1
  total: 2
  necessity: 0
status: issues_found
---

# Phase 19: Code Review Report

**Reviewed:** 2026-11-27T10:21:11Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Reviewed the Phase 19 second gap-closure round (plans 19-13, 19-14, 19-15) against
`b86da79`: the exact `--min-score` predicate in `BM25Searcher.search` (the displayed
score is computed in SQL from the same weighted `bm25()` expression that projects
`score`, with `min_score` bound as given; `bm25_rank_threshold` is removed), the
truthful `--min-score` help/reference/MCP/changelog text, and three guards.

The core change is correct. The predicate is one constant fragment feeding both SQL
branches, the parameter is bound after the collection ids and before the metadata
filter params (verified by `TestBm25ParamOrder`), values not above zero omit the
predicate (the NaN/`>= NULL` trap is avoided), and values of 1 or more keep nothing
because the displayed score is below 1 for any reachable bm25 value. Exactness is
corroborated twice: `test_sql_score_expression_matches_the_display_map_bit_for_bit`
checks SQLite's arithmetic against `bm25_display_score` on ~100k doubles, and
`bench/g19-8-exact-threshold.json` records 40 of 84 bench rows dropped at their own
displayed score before the fix and 0 after, with the one-ULP-adjacent sets unchanged.
The new CLI test round-trips the `--json` score through Click and pins the exact
row/set/rank, and the Markdown/XML and markup-bearing Chunk-cell guards are
mutation-gated by their own negative controls. No injection or other security issue
exists in the changed code: the predicate is constant and the threshold is bound.

Verification run: `ruff check src tests` and `ruff format --check src tests` clean;
`tests/test_docs.py`, `tests/unit/search/test_bm25.py`,
`tests/unit/search/test_filters_sql.py`, `tests/unit/cli/test_search.py`,
`tests/unit/cli/test_search_exact_threshold.py`, `tests/unit/search/test_hybrid.py`,
`tests/unit/search/test_vector.py`, and the docs/hygiene/release-metadata tests all
pass. `ty check src/sif` reports one diagnostic in `src/sif/embedding/embedder.py:850`
(`embed()` returning numpy scalars), which is pre-existing and outside this diff.

No necessity findings: the NaN branch is reachable (Click's FLOAT accepts
`--min-score nan`), and `SearchOptions` is a library API where a computed NaN
threshold is legitimate.

The two findings below are both in the new changelog text; the code itself needs no
change. One is a contradiction a reader of a single release's notes will hit, the
other is an overbroad correction for a supported BM25-only route.

## Narrative Findings (AI reviewer)

### WR-01: The Unreleased changelog says `query --min-score` "keeps its behaviour" and then says the exact-score fix reaches its BM25 leg

**File:** `docs/changelog.md:24`
**Issue:** The new Unreleased `Changed` entry opens with "`sif search query
--min-score` keeps its behaviour", while the new Unreleased `Fixed` entry
(`docs/changelog.md:33`, same release) states "The same fix reaches MCP
`lex_search` and the BM25 leg of `sif search query --min-score` and of MCP
`query`." Relative to the last release (v1.2.4), the query behaviour is not
unchanged: `HybridSearcher.search` copies the caller's `min_score` into both
legs' fetch options (`src/sif/search/hybrid.py:121-128`), and
`BM25Searcher.search` now keeps a row whose displayed score equals the
threshold (`src/sif/search/bm25.py:114-117`). A 1.2.4 `sif search query` run
with `--min-score` equal to a row's displayed BM25 score could therefore drop
that row from the BM25 leg where the current tree keeps it — exactly the
G-19-8 defect the `Fixed` entry describes. The two entries give a reader
contradictory answers about whether `query --min-score` changed.
**Fix:** Scope the sentence to the unchanged part, e.g.:

```markdown
- `sif search query --min-score` keeps its per-leg filtering semantics — each leg
  keeps the matches whose own score reaches the value ... — and this release only
  says so in the help text; the exact-equality fix described under Fixed reaches
  the command's BM25 leg as well.
```

### IN-01: The conversion correction says subtract-from-1 holds for `search search` only, but a BM25-only `query` route behaves the same way

**File:** `docs/changelog.md:24`
**Issue:** The correction says the 1.2.4 advice "to convert a threshold written
against the old scores by subtracting it from 1 holds for `sif search search`
only; a `sif search query --min-score` value must not be converted, because the
same number is also the vector leg's threshold". That rationale only covers the
hybrid/vector routes. `sif search query lex:<terms>` routes to the BM25 leg
alone (`SearchPipeline.search`, `src/sif/search/hybrid.py:342-356`; prefix
parsing is on for the CLI), and a deployment with a `bm25` default search type
does the same (`src/sif/cli/commands/search.py:1330`,
`src/sif/search/hybrid.py:344-345`). On those supported routes no vector leg
runs, the same number is not a vector threshold, and the subtract-from-1
conversion applies exactly as it does to `sif search search` (MCP `query` with a
`lex:` prefix likewise). The blanket "must not be converted" is wrong for those
callers.
**Fix:** Qualify the correction to the hybrid route, e.g.:

```markdown
- ... holds for `sif search search` only, and for a hybrid `sif search query`;
  on that command do not convert a value that also thresholds the vector leg,
  because the vector similarity scale did not change. A `lex:`-prefixed query
  (or a `bm25` default search type) runs only the BM25 leg, so there the
  subtraction applies as it does for `sif search search`.
```

---

_Reviewed: 2026-11-27T10:21:11Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
