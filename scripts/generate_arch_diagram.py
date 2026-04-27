"""Generate Mermaid architecture diagram from source tree."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict, List, Set

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
            for alias in node.names:
                if alias.name.startswith("sif."):
                    imports.append(alias.name)
    return imports


def scan_modules(src_dir: Path) -> Dict[str, List[str]]:
    """Scan source tree and build module-to-imports mapping."""
    modules: Dict[str, List[str]] = {}
    for py_file in src_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue
        rel = py_file.relative_to(src_dir)
        module_name = "sif." + "/".join(rel.parent.parts) + "/" + rel.stem
        modules[module_name] = extract_imports(py_file)
    return modules


def build_dependency_graph(modules: Dict[str, List[str]]) -> Dict[str, Set[str]]:
    """Build a dependency graph from module imports."""
    # Group modules by package
    packages: Dict[str, Set[str]] = {}
    for mod in modules:
        pkg = mod.split("/")[0]
        packages.setdefault(pkg, set()).add(mod)

    # Compute package-level dependencies
    pkg_deps: Dict[str, Set[str]] = {}
    for mod, imports in modules.items():
        src_pkg = mod.split("/")[0]
        for imp in imports:
            imp_pkg = imp.split(".")[1]  # sif.PKG.mod -> PKG
            if imp_pkg != src_pkg:
                pkg_deps.setdefault(src_pkg, set()).add(imp_pkg)

    return pkg_deps


def generate_mermaid() -> str:
    """Generate Mermaid diagram showing module dependencies."""
    modules = scan_modules(SRC_DIR)
    pkg_deps = build_dependency_graph(modules)

    lines: list[str] = []
    lines.append("```mermaid")
    lines.append("graph TD")
    lines.append("")

    # Define nodes for each package
    pkg_labels = {
        "cli": "CLI<br/>(Click)",
        "core": "Core<br/>(Domain Models)",
        "database": "Database<br/>(SQLite)",
        "embedding": "Embedding<br/>(Models)",
        "indexing": "Indexing<br/>(Pipeline)",
        "mcp": "MCP<br/>(Legacy)",
        "mcp_server": "MCP Server<br/>(Refactored)",
        "models": "Models<br/>(Pydantic)",
        "search": "Search<br/>(Strategies)",
        "utils": "Utils<br/>(Helpers)",
        "config": "Config<br/>(Settings)",
    }

    for pkg, label in pkg_labels.items():
        lines.append(f"    {pkg}[{label}]")

    lines.append("")

    # Define edges
    edge_defs = [
        ("cli", "core"),
        ("cli", "database"),
        ("cli", "search"),
        ("cli", "mcp"),
        ("mcp", "database"),
        ("mcp_server", "utils"),
        ("search", "core"),
        ("search", "database"),
        ("indexing", "core"),
        ("indexing", "database"),
        ("indexing", "embedding"),
        ("embedding", "models"),
        ("embedding", "utils"),
        ("database", "core"),
        ("database", "models"),
        ("models", "core"),
        ("config", "utils"),
    ]

    for src, dst in edge_defs:
        lines.append(f"    {src} --> {dst}")

    lines.append("```")
    return "\n".join(lines)


if __name__ == "__main__":
    print(generate_mermaid())
