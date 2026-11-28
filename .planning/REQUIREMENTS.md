# Requirements: DocSift (SIF) — v1.3

**Defined:** 2026-11-27
**Milestone:** v1.3 Anchor-Augmented Retrieval Evidence
**Core Value:** 用户可以在自己的笔记和文档库中，用自然语言快速、准确地找到需要的信息——无论关键词是否匹配。

**Scope decision (user, 2026-11-27):** v1.3 只做 LLM Anchor；Web UI 推迟 v1.4。`PROJECT.md` 的 `Web UI` 与 `chat-with-notes / ask` Out of Scope 条款不反转。

**Research basis (existing, no re-research needed):** `.planning/research/UI-FRONTEND.md`、`/Users/forrest/Downloads/SIF-LLM-Anchor-Implementation-Guide.md`、`.planning/v1.3-ui-anchor-milestone-research.md`、2026-11-27 用 ego lite 核实的 ModelScope `LiquidAI/LFM3-1.7B-GGUF` 文件清单 / SHA256 / chat template / `LICENSE` 全文，以及当前 `src/sif` 代码勘察。

## v1.3 Requirements

### Spike & Feasibility

- [x] **SPK-01**: 团队能用 SIF 锁定的 `llama-cpp-python` 加载 `LFM3-1.7B-Q4_K_M.gguf` 并确认 `lfm3` 架构可推理；不兼容时记录升级或外部 `llama-server` 退路及其对现有 GGUF embed/rerank 路径的影响
- [x] **SPK-02**: 团队能用固定/规则锚点在现有 fixture 上跑 `lex:` → `anchor:` 配对对比，产出可复现的方向性信号判定与 delta 表
- [x] **SPK-03**: 无方向性信号时里程碑可止损归档假设，不投入后续阶段，且不留下未提交的半成品代码

### Anchor Retrieval Arm

- [ ] **ANC-01**: 用户可用 `anchor:` 前缀或 `--anchor` 触发锚点增强 BM25；不使用时零构造、零模型加载、零成本
- [x] **ANC-02**: 锚点仅注入 BM25 腿并 prepend 到查询；snippet 与 highlight 仍使用原始查询
- [x] **ANC-03**: `SearchType.ANCHOR`、`SearchOptions.anchor_terms` 与两处前缀映射（`search/hybrid.py` / `mcp/backend.py`）同步，且 settings 不绕过 `SearchOptions`
- [x] **ANC-04**: `hybrid+anchor` 仅作为诊断臂，默认关闭，不替换默认 RRF 的 BM25 腿
- [ ] **ANC-05**: 词表守卫可作为独立 A/B 开关，丢弃 FTS 词表外的锚点；默认行为、对论文的偏离与影响均有记录

### Generator & Cache

- [x] **GEN-01**: 锚点生成使用冻结 prompt（带版本号）、greedy / temperature 0、每行一个术语、最多 10 个、去重，且模型与 prompt revision 在评测前冻结
- [x] **GEN-02**: 同一 query + model + prompt version 命中缓存后不再调用生成器；`bench --sweep` 的 N 条查询只生成 N 次而非 45N 次
- [x] **GEN-03**: 生成失败或超时时 fail-open 回退原查询，不产生重试风暴，且用户可见失败原因
- [x] **GEN-04**: 默认本地 GGUF；远程 OpenAI-compatible 后端仅 opt-in，并明确披露查询文本外发

### Evidence & Gates

- [ ] **EVL-01**: `lex` / `anchor` / `hybrid` / `hybrid+anchor` 四臂可在同一 fixture 上通过 `search_fn` 注入评测
- [ ] **EVL-02**: 新增 `Recall@10`，并报告 `vec:` + anchor 诊断臂的 gain gap
- [ ] **EVL-03**: 报告 paired delta、10,000 次 bootstrap 95% CI、N / `1/N` noise floor 与 helped-hurt-unchanged 计数
- [ ] **EVL-04**: 报告 per-leg × per-language、p50/p95 延迟、生成调用数与缓存命中率
- [ ] **EVL-05**: 只有 tuning 排名 + held-out 胜出（0.01 tie rule 且 CI 排除 0）才讨论升默认；否则记录 `keep-default` 且默认值不变

### Contract & Safety

