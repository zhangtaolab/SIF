# Pitfalls Research

**Domain:** Adding search precision (metadata filtering, correctness/scale fixes), MCP SDK v2 modernization, measurable quality (personal bench + gated model evaluation), and distribution (CI/PyPI/models UX) to SIF v1.2 — an existing local-first hybrid search engine (Python 3.10+, SQLite FTS5 porter + sqlite-vec, Click CLI + hand-rolled MCP, 1628 tests @ 95%)
**Researched:** 2026-11-13
**Confidence:** HIGH for codebase-grounded findings (every code claim below was read at HEAD `1aff2c9` and is cited file:line); MEDIUM for external ecosystem findings (classify-confidence seam: verified websearch = MEDIUM, generic webfetch floor = LOW — external claims are tagged per-source in Sources; official primary publishers are noted, and critical claims were cross-referenced across ≥2 independent sources per the verification protocol). One primary source was unavailable (ggml-org GGUF repo returned HTTP 401) and is flagged honestly.

**Locked decisions respected:** PDF/HTML/EPUB out; Windows full support deferred to v2 (smoke only); Harrier default switch only on EN+ZH held-out win; spellfix1 skip / symspellpy defer / semantic-late chunking skip / ANN skip; local-first MIT single-user.

## Critical Pitfalls

### Pitfall 1: Same-dimension embedder swap passes the width-only guard — silent vector contamination

**What goes wrong:**
Harrier-OSS-v1-0.6b and Qwen3-Embedding-0.6B are **both 1024-dim** (verified on both official model cards). SIF's only schema guard compares vector width: `_create_vector_tables` regex-matches `FLOAT[N]` against `settings.embedding_dim` (`src/sif/database/schema.py:361-376`). Swapping `SIF_MODEL_NAME` from Qwen3 to Harrier (or back) passes this guard, and the new model's query vectors get compared against the old model's stored document vectors — mutually unintelligible spaces, silently degraded search with zero errors. This is not hypothetical: localGPT's `design_rationale.md` documents exactly this failure ("It compared vector _width_ only, and harrier-0.6b and Qwen3-Embedding-0.6B are both 1024-dim … It would have appended mutually unintelligible vectors to a live table, silently") and shipped per-table embedder identity markers + `EmbedderMismatchError` as the fix.

**Why it happens:**
Width is the only dimension identity the schema records. The embedding cache bucket (`manager.py:153-163`: `model_type:model_name[@api_base]`) segments by *name*, which helps across named models but not across a GGUF file replaced at the same path/name, a model revision change, or a prompt-scheme change. Nothing records *which embedder wrote the stored vectors*.

