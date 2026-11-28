---
phase: 25-contract-freeze-feasibility-spike
verified: 2026-11-28T00:59:49Z
status: passed
score: 12/12 must-haves verified
covered_files:
  - .planning/phases/25-contract-freeze-feasibility-spike/25-01-PLAN.md
  - .planning/phases/25-contract-freeze-feasibility-spike/25-01-SUMMARY.md
  - .planning/phases/25-contract-freeze-feasibility-spike/25-02-PLAN.md
  - .planning/phases/25-contract-freeze-feasibility-spike/25-02-SUMMARY.md
  - .planning/phases/25-contract-freeze-feasibility-spike/bench/anchor-table.json
covered_digest: "v4:sha256:96cf8e869d9dde8cb2958138d0e010b96e6eab359e16e00d3334b974c194ba80"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 25: Contract Freeze & Feasibility Spike Verification Report

**Phase Goal:** 在写任何新代码前证明 `llama.cpp` 能加载 `lfm3` 架构、确定性锚点有方向性信号，并冻结 MCP/打包契约。
**Verified:** 2026-11-28T00:59:49Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

This is a spec-less research spike. It changed **no** `src/sif`, `tests/`, `pyproject.toml`, or `uv.lock` file; every deliverable is a planning/evidence artifact. Verification was run goal-backward against the four ROADMAP success criteria plus the two plans' `must_haves`, then cross-checked against the gitignored raw evidence under `.planning/tmp/phase-25/`. Every factual claim in the SUMMARYs was re-derived independently from the raw data, the source files, `shasum`, and `git`.

### Observable Truths

| #   | Truth   | Status     | Evidence       |
| --- | ------- | ---------- | -------------- |
| 1 | Compatibility evidence records the locked 0.3.35 outcome verbatim, the isolated 0.3.37 trial, chat template, generation/error, and embed/rerank impact (SPK-01; D-02, D-04) | ✓ VERIFIED | `bench/spike-verdict.json` `compatibility` block: locked `outcome=load-error`, `error_type=ValueError`, `native_error="…unknown model architecture: 'lfm3'"`; upgrade `outcome=loaded`; chat template present; both versions `embed_dimension=1024`. Corroborated by raw `.planning/tmp/phase-25/{compat_result.json,probe-locked.json,probe-locked-verbose.log,probe-upgrade.json,probe-embed-*.json}` |
| 2 | 0.3.37 loads `LFM3-1.7B-Q4_K_M.gguf` via plain `Llama(model_path=...)` without `embedding=True` and emits non-empty greedy text at temp 0.0 / top_k 1 (D-02) | ✓ VERIFIED | Raw `probe-upgrade.json`: `outcome=loaded`, `generation_non_empty=true`, `usage={prompt_tokens:8, completion_tokens:64}`, `signature_embedding_param` recorded separately; `generation={max_tokens:64,temperature:0.0,top_k:1}`. Real native startup output in `probe-upgrade-0.3.37.log` (exit=0) |
| 3 | Delta table has exactly 36 tuning rows in fixture order with per-query lex/anchor nDCG@10, Hit@10, Recall@10 diagnostics, helped/hurt/unchanged, mean, noise floor 1/36, `heldout_read:false` (SPK-02; D-06, D-07, D-08) | ✓ VERIFIED | `bench/spike-delta.csv` = 36 data rows, header exactly the 14 specified columns, all `split=tuning`; recomputed from CSV: helped 6 / hurt 0 / unchanged 30 (sum 36), mean 0.130203, noise floor 0.027778. `queries.heldout_read=false` |
| 4 | Anchors are derived only from the query string through the committed query-only table; no relevance/gold title/path reaches derivation (D-05) | ✓ VERIFIED | `spike_delta.py` `derive_anchors(query: str, table: dict)` raises `TypeError` on non-str and reads only `query`+`table`; script filter is `split == "tuning"`; fixture has 36 tuning / 20 heldout and only 36 were evaluated. `bench/anchor-table.json` `seed=0`, `provenance` contains `query-only`, `rrf_k=60` |
| 5 | A second run with the same fixture/table/seed produces identical rows/aggregates and the decision applies `mean>0 AND helped>hurt` literally (D-08) | ✓ VERIFIED | Raw `delta_result.json` vs `delta_result-rerun.json`: `rows` identical and `aggregates` identical (checked programmatically). CSV mean 0.130203>0, helped 6>hurt 0 → `directional-signal` |
| 6 | Phase-start 11-file SHA-256 manifest and the two MCP test results were captured before any install/artifact write, and START equals END (D-10, D-12) | ✓ VERIFIED | `start-manifest.sha256` == `end-manifest.sha256` (11 lines each; `diff -u` empty); both `13 passed`; `start-git.txt` records HEAD `7ac8354` / v1.2.5 / 16 commits at plan-start |
| 7 | All 11 END hashes equal START and the CONTEXT expected table; 13 passed at both ends; `git diff v1.2.5..HEAD` under frozen paths empty; working tree clean there (CTR-01, CTR-02; D-09..D-12) | ✓ VERIFIED | Independently recomputed `shasum -a 256` over all 11 paths → byte-identical to the CONTEXT expected table. `pytest … test_wire_transcripts.py test_packaging.py -q --no-cov` → `13 passed`. `git diff --stat v1.2.5..HEAD -- pyproject.toml uv.lock src/sif/mcp/ tests/unit/mcp/` empty; `git status --porcelain` there empty |
| 8 | Contract facts name the 7 tools in pinned order, `QueryInput` fields with no `anchor`, 5 goldens, 13 runtime deps, 0.3.35 pin unchanged (CTR-01, CTR-02) | ✓ VERIFIED | `src/sif/mcp/tools.py`: 7 `@mcp.tool` at 128/189/220/243/256/308/347 → query,get,multi_get,status,metadata,lex_search,vec_search. `protocol.py` `QueryInput` fields = query,collections,limit,offset,filter,per_chunk,min_score,rrf_k,bm25_weight,vector_weight (no anchor). 5 goldens present. `pyproject.toml` 13 deps; `uv.lock` resolves `llama-cpp-python` 0.3.35 |
| 9 | `bench/spike-verdict.json` is authoritative and every value rendered in the CSV and `25-CONTRACT-FREEZE.md` comes from it; CSV has 36 rows in fixture order; report records measured HEAD and commit count, never stale (D-14) | ✓ VERIFIED | CSV query order == JSON `rows` order; per-row `delta` matches to 6 dp; report contains `6c25e88d9913`, `0.130203`, `helped 6`, and both measured counts (20 at freeze check, 21 at final render) |
| 10 | Verdict is recorded through the state seam; on `directional-signal` the record names the signal and the Phase 26/27 unlock (D-15, SPK-03) | ✓ VERIFIED | `.planning/STATE.md` `stopped_at: Phase 25 complete — directional signal recorded; Phases 26/27 unlocked`. `25-SPIKE-VERDICT.md` absent (correct for this branch). ROADMAP Phase 25 checkbox left for orchestrator bookkeeping (untouched by the phase, per D-15) |
| 11 | Working-tree proof pastes `git status --porcelain` and explains the three whitelisted docs; `src/`, `tests/`, `pyproject.toml`, `uv.lock` have zero changes (D-16) | ✓ VERIFIED | `25-CONTRACT-FREEZE.md` §"Working tree (D-16)" explains `.planning/.continue-here.md`, `.planning/HANDOFF.json`, `.planning/v1.3-ui-anchor-milestone-research.md`. `git diff v1.2.5..HEAD -- src tests pyproject.toml uv.lock` empty; phase-window `7ac8354..HEAD` touches no such path |
| 12 | `COVERAGE.md` declares no external API integration and the api-coverage seal accepts it | ✓ VERIFIED | `COVERAGE.md` contains the exact reasoned declaration; no matrix rows |

