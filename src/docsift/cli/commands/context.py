"""Context management commands."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from docsift.core.models import PathContext
from docsift.database.database import Database
from docsift.database.repositories import PathContextRepository

console = Console()


@click.group("context")
def context_group() -> None:
    """Manage path contexts."""
    pass


@context_group.command("add")
@click.argument("path")
@click.argument("context_text")
@click.option("--collection", "-c", help="Associate with a collection")
@click.pass_context
def context_add(
    ctx: click.Context,
    path: str,
    context_text: str,
    collection: Optional[str],
) -> None:
    """Add context for a path."""
    index_path = ctx.obj["index_path"]
    
    db = Database(index_path)
    db.init_schema()
    
    with db.transaction() as conn:
        repo = PathContextRepository(conn)
        
        # Get collection ID if specified
        collection_id = None
        if collection:
            from docsift.database.repositories import CollectionRepository
            coll_repo = CollectionRepository(conn)
            coll = coll_repo.get_by_name(collection)
            if not coll:
                raise click.ClickException(f"Collection '{collection}' not found")
            collection_id = coll.id
        
        # Check if context already exists
        existing = repo.get_by_path(path)
        if existing:
            # Update existing
            existing.context = context_text
            repo.update(existing)
            console.print(f"[green]Context updated for '{path}'[/green]")
        else:
            # Create new
            path_context = PathContext(
                path=path,
                context=context_text,
                collection_id=collection_id,
            )
            repo.create(path_context)
            console.print(f"[green]Context added for '{path}'[/green]")


@context_group.command("remove")
@click.argument("path")
@click.pass_context
def context_remove(ctx: click.Context, path: str) -> None:
    """Remove context for a path."""
    index_path = ctx.obj["index_path"]
    
    db = Database(index_path)
    db.init_schema()
    
    with db.transaction() as conn:
        repo = PathContextRepository(conn)
        
        existing = repo.get_by_path(path)
        if not existing:
            raise click.ClickException(f"No context found for '{path}'")
        
        repo.delete(existing.id)
    
    console.print(f"[green]Context removed for '{path}'[/green]")


@context_group.command("list")
@click.option("--collection", "-c", help="Filter by collection")
@click.pass_context
def context_list(ctx: click.Context, collection: Optional[str]) -> None:
    """List all path contexts."""
    index_path = ctx.obj["index_path"]
    
    if not index_path.exists():
        console.print("[yellow]No index found.[/yellow]")
        return
    
    db = Database(index_path)
    db.init_schema()
    
    with db.connection:
        repo = PathContextRepository(db.connection)
        
        if collection:
            from docsift.database.repositories import CollectionRepository
            coll_repo = CollectionRepository(db.connection)
            coll = coll_repo.get_by_name(collection)
            if not coll:
                raise click.ClickException(f"Collection '{collection}' not found")
            contexts = repo.list_by_collection(coll.id)
        else:
            contexts = repo.list_all()
    
    if not contexts:
        console.print("[yellow]No contexts found.[/yellow]")
        return
    
    table = Table(title="Path Contexts")
    table.add_column("Path", style="cyan")
    table.add_column("Context", style="green")
    
    for ctx_item in contexts:
        # Truncate long contexts
        context_text = ctx_item.context
        if len(context_text) > 50:
            context_text = context_text[:47] + "..."
        table.add_row(ctx_item.path, context_text)
    
    console.print(table)
