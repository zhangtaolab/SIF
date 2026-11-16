"""MCP Registry script preflight and idempotency (Phase 22 MCP-09).

All HTTP is mocked, so these tests exercise the refusal branches, the
already-listed short circuit, and the publisher delegation without touching
the network.
"""

from __future__ import annotations

import importlib.util
import json
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from sif._version import __version__


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "publish_registry.py"
SERVER_JSON_PATH = PROJECT_ROOT / "server.json"
README_PATH = PROJECT_ROOT / "README.md"

SERVER_NAME = "io.github.zhangtaolab/sif"
PACKAGE_NAME = "docsif"
CREDENTIAL_KEYS = ("password", "api_key", "apikey", "secret", "bearer", "token")


def _load_registry_script() -> Any:
    """Load scripts/publish_registry.py as a module (it is not a package)."""
    spec = importlib.util.spec_from_file_location("publish_registry", SCRIPT_PATH)
    assert spec is not None, "could not create an import spec"
    assert spec.loader is not None, "import spec has no loader"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def registry_script() -> Any:
    """The loaded publish_registry module."""
    return _load_registry_script()


@pytest.fixture(autouse=True)
def repo_fixture_paths(registry_script: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the script at the real repo fixtures unless a test overrides them."""
    monkeypatch.setattr(registry_script, "README_PATH", README_PATH)
    monkeypatch.setattr(registry_script, "SERVER_JSON_PATH", SERVER_JSON_PATH)


def _fake_http(
    *,
    pypi_status: int = 200,
    pypi_payload: Any = None,
    registry_status: int = 404,
    registry_payload: Any = None,
) -> tuple[Any, list[str]]:
    """Build a fake ``_http_get_json`` plus the list of requested URLs."""
    urls: list[str] = []

    def _fake(url: str) -> tuple[int, Any]:
        urls.append(url)
        if url.startswith("https://pypi.org/"):
            payload = {"releases": {__version__: []}} if pypi_payload is None else pypi_payload
            return pypi_status, payload
        payload = {"detail": "Server not found"} if registry_payload is None else registry_payload
        return registry_status, payload

    return _fake, urls


def _write_server_json(path: Path, **overrides: Any) -> Path:
    """Copy the real manifest to ``path`` with top-level overrides applied."""
    manifest = json.loads(SERVER_JSON_PATH.read_text(encoding="utf-8"))
    manifest.update(overrides)
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


class TestServerJson:
    """server.json matches the published package and the version source."""

    def test_manifest_identity(self) -> None:
        """Name, package, transport, and version agree with the release surface."""
        manifest = json.loads(SERVER_JSON_PATH.read_text(encoding="utf-8"))
        assert manifest["name"] == SERVER_NAME
        assert manifest["version"] == __version__
        assert 0 < len(manifest["description"]) <= 100
        assert "\n" not in manifest["description"]
        packages = manifest["packages"]
        assert len(packages) == 1
        package = packages[0]
        assert package["registryType"] == "pypi"
        assert package["identifier"] == PACKAGE_NAME
        assert package["version"] == __version__
        assert package["transport"] == {"type": "stdio"}

    def test_manifest_has_no_remote_or_credential_fields(self) -> None:
        """No remote transport, OAuth, or credential-like field is declared."""
        manifest = json.loads(SERVER_JSON_PATH.read_text(encoding="utf-8"))
        text = json.dumps(manifest).lower()
        for key in (*CREDENTIAL_KEYS, "remotes", "oauth"):
            assert key not in text, f"server.json declares {key!r}"


class TestCheck:
    """``--check`` validates every preflight branch and refuses each mismatch."""

    def test_check_passes_for_repo_state(
        self,
        registry_script: Any,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """The checked-in README/version/server.json pass with a reachable 404."""
        fake, urls = _fake_http()
        monkeypatch.setattr(registry_script, "_http_get_json", fake)

        assert registry_script.main(["--check"]) == 0

        output = capsys.readouterr().out
        assert "not listed (reachable)" in output
        assert any("pypi.org/pypi/docsif/json" in url for url in urls)
        assert f"{SERVER_NAME.replace('/', '%2F')}/versions/{__version__}" in urls[-1]

    def test_check_passes_when_already_listed(
        self,
        registry_script: Any,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """A 200 registry lookup passes ``--check`` as already listed."""
        fake, _ = _fake_http(
            registry_status=200, registry_payload={"server": {"name": SERVER_NAME}}
        )
        monkeypatch.setattr(registry_script, "_http_get_json", fake)

        assert registry_script.main(["--check"]) == 0
        assert "already listed" in capsys.readouterr().out

    def test_marker_mismatch_refuses(
        self,
        registry_script: Any,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """A missing exact README marker refuses before any network call."""
        readme = tmp_path / "README.md"
        readme.write_text("# SIF\n\nNo ownership marker here.\n", encoding="utf-8")
        monkeypatch.setattr(registry_script, "README_PATH", readme)
        fake, urls = _fake_http()
        monkeypatch.setattr(registry_script, "_http_get_json", fake)

        assert registry_script.main(["--check"]) == 1

        assert "FAIL README marker mismatch" in capsys.readouterr().out
        assert urls == []

    def test_pypi_404_refuses(
        self,
        registry_script: Any,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """A missing PyPI project refuses the check."""
        fake, _ = _fake_http(pypi_status=404, pypi_payload={"message": "Not Found"})
        monkeypatch.setattr(registry_script, "_http_get_json", fake)

        assert registry_script.main(["--check"]) == 1
        assert f"FAIL PyPI project {PACKAGE_NAME} not found (404)" in capsys.readouterr().out

    def test_pypi_missing_version_refuses(
        self,
        registry_script: Any,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """A PyPI project without the declared release refuses the check."""
        fake, _ = _fake_http(pypi_payload={"releases": {"1.0.0": []}})
        monkeypatch.setattr(registry_script, "_http_get_json", fake)

        assert registry_script.main(["--check"]) == 1
        assert f"has no release {__version__}" in capsys.readouterr().out

    def test_pypi_network_failure_refuses(
        self,
        registry_script: Any,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """A transport failure is a refusal naming PyPI, not a traceback."""

        def _offline(*_args: Any) -> tuple[int, Any]:
            raise urllib.error.URLError("offline")

        monkeypatch.setattr(registry_script, "_http_get_json", _offline)

        assert registry_script.main(["--check"]) == 1
        assert f"FAIL PyPI lookup failed for {PACKAGE_NAME}" in capsys.readouterr().out

    def test_server_json_version_mismatch_refuses(
        self,
        registry_script: Any,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """A server.json version that disagrees with _version.py refuses."""
        manifest_path = _write_server_json(tmp_path / "server.json", version="9.9.9")
        monkeypatch.setattr(registry_script, "SERVER_JSON_PATH", manifest_path)
        fake, _ = _fake_http()
        monkeypatch.setattr(registry_script, "_http_get_json", fake)

        assert registry_script.main(["--check"]) == 1
        assert "FAIL server.json version mismatch" in capsys.readouterr().out

    def test_server_json_name_mismatch_refuses(
        self,
        registry_script: Any,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """A server.json name that disagrees with the namespace refuses."""
        manifest_path = _write_server_json(tmp_path / "server.json", name="io.github.example/other")
        monkeypatch.setattr(registry_script, "SERVER_JSON_PATH", manifest_path)
        fake, _ = _fake_http()
        monkeypatch.setattr(registry_script, "_http_get_json", fake)

        assert registry_script.main(["--check"]) == 1
        assert "FAIL server.json name mismatch" in capsys.readouterr().out

    def test_server_json_package_mismatch_refuses(
        self,
        registry_script: Any,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """A package identifier other than docsif refuses."""
        manifest = json.loads(SERVER_JSON_PATH.read_text(encoding="utf-8"))
        manifest["packages"][0]["identifier"] = "not-docsif"
        manifest_path = tmp_path / "server.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        monkeypatch.setattr(registry_script, "SERVER_JSON_PATH", manifest_path)
        fake, _ = _fake_http()
        monkeypatch.setattr(registry_script, "_http_get_json", fake)

        assert registry_script.main(["--check"]) == 1
        assert "FAIL server.json package identifier mismatch" in capsys.readouterr().out

    def test_registry_5xx_refuses(
        self,
        registry_script: Any,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """A registry 5xx is a refusal, never a silent not-listed pass."""
        fake, _ = _fake_http(registry_status=503, registry_payload={"detail": "unavailable"})
        monkeypatch.setattr(registry_script, "_http_get_json", fake)

        assert registry_script.main(["--check"]) == 1
        assert "FAIL registry lookup returned HTTP 503" in capsys.readouterr().out

    def test_malformed_registry_404_refuses(
        self,
        registry_script: Any,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Only a well-formed JSON 404 counts as the not-listed state."""
        fake, _ = _fake_http(registry_status=404, registry_payload="not a JSON object")
        monkeypatch.setattr(registry_script, "_http_get_json", fake)

        assert registry_script.main(["--check"]) == 1
        assert "FAIL registry lookup returned a malformed 404 response" in capsys.readouterr().out


class TestPublish:
    """``--publish`` is idempotent and delegates authentication to mcp-publisher."""

    def test_already_listed_skips_publisher(
        self,
        registry_script: Any,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """A listed name+version prints ``already listed`` and exits 0."""
        fake, _ = _fake_http(
            registry_status=200, registry_payload={"server": {"name": SERVER_NAME}}
        )
        monkeypatch.setattr(registry_script, "_http_get_json", fake)
        calls: list[list[str]] = []

        def _unexpected(args: Any, **_kwargs: Any) -> Any:
            calls.append(list(args))
            raise AssertionError("publisher must not run for an already listed version")

        monkeypatch.setattr(registry_script.subprocess, "run", _unexpected)

        assert registry_script.main(["--publish"]) == 0

        output = capsys.readouterr().out
        assert "already listed" in output
        assert calls == []

    def test_publish_invokes_publisher_on_404(
        self,
        registry_script: Any,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """A not-listed version invokes mcp-publisher publish and exits 0."""
        fake, _ = _fake_http(registry_status=404)
        monkeypatch.setattr(registry_script, "_http_get_json", fake)
        calls: list[tuple[list[str], Path, bool]] = []

        def _record(args: Any, **kwargs: Any) -> Any:
            calls.append((list(args), kwargs["cwd"], kwargs["check"]))
            return SimpleNamespace(returncode=0)

        monkeypatch.setattr(registry_script.subprocess, "run", _record)

        assert registry_script.main(["--publish"]) == 0

        assert calls == [(["mcp-publisher", "publish"], PROJECT_ROOT, False)]
        assert f"published {SERVER_NAME} {__version__}" in capsys.readouterr().out

    def test_publish_propagates_publisher_failure(
        self,
        registry_script: Any,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """The publisher's non-zero exit status propagates unchanged."""
        fake, _ = _fake_http(registry_status=404)
        monkeypatch.setattr(registry_script, "_http_get_json", fake)

        def _failing(*_args: Any, **_kwargs: Any) -> Any:
            return SimpleNamespace(returncode=7)

        monkeypatch.setattr(registry_script.subprocess, "run", _failing)

        assert registry_script.main(["--publish"]) == 7
        assert "publish exited 7" in capsys.readouterr().out

    def test_missing_publisher_refuses(
        self,
        registry_script: Any,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """A missing mcp-publisher names the install and login remedy."""
        fake, _ = _fake_http(registry_status=404)
        monkeypatch.setattr(registry_script, "_http_get_json", fake)

        def _missing(*_args: Any, **_kwargs: Any) -> Any:
            raise FileNotFoundError("mcp-publisher")

        monkeypatch.setattr(registry_script.subprocess, "run", _missing)

        assert registry_script.main(["--publish"]) == 1
        assert "is not installed" in capsys.readouterr().out

    def test_publish_refuses_when_preflight_fails(
        self,
        registry_script: Any,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """A preflight refusal stops ``--publish`` before the publisher runs."""
        fake, _ = _fake_http(registry_status=503, registry_payload={"detail": "unavailable"})
        monkeypatch.setattr(registry_script, "_http_get_json", fake)
        calls: list[list[str]] = []

        def _unexpected(args: Any, **_kwargs: Any) -> Any:
            calls.append(list(args))
            raise AssertionError("publisher must not run after a failed preflight")

        monkeypatch.setattr(registry_script.subprocess, "run", _unexpected)

        assert registry_script.main(["--publish"]) == 1
        assert calls == []
        assert "FAIL registry lookup returned HTTP 503" in capsys.readouterr().out


class TestCredentialFreeSource:
    """The script contains no credential handling and no publisher auth flag."""

    def test_script_source_has_no_credential_keys(self) -> None:
        """A source scan finds no credential-like key."""
        source = SCRIPT_PATH.read_text(encoding="utf-8").lower()
        for key in CREDENTIAL_KEYS:
            assert key not in source, f"credential-like key in script: {key}"

    def test_script_adds_no_auth_arguments(self) -> None:
        """The publisher is invoked with only its publish subcommand."""
        source = SCRIPT_PATH.read_text(encoding="utf-8")
        assert '"--token"' not in source
        assert "Authorization" not in source
