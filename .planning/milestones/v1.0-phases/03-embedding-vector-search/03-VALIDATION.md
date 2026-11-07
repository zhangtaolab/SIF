---
phase: 03
slug: embedding-vector-search
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-16
updated: 2026-09-03
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest tests/unit/embedding/ tests/unit/search/ tests/unit/config/ -x` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/unit/embedding/ tests/unit/search/ tests/unit/config/ -x`
- **After every plan wave:** Run `pytest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | VEC-01 | — | API key not logged | unit | `pytest tests/unit/config/test_settings.py -x` | ✅ | ✅ green |
| 03-01-02 | 01 | 1 | VEC-01 | — | API key not logged | unit | `pytest tests/unit/embedding/test_factory.py -x` | ✅ | ✅ green |
| 03-02-01 | 02 | 1 | VEC-01 | — | N/A | unit | `pytest tests/unit/embedding/test_openai_embedder.py -x` | ✅ | ✅ green |
| 03-03-01 | 03 | 2 | VEC-01 | — | N/A | unit | `pytest tests/unit/database/test_schema.py -x` | ✅ | ✅ green |
| 03-04-01 | 04 | 2 | VEC-02 | — | N/A | unit | `pytest tests/unit/search/test_vector.py -x` | ✅ | ✅ green |
| 03-05-01 | 05 | 2 | VEC-03 | — | N/A | unit | `pytest tests/unit/embedding/test_manager.py -x` | ✅ | ✅ green |
| 03-06-01 | 06 | 3 | VEC-01 | — | N/A | unit | `pytest tests/unit/cli/test_search.py -x` | ✅ | ✅ green |
| 03-07-01 | 07 | 1 | VEC-01 | T-03-01 | api_key never logged/repr'd | unit | `pytest tests/unit/embedding/test_openai_embedder.py -x` | ✅ | ✅ green |
| 03-07-02 | 07 | 1 | VEC-01 | T-03-03 | ragged batch / dim mismatch fail-fast | unit | `pytest tests/unit/embedding/test_openai_embedder.py -x` | ✅ | ✅ green |
| 03-07-03 | 07 | 1 | VEC-01 | T-03-04 | egress strictly opt-in | unit | `pytest tests/unit/embedding/test_factory.py tests/unit/cli/test_index.py -x` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/unit/embedding/test_factory.py` — factory and embedder tests (created 2026-09-03, plan 03-07)
- [x] `tests/unit/embedding/test_openai_embedder.py` — OpenAI embedder tests (created 2026-09-03, plan 03-07)
- [x] `tests/unit/database/test_schema.py` — schema/dimension tests
- [x] `tests/unit/embedding/test_manager.py` — EmbeddingManager refactor tests
- [x] `tests/unit/search/test_vector.py` — vector search batch insert tests
- [x] `tests/unit/config/test_settings.py` — settings validation tests
- [x] Fix stale test imports — resolved by the phase 02/08 test-layout restructure (`test_index_commands.py` → `test_index.py`, etc.); current suite green

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live OpenAI-compatible endpoint | VEC-01 | Requires live API key + endpoint | Set `SIF_MODEL_TYPE=openai`, `SIF_API_BASE=https://<compatible-endpoint>/v1`, `SIF_API_KEY=...`, `SIF_MODEL_NAME=<endpoint-model-id>`, run `sif vsearch <query>` against a real endpoint. Note: `SIF_MODEL_NAME` must be the endpoint's model id (the shared default is a local-model id). Dimension auto-detect caching is covered by unit tests (probe-once/cache-hit/TTL); the live check exercises the real SDK transport only. |
| ModelScope model download and load | VEC-04 | Requires network + large model download | Set `SIF_MODEL_TYPE=modelscope`, run `sif embed <file>`, verify model downloads from ModelScope and produces embeddings |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s (full suite 10.8s)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated

## Validation Audit 2026-09-03

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

Audit performed after gap-closure plan 03-07: the two Wave-0 files declared missing in 03-VERIFICATION.md (`test_factory.py`, `test_openai_embedder.py`) now exist and pass; every requirement-to-task row in the map has an existing, green automated command (full suite: 528 passed, 11 skipped, 0 failed). Two verifications remain Manual-Only by nature (live endpoint, network model download).
