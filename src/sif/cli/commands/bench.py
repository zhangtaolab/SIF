"""Benchmark commands."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, replace
from pathlib import Path

import click
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from sif.cli.error_handling import open_initialized_database
from sif.config.settings import Settings, get_settings, resolve_candidate_limit
from sif.core.models import Embedder, SearchOptions
from sif.database.database import Database
from sif.database.repositories import CollectionRepository
from sif.embedding.manager import EmbeddingManager
from sif.search.benchmark import (
    CATEGORIES,
    LEGACY_K_VALUES,
    BenchReport,
    ConfigResult,
    SearchEvaluator,
    SweepRanking,
    iter_grid,
    rank_sweep,
)
from sif.search.hybrid import SearchPipeline
from sif.search.rerank import (
    CrossEncoderReranker,
    LlamaCppReranker,
    Qwen3Reranker,
    create_reranker,
)
from sif.utils.logging import get_logger


logger = get_logger(__name__)
console = Console()
# D-07 stderr contract (search.py precedent): soft-fail warnings must never
# pollute stdout, which stays clean for --json piping (`sif bench --json | jq`).
console_err = Console(stderr=True)

# The four keys every rerank state carries (D-12): metrics plus latency.
_STATE_METRIC_KEYS: tuple[str, ...] = ("ndcg_at_10", "hit_at_10", "p50_ms", "p95_ms")

_Reranker = LlamaCppReranker | CrossEncoderReranker | Qwen3Reranker


@dataclass
class BenchHarness:
    """DB + embedder wiring shared by every measured bench state.

    Bundles the trio every measurement path needs (db, embedder, dim) so the
    measurement helpers stay under the argument-count limit without noqa
    exemptions (house pattern, Phase 12 WatchConfig).
    """

    db: Database
    embedder: Embedder | None
    embedding_dim: int


class CachedEmbedder:
    """Memoizing Embedder wrapper: one embed per distinct query text (D-07).

    The sweep re-runs BM25 and fusion for every configuration while query
    embeddings are identical across configs; wrapping the loaded model
    memoizes ``embed`` per text so each distinct query is embedded once per
    bench invocation — for the baseline and the sweep alike (research
    Pattern 4). No search-signature change.
    """

    def __init__(self, inner: Embedder) -> None:
        """Wrap ``inner``; the memo lives on the wrapper, never the model."""
        self._inner = inner
        self._cache: dict[str, list[float]] = {}

    def embed(self, text: str) -> list[float]:
        """Embed one text, memoized (the model runs once per distinct text)."""
        if text not in self._cache:
            self._cache[text] = self._inner.embed(text)
        return self._cache[text]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts through the per-text cache."""
        return [self.embed(text) for text in texts]

    @property
    def dimension(self) -> int:
        """Forward the inner model's dimensionality."""
        return self._inner.dimension


def _load_embedder(
    settings: Settings,
    model_type: str | None,
) -> tuple[EmbeddingManager | None, int]:
    """Load the embedding model; soft-fail to BM25-only bench on error."""
    if model_type:
        settings = settings.model_copy(update={"model_type": model_type})
    manager = None
    # BM25-only soft-fail keeps the neutral configured dimension (IN-07).
    embedding_dim = settings.embedding_dim
    try:
        manager = EmbeddingManager.from_settings(settings)
        manager.load_model()
        # IN-07 (index.py precedent): prefer the loaded model's metadata dim;
        # probe only when it has no usable integer dimension.
        model_dim = manager.get_model_info().get("embedding_dim")
        embedding_dim = (
            model_dim if isinstance(model_dim, int) else len(manager.embed_single("probe"))
        )
    except ImportError as e:
        console_err.print(f"[yellow]Embedding backend not installed: {e}[/yellow]")
    except Exception as e:
        console_err.print(f"[yellow]Failed to load embedding model: {e}[/yellow]")
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


def _state_metrics(report: BenchReport) -> dict[str, float] | None:
    """Four-key rerank-state summary (metrics plus latency, D-12).

    None when the report's fields are not numeric: a fully mocked report
    (the narrow-width JSON pin substitutes one) must not leak MagicMock
    objects into the JSON payload — states are omitted there instead.
    """
    values = {key: getattr(report, key) for key in _STATE_METRIC_KEYS}
    if not all(isinstance(value, (int, float)) for value in values.values()):
        return None
    return values


