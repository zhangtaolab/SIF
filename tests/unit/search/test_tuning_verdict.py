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
    DECISION_ADOPT_BREADCRUMB,
    DECISION_INSUFFICIENT,
    DECISION_KEEP,
    DECISION_KEEP_BREADCRUMB,
    MIN_HELDOUT_FOR_EPSILON_WIN,
    SWEEP_GRID,
    decide_breadcrumb_default,
    decide_chunk_default,
    select_tuning_candidate,
)


CANDIDATE = "smaller-384-96"
BREADCRUMB_DUPLICATES = {
    "chunks": 100,
    "documents": 10,
    "title_share": 1.0,
    "in_content_share": 0.545,
    "subchunk_share": 0.459,
    "title_equals_heading_share": 0.937,
}


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


class TestBreadcrumbBodyLegVeto:
    """A title-leg-only or flat-body gain never changes the breadcrumb default."""

    def test_n100_epsilon_tie_does_not_adopt(self) -> None:
        confirmation = noise_gate([0.0] * 100, [0.01] * 100)
        assert confirmation.winner is False

        decision = decide_breadcrumb_default(
            confirmation,
            {
                "body": _constant_gate(100, 0.02),
                "title": _constant_gate(100, 0.02),
            },
            BREADCRUMB_DUPLICATES,
        )

        assert decision.decision == DECISION_KEEP_BREADCRUMB
        assert "overall held-out gate winner is false" in decision.reasons

    def test_n101_overall_and_body_win_adopts(self) -> None:
        decision = decide_breadcrumb_default(
            _constant_gate(101, 0.02),
            {
                "body": _constant_gate(101, 0.015),
                "title": _constant_gate(101, 0.03),
                "replay": _constant_gate(101, 0.0),
            },
            BREADCRUMB_DUPLICATES,
        )

        assert decision.decision == DECISION_ADOPT_BREADCRUMB
        assert decision.confirmation_winner is True
        assert decision.body_winner is True
        assert decision.reasons == ()

    def test_overall_winner_with_a_flat_body_leg_is_title_leg_only(self) -> None:
        decision = decide_breadcrumb_default(
            {"n": 101, "mean_delta": 0.02, "winner": True, "sufficient": True},
            {
                "body": {"n": 101, "mean_delta": 0.0, "winner": False, "sufficient": True},
                "title": {"n": 101, "mean_delta": 0.03, "winner": True, "sufficient": True},
            },
            {"title_share": 1.0, "in_content_share": 0.5, "subchunk_share": 0.4},
        )

        assert decision.decision == DECISION_KEEP_BREADCRUMB
        assert decision.title_winner is True
        assert decision.body_winner is False
        assert any("confined to the title leg" in reason for reason in decision.reasons)

    def test_overall_winner_with_a_non_winning_body_and_title_is_flat_body(self) -> None:
        decision = decide_breadcrumb_default(
            _constant_gate(101, 0.02),
            {
                "body": {"n": 101, "mean_delta": 0.0, "winner": False, "sufficient": True},
                "title": {"n": 101, "mean_delta": 0.0, "winner": False, "sufficient": True},
            },
            BREADCRUMB_DUPLICATES,
        )

        assert decision.decision == DECISION_KEEP_BREADCRUMB
        assert any("flat body leg" in reason for reason in decision.reasons)

    def test_regressing_body_leg_is_rejected_with_numbers(self) -> None:
        decision = decide_breadcrumb_default(
            _constant_gate(101, 0.02),
            {
                "body": {"n": 101, "mean_delta": -0.02, "winner": False, "sufficient": True},
                "title": _constant_gate(101, 0.04),
            },
            BREADCRUMB_DUPLICATES,
        )

        assert decision.decision == DECISION_KEEP_BREADCRUMB
        assert any("negative (regressing)" in reason for reason in decision.reasons)

    def test_regressing_body_leg_alone_keeps_even_without_an_overall_win(self) -> None:
        decision = decide_breadcrumb_default(
            _constant_gate(101, -0.01),
            {
                "body": {"n": 101, "mean_delta": -0.02, "winner": False, "sufficient": True},
            },
            BREADCRUMB_DUPLICATES,
        )

        assert decision.decision == DECISION_KEEP_BREADCRUMB
        assert any("negative (regressing)" in reason for reason in decision.reasons)

    def test_absent_body_leg_is_insufficient_evidence(self) -> None:
        decision = decide_breadcrumb_default(
            _constant_gate(101, 0.02),
            {"title": _constant_gate(101, 0.03)},
            BREADCRUMB_DUPLICATES,
        )

        assert decision.decision == DECISION_INSUFFICIENT
        assert decision.body_winner is False
        assert any("absent" in reason for reason in decision.reasons)

    def test_empty_confirmation_is_insufficient(self) -> None:
        decision = decide_breadcrumb_default(
            noise_gate([], []),
            {"body": _constant_gate(101, 0.02)},
            BREADCRUMB_DUPLICATES,
        )

        assert decision.decision == DECISION_INSUFFICIENT
        assert decision.confirmation_n == 0

    def test_insufficient_body_leg_cannot_adopt(self) -> None:
        decision = decide_breadcrumb_default(
            _constant_gate(101, 0.02),
            {
                "body": {"n": 5, "mean_delta": 0.5, "winner": True, "sufficient": False},
            },
            BREADCRUMB_DUPLICATES,
        )

        assert decision.decision == DECISION_KEEP_BREADCRUMB
        assert decision.body_sufficient is False

    def test_missing_duplicate_summary_cannot_adopt(self) -> None:
        decision = decide_breadcrumb_default(
            _constant_gate(101, 0.02),
            {"body": _constant_gate(101, 0.02)},
            {},
        )

        assert decision.decision == DECISION_KEEP_BREADCRUMB
        assert any("duplicate-signal summary is missing" in reason for reason in decision.reasons)

    @pytest.mark.parametrize(
        ("confirmation", "leg_gates"),
        [
            (noise_gate([], []), {}),
            (noise_gate([0.0] * 100, [0.01] * 100), {"body": _constant_gate(100, 0.02)}),
            (_constant_gate(101, 0.02), {"title": _constant_gate(101, 0.02)}),
            (_constant_gate(101, 0.02), {"body": _constant_gate(101, 0.02)}),
        ],
    )
    def test_duplicate_summary_survives_every_outcome(
        self, confirmation: object, leg_gates: dict[str, object]
    ) -> None:
        decision = decide_breadcrumb_default(confirmation, leg_gates, BREADCRUMB_DUPLICATES)

        assert decision.duplicate_summary == BREADCRUMB_DUPLICATES
        assert decision.to_dict()["duplicate_summary"] == BREADCRUMB_DUPLICATES
        assert decision.min_heldout_for_epsilon_win == 101

    def test_fixed_key_order_and_reasons_are_serialized(self) -> None:
        decision = decide_breadcrumb_default(
            _constant_gate(101, 0.02),
            {"body": {"n": 101, "mean_delta": 0.0, "winner": False, "sufficient": True}},
            BREADCRUMB_DUPLICATES,
        )

        assert list(decision.to_dict()) == [
            "decision",
            "confirmation_n",
            "confirmation_mean_delta",
            "confirmation_winner",
            "confirmation_sufficient",
            "body_winner",
            "body_sufficient",
            "title_winner",
            "duplicate_summary",
            "reasons",
            "min_heldout_for_epsilon_win",
        ]
        assert isinstance(decision.to_dict()["reasons"], list)

    def test_missing_leg_field_raises_a_named_error(self) -> None:
        with pytest.raises(ValueError, match="winner"):
            decide_breadcrumb_default(
                _constant_gate(101, 0.02),
                {"body": {"n": 101, "mean_delta": 0.0, "sufficient": True}},
                BREADCRUMB_DUPLICATES,
            )
