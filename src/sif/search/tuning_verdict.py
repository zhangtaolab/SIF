"""Pure chunk-sweep selection and held-out gate policy (Phase 24, QUAL-02).

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
