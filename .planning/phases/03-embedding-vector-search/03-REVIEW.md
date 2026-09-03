---
phase: 03-embedding-vector-search
reviewed: 2026-09-03T04:02:30Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - pyproject.toml
  - src/sif/config/settings.py
  - src/sif/embedding/embedder.py
  - src/sif/embedding/factory.py
  - src/sif/embedding/manager.py
  - src/sif/models/embedding.py
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
  critical: 3
  warning: 11
  info: 7
  total: 21
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-09-03T04:02:30Z
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

Fresh re-review after gap-closure plan 03-07 (OpenAI embedding backend). The 03-07 work itself is solid: `OpenAIEmbedder` follows the lazy-import pattern with the `sif[openai]` install hint, `api_key` is passed only to the `OpenAI(...)` constructor and never logged or interpolated inside the new code, `embed_batch` validates response length per slice and raises before any cache write, the dimension mismatch error names both values plus `SIF_EMBEDDING_DIM`, the factory wiring is correct, and the new tests (fake `openai` module, dispatch matrix, CLI end-to-end tracer) are well constructed. All 192 in-scope tests pass and ruff is clean on the in-scope files.

However, three blockers remain — two carried over from the previous review and unfixed, one environmental consequence of them — and the new OpenAI backend materially aggravates the first: the embedding cache is not segmented by model, so switching between the newly-supported backends silently serves stale wrong-model (wrong-dimension) vectors under default settings. Empirically verified issues: FTS5 crashes on common user queries (`e-mail`, `don't`, `c++`), `repr(EmbeddingConfig(...))` leaks `api_key` while `settings.model_dump()` leaks it the opposite way, and the declared Python 3.9 support is broken at import time. Additional warnings cover the MCP path that 03-07 did not wire (SIF_API_KEY dead-ends there), dead configuration plumbing (`batch_size`), response-order assumptions, and test side effects on the developer's home directory.

Findings marked with cross-references were discovered while tracing the reviewed files' imports/callers; the primary defect location is cited first.

## Critical Issues

### CR-01: Embedding cache is not segmented by model — switching backends silently serves stale wrong-model embeddings

**File:** `src/sif/embedding/manager.py:128,143-144` (cross-ref `src/sif/embedding/cache.py:68,97`)
**Issue:** `EmbeddingCache.get()`/`set()` accept a `model_id` parameter documented as "Model identifier for cache segmentation", but `EmbeddingManager.embed()` never passes it — every model reads and writes the `"default"` bucket, keyed only by content hash. Plan 03-07 makes this acute: with default settings (`cache_embeddings=True`, cache dir `~/.Caches/SIF`), a user who embeds with one backend (e.g. modelscope/Qwen, 1024-dim) and then runs `sif index embed --model-type openai` gets the old model's cached vectors returned for every previously-seen chunk text — no API call, no error. Depending on whether `"probe"` (`src/sif/cli/commands/index.py:272`, which routes through the same cache) is also cached, this either silently poisons the vector index with semantically meaningless vectors from the wrong model, or fails with a confusing sqlite-vec dimension error. `EmbeddingResponse.dimensions` reports the *new* model's dimension while the embeddings carry the *old* model's — an internally inconsistent response. There is no TTL on this cache, so the poisoning is permanent until the user manually deletes the DB.
**Fix:**
```python
# src/sif/embedding/manager.py (embed method)
model_id = self._config.model_name
...
cached = self._cache.get(text, model_id=model_id)
...
self._cache.set(text, emb, model_id=model_id)
```
(Consider including `model_type`/dimension in the key as well, and add a regression test that embeds the same text under two models and asserts both miss the shared bucket.)

### CR-02: BM25 FTS5 query built from raw user input — common queries crash with unhandled `sqlite3.OperationalError`

**File:** `src/sif/search/bm25.py:143-161` (`_build_fts_query`; pinned by `tests/unit/search/test_bm25.py:251-267` which only covers the happy path)
**Issue:** `_build_fts_query` interpolates raw whitespace-split tokens into an FTS5 `MATCH` expression with no escaping. Verified empirically against a real FTS5 table:

```
'e-mail'  -> 'e-mail*'   OperationalError: no such column: mail
"c++"     -> 'c++*'      OperationalError: fts5: syntax error near "+"
"don't"   -> "don't*"    OperationalError: fts5: syntax error near "'"
'foo:bar' -> 'foo:bar*'  OperationalError: no such column: foo
'(paren)' -> '(paren)*'  OperationalError: fts5: syntax error near "*"
'a AND'   -> 'a* AND AND*' OperationalError: fts5: syntax error near "AND"
'"quote'  -> '"quote*'   OperationalError: unterminated string
```

