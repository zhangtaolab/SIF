---
phase: 26-anchor-arm-deterministic-cache
plan: 04
subsystem: search
tags: [anchor, fts5, porter, vocabulary-guard, mcp, packaging, lfm-license]

requires:
  - phase: 26-01
    provides: rule anchors, anchor: route, SearchOptions.anchor_terms
  - phase: 26-02
    provides: AnchorResolver, generator/cache term paths, SIF_ANCHOR_* settings
  - phase: 26-03
    provides: --anchor CLI flag, zero-model route, docs-generate zero-diff baseline
provides:
  - BM25Searcher.term_in_index FTS vocabulary probe
  - filter_known_terms / _setting_bool / AnchorResolver._apply_vocab_guard
  - SIF_ANCHOR_VOCAB_GUARD default-off independent A/B wired to resolver and MCP
  - static GGUF packaging guards, Anchor Expansion user docs, LFM license Key Decision
affects: [phase-27-evidence-gate, anchor-evaluation, search-algorithms-docs]

actuals:
  tokens: 34000
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "read-time vocabulary filtering: guard filters terms, never mutates llm_cache rows"
    - "lazy import of BM25Searcher inside filter_known_terms to keep default import graph unchanged"
    - "static packaging guards inspect only git-tracked files (local model dirs out of scope)"

key-files:
  created:
    - tests/unit/search/test_anchor_vocab_guard.py
    - tests/test_packaging_assets.py
  modified:
    - src/sif/search/anchor.py
    - src/sif/search/bm25.py
    - src/sif/mcp/backend.py
    - tests/unit/mcp/test_backend_anchor.py
    - docs/search-algorithms.md
    - docs/changelog.md
    - .planning/PROJECT.md

key-decisions:
  - "Vocabulary guard defaults to False; default anchor set stays byte-identical to the 26-01/26-02 rules baseline (D-16)."
  - "Guard filters at read time across rules/unavailable-latch/cache/generator paths; llm_cache still stores raw terms so the A/B is reproducible."
  - "MCP anchor: applies the same filter in memory only — no resolver, no llm_cache writes, no embedder load."
  - "LFM3 GGUF stays user-supplied; static guards assert no .gguf under src/sif, in pyproject.toml, or tracked by git."
  - "8-cell CI is an external post-push gate; local equivalent gates are recorded here, not conflated with CI."

patterns-established:
  - "Pattern 1: FTS term existence is probed with the same porter-tokenizer MATCH expression used by retrieval."
  - "Pattern 2: experimental switches are bool-typed with non-bool fallback to default (MagicMock-safe)."

requirements-completed: [ANC-05, CTR-03, CTR-04]

coverage:
  - id: D1
    description: "Default-off FTS vocabulary guard filters OOV anchor terms across rules/cache/generator paths"
    requirement: ANC-05
    verification:
      - kind: unit
        ref: "tests/unit/search/test_anchor_vocab_guard.py — 4 probe cases + default byte-identical + cache-path filtering"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_bm25.py tests/unit/search/test_anchor_rules.py tests/unit/search/test_anchor_cache.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "MCP anchor: applies the guard but stays read-only (no cache writes, no embedder)"
    requirement: ANC-05
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_backend_anchor.py — guard on/off options + llm_cache row count 0 + _ensure_embedder uncalled"
        status: pass
    human_judgment: false
  - id: D3
    description: "No GGUF weights packaged or committed; Anchor Expansion docs and LFM license Key Decision ship"
    requirement: CTR-03
    verification:
      - kind: unit
        ref: "tests/test_packaging_assets.py tests/test_docs.py"
        status: pass
      - kind: other
        ref: "grep 'LFM Open License v1.0' docs/search-algorithms.md; grep 'Validated in Phase 26 (CTR-03)' .planning/PROJECT.md"
        status: pass
    human_judgment: false
  - id: D4
    description: "Local full quality gates: pytest+coverage, ty, ruff, docs-generate zero diff, MCP contract, frozen paths"
    requirement: CTR-04
    verification:
      - kind: other
        ref: "uv run --frozen --extra dev --extra embed python -m pytest (see gate results below)"
        status: pass
      - kind: other
        ref: "uv run --frozen --extra dev ty check src/sif; ruff check src tests; ruff format --check src tests; make docs-generate && git diff --exit-code; MCP contract 13 passed; frozen paths zero diff"
        status: pass
    human_judgment: false
  - id: D5
    description: "8-cell CI matrix (external post-push gate, ROADMAP success criterion 5)"
    requirement: CTR-04
    verification: []
    human_judgment: true
    rationale: "CI runs on the remote after push; it cannot be executed locally and is explicitly handed to the orchestrator."

duration: ~20min
completed: 2026-11-28
status: complete
---

# Phase 26: Anchor Arm + Deterministic Cache — Plan 04 Summary

**Default-off FTS vocabulary guard (independent A/B), static no-GGUF packaging guards, LFM-licensed Anchor Expansion documentation, and the Phase 26 local full gate suite.**

## Performance

