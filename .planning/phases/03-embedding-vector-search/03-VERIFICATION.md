---
phase: 03-embedding-vector-search
verified: 2026-09-04T11:58:41Z
status: passed
score: 17/17 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 11/12
  gaps_closed:
    - "UAT gap G-03-3 (03-UAT.md test 3): repeated `sif index embed` runs polluted the vector store with orphaned embeddings and --force was ignored — closed by plan 03-08, behaviorally verified this round (4 real-sqlite-vec integration tests independently re-run, all pass)"
    - "Previous behavior-unverified truth 12 (ModelScope interrupted/parallel download resume) — resolved by UAT test 3 direct observation (SIGKILL at 44-49%, byte-level resume from 506M local cache, no restart, no corruption, bit-identical scores)"
    - "All five previous human items were exercised by the 2026-09-04 UAT round: 4 passed; test 3's pass surfaced G-03-3, now closed"
  gaps_remaining: []
  regressions: []
coincidental_reliance_items:

  - truth: "Document indexing benefits from batch embedding insertion for better performance (SC3 / VEC-03)"
    reason: undeclared-precondition
    harden: >-
      Carried forward unchanged: VectorSearcher.add_embeddings_batch advertises `chunk_id: str | None`
      but the installed sqlite-vec rejects NULL for the TEXT metadata column. It works only because
      embed_cmd always passes chunk.id. Either declare the non-None precondition (type + docstring +
      guard) or serialize None to a sentinel before executemany.
human_verification:

  - test: "REVIEW CRITICAL CR-01 (validated by this verifier): edit a note, run `sif index update`,
      then `sif index embed` (no --force) — decide remediation: fix now or defer with tracking"
    expected: "Decision required, not a test pass/fail: update_cmd's changed-document branch updates the
      documents row but never invalidates document_chunks/document_embeddings, and 03-08's new
      completeness check (chunk-id set == embedded set) then skips the document on every default run —
      edited notes silently serve stale chunk text and stale vectors until a global --force. Confirmed
      by code reading (index.py:127-140 vs 280-284) and empirically (small edit: embed run 2 performs
      0 embed calls, stale chunks remain). NOTE for the fix: medium+ content edits crash earlier —
      see the FTS discovery below (pre-existing, FND-06)."
    why_human: "Neither CR-01 nor its fix is a Phase 03 must-have (03-08's scope was explicitly
      G-03-3-only, and its prohibition P3 forbade lifecycle extension), but it is flagged CRITICAL by
      the phase's own 03-REVIEW.md (status: issues_found, no fix round yet) and it degrades the
      product's core edit->update->embed->search loop. Accept-as-deferred vs fix-now is a developer
      decision (Escalation Gate)."
  - test: "REVIEW CRITICAL CR-02 (validated by this verifier): make one collection's embed fail while
      another succeeds — decide the transaction model"
    expected: "Decision required: embed_cmd raises the failed-collections ClickException inside
      `with db.connection:` (index.py:236, 324-328), so sqlite3 rolls back EVERY successful
      collection's work after `Embedding complete: N chunks embedded` was already printed — output
      claims work that was discarded, and remote backends re-bill the successful spend on every
      retry. The 03-08 plan's assumed model ('a caught per-collection failure leaves
      deleted-but-not-reinserted documents for the completeness check to re-embed next run') does not
      hold; self-healing still converges only because the rollback resets to the pre-run state."
    why_human: "Not a must-have failure (self-heal truth holds observationally and is tested), but a
      real correctness/cost defect flagged CRITICAL by the phase's own review. Choose per-collection
      transactions with the raise moved outside the transaction, or all-or-nothing semantics without
      the success print — a design decision, then a small fix."
  - test: "OPTIONAL (03-08 coverage D6): on any real collection, run `sif index embed -c <name>`
      twice then `sif search vsearch <query>` — each document appears once per live chunk"
    expected: "No duplicated rows per historical run. Optional per the 03-08 plan (the automated
      integration tests already prove the mechanics against a real sqlite-vec store, and the UAT
      round already performed this exact reproduction shape when discovering G-03-3)"
    why_human: "Plan marks it optional human confirmation; included for completeness, not blocking."
