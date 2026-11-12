---
status: complete
phase: 14-Freshness Floor (Pre-Command Refresh + Staleness Marking)
source: [14-VERIFICATION.md]
started: 2026-11-08T04:35:00Z
updated: 2026-11-08T04:58:59.812Z
---

## Current Test

[testing complete]

## Tests

### 1. D-05 refresh-failure leg — decide accept vs. add exercising test
expected: Decide: accept the flagged (present-but-unexercised) refresh-failure warning path, or add the small exception-injection test the verifier sketched (patch refresh_drifted to raise; assert stderr warning + exit 0 + results still returned).
result: pass
evidence: |
  Resolved by ADDING the exercising test (user delegated verification to the agent:
  "你来验证"). Test `test_refresh_failure_warns_and_search_proceeds` added to
  tests/unit/cli/test_search.py::TestPreSearchRefresh (commit 1062afc). It patches
  `sif.cli.commands.search.refresh_drifted` to raise RuntimeError, then asserts:
  exit_code == 0; "Pre-search refresh failed; searching the current index" on
  stderr; the STALE document ("Heading One") is served while the drifted content
  ("Heading Three") is absent; and a follow-up search without the failure refreshes
  normally ("refreshed 1 files (bm25) before search" + finds the new term).
  Verification: 1 passed (targeted), then full class 124 passed; ruff check +
  ruff format --check + ty check src/sif all green (one amend to fix ARG001
  unused-argument naming, b767529 → 1062afc).
  The flagged prohibition leg is now test-enforced, closing the verifier's
  fail-closed flag.

### 2. SC2 perceived latency on a real knowledge base
expected: Run `sif search <query>` against a real KB with a clean index (no drift) and confirm the pre-command stat walk is imperceptible. SC2's near-zero cost was proven structurally (no lock, no writes, no notice); this is the performance-feel judgment.
result: pass
evidence: |
  Measured by the agent (user delegated) on a representative 3000-document corpus
  (3000 markdown files, 4 nested dirs, ~2-8 paragraphs each, built in /tmp/sif-uat-kb;
  indexed via the real CLI `sif index update`, 3000 docs confirmed in DB).
  Wall-clock, subprocess-level, n=5 per configuration (Apple Silicon, miniconda py3.13):
  - clean index + pre-command check (default): median 1640 ms (min 1611, max 1673)
  - clean index + --no-refresh (control):       median 1535 ms (min 1522, max 1633)
  - PRE-COMMAND WALK DELTA: +105 ms median on 3000 docs — silent (stderr empty,
    n=5), exit 0, no lock file, no notice
  - interpreter/CLI startup baseline (`--help`): ~711 ms; total command time is
    dominated by startup (~0.7 s) + DB open/search/render — the check is ~7% of
    total, below perceptibility for a CLI invocation
  - drift case (1 file edited): search found the NEW term with the stderr notice
    "refreshed 1 files (bm25) before search"; the SECOND search was silent (991 ms)
    and still found the term — real-world confirmation of the CR-01 convergence fix
  - trio sanity on clean index: search/vsearch/query all exit 0; refresh check
    silent on all three (vsearch/query stderr contains only the pre-existing
    embedding-model load INFO logs, unrelated to the check)
  Verdict: +105 ms on a 3000-doc clean index with zero output/lock/write side
  effects satisfies SC2's "near-zero, no perceptible latency" bar; drift refresh
  cost is proportional (1 file, no perceptible add).

## Summary

total: 2
passed: 2
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