**Score:** 12/12 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected    | Status | Details |
| -------- | ----------- | ------ | ------- |
| `bench/anchor-table.json` | Committed query-only anchor mapping | ✓ VERIFIED | Exists, 120 lines, committed at `ff9daa3`; sha256 `ea62ffdc…acfc` equals verdict `reproducibility.anchor_table_sha256`; seed 0, query-only provenance, rrf_k 60, max 6; wired via `derive_anchors` |
| `bench/spike-verdict.json` | Authoritative verdict/evidence | ✓ VERIFIED | 1,218 lines; contains decision, rule, arms, queries, delta, reproducibility, compatibility, contract_freeze, working_tree, evidence, notes, 36 raw rows |
| `bench/spike-delta.csv` | 36-row paired delta table | ✓ VERIFIED | 14-column header in exact order, 36 data rows in fixture order, values match JSON |
| `25-CONTRACT-FREEZE.md` | Freeze report | ✓ VERIFIED | Sections: Freeze anchor, Frozen file manifest, Existing test proof, Contract facts, Compatibility spike (SPK-01), Anchor signal spike (SPK-02), Working tree (D-16), Reproduction runbook, Limitations |
| `COVERAGE.md` | No-external-API declaration | ✓ VERIFIED | Exact declaration present; no fabricated rows |
| `25-SPIKE-VERDICT.md` | Present only on no-signal | N/A (correct) | Absent — directional-signal branch taken |

### Key Link Verification

