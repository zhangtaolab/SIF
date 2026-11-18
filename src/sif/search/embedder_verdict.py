"""Pure two-sided embedder verdict rule (Phase 23, MODEL-02).

No Click, Rich, embedding, or database imports: this module is a policy over
Phase 18 gate values, unit-testable without loading a model. ``GateResult``
already bundles the N floor, the 95% CI, the rounded 0.01 tie rule, and the
strict 1/N noise-floor veto, so nothing here re-derives bootstrap or gate
arithmetic (D-06, T-23-04).

The default may change only on a two-sided win (D-07, D-08):

(a) the overall held-out gate is a Phase 18 winner, and
(b) every required language's held-out mean delta is at or above -0.01.

A required language whose held-out gate is missing or has fewer than
``SUPPRESS_BELOW`` queries yields ``insufficient-evidence``; it is never
rendered as a zero winner. Every decision records the literal rule booleans
and human-readable reasons, so a rejection stays auditable even though
``GateResult.winner`` bundles four conditions (D-13, T-23-04).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from sif.search.benchmark import EPSILON
from sif.search.personal_bench import SUPPRESS_BELOW, strictly_above_noise_floor


if TYPE_CHECKING:
    from sif.search.personal_bench import GateResult


DECISION_ADOPT = "adopt-harrier"
DECISION_KEEP = "keep-qwen3"
DECISION_INSUFFICIENT = "insufficient-evidence"
# The strict 1/N floor makes a 0.01 mean delta a tie at N=100; only N >= 101
# can be strictly above its own floor (research Pitfall 1).
MIN_HELDOUT_FOR_EPSILON_WIN = 101
LANGUAGE_FLOOR = -EPSILON
_MISSING = object()


@dataclass(frozen=True)
class VerdictDecision:
    """One three-way verdict plus every literal rule input and reason.

    ``decision`` is one of ``DECISION_ADOPT`` / ``DECISION_KEEP`` /
    ``DECISION_INSUFFICIENT``. ``language_heldout_n`` and
    ``language_mean_deltas`` follow ``required_languages`` order; an absent
    language is recorded as ``0`` / ``0.0`` and is never adequate. The
    literal booleans make a rejection auditable even when the overall
    ``winner`` flag is false for an unexpected combination of conditions.
    """

    decision: str
    required_languages: tuple[str, ...]
    adequate: bool
    language_heldout_n: dict[str, int]
    language_mean_deltas: dict[str, float]
    overall_n: int
    overall_mean_delta: float
    overall_ci_low: float
    overall_ci_high: float
    overall_winner: bool
    ci_excludes_zero: bool
    mean_delta_at_least_epsilon: bool
    above_noise_floor: bool
    per_language_floor_ok: bool
    reasons: tuple[str, ...]
    min_heldout_for_epsilon_win: int = MIN_HELDOUT_FOR_EPSILON_WIN

    def to_dict(self) -> dict[str, Any]:
        """Serialize with a fixed key order; nested mappings are copied."""
        return {
            "decision": self.decision,
            "required_languages": list(self.required_languages),
            "adequate": self.adequate,
            "language_heldout_n": dict(self.language_heldout_n),
            "language_mean_deltas": dict(self.language_mean_deltas),
            "overall_n": self.overall_n,
            "overall_mean_delta": self.overall_mean_delta,
            "overall_ci_low": self.overall_ci_low,
            "overall_ci_high": self.overall_ci_high,
            "overall_winner": self.overall_winner,
            "ci_excludes_zero": self.ci_excludes_zero,
            "mean_delta_at_least_epsilon": self.mean_delta_at_least_epsilon,
            "above_noise_floor": self.above_noise_floor,
            "per_language_floor_ok": self.per_language_floor_ok,
            "reasons": list(self.reasons),
            "min_heldout_for_epsilon_win": self.min_heldout_for_epsilon_win,
        }


def _gate_value(gate: Any, field_name: str) -> Any:
    """Read one field from a ``GateResult`` or a mapping gate payload."""
    if isinstance(gate, Mapping):
        if field_name not in gate:
            raise ValueError(f"Gate payload is missing required field {field_name!r}")
        return gate[field_name]
    value = getattr(gate, field_name, _MISSING)
    if value is _MISSING:
        raise ValueError(
            f"Gate must be a GateResult or a mapping carrying {field_name!r}; "
            f"got {type(gate).__name__}"
        )
    return value


def _language_evidence(
    language_heldout: Mapping[str, Any],
    required_languages: tuple[str, ...],
    min_language_n: int,
) -> tuple[dict[str, int], dict[str, float], bool, bool, list[str]]:
    """Collect per-language counts, deltas, adequacy, floor, and reasons."""
    counts: dict[str, int] = {}
    deltas: dict[str, float] = {}
    adequate = True
    floor_ok = True
    reasons: list[str] = []
    for language in required_languages:
        gate = language_heldout.get(language)
        if gate is None:
            counts[language] = 0
            deltas[language] = 0.0
            adequate = False
            floor_ok = False
            reasons.append(
                f"language {language!r} has no held-out gate "
                f"(0 held-out queries; at least {min_language_n} required)"
            )
            continue
        n = int(_gate_value(gate, "n"))
        mean_delta = float(_gate_value(gate, "mean_delta"))
        counts[language] = n
        deltas[language] = mean_delta
        if n < min_language_n:
            adequate = False
            reasons.append(
                f"language {language!r} has {n} held-out queries; "
                f"at least {min_language_n} required"
            )
        if round(mean_delta, 6) < LANGUAGE_FLOOR:
            floor_ok = False
            reasons.append(
                f"language {language!r} held-out mean delta "
                f"{round(mean_delta, 6)} is below the {LANGUAGE_FLOOR} floor"
            )
    return counts, deltas, adequate, floor_ok, reasons


def decide_from_gates(
    heldout: GateResult | Mapping[str, Any] | None,
    language_heldout: Mapping[str, GateResult | Mapping[str, Any] | None],
    *,
    required_languages: tuple[str, ...] = ("en", "zh"),
    min_language_n: int = SUPPRESS_BELOW,
) -> VerdictDecision:
    """Decide from real ``GateResult`` objects or raw gate payloads.

    Adequacy is every required language gate present with ``n >=
    min_language_n``. The language floor is inclusive at exactly ``-0.01``
    under the same rounded arithmetic the tie rule uses. A missing overall
    gate is ``insufficient-evidence`` with zeroed overall fields and a named
    reason.
    """
    counts, deltas, adequate, floor_ok, reasons = _language_evidence(
        language_heldout, required_languages, min_language_n
    )
    if heldout is None:
        reasons.insert(0, "missing overall held-out gate")
        return VerdictDecision(
            decision=DECISION_INSUFFICIENT,
            required_languages=required_languages,
            adequate=adequate,
            language_heldout_n=counts,
            language_mean_deltas=deltas,
            overall_n=0,
            overall_mean_delta=0.0,
            overall_ci_low=0.0,
            overall_ci_high=0.0,
            overall_winner=False,
            ci_excludes_zero=False,
            mean_delta_at_least_epsilon=False,
            above_noise_floor=False,
            per_language_floor_ok=floor_ok,
            reasons=tuple(reasons),
        )
    overall_n = int(_gate_value(heldout, "n"))
    overall_mean_delta = float(_gate_value(heldout, "mean_delta"))
    overall_ci_low = float(_gate_value(heldout, "ci_low"))
    overall_ci_high = float(_gate_value(heldout, "ci_high"))
    overall_winner = bool(_gate_value(heldout, "winner"))
    ci_excludes_zero = overall_ci_low > 0 or overall_ci_high < 0
    mean_delta_at_least_epsilon = round(overall_mean_delta, 6) >= EPSILON
    above_noise_floor = strictly_above_noise_floor(
        overall_mean_delta, float(_gate_value(heldout, "noise_floor"))
    )
    if not adequate:
        decision = DECISION_INSUFFICIENT
    elif overall_winner and floor_ok:
        decision = DECISION_ADOPT
    else:
        decision = DECISION_KEEP
        if not overall_winner:
            reasons.append("overall held-out winner is false")
        if not ci_excludes_zero:
            reasons.append("95% CI includes zero")
        if not mean_delta_at_least_epsilon:
            reasons.append("mean delta below 0.01")
        if not above_noise_floor:
            reasons.append("mean delta is not strictly above the 1/N noise floor")
    return VerdictDecision(
        decision=decision,
        required_languages=required_languages,
        adequate=adequate,
        language_heldout_n=counts,
        language_mean_deltas=deltas,
        overall_n=overall_n,
        overall_mean_delta=overall_mean_delta,
        overall_ci_low=overall_ci_low,
        overall_ci_high=overall_ci_high,
        overall_winner=overall_winner,
        ci_excludes_zero=ci_excludes_zero,
        mean_delta_at_least_epsilon=mean_delta_at_least_epsilon,
        above_noise_floor=above_noise_floor,
        per_language_floor_ok=floor_ok,
        reasons=tuple(reasons),
    )


def _split_gate(per_split: Any, split: str) -> Any:
    """Return one split's gate, treating a malformed entry as absent."""
    if not isinstance(per_split, Mapping):
        return None
    return per_split.get(split)


