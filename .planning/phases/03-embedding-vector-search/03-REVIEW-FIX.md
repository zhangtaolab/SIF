---
phase: 03-embedding-vector-search
fixed_at: 2026-09-04T00:00:00Z
review_path: .planning/phases/03-embedding-vector-search/03-REVIEW.md
iteration: 1
findings_in_scope: 14
fixed: 14
skipped: 7
status: all_fixed
---

# Phase 03: Code Review Fix Report

**Fixed at:** 2026-09-04
**Source review:** `.planning/phases/03-embedding-vector-search/03-REVIEW.md`
**Iteration:** 1
**Fix scope:** critical_warning (3 Critical + 11 Warning in scope; 7 Info out of scope)

**Summary:**
- Findings in scope: 14 (CR-01..CR-03, WR-01..WR-11)
- Fixed: 14
- Skipped: 7 (all Info severity, out of scope per fix_scope)

All 14 in-scope findings were fixed, each as an atomic commit on `main`
(landed via a temporary worktree branch `gsd-reviewfix/03-19150`, fast-forwarded
to `main` at `072ca7f`). Every fix adds or updates regression tests where the
review requested them.

**Verification:** full quality suite run per fix and once more after landing,
from the main checkout at `072ca7f`: `ruff check src tests` (clean),
`ruff format --check src tests` (clean, 124 files), `pytest` (544 passed,
11 skipped, 2 pre-existing ResourceWarnings in
`tests/unit/search/test_bm25.py::TestBM25ContextAttachment`, untouched by this
work). Fixes were developed and verified inside the isolated worktree
(`PYTHONPATH=<worktree>/src` over the editable install) and the final gate run
was repeated in the main checkout after the fast-forward, so the numbers above
are reproducible from the tree a reader sees. Note: `mypy src/sif` still aborts
on a site-packages file (`mcp/client/sse.py`) both before and after this work —
a pre-existing follow-imports configuration issue, not part of the required
quality suite (see CR-03 notes).

## Fixed Issues

### CR-01: Embedding cache not segmented by model

**Files modified:** `src/sif/embedding/manager.py`, `src/sif/embedding/cache.py`, `tests/unit/embedding/test_manager.py`
**Commit:** `3ce5b20`
**Applied fix:** `EmbeddingManager.embed()` now keys cache reads/writes with a
model id (`"{model_type}:{model_name}"`, plus `@{api_base}` when set) instead of
the shared `"default"` bucket. Adapted beyond the suggestion: the review's
suggested caller-only fix was insufficient — `EmbeddingCache`'s table had
`PRIMARY KEY (content_hash)` alone, so one model's row *replaced* another's for
the same text (verified by the new regression test failing before the schema
change). The table now uses `PRIMARY KEY (content_hash, model_id)` and legacy
single-key tables are detected and rebuilt on open (cache entries simply
re-embed). Regression test embeds the same text under two models sharing one
cache and asserts the second misses, plus a same-model cache-hit assertion.

### CR-02: BM25 FTS5 query built from raw user input crashes on common queries

**Files modified:** `src/sif/search/bm25.py`, `tests/unit/search/test_bm25.py`
**Commit:** `f29d8e8`
**Applied fix:** Added `_sanitize_term()` — FTS5 metacharacters (`" * ( ) : ^`)
are replaced with spaces (preserving token boundaries, e.g. `foo:bar` becomes
phrase `foo bar` which still matches) and the remainder is wrapped in double
quotes with a trailing `*`. Deviations from the suggested snippet, verified
empirically against a real `tokenize='porter'` FTS5 table: (1) quote-wrapped
phrases with `*` *outside* the closing quote are valid phrase-prefix queries on
SQLite 3.51, so prefix matching is kept rather than dropped; (2) the suggested
`return "*"` for no usable terms is itself a crasher (`MATCH '*'` ->
`OperationalError: unknown special query`), so empty/sanitized-away queries now
return `'""'` (empty phrase, matches nothing, no crash). Tests execute built
queries for every crashing input from the review against a real FTS5 table and
assert `e-mail`/`c++`/`don't` still find their documents. The optional
CLI-boundary `OperationalError` catch was not added — sanitization removes the
crash class at the source.

### CR-03: Declared Python 3.9 support broken at import time

