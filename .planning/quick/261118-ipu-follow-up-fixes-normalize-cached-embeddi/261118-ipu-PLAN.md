---
phase: quick-261118-ipu
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/sif/embedding/normalize.py
  - src/sif/embedding/embedder.py
  - src/sif/embedding/manager.py
  - tests/unit/embedding/test_manager.py
  - tests/unit/inference/test_reranker.py
autonomous: true
requirements: [QUICK-ISSUES-4-FOLLOWUP]  # quick task: normalize cached embeddings on read (issue #4 gap) + hermetic Qwen3 CPU-load test on GPU hosts
estimate:
  tokens: 24000
  raw_tokens: 24000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - "A cache row written before v1.2.0 (off unit, e.g. norm 1.003596 or 0.9985) is returned by EmbeddingManager as a unit vector within 1e-12, with no re-encode: rerunning `sif index embed` on a populated cache no longer aborts on the `L2 norm ... is not 1.0 within 0.001` gate."
    - "Cached zero vectors pass through the manager unchanged as zeros so StreamingEmbedWriter.validate_batch's zero-norm gate remains reachable; non-finite and wrong-dimension rows remain cache misses and are recomputed as today."
    - "Renormalization on read is idempotent: an already unit cached vector comes back unchanged within float64 rounding, and the embedder's fresh output paths behave exactly as before."
    - "Exactly one L2 normalization implementation exists: sif/embedding/normalize.py:l2_normalize, called by both the sentence-transformers-backed embedder encode paths and the manager's cache-hit path."
    - "NORM_TOLERANCE stays 1e-3, validate_batch is unchanged, and LlamaCppEmbedder, OpenAIEmbedder, and SimpleEmbedder are untouched."
    - "tests/unit/inference/test_reranker.py::TestQwen3Reranker::test_local_load_cpu_quiet_and_already_loaded passes on hosts with a working CUDA device because it pins torch.cuda.is_available to False, while still exercising the constructor's auto device/dtype selection (no explicit device override)."
    - "The full quality suite (ruff check, ruff format --check, pytest) is green."
  artifacts:
    - "src/sif/embedding/normalize.py — shared float64 L2 normalization helper (moved from embedder.py)"
    - "src/sif/embedding/embedder.py — imports the shared helper; the six `_l2_normalize` call sites now call `l2_normalize`"
    - "src/sif/embedding/manager.py — `_lookup_cached` renormalizes usable cache hits before returning them"
    - "tests/unit/embedding/test_manager.py — off-unit cache-hit, zero pass-through, and idempotence regression tests; cache-segmentation test updated for unit vectors"
    - "tests/unit/inference/test_reranker.py — CUDA probe pinned False for the CPU auto-selection test"
  key_links:
    - "SQLite embedding cache row -> EmbeddingManager._lookup_cached -> _is_usable_cached (dimension + finiteness) -> l2_normalize(float64) -> list[float] -> EmbeddingResponse -> StreamingEmbedWriter.validate_batch norm gate"
    - "SentenceTransformerEmbedder/ModelScopeEmbedder encode output -> _encode_with_prompt/embed/embed_batch -> l2_normalize -> validate_batch"
    - "Qwen3Reranker.load torch.cuda.is_available probe -> dtype/device auto-selection -> test patch False -> to('cpu') + torch.float32"
---

<objective>
Close the two verified follow-ups left by commit 5f9c086:

1. Issue #4 stale-cache gap — the embedders now renormalize fresh model output in float64, but `EmbeddingManager._lookup_cached` still returns cached vectors verbatim. Users upgrading with a populated `<cache>/embeddings_cache.db` keep hitting `L2 norm 1.003596 is not 1.0 within 0.001` until they delete the cache. Renormalize cached vectors on read (float64, zero/non-finite pass through unchanged), keeping the storage format and `NORM_TOLERANCE = 1e-3` untouched.

