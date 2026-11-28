---
phase: 26-anchor-arm-deterministic-cache
plan: 01
subsystem: search
tags: [anchor, bm25, fts5, prefix-routing, mcp, deterministic]

# Dependency graph
requires:
  - phase: 25-contract-freeze-feasibility-spike
    provides: 规则锚点表 bench/anchor-table.json 与 OR 注入的实测证据（+0.127246 / helped 6 / hurt 0）
provides:
  - "SearchType.ANCHOR 与 SearchOptions.anchor_terms（唯一注入点）"
  - "sif/search/anchor.py：零模型规则表、normalize_query、derive_rule_anchors、AnchorResolution、AnchorResolver 协议"
  - "BM25Searcher._build_fts_query(query, anchor_terms) 的 OR 备选形式，默认路径逐字节不变"
  - "共享 PREFIX_ROUTES 常量与 SearchPipeline 的 ANCHOR 单腿路由"
  - "MCP SearchBackend 的只读 anchor: 直连 BM25 分支"
affects: [26-02, 26-03, 26-04, 27]

actuals:
  tokens: 12344
  tasks: 3
  commits: 3
  plan_head_before: 818607b720d7c56bf8ba36175dc27691f8b4390e
  plan_head_after: 5b1b52d09f85931930289a4618d32f9563958c1b

tech-stack:
  added: []
  patterns:
    - "锚点以 OR 备选注入 FTS MATCH：(`<query AND chain>`) OR \"<anchor>\"*"
    - "前缀路由单一常量（PREFIX_ROUTES）供 pipeline 与 MCP 共用"
    - "运行级元数据挂在 pipeline 属性，绝不进入 SearchResult.to_dict"

key-files:
  created:
    - src/sif/search/anchor.py
    - tests/unit/search/test_anchor_injection.py
    - tests/unit/search/test_anchor_rules.py
    - tests/unit/mcp/test_backend_anchor.py
  modified:
    - src/sif/core/models.py
    - src/sif/search/bm25.py
    - src/sif/search/hybrid.py
    - src/sif/mcp/backend.py
    - tests/unit/search/test_bm25.py
    - tests/unit/search/test_hybrid.py

key-decisions:
  - "锚点一律以 OR 备选拼接；字面 AND-prepend 实测 36/36 查询 0 结果，绝不采用"
  - "每个锚点整体调用 _sanitize_term（不先 split），multi-word 锚点保持短语"
  - "anchor_terms=[] 语义为「显式无锚点」并绕过 resolver，评测可注入空集对照"
  - "在 wave 1 一并声明 AnchorResolver 协议，使 pipeline 的 TYPE_CHECKING 注解可被 ty 解析"
  - "MCP anchor: 分支与 lex: 同构：规则锚点、只读、不加载 embedder、不写 llm_cache"

patterns-established:
  - "锚点注入：SearchOptions.anchor_terms → BM25Searcher._build_fts_query（唯一路径）"
  - "前缀路由：PREFIX_ROUTES 单表，anchor:lex:foo 只剥离一层"
  - "运行级元数据：SearchPipeline.last_anchor_resolution，每次 search 先重置"

requirements-completed: [ANC-01, ANC-02, ANC-03, ANC-04]

