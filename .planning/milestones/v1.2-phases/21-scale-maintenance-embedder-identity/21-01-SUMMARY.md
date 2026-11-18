---
phase: 21-scale-maintenance-embedder-identity
plan: 01
subsystem: embedding
tags: [embedder-identity, prompt-scheme, cache-bucketing, sqlite, pydantic-settings, sha256]

# Dependency graph
requires: []
provides:
  - "sif/embedding/identity.py - persisted deterministic embedder identity, field-wise comparison, schema FLOAT[n] read, legacy-assumed/certified sources, init/embed/search mode matrix"
  - "sif/embedding/prompts.py - PromptScheme + known-model prompt table (Harrier query prompt, Qwen3 unchanged)"
  - "sif/embedding/roles.py - type-aware embed_query/embed_queries/embed_documents dispatch"
  - "Settings.query_prompt_name / document_prompt_name and EmbeddingConfig mirrors"
  - "SentenceTransformerEmbedder/ModelScopeEmbedder role methods, pooling_mode, revision"
  - "EmbeddingManager.embed_query/embed_queries/embed_documents, get_identity, prompt/revision-aware _cache_bucket, cache vector validation"
affects: [21-02, 21-03, 21-05, 21-06, 22, 23, 24]

# Actuals (#2632) - pairs with the plan's `estimate` (74000 tokens, 3 tasks).
actuals:
  tokens: 24927
  tasks: 3
  commits: 3
plan_head_before: bc322ecece30e86e861de33896bdf1b4ee090f9b
plan_head_after: 64b96043fd3b6ecd2805a48ca027f78ca9eb2c40

tech-stack:
  added: []
  patterns:
    - "Field-wise identity comparison with unknown-tolerance, never fingerprint equality"
    - "Class-level role dispatch so MagicMock never takes a phantom role path"
    - "Cache bucket suffix discipline: |rev@<revision> then |q@<prompt>/|d@<prompt>"
    - "Defensive kv JSON parse: one warning, never raise, never block an embed"

key-files:
  created:
    - src/sif/embedding/identity.py
    - src/sif/embedding/prompts.py
    - src/sif/embedding/roles.py
    - tests/unit/embedding/test_identity.py
  modified:
    - src/sif/config/settings.py
    - src/sif/models/embedding.py
    - src/sif/embedding/embedder.py
    - src/sif/embedding/factory.py
    - src/sif/embedding/manager.py
    - tests/conftest.py
    - tests/unit/embedding/test_embedder_impl.py
    - tests/unit/embedding/test_manager.py
    - docs/configuration.md
    - scripts/generate_config_ref.py

key-decisions:
  - "Identity JSON keys follow the research payload (`schema`, `cache_model_id`, ...); `source` and `fingerprint` are written but excluded from the fingerprint, so assumed and verified records for the same model hash identically."
  - "Cache-read and cache-write dimension validation use the built identity's dimension (loaded model truth, falling back to config), not the raw settings `embedding_dim`; on the default ModelScope path they are equal, and injected/protocol-only doubles stay coherent."
  - "Prompt scheme is resolved once at EmbeddingManager construction (the EmbeddingConfig is immutable) and the effective names are passed to the factory at load; the manager never sets a model-wide default prompt."
  - "Module-level warn-once state lives in a mutable `_IdentityState` container instead of module globals (ruff PLW0603), reset by `reset_identity_state()` and an autouse conftest fixture."
  - "The config-doc generator's field list was extended with the two new Settings fields; generator-owned docs were regenerated, never hand-edited."

patterns-established:
  - "Identity records: canonical JSON + SHA-256 fingerprint; comparison tolerates one-sided unknown pooling/revision"
  - "Role dispatch: concrete methods on classes, class-level existence check, protocol doubles fall back to embed/embed_batch"
  - "Cache safety: validate count/finiteness/dimension before cache.set and on cache read; invalid entries become misses and are overwritten"

requirements-completed: [EMB-01, EMB-02]

