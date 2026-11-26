---
phase: 19-search-correctness
plan: 10
subsystem: search
tags: [per-chunk, chunk-identity, rich-table, csv, markdown, xml, path-only, gap-closure, uat, corr-02]

# Dependency graph
requires:
  - phase: 19-search-correctness
    provides: "19-07 --per-chunk escape hatch, chunk_id and sequence on SearchResult, the Chunk table column and the shipped path#sequence assertion; CONTEXT D-01 (no new option on document-level surfaces) and D-03 (chunk identity, display form path#sequence)"
provides:
  - "_ChunkAddress cell and _chunk_column declaration (_CHUNK_MIN_WIDTH = 8): both per-chunk tables keep #sequence at 80 columns with and without the Content column, and still show the whole address on a wide terminal"
  - "_fit_head: left-shortening that keeps a suffix whole, prefers separator-aligned tails, and measures display cells"
  - "format_results_csv, format_results_md and format_results_xml take a keyword-only per_chunk flag: CSV gains a last sequence column, Markdown a Sequence line, XML a sequence element; document-level rows and every default output are byte-identical to before"
  - "_unique_paths: --files and the quiet path-only output of per-chunk query and vsearch pages list each path once per page"
  - "docs/changelog.md entry under [Unreleased] / Changed; 23 new tests in TestPerChunkSurfaces"
  - "Plan base record left in place so the red-derivation and scope gates can be re-run"
affects: [19 (UAT tests 1 and 3), 18 and 24 (their verifications go stale after this change)]

# Actuals (#2632): tokens are chars/4 over the unified diff of the three changed files (src, tests, docs).
# commits counts the commits measured from the plan base; this SUMMARY is committed after them.
actuals:
  tokens: 8473
  tasks: 2
  commits: 3
  plan_head_before: 147661bd9f5e9986bab6d24cb4ddbc7b3a2cc5fb
  plan_head_after: 5e83d6db2205198272b0e8364458529b931ba3c8

tech-stack:
  added: []
  patterns:
    - "A table cell that must keep its tail is a Rich renderable: it measures at its full width and fits itself to the width Rich hands it at render time, so its column still takes part in the width sharing instead of being frozen out of it"
    - "Force a console width in tests by patching the module console with Console(width=...); Rich latches COLUMNS when a Console is constructed, so a later change of the variable has no effect"
    - "An optional per-row output field rides a keyword-only formatter flag and is written only for rows that carry it; the default path keeps producing the same bytes"

key-files:
  created: []
  modified:
    - src/sif/cli/commands/search.py
    - tests/unit/cli/test_search.py
    - docs/changelog.md

key-decisions:
  - "The Chunk cell is a _ChunkAddress renderable. __rich_measure__ reports the full address and __rich_console__ yields a plain Text fitted to the width Rich gives the cell, so the path is shortened from the left at render time and the sequence suffix is never dropped. Yielding Text parses no markup, so a document-derived path cannot inject Rich markup."
  - "The Chunk column floor is 8 cells (_CHUNK_MIN_WIDTH), not 24. Rich restores a column to its floor after sharing out the console width; with the floor at 8 every per-chunk layout is exactly 80 cells wide at 80 columns, with the Chunk column taking the share Rich gives it (37 cells in the vector layout, 15 in the hybrid layout, 17 and 10 with the Content column)."
  - "_chunk_column returns the add_column keywords with min_width equal to the smaller of 8 and the widest address on the page, and passes no no_wrap: marked no_wrap the column is left out of the collapse step and Rich takes the whole overflow from the other columns."
  - "_fit_head keeps the suffix whole and measures display cells, so a CJK path counts double-width characters the way Rich does. Beyond its stated scope (a path without a tab or line break, at most six sequence digits at the floor, a console of at least 30 columns) the suffix can still be lost."
  - "Per-chunk machine formats follow assumption A-19-10-1 as the plan states it: the path#sequence address in path plus the bare sequence as a last CSV column named sequence, a Sequence line in Markdown and a sequence element in XML. Document-level rows keep the plain path and get none of the three; output without --per-chunk is unchanged."
  - "--files and the quiet path-only output of a per-chunk page list each path once in first-occurrence order within that page. --limit and --offset keep counting chunk rows, so a path-only per-chunk page can print fewer lines than --limit. A default page still prints one line per row, also when two rows share a path."
  - "No option was added or removed (D-01): sif search vsearch still rejects --csv, --md, --xml and --files, and sif search search still rejects --per-chunk."

