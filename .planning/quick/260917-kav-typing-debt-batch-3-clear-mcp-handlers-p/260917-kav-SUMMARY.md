---
phase: 260917-kav-typing-debt-batch-3-clear-mcp-handlers-p
plan: 01
subsystem: typing-debt
tags: [mypy, strict-mode, typing, zero-behavior-change, deferred-item]
requires:
  - "batch 1 (260917-bo2): search/rerank.py mypy-clean, create_reranker returns LlamaCppReranker | CrossEncoderReranker | Qwen3Reranker"
  - "batch 2 (260917-dkf): watcher/manager/embedder mypy-clean, full-project baseline 78 errors / 31 files"
provides:
  - "src/sif/mcp/handlers.py mypy strict-clean (ToolHandler base attrs declared ClassVar)"
  - "src/sif/cli/commands/search.py mypy strict-clean (list[Any] helpers, tuple[str, ...] Click params, walrus content narrowing)"
  - "src/sif/database/connection.py mypy strict-clean (parameterized sqlite generics, typed fetchone row local)"
  - "SearchPipeline reranker param accepts Qwen3Reranker (union mirrors create_reranker return)"
affects:
  - "full-project mypy count: 78 -> 46 errors (31 -> 28 files); next batches draw from the remaining 46"
tech-stack:
  added: []
  patterns:
    - "ClassVar on ABC attribute annotations so subclass ClassVar overrides type-check"
    - "walrus binding for getattr-guard narrowing instead of widening the callee's param type"
    - "list[Any] for duck-typed display helpers (list[SearchResult] | list[dict[str, Any]] unions would break hasattr-branching bodies)"
key-files:
  created: []
  modified:
    - src/sif/mcp/handlers.py
    - src/sif/cli/commands/search.py
    - src/sif/search/hybrid.py
    - src/sif/database/connection.py
decisions:
  - "ToolHandler base name/description/input_schema declared ClassVar (mypy requires base/subclass agreement on variable kind; grep confirmed no instance assignment in src/sif/mcp)"
  - "prepend_line_numbers call sites narrowed via walrus instead of widening the helper to str | None — the guard already rejects None, and the helper's content.split would crash on None"
  - "format helpers typed list[Any] — precise unions break hasattr-branching bodies; documents the duck typing honestly"
  - "reranker union widened in hybrid.py directly (no shared alias/Protocol) — mirrors create_reranker's batch-1 return type, minimal surface"
  - "connection.py parameters typed to sqlite3 typeshed's accepted shapes; fetchone routed through a typed row local because typeshed's Cursor.fetchone() returns Any"
metrics:
  duration: 4min
  completed: "2026-09-17"
status: complete
actuals:
  tokens: 1889    # chars/4 over the realized diff (git diff HEAD~3 HEAD = 7558 chars); estimate 33000 covered exploration+verification, realized edits were annotation-only
  tasks: 3
  commits: 3       # measured: git rev-list --count HEAD~3..HEAD
  plan_head_before: bf4edb3d96114872b34ceb3bdfbf511076671061
---

# Quick Task 260917-kav: Typing Debt Batch 3 Summary

One-liner: Cleared all mypy strict errors in the three hottest remaining files (mcp/handlers.py 12, cli/commands/search.py 11, database/connection.py 9) via ClassVar markers, generic parameterization, and walrus narrowing; widened SearchPipeline's reranker union to include Qwen3Reranker. Full-project mypy 78 -> 46, zero behavior change, suite 676 green.

## What Was Done

### Task 1: ToolHandler base ClassVar declarations (12 -> 0)

`src/sif/mcp/handlers.py` lines 31-33: the three bare annotations on the abstract `ToolHandler` base became `name: ClassVar[str]`, `description: ClassVar[str]`, `input_schema: ClassVar[dict[str, Any]]`. All 12 `[misc]` "Cannot override instance variable with class variable" errors stemmed from the base/subclass disagreement; the four subclasses stay byte-identical. Annotation-only either way — no runtime attribute is created by a bare or ClassVar annotation.

- Commit: 296ca3d

### Task 2: search.py generics + content narrowing; hybrid.py reranker union (11 -> 0)

`src/sif/cli/commands/search.py`: added `from typing import Any`; the four format helpers (`format_results_json/csv/md/xml`) take `results: list[Any]`; the three Click `collection` params (search_cmd, vsearch_cmd, query_cmd) take `tuple[str, ...]`; the three prepend_line_numbers call sites replaced the bare getattr guard with `if line_numbers and (content := getattr(r, "content", None)):` + `content = prepend_line_numbers(content)` — the walrus binds the same value the guard already computed. `src/sif/search/hybrid.py`: TYPE_CHECKING import gains Qwen3Reranker; `SearchPipeline.__init__` reranker param widened to `LlamaCppReranker | CrossEncoderReranker | Qwen3Reranker | None`, mirroring create_reranker's declared return from batch 1. Both files committed atomically since the search.py gate follows imports into hybrid.py.

- Commit: 3521778

### Task 3: connection.py sqlite generics + full-project gate (9 -> 0, 78 -> 46)

`src/sif/database/connection.py`: added `from typing import Any`; `execute`/`fetchone`/`fetchall` parameters typed `tuple[Any, ...] | dict[str, Any] | None`; `executemany` takes `list[tuple[Any, ...] | dict[str, Any]]`; `fetchone` routes typeshed's Any-returning `Cursor.fetchone()` through a `row: sqlite3.Row | None` local. The `if parameters` truthiness semantics unchanged (empty tuple/dict was already falsy).

- Commit: 4f24682

## Verification Results

| Gate | Result |
|------|--------|
| mypy src/sif/mcp/handlers.py | exit 0 (unused-section NOTE only) |
| mypy src/sif/cli/commands/search.py | exit 0 (validates widened union via import-following) |
| mypy src/sif/database/connection.py | exit 0 |
| tests/unit/mcp | 42 passed |
| tests/unit/cli/test_search.py + test_formatters.py | 27 passed |
| tests/unit/db/test_database.py | 20 passed |
| Full pytest suite | 676 passed / 0 failed (the 2 order-dependent caplog flakers in tests/unit/embedding/test_openai_embedder.py did not fire this run) |
| ruff check src tests | clean |
| ruff format --check src tests | clean (132 files) |
| Full-project mypy | exactly 46 errors in 28 files (78 - 32 = 46, exact match); zero errors in the three target files |
| Zero-behavior-change audit | git diff HEAD~3 HEAD touches exactly the four planned files, 26 insertions / 23 deletions, every hunk annotation-only |

## Deviations from Plan

None - plan executed exactly as written. Baseline counts re-verified before editing (12/11/9, full 78) and matched the planner's inventory exactly; all predicted post-states landed on the nose (per-file zeros, full-project 46, suite 676).

## Deferred-Item Progress

Phase-03 open deferred item (mypy strict-mode typing debt): 46 errors remain in ~28 files after batches 1-3 (was ~117 in 31+ files after batch 2's full-project count of 78; batch 1 cleared 22, batch 2 cleared 39, batch 3 cleared 32). Next batches can pick from the remaining hottest files, or /gsd-complete-milestone can accept the residual debt.

## Self-Check: PASSED

- Files exist: src/sif/mcp/handlers.py, src/sif/cli/commands/search.py, src/sif/search/hybrid.py, src/sif/database/connection.py (all modified, all committed)
- Commits verified in git log: 296ca3d, 3521778, 4f24682
- Untracked runtime dirs (.gsd/, .planning/state.json, .planning/tmp/, .planning/ui-reviews/) left untouched by all three commits
