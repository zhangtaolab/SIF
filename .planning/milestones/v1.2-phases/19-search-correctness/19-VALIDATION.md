---
phase: "19"
slug: "search-correctness"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-11-15"
validated: "2026-11-18"
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (CI-locked 9.0.3) + pytest-cov 7.1.0 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` + `[tool.coverage.report]` (`fail_under = 90`) |
| **Quick run command** | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search tests/unit/indexing tests/unit/database/test_schema.py -x --no-cov` |
| **Full suite command** | `env -u FORCE_COLOR NO_COLOR=1 pytest` (then `ruff check src tests && ruff format --check src tests && ty check src/sif`) |
| **Estimated runtime** | ~205 s full suite (measured 2026-11-18: 3233 passed / 1 skipped, 95.03% coverage); 6.7 s for the 748-test targeted set |

---

## Sampling Rate

- **After every task commit:** Run the quick run command + `ruff check src tests` + `ruff format --check src tests`
- **After every plan wave:** Run `env -u FORCE_COLOR NO_COLOR=1 pytest` + `ty check src/sif`
- **Before `/gsd-verify-work`:** Full suite green; `make docs-generate` diff clean; the D-12 title-weight gate verdict recorded in the SUMMARY
- **Max feedback latency:** ~205 seconds (full suite); ≤ 10 seconds (targeted set measured 2026-11-18)

---

## Per-Task Verification Map

Task IDs resolved from the executed plans; requirement-level map from `19-RESEARCH.md` §Validation Architecture, audited 2026-11-18:

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 19-01 T1/T2 + 19-02 T1 | 19-01,19-02 | 1–2 | CORR-01 | T-19-01/02 | Frontmatter-only edit becomes searchable; chunks/embeddings preserved; md body byte-identical | unit/integration | `pytest tests/unit/indexing/test_incremental.py -x --no-cov` | ✅ | ✅ green |
| 19-01 T1/T3 | 19-01 | 1 | CORR-01 | T-19-01 | Parser dispatch per extension; YAML `---` whole-file; YAML date metadata storable | unit | `pytest tests/unit/indexing/test_parser.py tests/unit/indexing/test_parser_checksum.py -x --no-cov` | ✅ | ✅ green |
| 19-02 T2 | 19-02 | 2 | CORR-01 | T-19-03/04 | Convention marker migrates per collection; fast path; failure leaves marker | unit/integration | `pytest tests/unit/indexing/test_incremental.py -x --no-cov` | ✅ | ✅ green |
| 19-02 T3 | 19-02 | 2 | CORR-01 | T-19-05 | Watcher embed depth does not duplicate chunks on metadata-only edit | unit | `pytest tests/unit/indexing/test_watcher.py -x --no-cov` | ✅ | ✅ green |
| 19-06 T1 | 19-06 | 4 | CORR-02 | T-19-13/14 | Vector dedup: distinct docs, best chunk, `chunk_matches`, bounded escalation | unit | `pytest tests/unit/search/test_vector.py -x --no-cov` | ✅ | ✅ green |
| 19-06 T2 + 19-07 T1 | 19-06,19-07 | 4–5 | CORR-02 | T-19-15, T-19-16 | Hybrid default one row/doc; `--per-chunk` chunk rows; RRF metadata merge | unit/integration | `pytest tests/unit/search/test_hybrid.py tests/unit/search/test_rrf.py -x --no-cov` | ✅ | ✅ green |
| 19-06 T3 | 19-06 | 4 | CORR-02 | T-19-15 | Chunky-doc regression returns exactly `limit` distinct docs | integration | `pytest tests/integration/test_search_correctness.py -x --no-cov` | ✅ | ✅ green |
| 19-05 T1/T2 | 19-05 | 3 | CORR-03 | T-19-11 | Offset page continuity, past-end empty, global ranks, offset=0 golden | unit/integration | `pytest tests/unit/cli/test_search_pagination.py tests/integration/test_search_correctness.py -x --no-cov` | ✅ | ✅ green |
| 19-05 T1 | 19-05 | 3 | CORR-03 | T-19-10 | BM25 `min_score` before pagination (no holes) | unit | `pytest tests/unit/search/test_bm25.py -x --no-cov` | ✅ | ✅ green |
| 19-05 T3 + 19-07 T2 | 19-05,19-07 | 3–5 | CORR-03 | T-19-12, T-19-17 | MCP offset/per_chunk forwarding + hand-written schema sync | unit | `pytest tests/unit/mcp/test_backend.py -x --no-cov` | ✅ | ✅ green |
| 19-08 T1 | 19-08 | 6 | CORR-04 | T-19-18/19 | Legacy DB detect/rebuild on populated DB; title-only match; vocab+DYM survive; triggers sync; idempotent | unit/integration | `pytest tests/unit/database/test_schema_title_fts.py -x --no-cov` | ✅ | ✅ green |
| 19-08 T2 | 19-08 | 6 | CORR-04 | T-19-20 | Weighted `bm25()` ordering + constant pin + `1.0/1.0 == rank` | unit | `pytest tests/unit/search/test_bm25.py -x --no-cov` | ✅ | ✅ green |
| 19-09 T1 | 19-09 | 7 | CORR-04 | T-19-21/22 | `mtime` index exists on fresh and migrated DBs | unit | `pytest tests/unit/database/test_schema.py -x --no-cov` | ✅ | ✅ green |
| 19-03 T1–T3 + 19-04 T2 | 19-03,19-04 | 2–3 | CORR-05 | T-19-06/07/08/09 | Exactly one attach on every exit path; markers unchanged | unit/integration | `pytest tests/unit/search/test_staleness.py tests/unit/search/test_context_attach.py -x --no-cov` | ✅ | ✅ green |
| 19-08 T3 + 19-09 T3 | 19-08,19-09 | 6–7 | ALL | — | SC1 snapshot, bench snapshot, CSV/JSON shapes updated with rationale | unit | `pytest tests/unit/search/test_hybrid.py tests/unit/search/test_bench_snapshot.py tests/unit/cli/test_search.py -x --no-cov` | ✅ | ✅ green |
| 19-05 T3 + 19-09 T3 | 19-05,19-09 | 3,7 | ALL | — | Generated CLI reference has `--offset`/`--per-chunk`; no diff after generate | docs | `make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md` | ✅ | ✅ green |
| 19-01…19-09 | all | 1–7 | ALL | T-19-SC | Lint/format/type gates | static | `ruff check src tests && ruff format --check src tests && ty check src/sif` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Guard inventory (measured 2026-11-18):** 748 targeted tests collected and green in 6.69 s across the 17 files above; full suite 3233 passed / 1 skipped @ 95.03% coverage.

