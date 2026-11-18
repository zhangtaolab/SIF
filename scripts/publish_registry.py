#!/usr/bin/env python3
"""Preflight and publish the MCP Registry listing for io.github.zhangtaolab/sif.

The script is deliberately stdlib-only and never imports the ``sif`` package:
``--check`` is a read-only preflight (README ownership marker, PyPI release
presence, ``server.json`` consistency, Registry reachability) and ``--publish``
adds the ``mcp-publisher publish`` call. Authentication is delegated entirely
to the publisher's device flow; nothing here reads, writes, or prints
credentials.

Exit codes: 0 means the requested operation succeeded (including an already
listed name+version, which is never published twice); non-zero means a
preflight refusal, a network failure, or the publisher's own exit status.
"""

from __future__ import annotations

import argparse
import json
import runpy
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
_VERSION_FILE = PROJECT_ROOT / "src" / "sif" / "_version.py"
README_PATH = PROJECT_ROOT / "README.md"
SERVER_JSON_PATH = PROJECT_ROOT / "server.json"

SERVER_NAME = "io.github.zhangtaolab/sif"
PACKAGE_NAME = "docsif"
README_MARKER = f"<!-- mcp-name: {SERVER_NAME} -->"
PYPI_URL = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"
REGISTRY_BASE_URL = "https://registry.modelcontextprotocol.io"
PUBLISHER = "mcp-publisher"
_TIMEOUT_SECONDS = 20
_HTTP_OK = 200
_HTTP_NOT_FOUND = 404


def _emit(message: str) -> None:
    """Write one preflight line to stdout."""
    sys.stdout.write(message + "\n")


def _read_version(version_file: Path | None = None) -> str:
    """Read the single-sourced version literal without importing the package."""
    path = _VERSION_FILE if version_file is None else version_file
    namespace = runpy.run_path(str(path))
    return str(namespace["__version__"])


def _http_get_json(url: str) -> tuple[int, Any]:
    """GET a JSON endpoint and return ``(status, payload)``.

    HTTP error statuses are returned normally so callers can distinguish a
    well-formed 404 from a transport failure; network errors propagate.
    """
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            return int(response.status), json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            payload: Any = json.loads(body)
        except ValueError:
            payload = body
        return int(exc.code), payload


def check_readme_marker(readme_path: Path | None = None) -> str | None:
    """Return a refusal message unless the README carries the exact marker line."""
    path = README_PATH if readme_path is None else readme_path
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return f"FAIL cannot read {path}: {exc}"
    if README_MARKER not in lines:
        return f"FAIL README marker mismatch: expected a line exactly {README_MARKER!r} in {path}"
    return None


def _http_status_error(status: int, *, subject: str, missing: str) -> str | None:
    """Map a non-success HTTP status to a refusal, or return None on 200."""
    if status == _HTTP_NOT_FOUND:
        return missing
    if status != _HTTP_OK:
        return f"FAIL {subject} returned HTTP {status}"
    return None


def check_pypi_version(version: str) -> str | None:
    """Return a refusal message unless PyPI serves the declared release."""
    try:
        status, payload = _http_get_json(PYPI_URL)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return f"FAIL PyPI lookup failed for {PACKAGE_NAME}: {exc}"
    error = _http_status_error(
        status,
        subject=f"PyPI lookup for {PACKAGE_NAME}",
        missing=f"FAIL PyPI project {PACKAGE_NAME} not found (404)",
    )
    if error is not None:
        return error
    if not isinstance(payload, dict):
        return f"FAIL PyPI JSON for {PACKAGE_NAME} is not an object"
    releases = payload.get("releases")
    if not isinstance(releases, dict):
        return f"FAIL PyPI JSON for {PACKAGE_NAME} is missing releases"
    if version not in releases:
        return f"FAIL PyPI {PACKAGE_NAME} has no release {version}"
    return None


def _load_manifest(path: Path) -> dict[str, Any] | str:
    """Read a JSON manifest, returning the parsed object or a refusal message."""
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return f"FAIL cannot read {path}: {exc}"
    except ValueError as exc:
        return f"FAIL {path} is not valid JSON: {exc}"
    if not isinstance(manifest, dict):
        return f"FAIL {path} is not a JSON object"
    return manifest


def _select_pypi_package(manifest: dict[str, Any]) -> dict[str, Any] | str:
    """Return the PyPI package entry, or a refusal message."""
    packages = manifest.get("packages")
    if not isinstance(packages, list) or not packages:
        return "FAIL server.json packages must be a non-empty list"
    for package in packages:
        if isinstance(package, dict) and package.get("registryType") == "pypi":
            return package
    return "FAIL server.json has no pypi package entry"


