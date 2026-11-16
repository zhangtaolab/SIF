"""Unit battery for the MCP daemon lifecycle (Phase 22 D-19..D-21).

The MCP daemon reuses the watch daemon's double-fork/arming machinery but
owns a distinct PID artifact (``<db>.mcp.pid``) and a distinct corroboration
marker (``mcp``), so a watch daemon and an MCP daemon can coexist on one index
and each ``--stop`` signals only its own process. The real-process proofs
(arm -> serve -> stop, bind failure, watch coexistence) are POSIX-only and
skip where ``os.fork`` is unavailable.
"""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any, TypeVar

import pytest
from click.testing import CliRunner

from sif.cli.commands import mcp as mcp_mod
from sif.config.settings import Settings
from sif.core.models import Collection
from sif.database.database import Database
from sif.database.repositories import CollectionRepository
from sif.mcp import cli as mcp_cli
from sif.utils import daemon


_STARTUP_DEADLINE_S = 30.0
_STOP_DEADLINE_S = 20.0
_POLL_INTERVAL_S = 0.1
_PROXY_FREE_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

T = TypeVar("T")


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


def _seed_db(db_path: Path, notes_dir: Path) -> None:
    """Build a real index with one collection over a one-file tree."""
    notes_dir.mkdir(parents=True, exist_ok=True)
    (notes_dir / "seed.md").write_text("# Seed Note\n\nSeed paragraph text.\n", encoding="utf-8")
    db = Database(db_path)
    try:
        db.init_schema()
        with db.connection:
            CollectionRepository(db.connection).create(
                Collection(name="notes", path=str(notes_dir))
            )
    finally:
        db.close()


def _child_env() -> dict[str, str]:
    """Child environment: SIF_-stripped, FORCE_COLOR unset, NO_COLOR on."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("SIF_")}
    env.pop("FORCE_COLOR", None)
    env["NO_COLOR"] = "1"
    return env


def _reserve_loopback_port() -> int:
    """Reserve an ephemeral loopback port (pre-bind, close, tolerate the race)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _poll_until(check: Callable[[], T | None], deadline_s: float, description: str) -> T:
    """Poll ``check`` under an explicit deadline; None means "not yet"."""
    deadline = time.monotonic() + deadline_s
    while time.monotonic() < deadline:
        result = check()
        if result is not None:
            return result
        time.sleep(_POLL_INTERVAL_S)
    raise AssertionError(f"{description} not observed within {deadline_s}s")


def _pid_alive(pid: int) -> bool:
    """os.kill(pid, 0) liveness probe."""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _wait_pid_gone(pid: int, deadline_s: float) -> None:
    """Poll until the process is gone (deadline-bounded)."""
    _poll_until(
        lambda: True if not _pid_alive(pid) else None,
        deadline_s,
        f"PID {pid} to exit",
    )


def _read_pid(path: Path, deadline_s: float = _STARTUP_DEADLINE_S) -> int:
    """Poll for a parseable PID file; return its pid."""

    def _ready() -> int | None:
        payload = daemon.read_pid_file(path)
        if payload is None:
            return None
        pid = payload.get("pid")
        return pid if isinstance(pid, int) and not isinstance(pid, bool) else None

    return _poll_until(_ready, deadline_s, f"PID file {path.name}")


def _cli(*args: str) -> list[str]:
    """The module-form CLI launcher (ps-corroborable ``sif.cli.main``)."""
    return [sys.executable, "-u", "-m", "sif.cli.main", *args]


def _run_cli(args: list[str], cwd: Path, timeout: float = 60.0) -> subprocess.CompletedProcess[str]:
    """Run a real CLI subprocess with a hermetic child environment."""
    return subprocess.run(
        args,
        cwd=cwd,
        env=_child_env(),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _wait_for_log_marker(log_path: Path, needle: str, deadline_s: float) -> None:
    """Wait until the log's current content contains ``needle``."""

    def _seen() -> str | None:
        if not log_path.exists():
            return None
        text = log_path.read_text(encoding="utf-8", errors="replace")
        return text if needle in text else None

    _poll_until(_seen, deadline_s, f"marker {needle!r} in {log_path.name}")


def _header(headers: dict[str, str], name: str) -> str | None:
    """Case-insensitive header lookup."""
    return next((value for key, value in headers.items() if key.lower() == name), None)


def _initialize(port: int) -> tuple[dict[str, Any], dict[str, str]] | None:
    """POST a spec-valid 2024-11-05 initialize; None until the server answers.

    The params block is mandatory: the empty-params handshake is rejected with
    -32602, so a "bare" POST would prove nothing.
    """
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "sif-daemon-e2e", "version": "1"},
            },
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/mcp",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        method="POST",
    )
    try:
        with _PROXY_FREE_OPENER.open(request, timeout=2.0) as response:
            return json.loads(response.read().decode("utf-8")), dict(response.headers.items())
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return None


