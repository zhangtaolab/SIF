---
status: complete
phase: 03-Embedding & Vector Search
source: [03-VERIFICATION.md]
started: 2026-09-03T04:15:32Z
updated: 2026-09-04T13:48:10Z
---

## Current Test

[testing complete]

## Tests

### 1. Live OpenAI-compatible endpoint check
expected: Remote endpoint produces embeddings via real SDK transport; `sif vsearch` returns semantic results; dimension probed+cached on first run, cache hit (no re-probe) on second.
result: pass
note: |
  Tested by Claude against local LM Studio (http://127.0.0.1:1234/v1,
  text-embedding-snowflake-arctic-embed-l-v2.0, 1024-dim = default SIF_EMBEDDING_DIM).
  Same code path as an internet endpoint (real HTTP + openai SDK, no mocks);
  off-device egress not exercised (that is test 4's opt-in concern).
  Evidence: fresh DB /tmp/sif-uat03; collection add + index update + index embed OK;
  `sif search vsearch "怎么找语义相似的文档"` -> 混合搜索 rank1 0.4303 (no literal overlap);
  `sif search vsearch "数据存在哪里"` -> 数据库配置 rank1 0.4514.
  Dim cache: deleted -> run1 re-probed (detected_at 08:24:17.424739Z) -> run2 unchanged (cache hit).
  Cosmetic observations (not gaps): (a) first-ever run logs misleading
  "Discarding unreadable OpenAI dimension cache" when the cache file is merely absent
  (FileNotFoundError caught by the OSError branch in _write_dim_cache);
  (b) actual command is `sif search vsearch`, truth text's `sif vsearch` is shorthand.

### 2. Live ModelScope model download
expected: Set SIF_MODEL_TYPE=modelscope and run `sif embed <file>` with network access — model downloads from modelscope.cn via snapshot_download and produces embeddings usable by vector search.
result: pass
note: |
  Tested by Claude, fresh DB /tmp/sif-uat03-ms. `sif index embed -c uat03ms` ran
  snapshot_download against modelscope.cn (weights were already cached at
  ~/Library/Caches/sif/Qwen/Qwen3-Embedding-0___6B — cache hit; README.md 16.8k
  fetched live), loaded on mps, dim=1024, 3 chunks embedded.
  `sif search vsearch "怎么找语义相似的文档"` -> 混合搜索 rank1 0.4538 — embeddings usable.
  Caveat: full ~1.2GB cold transfer not observed (cache-served); cold-download mechanics
  are test 3's subject. Cosmetic: sentence-transformers 5.4.1 FutureWarning —
  get_sentence_embedding_dimension renamed (embedder.py:76,243).
  Actual commands: `sif index embed -c <coll>` (truth's `sif embed <file>` is shorthand).

### 3. ModelScope interrupted/parallel download resume
expected: Interrupted or parallel download resumes from the local snapshot cache — no restart-from-zero, no corruption (backstop-tagged truth; not unit-verifiable offline).
result: pass
note: |
  RESUME portion PASSED in the original round (byte-level resume proven, no
  corruption — see previous note). The issue found during this test (G-03-3,
  orphaned vectors) was fixed by plan 03-08 (commits bbdfc0e..fe3d0dd) and
  behaviorally verified by the re-verification round (integration tests re-run
  independently: 4 passed; full suite 554→572 passed).
  LIVE RE-CONFIRMATION (2026-09-04, delegated to Claude): fresh DB, 2 docs,
  LM Studio openai backend (snowflake-arctic-embed-l, dim=1024), 4 embed runs —
  run1 no-force 3 chunks; run2 no-force 0 ("Already embedded"); run3 --force
  3 re-embedded (force now honored); run4 no-force 0. Post-state:
  document_embeddings=3 == document_chunks=3; orphan embeddings 0; 1:1
  chunk_id↔embedding mapping, 3 distinct chunk_ids covered. vsearch ×3 queries
  (n=10) returned exactly 3 rows each, same-doc rows are distinct chunks with
  distinct scores, zero identical (score,title) duplicates — vs original repro
  21 rows/3 chunks, same doc ×7 at identical 0.4538. Gap G-03-3 confirmed
  closed; also covers 03-08 optional D6 spot-check (delete-before-insert shape).
reported: "Resume itself PASSED — byte-level resume proven, no corruption — but repeated `sif index embed` runs pollute the vector store: vsearch returned 混合搜索 ×7 (identical score 0.4538); document_embeddings holds 21 rows with 21 distinct orphan chunk_ids while document_chunks has only 3."
severity: major
note: |
  Download-resume verdict (PASS): SIGKILLed mid-transfer at 44-49% (temp file
  ~/Library/Caches/sif/._____temp/.../model.safetensors, 505M/1.11G). Rerun progress
  bar jumped 0% -> 45% (506M @ "1.52GB/s" = existing bytes counted, not network)
  then continued via network to 100% in 8s — no restart-from-zero. Completed small
  files showed no re-download lines (skipped). Model loaded, dim=1024, 3 chunks
  embedded, vsearch scores bit-identical to pre-interruption run (0.4538) — no
  corruption. Parallelism inherent (modelscope thread pool, "Got 12 files").
  Note: 3 earlier interruption attempts missed because cross-process pkill can't
  see sandboxed background tasks (pgrep found nothing while process was alive);
  self-kill within one shell worked. Attempt rounds also confirmed cold download
  ~13-70s at 85-110MB/s from modelscope.cn CDN.
  NEW DEFECT found during verification (see gap G-03-3): embed_cmd orphans vectors.

### 4. Prohibition review: no text egress from local backends
expected: Document/chunk text never leaves the device unless model_type=openai is explicitly configured; local backends (sentence_transformers, gguf, modelscope) keep all user content on-device, with model-file download as their only network traffic. Verifier LLM-judge verdict is PASS by code inspection (non-authoritative — human confirmation wanted).
result: pass
note: |
  Judgment delegated to Claude by user. Full-repo egress audit: the ONLY user-text
  egress point is OpenAIEmbedder.embed/embed_batch/_probe_dimension
  (embedder.py:390/395/405, client.embeddings.create), reachable only via
  factory.py:34 when model_type==OPENAI (explicit SIF_MODEL_TYPE=openai; default
  is modelscope). snapshot_download (models/download.py:91) and pull.py
  (urlretrieve/hf_hub_download) move model files only (ingress).
  mcp/transports/http.py is a local HTTP server (inbound). No other
  requests/httpx/urlopen hits; no telemetry. Empirical: tests 2/3 modelscope runs
  sent only model-file traffic; note text stayed in local SQLite + local model.

### 5. Prohibition review: no silent backend fallback
expected: When the configured backend fails to load, the failure surfaces as an explicit user-facing error (e.g. ClickException "Failed to load embedding model: ..."), never a silent switch to another backend. Verifier LLM-judge verdict is PASS by code inspection (non-authoritative — human confirmation wanted).
result: pass
note: |
  Judgment delegated to Claude by user. grep: SimpleEmbedder has zero call sites
  (dead fallback, unreachable silently); manager.py contains no try/except or
  fallback. Failure injections: (1) SIF_MODEL_TYPE=huggingface ->
  "Error: Failed to load embedding model: HuggingFace models not yet implemented",
  exit=1; (2) SIF_MODEL_TYPE=openai + dead endpoint (127.0.0.1:9) ->
  "Error: Failed to load embedding model: Connection error." — both explicit,
  neither switched backends. (WR-08 fix confirmed live.)

### 6. CR-01 fix spot-check — edited note re-embeds with fresh content
expected: |
  Edit a real note's content (medium+ edit), run `sif index update` then default
  `sif index embed` (no --force) — the document is re-chunked and re-embedded with
  fresh content (not skipped as stale, not crashed), and vsearch reflects the edit.
  Covers fix(03) 3d307da: invalidation in update_cmd + the FTS5 `documents_fts_update`
  trigger fix in schema.py (FND-06 — direct UPDATE on external-content FTS5 previously
  crashed medium+ edits with "database disk image is malformed"). Covered by +18 new
  regression tests (suite 572 passed); this is the live confirmation.
result: pass
note: |
  LIVE CONFIRMED 2026-09-04 (delegated to Claude), same fixture as test 3 re-run
  (LM Studio openai backend, fresh DB, 2 docs). Medium+ edit on 混合搜索笔记.md
  (mid-sentence change + new ~5-line section on 增量更新/量化/int8). `sif index
  update` exit 0 — no "database disk image is malformed" (FND-06 fix holds);
  PRAGMA integrity_check = ok. `sif index embed` (no --force) embedded 4 chunks —
  NOT skipped as stale; DB shows re-chunked fresh content (edited sentence in
  seq0, new section in seq2); document_embeddings=4 == document_chunks=4,
  orphans 0 (delete-before-insert held through edit path). vsearch "怎么减少
  向量内存占用" → 混合搜索引擎设计 #1 (0.4786, only doc containing new
  section; runner-up 0.3697); regression query unchanged; zero duplicate
  (score,doc) rows. Observation (non-blocking): update reported "Updated: 2"
  and re-chunked/re-embedded the UNCHANGED doc too (数据库配置.md) —
  over-invalidation is an efficiency note only; no stated truth violated.
  Cosmetic: `--json` output embeds raw newlines in content with --full
  (non-strict JSON) and ANSI color codes — machine consumers need
  strict=False + ANSI strip.

### 7. CR-02 fix spot-check (optional) — per-collection failure isolation
expected: |
  A multi-collection embed run where one collection fails leaves the other
  collections' work committed (no rollback-after-success-print; no re-billing of
  remote backends on retry). Covered by unit tests (fix(03) 44425c8: per-collection
  transactions, ClickException raised outside the transaction); live check optional.
