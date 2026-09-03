---
status: testing
phase: 03-Embedding & Vector Search
source: [03-VERIFICATION.md]
started: 2026-09-03T04:15:32Z
updated: 2026-09-03T04:15:32Z
---

## Current Test

number: 1
name: Live OpenAI-compatible endpoint check
expected: |
  Set SIF_MODEL_TYPE=openai, SIF_API_BASE=https://<compatible-endpoint>/v1,
  SIF_API_KEY=<key>, and SIF_MODEL_NAME=<the endpoint's model id> (not the shared
  local-model default), then run `sif vsearch <query>` against an indexed collection.
  Embeddings are produced by the remote endpoint (real SDK transport), vector search
  returns semantic results; first run probes and caches the dimension, second run
  reads openai_dim_cache.json without re-probing.
awaiting: user response

## Tests

### 1. Live OpenAI-compatible endpoint check
expected: Remote endpoint produces embeddings via real SDK transport; `sif vsearch` returns semantic results; dimension probed+cached on first run, cache hit (no re-probe) on second.
result: [pending]

### 2. Live ModelScope model download
expected: Set SIF_MODEL_TYPE=modelscope and run `sif embed <file>` with network access — model downloads from modelscope.cn via snapshot_download and produces embeddings usable by vector search.
result: [pending]

### 3. ModelScope interrupted/parallel download resume
expected: Interrupted or parallel download resumes from the local snapshot cache — no restart-from-zero, no corruption (backstop-tagged truth; not unit-verifiable offline).
result: [pending]

### 4. Prohibition review: no text egress from local backends
expected: Document/chunk text never leaves the device unless model_type=openai is explicitly configured; local backends (sentence_transformers, gguf, modelscope) keep all user content on-device, with model-file download as their only network traffic. Verifier LLM-judge verdict is PASS by code inspection (non-authoritative — human confirmation wanted).
result: [pending]

### 5. Prohibition review: no silent backend fallback
expected: When the configured backend fails to load, the failure surfaces as an explicit user-facing error (e.g. ClickException "Failed to load embedding model: ..."), never a silent switch to another backend. Verifier LLM-judge verdict is PASS by code inspection (non-authoritative — human confirmation wanted).
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
