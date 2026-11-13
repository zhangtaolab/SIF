# Requirements: DocSift (SIF)

**Defined:** 2026-11-13
**Milestone:** v1.2 — Search Precision and Agent Experience
**Core Value:** 用户可以在自己的笔记和文档库中，用自然语言快速、准确地找到需要的信息——无论关键词是否匹配。

Scope decisions locked 2026-11-13: PDF/format expansion OUT; MCP official SDK v2 upgrade approved; Harrier-OSS-v1-0.6b evaluation included, gated on EN+ZH held-out validation; full Windows deferred to v2 (CI smoke only, via hc remote yoga). Metadata namespace = `qmd.metadata` compatible (migration parity). Model arms = minimal: Harrier native vs Qwen3-Embedding-0.6B baseline only; GGUF arm is a conditional follow-up; bge-reranker-v2-m3 evaluation OUT.

## v1.2 Requirements (This Milestone)

Each maps to exactly one roadmap phase. Checkboxes mark committed scope.

### Engineering Foundation & Distribution (ENG)

- [x] **ENG-01**: Contributor can run the full test suite on a green CI matrix (py3.10–3.13 × ubuntu/macos, full suite per cell, fail_under=90, CPU torch on Linux, tolerant of both py3.10/3.11+ resolution fleets) on every push/PR.
- [ ] **ENG-02**: Contributor can verify Windows graceful degradation via a CI smoke run on hc remote yoga (uv python install first; assert fork/systemd/flock degrade honestly — not full Windows support).
- [ ] **ENG-03**: Maintainer can publish `docsif` to PyPI via trusted publishing (README `<!-- mcp-name: io.github.zhangtaolab/sif -->` marker before publish; TestPyPI dry run; version single-sourced; PEP 740 attestations).
- [x] **ENG-04**: Contributor works in a hygienic repo (dead `MigrationManager` + `models/search.py` + `search/strategy.py` quarantined/deleted; tracked junk removed; Makefile/extras/pre-commit cleaned, black dropped, fastapi/uvicorn kept as core deps; 3.13 classifier added only when green).

### Quality Instrument (EVAL)

- [ ] **EVAL-01**: User can measure search quality on their own corpus via `sif eval --personal` (known-item synthesis through the legacy fixture schema + `SearchEvaluator` reuse + query_log replay with documented CLI-only bias).
- [ ] **EVAL-02**: User can trust the personal bench's bias controls (paraphrase overlap budget; per-leg × per-language × per-category reports; hash-split tuning/held-out; paired deltas + noise gate).

### Search Quality Tuning (QUAL)

- [ ] **QUAL-01**: User gets faster, higher-recall did-you-mean suggestions (rapidfuzz measured swap dropping first-letter bucketing; ≤10 ms budget; cutoff deliberately re-measured on the 0–100 Indel scale; tie-break/probe contracts preserved).
- [ ] **QUAL-02**: User can find the best chunking via a held-out-gated chunk size/overlap sweep (per-arm re-chunk + re-embed; isolated arms; embed cost reported; defaults change only via the held-out gate).
- [ ] **QUAL-03**: User can benefit from a title-breadcrumb experiment (per-leg ablation; title-signal duplication checked against title FTS; defaults change only via the held-out gate).

### Search Correctness (CORR)

- [ ] **CORR-01**: User's frontmatter-only edits become searchable (parser dispatch wired + metadata-aware checksum in ONE plan with ONE shared forced-reindex migration; md path byte-identical; YAML `---` empty-body bug fixed).
- [ ] **CORR-02**: User gets one result per document by default (per-doc dedup inside VectorSearcher pre-fusion; `--per-chunk` escape hatch; recorded ranking-contract change with bench before/after and goldens updated with rationale).
- [ ] **CORR-03**: User can paginate results deterministically (CLI `--offset` + MCP offset + hybrid single offset slice + BM25 min_score order; offset=0 reproduces the recorded contract; searchers return from rank 0).
- [ ] **CORR-04**: User gets title-aware ranking (title-FTS detect-and-rebuild migration + rewritten triggers + bm25() column weights bench-measured + mtime index; `documents_fts_v` vocab shadow survives rebuild).
- [ ] **CORR-05**: User gets results without redundant attach work (double-attach eliminated; ONE context/staleness attach at pipeline exit).
- [ ] **CORR-06**: User gets fast searches without per-query full scans (bounded staleness/context reads via a transactional `embedded_documents` shadow reconciled in cleanup/vacuum; staleness stays derived; contexts keep verbatim two-sided normalization).

### Metadata Filtering & Discovery (FILT)

