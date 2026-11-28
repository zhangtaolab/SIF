---
phase: 25-contract-freeze-feasibility-spike
plan: 01
subsystem: research-spike
tags: [llama-cpp-python, lfm3, gguf, bm25, rrf, ndcg-at-10, contract-freeze, evidence]

# Dependency graph
requires: []
provides:
  - "SPK-01 evidence: locked llama-cpp-python 0.3.35 load-failure transcript (ValueError; native 'unknown model architecture: lfm3'), isolated 0.3.37 load + non-empty greedy generation, chat template, and a measured embed/rerank impact"
  - "Phase-start contract proof: 11-file SHA-256 manifest matching the 25-CONTEXT table, 13 passed MCP contract tests, HEAD/anchor-tag/anchor-commit/measured commit count"
  - "Committed query-only anchor table at .planning/phases/25-contract-freeze-feasibility-spike/bench/anchor-table.json"
  - "36-row tuning-only paired nDCG@10 delta table with Hit@10/Recall@10 diagnostics, two-run identical proof, and the literal D-08 decision"
affects: [25-02, phase-26, phase-27]

# Actuals (#2632) — same chars/4 scale as the plan estimate, measured over the committed diff.
actuals:
  tokens: 1353
  tasks: 3
  commits: 1
  plan_head_before: 7ac8354b472a64662fe95e2ec00c86845215a126
  plan_head_after: ff9daa3345ada4134ce0d97cf88d16f5a63521e1

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Throwaway spike scripts, venvs, databases, and raw logs confined to .planning/tmp/phase-25/ (D-13); only bench/anchor-table.json is committed"
    - "Anchor arm = RRFFusion of the lex leg with one BM25 probe per derived anchor, never appended into one AND-joined FTS string"
    - "derive_anchors is a pure function of the query string plus the committed query-only table"

key-files:
  created:
    - .planning/phases/25-contract-freeze-feasibility-spike/bench/anchor-table.json
  modified: []

key-decisions:
  - "Locked llama-cpp-python 0.3.35 cannot load the LFM3 GGUF: Python raises ValueError('Failed to load model from file') while native llama.cpp logs 'unknown model architecture: lfm3'; recorded verbatim, not treated as an unexpected blocker."
  - "Isolated-venv 0.3.37 loads the same GGUF and produces non-empty greedy text with a ChatML-style chat template exposed; 0.3.37 is the first viable upgrade target and no pin changed."
  - "Embed/rerank impact measured: both 0.3.35 and 0.3.37 accept embedding=True and return a 1024-dimension .embed vector, so the existing LlamaCppEmbedder/reranker path is unaffected by the upgrade."
  - "Anchors are query-only: authored from the 36 tuning query strings plus general vocabulary; the derivation function receives only the query string and the table."
  - "Paired delta (anchor minus lex) is +0.130203 mean nDCG@10 with helped 6 / hurt 0 / unchanged 30, so the literal D-08 rule yields directional-signal; two runs produced identical rows and aggregates."

patterns-established:
  - "Two-run identical proof: the script re-evaluates both arms in-process before writing, then a second process rebuilds the scratch index and re-evaluates for cross-process equality."
  - "Supplemental native-error capture: the primary probe keeps verbose=False per D-02; a second diagnostic run with verbose=True records llama.cpp's own reason without changing the binding-level proof."

requirements-completed: [SPK-01, SPK-02]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "Human-supplied GGUF validated (absolute, regular, readable, .gguf, >100 MB) with SHA-256 and byte size recorded in gitignored scratch"
    verification:
      - kind: other
        ref: "test -s .planning/tmp/phase-25/model-path.txt && test -s .planning/tmp/phase-25/model-facts.txt"
        status: pass
    human_judgment: false
  - id: D2
    description: "compat_result.json records both probe outcomes, chat template, generation text or error stack, embed/rerank impact, and the phase-start freeze block"
    verification:
      - kind: other
        ref: "python -c \"assert req blocks; assert (locked or upgrade).generation_non_empty is True; manifest_lines==11\""
        status: pass
    human_judgment: false
  - id: D3
    description: "Phase-start 11-file SHA-256 manifest matches the 25-CONTEXT expected hashes and the two MCP contract test files report 13 passed"
    verification:
      - kind: other
        ref: "awk 'END{print NR}' start-manifest.sha256 == 11; grep -q '13 passed' start-tests.txt"
        status: pass
    human_judgment: false
  - id: D4
    description: "36-row tuning-only paired delta table with per-query Hit@10/Recall@10 diagnostics, noise floor 0.027778, and two-run identical proof"
    verification:
      - kind: other
        ref: "spike_delta.py first run + second run; assert rows/aggregates identical; assert n=36, heldout_read false, counts sum to 36, mean matches"
        status: pass
    human_judgment: false
  - id: D5
    description: "Committed query-only anchor table with seed 0, query-only provenance, and RRF k=60; recorded hash matches the committed file"
    verification:
      - kind: other
        ref: "python -c \"assert delta.anchors.sha256 == sha256(bench/anchor-table.json); seed==0; 'query-only' in provenance; rrf_k==60\""
        status: pass
    human_judgment: false

