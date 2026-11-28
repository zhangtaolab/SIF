---
phase: "26"
slug: "anchor-arm-deterministic-cache"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-28"
---

# Phase 26 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x (project `addopts` carries coverage `fail_under = 90`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` / `[tool.coverage.report]` |
| **Quick run command** | `.venv/bin/python -m pytest <changed-area tests> -q --no-cov` |
| **Full suite command** | `.venv/bin/python -m pytest` (with `ruff check src tests`, `ruff format --check src tests`, `ty check src/sif`, `make docs-generate` diff) |
| **Estimated runtime** | ~180 seconds (full suite 3320+ tests @ 95%) |

---

## Sampling Rate

- **After every task commit:** Run `{quick run command}`
- **After every plan wave:** Run `{full suite command}`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 180 seconds

---

## Per-Task Verification Map

> Seeded from `26-RESEARCH.md` §Validation Architecture. Task IDs/plans are finalized by `gsd-planner`; this map is the validation contract the planner lifts per requirement.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 26-W0 | 01 | 0 | ANC-01..05, GEN-01..04, CTR-03..04 | T-26-01 / — | N/A (fixtures only) | unit | `.venv/bin/python -m pytest tests/unit/search/test_anchor*.py -q --no-cov` | ❌ W0 | ⬜ pending |
| 26-01 | 01 | 1 | ANC-01, ANC-02, ANC-03, ANC-04 | T-26-01 | default path byte-identical; no model load on prefix-free query | unit | `.venv/bin/python -m pytest tests/unit/search/test_bm25.py tests/unit/search/test_hybrid.py -q --no-cov` | ✅ | ⬜ pending |
| 26-02 | 01 | 1 | ANC-01, GEN-01 | T-26-02 | zero-model rule anchors don't touch llama_cpp | unit | `.venv/bin/python -m pytest tests/unit/search/test_anchor_rules.py -q --no-cov` | ❌ W0 | ⬜ pending |
| 26-03 | 02 | 2 | GEN-02 | T-26-03 | same query+model+prompt → zero generator calls; `llm_cache` namespaced | unit | `.venv/bin/python -m pytest tests/unit/search/test_anchor_cache.py -q --no-cov` | ❌ W0 | ⬜ pending |
| 26-04 | 02 | 2 | GEN-03, GEN-04 | T-26-04 | fail-open single warning, no retry storm; remote opt-in discloses egress | unit | `.venv/bin/python -m pytest tests/unit/search/test_anchor_generator.py -q --no-cov` | ❌ W0 | ⬜ pending |
| 26-05 | 03 | 3 | ANC-05, CTR-03, CTR-04 | T-26-05 | vocab guard default-off A/B; docs license + generate clean diff | unit + gate | `.venv/bin/python -m pytest tests/unit/mcp/test_wire_transcripts.py tests/unit/mcp/test_packaging.py -q --no-cov` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/search/test_anchor_rules.py` — deterministic query-only rule-anchor table stubs (ANC-01, GEN-01)
- [ ] `tests/unit/search/test_anchor_cache.py` — `llm_cache` namespace + `sha256(prompt_version+model_id+backend+stripped_query)` + cross-process hit stubs (GEN-02)
- [ ] `tests/unit/search/test_anchor_generator.py` — fake generator, fail-open, timeout, remote-disclosure stubs (GEN-03, GEN-04)
- [ ] `tests/unit/cli/test_anchor_flag.py` — `--anchor` on `query` only, prefix routing parity (ANC-01, ANC-03)
- [ ] `tests/unit/search/test_anchor_injection.py` — OR-alternative FTS MATCH + snippet/highlight use original query (ANC-02; see RESEARCH §AND-join finding)

*Existing infrastructure covers the remaining assertions (BM25, hybrid, MCP goldens, packaging, docs generator).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real GGUF `AnchorGenerator` end-to-end (LFM3-1.7B-Q4_K_M) | GEN-01, GEN-04 | Model is user-downloaded, opt-in, never in wheel/sdist; 0.3.35 cannot load `lfm3` | With a compatible `llama-cpp-python` in an isolated venv + user-supplied GGUF path, run one greedy generation with explicit chat template and confirm ≤10 deduped terms; record in phase evidence, not CI. |
| Real remote OpenAI-compatible endpoint egress disclosure | GEN-04 | Requires external endpoint + explicit opt-in; local-first default makes no network call | Configure a remote backend explicitly, confirm the one-time stderr notice names `<base_url>` and that query text is sent only after opt-in; no CI network call. |
| LFM Open License v1.0 doc review | CTR-03 | Legal wording, not code | Read the user docs + PROJECT.md Key Decisions; confirm the $10M revenue threshold and redistribution obligations are stated. |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 180s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
