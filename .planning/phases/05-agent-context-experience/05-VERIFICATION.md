---
phase: 05-agent-context-experience
verified: 2026-09-06T05:19:14Z
status: gaps_found
score: 15/19 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "Search results include relevant contextual descriptions alongside document content (SC-3) — fails when the context target path and the stored document path differ by symlink resolution (e.g. user adds /tmp/... while documents store /private/tmp/... on macOS)"
    status: failed
    reason: >-
      Live falsification. `_attach_contexts()` in BM25/Vector/Hybrid queries
      `WHERE context_type = 'path' AND target_id IN (<result paths>)`. The
      contexts table stores the verbatim user-typed path (`context add` does no
      normalization), while documents.path stores the resolved path. The SQL
      IN-clause returns ZERO rows for the mismatch, so the Python-side
      `os.path.realpath()` normalization (bm25.py:120-125, vector.py, hybrid.py:142-145)
      never receives any rows to normalize — it is dead code for exactly the
      scenario gap-closure plan 05-06 was created to fix. The normalized-path
      unit tests pass only because the mocked context cursor returns rows
      regardless of the SQL WHERE clause; they never validate that real SQL
      matching occurs. Verified live: `context add path /tmp/.../doc1.md` +
      document `/private/tmp/.../doc1.md` -> `context_description: null`;
      same flow with the resolved `/private/tmp/...` path -> description
      attached. Same root cause makes `context prune` delete the valid
      mismatched context (REVIEW.md CR-02, reproduced live).
    artifacts:
      - path: "src/sif/search/bm25.py"
        issue: "_attach_contexts() SQL IN-clause pre-filters with result paths only; realpath normalization at lines 120-125 is unreachable for mismatched forms"
      - path: "src/sif/search/vector.py"
        issue: "identical _attach_contexts() pattern and identical dead normalization"
      - path: "src/sif/search/hybrid.py"
        issue: "identical _attach_contexts() pattern and identical dead normalization (lines 112-146)"
      - path: "src/sif/cli/commands/context.py"
        issue: "context_add() stores path targets verbatim (line 58) with no expanduser/realpath normalization"
      - path: "src/sif/database/repositories.py"
        issue: "delete_orphaned_paths() compares raw target_id strings against documents.path — deletes contexts whose paths differ only by symlink resolution (CR-02, reproduced live)"
    missing:
      - "Normalize the path target at `context add` time (os.path.realpath + expanduser) so contexts.target_id matches the resolved form documents store, and/or include both original and normalized variants in the _attach_contexts() IN clause"
      - "Backfill/migrate existing verbatim context rows or re-normalize on read"
      - "Make delete_orphaned_paths() use the same normalization as search so prune stops deleting contexts for existing documents"
      - "Replace or supplement the mock-based normalized-path tests with a real in-memory SQLite test that exercises the actual SQL matching (the current mocks bless the fix without proving it)"
  - truth: "Vector search results include context_description when path context exists, even with macOS /private/tmp normalization (05-06 truth)"
    status: failed
    reason: "Same SQL IN-clause root cause as SC-3; code path is byte-identical to BM25's _attach_contexts(). Unit test passes via mocked cursor only."
    artifacts:
      - path: "src/sif/search/vector.py"
        issue: "identical dead normalization pattern"
    missing:
      - "Same fix as SC-3 root cause"
  - truth: "Hybrid search results include context_description when path context exists, even with macOS /private/tmp normalization (05-06 truth)"
    status: failed
    reason: "Same SQL IN-clause root cause as SC-3; HybridSearcher._attach_contexts() shares the identical query construction."
    artifacts:
      - path: "src/sif/search/hybrid.py"
        issue: "identical dead normalization pattern"
    missing:
      - "Same fix as SC-3 root cause"
---

# Phase 5: Agent Context Experience Verification Report

