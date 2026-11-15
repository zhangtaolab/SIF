"""Index management commands."""

from __future__ import annotations

import sqlite3
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import click
from rich.console import Console
from rich.markup import escape
from rich.progress import Progress, SpinnerColumn, TaskID, TextColumn

from sif.cli.error_handling import open_initialized_database
from sif.core.models import Collection
from sif.database.database import Database
from sif.database.locking import index_lock
from sif.database.maintenance import (
    MaintenanceBusyError,
    MaintenanceTargetError,
    backup_index,
    vacuum_index,
)
from sif.database.repositories import (
    CollectionRepository,
    DocumentChunkRepository,
    DocumentRepository,
)
from sif.embedding.identity import (
    EmbedderIdentity,
    certify_identity,
    check_identity,
    ensure_legacy_identity,
    schema_embedding_dim,
)
from sif.indexing.chunker import create_chunker, token_size_to_chars
from sif.indexing.embed_writer import StreamingEmbedWriter, SystemicEmbedError
from sif.indexing.incremental import IncrementalIndexer
from sif.utils.progress import spinner_name


if TYPE_CHECKING:
    from sif.embedding.manager import EmbeddingManager


console = Console()
console_err = Console(stderr=True)

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

    with open_initialized_database(index_path, Database) as db:
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
                    SpinnerColumn(spinner_name(console)),
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
        elif code == "migrate":
            # D-09: one announcement per collection, naming the scanned count.
            console.print(
                f"  [yellow]Upgrading index format: reindexing {escape(payload)} "
                "documents once[/yellow]"
            )
        elif code == "unchanged":
            console.print(f"  [dim]Unchanged: {escape(payload)}[/dim]")
        elif code == "error":
            console.print(f"  [red]{escape(payload)}[/red]")
        progress.advance(task)

    return _on_event


def _needs_embedding(live_chunk_ids: set[str], embedded_chunk_ids: set[str], force: bool) -> bool:
    """Decide whether a document needs (re-)embedding.

    A document is skipped only when --force is off and its live chunk ids
    exactly match the stored embedding chunk-id set — complete and orphan-free.
    Chunkless, partial, or orphaned states all re-embed (self-healing).
    """
    return force or not live_chunk_ids or live_chunk_ids != embedded_chunk_ids


class _EmbedAbortError(Exception):
    """A systemic embed failure: stop after prior commits, then report once."""


def _index_has_vectors(conn: sqlite3.Connection) -> bool:
    """Whether any vector row exists; a missing vec0 table counts as none."""
    try:
        return conn.execute("SELECT 1 FROM document_embeddings LIMIT 1").fetchone() is not None
    except sqlite3.OperationalError:
        return False


def _resolve_identity(
    conn: sqlite3.Connection, manager: EmbeddingManager
) -> EmbedderIdentity | None:
    """Return the current identity when this host has enforceable index state.

    Injected manager doubles return a MagicMock identity and test hosts that
    patch ``Database`` hand over a MagicMock connection; like every Phase 21
    host they carry no identity policy, so the streaming writer keeps the
    pre-Phase-21 path for them. A real ``EmbeddingManager`` always returns a
    real identity, and every production connection is a real SQLite one.
    """
    if not isinstance(conn, sqlite3.Connection):
        return None
    current = manager.get_identity()
    return current if isinstance(current, EmbedderIdentity) else None


