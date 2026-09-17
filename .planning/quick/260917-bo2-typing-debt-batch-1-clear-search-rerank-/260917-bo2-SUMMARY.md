---
phase: 260917-bo2-typing-debt-batch-1-clear-search-rerank-
plan: 01
subsystem: search/rerank
tags: [typing, mypy, tech-debt, rerank]
requires:
  - "phase-03 open deferred item: mypy strict-mode typing debt (~139 errors / 35 files)"
provides:
  - "src/sif/search/rerank.py mypy strict-clean (0 errors) — batch 1 of N"
  - "reusable pattern for later batches: TYPE_CHECKING third-party imports + X | None lazy-field annotations + narrowing asserts after load guards"
affects:
  - src/sif/search/rerank.py
tech-stack:
  added: []
  patterns:
    - "Lazy optional-dependency fields typed as `X | None` with TYPE_CHECKING-only imports; runtime narrowing via `assert self._x is not None` immediately after the existing `if self._x is None: self.load()` guard"
key-files:
  created: []
  modified:
    - src/sif/search/rerank.py
decisions:
  - "Typing fixed at the field level, not with ignores: annotating `self._model: X | None = None` makes the three `load()` early-exit guards type-check as reachable — the typing was wrong, the code was right"
  - "TYPE_CHECKING-only `from sif.config.settings import Settings` for the create_reranker param — zero runtime import edge, no circular-import risk"
metrics:
  duration: 3min
  completed: "2026-09-17"
  tests_before: "676 passed / 0 failed"
  tests_after: "676 passed / 0 failed"
actuals:
  tokens: 958      # chars/4 over the realized diff (3831 chars)
  tasks: 2
  commits: 2
status: complete
---

# Quick Task 260917-bo2: Typing Debt Batch 1 — rerank.py mypy strict-clean Summary

Cleared all 22 mypy strict-mode errors in `src/sif/search/rerank.py` (lazy optional-dependency model fields annotated `X | None` via TYPE_CHECKING imports, runtime-safe narrowing asserts after existing load guards, 4 stale type-ignores + 1 stale noqa removed, `create_reranker(settings: Settings)` annotated) with zero behavior change; suite green at 676/0.

## What Was Done

### Task 1: LlamaCppReranker + CrossEncoderReranker (22 → 16 errors) — commit 6d3875c

- `if TYPE_CHECKING:` block extended with `from llama_cpp import Llama`; the `# noqa: F401` on the existing `sentence_transformers.CrossEncoder` import dropped (now referenced by an annotation — keeping it would trip RUF100).
- `LlamaCppReranker.__init__`: `self._model = None` → `self._model: Llama | None = None`. This alone fixed the `load()` unreachable-statement error (guard at 107-108 now type-checks as reachable) and both `"None" has no attribute "embed"` errors in `rerank()`.
- `LlamaCppReranker.rerank()`: `assert self._model is not None` added directly after the existing `if self._model is None: self.load()` guard.
- `CrossEncoderReranker.__init__`: `self._model: CrossEncoder | None = None`; same narrowing assert pattern in `rerank()`; stale `# type: ignore[union-attr]` removed from the `predict()` line.
- Verify gate: mypy reported exactly 16 remaining errors, all at lines ≥ 281 (Qwen3Reranker + factory); `tests/unit/inference/test_rerank.py` 27 passed; ruff check + format clean on the file.

### Task 2: Qwen3Reranker + create_reranker (16 → 0 errors) — commit 1c1bec2

