# Requirements: DocSift/SIF

**Defined:** 2026-11-07
**Milestone:** v1.1 — Live Index and Search Quality
**Core Value:** 用户可以在自己的笔记和文档库中，用自然语言快速、准确地找到需要的信息——无论关键词是否匹配。

## v1.1 Requirements

Requirements for milestone v1.1. Each maps to roadmap phases (numbering continues from v1.0's 11 phases).

### Live Index

- [x] **LIVE-01**: 运行 `sif watch` 后，collection 内文件增/改/删自动增量重索引，无需手动 `sif index update`
- [x] **LIVE-02**: 编辑器保存风暴（单次保存 2-5 事件）防抖合并为一次索引操作
- [x] **LIVE-03**: macOS 原子保存（rename 链）与文件移动/重命名正确处理，不误删不重建
- [x] **LIVE-04**: 临时文件（`.swp`/`.sb-*`/`4913`/`.DS_Store` 等）与 scanner `ignore_patterns` 一致排除
- [x] **LIVE-05**: 默认仅更新 BM25/FTS；`--embed` 显式开启向量更新（embed 永不作为后台默认）
- [x] **LIVE-06**: watch 写入与 CLI/MCP 并发读共存，零 "database is locked"（WAL + busy_timeout + BEGIN IMMEDIATE）
- [x] **LIVE-07**: flock 单写者仲裁，多 watch 形态并存不重复 embed
- [x] **LIVE-08**: `SIF_MCP_WATCH=1` 启用 MCP server 内嵌刷新，查询不被事件风暴阻塞
- [x] **LIVE-09**: `sif watch --detach`（PID/stop/status）+ launchd/systemd 服务安装
- [ ] **LIVE-10**: 未运行 watch 时，搜索命令前 stat 漂移检测自动刷新（有上限，干净时零成本）
- [x] **LIVE-11**: collection 根目录消失不解读为全量删除（missing-root 防护）

### Search Quality

- [ ] **QUAL-01**: `rrf_k`/`bm25_weight`/`vector_weight` 经 `SIF_` 设置 + per-query 参数配置；默认行为逐字节不变（k=60 等权）
- [ ] **QUAL-02**: 零/少结果时给出 "Did you mean" 建议（词表 + 历史，仅建议不静默改写）
- [ ] **QUAL-03**: 基于查询历史的建议（query_log 本地存储）
- [ ] **QUAL-04**: `sif suggest` 命令（prefix 补全 + DYM + 历史）
- [ ] **QUAL-05**: reranker 候选上限（CPU 10-20）+ 相对阈值（≥top1×α）可配；skip-rerank 快路径保持交互延迟
- **QUAL-06**: 分层更新深度下，向量滞后的搜索结果标记 staleness 状态

### Evaluation

- [ ] **EVAL-01**: `sif bench` 输出 nDCG@k、Hit@k、p50/p95 延迟
- [ ] **EVAL-02**: 基准 fixture ≥50 条分类查询（关键词/同义改写/多语言/竞争笔记）+ tuning/held-out 分割
- [ ] **EVAL-03**: `sif bench --sweep` 网格扫描权重/k，噪声内差异（<0.01）不判胜
- [ ] **EVAL-04**: 出厂默认权重经 held-out 数据论证，不因调优集过拟合而改变

## Future Requirements (v2+)

- **FUTR-01**: spellfix1 加速 did-you-mean（sqlite 可加载扩展，可移植性受限）
- **FUTR-02**: LLM 辅助权重调优
- **FUTR-03**: symspellpy 作为 DYM 质量备胎（仅当 UAT 证明 difflib 不足时引入新依赖）

## Out of Scope

| Feature | Reason |
|---------|--------|
| 服务器/集群部署 | 本地单用户工具定位；研究列为 anti-feature |
| match-time 容错（搜索时拼写纠正） | 错误层级：应在建议层解决；index bloat |
| 静默自动改写查询 | UX 惯例：仅建议（Meilisearch/Typesense 一致） |
| auto-embed 作为后台默认 | embed 慢 100-1000×，且远程 API 有计费风险，必须显式 opt-in |
| watcher 作为唯一真相源（无 backstop） | 内核事件队列会溢出；pre-command 检测就是 backstop |
| 自定义 lockfile 方案 | flock 语义上不可能 stale，优先于 PID 文件方案 |
| DYM 路径中的 LLM 调用 | 本地零依赖原则；延迟不可控 |
| 监控 collection 根目录之外 | 范围界定与资源安全 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| LIVE-01 | Phase 12 | Complete |
| LIVE-02 | Phase 12 | Complete |
| LIVE-03 | Phase 12 | Complete |
| LIVE-04 | Phase 12 | Complete |
| LIVE-05 | Phase 12 | Complete |
| LIVE-06 | Phase 11 | Complete |
| LIVE-07 | Phase 11 | Complete |
| LIVE-08 | Phase 13 | Complete |
| LIVE-09 | Phase 13 | Complete |
| LIVE-10 | Phase 14 | Pending |
| LIVE-11 | Phase 12 | Complete |
| QUAL-01 | Phase 15 | Pending |
| QUAL-02 | Phase 15 | Pending |
| QUAL-03 | Phase 15 | Pending |
| QUAL-04 | Phase 15 | Pending |
| QUAL-05 | Phase 16 | Pending |
| QUAL-06 | Phase 14 | Pending |
| EVAL-01 | Phase 16 | Pending |
| EVAL-02 | Phase 16 | Pending |
| EVAL-03 | Phase 16 | Pending |
| EVAL-04 | Phase 16 | Pending |

**Coverage:**
- v1.1 requirements: 21 total (11 LIVE + 6 QUAL + 4 EVAL; earlier count of 22 was a miscount — no requirement ID is missing)
- Mapped to phases: 21
- Unmapped: 0

---
*Requirements defined: 2026-11-07*
*Last updated: 2026-11-07 after v1.1 roadmap creation (traceability filled, 21/21 mapped)*
