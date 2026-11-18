# Stack Research

**Domain:** v1.2 additions to an existing local hybrid search engine (DocSIF/SIF): metadata filtering, correctness/scale fixes, MCP SDK v2 modernization, measurable quality (Harrier/bge/rapidfuzz), CI + PyPI distribution
**Researched:** 2026-11-13
**Confidence:** HIGH — every version and migration surface below was verified directly against primary sources (PyPI JSON API, official docs, GitHub source at tag, Hugging Face model cards/configs, local runtime experiments with uv 0.13.7 and the installed locked deps). Method note: the `classify-confidence` seam rates the websearch/webfetch *channels* LOW; per research-philosophy ("official docs trump training data") and the approved v1.1 research precedent, claims cross-verified against primary sources are tagged HIGH/MEDIUM on evidence quality, and unverified leads stay LOW. Context7 MCP and the `ctx7` CLI were unavailable in this runtime; docs questions fell back to official documentation sites (recorded per item in Sources).

## Headline Verdict

**TWO new runtime dependencies, everything else is reuse.** v1.2 needs exactly:

1. **`mcp>=2.3.0,<3`** — the official MCP Python SDK v2 (`MCPServer`). This is an *adoption*, not an upgrade: SIF's MCP server is hand-rolled (623 LOC, protocol hardcoded `2024-11-05` at `src/sif/mcp/server.py:71`) and `pyproject.toml` has **no `mcp` dependency today** (the `mcp`/`http` extras are uvicorn-only placeholders).
2. **`rapidfuzz>=3.14.5,<4`** — measured replacement for `difflib` in did-you-mean (`src/sif/search/suggest.py`), per the locked DYM decision.

Zero new dependencies for: metadata filter AST + discovery + pagination (in-house parser + existing Pydantic), all correctness/scale fixes (stdlib `sqlite3` VACUUM/backup, schema changes, streaming batches), the personal known-item eval instrument (extend `benchmark.py`, v1.1 precedent), Harrier evaluation (locked sentence-transformers 5.4.1 already supports `prompt_name` — verified in installed source), bge-reranker-v2-m3 (existing `CrossEncoderReranker` in `rerank.py`, model-name swap), `sif models pull/status` (existing `hf_hub_download`/ModelScope code in `pull.py`, huggingface-hub 1.10.2 locked), CI matrix, PyPI trusted publishing, MCP Registry listing, and the Claude Code skill/plugin (Markdown + JSON manifests, no Python deps).