coverage:
  - id: D1
    description: "Deterministic identity record round-trips through the real index_meta table; fingerprint stable across builds and a subprocess; corrupt JSON degrades to absent with one warning"
    requirement: EMB-01
    verification:
      - kind: unit
        ref: "tests/unit/embedding/test_identity.py#TestIdentityPersistence,TestFromJson"
        status: pass
    human_judgment: false
  - id: D2
    description: "Legacy DBs get source=legacy-assumed with one warning per process, certification rewrites source=verified, and the init/embed/search mode matrix (including the D-02 no-vectors branch) holds"
    requirement: EMB-01
    verification:
      - kind: unit
        ref: "tests/unit/embedding/test_identity.py#TestLegacyIdentity,TestCheckIdentity,TestSchemaEmbeddingDim"
        status: pass
    human_judgment: false
  - id: D3
    description: "Concrete ST/ModelScope backends accept per-role prompt names, validate them at construction, expose pooling/revision provenance, and keep the no-prompt encode kwargs byte-identical"
    requirement: EMB-02
    verification:
      - kind: unit
        ref: "tests/unit/embedding/test_embedder_impl.py#TestRoleAwareEmbedding,TestPoolingMode,TestGgufRevision"
        status: pass
    human_judgment: false
  - id: D4
    description: "Manager role methods dispatch correctly, prompt/revision bucketing keeps the default Qwen3 cache key unchanged, and non-finite/wrong-size vectors never reach or survive the cache"
    requirement: EMB-02
    verification:
      - kind: unit
        ref: "tests/unit/embedding/test_manager.py#TestCacheBuckets,TestRoleMethods,TestCacheSafety,TestRoleHelpers"
        status: pass
    human_judgment: false
  - id: D5
    description: "SIF_QUERY_PROMPT_NAME and SIF_DOCUMENT_PROMPT_NAME are documented through make docs-generate with no hand edits"
    requirement: EMB-02
    verification:
      - kind: other
        ref: "make docs-generate (idempotent) + tests/test_docs.py"
        status: pass
    human_judgment: false

duration: 13min
completed: 2026-11-16
status: complete
---

# Phase 21 Plan 01: Scale, Maintenance + Embedder Identity Summary

**Persisted embedder identity with field-wise comparison, a prompt-scheme resolver, role-explicit embed methods on both ST-backed backends, and prompt/revision-aware cache buckets that leave the default Qwen3 path byte-identical.**

## Performance

- **Duration:** 13 min
- **Started:** 2026-11-15T16:04:09Z
- **Completed:** 2026-11-15T16:17:21Z (2026-11-16 local)
- **Tasks:** 3
- **Files modified:** 14
- **Commits:** 3 task commits

## Accomplishments

- `src/sif/embedding/identity.py` is now the single owner of identity construction, persistence, fingerprinting, the `FLOAT[n]` schema read, and the mode-aware `check_identity` (init/embed/search), proven against a real on-disk index and real vec0 table.
- Legacy populated indexes are assumed once with `source="legacy-assumed"` and a one-per-process warning naming the `sif index embed --force` remedy; `certify_identity` rewrites `source="verified"`.
- `PromptScheme` resolution keeps Qwen3 prompt-free (no table entry) while giving Harrier `web_search_query`; Settings/EmbeddingConfig surface `SIF_QUERY_PROMPT_NAME`/`SIF_DOCUMENT_PROMPT_NAME`, documented through the generator.
- Both sentence-transformers backends expose `embed_query`/`embed_queries`/`embed_documents`, `pooling_mode`, and `revision` (GGUF file SHA-256), with prompt-name validation at construction.
- `EmbeddingManager` role methods, `get_identity`, and `_cache_bucket` add `|rev@`/`|q@`/`|d@` suffixes only when effective, so the default bucket string and encode kwargs are byte-identical to pre-phase behavior.
- Cache writes and reads validate count, finiteness, and dimension (T-21-01); invalid entries become misses and are overwritten, and bad model output raises naming the bucket and position.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end identity record — settings prompt fields, prompt resolver, identity build/persist/compare** — `c6083a4` (feat)
2. **Task 2: Prompt-aware embedder plumbing — prompt_name encode, pooling/revision provenance, factory dispatch** — `058f1f3` (feat)
3. **Task 3: Manager role methods, prompt/revision cache buckets, cache-poison guard, type-aware helpers** — `64b9604` (feat)

**Plan metadata:** docs commit at the end of the plan captures this SUMMARY plus STATE/ROADMAP updates.

## Files Created/Modified

