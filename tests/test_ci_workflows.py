"""Regression guards for CI-facing packaging and workflow state (Phase 17).

Text-level assertions only: ``uv.lock``, ``pyproject.toml``, and the workflow
files are read as files, so the guards stay dependency-free on every Python in
the CI matrix.
"""

from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = REPO_ROOT / "pyproject.toml"
UV_LOCK = REPO_ROOT / "uv.lock"
DOCS_ROOT = REPO_ROOT / "docs"
INSTALLATION = DOCS_ROOT / "installation.md"
GENERATOR_OWNED_DOCS = {"cli-reference.md", "configuration.md"}
BLACK_DEV_REQUIREMENT = "black>=23.0.0"
CPU_INDEX_URL = "https://download.pytorch.org/whl/cpu"
CPU_TORCH_VERSION = re.compile(r'version = "2\.[0-9]+\.[0-9]+\+cpu"')
CUDA_PACKAGE_LINE = re.compile(r'^name = "(nvidia-[^"]*|triton)"$', re.MULTILINE)
BLACK_PACKAGE_LINE = re.compile(r'^name = "black"$', re.MULTILINE)
BLACK_SECTION = re.compile(r"^\[tool\.black\]", re.MULTILINE)
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
TEST_MATRIX = WORKFLOWS / "test-matrix.yml"
SETUP_UV_SHA = "astral-sh/setup-uv@68559e99cc807c1eb7e9238fd43a15bba460eec2"
PYTHON_VERSION_MATRIX = "python-version: ['3.10', '3.11', '3.12', '3.13']"


def _section(text: str, name: str) -> str:
    """Return the raw TOML text of a table section (Py3.10-safe fallback helper)."""
    header = re.compile(rf"^\[{re.escape(name)}\]\s*$", re.MULTILINE).search(text)
    assert header is not None, f"missing [{name}] section in pyproject.toml"
    start = header.end()
    next_header = re.compile(r"^\[", re.MULTILINE).search(text, start)
    end = next_header.start() if next_header is not None else len(text)
    return text[start:end]


def _extra_block(section: str, name: str) -> str:
    """Return the array body of one optional-dependency extra."""
    pattern = re.compile(rf"^{re.escape(name)}\s*=\s*\[(.*?)^\]", re.DOTALL | re.MULTILINE)
    match = pattern.search(section)
    assert match is not None, f"missing optional-dependencies entry '{name}' in pyproject.toml"
    return match.group(1)


def _pyproject_text() -> str:
    return PYPROJECT.read_text(encoding="utf-8")


def _uv_lock_text() -> str:
    return UV_LOCK.read_text(encoding="utf-8")


def _workflow_text() -> str:
    return TEST_MATRIX.read_text(encoding="utf-8")


def _job_block(text: str, job_id: str) -> str:
    """Return the raw YAML text of one top-level job block."""
    header = re.compile(rf"^  {re.escape(job_id)}:\s*$", re.MULTILINE).search(text)
    assert header is not None, f"missing job '{job_id}' in .github/workflows/test-matrix.yml"
    start = header.end()
    next_job = re.compile(r"^  [A-Za-z0-9_-]+:\s*$", re.MULTILINE).search(text, start)
    end = next_job.start() if next_job is not None else len(text)
    return text[start:end]


def test_lock_has_cpu_torch() -> None:
    """The lock resolves torch from the explicit CPU index with a +cpu tag."""
    text = _uv_lock_text()

    assert CPU_INDEX_URL in text, (
        f"uv.lock does not reference the CPU index {CPU_INDEX_URL!r}; "
        "the torch source did not materialize"
    )
    assert 'name = "torch"' in text, "uv.lock has no torch package entry"

    match = CPU_TORCH_VERSION.search(text)
    assert match is not None, (
        'uv.lock has no CPU-tagged torch version (expected version = "2.x.y+cpu"); '
        "torch lines: " + repr([line for line in text.splitlines() if 'name = "torch"' in line][:4])
    )


def test_lock_has_no_cuda_stack() -> None:
    """No nvidia-* or triton package survives in the lock (CUDA stack removed)."""
    offenders = CUDA_PACKAGE_LINE.findall(_uv_lock_text())

    assert offenders == [], f"uv.lock still carries CUDA-stack packages: {sorted(offenders)}"


def test_lock_has_no_black() -> None:
    """black was dropped from the dev extra, so the lock cannot contain it."""
    offenders = BLACK_PACKAGE_LINE.findall(_uv_lock_text())

    assert offenders == [], f"uv.lock still carries black package entries: {len(offenders)}"


def test_pyproject_cpu_index_is_explicit() -> None:
    """The CPU index is explicit and the torch source is marker-scoped to Linux."""
    text = _pyproject_text()

    required = [
        'name = "pytorch-cpu"',
        f'url = "{CPU_INDEX_URL}"',
        "explicit = true",
        "marker = \"sys_platform == 'linux'\"",
    ]
    missing = [item for item in required if item not in text]

    assert missing == [], f"pyproject.toml is missing the CPU-torch packaging contract: {missing}"


