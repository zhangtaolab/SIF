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
import sqlite3
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click
from pydantic import ValidationError
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from sif.cli.error_handling import open_initialized_database
from sif.config.settings import Settings, get_settings, resolve_candidate_limit
from sif.core.models import Embedder, SearchOptions, SearchResult
from sif.database.database import Database
from sif.database.repositories import CollectionRepository
from sif.embedding.manager import EmbeddingManager
from sif.search.hybrid import SearchPipeline
from sif.search.personal_bench import (
    INITIAL_SAMPLE_DOCUMENTS,
    MAX_TOP_K,
    MIN_DOCUMENTS,
    SUPPRESS_BELOW,
    ComparisonReport,
    DocumentRecord,
    PersonalReport,
    SavedRun,
    build_personal_report,
    compare_saved_run,
    ensure_heldout,
    evaluate_known_items,
    load_document_metadata,
    load_replay_queries,
    load_saved_run,
    replay_leg,
    require_matching_corpus,
    resolve_saved_targets,
    run_to_saved,
    saved_run_to_dict,
    validate_saved_run,
    write_saved_run,
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


def _has_scoped_embeddings(db: Database, collection_ids: list[str] | None) -> bool:
    """True when the scoped index has at least one vector row (WR-07).

    A cheap existence probe over ``document_embeddings`` (the vec0 metadata
    columns are unindexed, so one LIMIT 1 scan is the batching-rule shape).
    A missing vec0 table counts as no coverage — the caller's remedy names
    the embed step either way.
    """
    if collection_ids is not None and not collection_ids:
        return False
    try:
        if collection_ids is None:
            row = db.connection.execute("SELECT 1 FROM document_embeddings LIMIT 1").fetchone()
        else:
            placeholders = ", ".join("?" for _ in collection_ids)
            row = db.connection.execute(
                "SELECT 1 FROM document_embeddings de "
                "JOIN documents d ON d.id = de.document_id "
                f"WHERE d.collection_id IN ({placeholders}) LIMIT 1",
                list(collection_ids),
            ).fetchone()
    except sqlite3.OperationalError:
        return False
    return row is not None


def _require_scoped_embeddings(db: Database, collection_ids: list[str] | None) -> None:
    """Fail loudly instead of labelling BM25 results as hybrid (WR-07)."""
    if _has_scoped_embeddings(db, collection_ids):
        return
    raise click.ClickException(
        "Hybrid retrieval is the default, but the index has no embeddings in "
        "scope; results would silently be BM25-only. Build the vectors with "
        "'sif index embed' (after installing the embed extra) — or pass "
        "--bm25-only to measure the BM25 path explicitly."
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
    # The bias note is a fixed module constant, so it is never truncated —
    # the CLI-only limitation must remain readable in full.
    console.print(f"[dim]{escape(str(replay['bias']))}[/dim]")


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


def _format_ci(gate: dict[str, Any]) -> str:
    """One 95% CI cell, four decimals."""
    return f"[{gate['ci_low']:.4f}, {gate['ci_high']:.4f}]"


def _winner_cell(gate: dict[str, Any]) -> str:
    """Winner cell: improvement, regression, or no (never a silent zero)."""
    if gate.get("winner"):
        return "yes (improvement)"
    if gate.get("regression"):
        return "yes (regression)"
    return "no"


def _comparison_summary_table(comparison: dict[str, Any]) -> Table:
    """Overall, tuning, and held-out gate rows plus their paired metrics."""
    table = Table(title="Personal Search Comparison")
    for column in (
        "Scope",
        "N",
        "Baseline NDCG@10",
        "Current NDCG@10",
        "Mean delta",
        "95% CI",
        "Helped/Hurt/Unchanged",
        "Winner",
    ):
        table.add_column(column, style="cyan")
    rows = (
        (
            "Overall",
            comparison["gate"],
            comparison["baseline"]["ndcg_at_10"],
            comparison["current"]["ndcg_at_10"],
        ),
        (
            "Tuning (diagnostic)",
            comparison["splits"]["tuning"],
            comparison["splits"]["tuning"]["baseline_mean"],
            comparison["splits"]["tuning"]["current_mean"],
        ),
        (
            "Held-out",
            comparison["splits"]["heldout"],
            comparison["splits"]["heldout"]["baseline_mean"],
            comparison["splits"]["heldout"]["current_mean"],
        ),
    )
    for scope, gate, baseline, current in rows:
        table.add_row(
            scope,
            str(gate["n"]),
            f"{baseline:.4f}",
            f"{current:.4f}",
            f"{gate['mean_delta']:+.4f}",
            _format_ci(gate),
            f"{gate['helped']}/{gate['hurt']}/{gate['unchanged']}",
            _winner_cell(gate),
        )
    return table


def _comparison_context_table(comparison: dict[str, Any]) -> Table:
    """Noise floor, fingerprint match, replay stability, and mode context."""
    table = Table(title="Comparison Context")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Noise floor (1/N)", f"{comparison['gate']['noise_floor']:.4f}")
    # A mismatch refuses the comparison, so a rendered comparison matched.
    table.add_row("Corpus fingerprint match", "yes")
    replay = comparison["replay"]
    if replay["available"]:
        table.add_row(
            "Replay stability (Jaccard@10)",
            f"{replay['jaccard_at_10']:.4f}",
        )
        table.add_row(
            "Replay stability (top-1)",
            f"{replay['top1_stability']:.4f}",
        )
    else:
        table.add_row("Replay stability", "unavailable")
    table.add_row(
        "Retrieval mode",
        f"saved {comparison['retrieval']['saved']} / current {comparison['retrieval']['current']}",
    )
    table.add_row("Saved top_k", str(comparison["top_k"]))
    table.add_row(
        "Suppressed groups",
        f"{len(comparison['suppressed'])} (names on stderr)",
    )
    return table


def _comparison_groups_table(groups: list[dict[str, Any]]) -> Table:
    """One diagnostic row per non-suppressed leg x language x length group."""
    table = Table(title="Groups (diagnostic)")
    for column in (
        "Leg",
        "Language",
        "Length",
        "N",
        "Baseline NDCG@10",
        "Current NDCG@10",
        "Mean delta",
        "95% CI",
        "Helped/Hurt/Unchanged",
        "Winner",
    ):
        table.add_column(column, style="cyan")
    for group in groups:
        table.add_row(
            group["leg"],
            group["language"],
            group["length_bucket"],
            str(group["n"]),
            f"{group['baseline_mean']:.4f}",
            f"{group['current_mean']:.4f}",
            f"{group['mean_delta']:+.4f}",
            _format_ci(group),
            f"{group['helped']}/{group['hurt']}/{group['unchanged']}",
            _winner_cell(group),
        )
    return table


def _render_comparison(payload: dict[str, Any]) -> None:
    """Render a saved-vs-current comparison (tables only; JSON bypasses)."""
    comparison = payload["comparison"]
    console.print(_comparison_summary_table(comparison))
    console.print(_comparison_context_table(comparison))
    if comparison["groups"]:
        console.print(_comparison_groups_table(comparison["groups"]))
    else:
        console.print(
            f"[dim]No leg x language x length group reached the N >= {SUPPRESS_BELOW} floor.[/dim]"
        )
    _render_footer(payload)


def _render_personal(payload: dict[str, Any], output_json: bool) -> None:
    """Render the report as strict JSON or Rich tables.

    The CLI never recomputes a metric, split, group, or suppression: it only
    formats ``PersonalReport.to_dict()`` (plus the ``comparison`` object on
    ``--compare``). Every user/config-derived cell is truncated then
    markup-escaped (T-18-06); group names come from fixed enums.
    """
    if output_json:
        click.echo(json.dumps(payload, indent=2))
        return
    if "comparison" in payload:
        _render_comparison(payload)
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


def _save_run(
    report: PersonalReport,
    settings: Settings,
    no_save: bool,
) -> Path | None:
    """Write the run under ``<cache_dir>/eval`` unless ``--no-save`` (D-10).

    The envelope is validated against the loader's own contract before any
    file is created (WR-02): a run the tool cannot load again is a writer
    bug, not a saved baseline. The filename is
    ``eval-<fingerprint12>-<UTC timestamp>.json``; the write is atomic
    (sibling temp file then ``replace``) and size-capped. The path is
    announced on stderr so stdout stays pipe-clean for ``--json``.
    """
    if no_save:
        return None
    run = run_to_saved(report)
    try:
        validate_saved_run(saved_run_to_dict(run))
        cache_dir = Path(settings.get_cache_dir()) / "eval"
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        path = cache_dir / f"eval-{run.corpus['fingerprint'][:12]}-{timestamp}.json"
        write_saved_run(run, path)
    except (OSError, ValueError) as error:
        raise click.ClickException(f"Could not save the personal eval run: {error}") from error
    console_err.print(f"[dim]Saved run: {path}[/dim]", soft_wrap=True)
    return path


def _model_label(model: dict[str, Any] | None) -> str:
    """One model-identity label with saved/config text escaped (T-18-01)."""
    if model is None:
        return "no model (bm25)"
    return (
        f"{_cell(str(model['model_name']))} "
        f"({_cell(str(model['model_type']))}, {model['dimension']}d)"
    )


def _print_comparison_warnings(
    saved: SavedRun,
    comparison: ComparisonReport,
    model_identity: dict[str, Any] | None,
) -> None:
    """Every comparison caveat goes to stderr; stdout stays clean (T-18-10)."""
    if comparison.suppressed:
        console_err.print(
            f"[yellow]Suppressed groups (N < {SUPPRESS_BELOW}): "
            f"{', '.join(comparison.suppressed)}[/yellow]",
            soft_wrap=True,
        )
    if comparison.model_mismatch:
        console_err.print(
            "[yellow]Model identity differs: the saved run used "
            f"{_model_label(saved.model)}, the current run uses "
            f"{_model_label(model_identity)}. The comparison is still "
            "reported; only a corpus-fingerprint mismatch refuses one.[/yellow]",
            soft_wrap=True,
        )
    if not comparison.replay.available:
        console_err.print(
            f"[yellow]Replay stability unavailable: {comparison.replay.note}[/yellow]",
            soft_wrap=True,
        )


def _load_settings(index_path: Path) -> Settings:
    """Resolve settings after the index-existence guard (loud failures)."""
    if not index_path.exists():
        raise click.ClickException("No index found. Run 'sif index update' first.")
    try:
        return get_settings()
    except ValidationError as e:
        raise click.ClickException(str(e)) from e


def _load_saved(compare: Path | None) -> SavedRun | None:
    """Load and validate the saved run before any search (D-12)."""
    if compare is None:
        return None
    try:
        return load_saved_run(compare)
    except ValueError as e:
        raise click.ClickException(f"Compare failed: {e}") from e


def _search_fn(
    db: Database,
    embedder: Embedder | None,
    embedding_dim: int,
    options: SearchOptions,
) -> Callable[[str], list[SearchResult]]:
    """One hoisted literal-mode pipeline per run (never per query, CR-01).

    Known-item and replay text is searched literally: a document title such
    as ``vec: embedding notes`` or a logged ``hyde: ...`` query must never be
    reinterpreted as a search operator (which would abort the run without an
    embedder). ``default_search_type`` follows the measured retrieval mode so
    the pipeline performs exactly what the report labels.
    """
    pipeline = SearchPipeline(
        db.connection,
        embedder=embedder,
        embedding_dim=embedding_dim,
        default_search_type="hybrid" if embedder is not None else "bm25",
        parse_prefix=False,
    )
    return lambda query: pipeline.search(query, options)


def _save_and_render(
    report: PersonalReport,
    settings: Settings,
    no_save: bool,
    output_json: bool,
    extra: dict[str, Any] | None = None,
) -> None:
    """Serialize one report, auto-save it, and render (one writer path)."""
    payload = report.to_dict()
    if extra:
        payload.update(extra)
    run_path = _save_run(report, settings, no_save)
    payload["run_path"] = str(run_path) if run_path is not None else None
    _render_personal(payload, output_json)


def _run_fresh(  # noqa: C901, PLR0913
    db: Database,
    metadata: list[DocumentRecord],
    collection_ids: list[str] | None,
    settings: Settings,
    bm25_only: bool,
    limit: int,
    output_json: bool,
    no_save: bool,
) -> None:
    """Synthesize, evaluate, and render a fresh personal run."""
    if len(metadata) < MIN_DOCUMENTS:
        raise click.ClickException(
            f"Personal eval needs at least {MIN_DOCUMENTS} indexed documents in "
            f"scope; found {len(metadata)}. Index more documents with "
            "'sif index update' and retry."
        )
    # A hybrid-labelled run must have vectors to search; never let an
    # un-embedded index silently produce BM25 results under a hybrid label.
    if not bm25_only:
        _require_scoped_embeddings(db, collection_ids)
    # Bodies load only for the sampled subset; widening re-samples the
    # deterministic prefix and loads only the newly added documents.
    try:
        sampled, synthesis = ensure_heldout(metadata, db.connection)
    except ValueError as e:
        raise click.ClickException(str(e)) from e
    manager, embedding_dim, model_identity = _load_embedder(settings, bm25_only)
    embedder: Embedder | None = manager.model if manager is not None else None
    retrieval = "bm25" if bm25_only else "hybrid"
    options = _build_options(
        limit,
        resolve_candidate_limit(None, settings),
        settings,
        collection_ids,
    )
    try:
        with db.connection:
            search = _search_fn(db, embedder, embedding_dim, options)
            evaluations = evaluate_known_items(synthesis.queries, search)
            # Replay runs after the known-item evaluation on the same hoisted
            # pipeline and options; it never enters the metrics. The setting
            # is a global read opt-out (SIF_QUERY_HISTORY_ENABLED=0), so a
            # disabled history must never read the local query_log (WR-04).
            if settings.query_history_enabled:
                replay = replay_leg(load_replay_queries(db.connection), search)
            else:
                replay = replay_leg([], search)
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"Personal eval failed: {e}") from e
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
    if not settings.query_history_enabled:
        notes.append("Replay skipped: SIF_QUERY_HISTORY_ENABLED=0 disables query-history reads.")
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
    _save_and_render(report, settings, no_save, output_json)


def _run_compare(  # noqa: PLR0913
    db: Database,
    metadata: list[DocumentRecord],
    collection_ids: list[str] | None,
    saved: SavedRun,
    settings: Settings,
    bm25_only: bool,
    limit: int,
    output_json: bool,
    no_save: bool,
) -> None:
    """Re-evaluate the saved query set at the saved depth, then render."""
    # Refuse a different corpus and unresolvable targets before the embedder
    # loads or any search runs (T-18-09, T-18-08).
    try:
        require_matching_corpus(saved, metadata)
        resolve_saved_targets(saved, db.connection)
    except ValueError as e:
        raise click.ClickException(str(e)) from e
    if not bm25_only:
        _require_scoped_embeddings(db, collection_ids)
    manager, embedding_dim, model_identity = _load_embedder(settings, bm25_only)
    embedder: Embedder | None = manager.model if manager is not None else None
    retrieval = "bm25" if bm25_only else "hybrid"
    if limit != saved.top_k:
        console_err.print(
            "[yellow]Compare mode uses the saved run's retrieval depth "
            f"top_k={saved.top_k}; ignoring -n {limit}.[/yellow]",
            soft_wrap=True,
        )
    if retrieval != saved.retrieval:
        console_err.print(
            "[yellow]Retrieval mode differs: the saved run used "
            f"'{saved.retrieval}', the current run uses '{retrieval}'. "
            "Both modes are recorded in the comparison.[/yellow]",
            soft_wrap=True,
        )
    # Both arms evaluate at the saved depth, so -n never silently moves it.
    options = _build_options(
        saved.top_k,
        resolve_candidate_limit(None, settings),
        settings,
        collection_ids,
    )
    try:
        with db.connection:
            comparison = compare_saved_run(
                saved,
                metadata,
                _search_fn(db, embedder, embedding_dim, options),
                conn=db.connection,
                retrieval=retrieval,
                model=model_identity,
            )
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"Personal eval failed: {e}") from e
    _print_comparison_warnings(saved, comparison, model_identity)
    _save_and_render(
        comparison.current_report,
        settings,
        no_save,
        output_json,
        extra={"comparison": comparison.to_dict()},
    )


