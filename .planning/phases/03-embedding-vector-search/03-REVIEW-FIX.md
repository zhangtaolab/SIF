---
phase: 03-embedding-vector-search
fixed_at: 2026-09-04T13:12:00Z
review_path: .planning/phases/03-embedding-vector-search/03-REVIEW.md
iteration: 1
findings_in_scope: 10
fixed: 10
skipped: 0
status: all_fixed
---

# Phase 3: Code Review Fix Report

**Fixed at:** 2026-09-04T13:12:00Z
**Source review:** .planning/phases/03-embedding-vector-search/03-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 10 (2 Critical + 8 Warning; Info findings out of scope per fix_scope)
- Fixed: 10
- Skipped: 0

**Verification (where it ran):** all gates ran inside the isolated review-fix
worktree (`.claude/worktrees/rf-03-52365-1788523423`, branch
`gsd-reviewfix/03-52365`), with `PYTHONPATH` pinned to the worktree's `src/`
because the editable install resolves `sif` to the main checkout. Full suite:
`python -m pytest -q` -> **572 passed, 11 skipped** (baseline before this
round: 554 passed, 11 skipped; +18 new tests). `ruff check src tests` and
`ruff format --check src tests`: clean. `mypy` on the modified files fails
inside third-party `sentence_transformers` (site-packages, Python-version
mismatch) — reproduced identically on the pre-fix main checkout, i.e.
pre-existing and untouched by these fixes.

## Fixed Issues

### CR-01: Content changes never propagate — stale chunks and stale vectors with no invalidation path

**Files modified:** `src/sif/cli/commands/index.py`, `src/sif/database/schema.py`,
`tests/unit/database/test_schema.py`, `tests/integration/test_embed_idempotency.py`
**Commit:** 3d307da
**Applied fix:** Two-part fix, per the verifier's authorized minimal-correct path.

1. `update_cmd` now invalidates chunk/embedding state when a document's
   content changes (or `--force` re-indexes): `chunk_repo.delete_by_document()`
   plus `vector_searcher.delete_embeddings_by_document()` via a new
   `_embedding_purger()` helper (returns None when sqlite-vec is absent, which
   also means no vec0 table — nothing to purge). The next `embed` run then
   sees an empty live chunk set and re-chunks/re-embeds the new content
   instead of skipping it forever.
2. Fixed the pre-existing FND-06 trigger bug that blocks the same edit loop:
   `documents_fts_update` (and the identical `chunks_fts_update` pattern)
   direct-UPDATEd an external-content FTS5 table, which crashes with
   `database disk image is malformed` on medium+ content edits (reproduced
   before fixing; `doc_repo.update()` fires this trigger for every content
   edit). Both triggers now use the documented `'delete'`-command + INSERT
   pattern, and `create_all()` migrates legacy triggers by detecting the
   direct-UPDATE form in `sqlite_master` and dropping/recreating them.

**Decision documented:** without the trigger fix, any medium+ content edit
crashes inside `update_cmd` — CR-01's edit -> update -> embed loop could not
work end-to-end — so the trigger fix was included in CR-01 rather than
deferred. Residual limitation (accepted): documents edited *before* this fix
(row already updated, chunks stale, embed already skipped them once) stay
stale until their next edit or `--force`; invalidation happens at update
time, and embedding state is not versioned by checksum.

**Tests:** 4 new schema tests (medium-update keeps FTS in sync + integrity ok
for both triggers, legacy-trigger migration, no-churn for migrated triggers)
— these use a plain in-memory connection (FTS5 is core SQLite) because the
existing `vec_db` fixture's `load_extension("vec0")` mechanism never loads in
this environment and would have skipped them everywhere. 1 new end-to-end
integration test: edit note -> `update` -> `embed` (no --force) -> fresh chunk
text in `document_chunks`/`chunks_fts`/`documents_fts`, fresh embedding ids,
second embed batch actually runs (fails on the old code by skipping instead).

### CR-02: embed_cmd per-collection failure handling defeated by its own transaction

