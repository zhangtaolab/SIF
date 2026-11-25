---
phase: "19"
slug: "search-correctness"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-11-15"
validated: "2026-11-25"
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

Task IDs resolved from the executed plans; requirement-level map from `19-RESEARCH.md` §Validation Architecture, audited 2026-11-18, corrected 2026-11-25 (five rows added, two rows made to agree with their commands):

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 19-01 T1/T2 + 19-02 T1 | 19-01,19-02 | 1–2 | CORR-01 | T-19-01/02 | Frontmatter-only edit becomes searchable; chunks/embeddings preserved; md body byte-identical | unit/integration | `pytest tests/unit/indexing/test_incremental.py -x --no-cov` | ✅ | ✅ green |
| 19-01 T1/T3 | 19-01 | 1 | CORR-01 | T-19-01 | Parser dispatch per extension; YAML `---` whole-file; YAML date metadata storable | unit | `pytest tests/unit/indexing/test_parser.py tests/unit/indexing/test_parser_checksum.py -x --no-cov` | ✅ | ✅ green |
| 19-02 T2 | 19-02 | 2 | CORR-01 | T-19-03/04 | Convention marker migrates per collection; fast path; failure leaves marker | unit/integration | `pytest tests/unit/indexing/test_incremental.py -x --no-cov` | ✅ | ✅ green |
| 19-02 T3 | 19-02 | 2 | CORR-01 | T-19-05 | Watcher embed depth does not duplicate chunks on metadata-only edit | unit | `pytest tests/unit/indexing/test_watcher.py -x --no-cov` | ✅ | ✅ green |
| 19-06 T1 | 19-06 | 4 | CORR-02 | T-19-13/14 | Vector dedup: distinct docs, best chunk, `chunk_matches`, bounded escalation | unit | `pytest tests/unit/search/test_vector.py -x --no-cov` | ✅ | ✅ green |
| 19-06 T2 + 19-07 T1 | 19-06,19-07 | 4–5 | CORR-02 | T-19-15, T-19-16 | Hybrid default one row/doc; `--per-chunk` chunk rows; RRF metadata merge | unit/integration | `pytest tests/unit/search/test_hybrid.py tests/unit/search/test_rrf.py -x --no-cov` | ✅ | ✅ green |
| 19-06 T2 (rerank rebuild) | 19-06 | 4 | CORR-02 | T-19-14 | Rerank rebuild keeps each row's `chunk_id`/`sequence`/`chunk_matches` (D-02/D-03) through the sort, the threshold and the top_k cut; document-level rows stay chunk-less | unit | `pytest tests/unit/search/test_rerank.py -x --no-cov` | ✅ | ✅ green |
| 19-06 T3 | 19-06 | 4 | CORR-02 | T-19-15 | Chunky-doc regression returns exactly `limit` distinct docs | integration | `pytest tests/integration/test_search_correctness.py -x --no-cov` | ✅ | ✅ green |
| 19-05 T1/T2 | 19-05 | 3 | CORR-03 | T-19-11 | Offset page continuity, past-end empty, global ranks, offset=0 golden | unit/integration | `pytest tests/unit/cli/test_search_pagination.py tests/integration/test_search_correctness.py -x --no-cov` | ✅ | ✅ green |
| 19-05 T1 | 19-05 | 3 | CORR-03 | T-19-10 | BM25 `min_score` before pagination (no holes) | unit | `pytest tests/unit/search/test_bm25.py -x --no-cov` | ✅ | ✅ green |
| 19-05 T3 + 19-07 T2 | 19-05,19-07 | 3–5 | CORR-03 | T-19-12, T-19-17 | MCP offset/per_chunk forwarding + hand-written schema sync | unit | `pytest tests/unit/mcp/test_backend.py -x --no-cov` | ✅ | ✅ green |
| 19-08 T1 | 19-08 | 6 | CORR-04 | T-19-18/19 | Legacy DB detect/rebuild on populated DB; title-only match; vocab+DYM survive; triggers sync; idempotent | unit/integration | `pytest tests/unit/database/test_schema_title_fts.py -x --no-cov` | ✅ | ✅ green |
| 19-08 T2 | 19-08 | 6 | CORR-04 | T-19-20, T-19-23 | Weighted `bm25()` ordering + constant pin + `1.0/1.0 == rank` | unit | `pytest tests/unit/search/test_bm25.py -x --no-cov` | ✅ | ✅ green |
| 19-09 T1 (mtime index) | 19-09 | 7 | CORR-04 | — | `mtime` index exists on fresh and migrated DBs | unit | `pytest tests/unit/database/test_schema.py -x --no-cov` | ✅ | ✅ green |
| 19-09 T1 (MCP startup) | 19-09 | 7 | CORR-04 | T-19-21 | `SearchBackend` construction migrates a pre-title DB without a CLI command, uses the backend's own embedding dimension, and is idempotent | unit | `pytest tests/unit/mcp/test_backend.py tests/unit/database/test_schema.py -x --no-cov` | ✅ | ✅ green |
| 19-09 T2 | 19-09 | 7 | CORR-04 | T-19-22 | Per-leg and per-leg×split noise gates cover exactly the saved legs, partition every record once, and never name a winner for an absent combination | unit | `pytest tests/unit/search/test_personal_bench.py tests/unit/cli/test_eval.py -x --no-cov` | ✅ | ✅ green |
| 19-03 T1–T3 | 19-03 | 2 | CORR-05 | T-19-06/07 | Exactly one attach on every pipeline exit path; markers unchanged | unit/integration | `pytest tests/unit/search/test_staleness.py tests/unit/search/test_context_attach.py -x --no-cov` | ✅ | ✅ green |
| 19-04 T1 (B0 saved run) | 19-04 | 4 | CORR-05 | T-19-09 | A saved run carries its corpus fingerprint and model identity; `--compare` refuses a baseline whose fingerprint differs instead of computing a delta; the stored run holds no `content`/`snippet` | unit | `pytest tests/unit/search/test_personal_bench.py tests/unit/cli/test_eval.py -x --no-cov` | ✅ | ✅ green |
| 19-04 T2 | 19-04 | 3 | CORR-05 | T-19-08 | Direct CLI `search`/`vsearch` and the MCP BM25 fallback each enrich exactly once; the MCP pipeline path does not enrich again | unit | `pytest tests/unit/cli/test_search.py tests/unit/mcp/test_backend.py -x --no-cov` | ✅ | ✅ green |
| 19-08 T3 + 19-09 T3 | 19-08,19-09 | 6–7 | ALL | — | SC1 snapshot, bench snapshot, CSV/JSON shapes updated with rationale | unit | `pytest tests/unit/search/test_hybrid.py tests/unit/search/test_bench_snapshot.py tests/unit/cli/test_search.py -x --no-cov` | ✅ | ✅ green |
| 19-05 T3 + 19-09 T3 | 19-05,19-09 | 3,7 | ALL | — | Generated CLI reference has `--offset`/`--per-chunk`; no diff after generate | docs | `make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md` | ✅ | ✅ green |
| 19-01…19-09 | all | 1–7 | ALL | T-19-SC | Lint/format/type gates | static | `ruff check src tests && ruff format --check src tests && ty check src/sif` | ✅ | ⚠️ green except `ty` |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Guard inventory (measured 2026-11-18):** 748 targeted tests collected and green in 6.69 s across the 17 files above; full suite 3233 passed / 1 skipped @ 95.03% coverage.

