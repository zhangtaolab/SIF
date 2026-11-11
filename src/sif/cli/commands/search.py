"""Search commands."""

from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape, quoteattr

import click
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from sif.cli.formatters import add_line_numbers_to_results, prepend_line_numbers
from sif.core.models import Collection, QueryLogEntry, SearchOptions, SearchResult
from sif.database.database import Database
from sif.database.repositories import CollectionRepository, QueryLogRepository
from sif.indexing.drift import detect_drift, refresh_drifted
from sif.indexing.incremental import IncrementalResult
from sif.search.bm25 import BM25Searcher
from sif.search.hybrid import SearchPipeline
from sif.search.suggest import SuggestionEngine
from sif.utils.logging import get_logger, set_quiet


console = Console()
# D-07 stderr contract: refresh notices/warnings must never pollute stdout,
# which stays clean for --json/--csv piping (mcp.py console_err precedent).
console_err = Console(stderr=True)
logger = get_logger(__name__)

# Display truncation constants
_TITLE_MAX_LEN = 50
_CONTENT_MAX_LEN = 200

# XML 1.0 Char production (W3C REC-xml §2.2): #x9 | #xA | #xD | [#x20-#xD7FF] |
# [#xE000-#xFFFD] | [#x10000-#x10FFFF]. This class is its forbidden complement:
# #x00-#x08, #x0B, #x0C, #x0E-#x1F, surrogates #xD800-#xDFFF, #xFFFE-#xFFFF.
_XML_1_0_INVALID = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")


def _xml_sanitize(text: str) -> str:
    """Strip code points forbidden by the XML 1.0 Char production.

    Tab (#x9), LF (#xA), and CR (#xD) are preserved. #x7F-#x9F are legal per
    the production (only discouraged) and are NOT stripped.
    """
    return _XML_1_0_INVALID.sub("", text)


def _display_snippet(r: SearchResult, max_len: int = _CONTENT_MAX_LEN) -> str:
    """Return the display text for the Snippet table column.

    Prefers the pipeline-extracted snippet; falls back to the first BM25
    highlight when no snippet is present; returns the empty string when
    neither is available.
    """
    text = getattr(r, "snippet", None)
    if not text:
        highlights = getattr(r, "highlights", None) or []
        text = highlights[0] if highlights else ""
    if not text:
        return ""
    return text[:max_len] + "..." if len(text) > max_len else text


def format_results_json(results: list[Any]) -> str:
    """Format results as JSON."""
    return json.dumps(
        [r.to_dict() if hasattr(r, "to_dict") else r for r in results],
        indent=2,
        ensure_ascii=False,
    )


def _field(r: Any, name: str) -> Any:
    """Read a result field from a dict (--line-numbers path) or object row."""
    return r.get(name, "") if isinstance(r, dict) else getattr(r, name, "")


def _title_cell(r: Any) -> str:
    """Build the Title cell for a Rich table row (D-12).

    The title itself stays escape()d; a result whose vectors lag carries
    the dim inline annotation beside it — no new column. The annotation
    is a constant string (never document-derived text), so its markup is
    ours to write unescaped; only the title passes through escape().
    """
    title = str(_field(r, "title"))
    title = title[:_TITLE_MAX_LEN] + "..." if len(title) > _TITLE_MAX_LEN else title
    cell = escape(title)
    if _field(r, "vectors_stale"):
        cell += " [dim](stale vectors)[/dim]"
    return cell


def _resolve_collections(
    db: Database,
    collection: tuple[str, ...],
    search_all: bool,
) -> list[Collection]:
    """Resolve the collections a search targets, preserving trio semantics (D-04).

    ``-c`` resolves names via ``get_by_name`` (unknown names silently
    skipped — today's behavior), ``--all`` resolves every collection while
    the search itself stays unfiltered, and the default targets enabled
    collections. The returned objects feed both the search's
    ``collection_ids`` and the pre-search drift walk.
    """
    with db.connection:
        repo = CollectionRepository(db.connection)
        if collection:
            resolved: list[Collection] = []
            for name in collection:
                coll = repo.get_by_name(name)
                if coll:
                    resolved.append(coll)
            return resolved
        if search_all:
            return repo.list_all()
        return repo.list_enabled()


def _refresh_notice(result: IncrementalResult) -> str:
    """Build the D-07 under-cap refresh notice from actual outcomes (WR-02).

    Names what the refresh really did — added+updated files were refreshed,
    removed documents were removed — instead of the pre-refresh drift count,
    which claimed deletions and no-op checksum skips as "refreshed". Parse
    failures are named too (WR-01): a refresh that could not re-read a
    drifted file must never be announced as a clean one.
    """
    parts = [f"refreshed {result.added + result.updated} files"]
    if result.removed:
        parts.append(f"removed {result.removed}")
    if result.failed:
        parts.append(f"{result.failed} failed to parse")
    return f"{', '.join(parts)} (bm25) before search"


