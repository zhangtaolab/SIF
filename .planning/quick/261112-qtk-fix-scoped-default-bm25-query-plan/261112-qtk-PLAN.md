---
phase: 261112-qtk-fix-scoped-default-bm25-query-plan
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/sif/search/bm25.py
  - tests/unit/search/test_collection_filter.py
  - .planning/quick/261112-qtk-fix-scoped-default-bm25-query-plan/261112-qtk-SUMMARY.md
autonomous: true
must_haves:
  truths:
    - "Collection-scoped BM25 search executes a MATERIALIZED FTS match CTE: EXPLAIN QUERY PLAN of the exact statement BM25Searcher.search ran contains no per-document `:=`-constrained FTS scan (`SCAN fts VIRTUAL TABLE INDEX 32:=M1`), for a one-collection filter and a multi-collection filter alike."
    - "Scoped results preserve default scoring: for each filter shape, the scoped result set equals the unfiltered result set restricted to those collections with byte-identical score values (FTS5 rank unchanged; the 1.0/(1.0+abs(rank)) conversion untouched)."
    - "The unfiltered path (collection_ids=None, `--all`) keeps its existing SQL and plan byte-for-byte — no MATERIALIZE/sort step is introduced where the planner was already correct."
    - "Both audience commands are covered by the one searcher fix: `sif search search` calls BM25Searcher.search directly, and `sif search query` (the item's `sif query`) reaches it through SearchPipeline -> HybridSearcher -> BM25Searcher, both passing resolved non-empty collection_ids on the default path."
  artifacts:
    - "src/sif/search/bm25.py — the filtered branch of BM25Searcher.search builds `WITH matched AS MATERIALIZED (SELECT rowid, rank FROM documents_fts WHERE documents_fts MATCH ?)` joined to documents/collections with the collection predicate applied outside the CTE; the unfiltered branch SQL is unchanged."
    - "tests/unit/search/test_collection_filter.py — `_build_search_db` gains `idx_documents_collection` (the real-schema planner input); new `TestBM25ScopedQueryPlan` asserts plan shape on the executed SQL and scoped-vs-unfiltered score equivalence on a two-collection fixture."
  key_links:
    - "MATERIALIZED keyword <-> plan shape: without it SQLite flattens the CTE and drives `documents` by `idx_documents_collection`, re-running the FTS match per document; the keyword forces the match to be evaluated once before the join."
    - "Regression test <-> production SQL: the test records the statement BM25Searcher actually executed and EXPLAINs that same SQL with its own bound parameters, so the assertion cannot drift from the shipped query."
    - "Score preservation <-> alias: `m.rank AS score` carries the same FTS5 BM25 rank value the old `rank AS score` did; only the query shape changes."
---

<objective>
Fix the BM25 query plan used whenever a collection filter is present, so the default CLI search paths stop degrading to a per-document FTS scan. The fix is a query-shape change only: replace the collection-filtered `documents_fts JOIN documents ... WHERE documents_fts MATCH ? AND d.collection_id IN (...)` statement with a `WITH matched AS MATERIALIZED (...)` FTS match CTE whose collection filter is applied after the match is computed. Default scoring must stay byte-identical.

Why this matters: the DEFAULT CLI search is scoped, not unfiltered. `_resolve_collections` returns the enabled collections and every search command assigns `options.collection_ids = [c.id for c in collections]` (src/sif/cli/commands/search.py:472, :660, :874); only `--all` sets it to None. `sif search search` constructs `BM25Searcher` directly (search.py:487) and `sif search query` reaches it through `SearchPipeline -> HybridSearcher` (hybrid.py:60), so both commands hit the same degenerate plan on ordinary use.

**Planner-verified facts this session (PATH python 3.13.9, SQLite 3.51.0; executor re-establishes at HEAD):**

