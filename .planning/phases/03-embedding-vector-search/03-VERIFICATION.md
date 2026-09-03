---
phase: 03-embedding-vector-search
verified: 2026-09-03T04:13:30Z
status: human_needed
score: 11/12 must-haves verified
behavior_unverified: 1
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 6/7
  gaps_closed:
    - "User can configure the OpenAI-compatible API embedding backend via Settings and CLI (SC1 / VEC-01)"
  gaps_remaining: []
  regressions: []
behavior_unverified_items:
  - truth: "An interrupted or parallel ModelScope download resumes from the local snapshot
      cache instead of restarting or corrupting it (VEC-04 edge probe, backstop-tagged in
      03-07-PLAN must_haves)"
    test: "Interrupt a ModelScope model download mid-transfer (or run two concurrently),
      then re-run the download"
    expected: "Download resumes from the local snapshot cache without restarting from zero
      or corrupting the snapshot; the model then loads and embeds"
    why_human: "Backstop-tagged truth — the guarantee rests with modelscope
      snapshot_download's caching/resume semantics and is not unit-verifiable offline;
      presence+wiring never qualifies. No test in the suite exercises it."
coincidental_reliance_items:
  - truth: "Document indexing benefits from batch embedding insertion for better performance (SC3 / VEC-03)"
    reason: undeclared-precondition
    harden: >-
      Carried forward unchanged from the initial verification: VectorSearcher.add_embeddings_batch
      advertises `chunk_id: str | None` but the installed sqlite-vec rejects NULL for the TEXT
      metadata column ("Expected text for TEXT metadata column chunk_id, received NULL").
      It works only because embed_cmd always passes chunk.id. Either declare the non-None
      precondition (type + docstring + guard) or serialize None to a sentinel before executemany.
human_verification:
  - test: "Live OpenAI-compatible endpoint check: set SIF_MODEL_TYPE=openai,
      SIF_API_BASE=https://<compatible-endpoint>/v1, SIF_API_KEY=<key>, and
      SIF_MODEL_NAME=<the endpoint's model id> (not the shared local-model default),
      then run `sif vsearch <query>` against an indexed collection"
    expected: "Embeddings are produced by the remote endpoint (real SDK transport), vector
      search returns semantic results; first run probes and caches the dimension,
      second run reads openai_dim_cache.json without re-probing"
    why_human: "Requires a live API key and remote service; all 22 automated tests mock the
      openai module. 03-07 coverage item D6 and 03-VALIDATION.md both classify this as
      manual-only."
  - test: "Live ModelScope model download: set SIF_MODEL_TYPE=modelscope and run
      `sif embed <file>` with network access"
    expected: "Model downloads from modelscope.cn via snapshot_download and produces
      embeddings usable by vector search"
    why_human: "Real network download of a large model; unit tests mock snapshot_download.
      03-VALIDATION.md manual-only table."
  - test: "ModelScope interrupted/parallel download resume (see behavior_unverified_items)"
    expected: "Resume from local snapshot cache; no restart-from-zero, no corruption"
    why_human: "Backstop-tagged; not unit-verifiable offline"
  - test: "Prohibition review (unverified-prohibition — human review recommended):
      confirm document/chunk text never leaves the device unless model_type=openai is
      explicitly configured"
    expected: "Local backends (sentence_transformers, gguf, modelscope) keep all user
      content on-device; their only network traffic is model-file download"
    why_human: "Judgment-tier prohibition; verifier's LLM-judge verdict is PASS by code
      inspection (OpenAIEmbedder is the only class holding a remote client and is
      constructed only on ModelType.OPENAI dispatch; ST/GGUF/ModelScope embed via local
      inference — modelscope downloads model files then SentenceTransformer.encode locally),
      but this is non-authoritative"
  - test: "Prohibition review (unverified-prohibition — human review recommended):
      confirm no silent fallback to a different embedding backend when the configured
      backend fails to load"
    expected: "Failure surfaces as an explicit user-facing error (e.g. ClickException
      'Failed to load embedding model: ...'), never a silent switch to another backend"
    why_human: "Judgment-tier prohibition; verifier's LLM-judge verdict is PASS (factory
      dispatch raises rather than substituting; EmbeddingManager has no fallback logic;
      vsearch wraps load failure in ClickException at search.py:293-296), but this is
      non-authoritative"
