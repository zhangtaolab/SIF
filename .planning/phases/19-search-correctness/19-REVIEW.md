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
