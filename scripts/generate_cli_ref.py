#!/usr/bin/env python3
"""Generate CLI reference documentation from Click introspection."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import click


# Ensure docsift is importable
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from docsift.cli.main import cli  # noqa: E402


def _is_sentinel(value: Any) -> bool:
    """Check if a value is a Click sentinel (internal default marker)."""
    return type(value).__name__ == "Sentinel"


def _format_default(value: Any) -> str | None:
    """Format a default value for display, skipping sentinels and callables."""
    if _is_sentinel(value):
        return None
    if value is None:
        return None
    if callable(value):
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)) and not value:
        return None
    return str(value)


def _format_type(param: click.Parameter) -> str:
    """Format the type of a parameter for display."""
    if param.is_flag:
        return "flag"
    if param.multiple:
        return f"{param.type.name}[]"
    return param.type.name


def traverse_commands(
    cmd: click.Command, path: str = "",
) -> list[tuple[str, click.Command]]:
    """Recursively traverse the Click command tree."""
    results: list[tuple[str, click.Command]] = []
    if isinstance(cmd, click.Group):
        for name, subcmd in cmd.commands.items():
            new_path = f"{path} {name}".strip()
            results.extend(traverse_commands(subcmd, new_path))
    else:
        results.append((path, cmd))
    return results


def _build_tree_lines(cmd: click.Command, prefix: str = "") -> list[str]:
    """Build ASCII tree lines for command overview."""
    tree_lines: list[str] = []
    if isinstance(cmd, click.Group):
        items = list(cmd.commands.items())
        for i, (name, subcmd) in enumerate(items):
            is_last = i == len(items) - 1
            connector = "└──" if is_last else "├──"
            tree_lines.append(
                f"{prefix}{connector} {name:<15} {subcmd.help or ''}"
            )
            if isinstance(subcmd, click.Group):
                extension = "    " if is_last else "│   "
                tree_lines.extend(_build_tree_lines(subcmd, prefix + extension))
    return tree_lines


def _format_command_section(path: str, cmd: click.Command) -> list[str]:
    """Format a single command section as markdown lines."""
    section: list[str] = []
    section.append(f"### `{path}`")
    section.append("")
    if cmd.help:
        section.append(cmd.help)
        section.append("")

    section.append(f"```bash\ndocsift {path} [OPTIONS]\n```")
    section.append("")

    args = [p for p in cmd.params if isinstance(p, click.Argument)]
    if args:
        section.append("**Arguments:**")
        section.append("")
        section.append("| Argument | Type | Required | Description |")
        section.append("|----------|------|----------|-------------|")
        for arg in args:
            required = "Yes" if arg.required else "No"
            help_text = getattr(arg, "help", "") or ""
            section.append(
                f"| `{arg.name}` | {arg.type.name} | {required} | {help_text} |"
            )
        section.append("")

    opts = [p for p in cmd.params if isinstance(p, click.Option)]
    if opts:
        section.append("**Options:**")
        section.append("")
        section.append("| Option | Short | Type | Default | Description |")
        section.append("|--------|-------|------|---------|-------------|")
        for opt in opts:
            long_opt = next(
                (o for o in opt.opts if o.startswith("--")), opt.opts[0]
            )
            short_opt = next(
                (o for o in opt.opts if not o.startswith("--")), "—"
            )
            ptype = _format_type(opt)
            default = _format_default(opt.default)
            default_str = f"`{default}`" if default else "—"
            help_text = opt.help or ""
            section.append(
                f"| `{long_opt}` | `{short_opt}` | {ptype} | "
                f"{default_str} | {help_text} |"
            )
        section.append("")

    return section


def generate_cli_reference() -> str:
    """Generate markdown CLI reference from Click introspection."""
    lines: list[str] = []

    lines.append("# CLI Reference")
    lines.append("")
    lines.append("Complete reference for all DocSift CLI commands.")
    lines.append("")

    # Global options
    lines.append("## Global Options")
    lines.append("")
    lines.append("These options can be used with any command:")
    lines.append("")
    lines.append("| Option | Short | Type | Default | Description |")
    lines.append("|--------|-------|------|---------|-------------|")

    for param in cli.params:
        if isinstance(param, click.Option):
            long = ", ".join(o for o in param.opts if o.startswith("--"))
            short = ", ".join(o for o in param.opts if not o.startswith("--"))
            ptype = _format_type(param)
            default = _format_default(param.default)
            default_str = f"`{default}`" if default else "—"
            lines.append(
                f"| `{long}` | `{short}` | {ptype} | "
                f"{default_str} | {param.help or ''} |"
            )

    lines.append("")

    # Command overview tree
    lines.append("## Command Overview")
    lines.append("")
    lines.append("```")
    lines.append("docsift")
    lines.extend(_build_tree_lines(cli))
    lines.append("```")
    lines.append("")

    # Collect all leaf commands
    all_commands = traverse_commands(cli)

    # Group by top-level command (first word of path)
    groups: dict[str, list[tuple[str, click.Command]]] = {}
    for path, cmd in all_commands:
        top = path.split()[0]
        groups.setdefault(top, []).append((path, cmd))

    # Define group order and names
    group_order = [
        ("collection", "Collection Commands"),
        ("context", "Context Commands"),
        ("get", "Get Commands"),
        ("index", "Index Commands"),
        ("search", "Search Commands"),
        ("mcp", "MCP Commands"),
        ("bench", "Other Commands"),
        ("pull", "Other Commands"),
        ("ls", "Other Commands"),
        ("status", "Other Commands"),
        ("cleanup", "Other Commands"),
    ]

    other_commands: list[tuple[str, click.Command]] = []

    for group_key, group_title in group_order:
        if group_key not in groups:
            continue

        if group_title == "Other Commands":
            other_commands.extend(groups[group_key])
        else:
            lines.append(f"## {group_title}")
            lines.append("")
            for path, cmd in sorted(groups[group_key], key=lambda x: x[0]):
                lines.extend(_format_command_section(path, cmd))

        del groups[group_key]

    # Handle any remaining groups
    for _group_key, cmds in sorted(groups.items()):
        other_commands.extend(cmds)

    if other_commands:
        lines.append("## Other Commands")
        lines.append("")
        for path, cmd in sorted(other_commands, key=lambda x: x[0]):
            lines.extend(_format_command_section(path, cmd))

    # Output formats section
    lines.append("## Output Formats")
    lines.append("")
    lines.append("Several commands support multiple output formats via flags:")
    lines.append("")
    lines.append("| Format | Flag | Description |")
    lines.append("|--------|------|-------------|")
    lines.append("| Table (default) | — | Rich formatted table |")
    lines.append("| JSON | `--json` | Machine-readable JSON |")
    lines.append("| CSV | `--csv` | Comma-separated values |")
    lines.append("| Markdown | `--md` | Markdown table format |")
    lines.append("| XML | `--xml` | XML format |")
    lines.append("| Files | `--files` | Plain file paths, one per line |")
    lines.append("")

    # Exit codes
    lines.append("## Exit Codes")
    lines.append("")
    lines.append("| Code | Meaning |")
    lines.append("|------|---------|")
    lines.append("| 0 | Success |")
    lines.append("| 1 | General error |")
    lines.append("| 2 | Invalid arguments |")
    lines.append("")

    # Common workflows
    lines.append("## Common Workflows")
    lines.append("")

    lines.append("**Setting up a new collection:**")
    lines.append("```bash")
    lines.append("# Add a collection")
    lines.append(
        'docsift collection add ~/Documents/notes '
        '--name my-notes --description "Personal notes"'
    )
    lines.append("")
    lines.append("# Update index")
    lines.append("docsift index update my-notes")
    lines.append("")
    lines.append("# Search")
    lines.append('docsift search "python tips"')
    lines.append("```")
    lines.append("")

    lines.append("**Managing collection visibility:**")
    lines.append("```bash")
    lines.append("# Exclude from default searches")
    lines.append("docsift collection exclude my-notes")
    lines.append("")
    lines.append("# Include again")
    lines.append("docsift collection include my-notes")
    lines.append("")
    lines.append("# Set pre-update command")
    lines.append('docsift collection update-cmd my-notes --cmd "git pull"')
    lines.append("```")
    lines.append("")

    lines.append("**Adding context:**")
    lines.append("```bash")
    lines.append("# Add global context")
    lines.append(
        'docsift context add global global "I am a software engineer."'
    )
    lines.append("")
    lines.append("# Add collection context")
    lines.append(
        'docsift context add collection my-notes '
        '"These are my programming notes."'
    )
    lines.append("")
    lines.append("# List contexts")
    lines.append("docsift context list")
    lines.append("")
    lines.append("# Prune orphaned contexts")
    lines.append("docsift context prune")
    lines.append("```")
    lines.append("")

    lines.append("**Hybrid search with options:**")
    lines.append("```bash")
    lines.append(
        'docsift search query "python decorators" '
        "--explain --candidate-limit 30 --limit 10"
    )
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    """Generate and write CLI reference to docs/cli-reference.md."""
    output_path = project_root / "docs" / "cli-reference.md"
    content = generate_cli_reference()
    output_path.write_text(content, encoding="utf-8")
    print(f"Generated CLI reference: {output_path}")  # noqa: T201


if __name__ == "__main__":
    main()
