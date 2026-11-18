# Feature Research

**Domain:** SIF v1.2 — search precision (metadata filtering + correctness/scale), MCP modernization + agent-native packaging, measurable quality (personal-corpus eval), engineering/distribution
**Researched:** 2026-11-13
**Confidence:** MEDIUM overall (load-bearing claims cross-verified against primary sources; per-source seam tiers recorded in Sources. Note: the research seam rates the `webfetch` provider LOW even for official primary sources; where such reads are corroborated by a second source the claim is tagged MEDIUM. Local codebase facts are HIGH — read directly.)
**Scope:** v1.2 target features ONLY. Existing validated capabilities (BM25/FTS5, sqlite-vec, weighted RRF, SearchPipeline, live index, bench harness, DYM, multi-format output, CLI `get --from-line/--lines/--line-numbers`) are treated as dependencies, not re-researched. Locked decisions (2026-11-13) respected: no PDF/HTML/EPUB, no chat-with-notes/ask, Windows full support deferred to v2, spellfix1 SKIP, symspellpy DEFER, semantic/late chunking SKIP, ANN SKIP.

## Feature Landscape

**Key context finding 1 — the parity target is real and verified.** qmd v2.8.3 (2026-08-16) already speaks MCP protocol 2026-07-28 via the official TypeScript SDK 2.x (sessionless HTTP, `server/discover`, 2025-era stdio clients still served). Its **[Unreleased]** flagship is opt-in namespaced frontmatter (`qmd.metadata`) + a recursive filter AST shared across CLI `--filter <json>` / SDK / MCP `query` / HTTP, applied **before RRF fusion and reranking**, plus a `metadata` discovery tool (MCP) and `qmd collection metadata` (CLI). SIF v1.2's filtering track catches up to qmd's *unreleased* state; the MCP track catches up to qmd's *released* state. qmd still has **no file watching** — SIF's v1.1 live index remains a differentiator. [MEDIUM: qmd CHANGELOG + README read directly (primary), cross-checked via commit abfabc5 docs and issue tracker]

**Key context finding 2 — MCP moved two eras; the SDK makes the jump a migration, not a rewrite.** SIF's hand-rolled server speaks 2024-11-05. Since then: 2025-03-26 added tool annotations + Streamable HTTP; 2025-06-18 added `structuredContent`/`outputSchema` + elicitation (and removed JSON-RPC batching); 2025-11-25 added the invalid-Origin **403 MUST**, tool-naming guidance, and "input validation errors are Tool Execution Errors, not Protocol Errors"; 2026-07-28 is a **stateless redesign** (no `initialize`, no sessions, per-request `_meta`, `server/discover` MUST, MRTR replaces server-initiated requests, `ping`/`logging/setLevel` removed, Roots/Sampling/Logging deprecated, deterministic `tools/list` SHOULD, `ttlMs`/`cacheScope` required on list results). The official **Python SDK v2.0.0** (released 2026-07-28, `FastMCP` renamed `MCPServer`) serves **both eras on the same endpoint with zero configuration**. For a loopback read-mostly search server, most of the new surface (MRTR, tasks, OAuth, subscriptions, sampling) is skippable — see Anti-Features. [MEDIUM: all four spec changelogs read directly from modelcontextprotocol.io (primary), cross-checked against SDK whats-new + release notes]

**Key context finding 3 — agent-native packaging is now table stakes.** qmd ships a Claude Code plugin marketplace (`claude plugin marketplace add tobi/qmd`) **and** an in-repo skill (`skills/qmd/SKILL.md`) whose citation rule is "Output is line-numbered and carries the docid — cite both". basic-memory ships a plugin with 8 skills + SessionStart/PreCompact hooks; GNO ships `gno skill install` + `gno mcp install --target claude-code`; memsearch ships a plugin + `uv tool install`. The official MCP Registry is in **preview** but publishable today, with a PyPI ownership-verification path (`mcp-name:` README marker) that fits SIF's `docsif` package. [MEDIUM: official docs + peer repos via cross-verified search]

**Key context finding 4 — label-free personal eval works, but only as relative A/B with bias controls.** Synthetic doc→query evaluation correlates with real-query system rankings at Kendall τ 0.48–0.88 (source-only labels), improving to 0.69–1.00 with pooled LLM relabeling (TU Delft MSc thesis, 2026-10). Synthetic queries reuse source wording, inflating BM25 (documented: 0.266→0.856 on a synthetic clinical corpus). LLM-as-judge is reliable for **relative system ranking** (run-level τ ≥ 0.86) but not absolute labels (doc-level κ ≈ 0.30–0.37; scores inflated ~+0.28), and becomes circular when the judge also reranks (τ 0.84 → 0.44). Absolute click metrics fail even at 10M–70M queries (CIKM 2008 / TOIS 2012) — at single-user N they are hopeless; interleaving-style **relative** comparison is the only statistically sound online pattern. [MEDIUM: peer-reviewed sources, cross-verified]

### Corrections to prior research leads (verified this session)

