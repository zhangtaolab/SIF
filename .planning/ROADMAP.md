# Roadmap: DocSift (SIF)

## Milestones

- ✅ **v1.0 MVP — qmd 功能对等的本地混合搜索引擎** — Phases 1-10.1 (shipped 2026-11-07)
- ✅ **v1.1 Live Index and Search Quality** — Phases 11-16.1 (shipped 2026-11-12)
- 🚧 **v1.2 Search Precision and Agent Experience** — Phases 17-24 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-10.1) — SHIPPED 2026-11-07</summary>

- [x] Phase 1: Foundation Fix (6/6 plans) — completed 2026-04-14
- [x] Phase 2: CLI Core Completion (6/6 plans) — completed 2026-04-15
- [x] Phase 3: Embedding & Vector Search (8/8 plans) — completed 2026-04-16
- [x] Phase 4: Advanced Search Pipeline (8/8 plans) — completed 2026-04-17
- [x] Phase 5: Agent Context Experience (12/12 plans) — completed 2026-09-07
- [x] Phase 6: Documentation Audit & Refresh (10/10 plans) — completed 2026-04-18
- [x] Phase 7: CLI Claude Skill (2/2 plans) — completed 2026-04-20
- [x] Phase 8: Project rename DocSift → SIF (8/8 plans) — completed 2026-04-27
- [x] Phase 9: MCP Server Implementation (6/6 plans) — completed 2026-05-12
- [x] Phase 10: Raise pytest coverage to 90% (7/7 plans) — completed 2026-11-06
- [x] Phase 10.1: Tech debt — path normalization + CR-01/CR-02/WR-01 (4/4 plans) — completed 2026-11-06

Full detail: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>✅ v1.1 Live Index and Search Quality (Phases 11-16.1) — SHIPPED 2026-11-12</summary>

**Goal:** 让索引从手动 `index update` 变为自动常新（Live Index），并让搜索质量可配置、可量化、持续可调（Search Quality）。

- [x] Phase 11: Live-Index Foundation (Concurrent DB + Incremental Core) (3/3 plans) — completed 2026-11-07
- [x] Phase 12: `sif watch` Foreground MVP (3/3 plans) — completed 2026-11-07
- [x] Phase 13: Watch Everywhere (MCP-Embedded Refresh + Background Daemon) (4/4 plans) — completed 2026-11-08
- [x] Phase 14: Freshness Floor (Pre-Command Refresh + Staleness Marking) (3/3 plans) — completed 2026-11-08
- [x] Phase 15: Search Quality Configuration (Hybrid Weights + Query Suggestions) (3/3 plans) — completed 2026-11-08
- [x] Phase 16: Bench Expansion + Reranker Tuning (6/6 plans) — completed 2026-11-09
- [x] Phase 16.1: Address tech debt: CLI error conventions + cache TTL + watch-host enqueue API (INSERTED) (5/5 plans) — completed 2026-11-12

Full detail: `.planning/milestones/v1.1-ROADMAP.md`

</details>

**🚧 v1.2 Search Precision and Agent Experience — Phases 17-24 (in progress)**

**Milestone Goal:** 让搜索精准可控（元数据过滤 + 正确性修复）、让 MCP 达到 2026 生态就绪（SDK v2 + agent 包装）、让质量提升有 held-out 证据（个人语料评测 + Harrier 评估），并补齐分发与 CI 缺口。

**Granularity:** Standard · **Phases:** 8 · **Coverage:** 39/39 v1.2 requirements mapped

**Phase numbering:** continues from v1.1 (last phase 16.1) — v1.2 starts at **17**, no reset. Integer phases are planned milestone work; decimal phases (e.g. 19.1) are reserved for urgent insertions via `/gsd-phase --insert`.

