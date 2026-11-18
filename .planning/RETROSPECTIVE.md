# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — MVP（qmd 功能对等的本地混合搜索引擎）

**Shipped:** 2026-11-07
**Phases:** 11 | **Plans:** 68 | **Tasks:** 112 | **Quick tasks:** 18

### What Was Built
- 可信的本地混合搜索引擎：BM25（FTS5 外部内容表 + 触发器同步）+ 向量（sqlite-vec,fail-fast）+ RRF 融合 + Qwen3 重排序/查询扩展，Click CLI 与 MCP 服务器（stdio + Streamable HTTP）双入口
- 可配置嵌入后端：sentence-transformers / GGUF(llama-cpp) / ModelScope / OpenAI 兼容（默认 Qwen3 系列,维度守护 + 缓存探测）
- 上下文系统（path/collection/global 三作用域）与路径规范化(别名解析、写入规范化、读取双侧匹配)
- 质量基线:1015 测试 @ 96.20%,`fail_under=90` 常驻门禁、零豁免行;ty 唯一类型检查器 0 诊断;docs 事实核验 512 声明 0 失败;CI 漂移门禁

### What Worked
- SDD 分层 + Repository/Protocol/Factory 模式让 11 个阶段可以在几乎无回归的情况下持续插入(05/07/08/09/10/10.1 均为后插)
- 质量门禁前置:fail_under=90 落地后,后续所有维护(ty 清债、get 修复、文档刷新)都套件全绿通过,零回归逃逸
- stale-verification 再生机制虽繁琐但可靠:四阶段(05/06/07/10.1)全部翻新,级联失效(06/07 被 10 的修复再度弄陈旧)也被指纹机制如实捕获
- 代码评审在里程碑收尾抓出 5 个真实 Critical(README 坏命令、生成器管道转义、版本依赖输出、get 内容 markup、表头 markup)——全部实测复现后修复

### What Was Inefficient
- 显示层 markup 完整性修了三次(05-10/05-11 context 表格、10.1 XML、v1.0 收尾 get 内容+表头)——同类缺陷应一次性全库扫清,而非每阶段撞一次
- docs CI 自 Phase 10 落地 fail_under 后恒红,直到里程碑收尾才被发现——门禁变更应立即跑一遍受影响的局部套件
- 版本号散布 6 处无同步机制(评审 WR-03,仍开放)
- 验证指纹的级联陈旧(修 A 阶段文件弄陈旧 B 阶段)在交叉覆盖集下产生两轮额外再生

### Patterns Established
- 用户内容永不经 Rich markup 渲染:内容 `markup=False`、表头 `escape()`、机器输出 XML 1.0 净化器——三例同构,已有回归测试锁定
- 生成器拥有的文档(cli-reference/configuration)只改生成器源 + `make docs-generate`,CI 漂移门禁兜底
- 测试侧也守资源契约:`contextlib.closing` 包裹裸 sqlite3 连接(全库 0 warning)
- optional 导入 None 回退是刻意的测试补丁目标:类型收窄在使用点(assert),不重构导入

### Key Lessons
1. 覆盖率门禁 + 零豁免一旦落地,后续一切维护的回归成本趋近于零——值得在 v1.x 前置
2. 跨阶段共享文件(显示层、CI、Makefile)的修复要按缺陷类全库横扫,不要按阶段纵切
3. 里程碑收尾时"审计→resolve 全部→验证全 fresh→归档"的顺序是对的:audit-open 的三项全部真修(CR-03 实测、ResourceWarning 清零、mypy 销账),不留 acknowledge

### Cost Observations
- 692 commits / 207 天(2026-04-14 → 2026-11-07);src 12.5K 行、tests 23.1K 行(测试:源 ≈ 1.8:1)
- 里程碑收尾日单会话完成:ty 清债 quick task、文档全量核验、版本 1.0.0、四阶段验证再生、5 个 Critical 修复、归档

## Milestone: v1.1 — Live Index and Search Quality

**Shipped:** 2026-11-12
**Phases:** 7 (11–16.1) | **Plans:** 27 | **Tasks:** 67

### What Was Built
- Concurrent-DB foundation: one connection factory (busy_timeout→WAL→synchronous + BEGIN IMMEDIATE) + kernel-flock single-writer arbitration; IncrementalIndexer as the one per-file update path.
- Live Index hosts: `sif watch` foreground, MCP-embedded (`SIF_MCP_WATCH`), detached daemon + launchd/systemd install; pre-command drift refresh + staleness marking.
- Search Quality: configurable RRF weights (byte-identical defaults), did-you-mean + history + `sif suggest`, bench expansion + reranker tuning (held-out verdict: defaults unchanged).
- Tech debt (16.1): convention-wide CLI error boundary, instant-compare cache TTL, embedding-cache factory delegation, public reconcile-enqueue API.

### What Worked
- Tracer-first planning: each phase led with an end-to-end slice proven before expansion (11→watch, 15→weighted fusion, 16.1→error boundary).
- Deterministic, time-bounded tests: two-writer subprocess proofs, real-FS e2e with deadline polls, fixed-TZ TTL regressions — no wall-clock races.
- Honest held-out gate: the 0.01 tie rule and committed snapshot kept defaults from moving on tuning-set noise.
- Ledger-closure culture: dispositions carried evidence, and re-verification at HEAD exposed a real cache-cleanup regression (WR-01) that was fixed and re-proven.

