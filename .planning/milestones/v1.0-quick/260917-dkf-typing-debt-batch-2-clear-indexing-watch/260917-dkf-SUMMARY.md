---
phase: 260917-dkf-typing-debt-batch-2-clear-indexing-watch
plan: 01
subsystem: indexing/embedding/models
tags: [typing, mypy, tech-debt, watcher, embedding]
requires:
  - "phase-03 open deferred item: mypy strict-mode typing debt (117 errors / 34 files after batch 1)"
provides:
  - "src/sif/indexing/watcher.py mypy strict-clean (0 errors) — batch 2 of N"
  - "src/sif/embedding/manager.py mypy strict-clean (0 errors) — batch 2 of N"
  - "src/sif/embedding/embedder.py mypy strict-clean (0 errors) — batch 2 of N"
  - "src/sif/models/embedding.py mypy strict-clean in full-project run (call-args gone via Field(default=...) keyword form)"
  - "reusable patterns for later batches: TYPE_CHECKING same-package imports to resolve quoted forward refs; os.fsdecode coercion for watchdog bytes|str event paths; BaseObserver annotation for conditionally-imported Observer; `default=` keyword form for pydantic Field defaults under mypy's native dataclass_transform; typed intermediate locals for Any-returning third-party calls"
affects:
  - src/sif/indexing/watcher.py
  - src/sif/models/embedding.py
  - src/sif/embedding/manager.py
  - src/sif/embedding/embedder.py
tech-stack:
  added: []
  patterns:
    - "Pydantic `Field(<positional default>)` → `Field(default=...)`: mypy's native pydantic dataclass_transform reads defaults only from the `default=` keyword or direct assignment (no plugin needed); positional form reads as required and call-args-errors every defaulted construction site"
    - "Typed intermediate locals (`result: <declared return type> = <Any expr>` immediately before return) as the deterministic no-any-return fix for uninstalled third-party packages and numpy members that reveal Any"
    - "Consecutive `result:` annotated locals in ONE function scope trip mypy no-redef and (unannotated) ruff RET504 — use a distinct annotated local name per branch instead"
key-files:
  created: []
  modified:
    - src/sif/indexing/watcher.py
    - src/sif/models/embedding.py
    - src/sif/embedding/manager.py
    - src/sif/embedding/embedder.py
decisions:
  - "Watcher: `BaseObserver` (from watchdog.observers.api) as the `_observer` field annotation while `Observer()` stays the constructor — mypy cannot use the conditionally-imported Observer name as a type; runtime-verified the platform Observer is a BaseObserver subclass"
  - "Watcher: `os.fsdecode` coercion via `_event_path(path: bytes | str) -> str` — identity for the str paths watchdog actually produces; only replaces a latent TypeError on hypothetical bytes"
  - "EmbeddingConfig: declaration-syntax fix at the model (10 positional Field defaults → `default=` keyword) instead of touching either construction site — `Field(5)` and `Field(default=5)` are the identical pydantic call, so every runtime default is unchanged (probe re-verified post-edit: MODELSCOPE / Qwen/Qwen3-Embedding-0.6B / 1024 / 512 / 32 / 0 / 2048 / None / None / True / None)"
  - "manager.py lines 39 and 54 untouched: both construction sites become type-correct once the declaration is fixed; Settings has no n_ctx attribute and `load_model` reads `self._config.n_ctx` defaulting to 2048 exactly as before"
metrics:
  duration: 8min
  completed: "2026-09-17"
  tests_before: "676 passed / 0 failed"
  tests_after: "676 passed / 0 failed"
  mypy_full_project_before: "117 errors in 34 files"
  mypy_full_project_after: "78 errors in 31 files"
actuals:
  tokens: 3072     # chars/4 over the realized diff (12290 chars)
  tasks: 3
  commits: 3
status: complete
---

# Quick Task 260917-dkf: Typing Debt Batch 2 — watcher/manager/embedder mypy strict-clean Summary

Cleared all mypy strict-mode errors in the three hottest typing-debt files — `src/sif/indexing/watcher.py` (13→0), `src/sif/embedding/manager.py` (12→0), `src/sif/embedding/embedder.py` (14→0) — via the pydantic `Field(default=...)` declaration fix in `src/sif/models/embedding.py` (11 call-args), a TYPE_CHECKING `DocumentIndexer` import + `os.fsdecode` path coercion + `BaseObserver` annotation in the watcher, and source-field/typed-local annotations in the embedder. Zero behavior change; full-project mypy 117 → 78 errors; suite green at 676/0; ruff clean.

## What Was Done

### Task 1: watcher.py (13 → 0 errors) — commit 30a14ae

