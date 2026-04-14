"""Search commands."""

from __future__ import annotations

import json
from typing import Optional

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from docsift.core.models import SearchOptions
from docsift.database.database import Database
from docsift.search.bm25 import BM25Searcher
from docsift.search.hybrid import HybridSearcher, SearchPipeline

console = Console()


def format_results_json(results: list) -> str:
    """Format results as JSON."""
    return json.dumps([r.to_dict() for r in results], indent=2, ensure_ascii=False)


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
        if r.highlights:
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
            from docsift.database.repositories import CollectionRepository
            repo = CollectionRepository(db.connection)
            options.collection_ids = []
            for name in collection:
                coll = repo.get_by_name(name)
                if coll:
                    options.collection_ids.append(coll.id)
    
    # Search
    with db.connection:
        searcher = BM25Searcher(db.connection)
        results = searcher.search(query, options)
    
    # Output results
    if output_files:
        for r in results:
            console.print(r.path)
    elif output_json:
        console.print(format_results_json(results))
    elif output_csv:
        console.print(format_results_csv(results))
    elif output_md:
        console.print(format_results_md(results, query))
    elif output_xml:
        console.print(format_results_xml(results, query))
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
        
        for r in results:
            table.add_row(
                str(r.rank),
                f"{r.score:.4f}",
                r.title[:50] + "..." if len(r.title) > 50 else r.title,
                r.collection_name,
            )
        
        console.print(table)
        
        if explain:
            console.print(f"\n[dim]Query: {query}[/dim]")
            console.print(f"[dim]Results: {len(results)}[/dim]")


@search_group.command("vsearch")
@click.argument("query")
@click.option("-n", "--limit", default=10, help="Number of results")
@click.option("-c", "--collection", multiple=True, help="Collection to search")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def vsearch_cmd(
    ctx: click.Context,
    query: str,
    limit: int,
    collection: tuple,
    output_json: bool,
) -> None:
    """Search documents using vector similarity."""
    index_path = ctx.obj["index_path"]

    if not index_path.exists():
        console.print("[yellow]No index found. Run 'docsift update' and 'docsift embed' first.[/yellow]")
        return

    from docsift.config.settings import get_settings
    from docsift.embedding.embedder import SentenceTransformerEmbedder
    from docsift.database.database import Database
    from docsift.search.vector import VectorSearcher
    from docsift.database.repositories import CollectionRepository

    settings = get_settings()

    try:
        embedder = SentenceTransformerEmbedder(model_name=settings.model_name)
    except ImportError as e:
        raise click.ClickException(f"sentence-transformers not installed: {e}")
    except Exception as e:
        raise click.ClickException(f"Failed to load embedding model: {e}")

    db = Database(index_path)
    db.init_schema()

    options = SearchOptions(limit=limit)

    if collection:
        with db.connection:
            repo = CollectionRepository(db.connection)
            options.collection_ids = []
            for name in collection:
                coll = repo.get_by_name(name)
                if coll:
                    options.collection_ids.append(coll.id)

    with db.connection:
        query_embedding = embedder.embed(query)
        searcher = VectorSearcher(db.connection, embedder.dimension)
        results = searcher.search(query_embedding, options)

    if output_json:
        console.print(format_results_json(results))
    else:
        if not results:
            console.print("[yellow]No results found.[/yellow]")
            return

        table = Table(title=f'Vector Search Results: "{query}"')
        table.add_column("#", style="cyan", justify="right")
        table.add_column("Score", style="green", justify="right")
        table.add_column("Title", style="yellow")
        table.add_column("Collection", style="blue")

        for r in results:
            table.add_row(
                str(r.rank),
                f"{r.score:.4f}",
                r.title[:50] + "..." if len(r.title) > 50 else r.title,
                r.collection_name,
            )

        console.print(table)


@search_group.command("query")
@click.argument("query")
@click.option("-n", "--limit", default=10, help="Number of results")
@click.option("-c", "--collection", multiple=True, help="Collection to search")
@click.option("--all", "search_all", is_flag=True, help="Search all collections")
@click.option("--min-score", default=0.0, help="Minimum score threshold")
@click.option("--full", is_flag=True, help="Include full content")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--csv", "output_csv", is_flag=True, help="Output as CSV")
@click.option("--md", "output_md", is_flag=True, help="Output as Markdown")
@click.option("--xml", "output_xml", is_flag=True, help="Output as XML")
@click.option("--files", "output_files", is_flag=True, help="Output file paths only")
@click.pass_context
def query_cmd(
    ctx: click.Context,
    query: str,
    limit: int,
    collection: tuple,
    search_all: bool,
    min_score: float,
    full: bool,
    output_json: bool,
    output_csv: bool,
    output_md: bool,
    output_xml: bool,
    output_files: bool,
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
    )
    
    # Get collection IDs if specified
    if collection:
        with db.connection:
            from docsift.database.repositories import CollectionRepository
            repo = CollectionRepository(db.connection)
            options.collection_ids = []
            for name in collection:
                coll = repo.get_by_name(name)
                if coll:
                    options.collection_ids.append(coll.id)
    
    # Search using hybrid approach
    with db.connection:
        searcher = HybridSearcher(db.connection)
        results = searcher.search(query, options)
    
    # Output results
    if output_files:
        for r in results:
            console.print(r.path)
    elif output_json:
        console.print(format_results_json(results))
    elif output_csv:
        console.print(format_results_csv(results))
    elif output_md:
        console.print(format_results_md(results, query))
    elif output_xml:
        console.print(format_results_xml(results, query))
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
        
        for r in results:
            table.add_row(
                str(r.rank),
                f"{r.score:.4f}",
                r.title[:50] + "..." if len(r.title) > 50 else r.title,
                r.collection_name,
            )
        
        console.print(table)