**Do not upgrade sentence-transformers for v1.2.** Locked 5.4.1 handles Harrier; 6.3.0 is a breaking major (MultiVectorEncoder, scoring fixes) with no v1.2 need — optional post-milestone upgrade with its migration guide.

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `mcp` (official Python SDK v2) | **2.3.0** (2026-10-02; pin `>=2.3.0,<3`) | Replace hand-rolled MCP protocol/transport with `MCPServer`; dual-era client serving; tool annotations; structuredContent/outputSchema | Locked decision (SDK v2). MIT, `requires-python >=3.10`, pure `py3-none-any` wheel. One server serves **all** handshake eras 2024-11-05 → 2025-11-25 **plus** the stateless 2026-07-28 era with no flags — verified `HANDSHAKE_PROTOCOL_VERSIONS`/`MODERN_PROTOCOL_VERSIONS` in `mcp_types/version.py`. SIF's current 2024-11-05 clients keep working (`OLDEST_SUPPORTED_VERSION = "2024-11-05"`). 2.0.0 stable landed 2026-07-28; 1.30.0 is the last maintenance 1.x. |
| `rapidfuzz` | **3.14.5 on py3.10 / 3.14.6 on py3.11+** (pin `>=3.14.5,<4`) | did-you-mean / suggestion ranking replacing `difflib` | Locked decision (measured swap). MIT (LICENSE verified). 3.14.6 (2026-08-30) requires py≥3.11; pip auto-resolves py3.10 users to 3.14.5 (2026-04-07) which ships cp310–cp314 wheels for win32/win_amd64/win_arm64, macOS x86_64+arm64, manylinux+musllinux x86_64+aarch64 — every v1.2 CI target covered. Zero runtime deps. C++ speed lets us drop the first-letter bucketing (the recall fix in the locked decision). |
| `sentence-transformers` | **keep locked 5.4.1** (latest 6.3.0, 2026-11-11; raise `embed` extra floor to `>=5.4.1`) | Harrier-OSS-v1-0.6b embeddings (`prompt_name`) + bge-reranker-v2-m3 (`CrossEncoder`) | `encode(prompt_name=...)` verified present in installed 5.4.1 (`sentence_transformer/model.py:220`). Harrier's config needs transformers ≥4.57.6; locked 5.5.4 satisfies it. 6.0.0 (2026-08-18) is a breaking major (ColBERT MultiVectorEncoder, transformers-v5 floor, half-precision scoring fixes) — no v1.2 feature needs it; defer with migration guide. |
| `llama-cpp-python` | **keep locked 0.3.35; latest 0.3.36** (2026-10-01; raise `all` extra floor to `>=0.3.35`) | Optional GGUF route for Harrier + existing GGUF embed/rerank | MIT, py≥3.8, **PyPI sdist-only** — prebuilt wheels come from the abetlen index (see Patterns). `Llama(embedding=True, pooling_type=LLAMA_POOLING_TYPE_LAST)` verified in v0.3.36 source (`LAST=3`, `UNSPECIFIED=-1` defers to GGUF metadata). |
| `torch` | **keep locked 2.11.0**; fleet resolves 2.14.1 (py3.10) / 2.15.0 (py3.11+) | sentence-transformers backend | **New constraint discovered:** torch 2.15.0 (2026-10-28) requires py≥3.11; last py3.10 release is 2.14.1. Linux PyPI wheels bundle CUDA (539 MB wheel + nvidia-cudnn-cu13 517 MB + nccl 207 MB + cusparselt/nvshmem/triton = multi-GB); macOS/Windows PyPI wheels are CPU-only (139/127 MB). Use the CPU index on Linux (verified recipe in Patterns). |
| `huggingface-hub` | **1.10.2 locked** (transitive via ST/ModelScope; already imported in `pull.py`) | `sif models pull/status` downloader | Already the code path in `src/sif/cli/commands/pull.py` (`hf_hub_download` + ModelScope `snapshot_download`). Extend, don't replace. Non-TTY silence via existing rich Console detection. |
| FastAPI + uvicorn | **keep** (locked 0.136.0 / 0.44.0) | HTTP host app for the SDK's ASGI transport | SDK v2's `streamable_http_app()` is a Starlette app; FastAPI (already a core dep) mounts it unchanged. mcp requires uvicorn≥0.31.1 — locked 0.44.0 satisfies. No new web framework. |
| SQLite via stdlib `sqlite3` | system (WAL already shipped v1.1) | `sif index vacuum`/backup, title FTS column, dedup, scan elimination | `VACUUM` and the online backup API are stdlib; FTS5 external-content schema changes are in-house. Zero deps (v1.1 precedent). |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `mcp-types` | 2.3.0 (auto, exact-pinned by `mcp`) | Protocol wire types (`mcp.types` is a permanent alias) | Transitive — never declare directly. Only deps: pydantic≥2.12 + typing-extensions. |
| `httpx2` | ≥2.10.0 (auto; **2.14.0 on py3.10**, 2.16.0 on py3.11+) | SDK's HTTP client (replaces httpx/httpx-sse) | Transitive. Same requires-python split-brain pattern as rapidfuzz: 2.15.0+ needs py≥3.11, so py3.10 resolves 2.14.0 (2026-10-18). TLS verifies via `truststore` (OS store) — containers may need `SSL_CERT_FILE`. |
| `mcp-codemod` | 0.1.3 (2026-08-01) | Automates v1-SDK→v2 renames | **Dev-only, optional, and mostly irrelevant to SIF**: it is a *community* tool (github.com/8crsk, libcst-based), NOT official — the official Python migration guide ships no codemod. It rewrites `FastMCP` v1 code; SIF's server is hand-rolled JSON-RPC, so the migration is a rewrite onto `MCPServer`, not a codemod pass. |
| Models (not libraries): `microsoft/harrier-oss-v1-0.6b`, `majentik/harrier-oss-v1-0.6b-GGUF-Q8_0`, `BAAI/bge-reranker-v2-m3` | see Integration Points | Evaluation candidates | Downloaded via existing HF/ModelScope paths; no packaging changes. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `astral-sh/setup-uv` **v10.3.3** (2026-10-28) | CI uv setup | SHA-pin `68559e99cc807c1eb7e9238fd43a15bba460eec2 # v10.3.3` (README's own pattern). `python-version` input only sets `UV_PYTHON` — it does **not** install Python; add `uv python install <ver>` where needed (Windows yoga smoke: no Python installed). `enable-cache: auto` on GitHub-hosted runners. |
| `actions/setup-python` **v7.1.0** (2026-10-22) | Alternative/adjunct interpreter setup | Fine for the matrix, but uv-first (`setup-uv` + `uv sync --frozen` + `uv run --frozen pytest`) matches the project's uv.lock workflow and the install-docs direction. |
| `pypa/gh-action-pypi-publish` **v1.14.3** (2026-10-20), use `@release/v1` | PyPI trusted publishing | `master` branch is sunset. `id-token: write` on the publish job only; `environment: pypi`; **attestations ON by default** (Sigstore, PEP 740; trusted-publishing flows only). Docker-based → Linux runners only; **cannot run inside reusable workflows**; build dists in a separate low-privilege job and pass via artifacts. |
| `mcp-publisher` CLI (MCP Registry, repo v1.8.9 2026-11-10) | Registry listing | `brew install mcp-publisher` (or release binaries); `login github` (device flow) or GitHub OIDC from Actions; `init` / `validate` / `publish`. Publishing is **not** a PR to the registry repo. |
| `uv` 0.13.x (local: 0.13.7) | Distribution + dev installs | `uv tool install` / `uvx` for end users; `uv build` for dists; index flags verified locally (see Patterns). |
| `claude plugin validate` | Claude Code plugin CI check | Validates `.claude-plugin/plugin.json`, component paths, MCP entries (MCP checks need Claude Code ≥2.1.281). No Python dependency. |
| Existing gates: pytest (fail_under=90), ruff, ty | Everything ships under them | CI matrix must run the full suite per cell; `black` in dev extras is redundant with `ruff format` — remove in the cleanup feature. |

## Integration Points (what the roadmap plans should touch)

### (a) MCP SDK v2 adoption — the one medium-cost migration

**Current surface (verified):** `src/sif/mcp/server.py` 193 LOC + `transports/http.py` 264 + `transports/stdio.py` 150 + `__init__.py` 16 = **623 LOC hand-rolled**, protocol string `"2024-11-05"` hardcoded (server.py:71), FastAPI-based HTTP, `SearchBackend` boundary already isolates search logic. No `mcp` package dependency exists today.

**Target shape (all verified against official docs):**

```python
from mcp.server import MCPServer            # canonical: mcp.server.mcpserver
from mcp.types import ToolAnnotations
from pydantic import BaseModel

mcp = MCPServer("sif", version="1.2.0")     # extras by keyword; positional order changed in v2

class SearchHit(BaseModel):
    path: str
    score: float
    snippet: str

@mcp.tool(
    title="Search notes",
    annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False),
)
def query(q: str, limit: int = 10) -> list[SearchHit]:
    """Hybrid search over the local knowledge base."""
    return backend.query(q, limit)          # existing SearchBackend, unchanged
```

- **structuredContent/outputSchema are automatic**: the return annotation *is* the output schema. Pydantic models → unwrapped schema; `list[...]`/scalars → wrapped `{"result": ...}`; `dict[str, ...]` → unwrapped. Results are validated before leaving the server (mismatch → `is_error=True`). Opt out per tool with `structured_output=False`. Attributes are snake_case (`result.structured_content`, `tool.output_schema`); wire JSON stays camelCase — if SIF serializes types manually anywhere, use `model_dump(by_alias=True, mode="json")` (silent wrong-shape otherwise).
- **Dual-era serving is free**: same `streamable_http_app()` and same stdio server answer 2024-11-05…2025-11-25 `initialize` handshakes and 2026-07-28 stateless per-request traffic with no flag. `stateless_http=True` only affects 2025-era clients (2026 traffic is inherently stateless — no `Mcp-Session-Id`). SIF's existing 2024-11-05 clients are **not** broken (`OLDEST_SUPPORTED_VERSION="2024-11-05"`).
- **HTTP transport**: transport params moved off the constructor onto `run()` / `streamable_http_app()` (`host`, `port`, `stateless_http`, `json_response`, `streamable_http_path`, `transport_security`, `max_request_body_size` default 4 MiB). `mount_path=` removed. Mount into the existing FastAPI app with the SDK lifespan, or you get `RuntimeError: Task group is not initialized`:

```python
async def lifespan(app):
    async with mcp.session_manager.run():
        yield
# FastAPI(lifespan=lifespan); app.mount("/mcp", mcp.streamable_http_app(json_response=True))
```

- **Host/Origin validation**: SDK auto-enables DNS-rebinding protection on loopback and exposes `transport_security` — replaces SIF's hand-rolled Origin check and closes the Host-header item.
- **stdio**: `mcp.run(transport="stdio")` replaces `transports/stdio.py`.
- **v1.1 embedded watch refresh**: re-wire the existing `queue.Queue` observer→asyncio bridge into the SDK lifespan (v1.1 pattern still applies; no janus).
- **Dependency weight**: mcp 2.3.0 adds ~12–15 transitive packages (mcp-types, httpx2+httpcore2+truststore, opentelemetry-api, pyjwt[crypto]→cryptography, sse-starlette≥3, python-multipart, jsonschema chain, typing-inspection; pywin32 on Windows). Largest is cryptography; no torch-class weight. **pydantic floor ≥2.12 is satisfied by locked 2.13.1.** `pydantic-settings` was *removed* from mcp's deps (SIF keeps its own).
- **Migration traps**: `mcp.server.fastmcp` imports raise `ModuleNotFoundError` (old-path fallback `except ImportError` still works); `except httpx.*` handlers silently never match (httpx replaced by httpx2); `McpError`→`MCPError`; `ctx.fastmcp`→`ctx.mcp_server`; low-level `Server` decorator API replaced by constructor `on_*` params (SIF doesn't use it — hand-rolled). `mcp-codemod` (community) does not apply to hand-rolled code.
- **Cost estimate: MEDIUM, one focused phase.** ~623 LOC of protocol/transport deleted, ~300–500 LOC of thin tool wrappers + lifespan wiring added; `SearchBackend` and all search logic untouched; MCP protocol-level tests rewritten; CLI untouched. Lazy embedder + query-pipeline parity are backend changes independent of the SDK swap.

### (b) rapidfuzz swap — small

`suggest.py` today: `difflib.get_close_matches(token, bucket, n=n, cutoff=0.75)` (line 266) + `SequenceMatcher(...).ratio()` (line 274), with first-letter bucketing. Replace with `rapidfuzz.process.extract(token, vocab, scorer=fuzz.WRatio, limit=n, score_cutoff=75)` (0–100 scale) and `fuzz.ratio(a, b)/100`; **drop the first-letter buckets** (rapidfuzz is fast enough for full-vocab scans at personal-KB scale — this is the locked recall fix). Keep the v1.1 ≤10 ms suggestion budget as the acceptance measurement; bench before/after per the locked "measured replacement" decision. Pin `>=3.14.5,<4`; no py3.10 cap needed (requires-python metadata routes 3.10 users to 3.14.5 automatically).

### (c) Harrier-OSS-v1-0.6b evaluation — no new deps, two routes

**Primary (sentence-transformers, verified model card + configs):** MIT, 0.6B params, **1024 dims**, 32,768 ctx, `Qwen3Model` (config `transformers_version: 4.57.6` — locked 5.5.4 OK), last-token pooling + L2 norm (automatic in ST), MTEB Multilingual v2 69.0, 94 languages.

```python
model = SentenceTransformer("microsoft/harrier-oss-v1-0.6b")
q = model.encode(queries, prompt_name="web_search_query")   # MANDATORY query-side
d = model.encode(documents)                                  # NO prompt on doc side
```

`config_sentence_transformers.json` (fetched): prompts `web_search_query`/`sts_query`/`bitext_query`, `default_prompt_name: null`, cosine. **Never set `default_prompt_name`** — it would also apply to document encoding. Locked 5.4.1 supports all of this (verified in installed source).

**Secondary (GGUF, optional):** `majentik/harrier-oss-v1-0.6b-GGUF-Q8_0` — Q8_0 only, 639 MB, MIT, **community quant with ~47 downloads/month** (low-adoption risk; the page has no llama-cpp-python guidance). Integration: `Llama(model_path=..., embedding=True, pooling_type=LLAMA_POOLING_TYPE_LAST, n_ctx=...)` + **manually prepend the query instruction** (`"Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery: "`) — llama-cpp has no `prompt_name` concept. `UNSPECIFIED` pooling defers to GGUF metadata; pass `LAST` explicitly and verify output parity against the ST route on a few fixtures before trusting it.

**Guard (locked decision):** Harrier and Qwen3-Embedding-0.6B are both 1024-dim — a width check silently accepts a bad switch. Store an **embedder identity marker** (model id + revision) with the vectors and refuse mixed-identity comparisons; default switch only on EN+ZH held-out win.

### (d) bge-reranker-v2-m3 low-latency option — config-level, zero deps

Official model card: Apache-2.0, 0.6B params, bge-m3 (XLM-RoBERTa) base, multilingual, "lightweight… fast inference". Card-sanctioned ST path:

```python
from sentence_transformers import CrossEncoder
model = CrossEncoder("BAAI/bge-reranker-v2-m3")
scores = model.predict([(query, passage) for passage in passages])
```

SIF already has `CrossEncoderReranker` (`src/sif/search/rerank.py:190`, default `cross-encoder/ms-marco-MiniLM-L-6-v2`) beside `LlamaCppReranker` — this is a **model_name/settings swap**, not new integration code. Note the card's example uses `max_length=512` (truncation interacts with chunk size — feed into the chunk-tuning sweep). The prior lead's "~0.9 s vs Qwen3 ~5 s per 50 candidates (PROPOR 2026)" is **UNVERIFIED (LOW)** — do not cite as fact; measure both rerankers with the existing bench instrument (latency percentiles already collected). FlagEmbedding/`FlagReranker` is the card's other path — **not needed** (extra dependency weight for no gain here).

### (e) CI matrix + PyPI trusted publishing — small/medium, no runtime deps

- Matrix: py3.10–3.13 × ubuntu-latest/macos-latest, full suite per cell (fail_under=90 applies everywhere); Windows = **smoke only** (locked): install + `sif --help` + BM25 index/search roundtrip. On yoga (no Python) the workflow must `uv python install` first — setup-uv's `python-version` input alone does not install Python.
- **Resolution splits CI must tolerate:** py3.10 cells get torch 2.14.1 / rapidfuzz 3.14.5 / httpx2 2.14.0; py3.11+ cells get torch 2.15.0 / rapidfuzz 3.14.6 / httpx2 2.16.0. All automatic via requires-python; pin nothing extra, but don't assert exact transitive versions in tests.
- CI should install torch from the CPU index (Linux) to avoid multi-GB CUDA downloads; GGUF tests either use the prebuilt cpu wheel index or stay optional/skipped in CI (llama-cpp source builds are slow).
- Publish workflow (verified README pattern): separate **build job** (`uv build` → hatchling, upload-artifact) and **publish job** (`environment: pypi`, `permissions: id-token: write`, `uses: pypa/gh-action-pypi-publish@release/v1` — v1.14.3). Attestations (PEP 740/Sigstore) generate automatically; keep them on. Configure the trusted publisher on PyPI for **docsif** (owner `zhangtaolab/sif`, workflow filename, environment `pypi`) before first run. Not inside a reusable workflow; Linux runner only.
- **Before publishing:** add the MCP Registry ownership marker to `README.md` (it becomes the PyPI description): `<!-- mcp-name: io.github.zhangtaolab/sif -->` on its own line (see (g)). Also add the `Programming Language :: Python :: 3.13` classifier (currently stops at 3.12).

### (f) Distribution: uv-first install docs + models UX — small

Verified end-user recipes (uv 0.13.7; index precedence confirmed by Linux-target resolution experiments):

```bash
# base (BM25-only, light — no torch):
uv tool install docsif
# with embeddings — macOS/Windows (PyPI torch is already CPU-only there):
uv tool install 'docsif[embed]'
# with embeddings — Linux, avoid multi-GB CUDA (CLI --index takes precedence over PyPI):
uv tool install 'docsif[embed]' --index https://download.pytorch.org/whl/cpu
# ephemeral: uvx docsif --help     |     pipx fallback: pipx install 'docsif[embed]'
# GGUF users: add the prebuilt wheel index for llama-cpp-python:
uv tool install 'docsif[all]' --index https://abetlen.github.io/llama-cpp-python/whl/cpu
```

- **Verified experiment:** `uv pip compile --python-platform x86_64-unknown-linux-gnu --index https://download.pytorch.org/whl/cpu` → `torch==2.15.0+cpu`; PyPI-only → `torch==2.15.0` (CUDA). (An earlier macOS-target test was platform-confounded — mac wheels carry no `+cpu` tag.) Project/dev pattern from the official uv PyTorch guide: `[[tool.uv.index]] name="pytorch-cpu" url="https://download.pytorch.org/whl/cpu" explicit=true` + `[tool.uv.sources] torch=[{index="pytorch-cpu"}]`.
- CPU wheel sizes (verified HEAD): torch 2.15.0+cpu cp313 manylinux = **210 MB**; 2.14.1+cpu cp310 = **196 MB**; **no cp310 build of 2.15.0+cpu** (py3.10 ceiling = 2.14.1 everywhere).
- llama-cpp-python: PyPI is sdist-only; prebuilt indexes `abetlen.github.io/llama-cpp-python/whl/{cpu,metal,cu118,cu121,cu122,cu123,cu124,cu125,cu130,cu132,rocm72,hip-radeon,vulkan}`. **Correction to the stale lead:** current 0.3.36 wheels are `py3-none` platform wheels (cpu covers win_amd64, macosx_11_0_arm64, manylinux/musllinux x86_64+aarch64; cu121 = manylinux_2_35_x86_64; metal = macosx_11_0_arm64) — **no CPython-version ceiling** on the latest builds; the docs' "Python 3.10–3.12" and the old cp312 stop apply to earlier cp-tagged wheels. pip's wheel cache keys on version, not `CMAKE_ARGS` → switching backends needs `--force-reinstall --no-cache-dir` (docs' own upgrade advice). macOS: arm64 Python or 10× slower.
- `sif models pull/status`: extend `pull.py`'s existing `hf_hub_download` / ModelScope `snapshot_download` paths (huggingface-hub 1.10.2 locked); add status/listing + non-TTY silence via rich. No new deps.

### (g) MCP Registry listing + Claude Code skill/plugin — small, no Python deps

**Registry (verified quickstart + package-types docs, repo v1.8.9):**
- `server.json`: `$schema: https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json`; `name: "io.github.zhangtaolab/sif"`; `description` ≤100 chars; `packages: [{ "registryType": "pypi", "identifier": "docsif", "version": "<published>", "transport": {"type": "stdio"} }]`.
- Ownership: PyPI verification reads an **`mcp-name: io.github.zhangtaolab/sif`** line (or HTML comment) from the package README/description; must exactly match `server.json` name; token needs a boundary after it (newline/whitespace/tag/`-->`) — no trailing period. **Add to README.md before the v1.1.x publish** so the first published version already carries it.
- Publish: `mcp-publisher login github` (device flow) or **GitHub OIDC from a workflow on zhangtaolab/sif** (cleanest for an org repo), then `mcp-publisher publish`. Registry validates namespace ownership; official PyPI only.

**Claude Code plugin (verified plugins-reference):** directory with `.claude-plugin/plugin.json` (`name` required, kebab-case; `claude-`/`anthropic-` prefixes reserved), `skills/<name>/SKILL.md`, and `.mcp.json` declaring the stdio server (e.g. `command: "sif", args: ["mcp", "stdio"]` — or `uvx --from docsif sif ...` for zero-install). Distribute via a `marketplace.json` (repo-hosted); validate with `claude plugin validate`. `${CLAUDE_PLUGIN_ROOT}` for bundled paths. Pure Markdown/JSON — nothing enters pyproject.

## Installation

```toml
# pyproject.toml deltas (the only dependency changes for v1.2):
[project]
dependencies = [
    # ... existing unchanged ...
    "mcp>=2.3.0,<3",          # NEW: official SDK v2 (MCPServer)
    "rapidfuzz>=3.14.5,<4",   # NEW: did-you-mean engine
]
classifiers = [ /* ... add "Programming Language :: Python :: 3.13" ... */ ]

[project.optional-dependencies]
embed = ["sentence-transformers>=5.4.1", "modelscope>=1.36.0", "numpy>=1.24.0"]  # floor raised to tested version
all   = ["sentence-transformers>=5.4.1", "llama-cpp-python>=0.3.35", "modelscope>=1.36.0", "numpy>=1.24.0", "openai>=2.0.0"]
dev   = ["pytest>=7.0.0", "pytest-cov>=4.0.0", "pytest-asyncio>=0.23.0", "ruff>=0.1.0", "ty>=0.0.1"]  # drop black (ruff format is the formatter)
# mcp/http extras: keep as thin compatibility aliases (mcp is now core); document as deprecated.
```

```bash
uv lock && uv sync --extra dev          # refresh lock (torch/ST/llama-cpp stay at locked versions)
# CI publish build: uv build  → dist/  → pypa/gh-action-pypi-publish@release/v1
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Official `mcp` 2.x SDK | Standalone `fastmcp` 3.x (jlowin) | Never for v1.2 — locked decision is the official SDK; standalone FastMCP is a different project with its own API (the local env's `fastmcp 3.2.4` is unrelated baggage). Only if official SDK v2 stalls on a needed feature. |
| Official `mcp` 2.x | Stay on `mcp` 1.x (`>=1.28,<2`, maintenance; last 1.30.0) | Only as a fallback if v2 migration blows up mid-phase: 1.x still gets fixes, but no 2026-era serving, and the milestone goal is 2026-ecosystem readiness. |
| Adopt SDK (rewrite 623 LOC) | Keep hand-rolled server, add 2026 era manually | Never — re-implementing dual-era negotiation, stateless envelopes, and schema validation by hand is exactly the maintenance debt the milestone removes. |
| `rapidfuzz` | `thefuzz`/python-Levenshtein | rapidfuzz is the maintained, faster, MIT-licensed standard with full wheel coverage; thefuzz adds a Levenshtein dep for less speed. |
| `rapidfuzz` now | `symspellpy` / `spellfix1` | Locked: symspellpy DEFER (revisit only >200k-term vocab), spellfix1 SKIP (ASCII-only core, sdist packaging tax, zero ZH benefit). |
| ST `CrossEncoder` for bge | `FlagEmbedding.FlagReranker` | Only if a FlagEmbedding-only feature is needed (e.g., layerwise minicpm rerankers). For bge-v2-m3 the card sanctions CrossEncoder and SIF already has the wrapper. |
| Harrier via ST 5.4.1 | Upgrade to ST 6.3.0 first | Only post-milestone: 6.x is a breaking major (migration guide at sbert.net/docs/migration_guide.html); nothing in v1.2 needs it. |
| Harrier ST route primary | GGUF (majentik Q8_0) primary | GGUF stays secondary: single community quant, ~47 downloads/mo, manual prompt/pooling handling. Prefer it only for llama.cpp-only deployments after parity checks. |
| `uv tool install` docs first | pipx-first docs | pipx remains a valid fallback (it even uses uv internally when available); uv-first matches the project's uv Python installation on bare machines (yoga). |
| CPU torch index on Linux | Default PyPI torch | Only on CUDA GPU machines that will actually use the GPU (SIF is CPU/local-first; multi-GB CUDA download is waste). |
| `setup-uv` + `uv run --frozen` | `setup-python` + pip | setup-python v7.1.0 is fine, but uv reuses the committed lockfile and caches better; keep one workflow style. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `pypdf` / `trafilatura` / `ebooklib` (PDF/HTML/EPUB) | **Locked out 2026-11-13** (selection research archived) | Markdown/text/code focus stays |
| Windows full-support shims | **Locked deferred to v2**; v1.2 = CI smoke only | Smoke job; mcp's pywin32 dep arrives automatically on win32, nothing to add |
| `spellfix1` | Locked SKIP: ASCII-only distance core, sdist-only tax, zero Chinese benefit | rapidfuzz |
| `symspellpy` | Locked DEFER: personal-KB vocab doesn't need it | rapidfuzz; revisit only >200k terms |
| ANN libs (`faiss`, `hnswlib`, `usearch`) | Locked SKIP: brute-force 75–150 ms @100k vectors is fine | sqlite-vec quantization+rescore is the ready escape hatch |
| Semantic/late-chunking libs | Locked SKIP (NAACL 2025 counter-evidence; last-token pooling mechanically incompatible) | Chunk size/overlap sweep + title breadcrumbs (in-house) |
| Standalone `fastmcp` (jlowin) | Different project; official SDK v2 is the locked target | `mcp>=2.3,<3` |
| `FlagEmbedding` | Extra dependency chain for a model SIF can run via existing CrossEncoder | `CrossEncoder("BAAI/bge-reranker-v2-m3")` |
| `mcp[ws]` / websockets, `streamablehttp_client`, `mount_path=`, `mcp.shared.version` | **Removed in SDK v2** (verified whats-new/migration guide) | `streamable_http_app()` mount; `mcp.types.version` |
| `except httpx.*` handling around MCP calls | httpx replaced by httpx2 — handlers silently never match | Audit during migration; catch `mcp.MCPError` |
| `default_prompt_name` for Harrier | Applies the query instruction to document encodings too (model card FAQ) | Explicit `prompt_name="web_search_query"` on query side only |
| Width-only embedder guard | Harrier and Qwen3-0.6B are both 1024-dim — silently accepts a bad switch (locked) | Embedder identity marker (model id + revision) |
| `black` in dev extras | Redundant — ruff format is the enforced formatter | Remove in Makefile/extras/pre-commit cleanup |
| `mypy` | Retired 2026-11-06; ty is the only type checker | `ty check src/sif` |
| `python-daemon` / `janus` / `ir-measures` / `ranx` at runtime | v1.1 precedent stands: stdlib double-fork, stdlib queue bridge, in-house metrics | Existing patterns; extend `benchmark.py` for the personal eval instrument |
| Unpinned `sentence-transformers>=2.2.0` floor (status quo) | Lets pip install pre-`prompt_name` releases for Harrier users | Floor `>=5.4.1` (tested) |
| CUDA torch by default on Linux | 539 MB wheel + 517 MB cudnn + 207 MB nccl + more, unused on CPU | `--index https://download.pytorch.org/whl/cpu` (verified) |

## Stack Patterns by Variant

**If Python 3.10 (the floor):**
- Everything resolves automatically via requires-python metadata: rapidfuzz 3.14.5, httpx2 2.14.0, torch 2.14.1 (2.15.0 dropped 3.10). No manual caps needed — but CI must include a 3.10 cell, and tests must not assert exact transitive versions.

**If Linux + embeddings:**
- Install torch from the CPU index: `uv tool install 'docsif[embed]' --index https://download.pytorch.org/whl/cpu` (verified: CLI `--index` takes precedence over PyPI first-match; Linux-target resolution yields `torch==2.15.0+cpu`). Dev/lockfile pattern: `[[tool.uv.index]] explicit=true` + `[tool.uv.sources]` torch pin (official uv PyTorch guide).

**If macOS / Windows:**
- PyPI torch is already CPU-only (139 MB arm64 / 127 MB win) — plain `uv tool install 'docsif[embed]'`. llama-cpp prebuilt: `metal` index (macosx_11_0_arm64, py3-none) / `cpu` index (win_amd64, py3-none). macOS needs arm64 Python for llama-cpp (10× slower otherwise).

**If GGUF Harrier (llama-cpp route):**
- `Llama(embedding=True, pooling_type=LLAMA_POOLING_TYPE_LAST)`; prepend the query instruction manually; verify parity vs the ST route on fixtures; `UNSPECIFIED` pooling defers to GGUF metadata (don't rely on it). Switching llama-cpp backends: `--force-reinstall --no-cache-dir` (pip cache ignores CMAKE_ARGS).

**If HTTP MCP in containers:**
- SDK v2 TLS uses `truststore` (OS trust store); set `SSL_CERT_FILE`/`SSL_CERT_DIR` or pass a custom ssl context if the container lacks OS roots. `stateless_http=True` for 2025-era horizontal scaling; 2026-era traffic is stateless regardless.

**If Windows smoke on yoga:**
- No Python installed (Store alias only): workflow runs `uv python install 3.12` after setup-uv (the `python-version` input only sets `UV_PYTHON`). Smoke = install + `sif --help` + BM25 roundtrip; no daemon/flock coverage (locked).

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| mcp 2.3.0 | pydantic ≥2.12 (locked **2.13.1** ✓), uvicorn ≥0.31.1 (locked **0.44.0** ✓), starlette/FastAPI (locked **0.136.0** ✓) | mcp pins `mcp-types==2.3.0` exactly; `pydantic-settings` no longer an mcp dep (SIF keeps its own) |
| mcp 2.3.0 on py3.10 | httpx2 **2.14.0** (2.15.0+ needs py≥3.11) | Automatic resolution; same split-brain pattern as rapidfuzz |
| mcp 2.x protocol support | SIF's current **2024-11-05** clients ✓ | `OLDEST_SUPPORTED_VERSION="2024-11-05"`; handshake eras through 2025-11-25 + modern 2026-07-28 |
| sentence-transformers 5.4.1 (locked) | transformers 5.5.4 (locked) ✓; Harrier config floor 4.57.6 ✓; `prompt_name` ✓ (verified installed source) | ST 6.x needs transformers ≥5,<6 — locked 5.5.4 would satisfy, but upgrade is breaking; defer |
| torch 2.15.0 | py ≥3.11 only | py3.10 ceiling = **2.14.1** (PyPI and CPU index alike); locked 2.11.0 unaffected |
| llama-cpp-python 0.3.36 prebuilt | py3-none platform wheels → py3.10–3.14 | Older cp-tagged wheels stopped at cp312; docs' "3.10–3.12" is stale for current builds |
| rapidfuzz 3.14.5 / 3.14.6 | py3.10 / py3.11+ respectively | Wheels cover all CI targets incl. win_arm64; MIT |
| gh-action-pypi-publish v1.14.3 | Trusted publishing + attestations (PEP 740) | Linux runners only; not in reusable workflows; `@release/v1` (master sunset) |
| setup-uv v10.3.3 | uv ≥0.13.x; `python-version` sets UV_PYTHON only | Add `uv python install` step for bare machines |
| MCP Registry server.json | schema 2025-12-11; `registryType: "pypi"` | README `mcp-name:` marker must match `name` exactly; description ≤100 chars |

## Corrections to Prior Leads (this session's unverified leads, now checked)

1. **mcp-codemod is community, not official** (8crsk/mcp-codemod 0.1.3, libcst). The official Python migration guide ships no codemod. Mostly irrelevant to SIF anyway (hand-rolled server, not v1 SDK code).
2. **Dual-era is broader than "2025/2026":** handshake eras 2024-11-05 / 2025-03-26 / 2025-06-18 / 2025-11-25 + modern 2026-07-28. SIF's 2024-11-05 clients survive the migration.
3. **llama-cpp "GPU wheels stop at cp312" is stale:** 0.3.36 cpu/metal/cu121 wheels are `py3-none` platform wheels with no CPython ceiling; the cp312 stop applied to older builds.
4. **majentik GGUF page has no `embedding=True` guidance** — that is our integration requirement, not documented upstream; low adoption (~47 downloads/mo) is a real risk flag.
5. **bge "~0.9 s vs Qwen3 ~5 s" (PROPOR 2026) remains UNVERIFIED (LOW)** — measure with `sif bench`; the model card only claims "fast inference".
6. **CPU torch wheels are ~196–210 MB** (not 140–190); CUDA-side verified components: 539 MB wheel + 517 MB cudnn + 207 MB nccl + cusparselt/nvshmem/triton (multi-GB total).
7. **New findings:** httpx2 has the same py3.10 resolution split (2.14.0); torch 2.15.0 dropped py3.10 (CI matrix implication); uv `--index <cpu>` *does* override PyPI for Linux targets (initial macOS test was platform-confounded).
8. **ST 6.3.0 exists (2026-11-11) but is not needed** — locked 5.4.1 already supports everything Harrier requires.

## Sources

Primary sources fetched 2026-11-13 (all direct, no proxies). Confidence per claim class: HIGH = read from registry/official docs/tagged source/local runtime; MEDIUM = single official source, not cross-checked; LOW = unverified lead.

- PyPI JSON API `pypi.org/pypi/{mcp,mcp-types,mcp-codemod,httpx2,rapidfuzz,sentence-transformers,llama-cpp-python,torch,nvidia-cudnn-cu13,nvidia-nccl-cu13}/json` — versions, requires_python, requires_dist, wheel filenames/tags/sizes, upload dates (HIGH)
- `py.sdk.modelcontextprotocol.io/v2/whats-new/` and `/v2/migration/` — MCPServer rename, dual-era serving, transport params, lifespan mount, mcp-types/httpx2 split, removals, snake_case/by_alias (HIGH)
- `py.sdk.modelcontextprotocol.io/servers/structured-output/` and `/servers/tools/` — outputSchema derivation/wrapping/validation, `ToolAnnotations(read_only_hint=...)` (HIGH)
- GitHub raw `modelcontextprotocol/python-sdk` main: `src/mcp-types/mcp_types/version.py` — protocol version tuples, OLDEST_SUPPORTED_VERSION (HIGH); `src/mcp/types/version.py` alias shim (HIGH)
- `huggingface.co/microsoft/harrier-oss-v1-0.6b` (card, raw README, `config.json`, `config_sentence_transformers.json`) — specs, pooling, prompts, license (HIGH); `huggingface.co/majentik/harrier-oss-v1-0.6b-GGUF-Q8_0` — quant, size, license, absence of llama-cpp guidance (HIGH); `huggingface.co/BAAI/bge-reranker-v2-m3` — license, CrossEncoder/FlagReranker usage, max_length example (HIGH)
- GitHub raw `abetlen/llama-cpp-python` v0.3.36: `llama_cpp/llama.py`, `llama_cpp/llama_cpp.py` — embedding/pooling_type params, LLAMA_POOLING_TYPE constants (HIGH); `llama-cpp-python.readthedocs.io/en/latest/` — wheel indexes, CMAKE_ARGS, platform notes (HIGH, docs partially stale on Python tags); `abetlen.github.io/llama-cpp-python/whl/{cpu,cu121,metal}/llama-cpp-python/` — actual wheel tags (HIGH)
- GitHub raw `rapidfuzz/RapidFuzz` main LICENSE — MIT (HIGH); installed sentence-transformers 5.4.1 source (`sentence_transformer/model.py`) — prompt_name (HIGH, local runtime)
- GitHub API releases: `pypa/gh-action-pypi-publish` v1.14.3, `astral-sh/setup-uv` v10.3.3, `actions/setup-python` v7.1.0, `modelcontextprotocol/registry` v1.8.9 (HIGH); raw READMEs: gh-action-pypi-publish `release/v1` (trusted publishing/attestations YAML), setup-uv (inputs, SHA pin, matrix) (HIGH)
- GitHub raw `modelcontextprotocol/registry` main: README, `docs/modelcontextprotocol-io/quickstart.mdx`, `docs/modelcontextprotocol-io/package-types.mdx` — mcp-publisher, server.json schema 2025-12-11, PyPI `mcp-name` marker + boundary rules (HIGH)
- `docs.astral.sh/uv/guides/tools/`, `/guides/integration/pytorch/`, `/reference/cli/` — uv tool install/uvx, explicit-index pattern, CPU/CUDA indexes (HIGH); `pipx.pypa.io/stable/` — isolation, uv-under-the-hood (HIGH)
- `download.pytorch.org/whl/cpu/torch/` + HEAD requests — CPU wheel availability/sizes, cp310 ceiling (HIGH); local `uv 0.13.7` resolution experiments (`uv pip compile --python-platform x86_64-unknown-linux-gnu`) — index precedence (HIGH, local runtime)
- `code.claude.com/docs/en/plugins-reference` — plugin.json, skills layout, .mcp.json, marketplace, validate (HIGH)
- SIF repo inspection: `src/sif/mcp/*` LOC + protocol string, `src/sif/search/suggest.py` difflib call sites, `src/sif/search/rerank.py` CrossEncoderReranker/LlamaCppReranker, `src/sif/cli/commands/pull.py` downloaders, `uv.lock` locked versions, `pyproject.toml` extras (HIGH, local)
- WebSearch discovery only (LOW until primary-verified above): mcp v2 release coverage, Harrier launch coverage; PROPOR 2026 reranker latency claim stayed LOW (not cited as fact)
- Seam: `gsd-tools query research-plan` (12 questions; context7 routed items fell back to official docs — context7 MCP and ctx7 CLI unavailable), `classify-confidence` (channel tiers websearch/webfetch=LOW, context7=MEDIUM; evidence-based upgrades documented in header), `research-store` (12 digests cached, verified hits)

---
*Stack research for: SIF v1.2 Search Precision and Agent Experience*
*Researched: 2026-11-13*
