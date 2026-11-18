# Phase 21: Scale, Maintenance + Embedder Identity - Pattern Map

**Mapped:** 2026-11-15
**Files analyzed:** 28 (4 new source, 20 modified source, 4 new test files + 1 shared test fixture file)
**Analogs found:** 24 / 28 with a role analog (4 have role-match only; no exact vacuum/backup precedent exists)

**Tracked-source gate:** every analog path below was verified with `git ls-files -- <path>` at HEAD (all tracked). The four new modules (`embedding/identity.py`, `embedding/prompts.py`, `indexing/embed_writer.py`, `database/maintenance.py`) do not exist on disk yet — they are targets, not analogs.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/sif/embedding/identity.py` (new) | service (identity/infrastructure) | CRUD (`index_meta`) + transform (fingerprint) | `src/sif/database/schema.py` (`_backfill_metadata_values` marker + `_create_vector_tables` guard) | role-match |
| `src/sif/embedding/prompts.py` (new) | utility (resolution table) | transform | `src/sif/embedding/factory.py` | role-match |
| `src/sif/config/settings.py` | config | request-response (env load) | itself — existing model-field block, `settings.py:110-152` | exact |
| `src/sif/embedding/embedder.py` | provider (adapter) | request-response | `SentenceTransformerEmbedder` current `embed`/`_encode_kwargs`, `embedder.py:92-132` | exact |
| `src/sif/embedding/factory.py` | factory | transform (config dispatch) | itself, `factory.py:22-110` | exact |
| `src/sif/embedding/manager.py` | service | CRUD (cache) + request-response | itself — `embed`/`_compute_embeddings`/`_cache_model_id` | exact |
| `src/sif/database/database.py` | infrastructure | request-response | itself — `init_schema`/`transaction`, `database.py:31-55` | exact |
| `src/sif/database/schema.py` | migration | batch (one-time pass) | itself — `_backfill_metadata_values`, `schema.py:277-316` | exact |
| `src/sif/database/repositories.py` | repository | CRUD | itself — `ContextRepository` / `IndexMetaRepository` | exact |
| `src/sif/search/vector.py` | repository (vector store) | CRUD | itself — three write methods, `vector.py:325-384` | exact |
| `src/sif/search/staleness.py` | utility | read (derived signal) | itself + `vector.py:398-417` batching rule | exact |
| `src/sif/search/context_attach.py` | utility | read + transform | its own context scan; module-level resource shape from `embedding/cache.py` | role-match |
| `src/sif/search/hybrid.py` | service (pipeline) | request-response | itself — optional-constructor-arg pattern, `hybrid.py:196-224` | exact |
| `src/sif/search/expansion.py` | service | request-response | itself, `expansion.py:77-110` | exact |
| `src/sif/indexing/embed_writer.py` (new) | service | batch / streaming | `src/sif/indexing/watcher.py` `_EmbedSession.embed_documents`, `watcher.py:255-316` | exact (data flow) |
| `src/sif/indexing/watcher.py` | service (event host) | event-driven + batch | itself — `_EmbedSession`, `watcher.py:190-326` | exact |
| `src/sif/indexing/incremental.py` | service | per-file batch | itself — purger seam, `incremental.py:88-94,452-458,523-530` | exact (no change expected) |
| `src/sif/database/maintenance.py` (new) | service (ops) | file-I/O + maintenance | `src/sif/database/locking.py` + `src/sif/database/factory.py` + `cli/main.py` cleanup | partial |
| `src/sif/cli/commands/index.py` | controller (CLI) | batch + request-response | itself — `embed_cmd`, `index.py:206-391` | exact |
| `src/sif/cli/main.py` | controller (CLI) | request-response | itself — `cleanup_cmd`/`_vector_lag_text` | exact |
| `src/sif/cli/commands/search.py` | controller (CLI) | request-response | itself — `vsearch`, `search.py:757-804` | exact |
| `src/sif/cli/commands/bench.py` | controller + wrapper | batch | itself — `CachedEmbedder`/`BenchHarness`, `bench.py:53-96` | exact |
| `src/sif/cli/commands/eval.py` | controller (CLI) | batch | itself — `_search_fn`/pipeline hoist, `eval.py:647-654,702-713` | role-match |
| `src/sif/mcp/backend.py` | provider (MCP backend) | async request-response | itself — init/embedder construction, `backend.py:88-137` | exact |
| `tests/unit/embedding/test_identity.py` (new) | test | battery | `tests/unit/database/test_schema.py` marker battery | role-match |
| `tests/unit/database/test_embedded_documents.py` (new) | test | battery | `tests/unit/search/test_staleness.py` real-vec0 fixture | role-match |
| `tests/unit/database/test_maintenance.py` (new) | test | battery | `tests/unit/database/test_schema.py` + `tests/integration/test_concurrency.py` | role-match |
| `tests/unit/indexing/test_embed_writer.py` (new) | test | battery | `tests/integration/test_embed_idempotency.py` | role-match |
| `tests/integration/test_maintenance.py` (new) | test | integration | `tests/integration/test_concurrency.py` | role-match |
| `tests/conftest.py` | test config | n/a | itself — autouse reset fixture, `conftest.py:54-71` | exact |

---

## Pattern Assignments

### `src/sif/embedding/identity.py` (new — service, CRUD + transform)

**Analog:** `src/sif/database/schema.py` (guard + marker migration) and `src/sif/database/repositories.py` (`IndexMetaRepository`)

**Imports / module shape** — follow the logger convention (`manager.py:1-14`):
```python
from sif.utils.logging import get_logger

