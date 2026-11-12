# Milestone v1.1 — Project Summary

**Generated:** 2026-11-12
**Purpose:** Team onboarding and project review
**Milestone:** v1.1 — Live Index and Search Quality（2026-11-07 → 2026-11-12）

---

## 1. Project Overview

**DocSift（包名 `sif`）** 是一个 Python 3.10+ 的本地混合搜索引擎，面向个人知识库：索引 Markdown 笔记与文档，提供 BM25 关键词搜索、sqlite-vec 语义向量搜索、RRF 混合排序，以及可选的 LLM 重排序与查询扩展。所有数据保存在本地 SQLite，对外提供 Click CLI（`sif`）与 MCP 服务器（stdio + Streamable HTTP）两种入口。

**核心价值：** 用户可以在自己的笔记和文档库中，用自然语言快速、准确地找到需要的信息——无论关键词是否匹配。

**v1.1 目标：** 让索引从手动 `sif index update` 变为自动常新（Live Index），并让搜索质量可配置、可量化、持续可调（Search Quality）。

**v1.1 交付：**

- 并发安全的 SQLite 基座：统一连接工厂（busy_timeout → WAL → synchronous）、`BEGIN IMMEDIATE` 写事务、内核 flock 单写者仲裁。
- 四种 Live Index 宿主：`sif watch` 前台、MCP 内嵌刷新、`--detach` 守护进程、launchd/systemd 服务安装。
- 搜索前 stat 漂移刷新，以及无守护进程时的向量滞后 staleness 标记。
- 可配置 RRF 权重、did-you-mean/历史建议、`sif suggest`。
- bench 指标扩充（nDCG@10、Hit@10、p50/p95）与 45 配置扫描；held-out 结论：默认值不变。
- 16.1 技术债收口：CLI 错误边界、缓存 TTL instant 比较、embedding cache 工厂委派、公开 reconcile-enqueue API。

---

## 2. Architecture & Technical Decisions

- **统一 SQLite 连接工厂**（`src/sif/database/factory.py`）
  - **Why:** CLI、MCP、watch 三个宿主必须共享同一套 PRAGMA 与事务语义，避免 "database is locked"。
  - **Phase:** 11

- **内核 flock 单写者仲裁**（`src/sif/database/locking.py`）
  - **Why:** flock 在进程死亡时由内核释放，语义上不可能 stale；优于 PID 文件仲裁。
  - **Phase:** 11

- **`IncrementalIndexer` 作为唯一 per-file 更新路径**
  - **Why:** `index update`、watch、drift refresh 共用同一循环；每个文件一个短 `BEGIN IMMEDIATE` 事务，失败可恢复。
  - **Phase:** 11

- **Watch 管线：per-burst flock + per-path 定向更新**
  - **Why:** watch 空闲时不持锁；`update_paths` 成本正比于变更规模，避免每次全量扫描。
  - **Phase:** 12

- **单一排除谓词 `FileScanner.matches`**
  - **Why:** 扫描与 watch 同源，LIVE-04 一致性由构造保证；内置编辑器噪声模式。
  - **Phase:** 12

- **missing-root 防护在共享核心**
  - **Why:** 根目录消失不得被解读为“全部文件删除”；两条更新路径都有回归测试。
  - **Phase:** 12

- **所有 watch 宿主共享一个 host body**
  - **Why:** 前台、daemon、MCP 内嵌复用同一启动 reconcile、shutdown、WAL checkpoint 逻辑。
  - **Phase:** 13

- **搜索前 drift refresh + 派生 staleness**
  - **Why:** 没有 watch 时搜索仍能找到刚编辑的文件；staleness 从 `document_embeddings` 派生，不维护易说谎的持久标记。
  - **Phase:** 14

- **加权 RRF，默认逐字节不变**
  - **Why:** `rrf_k`/`bm25_weight`/`vector_weight` 可配置，但默认 60/1.0/1.0 与旧行为完全一致。
  - **Phase:** 15

- **DYM 与查询历史基于 FTS vocab + `query_log`**
  - **Why:** 索引词表与本地历史足以提供建议，不引入外部依赖或 LLM 调用。
  - **Phase:** 15

- **Reranker 显式 opt-in + 候选上限/相对阈值**
  - **Why:** 保持默认查询的低延迟快路径；`SIF_RERANK_ENABLED`/`--rerank` 才加载模型。
  - **Phase:** 16