class TestMcpDaemonEndToEnd:
    """D-19..D-21 real-process proofs (POSIX only)."""

    @pytest.mark.skipif(not hasattr(os, "fork"), reason="POSIX double-fork daemon")
    def test_daemon_e2e_serves_initialize_and_stops(self, tmp_path: Path) -> None:
        """Arm -> bind -> 2024-11-05 initialize -> --stop -> PID removed."""
        db_path = tmp_path / "index.db"
        _seed_db(db_path, tmp_path / "notes")
        port = _reserve_loopback_port()
        log_path = tmp_path / "mcp.log"
        pid_path = daemon.pid_path_for_mcp(db_path)
        pid: int | None = None
        try:
            start = _run_cli(
                _cli(
                    "--index",
                    str(db_path),
                    "mcp",
                    "daemon",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--log-file",
                    str(log_path),
                ),
                cwd=tmp_path,
            )
            assert start.returncode == 0, (
                f"daemon parent exited {start.returncode}:\n"
                f"stdout:\n{start.stdout}\nstderr:\n{start.stderr}"
            )
            pid = _read_pid(pid_path)
            payload = daemon.read_pid_file(pid_path)
            assert payload is not None
            assert payload["pid"] == pid
            assert payload["mode"] == "mcp"
            assert payload["depth"] == "bm25"

            answer, headers = _poll_until(
                lambda: _initialize(port),
                _STARTUP_DEADLINE_S,
                "MCP initialize response",
            )
            assert answer["result"]["protocolVersion"] == "2024-11-05"
            assert _header(headers, "mcp-session-id")

            stop = _run_cli(
                _cli("--index", str(db_path), "mcp", "daemon", "--stop"),
                cwd=tmp_path,
            )
            assert stop.returncode == 0, (
                f"stop exited {stop.returncode}:\nstdout:\n{stop.stdout}\nstderr:\n{stop.stderr}"
            )
            assert "MCP daemon stopped" in stop.stdout
            _wait_pid_gone(pid, _STOP_DEADLINE_S)
            assert not pid_path.exists()

            again = _run_cli(
                _cli("--index", str(db_path), "mcp", "daemon", "--stop"),
                cwd=tmp_path,
            )
            assert "not running" in again.stdout
        finally:
            if pid_path.exists():
                _run_cli(
                    _cli("--index", str(db_path), "mcp", "daemon", "--stop"),
                    cwd=tmp_path,
                )
            if pid is not None and _pid_alive(pid):
                os.kill(pid, signal.SIGKILL)
                _wait_pid_gone(pid, _STOP_DEADLINE_S)
            pid_path.unlink(missing_ok=True)

    def test_daemon_bind_failure_removes_pid_and_propagates(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """D-21/T-22-19: a bind failure cleans the PID and is never swallowed."""
        db_path = tmp_path / "index.db"
        test_settings = Settings(
            _env_file=None, embedding_dim=8, model_name="test", cache_embeddings=False
        )
        # Patch BEFORE seeding so the schema and the arm agree on the dim.
        monkeypatch.setattr("sif.config.settings.get_settings", lambda: test_settings)
        monkeypatch.setattr("sif.mcp.backend.get_settings", lambda: test_settings)
        _seed_db(db_path, tmp_path / "notes")
        pid_path = daemon.pid_path_for_mcp(db_path)

        def fake_detach(_log_path: Path, arm: Callable[[], None]) -> daemon.DetachOutcome:
            arm()
            return daemon.DetachOutcome(daemon=True)

        def failing_host(*_args: Any, **_kwargs: Any) -> None:
            raise OSError("address already in use")

        monkeypatch.setattr(mcp_mod.daemon, "detach", fake_detach)
        monkeypatch.setattr(mcp_cli, "run_http_host", failing_host)

        result = CliRunner().invoke(
            mcp_mod.mcp_daemon_cmd,
            [
                "--host",
                "127.0.0.1",
                "--port",
                "0",
                "--log-file",
                str(tmp_path / "mcp.log"),
            ],
            obj={"index_path": db_path},
        )

        assert result.exit_code != 0
        assert isinstance(result.exception, OSError)
        assert not pid_path.exists()

    @pytest.mark.skipif(not hasattr(os, "fork"), reason="POSIX double-fork daemons")
    def test_daemon_coexists_with_a_watch_daemon(self, tmp_path: Path) -> None:
        """D-20: stopping the MCP daemon leaves the watch daemon and PID intact."""
        db_path = tmp_path / "index.db"
        _seed_db(db_path, tmp_path / "notes")
        watch_log = tmp_path / "watch.log"
        mcp_log = tmp_path / "mcp.log"
        watch_pid_path = daemon.pid_path_for(db_path)
        mcp_pid_path = daemon.pid_path_for_mcp(db_path)
        assert watch_pid_path != mcp_pid_path
        port = _reserve_loopback_port()
        watch_pid: int | None = None
        mcp_pid: int | None = None
        try:
            watch_start = _run_cli(
                _cli(
                    "--index",
                    str(db_path),
                    "watch",
                    "--detach",
                    "--log-file",
                    str(watch_log),
                ),
                cwd=tmp_path,
            )
            assert watch_start.returncode == 0, (
                f"watch detach exited {watch_start.returncode}:\n"
                f"stdout:\n{watch_start.stdout}\nstderr:\n{watch_start.stderr}"
            )
            watch_pid = _read_pid(watch_pid_path)
            # Steady state before the MCP arm touches the same schema.
            _wait_for_log_marker(watch_log, "Watching", _STARTUP_DEADLINE_S)

            mcp_start = _run_cli(
                _cli(
                    "--index",
                    str(db_path),
                    "mcp",
                    "daemon",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--log-file",
                    str(mcp_log),
                ),
                cwd=tmp_path,
            )
            assert mcp_start.returncode == 0, (
                f"mcp detach exited {mcp_start.returncode}:\n"
                f"stdout:\n{mcp_start.stdout}\nstderr:\n{mcp_start.stderr}"
            )
            mcp_pid = _read_pid(mcp_pid_path)

            assert watch_pid_path.exists()
            assert mcp_pid_path.exists()
            assert watch_pid_path.name.endswith(".watch.pid")
            assert mcp_pid_path.name.endswith(".mcp.pid")

            stop = _run_cli(
                _cli("--index", str(db_path), "mcp", "daemon", "--stop"),
                cwd=tmp_path,
            )
            assert stop.returncode == 0, stop.stderr
            assert "MCP daemon stopped" in stop.stdout
            _wait_pid_gone(mcp_pid, _STOP_DEADLINE_S)

            assert not mcp_pid_path.exists()
            assert watch_pid_path.exists()
            assert _pid_alive(watch_pid)
        finally:
            if mcp_pid_path.exists():
                _run_cli(
                    _cli("--index", str(db_path), "mcp", "daemon", "--stop"),
                    cwd=tmp_path,
                )
            _run_cli(
                _cli("--index", str(db_path), "watch", "--stop"),
                cwd=tmp_path,
            )
            if mcp_pid is not None and _pid_alive(mcp_pid):
                os.kill(mcp_pid, signal.SIGKILL)
                _wait_pid_gone(mcp_pid, _STOP_DEADLINE_S)
            if watch_pid is not None and _pid_alive(watch_pid):
                os.kill(watch_pid, signal.SIGKILL)
                _wait_pid_gone(watch_pid, _STOP_DEADLINE_S)

    def test_windows_daemon_refusal_names_posix_cause_and_foreground_remedy(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """D-19: no os.fork refuses before any log/PID work, cause + remedy."""
        monkeypatch.setattr(mcp_mod, "os", SimpleNamespace())

        result = CliRunner().invoke(
            mcp_mod.mcp_daemon_cmd, [], obj={"index_path": tmp_path / "index.db"}
        )

        assert result.exit_code != 0
        assert "POSIX fork" in result.output
        assert "sif mcp http" in result.output
        assert "foreground" in result.output
        assert "Traceback" not in result.output
