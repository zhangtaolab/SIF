"""Tests for the sweep grid and tie-group ranking (Phase 16, EVAL-03)."""

from __future__ import annotations

import pytest

from sif.search.benchmark import (
    CATEGORIES,
    EPSILON,
    GRID_RRF_K,
    GRID_WEIGHTS,
    ConfigResult,
    iter_grid,
    rank_sweep,
)


def _config(rrf_k: int, bm25_weight: float, vector_weight: float, ndcg: float) -> ConfigResult:
    """Fabricated ConfigResult for pure ranking tests (metrics not measured)."""
    return ConfigResult(
        rrf_k=rrf_k,
        bm25_weight=bm25_weight,
        vector_weight=vector_weight,
        ndcg_at_10=ndcg,
        hit_at_10=ndcg,
    )


class TestIterGrid:
    def test_grid_yields_exactly_45_configurations(self) -> None:
        configs = list(iter_grid())
        assert len(configs) == 45
        assert len(GRID_RRF_K) * len(GRID_WEIGHTS) ** 2 == 45

    def test_grid_contains_shipped_baseline(self) -> None:
        """The shipped default (60, 1.0, 1.0) must be a grid point (Pitfall 7)."""
        keys = [(c.rrf_k, c.bm25_weight, c.vector_weight) for c in iter_grid()]
        assert (60, 1.0, 1.0) in keys

    def test_grid_enumerates_in_declared_order(self) -> None:
        keys = [(c.rrf_k, c.bm25_weight, c.vector_weight) for c in iter_grid()]
        expected = [
            (rrf_k, bm25_weight, vector_weight)
            for rrf_k in GRID_RRF_K
            for bm25_weight in GRID_WEIGHTS
            for vector_weight in GRID_WEIGHTS
        ]
        assert keys == expected

    def test_grid_configs_carry_zeroed_metrics_and_all_categories(self) -> None:
        config = next(iter_grid())
        assert config.ndcg_at_10 == 0.0
        assert config.hit_at_10 == 0.0
        assert list(config.categories.keys()) == list(CATEGORIES)
        assert all(m.count == 0 for m in config.categories.values())


class TestRankSweep:
    def test_tie_group_within_epsilon_declares_no_winner(self) -> None:
        ranking = rank_sweep([_config(20, 0.5, 0.5, 0.500), _config(40, 0.5, 0.5, 0.505)])
        assert len(ranking.tie_group) == 2
        assert ranking.winner_declared is False

    def test_clear_gap_declares_single_winner(self) -> None:
        ranking = rank_sweep([_config(20, 0.5, 0.5, 0.500), _config(40, 0.5, 0.5, 0.520)])
        assert ranking.winner_declared is True
        assert len(ranking.tie_group) == 1
        assert ranking.tie_group[0].rrf_k == 40

    def test_ranking_is_descending_with_grid_order_tiebreak(self) -> None:
        results = [
            _config(100, 2.0, 2.0, 0.5),
            _config(20, 0.5, 0.5, 0.5),
            _config(60, 1.0, 1.0, 0.7),
        ]
        ranking = rank_sweep(results)
        assert [r.rrf_k for r in ranking.ranked] == [60, 20, 100]

    def test_tie_break_follows_weight_order_after_rrf_k(self) -> None:
        results = [
            _config(60, 2.0, 2.0, 0.5),
            _config(60, 0.5, 0.5, 0.5),
            _config(60, 1.0, 2.0, 0.5),
            _config(60, 1.0, 0.5, 0.5),
        ]
        ranking = rank_sweep(results)
        keys = [(r.bm25_weight, r.vector_weight) for r in ranking.ranked]
        assert keys == [(0.5, 0.5), (1.0, 0.5), (1.0, 2.0), (2.0, 2.0)]

    def test_empty_sequence_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="at least one ConfigResult"):
            rank_sweep([])

    def test_epsilon_is_recorded_on_the_ranking(self) -> None:
        ranking = rank_sweep([_config(60, 1.0, 1.0, 0.5)])
        assert ranking.epsilon == EPSILON
        assert ranking.winner_declared is True

    def test_to_dict_serializes_categories_in_declared_order(self) -> None:
        ranking = rank_sweep([_config(60, 1.0, 1.0, 0.5)])
        payload = ranking.to_dict()
        assert set(payload) == {"configs", "tie_group", "winner_declared", "epsilon"}
        config = payload["configs"][0]
        assert list(config["categories"].keys()) == list(CATEGORIES)
        for metrics in config["categories"].values():
            assert {"ndcg_at_10", "hit_at_10"} <= set(metrics)


class TestRankSweepTieBoundary:
    """Pin the strict tie boundary on the 6-decimal-rounded delta (D-08).

    Implementation and tests share ONE arithmetic rule —
    round(best - ndcg_at_10, 6) < EPSILON — so a nominal 0.01 whose raw
    IEEE-754 subtraction yields 0.009999... is exactly 0.01 and never a tie.
    """

    def test_exactly_epsilon_apart_is_not_a_tie(self) -> None:
        ranking = rank_sweep([_config(20, 0.5, 0.5, 0.500), _config(40, 0.5, 0.5, 0.510)])
        assert ranking.winner_declared is True
        assert len(ranking.tie_group) == 1

    def test_just_inside_epsilon_is_a_tie(self) -> None:
        ranking = rank_sweep([_config(20, 0.5, 0.5, 0.500), _config(40, 0.5, 0.5, 0.5099)])
        assert ranking.winner_declared is False
        assert len(ranking.tie_group) == 2

    def test_representation_noise_delta_is_not_a_tie(self) -> None:
        """0.29 - 0.28 is 0.009999999999999953 in raw IEEE-754 arithmetic.

        A naive ``best - ndcg < EPSILON`` comparison misreads that as a tie;
        the rounded-delta rule calls it exactly 0.01 (signal, not noise).
        """
        assert repr(0.29 - 0.28) == "0.009999999999999953"
        ranking = rank_sweep([_config(20, 0.5, 0.5, 0.28), _config(40, 0.5, 0.5, 0.29)])
        assert ranking.ranked[0].ndcg_at_10 == 0.29
        assert ranking.winner_declared is True
        assert len(ranking.tie_group) == 1