| From | To  | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `.planning/tmp/phase-25/spike_compat.py` | `compat_result.json` | structured probe dump | ✓ WIRED | raw file exists with `probes`,`model`,`generation`,`embed_rerank`,`freeze_start` |
| `.planning/tmp/phase-25/spike_delta.py` | `delta_result.json` | per-query rows + aggregates | ✓ WIRED | raw file exists; `heldout_read:false`, n=36 |
| `spike_delta.py` | `src/sif/search/benchmark.py` | `SearchEvaluator.evaluate_per_query` | ✓ WIRED | paired arms on same tuning items |
| `spike_delta.py` | `src/sif/search/rrf.py` | `RRFFusion(k=60).fuse([lex, *probes])` | ✓ WIRED | implemented exactly as documented |
| `spike_delta.py` | `bench/anchor-table.json` | `derive_anchors(query, table)` | ✓ WIRED | pure function; hash-verified table |
| `assemble_evidence.py` | `bench/spike-verdict.json` | single in-memory dict → json.dump | ✓ WIRED | same dict renders CSV and Markdown |
| `spike-verdict.json` | `bench/spike-delta.csv` | same-source rows | ✓ WIRED | query order + deltas equal |
| `spike-verdict.json` | `25-CONTRACT-FREEZE.md` | same-source render | ✓ WIRED | mean, helped, hashes, commit counts equal |
| `25-SPIKE-VERDICT.md` | `.planning/STATE.md` | `state record-session` | N/A | directional branch records `bench/spike-verdict.json` as resume-file instead; STATE record present |
| `tests/unit/mcp/test_wire_transcripts.py` | `tests/unit/mcp/goldens` | golden-parametrized test, `--no-cov` at both ends | ✓ WIRED | 13 passed end-to-end (6+3 test funcs across the two files, parametrized) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `spike-delta.csv` | `delta`, `helped/hurt/unchanged`, `lex/anchor_ndcg_at_10` | `delta_result.json` ← real `SearchEvaluator.evaluate_per_query` on 36 tuning queries over a scratch index built from `tests/fixtures/bench/corpus` (150 docs) | Yes — recomputed mean 0.130203 from CSV rows matches JSON | ✓ FLOWING |
| `spike-verdict.json` compatibility | generation text, error stack, embed dim | raw `probe-upgrade.json` / `probe-locked*.json` from real subprocess runs | Yes — real native llama.cpp logs, real GGUF metadata (`general.architecture=lfm3`), exit codes | ✓ FLOWING |
| `25-CONTRACT-FREEZE.md` | manifests, contract facts | `shasum` over 11 files + `contract-facts.json` extracted from source | Yes — all 11 hashes re-derived independently | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Shipped MCP contract tests pass | `.venv/bin/python -m pytest tests/unit/mcp/test_wire_transcripts.py tests/unit/mcp/test_packaging.py -q --no-cov` | `13 passed, 1 warning` | ✓ PASS |
| Frozen contract byte-identical to v1.2.5 expected table | `shasum -a 256 <11 paths>` | All 11 match CONTEXT expected values | ✓ PASS |
| START == END manifest | `diff -u start-manifest.sha256 end-manifest.sha256` | empty output | ✓ PASS |
| No committed-history drift on frozen paths | `git diff --stat v1.2.5..HEAD -- pyproject.toml uv.lock src/sif/mcp/ tests/unit/mcp/` | empty | ✓ PASS |
| Working tree clean on frozen + source paths | `git status --porcelain -- src tests pyproject.toml uv.lock` (and frozen set) | empty | ✓ PASS |
| Delta aggregates reproducible from CSV | recompute mean/helped/hurt/unchanged from `spike-delta.csv` | 0.130203, 6/0/30, sum 36 | ✓ PASS |
| Rerun determinism | compare `delta_result.json` vs `delta_result-rerun.json` | rows and aggregates identical | ✓ PASS |
| Anchor-table hash matches verdict | `sha256(anchor-table.json)` vs `reproducibility.anchor_table_sha256` | equal (`ea62ffdc…acfc`) | ✓ PASS |

### Probe Execution

| Probe | Command | Result | Status |
| ----- | ------- | ------ | ------ |
| (none declared under `scripts/*/tests/probe-*.sh`) | — | The phase's probes are the gitignored scratch scripts `spike_compat.py` / `spike_delta.py`; their execution outputs are preserved as raw artifacts | Step 7c: N/A (no conventional probe scripts). Rerunning them would require the external user-supplied GGUF and the throwaway venvs; their outputs were verified as raw data instead |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| SPK-01 | 25-01 | Locked `llama-cpp-python` loads `LFM3…gguf` & confirms `lfm3` inference; record upgrade/fallback + embed/rerank impact if incompatible | ✓ SATISFIED | Locked 0.3.35 fails (`unknown model architecture: 'lfm3'`); isolated 0.3.37 loads + generates; embed/rerank measured 1024-dim on both |
| SPK-02 | 25-01 | Reproducible `lex:`→`anchor:` paired comparison on existing fixture with directional-signal verdict + delta table | ✓ SATISFIED | 36-row tuning-only paired nDCG@10 table, two-run identical, `directional-signal` |
| SPK-03 | 25-02 | No-signal milestone may archive hypothesis with no half-finished code | ✓ SATISFIED (directional branch) | Directional signal was produced, so the no-signal archival path is not exercised; the required positive path (state record names signal + Phase 26/27 unlock; tree clean; no scratch committed) is verified. The conditional stop-loss mechanism is documented and would apply symmetrically |
| CTR-01 | 25-02 | MCP 7 tools, 5 wire goldens, `QueryInput` unchanged; no MCP `anchor` request field | ✓ SATISFIED | Verified from source + 11-file manifest + `has_anchor_field:false` |
| CTR-02 | 25-02 | No new runtime deps; 13 core deps frozen | ✓ SATISFIED | 13 deps match exactly; `test_packaging.py` green; `0.3.35` lock pin unchanged |