- Imports: `import os`, `from typing import TYPE_CHECKING`, `from watchdog.observers.api import BaseObserver`; `if TYPE_CHECKING: from sif.indexing.indexer import DocumentIndexer` (typecheck-only, zero runtime import edge).
- Both quoted `"DocumentIndexer"` annotations kept their quotes; the two stale `# noqa: F821` comments removed (would trip RUF100 once the name resolves).
- `self._observer: Observer | None` → `BaseObserver | None`; the `Observer()` constructor call untouched. Fixes valid-type at 102 and the stop/join attr-defined cascade at 141-142.
- Module-level `_event_path(path: bytes | str) -> str` via `os.fsdecode`; all four handlers coerce `event.src_path` into a `src_path` local used by both the `_should_handle` guard and the log line; `on_moved` additionally coerces `event.dest_path` inside the f-string. For the str paths watchdog actually produces, `fsdecode` is identity, so log output is byte-identical.
- Verify: mypy Success; `tests/unit/indexing/test_watcher.py` 28 passed; ruff check + format clean on the file.

### Task 2: models/embedding.py + manager.py (12 → 0 errors) — commit d150a8a

- EmbeddingConfig ONLY (EmbeddingModelInfo / EmbeddingRequest / EmbeddingResponse untouched): the 10 positional `Field(<default>, ...)` first args converted to `default=<default>` keyword form — model_type, model_path, model_name, embedding_dim, max_tokens, batch_size, n_gpu_layers, n_ctx, api_key, cache_embeddings. `model_name` wrapped to three lines to stay under the 100-char limit (ruff-format-canonical).
- manager.py: `from typing import Any` added after `import time`; `get_model_info(self) -> dict` → `-> dict[str, Any]`. Lines 39 (`EmbeddingConfig()`) and 54 (`from_settings`, legitimately omitting n_ctx — Settings has no n_ctx attribute) byte-untouched; both become type-correct from the declaration fix alone.
- Runtime probe re-verified all 11 EmbeddingConfig defaults identical post-edit (pydantic 2.13.1): `ModelType.MODELSCOPE | Qwen/Qwen3-Embedding-0.6B | 1024 512 32 0 2048 | None None | True None`.
- Verify: mypy on manager.py Success (follows imports into models/embedding.py, validating the pair); `test_manager.py + test_factory.py` 19 passed; ruff clean on both files.

### Task 3: embedder.py (14 → 0 errors; full-project 117 → 78) — commit e39d092

- Source-field annotations: `self._dimension: int = ...` at the three third-party assignment sites (SentenceTransformerEmbedder, LlamaCppEmbedder `n_embd()`, ModelScopeEmbedder) — makes the three `dimension` properties return int.
- Typed intermediate locals before each return at the no-any-return sites: `result: list[float]` (ST embed, Llama embed, ModelScope embed, OpenAI `_normalize`), `result: list[list[float]]` (both embed_batch), `result: dict[str, Any]` (create_completion, arguments unchanged including the `stop if stop is not None else []` normalization), `result: np.ndarray` / `pooled: np.ndarray` (the two `_unwrap_embedding` mean-pool branches — see Deviations), plus `arr: np.ndarray` documentation annotation on `np.asarray` in `_unwrap_embedding`.
- Stragglers: `self.vocabulary: dict = {}` → `dict[str, int]` (TF-IDF term-to-index intent; never populated); `**kwargs,` → `**kwargs: Any` in `create_embedder` (`Any` already imported).
- Untouched per plan: all `# noqa: PLC0415` runtime imports, is_quiet/suppress_output branches, the ragged/misindexed response guards in OpenAIEmbedder.embed_batch, and the ValueError shapes in `_unwrap_embedding`.
- Full gates: mypy on embedder.py Success; `tests/unit/embedding` 87 passed; FULL suite 676 passed / 0 failed; `ruff check src tests` + `ruff format --check src tests` clean (132 files); full-project mypy exactly 78 errors in 31 files with zero error lines referencing watcher.py, manager.py, embedder.py, or models/embedding.py.

## Verification Results

