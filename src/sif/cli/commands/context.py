"""Context management commands."""

from __future__ import annotations

from datetime import timezone

import click
from rich.console import Console
from rich.table import Table

from sif.core.models import PathContext
from sif.database.database import Database
from sif.database.repositories import CollectionRepository, ContextRepository
from sif.utils.paths import expand_path, normalize_path


console = Console()

# Display truncation constant
_CONTEXT_TRUNCATE_LEN = 50


def _merge_key(context: PathContext) -> float:
    """Tz-safe epoch-seconds sort key over ``updated_at`` for the self-heal merge.

    Rows migrated from the legacy ``path_contexts`` table can carry
    offset-less timestamps (naive datetimes); treating those as UTC keeps the
    sort total over mixed naive/aware values instead of raising TypeError on
    exactly the legacy rows the merge exists to collapse.
    """
    updated = context.updated_at
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    return updated.timestamp()


def _resolve_path_target(target: str) -> str:
    """Canonicalize a path target, raising a clean CLI error when un-expandable.

    normalize_path is total (a stored row must never crash the read paths,
    REVIEW WR-01), so an un-expandable ``~user`` typo is probed here and
    surfaced as a ``click.ClickException`` instead of storing a target that
    could never match any document — or leaking a raw traceback.
    """
    try:
        expand_path(target)
    except (RuntimeError, OSError, ValueError) as e:
        raise click.ClickException(f"Cannot resolve path '{target}': {e}") from e
    return normalize_path(target)


def _self_heal_path_row(
    repo: ContextRepository,
    typed_target: str,
    actual_target: str,
) -> PathContext | None:
    """Resolve a legacy path-context row for an explicit re-add (self-heal merge).

    Exact dual-form lookup first (the verbatim spelling the user typed
    before write-side normalization existed), then — REVIEW WR-02 —
    normalized-key resolution over all path rows, because the exact
    spellings miss the most likely re-add path: a legacy row stored under
    ANY other alias of the same file (typically re-adding via the canonical
    spelling while the legacy row holds the symlink-alias form). Every
    historical spelling is merged into one canonical row: newest
    updated_at wins, older duplicates are deleted, and no second row is
    created. normalize_path is total (WR-01), so a malformed row cannot
    crash the merge. Explicit re-add only — never a bulk migration.

    Returns:
        The merged row re-pointed to ``actual_target``, or None when no
        historical spelling exists.
    """
    existing = repo.get_by_target(typed_target, "path")
    if existing:
        repo.update_target(existing.id, actual_target)
        return existing
    candidates = sorted(
        (c for c in repo.list_by_type("path") if normalize_path(c.path) == actual_target),
        key=_merge_key,
        reverse=True,
    )
    if not candidates:
        return None
    winner, losers = candidates[0], candidates[1:]
    # Collapse duplicates only when the re-point actually landed; otherwise
    # signal "no merge" so the caller creates a fresh row rather than
    # deleting rows whose content would be lost.
    if not repo.update_target(winner.id, actual_target):
        return None
    for loser in losers:
        repo.delete(loser.id)
    return winner


@click.group("context")
def context_group() -> None:
    """Manage contextual descriptions for paths, collections, and global scope."""
    pass


@context_group.command("add")
@click.argument("type", type=click.Choice(["path", "collection", "global"]))
@click.argument("target")
@click.argument("content")
@click.pass_context
def context_add(
    ctx: click.Context,
    type: str,  # noqa: A002
    target: str,
    content: str,
) -> None:
    """Add context for a path, collection, or global scope."""
    index_path = ctx.obj["index_path"]
    db = Database(index_path)
    db.init_schema()

    with db.transaction() as conn:
        repo = ContextRepository(conn)

        # Resolve target based on type
        actual_target = target
        if type == "collection":
            coll_repo = CollectionRepository(conn)
            coll = coll_repo.get_by_name(target)
            if not coll:
                # Fallback: treat target as collection ID
                coll = coll_repo.get_by_id(target)
            if not coll:
                raise click.ClickException(f"Collection '{target}' not found")
            actual_target = coll.id
        elif type == "global":
            actual_target = "global"
        elif type == "path":
            # Canonical form: the same normalize_path used by search context
            # attachment and prune, so the stored target byte-matches
            # documents.path regardless of ~ or symlink-alias spelling.
            # Clean ClickException for an un-expandable "~user" typo
            # (REVIEW WR-01).
            actual_target = _resolve_path_target(target)

        # Upsert: update if exists for this target+type, else create
        existing = repo.get_by_target(actual_target, type)
        if not existing and type == "path":
            # Re-point a legacy row holding any historical spelling of the
            # same file instead of creating a duplicate (self-heal merge,
            # REVIEW WR-02).
            existing = _self_heal_path_row(repo, target, actual_target)
        if existing:
            existing.context = content
            repo.update(existing)
            display_target = actual_target if type == "path" else target
            console.print(f"[green]Context updated for {type} '{display_target}'[/green]")
        else:
            path_context = PathContext(
                path=actual_target,
                context=content,
                context_type=type,
            )
            repo.create(path_context)
            display_target = actual_target if type == "path" else target
            console.print(f"[green]Context added for {type} '{display_target}'[/green]")


@context_group.command("remove")
@click.argument("context_id")
@click.pass_context
def context_remove(ctx: click.Context, context_id: str) -> None:
    """Remove a context by its ID."""
    index_path = ctx.obj["index_path"]
    db = Database(index_path)
    db.init_schema()

    with db.transaction() as conn:
        repo = ContextRepository(conn)
        deleted = repo.delete(context_id)
        if not deleted:
            raise click.ClickException(f"No context found with ID '{context_id}'")

    console.print(f"[green]Context '{context_id}' removed[/green]")


@context_group.command("list")
@click.option(
    "--type",
    "context_type",
    type=click.Choice(["path", "collection", "global"]),
    help="Filter by context type",
)
@click.pass_context
def context_list(ctx: click.Context, context_type: str | None) -> None:
    """List all contexts."""
    index_path = ctx.obj["index_path"]

    if not index_path.exists():
        console.print("[yellow]No index found.[/yellow]")
        return

    db = Database(index_path)
    db.init_schema()

    with db.connection:
        repo = ContextRepository(db.connection)
        contexts = repo.list_by_type(context_type) if context_type else repo.list_all()

    if not contexts:
        console.print("[yellow]No contexts found.[/yellow]")
        return

    table = Table(title="Contexts")
    table.add_column("Type", style="magenta")
    table.add_column("Target", style="cyan")
    table.add_column("Content", style="green")

    for ctx_item in contexts:
        # Truncate long contexts for display
        content_text = ctx_item.context
        if len(content_text) > _CONTEXT_TRUNCATE_LEN:
            content_text = content_text[: _CONTEXT_TRUNCATE_LEN - 3] + "..."
        table.add_row(ctx_item.context_type, ctx_item.path, content_text)

    console.print(table)


@context_group.command("prune")
@click.pass_context
def context_prune(ctx: click.Context) -> None:
    """Remove orphaned path contexts (whose target paths no longer exist in the index)."""
    index_path = ctx.obj["index_path"]

    if not index_path.exists():
        console.print("[yellow]No index found.[/yellow]")
        return

    db = Database(index_path)
    db.init_schema()

    with db.transaction() as conn:
        repo = ContextRepository(conn)
        count = repo.delete_orphaned_paths()

    console.print(f"[green]Pruned {count} orphaned path context(s).[/green]")


# Register 'rm' as an alias for 'remove'
context_group.add_command(context_remove, name="rm")
