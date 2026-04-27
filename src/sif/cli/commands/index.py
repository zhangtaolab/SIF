"""Index management commands."""

from __future__ import annotations

import subprocess
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from sif.core.models import Document
from sif.database.database import Database
from sif.database.repositories import (
    CollectionRepository,
    DocumentChunkRepository,
    DocumentRepository,
)
from sif.indexing.chunker import create_chunker
from sif.indexing.parser import MarkdownParser
from sif.indexing.scanner import FileScanner


console = Console()


@click.group("index")
def index_group() -> None:
    """Index management commands."""
    pass


@index_group.command("update")
@click.option("--collection", "-c", help="Update specific collection only")
@click.option("--force", "-f", is_flag=True, help="Force re-index all documents")
@click.pass_context
def update_cmd(ctx: click.Context, collection: str | None, force: bool) -> None:  # noqa: C901, PLR0912, PLR0915
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
            console.print(
                "[yellow]No collections found. Add one with 'sif collection add'.[/yellow]"
            )
            return

        total_added = 0
        total_updated = 0
        total_removed = 0

        for coll in collections:
            if not coll:
                continue

            console.print(f"\n[bold]Updating collection: {coll.name}[/bold]")

            if coll.pre_update_cmd:
                console.print(f"  Running pre-update command: {coll.pre_update_cmd}")
                result = subprocess.run(
                    coll.pre_update_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode != 0:
                    err_msg = (
                        f"Pre-update command failed for '{coll.name}' "
                        f"(exit {result.returncode}): "
                        f"{result.stderr.strip() or result.stdout.strip()}"
                    )
                    raise click.ClickException(err_msg)

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
            from datetime import datetime, timezone  # noqa: PLC0415

            coll.last_indexed_at = datetime.now(timezone.utc)
            coll_repo.update(coll)

        console.print("\n[green]Index updated:[/green]")
        console.print(f"  Added: {total_added}")
        console.print(f"  Updated: {total_updated}")
        console.print(f"  Removed: {total_removed}")


@index_group.command("embed")
@click.option("--collection", "-c", help="Embed specific collection only")
@click.option("--force", "-f", is_flag=True, help="Force re-embed all documents")
@click.option("--chunk-strategy", default="auto", help="Chunking strategy")
@click.option("--model", "-m", help="Embedding model name")
@click.option(
    "--model-type",
    type=click.Choice(["sentence_transformers", "gguf", "openai", "modelscope"]),
    help="Embedding model type override",
)
@click.pass_context
def embed_cmd(  # noqa: C901, PLR0912, PLR0913, PLR0915
    ctx: click.Context,
    collection: str | None,
    force: bool,  # noqa: ARG001
    chunk_strategy: str,
    model: str | None,
    model_type: str | None = None,
) -> None:
    """Generate embeddings for documents."""
    index_path = ctx.obj["index_path"]

    db = Database(index_path)
    db.init_schema()

    # Initialize embedder
    from sif.config.settings import get_settings  # noqa: PLC0415
    from sif.embedding.manager import EmbeddingManager  # noqa: PLC0415
    from sif.search.vector import VectorSearcher  # noqa: PLC0415

    settings = get_settings()
    if model:
        settings = settings.model_copy(update={"model_name": model})
    if model_type:
        settings = settings.model_copy(update={"model_type": model_type})

    try:
        manager = EmbeddingManager.from_settings(settings)
    except ImportError as e:
        console.print(f"[red]Embedding backend not installed: {e}[/red]")
        return
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
            chunker = create_chunker(chunk_strategy)

            # Collect all chunks across documents
            all_chunks = []  # (chunk, document_id)
            doc_chunks_map: dict[str, list] = {}

            for doc in documents:
                chunk_repo.delete_by_document(doc.id)
                chunks = chunker.chunk(doc.content)
                doc_chunks_map[doc.id] = chunks
                for i, chunk in enumerate(chunks):
                    chunk.document_id = doc.id
                    chunk.sequence = i
                    all_chunks.append((chunk, doc.id))

            # Batch embed all chunks
            if all_chunks:
                try:
                    chunk_texts = [c.content for c, _ in all_chunks]
                    embedding_response = manager.embed(chunk_texts)
                    embeddings = embedding_response.embeddings

                    # Persist chunks and embeddings
                    batch_items: list[tuple[str, str, str | None, list[float]]] = []
                    for (chunk, doc_id), embedding in zip(all_chunks, embeddings):
                        chunk_repo.create(chunk)
                        batch_items.append((chunk.id, doc_id, chunk.id, embedding))

                    if batch_items:
                        vector_searcher = VectorSearcher(
                            db.connection, len(manager.embed_single("probe"))
                        )
                        vector_searcher.add_embeddings_batch(batch_items)

                    total_chunks += len(all_chunks)
                except Exception as e:
                    console.print(f"  [red]Error embedding collection {coll.name}: {e}[/red]")

            # Update collection stats
            documents = doc_repo.list_by_collection(coll.id)
            coll.chunk_count = sum(len(chunk_repo.get_by_document(d.id)) for d in documents)
            coll_repo.update(coll)

        console.print(f"\n[green]Embedding complete: {total_chunks} chunks embedded[/green]")


@index_group.command("status")
@click.pass_context
def index_status_cmd(ctx: click.Context) -> None:
    """Show index status."""
    # Delegate to main status command
    from sif.cli.main import status_cmd  # noqa: PLC0415

    ctx.invoke(status_cmd)
