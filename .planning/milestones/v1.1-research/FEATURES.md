# Feature Research

**Domain:** Live indexing (file watching, incremental reindex, daemon modes) and search-quality tuning (hybrid weights, did-you-mean, reranker thresholds, benchmarks) for a local-first CLI/MCP hybrid search engine
**Researched:** 2026-11-07
**Confidence:** MEDIUM (exa-sourced per seam tier; all load-bearing claims cross-verified against official docs or multiple independent sources; primary-source qmd README/CHANGELOG read directly)
**Scope:** v1.1 milestone features ONLY. Collection CRUD, scan indexing with checksum dedup, BM25/FTS5, sqlite-vec, RRF hybrid, SearchPipeline (expansion + Qwen3-Reranker), MCP server, multi-format output, and `sif bench` exist already and are not re-researched.

## Feature Landscape

Key context finding: **qmd itself has no watch/live-index at all.** Its freshness story is manual `qmd update` (with an mtime+size fast-path table), per-collection `update-cmd` pre-hooks, and an MCP HTTP daemon that keeps models warm (`qmd mcp --http --daemon`, PID file, `qmd mcp stop`). Live Index is therefore SIF differentiating beyond parity, not catching up. Search-quality tuning, conversely, follows well-established industry conventions (Elasticsearch, Weaviate, Meilisearch, Typesense) that transfer directly.

### Table Stakes (Users Expect These)

For the Live Index category, what any tool that claims "automatic indexing" must do (validated against recoll, Zoekt, watchdog ecosystem, Omnisearch, qmd):

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| `sif watch` foreground command (events → incremental reindex) | recoll's `recollindex -m` daemon and every watchdog-based tool offer a run-in-place mode; the milestone's foundation | MEDIUM | watchdog base exists in `src/sif/indexing/watcher.py` but handlers are stubs (log-only). Wire create/modify/delete/moved; resolve path → collection. Use one Observer per process; watchdog auto-selects FSEvents/inotify/ReadDirectoryChangesW |
| Event debouncing / coalescing | Editors emit 2-5 events per save; atomic-rename saves arrive as `moved` not `modified`; Emacs/Kate swap files fire continuous modifies. Without debounce, watch is a CPU churn loop | LOW-MED | watchdog ships `EventDebouncer` (`debounce_interval`, callback receives the burst). Peer conventions: ~50ms debounce + ~500ms forced-flush ceiling for build loops; mkdocs batches ~250ms; Omnisearch defers until next search. SIF's existing checksum dedup makes duplicate/re-fired events harmless no-ops — the hash gate is the safety net |
| Delete / rename handling | Ghost documents otherwise accumulate in the index; recoll maps IN_DELETE/IN_MOVED_FROM → delete, IN_MOVED_TO/IN_CREATE → modify | MEDIUM | Rename = deactivate old path + index new (or path update). Reuse qmd's hard-won lesson: re-index must reactivate deactivated docs, not duplicate them. Missing-root protection: an unmounted collection root must NOT read as mass deletion (qmd #989/#990 shipped this bug) |
| Tiered update depth: FTS/BM25 live by default, embedding opt-in (`--embed`) | Embedding is model-load + per-chunk inference (seconds-minutes); FTS update is milliseconds. Zoekt separates meta-only vs full updates; recoll real-time indexes only its (non-vector) index | MEDIUM | Needs explicit staleness semantics: after a text edit, BM25 is fresh but vectors are stale until `sif embed` (or `--embed` watch). Hybrid search must tolerate stale vectors (existing fail-fast contract only covers vector errors, not staleness) |
| Pre-command staleness detection (lightweight incremental before search when watch is off) | Users who never run a daemon still expect search to reflect recent edits. qmd's `file_sync_state` (mtime+size) fast-path makes re-indexing an unchanged collection take seconds; Omnisearch diffs path→mtime map when the search modal opens | MEDIUM | mtime+size stat scan (no hashing) → changed files only → existing checksum-verified incremental path. Must be quiet when nothing changed, bounded in time, and disableable. Guard the missing-root case. Independent of watch — can ship first as the "always works" floor |
| Multi-process DB coexistence (WAL + busy_timeout) | Watch daemon + MCP server + ad-hoc CLI all open `sif.db`; without WAL, a writer blocks/kills readers | LOW-MED | `PRAGMA journal_mode=WAL` (one writer, many readers, same host — persists across connections), `busy_timeout=5000`, `synchronous=NORMAL`. sqlite-vec vec0 tables are expected to work under WAL (llama-stack ships exactly this pragma set on sqlite-vec connections). Watch writes must dispatch off the observer thread (sqlite3 connections are thread-bound) |
| MCP-embedded watch (same-process refresh) | The milestone's differentiating shape: AI-assistant queries always fresh with zero user ritual. Foundation is just the watch core + WAL inside the server process | MEDIUM-HIGH | Watch thread inside MCPServer (both stdio and HTTP transports). WAL lets queries read while the writer batch commits; writes off the observer thread; batch-debounce so a sync storm never starves query handling. Signal/loop integration differs per transport (stdio: background thread; HTTP: FastAPI lifespan) |
| Daemon lifecycle: `--detach`, PID file, `stop`, `status` | recoll `-m` detaches; qmd daemon writes `~/.cache/qmd/mcp.pid` with `stop`/`status` subcommands | LOW-MED | Stale-PID detection (PID alive? cmdline match?), graceful SIGTERM (flush pending batch), logs to file (not terminal) when detached. Double-fork is ~a dozen stdlib lines; python-daemon (PEP 3143, v3.1.2) is optional weight — qmd precedent favors stdlib detach |
| launchd / systemd service install generation | Daemon form per PROJECT.md (`--detach / launchd / systemd`). Peers punt to manual setup; generating the unit (LaunchAgent plist with KeepAlive/RunAtLoad/ThrottleInterval=10/log paths; systemd user unit with Restart=always/RestartSec=10/WantedBy=default.target) is the standard mechanism | MEDIUM | Established mapping: `launchctl bootstrap gui/$(id -u)` / `systemctl --user enable --now`; absolute interpreter paths (launchd has no user PATH); linger for logout survival on Linux; Windows → print Scheduled-Task instructions rather than calling schtasks. Render templates from `sys.executable`, explicit arg-list subprocess, clear errors when launchctl/systemctl missing |
| Status visibility | qmd `status` shows "time since last update" and "MCP: running (PID …)"; recoll GUI shows monitor state; users must be able to tell whether the index is live | LOW | `sif status`: watcher running?, last sync time, docs indexed/deleted/updated counters, daemon PID. Log to stderr per event batch (indexed N, deleted M) |