- **held-out 论证默认值**
  - **Why:** 调优集胜出但 held-out 差异 < 0.01 时判定“不改变”，避免过拟合噪声。
  - **Phase:** 16

- **CLI 共享 DB 错误边界**
  - **Why:** 可预见失败统一转为带修复提示的 `ClickException`；意外异常仍保留完整 traceback。
  - **Phase:** 16.1

---

## 3. Phases Delivered

| Phase | Name | Status | One-Liner |
|-------|------|--------|-----------|
| 11 | Live-Index Foundation (Concurrent DB + Incremental Core) | ✅ Complete | 连接工厂 + flock + `IncrementalIndexer`，退役重复索引循环 |
| 12 | `sif watch` Foreground MVP | ✅ Complete | 防抖、原子保存/移动、临时文件排除、分层 `--embed`、missing-root 防护 |
| 13 | Watch Everywhere (MCP-Embedded Refresh + Background Daemon) | ✅ Complete | `SIF_MCP_WATCH`、`--detach`、launchd/systemd 服务安装 |
| 14 | Freshness Floor (Pre-Command Refresh + Staleness Marking) | ✅ Complete | 搜索前 stat 漂移刷新 + 五格式 staleness 标记 |
| 15 | Search Quality Configuration (Weights + Suggestions) | ✅ Complete | 加权 RRF、DYM/历史建议、`sif suggest` |
| 16 | Bench Expansion + Reranker Tuning | ✅ Complete | nDCG/Hit/延迟指标、56 条分级查询、45 配置扫描、held-out 默认锁定 |
| 16.1 | Address tech debt (CLI errors + cache TTL + enqueue API) | ✅ Complete | 共享 CLI 错误边界、instant TTL、cache 工厂委派、公开 reconcile API |

---

## 4. Requirements Coverage

**21/21 v1.1 requirements satisfied**（审计 2026-11-12，verdict `tech_debt` — 无 critical blocker）。

### Live Index（11/11）

- ✅ LIVE-01 watch 自动增量重索引
- ✅ LIVE-02 保存风暴防抖合并
- ✅ LIVE-03 原子保存/移动处理
- ✅ LIVE-04 临时文件一致排除
- ✅ LIVE-05 默认 BM25 深度，`--embed` opt-in
- ✅ LIVE-06 并发读写零锁错
- ✅ LIVE-07 flock 单写者仲裁
- ✅ LIVE-08 MCP 内嵌刷新
- ✅ LIVE-09 `--detach` + 服务安装
- ✅ LIVE-10 搜索前漂移刷新
- ✅ LIVE-11 missing-root 防护

### Search Quality（6/6）

- ✅ QUAL-01 `rrf_k`/权重可配置，默认不变
- ✅ QUAL-02 Did-you-mean 建议
- ✅ QUAL-03 查询历史建议
- ✅ QUAL-04 `sif suggest`
- ✅ QUAL-05 reranker 上限/阈值可配
- ✅ QUAL-06 向量滞后 staleness 标记

### Evaluation（4/4）

- ✅ EVAL-01 nDCG@k/Hit@k/p50-p95
- ✅ EVAL-02 ≥50 条分级查询 + tuning/held-out 分割
- ✅ EVAL-03 `--sweep` 网格扫描
- ✅ EVAL-04 held-out 论证默认值

**Integration:** 24/24 cross-phase seams wired，12/12 E2E flows complete（审计时 HEAD）。

---

## 5. Key Decisions Log

| Decision | Rationale | Phase |
|----------|-----------|-------|
| 统一连接工厂（busy_timeout→WAL→synchronous + `BEGIN IMMEDIATE`） | 三宿主共享一套语义，消除锁错 | 11 |
| flock 而非 PID 文件做写者仲裁 | 内核释放，无 stale 锁风险 | 11 |
| `IncrementalIndexer` 单一更新路径 | 消除第三份重复循环，行为可证明等价 | 11 |
| per-burst flock + per-path 更新 | watch 空闲不持锁，成本随变更规模 | 12 |
| 扫描/watch 共用一个排除谓词 | 一致性由构造保证 | 12 |
| missing-root 防护放在共享核心 | 同时修复 `update_cmd` 潜在全量删除 | 12 |
| 四种宿主共享 host body | 启动 reconcile/shutdown/checkpoint 只有一份 | 13 |
| staleness 派生而非持久标记 | 避免多写路径维护的“说谎标记” | 14 |
| 加权 RRF 默认逐字节不变 | 可调但不改变既有用户行为 | 15 |
| rerank 显式 opt-in | 默认查询保持低延迟 | 16 |
| 0.01 噪声内不判胜 | 防止 tuning 集过拟合 | 16 |
| 共享 CLI DB 错误边界 + AST 门禁 | 统一修复提示，结构上禁止回归 | 16.1 |

