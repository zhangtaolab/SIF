---
phase: 21-scale-maintenance-embedder-identity
plan: 05
subsystem: indexing
tags:
  [
    streaming-embed,
    per-document-commit,
    batch-sanity,
    failure-taxonomy,
    embedder-identity,
    certification,
    watcher,
    sqlite,
    d-15,
    d-16,
    d-17,
    d-18,
  ]

# Dependency graph
requires:
  - phase: 21-scale-maintenance-embedder-identity
    plan: 01
    provides: "identity module (read/write/ensure/certify/check), role-aware EmbeddingManager.embed_documents, prompt scheme"
  - phase: 21-scale-maintenance-embedder-identity
    plan: 02
    provides: "transactionally maintained embedded_documents shadow inside VectorSearcher write/delete methods"
  - phase: 21-scale-maintenance-embedder-identity
    plan: 08
    provides: "schema-open identity adoption and the shared FLOAT[n] read the CLI width guard now delegates to"
  - phase: 21-scale-maintenance-embedder-identity
    plan: 04
    provides: "injected-double identity policy precedent (no policy without a real EmbedderIdentity)"
provides:
  - "src/sif/indexing/embed_writer.py - StreamingEmbedWriter, validate_batch, SystemicEmbedError, NORM_TOLERANCE"
  - "Streaming embed_cmd: identity adoption/check, per-document short commit, failure taxonomy, one outside-transaction CR-02 report, D-04 certification"
  - "Watcher _EmbedSession.writer: per-path chunks, vectors, shadow, and identity through the same streaming writer"
affects: [21-06, 21-07, 22, 23, 24]

# Actuals (#2632) - pairs with the plan's `estimate` (88000 tokens, 3 tasks).
actuals:
  tokens: 23458
  tasks: 3
  commits: 3
plan_head_before: 42ca9dfabe38dc6ed9c392a6b6df4be33243af59
plan_head_after: dad4fa770473327734fb71358108858ee46d1759

tech-stack:
  added: []
  patterns:
    - "Streaming writer owns completeness, sanity, shadow maintenance, and the first-write identity in one place"
    - "Embedding compute outside every transaction; one short `with conn:` per document for all derived rows"
    - "Systemic vs document-local failure taxonomy with ONE final report raised outside any transaction"
    - "Identity source=verified only on a fresh index's first commit or a complete unfiltered zero-failure --force"

key-files:
  created:
    - src/sif/indexing/embed_writer.py
    - tests/unit/indexing/test_embed_writer.py
  modified:
    - src/sif/cli/commands/index.py
    - src/sif/indexing/watcher.py
    - tests/unit/cli/test_index.py
    - tests/unit/cli/test_index_locking.py
    - tests/unit/cli/test_watch_cmd.py
    - tests/unit/indexing/test_watcher.py
    - tests/integration/test_embed_idempotency.py

key-decisions:
  - "D-15 refinement: collection stats are recomputed once per collection in a short O(N) joined count instead of per document; a collection that aborts mid-loop keeps its previous counts until its next successful run (the per-document alternative would update them incrementally)."
  - "The writer accepts an optional identity so injected manager doubles keep the inert pre-Phase-21 path; embed_cmd gates identity enforcement on both a real sqlite3.Connection and a real EmbedderIdentity, extending the 21-04 injected-double precedent."
  - "The first successful document commit writes the identity via write_identity(replace(identity, source='verified')) inside the same transaction; final certification is skipped when a writer already wrote and runs vacuously on an empty full --force index."
  - "Failure taxonomy: locked/busy OperationalError and SystemicEmbedError abort after prior commits; every other exception is document-local and the run continues, with the single report raised outside any transaction."
  - "validate_batch uses stdlib math only (count, dimension, finiteness, L2 norm) so no dependency is added; unit-norm test vectors replace the previous non-normalized fakes."
  - "The watcher builds the writer after its existing identity adoption and computes had_vectors once, keeping trigger/debounce/depth and the pending-retry/fail-soft semantics unchanged."