**Ordering (locked by research SUMMARY.md):** regression net (17) → measurement instrument (18) → correctness (19) → filtering (20) → scale + embedder identity (21) → MCP shell swap (22) → gated Harrier evaluation (23) → tuning/models/docs (24). Hard constraints: CI/hygiene/PyPI (17) before any schema migration (19/21) and the shell swap (22); instrument (18) before ranking mutations (19) and Harrier (23); CORR-01 frontmatter freshness (19) before filters (20) — filters would serve stale tags otherwise; embedder identity (21) before Harrier (23) — the same-1024-dimension trap; MCP swap (22) after search-layer semantics stabilize (19/20) — no double tool-schema rework; README mcp-name marker + PyPI publish (17) before MCP Registry listing (22). Standard granularity would compress toward 4-6 phases, but every boundary here is a locked dependency or a distinct verifiable capability — there are no thin phases to fold.

**Locked scope (2026-11-13 — do not re-open):** metadata namespace = `qmd.metadata` compatible (migration parity); model arms MINIMAL (user decision "d") — Phase 23 tests ONLY Harrier native vs Qwen3-Embedding-0.6B baseline (GGUF Harrier arm = conditional follow-up MODEL-F1, not a v1.2 phase; bge-reranker-v2-m3 evaluation OUT); full Windows deferred to v2 (Phase 17 ships a degradation SMOKE only, via hc remote yoga — Python not preinstalled, `uv python install` first); exactly TWO new runtime deps total — `mcp>=2.3.0,<3` (Phase 22) and `rapidfuzz>=3.14.5,<4` (Phase 18); sentence-transformers stays locked 5.4.1; PDF/HTML/EPUB, chat-with-notes, ANN, semantic/late chunking, spellfix1 all OUT (see REQUIREMENTS.md Out of Scope).

- [ ] **Phase 17: Engineering Foundation (CI Matrix + Hygiene + PyPI)** - Green py3.10–3.13 × ubuntu/macos test matrix, Windows degradation smoke (hc yoga), dead-layer/repo cleanup, trusted-publishing release of `docsif` v1.1.x
- [ ] **Phase 18: Quality Instrument (Personal Bench + rapidfuzz DYM)** - `sif eval --personal` known-item measurement with bias controls; measured rapidfuzz did-you-mean swap
- [ ] **Phase 19: Search Correctness** - Frontmatter-only edit freshness, per-doc dedup pre-fusion, deterministic pagination, title-FTS ranking, single context/staleness attach
- [ ] **Phase 20: Metadata Filtering + Discovery** - qmd-parity recursive filter AST applied pre-RRF, built-in path/mtime fields, typed frontmatter storage, `metadata` discovery tool
- [ ] **Phase 21: Scale, Maintenance + Embedder Identity** - Bounded staleness/context reads, `index vacuum` + backup, streaming embed, `index_meta` embedder identity + role-aware embed
- [ ] **Phase 22: MCP SDK v2 Modernization + Agent Packaging** - Official SDK shell swap (dual-era), accurate annotations + structuredContent, query pipeline parity, daemon, Claude Code plugin + MCP Registry
- [ ] **Phase 23: Harrier Gated Evaluation** - EN+ZH held-out A/B of Harrier native vs Qwen3-Embedding-0.6B; default switch ONLY on a proven win
- [ ] **Phase 24: Tuning + Models UX + Install Docs** - Held-out-gated chunk sweep + title-breadcrumb experiment, `models pull/status`, uv-first install docs

## Phase Details

### Phase 17: Engineering Foundation (CI Matrix + Hygiene + PyPI)
**Goal**: Contributors get a green regression net on every push and a proven release pipeline — every later schema migration and the MCP shell swap land against a verified matrix, and `docsif` is on PyPI before the MCP Registry needs it.
**Depends on**: Nothing (first v1.2 phase; v1.1 shipped)
**Requirements**: ENG-01, ENG-02, ENG-03, ENG-04
**Success Criteria** (what must be TRUE):
  1. Every push/PR runs the full test suite green on py3.10–3.13 × ubuntu/macos — fail_under=90 per cell, CPU torch on Linux (no multi-GB CUDA resolve), both the py3.10 and py3.11+ resolution fleets tolerated without asserting exact transitive versions
  2. A Windows smoke run on hc remote yoga (uv python install first) proves fork/systemd/flock degrade honestly with clear messages — degradation asserted, NOT full Windows support
  3. `docsif` v1.1.x is installable from PyPI via trusted publishing — TestPyPI dry run passed, version single-sourced, PEP 740 attestations present, and the README `<!-- mcp-name: io.github.zhangtaolab/sif -->` marker landed BEFORE publish
  4. The repo is hygienic — dead `MigrationManager` + `models/search.py` + `search/strategy.py` quarantined/deleted (no tempting dead `filters` dict for Phase 20), tracked junk removed, Makefile/extras/pre-commit cleaned (black dropped; fastapi/uvicorn kept as core deps); the 3.13 classifier appears only once the matrix is green