def _load_reranker(rerank: bool, settings: Settings) -> _Reranker | None:
    """Load the reranker for the on state — an explicit opt-in (D-12).

    Without --rerank the gate never calls create_reranker, so the off state
    is zero-cost by construction: no model load, no optional-backend import.
    A missing backend or a model-load failure degrades to off-only with a
    warning (bench is diagnostic — the same fail-soft the embedder loader
    uses), while a factory ValueError is a configuration error and stays a
    ClickException.
    """
    if not rerank:
        return None
    try:
        return create_reranker(settings)
    except ImportError as e:
        console_err.print(
            f"[yellow]Reranker backend not available, measuring the off state only: {e}[/yellow]"
        )
    except ValueError as e:
        raise click.ClickException(str(e)) from e
    except Exception as e:
        console_err.print(
            f"[yellow]Failed to load reranker model, measuring the off state only: {e}[/yellow]"
        )
    return None


def _measure_state(
    harness: BenchHarness,
    options: SearchOptions,
    evaluator: SearchEvaluator,
    reranker: _Reranker | None = None,
) -> BenchReport:
    """Measure one state: one hoisted pipeline, warmed per-query timing.

    The pipeline is built once per measured state inside the connection
    context (never per query), so latency measures search rather than
    pipeline re-initialization. The off state passes ``reranker=None`` — it
    never constructs a reranker model (D-12).
    """
    with harness.db.connection:
        pipeline = SearchPipeline(
            harness.db.connection,
            embedder=harness.embedder,
            embedding_dim=harness.embedding_dim,
            reranker=reranker,
        )
        return evaluator.report(
            lambda query: pipeline.search(query, options),
            clock=time.perf_counter,
        )


def _tuning_evaluator(fixture_data: dict, fixture_path: Path) -> SearchEvaluator:
    """Evaluator over the tuning split only — the sweep's ranking set.

    D-03/EVAL-04 guard: held-out queries are filtered out of the fixture
    BEFORE any search call, so a sweep can never consult them while ranking
    configurations. Fixture metadata (relevance_key, corpus_root) is carried
    over so path-keyed relevance resolves identically.

    A fixture with no tuning queries (legacy ``relevant_docids`` fixtures
    carry no split at all) fails loudly: sweeping zero queries would yield an
    empty, meaningless ranking reported as success.
    """
    tuning_queries = [item for item in fixture_data["queries"] if item.get("split") == "tuning"]
    if not tuning_queries:
        raise click.ClickException(
            "Sweep requires fixtures with split labels; this fixture has no "
            "queries with split == 'tuning' (expected 'split': 'tuning' or "
            "'heldout' per query)"
        )
    tuning_fixture = {key: value for key, value in fixture_data.items() if key != "queries"}
    tuning_fixture["queries"] = tuning_queries
    return SearchEvaluator(tuning_fixture, fixture_path=fixture_path)


def _measure_config(
    pipeline: SearchPipeline,
    evaluator: SearchEvaluator,
    options: SearchOptions,
    rerank_pipeline: SearchPipeline | None = None,
) -> ConfigResult:
    """Measure one configuration's tuning metrics into a ConfigResult.

    The per-category breakdown comes from the same report() grouping the
    baseline uses — computed from the per-query values already in hand, with
    zero extra search calls (D-06). With a ``rerank_pipeline`` (D-12), the
    rerank-on state is measured through the same options and both states ride
    the ConfigResult; without one the flat fields ARE the off state and no
    ``states`` mapping is constructed.
    """
    report = evaluator.report(
        lambda query: pipeline.search(query, options),
        clock=time.perf_counter,
    )
    states: dict[str, dict[str, float]] | None = None
    if rerank_pipeline is not None:
        on_report = evaluator.report(
            lambda query: rerank_pipeline.search(query, options),
            clock=time.perf_counter,
        )
        off_state = _state_metrics(report)
        on_state = _state_metrics(on_report)
        if off_state is not None and on_state is not None:
            states = {"off": off_state, "on": on_state}
    return ConfigResult(
        rrf_k=options.rrf_k,
        bm25_weight=options.bm25_weight,
        vector_weight=options.vector_weight,
        ndcg_at_10=report.ndcg_at_10,
        hit_at_10=report.hit_at_10,
        p50_ms=report.p50_ms,
        p95_ms=report.p95_ms,
        categories=report.categories,
        states=states,
    )


