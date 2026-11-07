---
phase: 03-embedding-vector-search
reviewed: 2026-09-04T11:39:13Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - pyproject.toml
  - src/sif/cli/commands/index.py
  - src/sif/embedding/embedder.py
  - src/sif/embedding/factory.py
  - src/sif/search/vector.py
  - tests/integration/test_embed_idempotency.py
  - tests/integration/test_search_pipeline.py
  - tests/unit/cli/test_index.py
  - tests/unit/config/test_settings.py
  - tests/unit/embedding/test_factory.py
  - tests/unit/embedding/test_manager.py
  - tests/unit/embedding/test_openai_embedder.py
  - tests/unit/search/test_bm25.py
  - tests/unit/search/test_hybrid.py
  - tests/unit/search/test_vector.py
findings:
  critical: 2
  warning: 8
  info: 10
  total: 20
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-09-04T11:39:13Z
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

Re-review after the 03-07 (OpenAIEmbedder / dimension detection) and 03-08
(G-03-3 idempotent embed) plans and the prior review-fix round. The prior
round's fixes (cache segmentation, FTS sanitization, response reordering,
endpoint-keyed dim cache, fail-fast load errors) verify as implemented and
well-tested; `tests/integration/test_embed_idempotency.py` is genuinely
strong — real sqlite-vec, real DB, exact chunk-id-set invariants.

However, the new skip-or-embed logic interacts badly with the rest of the
index lifecycle. Two blockers remain: (1) `sif index update` never
invalidates chunks/embeddings when a document's content changes, and the new
"Already embedded" completeness check then skips those documents forever, so
edited notes silently serve stale chunk text and stale vectors without
`--force`; (2) `embed_cmd`'s per-collection failure handling is defeated by
its own transaction scope — the final `ClickException` is raised inside
`with db.connection:`, rolling back every successful collection's work after
the CLI has already printed "Embedding complete". Additional warnings cover
orphaned vec0 rows from file deletion, an unvalidated model-vs-schema
dimension path for local backends, SQL string interpolation of `k`, a
KNN-vs-collection-filter recall defect, an uncaught `ValueError` on a bad
`--chunk-strategy`, a hang-prone `subprocess.run` without timeout, the
phantom `huggingface` backend, and the silently dropped `n_gpu_layers`
setting.

## Critical Issues

### CR-01: Content changes never propagate — `index update` + `index embed` leaves stale chunks and stale vectors with no invalidation path

**File:** `src/sif/cli/commands/index.py:127-140` (update branch), `src/sif/cli/commands/index.py:175-182` (`_needs_embedding`), `src/sif/cli/commands/index.py:277-284` (skip branch)
**Issue:** `update_cmd` updates a changed document's row (`doc_repo.update(existing)`) but never touches `document_chunks` or `document_embeddings`. The new idempotency check then decides freshness purely from chunk-id-set equality:

```python
if not _needs_embedding({c.id for c in existing}, embedded, force):
    console.print(f"  [dim]Already embedded: {doc.path}[/dim]")
    continue
```

After a content edit, the live chunk ids and the embedded chunk ids are both
the *old* set (update_cmd never re-chunked), so they match exactly and the
document is skipped on every default run. Result: edited documents keep stale
`chunks_fts` rows (BM25 chunk search serves old text) and stale vectors
(vector/hybrid search matches old content) indefinitely. Only a full
`--force` (re-embeds *everything*, all collections) escapes the trap. The
skip heuristic has no input that can observe the content change — the
document's new checksum is never consulted. The update-side logic predates
this phase, but the 03-08 completeness check is what makes the staleness
silent and permanent-looking, and this is the product's core loop
(edit note → update → embed → search).
**Fix:** Invalidate chunk/embedding state when the checksum changes. Minimal
version in `update_cmd`'s changed-document branch:

```python
if existing.checksum == parsed.checksum and not force:
    ...
# content changed: drop chunks + embeddings so embed_cmd re-chunks
chunk_repo.delete_by_document(existing.id)
vector_searcher.delete_embeddings_by_document(existing.id)
doc_repo.update(existing)
```

(or, equivalently, record the indexed checksum per chunk set and include
`existing.checksum != doc.checksum` in `_needs_embedding`). Add a regression
test: update content → run `embed` (no force) → assert new chunk text and
fresh embedding ids.

### CR-02: `embed_cmd` per-collection failure handling is defeated by its own transaction — the final raise rolls back all successful collections after printing success