**Phase Goal:** Users can augment document collections with contextual descriptions to improve retrieval quality for agent workflows.
**Verified:** 2026-09-06T05:19:14Z
**Status:** gaps_found
**Re-verification:** No — initial verification

**Verification basis:** Verified against current on-disk paths (`src/sif/...` — package renamed from `docsift` in Phase 08; `SIF_DB_PATH` replaced `DOCSIFT_DB_PATH`). All truth statuses below are backed by live CLI execution against a scratch SQLite DB, direct code reading, single named pytest runs, or a live in-process behavioral test of the migration — not by SUMMARY.md claims.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC-1: User can add contextual descriptions to paths or collections via `context add` | ✓ VERIFIED | Live: `sif context add path /tmp/.../doc1.md "..."`, `context add collection verify-coll "..."` (name resolved to collection UUID), `context add global global "..."` all succeeded; click.Choice validates type; upsert on re-add (src/sif/cli/commands/context.py:26-73) |
| 2 | SC-2: User can list and remove contextual descriptions via `context list` and `context rm` | ✓ VERIFIED | Live: `context list` renders per-row Type (path/collection/global); `--type collection` filters correctly; `context rm <uuid>` removed the row (verified absent afterwards); `rm` alias registered (context.py:157) |
| 3 | SC-3: Search results include relevant contextual descriptions alongside document content | ✗ FAILED | Live: works ONLY when contexts.target_id byte-matches documents.path. With user-typed `/tmp/...` vs stored `/private/tmp/...`, BM25 JSON returned `context_description: null`. Root cause: SQL `IN` pre-filter in `_attach_contexts()` (bm25.py:115-119) returns zero rows; Python realpath normalization (bm25.py:120-125) is dead code in the mismatch scenario. See Gaps |
| 4 | contexts table exists with target_id, context_type, content columns + CHECK constraint (05-01) | ✓ VERIFIED | Live in-process test: schema.py:94-105 creates table with `CHECK(context_type IN ('path','collection','global'))`; INSERT with type 'bogus' raised IntegrityError |
| 5 | Existing path_contexts data migrates to contexts with context_type='path'; old table dropped; atomic/idempotent (05-01) | ✓ VERIFIED | Live in-process test on in-memory SQLite via production `sqlite_vec.load()`: 2 legacy rows migrated with content/timestamps preserved, `path_contexts` dropped from sqlite_master, second `create_all()` left count at 2 (idempotent), SAVEPOINT rollback path present (schema.py:107-131) |
| 6 | SchemaManager.get_stats() reports context count from contexts (05-01) | ✓ VERIFIED | schema.py:383-384 `SELECT COUNT(*) FROM contexts` keyed `contexts`; live `sif status` shows "Contexts" row (not "Path Contexts") |
| 7 | Path/collection/global contexts stored with correct context_type in DB (05-05) | ✓ VERIFIED | Live DB inspection after CLI adds: rows show context_type='path', 'collection' (target=collection UUID), 'global' |
| 8 | List contexts displays actual context_type per row (05-05) | ✓ VERIFIED | Live: table rendered `global`, `path`, `collection` per row (context.py:131 uses `ctx_item.context_type`); PathContext carries the field (core/models.py:190) and `_row_to_context` reads it (repositories.py:452) |
| 9 | Collection targets resolved by name first, then by ID (05-02 D-02) | ✓ VERIFIED | Live: `context add collection verify-coll` resolved by name to UUID; code get_by_name → get_by_id fallback (context.py:47-55); unit tests cover ID fallback and not-found error |
| 10 | User can prune orphaned path contexts via `context prune` (05-02 D-12) | ✓ VERIFIED (with warning) | Live: added context for `/nonexistent/orphan.md`, prune reported "Pruned 1", valid contexts survived. WARNING: prune also deletes valid contexts whose paths differ only by symlink resolution (REVIEW CR-02) — reproduced live: context for existing doc `/tmp/sif-verify2/only.md` (stored `/private/tmp/...`) was pruned. Quality debt tracked in 05-REVIEW.md |
| 11 | BM25 results include context_description even with macOS /private/tmp normalization (05-06) | ✗ FAILED | Live falsified — see Truth 3. Unit test `test_search_attaches_context_with_normalized_path` passes only because the mocked context cursor bypasses the SQL WHERE clause |
| 12 | Vector results include context_description even with normalization (05-06) | ✗ FAILED | Byte-identical `_attach_contexts()` SQL pattern (vector.py:116-132); same root cause proven on BM25. Live run not possible in this env (modelscope embedding backend absent) — unit tests pass via mocks only |
| 13 | Hybrid results include context_description even with normalization (05-06) | ✗ FAILED | Identical `_attach_contexts()` construction (hybrid.py:112-146); same root cause |
| 14 | SearchPipeline final results include context_description after reranking (05-03) | ✓ VERIFIED | hybrid.py:273 `return self.hybrid._attach_contexts(results)` is the final return, after rerank (line 265) and snippets (line 271); single named test `test_pipeline_search_attaches_context_after_reranking` passed |
| 15 | Only path contexts are attached in search (05-03 D-07) | ✓ VERIFIED | All three `_attach_contexts()` implementations filter `context_type = 'path'` in SQL (bm25.py:117, vector.py:124, hybrid.py:120) |
| 16 | context_description survives RRF fusion (05-01) | ✓ VERIFIED | rrf.py:76 and rrf.py:160 propagate `context_description=result.context_description` in both fuse() and fuse_with_weights(); single named test `test_hybrid_search_attaches_context_after_rrf` passed |
| 17 | Status command respects SIF_DB_PATH via Settings.get_db_path() (05-07) | ✓ VERIFIED | Live: entire end-to-end run used `SIF_DB_PATH=<scratch>` and every command hit that DB; main.py:26-37 callable default `_get_default_db_path` → `get_settings().get_db_path()`; status fallback at main.py:103 |
| 18 | Comprehensive unit tests exist for migration, repository, CLI, and search integration (05-04) | ✓ VERIFIED | tests/unit/cli/test_context.py (16 tests), test_schema.py (16), test_bm25.py (22), test_vector.py (19), test_hybrid.py (26), test_status.py (2). Full suite: 629 passed, 11 skipped in a clean environment (2 initial failures were this verifier's shell leaking OPENAI_* env vars; FORCE_COLOR similarly breaks 2 prune substring assertions — see Anti-Patterns) |
| 19 | ContextRepository with context_type support + backward-compat alias (05-01/05-05) | ✓ VERIFIED | Live round-trip: create with context_type='collection'/'global' → get_by_target/list_by_type return correct type; parameterized INSERT uses `context.context_type` (repositories.py:381); `PathContextRepository = ContextRepository` alias (repositories.py:460) |

**Score:** 15/19 truths verified (4 failed, all sharing one root cause)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/sif/database/schema.py` (was src/docsift/...) | contexts table, SAVEPOINT migration, idx_contexts_target | ✓ VERIFIED | Lines 23-24 (create_all order), 94-131 (table+migration), 339-340 (index), 383-384 (stats); live-tested |
| `src/sif/database/repositories.py` | ContextRepository with get_by_target, list_by_type, delete_orphaned_paths | ✓ VERIFIED | Lines 366-456; alias at 460; live round-trip tested |
| `src/sif/core/models.py` | SearchResult.context_description; PathContext.context_type | ✓ VERIFIED | Lines 221/236; 190/200 |
| `src/sif/cli/commands/context.py` | add/list/remove/rm/prune with type support | ✓ VERIFIED | 157 lines, all commands live-tested |
| `src/sif/cli/main.py` | rm-free registration, Contexts stat, Settings-based default | ✓ VERIFIED | Lines 26-37, 76/86, 103, 122 |
| `src/sif/search/bm25.py` | _attach_contexts at final return | ✓ VERIFIED (wired; behavior gap in Truth 3) | Line 107 return, 109-126 helper |
| `src/sif/search/vector.py` | _attach_contexts at final return | ✓ VERIFIED (wired; behavior gap in Truth 3) | Line 114 return, 116-132 helper |
| `src/sif/search/hybrid.py` | _attach_contexts in HybridSearcher (3 returns) + SearchPipeline final | ✓ VERIFIED (wired; behavior gap in Truth 3) | Lines 68/70/90 + 273 |
| `tests/unit/cli/test_context.py` | ≥200 lines, ≥12 tests | ✓ VERIFIED | 16 tests, 6 classes |
| `tests/unit/database/test_schema.py` | migration tests | ✓ VERIFIED (7 migration/contexts tests; 4 skip in this env — see Anti-Patterns) | test_migrates_*, test_contexts_table_* |
| `tests/unit/search/test_{bm25,vector,hybrid}.py` | context attachment tests | ✓ VERIFIED (see Test Quality Audit — mock limitation) | TestXContextAttachment classes present, all pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| SchemaManager.create_all() | _migrate_path_contexts() | called before _create_contexts_table | ✓ WIRED | schema.py:23-24; live-verified migration |
| ContextRepository.list_by_type() | contexts table | SELECT ... WHERE context_type = ? | ✓ WIRED | repositories.py:403-409; live-tested |
| context_add | CollectionRepository.get_by_name | name-first resolution | ✓ WIRED | context.py:47-55; live-tested |
| context_remove | `rm` alias | add_command(name="rm") | ✓ WIRED | context.py:157; live-tested |
| context_prune | delete_orphaned_paths | repository call | ✓ WIRED | context.py:149-151; live-tested |
| BM25Searcher.search() | _attach_contexts() | final return | ✓ WIRED | bm25.py:107 |
| VectorSearcher._search_with_vec() | _attach_contexts() | final return | ✓ WIRED | vector.py:114 |
| HybridSearcher.search() | _attach_contexts() | all 3 returns, after RRF | ✓ WIRED | hybrid.py:68/70/90 |
| SearchPipeline.search() | hybrid._attach_contexts() | FINAL return after rerank+snippets | ✓ WIRED | hybrid.py:273 |
| status_cmd | Settings.get_db_path() | callable --index default | ✓ WIRED | main.py:26-37, 103; live-tested via SIF_DB_PATH |
| SearchResult.path | contexts.target_id | os.path.realpath normalization | ✗ NOT_WIRED (broken by SQL pre-filter) | The normalization exists but the SQL IN-clause returns zero rows for mismatched forms — the link never fires in the real mismatch scenario |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| context add/list/rm/prune | contexts table rows | real SQLite via ContextRepository | Yes — live round-trips | ✓ FLOWING |
| search --json output context_description | SearchResult.context_description | `_attach_contexts()` DB query | Conditional — only when target_id byte-matches result path | ⚠️ STATIC in the mismatch scenario (live: null) |
| status "Contexts" | stats["contexts"] | `SELECT COUNT(*) FROM contexts` | Yes — live count matched | ✓ FLOWING |
| MCP query tool | mcp SearchResult | backend.py rebuilds from core results | No — context_description dropped (no field in mcp/protocol.py:199-208) | ⚠️ Info: out of Phase 05 scope; Phase 09 SCs did not include it |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Migration preserves data, drops old table, idempotent | In-process live test (production sqlite_vec.load) | All assertions passed | ✓ PASS |
| CHECK constraint rejects invalid context_type | In-process live test | IntegrityError raised | ✓ PASS |
| ContextRepository round-trip collection/global | In-process live test | context_type preserved | ✓ PASS |
| BM25 attach (byte-match path) | `sif search search ... --json` (live) | context_description present | ✓ PASS |
| BM25 attach (symlinked /tmp path) | `sif search search ... --json` (live) | context_description null | ✗ FAIL |
| Prune deletes valid mismatched-path context | `sif context prune` (live) | context for existing doc deleted | ✗ FAIL (CR-02 quality debt) |
| Pipeline attach after rerank | pytest -k test_pipeline_search_attaches_context_after_reranking | 1 passed | ✓ PASS |
| Hybrid attach after RRF | pytest -k test_hybrid_search_attaches_context_after_rrf | passed | ✓ PASS |
| Normalized-path unit tests (bm25/vector/hybrid) | pytest -k ContextAttachment | 8+3+3 passed | ✓ PASS (but mock-bypassed — see Test Quality Audit) |
| CLI context suite | pytest tests/unit/cli/test_context.py test_status.py | 18 passed | ✓ PASS |
| Full suite | pytest (clean env) | 629 passed, 11 skipped | ✓ PASS |

### Probe Execution

No probes declared in any Phase 05 plan and no `scripts/*/tests/probe-*.sh` exist. Step 7c: N/A.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CTX-01 | 05-01, 05-02, 05-04, 05-05 | `context add`: add description text for paths or collections | ✓ SATISFIED | Live CLI adds for path/collection/global with correct context_type storage |
| CTX-02 | 05-02, 05-04, 05-05, 05-07 | `context list` and `context rm`: view and delete contexts | ✓ SATISFIED | Live list/filter/rm; status honors SIF_DB_PATH |
| CTX-03 | 05-03, 05-04, 05-06, 05-07 | Context descriptions carried back in search results | ✗ PARTIAL | Works for byte-matching path forms (live); fails for symlink-resolved mismatch (/tmp vs /private/tmp) — the exact scenario gap-closure plan 05-06 claimed to close |

Orphaned requirements: none — REQUIREMENTS.md maps only CTX-01..03 to Phase 5 and all three are claimed by plans. Note: REQUIREMENTS.md still marks all three "Pending" and ROADMAP.md shows plans 05-05/06/07 checkboxes unchecked — bookkeeping lag, not code state.

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| tests/unit/search/test_bm25.py::test_search_attaches_context_with_normalized_path | CTX-03 | 1 | 0 | Mock-bypassed | Value | ⚠️ INSUFFICIENT — mocked context cursor returns rows regardless of SQL; real DB returns zero rows (proven live) |
| tests/unit/search/test_vector.py::test_search_attaches_context_with_normalized_path | CTX-03 | 1 | 0 | Mock-bypassed | Value | ⚠️ INSUFFICIENT — same pattern |
| tests/unit/search/test_hybrid.py::test_hybrid_search_attaches_context_with_normalized_path | CTX-03 | 1 | 0 | Mock-bypassed | Value | ⚠️ INSUFFICIENT — same pattern |
| tests/unit/database/test_schema.py (migration tests) | CTX-01 | 12 | 4 (this env) | No | Value/Behavioral | ⚠️ Env-skip: `vec_db` fixture loads extension via bare name `load_extension("vec0")` which fails although sqlite_vec is installed (production code uses `sqlite_vec.load()`); migration verified live by verifier instead |
| tests/unit/cli/test_context.py | CTX-01/02 | 16 | 0 | No | Value | OK |
| tests/unit/cli/test_status.py | CTX-02 | 2 | 0 | No | Value | OK |

**Disabled tests on requirements:** 0. **Circular/mock-blessed patterns:** 3 (the normalized-path tests — this is precisely why the SC-3 gap survived a green suite). **Insufficient assertions:** 3 (same tests).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| src/sif/search/bm25.py (also vector.py, hybrid.py) | 115-125 | Dead normalization: realpath applied to SQL-filtered rows that can never mismatch | 🛑 Blocker | SC-3 fails in real mismatch scenario |
| src/sif/cli/commands/context.py | 58 | Path target stored verbatim (no expanduser/realpath) | 🛑 Blocker | Root cause of both search-attach and prune failures |
| src/sif/database/repositories.py | 437-444 | delete_orphaned_paths raw string comparison | ⚠️ Warning | Deletes valid contexts (REVIEW CR-02, reproduced live) |
| src/sif/database/schema.py | 236-241, 260-266 | FTS5 delete triggers use plain DELETE form (invalid in AFTER DELETE on external-content FTS) | ⚠️ Warning | REVIEW CR-01 — stale FTS entries after document deletion; search-quality debt tracked separately in 05-REVIEW.md, out of this phase's context-goal scope |
| tests/unit/database/test_schema.py | 12-18 | Extension load via bare name, skips despite sqlite_vec installed | ⚠️ Warning | Migration tests silently skip in this environment |
| tests/unit/cli/test_context.py | 401, 419 | `"Pruned N" in result.output` breaks under FORCE_COLOR | ℹ️ Info | Env-dependent test brittleness (failed in verifier shell, passes clean) |
| mcp/protocol.py + mcp/backend.py | 199-208, 92-99 | MCP SearchResult lacks context_description field; backend drops it | ℹ️ Info | Agent-facing MCP path omits descriptions; Phase 09 scope did not require it — consider for backlog |
| 05-01/02/03 SUMMARY commit hashes | — | 7 of 16 documented hashes absent from history (worktree-branch churn; final-state commits a95f302, f6de07e, bf321ea, 9d6663a, 23f9cd5, ba8a440, 32de054, e785ea3 all exist) | ℹ️ Info | Code verified on disk regardless |

Debt-marker scan (TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER) on all 10 phase source files: zero matches.

### Decision Coverage

13 CONTEXT.md decisions checked: 12 honored, 1 not found (D-13, a negative decision — "deletion does not auto-delete contexts" — not greppable as presence; behavior matches the decision, prune is explicit). Non-blocking warning per gate contract.

### Human Verification Required

None newly required — 05-UAT.md is status: complete with 11/11 tests passing (re-verified live 2026-09-06 with evidence recorded per-test). This verification's gaps are machine-demonstrated (live CLI falsification) and structured for `/gsd-plan-phase --gaps`; they do not require human adjudication. Note: the 2026-09-06 UAT re-verification of Test 9 ("BM25 JSON shows context_description") must have used a byte-matching path form — under a symlinked `/tmp/...` context path the same command returns null, as reproduced above.

### Gaps Summary

One root cause produces all four failed truths: **path-form mismatch between contexts.target_id (verbatim user input) and documents.path (resolved), combined with an SQL IN-clause pre-filter that drops all mismatched rows before the realpath normalization can act.**

- The CLI half of the goal (SC-1, SC-2) is fully delivered and live-verified, including the gap-closed context_type storage/display and SIF_DB_PATH status behavior.
- The search half (SC-3 / CTX-03) works only when path forms match exactly. The specific defect UAT Gap 4 reported and plan 05-06 was written to close is NOT closed in real behavior: the fix normalized the Python-side dictionary but left the SQL filter on raw strings, so the normalization is unreachable for the mismatch case. Three unit tests bless the fix because their mocked cursors bypass the SQL.
- The same mismatch makes `context prune` silently delete contexts for existing documents (REVIEW CR-02, reproduced live): a user who adds a context via `/tmp/...` gets an unusable context that prune then destroys.
- Recommended fix direction (single change closes all four truths): normalize path targets at `context add` time (expanduser + realpath) and/or extend the `_attach_contexts()` IN-list with normalized variants; align `delete_orphaned_paths()` with the same normalization; add one real-SQL (in-memory SQLite) regression test for the mismatch scenario.

No later milestone phase (06 docs, 07 skills, 08 rename, 09 MCP) covers path normalization, so nothing is deferred.

---

_Verified: 2026-09-06T05:19:14Z_
_Verifier: Claude (gsd-verifier)_