result: pass
note: |
  LIVE CONFIRMED 2026-09-04 (delegated to Claude). Deterministic injection:
  fail-later proxy in front of LM Studio (forwards real embeddings; 500s on
  demand), fresh DB, 2 collections (collA_ok 1 doc, collB_bad 1 doc; embed
  order = ORDER BY name so collA_ok first). Phase 1 (proxy allows 1 success):
  collA_ok embedded + committed; collB_bad's request 500-injected → openai SDK
  auto-retried 2× (3 attempts in proxy log) → per-collection rollback
  (collB_bad: 0 chunks/0 embeddings) while collA_ok's commit SURVIVED
  (1 chunk + 1 embedding); success print showed only committed work
  ("1 chunks embedded" — no rollback-after-success); explicit
  "Error: Embedding failed for 1 collection(s): collB_bad", exit code 1.
  Phase 2 (healthy passthrough, retry): collA_ok printed "Already embedded"
  with ZERO proxy requests for its text (billing evidence: phase-2 log has
  exactly 1 request, for collB_bad) — no re-billing; collB_bad embedded,
  exit 0; collA_ok chunk_id unchanged across failure+retry; final state both
  collections 1:1:1 chunk:embedding, orphans 0.
  Observations (non-blocking): (a) openai SDK default retries 500 ×2 — a
  persistently failing backend costs 3 requests per batch before the error
  surfaces; (b) dim probe "." request is billed once per new
  base_url::model key (dim cache keyed by base URL — confirmed by
  openai_dim_cache.json).

