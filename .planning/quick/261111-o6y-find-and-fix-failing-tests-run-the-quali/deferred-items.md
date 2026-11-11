# Deferred Items — quick-261111-o6y

Out-of-scope discoveries (scope boundary: not caused by this task's changes; not fixed here).

## D-1: Pre-existing caplog cross-test leak in test_watch_cmd.py under .venv batch runs

- **Test:** `tests/unit/cli/test_watch_cmd.py::TestShutdownRoutine::test_shutdown_skips_checkpoint_when_worker_still_busy`
- **Found during:** Task 2 supplemental Rich-15 verification (11 previously-failing files batch under `.venv/bin/python`, FORCE_COLOR=1, `--no-cov`).
- **Symptom:** Fails in the compressed 11-file batch (`assert False` on the caplog "skipping WAL checkpoint" assertion); passes in isolation under both ambient regimes; passes in the full suite under the project baseline interpreter (miniconda base `python`, pytest 9.1.1) in both regimes.
- **Pre-existence proof:** Identical batch at pre-change HEAD 134f0f6 in a scratch worktree shows **61 failed** = the 60 known color failures + this same test. Post-change the batch shows **1 failed, 343 passed** — this task's conftest fix removed exactly the 60 color failures; this one predates the change.
- **Suspected mechanism:** Logging-state leakage from an earlier test in the batch (logger level/propagation on `sif.cli.commands.watch` or a parent) under .venv pytest 9.0.3; the test itself is a pure MagicMock/caplog test with no timing or env dependence. Not color-env related.
- **Why deferred:** Not caused by this task (test-side-only scope: only tests/conftest.py and tests/unit/cli/test_color_hermeticity.py may change); full-suite gates on the baseline interpreter are green in both regimes. Fixing it would require editing test_watch_cmd.py or unrelated logging fixtures — outside this quick task's scope.
- **Suggested follow-up:** A `/gsd-debug` or quick task to isolate the leaking predecessor (bisect the batch order) and reset logger state in the affected fixture.
