# Phase 10: Raise pytest coverage to 90% - Context

**Gathered:** 2026-11-06
**Status:** Ready for re-planning — 7 agent-created plans (2026-11-05) exist without user context; user chose "discuss now, replan after" (`/gsd-plan-phase 10`). Existing `10-RESEARCH.md` / `10-PATTERNS.md` / `10-VALIDATION.md` remain valid inputs.

<domain>
## Phase Boundary

将 `src/sif` 的 pytest 行覆盖率从 78%(5587 语句 / 1220 未覆盖,2026-11-05 基线,688 测试全绿)提升到 ≥90%:删除已证实的死代码簇(重定基线 ~81%)→ 按缺口清单补测试 → 最后在 `pyproject.toml` 落地 `[tool.coverage.report] fail_under = 90` 使门禁永久生效。门禁命令:`env -u FORCE_COLOR NO_COLOR=1 pytest --cov=src/sif`,TOTAL ≥90% 且全量套件绿色。

本次讨论澄清 HOW:死代码删除的确认与政策、覆盖率豁免尺度、顺序依赖测试处理、套件时间预算。

</domain>

<decisions>
## Implementation Decisions

### 死代码删除(A3/A5 假设消解)
- **D-01:** sif 定位为**纯 CLI/MCP 工具**——没有也不打算支持外部代码 `import sif` 当库用。删除 ~266 条死码语句零 breaking 风险,按 10-01 计划全删:`cli/config.py` 整文件、`cli/formatters.py` 只留 2 个活符号(`prepend_line_numbers`/`add_line_numbers_to_results`)、`utils/text.py` 删 5 个死函数。— **Reversibility:** reversible — 删除均可用 git revert 恢复,且无外部消费者依赖被删符号。
- **D-02:** **持续删除政策**:Wave 2/3 补测试过程中发现新的零引用代码可顺手删,不限于 Wave 1 已证实批次;但必须满足 Pattern 4 证据门槛:全仓 grep(src/tests/scripts/docs)零引用 + 全套件绿 + 重测覆盖率基线。该标准适用于全阶段。

### 覆盖率豁免政策
- **D-03:** **窄白名单豁免**——仅三类分支允许 `# pragma: no cover`:`__main__` 守卫(coverage 默认已豁免)、KeyboardInterrupt/信号处理、防御性不可达分支。禁止对业务逻辑行打 pragma;90% 的成色由真测试保证。
- **D-04:** 豁免机制用**逐行 pragma + 理由注释**(如 `# pragma: no cover — KeyboardInterrupt 仅交互式触发`),豁免点在代码内可见、review 可审计;`pyproject.toml` 只落 `fail_under`,**不改** `exclude_lines`/`exclude_also` 配置(避开 Pitfall 6 的默认豁免替换陷阱)。
- **D-05:** **长尾质量红线**:Wave 3 冲刺时若某文件只能写出低价值测试(纯 getter 断言、回声测试),取舍优先级为:可测性重构 → 证据门槛删除(接 D-02)→ 凑数测试仅作最后手段。

### 顺序依赖测试处理
- **D-06:** **修根因,不维持现状**:Wave 2 早期加入条件性任务,诊断 `test_openai_embedder.py` 2 个顺序依赖失败的污染源(候选:sys.modules mock 泄漏、`get_settings` lru_cache 残留、环境变量污染),修复后验收标准 = 单文件独跑绿 + 全量跑绿(两种顺序均绿)。
- **D-07:** **防新雷编码约定强制适用于所有新测试**:环境变量一律 `monkeypatch.setenv`(禁裸 `os.environ` 赋值)、`sys.modules` mock 注入必须在 fixture teardown 撤销、不依赖其他测试的副作用(动过 `get_settings` 缓存的测试要 `get_settings.cache_clear()`)。写入执行者约束,plan review 时检查。

### 套件时间预算
- **D-08:** **不设时间预算**——覆盖率为唯一目标,套件时长允许自由增长;real-DB/real-temp-file 优先的测试模式(Pattern 1/2)不受时长约束,不为提速牺牲测试真实性。

