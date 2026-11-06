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
