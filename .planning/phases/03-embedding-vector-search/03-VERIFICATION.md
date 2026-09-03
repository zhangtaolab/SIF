---
phase: 03-embedding-vector-search
verified: 2026-09-03T01:04:38Z
status: gaps_found
score: 6/7 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: none
gaps:
  - truth: "User can configure the OpenAI-compatible API embedding backend via Settings and CLI (SC1 / VEC-01)"
    status: failed
    reason: >-
      The openai backend cannot load. EmbeddingModelFactory._create_openai_model raises
      NotImplementedError("OpenAI models not yet implemented"); the OpenAIEmbedder class
      from plan 03-02 does not exist anywhere in the codebase or in any reachable git
      commit (pickaxe for "class OpenAIEmbedder" returns nothing). Settings and the CLI
      accept model_type=openai (validator, --model-type Choice, SIF_MODEL_TYPE env), and
      api_key/api_base flow from Settings through EmbeddingManager into factory kwargs,
      but they are dead ends: `sif vsearch --model-type openai` and SIF_MODEL_TYPE=openai
      always terminate in ClickException "Failed to load embedding model: OpenAI models
      not yet implemented". Two of the three named backends (sentence_transformers,
      gguf) are wired and functional. All three ML libraries (sentence-transformers
      5.4.1, llama-cpp-python, modelscope 1.36.0) are installed in this environment, so
      this is not an optional-dependency absence.
    artifacts:
      - path: src/sif/embedding/factory.py
        issue: "_create_openai_model (line 66-72) raises NotImplementedError; no OpenAIEmbedder import; api_key/api_base kwargs unused for the openai branch"
      - path: src/sif/embedding/embedder.py
        issue: "OpenAIEmbedder class absent — plan 03-02 Task 1 deliverable never landed in git history (commits f4185bd and ede0d6f claimed in 03-01/03-02 SUMMARYs are missing from the repo)"
      - path: tests/unit/embedding/test_factory.py
        issue: "Missing — declared as Wave 0 requirement in 03-VALIDATION.md; no factory test file exists in the current tree"
      - path: tests/unit/embedding/test_openai_embedder.py
        issue: "Missing — declared as Wave 0 requirement in 03-VALIDATION.md"
    missing:
      - "Implement OpenAIEmbedder(Embedder) in src/sif/embedding/embedder.py with embed/embed_batch/dimension, api_base support for OpenAI-compatible endpoints, and lazy `from openai import OpenAI` import"
      - "Wire _create_openai_model in src/sif/embedding/factory.py to construct OpenAIEmbedder(model_name, api_key=kwargs.get('api_key'), api_base=kwargs.get('api_base'), embedding_dim=kwargs.get('embedding_dim'), cache_dir=kwargs.get('cache_dir'))"
      - "Add unit tests (tests/unit/embedding/test_factory.py, test_openai_embedder.py) with a mocked OpenAI client covering factory dispatch, dimension detection/caching, embed, embed_batch, and ImportError messaging"
coincidental_reliance_items:
  - truth: "Document indexing benefits from batch embedding insertion for better performance (SC3 / VEC-03)"
    reason: undeclared-precondition
    harden: >-
      VectorSearcher.add_embeddings_batch advertises `chunk_id: str | None` in its
      signature, but the installed sqlite-vec rejects NULL for the TEXT metadata column
      ("Expected text for TEXT metadata column chunk_id, received NULL" — reproduced
      during verification). It works in production only because embed_cmd always passes
      chunk.id. Either declare the non-None precondition (type + docstring + guard) or
      serialize None to a sentinel before executemany.
---

# Phase 03: Embedding & Vector Search Verification Report

**Phase Goal:** Users can perform semantic vector search with configurable embedding backends.
**Verified:** 2026-09-03T01:04:38Z
**Status:** gaps_found
**Re-verification:** No — initial verification

**Verification basis:** the CURRENT codebase (`src/sif/` after the Phase 08 docsift→sif rename), per project context. Path references in the PLANs (`src/docsift/...`) map to `src/sif/...`.

## Goal Achievement

### Observable Truths