patterns-established:
  - "One shared writer is the only place chunk/embed/persist semantics live; hosts own selection and failure policy"
  - "A garbage batch persists nothing and aborts systemically; a bad document never rolls back a prior document's commit"
  - "The CLI width guard and the identity check share schema_embedding_dim and the identity module, never an inline regex"

requirements-completed: [SCALE-03, EMB-01, EMB-02]

coverage:
  - id: D1
    description: "One document is chunked and embedded outside any transaction, then persisted in exactly one short transaction carrying chunks, vectors, the shadow row, and (on an empty index) the identity"
    requirement: SCALE-03
    verification:
      - kind: unit
        ref: "tests/unit/indexing/test_embed_writer.py#test_batches_run_outside_the_transaction_and_commit_once"
        status: pass
    human_judgment: false
  - id: D2
    description: "A fresh index's first commit certifies the identity as source=verified; a populated index keeps its stored identity; a stale zero-vector identity is overwritten by the first commit (D-02)"
    requirement: EMB-01
    verification:
      - kind: unit
        ref: "tests/unit/indexing/test_embed_writer.py#test_first_vector_write_certifies_the_identity,test_populated_index_keeps_the_stored_identity; tests/unit/cli/test_index.py#TestStreamingEmbed.test_stale_identity_on_empty_index_is_overwritten_by_first_commit"
        status: pass
    human_judgment: false
  - id: D3
    description: "All six garbage classes (count, dimension, NaN, Inf, unit-norm violation, zero norm) raise SystemicEmbedError and persist no chunk, vector, shadow, or identity row, naming the identity, document, batch, position, and chunk"
    requirement: SCALE-03
    verification:
      - kind: unit
        ref: "tests/unit/indexing/test_embed_writer.py#test_garbage_batch_sanity_aborts_and_persists_nothing,test_garbage_sanity_after_a_committed_document_leaves_it_intact"
        status: pass
    human_judgment: false
  - id: D4
    description: "A mid-run failure leaves earlier documents committed and a re-run embeds exactly the remainder; the report is raised outside any transaction with a non-zero exit"
    requirement: SCALE-03
    verification:
      - kind: integration
        ref: "tests/integration/test_embed_idempotency.py#TestStreamingFailureDurability; tests/unit/cli/test_index.py#TestStreamingEmbed.test_per_document_commit_survives_a_later_failure_and_resumes"
        status: pass
    human_judgment: false
  - id: D5
    description: "source=verified is written only by a fresh index's first commit or a complete unfiltered zero-failure --force; a scoped --force, a normal run, or any failure keeps legacy-assumed; vacuous certification is replaced by the next embedder's first write"
    requirement: EMB-01
    verification:
      - kind: integration
        ref: "tests/integration/test_embed_idempotency.py#TestIdentityCertification; tests/unit/cli/test_index.py#TestStreamingEmbed.test_vacuous_full_force_certification_is_replaced_by_the_first_write"
        status: pass
    human_judgment: false
  - id: D6
    description: "The watcher embeds every path through the same writer, writes the shadow in the same transaction, and a SystemicEmbedError emits one error event, disables embedding for the session, and stops the loop while BM25 freshness continues"
    requirement: SCALE-03
    verification:
      - kind: unit
        ref: "tests/unit/indexing/test_watcher.py#TestEmbedDepth.test_burst_writes_chunks_vectors_and_shadow_in_one_writer_transaction,test_systemic_sanity_failure_disables_embed_for_the_session"
        status: pass
    human_judgment: false
  - id: D7
    description: "Full quality suite stays green with the configured coverage floor and no new runtime dependency"
    requirement: SCALE-03
    verification:
      - kind: other
        ref: "env -u FORCE_COLOR NO_COLOR=1 pytest (2692 passed, 1 skipped, 95.22%); ruff check; ruff format --check; ty check src/sif (one pre-existing bench.py diagnostic)"
        status: pass
    human_judgment: false

duration: 10min
completed: 2026-11-16
status: complete
---

# Phase 21 Plan 05: Streaming Embed, Batch Sanity, and Identity Certification

