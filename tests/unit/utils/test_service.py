"""Unit tests for the watch service install/uninstall module (13-04, SC3).

Generation is pure text and asserted on ANY platform (D-13): the plist is
parsed back through plistlib and the systemd unit text asserted directly —
no platform-skipped generation tests. Manager invocation is asserted via a
fake runner recording exact argv lists — never a real launchctl/systemctl
call in unit tests (the live proof lives in tests/integration/
test_service_live_launchd.py behind SIF_TEST_LIVE_LAUNCHD).
"""

from __future__ import annotations

import ast
import os
import plistlib
import stat
import subprocess
from pathlib import Path
from typing import Any

import pytest

from sif.utils import service
from sif.utils.service import (
    SERVICE_LABEL,
    UNIT_NAME,
    ServiceManagerMissing,
    build_plist,
    install_watch_service,
    render_unit,
    uninstall_watch_service,
)


def _ok(argv: list[str]) -> subprocess.CompletedProcess[str]:
    """A successful scripted manager result."""
    return subprocess.CompletedProcess(argv, 0, stdout="active", stderr="")


def _mode_of(path: Path) -> int:
    """The artifact's permission bits (S_IMODE)."""
    return stat.S_IMODE(os.stat(path).st_mode)


def _fake_which(monkeypatch: pytest.MonkeyPatch) -> None:
    """Gate check passes hermetically on any platform."""
    monkeypatch.setattr(service.shutil, "which", lambda _name: "/usr/bin/fakebin")