---

# Phase 03: Embedding & Vector Search Verification Report

**Phase Goal:** Users can perform semantic vector search with configurable embedding backends.
**Verified:** 2026-09-04T11:58:41Z
**Status:** human_needed
**Re-verification:** Yes — after UAT gap G-03-3 closure (plan 03-08)

**Verification basis:** the CURRENT codebase. Re-verification scope: full 3-level + behavioral
verification of the five new 03-08 truths (G-03-3 closure) and the three 03-08 prohibitions; quick
regression on the twelve previously-verified truths; independent re-run of the G-03-3 integration
tests, the touched unit test files, ruff, and the full suite. The five previous human-verification
items were exercised by the 2026-09-04 UAT round (03-UAT.md: 4 passed; test 3's pass surfaced
G-03-3, now closed).

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can configure different embedding backends (sentence-transformers, llama-cpp-python, OpenAI-compatible API) via Settings and CLI (SC1 / VEC-01) | ✓ VERIFIED | Regression: `OpenAIEmbedder` at embedder.py:267, `_create_openai_model` factory.py:70, `_create_modelscope_model` factory.py:93, Settings model_type/api_key/api_base + validator (settings.py:61-80, 152), `--model-type` CLI Choice on embed (index.py:192). UAT test 1 (2026-09-04) live-verified the openai backend against a real LM Studio endpoint (semantic results rank1 0.4303/0.4514, dim cache probe-then-hit). Full suite green. |
| 2 | Vector search uses `sqlite-vec` and refuses brute-force Python fallback on large indexes (SC2 / VEC-02) | ✓ VERIFIED | Regression: `VectorSearcher.__init__` raises RuntimeError when vec extension missing (vector.py:19-23); no Python cosine fallback anywhere in the search path; `test_init_raises_when_vec_unavailable` in the green suite. vector.py untouched by 03-08 except two additive methods (git diff: 24 insertions, 0 deletions). |
| 3 | Document indexing benefits from batch embedding insertion for better performance (SC3 / VEC-03) | ✓ VERIFIED | Regression: `add_embeddings_batch` executemany (vector.py:160-178) wired in embed_cmd (index.py:310); `test_add_embeddings_batch_executes_many` and `test_embed_cmd_batches_across_documents` pass; batch tuple shape byte-identical (additive-only diff). Advisory coincidental-reliance (NULL chunk_id) carried forward. |
| 4 | User can download embedding models from ModelScope as an alternative to HuggingFace (SC4 / VEC-04) | ✓ VERIFIED | Regression + UAT live evidence: UAT test 2 ran real `snapshot_download` against modelscope.cn (Qwen3-Embedding-0.6B, dim=1024, 3 chunks embedded, vsearch rank1 0.4538); factory modelscope branch and `snapshot_download` wiring untouched by 03-08; 6 modelscope unit tests in the green suite. |
| 5 | Settings accepts model_type/api_base/api_key with validation and env override (plans 03-01/03-05) | ✓ VERIFIED | Regression: fields + validator present (settings.py:61-80, 152-168); env-var dispatch tests in green suite; settings.py untouched by 03-08. |
| 6 | SchemaManager creates dimension-aware vec0 table and fails fast on dimension mismatch (plan 03-03) | ✓ VERIFIED | Regression: schema.py untouched by 03-08 (git log: last schema.py change predates the milestone); dimension mismatch fail-fast previously proven by direct execution (RuntimeError naming both dims). |
| 7 | vsearch/query/embed commands use EmbeddingManager with --model-type (plan 03-06) | ✓ VERIFIED | Regression: `--model-type` Choice on embed (index.py:190-194); `test_embed_cmd_respects_model_type_override` and `test_embed_cmd_openai_model_type_reaches_endpoint` pass. |
| 8 | First openai load resolves dimension from API, caches to openai_dim_cache.json (7-day TTL, per-model) (03-07) | ✓ VERIFIED | Regression: embedder.py:322-387 unchanged; all 8 dimension-cache tests in the green suite. UAT test 1 observed the cache behavior live (deleted -> re-probe -> cache hit). |
| 9 | Caller-supplied dim disagreeing with API-detected dim fails fast naming both values (03-07) | ✓ VERIFIED | Regression: `test_dimension_mismatch_fails_fast` in green suite; error text at embedder.py:311-317. |
| 10 | Absent openai package -> ImportError with `pip install sif[openai]` hint; extra in pyproject (03-07) | ✓ VERIFIED | Regression: `test_import_error_logs_install_hint` in green suite; pyproject unchanged by 03-08. |
| 11 | openai backend parallel/interruption-safe, no partial embeddings persisted (03-07) | ✓ VERIFIED | Regression: `test_embed_batch_no_partial_result_on_midbatch_failure` in green suite. |
| 12 | Interrupted/parallel ModelScope download resumes from local snapshot cache without corruption (03-07 backstop, VEC-04 edge) | ✓ VERIFIED | **Upgraded from PRESENT_BEHAVIOR_UNVERIFIED** on UAT direct observation (03-UAT.md test 3, 2026-09-04): download SIGKILLed at 44-49% (505M/1.11G temp file); rerun resumed from existing bytes (0% -> 45% jump at memory-speed, then network to 100% in 8s — no restart-from-zero); completed small files skipped; vsearch scores bit-identical to pre-interruption (0.4538) — no corruption. |
| 13 | **[G-03-3]** Running `sif index embed` twice without --force leaves document_embeddings with exactly one row per live chunk — replace, not append (03-08 truth 1) | ✓ VERIFIED | Behavioral: `test_two_embed_runs_leave_one_row_per_live_chunk` PASSED against a real sqlite-vec database (independently re-run by this verifier: 4 passed). Run 1: emb_count == chunk_count, chunk-id sets equal; run 2 (default): store byte-identical — the completed document is skipped, strictly stronger than replace. The replace path itself is proven by the --force and self-heal runs, which assert fresh disjoint chunk-id sets (the UAT 21-rows-vs-3 symptom inverted). Implementation: delete-before-insert chain at index.py:285-289. |
| 14 | **[G-03-3]** After a repeated embed run, vector search returns each chunk exactly once (03-08 truth 2) | ✓ VERIFIED | Behavioral: `test_vector_search_returns_each_chunk_once_after_two_runs` PASSED — after two embed runs, a vec0 KNN query with limit=chunk_count returns exactly chunk_count rows, all for the seeded document. The UAT 混合搜索-times-7 / identical-0.4538 symptom cannot reproduce. |
| 15 | **[G-03-3]** Default run embeds only documents whose live chunks lack an exact complete embedding set; fully embedded documents are skipped with no embedding call (03-08 truth 3) | ✓ VERIFIED | Behavioral: integration `test_default_run_skips_complete_then_force_reembeds_all` run 2 asserts `manager.embed.call_count` stays 1 (ZERO new embed calls) and full store-state tuple unchanged; unit `test_embed_cmd_default_skips_fully_embedded_document` asserts no deletes fire and the skip line names the document. Decision logic: `_needs_embedding` (index.py:175-182) = `force or not live or live != embedded`. |
| 16 | **[G-03-3]** `--force` re-chunks and re-embeds every document in scope, deleting and replacing all previous embeddings (03-08 truth 4) | ✓ VERIFIED | Behavioral: same integration test run 3 — `--force` fires exactly one more embed batch, leaves emb_count == chunk_count with exactly matching sets, and asserts the new chunk-id set is fully disjoint from the pre-force set (true replace). Unit `test_embed_cmd_force_reembeds_fully_embedded_document` confirms both deletes fire on a fully embedded document. The `# noqa: ARG001` suppression on force is gone (grep: 0 hits) — the parameter drives a real branch. |
| 17 | **[G-03-3]** A failed/interrupted run self-heals on the next default run — missing, partial, or stale sets are detected and re-embedded to an exact match (03-08 truth 5) | ✓ VERIFIED | Behavioral: `test_default_run_self_heals_partial_state` PASSED — one embedding row deleted to simulate an interrupted run; next default run detects the incomplete set (embed call count 2), re-embeds, and restores emb==chunks with matching sets and disjoint fresh ids. Unit `test_embed_cmd_default_heals_stale_embedding_state` covers the stale/orphan shape. (Caveat: with the current single-transaction scope, an in-process embed failure rolls back wholesale — see CR-02 — so partial states arise from external factors; the detection logic is proven for any partial state however caused.) |