def _run_sweep(
    harness: BenchHarness,
    base_options: SearchOptions,
    evaluator: SearchEvaluator,
    reranker: _Reranker | None = None,
) -> tuple[SweepRanking, ConfigResult]:
    """Measure every declared grid configuration and rank it (D-07/D-08/D-09).

    One hoisted pipeline serves all 45 configurations; only the fusion knobs
    (rrf_k/bm25_weight/vector_weight, the Phase 15 per-query override bridge)
    vary per config on top of the Plan 01 ``_build_options`` baseline. With a
    ``reranker``, a second hoisted pipeline measures the rerank-on state per
    configuration (D-12).

    The current-settings run is measured first through the same path as the
    baseline row. When the settings configuration is a grid point (the
    shipped default 60/1.0/1.0 always is), its measured ConfigResult is
    reused for that grid slot so the baseline's deltas are exactly zero
    (research Pitfall 7).
    """
    with harness.db.connection:
        pipeline = SearchPipeline(
            harness.db.connection,
            embedder=harness.embedder,
            embedding_dim=harness.embedding_dim,
        )
        rerank_pipeline = (
            SearchPipeline(
                harness.db.connection,
                embedder=harness.embedder,
                embedding_dim=harness.embedding_dim,
                reranker=reranker,
            )
            if reranker is not None
            else None
        )
        baseline = _measure_config(pipeline, evaluator, base_options, rerank_pipeline)
        baseline_key = (baseline.rrf_k, baseline.bm25_weight, baseline.vector_weight)
        results: list[ConfigResult] = []
        for grid in iter_grid():
            if (grid.rrf_k, grid.bm25_weight, grid.vector_weight) == baseline_key:
                results.append(baseline)
                continue
            results.append(
                _measure_config(
                    pipeline,
                    evaluator,
                    replace(
                        base_options,
                        rrf_k=grid.rrf_k,
                        bm25_weight=grid.bm25_weight,
                        vector_weight=grid.vector_weight,
                    ),
                    rerank_pipeline,
                )
            )
    return rank_sweep(results), baseline


def _config_row(result: ConfigResult, baseline: ConfigResult) -> dict:
    """One sweep JSON row: the config's serialization plus baseline deltas."""
    row = result.to_dict()
    row["ndcg_delta"] = result.ndcg_at_10 - baseline.ndcg_at_10
    row["hit_delta"] = result.hit_at_10 - baseline.hit_at_10
    row["p50_delta_ms"] = result.p50_ms - baseline.p50_ms
    row["p95_delta_ms"] = result.p95_ms - baseline.p95_ms
    return row


def _sweep_payload(ranking: SweepRanking, baseline: ConfigResult) -> dict:
    """Sweep JSON payload with baseline deltas and the baseline row (D-09).

    Ranked configs and the tie group each carry per-metric deltas against
    the current-settings baseline, alongside the winner-honesty fields.
    """
    return {
        "configs": [_config_row(result, baseline) for result in ranking.ranked],
        "tie_group": [_config_row(result, baseline) for result in ranking.tie_group],
        "winner_declared": ranking.winner_declared,
        "epsilon": ranking.epsilon,
        "baseline": baseline.to_dict(),
    }


def _rerank_states(
    report: BenchReport,
    on_report: BenchReport | None,
) -> dict[str, dict[str, float]]:
    """Rerank states mapping for the report: off always, on only when measured."""
    states: dict[str, dict[str, float]] = {}
    off_state = _state_metrics(report)
    if off_state is not None:
        states["off"] = off_state
    if on_report is not None:
        on_state = _state_metrics(on_report)
        if on_state is not None:
            states["on"] = on_state
    return states


def _render_report(
    report: BenchReport,
    on_report: BenchReport | None,
    fixture_name: str,
    output_json: bool,
) -> None:
    """Render the report as JSON or a Rich table.

    JSON goes through click.echo (never Rich) so it strict-parses at narrow
    terminal widths; the table carries the per-category breakdown. Rerank
    states (D-12) are STRICTLY ADDITIVE on the JSON output: every flat
    top-level key Plan 01 pins stays top-level and keeps mirroring the
    always-measured off state, with ``states`` added alongside — never a
    replacement wrapper.
    """
    states = _rerank_states(report, on_report)
    if output_json:
        payload = report.to_dict()
        if states:
            payload["states"] = states
        click.echo(json.dumps(payload, indent=2))
        return
    console.print(_report_table(report, on_report, states, fixture_name))


