---
phase: 03-embedding-vector-search
plan: 08
subsystem: vector-search
tags: [sqlite-vec, vec0, embeddings, idempotency, click-cli, delete-before-insert, force-flag]

requires:
  - phase: 03-embedding-vector-search (plans 03-01..03-07)
    provides: VectorSearcher vec0 insert/search, embed_cmd batch-embed flow (D-10),
      EmbeddingManager.get_model_info, schema FLOAT[embedding_dim] vec0 tables
provides:
  - VectorSearcher.delete_embeddings_by_document(document_id) -> int — parameterized
    vec0 DELETE returning the removed row count
  - VectorSearcher.get_embedded_chunk_ids(document_id) -> set[str] — parameterized read
    of a document's stored embedding chunk ids (None rows skipped)
  - Idempotent `sif index embed`: delete-before-insert per re-chunked document, so
    repeated runs replace vectors instead of accumulating orphaned searchable rows
  - Honored --force semantics — default run skips documents whose live chunks have an
    exact complete embedding set (zero embedding calls); --force re-embeds everything
  - Crash-safety self-healing — partial, orphaned, or stale sets re-embed on the next
    default run
affects: [04-advanced-search-pipeline, 09-mcp-server-implementation, phase-verification, ship]

actuals:
  tokens: 6656
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Delete-before-insert in the same transaction: chunk_repo.delete_by_document ->
      VectorSearcher.delete_embeddings_by_document -> add_embeddings_batch (fresh uuid4
      chunk ids can never collide with old rows, so old vectors must be removed explicitly)"
    - "Exact chunk-id-set completeness check: {c.id for c in get_by_document(doc)} vs
      get_embedded_chunk_ids(doc) — skip only on exact equality; every other state re-embeds"
    - "Probe-free dimension: manager.get_model_info()['embedding_dim'] with an
      isinstance-guarded embed_single('probe') fallback — remote backends are never
      billed for a throwaway probe"
    - "Real-sqlite-vec integration harness: settings-aware schema init under a patched
      get_settings (FLOAT[8] vec0), mocked EmbeddingManager with per-call vector log"

key-files:
  created:
    - tests/integration/test_embed_idempotency.py
  modified:
    - src/sif/search/vector.py
    - src/sif/cli/commands/index.py
    - tests/unit/search/test_vector.py
    - tests/unit/cli/test_index.py

key-decisions:
  - "Probe-free dimension source: get_model_info()['embedding_dim'] on the eagerly-loaded
    manager, isinstance(int)-guarded with the legacy probe as fallback (plan's fallback
    clause; mocks never hit the probe either way)"
  - "Skip decision extracted to module-level _needs_embedding(live, embedded, force)
    helper per Task 3 guidance — keeps embed_cmd within its existing suppressions, no
    new noqa added, mccabe pressure contained"
  - "VectorSearcher construction failure converts to click.ClickException (never
    swallowed into failed_collections) per D-03 fail-fast and the plan's prohibition"
  - "Task 1 tracer run-2 assertion updated to final semantics: a default re-run on a
    complete store is byte-identical (skip); replace-not-append is proven by the --force
    and self-heal tests, which assert fresh disjoint chunk-id sets"
  - "No existing test_index.py scaffolding changes were needed: MagicMock's default
    empty iteration keeps get_by_document on the embed path for the three tests the plan
    expected to break"

patterns-established:
  - "Real-vec0 idempotency harness: seed through real repositories under patched
    settings, invoke embed_cmd twice through CliRunner, assert count/set equality via a
    vec-loaded raw connection (sqlite_vec.load required on every connection touching
    the vec0 table)"
  - "Per-call vector logging on the mocked manager (distinct vectors per input index
    plus a per-call offset) makes runs distinguishable and gives the search test exact
    query vectors"

requirements-completed: [VEC-02, VEC-03]

