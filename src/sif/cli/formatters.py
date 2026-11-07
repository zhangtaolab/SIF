"""Output formatters for SIF CLI."""

from typing import Any


def prepend_line_numbers(content: str) -> str:
    """Prepend line numbers to each line of content."""
    return "\n".join(f"{i + 1:4d}: {line}" for i, line in enumerate(content.split("\n")))


def add_line_numbers_to_results(
    results: list[dict[str, Any]],
    content_key: str = "content",
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