**Guard inventory (measured 2026-11-25):** 1000 targeted tests collected and green in 21.36 s across the 20 files cited above — the 2026-11-18 set plus `test_rerank.py` (18), `test_personal_bench.py` (159) and `test_eval.py` (75); full suite 3263 passed / 1 skipped @ 95.12% coverage.

**Gate note (2026-11-25 re-audit):** `ruff check src tests` and `ruff format --check src tests` are green. `ty check src/sif` exits 1 locally with 10 diagnostics: `src/sif/embedding/embedder.py` (5), `src/sif/models/download.py` (1) and `src/sif/search/rerank.py` (4). `rerank.py` is a file Phase 19 touched (`3946b3f1`, plan 19-06 Task 2), but none of its four diagnostics is on a Phase 19 line: all sit on reranker-backend lines blamed to 2026-04-20 and 2026-09-17, and the same four are present in the tree before Phase 19 began (`999ab9a6`, the parent of its first task commit), so the phase introduced none. The same 10 appear at `b817ebb` in the same three files; only line numbers in `embedder.py` and `download.py` shifted. They are third-party-type diagnostics in a local environment whose `transformers` 4.57.6, `huggingface-hub` 0.36.2 and `torch` 2.7.1 differ from the locked 5.5.4, 1.10.2 and 2.14.1. CI's `Type check` step is not type-checking evidence: its lint job installs `--extra dev` only and `[tool.ty.rules]` sets `import-not-found = "ignore"`, so the third-party symbols behind these diagnostics are unresolved there. Not a Phase 19 regression and not a requirement-coverage gap.

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
| Title-weight D-12 per-leg gate verdict | CORR-04 | The gate runs the Phase 18 personal-bench instrument (150-doc scratch index over `tests/fixtures/bench/corpus`, `--bm25-only`); automated tests pin the gate logic, but the accept/reject evidence is a recorded measurement | Record baseline B0 after CORR-01 and B1 after CORR-02; run the title-weight candidates (2–4× band) against B1; confirm the title/known-item leg improves and body/hybrid held-out does not regress beyond the 0.01 tie rule; record weights + deltas + verdict in the SUMMARY | ✅ candidates 2.0/3.0/4.0 all 0 helped / 0 hurt / all unchanged on both held-out legs (title baseline at 1.0 ceiling; body mean 0.900635) → D-12 rejected the band, `_TITLE_WEIGHT = 1.0` pinned; evidence in `.planning/milestones/v1.2-phases/19-search-correctness/bench/d12-verdict.json` |
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

