"""Document retrieval commands."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.syntax import Syntax

from docsift.database.database import Database
from docsift.database.repositories import DocumentRepository

console = Console()


@click.group("get")
def get_group() -> None:
    """Retrieve documents."""
    pass


@get_group.command("get")
@click.argument("path_or_docid")
@click.option("--from-line", "-f", type=int, help="Start from line number")
@click.option("--lines", "-l", type=int, help="Number of lines to show")
@click.pass_context
def get_cmd(
    ctx: click.Context,
    path_or_docid: str,
    from_line: Optional[int],
    lines: Optional[int],
) -> None:
    """Get a document by path or document ID."""
    index_path = ctx.obj["index_path"]
    
    if not index_path.exists():
        console.print("[yellow]No index found.[/yellow]")
        return
    
    db = Database(index_path)
    db.init_schema()
    
    with db.connection:
        doc_repo = DocumentRepository(db.connection)
        
        # Try to find by ID first
        doc = doc_repo.get_by_id(path_or_docid)
        
        if not doc:
            # Try to find by path
            # Need collection ID - search all collections
            from docsift.database.repositories import CollectionRepository
            coll_repo = CollectionRepository(db.connection)
            
            for coll in coll_repo.list_all():
                doc = doc_repo.get_by_path(path_or_docid, coll.id)
                if doc:
                    break
        
        if not doc:
            # Try as file path
            path = Path(path_or_docid)
            if path.exists():
                try:
                    content = path.read_text()
                    console.print(f"[bold]{path}[/bold]")
                    console.print(content)
                    return
                except Exception as e:
                    raise click.ClickException(f"Cannot read file: {e}")
            
            raise click.ClickException(f"Document not found: {path_or_docid}")
        
        # Display document
        console.print(f"[bold cyan]{doc.title or doc.filename}[/bold cyan]")
        console.print(f"[dim]Path: {doc.path}[/dim]")
        console.print(f"[dim]Collection: {doc.collection_id}[/dim]")
        console.print("")
        
        # Get content
        content = doc.content
        
        # Apply line filtering
        if from_line is not None or lines is not None:
            content_lines = content.split("\n")
            
            start = (from_line or 1) - 1  # Convert to 0-indexed
            start = max(0, start)
            
            if lines is not None:
                end = start + lines
                content_lines = content_lines[start:end]
            else:
                content_lines = content_lines[start:]
            
            content = "\n".join(content_lines)
        
        # Display with syntax highlighting if markdown
        if doc.path.endswith(".md"):
            console.print(content)
        else:
            console.print(content)


@get_group.command("multi-get")
@click.argument("pattern")
@click.option("--max-bytes", "-b", type=int, default=100000, help="Max bytes per file")
@click.pass_context
def multi_get_cmd(
    ctx: click.Context,
    pattern: str,
    max_bytes: int,
) -> None:
    """Get multiple documents matching a pattern."""
    index_path = ctx.obj["index_path"]
    
    if not index_path.exists():
        console.print("[yellow]No index found.[/yellow]")
        return
    
    import fnmatch
    
    db = Database(index_path)
    db.init_schema()
    
    with db.connection:
        doc_repo = DocumentRepository(db.connection)
        
        # Get all documents
        from docsift.database.repositories import CollectionRepository
        coll_repo = CollectionRepository(db.connection)
        
        matched_docs = []
        errors = []
        
        for coll in coll_repo.list_all():
            for doc in doc_repo.list_by_collection(coll.id):
                if fnmatch.fnmatch(doc.path, pattern) or fnmatch.fnmatch(doc.filename, pattern):
                    matched_docs.append(doc)
        
        if not matched_docs:
            console.print(f"[yellow]No documents matching pattern: {pattern}[/yellow]")
            return
        
        console.print(f"[green]Found {len(matched_docs)} matching documents[/green]")
        console.print("")
        
        for doc in matched_docs:
            content = doc.content
            if len(content.encode()) > max_bytes:
                content = content[:max_bytes] + "\n... [truncated]"
            
            console.print(f"[bold cyan]=== {doc.path} ===[/bold cyan]")
            console.print(content)
            console.print("")
