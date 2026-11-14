"""Regression tests pinning the release metadata surfaces (ENG-03)."""

from __future__ import annotations

import runpy
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"
CHANGELOG = REPO_ROOT / "docs" / "changelog.md"
VERSION_MODULE = REPO_ROOT / "src" / "sif" / "_version.py"
PYPROJECT = REPO_ROOT / "pyproject.toml"
PUBLISH_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "publish.yml"

MCP_NAME_MARKER = "<!-- mcp-name: io.github.zhangtaolab/sif -->"


def _top_level_block(text: str, key: str) -> str:
    """Return the body of a top-level ``key:`` block, up to the next top-level key."""
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.rstrip() == f"{key}:":
            start = index + 1
            break
    assert start is not None, f"missing top-level {key}: block"

    body: list[str] = []
    for line in lines[start:]:
        if line and not line.startswith(" "):
            break
        body.append(line)
    return "\n".join(body)


def _job_blocks(text: str) -> dict[str, str]:
    """Split the jobs mapping into per-job text blocks keyed by job id."""
    blocks: dict[str, list[str]] = {}
    current: str | None = None
    for line in _top_level_block(text, "jobs").splitlines():
        stripped = line.strip()
        if line.startswith("  ") and not line.startswith("    ") and stripped.endswith(":"):
            current = stripped[:-1]
            blocks[current] = []
        elif current is not None:
            blocks[current].append(line)
    return {name: "\n".join(body) for name, body in blocks.items()}


def test_readme_has_mcp_name_marker() -> None:
    """The Registry ownership marker is one complete README line, no trailing period."""
    lines = README.read_text(encoding="utf-8").splitlines()
    assert MCP_NAME_MARKER in lines, "README is missing the exact mcp-name marker line"


def test_changelog_has_1_1_2() -> None:
    """The changelog records 1.1.2 and its compare/release links."""
    text = CHANGELOG.read_text(encoding="utf-8")
    assert "## [1.1.2]" in text
    assert "[1.1.2]:" in text
    assert "compare/v1.1.2...HEAD" in text


def test_version_literal_is_1_1_2() -> None:
    """The single version literal the publish tag gate reads is 1.1.2."""
    version = runpy.run_path(str(VERSION_MODULE))["__version__"]
    assert version == "1.1.2"


def test_pyproject_readme_is_readme_md() -> None:
    """hatchling bakes README.md into the PyPI description at build time."""
    text = PYPROJECT.read_text(encoding="utf-8")
    assert 'readme = "README.md"' in text


def test_publish_workflow_is_tag_gated() -> None:
    """Only a v* tag push triggers publishing; no branch or PR trigger."""
    trigger = _top_level_block(PUBLISH_WORKFLOW.read_text(encoding="utf-8"), "on")
    assert "push:" in trigger
    assert "tags: ['v*']" in trigger
    assert "branches" not in trigger
    assert "pull_request" not in trigger


def test_publish_workflow_scopes_id_token() -> None:
    """id-token: write is job-scoped to the publish jobs, never workflow-global."""
    text = PUBLISH_WORKFLOW.read_text(encoding="utf-8")
    jobs = _job_blocks(text)
    assert set(jobs) == {"build", "publish-testpypi", "publish-pypi"}
    assert "id-token: write" in jobs["publish-testpypi"]
    assert "id-token: write" in jobs["publish-pypi"]
    assert "id-token" not in jobs["build"]
    assert _top_level_block(text, "permissions").strip() == "contents: read"


def test_publish_workflow_uses_artifact_handoff() -> None:
    """The build job uploads one dist artifact that both publish jobs download."""
    jobs = _job_blocks(PUBLISH_WORKFLOW.read_text(encoding="utf-8"))
    assert "uv build" in jobs["build"]
    assert "actions/upload-artifact@v7" in jobs["build"]
    assert "name: dist" in jobs["build"]
    for name in ("publish-testpypi", "publish-pypi"):
        assert "actions/download-artifact@v8" in jobs[name]
        assert "name: dist" in jobs[name]
        assert "uv build" not in jobs[name]


def test_publish_workflow_orders_testpypi_first() -> None:
    """TestPyPI is the required dry run and is the only index that skips existing files."""
    jobs = _job_blocks(PUBLISH_WORKFLOW.read_text(encoding="utf-8"))
    assert "needs: build" in jobs["publish-testpypi"]
    assert "needs: publish-testpypi" in jobs["publish-pypi"]
    assert "https://test.pypi.org/legacy/" in jobs["publish-testpypi"]
    assert "skip-existing: true" in jobs["publish-testpypi"]
    assert "skip-existing" not in jobs["publish-pypi"]
    assert "test.pypi.org" not in jobs["publish-pypi"]


def test_publish_workflow_version_gate() -> None:
    """The build job refuses a tag that does not equal the _version.py literal."""
    build = _job_blocks(PUBLISH_WORKFLOW.read_text(encoding="utf-8"))["build"]
    assert "src/sif/_version.py" in build
    assert "GITHUB_REF_NAME" in build


def test_publish_workflow_has_no_secrets() -> None:
    """Trusted publishing means no token secrets are referenced anywhere."""
    text = PUBLISH_WORKFLOW.read_text(encoding="utf-8")
    assert "secrets." not in text