logger = get_logger(__name__)
```

**Key/value persistence pattern** — `repositories.py:662-685`. The identity module must not own a transaction; every caller already owns one:
```python
class IndexMetaRepository:
    def get(self, key: str) -> str | None:
        cursor = self.db.execute("SELECT value FROM index_meta WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else None

    def set(self, key: str, value: str) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO index_meta (key, value) VALUES (?, ?)",
            (key, value),
        )
```

**Guard pattern to consolidate** — the three existing inline dimension guards. Keep the exact messages when delegating:
```python
# schema.py:592-607 (message must survive the move)
match = re.search(r"FLOAT\[(\d+)\]", row[0])
if match:
    existing_dim = int(match.group(1))
    if existing_dim != self.embedding_dim:
        raise RuntimeError(
            f"Embedding dimension mismatch: database has FLOAT[{existing_dim}], "
            f"but settings require FLOAT[{self.embedding_dim}]. "
            ...
        )

# cli/commands/index.py:250-261 (user-facing wording)
raise click.ClickException(
    f"Model '{model or settings.model_name}' produces {embedding_dim}-dim "
    f"embeddings but the index stores {dim_match.group(1)}-dim vectors. ..."
)
```

**Marker discipline** (copy verbatim from `schema.py:284-316`): write the key only after a complete pass, with per-item short transactions; exceptions propagate:
```python
if marker.get(_METADATA_VALUES_VERSION_KEY) == _METADATA_VALUES_VERSION:
    return
...
for document_id, metadata_json in rows:
    with self.db:
        repo.replace_from_canonical(document_id, metadata_json or "{}")
with self.db:
    marker.set(_METADATA_VALUES_VERSION_KEY, _METADATA_VALUES_VERSION)
```

**Cycle-avoidance pattern** — deferred import inside the method, as `schema.py:297-298` does:
```python
from sif.database.repositories import IndexMetaRepository  # noqa: PLC0415
```
`SchemaManager` must import the identity helpers *inside* its methods (`from sif.embedding.identity import ...  # noqa: PLC0415`) because `sif.embedding.__init__` eagerly imports the manager/factory.

**Canonical identity base** — re-extract the exact format from `manager.py:153-163` (`format_cache_model_id`) without changing its output.

**Fingerprint shape** — `hashlib.sha256` hashing is already the project norm (`cache.py:87-96`, `tests/conftest.py:316`); use canonical JSON (`json.dumps(..., sort_keys=True, separators=(",", ":"))`) as RESEARCH Pattern 1 specifies. Do not hand-roll any other hash.

---

### `src/sif/embedding/prompts.py` (new — utility, transform)

**Analog:** `src/sif/embedding/factory.py`

**Dispatch-table pattern** (`factory.py:22-40`) — a small explicit table + a default, no plugin registry:
```python
def create_model(self, model_type: ModelType, model_path, model_name, **kwargs) -> Embedder:
    if model_type == ModelType.SENTENCE_TRANSFORMERS:
        return self._create_sentence_transformers_model(model_name, **kwargs)
    ...
    raise ValueError(f"Unsupported model type: {model_type}")
```

**Settings-override precedence:** follow `Settings` field validators (`settings.py:307-348`) for rejecting bad values early; unknown model names must return `(None, None)` and never raise.

---

### `src/sif/config/settings.py` (config, request-response)

**Analog:** itself — the model-settings block at `settings.py:110-152`

```python
    model_name: str = Field(
        default="Qwen/Qwen3-Embedding-0.6B",
        description="Embedding model name",
    )
    ...
    api_base: str | None = Field(
        default=None,
        description="Base URL for remote embedding API",
    )
```

Add `query_prompt_name: str | None = Field(default=None, description=...)` and `document_prompt_name: str | None` with the same Field style (env prefix `SIF_` is automatic). The validator style for optional strings is `validate_api_base` at `settings.py:340-348`. These are generator-owned doc inputs — never hand-edit `docs/configuration.md` (`Makefile:73-76`).

---

### `src/sif/embedding/embedder.py` (provider, request-response)

**Analog:** itself — `SentenceTransformerEmbedder` at `embedder.py:29-132`

