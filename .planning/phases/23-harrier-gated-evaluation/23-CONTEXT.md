# Phase 23: Harrier Gated Evaluation - Context

**Gathered:** 2026-11-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Evaluate the Harrier-OSS-v1-0.6b native embedder against the existing Qwen3-Embedding-0.6B default on the user's own EN+ZH corpus, using the Phase 18 personal-bench instrument, and switch the default embedder **only** on a proven held-out win beyond the 0.01 tie rule.

In scope: two isolated evaluation arms, full per-arm re-embed, EN+ZH held-out comparison, per-language × per-leg verdicts, paired deltas + intervals, a committed verdict artifact, and (only on a pass) the default flip.

Out of scope: the GGUF Harrier arm (conditional follow-up MODEL-F1), bge-reranker-v2-m3, chunk-size/title-breadcrumb tuning (Phase 24), `sif models pull/status` fixes (Phase 24), any new retrieval feature, and any simultaneous multi-embedder serving.

</domain>

<decisions>
## Implementation Decisions

### Arm construction and isolation (MODEL-01)
- **D-01:** **Two fully isolated, file-backed indexes — one per arm — built from the identical corpus snapshot and chunker/config.** Never place two embedders' vectors in one index. Each arm's `index_meta.embedder.identity` is written by its first embedding write and recorded in the run artifact. Rationale: one vec0 table is one vector space; Phase 21 identity is the only thing that makes a same-width (1024-dim) swap detectable. — **Reversibility:** reversible — scratch DBs can be deleted.
- **D-02:** **Full per-arm re-embed through the Phase 21 streaming writer.** Build both arms from the same indexed documents and checksums; do not reuse pre-existing vectors unless the existing index already certifies the matching identity with `source: verified`. Report documents/chunks embedded, wall time, and embedding-cache hit counts per arm. — **Reversibility:** reversible — evaluation procedure only.
- **D-03:** **Harrier arm = native sentence-transformers; Qwen3 arm = the current default.** Harrier: `model_type=sentence_transformers`, `model_name=microsoft/harrier-oss-v1-0.6b`; prompts come from the Phase 21 known-model table (query `web_search_query`, document `None`) — never `default_prompt_name`. Qwen3: `model_type=modelscope`, `model_name=Qwen/Qwen3-Embedding-0.6B`, prompt-free. The Qwen3 arm must remain byte-identical to today's default path. Pin and record the model revision in the arm identity. — **Reversibility:** reversible — settings/env per arm.
- **D-04:** **Scratch arm artifacts live outside the default index.** Use a dedicated scratch directory (for example `.planning/tmp/phase-23/` or a cache subdirectory) for the two arm DBs and records; the committed deliverable is the verdict artifact, not the multi-GB arm DBs. Clean up arm DBs after the verdict unless the user asks to keep them. — **Reversibility:** reversible — scratch data.

### Corpus, query set, and splits (MODEL-01)
- **D-05:** **Use the user's personal corpus and the Phase 18 saved-run comparison.** Run the Qwen3 arm first with `sif eval --personal` (auto-saves the run), then run the Harrier arm with `--compare <saved-run>`. `--compare` already tolerates a different model identity and refuses only on a corpus-fingerprint mismatch (`ComparisonReport.model_mismatch`); the runbook must record both arms' identities because the saved `model` dict carries only model name/type/dimension, not the prompt scheme or revision. — **Reversibility:** reversible — procedure.
- **D-06:** **Reuse Phase 18 D-01..D-08 verbatim.** Three legs (title/H1, body snippet, query-log replay); deterministic hash sampling; 50/50 tuning/held-out split with held-out ≥ 25; per-leg overlap budgets; groups are leg × language × category with groups < 10 suppressed and named; paired bootstrap 95% CI + mean Δ ≥ 0.01. No new metrics, query synthesis, or split logic in this phase. — **Reversibility:** costly — changing the instrument would make the Phase 18 baseline and Phase 23 verdict incomparable.
- **D-07:** **EN+ZH adequacy is a precondition for a verdict.** The verdict requires held-out groups for both `en` and `zh` with N ≥ 10 per reported group. If either language's held-out N is short, widen sampling per Phase 18 D-06; if it remains short, record `insufficient evidence` and keep Qwen3. A one-language win is not a default-switch basis. — **Reversibility:** reversible — analysis rule.