**Files modified:** `src/sif/cli/commands/index.py`, `tests/integration/test_embed_idempotency.py`
**Commit:** 44425c8
**Applied fix:** Removed the whole-run `with db.connection:` wrapper and made
the transaction per collection (reviewer's option A): each collection's
chunk/persist/stats work commits in its own `with db.connection:` block inside
a try/except; a failed collection rolls back only itself and is recorded in
`failed_collections`; the final `ClickException` is raised *outside any
transaction* after the success print. `total_chunks` is now incremented only
after a collection's transaction commits, so the "Embedding complete" line
never reports rolled-back work. The `VectorSearcher`-construction
`ClickException` is likewise raised outside any open transaction.
**Tests:** new integration test on a real DB: collection `a-good` embeds,
collection `b-bad`'s backend call fails -> command exits non-zero naming
`b-bad`, yet `a-good`'s chunks and embeddings are persisted (asserted by
re-opening the DB) — fails on the old code, which rolled everything back.

### WR-01: Deleting a document orphans its vec0 rows

**Files modified:** `src/sif/cli/commands/index.py`, `tests/integration/test_embed_idempotency.py`
**Commit:** bec80ec
**Applied fix:** The removal loop in `update_cmd` now purges embeddings
(via the CR-01 `_embedding_purger`) before `doc_repo.delete()`, so vanished
files no longer leave orphan vectors occupying KNN top-k slots.
The longer-term suggestion (purge inside `DocumentRepository.delete` for every
caller) was not taken — repository layer has no VectorSearcher dependency
today and the finding's minimal fix covers the orphan-manufacturing path.
**Tests:** new integration test: embed a real file, unlink it, `update` ->
`Removed: 1`, and both `document_chunks` and `document_embeddings` counts are
0 (old code left embeddings > 0).

### WR-02: Model dimension never validated against the schema for local backends