---

# Phase 03: Embedding & Vector Search Verification Report

**Phase Goal:** Users can perform semantic vector search with configurable embedding backends.
**Verified:** 2026-09-03T04:13:30Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (plan 03-07)

**Verification basis:** the CURRENT codebase. Re-verification mode: full 3-level verification
on the single previous gap (OpenAI backend / SC1 / VEC-01 + both missing Wave-0 test files);
quick regression on the six previously-verified truths. Full suite independently re-run:
**528 passed, 11 skipped, 0 failed** (`python -m pytest -x -q`, 11.19s).

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can configure different embedding backends (sentence-transformers, llama-cpp-python, OpenAI-compatible API) via Settings and CLI (SC1 / VEC-01) — **the previous gap** | ✓ VERIFIED | **Gap closed.** `OpenAIEmbedder(Embedder)` exists (embedder.py:267-422, 156 substantive lines); `_create_openai_model` constructs it from api_key/api_base/embedding_dim/cache_dir kwargs (factory.py:70-82) — the `NotImplementedError` stub is gone. Behavioral: direct execution of the exact previously-failing path — `Settings(model_type='openai', api_key, api_base)` → `EmbeddingManager.from_settings` → `load_model` → **OpenAIEmbedder loaded**, `embed()` returned 2 embeddings dim 3, client constructed with `{'api_key': 'sk-test', 'base_url': 'https://api.example.com/v1'}`, 2 recorded `embeddings.create` calls (probe + batch) — SPOT-CHECK PASS. `--model-type openai` is a CLI Choice on vsearch (search.py:247), query (search.py:391), embed (index.py:181); Settings validator accepts `openai` (settings.py:156). Named tests pass: end-to-end settings→embeddings, env-var dispatch, advertised-backends invariant, CLI `--model-type openai` reaches endpoint via real manager. Live-endpoint transport remains a human item (below). |
| 2 | Vector search uses `sqlite-vec` and refuses brute-force Python fallback (SC2 / VEC-02) | ✓ VERIFIED | Regression: `test_init_raises_when_vec_unavailable` PASSED. vector.py untouched by 03-07; no Python cosine fallback in the vector search path (re-confirmed previous finding). |
| 3 | Document indexing benefits from batch embedding insertion for better performance (SC3 / VEC-03) | ✓ VERIFIED | Regression: `test_add_embeddings_batch_executes_many` PASSED. executemany batch insert wired in embed_cmd; vector.py/index.py untouched by 03-07. Advisory coincidental-reliance (NULL chunk_id) carried forward. |
| 4 | User can download embedding models from ModelScope as an alternative to HuggingFace (SC4 / VEC-04) | ✓ VERIFIED | Regression: 6 ModelScope embedder tests PASSED (incl. `test_create_modelscope`); download.py/factory modelscope branch untouched by 03-07; `snapshot_download` is the real SDK. Live network download = human item; resume semantics = behavior-unverified item (backstop). |
| 5 | Settings accepts model_type, api_base, api_key with validation and env override (plans 03-01/03-05) | ✓ VERIFIED | Regression: `test_model_type_env_var_override` and `test_from_settings_passes_api_key_and_api_base` PASSED. Fields + validators present (settings.py:61-80, 151-168). |
| 6 | SchemaManager creates dimension-aware vec0 table and fails fast on dimension mismatch (plan 03-03) | ✓ VERIFIED | Regression: direct execution with sqlite-vec loaded — FLOAT[384] then re-init at 768 raised `RuntimeError("Embedding dimension mismatch: database has FLOAT[384], but settings require FLOAT[768]...")`. (pytest class env-skips because its fixture loads vec differently than production — pre-existing, unchanged.) |
| 7 | vsearch/query/embed commands use EmbeddingManager with --model-type; embedder reaches hybrid pipeline (plan 03-06) | ✓ VERIFIED | Regression: `test_embed_cmd_respects_model_type_override` PASSED; CLI wiring re-confirmed in source (search.py:282-296, index.py:208-212). |
| 8 | First openai load resolves dimension from the API, caches to openai_dim_cache.json (7-day TTL, keyed by model); subsequent loads hit cache and do not re-probe (03-07 / D-05) | ✓ VERIFIED | Behavioral tests PASSED: probe-once-then-cache-hit, cache file schema, TTL expiry re-probe, per-model keys, corrupt-cache-as-miss, no-cache-dir probes. Implementation verified in source (embedder.py:322-387). |
| 9 | Caller-supplied embedding_dim disagreeing with API-detected dimension fails fast at load, naming both values + SIF_EMBEDDING_DIM (03-07) | ✓ VERIFIED | `test_dimension_mismatch_fails_fast` PASSED; error text at embedder.py:311-317 names model, both dims, and the setting. |
| 10 | Absent openai package → ImportError after logger.error naming `pip install sif[openai]`; extra declared in pyproject (03-07) | ✓ VERIFIED | `test_import_error_logs_install_hint` PASSED (embedder.py:297-303); `openai = ["openai>=2.0.0"]` extra present and included in `all` (pyproject.toml:56-57, 64). |
| 11 | openai backend is parallel/interruption-safe: independent instances, no shared mutable state, no partial embeddings persisted on mid-batch failure (03-07) | ✓ VERIFIED | `test_embed_batch_no_partial_result_on_midbatch_failure` PASSED (ragged response raises before results are produced, so callers never write partial vectors); `embed_batch` validates response length per slice before extending (embedder.py:399-408). Instance-state-only construction (all mutable state is per-instance; class attrs are constants). |
| 12 | Interrupted/parallel ModelScope download resumes from local snapshot cache without corruption (03-07 backstop truth, VEC-04 edge) | ⚠ PRESENT_BEHAVIOR_UNVERIFIED | Backstop-tagged (`verification: backstop`): abstain per policy — no wired test exercises snapshot_download resume semantics, no direct observation available offline. Routed to human verification. |