coverage:
  - id: D1
    description: "anchor: 查询在真实 FTS 索引上端到端返回结果，规则锚点以 OR 备选注入 BM25 单腿"
    requirement: ANC-01
    verification:
      - kind: unit
        ref: "tests/unit/search/test_anchor_injection.py#test_anchor_prefix_end_to_end_uses_rules"
        status: pass
    human_judgment: false
  - id: D2
    description: "BM25 FTS MATCH 的默认、空锚点、OR 短语、元字符与空查询形状被字面量钉死"
    requirement: ANC-02
    verification:
      - kind: unit
        ref: "tests/unit/search/test_bm25.py#test_build_fts_query_anchor_terms_are_or_alternatives"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_anchor_injection.py#test_bm25_or_alternative_shape"
        status: pass
    human_judgment: false
  - id: D3
    description: "SearchType.ANCHOR、anchor_terms 默认 None 与共享 PREFIX_ROUTES 落地"
    requirement: ANC-03
    verification:
      - kind: unit
        ref: "tests/unit/search/test_hybrid.py#test_prefix_routes_shared_table_has_anchor"
        status: pass
      - kind: unit
        ref: "tests/unit/mcp/test_backend_anchor.py#test_prefix_routes_include_anchor_exactly_once"
        status: pass
    human_judgment: false
  - id: D4
    description: "MCP anchor: 只读分支：不加载 embedder、不写 llm_cache，且只剥离一层前缀"
    requirement: ANC-03
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_backend_anchor.py#test_anchor_query_returns_rows_without_loading_embedder"
        status: pass
      - kind: unit
        ref: "tests/unit/mcp/test_backend_anchor.py#test_anchor_query_writes_no_llm_cache"
        status: pass
    human_judgment: false
  - id: D5
    description: "highlight 与 snippet 仍使用去掉前缀后的原始 query（锚点不进入文本）"
    requirement: ANC-02
    verification:
      - kind: unit
        ref: "tests/unit/search/test_anchor_injection.py#test_highlights_use_the_original_query"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_anchor_injection.py#test_snippets_use_the_original_query_terms"
        status: pass
    human_judgment: false
  - id: D6
    description: "hybrid+anchor 可组合：anchor_terms 抵达 BM25 腿，向量腿分数与 embed 参数不变"
    requirement: ANC-04
    verification:
      - kind: unit
        ref: "tests/unit/search/test_hybrid.py#test_anchor_terms_reach_the_bm25_leg_in_hybrid_mode"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_hybrid.py#test_anchor_terms_leave_vector_scores_unchanged"
        status: pass
    human_judgment: false

duration: 7min
completed: 2026-11-28
status: complete
---

# Phase 26 Plan 01: Anchor Arm + Deterministic Cache Summary

**`anchor:` 规则锚点以 OR 备选注入 BM25 单腿：真实 FTS 端到端可跑、默认路径逐字节不变、pipeline 与 MCP 共用一张前缀表**

## Performance

- **Duration:** 7 min
- **Started:** 2026-11-28T04:59:38Z
- **Completed:** 2026-11-28T05:06:37Z
- **Tasks:** 3
- **Files modified:** 10

## Accomplishments

- 新增 `SearchType.ANCHOR` 与 `SearchOptions.anchor_terms`（唯一注入点，默认 `None`，不加任何 `anchor_enabled`/`anchor_mode` 开关）。
- 新建 `src/sif/search/anchor.py`：从 Phase 25 的 `anchor-table.json` 逐字移植 `phrases`/`tokens`/`cjk`/`compounds` 与四条派生规则；`derive_rule_anchors` 为纯函数（NFKC + casefold + 去重 + query 词排除 + 6 条上限），模块顶层只 import stdlib。
- `BM25Searcher._build_fts_query(query, anchor_terms=None)` 输出 `(<query AND chain>) OR "<anchor>"* ...`；`anchor_terms` 为 None/空时与今天逐字节相同；锚点整体经 `_sanitize_term`，`machine learning` 保持一个短语。
- `PREFIX_ROUTES` 提升为 `src/sif/search/hybrid.py` 的模块级常量（含 `anchor:`），`SearchPipeline` 与 MCP `SearchBackend` 共用；`SearchPipeline` 新增 ANCHOR 分支与 `last_anchor_resolution` 运行级元数据。
- MCP 的 `anchor:` 在 `_ensure_embedder()` 之前返回：只用规则锚点、不构造 resolver、不写 `llm_cache`（保持 7 个只读工具）。
- ANC-02/ANC-04 由机械测试钉死：highlight/snippet 用原始 query、`SearchResult.to_dict()` 无锚点键、hybrid 路由的 `_build_fts_query` spy 证明 `anchor_terms` 只抵达 BM25 腿且向量分数不变。

## Task Commits

Each task was committed atomically:

1. **Task 1: 端到端 `anchor:` 规则锚点单腿路径** — `951565e` (feat)
2. **Task 2: 共享前缀路由 + MCP 只读锚点分支** — `844bdd9` (feat)
3. **Task 3: ANC-02/ANC-04 机械保证与默认逐字节回归** — `5b1b52d` (test)

**Plan metadata:** (docs commit, this SUMMARY)

## Files Created/Modified

