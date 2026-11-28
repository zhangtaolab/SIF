---
phase: 26-anchor-arm-deterministic-cache
verified: 2026-11-28T08:20:57Z
status: passed
score: 5/5 must-haves verified
covered_files:
  - .planning/PROJECT.md
  - .planning/phases/26-anchor-arm-deterministic-cache/26-01-PLAN.md
  - .planning/phases/26-anchor-arm-deterministic-cache/26-01-SUMMARY.md
  - .planning/phases/26-anchor-arm-deterministic-cache/26-02-PLAN.md
  - .planning/phases/26-anchor-arm-deterministic-cache/26-02-SUMMARY.md
  - .planning/phases/26-anchor-arm-deterministic-cache/26-03-PLAN.md
  - .planning/phases/26-anchor-arm-deterministic-cache/26-03-SUMMARY.md
  - .planning/phases/26-anchor-arm-deterministic-cache/26-04-PLAN.md
  - .planning/phases/26-anchor-arm-deterministic-cache/26-04-SUMMARY.md
  - docs/changelog.md
  - docs/cli-reference.md
  - docs/configuration.md
  - docs/search-algorithms.md
  - scripts/generate_config_ref.py
  - src/sif/cli/commands/search.py
  - src/sif/config/settings.py
  - src/sif/core/models.py
  - src/sif/mcp/backend.py
  - src/sif/search/anchor.py
  - src/sif/search/bm25.py
  - src/sif/search/hybrid.py
  - tests/test_packaging_assets.py
  - tests/unit/cli/test_anchor_flag.py
  - tests/unit/cli/test_search.py
  - tests/unit/config/test_settings_anchor.py
  - tests/unit/mcp/test_backend_anchor.py
  - tests/unit/search/test_anchor_cache.py
  - tests/unit/search/test_anchor_generator.py
  - tests/unit/search/test_anchor_injection.py
  - tests/unit/search/test_anchor_rules.py
  - tests/unit/search/test_anchor_vocab_guard.py
  - tests/unit/search/test_bm25.py
  - tests/unit/search/test_hybrid.py
covered_digest: "v4:sha256:4c4b746b03abe50b99e806414f43fbc4cb5494879aba809c1cbc54d34ee8c8e8"
behavior_unverified: 1
overrides_applied: 0
---

# Phase 26: Anchor Arm + Deterministic Cache — Verification Report

**Phase Goal:** 交付默认关闭、可缓存、失败回退的 `anchor:` 检索臂与本地可选生成器，不新增 runtime 依赖、不动 MCP schema。
**Verified:** 2026-11-28T08:20:57Z
**Status:** passed
**Re-verification:** No — initial verification
**Fingerprint:** `v4:sha256:4c4b746b03abe50b99e806414f43fbc4cb5494879aba809c1cbc54d34ee8c8e8` (computed by `gsd_run query verification.fingerprint .planning/phases/26-anchor-arm-deterministic-cache <files>`; the 9 PLAN/SUMMARY files were added automatically by the verb).

All claims below were re-derived by independently reading source files, running single-named behavioral tests, running the full local suite, and executing independent probes. SUMMARY.md / orchestrator numbers were treated as claims, not evidence.

## Goal Achievement

The phase goal is met locally: a default-off, cacheable, fail-open `anchor:` retrieval arm and an optional local generator exist as real, wired code; no runtime dependency was added and the MCP schema is untouched. The one open item (8-cell CI) is an explicitly post-push external gate (ROADMAP SC 5 / PLAN 26-04 must-have: "8-cell CI 不是本计划可本地执行的门禁；由 orchestrator 在 push 后确认"). It is recorded as DEFERRED / behavior-unverified, never as a pass; it does not block conclusion of the local phase goal because the plan and CONTEXT.md deliberately hand it to the post-push orchestrator and the authoritative `--extra embed` suite cannot be produced in this environment.

### Observable Truths

