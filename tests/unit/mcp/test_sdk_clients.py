"""SDK client matrix for the SIF MCP server (Phase 22 D-04).

``mode="legacy"`` drives the initialize handshake (2025-11-25) and
``mode="auto"`` negotiates 2026-07-28. Both are exercised over the in-process
server, the mounted ASGI app, and a real ``sif mcp stdio`` subprocess. The
initialize result's ``serverInfo`` is the wire-level release-identity proof:
the golden transcripts normalize ``serverInfo.version``, so this assertion is
where the served version must equal ``APP_VERSION``.

The stdio subprocess gets a temporary ``HOME`` and an explicit ``--index`` so
the developer's platform database is never opened.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx2
import pytest
from mcp import Client, StdioServerParameters
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult

from sif._version import __version__
from sif.mcp.app import SERVER_NAME, build_server, create_http_app


_REPO_ROOT = Path(__file__).resolve().parents[3]
_MODES = ["legacy", "auto"]


def _child_env(home: Path) -> dict[str, str]:
    """Child environment: stripped SIF_, temp HOME, color disabled."""
    env = {key: value for key, value in os.environ.items() if not key.startswith("SIF_")}
    env.pop("FORCE_COLOR", None)
    env["NO_COLOR"] = "1"
    env["HOME"] = str(home)
    return env


def _assert_status_result(result: CallToolResult) -> None:
    """The dual-channel invariant: text parses to the structured mapping."""
    assert result.is_error is False
    assert result.structured_content is not None
    assert json.loads(result.content[0].text) == result.structured_content
    assert set(result.structured_content) == {"collections", "total_documents"}


async def _assert_client_matrix(client: Client) -> None:
    """List tools and call status through one connected client."""
    tools = await client.list_tools()
    assert [tool.name for tool in tools.tools] == [
        "query",
        "get",
        "multi_get",
        "status",
        "metadata",
        "lex_search",
        "vec_search",
    ]

    result = await client.call_tool("status", {})
    _assert_status_result(result)

    # D-04 wire identity: the served version is the release version.
    assert client.server_info is not None
    assert client.server_info.name == SERVER_NAME
    assert client.server_info.version == __version__


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", _MODES)
async def test_in_process_client_modes(tmp_path: Path, mode: str) -> None:
    """Both modes work directly against the MCPServer instance."""
    server = build_server(str(tmp_path / f"inproc-{mode}.db"))
    async with Client(server, mode=mode) as client:  # type: ignore[arg-type]
        await _assert_client_matrix(client)


@asynccontextmanager
async def _asgi_transport(app: object, url: str) -> AsyncIterator[Any]:
    """Streamable-HTTP transport over an in-process ASGI app (no sockets)."""
    async with httpx2.AsyncClient(
        transport=httpx2.ASGITransport(app=app),
        base_url="http://localhost",
    ) as http_client:
        async with streamable_http_client(url, http_client=http_client) as streams:
            yield streams


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", _MODES)
async def test_asgi_http_client_modes(tmp_path: Path, mode: str) -> None:
    """Both modes work over the mounted Streamable HTTP app (ASGI transport)."""
    app = create_http_app(str(tmp_path / f"asgi-{mode}.db"))

    async with app.router.lifespan_context(app):
        transport = _asgi_transport(app, "http://localhost/mcp")
        async with Client(transport, mode=mode) as client:  # type: ignore[arg-type]
            await _assert_client_matrix(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", _MODES)
async def test_stdio_subprocess_client_modes(tmp_path: Path, mode: str) -> None:
    """Both modes work over a real ``python -m sif.cli.main mcp stdio`` child."""
    home = tmp_path / "home"
    home.mkdir()
    db_path = tmp_path / "mcp-sdk.db"
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "sif.cli.main", "--index", str(db_path), "mcp", "stdio"],
        env=_child_env(home),
        cwd=_REPO_ROOT,
    )

    async with Client(params, mode=mode) as client:  # type: ignore[arg-type]
        await _assert_client_matrix(client)

    assert db_path.exists(), "the subprocess must open the explicit --index database"