def _pre_search_refresh(
    db: Database,
    index_path: Path,
    collections: list[Collection],
    *,
    quiet: bool,
    no_refresh: bool = False,
) -> None:
    """Run the LIVE-10 pre-search drift check for one search command (D-01..D-07).

    One read-only stat walk decides; only an under-cap drift burst ever
    writes or opens the index lock. All notices ride stderr (``console_err``)
    so ``--json``/``--csv`` stdout stays pipeable, and ``-q`` suppresses
    them. ``no_refresh`` (the ``--no-refresh`` flag) and
    ``SIF_SEARCH_REFRESH_ENABLED=0`` skip the check entirely. Drift is
    never a search error (D-05): even a refresh failure only warns and the
    search proceeds on the current index.
    """
    if no_refresh:
        return
    from sif.config.settings import get_settings  # noqa: PLC0415

    try:
        settings = get_settings()
    except Exception:
        # The check is best-effort: bad global config (e.g. an invalid
        # reranker type irrelevant to BM25 search) must not break
        # `sif search`, which never touched settings before this check.
        # query/vsearch surface the same error cleanly at their own embedder
        # settings touchpoints.
        logger.debug("Pre-search refresh skipped: settings unavailable", exc_info=True)
        return
    if not settings.search_refresh_enabled:
        return
    try:
        report = detect_drift(db.connection, collections)
        if report.total_count == 0:
            # SC2 clean path: silence, no writes, no lock — decided before
            # the cap is ever consulted.
            return
        if report.total_count > settings.search_refresh_max_files:
            # D-05/D-06 count-first: no refresh, no lock — warn and search.
            if not quiet:
                console_err.print(
                    f"[yellow]index drift: {report.total_count} changed files "
                    f"exceeds the pre-search refresh cap "
                    f"({settings.search_refresh_max_files}) — run "
                    "'sif index update' to refresh; searching the current "
                    "index[/yellow]",
                )
        else:
            result = refresh_drifted(
                index_path,
                db.connection,
                {c.id: c for c in collections},
                report,
                lock_timeout=settings.lock_wait_timeout,
            )
            if not quiet:
                # WR-01: parse failures turn the dim notice into a yellow
                # warning — still exactly one stderr line (D-07), stdout
                # untouched, -q-suppressible, silent on the clean path.
                style = "yellow" if result.failed else "dim"
                console_err.print(f"[{style}]{_refresh_notice(result)}[/{style}]")
    except Exception:
        # D-05: a refresh failure surfaces as a warning; the search itself
        # proceeds on the current index.
        logger.warning(
            "Pre-search drift refresh failed; searching current index",
            exc_info=True,
        )
        if not quiet:
            console_err.print(
                "[yellow]Pre-search refresh failed; searching the current index[/yellow]",
            )


def _warn_stale_results(results: list[Any], *, quiet: bool) -> None:
    """Print the D-13 remedy hint after results when any result's vectors lag.

    Exactly one stderr line (``console_err`` — stdout stays clean for
    ``--json``/``--csv`` pipes); ``-q`` suppresses it, matching the 14-01
    notice contract. The count uses the same dual-shape ``_field`` reader
    as the format battery, so both SearchResult rows and dict rows count.
    """
    if quiet:
        return
    stale_count = sum(1 for r in results if _field(r, "vectors_stale"))
    if stale_count:
        hint = f"{stale_count} results have stale vectors — run 'sif index embed' to refresh"
        console_err.print(f"[yellow]{hint}[/yellow]")


def _zero_result_suggestions(conn: Any, query: str, results: list[Any]) -> list[str]:
    """Compute D-05 did-you-mean only when the search returned nothing (SC2).

    The engine is built on the already-open connection — the zero-result
    path is the only one that pays its cost (D-05). Any failure is fail-soft
    with a warning: a suggestion problem must never fail a search (Pitfall
    10 posture). Suggestions are display-only; the query is never rewritten.
    """
    if results:
        return []
    try:
        return SuggestionEngine(conn).did_you_mean(query)
    except Exception:
        logger.warning("Did-you-mean computation failed", exc_info=True)
        return []