coverage:
  - id: D1
    description: "VectorSearcher delete/read methods — delete_embeddings_by_document
      (parameterized DELETE, rowcount return) and get_embedded_chunk_ids (parameterized
      SELECT, non-None set); insert and search paths byte-identical (0 deletions in diff)"
    requirement: VEC-02
    verification:
      - kind: unit
        ref: "tests/unit/search/test_vector.py::TestVectorEmbeddingDeletion (3 tests, pass)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Delete-before-insert wiring in embed_cmd — one VectorSearcher per
      non-empty collection with probe-free dimension, RuntimeError construction failure
      surfaced as ClickException, old vectors removed before the fresh batch (G-03-3
      root cause)"
    requirement: VEC-03
    verification:
      - kind: integration
        ref: "tests/integration/test_embed_idempotency.py::test_two_embed_runs_leave_one_row_per_live_chunk (pass)"
        status: pass
      - kind: other
        ref: "grep: delete_embeddings_by_document present in both embed_cmd re-chunk branch and vector.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Honored --force — default run skips fully embedded documents with a dim
      already-embedded line and zero manager.embed calls; --force re-embeds all documents
      replacing previous embeddings; ARG001 suppression removed and ruff clean"
    requirement: VEC-03
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_index.py::TestEmbedCommand skip/heal/force tests (3 tests, pass)"
        status: pass
      - kind: integration
        ref: "tests/integration/test_embed_idempotency.py::test_default_run_skips_complete_then_force_reembeds_all (pass)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Self-healing — a document left with missing/partial/stale embeddings by
      a failed or interrupted run is detected and re-embedded to an exact set on the next
      default run (D-10 crash-safety)"
    verification:
      - kind: integration
        ref: "tests/integration/test_embed_idempotency.py::test_default_run_self_heals_partial_state (pass)"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_index.py::test_embed_cmd_default_heals_stale_embedding_state (pass)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Vector search result integrity after repeated runs — each live chunk
      returns exactly once; the UAT document-times-7 duplicate symptom cannot reproduce"
    requirement: VEC-02
    verification:
      - kind: integration
        ref: "tests/integration/test_embed_idempotency.py::test_vector_search_returns_each_chunk_once_after_two_runs (pass)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Optional human confirmation matching the UAT reproduction shape: run
      `sif index embed -c <name>` twice then `sif search vsearch <query>` on a real
      collection — each document appears once per live chunk"
    verification: []
    human_judgment: true
    rationale: "Plan verification item 4 marks this optional: the automated integration
      test already covers the mechanics against a real vec0 store; any local or remote
      backend works for the manual spot-check."

duration: 22min
completed: 2026-09-04
status: complete
---

# Phase 3 Plan 8: Idempotent Embed / G-03-3 Gap Closure Summary

**Idempotent `sif index embed`: delete-before-insert replaces a re-chunked document's vec0 rows, and a per-document exact-set check skips complete documents unless `--force` — closing UAT gap G-03-3 where 7 runs on a 3-chunk collection left 21 searchable embedding rows returning the document 7 times.**

## Performance

- **Duration:** 22 min
- **Started:** 2026-09-04T09:29:52Z
- **Completed:** 2026-09-04T09:51:53Z
- **Tasks:** 3/3
- **Files modified:** 5 (2 src, 3 tests; 1 test file new)

## Accomplishments

- Repeated `sif index embed` runs are now idempotent for the vector store: the re-chunk
  branch deletes a document's old document_embeddings rows before inserting the fresh
  batch, inside the same `with db.connection:` transaction — the exact G-03-3 root cause
  (insert-only batch over fresh uuid4 chunk ids) is removed
- `--force` is honored: the default run embeds only documents whose live chunks lack an
  exact, complete matching embedding set (zero embedding calls when everything is
  embedded); `--force` re-chunks and re-embeds everything, replacing prior embeddings
- Interrupted or partially failed runs self-heal — any missing/partial/orphaned set
  fails the exact-match check and is re-embedded on the next default run
- sqlite-vec unavailability during embed now surfaces as a ClickException instead of
  being silently skipped (D-03 fail-fast; prohibition upheld)
- The batch insert contract (embedding_id/document_id/chunk_id/embedding tuple shape,
  INSERT OR REPLACE semantics) and the entire search path are byte-identical —
  `git diff` on vector.py shows 24 insertions, 0 deletions

## Task Commits

Each task was committed atomically (TDD: RED before GREEN):

1. **Task 1: End-to-end idempotent embed (tracer)** — `bbdfc0e` (test: 5 failing tests,
   tracer reproduced the live bug at `assert 6 == 3`) + `ef2b0f9` (feat: delete/read
   methods + delete-before-insert wiring + probe-free dimension)
2. **Task 2: Honor --force** — `12f077d` (test: skip-semantics tests fail at RED) +
   `7ee95cd` (feat: _needs_embedding decision, skip line, ARG001 removed)
