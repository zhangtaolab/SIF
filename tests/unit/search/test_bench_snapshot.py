"""Held-out evidence snapshot: shipped defaults locked to committed numbers.

EVAL-04's honesty bar made testable: the committed held-out metrics reproduce
exactly from the deterministic fixture index using the ``Settings(_env_file=None)``
-derived configuration, the defaults lock lives in the SAME test as the
recomputation (so a default change with only the snapshot's defaults block
edited fails on the metrics), a delta of exactly 0.01 warrants a default
change while 0.0099 never does, and a snapshot without held-out evidence
yields the explicit "unchanged-no-evidence" verdict.

DB-backed tests skip when sqlite-vec is unavailable (build_bench_db's
discipline, consistent with the rest of the suite). A real-model run is a
separate manual evidence step (16-VALIDATION.md Manual-Only Verifications);
this snapshot is the deterministic concept-embedder evidence (research
Pitfall 5).

Snapshot provenance (CORR-02, 2026-11-15): the committed numbers were
regenerated through this same deterministic harness after per-document dedup
landed in ``VectorSearcher`` (one result row per document, carrying chunk
identity and a collapsed match count). This fixture corpus has exactly one
chunk per document, so dedup moved no held-out metric; the snapshot's
``rationale`` string records the pre-dedup and post-dedup totals and
per-category values. The ranking-contract evidence is the regenerated SC1
hybrid golden (byte-identical bm25_score/rrf_score values) plus the
chunky-document integration regression in
``tests/integration/test_search_correctness.py``; the ``--bm25-only`` saved
runs are the BM25 no-drift check, not dedup evidence.

Title-column provenance (CORR-04, 2026-11-15): ``documents_fts`` gained a
``title`` column and BM25 binds equal 1.0/1.0 content/title weights. Held-out
metrics were recomputed through this same harness and did not move (the
rationale records the identical values); the SC1 golden's two BM25-bearing
rows moved while their ordering and RRF scores did not. Every document in this
fixture corpus has an H1 identical to its title, so title text is indexed in
both columns — the research Pitfall 16 duplication that Phase 24 QUAL-03 owns.

D-12 title-weight outcome (19-09, 2026-11-15): the measured 2.0/3.0/4.0
candidates were rejected against B1, so ``_TITLE_WEIGHT`` stays 1.0 and these
metrics are unchanged. The held-out title leg was already at its 1.0 ceiling
and the body held-out leg did not move; the per-candidate GateResult fields
and the accept/reject decision are committed in
``.planning/phases/19-search-correctness/bench/d12-verdict.json``. A future
weight change must regenerate this snapshot (and record a new verdict) rather
than editing the constant alone.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from sif.config.settings import Settings
from sif.core.models import SearchOptions
from sif.embedding.prompts import resolve_prompt_scheme
from sif.search.benchmark import (
    CATEGORIES,
    ConfigResult,
    SearchEvaluator,
    iter_grid,
    rank_sweep,
    warrants_default_change,
)
from sif.search.hybrid import SearchPipeline
from tests.support.bench import (
    EMBEDDING_DIM,
    ConceptEmbedder,
    build_bench_db,
    load_fixture_queries,
)


PACK_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "bench"
FIXTURE_PATH = PACK_ROOT / "queries.json"
CORPUS_ROOT = PACK_ROOT / "corpus"
SNAPSHOT_PATH = PACK_ROOT / "heldout_defaults.json"
VERDICT_CHANGE = "change-warranted"
VERDICT_UNCHANGED = "unchanged"
VERDICT_NO_EVIDENCE = "unchanged-no-evidence"

# D-19: the shipped default embedder. These literals are the pre-Phase-21
# baseline the held-out snapshot was recorded against; assert, never regenerate.
DEFAULT_QWEN3_MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"
DEFAULT_MODEL_TYPE = "modelscope"


def _load_snapshot() -> dict[str, Any]:
    """Load the committed held-out snapshot."""
    with open(SNAPSHOT_PATH, encoding="utf-8") as f:
        return json.load(f)


def _split_fixture(fixture: dict, split: str) -> dict:
    """Fixture copy restricted to one split, metadata carried over (D-03)."""
    filtered = {key: value for key, value in fixture.items() if key != "queries"}
    filtered["queries"] = [item for item in fixture["queries"] if item.get("split") == split]
    return filtered


def _options(rrf_k: int, bm25_weight: float, vector_weight: float) -> SearchOptions:
    """Options for one measured configuration (reranker None, metrics only)."""
    return SearchOptions(
        limit=10,
        include_content=False,
        include_highlights=False,
        rrf_k=rrf_k,
        bm25_weight=bm25_weight,
        vector_weight=vector_weight,
    )


def _measure_heldout(conn, rrf_k: int, bm25_weight: float, vector_weight: float):
    """Recompute held-out metrics on the deterministic index for one config."""
    fixture = load_fixture_queries(FIXTURE_PATH)
    # The fixture PATH (never a bare corpus root) so resolve_corpus_root joins
    # the declared corpus_root and relevance keys match result paths.
    evaluator = SearchEvaluator(_split_fixture(fixture, "heldout"), fixture_path=FIXTURE_PATH)
    pipeline = SearchPipeline(conn, embedder=ConceptEmbedder(), embedding_dim=EMBEDDING_DIM)
    options = _options(rrf_k, bm25_weight, vector_weight)
    return evaluator.report(lambda query: pipeline.search(query, options))


def _assert_defaults_lock(settings: Settings, snapshot: dict[str, Any]) -> None:
    """The shipped defaults ARE the snapshot's defaults (T-16-08).

    Fails with a message naming the snapshot to regenerate, so a drifted
    default cannot hide behind a stale committed evidence file.
    """
    live = (settings.rrf_k, settings.bm25_weight, settings.vector_weight)
    recorded = (
        snapshot["defaults"]["rrf_k"],
        snapshot["defaults"]["bm25_weight"],
        snapshot["defaults"]["vector_weight"],
    )
    assert live == recorded, (
        f"Shipped fusion defaults {live} do not match the held-out snapshot "
        f"{recorded}; regenerate tests/fixtures/bench/heldout_defaults.json "
        "from the deterministic index (and update docs/benchmarking.md) after "
        "changing a default"
    )


def snapshot_verdict(snapshot: dict[str, Any]) -> str:
    """Apply the held-out delta rule to a snapshot dict.

    No held-out evidence (or no candidate to evaluate) can never warrant a
    default change — that absence is an explicit verdict, not silence
    (EVAL-04 "no evidence, no change").
    """
    heldout = snapshot.get("heldout")
    candidate = snapshot.get("candidate")
    if not heldout or not candidate:
        return VERDICT_NO_EVIDENCE
    if warrants_default_change(heldout["ndcg_at_10"], candidate["ndcg_at_10"]):
        return VERDICT_CHANGE
    return VERDICT_UNCHANGED


@pytest.fixture(scope="module")
def live_settings() -> Iterator[Settings]:
    """Fresh Settings without any .env file — the shipped defaults.

    Hermetic (WR-02): the fusion-knob env vars are cleared first so an
    exported SIF_RRF_K / SIF_BM25_WEIGHT / SIF_VECTOR_WEIGHT in the
    developer/CI shell cannot masquerade as changed defaults — the same
    delenv discipline as tests/unit/config/test_settings.py
    (test_fusion_defaults_match_prechange_behavior), made module-scoped via
    MonkeyPatch.context (the built-in monkeypatch fixture is function-scoped).
    """
    with pytest.MonkeyPatch.context() as mp:
        for var in ("SIF_RRF_K", "SIF_BM25_WEIGHT", "SIF_VECTOR_WEIGHT"):
            mp.delenv(var, raising=False)
        yield Settings(_env_file=None)


@pytest.fixture(scope="module")
def bench_conn() -> Iterator:
    """The deterministic bench index (one build shared by this module)."""
    conn = build_bench_db(CORPUS_ROOT, ConceptEmbedder())
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def sweep_ranking(bench_conn) -> Any:
    """rank_sweep over the tuning split on the deterministic index (D-08).

    Latency is irrelevant to ranking, so each configuration is measured
    without a clock — one search per tuning query per grid point.
    """
    fixture = load_fixture_queries(FIXTURE_PATH)
    evaluator = SearchEvaluator(_split_fixture(fixture, "tuning"), fixture_path=FIXTURE_PATH)
    pipeline = SearchPipeline(bench_conn, embedder=ConceptEmbedder(), embedding_dim=EMBEDDING_DIM)
    results: list[ConfigResult] = []
    for grid in iter_grid():
        options = _options(grid.rrf_k, grid.bm25_weight, grid.vector_weight)
        report = evaluator.report(lambda query, o=options: pipeline.search(query, o))
        results.append(
            ConfigResult(
                rrf_k=grid.rrf_k,
                bm25_weight=grid.bm25_weight,
                vector_weight=grid.vector_weight,
                ndcg_at_10=report.ndcg_at_10,
                hit_at_10=report.hit_at_10,
            )
        )
    return rank_sweep(results)


class TestWarrantsDefaultChange:
    def test_inclusive_at_exactly_delta(self) -> None:
        assert warrants_default_change(0.500, 0.510) is True

    def test_rejects_sub_delta_noise(self) -> None:
        assert warrants_default_change(0.500, 0.5099) is False

    def test_rejects_zero_and_negative_deltas(self) -> None:
        assert warrants_default_change(0.500, 0.500) is False
        assert warrants_default_change(0.510, 0.500) is False

    def test_representation_noise_at_nominal_0_01_still_warrants(self) -> None:
        """0.29 - 0.28 is raw 0.009999999999999953; the rounded-delta
        arithmetic (the same rule rank_sweep uses) must count it as 0.01."""
        assert 0.29 - 0.28 < 0.01
        assert warrants_default_change(0.28, 0.29) is True

    def test_custom_delta_threshold(self) -> None:
        assert warrants_default_change(0.500, 0.505, delta=0.005) is True
        assert warrants_default_change(0.500, 0.504, delta=0.005) is False


class TestHeldoutSnapshotReproduction:
    def test_metrics_reproduce_and_defaults_lock_in_one_test(
        self, bench_conn, live_settings
    ) -> None:
        """Tests 2 and 3 share ONE test so the lock cannot drift from the
        recomputation: the measured configuration IS the settings tuple, and
        the settings tuple IS the snapshot's defaults object."""
        snapshot = _load_snapshot()
        _assert_defaults_lock(live_settings, snapshot)

        report = _measure_heldout(
            bench_conn,
            live_settings.rrf_k,
            live_settings.bm25_weight,
            live_settings.vector_weight,
        )
        heldout = snapshot["heldout"]
        assert report.ndcg_at_10 == pytest.approx(heldout["ndcg_at_10"], abs=1e-9)
        assert report.hit_at_10 == pytest.approx(heldout["hit_at_10"], abs=1e-9)
        assert report.num_queries == heldout["num_queries"] == 20
        for category in CATEGORIES:
            recorded = heldout["per_category"][category]
            metrics = report.categories[category]
            assert metrics.ndcg_at_10 == pytest.approx(recorded["ndcg_at_10"], abs=1e-9), category
            assert metrics.hit_at_10 == pytest.approx(recorded["hit_at_10"], abs=1e-9), category
            assert metrics.count == recorded["count"], category

    def test_mutated_snapshot_default_fails_the_lock_with_clear_message(
        self, live_settings
    ) -> None:
        snapshot = _load_snapshot()
        snapshot["defaults"]["rrf_k"] = 80  # only the defaults block mutated
        with pytest.raises(AssertionError, match=r"heldout_defaults\.json"):
            _assert_defaults_lock(live_settings, snapshot)

    def test_settings_default_change_without_metric_regeneration_fails(
        self, bench_conn, live_settings
    ) -> None:
        """The property this snapshot exists to pin: editing a Settings
        default and regenerating ONLY the snapshot's defaults block keeps the
        lock green (the trap) while the recomputed held-out metrics diverge
        from the stale committed values — the equality test fails. Proven
        with vector_weight (the knob that measurably moves held-out nDCG on
        this pack; rrf_k alone does not)."""
        drifted = live_settings.model_copy(update={"vector_weight": 2.0})
        snapshot = _load_snapshot()
        snapshot["defaults"]["vector_weight"] = 2.0  # defaults block "regenerated"
        _assert_defaults_lock(drifted, snapshot)  # passes — insufficient alone

        report = _measure_heldout(
            bench_conn, drifted.rrf_k, drifted.bm25_weight, drifted.vector_weight
        )
        assert report.ndcg_at_10 != pytest.approx(snapshot["heldout"]["ndcg_at_10"], abs=1e-9)