| Gate | Command | Result |
|------|---------|--------|
| mypy file gate (watcher) | `env -u FORCE_COLOR NO_COLOR=1 uv run mypy src/sif/indexing/watcher.py` | exit 0, `Success: no issues found in 1 source file` |
| mypy file gate (manager) | `env -u FORCE_COLOR NO_COLOR=1 uv run mypy src/sif/embedding/manager.py` | exit 0, `Success` (validates the models/embedding.py pair via follow-imports) |
| mypy file gate (embedder) | `env -u FORCE_COLOR NO_COLOR=1 uv run mypy src/sif/embedding/embedder.py` | exit 0, `Success` |
| Watcher unit tests | `pytest tests/unit/indexing/test_watcher.py -q` | 28 passed |
| Manager/factory tests | `pytest tests/unit/embedding/test_manager.py tests/unit/embedding/test_factory.py -q` | 19 passed |
| Embedding unit tests | `pytest tests/unit/embedding -q` | 87 passed |
| Full suite | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` | 676 passed / 0 failed (run twice — final state included; the 2 order-dependent caplog flakers in test_openai_embedder.py did not fire) |
| Lint | `ruff check src tests` | All checks passed |
| Format | `ruff format --check src tests` | 132 files already formatted |
| Full-project count | `env -u FORCE_COLOR NO_COLOR=1 uv run mypy src/sif` | 78 errors in 31 files (baseline this session: 117 in 34; 13+12+14=39 cleared → exactly 78 as planned) |
| Target-file zero | error lines grep over full-project run | 0 matches for watcher.py / manager.py / embedder.py / models/embedding.py |
| Runtime defaults probe | `EmbeddingConfig()` field dump | identical to pre-change defaults (see Task 2) |
| Zero behavior change | `git diff HEAD~3 -- <4 files>` full-line audit | every hunk is an import addition, the `_event_path` helper + handler locals, a noqa removal, the BaseObserver annotation, one of the 10 `default=` conversions, `dict[str, Any]`, `self._dimension: int` ×3, a typed local, the `arr` annotation, `dict[str, int]`, or `**kwargs: Any` — no logic edits, no guard removals, no constructor/value changes |

## Deviations from Plan

**1. [Rule 3 - blocking lint/type collision] second `_unwrap_embedding` mean-pool local named `pooled`, not `result`**
- **Found during:** Task 3 (embedder.py)
- **Issue:** The plan prescribed an annotated `result: np.ndarray` local in BOTH mean-pool branches of `LlamaCppEmbedder._unwrap_embedding`. Python function scope is flat, so two annotated declarations of `result` tripped mypy `[no-redef]` (line 217 vs 208). Downgrading the second to an unannotated assignment fixed mypy but then tripped ruff RET504 (unnecessary assignment before return — flake8-return exempts annotated assignments only).
- **Fix:** Distinct annotated local `pooled: np.ndarray = arr[0].mean(axis=0)` in the 3-D branch. Same guarantee (typed np.ndarray local before return), still annotation-only, satisfies mypy and ruff simultaneously.
- **Files modified:** src/sif/embedding/embedder.py
- **Commit:** e39d092

No other deviations. Two observations, neither requiring action:
- The plan's error inventory for embedder.py listed 12 no-any-return sites; the fresh run confirmed exactly 12 (lines 95, 111, 116, 184, 205, 213, 253, 263, 334, 343, 348, 514) + type-arg 532 + no-untyped-def 567 = 14. Line 199's bare `return arr` was itself clean (np.asarray is properly typed); the `arr: np.ndarray` annotation is the documentation-only extra the plan prescribed.
- Full-project count landed exactly on the planned 78 (not the batch-context's stale "expect 75"); counts matched the planner's fresh 13/12/14 inventory at every gate.

## Commits

| Commit | Task | Scope |
|--------|------|-------|
| 30a14ae | Task 1 | `fix(260917-dkf): type watcher event paths, observer, and DocumentIndexer; watcher.py mypy-clean` — pathspec `src/sif/indexing/watcher.py` |
| d150a8a | Task 2 | `fix(260917-dkf): declare EmbeddingConfig Field defaults as keywords; type manager; manager.py mypy-clean` — pathspec `src/sif/models/embedding.py src/sif/embedding/manager.py` |
| e39d092 | Task 3 | `fix(260917-dkf): annotate embedder third-party returns; embedder.py mypy-clean` — pathspec `src/sif/embedding/embedder.py` |

All three commits pathspec-scoped; no unrelated files swept in; untracked runtime dirs (`.gsd/`, `.planning/state.json`, `.planning/tmp/`, `.planning/ui-reviews/`) left alone; pyproject.toml untouched.

## Deferred Items (for later batches)

- Phase-03 typing debt remains open: full-project `uv run mypy src/sif` now reports 78 errors in 31 files. Next hottest: `mcp/handlers.py` (12). Patterns established across batches 1-2: TYPE_CHECKING imports for forward refs and uninstalled third parties, `X | None` field annotations + narrowing asserts, `os.fsdecode` path coercion, `BaseObserver` base-class annotation, pydantic `default=` keyword form, typed intermediate locals (with DISTINCT names per branch scope).
- `pyproject.toml` untouched per plan — the `unused section(s): module = ['sif.cli.*', 'tests.*']` note under single-file mypy invocation is config-level noise serving full-project runs.

## Self-Check: PASSED

- File modified and committed: `src/sif/indexing/watcher.py` — FOUND (30a14ae)
- File modified and committed: `src/sif/models/embedding.py` — FOUND (d150a8a)
- File modified and committed: `src/sif/embedding/manager.py` — FOUND (d150a8a)
- File modified and committed: `src/sif/embedding/embedder.py` — FOUND (e39d092)
- Commits 30a14ae / d150a8a / e39d092 in `git log` — FOUND
- SUMMARY written to this path with `status: complete`; not committed (orchestrator handles planning-file commits per task constraints)
