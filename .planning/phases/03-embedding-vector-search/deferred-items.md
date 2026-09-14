# Deferred Items — Phase 03 (out-of-scope discoveries)

## 2026-09-03 — plan 03-07 execution

- ~~**mypy cannot run in this environment (pre-existing).**~~ (verify-work close-out follow-up). CR-03 (bc441d0) bumped `pyproject.toml [tool.mypy]` `python_version` to 3.10 but legacy `mypy.ini` (phase 08-06) pinned `python_version = 3.9` and by mypy's config precedence completely shadowed pyproject, so mypy kept dying in third-party packages using 3.10+ syntax (sentence_transformers, then mcp); fix consolidated all per-module overrides into `pyproject.toml [[tool.mypy.overrides]]` (sif.cli.* click-decorator relaxation, sentence_transformers/numpy ignores, tests.* relaxations) and deleted `mypy.ini` — single source of truth; quality suite re-confirmed green (ruff clean, format clean, pytest 572 passed / 11 skipped).
  **Status:** resolved
  Resolved 2026-09-04 — `mypy src/sif` runs to completion after the fix (re-confirmed 2026-09-14). The strict-mode typing debt that remained (142 errors in 36 files at the time) is re-filed below as its own open deferred item rather than buried inside this resolved entry.

## 2026-09-14 — audit re-file: mypy strict-mode typing debt

- Untracked anywhere else in `.planning/`; replaces the resolved "mypy cannot run" item above. As of 2026-09-14 `uv run mypy src/sif` reports 140 errors in 36 files (76 checked); top error codes type-arg, no-any-return, attr-defined; hottest files search/rerank.py, indexing/watcher.py, mcp/handlers.py, embedding/manager.py. Pre-existing strict-mode typing debt, unrelated to phase 03 scope.
  Disposition: tracked backlog — scheduling a dedicated typing-hardening phase is a future `/gsd-phase` decision; until then this item stays open by design so the audit keeps surfacing it.