**Re-certified:** 2026-11-25 — gap 1 (19-06 T2 / CORR-02) closed by three tests; 21 map rows (17 + 4) at re-certification, of which all 19 pytest rows are green (1000/1000 targeted tests), the docs row is green and the static row is unchanged (`ruff` green, `ty` as in the gate note); 0 open gaps, 0 escalated. A repair later the same day added a fifth row (19-04 T1 (B0 saved run)) to trace T-19-09, so the map now has 22 rows, 20 of them pytest rows, all green.

## Validation Audit 2026-11-18

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

## Validation Audit 2026-11-25

| Metric | Count |
|---|---|
| Gaps found | 1 |
| Resolved | 1 |
| Escalated | 0 |

**Incremental re-audit (2026-11-25, HEAD `1b0cfd6`).** **The delta invalidates nothing.** Four Phase 19-covered test files changed since the 2026-11-18 audit (last committed `b817ebb`), all in one commit, `c95d2cee` (Windows portability):

- `tests/unit/cli/test_search.py` (+6/−2): two title-truncation literals in `TestSearchOutputBranches` relaxed from `"A" * 15` and `"B" * 34` to 10-character prefixes.
- `tests/unit/database/test_repositories.py` (+3/−1): `alias_pair` goes through `tests.support.symlink_or_skip`; a `tzset` skipif on `TestLLMCacheExpiryWR09.test_set_stores_aware_utc_expiry`.
- `tests/unit/mcp/test_backend.py` (+3/−3): `symlink_or_skip` in two document-get alias tests.
- `tests/unit/search/test_context_attach.py` (+7/−1): `alias_pair` through `symlink_or_skip`; a `win32` skipif on `test_normalize_path_unexpandable_tilde_degrades_to_raw_form`.

