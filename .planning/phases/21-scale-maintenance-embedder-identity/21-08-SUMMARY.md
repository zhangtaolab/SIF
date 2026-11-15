---
phase: 21-scale-maintenance-embedder-identity
plan: 08
subsystem: database
tags:
  [
    embedder-identity,
    dimension-guard,
    legacy-migration,
    schema-open,
    watcher,
    mcp,
    prompt-scheme,
    d-02,
    d-04,
    d-05,
  ]

# Dependency graph
requires:
  - phase: 21-scale-maintenance-embedder-identity
    plan: 01
    provides: "identity module (schema_embedding_dim, ensure_legacy_identity, check_identity, build_identity/build_settings_identity), prompt-scheme resolver"
  - phase: 21-scale-maintenance-embedder-identity
    plan: 02
    provides: "create_all ordering (shadow DDL + backfill) that the legacy ensure call slots into"
provides:
  - "IdentityDimensionError + dimension_mismatch_text + schema_dimension_remedy: one shared dimension wording (D-05)"
  - "SchemaManager.initial_identity with check_identity(mode=\"init\") in production and the legacy-assumed write in create_all (D-04)"
  - "Database.init_schema(identity=...) settings-only identity; injected dimensions keep the no-get_settings contract"
  - "Watcher identity adoption at first embed use (delegated FLOAT[n] read, embed-mode check, soft fail)"
  - "SearchBackend settings-only identity at schema open, prompt-aware factory construction, full self._identity"
affects: [21-04, 21-05, 21-06, 22, 23, 24]

# Actuals (#2632) - pairs with the plan's `estimate` (36000 tokens, 2 tasks).
actuals:
  tokens: 11990
  tasks: 2
  commits: 2
plan_head_before: 646dcd12dc7e41fe913c05618d56e7e35ad1df10
plan_head_after: c8a9a7098e70567c8c3a90f565f00f4ec363bf24

tech-stack:
  added: []
  patterns:
    - "One shared dimension sentence family: IdentityDimensionError for the schema guard, dimension_mismatch_text for config-layer checks"
    - "The schema width guard IS the identity init-mode check when the host has an identity; width-only when a dimension is injected"
    - "Legacy-assumed write is idempotent and gated on stored vectors only, never on a fresh/empty index"
    - "Hosts resolve one prompt scheme and reuse it for the recorded identity and the embedder constructor (T-21-28)"
    - "Watcher adoption runs inside one short transaction so a mismatch rolls the assumed row back with the error"

key-files:
  created: []
  modified:
    - src/sif/embedding/identity.py
    - src/sif/embedding/embedder.py
    - src/sif/database/schema.py
    - src/sif/database/database.py
    - src/sif/indexing/watcher.py
    - src/sif/mcp/backend.py
    - tests/unit/database/test_schema.py
    - tests/unit/embedding/test_embedder_impl.py
    - tests/unit/embedding/test_openai_embedder.py
    - tests/unit/indexing/test_watcher.py
    - tests/unit/mcp/test_backend.py
    - tests/unit/cli/test_watch_cmd.py

key-decisions:
  - "IdentityDimensionError renders 'database has FLOAT[n], but settings require FLOAT[m]' + schema_dimension_remedy, byte-identical to the pre-change schema guard; dimension_mismatch_text renders the OpenAI/config sentence, also byte-identical."
  - "With an initial identity the schema guard is check_identity(mode=\"init\"); without one (injected dimension) the pre-existing width-only comparison against self.embedding_dim remains, so the Phase 19 no-get_settings contract is untouched."
  - "create_all calls ensure_legacy_identity after the shadow backfill and before the single commit; the init-mode check normally performs the write first, making the tail call an idempotent no-op."
  - "The watcher adopts manager.get_identity() (the authoritative full identity, the plan's sanctioned public accessor) inside one short `with conn:` block; a mismatch rolls the assumed row back, emits one error event, and disables embedding while BM25 freshness continues."
  - "The MCP backend resolves its scheme once and reuses it for both build_settings_identity and factory.create_model kwargs; the full identity is built with the loaded embedder and stored as self._identity for 21-04's search-mode closure."
  - "The watcher's inline FLOAT[n] regex and its `re` import are gone; schema_embedding_dim from identity.py is the only read it uses."

requirements-completed: [EMB-01]

