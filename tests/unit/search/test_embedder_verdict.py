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
