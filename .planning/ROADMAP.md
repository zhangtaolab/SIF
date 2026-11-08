# Roadmap: DocSift (SIF)

## Milestones

- ✅ **v1.0 MVP — qmd 功能对等的本地混合搜索引擎** — Phases 1-10.1 (shipped 2026-11-07)
- 🚧 **v1.1 Live Index and Search Quality** — Phases 11-16 (in progress)

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

**🚧 v1.1 Live Index and Search Quality — Phases 11-16 (in progress)**

**Milestone Goal:** 让索引从手动 `index update` 变为自动常新（Live Index），并让搜索质量可配置、可量化、持续可调（Search Quality）。

**Granularity:** Standard · **Phases:** 6 · **Coverage:** 21/21 v1.1 requirements mapped

**Track structure:** Phase 11 is the shared foundation (WAL hardening lands before any second writer process exists). Phases 12-14 form the live-index track (watch hosts, then freshness floor). Phases 15-16 form the search-quality track — orthogonal to 12-14, depending only on 11; bench expansion arrives together with the tuning conclusions it arbitrates. Research SUMMARY.md's suggested phases 1-8 map onto roadmap phases: 1→11, 2→12, 3+4→13, 5→14, 6+7→15, 8→16.

- [x] **Phase 11: Live-Index Foundation (Concurrent DB + Incremental Core)** - WAL/busy_timeout/BEGIN IMMEDIATE hardening, IncrementalIndexer extraction, flock single-writer arbitration (completed 2026-11-07)
- [x] **Phase 12: `sif watch` Foreground MVP** - File changes auto-reindex with debounce, atomic-save/move handling, temp-file exclusion, tiered depth (`--embed`), missing-root protection (completed 2026-11-07)
- [ ] **Phase 13: Watch Everywhere (MCP-Embedded Refresh + Background Daemon)** - `SIF_MCP_WATCH=1` embedded refresh; `--detach` + launchd/systemd service install
- [ ] **Phase 14: Freshness Floor (Pre-Command Refresh + Staleness Marking)** - Stat-based drift refresh before search with no daemon running; staleness markers on vector-lagging results
- [ ] **Phase 15: Search Quality Configuration (Weights + Suggestions)** - `rrf_k`/BM25/vector weights configurable with unchanged defaults; did-you-mean + history suggestions; `sif suggest`
- [ ] **Phase 16: Bench Expansion + Reranker Tuning** - nDCG@k/Hit@k/p50-p95 metrics, ≥50-query tuning/held-out fixtures, `--sweep`, reranker cap + threshold

## Phase Details

### Phase 11: Live-Index Foundation (Concurrent DB + Incremental Core)
**Goal**: The database and indexing core can safely host a resident background writer — watch writes and CLI/MCP reads coexist without lock errors, and exactly one per-file incremental update path exists for all watch hosts to reuse.
**Depends on**: Nothing (first v1.1 phase; v1.0 shipped)
**Requirements**: LIVE-06, LIVE-07
**Success Criteria** (what must be TRUE):
  1. A background index writer running concurrently with CLI and MCP searches completes with zero "database is locked" errors — every connection sets busy_timeout → WAL → synchronous=NORMAL, and write transactions use BEGIN IMMEDIATE
  2. Two index-writer processes started at the same time: exactly one does the work; the other defers cleanly with no duplicated indexing or embedding (flock single-writer arbitration)
  3. `sif index update` produces identical results before and after the refactor — the per-file incremental loop is extracted into one shared IncrementalIndexer (update_cmd delegates to it; the dead DocumentIndexer is retired, no third copy)
  4. Existing CLI/MCP behavior is unchanged — full quality suite green (pytest fail_under=90, ruff, ty)
**Plans**: 3/3 plans complete
Plans:
**Wave 1**
- [x] 11-01-PLAN.md — Shared connection factory (WAL/busy_timeout/BEGIN IMMEDIATE), flock per-DB arbitration, SC1/SC2 proofs (in-suite + subprocess)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 11-02-PLAN.md — IncrementalIndexer extraction with per-file transactions; update_cmd delegates; SC3 golden equivalence

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 11-03-PLAN.md — Dead-code retirement (D-07), embed_cmd under the lock (D-01), full quality gate (SC4)

