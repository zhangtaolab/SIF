
## ResourceWarning in 13-01 idle-checkpoint tests

- **Found during:** 13-02 full-suite run (out of scope — pre-existing)
- **Item:** tests/unit/indexing/test_watcher.py TestIdleCheckpoint leaves an unclosed sqlite3 connection; ResourceWarning under unittest.mock
- **Owning plan:** 13-01 (test hygiene only, no production impact)
  **Status:** resolved
  Resolved 2026-11-11 by quick task 261111-kn2 — TestIdleCheckpoint now closes each test-owned Database after stopping its watcher; the strict ResourceWarning and pytest-unraisable gate passes.