Hyphenated words and apostrophes are ordinary search input for a personal knowledge base. The exception propagates uncaught through `HybridSearcher.search` → `SearchPipeline.search` → `pipeline.search(query, options)` at `src/sif/cli/commands/search.py:505` (no surrounding try/except), so `sif search don't` terminates with a raw traceback instead of results. The docstring also claims phrase/quoted-string handling that does not exist.
**Fix:** Sanitize each token before building the expression — strip FTS5 metacharacters and wrap tokens in double quotes, e.g.:
```python
import re

def _sanitize_term(term: str) -> str:
    # Remove FTS5 metacharacters; keep word characters, digits, and internal -/_/'.
    cleaned = re.sub(r"""["*():^]""", "", term)
    return f'"{cleaned}"' if cleaned else ""

def _build_fts_query(self, query: str) -> str:
    terms = [t for t in (self._sanitize_term(tok) for tok in query.split()) if t]
    if not terms:
        return "*"
    return " AND ".join(terms)
```
(Decide deliberately whether prefix `*` is kept — if kept, append `*` outside the closing quote is invalid; quote-wrapped phrases without `*` are the safe form. Also add tests for the crashing inputs above, and consider catching `sqlite3.OperationalError` at the CLI boundary to degrade gracefully.)

### CR-03: Declared Python 3.9 support is broken — modules crash on import under 3.9

**File:** `pyproject.toml:11,21-24` (`requires-python = ">=3.9"` + 3.9 classifier); `src/sif/config/settings.py:32`, `src/sif/models/embedding.py:22-40`, `src/sif/embedding/manager.py:28-30`, `src/sif/embedding/factory.py:24-27`
**Issue:** These reviewed modules use PEP 604 unions (`Path | None`, `str | None`, `EmbeddingConfig | None`) in eagerly-evaluated annotation positions *without* `from __future__ import annotations` (only `embedder.py` has it — and even there, pydantic resolves annotations via `get_type_hints`, which re-evaluates the strings and still fails on 3.9). On Python 3.9, `import sif.config.settings` raises `TypeError: unsupported operand type(s) for |` at class-definition time, so the package installs (pip honors `>=3.9`) but is unusable. The project's own tooling confirms the fiction: `[tool.mypy] python_version = "3.9"` cannot even type-check the installed `sentence_transformers`/`huggingface_hub` dependencies (verified: `mypy src/sif` aborts with "Pattern matching is only supported in Python 3.10 and greater"). CLAUDE.md's style rule ("Target Python 3.9+; use `list[str] | None` union syntax") is internally contradictory. Note the previous review flagged this and it was not addressed by 03-07, which added more `str | None`/`int | None` annotations to `embedder.py`/`factory.py`.
**Fix:** Either honestly bump the floor (recommended, matching what the code already assumes):
```toml
requires-python = ">=3.10"
classifiers = [... "Programming Language :: Python :: 3.10", ...]  # drop 3.9
```
plus `[tool.mypy] python_version = "3.10"` and updating CLAUDE.md's style section; or convert all annotations in these modules to `Optional[...]`/`Union[...]` and add a 3.9 CI job to prove it.

## Warnings

### WR-01: `EmbeddingConfig.api_key` leaks in `repr()` — violates threat T-03-01's repr requirement

**File:** `src/sif/models/embedding.py:35`
**Issue:** `api_key: str | None = Field(None, exclude=True)` — in pydantic v2, `exclude` only affects `model_dump()`/`model_dump_json()`, not `repr()`. Verified empirically: `repr(EmbeddingConfig(api_key="sk-X"))` contains the key. T-03-01 (03-07 plan, threat table) requires api_key to never appear in reprs. `EmbeddingManager` carries this config on `self._config`; any future debug logging of the config object leaks the secret. `Settings.api_key` got `repr=False` — the two models are hardened in exactly opposite ways.
**Fix:** `api_key: str | None = Field(None, exclude=True, repr=False)`

### WR-02: `Settings.model_dump()` includes `api_key` — serialization leak path

**File:** `src/sif/config/settings.py:72-76`
**Issue:** `Settings.api_key` has `repr=False` but not `exclude=True`. Verified empirically: `str(Settings(api_key="sk-X").model_dump())` contains the key while `repr()` does not. No current call site dumps settings, but any debug/diagnostic dump (the natural reflex when debugging configuration) exfiltrates the secret into logs.
**Fix:** `api_key: str | None = Field(default=None, description="API key for remote embedding models", repr=False, exclude=True)` — and add a test asserting both `repr()` and `model_dump()` are clean.

