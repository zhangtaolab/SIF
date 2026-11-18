---
phase: 21-scale-maintenance-embedder-identity
plan: 04
subsystem: search
tags:
  [embedder-identity, identity-mismatch, vectors-stale, role-aware-embed, search-pipeline, vsearch, bench, eval, mcp, d-03, d-04, d-06]

# Dependency graph
requires:
  - phase: 21-scale-maintenance-embedder-identity
    plan: 01
    provides: "identity module (check_identity, warn-once latch, build_identity), role helpers (embed_query/embed_queries), EmbeddingManager.get_identity and role surface"
  - phase: 21-scale-maintenance-embedder-identity
    plan: 03
    provides: "enrich_results(..., vectors_untrusted=True) seam and the CORR-05 single-enrichment contract at every exit"
  - phase: 21-scale-maintenance-embedder-identity
    plan: 08
    provides: "IdentityDimensionError + shared dimension wording, settings identity at schema open, MCP self._identity from the loaded embedder"
provides:
  - "SearchPipeline.identity_check / _identity_state: one lazy search-mode check on VECTOR/HYDE/hybrid exits, BM25 stays check-free"
  - "Same-dimension swap policy: one stderr warning per process per pair and vectors_stale=True on every returned row, on hybrid, vec:, hyde:, vsearch and MCP"
  - "Width mismatch policy: IdentityDimensionError on vec:/hyde:, marked BM25 degradation on hybrid/MCP, remedy-bearing ClickException in vsearch/bench/eval"
  - "Query-role embeds on the hybrid, vec:, hyde:, vsearch, expansion query+candidate, and bench/eval measured legs"
  - "CachedEmbedder role methods memoized by (role, text); BenchHarness.identity_check; eval _load_embedder returns the full identity"
  - "search_dimension_error + SEARCH_DIMENSION_REMEDY shared by every search host"
affects: [21-05, 21-06, 21-07, 22, 23, 24]

# Actuals (#2632) - pairs with the plan's `estimate` (60000 tokens, 2 tasks).
actuals:
  tokens: 24964
  tasks: 2
  commits: 2
plan_head_before: e9cf243f57fab55df20b62b86d311ed9f053fbd7
plan_head_after: c9386e78c95babda34edb45b35ffc060432660c7

tech-stack:
  added: []
  patterns:
    - "Injected lazy identity closure: the host binds one current identity, the pipeline evaluates it once per instance and only on a vector-touching route"
    - "Warn-once latch shared across pipelines; per-result warnings forbidden, marking is the only per-row signal"
    - "One shared search-mode dimension remedy (search_dimension_error) reused by pipeline, vsearch, bench, and eval"
    - "Role dispatch reaches every query consumer; protocol-only doubles (MagicMock, ConceptEmbedder) keep the plain embed path"
    - "Batch role APIs are memoized per text by calling them with one-element lists under a (role, text) key"

key-files:
  created: []
  modified:
    - src/sif/search/hybrid.py
    - src/sif/cli/commands/search.py
    - src/sif/search/expansion.py
    - src/sif/cli/commands/bench.py
    - src/sif/cli/commands/eval.py
    - src/sif/mcp/backend.py
    - tests/unit/search/test_hybrid.py
    - tests/unit/cli/test_search.py
    - tests/unit/cli/test_bench.py
    - tests/unit/cli/test_eval.py
    - tests/unit/inference/test_query_expander.py
    - tests/unit/mcp/test_backend.py

key-decisions:
  - "The pipeline caches the IdentityCheck for its lifetime and evaluates the closure only on VECTOR/HYDE/hybrid-with-embedder; the BM25 exit returns before any call, so lexical search never pays for identity work (D-03)."
  - "A width mismatch on the hybrid route runs the BM25 variant search instead of the hybrid searcher, so fusion, reranking, pagination, and the single enrichment stay identical on the degraded path and every row is marked stale."
  - "The search-mode dimension remedy lives in hybrid.py (search_dimension_error + SEARCH_DIMENSION_REMEDY) so the pipeline and all CLI hosts share one sentence without editing identity.py outside this plan's file scope."
  - "Every host treats a manager that cannot return a real EmbedderIdentity as having no identity policy; a real EmbeddingManager always returns one, while injected doubles never fabricate a check against a non-SQLite connection."
  - "CachedEmbedder reuses batch role methods with one-element lists so the (role, text) memo still guarantees one inner call per text, and query/document/plain vectors of the same text stay distinct (D-08)."
  - "expansion.py normalizes the manager's EmbeddingResponse and the protocol fallback's bare list through getattr(response, 'embeddings', response), keeping candidate ordering and exception handling unchanged."

