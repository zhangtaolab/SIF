"""Personal evaluation commands (Phase 18, EVAL-01).

``sif eval --personal`` measures search quality on the user's own indexed
corpus: documents are sampled deterministically, one title/H1 known-item
query is synthesized per sampled document, and the existing
``SearchEvaluator`` metric math reports NDCG@10/Hit@10. Table output follows
the ``sif bench`` convention; ``--json`` goes through ``click.echo`` (never
Rich) so the stream strict-parses.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click
from pydantic import ValidationError
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from sif.cli.error_handling import open_initialized_database
from sif.config.settings import Settings, get_settings, resolve_candidate_limit
from sif.core.models import Embedder, SearchOptions
from sif.database.database import Database
from sif.database.repositories import CollectionRepository
from sif.embedding.manager import EmbeddingManager
from sif.search.benchmark import QueryEvaluation
from sif.search.hybrid import SearchPipeline
from sif.search.personal_bench import (
    MIN_DOCUMENTS,
    SynthesisResult,
    corpus_fingerprint,
    evaluate_known_items,
    load_document_metadata,
    require_minimum_queries,
    sample_documents,
    synthesize_title_queries,
)
from sif.utils.logging import get_logger


logger = get_logger(__name__)
console = Console()
# stderr contract (bench.py precedent): warnings and disclosures must never
# pollute stdout, which stays clean for `sif eval --personal --json | jq`.
console_err = Console(stderr=True)

# Remote-capable embedding backends: synthesized query text crosses the
# machine boundary, so the run discloses it and names the local alternative
# (T-18-15, D-11).
_REMOTE_MODEL_TYPES = frozenset({"openai", "modelscope"})

# Truncate then escape one config/user-derived cell (T-18-01, suggest.py
# `_cell` convention): the cap applies to raw text, the escape then keeps
# bracket sequences literal in the markup-parsed console.
_CELL_MAX_LEN = 80

_EMBED_REMEDY = (
    "Personal eval defaults to hybrid retrieval, but the embedding backend is not "
    'installed. Install it with: pip install "docsif[embed]" — or pass --bm25-only.'
)


def _cell(text: str) -> str:
    """Truncate then escape one user/config-derived cell (T-18-01)."""
    if len(text) > _CELL_MAX_LEN:
        text = text[: _CELL_MAX_LEN - 3] + "..."
    return escape(text)


def _mean(values: list[float]) -> float:
    """Arithmetic mean; empty input yields 0.0 (house style)."""
    return sum(values) / len(values) if values else 0.0


def _resolve_collection_ids(
    db: Database,
    collection: tuple[str, ...],
    search_all: bool,
) -> list[str] | None:
    """Resolve the collection scope once for the whole run (bench.py shape).

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
    """Build search options from the current SIF_ fusion settings (bench.py)."""
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


def _load_embedder(
    settings: Settings,
    bm25_only: bool,
) -> tuple[EmbeddingManager | None, int, dict[str, Any] | None]:
    """Load the hybrid-default embedder; fail loudly with the remedy (D-11).

    Unlike ``sif bench``'s soft-fail, a measurement command must fail loudly:
    a missing backend raises the exact ``pip install "docsif[embed]"`` remedy
    and names ``--bm25-only`` as the local path. ``--bm25-only`` returns
    before touching ``EmbeddingManager`` at all.
    """
    if bm25_only:
        return None, settings.embedding_dim, None
    try:
        manager = EmbeddingManager.from_settings(settings)
        manager.load_model()
    except ImportError as e:
        raise click.ClickException(_EMBED_REMEDY) from e
    except Exception as e:
        raise click.ClickException(
            f"Failed to load the embedding model: {e}. "
            "Fix the model configuration or pass --bm25-only."
        ) from e
    # IN-07 precedent (bench.py): prefer the loaded model's metadata dimension;
    # probe only when it has no usable integer dimension.
    model_dim = manager.get_model_info().get("embedding_dim")
    embedding_dim = model_dim if isinstance(model_dim, int) else len(manager.embed_single("probe"))
    identity: dict[str, Any] = {
        "model_name": settings.model_name,
        "model_type": settings.model_type,
        "dimension": embedding_dim,
    }
    if settings.model_type in _REMOTE_MODEL_TYPES:
        console_err.print(
            f"[yellow]Embedding provider '{settings.model_type}' is remote-capable: "
            "synthesized query text is sent to the configured provider. "
            "Pass --bm25-only to keep the run local.[/yellow]"
        )
    return manager, embedding_dim, identity