- **Duration:** ~20 min (including partial-execution reconciliation)
- **Started:** 2026-11-28T06:39Z
- **Completed:** 2026-11-28T07:0xZ
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments
- `BM25Searcher.term_in_index` probes `documents_fts MATCH` with the same porter tokenizer as retrieval; `filter_known_terms` and `AnchorResolver._apply_vocab_guard` drop OOV anchors at read time on all resolver term paths (rules default, unavailable latch, cache hit, generator success) while leaving `llm_cache` contents untouched.
- `SIF_ANCHOR_VOCAB_GUARD` defaults to `False`; with it off, resolver terms equal `derive_rule_anchors(normalize_query(q))` byte-for-byte. MCP `anchor:` applies the same in-memory filter without constructing a resolver, writing `llm_cache`, or loading an embedder.
- `tests/test_packaging_assets.py` asserts no `.gguf` under `src/sif`, none in `pyproject.toml`, and none tracked by git. `docs/search-algorithms.md` gains the English `Anchor Expansion (Experimental, Opt-In)` section (default-off, zero-model rules, local GGUF / remote opt-in, cost+cache, guard deviation, `LFM Open License v1.0` $10M threshold and redistribution obligations, Phase 27 verdict); changelog entry and `.planning/PROJECT.md` Key Decision updated to `Validated in Phase 26 (CTR-03)`.

## Task Commits

1. **Task 1: 词表守卫端到端** - `e23dc065` (feat: default-off FTS vocabulary guard for anchor terms)
2. **Task 2: MCP 守卫接线与只读证据** - `52efe41d` (feat: wire the vocabulary guard into the read-only MCP anchor route)
3. **Task 3: LFM 许可/用户文档、无 GGUF 打包守卫与全量门禁** - (docs/test commit written during close-out)

**Plan metadata:** SUMMARY.md (this file).

_Note: Tasks 1-2 were committed by an interrupted executor at 14:39-14:40 local time; Task 3's docs/test were left uncommitted in the working tree. The safe-resume gate stopped re-dispatch; close-out was completed manually with the user's approval (option 1), preserving the two commits._

## Files Created/Modified
- `src/sif/search/bm25.py` - `term_in_index` FTS vocabulary probe
- `src/sif/search/anchor.py` - `filter_known_terms`, `_setting_bool`, `_apply_vocab_guard` on every resolver return point
- `src/sif/mcp/backend.py` - ANCHOR branch guard filter (in-memory, read-only)
- `tests/unit/search/test_anchor_vocab_guard.py` - probe/default/cache-path tests (new)
- `tests/unit/mcp/test_backend_anchor.py` - MCP guard on/off + read-only assertions
- `tests/test_packaging_assets.py` - static GGUF guards (new)
- `docs/search-algorithms.md` - Anchor Expansion section + LFM license
- `docs/changelog.md` - Unreleased/Added entry
- `.planning/PROJECT.md` - LFM Key Decision `Validated in Phase 26 (CTR-03)`

## Decisions Made
- Guard is a read-time filter, not a cache mutation: the same cached raw terms can be replayed with guard on or off for the Phase 27 A/B.
- Explicit `SearchOptions.anchor_terms` injection bypasses the resolver entirely and is therefore unaffected by the guard (documented as the reproducible evaluation control group).
- 8-cell CI is not locally executable; recorded as an orchestrator post-push gate per the plan.

## Deviations from Plan

### Safe-resume close-out (process deviation, not code deviation)
- **Found during:** `/gsd-execute-phase 26` initialization
- **Issue:** Two 26-04 production commits existed with no SUMMARY.md and an incomplete Task 3 in the working tree (interrupted executor).
- **Fix:** With user approval, closed out manually: verified all gates, committed the remaining Task 3 artifacts, wrote this SUMMARY. No code was re-executed or duplicated.
- **Impact on plan:** None on deliverables; STATE/ROADMAP tracking is brought current by the orchestrator after waves.

### Auto-fixed Issues
None — implementation matched the plan.

---

**Total deviations:** 1 process deviation (safe-resume close-out)
**Impact on plan:** No scope creep; all must-haves verified below.

## Issues Encountered
- `uv run --frozen --extra dev --extra embed` needed to download torch (132 MiB) + scipy/transformers/sklearn/modelscope on first use, taking longer than the local `.venv` fallback. The plan's documented fallback (`.venv/bin/python -m pytest --ignore=tests/unit/inference/test_reranker.py -q`) passed: 3367 passed / 1 skipped / 94.18% coverage; the authoritative `uv --extra embed` run also passed (see gate results).
- The 8-cell CI matrix remains external; the orchestrator must confirm it after push.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- ANC-05 / CTR-03 deliverables complete; CTR-04 local gates green. Phase 27 (Evidence Gate & Verdict) can consume the guard as an independent A/B using the reproducible `SearchOptions.anchor_terms` control path.
- Blocker: none. 8-cell CI must be confirmed post-push before the milestone's success criterion 5 is claimed.

---
*Phase: 26-anchor-arm-deterministic-cache*
*Completed: 2026-11-28*