class TestSnapshotVerdict:
    def test_snapshot_without_heldout_block_is_unchanged_no_evidence(self) -> None:
        snapshot = _load_snapshot()
        del snapshot["heldout"]
        verdict = snapshot_verdict(snapshot)
        assert verdict == VERDICT_NO_EVIDENCE
        # No default change may be applied on that verdict.
        assert verdict != VERDICT_CHANGE

    def test_snapshot_without_candidate_is_unchanged_no_evidence(self) -> None:
        snapshot = _load_snapshot()
        del snapshot["candidate"]
        assert snapshot_verdict(snapshot) == VERDICT_NO_EVIDENCE

    def test_committed_verdict_matches_the_delta_rule(self) -> None:
        snapshot = _load_snapshot()
        assert snapshot["verdict"] in (VERDICT_CHANGE, VERDICT_UNCHANGED, VERDICT_NO_EVIDENCE)
        assert snapshot["verdict"] == snapshot_verdict(snapshot)


class TestSweepWinnerEvidence:
    def test_candidate_is_ranked_winner_with_heldout_delta_and_verdict(
        self, bench_conn, live_settings, sweep_ranking
    ) -> None:
        """Test 5: the snapshot's candidate is the rank_sweep winner over the
        tuning split (declared-order first within any tie group), its held-out
        metrics are recomputed from the deterministic index, heldout_delta is
        candidate minus baseline, and the recorded verdict agrees with
        warrants_default_change on the measured values."""
        snapshot = _load_snapshot()
        _assert_defaults_lock(live_settings, snapshot)

        winner = sweep_ranking.ranked[0]
        candidate = snapshot["candidate"]
        assert (winner.rrf_k, winner.bm25_weight, winner.vector_weight) == (
            candidate["rrf_k"],
            candidate["bm25_weight"],
            candidate["vector_weight"],
        )

        report = _measure_heldout(
            bench_conn, winner.rrf_k, winner.bm25_weight, winner.vector_weight
        )
        assert report.ndcg_at_10 == pytest.approx(candidate["ndcg_at_10"], abs=1e-9)
        assert report.hit_at_10 == pytest.approx(candidate["hit_at_10"], abs=1e-9)

        baseline_ndcg = snapshot["heldout"]["ndcg_at_10"]
        assert snapshot["heldout_delta"] == pytest.approx(
            candidate["ndcg_at_10"] - baseline_ndcg, abs=1e-9
        )
        expected = (
            VERDICT_CHANGE
            if warrants_default_change(baseline_ndcg, candidate["ndcg_at_10"])
            else VERDICT_UNCHANGED
        )
        assert snapshot["verdict"] == expected

    def test_winner_ranking_is_deterministic(self, sweep_ranking) -> None:
        """Repeated ranking over identical measurements is stable: the
        ranking order and tie-group size are properties of the pack, so the
        committed candidate cannot flip between runs."""
        assert sweep_ranking.epsilon == 0.01
        assert len(sweep_ranking.ranked) == 45
        keys = [(r.rrf_k, r.bm25_weight, r.vector_weight) for r in sweep_ranking.ranked]
        assert len(set(keys)) == 45  # every declared configuration exactly once