patterns-established:
  - "Width-sensitive render tests go through the real CLI commands with a console of explicit width patched over the module console, pair each rendered Chunk cell with its own row strictly, and check all five line shapes of the table against the console width."
  - "Guards that pass before the change sit next to the tests that go red: default CSV, Markdown, XML and path-only output are pinned so de-duplication and chunk fields can never reach document-level mode."

requirements-completed: [CORR-02]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "Both per-chunk tables keep every chunk row's path#sequence at 80 columns and end at their right border there, with and without the Content column, for 31-, 49- and 304-character paths and a double-width CJK file name; a document-level BM25 row keeps the bare path; a 200-column terminal shows the whole address"
    requirement: CORR-02
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestPerChunkSurfaces.test_vsearch_per_chunk_keeps_sequence_at_80_columns + test_query_per_chunk_keeps_sequence_at_80_columns + test_vsearch_per_chunk_with_content_fits_the_console_at_80_columns + test_query_per_chunk_with_content_fits_the_console_at_80_columns + test_per_chunk_shows_the_full_path_on_a_wide_terminal + test_per_chunk_table_renders_path_sequence"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestPerChunkSurfaces.test_fit_head_keeps_the_suffix_and_prefers_separator_edges (7 cases) + test_fit_head_counts_double_width_characters_as_rich_does (3 budgets) + test_chunk_column_never_reserves_more_than_the_page_needs"
        status: pass
      - kind: other
        ref: "red-derivation gate against the base render module 147661b (exit 0; inner pytest exit 1; exactly the four 80-column tests FAILED by name; 4 failed, 2 passed)"
        status: pass
      - kind: other
        ref: "live render on a scratch index at COLUMNS=80: vsearch 12 of 12 rows, hybrid 6 of 6 chunk rows, 0 lines wider than 80 cells, every table line at its right border, with and without the Content column"
        status: pass
    human_judgment: false
  - id: D2
    description: "Per-chunk CSV carries the path#sequence address and a last sequence column; per-chunk Markdown and XML carry the address and the bare sequence for chunk rows only; default CSV, Markdown and XML output is unchanged for rows that carry a sequence"
    requirement: CORR-02
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestPerChunkSurfaces.test_per_chunk_csv_carries_address_and_sequence + test_per_chunk_markdown_and_xml_carry_chunk_identity + test_default_csv_is_unchanged_for_rows_that_carry_a_sequence + test_default_markdown_and_xml_omit_chunk_identity"
        status: pass
      - kind: other
        ref: "differential check of the default formatters against the base module over 960 row sets (object and dict rows, with and without a sequence): 3,840 CSV, Markdown, XML and JSON comparisons, 0 mismatches"
        status: pass
    human_judgment: false
  - id: D3
    description: "--files and the quiet path-only output of a per-chunk page of query and vsearch list each path once in first-occurrence order; a default page keeps one line per row; the per-row path echo remains only in search_cmd"
    requirement: CORR-02
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestPerChunkSurfaces.test_per_chunk_files_and_quiet_list_each_path_once + test_per_chunk_path_only_page_counts_chunk_rows + test_default_files_and_quiet_output_keep_one_line_per_row"
        status: pass
      - kind: other
        ref: "grep -c 'click.echo(r.path)' src/sif/cli/commands/search.py (exit 0, count 1, inside search_cmd)"
        status: pass
    human_judgment: false
  - id: D4
    description: "docs/changelog.md carries one entry under [Unreleased] / Changed for the changed per-chunk output"
    verification:
      - kind: other
        ref: "grep -c 'now carries the chunk identity in' docs/changelog.md (exit 0, count 1)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Scope and quality hold: exactly the three declared files changed since the plan base, both generated docs are byte-identical after make docs-generate, no option was added or removed, lint and type check are clean, and the full suite passes with coverage at or above 90"
    verification:
      - kind: other
        ref: "base-anchored scope gate (exit 0 before and after each commit; changed set equals the three declared files)"
        status: pass
      - kind: other
        ref: "make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md (exit 0; SHA-256 of both files unchanged)"
        status: pass
      - kind: other
        ref: "env -u FORCE_COLOR NO_COLOR=1 pytest (3286 passed, 1 skipped, 27 warnings, 95.16%, fail_under=90 reached)"
        status: pass
      - kind: other
        ref: "ruff check src tests && ruff format --check src tests; ty check src/sif/cli/commands/search.py (all clean)"
        status: pass
    human_judgment: false
  - id: D6
    description: "On a real 80-column terminal the per-chunk rows of both tables stay recognisable: for each row the operator can say which document it comes from and which chunk it is, using the table alone (UAT test 1, the visual half of G-19-1)"
    requirement: CORR-02
    verification:
      - kind: other
        ref: "live render on a scratch index at COLUMNS=80 (counts recorded below); this is the backstop, not the judgement"
        status: pass
    human_judgment: true
    rationale: "Whether rows stay recognisable at the canonical width on a real terminal is a visual judgement. The tests force the same width through the same CLI code and pin that each row shows its own sequence and that the table fits, but they cannot see the terminal or say whether the result is readable; the UAT tester observed the defect only on a live render. Not self-approved by the executor."
  - id: D7
    description: "The machine-format and path-only behaviour that assumption A-19-10-1 implements is the behaviour the operator wants (UAT test 3, a decision row): a seventh CSV column named sequence, a Sequence line in Markdown, a sequence element in XML, and one line per path for per-chunk pages"
    requirement: CORR-02
    verification: []
    human_judgment: true
    rationale: "UAT test 3 is a decision row, not a failed test: whether machine formats must carry chunk identity, and in which fields, is the operator's call. The plan implements the assumed behaviour and can be amended if the operator wants another field layout. Not self-approved by the executor."