- **`symlink_or_skip`:** behaves as the `symlink_to` it replaced wherever a symlink can be created, and skips instead of erroring where one cannot. A fifth Phase 19-touched file changed as well: `src/sif/search/rerank.py` at `5f9c0869`, only in `create_reranker`'s cache path; `_sort_and_build_results`, the function Phase 19 changed, is untouched.
- **Changed-file rows:** The MCP row (19-05 T3 + 19-07 T2) passes 93; its two changed tests are document-get alias tests outside the row's claim, and no Phase 19 test in the file uses a symlink. The CORR-05 row (19-03 T1–T3 + 19-04 T2) passes 49, `TestAttachPathContextsRealSQL` 10 of 10 including `test_enrich_results_on_real_db`. The Goldens row (19-08 T3 + 19-09 T3) passes 276. Plan 19-01 Task 2's `tests/unit/database/test_repositories.py`, which no map row cites, passes 31; its Phase 19 class `TestDocumentMetadataCanonicalStorage` takes only `db`. Ten tests in `test_context_attach.py` take `alias_pair`, seven of them in `TestAttachPathContextsRealSQL`, so on a host that cannot create symlinks they now skip instead of failing; the one-attach count does not depend on them, because the spy tests in `test_staleness.py` and `test_enrich_results_composes_both_signals` need no symlink. The CI matrix is Ubuntu and macOS, so no CI cell exercises that skip path.
- **Title-cell widths:** No row relied on the exact widths. The relaxed literals belong to two Phase 10 tests (`788ca426`) that pin title truncation with an ellipsis on the `--line-numbers` surfaces, a behaviour no Phase 19 row claims; `TestPerChunkSurfaces`, the Phase 19 class, is unchanged and asserts no width. The Goldens row runs the two only because it cites `test_search.py` at file level; its claim is decided by `TestHybridSC1PipelineGolden`, `TestHeldoutSnapshotReproduction` and the JSON-shape tests in `TestPerChunkSurfaces` (`test_default_table_annotates_multi_chunk_matches` checks only the `(4 chunk matches)` substring). For what those two tests do decide, the relaxed assertions still decide it: a 10-character prefix is present, the full 55-character title is not, and an ellipsis is. Only the exact cell width is no longer pinned.
- **Rest of the map:** The other 12 pytest rows exit 0 (28, 40, 28, 57, 41, 115, 11, 25, 36, 14, 36 and 46 passed), and the docs row exits 0 with both generated docs byte-identical after regeneration. No map command carries a class or function selector, every cited path exists, and every symbol and test class the rows name is implemented. The union of the 17 cited files is still 748 tests, green in 6.04 s, the same count as 2026-11-18. The nine plan verify-block files no row cites pass as well (31, 28, 4, 32, 159, 75, 15, 15 and 12 passed). Plan 19-03 Task 3's literal `grep -rn '_attach_contexts' src/sif/search` exits non-zero in this working tree only through four stale cpython-312 `.pyc` files; the source has no match.
- **Map notes (first pass; predate the delta; no coverage gap; corrected at Step 6, see below):** The CORR-05 row is attributed to 19-04 T2 as well as 19-03, but its command does not run plan 19-04 Task 2's tests (`TestSingleEnrichmentOwner` in `test_search.py` and `test_backend.py`); they run under the Goldens row and the MCP row. Plan 19-09 Task 2 (per-leg noise gates: `TestPerLegNoiseGates`, `test_eval.py`) and the MCP startup-migration half of 19-09 Task 1 (`TestSchemaInitializationAtStartup`, threat T-19-21) have no row of their own; the first is cited by no row, the second runs under the MCP row. Both follow the requirement-level table in `19-RESEARCH.md` §Validation Architecture and were recorded here uncorrected at the first pass. The Manual-Only D-12 row cited the pre-archive path `.planning/phases/19-search-correctness/bench/d12-verdict.json`; the artifact is at `.planning/milestones/v1.2-phases/19-search-correctness/bench/d12-verdict.json`, and its shape checks pass there (`rejected`, pinned 1.0, candidates 2.0/3.0/4.0).
- **Gap found (open at the first pass; closed at Step 5, see below; predates the delta):** Plan 19-06 Task 2 auto-fix 1 made `_sort_and_build_results` (`src/sif/search/rerank.py:65-70`) copy `chunk_id`, `sequence` and `chunk_matches` into each rebuilt result, so chunk identity survives the reranked pipeline path (CORR-02, D-03). No test targets that behaviour: `test_rerank.py` calls the rebuild seven times with no chunk field on input or output, the real-reranker tests in `tests/unit/inference/test_reranker.py` assert none, and in `test_hybrid.py` the only caller is `_ThresholdRerankSpy`, whose results carry no chunk fields. Removing the three lines in a scratch copy of the tree (this repository untouched) leaves all 565 tests green across the 12 files that cover rerank, hybrid, RRF, vector, context, CLI, MCP and chunk identity. The 19-06 summary verified the fix by its suites staying green, which cannot fail on a regression. Classified MISSING for task 19-06 T2 under CORR-02; suggested test `tests/unit/search/test_rerank.py`, suggested command `pytest tests/unit/search/test_rerank.py -x --no-cov`.
- **Result of the first pass (stopped at the gap gate):** One gap was recorded as open and not filled: the gap-filling step (`gsd-nyquist-auditor`) runs only after the user chooses "Fix all gaps" at the gap gate, and that decision was not available to that run, which stopped there. No test was generated then. `status` and `nyquist_compliant` were left as stamped on 2026-11-18 and were not re-certified by that pass; they follow the decision (see the Step 6 entry below). The one in-place row change of that pass was the `ty` leg of the ALL gate.
- **Full suite:** not re-run locally; 3261 tests collect at HEAD with `pytest` from PATH (9.1.1, `pytest-cov` 7.0.0, miniconda py3.13.9). The four changed files pass 342. Test Matrix run `45522236981` on `a25eb07` (an ancestor of HEAD; `a25eb07..HEAD` differs only under `.planning/`) passed all 9 jobs: 8/8 cells (py3.10–3.13 × Ubuntu/macOS) with 3259 passed, 2 skipped and 95.12% coverage against the enforced 90% floor, plus the lint job.
- **Carried forward, not re-run:** the guard inventory and latency figures dated 2026-11-18, and the Manual-Only rows, which stay as stamped.
- **Step 5 — gap 1 closed (2026-11-25, after the gap gate was answered "Fix all gaps").** The `gsd-nyquist-auditor` work was done inline from its persona (this runtime has no Agent tool). `src/` is untouched: `src/sif/search/rerank.py` is byte-identical to `fee02316`. `TestRebuildChunkIdentity` was added to `tests/unit/search/test_rerank.py`; its 15 earlier tests are unchanged and the file now collects 18:
  - `tests/unit/search/test_rerank.py::TestRebuildChunkIdentity::test_rebuild_keeps_each_rows_chunk_identity_after_reordering` — three rows with distinct, non-zero chunk identities are reordered by the descending sort; each rebuilt row carries the `chunk_id`, `sequence` and `chunk_matches` of its own input row, checked against hand-written expected tuples (one row has `sequence=0`, a real chunk position).
  - `tests/unit/search/test_rerank.py::TestRebuildChunkIdentity::test_rebuild_leaves_document_level_rows_without_chunk_identity` — chunk-less rows on both sides of a chunk row come back `None`/`None`/`0`; identity is neither borrowed from a neighbour nor invented.
  - `tests/unit/search/test_rerank.py::TestRebuildChunkIdentity::test_cross_encoder_rerank_keeps_chunk_identity_of_survivors` — through `CrossEncoderReranker.rerank` with a mocked model, the two rows that survive `relative_threshold=0.5` and `top_k=2` keep their own identity.
  - **Not vacuous.** In a scratch export of `fee02316` (this checkout untouched), deleting the three lines (`src/sif/search/rerank.py:68-70`) turns the suggested command red: `1 failed, 15 passed`, exit 1, `('top', None, None, 0) != ('top', 'chunk-top', 0, 5)`. Run without `-x`, all three new tests fail and the 15 earlier tests pass. The same scratch tree is 18/18 green with the lines present, and the real checkout is 18/18 green at HEAD (`env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search/test_rerank.py -x --no-cov`); `ruff check` and `ruff format --check` pass on the file. A second scratch variant that fabricates identity (`chunk_id or document_id`, `sequence or 0`, `chunk_matches or 1`) fails the document-level test alone (1 failed, 17 passed).
  - Classification: FILLED. No BLOCKER, no WARNING, no escalation, and no debug iteration was needed (the tests passed on their first run; one docstring was shortened to satisfy the line-length lint).
