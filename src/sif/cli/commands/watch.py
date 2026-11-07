"""The ``sif watch`` foreground command (Phase 12 MVP host)."""

from __future__ import annotations

import click
from rich.console import Console


console = Console()


@click.command("watch")
@click.pass_context
def watch_cmd(ctx: click.Context) -> None:
    """Watch collections and keep the index current as files change."""
    console.print(
        f"[yellow]watch skeleton: pipeline lands later in this plan "
        f"(index: {ctx.obj.get('index_path')})[/yellow]"
    )
