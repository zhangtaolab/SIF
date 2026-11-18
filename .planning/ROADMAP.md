# Roadmap: DocSift (SIF)

## Milestones

- ✅ **v1.0 MVP — qmd 功能对等的本地混合搜索引擎** — Phases 1-10.1 (shipped 2026-11-07)
- ✅ **v1.1 Live Index and Search Quality** — Phases 11-16.1 (shipped 2026-11-12)
- ✅ **v1.2 Search Precision and Agent Experience** — Phases 17-24 (shipped 2026-11-18)

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

<details>
<summary>✅ v1.2 Search Precision and Agent Experience (Phases 17-24) — SHIPPED 2026-11-18</summary>

**Goal:** 让搜索精准可控（元数据过滤 + 正确性修复）、让 MCP 达到 2026 生态就绪（SDK v2 + agent 包装）、让质量提升有 held-out 证据（个人语料评测 + Harrier 评估），并补齐分发与 CI 缺口。

- [x] Phase 17: Engineering Foundation (CI Matrix + Hygiene + PyPI) (9/9 plans) — completed 2026-11-14
- [x] Phase 18: Quality Instrument (Personal Bench + rapidfuzz DYM) (4/4 plans) — completed 2026-11-15
- [x] Phase 19: Search Correctness (9/9 plans) — completed 2026-11-15
- [x] Phase 20: Metadata Filtering + Discovery (5/5 plans) — completed 2026-11-15
- [x] Phase 21: Scale, Maintenance + Embedder Identity (8/8 plans) — completed 2026-11-16
- [x] Phase 22: MCP SDK v2 Modernization + Agent Packaging (7/7 plans) — completed 2026-11-16
- [x] Phase 23: Harrier Gated Evaluation (6/6 plans) — completed 2026-11-16
- [x] Phase 24: Tuning + Models UX + Install Docs (7/7 plans) — completed 2026-11-18

Full detail: `.planning/milestones/v1.2-ROADMAP.md`

</details>

---
*Roadmap updated 2026-11-18 after the v1.2 milestone close. Phase numbering continues in the next milestone (no reset).*
