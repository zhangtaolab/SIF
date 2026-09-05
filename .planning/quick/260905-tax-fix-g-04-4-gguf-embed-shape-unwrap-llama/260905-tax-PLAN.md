---
phase: 260905-tax-fix-g-04-4-gguf-embed-shape-unwrap
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/sif/embedding/embedder.py
  - tests/unit/embedding/test_embedder_impl.py
autonomous: true
requirements: [G-04-4]
estimate:
  tokens: 45000
  raw_tokens: 28000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - "LlamaCppEmbedder.embed returns a FLAT list[float] for every llama_cpp 0.3.20 return shape reachable from a single-string embed call: flat list[float] (pooled models), list[list[float]] (token-level output when pooling_type is NONE — decoder-only GGUFs like Qwen2.5-0.5B-Instruct — mean-pooled over axis 0), and defensively list[list[list[float]]] (fully-wrapped token-level). Every element of the returned list is a built-in float, never a nested list, so EmbeddingResponse.embeddings (pydantic list[list[float]]) validates and `sif index embed` with a GGUF embedder persists chunks instead of reporting 'Embedding complete: 0 chunks embedded' (G-04-4)"
    - "The output stays L2-normalized under the existing contract: unit norm when norm > 0; a zero-norm vector is returned unchanged (existing test_embed_zero_norm keeps passing untouched)"
    - "Public API surface is unchanged: embed(text: str) -> list[float] and embed_batch(texts: list[str]) -> list[list[float]] keep their exact signatures; embed_batch still loops embed, and each row it returns is a flat list of floats"
    - "Malformed or empty model output fails fast with ValueError naming the offending shape (no silent fallback, per the project's D-03 fail-fast philosophy): outer axis != 1 on a 3-D payload, ndim 0 or > 3, and empty payloads (zero rows or zero-length vectors, caught by a single arr.size == 0 check) all raise instead of returning garbage or []"
    - "Model loading is untouched: __init__ and the Llama construction kwargs (embedding=True, n_ctx, n_threads, n_gpu_layers, verbose) are byte-identical; no other embedder class changes"
    - "Full quality suite green: ruff check src tests; ruff format --check src tests; env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q — zero failures (baseline 632 collected after the httpx env repair, expect 639 with the 7 new tests)"
  artifacts:
    - "src/sif/embedding/embedder.py — LlamaCppEmbedder.embed rewritten shape-first (unwrap/mean-pool, then L2-normalize) with a private static helper keeping mccabe under 10; fully type-annotated per strict mode; no other class modified"
    - "tests/unit/embedding/test_embedder_impl.py — 7 new test methods inside the existing TestLlamaCppEmbedder class (reusing its _make_module mock scaffold): token-level mean-pool + unit norm + float elements, wrapped-pooled unwrap, fully-wrapped token-level unwrap, call passthrough preserved, empty payload raises, malformed 3-D raises, embed_batch rows are flat float lists"
  key_links:
    - "llama_cpp.Llama.embed (string input, ends `output = data[0] if isinstance(input, str) else data`: pooled -> flat list[float]; pooling NONE -> list[list[float]] per-token vectors) -> LlamaCppEmbedder._unwrap helper -> L2 normalize -> .tolist() -> embed_batch rows -> indexer embed path -> EmbeddingResponse.embeddings pydantic list[list[float]] validation -> sqlite-vec persistence (the link that broke: nested rows rejected by float_type validation, 0 chunks persisted)"
---

<objective>
Fix UAT gap G-04-4 (04-UAT.md, severity blocker, test 3): `sif index embed` with a GGUF embedder (Qwen2.5-0.5B-Instruct q4_k_m, llama-cpp-python 0.3.20) reports "Embedding complete: 0 chunks embedded" — GGUF embeddings have never been persistable.

