# Roadmap: DocSift (SIF)

## Milestones

- ✅ **v1.0 MVP — qmd 功能对等的本地混合搜索引擎** — Phases 1-10.1 (shipped 2026-11-07)
- ✅ **v1.1 Live Index and Search Quality** — Phases 11-16.1 (shipped 2026-11-12)

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

<details>
<summary>✅ v1.1 Live Index and Search Quality (Phases 11-16.1) — SHIPPED 2026-11-12</summary>

**Goal:** 让索引从手动 `index update` 变为自动常新（Live Index），并让搜索质量可配置、可量化、持续可调（Search Quality）。

- [x] Phase 11: Live-Index Foundation (Concurrent DB + Incremental Core) (3/3 plans) — completed 2026-11-07
- [x] Phase 12: `sif watch` Foreground MVP (3/3 plans) — completed 2026-11-07
- [x] Phase 13: Watch Everywhere (MCP-Embedded Refresh + Background Daemon) (4/4 plans) — completed 2026-11-08
- [x] Phase 14: Freshness Floor (Pre-Command Refresh + Staleness Marking) (3/3 plans) — completed 2026-11-08
- [x] Phase 15: Search Quality Configuration (Hybrid Weights + Query Suggestions) (3/3 plans) — completed 2026-11-08
- [x] Phase 16: Bench Expansion + Reranker Tuning (6/6 plans) — completed 2026-11-09
- [x] Phase 16.1: Address tech debt: CLI error conventions + cache TTL + watch-host enqueue API (INSERTED) (5/5 plans) — completed 2026-11-12

Full detail: `.planning/milestones/v1.1-ROADMAP.md`

</details>

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 11. Live-Index Foundation | v1.1 | 3/3 | Complete    | 2026-11-07 |
| 12. `sif watch` Foreground MVP | v1.1 | 3/3 | Complete    | 2026-11-07 |
| 13. Watch Everywhere (MCP + Daemon) | v1.1 | 4/4 | Complete    | 2026-11-08 |
| 14. Freshness Floor (Pre-Command + Staleness) | v1.1 | 3/3 | Complete    | 2026-11-08 |
| 15. Search Quality Configuration | v1.1 | 3/3 | Complete    | 2026-11-08 |
| 16. Bench Expansion + Reranker Tuning | v1.1 | 6/6 | Complete    | 2026-11-09 |
| 16.1. Address tech debt (CLI errors + cache TTL + enqueue API) | v1.1 | 5/5 | Complete    | 2026-11-12 |

---
*Roadmap created 2026-11-07 for milestone v1.1. v1.0 (Phases 1-10.1) and v1.1 (Phases 11-16.1) shipped. Next milestone continues phase numbering at 17.*
