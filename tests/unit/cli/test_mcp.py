"""Tests for the MCP CLI defaults wired from Settings."""

from __future__ import annotations

from types import SimpleNamespace

import click
from click.testing import CliRunner

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


def test_http_allowed_hosts_are_repeatable_and_forwarded(monkeypatch, tmp_path) -> None:
    """D-13: every ``--allowed-hosts`` value reaches ``run_http_server``."""
    captured: dict[str, object] = {}

    def fake_run_http_server(db_path: str, **kwargs: object) -> None:
        captured["db_path"] = db_path
        captured.update(kwargs)

    monkeypatch.setattr("sif.mcp.cli.run_http_server", fake_run_http_server)

    result = CliRunner().invoke(
        mcp_mod.mcp_http_cmd,
        [
            "--host",
            "127.0.0.1",
            "--port",
            "8123",
            "--allowed-hosts",
            "sif.local",
            "--allowed-hosts",
            "sif.example",
            "--cors-origins",
            "https://sif.local",
        ],
        obj={"index_path": tmp_path / "index.db"},
    )

    assert result.exit_code == 0, result.output
    assert captured["allowed_hosts"] == ["sif.local", "sif.example"]
    assert captured["cors_origins"] == ["https://sif.local"]


def test_http_without_allowed_hosts_forwards_none(monkeypatch, tmp_path) -> None:
    """No flag keeps the loopback defaults (None, never an empty wildcard)."""
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        "sif.mcp.cli.run_http_server",
        lambda _db_path, **kwargs: captured.update(kwargs),
    )

    result = CliRunner().invoke(
        mcp_mod.mcp_http_cmd,
        ["--host", "127.0.0.1", "--port", "8123"],
        obj={"index_path": tmp_path / "index.db"},
    )

    assert result.exit_code == 0, result.output
    assert captured["allowed_hosts"] is None


def test_daemon_help_lists_lifecycle_and_security_flags() -> None:
    """The daemon surface exposes its real options from the start (D-13/D-19)."""
    result = CliRunner().invoke(mcp_mod.mcp_daemon_cmd, ["--help"])

    assert result.exit_code == 0
    assert "--allowed-hosts" in result.output
    assert "--cors-origins" in result.output
    assert "--pid-file" in result.output
    assert "--log-file" in result.output
    assert "--stop" in result.output
    assert "not implemented" not in result.output


def test_daemon_stop_targets_the_mcp_pid_artifact_with_the_mcp_marker(
    monkeypatch, tmp_path
) -> None:
    """D-20: --stop resolves <db>.mcp.pid and corroborates with the mcp marker."""
    captured: dict[str, object] = {}

    def fake_stop(pid_path, *, marker: str) -> object:
        captured["pid_path"] = pid_path
        captured["marker"] = marker
        return mcp_mod.daemon.StopOutcome("stopped", pid=4242)

    monkeypatch.setattr(mcp_mod.daemon, "stop_daemon", fake_stop)

    result = CliRunner().invoke(
        mcp_mod.mcp_daemon_cmd, ["--stop"], obj={"index_path": tmp_path / "index.db"}
    )

    assert result.exit_code == 0, result.output
    assert captured["marker"] == "mcp"
    assert captured["pid_path"] == mcp_mod.daemon.pid_path_for_mcp(tmp_path / "index.db")
    assert "MCP daemon stopped (PID 4242)" in result.output


def test_daemon_stop_honors_an_explicit_pid_file(monkeypatch, tmp_path) -> None:
    """D-20: --pid-file overrides the default <db>.mcp.pid path."""
    captured: dict[str, object] = {}

    def fake_stop(pid_path, *, marker: str) -> object:
        captured["pid_path"] = pid_path
        captured["marker"] = marker
        return mcp_mod.daemon.StopOutcome("not_running")

    monkeypatch.setattr(mcp_mod.daemon, "stop_daemon", fake_stop)
    explicit = tmp_path / "custom" / "mcp.pid"

    result = CliRunner().invoke(
        mcp_mod.mcp_daemon_cmd,
        ["--stop", "--pid-file", str(explicit)],
        obj={"index_path": tmp_path / "index.db"},
    )

    assert result.exit_code == 0, result.output
    assert captured["pid_path"] == explicit
    assert captured["marker"] == "mcp"
    assert "MCP daemon is not running." in result.output


def test_daemon_stop_reports_permission_denied(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        mcp_mod.daemon,
        "stop_daemon",
        lambda *_args, **_kwargs: mcp_mod.daemon.StopOutcome("permission_denied", pid=4242),
    )

    result = CliRunner().invoke(
        mcp_mod.mcp_daemon_cmd, ["--stop"], obj={"index_path": tmp_path / "index.db"}
    )

    assert "another user" in result.output
    assert "4242" in result.output


def test_daemon_stop_reports_stale_cleanup(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        mcp_mod.daemon,
        "stop_daemon",
        lambda *_args, **_kwargs: mcp_mod.daemon.StopOutcome("stale", pid=7),
    )

    result = CliRunner().invoke(
        mcp_mod.mcp_daemon_cmd, ["--stop"], obj={"index_path": tmp_path / "index.db"}
    )

    assert "MCP daemon is not running" in result.output
    assert "stale PID file removed" in result.output


def test_daemon_start_on_windows_refuses_with_cause_and_remedy(monkeypatch, tmp_path) -> None:
    """D-19: Windows refuses before log/PID work with the foreground remedy."""
    monkeypatch.setattr(mcp_mod, "os", SimpleNamespace())

    result = CliRunner().invoke(
        mcp_mod.mcp_daemon_cmd, [], obj={"index_path": tmp_path / "index.db"}
    )

    assert result.exit_code != 0
    assert "POSIX fork" in result.output
    assert "not available on Windows" in result.output
    assert "sif mcp http" in result.output
    assert "foreground" in result.output
    assert "Traceback" not in result.output