**File:** `src/sif/cli/commands/index.py:236` (`with db.connection:`), `src/sif/cli/commands/index.py:313-328`, `src/sif/cli/commands/index.py:268-271`
**Issue:** The whole run executes inside one `with db.connection:` block.
Per-collection embedding errors are caught (line 313), the loop continues,
successful collections' chunks/vectors accumulate — then line 324-328 raises
`click.ClickException` *inside the with-block* because `failed_collections`
is non-empty. The sqlite3 connection context manager rolls back on exception,
so **every successful collection's work from this run is discarded**, after
the CLI already printed `Embedding complete: {total_chunks} chunks embedded`
(line 322) for it. The `VectorSearcher`-construction `ClickException`
(line 271) has the same effect. Consequences: (a) output claims embeddings
were stored that were rolled back; (b) for the OpenAI backend each retry
re-bills the full successful API spend — with one persistently failing
collection the user pays for everything on every run and retains nothing;
(c) the code's own per-collection error model (`failed_collections`,
continue-on-error, 03-08-PLAN's "a caught per-collection failure leaves
deleted-but-not-reinserted documents … to re-embed next run") is
contradicted — instead the DB is reset to the pre-run state. The self-heal
check tolerates the rollback, so nothing corrupts, but the behavior is
incorrect and costly.
**Fix:** Decide one model and make the transaction match it. For per-collection
success persistence, raise after commit and commit per collection:

```python
for coll in collections:
    ...
    try:
        with db.connection:  # one transaction per collection
            ...chunk, embed, persist...
    except Exception as e:
        console.print(f"  [red]Error embedding collection {coll.name}: {e}[/red]")
        failed_collections.append(coll.name)
        continue
...
if failed_collections:
    raise click.ClickException(...)  # outside any db transaction
```

If all-or-nothing is the intended D-10 semantics instead, drop the
"Embedding complete" print when `failed_collections` is non-empty and stop
embedding further collections after the first failure.

## Warnings

### WR-01: Deleting a document orphans its vec0 rows — orphans consume KNN top-k slots and silently degrade vector search

**File:** `src/sif/cli/commands/index.py:156-160` (removal loop); root cause `src/sif/database/repositories.py:223-231` (`DocumentRepository.delete` deletes chunks but not `document_embeddings`)
**Issue:** `update_cmd` removes documents whose files vanished via
`doc_repo.delete(doc.id)`. That deletes `document_chunks` but never
`document_embeddings` (the vec0 virtual table cannot carry the FK cascade).
In `_search_with_vec` the KNN constraint `k = {options.limit}` is resolved
*inside* the vec0 MATCH, before the `JOIN documents` filters orphans out —
so orphaned vectors occupy top-k slots and crowd live documents out of the
result set. This is exactly the T-03-08-01 orphan-pollution threat the phase
set out to close; the re-embed path was fixed, but the file-removal path
still manufactures orphans. They persist until the user happens to run
`sif cleanup` manually.
**Fix:** In the removal loop, delete embeddings alongside the document:

```python
from sif.search.vector import VectorSearcher  # noqa: PLC0415

vector_searcher = VectorSearcher(db.connection, ...)
for path, doc in existing_docs.items():
    if path not in scanned_paths:
        vector_searcher.delete_embeddings_by_document(doc.id)
        doc_repo.delete(doc.id)
        total_removed += 1
```

(Longer term, put the embedding purge inside `DocumentRepository.delete` so
every caller gets it.)

### WR-02: Model dimension is never validated against the schema for local backends — dimension-changing `--model` overrides fail mid-insert with a raw sqlite-vec error

**File:** `src/sif/cli/commands/index.py:207-234`; `src/sif/embedding/factory.py:58-68, 93-103`
**Issue:** `db.init_schema()` creates/validates the vec0 table against the
*global* settings dim (`SIF_EMBEDDING_DIM`, default 1024) *before* any CLI
override is applied. `embed_cmd` then discovers the *model's* actual dim
(line 233-234) and hands it to `VectorSearcher` — whose `embedding_dim`
parameter is never used (see IN-02). Only the OpenAI backend cross-checks
model dim vs settings dim (nice fail-fast message); `_create_sentence_transformers_model`,
`_create_modelscope_model`, and `_create_gguf_model` all **drop** the
`embedding_dim` kwarg the manager passes. So `sif index embed --model <local
model with dim != SIF_EMBEDDING_DIM>` proceeds all the way to
`add_embeddings_batch`, where `vec_f32(?)` fails with a raw sqlite-vec
dimension error — caught by the blanket except, reported as "Error embedding
collection …", with chunks already inserted and vectors absent. Every
subsequent run self-heals into the same failure.
**Fix:** After computing `embedding_dim` from the loaded model, compare it to
the table's declared dimension and fail fast with remediation text, e.g. in
`embed_cmd` after line 234:

