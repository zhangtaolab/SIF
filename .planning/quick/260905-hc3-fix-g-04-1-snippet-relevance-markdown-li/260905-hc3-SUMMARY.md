---
phase: 260905-hc3-fix-g-04-1-snippet-relevance
plan: 01
type: execute
status: complete
tags: [search, snippets, bm25, highlights, markdown, g-04-1]
key-files:
  created:
    - src/sif/search/term_match.py
    - tests/unit/search/test_term_match.py
  modified:
    - src/sif/search/snippets.py
    - src/sif/search/bm25.py
    - tests/unit/search/test_snippets.py
    - tests/unit/search/test_bm25.py
decisions:
  - "Lookaround boundaries (?<![a-z0-9])/(?![a-z0-9]) instead of \\b so snake_case segments match but table never matches inside notable"
  - "Window frontiers move monotonically outward so edge-trimmed structural lines are never re-added (termination + budget reuse)"
  - "context_radius kept stored-and-unused for API compat; line-aware windows size by max_length alone"
metrics:
  duration: 9min
  completed: 2026-09-05T04:47:40Z
actuals:
  tokens: 7978   # 31912 diff chars / 4
  tasks: 3
  commits: 4
requires: [G-04-1]
provides: [stem-tolerant-term-matching, markdown-line-aware-snippets]
---

# Quick Task 260905-hc3: Fix G-04-1 Snippet Relevance (markdown line-aware + stem-tolerant matching) Summary

**One-liner:** Shared stem-tolerant term matcher (term_match.py) + line-aware SmartSnippetExtractor rewrite + BM25 highlight routing through it — snippets now center on the matched table row / code line, stem variants highlight, notable/table false positives die, CJK gets per-character fallback.

## What Changed Per Task

### Task 1: Shared stem-tolerant, word-boundary term matcher (TDD) — commits a4887de (RED), 2d99c86 (GREEN)

- New `src/sif/search/term_match.py`: `term_matches`, `count_matches`, `distinct_terms_matched`, `find_first_match` — all case-insensitive, backed by a single `@lru_cache(maxsize=512)` `_compile(term)` (threat T-260905-01: `re.escape` on all term text; only finite lookaround + optional-suffix structure added).
- ASCII alphabetic terms: light stem (ies→y when len>4; first applicable suffix from ing/ed/es/s/e stripped when base ≥ 3) + pattern `(?<![a-z0-9])base(?:s|es|ed|ing|e)?(?![a-z0-9])` with `re.IGNORECASE`. Lookarounds (not `\b`) make `CHUNK` inside `SIF_CHUNK_OVERLAP` matchable while `table` inside `notable` never matches.
- ASCII non-alphabetic terms (sqlite-vec, 3.5): literal escape, boundary lookarounds attached only on alphanumeric edge chars.
- Non-ASCII (CJK): no regex — full-run substring gate with per-character fallback passing at `max(2, distinct_term_chars // 2)`; find_first_match returns full-run position when present, else first shared term character (length 1).
- 18 tests in `tests/unit/search/test_term_match.py`.

### Task 2: Line-aware SmartSnippetExtractor rewrite — commit f85747a

- `src/sif/search/snippets.py` internals replaced: newline line-splitting (`_split_lines`) instead of sentence-punctuation splitting; `_is_structural_line` classifies blanks, code-fence delimiters, horizontal rules, table separator rows.
- `_score_line`: distinct-terms primary / weighted-count secondary / shorter-line tiebreak via term_match.
- `_build_window`: alternate up/down expansion under max_length (newline-joined), monotonic outward frontiers, edge-trim of structural lines with budget reuse for one more content neighbor; `_cut_long_line` centers a max_length window on `find_first_match` when the best line alone is too long; fallback skips leading blank/fence lines (headings stay).
- Public contract byte-compatible: `__init__(max_length=300, context_radius=80)` (context_radius stored, documented as API-compat) and `extract(text, query_terms)` — `search_cmd` and `SearchPipeline._apply_snippets` needed zero edits (verified: no diff in `src/sif/cli/commands/search.py` or `src/sif/search/hybrid.py`).
- Existing 10 snippet tests pass unchanged; 4 G-04-1 regression tests added (table row vs section heading, code line with fence-edge guard, fallback skipping, over-long line centering).

### Task 3: BM25 highlights via shared matcher + full quality suite — commit 89a8a5e

