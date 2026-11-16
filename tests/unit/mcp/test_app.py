"""Composition-root tests for the SDK v2 MCP server (Phase 22 D-01/D-09/D-13).

One server/app per test: ``streamable_http_app()`` may be called only once per
``MCPServer`` and the session manager may be entered only once (22-RESEARCH.md
Pattern 1/Pitfall 3). Every request that expects 200 sends a Host the loopback
allowlist accepts (``base_url="http://localhost"``); ``testserver`` is never
added to the production allowlist.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from mcp import Client
from mcp.shared.exceptions import MCPError

from sif._version import __version__
from sif.core.models import Collection, Document
from sif.database.database import Database
from sif.database.repositories import CollectionRepository, DocumentRepository
from sif.mcp.app import (
    DEFAULT_ALLOWED_HOSTS,
    DEFAULT_CORS_ORIGINS,
    SERVER_NAME,
    _resolve_transport_security,
    build_server,
    build_transport_security,
    create_http_app,
)


_DOC_BODY = "# Title\n\nline one\nline two\nline three\nline four\nline five\n"

_INITIALIZE_PARAMS = {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {"name": "sif-app-test", "version": "1"},
}


def _seed_document(db_path: Path, *, doc_id: str = "doc-1") -> None:
    """Create one real collection and one multi-line document."""
    db = Database(db_path)
    try:
        db.init_schema()
        with db.connection:
            collection = Collection(name="notes", path=str(db_path.parent / "notes"))
            CollectionRepository(db.connection).create(collection)
            DocumentRepository(db.connection).create(
                Document(
                    path=str(db_path.parent / "notes" / "note.md"),
                    collection_id=collection.id,
                    content=_DOC_BODY,
                    id=doc_id,
                )
            )
    finally:
        db.close()


def _initialize(client: TestClient) -> str:
    """Run the 2024-11-05 handshake and return the minted session id."""
    response = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": dict(_INITIALIZE_PARAMS),
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["result"]["protocolVersion"] == "2024-11-05"
    return response.headers["mcp-session-id"]


def test_build_server_exposes_the_wire_identity_without_opening_the_index(
    tmp_path: Path,
) -> None:
    """Name/version are assertable through the seam; the backend waits for lifespan."""
    with patch("sif.mcp.app.SearchBackend") as backend_cls:
        server = build_server(str(tmp_path / "identity.db"))

    assert server.name == SERVER_NAME == "sif-mcp-server"
    assert server.version == __version__
    backend_cls.assert_not_called()


def test_build_transport_security_is_explicit_and_loopback_only() -> None:
    """D-13: always an explicit object with loopback hosts and no wildcard."""
    security = build_transport_security()

    assert security.enable_dns_rebinding_protection is True
    assert security.allowed_hosts == DEFAULT_ALLOWED_HOSTS
    assert security.allowed_origins == DEFAULT_CORS_ORIGINS
    assert "*" not in security.allowed_hosts
    assert "*" not in security.allowed_origins


def test_build_transport_security_unions_explicit_hosts_with_loopback_defaults() -> None:
    """D-13: explicit hosts EXTEND the loopback defaults, never replace them."""
    security = build_transport_security(
        allowed_hosts=["sif.local"],
        allowed_origins=["https://sif.local"],
    )

    assert security.allowed_hosts == [*DEFAULT_ALLOWED_HOSTS, "sif.local"]
    assert security.allowed_origins == ["https://sif.local"]
    assert build_transport_security(allowed_origins=[]).allowed_origins == []


def test_build_transport_security_never_honors_a_wildcard_host() -> None:
    """A literal ``*`` is dropped, not widened into an open allowlist."""
    security = build_transport_security(allowed_hosts=["*", "sif.local"])

    assert security.allowed_hosts == [*DEFAULT_ALLOWED_HOSTS, "sif.local"]
    assert "*" not in security.allowed_hosts


class TestPartialTransportSecurityOverrides:
    """WR-05: a one-dimensional override must not drop the other dimension."""

    def test_host_override_keeps_the_recorded_origins(self, tmp_path: Path) -> None:
        """Overriding allowed_hosts keeps the caller-supplied origins."""
        server = build_server(
            str(tmp_path / "policy.db"),
            allowed_hosts=["sif.local"],
            cors_origins=["https://sif.local"],
        )

        security = _resolve_transport_security(server, ["other.local"], None)

        assert security.allowed_hosts == [*DEFAULT_ALLOWED_HOSTS, "other.local"]
        assert security.allowed_origins == ["https://sif.local"]

    def test_origin_override_keeps_the_recorded_host_allowlist(self, tmp_path: Path) -> None:
        """Overriding origins keeps the operator's host allowlist."""
        server = build_server(
            str(tmp_path / "policy.db"),
            allowed_hosts=["sif.local"],
            cors_origins=["https://sif.local"],
        )

        security = _resolve_transport_security(server, None, ["https://other.local"])

        assert security.allowed_hosts == [*DEFAULT_ALLOWED_HOSTS, "sif.local"]
        assert security.allowed_origins == ["https://other.local"]

    def test_host_override_keeps_a_fail_closed_origin_list(self, tmp_path: Path) -> None:
        """A fail-closed ``cors_origins=[]`` is not widened to the defaults."""
        server = build_server(str(tmp_path / "policy.db"), cors_origins=[])

        security = _resolve_transport_security(server, ["sif.local"], None)

        assert security.allowed_hosts == [*DEFAULT_ALLOWED_HOSTS, "sif.local"]
        assert security.allowed_origins == []