- **Step 6 — map corrections (2026-11-25; every added or changed command was re-run on this tree).**
  - **19-06 T2:** a new row, "19-06 T2 (rerank rebuild)", cites `pytest tests/unit/search/test_rerank.py -x --no-cov` (18 passed). The fusion half of the task stays on the existing "19-06 T2 + 19-07 T1" row.
  - **CORR-05 row:** cite and command now agree. The row is "19-03 T1–T3" (plan 19-03, wave 2, T-19-06/07) with its unchanged command `pytest tests/unit/search/test_staleness.py tests/unit/search/test_context_attach.py -x --no-cov` (49 passed), the pairing `19-RESEARCH.md` gives CORR-05. Plan 19-04 Task 2 has its own row, "19-04 T2" (wave 3, T-19-08), carrying that task's verify command `pytest tests/unit/cli/test_search.py tests/unit/mcp/test_backend.py -x --no-cov` (282 passed), which runs `TestSingleEnrichmentOwner` in both files. T-19-09 (saved-run baseline integrity, plan 19-04 Task 1) is cited by no row after the trim; no map command targets it.
  - **19-09 T2 (per-leg gates):** an existing test covers it, so a row was added and nothing was left as manual-only. "19-09 T2" (T-19-22) cites the task's verify command `pytest tests/unit/search/test_personal_bench.py tests/unit/cli/test_eval.py -x --no-cov` (234 passed; `TestPerLegNoiseGates` holds 4 of them).
  - **MCP startup migration (19-09 Task 1):** `TestSchemaInitializationAtStartup` (5 tests) covers it, so a row was added: "19-09 T1 (MCP startup)" (T-19-21), citing `pytest tests/unit/mcp/test_backend.py -x --no-cov` (93 passed). The existing mtime-index row is now "19-09 T1 (mtime index)" with Threat Ref "—": T-19-21 (MCP-only schema startup) and T-19-22 (D-12 verdict) are not the mtime index, and neither threat's tests run under its command, `pytest tests/unit/database/test_schema.py -x --no-cov` (46 passed).
  - **Manual-Only D-12 row:** now cites `.planning/milestones/v1.2-phases/19-search-correctness/bench/d12-verdict.json`, which exists (`rejected`, pinned 1.0, candidates 2.0/3.0/4.0).
  - No further tests were generated and no other test file was touched.
- **Step 6 — re-certification (2026-11-25).** The map has 21 rows (17 + 4) at this step; a repair later the same day added a fifth (19-04 T1 (B0 saved run)) to trace T-19-09, making 22. All 19 pytest rows are green: their cited files are the 20 in the guard inventory above, 1000 passed in 21.36 s. The docs row is green (`make docs-generate` exits 0 and both generated files are byte-identical). The static row is unchanged: `ruff check src tests` and `ruff format --check src tests` pass, and `ty check src/sif` still exits 1 with the same 10 diagnostics in the same three files (`rerank.py` at lines 273, 406, 413 and 416; the gate note above explains why they are not a Phase 19 regression). Full suite with coverage on this tree: 3263 passed, 1 skipped, 95.12% coverage, 207 s. Frontmatter: `status: validated`, `nyquist_compliant: true`, `validated: "2026-11-25"`.