- TYPE_CHECKING block: added `from transformers import AutoModelForCausalLM, AutoTokenizer` (third-party group) and `from sif.config.settings import Settings` (first-party group, blank-line separated).
- `Qwen3Reranker.__init__`: `self._model: AutoModelForCausalLM | None = None`, `self._tokenizer: AutoTokenizer | None = None`. `_token_true_id`/`_token_false_id` left as-is (`int | None` — indexing on Any-typed logits needs no change, as planned).
- `Qwen3Reranker.load()`: zero edits — with the annotations in place the assignments narrow the fields and the `.to()` chains / `convert_tokens_to_ids` calls type-check; the third unreachable guard became reachable.
- `Qwen3Reranker.rerank()`: two asserts (`_model`, `_tokenizer`) after the existing load guard; three stale ignores removed (`union-attr` ×2, `operator` ×1).
- `create_reranker(settings: Settings)` annotated; body byte-identical (getattr/hasattr defensive reads, qwen3 name auto-detection, unknown-type ValueError untouched).

## Verification Results

| Gate | Command | Result |
|------|---------|--------|
| mypy file gate | `env -u FORCE_COLOR NO_COLOR=1 uv run mypy src/sif/search/rerank.py` | exit 0, `Success: no issues found in 1 source file` (only the expected `pyproject.toml: note: unused section(s)` config note — single-file-invocation noise, out of scope per plan) |
| Full suite | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` | 676 passed / 0 failed (baseline preserved; the 2 order-dependent caplog flakers did not fire) |
| Reranker unit tests | `pytest tests/unit/inference/test_rerank.py -q` | 27 passed |
| Lint | `ruff check src tests` | All checks passed |
| Format | `ruff format --check src tests` | 132 files already formatted |
| Guards retained | `grep -c "if self._model is not None:" src/sif/search/rerank.py` | 3 (LlamaCpp 107 / CrossEncoder 185 / Qwen3 280 — all load() early-exits intact) |
| Zero behavior change | `git diff HEAD~2 -- src/sif/search/rerank.py` full-line audit | Every changed line is one of: field annotations, TYPE_CHECKING imports, narrowing asserts directly after existing guards, 4 stale type-ignore removals, noqa F401 removal, `settings: Settings` annotation. No guard removals, no logic edits, no signature/value changes |

## Deviations from Plan

None — plan executed exactly as written. Two environment observations, neither requiring action:

- The plan's verify command references `tests/unit/inference/test_rerank.py`; the first invocation transiently reported "no tests ran" (0.00s collection anomaly). Re-run from the repo root collected and passed all 27 tests; treated as a transient shell/cwd artifact, not a code issue.
- Plan cited line numbers pre-edit (108/186/278 guards, ignores at 238/374/377/380, `no-untyped-def` at 391); post-edit lines shifted by the 3 added lines as expected. Error classes and locations matched the planner's inventory exactly at each gate (22 → 16 → 0).

## Commits

| Commit | Task | Scope |
|--------|------|-------|
| 6d3875c | Task 1 | `fix(260917-bo2): type lazy model fields in LlamaCpp/CrossEncoder rerankers` — pathspec `src/sif/search/rerank.py` |
| 1c1bec2 | Task 2 | `fix(260917-bo2): type Qwen3Reranker fields and create_reranker param; rerank.py mypy-clean` — pathspec `src/sif/search/rerank.py` |

Both commits pathspec-scoped to `src/sif/search/rerank.py`; no unrelated files swept in; untracked runtime dirs (`.gsd/`, `.planning/state.json`, `.planning/tmp/`, `.planning/ui-reviews/`) left alone.

## Deferred Items (for later batches)

- Phase-03 typing debt remains open: full-project `uv run mypy src/sif` still reports ~117 errors in OTHER files (batch-1 scope was rerank.py only). Reusable fix pattern established here: TYPE_CHECKING third-party imports + `X | None` lazy-field annotations + narrowing asserts after existing load guards.
- `pyproject.toml` untouched per plan — the `unused section(s): module = ['sif.cli.*', 'tests.*']` note under single-file mypy invocation is config-level noise serving full-project runs.

## Self-Check: PASSED

- File exists: `src/sif/search/rerank.py` (modified, committed) — FOUND
- Commit 6d3875c in `git log` — FOUND
- Commit 1c1bec2 in `git log` — FOUND
- SUMMARY written to this path with `status: complete`; not committed (orchestrator handles planning-file commits per task constraints)