def _record_query_history(
    conn: Any,
    query: str,
    results: list[Any],
    collections: list[Collection],
    settings: Any | None = None,
) -> None:
    """Persist one executed-search row, opt-out aware and fail-soft (D-08..D-10).

    ``SIF_QUERY_HISTORY_ENABLED=0`` skips the write entirely. ``search_cmd``
    has no settings object in scope, so the hook does its own best-effort
    settings read (the ``_pre_search_refresh`` precedent: unrelated bad
    config must never break BM25 search). A history failure NEVER fails the
    search — the write is short CRUD outside the flock (Phase 11 D-01).
    """
    try:
        if settings is None:
            from sif.config.settings import get_settings  # noqa: PLC0415

            settings = get_settings()
        if not settings.query_history_enabled:
            return
        QueryLogRepository(conn).add(
            QueryLogEntry(
                query=query,
                result_count=len(results),
                collections=[c.name for c in collections],
            ),
            keep=settings.query_history_limit,
        )
    except Exception:
        logger.warning("Query history write failed", exc_info=True)


def _dym_line(suggestions: list[str]) -> str:
    """Markup-safe 'Did you mean' line body for vocab-derived suggestions."""
    rendered = ", ".join(escape(suggestion) for suggestion in suggestions)
    return f"[yellow]Did you mean: {rendered}?[/yellow]"


def _print_dym_stdout(suggestions: list[str]) -> None:
    """Table-mode DYM line on stdout after 'No results found.' (T-15-06)."""
    if suggestions:
        console.print(_dym_line(suggestions))


def _print_dym_stderr(suggestions: list[str], *, quiet: bool) -> None:
    """Machine-mode DYM notice on stderr only — stdout stays pipeable."""
    if suggestions and not quiet:
        console_err.print(_dym_line(suggestions))


def _json_with_suggestions(results: list[Any], query: str, suggestions: list[str]) -> str:
    """Conditional zero-result JSON object; plain array otherwise (Pitfall 5).

    The documented ``[]`` contract is preserved when there are no
    suggestions (the no-forced-DYM case); only a zero-result search WITH
    suggestions wraps into ``{"query", "results": [], "suggestions"}``.
    """
    if not results and suggestions:
        return json.dumps(
            {"query": query, "results": [], "suggestions": suggestions},
            indent=2,
            ensure_ascii=False,
        )
    return format_results_json(results)


def format_results_csv(results: list[Any]) -> str:
    """Format results as CSV.

    Accepts raw SearchResult objects and the dict rows produced by
    add_line_numbers_to_results (--line-numbers). Uses csv.writer so
    embedded quotes and commas are escaped correctly.
    """
    buf = io.StringIO()
    # D-12: one extra column carries the staleness boolean (fixed literal).
    buf.write("rank,score,title,path,collection,vectors_stale\n")
    writer = csv.writer(buf, quoting=csv.QUOTE_ALL, lineterminator="\n")
    for r in results:
        writer.writerow(
            [
                _field(r, "rank"),
                f"{float(_field(r, 'score')):.4f}",
                _field(r, "title"),
                _field(r, "path"),
                _field(r, "collection_name"),
                "true" if _field(r, "vectors_stale") else "false",
            ],
        )
    return buf.getvalue().rstrip("\n")


def format_results_md(results: list[Any], query: str) -> str:
    """Format results as Markdown."""
    lines = [f"# Search Results: {query}", ""]
    for r in results:
        # D-12: the stale result's title line carries the inline annotation
        # (plain text, mirroring the Rich table's dim marker).
        title = f"## {_field(r, 'rank')}. {_field(r, 'title')}"
        if _field(r, "vectors_stale"):
            title += " (stale vectors)"
        lines.append(title)
        lines.append(f"- **Score:** {float(_field(r, 'score')):.4f}")
        lines.append(f"- **Path:** `{_field(r, 'path')}`")
        lines.append(f"- **Collection:** {_field(r, 'collection_name')}")
        if hasattr(r, "get") and r.get("line_numbers"):
            lines.append(f"- **Line Numbers:** `{r.get('line_numbers')}`")
        elif hasattr(r, "line_numbers") and r.line_numbers:
            lines.append(f"- **Line Numbers:** `{r.line_numbers}`")
        if hasattr(r, "highlights") and r.highlights:
            lines.append("")
            lines.append("> " + "\n> ".join(r.highlights[:3]))
        lines.append("")
    return "\n".join(lines)