Purpose: UAT test 3 (HyDE end-to-end with a generation-capable model, SC 2) is blocked on this even after the G-04-3 create_completion fix: HyDE's e2e rerun needs a re-embedded GGUF scratch index, and every embed currently fails pydantic validation. Root cause (verified, recorded in 04-UAT.md Gaps G-04-4 — do not re-diagnose): `LlamaCppEmbedder.embed` (src/sif/embedding/embedder.py lines 162-169) treats `self.model.embed(text)` as a flat vector, but it returns a list-of-embeddings structure. Confirmed against the installed llama_cpp 0.3.20 source (llama.py): `Llama.embed` builds `data: List[List[float]] | List[List[List[float]]]` (per-text pooled vector, or per-token vectors when pooling_type is NONE) and ends with `output = data[0] if isinstance(input, str) else data` — so for the single-string call embed() makes, a pooled model returns flat `list[float]` (works today by luck), while a decoder-only GGUF with no pooling layer (Qwen2.5-0.5B-Instruct) returns `list[list[float]]` of per-token vectors. np division broadcasts over the 2-D array preserving nesting, `.tolist()` returns `[[...], ...]`, and EmbeddingResponse (embeddings: list[list[float]]) rejects every per-text value one level too deep; the embed CLI swallows the per-collection exception leaving 0 chunks.

Output: shape-aware `LlamaCppEmbedder.embed` that unwraps/pools FIRST and L2-normalizes the flat vector second; unit tests with stubbed llama_cpp returns covering all shapes, normalization, and failure cases; full quality suite green.

