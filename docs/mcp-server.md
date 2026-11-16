# MCP Server

SIF includes a Model Context Protocol (MCP) server built on the official Python
SDK (`mcp>=2.3.0,<3`). It gives AI assistants search, retrieval, and discovery
access to your local index, with citation-grade structured output.

## Overview

The Model Context Protocol is an open protocol that connects AI systems to
external data sources. SIF's MCP server lets assistants:

- Search document collections (hybrid, BM25-only, or vector-only)
- Retrieve exact documents and line ranges for citation
- Discover filterable metadata keys and values
- Inspect indexing status

All seven tools are read-only. None of them mutates the index, and none accepts
a filesystem target path.

## Architecture

```
+-----------------+      +-------------------------+      +--------------+
|   AI Assistant  |<---->|   SIF MCP server        |<---->|   SIF Index  |
| (Claude, etc.)  |      | (SDK v2: stdio / HTTP)  |      |   (SQLite)   |
+-----------------+      +-------------------------+      +--------------+
```

The implementation lives in `src/sif/mcp/`:

| Module | Responsibility |
|--------|----------------|
| `app.py` | Composition root: one SDK `MCPServer`, the tool/resource registration, the mounted Streamable HTTP app, and the stdio/HTTP runners |
| `tools.py` | The seven tool definitions, reviewed descriptions, read-only annotations, and the dual-channel result builder |
| `backend.py` | `SearchBackend`: async wrapper over SIF search, retrieval, discovery, and status |
| `protocol.py` | The SIF tool input/output Pydantic models (the `outputSchema` source) |
| `watch_host.py` | The optional embedded watcher lifespan (`SIF_MCP_WATCH=1`) |
| `cli.py` | Thin entry points used by the `sif mcp` CLI commands |

The SDK owns protocol negotiation, sessions, and era routing. SIF supplies the
backend, the tool set, and the watch lifespan around it.

### Protocol versions

One server answers both handshake-era clients and the stateless 2026-07-28 era:

- **2024-11-05, 2025-03-26, 2025-06-18, 2025-11-25**: normal `initialize`
  handshakes, then `tools/list` / `tools/call`.
- **2026-07-28**: requests carry `MCP-Protocol-Version: 2026-07-28`,
  `Mcp-Method`, `Mcp-Name`, and `_meta`; no `initialize` and no session id are
  required.

The server advertises `outputSchema` and returns `structuredContent` in every
era. Legacy clients continue to receive the compact JSON text payload they
parse today; the structured channel is additive.

## Transport Types

### stdio transport

Uses standard input/output for communication. This is the transport the Claude
Code plugin uses by default.

```bash
sif mcp stdio
```

All diagnostics go to stderr; stdout carries protocol frames only. The
embedding model is not loaded at startup — the first vector query loads it
lazily.

### HTTP transport

Serves the SDK Streamable HTTP endpoint on a FastAPI parent app.

```bash
sif mcp http --host 127.0.0.1 --port 8080
```

**HTTP endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/mcp` | POST | Streamable HTTP message endpoint |
| `/mcp` | GET | Server-Sent Events stream |

The default bind is `127.0.0.1:8080` (`SIF_MCP_HOST` / `SIF_MCP_PORT` change
the defaults). The mounted app answers JSON responses rather than SSE-only
streams, preserving SIF's historical client behavior.

### daemon transport

Runs the HTTP transport as a detached background process using the same POSIX
double-fork lifecycle as `sif watch`.

```bash
sif mcp daemon
sif mcp daemon --host 127.0.0.1 --port 8080
sif mcp daemon --stop
```

- PID file: `<db>.mcp.pid` by default (`--pid-file` overrides). It is distinct
  from the watch daemon's `<db>.watch.pid`, so a watch daemon and an MCP daemon
  can serve one index at the same time.
- Log file: `mcp.log` in the platform log directory (`--log-file` overrides).
- The daemon arms quietly on a schema-ready, model-free backend before binding;
  a bind failure exits non-zero and removes the PID file.
- The daemon is POSIX-only. On Windows the command refuses with the shared
  POSIX-fork cause/remedy; run `sif mcp http` in the foreground instead.

## Available Tools

Every tool carries `readOnlyHint: true` and `openWorldHint: false`. These
annotations describe behavior; they do not auto-approve calls or enable
prompt-free execution — the host's approval rules still apply.

Each tool returns two channels: the compact JSON text payload legacy clients
parse, and `structuredContent` matching the tool's `outputSchema`.

### query

Hybrid search: BM25 full-text search, vector semantic search, and weighted RRF
fusion. Query expansion matches the CLI. Reranking is opt-in.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Search query |
| `collections` | array | No | Collection names to search |
| `limit` | integer | No | Maximum results (default: 10) |
| `offset` | integer | No | Absolute row skip for pagination (default: 0) |
| `filter` | object | No | Shared filter AST (see `metadata`) |
| `per_chunk` | boolean | No | Group by chunk instead of document (default: false) |
| `min_score` | number | No | Minimum score threshold (default: 0.0) |
| `rerank` | boolean | No | Force reranking on/off; omitted follows `SIF_RERANK_ENABLED` |
| `rrf_k` | integer | No | RRF constant (default: server `SIF_RRF_K` or 60) |
| `bm25_weight` | number | No | BM25 fusion weight (default: server setting) |
| `vector_weight` | number | No | Vector fusion weight (default: server setting) |

Each result carries `doc_id`, `path`, `title`, `score`, `snippet`,
`line_start`, `line_end`, `content_hash`, `highlights`, and `metadata`
(including `vectors_stale`). `suggestions` carries display-only did-you-mean
rewrites on a zero-result query.

### get

Retrieve one document by path or docid, optionally limited to a line range.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path_or_docid` | string | Yes | Document path or ID |
| `from_line` | integer | No | 1-based first line |
| `max_lines` | integer | No | Maximum lines to return |