```python
row = db.connection.execute(
    "SELECT sql FROM sqlite_master WHERE type='table' AND name='document_embeddings'"
).fetchone()
if row and row[0]:
    import re
    m = re.search(r"FLOAT\[(\d+)\]", row[0])
    if m and int(m.group(1)) != embedding_dim:
        raise click.ClickException(
            f"Model '{model or settings.model_name}' produces {embedding_dim}-dim "
            f"embeddings but the index stores {m.group(1)}-dim vectors. "
            "Set SIF_EMBEDDING_DIM to the model's dimension and rebuild."
        )
```

(Or surface it from `SchemaManager`/`VectorSearcher` so every caller gets it.)

### WR-03: `k = {options.limit}` interpolates a query parameter into SQL text; limit is unvalidated at every entry point

**File:** `src/sif/search/vector.py:71`
**Issue:** The KNN limit is formatted into the SQL string while the adjacent
collection filter correctly uses placeholders. `SearchOptions` is a plain
dataclass (no bounds), CLI (`--limit`, `type=int`, no `min=`) and MCP
(`limit: int`, no `ge`) don't bound it either, so `limit <= 0` reaches
sqlite-vec as `k = 0`/`k = -1` and surfaces as a raw `sqlite3.OperationalError`
traceback. Today all entry points type it as int so injection isn't directly
reachable, but this is the one spot in the query built from externally
supplied values that bypasses parameter binding — a defense-in-depth gap the
project's own threat-model discipline (T-03-08-02 test asserts `"d1" not in sql`
for the delete path) argues against keeping.
**Fix:** Bind it: sqlite-vec supports `k = ?`.

```python
sql = f"""
    ...
    WHERE embedding MATCH ? AND k = ? {collection_filter}
    ORDER BY distance
"""
params = [embedding_str, max(1, options.limit), *options.collection_ids]
```

(And add `limit: int = Field(ge=1)`-style validation / click `min=1`.)

### WR-04: Collection filter is applied after the KNN k-limit — filtered vector searches under-return even when the collection has enough matches

**File:** `src/sif/search/vector.py:56-73`
**Issue:** `AND d.collection_id IN (...)` constrains the *joined* table, but
`k = {options.limit}` bounds the vec0 MATCH itself: sqlite-vec returns the k
globally-nearest rows first, the join/filter then discards those belonging to
other collections. With several collections indexed, `sif search --collection
X` can legitimately return fewer than `limit` (or nothing) while collection X
holds `limit`+ strong matches — a silent recall defect, not an error. Same
mechanism as WR-01's orphans (post-KNN filtering).
**Fix:** Over-fetch then trim, e.g. `k = max(options.limit * 4, 50)` (bounded),
filter by collection, sort by distance, cut to `options.limit`, and compute
ranks after the cut (also fixes IN-03). Document the limitation if over-fetch
is deemed too costly.

### WR-05: Invalid `--chunk-strategy` crashes with a raw traceback instead of a ClickException