duration: 31min
completed: 2026-11-26
status: complete
---

# Phase 19 Plan 10: Chunk Identity on Per-Chunk Tables and in Machine Formats Summary

**Both per-chunk tables now keep every chunk row's `path#sequence` inside an 80-column terminal (a self-sizing Chunk cell with a column floor of 8), and per-chunk CSV, Markdown, XML and path-only output carry the chunk identity while output without `--per-chunk` stays byte-for-byte unchanged.**

## Performance

- **Duration:** 31 min
- **Started:** 2026-11-26T00:31:17Z
- **Completed:** 2026-11-26T01:02:00Z
- **Tasks:** 2/2
- **Files modified:** 3 (1 source, 1 test, 1 changelog)

Environment: Python 3.13.9, Rich 14.3.3, pytest 9.1.1, branch `gsd/phase-24-reverify`, no worktree.

## Plan Base and Precondition

- Plan base: `147661bd9f5e9986bab6d24cb4ddbc7b3a2cc5fb`, recorded at Task 1 Step 0 in the file that `git rev-parse --git-path gsd-plan-19-10-base` prints (`.git/gsd-plan-19-10-base`). No earlier commit carries the `(19-10)` scope, so the record holds HEAD at the start. It survived the three commits and is left in place so the red-derivation and scope gates can be re-run.
- Precondition: `git diff --quiet 6e28002 -- src/sif/cli/commands/search.py tests/unit/cli/test_search.py` exited 0, and `pytest`, `ruff`, `ty` and `git` were on PATH.
- Tracer feedback gate (Task 1 is `type="tracer"`, automated-only verify, auto mode active because `workflow.auto_advance` is `true`): the verify block was re-run after the Task 1 commit; all five gates were green, then Task 2 started.

## Red Runs

### Task 1 Step 2, against the unchanged source

```
env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/cli/test_search.py::TestPerChunkSurfaces -q --no-cov -p no:cacheprovider
```

Exit code 1. Short test summary, verbatim:

