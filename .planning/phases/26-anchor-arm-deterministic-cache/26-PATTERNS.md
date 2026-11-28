# Phase 26: Anchor Arm + Deterministic Cache - Pattern Map

**Mapped:** 2026-11-28
**Files analyzed:** 16
**Analogs found:** 14 / 16

> 说明：本文件的所有代码片段均为逐字摘录（英文标识符、路径、行号保持原样）。所有 analog 路径均已通过 `git ls-files` 校验为 tracked source，未引用任何 gitignored mirror。

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/sif/core/models.py` | model / enum | request-response | 自身（`SearchType` / `SearchOptions` 既有字段） | exact |
| `src/sif/search/bm25.py` | search strategy | transform (FTS MATCH 构造) | 自身 `_build_fts_query` | exact |
| `src/sif/search/hybrid.py` | service / router | request-response | 自身 `SearchPipeline.search` lex 分支 + `_parse_query_prefix` | exact |
| `src/sif/mcp/backend.py` | service / router | request-response | 自身 `_PREFIX_ROUTES` + BM25 分支 | exact |
| `src/sif/cli/commands/search.py` | controller (CLI) | request-response | 自身 `query_cmd` 的 options 构建 / embedder 加载 / explain 输出 | exact |
| `src/sif/config/settings.py` | config | batch (启动期校验) | 自身 `rerank_enabled` + `resolve_candidate_limit` | exact |
| `scripts/generate_config_ref.py` | config / docs generator | transform | 自身 `SECTIONS` 的 `Reranker Settings` 段 | exact |
| `src/sif/search/anchor.py` (**新**) | service / provider / utility | request-response + cache I/O | `src/sif/search/expansion.py`（可选组件）+ `src/sif/embedding/embedder.py`（lazy llama import + create_completion） | role-match |
| `src/sif/embedding/cache.py`（只读参考，不改） | service / cache | file-I/O | 自身 `EmbeddingCache.get/set`（TTL/commit 语义参考） | reference |
| `tests/unit/search/test_anchor.py` (**新**) | test | unit | `tests/unit/search/test_hybrid.py` + `tests/unit/search/test_bm25.py` | role-match |
| `tests/unit/mcp/test_backend_anchor.py` (**新**) | test | unit | `tests/unit/mcp/test_lazy_embedder.py`（若不存在则 `tests/unit/mcp/test_backend*.py`） | role-match |
| `tests/unit/cli/test_search_anchor.py` (**新**) | test | CLI | `tests/unit/cli/test_search.py`（`_query_settings_mock` 夹具） | exact |
| `tests/unit/config/test_settings_anchor.py` (**新**) | test | unit | 既有 settings 测试 | role-match |
| `tests/test_packaging_assets.py` (**新**) | test | static guard | `tests/test_docs.py` 的静态守卫风格 | role-match |
| `docs/configuration.md` / `docs/cli-reference.md` | docs (generator-owned) | generated | `make docs-generate` 产物 | exact (只重生成，不手改) |
| 用户文档（`docs/anchor.md` 或 `docs/models.md` 增节） | docs (hand-maintained) | prose | `docs/models.md` | role-match |

### Frozen / READ-ONLY（本阶段绝不修改，仅 verify）

以下为 v1.2.5 逐字节冻结契约，任何计划中出现均标 **READ-ONLY / verify-only**：

| 文件 | 处理方式 |
|------|----------|
| `src/sif/mcp/protocol.py` | READ-ONLY，`shasum -a 256` 对比 Phase 25 manifest |
| `src/sif/mcp/tools.py` | READ-ONLY，同上 |
| `tests/unit/mcp/goldens/*.json`（5 份 wire goldens） | READ-ONLY，`test_wire_transcripts.py` 必须仍 13 passed |
| `pyproject.toml` | READ-ONLY（`llama-cpp-python==0.3.35`、`fail_under=90` 均不变） |
| `uv.lock` | READ-ONLY（不 bump pin） |
| `tests/unit/mcp/test_packaging.py` | READ-ONLY（13 项 runtime 依赖冻结断言，不改；新增 GGUF 守卫放 `tests/test_packaging_assets.py`） |

---

## Pattern Assignments

### `src/sif/search/bm25.py` (search strategy, transform) — 本阶段最大风险点

**Analog:** 自身。**必须同时看两段：现状 AND-join 与 Phase 25 实测的 OR 备选形状。**

**现状 AND-join（逐字节，`src/sif/search/bm25.py:258-270`）：**
```python
    def _build_fts_query(self, query: str) -> str:
        """Build a safe FTS5 query from raw user input.

        Each whitespace-separated token is sanitized into a quoted prefix
        phrase and tokens are joined with AND, so ordinary input like
        ``e-mail``, ``don't``, or ``c++`` cannot be parsed as FTS5 query
        syntax. A query with no usable terms yields an empty phrase, which
        matches nothing instead of raising sqlite3.OperationalError.
        """
        terms = [t for t in (_sanitize_term(tok) for tok in query.split()) if t]
        if not terms:
            return '""'
        return " AND ".join(terms)
```

**`_sanitize_term` 语义（`src/sif/search/bm25.py:32-44`）——正确调用方式是「对每个锚点整体调用、不要先 split」：**
```python
def _sanitize_term(term: str) -> str:
    """Sanitize a raw query token into a safe FTS5 phrase.

    Metacharacters are replaced with spaces (the tokenizer then treats the
    remainder as plain phrase text) and the result is wrapped in double
    quotes so the token is matched literally instead of being parsed as
    FTS5 query syntax. A trailing ``*`` outside the quotes keeps prefix
    matching. Returns an empty string for tokens with nothing left.
    """
    cleaned = _FTS_METACHARS.sub(" ", term).strip()
    if not cleaned:
        return ""
    return f'"{cleaned}"*'
```

**Phase 25 OR 备选形状（research 实测 +0.127246，helped 6 / hurt 0；AND-prepend 实测 36/36 查询 0 结果）：**
```python
# 目标形状（锚点存在时）。缺省 anchor_terms 时输出必须与今天逐字节相同。
def _build_fts_query(self, query: str, anchor_terms: list[str] | None = None) -> str:
    terms = [t for t in (_sanitize_term(tok) for tok in query.split()) if t]
    base = " AND ".join(terms) if terms else '""'
    if not anchor_terms:
        return base                      # byte-identical default path
    alternatives = [t for t in (_sanitize_term(a) for a in anchor_terms) if t]
    if not alternatives:
        return base
    return f"({base}) OR " + " OR ".join(alternatives)
```

**关键事实（必须传给 planner）：**
- 锚点必须走 **OR 备选**；把它们并进 `" AND ".join(...)` 会导致 `anchor:` 在真实语料上全零（36/36）。
- 锚点侧**对每个锚点整体**调用 `_sanitize_term(anchor)`，**不要先 `split()`**，使 `machine learning` → `'"machine learning"*'`（短语）。
- 缺省 `anchor_terms`（None/[]）时返回 `base`，逐字节不变，`test_bm25.py` 的 `test_build_fts_query_*` 仍绿。

**highlight 使用原始 query（ANC-02 的机械保证，`src/sif/search/bm25.py:208-213`）：**
```python
            if options.include_highlights:
                result.highlights = self._get_highlights(
                    row["document_id"],
                    query,
                    options.max_highlights,
                )
```
只要锚点走 `options.anchor_terms` 而不进 `query` 参数，highlight 自动保持原 query。

**调用点改造（`src/sif/search/bm25.py:88`）：**
```python
        # Build the FTS query
        fts_query = self._build_fts_query(query)
```
→ 改为 `self._build_fts_query(query, options.anchor_terms)`。`search_chunks`（`:234`）保持不传锚点。

---

### `src/sif/core/models.py` (model / enum, request-response)

**Analog:** 自身既有 `SearchType` 与 `SearchOptions`。

**SearchType 枚举（`src/sif/core/models.py:84-91`）：**
```python
class SearchType(Enum):
    """Search types."""

    BM25 = "bm25"
    VECTOR = "vector"
    HYBRID = "hybrid"
    HYDE = "hyde"
    EXPAND = "expand"
```
→ 追加 `ANCHOR = "anchor"`。

**SearchOptions 字段范式（`src/sif/core/models.py:347-384`，含「settings never bypass SearchOptions」注释）：**
```python
@dataclass
class SearchOptions:
    """Options for search."""

    limit: int = 10
    offset: int = 0
    ...
    # Fusion tunables (Phase 15, D-03): defaults equal today's hardcoded
    # behavior (k=60, equal weights), so every existing construction site and
    # unconfigured query stays byte-identical (SC1). CLI flags and MCP request
    # fields resolve INTO these fields; settings never bypass SearchOptions.
    rrf_k: int = 60
    bm25_weight: float = 1.0
    vector_weight: float = 1.0
```
→ 追加 `anchor_terms: list[str] | None = None`（默认 None = 无锚点；`[]` = 显式无锚点，绕过 resolver）。`dataclasses.replace` 自动扇出，无需新增开关字段（D-04/D-08）。

---

### `src/sif/search/hybrid.py` (service / router, request-response)

**Analog:** 自身 `SearchPipeline.search` 的 lex 分支与 `_parse_query_prefix`。

**lex 分支形状（`src/sif/search/hybrid.py:352-356`）——ANCHOR 分支照此：**
```python
        # Route to appropriate search mode
        if search_type == SearchType.BM25:
            # BM25-only: the identity check is never evaluated (no vectors are
            # touched, so there is nothing to distrust) and nothing is marked.
            results = self.hybrid.bm25.search(parsed_query, options)
            return enrich_results(self.db, self._apply_snippets(results, parsed_query))
```

**ANCHOR 分支目标形状（research Pattern 2）：**
```python
        if search_type == SearchType.ANCHOR:
            terms, resolution = self._resolve_anchor_terms(parsed_query, options)
            opts = replace(options, anchor_terms=terms or None)
            results = self.hybrid.bm25.search(parsed_query, opts)
            self.last_anchor_resolution = resolution          # 运行级元数据，不进 SearchResult
            return enrich_results(self.db, self._apply_snippets(results, parsed_query))
```

**前缀解析（`src/sif/search/hybrid.py:528-544`）——提升为模块级 `PREFIX_ROUTES` 并加 `anchor:`：**
```python
    def _parse_query_prefix(self, query: str) -> tuple[str, SearchType]:
        """Parse query prefix to determine search mode.
        ...
        """
        prefix_map = {
            "lex:": SearchType.BM25,
            "vec:": SearchType.VECTOR,
            "hyde:": SearchType.HYDE,
            "expand:": SearchType.EXPAND,
        }
        for prefix, search_type in prefix_map.items():
            if query.startswith(prefix):
                return query[len(prefix) :].strip(), search_type
        return query, self._default_search_type_enum()
```

**失败降级范式（一处 warning + 继续，`src/sif/search/hybrid.py:406-407`）——resolver fail-open 照此：**
```python
            except Exception as e:
                logger.warning(f"Query expansion failed: {e}")
```

**注意：** `_apply_snippets(results, parsed_query)`（`:480`）与 lex 分支一致，确保 snippet 用原 query（ANC-02）。

---

### `src/sif/mcp/backend.py` (service / router, request-response)

**Analog:** 自身 `_PREFIX_ROUTES` 与 BM25 分支。

**前缀表（`src/sif/mcp/backend.py:120-129`）：**
```python
# D-15/D-17: the same prefix map ``SearchPipeline._parse_query_prefix`` uses.
# The backend consults it BEFORE any load decision so a ``lex:`` query never
# pays a model load and every other route strips its prefix before the
# BM25 degrade.
_PREFIX_ROUTES: dict[str, SearchType] = {
    "lex:": SearchType.BM25,
    "vec:": SearchType.VECTOR,
    "hyde:": SearchType.HYDE,
    "expand:": SearchType.EXPAND,
}
```
→ 建议从 `hybrid.py`/`core` 共享 `PREFIX_ROUTES` 常量替代这份副本，加入 `"anchor:": SearchType.ANCHOR`（research Pattern 3，结构上消灭漂移）。

**prefix-first 拆分（`src/sif/mcp/backend.py:137-147`）：**
```python
def _split_query_prefix(query: str, default_search_type: str) -> tuple[str, SearchType]:
    """Mirror the pipeline's prefix routing without constructing a pipeline.
    ...
    """
    for prefix, search_type in _PREFIX_ROUTES.items():
        if query.startswith(prefix):
            return query[len(prefix) :].strip(), search_type
    return query, _DEFAULT_SEARCH_TYPES.get(default_search_type, SearchType.HYBRID)
```

**直连 BM25 分支（`src/sif/mcp/backend.py:486-495`）——ANCHOR 分支照此形状，且只走规则锚点、绝不写缓存：**
```python
            if search_type is SearchType.BM25:
                # D-15: prefix-first BM25 bypasses the loader entirely; the
                # prefix is stripped so FTS sees the intended terms.
                core_results = BM25Searcher(conn).search(parsed_query, options)
                core_results = enrich_results(conn, core_results)
                return _with_suggestions(
                    conn,
                    parsed_query,
                    _map_core_results(core_results, _page_checksums(conn, core_results)),
                )
```
→ 新增 `if search_type is SearchType.ANCHOR:` 分支：规则锚点 → `replace(options, anchor_terms=...)` → `BM25Searcher`，**早于 `_ensure_embedder()`**，不构造 resolver/cache（Pitfall 10：MCP 只读）。

---

### `src/sif/cli/commands/search.py` (controller / CLI, request-response)

**Analog:** 自身 `query_cmd`。

**`SearchOptions` 构建范式（`src/sif/cli/commands/search.py:1226-1242`，flag > setting > default）：**
```python
        options = SearchOptions(
            limit=limit,
            offset=offset,
            min_score=min_score,
            include_content=full,
            include_highlights=True,
            explain=explain,
            candidate_limit=resolve_candidate_limit(candidate_limit, settings),
            intent=intent,
            rrf_k=rrf_k if rrf_k is not None else settings.rrf_k,
            bm25_weight=bm25_weight if bm25_weight is not None else settings.bm25_weight,
            vector_weight=(vector_weight if vector_weight is not None else settings.vector_weight),
            per_chunk=per_chunk,
            filter=filter_node,
        )
```
→ `--anchor` 新增为 Click flag（与 `--rerank` 并列，`:1117-1121`），解析后 prepend `anchor:` 前缀给「交给 pipeline 的那一次调用」，并写 `options.anchor_terms`。

**`--rerank` flag 声明范式（`src/sif/cli/commands/search.py:1116-1121`）：**
```python
@click.option(
    "--rerank",
    is_flag=True,
    help="Rerank results (default: SIF_RERANK_ENABLED or false)",
)
```

**embedder 加载点（`src/sif/cli/commands/search.py:1268-1281`）——route-first 改造位置，ANCHOR 且无 rerank 时跳过整段：**
```python
        try:
            manager = EmbeddingManager.from_settings(settings)
            manager.load_model()
            # IN-07 (index.py precedent): the loaded model already knows its
            # dim, so remote backends are never billed for a throwaway probe.
            model_dim = manager.get_model_info().get("embedding_dim")
            embedding_dim = (
                model_dim if isinstance(model_dim, int) else len(manager.embed_single("probe"))
            )
        except ImportError as e:
            raise click.ClickException(f"Embedding backend not installed: {e}") from None
        except Exception as e:
            raise click.ClickException(f"Failed to load embedding model: {e}") from e
```

**`--explain` 输出位置（`src/sif/cli/commands/search.py:1441-1448`）——运行级元数据只进 stderr，不进 `to_dict()`：**
```python
            if explain:
                for r in results:
                    scores_str = ", ".join(
                        f"{k}={v:.4f}" for k, v in r.scores.items() if v is not None
                    )
                    if scores_str:
                        console.print(f"[dim]{escape(r.title)}: {scores_str}[/dim]")
```
→ 在 explain 段追加一行 `anchor: backend=... calls=... hits=... fallback=...`（stderr/console），**绝不**给 `SearchResult.to_dict()` 加键。

**DYM / history 必须用原始 `query`（`src/sif/cli/commands/search.py:1345-1347`）：**
```python
            suggestions = _zero_result_suggestions(db.connection, query, results)
            # D-08: one history row for an executed search (fail-soft).
            _record_query_history(db.connection, query, results, collections, settings=settings)
```
→ 这两处继续传**原始** `query`，不带 `anchor:` 前缀。

---

### `src/sif/config/settings.py` (config, batch)

**Analog:** 自身 `rerank_enabled`（opt-in 布尔范式）与 `resolve_candidate_limit`（解析范式）。

**opt-in 字段范式（`src/sif/config/settings.py:164-176`）：**
```python
    # Reranker settings
    # D-12 (Phase 16): rerank is opt-in. The False default keeps `sif search
    # query` on the zero-cost skip-rerank fast path — no reranker model is
    # constructed unless --rerank or SIF_RERANK_ENABLED=1 requests it.
    rerank_enabled: bool = Field(
        default=False,
        # Phrasing note: "sif search query" must be followed by whitespace or
        # the docs gate's bare-command regex (tests/test_docs.py) trips on the
        # generated configuration.md row.
        description="Enable reranking on the sif search query command "
        "(the default keeps the zero-cost skip-rerank fast path; "
        "pass --rerank or set 1 to enable)",
    )
```
→ 新增 `SIF_ANCHOR_*` 字段（`anchor_backend`、`anchor_model_path`、`anchor_api_base`、`anchor_api_key`（`repr=False, exclude=True`）、`anchor_timeout_ms`、`anchor_max_calls`、`anchor_cache_ttl`、`anchor_vocab_guard`），全部默认关/零成本。**生成器 prompt/版本/最多 10 术语不进 Settings**（D-06，模块常量）。

**解析/校验范式（`src/sif/config/settings.py:439-460`）——非 int 回落默认，防 MagicMock：**
```python
def resolve_candidate_limit(explicit: int | None, settings: object) -> int:
    """Resolve the reranker candidate cap: an explicit flag wins, else the setting.
    ...
    """
    value: object = (
        explicit if explicit is not None else getattr(settings, "rerank_candidate_limit", 20)
    )
    if not isinstance(value, int):
        value = 20
    return min(max(value, RERANK_CANDIDATE_LIMIT_MIN), RERANK_CANDIDATE_LIMIT_MAX)
```
→ `anchor_backend` 用 `str` 白名单校验而非 truthiness（Pitfall 6）。

---

### `scripts/generate_config_ref.py` (config / docs generator, transform)

**Analog:** 自身 `SECTIONS` 的 `Reranker Settings` 段；字段不在 `SECTIONS` 会被**静默丢弃**（`:313-315` 的 `continue`）。

**SECTIONS 范式（`scripts/generate_config_ref.py:157-186`）：**
```python
SECTIONS: list[tuple[str, list[str]]] = [
    ("Application Settings", ["app_name", "debug", "log_level"]),
    ("Database Settings", ["db_path", "lock_wait_timeout"]),
    (
        "Embedding Model Settings",
        [
            "model_name",
            ...
        ],
    ),
    ("API Settings", ["api_key", "api_base"]),
    (
        "Reranker Settings",
        [
            "reranker_model_name",
            ...
            "rerank_relative_threshold",
        ],
    ),
    ...
```
→ 追加 `("Anchor Settings", ["anchor_backend", "anchor_model_path", ...])`。建议补一条测试断言「`Settings.model_fields` 的每个键都出现在某个 SECTION」。

---

### `src/sif/search/anchor.py` (**新**, service / provider / utility)

本阶段唯一真正新增的模块。没有单一 exact analog；用以下三个源组合：

**A. 可选组件形状（`src/sif/search/expansion.py:1-40`）——构造函数接收可选依赖、方法返回纯数据：**
```python
"""Query expansion for improving search recall."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import numpy as np

from sif.embedding.roles import embed_queries, embed_query
from sif.utils.logging import get_logger


logger = get_logger(__name__)

if TYPE_CHECKING:
    from sif.core.models import Embedder
    from sif.embedding.manager import EmbeddingManager


class QueryExpansion:
    """..."""

    def __init__(
        self,
        embedding_manager: EmbeddingManager | None = None,
        expansion_factor: int = 3,
    ) -> None:
        ...
```

**B. lazy llama import（`src/sif/embedding/embedder.py:327` 与 `:345-352`）——必须 lazy，否则 Docs job 崩：**
```python
            from llama_cpp import Llama  # noqa: PLC0415
```
```python
        self.model = Llama(
            model_path=str(self.model_path),
            n_ctx=n_ctx,
            n_threads=n_threads,
            n_gpu_layers=n_gpu_layers,
            embedding=True,
            verbose=verbose,
        )
```
→ `AnchorGenerator` 自建 `Llama(..., embedding=False)`，绝不复用 `LlamaCppEmbedder` 实例（`embedding=True`）。

**C. 冻结 prompt / 解析纯函数 / chat template / deadline（research Pattern 4 + 5，逐字可用）：**
```python
PROMPT_VERSION = "anchor.v1"      # 任何 prompt 文本改动必须 bump
MAX_ANCHOR_TERMS = 10             # GEN-01 冻结，不做 Settings
_LIST_PREFIX = re.compile(r"^[\s\-\*•\d\)\.]+")

def parse_terms(text: str, *, limit: int = MAX_ANCHOR_TERMS) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for raw in text.splitlines():
        term = _LIST_PREFIX.sub("", raw).strip().strip("\"'`").lower()
        if not term or len(term) > 64 or len(term.split()) > 6:
            continue
        if not re.search(r"[0-9a-z一-鿿]", term):
            continue
        if term in seen:
            continue
        seen.add(term)
        terms.append(term)
        if len(terms) >= limit:
            break
    return terms
```
```python
from llama_cpp import Llama, StoppingCriteriaList
from llama_cpp.llama_chat_format import Jinja2ChatFormatter

llm = Llama(model_path=str(path), n_ctx=2048, embedding=False, verbose=False)
template = llm.metadata.get("tokenizer.chat_template")
formatter = Jinja2ChatFormatter(
    template=template,
    eos_token=llm.detokenize([llm.token_eos()]).decode("utf-8"),
    bos_token=llm.detokenize([llm.token_bos()]).decode("utf-8"),
    stop_token_ids=[llm.token_eos()],
)
rendered = formatter(messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(query=q)}])

deadline = time.monotonic() + timeout_ms / 1000
def _expired(_tokens, _logits) -> bool:
    return time.monotonic() >= deadline

out = llm.create_completion(
    prompt=rendered.prompt,
    stop=rendered.stop,
    max_tokens=max_tokens,
    temperature=0.0,
    top_k=1,
    repeat_penalty=1.0,
    stopping_criteria=StoppingCriteriaList([_expired]),
)
```

**D. 缓存读写（复用 `LLMCacheRepository`，`src/sif/database/repositories.py:629-691`）：**
```python
model_name = f"anchor::{backend}::{model_id}"
prompt_hash = hashlib.sha256(
    f"{PROMPT_VERSION}\x00{model_id}\x00{backend}\x00{stripped_query}".encode("utf-8")
).hexdigest()
cached = LLMCacheRepository(conn).get(model_name, prompt_hash)      # None = miss/expired
if cached is None:
    response = generator.generate(stripped_query)
    terms = parse_terms(response)
    LLMCacheRepository(conn).set(
        model_name, prompt_hash, stripped_query,
        json.dumps({"version": 1, "terms": terms}, ensure_ascii=False),
        ttl_seconds=settings.anchor_cache_ttl or None,
    )
    if not conn.in_transaction:      # host 已开事务则让它提交（Pitfall 7）
        conn.commit()
else:
    terms = _parse_cached(cached)    # JSON 校验失败 → 视为 miss 并覆盖，不抛异常
```

**E. 远程后端零新增依赖（`src/sif/cli/commands/pull.py` 既有先例）：**
```python
from urllib import request
```

**关键约束：** 模块顶层只 import stdlib；`llama_cpp` / `jinja2` 全部在生成调用点 lazy import。resolver 只产出 terms，不写 `SearchResult`；运行级元数据（`generator_calls` / `cache_hits` / `anchor_backend` / `anchor_fallback_reason`）挂在 pipeline 属性。规则锚点后端（默认）纯函数、不写缓存。

---

### 缓存语义参考（`src/sif/embedding/cache.py`，只读，不修改）

**`EmbeddingCache.get/set` 的 TTL + commit 形状（`src/sif/embedding/cache.py:98-155`）**为跨进程命中与提交时机的参考：
```python
    def get(self, content: str, model_id: str = "default") -> list[float] | None:
    ...
    def set(...):
        ...
            conn.commit()
```
本阶段不复制这个类，只用它印证「只在成功时写、显式 commit」的既有语义；真正的缓存走 `LLMCacheRepository`（主 DB `llm_cache`）。

---

## Shared Patterns

### 路由前缀（跨 pipeline / MCP / CLI）
**Source:** `src/sif/search/hybrid.py:535-544` 与 `src/sif/mcp/backend.py:124-129`（两份同构字典）
**Apply to:** `hybrid.py`、`backend.py`（并建议抽共享 `PREFIX_ROUTES` 常量）
```python
PREFIX_ROUTES: dict[str, SearchType] = {
    "lex:": SearchType.BM25,
    "vec:": SearchType.VECTOR,
    "hyde:": SearchType.HYDE,
    "expand:": SearchType.EXPAND,
    "anchor:": SearchType.ANCHOR,
}
```

### 错误处理 / CLI 转换
**Source:** `src/sif/cli/commands/search.py:1268-1281`
**Apply to:** 所有新 CLI 路径
```python
        except ImportError as e:
            raise click.ClickException(f"Embedding backend not installed: {e}") from None
```
预算超限 `AnchorBudgetExceeded(RuntimeError)` 在 CLI 层转 `click.ClickException`；日志用 `logger.warning` 到 stderr（`get_logger(__name__)`）。

### lazy optional imports
**Source:** `src/sif/embedding/embedder.py:327`
**Apply to:** `sif/search/anchor.py` 全部生成器/远程后端
```python
            from llama_cpp import Llama  # noqa: PLC0415
```
Docs Validation job 只装 `.[dev]`，任何顶层 `llama_cpp` / `jinja2` import 都会让 `import sif` 崩。

### Settings 不绕过 SearchOptions
**Source:** `src/sif/core/models.py:378-384` 注释 + `query_cmd` options 构建
**Apply to:** `anchor_terms` 是唯一注入点；flag/settings 都解析进 `SearchOptions`，pipeline 只读 options。

### generator-owned docs
**Source:** `make docs-generate`（`Makefile:73`）+ `scripts/generate_config_ref.py` / `generate_cli_ref.py`
**Apply to:** `docs/configuration.md` / `docs/cli-reference.md` **只重生成、绝不手改**；新字段必须进 `SECTIONS`。hand-maintained 用户文档单独维护（LFM Open License v1.0 条款、experimental / 默认关闭 / 成本 / 隐私）。

### 静态守卫测试
**Source:** `tests/test_docs.py`（bare-command regex + docs diff gate 风格）
**Apply to:** `tests/test_packaging_assets.py`（`src/sif/**/*.gguf` 为空 + pyproject 无 gguf include）

---

## Test Pattern Assignments

### `tests/unit/search/test_anchor.py`（新）
**Analog:** `tests/unit/search/test_hybrid.py` + `tests/unit/search/test_bm25.py`
**Fixtures:** 复用 `tests/support/bench.py:100 build_bench_db`（真 sqlite + FTS）与 `:186 load_fixture_queries`；fake generator 建议放 `tests/support/` 或测试模块内。
覆盖：规则表/解析/缓存命中（同实例 + 跨实例）/fail-open（异常、超时、预算）/词表守卫/无网络（monkeypatch `socket.socket`）/预算超限。

### `tests/unit/cli/test_search_anchor.py`（新）
**Analog:** `tests/unit/cli/test_search.py:42-60` 的 `_query_settings_mock`（显式字段白名单，Pitfall 10）
```python
def _query_settings_mock(**overrides: object) -> MagicMock:
    """Explicit settings mock enumerating every field query_cmd reads.
    ...
    """
    fields: dict[str, object] = {
        "model_name": "all-MiniLM-L6-v2",
        "reranker_model_name": None,
        "reranker_model_path": None,
        "rerank_enabled": False,
        "rerank_candidate_limit": 20,
        "rerank_relative_threshold": 0.5,
        "model_dump": lambda: {"model_name": "all-MiniLM-L6-v2"},
    }
    fields.update(overrides)
    return MagicMock(**fields)