**How to avoid:**
- Before any Harrier A/B: add a persisted embedder identity marker to the main DB (model name + resolved revision or file hash + pooling mode + normalization flag + query-prompt scheme), written at first embed and checked at every vector search/index open. Mismatch → fail fast with a re-embed instruction (the schema guard's existing error style), never silent acceptance. This is the PROJECT.md locked gate ("embedder 身份标记防同维陷阱") — implement it as a precondition plan of the Harrier phase, not a follow-up.
- Extend the identity into the embedding-cache bucket key (a GGUF swapped at the same path must not read the old file's cached vectors).
- Regression lock: a test that writes vectors with embedder A, opens with embedder B at equal width, and asserts a hard error.

**Warning signs:**
Search quality drops immediately after a model/config change with no error; bench numbers move without a re-index; `sif status` shows embeddings present but vector results look random; cache hit rate stays high across a model swap (it should not).

**Phase to address:**
**Harrier evaluation phase — first plan (identity marker), before any A/B arm runs.** Also consumed by `sif models pull/status` (Distribution phase) which should display the resolved identity.

---

### Pitfall 2: Query-side instruction asymmetry — the Embedder protocol has no query/document role, and the cache has no prompt dimension

**What goes wrong:**
Harrier's card is explicit: queries **must** carry an instruction (`model.encode(queries, prompt_name="web_search_query")`), documents get **none**, and omitting the query instruction causes "a performance degradation". Qwen3's card quantifies the same asymmetry: 1–5% retrieval drop without the query-side instruct. SIF cannot express this today: the `Embedder` protocol is `embed(text)` / `embed_batch(texts)` / `dimension` (`src/sif/core/models.py:318-332`), and `SentenceTransformerEmbedder.embed` calls `self.model.encode(text, normalize_embeddings=True)` with no prompt/prompt_name kwarg (`src/sif/embedding/embedder.py:99-127`). Both the query path (`hybrid.py:65`) and the document path (`embed_cmd`) call the same role-less API. Two failure modes follow: (a) Harrier is evaluated/served without its mandatory query instruction → the A/B measures a crippled model and the gate verdict is invalid; (b) once instructions are added, `EmbeddingCache` keys on `(content_hash, model_id)` only (`cache.py:69-77`, `manager.py:153-163`) — the same text embedded as a query (with instruction) and as a document (without) collides in one bucket, so whichever runs first poisons the other.

**Why it happens:**
The protocol was designed for symmetric embedders (MiniLM-era). Instruction-tuned last-token models broke that assumption, and the cache key predates prompts. localGPT's eval records a missing-prefix audit and a prefix-induced semantic-cache cosine shift (mean pairwise 0.361 → 0.216) — the cache-contamination vector is real and measured.

**How to avoid:**
- Extend the embed surface with an explicit role: `embed_query(text)` vs `embed_document(text)` (or a `prompt_name` parameter threaded through `EmbeddingManager`), defaulting to today's behavior for Qwen3 so existing output stays byte-identical until the gate passes.
- Include the role/instruction identity in the cache bucket key (e.g. `…:query@web_search_query`), or bypass the cache for query embeddings.
- Regression locks: (1) identical text yields different query vs document vectors under Harrier; (2) cache round-trip never returns a document vector for a query lookup; (3) Qwen3 default path unchanged (SC1-style byte comparison).
- Note the GGUF path: `LlamaCppEmbedder` has no prompt handling either — a Harrier GGUF query without the instruction template is equally crippled.

**Warning signs:**
Harrier A/B shows no gain or a loss vs Qwen3 (suspect the missing prefix before blaming the model); vector search returns near-duplicate scores for everything; cache stats show one bucket serving both `sif embed` and search queries.

**Phase to address:**
**Harrier evaluation phase** (role-aware API + cache key, with the identity marker of Pitfall 1). The MCP lazy-embedder plan must use the same role-aware surface.

---

### Pitfall 3: GGUF pooling mismatch — SIF mean-pools token-level payloads, silently degrading last-token models

**What goes wrong:**
Both Harrier and Qwen3-Embedding are **last-token pooling** models (official cards). `LlamaCppEmbedder._unwrap_embedding` reduces a token-level `(T, D)` payload by **mean-pooling** (`src/sif/embedding/embedder.py:241-254`). If a GGUF conversion lacks the correct pooling metadata, llama.cpp returns per-token vectors and SIF happily mean-pools them — producing plausible-looking 1024-dim vectors that are *not* the model's intended representation. The dimension guard passes, the cache stores them, and search quietly underperforms. `embedding=True` is already set correctly (`embedder.py:181`); the pooling mode is the unguarded half.

**Why it happens:**
The mean-pool fallback was written for decoder-only GGUFs with pooling NONE (the docstring names Qwen2.5-0.5B-Instruct). It cannot distinguish "model intends mean pooling" from "conversion lost the pooling metadata". Neither official model card ships GGUF guidance (verified absent on both cards), and the ggml-org Qwen3-Embedding GGUF repo returned HTTP 401 during this research — so community conversions are the likely source, and their pooling metadata is unverified.

**How to avoid:**
- Treat GGUF provenance as part of embedder identity (Pitfall 1): record the file hash; prefer publisher-official GGUFs; document the approved source in `sif models pull`.
- Add a load-time pooling sanity probe for GGUF embedders: embed a fixed reference text and compare cosine against a sentence-transformers reference embedding of the same model (a one-time, cached check). A mean-pooled last-token model diverges sharply.
- Never "fix" a bad GGUF by changing SIF's pooling globally — the unwrap logic is correct for genuinely mean-pooling models; the fix is per-model metadata/validation.

**Warning signs:**
GGUF backend scores systematically below the ST backend for the same model name; embedding norms look fine but nearest neighbors are topical mush; the same GGUF works in llama.cpp's `llama-embedding --pooling last` but not through SIF.

**Phase to address:**
**Harrier evaluation phase** (GGUF arm validation) and **Distribution phase** (`sif models pull` provenance + status backend/pooling display).

---

### Pitfall 4: Personal known-item queries reuse source wording — lexical bias inflates BM25 and compresses the hybrid delta

**What goes wrong:**
`sif eval --personal` generates known-item queries from the user's own notes. LLM/template-generated queries systematically reuse the source document's wording, making them lexically easier than real queries. Verified evidence: the TU Delft thesis (van Wolfswinkel, 2026-10-01) measures Kendall τ 0.48–0.88 between synthetic-query and real-query system rankings (source-only labels), rising to 0.69–1.00 after pooled LLM relabeling; higher source-overlap → lower sparse-retrieval ranking agreement; NFCorpus synthetic nDCG@10 0.92 vs 0.32 real. SIF's existing synthetic fixture already shows the pattern by construction (keyword docs "own a unique exact codename"; multilingual queries use "exact contiguous runs … respecting the FTS porter tokenizer" — `tests/fixtures/bench/README.md`). A personal bench built the same way will report BM25 near-ceiling, make the vector leg look useless, and mis-rank any tuning decision (chunk sweep, weights, DYM) that trades lexical for semantic performance.

**Why it happens:**
Known-item generation is cheap and label-free (the generator knows the source doc — that part is good), but the query text is drawn from the very tokens the lexical leg indexes. The instrument then measures "can BM25 find the words it was given" instead of "can the engine find the note the user means".

**How to avoid:**
- Generate **paraphrased** queries with an explicit content-word-overlap budget (localGPT's `paraphrases.jsonl` targets ~0.21 overlap) and keep a separate exact-term known-item category (title/filename/codename lookup) — both are legitimate, but they must be reported as distinct categories, never averaged into one number that drives defaults.
- Report **BM25-only, vector-only, and hybrid** columns per category (the v1.1 bench already has the leg structure; extend it). A hybrid delta computed on lexically-biased queries is not evidence about the vector leg.
- Ground truth from document identity (the generator's source doc), never from the engine's current top-k (v1.1 Pitfall 8 leakage rule still binds).
- Keep the committed-snapshot + 0.01 tie-rule discipline (`benchmark.py:33` EPSILON, `heldout_defaults.json`): personal-bench results inform, but defaults move only under the locked held-out gate.

**Warning signs:**
BM25-only nDCG ≈ hybrid nDCG on the personal set; every generated query contains a distinctive phrase from its source doc; tuning "improvements" that vanish when queries are paraphrased; category averages hiding a keyword-ceiling/semantic-floor split.

**Phase to address:**
**Personal bench phase** (instrument design — before Harrier and chunk-sweep phases consume it).

---

### Pitfall 5: CJK evaluation confound — porter makes Chinese sentences single tokens, so ZH gains are vector-leg gains by construction

**What goes wrong:**
Verified empirically on this machine (SQLite 3.51.0, `tokenize='porter'`): the sentence `如何配置混合搜索引擎的权重` becomes **one** vocab term; `MATCH '配置'` and `MATCH '搜索权重'` return **0 hits**. FTS5's unicode61 base treats a contiguous CJK run as one token; porter stemming does not segment it. Consequences for v1.2: (a) any ZH held-out query that is not an exact contiguous run present in a document scores ~0 on the BM25 leg — Harrier's ZH win will be a **vector-leg** win, and attributing it to lexical changes (title FTS, DYM, chunking) is invalid; (b) vocab-based DYM is fundamentally limited for Chinese regardless of library — the "words" are whole sentences, so edit-distance correction is meaningless (rapidfuzz does not fix this; the locked spellfix1-skip rationale already notes zero Chinese benefit); (c) the personal bench's ZH slice must be constructed deliberately or it measures nothing lexical.

**Why it happens:**
The tokenizer choice is invisible until you query CJK substrings. The existing fixture works around it explicitly (exact Chinese runs), which can mislead planners into thinking ZH lexical search "works".

**How to avoid:**
- In the Harrier gate and personal bench: report **per-language × per-leg** metrics. Construct ZH lexical queries as exact contiguous runs (the fixture convention) and ZH semantic queries as paraphrases; state in the report that ZH lexical recall is bounded by the tokenizer, not the embedder.
- Do not promise CJK improvements from title-FTS or DYM work; scope those claims to EN.
- If CJK lexical search ever becomes a goal, that is a tokenizer change (out of v1.2 scope) — flag it as a future milestone, not a tuning knob.

**Warning signs:**
ZH BM25-only metrics at or near zero while hybrid looks healthy; DYM suggestions for Chinese that are whole-sentence swaps; a "ZH win" headline that disappears when the vector leg is ablated.

**Phase to address:**
**Personal bench phase** (slice design) and **Harrier evaluation phase** (per-language reporting in the gate verdict).

---

### Pitfall 6: Moving defaults on personal-N noise — one query is ~0.014 nDCG, and the tie rule is 0.01

**What goes wrong:**
At personal-bench scale (tens of queries), a single query flip moves nDCG@10 by ~0.014 (localGPT's measured noise floor on 72 queries) — larger than SIF's entire 0.01 held-out tie rule. The v1.1 gate worked because it was honest about this (defaults unchanged); v1.2 raises the stakes with three decision points (Harrier switch, chunk sweep, bge option) that all want to move defaults. Add judge bias: pooled LLM relabeling improves ranking agreement (τ 0.69–1.00 in the TU Delft work) but labels produced by the engine under test are circular, and LLM judges have their own verbosity/position biases. Click/usage metrics are worse at this N: CIKM 2008 (Radlinski/Kurup/Joachims) found **none of 8 absolute usage metrics** reliably reflected quality at realistic sample sizes, while interleaving detected relative differences; IJCAI 2018 (Bendersky et al.) documents personal-search feedback as sparse and biased. SIF's `query_log` is CLI-only (MCP never writes it — `backend.py:204`), capped at 500 rows, and already consumed by history suggestions — it is not an evaluation oracle.

**Why it happens:**
A new instrument produces numbers; numbers invite decisions; small-N numbers look precise (four decimal places in `heldout_defaults.json`) but carry ±1-query noise. The culture fix (held-out + tie rule + committed snapshot) exists precisely because v1.1 hit this.

**How to avoid:**
- Every quality decision reports **paired per-query deltas and counts** (helped N / hurt M / unchanged K), not just averaged metrics; require the win to exceed the tie rule on **both EN and ZH held-out** (locked gate) with a bootstrap or sign-test interval that excludes zero.
- Keep tuning and held-out fixtures structurally separate (existing 36/20 split); the personal bench is a *third* instrument — its results never overwrite the committed held-out snapshot without the full gate.
- If implicit feedback is ever used, use paired/interleaved comparisons (team-draft), never absolute CTR/abandonment dashboards; treat `query_log` as suggestion fuel only.
- Record rejections with numbers (localGPT's eval/decisions culture: the 0.6B reranker rejection page is "among the most valuable").

**Warning signs:**
A default change justified by a 0.005–0.015 metric delta; no per-query delta table; "the personal bench says it's better" without a held-out run; quality claims sourced from click counts.

**Phase to address:**
**Personal bench phase** (statistics design), enforced by **Harrier** and **Tuning** phase gates.

---

### Pitfall 7: bge-reranker-v2-m3 as a "free upgrade" — it hurt a strong first stage, and SIF's threshold/truncation assumptions don't transfer

**What goes wrong:**
Three verified traps stack. (1) **Quality direction is not guaranteed:** localGPT measured bge-reranker-v2-m3 **hurting** a strong Harrier first stage (−0.022 mixed / −0.058 docs nDCG@10 at +1.6 s/query); its famous gains were "a repair job on a weak first stage". Qwen3-Reranker-4B helped (+0.062/+0.173) but at +12.7 s and 7.5 GB — unusable as a laptop default; Qwen3-Reranker-0.6B was rejected (noise-band gain, 1.5–2.8× latency). SIF's first stage is exactly the "strong" regime where bge can subtract value. (2) **Score-scale mismatch:** SIF's relative threshold α=0.5 (`settings.py:176-182`) was tuned on Qwen3 yes/no softmax probabilities; bge via `CrossEncoderReranker` is sigmoid-normalized raw logits (`rerank.py:267-272`) — a different distribution, so α silently filters different fractions. (3) **Truncation mismatch:** `CrossEncoderReranker` hardcodes `max_length=512` (`rerank.py:237,239`) while bge-m3 supports long inputs — long chunks get silently truncated, changing what is scored. Bonus trap from localGPT: libraries that route Qwen3 rerankers through `Qwen3ForSequenceClassification` build a **randomly initialized score head**; SIF's `Qwen3Reranker` correctly uses yes/no logits (`rerank.py:409-418`) — keep that scheme, and note `create_reranker`'s name-based auto-detection (`rerank.py:438-446`) overrides `reranker_model_type` for any "qwen3-reranker" name.

**Why it happens:**
Leaderboards and model cards report gains over weak baselines; the option looks like a config flag, but the threshold, truncation, and cache assumptions are model-specific. And if rerank caching is added (qmd #764 precedent: cache key stable across model swaps served **bit-identical stale scores** until fixed to include the resolved model), an A/B between rerankers is silently invalidated.

**How to avoid:**
- Evaluate bge as an **option** on personal + synthetic held-out with latency columns (p50/p95 per query, candidate cap 5–50 already clamped); re-tune or disable α per reranker; make `max_length` a per-model setting.
- Any rerank/expansion cache key must include the **resolved** model identity (name + type + path/revision) — SIF's `llm_cache` is keyed `(model_name, prompt_hash)` (`schema.py:134-147`); verify the expansion path passes the resolved name, and apply the same rule to any new rerank cache.
- Keep rerank opt-in (locked v1.1 decision); never ship a default reranker change on synthetic-only evidence.

**Warning signs:**
bge "improves" the synthetic keyword category but drops the personal semantic slice; α=0.5 keeps almost everything or almost nothing after the swap; A/B reranker scores are suspiciously identical (cache); query latency jumps without a candidate-count change.

**Phase to address:**
**Tuning phase** (bge option), with the cache-identity rule landed before any reranker A/B.

---

### Pitfall 8: Big-bang MCP SDK v2 migration breaks the well-tested hand-rolled stack

**What goes wrong:**
SIF's MCP layer is hand-rolled and deeply integrated: `MCPServer` state machine + 4 tools (`mcp/server.py`, `handlers.py`), line-delimited stdio with executor I/O (`transports/stdio.py`), FastAPI Streamable HTTP with Origin validation and in-memory sessions (`transports/http.py`), and the embedded watch host with load-bearing invariants (SIF_MCP_WATCH opt-in, literal `bm25` depth, logger-only callbacks, serve-first reconcile, D-14 flush→checkpoint→close teardown — `watch_host.py`). SDK v2 is a rename-and-rewrite, not a drop-in: `FastMCP`→`MCPServer` (`mcp.server.mcpserver.*`), types split into an exact-pinned `mcp-types` package with **snake_case attributes** (wire stays camelCase via `by_alias`), low-level `Server` **loses auto-wrapping of dict/list returns and jsonschema argument validation**, unexpected exceptions are **sanitized to −32603** (only `ToolError` messages reach the model), `ping` is removed from the protocol, and transport options move to `run()`. SIF's handlers return `ToolsCallResult(content=[JSON text])` and rely on pydantic `QueryInput` validation inside handlers; the protocol models use camelCase aliases with `exclude_none` dumps. A big-bang swap silently changes wire format, error text, validation behavior, and watch teardown ordering — across ~hundreds of MCP tests.

**Why it happens:**
The SDK's high-level API looks like a thin wrapper, so migration reads as "replace the server class". The behavioral deltas (auto-wrapping, validation, error sanitization, session semantics) only surface under real clients and the watch-host integration tests.

**How to avoid:**
- **Tracer-first** (project culture): migrate ONE tool (`status`) end-to-end through both transports with watch on/off, prove wire compatibility against golden JSON-RPC transcripts, then expand tool-by-tool. Keep `SearchBackend` as the stable seam — it already isolates DB/embedder logic from transport.
- Decide structuredContent policy explicitly: spec says a tool with `outputSchema` **MUST** return conforming `structuredContent` and **SHOULD** also return the serialized JSON in a TextContent block for backwards compatibility. SIF's current JSON-in-text is the compat half; add structuredContent alongside, not instead.
- Preserve input validation (pydantic models in handlers) since SDK low-level validation is gone; map user-facing errors to `ToolError` deliberately (sanitization will otherwise hide them).
- Re-lock the watch-host invariants as regression tests around the new lifespan integration (the `mcp_watch_lifespan` factory shape exists precisely because FastAPI lifespan wiring was a past CR).
- Dependency floors move: pydantic>=2.12, anyio>=4.9, sse-starlette>=3.0, httpx2, opentelemetry-api (migration guide). Resolve the full tree on **Python 3.10** in a scratch venv first; SIF pins pydantic>=2.0.0 and fastapi>=0.100 today.

**Warning signs:**
MCP tests pass but a real client shows different result shapes; error messages become "Error executing tool …"; watch teardown leaves `-wal` growing or checkpoint warnings; `tools/list` schemas lose fields (snake_case dump without `by_alias`).

**Phase to address:**
**MCP SDK phase — plan 1 is the tracer + dependency resolution + golden wire locks**, before annotations/parity/lex-vec expansion.

---

### Pitfall 9: Dual-era protocol gap — SDK v2 documents 2025-11-25 + 2026-07-28; 2025-06-18 clients are unconfirmed

**What goes wrong:**
The milestone targets "dual-era (2025/2026) client service". Verified: SDK v2 speaks **2026-07-28** (modern, no `initialize` handshake — per-request `_meta` + `server/discover`, no `Mcp-Session-Id`, no server→client back-channel) and **2025-11-25** (handshake era, sessions retained). The official whats-new/migration docs **never mention 2025-06-18** — the revision many current clients (including Claude Code-era tooling) still speak. SIF today hardcodes `protocolVersion="2024-11-05"` with **no negotiation** (`server.py:68-74` ignores the client's requested version). Migrating to SDK v2 without verifying the client matrix can silently drop the exact clients the milestone exists to serve; conversely, testing only with the SDK's own `Client` (which negotiates 2026 by default) proves nothing about 2025-era compatibility.

**Why it happens:**
"v2 supports old clients" is true for the 2025-11-25 era and gets generalized to all 2025 revisions. The 2026 era's structural changes (no handshake, no sessions, `subscriptions/listen` replacing the GET stream) also break assumptions baked into SIF's HTTP transport (ping-only SSE GET, session OrderedDict).

**How to avoid:**
- Before choosing the SDK version, build an explicit **client matrix** (Claude Code current, other 2025-06-18 clients, 2025-11-25 clients, 2026-era SDK client) and test each against the tracer server. If 2025-06-18 support is required and unconfirmed in v2, either keep a v1 compat path (`mcp>=1.28,<2` maintenance pin) or implement negotiation explicitly.
- Implement real version negotiation (respond with the requested supported version, else the server's latest) — the current hardcoded response is already a latent bug for any modern client.
- Lock per-era wire transcripts as golden tests; test the watch host under both eras' session semantics.

**Warning signs:**
A real client fails at initialize or gets "unsupported protocol version"; SDK-client tests green while Claude Code cannot list tools; session-id assumptions break under 2026 clients (there is no session).

**Phase to address:**
**MCP SDK phase — client matrix is a plan-1 deliverable**, gating the SDK version choice.

---

### Pitfall 10: stdout pollution under the SDK + lazy embedder — model loading inside the MCP process

**What goes wrong:**
stdio MCP's stdout is the JSON-RPC channel; one stray byte corrupts the stream. SIF guards this today by convention (watch host renders through stderr loggers only — `watch_host.py:64-89`). The lazy-embedder feature moves model loading from `SearchBackend.__init__` (eager, `backend.py:91-109`) to first query — inside the serving process, under the SDK's anyio runtime. Model loading is noisy: sentence-transformers shows a progress bar for batches >100 (`embedder.py:123`), HF/ModelScope downloads print progress, torch emits warnings. SIF's suppression (`is_quiet()`/`suppress_output()`, `utils/logging.py`) only activates at `log_level=WARNING` — the MCP entrypoints do not force quiet. `RichProgressTracker` defaults to a **stdout** console (`utils/progress.py:49`). qmd #776 is the direct upstream precedent: download progress bars flooded Claude Code transcripts ("wasting a lot of tokens"), fixed hidden-by-default.

**Why it happens:**
The hand-rolled transport made stdout purity a visible, tested concern; an SDK migration plus lazy loading reopens it in new code paths (SDK internals, anyio workers, first-query model init) where the old conventions aren't automatically inherited.

**How to avoid:**
- Force quiet at MCP entrypoints **before any model import**: `set_quiet(True)` + `TQDM_DISABLE=1` + `HF_HUB_DISABLE_PROGRESS_BARS=1` + `TRANSFORMERS_VERBOSITY=error` (the `_apply_quiet_mode` recipe already exists).
- Belt-and-suspenders: redirect process stdout to stderr at the stdio transport boundary, writing protocol frames to the saved real stdout (SDK stdio servers do this; verify v2's behavior rather than assuming).
- Regression lock: a cold-first-query test that captures every stdout byte and asserts each line parses as JSON-RPC — with the embedder loading lazily mid-session.
- Apply the same rule to `sif models pull/status`: progress hidden by default when `not stdout.isatty()`, `--progress` opt-in, `--json` machine-readable (qmd #776 resolution).

**Warning signs:**
Client reports "parse error" on first query; transcript contains ANSI escape sequences or `Downloading…` lines; MCP works in tests (mocked embedder) but fails with a real model.

**Phase to address:**
**MCP SDK phase** (lazy embedder plan) and **Distribution phase** (models UX non-TTY silence).

---

### Pitfall 11: Annotation dishonesty — readOnlyHint is an auto-approval trigger, and SIF's query description already overclaims

**What goes wrong:**
The spec is normative: clients **MUST consider tool annotations untrusted** unless from trusted servers — because hosts auto-approve on them. Real incidents: GHSA-PQH8-P93P-2RX7 (Dynatrace MCP: DQL injection in tools annotated `readOnlyHint: true`, auto-approved by clients); a generated SQLite MCP tool that claimed readOnly while opening read-write (`?mode=ro` silently dropped without the `file:` URI prefix), with `VACUUM INTO`/`ATTACH DATABASE` blocklist gaps enabling exfiltration **with no permission prompt** in Claude Code/Cursor. SIF's v1.2 adds annotations *and* write tools (index/vacuum) *and* a vacuum feature — the exact combination that incident exploited. Separately, SIF's `query` tool description already claims "and reranking" while the backend never reranks (`handlers.py:48-52` vs `backend.py:162-181`) — description honesty is broken today and the parity work must fix it, not cement it.

**Why it happens:**
Annotations read as metadata polish ("mark the read tools read-only"), but they are a security-relevant contract with the host's approval UI. Overclaiming is incentivized: readOnly tools get frictionless auto-approval, so there is pressure to mark borderline tools readOnly.

**How to avoid:**
- Annotate by **actual behavior**: `query/get/multi_get/status/metadata/lex/vec` → `readOnlyHint: true`; `index update/embed` → `readOnlyHint: false`, `idempotentHint: true` (checksum-skip makes re-runs no-ops); `vacuum`/`collection remove` → `destructiveHint: true`. Never mark a tool readOnly that can write, even "harmlessly".
- Keep SIF's own safety independent of annotations: Host/Origin validation, input validation, and the flock remain the real guards (annotations are hints to clients, not a security layer for the server).
- Fix the query description during parity work (describe what the pipeline actually does); add a test asserting description/annotation claims match backend behavior.
- The vacuum tool specifically: the SQLite incident's exfil vectors were `VACUUM INTO` and `ATTACH` — SIF's vacuum must not accept arbitrary target paths from tool arguments without validation (write only inside the user data dir, or require CLI-only vacuum).

**Warning signs:**
A write-capable tool carries `readOnlyHint: true`; descriptions promise features the backend lacks; vacuum accepts a caller-supplied destination path; annotation values copied from a template without per-tool review.

**Phase to address:**
**MCP SDK phase** (annotations plan) with the vacuum-path rule co-owned by the **Scale phase**.

---

### Pitfall 12: Dedup ordering vs fusion — moving dedup changes default output, and the vector-only path has no dedup at all

**What goes wrong:**
Verified current behavior: `HybridSearcher.search` fuses with `options.limit` truncation **then** dedups by document_id (`hybrid.py:77-99`, `_deduplicate_results:101-119`). When one document owns several chunk slots in the fused top-limit, dedup shrinks the page **below limit** (ask for 10, get 6). Worse, the single-leg early returns (`hybrid.py:69-72`) skip dedup entirely — a vector-only result list can contain the same document many times (vector search is chunk-level, `vector.py:87-131`). The v1.2 "per-doc vector dedup" fix must move dedup **before** fusion/truncation — which changes RRF input composition (each document contributes one rank instead of several), shifting every fused score. That violates the project's byte-identical-defaults culture (QUAL-01 SC1) unless handled as a deliberate, evidenced contract change.

**Why it happens:**
Dedup-after-truncation is the naive composition order; it "works" until a chunky document dominates a query. The fix looks like a one-line move, but RRF is rank-sensitive: removing duplicate ranks renumbers everything below.

**How to avoid:**
- Decide the contract explicitly: dedup per leg **before** fusion (vector leg collapses chunks to best-scoring doc; BM25 leg is already doc-level), over-fetch so the fused page still yields `limit` documents, then truncate. Apply the same dedup to the vector-only and BM25-only exit paths.
- Treat the output change as a **recorded contract change**: update golden tests with rationale, run the synthetic bench before/after (defaults may legitimately move *results* while keeping *weights* unchanged — document the distinction), and note it in the milestone ledger.
- Regression locks: chunky-document fixture returns exactly `limit` distinct docs; vector-only path returns distinct docs; page-2 continuity (with Pitfall 15).

**Warning signs:**
`--limit 10` returns 6 results on note-heavy queries; vector-only search shows the same file 4 times; golden tests "fixed" by relaxing assertions instead of recording the contract change.

**Phase to address:**
**Correctness phase** (dedup plan), before MCP parity mirrors the pipeline.

---

### Pitfall 13: Pre-RRF metadata filtering on the vector leg — vec0 resolves KNN before the JOIN, so filters silently under-return

**What goes wrong:**
The filter AST must apply **pre-RRF** (locked design). On the BM25 leg this is straightforward (the materialized-CTE pattern already exists for collection filters, `bm25.py:76-93`). On the vector leg it is a trap: sqlite-vec resolves the KNN MATCH **before** the JOIN applies any document filter — SIF already documents this for collection filters and over-fetches `fetch_k = max(limit*4, 50)` (`vector.py:70-86`, WR-04). A selective metadata filter (`tag=x` matching 2% of docs) needs far more than 4× surplus: the KNN top-50 may contain **zero** matching documents, and the query returns empty while matching documents exist. Post-RRF filtering is the other wrong answer: it shrinks pages, breaks rank continuity, and wastes the candidate budget.

**Why it happens:**
"Add a WHERE clause" is the reflex; vec0's execution order makes WHERE-after-KNN a recall bug, not a filter. The existing 4× heuristic was sized for coarse collection filters and reads as "already handled".

**How to avoid:**
- Compile the filter AST to SQL predicates applied **inside each leg** before fusion. For the vector leg, choose between (a) adaptive over-fetch with a bounded escalation (grow k until limit matches or a ceiling), or (b) pre-filtering the candidate document set and scoring within it (requires a non-vec0 path or metadata-column strategy — measure before choosing; ANN is locked out, brute force is fine at 100k).
- Extend the exclude-all sentinel contract: an empty filter match set returns zero results, never "no filter" (`vector.py:43-49`, `bm25.py:48-56` pattern).
- Property tests: filtered-hybrid ⊆ unfiltered-hybrid ∩ filter-set; selective-filter recall fixture (2% match rate) returns the right docs; filter + collection + pagination compose.
- Discovery tool (`metadata`) must read the same stored metadata the filters use — including its staleness (Pitfall 14).

**Warning signs:**
`tag:x` returns nothing while `sif ls` shows tagged docs; filtered vector search recall collapses as the filter gets more selective; results differ between CLI and MCP for the same filter.

**Phase to address:**
**Metadata filtering phase** (AST + both-leg application), with the vector-leg strategy measured in plan 1.

---

### Pitfall 14: Frontmatter-only edits are invisible — metadata filters will serve stale tags by construction

**What goes wrong:**
This is the most SIF-specific trap in the milestone. The checksum convention covers the **body only** (`parser.py:66-71`; `Document.__post_init__` hashes content, `core/models.py:146-150`). `IncrementalIndexer._process_file` skips re-index when the checksum matches and converges **mtime only** — the comment is explicit: "the checksum covers the body alone, so a whole-row update could smuggle a new frontmatter title/metadata through this skip" (`incremental.py:302-318`). Therefore: user edits only the tags/frontmatter → drift detection fires (mtime moved) → checksum matches → **metadata column never updates**. v1.2's tag/frontmatter filters and the metadata discovery tool will confidently serve stale values, and no amount of filter-AST correctness fixes it. Related: `documents.file_size` is never refreshed on update (`drift.py:18-23` docstring) — a size-based filter would read creation-time sizes forever.

**Why it happens:**
The body-only convention was a deliberate v1.0 fix (whole-file hash mismatch caused perpetual re-index). It predates metadata filtering; the skip path's mtime-only convergence is correct for content but silently wrong for metadata-as-a-feature.

**How to avoid:**
- Make change detection metadata-aware: store a frontmatter/metadata hash alongside the body checksum (or hash body+frontmatter with a convention version), and re-index when either changes. This is a **checksum convention change** — pair it with a one-time forced re-index migration for existing collections (the CR-01 gated-rebuild pattern is the template).
- Keep the skip path's guarantee: a truly unchanged file still costs one stat + hash, no writes.
- If size filters ship, refresh `file_size` on update (and backfill in the same migration).
- Regression locks: tag-only edit → filter sees the new tag without a body change; body-only edit → metadata preserved; unchanged file → zero writes (mtime convergence still works).

**Warning signs:**
"I added a tag and the filter doesn't find it"; metadata discovery shows old frontmatter; `index update` reports "unchanged" for a file whose tags changed; filter tests pass on fresh indexes but fail on upgraded ones.

**Phase to address:**
**Metadata filtering phase — precondition plan** (or Correctness phase if parser wiring lands first; the two convention changes should share one migration).

---

### Pitfall 15: Pagination is broken at three different points — fixing one leaves the others

**What goes wrong:**
Verified: (1) BM25 applies `LIMIT ? OFFSET ?` in SQL (`bm25.py:92,110-112`) but filters `min_score` **after** pagination (`bm25.py:119-122`) — pages develop holes; (2) vector search **ignores offset** entirely (trims to limit, `vector.py:127`); (3) hybrid fuses a offset-shifted BM25 page with an unshifted vector page — page 2 is a meaningless mix; (4) `SearchPipeline` over-fetches `max(limit+offset, candidate_limit)` when reranking (`hybrid.py:235-241`) but **never slices the offset** — results always start at rank 1; (5) the CLI exposes no offset flag at all (grep: zero hits in `cli/commands/search.py`), and MCP `QueryInput` has no offset field. "Pagination fixes" that only add an MCP offset field will paginate the broken hybrid semantics.

**Why it happens:**
Offset was implemented per-leg as each searcher was written; fusion and the pipeline never reconciled them. The rerank over-fetch even *looks* like offset support.

**How to avoid:**
- One offset application point: each leg fetches `limit+offset` (no per-leg OFFSET), fusion+dedup run on the full candidate set, then a single `[offset:offset+limit]` slice after rerank/snippets. Ranks stay contiguous across pages (`offset+rank`).
- Apply `min_score` before pagination (or document it as a post-filter with the hole behavior — but prefer before).
- Expose offset identically in CLI and MCP (shared `SearchOptions` already carries it); golden tests for page-1/page-2 continuity, offset+rerank, offset+filter composition.
- Keep the no-offset default byte-identical (SC1): offset=0 must reproduce today's output exactly after the dedup contract change is accounted for.

**Warning signs:**
Page 2 repeats page-1 documents; `--limit 5` page 2 returns 3 rows; MCP offset accepted but ignored; rerank+offset returns the top of the list.

**Phase to address:**
**Correctness phase** (offset plan), surfaced through **Metadata phase** CLI/MCP UX.

---

### Pitfall 16: Title FTS migration — CREATE VIRTUAL TABLE IF NOT EXISTS never adds a column, and the misconfiguration gate won't fire

**What goes wrong:**
`documents_fts` indexes **content only** (`schema.py:244-251`). Adding title search requires a new FTS column — but `CREATE VIRTUAL TABLE IF NOT EXISTS` is a no-op on the existing table, and the existing migration gate `_fts_is_misconfigured` only checks the `content='documents'` setting (`schema.py:221-231`), so it will **not** detect the missing title column. Every existing database silently keeps the old single-column schema; title queries match nothing; triggers (which insert only `content`, `schema.py:274-324`) keep syncing one column. FTS5 external-content tables cannot ALTER — the table must be dropped, recreated with both columns, reseeded, and all six triggers rewritten to carry `(rowid, content, title)` in insert/update/delete forms.

**Why it happens:**
The schema manager's idempotent DDL pattern works for tables/columns but not for FTS5 column sets; the one existing FTS migration gate was written for a different defect (content= misconfiguration) and reads as "FTS migration already handled".

**How to avoid:**
- Add a dedicated detection gate (parse the stored FTS SQL for the column list, the `_fts_trigger_is_legacy` pattern at `schema.py:172-216` is the template) → drop/recreate/reseed in one transaction, rewrite triggers, gate the rebuild so fresh/migrated DBs pay nothing (CR-01 culture).
- Trigger sync tests for both columns: insert/update/delete on documents must keep FTS consistent (the legacy direct-UPDATE/DELETE forms corrupt or orphan — the docstring at `schema.py:172-182` documents both failure modes).
- Title changes ranking: decide column weights (bm25 title boost) deliberately and bench before/after; porter stems titles too; CJK titles remain single-run tokens (Pitfall 5).
- The vocab shadow `documents_fts_v` and DYM ride the same FTS table — verify suggestions still work post-rebuild.

**Warning signs:**
Title search works on fresh test DBs but not on upgraded ones; `sqlite_master` shows the old single-column FTS SQL; orphaned FTS entries after document updates (MATCH returns deleted content); suggestion vocabulary empties after migration.

**Phase to address:**
**Correctness phase** (title FTS plan), with the migration gate as its first task.

---

### Pitfall 17: Parser dispatch wiring changes the checksum convention for non-Markdown files — one forced reindex, plus a latent YAML bug

**What goes wrong:**
`IncrementalIndexer` hardcodes `MarkdownParser()` for **every** file (`incremental.py:30,77`); `create_parser` exists but is unwired (`parser.py:185-203`). Wiring it is a v1.2 correctness fix, but it changes stored data for non-md files: TextParser/CodeParser hash **full content** while MarkdownParser hashes the **frontmatter-stripped body** (`parser.py:71,106,173`), and titles change (CodeParser extracts module docstrings). Existing non-md documents therefore mismatch on the next update → re-index churn unless migrated deliberately. Latent bug the wiring fixes: a `.yaml`/`.json` file starting with `---` is currently parsed by `frontmatter.loads` as **all frontmatter, empty body** — such files are indexed as empty documents today. Also: collections whose pattern includes non-md files have been storing MarkdownParser titles (`file_path.stem` or first H1) — discovery/metadata features will surface the inconsistency.

**Why it happens:**
The single-parser shortcut was fine for `**/*.md` defaults; multi-format collections expose it. The checksum convention is implicit (no version marker), so a parser change silently redefines "changed".

**How to avoid:**
- Wire `create_parser` and the checksum-convention change in **one plan** with a one-time forced reindex of affected (non-md) documents — share the migration with Pitfall 14's metadata-hash change so users pay one rebuild, not two.
- Per-parser regression fixtures: YAML starting `---` (body must be the whole file), Python docstring title, `.txt` first-line title, `.md` frontmatter stripped (unchanged convention).
- Keep the md path byte-identical (it is the default and the bench corpus).
- Record the convention version in the DB so future parser changes can gate migrations instead of churning.

**Warning signs:**
`index update` re-indexes every `.py`/`.txt` file once after upgrade (expected if migrated, a bug if not); YAML documents searchable as empty; title metadata inconsistent across formats; drift refresh loops on non-md files.

**Phase to address:**
**Correctness phase** (parser plan), migration coordinated with **Metadata phase** precondition.

---

### Pitfall 18: Per-query scan elimination that breaks derived staleness or reintroduces the verbatim-context bug

**What goes wrong:**
Two scans are targeted, and both exist for documented reasons. (1) **Staleness** is derived: one full scan of `document_embeddings` per result set (`staleness.py:34-77`), invoked from every searcher's `_attach_contexts` — a hybrid query runs it **three times** (BM25 leg + vector leg + hybrid exit), and the pipeline adds a fourth. The naive "optimization" is a stored `vectors_stale` column — exactly the silent-lie bug class the project banished (4+ write paths must keep a flag truthful; the module docstring says so). (2) **Contexts** attachment scans *all* path contexts per query with two-sided `normalize_path` matching (`context_attach.py:53-61`) — deliberately no SQL pre-filter, because `contexts.target_id` stores verbatim user-typed paths while `documents.path` is resolved, and realpath is not invertible: a SQL pre-filter on resolved paths returns **zero** legacy rows (the 05-VERIFICATION gap-1 root cause, documented in the module docstring). "Fixing" the scan with a WHERE clause reintroduces that bug.

**Why it happens:**
Full scans look like obvious waste; the reasons they exist live in docstrings and old verification reports, not in the SQL. Scale work that reads only the query text will "simplify" them into correctness bugs.

**How to avoid:**
- Attach **once per query** at the pipeline/searcher exit instead of per leg (keep D-09: every exit marks consistently — BM25-only, vector-only, hybrid, MCP, bench). This alone removes 2–3 scans per hybrid query with zero semantic change.
- If caching the embedded-id set: cache per connection with invalidation on any embedding write (a write-generation counter), keeping the signal **derived** — never a persisted per-document flag. Preserve the display gate (no embeddings at all → no markers) and the None-degradation (vec0 missing → unmarked, never crash).
- Contexts: keep two-sided normalization; optionally cache the normalized map with invalidation on contexts writes; never SQL-prefilter verbatim rows. Regression: legacy verbatim context rows still attach (the `/tmp` vs `/private/tmp` fixture).
- Lock marker parity: staleness/context output byte-identical before/after on the existing fixture suite.

**Warning signs:**
Staleness markers disappear or freeze after the "optimization"; contexts stop attaching on upgraded DBs but work on fresh ones; markers differ between CLI and MCP; a stored `stale` column appears in a diff.

**Phase to address:**
**Scale phase** (scan-elimination plan), with the derived-signal invariant as an explicit acceptance criterion.

---

### Pitfall 19: VACUUM against live hosts — write locks, open transactions, and the MCP connection that never closes

**What goes wrong:**
SIF has no vacuum/backup today (grep: zero hits). SQLite semantics (official docs): VACUUM is a **write operation** — it fails if another connection holds a lock preventing writes, fails with an open transaction or unfinalized statements on the same connection, and needs up to **2× the DB size** in free disk; in WAL mode only `auto_vacuum` can be changed. SIF runs long-lived MCP connections (per-request `DatabaseConnection` in `backend.py:111-118`, plus the watch host's owned connection), a watch worker, and pre-search drift refreshes. Taking the flock is necessary but not sufficient: readers don't take the flock, and `Database.transaction()` wrappers mean a VACUUM issued inside one fails immediately. `VACUUM INTO` (backup) is safer — consistent snapshot, original untouched — but the target must not exist, and an unplanned shutdown mid-copy can leave a corrupt output file.

**Why it happens:**
VACUUM reads as a maintenance no-brainer; the locking model (and the difference between VACUUM and VACUUM INTO) is only visible in the official docs. The flock gives a false sense of exclusivity because it arbitrates *writers*, not readers.

**How to avoid:**
- `sif index vacuum`: acquire `index_lock`, ensure no open transaction on the executing connection, checkpoint WAL first, then VACUUM; surface busy failures as retryable user errors, never crash. Document the 2× disk requirement.
- Backup: prefer the **online backup API** (incremental, fewer CPU cycles, live-safe) or `VACUUM INTO` with a non the user data dir; verify the copy (open + `PRAGMA integrity_check`) before reporting success.
- Test with a concurrent MCP search loop and a running watch host: vacuum must either succeed cleanly or fail retryably — never corrupt, never deadlock the watch worker.
- MCP exposure: if vacuum becomes a tool, it is `destructiveHint: true` and path-restricted (Pitfall 11 — `VACUUM INTO` was an exfil vector in the SQLite incident).

**Warning signs:**
"database is locked" from vacuum while MCP serves; "cannot vacuum from within a transaction"; `-wal` unchanged after vacuum; backup file exists but fails integrity_check; disk-full failures on large DBs.

**Phase to address:**
**Scale phase** (vacuum/backup plan), with the MCP-exposure rule co-owned by **MCP SDK phase**.

---

### Pitfall 20: Streaming embed batches that break the per-collection transaction contract

**What goes wrong:**
`embed_cmd` today accumulates **all chunks of a collection in memory** and embeds them **inside one write transaction** (`index.py:317-359`), with deliberate contracts: one transaction per collection (CR-02 — a failed collection rolls back only itself), failure report raised outside transactions, counts after commit, delete-before-insert idempotency (G-03-3), and the completeness skip via one batched `get_all_embedded_chunk_ids()` scan. Streaming batches fix memory and lock-hold time, but moving embedding **outside** the transaction changes failure atomicity: a mid-run crash can leave half a collection's chunks committed. Re-chunking between batches can also orphan vectors if delete-before-insert is not preserved per document.

**Why it happens:**
"Stream the batches" sounds like a pure performance change; the transaction boundary is a correctness contract documented in three decision records (CR-02, G-03-3, D-05). The v1.1 research even warned "never hold a write transaction across an embed call" — the current code does, and fixing it is a semantic change, not a refactor.

**How to avoid:**
- Pipeline: chunk → embed batch (outside any transaction) → short BEGIN IMMEDIATE write per batch/document → next batch. Keep delete-before-insert and the completeness skip so a resumed run converges (checksum/chunk-id skipping makes overlap a no-op).
- Preserve CR-02 reporting: per-collection failure isolation, exit code non-zero, counts after commit. Decide and document the new failure semantics (partial progress durable + resumable is the project's established direction — D-04 per-file commits in the incremental core).
- Regression locks: mid-run failure leaves no orphan vectors and a resumable state; re-run embeds exactly the missing chunks; memory bounded by batch size (fixture with a large collection); watch host interleaves searches during embed without lock errors.

**Warning signs:**
OOM on large collections (today) or orphaned vec0 rows after a failed embed (tomorrow); `sif embed` re-embeds everything after a crash; "Already embedded" skips documents with partial chunk sets; write lock held for minutes.

**Phase to address:**
**Scale phase** (streaming plan), after the correctness phase stabilizes chunk identity.

---

### Pitfall 21: Linux pip resolves multi-GB CUDA torch by default — and torch 2.15 dropped Python 3.10

**What goes wrong:**
Verified from PyPI metadata (torch 2.15.0): the Linux x86_64 wheel is ~539 MB **and** requires `cuda-toolkit==13.2.2`, `nvidia-cudnn-cu13`, `nvidia-nccl-cu13`, `nvidia-nvshmem-cu13`, `nvidia-cusparselt-cu13`, `cuda-bindings`, and `triton` — a multi-GB CUDA stack on a machine that may have no GPU. macOS (~139 MB) and Windows (~127 MB) wheels carry none of it. `sentence-transformers` pulls torch transitively; SIF's `embed` extra has no torch pin or index guidance, so `pip install docsif[embed]` on Linux is the bloat path. Second verified trap: torch 2.15 declares `Requires-Python >=3.11` — SIF supports 3.10, so a 3.10 install resolves an **older** torch; the CI matrix must not assume one torch version across 3.10–3.13.

**Why it happens:**
PyTorch's default Linux distribution is CUDA-enabled; the CPU-only wheels live on a separate index (`download.pytorch.org/whl/cpu`) that transitive resolution never consults. The project's macOS dev experience hides the problem entirely.

**How to avoid:**
- uv-first install docs with an explicit Linux CPU path (uv index strategy / `--extra-index-url https://download.pytorch.org/whl/cpu`), and a documented CUDA opt-in for GPU users. Never add torch as a hard dependency.
- CI matrix: install CPU torch on ubuntu runners (cache it); verify the 3.10 leg resolves a working torch/transformers/sentence-transformers set and pin floors accordingly.
- `sif models status` should report the resolved torch device/backend so users can see they are on CPU (or accidentally on CUDA).

**Warning signs:**
Linux install downloads gigabytes of nvidia-* packages; CI ubuntu jobs slow/OOM on dependency install; 3.10 and 3.13 legs run different torch majors with different MPS/CPU behavior; "it works on my Mac" install reports.

**Phase to address:**
**Distribution phase** (install docs) and **CI phase** (matrix dependency strategy).

---

### Pitfall 22: llama-cpp-python wheel caching silently serves the wrong backend; GPU wheels stop at cp312

**What goes wrong:**
Verified from the official README: PyPI `llama-cpp-python` **builds from source**; prebuilt wheels live on per-backend indexes (`whl/cpu`, `whl/cu118…cu132`, `whl/metal`, `whl/rocm72`, `whl/vulkan`), and CUDA/Metal wheels support **Python 3.10–3.12 only — no cp313**. pip/uv cache wheels by version, **not by CMAKE_ARGS**: a previously cached CPU wheel silently satisfies a later Metal/CUDA request, so `n_gpu_layers>0` runs on CPU with no error (the README's upgrade guidance is `--upgrade --force-reinstall --no-cache-dir`). Windows source builds need Visual Studio or MinGW. SIF's `[all]` extra pulls `llama-cpp-python>=0.2.0` with zero backend guidance, and `n_gpu_layers` is a settings knob users will turn expecting GPU.

**Why it happens:**
The package name is identical across backends; the build configuration is invisible to the resolver. A developer who once built CPU (or installed the CPU wheel) carries that cache into every later "GPU install".

**How to avoid:**
- Install docs: per-platform exact commands (Metal wheel index for macOS GPU, CPU index for CI, source + CMAKE_ARGS recipe with the force-reinstall flags when switching backends).
- `sif models status`: probe and display the actual llama.cpp backend/offload capability; warn when `n_gpu_layers>0` but the build is CPU-only.
- CI: the 3.13 leg cannot use prebuilt GPU wheels — use CPU wheels or source; Windows smoke expects no build tools (document, don't fight it — full Windows support is locked to v2).
- Pin a tested llama-cpp-python floor in the extra; record the backend in embedder identity (Pitfall 1) since CPU vs Metal numerics can differ slightly.

**Warning signs:**
"Metal enabled" but fans silent and latency unchanged; `pip install` finishes suspiciously fast after a backend switch; cp313 install falls back to a source build and fails on a missing compiler; Windows smoke dies on `nmake`/`CMAKE_C_COMPILER`.

**Phase to address:**
**Distribution phase** (models UX + docs) and **CI phase** (matrix wheel strategy).

---

### Pitfall 23: Windows smoke tests that crash instead of degrading — and a remote box with no Python

**What goes wrong:**
Verified degradation points: `daemon.detach()` is a POSIX double-fork (`os.fork`, `utils/daemon.py:216-286`) — on Windows `os.fork` does not exist; `_service_manager()` returns systemd for **every** non-darwin platform including Windows (`cli/commands/watch.py:416-418`); `index_lock` silently disables without fcntl (warning only, `locking.py:29-34,57-63`). The locked decision is smoke-only, so the trap is not "make Windows work" but "smoke tests that assert graceful degradation": a smoke suite that only runs search/index on Windows will pass while `watch --detach` dies with AttributeError and `install-service` generates a systemd unit on Win11. The remote target (hc yoga, Win11) has **no Python installed** (Store alias stub only) — the CI phase must bootstrap uv/Python first or every smoke run fails at step zero.

**Why it happens:**
POSIX assumptions are invisible on the dev Mac; "smoke" gets scoped to the happy path; the Store python.exe alias looks like Python until it opens the Store.

**How to avoid:**
- Smoke matrix asserts: search/index/embed basic path works; `watch --detach` and `install-service` fail with **clear platform messages** (guard `os.fork`/service derivation before use); the flock-disabled warning is visible; WAL+busy_timeout still protect integrity (the documented A2 assumption).
- Bootstrap the remote with uv (`uv python install`) before any pytest; treat the Store alias as absent Python.
- Document the degradation matrix in install docs (what works / what refuses / what silently degrades on Windows) — honesty is the v1.2 deliverable, not support.

**Warning signs:**
AttributeError: module 'os' has no attribute 'fork' on Windows; a `.service` file generated on Win11; smoke green while daemon commands crash; remote runs fail with "Python was not found".

**Phase to address:**
**CI phase** (Windows smoke plan), degradation guards landed in **Distribution/MCP daemon-stub** work as applicable.

---

### Pitfall 24: PyPI publish mechanics — name, version drift, classifiers, and trusted-publisher wiring

**What goes wrong:**
The package is **docsif** (CLI `sif`) — publish under the wrong name and the install docs break. Version lives in `_version.py` (1.1.1, hatch reads it) but the retrospective flags **6 unsynced version sites** (WR-03, still open). Classifiers stop at 3.12 (`pyproject.toml:16-26`) while the CI matrix targets 3.13 — claiming 3.13 before CI proves it is a false advertisement; omitting it after CI proves it hides support. Trusted publishing (official docs) requires the exact workflow filename + owner/repo registered on PyPI, `permissions: id-token: write` (job-level recommended), and `pypa/gh-action-pypi-publish@release/v1`; a pending publisher creates the project on first publish. Runtime deps include fastapi/uvicorn as **hard** dependencies — moving them to extras during "cleanup" breaks existing MCP users on a patch release.

**Why it happens:**
First publish is a checklist of small independent facts, each easy to get subtly wrong; the version-drift debt is known but unfixed; extras cleanup feels like hygiene but is a breaking change for the MCP install path.

**How to avoid:**
- Single-source the version (hatch already does; audit and fix the other sites in the same plan), verify with a build + `twine check` + TestPyPI dry run before the real publish.
- Add the 3.13 classifier only when the CI matrix is green on 3.13; keep `requires-python >=3.10` honest against the torch/llama-cpp resolution facts (Pitfalls 21–22).
- Trusted publisher: register owner/repo/workflow/environment on PyPI, protect the `pypi` environment, publish from a tagged CI job; no long-lived tokens.
- Defer moving fastapi/uvicorn out of hard deps to a minor version with a documented migration (or keep them; the bloat is modest next to torch).

**Warning signs:**
`pip install docsif` vs `sif` confusion in docs; version strings disagree across files; publish job fails with OIDC audience errors; a patch release breaks `sif mcp` imports.

**Phase to address:**
**Distribution phase** (PyPI plan), after **CI phase** proves the matrix.

### Pitfall 25: Chunk sweep arms invalidate every vector — and the breadcrumb experiment changes both legs at once

**What goes wrong:**
The chunk size/overlap sweep re-chunks the corpus: chunk ids are fresh uuid4s and chunk text boundaries move, so **every stored embedding is invalid per arm** (the completeness skip judges live chunk-id sets against stored ones — `vector.py:208-239`, `index.py:326-337`). Arms that reuse the previous arm's vectors measure nothing. The embedding cache (content-hash keyed) *does* help — identical chunk text across arms hits cache — but the **breadcrumb experiment** (prepending title/path context to chunk text) changes the text itself: cache misses everywhere, AND the modified text flows into `chunks_fts`, so the lexical leg changes too. A breadcrumb "win" can be a BM25 win (title tokens now in chunks) masquerading as a semantic win, and `documents_fts` already indexes content while title is being added separately (Pitfall 16) — triple-counting title signal is a real risk. Mid-sweep, the index holds mixed old/new chunks; the derived staleness display gate will mark documents inconsistently.

**Why it happens:**
Sweeps feel like config flips (`SIF_CHUNK_SIZE` is a setting), but chunking is an index-time transform with vector and FTS consequences. The cache's content-hash keying makes reuse *look* safe even when boundaries moved.

**How to avoid:**
- One full re-chunk + re-embed per arm (budget the embed cost in the sweep plan); isolate arms in separate collections or DB copies so no mixed state is ever queried; hold the query set and weights fixed.
- Report per-leg deltas for the breadcrumb arm (BM25-only vs vector-only vs hybrid) so a lexical win is not attributed to semantics; check title-signal duplication against the title-FTS change before combining the two.
- Keep the sweep on the tuning split; any default change goes through the held-out gate (Pitfall 6). Record embed cost and latency per arm — a chunk-size "win" that doubles index time may not be worth it.

**Warning signs:**
Sweep arms run suspiciously fast (cache reuse across changed boundaries); breadcrumb gains vanish in the vector-only ablation; staleness markers flicker during a sweep; chunk counts differ between arms' indexes and their reports.

**Phase to address:**
**Tuning phase** (chunk sweep + breadcrumb plan), after Personal-Bench provides the instrument and Correctness stabilizes chunk identity.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Width-only embedder guard "until we swap models" | Zero schema work | Silent cross-model vector contamination the first time Harrier ships (Pitfall 1) | Never — identity marker is the locked gate precondition |
| Role-less `embed(text)` + prompt-free cache key | Protocol stays simple | Harrier evaluated crippled; query/document cache poisoning (Pitfall 2) | Never for instruction-tuned models |
| Dedup after RRF truncation | One-line composition | Short pages + duplicate vector-only results; moving it later breaks goldens twice (Pitfall 12) | Never — fix once, record the contract change |
| Stored `vectors_stale` flag to kill the scan | Fastest "optimization" | The silent-lie bug class: 4+ write paths must keep it truthful (Pitfall 18) | Never — derived signals are project culture |
| SQL pre-filter on contexts.target_id | Kills the full scan | Reintroduces 05-VERIFICATION gap-1: verbatim legacy rows never match (Pitfall 18) | Never — two-sided normalization is load-bearing |
| Big-bang SDK v2 swap | One migration PR | Wire/validation/error/teardown deltas surface under real clients, hundreds of tests churn (Pitfall 8) | Never — tracer-first per project culture |
| `readOnlyHint: true` on borderline tools | Frictionless auto-approval | Real auto-approval bypass incidents; trust collapse (Pitfall 11) | Never — annotate actual behavior |
| embed inside the collection write transaction | Atomic simplicity | Minutes-long write lock; streaming fix changes failure semantics (Pitfall 20) | Only until the Scale phase lands the batch pipeline |
| md5[:8] cache-dir check in ModelDownloader | Cheap cache lookup | Cache-hit path checks a dir snapshot_download never writes → re-downloads; wrong reranker default (an embedding model) | Never — fix in models UX plan |
| Golden-number bench asserts on personal corpus | Regression safety theater | Fixture becomes immutable spec; lexical bias enshrined (Pitfall 4) | Regression floor bands + held-out gate only |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| MCP SDK v2 types | `model_dump()` without `by_alias` after snake_case rename → camelCase wire fields lost | Dump with `by_alias=True`; lock wire transcripts (migration guide: wire format unchanged, attributes renamed) |
| MCP SDK v2 low-level Server | Assuming v1 auto-wrapping of dict/list returns and jsonschema validation | Construct `CallToolResult(content=…, structured_content=…)` explicitly; keep pydantic validation in handlers; raise `ToolError` for user-facing messages (others sanitize to −32603) |
| MCP structuredContent | Returning structuredContent *instead of* text | Spec: with outputSchema, MUST conform AND SHOULD keep serialized JSON TextContent for backwards compat |
| MCP 2026-era clients | Assuming initialize handshake / session id / ping | 2026: per-request `_meta`, `server/discover`, no session, ping removed; 2025-11-25 keeps sessions; verify 2025-06-18 clients explicitly (Pitfall 9) |
| FastAPI lifespan + SDK | Handing an already-invoked context manager; losing watch teardown order | Keep the `mcp_watch_lifespan` factory shape; re-lock D-14 flush→checkpoint→close (past CR-01) |
| sentence-transformers prompts | `encode(text)` for both queries and docs on Harrier/Qwen3 | `prompt_name="web_search_query"` (Harrier) / `"query"` (Qwen3) on queries only; documents bare (official cards) |
| llama-cpp-python backend | Same package name ⇒ same build; pip cache ignores CMAKE_ARGS | Per-backend wheel indexes; `--force-reinstall --no-cache-dir` when switching; cp312 ceiling on GPU wheels (official README) |
| torch on Linux | Default pip resolution = CUDA stack | CPU index for CI/CPU users; torch 2.15 needs py≥3.11 (PyPI metadata) |
| sqlite-vec KNN + filters | WHERE after MATCH filters the top-k, not the corpus | Over-fetch/escalate or pre-filter candidates; vec0 resolves KNN before JOIN (SIF WR-04 audit note) |
| FTS5 external content | ALTER/IF NOT EXISTS to add a column; direct UPDATE/DELETE triggers | Drop/recreate/reseed + 'delete'-command triggers; gated rebuild (CR-01 pattern) |
| SQLite VACUUM | Running inside a transaction / beside live readers | Flock + no open tx + checkpoint first; VACUUM INTO/backup API for live backup; 2× disk (sqlite.org) |
| rapidfuzz swap | Porting difflib cutoff 0.75 as-is; losing tie-break order | fuzz.ratio is normalized Indel 0–100 (different algorithm); re-measure cutoff (~75), preserve (ratio desc, term asc) and the _hits/_retrievable FTS-probe contracts |
| ModelScope/HF downloads | md5-dir cache check; ModelScope-only for HF-hosted models | Match the real download layout; add HF source with revision pin (pull.py already has `_download_from_hf`; download.py does not) |
| MCP Registry | PR a server.json into the registry repo | `mcp-publisher` CLI from the server project; GitHub OAuth/OIDC or DNS/HTTP namespace proof (official README) |
| PyPI trusted publishing | Long-lived token; workflow-level id-token | Register owner/repo/workflow/environment; job-level `id-token: write`; `pypa/gh-action-pypi-publish@release/v1` (docs.pypi.org) |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| 3–4 staleness scans + 3–4 context scans per hybrid/pipeline query | Query latency grows with embedding count, flat with result count | Attach once at pipeline exit; derived caches with write invalidation (Pitfall 18) | Every query today; compounds at 100k vectors |
| vec0 brute-force KNN per query (locked: no ANN) | 75–150 ms at 100k vectors (accepted) | Keep brute force; sqlite-vec quantization+rescore is the locked escape hatch | >100k vectors — revisit then, not now |
| Selective metadata filter + fixed 4× over-fetch | Filtered vector search returns empty | Adaptive k escalation or candidate pre-filter (Pitfall 13) | Filter selectivity < ~25% |
| Whole-collection chunk list + embed inside write tx | OOM on large collections; minutes-long write lock | Streaming batches, embed outside tx, short per-batch commits (Pitfall 20) | ~10k+ chunks per collection |
| VACUUM beside live MCP/watch | "database is locked", failed maintenance | Flock + quiesce + checkpoint; VACUUM INTO for backup (Pitfall 19) | Any concurrent host |
| DYM full-vocab difflib (~46 ms/word at 73k terms; bucket ~11 ms) | Suggestion latency grows with vocab | rapidfuzz measured swap preserving contracts; keep bucket or re-measure recall | >73k terms (measured in suggest.py docstring) |
| Reranker candidates × context on CPU | 10 s+ queries; MCP timeouts | Cap 5–50 (clamped), α per model, latency columns in every eval (Pitfall 7) | >20 candidates on CPU (v1.1 evidence) |
| Eager embedder load in MCP init | Slow server start; model loaded for BM25-only users | Lazy load on first vector query + forced quiet (Pitfall 10) | Every MCP start today |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| False `readOnlyHint` on write-capable tools | Host auto-approval bypass (GHSA-PQH8-P93P-2RX7; SQLite false-readOnly incident) | Annotate actual behavior; test write tools never carry readOnly (Pitfall 11) |
| Vacuum tool accepting caller-supplied target path | `VACUUM INTO` exfil/write-anywhere (named in the SQLite incident) | Restrict targets to the user data dir or CLI-only; destructiveHint: true |
| Host header unvalidated (Origin is validated) | DNS-rebinding against the local HTTP MCP | Use SDK v2 transport_security Host/Origin validation; keep 127.0.0.1 default (`http.py:181-191` today) |
| Filter AST string-interpolated into SQL | Injection via tag/path values | Parameterized predicates only; the AST compiles to bound parameters, never f-string values |
| Personal bench corpus committed | Private KB content leaks into the repo | Existing fixture rule binds: synthetic only in-repo; personal runs local-only (tests/fixtures/bench/README.md) |
| query_log treated as shareable telemetry | Query strings are personal data | Local-only, 500-row cap, opt-out exists; never upload; MCP already never writes it |
| Daemon stub shipped as working | Users believe a daemon runs; silent no-op | Implement with existing daemon.py machinery or remove the command; never a silent stub (Pitfall 23) |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Metadata filters serve stale frontmatter | "I tagged it and search can't find it" — trust collapse | Metadata-aware change detection + one-time migration (Pitfall 14) |
| `--limit 10` returns 6 | Looks like a bug, erodes confidence | Dedup-before-fusion + over-fetch to fill the page (Pitfall 12) |
| Progress bars in agent transcripts | Wasted tokens, unreadable tool output (qmd #776) | Non-TTY silent by default, `--progress` opt-in, `--json` status |
| Model swap silently degrades search | Users blame the engine, not the config | Identity marker fail-fast with re-embed instruction (Pitfall 1) |
| `sif models pull` re-downloads cached models | Bandwidth, time, confusion | Fix the cache-layout check; status shows resolved identity/backend/dim |
| Windows commands crash with tracebacks | "Broken on Windows" vs the honest "deferred to v2" | Graceful platform guards + degradation matrix in docs (Pitfall 23) |
| Query tool promises reranking it doesn't do | Agents plan around a false capability | Fix description during parity; annotations match behavior (Pitfall 11) |
| Default switch on a 0.01 synthetic win | Quality regressions users can't explain | Held-out EN+ZH gate, paired deltas, recorded rejections (Pitfall 6) |

## "Looks Done But Isn't" Checklist

- [ ] **Harrier gate:** Often missing the identity marker — verify a same-width cross-model open fails fast, and the A/B re-embedded the corpus per arm (no cached-vector cross-contamination)
- [ ] **Harrier gate:** Often missing the query instruction — verify query vectors differ from document vectors for identical text, and the GGUF arm passed a pooling sanity probe
- [ ] **Personal bench:** Often missing paraphrase pressure — verify content-word overlap is bounded and BM25-only vs hybrid deltas are reported per category and per language
- [ ] **Personal bench:** Often missing CJK honesty — verify ZH lexical queries are exact runs and ZH gains are attributed to the vector leg
- [ ] **Metadata filters:** Often missing frontmatter-only edits — verify a tag-only edit is visible to filters without a body change, on an upgraded DB
- [ ] **Metadata filters:** Often missing selective-filter recall — verify a 2%-selectivity filter returns matching docs on the vector leg
- [ ] **Dedup/offset:** Often missing page continuity — verify page 2 has no page-1 repeats, offset+rerank+filter compose, and offset=0 is byte-identical to the recorded contract
- [ ] **Title FTS:** Often missing the upgrade path — verify an old single-column DB migrates, triggers sync both columns, and suggestions survive
- [ ] **Parser wiring:** Often missing the YAML `---` case and the one-time reindex — verify non-md checksums migrate once, md stays byte-identical
- [ ] **Scan fixes:** Often missing derived-signal parity — verify staleness/context output is byte-identical and legacy verbatim context rows still attach
- [ ] **Vacuum/backup:** Often missing live-host proof — verify vacuum succeeds or fails retryably beside MCP+watch; backup passes integrity_check
- [ ] **MCP SDK:** Often missing real-client dual-era proof — verify the client matrix (not just SDK Client), stdout purity on cold first query, and watch teardown order under the new lifespan
- [ ] **MCP annotations:** Often missing honesty tests — verify no write tool carries readOnlyHint and descriptions match backend behavior
- [ ] **Distribution:** Often missing non-TTY silence and backend truth — verify piped stdout has zero progress bytes; models status shows the actual llama.cpp backend; Linux install avoids CUDA by default
- [ ] **Windows smoke:** Often missing degradation assertions — verify daemon/service commands refuse cleanly and the flock warning is visible
- [ ] **Chunk sweep:** Often missing per-arm re-embedding — verify arms use isolated indexes, breadcrumb gains are ablated per leg, and embed cost is reported
- [ ] **PyPI:** Often missing version single-sourcing and a TestPyPI dry run — verify all version sites agree and the OIDC workflow publishes from a protected environment

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Cross-model vectors shipped (no identity marker) | MEDIUM | Add marker; force re-embed affected collections (`sif embed --force`); purge the contaminated cache bucket; re-run the gate |
| Harrier evaluated without query instruction | LOW | Add role-aware embed + cache key; re-run the A/B (vectors re-embed); the gate verdict was invalid, not the model |
| Bad GGUF pooling | LOW | Switch to a verified GGUF (file hash recorded); re-embed; add the load-time probe |
| Stale frontmatter in filters | MEDIUM | Land metadata-aware detection + one-time reindex migration; filters self-heal on next update |
| Dedup/offset contract changed without evidence | LOW | Revert to recorded contract; re-land with golden updates + bench delta recorded |
| Title FTS migration missed old DBs | LOW | Add the column-list detection gate; gated rebuild reseeds; triggers rewritten |
| Scan fix broke staleness/contexts | LOW | Revert to derived per-exit marking; re-land attach-once + invalidation caches with parity tests |
| Vacuum corrupted/locked | LOW–MEDIUM | Restore from backup (why backup ships first); re-run under flock+quiesce; integrity_check gate |
| Streaming embed left orphans | LOW | Completeness skip + delete-before-insert make a re-run converge; purge orphan vec0 rows by document |
| SDK migration broke clients | MEDIUM | Pin `mcp>=1.28,<2` compat path; restore golden wire transcripts; re-migrate tool-by-tool |
| CUDA bloat shipped in docs | LOW | Docs fix + CPU index guidance; no data migration |
| Wrong-backend llama-cpp wheel | LOW | `--force-reinstall --no-cache-dir` from the correct index; status probe prevents recurrence |
| PyPI version/name drift | LOW | Yank if needed; single-source version; republish patch |

## Pitfall-to-Phase Mapping

Phases named by feature (roadmap numbering is created downstream). Ordering rationale: CI early (regression net for everything); Correctness before Metadata (shared checksum migration) and before MCP parity (parity mirrors the fixed pipeline); Personal-Bench before Harrier/Tuning (instrument first — v1.1 lesson); identity marker before any Harrier arm; Distribution after CI proves the matrix.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 1. Same-dim swap | Harrier (plan 1: identity marker) | Cross-model equal-width open fails fast; cache bucket carries identity |
| 2. Query instruction + cache role | Harrier | Query≠document vectors; cache role isolation; Qwen3 default byte-identical |
| 3. GGUF pooling | Harrier + Distribution (models pull) | Pooling sanity probe vs ST reference; provenance hash recorded |
| 4. Synthetic lexical bias | Personal-Bench | Overlap budget; per-leg per-category reports; identity-based labels |
| 5. CJK confound | Personal-Bench + Harrier | Per-language × per-leg metrics; ZH lexical = exact runs |
| 6. Small-N default moves | Personal-Bench (stats) + all quality gates | Paired deltas + intervals; EN+ZH held-out tie rule; committed snapshot |
| 7. bge option traps | Tuning | Held-out + latency eval; α per model; max_length per model; cache identity |
| 8. SDK big-bang | MCP-SDK (plan 1 tracer) | Golden wire transcripts per tool; dependency tree resolved on 3.10 |
| 9. Dual-era gap | MCP-SDK (client matrix) | Real clients from each era pass; negotiation implemented |
| 10. stdout purity | MCP-SDK (lazy embedder) + Distribution | Cold-first-query stdout all JSON-RPC; non-TTY progress silent |
| 11. Annotation honesty | MCP-SDK (annotations) + Scale (vacuum path) | Write tools never readOnly; descriptions match behavior; vacuum path restricted |
| 12. Dedup ordering | Correctness | Chunky fixture fills limit; vector-only distinct; contract change recorded |
| 13. Filter application point | Metadata | Both-leg pre-RRF predicates; selective-recall fixture; sentinel contract |
| 14. Frontmatter invisibility | Metadata (precondition) / Correctness | Tag-only edit visible; one shared migration; unchanged file zero writes |
| 15. Pagination | Correctness | Single offset slice; page continuity; offset+rerank+filter compose |
| 16. Title FTS migration | Correctness | Old-DB gate fires; both-column trigger sync; suggestions survive |
| 17. Parser wiring | Correctness | Per-parser fixtures; one forced reindex; md byte-identical |
| 18. Scan fixes vs semantics | Scale | Attach-once parity; derived caches; verbatim-context regression |
| 19. Vacuum vs live hosts | Scale | Concurrent MCP+watch proof; backup integrity_check; 2× disk documented |
| 20. Streaming embed | Scale | Mid-run failure resumable; no orphans; bounded memory; CR-02 reporting |
| 21. torch CUDA bloat | Distribution + CI | Linux CPU install path; 3.10 torch resolution verified |
| 22. llama-cpp wheels | Distribution + CI | Backend probe in status; cp313 CPU/source strategy; switch-backend recipe |
| 23. Windows degradation | CI (smoke) | Graceful refusals; flock warning visible; uv bootstrap on yoga |
| 24. PyPI mechanics | Distribution (after CI) | Version single-source; TestPyPI dry run; OIDC protected environment |
| 25. Chunk sweep invalidation | Tuning | Per-arm re-embed; isolated arm indexes; per-leg breadcrumb deltas; embed cost reported |

## Sources

Confidence scheme: codebase claims HIGH (read at HEAD `1aff2c9`, cited file:line). External claims carry the classify-confidence seam tier (verified websearch MEDIUM; generic webfetch floor LOW) with the source class noted; critical claims were cross-referenced across ≥2 independent sources per the verification protocol. Official primary publishers (model cards, sqlite.org, MCP spec/SDK docs, PyPI metadata, upstream issues) are the strongest external evidence available; community write-ups are tagged MEDIUM and never stand alone.

**Codebase grounding (HIGH — verified locally 2026-11-13):**
- `src/sif/search/hybrid.py` (dedup after truncation :77-99; early-return no-dedup :69-72; over-fetch without offset slice :235-241), `src/sif/search/vector.py` (fetch_k :77; KNN-before-JOIN audit :80-86; no offset :127), `src/sif/search/bm25.py` (LIMIT/OFFSET :92,110-112; min_score after pagination :119-122)
- `src/sif/database/schema.py` (width-only guard :361-376; content-only porter FTS :244-251; misconfig gate :221-231; legacy-trigger pattern :172-216; CR-01 gated rebuild :338-348), `src/sif/database/locking.py` (fcntl fallback :29-34,57-63; deadline→unlocked :83-92)
- `src/sif/indexing/incremental.py` (MarkdownParser hardcoded :30,77; body-checksum skip + mtime-only convergence :302-318), `src/sif/indexing/parser.py` (body vs full-content checksums :71,106,173; create_parser :185-203), `src/sif/indexing/drift.py` (file_size never refreshed :18-23), `src/sif/core/models.py` (Document checksum :146-150; role-less Embedder protocol :318-332)
- `src/sif/embedding/embedder.py` (no prompt support :99-127; embedding=True :181; mean-pool unwrap :225-258; progress bar :123), `src/sif/embedding/manager.py` (cache bucket :153-163), `src/sif/embedding/cache.py` (PK :69-77)
- `src/sif/search/staleness.py` (derived scan/gate/degrade :34-77), `src/sif/search/context_attach.py` (verbatim two-sided matching :1-62), `src/sif/search/suggest.py` (difflib bucket/cutoff/tie-break :250-269; probe contracts :140-166), `src/sif/search/rerank.py` (max_length=512 :237,239; name-based Qwen3 route :438-446; yes/no logits :409-418)
- `src/sif/mcp/server.py` (hardcoded 2024-11-05 :68-74), `src/sif/mcp/backend.py` (eager embedder :91-109; no rerank/expand/snippets :162-181; field remap :182-202; MCP never writes query_log :204), `src/sif/mcp/handlers.py` (query description overclaim :48-52; 4 tools :215-222), `src/sif/mcp/transports/http.py` (Origin-only :181-191), `src/sif/mcp/watch_host.py` (bm25 literal :46-48; D-14 teardown :166-186), `src/sif/cli/commands/mcp.py` (daemon stub :109-126)
- `src/sif/utils/daemon.py` (POSIX double-fork :216-286), `src/sif/cli/commands/watch.py` (systemd-everywhere-non-darwin :416-418), `src/sif/utils/progress.py` (Rich stdout console :49), `src/sif/utils/logging.py` (quiet recipe :48-69)
- `src/sif/cli/commands/index.py` (all-chunks-in-memory + embed inside write tx :317-359; CR-02 :313-316), `src/sif/models/download.py` (md5[:8] cache check :69-75; reranker default = embedding model :18-33), `src/sif/config/settings.py` (Qwen3-0.6B/1024/modelscope defaults :115-137; α=0.5 :176-182; cap 5–50 :15-16)
- `pyproject.toml` (name docsif :6; py>=3.10 :11; classifiers ≤3.12 :16-26; fastapi/uvicorn hard deps :28-40; black in dev :43-50; llama-cpp only in [all] :65-71), `.github/workflows/` (docs.yml only — no test CI), `tests/fixtures/bench/` (56 queries 36/20; heldout_defaults.json; EPSILON=0.01 at benchmark.py:33)
- Empirical CJK test (local, SQLite 3.51.0): porter tokenizer makes `如何配置混合搜索引擎的权重` one vocab term; `MATCH '配置'` = 0 hits

**Embedding models & evaluation (official cards HIGH-content; seam webfetch floor LOW, cross-verified):**
- [microsoft/harrier-oss-v1-0.6b model card](https://huggingface.co/microsoft/harrier-oss-v1-0.6b) — 1024-dim, 32k ctx, last-token + L2, MIT; `prompt_name="web_search_query"` queries only; degradation warning; no GGUF guidance (cross-verified with localGPT + Qwen card)
- [Qwen/Qwen3-Embedding-0.6B model card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) — 1024 (MRL 32–1024), last-token, `prompt_name="query"`, 1–5% drop without instruct (cross-verified with Harrier card)
- [PromtEngineer/localGPT design_rationale.md](https://github.com/PromtEngineer/localGPT/blob/main/Documentation/design_rationale.md) — per-table embedder identity marker + EmbedderMismatchError; width-only guard failure (both 1024); A/B harrier-0.6b vs **Qwen3-Embedding-4B** mixed nDCG@10 0.915 vs 0.875 / docs 0.759 vs 0.638; bge −0.022/−0.058 +1.6 s; Qwen3-Reranker-4B +0.062/+0.173 +12.7 s/7.5 GB; 0.6B rejection; noise floor ~0.014/query; random score-head trap; references eval/DECISIONS.md and eval/decisions/{embedder,reranker}.md. **Correction to the session lead:** the verified design_rationale comparison is vs Qwen3-Embedding-**4B** (0.875), not 0.6B at 0.805 — the 0.805 figure was not verified at that exact value (it may live in eval/decisions/embedder.md, not fetched).
- ggml-org/Qwen3-Embedding-0.6B-GGUF — **unavailable (HTTP 401)**; GGUF pooling-metadata claims rest on the cards' last-token architecture + llama.cpp `--pooling` flag existence ([llama.cpp embedding example](https://github.com/ggml-org/llama.cpp/blob/master/examples/embedding/README.md)) + SIF's mean-pool code; treat specific conversion guidance as MEDIUM until a publisher GGUF card is readable.

**Upstream qmd incidents (HIGH-content primary issues; seam webfetch floor LOW):**
- [tobi/qmd #764](https://github.com/tobi/qmd/issues/764) — rerank cache key stable across model swaps → bit-identical stale scores; fixed by resolved-model-in-key (PR #848)
- [tobi/qmd #776](https://github.com/tobi/qmd/issues/776) — download progress bars flooded Claude Code transcripts; hidden by default (PR #872)

**MCP SDK v2 & spec (official docs; cross-verified whats-new + migration guide):**
- [MCP Python SDK v2 whats-new](https://py.sdk.modelcontextprotocol.io/v2/whats-new/) — 2026-07-28 + 2025-11-25 eras; renames; removals; dual-era serving
- [python-sdk migration.md](https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/docs/migration.md) — pydantic>=2.12, anyio>=4.9, sse-starlette>=3.0, httpx2, opentelemetry-api, exact-pinned mcp-types; snake_case attrs / by_alias wire; low-level auto-wrapping + jsonschema validation removed; 2025-06-18 not mentioned (gap flagged)
- [MCP spec 2025-06-18 tools](https://modelcontextprotocol.io/specification/2025-06-18/server/tools) — annotations MUST be treated as untrusted; outputSchema ⇒ MUST conform structuredContent + SHOULD keep TextContent JSON
- [modelcontextprotocol/registry](https://github.com/modelcontextprotocol/registry) — mcp-publisher CLI; GitHub OAuth/OIDC/DNS/HTTP namespace auth; PRs do not publish
- Annotation incidents: GHSA-PQH8-P93P-2RX7 (Dynatrace DQL injection under readOnlyHint:true; surfaced via search, canonical advisory https://github.com/advisories/GHSA-PQH8-P93P-2RX7); [false-readOnly SQLite tool write-up](https://github.com/mvanhorn/cli-printing-press/blob/8e70ccec8180fb8df72ab6e5f2e7072f37f064dc/docs/solutions/security-issues/mcp-sql-search-readonly-bypass-2026-05-08.md) (MEDIUM — community write-up; VACUUM INTO/ATTACH blocklist gaps, auto-approval in Claude Code/Cursor); [Trust Labels as Attack Surface](https://zenodo.org/records/23129666) (MEDIUM — research preprint)

**Distribution & infrastructure (official primary):**
- [abetlen/llama-cpp-python README](https://github.com/abetlen/llama-cpp-python) — source-only PyPI; per-backend wheel indexes; CUDA/Metal wheels py3.10–3.12 only; `--upgrade --force-reinstall --no-cache-dir`; Windows VS/MinGW
- [PyPI torch 2.15.0](https://pypi.org/project/torch/) + [torch JSON metadata](https://pypi.org/pypi/torch/json) — Linux ~539 MB + cuda-toolkit 13.2.2/nvidia-*/triton; macOS ~139 MB / Windows ~127 MB; Requires-Python >=3.11
- [sqlite.org/lang_vacuum.html](https://sqlite.org/lang_vacuum.html) — VACUUM write-lock/transaction/2×-disk semantics; VACUUM INTO snapshot + crash caveat; backup API incremental
- [docs.pypi.org trusted publishers](https://docs.pypi.org/trusted-publishers/) — OIDC 15-min project-scoped tokens; owner/repo/workflow/environment registration; id-token:write; pending publisher
- [RapidFuzz fuzz docs](https://rapidfuzz.github.io/RapidFuzz/Usage/fuzz.html) — fuzz.ratio = normalized Indel 0–100; score_cutoff semantics (algorithmic difference from difflib matching-blocks ratio is a documented property of the two libraries)
- [BAAI/bge-reranker-v2-m3 card](https://huggingface.co/BAAI/bge-reranker-v2-m3) — 0.6B, bge-m3 base, multilingual, Apache-2.0; CrossEncoder/FlagReranker/transformers usage; sigmoid normalize; example max_length=512

**Evaluation validity (peer-reviewed/thesis primary; cross-verified):**
- [Radlinski, Kurup, Joachims — CIKM 2008](https://dl.acm.org/doi/10.1145/1458082.1458092) ([Cornell PDF](https://www.cs.cornell.edu/courses/cs6784/2010sp/lecture/21-RadlinskiEtAl08.pdf)) — 8 absolute usage metrics unreliable at realistic N; interleaving sensitive for relative judgments
- [Bendersky, Wang, Najork, Metzler — IJCAI 2018](https://www.ijcai.org/Proceedings/2018/725) — personal-search feedback sparse and biased
- [van Wolfswinkel — TU Delft MSc thesis (2026-10-01)](https://repository.tudelft.nl/record/uuid:eb09dbf7-c826-4c63-8bd4-f37f96db38d1) — synthetic-query lexical bias; τ 0.48–0.88 source-only → 0.69–1.00 pooled LLM relabel; NFCorpus synthetic 0.92 vs real 0.32

**Open gaps (flagged for phase-specific research):**
- Exact 2025-06-18 client support in SDK v2 (docs silent) — MCP-SDK plan 1 must test real clients or read SDK source before choosing the version.
- ggml-org GGUF card inaccessible (401) — Harrier phase should verify publisher GGUF pooling metadata directly before the GGUF arm.
- The lead's "0.805 vs Qwen3-0.6B" A/B figure unverified at that exact value (verified comparison is vs 4B) — Harrier phase should read localGPT eval/decisions/embedder.md if the 0.6B head-to-head matters to the gate.
- rapidfuzz cutoff re-measurement on SIF's actual vocab (bucket recall vs speed) — Tuning phase measurement, not a research guess.
- IJCAI 2018 / CIKM 2008 verified at abstract+PDF level; specific metric counts cited from the Cornell PDF summary — sufficient for the directional claim (no absolute click gates at single-user N).

---
*Pitfalls research for: SIF v1.2 — search precision, MCP modernization, measurable quality, distribution*
*Researched: 2026-11-13*
