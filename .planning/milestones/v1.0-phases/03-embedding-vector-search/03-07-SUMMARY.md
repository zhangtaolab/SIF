---
phase: 03-embedding-vector-search
plan: 07
subsystem: embedding
tags: [openai, embeddings, vector-search, factory-pattern, dimension-detection, api-client]

requires:
  - phase: 03-embedding-vector-search (plans 03-01..03-06)
    provides: Settings model_type/api_key/api_base surface, EmbeddingManager.from_settings,
      EmbeddingModelFactory dispatch, Embedder protocol, sqlite-vec vector storage
provides:
  - OpenAIEmbedder(Embedder) — embed/embed_batch/dimension against any OpenAI-compatible
    endpoint addressed as {api_base}/embeddings via the SDK base_url parameter
  - Dimension auto-detection: one minimal API probe cached per model to
    openai_dim_cache.json (7-day TTL) with fail-fast SIF_EMBEDDING_DIM mismatch validation
  - Factory wiring for ModelType.OPENAI (the load-time dead end is removed) plus honest
    factory signatures (-> Embedder, **kwargs: Any)
  - openai optional extra (openai>=2.0.0) in pyproject.toml, also in the all extra
  - The two missing Wave-0 test artifacts — test_factory.py (7 tests) and
    test_openai_embedder.py (15 tests)
affects: [04-advanced-search-pipeline, 09-mcp-server-implementation, phase-verification, ship]

actuals:
  tokens: 9400
  tasks: 3
  commits: 5

tech-stack:
  added:
    - "openai>=2.0.0 (optional extra; legitimacy verified at plan time — official OpenAI
      publisher, Trusted Publishing, Apache-2.0)"
  patterns:
    - "Recording fake openai module via patch.dict('sys.modules') — constructor kwargs and
      embeddings.create calls captured for wiring assertions"
    - "File-based dimension cache: JSON map keyed by model name with ISO-8601 detected_at
      and TTL; cache is an optimization, the probe is the correctness source"
    - "Fail-fast load-time validation of configured vs API-detected dimension (extends the
      D-09 schema-mismatch philosophy to backend selection)"

key-files:
  created:
    - tests/unit/embedding/test_openai_embedder.py
    - tests/unit/embedding/test_factory.py
  modified:
    - src/sif/embedding/embedder.py
    - src/sif/embedding/factory.py
    - pyproject.toml
    - tests/unit/cli/test_index.py

key-decisions:
  - "D-04 realized via OpenAI(api_key=..., base_url=...) constructed once in __init__; the
    SDK appends the /embeddings path, api_base=None uses the SDK default endpoint"
  - "D-05 realized with the API as dimension source of truth: single minimal probe
    (input=['.']) cached per model in openai_dim_cache.json with 7-day (604800s) TTL;
    missing/corrupt/unreadable cache degrades to a probe with a warning, never crashes load"
  - "Configured embedding_dim disagreeing with the detected dimension fails fast at load
    with both values named plus SIF_EMBEDDING_DIM (prevents opaque sqlite-vec
    wrong-number-of-entries insert errors later)"
  - "api_key passes only to the client constructor — never logged, interpolated, or
    embedded in exception messages (threat T-03-01)"
  - "Honest factory signatures completed what plan 03-02's title promised and 03-REVIEW
    WR-01/WR-02 flagged: create_model/_create_* return Embedder, kwargs typed Any,
    ModelType imported from the canonical sif.models.embedding"

patterns-established:
  - "Recording-fake-module injection: assert SDK client constructor kwargs and API call
    payloads through sys.modules patching, reusable for any future remote backend"
  - "Per-model TTL dimension cache file living beside the embedding cache in the
    configured cache dir"

requirements-completed: [VEC-01]