3. **Task 3: Full quality suite green** — verification only, no code changes; suite
   results recorded below

**Plan metadata:** see final docs commit

Tracer feedback gate (auto mode): re-ran all tracer `<verify>` commands end-to-end after
Task 1's GREEN — 17 tests passed, hasattr and grep gates passed. Expanded to Task 2.

## Files Created/Modified

- `src/sif/search/vector.py` — added `delete_embeddings_by_document(document_id) -> int`
  and `get_embedded_chunk_ids(document_id) -> set[str]` (both fully parameterized, single
  `?` placeholder); nothing else in the file changed
- `src/sif/cli/commands/index.py` — embed_cmd: probe-free `embedding_dim` from
  `manager.get_model_info()` (isinstance-guarded probe fallback), one VectorSearcher per
  non-empty collection with RuntimeError → ClickException, per-document
  `_needs_embedding` skip decision with a dim already-embedded line, delete-before-insert
  in the re-chunk branch, `# noqa: ARG001` removed from force; new module-level
  `_needs_embedding` helper
- `tests/integration/test_embed_idempotency.py` (new, 4 tests) — real sqlite-vec
  database harness: two-run count/set idempotency, no-duplicate search results,
  default-run zero-embed skip + --force full re-embed, partial-state self-heal
- `tests/unit/search/test_vector.py` — new `TestVectorEmbeddingDeletion` class: mocked
  SQL-shape assertions (parameterized DELETE/SELECT, no f-string interpolation of the
  id — threat T-03-08-02) and a real-vec0 delete test across two seeded documents
- `tests/unit/cli/test_index.py` — three embed-semantics tests (default skip, default
  heal, --force re-embed) with a shared `_make_embed_mocks`/`_invoke_with_mocks` harness;
  existing tests untouched

## Decisions Made

Documented in key-decisions above; all follow the plan's text. Discretionary items:
skip-line wording ("Already embedded: {path}"), the isinstance-guarded probe fallback,
and the module-level helper placement all match the plan's stated intent.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Lint bug] SIM108 if/else where ternary required in dimension resolution**
- **Found during:** Task 1 GREEN lint pass
- **Issue:** Ruff SIM108 rejected the if/else assigning `embedding_dim`
- **Fix:** Single ternary `model_dim if isinstance(model_dim, int) else len(...)` — mypy
  narrowing still works
- **Files modified:** src/sif/cli/commands/index.py
- **Verification:** ruff check + format green; full suite green
- **Committed in:** `ef2b0f9`

**2. [Rule 3 - Blocking] Integration harness: schema init needed the patched settings and vec0-loaded verification connections**
- **Found during:** Task 1 RED (tests failed for the wrong reason — `no such table` then `no such module: vec0`)
- **Issue:** `_seed_collection` never ran `init_schema()`, and an unpatched init would
  create the vec0 table as FLOAT[1024] (default settings) causing a dimension-mismatch
  RuntimeError on the embed run; raw verification connections also need `sqlite_vec.load`
  before touching the vec0 table
- **Fix:** `_seed_collection(db_path, settings)` runs `db.init_schema()` inside the
  patched-get_settings context; `_store_state` loads sqlite_vec on its connection
- **Files modified:** tests/integration/test_embed_idempotency.py
- **Verification:** RED then showed the intended failures (AttributeError on the missing
  methods; tracer `assert 6 == 3` reproducing the bug)
- **Committed in:** `bbdfc0e`

**3. [Rule 1 - Test/impl consistency] Task 1 tracer run-2 "disjoint chunk ids" assertion superseded by Task 2 skip semantics**
- **Found during:** Task 2 GREEN (tracer failed at `emb_ids2.isdisjoint(emb_ids1)`)
- **Issue:** The Task 1 tracer asserted run-2 re-chunks with fresh ids, but Task 2's
  designed behavior skips the complete document on a default re-run — state stays
  byte-identical, which is a strictly stronger idempotency guarantee
- **Fix:** Run-2 now asserts `(emb2, emb_ids2) == (emb1, emb_ids1)` (no mutation at all);
  the replace-not-append proof lives where re-chunking genuinely happens — the --force
  run and the self-heal test both assert fresh disjoint chunk-id sets. Plan-level
  verification item 1 (count equality + exact set match + once-per-chunk search) is
  unchanged and green