1. The current statement in `BM25Searcher.search` (src/sif/search/bm25.py:71-84) is `SELECT ... rank as score FROM documents_fts fts JOIN documents d ON fts.rowid = d.rowid JOIN collections c ON d.collection_id = c.id WHERE documents_fts MATCH ? [AND d.collection_id IN (...)] ORDER BY rank LIMIT ? OFFSET ?`.
2. With the real schema present (which includes `idx_documents_collection`, created at src/sif/database/schema.py:391), the filtered statement's EXPLAIN QUERY PLAN is `SEARCH c USING INDEX sqlite_autoindex_collections_1 (id=?)` -> `SEARCH d USING INDEX idx_documents_collection (collection_id=?)` -> `SCAN fts VIRTUAL TABLE INDEX 32:=M1` -> `USE TEMP B-TREE FOR ORDER BY`: the planner drives from `documents` and re-runs the FTS match once per candidate document. Reproduced through the real `BM25Searcher.search` on a two-collection fixture. The same SQL without the collection filter plans correctly (`SCAN fts VIRTUAL TABLE INDEX 32:M1` once, then PK lookups), which is why only the filtered branch needs to change.
3. A plain (non-MATERIALIZED) CTE is flattened by SQLite and reproduces the degenerate plan. `AS MATERIALIZED` is load-bearing and yields `MATERIALIZE matched` + a single `SCAN documents_fts VIRTUAL TABLE INDEX 0:M1`, then the join/filter. `AS MATERIALIZED` requires SQLite >= 3.35.0 (2021-03); supported CPython 3.10+ builds and the CI interpreter ship newer SQLite.
4. Equivalence probe on the two-collection fixture: the MATERIALIZED shape returned the same document ids and identical score values as the current statement for the no-filter, one-id, and two-id shapes; the scoped ids/scores equal the unfiltered ids/scores restricted to the requested collections.
5. The item reports a read-only validation on a 20k-document corpus: 72.7s -> 0.03s. The executor does not need to re-measure; the regression test pins the plan shape deterministically instead of a timing threshold.

Purpose: restore default search latency on realistically sized indexes without touching ranking semantics, and lock the fix in with a plan-shape regression test.
Output: two-branch SQL in `BM25Searcher.search` (MATERIALIZED CTE for the filtered case, unchanged SQL for the unfiltered case) plus regression tests proving scoped correctness, byte-identical scores, and the absence of the per-document FTS scan.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@src/sif/search/bm25.py
@src/sif/search/hybrid.py
@tests/unit/search/test_collection_filter.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Replace the collection-filtered FTS join with a MATERIALIZED match CTE</name>
  <files>src/sif/search/bm25.py</files>
  <action>
In `BM25Searcher.search` (src/sif/search/bm25.py), split the single interpolated statement into two branches while keeping the sentinel early return, `fts_query`, and parameter assembly (`params = [fts_query]`, then extend with `options.collection_ids` when non-empty, then extend with `options.limit, options.offset`) unchanged.

Filtered branch — when `options.collection_ids` is non-empty: build the statement as a CTE named `matched` declared `AS MATERIALIZED` that selects `rowid, rank` from `documents_fts` with `WHERE documents_fts MATCH ?`. The outer SELECT keeps the existing output column names exactly — `d.id as document_id`, `d.title`, `d.path`, `c.name as collection_name`, and `m.rank as score` — reading `FROM matched m JOIN documents d ON m.rowid = d.rowid JOIN collections c ON d.collection_id = c.id`, with the collection predicate applied OUTSIDE the CTE as `WHERE d.collection_id IN (<placeholders>)`, and `ORDER BY m.rank LIMIT ? OFFSET ?`. Generate the placeholders with the same one-`?`-per-id formula the code uses today. Do not move the MATCH into the outer SELECT and do not put the collection predicate inside the CTE.

Unfiltered branch — when `options.collection_ids` is None: keep the existing SQL byte-for-byte (`FROM documents_fts fts JOIN documents d ... JOIN collections c ... WHERE documents_fts MATCH ? ORDER BY rank LIMIT ? OFFSET ?`). Its plan is already the single FTS scan, and routing it through a materialized CTE would add an unnecessary sort.

