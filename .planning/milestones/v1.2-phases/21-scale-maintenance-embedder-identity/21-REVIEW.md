---
phase: 21-scale-maintenance-embedder-identity
reviewed: 2026-11-15T18:20:00Z
depth: standard
files_reviewed: 26
files_reviewed_list:
  - src/sif/embedding/identity.py
  - src/sif/embedding/prompts.py
  - src/sif/embedding/roles.py
  - src/sif/embedding/embedder.py
  - src/sif/embedding/manager.py
  - src/sif/embedding/factory.py
  - src/sif/config/settings.py
  - src/sif/models/embedding.py
  - src/sif/database/database.py
  - src/sif/database/schema.py
  - src/sif/database/repositories.py
  - src/sif/database/maintenance.py
  - src/sif/search/vector.py
  - src/sif/search/staleness.py
  - src/sif/search/context_attach.py
  - src/sif/search/hybrid.py
  - src/sif/search/expansion.py
  - src/sif/indexing/embed_writer.py
  - src/sif/indexing/watcher.py
  - src/sif/cli/commands/index.py
  - src/sif/cli/main.py
  - src/sif/cli/commands/search.py
  - src/sif/cli/commands/bench.py
  - src/sif/cli/commands/eval.py
  - src/sif/mcp/backend.py
  - scripts/generate_config_ref.py
findings:
  critical: 3
  warning: 6
  info: 7
  total: 16
  necessity: 0
status: issues_found
---

# Phase 21: Code Review Report

**Reviewed:** 2026-11-15T18:20:00Z
**Depth:** standard
**Files Reviewed:** 26
**Status:** issues_found

## Summary

Reviewed the 26 Phase 21 source files at standard depth (no structural-findings
block was supplied). The phase delivers real value and the focused unit suite
for these areas passes (`tests/unit/embedding`, `test_embedded_documents.py`,
`test_maintenance.py`, `test_context_attach.py`, `test_staleness.py`,
`test_embed_writer.py`: 297 passed), but the findings below sit outside that
suite's coverage. Three BLOCKERs were confirmed with runtime probes:

1. `sif bench` now crashes with an uncaught `ImportError`/exception when the
   embedder backend is missing, instead of the documented BM25-only soft-fail
   (the soft-fail test patches the wrong seam).
2. The embedder identity check and the "first vector write owns the identity"
   decision are made **before** `index_lock`; a concurrent embed writer (or a
   watch session) can overwrite the identity and leave two models' vectors in
   one vec0 table — exactly the same-dimension trap EMB-01 exists to prevent.
3. `sif index backup` / `sif index vacuum` create a brand-new empty index when
   `--index` points at a nonexistent path and report success, defeating the
   helper's own "index database does not exist" refusal.

Warnings cover the vec0-less reconcile failure, the systemic/document-local
failure-taxonomy gap (the new manager-level validation shadows `validate_batch`
and makes watch retry failing paths forever), the backup permission window and
backup-target TOCTOU, `vsearch` embedding before its identity check, and the
writer clearing its identity-write flag before the commit. Info items are
hardening/contract observations. No necessity findings: every guard reviewed is
reachable on a supported path (the duplicate legacy-identity call in
`create_all` was treated as deliberate idempotent defense, per the
necessity-review negative-space rule).

---

## Narrative Findings (AI reviewer)

### Critical Issues

#### CR-01: Bench embedder soft-fail is converted into an uncaught crash

**File:** `src/sif/cli/commands/bench.py:150-173` (`_load_embedder`), `:176-204` (`_search_identity_check`), `:734-738` (call site)
**Issue (BLOCKER):** `_load_embedder` assigns `manager = EmbeddingManager.from_settings(settings)` and then calls `manager.load_model()` inside the same try. When the real load fails (the common "embed extra not installed" case — `from_settings` itself never imports the backend), the exception is caught, `manager` is still the constructed-but-unloaded object, and that object is returned. The new `_search_identity_check(manager, db)` immediately calls `manager.get_identity()`, which re-enters `load_model()` and re-raises the same `ImportError`/`Exception` with no handler, so `sif bench` now dies with a traceback instead of measuring BM25-only. Verified by patching `EmbeddingManager.load_model` to raise `ImportError`: `_load_embedder` returned an `EmbeddingManager`, and `_search_identity_check` propagated `ImportError`. The existing soft-fail test (`tests/unit/cli/test_bench.py:226-234`) patches `EmbeddingManager.from_settings`, which is not where the real failure occurs, so it masks this regression.
**Fix:** Drop the manager on any load failure so the existing soft-fail contract holds:

