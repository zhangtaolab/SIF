"""Generate Mermaid architecture diagram from source tree."""

from __future__ import annotations

import ast
from pathlib import Path


SRC_DIR = Path("src/sif")


def extract_imports(file_path: Path) -> list[str]:
    """Extract first-party imports from a Python file."""
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return []
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("sif."):
                imports.append(node.module)
        elif isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names if alias.name.startswith("sif."))
    return imports


def scan_modules(src_dir: Path) -> dict[str, list[str]]:
    """Scan source tree and build module-to-imports mapping."""
    modules: dict[str, list[str]] = {}
    for py_file in src_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue
        rel = py_file.relative_to(src_dir)
        module_name = "sif." + "/".join(rel.parent.parts) + "/" + rel.stem
        modules[module_name] = extract_imports(py_file)
    return modules


def package_of_module(module_name: str) -> str:
    """Return the top-level sif package a scanned module belongs to."""
    parts = module_name.split("/", 1)[0].split(".", 2)
    return parts[1] if len(parts) > 1 else ""


def build_dependency_graph(modules: dict[str, list[str]]) -> dict[str, set[str]]:
    """Build a dependency graph from module imports."""
    # Compute package-level dependencies (top-level package under sif on both
    # sides so intra-package imports are filtered and keys match targets)
    pkg_deps: dict[str, set[str]] = {}
    for mod, imports in modules.items():
        src_pkg = package_of_module(mod)
        if not src_pkg:
            continue
        for imp in imports:
            imp_pkg = imp.split(".")[1]  # sif.PKG.mod -> PKG
            if imp_pkg != src_pkg:
                pkg_deps.setdefault(src_pkg, set()).add(imp_pkg)

    return pkg_deps


def generate_mermaid() -> str:
    """Generate Mermaid diagram showing module dependencies."""
    modules = scan_modules(SRC_DIR)
    pkg_deps = build_dependency_graph(modules)

    # Friendly display names; a discovered package without an entry falls back
    # to the bare package name.
    pkg_labels = {
        "cli": "CLI<br/>(Click)",
        "config": "Config<br/>(Settings)",
        "core": "Core<br/>(Domain Models)",
        "database": "Database<br/>(SQLite)",
        "embedding": "Embedding<br/>(Models)",
        "indexing": "Indexing<br/>(Pipeline)",
        "mcp": "MCP<br/>(Server)",
        "models": "Models<br/>(Pydantic)",
        "search": "Search<br/>(Strategies)",
        "utils": "Utils<br/>(Helpers)",
    }

    lines: list[str] = []
    lines.append("```mermaid")
    lines.append("graph TD")
    lines.append("")

    # One node per package present in the computed graph (sources and targets)
    packages = sorted(set(pkg_deps) | {dep for deps in pkg_deps.values() for dep in deps})
    lines.extend(f"    {pkg}[{pkg_labels.get(pkg, pkg)}]" for pkg in packages)

    lines.append("")

    # Edges straight from the computed package dependencies
    lines.extend(
        f"    {src} --> {dst}" for src in sorted(pkg_deps) for dst in sorted(pkg_deps[src])
    )

    lines.append("```")
    return "\n".join(lines)


if __name__ == "__main__":
    print(generate_mermaid())  # noqa: T201
