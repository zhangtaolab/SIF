---
phase: 261105-wbj-embed-o-n-bug-src-sif-search-vector-py-2
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/sif/search/vector.py
  - tests/unit/search/test_vector.py
  - src/sif/cli/commands/index.py
  - tests/unit/cli/test_index.py
autonomous: true
requirements: [QUICK-PERF-EMBED-PREFETCH]  # quick task: fix O(N^2) embed completeness check (user-reported with root cause and fix direction; ~40k per-document full scans of a ~495k-row vec0 table, ~10h -> ~2s of scan time)
estimate:
  tokens: 20000
  raw_tokens: 20000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - "Batch method present: [ $(grep -c 'def get_all_embedded_chunk_ids' src/sif/search/vector.py) = 1 ] (baseline 0 at HEAD, planner-verified this session) — a new public VectorSearcher method returning dict[str, set[str]] built from ONE unfiltered SELECT of the document_id and chunk_id columns with zero bound parameters; the mock test asserts the SQL carries no WHERE clause and no params"
    - "Per-document vec0 scan eliminated from the embed loop: [ $(grep -c 'get_embedded_chunk_ids' src/sif/cli/commands/index.py) = 0 ] (baseline 1 at HEAD — the index.py:358 call) and [ $(grep -c 'get_all_embedded_chunk_ids' src/sif/cli/commands/index.py) = 1 ] (baseline 0) — the loop consults a prefetched dict via .get(doc.id, set()); no index.py comment names either method (a comment naming the removed method re-trips the =0 gate; naming the new one breaks the =1 gate)"
    - "Skip semantics unchanged: `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/cli/test_index.py -q` green (baseline 10 passed) — the three force-semantics tests (skip / heal-stale / force) pass with their existing assertions byte-unchanged; _needs_embedding (index.py:224-231) and its three call arguments are not modified"
    - "Batch map is per-document-equivalent on a real vec0 table: `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/search/test_vector.py -q` green (baseline 18 passed + 2 new tests) — the real-vec0 test asserts the batch dict equals the single-document lookup result for every document, and that a NULL chunk_id row is skipped by both forms"
    - "O(N^2) regression guard: the skip and heal tests assert the batch method was called exactly once per collection and the single-document lookup mock was never called — these assertions are RED at HEAD (the current loop performs the per-document call) and GREEN after the switch"
    - "Full quality suite green: ruff check src tests; ruff format --check src tests; env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q with 0 failures (676+ passed at HEAD per 261105-eev; FORCE_COLOR must be UNSET, not set to 0 — known spurious-failure mode in this repo)"
  artifacts:
    - "src/sif/search/vector.py — new method get_all_embedded_chunk_ids placed directly after the existing single-document lookup (vector.py:200-210, end of class): one static SELECT of document_id and chunk_id from document_embeddings with no WHERE clause and no parameters; iterate the cursor row-by-row (NOT fetchall — the table holds ~495k rows at the reported scale); build dict[str, set[str]] via setdefault(document_id, set()).add(chunk_id), skipping rows whose chunk_id is None; docstring states why the batch form exists (vec0 metadata columns are unindexed, so each filtered per-document lookup costs a full table scan) and that the NULL-skip contract matches the single-document lookup directly above it"
    - "tests/unit/search/test_vector.py — two new tests appended to TestVectorEmbeddingDeletion (after test_delete_embeddings_by_document_on_real_vec0, vector test file lines 383-423): a MagicMock test (file style: configure cursor, VectorSearcher(mock_db), set _vec_available = True, inspect mock_db.execute.call_args) and a real-vec0 equivalence test modeled on the existing real-vec0 test (sqlite_vec.load with pytest.skip fallback, vec0 table FLOAT[2])"
    - "src/sif/cli/commands/index.py — prefetch assignment inserted as the FIRST statement inside the per-collection try block (a new line between index.py:352 `try:` and :353 `with db.connection:`), preceded by a short method-name-free comment explaining the cost asymmetry (one unindexed metadata scan per document made the completeness check quadratic; prefetch once per collection instead); loop line 358 replaced by a dict .get(doc.id, set()) lookup against the prefetched map; lines 357 and 359 and the comment block at 355-356 untouched"
    - "tests/unit/cli/test_index.py — _make_embed_mocks (test_index.py:436-457) swaps its searcher stub to the batch method returning {d.id: set(embedded_chunk_ids) for d in docs}; the two regression assertions from the Task 2 behavior block added inside test_embed_cmd_default_skips_fully_embedded_document (test_index.py:499) and test_embed_cmd_default_heals_stale_embedding_state (test_index.py:521)"
  key_links:
    - "batch map <-> embed loop lookup: index.py consumes the map via .get(doc.id, set()) — a document absent from the map gets set(), so _needs_embedding re-embeds it exactly as an empty single-document query result would; documents with zero stored embeddings are never skipped"
    - "snapshot freshness <-> one-shot judgment: the prefetch is read before any write of that collection's transaction (first statement of the try, before the with db.connection block); every document is judged exactly once against the snapshot, so no dirty-read window is introduced — the old code also read each document exactly once, before its own delete"
    - "NULL chunk_id parity: both lookup forms skip NULL rows; a document carrying only NULL-chunk-id rows yields an empty set from either form and re-embeds, preserving the self-heal behavior established in Phase 03 (G-03-3 / exact chunk-id-set skip)"
    - "bare-MagicMock test compatibility: the seven other TestEmbedCommand tests (test_index.py:63-434) patch VectorSearcher with a bare MagicMock; .get on the resulting MagicMock returns a MagicMock that fails set equality exactly as the previously un-stubbed single-document mock did — both routes take the re-embed path, so those tests keep passing unchanged"
    - "error-path parity: a prefetch failure lands inside the per-collection try, so the existing except Exception -> failed_collections path (index.py:395-398) reports it as a failed collection instead of crashing the run — identical handling to a per-document read error today"
