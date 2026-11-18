"""Transport-security proof against the mounted SDK app (Phase 22 D-13/D-14).

This is the C1/C2 baseline that must be green BEFORE the hand-rolled shell is
deleted in 22-02. The SDK's own status codes are authoritative: bad ``Host``
-> 421 Misdirected Request, bad ``Origin`` -> 403, non-JSON ``Content-Type``
-> 400 (22-RESEARCH.md C1/Pitfall 6).

Every assertion that expects 200 sends a Host the loopback allowlist accepts
(``base_url="http://localhost"``); ``testserver`` is never added to the
production allowlist.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from sif.mcp.app import build_transport_security, create_http_app


_INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "sif-security-test", "version": "1"},
    },
}


@pytest.fixture
def mounted_app(tmp_path: Path):
    """One fresh mounted app per test (one streamable app per server)."""
    return create_http_app(str(tmp_path / "security.db"))


@pytest.fixture
def client(mounted_app):
    """TestClient on an allowed loopback Host."""
    with TestClient(mounted_app, base_url="http://localhost") as test_client:
        yield test_client


def test_allowed_loopback_host_is_accepted(client: TestClient) -> None:
    """A bare ``localhost`` Host passes DNS-rebinding validation."""
    response = client.post("/mcp", json=_INITIALIZE)

    assert response.status_code == 200
    assert "mcp-session-id" in response.headers


def test_allowed_loopback_host_with_explicit_port_is_accepted(client: TestClient) -> None:
    """The ``localhost:*`` form matches an explicit port too."""
    response = client.post("/mcp", json=_INITIALIZE, headers={"host": "localhost:8080"})

    assert response.status_code == 200


def test_spoofed_host_is_rejected_with_421(client: TestClient) -> None:
    """D-14/C1: the SDK returns 421 Misdirected Request, not 403."""
    response = client.post("/mcp", json=_INITIALIZE, headers={"host": "evil.example"})

    assert response.status_code == 421
    assert response.text == "Invalid Host header"


def test_spoofed_origin_is_rejected_with_403(client: TestClient) -> None:
    """D-14: a non-allowlisted Origin is forbidden."""
    response = client.post(
        "/mcp",
        json=_INITIALIZE,
        headers={"origin": "http://evil.example"},
    )

    assert response.status_code == 403
    assert response.text == "Invalid Origin header"


def test_allowed_origin_is_accepted_with_cors_headers(client: TestClient) -> None:
    """The existing CORS origins stay the origin allowlist."""
    response = client.post(
        "/mcp",
        json=_INITIALIZE,
        headers={"origin": "http://localhost:3000"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_absent_origin_is_allowed(client: TestClient) -> None:
    """D-14: no Origin header (non-browser clients) is not a rejection."""
    response = client.post("/mcp", json=_INITIALIZE)

    assert response.status_code == 200


def test_non_json_content_type_is_rejected_with_400(client: TestClient) -> None:
    """D-14/C1: the SDK validates the POST content type before handling."""
    response = client.post(
        "/mcp",
        content="not json",
        headers={"content-type": "text/plain"},
    )

    assert response.status_code == 400
    assert response.text == "Invalid Content-Type header"


def test_explicitly_allowed_host_is_accepted(tmp_path: Path) -> None:
    """D-13: ``allowed_hosts`` extends the SDK allowlist for a named bind."""
    app = create_http_app(str(tmp_path / "explicit.db"), allowed_hosts=["sif.local"])

    with TestClient(app, base_url="http://sif.local") as client:
        response = client.post("/mcp", json=_INITIALIZE)

    assert response.status_code == 200


def test_health_rejects_a_spoofed_host_with_421(client: TestClient) -> None:
    """C2: ``/health`` is outside the SDK mount, so it carries its own guard."""
    response = client.get("/health", headers={"host": "evil.example"})

    assert response.status_code == 421


def test_health_allows_an_allowed_loopback_host(client: TestClient) -> None:
    """The guard shares the allowlist: loopback Hosts still get 200."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_non_loopback_bind_warns_and_keeps_loopback_only_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """D-13: a non-loopback bind never widens silently — warn, keep defaults."""
    from sif.mcp import app as app_module

    captured: dict[str, Any] = {}

    def fake_create_http_app(*_args: Any, **kwargs: Any) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(app_module, "create_http_app", fake_create_http_app)
    monkeypatch.setattr(app_module, "run_http_app", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(app_module, "set_quiet", lambda _quiet: None)

    with caplog.at_level(logging.WARNING, logger="sif.mcp.app"):
        app_module.run_http(str(tmp_path / "warn.db"), host="0.0.0.0", port=9000)

    assert captured["allowed_hosts"] is None
    messages = [record.getMessage() for record in caplog.records]
    assert any("not loopback" in message and "--allowed-hosts" in message for message in messages)
    assert "*" not in build_transport_security().allowed_hosts
