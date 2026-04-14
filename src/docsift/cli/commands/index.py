"""Index management commands."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from docsift.core.models import Document
from docsift.database.database import Database
from docsift.database.repositories import (
    CollectionRepository,
    DocumentChunkRepository,
    DocumentRepository,
)
from docsift.indexing.chunker import create_chunker
from docsift.indexing.parser import MarkdownParser
from docsift.indexing.scanner import FileScanner

console = Console()


@click.group("index")
def index_group() -> None:
    """Index management commands."""
    pass


@index_group.command("update")
@click.option("--collection", "-c", help="Update specific collection only")
@click.option("--force", "-f", is_flag=True, help="Force re-index all documents")
@click.pass_context
def update_cmd(ctx: click.Context, collection: str | None, force: bool) -> None:
    """Update the index by scanning collections."""
    index_path = ctx.obj["index_path"]
    
    db = Database(index_path)
    db.init_schema()
    
    with db.connection:
        coll_repo = CollectionRepository(db.connection)
        doc_repo = DocumentRepository(db.connection)
        
        # Get collections to update
        if collection:
            collections = [coll_repo.get_by_name(collection)]
            if not collections[0]:
                raise click.ClickException(f"Collection '{collection}' not found")
        else:
            collections = coll_repo.list_all()
        
        if not collections:
            console.print("[yellow]No collections found. Add one with 'docsift collection add'.[/yellow]")
            return
        
        total_added = 0
        total_updated = 0
        total_removed = 0
        
        for coll in collections:
            if not coll:
                continue
            
            console.print(f"\n[bold]Updating collection: {coll.name}[/bold]")
            
            # Scan files
            scanner = FileScanner()
            scan_result = scanner.scan(
                Path(coll.path),
                pattern=coll.pattern,
                ignore_patterns=coll.ignore_patterns,
            )
            
            console.print(f"  Found {scan_result.file_count} files")
            
            # Get existing documents
            existing_docs = {d.path: d for d in doc_repo.list_by_collection(coll.id)}
            scanned_paths = set()
            
            # Process each file
            parser = MarkdownParser()
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(f"Indexing {coll.name}...", total=scan_result.file_count)
                
                for file_path in scan_result.files:
                    scanned_paths.add(str(file_path))
                    
                    # Parse document
                    try:
                        parsed = parser.parse(file_path)
                    except Exception as e:
                        console.print(f"  [red]Error parsing {file_path}: {e}[/red]")
                        progress.advance(task)
                        continue
                    
                    # Check if document exists
                    existing = existing_docs.get(str(file_path))
                    
                    if existing:
                        # Check if changed
                        if existing.checksum == parsed.checksum and not force:
                            console.print(f"  [dim]Unchanged: {file_path.name}[/dim]")
                            progress.advance(task)
                            continue
                        
                        # Update document
                        existing.content = parsed.content
                        existing.title = parsed.title
                        existing.metadata = parsed.metadata
                        existing.mtime = parsed.mtime
                        doc_repo.update(existing)
                        total_updated += 1
                    else:
                        # Create new document
                        doc = Document(
                            path=str(file_path),
                            collection_id=coll.id,
                            content=parsed.content,
                            title=parsed.title,
                            metadata=parsed.metadata,
                            mtime=parsed.mtime,
                        )
                        doc_repo.create(doc)
                        total_added += 1
                    
                    progress.advance(task)
            
            # Remove documents that no longer exist
            for path, doc in existing_docs.items():
                if path not in scanned_paths:
                    doc_repo.delete(doc.id)
                    total_removed += 1
            
            # Update collection stats
            coll.document_count = len(doc_repo.list_by_collection(coll.id))
            from datetime import datetime
            coll.last_indexed_at = datetime.utcnow()
            coll_repo.update(coll)
        
        console.print(f"\n[green]Index updated:[/green]")
        console.print(f"  Added: {total_added}")
        console.print(f"  Updated: {total_updated}")
        console.print(f"  Removed: {total_removed}")


@index_group.command("embed")
@click.option("--collection", "-c", help="Embed specific collection only")
@click.option("--force", "-f", is_flag=True, help="Force re-embed all documents")
@click.option("--chunk-strategy", default="auto", help="Chunking strategy")
@click.option("--model", "-m", help="Embedding model name")
@click.pass_context
def embed_cmd(
    ctx: click.Context,
    collection: str | None,
    force: bool,
    chunk_strategy: str,
    model: str | None,
) -> None:
    """Generate embeddings for documents."""
    index_path = ctx.obj["index_path"]
    
    console.print("[yellow]Embedding generation requires an embedding model.[/yellow]")
    console.print("[dim]Install with: pip install sentence-transformers[/dim]")
    console.print("")
    
    # Check if sentence-transformers is available
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        console.print("[red]sentence-transformers not installed.[/red]")
        console.print("Run: pip install sentence-transformers")
        return
    
    db = Database(index_path)
    db.init_schema()
    
    # Initialize embedder
    from docsift.config.settings import get_settings
    settings = get_settings()
    model_name = model or settings.model_name

    console.print("Loading embedding model...")
    try:
        embedder = SentenceTransformer(model_name)
    except Exception as e:
        console.print(f"[red]Failed to load embedding model: {e}[/red]")
        return
    
    with db.connection:
        coll_repo = CollectionRepository(db.connection)
        doc_repo = DocumentRepository(db.connection)
        chunk_repo = DocumentChunkRepository(db.connection)
        
        # Get collections
        if collection:
            collections = [coll_repo.get_by_name(collection)]
            if not collections[0]:
                raise click.ClickException(f"Collection '{collection}' not found")
        else:
            collections = coll_repo.list_all()
        
        total_chunks = 0
        
        for coll in collections:
            if not coll:
                continue
            
            console.print(f"\n[bold]Embedding collection: {coll.name}[/bold]")
            
            documents = doc_repo.list_by_collection(coll.id)
            
            # Create chunker
            chunker = create_chunker(chunk_strategy)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(f"Embedding {coll.name}...", total=len(documents))
                
                for doc in documents:
                    # Remove old chunks
                    chunk_repo.delete_by_document(doc.id)
                    
                    # Chunk document
                    chunks = chunker.chunk(doc.content)
                    
                    # Embed chunks
                    chunk_texts = [c.content for c in chunks]
                    if chunk_texts:
                        try:
                            embeddings = embedder.encode(
                                chunk_texts,
                                normalize_embeddings=True,
                                show_progress_bar=False,
                            )
                            
                            # Save chunks with embeddings
                            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                                chunk.document_id = doc.id
                                chunk.sequence = i
                                chunk_repo.create(chunk)
                                
                                # Save embedding to vector table
                                from docsift.search.vector import VectorSearcher
                                vector_searcher = VectorSearcher(db.connection)
                                vector_searcher.add_embedding(
                                    embedding_id=chunk.id,
                                    document_id=doc.id,
                                    chunk_id=chunk.id,
                                    embedding=embedding.tolist(),
                                )
                            
                            total_chunks += len(chunks)
                        except Exception as e:
                            console.print(f"  [red]Error embedding {doc.filename}: {e}[/red]")
                    
                    progress.advance(task)
            
            # Update collection stats
            coll.chunk_count = sum(
                len(chunk_repo.get_by_document(d.id))
                for d in documents
            )
            coll_repo.update(coll)
        
        console.print(f"\n[green]Embedding complete: {total_chunks} chunks embedded[/green]")


@index_group.command("status")
@click.pass_context
def index_status_cmd(ctx: click.Context) -> None:
    """Show index status."""
    # Delegate to main status command
    from docsift.cli.main import status_cmd
    ctx.invoke(status_cmd)
