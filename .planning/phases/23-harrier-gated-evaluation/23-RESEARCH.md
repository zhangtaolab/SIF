# Phase 23: Harrier Gated Evaluation - Research

**Researched:** 2026-11-16
**Domain:** Local embedder A/B evaluation over the Phase 18 personal-bench instrument (Python 3.10+, SQLite/sqlite-vec, sentence-transformers 5.4.1, Click CLI)
**Confidence:** HIGH for the instrument, comparison contract, and gate math (all read from source this session); MEDIUM for Harrier runtime loading (config, prompts, pooling, revision path verified; the 1.19 GB weight load was not executed); LOW / at-risk for the EN+ZH adequacy precondition (the available local personal corpus measures at roughly 2% Chinese Markdown).

## Summary

The Phase 18 instrument already contains almost everything this phase needs: `sif eval --personal` synthesizes deterministic title/body queries, auto-saves a versioned run, and `--compare` re-evaluates exactly the saved query set at the saved depth while tolerating a different model identity (it refuses only a corpus-fingerprint mismatch) `[VERIFIED: src/sif/search/personal_bench.py:2083-2194, src/sif/cli/commands/eval.py:815-881]`. The Phase 21 work already gives each arm a persisted `embedder.identity` (model, type, dimension, pooling, prompt scheme, revision, source) and a role-aware prompt path `[VERIFIED: src/sif/embedding/identity.py:117-206, src/sif/embedding/manager.py:161-191]`; the Harrier prompt row (`web_search_query`, document none) is already in `_KNOWN_PROMPT_SCHEMES` `[VERIFIED: src/sif/embedding/prompts.py:28-30]`. Both models are 1024-dimension, last-token-pooled `[VERIFIED: Harrier raw 1_Pooling/config.json; local Qwen3 cache 1_Pooling/config.json]`, so width is not a guard - the identity fingerprint is.

Three real gaps must be closed before a verdict is possible:

1. **Per-language held-out evidence does not exist in `ComparisonReport`.** The overall held-out gate (`splits["heldout"]`) is the whole D-08 rule (a) `[VERIFIED: src/sif/search/personal_bench.py:2192]`, but the existing `groups` are leg x language x length over *both* splits and `leg_splits` has no language axis `[VERIFIED: src/sif/search/personal_bench.py:1849-1928]`. D-08 rule (b) ("neither per-language held-out mean delta below -0.01") cannot be computed from the report as-is. An additive `language_splits` (and optionally `leg_language_splits`) field plus a tiny pure verdict rule are needed.
2. **D-07's "widen sampling per Phase 18 D-06" is not implementable today.** `ensure_heldout` widens only while total accepted < 50 or total held-out < 25; it is language-blind `[VERIFIED: src/sif/search/personal_bench.py:1058]`. A corpus with enough total queries but fewer than 10 held-out Chinese queries stops early and then reports a language-blind pass. A language-aware widening condition (opt-in) is required to honor the locked decision.
3. **The evidence run is a hard, corpus-dependent manual step.** The two local SIF indexes contain 2 and 0 documents `[VERIFIED: local read-only SQLite inspection 2026-11-16]`; the largest available Markdown collection (`~/SynologyDrive`, 6,590 files) measures at ~1.1% zh titles and ~2.3% documents with meaningful CJK bodies, so a 250-document sample would contain roughly 6 Chinese documents `[VERIFIED: local deterministic filesystem sample 2026-11-16]`. That is very likely below the 10-held-out-queries-per-language floor. The plan must include a cheap adequacy preflight and treat "insufficient evidence" as a distinct, recorded outcome that does not silently pass MODEL-01.

**Primary recommendation:** Build the verdict as a pure two-sided rule over the existing Phase 18 gates (add `language_splits`, language-aware widening, and `--require-language en --require-language zh`), add a stdlib-orchestrated runbook under `scripts/` that builds two isolated scratch arms with `-q` (required: ModelScope pollutes stdout even on a cached model `[VERIFIED: local subprocess capture 2026-11-16]`), verifies each arm's full `index_meta` identity before evaluating, and writes a committed phase artifact; flip the default only when the held-out winner plus both per-language floors pass, and resolve corpus adequacy with the user before spending the multi-hour embed budget.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Arm construction and isolation (MODEL-01)
- **D-01:** **Two fully isolated, file-backed indexes — one per arm — built from the identical corpus snapshot and chunker/config.** Never place two embedders' vectors in one index. Each arm's `index_meta.embedder.identity` is written by its first embedding write and recorded in the run artifact. Rationale: one vec0 table is one vector space; Phase 21 identity is the only thing that makes a same-width (1024-dim) swap detectable. — **Reversibility:** reversible — scratch DBs can be deleted.
- **D-02:** **Full per-arm re-embed through the Phase 21 streaming writer.** Build both arms from the same indexed documents and checksums; do not reuse pre-existing vectors unless the existing index already certifies the matching identity with `source: verified`. Report documents/chunks embedded, wall time, and embedding-cache hit counts per arm. — **Reversibility:** reversible — evaluation procedure only.
- **D-03:** **Harrier arm = native sentence-transformers; Qwen3 arm = the current default.** Harrier: `model_type=sentence_transformers`, `model_name=microsoft/harrier-oss-v1-0.6b`; prompts come from the Phase 21 known-model table (query `web_search_query`, document `None`) — never `default_prompt_name`. Qwen3: `model_type=modelscope`, `model_name=Qwen/Qwen3-Embedding-0.6B`, prompt-free. The Qwen3 arm must remain byte-identical to today's default path. Pin and record the model revision in the arm identity. — **Reversibility:** reversible — settings/env per arm.
- **D-04:** **Scratch arm artifacts live outside the default index.** Use a dedicated scratch directory (for example `.planning/tmp/phase-23/` or a cache subdirectory) for the two arm DBs and records; the committed deliverable is the verdict artifact, not the multi-GB arm DBs. Clean up arm DBs after the verdict unless the user asks to keep them. — **Reversibility:** reversible — scratch data.

#### Corpus, query set, and splits (MODEL-01)
- **D-05:** **Use the user's personal corpus and the Phase 18 saved-run comparison.** Run the Qwen3 arm first with `sif eval --personal` (auto-saves the run), then run the Harrier arm with `--compare <saved-run>`. `--compare` already tolerates a different model identity and refuses only on a corpus-fingerprint mismatch (`ComparisonReport.model_mismatch`); the runbook must record both arms' identities because the saved `model` dict carries only model name/type/dimension, not the prompt scheme or revision. — **Reversibility:** reversible — procedure.
- **D-06:** **Reuse Phase 18 D-01..D-08 verbatim.** Three legs (title/H1, body snippet, query-log replay); deterministic hash sampling; 50/50 tuning/held-out split with held-out ≥ 25; per-leg overlap budgets; groups are leg × language × category with groups < 10 suppressed and named; paired bootstrap 95% CI + mean Δ ≥ 0.01. No new metrics, query synthesis, or split logic in this phase. — **Reversibility:** costly — changing the instrument would make the Phase 18 baseline and Phase 23 verdict incomparable.
- **D-07:** **EN+ZH adequacy is a precondition for a verdict.** The verdict requires held-out groups for both `en` and `zh` with N ≥ 10 per reported group. If either language's held-out N is short, widen sampling per Phase 18 D-06; if it remains short, record `insufficient evidence` and keep Qwen3. A one-language win is not a default-switch basis. — **Reversibility:** reversible — analysis rule.

#### Verdict and default-switch rule (MODEL-02)
- **D-08:** **The switch gate is two-sided.** The default changes only when (a) the overall held-out paired-delta CI excludes 0 and mean Δ ≥ 0.01, **and** (b) neither per-language held-out mean Δ is below −0.01. An EN win with a ZH regression is not a win; this is the operational reading of "EN+ZH held-out win beyond the 0.01 tie rule". — **Reversibility:** costly — the gate governs whether the published default changes.
- **D-09:** **No-win is a first-class, recorded outcome.** Write a committed verdict artifact (for example `bench/harrier-verdict.json`) and a `docs/benchmarking.md` section containing arm identities, corpus fingerprint, query-set/saved-run fingerprint, per-leg × per-language gates, N, deltas, CIs, and the decision. A rejection leaves `DEFAULT_MODELS`/settings and the Qwen3 path byte-identical and cuts no release. — **Reversibility:** reversible — evidence artifact.
- **D-10:** **A pass flips the default in the same phase.** Update the Settings default model/type (and any generated docs via `make docs-generate`), keep Qwen3 selectable, and prove the explicit-Qwen3 path still produces the byte-identical baseline. `DEFAULT_MODELS`/`models pull` registry corrections remain Phase 24 (MODELS-01). — **Reversibility:** costly — the default embedder is a published behavior and changes the vector space of new indexes.

#### Deliverable and instrumentation (MODEL-01/02)
- **D-11:** **No new public CLI command.** The instrument is the existing `sif eval --personal` + `--compare`; a stdlib-only reproducible runbook/script under `scripts/` orchestrates the two arms and writes the verdict artifact. If implementation proves `--compare` cannot express a needed comparison, prefer an additive flag over a new command. — **Reversibility:** reversible — scripts are internal.
- **D-12:** **Record cost and provenance.** Report per arm: model identity (including prompt scheme and revision), document/chunk counts, embed wall time, cache hits, corpus fingerprint, and query-set fingerprint. The evaluation runs locally (sentence-transformers/ModelScope), with single-threaded/batched embedding on macOS where needed. — **Reversibility:** reversible — reporting.
- **D-13:** **Test the gate math and orchestration, not the models.** Unit tests cover the two-arm verdict rule (overall CI + tie rule + per-language floor), saved-run comparison across model identities, and the runbook's argument/record building, using deterministic stub embedders/fixtures. Real-model runs are recorded evidence, not CI tests. — **Reversibility:** reversible — tests.

