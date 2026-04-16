---
phase: 03
slug: embedding-vector-search
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-16
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
| 03-01-01 | 01 | 1 | VEC-01 | — | API key not logged | unit | `pytest tests/unit/config/test_settings.py -x` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | VEC-01 | — | API key not logged | unit | `pytest tests/unit/embedding/test_factory.py -x` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 1 | VEC-01 | — | N/A | unit | `pytest tests/unit/embedding/test_openai_embedder.py -x` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 2 | VEC-01 | — | N/A | unit | `pytest tests/unit/database/test_schema.py -x` | ❌ W0 | ⬜ pending |
| 03-04-01 | 04 | 2 | VEC-02 | — | N/A | unit | `pytest tests/unit/search/test_vector.py -x` | ❌ W0 | ⬜ pending |
| 03-05-01 | 05 | 2 | VEC-03 | — | N/A | unit | `pytest tests/unit/embedding/test_manager.py -x` | ❌ W0 | ⬜ pending |
| 03-06-01 | 06 | 3 | VEC-01 | — | N/A | unit | `pytest tests/unit/cli/test_search.py -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/embedding/test_factory.py` — factory and embedder tests
- [ ] `tests/unit/embedding/test_openai_embedder.py` — OpenAI embedder tests
- [ ] `tests/unit/database/test_schema.py` — schema/dimension tests
- [ ] `tests/unit/embedding/test_manager.py` — EmbeddingManager refactor tests
- [ ] `tests/unit/search/test_vector.py` — vector search batch insert tests
- [ ] `tests/unit/config/test_settings.py` — settings validation tests
- [ ] Fix stale test imports in `tests/unit/cli/test_index_commands.py`, `tests/unit/cli/test_search_commands.py`, `tests/unit/cli/test_collection_commands.py`, `tests/unit/search/test_bm25.py`, `tests/unit/search/test_hybrid.py`, `tests/unit/search/test_vector.py`, `tests/unit/indexing/test_chunker.py`, `tests/unit/indexing/test_parser.py`, `tests/integration/test_index_and_search.py`, `tests/integration/test_search_pipeline.py`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| OpenAI dimension auto-detection caching | VEC-01 | Requires live API call | Set `DOCSIFT_MODEL_TYPE=openai`, run `docsift vsearch test`, verify cache file created in `~/.docsift/`, run again and verify no second API dimension probe |
| ModelScope model download and load | VEC-04 | Requires network + large model download | Set `DOCSIFT_MODEL_TYPE=modelscope`, run `docsift embed <file>`, verify model downloads from ModelScope and produces embeddings |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