- [x] **CTR-01**: MCP 7 工具、5 份 wire goldens 与 `QueryInput` 不变；不新增 MCP `anchor` 请求字段
- [x] **CTR-02**: 不新增 runtime 依赖；`test_packaging.py` 冻结的 13 项核心依赖不变
- [ ] **CTR-03**: LFM3 GGUF 不打进 wheel/sdist；`LFM Open License v1.0` 的 $10M 营收阈值与再分发义务写入用户文档与 Key Decisions
- [x] **CTR-04**: 新增 Settings / CLI 通过 `make docs-generate` 与 docs CI diff gate；新增 `src/sif` Python 代码保持 ≥90% coverage；8-cell CI 全绿

## v1.4+ Requirements

Deferred to future release. Tracked but not in current roadmap.

### Browser Surface

- **UI-01**: 用户可启动 `sif serve` 并在浏览器完成只读搜索、查看文档与 status/metadata（需先出静态 HTML 多方案并完成 `PROJECT.md` Out of Scope 反转）
- **UI-02**: 可写 UI / 服务层抽取 / job 层（依赖真实 DB 特征测试，独立立项）

### Anchor Extensions

- **ANC-F1**: 确定性锚点基线升级为默认后端（需在 v1.3 证据上再次 held-out 验证）
- **ANC-F2**: Qwen3-8B 级对照臂或 MCP `anchor` 请求字段（若需要，单列契约变更阶段）
- **ANC-F3**: `hybrid+anchor` 升默认（仅在 v1.3 held-out 明确胜出后）

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Web UI / REST / `sif serve` | 用户拍板推迟 v1.4；`PROJECT.md` Out of Scope 未反转；两者零功能依赖 |
| 可写 UI、Click 服务层抽取、job registry、SSE | 只读 MVP 尚需范围评审；抽服务层是真正的高风险项，独立立项 |
| chat-with-notes / `ask` / 答案合成 | MCP 消费者本身就是 chat 层；投资引用级检索而非问答（既有 Out of Scope） |
| 自动查询路由 / LLM judge router | 论文路由器 AUROC 0.47–0.54、lockbox +0.005 区间覆盖 0；不投入 |
| 改默认 embedder、改 RRF 权重、改 BM25 索引粒度 | BM25 已 document-level，与论文公平基线一致；v1.2 的 keep 决策仍有效 |
| 改造 `expand:` 的 embedding PRF | 论文证明 RM3 / embedding PRF 降低 BM25；增益来自 LLM 精确术语，不是 PRF |
| `hybrid+anchor` 默认化 | v1.3 的定位是可证伪的诊断臂，不是默认行为变更 |
| 远程 LLM 后端作为默认 | local-first；外发 + 计费 + 延迟，仅 opt-in 对照 |
| 把 GGUF 打进 wheel/sdist | `lfm1.0` 第 4 条再分发义务 + 1.10 GB 体积不现实 |
| 122B / 31B 级模型、bge reranker 默认化 | 资源跃升一个数量级，违背 local-first；v1.2 已记录 keep 决策 |
| SPA + Node 构建链、多用户/LAN、cookie 会话 | UI 未立项；本地单用户定位不变 |
| ANN / semantic chunking / PDF-HTML-EPUB 解析 | 既有 Out of Scope，v1.3 不重新打开 |
| 把论文数值（+0.11–0.19 nDCG、1.5 s/query、158 查询）当成 SIF 承诺 | 代码搜索基准不可迁移到个人 Markdown 笔记；必须本机实测 |

## Traceability

Which phases cover which requirements. Populated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SPK-01 | Phase 25 | Complete |
| SPK-02 | Phase 25 | Complete |
| SPK-03 | Phase 25 | Complete |
| CTR-01 | Phase 25 | Complete |
| CTR-02 | Phase 25 | Complete |
| ANC-01 | Phase 26 | Pending |
| ANC-02 | Phase 26 | Complete |
| ANC-03 | Phase 26 | Complete |
| ANC-04 | Phase 26 | Complete |
| ANC-05 | Phase 26 | Pending |
| GEN-01 | Phase 26 | Complete |
| GEN-02 | Phase 26 | Complete |
| GEN-03 | Phase 26 | Complete |
| GEN-04 | Phase 26 | Complete |
| CTR-03 | Phase 26 | Pending |
| CTR-04 | Phase 26 | Complete |
| EVL-01 | Phase 27 | Pending |
| EVL-02 | Phase 27 | Pending |
| EVL-03 | Phase 27 | Pending |
| EVL-04 | Phase 27 | Pending |
| EVL-05 | Phase 27 | Pending |

**Coverage:**
- v1.3 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0 ✓

---
*Requirements defined: 2026-11-27*
*Last updated: 2026-11-27 after milestone v1.3 start*