```
FAILED tests/unit/cli/test_search.py::TestPerChunkSurfaces::test_vsearch_per_chunk_keeps_sequence_at_80_columns
FAILED tests/unit/cli/test_search.py::TestPerChunkSurfaces::test_query_per_chunk_keeps_sequence_at_80_columns
FAILED tests/unit/cli/test_search.py::TestPerChunkSurfaces::test_vsearch_per_chunk_with_content_fits_the_console_at_80_columns
FAILED tests/unit/cli/test_search.py::TestPerChunkSurfaces::test_query_per_chunk_with_content_fits_the_console_at_80_columns
FAILED tests/unit/cli/test_search.py::TestPerChunkSurfaces::test_fit_head_keeps_the_suffix_and_prefers_separator_edges[/notes/a.md-#0-24-/notes/a.md#0]
FAILED tests/unit/cli/test_search.py::TestPerChunkSurfaces::test_fit_head_keeps_the_suffix_and_prefers_separator_edges[/notes/chunky/protocol-notes.md-#0-24-\u2026protocol-notes.md#0]
FAILED tests/unit/cli/test_search.py::TestPerChunkSurfaces::test_fit_head_keeps_the_suffix_and_prefers_separator_edges[/notes/chunky/protocol-notes.md-#12-28-\u2026chunky/protocol-notes.md#12]
FAILED tests/unit/cli/test_search.py::TestPerChunkSurfaces::test_fit_head_keeps_the_suffix_and_prefers_separator_edges[/notes/chunky/protocol-notes.md-#12-26-\u2026protocol-notes.md#12]
FAILED tests/unit/cli/test_search.py::TestPerChunkSurfaces::test_fit_head_keeps_the_suffix_and_prefers_separator_edges[/notes/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.md-#3-24-\u2026xxxxxxxxxxxxxxxxxx.md#3]
FAILED tests/unit/cli/test_search.py::TestPerChunkSurfaces::test_fit_head_keeps_the_suffix_and_prefers_separator_edges[/notes/chunky/protocol-notes.md--24-\u2026protocol-notes.md]
FAILED tests/unit/cli/test_search.py::TestPerChunkSurfaces::test_fit_head_keeps_the_suffix_and_prefers_separator_edges[/notes/chunky/protocol-notes.md-#123456-8-\u2026#123456]
FAILED tests/unit/cli/test_search.py::TestPerChunkSurfaces::test_fit_head_counts_double_width_characters_as_rich_does[8-\u2026\u7a76.md#7]
FAILED tests/unit/cli/test_search.py::TestPerChunkSurfaces::test_fit_head_counts_double_width_characters_as_rich_does[10-\u2026\u7814\u7a76.md#7]
FAILED tests/unit/cli/test_search.py::TestPerChunkSurfaces::test_fit_head_counts_double_width_characters_as_rich_does[24-\u2026\u76f8\u5173\u6027\u6392\u5e8f\u65b9\u6cd5\u7814\u7a76.md#7]
FAILED tests/unit/cli/test_search.py::TestPerChunkSurfaces::test_chunk_column_never_reserves_more_than_the_page_needs
15 failed, 8 passed in 0.61s
```

- The four 80-column render tests each raised on the `cell.endswith` assertion. Example: `'/Users/forrest/Documents/kb/sif/prot…'.endswith('#3')` is false. The base table still fitted the console in all four layouts (every table line was 80 cells and ended at its right border), so only the suffix assertion made them red.
- The eleven other failures were `ImportError: cannot import name '_fit_head'` (ten cases) and `'_CHUNK_MIN_WIDTH'` (one case): the helpers did not exist yet.
- The eight passes were the seven shipped tests and the wide-terminal guard, which passes on the base by design.

### Task 2, against the source at the Task 1 commit `4e258cf`

Same command. Exit code 1. Short test summary, verbatim:

```
FAILED tests/unit/cli/test_search.py::TestPerChunkSurfaces::test_per_chunk_csv_carries_address_and_sequence
FAILED tests/unit/cli/test_search.py::TestPerChunkSurfaces::test_per_chunk_markdown_and_xml_carry_chunk_identity
FAILED tests/unit/cli/test_search.py::TestPerChunkSurfaces::test_per_chunk_files_and_quiet_list_each_path_once
FAILED tests/unit/cli/test_search.py::TestPerChunkSurfaces::test_per_chunk_path_only_page_counts_chunk_rows
4 failed, 26 passed in 1.15s
```

- CSV: the record had six keys (`Right contains one more item: 'sequence'`).
- Markdown: the Path line held the plain path, so `- **Path:** \`/notes/chunky/protocol-notes.md#0\`` was absent.
- `--files`: the first document's path was printed twice (five lines for four distinct paths).
- Path-only page: three lines, one per chunk row, where two documents were expected.
- The three guards for default output passed before the change.

The terminal was 80 columns in both runs, so every `FAILED` line ends at the test id; no overlay gate needed a re-run with a different `COLUMNS`.

## Accomplishments

