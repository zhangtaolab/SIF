#!/usr/bin/env python3
"""SIF CLI - Main entry point."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from sif import __version__
from sif.config.settings import get_settings
from sif.database.database import Database
from sif.utils.logging import get_logger, setup_logging


logger = get_logger(__name__)
console = Console()

# Default paths
DEFAULT_INDEX_PATH = Path.home() / ".local" / "share" / "sif" / "sif.db"
DEFAULT_CONFIG_PATH = Path.home() / ".config" / "sif"


def _get_default_db_path() -> str:
    """Get default database path from Settings."""
    return str(get_settings().get_db_path())


@click.group()
@click.version_option(version=__version__, prog_name="sif")
@click.option(
    "--index",
    "-i",
    type=click.Path(),
    default=_get_default_db_path,
    help="Path to the index database",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(),
    default=str(DEFAULT_CONFIG_PATH),
    help="Path to the configuration file",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--quiet", "-q", is_flag=True, help="Suppress non-error output")
@click.pass_context
def cli(ctx: click.Context, index: str, config: str, verbose: bool, quiet: bool) -> None:
    """SIF - Search / Index / Find - Local document search engine.

    SIF indexes your documents and enables fast, intelligent search
    using BM25, vector similarity, and hybrid approaches.
    """
    # Setup logging
    log_level = "DEBUG" if verbose else ("WARNING" if quiet else "INFO")
    setup_logging(log_level)

    # Ensure context object exists
    ctx.ensure_object(dict)

    # Store options in context
    ctx.obj["index_path"] = Path(index).expanduser()
    ctx.obj["config_path"] = Path(config).expanduser()
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet

    # Create index directory if needed
    ctx.obj["index_path"].parent.mkdir(parents=True, exist_ok=True)


# Import and register subcommands after cli group to avoid circular imports
from sif.cli.commands.bench import bench_cmd  # noqa: E402
from sif.cli.commands.collection import collection_group  # noqa: E402
from sif.cli.commands.context import context_group  # noqa: E402
from sif.cli.commands.get import get_group  # noqa: E402
from sif.cli.commands.index import index_group  # noqa: E402
from sif.cli.commands.ls import ls_cmd  # noqa: E402
from sif.cli.commands.mcp import mcp_group  # noqa: E402
from sif.cli.commands.pull import pull_cmd  # noqa: E402
from sif.cli.commands.search import search_group  # noqa: E402


cli.add_command(collection_group)
cli.add_command(context_group)
cli.add_command(index_group)
cli.add_command(search_group)
cli.add_command(get_group)
cli.add_command(mcp_group)
cli.add_command(ls_cmd)
cli.add_command(pull_cmd)
cli.add_command(bench_cmd)


@cli.command("status")
@click.pass_context
def status_cmd(ctx: click.Context) -> None:
    """Show index status."""
    ctx.ensure_object(dict)
    index_path = ctx.obj.get("index_path")
    if index_path is None:
        index_path = get_settings().get_db_path()

    if not index_path.exists():
        console.print("[yellow]No index found. Run 'sif update' to create one.[/yellow]")
        return

    try:
        db = Database(index_path)
        db.init_schema()
        stats = db.get_stats()

        table = Table(title="Index Status")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Index Path", str(index_path))
        table.add_row("Collections", str(stats.get("collections", 0)))
        table.add_row("Documents", str(stats.get("documents", 0)))
        table.add_row("Chunks", str(stats.get("chunks", 0)))
        table.add_row("Contexts", str(stats.get("contexts", 0)))

        total_size = stats.get("total_size_bytes", 0)
        if total_size > 0:
            size_mb = total_size / (1024 * 1024)
            table.add_row("Total Size", f"{size_mb:.2f} MB")

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error reading index: {e}[/red]")
        raise click.ClickException(str(e)) from e


@cli.command("cleanup")
@click.confirmation_option(prompt="Are you sure you want to clean up the index?")
@click.pass_context
def cleanup_cmd(ctx: click.Context) -> None:
    """Clean up the index (remove orphaned entries)."""
    index_path = ctx.obj["index_path"]

    if not index_path.exists():
        console.print("[yellow]No index found.[/yellow]")
        return

    try:
        db = Database(index_path)
        db.init_schema()

        with db.transaction() as conn:
            # Clean up orphaned chunks
            cursor = conn.execute("""
                DELETE FROM document_chunks
                WHERE document_id NOT IN (SELECT id FROM documents)
            """)
            chunks_removed = cursor.rowcount

            # Clean up orphaned embeddings
            try:
                cursor = conn.execute("""
                    DELETE FROM document_embeddings
                    WHERE document_id NOT IN (SELECT id FROM documents)
                """)
                embeddings_removed = cursor.rowcount
            except sqlite3.OperationalError:  # noqa: F821
                embeddings_removed = 0

            # Clean up expired LLM cache
            from datetime import datetime, timezone  # noqa: PLC0415

            cursor = conn.execute(
                """
                DELETE FROM llm_cache
                WHERE expires_at IS NOT NULL AND expires_at <= ?
            """,
                (datetime.now(timezone.utc).isoformat(),),
            )
            cache_removed = cursor.rowcount

        console.print("[green]Cleanup complete:[/green]")
        console.print(f"  - Removed {chunks_removed} orphaned chunks")
        console.print(f"  - Removed {embeddings_removed} orphaned embeddings")
        console.print(f"  - Removed {cache_removed} expired cache entries")

    except Exception as e:
        console.print(f"[red]Error during cleanup: {e}[/red]")
        raise click.ClickException(str(e)) from e


def main() -> None:
    """Main entry point."""
    # Migrate old docsift model cache if present
    old_model_dir = Path.home() / ".local" / "share" / "docsift" / "models"
    new_model_dir = Path.home() / ".local" / "share" / "sif" / "models"
    if old_model_dir.exists() and not new_model_dir.exists():
        new_model_dir.parent.mkdir(parents=True, exist_ok=True)
        old_model_dir.rename(new_model_dir)
        console.print("[green]Migrated: ~/.local/share/docsift -> ~/.local/share/sif[/green]")

    cli()


if __name__ == "__main__":
    main()
