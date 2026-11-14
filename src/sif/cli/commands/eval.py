"""Personal evaluation commands (Phase 18, EVAL-01/EVAL-02).

``sif eval --personal`` measures search quality on the user's own indexed
corpus with three query legs: title/H1 (exact-term), body snippet
(paraphrased, overlap-budgeted), and query_log replay (stability only).
Documents are sampled deterministically, held-out widening keeps the
tuning/held-out floors, and the existing ``SearchEvaluator`` metric math
reports NDCG@10/Hit@10 per leg x language x length bucket with small-group
suppression. Table output follows the ``sif bench`` convention; ``--json``
goes through ``click.echo`` (never Rich) so the stream strict-parses.
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
from sif.search.hybrid import SearchPipeline
from sif.search.personal_bench import (
    INITIAL_SAMPLE_DOCUMENTS,
    MIN_DOCUMENTS,
    REPLAY_BIAS_NOTE,
    SUPPRESS_BELOW,
    ReplayResult,
    build_personal_report,
    ensure_heldout,
    evaluate_known_items,
    load_document_metadata,
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


def _budget_cell(counts: dict[str, Any]) -> str:
    """One per-leg budget description (fixed vocabulary, never user text)."""
    if counts["budget"] is None:
        return "exact-term" if counts["exact_term"] else "not synthesized"
    return f"Jaccard <= {counts['budget']:.2f}"


def _summary_table(payload: dict[str, Any]) -> Table:
    """The headline counts and known-item metrics table."""
    corpus = payload["corpus"]
    queries = payload["queries"]
    metrics = payload["metrics"]
    sampled = str(corpus["sampled"])
    if corpus["widened"]:
        sampled += " (widened)"
    table = Table(title="Personal Search Quality")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green", justify="right")
    table.add_row("Documents", str(corpus["documents"]))
    table.add_row("Sampled documents", sampled)
    table.add_row("Queries", str(queries["accepted"]))
    table.add_row("NDCG@10", f"{metrics['ndcg_at_10']:.4f}")
    table.add_row("Hit@10", f"{metrics['hit_at_10']:.4f}")
    table.add_row("Rejected (empty)", str(queries["rejected_empty"]))
    table.add_row("Rejected (duplicate)", str(queries["rejected_duplicate"]))
    table.add_row("Rejected (overlap)", str(queries["rejected_overlap"]))
    table.add_row("Split (tuning)", str(payload["splits"]["tuning"]))
    table.add_row("Split (held-out)", str(payload["splits"]["heldout"]))
    return table


def _legs_table(by_leg: dict[str, Any]) -> Table:
    """Per-leg accepted and rejection counts with the applied budget."""
    table = Table(title="Per-leg synthesis")
    for column in ("Leg", "Budget", "Accepted", "Empty", "Duplicate", "Overlap"):
        table.add_column(column, style="cyan" if column == "Leg" else "green")
    for leg, counts in by_leg.items():
        table.add_row(
            leg,
            _budget_cell(counts),
            str(counts["accepted"]),
            str(counts["rejected_empty"]),
            str(counts["rejected_duplicate"]),
            str(counts["rejected_overlap"]),
        )
    return table


def _groups_table(groups: list[dict[str, Any]]) -> Table:
    """One row per non-suppressed leg x language x length group."""
    table = Table(title="Groups (leg x language x length)")
    for column in ("Leg", "Language", "Length", "N", "NDCG@10", "Hit@10"):
        table.add_column(column, style="cyan")
    for group in groups:
        table.add_row(
            group["leg"],
            group["language"],
            group["length_bucket"],
            str(group["count"]),
            f"{group['ndcg_at_10']:.4f}",
            f"{group['hit_at_10']:.4f}",
        )
    return table


def _render_replay(replay: dict[str, Any]) -> None:
    """Replay counts and the CLI-only bias note (stability, never quality)."""
    baseline = "yes" if replay["baseline_available"] else "no"
    console.print(
        f"Replay (stability, not quality): queries {replay['num_queries']} "
        f"· baseline available: {baseline}"
    )
    console.print(f"[dim]{_cell(str(replay['bias']))}[/dim]")


def _render_footer(payload: dict[str, Any]) -> None:
    """Notes plus the retrieval/model identity line."""
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


def _render_personal(payload: dict[str, Any], output_json: bool) -> None:
    """Render the report as strict JSON or Rich tables.

    The CLI never recomputes a metric, split, group, or suppression: it only
    formats ``PersonalReport.to_dict()``. Every user/config-derived cell is
    truncated then markup-escaped (T-18-06); group names come from fixed
    enums.
    """
    if output_json:
        click.echo(json.dumps(payload, indent=2))
        return
    console.print(_summary_table(payload))
    console.print(_legs_table(payload["queries"]["by_leg"]))
    if payload["groups"]:
        console.print(_groups_table(payload["groups"]))
    if payload["suppressed"]:
        names = ", ".join(payload["suppressed"])
        console.print(f"[dim]Suppressed groups (N < {SUPPRESS_BELOW}): {names}[/dim]")
    _render_replay(payload["replay"])
    _render_footer(payload)


def run_personal(  # noqa: PLR0913
    index_path: Path,
    bm25_only: bool,
    limit: int,
    collection: tuple[str, ...],
    search_all: bool,
    output_json: bool,
) -> None:
    """Run the title+body personal evaluation end to end.

    Missing index and insufficient corpus/query counts exit 1 with a named
    cause and remedy; the default hybrid path loads the configured embedder
    and fails loudly when it is unavailable (D-11). Held-out widening runs
    before any search, and known-item metrics come solely from the
    per-query evaluator over title+body queries.
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
        # Bodies load only for the sampled subset; widening re-samples the
        # deterministic prefix and loads only the newly added documents.
        try:
            sampled, synthesis = ensure_heldout(metadata, db.connection)
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
        replay = ReplayResult(
            available=False,
            num_queries=0,
            baseline_available=False,
            top_k_paths={},
            bias=REPLAY_BIAS_NOTE,
        )
        notes = [
            "Known-item labels: the target document is grade 1 and all other "
            "documents grade 0; NDCG@10 is a rank-sensitive known-item metric, "
            "not a graded-relevance score.",
            "Title queries are exact-term (unbudgeted); body queries are paraphrased "
            "and rejected above a 0.60 token Jaccard against the target title plus "
            "opening text.",
            "Replay stability against a saved baseline is computed by --compare "
            "(Plan 03); a fresh run has no baseline.",
        ]
        if len(sampled) > INITIAL_SAMPLE_DOCUMENTS:
            notes.append(
                f"Sampling widened from the initial {INITIAL_SAMPLE_DOCUMENTS} "
                f"documents to {len(sampled)} to satisfy the held-out floor."
            )
        if bm25_only:
            notes.append("Retrieval mode is BM25-only (--bm25-only): no embedder was loaded.")
        elif settings.model_type in _REMOTE_MODEL_TYPES:
            notes.append(
                f"Embedding provider '{settings.model_type}' is remote-capable: "
                "synthesized query text is sent to it; --bm25-only keeps the run local."
            )
        report = build_personal_report(
            retrieval=retrieval,
            top_k=limit,
            metadata=metadata,
            sampled=sampled,
            model=model_identity,
            synthesis=synthesis,
            evaluations=evaluations,
            replay=replay,
            notes=notes,
        )
        _render_personal(report.to_dict(), output_json)


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

    With --personal, title/H1 (exact-term) and body-snippet (paraphrased,
    overlap-budgeted) known-item queries are synthesized from deterministically
    sampled documents; NDCG@10/Hit@10 are reported overall and per leg x
    language x length bucket with small-group suppression, alongside the
    query_log replay stability leg. Hybrid retrieval is the default; pass
    --bm25-only when the embed extra is unavailable (the default path fails
    loudly with an install remedy). --json emits strict JSON.
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
