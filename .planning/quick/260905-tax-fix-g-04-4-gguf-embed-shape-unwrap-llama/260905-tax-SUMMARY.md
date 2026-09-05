---
phase: quick-260905-tax-fix-g-04-4-gguf-embed-shape-unwrap
plan: 01
subsystem: embedding
tags: [embedding, llama-cpp, gguf, g-04-4, uat-gap, shape-handling]
requires: [G-04-4 open, llama-cpp-python 0.3.20]
provides: [shape-aware LlamaCppEmbedder.embed, flat list[float] GGUF embeddings, fail-fast shape validation]
affects: [src/sif/embedding/embedder.py, tests/unit/embedding/test_embedder_impl.py]
tech-stack:
  added: []
  patterns:
    - "private static _unwrap_embedding helper mirrors OpenAIEmbedder._normalize convention"
    - "shape-first (np.asarray -> ndim dispatch -> mean-pool) then L2-normalize"
key-files:
  created:
    - .planning/quick/260905-tax-fix-g-04-4-gguf-embed-shape-unwrap-llama/deferred-items.md
  modified:
    - src/sif/embedding/embedder.py
    - tests/unit/embedding/test_embedder_impl.py
decisions:
  - "ndim==2 mean-pools over axis 0: one rule covers token-level (T, D) and wrapped pooled (1, D) exactly"
  - "arr.size == 0 is the single emptiness check: covers zero rows and zero-length vectors in every nesting"
  - "Ragged payloads fail naturally at np.asarray conversion (acceptable fail-fast)"
metrics:
  duration: 16min
  completed: 2026-09-05T13:31:00Z
  tasks: 2
  commits: 3
status: complete
estimate:
  tokens: 45000
actuals:
  tokens: 2436
  tasks: 2
  commits: 3
---

# Quick Task 260905-tax: Fix G-04-4 GGUF Embed Shape (unwrap llama_cpp list-of-embeddings) Summary

Shape-aware `LlamaCppEmbedder.embed` that unwraps/mean-pools llama_cpp's list-of-embeddings return (pooled flat, token-level, fully-wrapped) before L2-normalizing, so GGUF embeddings persist as flat `list[float]` instead of failing pydantic validation with "0 chunks embedded".

## What Changed Per Task

### Task 1: Shape-aware LlamaCppEmbedder.embed (TDD) — commits 4560127, 958262b

**RED (4560127)** — 8 new test methods inside `TestLlamaCppEmbedder`
(tests/unit/embedding/test_embedder_impl.py), reusing the existing `_make_module`
mock scaffold:

1. `test_embed_token_level_shape_mean_pools` — `[[3,4],[6,8]]` → flat `[0.6, 0.8]`, all built-in floats, unit norm (the exact G-04-4 pydantic float_type failure)
2. `test_embed_wrapped_pooled_shape` — `[[3,4,0.0]]` → `[0.6, 0.8, 0.0]`
3. `test_embed_fully_wrapped_token_level_shape` — `[[[3,4],[6,8]]]` → `[0.6, 0.8]`
4. `test_embed_call_passthrough_preserved` — `model.embed` still receives the bare string
5. `test_embed_empty_payload_raises` — `[]` raises ValueError
6. `test_embed_empty_vector_payload_raises` — `[[]]` raises ValueError
7. `test_embed_malformed_3d_payload_raises` — outer axis 2 on 3-D raises ValueError
8. `test_embed_batch_rows_are_flat_float_lists` — persistence-path regression

