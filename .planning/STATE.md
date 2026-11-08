---
gsd_state_version: "1.0"
milestone: v1.1
milestone_name: Live Index and Search Quality
current_phase: 15
current_phase_name: Search Quality Configuration (Hybrid Weights + Query Suggestions)
status: planning
stopped_at: Phase 15 context gathered
last_updated: "2026-11-08T08:59:37.736Z"
last_activity: 2026-11-08
last_activity_desc: Phase 13 complete, transitioned to Phase 15
state_head: 82b139a13ad1ee2488e03a3eec184dc5b3926415
progress:
  total_phases: 6
  completed_phases: 4
  total_plans: 13
  completed_plans: 13
---

# DocSift — Project State

## Project Reference

- **Name:** DocSift (package `sif`)
- **Core Value:** 用户可以在自己的笔记和文档库中，用自然语言快速、准确地找到需要的信息——无论关键词是否匹配。
- **Current Focus:** v1.1 Live Index and Search Quality — Phase 13 (Watch Everywhere: MCP-Embedded Refresh + Background Daemon) ready to discuss
- **Tech Stack:** Python 3.10+, SQLite (FTS5 + sqlite-vec), Click, Pydantic, sentence-transformers, llama-cpp-python
- See: .planning/PROJECT.md (updated 2026-11-07)

## Current Position

Phase: 15 — Search Quality Configuration (Hybrid Weights + Query Suggestions)
Plan: Not started
Status: Ready to plan
Last activity: 2026-11-08 — Phase 13 complete, transitioned to Phase 15

Progress: [███████░░░] 67%

## Performance Metrics

- **Velocity:** v1.0 shipped 68 plans / 11 phases (2026-04-14 → 2026-11-07); recent plans averaged ~13 min
- **Suite:** 1015 passed @ 96.20% coverage (fail_under=90 active); ruff/format/ty green
- **v1.1:** 0/6 phases, 0 plans

| Phase | Plans | Status |
|-------|-------|--------|
| 11-16 (v1.1) | 0 | Not started |
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

### Pending Todos

- [ ] (Backlog) Phase 10 regen code review: WR-01..WR-10 open — ledger in 10-REVIEW-DISPOSITION.md
- [ ] (Backlog) Phase 10.1 regen code review: IN-10..IN-13 — ledger in 10.1-REVIEW-DISPOSITION.md

### Blockers/Concerns

- None

## Deferred Items

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| Feature | FUTR-01 spellfix1 DYM acceleration | v2+ | 2026-11-07 | v1.1 |
| Feature | FUTR-02 LLM-assisted weight tuning | v2+ | 2026-11-07 | v1.1 |
| Feature | FUTR-03 symspellpy DYM fallback (only if UAT shows difflib gaps) | v2+ | 2026-11-07 | v1.1 |

## Session Continuity

Last session: 2026-11-08T08:59:37.444Z
Stopped at: Phase 15 context gathered
Resume file: .planning/phases/15-search-quality-configuration-hybrid-weights-query-suggestions/15-CONTEXT.md

- **Next expected action:** `/gsd-discuss-phase 13` (Phase 13 needs context; research flags: daemon/service-install specifics already in research/STACK.md)
- Research flags for later phases: Phase 13 (daemon/service-install specifics), Phase 16 (`SearchOptions.candidate_limit` audit + fixture design)
