---
phase: "19"
slug: "search-correctness"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-15"
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
| **Estimated runtime** | ~100–120 s full suite (Phase 18 measured ~100 s at HEAD `b6078d3`; re-measure at Wave 0); ≤ 20 s targeted (estimate) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command + `ruff check src tests` + `ruff format --check src tests`
- **After every plan wave:** Run `env -u FORCE_COLOR NO_COLOR=1 pytest` + `ty check src/sif`
- **Before `/gsd-verify-work`:** Full suite green; `make docs-generate` diff clean; the D-12 title-weight gate verdict recorded in the SUMMARY
- **Max feedback latency:** ~120 seconds (full suite); ≤ 20 seconds (targeted)

---

## Per-Task Verification Map

Task IDs assigned at execution time; requirement-level map from `19-RESEARCH.md` §Validation Architecture, audited 2026-11-15:

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| CORR-01-* | TBD | TBD | CORR-01 | TBD at planning | Frontmatter-only edit becomes searchable; chunks/embeddings preserved; md body byte-identical | unit/integration | `pytest tests/unit/indexing/test_incremental.py -x --no-cov` (new cases) | ✅ extend | ⬜ pending |
| CORR-01-* | TBD | TBD | CORR-01 | TBD at planning | Parser dispatch per extension; YAML `---` whole-file; YAML date metadata storable | unit | `pytest tests/unit/indexing/test_parser.py tests/unit/indexing/test_parser_checksum.py -x --no-cov` | ✅ extend/replace checksum contract | ⬜ pending |
| CORR-01-* | TBD | TBD | CORR-01 | TBD at planning | Convention marker migrates per collection; fast path; failure leaves marker | unit/integration | `pytest tests/unit/indexing/test_incremental.py -x --no-cov` (migration cases) | ❌ W0 | ⬜ pending |
| CORR-01-* | TBD | TBD | CORR-01 | TBD at planning | Watcher embed depth does not duplicate chunks on metadata-only edit | unit | `pytest tests/unit/indexing/test_watcher.py -x --no-cov` (new) | ❌ W0 | ⬜ pending |
| CORR-02-* | TBD | TBD | CORR-02 | TBD at planning | Vector dedup: distinct docs, best chunk, `chunk_matches`, bounded escalation | unit | `pytest tests/unit/search/test_vector.py -x --no-cov` (new real-vec0) | ✅ extend | ⬜ pending |
| CORR-02-* | TBD | TBD | CORR-02 | TBD at planning | Hybrid default one row/doc; `--per-chunk` chunk rows; RRF metadata merge | unit/integration | `pytest tests/unit/search/test_hybrid.py tests/unit/search/test_rrf.py -x --no-cov` | ✅ extend | ⬜ pending |
| CORR-02-* | TBD | TBD | CORR-02 | TBD at planning | Chunky-doc regression returns exactly `limit` distinct docs | integration | new `tests/integration/test_search_correctness.py` | ❌ W0 | ⬜ pending |
| CORR-03-* | TBD | TBD | CORR-03 | TBD at planning | Offset page continuity, past-end empty, global ranks, offset=0 golden | unit/integration | new `tests/unit/cli/test_search_pagination.py` + integration | ❌ W0 | ⬜ pending |
| CORR-03-* | TBD | TBD | CORR-03 | TBD at planning | BM25 `min_score` before pagination (no holes) | unit | `pytest tests/unit/search/test_bm25.py -x --no-cov` (new) | ✅ extend | ⬜ pending |
| CORR-03-* | TBD | TBD | CORR-03 | TBD at planning | MCP offset/per_chunk forwarding + hand-written schema sync | unit | `pytest tests/unit/mcp/test_backend.py -x --no-cov` (new) | ✅ extend | ⬜ pending |
| CORR-04-* | TBD | TBD | CORR-04 | TBD at planning | Legacy DB detect/rebuild on populated DB; title-only match; vocab+DYM survive; triggers sync; idempotent | unit/integration | new `tests/unit/database/test_schema_title_fts.py` | ❌ W0 | ⬜ pending |
| CORR-04-* | TBD | TBD | CORR-04 | TBD at planning | Weighted `bm25()` ordering + constant pin + `1.0/1.0 == rank` | unit | `pytest tests/unit/search/test_bm25.py -x --no-cov` | ✅ extend | ⬜ pending |
| CORR-04-* | TBD | TBD | CORR-04 | TBD at planning | `mtime` index exists on fresh and migrated DBs | unit | `pytest tests/unit/database/test_schema.py -x --no-cov` | ✅ extend | ⬜ pending |
| CORR-05-* | TBD | TBD | CORR-05 | TBD at planning | Exactly one attach on every exit path; markers unchanged | unit/integration | `pytest tests/unit/search/test_staleness.py tests/unit/search/test_context_attach.py -x --no-cov` (rewrite) | ✅ rewrite | ⬜ pending |
| Goldens | TBD | TBD | ALL | — | SC1 snapshot, bench snapshot, CSV/JSON shapes updated with rationale | unit | `pytest tests/unit/search/test_hybrid.py tests/unit/search/test_bench_snapshot.py tests/unit/cli/test_search.py -x --no-cov` | ✅ update | ⬜ pending |
| Docs | TBD | TBD | ALL | — | Generated CLI reference has `--offset`/`--per-chunk`; no diff after generate | docs | `make docs-generate && git diff --exit-code docs/` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/integration/test_search_correctness.py` — chunky-doc dedup, offset continuity, per-chunk composition, one-attach spy (CORR-02/03/05)
- [ ] `tests/unit/database/test_schema_title_fts.py` — populated legacy DB detect/rebuild, vocab survival, DYM, trigger sync (CORR-04)
- [ ] `tests/unit/cli/test_search_pagination.py` — `--offset`/`--per-chunk` flags, global ranks, JSON/CSV fields (CORR-03)
- [ ] `tests/unit/indexing/test_watcher.py` new migration/fast-path embed cases (CORR-01)
- [ ] Fixtures: `.yaml` `---` (three forms), YAML date, frontmatter-only edit, chunky document (one doc ≥5 chunks), legacy single-column FTS DB builder
- [ ] Deterministic benchmark drivers use `ConceptEmbedder`; migration tests use `tmp_path` + real `SchemaManager`
- [ ] Framework install: none — pytest/pytest-cov are already locked dev deps

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Title-weight D-12 per-leg gate verdict | CORR-04 | The gate runs the Phase 18 personal-bench instrument (150-doc scratch index over `tests/fixtures/bench/corpus`, `--bm25-only`); automated tests pin the gate logic, but the accept/reject evidence is a recorded measurement | Record baseline B0 after CORR-01 and B1 after CORR-02; run the title-weight candidates (2–4× band) against B1; confirm the title/known-item leg improves and body/hybrid held-out does not regress beyond the 0.01 tie rule; record weights + deltas + verdict in the SUMMARY |
| Upgrade notice on an existing personal DB | CORR-01 | Requires a real pre-migration database with user content; the automated tests cover the marker mechanics on tmp DBs | Run `sif index update` on a pre-CORR-01 DB; confirm one line "Upgrading index format: reindexing N documents once", fast-path docs keep embeddings, marker clears only after success |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
