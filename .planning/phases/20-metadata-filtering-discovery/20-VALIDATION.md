---
phase: "20"
slug: "metadata-filtering-discovery"
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-15"
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded from `20-RESEARCH.md` §"Validation Architecture". The Per-Task Verification
> Map is populated from the requirement-level map below once the planner assigns
> task IDs; the automated commands are already grounded (paths verified or marked
> Wave 0).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (PATH), pytest-asyncio, pytest-cov |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (`--cov=src/sif`, `fail_under=90`); no separate `pytest.ini` |
| **Quick run command** | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/core/test_filters.py tests/unit/search/test_filters_sql.py tests/unit/database/test_metadata_values.py -x` |
| **Full suite command** | `env -u FORCE_COLOR NO_COLOR=1 pytest` |
| **Estimated runtime** | ~180 seconds (full suite at v1.1 close: 1591 tests) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command
- **After every plan wave:** Run the full suite command
- **Before `/gsd-verify-work`:** Full suite must be green; plus `ruff check src tests`, `ruff format --check src tests`, `ty check src/sif`, and `make docs-generate` with a clean diff on `docs/cli-reference.md` / `docs/configuration.md`
- **Max feedback latency:** 180 seconds

---

## Per-Task Verification Map

Task IDs are assigned by the planner; this table is the requirement-level contract each
task's `<automated>` command must draw from.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | FILT-01 | T-20-01 / T-20-02 | Unknown properties rejected; budgets enforced before recursion; no coercion | unit | `pytest tests/unit/core/test_filters.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | FILT-01 | T-20-01 | One validator drives CLI + MCP; CLI `ClickException` names operator/field/path; MCP `isError=True`, never `INVALID_PARAMS` | unit | `pytest tests/unit/cli/test_search_filter.py tests/unit/mcp/test_backend.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | FILT-02 | — | `path` prefix compiles to a half-open range using `idx_documents_path`; mtime range uses `idx_documents_mtime`; reserved-name shadowing; ordering on `path` is a validation error | unit + plan | `pytest tests/unit/search/test_filters_sql.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | FILT-03 | T-20-01 | BM25 plan keeps `MATERIALIZE matched`; predicate in the OUTER WHERE; SQL shape unchanged under `'`, `;`, `--`, `%` values | unit | `pytest tests/unit/search/test_bm25.py tests/unit/search/test_filters_sql.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | FILT-03 | T-20-03 | `filtered-hybrid ⊆ unfiltered-hybrid ∩ filter-set`; admit-all reproduces the unfiltered page; ~2 % selectivity returns matching docs; filter × collection × pagination composes | integration/property | `pytest tests/integration/test_metadata_filtering.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | FILT-03 | T-20-03 | Too-selective warning fires (many matches, ceiling hit) and is suppressed (few matches, short page); empty match → empty page on both legs | unit | `pytest tests/unit/search/test_vector.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | FILT-04 | T-20-05 | Typed rows written on create/update/full-path/metadata-fast-path; numeric compares as number; bool is not number; date-valued key live == backfill; `qmd.metadata` resolves identically to native keys; reserved names shadowed | unit | `pytest tests/unit/database/test_metadata_values.py tests/unit/indexing/test_incremental.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | FILT-04 | T-20-04 | Backfill marker written only after a complete pass; interrupt mid-pass is resumable and non-duplicating; fresh DB zero cost; marker survives reopen; never a half-populated store | unit | `pytest tests/unit/database/test_schema.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | FILT-05 | T-20-06 | Discovery doc counts, per-type split, numeric min/median/max (odd/even, array elements each count), distinct value counts, exact `totalKeys`/`remainingKeys`/`remainingValues`, filter-aware denominator, skipped-key count, match grammar (key/value; exists/all rejected) | unit | `pytest tests/unit/database/test_metadata_values.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | FILT-05 | T-20-01 | CLI `collection metadata` table/JSON + options; MCP `metadata` registered with input_schema in sync; invalid filter/match → `isError` | unit/integration | `pytest tests/unit/cli/test_collection.py tests/unit/mcp/test_integration.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | FILT-05 | — | Discovery never lies: every reported key is filterable, every filterable key appears, a non-indexable key is counted not dropped | integration | `pytest tests/integration/test_metadata_filtering.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/core/test_filters.py` — new; AST/operator/budget coverage (FILT-01)
- [ ] `tests/unit/search/test_filters_sql.py` — new; compiler fragments, plan assertions, injection-shaped values (FILT-02/03)
- [ ] `tests/unit/database/test_metadata_values.py` — new; typed rows, canonical derivation, discovery aggregates, backfill (FILT-04/05)
- [ ] `tests/integration/test_metadata_filtering.py` — new; real-schema containment invariant, 2 % selectivity, composition, discovery parity (FILT-03/05)
- [ ] Extend `tests/unit/search/test_bm25.py`, `test_vector.py`, `test_hybrid.py`; `tests/unit/indexing/test_incremental.py`; `tests/unit/database/test_schema.py`; `tests/unit/cli/test_search.py`, `test_collection.py`; `tests/unit/mcp/test_backend.py`, `test_integration.py`
- [ ] Fixture support: extend `tests/support/bench.py::build_bench_db` so the 150-document corpus is filterable; `ConceptEmbedder` stays the hermetic embedder
- [ ] Framework install: none (pytest / pytest-asyncio present)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| (none expected) | — | — | — |

*All phase behaviors have automated verification. If the too-selective notice wording needs a human read, keep the assertion on its presence/absence and treat wording as discretionary.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 180s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
