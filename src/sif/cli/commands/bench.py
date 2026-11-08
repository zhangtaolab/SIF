"""Benchmark commands."""

from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from sif.config.settings import get_settings
from sif.database.database import Database
from sif.database.repositories import CollectionRepository
from sif.embedding.manager import EmbeddingManager
from sif.search.benchmark import CATEGORIES, LEGACY_K_VALUES, SearchEvaluator
from sif.search.hybrid import SearchPipeline
from sif.utils.logging import get_logger


logger = get_logger(__name__)
console = Console()


@click.command("bench")
@click.argument("fixture", type=click.Path(exists=True, path_type=Path))
@click.option("-n", "--limit", default=10, help="Number of results per query")
@click.option("-C", "--candidate-limit", default=20, help="Reranker candidate pool size")
@click.option("-c", "--collection", multiple=True, help="Collection to search")
@click.option("--all", "search_all", is_flag=True, help="Search all collections")
@click.option(
    "--model-type",
    type=click.Choice(["sentence_transformers", "gguf", "openai", "modelscope"]),
    help="Embedding model type override",
)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def bench_cmd(  # noqa: C901, PLR0913, PLR0915
    ctx: click.Context,
    fixture: Path,
    limit: int,
    candidate_limit: int,
    collection: tuple,
    search_all: bool,
    model_type: str | None,
    output_json: bool,
) -> None:
    """Run benchmark evaluation against a fixture file.

    Fixture format (JSON):
        {
            "queries": [
                {
                    "query": "search terms",
                    "relevant_docids": ["doc-id-1", "doc-id-2"],
                    "collections": ["optional-collection-filter"]
                }
            ]
        }
    """
    index_path = ctx.obj["index_path"]

    if not index_path.exists():
        console.print("[yellow]No index found. Run 'sif index update' first.[/yellow]")
        return

    # Load fixture
    with open(fixture) as f:
        fixture_data = json.load(f)

    with Database(index_path) as db:
        db.init_schema()

        # Build search function
        settings = get_settings()
        if model_type:
            settings = settings.model_copy(update={"model_type": model_type})

        # Load embedder
        manager = None
        embedding_dim = 384
        try:
            manager = EmbeddingManager.from_settings(settings)
            manager.load_model()
            embedding_dim = len(manager.embed_single("probe"))
        except ImportError as e:
            console.print(f"[yellow]Embedding backend not installed: {e}[/yellow]")
        except Exception as e:
            console.print(f"[yellow]Failed to load embedding model: {e}[/yellow]")

        def search_fn(query: str):
            from sif.core.models import SearchOptions  # noqa: PLC0415

            options = SearchOptions(
                limit=limit,
                candidate_limit=candidate_limit,
                include_content=False,
                include_highlights=False,
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

            with db.connection:
                pipeline = SearchPipeline(
                    db.connection,
                    embedder=manager._model if manager else None,  # noqa: SLF001
                    embedding_dim=embedding_dim,
                )
                return pipeline.search(query, options)

        # Run evaluation: the graded report layers nDCG@10 / Hit@10 and the
        # per-category breakdown over the legacy flat metrics (D-13).
        try:
            evaluator = SearchEvaluator(fixture_data, fixture_path=fixture)
            report = evaluator.report(search_fn)
        except Exception as e:
            raise click.ClickException(f"Benchmark failed: {e}") from e

        # Output results. JSON uses click.echo (never Rich) so it
        # strict-parses at narrow terminal widths.
        if output_json:
            click.echo(json.dumps(report.to_dict(), indent=2))
        else:
            table = Table(title=f"Benchmark Results: {fixture.name}")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green", justify="right")

            table.add_row("Queries", f"{report.num_queries}")
            table.add_row("NDCG@10", f"{report.ndcg_at_10:.4f}")
            table.add_row("Hit@10", f"{report.hit_at_10:.4f}")
            table.add_row("MRR", f"{report.legacy_metrics.get('mrr', 0.0):.4f}")
            for metric_k in LEGACY_K_VALUES:
                precision_key = f"precision@{metric_k}"
                recall_key = f"recall@{metric_k}"
                if precision_key in report.legacy_metrics:
                    table.add_row(
                        f"Precision@{metric_k}",
                        f"{report.legacy_metrics[precision_key]:.4f}",
                    )
                if recall_key in report.legacy_metrics:
                    table.add_row(
                        f"Recall@{metric_k}",
                        f"{report.legacy_metrics[recall_key]:.4f}",
                    )
            for category in CATEGORIES:
                metrics = report.categories.get(category)
                if metrics is None:
                    continue
                table.add_row(f"{category} nDCG@10", f"{metrics.ndcg_at_10:.4f}")
                table.add_row(f"{category} Hit@10", f"{metrics.hit_at_10:.4f}")
                table.add_row(f"{category} queries", f"{metrics.count}")

            console.print(table)
