"""Index management commands."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TaskID, TextColumn

from sif.core.models import Collection
from sif.database.database import Database
from sif.database.locking import index_lock
from sif.database.repositories import (
    CollectionRepository,
    DocumentChunkRepository,
    DocumentRepository,
)
from sif.indexing.chunker import create_chunker
from sif.indexing.incremental import IncrementalIndexer


console = Console()

# A hung pre-update command (network stall, prompt on stdin) must not block
# `sif index update` forever (WR-06). No per-collection timeout setting exists
# yet, so all commands share this bound.
_PRE_UPDATE_TIMEOUT_SECONDS = 300


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

    with Database(index_path) as db:
        db.init_schema()

        from sif.config.settings import get_settings  # noqa: PLC0415

        lock_timeout = get_settings().lock_wait_timeout
        with index_lock(
            Path(index_path),
            lock_timeout,
            on_wait=lambda: console.print(
                f"[dim]Another index writer is running; waiting up to {lock_timeout:.0f}s...[/dim]"
            ),
        ):
            coll_repo = CollectionRepository(db.connection)

            # Get collections to update
            if collection:
                found = coll_repo.get_by_name(collection)
                if not found:
                    raise click.ClickException(f"Collection '{collection}' not found")
                collections = [found]
            else:
                collections = coll_repo.list_all()

            if not collections:
                console.print(
                    "[yellow]No collections found. Add one with 'sif collection add'.[/yellow]",
                )
                return

            # The per-file incremental loop lives in exactly one place (SC3):
            # the CLI delegates to the shared core and renders its counts.
            indexer = IncrementalIndexer(db.connection)
            total_added = 0
            total_updated = 0
            total_removed = 0

            for coll in collections:
                if not coll:
                    continue

                console.print(f"\n[bold]Updating collection: {coll.name}[/bold]")
                _run_pre_update_hook(coll)

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    task = progress.add_task(f"Indexing {coll.name}...", total=None)
                    result = indexer.update_collection(
                        coll,
                        force=force,
                        progress=_render_index_event(console, progress, task),
                    )

                total_added += result.added
                total_updated += result.updated
                total_removed += result.removed

            console.print("\n[green]Index updated:[/green]")
            console.print(f"  Added: {total_added}")
            console.print(f"  Updated: {total_updated}")
            console.print(f"  Removed: {total_removed}")


def _run_pre_update_hook(coll: Collection) -> None:
    """Run a collection's pre-update subprocess hook.

    The hook is command policy/presentation, so it stays in the CLI: MCP and
    watch hosts (Phases 12-13) decide their own pre-behavior.
    """
    if not coll.pre_update_cmd:
        return
    console.print(f"  Running pre-update command: {coll.pre_update_cmd}")
    try:
        result = subprocess.run(
            coll.pre_update_cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=False,
            timeout=_PRE_UPDATE_TIMEOUT_SECONDS,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired as e:
        raise click.ClickException(
            f"Pre-update command for '{coll.name}' timed out after "
            f"{_PRE_UPDATE_TIMEOUT_SECONDS}s: {coll.pre_update_cmd}"
        ) from e
    if result.returncode != 0:
        err_msg = (
            f"Pre-update command failed for '{coll.name}' "
            f"(exit {result.returncode}): "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
        raise click.ClickException(err_msg)


def _render_index_event(
    console: Console,
    progress: Progress,
    task: TaskID,
) -> Callable[[str], None]:
    """Render IncrementalIndexer progress events with the CLI's Rich styling.

    The core emits presentation-free ``"code payload"`` events; this callback
    is the only place they become console lines and progress advances, so MCP
    and watch hosts reuse the core without Rich.
    """

    def _on_event(event: str) -> None:
        code, _, payload = event.partition(" ")
        if code == "scan":
            progress.update(task, total=int(payload))
            console.print(f"  Found {payload} files")
        elif code == "unchanged":
            console.print(f"  [dim]Unchanged: {payload}[/dim]")
        elif code == "error":
            console.print(f"  [red]{payload}[/red]")
        progress.advance(task)

    return _on_event


def _needs_embedding(live_chunk_ids: set[str], embedded_chunk_ids: set[str], force: bool) -> bool:
    """Decide whether a document needs (re-)embedding.

    A document is skipped only when --force is off and its live chunk ids
    exactly match the stored embedding chunk-id set — complete and orphan-free.
    Chunkless, partial, or orphaned states all re-embed (self-healing).
    """
    return force or not live_chunk_ids or live_chunk_ids != embedded_chunk_ids


@index_group.command("embed")
@click.option("--collection", "-c", help="Embed specific collection only")
@click.option("--force", "-f", is_flag=True, help="Force re-embed all documents")
@click.option(
    "--chunk-strategy",
    type=click.Choice(["auto", "fixed", "markdown", "code"]),
    default="auto",
    help="Chunking strategy",
)
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
    force: bool,
    chunk_strategy: str,
    model: str | None,
    model_type: str | None = None,
) -> None:
    """Generate embeddings for documents."""
    index_path = ctx.obj["index_path"]

    with Database(index_path) as db:
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
            # Load eagerly so backend-missing / dimension-mismatch errors surface
            # here (model loading is lazy, so from_settings alone never raises).
            manager.load_model()
        except ImportError as e:
            raise click.ClickException(f"Embedding backend not installed: {e}") from e
        except Exception as e:
            raise click.ClickException(f"Failed to load embedding model: {e}") from e

        # Probe-free dimension: the eagerly-loaded model already knows its dim, so
        # remote backends are never billed for a throwaway probe embedding.
        model_dim = manager.get_model_info().get("embedding_dim")
        embedding_dim = (
            model_dim if isinstance(model_dim, int) else len(manager.embed_single("probe"))
        )

        # Fail fast when the loaded model's dimension disagrees with the vec0
        # table's declared dimension (WR-02): local backends validate this nowhere
        # else, and the mismatch would otherwise surface as a raw sqlite-vec
        # insert error only after chunks are already written.
        schema_row = db.connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='document_embeddings'"
        ).fetchone()
        if schema_row:
            schema_sql = schema_row[0] if isinstance(schema_row[0], str) else ""
            dim_match = re.search(r"FLOAT\[(\d+)\]", schema_sql)
            if dim_match and int(dim_match.group(1)) != embedding_dim:
                raise click.ClickException(
                    f"Model '{model or settings.model_name}' produces {embedding_dim}-dim "
                    f"embeddings but the index stores {dim_match.group(1)}-dim vectors. "
                    "Set SIF_EMBEDDING_DIM to the model's dimension and rebuild."
                )

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

        # D-01: embed_cmd holds the DB write lock for an entire collection, so
        # it must arbitrate with update_cmd on the same per-DB flock. The lock
        # sits below the embedder load and the vec0 dimension check on purpose
        # — it is never held across model loading. The collection loop's
        # per-collection transactions keep their exact commit points (D-05):
        # the factory's implicit BEGIN IMMEDIATE flowing through the existing
        # with-conn blocks is the accepted, strictly-better change (CR-02).
        lock_timeout = settings.lock_wait_timeout
        with index_lock(
            Path(index_path),
            lock_timeout,
            on_wait=lambda: console.print(
                f"[dim]Another index writer is running; waiting up to {lock_timeout:.0f}s...[/dim]"
            ),
        ):
            total_chunks = 0
            failed_collections: list[str] = []

            for coll in collections:
                if not coll:
                    continue

                console.print(f"\n[bold]Embedding collection: {coll.name}[/bold]")
                documents = doc_repo.list_by_collection(coll.id)

                if not documents:
                    with db.connection:
                        coll.chunk_count = 0
                        coll_repo.update(coll)
                    continue

                chunker = create_chunker(chunk_strategy)

                # One searcher per collection. Construction failure (sqlite-vec
                # unavailable) is user-facing and never swallowed (D-03 fail-fast).
                # Raised outside any open transaction so it cannot roll back work
                # already committed by earlier collections (CR-02).
                try:
                    vector_searcher = VectorSearcher(db.connection, embedding_dim)
                except RuntimeError as e:
                    raise click.ClickException(f"Vector store unavailable: {e}") from e

                # One transaction per collection (CR-02): a failed collection rolls
                # back only its own work, and successful collections keep theirs.
                # (The previous whole-run transaction discarded every successful
                # collection when the final failure report was raised inside it.)
                all_chunks = []  # (chunk, document_id)
                doc_chunks_map: dict[str, list] = {}
                try:
                    # One unindexed metadata scan per document made the completeness
                    # check quadratic; prefetch the whole map once per collection and
                    # judge each document against it.
                    embedded_by_doc = vector_searcher.get_all_embedded_chunk_ids()
                    with db.connection:
                        for doc in documents:
                            # Skip documents whose live chunks already have an exact,
                            # complete set of embeddings; --force bypasses the check.
                            existing = chunk_repo.get_by_document(doc.id)
                            embedded = embedded_by_doc.get(doc.id, set())
                            if not _needs_embedding({c.id for c in existing}, embedded, force):
                                console.print(f"  [dim]Already embedded: {doc.path}[/dim]")
                                continue
                            chunk_repo.delete_by_document(doc.id)
                            # Delete-before-insert (G-03-3): re-chunked rows get fresh
                            # uuid4 ids that can never collide with the old embedding
                            # rows, so the old vectors must be removed explicitly.
                            vector_searcher.delete_embeddings_by_document(doc.id)
                            chunks = chunker.chunk(doc.content)
                            doc_chunks_map[doc.id] = chunks
                            for i, chunk in enumerate(chunks):
                                chunk.document_id = doc.id
                                chunk.sequence = i
                                all_chunks.append((chunk, doc.id))

                        # Batch embed all chunks
                        if all_chunks:
                            chunk_texts = [c.content for c, _ in all_chunks]
                            embedding_response = manager.embed(chunk_texts)
                            embeddings = embedding_response.embeddings

                            # Persist chunks and embeddings
                            batch_items: list[tuple[str, str, str | None, list[float]]] = []
                            for (chunk, doc_id), embedding in zip(
                                all_chunks, embeddings, strict=True
                            ):
                                chunk_repo.create(chunk)
                                batch_items.append((chunk.id, doc_id, chunk.id, embedding))

                            vector_searcher.add_embeddings_batch(batch_items)

                        # Update collection stats
                        documents = doc_repo.list_by_collection(coll.id)
                        coll.chunk_count = sum(
                            len(chunk_repo.get_by_document(d.id)) for d in documents
                        )
                        coll_repo.update(coll)
                    # Count only after the transaction committed — a rolled-back
                    # collection must not be reported as embedded.
                    total_chunks += len(all_chunks)
                except Exception as e:
                    console.print(f"  [red]Error embedding collection {coll.name}: {e}[/red]")
                    failed_collections.append(coll.name)
                    continue

        console.print(f"\n[green]Embedding complete: {total_chunks} chunks embedded[/green]")

        # Raised outside any db transaction (CR-02): the successful collections'
        # commits above must survive this non-zero exit.
        if failed_collections:
            raise click.ClickException(
                f"Embedding failed for {len(failed_collections)} collection(s): "
                + ", ".join(failed_collections)
            )


@index_group.command("status")
@click.pass_context
def index_status_cmd(ctx: click.Context) -> None:
    """Show index status."""
    # Delegate to main status command
    from sif.cli.main import status_cmd  # noqa: PLC0415

    ctx.invoke(status_cmd)
