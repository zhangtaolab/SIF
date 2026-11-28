# Roadmap: DocSift (SIF)

## Milestones

- ✅ **v1.0 MVP — qmd 功能对等的本地混合搜索引擎** — Phases 1-10.1 (shipped 2026-11-07)
- ✅ **v1.1 Live Index and Search Quality** — Phases 11-16.1 (shipped 2026-11-12)
- ✅ **v1.2 Search Precision and Agent Experience** — Phases 17-24 (shipped 2026-11-18)
- [ ] **v1.3 Anchor-Augmented Retrieval Evidence** — Phases 25-27 (in progress)

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

<details>
<summary>🚧 v1.3 Anchor-Augmented Retrieval Evidence (Phases 25-27) — IN PROGRESS (started 2026-11-27)</summary>

**Goal:** 在不破坏 CLI / MCP / 默认检索行为与 local-first 约束的前提下，新增默认关闭、可缓存、可证伪的 `anchor:` 检索臂，并由 SIF 自己的 held-out 证据决定是否升默认；`keep-default` 是有效交付。

- [x] **Phase 25: Contract Freeze & Feasibility Spike** — SPK-01, SPK-02, SPK-03, CTR-01, CTR-02 (completed 2026-11-28)
- [x] **Phase 26: Anchor Arm + Deterministic Cache** — ANC-01, ANC-02, ANC-03, ANC-04, ANC-05, GEN-01, GEN-02, GEN-03, GEN-04, CTR-03, CTR-04 (completed 2026-11-28) — ⚠ CTR-04 的 8-cell CI 是 push 后外部门禁，**尚未确认**（`dev` 领先 `origin/dev` 且未推送）；`26-UAT.md` test 24 = `blocked`，UAT 状态 `partial` —— CI 绿之前 Phase 26 不算完全签收
- [ ] **Phase 27: Evidence Gate & Verdict** — EVL-01, EVL-02, EVL-03, EVL-04, EVL-05

Full detail: `.planning/REQUIREMENTS.md` (v1.3 Requirements + Traceability)

</details>

## Phase Details

### Phase 25: Contract Freeze & Feasibility Spike

**Requirements**: SPK-01, SPK-02, SPK-03, CTR-01, CTR-02

**Goal:** 在写任何新代码前证明 `llama.cpp` 能加载 `lfm3` 架构、确定性锚点有方向性信号，并冻结 MCP/打包契约。
**First plan (MUST):** 兼容性 + 信号 spike（`Llama(model_path=LFM3-1.7B-Q4_K_M.gguf)` 加载 + 固定/规则锚点配对对比）。
**Kill criterion:** 无方向性信号即归档假设、不投 Phase 26/27、不留半成品代码。
**Success Criteria** (what must be TRUE):
  1. 团队能用锁定的 `llama-cpp-python` 让 `Llama(model_path=LFM3-1.7B-Q4_K_M.gguf)` 成功加载并生成一次；若 `lfm3` 不兼容，则升级或外部 `llama-server` 退路及其对现有 GGUF embed/rerank 路径的影响被记录为可复核结论。
  2. 一份可复现的 `lex:` → `anchor:` 配对 delta 表给出明确的方向性信号判定（有/无），任何人用固定种子重跑得到相同结论。
  3. MCP 5 份 wire goldens 与 `test_packaging.py` 逐字节未变，7 工具与 `QueryInput`（不新增 `anchor` 请求字段）契约冻结状态可被核对。
  4. 当判定为「无方向性信号」时，止损被记录为归档假设、Phase 26/27 未启动，工作树不留任何半成品代码。

**Plans:** 2/2 plans complete
**Wave 1**
- [x] 25-01-PLAN.md — 兼容性 + 信号 spike（用户提供的 GGUF 路径、锁定版 vs 隔离升级版加载/生成、query-only 锚点配对 delta）

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 25-02-PLAN.md — 契约冻结证明、权威证据三件套、stop/go 状态记录

### Phase 26: Anchor Arm + Deterministic Cache

**Requirements**: ANC-01, ANC-02, ANC-03, ANC-04, ANC-05, GEN-01, GEN-02, GEN-03, GEN-04, CTR-03, CTR-04

