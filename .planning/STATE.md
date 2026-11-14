---
gsd_state_version: "1.0"
milestone: v1.2
milestone_name: Search Precision and Agent Experience
current_phase: 17
current_phase_name: Engineering Foundation (CI Matrix + Hygiene + PyPI)
status: executing
stopped_at: Completed 17-05-PLAN.md
last_updated: "2026-11-14T01:50:41.881Z"
last_activity: 2026-11-13
last_activity_desc: Phase 17 execution started
state_head: 9164e4f40453daeec2fc736740d7655b659e8755
progress:
  total_phases: 8
  completed_phases: 0
  total_plans: 9
  completed_plans: 6
---

# DocSift — Project State

## Project Reference

- **Name:** DocSift (package `sif`, PyPI `docsif`)
- **Core Value:** 用户可以在自己的笔记和文档库中，用自然语言快速、准确地找到需要的信息——无论关键词是否匹配。
- **Current Focus:** v1.2 Search Precision and Agent Experience — roadmap created (Phases 17-24); Phase 17 ready to plan
- **Tech Stack:** Python 3.10+, SQLite (FTS5 + sqlite-vec), Click, Pydantic, sentence-transformers 5.4.1 (locked), llama-cpp-python; v1.2 adds ONLY `mcp>=2.3.0,<3` + `rapidfuzz>=3.14.5,<4`
- See: .planning/PROJECT.md (updated 2026-11-13)
- Archives: v1.0/v1.1 phase artifacts, full decision logs, per-plan metrics under .planning/milestones/

## Current Position

Phase: 17 (Engineering Foundation (CI Matrix + Hygiene + PyPI)) — EXECUTING
Plan: 7 of 9
Status: Ready to execute
Last activity: 2026-11-13 — Phase 17 execution started

Progress: [░░░░░░░░░░] 0%

**v1.2 phase list:** 17 Engineering Foundation (CI + Hygiene + PyPI) · 18 Quality Instrument (Personal Bench + rapidfuzz DYM) · 19 Search Correctness · 20 Metadata Filtering + Discovery · 21 Scale, Maintenance + Embedder Identity · 22 MCP SDK v2 + Agent Packaging · 23 Harrier Gated Evaluation · 24 Tuning + Models UX + Install Docs

## Performance Metrics

- **Velocity:** v1.0 shipped 68 plans / 11 phases (2026-04-14 → 2026-11-07); v1.1 shipped 27 plans / 7 phases (2026-11-07 → 2026-11-12); recent plans averaged ~13-20 min
- **Suite at v1.1 close:** 1591 passed, 1 skipped @ 95.18% coverage (fail_under=90 active); ruff/format/ty green
- **v1.2:** 0/8 phases, 0 plans — per-plan metrics start at Phase 17

**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 17 P01 | 11min | 3 tasks | 14 files |
| Phase 17 P02 | 6min | 2 tasks | 4 files |
| Phase 17 P03 | 21min | 3 tasks | 4 files |
| Phase 17 P04 | 30min | 3 tasks | 10 files |
| Phase 17 P08 | 9 | 2 tasks | 9 files |
| Phase 17 P05 | 7min | 3 tasks | 8 files |

## Accumulated Context

### Decisions

Full log: PROJECT.md Key Decisions. Recent (v1.2 scoping, locked 2026-11-13):

