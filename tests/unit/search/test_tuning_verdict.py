"""Unit battery for the pure chunk-sweep verdict policy (QUAL-02).

Every case is a pure policy check over Phase 18 gate values: the grid shape,
the tuning-selection tie-break, the strict held-out confirmation, the
insufficient-evidence paths, and malformed payload errors. Nothing here loads
a model or touches the database.
"""

from __future__ import annotations

import pytest

from sif.search.personal_bench import noise_gate
from sif.search.tuning_verdict import (
    BASELINE_ARM_NAME,
    DECISION_ADOPT,
    DECISION_INSUFFICIENT,
    DECISION_KEEP,
    MIN_HELDOUT_FOR_EPSILON_WIN,
    SWEEP_GRID,
    decide_chunk_default,
    select_tuning_candidate,
)


CANDIDATE = "smaller-384-96"


def _constant_gate(n: int, delta: float) -> object:
    """A gate whose every paired query gains exactly ``delta``."""
    return noise_gate([0.0] * n, [delta] * n)


class TestGrid:
    """The six-arm grid is fixed and always includes the shipped default."""

    def test_declared_order_and_default(self) -> None:
        assert [arm.name for arm in SWEEP_GRID] == [
            "baseline-512-128",
            "overlap-64",
            "overlap-0",
            "near-default-448-112",
            "smaller-384-96",
            "smallest-256-64",
        ]
        assert (SWEEP_GRID[0].chunk_size, SWEEP_GRID[0].chunk_overlap) == (512, 128)

    def test_six_unique_chunk_configurations(self) -> None:
        configurations = {(arm.chunk_size, arm.chunk_overlap) for arm in SWEEP_GRID}
        assert len(SWEEP_GRID) == 6
        assert len(configurations) == 6

    def test_epsilon_win_floor_is_101(self) -> None:
        assert MIN_HELDOUT_FOR_EPSILON_WIN == 101


class TestHeldoutGateBoundaries:
    """Only a strict held-out winner may change the default (D-03, D-12)."""

    def test_n100_epsilon_tie_keeps_default(self) -> None:
        gate = _constant_gate(100, 0.01)
        assert gate.winner is False  # 0.01 ties its own 1/N floor at N=100.

        decision = decide_chunk_default(CANDIDATE, 0.02, gate)

        assert decision.decision == DECISION_KEEP
        assert "held-out gate winner is false" in decision.reasons

    def test_n101_two_epsilon_win_adopts(self) -> None:
        gate = _constant_gate(101, 0.02)
        assert gate.winner is True

        decision = decide_chunk_default(CANDIDATE, 0.02, gate)

        assert decision.decision == DECISION_ADOPT
        assert decision.reasons == ()

    def test_ci_including_zero_never_adopts(self) -> None:
        current = [0.5] * 51 + [-0.48] * 50
        gate = noise_gate([0.0] * 101, current)
        assert gate.winner is False

        decision = decide_chunk_default(CANDIDATE, 0.02, gate)

        assert decision.decision == DECISION_KEEP
        assert "held-out gate winner is false" in decision.reasons


class TestInsufficientEvidence:
    """Missing evidence is always named, never a fabricated winner."""

    def test_empty_confirmation_is_insufficient(self) -> None:
        decision = decide_chunk_default(CANDIDATE, 0.02, noise_gate([], []))

        assert decision.decision == DECISION_INSUFFICIENT
        assert decision.confirmation_n == 0
        assert "0 evaluated queries" in decision.reasons[0]

    def test_missing_candidate_is_insufficient(self) -> None:
        decision = decide_chunk_default(None, None, _constant_gate(101, 0.05))

        assert decision.decision == DECISION_INSUFFICIENT
        assert decision.selected_arm is None
        assert decision.reasons

    def test_below_sufficiency_floor_is_insufficient(self) -> None:
        decision = decide_chunk_default(CANDIDATE, 0.02, _constant_gate(5, 0.5))

        assert decision.decision == DECISION_INSUFFICIENT
        assert "sufficiency floor" in decision.reasons[0]

    def test_baseline_candidate_keeps_default(self) -> None:
        decision = decide_chunk_default(BASELINE_ARM_NAME, 0.02, _constant_gate(101, 0.05))

        assert decision.decision == DECISION_KEEP
        assert "shipped baseline" in decision.reasons[0]


class TestTuningSelection:
    """Tuning selection is deterministic and never picks the baseline."""

    def test_equal_deltas_resolve_by_wall_time_then_grid_order(self) -> None:
        arms = {
            BASELINE_ARM_NAME: {"mean_delta": 0.0, "embed_wall_seconds": 0.0, "grid_index": 0},
            "overlap-64": {"mean_delta": 0.02, "embed_wall_seconds": 9.0, "grid_index": 1},
            "overlap-0": {"mean_delta": 0.02, "embed_wall_seconds": 5.0, "grid_index": 2},
        }
        assert select_tuning_candidate(arms) == "overlap-0"

        arms["overlap-0"]["embed_wall_seconds"] = 9.0
        assert select_tuning_candidate(arms) == "overlap-64"

    def test_no_positive_candidate_returns_none(self) -> None:
        arms = {
            BASELINE_ARM_NAME: {"mean_delta": 0.0, "embed_wall_seconds": 0.0, "grid_index": 0},
            "overlap-64": {"mean_delta": 0.0, "embed_wall_seconds": 4.0, "grid_index": 1},
            "overlap-0": {"mean_delta": -0.02, "embed_wall_seconds": 3.0, "grid_index": 2},
        }
        assert select_tuning_candidate(arms) is None

    def test_malformed_arm_evidence_names_the_field(self) -> None:
        with pytest.raises(ValueError, match="mean_delta"):
            select_tuning_candidate({"overlap-64": {"embed_wall_seconds": 1.0, "grid_index": 1}})


class TestMalformedConfirmation:
    """A truncated gate payload raises a named ValueError, never a KeyError."""

    @pytest.mark.parametrize("missing", ["n", "mean_delta", "winner", "sufficient"])
    def test_missing_field_raises_named_error(self, missing: str) -> None:
        payload = {"n": 101, "mean_delta": 0.02, "winner": True, "sufficient": True}
        payload.pop(missing)

        with pytest.raises(ValueError, match=missing):
            decide_chunk_default(CANDIDATE, 0.02, payload)

    def test_non_gate_object_raises_named_error(self) -> None:
        with pytest.raises(ValueError, match="GateResult"):
            decide_chunk_default(CANDIDATE, 0.02, object())
