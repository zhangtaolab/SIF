# Project Research Summary

**Project:** SIF (DocSift, PyPI `docsif`) — milestone v1.2 "Search Precision and Agent Experience"
**Domain:** Local-first hybrid search engine for personal knowledge bases (Python 3.10+, SQLite FTS5 + sqlite-vec, Click CLI + MCP server) — brownfield milestone on a mature v1.1 codebase
**Researched:** 2026-11-13
**Confidence:** HIGH overall (stack/architecture/pitfalls codebase-verified at HEAD `1aff2c9`; feature/ecosystem claims MEDIUM, cross-verified against primary sources)

## Executive Summary

v1.2 is a precision-and-readiness milestone on an already-shipped engine (v1.1: live index, WAL+flock, configurable RRF weights, DYM, bench harness with held-out tie rule, 1591 tests @ 95%). The research verdict is unusually clean: **exactly two new runtime dependencies** (`mcp>=2.3.0,<3` and `rapidfuzz>=3.14.5,<4`); everything else — filter AST, discovery, pagination, correctness fixes, vacuum/backup, streaming embed, the personal eval instrument, Harrier evaluation, CI, PyPI publishing, Registry listing, Claude Code plugin — is in-house work on existing machinery. Experts build this class of tool the way qmd (the parity target) and hosted engines (ES/Meilisearch/Weaviate) do: recursive filter AST applied **pre-RRF per leg**, typed metadata storage for pushdown and discovery, per-document dedup before fusion, deterministic pagination, and agent-native packaging (annotations + structuredContent + skill + registry). SIF's differentiators are the retained live index (qmd still has no watching), built-in path/mtime filter fields beyond qmd's frontmatter-only AST, and a label-free personal-corpus eval command no peer ships.