Must-haves were merged from ROADMAP success criteria 1-5 (contract, non-negotiable) with the four PLAN `must_haves.truths` blocks and key links/prohibitions (detail, additive). The 5 roadmap SCs are the scored truths; plan truths/prohibitions were each checked as supporting evidence (see tables below).

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `sif search query --anchor` / `anchor:` prefix triggers anchor-enhanced BM25; anchors enter only the BM25 leg, snippets/highlights use the original query; off-flag behavior byte-identical to v1.2.5 with zero construction / zero model load (ROADMAP SC 1; ANC-01/02/03/04) | ✓ VERIFIED | `src/sif/core/models.py:92` (`ANCHOR`), `:393` (`anchor_terms=None`); `src/sif/search/hybrid.py:43-49` (single shared `PREFIX_ROUTES` incl. `anchor:`), `:384-394` (ANCHOR = one `self.hybrid.bm25.search` leg, `replace(options, anchor_terms=...)`), `:524-537` (snippets use `parsed_query`), `:559-575` (`_resolve_anchor` lazy import), `:584-596` (first-prefix-only parse); `src/sif/search/bm25.py:259-281` (OR-alternative `_build_fts_query`, `if not anchor_terms: return base`), `:210-214` (highlight uses original `query`); `src/sif/mcp/backend.py:34` (imports shared `PREFIX_ROUTES`), `:206-235` (`_prefix_route` ANCHOR branch), `:537-545` (prefix-first, before `_ensure_embedder` at :547); `src/sif/cli/commands/search.py:1267-1322` (route-first: ANCHOR sets `manager=None/embedder=None`, no `EmbeddingManager.from_settings`, injects `AnchorResolver`; off-path unchanged). Independent probe: default path does NOT import `sif.search.anchor`; `_build_fts_query` literals for default/`[]`/`None`/phrase/metachar byte-checked; `_split_query_prefix("anchor:lex:foo")==("lex:foo", ANCHOR)`. 318 targeted tests pass incl. `test_anchor_prefix_end_to_end_uses_rules`, `test_highlights_use_the_original_query`, `test_snippets_use_the_original_query_terms`, `test_default_path_does_not_import_the_anchor_module`, `test_anchor_terms_leave_vector_scores_unchanged`, `test_anchor_terms_reach_the_bm25_leg_in_hybrid_mode`. |
| 2 | Repeating one query makes zero generator calls; a 45-config sweep over N queries makes N calls (frozen prompt / greedy / ≤10 terms / dedupe) (ROADMAP SC 2; GEN-01/GEN-02) | ✓ VERIFIED | `src/sif/search/anchor.py:256-272` (`PROMPT_VERSION="anchor.v1"`, `MAX_ANCHOR_TERMS=10`, frozen `PROMPT_TEMPLATE`), `:400-422` (`parse_terms`: strips numbering/bullets, >64 chars / >6 words / pure-punct drop, dedupe, cap), `:370-378` (sha256 key over prompt version/model/backend/normalized query), `:365-367` (`anchor::<backend>::<model_id>` namespace), `:644-681`/`:769-820` (resolve → `LLMCacheRepository.get` miss → one generate → `.set` on success only, `was_in_transaction` observed at entry, commit only own write), `:522-561` (local generator `temperature=0.0/top_k=1/repeat_penalty=1.0` + deadline). Named behavioral test `test_grid_sweep_generates_once_per_query` (uses real `iter_grid()` from `src/sif/search/benchmark.py:363`): `configs==45`, `fake.calls==len(QUERIES)`, `hits==45*N-N`. Also `test_same_resolver_second_resolve_hits_cache`, `test_second_independent_connection_hits_the_committed_row`, `test_prompt_identity_is_frozen`, `test_parse_terms_*` — all passed on independent re-run. |
| 3 | Generator timeout/failure fail-opens to original-query results, no retry storm, user sees the reason; fail-open fallback is reproducible (ROADMAP SC 3; GEN-03) | ✓ VERIFIED | `src/sif/search/anchor.py:672-677` (`_failed` latch → `terms=[]` + `fallback_reason`, no retry), `:783-797` (single `_warn_once`, `terms=[]`, no cache write), `:731-734` (deadline `AnchorGenerationFailed("timeout")` via `StoppingCriteriaList`), `:736-742` (`AnchorBudgetExceeded` hard raise, not swallowed), `:736-742`/`:678`. `src/sif/cli/commands/search.py:1416-1422` (`--explain` stderr `anchor: backend=... fallback=...`, stdout/JSON untouched). Named behavioral tests passed independently: `test_fail_open_matches_lex_and_warns_once`, `test_generation_failure_writes_no_row_and_latches`, `test_budget_exceeded_is_a_hard_failure`, `test_local_generator_deadline_raises_timeout`, `test_expired_cache_row_regenerates`. |
| 4 | No external request unless explicitly opt-in remote backend; remote opt-in discloses query-text egress; vocab guard is an independent A/B (ROADMAP SC 4; GEN-04, ANC-05) | ✓ VERIFIED | `src/sif/search/anchor.py:274` (`_ANCHOR_BACKENDS={rules,gguf,openai}`), `:636-637` (default `rules`), `:430-435` (`_warn_egress_once` per base_url), `:702-715` (openai only when `anchor_backend=openai` AND base/model configured), `:564-613` (stdlib `urllib` POST, injectable transport), `:491-497` (`llama_cpp`/`jinja2` lazy-import only at generator call site), `:725-734` (`_apply_vocab_guard`, `_setting_bool` default False), `:349-362` (`filter_known_terms`); `src/sif/search/bm25.py:283-299` (`term_in_index` porter/CJK probe); `src/sif/mcp/backend.py:224-234` (guard applies in-memory, no cache/embedder). Independent probe confirmed import of `anchor.py` does NOT pull `llama_cpp`/`jinja2`, default-off resolver terms equal `derive_rule_anchors(normalize_query(q))` byte-for-byte, and `term_in_index` porter-stem/CJK/metachar behavior. Named tests passed independently: `test_default_and_remote_fake_paths_open_no_socket`, `test_openai_egress_is_disclosed_once_per_base_url`, `test_vocab_guard_off_keeps_oov_rule_anchors`, `test_vocab_guard_on_drops_oov_rule_anchors_read_only`. Docs `docs/search-algorithms.md:339-346` record default-off, deviation from paper/Phase 25, and impact. |
| 5 | Full pytest ≥90% coverage, `make docs-generate` zero diff, 8-cell CI green; LFM3 GGUF not packaged, `LFM Open License v1.0` $10M threshold + redistribution obligations in user docs & Key Decisions (ROADMAP SC 5; CTR-03/CTR-04) | ✓ VERIFIED (local portion) + DEFERRED (8-cell CI) | Local: full fallback suite `3367 passed / 1 skipped / 94.18% coverage` (independent re-run); `make docs-generate` exit 0 with zero diff on `docs/cli-reference.md`/`docs/configuration.md`; 10/10 `SIF_ANCHOR_*` in `generate_config_ref.py:203-216` and `docs/configuration.md`; `git ls-files -- '*.gguf'` empty; `tests/test_packaging_assets.py` (3 static guards) + `tests/test_docs.py` pass; `docs/search-algorithms.md:348-354` ($10M threshold + redistribution) and `.planning/PROJECT.md:216` (`Validated in Phase 26 (CTR-03)`); frozen paths `git diff --exit-code v1.2.5..HEAD --` (11 paths) empty; MCP contract 13 passed (+ 7 tools, 5 goldens unchanged). **8-cell CI is DEFERRED / behavior-unverified:** `.github/workflows/test-matrix.yml:22-44` runs 2 OS × 4 Python (`--extra embed`) on `push`/`pull_request`; it cannot run locally (authoritative `uv run --frozen --extra dev --extra embed python -m pytest` did not complete — slow mirror / 132 MiB torch) and this branch is `[ahead 51]` with no push. PLAN 26-04 must-have and REQUIREMENTS CTR-04 deliberately defer CI confirmation to the post-push orchestrator. Recorded, never claimed green. |