```python
    except ImportError as e:
        manager = None
        console_err.print(f"[yellow]Embedding backend not installed: {e}[/yellow]")
    except Exception as e:
        manager = None
        console_err.print(f"[yellow]Failed to load embedding model: {e}[/yellow]")
    return manager, embedding_dim
```

(Alternatively make `_search_identity_check` catch load failures and return `None`, but clearing `manager` also keeps `harness.embedder` correctly `None`.)

#### CR-02: Identity decision is taken outside the index flock — concurrent writers can mix vector spaces and falsify the identity

**File:** `src/sif/cli/commands/index.py:326-349` (check + `write_identity_on_first`), `:369-375` (`index_lock`), `:497-504` (certification outside the lock); `src/sif/indexing/embed_writer.py:195-198` (identity overwrite); `src/sif/indexing/watcher.py:248-296` (session caches the decision); `src/sif/database/locking.py:83-92` (deadline proceeds unlocked)
**Issue (BLOCKER):** `embed_cmd` runs `ensure_legacy_identity` / `check_identity(mode="embed")` / `_index_has_vectors` **before** acquiring `index_lock`. On an embeddings-empty index (the D-02 accept-any-embedder state) two embed writers with different same-dimension models both pass the check, then serialize on the flock (or the loser proceeds unlocked after `lock_wait_timeout`). The loser's `write_identity_on_first` is stale `True`; inside the lock `_needs_embedding` skips the documents the winner already embedded (`get_all_embedded_chunk_ids`), and `StreamingEmbedWriter.embed_document` unconditionally `INSERT OR REPLACE`s the identity on its first commit. Result: vec0 holds model A vectors for some documents and model B vectors for others, while the persisted identity names only B — searches with B then pass the identity check silently. The same shape occurs between a long-lived `sif watch` `_EmbedSession` (which caches its empty-index decision in `ensure_ready`/`self._write_identity`) and a later CLI writer, and `certify_identity` at `index.py:502-504` runs after the lock is released. This is precisely the same-dimension swap that EMB-01/D-03 exist to reject; the phase's own `index_lock` comment ("never held across model loading") does not justify moving the cheap identity reads outside the lock — the model is already loaded at that point.
**Fix:** Re-validate provenance inside the write transaction that is about to claim the identity, and move the CLI check under the lock:

```python
# StreamingEmbedWriter.embed_document, inside `with self._conn:`
if self._write_identity:
    assert self._identity is not None
    stored = read_identity(self._conn)
    if stored is not None and not identity_matches(stored, self._identity):
        raise SystemicEmbedError(
            "Embedder identity mismatch while claiming the first vector write: "
            f"stored {stored.display_fingerprint()} ({stored.cache_model_id}) vs "
            f"current {self._identity.display_fingerprint()} ({self._identity.cache_model_id})."
        )
    if stored is None and _has_stored_vectors(self._conn):
        raise SystemicEmbedError(
            "Refusing to claim the embedder identity: vectors with no identity appeared "
            "concurrently; rerun `sif index embed`."
        )
    write_identity(self._conn, replace(self._identity, source="verified"))
```

Also compute `current`/`check`/`write_identity_on_first` after entering `index_lock` (the embedder is loaded, so no lock-across-model-load), and keep certification inside the same lock window or re-verify before writing it.

#### CR-03: `sif index backup` / `sif index vacuum` silently create an empty index and report success