Merged from ROADMAP success criteria (contract) and PLAN frontmatter must-haves.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can configure different embedding backends (sentence-transformers, llama-cpp-python, OpenAI-compatible API) via Settings and CLI (SC1 / VEC-01) | ✗ FAILED | **OpenAI leg broken.** `EmbeddingModelFactory._create_openai_model` raises `NotImplementedError("OpenAI models not yet implemented")` (factory.py:72, verified by direct execution); `OpenAIEmbedder` class does not exist in src/ or tests/ and never existed in any reachable commit. CLI advertises `--model-type openai` on vsearch/query/embed but any use fails. ST + GGUF legs: WIRED and functional (SentenceTransformerEmbedder/LlamaCppEmbedder, `create_model` dispatch verified; ST backend constructed live during verification). |
| 2 | Vector search uses `sqlite-vec` and refuses brute-force Python fallback (SC2 / VEC-02) | ✓ VERIFIED | `VectorSearcher.__init__` raises RuntimeError when vec extension unavailable (behavioral test `test_init_raises_when_vec_unavailable` PASSED); search path uses only `embedding MATCH` vec0 queries (vector.py:61-75); no Python cosine fallback exists anywhere in src/sif/search (only rerank.py/expansion.py np.dot on small candidate pools — Phase 4 features, not the vector search path). |
| 3 | Document indexing benefits from batch embedding insertion for better performance (SC3 / VEC-03) | ✓ VERIFIED | `add_embeddings_batch` uses `executemany` + `json.dumps` (vector.py:160-178); wired in `embed_cmd` (index.py:260-274) which collects chunks cross-document and inserts in one batch. Behavioral: direct execution against real sqlite-vec inserted 3 rows in one call; `test_add_embeddings_batch_executes_many` PASSED. Advisory: see coincidental_reliance_items (NULL chunk_id). |
| 4 | User can download embedding models from ModelScope as an alternative to HuggingFace (SC4 / VEC-04) | ✓ VERIFIED | `ModelScopeEmbedder` → `ModelDownloader.download` → `modelscope.snapshot_download` (models/download.py:63, real SDK, installed v1.36.0); wired via `_create_modelscope_model` (factory.py:82-92); `model_type` defaults to `modelscope`; `sif pull` additionally implements HF-first/ModelScope-fallback (pull.py:54-81). `test_create_modelscope` PASSED. Live network download itself is a manual check (below). |
| 5 | Settings accepts model_type, api_base, api_key with validation and env override (plans 03-01/03-05) | ✓ VERIFIED | settings.py:61-80 fields + `validate_model_type`/`validate_api_base` validators (151-169); `SIF_MODEL_TYPE` env override behaviorally verified (`test_model_type_env_var_override` PASSED); api_key `repr=False` exclusion tested. Note: env prefix is `SIF_` (post-rename), default model_type changed `sentence_transformers`→`modelscope` in a later commit (82fa350) — mechanism intact. |
| 6 | SchemaManager creates dimension-aware vec0 table and fails fast on dimension mismatch (plan 03-03) | ✓ VERIFIED | schema.py:13-16 accepts `embedding_dim`; :252-271 introspects sqlite_master and raises `RuntimeError("Embedding dimension mismatch...")`; `Database.init_schema` passes `settings.embedding_dim` (database.py:51-57). Behavioral: direct execution with real sqlite-vec — FLOAT[384] table created, dim 768 re-init raised the mismatch RuntimeError. |
| 7 | vsearch/query/embed commands use EmbeddingManager with --model-type; embedder reaches hybrid pipeline (plan 03-06) | ✓ VERIFIED | search.py: `--model-type` Choice on vsearch (247) and query (391); both use `EmbeddingManager.from_settings` (290, 472) with `model_copy` override; query passes `embedder=manager._model` into SearchPipeline (528). index.py: embed_cmd `--model-type` (181), `EmbeddingManager.from_settings` (212), `manager.embed(chunk_texts)` (260), `add_embeddings_batch` (274). `test_embed_cmd_respects_model_type_override` PASSED. Indexer imports fixed (indexer.py:7-8, `start_pos` at :209). |

