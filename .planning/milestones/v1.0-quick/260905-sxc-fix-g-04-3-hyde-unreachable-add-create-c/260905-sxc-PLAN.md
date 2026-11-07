---
phase: 260905-sxc-fix-g-04-3-hyde-unreachable
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/sif/embedding/embedder.py
  - tests/unit/embedding/test_embedder_impl.py
autonomous: true
requirements: [G-04-3]
estimate:
  tokens: 45000
  raw_tokens: 30000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - "A constructed LlamaCppEmbedder satisfies hasattr(embedder, 'create_completion') — the exact capability gate SearchPipeline._generate_hypothetical_document checks — so `hyde:` queries with a GGUF embedder no longer raise RuntimeError('HyDE search requires a text-generation-capable model (e.g., GGUF)...') before generating anything (G-04-3)"
    - "create_completion(prompt, max_tokens=256, temperature=0.3, stop=None) delegates to the llama_cpp Llama instance stored as self.model, forwarding prompt positionally and max_tokens/temperature/stop as kwargs; stop=None normalizes to [] (llama-cpp-python 0.3.20's own default for that parameter)"
    - "The openai-style dict from llama_cpp propagates unchanged through the wrapper — the exact shape the HyDE call site consumes as result['choices'][0]['text'].strip()"
    - "Model loading is untouched: Llama() is still constructed exactly once in __init__ with embedding=True and the same n_ctx/n_threads/n_gpu_layers/verbose kwargs; src/sif/search/hybrid.py is unchanged by this plan"
    - "Full quality suite green: ruff check src tests; ruff format --check src tests; env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q — 0 failures (baseline 628 collected, expect 632 with the 4 new tests)"
  artifacts:
    - "src/sif/embedding/embedder.py — LlamaCppEmbedder.create_completion added to the class, fully type-annotated (strict mode), no other class modified"
    - "tests/unit/embedding/test_embedder_impl.py — 4 new test methods inside the existing TestLlamaCppEmbedder class (it already provides the _make_module mock scaffold), covering kwarg forwarding, defaults + stop normalization, return-shape propagation, and the HyDE hasattr gate"
  key_links:
    - "SearchPipeline._generate_hypothetical_document hasattr(embedder, 'create_completion') gate (src/sif/search/hybrid.py ~line 334) -> LlamaCppEmbedder.create_completion (src/sif/embedding/embedder.py) -> self.model.create_completion (llama_cpp.Llama) -> {'choices': [{'text': ...}]} returned to hybrid.py ~line 338"
---

<objective>
Fix UAT gap G-04-3 (04-UAT.md, severity blocker, test 3): every `hyde:` query raises RuntimeError before generating anything because no shipped embedder class implements the generation API the HyDE pipeline gates on.

Purpose: UAT test 3 (HyDE end-to-end with a generation-capable model, SC 2) is blocked on this. Root cause (verified, recorded in 04-UAT.md Gaps G-04-3 — do not re-diagnose): `SearchPipeline._generate_hypothetical_document` (src/sif/search/hybrid.py ~lines 315-350) gates on `hasattr(self.hybrid.embedder, "generate")` then `hasattr(self.hybrid.embedder, "create_completion")`, but LlamaCppEmbedder (src/sif/embedding/embedder.py, class starts ~line 113) — the only GGUF embedder, the one the feature targets — implements only `__init__`/`embed`/`embed_batch`/`dimension`. The generation method was specified in the HyDE design but never wired into the embedder. llama-cpp-python 0.3.20 is installed and its `Llama` class natively provides `create_completion(prompt, max_tokens=..., temperature=..., stop=..., ...)` returning the openai-style `{"choices": [{"text": ...}, ...]}` dict the call site already consumes — so the fix is a thin delegation wrapper, and the call site in hybrid.py is already correct and stays untouched.

Output: `LlamaCppEmbedder.create_completion` delegating to the underlying `self.model` Llama instance; 4 unit tests proving the wrapper contract and the HyDE capability gate; full quality suite green.