**File:** `src/sif/cli/commands/index.py:520-524` (vacuum init), `:564-568` (backup init); `src/sif/database/maintenance.py:320-324` (unreachable existence refusal)
**Issue (BLOCKER):** Both commands call `open_initialized_database(index_path, Database)` before taking the lock. `Database.__init__`/`create_connection` create the file and `create_all` creates the full schema, so `backup_index`'s explicit `if not db_path.exists(): raise MaintenanceTargetError(...)` can never fire from the CLI. Verified: `sif index backup --index /tmp/sifbkp/typo-index.db` created a 253 KB empty database plus `backups/typo-index-20261115T180847Z.db` and printed "Backup complete" with exit 0. A user who typo-ed `--index` (or whose `SIF_DB_PATH` points elsewhere) gets a successful-looking backup of nothing and may then rely on it before destructive work. `vacuum` reports a clean vacuum of a newly created empty index.
**Fix:** Guard existence before initializing, as `search_cmd` already does:

```python
    if not Path(index_path).exists():
        raise click.ClickException(
            f"No index found at {index_path}. Run 'sif index update' first."
        )
    with open_initialized_database(index_path, Database):
        pass
```

Apply to both commands (the helper-level checks stay as the API contract).

### Warnings

#### WR-01: Reconcile assumes `document_embeddings` exists whenever the shadow does; `cleanup`/`vacuum` fail on stripped environments

**File:** `src/sif/database/maintenance.py:63-95`; callers `src/sif/database/maintenance.py:141-142` and `src/sif/cli/main.py:266`
**Issue:** `reconcile_embedded_documents` probes only `embedded_documents`. `PRAGMA foreign_keys`/schema creation is conditional on sqlite-vec, and the phase explicitly requires stripped environments to keep working (21-02-PLAN: "stripped environments must keep working"). On a host where the extension cannot load but the database was built with it, the shadow table exists while `document_embeddings` is unqueryable, so `_SHADOW_DELETE_STALE_SQL` raises `sqlite3.OperationalError: no such table: document_embeddings`. Reproduced by creating the schema and dropping `document_embeddings`: `reconcile_embedded_documents` raised exactly that error. `cleanup` wraps this in its main transaction, so the whole cleanup (orphan chunks, expired LLM cache included) rolls back and fails; `vacuum` becomes `MaintenanceTargetError`. Before Phase 21 both commands worked in that environment.
**Fix:** Require both source tables before touching anything:

```python
def reconcile_embedded_documents(conn: sqlite3.Connection) -> tuple[int, int]:
    for table in ("embedded_documents", "document_embeddings"):
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if row is None:
            return 0, 0
    ...
```

#### WR-02: Systemic model-output failures are classified as document-local (and retried forever by watch)