## Summary

total: 7
passed: 7
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

- gap_id: G-03-3
  truth: "Repeated `sif index embed` runs (no --force) are idempotent for the vector store — embeddings of re-chunked documents replace the old ones; search returns each chunk once"
  status: resolved
  resolved_by: 03-08-PLAN.md
  resolved_at: 2026-09-04
  reason: 'Original round observed 21 orphaned document_embeddings rows vs 3 live chunks after 7 embed runs; vsearch returned the same document 7 times at identical score.'
  severity: major
  test: 3
  root_cause: "embed_cmd (src/sif/cli/commands/index.py) calls chunk_repo.delete_by_document(doc.id) which deletes only document_chunks rows, then re-chunks (fresh UUIDs) and calls vector_searcher.add_embeddings_batch() which is insert-only — old document_embeddings rows for the deleted chunk_ids are never removed. --force flag is accepted but ignored (force: bool noqa ARG001), so every run re-chunks everything."
  closure: "Closed by plan 03-08 (bbdfc0e..fe3d0dd): VectorSearcher.delete_embeddings_by_document wired as delete-before-insert in the re-chunk branch; --force honored via _needs_embedding chunk-id-set equality; tests/integration/test_embed_idempotency.py reproduces the UAT evidence inverted against real sqlite-vec. Re-verification round independently confirmed (17/17 must-haves). LIVE CONFIRMED 2026-09-04 (test 3 re-run, see test note)."
  artifacts:
    - path: "src/sif/cli/commands/index.py"
      issue: "embed_cmd: delete_by_document without matching vector deletion; add_embeddings_batch insert-only; unused --force param"
    - path: "src/sif/search/vector.py"
      issue: "VectorSearcher has no delete/upsert path for embeddings by chunk_id or document_id"
  missing:
    - "Delete a document's existing document_embeddings rows before inserting re-chunked embeddings (or upsert keyed on chunk_id)"
    - "Honor --force: default should embed only chunks lacking vectors"
  debug_session: ""