**Score:** 5/5 roadmap success criteria verified locally (1 has an external/pending sub-item). 1 behavior-unverified (8-cell CI, external post-push gate).

### Deferred Items

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | "8-cell CI 全绿" (ROADMAP SC 5 / CTR-04 external clause) | Post-push orchestrator (not a later milestone phase; Phase 27 is the evidence-gate evaluation, not CI) | `.github/workflows/test-matrix.yml` runs on `push` (2 OS × 4 Python, `uv sync --frozen --extra dev --extra embed`, `uv run --frozen pytest`); PLAN 26-04 must-have: "8-cell CI 不是本计划可本地执行的门禁；由 orchestrator 在 push 后确认"; `26-04-SUMMARY.md` coverage D5 `verification: []`, `human_judgment: true`, rationale "CI runs on the remote after push; it cannot be executed locally and is explicitly handed to the orchestrator." Not matched by any later phase goal/SC (Phase 27 concerns four-arm evaluation), so it is not reclassified as a deferred *phase* item — it stays an external pending gate, reported here for visibility. |

Step 9b conservatively found no later-phase match that would reclassify any gap; the only open item is the externally-deferred CI gate, which by the decision tree does not produce a FAILED truth (the plan explicitly removes it from local scope).

### Advisory (New Scope, Unevidenced)