def _personal_payload(  # noqa: PLR0913
    *,
    retrieval: str,
    documents: int,
    sampled: int,
    fingerprint: str,
    model: dict[str, Any] | None,
    synthesis: SynthesisResult,
    evaluations: list[QueryEvaluation],
    notes: list[str],
) -> dict[str, Any]:
    """Build the strict-JSON payload with integer counts and no content keys."""
    return {
        "mode": "personal",
        "retrieval": retrieval,
        "corpus": {
            "documents": documents,
            "sampled": sampled,
            "fingerprint": fingerprint,
        },
        "model": model,
        "queries": {
            "accepted": len(synthesis.queries),
            # Per-leg tallies (Plan 02); the Plan 01 flat keys stay integer
            # totals so existing JSON consumers do not move.
            "rejected_empty": sum(synthesis.rejected_empty.values()),
            "rejected_duplicate": sum(synthesis.rejected_duplicate.values()),
        },
        "metrics": {
            "ndcg_at_10": _mean([evaluation.ndcg_at_10 for evaluation in evaluations]),
            "hit_at_10": _mean([evaluation.hit_at_10 for evaluation in evaluations]),
            "num_queries": len(evaluations),
        },
        "notes": notes,
    }


def _render_personal(payload: dict[str, Any], output_json: bool) -> None:
    """Render the personal report as strict JSON or a Rich metric table.

    Every table cell is a count or a metric — never a title, path, or body.
    The model identity line is truncated and markup-escaped because the model
    name/type come from user configuration (T-18-01).
    """
    if output_json:
        click.echo(json.dumps(payload, indent=2))
        return
    corpus = payload["corpus"]
    queries = payload["queries"]
    metrics = payload["metrics"]
    table = Table(title="Personal Search Quality")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green", justify="right")
    table.add_row("Documents", str(corpus["documents"]))
    table.add_row("Sampled documents", str(corpus["sampled"]))
    table.add_row("Queries", str(queries["accepted"]))
    table.add_row("NDCG@10", f"{metrics['ndcg_at_10']:.4f}")
    table.add_row("Hit@10", f"{metrics['hit_at_10']:.4f}")
    table.add_row("Rejected (empty title)", str(queries["rejected_empty"]))
    table.add_row("Rejected (duplicate)", str(queries["rejected_duplicate"]))
    console.print(table)
    for note in payload["notes"]:
        console.print(f"[dim]{_cell(str(note))}[/dim]")
    model = payload["model"]
    mode_line = f"Retrieval mode: {payload['retrieval']}"
    if model is not None:
        mode_line += (
            f" · model: {_cell(str(model['model_name']))} "
            f"({_cell(str(model['model_type']))}, {model['dimension']}d)"
        )
    console.print(mode_line)