duration: ~8 min
completed: 2026-11-28
status: complete
---

# Phase 25 Plan 01: Contract Freeze & Feasibility Spike — Compatibility + Signal Evidence

**Locked llama-cpp-python 0.3.35 cannot load `lfm3` (native `unknown model architecture: 'lfm3'`), isolated 0.3.37 loads and generates non-empty text with embed unchanged at 1024 dims, and query-only RRF anchors produce a +0.130203 mean paired nDCG@10 delta (6 helped / 0 hurt / 30 unchanged) under a two-run identical, 36-query tuning-only table.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-11-28T00:33:42Z (first scratch artifact written)
- **Completed:** 2026-11-28T00:39Z
- **Tasks:** 3
- **Files modified:** 1 tracked file committed (120-line anchor table); 29 gitignored scratch artifacts under `.planning/tmp/phase-25/`

## Accomplishments

- **SPK-01 compatibility verdict is reviewable.** The locked 0.3.35 probe fails to load the human-supplied `LFM3-1.7B-Q4_K_M.gguf` (SHA-256 `3793e1e6e2266919d6e015287221b41100175a98eddaba92e111aed3b05c93c4`, 1,099,627,808 bytes); Python surfaces `ValueError`, and a supplemental verbose run captures llama.cpp's own `llama_model_load: error loading model: unknown model architecture: 'lfm3'`. The isolated 0.3.37 venv loads the same file through a plain `Llama(model_path=...)` constructor (no `embedding=True`) and produces non-empty greedy text at temperature 0.0 / top_k 1.
- **Chat template and embed/rerank impact are measured.** 0.3.37 exposes the model's ChatML-style `tokenizer.chat_template`; both 0.3.35 and 0.3.37 accept `embedding=True` and return a 1024-dimension `.embed("local search")` vector, so the shipped `LlamaCppEmbedder` / GGUF reranker path is unaffected by the upgrade.
- **Phase-start contract state is frozen before any artifact write.** All 11 SHA-256 hashes match the `25-CONTEXT.md` table exactly, the two existing MCP test files report `13 passed` with `--no-cov`, and HEAD / `v1.2.5` / measured commit count (16) are captured. The manifest is byte-identical at plan end.
- **SPK-02 signal table is deterministic and reproducible.** `bench/anchor-table.json` (version 1, seed 0, `query-only` provenance) drives a pure `derive_anchors(query, table)`; exactly the 36 tuning queries are evaluated in fixture order with paired nDCG@10 plus Hit@10/Recall@10 diagnostics. Mean paired delta is +0.130203 with helped 6 / hurt 0 / unchanged 30; every helped row is a synonym query whose raw terms score 0.0 lexically and whose anchors retrieve the graded documents.

## Task Commits

1. **Task 1: Validate and record the human-supplied GGUF path** — no commit (outputs are gitignored scratch: `model-path.txt`, `model-facts.txt`; D-13).
2. **Task 2: Tracer — locked-vs-upgrade compatibility and phase-start freeze** — no commit (all scripts, venvs, logs, and `compat_result.json` are gitignored scratch; D-13).
3. **Task 3: Deterministic query-only anchors to tuning-only paired delta** — `ff9daa3` (feat)

**Plan metadata:** committed separately after this file (docs commit for this SUMMARY).

## Files Created/Modified

- `.planning/phases/25-contract-freeze-feasibility-spike/bench/anchor-table.json` — committed query-only anchor table (phrases/tokens/CJK/compounds, rules: max 6 anchors, RRF k=60, weights 1.0).
- `.planning/tmp/phase-25/model-path.txt`, `model-facts.txt` — validated GGUF path (scratch) and basename/SHA-256/size facts.
- `.planning/tmp/phase-25/spike_compat.py`, `probe_generate.py`, `run_spike_compat.sh` — compatibility driver, isolated-venv child probe, reproduction runbook.
- `.planning/tmp/phase-25/compat_result.json` — raw SPK-01 evidence (probes, chat template, generation, embed/rerank, freeze_start, commands).
- `.planning/tmp/phase-25/spike_delta.py`, `delta_result.json`, `delta_result-rerun.json`, `bench-spike.db` — delta driver, paired rows, cross-process rerun, scratch index.
- `.planning/tmp/phase-25/start-manifest.sha256`, `start-tests.txt`, `start-git.txt` — phase-start freeze proof consumed by plan 25-02.