- [ ] **FILT-01**: User can filter search with a recursive JSON AST (and/or/not + comparison/in/contains/type/exists; qmd semantics verbatim — typed exact match, no coercion, missing keys don't match `ne`/`nin`, budgets) via shared CLI `--filter <json>` and MCP `filter` param.
- [ ] **FILT-02**: User can filter by built-in `path`/`mtime` fields (columns already exist; mtime index added) — strictly more expressive than qmd's frontmatter-only AST.
- [ ] **FILT-03**: User's filters apply pre-RRF per leg (BM25 outer WHERE of the materialized CTE — never inside it; vector post-KNN JOIN + adaptive over-fetch with a selectivity bound and honest "too selective" message; parameterized SQL only).
- [ ] **FILT-04**: User's frontmatter is stored typed for pushdown/discovery (typed kv storage + backfill; `qmd.metadata` namespace opt-in for migration parity).
- [ ] **FILT-05**: Agent can discover available metadata via a `metadata` tool (CLI + MCP; doc counts, numeric min/median/max, exact remainders; one validator shared with FILT-01; invalid filter → ToolError for model self-correction, never a protocol error).

### Scale & Maintenance (SCALE)

- [ ] **SCALE-01**: User can reclaim space safely via `sif index vacuum` (flock + quiesce + no open txn + checkpoint + 2× disk check; retryable busy errors; target paths restricted).
- [ ] **SCALE-02**: User can back up the index safely (SQLite online backup API + integrity_check).
- [ ] **SCALE-03**: User can embed large corpora without giant transactions (streaming embed batches; embed outside txn; short per-batch commits; resumable; CR-02 failure reporting preserved; batch-boundary sanity against garbage vectors).

### Embedder Identity (EMB)

- [ ] **EMB-01**: User is protected from silent bad model swaps (persisted `index_meta` embedder identity — model id + revision/hash + pooling + prompt scheme, reusing the cache's `_cache_model_id` format; 3 dim-guard sites consolidated; legacy-DB warn-once + backfill; mismatch → fail-fast embed / warn+mark search).
- [ ] **EMB-02**: User gets correct query-vs-document embeddings (role-aware embed surface with `prompt_name`; prompt dimension in the cache key; Qwen3 default path byte-identical until the Harrier gate passes).

### MCP SDK v2 & Agent Packaging (MCP)

- [ ] **MCP-01**: User's existing MCP clients keep working after the official SDK v2 migration (dual-era 2024-11-05 → 2026-07-28 + stateless; tracer-first with golden wire transcripts + real-client matrix; py3.10 install/import smoke at phase start; `SearchBackend`/watch_host/I/O models preserved, protocol shell deleted).
- [ ] **MCP-02**: Agent gets accurate tool annotations on all tools (read-only tools annotated for parallel calls + one retry; write tools never readOnly; no auto-approval claims — annotations are metadata, not enforcement).
- [ ] **MCP-03**: Agent gets citation-grade structured output (structuredContent/outputSchema automatic from return annotations with docid, path, line range, hash, staleness; text content kept alongside for legacy clients).
- [ ] **MCP-04**: User's loopback MCP server is protected from DNS rebinding (Host/Origin validation via SDK `transport_security`, verified with spoofed headers before deleting the hand-rolled middleware).
- [ ] **MCP-05**: Agent gets full query pipeline parity (expander/reranker opt-in/snippet wired; pipeline hoisted; overclaiming rerank description fixed; rerank stays opt-in and documented).
- [ ] **MCP-06**: User gets a clean-stdout MCP server (lazy embedder; forced quiet before any model import; stdout-purity regression on cold first query; lex/vec wiring).
- [ ] **MCP-07**: User can run MCP as a daemon (`mcp daemon` un-stubbed via existing `utils/daemon.py`).
- [ ] **MCP-08**: User can install SIF as a Claude Code plugin (plugin + marketplace.json + citation-discipline skill encoding search→get two-stage citation; `claude plugin validate` passes).
- [ ] **MCP-09**: User can discover SIF in the MCP Registry (listing via mcp-publisher, scripted and re-runnable; PyPI publish prerequisite satisfied first).

### Harrier Gated Evaluation (MODEL)

- [ ] **MODEL-01**: User gets an evidence-based embedder comparison (EN+ZH held-out A/B of Harrier-OSS-v1-0.6b native vs Qwen3-Embedding-0.6B baseline; per-arm full re-embed; isolated indexes; per-language × per-leg verdict; paired deltas + intervals; query `prompt_name="web_search_query"`, never `default_prompt_name`).
- [ ] **MODEL-02**: User's default embedder changes only on a proven win (default switch ONLY on an EN+ZH held-out win beyond the 0.01 tie rule; recorded rejection with numbers if no win; Qwen3 path byte-identical until the gate passes).

### Models UX (MODELS)

- [ ] **MODELS-01**: User can pull models reliably (`sif models pull`; DEFAULT_MODELS corrected from 7B gte_Qwen2 to the Qwen3-0.6B family; md5 cache-check bug fixed; deterministic ModelScope path; canonical cache dir).
- [ ] **MODELS-02**: User can inspect model status (`sif models status`; identity/backend/dims display; backend probe; non-TTY silence).

### Install Documentation (DOCS)

- [ ] **DOCS-01**: User can install SIF correctly on every platform (uv-first docs; Linux CPU torch index recipe; llama-cpp backend indexes; degradation matrix; client config snippets; every new command/Settings field passes `make docs-generate` CI diff gate).

## Future Requirements (Deferred)

Tracked but not in the v1.2 roadmap. Moving any to committed scope requires a roadmap update.

### Conditional Follow-up

- **MODEL-F1**: GGUF Harrier arm (majentik Q8_0 via llama-cpp, explicit `LLAMA_POOLING_TYPE_LAST`, manual instruction, ST-parity probe, file-hash provenance) — only if MODEL-01/02 gate passes AND quantized deployment is wanted.

### v2+ Carried Forward

- **WIN-F1**: Full Windows support (daemon/service/flock parity) — v1.2 ships smoke only.
- **FUTR-01**: spellfix1 DYM acceleration — superseded by rapidfuzz; revisit only if measured gaps remain.
- **FUTR-02**: LLM-assisted weight tuning.
- **FUTR-03**: symspellpy DYM fallback — only if UAT shows rapidfuzz gaps at >200k vocab.

### v1.x Candidates

- **EVAL-F1**: LLM-judge relative grading layer (re-verify Dietz 2025 judge-circularity numbers before relying on them).
- **FILT-F1**: Saved filters.
- **QUAL-F1**: Sweep automation.

## Out of Scope

Explicitly excluded to prevent scope creep.

| Feature | Reason |
|---------|--------|
| PDF/HTML/EPUB format expansion | User decision 2026-11-13 — OUT; Markdown-first focus retained |
| Chat-with-notes / ask | OUT — not core to the search value proposition |
| bge-reranker-v2-m3 evaluation arm | Decision d (2026-11-13): orthogonal to the embedder decision; v1.1 Phase 16 already gated the reranker; documented risk of hurting a strong first stage |
| Full Windows support | Deferred to v2; v1.2 ships degradation smoke only |
| spellfix1 | SKIP — rapidfuzz chosen as the measured DYM replacement |
| Semantic / late chunking | SKIP — no v1.2 need; fixed/markdown chunking retained |
| ANN index | SKIP — sqlite-vec quantization + rescore is the escape hatch at scale |
| Post-fusion filtering | Rejected — pre-RRF per-leg pushdown is the correct seam |
| SQL passthrough filters | Rejected — injection risk; parameterized AST compiler only |
| Nested frontmatter objects | Rejected — qmd parity is flat typed kv |
| OAuth/elicitation/MRTR/tasks/sampling/roots/logging on loopback server | Rejected — out of scope for a loopback personal server |
| Faceted UI | Rejected — CLI/MCP-first, no UI layer |
| Auto-approval from tool annotations | Never promised — open request claude-code#87452; documented effects are parallel read-only calls + one retry only |

## Traceability

Populated during roadmap creation. Each requirement maps to exactly one phase.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ENG-01 | Phase 17 | Complete |
| ENG-02 | Phase 17 | Pending |
| ENG-03 | Phase 17 | Pending |
| ENG-04 | Phase 17 | Complete |
| EVAL-01 | Phase 18 | Pending |
| EVAL-02 | Phase 18 | Pending |
| QUAL-01 | Phase 18 | Pending |
| QUAL-02 | Phase 24 | Pending |
| QUAL-03 | Phase 24 | Pending |
| CORR-01 | Phase 19 | Pending |
| CORR-02 | Phase 19 | Pending |
| CORR-03 | Phase 19 | Pending |
| CORR-04 | Phase 19 | Pending |
| CORR-05 | Phase 19 | Pending |
| CORR-06 | Phase 21 | Pending |
| FILT-01 | Phase 20 | Pending |
| FILT-02 | Phase 20 | Pending |
| FILT-03 | Phase 20 | Pending |
| FILT-04 | Phase 20 | Pending |
| FILT-05 | Phase 20 | Pending |
| SCALE-01 | Phase 21 | Pending |
| SCALE-02 | Phase 21 | Pending |
| SCALE-03 | Phase 21 | Pending |
| EMB-01 | Phase 21 | Pending |
| EMB-02 | Phase 21 | Pending |
| MCP-01 | Phase 22 | Pending |
| MCP-02 | Phase 22 | Pending |
| MCP-03 | Phase 22 | Pending |
| MCP-04 | Phase 22 | Pending |
| MCP-05 | Phase 22 | Pending |
| MCP-06 | Phase 22 | Pending |
| MCP-07 | Phase 22 | Pending |
| MCP-08 | Phase 22 | Pending |
| MCP-09 | Phase 22 | Pending |
| MODEL-01 | Phase 23 | Pending |
| MODEL-02 | Phase 23 | Pending |
| MODELS-01 | Phase 24 | Pending |
| MODELS-02 | Phase 24 | Pending |
| DOCS-01 | Phase 24 | Pending |

**Coverage:**
- v1.2 requirements: 39 total
- Mapped to phases: 39
- Unmapped: 0 ✓ (100% coverage — every requirement maps to exactly one phase)

---
*Requirements defined: 2026-11-13*
*Last updated: 2026-11-13 after v1.2 roadmap creation (traceability: 39/39 mapped to Phases 17-24; namespace=qmd.metadata, model arms=d)*
