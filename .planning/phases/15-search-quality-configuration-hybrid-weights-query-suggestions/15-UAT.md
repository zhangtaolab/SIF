---
status: complete
phase: 15-Search Quality Configuration (Hybrid Weights + Query Suggestions)
source: [15-VERIFICATION.md]
started: 2026-11-08T11:00:00Z
updated: 2026-11-08T11:26:59.692Z
---

## Current Test

[testing complete]

## Tests

### 1. Suggestion quality on a real personal KB
expected: On the real KB, DYM suggestions are useful; porter-stem display is acceptable; collection-filtered searches may suggest terms from other collections (accepted design); CJK queries yield run-level completions.
result: pass
evidence: |
  Verified by the agent (user delegated: "你来检测") on a representative 1,206-document
  corpus (/tmp/sif-uat15: 1,200 English topic notes + co-occurrence/cross-document
  fixtures + 3 CJK notes; real CLI index):
  - prefix completions: `sif suggest quant` → "quantum"; DYM section "(none)" for a valid prefix ✓
  - zero-result typo: `sif search "quantum machien"` → "No results found. Did you mean: quantum machin?"
    — stem display EXACTLY as the accepted D-06 trade-off ✓
  - CR-01 fix live: `sif search "alphx beta"` (alpha/beta in DIFFERENT docs) → NO suggestion
    (the AND-conjunction probe correctly drops zero-hit variants) ✓
  - CJK run-level: `sif suggest 量子` → 量子计算入门 / 量子计算是一种利用量子力学原理进行计算的技术
    (whole-sentence run as a term — the documented unicode61 run-level trade-off) ✓
  - collection filter: `sif search "quantum machien" -c uat15` → DYM still fires (index-global, accepted) ✓
  Observation (not a failure): the CJK whole-sentence completion reads oddly as a "suggestion";
  matches the accepted run-level design and the RESEARCH A1 disclosure.

### 2. Accept the zero-result-only trigger (CONTEXT D-05)
expected: Confirm the product decision — ROADMAP SC2 says "zero- or low-result", CONTEXT D-05 deliberately narrows to zero-result only. The implementation honors D-05.
result: pass
evidence: |
  The user selected D-05 ("仅零结果（推荐）") during phase-15 discuss-phase — the
  decision was theirs. Implementation verified consistent: single did_you_mean call
  site on the zero-result path only (search.py:249; three early-return hooks).
  ROADMAP SC2's "or low-result" wording is superseded by the later user decision,
  recorded by the plan-checker's advisory so verification does not re-litigate.

### 3. Perceived latency on the real index
expected: Time sif suggest --json on the real KB and compare with sif --help; synthetic measurement showed ≤ ~10 ms core work.
result: pass
evidence: |
  Measured by the agent on the 1,206-doc corpus (n=5 each):
  - suggest --json: median 698.4 ms; suggest --help baseline: median 703.7 ms
  - core-work delta: -5.3 ms (within noise) — the suggestion work is imperceptible
    against the ~700 ms interpreter/CLI startup; SC4's 100 ms budget met with
    >10x headroom on a 20k-term index (verifier's independent run: ≤ ~10 ms).
  - zero-result search WITH DYM: median 782.9 ms (search itself + one DYM pass)

### 4. Security follow-up — /gsd-secure-phase 15
expected: Produce 15-SECURITY.md (threat-model entries from the plans; ASVS L1 audit).
result: pass
evidence: |
  Executed by the agent (secure-phase workflow, State B): 9 threats across the three
  plans (T-15-01..08 + T-15-SC), every mitigation L1-verified against source
  (click IntRange/FloatRange, Pydantic ge/gt, sanitizer-quoted MATCH path,
  metadata-only query_log + parameterized SQL, escape()-after-truncate cells,
  zero-result-only trigger, zero new deps). threats_open: 0. Committed 3f9ec15.

### 5. Terminal rendering of the three Rich sections
expected: sif suggest <prefix> renders the three labeled sections cleanly at terminal width.
result: pass
evidence: |
  Captured at 80 columns: sections render in fixed order (Prefix completions /
  Did you mean / History), each a well-formed Rich table; max ASCII line width 57
  chars. The History section correctly showed a prior query ("quantum machien")
  from this session's earlier searches — the query_log write hook confirmed
  end-to-end. CJK tables widen to fit their content (expected).

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
