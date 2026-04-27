"""Context management commands."""

from __future__ import annotations

from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from sif.core.models import PathContext
from sif.database.database import Database
from sif.database.repositories import CollectionRepository, ContextRepository


console = Console()


@click.group("context")
def context_group() -> None:
    """Manage contextual descriptions for paths, collections, and global scope."""
    pass


@context_group.command("add")
@click.argument("type", type=click.Choice(["path", "collection", "global"]))
@click.argument("target")
@click.argument("content")
@click.pass_context
def context_add(
    ctx: click.Context,
    type: str,
    target: str,
    content: str,
) -> None:
    """Add context for a path, collection, or global scope."""
    index_path = ctx.obj["index_path"]
    db = Database(index_path)
    db.init_schema()

    with db.transaction() as conn:
        repo = ContextRepository(conn)

        # Resolve target based on type
        actual_target = target
        if type == "collection":
            coll_repo = CollectionRepository(conn)
            coll = coll_repo.get_by_name(target)
            if not coll:
                # Fallback: treat target as collection ID
                coll = coll_repo.get_by_id(target)
            if not coll:
                raise click.ClickException(f"Collection '{target}' not found")
            actual_target = coll.id
        elif type == "global":
            actual_target = "global"
        # For path type, actual_target = target (the path string)

        # Upsert: update if exists for this target+type, else create
        existing = repo.get_by_target(actual_target, type)
        if existing:
            existing.context = content
            repo.update(existing)
            console.print(f"[green]Context updated for {type} '{target}'[/green]")
        else:
            path_context = PathContext(
                path=actual_target,
                context=content,
                context_type=type,
            )
            repo.create(path_context)
            console.print(f"[green]Context added for {type} '{target}'[/green]")


@context_group.command("remove")
@click.argument("context_id")
@click.pass_context
def context_remove(ctx: click.Context, context_id: str) -> None:
    """Remove a context by its ID."""
    index_path = ctx.obj["index_path"]
    db = Database(index_path)
    db.init_schema()

    with db.transaction() as conn:
        repo = ContextRepository(conn)
        deleted = repo.delete(context_id)
        if not deleted:
            raise click.ClickException(f"No context found with ID '{context_id}'")

    console.print(f"[green]Context '{context_id}' removed[/green]")


@context_group.command("list")
@click.option(
    "--type",
    "context_type",
    type=click.Choice(["path", "collection", "global"]),
    help="Filter by context type",
)
@click.pass_context
def context_list(ctx: click.Context, context_type: Optional[str]) -> None:
    """List all contexts."""
    index_path = ctx.obj["index_path"]

    if not index_path.exists():
        console.print("[yellow]No index found.[/yellow]")
        return

    db = Database(index_path)
    db.init_schema()

    with db.connection:
        repo = ContextRepository(db.connection)
        if context_type:
            contexts = repo.list_by_type(context_type)
        else:
            contexts = repo.list_all()

    if not contexts:
        console.print("[yellow]No contexts found.[/yellow]")
        return

    table = Table(title="Contexts")
    table.add_column("Type", style="magenta")
    table.add_column("Target", style="cyan")
    table.add_column("Content", style="green")

    for ctx_item in contexts:
        # Truncate long contexts for display
        content_text = ctx_item.context
        if len(content_text) > 50:
            content_text = content_text[:47] + "..."
        table.add_row(ctx_item.context_type, ctx_item.path, content_text)

    console.print(table)


@context_group.command("prune")
@click.pass_context
def context_prune(ctx: click.Context) -> None:
    """Remove orphaned path contexts (whose target paths no longer exist in the index)."""
    index_path = ctx.obj["index_path"]

    if not index_path.exists():
        console.print("[yellow]No index found.[/yellow]")
        return

    db = Database(index_path)
    db.init_schema()

    with db.transaction() as conn:
        repo = ContextRepository(conn)
        count = repo.delete_orphaned_paths()

    console.print(f"[green]Pruned {count} orphaned path context(s).[/green]")


# Register 'rm' as an alias for 'remove'
context_group.add_command(context_remove, name="rm")
