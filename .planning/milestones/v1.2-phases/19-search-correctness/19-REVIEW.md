---
phase: 19-search-correctness
reviewed: 2026-11-27T12:04:20Z
depth: standard
files_reviewed: 1
files_reviewed_list:
  - docs/changelog.md
findings:
  critical: 0
  warning: 0
  info: 0
  total: 0
  necessity: 0
status: clean
---

# Phase 19: Code Review Report

**Reviewed:** 2026-11-27T12:04:20Z
**Depth:** standard
**Files Reviewed:** 1
**Status:** clean

## Summary

Incremental re-review of `docs/changelog.md` after commit `5268218`, which rewrote the
Unreleased `Changed` bullet to fix the previous review's WR-01 (a "keeps its behaviour"
claim that contradicted the same release's `Fixed` entry) and IN-01 (a conversion
correction that said a `sif search query --min-score` value must never be converted,
ignoring the supported BM25-only routes). The rest of the tree is unchanged since the
previous review.

Both fixes are accurate, and no new issue was found.

**WR-01 resolved.** The new text scopes the unchanged part — "keeps its per-leg filtering
semantics" — defines that semantics (each leg filters on its own score; the fused hybrid
score is never compared), limits the release's claim to documenting it in the help text,
and then states that the exact-equality fix reaches the query command's BM25 leg as well.
That matches the code: `HybridSearcher.search` copies the caller's `min_score` into both
legs' fetch options (`src/sif/search/hybrid.py:121-128`, vector leg at `:136`), the fused
score is never compared with it (no `min_score` reference exists in `hybrid.py` after the
leg calls), and `BM25Searcher.search` keeps a row at exact equality
(`src/sif/search/bm25.py:114-117`), so relative to 1.2.4 the query command's BM25 leg did
change — which the entry now says. The previous contradiction is gone.

**IN-01 resolved.** The correction now says the subtract-from-1 advice applies to
`sif search search` and to routes that run the BM25 leg alone, naming a `lex:`-prefixed
`sif search query` and a `bm25` default search type, and separately says not to convert a
value that also thresholds the vector leg. Each branch matches the code:

- `lex:` maps to `SearchType.BM25` (`src/sif/search/hybrid.py:536,541-543`) and the
  pipeline's BM25 route calls `BM25Searcher.search` with the caller's options
  (`src/sif/search/hybrid.py:352-356`), so the exact predicate and the conversion apply.
- `default_search_type="bm25"` resolves to `SearchType.BM25`
  (`src/sif/search/hybrid.py:521-527`); the setting accepts only
  `bm25`/`vector`/`hybrid` (`src/sif/config/settings.py:384-393`), and the CLI query
  command passes it into `SearchPipeline` (`src/sif/cli/commands/search.py:1323-1332`).
- The MCP routes mirror this: `_split_query_prefix` maps `lex:` and a `bm25` default to
  BM25 (`src/sif/mcp/backend.py:131-147`) and the direct route calls `BM25Searcher`
  (`src/sif/mcp/backend.py:486-495`).
- The hybrid caution is correctly conditioned: on a hybrid query the same value rides
  `fetch_options` into both legs, and the vector score map did not change (`git diff
  v1.2.2..v1.2.4` is empty for `search/vector.py` and `search/hybrid.py`; the 1.2.4 entry
  also records `vsearch` as unchanged).

The remaining claims in the same bullet also check out: the vsearch help text names the
vector similarity (`src/sif/cli/commands/search.py:852-855`), and `docs/mcp-server.md`
names the filtered score for every MCP tool that accepts `min_score` — `query`
(`docs/mcp-server.md:134`), `lex_search` (`:188-190`) and `vec_search` (`:195-198`) — all
three of which are registered (`src/sif/mcp/tools.py:406-407`) and read
`min_score` (`src/sif/mcp/protocol.py:98,131,159`).

The Unreleased `Fixed` entry (unchanged by `5268218`) is corroborated by
`.planning/milestones/v1.2-phases/19-search-correctness/bench/g19-8-exact-threshold.json`:
40 of 84 rows were dropped at their own displayed score before the fix and 0 after; the
rank-1 probe score `0.8942969341194331` was dropped at `--min-score 0.8942969341194331`
before and kept after; the fixed-threshold counts (0.12/0.23/0.3/0.5/0.85/0.89) and the
one-ULP-adjacent sets are identical. The four-decimal claim is accurate for CSV, Markdown,
XML and the tables (`src/sif/cli/commands/search.py:520,547,576,800,1046,1426`), while
`--json` emits the raw float (`SearchResult.to_dict`, `src/sif/core/models.py:326-344`,
serialized at `src/sif/cli/commands/search.py:155-161`).

Verification run: `pytest tests/test_docs.py tests/test_release_metadata.py
tests/test_hygiene.py -q` — 51 passed (the run's coverage gate reports 29% only because a
subset of the suite ran; that is not a test failure).

No necessity findings. One residual nuance, not a defect: the hybrid sentence opts to
preserve the vector leg's unchanged scale, so a value originally written against old BM25
scores is not preserved by leaving it unconverted. The text does not claim otherwise — it
states the rationale (the vector similarity scale did not change) and remains conditional
on the value also thresholding the vector leg — so no contradiction or false statement
remains.

All reviewed files meet quality standards. No issues found.

---

_Reviewed: 2026-11-27T12:04:20Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