- `src/sif/embedding/identity.py` (new) — `EmbedderIdentity`, `IDENTITY_KEY`, `IDENTITY_SCHEMA_VERSION`, `format_cache_model_id`, `build_identity`, `build_settings_identity`, `read_identity`, `write_identity`, `ensure_legacy_identity`, `certify_identity`, `identity_matches`, `IdentityCheck`, `check_identity`, `warn_identity_mismatch_once`, `reset_identity_state`, `schema_embedding_dim`.
- `src/sif/embedding/prompts.py` (new) — `PromptScheme`, `resolve_prompt_scheme`, known-model table.
- `src/sif/embedding/roles.py` (new) — class-level `embed_query`/`embed_queries`/`embed_documents` dispatch helpers.
- `src/sif/config/settings.py` — `query_prompt_name`, `document_prompt_name`.
- `src/sif/models/embedding.py` — `EmbeddingConfig` prompt-name mirrors.
- `src/sif/embedding/embedder.py` — prompt validation, role methods, `pooling_mode`/`revision` on ST and ModelScope; `LlamaCppEmbedder.revision`/`pooling_mode`; `OpenAIEmbedder.pooling_mode`.
- `src/sif/embedding/factory.py` — forwards prompt names to the two ST-backed constructors.
- `src/sif/embedding/manager.py` — role methods, `get_identity`, `_cache_bucket`, cache vector validation, shared response builder.
- `tests/conftest.py` — autouse `reset_identity_state` fixture (lazy module lookup).
- `tests/unit/embedding/test_identity.py` (new) — 57-test real-database battery.
- `tests/unit/embedding/test_embedder_impl.py` — role/prompt/pooling/revision batteries.
- `tests/unit/embedding/test_manager.py` — bucket, role, cache-safety, and helper batteries.
- `docs/configuration.md` — regenerated (two new settings rows).
- `scripts/generate_config_ref.py` — generator field list extended with the two settings (deviation; see below).

## Decisions Made

- Identity fingerprint excludes `source` and `fingerprint`; assumed and verified records for the same model therefore share a fingerprint, and comparison is field-wise with one-sided unknown-tolerance for pooling/revision.
- Cache vector validation uses the identity dimension (loaded model truth) rather than raw settings; the default ModelScope path has both equal, and real-database/mocked models stay coherent.
- Prompt scheme is resolved once at manager construction and the effective names are handed to the factory; no model-wide `default_prompt_name` is ever set (source-absence gate passes).
- Warn-once state uses a mutable `_IdentityState` container to satisfy ruff PLW0603 and remain resettable.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Extended the config-doc generator's field list**
- **Found during:** Task 1 (identity + settings)
- **Issue:** `make docs-generate` renders only the fields hand-listed in `scripts/generate_config_ref.py::SECTIONS`; the two new Settings fields were silently omitted, so the acceptance criterion requiring `docs/configuration.md` to document `SIF_QUERY_PROMPT_NAME`/`SIF_DOCUMENT_PROMPT_NAME` could not be met without hand-editing a generator-owned file (forbidden).
- **Fix:** Added `query_prompt_name` and `document_prompt_name` to the "Embedding Model Settings" section list, then regenerated the docs and verified a second run is byte-identical.
- **Files modified:** `scripts/generate_config_ref.py`, `docs/configuration.md`
- **Verification:** `make docs-generate` twice; `cmp` identical; `tests/test_docs.py` passes.
- **Committed in:** `c6083a4` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The generator change is required for the plan's own docs acceptance criterion; it adds no runtime behavior and does not touch the generated doc by hand.

## Issues Encountered

- A docs-idempotence check briefly used `git stash` on `docs/configuration.md`. The sole stash entry (verified to contain only that regenerated two-line diff) was removed and the regenerated file restored; no work was lost and no other ref was touched.
- `SentenceTransformerEmbedder.__init__` crossed the `PLR0913` argument threshold once the two keyword-only prompt params landed; added the same `# noqa: PLR0913` already used by the other backend constructors.

## User Setup Required

None - no external service configuration required. No runtime dependency was added (`pyproject.toml`/`uv.lock` untouched).

## Verification

- `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/embedding/test_identity.py tests/unit/embedding/test_embedder_impl.py tests/unit/embedding/test_manager.py -x --no-cov` — 159 passed.
- `ruff check src tests` — clean; `ruff format --check src tests` — clean; `ty check src/sif` — clean.
- Full suite: `env -u FORCE_COLOR NO_COLOR=1 pytest` — **2579 passed, 1 skipped**, total coverage **95.30%** (fail_under=90).
- Prohibitions: `git diff bc322ec..HEAD -- pyproject.toml uv.lock src/sif/core/models.py` is empty (no dependency; `Embedder` protocol unchanged); `grep -rn default_prompt_name src/sif` exits 1; no `.msc`/pickle use in `src/sif/embedding`.

## Self-Check: PASSED

- FOUND: src/sif/embedding/identity.py
- FOUND: src/sif/embedding/prompts.py
- FOUND: src/sif/embedding/roles.py
- FOUND: tests/unit/embedding/test_identity.py
- FOUND: c6083a4
- FOUND: 058f1f3
- FOUND: 64b9604

## Next Phase Readiness

- The identity module, prompt scheme, role methods, and cache buckets are the foundation for plan 21-02 (search boundaries), 21-05 (streaming writer), and Phase 22-24 consumers.
- Residual accepted limitation: a ModelScope local snapshot exposes no revision, so the identity records honest `revision: null`; the `--force` certification path is the only remedy.
- No blockers.

---
*Phase: 21-scale-maintenance-embedder-identity*
*Completed: 2026-11-16*
