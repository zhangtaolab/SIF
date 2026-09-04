---
phase: 04
slug: advanced-search-pipeline
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-17
---

# Phase 04 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` (tool.pytest.ini_options) |
| **Quick run command** | `pytest tests/unit/search/ -x --ignore=tests/unit/search/test_bm25.py --ignore=tests/unit/search/test_hybrid.py` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/unit/search/ -x --ignore=tests/unit/search/test_bm25.py --ignore=tests/unit/search/test_hybrid.py`
- **After every plan wave:** Run `pytest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | SRCH-01 | T-04-01 / — | Cross-encoder reranking produces reordered results | unit | `pytest tests/unit/inference/test_reranker.py -x` | ✅ | ✅ green |
| 04-02-01 | 02 | 1 | SRCH-02 | T-04-02 / — | Query expansion returns expanded variants | unit | `pytest tests/unit/inference/test_query_expander.py -x` | ✅ | ✅ green |
| 04-03-01 | 03 | 2 | SRCH-03 | T-04-03 / — | `lex:` prefix routes to BM25 only | integration | `pytest tests/integration/test_search_pipeline.py -x` | ✅ | ✅ green |
| 04-04-01 | 04 | 2 | SRCH-04 | T-04-04 / — | `--explain` includes scores dict in JSON output | unit | `pytest tests/unit/search/test_hybrid.py -x` | ✅ | ✅ green |
| 04-05-01 | 05 | 2 | SRCH-05 | T-04-05 / — | `--candidate-limit` caps reranker input | unit | `pytest tests/unit/search/test_hybrid.py -x` | ✅ | ✅ green |
| 04-06-01 | 06 | 2 | SRCH-06 | T-04-06 / — | `--intent` propagates to search pipeline | unit | `pytest tests/unit/search/test_hybrid.py -x` | ✅ | ✅ green |
| 04-07-01 | 07 | 3 | SRCH-07 | T-04-07 / — | Smart snippet extraction scores sentences | unit | `pytest tests/unit/search/test_snippets.py -x` | ✅ | ✅ green |
| 04-08-01 | 08 | 3 | SRCH-08 | T-04-08 / — | `bench` command computes precision@k, recall, MRR | integration | `pytest tests/unit/cli/test_bench.py tests/unit/search/test_benchmark.py -x` | ✅ | ✅ green |
| 04-09-01 | 09 | 3 | CLI-06 | T-04-09 / — | `--min-score` filters results | unit | `pytest tests/unit/search/test_vector.py::TestVectorSearcher::test_search_applies_min_score -x` | ✅ | ✅ green |
| 04-10-01 | 10 | 3 | CLI-07 | T-04-10 / — | `--full` includes document content | unit | `pytest tests/unit/cli/test_search.py -x` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/inference/test_reranker.py` — update for real `CrossEncoder` implementation
- [ ] `tests/unit/inference/test_query_expander.py` — update for real embedding-based expansion
- [ ] `tests/unit/search/test_snippets.py` — NEW: smart snippet extraction
- [ ] `tests/unit/search/test_benchmark.py` — NEW: benchmark metrics
- [ ] `tests/unit/cli/test_bench.py` — NEW: bench CLI command
- [ ] `tests/integration/test_search_pipeline.py` — fix imports (`BM25SearchStrategy` -> `BM25Searcher`)
- [ ] `tests/unit/search/test_bm25.py` — fix imports (`BM25SearchStrategy` -> `BM25Searcher`)
- [ ] `tests/unit/search/test_hybrid.py` — fix imports (`BM25SearchStrategy` -> `BM25Searcher`)
- [ ] `tests/unit/search/test_rrf.py` — fix `RRFFusion(default_k=60)` -> `RRFFusion(k=60)`
- [ ] `pip install -e ".[embed]"` — install sentence-transformers if not available

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | — | — | — |

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-09-04 (retroactive audit)

---

## Validation Audit 2026-09-04

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

All 10 per-task verification commands executed green (101 tests across reranker,
query expander, search pipeline, hybrid, snippets, bench/benchmark, vector
min-score, search CLI). All Wave 0 test files exist on disk.

**Environment note:** tests assert plain CLI output; Rich `Console()` in
`src/sif/cli/commands/search.py` emits ANSI escapes when attached to this
interactive terminal, causing spurious failures (`test_bench_json_output`,
`TestSearchLineNumbers`, `test_query_with_explain`). Run verification suites
with `NO_COLOR=1` in interactive terminals — not a code regression.
