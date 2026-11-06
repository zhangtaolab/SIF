---
phase: 261106-u7d
plan: 01
type: quick
subsystem: typing-debt
tags: [typing, ty, tech-debt, quality-suite]
status: complete
requires:
  - "10.1 deferred-items.md item 1 (17 pre-existing ty diagnostics)"
provides:
  - "`ty check src/sif` exits 0 with zero diagnostics — milestone v1.0 type gate green"
  - "ty as the project's sole type checker (no mypy references remain in src, tests, pyproject.toml)"
affects: []
tech-stack:
  added: []
  patterns:
    - "assert-narrowing of module-level optional imports at use sites (ty 0.0.97 narrows module-level names after assert)"
    - "Protocol describing the real structural surface replaces a wrong forward-ref annotation"
key-files:
  created: []
  modified:
    - src/sif/cli/commands/mcp.py
    - src/sif/database/database.py
    - src/sif/database/migrations.py
    - src/sif/embedding/model.py
    - src/sif/indexing/parser.py
    - src/sif/mcp/transports/http.py
    - src/sif/search/hybrid.py
    - src/sif/indexing/scanner.py
    - pyproject.toml
    - .planning/phases/10.1-address-tech-debt-path-normalization-review-findings-cr-01-c/deferred-items.md
decisions:
  - "getattr locals in hybrid.py carry `# noqa: B009` — ruff B009 and ty's object-not-callable are in direct conflict there; direct attribute access probe-verified FAILING under ty (still `object is not callable`), so getattr is required for ty and the noqa for ruff"
metrics:
  duration: 392s
  completed: 2026-11-06
actuals:
  tokens: 2123   # chars/4 over the committed src+pyproject diff (plan estimate: 30000)
  tasks: 2
  commits: 2     # measured: git rev-list --count e0d9596^..HEAD
plan_head_before: 36a59f6
plan_head_after: 3fc5908
---

# Quick Task 261106-u7d: Typing debt batch 4 — clear all 17 ledgered ty diagnostics Summary

One-liner: All 17 `ty check src/sif` diagnostics cleared via annotation/narrowing/assert/Protocol/cast fixes across 7 files (17 → 0), the latent `sif mcp stdio` no-index TypeError fixed with a stderr console, and both residual mypy references dropped so ty stands as the sole type checker.

## What Was Done

### Task 1: Clear all 17 ty diagnostics (commit e0d9596)

