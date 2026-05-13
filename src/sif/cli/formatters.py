"""Output formatters for SIF CLI."""

import csv
import io
import json
from dataclasses import asdict, is_dataclass
from typing import Any, Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.tree import Tree


# Global console instance
console = Console()


def format_json(data: Any, indent: int = 2) -> str:
    """Format data as JSON string."""

    def serialize(obj: Any) -> Any:
        if is_dataclass(obj):
            return asdict(obj)
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return str(obj)

    return json.dumps(data, indent=indent, default=serialize, ensure_ascii=False)


def format_csv(data: list[dict[str, Any]]) -> str:
    """Format list of dictionaries as CSV string."""
    if not data:
        return ""

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()


def format_markdown_table(data: list[dict[str, Any]], title: Optional[str] = None) -> str:
    """Format list of dictionaries as Markdown table."""
    if not data:
        return ""

    lines = []
    if title:
        lines.append(f"## {title}\n")

    # Header
    headers = list(data[0].keys())
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    # Rows
    for row in data:
        values = [str(row.get(h, "")) for h in headers]
        lines.append("| " + " | ".join(values) + " |")

    return "\n".join(lines)


def format_xml(data: Any, root_tag: str = "root") -> str:
    """Format data as XML string."""

    def to_xml(obj: Any, tag: str) -> str:
        if isinstance(obj, dict):
            children = "\n".join(to_xml(v, k) for k, v in obj.items())
            return f"<{tag}>\n{children}\n</{tag}>"
        if isinstance(obj, list):
            children = "\n".join(to_xml(item, "item") for item in obj)
            return f"<{tag}>\n{children}\n</{tag}>"
        return f"<{tag}>{obj}</{tag}>"

    return f'<?xml version="1.0" encoding="UTF-8"?>\n{to_xml(data, root_tag)}'


def format_files_list(paths: list[str]) -> str:
    """Format list of file paths."""
    return "\n".join(paths)


def print_json(data: Any, console: Optional[Console] = None) -> None:
    """Print data as formatted JSON."""
    cons = console or Console()
    json_str = format_json(data)
    syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)
    cons.print(syntax)


def print_csv(data: list[dict[str, Any]], console: Optional[Console] = None) -> None:
    """Print data as CSV."""
    cons = console or Console()
    cons.print(format_csv(data))


def print_markdown(
    data: list[dict[str, Any]], title: Optional[str] = None, console: Optional[Console] = None
) -> None:
    """Print data as Markdown table."""
    cons = console or Console()
    cons.print(format_markdown_table(data, title))


def print_xml(data: Any, root_tag: str = "root", console: Optional[Console] = None) -> None:
    """Print data as XML."""
    cons = console or Console()
    xml_str = format_xml(data, root_tag)
    syntax = Syntax(xml_str, "xml", theme="monokai", line_numbers=False)
    cons.print(syntax)


def print_files(paths: list[str], console: Optional[Console] = None) -> None:
    """Print list of files."""
    cons = console or Console()
    for path in paths:
        cons.print(path)


def print_table(
    data: list[dict[str, Any]], title: Optional[str] = None, console: Optional[Console] = None
) -> None:
    """Print data as a rich table."""
    cons = console or Console()

    if not data:
        cons.print("[yellow]No data to display[/yellow]")
        return

    table = Table(title=title, box=box.ROUNDED)

    # Add columns
    for key in data[0]:
        table.add_column(str(key), overflow="fold")

    # Add rows
    for row in data:
        values = [str(row.get(k, "")) for k in data[0]]
        table.add_row(*values)

    cons.print(table)


def print_success(message: str, console: Optional[Console] = None) -> None:
    """Print a success message."""
    cons = console or Console()
    cons.print(f"[green]✓[/green] {message}")


def print_error(message: str, console: Optional[Console] = None) -> None:
    """Print an error message."""
    cons = console or Console()
    cons.print(f"[red]✗[/red] {message}")


def print_warning(message: str, console: Optional[Console] = None) -> None:
    """Print a warning message."""
    cons = console or Console()
    cons.print(f"[yellow]⚠[/yellow] {message}")


def print_info(message: str, console: Optional[Console] = None) -> None:
    """Print an info message."""
    cons = console or Console()
    cons.print(f"[blue]ℹ[/blue] {message}")


def print_panel(
    content: str,
    title: Optional[str] = None,
    border_style: str = "blue",
    console: Optional[Console] = None,
) -> None:
    """Print content in a panel."""
    cons = console or Console()
    panel = Panel(content, title=title, border_style=border_style)
    cons.print(panel)


def print_tree(
    data: dict[str, Any], title: str = "Tree", console: Optional[Console] = None
) -> None:
    """Print data as a tree structure."""
    cons = console or Console()
    tree = Tree(f"[bold]{title}[/bold]")

    def add_branch(node: Tree, obj: Any) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                branch = node.add(f"[cyan]{key}[/cyan]")
                add_branch(branch, value)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                branch = node.add(f"[dim][{i}][/dim]")
                add_branch(branch, item)
        else:
            node.add(str(obj))

    add_branch(tree, data)
    cons.print(tree)


def prepend_line_numbers(content: str) -> str:
    """Prepend line numbers to each line of content."""
    return "\n".join(f"{i + 1:4d}: {line}" for i, line in enumerate(content.split("\n")))


def add_line_numbers_to_results(
    results: list[dict[str, Any]], content_key: str = "content"
) -> list[dict[str, Any]]:
    """Add a 'line_numbers' field to each result dict based on content."""
    formatted = []
    for item in results:
        row = dict(item)
        content = row.get(content_key, "")
        if content:
            row["line_numbers"] = "\n".join(f"{i + 1}" for i in range(len(content.split("\n"))))
        else:
            row["line_numbers"] = ""
        formatted.append(row)
    return formatted


class OutputFormatter:
    """Handles output formatting based on format option."""

    FORMATS = ["table", "json", "csv", "md", "xml", "files"]

    def __init__(self, format_type: str = "table", console: Optional[Console] = None):
        """Initialize the output formatter."""
        self.format_type = format_type
        self.console = console or Console()

    def print(self, data: Any, title: Optional[str] = None) -> None:  # noqa: PLR0912
        """Print data in the specified format."""
        if self.format_type == "json":
            print_json(data, self.console)
        elif self.format_type == "csv":
            if isinstance(data, list) and data and isinstance(data[0], dict):
                print_csv(data, self.console)
            else:
                print_json(data, self.console)
        elif self.format_type == "md":
            if isinstance(data, list) and data and isinstance(data[0], dict):
                print_markdown(data, title, self.console)
            else:
                print_json(data, self.console)
        elif self.format_type == "xml":
            print_xml(data, title or "root", self.console)
        elif self.format_type == "files":
            if isinstance(data, list):
                print_files(data, self.console)
            else:
                print_json(data, self.console)
        elif isinstance(data, list) and data and isinstance(data[0], dict):
            print_table(data, title, self.console)
        else:
            print_json(data, self.console)


def get_formatter(format_type: str = "table", console: Optional[Console] = None) -> OutputFormatter:
    """Get an output formatter instance."""
    return OutputFormatter(format_type, console)