### Verdict and default-switch rule (MODEL-02)
- **D-08:** **The switch gate is two-sided.** The default changes only when (a) the overall held-out paired-delta CI excludes 0 and mean Δ ≥ 0.01, **and** (b) neither per-language held-out mean Δ is below −0.01. An EN win with a ZH regression is not a win; this is the operational reading of "EN+ZH held-out win beyond the 0.01 tie rule". — **Reversibility:** costly — the gate governs whether the published default changes.
- **D-09:** **No-win is a first-class, recorded outcome.** Write a committed verdict artifact (for example `bench/harrier-verdict.json`) and a `docs/benchmarking.md` section containing arm identities, corpus fingerprint, query-set/saved-run fingerprint, per-leg × per-language gates, N, deltas, CIs, and the decision. A rejection leaves `DEFAULT_MODELS`/settings and the Qwen3 path byte-identical and cuts no release. — **Reversibility:** reversible — evidence artifact.
- **D-10:** **A pass flips the default in the same phase.** Update the Settings default model/type (and any generated docs via `make docs-generate`), keep Qwen3 selectable, and prove the explicit-Qwen3 path still produces the byte-identical baseline. `DEFAULT_MODELS`/`models pull` registry corrections remain Phase 24 (MODELS-01). — **Reversibility:** costly — the default embedder is a published behavior and changes the vector space of new indexes.

### Deliverable and instrumentation (MODEL-01/02)
- **D-11:** **No new public CLI command.** The instrument is the existing `sif eval --personal` + `--compare`; a stdlib-only reproducible runbook/script under `scripts/` orchestrates the two arms and writes the verdict artifact. If implementation proves `--compare` cannot express a needed comparison, prefer an additive flag over a new command. — **Reversibility:** reversible — scripts are internal.
- **D-12:** **Record cost and provenance.** Report per arm: model identity (including prompt scheme and revision), document/chunk counts, embed wall time, cache hits, corpus fingerprint, and query-set fingerprint. The evaluation runs locally (sentence-transformers/ModelScope), with single-threaded/batched embedding on macOS where needed. — **Reversibility:** reversible — reporting.
- **D-13:** **Test the gate math and orchestration, not the models.** Unit tests cover the two-arm verdict rule (overall CI + tie rule + per-language floor), saved-run comparison across model identities, and the runbook's argument/record building, using deterministic stub embedders/fixtures. Real-model runs are recorded evidence, not CI tests. — **Reversibility:** reversible — tests.

