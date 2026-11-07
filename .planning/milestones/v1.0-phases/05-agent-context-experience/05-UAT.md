---
status: complete
phase: 05-agent-context-experience
source: [05-VERIFICATION.md]
started: 2026-11-06T09:15:00Z
updated: 2026-11-06T14:55:00Z
---

## Current Test

number: 1
name: CR-03 disposition — bracket-named targets can never be added (violated flagged prohibition 05-10-P3)
expected: |
  On a real index run `context add path '<dir>/notes [/3].md' 'my note'` (any target containing an
  unmatched Rich closing tag, e.g. [/3] or [/]). Previously (pre-05-12): exit 1 with
  rich.errors.MarkupError and NO row persisted — the confirmation print at context.py:203/212
  interpolated the raw target inside `with db.transaction()`, and Database.transaction() rolled
  back on exception; every retry failed identically. DECIDE: accept as ledger warning or order a
  gap-closure plan — RESOLVED: plan 05-12 ordered and executed the fix (escape() at the three
  display sites + regression tests); live-verified at milestone close.
awaiting: none

## Tests

### 1. CR-03 disposition — bracket-named targets can never be added
expected: Currently exit 1 `MarkupError`, zero rows persisted (rollback inside the open transaction), retries identical. Decide: accept as ledger warning or order a gap-closure plan (escape() at context.py:203/212/236 + one regression test, mirroring 05-10 Task 3).
result: passed
evidence: |
  Resolved by plan 05-12 (CR-03 closed — rich.markup.escape at context.py:216 add confirmation,
  :240 remove print, :286-288 list cells; display-layer only, both write branches stay inside
  with db.transaction()). Live-verified at milestone close 2026-11-06: temp DB, `context add path
  'corpus/[weird] note.md' 'bracket test content'` → exit 0, row persisted, `context list`
  renders the bracket-named target literally (no MarkupError, no rollback). Regression tests
  renamed *_renders_markup_literally per 05-12 (05-10-P3 holds at all three sites).

## Summary

total: 1
passed: 1
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
