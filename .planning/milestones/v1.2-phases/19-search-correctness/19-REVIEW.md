---
phase: 19-search-correctness
reviewed: 2026-11-15T05:04:54Z
depth: standard
files_reviewed: 50
files_reviewed_list:
  - docs/benchmarking.md
  - docs/cli-reference.md
  - src/sif/cli/commands/eval.py
  - src/sif/cli/commands/index.py
  - src/sif/cli/commands/search.py
  - src/sif/core/models.py
  - src/sif/database/database.py
  - src/sif/database/repositories.py
  - src/sif/database/schema.py
  - src/sif/indexing/incremental.py
  - src/sif/indexing/parser.py
  - src/sif/indexing/watcher.py
  - src/sif/mcp/backend.py
  - src/sif/mcp/handlers.py
  - src/sif/mcp/protocol.py
  - src/sif/search/bm25.py
  - src/sif/search/context_attach.py
  - src/sif/search/hybrid.py
  - src/sif/search/personal_bench.py
  - src/sif/search/rerank.py
  - src/sif/search/rrf.py
  - src/sif/search/staleness.py
  - src/sif/search/vector.py
  - tests/fixtures/bench/heldout_defaults.json
  - tests/integration/test_incremental_equivalence.py
  - tests/integration/test_search_correctness.py
  - tests/unit/cli/test_eval.py
  - tests/unit/cli/test_index.py
  - tests/unit/cli/test_search.py
  - tests/unit/cli/test_search_pagination.py
  - tests/unit/database/test_repositories.py
  - tests/unit/database/test_schema.py
  - tests/unit/database/test_schema_title_fts.py
  - tests/unit/indexing/test_incremental.py
  - tests/unit/indexing/test_parser.py
  - tests/unit/indexing/test_parser_checksum.py
  - tests/unit/indexing/test_watcher.py
  - tests/unit/mcp/test_backend.py
  - tests/unit/search/test_bench_snapshot.py
  - tests/unit/search/test_bm25.py
  - tests/unit/search/test_collection_filter.py
  - tests/unit/search/test_context_attach.py
  - tests/unit/search/test_hybrid.py
  - tests/unit/search/test_personal_bench.py
  - tests/unit/search/test_rrf.py
  - tests/unit/search/test_staleness.py
  - tests/unit/search/test_vector.py
  - tests/unit/search/test_rerank.py
  - tests/unit/cli/test_search_min_score.py
  - tests/unit/search/test_filters_sql.py
findings:
  critical: 2
  warning: 2
  info: 12
  total: 16
  necessity: 0
status: issues_found
---

# Phase 19: Code Review Report

**Reviewed:** 2026-11-15T05:04:54Z
**Depth:** standard
**Files Reviewed:** 47
**Status:** issues_found

## Summary

Reviewed the Phase 19 search-correctness implementation: parser dispatch + D-08 checksum
convention, the D-07 metadata fast path / D-09 convention migration / watch embed leg,
the single-owner `enrich_results` boundary, offset ownership + global ranks + min_score,
vector per-document dedup and chunk identity, title-FTS migration + weighted BM25, the
MCP boundary forwarding, and the associated tests and docs. The phase-relevant unit and
integration suites pass (521 unit tests in the database/search/indexing/MCP/pagination
groups, 249 eval/bench/personal-bench/integration tests), which is exactly why the two
Critical findings matter: both are invisible to the committed tests.