- `_chunk_cell` now returns a `_ChunkAddress`. It measures at the full address and, at render time, shortens the path from the left to the width Rich gives the cell (`_fit_head`: the longest tail that begins right after a path separator, prefixed with an ellipsis; otherwise a character-by-character cut; the suffix is always kept whole). It yields a plain `Text`, so no markup in a path is parsed.
- Both per-chunk tables declare their column with `table.add_column("Chunk", **_chunk_column(results))`: `min_width` is the smaller of `_CHUNK_MIN_WIDTH` (8) and the widest address on the page, and `no_wrap` is not passed.
- At 80 columns, on this plan's rows, the Chunk column takes 37 cells in the vector layout, 15 in the hybrid layout, and 17 and 10 with the Content column (the same shares as before the change); every layout is exactly 80 cells wide and every chunk row ends with its own `#sequence`. At 200 columns the full address is shown.
- `format_results_csv`, `format_results_md` and `format_results_xml` take a keyword-only `per_chunk` flag, and `query_cmd` passes it; `search_cmd` calls them unchanged. `_CSV_HEADER` names the default header.
- `_unique_paths` drives the path-only loops of `vsearch_cmd` and `query_cmd` in per-chunk mode only. The loop of `search_cmd` is untouched.
- `docs/changelog.md` carries the entry under `[Unreleased]` / `Changed`.
- `test_per_chunk_table_renders_path_sequence` is unmodified and passes. `TestPerChunkSurfaces` went from 7 to 30 test items (22 test functions, seven and three of them parametrized).

## Task Commits

Each task was committed atomically, by explicit path, on `gsd/phase-24-reverify`:

1. **Task 1: Chunk identity survives an 80-column terminal on both per-chunk tables (G-19-1, D-03)** - `4e258cf` (fix)
2. **Task 2: Chunk identity in CSV, Markdown, XML and path-only output (UAT test 3, D-03)** - `8cf0ec9` (feat)
3. Fixture sentence correction in the Task 1 test data (see Deviations) - `5e83d6d` (test)

**Plan metadata:** this SUMMARY is committed separately, immediately after it is written (docs: complete 19-10 plan).

## Gate Evidence

| Gate | Outcome |
|------|---------|
| **Task 1** | |
| Class run, `pytest tests/unit/cli/test_search.py::TestPerChunkSurfaces -x -q --no-cov -p no:cacheprovider` | 23 passed (7 shipped + 16 new) |
| `grep -c 'table.add_column("Chunk", \*\*_chunk_column(results))'` | count 2 |
| Red-derivation gate (current tests over the base render module in a temp overlay) | exit 0; inner pytest exit 1; the four 80-column tests FAILED by name; `4 failed, 2 passed, 17 deselected` |
| `ty check src/sif/cli/commands/search.py` | All checks passed! |
| `ruff check` and `ruff format --check` on both files | All checks passed!; 2 files already formatted |
| Tracer feedback gate (auto mode, verify re-run after the Task 1 commit) | all five green again at `4e258cf` |
| **Task 2** | |
| `pytest tests/unit/search/test_bm25.py tests/unit/cli/test_search.py -x --no-cov` | 248 passed, before and after the commit |
| `grep -c 'click.echo(r.path)'` | count 1, in `search_cmd` |
| `grep -c 'now carries the chunk identity in' docs/changelog.md` | count 1 |
| `make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md` | exit 0; both files byte-identical (SHA-256 `38239d90…` and `6dfa4c17…` before and after) |
| Base-anchored scope gate | exit 0 before and after each commit; changed set is exactly `docs/changelog.md`, `src/sif/cli/commands/search.py`, `tests/unit/cli/test_search.py` |
| Full suite, `env -u FORCE_COLOR NO_COLOR=1 pytest` | run 1 at the Task 2 tree: exit 0, 3286 passed, 1 skipped, 27 warnings in 208.85s, coverage 95.15%. Run 2 on the final tree: exit 0, 3286 passed, 1 skipped, 27 warnings in 204.57s, coverage 95.16%. `fail_under=90` reached in both |
| `ruff check src tests && ruff format --check src tests` | All checks passed!; 237 files already formatted |
| **Plan-level verification** | |
| `pytest tests/unit/search tests/unit/cli tests/unit/mcp tests/integration/test_search_correctness.py -x --no-cov` | 1817 passed |
| `make docs-generate && git diff --exit-code docs/` | exit 0 at the final commit (before the Task 2 commit it exited 1 on the uncommitted changelog entry alone) |
| **Acceptance spot checks** | |
| `sif search vsearch` with `--csv`, `--md`, `--xml`, `--files`; `sif search search` with `--per-chunk` | exit 2 for all five, `No such option` |
| Document-level row in per-chunk Markdown and XML | plain Path line and no Sequence line; element children `title, path, collection`; chunk rows `title, path, sequence, collection` |
| Chunk cell with a markup-bearing path (`/notes/[red]evil[/red].md`) | rendered literally; no markup applied |
| `_table_fits_console` with one line shape at a time losing its right corner | False for each of the five shapes, including the bottom border |