### WR-03: `EmbeddingManager.embed()` silently drops unfilled slots — embeddings can misalign with input texts

**File:** `src/sif/embedding/manager.py:137-148,157`
**Issue:** If a backend's `embed_batch` returns fewer vectors than requested (misbehaving or partially-failing local backend — the OpenAI ragged guard only protects the openai path), `zip(indices, new_embeddings)` silently truncates, the leftover `embeddings[i]` stay `None`, and the final `[e for e in embeddings if e is not None]` silently shortens the response with no error. `EmbeddingResponse` then violates the 1:1 texts↔embeddings contract, and `embed_cmd` (`src/sif/cli/commands/index.py:265`) zips chunks against embeddings — tail chunks silently get no vectors persisted, or worse, associations shift if a middle slot is dropped after a partial cache fill.
**Fix:** After `new_embeddings = self._model.embed_batch(list(to_embed))`, validate and fail fast:
```python
if len(new_embeddings) != len(to_embed):
    raise RuntimeError(
        f"Embedding model returned {len(new_embeddings)} embeddings for "
        f"{len(to_embed)} inputs"
    )
```
and return `embeddings` directly (asserting none are `None`) instead of filtering.

### WR-04: `OpenAIEmbedder.embed_batch` assumes `response.data` ordering — reordered responses silently corrupt the index

**File:** `src/sif/embedding/embedder.py:399-408`
**Issue:** The class is explicitly designed for OpenAI-*compatible* endpoints via `api_base` (vLLM, LM Studio, Ollama, etc.), but `embed_batch` assumes `response.data[i]` corresponds to `batch[i]`. Each item carries an `index` field precisely because ordering is not guaranteed by every compatible server. A reordered response passes the length check and produces silently wrong chunk→vector associations — strictly worse than the ragged case 03-07 guarded against, because there is no error at all. The new tests' fakes always return in-order data, baking in the assumption.
**Fix:** Validate/normalize per slice:
```python
data = sorted(response.data, key=lambda item: item.index)
if [item.index for item in data] != list(range(len(batch))):
    raise RuntimeError(
        f"Embedding model '{self.model_name}' returned misindexed embeddings ..."
    )
```
(the openai SDK response model always populates `index`).

### WR-05: Dimension cache is keyed by model name only — endpoints cross-contaminate for up to 7 days