- `src/sif/search/anchor.py` — 规则表、规范化、`derive_rule_anchors`、`AnchorResolution`、`AnchorResolver`
- `src/sif/core/models.py` — `SearchType.ANCHOR`、`SearchOptions.anchor_terms`
- `src/sif/search/bm25.py` — `_build_fts_query` 的 OR 备选注入与调用点
- `src/sif/search/hybrid.py` — `PREFIX_ROUTES`、ANCHOR 路由、`_resolve_anchor`、`last_anchor_resolution`
- `src/sif/mcp/backend.py` — 共享 `PREFIX_ROUTES`、`_prefix_route`/`_lexical_route`、只读 ANCHOR 分支
- `tests/unit/search/test_anchor_rules.py` — 规则表纯函数
- `tests/unit/search/test_anchor_injection.py` — 端到端、highlight/snippet、惰性导入
- `tests/unit/mcp/test_backend_anchor.py` — MCP 只读契约
- `tests/unit/search/test_bm25.py` / `tests/unit/search/test_hybrid.py` — 字面量与可组合性

## Decisions Made

- 锚点只能以 OR 备选扩展；AND-prepend 在真实 FTS 上会把 36/36 条 tuning 查询打到 0 结果（Phase 26 研究实测）。
- `anchor_terms=[]` = 显式无锚点并绕过 resolver，便于评测注入空集。
- 在 wave 1 提前声明 `AnchorResolver` 协议，使 `SearchPipeline` 的 `TYPE_CHECKING` 注解可以被 `ty` 解析。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] 在 wave 1 定义 `AnchorResolver` 协议**
- **Found during:** Task 1
- **Issue:** 计划要求在 `TYPE_CHECKING` 下导入 `AnchorResolver` 并用于 `SearchPipeline.__init__` 注解，但该名字原属 26-02；缺失会让 `ty check src/sif` 报未解析符号。
- **Fix:** 在 `sif/search/anchor.py` 定义结构性 `Protocol`（仅 `resolve(query) -> AnchorResolution`），26-02 直接实现它，不改注解形状。
- **Files modified:** `src/sif/search/anchor.py`
- **Verification:** `ty check src/sif` 全绿。
- **Committed in:** `951565e`

**2. [Rule 3 - Blocking] 抽出 `_prefix_route` / `_lexical_route` 以守住 mccabe ≤10**
- **Found during:** Task 2
- **Issue:** 新增 ANCHOR 分支让 `SearchBackend.hybrid_search` 复杂度升到 11，`ruff` C901 失败。
- **Fix:** 把 `lex:`/`anchor:` 的前缀直连逻辑收敛到两个模块级 helper，`hybrid_search` 只保留一处判定。
- **Files modified:** `src/sif/mcp/backend.py`
- **Verification:** `ruff check src tests` 通过；MCP 183 测试全绿。
- **Committed in:** `844bdd9`

**3. [Rule 1 - Bug] 测试种子连接补 `row_factory = sqlite3.Row`**
- **Found during:** Task 2
- **Issue:** `SchemaManager` 按列名读取 `PRAGMA table_info`，默认 tuple row factory 导致 `TypeError`。
- **Fix:** 在测试的 `_seed_db` 里设置 `conn.row_factory = sqlite3.Row`。
- **Files modified:** `tests/unit/mcp/test_backend_anchor.py`
- **Verification:** 该文件 4 个测试通过。
- **Committed in:** `844bdd9`

---

**Total deviations:** 3 auto-fixed (1 missing critical, 1 blocking, 1 bug)
**Impact on plan:** 全部为正确性/可交付性所需，无范围扩张。锁定的 D-01/D-03/D-04/D-05/D-08 语义未被改动。

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 26-02（生成器与确定性缓存）可直接在 `AnchorResolution` 上追加带默认值的字段，并用 `AnchorResolver` 协议实现 `resolve`；`SearchPipeline._resolve_anchor` 已优先采用注入的 resolver。
- `anchor:` 单腿 OR 语义、默认逐字节路径与共享前缀表均由测试钉死，后续计划无需重复验证。
- 全部 167 个相关测试通过，`ruff check src tests` 与 `ruff format --check src tests` 全绿，`ty check src/sif` 全绿，全部冻结文件（`pyproject.toml`/`uv.lock`/`src/sif/mcp/protocol.py`/`src/sif/mcp/tools.py`/goldens/`test_packaging.py`/`test_wire_transcripts.py`）无改动。

## Self-Check: PASSED

- FOUND: src/sif/search/anchor.py
- FOUND: tests/unit/search/test_anchor_injection.py
- FOUND: tests/unit/mcp/test_backend_anchor.py
- FOUND: tests/unit/search/test_anchor_rules.py
- FOUND: 951565e
- FOUND: 844bdd9
- FOUND: 5b1b52d

---
*Phase: 26-anchor-arm-deterministic-cache*
*Completed: 2026-11-28*