**`StreamingEmbedWriter` replaces the per-collection giant embed transaction: chunk+embed outside every transaction in bounded batches, validate count/dimension/finiteness/norm, then commit one short per-document transaction carrying chunks, vectors, shadow, stats, and the first-write identity; `embed_cmd` and the watcher both route through it.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-11-15T17:23:06Z
- **Completed:** 2026-11-15T17:33:15Z (2026-11-16 local)
- **Tasks:** 3
- **Files modified:** 9 (2 created, 7 modified)
- **Commits:** 3 task commits

## Accomplishments

- `src/sif/indexing/embed_writer.py` is the single streaming pipeline: `_chunk_document` filters empty text and renumbers contiguously, batches by `settings.batch_size`, embeds through `manager.embed_documents` with no transaction open, validates each batch, and persists one document's chunks + `add_embeddings_batch` vectors + shadow row + optional identity in exactly one `with conn:` block.
- `validate_batch` (D-17) rejects wrong count, wrong dimension, NaN/Inf, non-unit norm when normalized (tolerance 1e-3), and zero norm when not normalized; `SystemicEmbedError` names the identity fingerprint, document path, batch index, position, and chunk id/sequence.
- `embed_cmd` delegates the `FLOAT[n]` width guard to the shared `schema_embedding_dim` (pre-change ClickException wording preserved) and adopts the identity before any vector write: legacy indexes are assumed once; a same-width swap fails fast; an embeddings-empty index accepts any embedder (D-02).
- `embed_cmd`'s failure taxonomy is D-16 exact: locked/busy SQLite and `SystemicEmbedError` abort after prior commits; every other exception is a document-local `(collection, path, error)` record and the run continues. ONE final report is raised outside any transaction and exits non-zero.
- Certification is gated on `--force` AND no collection filter AND zero failed documents/collections and no writer-written identity; an empty index certifies vacuously, which D-02 lets the next embedder's first write replace.
- `_EmbedSession.ensure_ready` builds the writer after its existing identity adoption; `embed_documents` routes each path through `writer.embed_document`, preserving the pending-retry union, the one-error-event local failure, and the LIVE-05 fail-soft contract. A systemic sanity failure emits one error, sets `_ready = False`, and stops the loop with earlier paths committed.
- Tests migrated from collection-wide `manager.embed` to per-document `manager.embed_documents`, with fake vectors normalized to unit L2 so the new sanity boundary is exercised rather than bypassed.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end streaming embed - one document outside any transaction, one short commit** - `5d94231` (feat)
2. **Task 2: Batch-boundary sanity, failure taxonomy, CR-02 report, and identity certification** - `2d4013b` (feat; pins the production code that landed with the Task 1 loop rewrite)
3. **Task 3: Route the watcher through the shared writer and migrate watcher call-shape tests** - `dad4fa7` (feat)

**Plan metadata:** the final docs commit captures this SUMMARY plus STATE/ROADMAP/REQUIREMENTS updates.

## Files Created/Modified

- `src/sif/indexing/embed_writer.py` (new) - `StreamingEmbedWriter`, `validate_batch`, `SystemicEmbedError`, `NORM_TOLERANCE`, whitespace filtering/renumbering, one-transaction persistence.
- `src/sif/cli/commands/index.py` - shared `schema_embedding_dim` width guard, `_resolve_identity`/`_index_has_vectors`/`_count_collection_chunks`/`_EmbedAbortError`, streaming per-collection loop, stderr document-failure report, certification gate.
- `src/sif/indexing/watcher.py` - `_EmbedSession.writer` construction in `ensure_ready`; `embed_documents` delegates to `writer.embed_document`; `SystemicEmbedError` disables the session after one error event.
- `tests/unit/indexing/test_embed_writer.py` (new) - transaction-boundary, identity-write, idempotency, whitespace, and six-class garbage battery.
- `tests/unit/cli/test_index.py` - `embed_documents` call-shape migration, per-document commit/resume and D-02 stale-identity tests, vacuous-certification reset.
- `tests/unit/cli/test_index_locking.py` - manager mock migrated to `embed_documents` (collateral; see deviations).
- `tests/unit/cli/test_watch_cmd.py` - `embed_documents` call shape and unit-norm fake vectors.
- `tests/unit/indexing/test_watcher.py` - unit-norm `embed_documents` mocks, shadow-row and systemic-session-disable contracts.
- `tests/integration/test_embed_idempotency.py` - `embed_documents`/unit-vector migration, mid-run durability/resume, certification matrix, legacy-vector seeding.

