# Phase 21: Scale, Maintenance + Embedder Identity - Research

**Researched:** 2026-11-15
**Domain:** SQLite maintenance/streaming writes, transactional derived shadow tables, embedder identity + role-aware embedding, per-process read caches
**Confidence:** HIGH for the code seams and SQLite/Python runtime semantics; MEDIUM for the model-revision provenance limits (ModelScope) and a few CONTEXT-discretion choices

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

Copied verbatim from `21-CONTEXT.md` `## Implementation Decisions`:

- **D-01:** **Identity is GLOBAL per index, not per collection.** One global `index_meta` key (e.g. `embedder.identity`) describes the vector space of `document_embeddings`. Rationale: there is exactly ONE vec0 table, hence one KNN space; search is not collection-scoped by default, so per-collection identities would imply a multi-space storage that does not exist and could silently compare mutually unintelligible vectors. The `index_meta` docstring's "embedder identity in Phase 21" anticipation is realized as a global key — the per-collection `convention:<id>` namespace stays for parser/convention markers only. — **Reversibility:** costly — moving to per-collection identity later changes every vector write and every identity read (Phase 22/23/24 consumers).
- **D-02:** **Identity payload is structured JSON with a deterministic fingerprint; the base string reuses `_cache_model_id()`.** Fields: schema/format version, `cache_model_id` (`model_type:model_name[@api_base]`), model name/type, `api_base` when present, dimension, effective pooling (`mean`/`last_token`/`unknown`), normalization flag, effective query/document prompt scheme, and a best-effort revision (`revision` or `unknown`). For GGUF, include the model-file SHA-256 (computed once per process; a file swapped at the same path must be detectable). For sentence-transformers, include the resolved model revision when the loaded model exposes one. OpenAI/ModelScope record `api_base` + model name and `revision: unknown`. Revision resolution never blocks an embed. **Identity checks apply only while stored vectors exist** — an embeddings-empty index accepts any embedder and the next embed overwrites the identity, so deleting all vectors resets the contract naturally. Written inside the same transaction as the index's first successful embedding write. — **Reversibility:** costly — the JSON is consumed by Phase 22 (lazy embedder), Phase 23 (Harrier arms) and Phase 24 (`models status`), and the fingerprint feeds the cache key.
- **D-03:** **Mismatch: fail-fast embed, warn + mark search.** On an embed/index-write path (embed_cmd, watcher inline embed), an identity mismatch — including a dimension disagreement — raises a user-facing `ClickException` naming the stored fingerprint vs the current one and the remedy (`sif index embed --force` with the matching model, or restore the stored model), and writes no vectors. On a search path that touches vectors (CLI `vsearch`/`query`, MCP vector path, eval/bench hybrid), a mismatch emits ONE stderr warning per process naming both identities and the remedy and marks every result `vectors_stale=True` — reusing the existing derived marker, **no new result field and no schema change** — while still returning results. BM25-only commands neither warn nor mark. Never silent acceptance. — **Reversibility:** costly — a public failure contract agents/clients will branch on.
- **D-04:** **Legacy DBs: warn-once + assumed-identity backfill, certified by a full re-embed.** When `document_embeddings` has rows but no identity key, the first open writes `source: legacy-assumed` with the current identity and emits ONE warning per process ("index predates embedder identity; assuming <id>; run `sif index embed --force` to certify"). Search is never blocked on an assumed identity (it may be correct) and a later model swap is still detected against the assumed value. The identity is rewritten as `source: verified` only after a complete `--force` re-embed of every collection with zero failures (or on a fresh DB's first embedding write); a partial/normal run keeps it `assumed`. — **Reversibility:** costly — the source marker and warning are a one-time migration contract.
- **D-05:** **Consolidate the index-vs-model dimension guards into one identity module.** A single module (e.g. `src/sif/embedding/identity.py`) owns identity construction from settings + the loaded model, the single `FLOAT[n]` schema read, and a mode-aware `check_identity(conn, identity, mode=embed|search|init)`. The three inline index-vs-model guards (`database/schema.py` `_create_vector_tables`, `cli/commands/index.py` `embed_cmd`, `indexing/watcher.py` `_schema_embedding_dim`) delegate to it; the width check becomes the legacy facet of the identity check (identity absent ⇒ width-only). The OpenAI constructor's endpoint-vs-`SIF_EMBEDDING_DIM` check remains a config-layer check but reuses the shared error wording. — **Reversibility:** reversible.
- **D-06:** **Role-explicit methods on `EmbeddingManager`; the `Embedder` protocol is unchanged.** Add `embed_query(text)` and `embed_documents(texts)` (names are the planner's) that route through an internal role-aware path; the `Embedder` protocol keeps `embed`/`embed_batch`/`dimension` so every implementation and test double (`ConceptEmbedder`) keeps working without churn. `SentenceTransformerEmbedder` gains `prompt_name` support via the installed sentence-transformers 5.4.1 `encode(..., prompt_name=...)` (verified present on this machine); backends without prompt support record `prompt_scheme: none` in the identity. Audit every call site: hybrid query, HyDE, query expansion candidates, eval/bench query legs → query role; `embed_cmd` and watcher document embeds → document role. — **Reversibility:** costly — the role boundary is the cross-phase embed contract consumed by Phase 22's lazy embedder and Phase 23's arms.
- **D-07:** **Prompt names come from Settings plus a small known-model default table; no new CLI flag.** Settings `query_prompt_name` / `document_prompt_name` (env `SIF_QUERY_PROMPT_NAME` / `SIF_DOCUMENT_PROMPT_NAME`, default `None`) are the override surface. A small internal table maps known instruction-tuned models (Harrier → query `web_search_query`, document none) so the Phase 23 arm cannot be silently crippled by a missing instruction; unknown models default to no prompt. Qwen3 has no table entry, so its vectors and cache keys stay byte-identical until the Phase 23 gate. The effective prompt scheme is part of the identity fingerprint (D-02). — **Reversibility:** costly — a public Settings surface (generator-owned docs) and a vector-affecting behavior.
- **D-08:** **The prompt/role dimension enters the cache key only when a prompt is effective.** Cache bucket = `_cache_model_id()` + `|q@<prompt>` / `|d@<prompt>` when that role's prompt is set; when both prompts are `None`, keys are exactly today's value (Qwen3 byte-identical). A prompted query and an unprompted document of the same text therefore never collide. When the identity carries a revision/file hash, it also joins the bucket (a GGUF swapped at the same path must not read the old file's cached vectors), with the same suffix discipline so an absent revision leaves keys unchanged. — **Reversibility:** reversible.
- **D-09:** **`embedded_documents` is a transactional shadow, not a flag.** New table `embedded_documents(document_id TEXT PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE)`; a row means the document has ≥1 row in `document_embeddings`. Maintained in the SAME transaction as every embedding write/delete: `embed_cmd` batches, the watcher's inline embed, `delete_embeddings_by_document`, cleanup's orphan-embedding delete, and document/collection delete paths. It is rebuildable from `document_embeddings` at any time and never independently authoritative — staleness stays a derived signal. Orphan embedding rows (possible after a document delete until cleanup) never create shadow rows: every insert joins `documents`. — **Reversibility:** costly — a new schema surface every embedding writer must maintain; divergence is a correctness bug.
- **D-10:** **One-time backfill at schema init, reconciliation in cleanup/vacuum.** For legacy DBs, `SchemaManager` backfills the shadow from `document_embeddings` (existing documents only) in one idempotent pass gated by an `index_meta` version key (the Phase 20 D-06 backfill pattern), warning once; fresh DBs write the marker immediately at zero cost. `sif cleanup` and `sif index vacuum` reconcile (delete shadow rows whose embeddings are gone, insert missing rows for existing documents) inside their existing transactions. The shadow is created only when the vec0 table exists; a missing shadow/vec0 degrades to "no markers" exactly like today's `None` path. — **Reversibility:** costly — the version marker is a one-time migration contract.
- **D-11:** **Staleness reads switch to the shadow with byte-identical output.** `embedded_document_ids()` becomes an indexed read of the shadow; the display gate keeps today's semantics (empty set ⇒ no markers; vec0 absent ⇒ `None` ⇒ unmarked), the Phase 19 single-`enrich_results`-at-exit contract is untouched, and `sif status`'s vector-lag row (which shares the helper) becomes bounded too. Regression: marker output byte-identical on the existing fixture suite, including the legacy verbatim `/tmp` vs `/private/tmp` context fixture. — **Reversibility:** reversible.
- **D-12:** **Per-process/connection cache of the normalized context map; no schema change.** Cache the `normalize_path(target_id) → content` map (newest `updated_at` wins, preserving the current D-06 semantics) and invalidate on (a) any `ContextRepository` write in the same process and (b) a SQLite `PRAGMA data_version` change (another connection committed). Keep the no-SQL-prefilter rule and two-sided normalization verbatim; do NOT add a `normalized_target_id` column or backfill in this phase. Rationale: the write-side column touches the locked PROJECT.md Key Decision (realpath is not invertible; verbatim legacy rows must keep matching) and buys nothing at personal-KB context counts; the cache removes the per-query scan while preserving every existing row. — **Reversibility:** reversible.
- **D-13:** **`sif index vacuum` and `sif index backup` live on the `index` group; CLI only in this phase.** `sif index vacuum` (no args) prints before/after file sizes and reclaimed bytes. `sif index backup [--output PATH]` defaults to `<db_dir>/backups/<db-stem>-<UTC-timestamp>.db`, creates the default backup directory, refuses an existing target file, and always verifies the copy. Neither command registers an MCP tool in Phase 21; Phase 22 owns any MCP exposure (destructiveHint + target-path restriction per PITFALLS 11/19). — **Reversibility:** costly — command names and the default backup path are public surfaces behind the `make docs-generate` CI diff gate.
- **D-14:** **Vacuum/backup semantics: flock + busy timeout + checkpoint + no open transaction + explicit 2× disk check; busy errors are retryable.** Both commands take `index_lock` (`settings.lock_wait_timeout`), set a busy timeout on their own connection, and run outside `Database.transaction()`. Vacuum runs `PRAGMA wal_checkpoint(TRUNCATE)` first, then `VACUUM`. Backup uses the SQLite online backup API (not `VACUUM INTO`, never a file copy) and runs `PRAGMA integrity_check` on the copy before reporting success. Busy/locked failures become `click.ClickException` with retry wording (never a crash, never a partial success report). Vacuum prechecks `shutil.disk_usage` free bytes ≥ 2× (db + WAL) bytes and errors with required/available numbers; there is no `--skip-space-check` in this phase. Watch daemons and MCP hosts do NOT need to be stopped first: WAL readers coexist, and a conflict surfaces as the documented retryable error. — **Reversibility:** reversible — constraints can be relaxed additively.
- **D-15:** **Per-document atomicity with embedding outside the transaction.** Iterate documents; chunk, embed in model batches of `settings.batch_size` **outside any transaction**, then commit ONE short transaction per document (delete-before-insert chunks + embeddings, shadow row, document/collection stats). Memory is bounded by one document's chunks, and the write lock is held only for inserts. Resume is the existing exact-set skip (`get_all_embedded_chunk_ids` / `_needs_embedding`), so a re-run embeds exactly the missing documents. A document's partial state is never visible. — **Reversibility:** costly — the transaction/failure contract changes and partial progress becomes durable by design.
- **D-16:** **Document-local failures are isolated; systemic failures abort after committing prior work.** A document-local failure (parse/chunk/storage for that document) is recorded and the run continues. Systemic failures (model load, identity mismatch, batch-boundary sanity) abort the run after prior documents are committed. At the end, one failure report is raised outside any transaction, the exit code is non-zero, and successful work is durable — preserving CR-02's per-collection isolation and reporting contract. The "already embedded" skip and collection stats behavior stay. — **Reversibility:** costly — failure semantics are an operational contract.
- **D-17:** **Batch-boundary sanity is mandatory (qmd #897 lesson).** After each model batch: output count equals input count, every vector is finite (no NaN/Inf), dimensions match the identity, and when normalization is on each vector's L2 norm is 1 within tolerance (otherwise non-zero). A violation is systemic: the batch is not persisted, the run aborts after prior commits, and the error names the identity, batch position, and offending chunk. Empty/whitespace-only chunk text is rejected before embedding. — **Reversibility:** reversible.
- **D-18:** **One shared streaming embed service; the watcher routes through it.** Extract the chunk → embed → persist pipeline (sanity checks, shadow maintenance, short transaction) into a shared helper used by `embed_cmd`; the watcher's per-path inline embed reuses the same writer so completeness, sanity, and shadow maintenance cannot diverge. The watcher's trigger/debounce/depth semantics are unchanged. Phase 24's per-arm re-embed reuses the helper. — **Reversibility:** reversible.
- **D-19:** **The Qwen3 default path stays byte-identical.** With default settings (no prompt names, no identity mismatch), query vectors, document vectors, search output, and cache keys are byte-identical to pre-Phase-21 for the same corpus; the Phase 19/20 goldens and the SC1 hybrid golden must reproduce. The only new side effects are the identity `index_meta` row, the shadow table, and (on legacy DBs) the one-time backfill/assumed-identity warning. This is the locked precondition for Phase 23's baseline arm. — **Reversibility:** costly — the Harrier gate compares against this exact baseline.
- **D-20:** **Docs-generate gate and no new runtime dependencies.** New Settings fields (`query_prompt_name`, `document_prompt_name`) and new CLI commands (`index vacuum`, `index backup`) flow through `make docs-generate`; `docs/cli-reference.md` and `docs/configuration.md` are never hand-edited. No dependency is added in this phase. — **Reversibility:** reversible.

### Claude's Discretion

- Exact identity JSON key spelling, schema-version value, and fingerprint hash algorithm (must be deterministic and stable across processes).
- Whether the identity check exposes a cheap settings-only precheck at schema init and a full check after the model loads; the layering is the planner's as long as D-03's modes hold.
- Shadow-table column set beyond `document_id` (e.g. a write-generation/updated_at column), index shape, and whether reconciliation lives in a `database/maintenance.py` helper.
- Cache placement for D-12 (module-level keyed by connection vs an object threaded through the pipeline) and the exact `data_version` polling point.
- Maintenance command output layout, progress presentation, and whether `--json` is offered (follow existing output conventions; stdout must stay machine-clean when JSON is requested).
- Exact batch size for embed calls when `settings.batch_size` is not suitable per document, and whether document-level progress prints every N documents.
- How the identity is surfaced in `sif index status` (if at all) — Phase 24's `models status` is the consumer of record.
- Test fixture design for the byte-identical baseline, legacy-DB upgrade, mid-run failure, garbage-vector sanity, vacuum-under-concurrent-reader, and backup integrity.

### Deferred Ideas (OUT OF SCOPE)

- **Per-collection embedder identity / multiple vector spaces** — rejected now: one vec0 table means one KNN space and global search would compare unintelligible vectors across collections. Revisit only if per-collection vector spaces become a feature (would require storage redesign).
- **MCP exposure of vacuum/backup** — belongs to Phase 22 (`destructiveHint: true` + target-path restriction per PITFALLS 11/19).
- **`contexts.normalized_target_id` write-side column** — touches the locked PROJECT.md Key Decision (realpath is not invertible; verbatim legacy rows must keep matching); revisit only if context counts outgrow the cache.
- **`--skip-space-check` / `PRAGMA optimize` / `auto_vacuum` mode changes** — additive later if the conservative defaults prove annoying.
- **Scheduled or threshold-triggered auto-vacuum** — a new capability, not a clarification of this phase.
- **Embedder identity display in `sif status`** — Phase 24's `sif models status` is the designated consumer; adding a status row is additive later.
- **A dedicated `sif index embed --certify` command** — `--force` is the certification path; no separate command in this phase.

</user_constraints>

## Summary

Phase 21 is a **contract phase**, not a feature sweep: every locked decision in `21-CONTEXT.md` already names the mechanism. Research therefore focused on (a) the exact HEAD seams every mechanism must touch, (b) the SQLite/Python runtime facts that constrain vacuum/backup/streaming, and (c) the several places where the decisions collide with existing code or test fixtures and need an explicit implementation choice.

The most important findings:

1. **The identity record is feasible exactly as specified.** `_cache_model_id()` already produces `model_type:model_name[@api_base]` (`manager.py:153-163`) [VERIFIED: manager.py:153-163]; sentence-transformers 5.4.1 on this machine exposes `encode(..., prompt_name=...)` and resolves prompts from the model's `prompts` dict / `config_sentence_transformers.json` [VERIFIED: installed 5.4.1 source + cached Qwen config]; HuggingFace-hub loads expose `config._commit_hash`, while the default ModelScope local snapshot exposes `None` (both verified locally) [VERIFIED: local probes]; GGUF SHA-256 costs ~0.43 s for a 1.19 GB model file (~2.8 GB/s), so a per-process file hash is affordable [VERIFIED: local hash throughput probe].
2. **The shadow table must be maintained inside `VectorSearcher`'s three write methods** — `add_embedding`, `add_embeddings_batch`, `delete_embeddings_by_document` — because every production embedding write already flows through them inside a caller transaction [VERIFIED: vector.py:325-384 + the write-path audit in Pattern 3]. `VectorSearcher` can detect the shadow table once at construction (it already detects sqlite-vec the same way), so fixtures that build bare vec0 tables keep working.
3. **The contexts cache cannot live on the connection.** `sqlite3.Connection` has no `__dict__` and is not weak-referenceable [VERIFIED: local Python probe]. The workable design is a module-level, per-database-path cache with a dedicated sentinel connection for `PRAGMA data_version`, a module-level write generation bumped by `ContextRepository`, and bypass for `:memory:` databases.
4. **Streaming embed changes test-visible call shapes, not vector values.** The safe design delegates the no-prompt document path to the existing `embed` internals (same `encode` call, same cache bucket), while adding `embed_documents`/`embed_query` for prompt-bearing paths. Per-document commits replace the per-collection transaction, so ~30 tests that pin `manager.embed` call counts and `add_embeddings_batch` calls must be migrated deliberately.
5. **Vacuum/backup semantics verified against the official docs and the local runtime**: VACUUM is a write operation that fails inside an open transaction (including the same connection's implicit DML transaction), needs up to 2× the DB size, and succeeds alongside WAL readers [CITED: sqlite.org/lang_vacuum.html + local probes]; the Python online backup API silently overwrites an existing target and fails with `OperationalError: destination database is in use` when the target connection has an open transaction [CITED: sqlite.org/backup.html + local probe]; `PRAGMA integrity_check` returns `ok` on a vec0-bearing copy even without the extension loaded [VERIFIED: local probe].
6. **Four hidden divergences will break existing fixtures unless planned for**: raw `DELETE FROM document_embeddings` in `test_hybrid.py` (d4 staleness test) and `test_eval.py`, raw vec0 inserts in `test_staleness.py`, and the `test_drop_all_removes_index_meta...` assertion that only `metadata_values_version` exists in `index_meta` [VERIFIED: fixture audit at HEAD].

**Primary recommendation:** Implement in the locked order — identity/role-aware embed first, then the shadow + readers, then streaming embed, then maintenance — and treat the identity comparison as **field-wise with unknown-tolerance**, never a bare fingerprint equality, so a legacy assumed identity does not emit a false mismatch against the same model.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SCALE-01 | User can reclaim space safely via `sif index vacuum` (flock + quiesce + no open txn + checkpoint + 2× disk check; retryable busy errors; target paths restricted). | Maintenance design below: exact VACUUM/checkpoint semantics verified; `index_lock` + busy timeout integration; disk precheck math; CLI-only target. |
| SCALE-02 | User can back up the index safely (SQLite online backup API + integrity_check). | Online-backup call shape, target-transaction restriction, existing-target refusal, verification on a vec0 copy, default path conventions. |
| SCALE-03 | User can embed large corpora without giant transactions (streaming embed batches; embed outside txn; short per-batch commits; resumable; CR-02 failure reporting preserved; batch-boundary sanity). | Shared streaming writer design, per-document transaction, failure taxonomy, sanity thresholds, resume via `_needs_embedding`, watcher routing, test migration list. |
| CORR-06 | User gets fast searches without per-query full scans (bounded staleness/context reads via transactional `embedded_documents` shadow reconciled in cleanup/vacuum; staleness derived; contexts verbatim two-sided normalization). | Shadow DDL + write-path audit + backfill/reconcile + reader change; contexts cache design with `sqlite3.Connection` constraints and `PRAGMA data_version`. |
| EMB-01 | User is protected from silent bad model swaps (persisted `index_meta` embedder identity; 3 dim-guard sites consolidated; legacy warn-once + backfill; mismatch → fail-fast embed / warn+mark search). | Identity JSON schema, fingerprint, revision resolution, mode matrix, legacy assumed/certify flow, guard consolidation. |
| EMB-02 | User gets correct query-vs-document embeddings (role-aware embed surface with `prompt_name`; prompt dimension in cache key; Qwen3 default byte-identical until the Harrier gate). | Role methods on embedders/manager, prompt scheme resolution (Settings + known table), cache bucket suffix discipline, call-site audit, no-prompt delegation to preserve the default path. |

</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Embedder identity construction/check | `embedding/identity.py` (infrastructure) | `database/schema.py` (init), CLI/MCP/watcher boundaries | One owner for the payload, fingerprint, schema read, and mode-aware comparison; callers only translate the outcome to their error/warn surface. |
| Identity persistence | `index_meta` (database) | `IndexMetaRepository` | Regular table readable without sqlite-vec; one global key per index (D-01). |
| Role-aware embedding | `embedding/` (embedder + manager) | `search/` call sites via a tiny helper | Prompt mechanics belong to the backend; call sites only choose query vs document role. |
| Prompt-scheme defaults | `embedding/prompts.py` (new) | `Settings` override | Known-model table + Settings resolution must happen before model construction. |
| Embedding cache segmentation | `embedding/manager.py` + `embedding/cache.py` | — | The manager owns buckets; the cache table is unchanged. |
| Streaming chunk→embed→persist | `indexing/embed_writer.py` (new) | `cli/commands/index.py`, `indexing/watcher.py` | One writer so sanity/shadow/identity cannot diverge (D-18). |
| `embedded_documents` shadow maintenance | `search/vector.py` write methods | `database/schema.py` (DDL/backfill), `database/maintenance.py` (reconcile) | Every production vector write already funnels through the three `VectorSearcher` methods. |
| Staleness reads | `search/staleness.py` | `sif status` helper | Derived signal stays in the search layer; status uses the same shadow. |
| Contexts cache | `search/context_attach.py` (new cache helper) | `database/repositories.py` (write generation) | The cache is a read optimization internal to attachment; repository writes invalidate. |
| Vacuum/backup/reconcile | `database/maintenance.py` (new) | `cli/commands/index.py` (presentation) | SQL operations and invariant checks stay presentation-free; Click renders. |
| Byte-identical baseline | Test suite + goldens | — | D-19 is a test contract, not a runtime mode. |

## Standard Stack

No new packages. This phase is built from the Python standard library and already-locked dependencies. Versions verified in this session:

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `sqlite3` | Python 3.13.9 / SQLite 3.51.0 locally; CI 3.10–3.13 | VACUUM, online backup API, `PRAGMA data_version`, `PRAGMA wal_checkpoint`, `PRAGMA integrity_check` | `Connection.backup` added in 3.7; all required pragmas exist on every supported Python. [VERIFIED: local runtime probe] |
| `sqlite-vec` | `>=0.1.9` (core dep) | vec0 table; DELETE by metadata; shadow-table integrity_check | Already locked; no change. [VERIFIED: pyproject.toml:33 + local vec0 probe] |
| `sentence-transformers` | 5.4.1 (locked) | `encode(..., prompt_name=...)`; `prompts` dict; `Pooling.pooling_mode` | `prompt_name` present in the installed `encode` signature; `_resolve_prompt` raises a clear ValueError on an unknown name. [VERIFIED: installed 5.4.1 source + local model probe] |
| `transformers` | locked floor | `config._commit_hash` for HF-hub revision provenance | Populated for an HF-hub load; `None` for the default ModelScope local snapshot. [VERIFIED: local probes on all-MiniLM-L6-v2 and the cached Qwen3 dir] |
| `click` / `rich` | existing | `index vacuum`/`index backup` CLI | Existing convention; generated docs. |
| Pydantic Settings | 2.x | two new `str \| None` fields | Existing pattern. |

**Installation:** none. D-20 forbids new runtime dependencies; the v1.2 pair (`mcp`, `rapidfuzz`) already landed.

**Version verification:** `python3` 3.13.9, `sqlite3.sqlite_version` 3.51.0, `sentence_transformers.__version__` 5.4.1 on this machine; CI covers 3.10–3.13 via the existing matrix. No package version is being changed.

## Package Legitimacy Audit

Not applicable: **this phase installs no packages** (D-20). Every mechanism is stdlib or existing locked dependencies. The legitimacy gate and registry probes are therefore not run; there is nothing to remove or flag.

## Architecture Patterns

### Current Code Seams (verified at HEAD `39e8234`)

This is the audit the planner should use as the change map. Values are quoted verbatim from the files read this session.

| Capability | Seam (file:line) | Verbatim value / behavior | Planning implication |
|---|---|---|---|
| Canonical cache model id | `src/sif/embedding/manager.py:153-163` | `model_id = f"{self._config.model_type.value}:{self._config.model_name}"` then `if self._config.api_base: model_id = f"{model_id}@{self._config.api_base}"` [VERIFIED: manager.py:153-163] | Extract `format_cache_model_id()` and reuse it as the identity base; do not change the method's output. |
| Cache table PK | `src/sif/embedding/cache.py:69-77` | `PRIMARY KEY (content_hash, model_id)` [VERIFIED: cache.py:69-77] | No schema change; the manager passes an extended bucket string. |
| `index_meta` DDL | `src/sif/database/schema.py:270-275` | `CREATE TABLE IF NOT EXISTS index_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)`; docstring says "embedder identity in Phase 21" [VERIFIED: schema.py:262-275] | Identity + shadow backfill marker go here; no schema change. |
| vec0 DDL / width guard | `src/sif/database/schema.py:581-616` | `embedding FLOAT[{self.embedding_dim}]`; mismatch raises `RuntimeError` "Embedding dimension mismatch: database has FLOAT[...]" [VERIFIED: schema.py:592-616] | Keep the message; delegate the `FLOAT[n]` read to the identity module. |
| `IndexMetaRepository` | `src/sif/database/repositories.py:662-685` | `get(key) -> str \| None`; `set(key, value)` uses `INSERT OR REPLACE` on `index_meta(key, value)` [VERIFIED: repositories.py:674-685] | Identity/backfill marker CRUD; all callers own the transaction. |
| `Database.init_schema` | `src/sif/database/database.py:31-44` | `if embedding_dim is None: ... get_settings().embedding_dim`; constructs `SchemaManager(self.connection, embedding_dim=embedding_dim)` [VERIFIED: database.py:31-44] | Add an optional settings-only identity so legacy backfill can run at init; injected-dimension callers stay settings-free. |
| `DocumentRepository.delete` | `src/sif/database/repositories.py:256-265` | deletes chunks, then `DELETE FROM documents WHERE id = ?`; **never touches `document_embeddings`** [VERIFIED: repositories.py:256-265] | Landmine: shadow rows cascade (FK ON), orphan vectors remain until cleanup; never treat the shadow as authoritative. |
| `DocumentRepository.delete_by_collection` | `src/sif/database/repositories.py:267-284` | deletes chunks per doc, then `DELETE FROM documents WHERE collection_id = ?`; no embedding purge [VERIFIED: repositories.py:267-284] | `collection remove` does the vector purge explicitly before calling this. |
| Vector write methods | `src/sif/search/vector.py:325-384` | `add_embedding` → `_add_embedding_vec`; `add_embeddings_batch` → `executemany`; `delete_embeddings_by_document` → `DELETE FROM document_embeddings WHERE document_id = ?` [VERIFIED: vector.py:325-384] | The three shadow maintenance points; callers own transactions. |
| Completeness read | `src/sif/search/vector.py:398-417` | `SELECT document_id, chunk_id FROM document_embeddings`, iterated one row at a time; NULL chunk ids skipped [VERIFIED: vector.py:398-417] | Resume/skip unchanged; still a vec0 scan per collection, not per query. |
| Staleness read | `src/sif/search/staleness.py:37-52` | `cursor = db.execute("SELECT document_id FROM document_embeddings")`; `except sqlite3.OperationalError: return None` [VERIFIED: staleness.py:37-52] | Replace with the shadow; keep `None` for a missing table and the empty-set display gate. |
| Enrichment owner | `src/sif/search/context_attach.py:66-85` | `return mark_vector_staleness(db, attach_path_contexts(db, results))` [VERIFIED: context_attach.py:66-85] | Single attach exit; add an optional forced-stale flag only when a mismatch is detected. |
| Contexts scan | `src/sif/search/context_attach.py:54-62` | `SELECT target_id, content FROM contexts WHERE context_type = 'path' ORDER BY updated_at`; no SQL prefilter [VERIFIED: context_attach.py:54-62] | Keep verbatim; wrap in the cache. |
| Embedder protocol | `src/sif/core/models.py:403-417` | `embed`, `embed_batch`, `dimension` only [VERIFIED: core/models.py:403-417] | Do not change; extend concrete classes with role methods. |
| Stale marker field | `src/sif/core/models.py:294-319` | `vectors_stale: bool = False` [VERIFIED: core/models.py:312] | Reuse; no new field. |
| `embed_cmd` transaction | `src/sif/cli/commands/index.py:332-381` | `embedded_by_doc = vector_searcher.get_all_embedded_chunk_ids()` then `with db.connection:` covers the whole collection; `manager.embed(chunk_texts)` inside it [VERIFIED: index.py:332-377] | This is the giant transaction to replace with per-document commits. |
| Completeness predicate | `src/sif/cli/commands/index.py:180-187` | `return force or not live_chunk_ids or live_chunk_ids != embedded_chunk_ids` [VERIFIED: index.py:180-187] | Reuse verbatim for resume. |
| Inline dim guard | `src/sif/cli/commands/index.py:246-261` | regex `FLOAT\[(\d+)\]` on `sqlite_master.sql`; error "Model '...' produces N-dim embeddings but the index stores M-dim vectors" [VERIFIED: index.py:250-261] | Delegate the read; keep the message. |
| Watcher embed leg | `src/sif/indexing/watcher.py:295-310` | chunks → `manager.embed([...])` with no transaction → `with self._conn:` chunk rows + `add_embeddings_batch` [VERIFIED: watcher.py:295-310] | Route through the shared writer; keep embed-outside-txn. |
| Watcher schema dim | `src/sif/indexing/watcher.py:318-326` | `SELECT sql ... name='document_embeddings'`; regex `FLOAT\[(\d+)\]` [VERIFIED: watcher.py:318-326] | Replace with the shared read. |
| Cleanup orphan delete | `src/sif/cli/main.py:244-258` | `DELETE FROM document_embeddings WHERE document_id NOT IN (SELECT id FROM documents)`, `OperationalError` swallowed [VERIFIED: main.py:244-258] | Add reconcile in the same transaction. |
| Status vector lag | `src/sif/cli/main.py:141-164` | uses `embedded_document_ids(conn)` then iterates `SELECT id FROM documents` [VERIFIED: main.py:141-164] | Switch to the shadow (set or anti-join); output byte-identical. |
| MCP init dimension | `src/sif/mcp/backend.py:115` | `db.init_schema(embedding_dim=self.settings.embedding_dim)` [VERIFIED: backend.py:115] | Pass the backend's settings-only identity so a legacy DB is assumed-marked on MCP first open. |
| MCP raw embedder | `src/sif/mcp/backend.py:119-135` | `factory.create_model(...)` in a `try/except`; failure warns and disables vectors [VERIFIED: backend.py:119-135] | Build the full identity after load; pass a search-mode check closure to the pipeline. |
| Query embeds | `src/sif/search/hybrid.py:103, 273, 280` | `query_embedding = self.embedder.embed(query)`; vector route `embed(parsed_query)`; HyDE route `embed(hyde_doc)` [VERIFIED: hybrid.py:100-104, 269-282] | Query role via a type-aware helper; fall back to `embed` for doubles. |
| Expansion embeds | `src/sif/search/expansion.py:82, 110` | `embed_single(query)`; `embed(candidate_list)` [VERIFIED: expansion.py:75-115] | Query role (`embed_query` / `embed_queries`). |
| vsearch embed | `src/sif/cli/commands/search.py:758` | `query_embedding = manager.embed_single(query)` [VERIFIED: search.py:757-758] | Query role; then mark on mismatch. |
| Bench query embed | `src/sif/cli/commands/bench.py:67-96` | `CachedEmbedder.embed` memoizes `inner.embed(text)` [VERIFIED: bench.py:67-96] | Make it role-aware with a `(role, text)` memo key; `BenchHarness` (bench.py:54-64) needs an `identity_check` field because it bundles only `db`/`embedder`/`embedding_dim` today. |
| Eval pipeline | `src/sif/cli/commands/eval.py:647-651, 703` | `SearchPipeline(..., embedder=embedder, ...)`; `embedder = manager.model` [VERIFIED: eval.py:647-651, 703] | Pass an identity check closure into the hoisted pipeline. |
| WAL checkpoint recipe | `src/sif/database/factory.py:45` | `WAL_CHECKPOINT_TRUNCATE = "PRAGMA wal_checkpoint(TRUNCATE)"` [VERIFIED: factory.py:45] | Reuse in vacuum. |
| Flock semantics | `src/sif/database/locking.py:42-98` | "Deadline expiry is NOT an error: the block runs without the kernel lock" (D-02 availability-over-exclusion) [VERIFIED: locking.py:52-56] | Vacuum cannot assume the flock is exclusive; SQLite's write lock + busy errors are the real guard. |
| Settings defaults | `src/sif/config/settings.py:110-152` | `model_name="Qwen/Qwen3-Embedding-0.6B"`, `embedding_dim=1024`, `batch_size=32`, `model_type="modelscope"`, `api_base=None` [VERIFIED: settings.py:115-152] | The default path is ModelScope Qwen3 1024-dim; revision resolves to `None`. |
| DB path default | `src/sif/config/settings.py:391-400` | `data_dir / "sif.db"` [VERIFIED: settings.py:391-400] | Backup default dir = `db_path.parent / "backups"`. |

### Pattern 1: Embedder identity record (EMB-01, D-01/D-02/D-04)

**What:** one JSON value under `index_meta['embedder.identity']` describing the vector space, written in the same transaction as the first vector write, checked at every vector-touching boundary.

**Recommended payload (schema version 1, snake_case):**

```json
{
  "schema": 1,
  "cache_model_id": "modelscope:Qwen/Qwen3-Embedding-0.6B",
  "model_name": "Qwen/Qwen3-Embedding-0.6B",
  "model_type": "modelscope",
  "api_base": null,
  "dimension": 1024,
  "pooling": "last_token",
  "normalized": true,
  "query_prompt": null,
  "document_prompt": null,
  "prompt_supported": true,
  "revision": null,
  "source": "verified",
  "fingerprint": "sha256:<64 hex>"
}
```

- `cache_model_id`: exactly `format_cache_model_id(model_type, model_name, api_base)` reproducing `manager.py:153-163`. [VERIFIED: manager.py:153-163]
- `pooling`: map ST `Pooling.pooling_mode` as observed: `"lasttoken"` → `"last_token"`, `"mean"` → `"mean"`, `"cls"` → `"cls"`, `"max"` → `"max"`; tuple/list → `"mixed:<a>+<b>"`; absent/unreadable → `"unknown"`. Verified Qwen3's local `1_Pooling/config.json` loads as `pooling_mode='lasttoken'`; the installed `Pooling.POOLING_MODES` are `('cls', 'max', 'mean', 'mean_sqrt_len_tokens', 'weightedmean', 'lasttoken')`. [VERIFIED: local ST 5.4.1 probe]
- `normalized`: `true` for every current SIF backend. Verbatim: `_encode_kwargs` returns `{"normalize_embeddings": True}`; `LlamaCppEmbedder.embed` runs `norm = np.linalg.norm(vector); if norm > 0: vector = vector / norm`; `OpenAIEmbedder._normalize` is the same shape. [VERIFIED: embedder.py:92-97, 217-223, 565-573]
- `revision`: `"sha256:<hex>"` for GGUF (hash the model file once per embedder instance), the transformers `config._commit_hash` for HF-hub ST loads, `null` for the default ModelScope local snapshot and OpenAI. Verified: HF-hub all-MiniLM-L6-v2 `_commit_hash` is a 40-hex string; the cached ModelScope Qwen3 snapshot's `AutoConfig._commit_hash` is `None`. [VERIFIED: local probes]
- `source`: `"verified"` or `"legacy-assumed"`, deliberately **excluded from the fingerprint**.
- `fingerprint`: SHA-256 over canonical JSON of every field above except `fingerprint` and `source`: `json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`. Deterministic across processes; test by building twice and by a subprocess if desired.

**Mode matrix (recommended implementation of D-03/D-04/D-05):**

| Mode | Stored vectors? | Identity missing | Match | Same-dim mismatch | Dimension mismatch |
|---|---|---|---|---|---|
| `init` | any | write `legacy-assumed` + warn once if vectors exist | width-only | width-only (never fail; search warns later) | fail with the existing `RuntimeError` width message |
| `embed` | no (D-02: identity checks do not apply) | allowed; overwrite identity as `verified` on first vector write | allowed; keep identity (identical) | allowed; overwrite the stale identity as `verified` on first vector write | **fail fast** with the schema width message (`FLOAT[n]` cannot store the current dimension) |
| `embed` | yes | write `legacy-assumed` + warn once; then allowed | allowed; keep `assumed` unless a full `--force` certifies | **fail fast** | **fail fast** |
| `search` | no | no warning, no mark | no warning, no mark | no warning, no mark | no warning, no mark |
| `search` | yes | `unknown`: debug log only (SchemaManager normally wrote assumed at open) | no warning, no mark | warn once per process + mark all results `vectors_stale=True` | warn + degrade/error (see Open Questions) |

**D-02 no-stored-vectors branch (authoritative):** when `document_embeddings` holds no row (or the table is absent), identity checks do not apply in any mode. A stale identity row — including one written by a vacuous unfiltered `--force` certification — never blocks an `embed`: the index accepts any embedder, and the first successful vector write overwrites the identity as `verified`. The one exception is the schema width guard: vectors of a dimension the stored `FLOAT[n]` cannot hold still fail fast. `search` on such an index neither warns nor marks.

**Comparison is field-wise, not fingerprint equality.** This is the single most important implementation detail beyond the CONTEXT text:

```python
def identity_matches(stored, current) -> bool:
    if stored.cache_model_id != current.cache_model_id: return False
    if stored.dimension != current.dimension: return False
    if stored.normalized != current.normalized: return False
    if stored.pooling != "unknown" and current.pooling != "unknown" \
       and stored.pooling != current.pooling: return False
    if stored.revision and current.revision and stored.revision != current.revision: return False
    if stored.query_prompt != current.query_prompt: return False
    if stored.document_prompt != current.document_prompt: return False
    return True
```

Why: a settings-only assumed identity records `pooling: "unknown"`, `revision: null`; the same model loaded later records `pooling: "last_token"`, `revision: null` for ModelScope. A fingerprint-only comparison would emit a **false mismatch warning on every search of a legacy DB** and mark every result stale. Unknown-vs-known is not evidence of a swap; known-vs-known difference is. This preserves D-04's "search is never blocked on an assumed identity" while still detecting a real `cache_model_id` swap against the assumed value.

**Write timing (D-02):** the identity row is written inside the same transaction as the first successful vector write. The streaming writer receives a `write_identity: bool` decided by the command:

- `had_vectors = has_vectors(conn)` at run start (`SELECT 1 FROM document_embeddings LIMIT 1`; vec0 is the authority).
- If `not had_vectors`: the first document transaction writes the full current identity with `source: "verified"` (this includes the "all vectors deleted" reset).
- If `had_vectors` and the stored source is `verified`: never rewrite.
- If `had_vectors` and the stored source is `legacy-assumed`: keep assumed during the run; the command certifies only after a complete, unfiltered, zero-failure `--force` run.
- If `had_vectors` and identity missing: `ensure_legacy_identity` writes assumed first (inside the flock / schema init), then proceeds.

**Certification (D-04):** `embed_cmd` rewrites the identity as `source: "verified"` with the full current fields only when `force and collection is None and not failed_documents and not failed_collections`. A scoped `--force` or any failure keeps assumed. A fresh/empty index's first write is verified by definition. A full unfiltered zero-failure `--force` against an index with no documents certifies vacuously; because the index still has zero stored vectors, D-02 keeps accepting any later embedder and that embedder's first vector write overwrites the vacuous identity.

**Legacy write location:** `SchemaManager.create_all` calls `ensure_legacy_identity(conn, source_identity, dimension=schema_embedding_dim(conn) or embedding_dim)` after vector tables exist. `Database.init_schema(embedding_dim=None)` builds a settings-only identity; when `embedding_dim` is injected (MCP), the backend passes its own settings-only identity so Phase 19's "no `get_settings()` when injected" contract holds. [VERIFIED: database.py:31-44]

**Layering note:** `embedding/identity.py` needs `IndexMetaRepository` and the schema needs `schema_embedding_dim`. To avoid a module-import cycle through `sif.embedding.__init__` (which imports the manager/factory), import the identity helper **inside** the `SchemaManager` methods (`from sif.embedding.identity import ...  # noqa: PLC0415`) and import `IndexMetaRepository` lazily inside the identity functions. This matches the repository's established deferred-import convention and keeps `database.schema` importable on its own.

**Search-entry wiring (D-03):** the check must run only on routes that actually touch vectors, once per pipeline, and the "warn once per process" state belongs in `identity.py`, not the callers.

- `SearchPipeline.__init__(..., identity_check: Callable[[sqlite3.Connection], bool] | None = None)`; the closure is built by the caller from the current identity (`lambda conn: check_identity(conn, current, mode="search").untrusted`).
- In `SearchPipeline.search`, evaluate the closure lazily on the first VECTOR/HYDE/hybrid exit that has an embedder; cache the boolean on the pipeline instance. The BM25 exit never calls it (BM25-only commands neither warn nor mark).
- When the boolean is true, pass `vectors_untrusted=True` to `enrich_results`; when false, call the existing two-argument form so the Phase 19 golden/mocks are untouched.
- `HYBRID` with `embedder is None` is BM25-only (the vector leg is skipped at `hybrid.py:100-104`) and must not trigger the check.
- Direct `sif search vsearch` owns its own check (it does not construct a pipeline) and passes the flag to its `enrich_results` call.
- MCP (`SearchBackend.hybrid_search`), `eval`, and `bench` pass closures; `BenchHarness` needs the extra field, and eval's hoisted `_search_fn` closure should capture it.
- The wording/idempotence lives in `warn_identity_mismatch_once(stored, current)`: a module-level set keyed by `(stored_fingerprint, current_fingerprint)` ensures one stderr warning per process; `reset_identity_state()` clears it for tests.

### Pattern 2: Role-aware embed + cache buckets (EMB-02, D-06/D-07/D-08)

**Model layer (concrete classes only; protocol unchanged):**

- `SentenceTransformerEmbedder` / `ModelScopeEmbedder` gain constructor parameters `query_prompt_name`, `document_prompt_name` and methods:
  - `embed_query(text)`: no prompt → `self.embed(text)` (exact current path); prompt → `self.model.encode(text, prompt_name=..., **self._encode_kwargs())`.
  - `embed_queries(texts)`: no prompt → `self.embed_batch(texts)`; prompt → `encode(texts, prompt_name=..., ...)`.
  - `embed_documents(texts)`: no document prompt → `self.embed_batch(texts)`; prompt → `encode(texts, prompt_name=..., ...)`.
  - Properties: `pooling_mode` (from the `Pooling` child module), `revision` (commit hash or `sha256:<file>`), `query_prompt_name`, `document_prompt_name`.
  - Validate at load: if a prompt name is set and not in `self.model.prompts`, raise `ValueError` listing the available keys (ST's `_resolve_prompt` does this at encode time; validating at construction gives the CLI's "Failed to load embedding model" wrapper). [VERIFIED: installed ST 5.4.1 `_resolve_prompt` source]
- `LlamaCppEmbedder` / `OpenAIEmbedder` define no role methods; the type-aware helper falls back to `embed`/`embed_batch`, and the identity records `prompt_supported: false`. Warn once if Settings configure a prompt on an unsupported backend.
- `SimpleEmbedder` / `ConceptEmbedder` / test doubles: unchanged.

**Manager layer:**

- `embed_query(text) -> list[float]`, `embed_queries(texts) -> EmbeddingResponse`, `embed_documents(texts) -> EmbeddingResponse`.
- Internal role path shares `_compute_embeddings` with a `bucket: str` and a `model_call`:
  - `bucket = _cache_model_id()`; if the identity's `revision` is known, append `|rev@<revision>`; then for the role, append `|q@<prompt>` or `|d@<prompt>` only when that role's prompt is effective.
  - No revision and no prompt ⇒ the bucket is exactly `_cache_model_id()` (D-08/D-19). The default ModelScope Qwen3 path has `revision=None`, prompts None ⇒ byte-identical cache keys.
  - `embed`/`embed_single` stay role-less and keep exactly `_cache_model_id()`; they remain the probe/compat surface. D-08's revision suffix applies on the role paths (document/query embeddings), which is where a swapped GGUF must not read the old file's cache.
- **Cache safety (new, tied to qmd #897):** validate vectors before `cache.set` (count, finite, dimension, and L2 norm ≈ 1 — SIF always normalizes) and validate cached vectors on read (finite, dimension); an invalid cached entry is treated as a miss and overwritten. This prevents a bad batch from poisoning the cache and prevents a previously poisoned entry from failing forever. The writer's identity-aware check remains the second line (it also names the chunk/identity).
- `get_identity()` convenience returns a cached `EmbedderIdentity` (invalidated on load/unload). Call sites that already have settings may use the pure `build_identity(...)` instead; the builder is defensive against test doubles.

**Prompt-scheme resolution (D-07):**

```python
_PROMPT_SUPPORTED_TYPES = {"sentence_transformers", "modelscope"}
_KNOWN_PROMPT_SCHEMES = {
    "microsoft/harrier-oss-v1-0.6b": ("web_search_query", None),
}

def resolve_prompt_scheme(source, model_name: str, model_type: str) -> PromptScheme:
    # unsupported backend -> (None, None, supported=False)
    # Settings value (str) wins; "" explicitly disables; unknown models default to (None, None)
```

Harrier's card requires `prompt_name="web_search_query"` on queries and none on documents; `default_prompt_name` must never be set (it would apply the query instruction to documents). [CITED: huggingface.co/microsoft/harrier-oss-v1-0.6b via .planning/research/STACK.md:107-117] Qwen3's own `config_sentence_transformers.json` also defines `query`/`document` prompts, but SIF intentionally has no table entry for it, so the default path stays unchanged. [VERIFIED: cached Qwen3 config_sentence_transformers.json]

**Call-site audit (all query-side sites must use the query role):**

| Site | Current call | New call |
|---|---|---|
| `search/hybrid.py:103` (hybrid BM25+vector) | `embedder.embed(query)` | type-aware `embed_query` helper |
| `search/hybrid.py:273` (`vec:`) | `embedder.embed(parsed_query)` | helper |
| `search/hybrid.py:280` (`hyde:`) | `embedder.embed(hyde_doc)` | helper (query role per D-06) |
| `search/expansion.py:82` | `manager.embed_single(query)` | `manager.embed_query(query)` |
| `search/expansion.py:110` | `manager.embed(candidate_list)` | `manager.embed_queries(candidate_list)` |
| `cli/commands/search.py:758` (`vsearch`) | `manager.embed_single(query)` | `manager.embed_query(query)` |
| `cli/commands/search.py:1068`, `cli/commands/index.py:243`, `cli/commands/bench.py:115`, `cli/commands/eval.py:207` | `embed_single("probe")` | unchanged (dimension probe, role-less) |
| `cli/commands/index.py:356` (`embed_cmd`) | `manager.embed(chunk_texts)` | `manager.embed_documents(...)` per batch |
| `indexing/watcher.py:298` | `manager.embed([...])` | `manager.embed_documents(...)` via the shared writer |
| `cli/commands/bench.py:67-96` | `CachedEmbedder.embed` | role-aware methods with `(role, text)` memo |
| `search/rerank.py:167,179` | reranker model `embed` | out of scope (different model) |

**Type-aware helper (preserves test doubles):**

```python
def embed_query(embedder: Embedder, text: str) -> list[float]:
    method = getattr(type(embedder), "embed_query", None)
    if method is not None:
        return embedder.embed_query(text)  # concrete ST/manager/CachedEmbedder
    return embedder.embed(text)            # ConceptEmbedder, MagicMock, protocol-only doubles
```

Using `type(embedder)` (not `getattr(embedder, ...)`) is deliberate: `MagicMock` auto-creates instance attributes, so an instance-level check would route every mock through a magic `embed_query` and break the existing test suite. Real role-aware classes define the method on the class.

### Pattern 3: `embedded_documents` shadow + bounded staleness (CORR-06, D-09/D-10/D-11)

**DDL (recommended; minimal column set):**

```sql
CREATE TABLE IF NOT EXISTS embedded_documents (
    document_id TEXT PRIMARY KEY,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
)
```

- One row per embedded document; PK gives O(log N) lookups and a covering read for status.
- `PRAGMA foreign_keys = ON` is set by `create_connection` (`factory.py:65`), so document deletes cascade. Raw test connections may not enable FKs; the explicit delete/reconcile paths cover that. [VERIFIED: factory.py:64-65]
- No `updated_at`/generation column: nothing needs it; fewer invariants.

**Write-path audit (every production vector write):**

| Path | Transaction owner | Shadow action |
|---|---|---|
| `VectorSearcher.add_embedding` / `_add_embedding_vec` | caller (`embed_cmd` per-doc, watcher per-doc, tests) | `INSERT OR IGNORE INTO embedded_documents(document_id) SELECT id FROM documents WHERE id = ?` |
| `VectorSearcher.add_embeddings_batch` | caller | same, once per distinct `document_id` in the batch |
| `VectorSearcher.delete_embeddings_by_document` | caller | `DELETE FROM embedded_documents WHERE document_id = ?` |
| `embed_cmd` delete-before-insert | per-document `with conn:` | delete + re-add via the two methods |
| watcher inline embed | per-document `with self._conn:` | same |
| `IncrementalIndexer` update/remove purge | per-file `with self._conn:` | delete via the method |
| `collection remove` purge loop | `db.transaction()` | delete via the method; documents cascade |
| `cleanup` orphan embedding delete | `db.transaction()` | reconcile after (delete orphans, insert missing) |
| `vacuum` | short `with conn:` before checkpoint | reconcile |

**Implementation detail:** `VectorSearcher.__init__` detects the shadow once and stores a plain Python bool (a `Connection` cannot hold attributes — verified: `AttributeError ... no __dict__`). When absent (bare vec0 fixtures), the maintenance methods no-op exactly like the existing `_vec_available` degradation. The identity of the document is resolved by the `SELECT id FROM documents` join, so an orphan vector insert never creates a shadow row (D-09).

**Backfill (D-10), following the Phase 20 D-06 template:**

- Marker: `index_meta['embedded_documents_version'] = "1"`.
- Create the shadow **only when vec0 exists**; on a fresh DB write the marker immediately.
- On a legacy DB: `DELETE FROM embedded_documents` (derived table; makes a resumed pass clean), then `INSERT OR IGNORE INTO embedded_documents(document_id) SELECT document_id FROM document_embeddings WHERE document_id IN (SELECT id FROM documents)`; write the marker only after the pass; warn once if rows were inserted. The template's contract is verbatim: "The marker is written **only after** the loop completes" [VERIFIED: schema.py:286-288].
- **Force a backfill when the table did not exist before this call**, even if the marker is present: a dropped/recreated shadow with a surviving marker would otherwise stay silently empty. (Add this detection; the Phase 20 template gates only on the marker.)
- Per-item short transactions (or one transaction with a final marker commit) so an interrupted pass resumes; exceptions propagate out of `create_all`, matching `_backfill_metadata_values`. [VERIFIED: schema.py:277-316]

**Reconcile helper (cleanup + vacuum):**

```sql
-- delete shadow rows whose document is gone or whose embeddings are gone
DELETE FROM embedded_documents
WHERE document_id NOT IN (SELECT id FROM documents)
   OR document_id NOT IN (SELECT document_id FROM document_embeddings);
-- insert missing rows for existing documents that still have embeddings
INSERT OR IGNORE INTO embedded_documents(document_id)
SELECT DISTINCT de.document_id
FROM document_embeddings de JOIN documents d ON d.id = de.document_id;
```

Maintenance paths only; both may scan. The insert joins `documents`, so a deleted document is never resurrected (the specific D-09/D-10 test).

**Reader change (recommended, stronger than D-11's minimum):**

- Keep `embedded_document_ids(db) -> set[str] | None` as the set form (`SELECT document_id FROM embedded_documents`; `OperationalError` → `None`). It is bounded by document count and used by status/compat.
- For **per-query marking**, do **not** materialize the whole set. Use one display-gate probe plus indexed per-result lookups:

```python
def mark_vector_staleness(db, results):
    if not results: return results
    try:
        any_embedded = db.execute("SELECT 1 FROM embedded_documents LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        return results                      # vec0/shadow absent -> unmarked
    if any_embedded is None:
        return results                      # display gate: no embeddings at all
    for result in results:
        row = db.execute(
            "SELECT 1 FROM embedded_documents WHERE document_id = ?",
            (result.document_id,),
        ).fetchone()
        result.vectors_stale = row is None
    return results
```

This is O(limit · log N), not O(N) per query. The old batching rule in `staleness.py` exists because **vec0 metadata columns are unindexed**; the shadow PK is an ordinary index, so per-result probes are the correct shape here. Update the docstring to distinguish the two. `sif status` should use an anti-join (`SELECT COUNT(*) FROM documents d WHERE NOT EXISTS (...)`) and the same gate text instead of iterating documents; output stays byte-identical.

**Enrichment contract:** `enrich_results` gains an optional keyword `vectors_untrusted: bool = False`; when true it marks all results stale after the normal staleness pass. The pipeline/direct entry points pass it **only when true**, so existing two-arg monkeypatched `enrich_results` tests keep working.

### Pattern 4: Contexts cache (CORR-06, D-12)

**Why a connection-keyed cache is impossible:** `sqlite3.Connection` has no `__dict__` and cannot be weak-referenced:

```
AttributeError: 'sqlite3.Connection' object has no attribute 'foo' and no __dict__ for setting new attributes
TypeError: cannot create weak reference to 'sqlite3.Connection' object
```
[VERIFIED: local Python 3.13.9 probe]

**Recommended design (module-level, per resolved DB path):**

```python
@dataclass
class _ContextCacheEntry:
    sentinel: sqlite3.Connection     # own connection, read-only use
    data_version: int                # sentinel's PRAGMA data_version at build
    generation: int                  # process ContextRepository write generation
    inode: tuple[int, int]           # st_dev, st_ino of the main DB file
    context_map: dict[str, str]      # normalize_path(target_id) -> content
```

- **Key:** the resolved main DB path from `PRAGMA database_list` (`[(0, 'main', '/abs/path')]` for a file DB; `''` for `:memory:` — verified locally). Bypass the cache entirely for `:memory:` (no cross-connection visibility).
- **Invalidate on:**
  1. `ContextRepository.create/update/update_target/delete/delete_orphaned_paths` — bump a module-level counter (put it in `database/repositories.py`, which search may import; avoids database→search). Rolled-back writes may cause an unnecessary rebuild, which is safe.
  2. Sentinel `PRAGMA data_version` differs from the stored value. Official semantics: the value changes when **another connection** commits; it is unchanged for commits on the same connection. [CITED: sqlite.org/pragma.html#pragma_data_version] A dedicated sentinel therefore sees every commit from the search connections, including same-process ones.
  3. `(st_dev, st_ino)` changed (backup restore / file replacement) → close and reopen the sentinel.
- **Build:** on the *calling* connection, run the unchanged constant query `SELECT target_id, content FROM contexts WHERE context_type = 'path' ORDER BY updated_at`; normalize both sides on read as today; dict last-wins preserves newest-`updated_at` semantics. [VERIFIED: context_attach.py:54-62]
- **Sentinel:** plain `sqlite3.connect(str(path), timeout=5.0, check_same_thread=False)`; `PRAGMA busy_timeout=5000`; no sqlite-vec, no WAL switch, no writes. One per DB path per process, created lazily on the second attach call; guarded by a `threading.Lock`.
- **Lifecycle:** `atexit` closes sentinels; expose `reset_context_cache()` and call it from an autouse conftest fixture (the existing logger-reset culture).
- **Failure policy:** if the sentinel cannot be opened, bypass the cache (fresh scan) with a debug log. A DB on a read-only/odd filesystem still works.
- **Tradeoff:** `PRAGMA data_version` is DB-wide, so any commit (including query-log/chunk/embed writes) invalidates the map. That is conservative and correct; at personal-KB context counts the rebuild is one small query.

**Do not** add `contexts.normalized_target_id`, do not SQL-prefilter, do not change newest-wins.

### Pattern 5: Streaming embed service (SCALE-03, D-15/D-16/D-17/D-18)

**Shared writer (new module, e.g. `src/sif/indexing/embed_writer.py`):**

```python
class StreamingEmbedWriter:
    def __init__(self, conn, manager, chunker, vector_searcher, identity,
                 *, batch_size: int, write_identity: bool) -> None: ...

    def embed_document(self, doc: Document) -> int:
        chunks = [c for c in self._chunker.chunk(doc.content) if c.content.strip()]
        if not chunks:
            return 0
        vectors: list[list[float]] = []
        for batch in _batches(chunks, self._batch_size):
            response = self._manager.embed_documents([c.content for c in batch])
            validate_batch(response.embeddings, batch, self._identity, doc.path)
            vectors.extend(response.embeddings)
        with self._conn:                       # ONE short transaction
            self._chunk_repo.delete_by_document(doc.id)
            self._searcher.delete_embeddings_by_document(doc.id)   # deletes shadow row
            for sequence, chunk in enumerate(chunks):
                chunk.document_id, chunk.sequence = doc.id, sequence
                self._chunk_repo.create(chunk)
            self._searcher.add_embeddings_batch(
                [(c.id, doc.id, c.id, v) for c, v in zip(chunks, vectors, strict=True)]
            )
            if self._write_identity:           # first vector write on an empty index
                write_identity(self._conn, self._identity)
                self._write_identity = False
        return len(chunks)
```

- **Embedding is outside every transaction**; the manager's role path writes only to the separate embedding-cache DB.
- **Delete-before-insert** is preserved per document; the watcher's already-purged documents are a no-op delete.
- **Memory** is bounded by one document's chunks plus one batch.
- **Resume** is the existing `_needs_embedding` exact-set skip in `embed_cmd`; the writer itself is idempotent.
- **Batch boundaries:** slice by `settings.batch_size` before calling the manager, so the sanity check runs on true batch boundaries even when a document has more chunks than the batch size.

**Failure taxonomy (D-16):**

| Failure | Classification | Behavior |
|---|---|---|
| Parse/chunk error for one document | local | record `(collection, path, error)`; continue |
| SQLite storage error for one document's transaction | local (except busy/locked) | transaction rolls back; continue |
| `sqlite3.OperationalError` "locked"/"busy" | systemic/environmental | abort; retryable ClickException wording |
| Model load / embedding backend error | systemic | abort |
| Identity mismatch | systemic | abort (checked before the loop) |
| Batch sanity violation | systemic | abort; do not persist that batch or that document |

Prior documents remain committed in every abort case (per-document transactions). The final report is raised **outside** any transaction, the exit code is non-zero, and the existing "Embedding failed for N collection(s)" summary is retained for collection-level failures, with per-document details on stderr/console.

**Sanity check (D-17):**

```python
NORM_TOLERANCE = 1e-3

def validate_batch(vectors, chunks, identity, document_path):
    if len(vectors) != len(chunks):
        raise SystemicEmbedError(...)          # count
    for position, (vector, chunk) in enumerate(zip(vectors, chunks, strict=True)):
        if len(vector) != identity.dimension:
            raise SystemicEmbedError(...)      # dimension
        if not all(math.isfinite(value) for value in vector):
            raise SystemicEmbedError(...)      # NaN/Inf
        norm = math.sqrt(sum(value * value for value in vector))
        if identity.normalized:
            if abs(norm - 1.0) > NORM_TOLERANCE:
                raise SystemicEmbedError(...)  # normalization
        elif norm <= 0.0:
            raise SystemicEmbedError(...)      # non-normalized zero vector
```

The error names the identity fingerprint, the document path, the batch position, and the offending chunk id/sequence. Empty/whitespace-only chunks are filtered before embedding.

**Embedding-cache poisoning guard:** validate vectors inside `EmbeddingManager._compute_embeddings` before `cache.set` (count/finite/dimension/norm) and validate cached vectors on read (finite/dimension). Without this, a garbage batch gets cached and re-fails forever (or worse, silently serves garbage). The writer's check runs too; the manager's check is the cache-safety boundary, and the norm check belongs there because a structural failure must not leave the failing batch in the cache.

**Watcher routing (D-18):** `_EmbedSession.ensure_ready` builds the manager and identity, runs `ensure_legacy_identity`, `check_identity(mode="embed")`, and constructs the shared writer. A mismatch/systemic sanity failure emits one `error` event and disables embedding for the session (the existing LIVE-05 fail-soft contract); BM25 freshness continues. Per-path local failures keep the existing `_pending_retry` re-queue.

**CR-02 preservation:** collection-level isolation still holds because every prior document/collection commit is durable; the final report is outside transactions; counts count committed chunks only. Collection stats should be recomputed once per collection in a short transaction (an O(N) SQL count) rather than per document, to avoid O(N²); this is a deliberate refinement of D-15's "document/collection stats" wording.

### Pattern 6: Maintenance commands (SCALE-01/02, D-13/D-14)

**Module:** `src/sif/database/maintenance.py` (presentation-free), CLI presentation in `cli/commands/index.py`.

**Vacuum algorithm (verified semantics):**

1. Command opens/closes an initialized DB first (`open_initialized_database`) so schema migration/backfill runs; then `vacuum_index(db_path, settings)`.
2. `with index_lock(db_path, settings.lock_wait_timeout, on_wait=...)`: open a dedicated connection via `create_connection`; set `PRAGMA busy_timeout = max(1, int(settings.lock_wait_timeout * 1000))`; ensure `conn.in_transaction is False`.
3. Reconcile the shadow in a short `with conn:` transaction.
4. Measure `before = db.st_size + wal.st_size` (if present).
5. `PRAGMA wal_checkpoint(TRUNCATE)`: returns `(busy, log_pages, checkpointed_pages)`. `busy == 1` means it was blocked (the busy handler expired); treat as retryable and do not proceed. [CITED: sqlite.org/pragma.html#pragma_wal_checkpoint]
6. Disk precheck: `required = 2 * (db_size + wal_size)`; `shutil.disk_usage(db_path.parent).free`; if insufficient, raise with required/available numbers.
7. `conn.execute("VACUUM")` outside any transaction. Official semantics: VACUUM is a write operation, fails with an open transaction or an unfinalized statement on the same connection, requires up to 2× the DB size in free space, and uses the WAL like any other transaction. [CITED: sqlite.org/lang_vacuum.html]
8. Best-effort final `wal_checkpoint(TRUNCATE)`; a busy final checkpoint is a warning, not a failed vacuum (the rewrite already committed).
9. Measure `after`; return `(before, after, reclaimed)`.

Hidden constraints verified locally: VACUUM succeeds with idle WAL readers and even a reader holding an open read transaction; it fails with `database is locked` while another connection holds a write transaction; it succeeds after a `fetchone()`-only checkpoint (statements are finalized); an unfinalized cursor on the same connection did not block it in this probe (still close cursors defensively). [VERIFIED: local SQLite 3.51.0 probes]

**Backup algorithm (verified semantics):**

1. Refuse a target that exists, is a symlink, or has stale `-wal`/`-shm` sidecars; refuse `output` equal to the DB path or its sidecar/lock names. Default: `<db_path.parent>/backups/<stem>-<UTC %Y%m%dT%H%M%SZ>.db`; create the default dir (mode 0700).
2. `with index_lock(...)`: open source via `create_connection`, target via `sqlite3.connect(str(output))` (a fresh target connection has no transaction). Python's `backup(target, *, pages=-1, progress=None, name='main', sleep=0.250)` works even with concurrent clients; a positive `pages` copies in chunks. Use `pages=-1` for personal-scale DBs (single-step snapshot); do not rely on a return value (it returns `None` here). [CITED: docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup]
3. **Target must not have an open transaction**: a pending DML on the target raises `OperationalError: destination database is in use` (verified locally). Commit/close first.
4. Verify the copy with `PRAGMA integrity_check` on a plain connection; require exactly `[("ok",)]`. Verified: works on a vec0-bearing copy without loading the extension; the copy contains the committed rows. [VERIFIED: local probe]
5. `os.chmod(output, 0o600)` (backups contain full document text); warn if chmod fails.
6. On a backup-API/OS failure, remove the just-created target (it did not exist before) and raise; never report partial success. On an integrity-verification failure, keep the copy for forensics, name its path and the integrity output, and exit non-zero — the caller must never mistake it for a valid backup.

The online backup API replaces the target's contents and produces a consistent snapshot; writes to the source during the copy are usually detected and the backup restarts, and with `pages=-1` there is no sleeping window. [CITED: sqlite.org/backup.html]

**Busy/mapping:** `database is locked`/`database is busy`/busy checkpoint → a `MaintenanceBusyError` translated to `click.ClickException` with retry wording. Other SQLite/OS errors → `click.ClickException` with the cause. The flock's "proceed unlocked after the deadline" semantics (D-02) mean the flock is not a hard mutex; SQLite's write lock and the busy timeout are the real serialization. [VERIFIED: locking.py:55-92]

### Pattern 7: Legacy migration ordering and markers

`SchemaManager.create_all` recommended order (only the relevant tail):

```
_create_vector_tables()                 # existing; width guard preserved
_create_embedded_documents_table()      # no-op without vec0
_create_indexes()
_backfill_metadata_values()             # existing Phase 20
_backfill_embedded_documents()          # marker-gated; force when table was absent
_ensure_legacy_identity(initial_identity)  # settings-only; warn once
self.db.commit()
```

- `drop_all` must drop `embedded_documents` **before** `documents`. The current list begins `"document_embeddings", "chunks_fts", "documents_fts_v", "documents_fts", "document_chunks", ...` and reaches `"documents"` before `"index_meta"` [VERIFIED: schema.py:660-673]; add `embedded_documents` near the front. [VERIFIED: schema.py:658-678]
- Fresh DB with vec0: the shadow marker is written immediately; no identity row (no vectors). This means the existing test asserting `index_meta` holds only `metadata_values_version` **will fail on a vec0-enabled connection** — update it to allow `embedded_documents_version` (see test migration list).
- A missing vec0 means no shadow and no marker; if sqlite-vec is installed later, the next open creates and backfills.

### Suggested plan decomposition

The dependency graph is mostly a chain (identity → role-aware cache buckets → streaming writer → maintenance/reconcile), with the shadow table shared by two plans. A safe six-plan split:

| Plan | Scope | Depends on | Why this order |
|---|---|---|---|
| 21-01 | Settings prompt fields + `embedding/prompts.py` + `embedding/identity.py` + dim-guard consolidation + manager/embedder role methods + cache buckets + identity tests | — | Every later plan consumes the identity and role surface; D-19 goldens can be pinned immediately. |
| 21-02 | `embedded_documents` DDL + backfill/marker + `VectorSearcher` shadow maintenance + `staleness.py`/`status` reader changes + tests | — (schema-only; coordinate `schema.py` edits with 21-01) | The shadow is the read contract for 21-04/21-05; it does not need the identity. |
| 21-03 | Contexts cache + `ContextRepository` write generation + conftest reset + tests | — | Independent read optimization; small and self-contained. |
| 21-04 | Shared streaming writer + `embed_cmd` rewrite + watcher routing + sanity/cache validation + failure taxonomy + test migration | 21-01, 21-02 | The writer needs the identity and shadow; the test migration is the largest mechanical task. |
| 21-05 | `database/maintenance.py` vacuum/backup/reconcile + CLI commands + cleanup reconcile + command tests | 21-02 (reconcile) | Vacuum/backup are independent of streaming but the reconcile helper lands here. |
| 21-06 | Byte-identical/legacy/garbage/concurrency verification, docs-generate, architecture doc update, full quality gate | all | Final gate: goldens + `make docs-generate` + ruff/format/ty/pytest. |

Parallelism note: 21-01/21-02/21-03 can overlap in time only if their `schema.py`/`conftest.py`/test-file ownership is partitioned; otherwise run 21-02 after 21-01 or merge their schema edits into one plan to avoid rebase churn. 21-04 is the critical path.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Cross-process consistency of the contexts cache | File mtime polling, inotify, a background thread | `PRAGMA data_version` on a sentinel connection + `ContextRepository` write generation | Official, per-connection, detects other connections/processes; no new deps. [CITED: sqlite.org/pragma.html#pragma_data_version] |
| Online backup | `shutil.copy` of the DB, `VACUUM INTO` | `sqlite3.Connection.backup` | File copy of a live WAL DB is corrupt-by-construction; the online API is WAL-safe and restarts on concurrent writes. [CITED: sqlite.org/backup.html] |
| Backup integrity | Custom row counting | `PRAGMA integrity_check` on the copy | Official full check; returns `ok` on vec0 copies. |
| Prompt resolution | Reimplementing instruction templates | ST `encode(..., prompt_name=...)` + the model's own `prompts` dict | The model card/config owns the exact instruction text; duplicating it drifts. [VERIFIED: installed ST 5.4.1] |
| Model revision | Parsing ModelScope's `.msc` pickle | HF `config._commit_hash`; GGUF SHA-256; `null` otherwise | `.msc` is an untrusted pickle (code-execution risk) and private; do not unpickle. [VERIFIED: local `.msc` inspection] |
| Vector-space identity | A dedicated `embedder_id` column on every vector row | One global `index_meta` JSON + fingerprint | One vec0 table = one space; per-row duplication is unmaintainable. Locked D-01. |
| Streaming resume | A separate "in-progress" journal | The existing exact-set `_needs_embedding` skip / chunk-id sets | Already correct and self-healing: `return force or not live_chunk_ids or live_chunk_ids != embedded_chunk_ids`. [VERIFIED: index.py:187] |
| Vacuum quiescence | Killing watch daemons / MCP hosts | Flock + busy timeout + retryable error | WAL readers coexist; locked D-14. |

## Runtime State Inventory

This phase is schema-additive, not a rename, but it does migrate stored state. The relevant surfaces:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Existing `document_embeddings` rows (vec0) with no `embedded_documents` shadow and no `embedder.identity` row; existing `index_meta['convention:<id>']` rows must be preserved. | One-time shadow backfill + identity `legacy-assumed` write at first open; markers `embedded_documents_version` and `embedder.identity`; no data rewrite. |
| Live service config | Long-lived watch daemons and MCP hosts may hold open connections across the upgrade; they use the schema through `create_connection` and will see the new tables on their next open/statement. No external service config embeds an embedder identity. | None beyond the detection-gated `create_all`; no restart requirement. Vacuum/backup do not require stopping them (D-14). |
| OS-registered state | None. | None. |
| Secrets/env vars | New optional env vars `SIF_QUERY_PROMPT_NAME`, `SIF_DOCUMENT_PROMPT_NAME`; no renamed secrets or keys. | Document via generated `docs/configuration.md`. |
| Build artifacts / installed packages | None carry a model identity; the embedding cache DB keeps its existing `(content_hash, model_id)` schema, but its bucket strings change only when a prompt or revision is effective (default ModelScope Qwen3 unchanged). | No reinstall; a user switching to an HF/GGUF model gets new cache buckets and re-embeds once (expected). |
| Deferred/derived state | `embedded_documents` is fully rebuildable from `document_embeddings` + `documents`; the identity is not derivable after the fact (that is why legacy DBs are assumed). | Reconcile command path: `sif cleanup` / `sif index vacuum`. |

## Common Pitfalls

### Pitfall 1: Fingerprint equality produces false mismatches on legacy assumed identities
**What goes wrong:** an assumed identity has `pooling: "unknown"`, `revision: null`; the same model loaded later has `last_token`/commit-hash fields. Comparing fingerprints warns and marks every result stale forever on a legacy DB.
**Why it happens:** the fingerprint covers best-effort fields; absence is not difference.
**How to avoid:** field-wise comparison with unknown-tolerance (Pattern 1); fingerprint for display/cache, not the mismatch predicate.
**Warning signs:** a warning on every search with the same `cache_model_id`; `vectors_stale=True` on every result after upgrading a legacy index.

### Pitfall 2: Raw SQL writers bypass the shadow
**What goes wrong:** tests or scripts execute `DELETE FROM document_embeddings` / raw inserts; the shadow diverges, so markers freeze or vanish.
**Why it happens:** the shadow is maintained only inside `VectorSearcher`'s three methods; vec0 has no triggers on virtual tables.
**How to avoid:** make `VectorSearcher` the only production writer; update fixtures to use `add_embedding(s)`/`delete_embeddings_by_document` or to seed/delete the shadow alongside raw SQL; reconcile in cleanup/vacuum; add a shadow-parity test helper.
**Warning signs:** a document with no embedding rows is unmarked; a deleted document stays marked; `embedded_documents` count ≠ distinct vector documents.
**Known fixtures:** `tests/unit/search/test_hybrid.py:565` (d4 delete), `tests/unit/search/test_staleness.py` (`_seed_embedding`), `tests/unit/cli/test_eval.py` (`_delete_embeddings`), `tests/integration/test_embed_idempotency.py:312` (partial delete; healed by re-embed but worth reconciling).

### Pitfall 3: `sqlite3.Connection` cannot hold cache state
**What goes wrong:** `conn._context_cache = ...` raises `AttributeError`; `weakref.ref(conn)` raises `TypeError`.
**Why it happens:** the C connection type has no `__dict__` and is not weak-referenceable.
**How to avoid:** the module-level per-path cache + sentinel design; bypass for `:memory:`.
**Warning signs:** a cache implementation that silently falls back to scanning every query (no speedup) or leaks a dict keyed by `id(conn)`.

### Pitfall 4: `PRAGMA data_version` does not change for the same connection's commits
**What goes wrong:** a cache keyed only on `data_version` serves stale contexts after the search connection itself writes contexts.
**Why it happens:** official semantics: unchanged for commits on the same connection.
**How to avoid:** the sentinel is a **different** connection, so it sees all other connections' commits; additionally bump the module generation from `ContextRepository`. Never use the same connection for build and invalidation.
**Warning signs:** `context add` followed by a search on the same connection returns the old map.

### Pitfall 5: Vacuum inside an implicit transaction
**What goes wrong:** `VACUUM` raises `OperationalError: cannot VACUUM from within a transaction` when the connection has pending DML (Python's legacy `isolation_level` opens a transaction on INSERT/UPDATE/DELETE).
**Why it happens:** VACUUM is a write operation and refuses an open transaction.
**How to avoid:** run maintenance on a fresh connection; commit before VACUUM; never call it inside `Database.transaction()` or `with conn:` DML; close/finalize cursors defensively.
**Warning signs:** the error text above; vacuum succeeding only on an empty/fresh connection.

### Pitfall 6: Backup target with an open transaction
**What goes wrong:** `source.backup(target)` raises `OperationalError: destination database is in use` if the target connection has uncommitted DML.
**Why it happens:** CPython's `backup` requires a usable destination; the probe confirmed the failure.
**How to avoid:** use a fresh target connection; never write to it before the backup; verify with a separate connection after closing.
**Warning signs:** the error above on a target file created moments earlier.

### Pitfall 7: Disk check underestimates or measures the wrong filesystem
**What goes wrong:** VACUUM fails with "database or disk is full" after the check passed; the temp copy may land on a different filesystem (`SQLITE_TMPDIR`) than the DB.
**Why it happens:** VACUUM's temporary database location is not necessarily the DB directory; the docs say up to 2× the DB size.
**How to avoid:** use the conservative 2× (db + WAL) check as locked; document `SQLITE_TMPDIR`; map disk errors to a remedy-bearing ClickException.
**Warning signs:** disk-full errors on large DBs; free space on the DB volume but not the temp volume.

### Pitfall 8: Flock is not a mutex after the deadline
**What goes wrong:** two maintenance commands run concurrently because `index_lock` proceeds unlocked after `lock_wait_timeout`.
**Why it happens:** D-02 availability-over-exclusion is the shipped lock contract (not an error).
**How to avoid:** rely on SQLite's write lock + busy timeout; translate busy to the documented retryable error; keep all maintenance writes inside one connection/transaction scope.
**Warning signs:** concurrent vacuum/backup both proceeding; intermittent busy errors.

### Pitfall 9: Garbage vectors are cached before the sanity check
**What goes wrong:** a NaN/Inf/dimension-corrupt batch is stored in the embedding cache; later runs keep reading it or fail forever.
**Why it happens:** `_compute_embeddings` caches immediately after `embed_batch`.
**How to avoid:** validate before `cache.set` and validate on cache read (treat invalid as a miss); the writer's identity-aware check is the second line.
**Warning signs:** repeated sanity failures for the same text; cache rows with non-finite JSON (`NaN`/`Infinity`).

### Pitfall 10: Batch sanity checks do not prove semantic quality
**What goes wrong:** the qmd #897 failure can produce finite, unit-norm, correct-dimension garbage, which the D-17 checks pass.
**Why it happens:** the mandated checks are structural, not semantic.
**How to avoid:** respect chunk/model token limits (existing chunker + `max_seq_length`), keep the checks as the locked floor, and let Phase 23's bench measure quality. Do not add a semantic canary in this phase.
**Warning signs:** quality drops with no structural failure after a backend/model change.

### Pitfall 11: Test fixtures that assert the old transaction shape
**What goes wrong:** ~30 tests pin `manager.embed` call counts, one `add_embeddings_batch` per collection, and the old `index_meta` contents.
**Why it happens:** streaming changes call shapes; the shadow adds markers.
**How to avoid:** budget a test-migration task; preserve vector byte-identity (not call shapes); update fixtures to the authoritative writer/reconciler; add a shadow-parity helper.
**Warning signs:** failures in `test_index.py`, `test_embed_idempotency.py`, `test_watcher.py`, `test_watch_cmd.py`, `test_hybrid.py:565`, `test_staleness.py`, `test_schema.py:604`.

### Pitfall 12: `DocumentRepository.delete` leaves orphan vectors
**What goes wrong:** deleting a document without purging embeddings leaves vec0 rows; the shadow row cascades (FK ON) but the vector remains until cleanup.
**Why it happens:** vec0 cannot carry the documents FK cascade.
**How to avoid:** keep the existing purge-before-delete order in the incremental/collection paths; never let the shadow imply "no orphan vectors"; reconcile in cleanup/vacuum.
**Warning signs:** KNN returns rows whose JOIN drops them; cleanup reports orphan embeddings.

## Code Examples

### Identity dataclass + canonical fingerprint

```python
# New: src/sif/embedding/identity.py
IDENTITY_KEY = "embedder.identity"
IDENTITY_SCHEMA_VERSION = 1

@dataclass(frozen=True)
class EmbedderIdentity:
    schema_version: int
    cache_model_id: str
    model_name: str
    model_type: str
    api_base: str | None
    dimension: int
    pooling: str
    normalized: bool
    query_prompt: str | None
    document_prompt: str | None
    prompt_supported: bool
    revision: str | None
    source: str = "verified"

    def _payload(self) -> dict[str, object]:
        return {
            "schema": self.schema_version,
            "cache_model_id": self.cache_model_id,
            "model_name": self.model_name,
            "model_type": self.model_type,
            "api_base": self.api_base,
            "dimension": self.dimension,
            "pooling": self.pooling,
            "normalized": self.normalized,
            "query_prompt": self.query_prompt,
            "document_prompt": self.document_prompt,
            "prompt_supported": self.prompt_supported,
            "revision": self.revision,
        }

    def fingerprint(self) -> str:
        canonical = json.dumps(
            self._payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def to_json(self) -> str:
        return json.dumps(
            {**self._payload(), "source": self.source, "fingerprint": self.fingerprint()},
            sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        )
```

### `_cache_model_id` reuse (behavior unchanged)

```python
# embedding/identity.py
def format_cache_model_id(model_type: str, model_name: str, api_base: str | None) -> str:
    model_id = f"{model_type}:{model_name}"
    if api_base:
        model_id = f"{model_id}@{api_base}"
    return model_id

# embedding/manager.py (unchanged output, one spelling)
def _cache_model_id(self) -> str:
    return format_cache_model_id(
        self._config.model_type.value, self._config.model_name, self._config.api_base
    )
```

### Shadow DDL + reconcile

```python
# database/schema.py
def _create_embedded_documents_table(self) -> None:
    if schema_embedding_dim(self.db) is None:   # vec0 absent
        return
    self.db.execute("""
        CREATE TABLE IF NOT EXISTS embedded_documents (
            document_id TEXT PRIMARY KEY,
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
        )
    """)

# database/maintenance.py
def reconcile_embedded_documents(conn: sqlite3.Connection) -> tuple[int, int]:
    if not _table_exists(conn, "embedded_documents"):
        return 0, 0
    deleted = conn.execute("""
        DELETE FROM embedded_documents
        WHERE document_id NOT IN (SELECT id FROM documents)
           OR document_id NOT IN (SELECT document_id FROM document_embeddings)
    """).rowcount
    inserted = conn.execute("""
        INSERT OR IGNORE INTO embedded_documents(document_id)
        SELECT DISTINCT de.document_id
        FROM document_embeddings de JOIN documents d ON d.id = de.document_id
    """).rowcount
    return deleted, inserted
```

### Vector write shadow maintenance

```python
# search/vector.py
def add_embeddings_batch(self, items):
    ...
    if self._shadow_available:
        self.db.executemany(
            "INSERT OR IGNORE INTO embedded_documents(document_id) "
            "SELECT id FROM documents WHERE id = ?",
            [(doc_id,) for doc_id in {item[1] for item in items}],
        )

def delete_embeddings_by_document(self, document_id):
    cursor = self.db.execute(
        "DELETE FROM document_embeddings WHERE document_id = ?", (document_id,)
    )
    if self._shadow_available:
        self.db.execute(
            "DELETE FROM embedded_documents WHERE document_id = ?", (document_id,)
        )
    return cursor.rowcount
```

### Vacuum/backup call shapes (verified)

```python
# database/maintenance.py
row = conn.execute(WAL_CHECKPOINT_TRUNCATE).fetchone()      # (busy, log_pages, checkpointed)
if row[0] != 0:
    raise MaintenanceBusyError("checkpoint blocked; retry after active readers finish")
conn.execute("VACUUM")                                       # outside any transaction

src = create_connection(db_path)
dst = sqlite3.connect(str(output))                           # fresh target: no open txn
try:
    src.backup(dst)                                          # returns None; pages=-1 default
finally:
    dst.close(); src.close()
ok, detail = _verify_backup(output)                          # PRAGMA integrity_check == [('ok',)]
```

### Role-aware no-prompt delegation (byte-identical default)

```python
# embedding/manager.py — sketch; _compute_embeddings is refactored to take
# (texts, *, model_id, model_call) while embed()/embed_single() pass today's
# _cache_model_id()/embed_batch and therefore keep their exact behavior.
def embed_documents(self, texts: list[str]) -> EmbeddingResponse:
    return self._embed_role(texts, role="document")

def _embed_role(self, texts, *, role: str) -> EmbeddingResponse:
    identity = self.get_identity()                 # cached; built once per load
    prompt = identity.query_prompt if role == "query" else identity.document_prompt
    if prompt is None:
        model_call = self._model.embed_batch       # exactly today's encode call
    else:
        model_call = (
            self._model.embed_queries if role == "query" else self._model.embed_documents
        )
    return self._compute_embeddings(
        texts, model_id=self._cache_bucket(role), model_call=model_call
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| Width-only `FLOAT[n]` guard | Model identity (id + revision/hash + pooling + prompt scheme) with a persisted `index_meta` record | This phase | Same-dim swaps become detectable; legacy DBs warn/assume; Phase 23 gate is valid. |
| Role-less `embed` | Query/document role methods with `prompt_name` | This phase | Harrier can be evaluated with its mandatory query instruction; cache keys cannot collide across roles. |
| Per-query `SELECT document_id FROM document_embeddings` | Bounded shadow reads (indexed lookups / anti-join) | This phase | Removes the O(vectors) scan from every search and status. |
| Per-query full `contexts` scan | Process-wide normalized-map cache with `data_version` + write-generation invalidation | This phase | Removes the per-query scan without a schema change or SQL prefilter. |
| Per-collection giant embed transactions | Per-document short commits, embedding outside transactions, batch sanity | This phase | Bounded memory/lock hold; resumable; garbage-vector guard. |
| No vacuum/backup | `sif index vacuum` + `sif index backup` | This phase | Safe space reclamation and a verified copy; CLI only until Phase 22. |

**Deprecated/outdated:** a persisted per-document `vectors_stale` flag (rejected — derived signal); a `contexts.normalized_target_id` column (deferred); `VACUUM INTO`/file copy for backup (rejected — online API); `default_prompt_name` (never — it applies the query instruction to documents).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Harrier's ST config exposes `prompt_name="web_search_query"` and documents take no prompt. | Pattern 2 | Phase 23 arm is crippled; mitigate by validating at load and failing loudly. (Research cites the model card; not re-fetched this session.) |
| A2 | ModelScope local snapshots expose no usable revision; `revision: null` is honest. | Pattern 1 | A re-downloaded model at the same name cannot be detected. Verified `_commit_hash is None` locally; the `.msc` manifest is an untrusted pickle and is not parsed. |
| A3 | An assumed identity should not be overwritten by a normal embed run; only a full `--force` certifies. | Pattern 1 | A legacy DB keeps untrusted provenance longer; the remedy is explicit. Locked D-04. |
| A4 | A same-dim verified mismatch on `vsearch` may not be able to "still return results"; hybrid degrades to BM25. | Pattern 1 / Open Q2 | UX inconsistency for vector-only search; decide at plan time. |
| A5 | Collection stats can be recomputed once per collection instead of per document. | Pattern 5 | Slight deviation from D-15's literal wording; avoids O(N²) and preserves output. |
| A6 | Empty/whitespace-only chunks are skipped (not a document failure) and renumbered. | Pattern 5 | A whitespace-only document is retried each run via `_needs_embedding` (chunkless contract); harmless but noisy. |
| A7 | The context-cache sentinel is acceptable (one extra idle connection per process per DB). | Pattern 4 | A long-lived MCP process holds an extra read connection; WAL readers coexist. |
| A8 | `PRAGMA integrity_check` on a vec0 copy is sufficient without loading the extension. | Pattern 6 | Verified locally; the check reports `ok` and the copy's rows open correctly. |
| A9 | Backup files should be mode 0600 (personal notes) even though D-13 does not mandate it. | Pattern 6 | A stricter default than the current DB file; reversible. |
| A10 | A full `--force` with zero failures certifies even if the index has no documents. | Pattern 1 | A vacuous certification on an empty index; harmless because no stored vectors exist, so D-02 still accepts any later embedder and the first later write overwrites the identity. |

## Open Questions (RESOLVED)

All five recommendations below are adopted by the phase plans: Q1 → 21-07 Task 3 (fresh-index switch documented; `--force` never bypasses a mismatch), Q2 → 21-04 Task 1 (vsearch fails, hybrid degrades), Q3 → 21-01 residual risk and 21-08 assumed identity, Q4 → 21-01 Task 1 / 21-02 Task 2, Q5 → 21-06 Tasks 1 and 3 (plain-text output, no `--json`).

1. **How does a user intentionally switch embedders?** (RESOLVED — 21-07 Task 3)
   - What we know: D-03 fails fast on any mismatch, including with `--force`, and the remedy is "restore the stored model"; D-02 says deleting all vectors resets the contract, but there is no command that deletes all vectors.
   - What's unclear: the intended migration path for an intentional permanent switch (vs the Harrier gate, which uses isolated indexes).
   - Recommendation: document "use a fresh index (`--index`) or delete the DB/vectors" for Phase 21; revisit a `--replace-identity`/switch surface in Phase 24. Do not silently let `--force` bypass the check.
2. **What should `sif search vsearch` do on a dimension mismatch (model dim ≠ schema dim)?** (RESOLVED — 21-04 Task 1)
   - What we know: D-03 says search warns + marks and still returns results; a vector-only command cannot return vector results if the KNN vector length is wrong.
   - Recommendation: warn + fail with a remedy-bearing ClickException for `vsearch`; for hybrid `query`, warn + degrade to BM25 + mark all results stale. Document the asymmetry.
3. **Should an assumed identity be refreshed with the loaded model's known fields (pooling/revision) on the first embed run?** (RESOLVED — 21-01 residual risk; 21-08 task 1)
   - What we know: the assumed record's unknown fields cause a permanent blind spot until `--force`; refreshing would improve later detection but mixes provenance.
   - Recommendation: keep assumed as written; `--force` is the certification path. Record the residual risk in docs.
4. **Exact identity/backfill key spelling and fingerprint display format.** (RESOLVED — 21-01 Task 1; 21-02 Task 2)
   - Recommendation: `embedder.identity`, `embedded_documents_version = "1"`, fingerprint `sha256:<16-hex-prefix>` in messages (full hash stored).
5. **Should `index vacuum`/`index backup` offer `--json`?** (RESOLVED — 21-06 Tasks 1 and 3; plain text in Phase 21)
   - Recommendation: plain text in Phase 21; add `--json` additively when Phase 22/MCP consumers need it.

## Environment Availability

Versions in the table below were probed in this session on the primary working directory host [VERIFIED: local `python3` import/version probes]; CI versions come from `.github/workflows` and `pyproject.toml`.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | whole phase | ✓ | 3.13.9 local; CI 3.10–3.13 | — |
| SQLite (stdlib) | VACUUM, backup, pragmas, shadow | ✓ | 3.51.0 local | CI system SQLite; all APIs are ancient |
| sqlite-vec | vec0, shadow tests | ✓ (core dep) | 0.1.9+ | Tests skip when unavailable (existing discipline) |
| sentence-transformers | prompt_name/role tests | ✓ | 5.4.1 | Mocked ST in tests; no model download needed |
| transformers | `_commit_hash` | ✓ | locked floor | Revision `null` if unavailable |
| `make`/docs scripts | docs-generate gate | ✓ | Makefile | Run the two Python scripts directly |
| `fcntl` | index_lock/vacuum | ✓ macOS/Linux; ✗ Windows | — | Lock degrades to a warning; SQLite still protects integrity |
| Optional model backends (openai/modelscope/llama-cpp) | identity variants | ✓ | openai 2.36.0, modelscope 1.36.0, llama-cpp-python 0.3.20 | Tests use fakes; no download required |

**Missing dependencies with no fallback:** none — no new dependencies are introduced (D-20).

**Missing dependencies with fallback:** Windows `fcntl` (documented degradation); sqlite-vec in a stripped environment (vector tests skip).

## Validation Architecture

Nyquist validation is enabled (`workflow.nyquist_validation: true` in `.planning/config.json`).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing; pytest-cov, pytest-asyncio) |
| Config file | `pyproject.toml` (`testpaths = ["tests"]`, `addopts` includes coverage, `fail_under = 90`) |
| Quick run command | `pytest tests/unit/<area>/test_<file>.py -x --no-cov` |
| Full suite command | `pytest` (plus `ruff check src tests`, `ruff format --check src tests`, `ty check src/sif`) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCALE-01 | Vacuum reclaims space, checkpoints, refuses low disk, retries busy, survives a concurrent reader | unit/integration | `pytest tests/unit/database/test_maintenance.py -x` | ❌ Wave 0 |
| SCALE-01 | CLI prints before/after/reclaimed; no target args | CLI | `pytest tests/unit/cli/test_index.py -x -k vacuum` | ❌ Wave 0 |
| SCALE-02 | Backup creates a verified copy; refuses existing/symlink targets; 0600; integrity failure reported | unit/integration | `pytest tests/unit/database/test_maintenance.py -x -k backup` | ❌ Wave 0 |
| SCALE-02 | Backup under concurrent writes contains committed rows and passes integrity_check | integration | `pytest tests/integration/test_maintenance.py -x -k backup` | ❌ Wave 0 |
| SCALE-03 | Embed outside transaction (assert `conn.in_transaction is False` during embed); per-document commit durability mid-run failure | unit/integration | `pytest tests/unit/indexing/test_embed_writer.py tests/integration/test_embed_idempotency.py -x` | ❌/✅ |
| SCALE-03 | Garbage-vector sanity (count/NaN/Inf/dim/norm) aborts without persisting; cache not poisoned | unit | `pytest tests/unit/indexing/test_embed_writer.py -x -k sanity` | ❌ Wave 0 |
| SCALE-03 | Resume embeds exactly the remainder; CR-02 report/exit code preserved | integration | `pytest tests/integration/test_embed_idempotency.py -x` | ✅ (update) |
| CORR-06 | Shadow backfill/legacy upgrade/reconcile/idempotence/orphan exclusion | unit | `pytest tests/unit/database/test_embedded_documents.py -x` | ❌ Wave 0 |
| CORR-06 | Staleness parity: same markers, display gate, None degradation; no vec0 scan in the trace | unit | `pytest tests/unit/search/test_staleness.py -x` | ✅ (update) |
| CORR-06 | Contexts cache invalidation (repository write, other-connection commit, inode change), verbatim legacy fixture, no second contexts SELECT | unit | `pytest tests/unit/search/test_context_attach.py -x` | ✅ (extend) |
| CORR-06 | `sif status` vector-lag text byte-identical on a real DB | CLI | `pytest tests/unit/cli/test_main.py tests/unit/cli/test_status.py -x` | ✅ |
| EMB-01 | Fingerprint determinism; same-dim swap embed fails/search warns+marks; unknown-tolerance; GGUF file-hash detects bytes | unit | `pytest tests/unit/embedding/test_identity.py -x` | ❌ Wave 0 |
| EMB-01 | Legacy DB assumed write + one warning + shadow backfill; `--force` certifies; partial force does not | integration/CLI | `pytest tests/unit/cli/test_index.py -x -k "legacy or certify"` | ❌ Wave 0 |
| EMB-01 | Three dim guards share one read; existing messages preserved | unit | `pytest tests/unit/database/test_schema.py tests/unit/indexing/test_watcher.py -x -k dimension` | ✅ (update) |
| EMB-01 | MCP search mismatch warns once + marks metadata; BM25 degrade does not | MCP | `pytest tests/unit/mcp/test_backend.py -x -k identity` | ❌ Wave 0 |
| EMB-02 | ST `embed_query` passes `prompt_name`; no prompt calls `encode` exactly as today; cache buckets q/d/rev isolation | unit | `pytest tests/unit/embedding/test_embedder_impl.py tests/unit/embedding/test_manager.py -x` | ✅ (extend) |
| EMB-02 | Pipeline query/HyDE/expansion use the query role; doubles fall back to `embed` | unit | `pytest tests/unit/search/test_hybrid.py tests/unit/search/test_suggest.py -x` | ✅ (extend) |
| D-19 | Default ModelScope Qwen3 path byte-identical: bucket string unchanged, no-prompt calls identical, SC1/bench goldens reproduce | unit/snapshot | `pytest tests/unit/search/test_bench_snapshot.py tests/unit/search/test_hybrid.py -x` | ✅ |
| D-19 | Only new writes are the identity row/shadow/markers on a fresh embed | unit | `pytest tests/unit/database/test_embedded_documents.py -x -k fresh` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** the narrow file command(s) above plus `ruff check`/`ruff format --check`.
- **Per wave merge:** `pytest` (full suite) + `ty check src/sif`.
- **Phase gate:** full suite green at `fail_under=90`, docs-generate diff clean, and the D-19 goldens green before `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] `tests/unit/embedding/test_identity.py` — fingerprint/stability/mode matrix/legacy/certify/GGUF hash/revision.
- [ ] `tests/unit/database/test_embedded_documents.py` — DDL, fresh marker, legacy backfill, idempotence, drop/recreate repair, reconcile, orphan exclusion, parity helper.
- [ ] `tests/unit/database/test_maintenance.py` — vacuum/backup/disk/busy/integrity.
- [ ] `tests/unit/indexing/test_embed_writer.py` — transaction flags, per-doc failure, sanity matrix, shadow/identity writes, empty chunks.
- [ ] `tests/integration/test_maintenance.py` — vacuum under a concurrent reader/writer, backup under live writes.
- [ ] Shared helpers: a legacy-index builder, an identity A/B fixture, a garbage-vector fake manager, a shadow-parity assertion, `reset_identity_state()`/`reset_context_cache()` autouse fixtures in `tests/conftest.py`.
- [ ] Test migration: update raw vec0 writers (`test_hybrid.py:565`, `test_staleness.py`, `test_eval.py:75`), `index_meta` fresh-DB assertions (`test_schema.py:604`), and manager/embed call-shape mocks (`test_index.py`, `test_embed_idempotency.py`, `test_watcher.py`, `test_watch_cmd.py`, `test_search.py`).
- [ ] Framework install: none — pytest/cov/ty already installed.

## Security Domain

`security_enforcement` is absent in `.planning/config.json`, so it is enabled. This phase has a file-writing maintenance surface and one new persisted metadata record.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Local CLI only; no new auth surface. |
| V3 Session Management | no | No sessions. |
| V4 Access Control | yes (file/destructive surface) | Vacuum/backup are CLI-only (no MCP tool); backup refuses the DB path/sidecars, existing files, and symlinks; default backup dir mode 0700, file 0600. |
| V5 Input Validation | yes | Click-typed `--output`; refuse existing/symlink/DB targets; all SQL constant/parameterized; identity JSON parsed defensively (corrupt → warning + treat as absent). |
| V6 Cryptography | yes (hashing only) | SHA-256 via `hashlib` for the identity fingerprint/GGUF file hash; never hand-roll crypto. |
| V12 File and Resources | yes | 2× disk precheck; flock + busy timeout; retryable errors; no partial-success reports; remove a failed just-created backup. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Backup path as an exfiltration vector (SQLite incident per PITFALLS 19) | Information Disclosure | CLI-only in Phase 21; Phase 22 owns MCP path restrictions + `destructiveHint`; refuse DB/sidecar/lock targets; 0600. |
| Symlink/TOCTOU on the backup output | Tampering | Refuse `is_symlink()` and existing targets; create with SQLite (not open-then-write); local single-user CLI threat model documented. |
| SQL injection via backup path or identity values | Tampering | Parameterized SQL only; PRAGMA values come from typed integers; no string interpolation of user input. |
| Unpickling ModelScope `.msc` for revision | Elevation of Privilege | Never unpickle; record revision `null` for local snapshots. |
| Cache poisoning via garbage vectors | Tampering (data integrity) | Validate before cache set and on read; abort systemic batches. |
| Stale vectors silently served after a model swap | Tampering | Persisted identity + fail-fast embed/warn+mark search; never width-only. |
| Vacuum/backup corrupting a live DB | Denial of Service / Tampering | Official VACUUM/online-backup APIs; integrity_check; retryable busy errors; no file copy. |

## Sources

### Primary (HIGH confidence)

- Local repository at HEAD `39e8234`: `src/sif/embedding/{manager,cache,embedder,factory}.py`, `src/sif/database/{schema,repositories,repository,database,factory,locking}.py`, `src/sif/search/{vector,staleness,context_attach,hybrid,expansion,rerank}.py`, `src/sif/indexing/{incremental,watcher}.py`, `src/sif/cli/{main.py,commands/index.py,commands/search.py,commands/bench.py,commands/eval.py,commands/collection.py}`, `src/sif/mcp/backend.py`, `src/sif/config/settings.py`, `src/sif/core/models.py`, `src/sif/models/{embedding,download}.py` — all file:line claims quoted above.
- Local runtime probes on Python 3.13.9 / SQLite 3.51.0 / sentence-transformers 5.4.1: VACUUM transaction/concurrency rules; `Connection.backup` target-transaction failure and vec0-copy integrity; `PRAGMA data_version` own-vs-other-connection semantics; `PRAGMA wal_checkpoint(TRUNCATE)` row shape; vec0 DELETE/metadata scan/EXPLAIN; `sqlite3.Connection` attribute/weakref limits; `total_changes`; `Pooling.pooling_mode='lasttoken'` for Qwen3; HF `_commit_hash` populated vs ModelScope local `None`; SHA-256 throughput.
- Official SQLite docs: [VACUUM](https://www.sqlite.org/lang_vacuum.html) — write operation, open-transaction failure, 2× disk, WAL behavior; [PRAGMA data_version / wal_checkpoint](https://www.sqlite.org/pragma.html) — per-connection change semantics and the three checkpoint return columns; [Online Backup API](https://www.sqlite.org/backup.html) — target replacement, snapshot semantics, restart-on-write.
- Official Python docs: [`sqlite3.Connection.backup`](https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup) — exact signature and `pages`/`progress`/`sleep` semantics.

### Secondary (MEDIUM confidence)

- `.planning/research/SUMMARY.md` §Phase 5 and Research Flags; `.planning/research/PITFALLS.md` Pitfalls 1, 2, 3, 18, 19, 20; `.planning/research/STACK.md` §sentence-transformers/Harrier prompts; `.planning/research/FEATURES.md` §correctness-and-scale; `.planning/research/ARCHITECTURE.md` integration map — all previously source-verified, used as roadmap context, not re-derived here.
- Harrier model card facts (`microsoft/harrier-oss-v1-0.6b`, 1024-dim, last-token, `web_search_query`, documents none, `default_prompt_name: null`) — cited through `STACK.md:107-117`; not re-fetched this session (`[ASSUMED]` for the exact prompt-key availability until Phase 23 loads the model).
- qmd #897 (garbage vectors at a 512-token physical batch boundary) — cited through `FEATURES.md:57`/`PITFALLS.md`; the D-17 checks are the locked mitigation.

### Tertiary (LOW confidence)

- GGUF pooling provenance and the ModelScope revision blind spot — documented as residual risks; no source can resolve them from a local snapshot without loading the model / unpickling.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — no new packages; every API verified locally or in official docs.
- Architecture: HIGH — all integration points read at HEAD with verbatim quotes; the shadow/write-path audit covers every production writer.
- Embedder identity: HIGH for construction/checks/fingerprint; MEDIUM for ModelScope revision provenance and Harrier's prompt-key availability (Phase 23 verifies).
- Maintenance: HIGH — VACUUM/backup/checkpoint/data_version semantics verified in official docs and locally.
- Pitfalls: HIGH for codebase-specific traps (quoted fixtures); MEDIUM for operational limits (flock semantics, disk temp location).

**Research date:** 2026-11-15
**Valid until:** 2026-12-15 (30 days; the code seams are HEAD-specific, the SQLite/ST facts are stable). Re-verify Harrier's `prompts` keys when Phase 23 loads the model.