def _count_collection_chunks(conn: sqlite3.Connection, collection_id: str) -> int:
    """Count a collection's committed chunk rows with one O(N) SQL query."""
    row = conn.execute(
        "SELECT COUNT(*) FROM document_chunks dc "
        "JOIN documents d ON dc.document_id = d.id "
        "WHERE d.collection_id = ?",
        (collection_id,),
    ).fetchone()
    return int(row[0]) if row is not None else 0


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

    with open_initialized_database(index_path, Database) as db:
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
        # table's declared dimension (WR-02/D-05): the identity module owns the
        # single FLOAT[n] read, and the pre-change user-facing wording survives.
        schema_dim = (
            schema_embedding_dim(db.connection)
            if isinstance(db.connection, sqlite3.Connection)
            else None
        )
        if schema_dim is not None and schema_dim != embedding_dim:
            raise click.ClickException(
                f"Model '{model or settings.model_name}' produces {embedding_dim}-dim "
                f"embeddings but the index stores {schema_dim}-dim vectors. "
                "Set SIF_EMBEDDING_DIM to the model's dimension and rebuild."
            )

        # D-02/D-03/D-04: adopt the identity before any vector write. A legacy
        # populated index is assumed once; a same-width model swap fails fast
        # naming both identities and the remedy. An embeddings-empty index
        # accepts any embedder (D-02) and the first document commit overwrites
        # a stale identity row as source="verified".
        current = _resolve_identity(db.connection, manager)
        write_identity_on_first = False
        if current is not None:
            with db.connection:
                ensure_legacy_identity(db.connection, current)
                check = check_identity(db.connection, current, mode="embed")
            if check.untrusted:
                stored = check.stored
                if stored is not None:
                    stored_desc = (
                        f"{stored.display_fingerprint()} "
                        f"({stored.cache_model_id}, dim {stored.dimension})"
                    )
                else:
                    stored_desc = f"an index with no identity (FLOAT[{schema_dim}])"
                raise click.ClickException(
                    "Embedder identity mismatch: index vectors were produced by "
                    f"{stored_desc} but the current model is "
                    f"{current.display_fingerprint()} "
                    f"({current.cache_model_id}, dim {current.dimension}). "
                    "Restore the stored model or run `sif index embed --force` "
                    "with the matching model."
                )
            write_identity_on_first = not _index_has_vectors(db.connection)

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

        # D-01: embed_cmd arbitrates with other index writers on the per-DB
        # flock. The lock sits below the embedder load and the dimension/
        # identity checks on purpose — it is never held across model loading.
        # Every document commits in its own short transaction (D-15), so prior
        # work stays durable on any later failure (CR-02/D-16).
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
            failed_documents: list[tuple[str, str, str]] = []
            abort_message: str | None = None
            identity_written = False

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

                chunker = create_chunker(
                    chunk_strategy,
                    max_chunk_size=token_size_to_chars(settings.chunk_size),
                    overlap=token_size_to_chars(settings.chunk_overlap),
                )

                # One searcher per collection. Construction failure (sqlite-vec
                # unavailable) is user-facing and never swallowed (D-03 fail-fast).
                # Raised outside any open transaction so it cannot roll back work
                # already committed by earlier collections (CR-02).
                try:
                    vector_searcher = VectorSearcher(db.connection, embedding_dim)
                except RuntimeError as e:
                    raise click.ClickException(f"Vector store unavailable: {e}") from e

                writer = StreamingEmbedWriter(
                    db.connection,
                    manager,
                    chunker,
                    vector_searcher,
                    current,
                    batch_size=settings.batch_size,
                    write_identity=write_identity_on_first,
                )
                try:
                    # One unindexed metadata scan per collection; judging every
                    # document against it keeps the completeness check linear.
                    embedded_by_doc = vector_searcher.get_all_embedded_chunk_ids()
                    for doc in documents:
                        # Skip documents whose live chunks already have an exact,
                        # complete set of embeddings; --force bypasses the check.
                        existing = chunk_repo.get_by_document(doc.id)
                        embedded = embedded_by_doc.get(doc.id, set())
                        if not _needs_embedding({c.id for c in existing}, embedded, force):
                            console.print(f"  [dim]Already embedded: {doc.path}[/dim]")
                            continue
                        try:
                            total_chunks += writer.embed_document(doc)
                        except SystemicEmbedError as e:
                            # D-17: a garbage batch is systemic — persist nothing
                            # for this document and abort after prior commits.
                            raise _EmbedAbortError(str(e)) from e
                        except sqlite3.OperationalError as e:
                            if "locked" in str(e).lower() or "busy" in str(e).lower():
                                # D-16: a locked/busy database is environmental.
                                raise _EmbedAbortError(
                                    "database is locked or busy. Retry once the other "
                                    f"index writer has finished ({e})."
                                ) from e
                            failed_documents.append((coll.name, doc.path, str(e)))
                        except Exception as e:
                            # D-16: document-local failures never abort the run.
                            failed_documents.append((coll.name, doc.path, str(e)))

                    # D-15 refinement: recompute collection stats once per
                    # collection in a short O(N) SQL count instead of per
                    # document. A collection that aborts mid-loop keeps its
                    # previous counts until its next successful run.
                    with db.connection:
                        coll.chunk_count = _count_collection_chunks(db.connection, coll.id)
                        coll_repo.update(coll)
                except _EmbedAbortError as e:
                    abort_message = str(e)
                except Exception as e:
                    console.print(
                        f"  [red]Error embedding collection {escape(coll.name)}: {e}[/red]"
                    )
                    failed_collections.append(coll.name)
                finally:
                    if write_identity_on_first and not writer.identity_pending:
                        # The first committed document already wrote the
                        # identity; later collections and the certification
                        # step must not rewrite it.
                        write_identity_on_first = False
                        identity_written = True

                if abort_message is not None:
                    break

        console.print(f"\n[green]Embedding complete: {total_chunks} chunks embedded[/green]")
        for coll_name, doc_path, message in failed_documents:
            console_err.print(
                f"[red]Embedding failed for {escape(doc_path)} "
                f"(collection {escape(coll_name)}): {escape(message)}[/red]"
            )

        # D-16/CR-02: ONE final report, raised outside any db transaction, so
        # every prior per-document/per-collection commit survives the non-zero
        # exit. Systemic aborts win over per-document/collection summaries.
        if abort_message is not None:
            raise click.ClickException(f"Embedding aborted: {abort_message}")
        if failed_collections or failed_documents:
            parts: list[str] = []
            if failed_collections:
                parts.append(
                    f"Embedding failed for {len(failed_collections)} collection(s): "
                    + ", ".join(failed_collections)
                )
            if failed_documents:
                parts.append(f"Embedding failed for {len(failed_documents)} document(s)")
            raise click.ClickException(". ".join(parts))

        # D-04 certification: only a complete, unfiltered, zero-failure
        # --force run certifies the stored identity as source="verified". A
        # fresh index's first vector write already certified through the
        # writer; a full --force on an empty index certifies vacuously (its
        # zero vectors keep D-02's accept-any-embedder rule in force).
        if force and collection is None and current is not None and not identity_written:
            with db.connection:
                certify_identity(db.connection, current)