</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@/Users/forrest/GitHub/SIF/CLAUDE.md
@/Users/forrest/GitHub/SIF/.planning/phases/04-advanced-search-pipeline/04-UAT.md
@/Users/forrest/GitHub/SIF/src/sif/embedding/embedder.py
@/Users/forrest/GitHub/SIF/src/sif/search/hybrid.py
@/Users/forrest/GitHub/SIF/tests/unit/embedding/test_embedder_impl.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: LlamaCppEmbedder.create_completion delegation wrapper + contract tests</name>
  <files>src/sif/embedding/embedder.py, tests/unit/embedding/test_embedder_impl.py</files>
  <behavior>
    - Test 1 (prompt passthrough + kwarg forwarding): construct LlamaCppEmbedder against a mocked llama_cpp module (existing `_make_module` pattern: `patch.dict("sys.modules", {"llama_cpp": mock_module})` plus `patch("os.cpu_count", return_value=4)`); call `embedder.create_completion("Answer the question", max_tokens=128, temperature=0.7, stop=["\n\n"])`; assert the mock Llama instance's `create_completion` was called exactly once with the prompt positional and those three kwargs (`mock_model.create_completion.assert_called_once_with("Answer the question", max_tokens=128, temperature=0.7, stop=["\n\n"])`).
    - Test 2 (defaults + stop normalization): call `embedder.create_completion("p")` with no kwargs; assert the underlying call received `max_tokens=256, temperature=0.3, stop=[]` — None normalized to llama-cpp-python 0.3.20's own default for that parameter.
    - Test 3 (return shape propagation): underlying returns `{"choices": [{"text": "hypothetical doc"}], "id": "cmpl-1"}`; the wrapper returns that dict unchanged (same value, subscriptable exactly as the HyDE call site consumes it: `result["choices"][0]["text"].strip()`).
    - Test 4 (HyDE capability gate, the G-04-3 regression): on a constructed LlamaCppEmbedder, `hasattr(embedder, "create_completion")` is True — the exact gate `_generate_hypothetical_document` checks; before the fix this failed for every shipped embedder class.
  </behavior>
  <action>
    RED first: add the four tests above as new methods inside the existing `TestLlamaCppEmbedder` class in tests/unit/embedding/test_embedder_impl.py (the class already provides `_make_module(mock_instance)` returning the sys.modules patch dict and the Llama constructor mock — reuse it exactly as `test_embed_single` does; set `mock_model.n_embd.return_value = 512` and the `create_completion` return value on the instance mock). Plain pytest style with one-line docstrings citing G-04-3, type-annotated `-> None`, no new imports beyond what the file already has (MagicMock, patch, and the class import are present). Run them — they must fail (AttributeError: no create_completion) before the implementation exists.
    GREEN: in src/sif/embedding/embedder.py, add a `create_completion` method to `LlamaCppEmbedder` only, placed after `embed_batch` and before the `dimension` property, fully type-annotated per strict mode (line length 100):
    - Signature: `def create_completion(self, prompt: str, max_tokens: int = 256, temperature: float = 0.3, stop: list[str] | None = None) -> dict[str, Any]:` — `Any` is already imported in the file's typing import; defaults mirror the HyDE call site's values (hybrid.py calls with max_tokens=256, temperature=0.3, stop=["\n\n"]).
    - Body: delegate to `self.model.create_completion(prompt, max_tokens=max_tokens, temperature=temperature, stop=stop if stop is not None else [])` and return its result as-is — llama-cpp-python 0.3.20 returns the openai-style dict the call site already consumes, so no reshaping. The stop normalization matches the underlying library's own default (`stop: Optional[Union[str, List[str]]] = []`).
    - Include a docstring stating this is the text-generation capability HyDE gates on via hasattr. Follow `embed`'s convention for the not-loaded case: `embed` performs no guard because `self.model` is assigned unconditionally in `__init__` (construction itself raises ImportError when llama_cpp is missing) — so direct delegation with no invented guard is the consistent behavior.
    - Do not change `__init__`, the Llama construction kwargs (embedding=True, verbose, n_ctx, n_threads, n_gpu_layers stay exactly as they are), or any other embedder class. The `Embedder` Protocol in src/sif/core/models.py declares no generation method — capability is discovered dynamically via hasattr at the call site, so adding the concrete method to LlamaCppEmbedder alone is the correct shape; do not add it to the Protocol. Per G-04-3 missing item 1.
  </action>
  <verify>
    <automated>env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/embedding/test_embedder_impl.py -q</automated>
  </verify>
  <done>All four new tests pass alongside the pre-existing tests in the file: kwargs forwarded verbatim with prompt positional, defaults are max_tokens=256/temperature=0.3/stop=[], the openai-style dict propagates unchanged, and hasattr(embedder, 'create_completion') is True. git diff for src/sif/embedding/embedder.py shows only the added method inside LlamaCppEmbedder.</done>