---

## 6. Tech Debt & Deferred Items

### 已在 v1.1.1 收口

- 补跑 `/gsd-validate-phase 12` 与 `/gsd-secure-phase 16`；SECURITY 覆盖补齐。
- Phase 16 真实模型 held-out 证据行已记录（WINDOWS id 10 关闭）。
- Broken Windows ledger 清理至 **0 open / 3 waived / 7 fixed**。
- BM25 collection-filter 查询计划修复（20k 文档探针 72.7s → 0.03s）。
- console-script daemon 身份识别、`watch --embed` 启动缺向量修复。
- 10 个此前未被运行时读取的 `SIF_` 设置已接线：`debug`、`log_level`、`max_tokens`、`batch_size`、`chunk_size`、`chunk_overlap`、`default_search_type`、`default_limit`、`mcp_host`、`mcp_port`、`mcp_transport`。

### 仍然保留

- `compute_rrf_score`（`src/sif/search/rrf.py`）为孤儿导出，零调用方，可删除。
- Phase 15/16 的若干 info findings（IN-01、IN-03..IN-07 等），不否决任何成功标准。
- FUTR-01 spellfix1、FUTR-02 LLM 辅助调权、FUTR-03 symspellpy 备胎，均推迟到 v2+。
- 4 个 `<!-- VERIFY: -->` 标记：`make install-dev`/`make pre-commit` 引用仓库中不存在的 `.pre-commit-config.yaml`。
- 5 份历史报告已归档到 `.planning/milestones/`，不再作为现行文档维护。

### 回顾经验

- Tracer-first：每个 phase 先用端到端切片证明，再扩展。
- 确定性测试：two-writer 子进程、real-FS e2e、固定时区 TTL 回归，避免 wall-clock 竞态。
- 诚实的 held-out 门禁：0.01 tie rule + committed snapshot 阻止默认值随噪声移动。
- 文档改动算 covered-input 变更：在最终验证前批量完成，而不是之后。

---

## 7. Getting Started

- **安装：** `pip install -e ".[dev]"`（开发）；用户安装 `pip install docsif[all]`。
- **运行：** `python -m sif.cli.main --help` 或 `sif --help`。
- **质量门禁：**
  ```bash
  ruff check src tests
  ruff format --check src tests
  ty check src/sif
  pytest
  ```
- **关键目录：**
  - `src/sif/cli/` — Click 命令入口（watch、search、index、mcp、suggest）
  - `src/sif/mcp/` — MCP server、handlers、transports
  - `src/sif/search/` — BM25、vector、hybrid/RRF、rerank、suggest、benchmark
  - `src/sif/indexing/` — scanner、parser、chunker、incremental、watcher、drift
  - `src/sif/database/` — factory、schema、repositories、locking
  - `src/sif/embedding/` — embedders、factory、manager、cache
  - `tests/` — unit、integration、e2e、bench fixtures
- **先看哪里：**
  - `src/sif/database/factory.py` — 连接与事务契约
  - `src/sif/indexing/incremental.py` — 唯一 per-file 更新路径
  - `src/sif/search/hybrid.py` — 混合检索与 pipeline
  - `src/sif/cli/commands/watch.py` — 四宿主共享的 watch body
  - `docs/architecture.md`、`docs/benchmarking.md` — 架构与评测说明

---

## Stats

- **Timeline:** 2026-11-07 → 2026-11-12（5 天）
- **Phases:** 7 / 7 complete（11–16.1）
- **Plans:** 27 · **Tasks:** 67
- **Commits (tag-to-tag v1.0.1..v1.1):** 1,155
- **Files changed:** 526（+62,928 / −4,052；含 planning 产物）
- **Contributors (git log):** AI, Tao Zhang
- **Quality gate (current HEAD):** 1,628 passed, 1 skipped @ 95.06% coverage; ruff/format/ty clean
- **Docs:** 19 份现行 Markdown 全部通过事实核验；5 份历史报告已归档