**Files modified:** `src/sif/cli/commands/index.py`, `tests/integration/test_embed_idempotency.py`
**Commit:** 5391438
**Applied fix:** After computing `embedding_dim` from the eagerly-loaded
model, `embed_cmd` reads the vec0 table's declared `FLOAT[n]` from
`sqlite_master` and fails fast with a remediation message ("Set
SIF_EMBEDDING_DIM to the model's dimension and rebuild") before any chunks
are written. Skips cleanly when the table is absent (no sqlite-vec).
**Tests:** new integration test: FLOAT[8] schema + manager reporting dim 4 ->
exit non-zero with "produces 4-dim embeddings but the index stores 8-dim
vectors", and zero chunks/embeddings written.

### WR-03: `k = {options.limit}` interpolates a query parameter into SQL text

**Files modified:** `src/sif/search/vector.py`, `tests/unit/search/test_vector.py`
**Commit:** 0978de5
**Applied fix:** The KNN limit is now bound (`k = ?`) with `max(1,
options.limit)` clamping, positioned in the params list between the embedding
and the collection ids to match SQL order. Verified against real sqlite-vec
that `k = ?` positional binding works. The reviewer's optional CLI
`min=1`/Field-ge validation was NOT added: `SearchOptions` is a plain shared
dataclass (CLI, MCP, pipeline) and the single clamp at the only SQL sink
covers every entry point; adding validation in one or two of them would
leave the others inconsistent.
**Tests:** k is bound not interpolated; non-positive limit clamps (fetch
floor + trim to 1 row).

### WR-04: Collection filter applied after the KNN k-limit — filtered searches under-return

**Files modified:** `src/sif/search/vector.py`, `tests/unit/search/test_vector.py`
**Commit:** a8b0943
**Applied fix:** Over-fetch then trim, as suggested: `fetch_k = max(limit *
4, 50)` bounded surplus into the vec0 MATCH, collection filter and min_score
applied on the joined rows (still `ORDER BY distance`), then trim to
`max(1, options.limit)` and assign ranks sequentially after the cut (also
fixes the IN-03 rank-gap issue as a side effect). Ordering semantics
preserved: score is monotone in distance, so unfiltered searches return the
same rows in the same order as before; `add_embeddings_batch` insert
semantics untouched per the 03-08 constraint. Fixed a `None` unpack bug
caught during verification (`*options.collection_ids` when the field is
None).
**Tests:** two real-vec0 tests — collection-filtered search returns matches
sitting at global ranks 4-5 (a tight k=2 returned nothing before), and
unfiltered search keeps exact top-limit ordering/ranks.

### WR-05: Invalid `--chunk-strategy` crashes with a raw traceback

**Files modified:** `src/sif/cli/commands/index.py`, `tests/unit/cli/test_index.py`
**Commit:** bda12a2
**Applied fix:** `--chunk-strategy` is now `click.Choice(["auto", "fixed",
"markdown", "code"])` (the closed set `create_chunker` accepts), so a bad
value is a usage error (exit 2) instead of a `ValueError` traceback.
**Tests:** `--chunk-strategy smrt` -> exit code 2 with "Invalid value".

### WR-06: `pre_update_cmd` runs with no timeout — a hung command hangs the CLI forever

**Files modified:** `src/sif/cli/commands/index.py`, `tests/unit/cli/test_collection.py`
**Commit:** 14c3986
**Applied fix:** `subprocess.run` now passes `timeout=300` (module constant
`_PRE_UPDATE_TIMEOUT_SECONDS` — the reviewer's suggested
`coll.pre_update_timeout` field does not exist on `Collection`, so a shared
constant is used until such a setting exists) and
`stdin=subprocess.DEVNULL`; `subprocess.TimeoutExpired` maps to a
`ClickException` alongside the existing returncode branch.
**Tests:** existing kwargs assertion updated to the new contract
(timeout/stdin); new test: `TimeoutExpired` -> non-zero exit with "timed out
after 300s".

### WR-07: `huggingface` advertised as valid `model_type` but every path dead-ends

**Files modified:** `src/sif/config/settings.py`, `tests/unit/config/test_settings.py`,
`docs/configuration.md`
**Commit:** 60a2c08
**Applied fix:** Removed `"huggingface"` from the Settings validator's valid
set (and from the field description) so `SIF_MODEL_TYPE=huggingface` fails at
validation time with the immediate error; `ModelType.HUGGINGFACE` enum member
and the factory's `NotImplementedError` branch are kept for internal use, per
the reviewer's preferred option. `docs/configuration.md`'s row documenting
the validator was updated to match (it listed the accepted set verbatim).
**Tests:** new rejection test for `model_type="huggingface"`; the 4-backend
accept test already existed.

### WR-08: `SIF_N_GPU_LAYERS` plumbed to the factory and silently dropped

**Files modified:** `src/sif/embedding/embedder.py`, `src/sif/embedding/factory.py`,
`tests/unit/embedding/test_embedder_impl.py`, `tests/unit/embedding/test_factory.py`
**Commit:** 733c7a1
**Applied fix:** `LlamaCppEmbedder.__init__` gains `n_gpu_layers: int = 0`
(forwarded to the `Llama(...)` constructor), and `_create_gguf_model` passes
`n_gpu_layers=kwargs.get("n_gpu_layers", 0)` so the settings value reaches the
backend instead of silently no-oping into CPU inference.
**Tests:** embedder forwards `n_gpu_layers=7` to `Llama` and defaults to an
explicit 0; factory dispatch forwards the kwarg end-to-end.

## Skipped Issues

None — all 10 in-scope findings were fixed. The 10 Info findings (IN-01
through IN-10) are out of scope for this round per `fix_scope:
critical_warning`.

**Human-verification note (per fixer policy):** CR-01 and CR-02 change
transaction and index-lifecycle behavior, not just syntax. Both carry
real-database regression tests that fail on the pre-fix code (edit-loop
staleness, medium-edit FTS corruption, cross-collection rollback), but the
behavioral deltas worth a human eyeball are: (a) `sif index update` now
deletes chunks/embeddings of changed documents inside its transaction — a
crash between `update` and `embed` leaves the document un-embedded (self-heals
on the next `embed`), and (b) `sif index embed` now commits per collection,
so a partially failed run is a partially embedded index by design (matching
the 03-08 continue-on-error model) rather than all-or-nothing.

---

_Fixed: 2026-09-04T13:12:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
