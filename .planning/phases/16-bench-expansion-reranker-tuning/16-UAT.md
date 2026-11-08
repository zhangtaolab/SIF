---
status: passed
phase: 16-Bench Expansion + Reranker Tuning
source: [16-VERIFICATION.md]
started: 2026-11-09T00:40:00+08:00
updated: 2026-11-09T00:40:00+08:00
---

## Current Test

number: 1
name: Real-model held-out evidence (EVAL-04)
expected: |
  Run `sif bench tests/fixtures/bench/queries.json --json` with the default real embedding
  model (not the deterministic test embedder). Record model / hardware / date / nDCG@10 /
  Hit@10 / p50 / p95 in the docs/benchmarking.md evidence table — the row is currently
  and honestly "not yet measured" (.planning/WINDOWS.md id 10). The deterministic
  snapshot evidence already shipped; this row is the real-model corroboration.
awaiting: (complete)

## Tests

### 1. Real-model held-out evidence
expected: `sif bench tests/fixtures/bench/queries.json --json` runs against the default real model; metrics recorded in docs/benchmarking.md's evidence table (model, hardware, date, nDCG@10, Hit@10, p50, p95).
result: passed

### 2. Interactive-latency figures on operator hardware (QUAL-05/SC5)
expected: Measure rerank-off vs rerank-on p50/p95 on your machine (e.g. `sif bench tests/fixtures/bench/queries.json --json` and the same with `--rerank`). The off path is structurally zero-cost (test-proven); record the wall-clock reference figure (~500 ms interactive reference expected for the off state).
result: passed

## Summary

total: 2
passed: 2
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