def _report_table(
    report: BenchReport,
    on_report: BenchReport | None,
    states: dict[str, dict[str, float]],
    fixture_name: str,
) -> Table:
    """Metric table with the per-category breakdown and on/off comparison."""
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
    # On/off comparison (D-12): only rendered when the on state was measured —
    # without --rerank the flat rows above ARE the off state.
    if on_report is not None and "on" in states:
        for label, measured in (("off", report), ("on", on_report)):
            table.add_row(f"Rerank {label} nDCG@10", f"{measured.ndcg_at_10:.4f}")
            table.add_row(f"Rerank {label} Hit@10", f"{measured.hit_at_10:.4f}")
            table.add_row(f"Rerank {label} p50 (ms)", f"{measured.p50_ms:.2f}")
            table.add_row(f"Rerank {label} p95 (ms)", f"{measured.p95_ms:.2f}")
    return table


def _render_sweep(
    ranking: SweepRanking,
    baseline: ConfigResult,
    fixture_name: str,
    output_json: bool,
) -> None:
    """Render the sweep as JSON or a Rich table with the settings baseline.

    JSON goes through click.echo (never Rich) so it strict-parses at narrow
    terminal widths. Every row — the baseline and the tie group included —
    renders its four per-category nDCG@10 columns so a win that quietly
    regresses one category is visible (D-06), plus per-metric deltas against
    the current-settings baseline (D-09).
    """
    if output_json:
        click.echo(json.dumps(_sweep_payload(ranking, baseline), indent=2))
        return
    table = Table(title=f"Parameter Sweep: {fixture_name}")
    table.add_column("rrf_k", justify="right")
    table.add_column("bm25_w", justify="right")
    table.add_column("vec_w", justify="right")
    table.add_column("nDCG@10", justify="right")
    table.add_column("Hit@10", justify="right")
    table.add_column("ΔnDCG", justify="right")
    table.add_column("ΔHit", justify="right")
    table.add_column("p50", justify="right")
    table.add_column("p95", justify="right")
    for category in CATEGORIES:
        table.add_column(f"{category} nDCG@10", justify="right")
    # Rerank states (D-12): an on-state nDCG column appears only when the
    # sweep also measured the rerank-on pipeline per configuration.
    has_states = baseline.states is not None or any(
        result.states is not None for result in ranking.ranked
    )
    if has_states:
        table.add_column("on nDCG@10", justify="right")
    table.add_column("note", justify="center")

    def cells_for(result: ConfigResult, note: str) -> list[str]:
        cells = [
            str(result.rrf_k),
            f"{result.bm25_weight:g}",
            f"{result.vector_weight:g}",
            f"{result.ndcg_at_10:.4f}",
            f"{result.hit_at_10:.4f}",
            f"{result.ndcg_at_10 - baseline.ndcg_at_10:+.4f}",
            f"{result.hit_at_10 - baseline.hit_at_10:+.4f}",
            f"{result.p50_ms:.2f}",
            f"{result.p95_ms:.2f}",
        ]
        cells.extend(f"{result.categories[category].ndcg_at_10:.4f}" for category in CATEGORIES)
        if has_states:
            cells.append(
                f"{result.states['on']['ndcg_at_10']:.4f}" if result.states is not None else ""
            )
        cells.append(note)
        return cells

    # The current SIF_ settings run leads the table as the baseline row; its
    # deltas against itself are zero by construction.
    table.add_row(*cells_for(baseline, "baseline"))
    tie_keys = {
        (result.rrf_k, result.bm25_weight, result.vector_weight) for result in ranking.tie_group
    }
    for result in ranking.ranked:
        key = (result.rrf_k, result.bm25_weight, result.vector_weight)
        table.add_row(*cells_for(result, "*" if key in tie_keys else ""))
    console.print(table)
    if ranking.winner_declared:
        best = ranking.tie_group[0]
        console.print(
            f"[green]Winner declared: rrf_k={best.rrf_k} bm25_w={best.bm25_weight:g} "
            f"vec_w={best.vector_weight:g} is beyond the {ranking.epsilon} tie rule[/green]"
        )
    else:
        console.print(
            f"[yellow]Tie group of {len(ranking.tie_group)} configurations within "
            f"{ranking.epsilon} of the best: no single winner declared[/yellow]"
        )