def format_results_xml(results: list[Any], query: str) -> str:
    """Format results as XML."""
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f"<search query={quoteattr(_xml_sanitize(query))}>",
    ]
    for r in results:
        score = f"{float(_field(r, 'score')):.4f}"
        # D-12: fixed boolean literal attribute (T-14-06) — never
        # document-derived text, so the _xml_sanitize/quoteattr discipline
        # for the other attributes is untouched.
        stale_attr = "true" if _field(r, "vectors_stale") else "false"
        lines.append(
            f'  <result rank="{_field(r, "rank")}" score="{score}" vectors_stale="{stale_attr}">'
        )
        lines.append(f"    <title>{xml_escape(_xml_sanitize(str(_field(r, 'title'))))}</title>")
        lines.append(f"    <path>{xml_escape(_xml_sanitize(str(_field(r, 'path'))))}</path>")
        lines.append(
            f"    <collection>{xml_escape(_xml_sanitize(str(_field(r, 'collection_name'))))}"
            "</collection>"
        )
        if hasattr(r, "get") and r.get("line_numbers"):
            lines.append(
                f"    <line_numbers>{xml_escape(_xml_sanitize(str(r.get('line_numbers'))))}"
                "</line_numbers>"
            )
        elif hasattr(r, "line_numbers") and r.line_numbers:
            lines.append(
                f"    <line_numbers>{xml_escape(_xml_sanitize(str(r.line_numbers)))}</line_numbers>"
            )
        lines.append("  </result>")
    lines.append("</search>")
    return "\n".join(lines)


@click.group("search")
def search_group() -> None:
    """Search commands."""
    pass


@search_group.command("search")
@click.argument("query")
@click.option("-n", "--limit", default=10, help="Number of results")
@click.option("-c", "--collection", multiple=True, help="Collection to search")
@click.option("--all", "search_all", is_flag=True, help="Search all collections")
@click.option("--min-score", default=0.0, help="Minimum score threshold")
@click.option("--full", is_flag=True, help="Include full content")
@click.option("--explain", is_flag=True, help="Show search explanation")
@click.option("--line-numbers", is_flag=True, help="Show line numbers in content")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--csv", "output_csv", is_flag=True, help="Output as CSV")
@click.option("--md", "output_md", is_flag=True, help="Output as Markdown")
@click.option("--xml", "output_xml", is_flag=True, help="Output as XML")
@click.option("--files", "output_files", is_flag=True, help="Output file paths only")
@click.option("--no-refresh", is_flag=True, help="Skip the pre-search drift refresh check")
@click.option("-q", "--quiet", is_flag=True, help="Suppress non-error output")
@click.pass_context
def search_cmd(  # noqa: C901, PLR0912, PLR0913, PLR0915
    ctx: click.Context,
    query: str,
    limit: int,
    collection: tuple[str, ...],
    search_all: bool,
    min_score: float,
    full: bool,
    explain: bool,
    line_numbers: bool,
    output_json: bool,
    output_csv: bool,
    output_md: bool,
    output_xml: bool,
    output_files: bool,
    no_refresh: bool,
    quiet: bool,
) -> None:
    """Search documents using BM25."""
    index_path = ctx.obj["index_path"]
    quiet = quiet or ctx.obj.get("quiet", False)
    if quiet:
        set_quiet(True)

    if not index_path.exists():
        if not quiet:
            console.print("[yellow]No index found. Run 'sif index update' first.[/yellow]")
        return

    with Database(index_path) as db:
        db.init_schema()

        # Build options
        options = SearchOptions(
            limit=limit,
            min_score=min_score,
            include_content=full,
            include_highlights=True,
        )

        # Collection scope (D-04): resolve once for both the search filter
        # and the pre-search drift walk; --all keeps the search unfiltered.
        collections = _resolve_collections(db, collection, search_all)
        options.collection_ids = None if search_all else [c.id for c in collections]

        # Pre-search drift refresh (LIVE-10): after resolution, before
        # searcher construction (D-01 CLI-layer placement — bench and the
        # MCP server never see this check).
        _pre_search_refresh(
            db,
            Path(index_path),
            collections,
            quiet=quiet,
            no_refresh=no_refresh,
        )

        # Search
        with db.connection:
            searcher = BM25Searcher(db.connection)
            results = searcher.search(query, options)
            # D-05/SC2: only the zero-result path pays the DYM cost.
            suggestions = _zero_result_suggestions(db.connection, query, results)
            # D-08: one history row for an executed search (fail-soft).
            _record_query_history(db.connection, query, results, collections)

        # Output results
        if output_files or (quiet and not any([output_json, output_csv, output_md, output_xml])):
            for r in results:
                click.echo(r.path)
            _print_dym_stderr(suggestions, quiet=quiet)
        elif output_json:
            click.echo(
                _json_with_suggestions(
                    add_line_numbers_to_results([r.to_dict() for r in results])
                    if line_numbers
                    else results,
                    query,
                    suggestions,
                ),
            )
        elif output_csv:
            click.echo(
                format_results_csv(
                    add_line_numbers_to_results([r.to_dict() for r in results])
                    if line_numbers
                    else results,
                ),
            )
            _print_dym_stderr(suggestions, quiet=quiet)
        elif output_md:
            click.echo(
                format_results_md(
                    add_line_numbers_to_results([r.to_dict() for r in results])
                    if line_numbers
                    else results,
                    query,
                ),
            )
            _print_dym_stderr(suggestions, quiet=quiet)
        elif output_xml:
            click.echo(
                format_results_xml(
                    add_line_numbers_to_results([r.to_dict() for r in results])
                    if line_numbers
                    else results,
                    query,
                ),
            )
            _print_dym_stderr(suggestions, quiet=quiet)
        else:
            # Rich table output
            if not results:
                if not quiet:
                    console.print("[yellow]No results found.[/yellow]")
                    _print_dym_stdout(suggestions)
                return

            table = Table(title=f'Search Results: "{escape(query)}"')
            table.add_column("#", style="cyan", justify="right")
            table.add_column("Score", style="green", justify="right")
            table.add_column("Title", style="yellow")
            table.add_column("Collection", style="blue")
            table.add_column("Snippet", style="white")
            if line_numbers and any(getattr(r, "content", None) for r in results):
                table.add_column("Content", style="white")

            for r in results:
                row = [
                    str(r.rank),
                    f"{r.score:.4f}",
                    _title_cell(r),
                    escape(r.collection_name),
                    escape(_display_snippet(r)),
                ]
                if line_numbers and (content := getattr(r, "content", None)):
                    content = prepend_line_numbers(content)
                    if len(content) > _CONTENT_MAX_LEN:
                        content = content[:_CONTENT_MAX_LEN] + "..."
                    row.append(escape(content))
                table.add_row(*row)

            console.print(table)

            if explain:
                console.print(f"\n[dim]Query: {escape(query)}[/dim]")
                console.print(f"[dim]Results: {len(results)}[/dim]")

        # D-13: one stderr remedy hint after the results; -q suppresses it.
        _warn_stale_results(results, quiet=quiet)