def _format_bytes(size: int) -> str:
    """Render a byte count with its MiB equivalent for maintenance output."""
    return f"{size} bytes ({size / (1024 * 1024):.2f} MiB)"


@index_group.command("vacuum")
@click.pass_context
def vacuum_cmd(ctx: click.Context) -> None:
    """Reclaim unused space in the index database."""
    index_path = ctx.obj["index_path"]

    # Run schema migrations/backfills first, then close the handle: VACUUM runs
    # on the maintenance helper's own connection outside every transaction.
    with open_initialized_database(index_path, Database):
        pass

    from sif.config.settings import get_settings  # noqa: PLC0415

    settings = get_settings()
    lock_timeout = settings.lock_wait_timeout
    with index_lock(
        Path(index_path),
        lock_timeout,
        on_wait=lambda: console.print(
            f"[dim]Another index writer is running; waiting up to {lock_timeout:.0f}s...[/dim]"
        ),
    ):
        try:
            result = vacuum_index(Path(index_path), settings)
        except MaintenanceBusyError as e:
            # Retryable by design (D-14): never a traceback, never partial success.
            raise click.ClickException(str(e)) from e
        except (MaintenanceTargetError, sqlite3.Error, OSError) as e:
            raise click.ClickException(
                f"Vacuum failed: {e}. Check free disk space and file permissions, then retry."
            ) from e

    console.print("[green]Vacuum complete:[/green]")
    console.print(f"  Before: {_format_bytes(result.before_bytes)}")
    console.print(f"  After: {_format_bytes(result.after_bytes)}")
    console.print(f"  Reclaimed: {_format_bytes(result.reclaimed_bytes)}")


@index_group.command("backup")
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Destination file for the verified backup copy",
)
@click.pass_context
def backup_cmd(ctx: click.Context, output: Path | None) -> None:
    """Create a verified backup copy of the index database."""
    index_path = ctx.obj["index_path"]

    # Run schema migrations/backfills first; the copy itself is taken by the
    # maintenance helper under the index lock, outside Database.transaction().
    with open_initialized_database(index_path, Database):
        pass

    from sif.config.settings import get_settings  # noqa: PLC0415

    settings = get_settings()
    lock_timeout = settings.lock_wait_timeout
    with index_lock(
        Path(index_path),
        lock_timeout,
        on_wait=lambda: console.print(
            f"[dim]Another index writer is running; waiting up to {lock_timeout:.0f}s...[/dim]"
        ),
    ):
        try:
            result = backup_index(Path(index_path), output, settings)
        except MaintenanceBusyError as e:
            # Retryable by design (D-14): never a traceback, never partial success.
            raise click.ClickException(str(e)) from e
        except (MaintenanceTargetError, sqlite3.Error, OSError) as e:
            raise click.ClickException(str(e)) from e

    console.print("[green]Backup complete:[/green]")
    console.print(f"  Output: {result.output}")
    console.print(f"  Size: {_format_bytes(result.bytes_written)}")


@index_group.command("status")
@click.pass_context
def index_status_cmd(ctx: click.Context) -> None:
    """Show index status."""
    # Delegate to main status command
    from sif.cli.main import status_cmd  # noqa: PLC0415

    ctx.invoke(status_cmd)
