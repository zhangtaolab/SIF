#!/usr/bin/env python3
"""Windows degradation smoke: assert the CLI degrades honestly without POSIX semantics.

This is NOT a claim of full Windows support. It drives only the user-visible
surface with a per-run temporary ``SIF_DB_PATH`` and asserts the documented
degradations: the fcntl lock warning, the missing-root "all documents
preserved" guard, and the fork/service refusals. Every invocation is an
explicit argv list (never a shell) and every command is model-free — no
``query``/``vsearch``/``embed`` — so no embedder loads and no model is
downloaded on the user's machine.
"""

from __future__ import annotations

import json
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
_VERSION_FILE = PROJECT_ROOT / "src" / "sif" / "_version.py"
_STEP_TIMEOUT_SECONDS = 120

_FCNTL_WARNING_PARTS = (
    "fcntl unavailable on this platform; index lock disabled",
    "WAL + busy_timeout still protect database integrity",
)
_MISSING_ROOT_WARNING = "does not exist; skipping update (all documents preserved)"
_DETACH_REFUSAL_PARTS = ("POSIX fork", "foreground")
_SERVICE_REFUSAL_PARTS = ("not supported on Windows", "foreground")
_TRACEBACK_MARKER = "Traceback (most recent call last)"


def matches_fcntl_warning(stderr: str) -> bool:
    """Return True when stderr carries the full documented fcntl degradation."""
    return all(part in stderr for part in _FCNTL_WARNING_PARTS)


def matches_missing_root_warning(stderr: str) -> bool:
    """Return True when the missing-root update warning preserves all documents."""
    return _MISSING_ROOT_WARNING in stderr


def matches_detach_refusal(output: str) -> bool:
    """Return True when the detach path names the POSIX-fork cause and the remedy."""
    return all(part in output for part in _DETACH_REFUSAL_PARTS)


def matches_service_refusal(output: str) -> bool:
    """Return True when the service path names the Windows limitation and the remedy."""
    return all(part in output for part in _SERVICE_REFUSAL_PARTS)


def looks_like_traceback(text: str) -> bool:
    """Return True when the output leaked a raw Python traceback."""
    return _TRACEBACK_MARKER in text


def build_cli_invocations(python: str, docs_dir: Path, expected_version: str) -> list[list[str]]:
    """Build the argv-only invocation table in assertion order.

    ``expected_version`` is the repo's single-sourced version literal: the
    caller asserts the CLI reports it, so an empty literal would make that
    assertion vacuous and is rejected here.
    """
    if not expected_version:
        raise ValueError("expected_version must be the repo version literal")
    base = [python, "-m", "sif.cli.main"]
    return [
        [*base, "--version"],
        [*base, "collection", "add", str(docs_dir), "--name", "smoke"],
        [*base, "index", "update"],
        [*base, "search", "search", "needle", "--json"],
        [*base, "status"],
        [*base, "index", "update"],
        [*base, "watch", "--detach"],
        [*base, "watch", "--install-service"],
    ]


def _emit(line: str) -> None:
    """Write one smoke line to stdout."""
    sys.stdout.write(line + "\n")


