#!/usr/bin/env python3
"""SIF CLI - Main entry point."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import click
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from sif import __version__
from sif.config.settings import get_settings
from sif.database.database import Database
from sif.database.repositories import LLMCacheRepository
from sif.search.staleness import embedded_document_ids
from sif.utils import daemon
from sif.utils.logging import get_logger, setup_logging


logger = get_logger(__name__)
console = Console()

# Default paths
DEFAULT_INDEX_PATH = Path.home() / ".local" / "share" / "sif" / "sif.db"
DEFAULT_CONFIG_PATH = Path.home() / ".config" / "sif"


def _get_default_db_path() -> str:
    """Get default database path from Settings.

    Click evaluates this callable on every invocation that omits --index, so
    invalid config must be converted here (REVIEW WR-09) — otherwise the
    Settings validator would escape group-level option parsing as a raw
    pydantic traceback for every command.
    """
    try:
        return str(get_settings().get_db_path())
    except ValidationError as e:
        raise click.ClickException(str(e)) from e


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
from sif.cli.commands.suggest import suggest_cmd  # noqa: E402
from sif.cli.commands.watch import watch_cmd  # noqa: E402


cli.add_command(collection_group)
cli.add_command(context_group)
cli.add_command(index_group)
cli.add_command(search_group)
cli.add_command(get_group)
cli.add_command(mcp_group)
cli.add_command(ls_cmd)
cli.add_command(pull_cmd)
cli.add_command(bench_cmd)
cli.add_command(suggest_cmd)
cli.add_command(watch_cmd)


def _watch_status_text(index_path: Path) -> str:
    """Watch-section value for the status table (D-08).

    Sourced from the daemon PID file payload plus an identity-corroborated
    liveness probe. Foreground watch and MCP hosts are deliberately
    untracked (they own their terminals / are client-spawned and plural) —
    status honestly reports what it knows. A stale or garbage payload
    reports not-running and cleans the file up (metadata only — safe).
    """
    pid_path = daemon.pid_path_for(index_path)
    payload = daemon.read_pid_file(pid_path)
    if payload is None:
        if pid_path.exists():
            daemon.remove_pid_file(pid_path)
            return "not running (stale PID file removed)"
        return "not running"
    if not daemon.corroborate_pid(payload):
        daemon.remove_pid_file(pid_path)
        return "not running (stale PID file removed)"
    return f"running — {payload['mode']} · PID {payload['pid']} · {payload['depth']}"


def _vector_lag_text(conn: sqlite3.Connection) -> str:
    """Vector-lag value for the status table (D-10).

    Same derived signal as the result marker (D-08): a document lags the
    vector index when it has no rows in ``document_embeddings``. ``None``
    (vec0 table missing) renders ``n/a``; an embeddings-free index renders
    the no-vectors state so pure-BM25 users are not nagged. The documents
    scan is iterated one row at a time and the embedded set is read via the
    shared :func:`embedded_document_ids` (one batched scan — the vec0
    batching rule).
    """
    embedded = embedded_document_ids(conn)
    if embedded is None:
        return "n/a"
    if not embedded:
        return "none (no vectors indexed)"
    lagging = 0
    cursor = conn.execute("SELECT id FROM documents")
    for row in cursor:
        if row[0] not in embedded:
            lagging += 1
    if lagging == 1:
        return "1 document"
    return f"{lagging} documents"


@cli.command("status")
@click.pass_context
def status_cmd(ctx: click.Context) -> None:
    """Show index status."""
    ctx.ensure_object(dict)
    index_path = ctx.obj.get("index_path")
    if index_path is None:
        index_path = get_settings().get_db_path()

    if not index_path.exists():
        console.print("[yellow]No index found. Run 'sif index update' to create one.[/yellow]")
        return

    try:
        with Database(index_path) as db:
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

            # Watch section (D-08): one row sourced from the daemon PID file.
            # Metadata display must never take the status command down, so
            # any unexpected failure renders as not-running instead.
            try:
                watch_text = _watch_status_text(Path(index_path))
            except Exception:
                logger.debug("Watch status probe failed", exc_info=True)
                watch_text = "not running"
            table.add_row("Watch", watch_text)

            # Vector lag (D-10): index-level vector lag at a glance, derived
            # from the same embedding scan as the result marker. Same
            # degrade-never-fail contract as the Watch row above.
            try:
                vector_lag_text = _vector_lag_text(db.connection)
            except Exception:
                logger.debug("Vector lag probe failed", exc_info=True)
                vector_lag_text = "n/a"
            table.add_row("Vector lag", vector_lag_text)

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
        with Database(index_path) as db:
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
                except sqlite3.OperationalError:
                    embeddings_removed = 0

                # Clean up expired LLM cache (WR-09: datetime comparison in the repository)
                cache_removed = LLMCacheRepository(conn).clear_expired()

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