class TestDefaultEmbedderBaseline:
    """D-19: the committed held-out snapshot was recorded on the pre-phase
    prompt-free ModelScope Qwen3 default and the plain, role-less embed path."""

    def test_shipped_defaults_are_prompt_free_modelscope_qwen3(self) -> None:
        """No env override may masquerade as a changed default (D-19 lock)."""
        with pytest.MonkeyPatch.context() as mp:
            for var in (
                "SIF_MODEL_NAME",
                "SIF_MODEL_TYPE",
                "SIF_QUERY_PROMPT_NAME",
                "SIF_DOCUMENT_PROMPT_NAME",
            ):
                mp.delenv(var, raising=False)
            settings = Settings(_env_file=None)

        assert settings.model_type == DEFAULT_MODEL_TYPE
        assert settings.model_name == DEFAULT_QWEN3_MODEL_NAME
        assert settings.query_prompt_name is None
        assert settings.document_prompt_name is None

        scheme = resolve_prompt_scheme(
            settings.model_name,
            settings.model_type,
            settings.query_prompt_name,
            settings.document_prompt_name,
        )
        # Qwen3 has no known-model prompt row, so the default path stays prompt-free.
        assert scheme.query_prompt is None
        assert scheme.document_prompt is None

    def test_snapshot_embedder_has_no_role_prompt_path(self) -> None:
        """The recorded held-out numbers were produced through plain embed_batch.

        ``ConceptEmbedder`` deliberately has no class-level role methods, so the
        snapshot reproduction exercises the same no-prompt path the shipped
        default uses; a future role-aware double must not silently replace it.
        """
        embedder = ConceptEmbedder()
        assert not hasattr(type(embedder), "embed_query")
        assert not hasattr(type(embedder), "embed_documents")