- [v1.2 scope]: PDF/format expansion OUT; MCP official SDK v2 upgrade approved; full Windows deferred to v2 — Phase 17 ships a degradation smoke only via hc remote yoga (Python not preinstalled; `uv python install` first)
- [v1.2 scope]: metadata namespace = `qmd.metadata` compatible (migration parity); model arms MINIMAL (decision "d"): Harrier native vs Qwen3-Embedding-0.6B only; GGUF arm = conditional follow-up MODEL-F1; bge-reranker-v2-m3 OUT
- [v1.2 gate]: Harrier default switch ONLY on an EN+ZH held-out win beyond the 0.01 tie rule; embedder identity marker (not width-only — both models are 1024-dim) is a locked precondition: Phase 21 before Phase 23
- [v1.2 deps]: exactly two new runtime deps — `mcp>=2.3.0,<3` (Phase 22), `rapidfuzz>=3.14.5,<4` (Phase 18); sentence-transformers stays 5.4.1
- [v1.1 carryover]: WAL+flock concurrent DB core; one LiveIndexService watch core hosted three ways; IncrementalIndexer is the single per-file update path; rerank explicit opt-in; bench held-out tie rule round(delta,6) < 0.01
- [Phase 17]: Hygiene deletions land as one atomic plan: modules + exports + fixtures + dependent tests + absence guards, so the suite never stops collecting
- [Phase 17]: uv.lock torch upgraded to the documented 2.14.1/2.15.0 fleets (uv lock --upgrade-package torch) so macOS/Windows PyPI torch matches the Linux CPU fleet instead of lagging at 2.11.0
- [Phase 17]: Lock/packaging guards assert structure (a +cpu torch from the explicit CPU index, no nvidia/triton/black, explicit + Linux-marker index) not exact transitive versions, per D-02
- [Phase 17]: CI matrix follows D-01..D-04 exactly: all 8 cells on every push/PR, dependency-only cache, macos-latest arm64 only, per-ref cancel with fail-fast false
- [Phase 17]: conftest now resets leaked sif logger state before every test — the matrix exposed 13 order-dependent caplog failures under locked pytest 9.0.3 that local pytest 9.1.1 masks
- [Phase 17]: LlamaCppReranker validates the missing model path before importing llama_cpp so clean dev+embed CI environments raise the documented ValueError
- [Phase 17]: Windows degradation guards sit at both detach boundaries (daemon.detach RuntimeError + CLI ClickException) and in _service_manager for win32; the yoga smoke is argv-only, temp-DB, and model-free, with evidence recorded as smoke_head in the SUMMARY
- [Phase 17]: Rich spinners select the ASCII 'line' spinner when the console stream cannot encode braille frames (GBK) — found by the first yoga smoke as a UnicodeEncodeError on the missing-root path
- [Phase 17]: Docs absence guards scan docs/**/*.md (changelog exempt by resolved path) plus DESIGN.md for dotted imports, slash paths, and bare name.py tree entries in one literal list
- [Phase 17]: Removed stale models/search.py tree entries from architecture.md and DESIGN.md alongside the migrations.py/strategy.py rows; bandit VERIFY guard asserts exactly one docs marker remains
- [Phase 17]: Release identity: _version.py stays the only literal and the publish build job requires exact ASCII equality of v+literal to GITHUB_REF_NAME before building
- [Phase 17]: Publish workflow builds once and hands the dist artifact to job-scoped OIDC publish jobs (TestPyPI then PyPI); skip-existing only on TestPyPI; no secrets
- [Phase 17]: 3.13 classifier added only after gh run 43399300651 proved the 8-cell matrix green; README mcp-name marker verified inside the built wheel METADATA

### Pending Todos

- [ ] (Backlog) Phase 10 regen code review: WR-01..WR-10 open — ledger in 10-REVIEW-DISPOSITION.md
- [ ] (Backlog) Phase 10.1 regen code review: IN-10..IN-13 — ledger in 10.1-REVIEW-DISPOSITION.md

### Blockers/Concerns

- ⚠️ [Phase 11 re-review, advisory] WR-03 init_schema raw tracebacks, WR-04 impossible-state guards, IN-05 model-type set duplication — carried in 11-REVIEW-DISPOSITION.md (WR-01/WR-02 fixed)
- [Research gaps — resolve at plan time] qmd filter AST is UNRELEASED (re-verify CHANGELOG at Phase 20); MCP py3.10 install/import smoke at Phase 22 start; transport_security spoofed-header proof before deleting custom middleware (22); documents_fts_v vocab shadow survival on populated DB (19); contexts normalization decision touches a locked Key Decision (21 discussion)

### Roadmap Evolution

- 2026-11-13: v1.2 roadmap created — Phases 17-24 (numbering continues from v1.1's 16.1; no reset). Cross-phase contracts recorded in ROADMAP.md: embedder identity/role-aware embed (21 → 22/23), `metadata` tool schema (20 → 22), docs-generate gate (every phase adding commands/settings)

## Deferred Items

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| Feature | MODEL-F1 GGUF Harrier arm (only if MODEL-01/02 gate passes AND quantized deployment wanted) | Conditional follow-up | 2026-11-13 | v1.2 |
| Feature | WIN-F1 full Windows support (daemon/service/flock parity) | v2+ | 2026-11-13 | v1.2 |
| Feature | FUTR-01 spellfix1 DYM acceleration | Superseded by rapidfuzz (QUAL-01) | 2026-11-07 | v1.1 |
| Feature | FUTR-02 LLM-assisted weight tuning | v2+ | 2026-11-07 | v1.1 |
| Feature | FUTR-03 symspellpy DYM fallback (only if >200k-vocab gaps) | v2+ | 2026-11-07 | v1.1 |
| Candidate | EVAL-F1 LLM-judge grading · FILT-F1 saved filters · QUAL-F1 sweep automation | v1.x candidates | 2026-11-13 | v1.2 |

## Session Continuity

Last session: 2026-11-14T01:50:36.324Z
Stopped at: Completed 17-05-PLAN.md
Resume file: None

- **Next expected action:** `/gsd-plan-phase 17` (Engineering Foundation). Execution order locked: 17 → 18 → 19 → 20 → 21 → 22 → 23 → 24; hard dependencies and cross-phase contracts in ROADMAP.md.
