---
gsd_state_version: "1.0"
milestone: v1.1
milestone_name: Live Index and Search Quality
current_phase: 11
status: completed
stopped_at: Phase 11 complete — all phases complete
last_updated: "2026-11-11T07:42:41.935Z"
last_activity: 2026-11-11
last_activity_desc: Phase 11 complete
state_head: 486fc59d124a2d86b8146c9d9637170473d985e9
progress:
  total_phases: 6
  completed_phases: 6
  total_plans: 22
  completed_plans: 22
  percent: 100
---

# DocSift — Project State

## Project Reference

- **Name:** DocSift (package `sif`)
- **Core Value:** 用户可以在自己的笔记和文档库中，用自然语言快速、准确地找到需要的信息——无论关键词是否匹配。
- **Current Focus:** v1.1 Live Index and Search Quality — all 6 phases complete; milestone ready for audit/close
- **Tech Stack:** Python 3.10+, SQLite (FTS5 + sqlite-vec), Click, Pydantic, sentence-transformers, llama-cpp-python
- See: .planning/PROJECT.md (updated 2026-11-09)

## Current Position

Phase: 11
Plan: Not started
Status: All phases complete
Last activity: 2026-11-11 - Completed quick task 261111-l7p: Correct Phase 10 WR-10 embedding-dimension mismatch recovery guidance

Progress: [██████████] 100%

## Performance Metrics

- **Velocity:** v1.0 shipped 68 plans / 11 phases (2026-04-14 → 2026-11-07); recent plans averaged ~13 min
- **Suite:** 1504 passed, 1 skipped @ 95.00% coverage (fail_under=90 active); ruff/format/ty green
- **v1.1:** 6/6 phases, 22/22 plans (complete; Phase 11 re-verified at HEAD e20ce25 2026-11-11 after review-fix cycle)

| Phase | Plans | Status |
|-------|-------|--------|
| 11-16 (v1.1) | 22 | Complete |
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 11 P01 | 27 min | 3 tasks | 13 files |
| Phase 11 P02 | 12 min | 2 tasks | 5 files |
| Phase 11 P03 | 9 min | 2 tasks | 11 files |
| Phase 12 P01 | 42 min | 2 tasks | 12 files |
| Phase 12 P02 | 34 min | 2 tasks | 5 files |
| Phase 12 P03 | 21 min | 2 tasks | 4 files |
| Phase 13 P01 | 25min | 2 tasks | 3 files |
| Phase 13 P02 | 28min | 2 tasks | 7 files |
| Phase 13 P03 | 18min | 2 tasks | 6 files |
| Phase 13 P04 | 18min | 2 tasks | 8 files |
| Phase 14 P01 | 24min | 2 tasks | 10 files |
| Phase 14 P02 | 14min | 2 tasks | 13 files |
| Phase 14 P03 | 13min | 2 tasks | 2 files |
| Phase 14 P03 | 13min | 2 tasks | 2 files |
| Phase 15 P01 | 21 min | 3 tasks | 17 files |
| Phase 15 P02 | 20 min | 3 tasks | 11 files |
| Phase 15 P03 | 10 min | 3 tasks | 11 files |
| Phase 16 P01 | 17 min | 3 tasks | 5 files |
| Phase 16 P01 | 17 min | 3 tasks | 5 files |
| Phase 16 P02 | 18 min | 3 tasks | 7 files |
| Phase 16 P03 | 14 min | 3 tasks | 157 files |
| Phase 16 P06 | 12 min | 3 tasks | 5 files |
| Phase 16 P04 | 27 min | 3 tasks | 5 files |
| Phase 16 P05 | 13 min | 3 tasks | 9 files |
| Phase 16 P05 | 13 min | 3 tasks | 9 files |

## Accumulated Context

### Decisions

Full log: PROJECT.md Key Decisions. Recent (v1.1 planning):

