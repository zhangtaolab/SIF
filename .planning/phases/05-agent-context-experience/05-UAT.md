---
status: testing
phase: 05-agent-context-experience
source: [05-VERIFICATION.md]
started: 2026-11-06T09:15:00Z
updated: 2026-11-06T09:15:00Z
---

## Current Test

number: 1
name: CR-03 disposition — bracket-named targets can never be added (violated flagged prohibition 05-10-P3)
expected: |
  On a real index run `context add path '<dir>/notes [/3].md' 'my note'` (any target containing an
  unmatched Rich closing tag, e.g. [/3] or [/]). Currently: exit 1 with rich.errors.MarkupError and
  NO row persisted — the confirmation print at context.py:203/212 interpolates the raw target inside
  `with db.transaction()`, and Database.transaction() rolls back on exception; every retry fails
  identically (verifier-reproduced on both create and update branches; update branch rolls back the
  content refresh too). DECIDE: accept as ledger warning (CR-03 stays open in
  05-REVIEW-DISPOSITION.md) or order a gap-closure plan — the fix is escape() at
  context.py:203/212/236 plus one regression test, mirroring 05-10 Task 3.
awaiting: user response

## Tests

### 1. CR-03 disposition — bracket-named targets can never be added
expected: Currently exit 1 `MarkupError`, zero rows persisted (rollback inside the open transaction), retries identical. Decide: accept as ledger warning or order a gap-closure plan (escape() at context.py:203/212/236 + one regression test, mirroring 05-10 Task 3).
result: [pending]

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
