# Deferred Items — Phase 03 (out-of-scope discoveries)

## 2026-09-03 — plan 03-07 execution

- ~~**mypy cannot run in this environment (pre-existing).**~~ (verify-work close-out follow-up). CR-03 (bc441d0) bumped `pyproject.toml [tool.mypy]` `python_version` to 3.10 but legacy `mypy.ini` (phase 08-06) pinned `python_version = 3.9` and by mypy's config precedence completely shadowed pyproject, so mypy kept dying in third-party packages using 3.10+ syntax (sentence_transformers, then mcp); fix consolidated all per-module overrides into `pyproject.toml [[tool.mypy.overrides]]` (sif.cli.* click-decorator relaxation, sentence_transformers/numpy ignores, tests.* relaxations) and deleted `mypy.ini` — single source of truth; quality suite re-confirmed green (ruff clean, format clean, pytest 572 passed / 11 skipped).
  **Status:** resolved
  Resolved 2026-09-04 — `mypy src/sif` runs to completion after the fix (re-confirmed 2026-09-14). The strict-mode typing debt that remained (142 errors in 36 files at the time) is re-filed below as its own open deferred item rather than buried inside this resolved entry.

## 2026-09-14 — audit re-file: mypy strict-mode typing debt

- As of 2026-09-14 `uv run mypy src/sif` reported 140 errors in 36 files (76 checked); top error codes type-arg, no-any-return, attr-defined; hottest files search/rerank.py, indexing/watcher.py, mcp/handlers.py, embedding/manager.py. Pre-existing strict-mode typing debt, unrelated to phase 03 scope.
  **Status:** resolved
  Resolved 2026-11-06 at milestone v1.0 close — mypy retired, ty is the sole type checker. Typing debt was cleared in two waves: batches 260917-bo2/dkf/kav drove mypy errors down (117→46 full-project) while mypy was still the checker; quick task 261106-u7d then cleared all 17 remaining `ty check src/sif` diagnostics (assert-narrowing, Protocol, cast; zero behavior change) and dropped every residual mypy reference (commits e0d9596 + 3fc5908). Final state: `ty check src/sif` exits 0, zero mypy references in src/tests/pyproject, 10.1 deferred-items item 1 ledgered resolved.
