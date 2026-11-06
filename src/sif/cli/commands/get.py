"""Document retrieval commands."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.markup import escape

from sif.cli.formatters import prepend_line_numbers
from sif.core.models import Document
from sif.database.database import Database
from sif.database.repositories import DocumentRepository
from sif.utils.paths import normalize_path


console = Console()


@click.group("get")
def get_group() -> None:
    """Retrieve documents."""
    pass


@get_group.command("get")
@click.argument("path_or_docid")
@click.option("--from-line", "-f", type=int, help="Start from line number")
@click.option("--lines", "-l", type=int, help="Number of lines to show")
@click.option("--line-numbers", is_flag=True, help="Show line numbers")
@click.pass_context
def get_cmd(  # noqa: C901, PLR0912, PLR0915
    ctx: click.Context,
    path_or_docid: str,
    from_line: int | None,
    lines: int | None,
    line_numbers: bool,
) -> None:
    """Get a document by path or document ID.

    Path arguments are canonicalized (~ expansion and symlink resolution)
    before lookup, so alias paths that resolve to the same file as the
    indexed path also match. If no indexed document matches, the argument
    is treated as a filesystem path: a readable file is printed directly
    from disk even if it was never indexed.
    """
    index_path = ctx.obj["index_path"]

    if not index_path.exists():
        console.print("[yellow]No index found.[/yellow]")
        return

    with Database(index_path) as db:
        db.init_schema()

        with db.connection:
            doc_repo = DocumentRepository(db.connection)

            # Try to find by ID first
            doc = doc_repo.get_by_id(path_or_docid)

            if not doc:
                # Try to find by path — canonicalized so symlink-alias paths
                # (e.g. /tmp vs /private/tmp) match the stored resolved form.
                # Need collection ID - search all collections
                from sif.database.repositories import CollectionRepository  # noqa: PLC0415

                coll_repo = CollectionRepository(db.connection)

                for coll in coll_repo.list_all():
                    doc = doc_repo.get_by_path(normalize_path(path_or_docid), coll.id)
                    if doc:
                        break

            if not doc:
                # Try matching by filename (short name lookup)
                doc = doc_repo.get_by_filename(path_or_docid)

            if not doc:
                # Try as file path
                path = Path(path_or_docid)
                if path.exists():
                    try:
                        content = path.read_text()
                        # Honor the same line filtering/numbering contract
                        # as the indexed path (CR-02: these were silently
                        # ignored on the fallback, dumping unbounded output).
                        if from_line is not None or lines is not None:
                            content_lines = content.split("\n")
                            start = max(0, (from_line or 1) - 1)
                            if lines is not None:
                                content_lines = content_lines[start : start + lines]
                            else:
                                content_lines = content_lines[start:]
                            content = "\n".join(content_lines)
                        if line_numbers:
                            content = prepend_line_numbers(content)
                        # Header interpolates user-derived path text into a
                        # markup-enabled line — escape it (10-delta CR-01).
                        console.print(f"[bold]{escape(str(path))}[/bold]")
                        # Document content is data, not markup — print raw so
                        # bracket sequences render literally instead of being
                        # consumed or raising MarkupError (CR-01).
                        console.print(content, markup=False)
                        return
                    except Exception as e:
                        raise click.ClickException(f"Cannot read file: {e}") from e

                raise click.ClickException(f"Document not found: {path_or_docid}")

            # Display document. Header lines interpolate user-derived title /
            # filename / path text into markup-enabled strings — escape the
            # values, keep the styling tags (10-delta CR-01; 04-06/05-10
            # escape() precedent).
            console.print(f"[bold cyan]{escape(doc.title or doc.filename)}[/bold cyan]")
            console.print(f"[dim]Path: {escape(doc.path)}[/dim]")
            console.print(f"[dim]Collection: {escape(doc.collection_id)}[/dim]")
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

            if line_numbers:
                content = prepend_line_numbers(content)

            # Document content is data, not markup — print raw so bracket
            # sequences render literally instead of being consumed or raising
            # MarkupError (CR-01). The former markdown/else branches were
            # byte-identical calls; collapsed to the single raw print.
            console.print(content, markup=False)


@get_group.command("multi-get")
@click.argument("pattern")
@click.option("--max-bytes", "-b", type=int, default=100000, help="Max bytes per file")
@click.option("--line-numbers", is_flag=True, help="Show line numbers")
@click.pass_context
def multi_get_cmd(  # noqa: C901
    ctx: click.Context,
    pattern: str,
    max_bytes: int,
    line_numbers: bool,
) -> None:
    """Get multiple documents matching a pattern.

    Absolute glob patterns are canonicalized before path matching, so
    symlinked directory prefixes match indexed paths; bare filenames always
    match raw.
    """
    index_path = ctx.obj["index_path"]

    if not index_path.exists():
        console.print("[yellow]No index found.[/yellow]")
        return

    import fnmatch  # noqa: PLC0415

    with Database(index_path) as db:
        db.init_schema()

        with db.connection:
            doc_repo = DocumentRepository(db.connection)
            from sif.database.repositories import CollectionRepository  # noqa: PLC0415

            coll_repo = CollectionRepository(db.connection)

            matched_docs: list[Document] = []

            def _lookup_by_id_or_path_or_filename(item: str) -> Document | None:
                """Try ID, then exact path, then filename match."""
                doc = doc_repo.get_by_id(item)
                if doc:
                    return doc
                for coll in coll_repo.list_all():
                    # Canonicalized so symlink-alias paths match stored rows.
                    doc = doc_repo.get_by_path(normalize_path(item), coll.id)
                    if doc:
                        return doc
                return doc_repo.get_by_filename(item)

            if "," in pattern:
                # Comma-separated IDs/paths
                items = [item.strip() for item in pattern.split(",") if item.strip()]
                seen_ids: set[str] = set()
                for item in items:
                    doc = _lookup_by_id_or_path_or_filename(item)
                    if doc and doc.id not in seen_ids:
                        matched_docs.append(doc)
                        seen_ids.add(doc.id)
            elif "*" in pattern or "?" in pattern:
                # Glob pattern: raw pattern first (relative patterns and
                # hand-migrated rows), then a canonicalized pattern whose
                # symlinked directory prefixes match resolved stored paths.
                normalized_pattern = normalize_path(pattern)
                for coll in coll_repo.list_all():
                    matched_docs.extend(
                        doc
                        for doc in doc_repo.list_by_collection(coll.id)
                        if fnmatch.fnmatch(doc.path, pattern)
                        or fnmatch.fnmatch(doc.filename, pattern)
                        or fnmatch.fnmatch(doc.path, normalized_pattern)
                    )
            else:
                # Single item
                doc = _lookup_by_id_or_path_or_filename(pattern)
                if doc:
                    matched_docs.append(doc)

            if not matched_docs:
                console.print(f"[yellow]No documents matching pattern: {pattern}[/yellow]")
                return

            console.print(f"[green]Found {len(matched_docs)} matching document(s)[/green]")
            console.print("")

            for doc in matched_docs:
                content = doc.content
                if len(content.encode()) > max_bytes:
                    content = content[:max_bytes] + "\n... [truncated]"

                if line_numbers:
                    content = prepend_line_numbers(content)

                # Escape the user-derived path in the markup-enabled header
                # (10-delta CR-01) — a bracketed filename must not abort the
                # batch or have segments consumed.
                console.print(f"[bold cyan]=== {escape(doc.path)} ===[/bold cyan]")
                # Raw content print (CR-01): also protects the literal
                # "... [truncated]" marker added above from markup parsing.
                console.print(content, markup=False)
                console.print("")