The response carries `doc_id`, `path`, `title`, `content`, `content_hash`, and
an inclusive `line_start`/`line_end` range: `1..N` for a full document read or
the requested range for a ranged read.

### multi_get

Batch retrieve documents matching a glob pattern.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `pattern` | string | Yes | Glob pattern (for example `notes/*.md`) |
| `max_bytes` | integer | No | Maximum total bytes returned |

Every returned document carries its full `1..N` line range and stored
`content_hash`.

### status

Get indexing status for all collections. Takes no parameters.

### metadata

Report filterable metadata keys, value types, document counts, numeric ranges,
and exact remaining window counts. Accepts the same filter grammar as `query`;
`path` and `mtime` are reported through `builtIns`. The response is the frozen
Phase 20 discovery envelope (`documents`, optional `filteredDocuments`,
`totalKeys`, `remainingKeys`, `skippedKeys`, `builtIns`, `keys`).

### lex_search

Lexical BM25 search only, matching the CLI's BM25-only search subcommand.
Supports `filter`, `offset`, and `min_score`; no expansion and no reranking.

### vec_search

Vector semantic search only, matching the CLI's vector-only search subcommand.
Supports `filter`, `offset`, `per_chunk`, and `min_score`; no expansion and no
reranking. Requires an embedding model — without one the tool returns an error
naming the `docsif[embed]` install and model remedy.

### Resources

The server also exposes `docs://{doc_id}` (MIME type `text/markdown`) backed by
the same retrieval path. The `get` tool remains the citation-grade line-range
surface.

## Citation workflow

For answers that need evidence rather than discovery, use two stages:

1. Search (`query`, `lex_search`, or `vec_search`) to find candidates. The
   result's `snippet`, `line_start`, and `line_end` describe the search-time
   window, not a citation.
2. Retrieve the source with `get` (or `multi_get`) and cite the `doc_id` plus
   the `line_start`-`line_end` range returned by `get`. Quote only text
   returned by `get`, never a snippet alone.

Surfaces worth reporting:

- `metadata.vectors_stale: true` — the result's vector embedding no longer
  matches the stored document; lexical matches remain valid.
- `content_hash` — the stored checksum. If the `query` and `get` hashes for
  one document differ, it changed between search and retrieval; re-read and
  cite the `get` values.

The plugin's `sif-cite` skill encodes this discipline for the agent.

## Configuration

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SIF_DB_PATH` | platform data dir (`.../sif/sif.db`) | SQLite database path |
| `SIF_MCP_HOST` | `127.0.0.1` | HTTP bind host |
| `SIF_MCP_PORT` | `8080` | HTTP bind port |
| `SIF_MCP_WATCH` | unset | Set to `1` to run the embedded watcher while serving |
| `SIF_RERANK_ENABLED` | unset | Enables reranking by default for `query` |
| `SIF_MODEL_NAME` | `Qwen/Qwen3-Embedding-0.6B` | Embedding model for vector search |

When `SIF_DB_PATH` is not set, the path is computed in the platform data
directory (via platformdirs) and created on first run —
`~/.local/share/sif/sif.db` on Linux, `~/Library/Application Support/sif/sif.db`
on macOS.

### CLI flags

- `--host` / `-h`, `--port` / `-p` — bind address (defaults from
  `SIF_MCP_HOST` / `SIF_MCP_PORT`).
- `--cors-origins` (repeatable) — browser origin allowlist. Defaults to
  `http://localhost:3000`, `http://127.0.0.1:3000`, `http://localhost:8080`,
  and `http://127.0.0.1:8080`.
