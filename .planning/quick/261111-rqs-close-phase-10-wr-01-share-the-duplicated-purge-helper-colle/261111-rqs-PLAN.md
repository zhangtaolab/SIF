---
phase: quick-261111-rqs
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/sif/search/vector.py
  - src/sif/indexing/incremental.py
  - src/sif/cli/commands/collection.py
  - tests/unit/cli/test_collection.py
  - .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
autonomous: true
requirements:
  - PHASE10-WR-01
must_haves:
  truths:
    - "sif collection remove leaves ZERO document_embeddings (vec0) rows for the removed collection's documents, proven on a fresh sqlite-vec-loaded connection"
    - "A sibling (keeper) collection's documents, chunks, documents_fts/chunks_fts rows, and vec0 embeddings all survive the removal unchanged"
    - "collection remove still succeeds on BM25-only installs where sqlite-vec is unavailable (purger None path, fail-soft)"
    - "IncrementalIndexer purge behavior is byte-preserving: the existing purge-ordering and update_paths purge tests pass unmodified against the shared helper"
    - "Exactly ONE purger-construction helper definition exists in src/ after the change, used by both IncrementalIndexer and collection_remove"
    - "WR-01 is marked fixed in the ledger with Source naming quick 261111-rqs; the open count is decremented exactly once from its EXECUTION-TIME value; all other records stay byte-identical"
  artifacts:
    - src/sif/search/vector.py
    - src/sif/indexing/incremental.py
    - src/sif/cli/commands/collection.py
    - tests/unit/cli/test_collection.py
    - .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
  key_links:
    - "collection_remove -> create_embedding_purger(conn) -> VectorSearcher.delete_embeddings_by_document per doc id, BEFORE DocumentRepository.delete_by_collection, inside the same db.transaction()"
    - "IncrementalIndexer.__init__ -> the SAME create_embedding_purger (single shared definition; private incremental copy removed)"
    - "WR-01 YAML disposition + execution-time open-count decrement + WR-01 markdown row -> one consistent ledger with exactly three edited lines"
---

<objective>
Close Phase 10 WR-01 only: "`collection remove` orphans vec0 embeddings — vector search pollution until `sif cleanup`". The original finding (10-REVIEW.md, "WR-01", lines 58-70) names:

1. `collection_remove` in `src/sif/cli/commands/collection.py` (finding cited lines 89-96; live: command at 75-98, the delete call at line 93) deletes documents (cascade removes chunks) but never purges `document_embeddings`. The vec0 virtual table cannot carry the FK cascade, so every embedding of the removed collection is orphaned in the KNN index — the exact failure mode `index update`'s removal path explicitly guards against.
2. `DocumentRepository.delete_by_collection` in `src/sif/database/repositories.py` (finding cited 235-252; live: 250-267) also skips the purge — it is the mechanism `collection_remove` calls.
3. The finding's fix: "Purge embeddings before deleting documents, mirroring `update_cmd`" using `_embedding_purger(db)` — "reuse the helper from index.py, or move it to a shared module".

Live re-verification at planning time (src/ and tests/ are byte-identical to batch base 802c08c; later HEAD commits touched only .planning/): the helper the finding calls "from index.py" was moved by Phase 11 into `src/sif/indexing/incremental.py:58-69` as private `_embedding_purger(conn) -> VectorSearcher | None`. `collection.py` contains NO purge logic at all (lines 75/93 are the defect site, not a second copy). `IncrementalIndexer._remove_document` (incremental.py:385-396) is the guarded precedent: vec0 purge BEFORE the row delete, one short transaction. `VectorSearcher.delete_embeddings_by_document` (vector.py:196-206) is the parameterized vec0 DELETE. Baseline scoped battery green at planning time: `pytest tests/unit/cli/test_collection.py tests/unit/indexing/test_incremental.py tests/unit/search/test_vector.py tests/unit/database/test_repositories.py --no-cov -q` → 69 passed.

