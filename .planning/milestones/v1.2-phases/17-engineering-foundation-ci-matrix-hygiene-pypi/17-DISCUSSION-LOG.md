# Phase 17: Engineering Foundation (CI Matrix + Hygiene + PyPI) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-13
**Phase:** 17-Engineering Foundation (CI Matrix + Hygiene + PyPI)
**Areas discussed:** CI 拓扑与触发, Windows smoke 形态, 死层与 junk 处置, PyPI 发布载体

---

## CI 拓扑与触发

| Option | Description | Selected |
|--------|-------------|----------|
| 每 push/PR 全 8 胞全量 | 最强回归网；8 胞 × ~5min；研究建议 full suite per cell | ✓ |
| PR 全量 + push main 单胞快检 | 省 minutes；main 分支保护变弱 | |
| PR 2 胞 + nightly 全矩阵 | PR 快；全矩阵问题延迟到夜间发现 | |

**User's choice:** 每 push/PR 全 8 胞全量
**Notes:** —

| Option | Description | Selected |
|--------|-------------|----------|
| 仅 uv/pip 依赖缓存 | CI 测试用 ConceptEmbedder 确定性嵌入（Phase 16 D-01），无需 HF 模型缓存 | ✓ |
| 依赖 + HF 模型缓存 | 为将来真实模型测试预留；当前套件无真模型，收益低 | |
| 不缓存 | 最简；每胞多几分钟安装时间 | |

**User's choice:** 仅 uv/pip 依赖缓存
**Notes:** —

| Option | Description | Selected |
|--------|-------------|----------|
| ubuntu + macos-latest(arm64)，8 胞 | 控成本；研究未要求 Intel mac | ✓ |
| ubuntu + macos-13(Intel) + macos-14(arm64) | 覆盖双架构；成本 +50%（12 胞） | |
| ubuntu + macos-13(Intel)，8 胞 | Intel 更接近多数用户；arm64 未覆盖 | |

**User's choice:** ubuntu + macos-latest(arm64)，8 胞
**Notes:** —

---

## Windows smoke 形态

| Option | Description | Selected |
|--------|-------------|----------|
| hc yoga 脚本 + Makefile 目标 | 匹配用户的 hc 指令；不依赖 GH runner；脚本可在 yoga 上复跑（先 uv python install） | ✓ |
| GH windows-latest 子集 marker | 真实 CI 信号，但 GH Windows 是 Server 2022，不是 Win11 yoga；与 hc 要求不符 | |
| 两者都要 | yoga 脚本为主 + GH windows-latest 为备；工作量最大 | |

**User's choice:** hc yoga 脚本 + Makefile 目标
**Notes:** 用户补充：yoga 上 Windows 项目目录 = `D:\Github\SIF`（2026-11-13 会话中提供）。

| Option | Description | Selected |
|--------|-------------|----------|
| CLI 级降级断言 | index/search/status 在缺 fcntl/systemd/fork 时给出明确错误或安全降级；面向真实用户面 | ✓ |
| pytest curated 子集 | DB factory/WAL、flock 缺失路径、service derivation；更深但需 marker 门控 | |
| 两者组合 | CLI 断言 + 小规模 pytest 子集；工作量较大 | |

**User's choice:** CLI 级降级断言
**Notes:** —

| Option | Description | Selected |
|--------|-------------|----------|
| 手动/按需 + 发布前 | 最省；发布前跑一次即可，风险由 v2 专门设计兑付 | ✓ |
| 每周定期 + 发布前 | 周期性捕捉漂移；yoga 需常驻可用 | |
| 每个 PR | 每 PR 都跑；yoga 是用户机器，成本与可用性风险高 | |

**User's choice:** 手动/按需 + 发布前
**Notes:** —

---

## 死层与 junk 处置

| Option | Description | Selected |
|--------|-------------|----------|
| 直删 | 最干净；git 历史可随时找回；符合项目 no-noqa 文化 | ✓ |
| 移到隔离目录保留一版 | 多一步保险；但隔离目录仍可能被误引 | |
| 保留但加 deprecation warning | 不推荐——死层最危险之处正是可被误接线 | |

**User's choice:** 直删
**Notes:** —

| Option | Description | Selected |
|--------|-------------|----------|
| 死层 + orphan + 幻影 + black | 全为零调用/零行为风险；v1.1 遗留一次收口 | ✓ |
| 仅本 phase 列出的死层 | 最小改动；v1.1 orphan 继续留账 | |
| 上述全部 + 全仓零引用扫描 | 更彻底；有误报与删错风险 | |

**User's choice:** 死层 + orphan + 幻影 + black
**Notes:** —

| Option | Description | Selected |
|--------|-------------|----------|
| 删目标+文档引用，清 VERIFY | 无 .pre-commit-config.yaml；ruff/ty/pytest 已由 make ci 覆盖 | ✓ |
| 补建 .pre-commit-config.yaml | 恢复本地钩子能力；新增维护面 | |
| 仅清 VERIFY 标记，目标保留 | 文档不再报错但 make pre-commit 仍会失败 | |

**User's choice:** 删目标+文档引用，清 VERIFY
**Notes:** —

---

## PyPI 发布载体

| Option | Description | Selected |
|--------|-------------|----------|
| 1.1.2 patch | 当前 _version.py=1.1.1；发布管线演练，不承诺 v1.2 API；ENG-03 即 v1.1.x | ✓ |
| 1.1.3 | 同 patch 语义；留给后续 hotfix 编号空间 | |
| 1.2.0a1 预发布 | 预留 v1.2 语义；预发布默认不进用户安装 | |

**User's choice:** 1.1.2 patch
**Notes:** —

| Option | Description | Selected |
|--------|-------------|----------|
| tag push(v*) 自动 | 标准 trusted publishing 流程；tag 即发布意图；PEP 740 attestations | ✓ |
| workflow_dispatch 手动 | 首次更安全；多一次人工 gate | |
| tag→PyPI + dispatch→TestPyPI | 两套入口；维护面更大 | |

**User's choice:** tag push(v*) 自动
**Notes:** —

| Option | Description | Selected |
|--------|-------------|----------|
| 每次 tag 先 TestPyPI 再 PyPI | 每次发布都验证构建/元数据；同一 workflow 内顺序执行 | ✓ |
| 仅首次/版本 bump 时手动 | 省时间；后续发布跳过演练 | |
| 独立 workflow 人工 gate | 最稳但最慢；需人工确认节点 | |

**User's choice:** 每次 tag 先 TestPyPI 再 PyPI（同一 workflow）
**Notes:** —

---

## Claude's Discretion

- Workflow YAML structure (job names, matrix include/exclude, concurrency group, setup-uv SHA pin, cache keys)
- Windows smoke script language and exact assertion set/messages; Makefile target name
- Dead-layer test cleanup mechanics (delete vs relocate assertions)
- PyPI workflow environment name, build-job separation, artifact checks
- Exact tracked-junk audit procedure
- Whether `Makefile` `ci` target gains the new test workflow parity

## Deferred Ideas

- Intel macOS runner (macos-13) coverage — revisit if an Intel-only wheel bug appears
- GitHub-hosted windows-latest smoke job — rejected for v1.2; full Windows support is v2
- Repo-wide zero-reference/private-function scan — deferred (false-positive risk)
- Info-findings sweep remainder (v1.1 ledgers) — later cleanup pass