def _run(argv: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Run one argv list from the project root; never a shell, always bounded."""
    return subprocess.run(
        argv,
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=_STEP_TIMEOUT_SECONDS,
    )


def _report(step: str, argv: list[str], proc: subprocess.CompletedProcess[str], ok: bool) -> bool:
    """Print one PASS/FAIL line, including argv/exit/streams on failure."""
    if ok:
        _emit(f"PASS {step}")
        return True
    _emit(f"FAIL {step}")
    _emit(f"  argv: {argv}")
    _emit(f"  exit: {proc.returncode}")
    _emit(f"  stdout: {proc.stdout!r}")
    _emit(f"  stderr: {proc.stderr!r}")
    return False


def _preflight_head() -> str | None:
    """Print the yoga checkout HEAD and refuse a dirty tree (Pitfall 9)."""
    env = os.environ.copy()
    head_proc = _run(["git", "rev-parse", "HEAD"], env)
    if head_proc.returncode != 0:
        _emit(f"FAIL git rev-parse HEAD exited {head_proc.returncode}: {head_proc.stderr!r}")
        return None
    head = head_proc.stdout.strip()
    _emit(f"HEAD {head}")
    status_proc = _run(["git", "status", "--porcelain"], env)
    if status_proc.returncode != 0:
        _emit(f"FAIL git status --porcelain exited {status_proc.returncode}")
        return None
    if status_proc.stdout.strip():
        _emit("FAIL the checkout is dirty; sync yoga to the commit under test first")
        _emit(status_proc.stdout)
        return None
    return head


def _expected_version() -> str:
    """Read the repo's single-sourced version literal (hatch's source of truth)."""
    namespace = runpy.run_path(str(_VERSION_FILE))
    return str(namespace["__version__"])


def _step_version(argv: list[str], env: dict[str, str], expected_version: str) -> bool:
    """Assert ``sif --version`` reports the repo version literal."""
    proc = _run(argv, env)
    ok = proc.returncode == 0 and f"sif, version {expected_version}" in proc.stdout
    return _report("version", argv, proc, ok)


def _step_success(step: str, argv: list[str], env: dict[str, str]) -> bool:
    """Assert a command exits zero."""
    proc = _run(argv, env)
    return _report(step, argv, proc, proc.returncode == 0)


def _step_index_update(argv: list[str], env: dict[str, str], *, first: bool) -> bool:
    """Assert the index update counts and its degradation warning.

    The first pass must add the seeded document and carry the fcntl warning;
    the post-delete pass must remove nothing and carry the missing-root
    "all documents preserved" warning (Pitfall 11).
    """
    proc = _run(argv, env)
    if first:
        stdout_ok = "Index updated:" in proc.stdout and "Added: 1" in proc.stdout
        stderr_ok = matches_fcntl_warning(proc.stderr)
        ok = proc.returncode == 0 and stdout_ok and stderr_ok
        return _report("index update (flock warning)", argv, proc, ok)
    stdout_ok = "Index updated:" in proc.stdout and "Removed: 0" in proc.stdout
    stderr_ok = matches_missing_root_warning(proc.stderr)
    ok = proc.returncode == 0 and stdout_ok and stderr_ok
    return _report("index update (missing root preserved)", argv, proc, ok)


def _step_search(argv: list[str], env: dict[str, str]) -> bool:
    """Assert the BM25 JSON search yields exactly one result."""
    proc = _run(argv, env)
    try:
        payload = json.loads(proc.stdout)
        one_result = isinstance(payload, list) and len(payload) == 1
    except json.JSONDecodeError:
        one_result = False
    return _report("BM25 search json", argv, proc, proc.returncode == 0 and one_result)


def _step_status(argv: list[str], env: dict[str, str]) -> bool:
    """Assert the status table renders its title and Documents row."""
    proc = _run(argv, env)
    ok = proc.returncode == 0 and "Index Status" in proc.stdout and "Documents" in proc.stdout
    return _report("status", argv, proc, ok)


def _step_refusal(
    step: str,
    argv: list[str],
    env: dict[str, str],
    matcher: Callable[[str], bool],
) -> bool:
    """Assert a refusal path exits non-zero with a clear message, never a traceback."""
    proc = _run(argv, env)
    combined = proc.stdout + proc.stderr
    ok = proc.returncode != 0 and matcher(combined) and not looks_like_traceback(combined)
    return _report(step, argv, proc, ok)


def _run_table(
    argv_table: list[list[str]],
    docs_dir: Path,
    env: dict[str, str],
    expected_version: str,
) -> list[str]:
    """Execute the assertion table in order; return the failed step names."""
    version, collection_add, index_update, search, status, index_update_after, detach, service = (
        argv_table
    )
    results = [
        ("version", _step_version(version, env, expected_version)),
        ("collection add", _step_success("collection add", collection_add, env)),
        ("index update", _step_index_update(index_update, env, first=True)),
        ("BM25 search json", _step_search(search, env)),
        ("status", _step_status(status, env)),
    ]
    shutil.rmtree(docs_dir)
    results.extend(
        [
            (
                "index update after delete",
                _step_index_update(index_update_after, env, first=False),
            ),
            (
                "watch --detach refusal",
                _step_refusal("watch --detach refusal", detach, env, matches_detach_refusal),
            ),
            (
                "watch --install-service refusal",
                _step_refusal(
                    "watch --install-service refusal", service, env, matches_service_refusal
                ),
            ),
        ]
    )
    return [step for step, ok in results if not ok]


def main() -> int:
    """Run the CLI degradation assertion table; return 0 only when all pass."""
    head = _preflight_head()
    if head is None:
        return 1
    try:
        expected_version = _expected_version()
    except (KeyError, OSError) as exc:
        _emit(f"FAIL cannot read {_VERSION_FILE}: {exc}")
        return 1

    with tempfile.TemporaryDirectory(prefix="sif-windows-smoke-") as raw_tmp:
        tmp = Path(raw_tmp)
        docs_dir = tmp / "docs"
        docs_dir.mkdir()
        (docs_dir / "needle.md").write_text(
            "# Needle\n\nOne needle document for the Windows degradation smoke.\n",
            encoding="utf-8",
        )
        env = os.environ.copy()
        env["SIF_DB_PATH"] = str(tmp / "sif.db")
        env.pop("NO_COLOR", None)
        env.pop("FORCE_COLOR", None)
        argv_table = build_cli_invocations(sys.executable, docs_dir, expected_version)
        failures = _run_table(argv_table, docs_dir, env, expected_version)

    if failures:
        _emit(f"FAILED {len(failures)} assertion(s): {', '.join(failures)}")
        return 1
    _emit(f"PASS all assertions; tested HEAD {head}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