def _check_package(package: dict[str, Any], version: str) -> str | None:
    """Return a refusal unless the PyPI package entry matches docsif and version."""
    if package.get("identifier") != PACKAGE_NAME:
        return (
            f"FAIL server.json package identifier mismatch: "
            f"{package.get('identifier')!r} != {PACKAGE_NAME!r}"
        )
    if package.get("version") != version:
        return (
            f"FAIL server.json package version mismatch: {package.get('version')!r} != {version!r}"
        )
    transport = package.get("transport")
    if not isinstance(transport, dict) or transport.get("type") != "stdio":
        return "FAIL server.json package transport must be stdio"
    return None


def check_server_manifest(version: str, server_json_path: Path | None = None) -> str | None:
    """Return a refusal message unless server.json agrees with name, package, and version."""
    path = SERVER_JSON_PATH if server_json_path is None else server_json_path
    manifest = _load_manifest(path)
    if isinstance(manifest, str):
        return manifest
    if manifest.get("name") != SERVER_NAME:
        return f"FAIL server.json name mismatch: {manifest.get('name')!r} != {SERVER_NAME!r}"
    if manifest.get("version") != version:
        return f"FAIL server.json version mismatch: {manifest.get('version')!r} != {version!r}"
    package = _select_pypi_package(manifest)
    if isinstance(package, str):
        return package
    return _check_package(package, version)


def registry_url(version: str) -> str:
    """Build the version-lookup URL for the declared name and version."""
    encoded_name = urllib.parse.quote(SERVER_NAME, safe="")
    encoded_version = urllib.parse.quote(version, safe="")
    return f"{REGISTRY_BASE_URL}/v0.1/servers/{encoded_name}/versions/{encoded_version}"


def lookup_registry(version: str) -> tuple[bool | None, str | None]:
    """Return ``(listed, error)`` for the declared name+version.

    ``listed`` is True on 200, False on a well-formed 404 (the normal
    pre-publish state), and None when the lookup itself failed.
    """
    try:
        status, payload = _http_get_json(registry_url(version))
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return None, f"FAIL registry lookup failed: {exc}"
    if status == _HTTP_NOT_FOUND:
        if not isinstance(payload, dict):
            return None, "FAIL registry lookup returned a malformed 404 response"
        return False, None
    if status == _HTTP_OK:
        return True, None
    return None, f"FAIL registry lookup returned HTTP {status}"


def run_preflight(version: str) -> tuple[bool, bool | None]:
    """Run the read-only checks in order; return ``(ok, listed)``."""
    checks: tuple[tuple[str, Callable[[], str | None]], ...] = (
        ("README marker", check_readme_marker),
        ("PyPI version", partial(check_pypi_version, version)),
        ("server.json", partial(check_server_manifest, version)),
    )
    for label, check in checks:
        error = check()
        if error is not None:
            _emit(error)
            return False, None
        _emit(f"OK {label}")
    listed, error = lookup_registry(version)
    if error is not None:
        _emit(error)
        return False, None
    if listed:
        _emit(f"OK registry: already listed {SERVER_NAME} {version}")
    else:
        _emit(f"OK registry: not listed (reachable) {SERVER_NAME} {version}")
    return True, listed


def publish(version: str) -> int:
    """Invoke the authenticated publisher and propagate its exit status."""
    try:
        result = subprocess.run([PUBLISHER, "publish"], cwd=PROJECT_ROOT, check=False)
    except FileNotFoundError:
        _emit(f"FAIL {PUBLISHER} is not installed; install it and run `{PUBLISHER} login github`")
        return 1
    if result.returncode == 0:
        _emit(f"published {SERVER_NAME} {version}")
    else:
        _emit(f"FAIL {PUBLISHER} publish exited {result.returncode}")
    return int(result.returncode)


def build_parser() -> argparse.ArgumentParser:
    """Build the mutually exclusive ``--check``/``--publish`` parser."""
    parser = argparse.ArgumentParser(
        description="Preflight and publish the SIF MCP Registry listing.",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="run the read-only preflight")
    mode.add_argument(
        "--publish",
        action="store_true",
        help="run the preflight, then publish when the version is not listed",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the requested mode and return the process exit status."""
    args = build_parser().parse_args(argv)
    try:
        version = _read_version()
    except (KeyError, OSError) as exc:
        _emit(f"FAIL cannot read {_VERSION_FILE}: {exc}")
        return 1
    ok, listed = run_preflight(version)
    if not ok:
        return 1
    if args.check:
        return 0
    if listed:
        _emit("already listed")
        return 0
    return publish(version)


if __name__ == "__main__":
    sys.exit(main())