Design decisions (planner discretion, recorded for the executor — do not improvise alternatives):

- D1 — Shared helper home: promote the helper to a PUBLIC module-level `create_embedding_purger(conn: sqlite3.Connection) -> VectorSearcher | None` in `src/sif/search/vector.py`, body moved VERBATIM from incremental.py (try VectorSearcher(conn) / except RuntimeError -> None), preserving its docstring contract ("missing sqlite-vec also means no vec0 table — callers treat None as nothing to purge"). One definition, two consumers. The `create_*` name follows the existing `create_chunker` / `create_reranker` factory convention. vec0 expertise stays in the search layer where VectorSearcher lives.
- D2 — Purge orchestration stays in the CLI: `collection_remove` purges BEFORE calling `doc_repo.delete_by_collection`, exactly the finding's fix snippet. `src/sif/database/repositories.py` stays BYTE-IDENTICAL: repositories remain vec0-free (VectorSearcher owns all document_embeddings SQL; `_remove_document` is the layering precedent), and `delete_by_collection`'s only production caller is `collection_remove` (grep-verified: src/sif/cli/commands/collection.py:93 is the sole call site), so the CLI-side purge covers the entire reachable chain the finding names. Its relational contract (documents + chunks, return count) remains pinned by the existing `tests/unit/database/test_repositories.py::test_delete_by_collection_removes_documents_and_their_chunks`. This also keeps zero file overlap with sibling item 261111-rqq, which owns repositories.py in this batch.
- D3 — Id-only projection: collect doc ids with the finding's parameterized `SELECT id FROM documents WHERE collection_id = ?` — NOT `doc_repo.list_by_collection`, which would materialize every document's full content for a purge that only needs ids.
- D4 — Fail-soft None path preserved: without sqlite-vec, `create_embedding_purger` returns None and removal proceeds exactly as today (BM25-only installs unaffected).

Purpose: removed collections stop polluting KNN top-k slots, with one shared purger-construction helper and zero semantic change to any existing purge path.
Output: shared `create_embedding_purger` in vector.py, rewired IncrementalIndexer, fixed collection_remove, two real-SQLite regression tests (one red-to-green), and WR-01 marked fixed in the ledger without disturbing any other record.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW.md
@.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
@src/sif/cli/commands/collection.py
@src/sif/indexing/incremental.py
@src/sif/search/vector.py
@tests/unit/cli/test_collection.py
@tests/unit/indexing/test_incremental.py