def decide(
    comparison: Any,
    *,
    required_languages: tuple[str, ...] = ("en", "zh"),
    min_language_n: int = SUPPRESS_BELOW,
) -> VerdictDecision:
    """Decide from a ``ComparisonReport``-shaped object.

    Reads ``comparison.splits["heldout"]`` and
    ``comparison.language_splits[language]["heldout"]``. A missing
    ``heldout`` split raises ``ValueError`` naming it; a missing
    ``language_splits`` attribute is treated as no language evidence, which
    is ``insufficient-evidence`` rather than an exception.
    """
    splits = getattr(comparison, "splits", None)
    if not isinstance(splits, Mapping):
        raise ValueError("comparison is missing a 'splits' mapping")
    if "heldout" not in splits:
        raise ValueError("comparison 'splits' is missing the 'heldout' gate")
    language_splits = getattr(comparison, "language_splits", None) or {}
    if not isinstance(language_splits, Mapping):
        raise ValueError("comparison 'language_splits' must be a mapping")
    language_heldout = {
        language: _split_gate(language_splits.get(language), "heldout")
        for language in required_languages
    }
    return decide_from_gates(
        splits["heldout"],
        language_heldout,
        required_languages=required_languages,
        min_language_n=min_language_n,
    )


def decide_from_payload(
    payload: Any,
    *,
    required_languages: tuple[str, ...] = ("en", "zh"),
    min_language_n: int = SUPPRESS_BELOW,
) -> VerdictDecision:
    """Decide from the CLI comparison JSON payload.

    Reads ``payload["splits"]["heldout"]`` and
    ``payload.get("language_splits", {})``. The payload and its ``splits``
    block must be mappings with a ``heldout`` gate; a missing
    ``language_splits`` block is no language evidence (insufficient), while a
    present non-mapping block is malformed and raises a named ``ValueError``
    (T-23-05).
    """
    if not isinstance(payload, Mapping):
        raise ValueError("comparison payload must be a mapping")
    splits = payload.get("splits")
    if not isinstance(splits, Mapping):
        raise ValueError("comparison payload is missing a 'splits' mapping")
    if "heldout" not in splits:
        raise ValueError("comparison payload 'splits' is missing the 'heldout' gate")
    language_splits = payload.get("language_splits", {})
    if not isinstance(language_splits, Mapping):
        raise ValueError("comparison payload 'language_splits' must be a mapping")
    language_heldout = {
        language: _split_gate(language_splits.get(language), "heldout")
        for language in required_languages
    }
    return decide_from_gates(
        splits["heldout"],
        language_heldout,
        required_languages=required_languages,
        min_language_n=min_language_n,
    )
