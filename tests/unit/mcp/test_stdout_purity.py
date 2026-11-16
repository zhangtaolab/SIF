"""Cold stdio stdout-purity baseline (Phase 22 D-16 / T-22-04).

Runs the REAL ``python -m sif.cli.main mcp stdio`` subprocess with:

- a temporary ``HOME`` containing the legacy ``docsift/models`` fixture, so the
  pre-run migration notice is exercised, and
- a temporary index, so the developer's platform database is never opened.

Every stdout line must parse as a JSON-RPC frame: no ANSI, no progress bars,
and no migration text. The migration notice must appear on stderr instead.

The client is interactive (initialize, then the status call) because the SDK
stdio server, like a real client, expects the handshake to settle before the
next request; batching every line and closing stdin races the connection.
"""

from __future__ import annotations

import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[3]
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_RESPONSE_DEADLINE_S = 60.0
_SHUTDOWN_DEADLINE_S = 60.0
_POLL_S = 0.1


def _child_env(home: Path, db_path: Path) -> dict[str, str]:
    """Child environment: stripped SIF_, temp HOME, color disabled."""
    env = {key: value for key, value in os.environ.items() if not key.startswith("SIF_")}
    env.pop("FORCE_COLOR", None)
    env["NO_COLOR"] = "1"
    env["HOME"] = str(home)
    env["SIF_DB_PATH"] = str(db_path)
    return env


class _StdioProcess:
    """Interactive line-protocol client over a real stdio subprocess."""

    def __init__(self, home: Path, db_path: Path) -> None:
        self._proc = subprocess.Popen(
            [
                sys.executable,
                "-u",
                "-m",
                "sif.cli.main",
                "--index",
                str(db_path),
                "mcp",
                "stdio",
            ],
            cwd=_REPO_ROOT,
            env=_child_env(home, db_path),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.stdout_lines: list[str] = []
        self.stderr_text = ""
        self._pending: queue.Queue[str] = queue.Queue()
        self._stderr_chunks: list[str] = []
        self._readers = [
            threading.Thread(target=self._pump_stdout, daemon=True),
            threading.Thread(target=self._pump_stderr, daemon=True),
        ]
        for reader in self._readers:
            reader.start()

    def _pump_stdout(self) -> None:
        assert self._proc.stdout is not None
        for raw in self._proc.stdout:
            line = raw.decode("utf-8", errors="replace").strip()
            if line:
                self.stdout_lines.append(line)
                self._pending.put(line)

    def _pump_stderr(self) -> None:
        assert self._proc.stderr is not None
        for raw in self._proc.stderr:
            self._stderr_chunks.append(raw.decode("utf-8", errors="replace"))
            self.stderr_text = "".join(self._stderr_chunks)

    def send(self, message: dict[str, Any]) -> None:
        assert self._proc.stdin is not None
        self._proc.stdin.write((json.dumps(message) + "\n").encode("utf-8"))
        self._proc.stdin.flush()

    def wait_response(self, msg_id: int, description: str) -> dict[str, Any]:
        deadline = time.monotonic() + _RESPONSE_DEADLINE_S
        while time.monotonic() < deadline:
            try:
                line = self._pending.get(timeout=_POLL_S)
            except queue.Empty:
                continue
            try:
                frame = json.loads(line)
            except json.JSONDecodeError:
                continue
            if frame.get("id") == msg_id:
                return frame
        raise AssertionError(
            f"{description} not received; stdout={self.stdout_lines!r}; "
            f"stderr tail:\n{self.stderr_text[-2000:]}"
        )

    def finish(self) -> int:
        if self._proc.stdin is not None:
            self._proc.stdin.close()
        return self._proc.wait(timeout=_SHUTDOWN_DEADLINE_S)

    def __enter__(self) -> _StdioProcess:
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        if self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=_SHUTDOWN_DEADLINE_S)
            except subprocess.TimeoutExpired:  # pragma: no cover - safety net
                self._proc.kill()
                self._proc.wait(timeout=_SHUTDOWN_DEADLINE_S)
        for stream in (self._proc.stdin, self._proc.stdout, self._proc.stderr):
            if stream is not None:
                stream.close()


def test_cold_stdio_stdout_emits_only_json_rpc_frames(tmp_path: Path) -> None:
    """The protocol channel stays clean even when the migration notice fires."""
    home = tmp_path / "home"
    legacy_models = home / ".local" / "share" / "docsift" / "models"
    legacy_models.mkdir(parents=True)
    (legacy_models / "fixture.txt").write_text("legacy model cache fixture", encoding="utf-8")
    db_path = tmp_path / "purity.db"

    with _StdioProcess(home, db_path) as server:
        server.send(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "sif-purity", "version": "1"},
                },
            }
        )
        initialize = server.wait_response(1, "initialize response")
        assert initialize["result"]["protocolVersion"] == "2024-11-05"
        server.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        server.send(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "status", "arguments": {}},
            }
        )
        status = server.wait_response(3, "status response")
        returncode = server.finish()

    assert returncode == 0, f"stdio server failed:\n{server.stderr_text[-4000:]}"
    # The hazard fired: the legacy cache was migrated, and the notice is on
    # stderr rather than the protocol channel.
    assert "Migrated" in server.stderr_text
    assert "docsift" in server.stderr_text

    assert server.stdout_lines, "the server must answer the handshake and status call"
    frames: list[dict[str, Any]] = []
    for line in server.stdout_lines:
        assert _ANSI_ESCAPE.search(line) is None, f"ANSI escape on stdout: {line!r}"
        try:
            frame = json.loads(line)
        except json.JSONDecodeError:
            pytest.fail(f"non-JSON stdout line corrupts the protocol channel: {line!r}")
        assert isinstance(frame, dict), f"non-object JSON-RPC frame: {frame!r}"
        assert frame.get("jsonrpc") == "2.0", f"non JSON-RPC frame: {frame!r}"
        frames.append(frame)

    result_payload = status["result"]
    assert result_payload["isError"] is False
    assert json.loads(result_payload["content"][0]["text"]) == result_payload["structuredContent"]
