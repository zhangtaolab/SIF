"""Tests for MCP stdio transport."""

from __future__ import annotations

import asyncio
import json
from io import StringIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sif.mcp.protocol import MCPErrorCode
from sif.mcp.transports import stdio
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
        return_value=MagicMock(model_dump=lambda **_: {"jsonrpc": "2.0", "id": 1, "result": {}}),
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
        return_value=MagicMock(model_dump=lambda **_: {"jsonrpc": "2.0", "id": 1, "result": {}}),
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


@pytest.mark.asyncio
async def test_process_message_invalid_notification_is_contained() -> None:
    """Malformed notifications are logged and ignored without a response."""
    transport = StdioTransport(MagicMock(), stdin=StringIO(), stdout=StringIO())

    result = await transport._process_message(
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": "invalid"}
    )

    assert result is None


@pytest.mark.asyncio
async def test_run_cancellation_resets_running_and_propagates() -> None:
    """Cancellation follows asyncio semantics while restoring transport state."""
    transport = StdioTransport(MagicMock(), stdin=StringIO(), stdout=StringIO())
    transport._read_message = AsyncMock(side_effect=asyncio.CancelledError)

    with pytest.raises(asyncio.CancelledError):
        await transport.run()

    assert transport._running is False


@pytest.mark.asyncio
async def test_run_read_failure_is_contained_and_resets_running() -> None:
    """Unexpected input failures are logged and do not leave the loop active."""
    transport = StdioTransport(MagicMock(), stdin=StringIO(), stdout=StringIO())
    transport._read_message = AsyncMock(side_effect=OSError("stdin unavailable"))

    await transport.run()

    assert transport._running is False


@pytest.mark.asyncio
async def test_run_stdio_server_composes_components_without_subprocess() -> None:
    """The async stdio entry point wires backend, tools, and in-memory transport."""
    server = MagicMock()
    transport = MagicMock()
    transport.run = AsyncMock()
    tools = [MagicMock()]

    with (
        patch.object(stdio, "SearchBackend", return_value="backend") as backend,
        patch.object(stdio, "MCPServer", return_value=server) as server_type,
        patch.object(stdio, "create_default_tools", return_value=tools),
        patch.object(stdio, "StdioTransport", return_value=transport) as transport_type,
    ):
        await stdio.run_stdio_server("/tmp/sif-test.db")

    backend.assert_called_once_with("/tmp/sif-test.db")
    server_type.assert_called_once_with("backend")
    server.register_tools.assert_called_once_with(tools)
    transport_type.assert_called_once_with(server)
    transport.run.assert_awaited_once_with()


def test_run_stdio_server_sync_uses_asyncio_run() -> None:
    """The synchronous entry point delegates to asyncio.run without a process."""
    with patch.object(stdio.asyncio, "run") as run:
        stdio.run_stdio_server_sync("/tmp/sif-test.db")

    run.assert_called_once()
    assert run.call_args.args[0].cr_code is stdio.run_stdio_server.__code__
    run.call_args.args[0].close()
