---
phase: 26
reviewed: 2026-11-28T08:20:00Z
depth: standard
scope_count: 23
findings:
  critical: 0
  warning: 0
  info: 1
status: findings
---

# Phase 26 Code Review

## Summary

Standard-depth review of the 23 changed source/test/doc files in Phase 26 (Anchor Arm + Deterministic Cache). No correctness bug, security vulnerability, or convention violation was found. One INFO observation is recorded about the vocabulary guard's treatment of multi-word rule anchors. The phase's automated evidence is strong: 3367 passed / 1 skipped at 94.18% coverage (documented local fallback form), `ty`/`ruff`/`ruff format` clean, `make docs-generate` zero diff, MCP wire-transcript contract 13 passed, and 11 frozen paths byte-identical to v1.2.5.

Note: the `gsd-code-reviewer` subagent was dispatched for this review but stalled on an API request with no artifact written; it was stopped by the orchestrator. This report was produced by the orchestrator from independent source inspection and executed probes. Its evidence is recorded below; no unverified claim from the stalled agent is included.

## Findings

### [INFO] Multi-word rule anchors are always dropped when `SIF_ANCHOR_VOCAB_GUARD` is on

**File:** `src/sif/search/bm25.py` (`term_in_index`, `_sanitize_term`), `src/sif/search/anchor.py` (`_PHRASES`, `filter_known_terms`)

**Line:** `src/sif/search/bm25.py:32-44` and `:283-299`; `src/sif/search/anchor.py:55`

**Issue:** `term_in_index` sanitizes the whole term into a single quoted-prefix FTS expression (`"statistical learning"*`), so a multi-word anchor is judged as one phrase rather than as individual tokens. The rule table's phrase anchors (e.g. `"machine learning" -> ("statistical learning", "机器学习")`) therefore never match the FTS vocabulary as a phrase and are dropped when the guard is enabled. An independent probe against a real schema with one seeded document returned: for query `machine learning basics`, `derive_rule_anchors` produced `['statistical learning', '机器学习', 'computer', 'automated', 'training', 'education']`; only `机器学习` survived `filter_known_terms` (the other five were absent from the seed corpus — behavior consistent with the guard's stated purpose, but the phrase ones would be absent from *any* corpus).

**Evidence:** `.venv/bin/python` probe with `SchemaManager(conn).create_all()` + one document: `term_in_index('machine learning') is False`, `term_in_index('culture') is True` (porter stem), `term_in_index('机器学习') is True`, `term_in_index('":*()"') is False`, `_setting_bool` falls back for non-bool values. `tests/unit/search/test_anchor_vocab_guard.py` (4 probe cases) passes.

**Recommendation:** No change required for Phase 26 — the guard is a default-off, independent A/B (D-16) and this is consistent with "drop terms not in the index vocabulary". If Phase 27's held-out evaluation adopts the guard as a default, either tokenize multi-word anchors before probing or document that phrase anchors are intentionally excluded. Recorded here so the A/B's semantics are explicit for the evidence gate.

## Verified Invariants

| # | Invariant | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Default anchor behavior byte-identical to pre-anchor baseline; `SIF_ANCHOR_VOCAB_GUARD` defaults False | ✓ | `src/sif/config/settings.py:266-270` (`default=False`); `src/sif/search/bm25.py:258-280` — with `anchor_terms` empty, `_build_fts_query` returns the plain AND chain; `tests/unit/search/test_anchor_injection.py`, `tests/unit/search/test_bm25.py` pass; 26-04 Task 1 test asserts default resolver terms equal `derive_rule_anchors(normalize_query(q))` byte-for-byte |
| 2 | ANCHOR routing is zero-model: no embedder load, no reranker, no `llm_cache` writes on MCP `anchor:` path | ✓ | `src/sif/mcp/backend.py:215-240` — guard filters in memory via lazy `filter_known_terms`, returns `_lexical_route`; `tests/unit/mcp/test_backend_anchor.py` asserts `llm_cache` row count 0 and `_ensure_embedder` never called (guard on and off); `src/sif/cli/commands/search.py` route-first ANCHOR path verified by 26-03 tests |
| 3 | No `.gguf` assets in `src/sif` or `pyproject.toml`, none committed | ✓ | `tests/test_packaging_assets.py` (3 static guards) passes; `git ls-files -- '*.gguf'` empty; `.venv/bin/python -m pytest tests/test_packaging_assets.py tests/test_docs.py -q --no-cov` → 26 passed |
| 4 | MCP schema unchanged: 7 tools, 5 goldens, no new request fields; frozen paths zero diff from v1.2.5 | ✓ | `git diff --exit-code v1.2.5..HEAD --` (11 frozen paths incl. `pyproject.toml`, `uv.lock`, `protocol.py`, `tools.py`, 5 goldens) → empty; MCP contract `13 passed` in `0.53s` |
| 5 | Docs contain no bare `sif search <query>` | ✓ | `tests/test_docs.py` → 23 passed; all CLI examples use `sif search query ...` |
| 6 | `term_in_index` handles porter stems and CJK correctly | ✓ | Independent probe: `culture`/`cultures` → True (stem), `机器学习` → True (single CJK token), fabricated term and pure metacharacters → False; `tests/unit/search/test_anchor_vocab_guard.py` passes |
| 7 | Cache/generator fail-open, budget/timeout guards, remote opt-in disclosure | ✓ | `src/sif/search/anchor.py:425-444` — one-time stderr warning per remote `base_url` naming where query text is sent (D-15); `AnchorResolver` fail-open + `SIF_ANCHOR_MAX_CALLS` budget and `SIF_ANCHOR_TIMEOUT_MS` deadline in 26-02/26-03, covered by `tests/unit/search/test_anchor_cache.py`, `test_anchor_generator.py`, `test_settings_anchor.py`; `SIF_ANCHOR_BACKEND` restricted to `{rules, gguf, openai}` at `anchor.py:274` |

## Out of Scope / Limitations

- The authoritative `uv run --frozen --extra dev --extra embed python -m pytest` full suite did not complete locally (slow mirror, torch 132 MiB download); the plan's documented `--ignore=tests/unit/inference/test_reranker.py` fallback passed. 8-cell CI remains the external post-push gate — see `26-04-SUMMARY.md`.
- `docs/changelog.md`, `docs/cli-reference.md`, `docs/configuration.md`, `docs/search-algorithms.md` were reviewed for correctness of claims and doc conventions, not re-executed.
- The `sif` MCP server was disconnected this session; MCP behavior was verified through unit/contract tests, not a live server.
- This is a read-only review — no source changes were made.
