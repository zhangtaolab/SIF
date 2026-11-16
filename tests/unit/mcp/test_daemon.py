"""Unit battery for the MCP daemon lifecycle (Phase 22 D-19..D-21).

The MCP daemon reuses the watch daemon's double-fork/arming machinery but
owns a distinct PID artifact (``<db>.mcp.pid``) and a distinct corroboration
marker (``mcp``), so a watch daemon and an MCP daemon can coexist on one index
and each ``--stop`` signals only its own process. The real-process proofs
(arm -> serve -> stop, bind failure, watch coexistence) are POSIX-only and
skip where ``os.fork`` is unavailable.
"""

from __future__ import annotations

import signal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from sif.utils import daemon


def _alive_kill(_pid: int, _sig: int) -> None:
    """os.kill fake for a process that answers the 0-probe."""


def _ps_run(stdout: str):
    """subprocess.run fake answering with the given ps command line."""

    def _run(_argv: list[str], **_kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(returncode=0, stdout=stdout)

    return _run


def _write_mcp_payload(path: Path, pid: int = 4242) -> None:
    daemon.write_pid_file(path, pid=pid, mode="mcp", depth="bm25")


class TestMcpPidArtifact:
    """D-20: the MCP daemon has its own path and its own payload."""

    def test_pid_path_for_mcp_is_distinct_and_ends_with_the_mcp_suffix(
        self, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "index.db"

        mcp = daemon.pid_path_for_mcp(db_path)
        watch = daemon.pid_path_for(db_path)
        resolved = db_path.resolve()

        assert mcp == resolved.with_name(resolved.name + ".mcp.pid")
        assert mcp.name == "index.db.mcp.pid"
        assert watch.name == "index.db.watch.pid"
        assert mcp != watch

    def test_mcp_payload_carries_mode_mcp_and_depth_bm25(self, tmp_path: Path) -> None:
        path = daemon.pid_path_for_mcp(tmp_path / "index.db")

        _write_mcp_payload(path)
        payload = daemon.read_pid_file(path)

        assert payload is not None
        assert payload["pid"] == 4242
        assert payload["mode"] == "mcp"
        assert payload["depth"] == "bm25"


class TestMcpCorroboration:
    """D-20/C5: the marker is fail-closed and distinct per lifecycle."""

    def test_mcp_marker_accepts_an_mcp_process_and_rejects_watch_only(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(daemon.os, "kill", _alive_kill)
        monkeypatch.setattr(daemon, "shutil", SimpleNamespace(which=lambda _name: "/bin/ps"))
        monkeypatch.setattr(
            daemon,
            "subprocess",
            SimpleNamespace(
                run=_ps_run(
                    "/venv/bin/python -u /venv/bin/sif --index /tmp/index.db mcp daemon --port 8080"
                )
            ),
        )
        payload = {"pid": 4242, "mode": "mcp", "depth": "bm25", "started": "x"}

        assert daemon.corroborate_pid(payload, marker="mcp") is True
        # The default marker still requires the watch token, so an MCP
        # daemon is never corroborated by a watch lifecycle (and vice versa).
        assert daemon.corroborate_pid(payload) is False

    def test_mcp_marker_rejects_a_watch_process(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(daemon.os, "kill", _alive_kill)
        monkeypatch.setattr(daemon, "shutil", SimpleNamespace(which=lambda _name: "/bin/ps"))
        monkeypatch.setattr(
            daemon,
            "subprocess",
            SimpleNamespace(
                run=_ps_run(
                    "/venv/bin/python -u -m sif.cli.main --index /tmp/index.db watch --detach"
                )
            ),
        )
        payload = {"pid": 4242, "mode": "mcp", "depth": "bm25", "started": "x"}

        assert daemon.corroborate_pid(payload, marker="mcp") is False


class TestMcpStop:
    """D-20/C5: ``mcp daemon --stop`` only signals a corroborated MCP daemon."""

    def test_stop_forwards_the_mcp_marker_to_corroboration(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        recorded: list[str] = []

        def fake_corroborate(_payload: dict[str, object], *, marker: str = "watch") -> bool:
            recorded.append(marker)
            return False

        monkeypatch.setattr(daemon, "corroborate_pid", fake_corroborate)
        pid_file = daemon.pid_path_for_mcp(tmp_path / "index.db")
        _write_mcp_payload(pid_file)

        outcome = daemon.stop_daemon(pid_file, marker="mcp")

        assert outcome.status == "stale"
        assert recorded == ["mcp"]

    def test_default_stop_still_forwards_the_watch_marker(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        recorded: list[str] = []

        def fake_corroborate(_payload: dict[str, object], *, marker: str = "watch") -> bool:
            recorded.append(marker)
            return False

        monkeypatch.setattr(daemon, "corroborate_pid", fake_corroborate)
        pid_file = tmp_path / "sif.db.watch.pid"
        daemon.write_pid_file(pid_file, pid=4242, mode="daemon", depth="bm25")

        outcome = daemon.stop_daemon(pid_file)

        assert outcome.status == "stale"
        assert recorded == ["watch"]

    def test_stop_mcp_marker_signals_a_live_mcp_process(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A live MCP daemon is 'stopped', never classified as stale."""
        pid_file = daemon.pid_path_for_mcp(tmp_path / "index.db")
        _write_mcp_payload(pid_file)
        state = {"terminated": False}

        def fake_kill(_pid: int, sig: int) -> None:
            if sig == 0:
                if state["terminated"]:
                    raise ProcessLookupError()
                return
            if sig == signal.SIGTERM:
                state["terminated"] = True

        monkeypatch.setattr(daemon.os, "kill", fake_kill)
        monkeypatch.setattr(daemon, "shutil", SimpleNamespace(which=lambda _name: "/bin/ps"))
        monkeypatch.setattr(
            daemon,
            "subprocess",
            SimpleNamespace(
                run=_ps_run(
                    "/venv/bin/python -u -m sif.cli.main --index /tmp/index.db "
                    "mcp daemon --port 8080"
                )
            ),
        )

        outcome = daemon.stop_daemon(
            pid_file,
            marker="mcp",
            term_timeout_s=0.5,
            kill_timeout_s=0.5,
            poll_interval_s=0.001,
        )

        assert outcome.status == "stopped"
        assert outcome.pid == 4242
        assert not pid_file.exists()