### Claude's Discretion
- Exact scratch directory naming/cleanup, verdict JSON schema, and whether to persist the Harrier revision as a hash.
- Bootstrap resample count and RNG seed (reuse Phase 18's implementation).
- Whether to run a BM25-only control (recommended: no — BM25 is embedder-independent and identical across arms; the comparison is hybrid).
- Exact verdict table/JSON rendering, following `bench`/`eval` output conventions.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and requirements
- `.planning/ROADMAP.md` §Phase 23 — goal, dependencies, MODEL-01/MODEL-02, success criteria
- `.planning/REQUIREMENTS.md` — MODEL-01, MODEL-02
- `.planning/PROJECT.md` — Current Milestone v1.2 target features and the locked Harrier gate / model-arms decisions

### Instrument and prior decisions
- `.planning/phases/18-quality-instrument-personal-bench-rapidfuzz-dym/18-CONTEXT.md` — D-01..D-13: query legs, hash sampling, 50/50 split, per-leg budgets, paired bootstrap 95% CI + 0.01 tie rule, saved-run comparison
- `.planning/phases/21-scale-maintenance-embedder-identity/21-CONTEXT.md` — D-01..D-08 (identity JSON/fingerprint, mismatch policy, role-aware embed, prompt table), D-15..D-19 (streaming embed, Qwen3 byte-identical precondition)
- `.planning/phases/19-search-correctness/19-CONTEXT.md` — ranking/pagination contracts and the B0 baseline discipline
- `.planning/phases/22-mcp-sdk-v2-modernization-agent-packaging/22-CONTEXT.md` — lazy embedder/identity consumption (the MCP side of the same identity contract)

### Code anchors
- `src/sif/search/personal_bench.py` — `SavedRun`, `ComparisonReport`, `GateResult`, bootstrap, split/sampling logic
- `src/sif/cli/commands/eval.py` — `sif eval --personal`, `--compare`, `--bm25-only`, saved-run loading
- `src/sif/embedding/identity.py` — `EmbedderIdentity`, `build_identity`, `check_identity`, mismatch policy
- `src/sif/embedding/prompts.py` — `_KNOWN_PROMPT_SCHEMES` (Harrier query `web_search_query`, document none)
- `src/sif/embedding/manager.py` — `embed_query` / `embed_documents` / `get_identity`
- `src/sif/indexing/embed_writer.py` — streaming re-embed path used by both arms
- `docs/benchmarking.md` — held-out evidence conventions and the verdict-recording style
- `bench/b0.json` — committed baseline artifact convention

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `sif eval --personal` + `--compare`: already implements legs, splits, groups, paired bootstrap, tie rule, saved runs, and cross-model comparison warnings — the instrument is complete.
- `ComparisonReport.model_mismatch` and `require_matching_corpus`: the cross-model comparison is supported today; only a corpus-fingerprint mismatch refuses.
- `EmbeddingManager.embed_query` / `embed_documents` and `PromptScheme`: role-aware embedding and the Harrier prompt-table entry already exist.
- `EmbedderIdentity` / `check_identity`: the 1024-dim same-width trap is already guarded; arms must record the full identity.
- Phase 21 streaming writer + `index embed --force`: full per-arm re-embed with short transactions and resumability.

### Established Patterns
- No new runtime dependencies; scratch DBs are file-backed and disposed after evaluation.
- Generator-owned docs (`docs/cli-reference.md`, `docs/configuration.md`) are never hand-edited; `docs/benchmarking.md` is hand-maintained evidence.
- Full suite uses PATH `pytest`; `ty` is the type checker; coverage gate 90%.
- Identity mismatch: fail-fast on embed, warn + mark on search.

### Integration Points
- `sif eval` saved-run `model` metadata (name/type/dimension) — the verdict artifact adds prompt scheme/revision.
- Settings defaults (`model_name`, `model_type`, `query_prompt_name`, `document_prompt_name`) — the arm selector and the eventual default flip.
- `DEFAULT_MODELS` / `sif models pull` registry — Phase 24 owns its correction.
- `make docs-generate` — required if the default or a command surface changes.

</code_context>

<specifics>
## Specific Ideas

- The prompt table already maps `microsoft/harrier-oss-v1-0.6b` to query prompt `web_search_query` and no document prompt; the arm must not pass `default_prompt_name`.
- Both models are 1024-dimensional, so width-only guards are insufficient; the Phase 21 identity fingerprint is the protection against a silent bad swap.
- Independent public evidence for Harrier is English-only; this phase's value is its own EN+ZH held-out evidence on the user's corpus.
- The user's prior research recorded localGPT A/B numbers (nDCG@10 0.915 vs 0.875) that were **not** independently verified at the exact value — do not cite them as evidence; the Phase 23 run is the evidence.

</specifics>

<deferred>
## Deferred Ideas

- GGUF Harrier arm (MODEL-F1) — only if the native gate passes and quantized deployment is wanted.
- bge-reranker-v2-m3 evaluation — out of scope.
- Chunk-size/overlap sweep and title-breadcrumb experiment — Phase 24.
- Multi-embedder simultaneous serving / per-collection embedder identity — not scoped.
- `models pull` / `models status` fixes and install docs — Phase 24.

</deferred>

---

*Phase: 23-Harrier Gated Evaluation*
*Context gathered: 2026-11-16*