## Decisions Made

- **D-15 refinement (as required):** collection stats are recomputed once per collection in one `COUNT(*) ... JOIN documents` statement inside a short transaction. This preserves the committed stats output while a collection that aborts mid-loop keeps its previous counts until the next successful run; the per-document alternative would update counts incrementally.
- **Identity enforcement is host-gated, not writer-gated.** `embed_cmd` runs the identity check only when the connection is a real `sqlite3.Connection` and the manager returns a real `EmbedderIdentity`, extending the 21-04 precedent for injected doubles. Production always satisfies both; test hosts with patched `Database`/`MagicMock` managers stay inert instead of crashing inside `schema_embedding_dim`.
- **The writer treats `identity=None` as "no policy" only for those doubles.** A real host always hands over a real identity, so batch sanity and identity writes are never skipped in production.
- **First write vs final certification.** The first document commit writes `replace(identity, source="verified")` inside its own transaction. Final certification is skipped when a writer already wrote (no second identity row) and still runs vacuously for an empty full `--force` index, matching D-02's accept-any-embedder rule while zero vectors exist.
- **Failure classification follows the plan action verbatim:** locked/busy + `SystemicEmbedError` abort; all other exceptions are document-local. A backend failure therefore reports one document per attempted document and exits non-zero, while prior documents stay durable.
- **Sanity uses stdlib `math` only** so `pyproject.toml`/`uv.lock` are untouched (prohibition 5). Test fixtures now emit unit vectors instead of the previous non-normalized `[0.1] * dim` fakes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Migrated `tests/unit/cli/test_index_locking.py` to `embed_documents`**
- **Found during:** Task 1 (embed_cmd rewrite)
- **Issue:** The lock test's manager mock configured only `manager.embed`; the streaming command now calls `manager.embed_documents`, so the mock returned an empty batch and the command exited non-zero.
- **Fix:** Pointed the mock's `embed_documents.side_effect` at the existing deterministic vector factory.
- **Files modified:** `tests/unit/cli/test_index_locking.py`
- **Verification:** 5/5 lock tests pass.
- **Committed in:** `5d94231` (Task 1 commit)

**2. [Rule 3 - Blocking] Unit-normalized the fake manager vectors in watcher/integration tests**
- **Found during:** Task 1/Task 3 (writer validation)
- **Issue:** Watcher and integration fakes returned `[0.1] * dim` or `[0, 1, 0.5, ...]` vectors, which the new D-17 unit-norm check (identity.normalized=True) correctly rejects as systemic garbage.
- **Fix:** Fake managers now return `1/sqrt(dim)` components or divide their constructed vector by its L2 norm; call counts migrated to `embed_documents`.
- **Files modified:** `tests/unit/indexing/test_watcher.py`, `tests/unit/cli/test_watch_cmd.py`, `tests/integration/test_embed_idempotency.py`
- **Verification:** 56 watcher, 39 watch-CLI, and 13 integration tests pass.
- **Committed in:** `2d4013b` (integration) and `dad4fa7` (watcher)

**3. [Rule 3 - Blocking] Gated identity enforcement on a real connection + real identity**
- **Found during:** Task 1 (embed_cmd rewrite)
- **Issue:** Existing CLI unit tests patch `Database` with a `MagicMock`, so `schema_embedding_dim(MagicMock)` and `ensure_legacy_identity(MagicMock, MagicMock)` would raise unrelated `TypeError`s and break the pre-existing surface.
- **Fix:** Added `_resolve_identity`, which returns `None` unless both the connection and the manager's identity are real; the width guard likewise reads the schema only from a real connection. This mirrors the 21-04 "injected doubles have no identity policy" decision.
- **Files modified:** `src/sif/cli/commands/index.py`
- **Verification:** All migrated CLI tests and the full suite pass; real-DB identity tests exercise the enforced path.
- **Committed in:** `5d94231` (Task 1 commit)