### Phase 12: `sif watch` Foreground MVP
**Goal**: Running `sif watch` in a terminal keeps the index current as files change — the first complete host of the live-index loop, proving events → incremental reindex end-to-end.
**Depends on**: Phase 11
**Requirements**: LIVE-01, LIVE-02, LIVE-03, LIVE-04, LIVE-05, LIVE-11
**Success Criteria** (what must be TRUE):
  1. With `sif watch` running, adding, editing, and deleting files in a collection are all reflected in search results without running `sif index update`
  2. An editor save emitting 2-5 events coalesces into exactly one index operation, and macOS atomic-save rename chains plus file moves/renames reconcile to the right document (no missed saves, no spurious delete + full rebuild)
  3. Temporary files (`.swp`, `.sb-*`, `4913`, `.DS_Store`, etc.) never enter the index — watch exclusions behave identically to scanner ignore_patterns
  4. Default update depth is BM25/FTS only; `--embed` explicitly opts into vector updates (embedding never runs as a background default)
  5. A collection root that disappears (unmounted or renamed) is not treated as mass deletion — the index survives and recovers when the root returns
**Plans**: 3/3 plans complete
Plans:
**Wave 1**
- [x] 12-01-PLAN.md — End-to-end watch tracer (observer → EventDebouncer → fold → worker → per-burst flock → update_paths) + missing-root guard + shared exclusion predicate + synthetic proof battery

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 12-02-PLAN.md — CLI surface (-c/--embed/--verbose), signal-driven shutdown + WAL checkpoint (D-14), missing-root recovery (D-12), `--embed` inline depth outside write txns (LIVE-05)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 12-03-PLAN.md — Real-FS e2e battery (SC1-5), docs regeneration, full quality gate

### Phase 13: Watch Everywhere (MCP-Embedded Refresh + Background Daemon)
**Goal**: The index stays fresh with no terminal window open — the proven watch loop hosted inside the MCP server and as an installable background daemon.
**Depends on**: Phase 12
**Requirements**: LIVE-08, LIVE-09
**Success Criteria** (what must be TRUE):
  1. With `SIF_MCP_WATCH=1`, an MCP server keeps the index current while serving AI-assistant queries, and searches remain responsive during an event burst (event handling never starves query handling)
  2. `sif watch --detach` runs in the background with working lifecycle controls — PID reported at detach, `--stop` terminates cleanly, `status` reports running state
  3. A launchd LaunchAgent (macOS) or systemd user unit (Linux) can be generated and installed so watch survives login sessions (no forking under the supervisor)
  4. A daemon killed with SIGKILL leaves no stale lock — a restart succeeds immediately (flock, not PID-file, arbitration)
**Plans**: 4/4 plans executed
Plans:
**Wave 1**
- [x] 13-01-PLAN.md — FileWatcher long-lived-host growth: live rescope (D-15), idle WAL checkpoint (D-16), schedule-failure warn (D-17), mcp_watch + interval settings

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 13-02-PLAN.md — Detached daemon: `--detach` double-fork + PID file + `--stop` escalation + `sif status` Watch section + SC4 SIGKILL proof (SC2/SC4)
- [x] 13-03-PLAN.md — MCP-embedded watch on both transports behind SIF_MCP_WATCH, BM25-forced depth, serve-first reconcile (SC1/LIVE-08)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 13-04-PLAN.md — launchd/systemd service install/uninstall (SC3) + docs regeneration + full quality gate

### Phase 14: Freshness Floor (Pre-Command Refresh + Staleness Marking)
**Goal**: Search results are fresh even when no watch is running, and users can see how fresh their results are.
**Depends on**: Phase 11, Phase 12 (LIVE-10 needs the IncrementalIndexer from 11; QUAL-06 staleness marking needs the tiered-depth state from 12)
**Requirements**: LIVE-10, QUAL-06
**Success Criteria** (what must be TRUE):
  1. With no watch or daemon running, a search command detects drifted files (stat-based mtime/size check) and refreshes them before searching
  2. A clean index pays near-zero pre-command cost (no refresh work, no perceptible latency), and drift refresh is capped so a branch switch never becomes a hidden full reindex
  3. Search results for documents whose vectors lag behind BM25/FTS (tiered depth without `--embed`) carry a visible staleness marker in both table and JSON output
