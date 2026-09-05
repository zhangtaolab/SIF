---
phase: 260905-sxc-fix-g-04-3-hyde-unreachable
plan: 01
subsystem: embedding
tags: [hyde, llama-cpp, embedder, uat-gap-fix, g-04-3]
requires:
  - "G-04-3 gap record in 04-UAT.md (root cause already diagnosed)"
  - "llama-cpp-python 0.3.20 installed (Llama.create_completion API)"
provides:
  - "LlamaCppEmbedder.create_completion — the text-generation capability the HyDE pipeline gates on via hasattr"
affects:
  - "src/sif/search/hybrid.py (consumer, NOT modified — call site was already correct)"
tech-stack:
  added: []
  patterns:
    - "thin delegation wrapper over llama_cpp.Llama.create_completion; stop=None normalized to the underlying library's own default ([])"
key-files:
  created: []
  modified:
    - src/sif/embedding/embedder.py
    - tests/unit/embedding/test_embedder_impl.py
decisions:
  - "create_completion added to LlamaCppEmbedder only — NOT to the Embedder Protocol; capability stays dynamically discovered via hasattr at the HyDE call site (per G-04-3 missing item 1)"
  - "No not-loaded guard invented: self.model is assigned unconditionally in __init__ (construction raises ImportError when llama_cpp is missing), matching embed()'s convention"
metrics:
  duration: 3min
  completed: "2026-09-05"
status: complete
actuals:
  tokens: 1300    # chars/4 over the realized diff (5165 chars / 4); estimate was 45000 at confidence:low
  tasks: 2
  commits: 2
---

# Quick Task 260905-sxc: Fix G-04-3 HyDE unreachable — add create_completion to LlamaCppEmbedder Summary

Added the missing text-generation method to `LlamaCppEmbedder`, unblocking `hyde:` queries: a thin `create_completion` wrapper delegating to the underlying llama.cpp `Llama` instance, returning the openai-style completion dict the HyDE call site already consumes.

## What Changed Per Task

### Task 1: LlamaCppEmbedder.create_completion delegation wrapper + contract tests (TDD)

- **RED** (commit `9f079b6`): added 4 test methods inside the existing `TestLlamaCppEmbedder` class in `tests/unit/embedding/test_embedder_impl.py`, reusing the established `_make_module` + `patch("os.cpu_count", return_value=4)` scaffold:
  - `test_create_completion_forwards_prompt_and_kwargs` — prompt positional, `max_tokens`/`temperature`/`stop` kwargs forwarded verbatim (`assert_called_once_with`)
  - `test_create_completion_defaults_and_stop_normalization` — no-kwargs call reaches the Llama instance as `max_tokens=256, temperature=0.3, stop=[]` (None normalized to llama-cpp-python 0.3.20's own default)
  - `test_create_completion_returns_openai_style_dict_unchanged` — the `{"choices": [{"text": ...}]}` dict propagates unchanged and is subscriptable exactly as hybrid.py consumes it (`result["choices"][0]["text"].strip()`)
  - `test_create_completion_satisfies_hyde_capability_gate` — `hasattr(embedder, "create_completion")` is True, the exact G-04-3 regression (failed as `assert False is True` before the fix, reproducing the gate failure every shipped embedder had)
  - All 4 failed before implementation (3 via `AttributeError`, the hasattr test via assertion) — proper RED.
- **GREEN** (commit `67c9ecf`): added `create_completion` to `LlamaCppEmbedder` only in `src/sif/embedding/embedder.py`, placed after `embed_batch` and before the `dimension` property. Signature `create_completion(self, prompt: str, max_tokens: int = 256, temperature: float = 0.3, stop: list[str] | None = None) -> dict[str, Any]` — fully type-annotated, `Any` from the existing typing import. Body delegates to `self.model.create_completion(...)` with `stop if stop is not None else []`, returning the result as-is. `__init__`, the Llama construction kwargs (`embedding=True`, `n_ctx`, `n_threads`, `n_gpu_layers`, `verbose`), and every other class are untouched. Docstring documents the hasattr gate this satisfies.
- **REFACTOR**: not needed — the wrapper is minimal.

### Task 2: Full quality suite gate

No fixes required — the suite was green on first run; no third commit.

- `ruff check src tests` — All checks passed
- `ruff format --check src tests` — 128 files already formatted
- `env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q` — **621 passed, 11 skipped, 0 failed** (632 collected = 628 baseline + 4 new, exactly as planned)

## Test Results

| Scope | Result |
|-------|--------|
| New contract tests (`-k "create_completion or completion"`) | 4 passed |
| Full embedder test file | 42 passed (38 pre-existing + 4 new) |
| Full suite | 621 passed, 11 skipped, 0 failed, 19 warnings |

## Commits

| Hash | Type | Description |
|------|------|-------------|
| `9f079b6` | test | RED — 4 failing contract tests for LlamaCppEmbedder.create_completion |
| `67c9ecf` | feat | GREEN — create_completion delegation wrapper on LlamaCppEmbedder |

Both commits are pathspec-scoped (`git commit <files>`), preserving the user's staged `mypy.ini` deletion in the working index.

## Deviations from Plan

None — plan executed exactly as written.

- RED failure-mode nuance (not a deviation): the plan predicted `AttributeError` for all four tests; the three call-site tests failed with `AttributeError` as predicted, while the hasattr-gate test failed with `AssertionError: assert False is True` because `hasattr` swallows the underlying `AttributeError`. This is the same missing-capability condition and is exactly what G-04-3 describes.
- Suite-count phrasing (not a deviation): plan said "expect 632 with the 4 new tests" — actual 632 collected (621 passed + 11 skipped).

## Scope Verification

- `git diff --stat ae126c0 -- src tests` lists exactly `src/sif/embedding/embedder.py` (+33) and `tests/unit/embedding/test_embedder_impl.py` (+69); 0 deletions, so the `__init__` Llama construction is byte-identical.
- `src/sif/search/hybrid.py` untouched (READ-ONLY per plan; the call site was already correct).
- Embedder Protocol in `src/sif/core/models.py` untouched — capability remains dynamically discovered via hasattr.
- `git status --short src tests` clean after commits.

## Out of Scope (per plan)

- UAT re-verification of test 3 and flipping G-04-3 to resolved in 04-UAT.md — owned by the orchestrator / next `/gsd-verify-work 04` resume, not this quick plan.

## Self-Check: PASSED

- Commits `9f079b6` (test/RED) and `67c9ecf` (feat/GREEN) present in git log, applied on top of plan-start commit `ae126c0`.
- `src/sif/embedding/embedder.py` and `tests/unit/embedding/test_embedder_impl.py` exist with the added method/tests.
- Runtime introspection confirms `LlamaCppEmbedder.create_completion` exists with signature `(self, prompt: str, max_tokens: int = 256, temperature: float = 0.3, stop: list[str] | None = None) -> dict[str, Any]`.
- Full quality suite green (621 passed, 11 skipped, 0 failed); ruff check and format clean.