## Decisions Made

- Recorded the locked 0.3.35 outcome verbatim as a `ValueError` load failure, with the native llama.cpp reason captured separately; this corrects the research expectation of a Python `RuntimeError` without changing the verdict.
- Installed the locked 0.3.35 from the PyPI sdist after the Metal wheel index had no matching artifact, and 0.3.37 from the Metal wheel index; both are recorded with exact argv, index, and exit codes. No project lock file changed.
- Treated 0.3.37 as the upgrade target of record and recorded no pin change (D-03).
- Built the anchor arm as RRF fusion (one probe per anchor) rather than appending anchors into one FTS string, because `_build_fts_query` AND-joins tokens and would narrow instead of expand.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Evidence] Captured the native llama.cpp load error for the locked binding**
- **Found during:** Task 2 (compatibility probes)
- **Issue:** The planned primary probe uses `verbose=False`, so llama.cpp's native stderr was empty and the artifact recorded only Python's `ValueError: Failed to load model from file` — not the actual architecture reason the evidence exists to prove.
- **Fix:** Added a `--verbose` flag to the throwaway child probe and ran one supplemental locked-version diagnostic after the primary probe failed. The primary probe is unchanged, and the native tail is recorded at `probes.locked.native_evidence` in gitignored scratch.
- **Files modified:** `.planning/tmp/phase-25/probe_generate.py`, `.planning/tmp/phase-25/spike_compat.py` (both gitignored)
- **Verification:** Native tail contains `llama_model_load: error loading model: unknown model architecture: 'lfm3'`; all Task 2 verify commands pass, including `--rerun-only`.
- **Committed in:** not committed (D-13 scratch only)

---

**Total deviations:** 1 auto-fixed (1 missing critical evidence)
**Impact on plan:** The fix only strengthens the SPK-01 evidence; no product code, test, dependency, lock file, or committed artifact was touched, and the plan's probe contract is unchanged.

## Issues Encountered

- **Locked exception type differs from research.** Research Assumption A1 expected `RuntimeError` containing `unknown model architecture: 'lfm3'`; the binding actually raises `ValueError("Failed to load model from file: …")` after llama.cpp logs the architecture error. The catch-broadly design absorbed this exactly as planned.
- **Metal wheel index had no 0.3.35 artifact.** The driver fell back to the plain-PyPI sdist build, as the plan instructs; the attempt transcript is recorded in `probes.locked.install.attempts`.
- **The measured `v1.2.5..HEAD` commit count is 16**, not the 4 stated in CONTEXT or the 7 at research time; the artifact records the measured value (Pitfall 8).

## User Setup Required

None — the human-supplied GGUF path was obtained at the Task 1 checkpoint and validated; no further external service configuration is required.

## Next Phase Readiness

- Plan 25-02 can assemble the evidence trio from `compat_result.json`, `delta_result.json`, `start-manifest.sha256`, `start-tests.txt`, and `start-git.txt`; all paths are gitignored scratch and stable for this phase.
- The directional-signal verdict is positive under the literal D-08 rule; plan 25-02 owns the authoritative artifact assembly and the end-of-plan freeze re-check.
- `src/`, `tests/`, `pyproject.toml`, and `uv.lock` are untouched; `git status --porcelain` for those paths is empty, and the committed artifact contains no absolute model path.

## Known Stubs

None — no hardcoded placeholders, TODO/FIXME markers, or unwired data sources were introduced.

## Threat Flags

None — no new network endpoint, auth path, schema change, or trust boundary was introduced beyond the plan's threat model (T-25-01..T-25-SC).

## Self-Check: PASSED

- `bench/anchor-table.json` exists and is committed at `ff9daa3`.
- `compat_result.json`, `delta_result.json`, `delta_result-rerun.json`, `start-manifest.sha256`, `start-tests.txt`, and `start-git.txt` all exist under `.planning/tmp/phase-25/`.
- Both delta runs exit 0 and produce identical rows and aggregates.
- End-of-plan 11-file manifest is byte-identical to the start manifest.