**File:** `src/sif/cli/commands/index.py:188, 264` (`create_chunker(chunk_strategy)` outside any try/except; `src/sif/indexing/chunker.py:226` raises `ValueError`)
**Issue:** `--chunk-strategy` is a free-form string defaulting to `"auto"`.
`create_chunker` raises `ValueError("Unknown chunking strategy: …")` and the
call site is not wrapped, so `sif index embed --chunk-strategy smrt` dumps a
Python traceback. This violates the project convention ("CLI commands raise
`click.ClickException(str(e))` for user-facing errors") and is trivially
avoidable since the valid set is closed.
**Fix:** Use Click's choice validation and let the error be a usage message:

```python
@click.option(
    "--chunk-strategy",
    type=click.Choice(["auto", "fixed", "markdown", "code"]),
    default="auto",
    help="Chunking strategy",
)
```

### WR-06: `pre_update_cmd` runs with `shell=True` and no timeout — a hung command hangs the CLI forever

**File:** `src/sif/cli/commands/index.py:72-87`
**Issue:** `subprocess.run(coll.pre_update_cmd, shell=True, …)` executes a
user-configured command stored in the DB (by design — accepted), but with no
`timeout=` a command that blocks (network hang, waiting on stdin, etc.)
blocks `sif index update` indefinitely with no recourse except kill -9.
`check=False` plus manual returncode handling is good; the missing timeout is
the defect.
**Fix:** `subprocess.run(..., timeout=coll.pre_update_timeout or 300)` and map
`subprocess.TimeoutExpired` to a `ClickException` alongside the returncode
branch. Consider `stdin=subprocess.DEVNULL` too, so a command that reads
stdin can't stall either.

### WR-07: `huggingface` is advertised as a valid `model_type` but every path to it dead-ends

**File:** `src/sif/embedding/factory.py:85-91` (`raise NotImplementedError`); `src/sif/cli/commands/index.py:192` (CLI choice omits it); `tests/unit/config/test_settings.py:19` (test iterates only the 4 real backends)
**Issue:** The Settings validator accepts `"huggingface"` as a valid
`model_type`, so `SIF_MODEL_TYPE=huggingface` validates cleanly — then
`EmbeddingModelFactory._create_huggingface_model` raises
`NotImplementedError`, which only surfaces later as "Failed to load embedding
model: HuggingFace models not yet implemented". The CLI `--model-type`
choice and the settings tests both encode a 4-backend reality, so the
validator is the odd one out; misconfigured users get a late, confusing
error instead of an immediate validation failure.
**Fix:** Remove `"huggingface"` from the Settings validator's valid set until
the backend exists (keep `ModelType.HUGGINGFACE` in the enum for internal
use), or add it to the CLI choice and document it as unavailable. Update
`test_model_type_validation_rejects_invalid_values` to cover it.

### WR-08: `SIF_N_GPU_LAYERS` is plumbed to the factory and then silently dropped

**File:** `src/sif/embedding/factory.py:42-56`; caller `src/sif/embedding/manager.py:88` passes `n_gpu_layers=self._config.n_gpu_layers`
**Issue:** Settings expose `n_gpu_layers` ("Number of GPU layers for GGUF
models"), `EmbeddingManager.load_model` forwards it, but
`_create_gguf_model` only forwards `n_ctx`, `n_threads`, and `verbose` —
`LlamaCppEmbedder` doesn't even accept `n_gpu_layers`. Users configuring GPU
offload for GGUF models get silent CPU inference.
**Fix:** Add `n_gpu_layers: int = 0` to `LlamaCppEmbedder.__init__` and pass
`n_gpu_layers=kwargs.get("n_gpu_layers", 0)` through to the `Llama(...)`
constructor; or, if intentionally unsupported this phase, remove the setting
so it can't silently no-op.

## Info

### IN-01: `doc_chunks_map` is dead — populated, never read

**File:** `src/sif/cli/commands/index.py:275, 291`
**Issue:** `doc_chunks_map[doc.id] = chunks` is written in the document loop
and never consulted afterwards.
**Fix:** Delete the dict and the assignment; `all_chunks` already carries
`(chunk, doc.id)`.

### IN-02: `VectorSearcher.embedding_dim` is stored and never used; three disagreeing defaults

**File:** `src/sif/search/vector.py:15-18`
**Issue:** The parameter is never read by the class (the vec0 table enforces
dimensions at insert), so callers believe they've configured something they
haven't — which is why WR-02's mismatch goes undetected. Defaults also
disagree across the codebase: `VectorSearcher`/`HybridSearcher`/`SearchPipeline`
default 768 vs `Settings.embedding_dim` default 1024.
**Fix:** Either use it (validate query/insert vector lengths against it —
this is the natural home for the WR-02 check) or remove it and force callers
to read the schema. Unify the default with Settings.

### IN-03: Ranks assigned before `min_score` filtering — filtered result lists have gaps

**File:** `src/sif/search/vector.py:78-98`
**Issue:** `rank` comes from `enumerate(...)` over raw KNN rows; rows dropped
by `score < options.min_score` leave non-contiguous ranks (e.g. 1, 3, 4) in
the returned results, unlike `HybridSearcher._deduplicate_results`, which
re-ranks sequentially.
**Fix:** Filter first, then `enumerate(results, 1)` (falls out of the WR-04
rework).

### IN-04: Vector search silently ignores `options.offset`

**File:** `src/sif/search/vector.py:33-41`
**Issue:** BM25 honors `offset` for pagination; `VectorSearcher.search`
accepts the same `SearchOptions` and ignores it, so `--offset` pagination is
inconsistent across search modes (and `test_search_options_propagation`
asserts a field vector search doesn't implement).
**Fix:** Either implement it (skip `offset` rows post-filter) or document the
omission at the `SearchOptions` level.

### IN-05: `[tool.mypy.overrides]` uses table syntax — mypy requires an array of tables

**File:** `pyproject.toml:209-214`
**Issue:** `module = [...]` under `[tool.mypy.overrides]` is not a valid
mypy TOML shape (needs `[[tool.mypy.overrides]]` with one `module` per
entry). The section is also redundant: global `ignore_missing_imports = true`
(line 203) already covers everything, so nothing is lost — but as written the
overrides are ignored/invalid config noise.
**Fix:** Replace with `[[tool.mypy.overrides]]` entries, or delete the section
given the global setting.

### IN-06: Dev toolchain ships two competing formatters

**File:** `pyproject.toml:46` (`black` in dev extras), `pyproject.toml:78-80` (`[tool.black]`)
**Issue:** CLAUDE.md standardizes on `ruff format`; keeping `black` installed
and configured invites drift (they format differently by default).
**Fix:** Drop `black` from dev extras and remove `[tool.black]`.

### IN-07: `per-file-ignores` glob doesn't cover `src/sif/cli/commands/`

**File:** `pyproject.toml:177`
**Issue:** `"src/sif/cli/*.py" = ["T20"]` — ruff's `*` matches a single path
segment, so `src/sif/cli/commands/index.py` is not covered. Latent only
(the CLI uses `rich`, not `print`), but the intent is clearly "all CLI code".
**Fix:** `"src/sif/cli/**/*" = ["T20"]`.

### IN-08: Previously-deferred embedder defects are still present (re-listed for visibility)

**File:** `src/sif/embedding/embedder.py:204-210, 340-391, 483-504, 438-450`
**Issue:** The 03-REVIEW-FIX round deferred these as out of scope and they
remain in the submitted code: (a) `ModelScopeEmbedder` picks the model
directory via unsorted `glob("*")[0]` and falls back to the *parent* when the
first entry is a file (old IN-04); (b) `_write_dim_cache` is a non-atomic,
unlocked read-modify-write (old IN-05); (c) `_probe_dimension` indexes
`response.data[0]` unguarded (old IN-06); (d) `create_embedder()` free
function is dead code with no `openai` branch (old IN-02); (e)
`SimpleEmbedder`'s docstring says "TF-IDF" but the implementation is
hash-based and carries no semantic signal.
**Fix:** Track as backlog; the quick wins are sorting the glob
(`sorted(model_path.glob("*"))` and prefer a dir containing
`config.json`), guarding `if not response.data: raise`, and deleting
`create_embedder`/`SimpleEmbedder` or fixing the docstring.

### IN-09: GGUF backend depends on llama-cpp-python API surface far above the pinned floor; duplicate n_ctx defaults

**File:** `src/sif/embedding/embedder.py:113-156`; `src/sif/embedding/factory.py:51-56`; `pyproject.toml:60` (`llama-cpp-python>=0.2.0`)
**Issue:** `LlamaCppEmbedder` uses `Llama(embedding=True)` and
`model.embed(text)`, both of which appeared (and in `embedding=True`'s case
was later deprecated) well after 0.2.0 — at the pinned floor the constructor
or the `embed` call can raise. Also `LlamaCppEmbedder` defaults `n_ctx=8192`
while the factory passes `kwargs.get("n_ctx", 2048)` — two different defaults
for the same knob.
**Fix:** Verify against the llama-cpp-python version you actually target,
raise the floor to that version, and collapse the n_ctx default to one place
(prefer the class default; drop the factory's).

### IN-10: Dangling cross-reference to the previous review; mock-only "integration" suite

**File:** `tests/integration/test_embed_idempotency.py:120` (`_delenv_settings_vars` docstring cites "03-REVIEW WR-10/11"); `tests/integration/test_search_pipeline.py:1`
**Issue:** (a) The docstring cites finding numbers from the previous
03-REVIEW.md, which this regenerated report replaces — after this commit the
reference resolves to nothing. Cite 03-REVIEW-FIX.md instead. (b)
`test_search_pipeline.py` lives under `integration/` but exercises everything
against `MagicMock`s — it is a unit suite by any definition; the phase's real
integration coverage lives in test_embed_idempotency.py. Not a reliability
defect, but the placement misleads future maintainers about what is covered.
**Fix:** Point the docstring at 03-REVIEW-FIX.md; consider moving
test_search_pipeline.py to `tests/unit/search/` or seeding a real sqlite DB
in it.

---

_Reviewed: 2026-09-04T11:39:13Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