@search_group.command("vsearch")
@click.argument("query")
@click.option("-n", "--limit", default=10, help="Number of results")
@click.option("-c", "--collection", multiple=True, help="Collection to search")
@click.option("--all", "search_all", is_flag=True, help="Search all collections")
@click.option("--min-score", default=0.0, help="Minimum score threshold")
@click.option("--full", is_flag=True, help="Include full content")
@click.option("--line-numbers", is_flag=True, help="Show line numbers in content")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option(
    "--model-type",
    type=click.Choice(["sentence_transformers", "gguf", "openai", "modelscope"]),
    help="Embedding model type override",
)
@click.option("--no-refresh", is_flag=True, help="Skip the pre-search drift refresh check")
@click.option("-q", "--quiet", is_flag=True, help="Suppress non-error output")
@click.pass_context
def vsearch_cmd(  # noqa: C901, PLR0912, PLR0913, PLR0915
    ctx: click.Context,
    query: str,
    limit: int,
    collection: tuple[str, ...],
    search_all: bool,
    min_score: float,
    full: bool,
    line_numbers: bool,
    output_json: bool,
    model_type: str | None = None,
    no_refresh: bool = False,
    quiet: bool = False,
) -> None:
    """Search documents using vector similarity."""
    index_path = ctx.obj["index_path"]
    quiet = quiet or ctx.obj.get("quiet", False)
    if quiet:
        set_quiet(True)

    if not index_path.exists():
        if not quiet:
            console.print(
                "[yellow]No index found. Run 'sif index update' and "
                "'sif index embed' first.[/yellow]",
            )
        return

    from pydantic import ValidationError  # noqa: PLC0415

    from sif.config.settings import get_settings  # noqa: PLC0415
    from sif.embedding.manager import EmbeddingManager  # noqa: PLC0415
    from sif.search.vector import VectorSearcher  # noqa: PLC0415

    # Same guard as query_cmd: when --index IS passed the group default
    # never runs, so this command must convert invalid config into a
    # clean ClickException itself.
    try:
        settings = get_settings()
    except ValidationError as e:
        raise click.ClickException(str(e)) from e
    if model_type:
        settings = settings.model_copy(update={"model_type": model_type})

    try:
        manager = EmbeddingManager.from_settings(settings)
        query_embedding = manager.embed_single(query)
    except ImportError as e:
        raise click.ClickException(f"Embedding backend not installed: {e}") from None
    except Exception as e:
        raise click.ClickException(f"Failed to load embedding model: {e}") from e

    with Database(index_path) as db:
        db.init_schema()

        options = SearchOptions(
            limit=limit,
            min_score=min_score,
            include_content=full,
            include_highlights=True,
        )

        # Collection scope (D-04): resolve once for both the search filter
        # and the pre-search drift walk; --all keeps the search unfiltered.
        collections = _resolve_collections(db, collection, search_all)
        options.collection_ids = None if search_all else [c.id for c in collections]

        # Pre-search drift refresh (LIVE-10): always run even when a watch
        # or daemon is live (D-03 — the check doubles as the event-overflow
        # backstop; when watch already handled everything, the stat-decides
        # walk finds zero drift).
        _pre_search_refresh(
            db,
            Path(index_path),
            collections,
            quiet=quiet,
            no_refresh=no_refresh,
        )

        with db.connection:
            searcher = VectorSearcher(db.connection, len(query_embedding))
            results = searcher.search(query_embedding, options)
            # D-05/SC2: only the zero-result path pays the DYM cost.
            suggestions = _zero_result_suggestions(db.connection, query, results)
            # D-08: one history row for an executed search (fail-soft).
            _record_query_history(db.connection, query, results, collections, settings=settings)

        if quiet and not output_json:
            for r in results:
                click.echo(r.path)
            _print_dym_stderr(suggestions, quiet=quiet)
        elif output_json:
            click.echo(
                _json_with_suggestions(
                    add_line_numbers_to_results([r.to_dict() for r in results])
                    if line_numbers
                    else results,
                    query,
                    suggestions,
                ),
            )
        else:
            if not results:
                if not quiet:
                    console.print("[yellow]No results found.[/yellow]")
                    _print_dym_stdout(suggestions)
                return

            table = Table(title=f'Vector Search Results: "{escape(query)}"')
            table.add_column("#", style="cyan", justify="right")
            table.add_column("Score", style="green", justify="right")
            table.add_column("Title", style="yellow")
            table.add_column("Collection", style="blue")
            if line_numbers and any(getattr(r, "content", None) for r in results):
                table.add_column("Content", style="white")

            for r in results:
                row = [
                    str(r.rank),
                    f"{r.score:.4f}",
                    _title_cell(r),
                    escape(r.collection_name),
                ]
                if line_numbers and (content := getattr(r, "content", None)):
                    content = prepend_line_numbers(content)
                    if len(content) > _CONTENT_MAX_LEN:
                        content = content[:_CONTENT_MAX_LEN] + "..."
                    row.append(escape(content))
                table.add_row(*row)

            console.print(table)

        # D-13: one stderr remedy hint after the results; -q suppresses it.
        _warn_stale_results(results, quiet=quiet)


