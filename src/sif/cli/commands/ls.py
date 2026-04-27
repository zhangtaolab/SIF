"""Top-level ls command for indexed documents."""

from __future__ import annotations

import click
from rich.console import Console
from rich.tree import Tree

from sif.database.database import Database
from sif.database.repositories import CollectionRepository, DocumentRepository


console = Console()


@click.command("ls")
@click.argument("collection", required=False)
@click.argument("subpath", required=False)
@click.pass_context
def ls_cmd(
    ctx: click.Context,
    collection: str | None,
    subpath: str | None,
) -> None:
    """List indexed documents as a virtual file tree."""
    index_path = ctx.obj["index_path"]

    if not index_path.exists():
        console.print("[yellow]No index found.[/yellow]")
        return

    db = Database(index_path)
    db.init_schema()

    with db.connection:
        doc_repo = DocumentRepository(db.connection)
        coll_repo = CollectionRepository(db.connection)

        if collection:
            collections = [coll_repo.get_by_name(collection)]
            if not collections[0]:
                raise click.ClickException(f"Collection '{collection}' not found")
        else:
            collections = coll_repo.list_all()

        for coll in collections:
            if not coll:
                continue

            docs = doc_repo.list_by_collection(coll.id)
            if subpath:
                prefix = subpath.strip("/")
                docs = [d for d in docs if d.path.strip("/").startswith(prefix)]

            if not docs:
                continue

            tree = Tree(f"[bold cyan]{coll.name}[/bold cyan]")
            for doc in sorted(docs, key=lambda d: d.path):
                parts = doc.path.strip("/").split("/")
                node = tree
                for part in parts[:-1]:
                    found = next((c for c in node.children if str(c.label) == part), None)
                    node = found if found else node.add(part)
                node.add(parts[-1])

            console.print(tree)