RED evidence: 7 failed, 43 passed (Tests 1-3, 5a/5b, 6, 7 fail; Test 4 pins the unchanged
call signature and passes, as the plan's RED description anticipated for non-shape tests).

**GREEN (958262b)** — `LlamaCppEmbedder.embed` rewritten in src/sif/embedding/embedder.py:
`_unwrap_embedding(raw) -> np.ndarray` private static helper (placed next to `embed`,
mirroring `OpenAIEmbedder._normalize`) converts via `np.asarray(raw, dtype=float)`,
raises ValueError on `arr.size == 0` (single check for all empty nestings), returns 1-D
as-is (back-compat), mean-pools axis 0 for 2-D (token-level AND wrapped-pooled in one
rule), requires `shape[0] == 1` then `arr[0].mean(axis=0)` for 3-D, raises ValueError
naming the ndim otherwise. `embed` then runs the unchanged L2 block (unit norm when
norm > 0; zero-norm returned unchanged) and `.tolist()`.

Untouched per plan: `__init__`, Llama construction kwargs, `embed_batch` body,
`create_completion`, and every other embedder class — confirmed by the committed diff
(confined to `LlamaCppEmbedder`).

Result: tests/unit/embedding/test_embedder_impl.py 50 passed (was 42).
Contract isolation (`-k LlamaCpp`): 21 passed, including the pre-existing
flat/zero-norm/batch back-compat tests.

### Task 2: Full quality suite gate — commit 04f7504 (+ 2 environmental repairs)

- **PLR2004 fallout fixed (04f7504):** ruff flagged magic values `2`/`3` in the ndim
  comparisons; extracted `_NDIM_TOKEN_LEVEL` / `_NDIM_FULLY_WRAPPED_TOKEN_LEVEL` module
  constants (no behavior change).
- **Environmental repair 1 (precondition, no code change):** httpx present (0.28.1);
  both MCP test files collect (22 tests) — precondition met, nothing to do.
- **Environmental repair 2 (deviation, no code change):** `pytest-asyncio` was missing
  from `.venv` (env drift; not declared in pyproject/uv.lock despite committed
  `@pytest.mark.asyncio` tests) — 25 MCP async tests failed with
  `PytestUnknownMarkWarning` / "async def function". Installed `pytest-asyncio` 1.4.0
  into `.venv` via pip, following the Task 2 precondition's sanctioned env-repair
  pattern. Fixed all 25.
- **Committed scope check:** `git diff 30dc4d7 HEAD --stat` lists exactly
  src/sif/embedding/embedder.py (+55/-7) and tests/unit/embedding/test_embedder_impl.py
  (+126). (Working-tree changes to uv.lock/.planning/config.json/mypy.ini predate this
  task and are the user's staged/unstaged state — untouched.)

## Test Results

| Check | Result |
| --- | --- |
| ruff check src tests | All checks passed |
| ruff format --check src tests | 128 files already formatted |
| pytest tests/unit/embedding/test_embedder_impl.py | 50 passed (baseline 42 + 8 new) |
| pytest -k LlamaCpp (contract isolation) | 21 passed |
| Full suite: pytest -q | 640 collected, 627 passed, 11 skipped, **2 failed (pre-existing, see below)** |

The plan predicted 639 collected (632 + 7 new); actual is 640 (632 + 8 new) — see
Deviation 3.

## Commits

| Hash | Type | Content |
| --- | --- | --- |
| 4560127 | test(260905-tax) | Failing tests for llama_cpp embed shape unwrapping (RED) |
| 958262b | feat(260905-tax) | Shape-aware LlamaCppEmbedder.embed (GREEN) |
| 04f7504 | refactor(260905-tax) | Named ndim constants (PLR2004) |

All commits are pathspec-scoped (`git commit -- <files>`); the user's staged `mypy.ini`
deletion remains staged and untouched.

## Deviations from Plan

### 1. [Rule 3 - Environmental] pytest-asyncio restored into .venv

- **Found during:** Task 2 full-suite run — 25 MCP tests failed with unknown `asyncio` mark.
- **Issue:** `.venv` env drift (uv.lock was re-synced) dropped hand-installed test deps.
  `pytest-asyncio` is required by committed tests but undeclared in pyproject/uv.lock.
- **Fix:** `.venv/bin/python -m pip install pytest-asyncio` (1.4.0) — environmental repair
  per the Task 2 precondition's httpx pattern, no code change.
- **Follow-up:** dev test extras should declare `pytest-asyncio` and `httpx`.

### 2. [Scope boundary] 2 pre-existing full-suite failures NOT fixed (out of scope)

- **Found during:** Task 2. `test_import_error_logs_install_hint` and
  `test_corrupt_cache_treated_as_miss` (tests/unit/embedding/test_openai_embedder.py)
  fail with `caplog.text == ''` in the full run.
- **Proof of non-involvement:** the minimal repro `pytest tests/test_docs.py
  tests/unit/embedding/test_openai_embedder.py -q` → 2 failed, 28 passed — none of this
  plan's files in the run; each file passes standalone.
- **Root cause:** `setup_logging()` (src/sif/utils/logging.py ~line 130) permanently sets
  `logging.getLogger("sif").propagate = False`; test_docs.py's in-process CLI calls
  trigger it, so later `sif.*` records never reach caplog's root handler.
- **Action:** logged to `deferred-items.md` (with suggested fix) and WINDOWS.md ledger
  (id 3, kind unmet-truth). Not fixed — plan Task 2 explicitly excludes edits outside
  the two touched files.

### 3. [Count] 8 new test methods instead of the predicted 7

The behavior block's Test 5 explicitly requires the `[[]]` empty payload "in a second
test method", giving 8 methods (Tests 1-4, 5a, 5b, 6, 7) rather than the 7 counted in
must_haves/verification. File count 42+8=50 (predicted 49); full suite 640 (predicted
639). Count-only deviation, no functional difference.

### 4. [Rule 1 - Lint] PLR2004 magic values

Covered by commit 04f7504 above.

## Auth Gates

None.

## Known Stubs

None — no stub patterns introduced; all code paths are real implementations.

## Threat Flags

None beyond the plan's threat model. T-260905t-01 (mitigate) is implemented:
`_unwrap_embedding` raises ValueError naming the shape for empty payloads, outer
axis != 1 on 3-D, and ndim 0 or > 3; ragged payloads fail at `np.asarray` conversion.
T-260905t-02 (accept): no logging of text or vectors added.

## Deferred Issues

See `deferred-items.md` in this directory: the caplog pollution bug (pre-existing) and
the undeclared test-dependency hygiene item (pytest-asyncio/httpx not in dev extras).

## Next Step (out of scope, per plan verification item 5)

`/gsd-verify-work 04` resume at test 3: re-embed the GGUF scratch index (896-dim
Qwen2.5-0.5B-Instruct q4_k_m) with `sif index embed` — chunks should now persist with a
nonzero count — then run `sif search query hyde: <question>` end-to-end, then flip
G-04-4 to resolved in 04-UAT.md.

## Self-Check: PASSED

- src/sif/embedding/embedder.py modified: FOUND
- tests/unit/embedding/test_embedder_impl.py modified: FOUND
- Commit 4560127: FOUND
- Commit 958262b: FOUND
- Commit 04f7504: FOUND
- deferred-items.md: FOUND