patterns-established:
  - "Identity distrust is expressed only through the existing derived vectors_stale flag; no result field, schema, or MCP protocol change"
  - "Blocking dimension refusals happen before measurement/search, while same-dimension swaps never block — they warn once and mark"
  - "A test double without a class-level role method exercises the documented plain-embed fallback; role spies cover the prompted path"

requirements-completed: [EMB-01, EMB-02]

coverage:
  - id: D1
    description: "SearchPipeline warns once and marks every row on a same-dimension swap, stays silent on an assumed identity that matches, never evaluates identity on BM25, degrades a width mismatch to marked BM25, and raises IdentityDimensionError on vec:/hyde:"
    requirement: EMB-01
    verification:
      - kind: unit
        ref: "tests/unit/search/test_hybrid.py#TestSearchPipelineIdentity"
        status: pass
    human_judgment: false
  - id: D2
    description: "sif query emits exactly one identity warning and marks every JSON row on a same-dimension swap, repeats silently, and sif search stays check-free"
    requirement: EMB-01
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestSearchIdentityPolicy"
        status: pass
    human_judgment: false
  - id: D3
    description: "vsearch embeds its query through embed_query, warns once and marks on a swap, raises a remedy-bearing ClickException on a width mismatch before searching, and keeps its existing enrichment for ok/absent"
    requirement: EMB-01
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestSearchIdentityPolicy"
        status: pass
    human_judgment: false
  - id: D4
    description: "The hybrid, vec:, and hyde: legs record embed_query on a role-capable embedder and plain embed on a protocol-only double; the SC1 golden is unchanged"
    requirement: EMB-02
    verification:
      - kind: unit
        ref: "tests/unit/search/test_hybrid.py#TestSearchPipelineIdentity"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_hybrid.py#TestHybridSC1PipelineGolden"
        status: pass
    human_judgment: false
  - id: D5
    description: "Expansion's query and candidate legs use embed_query/embed_queries; the MagicMock fallback still returns a list without raising"
    requirement: EMB-02
    verification:
      - kind: unit
        ref: "tests/unit/inference/test_query_expander.py#TestQueryExpansionRoles"
        status: pass
    human_judgment: false
  - id: D6
    description: "CachedEmbedder memoizes by (role, text), delegates role methods, and falls back for protocol doubles; bench refuses a width mismatch before measuring and passes the closure on a same-dimension swap"
    requirement: EMB-01
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_bench.py#TestCachedEmbedderRoles"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_bench.py#TestBenchIdentityPolicy"
        status: pass
    human_judgment: false
  - id: D7
    description: "Eval's hoisted pipeline receives the identity closure, refuses a width mismatch before any query, and warns once on a same-dimension swap without blocking"
    requirement: EMB-01
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_eval.py#TestEvalIdentityPolicy"
        status: pass
    human_judgment: false
  - id: D8
    description: "MCP hybrid search warns once and marks mapped metadata on a same-dimension swap, returns marked BM25 on a width mismatch without a protocol error, and passes no closure when the embedder load failed"
    requirement: EMB-01
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_backend.py#TestHybridSearchIdentity"
        status: pass
    human_judgment: false

duration: 14min
completed: 2026-11-16
status: complete
---

# Phase 21 Plan 04: Vector-Space Enforcement at Every Search Boundary

**Same-dimension embedder swaps now warn once and mark every result stale across hybrid, vec:, hyde:, vsearch, bench, eval, and MCP; width mismatches fail or degrade with a shared remedy; every query-side embed uses the query role.**

## Performance

- **Duration:** 14 min
- **Started:** 2026-11-15T17:03:12Z
- **Completed:** 2026-11-15T17:17:23Z (2026-11-16 local)
- **Tasks:** 2
- **Files modified:** 12 (6 source, 6 test)
- **Commits:** 2 task commits

## Accomplishments