**Goal:** 交付默认关闭、可缓存、失败回退的 `anchor:` 检索臂与本地可选生成器，不新增 runtime 依赖、不动 MCP schema。
**Success Criteria** (what must be TRUE):
  1. 用户可用 `sif search query --anchor ...` 或 `anchor:` 前缀触发锚点增强 BM25（锚点仅注入 BM25 腿、snippet/highlight 仍用原始查询）；关闭 flag 时行为与 v1.2.5 逐字节一致、零构造零模型加载。
  2. 重复同一 query 产生零次生成器调用，45 配置 sweep 的 N 条查询只产生 N 次生成调用（冻结 prompt / greedy / ≤10 术语 / 去重，评测前冻结）。
  3. 生成器超时或失败时返回原始 query 的结果、无重试风暴，用户能看到失败原因；fail-open 回退可被复现。
  4. 除非显式 opt-in 远程后端，否则不产生任何外部请求；远程 opt-in 时明确披露查询文本外发，词表守卫可作为独立 A/B 开关。
  5. 全量 pytest ≥90% coverage、`make docs-generate` diff 为零、8-cell CI 全绿；LFM3 GGUF 不打进 wheel/sdist，`LFM Open License v1.0` 的 $10M 营收阈值与再分发义务写入用户文档与 Key Decisions。
     - 本地部分已验证：3367 passed / 1 skipped / 94.18% coverage，`make docs-generate` 零 diff，3 条 GGUF 静态守卫通过，license 与 Key Decision 已落文档（`26-VERIFICATION.md` truth 5）。
     - ⚠ **8-cell CI 未确认**：由 `.github/workflows/test-matrix.yml` 在 push 后运行（2 OS × 4 Python，`--extra embed`），本地无法执行。CI 绿之前本条为 `DEFERRED`，不是「已验证」。

**Plans:** 4/4 plans complete
**Wave 1**
- [x] 26-01-PLAN.md — 锚点检索基底：`SearchType.ANCHOR` + `SearchOptions.anchor_terms` + 规则锚点 + BM25 OR 注入 + 共享前缀路由（ANC-01..04）

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 26-02-PLAN.md — 可选生成器与确定性缓存：冻结 prompt、本地 GGUF/远程 opt-in、`llm_cache` 复用、fail-open 与预算、SIF_ANCHOR_* 配置（GEN-01..04, CTR-04）

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 26-03-PLAN.md — `sif search query --anchor`、route-first 零模型、`--explain` 成本元数据与 CLI 文档（ANC-01, GEN-03, CTR-04）

**Wave 4** *(blocked on Wave 3 completion)*
- [x] 26-04-PLAN.md — 词表守卫 A/B、LFM 许可/无 GGUF 打包守卫、本地全量门禁（ANC-05, CTR-03, CTR-04）

### Phase 27: Evidence Gate & Verdict

**Requirements**: EVL-01, EVL-02, EVL-03, EVL-04, EVL-05

**Goal:** 用四臂评测 + 配对 bootstrap + held-out 门禁产出 adopt/keep-default verdict；`keep-default` 是有效交付。
**Success Criteria** (what must be TRUE):
  1. 团队能在同一 fixture 上通过 `search_fn` 注入评测 `lex` / `anchor` / `hybrid` / `hybrid+anchor` 四臂，报告含 nDCG@10 与新增 Recall@10、`vec:` + anchor 诊断臂 gain gap。
  2. 报告给出 paired delta、10,000 次 bootstrap 95% CI、N / `1/N` noise floor 与 helped-hurt-unchanged 计数，以及 per-leg × per-language、p50/p95 延迟、生成器调用数与缓存命中率。
  3. 报告产出明确的 `adopt` 或 `keep-default` verdict；只有 tuning 排名 + held-out 胜出（0.01 tie rule 且 CI 排除 0）才讨论升默认，`keep-default` 时默认检索行为与 v1.2.5 完全一致、默认值不变仍被接受为交付。
  4. 文档明确论文数值（+0.11–0.19 nDCG 等）不可迁移到个人 Markdown 笔记、必须本机实测，并记录 `LFM Open License v1.0` 约束。


---
*Roadmap updated 2026-11-27 after starting milestone v1.3 (Anchor-Augmented Retrieval Evidence). Phase numbering continues from v1.2's Phase 24 — no reset.*
