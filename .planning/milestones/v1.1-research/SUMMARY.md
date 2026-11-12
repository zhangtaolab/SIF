# Project Research Summary

**Project:** DocSift/SIF v1.1 — Live Index and Search Quality
**Domain:** Local-first hybrid search engine (Python 3.10+, SQLite FTS5 + sqlite-vec, CLI + MCP) adding file-watch live indexing and search-quality tuning
**Researched:** 2026-11-07
**Confidence:** HIGH (stack verdict verified against primary sources + local runtime experiments; architecture mapped directly from `src/sif/` source; pitfalls grounded in exact code lines)

## Executive Summary

SIF v1.1 adds live indexing (file watching → incremental reindex) and search-quality tuning (hybrid weights, did-you-mean, reranker thresholds, benchmarks) to an existing, well-layered local search engine. The headline stack finding is decisive: **zero new runtime dependencies**. Everything is buildable with the existing dep set plus stdlib — the only dependency change is capping `watchdog>=3.0.0` to `watchdog>=4.0.0,<7.0.0` (watchdog 7.0 dropped Python 3.10, which SIF mandates). Competitively, **qmd has no live index at all** — live index is differentiation beyond parity, not catch-up; search-quality tuning follows settled industry conventions (Elasticsearch `rank_constant=60`, Weaviate `alpha`, Meilisearch typo tolerance as suggest-only).

The recommended approach is architectural: one `LiveIndexService` watch-loop core hosted three ways (CLI `sif watch`, MCP-embedded thread, one-shot pre-search staleness check), all funneling into an `IncrementalIndexer` extracted from the existing production loop in `update_cmd` — avoiding a third copy of indexing logic (one copy is already dead code). The non-negotiable foundation is SQLite concurrency hardening: `busy_timeout=5000` → `journal_mode=WAL` → `synchronous=NORMAL` on every connection, plus `BEGIN IMMEDIATE` write transactions — the current code has none of these, and a resident writer will hit "database is locked" on day one.

