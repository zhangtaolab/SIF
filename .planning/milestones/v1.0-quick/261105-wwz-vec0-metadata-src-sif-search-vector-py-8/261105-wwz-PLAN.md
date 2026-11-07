---
phase: 261105-wwz-vec0-metadata-src-sif-search-vector-py-8
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/sif/search/vector.py  # branch A (expected): comment-only audit note; branch B (contradicting evidence only): CROSS JOIN pinning in the same file's _search_with_vec SQL
  - .planning/quick/261105-wwz-vec0-metadata-src-sif-search-vector-py-8/261105-wwz-SUMMARY.md
  # branch B only: tests/unit/search/test_vector.py
autonomous: true
requirements: [QUICK-AUDIT-VEC0-SEARCH-SCAN]  # quick task: audit the search path for the vec0 unindexed-metadata-filter pattern fixed in embed by 261105-wbj; deliverable is measured/reasoned evidence and the documented conclusion — a code change ONLY if evidence demands it
estimate:
  tokens: 12000
  raw_tokens: 12000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - "No behavior change on branch A (expected): every src/sif/search/vector.py hunk in this task's commits is a comment/docstring line; zero executable-statement changes; return semantics byte-identical"
    - "Audit note present at the query site: [ $(grep -c '261105-wwz' src/sif/search/vector.py) = 1 ] (baseline 0 at HEAD 16b7b25, planner-verified this session) — the note names the quick task id so future re-audits find the disposition"
    - "Evidence recorded: .planning/quick/261105-wwz-vec0-metadata-src-sif-search-vector-py-8/261105-wwz-SUMMARY.md contains an EXPLAIN QUERY PLAN section (grep -q 'EXPLAIN QUERY PLAN' succeeds), the flat-timing numbers across the no-filter / 1-id / 3-id collection-filter shapes, and the call-frequency inventory proving VectorSearcher.search runs once per user query (src/sif/search/hybrid.py:64, :184, :191; src/sif/cli/commands/search.py:374) and never inside a per-result or per-document loop"
    - "Disposition documented in the SUMMARY: the search path has NO WHERE filter on vec0 metadata columns (document_id/chunk_id/embedding_id) — the only search-path vec0 access is the KNN MATCH (vector.py:89, embedding MATCH ? AND k = ?); document_id appears solely in the JOIN ON, which the planner resolves as PK lookups (SEARCH d USING INDEX sqlite_autoindex_documents_1 (id=?)); the remaining metadata-filtered statements (vector.py:195 per-document DELETE in the embed path, vector.py:207 single-doc lookup with zero production callers since 261105-wbj, src/sif/cli/main.py:173 cleanup DELETE once per explicit cleanup run) all sit OUTSIDE the search path and are already dispositioned"
    - "Full quality gates green: ruff check src tests; ruff format --check src tests; env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q with 0 failures (690 passed baseline at HEAD 16b7b25 post-261105-wbj; FORCE_COLOR must be UNSET, not 0 — known spurious-failure mode in this repo)"
  artifacts:
    - "src/sif/search/vector.py — branch A: a comment-only audit note of at most 8 lines inserted above the sql assignment in _search_with_vec (after the existing WR-04 over-fetch comment block, ~vector.py:78) covering: KNN MATCH is the only vec0 access in the search path with no metadata WHERE; the JOIN resolves as PK lookups on documents/collections per KNN-emitted row; vec0 v0.1.9 KNN is an inherent once-per-query brute-force pass regardless of collection-filter shape; audited 2026-11-05 with EQP and flat-timing evidence, quick task 261105-wwz. Branch B (ONLY on fresh contradicting evidence): pin de as outer loop by replacing the two JOIN keywords with CROSS JOIN (planner-verified result-identical) plus a real-vec0 result-equivalence regression test in tests/unit/search/test_vector.py asserting the filtered result equals the unfiltered result restricted to that collection, same rows, same order"
    - ".planning/quick/261105-wwz-vec0-metadata-src-sif-search-vector-py-8/261105-wwz-SUMMARY.md — disposition headline (search path clean, no change on branch A), verbatim EXPLAIN QUERY PLAN outputs for the three SQL shapes, timing table, call-frequency inventory with file:line refs, classification table of every document_embeddings statement in src/, branch taken and why"
  key_links:
    - "evidence <-> conclusion: the no-change disposition rests on three independent measurement classes — plan shape (EXPLAIN QUERY PLAN: single vec0 SCAN, PK joins, no metadata constraint in the vec0 index string), cost (flat timing across filter sizes, no KNN re-execution multiplier), and frequency (once per user query, never looped) — the SUMMARY must show all three so a future re-audit can re-verify cheaply"
    - "audit note <-> future audits: the in-code comment at the query site closes the same suspicion class as the get_all_embedded_chunk_ids docstring (vector.py:212-231) — the next unindexed-metadata concern finds the disposition in place instead of spawning a duplicate investigation"
    - "probe safety <-> user data: every probe against a real DB file opens it read-only via a file: URI with mode=ro; the timing bench lives in an in-memory synthetic database; the reporter's ~495,802-row index is never opened for write"