**Files modified:** `pyproject.toml`, `CLAUDE.md`, `README.md`, `docs/installation.md`, `docs/development.md`, plus 13 source/test files for mechanical lint conformance
**Commit:** `bc441d0`
**Applied fix:** Took the recommended honest-bump path:
`requires-python = ">=3.10"`, dropped the 3.9 classifier, set
`[tool.ruff] target-version = "py310"`, `[tool.black] target-version` without
py39, `[tool.mypy] python_version = "3.10"`, and updated every doc that
advertised 3.9 (CLAUDE.md overview + style section, README badge, installation
and development guides; `docs/installation.md`'s "SQLite 3.9.0+" is a SQLite
version, left alone). The ruff target bump activates py310-only rules, so the
required mechanical fixes were applied across the codebase: UP045
(`Optional[X]` -> `X | None`, matching CLAUDE.md's stated style), UP035
(`typing.Callable` -> `collections.abc`), and B905 (`zip(strict=True)` — at the
chunks/embeddings join points this additionally enforces the 1:1 contract WR-03
is about). Note: `mypy src/sif` still aborts, but on a site-packages file
(`mcp/client/sse.py` pattern matching) — the same abort-class the review
documented under the old 3.9 config; a separate pre-existing config issue.

### WR-01: `EmbeddingConfig.api_key` leaks in repr()

**Files modified:** `src/sif/models/embedding.py`, `tests/unit/embedding/test_manager.py`
**Commit:** `3649412`
**Applied fix:** `api_key: str | None = Field(None, exclude=True, repr=False)`,
closing the repr leak (pydantic v2 `exclude` never affected `repr()`). Added a
regression test asserting the key is absent from both `repr()` and
`model_dump()`.

### WR-02: `Settings.model_dump()` includes `api_key`

**Files modified:** `src/sif/config/settings.py`, `tests/unit/config/test_settings.py`
**Commit:** `c9cdc88`
**Applied fix:** Added `exclude=True` to `Settings.api_key` (alongside the
existing `repr=False`) and a regression test asserting both `repr()` and
`model_dump()` are clean. No call site dumps settings today.

### WR-03: `EmbeddingManager.embed()` silently drops unfilled slots

**Files modified:** `src/sif/embedding/manager.py`, `tests/unit/embedding/test_manager.py`
**Commit:** `f6d5642`
**Applied fix:** After `embed_batch`, a length mismatch raises `RuntimeError`
("Embedding model returned N embeddings for M inputs") instead of silently
truncating via `zip()`; the response construction fails if any slot is unfilled
rather than filtering. `embed()` was split into `_lookup_cached` /
`_compute_embeddings` helpers to stay under the mccabe-10 limit (no rule
suppression). Regression test covers the short backend response.

### WR-04: `OpenAIEmbedder.embed_batch` assumes `response.data` ordering

**Files modified:** `src/sif/embedding/embedder.py`, `tests/unit/embedding/test_openai_embedder.py`, `tests/unit/embedding/test_factory.py`, `tests/unit/cli/test_index.py`
**Commit:** `87a58e3`
**Applied fix:** Each slice's response is sorted by `item.index` and validated
to be exactly `0..n-1`, else `RuntimeError("...misindexed...")`; the ragged
length check is kept first so its clearer error is preserved. Test fakes in all
three files now populate `index` like the real SDK (the old fakes baked in the
in-order assumption). New tests: reversed-order response is normalized to
correct text->vector mapping; misindexed `[0, 0, 1]` raises.

### WR-05: Dimension cache keyed by model name only

**Files modified:** `src/sif/embedding/embedder.py`, `tests/unit/embedding/test_openai_embedder.py`
**Commit:** `9c21f0d`
**Applied fix:** Cache key is now `"{api_base or 'default'}::{model_name}"`
(taking the review's first suggested option). Docstrings updated. Existing
cache tests updated to the new key (the expiry test now writes the correct key
so it tests TTL, not a key miss), and a new test proves two endpoints serving
the same model name probe independently and coexist in the cache file.

### WR-06: `batch_size` never reaches `OpenAIEmbedder`

**Files modified:** `src/sif/embedding/factory.py`, `src/sif/embedding/manager.py`, `tests/unit/embedding/test_factory.py`, `tests/unit/embedding/test_manager.py`
**Commit:** `3cbf190`
**Applied fix:** `EmbeddingManager.load_model()` passes
`batch_size=self._config.batch_size` to the factory, and
`_create_openai_model` forwards `batch_size=kwargs.get("batch_size", 64)` to
`OpenAIEmbedder`. Tests cover factory forwarding and the manager plumbing.
(`max_tokens` remains unplumbed per the review's note that this is acceptable
for the API's own limits.)

### WR-07: MCP `SearchBackend` drops `api_key`/`api_base`

**Files modified:** `src/sif/mcp/backend.py`, `tests/unit/mcp/test_backend.py`
**Commit:** `cce4d60`
**Applied fix:** Mirrored `EmbeddingManager.from_settings`' kwargs:
`api_key`, `api_base`, `embedding_dim`, and `cache_dir` (only when
`cache_embeddings`) are now forwarded to `factory.create_model`, so
`SIF_MODEL_TYPE=openai` works via MCP instead of silently losing vector search.
Did not reuse `EmbeddingManager` itself — its `embed()` returns an
`EmbeddingResponse`, incompatible with the `Embedder` protocol
`SearchPipeline` expects. New test asserts the factory receives all four
kwargs.

### WR-08: `embed_cmd` load-error handlers unreachable; failures exit 0

**Files modified:** `src/sif/cli/commands/index.py`, `tests/unit/cli/test_index.py`
**Commit:** `b6eea30`
**Applied fix:** `manager.load_model()` is called inside the first try block so
backend-missing/dimension-mismatch errors reach the dedicated handlers (now
`click.ClickException`, per the project's CLI error convention, instead of
print-and-return-exit-0), and per-collection embedding failures are tracked and
convert to a non-zero exit with a summary `ClickException` after the loop. New
tests cover both the per-collection failure path (exit != 0, message shown) and
the backend-load-failure path.

### WR-09: `test_from_settings_passes_api_key_and_api_base` writes a real cache DB to home

**Files modified:** `tests/unit/embedding/test_manager.py`
**Commit:** `87cdfc7`
**Applied fix:** `cache_embeddings=False` added to the `Settings(...)`
construction plus `monkeypatch.delenv("SIF_CACHE_EMBEDDINGS", raising=False)`
for belt-and-braces, matching the sibling tests.

### WR-10: SearchPipeline expansion silently drops an expander's first variant

**Files modified:** `src/sif/search/hybrid.py`, `tests/unit/search/test_hybrid.py`
**Commit:** `5b99454`
**Applied fix:** The expansion loop iterates *all* returned variants and skips
any equal (case-insensitively) to the parsed original, instead of slicing
`expanded[1:]` under the unguaranteed echo assumption. Existing echo-based
tests still pass; a new test with a non-echoing expander (`["variant1",
"variant2"]`) asserts all three searches run.

### WR-11: Settings default test not hermetic against env/.env

**Files modified:** `tests/unit/config/test_settings.py`
**Commit:** `072ca7f`
**Applied fix:** `test_default_model_type_is_modelscope` now takes
`monkeypatch`, clears `SIF_MODEL_TYPE`, and constructs `Settings(_env_file=None)`
— hermetic against both a developer's exported variables and a `.env` file.

## Skipped Issues

### IN-01: Legacy duplicate embedding abstraction exported from package root

**File:** `src/sif/embedding/model.py`, `src/sif/embedding/__init__.py`
**Reason:** info severity, out of scope
**Original issue:** `EmbeddingModel` ABC + `EmbeddingModelFactory` Protocol remain and are re-exported; consolidation trap.

### IN-02: `create_embedder()` free function is dead code

**File:** `src/sif/embedding/embedder.py:470-491`
**Reason:** info severity, out of scope
**Original issue:** No callers; diverges from `EmbeddingModelFactory` (no openai branch).

### IN-03: `EmbeddingManager.embed(normalize=...)` parameter ignored

**File:** `src/sif/embedding/manager.py`
**Reason:** info severity, out of scope
**Original issue:** `normalize` accepted but never forwarded; callers cannot get unnormalized vectors.

### IN-04: `ModelScopeEmbedder` selects model dir via unsorted `glob("*")[0]`

**File:** `src/sif/embedding/embedder.py:204-210`
**Reason:** info severity, out of scope
**Original issue:** Filesystem-dependent directory choice can pick a `.temp` dir instead of the model.

### IN-05: `_write_dim_cache` non-atomic, unlocked read-modify-write

**File:** `src/sif/embedding/embedder.py:362-382`
**Reason:** info severity, out of scope
**Original issue:** Concurrent processes can lose entries; mid-write crash truncates the file (self-healing).

### IN-06: `_probe_dimension` indexes `response.data[0]` unguarded; missing key error lacks SIF hint

**File:** `src/sif/embedding/embedder.py:384-387,308`
**Reason:** info severity, out of scope
**Original issue:** Empty `data` -> IndexError; missing api_key error never mentions `SIF_API_KEY`.

### IN-07: `__builtins__["__import__"]` relies on CPython implementation detail

**File:** `tests/unit/embedding/test_openai_embedder.py:160-165`
**Reason:** info severity, out of scope
**Original issue:** Works today on CPython; fragile pattern.

---

**Human verification notes:** all fixed findings are behavior/logic changes;
each ships with an automated regression test (see per-finding notes), and the
full suite (544 passed) gates the branch. CR-02's FTS5 sanitization was
validated empirically against a real `tokenize='porter'` FTS5 table on SQLite
3.51 (phrase-prefix `"term"*` form confirmed valid); if the project ever
targets a SQLite older than FTS5 phrase-prefix support, revisit the trailing
`*`. CR-03's `zip(strict=True)` additions now make length mismatches raise at
join points — intentional, and aligned with WR-03's fail-fast contract.

_Fixed: 2026-09-04_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