**Constructor + single insertion point for encode kwargs** (lines 92-127):
```python
    def _encode_kwargs(self) -> dict[str, Any]:
        """Common encode kwargs, including the configured batch size."""
        kwargs: dict[str, Any] = {"normalize_embeddings": True}
        if self._batch_size is not None:
            kwargs["batch_size"] = self._batch_size
        return kwargs

    def embed(self, text: str) -> list[float]:
        embedding = self.model.encode(text, **self._encode_kwargs())
        result: list[float] = embedding.tolist()
        return result

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(
            texts,
            show_progress_bar=len(texts) > _PROGRESS_BAR_THRESHOLD,
            **self._encode_kwargs(),
        )
        return embeddings.tolist()
```
Role methods delegate to these exact calls when no prompt is effective, so the default path is byte-identical (D-19). `ModelScopeEmbedder` has the identical shape at `embedder.py:380-407`. `LlamaCppEmbedder` normalizes at `embedder.py:217-223` and `OpenAIEmbedder._normalize` at `embedder.py:565-573` — the identity's `normalized: true` is justified by those three sites.

**Construction-time validation precedent:** the ST constructor raises/warns on load failures (`embedder.py:49-56`, 73-90) — validate an unknown `prompt_name` against `self.model.prompts` here so the CLI's existing `Failed to load embedding model` wrapper (`index.py:234-237`) catches it.

---

### `src/sif/embedding/factory.py` (factory, transform)

**Analog:** itself — `_create_sentence_transformers_model` at `factory.py:61-73`
```python
    def _create_sentence_transformers_model(self, model_name: str, **kwargs: Any) -> Embedder:
        return SentenceTransformerEmbedder(
            model_name=model_name,
            device=kwargs.get("device"),
            cache_dir=kwargs.get("cache_dir"),
            max_tokens=kwargs.get("max_tokens"),
            batch_size=kwargs.get("batch_size"),
        )
```
Add `query_prompt_name=kwargs.get("query_prompt_name")` / `document_prompt_name=...` in the same style; `EmbeddingManager.load_model` (`manager.py:87-99`) is the call site that must pass them.

---

### `src/sif/embedding/manager.py` (service, CRUD + request-response)

**Analog:** itself

**Public method contract** (`manager.py:109-151`) — role methods must preserve this 1:1 guard and response shape:
```python
        result_embeddings = [e for e in embeddings if e is not None]
        if len(result_embeddings) != len(texts):
            raise RuntimeError(
                f"Embedding model returned {len(result_embeddings)} embeddings for "
                f"{len(texts)} inputs"
            )
        return EmbeddingResponse(
            embeddings=result_embeddings,
            model_id=self._config.model_name,
            dimensions=actual_dim,
            total_tokens=total_tokens,
            processing_time_ms=processing_time,
        )
```

**Cache flow to refactor** (`manager.py:165-215`) — `_lookup_cached` + `_compute_embeddings` are the refactor seam: parameterize the bucket (`model_id`) and the model call, leaving `embed`/`embed_single` on exactly today's `_cache_model_id()`/`embed_batch` path for D-19. `_cache_model_id` (`153-163`) becomes a call to the shared formatter. Cache API is unchanged (`cache.py:98-153`): `get(content, model_id=...)`, `set(content, embedding, model_id=...)`.

**Model lifecycle:** `load_model`/`unload_model` (`manager.py:80-107`) are where a cached `get_identity()` value must be invalidated.

**Response type:** `EmbeddingResponse` at `src/sif/models/embedding.py:66-73`; `EmbeddingConfig` at `18-43` (add prompt fields there if the manager must carry them).

---

### `src/sif/database/schema.py` (migration, batch)

**Analog:** itself

**Ordering** — extend `create_all` (`schema.py:43-56`) exactly where RESEARCH Pattern 7 says: after `_create_vector_tables()`, add `_create_embedded_documents_table()` (vec0-conditional), and after `_backfill_metadata_values()` add `_backfill_embedded_documents()` + `_ensure_legacy_identity(...)`, before the single `self.db.commit()`.

**Vector guard / vec0 detection** (`schema.py:581-590`) — reuse this availability idiom for the shadow table (no vec0 ⇒ no shadow):
```python
        try:
            self.db.execute("SELECT vec_version()")
            vec_available = True
        except sqlite3.OperationalError:
            vec_available = False
        if not vec_available:
            return
```

**Marker-gated backfill template** (`schema.py:277-316`): one Python/SQL pass, per-item short transaction (`with self.db:`), marker written only after completion, lazy repository imports, exceptions propagate.

**drop_all ordering** (`schema.py:658-678`) — add `"embedded_documents"` next to `"document_embeddings"` at the front so the FK'd child drops before `documents`.

**Body-identical default:** keep the width-check message text at `schema.py:601-607`; the identity check becomes the wrapper, width-only is its legacy facet.

---

### `src/sif/database/repositories.py` (repository, CRUD)

**Analog:** itself

**Context write hook points** — every write method must bump a module-level generation counter (D-12): `create` (406-416), `update` (453-463), `update_target` (465-488), `delete` (490-493), `delete_orphaned_paths` (495-517). The bump is one line at the end of each; do not change semantics.

**IndexMetaRepository** (`662-685`) — already the right shape for identity + `embedded_documents_version`; callers own transactions (documented in its docstring).

