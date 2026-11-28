---
phase: 26-anchor-arm-deterministic-cache
verified: 2026-11-28T13:42:06Z
status: passed
score: 6/6 must-haves verified (1 accepted by override)
covered_files:
  - .github/workflows/test-matrix.yml
  - .planning/PROJECT.md
  - .planning/REQUIREMENTS.md
  - .planning/ROADMAP.md
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
  - pyproject.toml
  - scripts/generate_config_ref.py
  - src/sif/cli/commands/search.py
  - src/sif/config/settings.py
  - src/sif/core/models.py
  - src/sif/mcp/backend.py
  - src/sif/search/anchor.py
  - src/sif/search/bm25.py
  - src/sif/search/hybrid.py
  - tests/test_ci_workflows.py
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
  - uv.lock
covered_digest: "v4:sha256:41086e86ad9c8c02bcf7a762e46fe13af2bc8291b7322e1561ec4df1ef332184"
behavior_unverified: 0
overrides_applied: 1
overrides:
  - must_have: "11 个冻结路径自 v1.2.5 起无 diff（CTR-04 本地全量门禁的一部分）"
    reason: "Owner-approved build change after the first verification: Python 3.10 support removed (commit 8babd7a1, 2026-11-28). Of the 11 frozen paths, 9 (protocol.py, tools.py, test_packaging.py, test_wire_transcripts.py, 5 goldens) are still zero-diff. pyproject.toml differs only in requires-python >=3.11 and the dropped 3.10 classifier; uv.lock differs only by removing <3.11-only package blocks (exceptiongroup, backports-asyncio-runner — verified as the only package names absent at HEAD) and cp310/pp310 wheel entries. Every 3.11+ package and wheel remains. Recorded in .planning/PROJECT.md Key Decisions (2026-11-28, with 6-cell CI run 46149558169 evidence) and docs/changelog.md; 6-cell CI run 46149558169 is green. Basis: the owner directed the removal in the working session (2026-11-28T12:31:40Z) and approved a plan that disclosed the frozen-path effect beforehand (2026-11-28T13:04:34Z)."
    accepted_by: "Tao Zhang (owner)"
    accepted_at: "2026-11-28T13:04:34Z"
re_verification:
  previous_status: passed
  previous_score: 5/5
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 26: Anchor Arm + Deterministic Cache — Verification Report