---

## Wave 0 Requirements

- [x] `tests/integration/test_search_correctness.py` — chunky-doc dedup, offset continuity, per-chunk composition, one-attach spy (CORR-02/03/05)
- [x] `tests/unit/database/test_schema_title_fts.py` — populated legacy DB detect/rebuild, vocab survival, DYM, trigger sync (CORR-04)
- [x] `tests/unit/cli/test_search_pagination.py` — `--offset`/`--per-chunk` flags, global ranks, JSON/CSV fields (CORR-03)
- [x] `tests/unit/indexing/test_watcher.py` new migration/fast-path embed cases (CORR-01)
- [x] Fixtures: `.yaml` `---` (three forms), YAML date, frontmatter-only edit, chunky document (one doc ≥5 chunks), legacy single-column FTS DB builder
- [x] Deterministic benchmark drivers use `ConceptEmbedder`; migration tests use `tmp_path` + real `SchemaManager`
- [x] Framework install: none — pytest/pytest-cov are already locked dev deps

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions | Verified |
|----------|-------------|------------|-------------------|----------|
| Title-weight D-12 per-leg gate verdict | CORR-04 | The gate runs the Phase 18 personal-bench instrument (150-doc scratch index over `tests/fixtures/bench/corpus`, `--bm25-only`); automated tests pin the gate logic, but the accept/reject evidence is a recorded measurement | Record baseline B0 after CORR-01 and B1 after CORR-02; run the title-weight candidates (2–4× band) against B1; confirm the title/known-item leg improves and body/hybrid held-out does not regress beyond the 0.01 tie rule; record weights + deltas + verdict in the SUMMARY | ✅ candidates 2.0/3.0/4.0 all 0 helped / 0 hurt / all unchanged on both held-out legs (title baseline at 1.0 ceiling; body mean 0.900635) → D-12 rejected the band, `_TITLE_WEIGHT = 1.0` pinned; evidence in `.planning/phases/19-search-correctness/bench/d12-verdict.json` |
| Upgrade notice on an existing personal DB | CORR-01 | Requires a real pre-migration database with user content; the automated tests cover the marker mechanics on tmp DBs | Run `sif index update` on a pre-CORR-01 DB; confirm one line "Upgrading index format: reindexing N documents once", fast-path docs keep embeddings, marker clears only after success | ✅ CLI smoke on a temp DB: simulated legacy marker printed the upgrade line exactly once (`Updated: 1`) and the next pass showed `Unchanged: 1` with no notice (19-02-SUMMARY) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-11-18 — 16/16 requirement rows covered, 748/748 targeted tests green, 0 gaps, 0 escalated.

## Validation Audit 2026-11-18

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