- `src/sif/search/bm25.py`: `_get_highlights` gate is now `find_first_match(chunk, query_terms) is not None`; `_extract_snippet` uses one `find_first_match` yielding `(pos, match_len)` with identical windowing/ellipses/fallback. Both signatures unchanged; hybrid.py delegation untouched.
- 3 regression tests: stem-variant document ("ranks"/"token" highlighted under query "ranking tokens"), notable-chunk yields empty highlights under query "table", CJK 向量搜索 highlights 向量检索 text.
- Pre-existing `test_search_with_highlights` passes unchanged (literal matching still works through the shared matcher).

## Test Results

| Suite | Result |
|-------|--------|
| tests/unit/search/test_term_match.py (new) | 18 passed |
| tests/unit/search/test_snippets.py | 14 passed (10 existing + 4 new) |
| tests/unit/search/test_bm25.py | 22 passed (19 existing + 3 new) |
| tests/unit/search/test_hybrid.py + tests/integration/test_search_pipeline.py | 36 passed |
| Full suite (`pytest -q`) | 608 passed, 11 skipped, 0 failed |
| `ruff check src tests` | All checks passed |
| `ruff format --check src tests` | 127 files already formatted |

TDD gates: RED commit a4887de (collection error — module absent) precedes GREEN commit 2d99c86; no refactor commit needed.

## Commits

- a4887de: test(260905-hc3): add failing tests for stem-tolerant term matcher
- 2d99c86: feat(260905-hc3): implement shared stem-tolerant term_match module
- f85747a: feat(260905-hc3): rewrite SmartSnippetExtractor as line-aware windows
- 89a8a5e: feat(260905-hc3): route BM25 highlights through shared term matcher

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] First commit attempts swept in a pre-existing staged deletion**

- Found during: Tasks 1 and 2 commits
- Issue: The working index carried a staged `mypy.ini` deletion (user state, present at spawn). `git commit` without pathspec commits the whole index, so commits 0eccec6 and 8d7b868 included that unrelated deletion.
- Fix: `git reset --soft HEAD~1` (no history loss, index preserved) then pathspec-scoped `git commit <files>`; final commits a4887de/2d99c86/f85747a/89a8a5e contain only task files. User's staged `mypy.ini` deletion and working-tree state preserved exactly.

**2. [Rule 1 - Bug] Two self-contradictory RED-phase test fixtures corrected during GREEN**

- Found during: Tasks 1 and 2
- Issue: (a) CJK single-char gate test used 只有搜索功能, which shares TWO term characters (搜, 索) — it legitimately passes the spec threshold max(2, 4//2)=2; (b) over-long-line test used `H*200 + "needle" + T*200`, one giant alphanumeric word inside which the matcher correctly refuses to match.
- Fix: (a) fixture changed to 检索功能 / 向导手册 (exactly one shared char each); (b) fixture changed to space-separated `H · needle · T` runs. Implementation unchanged in both cases — fixtures contradicted the plan's own spec.

**3. [Environmental, not fixed] 14 CLI tests fail under harness FORCE_COLOR=3**

- Found during: Task 3 full-suite run
- Issue: The agent harness exports `FORCE_COLOR=3`; rich honors it and emits ANSI codes, so tests asserting plain CLI output fail (e.g. `assert 'Pruned 3' in '\x1b[32mPruned \x1b...'`). Verified pre-existing: the identical 14 tests fail at baseline 70888ce in a temp worktree, and STATE.md records 0 failures in the user's normal environment.
- Resolution: out of scope (not caused by this task). Full suite passes with `env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q` → 608 passed, 11 skipped, 0 failed. Recorded here so future executors in this harness use that invocation.

Otherwise the plan executed exactly as written.

## Threat Mitigations Applied

- T-260905-01 (mitigate): all user query text passes through `re.escape` before pattern assembly; added structure limited to fixed optional-suffix alternation + two lookarounds (finite, linear-time); `@lru_cache(maxsize=512)` bounds compiled-pattern memory under unbounded distinct queries.
- T-260905-02 (accept): rendering path unchanged; only text selection changed.

## Known Stubs

None.

## Self-Check: PASSED

- All 6 created/modified files exist on disk.
- All 4 commit hashes (a4887de, 2d99c86, f85747a, 89a8a5e) present in git log.
- No tracked-file deletions in any task commit.
- All four public signatures unchanged; zero edits to search.py / hybrid.py callers.
