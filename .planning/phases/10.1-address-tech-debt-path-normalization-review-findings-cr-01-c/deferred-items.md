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

- Test-side raw `sqlite3.connect` handles leak ResourceWarnings (13 remain after WR-01)
  status: open
  **What:** After plan 10.1-04 converted every production CLI `Database` construction
  to context-manager ownership, full-suite unclosed-database ResourceWarnings dropped
  57 → 13. The remaining 13 come from TEST-side raw sqlite usage, not production code:
  `tests/unit/search/test_bm25.py:281,309` open in-memory `sqlite3.connect` connections
  without `conn.close()`, and `tests/unit/cli/test_collection.py` `_read_collection`
  uses `with sqlite3.connect(...)` (transaction-scoped, does NOT close). ResourceWarning
  fires at GC time, so pytest attributes them to whichever test runs when the interpreter
  collects the old handles (hence the misleading test_pull/test_collection attribution).
  **Found during:** Plan 10.1-04 plan-level verification.
  **Disposition:** Out of scope (test-file debt predating this plan; production modules
  verified leak-free — `grep -rn " = Database(index_path)" src/sif/cli` = 0, and the
  lifecycle harness asserts closure). Fix shape if taken up: `conn.close()` in bm25
  tests or `contextlib.closing`, and `_read_connection` helpers should close explicitly.
