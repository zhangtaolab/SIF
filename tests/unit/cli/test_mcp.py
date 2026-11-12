"""Tests for the MCP CLI defaults wired from Settings."""

from __future__ import annotations

from types import SimpleNamespace

import click

from sif.cli.commands import mcp as mcp_mod
from sif.config.settings import Settings


def test_mcp_host_and_port_defaults_read_settings(monkeypatch) -> None:
    """SIF_MCP_HOST / SIF_MCP_PORT become the HTTP command defaults."""
    monkeypatch.setattr(
        mcp_mod,
        "get_settings",
        lambda: SimpleNamespace(mcp_host="0.0.0.0", mcp_port=9999),
    )

    assert mcp_mod._default_mcp_host() == "0.0.0.0"
    assert mcp_mod._default_mcp_port() == 9999


def test_mcp_host_and_port_fall_back_on_invalid_settings(monkeypatch) -> None:
    """Invalid settings keep the historical loopback/8080 defaults."""
    monkeypatch.setattr(
        mcp_mod,
        "get_settings",
        lambda: Settings(_env_file=None, mcp_port=0),
    )

    assert mcp_mod._default_mcp_host() == "127.0.0.1"
    assert mcp_mod._default_mcp_port() == 8080


def test_mcp_group_dispatches_configured_http_transport(monkeypatch) -> None:
    """SIF_MCP_TRANSPORT=http makes bare `sif mcp` start the HTTP server."""
    monkeypatch.setattr(mcp_mod, "get_settings", lambda: SimpleNamespace(mcp_transport="http"))
    ctx = click.Context(mcp_mod.mcp_group)
    invoked: list[object] = []
    monkeypatch.setattr(ctx, "invoke", invoked.append)

    with ctx:
        mcp_mod.mcp_group.callback()  # type: ignore[misc]

    assert invoked == [mcp_mod.mcp_http_cmd]


def test_mcp_group_dispatches_configured_stdio_transport(monkeypatch) -> None:
    """SIF_MCP_TRANSPORT=stdio (the default) makes bare `sif mcp` start stdio."""
    monkeypatch.setattr(mcp_mod, "get_settings", lambda: SimpleNamespace(mcp_transport="stdio"))
    ctx = click.Context(mcp_mod.mcp_group)
    invoked: list[object] = []
    monkeypatch.setattr(ctx, "invoke", invoked.append)

    with ctx:
        mcp_mod.mcp_group.callback()  # type: ignore[misc]

    assert invoked == [mcp_mod.mcp_stdio_cmd]


def test_mcp_group_leaves_explicit_subcommands_alone(monkeypatch) -> None:
    """A real subcommand is not shadowed by the configured default transport."""
    monkeypatch.setattr(mcp_mod, "get_settings", lambda: SimpleNamespace(mcp_transport="http"))
    ctx = click.Context(mcp_mod.mcp_group)
    ctx.invoked_subcommand = "stdio"
    invoked: list[object] = []
    monkeypatch.setattr(ctx, "invoke", invoked.append)

    with ctx:
        mcp_mod.mcp_group.callback()  # type: ignore[misc]

    assert invoked == []
