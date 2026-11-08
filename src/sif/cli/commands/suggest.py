"""Query suggestion commands (Phase 15, QUAL-04).

``sif suggest QUERY`` renders three independently ranked sections — prefix
completions, did-you-mean rewrites, and query history — from the one
SuggestionEngine (D-11). ``--json`` mirrors that structure with exactly three
arrays (D-12: no CSV/MD/XML formats), and ``--clear-history`` is the single
history-clearing entry point (D-10), mutually exclusive with QUERY.
"""

from __future__ import annotations

import click


@click.command("suggest")
@click.argument("query", required=False)
@click.option(
    "--limit",
    type=click.IntRange(1, 50),
    default=5,
    show_default=True,
    help="Maximum entries per section",
)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("-q", "--quiet", is_flag=True, help="Suppress table output")
@click.option("--clear-history", is_flag=True, help="Delete all recorded query history")
@click.pass_context
def suggest_cmd(
    ctx: click.Context,  # noqa: ARG001
    query: str | None,  # noqa: ARG001
    limit: int,  # noqa: ARG001
    output_json: bool,  # noqa: ARG001
    quiet: bool,  # noqa: ARG001
    clear_history: bool,  # noqa: ARG001
) -> None:
    """Show prefix completions, did-you-mean rewrites, and query history."""