Leave the row-to-`SearchResult` conversion, the `score = 1.0 / (1.0 + abs(row["score"]))` formula, the empty-list exclude-all sentinel, `_attach_contexts`, `search_chunks`, and every other method untouched. The full `params` ordering must remain `[fts_query, *collection_ids, limit, offset]` so no caller or test sees a parameter change.

Above the filtered SQL assignment, add a concise comment (roughly 5-8 lines) that states why the keyword cannot be dropped: the scoped default CLI path always carries a non-empty collection filter; with a plain CTE or a bare join, SQLite drives from `documents` via `idx_documents_collection` and applies the MATCH per document (`SCAN fts VIRTUAL TABLE INDEX 32:=M1`, cost proportional to candidate documents); `AS MATERIALIZED` computes the match once before the join; SQLite >= 3.35.0 is required for the keyword.

Do NOT apply the CTE shape to the unfiltered branch, do NOT add query-plan hints or CROSS JOIN tricks as substitutes, and do NOT modify the scoring path.
  </action>
  <verify>
    <automated>python -m pytest tests/unit/search/test_bm25.py tests/unit/search/test_collection_filter.py -q --no-cov && ruff check src/sif/search/bm25.py && ruff format --check src/sif/search/bm25.py</automated>
  </verify>
  <done>`BM25Searcher.search` executes a `WITH matched AS MATERIALIZED (... WHERE documents_fts MATCH ?)` CTE when `collection_ids` is non-empty, with `WHERE d.collection_id IN (...)` outside it and `ORDER BY m.rank`; the unfiltered SQL is unchanged; the score formula and result column aliases are unchanged; both existing search test modules pass and ruff check/format are clean on the file.</done>
</task>

<task type="auto">
  <name>Task 2: Add the multi-collection plan-shape and scoring regression tests</name>
  <files>tests/unit/search/test_collection_filter.py</files>
  <action>
In tests/unit/search/test_collection_filter.py:

(a) Extend `_build_search_db` with `CREATE INDEX idx_documents_collection ON documents(collection_id)` immediately after the documents table creation, carrying a one-line comment that the real schema creates this index (src/sif/database/schema.py:391) and that it is the planner input which makes the collection-filtered join degenerate. Keep the rest of the fixture (two collections: c1 holds d1+d2, c2 holds d3, every content containing "python") unchanged so the existing sentinel tests keep covering the same data.

(b) Add a `TestBM25ScopedQueryPlan` class with a small recording proxy defined in the test module: it wraps a real `sqlite3.Connection`, exposes `execute(sql, parameters=())` that appends `(sql, parameters)` to a `calls` list and then delegates to the wrapped connection, and nothing else is needed because `BM25Searcher` only calls `.execute`. Use it with `include_highlights=False` throughout (keeps the recorded statements to the FTS query plus the context/staleness reads).

(c) `test_scoped_plan_uses_materialized_match_cte`, parametrized over `collection_ids` shapes `["c1"]` and `["c1", "c2"]`: run `BM25Searcher(recorder).search("python", SearchOptions(collection_ids=<shape>, include_highlights=False))`; pick the recorded statement containing `MATCH` (capture it and its parameters BEFORE running any EXPLAIN, because the EXPLAIN text also contains the word MATCH); assert `MATERIALIZED` appears in the uppercased SQL; run `EXPLAIN QUERY PLAN` with that exact SQL and its recorded parameters; collect each plan row's detail (index 3); assert no detail contains `:=`; assert at least one detail mentions `documents_fts` and that every such detail also contains `M1`; assert some detail contains `MATERIALIZE`. This test is the regression: at HEAD the recorded SQL has no MATERIALIZED and the plan contains the per-document `:=M1` FTS scan on this fixture (planner-verified), so it fails before Task 1 and passes after.

(d) `test_scoped_scores_match_unfiltered`, parametrized over the same two shapes: run a scoped search and an unfiltered search (`collection_ids=None`) on the same in-memory fixture (fresh `BM25Searcher` instances; the recording proxy is optional here, a real connection is fine); assert the scoped document-id set equals the ids of the unfiltered results whose `collection_name` is in the shape's expected names ("one" for c1; "one" and "two" for c1+c2), and assert each scoped result's `score` equals the unfiltered score for the same document id with exact `==` (compare dictionaries keyed by document id — FTS rank ties are not order-stable across plan shapes, so do not assert list order). This pins "preserve default scoring byte-for-byte".