**File:** `src/sif/embedding/manager.py:207-214` and `:284-299`; `src/sif/indexing/embed_writer.py:71-115, 173-179`; `src/sif/cli/commands/index.py:431-447`; `src/sif/indexing/watcher.py:341-355`
**Issue:** The manager now validates model output itself (`_validate_vector`: count/dimension/finiteness) and raises a plain `RuntimeError` **before** `validate_batch` is reached, so the writer's `SystemicEmbedError` path for count/dimension/non-finite output is unreachable in production (only the norm check remains novel to `validate_batch`). `embed_cmd`'s `except Exception` therefore records a garbage batch as a per-document failure and keeps going (not D-17's "abort after prior commits"), and the watcher's `except Exception` re-queues the path into `_pending_retry`, so a model that systematically returns wrong-width/NaN vectors fails and is retried on every later burst instead of disabling the session. Reproduced: `EmbeddingManager.embed_documents` with a 3-dim output for a 4-dim identity raised `RuntimeError`, not `SystemicEmbedError`.
**Fix:** Have the manager guards raise a dedicated systemic exception (e.g. `EmbeddingOutputError`) and translate it in `embed_writer.embed_document` into `SystemicEmbedError` (or catch only that type in both hosts). Keep genuine document-local errors (parse/chunk/storage) on the current path.

#### WR-03: Backup copy is group/other-readable for the entire copy + integrity-check window

**File:** `src/sif/database/maintenance.py:261-288`, `:290-303`, `:337-352`
**Issue:** `_copy_with_online_backup` creates the target with `sqlite3.connect(str(target))`, i.e. `0o666 & ~umask` (typically `0644`), and `_finalize_backup_copy` chmods `0o600` only after `Connection.backup` completes **and** `PRAGMA integrity_check` finishes. Backups contain full document text; for a large database the window is the entire copy plus verification, and a user-supplied `--output` in a shared directory (or a permissive umask) lets another local account read it. The code comment at `:299` claims "never group/other readable", which is only true after success.
**Fix:** Create the file exclusively with restrictive permissions **before** the backup API writes into it, or chmod immediately after the `sqlite3.connect` call:

```python
fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
os.close(fd)
target_conn = sqlite3.connect(str(target))
```

#### WR-04: Backup target validation is check-then-use (symlink TOCTOU)

**File:** `src/sif/database/maintenance.py:203-236`, `:261-273`, `:326-337`
**Issue:** `_validate_backup_target` refuses a symlink/existing file by inspecting the path, then `_copy_with_online_backup` calls `sqlite3.connect(str(target))`, which follows whatever is at the path at open time. In a shared writable output directory an attacker can create the symlink after the check; `sqlite3.connect` then opens the user's writable target file and `Connection.backup` writes a fresh SQLite database over it. The symlink refusal therefore does not hold at the point of use (the "target already exists" refusal has the same race and can silently overwrite the attacker's replacement).
**Fix:** Open the target itself exclusively and without following symlinks (`O_CREAT|O_EXCL|O_NOFOLLOW|O_WRONLY`, as in WR-03), then pass that file descriptor/path to the backup connection (or `fstat` the opened fd and reject non-regular files) rather than re-checking a path string.

#### WR-05: `vsearch` runs the query embedding (and can call a remote API) before its identity check

