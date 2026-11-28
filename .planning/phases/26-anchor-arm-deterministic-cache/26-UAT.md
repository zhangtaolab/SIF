---
status: partial
phase: 26-anchor-arm-deterministic-cache
source: 26-01-SUMMARY.md, 26-02-SUMMARY.md, 26-03-SUMMARY.md, 26-04-SUMMARY.md
started: 2026-11-28T09:30:00Z
updated: 2026-11-28T09:47:20.191Z
---

## Current Test

[testing complete]

## Tests

### 1. `anchor:` 前缀在真实 FTS 索引上端到端返回结果
expected: `sif search query "anchor:<query>"` 用规则锚点走 BM25 单腿；`--explain` 在 stderr 打印一行 anchor 元数据；JSON 输出不含任何锚点键。
result: pass
source: automated
coverage_id: 26-01/D1
note: 临时库 5 篇文档独立实测：`anchor:machine learning` 返回 3 条（ml.md / zh.md / stats.md），`--explain` 输出 `anchor: backend=rules calls=0 hits=0 fallback=none`，`--json` 键集无锚点字段。

### 2. FTS MATCH 形状：默认 / 空锚点 / OR 短语 / 元字符
expected: 无锚点、`anchor_terms=None`、`anchor_terms=[]` 三种情况生成逐字节相同的 AND 链；锚点以 `OR "<phrase>"*` 追加；纯元字符锚点被消毒为空后回退到基础查询。
result: pass
source: automated
coverage_id: 26-01/D2
note: 直接探针比对：`default==None -> True`，`default==[] -> True`，字面量 `"machine"* AND "learning"* AND "basics"*`；带锚点为 `(<base>) OR "statistical learning"* OR "机器学习"*`；`[*:()]` 锚点不改变查询。

### 3. `SearchType.ANCHOR`、`anchor_terms` 默认 None、共享 `PREFIX_ROUTES`
expected: 新增枚举与唯一注入点默认 None；pipeline 与 MCP 共用同一张前缀表，`anchor:` 只出现一次。
result: pass
source: automated
coverage_id: 26-01/D3

### 4. MCP `anchor:` 只读分支
expected: MCP 的 `anchor:` 在构造 embedder 之前返回规则锚点结果；不写 `llm_cache`；只剥离一层前缀。
result: pass
source: automated
coverage_id: 26-01/D4
note: 单元契约通过；临时库上连续 5 次 anchor 搜索后 `llm_cache` 仍为 0 行。（本次会话 MCP server 未连上，只读性由契约测试 + CLI 侧 cache 计数共同佐证。）

### 5. highlight 与 snippet 仍用原始 query
expected: 锚点不进入高亮和摘要文本；锚点词不会出现在 snippet 里。
result: pass
source: automated
coverage_id: 26-01/D5
note: 实测 snippet 只含原始 query 的上下文，未见 "statistical learning" 作为检索词进入摘要。

### 6. hybrid + anchor 可组合
expected: `anchor_terms` 抵达 BM25 腿，向量腿分数与 embed 参数不变。
result: pass
source: automated
coverage_id: 26-01/D6

### 7. 同一 query 二次解析命中缓存
expected: 第二次解析 0 次生成、1 次缓存命中；第二个 resolver 与第二个独立 `sqlite3.Connection` 同样命中。
result: pass
source: automated
coverage_id: 26-02/D1

### 8. 45 配置 × 3 query 只产生 3 次生成
expected: 网格扫描时每个 query 只生成一次，其余全部缓存命中。
result: pass
source: automated
coverage_id: 26-02/D2

### 9. 冻结 prompt 与 GEN-01 解析器
expected: 编号/项目符号剥离、大小写归一、去重、≤10 条、>64 字符或 6 词或纯标点丢弃、CJK 保留。
result: pass
source: automated
coverage_id: 26-02/D3

### 10. 本地 GGUF 生成器
expected: `embedding=False`、显式 chat template、greedy 参数；token deadline 以 `reason='timeout'` 浮出。
result: pass
source: automated
coverage_id: 26-02/D4

### 11. 生成失败/超时 fail-open 与预算硬失败
expected: 失败时结果与 `lex:` 逐行相等、只告警一次、同 query 不重试；`SIF_ANCHOR_MAX_CALLS` 超限为硬失败。
result: pass
source: automated
coverage_id: 26-02/D5

### 12. 远程后端显式 opt-in 与一次性外发披露
expected: 缺配置回退规则锚点；每个 `base_url` 只披露一次查询文本外发；默认与 fake 路径零 socket。
result: pass
source: automated
coverage_id: 26-02/D6

### 13. 10 个 `SIF_ANCHOR_*` 进入生成式配置文档
expected: 每个 Settings 字段都有 SECTION；`make docs-generate` 后零 diff。
result: pass
source: automated
coverage_id: 26-02/D7
note: `docs/configuration.md` 实测含 10 个 `SIF_ANCHOR_*` 键；`make docs-generate` 退出 0 且 `git status docs/` 为空。

### 14. `--anchor` 与 `anchor:` 等价
expected: 两种写法注入一次；同时出现只注入一次；无 flag 时 query 原样传入 pipeline。
result: pass
source: automated
coverage_id: 26-03/D1
note: 实测 `--anchor` 与 `anchor:machine learning` 返回同样 3 个文件。

