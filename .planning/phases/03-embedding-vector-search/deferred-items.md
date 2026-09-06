# Deferred Items — Phase 03 (out-of-scope discoveries)

## 2026-09-03 — plan 03-07 execution

- [x] RESOLVED 2026-09-04 — ~~**mypy cannot run in this environment (pre-existing).**~~
  (verify-work close-out follow-up).** Root cause was deeper than the original
  diagnosis: CR-03 (bc441d0) had already bumped `pyproject.toml [tool.mypy]
  python_version` to 3.10, but a legacy `mypy.ini` (phase 08-06) still pinned
  `python_version = 3.9` and — by mypy's config precedence — completely shadowed
  pyproject, so mypy kept dying in third-party packages using 3.10+ syntax
  (sentence_transformers, then mcp). Fix: consolidated all per-module overrides
  into `pyproject.toml [[tool.mypy.overrides]]` (sif.cli.* click-decorator
  relaxation, sentence_transformers/numpy ignores, tests.* relaxations) and
  deleted `mypy.ini` — single source of truth. `mypy src/sif` now runs to
  completion: **142 errors in 36 files (74 checked)** — strict-mode typing debt
  across the codebase (top: type-arg 27, no-any-return 16, attr-defined 16;
  hottest files: search/rerank.py 27, indexing/watcher.py 13, mcp/handlers.py 12,
  embedding/manager.py 12). This residual debt is pre-existing and unrelated to
  phase 03 scope; it is the actionable backlog replacement for "mypy cannot run".
  Quality suite re-confirmed green after the change: ruff clean, format clean,
  pytest 572 passed / 11 skipped.
