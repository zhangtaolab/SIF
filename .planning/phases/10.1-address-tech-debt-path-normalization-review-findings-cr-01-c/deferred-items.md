## Deferred Items

- Pre-existing `ty check src/sif` diagnostics (17) in files untouched by plan 10.1-01
  status: open
  **What:** `ty check src/sif` reports 17 diagnostics (call-non-callable on optional
  ML imports, `Connection | None` union attribute access in database/connection.py,
  http transport Request/State unions, one `any` annotation in a parameter). None are
  in `src/sif/cli/commands/get.py` or `src/sif/mcp/backend.py` — both files type-check
  clean after this plan's changes.
  **Found during:** Plan 10.1-01 Task 1 verification (post-GREEN gate run).
  **Disposition:** Out of scope per deviation scope boundary (pre-existing, unrelated
  files); recorded here for a future typing-debt pass. Project CLAUDE.md's mandatory
  quality suite (ruff check, ruff format --check, pytest) is green.
