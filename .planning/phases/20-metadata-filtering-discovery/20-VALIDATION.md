---
phase: "20"
slug: "metadata-filtering-discovery"
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-11-15"
validated: "2026-11-18"
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded from `20-RESEARCH.md` §"Validation Architecture"; task IDs resolved from the
> executed plans and audited 2026-11-18 (all automated commands grounded and green).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (PATH), pytest-asyncio, pytest-cov |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (`--cov=src/sif`, `fail_under=90`); no separate `pytest.ini` |
| **Quick run command** | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/core/test_filters.py tests/unit/search/test_filters_sql.py tests/unit/database/test_metadata_values.py -x` |
| **Full suite command** | `env -u FORCE_COLOR NO_COLOR=1 pytest` |
| **Estimated runtime** | ~205 s full suite (measured 2026-11-18: 3233 passed / 1 skipped, 95.03% coverage); 6.3 s for the 956-test targeted set |

---

## Sampling Rate

- **After every task commit:** Run the quick run command
- **After every plan wave:** Run the full suite command
- **Before `/gsd-verify-work`:** Full suite must be green; plus `ruff check src tests`, `ruff format --check src tests`, `ty check src/sif`, and `make docs-generate` with a clean diff on `docs/cli-reference.md` / `docs/configuration.md`
- **Max feedback latency:** ~205 seconds (full suite); < 10 seconds (targeted set measured 2026-11-18)

---

## Per-Task Verification Map

Task IDs resolved from the executed plans; requirement-level contract audited 2026-11-18:

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 20-01 T2 | 20-01 | 1 | FILT-01 | T-20-01/02 | Unknown properties rejected; budgets enforced before recursion; no coercion | unit | `pytest tests/unit/core/test_filters.py -x` | ✅ | ✅ green |
| 20-01 T1 + 20-04 T1/T2 | 20-01,20-04 | 1–2 | FILT-01 | T-20-01/13 | One validator drives CLI + MCP; CLI `ClickException` names operator/field/path; MCP `isError=True`, never `INVALID_PARAMS` | unit | `pytest tests/unit/cli/test_search_filter.py tests/unit/mcp/test_backend.py tests/unit/mcp/test_tools.py -x` | ✅ | ✅ green |
| 20-01 T3 | 20-01 | 1 | FILT-02 | T-20-01 | `path` prefix compiles to a half-open range using `idx_documents_path`; mtime range uses `idx_documents_mtime`; reserved-name shadowing; ordering on `path` is a validation error | unit + plan | `pytest tests/unit/search/test_filters_sql.py -x` | ✅ | ✅ green |
| 20-01 T3 | 20-01 | 1 | FILT-03 | T-20-01 | BM25 plan keeps `MATERIALIZE matched`; predicate in the OUTER WHERE; SQL shape unchanged under `'`, `;`, `--`, `%` values | unit | `pytest tests/unit/search/test_bm25.py tests/unit/search/test_filters_sql.py -x` | ✅ | ✅ green |
| 20-03 T3 | 20-03 | 2 | FILT-03 | T-20-10/12 | `filtered-hybrid ⊆ unfiltered-hybrid ∩ filter-set`; admit-all reproduces the unfiltered page; ~2 % selectivity returns matching docs; filter × collection × pagination composes | integration/property | `pytest tests/integration/test_metadata_filtering.py -x` | ✅ | ✅ green |
| 20-03 T1 | 20-03 | 2 | FILT-03 | T-20-10/11 | Too-selective warning fires (many matches, ceiling hit) and is suppressed (few matches, short page); empty match → empty page on both legs | unit | `pytest tests/unit/search/test_vector.py -x` | ✅ | ✅ green |
| 20-02 T1/T3 | 20-02 | 2 | FILT-04 | T-20-05/06 | Typed rows written on create/update/full-path/metadata-fast-path; numeric compares as number; bool is not number; date-valued key live == backfill; `qmd.metadata` resolves identically to native keys; reserved names shadowed | unit | `pytest tests/unit/database/test_metadata_values.py tests/unit/indexing/test_incremental.py -x` | ✅ | ✅ green |
| 20-02 T2 | 20-02 | 2 | FILT-04 | T-20-08 | Backfill marker written only after a complete pass; interrupt mid-pass is resumable and non-duplicating; fresh DB zero cost; marker survives reopen; never a half-populated store | unit | `pytest tests/unit/database/test_schema.py -x` | ✅ | ✅ green |
| 20-05 T1 | 20-05 | 3 | FILT-05 | T-20-17/18 | Discovery doc counts, per-type split, numeric min/median/max (odd/even, array elements each count), distinct value counts, exact `totalKeys`/`remainingKeys`/`remainingValues`, filter-aware denominator, skipped-key count, match grammar (key/value; exists/all rejected) | unit | `pytest tests/unit/database/test_metadata_values.py -x` | ✅ | ✅ green |
| 20-05 T2/T3 | 20-05 | 3 | FILT-05 | T-20-13/17 | CLI `collection metadata` table/JSON + options; MCP `metadata` registered with input_schema in sync; invalid filter/match → `isError` | unit/integration | `pytest tests/unit/cli/test_collection.py tests/unit/mcp/test_tools.py tests/unit/mcp/test_backend.py -x` | ✅ | ✅ green |
| 20-03 T3 + 20-05 T1 | 20-03,20-05 | 2–3 | FILT-05 | T-20-20 | Discovery never lies: every reported key is filterable, every filterable key appears, a non-indexable key is counted not dropped | integration | `pytest tests/integration/test_metadata_filtering.py -x` | ✅ | ✅ green |
| 20-01…20-05 | all | 1–3 | ALL | T-20-SC | Lint/format/type/docs gates | static/docs | `ruff check src tests && ruff format --check src tests && ty check src/sif && make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Guard inventory (measured 2026-11-18):** 956 targeted tests collected and green in 6.32 s across the 14 files above; full suite 3233 passed / 1 skipped @ 95.03% coverage.

---

## Wave 0 Requirements

- [x] `tests/unit/core/test_filters.py` — new; AST/operator/budget coverage (FILT-01)
- [x] `tests/unit/search/test_filters_sql.py` — new; compiler fragments, plan assertions, injection-shaped values (FILT-02/03)
- [x] `tests/unit/database/test_metadata_values.py` — new; typed rows, canonical derivation, discovery aggregates, backfill (FILT-04/05)
- [x] `tests/integration/test_metadata_filtering.py` — new; real-schema containment invariant, 2 % selectivity, composition, discovery parity (FILT-03/05)
- [x] Extend `tests/unit/search/test_bm25.py`, `test_vector.py`, `test_hybrid.py`; `tests/unit/indexing/test_incremental.py`; `tests/unit/database/test_schema.py`; `tests/unit/cli/test_search.py`, `test_collection.py`; `tests/unit/mcp/test_backend.py`; MCP metadata-tool assertions live in `tests/unit/mcp/test_tools.py` after the Phase 22 restructure
- [x] Fixture support: extend `tests/support/bench.py::build_bench_db` so the 150-document corpus is filterable; `ConceptEmbedder` stays the hermetic embedder
- [x] Framework install: none (pytest / pytest-asyncio present)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions | Verified |
|----------|-------------|------------|-------------------|----------|
| (none) | — | — | — | — |

*All phase behaviors have automated verification. The too-selective notice wording is discretionary; its presence/absence is asserted.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 180s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-11-18 — 12/12 requirement rows covered, 956/956 targeted tests green, 0 gaps, 0 escalated.

## Validation Audit 2026-11-18

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
