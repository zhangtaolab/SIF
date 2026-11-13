"""Unit battery for the Windows degradation smoke matchers (ENG-02, plan 17-04).

Pure-function tests only: nothing here invokes sif, touches a database, or
starts a subprocess. The script itself is exercised on hc yoga by
``make windows-smoke``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.windows_smoke import (
    build_cli_invocations,
    looks_like_traceback,
    matches_detach_refusal,
    matches_fcntl_warning,
    matches_missing_root_warning,
    matches_service_refusal,
)


FCNTL_WARNING = (
    "WARNING: fcntl unavailable on this platform; index lock disabled "
    "(WAL + busy_timeout still protect database integrity)\n"
)
MISSING_ROOT_WARNING = (
    "WARNING: Collection root D:\\docs does not exist; skipping update (all documents preserved)\n"
)
DETACH_REFUSAL = (
    "Error: --detach requires POSIX fork support and is not available on "
    "Windows; run `sif watch` in the foreground instead.\n"
)
SERVICE_REFUSAL = (
    "Error: the watch service is not supported on Windows; "
    "run `sif watch` in the foreground instead\n"
)
ATTRIBUTE_ERROR_TRACEBACK = (
    "Traceback (most recent call last):\n"
    '  File "sif\\utils\\daemon.py", line 241, in detach\n'
    "AttributeError: module 'os' has no attribute 'fork'\n"
)
BARE_TRACEBACK = (
    "Traceback (most recent call last):\n"
    '  File "sif\\cli\\commands\\watch.py", line 451, in _run_install_service\n'
    "RuntimeError: boom\n"
)


def test_fcntl_warning_matcher() -> None:
    """Both halves of the documented fcntl degradation must be present."""
    assert matches_fcntl_warning(FCNTL_WARNING)

    assert not matches_fcntl_warning("fcntl unavailable on this platform; index lock disabled")
    assert not matches_fcntl_warning("")


def test_missing_root_matcher() -> None:
    """Only the update warning (not the drift-walk variant) satisfies the check."""
    assert matches_missing_root_warning(MISSING_ROOT_WARNING)

    assert not matches_missing_root_warning(
        "Collection root D:\\docs does not exist; skipping drift walk (all documents preserved)"
    )
    assert not matches_missing_root_warning("")


def test_detach_refusal_matcher() -> None:
    """The detach refusal must name the POSIX-fork cause and the remedy."""
    assert matches_detach_refusal(DETACH_REFUSAL)

    assert not matches_detach_refusal("AttributeError: module 'os' has no attribute 'fork'")
    assert not matches_detach_refusal("POSIX fork support is unavailable")


def test_service_refusal_matcher() -> None:
    """The service refusal must name Windows and the foreground remedy."""
    assert matches_service_refusal(SERVICE_REFUSAL)

    assert not matches_service_refusal(
        "systemctl was not found on PATH — required to install the watch service (Linux only)."
    )
    assert not matches_service_refusal("")


def test_traceback_is_never_accepted() -> None:
    """A raw traceback is detected even when a refusal message also appears."""
    assert looks_like_traceback(ATTRIBUTE_ERROR_TRACEBACK)
    assert looks_like_traceback(BARE_TRACEBACK)
    assert looks_like_traceback(ATTRIBUTE_ERROR_TRACEBACK + DETACH_REFUSAL)
    assert not looks_like_traceback(DETACH_REFUSAL)
    assert not looks_like_traceback(SERVICE_REFUSAL)
    assert not matches_detach_refusal(ATTRIBUTE_ERROR_TRACEBACK)


def test_commands_are_argv_lists_without_model_loading(tmp_path: Path) -> None:
    """Every invocation is an argv list and none names a model-loading subcommand."""
    invocations = build_cli_invocations("python", tmp_path, "1.1.2")

    assert len(invocations) == 8
    for argv in invocations:
        assert isinstance(argv, list)
        assert argv
        assert all(isinstance(item, str) for item in argv)
        for forbidden in ("query", "vsearch", "embed", "pull"):
            assert forbidden not in argv

    assert invocations[0][-1] == "--version"
    assert invocations[-1][-2:] == ["watch", "--install-service"]


def test_empty_expected_version_is_rejected(tmp_path: Path) -> None:
    """An empty version literal would make the version assertion vacuous."""
    with pytest.raises(ValueError, match="version literal"):
        build_cli_invocations("python", tmp_path, "")