Key risks, ranked: (1) shipping the watcher without WAL/busy_timeout — instant lock errors; (2) macOS atomic-save rename chains (moved→deleted→created, never a clean modify) causing missed saves or index churn per save — path-based reconciliation + debounce + settle-check is the cure; (3) reranker CPU latency (34–49 s/query measured on qmd issue #264 against the same Qwen3 model) — latency must be a first-class bench axis and candidate caps enforced; (4) weight-tuning overfitting on a small fixture (measured collapse 0.91→0.68 on held-out) — bench expansion with tuning/held-out splits must precede the weights phase.

## Key Findings

### Recommended Stack

**Zero new runtime dependencies.** Only change: `watchdog>=4.0.0,<7.0.0`. Everything else is pragma configuration, stdlib code, and in-house modules. This preserves the pure-Python PyPI package constraint.

**Core technologies:**
- **watchdog (capped `>=4.0.0,<7.0.0`)** — `sif watch` event source; `Observer()` auto-selects FSEvents/inotify; ships built-in `EventDebouncer` (pass interval **positionally**). Cap mandatory: 7.0.0 dropped Python 3.10 and changed pattern/event semantics.
- **SQLite WAL mode (stdlib, config-only)** — `busy_timeout=5000` FIRST, then `journal_mode=WAL`, then `synchronous=NORMAL` in `_create_connection()` and `ConnectionPool`. Verified compatible with sqlite-vec vec0 tables (llama-stack production precedent).
- **Python stdlib (os/signal/plistlib/templates)** — `--detach` double-fork (~30 lines); launchd plist / systemd user-unit generation; foreground under supervisors (never fork under launchd/systemd).
- **stdlib difflib + FTS5 trigram tokenizer (SQLite ≥3.34, runtime-checked with fallback)** — did-you-mean with SQL pre-filter (brute-force difflib is 0.58 s/lookup at 15k terms).
- **In-house pure-Python metrics (extend `benchmark.py`)** — nDCG@k + MAP ~40 lines each; eval libraries (ranx/ir-measures) all pull C extensions/JIT — never at runtime.
- **Pydantic Settings (existing)** — all v1.1 tunables as `SIF_`-prefixed fields.

**Avoid:** watchdog ≥7 on Python 3.10; ranx/ir-measures/pytrec_eval at runtime; SQLite `spellfix1` (not in CPython's bundled sqlite3 — verified locally); `python-daemon` (conflicts with supervisor mode); janus (stdlib `queue.Queue` suffices); unversioned watchdog (split-brain 6.x/7.x semantics across the fleet).

### Expected Features

**Must have (table stakes, all P1):**
- `sif watch` foreground — events → incremental reindex; the foundation everything packages
- Event debouncing/coalescing + delete/rename handling — editors emit 2–5 events per save; atomic saves arrive as rename chains; missing-root must NOT read as mass deletion
- Tiered update depth — BM25/FTS live by default, embedding opt-in (`--embed`); embed is 100–1000× slower and must never be a background default
- Pre-command staleness detection — mtime+size stat fast-path before search; the "always works without a daemon" floor; doubles as the watcher's resync backstop
- WAL + busy_timeout multi-process coexistence — enabler, not headline
- MCP-embedded watch refresh — the standout differentiator (no peer does it); opt-in flag
- Daemon lifecycle (`--detach`, PID/stop/status) + launchd/systemd install generation
- Hybrid weights + RRF k as settings AND per-query flags — defaults unchanged (k=60, equal weights)
- Bench expansion: nDCG@k, Hit@k, categorized query sets, per-query breakdown, p50/p95 latency
- Reranker threshold/latency tuning — prefer relative threshold (`score ≥ top1×α`, α≈0.2–0.3); candidate cap is the latency dial
- Did-you-mean on zero/low results — suggest-only, corpus-constrained terms, never silent auto-rewrite

**Should have (differentiators, P2 after milestone core):**
- Query-history suggestions (composes with DYM; opt-out, local-only)
- `sif bench --sweep` — deterministic grid sweep; refuse to crown winners inside noise (<0.01)
- Staleness-aware result marking / auto-embed of dirty chunks

**Defer (v2+):** optional spellfix1 acceleration; LLM-assisted weight tuning; symspellpy (only if DYM quality proves insufficient in UAT).

**Anti-features:** server/cluster features; match-time typo tolerance (wrong layer, index bloat); silent auto-query-rewrite; auto-embed on every save; watcher as sole source of truth (no resync backstop); custom lockfiles; LLM in the DYM path; watching outside collection roots.

### Architecture Approach

One `LiveIndexService` (new `indexing/live.py`), three thin hosts (CLI watch process, MCP server background thread, one-shot pre-search check), one WAL-mode database, single-writer discipline. The per-file incremental logic is **extracted** from `update_cmd`'s production loop into `IncrementalIndexer` (new `indexing/incremental.py`); the existing `DocumentIndexer` is dead code — retire or delegate. Suggestions are a separate read-only `Suggester` (`search/suggest.py`) invoked by the presentation layer on empty/thin results — never inside `SearchPipeline.search()`. Weights flow via Settings → `HybridSearcher` constructor → `RRFFusion.fuse_with_weights` (which already exists — plumbing, not new math). Critical wiring trap: `sif/models/search.py`'s Pydantic `SearchOptions` already has weight fields but is **dead** — the live path uses `core/models.py` dataclasses; wire constructors, not the dead model.

**Major components:**
1. `LiveIndexService` (`indexing/live.py`, NEW) — debounce → coalesce paths → checksum diff → incremental FTS write → optional embed; host-agnostic
2. `IncrementalIndexer` (`indexing/incremental.py`, EXTRACTED) — per-file checksum-diff update; deletes/moves as first-class tombstones
3. `DatabaseConnection`/`Database` (MODIFIED) — WAL pragma stack + `BEGIN IMMEDIATE` write txns; `SchemaManager` gets a DDL race guard (qmd hit this exact race) + `fts5vocab` + `query_log` tables
4. `Suggester` (`search/suggest.py`, NEW) — prefix completion via fts5vocab + difflib DYM + history; read-only
5. Daemon helper (`utils/daemon.py`, NEW) — detach/pidfile/flock/launchd/systemd; un-stubs `sif mcp daemon`
6. `HybridSearcher`/`SearchPipeline` (MODIFIED) — `rrf_k`/weights ctor params; reranker threshold filter

### Critical Pitfalls

1. **No WAL/busy_timeout + deferred transactions** — a resident writer vs MCP/CLI readers = instant `SQLITE_BUSY`; and busy_timeout does NOT cover read→write lock upgrades, so writes need `BEGIN IMMEDIATE`. Precondition for the entire milestone, not a follow-up.
2. **macOS atomic-save rename chains** — handlers see moved→deleted→created, never a clean modify; treat the **path**, not the event, as the unit of work; filter `on_moved` on `dest_path`; exclude temp-file patterns (`.swp`, `.sb-*`, `4913`, `.DS_Store`). Fixture-test the TextEdit sequence.
3. **Reranker CPU latency** — 34–49 s/query measured (qmd #264, same Qwen3 model); hard candidate cap 10–20 on CPU, p50/p95 latency in every bench report, skip-rerank fast path as default for interactive use.
4. **Weight-tuning overfitting + benchmark leakage** — measured collapse on held-out (0.91→0.68); separate tuning/held-out fixtures, ≥50 queries across query types, regression-floor CI bands (no golden numbers), labels never generated from the engine's own output; bench expansion must precede the weights phase.
5. **Daemon lifecycle + double-writer** — stale-PID restart lockouts (flock is the backstop); three watch forms alive simultaneously triple embed work; design flock-based single-writer arbitration in the Watch MVP (cheap then, compatibility headache later).

Honorable mentions: silent inotify watch exhaustion on Linux (shape the watch scope, reuse scanner ignore logic — live events currently bypass `ignore_patterns` entirely); mid-write reads (settle-check event paths only, never tree-polling — FD exhaustion is proven); embed inside one transaction per collection (blocks all writers for minutes — embed outside txns, per-document commits).

## Implications for Roadmap

Research converges on a dependency-driven 8-step build order (architecture's Suggested Build Order, corroborated by features' dependency graph and pitfalls' phase mapping). Suggested phase structure:

### Phase 1: DB Concurrency Hardening + IncrementalIndexer Extraction
**Rationale:** Foundation every watcher host stands on; WAL retrofit after hosts multiply is the risky direction; extraction removes the dead-code hazard before a third copy of the indexing loop appears.
**Delivers:** WAL/busy_timeout/synchronous=NORMAL on every connection; `BEGIN IMMEDIATE` write txns; DDL race guard; `IncrementalIndexer` with per-file public API extracted from `update_cmd`; flock single-writer design.
**Addresses:** WAL multi-process coexistence (table stakes); single-file incremental (dependency of everything).
**Avoids:** Pitfall 1 (instant lock errors), Pitfall 5's arbitration (designed here), Anti-Pattern 1 (third indexing loop).
**Verification:** CI test of concurrent search + embed with zero lock errors; pragma audit on all connection sites.

### Phase 2: `sif watch` Foreground MVP
**Rationale:** First and simplest host; proves the event→index loop end-to-end; daemon and MCP embed reuse it verbatim. The phase-critical risk item of the milestone.
**Delivers:** EventDebouncer wiring, path-based reconciliation, delete/move tombstones, temp-file/ignore-pattern parity with scanner, BM25-only depth with `--embed` opt-in, settle-checks, overflow recovery.
**Addresses:** `sif watch` foreground, debounce, delete/rename handling, tiered depth.
**Avoids:** Pitfalls 2, 3, 4, 6 (rename chains, save storms, silent watch loss, mid-write reads).
**Verification:** TextEdit-sequence fixture test; burst test (N rapid writes → 1 index op); ignore-parity test; real-editor UAT.

### Phase 3: MCP-Embedded Watch Refresh
**Rationale:** Second host; the standout differentiator; stdio servers are client-lifecycle-owned so embedding must be explicit/opt-in.
**Delivers:** `LiveIndexService` thread in `SearchBackend` (start at construction, join at shutdown), opt-in flag (`SIF_MCP_WATCH=1`), `queue.Queue`/`call_soon_threadsafe` bridge from watchdog threads to asyncio, batch-debounce so sync storms never starve query handling.
**Avoids:** integration gotcha table's asyncio+threads traps; remote-embedding billing without consent.
**Verification:** p95 of concurrent search during an event burst.

### Phase 4: Daemon + Service Install
**Rationale:** Packaging of the proven loop; long-running exposure is where silent watch loss compounds — harden here.
**Delivers:** `--detach` (double-fork), pidfile with liveness validation, flock single-instance lock, SIGTERM graceful drain, launchd LaunchAgent + systemd user-unit generation, un-stub `sif mcp daemon`, `status` visibility.
**Avoids:** Pitfall 5 in full (stale PID, orphaning, double-writer), supervisor anti-patterns (never fork under launchd/systemd).
**Verification:** kill -9 restart recovery; SIGTERM drain exits 0; two-writer arbitration test.

### Phase 5: Pre-Command Staleness Detection
**Rationale:** Independent of the watch loop (needs only `IncrementalIndexer`); the freshness floor for users who run no daemon; doubles as the watcher's checksum-gated backstop.
**Delivers:** stat-only drift gate (milliseconds at personal-KB scale) → `refresh_once()` only on drift; capped so branch switches never become hidden full reindexes; quiet when clean.
**Avoids:** Pitfall 4's overflow backstop; unbounded pre-search cost.
**Verification:** unchanged library adds near-zero startup; missing-root does not mass-delete.

### Phase 6: Hybrid Weights Configurable
**Rationale:** Fully independent of watch tiers; pure plumbing over existing math (`fuse_with_weights` already exists); can slot anywhere after Phase 1 — placed here to keep live-index phases contiguous.
**Delivers:** `rrf_k`/`bm25_weight`/`vector_weight` Settings + constructor injection at the 3 construction sites + per-query CLI flags/MCP params; defaults byte-identical (k=60, equal).
**Avoids:** Anti-Pattern 5 (wiring through the dead Pydantic model).
**Verification:** default-behavior regression test; per-query override works without config reload.

### Phase 7: Query Suggestions
**Rationale:** Needs only schema changes (fts5vocab + query_log), not the watcher — orthogonal track; CJK limitation (porter tokenizer doesn't segment Chinese) means history suggestions matter for Chinese users.
**Delivers:** `Suggester` (prefix via fts5vocab, DYM via SQL-pre-filtered difflib, history from query_log), zero-result hook in CLI/MCP, `sif suggest` command, suggestion-index rebuild on index updates.
**Avoids:** Pitfall 10 (per-keystroke vocabulary scans, corrections not in corpus); anti-feature of silent auto-rewrite.
**Verification:** latency <100 ms on largest realistic vocabulary; every suggestion returns ≥1 hit by construction.

### Phase 8: Bench Expansion + Reranker Tuning
**Rationale:** Consumes Phases 6–7 as measurement subjects; quantified tuning last closes the loop. Bench must precede/accompany weight tuning to be the honest instrument (pitfalls is emphatic: bench before tuning, and latency from bench-expansion onward or reranker tunes blind).
**Delivers:** nDCG@k, Hit@k, categorized fixtures (≥50 queries: keyword/paraphrase/multilingual/rival-notes), tuning/held-out splits, p50/p95 latency columns, reranker candidate cap + relative threshold + skip-rerank fast path, per-query overrides as the sweep bridge.
**Avoids:** Pitfalls 7, 8, 9 (overfitting, leakage, CPU latency trap).
**Verification:** shipped defaults justified by held-out numbers; regression-floor CI bands; `query` on CPU stays interactive.

### Phase Ordering Rationale

- **Dependency-driven:** watch core (2) → MCP embed (3) → daemon (4) → pre-command detect (5) matches the milestone's stated "四种形态，依赖递进" — each later form is packaging around the same `LiveIndexService` core.
- **Foundation-first:** Phase 1 lands WAL before any second process exists; pitfalls research is unambiguous this is a precondition, not a follow-up (recovery is cheap only before hosts multiply).
- **Orthogonal tracks:** search-quality phases (6–8) are independent of live-index phases (2–5) and can proceed in parallel waves if desired — only Phase 1 is shared prerequisite. Suggestions (7) needs only a schema touch; weights (6) is trivial plumbing.
- **Bench before tuning within the quality track:** pitfall research insists bench expansion (measurement instrument) precedes or accompanies weight/reranker tuning; per-query overrides (Phase 6) are the bridge that makes bench a tuning tool.
- **Pitfall coverage:** each phase's verification items come from pitfalls' "Looks Done But Isn't" checklist — real-editor save chains, kill -9 recovery, concurrent search during embed, held-out numbers, latency on large vocabularies.

### Research Flags

Phases likely needing deeper research during planning (`/gsd-plan-phase --research-phase <N>`):
- **Phase 4 (Daemon + Service Install):** launchd plist vs systemd unit generation specifics flagged as an open gap by pitfalls research; platform matrices (linger, ThrottleInterval, exit codes) need concrete verification.
- **Phase 8 (Bench + Reranker):** whether SIF's existing `SearchOptions.candidate_limit` already caps rerank input today — audit before adding a new knob; fixture design (rival-notes, multilingual with porter/CJK limitation) needs deliberate construction.

Phases with standard patterns (skip research-phase):
- **Phase 1 (DB Hardening):** pragma recipe is fully specified in STACK.md integration points; verified against sqlite.org and production precedents.
- **Phase 2 (Watch MVP):** EventDebouncer recipe, rename-chain handling, and scope shaping all documented with exact code references.
- **Phases 3, 5, 6, 7:** well-documented patterns (queue bridge, stat-gate fast-path, constructor injection, fts5vocab suggestions) — standard execution.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Headline verdict verified against primary sources: watchdog changelog raw-fetched, PyPI JSON API, sqlite.org WAL doc, plus local runtime experiments (trigram OK, spellfix1 absent, WAL OK on this machine) |
| Features | MEDIUM | qmd README/CHANGELOG read directly (primary); peer conventions cross-verified across recoll/Zoekt/Meilisearch/Typesense/Omnisearch; exa-sourced per seam tier |
| Architecture | HIGH | Integration mapping read directly from `src/sif/` source (dead `DocumentIndexer`, unwired watcher, no WAL pragmas, hardcoded k=60 all confirmed by grep); external best practices MEDIUM but cross-verified |
| Pitfalls | HIGH | Codebase-grounded findings cite exact lines; several pitfalls backed by upstream incidents (qmd #264, sqlite-vec #40, Hermes #13655); community claims cross-verified across 3–5 sources each |

**Overall confidence:** HIGH

### Gaps to Address

- **Daemon service-generation specifics** (launchd plist fields, systemd linger/exit-code matrix): flagged for Phase 4 research; STUCK-notes carry the open questions.
- **`SearchOptions.candidate_limit` audit**: does it already cap rerank input? Answer during Phase 8 planning before adding a knob.
- **CJK suggestion quality**: porter tokenizer doesn't segment Chinese — vocab-based DYM skews ASCII. Validate history-based suggestions with a Chinese-language corpus during Phase 7 UAT; fixture tests must include CJK.
- **Difflib DYM quality at scale**: SQL pre-filter makes it fast; quality unproven — symspellpy is the documented last-resort fallback (new runtime dep, only if UAT shows gaps).
- **Battery/CPU claims for watchers**: single-community-source, directional only — treat as hypotheses to validate in-phase (Phase 2 profiling).
- **Network-mounted collections**: PollingObserver fallback + WAL-on-network-FS degradation path documented in STACK variants but needs a runtime decision (detect WAL-switch failure, degrade to DELETE journal with warning).

## Sources

### Primary (HIGH confidence)
- watchdog official changelog + `event_debouncer.py` source (tags v3.0.0–v6.0.0) — version history, Python support drops, positional signature
- PyPI JSON API (watchdog, python-daemon, ir-measures, ranx, symspellpy, sqlite-vec) — versions, requires_python, dependency lists
- sqlite.org WAL docs (sqlite.org/wal.html) — WAL semantics, BUSY edge cases, checkpointing
- qmd README + CHANGELOG (raw GitHub) — no watch command; `file_sync_state` fast-path; MCP daemon; missing-root fix (#989/#990); issue #264 reranker latency
- SIF codebase reads (2026-11-07) — watcher stubs, no WAL pragmas, dead DocumentIndexer, hardcoded RRF k=60, dead Pydantic SearchOptions, no fts5vocab
- Local runtime verification (macOS 26.6.2 / py3.13 / SQLite 3.50.4) — trigram OK, spellfix1 NOT available, WAL OK

### Secondary (MEDIUM confidence)
- llama-stack PRs #5428/#5442 + sqlite-vec issue #40 — WAL+busy_timeout with vec0 in production; transactional vec0 writes
- recoll user manual, Zoekt repo, Omnisearch DeepWiki — live-index peer conventions, resync backstops, resource warnings
- Elasticsearch RRF docs (rank_constant=60) + Weaviate hybrid docs (alpha) — fusion-knob conventions
- Meilisearch typo-tolerance + Typesense FAQ — suggest-only DYM conventions
- Qdrant hybrid-tuning guide + chicong115 case study — k-before-weights, measured overfit collapse on held-out
- watchdog issues #538, PRs #750/#754 — macOS rename chains, inode pairing
- taosmd/dotagent/agenttap service-install code — plist/systemd generation pattern (three independent implementations)
- IR-eval peer harnesses (obsidian-hybrid-search, gbrain) — nDCG graded/floor-band conventions

### Tertiary (LOW confidence, directional)
- Battery/CPU drain claims for event-driven vs polling watchers (AgentMonitors issue, SO answers) — validate in-phase
- Individual reranker-threshold vendor blogs (dreaming.press, apiyi) — consensus MEDIUM in aggregate across four sources

---
*Research completed: 2026-11-07*
*Ready for roadmap: yes*