</task>

<task type="auto">
  <name>Task 2: Full quality suite gate</name>
  <files>src/sif/embedding/embedder.py, tests/unit/embedding/test_embedder_impl.py</files>
  <action>
    Run the full CLAUDE.md quality suite and fix any fallout confined to the two files this plan touched — ruff line-length/format violations in the new method and tests, missing type annotations (disallow_untyped_defs), import-order issues, or mccabe complexity. Use the FORCE_COLOR-unset pytest invocation: rich emits ANSI when forced and breaks plain-output assertions in this harness (pre-existing, environmental). Behavior changes and edits to files outside this plan's scope are out of scope. Confirm via `git diff --stat` that exactly the two intended files changed versus the plan's starting commit.
  </action>
  <verify>
    <automated>ruff check src tests && ruff format --check src tests && env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q</automated>
  </verify>
  <done>ruff check and ruff format --check are clean over src and tests; the full suite passes with zero failures (baseline 628 collected before this plan, expect 632 with the 4 new tests); `git diff --stat` lists exactly src/sif/embedding/embedder.py and tests/unit/embedding/test_embedder_impl.py.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| user query -> HyDE prompt -> local GGUF model | User-controlled query text is embedded in the generation prompt built by hybrid.py and sent to the locally-loaded model |
| model completion text -> embedding + search | Model-generated completion text flows back into the pipeline, is embedded, and feeds vector search |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-260905s-01 | Tampering | LlamaCppEmbedder.create_completion | low | mitigate | Generation length is capped by the max_tokens default of 256 and runaway output is bounded by stop sequences the call site always passes (["\n\n"]); the wrapper adds no new parsing of completion text, so no new injection surface beyond what hybrid.py already handles |
| T-260905s-02 | Information Disclosure | create_completion return path | low | accept | Single-user local tool: completion text stays in-process (embedded and searched locally); the wrapper returns the library's dict as-is with no logging of prompt or output, consistent with the existing embed methods |
</threat_model>

<verification>
1. Task-level automated checks pass (see each task's verify).
2. Full suite: `ruff check src tests && ruff format --check src tests && env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q` — zero failures, zero lint violations.
3. Scope check: `git diff --stat` against the plan's starting commit lists only src/sif/embedding/embedder.py and tests/unit/embedding/test_embedder_impl.py; the diff in embedder.py is a single added method inside LlamaCppEmbedder; the Llama construction in `__init__` is byte-identical.
4. Contract check without a real model: `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/embedding/test_embedder_impl.py -q -k "create_completion or completion"` isolates the new wrapper contract tests.
5. UAT re-verification (out of scope for this quick plan, done via /gsd-verify-work 04 resume at test 3): with a generation-capable GGUF embedder configured, `sif search query hyde: <question>` generates a hypothetical document, embeds it, vector-searches without RuntimeError, and populates the snippet; then flip G-04-3 to resolved in 04-UAT.md.
</verification>

<success_criteria>
- G-04-3 missing item 1 delivered: LlamaCppEmbedder.create_completion(prompt, max_tokens, temperature, stop) wraps llama_cpp Llama.create_completion, forwards kwargs (stop=None normalized to []), and returns the openai-style {'choices': [{'text': ...}]} shape unchanged — matching the HyDE call site in hybrid.py, which is not modified.
- G-04-3 missing item 2 delivered: unit tests with a stubbed llama_cpp Llama verify the wrapper contract — prompt passthrough, max_tokens/temperature/stop forwarding, return-shape propagation, and hasattr(embedder, 'create_completion') now True (the HyDE gate that previously failed for every shipped embedder).
- No drift in model loading: `__init__` and the Llama construction kwargs are unchanged; no other embedder class or the Embedder Protocol is touched.
- Full quality suite green per CLAUDE.md.
</success_criteria>

<output>
Create `.planning/quick/260905-sxc-fix-g-04-3-hyde-unreachable-add-create-c/260905-sxc-SUMMARY.md` when done
</output>