**File:** `src/sif/cli/commands/search.py:787-795` (embed), `:797` (DB open), `:813-826` (identity check)
**Issue:** The comment at `:813-816` says the check "owns the vsearch policy before any vector work", but `manager.embed_query(query)` executes before the database is even opened. On a dimension mismatch the command pays a model load + embed (a remote `openai` call with the user's query on a remote backend) and only then refuses; on a same-dimension mismatch it also emits the query before warning. The manifest is therefore unnecessary work at best and an avoidable off-machine query at worst.
**Fix:** Open the DB and resolve collections first, then compute `current_identity`/`check_identity`, and only then embed the query (the drift refresh may stay where it is).

#### WR-06: `StreamingEmbedWriter` clears the identity-write flag before the transaction commits

**File:** `src/sif/indexing/embed_writer.py:183-200`
**Issue:** `self._write_identity = False` is executed inside the `with self._conn:` block, before `__exit__` commits. If the commit raises, SQLite rolls back the identity and the vectors together, but the in-memory writer now reports `identity_pending == False` forever. Subsequent documents commit vectors with no identity row, and `embed_cmd`'s `finally` (`index.py:463-469`) sets `identity_written = True`, skipping certification. The next schema open writes a legacy-assumed identity from whatever settings model is then configured, so the persisted provenance can name a model that did not produce those vectors. Watch sessions inherit the same wrong state.
**Fix:** Set the flag only after the commit succeeds:

```python
wrote_identity = False
with self._conn:
    ...
    if self._write_identity:
        write_identity(self._conn, replace(self._identity, source="verified"))
        wrote_identity = True
if wrote_identity:
    self._write_identity = False
```

### Info

#### IN-01: Prompted cache bucket can be paired with an unprompted encode for protocol-only embedders

**File:** `src/sif/embedding/manager.py:258-273`, `src/sif/embedding/prompts.py:22`
**Issue:** `_role_model_call` falls back to `self._model.embed_batch` when a prompt is effective but the embedder class lacks `embed_queries`/`embed_documents`, while `_cache_bucket` still appends `|q@…`/`|d@…`. That stores an unprompted vector under a prompted key. Today it is unreachable for production backends (only `sentence_transformers`/`modelscope` resolve prompts and both define the role methods; unsupported backends resolve prompts to `None`), but it is a silent cache-poisoning seam for any future backend added to `_PROMPT_SUPPORTED_TYPES` without role methods.
**Fix:** Fail closed — raise or drop the prompt marker when the class lacks the role method, so the bucket always describes the encode that produced the vector.

#### IN-02: Stored identity `schema` is never validated against `IDENTITY_SCHEMA_VERSION`

**File:** `src/sif/embedding/identity.py:88-114`, `:173-206`
**Issue:** `_payload_error` accepts any integer `schema` (including negative and future versions), and `from_json` parses it as a v1 record. A future payload shape would be silently interpreted with v1 semantics instead of being treated as absent/unknown.
**Fix:** Reject `schema != IDENTITY_SCHEMA_VERSION` (or `< IDENTITY_SCHEMA_VERSION`) in `_payload_error` with the same warn-and-ignore path.

#### IN-03: GGUF revision hashing blocks every process that builds an identity

**File:** `src/sif/embedding/embedder.py:92-101, 444-450`; `src/sif/embedding/identity.py:303-331`
**Issue:** `build_identity` reads `model.revision`, which for `LlamaCppEmbedder` hashes the whole GGUF file. Because every CLI invocation is a new process, every `sif query` / `vsearch` / `bench` / `eval` with a GGUF model hashes the model file synchronously at startup (potentially seconds for multi-GB files before the first query), which contradicts D-02's "revision resolution never blocks an embed" framing. This is a contract/robustness note, not an output-correctness bug.
**Fix:** Defer the hash (record `revision: null` until an explicit `--force`/certify path or a background computation), or cache the digest keyed by `(path, size, mtime_ns)` outside the process.

#### IN-04: `eval` labels ModelScope as a remote embedding provider

**File:** `src/sif/cli/commands/eval.py:79`, `:233-241` (pre-existing)
**Issue:** `_REMOTE_MODEL_TYPES = {"openai", "modelscope"}` triggers a disclosure that document titles/excerpts and replay queries "are sent to the configured provider for embedding". `ModelScopeEmbedder` downloads the model once via `ModelDownloader` and runs sentence-transformers locally, so the disclosure is factually wrong and pushes users to `--bm25-only` unnecessarily.
**Fix:** Restrict the disclosure to `{"openai"}` (or make it depend on a backend-provided "remote inference" capability flag).

#### IN-05: `embed_cmd` still materializes a whole collection's document bodies

**File:** `src/sif/cli/commands/index.py:387`; claim in `src/sif/indexing/embed_writer.py:1-14`
**Issue:** `documents = doc_repo.list_by_collection(coll.id)` loads every document row including full `content` before the per-document streaming loop. The writer itself is bounded, but peak memory per collection is O(total collection text), so the SCALE-03/D-15 "memory bounded by one document's chunks" invariant does not hold at the command level for large collections.
**Fix:** Iterate ids/paths (keyset pagination) and re-fetch one document's row at a time inside the loop.

#### IN-06: A chunkless document does not purge its existing rows

**File:** `src/sif/indexing/embed_writer.py:161-171, 202-207`
**Issue:** `embed_document` returns 0 for a whitespace-only/chunkless document before the delete-before-insert transaction, so any pre-existing chunks/embeddings for that document survive. The docstring's "delete-before-insert, self-healing re-chunk" claim is narrower than stated. Today the incremental indexer purges on body change, so this only bites callers that change content without the purge; a direct `embed_cmd` on a manually emptied document keeps stale vectors.
**Fix:** In the chunkless branch, still run the short delete transaction (or assert the document has no rows) so the self-healing contract is total.

#### IN-07: Unreachable branch in `QueryExpansion.expand`

**File:** `src/sif/search/expansion.py:58-65` (pre-existing)
**Issue:** `variants` is initialized as `[query]`, so `if not variants: return [query]` can never execute.
**Fix:** Remove the dead branch (or build `variants` from the expansion terms and keep the guard).

---

_Reviewed: 2026-11-15T18:20:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