def test_pyproject_extras_floors() -> None:
    """embed/all carry the research-locked floors and a direct torch declaration."""
    text = _pyproject_text()
    section = _section(text, "project.optional-dependencies")
    embed = _extra_block(section, "embed")
    all_block = _extra_block(section, "all")
    dev = _extra_block(section, "dev")

    for extra_name, block in (("embed", embed), ("all", all_block)):
        assert '"sentence-transformers>=5.4.1"' in block, (
            f"[{extra_name}] is missing the sentence-transformers>=5.4.1 floor; block: {block!r}"
        )
        assert re.search(r'^\s*"torch",\s*$', block, re.MULTILINE) is not None, (
            f"[{extra_name}] is missing a direct torch entry; block: {block!r}"
        )

    assert '"llama-cpp-python>=0.3.35"' in all_block, (
        f"[all] is missing the llama-cpp-python>=0.3.35 floor; block: {all_block!r}"
    )
    assert "black" not in dev, f"[dev] still advertises black; block: {dev!r}"


def test_core_deps_keep_fastapi_uvicorn() -> None:
    """fastapi and uvicorn stay core dependencies, not extras (D-11)."""
    project = _section(_pyproject_text(), "project")
    dependencies = _extra_block(project, "dependencies")
    names = re.findall(r'"([A-Za-z0-9_.-]+)', dependencies)

    for name in ("fastapi", "uvicorn"):
        assert name in names, f"missing core dependency {name!r}; dependencies = {names}"


def test_pyproject_has_no_black_section() -> None:
    """The [tool.black] table was deleted with the dependency (ENG-04)."""
    match = BLACK_SECTION.search(_pyproject_text())

    assert match is None, (
        f"pyproject.toml still starts a [tool.black] table at offset {match.start()}"
    )


def test_installation_docs_match_extras() -> None:
    """Installation docs carry the new floors and no dev black requirement."""
    text = INSTALLATION.read_text(encoding="utf-8")

    for required in ("sentence-transformers>=5.4.1", "torch"):
        assert required in text, f"docs/installation.md is missing {required!r}"
    assert BLACK_DEV_REQUIREMENT not in text, (
        f"docs/installation.md still lists the removed dev requirement {BLACK_DEV_REQUIREMENT!r}"
    )

    offenders: list[str] = []
    for doc in sorted(DOCS_ROOT.rglob("*.md")):
        if doc.name in GENERATOR_OWNED_DOCS:
            continue
        lines = doc.read_text(encoding="utf-8").splitlines()
        for lineno, line in enumerate(lines, start=1):
            if BLACK_DEV_REQUIREMENT in line:
                offenders.append(f"{doc.relative_to(REPO_ROOT)}:{lineno}: {line.strip()}")

    assert offenders == [], f"docs still advertise {BLACK_DEV_REQUIREMENT!r}: {offenders}"


def test_matrix_declares_eight_cells() -> None:
    """The matrix is a fixed literal 4 Python versions x 2 operating systems."""
    text = _workflow_text()

    missing = [
        value
        for value in ("'3.10'", "'3.11'", "'3.12'", "'3.13'", "ubuntu-latest", "macos-latest")
        if value not in text
    ]
    assert missing == [], f"test-matrix.yml is missing matrix cells {missing}; text: {text!r}"
    assert "fail-fast: false" in text, (
        "test-matrix.yml must disable fail-fast so every cell reports"
    )
    assert "cancel-in-progress: true" in text, (
        "test-matrix.yml must cancel superseded runs per ref; text: " + repr(text)
    )
    count = text.count(PYTHON_VERSION_MATRIX)
    assert count == 1, (
        "test-matrix.yml must declare the contiguous python-version list exactly once; "
        f"found {count}: {PYTHON_VERSION_MATRIX!r}"
    )


def test_matrix_runs_full_suite_with_coverage() -> None:
    """Each cell syncs the frozen lock and runs bare pytest so fail_under=90 applies."""
    text = _workflow_text()

    assert "uv sync --frozen --extra dev --extra embed" in text, (
        "test-matrix.yml must sync the frozen lock with the dev and embed extras"
    )
    assert "uv run --frozen pytest" in text, (
        "test-matrix.yml must run the full suite through the frozen environment"
    )
    for forbidden in ("--no-cov", "-p no:"):
        assert forbidden not in text, (
            f"test-matrix.yml must not disable coverage with {forbidden!r}; text: {text!r}"
        )


def test_matrix_has_least_privilege() -> None:
    """PR-triggered jobs get read-only contents and no secret or OIDC surface."""
    text = _workflow_text()

    assert "permissions:" in text, "test-matrix.yml must declare workflow permissions"
    assert "contents: read" in text, "test-matrix.yml must grant only contents: read"
    for forbidden in ("pull_request_target", "secrets.", "id-token"):
        assert forbidden not in text, (
            f"test-matrix.yml must not contain {forbidden!r}; text: {text!r}"
        )


def test_setup_uv_is_sha_pinned() -> None:
    """The third-party uv action is pinned to the verified commit SHA."""
    text = _workflow_text()

    assert SETUP_UV_SHA in text, f"test-matrix.yml is missing the pinned action {SETUP_UV_SHA!r}"
    floating = re.findall(r"astral-sh/setup-uv@v[0-9][^\s]*", text)
    assert floating == [], (
        f"test-matrix.yml uses a floating setup-uv ref {floating}; pin the commit SHA instead"
    )


def test_matrix_excludes_tag_pushes() -> None:
    """Only branch pushes and pull requests trigger the matrix; tags never do."""
    text = _workflow_text()

    assert re.search(r"^  push:\n    branches:", text, re.MULTILINE) is not None, (
        "test-matrix.yml push trigger must declare branches:; text: " + repr(text)
    )
    assert "tags:" not in text, (
        "test-matrix.yml must not trigger on tags (the release workflow owns v* tags)"
    )
