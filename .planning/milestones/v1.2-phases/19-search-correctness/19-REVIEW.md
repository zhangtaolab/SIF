---
phase: 19-search-correctness
reviewed: 2026-11-15T05:04:54Z
depth: standard
files_reviewed: 47
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
findings:
  critical: 2
  warning: 2
  info: 6
  total: 10
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
