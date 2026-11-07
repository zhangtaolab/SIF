---
status: testing
phase: 12-`sif watch` Foreground MVP
source: [12-VERIFICATION.md]
started: 2026-11-07T11:45:00Z
updated: 2026-11-07T11:45:00Z
---

## Current Test

number: 1
name: Foreground watch UX (banner, summary lines, Ctrl-C feel)
expected: |
  Banner (watched roots, depth mode, debounce interval) is readable; each settled
  save produces exactly one `indexed N · removed M · unchanged K` summary line;
  `--verbose` per-file lines are legible; a single Ctrl-C exits cleanly and promptly.
awaiting: user response

## Tests

### 1. Foreground watch UX (banner, summary lines, Ctrl-C feel)
expected: Run `sif watch` on a real notes collection in a terminal, save a file from a real editor, watch the output for a minute, then press Ctrl-C once. Banner readable; one summary line per settled save; `--verbose` lines legible; clean prompt exit.
result: [pending]

### 2. Real-editor save storm with `--embed`
expected: With `sif watch --embed` on a small real collection, make 3–4 rapid saves of the same note in a real editor (Vim/Emacs/VSCode), then search for the newest content. Each save storm coalesces to one summary line (no flooding); final content findable via `sif search`; no temp rows indexed.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