### 15. ANCHOR 路由零 embedder 构造
expected: 无 rerank 时不构造 embedder；注入 `AnchorResolver`；非 anchor 路由传 None。
result: pass
source: automated
coverage_id: 26-03/D2
note: 临时库未安装任何向量，anchor 搜索仍正常返回 —— 与"零 embedder"一致。

### 16. `--anchor` 与 `--rerank` 显式互斥
expected: 同时给出时在构造 reranker 之前报错退出，零构造；`--rerank` 单独使用仍构造 reranker。
result: pass
source: automated
coverage_id: 26-03/D3
note: 实测报错文本：`Error: --anchor cannot be combined with --rerank (or SIF_RERANK_ENABLED); the ANCHOR route is pure BM25 single-leg`。

### 17. `--explain` 只多一行 anchor 元数据
expected: stderr 恰一行；`--explain --json` 的 stdout 仍是合法 JSON 且无 anchor 键；GEN-03 fallback 原因可见。
result: pass
source: automated
coverage_id: 26-03/D4

### 18. DYM 与 query history 收原始 query
expected: did-you-mean 与查询历史记录的是去掉前缀后的原始 query，pipeline 收到 `anchor:<q>` 语义。
result: pass
source: automated
coverage_id: 26-03/D5

### 19. `docs/cli-reference.md` 重生成并含 `--anchor`
expected: 文档由 `make docs-generate` 生成；二次运行零 diff；`--help` 可见该 flag。
result: pass
source: automated
coverage_id: 26-03/D6
note: `--help` 实测显示 `--anchor  Expand the BM25 leg with deterministic rule anchors (default: off; the anchor: prefix is equivalent)`。

### 20. 默认关闭的 FTS 词表守卫过滤 OOV 锚点
expected: `SIF_ANCHOR_VOCAB_GUARD` 默认 False；开启后规则/缓存/生成器三条路径产出的锚点都按 `documents_fts MATCH` 过滤；porter 词干与 CJK 单 token 正确；关闭时锚点集合与基线逐字节一致。
result: pass
source: automated
coverage_id: 26-04/D1
note: 默认值实测 `anchor_vocab_guard=False`。本语料下守卫开/关用户可见结果相同（三个规则锚点恰好都在词表内），过滤本身由 4 个探针用例钉死。

### 21. MCP `anchor:` 在守卫开启时仍只读
expected: 守卫通过惰性导入在内存中过滤；不写 `llm_cache`、不构造 embedder。
result: pass
source: automated
coverage_id: 26-04/D2

### 22. 无 GGUF 打包/提交，LFM license 与 Key Decision 落地
expected: `src/sif` 下无 `.gguf`；`pyproject.toml` 不含 `.gguf`；仓库无已提交 `.gguf`；文档写明 `LFM Open License v1.0` 的 1000 万美元营收阈值与再分发义务；`PROJECT.md` 有 CTR-03 Key Decision。
result: pass
source: automated
coverage_id: 26-04/D3
note: 实测 `git ls-files -- '*.gguf'` 为空、`find src/sif -name '*.gguf'` 为空、pyproject 命中 0；`docs/search-algorithms.md` 含 license 名与阈值；`PROJECT.md` 含 2 处 `Validated in Phase 26 (CTR-03)`。另核 `sif cleanup` 确实通过 `LLMCacheRepository.clear_expired()` 清理过期缓存行。

### 23. 本地全量质量门禁
expected: `pytest` ≥90% 覆盖、`ty`、`ruff check`、`ruff format --check`、`make docs-generate` 零 diff、MCP 契约 13 passed、11 个冻结路径自 v1.2.5 无 diff。
result: pass
source: automated
coverage_id: 26-04/D4
note: 独立重跑全部通过 —— pytest 3367 passed / 1 skipped / 94.18%（187.39s，reranker 需 torch，按计划用它记录的 `--ignore` 回退）；`ty check src/sif` All checks passed；ruff check/fmt 全绿（249 files）；`make docs-generate` 退出 0 且零 diff；packaging+docs+MCP 契约 39 passed（含 13 条 wire-transcript）；11 个冻结路径 `git diff v1.2.5..HEAD` 为空。

### 24. 8-cell CI 矩阵（push 后外部门禁）
expected: `.github/workflows/test-matrix.yml` 在 2 OS × 4 Python 上以 `--extra embed` 跑全量，8 个 cell 全绿。
result: blocked
blocked_by: release-build
reason: "CI 在 GitHub Actions 上由 push 触发，本地无法执行；当前分支 dev 领先 origin/dev 54 个提交且尚未 push。"

## Summary

total: 24
passed: 23
issues: 0
pending: 0
skipped: 0
blocked: 1

## Gaps

[none yet]

## Notes

- 本次是 Claude 代测（用户指令：`26 你来检测并提供检查报告`），没有逐条对话问答；每条 `source: automated` 的记录都对应我本轮实际执行过的测试或命令，不是照抄 SUMMARY。
- 测试方式：临时数据库 + 3 篇合成语料（`ml.md` 含 "machine learning"、`stats.md` 只含 "statistical learning"、`zh.md` 只含 "机器学习"），验证锚点确实把 BM25 召回从 1 条扩到 3 条。
- 唯一未通过项是 8-cell CI，属于 push 后外部门禁，按设计本地无法产出；它不进 Gaps（阻塞项不是代码缺陷）。
