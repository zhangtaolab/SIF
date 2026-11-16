"""Golden wire transcripts for every supported MCP protocol revision (D-04).

The five checked-in goldens are normalized raw JSON-RPC transcripts:

- ``2024-11-05``, ``2025-03-26``, ``2025-06-18``, ``2025-11-25``:
  ``initialize -> tools/list -> tools/call status`` with a session header.
- ``2026-07-28``: no ``initialize`` and no session; each request carries
  ``MCP-Protocol-Version`` + ``Mcp-Method`` (+ ``Mcp-Name`` for tool calls)
  and ``params._meta``.

Only ``serverInfo.version`` and ``mcp-session-id`` are normalized. Everything
else is locked, including the C9 reality that ``outputSchema`` and
``structuredContent`` appear even on 2024-era responses.

Re-runnable writer: set ``SIF_UPDATE_WIRE_GOLDENS=1`` to rewrite all five
checked-in transcripts from live responses. Serialization is sorted-keys with
a trailing newline, so regeneration diffs only the changed payload. 22-02,
22-04, and 22-05 regenerate these files with the same command when their
surfaces change.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from sif.mcp.app import create_http_app


GOLDENS = Path(__file__).resolve().parent / "goldens"

LEGACY_ERAS = ("2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25")
MODERN_ERA = "2026-07-28"
ERAS = (*LEGACY_ERAS, MODERN_ERA)

_CLIENT_INFO = {"name": "sif-golden", "version": "1"}
_MODERN_META = {
    "io.modelcontextprotocol/protocolVersion": MODERN_ERA,
    "io.modelcontextprotocol/clientCapabilities": {},
    "io.modelcontextprotocol/clientInfo": _CLIENT_INFO,
}

_UPDATE_ENV = "SIF_UPDATE_WIRE_GOLDENS"


def _normalize(value: Any, parent_key: str | None = None) -> Any:
    """Replace only ``serverInfo.version`` values with a stable placeholder."""
    if isinstance(value, dict):
        return {
            key: (
                "<version>"
                if key == "version" and parent_key is not None and parent_key.endswith("serverInfo")
                else _normalize(item, key)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_normalize(item, parent_key) for item in value]
    return value


def _exchange(
    client: TestClient,
    body: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> tuple[dict[str, Any], str | None]:
    """POST one JSON-RPC request and return its normalized transcript record."""
    sent_headers = dict(headers or {})
    recorded_headers = {
        key: ("<session>" if key.lower() == "mcp-session-id" else value)
        for key, value in sent_headers.items()
    }
    response = client.post("/mcp", json=body, headers=sent_headers)
    recorded_response_headers: dict[str, str] = {}
    if "mcp-session-id" in response.headers:
        recorded_response_headers["mcp-session-id"] = "<session>"
    try:
        payload: Any = response.json()
    except ValueError:  # pragma: no cover - every recorded response is JSON
        payload = response.text
    record = {
        "request": {"headers": recorded_headers, "body": body},
        "response": {
            "status": response.status_code,
            "headers": recorded_response_headers,
            "body": _normalize(payload),
        },
    }
    return record, response.headers.get("mcp-session-id")


def _initialize_body(era: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": era,
            "capabilities": {},
            "clientInfo": _CLIENT_INFO,
        },
    }


def _legacy_transcript(client: TestClient, era: str) -> dict[str, Any]:
    exchanges: list[dict[str, Any]] = []
    record, session_id = _exchange(client, _initialize_body(era))
    exchanges.append(record)
    assert session_id, "a handshake-era initialize must mint a session id"

    headers = {"mcp-session-id": session_id}
    tools_record, _ = _exchange(
        client,
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        headers,
    )
    exchanges.append(tools_record)
    status_record, _ = _exchange(
        client,
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "status", "arguments": {}},
        },
        headers,
    )
    exchanges.append(status_record)
    return {"protocolVersion": era, "exchanges": exchanges}


def _modern_transcript(client: TestClient) -> dict[str, Any]:
    list_headers = {
        "MCP-Protocol-Version": MODERN_ERA,
        "Mcp-Method": "tools/list",
    }
    call_headers = {
        "MCP-Protocol-Version": MODERN_ERA,
        "Mcp-Method": "tools/call",
        "Mcp-Name": "status",
    }
    tools_record, _ = _exchange(
        client,
        {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/list",
            "params": {"_meta": _MODERN_META},
        },
        list_headers,
    )
    status_record, _ = _exchange(
        client,
        {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {"name": "status", "arguments": {}, "_meta": _MODERN_META},
        },
        call_headers,
    )
    return {
        "protocolVersion": MODERN_ERA,
        "exchanges": [tools_record, status_record],
    }


def _build_transcript(tmp_path: Path, era: str) -> dict[str, Any]:
    app = create_http_app(str(tmp_path / f"wire-{era}.db"))
    with TestClient(app, base_url="http://localhost") as client:
        if era == MODERN_ERA:
            return _modern_transcript(client)
        return _legacy_transcript(client, era)


def _dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _load(era: str) -> dict[str, Any]:
    return json.loads((GOLDENS / f"{era}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("era", ERAS)
def test_wire_transcript_matches_golden(tmp_path: Path, era: str) -> None:
    """Each supported revision is locked byte-for-byte after normalization."""
    transcript = _build_transcript(tmp_path, era)
    path = GOLDENS / f"{era}.json"

    if os.environ.get(_UPDATE_ENV) == "1":
        GOLDENS.mkdir(parents=True, exist_ok=True)
        path.write_text(_dump(transcript), encoding="utf-8")

    assert transcript == _load(era)


def test_2024_golden_records_output_schema_and_structured_content() -> None:
    """C9: structured output appears on 2024-era responses and is not normalized away."""
    golden = _load("2024-11-05")

    tools = golden["exchanges"][1]["response"]["body"]["result"]["tools"]
    assert tools[0]["name"] == "status"
    assert tools[0]["outputSchema"]["type"] == "object"

    result = golden["exchanges"][2]["response"]["body"]["result"]
    assert result["isError"] is False
    assert "structuredContent" in result
    assert json.loads(result["content"][0]["text"]) == result["structuredContent"]


def test_handshake_era_negotiates_the_requested_revision() -> None:
    """Each initialized transcript echoes its requested protocol version."""
    for era in LEGACY_ERAS:
        golden = _load(era)
        result = golden["exchanges"][0]["response"]["body"]["result"]
        assert result["protocolVersion"] == era
        assert golden["exchanges"][0]["response"]["headers"]["mcp-session-id"] == "<session>"


def test_modern_era_is_stateless_without_initialize_or_session() -> None:
    """The 2026 transcript has no initialize and no session id anywhere."""
    golden = _load(MODERN_ERA)

    assert [entry["request"]["body"]["method"] for entry in golden["exchanges"]] == [
        "tools/list",
        "tools/call",
    ]
    for entry in golden["exchanges"]:
        assert "mcp-session-id" not in entry["response"]["headers"]
        assert entry["request"]["headers"]["MCP-Protocol-Version"] == MODERN_ERA
        assert (
            entry["request"]["body"]["params"]["_meta"]["io.modelcontextprotocol/protocolVersion"]
            == MODERN_ERA
        )


def test_modern_request_without_mcp_name_is_rejected(tmp_path: Path) -> None:
    """T-22-03: a tool call at 2026-07-28 must name the tool in the header."""
    app = create_http_app(str(tmp_path / "no-name.db"))
    with TestClient(app, base_url="http://localhost") as client:
        response = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 20,
                "method": "tools/call",
                "params": {"name": "status", "arguments": {}, "_meta": _MODERN_META},
            },
            headers={"MCP-Protocol-Version": MODERN_ERA, "Mcp-Method": "tools/call"},
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == -32020


def test_modern_request_without_meta_is_rejected(tmp_path: Path) -> None:
    """T-22-03: the 2026 per-request envelope requires ``params._meta``."""
    app = create_http_app(str(tmp_path / "no-meta.db"))
    with TestClient(app, base_url="http://localhost") as client:
        response = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 21,
                "method": "tools/call",
                "params": {"name": "status", "arguments": {}},
            },
            headers={
                "MCP-Protocol-Version": MODERN_ERA,
                "Mcp-Method": "tools/call",
                "Mcp-Name": "status",
            },
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == -32602
    assert "params._meta" in response.json()["error"]["message"]