For the Search Quality category, what any engine exposing hybrid fusion is expected to expose:

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Hybrid weights + RRF k as settings | Elasticsearch exposes `rank_constant` (default 60) and weighted RRF (per-retriever `weight` × 1/(k+rank)); Weaviate exposes `alpha` (0=BM25, 1=vector, default 0.75) and fusion choice; qmd gives the original query 2× fusion weight | LOW | `HybridSearcher` currently hardcodes `RRFFusion(k=60)` with equal weights. Add settings (e.g., `hybrid_rrf_k`, `hybrid_bm25_weight`, `hybrid_vector_weight`) with validation: k ≥ 1, weights ≥ 0. Defaults unchanged (k=60, equal) — RRF's selling point is being tune-free |
| Per-query overrides (CLI flags / MCP params) | Weaviate and ES take fusion params per request, not just per index; needed for bench sweeps without config reload | LOW | `--rrf-k`, `--weights` (or `--bm25-weight/--vector-weight`) flags on search/query; same params on MCP `query` tool. This is the bridge that makes `sif bench` a tuning tool, not just a reporter |
| Reranker candidate count + score threshold settings | Universal pattern: fetch-k candidates into reranker (hosted convention 50–100; local CPU: keep in the tens), keep top-n (5–10), optional score cutoff. qmd exposes `--min-score 0.3/0.4` on search/query | LOW-MED | Qwen3-Reranker already produces scores. Prefer top-n plus a *relative* threshold (`score ≥ top1 × α`, α ≈ 0.2–0.3) over an absolute cutoff — absolute reranker scores are not calibrated across models/languages/query types and distributions overlap. Expose `rerank_min_score` as opt-in absolute threshold, calibrated via bench |
| Reranker latency controls + visibility | qmd prints per-LLM-step elapsed ("Expanding query… (4.2s)") and right-sized reranker context (40960→2048 tokens, 17× less memory) because chunks are capped ~900 tokens; qmd also skips LLM expansion entirely when BM25 returns strong results | LOW-MED | Candidate-count cap is the main latency dial (cost scales linearly with candidates; local CPU rerank is easily the slowest stage). Report rerank elapsed time in output; bench must measure p50/p95 latency per config so quality/latency tradeoffs are visible |
| Bench expansion: nDCG@k, Hit@k, categorized query sets, per-query breakdown | Golden-set harness convention (Obsidian hybrid-search eval, gbrain qrels gate, synthetic-corpus benchmarks): nDCG@k with graded/partial credit (0.5), MRR, Hit@k, Recall@k, by-category grouping, per-query details, and flagging metric deltas ≥ 0.01. qmd ships Hit@K over synthetic docs | MEDIUM | `benchmark.py` has P@k, recall, MRR (pure Python). Peers deliberately avoid heavy eval deps (ranx pulls Numba; ir-measures wraps C extensions) — pure-Python nDCG@k + Hit@k is the peer pattern. Fixture work dominates: categories (keyword / paraphrase / multilingual), single-gold vs multi-gold, rival-notes difficulty (short canonical note vs longer term-frequency-heavy derivatives — the case hybrid must win). Bench must run a deterministic pipeline (seeded/no-LLM or frozen expansion) or sweeps are noise |
| Did-you-mean on zero/low results | Every hosted engine handles typos: Meilisearch typo tolerance (1 typo for 5–8 char words, 2 for 9+, Damerau-Levenshtein), Typesense `num_typos=2` + drop-tokens fallback when a multi-word query returns nothing; Elasticsearch suggesters are the classic. For CLI: suggest, don't auto-rewrite | MEDIUM | Vocabulary source: FTS5 vocab table (terms + doc counts). Candidate match: `difflib.get_close_matches` (stdlib, fine for note-scale vocabularies) with doc-frequency ranking; spellfix1 is purpose-built but is a loadable extension not in CPython's bundled sqlite (portability cost — keep optional). UX: on zero results print "Did you mean: X?" (ranked, top 2-3); optionally auto-run the top suggestion only when original returned nothing, with a printed notice |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| MCP-embedded watch | No comparable tool does this: qmd's MCP daemon keeps models warm but relies on external `qmd update`; its 60s instruction cache is the closest nod to cross-process freshness. SIF's AI-assistant queries become always-fresh with zero user ritual | MEDIUM-HIGH | (Listed as table stakes above because it is milestone-scoped — but it is the standout differentiator vs every peer surveyed) |
| Pre-command staleness detection on every search | Goes beyond qmd (manual `update`) and Omnisearch (diff only when search UI opens): automatic, bounded freshness floor with no daemon and no ritual | MEDIUM | Milestone-scoped; doubles as the watcher's checksum-gated resync backstop |
| Query-history suggestions (beyond index-term DYM) | Omnisearch persists search history for autocomplete; personal-KB users repeat queries. Combining indexed-term did-you-mean with local history (opt-out, never leaves machine) matches "personal search engine" positioning | LOW-MED | History table (query, timestamp, result-count); suggest recently-used queries by prefix + fuzzy; dedupe against term suggestions |
| Bench-driven tuning loop (`sif bench --sweep`) | Turns the settings above into a closed loop: sweep (rrf_k × weights × rerank params) grid over the golden set, report best config by nDCG@10/MRR with latency. Peers do this offline/LLM-assisted (autoresearch pattern); a built-in deterministic sweep is a differentiator for a CLI tool | MEDIUM | Depends on per-query overrides + expanded metrics. Start with a manual grid (LLM-proposed weights later/never). Report deltas vs baseline; refuse to crown a winner inside noise (<0.01) |
| Staleness-aware search results | Mark results whose vectors lag their text (e.g., a "vector stale" indicator in `status`, or auto-trigger background embed of dirty chunks when `--embed` enabled) | LOW-MED | Natural extension of tiered depth; prevents the silent quality cliff where BM25 found the fresh doc but its stale embedding hurts hybrid fusion |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Server/cluster features (replication, sharding, multi-node, HTTP API for remote clients) | "Meilisearch/Typesense do it" | SIF is a single-user local tool; SQLite + one process per role is the architecture. Cluster features pull in auth, networking, and ops surface that contradict Local-First | WAL-backed multi-process coexistence on one host (already table stakes) |
| Match-time typo tolerance (Meilisearch-style fuzzy matching over all content) | Impressive demos; the hosted-engine UX benchmark | Requires a trigram re-index of the corpus (index bloat, full rebuild) or a spellfix1 extension loadable on every platform (not in CPython's sqlite; compiled-companion packaging burden on macOS/Linux variance). Wrong layer for a CLI: costs every query/index op to serve a rare case | Did-you-mean suggestions from the existing FTS vocabulary on zero/low results + existing prefix (`term*`) queries; add spellfix1 only as an optional accelerator |
| Silent auto-query-rewrite (auto-correct and re-run without telling the user) | "Just fix my typos" | Breaks trust: users can't tell why results appeared; overrides intentional rare-term queries. Typesense's drop-tokens fallback is visible in its API; CLI convention is suggest-only | Print "Did you mean X?" and optionally re-run the top suggestion with a clear notice; never rewrite silently |
| Auto-embedding on every file save (full-depth live updates by default) | "Index is always fully fresh" | Local CPU/battery cost is severe: model load + per-chunk inference per save bursts; recoll explicitly warns real-time indexing of big trees is expensive and periodic is "adequate in most cases" | Tiered depth (FTS live, embed opt-in via `--embed`); batch-dirty vectors and embed on idle/interval when enabled |
| Watcher as sole source of truth (no resync backstop) | Simplicity — "inotify/FSEvents will tell us" | Kernel event queues overflow (recoll handles IN_Q_OVERFLOW; inotify watch limits need sysctl raises on big trees); editors' atomic renames and laptop sleeps drop events. Every mature tool has a backstop: recoll's "Trigger incremental pass", Zoekt's periodic noop-checked resync, Omnisearch's full-reindex-when-too-much-changed | Checksum-gated incremental scan as the fallback layer: pre-command staleness detection IS this backstop; plus a periodic (or on-startup) quick pass while watching |
| Custom lock-file coordination between processes | "Prevent concurrent writes" | Reinvents SQLite locking badly; stale lockfiles after crashes are a classic support tar pit | WAL + busy_timeout + single-writer discipline per process; SQLite already serializes writers |
| LLM in the did-you-mean path | "The local LLM is right there" | Adds 0.5–4s latency and nondeterminism to what must be an instant, offline-safe suggestion; expansion already covers semantic reformulation | Deterministic vocabulary/history suggestions; LLM stays in the existing expansion stage |
| Watching outside collection roots (e.g., whole home dir) | "Catch everything" | recoll's monitordirs exists precisely because monitoring big trees burns resources; unbounded watching also multiplies the missing-root/permission edge cases | Watch exactly the registered collection paths; new dirs under a collection root come free (recursive watch) |

## Feature Dependencies

```
[sif watch foreground]
    └──requires──> [single-file incremental index (create/modify/delete/move)]
    │                  └──requires──> [existing scanner checksum dedup (HAVE) + doc deactivate/reactivate]
    └──requires──> [debounce/coalescing layer]
    └──requires──> [WAL + busy_timeout multi-process setup]

[MCP-embedded watch] ──requires──> [sif watch core] + [WAL multi-process] + [writer off observer thread]
[Daemon --detach]    ──requires──> [sif watch core] + [PID file / stop / status lifecycle]
[Service install]    ──requires──> [Daemon --detach]

[Pre-command staleness detection] ──requires──> [mtime+size fast-path state] + [existing incremental path]
    └──enhances──> [watch] (acts as the checksum-gated resync backstop)

[Tiered depth (--embed)] ──requires──> [single-file incremental] + [dirty-vector tracking]
    └──interacts──> [hybrid search] (stale vectors must not error or silently misrank)

[Hybrid weights/RRF k settings] ──requires──> [existing HybridSearcher/RRFFusion (HAVE)] + settings plumbing
[Per-query overrides]          ──requires──> [weights settings plumbing]
[Bench expansion nDCG/Hit@k]   ──requires──> [existing sif bench + SearchEvaluator (HAVE)]
[Bench --sweep tuning]         ──requires──> [per-query overrides] + [bench expansion]

[Reranker threshold/latency tuning] ──requires──> [existing Qwen3-Reranker scores (HAVE)] + [bench] for calibration
[Did-you-mean suggestions]     ──requires──> [FTS5 vocab table over existing index] + zero-result hook
[Query-history suggestions]    ──requires──> [history table] ──composes──> [did-you-mean]
```

### Dependency Notes

- **Watch shapes are a progression** (per PROJECT.md): foreground `watch` → MCP-embedded → daemon → service install. All four are v1.1 scope; each later form is packaging around the same watch core, so the core (single-file incremental + delete/move + debounce) is the phase-critical risk item and must land first. Order phases along this progression.
- **Pre-command staleness detection is independent of watch** and depends only on existing scan machinery plus an mtime/size fast-path (qmd's `file_sync_state` pattern). It can ship before or in parallel with watch, and doubles as the watcher's resync backstop — high value, low coupling.
- **Tiered depth is coupled to hybrid semantics**: default watch updates FTS only; hybrid queries then fuse fresh BM25 with stale vectors. Requires an explicit decision (acceptable-by-default with `--embed` opt-in, per milestone) plus staleness visibility, not silent divergence.
- **Bench before tuning**: weight/threshold settings without per-query overrides and richer metrics cannot be validated. The peer convention is a frozen golden set + deterministic pipeline; sweeps on a nondeterministic (LLM-expansion) pipeline produce noise. Sequence: metrics/fixtures → overrides → rerank/weight knobs → (optional) sweep.
- **Did-you-mean depends only on the FTS index** (vocabulary extraction via an FTS5 vocab virtual table), not on any live-index work — the two milestone tracks are orthogonal and can proceed in parallel phases.

## MVP Definition

### Launch With (v1.1)

Maps to all nine Active requirements in PROJECT.md:

- [ ] `sif watch` foreground (incremental + debounce + delete/move) — the foundation everything else packages
- [ ] MCP-embedded watch refresh — differentiator; sequenced after foreground watch per the progression
- [ ] Daemon `--detach` + PID/stop/status + launchd/systemd install — packaging of the proven watch core
- [ ] Pre-command staleness detection — the "always works even without watch" floor; qmd/Omnisearch-validated pattern
- [ ] Tiered update depth (FTS default, `--embed` opt-in) — cost control; recoll's resource warning is the cautionary tale
- [ ] WAL + busy_timeout multi-process coexistence — watch must not break MCP/CLI (enabler, not a headline feature)
- [ ] Hybrid weights (BM25/vector/RRF k) as settings + per-query flags — cheapest quality win; industry-standard surface
- [ ] Bench expansion (nDCG@k, Hit@k, categories, per-query, latency) — the measurement substrate for every other knob
- [ ] Reranker threshold/latency tuning (candidates, top-n, relative threshold) — with bench calibration
- [ ] Did-you-mean from index vocabulary (zero-result hook) — the visible UX win

### Add After Validation (v1.x)

- [ ] Query-history suggestions — trigger: did-you-mean adopted; trivial compose
- [ ] `sif bench --sweep` — trigger: bench metrics + per-query overrides landed
- [ ] Staleness-aware result marking / auto-embed of dirty chunks — trigger: tiered-depth semantics field-tested

### Future Consideration (v2+)

- [ ] Optional spellfix1 acceleration for suggestions — only if difflib latency shows up on large vocabularies
- [ ] LLM-assisted weight tuning — only after deterministic sweep exists and proves insufficient

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| `sif watch` foreground core | HIGH | MEDIUM | P1 |
| Pre-command staleness detection | HIGH | MEDIUM | P1 |
| Debounce/coalescing | HIGH (enabler) | LOW-MED | P1 |
| Delete/move handling | HIGH (correctness) | MEDIUM | P1 |
| WAL multi-process setup | HIGH (enabler) | LOW-MED | P1 |
| Tiered depth (`--embed`) | HIGH | MEDIUM | P1 |
| MCP-embedded watch | HIGH | MED-HIGH | P1 (land after foreground watch) |
| Daemon `--detach` + lifecycle + service install | MEDIUM-HIGH | MEDIUM | P1 (last of the progression) |
| Hybrid weights + RRF k settings & flags | HIGH | LOW | P1 |
| Bench expansion (nDCG@k, Hit@k, categories) | HIGH | MEDIUM | P1 |
| Reranker threshold/latency tuning | MED-HIGH | LOW-MED | P1 |
| Did-you-mean suggestions | MED-HIGH | MEDIUM | P1 |
| Query-history suggestions | MEDIUM | LOW-MED | P2 |
| Bench `--sweep` | MEDIUM | MEDIUM | P2/P3 |

**Priority key:**
- P1: Must have for v1.1 (all milestone-scoped; ordering within P1 follows the dependency progression above)
- P2: Should have, add when possible after milestone core
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | qmd (parity reference) | recoll | Zoekt | Meilisearch / Typesense | Omnisearch | Our Approach |
|---------|------------------------|--------|-------|-------------------------|------------|--------------|
| Live file watching | None — manual `qmd update` (+ per-collection `update-cmd` pre-hook) | `recollindex -m` daemon, inotify/FSEvents, `monitordirs` subset, "Trigger incremental pass" resync, periodic mode called "adequate in most cases" | None — pull-based periodic reindex (default 1m interval + jitter), queue with backoff | N/A (push-based documents API; no file watching) | Vault events → flag-for-reindex, processed lazily (modal open / window blur); chunked 500/batch; full reindex when too much changed | watchdog `FileWatcher` (exists) wired to single-file incremental; debounce + checksum gate; FTS-first depth |
| Freshness when idle user runs a search | `qmd update` mtime+size fast-path (`file_sync_state`) — seconds on unchanged collections | n/a (GUI-driven) | Periodic noop-checked resync | n/a | path→mtime diff when search UI opens | Pre-command stat-based staleness detection with silent no-op when clean (goes beyond qmd: automatic, before search) |
| Daemon / background | MCP HTTP `--daemon`, PID file, `mcp stop`, `status` shows PID | `-m` detaches into daemon | Indexserver is a long-running process | Server-first architecture | Plugin process (host-managed) | `--detach` + PID/stop/status mirroring qmd UX; launchd/systemd unit generation for watch daemon |
| MCP-embedded refresh | No — daemon only keeps models warm; 60s instruction cache notices external updates | n/a | n/a | n/a | n/a | Same-process watch inside MCPServer (differentiator) |
| Hybrid fusion tuning | Weighted RRF hardcoded semantics: original query 2× weight; first sub-query 2×; RRF sold as "parameter-free" | n/a (single retrieval) | n/a | n/a | n/a | RRF k + BM25/vector weights as settings and per-query flags; defaults unchanged (k=60 equal weights, matching ES rank_constant=60 default) |
| Typo / did-you-mean | None | None | None | Match-time typo tolerance (1 typo ≥5 chars, 2 ≥9; typo as ranking rule) / num_typos=2 + drop-tokens on zero results | Field-weighted fuzzy (minisearch) | Suggest-only DYM from FTS vocabulary on zero results + optional auto-run-with-notice; no match-time fuzzy (anti-feature) |
| Reranker controls | `--min-score` filtering; right-sized context window; multi-chunk score aggregation; conditional expansion skip | n/a | n/a | n/a | n/a | Candidates/top-n/relative-threshold settings + latency reporting, calibrated by bench (relative threshold α≈0.2–0.3 over absolute — scores not calibrated across models) |
| Bench / eval | Synthetic docs + Hit@K harness (since 0.6.0) | n/a | n/a | n/a | n/a | Expand existing fixture bench: nDCG@k graded, Hit@k, categorized sets (keyword/paraphrase/multilingual), rival-notes difficulty, per-query output, p50/p95 latency; deterministic pipeline; optional sweep |

## Sources

- qmd README + CHANGELOG (https://raw.githubusercontent.com/tobi/qmd/main/README.md, /CHANGELOG.md) — primary source, read directly (current through 1.1.0, 2026-02-20 + Unreleased); no watch command exists; `file_sync_state` mtime+size fast-path; MCP `--daemon`/PID/`stop`; weighted RRF 2× original query; `--min-score`; per-step timing prints; Hit@K eval harness; missing-root protection fix (#989/#990) — MEDIUM (primary source, provider tier)
- Recoll user manual (https://recoll.org/usermanual/) + rclmonrcv_inotify.cpp — real-time indexing modes, `monitordirs`, "Trigger incremental pass", resource warnings, IN_Q_OVERFLOW handling — MEDIUM (official docs + source, cross-checked)
- Zoekt (https://github.com/sourcegraph/zoekt) — indexserver pull-based periodic reindex, incremental index-state (equal→noop / meta-only / corrupt→rebuild), queue + backoff — MEDIUM (official repo)
- watchdog official docs (https://python-watchdog.readthedocs.io/en/stable/examples.html) — EventDebouncer pattern; GitHub issue #795 editor-save event quirks (atomic rename, swap files, FileClosedEvent Linux-only) — MEDIUM (official docs + maintainer issue)
- SQLite WAL docs (https://sqlite.org/wal.html) — one-writer/many-readers, same-host constraint, BUSY edge cases; llama-stack PR #5428 (WAL+busy_timeout on sqlite-vec connections) — MEDIUM (official + corroborating engineering source)
- SQLite spellfix1 docs (https://sqlite.org/spellfix1.html) — vocabulary corrections, loadable-extension status — MEDIUM (official)
- Elasticsearch RRF docs (https://www.elastic.co/guide/en/elasticsearch/reference/current/rrf.html; rank_constant=60, rank_window_size) + weighted-RRF labs post (2025-09); Weaviate hybrid docs (https://docs.weaviate.io/weaviate/concepts/search/hybrid-search; alpha 0–1 default 0.75, relativeScoreFusion vs rankedFusion, no BM25 threshold because unbounded) — MEDIUM (official docs, two independent engines agree on the k=60 convention)
- Meilisearch typo-tolerance docs (https://www.meilisearch.com/docs/capabilities/full_text_search/relevancy/typo_tolerance_settings) + Typesense FAQ (https://typesense.org/docs/guide/faqs.html; num_typos=2, drop_tokens_threshold, max_candidates) — MEDIUM (official docs)
- Reranker thresholds: dreaming.press top-k/threshold guide (2026-08; fetch-k 50–100, keep-n 5–10, threshold-not-portable); apiyi RAG practices (score distributions overlap; relative threshold `score ≥ top1×α`, α≈0.2–0.3); BAAI/bge-reranker-v2-m3 HF discussion #11 (prefer top-k over absolute); Cohere rerank docs (relevant_spans threshold 0.3) — LOW-MEDIUM individually (vendor blogs); consensus consistent across four sources → MEDIUM in aggregate
- Omnisearch (DeepWiki scambier/obsidian-omnisearch + GitHub issue #134) — deferred reindex on flag, mtime diff map, chunked indexing, freeze/scaling failure mode, persisted search history — MEDIUM (AI-generated wiki cross-checked against maintainer issue)
- IR eval: ranx (ECIR 2022 paper, Numba dependency), ir-measures v0.4.3 (https://ir-measur.es/ — facade over pytrec-eval-terrier); peer golden-set harnesses: flowing-abyss/obsidian-hybrid-search eval README (nDCG graded 0.5 partial credit, by-category, per-query), obsidian-second-brain BENCHMARK.md (synthetic rival-notes corpus, single-gold limitations), gbrain eval-bench (qrels + regression gates) — MEDIUM
- Daemon/service patterns: PEP 3143 (https://peps.python.org/pep-3143/, Deferred) + python-daemon 3.1.2 (https://pypi.org/project/python-daemon/, 2024-12); discuss.python.org "Proper way to create a daemon process" (2025); dotagent/taosmd/svci/mise launchd+systemd unit conventions (KeepAlive/RunAtLoad/ThrottleInterval; Restart=always/RestartSec=10/WantedBy=default.target; bootstrap/bootout; enable --now; linger) — MEDIUM (multiple independent implementations agree)

---
*Feature research for: DocSift/SIF v1.1 — Live Index and Search Quality*
*Researched: 2026-11-07*