The headline defect is a schema-migration durability hole. The CORR-04 migration drops
and recreates `documents_fts` (DDL, auto-committed by pysqlite) and then populates it with
`INSERT ... VALUES('rebuild')` (DML, left in the connection's implicit transaction). Any
close, failure, or crash before a commit rolls the population back while the two-column
DDL persists; the detection gate then reports "already migrated" forever, leaving BM25
search empty. I reproduced this end-to-end with the real `Database`/`SchemaManager` code:
a migration followed by a read-only `sif status` (which never commits) and then a later
normal open returns zero `MATCH` rows. The same code path is exercised by the repo's own
MCP dimension-mismatch test, which raises inside `create_all` and rolls the rebuild back.
The second Critical finding is a valid-YAML frontmatter title (sequence/mapping value)
reaching SQLite as a list and aborting the whole index update outside the per-file error
boundary.

No security vulnerabilities were found in scope: all SQL is parameterized, FTS
metacharacters are stripped and terms are quoted, context/saved-run paths are never
opened, XML/CSV/Rich output escapes user-derived text, and no hardcoded credentials were
found. No structural-findings block was provided. The necessity review (standard depth)
found no reachable code guarding against a provably impossible state, so `necessity: 0`.

## Incremental Re-review (2026-11-25)

**Scope:** the five test files in this phase's domain that changed since the last commit touching this report (`b817ebb`), set through the workflow's `--files` override. `c95d2cee` (quick task 261119-fww-02, Windows portability; not Phase 19 work) changed `tests/unit/cli/test_search.py`, `tests/unit/database/test_repositories.py`, `tests/unit/mcp/test_backend.py` and `tests/unit/search/test_context_attach.py`: it routes four direct symlink calls through `tests.support.symlink_or_skip`, adds two platform `skipif` guards, and relaxes two title-cell assertions from exact lengths to ten-character prefixes. `f8ff9bea` (Phase 19's own post-archive validation-gap closure for plan 19-06, CORR-02) added `TestRebuildChunkIdentity`, three tests in `tests/unit/search/test_rerank.py`, pinning that `_sort_and_build_results` carries `chunk_id`, `sequence` and `chunk_matches` into each rebuilt result. Each is the only commit in range for its file; `test_rerank.py` also shows merge `975cb098`, which carried the phase's own earlier content onto this branch and is identical to its second parent for that file. No Phase 19 SUMMARY changed. With the workflow's default scoping the resolver found no task commit of this phase after `b817ebb` (`status: degraded`, `source: phase-range`, `reason: no-task-commits-since`) and widened to the 59 files changed since the archive commit. That scope was not reviewed: it would have filed a whole-tree review under this phase and rewritten this report. The override leaves every other gate in place. Four of the five files are in the 47-file scope above; `tests/unit/search/test_rerank.py` is new to this report.

**Result: two new Info findings, IN-07 and IN-08. No Critical and no Warning.** The ten findings below keep their id, title, severity and text. None was fixed by this delta and none was re-reviewed: only IN-04, and a mention in CR-01, points into one of the five files (`tests/unit/mcp/test_backend.py:1141-1154`), at lines this delta does not touch. IN-02 is still true at HEAD, because `_sort_and_build_results` still does not copy `vectors_stale` (`src/sif/search/rerank.py:52-71`). The ten rows in `19-REVIEW-DISPOSITION.md` keep their recorded disposition; IN-07 and IN-08 are recorded `open`.

Checked at HEAD `f64da50`:

- **State of the five files.** `pytest --no-cov` over them reports 360 passed, 0 skipped (189, 31, 93, 29 and 18 per file); `ruff check` and `ruff format --check` (ruff 0.15.11) are clean. No direct `os.symlink` or `Path.symlink_to` call remains in them, and the `import os` dropped from `tests/unit/mcp/test_backend.py` has no remaining use.
- **Chunk identity through the rerank rebuild (CORR-02; `f8ff9bea`).** The three tests are correct, independent and not vacuous. Each of the three copied lines in `src/sif/search/rerank.py:68-70`, deleted **one at a time** in a scratch copy, fails all three (3 failed, 15 passed), and so does deleting all three; the file's 15 earlier tests detect none of them. They are complementary: a mutant that takes identity by output position instead of by row is killed by the two reordering tests, and a mutant that carries the previous row's identity into a chunk-less row is killed only by `test_rebuild_leaves_document_level_rows_without_chunk_identity`. Every score is distinct, so no expectation rests on a tie-break, a stable sort or the input order. Two notes, neither risen to a finding: in `test_cross_encoder_rerank_keeps_chunk_identity_of_survivors` the `relative_threshold=0.5` is inert, because the asserted pair is the same at 0.0, 0.5, 0.9 and 0.995 (three rows survive the threshold and `top_k=2` keeps the first two), so only the `top_k` cut is exercised there and `TestRelativeThreshold` covers the threshold; and none of the three pins `vectors_stale`, which is IN-02.
- **Title-cell assertions (`c95d2cee`).** The relaxation opened a hole; see IN-07. At `COLUMNS=80` on macOS the two tables render 15 `A`s and 34 `B`s, each followed by Rich's single-character `…`. The old literals were therefore the exact visible widths, which is why a column one narrower broke them. The product's own cell text is `title[:50] + "..."` (`src/sif/cli/commands/search.py:54`, applied at `:167`), which Rich then cuts to the column width; the only ASCII `...` in either table is the Content cell's (`:690-691`, `:925-926`).
- **Symlink substitutions (`c95d2cee`).** The four `symlink_or_skip(alias_dir, <dir>, target_is_directory=True)` calls (`tests/unit/database/test_repositories.py:116`, `tests/unit/search/test_context_attach.py:46`, `tests/unit/mcp/test_backend.py:381`, `:416`) are like-for-like with what they replaced: same link and target direction, and `target_is_directory=True` is the form `os.symlink` lacked for a directory target. They skip only when creation raises, so a Windows host that can create symlinks still runs them. The helper itself is too broad; see IN-08.
- **The two `skipif` guards (`c95d2cee`).** Neither skips where the asserted behaviour is testable, and neither masks a product failure; on this host neither skips.
  - `skipif(not hasattr(time, "tzset"))` on `test_set_stores_aware_utc_expiry` (`tests/unit/database/test_repositories.py:605`) is required, not cosmetic: `east_of_utc` calls `time.tzset()` unconditionally (`:71`), so the test would error at setup on Windows without it. It brings the test in line with the three sibling guards already in the file (`:621`, `:755`, `:769`). The cost is that the format `set()` writes is then asserted nowhere on Windows, although its two assertions do not depend on the local zone and `test_llm_cache_hit_expiry_replacement_and_clear` (`:519`) still exercises the write end to end there. A fixture that guarded its own `tzset` call would keep the test running on Windows too.
  - `skipif(sys.platform == "win32")` on `test_normalize_path_unexpandable_tilde_degrades_to_raw_form` (`tests/unit/search/test_context_attach.py:206-209`) is accurate: `ntpath.expanduser` builds `<profile parent>\<user>` for an unknown user instead of raising, so the raw-string fallback the test asserts is not what Windows does. The crash-safety half of that contract is still exercised on Windows by the unskipped sibling `test_malformed_tilde_row_does_not_crash_attach` (`:221`) wherever symlinks can be made.
- **Requirements.** CORR-02 is the one requirement this delta bears on, and `f8ff9bea` pins its chunk-identity half soundly. The title-cell assertions cover display code, not CORR-04's ranking. The alias, tilde and cache-expiry guards answer earlier phases' reviews and were only made Windows-honest.
- **CI.** Test Matrix run `45522236981` (push, `a25eb07`) succeeded on lint and all eight cells (Ubuntu and macOS, Python 3.10 to 3.13). The four `c95d2cee` files are byte-identical between `a25eb07` and HEAD, so that run exercised exactly the content reviewed here. `tests/unit/search/test_rerank.py` at `f8ff9bea` is newer than that run.

Not checked here: the full suite; the Windows branches of these guards, which no CI job exercises (the matrix run above has no Windows job) and which were judged by reading, so `c95d2cee`'s "one column narrower on Windows" is consistent with the macOS widths above but is not confirmed; the ten findings above, whose files were not re-read, so no recorded disposition was re-verified and none was changed; `src/sif/cli/commands/collection.py`, `src/sif/cli/commands/ls.py` and the seven other test files `c95d2cee` touched, and the helper's other ten call sites, all outside this override. Necessity was assessed against the rubric and yields no finding. No structural section is included because no structural pre-pass was configured. This pass was performed inline from `gsd-code-reviewer.md` by the orchestrator, because this runtime exposes no Agent tool; no external reviewer evidence was supplied.

### IN-07: Relaxed title assertions lost their lower bound, and the `...` check is not about the title

**File:** `tests/unit/cli/test_search.py:2097-2101` (`test_search_snippet_fallback_and_truncation`), `:2313-2317` (`test_vsearch_table_line_numbers_and_truncation`)
**Issue:** `c95d2cee` (quick task 261119-fww-02, not Phase 19 work) lowered the two prefix assertions from `"A" * 15` and `"B" * 34` to ten characters. What is still pinned: a ten-character prefix is rendered, the full 55-character title is not, and `...` occurs somewhere in the table. What the two tests exist for survives only in that weak form.

The hole is the lost floor. The old literals were the exact visible widths at `COLUMNS=80` on macOS (15 and 34), which is why one narrower column broke them, and that made them a tight lower bound on the product's own truncation, `_TITLE_MAX_LEN` (`src/sif/cli/commands/search.py:54`, applied at `:167`). These two tests are its only guard: no other test references `_title_cell` or `_TITLE_MAX_LEN`. Driving the constant down in a scratch probe, any value from 10 to 33 now passes the vsearch test and any from 10 to 14 the query test, where both failed before.

Two things the assertions do not establish, before or after the change. First, `assert "..." in result.output` is satisfied by the Content cell (`content[:200] + "..."`, `src/sif/cli/commands/search.py:690-691` and `:925-926`), not by the title. The title cell ends with Rich's single-character `…`, cut at the column width long before the product's own `...` at character 51. The comment `c95d2cee` added at `:2313-2314`, that the title "is truncated with an ellipsis", is true of the output but is not proved by the test. Second, the full title's absence is Rich's doing: with the product's truncation removed entirely, both the old and the new assertions still pass.

**Fix:** assert the product's truncation directly, which does not depend on the console, and the rendered shape rather than an exact column width. Every line below holds at HEAD.

```python
from sif.cli.commands.search import _TITLE_MAX_LEN, _title_cell

# The product truncates the title itself and marks it with "...":
assert _title_cell(row) == "A" * _TITLE_MAX_LEN + "..."
# ... and no shorter than 34, the floor the old vsearch literal enforced:
assert _TITLE_MAX_LEN >= 34
# Rich then fits the cell to a console-dependent width: assert the shape, not the count.
assert re.search("A{10,}…", result.output)
assert "A" * 55 not in result.output
```

The same four lines for the `B` test. The file already imports `re` and a private name from that module.

### IN-08: `symlink_or_skip` turns any `OSError` into a host-capability skip, so a broken fixture is skipped, not failed

**File:** `tests/support/__init__.py:26-32` (root cause; outside the five files reviewed here) and the four call sites this delta routed through it: `tests/unit/database/test_repositories.py:116`, `tests/unit/search/test_context_attach.py:46`, `tests/unit/mcp/test_backend.py:381`, `:416`
**Issue:** The helper documents that it skips when the host forbids a symlink, but it catches every `OSError` and labels each one "Windows requires Developer Mode or elevation; WinError 1314". A link path that already exists (`EEXIST`) and a missing parent directory (`ENOENT`) are fixture mistakes, not host restrictions, and both are reported as that skip. Both were reproduced from a scratch test calling the real helper.

`c95d2cee` (quick task 261119-fww-02) replaced direct `os.symlink` and `Path.symlink_to` with this helper at the four sites above. The helper itself comes from quick task 261119-fww-01 (`91a53c07`) and is one of the 59 files the default scope would have swept in. Neither quick task is Phase 19 work.

Nothing is masked today. On this host all 292 tests in the eight files that use the helper pass and none skips, and at these four sites the link is always a fresh child of a per-test `tmp_path`, so neither error can arise unless a fixture is changed later. That is why this is Info and not Warning. It is filed because the hazard is latent and wide: 14 call sites in eight test files inherit it, CI runs plain `pytest` with no skip-reason report and no skip budget, and one more skip would be indistinguishable from the platform skips the same quick tasks added on purpose.

**Fix:** skip only on the errors that mean the host cannot create symlinks, and let everything else fail. Checked in a scratch test: a fresh link is created, `EEXIST` and `ENOENT` raise, a permission error and the Windows privilege error still skip, and a wrong `target_is_directory` on Windows fails. `errno` is the only new import.

```python
try:
    link.symlink_to(target, target_is_directory=target_is_directory)
except NotImplementedError as exc:
    pytest.skip(f"symlink creation is unsupported on this host: {exc}")
except OSError as exc:
    host_cannot = exc.errno in {
        errno.EPERM, errno.EACCES, errno.ENOSYS, errno.EOPNOTSUPP,
    } or getattr(exc, "winerror", None) == 1314
    if not host_cannot:
        raise  # EEXIST, ENOENT, ... is a broken fixture, not a host restriction
    pytest.skip(f"symlink creation is unavailable on this host: {exc}")
```

## Incremental Re-review (2026-11-26)

**Scope:** the seven non-planning files changed since the last commit that touched this report (`bb0ab7f`), set through the workflow's `--files` override (Tier 1): `src/sif/cli/commands/search.py`, `src/sif/search/bm25.py`, `tests/unit/cli/test_search.py`, `tests/unit/cli/test_search_min_score.py`, `tests/unit/search/test_bm25.py`, `tests/unit/search/test_filters_sql.py` and `tests/unit/search/test_hybrid.py`. This pass covers `bb0ab7f..HEAD` for those seven files and nothing else. The range holds three gap-closure plans: 19-10 (UAT gap G-19-1 and the UAT test 3 decision; `4e258cf`, `8cf0ec9`, `5e83d6d`), 19-11 (an evidence artifact and a recorded decision; no code) and 19-12 (UAT gap G-19-2; `37b6315`, `d08f93c`, `38f4551`). This is not the phase's first review. Without the override, Tier 3 widens to every non-planning file changed since the archive commit `b817ebb`; that default scope was not used and was not reviewed. `docs/benchmarking.md`, `docs/changelog.md` and `docs/cli-reference.md` changed in the range too and lie outside the override; they were read only where a check below needed them. Reviewed at HEAD `4cf172c`. The seven files are byte-identical to their content at `d5382ae`, the commit the orchestrator's gates ran on; the two later commits touch only `19-12-SUMMARY.md` and `.planning/WINDOWS.md`.

**Result: four new Info findings, IN-09 to IN-12. No Critical and no Warning.** The twelve existing findings keep their id, title, severity and text, and no status changed. Three of them point into this delta and were re-checked at HEAD: IN-05, IN-07 and IN-08 all still stand (below). None of the twelve was fixed by it. `19-REVIEW-DISPOSITION.md` is not updated here; the orchestrator regenerates it. The frontmatter list now also carries the three files that were reviewed for this report but never listed: `tests/unit/search/test_rerank.py` (the 2026-11-25 pass, which calls it new to this report) and the two files below that were not in the original 47. The frontmatter counts now cover all sixteen findings: the 2026-11-25 pass added IN-07 and IN-08 to the body but left `info` at 6 and `total` at 10.

Checked at HEAD `4cf172c`:

- **State of the seven files.** `pytest` over the five test files reports 453 passed, 0 skipped (212, 2, 49, 116 and 74 per file); `ruff check` and `ruff format --check` are clean on all seven. The full suite, `ty` and the generated docs were not repeated: the orchestrator ran them on `d5382ae` (3303 passed, 1 skipped, coverage 95.16%) and the source is the same.
- **The re-pinned tests reject a direction regression.** Six mutants of `src/sif/search/bm25.py`, applied in memory by a scratch pytest plugin (no repository file was edited), against the four test files plan 19-12 touched (241 tests). The predicate flipped to `m.score >= ?`: 14 failed. The reciprocal score map restored in `search` only: 15 failed. The shared map `bm25_display_score` reverted, which reaches `search_chunks` as well: 13 failed. The rule for a threshold of 1 or more removed: 5 failed, among them `test_min_score_of_one_returns_no_results` through the real CLI. The four red runs recorded in `19-12-SUMMARY.md` therefore hold on the final tree, and five tests pin the regenerated SC1 `bm25_score` values.
- **Where the threshold is applied is pinned by the SQL text alone.** A mutant that drops the predicate from the SQL and filters in Python after the window, keeping ranks as `offset + position`, fails four tests, all of them assertions on the SQL text or the parameter list. No behavioural test can fail: since 19-12 the surviving rows are a prefix of the ranking, so the same rows come out whether the filter runs before or after `LIMIT ? OFFSET ?`. The mutant fails eight tests once it also renumbers the ranks, and `test_min_score_applies_before_offset_with_global_ranks` is one of them. That test now distinguishes the rank only, as deviation 3 of `19-12-SUMMARY.md` records.
- **`bm25_rank_threshold` at the edges.** `0`, `-0.0`, a negative value, NaN and negative infinity return `None`; `1`, a value above it and positive infinity return negative infinity; a value between 0 and 1 returns `-M/(1-M)` (`0.5` gives `-1.0`, `5e-324` gives `-5e-324`). Through the real CLI on a scratch index of the corpus of `tests/unit/cli/test_search_min_score.py`: `0`, `-0.0`, `-1`, `nan` and `1e-300` keep every row; `inf`, `1`, `2.5` and `0.9999999999999999` keep none; a separately written `--min-score -1` is accepted with exit 0. SQLite 3.51.0 binds negative infinity as a REAL and compares it exactly, so no row is kept. Each outcome has a test and matches the help text.
- **IN-05 still stands.** `BM25Searcher.search_chunks` still applies `min_score` in Python after `LIMIT ? OFFSET ?` (`src/sif/search/bm25.py:262-270`; the lines IN-05 cites have moved from 186-220). On a real `chunks_fts` table, `limit=1, offset=1` with a threshold that only the strongest row clears returns an empty page although that row qualifies. `git grep` finds no caller under `src/`; the method is test-only, as its docstring says. Two notes on the text of IN-05, which is left as written: the predicate it proposes, `m.score >= 1 - 1/min_score`, was the bound under the earlier score map and now points the wrong way (19-12 replaced it with `m.score <= -M/(1-M)`); and `search_chunks` keeps a second difference from `search`, since a NaN threshold drops every row there where `search` omits the predicate. The new IN-12 is on the same method.
- **IN-07 still stands.** The two assertions of `c95d2cee` are unchanged (`tests/unit/cli/test_search.py:2103-2105` and `:2319-2321`; IN-07 cites them six lines higher). With `_TITLE_MAX_LEN` driven down in memory, both tests pass at 33, 20, 15 and 10 and fail at 9, so ten characters is still the only floor. No test under `tests/` references `_title_cell` or `_TITLE_MAX_LEN` of `sif.cli.commands.search`.
- **IN-08 still stands.** `tests/support/__init__.py:26-32` is unchanged since `91a53c07` and still turns every `OSError` into a skip labelled as the Windows privilege error. Called from a scratch probe, a link path that already exists (`EEXIST`) and a missing parent directory (`ENOENT`) are both skipped. `git grep` counts the same 14 call sites in eight test files and none changed in this range; those eight files report 292 passed and 0 skipped, so nothing is masked today.
- **Chunk identity on the per-chunk tables (G-19-1, plan 19-10).** Rendered through the real CLI commands with the console width forced as the tests force it: at 80 columns, and at every width down to 30, each chunk row of both tables ends with its own `#sequence` for the four path shapes, with and without the Content column, and the document-level row of the hybrid page shows no `#`. The four layouts fit the console from 45, 57, 57 and 66 columns, as the plan states. At 200 columns the 31-, 49- and CJK-character paths render whole. `_chunk_column` gives 7 for a page whose widest address is `/a.md#0` and 8 for a page with a long path, so the column never reserves more than the page needs. A Windows path is cut after a backslash, a path of separators only and an empty path both keep the suffix, and sequence `0` renders as `#0`. The exclusions the second truth of plan 19-10 names reproduce and are no wider than it says: a line break in a path moves the suffix off the row's first line, a tab that survives in the visible tail is expanded by Rich and the suffix is cut, and a sequence of seven digits is kept at 80 columns but cannot fit the column floor of 8.
- **Markup in the Chunk cell.** A path holding `[red]bold[/red]` or `[link=http://x]go[/link]` renders literally in both tables, because `_ChunkAddress.__rich_console__` yields a `Text` that parses no markup. No test pins that; see IN-11.
- **The measured minimum of the Chunk cell.** `_ChunkAddress.__rich_measure__` returns `Measurement(width, width)`, so it reports a minimum equal to the full address. Rich's table layout never reads a column's measured minimum: `_calculate_column_widths` in Rich 14.3.3 and in 15.0.0, the two installed copies, uses only the maximum and the column's own `min_width`. The value reaches only `Table.__rich_measure__`, which the CLI never calls. Noted and not filed: it would matter only if a table holding these cells were measured by a surrounding renderable.
- **Per-chunk machine formats and path-only output (UAT test 3).** `format_results_csv`, `format_results_md` and `format_results_xml` take `per_chunk` as a keyword-only argument that defaults to `False`, and only `query_cmd` passes it (`src/sif/cli/commands/search.py:1358`, `:1369`, `:1380`); `search_cmd` calls them unchanged, so the default CSV header, Markdown and XML are byte-identical for every row, rows that carry a sequence included. The `sequence` cell is an integer or empty, and every document-derived value in the new `path` address passes through the existing `_xml_sanitize` and `xml_escape` treatment. `--files` and the quiet path of `query` and `vsearch` list each path once per page in per-chunk mode and one line per row otherwise (`:1001`, `:1338`), and `search_cmd` keeps its per-row loop. The field layout is the one human check 2 of plan 19-10 approved.
- **Requirements.** CORR-02: chunk identity is on both per-chunk tables at 80 columns and in CSV, Markdown, XML and path-only output; IN-11 is a missing pin, not missing behaviour. CORR-03: `min_score` is still a bound parameter in the outer WHERE of both SQL branches, ahead of the metadata filter and of `LIMIT ? OFFSET ?` (`src/sif/search/bm25.py:131-134`, `:175-177`, `:197-199`), and ranks stay global.
- **Hand-written material outside the override.** A search of `README.md`, `DESIGN.md`, `docs/*.md` and the shipped skills finds no sentence that still describes the earlier BM25 direction. The generated reference rows for `vsearch` and `query` keep "Minimum score threshold", as plan 19-12 requires (IN-10). The changelog entry closes with "to convert a threshold written against the old scores, subtract it from 1". That holds for `sif search search`. It cannot be applied to `sif search query`, because the same number is also the vector leg's threshold, which did not change.
- **An observation not filed.** Score cells keep four decimals (`src/sif/cli/commands/search.py:520`, `:547`, `:576`, `:800`, `:1039`, `:1410`, `:1428`). A term that appears in at least half of the scoped documents contributes an IDF that FTS5 floors near 1e-06, so such matches score about 1e-06 on the new scale. On a scratch index, `number`, a word in 19 of 20 documents, returned 19 ranked rows that all print `0.0000` in the table and `"0.0000"` in CSV while `--json` carries 1.2e-06, and `--min-score 0.0001` removed all of them. The direction is right, where the earlier map printed `1.0000` for the same rows. Whether four fixed decimals still suit the scale is a product question for a later change, not a defect of these plans.

Not checked here: the full suite, `ty` and the generated docs (the orchestrator's gates on `d5382ae` stand, see above); CI for this delta, because none of the 19-10, 19-11 and 19-12 commits is on a remote branch and the newest Test Matrix run on this branch is still run `45522236981` for `a25eb07`; a real 80-column terminal and the live renders, which are human check 1 of plan 19-10 and the human check of plan 19-12, both recorded as approved by the orchestrator on the operator's behalf (the latter in `19-12-SUMMARY.md` at `e822b28`, so it is not a gap); rendering under Rich 15.0.0, whose source was read but under which no table was rendered for this pass; the other eight findings of 2026-11-15, which point outside these seven files (WR-02 points into `search.py`, and its three `IntRange(min=1)` options are still in place at `:621`, `:829` and `:1065`); and `src/sif/search/hybrid.py`, `src/sif/search/vector.py`, `src/sif/search/rrf.py`, `src/sif/mcp/` and `tests/support/__init__.py`, which were read as callers and context only. Necessity was assessed against the rubric and yields no finding. One candidate was examined and left unfiled: the `max(options.max_width, 1)` at `src/sif/cli/commands/search.py:250` is inert, because `_fit_head` returns the same text for a budget of 0 and of 1, which is a redundancy rather than a guard against an impossible state. No structural section is included because no structural pre-pass was configured. This pass was performed inline from `gsd-code-reviewer.md` by the audit role, because this runtime exposes no Agent tool; no external reviewer evidence was supplied.

### IN-09: `--min-score` drops a row whose displayed score equals the threshold

**File:** `src/sif/search/bm25.py:73-77` (the bound), `:131-134` (the predicate), `:209` (the displayed score); `tests/unit/search/test_bm25.py:188` (the bound pinned for 0.8); `tests/unit/cli/test_search_min_score.py:125-128` (the assertion weakened for this reason)

**Issue:** The predicate is `m.score <= ?` with the bound computed as `-M/(1-M)`, and SQLite compares that double exactly. The displayed score is `|bm25|/(1+|bm25|)` rounded to a double. The two rounded operations are not exact inverses, so "Keep matches scoring at least this value" does not hold on the last bit. The second truth of plan 19-12 records this (about 46% on 200,000 sampled values) and places every test threshold midway between two rows. Measured for this pass on 200,000 samples per range: a row whose displayed score equals the threshold is dropped in 19.9% of cases when `|bm25|` is below 0.001, 26.4% below 1, 41.7% below 20 and 49.7% below 2000. In the other direction 9,555 of 57,546 neighbours one ulp weaker than the threshold are kept. Through the real CLI on a scratch index of 90 documents, 12 of the 60 matching rows disappeared when their own `--json` score was passed back as `--min-score`, and a threshold one ulp lower returned each of them. A clean case: `--min-score 0.8` binds `-4.000000000000001`, so a row with bm25 `-4.0`, which displays exactly `0.8`, is dropped.

The JSON output prints the score in full, so the round trip is exact up to this comparison. A person or an agent that narrows a result set with a score copied from the previous output loses that row in roughly a fifth to a half of attempts.

Snapping the bound with `math.nextafter` is not a reliable fix, because `bm25_display_score` is itself not monotone at the last bit. Near the top of a binade a stronger match can display one ulp less: in `[7.0, 7.0001)` 1,499,999 of 4,000,000 consecutive doubles do, the first being `7.000000000000002`, which displays `0.875` against `0.8750000000000001` for `7.000000000000001`. That needs two bm25 values on adjacent doubles and is not reachable in practice; it only means the first truth of plan 19-12, "displayed scores never increase down a best-first list", holds to within one ulp.

**Fix:** compare the displayed value itself in SQL, which removes the inverse and its rounding together. Keep the `None` and negative-infinity rules in `bm25_rank_threshold` (a NaN bound is NULL in SQLite and would keep no row) and write the predicate as:

```sql
AND abs(m.score) / (1.0 + abs(m.score)) >= ?
```

bound with `min_score` itself. Checked on 400,000 rows and their weaker neighbours: the SQL expression equals `bm25_display_score` on 200,000 of 200,000 samples and disagrees with the Python comparison on none, where the current bound disagrees on 199,896. The change re-pins the predicate text in the four SQL-text tests and turns the `0.8` row of the threshold table into the value that is then bound. It is optional at Info severity: the plan documents the limitation and no committed test sits on the boundary.

### IN-10: `sif query --min-score` filters each leg on its own scale and never the displayed score

**File:** `src/sif/cli/commands/search.py:1084` (the help text) and `:1214` (the value into `SearchOptions`); `src/sif/search/hybrid.py:121-143` (outside the override; the two legs and the single-leg fallback); `tests/unit/search/test_hybrid.py::TestHybridMinScoreLeg` (pins the per-leg behaviour)

**Issue:** `HybridSearcher.search` copies the caller's options, `min_score` included, into the fetch options of both legs. The BM25 leg keeps matches whose displayed BM25 score is at least the value (plan 19-12). The vector leg keeps rows whose own score, `1 - L2 / 2` on the scale IN-01 describes, is at least the value. Nothing compares the value with the score the page shows. On a fused page that score is the RRF value, at most 0.0328 at the default weights. Checked on the SC1 corpus with the test file's fake embedder: `min_score=0.5` on `gardening` returns three rows that display 0.0323, 0.0164 and 0.0161, beside leg scores of 0.55 (BM25) and 0.60 to 0.89 (vector). The Score column also changes scale with the threshold, because a page whose one leg was emptied is the other leg's rows with that leg's own scores (`hybrid.py:140-143`). On the same corpus `apple` displays 0.0325 down to 0.0159 at `min_score=1e-6` and 0.9441 down to 0.3979 at `min_score=0.01`, its two BM25 scores being 1.4e-06 and 1.3e-06. The help text of `query` still reads "Minimum score threshold", and the `min_score` of MCP `query` shares the path.

None of this is introduced by the three plans: the per-leg filter and the single-leg fallback predate them, and plan 19-12 was prohibited from changing the help text. It is filed because 19-12 changed what the flag does on a hybrid page and rewrote the help text of `search` to say what that flag means. That leaves `query` as the one search command whose `--min-score` returns rows that score below the stated minimum. 19-12 lists the scale difference as an observation outside its scope, and no review has recorded it.

**Fix:** a product decision, recorded either way before the Phase 22 parity work. Either say in the help text what the flag does on `query` (a threshold applied to each leg's own score before fusion, not to the Score column), or apply the threshold to the fused score after the single slice, which the requirements currently rule out. If the help text changes, regenerate `docs/cli-reference.md` and align `docs/mcp-server.md` and the tool descriptions in `src/sif/mcp/tools.py`.

### IN-11: No test pins that a markup-bearing path renders literally in the per-chunk Chunk cell

**File:** `tests/unit/cli/test_search.py:4155` (`TestPerChunkSurfaces`); `src/sif/cli/commands/search.py:249-250`

**Issue:** Plan 19-10 replaced the Chunk cell's `escape(path)` string with `_ChunkAddress`, whose `__rich_console__` yields a `Text` that parses no markup; its threat model (T-19-24) counts on that for the mitigation. The three CR-01 markup tests cover title, collection, query, content and `--explain`; none covers a path, and the per-chunk tests use paths without brackets. With `__rich_console__` replaced in memory by the same method yielding a plain string, `/notes/[red]bold[/red].md#0` renders as `/notes/bold.md#0`, and all 30 tests of `TestPerChunkSurfaces`, the five CR-01 markup tests and all 37 tests under `tests/` selected by `per_chunk`, `chunk_identity` or `path_sequence` still pass. The behaviour is right at HEAD. The next refactor of that method can silently reopen an injection that the delta closed.

**Fix:** one test in `TestPerChunkSurfaces` that renders both per-chunk tables with a row whose path holds `[red]bold[/red]` and `[link=http://x]go[/link]`, and asserts the literal text in the Chunk cell of each.

### IN-12: No test pins the score map in `search_chunks`, the one line 19-12 changed there

**File:** `src/sif/search/bm25.py:269`; `tests/unit/search/test_bm25.py:356-370`, `:821-830`

**Issue:** Plan 19-12 replaced the score conversion in `search_chunks` with a call to `bm25_display_score`, and its first truth says the method uses the same function as `search`. Nothing verifies it. The only test that reads a score from `search_chunks`, `test_search_chunks_returns_tuples`, feeds the mock row `-1.0`, where the new map and the earlier reciprocal map both give `0.5`, and asserts the document id alone; `test_search_chunks_sql_is_untouched` pins SQL text. With that one line reverted in memory, all 241 tests of the four files pass. The consequence of such a regression is the G-19-2 defect again, confined to this method: the filter on the next line is `score >= options.min_score`, so the best matches would be removed first. The method has no production caller (IN-05), which is why this is Info.

**Fix:** feed `-5.0` instead of `-1.0` and assert `results[0][2] == pytest.approx(5 / 6)`, as `test_display_score_rises_with_relevance` does for `search`; or delete the method, the other remedy IN-05 offers.

## Narrative Findings (AI reviewer)

### Critical Issues

#### CR-01: FTS title migration is not durable — the rebuild is rolled back while its DDL is committed

**File:** `src/sif/database/schema.py:291-354` (migration + population); `src/sif/mcp/backend.py:104-113`; `src/sif/cli/error_handling.py:44-56`; `src/sif/database/database.py:57-60`

**Issue:** `SchemaManager.create_all()` never commits its own writes, and pysqlite
auto-commits DDL but not DML. On a pre-CORR-04 database the migration executes (in order)
`DROP TABLE documents_fts_v` / `DROP TRIGGER documents_fts_*` / `DROP TABLE documents_fts`
/ `CREATE VIRTUAL TABLE documents_fts (... content, title ...)` — all committed
immediately — and then `INSERT INTO documents_fts(documents_fts) VALUES('rebuild')`
(schema.py:341-342), which opens the connection's implicit transaction. The vocab, trigger,
vector-table and index DDL statements that follow join that transaction. If the connection
is closed or the process fails before a commit, only the rebuild is rolled back. The next
open parses the stored DDL, sees `title`, sees no legacy trigger, so
`needs_rebuild_docs` and `legacy_delete_docs` are both false and the population is never
retried: `documents` has N rows and `documents_fts` has zero, silently.

Concrete triggers:

1. `sif status` (`src/sif/cli/main.py:185-226`) and `sif index status` are read-only and
   never enter a `with db.connection:` block, so `open_initialized_database` runs
   `init_schema()` and then `Database.close()` rolls the rebuild back. A user who upgrades
   and runs `sif status` before any search gets an empty BM25 index; `sif search` then
   returns nothing while `sif status` still reports the document count.
2. `SearchBackend.__init__` commits only after `init_schema` returns
   (backend.py:106-111). The dimension-mismatch `RuntimeError` is raised later, by
   `_create_vector_tables` (schema.py:437-452), so the `finally: db.close()` rolls the
   rebuild back. `tests/unit/mcp/test_backend.py:1141-1154` exercises exactly this
   sequence and does not notice the emptied index.
3. Any crash/interrupt (SIGKILL, power loss, disk-full) between the rebuild and the first
   subsequent commit leaves the same permanent state. The `chunks_fts` seed/rebuild
   statements (schema.py:343-354) have the identical shape.

Verified with the real code: seeding a legacy one-column index with one document, running
`Database.init_schema()` and closing without a commit, then reopening returns
`SELECT COUNT(*) ... MATCH 'body'` = 0, and a later corrected open still returns 0
(triggers are recreated, the population is not). Only `sif index update --force` (or a
touch of every file, whose mtime-only UPDATE fires the FTS update trigger) repopulates the
index.

**Fix:** make the schema writes self-committing and the migration atomic. Minimal change:

```python
# SchemaManager.create_all(), after _create_indexes()
self.db.commit()
```

and commit in `open_initialized_database_unmanaged` after `db.init_schema()`. That fixes
the read-only-command path, but the failure path (dimension mismatch, crash) still rolls
the rebuild back after the DDL committed, so also make the migration crash-safe — either
commit immediately after the population statements:

```python
if needs_rebuild_docs or legacy_delete_docs:
    self.db.execute("INSERT INTO documents_fts(documents_fts) VALUES('rebuild')")
if needs_rebuild_chunks:
    self.db.execute("INSERT INTO chunks_fts(rowid, content) SELECT rowid, content FROM document_chunks")
if legacy_delete_chunks:
    self.db.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")
self.db.commit()  # population survives every later failure
```

or wrap the drop/recreate/rebuild block in an explicit `BEGIN`/`COMMIT` so a failure rolls
the DDL back too and the legacy DDL re-triggers the migration on the next open. Either way,
add a regression test that closes and reopens the connection (and that runs the
dimension-mismatch construction) and asserts the FTS match count, trigger presence, and
`documents_fts` row count == `documents` row count afterwards.

#### CR-02: A non-string frontmatter `title` aborts the entire index update with a raw traceback

**File:** `src/sif/indexing/parser.py:67`; `src/sif/indexing/incremental.py:456-466` (create path), `441-450` (update path)

**Issue:** `title = cast("str", metadata.get("title", ""))` is an unchecked assumption.
Valid YAML such as `title: [not, a, string]` or `title: {a: b}` parses to a list/dict,
which is truthy, so it is returned as `ParsedDocument.title` and `Document.title`. The
write then fails at SQLite binding:

```
sqlite3.ProgrammingError: Error binding parameter 5: type 'list' is not supported
```

The create/update writes live outside `_process_file`'s parse `try` (only
`parser.parse()` is guarded), so the exception aborts the whole `sif index update` /
`update_paths` pass instead of being counted as a per-file `failed` and continuing — a
direct violation of the D-04 per-file failure-isolation contract. Reproduced end-to-end
with the real `IncrementalIndexer`: one note carrying `title: [not, a, string]` aborted
the pass with `ProgrammingError` and later files were never processed. CLI users see an
uncaught traceback rather than a `ClickException`. (The `cast` predates this phase, but the
phase's D-08 work explicitly made typed YAML metadata safe via `default=str`; titles were
left behind.)

**Fix:** coerce/validate the title and let the H1/stem fallback handle non-strings:

```python
raw_title = metadata.get("title", "")
title = raw_title.strip() if isinstance(raw_title, str) else ""
if not title:
    match = self.title_pattern.search(body)
    title = match.group(1).strip() if match else file_path.stem
```

Also move the create/update writes inside the per-file `try` (or catch `sqlite3.Error` /
`TypeError` around them) so any future per-document failure increments `failed` instead of
killing the run. Add a parser fixture with a list-valued `title:` and an incremental test
asserting the file is either titled from the H1/stem or counted as `failed`, never fatal.

### Warnings

#### WR-01: The convention migration never completes when any in-scope file permanently fails to parse, so every update re-parses and rewrites every document forever

**File:** `src/sif/indexing/incremental.py:195-197` (marker gate), `152-157` (announcement), `341-350` (docstring contract)

**Issue:** The D-09 marker is written only when `failed == 0` for the whole scan, and
`failed` counts every scanned file that raises — including files that will fail on every
run (a binary/PDF picked up by `pattern="**/*"`, a legacy Latin-1 `.md`, a permission-lost
file). One such file keeps `migrating` true forever. Each subsequent `sif index update`
then (a) takes the forced re-parse branch, (b) rewrites every unchanged-body document
through the D-07 metadata fast path (`updated`/`metadata_only` counts, `updated_at`
churn, an FTS update-trigger write per document), and (c) prints "Upgrading index format:
reindexing N documents once" again. Reproduced with the real indexer: runs 2 and 3 both
emitted `migrate 5`, rewrote the healthy document (`updated: 1`, `metadata_only: 1`), and
left the marker `None`.

**Fix:** gate the marker on failures among *stored* documents rather than all scanned
files (`failed_stored = sum(1 for p in failed_paths if p in existing_docs)`), or persist
the set of un-migrated stored paths in `index_meta` and retry only those on later passes.
Add a regression test with one permanently unparseable file plus one healthy `.md`,
asserting (1) the marker is eventually written and (2) a second pass leaves the healthy
document untouched (no `updated`/`metadata_only` count).

#### WR-02: `-n/--limit` accepts zero/negative values with three different behaviors, including an unbounded BM25 result set

**File:** `src/sif/cli/commands/search.py:452-458`, `637-643`, `827-833`; `src/sif/search/bm25.py:152`

**Issue:** The three CLI `--limit` options are `type=int` with no lower bound. With
`sif search -n -1`, the value reaches `LIMIT ?` and SQLite treats a negative LIMIT as "no
limit", returning the entire match set (I confirmed `LIMIT -1` yields all rows), while
`sif vsearch -n -1` / `sif query -n -1` clamp to one row (`vector.py:140`, `hybrid.py:33`)
and the MCP boundary rejects `<1` (`protocol.py:245`). `sif search -n 0` returns an empty
page while `sif query -n 0` returns one row. Same flag, three contracts; the negative case
can dump an unbounded result set into stdout/`--json`.

**Fix:** validate at the boundary with `type=click.IntRange(min=1)` on all three `-n`
options (and the bench `-n`), or clamp once in `_resolve_limit`; add a Click-level test
that `-n 0` / `-n -1` exits 2 or clamps consistently across `search`/`vsearch`/`query`.

### Info

#### IN-01: Vector scores are L2-derived but documented/converted as cosine distance

**File:** `src/sif/search/vector.py:186-189`

**Issue:** sqlite-vec `vec0` defaults to L2 distance (verified: `[3,4]` vs `[0,0]` returns
`distance = 5.0`), not cosine, yet `_row_to_result` computes `1.0 - distance / 2.0` under
the comment "Cosine distance is 0-2, convert to 0-1 score". The displayed score and the
`--min-score` threshold therefore live on an unbounded L2-derived scale (negative scores
are possible) rather than a 0-1 similarity. Pre-existing, not introduced by this phase,
but the phase's pagination/min_score work makes the displayed score part of the paging
contract. **Fix:** either add `distance_metric=cosine` to the vec0 DDL (schema change +
migration) or correct the comment and document the actual score scale before Phase 20/21
expose score filters.

#### IN-02: Rerank rebuild drops `vectors_stale`

**File:** `src/sif/search/rerank.py:52-72`

**Issue:** `_sort_and_build_results` copies `chunk_id`, `sequence`, `chunk_matches`,
`snippet`, `context_description` and `scores`, but constructs the new `SearchResult`
without `vectors_stale=result.vectors_stale`, so an enriched result passing through a
reranker silently loses the staleness marker. Latent today because `SearchPipeline`
enriches after reranking (`hybrid.py:357`), but it is a result-contract field and the same
rebuild already had to be patched for chunk identity. **Fix:** copy
`vectors_stale=result.vectors_stale` (or use `dataclasses.replace`) so future fields
cannot be dropped silently.

#### IN-03: Docs claim an MCP `vec_search` per-chunk surface that is not registered

**File:** `docs/benchmarking.md:208`

**Issue:** The new section says `--per-chunk` is available on `sif vsearch`/`sif query`
and "MCP `per_chunk` on `query`/`vec_search`". `create_default_tools()` registers only
`query`, `get`, `multi_get`, `status` (`src/sif/mcp/handlers.py:224-231`), and
`VecSearchInput` is explicitly Phase-22 scaffolding (`src/sif/mcp/protocol.py:292-304`),
so no `vec_search` tool exists today. **Fix:** name only `query` now, or mark
`vec_search` as future/Phase 22 in the sentence.

#### IN-04: Migration tests never reopen the database, so rebuild rollbacks are invisible (test quality)

**File:** `tests/unit/database/test_schema_title_fts.py:135-150`; `tests/unit/database/test_schema.py:369-409`; `tests/unit/mcp/test_backend.py:1141-1154`

**Issue:** Every migration assertion runs on the same open connection where the
uncommitted rebuild is still visible, so the rollback-on-close defect in CR-01 cannot be
caught. The dimension-mismatch test leaves the seeded pre-title DB in the emptied-FTS
state and asserts only the `RuntimeError`. **Fix:** add tests that (a) run the migration,
close the connection, reopen, and assert the FTS match count and trigger presence; and
(b) run the dimension-mismatch construction, then reopen at the correct width and assert
the pre-existing documents are still MATCHable.

#### IN-05: `BM25Searcher.search_chunks` violates the phase's pre-pagination min_score / global-rank contract

**File:** `src/sif/search/bm25.py:186-220`

**Issue:** Unlike `search()`, `search_chunks()` applies `options.min_score` in Python
after `LIMIT ? OFFSET ?` (lines 212-218) and never numbers ranks globally, so a page can
be short even when enough filtered matches exist and page continuity is broken. It has no
production caller today (only tests), so the defect is latent, but it contradicts the
documented "min_score before LIMIT/OFFSET" contract the phase established and is a trap
if a chunk path is ever wired to it. **Fix:** push the same rank-threshold predicate
(`m.score >= 1 - 1/min_score`) into the SQL before `LIMIT/OFFSET`, or delete the unused
method.

#### IN-06: MCP backend now silently fabricates an empty index at a nonexistent path

**File:** `src/sif/mcp/backend.py:104-113`; `src/sif/database/database.py:17-29`

**Issue:** `SearchBackend.__init__` now runs `init_schema` on the configured path, and
`Database.__init__`/`sqlite3.connect` create the parent directory and file. With a typo'd
`SIF_DB_PATH` (or starting the server before ever indexing), the backend now creates a
complete empty schema: `query` returns `[]` and `status` reports zero collections, instead
of the previous "no such table" error. The MCP CLI already prints a "No index found"
warning (`src/sif/cli/commands/mcp.py:59-64`), so this is a diagnosability regression
rather than data loss. **Fix:** warn explicitly when the DB file did not exist before
`init_schema` (or require an explicit allow-fresh flag for the MCP host), so a
misconfigured path is visible in the server log.

---

_Reviewed: 2026-11-15T05:04:54Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