**File:** `src/sif/embedding/embedder.py:340,375`
**Issue:** `openai_dim_cache.json` entries are keyed by `self.model_name` alone. Two endpoints serving the same model name with different dimensions (e.g. OpenAI's `text-embedding-3-small` vs. a local server exposing a quantized/`dimensions`-reduced variant under the same name, selected via `SIF_API_BASE`) share one entry: after probing endpoint A, constructing against endpoint B returns A's cached dim for 7 days — either a spurious fail-fast mismatch or, when `embedding_dim=None`, a silently wrong `dimension` for the rest of the run.
**Fix:** Include the endpoint in the key (e.g. `f"{api_base or 'default'}::{model_name}"`) or store `api_base` in the entry and treat a mismatch as a cache miss.

### WR-06: `batch_size` configuration never reaches `OpenAIEmbedder` — `SIF_BATCH_SIZE` silently ignored

**File:** `src/sif/embedding/manager.py:81-92`, `src/sif/embedding/factory.py:70-82`
**Issue:** `Settings.batch_size` ("Batch size for inference", default 32, env `SIF_BATCH_SIZE`) is copied into `EmbeddingConfig.batch_size` but `load_model()` never passes it to the factory, and `_create_openai_model` never forwards it — `OpenAIEmbedder` always slices at its hardcoded default of 64. The new backend is the only one with a real batch-size knob, and it is the one place the setting does not apply. `max_tokens` is likewise passed and silently dropped (documented truncation never happens; acceptable for the API's own limits, but then the plumbing is misleading).
**Fix:** In `_create_openai_model`: `batch_size=kwargs.get("batch_size", 64)` and in `EmbeddingManager.load_model` add `batch_size=self._config.batch_size`.

### WR-07: MCP `SearchBackend` drops `api_key`/`api_base` — `SIF_MODEL_TYPE=openai` via MCP silently loses vector search

**File:** `src/sif/mcp/backend.py:39-50` (cross-file consumer of the reviewed `factory.py`)
**Issue:** The other factory call site constructs the model as `factory.create_model(model_type, model_path, self.settings.model_name)` — no `api_key`, `api_base`, `embedding_dim`, or `cache_dir`. With the openai backend now wired in the factory, MCP users setting `SIF_API_KEY`/`SIF_API_BASE` get `OpenAI(api_key=None, ...)` which raises (no OPENAI_API_KEY either), and the surrounding `except Exception: logger.warning("Failed to load embedder; vector search will be unavailable")` degrades silently. Plan 03-07's goal ("SIF_MODEL_TYPE=openai ... no longer terminates in a load-time error; api_key/api_base ... flow through") is closed on the CLI path but not the MCP path.
**Fix:** Mirror `EmbeddingManager.from_settings`'s kwargs:
```python
self._embedder = factory.create_model(
    model_type,
    model_path,
    self.settings.model_name,
    api_key=self.settings.api_key,
    api_base=self.settings.api_base,
    embedding_dim=self.settings.embedding_dim,
    cache_dir=str(self.settings.get_cache_dir()) if self.settings.cache_embeddings else None,
)
```
(or better, reuse `EmbeddingManager.from_settings` here).

### WR-08: `embed_cmd`'s load-error handlers are unreachable; embedding failures still exit 0

**File:** `src/sif/cli/commands/index.py:211-218,277-278` (cross-ref reviewed `tests/unit/cli/test_index.py:327-328`)
**Issue:** The `try: EmbeddingManager.from_settings(...) except ImportError/Exception` block promises "Embedding backend not installed" / "Failed to load embedding model" handling, but model loading is lazy (first `manager.embed`), so the OpenAI `ImportError` and the dimension-mismatch `RuntimeError` can never be raised there — they surface inside the per-collection `except Exception` as "Error embedding collection" and are swallowed. The command then prints "Embedding complete: 0 chunks embedded" and exits 0 even when every collection failed, breaking scripting/automation. The reviewed CLI test only asserts the two error strings are absent, so the misleading classification and exit code are untested.
**Fix:** Load eagerly inside the first try block (`manager.load_model()` after `from_settings`) so backend/dimension errors hit the dedicated handlers, and make the per-collection failure path track a failure flag that converts to a non-zero exit (`raise click.ClickException(...)` after the loop, or `ctx.exit(1)`).

### WR-09: `test_from_settings_passes_api_key_and_api_base` writes a real cache database to the developer's home

**File:** `tests/unit/embedding/test_manager.py:11-23`
**Issue:** The test constructs `Settings(model_type="openai", ..., embedding_dim=256)` without `cache_embeddings=False` and without clearing `SIF_CACHE_EMBEDDINGS`, so `from_settings` creates `EmbeddingCache(user_cache_dir)` — mkdir plus a real SQLite DB (`embeddings_cache.db`) under the developer's `~/Library/Caches/SIF` (verified present on this machine). Every test run mutates user state outside the repo; sibling tests in `test_factory.py`/`test_openai_embedder.py` carefully disable the cache, this one does not.
**Fix:** Pass `cache_embeddings=False` to the `Settings(...)` constructor (and optionally `monkeypatch.delenv("SIF_CACHE_EMBEDDINGS", raising=False)` for belt-and-braces).

### WR-10: `SearchPipeline` expansion silently drops an expander's first variant — reviewed tests encode the faulty contract

**File:** `tests/unit/search/test_hybrid.py:215-265` (cross-ref `src/sif/search/hybrid.py:224-238`)
**Issue:** The pipeline seeds `queries = [parsed_query]` and then iterates `expanded[1:]`, assuming `QueryExpander.expand()` echoes the original query as element 0. The `QueryExpander` protocol (`src/sif/core/models.py:303-309`) promises only "expand a query into multiple variants" — no echo guarantee. A conforming expander returning `["variant1", "variant2"]` loses `variant1` entirely. Both reviewed tests feed mocks that echo the original (`["query", "query variant"]`), so the suite pins the buggy assumption rather than the protocol.
**Fix:** In `hybrid.py`, deduplicate against the original without slicing: iterate all of `expanded`, skip any variant equal (case-insensitively) to `parsed_query`, and add a test where `expand` returns variants without the original echo.

### WR-11: Settings default test is not hermetic against real env vars / `.env`

**File:** `tests/unit/config/test_settings.py:8-11`
**Issue:** `test_default_model_type_is_modelscope` calls `Settings()` with no kwargs. Pydantic-settings reads `SIF_MODEL_TYPE` from the environment and a `.env` file in the CWD — a developer who followed the README and exported `SIF_MODEL_TYPE=openai` (the exact workflow plan 03-07 documents) gets a red suite. The 03-07 tests in `test_factory.py`/`test_openai_embedder.py` carefully `monkeypatch.delenv` these vars; this file does not.
**Fix:** Wrap with `monkeypatch` clearing the relevant vars (or pass `_env_file=None` and unset `SIF_MODEL_TYPE`):
```python
def test_default_model_type_is_modelscope(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SIF_MODEL_TYPE", raising=False)
    assert Settings().model_type == "modelscope"
```

## Info

### IN-01: Legacy duplicate embedding abstraction still exported from the package root

**File:** `src/sif/embedding/model.py:9-126`, `src/sif/embedding/__init__.py:13-23`
**Issue:** `EmbeddingModel` (an ABC with a `load`/`unload`/`embed` interface incompatible with the `Embedder` protocol the factory actually returns) and the `EmbeddingModelFactory` Protocol remain, and `__init__.py` re-exports them; `mcp/backend.py` imports `ModelType` through this shim. Harmless today (model.py re-exports the canonical `sif.models.embedding.ModelType`) but a consolidation trap.
**Fix:** Delete `model.py`, export `ModelType` from `sif.models.embedding` in `__init__.py`, and update `mcp/backend.py` + `tests/unit/inference/test_embedder.py` imports.

### IN-02: `create_embedder()` free function is dead code and now diverges further — no `openai` branch

**File:** `src/sif/embedding/embedder.py:470-491`
**Issue:** No callers anywhere in `src/` or `tests/`. It uses different type strings ("sentence_transformer", "llama_cpp") than `ModelType`, and 03-07 did not add an `openai` branch — the second factory layer is now strictly less capable than the first.
**Fix:** Delete it (or route it through `EmbeddingModelFactory` if a public function API is wanted).

### IN-03: `EmbeddingManager.embed(normalize=...)` parameter is documented but ignored

**File:** `src/sif/embedding/manager.py:102-107,164-169`
**Issue:** `normalize` is accepted (with `# noqa: ARG002`) and described in the docstring, but never forwarded; all backends normalize unconditionally. `EmbeddingRequest.normalize` (`src/sif/models/embedding.py:61`) is likewise plumbed nowhere. Callers cannot actually get unnormalized vectors.
**Fix:** Either honor it (pass through to backends that support it) or remove the parameter and the model field.

### IN-04: `ModelScopeEmbedder` selects the model directory via unsorted `glob("*")[0]`

**File:** `src/sif/embedding/embedder.py:204-210`
**Issue:** `list(model_path.glob("*"))` order is filesystem-dependent; a snapshot directory containing multiple entries (e.g. a `.temp` dir, `.lock` file — both observed in the real cache dir on this machine) can be picked instead of the model, failing later with an opaque sentence-transformers error.
**Fix:** Filter to directories and prefer a deterministic choice, e.g. pick the entry containing a `config.json`, or `sorted(p for p in model_path.iterdir() if p.is_dir())`.

### IN-05: `_write_dim_cache` performs a non-atomic, unlocked read-modify-write

**File:** `src/sif/embedding/embedder.py:362-382`
**Issue:** Concurrent processes (two `sif` invocations) can interleave read/write and lose other models' entries; a crash mid-`json.dump` truncates the file. Self-healing (corrupt file is treated as a miss and rewritten) so impact is limited to a redundant probe, but the write is also visible-partial to a concurrent reader.
**Fix:** Write to `cache_file.with_suffix(".json.tmp")` then `os.replace(...)`, and accept last-writer-wins for the entry merge.

### IN-06: `_probe_dimension` indexes `response.data[0]` unguarded and a missing API key surfaces as a generic SDK error

**File:** `src/sif/embedding/embedder.py:384-387,308`
**Issue:** An endpoint returning an empty `data` list raises `IndexError` instead of a diagnosable error; and when `api_key` is None with no `OPENAI_API_KEY`, the `OpenAI(...)` constructor raises an SDK message that never mentions `SIF_API_KEY` — the setting a SIF user would actually set. Fix: check `if not response.data: raise RuntimeError(...)` naming the model, and catch the constructor error to hint `SIF_API_KEY`/`OPENAI_API_KEY`.

### IN-07: `__builtins__["__import__"]` relies on implementation-defined behavior

**File:** `tests/unit/embedding/test_openai_embedder.py:160-165`
**Issue:** In imported modules `__builtins__` is a dict on CPython but this is a CPython implementation detail (it is the module itself in `__main__` and on other implementations). Works today; fragile pattern to copy.
**Fix:** Use `patch("builtins.__import__", ...)` as the accompanying `with` block already does — the `original_import = __builtins__["__import__"]` lookup can be `import builtins; original_import = builtins.__import__`.

---

_Reviewed: 2026-09-03T04:02:30Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