The 27 warnings are pre-existing `ResourceWarning: unclosed database` messages from unrelated code. `ty check src/sif` (whole package) reports the same 10 diagnostics as before this plan, in `embedding/embedder.py`, `models/download.py`, `search/rerank.py` and `sentence_transformers`; none is in `search.py`.

## Live Render at 80 Columns (Task 2 evidence step)

- Gate: with `SIF_CACHE_DIR` unset and `SIF_DB_PATH` on a non-existent scratch path, `sif models status | grep -xF 'cache.state: valid'` printed `cache.state: valid` and exited 0. The configured model is `Qwen/Qwen3-Embedding-0.6B` (`modelscope`, 1024 dimensions); `settings.cache_dir` was `/Users/forrest/Library/Caches/sif/models`.
- Scratch directory: `/var/folders/1q/2qhztsp1673fnqgrpblxnpd40000gn/T/tmp.hz64bDlSpt`, since removed. The real models directory was linked as `cache/models` inside it only after the gate passed. Every command ran with `SIF_DB_PATH` and `SIF_CACHE_DIR` inside the scratch directory.
- Corpus: 12 documents, 54 chunks: six documents of four sections each on one topic, plus six unrelated fillers. Paths are 107 to 218 characters; one file name is Chinese. `sif index embed` reported `Using cached model` and embedded on `mps` in 10 seconds.
- Query `Saltiv protocol session key negotiation`, `-n 12`, `COLUMNS=80`, `--no-refresh`, no `--rerank`:

| Render | Rows | Rows ending `#sequence` | Lines wider than 80 cells | Table lines at the right border |
|--------|------|-------------------------|---------------------------|---------------------------------|
| `vsearch --per-chunk` | 12 | 12 of 12 | 0 | 34 of 34 |
| `query --per-chunk` | 12 | 6 of 6 chunk rows | 0 | 188 of 188 |
| `vsearch --per-chunk --full --line-numbers` | 12 | 12 of 12 | 0 | 222 of 222 |
| `query --per-chunk --full --line-numbers` | 12 | 6 of 6 chunk rows | 0 | 296 of 296 |

- The hybrid page holds 6 document-level rows (JSON `sequence` is null for 6 of its 12 rows); they show a plain file-name tail with no `#`. The vector page holds none.
- On the same page `query --per-chunk --files` printed 6 lines, and `query --per-chunk --csv` printed the seven-column header with the address and number on chunk rows and the plain path with an empty `sequence` on document-level rows.

This reproduces the counts the plan recorded from planning (12 of 12, 6 of 6, every layout at its right border).

## Model Cache

- A metadata snapshot of `/Users/forrest/Library/Caches/sif` (path, size, modification time and type of all 129 entries) was taken before the gate. It was identical after the status gate and again after the evidence step, so that step wrote nothing to the real cache. The 16 files of the cached model kept their sizes and modification times, and so did the user's `embeddings_cache.db`.
- After the full-suite gate exactly two entries differed, by modification time only: `models/.lock/cross-encoder___ms-marco-MiniLM-L-6-v2` (0 bytes before and after) and the empty directory `models/cross-encoder`. This is the accepted T-19-36 behaviour of the project's reranker tests. The entry count stayed 129; no path was added or removed and no size changed, so no model was downloaded.
- The scratch directory was removed with the link unlinked first. No overlay copy remains under the OS temp folder. `~/SynologyDrive` was not read, watched, indexed or copied.

## Files Created/Modified

- `src/sif/cli/commands/search.py` - `_CHUNK_MIN_WIDTH`, `_PATH_SEPARATORS`, `_ELLIPSIS`, `_CSV_HEADER`; `_sequence_value`, `_chunk_suffix`, `chunk_address`, `_fit_head`, `_ChunkAddress`, `_chunk_cell`, `_chunk_column`, `_unique_paths`; `per_chunk` on the three formatters and on the `query_cmd` call sites; the two Chunk column declarations; the path-only loops of `vsearch_cmd` and `query_cmd`
- `tests/unit/cli/test_search.py` - three module-level imports plus `dataclasses.replace`; `_LONG_PATHS`, `_SNIPPETS`, `_long_path_rows`, `_render_at`, `_rendered_chunk_cells`, `_table_fits_console`; 23 new tests in `TestPerChunkSurfaces`
- `docs/changelog.md` - the `[Unreleased]` / `Changed` entry