Planning evidence (all grounded live; src/tests identical to base 802c08c):
- Defect site: `collection.py:75-98` — `collection_remove` opens `with db.transaction() as conn:`, resolves the collection, then `doc_repo.delete_by_collection(collection.id)` (line 93) and `repo.delete(collection.id)` (line 96). No embedding purge anywhere in the file. The function-local `from sif.database.repositories import DocumentRepository  # noqa: PLC0415` (line 90) stays as-is.
- Helper to share: `incremental.py:58-69` — private `_embedding_purger` with a function-local `from sif.search.vector import VectorSearcher  # noqa: PLC0415`; consumed at `incremental.py:92` (`self._vector_purger = _embedding_purger(conn)`). The `TYPE_CHECKING` import of VectorSearcher (lines 35-36) exists for annotations. No test patches this private name (grep-verified); the purge-ordering test injects its mock via `indexer._vector_purger = purger` (test_incremental.py:307), so the move breaks no patch target.
- Purge precedent: `incremental.py:385-396` `_remove_document` — purge BEFORE `doc_repo.delete`, one `with self._conn:` transaction; docstring already cites WR-01.
- vec0 DELETE: `vector.py:196-206` `delete_embeddings_by_document` — parameterized `DELETE FROM document_embeddings WHERE document_id = ?`, returns rowcount. `VectorSearcher.__init__` raises RuntimeError when `SELECT vec_version()` fails (vector.py:16-32) — this is the exact exception the shared helper catches.
- Connection wiring: `Database` (database.py) creates connections via `factory.create_connection`, which loads sqlite-vec when installed (factory.py:113-125, failure swallowed). `db.transaction()` yields the connection, commits on clean exit, rolls back on exception — the purge joins the removal's existing atomic unit.
- CRITICAL test pitfall — dim guard: `SchemaManager` raises "Embedding dimension mismatch" when an existing vec0 table's FLOAT[dim] disagrees with settings (schema.py:365-374). `collection remove` calls `db.init_schema()`, so a test that seeds an 8-dim vec0 table MUST patch `sif.config.settings.get_settings` to return `Settings(embedding_dim=8, model_name="test", cache_embeddings=False)` during BOTH seeding AND the CliRunner invoke — the exact pattern of `test_incremental.py:_test_settings/_seed_collection` (lines 40-58). `documents_fts` indexes `content` with the porter tokenizer (schema.py:245-251); insert/delete triggers keep it synchronized, so unique lowercase probe tokens in document content are MATCH-assertable on a fresh connection without sqlite-vec.
- Test hosts: `tests/unit/cli/test_collection.py` `TestCollectionRealDatabase` (line 26) provides autouse `isolated_settings` (get_settings cache_clear), `notes_dir`/`sibling_notes_dir` fixtures, `_invoke` (CliRunner, `--index <tmp>`, `collection` subcommand, COLUMNS=200), `_seed`, `_read_collection`. Existing `test_remove_and_missing_remove` (line 119) must pass unmodified. `test_incremental.py` provides the reusable patterns: `_embedding_count` (lines 107-125: fresh connection + enable_load_extension + sqlite_vec.load, pytest.skip on ImportError) and real-embedding seeding via `VectorSearcher(db.connection, embedding_dim=8).add_embedding(f"e-{doc.id}", doc.id, f"c-{doc.id}", [0.1] * 8)` (lines 456-461). Seed REAL chunk_id strings — vec0 v0.1.9 rejects NULL TEXT metadata on INSERT (Phase 14 lesson in STATE.md).
- Existing behavior guards that must pass UNMODIFIED after the helper move: `test_incremental.py::test_removed_file_purges_embeddings_before_document_delete` (line 271, purge-before-delete ordering), `::test_update_paths_purges_embeddings_of_modified_doc` (line 432, real vec0 purge), `tests/unit/database/test_repositories.py::test_delete_by_collection_removes_documents_and_their_chunks` (line 360, relational contract).
- Environment (verified at planning time): PATH pytest/python/ty/ruff resolve to miniconda base (NOT .venv — no torch there); `import sqlite_vec` succeeds; targeted runs use `--no-cov`; suite is color-env-hermetic.

Batch constraints (orchestrator):
- SHARED LEDGER: items 261111-rqp / 261111-rqq / 261111-rqs close records in the SAME ledger. At execution time the `open:` count may already be below the planning-time 16. Read the CURRENT value and decrement by 1 — never hardcode a planning-time literal. The closure gate compares against execution-time `git show HEAD:<ledger>`.
- Ledger convention: exactly THREE edits per record (YAML disposition, open-count decrement, markdown table row with Source cell naming quick 261111-rqs). NO `**Status:** resolved` lines in this ledger. All other records byte-identical.
- Preserve pre-existing uncommitted .planning/ churn (config.json, state.json, agent-history.json, tmp/, PATTERNS files, research cache, 16-REVIEW iter2 files, STATE.md edits): never stage, commit, or revert them. Commit with explicit file scopes only.
- Never hand-edit docs/cli-reference.md or docs/configuration.md (generator-owned). This change alters no CLI signature, option, or argument — no docs regeneration is needed or permitted.
</context>

<tasks>

<task type="auto">
  <name>Task 1: RED — real-SQLite regression tests for collection-remove vec0 purge (WR-01)</name>
  <files>tests/unit/cli/test_collection.py</files>
  <precondition>PATH python imports sqlite_vec (verified at planning time: miniconda base). If it is missing at execution time the vec0 assertions would skip and RED cannot be demonstrated — halt and report instead of proceeding.</precondition>
  <action>