### Claude's Discretion
- 测试文件组织细节、fixture 设计、断言风格(AAA 注释等沿用现有约定)
- Wave 3 tollgate 长尾文件的取舍顺序(哪些先补、补到什么程度)
- D-06 诊断的具体技术路径(哪个污染源、怎么隔离)
- 长尾文件可测性重构的具体手法

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 本阶段研究产物(2026-11-05,agent 规划期生成,重规划时复用)
- `.planning/phases/10-raise-pytest-coverage-to-90/10-RESEARCH.md` — 已验证缺口清单(死码簇 + 20 个缺口文件按 missed 排序)、6 种测试模式、8 个 pitfalls、4 个已解决开放问题、A1-A5 假设日志
- `.planning/phases/10-raise-pytest-coverage-to-90/10-PATTERNS.md` — 模式到测试文件的映射(Pattern 1-6)、新测试文件骨架、runner 调用约定、零新依赖约束
- `.planning/phases/10-raise-pytest-coverage-to-90/10-VALIDATION.md` — 门禁定义与验收口径

### 需求与路线图
- `.planning/REQUIREMENTS.md` — T-10-1(行覆盖率 ≥90% 门禁,含死码删除路径;traceability 表 Pending)
- `.planning/ROADMAP.md` §Phase 10 — 阶段边界、Wave 1-3 结构、成功判据

### 配置与约定
- `pyproject.toml` — `[tool.pytest.ini_options]`(coverage addopts);`[tool.coverage.report] fail_under = 90` 仅在最终 plan 落地(10-07 Task 2)
- `CLAUDE.md` — 质量套件命令、代码风格、GSD 工作流约束
- `.planning/STATE.md` §Accumulated Context — Phase 04/06 的测试决策(sys.modules 注入 mock、MagicMock sqlite3、include_highlights=False、CliRunner 优先)、已知 open follow-ups(WR-10..17、19 个 ty 诊断——均不在本阶段范围)

### 代码库地图(2026-04-14,部分内容早于 docsift→sif 重命名,路径过时处以 10-RESEARCH.md 为准)
- `.planning/codebase/TESTING.md` — 测试框架、目录结构、mock/fixture 约定(RESEARCH 已标注其中过时条目)
- `.planning/codebase/CONCERNS.md` §Test Coverage Gaps — 遗留关注点(多数已由 Phase 01-09 修复)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/conftest.py` — 既有 fixtures:temp_dir、temp_db_path、db_connection、mock_embedder、mock_repository 等,新测试直接复用
- `tests/factories.py` — CollectionFactory/DocumentFactory/DocumentChunkFactory 等 7 个工厂类
- `tests/unit/database/test_repositories.py`(05-09)—— real in-memory SQLite + 生产 DDL 的已验证形状(Pattern 2 的母本)
- `tests/unit/cli/test_collection.py` — 已有 CliRunner 测试可扩展(Pattern 1 目标文件)

### Established Patterns
- Pattern 1(CliRunner + real temp DB)/ Pattern 2(real in-memory SQLite)/ Pattern 3(mocked ML 对象,patch lazy import 点)/ Pattern 4(死码删除证据门槛)/ Pattern 5(DI-with-mocks)/ Pattern 6(pyproject 门禁最后落地)——详见 10-PATTERNS.md
- FORCE_COLOR 陷阱:测试命令必须 `env -u FORCE_COLOR NO_COLOR=1`(设 "0" 无效)
- 先例 D-02:sqlite_repository.py 重复实现删除——死码删除有项目先例
- 先例:261105-wbj 的 O(N²) 回归守护测试写法(新增回归测试的模式参考)

### Integration Points
- `pyproject.toml [tool.coverage.report]` — fail_under=90 随最终 plan 落地,落地前任何中间 plan 不得提前引入(否则阻塞后续 wave)
- Makefile 测试目标 + `docs/cli-reference.md`/`docs/configuration.md` 为生成器所有,删除死码若涉及文档面须走 `make docs-generate`,禁止手改

</code_context>

<specifics>
## Specific Ideas

- pragma 格式示例(带理由注释):`# pragma: no cover — KeyboardInterrupt 仅交互式触发`
- 豁免白名单精确到三类:`__main__` 守卫、KeyboardInterrupt/信号处理、防御性不可达分支——除此之外一律真测试
- D-07 的三条编码约定是硬约束,plan review 逐条检查,不是建议
- 时间预算的态度:"覆盖率是唯一目标,时长不是这个阶段的优化维度"

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 10-raise-pytest-coverage-to-90*
*Context gathered: 2026-11-06*
*Next step: /gsd-plan-phase 10 — re-planning(现有 7 个 plan 将按本 CONTEXT 决策重新生成)*