def run_personal(  # noqa: PLR0913
    index_path: Path,
    bm25_only: bool,
    limit: int,
    collection: tuple[str, ...],
    search_all: bool,
    output_json: bool,
    no_save: bool = False,
    compare: Path | None = None,
) -> None:
    """Run the personal evaluation end to end (fresh or ``--compare``).

    Missing index and insufficient corpus/query counts exit 1 with a named
    cause and remedy; the default hybrid path loads the configured embedder
    and fails loudly when it is unavailable (D-11). Held-out widening runs
    before any search, and known-item metrics come solely from the
    per-query evaluator over title+body queries. With ``--compare`` the
    saved run is loaded and validated before any search, its fingerprint and
    targets are checked before the embedder loads, and the saved query set is
    re-evaluated in saved order at the saved depth.
    """
    settings = _load_settings(index_path)
    saved = _load_saved(compare)
    with open_initialized_database(index_path, Database) as db:
        collection_ids = _resolve_collection_ids(db, collection, search_all)
        # Whole-corpus pass: metadata only, never bodies (T-18-02).
        metadata = load_document_metadata(db.connection, collection_ids)
        if saved is not None:
            _run_compare(
                db,
                metadata,
                collection_ids,
                saved,
                settings,
                bm25_only,
                limit,
                output_json,
                no_save,
            )
            return
        _run_fresh(
            db,
            metadata,
            collection_ids,
            settings,
            bm25_only,
            limit,
            output_json,
            no_save,
        )


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
    "--compare",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Compare against a saved run (evaluates its query set)",
)
@click.option(
    "--no-save",
    is_flag=True,
    help="Do not write the run to the cache directory",
)
@click.option(
    "--bm25-only",
    is_flag=True,
    help="Explicitly skip the embedder (hybrid is the default; keeps the run local)",
)
@click.option(
    "-n",
    "--limit",
    default=10,
    type=click.IntRange(1, MAX_TOP_K),
    help=f"Number of results per query (1-{MAX_TOP_K})",
)
@click.option("-c", "--collection", multiple=True, help="Collection to evaluate")
@click.option("--all", "search_all", is_flag=True, help="Evaluate all collections")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def eval_group(  # noqa: PLR0913
    ctx: click.Context,
    personal: bool,
    compare: Path | None,
    no_save: bool,
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
    loudly with an install remedy). Every run is saved under the cache
    directory unless --no-save. With --compare, a saved run is re-evaluated
    over its own query set at its saved depth and paired deltas are reported
    with a seeded 95% bootstrap CI and the 1/N noise floor; a corpus
    fingerprint mismatch refuses the comparison. --json emits strict JSON.
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
        no_save,
        compare,
    )