def test_http_health_and_mcp_mount_serve_without_a_redirect(tmp_path: Path) -> None:
    """`/health` is a parent route; `/mcp` serves in place (no 307)."""
    app = create_http_app(str(tmp_path / "app.db"))

    with TestClient(app, base_url="http://localhost") as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}

        session_id = _initialize(client)
        tools = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            headers={"mcp-session-id": session_id},
        )
        assert tools.status_code == 200
        assert [tool["name"] for tool in tools.json()["result"]["tools"]] == [
            "query",
            "get",
            "multi_get",
            "status",
            "metadata",
            "lex_search",
            "vec_search",
        ]

        called = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "status", "arguments": {}},
            },
            headers={"mcp-session-id": session_id},
        )
        assert called.status_code == 200
        result = called.json()["result"]
        assert result["isError"] is False
        assert json.loads(result["content"][0]["text"]) == result["structuredContent"]


def test_lifespan_enters_and_exits_the_session_manager_exactly_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-18: the parent lifespan owns exactly one session-manager enter/exit."""
    server = build_server(str(tmp_path / "lifespan.db"))
    app = create_http_app(str(tmp_path / "lifespan.db"), server=server)
    manager = server.session_manager
    real_run = manager.run
    enters: list[int] = []
    exits: list[int] = []

    @asynccontextmanager
    async def counting_run() -> Any:
        enters.append(1)
        async with real_run():
            yield
        exits.append(1)

    monkeypatch.setattr(manager, "run", counting_run)

    with TestClient(app, base_url="http://localhost") as client:
        assert enters == [1]
        assert client.get("/health").status_code == 200

    assert exits == [1]


@pytest.mark.asyncio
async def test_docs_resource_serves_full_and_ranged_documents(tmp_path: Path) -> None:
    """D-09: full Markdown by default, an inclusive line window on request."""
    db_path = tmp_path / "resource.db"
    _seed_document(db_path)
    server = build_server(str(db_path))

    async with Client(server, mode="legacy") as client:
        full = await client.read_resource("docs://doc-1")
        assert full.contents[0].text == _DOC_BODY
        assert full.contents[0].mime_type == "text/markdown"

        ranged = await client.read_resource("docs://doc-1?from_line=2&max_lines=3")
        # Lines 2-4 of the document, inclusive.
        assert ranged.contents[0].text == "\nline one\nline two"

        with pytest.raises(MCPError, match="Document not found"):
            await client.read_resource("docs://missing")


@pytest.mark.asyncio
async def test_status_dual_channel_parity_through_the_sdk_client(tmp_path: Path) -> None:
    """D-05/D-10: text parses to exactly the structured mapping."""
    db_path = tmp_path / "parity.db"
    _seed_document(db_path)
    server = build_server(str(db_path))

    async with Client(server, mode="legacy") as client:
        result = await client.call_tool("status", {})

    assert result.is_error is False
    assert result.structured_content == {
        "collections": [
            {
                "name": "notes",
                "document_count": 1,
                "last_updated": None,
                "size_bytes": None,
            }
        ],
        "total_documents": 1,
    }
    assert json.loads(result.content[0].text) == result.structured_content


def test_status_output_schema_is_published_from_the_output_model(tmp_path: Path) -> None:
    """The preserved Pydantic model drives ``outputSchema`` (D-10)."""
    app = create_http_app(str(tmp_path / "schema.db"))

    with TestClient(app, base_url="http://localhost") as client:
        session_id = _initialize(client)
        tools = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            headers={"mcp-session-id": session_id},
        )
        tools = tools.json()["result"]["tools"]
        status_tool = next(tool for tool in tools if tool["name"] == "status")

    assert status_tool["name"] == "status"
    assert status_tool["outputSchema"]["type"] == "object"
    assert set(status_tool["outputSchema"]["properties"]) >= {
        "collections",
        "total_documents",
    }
    assert status_tool["annotations"] == {"openWorldHint": False, "readOnlyHint": True}
