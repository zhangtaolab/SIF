---
status: complete
phase: 12-`sif watch` Foreground MVP
source: [12-VERIFICATION.md]
started: 2026-11-07T11:45:00Z
updated: 2026-11-07T12:05:57.301Z
---

## Current Test

[testing complete]

## Tests

### 1. Foreground watch UX (banner, summary lines, Ctrl-C feel)
expected: Banner readable; one summary line per settled save; `--verbose` lines legible; clean prompt exit.
result: pass
note: "Orchestrator-executed (user delegated: 你来检测). Temp collection + temp DB; create + plain edit + os.replace atomic save coalesced to one `notes: indexed 2 · removed 0 · unchanged 0` line; banner shows roots/depth/debounce; atomic-save content (Atomic v2) in DB; no temp rows (2 rows total); `--verbose` shows `Indexed: third.md`; SIGINT exit 0 with flush"

### 2. Real-editor save storm with `--embed`
expected: With `sif watch --embed` on a small real collection, make 3–4 rapid saves of the same note in a real editor (Vim/Emacs/VSCode), then search for the newest content. Each save storm coalesces to one summary line (no flooding); final content findable via `sif search`; no temp rows indexed.
result: pass
note: "Orchestrator-executed (user delegated: 你来检测). Fresh temp collection; `watch --embed` with 4 saves of the same note inside the 0.5s window (2 plain writes + 1 os.replace atomic + 1 final write) produced exactly ONE `notes: indexed 1 · removed 0 · unchanged 0` line; ModelScope Qwen3-Embedding-0.6B lazy-loaded on first embed work (dim 1024); final content is the top BM25 hit AND a vector hit (score 0.609); only storm.md in documents (no temp rows); SIGINT exit 0"

## Summary

total: 2
passed: 2
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