| Prior lead | Verdict | Evidence |
|------------|---------|----------|
| "Claude Code: `readOnlyHint:true` + `idempotentHint:true` enables auto-approval without prompts and plan-mode use" | **NOT confirmed — correct it.** Official docs document only: (a) `readOnlyHint:true` → calls run **in parallel** with other read-only calls; (b) `readOnlyHint` OR `idempotentHint` → **one retry** of a pending call after connection drop (HTTP/connector). "Annotations are metadata, not enforcement." Hint-based auto-approval is an **open feature request** (anthropics/claude-code#87452); plan-mode silent read-only execution is community-only evidence (jcodemunch-mcp PR #361). Do not write requirements that depend on auto-approval. | code.claude.com/docs/en/mcp ("Mark tools that are safe to call twice") + /agent-sdk/custom-tools ("Add tool annotations"), read directly [MEDIUM] |
| qmd v2.8.3 / filter AST / metadata tool / pre-RRF / `:from:count` since 2.5.3 / default models / no watching | **Confirmed** against primary CHANGELOG + README. Added detail: AST has 17 operators + `caseInsensitive`; discovery reports doc-counts (not value-counts), numeric min/median/max, mixed-type keys split per type, exact remainders; `file_sync_state` 20k-file first index ~5s vs ~3min. | raw.githubusercontent.com/tobi/qmd/main/{CHANGELOG,README}.md [primary; MEDIUM via cross-check] |
| MCP 2025-06-18 / 2025-11-25 / 2026-07-28 feature lists | **Confirmed** with nuance: tool annotations date to **2025-03-26** (not 2025-06-18); 2026-07-28 also removes SSE resumability, requires `resultType` on all results, moves tasks to an extension, and adopts a 12-month deprecation policy. | modelcontextprotocol.io spec changelogs [primary; MEDIUM via SDK cross-check] |
| TU Delft thesis τ 0.48–0.88 → pooled 0.69–1.00 | **Confirmed** (van Wolfswinkel, "Automated Offline Evaluation of RAG Pipelines Through Synthetic Query Generation", 2026-10). Nuance: it evaluates RAG pipelines with synthetic queries, not strictly "known-item" tasks; the known-item framing comes from the JMIR clinical bench and Dietz et al. 2025. Only **Promptagator** (few-shot in-domain query conditioning) beat naive doc2query across all datasets. | repository.tudelft.nl record uuid:eb09dbf7… [MEDIUM] |
| basic-memory / GNO / memsearch packaging; memsearch ONNX bge-m3 default | **Confirmed** (details in Competitor Analysis). | official docs/repos [MEDIUM] |
| Top qmd issue demands: Windows #452/#668, chunk size #641, CJK #454/#774 | **Confirmed**, plus higher-reaction correctness/scale issues that map directly to v1.2: **#952** (9👍, ~70s vsearch from per-expanded-query exact scans), **#897** (7👍, garbage vectors at 512-token batch boundary), **#685** (4👍, "Return multiple results per file"). | github.com/tobi/qmd/issues sorted by reactions [primary; LOW seam tier, single read] |

## Table Stakes (Users Expect These)

### A. Metadata filtering and discovery

What any 2026 personal-KB search tool exposing filters must do. Conventions verified across qmd (parity target), Elasticsearch, Weaviate, Meilisearch.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Recursive filter AST (and/or/not + eq/ne/gt/gte/lt/lte + in/nin/all + contains/prefix/suffix + type + exists, optional `caseInsensitive`) | qmd's unreleased flagship defines the parity bar; ES bool/filter, Weaviate And/Or operands, Meilisearch AND/OR/NOT all compose boolean filters. Flat key=value is no longer competitive for agent consumers | MEDIUM | Pydantic discriminated union on `operator` (SIF already uses Pydantic). Adopt qmd semantics verbatim: typed exact match **no coercion**, arrays are sets, **missing keys do not match `ne`/`nin`** (include them via `or` + `exists:false`), no implicit AND, `caseInsensitive` = ASCII folding. Add recursion-depth + size budgets (qmd caps: 64 keys, 128B key, 1024-char string, 128-element array, 64KB frontmatter) |
| Built-in `path` / `mtime` filter fields (plus tag/frontmatter keys) | Milestone scope; every engine filters on path/date natively (ES term/prefix/range, Meilisearch STARTS WITH/TO). qmd's AST is frontmatter-only + collection scoping — SIF extending to path/mtime is scoped parity-plus | LOW | **Both columns already exist** (`documents.path TEXT`, `documents.mtime REAL` — verified in schema.py). Reserved field names in the same AST; path prefix/glob + mtime numeric range push straight to SQL |
| Typed frontmatter extraction + namespaced opt-in | qmd: `qmd.metadata` block, strings/numbers/booleans/flat homogeneous arrays only; nested objects, nulls, empty arrays, mixed arrays **rejected** (doc still indexes, excluded from filtered search until corrected). Typing is what makes gt/lt/type meaningful | MEDIUM | **SIF already parses and persists full frontmatter**: `parser.py` uses python-frontmatter → `documents.metadata TEXT DEFAULT '{}'` (verified). Gap is typed normalization + namespace policy, not parsing. **Recommendation (requirements decision):** read the `qmd.metadata` namespace for migration compatibility (PROJECT.md constraint: qmd interface parity); keep raw JSON as-is. Reject-with-warning, never crash on bad frontmatter |
| Filter application BEFORE RRF fusion and rerank | Universal convention: qmd "applied before RRF fusion and reranking"; ES RRF retriever **propagates its filter to every sub-retriever**; Meilisearch filters then ranks within the filtered set. Post-fusion filtering breaks top-K completeness and wastes rerank compute | MEDIUM-HIGH | Pushdown per leg: SQL WHERE for BM25 (path/mtime indexed; metadata via typed kv join), candidate-ID binding for the vector leg. qmd hit SQLite's variable limit and binds candidate IDs as **one JSON list** — copy that. Document qmd's honesty caveat: "highly selective filters remain best-effort for top-K completeness"; interact with over-fetch (`candidate_limit`) so rerank still sees enough candidates |
| Shared CLI `--filter <json>` + MCP `filter` param (one AST, one validator) | qmd shares one AST across CLI/SDK/MCP/HTTP; milestone requires CLI+MCP parity. Agents construct JSON filters; humans use the same grammar | LOW-MED | Surface plumbing once the AST exists. **Invalid filter → MCP tool execution error (`isError`/ToolError), not protocol error** (2025-11-25 SEP-1303: enables model self-correction); qmd HTTP returns 400 for invalid filters. Error text must name the offending operator/field |
| `metadata` discovery tool (keys/types/value counts, numeric min/median/max, pagination with exact remainders) | qmd ships MCP `metadata` + `qmd collection metadata`; Meilisearch facetDistribution/facetStats and ES terms-agg are the hosted analogues. **Without discovery an agent cannot know which keys exist — filters become guesswork.** This is table stakes for agent-facing tools in 2026 | MEDIUM | Aggregate over the typed kv store (no re-index). qmd parity details: counts are **documents not values**; mixed-type keys split per type with own counts; `--filter` measures coverage against admitted docs; windowed key/value lists report exact remainder (`totalKeys`/`remainingKeys`/`remainingValues`); `--match` filters entries by `key`/`value`; sort count\|value, `--min-count`. CLI `sif collection metadata` + MCP `metadata` tool |
| Typed metadata storage for pushdown + discovery | qmd stores `document_metadata`/`document_metadata_values` with typed columns, rebuilt per update; JSON-blob scanning cannot serve gt/lt/type or cheap aggregates | MEDIUM | New kv table(s) + schema migration + backfill on reindex. At personal-KB scale (≤100k docs) this is small; `json_extract` expression indexes are a fallback but discovery stats favor typed rows. Rebuild-on-update matches qmd and SIF's existing delete-before-insert idempotency |
| Correct pagination under filter + dedup (stable order, limit/offset) | Milestone "pagination fixes"; ES/Meilisearch paginate the filtered+ranked set with deterministic order. Agents page through results; unstable order = duplicated/missed docs | LOW-MED | `hybrid.py` already over-fetches `max(limit+offset, candidate_limit)` and slices (verified) — fix the slice/dedup interaction, not the architecture. BM25 LIMIT/OFFSET exists. Add deterministic tiebreak (docid) so pages are stable across calls |

### B. Correctness and scale

Verified demand signals from qmd's issue tracker (reactions sorted) map 1:1 onto this track.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Parser dispatch wiring | Milestone gap; a search engine that silently mis-parses file types returns wrong content. `MarkdownParser` + code-language map exist but dispatch is unwired | LOW-MED | Wire extension→parser selection through the existing factory; regression-test each supported type. Keep text/code focus (PDF locked out) |
| Per-document vector result dedup | Duplicate chunks of one doc flooding top-K is the classic hybrid-search complaint; qmd #685 (4👍) shows the opposite tension (users also want multi-chunk access) | LOW-MED | Dedup by `document_id` keeping best-scoring chunk **before offset slicing** (dependency with pagination). **Recommendation:** dedup by default + explicit per-chunk escape hatch (`--per-chunk` / MCP param) to serve both camps; surface match-count per doc |
| Eliminate per-query full-table scans (staleness/contexts) | qmd #952 (9👍, top issue): ~70s vsearch from exact scans per expanded query; qmd fixed expansion dedup (#1000) in Unreleased. SIF's per-query staleness/contexts scans are the same anti-pattern | MEDIUM | Move to indexed lookups / precomputed state; v1.1 drift-refresh machinery exists — reuse its stat-based fast path instead of re-scanning per query. Budget: search latency must not carry index-maintenance cost |
| Title into FTS | Title is the highest-signal field in a notes corpus; every engine field-weights titles (ES multi_match boosts, Meilisearch searchableAttributes order, Weaviate BM25 property boosts). **Verified gap:** `documents_fts`/`chunks_fts` index `content` only (porter) | LOW-MED | Add title column to the external-content FTS table + trigger update + gated rebuild (SIF already has FTS migration machinery from CR-01). Use `bm25()` column weights; measure on bench before locking weights |
| `sif index vacuum` + backup | qmd Unreleased repacks vector tables in cleanup + final VACUUM after partition conversion; SQLite maintenance is expected of any local DB tool. Backup is the single-user safety net | LOW | VACUUM + `wal_checkpoint`; backup via SQLite online backup API (WAL-safe, never file-copy a live DB). Expose size-before/after |
| Embed streaming/batched with boundary correctness | qmd #897 (7👍): inputs at/over the 512-token physical batch boundary **silently store deterministic garbage vectors**. Milestone "embed 流式分批" must not repeat this | MEDIUM | Bounded batches streamed to the embedder; respect model context limits per chunk; verify output sanity (norm/finite) at batch boundaries; tie into embedder-identity marking (see D) |

### C. MCP modernization (loopback, read-mostly)

What a 2026-era local search server must expose. Spec facts verified against all four changelogs + SDK v2 docs.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Official Python SDK v2 (`MCPServer`) replacing the hand-rolled server, dual-era serving | qmd 2.8.3 already serves 2026-07-28 + 2025-era clients; SIF at 2024-11-05 is two eras behind. SDK v2.0.0 (2026-07-28) serves **both eras on one endpoint, zero config** — the ecosystem floor has moved | HIGH | `mcp.server.fastmcp` → `mcp.server.mcpserver` (old path **gone**, not deprecated); protocol types split to `mcp-types`; transport config moves to `run()` (`host/port/stateless_http/json_response/transport_security`); `stateless_http` only affects 2025-era clients. Sync handlers run on worker threads (SIF search is sync — fine). `ToolError` text reaches the model; `MCPError` becomes a protocol error — audit SIF's error paths. **Gaps to verify at plan time:** SDK v2 minimum Python (SIF targets 3.10+) and the exact structured-output API (not covered on the whats-new page) |
| Tool annotations on every tool: `readOnlyHint:true`, `idempotentHint:true`, `destructiveHint:false`, `openWorldHint:false` | Annotations exist since 2025-03-26; qmd/peers annotate. **Documented Claude Code effects:** read-only calls run in parallel; read-only/idempotent calls get one retry after connection drop. Defaults are conservative (readOnly false, destructive true) — unannotated tools look mutating | LOW | All five tools (query/get/multi_get/status/metadata) are pure reads over a local corpus → closed world, non-destructive. **Do NOT claim auto-approval** (see Corrections). Keep annotations accurate to handlers ("metadata, not enforcement") |
| `structuredContent` + `outputSchema` on query/get/multi_get/status/metadata | Added 2025-06-18; loosened 2026-07-28 (any JSON Schema 2020-12 / any JSON value). Claude Code Agent SDK documents structuredContent as the machine-readable channel; citation mapping relies on it (Foundry Q&A: inline markers have no official chunk-id mapping) | MEDIUM | Define result schemas carrying citation-grade fields (docid, path, title, score, line start/end, snippet, content hash, staleness). **Keep text `content` alongside** for 2025-era clients. Schema is a contract — version it |
| Host header validation (Origin already present) on HTTP transport | 2025-11-25: servers **MUST** return 403 for invalid Origin on Streamable HTTP; DNS-rebinding defense needs Host too. qmd validates both (`QMD_ALLOWED_ORIGINS`/`QMD_ALLOWED_HOSTS`); endpoints stay unauthenticated | LOW | SDK v2 `transport_security` + Host allowlist on `run()`. Loopback default allowlist (localhost/127.0.0.1/[::1]); explicit override env vars mirroring qmd UX |
| MCP `query` pipeline parity with CLI (rerank/expand/snippet) + lazy embedder + lex/vec tool wiring | Milestone requirement; qmd's `query` tool exposes `searches` (lex/vec/hyde sub-queries 1–10, first gets 2× weight), `rerank` (default true), `candidateLimit`, `minScore`, `intent`. An MCP tool weaker than the CLI is a broken promise to agents | MEDIUM-HIGH | Reuse `SearchPipeline` (exists). Lazy embedder load: BM25-only degradation at the SearchBackend boundary already exists — extend, don't reinvent. Decide rerank default for MCP deliberately (qmd defaults true; SIF CLI is opt-in — **recommendation:** keep opt-in for latency predictability, expose the flag, document the difference) |
| Deterministic `tools/list` order + `ttlMs`/`cacheScope` cache hints | 2026-07-28: deterministic order SHOULD (client prompt-cache hits); `ttlMs`+`cacheScope` **required** on list results (CacheableResult). SDK exposes `cache_hints=` per method | LOW | Static tool list → long TTL, `cacheScope:"public"` (single-user loopback, no shared intermediary). SDK handles `server/discover` (auto-derived), `resultType`, per-request `_meta` era negotiation — verify with the conformance suite, don't hand-roll |
| Tool naming + error semantics per 2025-11-25 guidance | SEP-986 naming guidance; SEP-1303 input-validation errors as tool execution errors so the model can self-correct | LOW | Keep qmd-compatible snake_case names (query/get/multi_get/status/metadata); clients namespace as `mcp__sif__query`. Filter-AST validation failures → ToolError with actionable message, never a protocol error |
| `sif mcp daemon` stub closure | Milestone item; qmd `mcp --http --daemon` + PID file + `mcp stop` is the peer UX; SIF already has v1.1 daemon infrastructure (PID/stop/status, launchd/systemd) | LOW-MED | Reuse the watch-daemon lifecycle machinery; keep models warm (qmd's stated daemon purpose). Non-TTY quiet logging |

### D. Measurable quality

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Personal known-item bench instrument (`sif eval --personal`, label-free) | Milestone centerpiece; v1.1 proved the pattern (synthetic bench + held-out 0.01 tie rule). TU Delft: synthetic doc2query ranks 8 fixed pipelines at τ 0.48–0.88 vs real queries; pooled LLM relabeling → 0.69–1.00. A personal-corpus instrument is how default changes get evidence on the user's own notes | HIGH | Generate queries from the user's docs (gold = source doc, no human labels). **Bias controls are the feature, not garnish:** (1) offer paraphrase/metadata-only query variants — JMIR showed BM25 keyword scores inflate 0.266→0.856 on synthetic corpora; (2) Promptagator-style few-shot conditioning on real user queries (query_log exists) beat naive doc2query in the thesis; (3) report BM25-only vs hybrid deltas so lexical reuse is visible; (4) held-out split + existing nDCG@10/Hit@10/MRR + 0.01 tie rule. Local-LLM generation optional; deterministic template fallback keeps it offline |
| Harrier-OSS-v1-0.6b gated evaluation (EN+ZH held-out, win-only switch) | PROJECT.md locked decision. Verified model facts: Microsoft Bing team, 2026-03-30, MIT, 0.6B, **1024-dim**, 94 languages incl. EN+ZH, Qwen3-based decoder + ST projection head, **last-token pooling + L2 norm**, 32k context, Multilingual MTEB v2 69.0 | MEDIUM | **Same 1024 dims as Qwen3-Embedding-0.6B → width guards silently accept a bad switch** (verified: `document_embeddings FLOAT[dim]` fixed at creation). Embedder identity marker = model name+version+pooling+prompt scheme, not width. Query-side `prompt_name` required (last-token pooling models). Independent evidence is EN-only (localGPT A/B per PROJECT.md) — ZH held-out is the gate. Note: last-token pooling also re-confirms the late-chunking SKIP |
| rapidfuzz DYM swap, measured | PROJECT.md decision: rapidfuzz > symspellpy (defer) > spellfix1 (skip). Verified: MIT, C++ bit-parallel kernels, ~order-of-magnitude faster than difflib; 2025 multilingual benchmark ~40% faster + memory-efficient; `process.extract/extractOne` with `score_cutoff` | LOW | Migrate score scale (0–100 vs difflib 0–1) deliberately. Remove first-letter bucketing (the recall fix per PROJECT decision). Vocabulary source `documents_fts_v` (fts5vocab) already exists. Measure recall/latency vs difflib baseline on the personal vocab; keep the v1.1 ≤10ms budget. CyDifflib is the drop-in-API alternative if migration friction matters |
| Chunk size/overlap sweep + title-breadcrumb experiment | qmd #641 (configurable chunk size/overlap) is a verified user demand; v1.1 established bench-before-tuning. Chunking is the cheapest quality dial left | MEDIUM | Grid sweep on synthetic + personal bench (deterministic pipeline — freeze expansion). Title breadcrumbs = prepend heading path to chunk text; treat as experiment with held-out evidence, not a default-on change. Expose size/overlap as settings only after the sweep shows a defensible default |
| Relative A/B reporting with noise gate (reuse v1.1 tie rule) | CIKM 2008/TOIS 2012: absolute usage metrics fail at realistic N; relative paired comparison is the sound pattern. UMBRELA: LLM judges valid for run-level ranking (τ≥0.86), not absolute labels | LOW | Report deltas vs baseline with the existing 0.01 held-out tie rule; refuse to crown winners inside noise. This is harness behavior, mostly exists — extend to the personal instrument |

### E. Engineering and distribution

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Test CI matrix (py3.10–3.13 × ubuntu/macos) | Milestone item; a published package without CI is a trust gap. Suite exists (1591 tests, fail_under=90) | MEDIUM | Model-free test paths in CI (no torch on the CI pytest per project memory); coverage gate must hold on every matrix cell; ruff/format/ty gates reuse existing Makefile targets |
| Windows smoke (hc remote yoga) | Milestone item; qmd's top Windows issues (#452 3👍, #668 2👍) show the demand is real but full support is locked to v2 | LOW-MED | yoga has no Python (Store alias only) — uv/Python setup first. Smoke = install → index → search → MCP stdio handshake. Document known POSIX-only corners (fork/systemd/flock) as v2 scope, not bugs |
| PyPI publish (`docsif`, trusted publishing) | Milestone item; **hard prerequisite for MCP Registry listing** (registry hosts metadata only, package must exist first). Peers: basic-memory/memsearch on PyPI via uv | LOW-MED | OIDC trusted publishing (no long-lived tokens); version bump + extras/Makefile/pre-commit cleanup per milestone; verify `uvx docsif --help` works from a clean env |
| MCP Registry listing | Discoverability floor for MCP servers in 2026; qmd-class tools are listed. **Preview status** — breaking changes/data resets possible before GA | LOW (after PyPI) | `mcp-publisher` CLI (brew/binary): `init` → `login github` (device flow) → `publish`. `server.json`: name `io.github.<user>/docsif` (GitHub auth namespace rule), description ≤100 chars, version unique+immutable, `packages:[{registryType:"pypi", identifier:"docsif", transport:{type:"stdio"}}]`. **PyPI ownership marker: `mcp-name: io.github.<user>/docsif` line (or HTML comment) in the package README.** Verify via `registry.modelcontextprotocol.io/v0.1/servers?search=…`. Optional GitHub Actions OIDC (`id-token: write`) |
| Claude Code plugin + skill | All four surveyed peers ship one (qmd marketplace+skill, basic-memory 8 skills+hooks, GNO skill+mcp install, memsearch plugin). An MCP server without agent packaging is invisible to the target user | MEDIUM | In-repo `.claude-plugin/plugin.json` + `marketplace.json` (source can be `github` or `pip`); root `.mcp.json` with `command: uvx, args: [docsif, mcp]` (no pre-install needed; basic-memory's uvx-fallback precedent); `skills/sif-search/SKILL.md` teaching: when to search, filter AST usage, metadata discovery first, **search→get citation discipline** (cite docid + line numbers from get output, not snippets — qmd skill + Vault-Agent-Memory pattern). `${CLAUDE_PLUGIN_ROOT}` for internal refs; `claude plugin validate`; name must not start `claude-`/`anthropic-`. SKILL.md description drives invocation (~1536-char budget) |
| `sif models pull/status` + downloader fixes + non-TTY quiet | qmd precedent: `qmd pull` prefetches, progress hidden by default (`--progress` to show); models auto-download on first use. Milestone item; silent non-TTY behavior is required for CI/MCP log hygiene | LOW-MED | `status`: cached models, dims, **identity marker** (feeds the Harrier gate); `pull`: explicit prefetch with checksum verification; fix downloader bugs per milestone; detect TTY before emitting progress |
| uv-first install docs | Peers are uv-first (basic-memory `uv tool install`, memsearch `uv tool install [onnx]`); qmd is npm/bun. uv is the 2026 Python CLI install convention | LOW | Rewrite install docs: `uv tool install docsif` / `uvx docsif mcp` primary, pip fallback; client config snippets (Claude Code/Desktop/Cursor) mirroring qmd README structure |

## Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Full qmd-unreleased filter parity **plus built-in path/mtime fields** | qmd's AST covers frontmatter + collections only; SIF's milestone adds path/mtime/tag as first-class AST fields — strictly more expressive than the parity target at release time | MEDIUM-HIGH | Depends on the whole A-track; the built-in fields are nearly free (columns exist) once the AST lands |
| Label-free personal-corpus eval shipped as a command | qmd ships a synthetic `bench`; basic-memory/GNO/memsearch ship none. `sif eval --personal` turns "did that change help MY notes?" into a repeatable measurement — unique in the peer set | HIGH | The bias controls (paraphrase variants, pooled judgments, BM25-delta reporting) are what make it credible rather than theater |
| Citation-grade `structuredContent` (docid + path + line range + content hash + staleness) | Most MCP search tools return text blobs; structured citation fields let agents map results→sources reliably (the documented Foundry pain point) and detect drift between search and get | MEDIUM | Rides on SDK v2 + existing CLI line-range get + existing checksums; the schema is the differentiator, not new machinery |
| Skill-encoded two-stage citation discipline | qmd's skill says "cite both" (docid + line numbers); Vault-Agent-Memory forbids citing snippets. Shipping a skill that enforces search→get→cite makes SIF results verifiably grounded out of the box | LOW-MED | Packaging, not engine work; compounds with the structuredContent schema |
| Live index + MCP-embedded freshness (v1.1, retained) | qmd **still has no watching** (verified again this session); SIF's always-fresh MCP queries remain unmatched in the peer set | — (shipped) | Mention in plugin/skill marketing; do not re-build |
| Discovery with exact remainders + numeric min/median/max + filter-aware coverage | qmd parity detail most tools skip; lets agents budget pagination and understand key distributions before filtering | MEDIUM | Part of the A-track discovery tool; the exactness details are the polish |

## Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| PDF/HTML/EPUB parsing | "Competitors have it" | **Locked out 2026-11-13 (user-confirmed).** Parsing tax + quality variance distracts from text/code precision | Keep text/code focus; archived pypdf/trafilatura selection research stays archived |
| chat-with-notes / `ask` command | "GNO has ask; RAG is the trend" | **Locked out.** MCP consumers ARE the chat layer; building QA duplicates them badly and shifts investment away from retrieval quality | Citation-grade retrieval (structuredContent + line ranges + skill discipline) — let the agent compose answers |
| Full Windows support in v1.2 | qmd #452/#668 demand | **Locked to v2.** POSIX fork/systemd-everywhere/flock degradation needs dedicated design | v1.2 CI smoke only (hc remote yoga); document known limitations honestly |
| spellfix1 / symspellpy / match-time fuzzy | "Real spell correction" | **Locked:** spellfix1 SKIP (ASCII-only distance core, sdist packaging tax, zero CJK benefit); symspellpy DEFER (>200k vocab only); match-time fuzzy needs trigram re-index | rapidfuzz DYM swap (measured) over the existing FTS vocabulary |
| Semantic / late chunking | "SOTA chunking" | **Locked SKIP** (NAACL 2025 counter-evidence; last-token pooling mechanical incompatibility — re-confirmed by Harrier's last-token pooling) | Size/overlap sweep + title breadcrumbs, measured |
| ANN vector index | "Scale to millions" | **Locked SKIP.** 100k vectors brute-force 75–150ms is adequate; ANN adds recall loss + build complexity | sqlite-vec quantization+rescore is the documented escape hatch if scale demands |
| Post-fusion filtering (`post_filter`-style) | "Simpler: filter the final list" | Breaks top-K completeness (filtered docs consume ranks), wastes rerank compute on rejected docs; contradicts qmd/ES/Meilisearch convention | Pre-RRF pushdown per leg (A-track); document best-effort top-K under highly selective filters |
| SQL/string passthrough filters | "Power users want SQL" | Injection surface, unvalidatable, breaks the shared CLI/MCP contract, impossible to schema-describe to agents | The recursive AST with budgets; `type`/`exists` cover the legitimate power cases |
| Nested frontmatter objects / arbitrary YAML paths | "My notes have nested metadata" | qmd deliberately rejects nested objects/nulls/empty/mixed arrays — typing and pushdown stay tractable; nested paths explode the discovery surface | Flat homogeneous arrays only (qmd parity); reject-with-warning, doc still indexes |
| OAuth / elicitation / MRTR / tasks / sampling / roots / logging on the loopback server | "Spec completeness" | No threat model (single-user loopback; qmd's endpoints are unauthenticated + Origin/Host-guarded); no mid-call user input needed; search is sub-second (tasks SDK support doesn't even exist yet); Roots/Sampling/Logging are **deprecated** in 2026-07-28 with a 12-month removal window | Origin+Host 403 validation; annotations; structuredContent; cache hints; stderr logging. Skip the rest deliberately and document why |
| Promising auto-approval from `readOnlyHint`/`idempotentHint` | "Annotated tools run without prompts" | **Not documented behavior** (official docs: parallel + retry only; hint-based permissions are an open feature request #87452). Requirements built on it will fail UAT | Annotate accurately for the documented benefits; use allow-rules/`allowedTools` for pre-approval; never claim prompt-free execution |
| Absolute click/CTR quality gates; LLM judge as absolute oracle; judge==reranker | "Use real usage data / LLM labels" | CIKM 2008/TOIS 2012: absolute metrics fail even at 10M+ queries, hopeless at single-user N. LLM doc-level κ≈0.30–0.37, scores inflated ~+0.28; judge-that-reranks circularity drops τ 0.84→0.44 | Offline relative A/B with held-out tie rule; pooled LLM judgments for relative grading only; judge model ≠ rerank model; log implicit signals descriptively |
| Faceted-search UI / disjunctive faceting | "Meilisearch has facets" | Web UI is locked out; disjunctive faceting needs multi-search machinery for a single-user CLI/MCP tool | The `metadata` discovery tool IS the facet equivalent for agents (counts + stats + remainders) |
| Index-mutating MCP tools without `destructiveHint` | "Let the agent reindex" | MCP is read-mostly by design; unannotated mutations violate the conservative-default contract and surprise users | Keep mutations in CLI/watch; if ever exposed, `destructiveHint:true` + explicit approval semantics |

## Feature Dependencies

```
A. FILTERING TRACK
[Typed frontmatter extraction] ──requires──> [parser frontmatter parse (HAVE)] + [namespace decision]
[Metadata kv storage + migration] ──requires──> [typed extraction] + [reindex/backfill path (HAVE idempotent re-chunk)]
[Filter AST + validator] ──requires──> [Pydantic (HAVE)]            (parallelizable with storage)
[Pre-RRF pushdown] ──requires──> [AST] + [kv storage] + [path/mtime columns (HAVE)]
[CLI --filter / MCP filter param] ──requires──> [AST + pushdown]
[metadata discovery tool] ──requires──> [kv storage]
[Pagination fixes] ──independent── ; [Vector dedup] ──must-precede──> [offset semantics]

B. CORRECTNESS TRACK (mostly independent)
[Parser dispatch] ──independent──
[Title FTS] ──requires──> [FTS migration machinery (HAVE, CR-01)]
[Per-query scan elimination] ──requires──> [v1.1 drift/stat fast path (HAVE)]
[vacuum/backup] ──independent── ; [Embed batching] ──interacts──> [embedder identity marker]

C. MCP TRACK
[SDK v2 migration] ──gates──> [annotations] + [structuredContent/outputSchema] + [cache hints]
                              + [server/discover + resultType] + [Host validation (transport_security)]
[MCP query parity] ──requires──> [SearchPipeline (HAVE)] + [new tool surface] + [lazy embedder]
[structuredContent citation fields] ──requires──> [SDK v2] + [line-range get (HAVE CLI; MCP parity)]
                                                  + [docid/checksum (HAVE)]
[sif mcp daemon closure] ──requires──> [v1.1 daemon lifecycle (HAVE)]

D. QUALITY TRACK
[Personal bench instrument] ──requires──> [bench harness (HAVE)] + [query generation] + [query_log (HAVE)]
    └──feeds──> [Harrier gate] + [chunk sweep] + [rapidfuzz measurement]
[Harrier gate] ──requires──> [personal bench EN+ZH held-out] + [embedder identity marker]
[rapidfuzz swap] ──requires──> [DYM (HAVE)] + [fts5vocab (HAVE)] + [measurement]

E. DISTRIBUTION TRACK
[PyPI publish] ──hard-prerequisite──> [MCP Registry listing (+ README mcp-name marker)]
[Plugin + skill] ──requires──> [stable MCP tool surface (C-track settled)] + [uvx entry point]
[CI matrix] ──independent── ; [Windows smoke] ──requires──> [CI] + [uv/Python setup on yoga]
[models pull/status] ──independent── ; ──enhances──> [install docs, registry UX, Harrier gate]
```

### Dependency Notes

- **Filtering is a chain, but two links parallelize:** AST+validator and typed storage can be built concurrently; pushdown needs both. Discovery needs only storage. Pagination/dedup are independent correctness work, but **dedup must be defined before offset semantics** (dedup-then-slice, not slice-then-dedup).
- **SDK migration is the gate for the entire MCP feature set** — annotations, structuredContent, cache hints, discover, Host validation all ride on it. Sequence it first in the MCP track; query parity can be developed against SearchPipeline beforehand but must land on the new tool surface to avoid double work.
- **PyPI → Registry is a hard external order** (registry verifies package ownership; the package must exist). Plugin/skill should land **after** tool names/schemas stabilize (post-SDK + parity) so the skill text doesn't churn.
- **Bench before tuning, again:** the personal instrument is the measurement substrate for the Harrier gate, chunk sweep, and rapidfuzz swap — v1.1's lesson transfers directly. Build the instrument first in the quality track.
- **Cross-track coupling:** structuredContent citation fields depend on MCP get parity (C) and existing line-range/hash machinery (B/HAVE); the `metadata` tool is simultaneously an A-track feature and a C-track tool — agree its schema once. Embed batching (B) and the Harrier gate (D) share the embedder-identity marker — define it once.
- **Namespace decision is a requirements fork:** reading `qmd.metadata` (recommended for migration parity) vs a SIF-native namespace changes extraction, docs, and skill text. Decide before A-track implementation.

## MVP Definition

### Launch With (v1.2)

All milestone-scoped; ordering within follows the dependency chains above.

- [ ] Filter AST + typed extraction + kv storage + pre-RRF pushdown + CLI/MCP surfaces — the precision headline (qmd-unreleased parity + path/mtime)
- [ ] `metadata` discovery tool (CLI + MCP) — what makes filters usable by agents
- [ ] Pagination/dedup/parser-dispatch/title-FTS/scan-elimination correctness fixes — trust floor; verified qmd issue demand
- [ ] `sif index vacuum` + backup; embed streaming/batching with boundary sanity
- [ ] SDK v2 migration with dual-era serving + annotations + structuredContent/outputSchema + Host validation + cache hints — the 2026 readiness headline
- [ ] MCP query pipeline parity + lazy embedder + lex/vec wiring + daemon stub closure
- [ ] Personal known-item bench instrument with bias controls — evidence substrate
- [ ] Harrier EN+ZH held-out gate + embedder identity marker (win-only switch)
- [ ] rapidfuzz DYM swap (measured) + chunk size/overlap sweep + title-breadcrumb experiment
- [ ] CI matrix + Windows smoke; PyPI publish; MCP Registry listing; plugin + skill; models pull/status; uv-first docs

### Add After Validation (v1.x)

- [ ] LLM-as-judge relative grading layer for the personal bench — trigger: known-item harness adopted; pooled judgments, judge ≠ reranker
- [ ] Saved filters / filter presets — trigger: filter usage observed in query_log
- [ ] SessionStart hook-assisted freshness in the plugin (basic-memory pattern) — trigger: plugin adoption; watch already covers freshness, so this is convenience only
- [ ] `bench --sweep` automation over the personal instrument — trigger: manual grids prove insufficient

### Future Consideration (v2+)

- [ ] Full Windows support (locked v2; fork/systemd/flock design)
- [ ] symspellpy (only if vocab >200k), ANN quantization+rescore escape hatch (only if scale demands)
- [ ] MCP resources/prompts surface (documents-as-resources) — only if a consumer asks; tools are the peer convention
- [ ] Sensitivity-aware search (SIGIR'26 direction) — not needed for single-user local; revisit only if sharing features ever appear

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Filter AST + pushdown + surfaces | HIGH | MEDIUM-HIGH | P1 |
| Typed extraction + kv storage | HIGH (enabler) | MEDIUM | P1 |
| metadata discovery | HIGH | MEDIUM | P1 |
| Pagination + dedup correctness | HIGH | LOW-MED | P1 |
| Parser dispatch / title FTS / scan elimination | HIGH | LOW-MED each | P1 |
| vacuum/backup + embed batching | MED-HIGH | LOW / MEDIUM | P1 |
| SDK v2 migration (dual-era) | HIGH | HIGH | P1 (first in MCP track) |
| Annotations + structuredContent + Host + cache hints | HIGH | LOW-MED | P1 (after SDK) |
| MCP query parity + lazy embedder | HIGH | MED-HIGH | P1 |
| Personal bench instrument | HIGH | HIGH | P1 (first in quality track) |
| Harrier gate + identity marker | MED-HIGH | MEDIUM | P1 (after instrument) |
| rapidfuzz swap | MED | LOW | P1 |
| Chunk sweep + breadcrumbs | MED | MEDIUM | P1 |
| CI matrix + Windows smoke | HIGH (trust) | MEDIUM | P1 |
| PyPI publish | HIGH (enabler) | LOW-MED | P1 (before registry) |
| MCP Registry listing | MED-HIGH | LOW | P1 (after PyPI) |
| Plugin + skill | HIGH | MEDIUM | P1 (after tool surface settles) |
| models pull/status + uv docs | MED-HIGH | LOW-MED | P1 |
| LLM-judge grading layer | MED | MEDIUM | P2 |
| Saved filters / hooks / sweep automation | MED | LOW-MED | P2 |

**Priority key:** P1 = must have for v1.2 (all milestone-scoped); P2 = should have after core validates; P3/v2+ = deferred per locked decisions.

## Competitor Feature Analysis

| Feature | qmd (parity reference) | basic-memory | GNO | memsearch | Hosted-engine convention (ES/Weaviate/Meilisearch) | Our Approach |
|---------|------------------------|--------------|-----|-----------|----------------------------------------------------|--------------|
| Metadata filtering | [Unreleased] recursive AST, 17 ops + caseInsensitive, pre-RRF, CLI/SDK/MCP/HTTP shared; typed `qmd.metadata` frontmatter | None (wikilink graph + hybrid search_notes, min_similarity 0.45) | None documented (retrieval ladder instead) | None (memory layers) | ES bool filter + RRF filter propagation; Weaviate where operands; Meilisearch expressions, filter-before-rank | qmd AST parity + built-in path/mtime fields; typed kv pushdown; ToolError validation |
| Metadata discovery | [Unreleased] `metadata` MCP tool + `collection metadata` CLI; counts/types/min-median-max, exact remainders | None | None | None | facetDistribution/facetStats (Meili), terms agg (ES) | Full parity incl. filter-aware coverage + remainders |
| MCP era | **2026-07-28 via TS SDK 2.x**, sessionless HTTP, server/discover, 2025-era stdio still served | FastMCP (prerelease dependency noted in install docs) | MCP install target claude-code | MCP plugin | n/a | Python SDK v2 MCPServer, dual-era zero-config |
| Annotations / structured output | TS SDK 2.x surface (annotations/structured output available) | FastMCP annotations (per prior lead; not re-verified this session) | not verified | not verified | n/a | readOnly+idempotent on all 5 tools; structuredContent with citation fields; no auto-approval claims |
| Agent packaging | Plugin marketplace (tobi/qmd) + in-repo skill ("cite docid + line numbers") | Plugin: 8 skills + SessionStart/PreCompact hooks, uvx fallback; npx skills add | `gno skill install` + `gno mcp install` (coexist); recall <512 tokens | Plugin + uv tool install [onnx]; search→expand(chunk_hash) | n/a | Plugin + marketplace.json + citation-discipline skill; uvx entry |
| Registry | Listed (ecosystem presence) | Listed | Listed | Listed | n/a | io.github.<user>/docsif via mcp-publisher; PyPI mcp-name README marker; preview caveat |
| Eval instrument | Synthetic `bench` fixture (Hit@K lineage) | None shipped | None shipped | None shipped | n/a | Synthetic bench (HAVE) + **personal label-free instrument** (differentiator) with bias controls |
| Citation conventions | docid #abc123 + path:from:count (2.5.3+) + lineNumbers; skill: cite both | Markdown permalinks/wikilinks | recall facts + sources | chunk_hash expand | n/a | docid+path+line range+hash in structuredContent; two-stage search→get; cite get output only |
| Models UX | Auto-download first use; `qmd pull` (progress hidden default); embeddinggemma-300M + Qwen3-Reranker-0.6B + expansion-1.7B | uv-managed deps | Qwen3-Embedding/Reranker-0.6B, slim/quality bundles | ONNX bge-m3 ~558MB default + Milvus Lite | n/a | models pull/status + identity marker + non-TTY quiet; Harrier gated |
| Live index | **None** (manual update + file_sync_state fast path) | Sync on write | n/a | Transcript ingest | n/a | v1.1 watch/daemon/MCP-embedded (retained differentiator) |
| Install | npm/bun -g @tobilu/qmd (Node ≥22) | uv tool install (--prerelease=allow gotcha) | Installer + skill/mcp install commands | uv tool install [onnx] | n/a | uv tool install docsif / uvx docsif mcp first |

## Sources

Confidence tags use the research seam's provider tiers (`webfetch`=LOW even for primary sources; `websearch` cross-verified=MEDIUM; local code=HIGH). "Primary" marks official sources read directly. All URLs are the real task-target sources; no proxies/mirrors were used as substitutes.

**qmd (parity target)**
- https://raw.githubusercontent.com/tobi/qmd/main/CHANGELOG.md — primary, read 2026-11-13; v2.8.3 (2026-08-16) + [Unreleased] filter AST/metadata/file_sync_state/partitioning; MCP 2026-07-28 via TS SDK 2.x — LOW seam tier (webfetch), cross-checked → MEDIUM
- https://raw.githubusercontent.com/tobi/qmd/main/README.md — primary; tools/params, filter semantics, models, install, plugin marketplace, Origin/Host — LOW seam tier, cross-checked → MEDIUM
- https://github.com/tobi/qmd/commit/abfabc5424623046069c42705682c9da0966511a — metadata docs commit (search-surfaced) — MEDIUM
- https://github.com/tobi/qmd/issues?q=is%3Aissue%20state%3Aopen%20sort%3Areactions-%2B1-desc — primary issue tracker; #952/#897/#685/#452/#454/#668/#641/#774 — LOW seam tier (single webfetch read)
- https://deepwiki.com/tobi/qmd/3.7-metadata-and-frontmatter-filtering — AI-generated wiki; implementation limits + kv tables; corroborates primary only — LOW individually

**MCP specification + SDK**
- https://modelcontextprotocol.io/specification/2025-03-26/changelog — primary; annotations + Streamable HTTP added — LOW seam tier, cross-checked → MEDIUM
- https://modelcontextprotocol.io/specification/2025-06-18/changelog — primary; structuredContent/outputSchema, elicitation, batching removed — LOW seam tier, cross-checked → MEDIUM
- https://modelcontextprotocol.io/specification/2025-11-25/changelog — primary; Origin 403 MUST, naming guidance, tasks experimental, ToolError validation guidance — LOW seam tier, cross-checked → MEDIUM
- https://modelcontextprotocol.io/specification/2026-07-28/changelog — primary; stateless redesign, server/discover MUST, MRTR, resultType, ttlMs/cacheScope, deprecations — LOW seam tier, cross-checked → MEDIUM
- https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/docs/whats-new.md — primary; MCPServer rename, dual-era zero-config, cache_hints, breaking changes — LOW seam tier, cross-checked → MEDIUM
- https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.0.0b1 + https://newreleases.io/project/github/modelcontextprotocol/python-sdk/release/v2.0.0 — v2.0.0 stable 2026-07-28 — MEDIUM

**Claude Code behavior + packaging**
- https://code.claude.com/docs/en/mcp — primary, read directly (both halves); "Mark tools that are safe to call twice" (parallel + one retry), anthropic/requiresUserInteraction, anthropic/maxResultSizeChars (50k→500k) — LOW seam tier, cross-checked with second official page → MEDIUM
- https://code.claude.com/docs/en/agent-sdk/custom-tools.md — primary; "Annotations are metadata, not enforcement", defaults table, readOnlyHint parallelism, structuredContent — LOW seam tier, cross-checked → MEDIUM
- https://github.com/anthropics/claude-code/issues/87452 — open feature request for hint-based permissions (evidence auto-approval is NOT current behavior) — MEDIUM
- https://github.com/jgravelle/jcodemunch-mcp/pull/361 — community plan-mode claim (weak evidence, flagged as such) — LOW
- https://code.claude.com/docs/en/plugins + https://code.claude.com/docs/en/plugins/overview (+ manifest-reference) — plugin/marketplace/SKILL.md conventions — MEDIUM (search-corroborated official docs)

**MCP Registry**
- https://modelcontextprotocol.io/registry/quickstart.md — primary, read directly; preview status, mcp-publisher flow, server.json fields, **PyPI `mcp-name:` README marker** (troubleshooting table) — LOW seam tier, cross-checked → MEDIUM
- https://modelcontextprotocol.io/registry/authentication.md — namespace rules (io.github.<user>/*) — MEDIUM

**Peer tools**
- https://docs.basicmemory.com/local/local-install + /integrations/claude-code + https://github.com/basicmachines-co/basic-memory/pull/865 — uv install, plugin/skills/hooks — MEDIUM
- https://gno.sh/docs/skills + /docs/quickstart + https://github.com/gmickel/gno — skill/mcp install, retrieval ladder — MEDIUM
- https://github.com/zilliztech/memsearch (README) + https://zilliztech.github.io/memsearch/home/skills-from-memory/ — plugin, ONNX bge-m3, chunk_hash expand — MEDIUM

**Filtering conventions (hosted engines)**
- https://www.elastic.co/guide/en/elasticsearch/reference/6.8/query-filter-context.html + https://www.elastic.co/docs/solutions/search/retrievers-overview + https://www.elastic.co/search-labs/blog/elasticsearch-retrievers — filter context, RRF filter propagation, rank_constant=60 — MEDIUM
- https://github.com/weaviate/docs/blob/main/docs/weaviate/api/graphql/filters.md + https://weaviate.github.io/typescript-client/types/core_src.Operator.html + https://docs.weaviate.io/weaviate/concepts/search/hybrid-search — operator enum, Like cost, fusion/alpha — MEDIUM (hybrid+where timing: GAP, see below)
- https://www.meilisearch.com/docs/capabilities/filtering_sorting_faceting/advanced/filter_expression_syntax + https://www.meilisearch.com/docs/capabilities/filtering_sorting_faceting/how_to/search_and_filter_together — expression syntax, filter-before-ranking, facetStats — MEDIUM

**Evaluation evidence**
- https://repository.tudelft.nl/record/uuid:eb09dbf7-c826-4c63-8bd4-f37f96db38d1 — van Wolfswinkel MSc thesis (2026-10): τ 0.48–0.88 → pooled 0.69–1.00; Promptagator — MEDIUM
- https://medinform.jmir.org/2026/1/e94241/PDF (+ preprints.jmir.org/preprint/94241/accepted) — known-item clinical bench; BM25 lexical inflation 0.266→0.856; metadata-only τ 0.59–0.90 — MEDIUM
- https://uwspace.uwaterloo.ca/bitstreams/56a91d69-0efa-4944-85f5-552432fd5806/download — UMBRELA: run-level τ≥0.86/ρ≥0.97, doc-level κ 0.30–0.37 — MEDIUM
- https://bhaskar-mitra.github.io/files/3746252.3760908.pdf — Rahmani et al. CIKM'25 synthetic-eval bias (+0.28 judge inflation; generator favoritism) — MEDIUM
- https://krisztianbalog.com/files/sigir2025-llms.pdf — Balog SIGIR'25 tutorial: judge circularity risk — MEDIUM
- https://www.cs.unh.edu/~dietz/papers/dietz2025principles.pdf — Dietz et al. 2025: UMBRELA τ 0.84 vs human → 0.63/0.44 when judge also reranks (numbers via search extraction, not full-text read) — MEDIUM, verify at plan time if load-bearing
- https://www.cs.cornell.edu/courses/cs6784/2010sp/lecture/21-RadlinskiEtAl08.pdf + https://dtic.dimensions.ai/details/publication/pub.1031929131 — CIKM 2008: absolute metrics fail, interleaving works — MEDIUM
- https://www.cs.cornell.edu/courses/cs6784/2014sp/lectures/15-ChapelleEtAl12.pdf — TOIS 2012 large-scale interleaving validation — MEDIUM
- https://arxiv.org/abs/2606.27559 — SIGIR'26 sensitivity-aware personal-search test collection (Enron; crowdsourced + LLM-augmented judgments; ir_datasets) — primary abstract read — LOW seam tier (context only)

**DYM + models**
- https://pypi.org/project/RapidFuzz/ + https://raw.githubusercontent.com/The-Billy-Company/unstd/refs/tags/v2.0.0/src/unstd/text/README.md + http://ijeedu.com/index.php/ijeedu/article/download/188/99/489 — MIT/C++/perf, score-scale difference, 2025 multilingual benchmark — MEDIUM
- https://ai.azure.com/catalog/models/microsoft-harrier-oss-v1-0.6b + https://developer.furiosa.ai/v2026.4.0/en/furiosa_llm/models/harrier-oss-v1.html + https://the-decoder.com/microsofts-bing-team-open-sources-harrier-embedding-model/ — Harrier facts (1024-dim, 94 langs, last-token pooling, MIT, 2026-03-30) — MEDIUM

**Citation-grade retrieval**
- https://github.com/zyf0717/flash-context (path:42-88 default) + https://github.com/mgd43b/manicule (page/heading/line/cell citations) + https://pypi.org/project/groundkit/ (content-hash + verify_citation) + https://raw.githubusercontent.com/zycaskevin/Vault-Agent-Memory/a0a59c331b8900122c3417f789fa65134185d4f2/docs/document_map_citation_policy.md (cite read_range only) + https://raw.githubusercontent.com/opendatalab/Sciverse-Agent-Tools/main/skill-claude-code/SKILL.md (chunk_id/doc_id/offset) + https://github.com/nvidia/nemo-retriever/blob/ca5b3116669b710b2bddae1abba3ce28d8e72907/skills/nemo-retriever-mcp/SKILL.md + https://learn.microsoft.com/en-au/answers/questions/5936633/ (Foundry citation-mapping gap) — MEDIUM (multiple shipping tools agree)

**Local codebase (HIGH — read directly 2026-11-13)**
- src/sif/indexing/parser.py (python-frontmatter parse, title extraction, body-sha256 checksum), src/sif/database/schema.py (documents.metadata JSON persisted, mtime REAL, title TEXT, FTS content-only porter, fts5vocab, vec0 FLOAT[dim]), src/sif/database/repositories.py (metadata JSON round-trip), src/sif/search/hybrid.py (over-fetch+slice), src/sif/search/bm25.py (LIMIT/OFFSET), src/sif/mcp/server.py (hand-rolled registry)

## Gaps to Address (phase-specific research later)

- **SDK v2 minimum Python version and structured-output API** are not on the whats-new page — verify against SDK docs/source at MCP-phase plan time (SIF floor is 3.10).
- **qmd's filter AST is UNRELEASED** — it may change before qmd ships it. Pin expectations to the current CHANGELOG/commit abfabc5 era and re-verify at filtering-phase plan time.
- **Weaviate hybrid+where timing** not explicitly documented on the concepts page (two URL attempts 404). The pre-fusion convention is established by three other primary sources (qmd/ES/Meilisearch); no action needed unless a Weaviate-specific claim becomes load-bearing.
- **Claude Code plan-mode read-only behavior** rests on community evidence only; official docs document parallel+retry. Re-check official docs at packaging-phase plan time if any requirement depends on it.
- **MCP Registry is preview** — schema/flow may break or data may reset before GA; keep the listing step cheap and re-runnable (script it).
- **Dietz 2025 circularity numbers** were extracted via search, not full-text read — re-verify if they become load-bearing for the judge-layer requirement.
- **basic-memory FastMCP annotations** carried from prior leads were not re-verified this session (not load-bearing for SIF).

---
*Feature research for: DocSift/SIF v1.2 — Search Precision and Agent Experience*
*Researched: 2026-11-13*