class _RecordingRunner:
    """Fake ``subprocess.run`` recording exact argv lists (never a real manager)."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(argv))
        return _ok(argv)


class TestPlistGeneration:
    """Test 1: the launchd LaunchAgent carries the locked D-13 keys (any platform)."""

    def test_round_trip_carries_label_argv_supervision_and_logs(self, tmp_path) -> None:
        db = tmp_path / "index" / "sif.db"
        log_dir = tmp_path / "logs"

        plist = build_plist("/usr/bin/python3", db, ["-c", "notes", "--embed"], log_dir)

        parsed = plistlib.loads(plistlib.dumps(plist))
        assert parsed["Label"] == SERVICE_LABEL
        assert parsed["ProgramArguments"] == [
            "/usr/bin/python3",
            "-m",
            "sif.cli.main",
            "--index",
            str(Path(db).resolve()),
            "watch",
            "-c",
            "notes",
            "--embed",
        ]
        assert parsed["RunAtLoad"] is True
        assert parsed["KeepAlive"] is True
        assert parsed["ThrottleInterval"] == 10
        assert parsed["StandardOutPath"] == str(Path(log_dir) / "watch.log")
        assert parsed["StandardErrorPath"] == str(Path(log_dir) / "watch.err.log")


class TestUnitGeneration:
    """Test 2: the systemd user unit carries the locked D-13 keys (any platform)."""

    def test_rendered_text_carries_sections_and_exec_start(self, tmp_path) -> None:
        db = tmp_path / "sif.db"

        text = render_unit("/usr/bin/python3", db, ["-c", "notes", "--embed"])

        assert "[Unit]" in text
        assert "[Service]" in text
        assert "[Install]" in text
        assert text.index("[Unit]") < text.index("[Service]") < text.index("[Install]")
        assert "Type=simple" in text
        assert "Restart=on-failure" in text
        assert "RestartSec=5" in text
        assert "WantedBy=default.target" in text
        exec_line = next(line for line in text.splitlines() if line.startswith("ExecStart="))
        assert exec_line == (
            f"ExecStart=/usr/bin/python3 -m sif.cli.main "
            f"--index {Path(db).resolve()} watch -c notes --embed"
        )

    def test_whitespace_tokens_are_quoted(self, tmp_path) -> None:
        """A collection name with a space must not split into phantom argv."""
        db = tmp_path / "sif.db"

        text = render_unit("/usr/bin/python3", db, ["-c", "my notes"])

        exec_line = next(line for line in text.splitlines() if line.startswith("ExecStart="))
        assert '"my notes"' in exec_line


class TestInstallArgvLaunchd:
    """Test 3: exact launchctl argv (bootstrap, verify) and a 0644 artifact."""

    def test_bootstrap_then_print_with_domain_target_and_mode(self, tmp_path, monkeypatch) -> None:
        _fake_which(monkeypatch)
        dest_dir = tmp_path / "LaunchAgents"
        runner = _RecordingRunner()

        result = install_watch_service(
            tmp_path / "sif.db",
            ["-c", "notes"],
            manager="launchd",
            python="/usr/bin/python3",
            dest_dir=dest_dir,
            log_dir=tmp_path / "logs",
            runner=runner,
        )

        uid = os.getuid()
        plist_path = dest_dir / f"{SERVICE_LABEL}.plist"
        assert runner.calls == [
            ["launchctl", "bootstrap", f"gui/{uid}", str(plist_path)],
            ["launchctl", "print", f"gui/{uid}/{SERVICE_LABEL}"],
        ]
        assert result.artifact_path == plist_path
        assert result.log_location == str(tmp_path / "logs" / "watch.log")
        assert result.verify_command == f"launchctl print gui/{uid}/{SERVICE_LABEL}"
        assert plist_path.exists()
        assert _mode_of(plist_path) == 0o644
        parsed = plistlib.loads(plist_path.read_bytes())
        assert parsed["Label"] == SERVICE_LABEL


class TestInstallArgvSystemd:
    """Test 4: exact systemctl argv (reload, enable --now, is-active) and a 0644 unit."""

    def test_reload_enable_now_then_is_active(self, tmp_path, monkeypatch) -> None:
        _fake_which(monkeypatch)
        dest_dir = tmp_path / "systemd" / "user"
        runner = _RecordingRunner()

        result = install_watch_service(
            tmp_path / "sif.db",
            [],
            manager="systemd",
            python="/usr/bin/python3",
            dest_dir=dest_dir,
            runner=runner,
        )

        assert runner.calls == [
            ["systemctl", "--user", "daemon-reload"],
            ["systemctl", "--user", "enable", "--now", "sif-watch"],
            ["systemctl", "--user", "is-active", "sif-watch"],
        ]
        unit_path = dest_dir / UNIT_NAME
        assert result.artifact_path == unit_path
        assert result.log_location == "journalctl --user -u sif-watch -f"
        assert result.verify_command == "systemctl --user status sif-watch"
        assert _mode_of(unit_path) == 0o644
        assert "Type=simple" in unit_path.read_text()


class TestReinstallConflict:
    """Test 5 (Pitfall 5): a conflicting bootstrap is booted out, then retried."""

    def test_first_bootstrap_failure_runs_bootout_then_retries(self, tmp_path, monkeypatch) -> None:
        _fake_which(monkeypatch)
        dest_dir = tmp_path / "LaunchAgents"
        plist_path = dest_dir / f"{SERVICE_LABEL}.plist"
        plist_path.parent.mkdir(parents=True)
        plist_path.write_bytes(b"stale bytes from an older install")
        bootstraps = {"count": 0}
        calls: list[list[str]] = []

        def runner(argv: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
            calls.append(list(argv))
            if argv[1] == "bootstrap":
                bootstraps["count"] += 1
                if bootstraps["count"] == 1:
                    return subprocess.CompletedProcess(
                        argv, 5, stdout="", stderr="Bootstrap failed: 5: Input/output error"
                    )
            return _ok(argv)

        install_watch_service(
            tmp_path / "sif.db",
            [],
            manager="launchd",
            python="/usr/bin/python3",
            dest_dir=dest_dir,
            log_dir=tmp_path / "logs",
            runner=runner,
        )

        uid = os.getuid()
        assert calls == [
            ["launchctl", "bootstrap", f"gui/{uid}", str(plist_path)],
            ["launchctl", "bootout", f"gui/{uid}/{SERVICE_LABEL}"],
            ["launchctl", "bootstrap", f"gui/{uid}", str(plist_path)],
            ["launchctl", "print", f"gui/{uid}/{SERVICE_LABEL}"],
        ]
        # The stale artifact was replaced by the freshly generated plist.
        assert plistlib.loads(plist_path.read_bytes())["Label"] == SERVICE_LABEL


class TestMissingManager:
    """Test 6: a missing manager binary raises a typed, friendly error."""

    @pytest.mark.parametrize("manager", ["launchd", "systemd"])
    def test_raises_typed_error_before_any_write(self, tmp_path, monkeypatch, manager) -> None:
        monkeypatch.setattr(service.shutil, "which", lambda _name: None)
        dest_dir = tmp_path / "dest"

        with pytest.raises(ServiceManagerMissing) as exc_info:
            install_watch_service(
                tmp_path / "sif.db",
                [],
                manager=manager,
                dest_dir=dest_dir,
                runner=_RecordingRunner(),
            )

        binary = "launchctl" if manager == "launchd" else "systemctl"
        assert binary in str(exc_info.value)
        assert "watch service" in str(exc_info.value)
        assert not dest_dir.exists()  # the gate fires before any artifact write

    def test_uninstall_gates_the_manager_too(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(service.shutil, "which", lambda _name: None)

        with pytest.raises(ServiceManagerMissing):
            uninstall_watch_service(manager="launchd", dest_dir=tmp_path, runner=_RecordingRunner())


class TestUninstallArgv:
    """Stop-then-remove semantics for both managers (D-11/D-12)."""

    def test_launchd_bootout_then_unlink(self, tmp_path, monkeypatch) -> None:
        _fake_which(monkeypatch)
        dest_dir = tmp_path / "LaunchAgents"
        plist_path = dest_dir / f"{SERVICE_LABEL}.plist"
        plist_path.parent.mkdir(parents=True)
        plist_path.write_bytes(plistlib.dumps({"Label": SERVICE_LABEL}))
        runner = _RecordingRunner()

        removed = uninstall_watch_service(manager="launchd", dest_dir=dest_dir, runner=runner)

        uid = os.getuid()
        assert runner.calls == [["launchctl", "bootout", f"gui/{uid}/{SERVICE_LABEL}"]]
        assert removed == plist_path
        assert not plist_path.exists()

    def test_systemd_disable_now_unlink_then_reload(self, tmp_path, monkeypatch) -> None:
        _fake_which(monkeypatch)
        dest_dir = tmp_path / "systemd" / "user"
        unit_path = dest_dir / UNIT_NAME
        unit_path.parent.mkdir(parents=True)
        unit_path.write_text("[Unit]\n", encoding="utf-8")
        runner = _RecordingRunner()

        removed = uninstall_watch_service(manager="systemd", dest_dir=dest_dir, runner=runner)

        assert runner.calls == [
            ["systemctl", "--user", "disable", "--now", "sif-watch"],
            ["systemctl", "--user", "daemon-reload"],
        ]
        assert removed == unit_path
        assert not unit_path.exists()


class TestInvocationDiscipline:
    """D-12 source discipline (AST, not prose): no shell, argv lists only."""

    def test_no_shell_true_or_string_command_lines_in_module(self) -> None:
        source = Path(service.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for keyword in node.keywords:
                if (
                    keyword.arg == "shell"
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is True
                ):
                    pytest.fail(f"shell=True at line {node.lineno}: forbidden (D-12)")
            if (
                isinstance(node.func, ast.Name)
                and node.func.id == "_run"
                and len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)
            ):
                pytest.fail(
                    f"_run call at line {node.lineno} passes a string, not an argv list (D-12)"
                )
