---
status: complete
phase: 18-quality-instrument-personal-bench-rapidfuzz-dym
source: [18-VERIFICATION.md]
started: 2026-11-15T00:00:00Z
updated: 2026-11-14T16:51:47.899Z
---

## Current Test

[testing complete]

## Tests

### 1. P1 — body-leg query excerpt acceptable under the no-document-body-content prohibition
expected: You agree titles/paths/ids/metrics plus the <=10-token synthesized excerpt (WR-05 disclosure) are the intended output.
result: pass

### 2. P2 — remote-provider disclosure plus --bm25-only satisfies the no-personal-data-upload prohibition
expected: No eval-owned upload; disclosure is accurate and visible on stderr and in report notes.
result: pass

### 3. P3 — per-leg and total rejected-query counts are sufficient transparency
expected: No silent query-set shrinkage.
result: pass

### 4. P4 — suppressed group names are listed and replay is labelled stability, never quality
expected: No zero-valued rendering for a suppressed group.
result: pass

### 5. P5 — per-leg rejection counts and the applied budget are always reported
expected: No hidden rejections.
result: pass

### 6. P6 — audit report fields for document content/snippets beyond query strings
expected: Query strings, paths, ids, metrics only.
result: pass

### 7. P7 — review the winner rule and held-out gating
expected: No winner inside noise and no defaults change from tuning results.
result: pass

### 8. P8 — run --compare against a changed corpus
expected: Clear refusal naming both fingerprints; no manufactured delta.
result: pass

### 9. P9 — inspect a saved run file from a real corpus
expected: Only query text/paths/ids/metrics; local cache only; short body excerpt acknowledged.
result: pass

### 10. P10 — feed a malformed saved run to --compare
expected: Clear ClickException naming the field; no traceback and no path opened.
result: pass

### 11. P11 — confirm scorer=fuzz.ratio and cutoff 75.0 on the 0-100 Indel scale, with no WRatio path
expected: Deliberate, documented scorer semantics.
result: pass

### 12. P12 — confirm every displayed suggestion re-queries to at least one hit
expected: No fabricated suggestion.
result: pass

### 13. P13 — confirm the search path never auto-rewrites a user query
expected: Suggestions remain display-only.
result: pass

### 14. Run `sif eval --personal` on a real indexed corpus with >=50 documents, then `--compare` the saved run after re-indexing
expected: Readable per-leg/group table, saved-run path on stderr, and a comparison with CI/winner columns; numbers plausible for the corpus.
result: pass

### 15. Run `sif suggest <first-letter-typo>` on a large indexed corpus
expected: Suggestions appear promptly (measured p50 1.376 ms at 73k terms) and include first-letter-typo corrections.
result: pass

## Summary

total: 15
passed: 15
issues: 0
pending: 0
skipped: 0
blocked: 0

## Evidence

Real-corpus UAT on 60 Markdown documents (EN + 2 ZH), temp DB/cache, `--bm25-only`:

- `sif eval --personal --bm25-only`: exit 0; 60 docs / 50 sampled / 97 queries; NDCG@10 0.9772, Hit@10 1.0000; title 50 accepted, body 47 accepted + 3 overlap-rejected; 2 reported groups + 3 suppressed names; replay `available: false` with the CLI-only bias note; saved path printed on stderr.
- Saved run (`eval-d737ab1d7bfc-*.json`, 49,898 bytes): `version: 1`, `top_k: 10`, `retrieval: bm25`, `corpus` fingerprint/documents/sampled, 97 records with `query/target_doc_id/target_path/leg/language/length_bucket/split/grade/retrieved/retrieved_doc_ids`; no `content`/`snippet`; includes `vec:` and `hyde:` title records without aborting (CR-01 fix verified).
- `--compare` same corpus: exit 0; overall N 97, mean delta +0.0000, 95% CI [0.0000, 0.0000], winner no; noise floor 0.0103; fingerprint match yes; per-group diagnostic table; suppressed names on stderr; compare-mode auto-save path on stderr.
- Changed corpus: `Error: Corpus fingerprint mismatch: saved run has 'd737ab1d7bfc7836', current index has 'd8c4d2c7f0be897f'; refusing to compare different corpora.` (exit 1, no traceback).
- Malformed saved run (100k nested arrays): `Error: Compare failed: Cannot load saved run /tmp/uat-bad.json: JSON is nested too deeply` (exit 1, no traceback).
- `--no-save`: no new saved file (3 before / 3 after).
- `sif suggest resturant` → `restaur`; `sif suggest xuantum` → `quantum`; both re-query to ≥1 hit (`restaur` 1, `quantum` 10); core DYM p50 0.014 ms / max 0.596 ms on this small vocab (large-vocab p50 1.376 ms from the verifier).
- Privacy: no eval-owned upload path; remote-provider disclosure present in code/report notes for `openai`/`modelscope` (UAT ran `--bm25-only`); saved run stores a short body excerpt (WR-05 disclosure) and never a full body.

## Gaps

## Deferred Follow-Ups

- test: 14
  idea: "Comparison per-group diagnostic table ellipsizes headers and numbers at 80 columns; use a compact one-line-per-group layout below ~110 columns or gate the diagnostic table behind --json/--verbose (UI-REVIEW priority fix 2)."
  deferred_at: 2026-11-15