No ORPHANED requirements: REQUIREMENTS.md maps only SPK-01..CTR-02 to Phase 25, and both plans claim all five.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` in committed phase artifacts | — | None |
| — | — | No absolute `/Users/...` path in any committed phase artifact (raw scratch retains paths but is gitignored) | — | None |

No stubs, no hollow props, no unwired data sources (this phase adds no product code).

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| `tests/unit/mcp/test_wire_transcripts.py` | CTR-01 | yes | 0 | no | Behavioral (golden byte compare, `--no-cov`) | PASS |
| `tests/unit/mcp/test_packaging.py` | CTR-02 | yes | 0 | no | Value (frozen 13-dep assertion) | PASS |

**Disabled tests on requirements:** 0. **Circular patterns:** 0 (the phase added no tests). **Insufficient assertions:** 0.

### Decision Coverage

All trackable CONTEXT.md decisions are honored by shipped artifacts (16/16; `check.decision-coverage-verify` → `not_honored: []`).

### Deviations & Observations (weighed honestly, non-blocking)

1. **GGUF acquisition.** The phase scripts never downloaded or made any network request (grep of `spike_compat.py` / `probe_generate.py` / `spike_delta.py` / `run_spike_compat.sh` finds no HTTP client). The GGUF was obtained by the orchestrator on the user's authorization (user supplied the ModelScope repo URL) and reached the spike only via `--model-path` with SHA-256/size verification. The D-01 prohibition holds at the spike level.
2. **`uv.lock` mid-run restore.** An out-of-band Aliyun-mirror `uv` rewrite was restored with `git checkout -- uv.lock`. Independently verified: `shasum` == expected `b0175d45…`, and `git diff v1.2.5..HEAD -- uv.lock` is empty. The restore is what makes the byte-identical claim genuinely true; it changes no version. (Forward-looking "mirror-pinned lock?" is a future decision, not a Phase 25 must-have.)
3. **Degenerate generation text (informational).** The upgrade probe produced non-empty greedy text that repeats the prompt, because `create_completion` is called with a raw prompt rather than a chat-template-formatted prompt. This satisfies D-02's literal contract (non-empty text at temp 0 / top_k 1) and proves inference runs; the chat template is recorded separately. **Phase 26 must apply the chat template when building the real generator** — recommended as a Phase 26 design note.
4. **`25-VALIDATION.md` draft / no `25-SECURITY.md`.** `verify:post` hooks (validate-phase / secure-phase / ui-review) are advisory and out of the must-have surface; surfaced as next-step routing, not phase blockers.
5. **Stale-narrative avoidance.** Three distinct measured commit counts (16 at plan start, 20 at freeze check, 21 at final render) each match their own raw capture; CONTEXT's "4" and research's "7" were correctly not copied.
6. **Large-context note:** phase 25 changed no `src/`/`tests/` file, so the project's full quality suite reports only on unchanged code; the orchestrator's 3275 passed / 1 skipped gate and the reasoned CLAUDE.md waiver are consistent.

### Human Verification

N/A — research/evidence phase with no user-facing elements. All acceptance criteria are verifiable programmatically from the committed artifacts, the source, `shasum`, `git`, and the raw evidence; no ⚠️ PRESENT_BEHAVIOR_UNVERIFIED or abstained truths exist.

### Gaps Summary

None. All four ROADMAP success criteria and all plan `must_haves` are satisfied in the codebase/artifacts, not merely asserted in the SUMMARYs. The frozen MCP/packaging contract is byte-identical to v1.2.5 across all 11 files and the shipped 13-test proof is green at both ends; the query-only anchor spike produced a reproducible `directional-signal` (mean paired nDCG@10 +0.130203, helped 6 / hurt 0 / unchanged 30, N=36) recorded through the state seam; and the tree carries no half-finished product code. Phase 26/27 are unlocked.

---

_Verified: 2026-11-28T00:59:49Z_
_Verifier: Claude (gsd-verifier)_
