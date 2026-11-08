"""Benchmark commands."""

from __future__ import annotations

import json
import time
from pathlib import Path

import click
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from sif.config.settings import Settings, get_settings
from sif.core.models import SearchOptions
from sif.database.database import Database
from sif.database.repositories import CollectionRepository
from sif.embedding.manager import EmbeddingManager
from sif.search.benchmark import CATEGORIES, LEGACY_K_VALUES, BenchReport, SearchEvaluator
from sif.search.hybrid import SearchPipeline
from sif.utils.logging import get_logger


logger = get_logger(__name__)
console = Console()


def _load_embedder(
    settings: Settings,
    model_type: str | None,
) -> tuple[EmbeddingManager | None, int]:
    """Load the embedding model; soft-fail to BM25-only bench on error."""
    if model_type:
        settings = settings.model_copy(update={"model_type": model_type})
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
    return manager, embedding_dim


def _resolve_collection_ids(
    db: Database,
    collection: tuple[str, ...],
    search_all: bool,
) -> list[str] | None:
    """Resolve the collection scope once for the whole run.

    None = unfiltered (--all); otherwise explicit -c names, falling back to
    every enabled collection.
    """
    with db.connection:
        repo = CollectionRepository(db.connection)
        if collection:
            ids: list[str] = []
            for name in collection:
                coll = repo.get_by_name(name)
                if coll:
                    ids.append(coll.id)
            return ids
        if not search_all:
            return [c.id for c in repo.list_enabled()]
        return None


def _build_options(
    limit: int,
    candidate_limit: int,
    settings: Settings,
    collection_ids: list[str] | None,
) -> SearchOptions:
    """Baseline options: fusion knobs resolve from the current SIF_ settings.

    A no-sweep bench run IS the current-settings baseline (D-09, fixing the
    Phase 15 IN-02 finding that bench ignored the fusion settings).
    """
    return SearchOptions(
        limit=limit,
        candidate_limit=candidate_limit,
        include_content=False,
        include_highlights=False,
        collection_ids=collection_ids,
        rrf_k=settings.rrf_k,
        bm25_weight=settings.bm25_weight,
        vector_weight=settings.vector_weight,
    )


def _measure_state(
    db: Database,
    manager: EmbeddingManager | None,
    embedding_dim: int,
    options: SearchOptions,
    evaluator: SearchEvaluator,
) -> BenchReport:
    """Measure one configuration: one hoisted pipeline, warmed per-query timing.

    The pipeline is built once per measured state inside the connection
    context (never per query), so latency measures search rather than
    pipeline re-initialization.
    """
    with db.connection:
        pipeline = SearchPipeline(
            db.connection,
            embedder=manager._model if manager else None,  # noqa: SLF001
            embedding_dim=embedding_dim,
        )
        return evaluator.report(
            lambda query: pipeline.search(query, options),
            clock=time.perf_counter,
        )


def _render_report(report: BenchReport, fixture_name: str, output_json: bool) -> None:
    """Render the report as JSON or a Rich table.

    JSON goes through click.echo (never Rich) so it strict-parses at narrow
    terminal widths; the table carries the per-category breakdown.
    """
    if output_json:
        click.echo(json.dumps(report.to_dict(), indent=2))
        return
    table = Table(title=f"Benchmark Results: {fixture_name}")
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
    table.add_row("p50 (ms)", f"{report.p50_ms:.2f}")
    table.add_row("p95 (ms)", f"{report.p95_ms:.2f}")
    if report.cold_start_ms is not None:
        table.add_row("Cold start (ms)", f"{report.cold_start_ms:.2f}")
    for category in CATEGORIES:
        metrics = report.categories.get(category)
        if metrics is None:
            continue
        table.add_row(f"{category} nDCG@10", f"{metrics.ndcg_at_10:.4f}")
        table.add_row(f"{category} Hit@10", f"{metrics.hit_at_10:.4f}")
        table.add_row(f"{category} queries", f"{metrics.count}")

    console.print(table)


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
def bench_cmd(  # noqa: PLR0913
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

    Graded fixtures (Phase 16) instead declare corpus_root/relevance_key and
    per-query category/split/relevance; the report layers nDCG@10, Hit@10,
    warmed p50/p95 latency and a per-category breakdown over the legacy flat
    metrics.
    """
    index_path = ctx.obj["index_path"]

    if not index_path.exists():
        console.print("[yellow]No index found. Run 'sif index update' first.[/yellow]")
        return

    # Load fixture
    with open(fixture) as f:
        fixture_data = json.load(f)

    # A no-sweep bench run uses the current SIF_ settings as its
    # configuration (D-09, fixes Phase 15 IN-02); invalid config surfaces as
    # a ClickException rather than a raw traceback.
    try:
        settings = get_settings()
    except ValidationError as e:
        raise click.ClickException(str(e)) from e

    with Database(index_path) as db:
        db.init_schema()

        manager, embedding_dim = _load_embedder(settings, model_type)
        collection_ids = _resolve_collection_ids(db, collection, search_all)
        options = _build_options(limit, candidate_limit, settings, collection_ids)
        try:
            evaluator = SearchEvaluator(fixture_data, fixture_path=fixture)
            report = _measure_state(db, manager, embedding_dim, options, evaluator)
        except Exception as e:
            raise click.ClickException(f"Benchmark failed: {e}") from e
        _render_report(report, fixture.name, output_json)