- **Files modified:** tests/integration/test_embed_idempotency.py
- **Verification:** all 4 integration tests pass; plan verification item 1 green
- **Committed in:** `7ee95cd`

**4. [Rule 1 - Lint bug] E501 line length + RUF059 unused unpack in new Task 2 tests**
- **Found during:** Task 2 RED lint pass
- **Issue:** One 101-char invoke line; `mock_coll_repo` unpacked but unused in 3 tests
- **Fix:** Wrapped the invoke call; prefixed the unused unpack with underscore
- **Files modified:** tests/unit/cli/test_index.py
- **Verification:** ruff green
- **Committed in:** `12f077d`

---

**Total deviations:** 4 auto-fixed (2x Rule 1 lint, 1 Rule 3 test-harness blocker, 1 Rule 1 test/impl consistency)
**Impact on plan:** None — no behavioral deviation from the plan; deviation 3 is the
plan's own Task 1 test being brought onto the plan's Task 2 final semantics, with the
original invariant preserved where it applies.

## TDD Gate Compliance

Both implementation tasks carried `tdd="true"`; gate commits verified in git log:

- Task 1: `test(03-08)` (bbdfc0e) precedes `feat(03-08)` (ef2b0f9) — RED failed on
  AttributeError + the live `assert 6 == 3` bug reproduction; GREEN passed all 5
- Task 2: `test(03-08)` (12f077d) precedes `feat(03-08)` (7ee95cd) — RED failed on the
  two skip-semantics tests (`delete_by_document` unexpectedly called; `assert 2 == 1`
  embed count); GREEN passed all 13
- Task 3: type="auto" without tdd — verification only, no code changes, no commit

The Task 2 heal/force/self-heal tests passed at RED by design: they lock in the
embed-path behavior Task 1 already delivered and constrain the new skip branch; the
skip tests prove the suite detects the missing behavior.

## Issues Encountered

- **mypy `src/sif` cannot run in this environment (pre-existing)** — dies inside
  site-packages (`huggingface_hub` 3.10+ pattern-matching syntax vs pyproject's
  `python_version = 3.9`), aborting before reaching project files. Logged in
  `deferred-items.md` since plan 03-07; out of scope per the scope boundary. Scoped
  verification (`mypy --python-version 3.10` on the two modified files) shows vector.py
  fully clean and index.py carrying exactly the same 3 pre-existing errors as at the
  plan-start HEAD (line-shifted only) — zero new type errors introduced, and the two new
  methods carry full strict annotations.
- No other issues. Baseline precondition verified before Task 1: 544 passed, 11 skipped
  (555 collected), 0 failed.

## Known Stubs

None. No placeholder values, TODO/FIXME markers, or unwired data paths were introduced.

## Authentication Gates

None — all tests mock the embedding backend; no external services touched.

## User Setup Required

None — no external service configuration required. (Optional coverage D6 spot-check uses
whatever backend is already configured.)

## Threat Surface

No new threat surface beyond the plan's `<threat_model>`. All four registered threats
received their planned mitigation, verified:
- T-03-08-01 (orphaned rows): delete-before-insert + exact-set completeness check — D2/D3/D4 tests
- T-03-08-02 (SQL construction): both statements fully parameterized, no id interpolation — unit SQL-shape tests
- T-03-08-03 (re-embed cost amplification): default run performs zero embed calls on complete stores — D3 integration test
- T-03-08-04 (concurrent runs): accepted as designed; per-document exact replacement converges instead of accumulating

## Next Phase Readiness

**Phase 03 gap closure complete (8 of 8 plans have SUMMARYs).** G-03-3 — the single
major UAT defect — is closed: repeated embed runs replace vectors, `--force` is honored,
partial states self-heal, and the full quality suite is green (ruff check, ruff format
--check, pytest **554 passed, 11 skipped, 0 failed** — baseline 544+11, +10 tests; 565
collected ≥ the 555 gate). Remaining human items for verification: the optional D6
manual spot-check, plus the carried-over live-endpoint check (03-07 D6) and the mypy
environment issue in deferred-items.md.

## Self-Check: PASSED

All 5 created/modified files exist on disk; all 4 task commits (bbdfc0e, ef2b0f9,
12f077d, 7ee95cd) verified in git log; isolated
`pytest tests/integration/test_embed_idempotency.py -q` green (4 passed).

---
*Phase: 03-embedding-vector-search*
*Completed: 2026-09-04*