Do not loosen or delete any existing sentinel test; do not assert on a wall-clock latency threshold (the plan-shape assertion is deterministic and machine-independent).
  </action>
  <verify>
    <automated>python -m pytest tests/unit/search/test_collection_filter.py -q --no-cov && python -m pytest tests/unit/search/test_bm25.py -q --no-cov && ruff check tests/unit/search/test_collection_filter.py && ruff format --check tests/unit/search/test_collection_filter.py</automated>
  </verify>
  <done>`_build_search_db` creates `idx_documents_collection`; `TestBM25ScopedQueryPlan` exercises both filter shapes, proves the executed SQL is MATERIALIZED with no `:=`-constrained FTS scan in its plan, and proves scoped results/scores equal the unfiltered results restricted to the requested collections; existing sentinel tests still pass; ruff check/format clean on the test file.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| user query string -> FTS5 MATCH | raw free-text input becomes the MATCH parameter |
| CLI/MCP collection ids -> SQL IN list | collection identifiers cross into the statement |
| local SQLite index -> BM25 read path | read-only query against user-owned data |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-qtk-01 | Tampering | BM25Searcher.search SQL construction | low | mitigate | the collection ids stay bound `?` placeholders inside `IN (...)` and the FTS expression stays the bound MATCH parameter; the only new SQL text is static (CTE name, keywords, fixed column list), so no user data is interpolated anywhere |
| T-qtk-02 | Denial of Service | MATERIALIZED match CTE on broad queries | low | accept | materialization holds one row per FTS match for that query; FTS5 already computes and sorts the full match set to satisfy ORDER BY rank, so the CTE is the same order of work as the previously correct unfiltered plan and strictly better than the per-document scan it replaces |
| T-qtk-SC | Tampering | package-manager installs | high | accept | no package installs: the change uses the Python stdlib `sqlite3` module only; package-legitimacy gate not applicable |
</threat_model>

<verification>
Per-task gates above, then the full CLAUDE.md quality suite before marking the plan done:

  ruff check src tests
  ruff format --check src tests
  env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q

FORCE_COLOR must be UNSET (not set to 0) and NO_COLOR=1 set when running pytest in agent shells — known spurious-failure mode in this repo. The full suite is the merge gate; run it after both tasks, not on a subset (the pytest addopts enforce `--cov=src/sif ... fail_under=90`, so `--no-cov` is appropriate only for the targeted task gates above). Planner baseline at HEAD 1e0eac5 this session: 1591 passed, 1 skipped, coverage 93.78%; the post-change run must show 0 failures (the two new tests raise the passed count).

Optional user-run confirmation on a large real index: time `sif search <term>` before and after; the item reports 72.7s -> 0.03s on a 20k-document corpus. Plan shape, not timing, is the automated gate.
</verification>

<success_criteria>
- The default scoped CLI paths (`sif search search`, `sif search query`) execute the MATERIALIZED match CTE; EXPLAIN QUERY PLAN of the executed statement shows the FTS match evaluated once with no `:=` constraint in its index detail.
- Ranking semantics are untouched: for both a one-collection and a multi-collection filter, scoped ids and score values exactly equal the unfiltered results restricted to those collections.
- The unfiltered (`--all`, `collection_ids=None`) statement is unchanged, so its already-correct plan and behavior stay byte-identical.
- The regression test fails against the pre-fix SQL (no MATERIALIZED; per-document `:=M1` scan present on the indexed fixture) and passes after the fix.
- Full quality suite green: ruff check, ruff format --check, and the complete pytest run with 0 failures.
</success_criteria>

<output>
Create `.planning/quick/261112-qtk-fix-scoped-default-bm25-query-plan/261112-qtk-SUMMARY.md` when done
</output>
