"""Pure chunk-sweep and breadcrumb gate policy (Phase 24, QUAL-02/03).

No Click, Rich, embedding, or database imports: this module is a policy over
Phase 18 gate values, unit-testable without loading a model. ``GateResult``
already bundles the N floor, the 95% CI, the rounded 0.01 tie rule, and the
strict 1/N noise-floor veto, so nothing here re-derives bootstrap or gate
arithmetic (D-03, D-12, T-24-01).

The selection rule is tuning-select then held-out-confirm (research Pitfall
10): the candidate is chosen on the tuning split as a diagnostic, and the
single candidate is then confirmed on the held-out split. Only a strict
held-out winner of a non-baseline candidate may adopt; every other path
returns ``keep-default`` or ``insufficient-evidence`` with a named reason, so
a rejection stays auditable (D-03, D-12).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from sif.search.benchmark import EPSILON


if TYPE_CHECKING:
    from sif.search.personal_bench import GateResult


BASELINE_ARM_NAME = "baseline-512-128"
DECISION_ADOPT = "adopt-chunking"
DECISION_KEEP = "keep-default"
DECISION_INSUFFICIENT = "insufficient-evidence"
DECISION_ADOPT_BREADCRUMB = "adopt-breadcrumb"
DECISION_KEEP_BREADCRUMB = "keep-breadcrumb-off"
# The strict 1/N floor makes a 0.01 mean delta a tie at N=100; only N >= 101
# can be strictly above its own floor (research Pitfall 1, D-02).
MIN_HELDOUT_FOR_EPSILON_WIN = 101
_MISSING = object()


@dataclass(frozen=True)
class ChunkArm:
    """One sweep arm: a name plus the two chunking knobs it varies."""

    name: str
    chunk_size: int
    chunk_overlap: int


# The fixed six-arm grid, in declaration order. The shipped default 512/128 is
# always the first arm; only chunk_size/chunk_overlap vary (D-01).
SWEEP_GRID: tuple[ChunkArm, ...] = (
    ChunkArm("baseline-512-128", 512, 128),
    ChunkArm("overlap-64", 512, 64),
    ChunkArm("overlap-0", 512, 0),
    ChunkArm("near-default-448-112", 448, 112),
    ChunkArm("smaller-384-96", 384, 96),
    ChunkArm("smallest-256-64", 256, 64),
)


@dataclass(frozen=True)
class TuningDecision:
    """One three-way chunk-default verdict plus every literal gate input.

    ``decision`` is one of ``DECISION_ADOPT`` / ``DECISION_KEEP`` /
    ``DECISION_INSUFFICIENT``. ``reasons`` names every false rule so a
    rejection is auditable; ``adopt-chunking`` alone carries an empty tuple.
    """

    decision: str
    selected_arm: str | None
    tuning_mean_delta: float | None
    confirmation_n: int
    confirmation_mean_delta: float
    confirmation_winner: bool
    confirmation_sufficient: bool
    reasons: tuple[str, ...]
    min_heldout_for_epsilon_win: int = MIN_HELDOUT_FOR_EPSILON_WIN

    def to_dict(self) -> dict[str, Any]:
        """Serialize with a fixed key order matching the field order."""
        return {
            "decision": self.decision,
            "selected_arm": self.selected_arm,
            "tuning_mean_delta": self.tuning_mean_delta,
            "confirmation_n": self.confirmation_n,
            "confirmation_mean_delta": self.confirmation_mean_delta,
            "confirmation_winner": self.confirmation_winner,
            "confirmation_sufficient": self.confirmation_sufficient,
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


def _arm_value(values: Any, field_name: str) -> Any:
    """Read one required tuning-arm evidence field, naming it when absent."""
    if not isinstance(values, Mapping) or field_name not in values:
        raise ValueError(f"tuning arm evidence is missing required field {field_name!r}")
    return values[field_name]


def select_tuning_candidate(arms: Mapping[str, Mapping[str, Any]]) -> str | None:
    """Return the best non-baseline tuning arm, or ``None`` without one.

    ``arms`` maps arm name to a mapping carrying numeric ``mean_delta`` and
    ``embed_wall_seconds`` plus integer ``grid_index``. The baseline arm is
    never a candidate, and an arm whose rounded mean delta is not positive is
    never a candidate. Equal rounded deltas resolve deterministically: lower
    embed wall time first, then fixed grid order (assumption "Adjacency").
    """
    best: tuple[float, float, int, str] | None = None
    for name, values in arms.items():
        if name == BASELINE_ARM_NAME:
            continue
        mean_delta = round(float(_arm_value(values, "mean_delta")), 6)
        embed_wall_seconds = float(_arm_value(values, "embed_wall_seconds"))
        grid_index = int(_arm_value(values, "grid_index"))
        if mean_delta <= 0:
            continue
        candidate = (-mean_delta, embed_wall_seconds, grid_index, name)
        if best is None or candidate < best:
            best = candidate
    return None if best is None else best[3]


def decide_chunk_default(
    selected_arm: str | None,
    tuning_mean_delta: float | None,
    confirmation: GateResult | Mapping[str, Any],
) -> TuningDecision:
    """Decide the chunk default from the tuning pick and the held-out gate.

    ``confirmation`` is a ``GateResult`` or a mapping carrying ``n``,
    ``mean_delta``, ``winner``, and ``sufficient``. Missing evidence is
    ``insufficient-evidence``; a non-strict held-out win, a sub-0.01 mean
    delta, or a baseline candidate is ``keep-default`` with one reason per
    false rule. ``adopt-chunking`` requires the strict held-out winner.
    """
    confirmation_n = int(_gate_value(confirmation, "n"))
    confirmation_mean_delta = float(_gate_value(confirmation, "mean_delta"))
    confirmation_winner = bool(_gate_value(confirmation, "winner"))
    confirmation_sufficient = bool(_gate_value(confirmation, "sufficient"))
    reasons: list[str] = []
    if selected_arm is None:
        reasons.append("no non-baseline arm has a positive tuning mean delta")
        decision = DECISION_INSUFFICIENT
    elif tuning_mean_delta is None:
        reasons.append("the selected arm has no tuning mean delta")
        decision = DECISION_INSUFFICIENT
    elif confirmation_n == 0:
        reasons.append("the held-out confirmation has 0 evaluated queries")
        decision = DECISION_INSUFFICIENT
    elif not confirmation_sufficient:
        reasons.append(
            f"the held-out confirmation has {confirmation_n} queries and is below "
            "the instrument's sufficiency floor"
        )
        decision = DECISION_INSUFFICIENT
    elif selected_arm == BASELINE_ARM_NAME:
        reasons.append("the selected arm is the shipped baseline; the default is unchanged")
        decision = DECISION_KEEP
    elif not confirmation_winner:
        decision = DECISION_KEEP
        reasons.append("held-out gate winner is false")
        if round(confirmation_mean_delta, 6) < EPSILON:
            reasons.append("held-out mean delta is below 0.01")
    else:
        decision = DECISION_ADOPT
    return TuningDecision(
        decision=decision,
        selected_arm=selected_arm,
        tuning_mean_delta=None if tuning_mean_delta is None else float(tuning_mean_delta),
        confirmation_n=confirmation_n,
        confirmation_mean_delta=confirmation_mean_delta,
        confirmation_winner=confirmation_winner,
        confirmation_sufficient=confirmation_sufficient,
        reasons=tuple(reasons),
    )


@dataclass(frozen=True)
class BreadcrumbDecision:
    """One breadcrumb verdict plus the held-out, per-leg, and duplicate inputs.

    ``decision`` is ``DECISION_ADOPT_BREADCRUMB`` or
    ``DECISION_KEEP_BREADCRUMB``, or ``DECISION_INSUFFICIENT`` when the
    evidence cannot decide. ``reasons`` names every false rule, and
    ``duplicate_summary`` is carried on every outcome so a rejection is
    auditable with the measured duplicate shares (D-05, T-24-06).
    """

    decision: str
    confirmation_n: int
    confirmation_mean_delta: float
    confirmation_winner: bool
    confirmation_sufficient: bool
    body_winner: bool
    body_sufficient: bool
    title_winner: bool
    duplicate_summary: dict[str, Any]
    reasons: tuple[str, ...]
    min_heldout_for_epsilon_win: int = MIN_HELDOUT_FOR_EPSILON_WIN

    def to_dict(self) -> dict[str, Any]:
        """Serialize with a fixed key order matching the field order."""
        return {
            "decision": self.decision,
            "confirmation_n": self.confirmation_n,
            "confirmation_mean_delta": self.confirmation_mean_delta,
            "confirmation_winner": self.confirmation_winner,
            "confirmation_sufficient": self.confirmation_sufficient,
            "body_winner": self.body_winner,
            "body_sufficient": self.body_sufficient,
            "title_winner": self.title_winner,
            "duplicate_summary": dict(self.duplicate_summary),
            "reasons": list(self.reasons),
            "min_heldout_for_epsilon_win": self.min_heldout_for_epsilon_win,
        }


def _body_gate(leg_gates: Mapping[str, Any]) -> Any | None:
    """Return the body-leg gate, or ``None`` when the leg is absent."""
    return leg_gates.get("body")


def _breadcrumb_insufficient_reason(
    confirmation_n: int,
    confirmation_sufficient: bool,
    body_present: bool,
) -> str | None:
    """Return why the evidence cannot decide, or ``None`` when it can."""
    if confirmation_n == 0:
        return "the overall held-out confirmation has 0 evaluated queries"
    if not confirmation_sufficient:
        return (
            f"the overall held-out confirmation has {confirmation_n} queries and is below "
            "the instrument's sufficiency floor"
        )
    if not body_present:
        return (
            "the body leg gate is absent; a title-leg-only comparison cannot decide the "
            "breadcrumb default"
        )
    return None


def _breadcrumb_keep_reasons(  # noqa: PLR0913 - one keyword per gate input
    *,
    confirmation_winner: bool,
    body_winner: bool,
    body_sufficient: bool,
    body_mean_delta: float,
    title_winner: bool,
    duplicate_summary: Mapping[str, Any],
) -> list[str] | None:
    """Return the rejection reasons, or ``None`` when adoption is warranted."""
    reasons: list[str] = []
    if not confirmation_winner:
        reasons.append("overall held-out gate winner is false")
        if body_mean_delta < 0:
            reasons.append("body leg mean delta is negative (regressing)")
    elif not body_winner:
        if body_mean_delta < 0:
            reasons.append("body leg mean delta is negative (regressing)")
        elif title_winner:
            reasons.append(
                "the gain is confined to the title leg, which re-states the already-indexed "
                "title; the body leg did not win"
            )
        else:
            reasons.append(
                "the body leg gate winner is false; a flat body leg cannot justify the breadcrumb"
            )
    elif not body_sufficient:
        reasons.append("the body leg gate is below the instrument's sufficiency floor")
    elif not duplicate_summary:
        reasons.append("the duplicate-signal summary is missing")
    return reasons or None


def decide_breadcrumb_default(
    confirmation: GateResult | Mapping[str, Any],
    leg_gates: Mapping[str, GateResult | Mapping[str, Any]],
    duplicates: Mapping[str, Any],
) -> BreadcrumbDecision:
    """Decide the breadcrumb default from the held-out gate and the leg gates.

    ``confirmation`` is the overall held-out ``GateResult`` (or a mapping with
    ``n``, ``mean_delta``, ``winner``, ``sufficient``); ``leg_gates`` maps
    ``title``/``body``/``replay`` to their gates; ``duplicates`` is the
    aggregate duplicate-metric mapping.

    The body-leg veto is mandatory (research Pitfall 5): a breadcrumb gain
    confined to the title leg re-states the already-indexed title, so it is
    ``keep-breadcrumb-off`` even when the overall held-out gate wins. A flat
    or regressing body leg is rejected the same way, and an absent body leg is
    insufficient evidence rather than an implicit pass. Only an overall
    held-out winner with a winning, sufficient body leg and a recorded
    duplicate summary may adopt (D-04, D-05). Bootstrap and the 1/N floor are
    never recomputed here.
    """
    confirmation_n = int(_gate_value(confirmation, "n"))
    confirmation_mean_delta = float(_gate_value(confirmation, "mean_delta"))
    confirmation_winner = bool(_gate_value(confirmation, "winner"))
    confirmation_sufficient = bool(_gate_value(confirmation, "sufficient"))
    body = _body_gate(leg_gates)
    title = leg_gates.get("title")
    body_winner = False if body is None else bool(_gate_value(body, "winner"))
    body_sufficient = False if body is None else bool(_gate_value(body, "sufficient"))
    body_mean_delta = 0.0 if body is None else float(_gate_value(body, "mean_delta"))
    title_winner = False if title is None else bool(_gate_value(title, "winner"))
    summary = dict(duplicates) if isinstance(duplicates, Mapping) else {}
    insufficient = _breadcrumb_insufficient_reason(
        confirmation_n, confirmation_sufficient, body is not None
    )
    if insufficient is not None:
        decision = DECISION_INSUFFICIENT
        reasons = [insufficient]
    else:
        keep_reasons = _breadcrumb_keep_reasons(
            confirmation_winner=confirmation_winner,
            body_winner=body_winner,
            body_sufficient=body_sufficient,
            body_mean_delta=body_mean_delta,
            title_winner=title_winner,
            duplicate_summary=summary,
        )
        decision = DECISION_ADOPT_BREADCRUMB if keep_reasons is None else DECISION_KEEP_BREADCRUMB
        reasons = [] if keep_reasons is None else keep_reasons
    return BreadcrumbDecision(
        decision=decision,
        confirmation_n=confirmation_n,
        confirmation_mean_delta=confirmation_mean_delta,
        confirmation_winner=confirmation_winner,
        confirmation_sufficient=confirmation_sufficient,
        body_winner=body_winner,
        body_sufficient=body_sufficient,
        title_winner=title_winner,
        duplicate_summary=summary,
        reasons=tuple(reasons),
    )