- [Phase 12]: per-burst flock — watch never holds the Phase 11 lock while idle; `update_paths` is the per-path seam all Phase 13/14 hosts reuse (cost ∝ burst size, stat-decides)
- [Phase 12]: `FileScanner.matches` is the ONE exclusion predicate (scan and watch share it); `DEFAULT_IGNORE_PATTERNS` gained editor noise (`.sb-*`/`4913`/`.#*`/`*.tmp`)
- [Phase 12]: D-11 missing-root guard in the shared core closed a latent `update_cmd` mass-delete bug (rglob on a missing root yields empty → sweep)
- [Phase 12]: `--embed` computes chunk+embed strictly OUTSIDE write transactions inside the same burst lock window (embed_cmd's inside-txn shape deliberately NOT copied); lazy model load, fail-soft dimension check
- [Phase 12]: signal shutdown = one bounded flush + `wal_checkpoint(TRUNCATE)` + exit 0; second signal exits 130 (module-level SignalState, directly invocable for tests)
- One `LiveIndexService` watch core hosted three ways (CLI watch / MCP thread / pre-command check); `IncrementalIndexer` extracted from `update_cmd` — no third copy of the indexing loop
- WAL + busy_timeout + BEGIN IMMEDIATE lands BEFORE any second writer process (Phase 11 is first)
- Zero new runtime dependencies; only change is watchdog cap `>=4.0.0,<7.0.0`
- Search-quality track (Phases 15-16) is orthogonal to watch hosts (12-14); only Phase 11 is shared
- QUAL-06 staleness marking slotted with pre-command staleness detection (Phase 14)
- [Phase 16]: rerank is explicit opt-in (`SIF_RERANK_ENABLED` default off + `--rerank`); candidate cap clamped 5-50 in ONE shared `resolve_candidate_limit`; over-fetch `max(limit+offset, cap)` makes the cap bind
- [Phase 16]: sweep honesty = rounded-delta tie rule (`round(best-ndcg,6) < 0.01`), tuning-split-only ranking, per-category breakdown on every config; held-out delta +0.0066 < 0.01 → shipped defaults UNCHANGED, honestly documented
- Bench expansion + held-out split lands together with the tuning conclusions it arbitrates (Phase 16)
- [Phase 11]: Legacy duplicate DatabaseConnection (database.py) routed through the factory ahead of its 11-03 retirement: deleting the sqlite_vec import (plan-mandated) while leaving the class untouched would break ruff F821 and two patch-target tests
- [Phase 11]: index_lock deadline expiry breaks to the yield instead of returning - a pre-yield return from a contextmanager raises RuntimeError and crashes the D-02 loser path (caught by the 11-01 Task 3 RED test)
- [Phase 11]: WAL retry is a for-else with an unguarded final attempt (persistent contention surfaces the original OperationalError; non-wal row degrades with a warning); busy-timeout wait test made deterministic instead of the plan's racy busy_timeout=200 numbers
- [Phase 11]: Progress callback protocol is short 'code payload' events (scan/unchanged/error/indexed): IncrementalIndexer stays presentation-free and the CLI _render_index_event is the only place events become Rich output
- [Phase 11]: Per-file loop body split into _process_file/_sweep_removed helpers to keep complexity <=10 with no noqa exemption; MarkdownParser became indexer instance state (PLR0913)
- [Phase 11]: RED phase committed an importable zero-behavior skeleton with the failing tests so the suite collects (assertion failures, not import errors); the pre-update hook stays in the CLI as _run_pre_update_hook
- [Phase 11]: 11-03: dead-test cleanup lands inside the RED commit — deleted test files import symbols deleted in Task 1, so the same-commit removal is what lets the suite collect; the RED target fails on its assertion, never an import error
- [Phase 11]: 11-03: commit-on-clean-exit for the surviving DatabaseConnection is proven via transaction(); the retired duplicate's connect() was the only connect() that committed (D-07 consequence)
- [Phase 11]: 11-03: embed_cmd joins update_cmd under the same per-DB flock (D-01) — lock acquired after model load and dimension checks; per-collection transaction structure unchanged (D-05); REFACTOR skipped to avoid reworking 11-01's committed lock-wrap shape
- [Phase 11]: 11-03: embed_cmd's index_lock wrap made eight test_index.py mocks materialize MagicMock/mock/<id>.lock litter in the repo root — fixed by passing tmp_path sif.db (same class as 11-01's update_cmd fix; any command that wraps Path(index_path) must never receive a mock index_path)
- [Phase 12]: [Phase 12] FileWatcher tunables bundled into WatchConfig dataclass (plan's 8-param constructor trips PLR0913; no-noqa culture); 12-02 flags extend the struct
- [Phase 12]: [Phase 12] fold_events resolves a both-touched-and-deleted path toward the index candidate (remove -= index): order-independent, satisfies the atomic-save truth, lossless because update_paths' stat still removes gone paths
- [Phase 12]: [Phase 12] watch e2e waits for the banner printed AFTER observer.start() (python -u subprocess): seed-row polling alone leaves a lost-event window between the reconcile commit and arming
- [Phase 12]: [Phase 12] EventDebouncer float interval passed via cast(int): watchdog 6.0.0 annotates int but the value only flows into Condition.wait (source-verified)
- [Phase 12]: [Phase 12] Docs regen (make docs-generate) deferred to 12-03 per plan - docs gate test red until then; WINDOWS ledger entry open
- [Phase 12]: [Phase 12] Watch reconcile jobs stay BM25-only at embed depth: the per-file embed leg needs a computable changed-path set, which only burst jobs have (vectors catch up on the next burst or sif embed)
- [Phase 12]: [Phase 12] Worker stop sentinel wakes the re-stat idle wait so D-14 bounded shutdown never waits out watch_restat_interval (sentinel-skipping drain; T-12-06)
- [Phase 12]: [Phase 12] Embed changed-path detection = checksum before/after snapshots around the BM25 leg (None->new = added, old->new = updated) — IncrementalIndexer's Phase 11 contract untouched
- [Phase 12]: E2E WAL-truncate proof: parent holds an open read connection so the child's close is never last (SQLite deletes a checkpointed -wal otherwise) and first proves a non-empty WAL after a live write — the post-exit 0-byte file then uniquely demonstrates the D-14 truncate
- [Phase 12]: watch_* settings reach docs/configuration.md by registering a Watch Settings section in the generator's SECTIONS allowlist — the doc is only ever regenerated (never hand-edited); generator now renders default_factory defaults by product ([]) instead of PydanticUndefined
- [Phase 12]: E2e output capture merges stderr into the stdout capture file (banner = console/stdout, D-12 recovery warnings = logger/stderr) so both are assertable from one artifact; configuration.md greps must use SIF_WATCH_* env-var spellings, never lowercase field names
- [Phase 13]: 13-01: rescope is an exact-set diff — the provider embodies the host's eligible set (a -c filter withholds names), so rescope-within-the-filter is the locked reading of open question 1
- [Phase 13]: 13-01: tick deadline machinery (rescope + checkpoint) seeds lazily, resets on every due fire; busy/recent-burst skips postpone a full interval, never retry inside the tick (Pitfall 7)
- [Phase 13]: 13-01: D-17 schedule failure treated like a missing root (state.missing stays True) so the D-12 tick retries without spam; recovery 'returned' warning moved inside the successful-reschedule branch
- [Phase 13]: 13-01: worker-thread guards around rescope provider and checkpoint pragma — one failure cannot kill a months-long daemon's worker thread (Rule 2)
- [Phase 13]: 13-02: detach handshake = one pipe message (armed <pid>/error <msg>) with 30s bounded select; PID printed only when schema+collections+PID-file are ready (never a silent maybe-detach)
- [Phase 13]: 13-02: corroboration's 'watch' marker is token-based (command.split()) so a reused PID whose argv merely embeds 'watch.db' never corroborates — fail-closed Pitfall 3 reading
- [Phase 13]: 13-02: run_watch_host(WatchHostParams) is the shared body on an OPEN Database; daemon derives its params via dataclasses.replace wiring rescope-within-filter + checkpoint intervals; graceful daemon exit unlinks its own PID file
- [Phase 13]: MCP watch host forces the literal bm25 depth (D-02) and serves first (D-04/Pitfall 4): one shared host module gates on SIF_MCP_WATCH, never reads the update-depth setting, and enqueues the startup reconcile as the watcher's first queued jobs so initialize/lifespan never wait on indexing — A background host the user did not launch with an explicit embed flag must never compute embeddings (billing-surprise guard); a protocol server cannot afford a blocking first reconcile (12-D03 checksum skipping absorbs the startup burst either way)
- [Phase 13]: HTTP lifespan threading is unconditional with default-None parameters (D-01): create_app/HTTPTransport/run_http_server always accept and forward the lifespan; the flag check lives inside start_embedded_watch so flag-off serving stays byte-identical with zero transport-side conditionals — Keeps every existing create_app(server) call site compiling and passing (compat-pinned) and avoids conditional plumbing drifting between the two transports; mcp_watch_lifespan stays a plain async CM so watch_host never imports fastapi
- [Phase 13]: MCP watch e2e is hermetic: queries use the lex: BM25 prefix and the child env sets SIF_MODEL_TYPE=gguf so embedder construction fails fast - no model load, no network, ~1s deterministic server boot — The default ModelScope boot loaded a real embedding model in the subprocess (seconds of mps variance, cache dependence); lex: keeps the query path embedder-free by routing and the gguf fail-fast removes the load entirely
- [Phase 13]: 13-04: the service argv tail bakes exactly -c names + --embed-iff-embed-depth over an absolute interpreter and resolved --index path — the supervised process depends on neither user PATH nor cwd (SC3/D-11) — launchd sees no user environment, so a depth that arrived via SIF_WATCH_UPDATE_DEPTH in the installing shell is only replayable by baking the --embed flag into ProgramArguments/ExecStart
- [Phase 13]: 13-04: launchctl bootout is asynchronous — production uninstall returns after issuing it (a re-install inside the window is covered by the Pitfall-5 bootout-then-bootstrap retry); tests deadline-poll the not-loaded state — The job leaves the gui domain only after the SIGTERM-ed watcher finishes its graceful flush + checkpoint, so an immediate launchctl print still succeeds; waiting belongs to outcome-asserting tests, not the uninstall UX
- [Phase 13]: 13-04: manager binaries are invoked by bare name after a shutil.which gate — explicit argv lists only, never a shell (D-12); an AST-level unit test pins the discipline (no shell=True keyword, no string passed to the invocation helper) — Presence is gated once with a friendly typed ServiceManagerMissing surfaced as ClickException; the argv stays the documented literal form so fake-runner tests assert it exactly
- [Phase 14]: 14-01: drift compare is mtime-primary — documents.file_size is frontmatter-stripped body length never refreshed on update (size compare would false-positive forever); derivation intent preserved (content changes always move mtime)
- [Phase 14]: 14-01: silence-first cap decision in _pre_search_refresh — total_count==0 returns before the cap is consulted; settings-construction failure skips the check silently so unrelated bad config never breaks 'sif search' (query/vsearch surface it at their embedder touchpoints)
- [Phase 14]: 14-01: refresh_drifted is the only lock acquisition (one window for all collections); clean search provably lockless — recording-lock spy asserts zero acquisitions
- [Phase 14]: 14-02: staleness formula corrected to 'no rows in document_embeddings' (BM25 updates purge chunks AND embeddings — 'chunks without embeddings' never fires for the real lag state); display gate marks nothing until the index has >= 1 embedding
- [Phase 14]: 14-02: MCP backend re-maps core fields explicitly — vectors_stale must be forwarded into metadata by hand (B5); status Vector lag row counts lag via documents-id membership scan, robust to orphan embedding ids
- [Phase 14]: 14-02: lag-state e2e keeps a keeper doc embedded so the purge leaves the display gate armed; vec0 v0.1.9 rejects NULL TEXT metadata on INSERT so fixtures seed real chunk_id strings
- [Phase 14]: 14-03: one shared _title_cell helper serves all three command tables — the annotation is a constant string appended after the escape()d title (T-14-06), so a truncated title still annotates and search/vsearch/query render uniformly
- [Phase 14]: 14-03: the D-13 hint sits at each command's output tail (not inside a formatter) so every output mode including --files fires it; the no-results early return naturally skips it (zero results means zero stale)
- [Phase 14]: 14-03: stdout-purity tests assert hint-specific fragments ('have stale vectors') because the D-12 table annotation legitimately contains 'stale vectors' on stdout; format batteries read result.stdout (click >=8.2 mixes stderr into .output)
- [Phase 15]: 15-01: fuse() keeps one code path (weights=None means 1.0 per list) — IEEE 1.0*x keeps defaults repr-exact; fuse_with_weights deleted (normalization trap, zero call sites), mismatch ValueError moved onto fuse
- [Phase 15]: 15-01: k rides both fuse call sites (source + variant fusion), weights only at the source fusion (cross-query fusion is not source fusion, Pitfall 9); SIF_RRF_K removed from the docs phantom list once made real
- [Phase 15]: 15-01: MCP weight ranges enforced by Pydantic on QueryInput (ge=1/gt=0, no bespoke handler checks); hand-written input_schema kept in sync; backend falls back to server SIF_ settings per D-04
- [Phase 15]: 15-02: documents_fts_v is main-schema and lazily re-ensured by SuggestionEngine (temp fts5vocab cannot reference main FTS; old DBs/MCP never run init_schema); prefix completions rank df desc then lexical
- [Phase 15]: 15-02: DYM in-vocab predicate is prefix-range membership via bisect (locked Pitfall 4); an uncorrectable out-of-vocab word returns [] for the whole rewrite so every emitted suggestion has every word retrievable (SC2)
- [Phase 15]: 15-02: difflib equal-ratio matches are re-sorted by (ratio desc, term asc) because get_close_matches uses heapq.nlargest (not input order); bucket test is a deterministic <10%-of-vocab spy, no wall-clock races
- [Phase 15]: 15-02: history decay count x 2^(-age_days/14) over one GROUP BY aggregate; read gate is fail-soft (disabled/settings-failure/missing table -> []); query_log writes are short CRUD outside the flock with aware-UTC stamps
- [Phase 15]: 15-03: suggestions ride HybridSearchResults(list[SearchResult]) so hybrid_search's list contract (and every existing mock) survives while QueryToolHandler explicitly remaps QueryOutput.suggestions
- [Phase 15]: 15-03: zero-result JSON is conditional — plain [] preserved when no DYM, {query, results: [], suggestions} only when suggestions exist; SKILL.md documents both shapes
- [Phase 15]: 15-03: DYM computed only when results are empty, on the already-open connection; query_log writes are one fail-soft call per executed CLI search, skipped entirely at SIF_QUERY_HISTORY_ENABLED=0, never written by MCP
- [Phase 16]: [16-01] report(clock=...) measures warmed latency via measure_query_times; cold start = single first warm-up call, never a p50/p95 sample (D-05)
- [Phase 16]: [16-01] bench baseline resolves fusion knobs from current SIF_ settings (D-09, fixes Phase 15 IN-02); SearchPipeline built once per state inside the connection context; collection ids resolved once
- [Phase 16]: [16-01] precision_at_k/recall_at_k binarize internally (grade > 0) so graded fixtures never exceed 1.0 while legacy 0/1 fixtures are byte-unchanged (Pitfall 8)
- [Phase 16]: [16-01] path-keyed relevance: corpus_root resolved once (relative root joins fixture dir, absolute as-is, explicit ctor arg wins); result keys are corpus-relative POSIX with absolute fallback
- [Phase 16]: [16-02] rerank gate = --rerank OR SIF_RERANK_ENABLED, checked BEFORE create_reranker — the off path never constructs a model or imports an optional backend (D-12)
- [Phase 16]: [16-02] -C retained with default None; resolve_candidate_limit(explicit, settings) = explicit > setting > 20 (non-int falls back), always clamped 5..50 — the flag's Click range stays 1..200 and the A3 waiver is recorded beside the option; bench (16-04) imports the same resolver
- [Phase 16]: [16-02] rerank_enabled doc description avoids 'sif search query;' — the docs bare-command gate (tests/test_docs.py) exempts 'query' only when followed by whitespace
- [Phase 16]: 16-03: ConceptEmbedder = blake2b-seeded per-token unit vectors summed and L2-normalized, CJK runs kept whole — deterministic on every platform, no embedding model in CI (D-01)
- [Phase 16]: 16-03: relevance keys are corpus-relative (declared corpus_root resolved once via resolve_corpus_root); build_bench_db stores resolved absolute paths so result keys join — never document ids (D-02, Pitfall 4)
- [Phase 16]: 16-03: multilingual docs keep Chinese phrases as exact contiguous runs surrounded by non-CJK; queries reuse the exact run, never mid-run prefixes (Pitfall 3 porter constraint)
- [Phase 16]: 16-03: pack split fixed in the generator at 9 tuning + 5 held-out per category (36/20); drift gate flags unexpected files too; _settings_mock carries the rerank fields inertly until 16-04 reads them
- [Phase 16]: 16-06: rerank threshold = raw >= on top1*alpha after descending sort, before [:top_k] — exact half retained, no epsilon; 0.0 default keeps direct construction byte-identical
- [Phase 16]: 16-06: over-fetch rides SearchOptions.limit via dataclasses.replace (max(limit+offset, candidate_limit)) reaching hybrid.search and the cross-query fuse; off path passes the caller's options object by identity (SC1-pinned byte-identical)
- [Phase 16]: 16-06: create_reranker resolves rerank_relative_threshold with isinstance(float|int) after getattr — MagicMock settings fall back to 0.0, never leaking into the scoring path (Pitfall 10)
- [Phase 16]: [16-04] sweep ranking is tuning-only by construction: _tuning_evaluator filters split == 'tuning' before any search call (T-16-06); empty tuning set (legacy/all-heldout fixtures) raises a ClickException naming the missing split
- [Phase 16]: [16-04] tie rule = round(best - ndcg_at_10, 6) < 0.01 strict; exactly-0.01 (incl. 0.29-vs-0.28 raw 0.009999...953) is signal, 0.0099 is noise; grid order is the tie-break; the settings baseline measurement is REUSED for its grid slot so baseline deltas are exactly zero
- [Phase 16]: [16-04] rerank states are strictly additive on no-sweep --json (pinned flat keys stay top-level mirroring off); sweep rows carry states only under --rerank; off-only never calls create_reranker; missing backend/model-load degrades to off-only, factory ValueError stays ClickException
- [Phase 16]: [16-04] bench -C typed IntRange(1,200) default None resolves through resolve_candidate_limit (-C 200 -> 50); one CachedEmbedder per invocation shares embeddings across baseline and sweep (D-07)
- [Phase 16]: [16-05] warrants_default_change = round(candidate - baseline, 6) >= 0.01 — inclusive at exactly 0.01 under rank_sweep's rounded-delta arithmetic; tuning results alone can never change defaults
- [Phase 16]: [16-05] Measured verdict is "unchanged": sweep winner (20, 1.0, 0.5) held-out delta +0.0066 < 0.01, so shipped defaults 60/1.0/1.0 stay — the no-change-documented outcome EVAL-04 permits; change-warranted follow-up route named in docs, never executed in-plan
- [Phase 16]: [16-05] Held-out evidence lock: snapshot recomputation + Settings defaults lock in ONE test; vector_weight is the drift-probe knob (rrf_k alone does not move held-out nDCG on this pack); manual real-model row honestly "not yet measured" (WINDOWS id 10)

### Pending Todos

- [ ] (Backlog) Phase 10 regen code review: WR-01..WR-10 open — ledger in 10-REVIEW-DISPOSITION.md
- [ ] (Backlog) Phase 10.1 regen code review: IN-10..IN-13 — ledger in 10.1-REVIEW-DISPOSITION.md

### Blockers/Concerns

- ⚠️ [Phase 11 re-review 2026-11-11] WR-01/WR-02 watcher lifecycle races FIXED (guards in `src/sif/indexing/watcher.py` at 750-759/450/501-603, pinned by IN-04 TestConcurrencyGuardRegressions; re-verified 20/20 at e20ce25). Still open (advisory, carried in `11-REVIEW-DISPOSITION.md`): WR-03 init_schema errors escape as raw tracebacks, WR-04 impossible-state `if not coll: continue` guards, IN-05 model-type set duplicated CLI/Settings

## Deferred Items

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| Feature | FUTR-01 spellfix1 DYM acceleration | v2+ | 2026-11-07 | v1.1 |
| Feature | FUTR-02 LLM-assisted weight tuning | v2+ | 2026-11-07 | v1.1 |
| Feature | FUTR-03 symspellpy DYM fallback (only if UAT shows difflib gaps) | v2+ | 2026-11-07 | v1.1 |

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 261107-cdh | Fix README.md install typo: docdocsif -> docsif in extras install command | 2026-11-07 | ef8edc2 | [261107-cdh-fix-readme-md-install-typo-docdocsif-doc](./quick/261107-cdh-fix-readme-md-install-typo-docdocsif-doc/) |
| 261107-f5t | Bump version to 1.0.1 (release docsif 1.0.1: typo fixes + parser checksum fix since v1.0) | 2026-11-07 | c4088ca | [261107-f5t-bump-version-to-1-0-1-release-docsif-1-0](./quick/261107-f5t-bump-version-to-1-0-1-release-docsif-1-0/) |
| 261111-kn2 | Fix phase 13 idle-checkpoint ResourceWarnings and close the stale phase 16 deferred audit item | 2026-11-11 | c018a68 | [261111-kn2-fix-phase-13-idle-checkpoint-resourcewar](./quick/261111-kn2-fix-phase-13-idle-checkpoint-resourcewar/) |
| 261111-l7p | Correct Phase 10 WR-10 embedding-dimension mismatch recovery guidance | 2026-11-11 | 486fc59 | [261111-l7p-address-the-smallest-safe-well-scoped-op](./quick/261111-l7p-address-the-smallest-safe-well-scoped-op/) |

### Overrides

- [2026-09-03] Phase 03 decision-coverage gate override (user-approved): D-06/D-07/D-08/D-10 accepted as covered-by-legacy — implemented and behaviorally verified per 03-VERIFICATION.md; legacy plans 03-01…03-06 predate D-ID citation and are read-only in gap-closure mode. Verify-phase should re-surface this.

## Session Continuity

Last session: 2026-11-11
Stopped at: Phase 11 re-verified at HEAD e20ce25 (stale-verification regeneration after review-fix cycle, 20/20 passed) — all phases complete
Resume file: None

- **Next expected action:** `/gsd-complete-milestone v1.1` (all 6 phases complete and verified; milestone ready to archive)
