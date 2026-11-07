
## ResourceWarning in 13-01 idle-checkpoint tests

- **Found during:** 13-02 full-suite run (out of scope — pre-existing)
- **Item:** tests/unit/indexing/test_watcher.py TestIdleCheckpoint leaves an unclosed sqlite3 connection; ResourceWarning under unittest.mock
- **Owning plan:** 13-01 (test hygiene only, no production impact)
- **Status:** open