**Delete semantics to preserve** (`256-284`): `DocumentRepository.delete`/`delete_by_collection` never touch `document_embeddings` and rely on the caller's explicit vector purge; the shadow's FK `ON DELETE CASCADE` covers the shadow row, but never treat the shadow as authoritative (D-09).

```python
    def delete(self, document_id: str) -> bool:
        chunk_repo = DocumentChunkRepository(self.db)
        chunk_repo.delete_by_document(document_id)
        cursor = self.db.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        return cursor.rowcount > 0
```

---

### `src/sif/database/database.py` (infrastructure, request-response)

**Analog:** itself — `init_schema` (`database.py:31-44`)
```python
    def init_schema(self, embedding_dim: int | None = None) -> None:
        if embedding_dim is None:
            from sif.config.settings import get_settings  # noqa: PLC0415

            embedding_dim = get_settings().embedding_dim
        self._schema = SchemaManager(self.connection, embedding_dim=embedding_dim)
        self._schema.create_all()
```
Add an optional settings-only identity parameter with the same "injected caller never triggers `get_settings()`" contract (MCP passes its own). `Database.transaction()` (`46-55`) commits explicitly — maintenance commands must never be called inside it.

---

### `src/sif/search/vector.py` (repository, CRUD)

**Analog:** itself — the three write methods, `vector.py:325-384`
```python
    def delete_embeddings_by_document(self, document_id: str) -> int:
        cursor = self.db.execute(
            "DELETE FROM document_embeddings WHERE document_id = ?",
            (document_id,),
        )
        return cursor.rowcount
```
Add shadow maintenance in `add_embedding`/`_add_embedding_vec`, `add_embeddings_batch`, and `delete_embeddings_by_document`, using the RESEARCH insert form that joins `documents` so orphan vectors never create a shadow row. Detect the shadow once in `__init__` with the same boolean idiom as `_vec_available` (`vector.py:40-56`) — `sqlite3.Connection` cannot hold attributes, so store a plain bool on the searcher.

Parent transaction is always the caller's (`embed_cmd`, watcher, `incremental.py`, `collection.py`); the methods already document "callers own transactions" behavior. `get_all_embedded_chunk_ids` (`398-417`) stays a vec0 scan (resume only, not per-query).

---

### `src/sif/search/staleness.py` (utility, read)

**Analog:** itself

Current scan to replace (`staleness.py:37-52`):
```python
    embedded: set[str] = set()
    try:
        cursor = db.execute("SELECT document_id FROM document_embeddings")
        for row in cursor:
            embedded.add(row[0])
    except sqlite3.OperationalError:
        return None
    return embedded
```
Keep the `None`-on-missing-table degradation and the empty-set display gate (`staleness.py:70-80`). For per-result marking, use the one display-gate probe + indexed PK lookups (RESEARCH Pattern 3) instead of materializing the set; update the module docstring's batching rule (lines 23-27) to distinguish vec0 (unindexed metadata, batch) from the shadow (PK, per-result probe).

---

### `src/sif/search/context_attach.py` (utility, read + transform)

**Analog:** itself for semantics; `src/sif/embedding/cache.py` for the module-level resource shape

**Matching semantics that must stay verbatim** (`context_attach.py:46-63`):
```python
    if not results:
        return results
    cursor = db.execute(
        "SELECT target_id, content FROM contexts WHERE context_type = 'path' ORDER BY updated_at"
    )
    context_map = {normalize_path(row["target_id"]): row["content"] for row in cursor.fetchall()}
    for result in results:
        key = normalize_path(result.path)
        if key in context_map:
            result.context_description = context_map[key]
    return results
```
Wrap only the query+dict build in the cache; the key must be the resolved DB path (never `id(conn)`; `sqlite3.Connection` is neither attribute-able nor weak-referenceable — RESEARCH Pattern 4). Module-level connection lifecycle is modeled on `cache.py:17-29` (`_connection` contextmanager) but the sentinel is long-lived: create lazily, guard with `threading.Lock`, close via `atexit`, and expose `reset_context_cache()` for tests.

**Single enrichment owner** (`context_attach.py:66-85`) — add only an optional `vectors_untrusted: bool = False` keyword; existing two-argument monkeypatched tests must keep working:
```python
    return mark_vector_staleness(db, attach_path_contexts(db, results))
```

---

### `src/sif/indexing/embed_writer.py` (new — service, batch/streaming)

**Analog:** `src/sif/indexing/watcher.py` `_EmbedSession.embed_documents` — the existing embed-outside-transaction + short-write-transaction shape (D-18 lifts it):
```python
                chunks = chunker.chunk(doc.content)
                if not chunks:
                    continue
                # Embedding compute never runs inside an open write transaction.
                vectors = manager.embed([chunk.content for chunk in chunks]).embeddings
                # One short vector-write txn: chunk rows + batched vec0 inserts.
                with self._conn:
                    for sequence, chunk in enumerate(chunks):
                        chunk.document_id = doc.id
                        chunk.sequence = sequence
                        chunk_repo.create(chunk)
                    searcher.add_embeddings_batch(
                        [(chunk.id, doc.id, chunk.id, vector)
                         for chunk, vector in zip(chunks, vectors, strict=True)]
                    )
```
(`watcher.py:294-310`.)