**Plans**: 3/3 plans executed
Plans:
**Wave 1**
- [x] 14-01-PLAN.md — LIVE-10 pre-command drift refresh: drift helper + stat snapshot + cap skip-warn + trio wiring (`--no-refresh`) + settings/docs (SC1/SC2, D-01..D-07)
- [x] 14-02-PLAN.md — QUAL-06 staleness core: derived no-embeddings signal at the searcher enrichment seam + SearchResult.vectors_stale + MCP forwarding + `sif status` Vector lag row (D-08..D-11)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 14-03-PLAN.md — QUAL-06 presentation: marker on all five output formats (table/JSON/CSV/MD/XML) + `sif embed` remedy hint on stderr (SC3, D-12/D-13)

### Phase 15: Search Quality Configuration (Hybrid Weights + Query Suggestions)
**Goal**: Users can tune hybrid ranking to their corpus and recover from zero-result queries with suggestions — never silent rewrites.
**Depends on**: Phase 11 (quality track shares only the DB foundation; independent of Phases 12-14)
**Requirements**: QUAL-01, QUAL-02, QUAL-03, QUAL-04
**Success Criteria** (what must be TRUE):
  1. `rrf_k`, `bm25_weight`, and `vector_weight` are configurable via `SIF_` settings and per-query CLI flags / MCP params, and with no configuration the search behavior is byte-identical to today (k=60, equal weights)
  2. Zero- or low-result searches display "Did you mean" suggestions built from indexed terms — every suggestion returns at least one hit, and queries are never silently rewritten
  3. Suggestions incorporate the user's query history (stored locally in query_log, with opt-out / clear available)
  4. `sif suggest` returns prefix completions, did-you-mean corrections, and history suggestions, responding within 100 ms on a realistic personal-KB vocabulary
**Plans**: TBD

### Phase 16: Bench Expansion + Reranker Tuning
**Goal**: Search-quality tuning is quantified and honest — an expanded benchmark with metrics, sweep, and held-out validation justifies shipped defaults and tunes the reranker within interactive latency.
**Depends on**: Phase 15 (per-query weight overrides are the sweep bridge; bench arrives with the tuning conclusions it arbitrates)
**Requirements**: QUAL-05, EVAL-01, EVAL-02, EVAL-03, EVAL-04
**Success Criteria** (what must be TRUE):
  1. `sif bench` reports nDCG@k, Hit@k, and p50/p95 latency for each measured configuration
  2. The benchmark fixture contains at least 50 categorized queries (keyword, synonym/paraphrase, multilingual, rival-notes) split into tuning and held-out sets
  3. `sif bench --sweep` grids over weights and k, and differences within noise (<0.01) are explicitly not declared winners
  4. Shipped defaults are justified by held-out results and documented — defaults change only if held-out data (not the tuning set) warrants it
  5. The reranker honors a candidate cap (10-20 on CPU) and a configurable relative threshold (score ≥ top1 × α), and the skip-rerank fast path keeps `sif search query` interactive
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 11. Live-Index Foundation | v1.1 | 3/3 | Complete    | 2026-11-07 |
| 12. `sif watch` Foreground MVP | v1.1 | 3/3 | Complete    | 2026-11-07 |
| 13. Watch Everywhere (MCP + Daemon) | v1.1 | 4/4 | In Progress | - |
| 14. Freshness Floor (Pre-Command + Staleness) | v1.1 | 3/3 | In Progress | - |
| 15. Search Quality Configuration | v1.1 | 0/TBD | Not started | - |
| 16. Bench Expansion + Reranker Tuning | v1.1 | 0/TBD | Not started | - |

---
*Roadmap created 2026-11-07 for milestone v1.1 — phase numbering continues from v1.0's Phase 10.1 (11 phases shipped).*