Not applicable — initial verification (re-verification evidence gate is a no-op on a first pass).

### Required Artifacts

All `must_haves.artifacts` across the four plans were checked at Levels 1-3 (existence, substantive, wired) and Level 4 (data flow) where they render/produce dynamic data. `gsd_run query verify.artifacts` returned `all_passed: true` for 26-01 (4/4), 26-02 (4/4), 26-03 (2/2), 26-04 (5/5); independent reads confirm each is substantive and wired (no orphan/stub).

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/sif/search/anchor.py` | rule table + `derive_rule_anchors` + `AnchorResolution` + generator/resolver/cache/guard | ✓ VERIFIED | 820 lines; top-level stdlib-only + `LLMCacheRepository`; `derive_rule_anchors` pure; `AnchorResolver` real; `filter_known_terms` wired to resolver + MCP. |
| `src/sif/core/models.py` | `SearchType.ANCHOR`, `SearchOptions.anchor_terms` | ✓ VERIFIED | `:92`, `:393`; no `anchor_enabled`/`anchor_mode` switch (D-08). |
| `src/sif/search/hybrid.py` | shared `PREFIX_ROUTES`, ANCHOR single-leg route + resolution metadata | ✓ VERIFIED | `:43-49`, `:384-394`, `:559-575`; `last_anchor_resolution` reset per search (`:365`), never in `SearchResult`. |
| `src/sif/mcp/backend.py` | read-only ANCHOR branch importing shared `PREFIX_ROUTES` | ✓ VERIFIED | `:34`, `:206-235`, `:537-545`. |
| `src/sif/search/bm25.py` | `_build_fts_query` OR injection + `term_in_index` probe | ✓ VERIFIED | `:259-281`, `:283-299`. |
| `src/sif/config/settings.py` | 10 `SIF_ANCHOR_*` fields + validators | ✓ VERIFIED | `:215-270`, `:427-456`; `anchor_vocab_guard` `default=False`. |
| `scripts/generate_config_ref.py` | `Anchor Settings` SECTION | ✓ VERIFIED | `:203-216` lists all 10 fields. |
| `docs/configuration.md` | regenerated config reference | ✓ VERIFIED | 10 `SIF_ANCHOR_*` entries; zero diff after `make docs-generate`. |
| `src/sif/cli/commands/search.py` | `--anchor` flag, route-first zero-model, stderr explain, original-query DYM/history | ✓ VERIFIED | `:1122`, `:1267-1322`, `:1409-1422`. |
| `docs/cli-reference.md` | regenerated CLI reference with `--anchor` | ✓ VERIFIED | `:500`; zero diff after `make docs-generate`. |
| `tests/test_packaging_assets.py` | no-GGUF static guards | ✓ VERIFIED | 49 lines, 3 guards pass. |
| `docs/search-algorithms.md` | Anchor Expansion docs + LFM license | ✓ VERIFIED | `:281-359`. |
| `.planning/PROJECT.md` | LFM Key Decision status | ✓ VERIFIED | `:216` `Validated in Phase 26 (CTR-03)`. |
| 9 new test files | substantive, wired, active | ✓ VERIFIED | 92-461 lines each; 318 targeted tests collected and passed; no disabled/skipped tests on requirement-linked cases. |

### Key Link Verification

`gsd_run query verify.key-links` returned `all_verified: true` for 26-01 (4/4), 26-02 (4/4), 26-03 (3/3), 26-04 (3/3). Independent source reads confirmed each is a real import/call, not just a pattern match.

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/sif/search/hybrid.py` | `src/sif/search/anchor.py` | ANCHOR branch lazy `derive_rule_anchors` + `AnchorResolution` | ✓ WIRED | `hybrid.py:569` function-local import, used at `:575`; no top-level `anchor` import (probe-confirmed default path). |
| `src/sif/search/hybrid.py` | `src/sif/search/bm25.py` | `replace(options, anchor_terms=...)` → BM25 single leg | ✓ WIRED | `hybrid.py:391-392`. |
| `src/sif/mcp/backend.py` | `src/sif/search/hybrid.py` | import shared `PREFIX_ROUTES` | ✓ WIRED | `backend.py:34`, used at `:140`, `:537`. |
| `src/sif/search/anchor.py` | `src/sif/database/repositories.py` | `LLMCacheRepository.get/set` on `llm_cache` | ✓ WIRED | `anchor.py:37`, `:720`, `:800`; cross-connection hit test passed. |
| `src/sif/search/anchor.py` | `src/sif/config/settings.py` | resolver reads 10 anchor settings | ✓ WIRED | `anchor.py:636-742`, `:799` via `_setting_*`; defaults match `settings.py`. |
| `src/sif/search/anchor.py` | `src/sif/search/benchmark.py` | `iter_grid()` sweep call-count | ✓ WIRED | `test_anchor_cache.py:26,155-162` → `benchmark.py:363`. |
| `scripts/generate_config_ref.py` | `docs/configuration.md` | `make docs-generate` | ✓ WIRED | Makefile target re-ran; zero diff. |
| `src/sif/cli/commands/search.py` | `src/sif/search/hybrid.py` | `PREFIX_ROUTES` + `AnchorResolver` injection into `SearchPipeline` | ✓ WIRED | `search.py:45`, `:1275`, `:1390`. |
| `src/sif/cli/commands/search.py` | `src/sif/search/anchor.py` | `AnchorResolver` constructed only on anchor route | ✓ WIRED | `search.py:1317-1319` (function-local). |
| `docs/cli-reference.md` | `src/sif/cli/commands/search.py` | `generate_cli_ref.py` from Click flag | ✓ WIRED | `--anchor` present in both help and generated doc; zero diff. |
| `src/sif/search/anchor.py` | `src/sif/search/bm25.py` | `filter_known_terms` → `term_in_index` | ✓ WIRED | `anchor.py:349-362`. |
| `src/sif/mcp/backend.py` | `src/sif/search/anchor.py` | ANCHOR guard filter (read-only) | ✓ WIRED | `backend.py:224-234`. |
| `.planning/PROJECT.md` | `docs/search-algorithms.md` | same `LFM Open License v1.0` constraint | ✓ WIRED | `:216` / `:351`; both name $10M + redistribution. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `src/sif/search/bm25.py` | `fts_query` / `options.anchor_terms` | real `SearchOptions` from CLI/MCP/pipeline → `derive_rule_anchors` (pure) or `AnchorResolver.resolve` (DB `llm_cache` / generator) | ✓ FLOWING | `:89`, `:259-281`; real FTS MATCH against `documents_fts` (end-to-end test on real schema returns rows). |
| `src/sif/search/anchor.py` | `AnchorResolution.terms` | rules table / generator / `llm_cache` row | ✓ FLOWING | `:644-681`, `:769-820`; cross-process cache row verified by second `sqlite3.Connection`. |
| `src/sif/mcp/backend.py` | `anchor_terms` | `derive_rule_anchors(parsed_query)` (+ optional in-memory guard) | ✓ FLOWING | `:227-233`; no static fallback. |
| `src/sif/cli/commands/search.py` | `pipeline_query`, `anchor_resolution` | user query + `pipeline.last_anchor_resolution` | ✓ FLOWING | `:1271`, `:1403-1404`. |
| `docs/configuration.md` / `docs/cli-reference.md` | generated tables | `Settings` fields / Click flags via scripts | ✓ FLOWING | regenerated with zero diff. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Targeted anchor/BM25/MCP/CLI/config suite | `.venv/bin/python -m pytest <12 files> -q --no-cov` | `318 passed in 2.55s` | ✓ PASS |
| MCP wire/packaging + docs + static guards | `.venv/bin/python -m pytest tests/unit/mcp/test_wire_transcripts.py tests/unit/mcp/test_packaging.py tests/test_docs.py tests/test_packaging_assets.py -q --no-cov` | `39 passed in 0.63s` | ✓ PASS |
| State-transition/cancellation invariants (single named tests) | `pytest <7 named tests> -q --no-cov` | `7 passed in 0.11s` — covers 45-config sweep, expire-and-regenerate, failure latch/no-retry, hard budget, fail-open parity+single warning, no-socket, deadline timeout | ✓ PASS |
| Independent probe: lazy import, FTS literals, single-strip prefix, clean result keys | `.venv/bin/python - <<PY` | PASS | ✓ PASS |
| Independent probe: optional deps, frozen prompt, `parse_terms` bounds | `.venv/bin/python - <<PY` | PASS | ✓ PASS |
| Independent probe: `term_in_index` porter/CJK/metachar, guard survivors, default-off byte-identical | `.venv/bin/python - <<PY` (real `SchemaManager` DB) | PASS | ✓ PASS |
| Full local fallback suite + coverage | `.venv/bin/python -m pytest --ignore=tests/unit/inference/test_reranker.py -q` | `3367 passed, 1 skipped in 187.80s`; `Total coverage: 94.18%` (≥90%) | ✓ PASS |
| `make docs-generate` | `make docs-generate && git diff -- docs/cli-reference.md docs/configuration.md` | exit 0, zero diff | ✓ PASS |
| Ty / ruff | `uv run --frozen --extra dev ty check src/sif`; `.venv/bin/ruff check src tests`; `.venv/bin/ruff format --check src tests` | `All checks passed!` / `All checks passed!` / `249 files already formatted` (all exit 0) | ✓ PASS |
| Frozen contract paths | `git diff --exit-code v1.2.5..HEAD -- <11 paths>` | empty (exit 0) | ✓ PASS |
| No GGUF tracked | `git ls-files -- '*.gguf'` | empty | ✓ PASS |
| 8-cell CI (`--extra embed` full matrix) | GitHub Actions on `push` | NOT run locally; authoritative `uv run --frozen --extra dev --extra embed python -m pytest` could not complete (slow mirror / 132 MiB torch download). Branch `[ahead 51]`, no push. | ⏭ DEFERRED (external post-push gate — not verified, not a local failure) |

