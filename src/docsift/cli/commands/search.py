"""Search commands."""

from __future__ import annotations

import json

import click
from rich.console import Console
from rich.table import Table

from docsift.cli.formatters import add_line_numbers_to_results, prepend_line_numbers
from docsift.core.models import SearchOptions
from docsift.database.database import Database
from docsift.database.repositories import CollectionRepository
from docsift.search.bm25 import BM25Searcher
from docsift.search.hybrid import HybridSearcher, SearchPipeline


console = Console()


def format_results_json(results: list) -> str:
    """Format results as JSON."""
    return json.dumps(
        [r.to_dict() if hasattr(r, "to_dict") else r for r in results],
        indent=2,
        ensure_ascii=False,
    )


def format_results_csv(results: list) -> str:
    """Format results as CSV."""
    lines = ["rank,score,title,path,collection"]
    for r in results:
        lines.append(f'"{r.rank}","{r.score:.4f}","{r.title}","{r.path}","{r.collection_name}"')
    return "\n".join(lines)


def format_results_md(results: list, query: str) -> str:
    """Format results as Markdown."""
    lines = [f"# Search Results: {query}", ""]
    for r in results:
        lines.append(f"## {r.rank}. {r.title}")
        lines.append(f"- **Score:** {r.score:.4f}")
        lines.append(f"- **Path:** `{r.path}`")
        lines.append(f"- **Collection:** {r.collection_name}")
        if hasattr(r, "get") and r.get("line_numbers"):
            lines.append(f"- **Line Numbers:** `{r.get('line_numbers')}`")
        elif hasattr(r, "line_numbers") and r.line_numbers:
            lines.append(f"- **Line Numbers:** `{r.line_numbers}`")
        if hasattr(r, "highlights") and r.highlights:
            lines.append("")
            lines.append("> " + "\n> ".join(r.highlights[:3]))
        lines.append("")
    return "\n".join(lines)