- `SearchPipeline` accepts an injected search-mode identity closure, evaluates it once per instance, and only on vector-touching exits; the BM25 `sif search` path evaluates nothing and marks nothing.
- A same-dimension swap emits exactly one stderr warning per process per identity pair and sets `vectors_stale=True` on every returned row; a repeated search is silent, a new identity pair warns again, and an assumed legacy identity that matches the loaded model stays silent (D-04).
- A width mismatch cannot produce a vector result: `vec:`/`hyde:` raise `IdentityDimensionError` with both widths and the `sif index embed --force` remedy, the hybrid route returns BM25 rows marked stale, `vsearch` raises a remedy-bearing `ClickException` before searching, and bench/eval refuse before measuring.
- The query role now reaches every query consumer: hybrid, `vec:`, `hyde:`, vsearch, expansion query/candidate legs, and the bench/eval measured pipelines. Protocol-only doubles keep the plain `embed` path, and the SC1 no-prompt golden is byte-identical.
- `CachedEmbedder` memoizes by `(role, text)` so the same text as query and document yields two inner calls; `BenchHarness` carries the identity closure into every measured pipeline.
- MCP `hybrid_search` closes over the full identity stored at embedder load: one warning and marked metadata on a swap, marked BM25 on a width mismatch, and the existing BM25 degradation untouched when the embedder failed to load.
- No `SearchResult` field, database schema, MCP protocol, or stdout/JSON shape changed; warnings are stderr-only.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end same-dimension swap on `sif query` - one warning, all results marked stale; query-role embeds; BM25 silent** - `47c51f9` (feat)
2. **Task 2: Remaining vector-touching boundaries - expansion/bench/eval role legs and the MCP search closure** - `c9386e7` (feat)

**Plan metadata:** the final docs commit captures this SUMMARY plus STATE/ROADMAP updates.

## Files Created/Modified

- `src/sif/search/hybrid.py` - `search_dimension_error`/`SEARCH_DIMENSION_REMEDY`, `SearchPipeline.identity_check`/`_identity_state`, warn/mark/degrade policy on all four exits, query-role embeds
- `src/sif/cli/commands/search.py` - `_current_identity`/`_dimension_refusal`, query identity closure + `IdentityDimensionError` handler, vsearch check/warn/mark/refuse and `manager.embed_query`, BM25 silent-path comment
- `src/sif/search/expansion.py` - role-helper query and candidate legs with response-shape normalization
- `src/sif/cli/commands/bench.py` - `BenchHarness.identity_check`, `CachedEmbedder` role methods with `(role, text)` memo, `_search_identity_check` refusal/warn
- `src/sif/cli/commands/eval.py` - `_load_embedder` returns the full identity, `_search_identity_check`, hoisted pipeline closure, refusal before the evaluation loop
- `src/sif/mcp/backend.py` - `hybrid_search` identity closure over `self._identity`
- `tests/unit/search/test_hybrid.py` - pipeline identity policy, role recording, dimension degradation/refusal, assumed-match silence
- `tests/unit/cli/test_search.py` - vsearch policy, query closure, end-to-end same-dimension swap with one warning and all-marked JSON rows
- `tests/unit/cli/test_bench.py` - CachedEmbedder role memo/delegation, bench refusal/warn
- `tests/unit/cli/test_eval.py` - eval closure, refusal, warn-without-blocking
- `tests/unit/inference/test_query_expander.py` - role-capable manager double and MagicMock fallback
- `tests/unit/mcp/test_backend.py` - MCP same-dimension marks, width-mismatch BM25 degradation, no-closure path

## Decisions Made

- The pipeline caches one `IdentityCheck` per instance and evaluates the injected closure lazily; the BM25 exit returns before the call so a lexical command never constructs or evaluates one.
- On a hybrid width mismatch the pipeline routes each query variant through `BM25Searcher.search` instead of `HybridSearcher.search`; the downstream fusion/rerank/paginate/enrich code is shared, so the degraded page is shaped exactly like a normal one and every row is marked.
- The search-mode dimension wording (`search_dimension_error`, `SEARCH_DIMENSION_REMEDY`) lives in `hybrid.py` so the pipeline and the CLI hosts share it without editing `identity.py`, which is outside this plan's declared file scope.
- Hosts only run the identity policy when the manager returns a real `EmbedderIdentity`; this keeps injected manager doubles coherent and mirrors `build_identity`'s defensive model reads.
- `CachedEmbedder` calls batch role APIs with one-element lists to keep the `(role, text)` memo honest while still delegating to the model's own role methods.
- `expansion.py` accepts both an `EmbeddingResponse` and a bare vector list, preserving the manager API and the protocol-double fallback.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated 39 pre-existing vsearch manager mocks to configure `embed_query`**
- **Found during:** Task 1 (vsearch query-role switch)
- **Issue:** The vsearch query leg moved from `embed_single` to `embed_query`; every existing CLI test scaffold configured only `embed_single`, so the mock returned a `MagicMock` vector and the embedder-error cases silently changed exit codes.
- **Fix:** Added a matching `embed_query.return_value` beside every `embed_single.return_value` test fixture and moved the vsearch error-path `side_effect` onto `embed_query`.
- **Files modified:** `tests/unit/cli/test_search.py`
- **Verification:** `pytest tests/unit/cli/test_search.py` — 182 pre-existing + 6 new tests pass.
- **Committed in:** `47c51f9` (Task 1 commit)