**Plans:** 1/9 plans executed
**Wave 1**
- [x] 17-01-PLAN.md — Repo hygiene core: dead layers, orphan export, pre-commit Makefile target
- [ ] 17-02-PLAN.md — CPU-torch lock + extras floors + black removal

**Wave 2** *(blocked on Wave 1 completion)*
- [ ] 17-03-PLAN.md — 8-cell CI matrix + lint/type job, proven green
- [ ] 17-04-PLAN.md — Windows degradation guards + hc yoga smoke
- [ ] 17-08-PLAN.md — Documentation sweep: dead-layer prose + phantom pre-commit guidance

**Wave 3** *(blocked on Wave 2 completion)*
- [ ] 17-05-PLAN.md — Release artifacts: 1.1.2, README marker, publish workflow, 3.13 classifier
- [ ] 17-09-PLAN.md — Tracked junk removal + final ENG-04 hygiene gate

**Wave 4** *(blocked on Wave 3 completion)*
- [ ] 17-06-PLAN.md — Release prerequisites (environments, publishers) + pre-tag gate

**Wave 5** *(blocked on Wave 4 completion)*
- [ ] 17-07-PLAN.md — Tag v1.1.2, publish, attestation + install proofs

### Phase 18: Quality Instrument (Personal Bench + rapidfuzz DYM)
**Goal**: Users can measure search quality on their own corpus with trustworthy bias controls BEFORE any ranking behavior changes — the instrument that arbitrates the correctness fixes (19), the Harrier gate (23), and the tuning sweeps (24).
**Depends on**: Phase 17 (green CI matrix under the new instrument)
**Requirements**: EVAL-01, EVAL-02, QUAL-01
**Success Criteria** (what must be TRUE):
  1. User can run `sif eval --personal` on their own indexed corpus with no manual labeling — known-item synthesis through the legacy fixture schema + `SearchEvaluator` reuse + query_log replay produce a quality report, with the CLI-only replay bias documented
  2. User can trust the personal bench's numbers — paraphrase overlap budget enforced, per-leg × per-language × per-category reports, hash-split tuning/held-out separation, paired deltas with a noise gate (one query ≈ 0.014 nDCG at personal N vs the 0.01 tie rule)
  3. User gets faster, higher-recall did-you-mean suggestions — rapidfuzz measured swap drops first-letter bucketing, stays within the ≤10 ms budget, cutoff deliberately re-measured on the 0–100 Indel scale, tie-break/probe contracts preserved
**Plans**: TBD

### Phase 19: Search Correctness
**Goal**: Search results are fresh, deduplicated, deterministically paginable, and title-aware — the trust floor that metadata filtering (20) builds on, with every ranking-contract change measured before/after on the Phase 18 instrument.
**Depends on**: Phase 17 (CI for the riskiest schema migrations), Phase 18 (bench before/after for ranking-contract changes)
**Requirements**: CORR-01, CORR-02, CORR-03, CORR-04, CORR-05
**Success Criteria** (what must be TRUE):
  1. User's frontmatter-only edits (tags/title) become searchable after the next index update — parser dispatch wired + metadata-aware checksum in ONE plan with ONE shared forced-reindex migration; the Markdown body path stays byte-identical and the YAML `---` empty-body bug is fixed
  2. User gets one result per document by default — dedup inside VectorSearcher pre-fusion (duplicate chunks no longer inflate RRF scores); `--per-chunk` escape hatch restores chunk-level results; the ranking-contract change is recorded with bench before/after and goldens updated with rationale
  3. User can paginate results deterministically — CLI `--offset` and MCP offset return the correct next page (hybrid owns ONE offset slice, searchers return from rank 0, BM25 min_score order fixed); offset=0 reproduces the recorded contract
  4. User gets title-aware ranking — title-FTS detect-and-rebuild migration + rewritten triggers + bench-measured bm25() column weights + mtime index; the `documents_fts_v` vocab shadow survives the rebuild on a populated DB
  5. User gets results without redundant attach work — the double-attach is eliminated: exactly ONE context/staleness attach at pipeline exit
