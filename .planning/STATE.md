---
gsd_state_version: "1.0"
milestone: v1.1
milestone_name: Live Index and Search Quality
current_phase: 12
current_phase_name: "`sif watch` Foreground MVP"
status: executing
stopped_at: Completed 12-01-PLAN.md
last_updated: "2026-11-07T09:46:37.650Z"
last_activity: 2026-11-07
last_activity_desc: Phase 12 execution started
state_head: 10d652a1e0ba66212fd58ee11416883b87f32d69
progress:
  total_phases: 6
  completed_phases: 1
  total_plans: 6
  completed_plans: 4
---

# DocSift — Project State

## Project Reference

- **Name:** DocSift (package `sif`)
- **Core Value:** 用户可以在自己的笔记和文档库中，用自然语言快速、准确地找到需要的信息——无论关键词是否匹配。
- **Current Focus:** v1.1 Live Index and Search Quality — Phase 11 (Live-Index Foundation) ready to plan
- **Tech Stack:** Python 3.10+, SQLite (FTS5 + sqlite-vec), Click, Pydantic, sentence-transformers, llama-cpp-python
- See: .planning/PROJECT.md (updated 2026-11-07)

## Current Position

Phase: 12 (`sif watch` Foreground MVP) — EXECUTING
Plan: 2 of 3
Status: Ready to execute
Last activity: 2026-11-07 — Phase 12 execution started

Progress: [██░░░░░░░░] 17%

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

## Accumulated Context

### Decisions

Full log: PROJECT.md Key Decisions. Recent (v1.1 planning):

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

Last session: 2026-11-07T09:46:37.545Z
Stopped at: Completed 12-01-PLAN.md
Resume file: None

- **Next expected action:** `/gsd-plan-phase 11` (no research flag — pragma recipe fully specified in research/STACK.md)
- Research flags for later phases: Phase 13 (daemon/service-install specifics), Phase 16 (`SearchOptions.candidate_limit` audit + fixture design)