The recommended build order is dependency-driven and evidence-first: **CI/regression net → measurement instrument → search correctness → metadata filtering → scale/maintenance + embedder identity → MCP SDK v2 shell swap → gated Harrier evaluation → tuning/distribution polish**. Three hard internal dependencies force this order: (1) frontmatter-only edits are invisible to the index today (body-only checksum + mtime-only skip convergence), so tag filters would serve stale data unless the parser/checksum fix lands first; (2) dedup must move inside VectorSearcher pre-fusion (duplicate chunks currently inflate RRF scores, not just consume slots), and pagination is broken at three points — these are recorded ranking-contract changes that need the bench instrument before and the CI net under them; (3) Harrier and Qwen3-0.6B are both 1024-dim, so the width-only guard silently accepts a bad model swap — a persisted embedder identity marker (model id + prompt scheme, reusing the embedding cache's `_cache_model_id` format) is a locked precondition of any Harrier A/B. The MCP migration is a bounded shell replacement (~623 LOC deleted, `SearchBackend`/watch_host/I/O models preserved), sequenced after search-layer semantics stabilize so tool schemas aren't reworked twice.

Key risks and mitigations: evaluation invalidity (synthetic queries reuse source wording → BM25 inflation; porter makes Chinese sentences single tokens → ZH gains are vector-leg gains by construction; one query ≈ 0.014 nDCG at personal N vs the 0.01 tie rule) — mitigated by paraphrase budgets, per-language × per-leg reporting, paired deltas, and the locked EN+ZH held-out win-only gate. Big-bang SDK migration breaking well-tested transports — mitigated tracer-first (one tool, golden wire transcripts, real-client matrix). Annotation dishonesty (real auto-approval bypass incidents; and Claude Code annotations do **not** auto-approve — documented effects are parallel read-only calls + one retry only) — annotate actual behavior, never claim prompt-free execution, restrict vacuum target paths. Distribution traps (Linux pip resolves multi-GB CUDA torch; torch 2.15 dropped py3.10; llama-cpp wheel cache ignores backend) — CPU-index install docs, CI matrix tolerant of the 3.10/3.11+ resolution split, backend probe in `sif models status`.

## Key Findings

### Recommended Stack (details: STACK.md)

Two additions, everything else reuse. **Do not upgrade sentence-transformers** — locked 5.4.1 already has `prompt_name` (verified in installed source); 6.x is a breaking major with no v1.2 need.

**Core technologies:**
- `mcp` 2.3.0 (pin `>=2.3.0,<3`) — official SDK v2 `MCPServer`; adoption, not upgrade (no `mcp` dep exists today; server is hand-rolled, protocol hardcoded 2024-11-05). Serves **all** handshake eras 2024-11-05 → 2025-11-25 plus stateless 2026-07-28 with zero config; `OLDEST_SUPPORTED_VERSION="2024-11-05"` verified at source level, so SIF's current clients survive. structuredContent/outputSchema are automatic from return annotations; `transport_security` gives loopback Host/Origin DNS-rebinding protection.
- `rapidfuzz` (pin `>=3.14.5,<4`) — measured difflib replacement in `suggest.py`; drop first-letter bucketing (the locked recall fix). py3.10 auto-resolves 3.14.5, py3.11+ gets 3.14.6; wheels cover every CI target incl. win_arm64. Keep the ≤10 ms budget; migrate the 0–1 cutoff to the 0–100 scale deliberately (~75).
- Keep locked: sentence-transformers 5.4.1 (raise `embed` extra floor to `>=5.4.1`), torch 2.11.0, llama-cpp-python 0.3.35 (raise `all` floor), huggingface-hub 1.10.2, FastAPI 0.136.0 + uvicorn 0.44.0 (already **core** deps — SDK's ASGI app mounts unchanged), pydantic 2.13.1 (satisfies mcp's ≥2.12 floor).
- Models (no deps): `microsoft/harrier-oss-v1-0.6b` (MIT, 1024-dim, last-token pooling, query-side `prompt_name="web_search_query"` mandatory, never `default_prompt_name`); `BAAI/bge-reranker-v2-m3` via existing `CrossEncoderReranker` (model-name swap only); GGUF Harrier (`majentik` Q8_0) stays a secondary arm — community quant, ~47 downloads/mo, manual prompt + explicit `LLAMA_POOLING_TYPE_LAST`, parity-check vs ST route.
- Tooling: setup-uv v10.3.3 (SHA-pin; `python-version` does NOT install Python — yoga needs `uv python install`), `pypa/gh-action-pypi-publish@release/v1` (v1.14.3, trusted publishing + PEP 740 attestations, Linux-only, separate build job), `mcp-publisher` CLI for Registry, `claude plugin validate`.

**Python 3.10 resolution splits are real (CI must tolerate both fleets):** py3.10 → torch 2.14.1 / rapidfuzz 3.14.5 / httpx2 2.14.0; py3.11+ → torch 2.15.0 / rapidfuzz 3.14.6 / httpx2 2.16.0. Automatic via requires-python; never assert exact transitive versions in tests. Linux installs must use the torch CPU index (verified: `--index https://download.pytorch.org/whl/cpu` overrides PyPI; CUDA default is multi-GB). llama-cpp 0.3.36 prebuilt wheels are now `py3-none` (no cp312 ceiling — stale lead corrected); PyPI remains sdist-only; backend switches need `--force-reinstall --no-cache-dir`.

### Expected Features (details: FEATURES.md)

Parity target verified: qmd v2.8.3 already serves MCP 2026-07-28; its **[Unreleased]** flagship is the namespaced frontmatter filter AST (17 ops + `caseInsensitive`, pre-RRF, shared CLI/SDK/MCP/HTTP) + `metadata` discovery tool. SIF's filtering track catches up to qmd's unreleased state and exceeds it with built-in path/mtime fields; the MCP track catches up to its released state. Agent-native packaging (plugin + skill + registry) is table stakes — all four surveyed peers ship it.

**Must have (table stakes):**
- Recursive filter AST (and/or/not + comparison/in/contains/type/exists), qmd semantics verbatim (typed exact match, no coercion; missing keys don't match `ne`/`nin`; budgets), shared CLI `--filter <json>` + MCP `filter` param; invalid filter → ToolError (model self-correction), never protocol error
- Built-in `path`/`mtime` fields (columns already exist; add mtime index) + typed frontmatter extraction with namespaced opt-in + typed kv storage for pushdown/discovery
- Pre-RRF pushdown per leg (BM25 outer WHERE, vector post-KNN JOIN + adaptive over-fetch); `metadata` discovery tool (doc counts, numeric min/median/max, exact remainders) — without it agents guess keys
- Correctness: parser dispatch wiring, frontmatter-only edit freshness, per-doc dedup pre-fusion (+ `--per-chunk` escape hatch), pagination (offset is dead plumbing today — build CLI/MCP surface AND fix slicing), title FTS + column weights, per-query scan elimination, vacuum/backup, streaming embed with batch-boundary sanity (qmd #897 garbage-vector precedent)
- MCP SDK v2 dual-era + accurate annotations on all tools + structuredContent/outputSchema with citation-grade fields (docid, path, line range, hash, staleness) + Host validation + query pipeline parity (rerank stays opt-in, documented) + lazy embedder + lex/vec wiring + daemon stub closure
- Personal known-item bench instrument with bias controls; Harrier EN+ZH held-out gate; rapidfuzz measured swap; chunk sweep + breadcrumb experiment
- CI matrix + Windows smoke (degradation assertions, not support); PyPI publish (hard prerequisite for Registry); plugin + skill with search→get citation discipline; models pull/status; uv-first docs

**Should have (differentiators):**
- Path/mtime built-in filter fields (strictly more expressive than qmd at release)
- `sif eval --personal` as a shipped command (no peer has it) — credibility comes from the bias controls
- Citation-grade structuredContent + skill-encoded two-stage citation discipline (cite get output, not snippets)
- Live index + MCP-embedded freshness (v1.1, retained — qmd still has no watching; market it, don't rebuild)

**Defer / anti-features (locked 2026-11-13):** PDF/HTML/EPUB OUT; chat-with-notes/ask OUT; full Windows → v2 (smoke only); spellfix1 SKIP, symspellpy DEFER (>200k vocab), semantic/late chunking SKIP, ANN SKIP (sqlite-vec quantization+rescore is the escape hatch); post-fusion filtering, SQL passthrough filters, nested frontmatter objects, OAuth/elicitation/MRTR/tasks/sampling/roots/logging on the loopback server, faceted UI — all rejected with reasons in FEATURES.md. **Never promise auto-approval from annotations** (open feature request claude-code#87452; documented effects are parallelism + retry only). v1.x candidates: LLM-judge relative grading layer, saved filters, sweep automation.

### Architecture Approach (details: ARCHITECTURE.md)

Brownfield integration, fully mapped at file:line against HEAD `1aff2c9`. The filter AST lives in `core/filters.py` (domain) compiled by `search/filters.py` to one parameterized WHERE fragment injected at two verified seams (BM25 **outer** WHERE of the materialized CTE — never inside it; vector post-KNN JOIN), making pre-RRF application automatic. Corrected pipeline order: over-fetch → filter → per-doc dedup (inside VectorSearcher) → fuse over limit+offset → single offset slice → ONE context/staleness attach at pipeline exit. Embedder identity goes in a regular `index_meta` table (not vec0 markers — per-index fact, readable without sqlite-vec, reuses the cache's identity string). MCP migration deletes the protocol shell (server.py, wire types, transports) and preserves `SearchBackend`, watch_host (D-14 teardown), and the SIF I/O Pydantic models as the tool contract; new `mcp/app.py` composition root. All schema changes ride `SchemaManager`'s idempotent + detection-gated machinery (CR-01 pattern) — **never** the dead `MigrationManager`.

**Major components (new/modified):**
1. `core/filters.py` + `search/filters.py` — FilterAst + SQL compiler; `SearchOptions.filters` (delete/quarantine the dead `models/search.py` + `search/strategy.py` layer first so nobody wires filters into its tempting `filters` dict)
2. Search-layer fixes — `vector.py` (dedup pre-trim, adaptive fetch_k, filter JOIN), `hybrid.py` (slice, single attach), `bm25.py` (min_score order, title weights), `staleness.py`/`context_attach.py` (bounded reads; transactional `embedded_documents` shadow table recommended, reconcile in cleanup/vacuum)
3. Indexing — `parser.py`/`incremental.py` (wire `create_parser`, metadata-aware checksum, ONE shared forced-reindex migration for both convention changes)
4. `embedding/identity.py` + `index_meta` — consolidate the 3 dim-guard sites; role-aware embed surface (`prompt_name`) + prompt dimension in cache key
5. `mcp/app.py` (new) over preserved `backend.py`/`watch_host.py`; `database/maintenance.py` (vacuum/backup); `search/personal.py` + `cli/commands/eval.py` (reuses `SearchEvaluator` unchanged via legacy fixture schema — do NOT extend `CATEGORIES`)
6. Schema migrations: mtime index; title-FTS detect-and-rebuild (new gate — `IF NOT EXISTS` won't add a column and the existing misconfig gate won't fire; rewrite all triggers; verify `documents_fts_v` vocab shadow survives); `index_meta`; `embedded_documents` shadow. vec0 table UNCHANGED.

Every new CLI command/Settings field must run `make docs-generate` (CI diff gate on generator-owned docs).

### Critical Pitfalls (details: PITFALLS.md — 25 pitfalls, phase-mapped)

1. **Same-dimension embedder swap (P1) + query-instruction asymmetry (P2) + GGUF mean-pool fallback (P3)** — identity marker (model id + revision/hash + pooling + prompt scheme) before any Harrier arm; role-aware embed API with prompt identity in the cache key (query/document cache collision is real and measured); GGUF pooling sanity probe vs ST reference; Qwen3 default path byte-identical until the gate passes.
2. **Evaluation invalidity (P4/P5/P6)** — synthetic lexical bias (BM25 0.266→0.856 inflation documented), CJK single-token confound (empirically verified: `MATCH '配置'` = 0 hits), small-N noise (~0.014/query > 0.01 tie rule). Paraphrase budgets, per-language × per-leg reports, paired deltas + intervals, EN+ZH held-out win-only, record rejections with numbers.
3. **Frontmatter invisibility (P14) + parser checksum churn (P17)** — metadata filters serve stale tags by construction until change detection is metadata-aware; wire dispatch + checksum change in ONE plan with ONE forced reindex (md path stays byte-identical; YAML `---` empty-body bug fixed).
4. **Dedup/pagination contract changes (P12/P15) + vec0 KNN-before-JOIN under-return (P13)** — dedup pre-fusion is a recorded ranking-contract change (bench before/after, update goldens with rationale); single offset owner (hybrid slices, searchers return from rank 0); adaptive over-fetch with bounded escalation + honest "too selective" message; 2%-selectivity recall fixture.
5. **Big-bang MCP migration (P8/P9/P10/P11)** — tracer-first (status tool end-to-end, golden wire transcripts, real-client matrix); keep text content alongside structuredContent; keep pydantic validation in handlers (SDK sanitizes non-ToolError to −32603); `by_alias=True` dumps; force quiet before any model import (stdout purity regression on cold first query); annotate actual behavior — write tools never readOnly, vacuum path-restricted (VACUUM INTO was a real exfil vector); fix the query description that already overclaims reranking.

Also load-bearing: scan fixes must keep staleness **derived** and contexts two-sided normalization (P18 — the silent-lie and verbatim-path bug classes); vacuum needs flock + no open txn + checkpoint + 2× disk, backup via online API + integrity_check (P19); streaming embed changes CR-02 failure semantics — embed outside txn, short per-batch commits, resumable (P20); chunk sweep arms invalidate every vector — isolate arms, re-embed per arm, ablate breadcrumb per leg (P25); bge is not a free upgrade (hurt a strong first stage in localGPT; α=0.5 and max_length=512 assumptions don't transfer; rerank cache keys must include resolved model identity) (P7).

### Reconciliations (cross-file disagreements resolved this session)

1. **SDK era coverage:** STACK's source-level verification (`OLDEST_SUPPORTED_VERSION="2024-11-05"`, all handshake eras + 2026-07-28) supersedes PITFALLS P9's docs-only concern. 2024-era clients survive; the client-matrix test remains a plan-1 deliverable as proof, not as an open risk.
2. **Annotations do NOT auto-approve in Claude Code** (FEATURES read official docs; P11's "hosts auto-approve" framing applies to other hosts/incidents). Requirements must not depend on auto-approval; the documented benefits (parallel read-only calls, one retry) still justify annotating.
3. **localGPT A/B is harrier-0.6b vs Qwen3-Embedding-4B** (0.915 vs 0.875), not vs 0.6B at 0.805 (PITFALLS correction; PROJECT.md Key Decisions still cites 0.805 — treat magnitude evidence as vs-4B; direction holds; the EN-only limitation is why ZH held-out is the gate).
4. **llama-cpp 0.3.36 wheels are py3-none** (STACK correction of P22's cp312-ceiling claim, which applies to older builds). Backend-cache trap (`--force-reinstall --no-cache-dir`) still stands.
5. **py3.10 splits verified:** mcp 2.3.0 supports ≥3.10 (resolves ARCHITECTURE's PyPI-vs-README contradiction in favor of PyPI metadata; still run an install/import smoke on 3.10 at MCP phase start); torch ceiling 2.14.1 and httpx2 2.14.0 on 3.10 are real — CI tolerates both fleets.
6. **Only two new runtime deps**; sentence-transformers stays 5.4.1.

## Implications for Roadmap

Suggested structure: **8 phases** following ARCHITECTURE.md's dependency tiers (0–7). Ordering principle: regression net → measurement → correctness → features → shell swap → gated evaluation → polish.

### Phase 1: Engineering Foundation — CI, Hygiene, PyPI v1.1.x (tier 0)
**Rationale:** Every later phase (FTS rebuild, shell swap) needs a green matrix to land against; hygiene removes dead-layer traps before filter work; publishing v1.1.x de-risks the release pipeline and satisfies the Registry's hard prerequisite early.
**Delivers:** test CI matrix py3.10–3.13 × ubuntu/macos (full suite per cell, fail_under=90, CPU torch on Linux, both resolution fleets); Windows smoke via hc remote yoga (uv python install first; assert graceful degradation of fork/systemd/flock, not support); delete tracked junk; quarantine/delete dead `MigrationManager` + `models/search.py` + `search/strategy.py`; Makefile/extras/pre-commit cleanup (drop black; keep fastapi/uvicorn as core deps); 3.13 classifier (only when green); **README `<!-- mcp-name: io.github.zhangtaolab/sif -->` marker BEFORE publish**; version single-sourcing (WR-03) + TestPyPI dry run + trusted publishing (docsif v1.1.x).
**Avoids:** P21 (CUDA bloat), P22 (wheel strategy), P23 (Windows degradation), P24 (publish mechanics), Anti-Patterns 1/5 (dead layers).

### Phase 2: Quality Instrument — Personal Bench + rapidfuzz (tier 1)
**Rationale:** Measurement before mutation — dedup/title-FTS/chunk changes are ranking-behavior changes needing a baseline; the instrument is the substrate for the Harrier gate (locked: instrument FIRST).
**Delivers:** `sif eval --personal` (known-item synthesis via legacy fixture schema + `SearchEvaluator` reuse + query_log replay with documented CLI-only bias); bias controls as features (paraphrase overlap budget, per-leg × per-language × per-category reports, hash-split tuning/held-out, paired deltas + noise gate); rapidfuzz measured swap (drop buckets, re-measure cutoff, preserve tie-break/probe contracts, ≤10 ms budget).
**Avoids:** P4 (lexical bias), P5 (CJK confound), P6 (small-N default moves).

### Phase 3: Search Correctness (tier 2)
**Rationale:** The trust-floor fixes; parser/frontmatter freshness is a HARD precondition of Phase 4 filters; title FTS is the riskiest schema migration — do it early with CI + bench in place.
**Delivers:** parser dispatch wiring + metadata-aware checksum in ONE plan with ONE forced-reindex migration (md byte-identical; YAML `---` fix); per-doc dedup inside VectorSearcher pre-fusion + `--per-chunk` escape hatch (recorded contract change, bench before/after); pagination (CLI `--offset` + MCP offset + hybrid single slice + BM25 min_score order; offset=0 reproduces recorded contract); title-FTS detect-and-rebuild + triggers + bm25() column weights (bench-measured) + mtime index; double-attach elimination.
**Avoids:** P12, P14, P15, P16, P17; Anti-Patterns 2/4/7.

### Phase 4: Metadata Filtering + Discovery (tier 3)
**Rationale:** Depends on Phase 3 freshness + pagination; the precision headline (qmd-unreleased parity + path/mtime).
**Delivers:** FilterAst (qmd semantics + budgets) + SQL compiler (parameterized only) + pre-RRF pushdown both legs + adaptive over-fetch with selectivity bound; typed kv storage + backfill; CLI `--filter` + MCP `filter` (one validator, ToolError on invalid); `metadata` discovery tool CLI+MCP (counts/stats/remainders; schema agreed ONCE with Phase 6). **Requirements fork to decide before implementation:** read `qmd.metadata` namespace (recommended for migration parity) vs SIF-native.
**Avoids:** P13 (KNN-before-JOIN under-return), P14 (stale tags), Anti-Patterns 1/2/3; SQL injection via interpolation.

### Phase 5: Scale, Maintenance + Embedder Identity (tier 4)
**Rationale:** Identity BEFORE Harrier (same-dim trap is locked); scan elimination after correctness (attach-owner interacts with dedup); vacuum/backup/streaming are independent.
**Delivers:** `index_meta` embedder identity (reuse `_cache_model_id` format; consolidate 3 dim guards; legacy-DB warn-once + backfill; mismatch → fail-fast embed / warn+mark search); role-aware embed surface (`prompt_name`) + prompt dimension in cache key; staleness/contexts bounded reads (transactional `embedded_documents` shadow + reconcile in cleanup/vacuum; keep derived-signal + verbatim-context contracts); `sif index vacuum` (flock + quiesce + checkpoint, retryable busy errors) + backup (online API + integrity_check); streaming embed batches (embed outside txn, short commits, resumable, CR-02 reporting preserved, boundary sanity).
**Avoids:** P1/P2 preconditions, P18, P19, P20; Anti-Patterns 6/9.

### Phase 6: MCP SDK v2 Modernization + Agent Packaging (tier 5)
**Rationale:** After search-layer semantics stabilize so tool I/O schemas aren't reworked twice; SDK dual-era serving is free, migration cost is MEDIUM and bounded. Start with a py3.10 install/import smoke + tracer (can spike during Phases 3–4).
**Delivers:** shell replacement (`mcp/app.py`; delete server.py/wire types/transports; preserve backend/watch_host/I/O models); tracer-first with golden wire transcripts + real-client matrix (2024-11-05 → 2026-07-28); annotations (accurate, all read-only tools) + structuredContent/outputSchema with citation fields (keep text content for legacy); Host/Origin via `transport_security` (verify before deleting custom middleware); query pipeline parity (expander/reranker opt-in/snippet; hoist pipeline; fix overclaiming description) + lazy embedder (forced quiet, stdout-purity regression) + lex/vec wiring; `mcp daemon` un-stub via existing `utils/daemon.py`; Claude Code plugin + marketplace.json + citation-discipline skill (`claude plugin validate`); MCP Registry listing via mcp-publisher (script it — preview may reset).
**Avoids:** P8, P9 (now proof, not risk), P10, P11; Anti-Pattern 8.

### Phase 7: Harrier Gated Evaluation (tier 6)
**Rationale:** Locked gate — default switch ONLY on EN+ZH held-out win beyond the 0.01 tie rule; depends on Phase 2 instrument + Phase 5 identity/prompt machinery.
**Delivers:** EN+ZH held-out A/B (per-arm full re-embed, isolated indexes, per-language × per-leg verdict, paired deltas + intervals); query `prompt_name="web_search_query"` (never `default_prompt_name`); optional GGUF arm (majentik Q8_0, explicit LAST pooling, manual instruction, ST-parity probe, file-hash provenance); bge-reranker-v2-m3 as a measured OPTION (α + max_length per model, latency columns, cache identity in key); recorded rejection if no win.
**Avoids:** P1, P2, P3, P6, P7; width-only guard trap.

### Phase 8: Tuning + Models UX + Install Docs (tier 7)
**Rationale:** Chunk sweep needs the instrument + streaming embed + stable chunk identity; models UX is independent (can float earlier if capacity); docs after models UX settles.
**Delivers:** chunk size/overlap sweep (per-arm re-chunk+re-embed, isolated arms, embed cost reported) + title-breadcrumb experiment (per-leg ablation; check title-signal duplication vs Phase 3 title FTS); defaults only via held-out gate; `sif models pull/status` (fix DEFAULT_MODELS 7B gte_Qwen2 → Qwen3-0.6B family, md5 cache-check bug, deterministic ModelScope path, canonical cache dir; identity/backend/dims display; non-TTY silence); uv-first install docs (Linux CPU index recipe, llama-cpp backend indexes, degradation matrix, client config snippets).
**Avoids:** P25, P21/P22 (docs half), UX pitfalls (progress in transcripts, silent re-downloads).

### Phase Ordering Rationale

- CI (1) before migrations (3/5) and shell swap (6) — riskiest changes land against a green matrix.
- Instrument (2) before correctness (3) and Harrier (7) — v1.1's bench-before-tuning lesson; dedup/title changes need evidence.
- Parser/frontmatter fix (3) before filters (4) — hard correctness dependency (Anti-Pattern 7); one shared reindex migration.
- Identity (5) before Harrier (7) — same-dimension trap makes it a precondition, not a follow-up (satisfies PITFALLS' "first plan of Harrier phase" by landing earlier).
- MCP swap (6) after search-layer stability (3/4) — avoids double schema rework; PyPI (1) before Registry (6) — hard external order; plugin/skill after tool surface settles.
- Cross-phase contracts to define ONCE: embedder identity + role-aware embed (5, consumed by 6/7); `metadata` tool schema (4, surfaced by 6); docs-generate gate applies to every phase adding commands/settings.

### Research Flags

Phases likely needing deeper research during planning (`/gsd-plan-phase --research-phase`):
- **Phase 6 (MCP):** HIGH — exact `transport_security` Host/Origin semantics vs custom middleware; lifespan composition with watch_host (D-14); structured-output wrapping edge cases; real-client matrix execution. Era coverage + py3.10 support are already source-verified (reconciliations 1/5) — remaining work is integration proof, not discovery.
- **Phase 3 (title FTS):** MEDIUM — `documents_fts_v` vocab shadow survival across drop/recreate; bm25() column-weight query plan; rebuild cost at corpus scale.
- **Phase 4 (filters):** MEDIUM — LIKE-prefix index usability under default collation (EXPLAIN QUERY PLAN); JSON1 availability on all CI platforms; selectivity estimation for adaptive over-fetch; qmd AST is UNRELEASED — re-verify against current CHANGELOG at plan time.
- **Phase 5 (staleness shadow):** MEDIUM — transactional coupling audit of ALL vector write paths; reconcile design; contexts normalization decision touches a PROJECT.md Key Decision (per-connection cache is the lower-risk default; write-side column needs phase discussion).
- **Phase 7 (Harrier):** MEDIUM — GGUF publisher pooling metadata (ggml-org card returned 401); localGPT eval/decisions/embedder.md if the 0.6B head-to-head matters; rapidfuzz-style cutoff re-measurement is execution, not research.

Phases with standard patterns (skip research-phase):
- **Phase 1:** CI workflow, trusted publishing, hygiene — all verified recipes in STACK.md.
- **Phase 2:** instrument reuses verified SearchEvaluator/QueryLogRepository/BenchHarness seams.
- **Phase 8:** Click commands, downloader fixes, docs — established patterns; measurement is execution.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Every version/migration surface verified against primary sources (PyPI JSON, tagged SDK source, model cards/configs, local uv resolution experiments); prior leads corrected |
| Features | MEDIUM | Load-bearing claims cross-verified (qmd CHANGELOG/README, all four spec changelogs, official Claude Code docs, peer-reviewed eval evidence); competitive landscape rests on primary reads with seam-tier caveats |
| Architecture | HIGH | All integration mapping read at HEAD `1aff2c9` file:line; every prior claim re-verified; external SDK facts upgraded to HIGH via STACK's source-level checks (reconciliations 1/5) |
| Pitfalls | HIGH (codebase) / MEDIUM (external) | All code claims cited file:line at HEAD; CJK confound empirically reproduced locally; ecosystem incidents cross-referenced ≥2 sources; one primary source unavailable (ggml-org GGUF 401) |

**Overall confidence:** HIGH for roadmap creation — the dependency order is derived from verified code facts; residual uncertainty is concentrated in flagged integration proofs, not in what to build.

### Gaps to Address

- **Namespace decision (requirements fork):** `qmd.metadata` vs SIF-native — decide in requirements before Phase 4; recommendation is qmd namespace for migration parity.
- **MCP py3.10 install smoke:** metadata verified ≥3.10 but README says 3.11+ — resolve by actual install/import on a 3.10 interpreter at Phase 6 start (fallback: environment-marker pin, or a Constraints change requiring user decision).
- **transport_security Host+Origin coverage:** test with spoofed headers before deleting the hand-rolled middleware.
- **fts5vocab shadow survival** across title-FTS rebuild — test on a populated DB (Phase 3).
- **JSON1 on ubuntu/Windows CI** — verified locally on macOS only (Phase 1 matrix proves it).
- **Contexts normalization:** write-side column vs per-connection cache — touches a locked Key Decision; phase discussion (Phase 5).
- **qmd filter AST is unreleased** — may change; pin to current CHANGELOG era, re-verify at Phase 4 plan time.
- **MCP Registry is preview** — schema/flow may break or reset; keep listing scripted and re-runnable.
- **GGUF pooling metadata** — ggml-org card inaccessible (401); majentik quant has no upstream guidance; verify parity before trusting the GGUF arm (Phase 7).
- **Dietz 2025 judge-circularity numbers** extracted via search, not full text — re-verify only if load-bearing for the v1.x judge layer.
- **PROJECT.md cites the unverified 0.805 A/B figure** — correct to the verified vs-4B comparison (0.915 vs 0.875) when requirements are written.

## Sources

Aggregated from the four research files (full source lists with per-claim confidence tags live there). All reads were direct primary sources; no proxies/mirrors.

### Primary (HIGH confidence)
- Local codebase at HEAD `1aff2c9` — all file:line integration claims (ARCHITECTURE.md verification ledger; PITFALLS.md grounding list); empirical CJK tokenizer test (SQLite 3.51.0)
- PyPI JSON API — mcp 2.3.0, rapidfuzz, torch, llama-cpp-python, sentence-transformers, httpx2, docsif release history (STACK.md)
- GitHub `modelcontextprotocol/python-sdk` tagged source — `mcp_types/version.py` era tuples + OLDEST_SUPPORTED_VERSION; official v2 whats-new/migration/structured-output docs (STACK.md, FEATURES.md)
- Hugging Face model cards + configs — harrier-oss-v1-0.6b, majentik GGUF Q8_0, bge-reranker-v2-m3, Qwen3-Embedding-0.6B (STACK.md, PITFALLS.md)
- Official docs — code.claude.com (mcp, plugins-reference, agent-sdk/custom-tools), modelcontextprotocol.io (4 spec changelogs, registry quickstart), sqlite.org (VACUUM), docs.pypi.org (trusted publishers), docs.astral.sh/uv, abetlen.github.io wheel indexes (all four files)
- GitHub Actions releases — gh-action-pypi-publish v1.14.3, setup-uv v10.3.3, registry v1.8.9 (STACK.md)

### Secondary (MEDIUM confidence)
- qmd CHANGELOG/README/issues (primary reads, seam-tiered; parity target + demand signals #952/#897/#685/#776/#764) (FEATURES.md, PITFALLS.md)
- Peer repos — basic-memory, GNO, memsearch packaging conventions (FEATURES.md)
- Evaluation literature — TU Delft thesis (τ 0.48–0.88 → 0.69–1.00), JMIR clinical bench (BM25 inflation), UMBRELA, CIKM 2008/TOIS 2012 (FEATURES.md, PITFALLS.md)
- localGPT design_rationale.md — identity-marker precedent, vs-4B A/B, bge regression, noise floor (PITFALLS.md; corrected comparison target)
- Annotation security incidents — GHSA-PQH8-P93P-2RX7, false-readOnly SQLite write-up (PITFALLS.md)

### Tertiary (LOW confidence — do not cite as fact)
- bge "~0.9 s vs Qwen3 ~5 s" PROPOR 2026 latency claim — UNVERIFIED; measure with the bench instrument
- "0.805 vs Qwen3-0.6B" A/B figure — unverified at that value; verified comparison is vs 4B
- Claude Code plan-mode silent read-only execution — community evidence only; official docs document parallel + retry
- ggml-org GGUF pooling guidance — source inaccessible (401)

---
*Research completed: 2026-11-13*
*Ready for roadmap: yes*