coverage:
  - id: D1
    description: "The single FLOAT[n] read lives in identity.schema_embedding_dim; the schema guard raises IdentityDimensionError with the byte-identical pre-change message and check_identity(mode=\"init\") has a production caller"
    requirement: EMB-01
    verification:
      - kind: unit
        ref: "tests/unit/database/test_schema.py#TestSchemaManagerVectorTables,TestInitialIdentityAtSchemaOpen"
        status: pass
    human_judgment: false
  - id: D2
    description: "A legacy populated index is assumed once with one warning and no blocking; a fresh/embeddings-empty index writes no identity; an injected dimension without an identity performs no legacy write and never reads settings"
    requirement: EMB-01
    verification:
      - kind: unit
        ref: "tests/unit/database/test_schema.py#TestInitialIdentityAtSchemaOpen,TestDatabaseInitSchemaIdentity"
        status: pass
    human_judgment: false
  - id: D3
    description: "The watcher delegates its schema read, adopts the identity at first embed use, and fails a same-width or width mismatch soft: one error event, embedding disabled for the session, BM25 freshness unchanged"
    requirement: EMB-01
    verification:
      - kind: unit
        ref: "tests/unit/indexing/test_watcher.py#TestEmbedDepth"
        status: pass
    human_judgment: false
  - id: D4
    description: "MCP init passes a settings-only identity (legacy DB gets the assumed row), the factory receives both resolved prompt names, and a successful load stores the matching full identity (None after a failed load)"
    requirement: EMB-01
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_backend.py#TestEmbedderIdentityAtStartup"
        status: pass
    human_judgment: false
  - id: D5
    description: "Full regression suite and quality gates stay green with the configured coverage floor"
    requirement: EMB-01
    verification:
      - kind: other
        ref: "env -u FORCE_COLOR NO_COLOR=1 pytest (2638 passed, 1 skipped, 95.25%); ruff check; ruff format --check; ty check src/sif"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-11-16
status: complete
---

# Phase 21 Plan 08: Identity-Aware Schema Open, Watcher Adoption, and Prompt-Aware MCP Construction

**One shared `FLOAT[n]` read and a mode-aware identity check replace the inline dimension guards; legacy indexes are assumed exactly once (`source="legacy-assumed"`, one warning) while fresh indexes stay clean, the watcher fails its embed session soft on a mismatch, and the MCP backend constructs its embedder with the same prompt scheme it records.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-11-15T16:50:22Z
- **Completed:** 2026-11-15T17:01:58Z (2026-11-16 local)
- **Tasks:** 2
- **Files modified:** 12 (6 source, 6 test)
- **Commits:** 2 task commits

## Accomplishments