Add two tests to `TestCollectionRealDatabase` in tests/unit/cli/test_collection.py, plus one small seeding helper and one vec0 read helper. Do NOT modify any existing test or helper in this file.

Seeding helper (new private method, e.g. `_seed_embedded_collection`): under `patch("sif.config.settings.get_settings", return_value=Settings(embedding_dim=8, model_name="test", cache_embeddings=False))` (import Settings from sif.config.settings; mirror test_incremental.py `_test_settings`/`_seed_collection`), open `Database(db_path)`, call `init_schema()`, and in one `db.transaction()` create: a Collection (given name/path), one Document whose content contains a unique lowercase FTS probe token (e.g. "purgeprobealpha" for the removed collection, "purgeprobekeeper" for the keeper), one DocumentChunk for that document (real id string, sequence 0, start_pos 0, end_pos len(content)), and one REAL vec0 embedding via `VectorSearcher(conn, embedding_dim=8).add_embedding(f"e-{doc.id}", doc.id, f"c-{doc.id}", [0.1] * 8)` — real chunk_id string, never None (vec0 v0.1.9 rejects NULL TEXT metadata). Return the document id. Close the Database. The dim-8 settings patch is mandatory: schema.py's dimension-mismatch guard raises if init_schema later sees a different dim.

Vec0 read helper (module-level or static, mirroring test_incremental.py `_embedding_count` lines 107-125): fresh `sqlite3.connect(db_path)`, `enable_load_extension(True)`, `sqlite_vec.load(conn)`, `enable_load_extension(False)`, return the set of document_ids from `SELECT document_id FROM document_embeddings`; `pytest.skip("sqlite-vec not available")` on ImportError; close in finally.

Test 1 — `test_remove_purges_embeddings_chunks_and_fts` (the WR-01 RED test): seed TWO collections into one tmp_path db via the helper ("notes" with probe token purgeprobealpha, "keeper" with purgeprobekeeper). Under the SAME dim-8 settings patch, invoke `CliRunner().invoke(cli, ["--index", str(db_path), "collection", "remove", "notes"], input="y\n", env={"COLUMNS": "200"})` (the class `_invoke` hardcodes the collection group — reuse it). Assert exit_code 0. Then on fresh connections assert ALL of: (a) collections row for "notes" gone, "keeper" present; (b) documents — the notes document id absent, keeper document id present; (c) document_chunks — zero rows for the notes doc id, keeper chunk intact; (d) documents_fts MATCH 'purgeprobealpha' returns 0 rows and MATCH 'purgeprobekeeper' returns 1 (FTS5 needs no sqlite-vec); (e) chunks_fts MATCH 'purgeprobealpha' returns 0; (f) via the vec0 read helper: notes doc id NOT in the stored-embedding id set, keeper doc id IS, and the set has exactly one member. At current HEAD assertion (f) FAILS — the orphaned vec0 row survives removal; that is the WR-01 defect. The failure must be this assertion, never an import or collection error.

Test 2 — `test_remove_without_sqlite_vec_still_deletes` (fail-soft contract pin; green at HEAD and must stay green): seed one collection with a document and chunk but NO embeddings (plain repositories under the dim-8 patch). With `patch("sif.search.vector.VectorSearcher", side_effect=RuntimeError("sqlite-vec extension is not available."))` active around the remove invoke (patch target exists at HEAD; after the fix the shared helper constructs VectorSearcher through this same module global and catches the RuntimeError), assert exit_code 0 and that the collection row, document row, and chunk rows are all gone on a fresh connection. This pins D4: BM25-only installs keep working.

