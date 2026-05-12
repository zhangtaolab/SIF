"""Tests for MCP stdio transport."""

from __future__ import annotations

import json
from io import StringIO
from unittest.mock import AsyncMock, MagicMock

import pytest

from sif.mcp.protocol import MCPErrorCode
from sif.mcp.transports.stdio import StdioTransport


@pytest.mark.asyncio
async def test_read_message_valid_json() -> None:
    """Test reading valid JSON-RPC message."""
    server = MagicMock()
    stdin = StringIO('{"jsonrpc":"2.0","id":1,"method":"initialize"}\n')
    stdout = StringIO()
    transport = StdioTransport(server, stdin=stdin, stdout=stdout)

    result = await transport._read_message()

    assert result == {"jsonrpc": "2.0", "id": 1, "method": "initialize"}


@pytest.mark.asyncio
async def test_read_message_eof() -> None:
    """Test EOF returns None."""
    server = MagicMock()
    stdin = StringIO("")
    stdout = StringIO()
    transport = StdioTransport(server, stdin=stdin, stdout=stdout)

    result = await transport._read_message()

    assert result is None


@pytest.mark.asyncio
async def test_read_message_invalid_json() -> None:
    """Test invalid JSON returns ParseError."""
    server = MagicMock()
    stdin = StringIO("not json\n")
    stdout = StringIO()
    transport = StdioTransport(server, stdin=stdin, stdout=stdout)

    result = await transport._read_message()

    assert result is not None
    assert result["error"]["code"] == MCPErrorCode.PARSE_ERROR


@pytest.mark.asyncio
async def test_read_message_blank_line() -> None:
    """Test blank lines are skipped."""
    server = MagicMock()
    stdin = StringIO('\n\n{"jsonrpc":"2.0","id":1}\n')
    stdout = StringIO()
    transport = StdioTransport(server, stdin=stdin, stdout=stdout)

    result = await transport._read_message()
    assert result is None

    result = await transport._read_message()
    assert result is None

    result = await transport._read_message()
    assert result == {"jsonrpc": "2.0", "id": 1}


@pytest.mark.asyncio
async def test_write_message() -> None:
    """Test writing JSON-RPC message."""
    server = MagicMock()
    stdin = StringIO("")
    stdout = StringIO()
    transport = StdioTransport(server, stdin=stdin, stdout=stdout)

    await transport._write_message({"jsonrpc": "2.0", "id": 1, "result": {}})

    stdout.seek(0)
    assert stdout.read() == '{"jsonrpc": "2.0", "id": 1, "result": {}}\n'


@pytest.mark.asyncio
async def test_process_message_request() -> None:
    """Test processing a request message."""
    server = MagicMock()
    server.handle_request = AsyncMock(
        return_value=MagicMock(model_dump=lambda **_: {"jsonrpc": "2.0", "id": 1, "result": {}})
    )
    stdin = StringIO("")
    stdout = StringIO()
    transport = StdioTransport(server, stdin=stdin, stdout=stdout)

    result = await transport._process_message({"jsonrpc": "2.0", "id": 1, "method": "initialize"})

    assert result == {"jsonrpc": "2.0", "id": 1, "result": {}}
    server.handle_request.assert_called_once()


@pytest.mark.asyncio
async def test_process_message_notification() -> None:
    """Test processing a notification message."""
    server = MagicMock()
    server.handle_notification = AsyncMock()
    stdin = StringIO("")
    stdout = StringIO()
    transport = StdioTransport(server, stdin=stdin, stdout=stdout)

    msg = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    result = await transport._process_message(msg)

    assert result is None
    server.handle_notification.assert_called_once()


@pytest.mark.asyncio
async def test_run_loop_eof() -> None:
    """Test run loop exits cleanly on EOF."""
    server = MagicMock()
    stdin = StringIO("")
    stdout = StringIO()
    transport = StdioTransport(server, stdin=stdin, stdout=stdout)

    await transport.run()

    assert not transport._running


@pytest.mark.asyncio
async def test_run_loop_processes_request() -> None:
    """Test run loop processes a request and exits on EOF."""
    server = MagicMock()
    server.handle_request = AsyncMock(
        return_value=MagicMock(model_dump=lambda **_: {"jsonrpc": "2.0", "id": 1, "result": {}})
    )
    stdin = StringIO('{"jsonrpc":"2.0","id":1,"method":"initialize"}\n')
    stdout = StringIO()
    transport = StdioTransport(server, stdin=stdin, stdout=stdout)

    await transport.run()

    stdout.seek(0)
    output = stdout.read()
    assert "jsonrpc" in output
    server.handle_request.assert_called_once()


@pytest.mark.asyncio
async def test_run_loop_handles_exception() -> None:
    """Test run loop handles exceptions gracefully."""
    server = MagicMock()
    server.handle_request = AsyncMock(side_effect=Exception("boom"))
    stdin = StringIO('{"jsonrpc":"2.0","id":1,"method":"foo"}\n')
    stdout = StringIO()
    transport = StdioTransport(server, stdin=stdin, stdout=stdout)

    await transport.run()

    stdout.seek(0)
    output = stdout.read()
    data = json.loads(output.strip())
    assert data["error"]["code"] == MCPErrorCode.INTERNAL_ERROR