```
→ 新增 `anchor_backend="rules"` 等默认值；断言 `--anchor` 等价前缀、`EmbeddingManager.from_settings` 未被调用（patch 为 `AssertionError`）、`--explain` stderr 行、失败单次告警。

### 快照兼容（必须保持）
**Analog:** `tests/unit/search/test_hybrid.py:835` 起 `SNAPSHOT`（精确字典快照）
→ 默认路径 `SearchResult.to_dict()` 键集不变；锚点元数据只走 pipeline 属性 + CLI stderr，绝不进快照。

### `tests/unit/search/test_bm25.py`（扩展）
**Analog:** 自身 `test_build_fts_query_*`
→ 钉死两类：`_build_fts_query("hello world") == '"hello"* AND "world"*'`（默认逐字节）；锚点存在时 OR 短语形式。

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/sif/search/anchor.py`（生成器/远程后端部分） | provider | request-response | 仓库无 LLM 生成组件（`LlamaCppEmbedder` 是 `embedding=True`，不可复用）；按 RESEARCH Pattern 4/5 实现，并用 `expansion.py` + lazy import 范式组合 |
| 远程 OpenAI-compatible 后端 | provider | request-response | 无现成 remote-generation analog；仅 `pull.py` 的 `urllib.request` 先例 |

---

## Metadata

**Analog search scope:** `src/sif/{core,search,mcp,cli,config,database,embedding}`, `scripts/`, `tests/{unit,test_docs.py,support}`
**Files scanned:** ~20（含逐行读取 14 个 analog/扩展点）
**Pattern extraction date:** 2026-11-28
**Tracked-source check:** 全部 analog 经 `git ls-files` 校验为 tracked