**Score:** 6/7 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact (current path) | Expected | Status | Details |
|--------------------------|----------|--------|---------|
| `src/sif/config/settings.py` | model_type/api_base/api_key fields + validators | ✓ VERIFIED | Present, substantive, wired into EmbeddingManager.from_settings and CLI overrides. |
| `src/sif/models/embedding.py` | ModelType enum with MODELSCOPE | ✓ VERIFIED | All 5 members present (models/embedding.py:8-15). Added post-phase in commit 82fa350 (Apr 20) — was absent at phase-completion commit c5563ae, but holds in current codebase. |
| `src/sif/embedding/embedder.py` | Embedder implementations incl. OpenAIEmbedder | ⚠️ PARTIAL | SentenceTransformerEmbedder, LlamaCppEmbedder, ModelScopeEmbedder, SimpleEmbedder present; **OpenAIEmbedder absent** (missing class, missing tests). |
| `src/sif/embedding/factory.py` | Factory wiring all backends | ⚠️ PARTIAL | ST/GGUF/ModelScope wired; `_create_openai_model` raises NotImplementedError; does not use Embedder protocol annotations (duck-typed — embedders subclass Embedder, so functionally equivalent). |
| `src/sif/embedding/manager.py` | EmbeddingManager aligned with Embedder protocol | ✓ VERIFIED | `self._model: Embedder \| None` (:42), from_settings propagates model_type/api_key/api_base (:54-66), embed() uses embed_batch (:139), no .load()/.loaded. |
| `src/sif/database/schema.py` | Dynamic-dimension vec0 table + mismatch fail-fast | ✓ VERIFIED | See truth 6. |
| `src/sif/database/database.py` | init_schema passes settings.embedding_dim | ✓ VERIFIED | :51-57. |
| `src/sif/search/vector.py` | Batch insert via sqlite-vec | ✓ VERIFIED | add_embeddings_batch + json.dumps + executemany; fail-fast init. |
| `src/sif/indexing/indexer.py` | Correct imports, start_pos/end_pos fields | ✓ VERIFIED | :7-8, :209. |
| `tests/unit/embedding/test_factory.py` | Factory unit tests | ✗ MISSING | Plan 03-02 / 03-VALIDATION Wave 0 artifact; never created or lost with the missing 03-02 commit. |
| `tests/unit/embedding/test_openai_embedder.py` | OpenAI embedder unit tests | ✗ MISSING | Same as above. |
| `tests/unit/config/test_settings.py` | Settings tests | ✓ VERIFIED | 8 tests; key ones PASSED during verification. |
| `tests/unit/database/test_schema.py` | Dimension/mismatch tests | ✓ VERIFIED (env-skipped) | Tests exist and are correct, but `TestSchemaManagerVectorTables` SKIPs in this environment — fixture loads vec via `load_extension("vec0")` while production uses `sqlite_vec.load()`. Behavior independently verified by direct execution. |
| `tests/unit/search/test_vector.py` | VectorSearcher batch tests | ✓ VERIFIED | 12 tests; batch test PASSED (mock-based). |
| `tests/unit/embedding/test_manager.py` | Manager tests | ✓ VERIFIED | 6 tests; from_settings api_key/api_base test PASSED. |
| `tests/unit/cli/test_index.py` | embed_cmd batch/model-type tests | ✓ VERIFIED | `test_embed_cmd_respects_model_type_override` PASSED. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| Settings.model_type | SIF_MODEL_TYPE env var | `env_prefix="SIF_"` | ✓ WIRED | Behavioral test passed. |
| EmbeddingManager.from_settings | EmbeddingModelFactory.create_model | model_type/api_key/api_base kwargs | ✓ WIRED | manager.py:81-92 (kwargs then dropped by the openai factory branch — see gap). |
| EmbeddingModelFactory.create_model | OpenAIEmbedder | `_create_openai_model` | ✗ NOT_WIRED | Raises NotImplementedError; target class does not exist. |
| EmbeddingModelFactory.create_model | ModelScopeEmbedder | `_create_modelscope_model` | ✓ WIRED | factory.py:82-92; test passed. |
| vsearch_cmd | EmbeddingManager.from_settings | manager.embed_single(query) | ✓ WIRED | search.py:282-291. |
| query_cmd | Hybrid pipeline with embedder | SearchPipeline(embedder=manager._model) | ✓ WIRED | search.py:462-528 (evolved from raw HybridSearcher to SearchPipeline in Phase 4 — intent preserved). |
| embed_cmd | VectorSearcher.add_embeddings_batch | executemany batch insert | ✓ WIRED | index.py:260-274; behavioral insert verified. |
| Database.init_schema | SchemaManager(embedding_dim=...) | settings.embedding_dim | ✓ WIRED | database.py:56. |
| SchemaManager._create_vector_tables | sqlite_master introspection | FLOAT[(\d+)] regex + RuntimeError | ✓ WIRED | Behavioral mismatch check passed. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| embed_cmd | `embedding_response.embeddings` | `manager.embed(chunk_texts)` → real Embedder.embed_batch | Yes | ✓ FLOWING |
| embed_cmd | `batch_items` | chunk_repo-created chunk ids + embeddings | Yes (persisted via executemany into document_embeddings) | ✓ FLOWING |
| vsearch_cmd | `query_embedding` | `manager.embed_single(query)` | Yes | ✓ FLOWING |
| Factory (openai branch) | api_key/api_base kwargs | Settings → EmbeddingConfig → factory | No — discarded; branch raises before use | ✗ DISCONNECTED |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Dimension mismatch fails fast | direct python: SchemaManager dim 384 then 768 on real sqlite-vec | RuntimeError "Embedding dimension mismatch: database has FLOAT[384], but settings require FLOAT[768]" | ✓ PASS |
| Batch insert into real sqlite-vec | direct python: add_embeddings_batch(3 items) | 3 rows in document_embeddings | ✓ PASS |
| Batch insert with NULL chunk_id | direct python: item with chunk_id=None | sqlite3.OperationalError "Expected text for TEXT metadata column chunk_id, received NULL" | ⚠ EDGE (see coincidental_reliance_items; production never passes None) |
| OpenAI backend creation | direct python: factory.create_model(ModelType.OPENAI, ...) | NotImplementedError "OpenAI models not yet implemented" | ✗ FAIL (the gap) |
| sentence_transformers backend creation | direct python: factory.create_model(ModelType.SENTENCE_TRANSFORMERS, ...) | Embedder created (library 5.4.1 installed) | ✓ PASS |
| Settings env override | pytest test_model_type_env_var_override | PASSED | ✓ PASS |
| Vector fail-fast without vec | pytest test_init_raises_when_vec_unavailable | PASSED | ✓ PASS |
| Manager api_key/api_base propagation | pytest test_from_settings_passes_api_key_and_api_base | PASSED | ✓ PASS |
| CLI --model-type override | pytest test_embed_cmd_respects_model_type_override | PASSED | ✓ PASS |
| ModelScope factory dispatch | pytest test_create_modelscope | PASSED | ✓ PASS |

