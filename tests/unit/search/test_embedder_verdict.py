"""Table-driven battery for the two-sided embedder verdict rule (Phase 23, MODEL-02).

Pure domain tests: real ``noise_gate`` gates over deterministic value series,
no database, no embedder, and no model load. The rule consumes Phase 18 gate
values verbatim, so these tests pin boundaries (the strict 1/N floor, the
inclusive -0.01 language floor, and the 10-query adequacy floor) rather than
re-deriving gate arithmetic.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from sif.search.embedder_verdict import (
    DECISION_ADOPT,
    DECISION_INSUFFICIENT,
    DECISION_KEEP,
    LANGUAGE_FLOOR,
    MIN_HELDOUT_FOR_EPSILON_WIN,
    decide,
    decide_from_gates,
    decide_from_payload,
)
from sif.search.personal_bench import GateResult, noise_gate


def _gate(baseline: float, current: float, n: int) -> GateResult:
    """A real noise gate over ``n`` constant-value pairs."""
    return noise_gate([baseline] * n, [current] * n)


def _adequate_languages() -> dict[str, GateResult]:
    """Two non-regressing, adequate held-out language gates."""
    return {"en": _gate(0.5, 0.52, 12), "zh": _gate(0.5, 0.50, 11)}


def _winning_overall() -> GateResult:
    """N=101, mean delta 0.02: a Phase 18 winner cleared past the 1/N floor."""
    return _gate(0.5, 0.52, 101)


def _payload(overall: GateResult, languages: dict[str, GateResult]) -> dict[str, object]:
    """A CLI-comparison-shaped payload with raw gate dictionaries."""
    return {
        "splits": {
            "tuning": _gate(0.5, 0.5, 20).to_dict(),
            "heldout": overall.to_dict(),
        },
        "language_splits": {
            language: {"heldout": gate.to_dict()} for language, gate in languages.items()
        },
    }


class TestAdoptEndToEnd:
    def test_adopt_from_gates(self) -> None:
        decision = decide_from_gates(_winning_overall(), _adequate_languages())

        assert decision.decision == DECISION_ADOPT
        assert decision.adequate is True
        assert decision.overall_winner is True
        assert decision.per_language_floor_ok is True
        assert decision.ci_excludes_zero is True
        assert decision.mean_delta_at_least_epsilon is True
        assert decision.above_noise_floor is True
        assert decision.reasons == ()

    def test_adopt_from_comparison_object(self) -> None:
        comparison = SimpleNamespace(
            splits={"tuning": _gate(0.5, 0.5, 20), "heldout": _winning_overall()},
            language_splits={
                language: {"heldout": gate} for language, gate in _adequate_languages().items()
            },
        )

        decision = decide(comparison)

        assert decision.decision == DECISION_ADOPT
        assert decision.required_languages == ("en", "zh")
        assert decision.language_heldout_n == {"en": 12, "zh": 11}

    def test_adopt_from_cli_payload(self) -> None:
        payload = _payload(_winning_overall(), _adequate_languages())

        assert decide_from_payload(payload).decision == DECISION_ADOPT

    def test_min_heldout_floor_and_language_floor_constants(self) -> None:
        assert MIN_HELDOUT_FOR_EPSILON_WIN == 101
        assert pytest.approx(-0.01) == LANGUAGE_FLOOR

    def test_to_dict_emits_fixed_order_and_copies_nested_maps(self) -> None:
        decision = decide_from_gates(_winning_overall(), _adequate_languages())

        serialized = decision.to_dict()

        assert list(serialized) == [
            "decision",
            "required_languages",
            "adequate",
            "language_heldout_n",
            "language_mean_deltas",
            "overall_n",
            "overall_mean_delta",
            "overall_ci_low",
            "overall_ci_high",
            "overall_winner",
            "ci_excludes_zero",
            "mean_delta_at_least_epsilon",
            "above_noise_floor",
            "per_language_floor_ok",
            "reasons",
            "min_heldout_for_epsilon_win",
        ]
        assert serialized["min_heldout_for_epsilon_win"] == 101
        assert serialized["language_heldout_n"] is not decision.language_heldout_n
        assert serialized["reasons"] is not decision.reasons
        serialized["language_heldout_n"]["en"] = 999
        assert decision.language_heldout_n["en"] == 12


class TestBoundaryRules:
    def test_n100_delta_0_01_ties_its_own_noise_floor(self) -> None:
        overall = _gate(0.5, 0.51, 100)

        decision = decide_from_gates(overall, _adequate_languages())

        assert overall.n == 100
        assert overall.noise_floor == pytest.approx(0.01)
        assert overall.winner is False
        assert decision.decision == DECISION_KEEP
        assert decision.above_noise_floor is False
        assert decision.ci_excludes_zero is True
        assert decision.mean_delta_at_least_epsilon is True
        assert any("noise floor" in reason for reason in decision.reasons)

    def test_n101_delta_0_02_clears_the_floor(self) -> None:
        decision = decide_from_gates(_gate(0.5, 0.52, 101), _adequate_languages())

        assert decision.decision == DECISION_ADOPT
        assert decision.overall_winner is True
        assert decision.above_noise_floor is True

    def test_ci_containing_zero_never_adopts(self) -> None:
        overall = noise_gate([0.0, 0.0], [0.0, 0.02])

        decision = decide_from_gates(overall, _adequate_languages())

        assert decision.decision == DECISION_KEEP
        assert decision.ci_excludes_zero is False
        assert any("95% CI includes zero" in reason for reason in decision.reasons)

    def test_language_regression_vetoes_a_winning_overall_gate(self) -> None:
        languages = {"en": _gate(0.5, 0.52, 10), "zh": _gate(0.5, 0.48, 10)}

        decision = decide_from_gates(_winning_overall(), languages)

        assert decision.decision == DECISION_KEEP
        assert decision.overall_winner is True
        assert decision.per_language_floor_ok is False
        assert any("zh" in reason and "-0.02" in reason for reason in decision.reasons)

    def test_language_floor_is_inclusive_at_exactly_minus_0_01(self) -> None:
        languages = {"en": _gate(0.5, 0.50, 10), "zh": _gate(0.5, 0.49, 10)}

        decision = decide_from_gates(_winning_overall(), languages)

        assert languages["zh"].mean_delta == pytest.approx(-0.01)
        assert decision.decision == DECISION_ADOPT
        assert decision.per_language_floor_ok is True


class TestAdequacy:
    def test_absent_required_language_is_insufficient(self) -> None:
        decision = decide_from_gates(_winning_overall(), {"en": _gate(0.5, 0.52, 12)})

        assert decision.decision == DECISION_INSUFFICIENT
        assert decision.decision != DECISION_ADOPT
        assert decision.adequate is False
        assert decision.language_heldout_n["zh"] == 0
        assert decision.per_language_floor_ok is False
        assert any("zh" in reason and "no held-out gate" in reason for reason in decision.reasons)

    def test_thin_language_nine_is_insufficient(self) -> None:
        languages = {"en": _gate(0.5, 0.52, 10), "zh": _gate(0.5, 0.52, 9)}

        decision = decide_from_gates(_winning_overall(), languages)

        assert decision.decision == DECISION_INSUFFICIENT
        assert decision.decision != DECISION_ADOPT
        assert decision.adequate is False
        assert decision.language_heldout_n["zh"] == 9
        assert any("9" in reason and "10" in reason for reason in decision.reasons)

    def test_language_n10_is_adequate(self) -> None:
        languages = {"en": _gate(0.5, 0.52, 10), "zh": _gate(0.5, 0.50, 10)}

        decision = decide_from_gates(_winning_overall(), languages)

        assert decision.adequate is True
        assert decision.decision == DECISION_ADOPT

    def test_decide_without_language_splits_is_insufficient(self) -> None:
        comparison = SimpleNamespace(splits={"heldout": _winning_overall()})

        decision = decide(comparison)

        assert decision.decision == DECISION_INSUFFICIENT
        assert decision.language_heldout_n == {"en": 0, "zh": 0}


class TestMalformedPayloads:
    def test_empty_payload_raises_naming_splits(self) -> None:
        with pytest.raises(ValueError, match="splits"):
            decide_from_payload({})

    def test_payload_without_heldout_raises(self) -> None:
        payload = {"splits": {"tuning": _gate(0.5, 0.5, 20).to_dict()}}

        with pytest.raises(ValueError, match="heldout"):
            decide_from_payload(payload)

    def test_non_mapping_language_splits_raises(self) -> None:
        payload = {
            "splits": {"heldout": _winning_overall().to_dict()},
            "language_splits": [],
        }

        with pytest.raises(ValueError, match="language_splits"):
            decide_from_payload(payload)

    def test_decide_without_heldout_split_raises(self) -> None:
        comparison = SimpleNamespace(splits={"tuning": _gate(0.5, 0.5, 20)})

        with pytest.raises(ValueError, match="heldout"):
            decide(comparison)

    def test_missing_overall_gate_directly_is_insufficient(self) -> None:
        decision = decide_from_gates(None, {"en": _gate(0.5, 0.5, 10)})

        assert decision.decision == DECISION_INSUFFICIENT
        assert decision.overall_n == 0
        assert "missing overall held-out gate" in decision.reasons


class TestReasonAuditability:
    def test_every_rejection_names_a_reason_and_adopt_is_clean(self) -> None:
        rejections = [
            decide_from_gates(_gate(0.5, 0.51, 100), _adequate_languages()),
            decide_from_gates(noise_gate([0.0, 0.0], [0.0, 0.02]), _adequate_languages()),
            decide_from_gates(
                _winning_overall(),
                {"en": _gate(0.5, 0.52, 10), "zh": _gate(0.5, 0.48, 10)},
            ),
            decide_from_gates(_winning_overall(), {"en": _gate(0.5, 0.52, 12)}),
            decide_from_gates(_winning_overall(), {"en": _gate(0.5, 0.52, 9)}),
        ]

        for decision in rejections:
            assert decision.decision != DECISION_ADOPT
            assert decision.reasons, f"{decision.decision} rejection is anonymous"

        adopted = decide_from_gates(_winning_overall(), _adequate_languages())
        assert adopted.decision == DECISION_ADOPT
        assert adopted.reasons == ()