def format_results_xml(results: list, query: str) -> str:
    """Format results as XML."""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', f'<search query="{query}">']
    for r in results:
        lines.append(f'  <result rank="{r.rank}" score="{r.score:.4f}">')
        lines.append(f"    <title>{r.title}</title>")
        lines.append(f"    <path>{r.path}</path>")
        lines.append(f"    <collection>{r.collection_name}</collection>")
        if hasattr(r, "get") and r.get("line_numbers"):
            lines.append(f"    <line_numbers>{r.get('line_numbers')}</line_numbers>")
        elif hasattr(r, "line_numbers") and r.line_numbers:
            lines.append(f"    <line_numbers>{r.line_numbers}</line_numbers>")
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
@click.pass_context
def search_cmd(
    ctx: click.Context,
    query: str,
    limit: int,
    collection: tuple,
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
) -> None:
    """Search documents using BM25."""
    index_path = ctx.obj["index_path"]

    if not index_path.exists():
        console.print("[yellow]No index found. Run 'docsift update' first.[/yellow]")
        return

    db = Database(index_path)
    db.init_schema()

    # Build options
    options = SearchOptions(
        limit=limit,
        min_score=min_score,
        include_content=full,
        include_highlights=True,
    )

    # Get collection IDs if specified
    if collection:
        with db.connection:
            repo = CollectionRepository(db.connection)
            options.collection_ids = []
            for name in collection:
                coll = repo.get_by_name(name)
                if coll:
                    options.collection_ids.append(coll.id)
    elif not search_all:
        with db.connection:
            repo = CollectionRepository(db.connection)
            enabled = repo.list_enabled()
            options.collection_ids = [c.id for c in enabled]

    # Search
    with db.connection:
        searcher = BM25Searcher(db.connection)
        results = searcher.search(query, options)

    # Output results
    if output_files:
        for r in results:
            console.print(r.path)
    elif output_json:
        console.print(
            format_results_json(
                add_line_numbers_to_results([r.to_dict() for r in results])
                if line_numbers
                else results
            )
        )
    elif output_csv:
        console.print(
            format_results_csv(
                add_line_numbers_to_results([r.to_dict() for r in results])
                if line_numbers
                else results
            )
        )
    elif output_md:
        console.print(
            format_results_md(
                add_line_numbers_to_results([r.to_dict() for r in results])
                if line_numbers
                else results,
                query,
            )
        )
    elif output_xml:
        console.print(
            format_results_xml(
                add_line_numbers_to_results([r.to_dict() for r in results])
                if line_numbers
                else results,
                query,
            )
        )
    else:
        # Rich table output
        if not results:
            console.print("[yellow]No results found.[/yellow]")
            return

        table = Table(title=f'Search Results: "{query}"')
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
                r.title[:50] + "..." if len(r.title) > 50 else r.title,
                r.collection_name,
            ]
            if line_numbers and getattr(r, "content", None):
                content = prepend_line_numbers(r.content)
                content = content[:200] + "..." if len(content) > 200 else content
                row.append(content)
            table.add_row(*row)

        console.print(table)

        if explain:
            console.print(f"\n[dim]Query: {query}[/dim]")
            console.print(f"[dim]Results: {len(results)}[/dim]")


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
@click.pass_context
def vsearch_cmd(
    ctx: click.Context,
    query: str,
    limit: int,
    collection: tuple,
    search_all: bool,
    min_score: float,
    full: bool,
    line_numbers: bool,
    output_json: bool,
    model_type: str | None = None,
) -> None:
    """Search documents using vector similarity."""
    index_path = ctx.obj["index_path"]

    if not index_path.exists():
        console.print(
            "[yellow]No index found. Run 'docsift update' and 'docsift embed' first.[/yellow]"
        )
        return

    from docsift.config.settings import get_settings
    from docsift.database.database import Database
    from docsift.database.repositories import CollectionRepository
    from docsift.embedding.manager import EmbeddingManager
    from docsift.search.vector import VectorSearcher

    settings = get_settings()
    if model_type:
        settings = settings.model_copy(update={"model_type": model_type})

    try:
        manager = EmbeddingManager.from_settings(settings)
        query_embedding = manager.embed_single(query)
    except ImportError as e:
        raise click.ClickException(f"Embedding backend not installed: {e}")
    except Exception as e:
        raise click.ClickException(f"Failed to load embedding model: {e}")

    db = Database(index_path)
    db.init_schema()

    options = SearchOptions(
        limit=limit,
        min_score=min_score,
        include_content=full,
        include_highlights=True,
    )

    if collection:
        with db.connection:
            repo = CollectionRepository(db.connection)
            options.collection_ids = []
            for name in collection:
                coll = repo.get_by_name(name)
                if coll:
                    options.collection_ids.append(coll.id)
    elif not search_all:
        with db.connection:
            repo = CollectionRepository(db.connection)
            enabled = repo.list_enabled()
            options.collection_ids = [c.id for c in enabled]

    with db.connection:
        searcher = VectorSearcher(db.connection, len(query_embedding))
        results = searcher.search(query_embedding, options)

    if output_json:
        console.print(
            format_results_json(
                add_line_numbers_to_results([r.to_dict() for r in results])
                if line_numbers
                else results
            )
        )
    else:
        if not results:
            console.print("[yellow]No results found.[/yellow]")
            return

        table = Table(title=f'Vector Search Results: "{query}"')
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
                r.title[:50] + "..." if len(r.title) > 50 else r.title,
                r.collection_name,
            ]
            if line_numbers and getattr(r, "content", None):
                content = prepend_line_numbers(r.content)
                content = content[:200] + "..." if len(content) > 200 else content
                row.append(content)
            table.add_row(*row)

        console.print(table)