@search_group.command("query")
@click.argument("query")
@click.option("-n", "--limit", default=10, help="Number of results")
@click.option("-c", "--collection", multiple=True, help="Collection to search")
@click.option("--all", "search_all", is_flag=True, help="Search all collections")
@click.option("--min-score", default=0.0, help="Minimum score threshold")
@click.option("--full", is_flag=True, help="Include full content")
@click.option("--explain", is_flag=True, help="Show score breakdowns across pipeline stages")
# A3 waiver (D-10 calls the cap setting-only): the -C flag pre-exists in the
# shipped CLI, so it is RETAINED with a settings-resolving default (None ->
# SIF_RERANK_CANDIDATE_LIMIT) rather than removed, and no other cap flag is
# added. The 1..200 Click range stays — narrowing it would be a user-visible
# breaking change — so the D-10 bound is enforced at resolution instead.
@click.option(
    "-C",
    "--candidate-limit",
    default=None,
    type=click.IntRange(1, 200),
    help="Reranker candidate pool size "
    "(default: SIF_RERANK_CANDIDATE_LIMIT or 20; clamped to 5-50)",
)
@click.option(
    "--rerank",
    is_flag=True,
    help="Rerank results (default: SIF_RERANK_ENABLED or false)",
)
@click.option("--intent", help="Search intent hint for query expansion")
@click.option(
    "--rrf-k",
    type=click.IntRange(1, None),
    default=None,
    help="RRF k constant for hybrid fusion (default: SIF_RRF_K or 60)",
)
@click.option(
    "--bm25-weight",
    type=click.FloatRange(0, min_open=True),
    default=None,
    help="BM25 fusion weight (default: SIF_BM25_WEIGHT or 1.0)",
)
@click.option(
    "--vector-weight",
    type=click.FloatRange(0, min_open=True),
    default=None,
    help="Vector fusion weight (default: SIF_VECTOR_WEIGHT or 1.0)",
)
@click.option("--line-numbers", is_flag=True, help="Show line numbers in content")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--csv", "output_csv", is_flag=True, help="Output as CSV")
@click.option("--md", "output_md", is_flag=True, help="Output as Markdown")
@click.option("--xml", "output_xml", is_flag=True, help="Output as XML")
@click.option("--files", "output_files", is_flag=True, help="Output file paths only")
@click.option(
    "--model-type",
    type=click.Choice(["sentence_transformers", "gguf", "openai", "modelscope"]),
    help="Embedding model type override",
)
@click.option("--no-refresh", is_flag=True, help="Skip the pre-search drift refresh check")
@click.option("-q", "--quiet", is_flag=True, help="Suppress non-error output")
@click.pass_context
def query_cmd(  # noqa: C901, PLR0912, PLR0913, PLR0915
    ctx: click.Context,
    query: str,
    limit: int,
    collection: tuple[str, ...],
    search_all: bool,
    min_score: float,
    full: bool,
    explain: bool,
    candidate_limit: int | None,
    intent: str | None,
    line_numbers: bool,
    output_json: bool,
    output_csv: bool,
    output_md: bool,
    output_xml: bool,
    output_files: bool,
    rrf_k: int | None = None,
    bm25_weight: float | None = None,
    vector_weight: float | None = None,
    model_type: str | None = None,
    no_refresh: bool = False,
    rerank: bool = False,
    quiet: bool = False,
) -> None:
    """Search documents using hybrid approach (BM25 + Vector + RRF).

    This is the recommended search command for best results.
    """
    index_path = ctx.obj["index_path"]
    quiet = quiet or ctx.obj.get("quiet", False)
    if quiet:
        set_quiet(True)

    if not index_path.exists():
        if not quiet:
            console.print("[yellow]No index found. Run 'sif index update' first.[/yellow]")
        return

    with Database(index_path) as db:
        db.init_schema()

        # Settings touchpoint (Phase 15: loaded above the options build so the
        # fusion knobs can resolve flag > SIF_ setting > default, D-03). When
        # --index IS passed the group default never runs, so this is the first
        # settings touchpoint and must convert invalid config itself (WR-09).
        from pydantic import ValidationError  # noqa: PLC0415

        from sif.config.settings import (  # noqa: PLC0415
            get_settings,
            resolve_candidate_limit,
        )

        try:
            settings = get_settings()
        except ValidationError as e:
            raise click.ClickException(str(e)) from e

        # Build options; fusion knobs resolve flag > SIF_ setting > default.
        # Flag defaults are None (never the literal) or precedence dies
        # (RESEARCH Pattern 3). candidate_limit resolves through the same
        # clamp the bench command uses (Plan 04), so a mocked settings object
        # can never inject a non-int into the plain SearchOptions dataclass.
        options = SearchOptions(
            limit=limit,
            min_score=min_score,
            include_content=full,
            include_highlights=True,
            explain=explain,
            candidate_limit=resolve_candidate_limit(candidate_limit, settings),
            intent=intent,
            rrf_k=rrf_k if rrf_k is not None else settings.rrf_k,
            bm25_weight=bm25_weight if bm25_weight is not None else settings.bm25_weight,
            vector_weight=(vector_weight if vector_weight is not None else settings.vector_weight),
        )

        # Collection scope (D-04): resolve once for both the search filter
        # and the pre-search drift walk; --all keeps the search unfiltered.
        collections = _resolve_collections(db, collection, search_all)
        options.collection_ids = None if search_all else [c.id for c in collections]

        # Pre-search drift refresh (LIVE-10): always run even when a watch
        # or daemon is live (D-03 — the check doubles as the event-overflow
        # backstop; when watch already handled everything, the stat-decides
        # walk finds zero drift).
        _pre_search_refresh(
            db,
            Path(index_path),
            collections,
            quiet=quiet,
            no_refresh=no_refresh,
        )

        # Load embedder for hybrid search
        from sif.embedding.manager import EmbeddingManager  # noqa: PLC0415
        from sif.search.expansion import QueryExpansion  # noqa: PLC0415
        from sif.search.rerank import create_reranker  # noqa: PLC0415
        from sif.search.snippets import SmartSnippetExtractor  # noqa: PLC0415

        if model_type:
            settings = settings.model_copy(update={"model_type": model_type})

        try:
            manager = EmbeddingManager.from_settings(settings)
            manager.load_model()
            embedding_dim = len(manager.embed_single("probe"))
        except ImportError as e:
            raise click.ClickException(f"Embedding backend not installed: {e}") from None
        except Exception as e:
            raise click.ClickException(f"Failed to load embedding model: {e}") from e
        # Create optional components
        query_expander = QueryExpansion(embedding_manager=manager)

        reranker = None
        # D-12 (Phase 16): rerank is an explicit opt-in. The gate is checked
        # BEFORE create_reranker so the off path is zero-cost by construction —
        # no model load, no optional-backend import, no weights.
        rerank_requested = rerank or settings.rerank_enabled
        if rerank_requested:
            try:
                reranker = create_reranker(settings)
            except ImportError:
                if not quiet:
                    console.print(
                        "[yellow]Reranker not available. "
                        "Install with: pip install -e '.[embed]'[/yellow]",
                    )
            # Defense in depth (REVIEW WR-09): a factory ValueError for an
            # unknown model_type must not escape as a raw traceback.
            except ValueError as e:
                raise click.ClickException(str(e)) from e

        snippet_extractor = SmartSnippetExtractor(max_length=options.snippet_max_length)

        # Search using pipeline
        with db.connection:
            pipeline = SearchPipeline(
                db.connection,
                embedder=manager.model,
                query_expander=query_expander,
                reranker=reranker,
                snippet_extractor=snippet_extractor,
                embedding_dim=embedding_dim,
            )
            try:
                results = pipeline.search(query, options)
            except RuntimeError as e:
                raise click.ClickException(str(e)) from e
            # D-05/SC2: only the zero-result path pays the DYM cost; the hook
            # rides the post-results path and leaves WR-02 construction alone.
            suggestions = _zero_result_suggestions(db.connection, query, results)
            # D-08: one history row for an executed search (fail-soft).
            _record_query_history(db.connection, query, results, collections, settings=settings)

        # Output results
        if output_files or (quiet and not any([output_json, output_csv, output_md, output_xml])):
            for r in results:
                click.echo(r.path)
            _print_dym_stderr(suggestions, quiet=quiet)
        elif output_json:
            click.echo(
                _json_with_suggestions(
                    add_line_numbers_to_results([r.to_dict() for r in results])
                    if line_numbers
                    else results,
                    query,
                    suggestions,
                ),
            )
        elif output_csv:
            click.echo(
                format_results_csv(
                    add_line_numbers_to_results([r.to_dict() for r in results])
                    if line_numbers
                    else results,
                ),
            )
            _print_dym_stderr(suggestions, quiet=quiet)
        elif output_md:
            click.echo(
                format_results_md(
                    add_line_numbers_to_results([r.to_dict() for r in results])
                    if line_numbers
                    else results,
                    query,
                ),
            )
            _print_dym_stderr(suggestions, quiet=quiet)
        elif output_xml:
            click.echo(
                format_results_xml(
                    add_line_numbers_to_results([r.to_dict() for r in results])
                    if line_numbers
                    else results,
                    query,
                ),
            )
            _print_dym_stderr(suggestions, quiet=quiet)
        else:
            # Rich table output
            if not results:
                if not quiet:
                    console.print("[yellow]No results found.[/yellow]")
                    _print_dym_stdout(suggestions)
                return

            table = Table(title=f'Hybrid Search Results: "{escape(query)}"')
            table.add_column("#", style="cyan", justify="right")
            table.add_column("Score", style="green", justify="right")
            table.add_column("Title", style="yellow")
            table.add_column("Collection", style="blue")
            table.add_column("Snippet", style="white")
            if line_numbers and any(getattr(r, "content", None) for r in results):
                table.add_column("Content", style="white")

            for r in results:
                row = [
                    str(r.rank),
                    f"{r.score:.4f}",
                    _title_cell(r),
                    escape(r.collection_name),
                    escape(_display_snippet(r)),
                ]
                if line_numbers and (content := getattr(r, "content", None)):
                    content = prepend_line_numbers(content)
                    if len(content) > _CONTENT_MAX_LEN:
                        content = content[:_CONTENT_MAX_LEN] + "..."
                    row.append(escape(content))
                table.add_row(*row)

            console.print(table)

            if explain:
                for r in results:
                    scores_str = ", ".join(
                        f"{k}={v:.4f}" for k, v in r.scores.items() if v is not None
                    )
                    if scores_str:
                        console.print(f"[dim]{escape(r.title)}: {scores_str}[/dim]")

        # D-13: one stderr remedy hint after the results; -q suppresses it.
        _warn_stale_results(results, quiet=quiet)
