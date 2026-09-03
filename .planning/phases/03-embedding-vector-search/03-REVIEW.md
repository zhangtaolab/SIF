---
phase: 03-embedding-vector-search
reviewed: 2026-09-03T00:51:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - src/sif/config/settings.py
  - src/sif/embedding/embedder.py
  - src/sif/embedding/factory.py
  - src/sif/embedding/manager.py
  - src/sif/models/embedding.py
  - tests/unit/config/test_settings.py
  - tests/unit/embedding/test_manager.py
  - tests/unit/embedding/test_embedder_impl.py
  - tests/unit/search/test_bm25.py
  - tests/unit/search/test_hybrid.py
  - tests/unit/search/test_vector.py
  - tests/integration/test_search_pipeline.py
findings:
  critical: 3
  warning: 10
  info: 6
  total: 19
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-09-03T00:51:00Z
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Reviewed the Phase 03 embedding/vector-search surface: Settings, embedder implementations, factory, manager, embedding models, and their unit/integration tests. Cross-referenced every import against its dependency module (`sif.embedding.model`, `sif.embedding.cache`, `sif.models.download`, `sif.core.models`, `sif.search.{bm25,vector,hybrid,rrf}`).

All 106 tests in the reviewed test files pass, but empirical verification (real sqlite-vec round-trip, pydantic 2.13 repr behavior, mypy with the project's own `python_version = "3.9"`, real FTS5 query execution) exposed three critical defects that the mocked tests cannot catch:

1. The embedding cache is keyed `"default"` for every model, so switching embedding models silently serves stale vectors from the old model into the index.
2. The package declares `requires-python = ">=3.9"` while the reviewed modules use PEP 604 `X | Y` annotations evaluated eagerly — `import sif` crashes outright on Python 3.9.
3. The BM25 FTS query is built from raw user input with no escaping; common queries (`C++`, `a-b`, an unbalanced quote, a trailing `AND`) raise `sqlite3.OperationalError`, unhandled in the CLI.

Additionally, the project's own quality gate is failing: `mypy src/sif` reports 76 errors in the embedding/config modules alone, including the return-type fabrications in `factory.py`.

## Critical Issues

### CR-01: Embedding cache is not segmented by model — stale cross-model embeddings silently served

**File:** `src/sif/embedding/manager.py:128,143-144`
**Issue:** `EmbeddingManager.embed()` calls `self._cache.get(text)` and `self._cache.set(text, emb)` without the `model_id` argument. `EmbeddingCache` (src/sif/embedding/cache.py:68, 97-101) supports per-model segmentation (`model_id: str = "default"`), but the manager hardcodes `"default"` for every model. Since `cache_embeddings` defaults to `True` (settings.py:146-149) and `from_settings()` always wires a cache, any switch of `SIF_MODEL_NAME` / `SIF_MODEL_TYPE` makes the manager return cached embeddings computed by the *previous* model for any unchanged chunk text — wrong dimension and wrong semantic space. The response then reports `dimensions = self._model.dimension` (manager.py:155), actively misdescribing the returned vectors. The indexer (src/sif/indexing/indexer.py:200-212) and `sif index embed` (src/sif/cli/commands/index.py:260-274) consume these directly, so the vector index is silently populated with embeddings from a different model. No test covers cache/model interplay.
**Fix:**
```python
# manager.py — pass the model identity to every cache call
cached = self._cache.get(text, model_id=self._config.model_name)
...
self._cache.set(text, emb, model_id=self._config.model_name)
```

### CR-02: Declared Python 3.9 support is broken — modules crash on import under 3.9

**File:** `src/sif/config/settings.py:32-41`, `src/sif/models/embedding.py:22-40`, `src/sif/embedding/manager.py:28-30`, `src/sif/embedding/factory.py:21-23`
**Issue:** `pyproject.toml` declares `requires-python = ">=3.9"` and mypy is configured with `python_version = "3.9"`, but these four reviewed modules use PEP 604 union syntax (`str | None`, `Path | None`, `EmbeddingConfig | None`) **without** `from __future__ import annotations` (only `embedder.py` has it). Annotations in class bodies and function signatures are evaluated eagerly, and `X | Y` requires Python 3.10 — so on a real 3.9 interpreter `import sif.config.settings` raises `TypeError: unsupported operand type(s) for |` before any code runs. The package will pip-install on 3.9 (metadata allows it) and then be unusable. Running the project's own gate confirms it: `mypy` reports 76 errors in these modules, including repeated `X | Y syntax for unions requires Python 3.10 [syntax]`. CLAUDE.md's "Target Python 3.9+; use `list[str] | None` union syntax" is self-contradictory and the code picked the 3.10-only half. (Adding `from __future__ import annotations` is not sufficient: pydantic must resolve these annotations at runtime for `Settings`/`EmbeddingConfig`, which still fails on 3.9.)
**Fix:**
```toml
# pyproject.toml — make metadata match reality
requires-python = ">=3.10"
```
(and update CLAUDE.md; alternatively keep 3.9 by converting every union to `Optional[...]`/`Union[...]` across the evaluated-annotation modules, which is a much larger change).

### CR-03: BM25 FTS5 query built from raw user input — search crashes on common queries, unhandled in CLI

**File:** `tests/unit/search/test_bm25.py:251-267` (pins the contract); defect in `src/sif/search/bm25.py:143-161` (`_build_fts_query`, cross-referenced)
**Issue:** `_build_fts_query` interpolates raw query terms into FTS5 MATCH syntax (`f"{term}*"`). Verified against a real FTS5 table: `sif search "C++"` → `fts5: syntax error near "+"`; `"hello \"world"` → `unterminated string`; `"foo AND"` → `fts5: syntax error near "AND"`; `"a-b"` → `no such column: b`. These are ordinary queries for a knowledge-base tool (hyphenated filenames, quoted phrases, boolean-looking words). `BM25Searcher.search` is invoked with no try/except in the CLI (src/sif/cli/commands/search.py:158-160), so users get an unhandled `sqlite3.OperationalError` traceback. The reviewed tests only assert the naive happy path (`"hello*"` / `"hello* AND world*"`), locking in the unescaped behavior with zero negative cases.
**Fix:** Quote each term as an FTS5 phrase before appending the prefix operator, and strip embedded quotes:
```python
def _build_fts_query(self, query: str) -> str:
    terms = [t.replace('"', "") for t in query.split() if t.replace('"', "")]
    if not terms:
        return "*"
    return " AND ".join(f'"{term}"*' for term in terms)
```
Add tests for `"C++"`, `"a-b"`, unbalanced quotes, and trailing boolean words.

## Warnings

### WR-01: Factory return types are fabricated — returns `Embedder` impls annotated as `EmbeddingModel`

**File:** `src/sif/embedding/factory.py:18-92` (cross-ref `src/sif/embedding/model.py:9-99`)
**Issue:** `create_model(...) -> EmbeddingModel` but every branch returns `SentenceTransformerEmbedder` / `LlamaCppEmbedder` / `ModelScopeEmbedder`, which implement the `Embedder` protocol (src/sif/core/models.py:278-292) and are *not* subclasses of the `EmbeddingModel` ABC (no `load`/`unload`/`embed_single`). mypy confirms: `Incompatible return value type (got "LlamaCppEmbedder", expected "EmbeddingModel") [return-value]` (x3) and `manager.py:81: Incompatible types in assignment (expression has type "EmbeddingModel", variable has type "Embedder | None")`. The `EmbeddingModel` ABC and the duplicate `EmbeddingModelFactory` Protocol in `model.py` are parallel dead abstractions (nothing instantiates `EmbeddingModel`; the Protocol duplicates the concrete class). The `ModelType` re-export also trips mypy (`Module "sif.embedding.model" does not explicitly export attribute "ModelType"`).
**Fix:** Annotate `create_model` and the `_create_*` helpers as `-> Embedder`; delete `sif/embedding/model.py` (or fold its `count_tokens` into the protocol) and fix the `__init__.py` re-exports.

### WR-02: `**kwargs: dict[str, any]` uses the builtin `any` as a type

**File:** `src/sif/embedding/factory.py:23,41,57,69,77,85`; `src/sif/embedding/model.py:113`
**Issue:** `any` is the builtin function, not `typing.Any`. mypy: `Function "builtins.any" is not valid as a type [valid-type]` — 6 occurrences in the reviewed file. The annotation is also semantically wrong for `**kwargs` (each keyword arg isn't a `dict`). These errors contribute to the failing `mypy src/sif` gate documented in CLAUDE.md.
**Fix:** `from typing import Any` and `**kwargs: Any`.

### WR-03: `embed()` silently drops failed slots — embeddings can misalign with input texts

**File:** `src/sif/embedding/manager.py:156-157`
**Issue:** `embeddings=[e for e in embeddings if e is not None]` filters out any slot that was neither cached nor filled by `embed_batch` (e.g., a backend returning fewer vectors than texts). The response then contains fewer embeddings than input texts with no error, so position `i` no longer corresponds to `texts[i]`. Both consumers zip silently against this list (`indexer.py:203`, `cli/commands/index.py:265`), so trailing chunks get no embedding at all — silent data loss in the index instead of a loud failure.
**Fix:**
```python
if any(e is None for e in embeddings):
    raise RuntimeError(
        f"Embedding backend returned {sum(e is None for e in embeddings)} fewer embeddings than inputs"
    )
```

### WR-04: `normalize` parameter is accepted and documented but ignored

**File:** `src/sif/embedding/manager.py:102-107,164-169`
**Issue:** `embed(texts, normalize=True)` and `embed_single(...)` declare and document a `normalize` flag, but it is discarded (`# noqa: ARG002`) and every backend always L2-normalizes (`normalize_embeddings=True` in embedder.py:85,97-101). A caller requesting unnormalized vectors silently gets normalized ones — an API contract violation, and combined with CR-01 it means cache behavior can never be tuned either.
**Fix:** Either plumb the flag into the backends (and into the cache key), or remove the parameter from the public signatures.

### WR-05: `n_gpu_layers` and other documented settings are silently dropped by the factory

**File:** `src/sif/embedding/factory.py:38-52` (cross-ref `src/sif/embedding/embedder.py:113-151`, `src/sif/config/settings.py:67-71`)
**Issue:** `manager.load_model()` passes `embedding_dim`, `max_tokens`, `n_gpu_layers`, `n_ctx`, `api_key`, `api_base`, `cache_dir` (manager.py:81-92), but `_create_gguf_model` reads only `n_ctx`/`n_threads`/`verbose`, and `LlamaCppEmbedder.__init__` neither accepts `n_gpu_layers` nor passes it to `Llama(...)`. The documented setting "Number of GPU layers for GGUF models" therefore does nothing — a user who sets `SIF_N_GPU_LAYERS=32` gets silent CPU inference. Likewise `embedding_dim`/`max_tokens`/`api_key`/`api_base` are dropped everywhere (`api_key` will be required the moment the `openai` backend stops raising `NotImplementedError`), and `_create_modelscope_model` never forwards `force_download`. `Settings.embedding_dim` is never validated against the loaded model's actual dimension.
**Fix:** Add `n_gpu_layers: int = 0` to `LlamaCppEmbedder.__init__` and pass `n_gpu_layers=n_gpu_layers` to `Llama(...)`; in the factory, read `n_gpu_layers=kwargs.get("n_gpu_layers", 0)`.

### WR-06: `model_path` / `reranker_model_path` are not `expanduser`-ed, unlike `db_path`/`cache_dir`

**File:** `src/sif/config/settings.py:171-177`
**Issue:** The `expand_path` validator (mode="before") covers only `"db_path", "cache_dir"`. A user setting `SIF_MODEL_PATH=~/models/qwen.gguf` gets `Path("~/models/qwen.gguf")` verbatim, which does not resolve; `LlamaCppEmbedder` then fails to open the model. Same for `reranker_model_path`. The inconsistent treatment within the same Settings class makes this easy to hit.
**Fix:** `@field_validator("db_path", "cache_dir", "model_path", "reranker_model_path", mode="before")`.

### WR-07: `EmbeddingConfig.api_key` leaks in `repr()` despite `exclude=True`

**File:** `src/sif/models/embedding.py:35`
**Issue:** Verified on the project's pydantic (2.13.3): `repr(EmbeddingConfig(api_key="sk-supersecret"))` contains the secret — `exclude=True` only affects `model_dump()`, not `__repr__`. `Settings.api_key` is correctly protected with `repr=False` (settings.py:72-76) and `test_settings.py:46-50` asserts that, but the Pydantic model that actually travels through `EmbeddingManager.from_settings()` is unprotected; any debug log, traceback, or print of the config exposes the key.
**Fix:** `api_key: str | None = Field(None, exclude=True, repr=False)`.

### WR-08: `ModelScopeEmbedder` picks the model directory from an unsorted `glob("*")[0]`

**File:** `src/sif/embedding/embedder.py:201-207`
**Issue:** After download, the code does `model_dirs = list(model_path.glob("*"))` and uses `model_dirs[0]` if it is a directory. `Path.glob` ordering is filesystem-dependent (not sorted, not stable), so if the snapshot directory contains any subdirectory (auxiliary exports, `onnx/`, etc.) the embedder may load that subdirectory as "the model" — a nondeterministic failure that depends on directory insertion order. The mocked tests never exercise this logic (`download.return_value = Path("/tmp/model")` doesn't exist, so glob is empty and the fallback path is taken).
**Fix:** Look for a known marker file instead, e.g. `next((p for p in model_path.glob("*/config.json")), model_path / "config.json")` parent resolution, or `sorted(model_path.glob("*"))` plus explicit `config.json` check.

### WR-09: Vector tests never touch a real sqlite-vec, and the tested `chunk_id=None` contract is invalid against the real backend

**File:** `tests/unit/search/test_vector.py:51-73` (cross-ref `src/sif/search/vector.py:160-178`)
**Issue:** All assertions are string-matches against `MagicMock` (`assert "vec_f32(?)" in sql`). `sqlite_vec` **is installed in the venv**, so a real round-trip is cheap — and when run, it disproves the tested contract: the test explicitly passes `("e2", "d2", None, [0.3, 0.4])` and asserts the batch succeeds, but a real vec0 table rejects NULL for a TEXT metadata column: `sqlite3.OperationalError: Expected text for TEXT metadata column chunk_id, received NULL` (verified). `add_embeddings_batch`'s own annotation `chunk_id: str | None` invites this. The production caller happens to pass `chunk.id`, so the bug is latent, but the unit test provides false confidence for exactly the case it claims to cover. (The SELECT path — MATCH/k with JOINs and the collection filter — does execute correctly against real sqlite-vec; only inserts with NULL fail.)
**Fix:** Change the contract to `chunk_id: str` and coerce `None -> ""` inside `add_embeddings_batch`, and add one real-DB round-trip test: `sqlite3.connect(":memory:")` + `sqlite_vec.load(conn)` + create vec0 table + insert + search.

### WR-10: `test_from_settings_passes_api_key_and_api_base` writes a real cache database to the user's home

**File:** `tests/unit/embedding/test_manager.py:11-23`
**Issue:** `EmbeddingManager.from_settings(settings)` constructs `EmbeddingCache(config.cache_dir)` because `cache_embeddings` defaults to True, and `settings.get_cache_dir()` mkdirs the real platform cache dir. Verified: running this test created `/Users/forrest/Library/Caches/sif/embeddings_cache.db`. Tests must not mutate state outside the repo/tmp tree — this leaves droppings on every developer/CI machine and can couple tests to pre-existing cache contents.
**Fix:** `settings = Settings(..., cache_embeddings=False)` or monkeypatch a `tmp_path` cache dir.

### WR-11: Search tests build the entire "integration" on `MagicMock` DBs

**File:** `tests/integration/test_search_pipeline.py:14-17,23-194`
**Issue:** Despite being the integration suite for Phase 03's core deliverable, every test mocks the sqlite3 connection; no test loads the real schema (`SchemaManager`), real FTS5 tables, or real sqlite-vec. Consequently the actual pipeline (schema → index → BM25/vec/hybrid search → RRF) is never executed end-to-end anywhere in the suite — which is precisely why CR-03 (FTS injection), WR-09 (NULL chunk_id), and the real-dimension behavior are all invisible to CI. The fixtures also encode fragile `execute.side_effect` ordering assumptions that break on any refactor of query sequencing.
**Fix:** Add a genuine integration test: real `Database` on a tmp file (or `:memory:`), `init_schema()`, insert 3 documents via repositories, run `SearchPipeline.search()` for all three modes, assert ordering/dedup.

## Info

### IN-01: `SimpleEmbedder` docstring says TF-IDF; implementation is a degenerate periodic hash; dead state

**File:** `src/sif/embedding/embedder.py:264-306`
**Issue:** Class/method docstrings claim "TF-IDF" but the code is sha256-hash based. Because `idx = i % len(hash_bytes)` with a 32-byte digest, every embedding has period 32 — dimensions `i` and `i+32` are identical for *all* texts, so a 384-dim vector carries only 32 degrees of freedom and cosine similarity is noise. `self.vocabulary` and `self._doc_count` are never used. Nothing in `src/` constructs it (only `create_embedder`, itself unused outside tests) — so it is effectively test-only code that looks like a production fallback.
**Fix:** Fix the docstrings, delete `vocabulary`/`_doc_count`, and either derive per-dimension values from a proper hash stream (e.g., `hashlib.shake_256(text.encode()).digest(self._dimension)`) or delete the class if the fallback is no longer intended.

### IN-02: Duplicate factory layers with divergent type keys and defaults

**File:** `src/sif/embedding/embedder.py:309-330` vs `src/sif/embedding/factory.py:15-92`
**Issue:** Two parallel factories: `create_embedder("sentence_transformer")` (string keys, default model `all-MiniLM-L6-v2`) and `EmbeddingModelFactory.create_model(ModelType.SENTENCE_TRANSFORMERS, ...)` (enum keys, config default `Qwen/Qwen3-Embedding-0.6B`). `ModelScopeEmbedder`'s own default is a third value (`iic/gte_Qwen2-7B-instruct`). Nothing in `src/` uses `create_embedder`.
**Fix:** Remove `create_embedder` (or make it a thin alias of the enum-based factory) and centralize default model ids in one place.

### IN-03: `get_model_info()` returns different keys depending on load state

**File:** `src/sif/embedding/manager.py:183-200`
**Issue:** When unloaded it returns `{"loaded": False, "model_name": ...}`; when loaded it returns `{"loaded": True, "model_id": ...}`. Callers must handle two different key names for the same concept.
**Fix:** Use `model_id` (or `model_name`) in both branches.

### IN-04: `test_model_type_validation_accepts_valid_values` omits `huggingface`

**File:** `tests/unit/config/test_settings.py:16`
**Issue:** The validator (settings.py:155) accepts five backends including `huggingface`; the test's `valid_types` list covers only four, so the fifth accepted value is untested.
**Fix:** Add `"huggingface"` to the list.

### IN-05: `__builtins__["__import__"]` relies on implementation-defined behavior

**File:** `tests/unit/embedding/test_embedder_impl.py:230,349,493`
**Issue:** Whether `__builtins__` is a dict or the module itself differs between `__main__` and imported modules (CPython implementation detail). It happens to be subscriptable under pytest here, but the portable form is simply `builtins.__import__`.
**Fix:** `import builtins; original_import = builtins.__import__`.

### IN-06: Settings tests are not hermetic against real env vars / `.env`

**File:** `tests/unit/config/test_settings.py:8-11,28-31`
**Issue:** `Settings()` reads the process environment and a `.env` from CWD (`env_file=".env"`). A developer or CI shell exporting `SIF_MODEL_TYPE` (or a repo-root `.env`) flips `test_default_model_type_is_modelscope` and `test_api_base_validation_*` without any code change. Only one test (line 53) uses `monkeypatch`.
**Fix:** Wrap default-value tests in `monkeypatch.delenv("SIF_MODEL_TYPE", raising=False)` (or clear all `SIF_*` vars) before constructing `Settings()`.

---

_Reviewed: 2026-09-03T00:51:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

_Empirical verification performed during review: full run of all 12 reviewed test files (106 passed); pydantic 2.13.3 repr check for WR-07; mypy with project config (76 errors); real FTS5 execution for CR-03; real sqlite-vec insert/search round-trip for WR-09; filesystem check for WR-10._