**Plans**: TBD

### Phase 20: Metadata Filtering + Discovery
**Goal**: Users and agents can scope searches precisely with metadata filters applied before fusion — qmd-unreleased AST parity plus built-in path/mtime fields, and a discovery tool so agents never guess keys.
**Depends on**: Phase 19 (HARD: CORR-01 frontmatter freshness before filters — stale tags otherwise; pagination contract from CORR-03)
**Requirements**: FILT-01, FILT-02, FILT-03, FILT-04, FILT-05
**Success Criteria** (what must be TRUE):
  1. User can filter any CLI search with `--filter <json>` and any MCP query with the `filter` param — recursive and/or/not + comparison/in/contains/type/exists with qmd semantics verbatim (typed exact match, no coercion, missing keys don't match `ne`/`nin`, budgets enforced)
  2. User can filter by built-in `path` and `mtime` fields (mtime indexed) — strictly more expressive than qmd's frontmatter-only AST
  3. User's filters apply pre-RRF per leg — BM25 outer WHERE of the materialized CTE (never inside it), vector post-KNN JOIN with adaptive over-fetch, a selectivity bound, and an honest "too selective" message; parameterized SQL only (no injection surface, no post-fusion filtering)
  4. User's existing indexes filter correctly after upgrade — typed frontmatter storage + backfill runs, and `qmd.metadata`-namespaced keys (migration parity, opt-in) filter identically to native keys; numeric values compare as numbers, not strings
  5. Agent can discover available metadata via a `metadata` tool on CLI + MCP — doc counts, numeric min/median/max, exact remainders; ONE validator shared with the filter surface; invalid filter → ToolError for model self-correction, never a protocol error
**Plans**: TBD

### Phase 21: Scale, Maintenance + Embedder Identity
**Goal**: Large-corpus maintenance is safe and fast, and the index knows which embedder produced its vectors — the locked precondition for the Harrier evaluation (23) and the stable embed contract the MCP layer (22) consumes.
**Depends on**: Phase 17 (CI for `index_meta`/shadow-table migrations), Phase 19 (attach-owner/dedup interaction for bounded reads)
**Requirements**: SCALE-01, SCALE-02, SCALE-03, CORR-06, EMB-01, EMB-02
**Success Criteria** (what must be TRUE):
  1. User gets fast searches without per-query full scans — staleness/context reads are bounded via a transactional `embedded_documents` shadow reconciled in cleanup/vacuum; staleness stays a derived signal and contexts keep verbatim two-sided normalization
  2. User can maintain the index safely — `sif index vacuum` reclaims space (flock + quiesce + no open txn + checkpoint + 2× disk check, retryable busy errors, target paths restricted) and backup produces a verified copy (SQLite online backup API + integrity_check)
  3. User can embed large corpora without giant transactions — streaming embed batches run outside transactions with short per-batch commits, resumable, CR-02 failure reporting preserved, batch-boundary sanity against garbage vectors
  4. User is protected from silent bad model swaps — persisted `index_meta` embedder identity (model id + revision/hash + pooling + prompt scheme, reusing the cache's `_cache_model_id` format); the 3 dim-guard sites consolidated; legacy DBs get warn-once + backfill; mismatch → fail-fast embed / warn+mark search
  5. User gets correct query-vs-document embeddings — role-aware embed surface with `prompt_name`, prompt dimension in the cache key; the Qwen3 default path stays byte-identical until the Harrier gate passes
**Plans**: TBD

### Phase 22: MCP SDK v2 Modernization + Agent Packaging
**Goal**: SIF's MCP server runs on the official SDK v2 serving every client era, with accurate annotations, citation-grade structured output, full query-pipeline parity, and agent-native distribution (Claude Code plugin + MCP Registry).
**Depends on**: Phase 19, Phase 20, Phase 21 (search semantics + `metadata` tool schema + embedder identity/role-aware embed contracts stable — no double schema rework), Phase 17 (PyPI publish is the hard prerequisite for MCP-09 Registry listing)
**Requirements**: MCP-01, MCP-02, MCP-03, MCP-04, MCP-05, MCP-06, MCP-07, MCP-08, MCP-09
**Success Criteria** (what must be TRUE):
  1. User's existing MCP clients keep working after the SDK v2 shell swap — dual-era 2024-11-05 → 2026-07-28 + stateless handshakes proven tracer-first with golden wire transcripts and a real-client matrix; `SearchBackend`/watch_host/I/O models preserved, protocol shell deleted; py3.10 install/import smoke passes at phase start
  2. Agent gets accurate annotations and citation-grade structured output on every tool — read-only tools annotated (documented effects: parallel calls + one retry; NO auto-approval claims), write tools never readOnly; structuredContent/outputSchema carry docid, path, line range, hash, staleness, with text content kept alongside for legacy clients
  3. User's loopback MCP server is protected from DNS rebinding — Host/Origin validation via SDK `transport_security`, verified with spoofed headers BEFORE the hand-rolled middleware is deleted
  4. Agent gets full query pipeline parity with a clean server — expander/reranker opt-in/snippet wired (pipeline hoisted, overclaiming rerank description fixed, rerank stays opt-in and documented); lazy embedder with forced quiet before any model import and a stdout-purity regression on cold first query; lex/vec tools wired; `mcp daemon` runs as a real daemon via existing `utils/daemon.py`
  5. User can install SIF as a Claude Code plugin and discover it in the MCP Registry — plugin + marketplace.json + citation-discipline skill encoding search→get two-stage citation (`claude plugin validate` passes); Registry listing via mcp-publisher is scripted and re-runnable, after the Phase 17 PyPI prerequisite
**Plans**: TBD

### Phase 23: Harrier Gated Evaluation
**Goal**: The default embedder changes only on proven EN+ZH held-out evidence — Harrier-OSS-v1-0.6b native vs Qwen3-Embedding-0.6B baseline, measured on the Phase 18 instrument with identity-protected isolated arms. Model arms are MINIMAL (locked decision "d"): no GGUF arm (conditional follow-up MODEL-F1), no bge-reranker arm.
**Depends on**: Phase 18 (personal bench instrument), Phase 21 (HARD: embedder identity + role-aware embed — Harrier and Qwen3-0.6B are both 1024-dim, so a width-only guard silently accepts a bad swap)
**Requirements**: MODEL-01, MODEL-02
**Success Criteria** (what must be TRUE):
  1. User gets an evidence-based embedder comparison — EN+ZH held-out A/B of Harrier native vs Qwen3-Embedding-0.6B with per-arm full re-embed on isolated indexes, per-language × per-leg verdicts, paired deltas + intervals; Harrier queries use `prompt_name="web_search_query"`, never `default_prompt_name`
  2. User's default embedder changes ONLY on a proven win — EN+ZH held-out win beyond the 0.01 tie rule; a no-win outcome is recorded as a rejection with numbers; the Qwen3 path stays byte-identical until the gate passes
**Plans**: TBD

### Phase 24: Tuning + Models UX + Install Docs
**Goal**: Chunking defaults are evidence-gated, model management is reliable, and every platform has a correct install path — the milestone closes on measured defaults and generator-verified docs.
**Depends on**: Phase 18 (held-out gate instrument), Phase 19 (title-FTS baseline for the breadcrumb duplication check), Phase 21 (streaming embed for per-arm re-embed), Phase 23 (default embedder settled before sweeps)
**Requirements**: QUAL-02, QUAL-03, MODELS-01, MODELS-02, DOCS-01
**Success Criteria** (what must be TRUE):
  1. User can find the best chunking via a held-out-gated chunk size/overlap sweep — per-arm re-chunk + re-embed on isolated arms, embed cost reported; defaults change only via the held-out gate
  2. User can benefit from a title-breadcrumb experiment — per-leg ablation reported, title-signal duplication checked against Phase 19 title FTS; defaults change only via the held-out gate
  3. User can pull models reliably — `sif models pull` with DEFAULT_MODELS corrected from 7B gte_Qwen2 to the Qwen3-0.6B family, md5 cache-check bug fixed, deterministic ModelScope path, canonical cache dir
  4. User can inspect model status — `sif models status` shows identity/backend/dims with a backend probe, and stays silent in non-TTY contexts
  5. User can install SIF correctly on every platform — uv-first docs with the Linux CPU torch index recipe, llama-cpp backend indexes, degradation matrix, and client config snippets; every new command/Settings field across the milestone passes the `make docs-generate` CI diff gate
**Plans**: TBD

## Cross-Phase Contracts

v1.2 contracts — defined ONCE; downstream phases consume, never redefine:

- **Embedder identity + role-aware embed** — defined in Phase 21 (EMB-01/02: `index_meta` identity reusing the cache's `_cache_model_id` format; `prompt_name` embed surface with the prompt dimension in the cache key). Consumed by Phase 22 (lazy embedder / MCP query path) and Phase 23 (Harrier arms). The Qwen3 default path is byte-identical until the Phase 23 gate passes.
- **`metadata` tool schema** — defined in Phase 20 (FILT-05: doc counts, numeric min/median/max, exact remainders; one shared validator; ToolError on invalid input). Surfaced unchanged by Phase 22's SDK v2 tool layer.
- **docs-generate gate** — every phase adding CLI commands or Settings fields (18, 19, 20, 21, 22, 24) regenerates the generator-owned docs (`make docs-generate`) and passes the CI diff gate; `docs/cli-reference.md` and `docs/configuration.md` are never hand-edited.
- **Ranking-contract evidence** — Phase 19 dedup/pagination/title changes and Phase 24 tuning record bench before/after on the Phase 18 instrument; shipped defaults move only through held-out gates (0.01 tie rule), and rejections are recorded with numbers.

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 11. Live-Index Foundation | v1.1 | 3/3 | Complete    | 2026-11-07 |
| 12. `sif watch` Foreground MVP | v1.1 | 3/3 | Complete    | 2026-11-07 |
| 13. Watch Everywhere (MCP + Daemon) | v1.1 | 4/4 | Complete    | 2026-11-08 |
| 14. Freshness Floor (Pre-Command + Staleness) | v1.1 | 3/3 | Complete    | 2026-11-08 |
| 15. Search Quality Configuration | v1.1 | 3/3 | Complete    | 2026-11-08 |
| 16. Bench Expansion + Reranker Tuning | v1.1 | 6/6 | Complete    | 2026-11-09 |
| 16.1. Address tech debt (CLI errors + cache TTL + enqueue API) | v1.1 | 5/5 | Complete    | 2026-11-12 |
| 17. Engineering Foundation (CI + Hygiene + PyPI) | v1.2 | 1/9 | In Progress | - |
| 18. Quality Instrument (Personal Bench + rapidfuzz) | v1.2 | 0/TBD | Not started | - |
| 19. Search Correctness | v1.2 | 0/TBD | Not started | - |
| 20. Metadata Filtering + Discovery | v1.2 | 0/TBD | Not started | - |
| 21. Scale, Maintenance + Embedder Identity | v1.2 | 0/TBD | Not started | - |
| 22. MCP SDK v2 + Agent Packaging | v1.2 | 0/TBD | Not started | - |
| 23. Harrier Gated Evaluation | v1.2 | 0/TBD | Not started | - |
| 24. Tuning + Models UX + Install Docs | v1.2 | 0/TBD | Not started | - |

---
*Roadmap created 2026-11-07 for milestone v1.1; v1.2 (Phases 17-24) added 2026-11-13. v1.0 (Phases 1-10.1) and v1.1 (Phases 11-16.1) shipped. Phase numbering continues at 17 (no reset).*