### Probe Execution

Step 7c: SKIPPED — no probe scripts declared in PLAN/SUMMARY and no `scripts/*/tests/probe-*.sh` exist for this phase.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|---------------------|----------|
| VEC-01 | 03-01, 03-02, 03-05, 03-06 | Configure backends (sentence-transformers / llama-cpp-python / OpenAI-compatible API) via Settings and CLI | ✗ PARTIAL | Settings + CLI + validators + EmbeddingManager wiring complete; ST and GGUF functional; **OpenAI-compatible API backend not implemented** (factory NotImplementedError). |
| VEC-02 | 03-03, 03-04, 03-06 | Vector search uses sqlite-vec / refuses brute-force fallback | ✓ SATISFIED | Fail-fast RuntimeError; vec0 MATCH queries only; no Python fallback path. |
| VEC-03 | 03-04, 03-05, 03-06 | Batch embedding insertion for indexing performance | ✓ SATISFIED | add_embeddings_batch executemany; wired in embed_cmd cross-document batching. |
| VEC-04 | 03-02 | ModelScope download as HuggingFace alternative | ✓ SATISFIED | ModelDownloader → modelscope.snapshot_download; factory + pull command wired. (Landed via post-phase commit 82fa350 rather than plan 03-02's missing commit — outcome holds in current code.) |

**Orphaned requirements:** none — all four VEC IDs mapped to Phase 3 in REQUIREMENTS.md are claimed by plans. Note: REQUIREMENTS.md traceability table still lists VEC-01..04 as "Pending" — stale bookkeeping (info-level).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/sif/embedding/factory.py` | 72 | `raise NotImplementedError("OpenAI models not yet implemented")` — empty implementation | 🛑 Blocker | In-scope backend (SC1/VEC-01) non-functional; gap documented above. |
| `src/sif/embedding/factory.py` | 80 | `raise NotImplementedError("HuggingFace models not yet implemented")` | ℹ️ Info | Pre-existing; HuggingFace never in Phase 3 scope (ModelType.HUGGINGFACE predates phase; ModelScope is the delivered alternative per VEC-04). |
| `src/sif/embedding/embedder.py` | 264 | `SimpleEmbedder` hash-based fallback embedder | ℹ️ Info | Test-only; not reachable from any production path. |
| `tests/unit/database/test_schema.py` | 19-27 | vec fixture uses `load_extension("vec0")` instead of production `sqlite_vec.load()` | ⚠️ Warning | `TestSchemaManagerVectorTables` (5 tests) SKIP in this environment — part of the suite's 11 skips; weakens automated regression coverage of dimension mismatch. Behavior manually verified during this verification. |
| `src/sif/search/vector.py` | 160-178 | `add_embeddings_batch` accepts `chunk_id: str \| None` but sqlite-vec rejects NULL | ⚠️ Warning | Latent edge case; production callers always pass chunk.id (advisory coincidental-reliance item recorded). |

### Human Verification Required

Informational (overall status is gaps_found per the failed truth; these do not change status):

### 1. Live ModelScope model download and embed

**Test:** Run `sif embed --model-type modelscope` on a small collection with network access.
**Expected:** Model downloads from modelscope.cn via snapshot_download, embeddings are generated and vector search returns semantic results.
**Why human:** Real network download of a large model; unit tests mock snapshot_download.

### 2. Live OpenAI-compatible endpoint (after gap fix)

**Test:** Set `SIF_MODEL_TYPE=openai`, `SIF_API_BASE=https://<compatible-endpoint>/v1`, `SIF_API_KEY=...`, run `sif vsearch <query>`.
**Expected:** Embeddings produced from the remote endpoint; results returned. Currently impossible (NotImplementedError) — retest after gap closure.
**Why human:** Requires a live API key and remote service.

### Gaps Summary

One gap blocks full goal achievement: **the OpenAI-compatible API embedding backend named in Success Criterion 1 / VEC-01 was never implemented**. Plan 03-02 claimed OpenAIEmbedder + factory wiring, but its commits (`ede0d6f`, and 03-01's `f4185bd`) are missing from the repository — git evidence shows the factory at the phase-completion commit (c5563ae) already raised NotImplementedError for openai, and pickaxe search confirms `class OpenAIEmbedder` never existed in any reachable src/ commit. The current codebase accepts `openai` in Settings, env vars, and three CLI `--model-type` options, then fails at load time with "OpenAI models not yet implemented". The declared Wave 0 test artifacts (`tests/unit/embedding/test_factory.py`, `test_openai_embedder.py`) are also absent. Everything else the phase promised holds in the current codebase and was behaviorally verified: sqlite-vec-only vector search with fail-fast refusal, dimension-mismatch fail-fast schema, cross-document batch embedding insertion with executemany, ModelScope download wiring, and the EmbeddingManager/CLI integration. The gap is not addressed by any later phase (Phases 4-9 cover search pipeline, context, docs, skills, rename, MCP) and is therefore not deferred.

---

_Verified: 2026-09-03T01:04:38Z_
_Verifier: Claude (gsd-verifier)_