**2. [Rule 2 - Missing Critical] Refuse to fabricate an identity from an injected manager double**
- **Found during:** Task 1 (vsearch/query wiring) and Task 2 (bench/eval)
- **Issue:** Calling `check_identity` with a `MagicMock` manager's fabricated `get_identity()` value and a mocked connection crashes inside the schema width read, which would make every existing CLI test scaffold fail for the wrong reason and could hide a real manager misconfiguration behind a test-only error.
- **Fix:** Each host only builds/closes over the identity when `manager.get_identity()` returns a real `EmbedderIdentity`; a real `EmbeddingManager` always does.
- **Files modified:** `src/sif/cli/commands/search.py`, `src/sif/cli/commands/bench.py`, `src/sif/cli/commands/eval.py`
- **Verification:** Existing bench/eval/search suites stay green; new tests exercise both the real-identity and no-identity paths.
- **Committed in:** `47c51f9` (Task 1) and `c9386e7` (Task 2)

**3. [Rule 2 - Missing Critical] Keep the role memo correct for batch-only role APIs**
- **Found during:** Task 2 (CachedEmbedder role methods)
- **Issue:** A naive delegation of `embed_documents` to the inner batch method called it with a single string, iterating characters; the `(role, text)` memo would also have been bypassed.
- **Fix:** `_inner_role_call` uses the single-text `embed_query` when available and otherwise calls the batch method with a one-element list, so each `(role, text)` key still maps to exactly one inner call.
- **Files modified:** `src/sif/cli/commands/bench.py`
- **Verification:** `TestCachedEmbedderRoles` proves query/document/plain of the same text are three inner calls and repeats are memo hits.
- **Committed in:** `c9386e7` (Task 2 commit)

**4. [Rule 2 - Missing Critical] Normalize the expansion candidate response shape**
- **Found during:** Task 2 (expansion role legs)
- **Issue:** `EmbeddingManager.embed_queries` returns an `EmbeddingResponse` while the protocol-typed helper fallback returns a bare list; reading `.embeddings` unconditionally would break the documented fallback.
- **Fix:** `getattr(candidate_response, "embeddings", candidate_response)` before iterating, keeping candidate ordering and the existing exception handling unchanged.
- **Files modified:** `src/sif/search/expansion.py`
- **Verification:** `TestQueryExpansionRoles` covers both the role-manager and MagicMock fallback paths.
- **Committed in:** `c9386e7` (Task 2 commit)

---

**Total deviations:** 4 auto-fixed (1 blocking, 3 missing-critical hardening)
**Impact on plan:** No scope creep — no new result field, schema, protocol, or output shape. All fixes were necessary to keep the role switch and identity policy correct across real managers and injected doubles.

## Issues Encountered

- Two `ruff format` passes and one `ruff --fix` (B009 + E501) follow-up were needed after the new bench/eval/test code landed; no behavioral issue.
- A pre-existing MCP suggestion fixture had no `document_chunks` rows, so the new identity tests had to seed a chunk per document before writing a `vec0` embedding (metadata columns reject NULL).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- EMB-01/EMB-02 now have user-visible, agent-visible enforcement at every vector-touching boundary; 21-05's streaming embed and 21-06/21-07 maintenance commands can reuse `check_identity(mode="embed")` and `certify_identity` without new policy.
- The only remaining identity surface is Phase 22's lazy MCP embedder path, which consumes `SearchBackend._identity` and the same `search_dimension_error` helper.
- Full suite: 2670 passed, 1 skipped at 95.36% coverage (fail_under=90); ruff check/format and `ty check src/sif` green.

## Known Stubs

None.

## Self-Check: PASSED

- `21-04-SUMMARY.md` exists in the phase directory
- Task commits `47c51f9` and `c9386e7` are ancestors of HEAD
- All six modified source files exist and pass ruff/format/ty

---
*Phase: 21-scale-maintenance-embedder-identity*
*Completed: 2026-11-16*