coverage:
  - id: D1
    description: "OpenAIEmbedder backend — embed/embed_batch/dimension with batch slicing,
      ragged-response guard before any write, L2 normalization, no partial persistence on
      mid-batch failure, ImportError hint naming sif[openai]"
    requirement: VEC-01
    verification:
      - kind: unit
        ref: "tests/unit/embedding/test_openai_embedder.py::TestOpenAIEmbedderBehavior (7 tests, pass)"
        status: pass
      - kind: unit
        ref: "tests/unit/embedding/test_openai_embedder.py::TestOpenAIEmbedderEndToEnd::test_settings_to_embeddings_end_to_end (pass)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Factory wiring + honest signatures — _create_openai_model constructs
      OpenAIEmbedder from api_key/api_base/embedding_dim/cache_dir kwargs; every
      create_model/_create_* signature reads -> Embedder and **kwargs: Any"
    requirement: VEC-01
    verification:
      - kind: unit
        ref: "tests/unit/embedding/test_factory.py::TestEmbeddingModelFactoryDispatch (7 tests, pass)"
        status: pass
      - kind: other
        ref: "inspect.getsource(EmbeddingModelFactory) assertion: 'OpenAIEmbedder' present, '-> EmbeddingModel' and 'dict[str, any]' absent; stub grep inverted"
        status: pass
    human_judgment: false
  - id: D3
    description: "Dimension auto-detection with local cache — probe once then cache hit,
      JSON schema per model, 7-day TTL expiry, per-model keys, corrupt-cache-as-miss,
      no-cache-dir behavior, fail-fast mismatch naming both values + SIF_EMBEDDING_DIM"
    requirement: VEC-01
    verification:
      - kind: unit
        ref: "tests/unit/embedding/test_openai_embedder.py::TestOpenAIEmbedderDimensionCache (8 tests, pass)"
        status: pass
    human_judgment: false
  - id: D4
    description: "openai optional extra (openai>=2.0.0) declared in pyproject.toml and
      included in the all extra"
    verification:
      - kind: other
        ref: "tomllib parse of [project.optional-dependencies]: openai extra and all extra both list openai>=2.0.0 (pass)"
        status: pass
    human_judgment: false
  - id: D5
    description: "CLI path — sif embed --model-type openai reaches the endpoint through the
      real EmbeddingManager (no manager mock): exit 0 and a recorded embeddings.create call
      carrying the configured model name"
    requirement: VEC-01
    verification:
      - kind: integration
        ref: "tests/unit/cli/test_index.py::TestEmbedCommand::test_embed_cmd_openai_model_type_reaches_endpoint (pass)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Live OpenAI-compatible endpoint behavior (VEC-01 final satisfaction):
      SIF_MODEL_TYPE=openai with SIF_API_BASE/SIF_API_KEY/SIF_MODEL_NAME against a real
      endpoint, sif vsearch <query>"
    requirement: VEC-01
    verification: []
    human_judgment: true
    rationale: "Requires a live API key and remote service (plan verification item 5);
      all automated tests mock the endpoint. settings.model_name must be set to the
      endpoint's model id (the shared default is a local-model id)."

duration: 23min
completed: 2026-09-03
status: complete
---

# Phase 3 Plan 7: OpenAI-Compatible Embedding Backend (Gap Closure) Summary

**OpenAIEmbedder(Embedder) with generic OpenAI-compatible endpoint support (api_base → {api_base}/embeddings), per-model dimension auto-detection cached to openai_dim_cache.json with a 7-day TTL and fail-fast SIF_EMBEDDING_DIM mismatch validation, wired through EmbeddingModelFactory — closing the single 03-VERIFICATION VEC-01 gap and delivering both missing Wave-0 test files.**

## Performance

- **Duration:** 23min
- **Started:** 2026-09-03T03:13:55Z
- **Completed:** 2026-09-03T03:37:19Z
- **Tasks:** 3/3
- **Files modified:** 6 (2 src, 3 tests, 1 packaging)

## Accomplishments

- The exact path that failed verification (Settings → EmbeddingManager.from_settings →
  EmbeddingModelFactory.create_model → OpenAIEmbedder.embed) now returns embeddings;
  `SIF_MODEL_TYPE=openai` and `--model-type openai` no longer terminate in
  "OpenAI models not yet implemented"
