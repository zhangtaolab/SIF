"""Collection management commands."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from sif.core.models import Collection
from sif.database.database import Database
from sif.database.repositories import CollectionRepository


console = Console()


@click.group("collection")
def collection_group() -> None:
    """Manage document collections."""
    pass


@collection_group.command("add")
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--name", "-n", required=True, help="Collection name")
@click.option("--pattern", "-p", default="**/*.md", help="File pattern to match")
@click.option("--ignore", "-i", multiple=True, help="Patterns to ignore")
@click.option("--description", "-d", help="Collection description")
@click.option("--no-default", is_flag=True, help="Don't include in default searches")
@click.pass_context
def collection_add(
    ctx: click.Context,
    path: str,
    name: str,
    pattern: str,
    ignore: tuple,
    description: Optional[str],
    no_default: bool,
) -> None:
    """Add a new collection."""
    index_path = ctx.obj["index_path"]

    db = Database(index_path)
    db.init_schema()

    with db.transaction() as conn:
        repo = CollectionRepository(conn)

        # Check if collection already exists
        if repo.exists(name):
            raise click.ClickException(f"Collection '{name}' already exists")

        # Create collection
        collection = Collection(
            name=name,
            path=str(Path(path).resolve()),
            pattern=pattern,
            ignore_patterns=list(ignore),
            include_by_default=not no_default,
            description=description,
        )

        repo.create(collection)

    console.print(f"[green]Collection '{name}' added successfully[/green]")


@collection_group.command("remove")
@click.argument("name")
@click.confirmation_option(prompt="Are you sure you want to remove this collection?")
@click.pass_context
def collection_remove(ctx: click.Context, name: str) -> None:
    """Remove a collection."""
    index_path = ctx.obj["index_path"]

    db = Database(index_path)
    db.init_schema()

    with db.transaction() as conn:
        repo = CollectionRepository(conn)

        collection = repo.get_by_name(name)
        if not collection:
            raise click.ClickException(f"Collection '{name}' not found")

        # Delete documents first (cascade will handle chunks)
        from sif.database.repositories import DocumentRepository

        doc_repo = DocumentRepository(conn)
        doc_repo.delete_by_collection(collection.id)

        # Delete collection
        repo.delete(collection.id)

    console.print(f"[green]Collection '{name}' removed[/green]")


@collection_group.command("rename")
@click.argument("old_name")
@click.argument("new_name")
@click.pass_context
def collection_rename(ctx: click.Context, old_name: str, new_name: str) -> None:
    """Rename a collection."""
    index_path = ctx.obj["index_path"]

    db = Database(index_path)
    db.init_schema()

    with db.transaction() as conn:
        repo = CollectionRepository(conn)

        collection = repo.get_by_name(old_name)
        if not collection:
            raise click.ClickException(f"Collection '{old_name}' not found")

        # Check if new name already exists
        if repo.exists(new_name):
            raise click.ClickException(f"Collection '{new_name}' already exists")

        collection.name = new_name
        repo.update(collection)

    console.print(f"[green]Collection renamed from '{old_name}' to '{new_name}'[/green]")


@collection_group.command("list")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
@click.pass_context
def collection_list(ctx: click.Context, verbose: bool) -> None:
    """List all collections."""
    index_path = ctx.obj["index_path"]

    if not index_path.exists():
        console.print("[yellow]No index found.[/yellow]")
        return

    db = Database(index_path)
    db.init_schema()

    with db.connection:
        repo = CollectionRepository(db.connection)
        collections = repo.list_all()

    if not collections:
        console.print("[yellow]No collections found.[/yellow]")
        return

    if verbose:
        for collection in collections:
            console.print(f"\n[bold cyan]{collection.name}[/bold cyan]")
            console.print(f"  Path: {collection.path}")
            console.print(f"  Pattern: {collection.pattern}")
            console.print(f"  Documents: {collection.document_count}")
            console.print(f"  Chunks: {collection.chunk_count}")
            if collection.description:
                console.print(f"  Description: {collection.description}")
    else:
        table = Table(title="Collections")
        table.add_column("Name", style="cyan")
        table.add_column("Path", style="green")
        table.add_column("Documents", style="yellow", justify="right")
        table.add_column("Default", style="blue")

        for collection in collections:
            table.add_row(
                collection.name,
                collection.path,
                str(collection.document_count),
                "✓" if collection.include_by_default else "✗",
            )

        console.print(table)


@collection_group.command("show")
@click.argument("name")
@click.pass_context
def collection_show(ctx: click.Context, name: str) -> None:
    """Show collection details."""
    index_path = ctx.obj["index_path"]

    db = Database(index_path)
    db.init_schema()

    with db.connection:
        repo = CollectionRepository(db.connection)
        collection = repo.get_by_name(name)

        if not collection:
            raise click.ClickException(f"Collection '{name}' not found")

        console.print(f"[bold cyan]{collection.name}[/bold cyan]")
        console.print(f"  ID: {collection.id}")
        console.print(f"  Path: {collection.path}")
        console.print(f"  Pattern: {collection.pattern}")
        console.print(f"  Ignore Patterns: {', '.join(collection.ignore_patterns) or 'None'}")
        console.print(f"  Include by Default: {'Yes' if collection.include_by_default else 'No'}")
        console.print(f"  Documents: {collection.document_count}")
        console.print(f"  Chunks: {collection.chunk_count}")
        console.print(f"  Created: {collection.created_at}")
        console.print(f"  Updated: {collection.updated_at}")
        if collection.last_indexed_at:
            console.print(f"  Last Indexed: {collection.last_indexed_at}")
        if collection.description:
            console.print(f"  Description: {collection.description}")


@collection_group.command("enable")
@click.argument("name")
@click.pass_context
def collection_enable(ctx: click.Context, name: str) -> None:
    """Enable a collection for default searches."""
    index_path = ctx.obj["index_path"]

    db = Database(index_path)
    db.init_schema()

    with db.transaction() as conn:
        repo = CollectionRepository(conn)
        collection = repo.get_by_name(name)

        if not collection:
            raise click.ClickException(f"Collection '{name}' not found")

        collection.include_by_default = True
        repo.update(collection)

    console.print(f"[green]Collection '{name}' enabled[/green]")


@collection_group.command("disable")
@click.argument("name")
@click.pass_context
def collection_disable(ctx: click.Context, name: str) -> None:
    """Disable a collection from default searches."""
    index_path = ctx.obj["index_path"]

    db = Database(index_path)
    db.init_schema()

    with db.transaction() as conn:
        repo = CollectionRepository(conn)
        collection = repo.get_by_name(name)

        if not collection:
            raise click.ClickException(f"Collection '{name}' not found")

        collection.include_by_default = False
        repo.update(collection)

    console.print(f"[green]Collection '{name}' disabled[/green]")


@collection_group.command("update-cmd")
@click.argument("name")
@click.option("--cmd", "-c", help="Shell command to run before indexing")
@click.option("--clear", is_flag=True, help="Clear the pre-update command")
@click.pass_context
def collection_update_cmd(ctx: click.Context, name: str, cmd: str | None, clear: bool) -> None:
    """Set or clear a pre-index shell command for a collection."""
    index_path = ctx.obj["index_path"]
    db = Database(index_path)
    db.init_schema()
    with db.transaction() as conn:
        repo = CollectionRepository(conn)
        collection = repo.get_by_name(name)
        if not collection:
            raise click.ClickException(f"Collection '{name}' not found")
        if clear:
            collection.pre_update_cmd = None
        elif cmd is not None:
            collection.pre_update_cmd = cmd
        else:
            raise click.ClickException("Provide --cmd or --clear")
        repo.update(collection)
    if clear:
        console.print(f"[green]Cleared pre-update command for '{name}'[/green]")
    else:
        console.print(f"[green]Set pre-update command for '{name}': {cmd}[/green]")


@collection_group.command("include")
@click.argument("name")
@click.pass_context
def collection_include(ctx: click.Context, name: str) -> None:
    """Include a collection in default searches."""
    index_path = ctx.obj["index_path"]
    db = Database(index_path)
    db.init_schema()
    with db.transaction() as conn:
        repo = CollectionRepository(conn)
        collection = repo.get_by_name(name)
        if not collection:
            raise click.ClickException(f"Collection '{name}' not found")
        collection.include_by_default = True
        repo.update(collection)
    console.print(f"[green]Collection '{name}' included in default searches[/green]")


@collection_group.command("exclude")
@click.argument("name")
@click.pass_context
def collection_exclude(ctx: click.Context, name: str) -> None:
    """Exclude a collection from default searches."""
    index_path = ctx.obj["index_path"]
    db = Database(index_path)
    db.init_schema()
    with db.transaction() as conn:
        repo = CollectionRepository(conn)
        collection = repo.get_by_name(name)
        if not collection:
            raise click.ClickException(f"Collection '{name}' not found")
        collection.include_by_default = False
        repo.update(collection)
    console.print(f"[green]Collection '{name}' excluded from default searches[/green]")


@collection_group.command("ls")
@click.argument("name")
@click.argument("subpath", required=False)
@click.pass_context
def collection_ls(ctx: click.Context, name: str, subpath: Optional[str]) -> None:
    """List files in a collection."""
    index_path = ctx.obj["index_path"]

    db = Database(index_path)
    db.init_schema()

    with db.connection:
        repo = CollectionRepository(db.connection)
        collection = repo.get_by_name(name)

        if not collection:
            raise click.ClickException(f"Collection '{name}' not found")

        # Scan files
        from sif.indexing.scanner import FileScanner

        scanner = FileScanner()
        scan_result = scanner.scan(
            Path(collection.path),
            pattern=collection.pattern,
            ignore_patterns=collection.ignore_patterns,
        )

        if not scan_result.files:
            console.print("[yellow]No files found in collection.[/yellow]")
            return

        # Build tree
        tree = Tree(f"[bold cyan]{collection.name}[/bold cyan]")

        for file_path in sorted(scan_result.files):
            rel_path = file_path.relative_to(collection.path)
            tree.add(str(rel_path))

        console.print(tree)
