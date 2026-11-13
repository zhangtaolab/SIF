---
gsd_state_version: "1.0"
milestone: v1.2
milestone_name: Search Precision and Agent Experience
current_phase: 17
current_phase_name: Engineering Foundation (CI Matrix + Hygiene + PyPI)
status: executing
stopped_at: Phase 17 context gathered
last_updated: "2026-11-13T07:59:00.441Z"
last_activity: 2026-11-13
last_activity_desc: v1.2 roadmap created (8 phases, 39/39 requirements mapped)
state_head: 35f3658a7baa18ce4a8bc7f489de973b2c22731c
progress:
  total_phases: 8
  completed_phases: 0
  total_plans: 9
  completed_plans: 0
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

Phase: 17 (Engineering Foundation (CI Matrix + Hygiene + PyPI)) — READY TO EXECUTE
Plan: — (roadmap created; plans TBD)
Status: Ready to execute
Last activity: 2026-11-13 — v1.2 roadmap created (8 phases, 39/39 requirements mapped)

Progress: [░░░░░░░░░░] 0%

**v1.2 phase list:** 17 Engineering Foundation (CI + Hygiene + PyPI) · 18 Quality Instrument (Personal Bench + rapidfuzz DYM) · 19 Search Correctness · 20 Metadata Filtering + Discovery · 21 Scale, Maintenance + Embedder Identity · 22 MCP SDK v2 + Agent Packaging · 23 Harrier Gated Evaluation · 24 Tuning + Models UX + Install Docs

## Performance Metrics

- **Velocity:** v1.0 shipped 68 plans / 11 phases (2026-04-14 → 2026-11-07); v1.1 shipped 27 plans / 7 phases (2026-11-07 → 2026-11-12); recent plans averaged ~13-20 min
- **Suite at v1.1 close:** 1591 passed, 1 skipped @ 95.18% coverage (fail_under=90 active); ruff/format/ty green
- **v1.2:** 0/8 phases, 0 plans — per-plan metrics start at Phase 17

## Accumulated Context

### Decisions

Full log: PROJECT.md Key Decisions. Recent (v1.2 scoping, locked 2026-11-13):

- [v1.2 scope]: PDF/format expansion OUT; MCP official SDK v2 upgrade approved; full Windows deferred to v2 — Phase 17 ships a degradation smoke only via hc remote yoga (Python not preinstalled; `uv python install` first)
- [v1.2 scope]: metadata namespace = `qmd.metadata` compatible (migration parity); model arms MINIMAL (decision "d"): Harrier native vs Qwen3-Embedding-0.6B only; GGUF arm = conditional follow-up MODEL-F1; bge-reranker-v2-m3 OUT
- [v1.2 gate]: Harrier default switch ONLY on an EN+ZH held-out win beyond the 0.01 tie rule; embedder identity marker (not width-only — both models are 1024-dim) is a locked precondition: Phase 21 before Phase 23
- [v1.2 deps]: exactly two new runtime deps — `mcp>=2.3.0,<3` (Phase 22), `rapidfuzz>=3.14.5,<4` (Phase 18); sentence-transformers stays 5.4.1
- [v1.1 carryover]: WAL+flock concurrent DB core; one LiveIndexService watch core hosted three ways; IncrementalIndexer is the single per-file update path; rerank explicit opt-in; bench held-out tie rule round(delta,6) < 0.01

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

Last session: 2026-11-13T06:32:58.069Z
Stopped at: Phase 17 context gathered
Resume file: .planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-CONTEXT.md

- **Next expected action:** `/gsd-plan-phase 17` (Engineering Foundation). Execution order locked: 17 → 18 → 19 → 20 → 21 → 22 → 23 → 24; hard dependencies and cross-phase contracts in ROADMAP.md.
