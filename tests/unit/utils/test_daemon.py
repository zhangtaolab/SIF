"""Hermetic unit battery for :mod:`sif.utils.daemon` (13-02, LIVE-09).

Pure/read-path coverage only — no ``os.fork``, no real signals, no real
``ps`` (the real-process lifecycle proofs live in
``tests/integration/test_watch_daemon_e2e.py``). Every kill/ps interaction
is faked through the module's ``os.kill``/``subprocess``/``shutil`` seams;
the tests pin the escalation ORDER (SIGTERM before SIGKILL), the unlink
behavior, and the fail-closed corroboration outcomes (Pitfall 3, T-13-03).
"""

from __future__ import annotations

import os
import signal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from sif.utils import daemon


_PAYLOAD = {
    "pid": 999999,
    "mode": "daemon",
    "depth": "bm25",
    "started": "2026-11-07T00:00:00+00:00",
}


def _write_payload(path: Path, pid: int = 999999) -> None:
    daemon.write_pid_file(path, pid=pid, mode="daemon", depth="bm25")


def _alive_kill(_pid: int, _sig: int) -> None:
    """os.kill fake for a process that always answers the 0-probe."""


def _ps_run(stdout: str):
    """subprocess.run fake answering with the given ps command line."""

    def _run(_argv: list[str], **_kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(returncode=0, stdout=stdout)

    return _run


class TestPidPath:
    """Test 1: the sibling artifact path derivation (D-05)."""

    def test_pid_path_for_derives_resolved_sibling(self, tmp_path: Path) -> None:
        """tmp db -> tmp db + '.watch.pid', fully resolved (locking.py parity)."""
        db_path = tmp_path / "watch.db"

        pid_file = daemon.pid_path_for(db_path)

        resolved = db_path.resolve()
        assert pid_file == resolved.with_name(resolved.name + ".watch.pid")
        assert pid_file.name == "watch.db.watch.pid"
        assert pid_file.parent == resolved.parent


class TestPidPayload:
    """Test 2: payload round-trip; every defect reads back as None (T-13-04)."""

    def test_write_read_round_trip_with_0600_mode(self, tmp_path: Path) -> None:
        path = tmp_path / "sif.db.watch.pid"

        daemon.write_pid_file(path, pid=4242, mode="daemon", depth="bm25")
        payload = daemon.read_pid_file(path)

        assert payload is not None
        assert payload["pid"] == 4242
        assert payload["mode"] == "daemon"
        assert payload["depth"] == "bm25"
        assert isinstance(payload["started"], str)
        assert payload["started"] != ""
        assert path.stat().st_mode & 0o777 == 0o600

    def test_write_replaces_a_preplanted_symlink_without_following_it(self, tmp_path: Path) -> None:
        """Temp-then-rename hardening (IN-03): the symlink itself is replaced."""
        victim = tmp_path / "victim.txt"
        victim.write_text("do not touch", encoding="utf-8")
        pid_file = tmp_path / "sif.db.watch.pid"
        pid_file.symlink_to(victim)

        daemon.write_pid_file(pid_file, pid=4242, mode="daemon", depth="bm25")

        # The symlink was atomically replaced by a regular file, not followed.
        assert not pid_file.is_symlink()
        assert victim.read_text(encoding="utf-8") == "do not touch"
        payload = daemon.read_pid_file(pid_file)
        assert payload is not None
        assert payload["pid"] == 4242

    def test_missing_file_reads_as_none(self, tmp_path: Path) -> None:
        assert daemon.read_pid_file(tmp_path / "absent.pid") is None

    @pytest.mark.parametrize(
        "content",
        [
            b"",  # empty file
            b"\x00\xff\xfe not json",  # garbage bytes
            b"[1, 2, 3]",  # valid JSON, wrong shape
            b'{"pid": "123", "mode": "daemon", "depth": "bm25", "started": "x"}',
            b'{"pid": 123}',  # missing fields
            b'{"pid": 123, "mode": "daemon", "depth": "bm25", "started": 7}',
        ],
    )
    def test_defective_content_reads_as_none(self, tmp_path: Path, content: bytes) -> None:
        path = tmp_path / "sif.db.watch.pid"
        path.write_bytes(content)

        assert daemon.read_pid_file(path) is None


class TestPidFileConcurrentWriters:
    """WR-01: per-process temp names — two ``sif watch --detach`` arming on the
    same index never share a temp inode (the module's contract: two daemons
    may run simultaneously), so a healthy second armer never fails its rename
    and never corrupts the first writer's payload."""

    def test_temp_name_carries_the_writer_pid(self, tmp_path: Path, monkeypatch) -> None:
        """The temp artifact is ``.<name>.<pid>.tmp`` — a fixed function of the
        WRITER, not of the final path, so concurrent writers cannot collide."""
        path = tmp_path / "sif.db.watch.pid"
        replaced: list[str] = []
        real_replace = os.replace
        monkeypatch.setattr(daemon.os, "getpid", lambda: 31337)

        def _capture(src, dst) -> None:
            replaced.append(str(src))
            real_replace(src, dst)

        monkeypatch.setattr(daemon.os, "replace", _capture)

        daemon.write_pid_file(path, pid=4242, mode="daemon", depth="bm25")

        assert replaced == [str(tmp_path / ".sif.db.watch.pid.31337.tmp")]
        assert not list(tmp_path.glob("*.tmp"))  # rename consumed the temp
        assert daemon.read_pid_file(path) is not None

    def test_second_writer_between_create_and_rename_still_succeeds(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """The exact WR-01 interleaving: writer B arms while writer A sits
        between its temp create and its rename. Per-process temp names keep
        the two create/write/rename sequences independent — both renames
        land (last writer wins) and neither writer raises. The shared fixed
        temp name made A's rename raise FileNotFoundError: a healthy daemon
        reported "failed to start"."""
        path = tmp_path / "sif.db.watch.pid"
        current = {"pid": 1111}
        first_rename = {"done": False}
        real_replace = os.replace
        monkeypatch.setattr(daemon.os, "getpid", lambda: current["pid"])

        def _interleave(src, dst) -> None:
            if not first_rename["done"]:
                first_rename["done"] = True
                # Inside A's rename window: B runs a FULL concurrent write —
                # temp create, payload write, and its own rename — against
                # the same PID path before A's rename proceeds.
                current["pid"] = 2222
                daemon.write_pid_file(path, pid=2222, mode="daemon", depth="bm25")
                current["pid"] = 1111
            real_replace(src, dst)

        monkeypatch.setattr(daemon.os, "replace", _interleave)

        daemon.write_pid_file(path, pid=1111, mode="daemon", depth="bm25")

        payload = daemon.read_pid_file(path)
        assert payload is not None
        assert payload["pid"] == 1111  # A's rename resumed after B's — last wins
        assert not list(tmp_path.glob("*.tmp"))  # neither writer leaked a temp


class TestCorroboratePid:
    """Test 3: identity corroboration is fail-closed on every branch (Pitfall 3)."""

    def test_ps_argv_with_sif_watch_markers_corroborates(self, monkeypatch) -> None:
        monkeypatch.setattr(daemon.os, "kill", _alive_kill)
        monkeypatch.setattr(
            daemon,
            "subprocess",
            SimpleNamespace(
                run=_ps_run(
                    "/opt/python3.13 -u -m sif.cli.main --index "
                    "/tmp/watch.db watch --detach --log-file /tmp/d.log"
                )
            ),
        )

        assert daemon.corroborate_pid(dict(_PAYLOAD)) is True

    def test_unrelated_process_command_does_not_corroborate(self, monkeypatch) -> None:
        monkeypatch.setattr(daemon.os, "kill", _alive_kill)
        monkeypatch.setattr(
            daemon,
            "subprocess",
            SimpleNamespace(run=_ps_run("/opt/python3.13 /usr/local/bin/other-tool serve")),
        )

        assert daemon.corroborate_pid(dict(_PAYLOAD)) is False

    def test_watch_in_a_path_fragment_does_not_corroborate(self, monkeypatch) -> None:
        """A 'watch.db' path token must not count as the watch marker."""
        monkeypatch.setattr(daemon.os, "kill", _alive_kill)
        monkeypatch.setattr(
            daemon,
            "subprocess",
            SimpleNamespace(
                run=_ps_run("/opt/python3.13 -u -m sif.cli.main --index /tmp/watch.db mcp stdio")
            ),
        )

        assert daemon.corroborate_pid(dict(_PAYLOAD)) is False

    def test_process_gone_does_not_corroborate_and_never_runs_ps(self, monkeypatch) -> None:
        def _gone(_pid: int, _sig: int) -> None:
            raise ProcessLookupError()

        monkeypatch.setattr(daemon.os, "kill", _gone)
        calls: list[Any] = []

        def _no_run(argv: Any, **_kwargs: Any) -> None:
            calls.append(argv)

        monkeypatch.setattr(daemon, "subprocess", SimpleNamespace(run=_no_run))

        assert daemon.corroborate_pid(dict(_PAYLOAD)) is False
        assert calls == []

    def test_ps_executable_missing_fails_closed(self, monkeypatch) -> None:
        monkeypatch.setattr(daemon.os, "kill", _alive_kill)
        monkeypatch.setattr(daemon, "shutil", SimpleNamespace(which=lambda _name: None))

        assert daemon.corroborate_pid(dict(_PAYLOAD)) is False

    def test_ps_failure_fails_closed(self, monkeypatch) -> None:
        monkeypatch.setattr(daemon.os, "kill", _alive_kill)
        monkeypatch.setattr(daemon, "subprocess", SimpleNamespace(run=_ps_run_with_code(1)))

        assert daemon.corroborate_pid(dict(_PAYLOAD)) is False

    def test_wrong_typed_pid_never_probes(self, monkeypatch) -> None:
        monkeypatch.setattr(daemon.os, "kill", _alive_kill)
        assert daemon.corroborate_pid({"pid": "123"}) is False


def _ps_run_with_code(returncode: int):
    """subprocess.run fake failing with the given return code."""

    def _run(_argv: list[str], **_kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(returncode=returncode, stdout="")

    return _run


class TestStopEscalation:
    """Test 4: stop_daemon escalation order and unlink behavior with fakes."""

    def test_alive_at_deadline_sends_term_then_kill_and_unlinks(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """The full escalation: SIGTERM, bounded wait expiry, SIGKILL, unlink."""
        pid_file = tmp_path / "sif.db.watch.pid"
        _write_payload(pid_file)
        sent: list[tuple[int, int]] = []

        def fake_kill(pid: int, sig: int) -> None:
            if sig != 0:
                sent.append((pid, sig))

        monkeypatch.setattr(daemon.os, "kill", fake_kill)
        monkeypatch.setattr(daemon, "corroborate_pid", lambda _payload: True)

        outcome = daemon.stop_daemon(
            pid_file, term_timeout_s=0.03, kill_timeout_s=0.03, poll_interval_s=0.01
        )

        assert outcome.status == "stopped"
        assert outcome.pid == 999999
        assert [sig for _, sig in sent] == [signal.SIGTERM, signal.SIGKILL]
        assert not pid_file.exists()

    def test_gone_after_term_never_sends_kill(self, tmp_path: Path, monkeypatch) -> None:
        """SIGKILL only happens when the bounded wait expired (D-05)."""
        pid_file = tmp_path / "sif.db.watch.pid"
        _write_payload(pid_file)
        sent: list[int] = []
        gone = False

        def fake_kill(_pid: int, sig: int) -> None:
            nonlocal gone
            if sig == 0:
                if gone:
                    raise ProcessLookupError()
                return
            sent.append(sig)
            gone = True  # the daemon exits promptly on SIGTERM (D-14)

        monkeypatch.setattr(daemon.os, "kill", fake_kill)
        monkeypatch.setattr(daemon, "corroborate_pid", lambda _payload: True)

        outcome = daemon.stop_daemon(
            pid_file, term_timeout_s=5.0, kill_timeout_s=5.0, poll_interval_s=0.01
        )

        assert outcome.status == "stopped"
        assert sent == [signal.SIGTERM]
        assert not pid_file.exists()

    def test_gone_before_signal_issues_no_signal(self, tmp_path: Path, monkeypatch) -> None:
        """Died between corroboration and SIGTERM: no crash, no signal, unlink."""
        pid_file = tmp_path / "sif.db.watch.pid"
        _write_payload(pid_file)
        sent: list[int] = []

        def fake_kill(_pid: int, sig: int) -> None:
            sent.append(sig)
            raise ProcessLookupError()

        monkeypatch.setattr(daemon.os, "kill", fake_kill)
        monkeypatch.setattr(daemon, "corroborate_pid", lambda _payload: True)

        outcome = daemon.stop_daemon(pid_file)

        assert outcome.status == "stopped"
        assert sent == [signal.SIGTERM]
        assert not pid_file.exists()

    def test_stale_uncorroborated_payload_only_unlinks(self, tmp_path: Path, monkeypatch) -> None:
        """Fail-closed: an uncorroborated PID is never signalled (Pitfall 3)."""
        pid_file = tmp_path / "sif.db.watch.pid"
        _write_payload(pid_file)
        monkeypatch.setattr(daemon.os, "kill", lambda _pid, _sig: pytest.fail("signal sent"))
        monkeypatch.setattr(daemon, "corroborate_pid", lambda _payload: False)

        outcome = daemon.stop_daemon(pid_file)

        assert outcome.status == "stale"
        assert outcome.pid == 999999
        assert not pid_file.exists()

    def test_garbage_payload_is_stale_and_cleaned(self, tmp_path: Path, monkeypatch) -> None:
        pid_file = tmp_path / "sif.db.watch.pid"
        pid_file.write_bytes(b"\x00garbage")
        monkeypatch.setattr(daemon.os, "kill", lambda _pid, _sig: pytest.fail("signal sent"))

        outcome = daemon.stop_daemon(pid_file)

        assert outcome.status == "stale"
        assert not pid_file.exists()

    def test_missing_file_is_not_running(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(daemon.os, "kill", lambda _pid, _sig: pytest.fail("signal sent"))

        outcome = daemon.stop_daemon(tmp_path / "absent.pid")

        assert outcome.status == "not_running"


class TestStopCliPath:
    """The CLI wrapper renders each StopOutcome branch (stop-idempotence)."""

    def test_not_running_message(self, monkeypatch, capsys) -> None:
        from sif.cli.commands import watch as watch_mod

        monkeypatch.setattr(daemon, "stop_daemon", lambda _path: daemon.StopOutcome("not_running"))
        watch_mod._run_stop("/tmp/sif.db")
        output = capsys.readouterr().out
        assert "not running" in output
        assert "stale" not in output

    def test_stale_message(self, monkeypatch, capsys) -> None:
        from sif.cli.commands import watch as watch_mod

        monkeypatch.setattr(daemon, "stop_daemon", lambda _path: daemon.StopOutcome("stale", pid=7))
        watch_mod._run_stop("/tmp/sif.db")
        output = capsys.readouterr().out
        assert "not running" in output
        assert "stale PID file removed" in output

    def test_stopped_message_names_the_pid(self, monkeypatch, capsys) -> None:
        from sif.cli.commands import watch as watch_mod

        monkeypatch.setattr(
            daemon, "stop_daemon", lambda _path: daemon.StopOutcome("stopped", pid=4242)
        )
        watch_mod._run_stop("/tmp/sif.db")
        output = capsys.readouterr().out
        assert "stopped" in output
        assert "4242" in output


class TestDetachTimeout:
    """SC2/WR-04: a handshake timeout must never leave a silent maybe-daemon.

    The parent branch of ``detach`` SIGKILLs the detached process group
    before reporting the failure, and the error says so (with the --stop
    belt-and-braces). Hermetic: fork/read/killpg/waitpid are all faked.
    """

    def test_timeout_outcome_reports_the_termination(self) -> None:
        outcome = daemon._parent_outcome(None, 30.0)

        assert outcome.daemon is False
        assert outcome.pid is None
        assert "did not report readiness within 30s" in outcome.error
        assert "terminated" in outcome.error
        assert "sif watch --stop" in outcome.error

    def test_kill_detached_group_sigkills_the_pgid(self, monkeypatch) -> None:
        sent: list[tuple[int, int]] = []
        monkeypatch.setattr(daemon.os, "killpg", lambda pgid, sig: sent.append((pgid, sig)))

        daemon._kill_detached_group(4321)

        assert sent == [(4321, signal.SIGKILL)]

    def test_kill_detached_group_tolerates_an_already_gone_group(self, monkeypatch) -> None:
        def _gone(_pgid: int, _sig: int) -> None:
            raise ProcessLookupError()

        monkeypatch.setattr(daemon.os, "killpg", _gone)

        daemon._kill_detached_group(4321)  # must not raise

    def test_detach_timeout_kills_group_then_reports_terminated(
        self, monkeypatch, tmp_path
    ) -> None:
        """Wiring: with no handshake message, the parent killpgs the forked
        child's pid — the detached session's pgid (setsid made that child
        the group leader) — before translating the failure."""
        killed: list[tuple[int, int]] = []
        monkeypatch.setattr(daemon.os, "fork", lambda: 4321)
        monkeypatch.setattr(daemon, "_read_pipe_message", lambda _fd, _timeout: None)
        monkeypatch.setattr(daemon.os, "killpg", lambda pgid, sig: killed.append((pgid, sig)))
        monkeypatch.setattr(daemon.os, "waitpid", lambda pid, _flags: (pid, 0))

        outcome = daemon.detach(tmp_path / "watch.log", lambda: None, arm_timeout_s=0.5)

        assert outcome.daemon is False
        assert "terminated" in (outcome.error or "")
        assert killed == [(4321, signal.SIGKILL)]
