# Phase 21: Scale, Maintenance + Embedder Identity - Context

**Gathered:** 2026-11-15
**Status:** Ready for planning

<domain>
## Phase Boundary

The milestone's scale-and-contract phase — make large-corpus maintenance safe and fast, and make the index know which embedder produced its vectors. Delivers exactly SCALE-01, SCALE-02, SCALE-03, CORR-06, EMB-01, EMB-02:

1. **Bounded staleness/context reads (CORR-06)** — eliminate the per-query full scans of `document_embeddings` and `contexts` through a transactional `embedded_documents` shadow (reconciled in cleanup/vacuum) and a normalized-context cache; staleness stays a derived signal and contexts keep verbatim two-sided normalization.
2. **Index maintenance (SCALE-01/02)** — `sif index vacuum` (flock + quiesce + no open transaction + checkpoint + 2× disk check, retryable busy errors, restricted targets) and a verified backup via the SQLite online backup API + `integrity_check`.
3. **Streaming embed (SCALE-03)** — embed outside transactions in bounded batches, short per-document commits, resumable, CR-02 failure reporting preserved, batch-boundary sanity against garbage vectors (qmd #897 lesson).
4. **Embedder identity (EMB-01)** — persisted `index_meta` identity (model id + revision/hash + pooling + prompt scheme, reusing the cache's `_cache_model_id` format); consolidated dimension guards; legacy-DB warn-once + backfill; mismatch → fail-fast embed / warn+mark search.
5. **Role-aware embed (EMB-02)** — `embed_query`/`embed_documents` with `prompt_name`, the prompt dimension in the cache key; the Qwen3 default path stays byte-identical until the Phase 23 Harrier gate passes.

NOT in scope: metadata filtering (Phase 20, shipped), MCP SDK v2 shell swap and any MCP exposure of maintenance commands (Phase 22), Harrier evaluation/model arms (Phase 23), chunk/title-breadcrumb sweeps and `models pull/status` UX (Phase 24), ANN indexes, multi-space/per-collection embedder identity, a write-side normalized-contexts column, scheduled/automatic vacuum. No new runtime dependencies (the v1.2 pair `mcp` + `rapidfuzz` already landed).

</domain>

<decisions>
## Implementation Decisions

### Embedder identity contract (EMB-01)
- **D-01:** **Identity is GLOBAL per index, not per collection.** One global `index_meta` key (e.g. `embedder.identity`) describes the vector space of `document_embeddings`. Rationale: there is exactly ONE vec0 table, hence one KNN space; search is not collection-scoped by default, so per-collection identities would imply a multi-space storage that does not exist and could silently compare mutually unintelligible vectors. The `index_meta` docstring's "embedder identity in Phase 21" anticipation is realized as a global key — the per-collection `convention:<id>` namespace stays for parser/convention markers only. — **Reversibility:** costly — moving to per-collection identity later changes every vector write and every identity read (Phase 22/23/24 consumers).
- **D-02:** **Identity payload is structured JSON with a deterministic fingerprint; the base string reuses `_cache_model_id()`.** Fields: schema/format version, `cache_model_id` (`model_type:model_name[@api_base]`), model name/type, `api_base` when present, dimension, effective pooling (`mean`/`last_token`/`unknown`), normalization flag, effective query/document prompt scheme, and a best-effort revision (`revision` or `unknown`). For GGUF, include the model-file SHA-256 (computed once per process; a file swapped at the same path must be detectable). For sentence-transformers, include the resolved model revision when the loaded model exposes one. OpenAI/ModelScope record `api_base` + model name and `revision: unknown`. Revision resolution never blocks an embed. **Identity checks apply only while stored vectors exist** — an embeddings-empty index accepts any embedder and the next embed overwrites the identity, so deleting all vectors resets the contract naturally. Written inside the same transaction as the index's first successful embedding write. — **Reversibility:** costly — the JSON is consumed by Phase 22 (lazy embedder), Phase 23 (Harrier arms) and Phase 24 (`models status`), and the fingerprint feeds the cache key.
- **D-03:** **Mismatch: fail-fast embed, warn + mark search.** On an embed/index-write path (embed_cmd, watcher inline embed), an identity mismatch — including a dimension disagreement — raises a user-facing `ClickException` naming the stored fingerprint vs the current one and the remedy (`sif index embed --force` with the matching model, or restore the stored model), and writes no vectors. On a search path that touches vectors (CLI `vsearch`/`query`, MCP vector path, eval/bench hybrid), a mismatch emits ONE stderr warning per process naming both identities and the remedy and marks every result `vectors_stale=True` — reusing the existing derived marker, **no new result field and no schema change** — while still returning results. BM25-only commands neither warn nor mark. Never silent acceptance. — **Reversibility:** costly — a public failure contract agents/clients will branch on.
- **D-04:** **Legacy DBs: warn-once + assumed-identity backfill, certified by a full re-embed.** When `document_embeddings` has rows but no identity key, the first open writes `source: legacy-assumed` with the current identity and emits ONE warning per process ("index predates embedder identity; assuming <id>; run `sif index embed --force` to certify"). Search is never blocked on an assumed identity (it may be correct) and a later model swap is still detected against the assumed value. The identity is rewritten as `source: verified` only after a complete `--force` re-embed of every collection with zero failures (or on a fresh DB's first embedding write); a partial/normal run keeps it `assumed`. — **Reversibility:** costly — the source marker and warning are a one-time migration contract.
- **D-05:** **Consolidate the index-vs-model dimension guards into one identity module.** A single module (e.g. `src/sif/embedding/identity.py`) owns identity construction from settings + the loaded model, the single `FLOAT[n]` schema read, and a mode-aware `check_identity(conn, identity, mode=embed|search|init)`. The three inline index-vs-model guards (`database/schema.py` `_create_vector_tables`, `cli/commands/index.py` `embed_cmd`, `indexing/watcher.py` `_schema_embedding_dim`) delegate to it; the width check becomes the legacy facet of the identity check (identity absent ⇒ width-only). The OpenAI constructor's endpoint-vs-`SIF_EMBEDDING_DIM` check remains a config-layer check but reuses the shared error wording. — **Reversibility:** reversible.

### Role-aware embed + prompt scheme (EMB-02)
- **D-06:** **Role-explicit methods on `EmbeddingManager`; the `Embedder` protocol is unchanged.** Add `embed_query(text)` and `embed_documents(texts)` (names are the planner's) that route through an internal role-aware path; the `Embedder` protocol keeps `embed`/`embed_batch`/`dimension` so every implementation and test double (`ConceptEmbedder`) keeps working without churn. `SentenceTransformerEmbedder` gains `prompt_name` support via the installed sentence-transformers 5.4.1 `encode(..., prompt_name=...)` (verified present on this machine); backends without prompt support record `prompt_scheme: none` in the identity. Audit every call site: hybrid query, HyDE, query expansion candidates, eval/bench query legs → query role; `embed_cmd` and watcher document embeds → document role. — **Reversibility:** costly — the role boundary is the cross-phase embed contract consumed by Phase 22's lazy embedder and Phase 23's arms.
- **D-07:** **Prompt names come from Settings plus a small known-model default table; no new CLI flag.** Settings `query_prompt_name` / `document_prompt_name` (env `SIF_QUERY_PROMPT_NAME` / `SIF_DOCUMENT_PROMPT_NAME`, default `None`) are the override surface. A small internal table maps known instruction-tuned models (Harrier → query `web_search_query`, document none) so the Phase 23 arm cannot be silently crippled by a missing instruction; unknown models default to no prompt. Qwen3 has no table entry, so its vectors and cache keys stay byte-identical until the Phase 23 gate. The effective prompt scheme is part of the identity fingerprint (D-02). — **Reversibility:** costly — a public Settings surface (generator-owned docs) and a vector-affecting behavior.
- **D-08:** **The prompt/role dimension enters the cache key only when a prompt is effective.** Cache bucket = `_cache_model_id()` + `|q@<prompt>` / `|d@<prompt>` when that role's prompt is set; when both prompts are `None`, keys are exactly today's value (Qwen3 byte-identical). A prompted query and an unprompted document of the same text therefore never collide. When the identity carries a revision/file hash, it also joins the bucket (a GGUF swapped at the same path must not read the old file's cached vectors), with the same suffix discipline so an absent revision leaves keys unchanged. — **Reversibility:** reversible.

### Bounded staleness reads (CORR-06)
- **D-09:** **`embedded_documents` is a transactional shadow, not a flag.** New table `embedded_documents(document_id TEXT PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE)`; a row means the document has ≥1 row in `document_embeddings`. Maintained in the SAME transaction as every embedding write/delete: `embed_cmd` batches, the watcher's inline embed, `delete_embeddings_by_document`, cleanup's orphan-embedding delete, and document/collection delete paths. It is rebuildable from `document_embeddings` at any time and never independently authoritative — staleness stays a derived signal. Orphan embedding rows (possible after a document delete until cleanup) never create shadow rows: every insert joins `documents`. — **Reversibility:** costly — a new schema surface every embedding writer must maintain; divergence is a correctness bug.
- **D-10:** **One-time backfill at schema init, reconciliation in cleanup/vacuum.** For legacy DBs, `SchemaManager` backfills the shadow from `document_embeddings` (existing documents only) in one idempotent pass gated by an `index_meta` version key (the Phase 20 D-06 backfill pattern), warning once; fresh DBs write the marker immediately at zero cost. `sif cleanup` and `sif index vacuum` reconcile (delete shadow rows whose embeddings are gone, insert missing rows for existing documents) inside their existing transactions. The shadow is created only when the vec0 table exists; a missing shadow/vec0 degrades to "no markers" exactly like today's `None` path. — **Reversibility:** costly — the version marker is a one-time migration contract.
- **D-11:** **Staleness reads switch to the shadow with byte-identical output.** `embedded_document_ids()` becomes an indexed read of the shadow; the display gate keeps today's semantics (empty set ⇒ no markers; vec0 absent ⇒ `None` ⇒ unmarked), the Phase 19 single-`enrich_results`-at-exit contract is untouched, and `sif status`'s vector-lag row (which shares the helper) becomes bounded too. Regression: marker output byte-identical on the existing fixture suite, including the legacy verbatim `/tmp` vs `/private/tmp` context fixture. — **Reversibility:** reversible.

### Contexts read caching (CORR-06)
- **D-12:** **Per-process/connection cache of the normalized context map; no schema change.** Cache the `normalize_path(target_id) → content` map (newest `updated_at` wins, preserving the current D-06 semantics) and invalidate on (a) any `ContextRepository` write in the same process and (b) a SQLite `PRAGMA data_version` change (another connection committed). Keep the no-SQL-prefilter rule and two-sided normalization verbatim; do NOT add a `normalized_target_id` column or backfill in this phase. Rationale: the write-side column touches the locked PROJECT.md Key Decision (realpath is not invertible; verbatim legacy rows must keep matching) and buys nothing at personal-KB context counts; the cache removes the per-query scan while preserving every existing row. — **Reversibility:** reversible.

### Maintenance surface (SCALE-01/02)
- **D-13:** **`sif index vacuum` and `sif index backup` live on the `index` group; CLI only in this phase.** `sif index vacuum` (no args) prints before/after file sizes and reclaimed bytes. `sif index backup [--output PATH]` defaults to `<db_dir>/backups/<db-stem>-<UTC-timestamp>.db`, creates the default backup directory, refuses an existing target file, and always verifies the copy. Neither command registers an MCP tool in Phase 21; Phase 22 owns any MCP exposure (destructiveHint + target-path restriction per PITFALLS 11/19). — **Reversibility:** costly — command names and the default backup path are public surfaces behind the `make docs-generate` CI diff gate.
- **D-14:** **Vacuum/backup semantics: flock + busy timeout + checkpoint + no open transaction + explicit 2× disk check; busy errors are retryable.** Both commands take `index_lock` (`settings.lock_wait_timeout`), set a busy timeout on their own connection, and run outside `Database.transaction()`. Vacuum runs `PRAGMA wal_checkpoint(TRUNCATE)` first, then `VACUUM`. Backup uses the SQLite online backup API (not `VACUUM INTO`, never a file copy) and runs `PRAGMA integrity_check` on the copy before reporting success. Busy/locked failures become `click.ClickException` with retry wording (never a crash, never a partial success report). Vacuum prechecks `shutil.disk_usage` free bytes ≥ 2× (db + WAL) bytes and errors with required/available numbers; there is no `--skip-space-check` in this phase. Watch daemons and MCP hosts do NOT need to be stopped first: WAL readers coexist, and a conflict surfaces as the documented retryable error. — **Reversibility:** reversible — constraints can be relaxed additively.

### Streaming embed (SCALE-03)
- **D-15:** **Per-document atomicity with embedding outside the transaction.** Iterate documents; chunk, embed in model batches of `settings.batch_size` **outside any transaction**, then commit ONE short transaction per document (delete-before-insert chunks + embeddings, shadow row, document/collection stats). Memory is bounded by one document's chunks, and the write lock is held only for inserts. Resume is the existing exact-set skip (`get_all_embedded_chunk_ids` / `_needs_embedding`), so a re-run embeds exactly the missing documents. A document's partial state is never visible. — **Reversibility:** costly — the transaction/failure contract changes and partial progress becomes durable by design.
- **D-16:** **Document-local failures are isolated; systemic failures abort after committing prior work.** A document-local failure (parse/chunk/storage for that document) is recorded and the run continues. Systemic failures (model load, identity mismatch, batch-boundary sanity) abort the run after prior documents are committed. At the end, one failure report is raised outside any transaction, the exit code is non-zero, and successful work is durable — preserving CR-02's per-collection isolation and reporting contract. The "already embedded" skip and collection stats behavior stay. — **Reversibility:** costly — failure semantics are an operational contract.
- **D-17:** **Batch-boundary sanity is mandatory (qmd #897 lesson).** After each model batch: output count equals input count, every vector is finite (no NaN/Inf), dimensions match the identity, and when normalization is on each vector's L2 norm is 1 within tolerance (otherwise non-zero). A violation is systemic: the batch is not persisted, the run aborts after prior commits, and the error names the identity, batch position, and offending chunk. Empty/whitespace-only chunk text is rejected before embedding. — **Reversibility:** reversible.
- **D-18:** **One shared streaming embed service; the watcher routes through it.** Extract the chunk → embed → persist pipeline (sanity checks, shadow maintenance, short transaction) into a shared helper used by `embed_cmd`; the watcher's per-path inline embed reuses the same writer so completeness, sanity, and shadow maintenance cannot diverge. The watcher's trigger/debounce/depth semantics are unchanged. Phase 24's per-arm re-embed reuses the helper. — **Reversibility:** reversible.

### Baseline and project constraints
- **D-19:** **The Qwen3 default path stays byte-identical.** With default settings (no prompt names, no identity mismatch), query vectors, document vectors, search output, and cache keys are byte-identical to pre-Phase-21 for the same corpus; the Phase 19/20 goldens and the SC1 hybrid golden must reproduce. The only new side effects are the identity `index_meta` row, the shadow table, and (on legacy DBs) the one-time backfill/assumed-identity warning. This is the locked precondition for Phase 23's baseline arm. — **Reversibility:** costly — the Harrier gate compares against this exact baseline.
- **D-20:** **Docs-generate gate and no new runtime dependencies.** New Settings fields (`query_prompt_name`, `document_prompt_name`) and new CLI commands (`index vacuum`, `index backup`) flow through `make docs-generate`; `docs/cli-reference.md` and `docs/configuration.md` are never hand-edited. No dependency is added in this phase.

### Claude's Discretion
- Exact identity JSON key spelling, schema-version value, and fingerprint hash algorithm (must be deterministic and stable across processes).
- Whether the identity check exposes a cheap settings-only precheck at schema init and a full check after the model loads; the layering is the planner's as long as D-03's modes hold.
- Shadow-table column set beyond `document_id` (e.g. a write-generation/updated_at column), index shape, and whether reconciliation lives in a `database/maintenance.py` helper.
- Cache placement for D-12 (module-level keyed by connection vs an object threaded through the pipeline) and the exact `data_version` polling point.
- Maintenance command output layout, progress presentation, and whether `--json` is offered (follow existing output conventions; stdout must stay machine-clean when JSON is requested).
- Exact batch size for embed calls when `settings.batch_size` is not suitable per document, and whether document-level progress prints every N documents.
- How the identity is surfaced in `sif index status` (if at all) — Phase 24's `models status` is the consumer of record.
- Test fixture design for the byte-identical baseline, legacy-DB upgrade, mid-run failure, garbage-vector sanity, vacuum-under-concurrent-reader, and backup integrity.

### Locked upstream (roadmap/research — do not re-litigate)
- `embedded_documents` shadow reconciled in cleanup/vacuum; staleness stays derived; contexts keep verbatim two-sided normalization; attach-once already landed in Phase 19 (CORR-05).
- Vacuum: flock + quiesce + no open transaction + checkpoint + 2× disk check, retryable busy errors, restricted targets. Backup: SQLite online backup API + `integrity_check`.
- Streaming embed: embed outside transactions, short per-batch commits, resumable, CR-02 reporting preserved, batch-boundary sanity.
- Identity in a regular `index_meta` table (not vec0 markers — readable without sqlite-vec), reusing the cache's `_cache_model_id` format; the three dim-guard sites consolidated; legacy warn-once + backfill; mismatch → fail-fast embed / warn+mark search.
- Role-aware surface with `prompt_name`; the prompt dimension in the cache key; the Qwen3 default path byte-identical until the Phase 23 Harrier gate passes.
- Harrier model-arm decisions (native only, GGUF conditional follow-up) belong to Phase 23 — not re-opened here.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements and roadmap
- `.planning/REQUIREMENTS.md` — SCALE-01, SCALE-02, SCALE-03, CORR-06, EMB-01, EMB-02; Out of Scope table (ANN, semantic/late chunking, full Windows support, etc.)
- `.planning/ROADMAP.md` §Phase 21 — goal + five success criteria; §Phase 22/23/24 — consumers of the embedder identity, role-aware embed, and streaming embed; §Cross-Phase Contracts ("Embedder identity + role-aware embed", "docs-generate gate")
- `.planning/PROJECT.md` §Current Milestone + §Key Decisions — v1.2 scope, the 1024-dim Harrier/Qwen3 trap and identity gate, exactly two new runtime deps, byte-identical-defaults culture
- `.planning/STATE.md` — accumulated decisions; research gaps: "contexts normalization decision touches a locked Key Decision (21 discussion)"; "Phase 5 (staleness shadow): MEDIUM — transactional coupling audit of ALL vector write paths; reconcile design"

### Milestone research
- `.planning/research/SUMMARY.md` §"Phase 5: Scale, Maintenance + Embedder Identity" — deliverables and rationale ("Identity BEFORE Harrier (same-dim trap is locked)"); §Research Flags (staleness shadow MEDIUM; contexts normalization); §Architecture Approach (`index_meta` identity, transactional shadow)
- `.planning/research/PITFALLS.md` — Pitfall 1 (same-dimension swap), Pitfall 2 (query/document instruction asymmetry + cache prompt dimension), Pitfall 18 (scan elimination vs derived staleness / verbatim contexts), Pitfall 19 (VACUUM against live hosts, backup semantics), Pitfall 20 (streaming embed vs the per-collection transaction contract), Pitfall-to-Phase Mapping (18/19/20 → Scale)
- `.planning/research/FEATURES.md` §"B. Correctness and scale" — scan elimination, vacuum/backup, embed streaming, Harrier identity rows
- `.planning/research/ARCHITECTURE.md` — pipeline order and file-level change map; bounded-read surfaces
- `.planning/research/STACK.md` — zero new dependencies; SQLite VACUUM/online-backup mechanics; sentence-transformers 5.4.1 `prompt_name` verified

### Prior phase decisions (carry forward, do not re-litigate)
- `.planning/phases/20-metadata-filtering-discovery/20-CONTEXT.md` — D-06 backfill pattern (`index_meta` marker, one-time pass, never serve from a half-populated store); D-05 typed kv write paths; `builtIns`/discovery contract (Phase 22 consumer)
- `.planning/phases/19-search-correctness/19-CONTEXT.md` — D-07 metadata fast path, D-08 checksum over ALL frontmatter, single `enrich_results` attach (CORR-05), staleness stays derived, contexts two-sided normalization
- `.planning/phases/18-quality-instrument-personal-bench-rapidfuzz-dym/18-CONTEXT.md` — the bench instrument, per-leg × language reports, hash split, 0.01 tie rule (Phase 23 consumes it)
- `.planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-CONTEXT.md` — green CI matrix under migrations, deterministic test env, no new deps beyond the locked pair

### Code and data surfaces (verified this session at HEAD)
- `src/sif/embedding/manager.py` — `_cache_model_id()` at `manager.py:153-163`, cache lookup/store, `embed`/`embed_single`, `get_model_info`
- `src/sif/embedding/embedder.py` — `SentenceTransformerEmbedder.embed`/`embed_batch` (`encode` without prompt today), `LlamaCppEmbedder`, OpenAI endpoint-vs-settings dimension check
- `src/sif/embedding/cache.py` — `(content_hash, model_id)` primary key; `model_id` bucket
- `src/sif/embedding/factory.py` — per-`ModelType` construction
- `src/sif/database/schema.py` — `index_meta` table + docstring (`schema.py:262-275`), `_create_vector_tables` dimension guard (`schema.py:590-620`), `_backfill_metadata_values` (D-06 pattern), `create_all` ordering
- `src/sif/database/repositories.py` — `IndexMetaRepository` (`repositories.py:663+`), `DocumentRepository.delete`/`delete_by_collection`, `DocumentChunkRepository.delete_by_document`, `ContextRepository`
- `src/sif/search/vector.py` — `add_embedding`/`add_embeddings_batch` (`vector.py:325-372`), `delete_embeddings_by_document` (`vector.py:374-384`), `get_all_embedded_chunk_ids` (`vector.py:398-417`), `create_embedding_purger`
- `src/sif/search/staleness.py` — `embedded_document_ids` full scan (`staleness.py:37-52`), display gate and `None` degradation
- `src/sif/search/context_attach.py` — no-SQL-prefilter context scan (`context_attach.py:25-63`), single `enrich_results` composition
- `src/sif/search/hybrid.py` — query embed call site (`hybrid.py:103`), pipeline query/HyDE embeds (`hybrid.py:273-281`)
- `src/sif/indexing/watcher.py` — inline chunk+embed leg, `_schema_embedding_dim` (`watcher.py:319-327`), per-burst flock
- `src/sif/cli/commands/index.py` — `embed_cmd` per-collection transaction (`index.py:190-391`), inline dim guard (`index.py:246-261`), `_needs_embedding`
- `src/sif/cli/main.py` — `cleanup` (orphan delete, `main.py:229-269`), `_vector_lag_text` sharing `embedded_document_ids` (`main.py:141-164`), `status`
- `src/sif/database/database.py`, `src/sif/database/factory.py`, `src/sif/database/locking.py` — `Database.transaction`, `create_connection`, `WAL_CHECKPOINT_TRUNCATE`, `index_lock`
- `src/sif/config/settings.py` — `model_name`/`model_type`/`embedding_dim`/`batch_size`/`api_base` (`settings.py:110-160`), `lock_wait_timeout`, `chunk_size`/`chunk_overlap`
- `src/sif/mcp/backend.py` — embedder construction and `init_schema` dimension (`backend.py:96-135`, `207`)

### Project conventions
- `CLAUDE.md` — quality gates (`ruff check`, `ruff format --check`, `ty check src/sif`, `pytest` fail_under=90), error culture (`click.ClickException`, remedy hints), generator-owned docs
- `Makefile` — `docs-generate` target (`scripts/generate_cli_ref.py` + `scripts/generate_config_ref.py`), CI diff gate

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`_cache_model_id()`** already produces the canonical `model_type:model_name[@api_base]` bucket string — the identity base and the cache key extend it rather than inventing a parallel naming scheme.
- **`IndexMetaRepository`** is the key/value store; the `convention:<collection_id>` namespacing and Phase 20's `metadata_values_version` marker are proven precedent for the identity key and the shadow backfill marker.
- **`SchemaManager._backfill_metadata_values`** is the exact template for D-10: one Python pass, per-item short transaction, marker written only after a complete pass, exceptions propagate so no host serves a half-populated state.
- **The `index_lock` + `lock_wait_timeout` pair** already arbitrates all index writers; vacuum/backup use the same window and `WAL_CHECKPOINT_TRUNCATE` from `database/factory.py`.
- **`enrich_results`** is already the single attach owner for every search exit — the staleness read change is internal to `staleness.py` and must not move the call sites.
- **`_needs_embedding` + `get_all_embedded_chunk_ids()`** already provide exact-set completeness; streaming reuses them for resume.
- **`SentenceTransformerEmbedder`** already funnels every encode through `_encode_kwargs`, so role/prompt kwargs have one insertion point (verified: the installed 5.4.1 `encode` accepts `prompt_name`).
- **`create_embedding_purger`** is the shared embedding-delete construction point — the shadow delete must ride the same purge sites.

### Established patterns
- Detection-gated, idempotent migrations inside `SchemaManager`; fresh and already-migrated DBs pay zero cost. Never the deleted `MigrationManager`.
- Byte-identical defaults: default settings reproduce pre-change output; every new behavior is gated on a trigger (prompt set, identity present/mismatched, maintenance command, legacy DB).
- Warnings/notices on stderr; stdout/JSON stays machine-clean.
- Parameterized SQL and constant query strings only; no value interpolation.
- Remedy-hint error culture: name cause + fix (stored vs current identity, retry wording, free-vs-required bytes).
- Generator-owned docs: every new flag/command/setting runs `make docs-generate`; the CI diff gate proves it.
- Deterministic tests: `tmp_path` batteries, `ConceptEmbedder` for hermetic embeddings, no wall-clock races; latency asserts only on core functions.

### Integration points
- `src/sif/embedding/identity.py` (new) — identity dataclass/fingerprint, single `FLOAT[n]` read, mode-aware checks, legacy warn/backfill helpers.
- `src/sif/embedding/manager.py` — `embed_query`/`embed_documents`, prompt-aware cache key, identity exposure.
- `src/sif/embedding/embedder.py` — prompt plumbing for ST; pooling/normalization reporting for identity.
- `src/sif/embedding/cache.py` — no schema change; the manager passes the extended bucket string.
- `src/sif/database/schema.py` — `embedded_documents` DDL, backfill marker, identity key creation, create_all ordering (vec0-conditional).
- `src/sif/database/repositories.py` — shadow maintenance in document/chunk/context write paths; `ContextRepository` write-generation/write hooks; `IndexMetaRepository` identity CRUD.
- `src/sif/search/staleness.py` — shadow read; display-gate/degradation unchanged.
- `src/sif/search/context_attach.py` — normalized-map cache consumption; same matching semantics.
- `src/sif/search/vector.py` — shadow upsert/delete inside embedding write/delete methods (transaction inherited from caller).
- `src/sif/indexing/watcher.py` — route inline embed through the shared streaming writer; identity check on the embed depth.
- `src/sif/cli/commands/index.py` — streaming `embed_cmd`, identity check, `index vacuum`/`index backup` commands.
- `src/sif/cli/main.py` — `cleanup` reconciliation; `status` stays bounded via the shadow helper.
- `src/sif/database/maintenance.py` (new, name planner's) — vacuum/backup/reconcile logic, shared by CLI/cleanup.
- `src/sif/config/settings.py` — `query_prompt_name`, `document_prompt_name`.
- `src/sif/mcp/backend.py` — identity check on schema/vector init; Phase 22 consumes the contract.
- Tests: `tests/unit/embedding/`, `tests/unit/database/`, `tests/unit/search/`, `tests/unit/indexing/`, `tests/unit/cli/`, `tests/unit/mcp/`, `tests/e2e/`; plus the existing goldens and fixture corpora.

</code_context>

<specifics>
## Specific Ideas

- **Same-dimension swap regression:** build an index with a ConceptEmbedder-shaped identity A, then open with identity B at the same dimension — embed must fail fast naming both identities; a search must warn once and mark results. A "same model name, different GGUF bytes" fixture must be detected by the file hash.
- **Byte-identical baseline:** record query vectors, a hybrid result page, and the SC1 golden with default settings before/after; assert exact equality. The identity `index_meta` row and shadow table are the only new writes.
- **Legacy upgrade:** simulate a pre-Phase-21 DB (embeddings, no identity, no shadow) → first open backfills the shadow, warns once, writes `source: legacy-assumed`; `sif index embed --force` rewrites `source: verified`.
- **Staleness parity:** the fixture suite's `vectors_stale` markers (CLI all five formats, MCP, bench) and `sif status` vector-lag text must be byte-identical after the shadow switch; the `/tmp` vs `/private/tmp` verbatim context fixture must still attach.
- **Shadow divergence guard:** delete a document without purging its embeddings, run `sif cleanup` — the reconcile pass must not resurrect a shadow row for the missing document; run vacuum — same.
- **Streaming failure:** kill the process mid-run (fixture-injected failure) after N documents; the committed documents survive, a re-run embeds exactly the remainder, no orphan vectors/shadow rows; a garbage-vector batch aborts systemically and persists nothing from that batch.
- **Vacuum under load:** a concurrent reader loop (and a watch host) while vacuum runs — either a clean result or the documented retryable error; the DB passes `integrity_check` and the lock is released.
- **Backup proof:** backup a populated WAL DB while writes continue; the copy opens, passes `integrity_check`, and contains the committed rows; an existing target path is refused.
- **Cache isolation:** the same text embedded as a prompted query and an unprompted document lands in different cache buckets; with prompts unset, the bucket string is unchanged from today.
- **No new scans:** assert no per-query `SELECT ... FROM contexts` / `SELECT document_id FROM document_embeddings` full scans remain on the search path (grep-style test or query-plan assertion), while the reconcile/backfill paths may scan.

</specifics>

<deferred>
## Deferred Ideas

- **Per-collection embedder identity / multiple vector spaces** — rejected now: one vec0 table means one KNN space and global search would compare unintelligible vectors across collections. Revisit only if per-collection vector spaces become a feature (would require storage redesign).
- **MCP exposure of vacuum/backup** — belongs to Phase 22 (`destructiveHint: true` + target-path restriction per PITFALLS 11/19).
- **`contexts.normalized_target_id` write-side column** — touches the locked PROJECT.md Key Decision (realpath is not invertible; verbatim legacy rows must keep matching); revisit only if context counts outgrow the cache.
- **`--skip-space-check` / `PRAGMA optimize` / `auto_vacuum` mode changes** — additive later if the conservative defaults prove annoying.
- **Scheduled or threshold-triggered auto-vacuum** — a new capability, not a clarification of this phase.
- **Embedder identity display in `sif status`** — Phase 24's `sif models status` is the designated consumer; adding a status row is additive later.
- **A dedicated `sif index embed --certify` command** — `--force` is the certification path; no separate command in this phase.

</deferred>

---

*Phase: 21-Scale, Maintenance + Embedder Identity*
*Context gathered: 2026-11-15*