---

must legitimately appear (it is also part of the verification command's own grep regex):
<!-- planner-discipline-allow: get_all_embedded_chunk_ids -->
<!-- planner-discipline-allow: get_embedded_chunk_ids -->

<objective>
Fix the user-reported O(N^2) performance bug in the embed completeness check (root cause and fix direction user-provided):

**Root cause.** `VectorSearcher.get_embedded_chunk_ids(document_id)` (src/sif/search/vector.py:200-210) filters the sqlite-vec vec0 virtual table `document_embeddings` by `WHERE document_id = ?`. vec0 metadata columns have no secondary index, so every call is a near-full-table scan (~495,802 rows on the reporter's index). `embed_cmd` (src/sif/cli/commands/index.py:357-359) calls it once per document inside the main loop — ~40k scans at ~495k rows each, measured at roughly 10 hours, while one full read of the table takes ~1.9 seconds.

**Fix (semantics of the `_needs_embedding` judgment completely unchanged).**
1. vector.py: new batch method `get_all_embedded_chunk_ids() -> dict[str, set[str]]` — one SQL, full table, grouped by document_id in Python.
2. index.py: prefetch once before the per-document loop; in the loop, a dict `.get(doc.id, set())` lookup.
3. No dirty-read risk: each document is judged exactly once per run against the prefetch snapshot; snapshot entries are consumed exactly once (documents belong to exactly one collection; a collection's snapshot is read before any of its writes).

Planner-verified facts this session (executor may rely on them):
- index.py has exactly ONE production call site of the single-document method (index.py:358); grep count 1 at HEAD. vector.py defines it once (vector.py:200); it has its own tests and STAYS (public API, used by the new equivalence test).
- Grep-substring safety: a line containing only `get_all_embedded_chunk_ids(...)` does NOT match `grep 'get_embedded_chunk_ids'` (verified empirically) — the ==0 and ==1 gates below are jointly satisfiable.
- Baselines at HEAD: tests/unit/search/test_vector.py = 18 passed; tests/unit/cli/test_index.py = 10 passed; `grep -c 'get_all_embedded_chunk_ids'` in vector.py and index.py = 0 and 0.
- A full unfiltered SELECT on a real vec0 table works — the existing real-vec0 test already does `SELECT document_id FROM document_embeddings` (test_vector.py:418), and vec0 DELETE by non-key column (delete_embeddings_by_document) is established in production.
- Database connections set `conn.row_factory = sqlite3.Row` (src/sif/database/connection.py:27,128); sqlite3.Row supports tuple unpacking, so `for document_id, chunk_id in cursor:` works on both real connections and is what the mock test's cursor-iteration stub exercises.

Purpose: make `sif index embed` complete in minutes instead of ~10 hours on a 40k-document index with zero behavioral change to which documents get (re-)embedded.
Output: one new batch read method + tests, one call-site switch + regression assertions, full quality suite green.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@src/sif/search/vector.py
@src/sif/cli/commands/index.py
@tests/unit/search/test_vector.py
@tests/unit/cli/test_index.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: VectorSearcher batch method get_all_embedded_chunk_ids + mock and real-vec0 tests</name>
  <files>tests/unit/search/test_vector.py, src/sif/search/vector.py</files>
  <behavior>
    - Test 1 (mock, test_get_all_embedded_chunk_ids_groups_and_skips_none): MagicMock db + cursor with cursor.__iter__.return_value = iter over rows ("d1","c1"), ("d1","c2"), ("d1",None), ("d2","c3"); result == {"d1": {"c1", "c2"}, "d2": {"c3"}} (the NULL row is skipped, both d1 chunk ids grouped); mock_db.execute called exactly once; its SQL contains "SELECT document_id, chunk_id FROM document_embeddings"; the SQL contains no "WHERE"; no bound parameters (call_args[0][1:] == ())
    - Test 2 (real vec0, test_get_all_embedded_chunk_ids_matches_per_document_lookup_on_real_vec0): modeled on test_delete_embeddings_by_document_on_real_vec0 — sqlite_vec.load with pytest.skip fallback, CREATE VIRTUAL TABLE document_embeddings USING vec0 with embedding_id TEXT PRIMARY KEY, document_id TEXT NOT NULL, chunk_id TEXT, embedding FLOAT[2]; add_embeddings_batch with ("e1","d1","c1",[1.0,0.0]), ("e2","d1","c2",[0.0,1.0]), ("e3","d1",None,[1.0,1.0]), ("e4","d2","c3",[0.0,0.0]); batch result == {"d1": {"c1","c2"}, "d2": {"c3"}}; equivalence property: for each doc in ("d1","d2"), batch_result[doc] == searcher.get_embedded_chunk_ids(doc) — the single-document lookup on the same table
    - Both tests RED before the method exists (AttributeError), GREEN after
  </behavior>
  <action>Write the two tests first (confirm RED), then implement the method in src/sif/search/vector.py, placed directly after the existing single-document lookup at vector.py:200-210 (end of class). Signature: get_all_embedded_chunk_ids(self) -> dict[str, set[str]]. Body: ONE self.db.execute of a static SELECT naming exactly the document_id and chunk_id columns from document_embeddings — no WHERE clause, no query parameters; then iterate the cursor row-by-row (not fetchall — ~495k rows at the reported scale) unpacking each row into document_id and chunk_id, skip rows whose chunk_id is None, and accumulate via result.setdefault(document_id, set()).add(chunk_id) into a dict[str, set[str]] declared with an explicit annotation. Docstring: state the cost asymmetry that motivates the batch form (the vec0 virtual table has no index on its metadata columns, so each per-document filtered lookup costs a full table scan; callers judging every document must batch) and that NULL chunk_id rows are skipped with the same contract as the single-document lookup directly above (NULL can never equal a live chunk id, so documents carrying such rows re-embed and self-heal). Fully annotated per CLAUDE.md typing rules; comment text may name either method (no grep gate applies to vector.py beyond the def-count == 1 check, which a docstring cannot trip). Follow the file's existing test style for the mock test: MagicMock db, configure cursor, construct VectorSearcher(mock_db), set _vec_available = True, then inspect mock_db.execute.call_args.</action>
  <verify>
    <automated>env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/search/test_vector.py -q && [ "$(grep -c 'def get_all_embedded_chunk_ids' src/sif/search/vector.py)" = "1" ]</automated>
  </verify>
  <done>The batch method exists as the class's final method; both new tests pass (18 baseline + 2 = 20 in tests/unit/search/test_vector.py); the method issues exactly one unfiltered, parameter-free SELECT; NULL chunk_id rows are excluded; the real-vec0 test proves per-document equivalence.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: embed_cmd prefetches the batch map — per-document scan removed, regression-guarded</name>
  <files>tests/unit/cli/test_index.py, src/sif/cli/commands/index.py</files>
  <behavior>
    - RED-first regression assertions: inside test_embed_cmd_default_skips_fully_embedded_document (test_index.py:499) and test_embed_cmd_default_heals_stale_embedding_state (test_index.py:521), alongside the existing mock assertions, add mock_searcher.get_all_embedded_chunk_ids.assert_called_once() and mock_searcher.get_embedded_chunk_ids.assert_not_called() — at HEAD (before the code switch) the second assertion fails because the current loop performs the per-document call
    - Stub swap in _make_embed_mocks (test_index.py:436-457): replace the searcher's single-method stub line with mock_searcher.get_all_embedded_chunk_ids.return_value = {d.id: set(embedded_chunk_ids) for d in docs}
    - All three force-semantics tests (skip / heal-stale / force, test_index.py:499-561) pass with their existing assertions unchanged: skip test still expects delete_by_document NOT called, embed NOT called, "Already embedded" printed with the doc path; heal test still expects both deletes called once with doc.id and embed called once; force test unchanged
    - The seven other TestEmbedCommand tests (test_index.py:63-434, including the two-document test and the openai model-type test that patch VectorSearcher with a bare MagicMock) pass unchanged
  </behavior>
  <action>First add the two regression assertions and the _make_embed_mocks stub swap to tests/unit/cli/test_index.py and confirm the skip and heal tests are RED (heal/force still green — they re-embed either way). Then switch the call site in src/sif/cli/commands/index.py: (1) insert the prefetch as the FIRST statement inside the per-collection try block — a new line between the try at index.py:352 and the with db.connection at :353 — assigning vector_searcher.get_all_embedded_chunk_ids() to a local (e.g. embedded_by_doc), preceded by a short comment that contains NO method names (word it by concept: one unindexed metadata scan per document made the completeness check quadratic; prefetch the whole map once per collection and judge each document against it) so the ==0 and ==1 grep gates in this task's automated verify cannot be tripped by prose; (2) replace the per-document lookup at index.py:358 with a dict lookup on the prefetched map using .get(doc.id, set()) — a missing document maps to an empty set, preserving exactly the re-embed decision an empty query result produces today. Do NOT touch line 357 (chunk_repo.get_by_document), line 359 (_needs_embedding call), the comment block at 355-356, the _needs_embedding helper itself (index.py:224-231), or anything outside embed_cmd. Placement rationale the executor should preserve in the code arrangement: inside the try so a read failure follows the existing per-collection failure path (index.py:395-398) rather than crashing the run; before the with so the snapshot is read prior to any write of the collection's transaction. Then run the full test file to confirm GREEN (10 baseline tests + new assertions).</action>
  <verify>
    <automated>env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/cli/test_index.py -q && [ "$(grep -c 'get_embedded_chunk_ids' src/sif/cli/commands/index.py)" = "0" ] && [ "$(grep -c 'get_all_embedded_chunk_ids' src/sif/cli/commands/index.py)" = "1" ]</automated>
  </verify>
  <done>embed_cmd performs ONE batch read per collection and zero per-document completeness lookups (both grep gates hold: 0 for the single-document literal — baseline 1; exactly 1 for the batch literal — baseline 0); all 10 tests in tests/unit/cli/test_index.py pass including the two strengthened regression tests; skip/heal/force semantics byte-identical.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| local SQLite index file -> CLI process (read path) | the new full-table SELECT reads the same local vec0 table the old per-document queries read; no new boundary, no new input source, no new write path |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-wbj-01 | Denial of Service | get_all_embedded_chunk_ids (src/sif/search/vector.py) | low | mitigate | the full-table read materializes the entire document-to-chunk-id map in process memory (~495k UUID strings at the reported scale — order tens of MB plus dict/set overhead); mitigate by iterating the cursor row-by-row rather than fetchall so peak memory is the map itself; the map's size is accepted because it is bounded by the local single-user index and replaces ~10 hours of repeated full scans |
| T-wbj-SC | Tampering | package-manager installs | high | accept | no package installs in this task — sqlite3 is stdlib and all other dependencies are already declared in pyproject.toml; legitimacy gate not applicable |
</threat_model>

<verification>
Targeted (per-task automated gates above), then the CLAUDE.md full quality suite before marking done:

  ruff check src tests
  ruff format --check src tests
  env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q

(FORCE_COLOR must be unset, not set to 0, and NO_COLOR=1 set when running pytest in agent shells — known spurious-failure mode in this repo.)

Optional manual timing spot-check on the reporter's real ~40k-doc index (user-run, not agent-run): `time sif index embed` — expect the completeness-check phase to drop from hours to a single-digit number of full scans (one per collection, ~1.9s each per the user's measurement); the same documents must be skipped/embedded as before.
</verification>

<success_criteria>
- The embed loop performs one batched read per collection instead of one unindexed vec0 scan per document — both grep gates (0 single-document literal, exactly 1 batch literal in index.py) hold at commit time.
- `_needs_embedding` judgment semantics are provably unchanged: same helper, same arguments, empty/missing-map-entry documents re-embed, exact-set-match documents are skipped, `--force` bypasses, NULL-chunk-id rows still force re-embed (real-vec0 equivalence test).
- New O(N^2) regression guard: skip and heal tests fail if the per-document lookup is ever reintroduced into the loop.
- Full quality suite green (ruff check, ruff format --check, full pytest with 0 failures).
</success_criteria>

<output>
Create `.planning/quick/261105-wbj-embed-o-n-bug-src-sif-search-vector-py-2/261105-wbj-SUMMARY.md` when done
</output>