Nothing was created or deleted.

## Decisions Made

- **The cell sizes itself; the column keeps sharing the width.** Rich restores a column to its `min_width` after sharing out the console width. A floor of 24 therefore pushed the hybrid table past 80 columns, while 8 lets the column take what Rich gives it and still keeps the suffix.
- **Yield `Text`, not an escaped string.** An escaped string is truncated by Rich from the right, which is where the sequence lives, and still goes through markup parsing. A renderable controls its own shortening.
- **The new tests import the new helpers inside the test function.** A module-level import would have turned the red run into a collection error for the whole file.
- **Row copies in the Task 2 tests are built with `dataclasses.replace`.** It copies a row and changes only the named fields, which is what "a second chunk of the same document" and "a shared path" need.

## Deviations from Plan

No gate was weakened, skipped or re-run with different settings, and no product default was changed. Two small additions and one correction, none of which alters a count the plan states:

1. **[Rule 1 - Bug, cosmetic] Fixture sentence claimed a fold that Rich does not perform.** Found during the final review, after both task commits: my render check showed that Rich 14.3.3 cuts the 34-character token with an ellipsis (`supercalifrag…`) inside the narrow Snippet cell instead of folding it across lines, while the snippet text I wrote said "so Rich folds it across lines". The sentence was corrected in `5e83d6d`. Data only: the class still reports 30 passed, the red-derivation gate still exits 0, and the full suite was re-run on the final tree (run 2 above).
2. **[Addition] One module-level import beyond the three the plan names.** `from dataclasses import replace` in `tests/unit/cli/test_search.py`, for the row copies above.
3. **[Addition] One assertion beyond the plan's description.** `test_per_chunk_path_only_page_counts_chunk_rows` also asserts that the search received `limit == 3`, which pins the "counts chunk rows" half of the contract its name states. It passes before and after the change and does not affect the red count.

**Total deviations:** 1 cosmetic auto-fix, 2 additions. **Impact on plan:** none on scope, gates or behaviour.

## Issues Encountered

1. `ruff check` reported `E501` on the `_fit_head` condition until `ruff format` reflowed it. The plan's validation note describes the same step.
2. Two mistakes in my own throwaway verification scripts, both caught and re-run: a listing script indexed a border line as if it were a data row, and the first evidence-analysis script had an unmatched parenthesis in an f-string. No result recorded above comes from a faulty run.

## Manual Verification Pending (not self-approved)

The plan carries two `<human-check>` blocks in the Task 2 verify. Neither was performed or approved by the executor. Both are the operator's.

### CHECKPOINT 1: Verification Required (UAT test 1, the visual half of G-19-1)

- **Progress:** 2/2 tasks complete.
- **Built:** both per-chunk tables keep `#sequence` at 80 columns (commits `4e258cf`, `8cf0ec9`, `5e83d6d`).
- **How to verify:** in a real terminal 80 columns wide, on an index with embedded chunks whose paths are 30 or more characters, run `sif search query --per-chunk QUERY -n 12` and then `sif search vsearch --per-chunk QUERY -n 12`, with a query that matches several chunks of each of several documents, each also with `--full --line-numbers`.
- **Expected:** on both tables you can tell the rows apart: for each row you can say which document it comes from and which chunk of that document it is, using the table alone. The Chunk cell ends with a number sign followed by that row's sequence, and rows of one document differ by that number. At 80 columns the hybrid table gives the Chunk column 15 cells, so different documents can show the same file-name tail (in my live render: `…col-notes.md`, `…d-secrecy.md`, `…-overview.md` for document-level rows), and the Title and Collection columns must still tell them apart. The table ends at its right border inside the terminal in every render, also with the Content column; nothing is cut off on the right, and rank, score, title and collection are still visible. A visible number that leaves two rows indistinguishable does not pass this check.
- **YOUR ACTION:** type "approved", or describe the rows you cannot tell apart.

### CHECKPOINT 2: Decision Required (UAT test 3, assumption A-19-10-1)