@click.command("bench")
@click.argument("fixture", type=click.Path(exists=True, path_type=Path))
@click.option("-n", "--limit", default=10, help="Number of results per query")
# A3 waiver (Plan 02): the shipped -C flag keeps its 1..200 Click range so
# narrowing it stays a non-breaking change; the D-10 5..50 bound is enforced
# at resolution through the same resolve_candidate_limit clamp the search
# command uses, so no string and no 200 ever reaches SearchOptions.
@click.option(
    "-C",
    "--candidate-limit",
    default=None,
    type=click.IntRange(1, 200),
    help="Reranker candidate pool size "
    "(default: SIF_RERANK_CANDIDATE_LIMIT or 20; clamped to 5-50)",
)
@click.option("-c", "--collection", multiple=True, help="Collection to search")
@click.option("--all", "search_all", is_flag=True, help="Search all collections")
@click.option("--sweep", is_flag=True, help="Sweep the declared rrf_k/weight grid")
@click.option(
    "--rerank",
    is_flag=True,
    help="Also measure the rerank-on state (default: off only)",
)
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
    candidate_limit: int | None,
    collection: tuple,
    search_all: bool,
    sweep: bool,
    rerank: bool,
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
    metrics. With --sweep, the 45-configuration declared grid
    (rrf_k x bm25_weight x vector_weight) is measured on the tuning split
    only and ranked with the 0.01 tie-group rule. With --rerank, the
    rerank-on state is measured beside the always-measured off state.
    """
    index_path = ctx.obj["index_path"]

    if not index_path.exists():
        console.print("[yellow]No index found. Run 'sif index update' first.[/yellow]")
        return

    # Load fixture (T-16-02): malformed JSON is untrusted input and must
    # surface as a ClickException (non-zero exit), never a raw traceback.
    try:
        with open(fixture, encoding="utf-8") as f:
            fixture_data = json.load(f)
    except (OSError, ValueError) as e:
        raise click.ClickException(f"Benchmark failed: {e}") from e

    # A no-sweep bench run uses the current SIF_ settings as its
    # configuration (D-09, fixes Phase 15 IN-02); invalid config surfaces as
    # a ClickException rather than a raw traceback.
    try:
        settings = get_settings()
    except ValidationError as e:
        raise click.ClickException(str(e)) from e

    # Rerank is an explicit opt-in (D-12); _load_reranker never calls
    # create_reranker without the flag, so the off state is zero-cost.
    reranker = _load_reranker(rerank, settings)

    with open_initialized_database(index_path, Database) as db:
        manager, embedding_dim = _load_embedder(settings, model_type)
        # One embedding-once wrapper per bench invocation serves the baseline
        # and the sweep alike (D-07): every distinct query text is embedded
        # exactly once, then reused across all measurements.
        inner_embedder = manager.model if manager else None
        harness = BenchHarness(
            db=db,
            embedder=CachedEmbedder(inner_embedder) if inner_embedder is not None else None,
            embedding_dim=embedding_dim,
        )
        collection_ids = _resolve_collection_ids(db, collection, search_all)
        options = _build_options(
            limit,
            resolve_candidate_limit(candidate_limit, settings),
            settings,
            collection_ids,
        )
        try:
            if sweep:
                ranking, baseline = _run_sweep(
                    harness,
                    options,
                    _tuning_evaluator(fixture_data, fixture),
                    reranker,
                )
                _render_sweep(ranking, baseline, fixture.name, output_json)
                return
            evaluator = SearchEvaluator(fixture_data, fixture_path=fixture)
            report = _measure_state(harness, options, evaluator)
            on_report = (
                _measure_state(harness, options, evaluator, reranker=reranker)
                if reranker is not None
                else None
            )
        except click.ClickException:
            raise
        except Exception as e:
            raise click.ClickException(f"Benchmark failed: {e}") from e
        _render_report(report, on_report, fixture.name, output_json)