**Delete-before-insert + completeness predicate** — copy from `cli/commands/index.py:180-187` and `341-345`:
```python
def _needs_embedding(live_chunk_ids, embedded_chunk_ids, force) -> bool:
    return force or not live_chunk_ids or live_chunk_ids != embedded_chunk_ids
...
    chunk_repo.delete_by_document(doc.id)
    vector_searcher.delete_embeddings_by_document(doc.id)
```
The writer replaces the per-collection `with db.connection:` block (`index.py:332-374`) with one `with conn:` per document; memory is bounded by one document's chunks (batch slice with `settings.batch_size` before the manager call).

**Failure isolation analogue** — the watcher's per-path loop (`watcher.py:289-316`) shows the "record local failure, continue, re-queue" shape; promote systemic failures (model load, identity mismatch, sanity) to abort after prior per-document commits, then raise one `click.ClickException` outside any transaction, mirroring `index.py:383-391`:
```python
        console.print(f"\n[green]Embedding complete: {total_chunks} chunks embedded[/green]")
        if failed_collections:
            raise click.ClickException(
                f"Embedding failed for {len(failed_collections)} collection(s): "
                + ", ".join(failed_collections)
            )
```

**Sanity checks** — no existing analog; implement RESEARCH Pattern 5's `validate_batch` (count, dimension, finite, L2 norm). Use `math`, not numpy, to match the embedder's stdlib-only normalization style. Reject whitespace-only chunks before embedding (`if c.content.strip()`), consistent with the `if not chunks: continue` guard in the watcher.

---

### `src/sif/indexing/watcher.py` (service, event-driven + batch)

**Analog:** itself — `_EmbedSession` (`watcher.py:190-326`)

Keep the lazy, fail-soft session contract (`watcher.py:215-253`): `ensure_ready` loads the manager, then constructs the searcher. Replace the inline dimension check (`318-326`) with the identity module's shared `FLOAT[n]` read, and add `ensure_legacy_identity` + `check_identity(mode="embed")` here. Replace the per-path body (`294-310`) with `StreamingEmbedWriter.embed_document(doc)`. A systemic failure keeps the existing one-event + disable-session behavior (`_notify`, `250-252`); the `_pending_retry` re-queue (`213`, `311-316`) is unchanged.

---

### `src/sif/indexing/incremental.py` (service, per-file batch)

**No change expected** — it already purges through `create_embedding_purger` (`incremental.py:88-94`) and `delete_embeddings_by_document` (`452-458`, `523-530`), so shadow maintenance rides in automatically once `VectorSearcher` owns it. Add a parity test only.

---

### `src/sif/database/maintenance.py` (new — service, file-I/O + maintenance)

**Analog:** partial — no vacuum/backup precedent exists. Compose from:

**Flock + timeout recipe** — `database/locking.py:42-99`:
```python
@contextmanager
def index_lock(db_path: Path, timeout_s: float, on_wait: Callable[[], None] | None = None):
    ...
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    ...
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
```
Remember the documented D-02 semantics (`locking.py:83-92`): the deadline breaks to unlocked execution — the SQLite write lock + busy timeout are the real serialization.

**Connection + pragma recipe** — `database/factory.py:48-77` (`create_connection`) and the shared constant `WAL_CHECKPOINT_TRUNCATE = "PRAGMA wal_checkpoint(TRUNCATE)"` at `factory.py:45`. Maintenance may set `PRAGMA busy_timeout` on its own connection; do not duplicate the WAL/synchronous recipe — call `create_connection`.

**Transaction boundary** — `cli/main.py:240-262` cleanup shows the `with db.transaction() as conn:` style for reconcile; vacuum/backup must run *outside* it. `Database.transaction` (`database.py:46-55`) commits explicitly.

