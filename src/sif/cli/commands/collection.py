"""Collection management commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from sif.cli.error_handling import open_initialized_database
from sif.cli.filter_options import parse_filter_option, parse_match_option
from sif.core.models import Collection
from sif.database.database import Database
from sif.database.metadata_repository import MetadataValueRepository
from sif.database.repositories import CollectionRepository
from sif.search.filters import compile_filter, compile_match
from sif.utils.json_output import json_dumps_strict


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
def collection_add(  # noqa: PLR0913
    ctx: click.Context,
    path: str,
    name: str,
    pattern: str,
    ignore: tuple,
    description: str | None,
    no_default: bool,
) -> None:
    """Add a new collection."""
    index_path = ctx.obj["index_path"]

    with open_initialized_database(index_path, Database) as db:
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

    with open_initialized_database(index_path, Database) as db:
        with db.transaction() as conn:
            repo = CollectionRepository(conn)

            collection = repo.get_by_name(name)
            if not collection:
                raise click.ClickException(f"Collection '{name}' not found")

            # Purge vec0 embeddings first: the virtual table cannot carry the
            # documents FK cascade, so orphaned rows would pollute KNN search
            # until cleanup (WR-01). Documents then cascade-delete their chunks.
            from sif.database.repositories import DocumentRepository  # noqa: PLC0415
            from sif.search.vector import create_embedding_purger  # noqa: PLC0415

            purger = create_embedding_purger(conn)
            if purger is not None:
                doc_ids = [
                    row[0]
                    for row in conn.execute(
                        "SELECT id FROM documents WHERE collection_id = ?", (collection.id,)
                    )
                ]
                for doc_id in doc_ids:
                    purger.delete_embeddings_by_document(doc_id)

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

    with open_initialized_database(index_path, Database) as db:
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

    with open_initialized_database(index_path, Database) as db:
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

    with open_initialized_database(index_path, Database) as db:
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

    with open_initialized_database(index_path, Database) as db:
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

    with open_initialized_database(index_path, Database) as db:
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

    with open_initialized_database(index_path, Database) as db:
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

    with open_initialized_database(index_path, Database) as db:
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

    with open_initialized_database(index_path, Database) as db:
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
def collection_ls(ctx: click.Context, name: str, subpath: str | None) -> None:
    """List files in a collection."""
    index_path = ctx.obj["index_path"]

    with open_initialized_database(index_path, Database) as db, db.connection:
        repo = CollectionRepository(db.connection)
        collection = repo.get_by_name(name)

        if not collection:
            raise click.ClickException(f"Collection '{name}' not found")

        # Scan files
        from sif.indexing.scanner import FileScanner  # noqa: PLC0415

        scanner = FileScanner()
        scan_result = scanner.scan(
            Path(collection.path),
            pattern=collection.pattern,
            ignore_patterns=collection.ignore_patterns,
        )

        files = scan_result.files
        if subpath:
            sub = Path(subpath)
            resolved = sub if sub.is_absolute() else Path(collection.path) / sub
            # Normalize both sides to forward-slash form: on Windows a
            # backslash path never matches a "/"-suffixed comparison.
            target = resolved.as_posix().rstrip("/")
            files = [
                f for f in files if f.as_posix() == target or f.as_posix().startswith(target + "/")
            ]

        if not files:
            console.print("[yellow]No files found in collection.[/yellow]")
            return

        # Build tree
        tree = Tree(f"[bold cyan]{collection.name}[/bold cyan]")

        for file_path in sorted(files):
            rel_path = file_path.relative_to(collection.path)
            # Render forward-slash relative paths on every platform so the
            # listing is identical to the POSIX form on Windows.
            tree.add(rel_path.as_posix())

        console.print(tree)


def _format_number(value: float) -> str:
    """Render a range bound compactly (integers without a trailing ``.0``)."""
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


def _range_text(type_entry: dict[str, Any]) -> str:
    """Render ``min / median / max`` for a numeric type entry."""
    range_data = type_entry.get("range")
    if not range_data:
        return ""
    return " / ".join(_format_number(range_data[part]) for part in ("min", "median", "max"))


def _value_window_text(type_entry: dict[str, Any]) -> str:
    """Render ``returned of distinct`` plus the exact remainder."""
    text = f"{len(type_entry['values'])} of {type_entry['distinctValues']}"
    if type_entry["remainingValues"]:
        text += f" +{type_entry['remainingValues']} more"
    return text


def _render_metadata_table(result: dict[str, Any]) -> None:
    """Render the discovery envelope as a table (built-ins first, D-03/D-20)."""
    table = Table(title="Metadata")
    table.add_column("Source", style="magenta")
    table.add_column("Key", style="cyan")
    table.add_column("Types", style="green")
    table.add_column("Documents", style="yellow", justify="right")
    table.add_column("Values", justify="right")
    table.add_column("Range", justify="right")
    for entry in result["builtIns"]:
        for type_entry in entry["types"]:
            table.add_row(
                "built-in",
                entry["key"],
                type_entry["type"],
                str(entry["documents"]),
                f"0 of {type_entry['distinctValues']}",
                _range_text(type_entry),
            )
    for entry in result["keys"]:
        for type_entry in entry["types"]:
            table.add_row(
                "frontmatter",
                entry["key"],
                type_entry["type"],
                str(type_entry["documents"]),
                _value_window_text(type_entry),
                _range_text(type_entry),
            )
    console.print(table)
    if result["remainingKeys"]:
        console.print(f"... {result['remainingKeys']} more keys")
    skipped = int(result["skippedKeys"])
    if skipped:
        # D-07: silence is impossible — the default human surface must report
        # non-indexable keys too, or a corpus of all-skipped keys would look
        # identical to one with no frontmatter (WR-07).
        noun = "key" if skipped == 1 else "keys"
        console.print(f"... {skipped} {noun} skipped as non-indexable")


@collection_group.command("metadata")
@click.argument("name", required=False)
@click.option(
    "--filter",
    "filter_json",
    default=None,
    metavar="<json>",
    help="Metadata filter as a JSON AST; counts become filter-aware.",
)
@click.option(
    "--match",
    "match_json",
    default=None,
    metavar="<json>",
    help="Narrow reported entries by key or value (JSON AST).",
)
@click.option(
    "--min-count",
    type=click.IntRange(min=1),
    default=1,
    help="Minimum documents per reported value (default: 1)",
)
@click.option(
    "--sort",
    type=click.Choice(["count", "value"]),
    default="count",
    help="Key ordering: document count descending, or key ascending (default: count)",
)
@click.option(
    "--limit",
    type=click.IntRange(min=1),
    default=50,
    help="Key window size (default: 50)",
)
@click.option(
    "--value-limit",
    type=click.IntRange(min=0),
    default=10,
    help="Per-key value window size (default: 10)",
)
@click.option("--json", "output_json", is_flag=True, help="Output the JSON envelope")
@click.pass_context
def collection_metadata(  # noqa: PLR0913 — one parameter per the D-14 option contract
    ctx: click.Context,
    name: str | None,
    filter_json: str | None,
    match_json: str | None,
    min_count: int,
    sort: str,
    limit: int,
    value_limit: int,
    output_json: bool,
) -> None:
    """Report filterable metadata keys, types, counts, ranges, and remainders.

    No NAME means every collection. `path` and `mtime` are reserved built-in
    fields (D-03): they appear in the built-in section, never as frontmatter
    keys, and their counts narrow with `--filter` exactly like every other
    count.
    """
    index_path = ctx.obj["index_path"]
    # Parse/validate before the database opens (D-17): a bad filter or match
    # never pays schema init. An absent option stays None — never the
    # compiler's empty ("", []) fragment, which would signal a supplied filter.
    parsed_filter = parse_filter_option(filter_json)
    parsed_match = parse_match_option(match_json)

    with open_initialized_database(index_path, Database) as db, db.connection:
        collection_ids: list[str] | None = None
        if name is not None:
            collection = CollectionRepository(db.connection).get_by_name(name)
            if collection is None:
                raise click.ClickException(f"Collection '{name}' not found")
            collection_ids = [collection.id]
        filter_predicate = (
            compile_filter(parsed_filter, alias="d", scope="corpus")
            if parsed_filter is not None
            else None
        )
        match_predicate = (
            compile_match(parsed_match, alias="mv") if parsed_match is not None else None
        )
        result = MetadataValueRepository(db.connection).discover(
            collection_ids=collection_ids,
            filter_predicate=filter_predicate,
            match_predicate=match_predicate,
            min_count=min_count,
            sort=sort,
            limit=limit,
            value_limit=value_limit,
        )

    if output_json:
        click.echo(json_dumps_strict(result))
        return
    _render_metadata_table(result)