### Probe Execution

No `scripts/*/tests/probe-*.sh` probes are declared in the phase's PLAN/SUMMARY or present in the repo; this section is not applicable (the plan's verification is pytest/gate-based, not probe-based).

### Requirements Coverage

All 11 phase-26 requirement IDs from the four PLAN frontmatters are accounted for, cross-referenced against `.planning/REQUIREMENTS.md` (each `[x]` Complete at lines 21-25, 29-32, 46-47 and marked Complete in the phase table at lines 95-105). No orphaned requirements (EVL-01..05 are Phase 27, not this phase; CTR-01/02 are Phase 25). PLAN `requirements` fields: 26-01 `[ANC-01..04]`, 26-02 `[GEN-01..04, CTR-04]`, 26-03 `[ANC-01, GEN-03, CTR-04]`, 26-04 `[ANC-05, CTR-03, CTR-04]`.

| Requirement | Source Plan | Description (REQUIREMENTS.md) | Status | Evidence |
|-------------|------------|-------------------------------|--------|----------|
| ANC-01 | 26-01, 26-03 | `anchor:` prefix or `--anchor` triggers anchor BM25; unused = zero construction/load/cost | ✓ SATISFIED | `SearchType.ANCHOR`, CLI route-first zero-model branch (`search.py:1304-1319`), lazy `anchor` import probe, `test_anchor_route_loads_no_embedder`, `test_default_path_does_not_import_the_anchor_module`. |
| ANC-02 | 26-01 | anchors only in BM25 leg; snippet/highlight use original query | ✓ SATISFIED | `_build_fts_query` OR injection, `bm25.py:210-214` highlight, `hybrid.py:537` snippets, `test_highlights_use_the_original_query`, `test_snippets_use_the_original_query_terms`. |
| ANC-03 | 26-01 | `SearchType.ANCHOR`, `anchor_terms`, two prefix maps synced; settings don't bypass `SearchOptions` | ✓ SATISFIED | single `PREFIX_ROUTES` in `hybrid.py` imported by `backend.py`; no `anchor_enabled`/`anchor_mode` field; `test_prefix_routes_shared_table_has_anchor`, `test_split_query_prefix_strips_only_the_first_prefix`. |
| ANC-04 | 26-01 | `hybrid+anchor` diagnostic arm only, default off, doesn't replace default RRF BM25 | ✓ SATISFIED | default `SearchOptions().anchor_terms is None`; `test_default_options_match_prechange_snapshot`, `test_anchor_terms_reach_the_bm25_leg_in_hybrid_mode`, `test_anchor_terms_leave_vector_scores_unchanged`. |
| ANC-05 | 26-04 | vocab guard as independent A/B, drops OOV terms; default/deviation/impact documented | ✓ SATISFIED | `anchor_vocab_guard` default False (`settings.py:266-270`), `_apply_vocab_guard`, `filter_known_terms`/`term_in_index`, `docs/search-algorithms.md:339-346`, `test_anchor_vocab_guard.py` (4 cases) + MCP guard off/on tests. |
| GEN-01 | 26-02 | frozen versioned prompt, greedy/temp 0, one term/line, ≤10, dedupe; model+prompt frozen before eval | ✓ SATISFIED | `PROMPT_VERSION="anchor.v1"`, `PROMPT_TEMPLATE`, `parse_terms`, `LocalGGUFGenerator` greedy params + explicit chat template + deadline; `test_prompt_identity_is_frozen`, `test_parse_terms_*`, `test_local_generator_renders_template_with_greedy_params`, `test_local_generator_deadline_raises_timeout`. |
| GEN-02 | 26-02 | same query+model+prompt hits cache, no re-generate; sweep N queries = N calls not 45N | ✓ SATISFIED | `LLMCacheRepository` reuse + sha256 key; `test_grid_sweep_generates_once_per_query` (real `iter_grid()`, 45 configs, `fake.calls==N`), `test_second_independent_connection_hits_the_committed_row`. |
| GEN-03 | 26-02, 26-03 | fail-open on failure/timeout, no retry storm, visible reason | ✓ SATISFIED | `_failed` latch, `_warn_once`, `terms=[]` fallback, no cache write on failure, `AnchorBudgetExceeded` hard raise; `--explain` stderr `fallback=`; `test_fail_open_matches_lex_and_warns_once`, `test_generation_failure_writes_no_row_and_latches`, `test_gen03_fallback_reason_is_visible`. |
| GEN-04 | 26-02 | default local GGUF; remote OpenAI-compatible opt-in only, discloses query egress | ✓ SATISFIED | default `anchor_backend="rules"` (zero-model; CONTEXT D-05 locks zero-model default — GEN-04's "本地 GGUF" is the optional generator path, not the default arm); `gguf` local, `openai` explicit config required, `_warn_egress_once`; `test_default_and_remote_fake_paths_open_no_socket`, `test_openai_egress_is_disclosed_once_per_base_url`. |
| CTR-03 | 26-04 | LFM3 GGUF not in wheel/sdist; license $10M + redistribution in docs & Key Decisions | ✓ SATISFIED | `git ls-files -- '*.gguf'` empty, `tests/test_packaging_assets.py` (3 guards), `pyproject.toml` no `.gguf` entries, `docs/search-algorithms.md:348-354`, `.planning/PROJECT.md:216`. |
| CTR-04 | 26-02, 26-03, 26-04 | new Settings/CLI via `make docs-generate` + docs CI diff gate; ≥90% coverage; 8-cell CI green | ✓ SATISFIED (local) / ⏭ DEFERRED (8-cell CI) | `make docs-generate` zero diff; 94.18% coverage; all 10 settings in SECTIONS; `--anchor` in CLI ref; 8-cell CI is the external post-push gate (see Truth 5 / Deferred Items) — locally unevaluable by design, never claimed green. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None | — | Debt-marker scan (`TBD`/`FIXME`/`XXX`), `TODO`/`HACK`/`PLACEHOLDER`/`not implemented`, empty returns, and console-only implementations across all 16 phase source/test files: zero matches. `26-REVIEW.md` INFO-1 (multi-word rule anchors dropped by guard when on) is intentionally skipped per `26-REVIEW-DISPOSITION.md` — default-off independent A/B, consistent with "drop terms not in the index vocabulary"; independently reproduced in the vocabulary-guard probe above. No critical/warning findings (0/0/1 info). |

### Decision Coverage

All trackable `26-CONTEXT.md` decisions are honored by shipped artifacts (`gsd_run query check.decision-coverage-verify`: `16/16 honored`, `not_honored: []`, non-blocking warning gate).

### Test Quality Audit

Requirement-linked test files were scanned for disabled/skipped tests, circular expected-value generation, and assertion strength: no `@pytest.mark.skip`/`test.skip`/`xit` on any requirement-linked case; tests use real SQLite (`SchemaManager`), real `iter_grid()`, and a second independent connection for cache proofs — not circular self-comparison; assertions are value/behavior-level (call counts, byte-identical terms, row counts, `patch` spies). No BLOCKER/WARNING from the audit.

### Human Verification Required

**N/A for this infrastructure/library phase** — no user-facing UI, no real-time behavior, no external-service UX to observe manually; all acceptance criteria are programmatically verifiable. The one exception-class item is the external 8-cell CI gate (see below), which is a post-push orchestrator/CI confirmation, not a human UAT step.

**External pending evidence (not a local pass, not a local failure):** the `8-cell CI 全绿` clause of ROADMAP SC 5 / CTR-04 must be confirmed by the orchestrator after push. `.github/workflows/test-matrix.yml` runs the 2 OS × 4 Python matrix with `uv sync --frozen --extra dev --extra embed` and `uv run --frozen pytest` on `push`/`pull_request`; the authoritative `--extra embed` full suite could not complete locally (slow mirror / 132 MiB torch download stopped after ~26 min). PLAN 26-04 explicitly removes this from local scope ("由 orchestrator 在 push 后确认") and `26-04-SUMMARY.md` records coverage D5 with `human_judgment: true`. Recorded here as `behavior_unverified: 1` and DEFERRED so it is never conflated with the local fallback pass.

### Gaps Summary

No blocking gaps found. Every must-have truth, artifact, and key link is present, substantive, and wired; every one of the 11 requirement IDs is satisfied with source/test evidence. The phase goal (default-off, cacheable, fail-open `anchor:` arm + optional local generator, no new runtime deps, MCP schema untouched) is achieved in the codebase.

The sole open item is the external 8-cell CI confirmation, which is by design a post-push gate and cannot be produced locally. **Status reasoning:** this does not reduce the phase to `gaps_found` (there is no FAILED truth, missing/stub artifact, not-wired link, or blocker anti-pattern — the plan and CONTEXT.md deliberately hand CI to the post-push orchestrator, and all locally-executable equivalents — full fallback suite, ty, ruff, docs-generate, MCP contract, frozen paths, coverage — are green). It also does not rise to a blocking `human_needed` for this infrastructure phase: the pending item is an automated CI matrix run, not a human UAT judgment. Per the output contract, the phase is recorded `passed` with the CI item clearly listed as DEFERRED / behavior-unverified and must still be confirmed after push before ROADMAP SC 5 is claimed fully green.

**Score: 5/5 must-haves verified locally (1 with an external/pending post-push sub-item).**

---

_Verified: 2026-11-28T08:20:57Z_
_Verifier: Claude (gsd-verifier)_