**Phase Goal:** 交付默认关闭、可缓存、失败回退的 `anchor:` 检索臂与本地可选生成器，不新增 runtime 依赖、不动 MCP schema。
**Verified:** 2026-11-28T13:42:06Z
**Status:** passed
**Re-verification:** Yes — the prior report (2026-11-28T08:20:57Z, `status: passed`, 5/5) covered two files that changed afterwards (`tests/unit/search/test_hybrid.py`, `pyproject.toml`/`uv.lock`). Both changes were re-checked below; neither regresses the phase goal. The prior open item (8-cell CI, then DEFERRED/behavior-unverified) is now **confirmed green**, so `behavior_unverified` drops from 1 to 0.
**Fingerprint:** `v4:sha256:41086e86ad9c8c02bcf7a762e46fe13af2bc8291b7322e1561ec4df1ef332184` (computed by `gsd-tools query verification.fingerprint`; the phase's 8 PLAN/SUMMARY files are added automatically by the verb and are included above).

All claims below were re-derived from the source, named tests and independent probes. SUMMARY.md / orchestrator numbers were treated as claims, not evidence.

## Goal Achievement

### Observable Truths

Must-haves are the 5 ROADMAP success criteria (the contract, non-negotiable) plus the one plan-level CTR-04 gate truth that is not already covered by SC 5 (the frozen-path clause). All 5 roadmap SCs are now fully VERIFIED; the frozen-path clause is PASSED via the documented owner override below.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `sif search query --anchor` / `anchor:` triggers anchor-enhanced BM25; anchors enter only the BM25 leg; snippets/highlights use the original query; off-flag behavior byte-identical to v1.2.5 with zero construction / zero model load (ROADMAP SC 1; ANC-01/02/03/04) | ✓ VERIFIED | `src/sif/core/models.py:92` (`ANCHOR`), `:387-393` (`anchor_terms: list[str] | None = None`; comments state no `anchor_enabled`/`anchor_mode`); `src/sif/search/hybrid.py:43-48` (one shared `PREFIX_ROUTES` incl. `anchor:`), `:363-365` (reset per search), `:384-394` (ANCHOR = one `self.hybrid.bm25.search` leg + `replace(options, anchor_terms=...)`), `:559-575` (function-local `derive_rule_anchors`/`AnchorResolution` import), `:585-596` (first-prefix-only parse); `src/sif/search/bm25.py:259-281` (OR-alternative form; `if not anchor_terms: return base`), `:209-214` (highlight uses original `query`); `src/sif/mcp/backend.py:34` (imports shared `PREFIX_ROUTES`), `:213-235` (ANCHOR branch), `:537-545` (prefix-first, before `_ensure_embedder` at `:547`); `src/sif/cli/commands/search.py:1122-1125` (`--anchor`), `:1267-1322` (route-first; ANCHOR sets `manager=None/embedder=None`, no `EmbeddingManager.from_settings`), `:1409-1422` (DYM/history use original `query`). Independent probes: importing `sif.search.hybrid` leaves `sif.search.anchor` unimported (False); `_build_fts_query(q) == _build_fts_query(q, None) == _build_fts_query(q, [])` (`"machine"* AND "learning"*`); `_split_query_prefix("anchor:lex:foo") == ("lex:foo", ANCHOR)`. |
| 2 | Repeating one query makes zero generator calls; a 45-config sweep over N queries makes N calls (frozen prompt / greedy / ≤10 terms / dedupe) (ROADMAP SC 2; GEN-01/02) | ✓ VERIFIED | `src/sif/search/anchor.py:256-272` (`PROMPT_VERSION="anchor.v1"`, `MAX_ANCHOR_TERMS=10`, frozen `PROMPT_TEMPLATE`), `:400-425` (`parse_terms`: strips numbering/bullets/quotes, drops empty / >64 chars / >6 words / pure-punct, dedupes, caps at 10), `:370-378` (sha256 key over prompt version/model/backend/normalized query), `:366-368` (`anchor::<backend>::<model_id>` namespace), `:616-681`/`:769-820` (resolve → `LLMCacheRepository.get` miss → one generate → `.set` on success only; `was_in_transaction` observed at entry, commit only own write), `:522-561` (local generator `temperature=0.0/top_k=1/repeat_penalty=1.0` + deadline). Named behavioral tests passed independently: `test_grid_sweep_generates_once_per_query` (real `iter_grid()`, 45 configs, `fake.calls == len(QUERIES)`), `test_same_resolver_second_resolve_hits_cache`, `test_second_independent_connection_hits_the_committed_row`, `test_prompt_identity_is_frozen`, `test_expired_cache_row_regenerates`. Probe: `parse_terms` returned `['alpha','beta','gamma','t0'…'t6']` (dedupe + all bounds + 10 cap). |
| 3 | Generator timeout/failure fail-opens to original-query results, no retry storm, user sees the reason; fail-open fallback is reproducible (ROADMAP SC 3; GEN-03) | ✓ VERIFIED | `src/sif/search/anchor.py:640-681` (`_failed` latch → `terms=[]` + `fallback_reason`, no retry), `:762-772` (single `_warn_once` per reason), `:775-820` (no cache write on failure; `.set` only after success), `:725-742` (`_check_budget` raises `AnchorBudgetExceeded`, not swallowed), `:526-556` (deadline via `StoppingCriteriaList` → `AnchorGenerationFailed("timeout")`). `src/sif/cli/commands/search.py:1413-1422` (`--explain` stderr `anchor: backend=... calls=... hits=... fallback=...`; stdout/JSON untouched). Named behavioral tests passed independently: `test_fail_open_matches_lex_and_warns_once`, `test_generation_failure_writes_no_row_and_latches`, `test_budget_exceeded_is_a_hard_failure`, `test_local_generator_deadline_raises_timeout`, `test_gen03_fallback_reason_is_visible`. |
| 4 | No external request unless explicitly opt-in remote backend; remote opt-in discloses query-text egress; vocab guard is an independent A/B (ROADMAP SC 4; GEN-04, ANC-05) | ✓ VERIFIED | `src/sif/search/anchor.py:274` (`_ANCHOR_BACKENDS={rules,gguf,openai}`), `:636-637` (default `rules`), `:430-435` (`_warn_egress_once` per base_url), `:702-715` (openai only when `anchor_backend=openai` AND base/model configured), `:564-613` (stdlib `urllib` POST, injectable transport), `:491-518` (`llama_cpp`/`jinja2` lazy-import only at generator call site), `:725-732` (`_apply_vocab_guard`, default False), `:349-362` (`filter_known_terms`); `src/sif/search/bm25.py:283-299` (`term_in_index` porter/CJK probe); `src/sif/mcp/backend.py:224-234` (guard filters in memory, no cache/embedder); `src/sif/config/settings.py:266-270` (`anchor_vocab_guard: bool = Field(default=False)`); `docs/search-algorithms.md:281-358` (default-off, deviation, generator opt-ins, egress, guard, license). Independent probe: importing `anchor` pulls no `llama_cpp`/`jinja2`/`torch`. Named tests passed independently: `test_default_and_remote_fake_paths_open_no_socket`, `test_openai_egress_is_disclosed_once_per_base_url`, `test_vocab_guard_off_keeps_oov_rule_anchors`, `test_vocab_guard_on_drops_oov_rule_anchors_read_only`. |
| 5 | Full pytest ≥90% coverage, `make docs-generate` zero diff, 8-cell CI green; LFM3 GGUF not packaged, `LFM Open License v1.0` $10M threshold + redistribution obligations in user docs & Key Decisions (ROADMAP SC 5; CTR-03/CTR-04) | ✓ VERIFIED | **Coverage:** my run of `.venv/bin/python -m pytest --ignore=tests/unit/inference/test_reranker.py -q` → `3367 passed, 1 skipped in 193.48s`, `Required test coverage of 90.0% reached. Total coverage: 94.18%`, exit 0. **Docs:** `.venv/bin/python scripts/generate_cli_ref.py` + `generate_config_ref.py` exit 0; `git diff --exit-code -- docs/cli-reference.md docs/configuration.md` exit 0 (zero diff); 10 `SIF_ANCHOR_*` rows in `docs/configuration.md:123-132`; `--anchor` in `docs/cli-reference.md:500`. **CI:** `gh run view 46144675032` → `conclusion: success`, `headSha e2033ecd`, 9/9 jobs success: lint + py3.10/3.11/3.12/3.13 × ubuntu/macos, each test cell's "Run full test suite" success (8-cell `--extra embed` matrix). Post-change `gh run view 46149558169` → success at `8babd7a1`, 6 cells + lint. First run `46143534219` failed **only** in both py3.10 cells on the test-mock defect fixed by `e2033ecd` (test-only; `src/` unchanged). **Packaging/license:** `git ls-files -- '*.gguf'` empty; `pyproject.toml` has no `gguf` entry; `tests/test_packaging_assets.py` (3 static guards) and `tests/test_docs.py` pass; `docs/search-algorithms.md:348-356` states the USD 10M Section 5 threshold + license/NOTICE redistribution; `.planning/PROJECT.md:136,220` records `Validated in Phase 26 (CTR-03)`; `docs/changelog.md:22` records the anchor arm. |
| 6 | Plan-level CTR-04 gate: 11 frozen paths zero-diff from v1.2.5 (26-04 truth) | ⚠️ PASSED (override) | `git diff --stat v1.2.5..HEAD -- <11 paths>` shows **only** `pyproject.toml` (+3/−?) and `uv.lock` (+31/−779); the other 9 paths (`src/sif/mcp/protocol.py`, `src/sif/mcp/tools.py`, `tests/unit/mcp/test_packaging.py`, `tests/unit/mcp/test_wire_transcripts.py`, 5 goldens) are zero-diff. `pyproject.toml` diff is only `requires-python ">=3.10"→">=3.11"` and the dropped `3.10` classifier. Independent lockfile check: package-name sets are old 95 / new 93; the only names absent at HEAD are `exceptiongroup` and `backports-asyncio-runner` (both <3.11-only backports); `torch`, `numpy`, `scipy`, `scikit-learn`, `rapidfuzz`, `python-multipart`, `sse-starlette`, `rpds-py`, `networkx` all remain; no added lock line contains a mirror URL. This is the owner-approved Python 3.10 removal (commit `8babd7a1`, recorded in `PROJECT.md` Key Decisions and `docs/changelog.md`), not a contract change: 7 MCP tools, `QueryInput` (no anchor field), and all 5 goldens are byte-unchanged, and MCP contract tests pass (39 passed). See the frontmatter `overrides:` entry. |

**Score:** 6/6 must-haves verified (1 accepted by override). `behavior_unverified: 0` — every behavior-dependent truth (cache call counts, fail-open latch, timeout, no-socket, zero-model routing) is exercised by a named passing test.

### Delta Since the Previous Verification

1. **`e2033ecd` — test-only change** (`tests/unit/search/test_hybrid.py`, 1 inserted test helper). The `patch.object(..., autospec=True, wraps=...)` spy that returned a `MagicMock` on Python 3.10 was replaced with a named passthrough (`_recording_build`) that returns the real `_build_fts_query` result. Assertion strength is preserved (records `(searcher, query, anchor_terms)`, asserts `anchor_terms == ["quantum"]`, `'OR "quantum"*' in match`, and `match != real_build(..., None)`). Product code under `src/` is untouched. Re-run: `test_anchor_terms_reach_the_bm25_leg_in_hybrid_mode` passes locally; CI run `46144675032` is 9/9 green.
2. **`8babd7a1` — build change** (Python 3.10 removed). `requires-python >=3.11`, 3.10 classifier dropped, CI matrix 8→6 cells, `uv.lock` pruned of <3.11-only entries. Product code under `src/` is untouched. Verified above: 9/11 frozen contract paths remain zero-diff; the 2 that differ carry only the build change; 6-cell CI run `46149558169` is green. Recorded as an override rather than a failure because the owner decided this in the session; the decision is recorded in `PROJECT.md` Key Decisions and `docs/changelog.md`.

### Advisory (New Scope, Unevidenced)

None. Re-verification ran no new-scope finding that lacks deterministic evidence. One documentation note (not a finding against the goal): `26-REVIEW.md`'s invariant #4 still says "frozen paths zero diff from v1.2.5 → empty"; that review predates `8babd7a1` and is stale on the two build files. The current verified state is the override row above and `PROJECT.md` Key Decisions.

### Required Artifacts

`gsd-tools query verify.artifacts` returned `all_passed: true` for 26-01 (4/4), 26-02 (4/4), 26-03 (2/2), 26-04 (5/5). Independent reads confirmed each is substantive and wired (no orphan/stub).

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/sif/search/anchor.py` | rule table + `derive_rule_anchors` + `AnchorResolution` + generator/resolver/cache/guard | ✓ VERIFIED | 820 lines; top-level stdlib + `LLMCacheRepository` only; `derive_rule_anchors` pure; `AnchorResolver` real; `filter_known_terms` wired to resolver + MCP. |
| `src/sif/core/models.py` | `SearchType.ANCHOR`, `SearchOptions.anchor_terms` (default None) | ✓ VERIFIED | `:92`, `:387-393`; no `anchor_enabled`/`anchor_mode`. |
| `src/sif/search/hybrid.py` | shared `PREFIX_ROUTES`, ANCHOR single-leg route + resolution metadata | ✓ VERIFIED | `:43-48`, `:363-365`, `:384-394`, `:559-575`. |
| `src/sif/mcp/backend.py` | read-only ANCHOR branch importing shared `PREFIX_ROUTES` | ✓ VERIFIED | `:34`, `:213-235`, `:537-545`. |
| `src/sif/search/bm25.py` | `_build_fts_query` OR injection + `term_in_index` probe | ✓ VERIFIED | `:259-281`, `:283-299`. |
| `src/sif/config/settings.py` | 10 `SIF_ANCHOR_*` fields + validators | ✓ VERIFIED | `:211-270`, `:427-453`; `anchor_vocab_guard` default `False`. |
| `scripts/generate_config_ref.py` | `Anchor Settings` section | ✓ VERIFIED | `:203-216` lists all 10 fields. |
| `docs/configuration.md` | regenerated config reference | ✓ VERIFIED | 10 `SIF_ANCHOR_*` entries; zero diff after regeneration. |
| `src/sif/cli/commands/search.py` | `--anchor` flag, route-first zero-model, stderr explain, original-query DYM/history | ✓ VERIFIED | `:1122-1125`, `:1267-1322`, `:1409-1422`. |
| `docs/cli-reference.md` | regenerated CLI reference with `--anchor` | ✓ VERIFIED | `:500`; zero diff after regeneration. |
| `tests/test_packaging_assets.py` | no-GGUF static guards | ✓ VERIFIED | 3 guards pass. |
| `docs/search-algorithms.md` | Anchor Expansion docs + LFM license | ✓ VERIFIED | `:281-358`. |
| `.planning/PROJECT.md` | LFM Key Decision status | ✓ VERIFIED | `:136`, `:220` `Validated in Phase 26 (CTR-03)`. |
| 9 anchor test files | substantive, wired, active | ✓ VERIFIED | 2.3 KB–15.5 KB each; 437 targeted tests collected/passed; no disabled requirement-linked case. |

### Key Link Verification

`gsd-tools query verify.key-links` returned `all_verified: true` for 26-01 (4/4), 26-02 (4/4), 26-03 (3/3), 26-04 (3/3). Independent source reads confirmed real imports/calls.

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/sif/search/hybrid.py` | `src/sif/search/anchor.py` | ANCHOR branch function-local `derive_rule_anchors` + `AnchorResolution` | ✓ WIRED | `hybrid.py:569` import, used `:571-575`; probe confirms default path never imports the module. |
| `src/sif/search/hybrid.py` | `src/sif/search/bm25.py` | `replace(options, anchor_terms=...)` → BM25 single leg | ✓ WIRED | `hybrid.py:391-392`. |
| `src/sif/mcp/backend.py` | `src/sif/search/hybrid.py` | import shared `PREFIX_ROUTES` | ✓ WIRED | `backend.py:34`, used `:140`, `:537`. |
| `src/sif/search/anchor.py` | `src/sif/database/repositories.py` | `LLMCacheRepository.get/set` on `llm_cache` | ✓ WIRED | `anchor.py:37`, `:720`, `:800`; cross-connection hit test passes. |
| `src/sif/search/anchor.py` | `src/sif/config/settings.py` | resolver reads the 10 anchor settings | ✓ WIRED | `anchor.py:636-742`, `:799` via `_setting_*`; defaults match. |
| `src/sif/search/anchor.py` | `src/sif/search/benchmark.py` | `iter_grid()` sweep call-count | ✓ WIRED | `test_anchor_cache.py` → `benchmark.py:363`; named test passes. |
| `scripts/generate_config_ref.py` | `docs/configuration.md` | regeneration | ✓ WIRED | re-ran; zero diff. |
| `src/sif/cli/commands/search.py` | `src/sif/search/hybrid.py` | `PREFIX_ROUTES` + `AnchorResolver` injection | ✓ WIRED | `search.py:45`, `:1275`, `:1390`. |
| `src/sif/cli/commands/search.py` | `src/sif/search/anchor.py` | `AnchorResolver` constructed only on the anchor route | ✓ WIRED | `search.py:1317-1319` (function-local). |
| `docs/cli-reference.md` | `src/sif/cli/commands/search.py` | generated from the Click flag | ✓ WIRED | `--anchor` present in both; zero diff. |
| `src/sif/search/anchor.py` | `src/sif/search/bm25.py` | `filter_known_terms` → `term_in_index` | ✓ WIRED | `anchor.py:349-362`. |
| `src/sif/mcp/backend.py` | `src/sif/search/anchor.py` | ANCHOR guard filter (read-only) | ✓ WIRED | `backend.py:224-234`. |
| `.planning/PROJECT.md` | `docs/search-algorithms.md` | same LFM license constraint | ✓ WIRED | `PROJECT.md:136,220` / `search-algorithms.md:348-356`. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `src/sif/search/bm25.py` | `fts_query` / `options.anchor_terms` | real `SearchOptions` from CLI/MCP/pipeline → `derive_rule_anchors` (pure) or `AnchorResolver.resolve` (DB `llm_cache` / generator) | ✓ FLOWING | `:89`, `:259-281`; real FTS MATCH against `documents_fts` (end-to-end test returns rows). |
| `src/sif/search/anchor.py` | `AnchorResolution.terms` | rules table / generator / `llm_cache` row | ✓ FLOWING | `:616-681`, `:769-820`; cross-process row verified by a second `sqlite3.Connection`. |
| `src/sif/mcp/backend.py` | `anchor_terms` | `derive_rule_anchors(parsed_query)` (+ optional in-memory guard) | ✓ FLOWING | `:224-234`; no static fallback. |
| `src/sif/cli/commands/search.py` | `pipeline_query`, `anchor_resolution` | user query + `pipeline.last_anchor_resolution` | ✓ FLOWING | `:1271`, `:1402-1404`. |
| `docs/configuration.md` / `docs/cli-reference.md` | generated tables | `Settings` fields / Click flags via scripts | ✓ FLOWING | regenerated with zero diff. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full local fallback suite + coverage | `.venv/bin/python -m pytest --ignore=tests/unit/inference/test_reranker.py -q` | `3367 passed, 1 skipped in 193.48s`; `Total coverage: 94.18%`; exit 0 | ✓ PASS |
| Targeted anchor/BM25/MCP/CLI/config suite | `.venv/bin/python -m pytest tests/unit/search/test_anchor_{injection,rules,cache,generator,vocab_guard}.py tests/unit/search/test_bm25.py tests/unit/search/test_hybrid.py tests/unit/cli/test_anchor_flag.py tests/unit/cli/test_search.py tests/unit/config/test_settings_anchor.py tests/unit/mcp/test_backend_anchor.py -q --no-cov` | `437 passed in 3.16s` | ✓ PASS |
| 26 named behavioral tests (routes, cache, fail-open, deadline, budget, no-socket, guard, zero-model CLI) | one `pytest -q --no-cov` invocation over the 26 node IDs | `26 passed in 0.90s` | ✓ PASS |
| MCP wire/packaging + docs + static guards | `.venv/bin/python -m pytest tests/unit/mcp/test_wire_transcripts.py tests/unit/mcp/test_packaging.py tests/test_docs.py tests/test_packaging_assets.py -q --no-cov` | `39 passed in 0.74s` | ✓ PASS |
| Routes / import graph / FTS byte-identity / parse bounds | `.venv/bin/python -` probe | `anchor prefix count: 1`; `split anchor:lex:foo -> ('lex:foo', ANCHOR)`; `default==none==[]: True`; default `"machine"* AND "learning"*`; anchored `("machine"* AND "learning"*) OR "deep learning"*`; `parse_terms` bounded/deduped; default import of `sif.search.anchor` = False; `anchor` import pulls no `llama_cpp/jinja2/torch` | ✓ PASS |
| Docs regeneration | `.venv/bin/python scripts/generate_cli_ref.py && .venv/bin/python scripts/generate_config_ref.py && git diff --exit-code -- docs/cli-reference.md docs/configuration.md` | exit 0, zero diff | ✓ PASS |
| Ruff / format / ty | `.venv/bin/ruff check src tests`; `.venv/bin/ruff format --check src tests`; `.venv/bin/ty check src/sif` | `All checks passed!`; `249 files already formatted`; `All checks passed!` (all exit 0) | ✓ PASS |
| Frozen contract paths | `git diff --stat v1.2.5..HEAD -- <11 paths>` | only `pyproject.toml` + `uv.lock` (Python 3.10 removal); 9 MCP paths empty | ✓ PASS (override for the 2 build paths) |
| No GGUF tracked | `git ls-files -- '*.gguf'` | empty (exit 0) | ✓ PASS |
| CI matrix (8-cell, then 6-cell) | `gh run view 46144675032 --json conclusion,headSha,jobs`; `gh run view 46149558169 …` | 9/9 success at `e2033ecd`; 7/7 success at `8babd7a1` | ✓ PASS |

### Probe Execution

No `scripts/*/tests/probe-*.sh` probes are declared in the phase's PLAN/SUMMARY or present in the repo. Not applicable — verification is pytest/gate-based.

### Requirements Coverage

All 11 phase-26 IDs from the four PLAN frontmatters are accounted for and cross-referenced against `.planning/REQUIREMENTS.md` (all `[x]` and marked Complete). PLAN `requirements` fields: 26-01 `[ANC-01..04]`, 26-02 `[GEN-01..04, CTR-04]`, 26-03 `[ANC-01, GEN-03, CTR-04]`, 26-04 `[ANC-05, CTR-03, CTR-04]`. Orphaned: none (EVL-01..05 are Phase 27; CTR-01/02 are Phase 25).

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| ANC-01 | 26-01, 26-03 | `anchor:`/`--anchor` triggers anchor BM25; unused = zero construction/load/cost | ✓ SATISFIED | `SearchType.ANCHOR`, route-first zero-model CLI (`search.py:1304-1319`), lazy import probe, `test_anchor_route_loads_no_embedder`, `test_default_path_does_not_import_the_anchor_module`. |
| ANC-02 | 26-01 | anchors only in the BM25 leg; snippet/highlight use original query | ✓ SATISFIED | `_build_fts_query` OR injection; `bm25.py:209-214`; `test_highlights_use_the_original_query`, `test_snippets_use_the_original_query_terms`. |
| ANC-03 | 26-01 | `SearchType.ANCHOR`, `anchor_terms`, shared prefix map; settings don't bypass `SearchOptions` | ✓ SATISFIED | single `PREFIX_ROUTES` (anchor appears once); no `anchor_enabled`/`anchor_mode`; `test_prefix_routes_shared_table_has_anchor`, `test_split_query_prefix_strips_only_the_first_prefix`. |
| ANC-04 | 26-01 | `hybrid+anchor` diagnostic arm only, default off, doesn't replace default RRF BM25 | ✓ SATISFIED | `SearchOptions().anchor_terms is None`; `test_default_options_match_prechange_snapshot`, `test_anchor_terms_reach_the_bm25_leg_in_hybrid_mode`, `test_anchor_terms_leave_vector_scores_unchanged`. |
| ANC-05 | 26-04 | vocab guard independent A/B, drops OOV terms; default/deviation/impact documented | ✓ SATISFIED | `anchor_vocab_guard` default False; `_apply_vocab_guard`, `filter_known_terms`/`term_in_index`; `docs/search-algorithms.md:339-358`; `test_anchor_vocab_guard.py` + MCP guard off/on tests. |
| GEN-01 | 26-02 | frozen versioned prompt, greedy/temp 0, one term/line, ≤10, dedupe; frozen before eval | ✓ SATISFIED | `PROMPT_VERSION="anchor.v1"`, `PROMPT_TEMPLATE`, `parse_terms`, `LocalGGUFGenerator` greedy params + explicit chat template + deadline; `test_prompt_identity_is_frozen`, `test_parse_terms_*`, `test_local_generator_deadline_raises_timeout`. |
| GEN-02 | 26-02 | same query+model+prompt hits cache, no re-generate; sweep N queries = N calls not 45N | ✓ SATISFIED | `LLMCacheRepository` reuse + sha256 key; `test_grid_sweep_generates_once_per_query` (real `iter_grid()`, 45 configs), `test_second_independent_connection_hits_the_committed_row`. |
| GEN-03 | 26-02, 26-03 | fail-open on failure/timeout, no retry storm, visible reason | ✓ SATISFIED | `_failed` latch, `_warn_once`, `terms=[]` fallback, no cache write on failure, `AnchorBudgetExceeded` hard raise; `--explain` `fallback=`; named tests above + `test_gen03_fallback_reason_is_visible`. |
| GEN-04 | 26-02 | default local GGUF; remote OpenAI-compatible opt-in only, discloses query egress | ✓ SATISFIED | default `anchor_backend="rules"` (zero-model default per D-05; the local GGUF generator is the opt-in path); `openai` requires explicit config + `_warn_egress_once`; `test_default_and_remote_fake_paths_open_no_socket`, `test_openai_egress_is_disclosed_once_per_base_url`. |
| CTR-03 | 26-04 | LFM3 GGUF not in wheel/sdist; license $10M + redistribution in docs & Key Decisions | ✓ SATISFIED | `git ls-files -- '*.gguf'` empty, 3 static guards pass, `pyproject.toml` no `.gguf`; `docs/search-algorithms.md:348-356`; `PROJECT.md:136,220`. |
| CTR-04 | 26-02, 26-03, 26-04 | new Settings/CLI via `make docs-generate` + docs CI diff gate; ≥90% coverage; 8-cell CI green | ✓ SATISFIED | zero-diff regeneration; 94.18% coverage; all 10 settings in SECTIONS; `--anchor` in CLI ref; 8-cell run `46144675032` green (9/9) and post-change 6-cell run `46149558169` green. The frozen-path sub-clause is the overridden item (row 6). |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None | — | Debt-marker scan (`TBD`/`FIXME`/`XXX`), `TODO`/`HACK`/`PLACEHOLDER`/`not implemented`/placeholder text across all phase source and test files: zero matches. Four `return []`/`return {}` matches (`backend.py:202`, `search.py:427,432`, `bm25.py:85`) are legitimate empty-result fallbacks (no results → `{}` checksums / `[]` suggestions/paths / `[]` results), not stubs; each has a real data path. `26-REVIEW.md` INFO-1 (multi-word rule anchors dropped when the guard is on) is intentionally skipped per `26-REVIEW-DISPOSITION.md` — default-off A/B, consistent with the guard's "drop terms not in the vocabulary" semantics. 0 critical / 0 warning / 1 info. |

### Decision Coverage

`gsd-tools query check.decision-coverage-verify` → `{skipped: false, blocking: false, total: 16, honored: 16, not_honored: []}` — "All trackable CONTEXT.md decisions are honored by shipped artifacts." (Non-blocking warning gate; no status impact.)

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| `test_anchor_injection.py` | ANC-01/02 | yes | 0 | no (real FTS) | value/behavior | ✓ |
| `test_anchor_rules.py` | ANC-02/03 | yes | 0 | no (pure function) | value | ✓ |
| `test_anchor_cache.py` | GEN-01/02/03 | yes | 0 | no (real SQLite, real `iter_grid()`, 2nd connection) | call-count/value | ✓ |
| `test_anchor_generator.py` | GEN-01/03/04 | yes | 0 | no (fake transport, socket monkeypatch) | behavior | ✓ |
| `test_anchor_vocab_guard.py` | ANC-05 | yes | 0 | no (real `SchemaManager` DB) | value/behavior | ✓ |
| `test_anchor_flag.py` | ANC-01, GEN-03 | yes | 0 | no (patched `from_settings`) | behavior | ✓ |
| `test_settings_anchor.py` | CTR-04 | yes | 0 | no | value | ✓ |
| `test_backend_anchor.py` | ANC-05, CTR-04 | yes | 0 | no | value/behavior | ✓ |
| `test_hybrid.py` | ANC-04 | yes | env-guarded only (`pytest.skip` for absent sqlite-vec on vector tests) | no (real build function) | value/behavior | ✓ |
| `test_packaging_assets.py` | CTR-03 | yes | env-guarded only (`git not available`) | no (static file inspection) | existence/value | ✓ |

**Disabled tests on requirements:** 0 (the only `pytest.skip` calls are environment guards for sqlite-vec/git; none is the sole proof of a requirement, and none skipped in these runs). **Circular patterns detected:** 0. **Insufficient assertions:** 0. The changed `test_anchor_terms_reach_the_bm25_leg_in_hybrid_mode` retains value-level assertions after the passthrough rewrite.

### Human Verification Required

**N/A — infrastructure/library phase with no user-facing elements.** No UI, no real-time UX, no external-service UX; all acceptance criteria are programmatically verifiable, and the one externally-produced artifact (the 8-cell CI matrix) is now confirmed by GitHub Actions evidence rather than deferred. There are no `⚠️ PRESENT_BEHAVIOR_UNVERIFIED` truths (`behavior_unverified: 0`), so no behavior-unverified human item applies.

### Gaps Summary

No blocking gaps. Every roadmap success criterion is present, substantive, and wired; all 11 requirement IDs are satisfied with source/test/CI evidence. The two changed inputs since the first verification were re-checked in full:

- `e2033ecd` is a test-only rewrite that preserves assertion strength and fixes a Python 3.10 mock defect; product code is unchanged, the named test passes locally, and the 8-cell CI run is green.
- `8babd7a1` removes Python 3.10 support. It does not touch `src/`, and the frozen MCP contract (7 tools, `QueryInput`, 5 goldens, protocol/tools) remains byte-identical. The only frozen-path drift is `pyproject.toml`/`uv.lock`, confined to `requires-python`/classifier and <3.11-only lock entries, recorded as an owner decision in `PROJECT.md` Key Decisions and `docs/changelog.md`. It is accepted via the single override above rather than silently passed.

The prior report's sole open item — "8-cell CI 全绿" — is now satisfied: run `46144675032` on `e2033ecd` completed 9/9 jobs green (lint + py3.10–3.13 × ubuntu/macos, each running the full `--extra embed` suite under the 90% gate). The subsequent 6-cell matrix on `8babd7a1` is also green (`46149558169`). Nothing remains deferred.

**Status: `passed`** — no FAILED truth, missing/stub artifact, unwired link, blocker anti-pattern, or human-verification item. Score 6/6 (1 accepted by override).

---

_Verified: 2026-11-28T13:42:06Z_
_Verifier: Claude (gsd-verifier)_