</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@/Users/forrest/GitHub/SIF/CLAUDE.md
@/Users/forrest/GitHub/SIF/.planning/phases/04-advanced-search-pipeline/04-UAT.md
@/Users/forrest/GitHub/SIF/src/sif/embedding/embedder.py
@/Users/forrest/GitHub/SIF/tests/unit/embedding/test_embedder_impl.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Shape-aware LlamaCppEmbedder.embed (unwrap, mean-pool, then normalize) + regression tests</name>
  <files>src/sif/embedding/embedder.py, tests/unit/embedding/test_embedder_impl.py</files>
  <behavior>
    - Test 1 (token-level shape, the G-04-4 bug): mocked `model.embed` returns `[[3.0, 4.0], [6.0, 8.0]]` (per-token vectors, pooling NONE); `embedder.embed("hello")` returns a length-2 list where every element is a built-in `float` (assert `all(isinstance(v, float) for v in result)` — the exact pydantic float_type failure), equal to `[0.6, 0.8]` within 1e-6 (mean [4.5, 6.0], norm 7.5), and unit-norm (`abs(math.sqrt(sum(v*v for v in result)) - 1.0) < 1e-6`).
    - Test 2 (wrapped pooled shape): mocked return `[[3.0, 4.0, 0.0]]`; result is `[0.6, 0.8, 0.0]` within 1e-6 — mean over a single row is that row exactly.
    - Test 3 (fully-wrapped token-level, defensive): mocked return `[[[3.0, 4.0], [6.0, 8.0]]]`; result is `[0.6, 0.8]` within 1e-6.
    - Test 4 (call passthrough preserved): after Test 1's call, `mock_model.embed.assert_called_once_with("hello")` — the underlying call signature is unchanged.
    - Test 5 (empty payload raises): mocked return `[]` and, in a second test method, `[[]]` — both raise ValueError (pytest.raises with a match on a message naming the shape or emptiness).
    - Test 6 (malformed 3-D raises): mocked return `[[[1.0, 2.0]], [[3.0, 4.0]]]` (outer axis of 2 for a single text) raises ValueError.
    - Test 7 (embed_batch rows are flat, the persistence-path regression): `mock_model.embed.side_effect` of two token-level payloads; every row of `embedder.embed_batch(["a", "b"])` is a list whose elements are all `float` and no row contains a nested list.
    - Existing tests test_embed_single (flat np.array), test_embed_zero_norm, and test_embed_batch keep passing unchanged — they are the back-compat contract.
  </behavior>
  <action>
    RED first: add the seven tests above as new methods inside the existing `TestLlamaCppEmbedder` class in tests/unit/embedding/test_embedder_impl.py, following the established scaffold exactly as `test_embed_single` does — `mock_model = MagicMock()` with `mock_model.n_embd.return_value` set, `self._make_module(mock_model)` for the module dict, `patch.dict("sys.modules", modules)` plus `patch("os.cpu_count", return_value=4)` around construction, then assertions on the constructed embedder outside the patch context. Use plain nested Python lists for the mocked embed return values (that is what real llama_cpp returns); no new imports are needed (MagicMock, patch, pytest, math are already imported). One-line docstrings citing G-04-4, `-> None` annotations, line length 100. Run them — Tests 1-3 and 7 must fail against current code (current embed returns nested lists / fails the isinstance-float assertion) while the ValueError tests may coincidentally fail differently (e.g. numpy ragged/shape errors) — that is acceptable RED evidence.

    GREEN: rewrite `LlamaCppEmbedder.embed` in src/sif/embedding/embedder.py, shape FIRST then normalization, delegating shape handling to a new private static helper on the class (placed next to embed, mirroring the existing `OpenAIEmbedder._normalize` staticmethod convention), fully type-annotated per strict mode, line length 100, mccabe under 10 per branch-distribution:
    - Helper `_unwrap_embedding(raw: Any) -> np.ndarray` (Any is already imported from typing): convert with `np.asarray(raw, dtype=float)` — a ragged payload raises there naturally, which is acceptable fail-fast; if `arr.size == 0` raise ValueError naming the payload as empty (covers zero rows and zero-length vectors in every nesting); if `arr.ndim == 1` return it as-is (flat back-compat: pooled llama_cpp string returns and the existing mocked tests); if `arr.ndim == 2` return `arr.mean(axis=0)` — token-level (T, D) mean-pools the token axis, and a wrapped pooled (1, D) mean-pools to exactly itself (sum of one element divided by 1 is exact), so one rule covers both; if `arr.ndim == 3` require `arr.shape[0] == 1` (single input text — anything else raises ValueError naming the shape), take `arr[0]`, then return its `mean(axis=0)` (version-dependent fully-wrapped token-level); any other ndim (0 or > 3) raises ValueError naming the observed ndim.
    - `embed` becomes: `vector = self._unwrap_embedding(self.model.embed(text))`, then the existing L2 block against the 1-D array — `norm = np.linalg.norm(vector)`, divide when `norm > 0`, return `.tolist()` — preserving the zero-norm-returned-unchanged contract.
    - Update embed's docstring to state the unwrapping contract (flat result regardless of llama_cpp pooled/token-level return shape; unit-length when norm > 0).
    - Leave `embed_batch`, `create_completion`, `__init__`, the Llama construction kwargs, and every other embedder class exactly as they are. embed_batch already loops embed, so it inherits the fix with no code change. Per G-04-4 missing items 1 and 2.
  </action>
  <verify>
    <automated>env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/embedding/test_embedder_impl.py -q</automated>
  </verify>
  <done>All seven new tests pass alongside the pre-existing tests in the file (baseline 42 passed, expect 49): token-level and wrapped inputs produce flat unit-norm float lists matching the expected values, empty and malformed payloads raise ValueError, the underlying embed call still receives the bare string, and embed_batch returns flat float rows. git diff for src/sif/embedding/embedder.py shows changes confined to LlamaCppEmbedder (embed rewrite + new helper).</done>
</task>