**Score:** 11/12 truths verified (1 present, behavior-unverified — backstop abstention)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/sif/embedding/embedder.py` | OpenAIEmbedder(Embedder) with embed/embed_batch/dimension | ✓ VERIFIED | Lines 267-422; substantive (lazy SDK import + install hint, single client, batch slicing, ragged guard, L2 normalization, dimension probe/cache/TTL). |
| `src/sif/embedding/factory.py` | `_create_openai_model` constructs OpenAIEmbedder, no raise | ✓ VERIFIED | factory.py:70-82; openai branch wired; honest `-> Embedder` / `**kwargs: Any` signatures across all six methods; ModelType from `sif.models.embedding`. |
| `tests/unit/embedding/test_factory.py` | Wave-0 artifact previously missing | ✓ VERIFIED | 190 lines, 7 tests (dispatch matrix incl. captured client kwargs, env-var path, advertised-backend invariant). All pass. |
| `tests/unit/embedding/test_openai_embedder.py` | Wave-0 artifact previously missing | ✓ VERIFIED | 363 lines, 15 tests (end-to-end, batching, ragged guard, ImportError hint, normalization, no-partial-persistence, 8 dimension-cache tests). All pass. |
| `pyproject.toml` | openai optional extra, also in `all` | ✓ VERIFIED | `openai>=2.0.0` in both extras (lines 56-57, 64). |
| Regression artifacts (settings.py, schema.py, database.py, vector.py, indexer.py, manager.py, cli tests) | Untouched by gap closure, still wired | ✓ VERIFIED | 03-07 modified only embedder.py, factory.py, pyproject.toml + 3 test files (git: 789da35…445ecca). All regression tests pass. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| Settings.model_type=openai (incl. SIF_MODEL_TYPE env) | EmbeddingManager.from_settings → factory kwargs (api_key, api_base, embedding_dim, cache_dir) | `load_model` (manager.py:81-92) | ✓ WIRED | **Previously NOT_WIRED — now fixed.** Behavioral: client ctor captured `{'api_key': ..., 'base_url': ...}`; `test_env_var_model_type_openai_dispatches` passed. |
| `_create_openai_model` | OpenAIEmbedder → `OpenAI(api_key=..., base_url=...).embeddings.create` | factory.py:70-82, embedder.py:297-308 | ✓ WIRED | Direct execution + ctor-kwargs capture. |
| API-detected dimension | OpenAIEmbedder.dimension → EmbeddingResponse.dimensions, fail-fast vs settings.embedding_dim | `_resolve_dimension` + RuntimeError (embedder.py:310-318) | ✓ WIRED | `test_dimension_mismatch_fails_fast`, `test_manager_path_probe_matches_settings_dim` passed. |
| Regression links (embed_cmd→add_embeddings_batch; vsearch→manager.embed_single; Database.init_schema→SchemaManager(embedding_dim)) | unchanged | — | ✓ WIRED | All previously verified; regression tests pass; code untouched. |
| Settings → factory via **MCP** backend | `mcp/backend.py:48-52` `create_model(model_type, model_path, model_name)` | missing api_key/api_base/cache_dir kwargs | ⚠️ NOT WIRED (out of goal scope) | See Warnings — WR-07. SC1/VEC-01 text says "via Settings and CLI"; the Settings/CLI path is fully wired. MCP is Phase 9 territory. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| Manager (openai) | `embeddings` | `OpenAIEmbedder.embed_batch` → endpoint response (mocked in tests) | Yes — response data flows to EmbeddingResponse and onward to VectorSearcher | ✓ FLOWING |
| Factory (openai branch) | api_key/api_base kwargs | Settings → EmbeddingConfig → factory → OpenAI ctor | Yes — captured in ctor kwargs (previously DISCONNECTED) | ✓ FLOWING |
| Dimension cache | openai_dim_cache.json entries | probe response length, per model, TTL'd | Yes — read/write observed in tests | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| **Previously-failing check:** SIF_MODEL_TYPE=openai loads real OpenAIEmbedder through full dispatch path (endpoint mocked) | direct python: Settings→from_settings→load_model→embed | OpenAIEmbedder loaded; 2 embeddings dim 3; ctor kwargs `{api_key, base_url}`; 2 create calls | ✓ PASS (was ✗ FAIL) |
| End-to-end settings→embeddings (mocked endpoint) | pytest `test_settings_to_embeddings_end_to_end` | passed | ✓ PASS |
| SIF_MODEL_TYPE env → openai dispatch | pytest `test_env_var_model_type_openai_dispatches` | passed | ✓ PASS |
| CLI `--model-type openai` reaches endpoint via real manager | pytest `test_embed_cmd_openai_model_type_reaches_endpoint` | passed | ✓ PASS |
| Advertised-backend construct invariant (ST/gguf/openai/modelscope) | pytest `test_advertised_backends_construct_invariant` | passed | ✓ PASS |
| Dimension cache: probe-once/TTL/per-model/corrupt | pytest -k (5 cache tests) | passed | ✓ PASS |
| Mismatch fail-fast, ragged guard, ImportError hint, no-partial-persistence | pytest -k (4 behavior tests) | passed | ✓ PASS |
| Full suite | `python -m pytest -x -q` | **528 passed, 11 skipped, 0 failed** | ✓ PASS |
| SC2 fail-fast without vec | pytest `test_init_raises_when_vec_unavailable` | passed | ✓ PASS |
| SC3 batch insert | pytest `test_add_embeddings_batch_executes_many` | passed | ✓ PASS |
| SC4 ModelScope | pytest -k modelscope (6 tests) | passed | ✓ PASS |
| Schema dimension mismatch (direct, sqlite-vec loaded) | direct python | RuntimeError naming both dims | ✓ PASS |

### Probe Execution

Step 7c: SKIPPED — no probe scripts declared in PLAN/SUMMARY and no `scripts/*/tests/probe-*.sh` exist for this phase.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| VEC-01 | 03-01, 03-02, 03-05, 03-06, 03-07 | Configure backends (sentence-transformers / llama-cpp-python / OpenAI-compatible API) via Settings and CLI | ✓ SATISFIED | All three named backends load through the factory and are selectable via Settings validators, SIF_* env vars, and `--model-type` on vsearch/query/embed; behaviorally verified (mocked endpoint). Live endpoint = human item. REQUIREMENTS.md says Complete — consistent. |
| VEC-02 | 03-03, 03-04, 03-06 | Vector search via sqlite-vec / refuse brute-force on large indexes | ✓ SATISFIED | Fail-fast RuntimeError; vec0 MATCH queries only; no Python fallback. **REQUIREMENTS.md still says Pending — stale bookkeeping** (declared by legacy plans predating requirements-frontmatter citation; no executor ever marked it). Recommend updating the traceability table. |
| VEC-03 | 03-04, 03-05, 03-06 | Batch embedding insertion for indexing performance | ✓ SATISFIED | executemany batch insert wired in embed_cmd; tests pass. **REQUIREMENTS.md still Pending — stale bookkeeping.** |
| VEC-04 | 03-02 | ModelScope download as HuggingFace alternative | ✓ SATISFIED | Real snapshot_download wired through factory + pull; 6 tests pass. Live network download = human item. **REQUIREMENTS.md still Pending — stale bookkeeping.** |

**Orphaned requirements:** none — all four VEC IDs mapped to Phase 3 in REQUIREMENTS.md are claimed by plan frontmatters (mapping above). The status asymmetry (VEC-01 Complete, VEC-02/03/04 Pending) is a REQUIREMENTS.md traceability-table staleness issue, not an implementation gap: VEC-02/03/04 are declared by legacy plans 03-03…03-06 which predate requirements-frontmatter citation, so no executor marked them; the initial verification already assessed them satisfied and this re-verification confirms by regression.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/sif/embedding/manager.py` | 128, 143-144 | **CR-01 (from 03-REVIEW.md, re-confirmed in code):** `embed()` calls `self._cache.get(text)` / `set(text, emb)` while `EmbeddingCache.get/set` accept an unused `model_id="default"` param (cache.py:68, 97) — text-embedding cache is NOT segmented by backend/model | ⚠️ Warning | Pre-existing defect (manager.py untouched by 03-07) but materially aggravated by SC1's multi-backend configurability: with default `cache_embeddings=True`, switching backends re-serves previously-cached wrong-dimension vectors for already-seen chunk texts. Does not block configuration (SC1's truth) — all backends load and embed — but degrades backend-switching data quality until fixed. Fix is small (pass `model_id=self._config.model_name`, ideally including model_type). Recommend addressing before Phase 4/9 build on it. |
| `src/sif/mcp/backend.py` | 48-52 | **WR-07:** MCP `SearchBackend` factory call drops api_key/api_base/embedding_dim/cache_dir; wrapped in `except Exception: logger.warning(...)` | ⚠️ Warning | openai backend reachable via Settings/env/CLI but not via MCP settings passthrough. Outside SC1/VEC-01's literal "via Settings and CLI" scope; MCP ownership is Phase 9. Flag for Phase 9. |
| `src/sif/search/bm25.py` | 143-161 | CR-02: FTS5 MATCH built from raw user input; `e-mail`, `don't`, `c++` crash with sqlite3.OperationalError | ℹ️ Info (out of scope) | Pre-existing, phase-04 file, not a Phase 03 truth; surfaced by 03-REVIEW.md. |
| `pyproject.toml` | 11, 21-24 | CR-03: `requires-python >= 3.9` but modules use PEP 604 unions evaluated at import time | ℹ️ Info (out of scope) | Pre-existing packaging defect; not a Phase 03 SC; also blocks mypy in this env (deferred-items.md). |
| `src/sif/embedding/factory.py` | 90 | `raise NotImplementedError("HuggingFace models not yet implemented")` | ℹ️ Info | Pre-existing, intentionally retained per 03-07 plan; HuggingFace is not a VEC-01-named backend and is absent from CLI `--model-type` choices. Note the Settings validator still accepts `huggingface` (settings.py:156) — a Settings-accepted but unconstructible value; predates this phase, not advertised by CLI. |

Debt-marker gate: no TBD/FIXME/XXX in any phase-modified file; the only "not yet implemented" is the documented HuggingFace stub (referenced in 03-07-SUMMARY Known Stubs and pre-existing).

### Recorded Override Re-Surfaced (per STATE.md)

- **[2026-09-03, user-approved]** Phase 03 decision-coverage gate override: **D-06/D-07/D-08/D-10 accepted as covered-by-legacy** — implemented and behaviorally verified per the initial 03-VERIFICATION.md; legacy plans 03-01…03-06 predate D-ID citation and are read-only in gap-closure mode. No must-have override was needed this round (`overrides_applied: 0`); this decision-coverage acceptance is carried in STATE.md and re-surfaced here as instructed.

### Human Verification Required

1. **Live OpenAI-compatible endpoint** — SIF_MODEL_TYPE=openai + SIF_API_BASE/SIF_API_KEY/SIF_MODEL_NAME (endpoint's model id), `sif vsearch <query>`. Expected: remote embeddings, semantic results, dimension cached on first run. *(Requires live API key + remote service; all 22 automated tests mock the openai module.)*
2. **Live ModelScope download** — SIF_MODEL_TYPE=modelscope, `sif embed <file>` with network. Expected: model downloads from modelscope.cn and embeds. *(Large network download; unit tests mock snapshot_download.)*
3. **ModelScope download resume/interruption semantics** — the backstop-tagged truth #12; confirm interrupted/parallel downloads resume from the local snapshot cache without corruption.
4. **Prohibition review (egress)** — unverified-prohibition, human review recommended: no document/chunk text leaves the device unless model_type=openai is explicitly configured. Verifier's code-inspection verdict: PASS (non-authoritative).
5. **Prohibition review (fallback)** — unverified-prohibition, human review recommended: configured-backend load failure surfaces as an explicit error, never a silent backend switch. Verifier's code-inspection verdict: PASS (non-authoritative).

### Gaps Summary

**The single previous gap is closed.** The OpenAI-compatible API embedding backend named in SC1/VEC-01 now exists and works: OpenAIEmbedder is substantive and wired through the factory, api_key/api_base flow from Settings/env/CLI into the OpenAI client constructor, dimension auto-detection probes once and caches per model with a 7-day TTL and fail-fast mismatch, the `sif[openai]` extra is declared, and both previously-missing Wave-0 test files exist (22 tests, all passing). The exact spot-check that failed the initial verification now passes, and the full suite is green (528 passed, 11 skipped, 0 failed — independently re-run). No regressions in VEC-02/03/04 or the settings/schema/CLI truths (all regression tests pass; schema mismatch fail-fast re-confirmed by direct execution).

No truth FAILED; no artifact is MISSING or a stub; every key link is wired (the MCP call site remains unwired for api_key/api_base but is outside the goal's "via Settings and CLI" scope — flagged for Phase 9).

Status is **human_needed** rather than passed because five items inherently require a human: the two live-endpoint/network checks, the backstop-tagged ModelScope resume semantics (abstained per policy — no test exercises it), and the two judgment-tier prohibitions (LLM-judge PASS by code inspection, non-authoritative, flagged). One warning deserves early attention despite not blocking the goal: **CR-01, the un-segmented text-embedding cache**, which the newly-restored backend configurability makes materially worse for users who switch backends with caching enabled (default). Bookkeeping note: REQUIREMENTS.md still lists VEC-02/VEC-03/VEC-04 as Pending although implementation evidence satisfies them — recommend updating the traceability table (this verifier does not edit REQUIREMENTS.md).

---

_Verified: 2026-09-03T04:13:30Z_
_Verifier: Claude (gsd-verifier)_