**4. [Commit shape] Task 2 production code landed with Task 1's loop rewrite**
- **Found during:** Task 1
- **Issue:** The per-document loop cannot be expressed without the failure taxonomy and certification gate, so `validate_batch`, `SystemicEmbedError`, the abort/local split, and `certify_identity` were implemented alongside the streaming loop.
- **Fix:** Task 2's commit adds the pinning tests (garbage battery, durability/resume, certification matrix, vacuous reset) rather than duplicating the production diff.
- **Files modified:** tests only in `2d4013b`
- **Verification:** Every Task 2 acceptance criterion has a passing test; full suite green.

---

**Total deviations:** 3 auto-fixed (3 blocking) + 1 commit-shape note
**Impact on plan:** No production scope beyond the plan; the extra test file and fixture normalization are direct consequences of the streaming rewrite and the new sanity boundary.

## Issues Encountered

- `ty check src/sif` reports one diagnostic at `src/sif/cli/commands/bench.py:112` (`Embedder` has no `embed_query`) that exists at HEAD under the installed ty 0.0.97. `git diff 42ca9df..HEAD -- src/sif/cli/commands/bench.py` is empty, so this plan introduced no new ty diagnostic; the plan's `ty` gate cannot be fully green until that pre-existing item is fixed. No package installs, no schema changes, no new dependency.

## User Setup Required

None - no external service configuration required. No runtime dependency was added (`pyproject.toml`/`uv.lock` untouched).

## Verification

- Targeted: `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/indexing/test_embed_writer.py tests/unit/cli/test_index.py tests/unit/indexing/test_watcher.py tests/unit/cli/test_watch_cmd.py tests/integration/test_embed_idempotency.py -x --no-cov` - 137 passed.
- Full suite: `env -u FORCE_COLOR NO_COLOR=1 pytest` - **2692 passed, 1 skipped**, coverage **95.22%** (fail_under=90).
- `ruff check src tests` clean; `ruff format --check src tests` - 216 files already formatted.
- Grep gates: `StreamingEmbedWriter` in `index.py` = 2, `StreamingEmbedWriter` in `watcher.py` = 3, `in_transaction` in the writer tests = 2, `SystemicEmbedError` in `embed_writer.py` = 7.
- Prohibitions:
  - Embedding outside transactions: every fake-manager call records `conn.in_transaction is False`; exactly one BEGIN/COMMIT pair per document (trace callback count).
  - Garbage never persisted: all six classes leave no chunk, vector, shadow, or identity row.
  - No partial/scoped certification: scoped `--force` and any failure keep `legacy-assumed`; only a complete unfiltered zero-failure `--force` or a fresh index's first write yields `verified`.
  - Watcher semantics: trigger/debounce/depth untouched; 56 watcher tests include the error-event/pending-retry contracts.
  - No dependency: `git diff --stat 42ca9df..HEAD -- pyproject.toml uv.lock` is empty; `grep -rn "manager.embed(" src/sif/cli/commands/index.py src/sif/indexing/watcher.py` exits 1.

## Known Stubs

None.

## Threat Flags

None - no new network endpoint, auth path, file-access pattern, or trust-boundary surface. The plan's mitigations (T-21-15 batch validation, T-21-16 bounded writes, T-21-17 certification gating) are the contracts proven above.

## Next Phase Readiness

- `sif index embed` and the watcher now share one writer; 21-06's vacuum/backup work is independent of this path, and 21-07's byte-identical/legacy gate can rely on the per-document commit contract.
- Phase 24's per-arm re-embed can reuse `StreamingEmbedWriter` directly.
- Residual accepted risk (T-21-18): a whitespace-only document is retried on every explicit run; harmless and bounded by user runs. The D-17 checks are structural, not semantic (the plan's accepted floor).

## Self-Check: PASSED

- FOUND: src/sif/indexing/embed_writer.py
- FOUND: tests/unit/indexing/test_embed_writer.py
- FOUND: 5d94231
- FOUND: 2d4013b
- FOUND: dad4fa7

---
*Phase: 21-scale-maintenance-embedder-identity*
*Completed: 2026-11-16*