### What Was Inefficient
- Re-verification churn: editing covered docs (benchmarking.md, UAT) re-staled phases repeatedly, requiring multiple verifier passes near close.
- The real-model bench hit MPS/joblib deadlocks and a cache-dir mismatch; the robust path was an in-process batched single-threaded evaluation rather than the CLI bench against a rebuilt index.
- Phase 16.1's broad init_schema sweep touched many files, which invalidated several prior-phase fingerprints at once.

### Patterns Established
- One shared boundary/open helper for a convention-wide class of fixes (AST gate forbids regressions).
- Derived signals over stored flags (staleness = no embeddings, not a maintained column).
- Public narrow-intent APIs over private queue reach-ins (enqueue_reconcile).
- Factory-single-sourcing for all DB pragmas; delegating caches to it rather than copying the recipe.

### Key Lessons
- Fix driven by a re-review during close is worth the extra verification pass — WR-01 would have shipped a cleanup-aborting bug.
- Doc edits count as covered-input changes; batch them before the final verification, not after.
- Model-runtime deadlocks (MPS + joblib) are solved by batching + single-thread + explicit device, not by retrying.

### Cost Observations
- Model mix: orchestrator on the configured profile; subagents (researcher/planner/verifier/security/UI/executors) in fresh contexts.
- Sessions: one long continuous session spanning discuss→plan→execute→validate→secure→re-verify→close.
- Notable: the audit's `tech_debt` verdict drove a focused 16.1 phase plus four retroactive coverage runs; all closed before archiving.

## Milestone: v1.2 — Search Precision and Agent Experience

**Shipped:** 2026-11-18
**Phases:** 8 (17–24) | **Plans:** 55 | **Quick tasks:** 1

### What Was Built
- 工程基础：py3.10–3.13 × ubuntu/macos 8 格 CI 矩阵、Windows 降级 smoke（hc yoga）、trusted-publishing 的 `docsif` 发布流水线。
- 质量仪器：`sif eval --personal` known-item 评测（bias controls、saved run、bootstrap 噪声门、1/N 地板）、rapidfuzz did-you-mean。
- 搜索正确性：frontmatter-only 刷新、pre-fusion 去重、确定性分页、标题 FTS、单一 enrich 路径。
- 元数据过滤：qmd 17 操作符 AST（pre-RRF）、path/mtime 内置字段、类型化 kv + 回填、`metadata` 发现工具。
- 规模与身份：bounded staleness/contexts、`index vacuum`/backup、streaming embed、embedder identity + role-aware embed。
- MCP：官方 SDK v2（五 era）、七只读工具 + annotations/structuredContent、query pipeline 对等、daemon、plugin/skills、Registry manifest。
- 质量门禁证据：Harrier keep-qwen3、chunk keep-default、breadcrumb keep-breadcrumb-off——三个 held-out 决策全部带数字记录。
- 分发：`docsif` 1.2.0 上 TestPyPI + PyPI（tag `v1.2.0`）。

### What Worked
- Held-out 门禁 + 记录化 artifact：三次默认值决策都以 keep 收尾，没有一次靠感觉改默认。
- 指纹失效机制自动暴露跨阶段影响：修 `personal_bench` 一处，18/19/23/24 立即 stale，不靠人记得。
- 清单版本由 `_version.py` 单源 + 测试动态派生：bump 后 66 个 parity 测试直接证明 1.2.0 一致。
- 并行 verifier：四阶段重验在同一轮完成，且 23 的 27 个记录 gate 逐一重算 0 不一致。

### What Was Inefficient
- 两轮全里程碑重验：先是 17–24 的陈旧报告，后是 CI 修复（3 文件）再次弄陈旧 18/19/23/24——共享模块的修复应预算一次完整重验波。
- 版本 bump 放在收尾阶段，直接把 17/22/24 的验证打陈旧；bump 应在最终验证波之前完成。
- 本地 Python 3.13 掩盖了 3.10/3.11 的朴素求和差异：`0.010000000000000007` 只在 CI 暴露；边界规则不能依赖求和精度。
- 文档声称"已上架 Registry"而实际是 `blocked no-github-login`，属声明与事实漂移（已记录为 follow-up）。

### Patterns Established
- 跨版本确定性算术：`math.fsum` + 6 位 rounded 比较（`strictly_above_noise_floor`），地板平局永不胜出。
- 版本面单源 + 派生 parity 测试（server.json / plugin / marketplace / changelog）。
- 决策 artifact 的非适用分支：`default_flip: not-applicable` + `zero_delta_proof: not-applicable` 机器可读。
- 验证覆盖集指纹作为跨阶段失效引擎，修复即触发重验。

### Key Lessons
1. 共享模块修复要预期 N 个阶段 stale——先修复，再一次性跑完重验波，别在收尾前反复修。
2. 发布版本 bump 放在最后一次全量验证之前；否则 release-metadata 类阶段必然再跑一遍。
3. 本地全绿 ≠ CI 全绿：边界/浮点规则必须要么用 `fsum`/`round`，要么在最低支持 Python 上跑一次。
4. 声明类文档（Registry 上架、snippet 字段）要与真实状态同步，验证时应作为 must-have 检查。

### Cost Observations
- Model mix: orchestrator + parallel verifier/security/UI/code-review agents; heavy parallel re-verification near close.
- Sessions: continued session across execution → ship → CI fix → milestone close.
- Notable: the CI fix was a 3-file change that invalidated four phase fingerprints and required a full re-verification wave — the dominant close-out cost.
