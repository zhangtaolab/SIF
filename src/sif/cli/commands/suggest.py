"""Query suggestion commands (Phase 15, QUAL-04).

``sif suggest QUERY`` renders three independently ranked sections — prefix
completions, did-you-mean rewrites, and query history — from the one
SuggestionEngine (D-11). ``--json`` mirrors that structure with exactly three
arrays (D-12: no CSV/MD/XML formats), and ``--clear-history`` is the single
history-clearing entry point (D-10), mutually exclusive with QUERY.

Suggestions are display-only: this module never re-executes a suggestion on
the user's behalf (queries are never silently rewritten). Vocab/user-derived
cells are truncated before ``escape()`` (T-15-06) so bracket sequences render
literally. Reads are fail-soft — an engine failure leaves sections empty and
never turns into a command error.
"""

from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from sif.database.database import Database
from sif.database.repositories import QueryLogRepository
from sif.search.suggest import SuggestionEngine
from sif.utils.logging import get_logger, set_quiet


console = Console()
console_err = Console(stderr=True)
logger = get_logger(__name__)

# Truncate before escape(): the cap applies to raw stored/vocab text and the
# escape then keeps bracket sequences literal in the markup-parsed console.
_CELL_MAX_LEN = 80

SECTION_TITLES = ("Prefix completions", "Did you mean", "History")


def _cell(text: str) -> str:
    """Truncate then escape one vocab/user-derived cell (T-15-06)."""
    if len(text) > _CELL_MAX_LEN:
        text = text[: _CELL_MAX_LEN - 3] + "..."
    return escape(text)


def _render_section(title: str, items: list[str]) -> None:
    """Render one labeled, top-N section; an empty section is not an error."""
    console.print(f"[bold]{title}[/bold]")
    table = Table()
    table.add_column("Suggestion", style="cyan")
    if items:
        for item in items:
            table.add_row(_cell(item))
    else:
        table.add_row("[dim](none)[/dim]")
    console.print(table)


def _clear_history(index_path: Path) -> None:
    """Delete every query_log row and confirm after the commit (D-10)."""
    with Database(index_path) as db:
        db.init_schema()
        with db.transaction() as conn:
            removed = QueryLogRepository(conn).clear()
    # Confirmation outside the transaction (context.py precedent): a display
    # failure must not roll back a write that already committed.
    console.print(f"[green]Cleared {removed} query history row(s).[/green]")


def _validate_modes(query: str | None, clear_history: bool) -> None:
    """Reject the two invalid mode combinations before any I/O (D-10)."""
    if clear_history and query is not None:
        raise click.UsageError("QUERY and --clear-history are mutually exclusive")
    if not clear_history and query is None:
        raise click.UsageError("QUERY is required unless --clear-history is used")


def _collect(
    index_path: Path,
    query: str,
    limit: int,
    *,
    quiet: bool,
) -> tuple[list[str], list[str], list[str]]:
    """Read the three sections; an engine failure degrades to empty lists."""
    completions: list[str] = []
    did_you_mean: list[str] = []
    history: list[str] = []
    with Database(index_path) as db:
        db.init_schema()
        try:
            with db.connection:
                engine = SuggestionEngine(db.connection)
                completions = engine.prefix_completions(query, limit)
                did_you_mean = engine.did_you_mean(query)
                history = engine.history_suggestions(query, limit)
        except Exception:
            logger.warning("Suggestion computation failed", exc_info=True)
            if not quiet:
                console_err.print("[yellow]Suggestions unavailable.[/yellow]")
    return completions, did_you_mean, history


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
def suggest_cmd(  # noqa: PLR0913 — Click requires one parameter per option
    ctx: click.Context,
    query: str | None,
    limit: int,
    output_json: bool,
    quiet: bool,
    clear_history: bool,
) -> None:
    """Show prefix completions, did-you-mean rewrites, and query history."""
    index_path = ctx.obj["index_path"]
    quiet = quiet or ctx.obj.get("quiet", False)
    if quiet:
        set_quiet(True)

    _validate_modes(query, clear_history)

    if not index_path.exists():
        console.print("[yellow]No index found.[/yellow]")
        return

    if clear_history:
        _clear_history(index_path)
        return

    if query is None:  # defensive: _validate_modes already raised
        raise click.UsageError("QUERY is required unless --clear-history is used")

    completions, did_you_mean, history = _collect(index_path, query, limit, quiet=quiet)

    if output_json:
        click.echo(
            json.dumps(
                {
                    "completions": completions,
                    "did_you_mean": did_you_mean,
                    "history": history,
                },
                ensure_ascii=False,
            ),
        )
        return

    if quiet:
        return

    _render_section(SECTION_TITLES[0], completions)
    _render_section(SECTION_TITLES[1], did_you_mean)
    _render_section(SECTION_TITLES[2], history)