### Claude's Discretion
- Exact scratch directory naming/cleanup, verdict JSON schema, and whether to persist the Harrier revision as a hash.
- Bootstrap resample count and RNG seed (reuse Phase 18's implementation).
- Whether to run a BM25-only control (recommended: no — BM25 is embedder-independent and identical across arms; the comparison is hybrid).
- Exact verdict table/JSON rendering, following `bench`/`eval` output conventions.

### Deferred Ideas (OUT OF SCOPE)
- GGUF Harrier arm (MODEL-F1) — only if the native gate passes and quantized deployment is wanted.
- bge-reranker-v2-m3 evaluation — out of scope.
- Chunk-size/overlap sweep and title-breadcrumb experiment — Phase 24.
- Multi-embedder simultaneous serving / per-collection embedder identity — not scoped.
- `models pull` / `models status` fixes and install docs — Phase 24.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MODEL-01 | User gets an evidence-based embedder comparison (EN+ZH held-out A/B of Harrier-OSS-v1-0.6b native vs Qwen3-Embedding-0.6B baseline; per-arm full re-embed; isolated indexes; per-language × per-leg verdict; paired deltas + intervals; query `prompt_name="web_search_query"`, never `default_prompt_name`). | Two isolated scratch DBs built via `sif index update` + `sif index embed --force`; `sif eval --personal` then `--compare`; Harrier identity must record `query_prompt="web_search_query"`; per-language held-out gates require the additive `language_splits`; language-aware widening is required for D-07 adequacy; cross-arm document ids are UUIDs so `--compare` resolves saved targets by unique path. |
| MODEL-02 | User's default embedder changes only on a proven win (default switch ONLY on an EN+ZH held-out win beyond the 0.01 tie rule; recorded rejection with numbers if no win; Qwen3 path byte-identical until the gate passes). | D-08's rule (a) is exactly `ComparisonReport.splits["heldout"].winner` / `warrants_default_change`; rule (b) needs a pure per-language mean-delta floor; the Phase 18 gate includes the 1/N noise-floor veto (so a 0.01 win is only admissible at held-out N > 100); a no-win writes the committed artifact + docs section and touches no default; a pass updates Settings, generated docs, hand-maintained default claims, and re-proves the explicit-Qwen3 path with a zero-delta comparison. |
</phase_requirements>

## Architectural Responsibility Map

This is a layered Python application, not a web app. "Tier" below means the project's architectural layer.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Arm index construction and full re-embed | Infrastructure: SQLite + `StreamingEmbedWriter` + `EmbeddingManager` | CLI (`index update`, `index embed --force`) | Chunks, vectors, shadow rows, and `embedder.identity` must commit together in the DB; the CLI is the host. |
| Query synthesis, split, bootstrap, gate math | Domain: `src/sif/search/personal_bench.py`, `benchmark.py` | — | Pure deterministic logic; already unit-tested; must not be reimplemented. |
| Two-sided verdict decision | Domain: new `src/sif/search/embedder_verdict.py` | — | A pure rule over `GateResult`s; unit-testable without models. |
| Two-arm orchestration, env pinning, cost capture | Scripts: `scripts/harrier_eval.py` | CLI subprocesses (`python -m sif.cli.main`) | Each arm needs its own process env because `get_settings()` is `lru_cache`d; the script is the only place that sees both arms. |
| Per-arm identity provenance | Database: `index_meta['embedder.identity']` | `src/sif/embedding/identity.py` | The DB row is the source of truth; the saved run's `model` dict is intentionally narrow. |
| Model download and encoding | Embedding infrastructure (`factory.py`, `embedder.py`, ModelScope downloader) | — | Reuse existing backends; no new dependency or loader in this phase. |
| Evidence recording | `docs/benchmarking.md` + committed phase artifact | — | Aggregate evidence only; saved runs and arm DBs stay local. |

## Standard Stack

### Core (no new packages)

| Component | Version | Purpose | Why standard |
|-----------|---------|---------|--------------|
| Python stdlib (`sqlite3`, `json`, `hashlib`, `subprocess`, `pathlib`, `random`, `time`) | 3.10+ | Orchestration, identity read, cache accounting, fingerprinting | Project constraint: no new runtime deps; the instrument is already stdlib-only. |
| Click | >=8.0.0 (installed 8.3.2) | New additive `--require-language` option | Existing CLI framework; no new command. |
| SQLite + sqlite-vec | sqlite-vec >=0.1.9 (installed 0.1.9) | Arm indexes, vec0 KNN, `index_meta` | Existing storage; each arm is one DB. |
| sentence-transformers | 5.4.1 (locked; `uv.lock` and installed) | Harrier native backend and the Qwen3 ModelScope backend | Locked dependency; `prompt_name` support verified. |
| transformers | `uv.lock` 5.5.4; evidence env 4.57.6 | Qwen3Model architecture | Both support `Qwen3Model`; ST 5.4.1 requires `transformers<6.0.0,>=4.41.0`. |
| torch | `uv.lock` fleets 2.14.1/2.15.0; evidence env 2.7.1 | Encoding device (MPS on this Mac) | Existing dep; device auto-selected by the embedder. |
| modelscope | >=1.36.0 (installed 1.36.0) | Qwen3 baseline download/load path | Existing `embed` extra; baseline must stay byte-identical. |
| pytest / pytest-cov | 9.1.1 local; CI 9.0.3 | Validation | Existing locked dev deps; `fail_under=90`. |

No package is installed by this phase. No `npm`/`pip` install step. Versions in this table were verified this session via `uv.lock`, installed distribution metadata, and local probes `[VERIFIED: uv.lock; importlib.metadata("sentence-transformers"); local probes 2026-11-16]`.

### Model artifact: `microsoft/harrier-oss-v1-0.6b`

| Fact | Value | Provenance |
|------|-------|------------|
| Exact HF repo id | `microsoft/harrier-oss-v1-0.6b` | `[VERIFIED: huggingface.co/api/models/microsoft/harrier-oss-v1-0.6b]` |
| License | MIT (`license:mit` tag; cardData license `mit`) | `[CITED: https://huggingface.co/microsoft/harrier-oss-v1-0.6b/raw/main/README.md]` |
| Parameters | 0.6B | `[CITED: model card parameter table]` |
| Embedding dimension | 1024 (`word_embedding_dimension` 1024; `hidden_size` 1024) | `[VERIFIED: raw 1_Pooling/config.json + raw config.json]` |
| Pooling | last-token (`"pooling_mode_lasttoken": true`; `include_prompt: true`) | `[VERIFIED: raw 1_Pooling/config.json]` |
| Normalization | L2 normalization (`Normalize` module + card text) | `[VERIFIED: raw modules.json; CITED: model card]` |
| Max sequence length | 32768 (`max_position_embeddings`) at the model level; SIF overrides to `SIF_MAX_TOKENS` (default 512) | `[VERIFIED: raw config.json; VERIFIED: src/sif/embedding/embedder.py:170-171]` |
| Architecture | `Qwen3Model` / `model_type: "qwen3"`; standard ST `Transformer` + `Pooling` + `Normalize` modules | `[VERIFIED: raw config.json + modules.json; locally AutoConfig-loaded 2026-11-16]` |
| `trust_remote_code` | Not required (no `auto_map`; `Qwen3Model` is built into transformers 4.57.6 and documented in transformers 5.x) | `[VERIFIED: raw config.json; CITED: https://huggingface.co/docs/transformers/model_doc/qwen3]` |
| Prompt names in repo | `web_search_query`, `sts_query`, `bitext_query`; `default_prompt_name: null`; similarity `cosine` | `[VERIFIED: raw config_sentence_transformers.json]` |
| Query/document instruction rule | Query needs an instruction; documents need none. "Yes, this is how the model is trained, otherwise you will see a performance degradation." "there is no need to add instructions to the document side." | `[CITED: model card]` |
| Query prompt template (`web_search_query`) | `"Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery: "` | `[VERIFIED: raw config_sentence_transformers.json]` |
| Revision at research time | `f9b9dc8d367d443f2479d27aa5d8d2850c0774ee` (lastModified 2026-03-30) | `[VERIFIED: HF API sha + AutoConfig `_commit_hash` agreed 2026-11-16]` |
| Downloads / likes | 217,170 / 339 | `[CITED: HF API]` |
| Weight size | `model.safetensors` 1,192,133,232 bytes (~1.19 GB); repo `usedStorage` 3,588,994,158 | `[VERIFIED: HF API ?blobs=true]` |
| Languages | Card lists ~96 codes including `zh`; prose names Chinese | `[CITED: model card]` |
| ST requirement on the card | No explicit minimum; repo uses the standard ST modules format; `sentence-transformers` 5.4.1 loads it structurally (prompt merge, modules, normalization) | `[VERIFIED: installed ST 5.4.1 source + 1_Pooling/modules files]` (weight load not executed) |

**Local runtime verification performed this session (macOS arm64, Python 3.13.9, ST 5.4.1, transformers 4.57.6, torch 2.7.1, MPS available):**
- `AutoConfig.from_pretrained("microsoft/harrier-oss-v1-0.6b")` resolved `Qwen3Config`, `hidden_size=1024`, `max_position_embeddings=32768`, `_commit_hash=f9b9dc8d...`; `transformers.models.qwen3.Qwen3Model` imports.
- A full `SentenceTransformerEmbedder` load of a cached standard ST model (`mixedbread-ai/mxbai-embed-large-v1`, MPS) confirmed: `prompt_name` resolution, query-vs-document vector divergence, `embed_documents` equal to the legacy path when no document prompt, `pooling_mode` detection, `revision` from `auto_model.config._commit_hash` (non-null), `max_seq_length` override, and a construction-time `ValueError` for an unknown prompt name.
- A full `ModelScopeEmbedder` smoke test of the Qwen3 baseline loaded in 5.5 s (cached), returned `dim=1024`, `pooling=last_token`, `revision=None`, unit-norm vectors.

**Python 3.10 / CPU note:** the local probes ran on Python 3.13.9 and MPS. `sentence-transformers` 5.4.1 declares `Requires-Python >=3.10` `[VERIFIED: installed distribution metadata]`, the project CI matrix covers 3.10-3.13 `[VERIFIED: .planning/REQUIREMENTS.md:15]`, and the Harrier load path is pure ST/transformers with no 3.10-specific branch (structural verification only). CPU encoding was not re-run this session; device selection is CUDA -> MPS -> CPU, so a CPU host takes the same code path with a different device `[VERIFIED: src/sif/embedding/embedder.py:143-151]`.

### Baseline arm facts (verified in repo)

| Fact | Value | Provenance |
|------|-------|------------|
| Default model name | `Qwen/Qwen3-Embedding-0.6B` | `[VERIFIED: src/sif/config/settings.py:115-118]` — quote: `default="Qwen/Qwen3-Embedding-0.6B",` |
| Default model type | `modelscope` | `[VERIFIED: src/sif/config/settings.py:134-137]` — quote: `default="modelscope",` |
| Prompt scheme | prompt-free (no table row) | `[VERIFIED: src/sif/embedding/prompts.py:28-30]` — quote: `"microsoft/harrier-oss-v1-0.6b": ("web_search_query", None),` and the comment says Qwen3 is deliberately absent |
| Qwen3's own ST prompt config | `{"query": "Instruct: Given a web search query, ...", "document": ""}`, `default_prompt_name: null` | `[VERIFIED: cached ~/Library/Caches/sif/Qwen/Qwen3-Embedding-0___6B/config_sentence_transformers.json]` |
| Effective Qwen3 cache bucket | `modelscope:Qwen/Qwen3-Embedding-0.6B` (no revision, no prompt suffix) | `[VERIFIED: src/sif/embedding/manager.py:245-257]` — quotes: `bucket = f"{bucket}|rev@{identity.revision}"`, `bucket = f"{bucket}|{_ROLE_MARKERS[role]}@{prompt}"`; also observed as the live cache bucket with 997 rows |
| Model cache location | `settings.get_cache_dir()` (`~/Library/Caches/sif` on macOS) because `cache_embeddings=True`; Qwen3 sits at `<cache>/Qwen/Qwen3-Embedding-0___6B` | `[VERIFIED: src/sif/embedding/manager.py:82-88], src/sif/models/download.py:35-44, local filesystem]` |
| Local Qwen3 weight size | 1.1 GB | `[VERIFIED: local du]` |

**Important interpretation:** the baseline is Qwen3 *as shipped*, which is prompt-free even though its own card config defines a query instruction. The A/B therefore measures "Harrier with its required query prompt" against "the current Qwen3 default path", which is exactly what MODEL-02's byte-identical precondition requires. A Harrier win is not a claim about an optimally prompted Qwen3.

### Alternatives Considered

| Instead of | Could use | Tradeoff |
|------------|-----------|----------|
| Additive `language_splits` on `ComparisonReport` | Extend the saved-run `model` dict with prompt/revision | Saved runs are a versioned, validated contract whose loader rebuilds exactly `{model_name, model_type, dimension}`; extending it needs a version bump. The DB `index_meta` identity is the authoritative per-arm record and needs no schema change. |
| Additive `--require-language` flag | New `sif eval --embedder-ab` command | D-11 forbids a new command; the flag is the minimal additive surface and only affects sampling when set. |
| Reuse `noise_gate`/`paired_bootstrap` | Hand-rolled bootstrap or a new confidence interval | Duplicating metric math would break comparability with Phase 18 and the committed bench evidence. |
| Raw HF/ST arm | GGUF Harrier arm (MODEL-F1) | Deferred; GGUF pooling/quantization is a separate conditional follow-up. |
| Two scratch arms | Reset vectors in one index between arms | One vec0 table is one vector space; in-place reset risks identity mixing and destroys the independent-identity proof. |

**Installation:** none. This phase adds no runtime dependency. The only new artifact is a model download (~1.19 GB) into the existing model cache.

## Package Legitimacy Audit

**Packages installed by this phase:** none. No npm/PyPI install step, so the package-legitimacy gate is not triggered.

The only external artifact is a model repository. Its provenance row:

| Artifact | Source | Age / signals | Verdict | Disposition |
|----------|--------|---------------|---------|-------------|
| `microsoft/harrier-oss-v1-0.6b` (safetensors, 1.19 GB) | Hugging Face, official `microsoft` org | 217,170 downloads; 339 likes; MIT; `library_name: sentence-transformers`; last modified 2026-03-30 | Approved | Downloaded into the existing SIF model cache; revision recorded in the arm identity and verdict artifact |

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** none.

## Architecture Patterns

### System Architecture Diagram

```
                      same corpus snapshot (paths + checksums identical)
                                │
             ┌──────────────────┴───────────────────┐
             ▼                                      ▼
   Arm A: scratch DB A                     Arm B: scratch DB B
   collection add (same roots)              collection add (same roots)
   index update                             index update
   index embed --force                      index embed --force
   env: Qwen3 / modelscope / no prompts     env: Harrier / sentence_transformers
        │                                        │
        ▼                                        ▼
   index_meta identity A                    index_meta identity B
   (source=verified, 1024d, none/none)      (source=verified, 1024d,
                                             web_search_query/none, rev)
        │                                        │
        ▼                                        │
   sif eval --personal --json                   │
   (+ --require-language en --require-language zh)
        │                                        │
        ├── saved run A (auto-saved) ────────────┤
        │   corpus fingerprint, query set,       │
        │   model dict (name/type/dim)           │
        ▼                                        ▼
   adequacy preflight                    sif eval --personal --compare savedA --json
   (per-language held-out N)                    │
        │                                       ▼
        │                             ComparisonReport: overall heldout winner,
        │                             splits, legs, leg_splits, language_splits,
        │                             groups, suppressed, replay
        │                                       │
        └─────────── identity A + identity B + costs + env ───────────┐
                                                                       ▼
                                                     pure verdict rule (embedder_verdict.py)
                                                     rule (a): heldout.winner
                                                     rule (b): each language mean Δ >= -0.01
                                                     adequacy: each language heldout N >= 10
                                                                       │
                                                                       ▼
                                                     committed verdict artifact
                                                     + docs/benchmarking.md section
                                                                       │
                                            pass ──► flip Settings default + docs/tests
                                            fail ──► keep Qwen3, record numbers
                                     insufficient ──► keep Qwen3, record counts
```

### Pattern 1: two isolated scratch arms, each with its own verified identity

**What:** Build one file-backed DB per arm from the same resolved corpus roots, run `collection add` + `index update` + `index embed --force` with a pinned env, then evaluate each arm against the same query set.

**When to use:** Always for this phase. Never place two embedders' vectors in one vec0 table.

**Exact sequence (runbook core; `--require-language` is the additive Plan 23-01 change - without it the run is language-blind):**

```bash
# Shared arm environment (values pinned; unset everything else that could override)
# Every command uses the same env for its arm. -q is mandatory for --json purity.
# Arm A: Qwen3 baseline (byte-identical to today's default path)
env -u SIF_QUERY_PROMPT_NAME -u SIF_DOCUMENT_PROMPT_NAME -u SIF_MODEL_PATH -u SIF_DB_PATH \
  SIF_MODEL_TYPE=modelscope \
  SIF_MODEL_NAME=Qwen/Qwen3-Embedding-0.6B \
  SIF_EMBEDDING_DIM=1024 SIF_MAX_TOKENS=512 SIF_BATCH_SIZE=32 \
  SIF_CHUNK_SIZE=512 SIF_CHUNK_OVERLAP=128 SIF_CACHE_EMBEDDINGS=1 \
  python -m sif.cli.main -q --index .planning/tmp/phase-23/qwen3.db \
  collection add /path/to/corpus --name phase23
env ...same-as-above... python -m sif.cli.main -q --index .planning/tmp/phase-23/qwen3.db index update
env ...same-as-above... python -m sif.cli.main -q --index .planning/tmp/phase-23/qwen3.db index embed --force
env ...same-as-above... python -m sif.cli.main -q --index .planning/tmp/phase-23/qwen3.db \
  eval --personal --all --require-language en --require-language zh --json > arm-a.json

# Arm B: Harrier native (same corpus, same chunker/config)
env -u SIF_QUERY_PROMPT_NAME -u SIF_DOCUMENT_PROMPT_NAME -u SIF_MODEL_PATH -u SIF_DB_PATH \
  SIF_MODEL_TYPE=sentence_transformers \
  SIF_MODEL_NAME=microsoft/harrier-oss-v1-0.6b \
  SIF_EMBEDDING_DIM=1024 SIF_MAX_TOKENS=512 SIF_BATCH_SIZE=32 \
  SIF_CHUNK_SIZE=512 SIF_CHUNK_OVERLAP=128 SIF_CACHE_EMBEDDINGS=1 \
  python -m sif.cli.main -q --index .planning/tmp/phase-23/harrier.db \
  collection add /path/to/corpus --name phase23
env ...same-as-above... python -m sif.cli.main -q --index .planning/tmp/phase-23/harrier.db index update
env ...same-as-above... python -m sif.cli.main -q --index .planning/tmp/phase-23/harrier.db index embed --force
env ...same-as-above... python -m sif.cli.main -q --index .planning/tmp/phase-23/harrier.db \
  eval --personal --all --compare <arm-a saved run path> --json > arm-b.json
```

(`...same-as-above...` stands for the exact same `env -u ... VAR=...` prefix as its arm; the runbook builds an env dict and passes it to `subprocess.run`, so no shell variable is necessary. `SIF_QUERY_PROMPT_NAME`/`SIF_DOCUMENT_PROMPT_NAME` must be unset for Harrier so the known-model table supplies `web_search_query`; setting them to an empty string would disable the prompt and cripple the arm.)

`-q` is mandatory: the ModelScope loader prints `Downloading Model from ... to directory: ...` to stdout on every load, even when the model is cached. Verified this session; with `set_quiet(True)` the line is fully suppressed and stdout carries only the JSON.

**Identity proof per arm (read-only, before any eval):**

```python
from sif.embedding.identity import EmbedderIdentity, read_identity

stored_a = read_identity(conn_a)   # EmbedderIdentity
stored_b = read_identity(conn_b)
assert stored_a is not None and stored_a.source == "verified"
assert stored_b is not None and stored_b.source == "verified"
assert stored_a.dimension == stored_b.dimension == 1024
assert stored_a.cache_model_id == "modelscope:Qwen/Qwen3-Embedding-0.6B"
assert stored_b.model_name == "microsoft/harrier-oss-v1-0.6b"
assert stored_b.model_type == "sentence_transformers"
assert stored_b.query_prompt == "web_search_query"
assert stored_b.document_prompt is None
assert stored_a.fingerprint() != stored_b.fingerprint()
```

Then, before each eval, load the arm's model under that arm's env and require `check_identity(conn, current, mode="search").status == "ok"`. This is the guard against the search path's documented same-dimension behavior: a mismatch only warns once and marks results, it does **not** refuse, so a wrong env would otherwise produce plausible-looking garbage numbers.

### Pattern 2: the two-sided verdict as a pure rule over Phase 18 gates

**What:** A new pure module (`src/sif/search/embedder_verdict.py`) takes the comparison gates and returns one of three decisions plus machine-readable reasons.

**Decision inputs (all already computed or additively available):**

| Rule element | Source | Status |
|--------------|--------|--------|
| Rule (a): overall held-out CI excludes 0, mean Δ >= 0.01 | `ComparisonReport.splits["heldout"].winner` / `warrants_default_change` | Exists today |
| Rule (a) extra: the 1/N noise-floor veto | `GateResult.exceeds_floor` folded into `.winner` | Exists today |
| Rule (b): per-language held-out mean Δ >= -0.01 | **Missing**: no per-language held-out aggregate; `groups` covers both splits and `leg_splits` has no language axis | Additive |
| Adequacy: each required language held-out N >= 10 | Derivable from the saved run's `queries[].language`/`.split`, but not aggregated in the comparison | Additive |
| Per-language x per-leg verdicts (report only) | **Missing** as a split-scoped aggregate | Additive |
| N, deltas, CIs, helped/hurt/unchanged | `GateResult.to_dict()` | Exists today |

**Prescriptive helper shape (additive, no CLI command):**

```python
# src/sif/search/personal_bench.py
def language_noise_gates(
    saved_queries: Sequence[SavedQueryRecord],
    baseline_values: Sequence[float],
    current_values: Sequence[float],
) -> dict[str, dict[str, GateResult]]:
    """Per-language per-split paired gates, in LANGUAGES order."""

def leg_language_noise_gates(
    saved_queries: Sequence[SavedQueryRecord],
    baseline_values: Sequence[float],
    current_values: Sequence[float],
) -> dict[str, dict[str, dict[str, GateResult]]]:
    """Per-leg x per-language x per-split gates for the MODEL-01 report."""
```

Add to `ComparisonReport` (defaulted fields at the end, so the only constructor site and existing tests stay valid) and to `to_dict()`:

```python
language_splits: dict[str, dict[str, GateResult]] = field(default_factory=dict)
leg_language_splits: dict[str, dict[str, dict[str, GateResult]]] = field(default_factory=dict)
```

`compare_saved_run` already has both per-query series in hand (`baseline_ndcg`, `current_ndcg`) and the saved records (language/split), so these gates cost one more grouping pass. The verdict helper then needs no re-derivation of baseline grades (which are private today).

**Verdict rule (prescriptive):**

```python
decision = (
    "adopt-harrier"
    if adequate and comparison.splits["heldout"].winner and floor_ok
    else "keep-qwen3" if adequate
    else "insufficient-evidence"
)
```

with `adequate = all(language_heldout[lang].n >= SUPPRESS_BELOW for lang in ("en", "zh"))` and
`floor_ok = all(round(language_heldout[lang].mean_delta, 6) >= -EPSILON for lang in ("en", "zh"))`.

Record the literal booleans too (`ci_excludes_zero`, `mean_delta_at_least_epsilon`, `above_noise_floor`) so a rejection is auditable even when `.winner` bundles four conditions.

### Pattern 3: language-aware adequacy widening (required by D-07)

**What:** Extend `ensure_heldout` with an opt-in `required_languages` parameter and add a `--require-language` CLI option. Widen while any required language's held-out count is below `SUPPRESS_BELOW` and the sample is below the cap; at the cap, raise a counted `ValueError` naming per-language held-out counts.

**Why it is needed:** today the widening condition is exactly:

```python
while (len(accepted) < MIN_QUERIES or heldout < HELDOUT_MIN) and limit < hard_cap:
```

`[VERIFIED: src/sif/search/personal_bench.py:1058]`. It never inspects language. A bilingual corpus whose first hash-prefix documents are English stops at 50 documents and can report adequacy that the per-language gate then rejects - or, worse, the run proceeds with no zh evidence.

**Prescriptive shape:**

```python
def ensure_heldout(
    metadata, conn, *, initial=INITIAL_SAMPLE_DOCUMENTS, cap=MAX_SAMPLE_DOCUMENTS,
    required_languages: Sequence[str] = (),
) -> tuple[list[DocumentRecord], SynthesisResult]:
```

- Default `()` preserves every existing call and test byte-for-byte.
- The loop adds `or _language_floor_unmet(synthesis.queries, required_languages)`.
- The final error message adds per-language held-out counts (e.g. `en=31, zh=6`) so the runbook can record exact evidence.
- A helper `heldout_language_counts(queries)` is public enough for the verdict/artifact tests.

**CLI:** `--require-language` (multiple, `click.Choice(LANGUAGES)`), default empty, help text naming the 10-query floor. This is an additive flag, not a new command, so `make docs-generate` must regenerate `docs/cli-reference.md`.

### Pattern 4: runbook as a resumable stage machine

**What:** `scripts/harrier_eval.py` orchestrates the two arms in separate subprocesses, writes a run-state JSON with stage markers, and is re-runnable after a partial embed.

**Stages:** preflight environment -> build arm A index -> adequacy preflight -> embed arm A -> eval arm A -> build arm B index -> verify fingerprint -> embed arm B -> eval arm B -> verify query-set identity -> verdict -> artifact -> optional cleanup.

**Key properties:**
- Every `sif` call is `[sys.executable, "-m", "sif.cli.main", "-q", "--index", db, ...]` with a per-arm env dict; never import `sif` into the orchestrator and rely on `get_settings()` after changing env (it is `@lru_cache`d).
- A hidden `probe` mode re-invokes the script with the arm env to load the model and print `identity.to_json()` + `check_identity(...).status`; this avoids polluting the orchestrator process and validates loadability before the long embed.
- `--dry-run` prints every command + env dict + the planned artifact record; tests assert it.
- `--keep-arms` and a scratch-root guard (resolved path must be under the declared scratch root) protect cleanup.
- Cost/provenance per arm: `time.monotonic` around each subprocess, DB counts (`documents`, `document_chunks`, `document_embeddings`), cache rows before/after by `model_id`, identity JSON, corpus fingerprint, query-set fingerprint, environment probe, git HEAD/dirty.

### Recommended Project Structure

```
src/sif/
├── search/
│   ├── personal_bench.py        # + language gates, + ensure_heldout(required_languages)
│   └── embedder_verdict.py      # NEW: pure two-sided verdict rule and decision constants
├── cli/commands/
│   └── eval.py                  # + --require-language, pass-through only
scripts/
└── harrier_eval.py              # NEW: runbook / orchestrator / artifact writer
tests/unit/
├── search/
│   ├── test_personal_bench.py   # + language splits + language-aware widening (existing)
│   └── test_embedder_verdict.py # NEW: table-driven gate cases
├── cli/
│   └── test_eval.py             # + --require-language, cross-model comparison (existing)
└── scripts/
    ├── __init__.py              # NEW, matching tests/unit/*/__init__.py convention
    └── test_harrier_eval.py     # NEW: dry-run, identity checks, artifact record
.planning/phases/23-harrier-gated-evaluation/
├── bench/
│   └── harrier-verdict.json     # committed verdict artifact (Phase 19 precedent)
└── 23-VALIDATION.md
.planning/tmp/phase-23/          # scratch DBs (untracked, deleted after the verdict)
```

### Anti-Patterns to Avoid

- **Putting both arms' vectors in one index.** One vec0 table is one vector space; the same-width trap is real (both models are 1024-dim, last-token pooled). Always two DBs.
- **Trusting a search-path warning as the identity guard.** A same-dimension mismatch warns once and marks results but still evaluates; the runbook must assert `check_identity(...).status == "ok"` before each eval.
- **Hand-building the verdict from raw saved-run JSON with a custom bootstrap.** Reuse `noise_gate`/`paired_bootstrap` and the `GateResult` fields.
- **Adding a new public `sif eval --embedder-ab` command.** Use the existing command plus one additive flag.
- **Committing the saved runs or arm DBs.** They contain personal query text/paths; commit only aggregates and hashes.
- **Running the eval without `-q` and parsing stdout as JSON.** ModelScope prints a download line to stdout even when cached.
- **Clearing the shared embedding cache to "make it fair".** Cache buckets already separate models/revisions/prompts; clearing destroys the user's cache and hides real embed cost.
- **Widening the sample without a language condition and calling it adequate.** This is the current behavior and the reason D-07's remedy does not yet exist.

## Recommended Plan Split

1. **23-01 - Instrument additions (no models):** `language_noise_gates` / `leg_language_noise_gates`, `ComparisonReport` fields + `to_dict`, `compare_saved_run` wiring, `ensure_heldout(required_languages=...)`, `--require-language`, the pure `embedder_verdict.py`, and their unit/CLI tests. Regenerate `docs/cli-reference.md` for the new flag.
2. **23-02 - Runbook and record building:** `scripts/harrier_eval.py` with preflight, per-arm env, probe mode, dry-run, stage machine, identity/fingerprint assertions, cost capture, artifact writer, and cleanup guard; tests with stubs and dry-run.
3. **23-03 - Real evidence run (manual checkpoint):** corpus selection and adequacy preflight, both arm builds and evals, verdict artifact, `docs/benchmarking.md` section, environment/cost record. If adequacy fails, either curate a bilingual scope or record `insufficient-evidence` and escalate - do not claim a verdict.
4. **23-04 - Conditional default flip (only on `adopt-harrier`):** Settings defaults, `EmbeddingConfig` defaults (consistency), test updates (`test_settings.py`, `test_bench_snapshot.py` D-19 block), explicit-Qwen3 zero-delta re-comparison on the same arm DB, hand-maintained default-claim docs sweep, `make docs-generate`, changelog entry, full suite. If the verdict is not a pass, this plan records "not applicable" with the artifact path and makes no code change.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Paired bootstrap CI | A new bootstrap / t-test / normal approximation | `paired_bootstrap`, `noise_gate`, `percentile` in `src/sif/search/personal_bench.py` / `benchmark.py` | The 10,000-resample seeded gate is the Phase 18 contract; a different method makes the baseline incomparable. |
| Gate arithmetic | A parallel "winner" function | `GateResult.winner` / `ComparisonReport.splits["heldout"].winner` | Already encodes N>=10, CI excludes zero, rounded Δ>=0.01, and the 1/N floor. |
| Corpus identity | A new checksum | `corpus_fingerprint` + `require_matching_corpus` | Already hashes `path\0checksum\0file_size` over all in-scope docs and refuses mismatches. |
| Saved-run handling | Ad-hoc JSON reads | `load_saved_run` / `SavedRun` / `run_to_saved` | Full envelope validation, size caps, rank-aligned ids, atomic writes. |
| Target resolution across arms | Name/path heuristics | `resolve_saved_targets` | Id-first with a unique-path fallback; refuses ambiguity. |
| Query synthesis and splits | A new query set for Phase 23 | `ensure_heldout`, `synthesize_known_item_queries`, `split_queries` | D-06 requires the Phase 18 instrument verbatim. |
| Model loading and prompt roles | Direct `SentenceTransformer` calls | `EmbeddingManager` + `EmbeddingManager.from_settings` + `EmbeddingManager.embed_query`/`embed_documents` | Role-aware prompt scheme, identity, cache buckets, and batch sanity are already wired. |
| Identity comparison | Field-by-field string comparison in the script | `read_identity`, `EmbedderIdentity.from_json`, `identity_matches`, `check_identity` | Unknown-tolerance (legacy/ModelScope revision) and the documented mismatch semantics. |
| Verdict artifact schema | A bespoke "report" blob | `GateResult.to_dict()` verbatim + a small envelope | The Phase 19 `d12-verdict.json` precedent embeds gate dicts verbatim; reviewers can diff them. |

## Common Pitfalls

### Pitfall 1: The 1/N noise floor makes a 0.01 win impossible below 101 held-out queries
**What goes wrong:** A run with 50 held-out queries and a mean Δ of 0.015 has a CI that excludes zero and Δ >= 0.01, but `.winner` is False because `abs(mean_delta) > 1/N` is `0.015 > 0.02` = False. The team concludes "no win" even though rule (a)'s headline conditions looked satisfied.
**Why it happens:** `noise_gate` adds the displayed 1/N floor as a hard veto `[VERIFIED: src/sif/search/personal_bench.py:1824-1846]` — quote: `winner=sufficient and excludes_zero and improvement and exceeds_floor,` — at N=25 the floor is 0.04, at N=50 it is 0.02, at N=100 exactly 0.01 (strict `>` fails), and only at N>100 can a 0.01 delta pass.
**How to avoid:** Report the held-out N and the implied minimum detectable delta in the artifact; record `min_heldout_for_epsilon_win = 101`. Do not plan a 0.01 win on a 50-100-query corpus. If the user intended D-08's literal two conditions without the floor, that is an explicit gate change to confirm, not an implementation accident.
**Warning signs:** `mean_delta >= 0.01`, `ci_low > 0`, `winner == false`, `noise_floor > mean_delta`.

### Pitfall 2: Language adequacy is not enforced by the current instrument
**What goes wrong:** The sample stops as soon as total accepted >= 50 and held-out >= 25; both can be met with zero Chinese queries, and the per-language gate later finds no zh evidence (or the run proceeds and the verdict is "insufficient").
**Why it happens:** `ensure_heldout`'s widening condition is language-blind `[VERIFIED: src/sif/search/personal_bench.py:1058]` — quote: `while (len(accepted) < MIN_QUERIES or heldout < HELDOUT_MIN) and limit < hard_cap:` and no language term appears in the loop.
**How to avoid:** Add language-aware widening (opt-in) and run an adequacy preflight on the baseline arm DB *before* the expensive embed. If zh held-out < 10 at the cap, record `insufficient-evidence` and keep Qwen3.
**Warning signs:** `splits["heldout"] >= 25` but a language gate has `n < 10`; `mixed` dominates the language distribution.

### Pitfall 3: The available personal corpus is almost entirely English
**What goes wrong:** The phase scopes "the user's personal corpus", but the only large local Markdown collection measures at ~1.1% zh titles and ~2.3% documents with >=10% CJK bodies. A 250-document sample would contain roughly 6 Chinese documents, producing only a handful of zh held-out queries.
**Why it happens:** The instrument samples by `sha256(path + NUL + checksum)` over the whole in-scope corpus; the sample is not language-stratified. Corpus scope is the only lever.
**How to avoid:** Make corpus selection a user-visible decision. If a bilingual verdict is required, curate a scope with a deliberate Chinese share (for example the Chinese-heavy subfolders plus a representative English set) and let language-aware widening run to the cap; otherwise record `insufficient-evidence`. Do not fabricate or post-hoc reclassify queries.
**Warning signs:** the adequacy preflight reports `zh held-out < 10` at the 250-document cap.

### Pitfall 4: The search path does not refuse a same-dimension identity mismatch
**What goes wrong:** If the Harrier arm's eval runs with the Qwen3 env (or vice versa), the stored identity mismatches the current model, the search path warns once and marks results `vectors_stale`, but the comparison still computes numbers. The result is a plausible-looking verdict built on mutually unintelligible query/document vectors.
**Why it happens:** Phase 21 D-03 is "fail-fast embed, warn + mark search"; eval is a search host `[VERIFIED: src/sif/cli/commands/eval.py:244-269, src/sif/embedding/identity.py:452-494]`.
**How to avoid:** Before each eval, load the arm model in that arm's env and require `check_identity(conn, current, mode="search").status == "ok"`; also fail if captured stderr contains the identity-mismatch warning. Assert the stored identity fields (model, type, prompts, dimension, source, revision present for Harrier).
**Warning signs:** `model_mismatch` true in the comparison, identity-mismatch warnings on stderr, `vectors_stale=True` in results.

### Pitfall 5: The saved `model` dict is not the arm identity
**What goes wrong:** The verdict artifact records only `{model_name, model_type, dimension}`, so the prompt scheme and revision are lost, and a crippled Harrier arm (no query prompt) is indistinguishable from a correct one.
**Why it happens:** `validate_saved_run` rebuilds exactly those three keys `[VERIFIED: src/sif/search/personal_bench.py:1639-1659]` and `run_to_saved` stores `dict(report.model)` `[VERIFIED: src/sif/search/personal_bench.py:1335]`.
**How to avoid:** Read `index_meta['embedder.identity']` from each arm DB with `read_identity` and embed the full identity JSON (including `fingerprint`) in the artifact. Do not extend the versioned saved-run schema.
**Warning signs:** artifact has no `query_prompt`/`revision`; Harrier identity shows `query_prompt: null`.

### Pitfall 6: Document ids are UUIDs, so cross-arm comparison uses the path fallback
**What goes wrong:** Arm A's saved `target_doc_id`/`retrieved_doc_ids` are UUIDs generated in arm A; arm B's fresh DB has different UUIDs. If paths are not unique in scope, `resolve_saved_targets` refuses.
**Why it happens:** `Document.id` defaults to `str(uuid.uuid4())` `[VERIFIED: src/sif/core/models.py:190-205]` — quote: `id: str = field(default_factory=lambda: str(uuid.uuid4()))` — and `resolve_saved_targets` looks up ids first, then requires a unique path `[VERIFIED: src/sif/search/personal_bench.py:2008-2041]`.
**How to avoid:** One collection per arm with the same resolved corpus root, no duplicate indexing of the same path. Record the collection names/roots. Do not try to preserve ids across arms.
**Warning signs:** `Saved query ... target is missing ... matches N current documents`.

### Pitfall 7: ModelScope pollutes stdout even on a cached model
**What goes wrong:** `sif eval --personal --json` output starts with `Downloading Model from https://www.modelscope.cn to directory: ...`, so the runbook's JSON parse fails; the line appears with a warm cache too.
**Why it happens:** `ModelDownloader.download` calls `snapshot_download`, which prints; `ModelScopeEmbedder` only wraps it in `suppress_output()` when `is_quiet()` `[VERIFIED: src/sif/models/download.py:88-98, src/sif/embedding/embedder.py:490-531]`. Verified this session: without quiet, stdout was `Downloading Model from https://www.modelscope.cn to directory: ...` followed by the probe line; with `set_quiet(True)` stdout was only the probe line `[VERIFIED: local subprocess capture 2026-11-16]`.
**How to avoid:** Pass the global `-q` flag (or set the log level to WARNING) for every arm command. Verified this session: with `set_quiet(True)` stdout contains only the probe result; without it the download line appears on stdout.
**Warning signs:** JSON parse error at character 0; a `Downloading Model` line in stdout.

### Pitfall 8: `get_settings()` is process-cached
**What goes wrong:** The runbook sets `SIF_MODEL_NAME` inside the process after importing `sif`; the cached settings keep the old model, and both arms measure Qwen3.
**Why it happens:** `get_settings()` is `@lru_cache`d `[VERIFIED: src/sif/config/settings.py:424-430]`.
**How to avoid:** One subprocess per arm (the recommended design). Never mutate `os.environ` and call `get_settings()` in the same orchestrator process; if unavoidable, call `get_settings.cache_clear()` and re-resolve every derived object.
**Warning signs:** both arm identities identical; `--force` embed does not change the cache bucket.

### Pitfall 9: The ModelScope loader's directory heuristic and Phase 24 scope
**What goes wrong:** `ModelScopeEmbedder` picks `model_path.glob("*")[0]` when the first entry is a directory, which can select `1_Pooling` instead of the model root. The md5 early-cache check and the canonical ModelScope path are also known-buggy.
**Why it happens:** `src/sif/models/download.py` and `ModelScopeEmbedder` predate Phase 24 MODELS-01, which explicitly owns "md5 cache-check bug fixed; deterministic ModelScope path" `[VERIFIED: .planning/REQUIREMENTS.md:78]`. See also the `model_dirs[0]` heuristic at `[VERIFIED: src/sif/embedding/embedder.py:493-500]`.
**How to avoid:** In Phase 23, do not fix these; run the baseline identity probe before the long embed and fail with a clear message if the Qwen3 model cannot load. Escalate the fix to Phase 24. (The cached Qwen3 load succeeded in this session, so the local path works today.)
**Warning signs:** `1_Pooling` in the loaded path; `sentence-transformers` error about missing modules.json; a re-download despite the cache.

### Pitfall 10: MPS is auto-selected and cannot be forced to CPU by settings
**What goes wrong:** The embedder picks CUDA -> MPS -> CPU; on this Mac both arms run on MPS. There is no `SIF_DEVICE` setting, so an operator cannot force CPU from configuration. A reported macOS MPS/joblib deadlock could stall a long encode.
**Why it happens:** `SentenceTransformerEmbedder.__init__`/`ModelScopeEmbedder.__init__` choose the device internally.
**How to avoid:** Keep both arms on the same host/device, run each arm as its own process, do not use multiprocessing in the runbook, record the device and stack in the artifact, and make the runbook resumable. `PYTORCH_ENABLE_MPS_FALLBACK=1` is an environment-level mitigation for unsupported ops, not a device switch. (The MPS deadlock claim was not reproduced or verified this session; a real MPS load+encode smoke test succeeded.)
**Warning signs:** the process stalls during the first batch; MPS OOM; different devices across arms.

### Pitfall 11: Shared embedding cache is safe by bucket, but costs are not what they look like
**What goes wrong:** Both arms share `embeddings_cache.db`. The Qwen3 arm may get many hits from the user's existing index (or none), while the Harrier arm always misses (new model + revision bucket). Reporting only wall time hides the difference; clearing the cache would destroy the user's data.
**Why it happens:** Cache buckets are `model_type:model_name` + optional `|rev@...` + optional `|q@...`/`|d@...` `[VERIFIED: src/sif/embedding/manager.py:245-257]`; the Qwen3 bucket has neither suffix.
**How to avoid:** Record per-bucket row counts before/after each arm; compute `cache_hits = embedded_texts - added_rows` (a repeated chunk within the run is a hit); never clear the shared cache. The per-text connection-per-lookup cache implementation also adds I/O overhead on large corpora - report it, don't "optimize" it in this phase.
**Warning signs:** identical wall times with very different vector counts; Harrier rows appearing under a Qwen3 bucket (impossible unless the identity is wrong).

### Pitfall 12: The chunker/config must be identical, not just the corpus
**What goes wrong:** Different `SIF_CHUNK_SIZE`/`SIF_CHUNK_OVERLAP`/strategy changes the chunk texts and the vector evidence, while the corpus fingerprint still matches (it hashes documents, not chunks).
**Why it happens:** The fingerprint covers documents (path/checksum/size) `[VERIFIED: src/sif/search/personal_bench.py:1106-1115]`; chunk counts are a separate signal.
**How to avoid:** Pin and record `SIF_CHUNK_SIZE=512`, `SIF_CHUNK_OVERLAP=128`, `--chunk-strategy auto`, `SIF_MAX_TOKENS=512`, `SIF_BATCH_SIZE=32`; assert document and chunk counts equal across arms and `document_embeddings == document_chunks`.
**Warning signs:** equal document counts but different chunk counts; different embed wall times with a warm cache.

### Pitfall 13: Corpus drift between arms is a refusal, not a bug
**What goes wrong:** A synced corpus changes a file between arm A and arm B; `--compare` refuses with a fingerprint mismatch.
**Why it happens:** `corpus_fingerprint` includes the checksum (body bytes + canonical frontmatter); an edit moves it.
**How to avoid:** Freeze the corpus for the run, verify the fingerprint early (the refusal happens before the embedder loads, so it is cheap), and rerun both arms after any content change. Never edit the saved run's fingerprint to force a comparison.
**Warning signs:** `Corpus fingerprint mismatch: saved run has ... current index has ...`.

### Pitfall 14: Replay is empty on scratch arms
**What goes wrong:** A fresh scratch DB has no `query_log`, so the replay leg is `available: false`; the report's notes say so, but a reader may think a leg was dropped.
**Why it happens:** Replay reads only the local `query_log`; scratch DBs start empty.
**How to avoid:** Record `replay.available` and the reason in the artifact. Replay never enters the verdict (it is stability, not quality). If the user wants it, seed identical `query_log` rows into both arm DBs before evaluation and record that; do not copy only one side.
**Warning signs:** `replay.available == false`; `num_queries == 0`.

### Pitfall 15: A default flip invalidates every existing index until re-embedded
**What goes wrong:** After a pass, users with Qwen3-built indexes run hybrid search with Harrier query vectors against Qwen3 document vectors (same width, different space). The identity check warns and marks results stale, but ranking is unintelligible until `sif index embed --force` with the new model or an explicit Qwen3 env.
**Why it happens:** The default changes the vector space of new queries; Phase 21's search policy is warn+mark, not refuse.
**How to avoid:** The flip plan must update the migration/default documentation, state the re-embed requirement (or the explicit-Qwen3 escape hatch), keep Qwen3 selectable, and record the consequence in the verdict artifact's decision notes. `models pull` cannot fetch Harrier yet (Phase 24) - do not claim it can.
**Warning signs:** docs still call Qwen3 the default after a flip; the migration doc has no re-embed note; `test_shipped_defaults_are_prompt_free_modelscope_qwen3` fails on purpose but is not updated.

### Pitfall 16: `transformers` version drift can break Harrier loading
**What goes wrong:** The project lock resolves `transformers` 5.5.4; the local evidence env has 4.57.6; an old constrained env could have <4.51 and fail on `Qwen3Model`.
**Why it happens:** ST 5.4.1 allows `transformers>=4.41.0,<6.0.0` `[VERIFIED: installed sentence-transformers 5.4.1 distribution metadata]`, so the dependency spec alone does not guarantee Qwen3 support.
**How to avoid:** Record the exact stack in the artifact, prefer the project-locked uv env for reproducibility (or record why the local env was used), and let the preflight fail loudly if the model cannot load. Qwen3Model is documented in transformers v5.x, so 5.5.4 is safe.
**Warning signs:** `KeyError: 'qwen3'`/`does not recognize this architecture`; a `transformers` version below 4.51.

### Pitfall 17: The artifact path convention is phase-local, not repo-root `bench/`
**What goes wrong:** The plan writes `bench/harrier-verdict.json` at the repo root, but the only tracked precedent is `.planning/phases/19-search-correctness/bench/{b0,b1,d12-verdict}.json`; no repo-root `bench/` exists.
**Why it happens:** `docs/benchmarking.md` refers to `bench/b0.json` as shorthand for the phase's bench directory, and `git ls-files` tracks `.planning/phases/19-search-correctness/bench/{b0,b1,d12-verdict}.json` with no repo-root `bench/` directory `[VERIFIED: git ls-files 2026-11-16]`.
**How to avoid:** Use `.planning/phases/23-harrier-gated-evaluation/bench/harrier-verdict.json`, matching the tracked precedent, and reference it from `docs/benchmarking.md`. Confirm with the user if the literal root `bench/` was intended.
**Warning signs:** a new untracked root `bench/` with no other files.

## Code Examples

### Read and verify an arm identity

```python
# Source: src/sif/embedding/identity.py:385-399, 437-449
from sif.embedding.identity import EmbedderIdentity, check_identity, read_identity

stored = read_identity(conn)
assert isinstance(stored, EmbedderIdentity)
assert stored.source == "verified"
# The Qwen3 arm:
#   cache_model_id == "modelscope:Qwen/Qwen3-Embedding-0.6B"
#   query_prompt is None, document_prompt is None, revision is None, pooling "last_token"
# The Harrier arm:
#   model_name == "microsoft/harrier-oss-v1-0.6b", model_type == "sentence_transformers"
#   query_prompt == "web_search_query", document_prompt is None, revision == the HF commit
#   pooling == "last_token", dimension == 1024, source == "verified"
```

### Compute per-language held-out gates (proposed additive helper)

```python
# Source: pattern of src/sif/search/personal_bench.py:1895-1928 (leg_noise_gates)
def language_noise_gates(saved_queries, baseline_values, current_values):
    if not (len(saved_queries) == len(baseline_values) == len(current_values)):
        raise ValueError("saved queries and both metric series must have equal lengths")
    indices: dict[str, dict[str, list[int]]] = {}
    for index, record in enumerate(saved_queries):
        per_split = indices.setdefault(record.language, {"tuning": [], "heldout": []})
        per_split.setdefault(record.split, []).append(index)
    return {
        language: {
            split: noise_gate(
                [baseline_values[i] for i in per_split.get(split, [])],
                [current_values[i] for i in per_split.get(split, [])],
            )
            for split in ("tuning", "heldout")
        }
        for language, per_split in indices.items()
    }
```

### Two-sided verdict (proposed pure rule)

```python
# Source: GateResult semantics at src/sif/search/personal_bench.py:374-417 and
# the winner expression at :1843; EPSILON at src/sif/search/benchmark.py:33
from sif.search.personal_bench import EPSILON, SUPPRESS_BELOW

def decide(comparison, *, required_languages=("en", "zh"), min_language_n=SUPPRESS_BELOW):
    heldout = comparison.splits["heldout"]
    language_heldout = {
        language: comparison.language_splits.get(language, {}).get("heldout")
        for language in required_languages
    }
    adequate = all(
        gate is not None and gate.n >= min_language_n
        for gate in language_heldout.values()
    )
    floor_ok = all(
        gate is not None and round(gate.mean_delta, 6) >= -EPSILON
        for gate in language_heldout.values()
    )
    if not adequate:
        return "insufficient-evidence"
    return "adopt-harrier" if (heldout.winner and floor_ok) else "keep-qwen3"
```

### Clean stdout for the runbook

```python
# Verified: without quiet, ModelScope prints to stdout even on a cache hit.
cmd = [sys.executable, "-m", "sif.cli.main", "-q", "--index", str(db), "eval",
       "--personal", "--all", "--require-language", "en", "--require-language", "zh",
       "--json"]
proc = subprocess.run(cmd, env=arm_env, capture_output=True, text=True, check=False)
if proc.returncode != 0:
    raise RuntimeError(f"eval failed for {arm}: {proc.stderr[-4000:]}")
payload = json.loads(proc.stdout)   # strict JSON; run_path is in the payload
```

### Query-set identity fingerprint (artifact)

```python
# Mirrors the corpus_fingerprint style at personal_bench.py:1106-1115 (16 hex chars).
import hashlib
lines = [
    f"{record['leg']}\0{record['language']}\0{record['split']}\0{record['query']}"
    for record in saved_run["queries"]
]
query_set_fingerprint = hashlib.sha256("\n".join(lines).encode()).hexdigest()[:16]
# Assert this value is identical for the baseline saved run and the compare run.
# Target ids are deliberately excluded: they are per-arm UUIDs.
```

## State of the Art

| Old approach | Current approach | When changed | Impact |
|--------------|------------------|--------------|--------|
| Width-only dimension guard | Persisted `embedder.identity` with model/type/dimension/pooling/prompt/revision + fingerprint; fail-fast embed, warn+mark search | Phase 21 (v1.2) | The same-width Harrier/Qwen3 swap is detectable; this phase relies on it. |
| Role-less embedding | `embed_query`/`embed_documents` with prompt names; prompt + revision in the cache bucket | Phase 21 (v1.2) | Harrier's mandatory query instruction is expressible; Qwen3 stays prompt-free/byte-identical. |
| One synthetic bench fixture | `sif eval --personal` on the user's corpus with deterministic sampling, 50/50 split, paired bootstrap, saved runs | Phase 18 (v1.2) | The A/B can use the user's own EN+ZH corpus, not a synthetic pack. |
| "Use Qwen3-Embedding-0.6B as the default" | Candidate: Harrier-OSS-v1-0.6b native, gated on EN+ZH held-out evidence | Phase 23 (this phase) | The default changes only on a two-sided gate; Qwen3 remains selectable. |
| Instruction-tuned models used prompt-free | Harrier query prompt `web_search_query`; document none | Phase 21 table, exercised here | Omitting the query prompt measurably degrades Harrier `[CITED: model card]`; the table prevents a crippled arm. |

**Deprecated/outdated:**
- The localGPT A/B numbers (nDCG@10 0.915 vs 0.875) in prior research are not independent evidence and must not be cited `[CITED: .planning/phases/23-harrier-gated-evaluation/23-CONTEXT.md]`; the Phase 23 run is the evidence.
- A width-only dimension check is not a model-swap guard for these two 1024-dim models.
- The saved-run `model` dict is not a full identity record; do not treat it as one.

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|-------|---------|---------------|
| A1 | Harrier weights load under ST 5.4.1 with the installed transformers 4.57.6 and the locked 5.5.4 (config, modules, prompts, and architecture verified; weights not loaded this session). | Standard Stack | A load failure blocks the evidence run; the preflight must fail loudly and the plan must include a remedy (pin/upgrade transformers, or choose the evidence env). |
| A2 | `EmbedderIdentity.revision` will be non-null for Harrier because ST reads `auto_model.config._commit_hash`; verified on a different cached ST model, not on Harrier itself. | Architecture Patterns | If null, the artifact records `revision: null` plus the HF API sha and the cache key loses the revision suffix; the same-width guard still works via model name/prompt. |
| A3 | `transformers` 5.5.4 (uv.lock) supports `Qwen3Model`; the v5.x docs document it, but it was not executed locally (local is 4.57.6). | Standard Stack / Pitfall 16 | A uv-env load failure would force the evidence run onto the local env or a transformers pin. |
| A4 | The Harrier load defaults to the library dtype (likely float32) and MPS on this Mac; the artifact should record the actual stack. | Environment Availability | Memory pressure/OOM at batch 32; lower `SIF_BATCH_SIZE` and record it. |
| A5 | The macOS MPS/joblib deadlock is a real risk (research prompt), but it was not reproduced this session; a real MPS load+encode smoke test succeeded. | Pitfall 10 | A mid-run stall would need process isolation/resume; the runbook is staged. |
| A6 | Rule (a) should use `GateResult.winner` (including the 1/N floor), a superset of D-08's literal "CI excludes 0 and Δ >= 0.01". | Pitfall 1 / Open Questions | If the user intended the literal two conditions, a 0.01-0.04 delta at N<=100 would be rejected by the implementation but accepted by the text. |
| A7 | D-07 adequacy is language-level held-out N >= 10, not every leg × language × length cell. | Pattern 2 / Open Questions | A thin leg×language cell (e.g. body/zh) would be reported as diagnostic rather than blocking the verdict. |
| A8 | The evidence corpus is the operator's choice; the measured local SynologyDrive corpus is ~2% Chinese and likely inadequate without curation. | Pitfall 3 / Open Questions | A run on the current corpus will record `insufficient-evidence`, leaving MODEL-01 without a real A/B. |
| A9 | An additive `--require-language` flag is the acceptable D-11 surface (no new command). | Pattern 3 | If rejected, D-07's widening remedy cannot be honored through the CLI. |
| A10 | The committed artifact belongs under `.planning/phases/23-harrier-gated-evaluation/bench/` (Phase 19 precedent), not repo-root `bench/`. | Pitfall 17 | A root `bench/` would be a new, undocumented convention. |
| A11 | On a pass, `EmbeddingConfig` defaults should move with the Settings defaults for consistency, although D-10 names Settings only. | Plan 23-04 | Leaving `EmbeddingConfig()` at Qwen3 creates two "defaults" that disagree. |
| A12 | Replay is unavailable on scratch arms unless seeded; the verdict does not use replay. | Pitfall 14 | A reader may think the replay leg failed; record the reason. |
| A13 | The evidence environment may be the local conda env (ST 5.4.1 / transformers 4.57.6 / torch 2.7.1) rather than the uv-locked env (transformers 5.5.4); both are valid if recorded. | Environment Availability | Cross-environment vector differences are irrelevant within the A/B; only reproducibility across runs is affected. |
| A14 | A pass requires a docs sweep of hand-maintained default claims, not only `make docs-generate`; Phase 24 still owns the broader install docs. | Plan 23-04 | Stale docs would tell users Qwen3 is still the default. |

## Open Questions

1. **Which corpus will provide EN+ZH adequacy?**
   - What we know: the local default index has 2 documents; the largest local Markdown collection (~6,590 files) is ~2% Chinese by content, and a 250-document sample would contain roughly 6 Chinese documents `[VERIFIED: local filesystem/SQLite probes 2026-11-16]`.
   - What's unclear: whether the user has a different bilingual personal corpus (another machine, a Zotero/EndNote export, or the Chinese-heavy subfolders curated into a scope).
   - Recommendation: make corpus selection and a ~10-minute adequacy preflight an explicit checkpoint before the embed budget is spent; if inadequate, either curate a scope with a deliberate Chinese share or record `insufficient-evidence` and escalate. Do not silently proceed.

2. **Does rule (a) include the Phase 18 1/N floor?**
   - What we know: D-08's text lists "CI excludes 0 and mean Δ >= 0.01"; `GateResult.winner` additionally requires `abs(mean_delta) > 1/N`, which makes a 0.01 win impossible at N <= 100.
   - What's unclear: whether the user wants the stricter implemented gate or the literal text.
   - Recommendation: use `splits["heldout"].winner` (stricter, documented, consistent with D-06 "reuse Phase 18 verbatim") and record the literal booleans + `min_heldout_for_epsilon_win = 101` in the artifact. Confirm in planning.

3. **Is adequacy language-level or per leg × language × length?**
   - What we know: D-07 says "N >= 10 per reported group"; the report's groups are leg × language × length.
   - What's unclear: whether a 12-query zh held-out total spread across thin cells is acceptable.
   - Recommendation: require N >= 10 at the language × held-out level for the verdict; report all leg × language × held-out gates as diagnostics and mark cells below 10 as suppressed/insufficient, never as zero.

4. **Where does the committed verdict artifact live?**
   - What we know: the only tracked precedent is `.planning/phases/19-search-correctness/bench/`; D-09 says "for example `bench/harrier-verdict.json`".
   - What's unclear: whether the user wants a repo-root `bench/` convention created.
   - Recommendation: `.planning/phases/23-harrier-gated-evaluation/bench/harrier-verdict.json`; confirm if root `bench/` was intended.

5. **Should the replay leg be seeded into both scratch arms?**
   - What we know: scratch DBs start with an empty `query_log`; replay is stability, not quality, and never gates defaults.
   - What's unclear: whether a missing replay leg is acceptable in the evidence report.
   - Recommendation: leave it empty and record `available: false` with the reason; if the user wants it, copy identical `query_log` rows into both arms before evaluation.

6. **Does a pass change `EmbeddingConfig` defaults and the hand-maintained docs?**
   - What we know: Settings is the user-facing default; `EmbeddingConfig` has its own Qwen3 literal; many docs name Qwen3 as the default.
   - What's unclear: whether D-10's "Settings default model/type" is meant narrowly.
   - Recommendation: update both defaults and sweep all default claims (`README.md`, `docs/quickstart.md`, `docs/search-algorithms.md`, `docs/models.md`, `docs/mcp-server.md`, `docs/migration.md`, `docs/installation.md`), plus `make docs-generate`; Phase 24 still owns install docs.

7. **Which environment should produce the evidence?**
   - What we know: the local conda env has the locked ST 5.4.1 with transformers 4.57.6 and torch 2.7.1; the uv lock resolves transformers 5.5.4 and torch 2.14/2.15 fleets; `.venv` has no torch/ST/modelscope.
   - What's unclear: whether the operator will use the local env or `uv sync --extra embed`.
   - Recommendation: record the exact stack and git HEAD in the artifact; prefer the uv-locked env if a reproducible fleet is required, otherwise use the local env and state it.

8. **Is `insufficient-evidence` an acceptable phase outcome?**
   - What we know: D-07/D-09 make it first-class and instruct keeping Qwen3.
   - What's unclear: whether MODEL-01 can be marked complete without any real A/B numbers on this machine.
   - Recommendation: treat it as a recorded, non-code outcome only after the user accepts it; otherwise the phase is blocked on a bilingual corpus, not on code.

## Environment Availability

> Local probes on 2026-11-16; dependency versions from `uv.lock` and installed distribution metadata `[VERIFIED: uv.lock, importlib.metadata, local command probes 2026-11-16]`. Corpus/log-index counts are local filesystem/SQLite reads only.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Everything | Yes | 3.13.9 (local); project targets 3.10+ | CI matrix covers 3.10-3.13 |
| sentence-transformers | Harrier + Qwen3 loads | Yes | 5.4.1 (locked) | — |
| transformers | Qwen3Model architecture | Yes | 4.57.6 local; 5.5.4 in `uv.lock` | Use the local evidence env or `uv sync --extra embed` |
| torch | Encoding | Yes | 2.7.1 local; 2.14.1/2.15.0 in lock | — |
| sqlite-vec | vec0 arm indexes | Yes | 0.1.9 | No arm build without it |
| modelscope | Qwen3 baseline path | Yes | 1.36.0 | None for the byte-identical baseline (an ST local-path fallback would change the identity/cache bucket) |
| Hugging Face access | Harrier weights + config | Yes | HTTPS reachable; API/config fetched | Pre-download the snapshot if the network is later unavailable |
| Harrier weights | Harrier arm | No (not cached) | 1.19 GB download | Download during preflight |
| Qwen3 weights | Baseline arm | Yes (cached) | 1.1 GB at `~/Library/Caches/sif/Qwen/Qwen3-Embedding-0___6B` | ModelScope may still need network to resolve the snapshot |
| Apple MPS | Encoding device | Yes | torch 2.7.1 | CPU only via environment-level workarounds; no SIF setting |
| Disk space | Two arm DBs + cache growth | Yes | ~348 GiB free | Clean scratch DBs after the verdict |
| Default personal index | Personal bench | No | 2 documents at `~/Library/Application Support/sif/sif.db` (no vec0/index_meta); 0 documents at `~/.local/share/sif/sif.db` | Build both arms from an explicit corpus root |
| Bilingual personal corpus | EN+ZH adequacy | At risk | `~/SynologyDrive`: 6,590 Markdown files; ~1.1% zh titles, ~2.3% CJK bodies | Curate a bilingual scope or record insufficient evidence |
| uv | Reproducible env | Yes | 0.13.7 | Local conda env |
| `.venv` with embed deps | Runbook interpreter | No | `.venv` lacks torch/ST/modelscope | Use the PATH/conda Python or `uv sync --extra embed` |
| pytest | Validation | Yes | 9.1.1 local / 9.0.3 CI | — |
| git | Provenance | Yes | repo on `dev` | Record `git_head`/dirty; no git requirement for the verdict math |

**Missing dependencies with no fallback:**
- An adequate bilingual personal corpus (a user/corpus dependency, not a code dependency). Without it, the EN+ZH gate cannot produce a verdict; the honest outcome is `insufficient-evidence`.
- sqlite-vec (arm indexes cannot be built without vec0).

**Missing dependencies with fallback:**
- Harrier weights: download (~1.19 GB) during preflight.
- transformers 5.5.4 in the local env: use the local 4.57.6 evidence env and record it, or `uv sync --extra embed`.
- Qwen3 network resolution: the model is cached; if ModelScope is offline, the baseline path may still fail (Phase 24 owns the deterministic path).

## Validation Architecture

> Nyquist validation is enabled (`workflow.nyquist_validation: true` in `.planning/config.json`).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 local / 9.0.3 CI + pytest-cov 7.1.0 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` + `[tool.coverage.report]` (`fail_under = 90`) |
| Quick run command | `pytest tests/unit/search/test_embedder_verdict.py tests/unit/search/test_personal_bench.py tests/unit/cli/test_eval.py tests/unit/scripts/test_harrier_eval.py -x --no-cov` |
| Full suite command | `pytest` (2,889 passed / 1 skipped at Phase 22 close; 95.13% coverage `[VERIFIED: .planning/STATE.md:46]`) |
| Static gates | `ruff check src tests && ruff format --check src tests && ty check src/sif` |
| Docs gate | `make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md` |
| Estimated runtime | Full suite ~3-5 min locally; targeted < 20 s |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| MODEL-01 | Per-language × per-leg held-out gates exist and pair correctly (counts sum to split totals; absent languages are not fabricated; declared order) | unit | `pytest tests/unit/search/test_personal_bench.py -x --no-cov` (new test classes) | Extend existing |
| MODEL-01 | `--compare` across different model identities reports `model_mismatch` and still produces language/leg gates | cli | `pytest tests/unit/cli/test_eval.py -x --no-cov` (new test) | Extend existing |
| MODEL-01 | Both arms evaluate the same query set in saved order at saved `top_k`; query-set fingerprint matches | unit + cli | `pytest tests/unit/search/test_personal_bench.py::TestCompareSavedRun tests/unit/cli/test_eval.py::TestCompareCli -x --no-cov` | Existing + extension |
| MODEL-01 | Two-arm fixture: baseline saved run + candidate comparison yields the expected verdict record | integration (fixture DBs) | `pytest tests/unit/scripts/test_harrier_eval.py -x --no-cov` | New |
| MODEL-01 | Harrier query prompt is `web_search_query`, document prompt is `None`; an unknown prompt name fails loudly | unit | `pytest tests/unit/embedding/test_identity.py::test_known_harrier_model_gets_query_prompt -x --no-cov` + the ST embedder prompt test | Existing |
| MODEL-01 | Language-aware widening reaches a late Chinese doc block and raises with per-language counts at the cap | unit | `pytest tests/unit/search/test_personal_bench.py::TestEnsureHeldout -x --no-cov` (new cases) | Extend existing |
| MODEL-02 | Two-sided gate: adopt only when overall held-out winner + both language floors + adequacy; all rejection reasons are named | unit | `pytest tests/unit/search/test_embedder_verdict.py -x --no-cov` | **Wave 0: new file** |
| MODEL-02 | Boundary: Δ=0.01 at N=100 is not a winner; N=101 is; CI including 0 is never a winner; language mean -0.02 vetoes | unit | same | **Wave 0: new file** |
| MODEL-02 | No-win leaves settings/defaults untouched (no code path mutates them) | unit | `pytest tests/unit/config/test_settings.py tests/unit/search/test_bench_snapshot.py -x --no-cov` | Existing |
| MODEL-02 | A pass flips Settings, regenerates docs, and the explicit-Qwen3 path reproduces the baseline with zero deltas | unit + manual | `pytest tests/unit/config/test_settings.py tests/unit/search/test_bench_snapshot.py -x --no-cov`; manual `--compare` zero-delta on the same arm DB | Existing + manual |
| MODEL-01/02 | Runbook dry-run builds the exact per-arm commands/env (no prompt overrides for Harrier; explicit Qwen3; `-q`; `--index`) | unit | `pytest tests/unit/scripts/test_harrier_eval.py::TestDryRun -x --no-cov` | **Wave 0: new file** |
| MODEL-01/02 | Runbook identity checker rejects a swapped, prompt-free, wrong-dimension, or unverified identity | unit | `pytest tests/unit/scripts/test_harrier_eval.py::TestIdentityGate -x --no-cov` | **Wave 0: new file** |
| MODEL-01/02 | Runbook artifact builder emits the documented schema (decision, arms, corpus/query fingerprints, gates, costs, environment) | unit | `pytest tests/unit/scripts/test_harrier_eval.py::TestArtifact -x --no-cov` | **Wave 0: new file** |
| MODEL-01/02 | Scratch cleanup refuses paths outside the declared scratch root | unit | `pytest tests/unit/scripts/test_harrier_eval.py::TestCleanupGuard -x --no-cov` | **Wave 0: new file** |
| ALL | Lint/format/type gates | static | `ruff check src tests && ruff format --check src tests && ty check src/sif` | Existing |
| ALL | Generated docs current after the new flag (and after a default flip) | docs | `make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md` | Existing |

### Sampling Rate

- **Per task commit:** targeted pytest for the touched module + `ruff check` + `ruff format --check`.
- **Per wave merge:** full `pytest` + `ty check src/sif`; `make docs-generate` no-diff.
- **Phase gate:** full suite green; the verdict artifact and `docs/benchmarking.md` section committed; the manual evidence run recorded with environment, HEAD, corpus/query fingerprints, N, deltas, CIs, and the decision; if a pass, the explicit-Qwen3 zero-delta proof recorded.

### Wave 0 Gaps

- [ ] `tests/unit/search/test_embedder_verdict.py` - table-driven two-sided rule (new).
- [ ] `tests/unit/search/test_personal_bench.py` - language/leg-language split gates + language-aware widening cases (extend).
- [ ] `tests/unit/cli/test_eval.py` - `--require-language` parsing/forwarding + cross-model comparison with the new keys (extend).
- [ ] `tests/unit/scripts/__init__.py` + `tests/unit/scripts/test_harrier_eval.py` - runbook dry-run/identity/artifact/cleanup tests (new).
- [ ] A bilingual fixture helper or explicit mixed-language `titles`/`bodies` in `tests/support/eval.py` usage (no new runtime dep).
- [ ] `docs/cli-reference.md` regenerated for `--require-language`.
- [ ] No framework install: pytest/pytest-cov are already locked dev deps.

### Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real two-arm evidence run on the personal EN+ZH corpus | MODEL-01 | Requires a real 1.19 GB model download, a real corpus, and hours of local embedding; results are hardware/version-dependent and cannot gate CI | Run `python scripts/harrier_eval.py --corpus <roots> --json`; record the artifact path, environment, per-arm counts/wall time/cache deltas, N, deltas, CIs, and the decision; commit the aggregate artifact + the `docs/benchmarking.md` section only. |
| Default flip and explicit-Qwen3 byte-identical proof | MODEL-02 | Only runs after a real pass; the Qwen3 arm DB and saved run live locally | After the flip, rerun the Qwen3 arm's `sif eval --personal --compare <pre-flip Qwen3 saved run>` on the same arm DB with explicit Qwen3 env; require every overall/language/leg delta to be exactly 0.0 and the identity unchanged; record it. |
| Corpus adequacy preflight | MODEL-01/02 | Depends on the operator's corpus choice | Run the preflight on the baseline arm DB; report per-language held-out counts; if zh < 10 at the cap, record `insufficient-evidence` and escalate before embedding. |

## Security Domain

`security_enforcement` is absent from `.planning/config.json`, so it is enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No auth surface; local CLI. |
| V3 Session Management | No | No sessions. |
| V4 Access Control | No | Single-user local files. |
| V5 Input Validation | Yes | New `--require-language` validated against `LANGUAGES`; runbook paths resolved and scratch cleanup prefix-guarded; saved runs loaded through `load_saved_run` (type/range/enum/envelope validation); model ids are not interpolated into SQL (there is no SQL on model ids). |
| V6 Cryptography | No hand-rolled crypto | `hashlib.sha256` for fingerprints and file hashes; no new secret handling. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Same-width model swap silently mixing vector spaces | Spoofing / Tampering | Per-arm isolated DBs; full `index_meta` identity assertion; `check_identity(...).status == "ok"` before each eval; different identity fingerprints. |
| Wrong-arm env producing plausible garbage metrics | Tampering | Per-arm subprocess env; identity probe; fail on identity-mismatch warnings in stderr; record both identities in the artifact. |
| Personal note content/paths committed to git | Information Disclosure | Artifact contains aggregates, hashes, model identities, counts, and gates only; saved runs/arm DBs stay local; corpus label/hashes instead of absolute paths. |
| Runbook cleanup deleting outside its scratch area | Elevation / Destructive | Resolve the scratch path; refuse `/`, home, and paths outside the declared scratch root; `--keep-arms`; delete only the run's own DB files. |
| Model supply-chain substitution | Tampering | Official `microsoft` HF repo; MIT; record the resolved revision and identity fingerprint; the cache key includes the revision; a mid-run revision move is detected by the identity check. |
| Unbounded embed time/disk use | Denial of Service | Stage markers and resume; report docs/chunks/wall time/cache deltas; `--keep-arms`; disk precheck; lower `SIF_BATCH_SIZE` on OOM. |
| Forged/tampered saved run | Tampering | `load_saved_run` validates the whole envelope; corpus fingerprint is recomputed from the current metadata, never trusted from the file; targets resolve id-first with a unique-path fallback. |

## Sources

### Primary (HIGH confidence - read from source or executed locally this session)

- `src/sif/search/personal_bench.py` - `SavedRun`, `ComparisonReport`, `GateResult`, `noise_gate`, `paired_bootstrap`, `ensure_heldout`, `corpus_fingerprint`, `compare_saved_run`, `leg_noise_gates`, `group_noise_gates`, `resolve_saved_targets`.
- `src/sif/cli/commands/eval.py` - `run_personal`, `_run_fresh`, `_run_compare`, `_load_embedder`, `_search_identity_check`, `_save_run`, `_search_fn`, `_index_path`.
- `src/sif/embedding/identity.py` - `EmbedderIdentity`, `read_identity`, `identity_matches`, `check_identity`, `build_identity`, `schema_embedding_dim`.
- `src/sif/embedding/prompts.py` - `_KNOWN_PROMPT_SCHEMES`, `resolve_prompt_scheme`.
- `src/sif/embedding/manager.py` - `from_settings`, `_cache_model_id`, `_cache_bucket`, `_embed_role`, `get_identity`.
- `src/sif/embedding/embedder.py` - `SentenceTransformerEmbedder` (prompt roles, `max_seq_length`, `pooling_mode`, `revision`), `ModelScopeEmbedder`.
- `src/sif/embedding/cache.py` - `(content_hash, model_id)` key and `get_stats`.
- `src/sif/indexing/embed_writer.py` - first-write identity claim and `source="verified"`.
- `src/sif/cli/commands/index.py` - `embed_cmd` flags, fail-fast identity check, certification.
- `src/sif/config/settings.py` - model defaults, cache dir, chunk/batch defaults.
- `src/sif/models/embedding.py` - `EmbeddingConfig` defaults.
- `src/sif/core/models.py` - `Document.id` UUID default.
- `src/sif/cli/commands/collection.py` - `Path(path).resolve()`.
- `src/sif/database/schema.py` / `repositories.py` - `index_meta` table and repository.
- Installed `sentence-transformers` 5.4.1 source (`sentence_transformer/model.py`, `base/model.py`, `base/modules/transformer.py`) - prompt merge, `_resolve_prompt`, revision path, `Normalize.load` path-ignoring.
- Local smoke tests 2026-11-16: `AutoConfig.from_pretrained("microsoft/harrier-oss-v1-0.6b")`; `SentenceTransformerEmbedder` with a cached ST model on MPS (prompt divergence, revision, pooling); `ModelScopeEmbedder("Qwen/Qwen3-Embedding-0.6B")` (dim 1024, pooling `last_token`, revision `None`, unit norm); stdout capture showing ModelScope's download line and its suppression under `set_quiet(True)`.
- Local filesystem measurements: `~/Library/Application Support/sif/sif.db` (2 docs, no vec0/index_meta), `~/.local/share/sif/sif.db` (0 docs), `~/SynologyDrive` (6,590 `.md`; 999-file sample: 11 zh titles, 23 with >=10% CJK bodies), cached Qwen3 1.1 GB, 348 GiB free.

### Secondary (MEDIUM confidence - official documentation / model card)

- [Hugging Face model card: microsoft/harrier-oss-v1-0.6b](https://huggingface.co/microsoft/harrier-oss-v1-0.6b) - parameter table, MIT, last-token pooling + L2 normalization, 32,768 max tokens, multilingual incl. `zh`, query-instruction requirement, "no need to add instructions to the document side".
- [Hugging Face model API](https://huggingface.co/api/models/microsoft/harrier-oss-v1-0.6b) - id, sha `f9b9dc8d367d443f2479d27aa5d8d2850c0774ee`, lastModified 2026-03-30, downloads 217,170, likes 339, license `mit`, library `sentence-transformers`, siblings.
- [Hugging Face raw `config.json`](https://huggingface.co/microsoft/harrier-oss-v1-0.6b/raw/main/config.json) - `Qwen3Model`, `qwen3`, `hidden_size` 1024, `max_position_embeddings` 32768, no `auto_map`.
- [Hugging Face raw `config_sentence_transformers.json`](https://huggingface.co/microsoft/harrier-oss-v1-0.6b/raw/main/config_sentence_transformers.json) - prompts `web_search_query`/`sts_query`/`bitext_query`, `default_prompt_name: null`.
- [Hugging Face raw `modules.json`](https://huggingface.co/microsoft/harrier-oss-v1-0.6b/raw/main/modules.json) and [`1_Pooling/config.json`](https://huggingface.co/microsoft/harrier-oss-v1-0.6b/raw/main/1_Pooling/config.json) - Transformer/Pooling/Normalize, last-token pooling, 1024 dimensions.
- [Transformers Qwen3 docs](https://huggingface.co/docs/transformers/model_doc/qwen3) - `Qwen3Model` documented in v5.x.
- Project docs: `docs/benchmarking.md` (personal bench, saved runs, paired-bootstrap gate, manual real-model evidence style), `docs/architecture.md:730` (prompt scheme), `docs/changelog.md`, `docs/migration.md`, `docs/models.md`.
- Phase artifacts: `.planning/phases/18-quality-instrument-personal-bench-rapidfuzz-dym/18-CONTEXT.md` (D-01..D-08), `.planning/phases/21-scale-maintenance-embedder-identity/21-CONTEXT.md` (D-02/D-03/D-06/D-07/D-08/D-15..D-19), `.planning/phases/19-search-correctness/bench/d12-verdict.json` (artifact style), `.planning/phases/18-quality-instrument-personal-bench-rapidfuzz-dym/18-VALIDATION.md` (manual-verification style).

### Tertiary (LOW confidence - not verified this session)

- `[ASSUMED]` The Harrier weight load under ST 5.4.1 / transformers 4.57.6 and 5.5.4 (structural verification only).
- `[ASSUMED]` The macOS MPS/joblib deadlock risk (research prompt; not reproduced; encode succeeded on MPS).
- `[ASSUMED]` The library default dtype for Harrier (likely float32 unless ST/transformers default to the config dtype).
- `[ASSUMED]` That `identity.revision` for Harrier will be non-null (mechanism verified on another ST model, not Harrier).

## Metadata

**Confidence breakdown:**
- Standard stack and model facts: HIGH - config, prompts, modules, pooling, dimension, license, sha, and weight size read from authoritative sources; architecture and prompt mechanics executed locally on the installed stack (weights not loaded).
- Architecture and instrument integration: HIGH - every claim about `sif eval`, `--compare`, saved runs, identity, prompt roles, cache buckets, and widening is read from source with line-level citations.
- Verdict math: HIGH for what exists and what is missing; MEDIUM for the D-08 interpretation (the 1/N floor) because the locked text does not name it.
- Pitfalls: HIGH for the code/behavior pitfalls; MEDIUM for MPS/deadlock and dtype assumptions.
- Corpus adequacy: HIGH for the local measurement; LOW for the user's intended corpus (unknown).

**Research date:** 2026-11-16
**Valid until:** ~2026-12-16 for the instrument/code (stable); ~30 days for the HF revision sha (main can move; the runbook records the resolved revision). Re-verify the Harrier revision and the locked `uv.lock` transformers version if planning slips past 30 days.