Run the file, confirm exactly Test 1 fails on the vec0 assertion while every pre-existing test and Test 2 pass, then commit ONLY this test file: `test(quick-261111-rqs): add failing collection-remove vec0 purge regression (WR-01)`.
  </action>
  <verify>
    <automated>pytest tests/unit/cli/test_collection.py --no-cov -q</automated>
    Expected at RED: exactly 1 failure — test_remove_purges_embeddings_chunks_and_fts on the stored-embedding assertion (orphan row present); all other tests pass. If the failure is an import error, a dim-mismatch ClickException, or the degrade test fails, fix the test setup before committing.
  </verify>
  <done>Two new tests exist; the orphan test is red on the vec0 assertion at HEAD; the degrade test and all pre-existing tests are green; RED commit contains only tests/unit/cli/test_collection.py.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: GREEN — share create_embedding_purger and purge on collection remove (WR-01 fix)</name>
  <files>src/sif/search/vector.py, src/sif/indexing/incremental.py, src/sif/cli/commands/collection.py</files>
  <behavior>
  - Task 1's test_remove_purges_embeddings_chunks_and_fts flips to green: removed collection's vec0 rows gone, keeper's documents/chunks/FTS/embeddings intact.
  - Task 1's test_remove_without_sqlite_vec_still_deletes stays green (None purger path).
  - Existing guards pass UNMODIFIED: test_incremental.py purge-ordering (line 271) and update_paths purge (line 432) tests; test_repositories.py delete_by_collection relational test (line 360); the full Task-1-file battery.
  - Single-definition gate: exactly one `def create_embedding_purger` in src/ (vector.py); the private incremental helper name no longer occurs anywhere in src/ (planning-time baseline: two occurrences, incremental.py lines 58 and 92).
  </behavior>
  <action>
Three edits, minimal and behavior-preserving (D1-D4 in the objective):

1. src/sif/search/vector.py — add a public module-level function `create_embedding_purger(conn: sqlite3.Connection) -> VectorSearcher | None` AFTER the VectorSearcher class. Move the body VERBATIM from incremental.py's private helper: try returning `VectorSearcher(conn)`, except RuntimeError return None. Carry over its docstring contract (missing sqlite-vec means no vec0 table, hence nothing to purge; callers treat None as "nothing to purge") and note it is the single shared construction point for embedding purgers (WR-01). Fully annotated; no new imports needed (sqlite3 and VectorSearcher are already in this module). Do not touch any existing VectorSearcher method.

2. src/sif/indexing/incremental.py — delete the private helper function (lines 58-69) entirely. In `IncrementalIndexer.__init__`, replace the `self._vector_purger = _embedding_purger(conn)` line with a function-local `from sif.search.vector import create_embedding_purger  # noqa: PLC0415` followed by `self._vector_purger: VectorSearcher | None = create_embedding_purger(conn)`. The function-local import preserves today's import-time behavior (the search module is not imported when incremental is imported — same lazy pattern the deleted helper used). KEEP the existing TYPE_CHECKING VectorSearcher import for the annotation. Nothing else in this file changes — `_remove_document` and both purge call sites stay byte-identical.

3. src/sif/cli/commands/collection.py — in `collection_remove`, inside the existing `with db.transaction() as conn:` block, AFTER the not-found guard and BEFORE `doc_repo.delete_by_collection(collection.id)`: function-local `from sif.search.vector import create_embedding_purger  # noqa: PLC0415`; `purger = create_embedding_purger(conn)`; if purger is not None, collect ids with the finding's parameterized projection `SELECT id FROM documents WHERE collection_id = ?` bound to `(collection.id,)` and call `purger.delete_embeddings_by_document(doc_id)` for each. Update the stale "Delete documents first (cascade will handle chunks)" comment to state that vec0 embeddings are purged first because the virtual table cannot carry the FK cascade (WR-01). Keep the existing function-local DocumentRepository import, the transaction shape, the collection delete, and the success message byte-identical. Do NOT edit repositories.py (D2) — its relational contract is already pinned by existing tests.

All SQL stays parameterized; complexity stays well under 10; no noqa beyond the two established PLC0415 function-local-import exemptions; fully annotated per CLAUDE.md. No CLI signature change — generator-owned docs are untouched.