<task type="auto">
  <name>Task 2: Full quality suite gate</name>
  <files>src/sif/embedding/embedder.py, tests/unit/embedding/test_embedder_impl.py</files>
  <precondition>The .venv can collect the two MCP test files (tests/unit/mcp/test_integration.py, test_transports_http.py) — they need httpx for starlette's TestClient. httpx was installed into .venv during planning after collection errors from env drift; if it is missing again, run `.venv/bin/python -m pip install httpx` (environmental repair, not a code change) rather than treating the 2 collection errors as a regression.</precondition>
  <action>
    Run the full CLAUDE.md quality suite and fix any fallout confined to the two files this plan touched — ruff line-length/format violations in the rewritten embed and new tests, missing type annotations (disallow_untyped_defs), import-order issues, or mccabe complexity over 10 in the helper. Use the FORCE_COLOR-unset pytest invocation: rich emits ANSI when forced and breaks plain-output assertions in this harness (pre-existing, environmental). Behavior changes and edits to files outside this plan's scope are out of scope. Confirm via `git diff --stat` that exactly the two intended files changed versus the plan's starting commit.
  </action>
  <verify>
    <automated>ruff check src tests && ruff format --check src tests && env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q</automated>
  </verify>
  <done>ruff check and ruff format --check are clean over src and tests; the full suite passes with zero failures (632 collected at baseline after the httpx env repair, expect 639 with the 7 new tests); `git diff --stat` lists exactly src/sif/embedding/embedder.py and tests/unit/embedding/test_embedder_impl.py.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| local GGUF model output -> embedder | Raw llama_cpp embed() output (shapes varying by model pooling type) crosses into SIF's typed list[float] contract |
| note/document text -> model -> persisted vectors | Embedded content ultimately lands in the local sqlite-vec store |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-260905t-01 | Tampering | LlamaCppEmbedder._unwrap_embedding | medium | mitigate | A malformed or unexpectedly-shaped model output (wrong outer cardinality, ndim 0 or > 3, empty payload) raises ValueError naming the shape instead of silently coercing to a wrong-dimension vector that would corrupt the sqlite-vec index; ragged payloads fail at np.asarray conversion |
| T-260905t-02 | Information Disclosure | embed/embed_batch return path | low | accept | Single-user local tool: embeddings stay in-process and in the local SQLite store; the rewrite adds no logging of text or vectors, consistent with the existing methods |
</threat_model>

<verification>
1. Task-level automated checks pass (see each task's verify).
2. Full suite: `ruff check src tests && ruff format --check src tests && env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q` — zero failures, zero lint violations (expect 639 collected: 632 baseline + 7 new).
3. Scope check: `git diff --stat` against the plan's starting commit lists only src/sif/embedding/embedder.py and tests/unit/embedding/test_embedder_impl.py; within embedder.py the diff is confined to LlamaCppEmbedder (embed rewrite + new static helper + docstring); `__init__` and the Llama construction kwargs are byte-identical; embed_batch and create_completion bodies unchanged.
4. Contract isolation: `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/embedding/test_embedder_impl.py -q -k "LlamaCpp"` runs the whole LlamaCppEmbedder suite including the pre-existing flat/zero-norm/batch tests that pin back-compat.
5. UAT re-verification (out of scope for this quick plan, done via /gsd-verify-work 04 resume at test 3): re-embed the GGUF scratch index (896-dim, Qwen2.5-0.5B-Instruct q4_k_m cached at ~/.cache/modelscope) with `sif index embed` — chunks persist with nonzero count — then run `sif search query hyde: <question>` end-to-end; then flip G-04-4 to resolved in 04-UAT.md.
</verification>

<success_criteria>
- G-04-4 missing item 1 delivered: LlamaCppEmbedder.embed is shape-aware — it unwraps llama_cpp's list-of-embeddings return (element selection for wrapped payloads, mean-pooling over axis 0 for token-level output) BEFORE L2-normalizing, returns a flat list[float] for pooled, token-level, and fully-wrapped payloads, raises ValueError on empty or malformed shapes, and preserves the unit-norm-when-norm>0 and zero-norm-unchanged contracts with unchanged public signatures.
- G-04-4 missing item 2 delivered: unit tests with stubbed llama_cpp returns cover both shapes named in the gap (pooled-wrapped and token-level) plus the flat back-compat path, normalization, the empty case, and the embed_batch flat-row persistence contract.
- No drift outside scope: model loading, other embedder classes, and the indexer are untouched; the full quality suite is green.
</success_criteria>

<output>
Create `.planning/quick/260905-tax-fix-g-04-4-gguf-embed-shape-unwrap-llama/260905-tax-SUMMARY.md` when done
</output>
