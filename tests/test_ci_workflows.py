"""Regression guards for CI-facing packaging and workflow state (Phase 17).

Text-level assertions only: ``uv.lock`` and ``pyproject.toml`` are read as
files, so the guards stay dependency-free on every Python in the CI matrix.
The CI matrix workflow guards land with plan 17-03; this module owns the
lock/packaging half.
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