**Score:** 17/17 truths verified (0 present, behavior-unverified)

### G-03-3 Gap Closure Statement

The single UAT gap (G-03-3, severity major) is **closed and behaviorally verified**. Root cause
(insert-only `add_embeddings_batch` over fresh uuid4 chunk ids after `delete_by_document`, plus an
ignored `--force`) is removed: `VectorSearcher.delete_embeddings_by_document` (vector.py:180-190)
and `get_embedded_chunk_ids` (vector.py:192-202) exist with full annotations; embed_cmd wires the
delete-before-insert chain inside the existing transaction (index.py:285-289), the skip-or-embed
decision (index.py:280-284), and the --force bypass. All four integration tests against a real
sqlite-vec database pass, independently re-run by this verifier (`uv run pytest
tests/integration/test_embed_idempotency.py -q` -> 4 passed), as do the 3 new unit tests per file
(24 passed across test_vector.py + test_index.py). Task commits verified in git with test-before-feat
ordering (bbdfc0e -> ef2b0f9, 12f077d -> 7ee95cd).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/sif/search/vector.py` | delete_embeddings_by_document + get_embedded_chunk_ids; insert/search untouched | ✓ VERIFIED | Both methods present, fully parameterized single-`?` SQL, rowcount / non-None set returns; git diff since the 03-08 plan commit is 24 insertions, 0 deletions — `add_embedding`, `add_embeddings_batch`, `search` byte-identical (prohibition P2 upheld). |
| `src/sif/cli/commands/index.py` | embed_cmd: delete-before-insert wired, force drives a real branch, per-collection VectorSearcher, probe-free dim | ✓ VERIFIED | index.py:233-234 (get_model_info dim with isinstance-guarded probe fallback), 268-271 (RuntimeError -> ClickException, prohibition P1), 280-284 (skip decision), 285-289 (delete-before-insert), 175-182 (`_needs_embedding` helper); no ARG001 remains. |
| `tests/integration/test_embed_idempotency.py` | Real-sqlite-vec reproduction of UAT evidence inverted | ✓ VERIFIED | 262 lines, 4 tests (two-run idempotency, once-per-chunk search, skip-then-force, self-heal); real Database + patched settings (FLOAT[8] vec0), sqlite_vec loaded on every touching connection; hermetic against SIF_* env (delenv guard). Independently re-run: 4 passed. |
| `tests/unit/search/test_vector.py` | TestVectorEmbeddingDeletion: SQL-shape + real-vec0 delete | ✓ VERIFIED | 3 new tests at lines 205/226/247: parameterized DELETE (no id interpolation), non-None set semantics, real vec0 delete removing exactly the target document's rows. The `pytest.skip` at line 259 is an environment guard (skip only if sqlite-vec cannot load) — it did NOT trigger here; all 3 ran and passed. |
| `tests/unit/cli/test_index.py` | skip/heal/force embed-semantics tests | ✓ VERIFIED | 3 new tests (474/496/517) with shared harness; existing tests untouched and still passing. |
| Regression artifacts (embedder.py, factory.py, settings.py, schema.py, manager.py, pyproject.toml) | Untouched by 03-08 | ✓ VERIFIED | `git diff --stat` since the 03-08 plan commit: exactly the 5 declared files (2 src + 3 test); nothing else changed. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| embed_cmd re-chunk branch | chunk deletion -> embedding deletion -> fresh insert | `chunk_repo.delete_by_document` -> `vector_searcher.delete_embeddings_by_document` -> `add_embeddings_batch` (index.py:285-310) | ✓ WIRED | The previously-broken chain (G-03-3 root cause). Behaviorally proven by integration tests 1/3/4. |
| chunk_repo.get_by_document + VectorSearcher.get_embedded_chunk_ids | needs-embedding decision -> --force bypass -> skip or embed | `_needs_embedding` (index.py:175-182, 280-284) | ✓ WIRED | Unit + integration tests prove all three outcomes (skip/heal/force). |
| manager.get_model_info()["embedding_dim"] | VectorSearcher per-collection construction | index.py:233-234, 269 | ✓ WIRED | Probe-free (isinstance(int)-guarded with legacy probe fallback) — remote backends make no throwaway embedding call. |
| VectorSearcher construction failure | explicit user-facing error | RuntimeError -> ClickException (index.py:268-271) | ✓ WIRED | Prohibition P1: never swallowed into failed_collections. |
| main.py cleanup_cmd / DocumentRepository.delete | vector deletion extension | — | ✓ NOT EXTENDED (per prohibition P3) | main.py and repositories.py untouched — orphaned embeddings on document deletion remain `sif cleanup`'s job by explicit plan scope. See warning WR-01: the file-removal path still manufactures orphans that occupy KNN top-k slots until cleanup runs. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| embed_cmd | embedded chunk-id set | `SELECT chunk_id FROM document_embeddings WHERE document_id = ?` on the real vec0 table | Yes — drives the skip/heal/force decision; observed discriminating in 3 tests | ✓ FLOWING |
| embed_cmd | deleted embedding rows | `DELETE FROM document_embeddings WHERE document_id = ?` | Yes — rowcount returned; replace-not-append proven via disjoint-set assertions | ✓ FLOWING |
| Integration tests | embedding vectors | mocked manager side_effect with per-call offsets | Yes — distinguishes runs; queries the store with the exact inserted vectors (not echoes: expectations are count/set invariants vs live table state) | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| G-03-3 idempotency suite (real sqlite-vec) | `uv run pytest tests/integration/test_embed_idempotency.py -q` | 4 passed | ✓ PASS |
| New unit tests (vector delete + CLI embed semantics) | `uv run pytest tests/unit/search/test_vector.py tests/unit/cli/test_index.py -q` | 24 passed, 0 skipped | ✓ PASS |
| Full quality suite (canonical env, as in prior verifications) | `python -m pytest -q` | **554 passed, 11 skipped, 0 failed** | ✓ PASS |
| Lint / format | `ruff check src tests` + `ruff format --check` | All checks passed; 125 files formatted | ✓ PASS |
| Task commits exist, test-before-feat | `git log bbdfc0e ef2b0f9 12f077d 7ee95cd` | 4/4 verified | ✓ PASS |
| vector.py additive-only (prohibition P2) | `git diff <03-08-plan>..HEAD -- src/sif/search/vector.py` | 24 insertions, 0 deletions | ✓ PASS |
| force suppression removed | `grep ARG001 src/sif/cli/commands/index.py` | 0 hits | ✓ PASS |
| CR-01 edit-staleness (review critical, independently validated) | direct python harness: seed -> embed -> update content (update_cmd's exact DB effect) -> embed again | run 2 performs 0 embed calls; stale chunks remain — CR-01 REPRODUCED for small edits (see Human Verification) | ⚠ CONFIRMED DEFECT (outside must-have scope) |
| FTS trigger corruption (verifier discovery, pre-existing) | direct python: `UPDATE documents SET content=<~1.4KB>` after init_schema | `sqlite3.DatabaseError: database disk image is malformed` via `documents_fts_update` trigger (direct UPDATE on external-content FTS5) — reproduces with NO embed run; trigger predates the milestone (FND-06, Phase 1 Pending) | ⚠ CONFIRMED DEFECT (pre-existing, Phase 1) |

Environment note: `uv run pytest` fails in the uv-managed venv (missing `httpx` and `pytest_asyncio`
— 21 MCP/async collection or async-support failures plus 2 openai-env failures). All failures are
missing-module shaped, none touch Phase 03's modified files, and the canonical environment (system
python, used by the executor, UAT, and both prior verifications) is fully green. Informational only.

### Probe Execution

Step 7c: SKIPPED — no probe scripts declared in PLAN/SUMMARY and no `scripts/*/tests/probe-*.sh` exist.

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| tests/integration/test_embed_idempotency.py | VEC-02/VEC-03 (G-03-3) | 4 | 0 | No | Behavioral (count/set equality vs live table state; disjoint-set replace proof; call-count proofs) | PASS |
| tests/unit/search/test_vector.py (TestVectorEmbeddingDeletion) | VEC-02 | 3 | 0 (env-guard did not trigger) | No | Value (SQL string + params inspection; real-vec0 row counts) | PASS |
| tests/unit/cli/test_index.py (new) | VEC-03 | 3 | 0 | No | Behavioral (delete-call absence, embed-call counts, output line) | PASS |

Disabled tests on requirements: 0. Circular patterns: 0 — the integration tests assert independent
invariants (counts, set equality, disjointness) against live table state, not system output against
itself; expected values do not originate from the code under test. One legitimate deviation noted in
03-08-SUMMARY (tracer run-2 assertion moved from "fresh ids" to "byte-identical skip") is sound: it
reflects Task 2's designed skip semantics, and the replace proof was relocated to the --force and
self-heal tests where re-chunking genuinely occurs — verified in the test source.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-----------|--------|----------|
| VEC-01 | 03-01, 03-02, 03-05, 03-06, 03-07 | Configure backends via Settings and CLI | ✓ SATISFIED | Truths 1, 5, 7-11; UAT live pass on a real OpenAI-compatible endpoint. REQUIREMENTS.md: Complete — consistent. |
| VEC-02 | 03-03, 03-04, 03-06, 03-08 | sqlite-vec vector search / refuse brute-force | ✓ SATISFIED | Truths 2, 6, 13, 14, 17; idempotent store integrity restored. REQUIREMENTS.md: Complete — consistent. |
| VEC-03 | 03-04, 03-05, 03-06, 03-08 | Batch embedding insertion | ✓ SATISFIED | Truths 3, 15, 16; skip/force semantics make the batch flow honest. REQUIREMENTS.md: Complete — consistent. |
| VEC-04 | 03-02 | ModelScope download as HuggingFace alternative | ✓ SATISFIED | Truths 4, 12; UAT tests 2-3 live-verified against modelscope.cn including interrupted-download resume. **REQUIREMENTS.md still says Pending — stale bookkeeping; recommend updating** (this verifier does not edit REQUIREMENTS.md). |

**Orphaned requirements:** none — all four VEC IDs mapped to Phase 3 in REQUIREMENTS.md are claimed
by plan frontmatters.

### Decision Coverage

9/10 CONTEXT.md decisions honored in shipped artifacts (soft warning, non-blocking per gate). The
one miss, **D-07** ("the existing `pull` command's ModelScope fallback for GGUF models remains
unchanged"), is a no-change decision that leaves no artifact trace; the user already accepted
D-06/D-07/D-08/D-10 as covered-by-legacy on 2026-09-03 (recorded in the previous VERIFICATION.md per
STATE.md). Carried forward unchanged.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/sif/cli/commands/index.py` | 127-140 + 280-284 | **CR-01 (03-REVIEW.md, validated):** update_cmd never invalidates chunks/embeddings on content change; the new completeness check then skips edited documents forever — stale BM25 chunks + stale vectors until global --force | ⚠️ Warning → human decision | Introduced interaction (03-08's check makes pre-existing staleness silent); outside G-03-3's scoped truth; core edit->update->embed->search loop degraded. Fix is small (invalidate on checksum change). See Human Verification item 1. |
| `src/sif/cli/commands/index.py` | 236, 322-328 | **CR-02 (03-REVIEW.md, validated):** failed-collections ClickException raised inside `with db.connection:` rolls back all successful collections' work after printing success; re-bills remote backends on retry | ⚠️ Warning → human decision | Correctness/cost defect in the failure path; contradicts the plan's assumed partial-state model, though self-heal still converges. See Human Verification item 2. |
| `src/sif/database/schema.py` | documents_fts_update trigger | **Verifier discovery (pre-existing, FND-06 / Phase 1 Pending):** the trigger direct-UPDATEs the external-content FTS5 table; medium+ content changes raise `database disk image is malformed` (reproduced with no embed run involved; trigger predates this milestone) | ⚠️ Warning (out of phase scope) | `sif index update` on a substantially edited document crashes before CR-01's staleness can even manifest. The CR-01 fix must account for this; root fix is the FTS5 external-content delete+insert pattern — Phase 1 / FND-06 territory. |
| `src/sif/cli/commands/index.py` | 156-160 (+ repositories.py:223-231) | **WR-01 (03-REVIEW.md, validated):** file deletion via `doc_repo.delete` leaves orphaned vec0 rows that occupy KNN top-k slots (post-KNN JOIN filtering) until `sif cleanup` | ⚠️ Warning | Same orphan-pollution class as G-03-3 but on the removal path — explicitly excluded from 03-08 scope by prohibition P3 ("cleanup command's job"). Recommend a follow-up. |
| `src/sif/cli/commands/index.py` / factory.py | 207-234 / 58-103 | **WR-02 (03-REVIEW.md):** local backends drop the embedding_dim kwarg; model-vs-schema dim mismatch fails mid-insert with a raw sqlite-vec error instead of fail-fast | ⚠️ Warning | Only openai backend cross-checks dims today. |
| `src/sif/search/vector.py` | 56-73 | **WR-03/WR-04 (03-REVIEW.md):** `k = {options.limit}` interpolated into SQL text (adjacent params use placeholders); collection filter applied after the KNN k-limit — filtered searches can silently under-return | ⚠️ Warning | Pre-existing search-path behavior, kept byte-identical by prohibition P2; belongs to a search-phase fix. |
| `src/sif/mcp/backend.py` | 48-52 | WR-07 (carried): MCP factory call drops api_key/api_base | ⚠️ Warning | Out of SC1's "via Settings and CLI" scope; Phase 9. |
| `pyproject.toml` | — | requires-python >= 3.9 vs PEP 604 code; mypy env breakage (deferred-items.md) | ℹ️ Info (out of scope) | Carried; blocks `mypy src/sif` in this environment. 03-08 introduced zero new type errors (scoped check in 03-08-SUMMARY). |
| uv venv | — | `uv run pytest` red (missing httpx/pytest_asyncio) while canonical env green | ℹ️ Info | Environment artifact; canonical suite green (554/0 failed). |

Debt-marker gate: no TBD/FIXME/XXX in any phase-modified file. The `# noqa: ARG001` marker that
evidenced the ignored --force (G-03-3 root cause) is gone.

### Human Verification Required

1. **REVIEW CRITICAL CR-01 — remediation decision (escalation).** Edit a note -> `sif index update`
   -> `sif index embed` (no --force): the document is skipped and serves stale chunks/vectors
   indefinitely. Validated by this verifier (code + empirical). Options: (a) fix now via a small
   gap-closure plan — invalidate chunk/embedding state when checksum changes in update_cmd (also
   covers the WR-01 removal path cheaply), or (b) accept as deferred with explicit tracking. Note
   the fix interacts with the pre-existing FTS trigger defect below.
2. **REVIEW CRITICAL CR-02 — transaction-model decision (escalation).** Per-collection transactions
   with the failure raise moved outside the transaction block, or true all-or-nothing semantics
   without the premature success print. Validated by this verifier (code reading of
   index.py:236/322-328 against sqlite3 context-manager semantics).
3. **OPTIONAL — 03-08 D6 spot-check.** Two `sif index embed` runs + `sif search vsearch` on a real
   collection; each document once per live chunk. Optional per plan; mechanics already proven
   against a real sqlite-vec store, and the UAT round performed this exact shape when finding G-03-3.

Context for the CR-01 fix (verifier discovery): medium+ content edits currently crash in update_cmd
with `sqlite3.DatabaseError: database disk image is malformed` via the `documents_fts_update`
trigger (direct UPDATE on an external-content FTS5 table). This is pre-existing (FND-06, Phase 1,
correctly tracked Pending in REQUIREMENTS.md) and reproduces with no embedding involved. Any CR-01
fix should land alongside or after the FND-06 trigger fix, otherwise the edit loop stays broken at
the update step for substantial edits.

### Gaps Summary

**No must-have gaps.** The re-verification target — UAT gap G-03-3 — is closed and behaviorally
verified: repeated `sif index embed` runs are idempotent for the vector store (delete-before-insert
replace, exact-set skip, honored --force, self-healing), proven by four integration tests against a
real sqlite-vec database that this verifier independently re-ran (all pass), backed by 6 new unit
tests, with all three 03-08 prohibitions upheld (additive-only vector.py, no cleanup extension,
fail-fast on vec unavailability). All four previous human items were exercised by the UAT round and
resolve favorably; the backstop truth (ModelScope resume) is upgraded to VERIFIED on direct
observation. The full canonical quality suite is green (ruff clean, 554 passed / 11 skipped /
0 failed), and all 17 truths — 12 carried + 5 new — are verified, every behavior-dependent one by a
passing behavioral test.

Status is **human_needed**, not passed, because the phase's own post-03-08 code review
(03-REVIEW.md, 2026-09-04T11:39Z, status: issues_found) carries two critical findings this verifier
independently validated — CR-01 (edit-staleness made silent by the new skip check) and CR-02
(rollback-after-success-print transaction defect) — whose remediation-vs-deferral is a developer
decision neither blocked nor required by any Phase 03 must-have (03-08's scope was deliberately
G-03-3-only, and its truths are met to the letter). Neither is covered by a later phase's roadmap
goal (Phase 4 is reranking/query-expansion), so they cannot be silently deferred. One additional
pre-existing discovery (the FTS5 external-content trigger corrupting the index on medium+ content
updates — FND-06, Phase 1) is surfaced as required context for the CR-01 fix. Bookkeeping: VEC-04
remains "Pending" in REQUIREMENTS.md despite live UAT evidence — recommend updating.

---

## Acknowledged Gaps

- **[2026-09-04] mypy cannot run in this environment (pre-existing, user-acknowledged at phase close).** `[tool.mypy] python_version = 3.9` conflicts with sentence-transformers 5.4.1's 3.10+ syntax; `mypy src/sif` dies inside site-packages. Not caused by phase 03; mandated quality suite (ruff check / ruff format --check / pytest 572 passed) is green. Fix suggestion: raise mypy `python_version` to >=3.10 or add a `sentence_transformers` override. Tracked in deferred-items.md; scheduled for immediate follow-up fix this session.

---

_Verified: 2026-09-04T11:58:41Z_
_Verifier: Claude (gsd-verifier)_
_Acknowledged at phase completion: 2026-09-04 (UAT 7/7 passed, security threats_open: 0)_