**CLI error translation** — `cli/error_handling.py:31-66` shows the established boundary shape: catch only foreseeable classes, close the handle, raise remedy-bearing `click.ClickException`; never a catch-all in the command body (D-04 in that module's docstring). Translate busy/locked to a `MaintenanceBusyError` -> `ClickException` retry wording inside maintenance or the command boundary, matching `index.py:316-319`:
```python
                try:
                    vector_searcher = VectorSearcher(db.connection, embedding_dim)
                except RuntimeError as e:
                    raise click.ClickException(f"Vector store unavailable: {e}") from e
```

**Reconcile helper** — identical SQL to RESEARCH Pattern 3; call it from `cleanup_cmd` inside the existing transaction (`main.py:242-258`) and from vacuum in a short `with conn:` before the checkpoint.

**Backup default path** — derive from `Settings.get_db_path()` (`settings.py:391-400` per RESEARCH; default `data_dir / "sif.db"`), i.e. `db_path.parent / "backups"`. Use `Path.mkdir(mode=0o700)`; `os.chmod(output, 0o600)` after verification.

---

### `src/sif/cli/commands/index.py` (controller, batch + request-response)

**Analog:** itself

**Command registration/import style** — top of file (`index.py:1-34`): `click`, `Console`, repository imports, `index_lock`. New `@index_group.command("vacuum")` / `("backup")` follow `update_cmd` (`40-90`) and `embed_cmd` (`190-391`).

**Open pattern** (`index.py:215-217`) — every command starts with the shared boundary:
```python
    with open_initialized_database(index_path, Database) as db:
```

**Embedder load + probe-free dimension** (`index.py:229-244`) — keep this exact ordering for the identity check: load eagerly, read `get_model_info()["embedding_dim"]`, probe only if not an int:
```python
        try:
            manager = EmbeddingManager.from_settings(settings)
            manager.load_model()
        except ImportError as e:
            raise click.ClickException(f"Embedding backend not installed: {e}") from e
        except Exception as e:
            raise click.ClickException(f"Failed to load embedding model: {e}") from e
        model_dim = manager.get_model_info().get("embedding_dim")
        embedding_dim = (
            model_dim if isinstance(model_dim, int) else len(manager.embed_single("probe"))
        )
```

**Lock placement** (`index.py:275-289`) — below model load and dimension check; reuse the `on_wait` console line verbatim for the two new commands.

**Streaming rewrite target** — replace `with db.connection:` per collection (`index.py:332-374`) with the shared writer, keeping the `_needs_embedding` resume skip and "count only after commit" comment/behavior (`375-377`).

---

### `src/sif/cli/main.py` (controller, request-response)

**Analog:** itself

**`cleanup` reconcile** — add the reconcile call inside the existing transaction (`main.py:242-258`):
```python
            with db.transaction() as conn:
                cursor = conn.execute("""
                    DELETE FROM document_chunks
                    WHERE document_id NOT IN (SELECT id FROM documents)
                """)
                ...
                except sqlite3.OperationalError:
                    embeddings_removed = 0
```
Keep the swallowed `OperationalError` for a missing vec0 table; the reconcile helper must itself no-op when `embedded_documents` is absent.

**`status` vector lag** — `_vector_lag_text` (`main.py:141-164`) currently iterates `SELECT id FROM documents` against the set. Switch to an anti-join on the shadow while keeping the returned strings byte-identical (`"n/a"`, `"none (no vectors indexed)"`, `"1 document"`, `"N documents"`).

---

### `src/sif/search/hybrid.py` (service, request-response)

**Analog:** itself

**Optional-constructor-arg pattern** (`hybrid.py:199-224`) — add `identity_check: Callable[[sqlite3.Connection], bool] | None = None` in the same style as `parse_prefix`, stored on the instance; do not add a new module import of the identity module at import time if it risks a cycle — a callable injected by callers avoids the import entirely.

**Query-role call sites** (`hybrid.py:100-104`, `267-282`) — replace the two `embedder.embed(...)` calls (hybrid query, `vec:`, `hyde:`) with the type-aware helper from RESEARCH Pattern 2 (`getattr(type(embedder), "embed_query", None)` — deliberately class-level so MagicMocks do not auto-create the method).

**Single enrichment exit** (`hybrid.py:269`, `275`, `282`, `375`) — pass `vectors_untrusted=True` only when the cached identity check is true; otherwise call the existing two-argument form so Phase 19 golden/mock tests are untouched.

---

### `src/sif/search/expansion.py` (service, request-response)

**Analog:** itself — `expansion.py:77-110`
```python
            query_embedding = self._embedding_manager.embed_single(query)
            ...
            candidate_embeddings = self._embedding_manager.embed(candidate_list)
```
Swap to `embed_query` / `embed_queries` only when those methods exist on the manager type; both are query-role per D-06.

---

### `src/sif/cli/commands/search.py` (controller, request-response)

**Analog:** itself — `vsearch` (`search.py:757-804`)

Embeddings are computed *before* the DB opens (`757-758`), so the identity check must run after `open_initialized_database` and before `VectorSearcher` construction; on a mismatch/width error raise the remedy-bearing `ClickException` (RESEARCH Open Q2). Keep the existing `enrich_results` single-call comment/pattern (`801-804`):
```python
            results = searcher.search(query_embedding, options)
            # CORR-05 (Plan 19-04): the direct vector exit owns exactly one
            # enrichment (the pipeline is not involved on this path).
            results = enrich_results(db.connection, results)
```

---

### `src/sif/cli/commands/bench.py` (controller + wrapper, batch)

**Analog:** itself — `BenchHarness` / `CachedEmbedder` (`bench.py:53-96`)
```python
@dataclass
class BenchHarness:
    db: Database
    embedder: Embedder | None
    embedding_dim: int

class CachedEmbedder:
    def __init__(self, inner: Embedder) -> None:
        self._inner = inner
        self._cache: dict[str, list[float]] = {}

    def embed(self, text: str) -> list[float]:
        if text not in self._cache:
            self._cache[text] = self._inner.embed(text)
        return self._cache[text]
```
Add `identity_check` to the dataclass and a `(role, text)` memo key with `embed_query`/`embed_queries`/`embed_documents` methods that delegate to the inner model (falling back to `embed`) — do not change existing `embed` output.

---

### `src/sif/cli/commands/eval.py` (controller, batch)

**Analog:** itself — pipeline hoist (`eval.py:647-654`, `702-713`)
```python
    pipeline = SearchPipeline(
        db.connection,
        embedder=embedder,
        embedding_dim=embedding_dim,
        default_search_type="hybrid" if embedder is not None else "bm25",
        parse_prefix=False,
    )
    return lambda query: pipeline.search(query, options)
```
`_load_embedder` returns `(manager, embedding_dim, model_identity)` in the RESEARCH sketch; build the search-mode closure there and pass it into the hoisted pipeline. Reuse the existing `try: ... except (sqlite3.Error, OSError) as e: raise click.ClickException(...)` boundary (`696-701`).

---

### `src/sif/mcp/backend.py` (provider, async request-response)

**Analog:** itself — `SearchBackend.__init__` (`backend.py:92-135`)
```python
        db = Database(self.db_path)
        try:
            db.init_schema(embedding_dim=self.settings.embedding_dim)
        finally:
            db.close()

        try:
            factory = EmbeddingModelFactory()
            ...
            self._embedder = factory.create_model(...)
        except Exception:
            logger.warning("Failed to load embedder; vector search will be unavailable")
```
Pass the backend's settings-only identity into `init_schema` (legacy-assumed write) and build the full identity after the embedder load; hand a search-mode check closure into `hybrid_search` (around `146+`). Keep the existing "failed embedder disables vectors, one warning" contract for the BM25 degradation path — an identity mismatch must not change it beyond the one warning + `vectors_stale` marks.

---

### Tests (new + modified)

**Analogs:** `tests/unit/search/test_staleness.py` (real vec0 battery), `tests/unit/database/test_schema.py` (marker/migration battery), `tests/integration/test_embed_idempotency.py` (real DB + mocked manager), `tests/unit/cli/test_index.py` (CliRunner + patch seam)

**Real vec0 fixture + skip discipline** (`tests/unit/search/test_staleness.py:30-73`):
```python
def _vec0_conn(dim: int = 2) -> sqlite3.Connection:
    import sqlite_vec
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
    except Exception:
        conn.close()
        pytest.skip("sqlite-vec not available")
    conn.execute(f"""CREATE VIRTUAL TABLE document_embeddings USING vec0(...)""")
    return conn
```

**Marker/backfill test shape** (`tests/unit/database/test_schema.py:604-636`) — build schema, write a legacy row, drop/delete marker, re-run `create_all`, assert marker content. This is the template for `test_embedded_documents.py`; also note the existing assertion at `627-629` ("only `metadata_values_version` exists") must be widened when `embedded_documents_version` lands.

**CLI test seam** (`tests/unit/cli/test_index.py`): `CliRunner()` + `patch("sif.embedding.manager.EmbeddingManager.from_settings", return_value=mock_manager)`; real `Database(tmp_path)`; assertions on `mock_manager.embed` / `add_embeddings_batch` call shapes (e.g. `test_embed_cmd_batches_across_documents` at 231-301, `test_embed_cmd_default_skips_fully_embedded_document` at 506-530). These are the call-shape tests the streaming rewrite must migrate deliberately to `embed_documents` + per-document calls.

**Integration embed test shape** (`tests/integration/test_embed_idempotency.py:28-51,109-117`): a `MagicMock` manager with a `fake_embed` side effect + vector log, `_invoke_embed(db_path, manager, settings, [])`, real `Database`/`VectorSearcher` for assertions.

**Autouse reset hook precedent** (`tests/conftest.py:54-71`): add `reset_identity_state()` / `reset_context_cache()` autouse fixtures next to `_hermetic_sif_logging`:
```python
@pytest.fixture(autouse=True)
def _hermetic_sif_logging() -> None:
    ...
    sif_logger.handlers = []
    logging.Logger.manager.disable = logging.NOTSET
```

**ConceptEmbedder** (`tests/support/bench.py:42-69+`) — the hermetic, `Embedder`-protocol-only double; identity tests must prove it still routes through plain `embed` (class-level `getattr` helper) and that no prompt kwargs reach it.

---

## Shared Patterns

### Guard / identity gate (replaces "auth" in this local-CLI project)
**Source:** `src/sif/embedding/identity.py` (new), consuming `src/sif/database/repositories.py:662-685`
**Apply to:** `schema.py` init, `index.py` embed, `watcher.py` embed, `search.py` vsearch, `hybrid.py` pipeline, `mcp/backend.py`, `bench.py`, `eval.py`
Mode matrix: `init` width-only; `embed` fail-fast on mismatch, write no vectors; `search` warn once per process (`identity.py` owns the `(stored, current)` set) + mark results; BM25-only never checks. Comparison is field-wise with unknown-tolerance, never fingerprint equality.

### Error handling / remedy culture
**Source:** `src/sif/cli/error_handling.py:23-66`, `src/sif/cli/commands/index.py:234-237,316-319`
**Apply to:** all new CLI commands and call-site wrappers
```python
    except (sqlite3.Error, OSError) as e:
        raise click.ClickException(_database_remedy(index_path, e)) from e
```
Name cause + fix: stored-vs-current identity, retry wording for busy, required-vs-available bytes for the disk precheck.

### Transactions / locking
**Source:** `src/sif/database/factory.py:48-77`, `src/sif/database/locking.py:42-99`, `src/sif/database/database.py:46-55`
**Apply to:** streaming writer, shadow maintenance, maintenance commands
- Factory connections are `isolation_level="IMMEDIATE"`; `with conn:` == BEGIN IMMEDIATE + commit.
- Embedding compute always outside any transaction; writes in one short `with conn:` per document.
- Long writers take `index_lock(db_path, settings.lock_wait_timeout, on_wait=...)`; maintenance runs outside `Database.transaction()`, checkpoints with `WAL_CHECKPOINT_TRUNCATE`.

### Detection-gated idempotent migrations
**Source:** `src/sif/database/schema.py:277-316`
**Apply to:** shadow backfill, legacy identity write, `drop_all` ordering
Fresh/migrated DBs pay one kv read; marker only after a complete pass; lazy imports to dodge cycles.

### SQL discipline
**Source:** entire codebase (e.g. `vector.py:345-352`, `staleness.py:47`)
Constant query strings, parameterized values only; `PRAGMA` values from typed ints; no user-string interpolation (backup paths go through Click types and path validation, never SQL).

### Logging / output hygiene
**Source:** `manager.py:14`, `context_attach.py` docstrings, `hybrid.py` filter notice
`get_logger(__name__)`; warnings/notices on stderr; stdout/JSON stays machine-clean; one warning per process for identity mismatch and legacy identity.

### Generator-owned docs
**Source:** `Makefile:73-76`
**Apply to:** settings fields + new `index vacuum`/`index backup` commands — run `python scripts/generate_cli_ref.py` + `python scripts/generate_config_ref.py` (or `make docs-generate`); never hand-edit `docs/cli-reference.md` or `docs/configuration.md`.

---

## No Exact Analog Found

Files with no exact role+data-flow match; the planner should fall back to the RESEARCH patterns above plus the partial analogs named.

| File | Role | Data Flow | Reason / Use Instead |
|------|------|-----------|----------------------|
| `src/sif/database/maintenance.py` | service (ops) | file-I/O | No VACUUM/online-backup code exists. Compose from `locking.py` (flock), `factory.py` (connection + checkpoint constant), `main.py` (transaction/reconcile), RESEARCH Pattern 6 for call shapes. |
| `src/sif/embedding/identity.py` | service | CRUD + transform | No persisted identity/fingerprint module exists. Compose from `schema.py` marker template + `IndexMetaRepository` + the three inline guards. |
| `src/sif/embedding/prompts.py` | utility | transform | No prompt/model-capability table exists. Compose from `factory.py` dispatch style + `Settings` validator style. |
| `src/sif/indexing/embed_writer.py` | service | batch/streaming | No standalone writer module exists, but the data-flow is already implemented inside `watcher.py:255-316`; lift that shape. |
| `tests/unit/database/test_maintenance.py`, `tests/integration/test_maintenance.py` | test | battery | No maintenance tests exist; use `tests/integration/test_concurrency.py` patterns for reader/writer concurrency and `tests/unit/database/test_factory.py` for file/pragma assertions. |

---

## Plan Ordering Note (from RESEARCH "Suggested plan decomposition")

The dependency chain is identity/role surface -> shadow + readers -> streaming writer -> maintenance -> byte-identical gate. Files above are grouped to make that split mechanical:

- **21-01:** `settings.py`, `prompts.py`, `identity.py`, `embedder.py`, `factory.py`, `manager.py` (+ identity tests)
- **21-02:** `schema.py`, `repositories.py` (IndexMeta only), `vector.py`, `staleness.py`, `database.py`, `mcp/backend.py` init (+ shadow tests)
- **21-03:** `context_attach.py`, `repositories.py` (ContextRepository generation), `tests/conftest.py` (+ context cache tests)
- **21-04:** `embed_writer.py`, `index.py` embed, `watcher.py`, `hybrid.py`, `expansion.py`, `search.py`, `bench.py`, `eval.py` (+ writer tests, call-shape migrations)
- **21-05:** `maintenance.py`, `index.py` vacuum/backup, `cli/main.py` cleanup (+ maintenance tests)
- **21-06:** byte-identical/legacy/garbage/concurrency verification, `make docs-generate`, full quality gate

`repositories.py` and `schema.py` are touched by two plans each — partition ownership or merge those edits into one plan to avoid rebase churn (RESEARCH Parallelism note).

## Metadata

**Analog search scope:** `src/sif/{embedding,database,search,indexing,cli,mcp,config,core,models}`, `tests/{unit,integration,support}`, `Makefile`
**Files read this session:** 30 (full or targeted non-overlapping ranges)
**Tracked-source verification:** `git ls-files --` on every analog path (all tracked); new module paths confirmed absent
**Pattern extraction date:** 2026-11-15
**HEAD:** `f458a92` (dev)