- **src/sif/embedding/model.py** — casing fix `**kwargs: dict[str, any]` → `dict[str, Any]`; `Any` added to the typing import.
- **src/sif/database/migrations.py** — module-level `_MigrationConnection(Protocol)` with `execute`/`fetchone` (structural match to the tests' RealSQLiteAdapter) replaces the `"DatabaseConnection"` forward-ref that named a class with neither method; `# noqa: F821` dropped.
- **src/sif/indexing/parser.py** — `title = cast("str", metadata.get("title", ""))` at frontmatter title extraction (runtime-identity; a non-str title passes through exactly as before).
- **src/sif/database/database.py** — `_enable_extensions` binds `conn = self._connection` + `assert conn is not None`, then uses `conn` for the pragma and the sqlite-vec load trio; `except Exception: pass` handling and comments verbatim.
- **src/sif/search/hybrid.py** — `_generate_hypothetical_document` binds a local `embedder`, keeps the same-message RuntimeError guard, and inside each hasattr branch binds `generate`/`create_completion` via getattr locals with `cast(str, ...)` on the generate return. Both hasattr gates, both prompt blocks, the `.strip()` post-processing, and the final RuntimeError are unchanged — HyDE duck-typing contract intact.
- **src/sif/mcp/transports/http.py** — four assert-narrowing insertions: `assert JSONResponse is not None` (top of `_mcp_post_handler`), `assert StreamingResponse is not None` (top of `_mcp_get_handler`), `assert CORSMiddleware is not None` (in `create_app` before `add_middleware`), and `assert request is not None` + `assert JSONResponse is not None` (top of the `validate_origin` closure). The try/except optional-import block is byte-identical — test patch targets survive.
- **src/sif/cli/commands/mcp.py** — module-level `console_err = Console(stderr=True)`; the no-index warning now actually prints to stderr. The previous `file=sys.stderr` kwarg never worked (`Console.print` has no `file` parameter — latent TypeError on the untested path). `import sys` removed (no remaining references, grep-verified). Markup renders on the stderr console as before.

### Task 2: Drop residual mypy references + flip ledger (commit 3fc5908)

- **pyproject.toml** — `[tool.ty.rules]` comment rewritten to stand on its own in ty terms (optional-dependency imports not installed in every type-check environment); `import-not-found = "ignore"` value and all other keys unchanged.
- **src/sif/indexing/scanner.py** — `".mypy_cache"` removed from `DEFAULT_IGNORE_PATTERNS`. User-directed exception to zero-behavior-change: a directory literally named `.mypy_cache` inside an indexed notes tree is no longer skipped (no test asserts the default ignore-list contents).
- **.planning/phases/10.1-.../deferred-items.md** — item 1 flipped `status: open` → `status: resolved` with a `**Resolution:**` line pointing at quick task 261106-u7d; item 2 (test-side ResourceWarnings) untouched.

## Verification Results

All plan-level gates run from the repo root, in order — all green:

| Gate | Result |
|------|--------|
| `ty check src/sif` | exits 0, zero diagnostics (baseline: 17) |
| `ruff check src tests` | All checks passed |
| `ruff format --check src tests` | 151 files already formatted |
| `env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q` | 1011 passed, 96.21% coverage (fail_under=90 reached) |
| `grep -rIl mypy src tests pyproject.toml` | empty |

Task-level gates: the six targeted unit test files for Task 1 passed (129 passed; the 90% coverage gate "failure" on that subset run is a subset-run artifact — the full suite meets 96.21%), and Task 2's scanner tests passed (5 passed) with the mypy grep gate clean.

The 17 pytest warnings are the pre-existing test-side ResourceWarnings tracked as deferred-items.md item 2 — deliberately untouched by this task.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `# noqa: B009` added to the two hybrid.py getattr locals**
- **Found during:** Task 1 verification — `ruff check` failed with B009 (constant-attribute getattr) on both `getattr(embedder, "generate")` and `getattr(embedder, "create_completion")`.
- **Issue:** ruff B009 and ty's `call-non-callable` are in direct conflict at these two sites. The plan's getattr shape is required for ty (probe re-verified during execution: direct attribute access `embedder.generate` still yields `error[call-non-callable]: Object of type object is not callable` — the Embedder protocol has no `generate`/`create_completion`, so ty's hasattr fallback types the attribute as `object`), but B009 flags the getattr form.
- **Fix:** kept the plan's getattr locals and added `# noqa: B009` to both lines. B009's premise ("getattr with a constant is not any safer than property access") does not hold here — the getattr form is load-bearing for the type checker.
- **Files modified:** src/sif/search/hybrid.py
- **Commit:** e0d9596

Otherwise the plan executed exactly as written — every other fix shape from the 17-site table landed as specified, with no fallbacks needed (all four http.py asserts narrowed cleanly; the migrations.py Protocol resolved without RUF100 residue).

## Threat Flags

None. No new trust-boundary surface: annotation/narrowing-only changes plus the two user-approved exceptions already dispositioned in the plan's threat register (T-261106-u7d-01 accept, T-261106-u7d-02 mitigate — the stderr warning fix verified by the passing suite and ty/ruff gates).

## Self-Check: PASSED

- Commit e0d9596 (Task 1) and 3fc5908 (Task 2) both exist on dev and are ancestors of HEAD.
- All 9 modified source/config files present on disk with the changes described above.
- SUMMARY written to .planning/quick/261106-u7d-typing-debt-batch-4-clear-all-17-ledgere/261106-u7d-SUMMARY.md.