- api_key/api_base flow all the way into the OpenAI client constructor (asserted by
  captured constructor kwargs in both the factory test and the env-path test)
- Dimension handling per D-05: endpoint-probed once, cached per model for 7 days,
  mismatched SIF_EMBEDDING_DIM fails fast at load naming both values
- Honest factory signatures completed the 03-02-promised refactor (03-REVIEW WR-01/WR-02):
  `-> Embedder` returns, `**kwargs: Any`, ModelType from sif.models.embedding
- Full quality suite green: ruff check, ruff format --check, pytest
  **528 passed, 11 skipped, 0 failed** (baseline 505 passed, 11 skipped — +23 tests)

## Task Commits

Each task was committed atomically (TDD: test before feat):

1. **Task 1: End-to-end openai backend tracer** — `789da35` (test: 6-behavior failing suite) + `37d353c` (feat: OpenAIEmbedder, factory wiring, honest signatures, openai extra)
2. **Task 2: Dimension auto-detection with local cache** — `159e7fc` (test: 8 failing cache/mismatch tests) + `981855e` (feat: probe/cache/TTL/fail-fast mismatch)
3. **Task 3: Factory dispatch matrix + CLI path** — `445ecca` (test: test_factory.py 7 tests, CLI openai test)

**Plan metadata:** see final docs commit

## Files Created/Modified

- `src/sif/embedding/embedder.py` — added `OpenAIEmbedder(Embedder)` after ModelScopeEmbedder: lazy openai import with `pip install sif[openai]` hint, client built once in `__init__`, `embed`/`embed_batch` (batch_size slicing, ragged-response RuntimeError before any write), numpy L2 normalization, `dimension` property, and private `_resolve_dimension`/`_read_dim_cache`/`_write_dim_cache`/`_probe_dimension` helpers
- `src/sif/embedding/factory.py` — `_create_openai_model` constructs OpenAIEmbedder from the four kwargs (raise stub deleted; the distinct HuggingFace stub untouched per plan); honest signatures across all six methods; imports Embedder from sif.core.models and ModelType from sif.models.embedding (sif.embedding.model import removed)
- `pyproject.toml` — new `openai = ["openai>=2.0.0"]` extra, also listed in `all`
- `tests/unit/embedding/test_openai_embedder.py` — 15 tests: end-to-end manager path, batching/order, ragged guard, ImportError hint, normalization, no-partial-persistence, empty input, probe-then-cache-hit, cache schema, TTL expiry, no-cache-dir, per-model keys, mismatch fail-fast, corrupt cache, manager-path probe regression
- `tests/unit/embedding/test_factory.py` — 7 tests: dispatch matrix (ST/GGUF/openai/ModelScope), both ValueError guards, SIF_MODEL_TYPE env path through from_settings/load_model, advertised-backend construct invariant
- `tests/unit/cli/test_index.py` — added `test_embed_cmd_openai_model_type_reaches_endpoint` (real EmbeddingManager + fake openai module; asserts exit 0, no failure text, recorded create call with configured model name)

## Decisions Made

None beyond plan — the constructor signature, cache file name, TTL, probe input, and error wording followed the plan; Claude-discretion items (cache location/TTL were locked by 03-RESEARCH resolved open question 1) implemented as specified.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] PLR0911 too-many-returns in `_read_dim_cache`**
- **Found during:** Task 2 (dimension cache GREEN)
- **Issue:** Initial helper had 7 return statements; ruff max is 6
- **Fix:** Merged the malformed-top-level branch into an isinstance-guarded `cache.get()` expression (also silencing spurious warnings on routine per-model misses)
- **Files modified:** src/sif/embedding/embedder.py
- **Verification:** `ruff check` green; all 15 openai tests pass
- **Committed in:** `981855e` (part of task commit)

**2. [Rule 1 - Bug] ARG002 unused `tmp_path` fixture argument**
- **Found during:** Task 2 GREEN lint pass
- **Issue:** `test_no_cache_dir_probes_per_instance` declared an unused fixture
- **Fix:** Removed the parameter (cache_dir=None does no file operations, so there is nothing to assert under tmp_path)
- **Files modified:** tests/unit/embedding/test_openai_embedder.py
- **Verification:** ruff green; test passes
- **Committed in:** `981855e` (part of task commit)