- `--allowed-hosts` (repeatable, `mcp http` and `mcp daemon`) — additional
  accepted `Host` header values. The loopback defaults are always allowed and
  a literal `*` is dropped, so this flag can only add hosts.
- `--pid-file`, `--log-file`, `--stop` (`mcp daemon`) — daemon lifecycle.

## Installing the Claude Code plugin

The repository root is a Claude Code plugin and marketplace. The plugin's
`.mcp.json` starts the installed `sif` command (`sif mcp stdio`), so install
SIF first — the plugin adds no runtime dependencies of its own.

### Install SIF

The primary install includes the embedding stack:

```bash
uv tool install 'docsif[embed]'
```

The base install is BM25-only (keyword search, retrieval, status, metadata)
and skips the torch/embedding stack:

```bash
uv tool install docsif
```

On Linux, the embed install resolves CPU-only torch from the explicit
PyTorch CPU index declared in `pyproject.toml`
(`https://download.pytorch.org/whl/cpu`), so no CUDA stack is pulled in.

### Install the plugin

In Claude Code:

```text
/plugin install sif --marketplace zhangtaolab/SIF
```

Then connect the server. The plugin-provided `.mcp.json` runs `sif mcp stdio`
with no hardcoded database path — the installed CLI resolves its own default
(or `SIF_DB_PATH`).

A pre-existing manual `sif` MCP entry duplicates the plugin-provided server
until it is removed. Keep one registration to avoid two server processes.

### Zero-install fallback

The plugin supports a BM25-only, no-install fallback via `uvx`; the `sif`
command resolves from the plugin's cached copy of this repository:

```bash
uvx --from ${CLAUDE_PLUGIN_ROOT} sif mcp stdio
```

Point `.mcp.json` at that command only when the `sif` command is not installed.

### Manual MCP configuration

For hosts without plugin support, add the server manually:

```json
{
  "mcpServers": {
    "sif": {
      "command": "sif",
      "args": ["mcp", "stdio"]
    }
  }
}
```

Claude Desktop reads this from
`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS,
`%APPDATA%\Claude\claude_desktop_config.json` on Windows, or
`~/.config/Claude/claude_desktop_config.json` on Linux.

## Transport security

The HTTP transport always builds an explicit SDK `TransportSecuritySettings`
with DNS-rebinding protection enabled — never `None`, never `["*"]`:

- **Allowed hosts** default to loopback: `127.0.0.1`, `127.0.0.1:*`,
  `localhost`, `localhost:*`, `[::1]`, `[::1]:*`. `--allowed-hosts` values are
  unioned with these defaults.
- **Allowed origins** default to the CORS origins above. `--cors-origins`
  replaces them.
- A request with a bad `Host` header is rejected with **421 Misdirected
  Request**; a bad `Origin` is rejected with **403 Forbidden**; an allowed
  origin (or no `Origin`) is served normally.
- `/health` sits outside the SDK mount and carries a narrow `Host` guard over
  the same allowlist (bad `Host` → 421).
- A non-loopback bind without `--allowed-hosts` logs a warning and keeps the
  allowlist loopback-only rather than silently widening it.

There is no authentication layer: this is a local, loopback-oriented personal
server. Do not expose it to untrusted networks.

## Troubleshooting

### The server will not start

```bash
# Check whether the port is in use
lsof -i :8080

# Use another port
sif mcp http --port 8081
```

### The daemon will not start or stop

```bash
# Inspect the daemon log (platform log dir, file name mcp.log)
sif mcp daemon --log-file ./mcp.log
sif mcp daemon --stop
```

A bind failure removes `<db>.mcp.pid` and exits non-zero. On Windows, run the
foreground `sif mcp http` instead — daemonization requires POSIX fork.

### The host reports no tools

```bash
# List the MCP commands and confirm the installed plugin
sif mcp --help
```

Confirm the `sif` command is on the host's PATH (or use the `uvx` fallback),
and remove any duplicate manual `sif` MCP entry.

### Vector search fails

`vec_search` needs an embedding backend and may need to download a model on
first use. Install `docsif[embed]`; BM25 search, retrieval, metadata, and
status keep working without it.

### A 421 or 403 response from `/mcp`

The request's `Host` or `Origin` is not in the allowlist. Use a loopback
address, or pass the name explicitly:

```bash
sif mcp http --allowed-hosts myhost.local --cors-origins http://myhost.local:3000
```