- **Built:** per-chunk CSV, Markdown, XML and path-only output carry the chunk identity (commit `8cf0ec9`).
- **How to verify:** run `sif search query --per-chunk QUERY --csv`, then with `--md`, with `--xml` and with `--files`, on a document with several matching chunks; then the same without `--per-chunk`.
- **Expected:** the CSV header ends with a `sequence` column and a chunk row's path is the path followed by a number sign and the sequence; Markdown and XML chunk rows carry the same address and the bare sequence; a document-level row has the plain path and no sequence. `--files` lists each path once for that page. Without `--per-chunk` the three formats and `--files` look exactly as before, including a page that lists one document twice because it is indexed in two collections.
- **Decision:** confirm this field layout, or name the layout you want instead. A different choice re-plans the machine-format and path-only part of Task 2.
- **YOUR ACTION:** type "confirmed", or describe the field layout to change.

## Residual Observations (not fixed - outside this plan's scope)

- **The plan's ninth truth calls the 34-character token "folded".** In Rich 14.3.3 the token is cut with an ellipsis inside the narrow Snippet cell and its row wraps to 12 physical lines. The four 80-column tests assert the Chunk cell and the table fit only, so nothing depends on the wording.
- **Document-level rows of a hybrid per-chunk page show a file-name tail only.** They have no chunk identity, so at 80 columns their cell is the same kind of tail as before this plan (for example `…col-notes.md`). That is unchanged behaviour, but it bears on whether rows stay recognisable; CHECKPOINT 1 asks the operator exactly that.
- **`ty check src/sif` still reports the 10 pre-existing diagnostics** listed under Gate Evidence. They predate this plan and are already recorded as drift.

## Threat Model Disposition

- T-19-24 (tampering, cell and formatters): mitigated. The cell yields a plain `Text`; CSV keeps `QUOTE_ALL`; Markdown and XML keep `_xml_sanitize` and `xml_escape` on the new `sequence` value; the XML test parses with `ElementTree`; the markup-bearing path check rendered literally.
- T-19-25 (spreadsheet formulas in `--csv`): accepted, as the plan records. The new `sequence` cell is an integer and the per-chunk `path` value is an absolute path followed by `#` and a number.
- T-19-26 (denial of service, narrow terminals): mitigated. The floor is 8, the column is not `no_wrap`, and all four layouts are exactly 80 cells at 80 columns.
- T-19-27 (repudiation, identity correctness): mitigated. Render tests pair each cell with its own row strictly and the CSV test asserts the exact `path` and `sequence` of five rows.
- T-19-35 (real model cache during the evidence step): mitigated. Status gate first, link second; the cache snapshot was identical after the step.
- T-19-36 (real model cache during the full-suite gate): accepted, as the plan records, and observed as described.
- T-19-SC (package installs): no package was installed, added or removed; `pyproject.toml` and `uv.lock` are untouched.

No threat flags: no file adds an endpoint, auth path, file-access pattern or schema change beyond what the threat model records.

## Known Stubs

None. No test is skipped by this plan and every automated `<verify>` command ran.

## Next Phase Readiness

- UAT gap G-19-1 is closed in the automated sense at `5e83d6d`: every chunk row of both per-chunk tables shows its `path#sequence` at 80 columns and each table ends at its right border there. The visual half is CHECKPOINT 1.
- UAT test 3 is implemented as assumption A-19-10-1 states it; the operator's decision is CHECKPOINT 2.
- Adding `--csv`, `--md`, `--xml` and `--files` to `vsearch` remains out of scope, as the plan records.
- Not done by this executor, by instruction: `STATE.md`, `ROADMAP.md` and `REQUIREMENTS.md` (the CORR-02 checkbox) are untouched, and so are `19-UAT.md` and the other Phase 19 planning artifacts. The orchestrator owns those writes. Executing this plan re-stales the verifications of Phases 18 and 24.

## Self-Check: PASSED

Run at `5e83d6d`, immediately before this SUMMARY was written:

- Files: `src/sif/cli/commands/search.py`, `tests/unit/cli/test_search.py` and `docs/changelog.md` are present on disk; nothing was created or deleted.
- Commits: `4e258cf`, `8cf0ec9` and `5e83d6d` are ancestors of HEAD, and `git rev-list --count 147661b..HEAD` is 3.
- `gsd-tools check evaluation-scope --plan 19-10 --commits-only` resolved the same three commits.
- Plan base record present and equal to `147661bd9f5e9986bab6d24cb4ddbc7b3a2cc5fb`.
- Every symbol and test name the plan's artifacts list is defined (none missing); the column declaration count is 2 and the changelog phrase count is 1.
- Working tree clean outside `.planning/`.

The two human checks are not covered by this self-check; see Manual Verification Pending.

---
*Phase: 19-search-correctness*
*Completed: 2026-11-26*