- `src/sif/embedding/identity.py` now owns the whole dimension-error vocabulary: `IdentityDimensionError(RuntimeError)` with `stored_dimension`/`current_dimension`/`remedy`, `dimension_mismatch_text(...)`, and `schema_dimension_remedy(...)`. The schema guard's and the OpenAI constructor's pre-change sentences survive byte-identically.
- `SchemaManager._create_vector_tables` delegates its width read to `schema_embedding_dim`; with `initial_identity` it runs `check_identity(mode="init")` (the init mode now has its production caller) and raises `IdentityDimensionError`, and without one it keeps the injected-dimension width-only comparison. The created vec0 SQL is unchanged.
- `SchemaManager.create_all` calls `ensure_legacy_identity` after the shadow backfill and before the single commit. A legacy populated index is written once as `source="legacy-assumed"` with one warning per process; a fresh/embeddings-empty index writes nothing; a second open is silent. `drop_all`/`create_all` still produce only the fresh version markers.
- `Database.init_schema(embedding_dim=None, identity=None)` builds the settings-only identity (resolving the prompt scheme from Settings) when neither is supplied, takes the width from a supplied identity, and passes `initial_identity=None` for an injected dimension — so `get_settings()` is never consulted on the Phase 19 injected path.
- `_EmbedSession.ensure_ready` adopts `manager.get_identity()` inside one short transaction: it assumes a legacy identity once, then runs the embed-mode check. A same-width model swap or width disagreement raises before any vector work; the existing except turns it into one `error` event with both identities and the `--force` remedy, disables embedding for the session, and BM25 freshness continues. `_schema_embedding_dim` is now a delegation to `schema_embedding_dim`.
- `SearchBackend.__init__` resolves one prompt scheme from its own settings and uses it for both `build_settings_identity` (passed to `init_schema`, including a legacy DB's assumed row) and `factory.create_model(query_prompt_name=..., document_prompt_name=...)`. After a successful load it stores the full `build_identity(...)` as `self._identity` for 21-04; a failed load keeps the one-warning BM25 degradation with `self._identity is None`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Share the dimension guard and assume legacy identities at schema open** — `329f91c` (feat)
2. **Task 2: Adopt the identity at watcher and MCP open** — `c8a9a70` (feat)

**Plan metadata:** the final docs commit captures this SUMMARY plus STATE/ROADMAP updates.

## Files Created/Modified

- `src/sif/embedding/identity.py` — `_SCHEMA_GUARD_REMEDY`, `schema_dimension_remedy`, `dimension_mismatch_text`, `IdentityDimensionError`.
- `src/sif/embedding/embedder.py` — OpenAI endpoint-vs-`SIF_EMBEDDING_DIM` now renders through `dimension_mismatch_text`.
- `src/sif/database/schema.py` — `initial_identity` on `__init__`, init-mode check + shared read in `_create_vector_tables`, `ensure_legacy_identity` at the tail of `create_all`.
- `src/sif/database/database.py` — `init_schema(embedding_dim=None, identity=None)` with the settings-only identity construction.
- `src/sif/indexing/watcher.py` — identity adoption/check in `ensure_ready`, delegated `_schema_embedding_dim`, inline regex and `re` import removed.
- `src/sif/mcp/backend.py` — one resolved scheme, settings-only identity at init, prompt-aware factory kwargs, full `self._identity`.
- `tests/unit/database/test_schema.py` — exact schema message/type/attributes, delegation, init-mode caller, legacy-assumed once/fresh-no-write/injected-no-settings batteries.
- `tests/unit/embedding/test_embedder_impl.py` — shared wording byte-identity.
- `tests/unit/embedding/test_openai_embedder.py` — exact OpenAI message and a spy proving it is produced through `dimension_mismatch_text`.
- `tests/unit/indexing/test_watcher.py` — real identity in the manager mock, delegated read proof, same-width mismatch soft-fail battery.
- `tests/unit/mcp/test_backend.py` — init identity kwargs, prompt kwargs + stored identity, failed-load None, legacy-DB assumed row.
- `tests/unit/cli/test_watch_cmd.py` — local manager mock reports the same real identity (collateral; see deviations).

## Decisions Made

- **Two wording helpers, one family.** `IdentityDimensionError` owns the schema sentence ("database has FLOAT[n] ... settings require FLOAT[m]") and `dimension_mismatch_text` owns the "X produces n-dimensional embeddings but Y is set to m" sentence; both reproduce the pre-change text exactly, so users can always name the disagreeing model/width (T-21-27).
- **The init-mode check is the guard when an identity exists.** This gives `check_identity(mode="init")` its production caller and keeps the injected-dimension path exactly as Phase 19 defined it (no settings read, width-only, same RuntimeError text).
- **The assumed write is a tail step.** The init-mode check normally writes it first; the documented `ensure_legacy_identity` after the shadow backfill is an idempotent no-op that guarantees the ordering even if the guard path changes. `_has_stored_vectors` is the only gate, so a fresh index can never gain an identity row.
- **`manager.get_identity()` is the watcher's `current`.** It is the authoritative full identity (loaded-model pooling/revision included) and is the plan's sanctioned public accessor; the watcher resolves settings only for chunking and the session's other state.
- **Adoption is transactional and soft.** The `with self._conn:` block commits the assumed row on success and rolls it back when the check raises, so a mismatched index is not mutated; the one-error-event/embedding-disabled contract is unchanged.
- **MCP records exactly what it applies.** One `resolve_prompt_scheme` result feeds both the persisted identity and the factory, closing T-21-28 (a host that records prompts must embed with them). The full identity is stored for 21-04's search-mode closure; no search behavior is wired here.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] OpenAI wording tests live in `test_openai_embedder.py`, not `test_embedder_impl.py`**

- **Found during:** Task 1 (dimension wording)
- **Issue:** The plan named `tests/unit/embedding/test_embedder_impl.py` as the home of the OpenAI endpoint-check assertion, but the OpenAI constructor battery (fake `openai` module, endpoint probe, dimension cache) lives in `tests/unit/embedding/test_openai_embedder.py`. A helper-only assertion in `test_embedder_impl.py` cannot prove the constructor composes through the shared helper.
- **Fix:** Added the direct shared-wording byte-identity test to `test_embedder_impl.py` and pinned the exact message plus a `dimension_mismatch_text` spy in `test_openai_embedder.py`.
- **Files modified:** `tests/unit/embedding/test_embedder_impl.py`, `tests/unit/embedding/test_openai_embedder.py`
- **Verification:** Both files pass; full suite green.
- **Committed in:** `329f91c` (Task 1 commit)

**2. [Rule 3 - Blocking] The watch CLI has its own manager mock**

- **Found during:** Task 2 (full-suite regression)
- **Issue:** `tests/unit/cli/test_watch_cmd.py::TestStartupReconcileEmbedDepth::test_embed_startup_leaves_no_vectorless_documents` failed because that module defines its own `_embed_manager_mock`; without a real `get_identity`, the watcher's new adoption step saw a MagicMock identity, disabled embedding, and left the drifted document vector-less.
- **Fix:** Gave that helper the same real `build_identity(...)` return value used in the watcher battery.
- **Files modified:** `tests/unit/cli/test_watch_cmd.py`
- **Verification:** 39 watch-command tests pass; full suite green.
- **Committed in:** `c8a9a70` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both are test-only collateral forced by the real plan change; no production scope was added. The plan's declared test list under-counted the existing OpenAI and watch-CLI mocks.

## Issues Encountered

- A direct `_create_vector_tables` unit call needed `_create_index_meta_table()` first: `check_identity` reads `index_meta`, which production `create_all` always creates before the vector tables. The tests now mirror that ordering; production behavior is unchanged.
- No package installs, no schema changes, no new dependencies (`pyproject.toml`/`uv.lock` untouched).

## User Setup Required

None - no external service configuration required.

## Verification

- `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/database/test_schema.py tests/unit/embedding/test_embedder_impl.py tests/unit/indexing/test_watcher.py tests/unit/mcp/test_backend.py -x --no-cov` — 270 passed.
- Per-task gates: schema + embedder 138 passed; watcher 54 passed; backend 97 passed.
- `ruff check src tests` — clean; `ruff format --check src tests` — 214 files already formatted; `ty check src/sif` — clean.
- Full suite: `env -u FORCE_COLOR NO_COLOR=1 pytest` — **2638 passed, 1 skipped**, total coverage **95.25%** (fail_under=90).
- Grep gates: `schema_embedding_dim` in `schema.py` = 2; `initial_identity` in `schema.py` = 9; `IdentityDimensionError` in `identity.py` = 1; `check_identity` in `watcher.py` = 2; `query_prompt_name` and `self._identity` in `backend.py` = 2 each.
- Prohibitions:
  - Fresh/empty index: `test_fresh_index_writes_no_identity` (SchemaManager) and `test_drop_all_removes_index_meta_and_create_all_recreates_it` prove no identity row.
  - Injected dimension: `test_injected_dimension_without_identity_never_reads_settings_or_writes` patches `get_settings` to raise; the call succeeds and writes nothing.
  - Message texts: the schema and OpenAI messages are asserted byte-identical (including full-string equality).
  - Prompt scheme: `test_factory_receives_the_resolved_prompt_scheme_and_identity_is_stored` asserts both kwargs and the stored identity fields.
  - The only remaining `FLOAT[n]` regex read is `src/sif/cli/commands/index.py:255` (the `embed_cmd` site, delegated to 21-05 by the plan's must_haves); `schema.py` and `watcher.py` have none.

## Known Stubs

None.

## Threat Flags

None - the identity row is local SQLite state and the change introduces no network endpoint, auth path, or new file-access surface. The plan's mitigations are the ones verified above: T-21-26 (legacy assumption accepted, search never blocked), T-21-27 (shared byte-identical wording), T-21-28 (one scheme for identity + construction).

## Next Phase Readiness

- 21-04 can build the search-mode closure from `SearchBackend._identity` and the existing `check_identity(..., mode="search")`; `enrich_results(vectors_untrusted=...)` is already in place.
- 21-05 owns the remaining `embed_cmd` guard and the first-vector-write identity (`source="verified"` / `--force` certification); the schema/watcher paths here are compatible with that rewrite.
- Residual accepted limitation (unchanged): an assumed identity leaves `pooling`/`revision` unknown until a full `--force` re-embed certifies it. No blockers.

## Self-Check: PASSED

- FOUND: src/sif/embedding/identity.py
- FOUND: src/sif/embedding/embedder.py
- FOUND: src/sif/database/schema.py
- FOUND: src/sif/database/database.py
- FOUND: src/sif/indexing/watcher.py
- FOUND: src/sif/mcp/backend.py
- FOUND: 329f91c
- FOUND: c8a9a70
