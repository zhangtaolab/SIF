# Phase 10: Raise pytest coverage to 90% - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-06
**Phase:** 10-Raise pytest coverage to 90%
**Areas discussed:** 既有计划处理, 死代码删除确认, 覆盖率豁免政策, 顺序依赖测试处理, 套件时间预算

---

## 既有计划处理(工作流前置问题)

| Option | Description | Selected |
|--------|-------------|----------|
| 继续讨论,之后重规划 | 先完成讨论生成 CONTEXT.md,之后用 /gsd-plan-phase 10 重新规划(research 可复用) | ✓ |
| 先查看现有 plan | 先展示 7 个 plan 概要再决定 | |
| 取消 | 退出讨论,plan 保持原样直接执行 | |

**User's choice:** 继续讨论,之后重规划
**Notes:** Phase 10 已有 7 个 agent 创建的 plan + RESEARCH/PATTERNS/VALIDATION(均未执行),但创建时无用户上下文。

---

## 死代码删除确认

### Q1: sif 的对外定位(决定删除 ~266 条死码是否 breaking)

| Option | Description | Selected |
|--------|-------------|----------|
| 纯 CLI 工具,删(推荐) | 本地 CLI + MCP 服务器,无外部库消费者;删除零风险,全部按计划删 | ✓ |
| 有库消费者,保守删 | 只删零引用的 config.py,formatters/text.py 死符号保留并补测试或标 deprecated | |
| 删但标 breaking | 全删但在 CHANGELOG/版本号标注 breaking,给潜在库用户迁移窗口 | |

**User's choice:** 纯 CLI 工具,删(推荐)
**Notes:** 消解 RESEARCH A3 假设(formatters.format_* 公共 API 之问)与 A5(text.py 死函数范围之问)。

### Q2: 补测试过程中发现新死代码怎么处理

| Option | Description | Selected |
|--------|-------------|----------|
| 持续删除+证据门槛(推荐) | Wave 2/3 发现零引用代码可顺手删,须满足 Pattern 4 门槛(全仓 grep 零引用 + 全套绿 + 重测基线) | ✓ |
| 只删已证实批次 | 只删 Wave 1 那批,后续死码记入 deferred 留给未来阶段 | |

**User's choice:** 持续删除+证据门槛(推荐)

---

## 覆盖率豁免政策

### Q1: 新增覆盖率豁免(pragma)的尺度

| Option | Description | Selected |
|--------|-------------|----------|
| 窄白名单(推荐) | 仅 __main__ 守卫、KeyboardInterrupt/信号处理、防御性不可达分支可豁免;业务逻辑禁 pragma | ✓ |
| 严格零豁免 | 所有 missed 行真测试覆盖;数字最真实但长尾可能为覆盖而覆盖 | |
| 宽松自判 | 执行者自行判断;灵活但数字可能虚高 | |

**User's choice:** 窄白名单(推荐)

### Q2: 豁免机制落地方式

| Option | Description | Selected |
|--------|-------------|----------|
| 逐行 pragma+理由(推荐) | 就地 # pragma: no cover 附理由注释;可见可审计不误伤;pyproject 只落 fail_under | ✓ |
| exclude_also 正则 | pyproject 集中追加类别正则;集中管理但可能误豁免且代码内不可见 | |

**User's choice:** 逐行 pragma+理由(推荐)

### Q3: Wave 3 长尾只能写低价值测试时怎么取舍

| Option | Description | Selected |
|--------|-------------|----------|
| 重构/删除优先(推荐) | 可测性重构 → 证据门槛删除 → 凑数测试最后手段 | ✓ |
| 接受凑数测试 | 数量优先快过线;留下永久维护负担的垃圾测试 | |

**User's choice:** 重构/删除优先(推荐)

---

## 顺序依赖测试处理

### Q1: test_openai_embedder 顺序依赖失败怎么处理

| Option | Description | Selected |
|--------|-------------|----------|
| 修根因(推荐) | Wave 2 早期条件性任务:诊断污染源(sys.modules 泄漏/lru_cache 残留/环境变量污染),验收 = 单文件独跑绿 + 全量绿 | ✓ |
| 维持现状 | 按既有顺序跑;10-05 新测试大概率踩雷且阻塞 Wave 3 | |
| 触发才修 | 只在被新测试触发时修;修复时机不可控 | |

**User's choice:** 修根因(推荐)

### Q2: 新测试要不要强制防顺序依赖编码约定

| Option | Description | Selected |
|--------|-------------|----------|
| 写入执行约束(推荐) | monkeypatch.setenv、sys.modules 注入 teardown 撤销、无跨测试副作用;写入执行者约束 + review 检查 | ✓ |
| 仅修已知 | 只修两处;新测试大概率叉出新雷 | |

**User's choice:** 写入执行约束(推荐)

---

## 套件时间预算

### Q1: 新增 ~200 个测试后,套件时间预算定多少

| Option | Description | Selected |
|--------|-------------|----------|
| <60s 软预算(推荐) | 不限 real-DB 风格,给 tollgate 硬检查点 | |
| <30s 紧预算 | 执行者倾向 mock 优先、限制 real-DB 数量 | |
| 不设预算 | 覆盖率为唯一目标,时长随便涨 | ✓ |

**User's choice:** 不设预算
**Notes:** 用户明确偏离推荐项——覆盖率是唯一目标,时长不是本阶段的优化维度;real-DB 优先模式不受约束。

---

## 完成度确认

| Option | Description | Selected |
|--------|-------------|----------|
| 就绪,生成 CONTEXT | 决策已足够,生成 10-CONTEXT.md 供重规划使用 | ✓ |
| 再探索更多地带 | 还有未涉灰色地带想再谈 | |

**User's choice:** 就绪,生成 CONTEXT

---

## Claude's Discretion

- 测试文件组织细节、fixture 设计、断言风格(沿用现有 AAA 约定)
- Wave 3 tollgate 长尾文件取舍顺序
- 顺序依赖诊断的具体技术路径
- 长尾文件可测性重构的具体手法

## Deferred Ideas

None — discussion stayed within phase scope