Run the scoped battery and the single-definition gates, then commit exactly the three source files: `feat(quick-261111-rqs): share embedding purger and purge vec0 on collection remove (WR-01)`.
  </action>
  <verify>
    <automated>pytest tests/unit/cli/test_collection.py tests/unit/indexing/test_incremental.py tests/unit/search/test_vector.py tests/unit/database/test_repositories.py --no-cov -q</automated>
    <automated>test "$(grep -c 'def create_embedding_purger' src/sif/search/vector.py)" = "1" && test -z "$(grep -rn '_embedding_purger' src/)"</automated>
    <!-- planner-discipline-allow: _embedding_purger -->
    Gate baselines recorded at planning time: `def create_embedding_purger` count in vector.py is 0 at HEAD (must become 1); `grep -rn '_embedding_purger' src/` returns exactly incremental.py:58 and :92 at HEAD (must become empty). The negative-grep literal must not survive in any src/ comment either. Battery baseline: 69 passed at HEAD; expected 71 passed after Tasks 1-2.
  </verify>
  <done>Both new tests green; all 69 baseline tests still green unmodified; exactly one shared helper definition consumed by both IncrementalIndexer and collection_remove; repositories.py byte-identical; GREEN commit contains only the three source files.</done>
</task>

<task type="auto">
  <name>Task 3: Close WR-01 in the disposition ledger (three edits) and run the full quality suite</name>
  <files>.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md</files>
  <action>
SHARED-LEDGER RULE (orchestrator): siblings 261111-rqp (IN-08) and 261111-rqq (WR-09) close records in this same file and may run before this item. Read the ledger's CURRENT state at execution time; never use a planning-time literal as a replacement value.

Make EXACTLY three edits, all scoped to the WR-01 record, keeping every other line byte-identical (no `**Status:** resolved` lines exist in this ledger — do not introduce any):

1. YAML front matter: inside the `- id: WR-01` block ONLY, change `disposition: open` to `disposition: fixed`. Do not touch the title or severity lines, and do not touch any other record's disposition.
2. Front-matter counter: read the current `open: N` line and replace it with `open: N-1` using the value observed NOW (planning-time value was 16, but siblings may have already decremented it — if it reads 14, write 13). Leave `total: 22` and `recorded:` unchanged.
3. Markdown table: replace the row `| WR-01 | warning | open | - |` with `| WR-01 | warning | fixed | quick 261111-rqs (collection remove purges vec0 embeddings before document delete via the shared create_embedding_purger helper, plus real-SQLite regression tests) |`. No other row changes.

Run the three-edit closure gate BELOW BEFORE committing the ledger (it diffs against execution-time `git show HEAD:<ledger>`, which at that point is the pre-closure state). Then run the full CLAUDE.md quality suite. Then commit ONLY the ledger file: `docs(quick-261111-rqs): close Phase 10 WR-01 in disposition ledger (open N->N-1)` with the actual observed numbers in the message. Never stage the pre-existing uncommitted .planning/ churn (config.json, state.json, agent-history.json, tmp/, PATTERNS, research cache, 16-REVIEW iter2, STATE.md) — explicit file scope only.
  </action>
  <verify>
    <automated>python -c "
import pathlib, subprocess
p = '.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md'
head = subprocess.run(['git', 'show', 'HEAD:' + p], capture_output=True, text=True, check=True).stdout.splitlines()
cur = pathlib.Path(p).read_text(encoding='utf-8').splitlines()
assert len(head) == len(cur), 'line count changed'
diff = [(i, a, b) for i, (a, b) in enumerate(zip(head, cur)) if a != b]
assert len(diff) == 3, diff
kinds = set()
for i, a, b in diff:
    if a.strip() == 'disposition: open' and b.strip() == 'disposition: fixed':
        j = i
        while not cur[j].strip().startswith('- id:'):
            j -= 1
        assert cur[j].strip() == '- id: WR-01', cur[j]
        kinds.add('yaml')
    elif a.startswith('open: ') and b.startswith('open: '):
        assert int(b.split()[1]) == int(a.split()[1]) - 1, (a, b)
        kinds.add('count')
    elif a.startswith('| WR-01 |') and b.startswith('| WR-01 | warning | fixed | quick 261111-rqs'):
        kinds.add('row')