**3. [Rule 3 - Blocking] B009/ARG001 lint violations in Task 3 test surface**
- **Found during:** Task 3 full-suite verify
- **Issue:** `getattr` with constant attribute names (B009 x3) and an unused `**kwargs` in the CLI fake constructor (ARG001)
- **Fix:** Direct attribute access with `model: Any` annotation in `_assert_working_embedder`; the CLI fake now records constructor kwargs
- **Files modified:** tests/unit/embedding/test_factory.py, tests/unit/cli/test_index.py
- **Verification:** `ruff check src tests` + `ruff format --check src tests` green; 528 passed suite-wide
- **Committed in:** `445ecca` (part of task commit)

---

**Total deviations:** 3 auto-fixed (2x Rule 1 lint bugs, 1x Rule 3 blocking lint)
**Impact on plan:** None — all were lint-hygiene fixes inside files the tasks already owned; no behavioral deviation from the plan.

## TDD Gate Compliance

All three tasks carried `tdd="true"`; gate commits verified in git log:

- Task 1: `test(03-07)` (789da35) precedes `feat(03-07)` (37d353c) — RED failed on ImportError (class absent), GREEN passed 7 tests
- Task 2: `test(03-07)` (159e7fc) precedes `feat(03-07)` (981855e) — RED failed 7/8 new tests, GREEN passed 15
- Task 3: single `test(03-07)` commit (445ecca) — the plan explicitly designates Task 3 as test-surface-only ("Do not modify any production file — the factory and embedder are final after Task 2"), so its matrix passing immediately is the expected outcome, not an unexpected GREEN: the behaviors it locks in were RED in Tasks 1-2, and the tests go red again if a Settings-advertised backend ever dead-ends at load

## Issues Encountered

None. Out-of-scope discovery logged to `deferred-items.md`: mypy cannot run in this environment (pre-existing — sentence-transformers 5.4.1 uses 3.10+ syntax while pyproject pins mypy python_version=3.9; errors cite classes untouched by this plan). The mandated CLAUDE.md quality suite (ruff + pytest) is fully green.

## Known Stubs

- `src/sif/embedding/factory.py:82` — `raise NotImplementedError("HuggingFace models not yet implemented")`. Pre-existing and intentionally untouched: the plan's action says the sibling HuggingFace stub stays (out of scope per 03-VERIFICATION.md anti-pattern table; HuggingFace is not a VEC-01-named backend and is absent from CLI `--model-type` choices). Not a blocker for this plan's goal.

## Authentication Gates

None — all automated tests mock the openai module. The live-endpoint human check (coverage D6) requires the user's own API key.

## User Setup Required

Optional (only for the live-endpoint human verification, plan verification item 5): set `SIF_MODEL_TYPE=openai`, `SIF_API_BASE=https://<compatible-endpoint>/v1`, `SIF_API_KEY=...`, and `SIF_MODEL_NAME=<endpoint-model-id>` — note `model_name` must be the endpoint's API model id, not the local default — then run `sif vsearch <query>` against a real endpoint.

## Next Phase Readiness

**Phase 03 complete, ready for verification.** This was the last plan (7 of 7). The single verification gap from 03-VERIFICATION.md is closed: every backend Settings advertises under VEC-01 (sentence_transformers, gguf, openai) now constructs through the factory, both Wave-0 test files exist and pass, and the full suite is green (528 passed, 11 skipped). VEC-02/03/04 surfaces untouched. Remaining human check: live OpenAI-compatible endpoint (coverage D6). The HuggingFace factory stub and the mypy environment issue are recorded in Known Stubs / deferred-items.md for the verifier's awareness.

## Self-Check: PASSED

All 7 created/modified files exist on disk; all 5 task commits (789da35, 37d353c, 159e7fc, 981855e, 445ecca) verified in git log.

---
*Phase: 03-embedding-vector-search*
*Completed: 2026-09-03*