---

<objective>
Audit the search path for the vec0 unindexed-metadata-filter pattern that quick 261105-wbj fixed in the embed path, and record the measured conclusion. This task legitimately ends in "no change needed" — the evidence below, gathered live at planning time, already points there; the executor re-establishes it fresh at HEAD, records it, and adds a durable in-code audit note. A code change happens ONLY if the fresh evidence contradicts the planning-time findings.

**Planner-verified facts this session (sqlite 3.51.0 + sqlite-vec v0.1.9; executor re-establishes each at HEAD):**

1. The ONLY vec0 access in the search path is the KNN query in `_search_with_vec` (src/sif/search/vector.py:79-91): `FROM document_embeddings de JOIN documents d ON de.document_id = d.id JOIN collections c ON d.collection_id = c.id WHERE embedding MATCH ? AND k = ? {AND d.collection_id IN (...)}`. No WHERE clause filters a vec0 metadata column — `document_id` appears solely in the JOIN ON; the collection filter targets the plain `documents` table.
2. EXPLAIN QUERY PLAN on the real schema (both machine DBs, read-only) — no-filter and 3-id shapes: `SCAN de VIRTUAL TABLE INDEX 0:3{___}___` once, OUTERMOST; then `SEARCH d USING INDEX sqlite_autoindex_documents_1 (id=?)` and `SEARCH c USING INDEX sqlite_autoindex_collections_1 (id=?)` — PK lookups per KNN-emitted row (at most fetch_k = max(limit*4, 50) of them). The `{___}___` constraint map shows nothing but MATCH/k pushed into the virtual table — the catastrophic metadata-filter plan shape does not occur. The 1-id shape (`IN (?)`) prints collections outermost with the vec0 SCAN second; that outer loop has EXACTLY one iteration because vector.py:66 generates one placeholder per collection id, so the KNN still runs once.
3. EQP loop-ordering semantics: rows print OUTERMOST-FIRST on this sqlite build — verified empirically (idx_chunks_document can only serve an inner loop, and it printed second under its driving table).
4. Measured timing (synthetic in-memory vec0, FLOAT[8], 6,000 rows across 3 collections, best of 3): 0.23-0.27 ms for no-filter, 1-id, 2-id, and 3-id filters — FLAT. No KNN re-execution multiplier for any placeholder count the code can generate.
5. Call frequency: `VectorSearcher.search` runs once per user query — hybrid.py:64 (HybridSearcher.search), hybrid.py:184/:191 (SearchPipeline VECTOR/HYDE routes), search.py:374 (CLI direct vector search). The default hybrid route runs `HybridSearcher.search` once per expanded query variant (hybrid.py:217-218) — a small bounded constant. Never inside a per-result or per-document loop. This is NOT the 261105-wbj pattern (a metadata-filtered scan multiplied by ~40k loop iterations).
6. The one inherent O(N) cost — the vec0 KNN brute-force distance pass over all stored vectors (~495,802 x 1024 dims on the reporter's index) — is sqlite-vec v0.1.9's algorithm for `embedding MATCH` (no ANN index in this version). It is identical under any semantics-preserving SQL reshaping; eliminating it would require an ANN index type (out of scope). It is a per-query constant, not a per-call multiplier.
7. Full inventory of `document_embeddings` statements in src/ (grep, planner-run): vector.py KNN (search path, item 1); vector.py:161/:181 INSERTs (embed write path); vector.py:195 DELETE per re-embedded document and vector.py:207 single-doc lookup (embed path — 207 has zero production callers since 261105-wbj); vector.py:225 batch read (the 261105-wbj fix); src/sif/database/schema.py:307 DDL; src/sif/cli/commands/index.py:295 sqlite_master read; src/sif/cli/main.py:173 orphan-cleanup DELETE (once per explicit cleanup run). All non-search statements are maintenance-path and already dispositioned.
8. Branch-B fix pre-verified: replacing the two JOIN keywords with CROSS JOIN pins `de` outermost (SQLite never reorders CROSS JOIN); on synthetic data it produced IDENTICAL rows in identical order and the same `SCAN de` outer plan. It is NOT applied unless fresh evidence demands it.
9. Both real DBs on this machine (`/Users/forrest/.local/share/sif/sif.db`, `/Users/forrest/Library/Application Support/sif/sif.db`) hold 0 embedding rows — the synthetic in-memory table is the timing vehicle; EQP shape is data-independent.

Purpose: close out the user's suspicion that search/hybrid queries hit the same O(N) unindexed-metadata scan as the embed integrity check — with recorded evidence, not assumption — and leave an in-code note preventing re-investigation.
Output: evidence-rich SUMMARY; comment-only audit note in vector.py (branch A); full quality suite green. No behavioral change.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@src/sif/search/vector.py
@src/sif/search/hybrid.py
@.planning/quick/261105-wbj-embed-o-n-bug-src-sif-search-vector-py-2/261105-wbj-SUMMARY.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Re-establish audit evidence at HEAD; record the conclusion at the query site (expected: comment-only)</name>
  <files>src/sif/search/vector.py</files>
  <action>Run the audit fresh and capture verbatim outputs for the SUMMARY. (a) Inventory: grep every statement touching document_embeddings across src/ and classify each as search-path vs maintenance-path — expected exactly the eight sites listed in objective item 7. (b) Frequency: confirm by reading the call sites that VectorSearcher.search runs once per user query (hybrid.py:64, :184, :191; search.py:374) and that the SearchPipeline default route calls HybridSearcher.search once per expanded query variant (hybrid.py:217-218), never per-result. (c) Plan shape: on a synthetic in-memory vec0 table (sqlite_vec.load; collections/documents/document_embeddings mirroring schema.py:307 with FLOAT[8]; a few thousand rows across 3 collections), capture EXPLAIN QUERY PLAN for the exact _search_with_vec SQL in three shapes — no filter; AND d.collection_id IN (?) with one bound id; IN (?,?,?) with three bound ids — plus a KNN timing per shape (best of 3). If a NON-empty real index is reachable at execution time (SIF_DB_PATH or the two default paths), additionally capture its EQP by opening it read-only via a file: URI with mode=ro — never write a real DB. Expected results per objective items 2 and 4; deviations must be recorded either way. (d) Branch decision. Branch A (expected — fresh EQP shows the single outer vec0 SCAN with PK joins and no metadata constraint mapped into the vec0 index string, and timing is flat): insert a comment-only audit note of at most 8 lines above the sql assignment in _search_with_vec (after the existing WR-04 over-fetch comment block, ~vector.py:78) stating: the KNN MATCH is the only vec0 access in the search path and no WHERE filters vec0 metadata columns; the JOIN resolves as PK lookups on documents and collections per KNN-emitted row; vec0 v0.1.9 KNN is an inherent brute-force pass over all stored vectors executed exactly once per query regardless of collection-filter shape; audited 2026-11-05 via EXPLAIN QUERY PLAN and flat-timing measurement — quick task 261105-wwz (the grep gate requires that task id in the comment; do NOT also put the id anywhere else in the file). No executable statement may change. Branch B (only if the fresh EQP nests the vec0 SCAN under an outer loop NOT bounded by the placeholder count, or maps a document_id/chunk_id/embedding_id constraint into the vec0 virtual-table index): pin de outermost by replacing the two JOIN keywords with CROSS JOIN (semantics preserved — planner-verified identical rows and order; KNN-then-filter-then-trim contract of the WR-04 over-fetch unchanged), and add a real-vec0 regression test in tests/unit/search/test_vector.py modeled on the existing real-vec0 tests (sqlite_vec.load with pytest.skip fallback, FLOAT[2]) asserting the collection-filtered result equals the unfiltered result restricted to that collection — same rows, same order, same scores — for the same query embedding.
  <verify>
    <automated>ruff check src/sif/search/vector.py && ruff format --check src/sif/search/vector.py && [ "$(grep -c '261105-wwz' src/sif/search/vector.py)" = "1" ]</automated>
  </verify>
  <done>Verbatim EQP (three shapes), timing, inventory, and frequency outputs captured for the SUMMARY; branch decision made on the fresh evidence; branch A: vector.py diff is comment-only and the note containing the quick task id is in place (grep count 1, baseline 0); branch B: CROSS JOIN pinning in place with its real-vec0 equivalence test passing; ruff check and format clean on the file either way.</done>
</task>

<task type="auto">
  <name>Task 2: Record the evidence-backed conclusion in the SUMMARY; run full quality gates</name>
  <files>.planning/quick/261105-wwz-vec0-metadata-src-sif-search-vector-py-8/261105-wwz-SUMMARY.md</files>
  <action>Write the SUMMARY per the template with: the disposition headline (on branch A: search path clean — no vec0 metadata-filter scan, no code change, comment-only audit note; on branch B: the contradicting evidence and the applied fix); the verbatim EXPLAIN QUERY PLAN outputs for the three SQL shapes; the timing table showing flat cost across filter sizes; the call-frequency inventory with file:line references; the classification table of every document_embeddings statement in src/ (search-path KNN vs maintenance-path embed/cleanup, the latter already dispositioned by 261105-wbj); the branch taken and why; any deviations between planning-time and execution-time observations; probe-safety note (real DBs opened read-only via mode=ro URIs, bench in-memory). Then run the full CLAUDE.md quality suite exactly as specified below — FORCE_COLOR must be UNSET (env -u), not set to 0, with NO_COLOR=1.
  <verify>
    <automated>ruff check src tests && ruff format --check src tests && env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q && grep -q 'EXPLAIN QUERY PLAN' .planning/quick/261105-wwz-vec0-metadata-src-sif-search-vector-py-8/261105-wwz-SUMMARY.md</automated>
  </verify>
  <done>SUMMARY exists with all evidence sections (EQP verbatim, timing table, frequency inventory, statement classification, branch rationale); ruff check clean; ruff format --check clean; full pytest 0 failures (690 passed baseline at HEAD 16b7b25).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| local SQLite index files -> audit probes (read path) | probes open any real sif.db read-only via a file: URI with mode=ro; the timing bench is an in-memory synthetic database; no new write path, no external input, no network |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-wwz-01 | Tampering | audit probes vs the reporter's real index DB | low | mitigate | every real-DB probe opens via a file:...?mode=ro URI so no probe statement can mutate user data; the synthetic bench lives in :memory: only |
| T-wwz-02 | Denial of Service | _search_with_vec KNN brute-force pass (existing behavior, unchanged by this task) | low | accept | the once-per-query full-vector pass is sqlite-vec v0.1.9's inherent KNN algorithm and the current production baseline; this audit deliberately does not alter it (evidence recorded); an ANN index change would be a separately scoped task |
| T-wwz-SC | Tampering | package-manager installs | high | accept | no package installs — sqlite3 is stdlib and sqlite-vec is an existing declared dependency; legitimacy gate not applicable |
</threat_model>

<verification>
Targeted per-task gates above, then the full CLAUDE.md quality suite before marking done:

  ruff check src tests
  ruff format --check src tests
  env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q

(FORCE_COLOR must be unset, not set to 0, and NO_COLOR=1 set when running pytest in agent shells — known spurious-failure mode in this repo.)

On branch A nothing about runtime behavior changes, so no user-facing spot-check is required. Optional user-run confirmation on the real ~495k-row index: time a `sif search` before and after pulling this change — wall times must be indistinguishable.
</verification>

<success_criteria>
- The conclusion is evidence-backed, not assumed: the SUMMARY shows all three measurement classes (EQP plan shape for no-filter/1-id/3-id, flat timing, call-frequency inventory) — reproducible by any future re-audit.
- No behavioral change on branch A: full suite 690 passed / 0 failed, vector.py hunks comment-only, return semantics byte-identical.
- The disposition is durable: the audit note at the query site names quick task 261105-wwz (grep gate = 1), and the SUMMARY classifies every document_embeddings statement in src/ so the embed-path and cleanup-path metadata filters are explicitly bounded out of the search-path conclusion.
- If branch B fired instead: the CROSS JOIN form is covered by a real-vec0 result-equivalence test proving identical rows, order, and scores.
</success_criteria>

<output>
Create `.planning/quick/261105-wwz-vec0-metadata-src-sif-search-vector-py-8/261105-wwz-SUMMARY.md` when done
</output>