assert kinds == {'yaml', 'count', 'row'}, kinds
print('WR-01 closure OK: exactly 3 edits, open count decremented by 1 from execution-time HEAD')
"</automated>
    <automated>ruff check src tests && ruff format --check src tests && ty check src/sif && pytest</automated>
    The closure gate must run BEFORE the ledger commit (after it, HEAD contains the closure and the diff would be empty). The full suite is the CLAUDE.md end-of-work gate (longer runtime is expected and acceptable); planning-time baseline: 1504+ passed, 1 skipped, coverage fail_under=90 active, ruff/format/ty green.
  </verify>
  <done>Ledger shows WR-01 fixed in YAML and table with Source naming quick 261111-rqs; open count is exactly one less than its execution-time HEAD value; the closure gate proves exactly three lines changed; ruff check, ruff format --check, ty, and the full pytest suite all pass; ledger commit contains only the ledger file.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| CLI argument -> local SQLite | Collection name crosses into parameterized repository queries (existing boundary; no new surface, no network, no new inputs) |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-rqs-01 | Tampering | collection_remove embedding purge scope (src/sif/cli/commands/collection.py) | medium | mitigate | Purge is a per-document parameterized DELETE keyed on ids selected from the removed collection only — never a blanket document_embeddings wipe; the keeper-collection regression test proves sibling documents/chunks/FTS/vec0 rows survive; the purge runs inside the existing db.transaction() so a mid-purge failure rolls back atomically instead of leaving a half-removed collection |
| T-rqs-SC | Tampering | package installs | low | accept | No package-manager install, dependency, or lockfile task exists in this plan; the package legitimacy gate is not applicable |
</threat_model>

<verification>
Phase-level checks (all commands assume cwd at the checkout root, PATH pytest from miniconda base):
1. Scoped battery: `pytest tests/unit/cli/test_collection.py tests/unit/indexing/test_incremental.py tests/unit/search/test_vector.py tests/unit/database/test_repositories.py --no-cov -q` — 71 passed (69 baseline + 2 new), zero modifications to pre-existing tests.
2. Single shared definition: `grep -c 'def create_embedding_purger' src/sif/search/vector.py` == 1 and `grep -rn '_embedding_purger' src/` empty (baselines: 0 and two incremental.py hits at planning time).
3. repositories.py untouched: `git diff 802c08c -- src/sif/database/repositories.py` empty at merge base (sibling rqq owns any later changes there).
4. Ledger three-edit gate (Task 3 automated script) against execution-time `git show HEAD:<ledger>`.
5. Full CLAUDE.md suite: `ruff check src tests && ruff format --check src tests && ty check src/sif && pytest`.
</verification>

<success_criteria>
- `sif collection remove` leaves zero orphaned vec0 embeddings for the removed collection (real-SQLite regression proven red-to-green), while keeper collections and BM25-only installs are unaffected.
- One shared `create_embedding_purger` definition serves both IncrementalIndexer and collection_remove; all pre-existing purge tests pass unmodified; repositories.py byte-identical.
- WR-01 closed in 10-REVIEW-DISPOSITION.md with exactly three edits and Source naming quick 261111-rqs; open count decremented once from its execution-time value; no other record disturbed.
- Full quality suite green; three scoped commits (test RED, feat GREEN, docs ledger) with no pre-existing .planning/ churn staged.
</success_criteria>

<output>
Create `.planning/quick/261111-rqs-close-phase-10-wr-01-share-the-duplicated-purge-helper-colle/261111-rqs-SUMMARY.md` when done.
</output>