@search_group.command("query")
@click.argument("query")
@click.option("-n", "--limit", default=10, help="Number of results")
@click.option("-c", "--collection", multiple=True, help="Collection to search")
@click.option("--all", "search_all", is_flag=True, help="Search all collections")
@click.option("--min-score", default=0.0, help="Minimum score threshold")
@click.option("--full", is_flag=True, help="Include full content")
@click.option("--explain", is_flag=True, help="Show score breakdowns across pipeline stages")
@click.option(
    "-C",
    "--candidate-limit",
    default=20,
    type=click.IntRange(1, 200),
    help="Reranker candidate pool size",
)
@click.option("--intent", help="Search intent hint for query expansion")
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
@click.pass_context
def query_cmd(
    ctx: click.Context,
    query: str,
    limit: int,
    collection: tuple,
    search_all: bool,
    min_score: float,
    full: bool,
    explain: bool,
    candidate_limit: int,
    intent: str | None,
    line_numbers: bool,
    output_json: bool,
    output_csv: bool,
    output_md: bool,
    output_xml: bool,
    output_files: bool,
    model_type: str | None = None,
) -> None:
    """Search documents using hybrid approach (BM25 + Vector + RRF).

    This is the recommended search command for best results.
    """
    index_path = ctx.obj["index_path"]

    if not index_path.exists():
        console.print("[yellow]No index found. Run 'docsift update' first.[/yellow]")
        return

    db = Database(index_path)
    db.init_schema()

    # Build options
    options = SearchOptions(
        limit=limit,
        min_score=min_score,
        include_content=full,
        include_highlights=True,
        explain=explain,
        candidate_limit=candidate_limit,
        intent=intent,
    )

    # Get collection IDs if specified
    if collection:
        with db.connection:
            repo = CollectionRepository(db.connection)
            options.collection_ids = []
            for name in collection:
                coll = repo.get_by_name(name)
                if coll:
                    options.collection_ids.append(coll.id)
    elif not search_all:
        with db.connection:
            repo = CollectionRepository(db.connection)
            enabled = repo.list_enabled()
            options.collection_ids = [c.id for c in enabled]

    # Load embedder for hybrid search
    from docsift.config.settings import get_settings
    from docsift.embedding.manager import EmbeddingManager
    from docsift.search.expansion import QueryExpansion
    from docsift.search.rerank import create_reranker
    from docsift.search.snippets import SmartSnippetExtractor

    settings = get_settings()
    if model_type:
        settings = settings.model_copy(update={"model_type": model_type})

    try:
        manager = EmbeddingManager.from_settings(settings)
        manager.load_model()
        embedding_dim = len(manager.embed_single("probe"))
    except ImportError as e:
        raise click.ClickException(f"Embedding backend not installed: {e}")
    except Exception as e:
        raise click.ClickException(f"Failed to load embedding model: {e}")

    # Create optional components
    query_expander = QueryExpansion(embedding_manager=manager)

    reranker = None
    if settings.reranker_model_name or settings.reranker_model_path:
        try:
            reranker = create_reranker(settings)
        except ImportError:
            console.print(
                "[yellow]Reranker not available. Install with: pip install -e '.[embed]'[/yellow]"
            )

    snippet_extractor = SmartSnippetExtractor(max_length=options.snippet_max_length)

    # Search using pipeline
    with db.connection:
        pipeline = SearchPipeline(
            db.connection,
            embedder=manager._model,
            query_expander=query_expander,
            reranker=reranker,
            snippet_extractor=snippet_extractor,
            embedding_dim=embedding_dim,
        )
        results = pipeline.search(query, options)

    # Output results
    if output_files:
        for r in results:
            console.print(r.path)
    elif output_json:
        console.print(
            format_results_json(
                add_line_numbers_to_results([r.to_dict() for r in results])
                if line_numbers
                else results
            )
        )
    elif output_csv:
        console.print(
            format_results_csv(
                add_line_numbers_to_results([r.to_dict() for r in results])
                if line_numbers
                else results
            )
        )
    elif output_md:
        console.print(
            format_results_md(
                add_line_numbers_to_results([r.to_dict() for r in results])
                if line_numbers
                else results,
                query,
            )
        )
    elif output_xml:
        console.print(
            format_results_xml(
                add_line_numbers_to_results([r.to_dict() for r in results])
                if line_numbers
                else results,
                query,
            )
        )
    else:
        # Rich table output
        if not results:
            console.print("[yellow]No results found.[/yellow]")
            return

        table = Table(title=f'Hybrid Search Results: "{query}"')
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
                r.title[:50] + "..." if len(r.title) > 50 else r.title,
                r.collection_name,
            ]
            if line_numbers and getattr(r, "content", None):
                content = prepend_line_numbers(r.content)
                content = content[:200] + "..." if len(content) > 200 else content
                row.append(content)
            table.add_row(*row)

        console.print(table)

        if explain:
            for r in results:
                scores_str = ", ".join(f"{k}={v:.4f}" for k, v in r.scores.items() if v is not None)
                if scores_str:
                    console.print(f"[dim]{r.title}: {scores_str}[/dim]")