def run_personal(  # noqa: PLR0913
    index_path: Path,
    bm25_only: bool,
    limit: int,
    collection: tuple[str, ...],
    search_all: bool,
    output_json: bool,
) -> None:
    """Run the title-leg personal evaluation end to end.

    Missing index and insufficient corpus/query counts exit 1 with a named
    cause and remedy; the default hybrid path loads the configured embedder
    and fails loudly when it is unavailable (D-11).
    """
    if not index_path.exists():
        raise click.ClickException("No index found. Run 'sif index update' first.")
    try:
        settings = get_settings()
    except ValidationError as e:
        raise click.ClickException(str(e)) from e

    with open_initialized_database(index_path, Database) as db:
        collection_ids = _resolve_collection_ids(db, collection, search_all)
        # Whole-corpus pass: metadata only, never bodies (T-18-02).
        metadata = load_document_metadata(db.connection, collection_ids)
        if len(metadata) < MIN_DOCUMENTS:
            raise click.ClickException(
                f"Personal eval needs at least {MIN_DOCUMENTS} indexed documents in "
                f"scope; found {len(metadata)}. Index more documents with "
                "'sif index update' and retry."
            )
        sampled = sample_documents(metadata)
        synthesis = synthesize_title_queries(sampled)
        try:
            require_minimum_queries(synthesis)
        except ValueError as e:
            raise click.ClickException(str(e)) from e

        manager, embedding_dim, model_identity = _load_embedder(settings, bm25_only)
        embedder: Embedder | None = manager.model if manager is not None else None
        options = _build_options(
            limit,
            resolve_candidate_limit(None, settings),
            settings,
            collection_ids,
        )
        # One hoisted pipeline per run (never per query); search failures
        # surface as a ClickException rather than a raw traceback.
        try:
            with db.connection:
                pipeline = SearchPipeline(
                    db.connection,
                    embedder=embedder,
                    embedding_dim=embedding_dim,
                )
                evaluations = evaluate_known_items(
                    synthesis.queries,
                    lambda query: pipeline.search(query, options),
                )
        except click.ClickException:
            raise
        except Exception as e:
            raise click.ClickException(f"Personal eval failed: {e}") from e

        retrieval = "bm25" if bm25_only else "hybrid"
        notes = [
            "Known-item labels: the target document is grade 1 and all other "
            "documents grade 0; NDCG@10 is a rank-sensitive known-item metric, "
            "not a graded-relevance score.",
        ]
        if bm25_only:
            notes.append("Retrieval mode is BM25-only (--bm25-only): no embedder was loaded.")
        elif settings.model_type in _REMOTE_MODEL_TYPES:
            notes.append(
                f"Embedding provider '{settings.model_type}' is remote-capable: "
                "synthesized query text is sent to it; --bm25-only keeps the run local."
            )
        payload = _personal_payload(
            retrieval=retrieval,
            documents=len(metadata),
            sampled=len(sampled),
            fingerprint=corpus_fingerprint(metadata),
            model=model_identity,
            synthesis=synthesis,
            evaluations=evaluations,
            notes=notes,
        )
        _render_personal(payload, output_json)


def _index_path(ctx: click.Context) -> Path:
    """Resolve the index path from the root CLI callback (settings fallback)."""
    ctx.ensure_object(dict)
    index_path = ctx.obj.get("index_path")
    if index_path is not None:
        return Path(index_path)
    try:
        return get_settings().get_db_path()
    except ValidationError as e:
        raise click.ClickException(str(e)) from e


@click.group("eval", invoke_without_command=True)
@click.option("--personal", is_flag=True, help="Measure quality on the indexed personal corpus")
@click.option(
    "--bm25-only",
    is_flag=True,
    help="Explicitly skip the embedder (hybrid is the default; keeps the run local)",
)
@click.option("-n", "--limit", default=10, help="Number of results per query")
@click.option("-c", "--collection", multiple=True, help="Collection to evaluate")
@click.option("--all", "search_all", is_flag=True, help="Evaluate all collections")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def eval_group(  # noqa: PLR0913
    ctx: click.Context,
    personal: bool,
    bm25_only: bool,
    limit: int,
    collection: tuple[str, ...],
    search_all: bool,
    output_json: bool,
) -> None:
    """Measure search quality on your own indexed corpus.

    With --personal, one title/H1 known-item query is synthesized per
    deterministically sampled document and NDCG@10/Hit@10 are reported from
    the existing evaluator metric math. Hybrid retrieval is the default;
    pass --bm25-only when the embed extra is unavailable (the default path
    fails loudly with an install remedy). --json emits strict JSON.
    """
    if ctx.invoked_subcommand is not None:
        return
    if not personal:
        raise click.UsageError("--personal is required (or pass a subcommand)")
    run_personal(
        _index_path(ctx),
        bm25_only,
        limit,
        collection,
        search_all,
        output_json,
    )