2. GPU-host test failure — `tests/unit/inference/test_reranker.py::TestQwen3Reranker::test_local_load_cpu_quiet_and_already_loaded` assumes the CPU fallback but never pins `torch.cuda.is_available`, so it fails on any CUDA host (`Expected: to('cpu') / Actual: to('cuda')`). Pin the probe to False to keep the test's intent deterministic everywhere.

Also consolidate the L2 helper into one implementation shared by the embedders and the manager, per the task constraints. No research phase.

Purpose: make the issue-#4 fix effective for existing users, and make the suite green on GPU hosts without weakening any validation gate.
Output: 1 new shared module, 2 source files edited, 2 test files changed, one atomic commit. No NORM_TOLERANCE, validate_batch, LlamaCppEmbedder, OpenAIEmbedder, or SimpleEmbedder change.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@src/sif/embedding/embedder.py
@src/sif/embedding/manager.py
@src/sif/indexing/embed_writer.py
@tests/unit/embedding/test_manager.py
@tests/unit/inference/test_reranker.py

Planning-time observations (live, 2026-11-18):

- `_l2_normalize(values: Any) -> np.ndarray` is defined at src/sif/embedding/embedder.py:104 and called at six sites: `SentenceTransformerEmbedder.embed`, `.embed_batch`, `._encode_with_prompt` and the identical three in `ModelScopeEmbedder`. A repo-wide grep finds no other importer — no test, doc, or source file imports the private name — so moving it is compatible.
- `EmbeddingCache.get` returns `json.loads(row["embedding"])`; JSON round-trips float64 doubles exactly, so a cached norm of 1.003596 comes back as 1.003596 and the manager can renormalize deterministically.
- `EmbeddingManager._lookup_cached` currently assigns `embeddings[i] = cached` after `_is_usable_cached` (dimension + finiteness). Both role-aware (`_embed_role`) and role-less (`embed`) request paths go through it, so one edit covers every cache-hit surface.
- `tests/unit/embedding/test_manager.py::TestCacheSafety` is the home for cache-safety regressions; `_RecordingEmbedder(dimension=2)` and `_make_manager(tmp_path, embedder, cache=cache)` are the established fixtures, and `_cache_bucket("document")` returns the bucket to seed.
- `test_cache_is_segmented_by_model` (same file, lines ~85-88) is the only existing test that reads a cache hit back through the manager and asserts exact values `[[0.1, 0.2]]`; it must be updated or it will fail once hits are renormalized.
- `Qwen3Reranker.load()` evaluates `torch_bfloat16 if torch.cuda.is_available() else torch.float32` and `"cuda" if torch.cuda.is_available() else "cpu"` on every load, even for an explicit `device=` argument. The failing test is the only Qwen3 load test that neither passes an explicit device nor patches the probe; the neighboring `test_local_load_nonquiet_explicit_device_ignores_cuda_probe` already establishes the `patch("torch.cuda.is_available", return_value=...)` pattern.
- Full gates run under the frozen uv environment per the task constraints: `uv run --frozen --extra dev --extra embed ...`; there is no prepared `.venv`. pytest addopts enable coverage, so targeted runs pass `--no-cov` while the final full run keeps coverage on (`fail_under = 90`).
- Baseline on this Linux/CUDA host before the fix: 1 failed (`Expected: to('cpu') / Actual: to('cuda')`), 3233 passed. After the fix all tests must pass; do not chase pre-existing skips.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Renormalize cached embeddings on read and share one float64 L2 helper (issue #4 follow-up)</name>
  <files>src/sif/embedding/normalize.py, src/sif/embedding/embedder.py, src/sif/embedding/manager.py, tests/unit/embedding/test_manager.py</files>
  <precondition>None beyond the repo checkout: all tests mock the embedders and use real SQLite caches under tmp_path, so no model weights, GPU, or network access is required.</precondition>
  <action>
    Root cause: commit 5f9c086 renormalizes fresh encoder output but leaves `_lookup_cached` returning raw cache rows, so v1.2.0 cache rows (off unit by up to ~3.6e-3) still trip `StreamingEmbedWriter.validate_batch` and abort `sif index embed`. Fix at the manager's cache-read boundary and keep one shared helper implementation.

    1. Create src/sif/embedding/normalize.py holding the helper moved from src/sif/embedding/embedder.py. Name it `l2_normalize(values: Any) -> np.ndarray` (public name because it now crosses module boundaries; no leading underscore). Keep the existing body and float64 rationale verbatim, then extend the docstring to say it is shared by the sentence-transformers-backed embedder encode paths and by `EmbeddingManager`'s cache-hit path, that already unit vectors are idempotent under it, and that zero or non-finite vectors are divided by 1.0 and returned unchanged so `validate_batch`'s zero-norm and finiteness gates remain reachable. Body: `np.asarray(values, dtype=np.float64)`, per-vector norms via `np.linalg.norm(array, axis=-1, keepdims=True)`, divide by the norm only where `np.isfinite(norms) & (norms > 0.0)`, otherwise by 1.0. Import only `typing.Any` and `numpy as np`.

    2. In src/sif/embedding/embedder.py delete the `_l2_normalize` definition and import `from sif.embedding.normalize import l2_normalize` (first-party block, alphabetically between `sif.embedding.identity` and `sif.models.download`). Replace the six `_l2_normalize(` call sites with `l2_normalize(`. Do not change `_encode_kwargs`, `normalize_embeddings=True`, prompt plumbing, progress-bar rules, `LlamaCppEmbedder`, `OpenAIEmbedder`, or `SimpleEmbedder`.

    3. In src/sif/embedding/manager.py import the same helper and change the cache-hit assignment in `_lookup_cached` from `embeddings[i] = cached` to `embeddings[i] = l2_normalize(cached).tolist()`. Add a short comment: rows cached by v1.2.0 predate embedder-side renormalization, so hits are normalized on read in float64; `_is_usable_cached` still runs first so non-finite and wrong-dimension rows stay misses and are recomputed, while zero vectors are not filtered and pass through unchanged. Do not touch `_is_usable_cached`, `_validate_vector`, `_cache_bucket`, or any cache write path.

    4. In tests/unit/embedding/test_manager.py add `import math` (stdlib block, before `pathlib`). Update `test_cache_is_segmented_by_model`: change the mocked `embed_batch` output from `[[0.1, 0.2]]` to `[[1.0, 0.0]]` and the three response assertions accordingly, keeping exact equality (dividing the exact unit vector [1.0, 0.0] by its exact norm is byte-stable, so this doubles as an idempotence check on the role-less `embed` surface).

    5. Add three regression tests to `TestCacheSafety`, all using `EmbeddingCache(tmp_path)`, `_RecordingEmbedder()`, `_make_manager(tmp_path, embedder, cache=cache)`, and `bucket = manager._cache_bucket("document")`:
       - `test_off_unit_cached_vector_is_renormalized_on_read`, parametrized over norms (1.003596, 0.9985): seed `cache.set("stale text", [0.6 * norm, 0.8 * norm], model_id=bucket)`, call `manager.embed_documents(["stale text"])`, assert `embedder.batch_calls == []` (cache hit, no encode), assert `abs(math.sqrt(sum(v * v for v in vector)) - 1.0) <= 1e-12`, and assert the vector matches `[0.6, 0.8]` with `pytest.approx(..., rel=1e-12, abs=1e-12)`.
       - `test_zero_cached_vector_passes_through_unchanged`: seed `[0.0, 0.0]`, assert the response vector is exactly `[0.0, 0.0]` and `embedder.batch_calls == []`, so the zero-norm branch of `validate_batch` remains reachable.
       - `test_already_unit_cached_vector_is_unchanged`: seed `[0.6, 0.8]`, assert the response matches with `pytest.approx(rel=1e-12, abs=1e-12)` and `embedder.batch_calls == []`, proving read normalization is idempotent for rows written by the fixed embedder.

    Do not change NORM_TOLERANCE, validate_batch, src/sif/indexing/**, or the cache storage format.
  </action>
  <verify>
    <automated>
      uv run --frozen --extra dev --extra embed python -m pytest tests/unit/embedding/test_manager.py tests/unit/embedding/test_embedder_impl.py -q --no-cov
    </automated>
  </verify>
  <done>
    - src/sif/embedding/normalize.py exists and is the only L2 normalization implementation; embedder.py and manager.py both import it
    - Cached vectors with norms 1.003596 and 0.9985 come back unit within 1e-12 with no embedder call
    - Cached zero vectors return unchanged zeros; cached non-finite/wrong-dimension rows remain misses (existing test still passes)
    - Already unit cached vectors return unchanged within float64 rounding
    - The moved helper still satisfies the existing five-path off-unit embedder tests in test_embedder_impl.py
    - NORM_TOLERANCE and validate_batch are untouched; LlamaCppEmbedder, OpenAIEmbedder, and SimpleEmbedder are untouched
  </done>
</task>

<task type="auto">
  <name>Task 2: Pin the CUDA probe in the Qwen3 CPU-load test and run the full quality suite</name>
  <files>tests/unit/inference/test_reranker.py</files>
  <precondition>None: the test mocks transformers and the model, so no weights or network; the host has a working CUDA device, which is the condition being neutralized.</precondition>
  <action>
    Why: `Qwen3Reranker.load()` selects `torch.bfloat16` and `model.to("cuda")` whenever `torch.cuda.is_available()` is true. `test_local_load_cpu_quiet_and_already_loaded` never patches the probe and never passes an explicit device, so on a GPU host it asserts against the wrong branch.

    1. In tests/unit/inference/test_reranker.py, rewrite the existing context manager in `TestQwen3Reranker.test_local_load_cpu_quiet_and_already_loaded` as a parenthesized multi-manager `with` keeping `modules` and `patch("sif.search.rerank.is_quiet", return_value=True)`, and add `patch("torch.cuda.is_available", return_value=False)`. Add one comment stating the probe is pinned False so the constructor's auto-selection deterministically takes the CPU/float32 fallback on GPU hosts. Keep the constructor call without a device argument (`Qwen3Reranker(model_path=..., cache_dir=...)`) and keep both assertions (`model.to.assert_called_once_with("cpu")` and `torch_dtype == torch.float32`) — the test's intent is the auto-selected CPU fallback, not an explicit override.

    2. Do not modify the neighboring `test_local_load_nonquiet_explicit_device_ignores_cuda_probe` (it deliberately patches CUDA True) or `test_mocked_download_and_automatic_cuda_selection`.

    3. Run the full quality suite in CLAUDE.md order under the frozen lock: ruff check src tests, ruff format --check src tests, then the full pytest run. On this GPU host the pre-fix baseline was 1 failed / 3233 passed; after this task the suite must complete with zero failures. Fix only failures caused by this plan; report anything pre-existing instead of changing unrelated code.
  </action>
  <verify>
    <automated>
      uv run --frozen --extra dev --extra embed python -m pytest tests/unit/inference/test_reranker.py -q --no-cov
      uv run --frozen --extra dev --extra embed ruff check src tests
      uv run --frozen --extra dev --extra embed ruff format --check src tests
      uv run --frozen --extra dev --extra embed python -m pytest -q
    </automated>
  </verify>
  <done>
    - test_local_load_cpu_quiet_and_already_loaded patches torch.cuda.is_available to False, keeps the device-less constructor call, and passes on this CUDA host
    - The test still asserts to('cpu') and torch.float32, and the two double-load no-op behavior is unchanged
    - Full suite completes with zero failures under `uv run --frozen --extra dev --extra embed`
    - ruff check and ruff format --check are green
    - No production source file is modified by this task
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| SQLite embedding cache -> process memory | Rows written by other versions of the app cross into vector consumers; they are untrusted relative to the unit-norm invariant |
| encoder output -> persistence | Numeric model output crosses into SQLite vector storage through `validate_batch`, which must still reject zeros and non-finite values |
| host CUDA capability -> test process | A host-dependent branch makes test outcomes machine-dependent unless pinned |
| package indexes -> environment | No packages are added; the locked environment is used unchanged |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-ipu-01 | Tampering / Denial of service | `EmbeddingManager._lookup_cached` renormalization | medium | mitigate | Normalize only after `_is_usable_cached` verifies dimension and finiteness; divide in float64 only where the norm is finite and > 0; zero and non-finite vectors pass through unchanged so `validate_batch`'s gates stay reachable; `NORM_TOLERANCE` and the cache write format are unchanged. |
| T-ipu-02 | Denial of service | `l2_normalize` on hostile cached values | low | accept | Values come from the user's own local cache; an overflowing norm becomes non-finite, the vector passes through unchanged, and the existing writer gate rejects it. No loop, allocation, or code path scales with value magnitude, and reading a row still performs one dimension + finiteness pass. |
| T-ipu-03 | Repudiation | Test determinism on GPU hosts | low | mitigate | The CUDA probe is pinned per-test with `unittest.mock.patch`, matching the neighboring test's existing convention; no global fixture or environment mutation is introduced. |
| T-ipu-SC | Tampering | npm/pip/cargo installs | low | accept | No new package, no version change, and no install command is part of this plan; only source and test files are edited inside the frozen lock. |
</threat_model>

<verification>
1. Task 1: `pytest tests/unit/embedding/test_manager.py tests/unit/embedding/test_embedder_impl.py` is green; off-unit cached vectors (1.003596, 0.9985) return unit length within 1e-12 with zero embedder calls; zero vectors pass through as zeros; unit vectors are unchanged.
2. Task 1: `grep`-level check — `l2_normalize` is defined once (src/sif/embedding/normalize.py) and imported by both embedder.py and manager.py; `_l2_normalize` no longer exists in the tree.
3. Task 2: `pytest tests/unit/inference/test_reranker.py` is green on this CUDA host, including the CPU auto-selection test.
4. Overall: `ruff check src tests`, `ruff format --check src tests`, and the full `pytest` suite are green under `uv run --frozen --extra dev --extra embed`; the prior 1 failed / 3233 passed baseline becomes zero failures.
5. Scope: `git status --porcelain` shows only the five files in this plan's `files_modified` plus `.planning/` artifacts; NORM_TOLERANCE, validate_batch, src/sif/indexing/**, LlamaCppEmbedder, OpenAIEmbedder, and SimpleEmbedder are unmodified.
</verification>

<success_criteria>
- Issue #4 gap closed: existing users with a populated embedding cache get unit vectors on cache hits, so `sif index embed` succeeds without deleting `embeddings_cache.db`; storage format and `NORM_TOLERANCE = 1e-3` are unchanged.
- Safety preserved: zero cached vectors pass through unchanged for `validate_batch` to reject; non-finite and wrong-dimension rows remain misses and are recomputed.
- One implementation: the float64 L2 helper lives once in src/sif/embedding/normalize.py and serves both encoder output and cache reads; existing embedder renormalization tests still pass.
- GPU-host determinism: the Qwen3 CPU-load test pins `torch.cuda.is_available` False while still exercising auto-selection, and passes on this CUDA host.
- Full quality suite (ruff check, ruff format --check, pytest) green and one atomic commit for the plan.
</success_criteria>

<output>
Create `.planning/quick/261118-ipu-follow-up-fixes-normalize-cached-embeddi/261118-ipu-SUMMARY.md` when done
</output>
